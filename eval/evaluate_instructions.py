#!/usr/bin/env python3
"""Evaluate a human-reviewed calibration batch; full runs require explicit selection."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
from statistics import mean
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.utils.instruction_eval.corpus import calibration_tasks, load_pairs, load_target_pairs, load_custom_pairs
from src.utils.instruction_eval.runtime import DEFAULT_MODEL, ModelCallFailure, ModelRuntime, write_json
from src.utils.instruction_eval.evaluator import Evaluator


def make_report(output: Path, results: list[dict], expected: int) -> None:
    groups = defaultdict(list)
    for result in results:
        pair = result['pair']
        groups[(pair['corpus'], pair['condition'])].append(result)
    table, lines = [], ['# Instruction evaluation: calibration for human discussion', '',
                       'This is a calibration artifact, not a final benchmark result. '
                       'Model judgments require discussion before a full run.', '',
                       f'Expected comparisons: {expected}; returned: {len(results)}.', '',
                       '| Corpus / condition | Scored | Review | Failed | Forward R (n) | Mean final |',
                       '|---|---:|---:|---:|---:|---:|']
    for (corpus, condition), rows in sorted(groups.items()):
        counts = Counter(row['score']['status'] for row in rows)
        good = [row['score'] for row in rows if row['score']['status'] == 'scored']
        forward_good = [row.get('forward_score', row['score']) for row in rows
                        if row.get('forward_score', row['score'])['status'] == 'scored']
        entry = {'corpus': corpus, 'condition': condition, 'counts': dict(counts),
                 'mean_retention': mean(s['retention'] for s in good) if good else None,
                 'forward_scored_count': len(forward_good),
                 'mean_forward_retention': mean(s['retention'] for s in forward_good) if forward_good else None,
                 'mean_final': mean(s['final_score'] for s in good) if good else None}
        table.append(entry)
        retained = f"{entry['mean_forward_retention']:.4f} ({len(forward_good)})" if forward_good else 'N/A'
        final = f"{entry['mean_final']:.4f}" if good else 'N/A'
        lines.append(f"| {corpus}/{condition} | {counts['scored']} | {counts['needs_review']} | "
                     f"{counts['failed']} | {retained} | {final} |")
    lines += ['', 'Means cover scored rows only; review/failure counts remain explicit. '
              'No downstream performance correlation has been claimed.', '', '## Individual comparisons', '']
    for number, result in enumerate(results, 1):
        pair, scores = result['pair'], result['score']
        detail = output / 'review' / f'{number:03d}.json'
        write_json(detail, result)
        lines += [f"### {number}. {pair['corpus']} — {pair['task_id']}", '',
                  f"Condition: `{pair['condition']}`; status: **{scores['status']}**. "
                  f"[Full tree and evidence]({detail.resolve()})", '']
        if scores['status'] == 'failed':
            lines += [f"Failure: `{result['error']}`", '']
            if 'forward_score' in result:
                lines += [f"Independent forward result: {result['forward_score']['retention']} "
                          f"({result['forward_score']['status']}).", '']
            continue
        if 'forward_score' in result:
            lines += [f"Independent forward retention: {result['forward_score']['retention']} "
                      f"({result['forward_score']['status']}).", '']
        lines += [f"Retention: {scores['retention']}; final: {scores['final_score']}; "
                  f"harmful extras: {scores['harmful_extra_count']}.", '']
        for action in result['reference_tree']['actions']:
            key = action['id']
            lines.append(f"- {key} {action['text']}: local={scores['local_action_scores'][key]}, "
                         f"after dependencies={scores['effective_action_scores'][key]}")
        for reason in scores['review_reasons']:
            lines.append(f'- REVIEW: {reason}')
        bad = [(key, row) for key, row in result['judgment']['atoms'].items()
               if row['value'] == 0 or row['value'] is None and not row.get('skipped')]
        if bad:
            lines += ['', 'Missing/changed/uncertain requirements:', '']
            for key, row in bad:
                lines.append(f"- {key}: {row['reason']} (candidate evidence: {row.get('evidence')!r})")
        for key, row in result['judgment']['candidate_actions'].items():
            if row['classification'] != 'supported':
                lines.append(f"- EXTRA {key} ({row['classification']}): {row['reason']}")
        lines.append('')
    write_json(output / 'summary.json', {'expected': expected, 'returned': len(results), 'conditions': table,
                                       'human_calibration_approved': False})
    write_json(output / 'batch_results.json', results)
    (output / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['inventory', 'report', 'calibration', 'selected', 'full'], default='inventory')
    parser.add_argument('--output', type=Path, default=ROOT / 'eval/experiments/instruction-evaluation-v1')
    parser.add_argument('--input', type=Path, help='JSONL with id, reference and candidate for inventory or selected mode')
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--scope', choices=['target', 'original'], default='target')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--task-id')
    parser.add_argument('--corpus', choices=['wcb', 'tocasr', 'tocasr_recorded'])
    parser.add_argument('--condition')
    parser.add_argument('--decomposer-model', default=DEFAULT_MODEL)
    parser.add_argument('--validator-model', default=DEFAULT_MODEL)
    parser.add_argument('--checker-model', default=DEFAULT_MODEL, help='Default for both independent checkers')
    parser.add_argument('--forward-checker-model')
    parser.add_argument('--reverse-checker-model')
    parser.add_argument('--forward-only', action='store_true',
                        help='Retention only, with one targeted adjudication for unresolved items')
    parser.add_argument('--timeout', type=float, default=240)
    parser.add_argument('--request-interval', type=float, default=.1)
    parser.add_argument('--qpm', type=int, default=100)
    parser.add_argument('--tpm', type=int, default=1_000_000)
    parser.add_argument('--retries', type=int, default=3)
    parser.add_argument('--confirm-human-calibration', action='store_true',
                        help='Use only after the user explicitly approves the calibration results')
    args = parser.parse_args()
    if args.workers < 1 or args.retries < 1 or args.timeout <= 0 or args.request_interval < 0 or args.tpm < 1 or args.qpm < 1:
        parser.error('Invalid runtime bounds')
    if args.mode == 'full' and not args.confirm_human_calibration:
        parser.error('Full runs require explicit human calibration approval; no calls made')
    if args.mode == 'report':
        # Read the latest artifact per comparison; keep immutable older results on disk.
        latest = {}
        artifacts = list((args.output / 'results').glob('*.json'))
        artifacts += list((args.output / 'partial_results').glob('*.json'))
        for path in sorted(artifacts, key=lambda p: p.stat().st_mtime):
            result = json.loads(path.read_text())
            latest[result['pair']['key']] = result
        make_report(args.output, sorted(latest.values(), key=lambda r: r['pair']['key']), len(latest))
        print(json.dumps({'reported': len(latest), 'human_calibration_approved': False}))
        return 0
    if args.input:
        if args.mode not in ('inventory', 'selected'):
            parser.error('--input supports inventory and selected modes')
        try:
            pairs = load_custom_pairs(args.input)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        selections = []
    else:
        pairs = load_target_pairs(ROOT) if args.scope == 'target' else load_pairs(ROOT)
        selections = calibration_tasks(pairs)
    args.output.mkdir(parents=True, exist_ok=True)
    counts = Counter(f'{p.corpus}/{p.condition}' for p in pairs)
    write_json(args.output / 'inventory.json', {'comparisons': len(pairs), 'conditions': dict(counts),
                                              'pairs': [p.manifest() for p in pairs]})
    write_json(args.output / 'calibration_selection.json', selections)
    if args.mode == 'inventory':
        print(json.dumps({'comparisons': len(pairs), 'conditions': len(counts), 'calibration_references': len(selections)}))
        return 0
    if args.mode == 'calibration':
        selected = []
        for index, entry in enumerate(selections):
            options = [p for p in pairs if p.corpus == entry['corpus'] and p.task_id == entry['task_id']]
            if entry['corpus'] == 'tocasr_recorded':
                pass
            elif index % 2 == 0:
                options = [p for p in options if not p.condition.startswith('asr/')]
            else:
                options = [p for p in options if p.condition.startswith('asr/')
                           and ('gpt4o' in p.condition or 'gpt-4o' in p.condition or 'parakeet' in p.condition)
                           and 'typeless' not in p.condition and 'bias' not in p.condition]
            if not options:
                raise ValueError(f'No calibration condition for {entry}')
            selected.append(sorted(options, key=lambda p: p.condition)[0])
        pairs = selected
    for field in ('task_id', 'corpus', 'condition'):
        wanted = getattr(args, field)
        if wanted:
            pairs = [pair for pair in pairs if getattr(pair, field) == wanted]
    if args.limit:
        if args.limit < 1:
            parser.error('--limit must be positive')
        pairs = pairs[:args.limit]
    if args.mode == 'selected' and not (args.task_id or args.limit):
        parser.error('selected mode requires --task-id or --limit')
    if not pairs:
        parser.error('No matching pairs')
    try:
        runtime = ModelRuntime(ROOT, args.output, timeout=args.timeout, interval=args.request_interval,
                               retries=args.retries, tpm=args.tpm, qpm=args.qpm)
    except ModelCallFailure as exc:
        print(str(exc), file=sys.stderr)
        return 2
    evaluator = Evaluator(runtime, {'decompose': args.decomposer_model, 'audit': args.validator_model,
                                    'forward': args.forward_checker_model or args.checker_model,
                                    'reverse': args.reverse_checker_model or args.checker_model})
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(evaluator.evaluate, pair, forward_only=args.forward_only): pair for pair in pairs}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(json.dumps({'completed': len(results), 'total': len(pairs), 'key': result['pair']['key'],
                              'status': result['score']['status']}, ensure_ascii=False), flush=True)
            make_report(args.output, sorted(results, key=lambda r: r['pair']['key']), len(pairs))
    return 1 if any(r['score']['status'] != 'scored' for r in results) else 0


if __name__ == '__main__':
    raise SystemExit(main())
