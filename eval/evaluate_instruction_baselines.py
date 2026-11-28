#!/usr/bin/env python3
"""Evaluate JSONL reference/candidate pairs without executing benchmark agents."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import csv
from pathlib import Path
import sys
import threading
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.utils.instruction_eval.baselines import LLMBaselines, SemDistEncoder, lexical_scores
from src.utils.instruction_eval.corpus import digest, read_instruction_rows
from src.utils.instruction_eval.evidence import prepare, PROTOCOL
from src.utils.instruction_eval.runtime import ModelRuntime, TokenBudget, DEFAULT_MODEL, write_json
from src.utils.instruction_eval.scoring import InvalidEvaluation
from src.utils.instruction_eval.runtime import ModelCallFailure


class Budget(TokenBudget):
    def __init__(self, out: Path):
        super().__init__(800000, 90)
        self.out, self.pause_until = out, 0.0
        self.log_lock = threading.Lock()

    def rate_limited(self):
        with self.lock:
            now = time.monotonic()
            # Concurrent 429s from one burst share one reduction.
            if now >= self.pause_until:
                self.tpm = max(100000, int(self.tpm * .8))
                self.qpm = max(5, int(self.qpm * .8))
            self.pause_until = max(self.pause_until, now + 65)

    def reserve(self, tokens):
        while True:
            with self.lock:
                now = time.monotonic()
                while self.entries and now - self.entries[0][0] >= 60:
                    self.entries.popleft()
                used = sum(v for _, v in self.entries)
                if tokens > self.tpm:
                    raise ModelCallFailure('Request exceeds token reservation limit')
                if now >= self.pause_until and len(self.entries) < self.qpm and used + tokens <= self.tpm:
                    self.entries.append((now, tokens))
                    event = {'time': time.time(), 'window_requests': len(self.entries),
                             'window_reserved_tokens': used + tokens}
                    break
            time.sleep(.1)
        with self.log_lock:
            with (self.out / 'admissions.jsonl').open('a') as f:
                f.write(json.dumps(event) + '\n')




class CachedRuntime(ModelRuntime):
    """Reuse successful identical semantic requests across output-ceiling changes."""
    @staticmethod
    def signature(stage, model, prompt, data, backend):
        return digest(json.dumps([stage, model, prompt, data, backend], ensure_ascii=False, sort_keys=True))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prior = {}
        for path in (self.output / 'calls').glob('*.json'):
            artifact = json.loads(path.read_text()); r = artifact['request']
            if r.get('response_format') != {'type':'json_object'}:
                continue
            key = self.signature(r['stage'],r['model'],r['prompt'],r['data'],r['backend_sha256'])
            self.prior[key] = (artifact['result'],path.stem)

    def call(self, stage, model, prompt, data, validate):
        key = self.signature(stage,model,prompt+'\n\n'+PROTOCOL,prepare(data),self.backend_hash)
        if key in self.prior:
            result, call_id = self.prior[key]
            validate(result)
            return result,call_id
        return super().call(stage,model,prompt,data,validate)


def export_scores(out: Path, results: dict, manifests: list[dict]):
    records=[]
    for meta in manifests:
        row={k:v for k,v in meta.items()}
        metrics=results[meta['id']]['metrics']
        for name,key in [('lexical','lexical_error'),('semdist','semdist'),('aer','aer'),('atomic','atomic_score')]:
            value=metrics.get(name,{})
            row[name+'_status']=value.get('status','not_run')
            row[key]=value.get(key)
        records.append(row)
    fields=list(dict.fromkeys(k for row in records for k in row))
    with (out/'scores.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(records)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--metrics', nargs='+', choices=['lexical','semdist','aer','atomic'], default=['lexical','semdist','aer','atomic'])
    p.add_argument('--embedding-snapshot')
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--max-output-tokens', type=int, default=16000)
    p.add_argument('--resume', action='store_true')
    p.add_argument('--model', default=DEFAULT_MODEL)
    args = p.parse_args()
    rows = [row for _, row in read_instruction_rows(args.input)]
    if args.workers < 1:
        raise ValueError('Workers must be positive')
    args.output.mkdir(parents=True, exist_ok=True)
    manifests = [{k:v for k,v in r.items() if k not in ['reference','candidate']} |
                 {'reference_sha256':digest(r['reference']), 'candidate_sha256':digest(r['candidate'])} for r in rows]
    if args.resume:
        if json.loads((args.output/'manifest.json').read_text()) != manifests:
            raise ValueError('Resume requires identical manifest')
    write_json(args.output / 'manifest.json', manifests)
    prompt_dir = ROOT / 'eval/prompts/instruction_baselines'
    prompt_hashes = {p.name:digest(p.read_text()) for p in prompt_dir.glob('*.md')}
    if args.resume:
        previous_design = json.loads((args.output/'design.json').read_text())
        assert previous_design['prompts'] == prompt_hashes and previous_design['judge'] == args.model
        assert previous_design['embedding_snapshot'] == args.embedding_snapshot
    write_json(args.output / 'design.json', {'max_output_tokens':args.max_output_tokens, 'metrics':args.metrics,'judge':args.model,
        'embedding_snapshot':args.embedding_snapshot,'embedding_max_length':128,
        'prompts':{p.name:digest(p.read_text()) for p in prompt_dir.glob('*.md')},
        'qpm':90,'reserved_tpm':800000,'technical_attempts':3,'atomic_votes':3,
        'aer_question_count':'reference-only generation, no fixed k',
        'label':'AER multilingual adaptation; AASR-style binary task rubric; SemDist multilingual chunked adaptation'})
    if 'semdist' in args.metrics and not args.embedding_snapshot:
        raise ValueError('--embedding-snapshot required for SemDist; never silently skip/truncate')
    encoder = SemDistEncoder(args.embedding_snapshot) if 'semdist' in args.metrics else None
    results = {r['id']:{'id':r['id'],'metrics':{}} for r in rows}
    if args.resume:
        for prior in json.loads((args.output/'results.json').read_text()):
            results[prior['id']] = prior
        for path in (args.output/'pairs').glob('*.json'):
            prior=json.loads(path.read_text()); results[prior['id']]=prior
    for r in rows:
        if 'lexical' in args.metrics and 'lexical' not in results[r['id']]['metrics']:
            results[r['id']]['metrics']['lexical'] = {'status':'scored',**lexical_scores(r['reference'],r['candidate'])}
        if encoder and 'semdist' not in results[r['id']]['metrics']:
            results[r['id']]['metrics']['semdist'] = {'status':'scored',**encoder.score(r['reference'],r['candidate'])}
    write_json(args.output / 'results.json', list(results.values()))
    if not set(args.metrics) & {'aer','atomic'}:
        export_scores(args.output, results, manifests)
        return
    rt = CachedRuntime(ROOT, args.output, retries=3, max_tokens=args.max_output_tokens, qpm=90, tpm=800000)
    rt.token_budget = Budget(args.output)
    if args.resume:
        # Let the previous process's admissions expire before making new requests.
        rt.token_budget.pause_until = time.monotonic() + 65
    llm = LLMBaselines(rt, args.model, prompt_dir)
    groups = {}
    for r in rows:
        groups.setdefault(digest(r['reference']), []).append(r)
    def run(group):
        ref = group[0]['reference']; prepared = {}; errors = {}
        for metric in ['aer','atomic']:
            if metric not in args.metrics:
                continue
            try:
                prepared[metric] = llm.prepare_aer(ref) if metric == 'aer' else llm.prepare_atomic(ref)
            except (InvalidEvaluation, ModelCallFailure) as e:
                errors[metric] = str(e)
        write_json(args.output / 'prepared' / f'{digest(ref)}.json', {'reference_sha256':digest(ref),'prepared':prepared,'errors':errors})
        done=[]
        for r in group:
            result=results[r['id']]
            for metric in ['aer','atomic']:
                if metric not in args.metrics:
                    continue
                if result['metrics'].get(metric,{}).get('status') == 'scored':
                    continue
                if metric in errors:
                    result['metrics'][metric]={'status':'failed','reason':errors[metric]};continue
                try:
                    value=llm.aer(r['candidate'],prepared[metric]) if metric=='aer' else llm.atomic(ref,r['candidate'],prepared[metric])
                    result['metrics'][metric]={'status':'scored',**value}
                except (InvalidEvaluation,ModelCallFailure) as e:
                    result['metrics'][metric]={'status':'failed','reason':str(e)}
            write_json(args.output / 'pairs' / f"{digest(r['id'])}.json",result);done.append(result)
        return done
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        fs=[pool.submit(run,g) for g in groups.values()]
        completed=0
        for future in as_completed(fs):
            for result in future.result():results[result['id']]=result
            completed+=1
            write_json(args.output/'results.json',list(results.values()))
            progress={'references_finished':completed,'references_total':len(groups),'time':time.time()}
            write_json(args.output/'progress.json',progress);print(json.dumps(progress),flush=True)
    export_scores(args.output, results, manifests)
    calls=[json.loads(p.read_text()) for p in (args.output/'calls').glob('*.json')]
    write_json(args.output/'cost.json',{'cached_successful_calls':len(calls),'pair_count':len(rows),
        'prompt_tokens':sum((c.get('usage') or {}).get('prompt_tokens',0) for c in calls),
        'completion_tokens':sum((c.get('usage') or {}).get('completion_tokens',0) for c in calls),
        'sum_call_seconds':sum(c['duration_seconds'] for c in calls),
        'note':'Successful call usage, not dollar price or wall time; reference preparation shared; cache reuse amortizes cost. Failed attempts not included.'})

if __name__=='__main__':main()
