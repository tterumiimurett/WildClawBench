"""Judge one reference/candidate pair and preserve its evidence and scores."""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import threading

from .corpus import Pair, digest
from .runtime import ModelCallFailure, ModelRuntime, canonical, write_json
from .scoring import merge_judgments, score, validate_forward, validate_reverse, validate_tree
from .adjudication import (apply_adjudication, final_forward_score, has_pending,
                           pending_items, validate_adjudication)

ROOT = Path(__file__).resolve().parents[3]
PROMPTS = ROOT / 'eval/prompts/instruction_eval'


class Evaluator:
    def __init__(self, runtime: ModelRuntime, models: dict[str, str]) -> None:
        self.runtime, self.models = runtime, models
        rules = (PROMPTS / 'retention_rules.md').read_text()
        self.decompose = (PROMPTS / 'decompose.md').read_text() + '\n\n' + rules
        self.audit = (PROMPTS / 'audit.md').read_text() + '\n\n' + self.decompose
        self.forward = (PROMPTS / 'check_forward.md').read_text() + '\n\n' + rules
        self.adjudicate = (PROMPTS / 'adjudicate_forward.md').read_text() + '\n\n' + rules
        self.reverse = (PROMPTS / 'check_reverse.md').read_text()
        self.tree_cache = {}
        self.locks = defaultdict(threading.Lock)
        self.version = digest(canonical({'models': models, 'prompts': [self.decompose, self.audit, self.forward, self.reverse, self.adjudicate],
                                         'adjudication': (ROOT / 'src/utils/instruction_eval/adjudication.py').read_text(),
                                         'evidence_protocol': (ROOT / 'src/utils/instruction_eval/evidence.py').read_text(),
                                         'scoring': (ROOT / 'src/utils/instruction_eval/scoring.py').read_text()}))

    def tree(self, text: str, *, audited: bool) -> tuple[dict, list[str]]:
        key = digest(text) + str(audited)
        with self.locks[key]:
            if key in self.tree_cache:
                return self.tree_cache[key]
            first, first_id = self.runtime.call('decompose', self.models['decompose'], self.decompose,
                                               {'instruction': text}, lambda obj: validate_tree(obj, text))
            calls = [first_id]
            result = first
            if audited:
                result, audit_id = self.runtime.call('audit', self.models['audit'], self.audit,
                    {'instruction': text, 'first_shot': first}, lambda obj: validate_tree(obj, text))
                calls.append(audit_id)
            self.tree_cache[key] = result, calls
            return result, calls

    def check_forward(self, reference: str, candidate: str, tree: dict,
                      *, initial: dict | None = None) -> dict:
        """Check once, then adjudicate only unresolved items in one logical request."""
        calls = {}
        if initial is None:
            initial, calls['forward'] = self.runtime.call('forward', self.models['forward'], self.forward,
                {'reference_text': reference, 'candidate_text': candidate, 'reference_tree': tree},
                lambda obj: validate_forward(tree, obj, candidate))
        validate_forward(tree, initial, candidate)
        pending = pending_items(tree, initial)
        result = {'initial_judgment': initial, 'judgment': initial, 'scoring_tree': tree,
                  'calls': calls, 'pending_items': pending}
        if has_pending(pending):
            try:
                patch, calls['adjudication'] = self.runtime.call('adjudicate_forward',
                    self.models.get('adjudicate', self.models['forward']), self.adjudicate,
                    {'reference_text': reference, 'candidate_text': candidate, 'reference_tree': tree,
                     'initial_judgment': initial, 'pending_items': pending},
                    lambda obj: validate_adjudication(tree, initial, pending, obj, reference, candidate))
                resolved_tree, judgment = apply_adjudication(tree, initial, pending, patch, reference, candidate)
                result.update(adjudication=patch, judgment=judgment, scoring_tree=resolved_tree)
            except ModelCallFailure as exc:
                result['score'] = {'status': 'failed', 'retention': None, 'final_score': None,
                                   'failure_kind': 'adjudication_request_failed', 'failure_reasons': [str(exc)]}
                return result
        result['score'] = final_forward_score(result['scoring_tree'], result['judgment'])
        return result

    def evaluate(self, pair: Pair, *, forward_only: bool = False) -> dict:
        manifest = pair.manifest()
        key = digest(canonical({'pair': manifest, 'evaluation_version': self.version, 'forward_only': forward_only}))
        path = self.runtime.output / 'results' / f'{key}.json'
        if path.exists():
            return json.loads(path.read_text())
        calls, errors = {}, {}
        result = {'pair': manifest, 'evaluation_version': self.version, 'human_review_status': 'pending',
                  'calls': calls, 'stage_errors': errors}
        if forward_only:
            result.pop('human_review_status')
            result['evaluation_mode'] = 'forward_with_targeted_adjudication'
        try:
            ref, calls['reference'] = self.tree(pair.reference, audited=True)
            result['reference_tree'] = ref
        except ModelCallFailure as exc:
            errors['reference_tree'] = str(exc)
            result.update(score={'status': 'failed'}, error=str(exc))
            write_json(self.runtime.output / 'partial_results' / f'{key}.json', result)
            return result
        # Forward checking needs only the frozen reference and candidate text.
        # Its result is retained even if candidate decomposition or reverse checking fails.
        try:
            checked = self.check_forward(pair.reference, pair.candidate, ref)
            result['forward_pipeline'] = checked
            calls.update(checked['calls'])
            forward = checked['judgment']
            result['forward_judgment'] = forward
            result['forward_score'] = checked['score']
            if checked['score']['status'] == 'failed':
                errors['forward'] = canonical(checked['score']['failure_reasons'])
        except ModelCallFailure as exc:
            errors['forward'] = str(exc)
        if forward_only:
            result['score'] = result.get('forward_score', {'status': 'failed', 'retention': None})
            if 'forward_judgment' in result:
                result['judgment'] = {**result['forward_judgment'], 'candidate_actions': {}}
            if errors:
                result['error'] = canonical(errors)
            folder = 'results' if result['score']['status'] == 'scored' else 'partial_results'
            write_json(self.runtime.output / folder / f'{key}.json', result)
            return result
        try:
            candidate, calls['candidate'] = self.tree(pair.candidate, audited=True)
            result['candidate_tree'] = candidate
            reverse, calls['reverse'] = self.runtime.call('reverse', self.models['reverse'], self.reverse,
                {'reference_text': pair.reference, 'candidate_text': pair.candidate,
                 'reference_tree': ref, 'candidate_tree': candidate},
                lambda obj: validate_reverse(ref, candidate, obj, pair.reference, pair.candidate))
            result['reverse_judgment'] = reverse
        except ModelCallFailure as exc:
            errors['reverse_pipeline'] = str(exc)
        if errors:
            result.update(score={'status': 'failed'}, error=canonical(errors))
            write_json(self.runtime.output / 'partial_results' / f'{key}.json', result)
            return result
        judgment = merge_judgments(forward, reverse)
        result.update(judgment=judgment, score=score(checked['scoring_tree'], judgment, candidate))
        write_json(path, result)
        return result
