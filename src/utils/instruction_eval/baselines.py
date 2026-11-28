"""Independent lexical, embedding, QA and flat-rubric baselines.

These are explicitly named adaptations, never official benchmark scores.
"""
from __future__ import annotations

import math
import re
import statistics
import unicodedata
from pathlib import Path

from .scoring import InvalidEvaluation


def normalized_text(text: str) -> str:
    """NFKC + casefold + punctuation/symbol boundaries; no semantic rewriting."""
    return ' '.join(''.join(' ' if unicodedata.category(c)[0] in 'PS' else c
                           for c in unicodedata.normalize('NFKC', text).casefold()).split())


def edit_rate(reference: list[str], candidate: list[str]) -> float:
    if not reference:
        return 0.0 if not candidate else math.inf
    previous = list(range(len(candidate) + 1))
    for i, a in enumerate(reference, 1):
        current = [i]
        for j, b in enumerate(candidate, 1):
            current.append(min(current[-1] + 1, previous[j] + 1,
                               previous[j - 1] + (a != b)))
        previous = current
    return previous[-1] / len(reference)


def lexical_scores(reference: str, candidate: str) -> dict:
    ref, hyp = normalized_text(reference), normalized_text(candidate)
    han = len(re.findall(r'[\u4e00-\u9fff]', ref))
    letters = len(re.findall(r'[a-z\u4e00-\u9fff]', ref))
    chinese = han / max(1, letters) >= .1
    wer = edit_rate(ref.split(), hyp.split())
    cer = edit_rate(list(ref.replace(' ', '')), list(hyp.replace(' ', '')))
    return {'wer_whitespace': wer, 'cer': cer,
            'lexical_error': cer if chinese else wer,
            'lexical_unit': 'character' if chinese else 'whitespace_word',
            'normalization': 'nfkc_casefold_punctuation_symbol_boundaries_v1'}


def chunks(tokens: list[int], size: int) -> list[list[int]]:
    if size < 1:
        raise ValueError('Chunk capacity must be positive')
    return [tokens[i:i + size] for i in range(0, len(tokens), size)] or [[]]


class SemDistEncoder:
    """Mean contextual embedding cosine distance; all tokens covered in chunks."""
    def __init__(self, snapshot: str, max_length: int = 128, device: str = 'cpu'):
        import torch
        from transformers import AutoModel, AutoTokenizer
        self.torch = torch
        torch.set_num_threads(4)
        self.tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True)
        self.model = AutoModel.from_pretrained(snapshot, local_files_only=True,
                                               use_safetensors=True).to(device).eval()
        self.device = device
        probe = self.tokenizer.encode('probe', add_special_tokens=False)
        self.start_id, self.end_id = self.tokenizer.cls_token_id, self.tokenizer.sep_token_id
        if self.tokenizer.encode('probe') != [self.start_id] + probe + [self.end_id]:
            raise ValueError('Unsupported special-token layout for chunking')
        self.max_length = max_length
        self.cache = {}

    def encode(self, text: str):
        if text in self.cache:
            return self.cache[text]
        torch = self.torch
        ids = self.tokenizer.encode(text, add_special_tokens=False, truncation=False, verbose=False)
        pieces = chunks(ids, self.max_length - self.tokenizer.num_special_tokens_to_add(False))
        total = None
        count = 0
        with torch.inference_mode():
            for part in pieces:
                # Generic FastTokenizer.prepare_for_model may build mismatched
                # token_type_ids for this checkpoint. The verified layout is CLS/body/SEP.
                inputs = [self.start_id] + part + [self.end_id]
                batch = {'input_ids': torch.tensor([inputs], device=self.device),
                         'attention_mask': torch.ones((1, len(inputs)), dtype=torch.long, device=self.device)}
                output = self.model(**batch).last_hidden_state[0]
                mask = batch['attention_mask'][0].bool()
                value = output[mask].sum(0).cpu()
                total = value if total is None else total + value
                count += int(mask.sum())
        vector = total / count
        vector = vector / vector.norm().clamp_min(1e-12)
        self.cache[text] = (vector, {'tokens': len(ids), 'chunks': len(pieces), 'pooled_tokens': count})
        return self.cache[text]

    def score(self, reference: str, candidate: str) -> dict:
        a, am = self.encode(reference)
        b, bm = self.encode(candidate)
        similarity = max(-1.0, min(1.0, float(a @ b)))
        return {'semdist': 0.0 if reference == candidate else 1 - similarity,
                'reference_coverage': am, 'candidate_coverage': bm,
                'variant': 'multilingual_minilm_mean_cosine_chunked_v1'}


def validate_items(obj: dict, key: str, field: str, prefix: str) -> None:
    items = obj.get(key)
    if not isinstance(items, list) or not items:
        raise InvalidEvaluation(f'{key} must be nonempty')
    if [x.get('id') for x in items] != [f'{prefix}{i}' for i in range(1, len(items) + 1)]:
        raise InvalidEvaluation('IDs must be unique and consecutive')
    texts = [x.get(field) for x in items]
    if any(not isinstance(v, str) or not v.strip() for v in texts) or len(set(texts)) != len(texts):
        raise InvalidEvaluation('Items must contain unique nonempty text')


def validate_values(obj: dict, key: str, field: str, ids: list[str], binary: bool) -> None:
    items = obj.get(key)
    if not isinstance(items, list) or len(items) != len(ids) or {x.get('id') for x in items} != set(ids):
        raise InvalidEvaluation('Response IDs must cover inputs exactly once')
    for item in items:
        value = item.get(field)
        if binary:
            if type(value) is not bool:
                raise InvalidEvaluation(f'{field} must be boolean')
        elif field not in item or (value is not None and (not isinstance(value, str) or not value.strip())):
            raise InvalidEvaluation('Answer must be nonempty text or explicit null')


def majority(votes: list[dict], ids: list[str]) -> dict:
    if len(votes) != 3:
        raise InvalidEvaluation('Exactly three successful independent votes required')
    for vote in votes:
        validate_values(vote, 'judgments', 'preserved', ids, True)
    maps = [{v['id']: v['preserved'] for v in vote['judgments']} for vote in votes]
    scores = {i: int(sum(v[i] for v in maps) >= 2) for i in ids}
    return {'atomic_score': statistics.mean(scores.values()), 'atom_scores': scores,
            'disagreement_count': sum(len({v[i] for v in maps}) > 1 for i in ids)}


class LLMBaselines:
    def __init__(self, runtime, model: str, prompt_dir: Path):
        self.runtime, self.model, self.prompt_dir = runtime, model, prompt_dir

    def call(self, stage: str, data: dict, validate):
        return self.runtime.call('baseline_' + stage, self.model,
                                 (self.prompt_dir / f'{stage}.md').read_text(), data, validate)[0]

    def prepare_aer(self, reference: str) -> dict:
        questions = self.call('aer_questions', {'context': reference},
                              lambda x: validate_items(x, 'questions', 'question', 'q'))['questions']
        answers = self.answer(reference, questions)
        if any(a['answer'] is None for a in answers['answers']):
            raise InvalidEvaluation('Generated question is unanswerable from reference; calibration required')
        return {'questions': questions, 'reference_answers': answers['answers']}

    def answer(self, context: str, questions: list[dict]) -> dict:
        # Deliberately accepts only one context, never the other text or reference answers.
        return self.call('aer_answers', {'context': context, 'questions': questions},
                         lambda x: validate_values(x, 'answers', 'answer', [q['id'] for q in questions], False))

    def aer(self, candidate: str, prepared: dict) -> dict:
        answers = self.answer(candidate, prepared['questions'])['answers']
        refs = {a['id']: a['answer'] for a in prepared['reference_answers']}
        hyps = {a['id']: a['answer'] for a in answers}
        comparisons = [{**q, 'reference_answer': refs[q['id']], 'candidate_answer': hyps[q['id']]}
                       for q in prepared['questions']]
        ids = list(refs)
        def validate_comparison(obj):
            validate_values(obj, 'judgments', 'equivalent', ids, True)
            if any(hyps[x['id']] is None and x['equivalent'] for x in obj['judgments']):
                raise InvalidEvaluation('Missing candidate answer cannot match a known reference answer')
        judged = self.call('aer_compare', {'comparisons': comparisons}, validate_comparison)
        return {'aer': statistics.mean(not x['equivalent'] for x in judged['judgments']),
                'answers': answers, 'comparison': judged}

    def prepare_atomic(self, reference: str) -> list[dict]:
        return self.call('atomic_generate', {'context': reference},
                         lambda x: validate_items(x, 'rubrics', 'requirement', 'r'))['rubrics']

    def atomic(self, reference: str, candidate: str, rubrics: list[dict]) -> dict:
        ids = [r['id'] for r in rubrics]
        votes = [self.call('atomic_check', {'reference': reference, 'candidate': candidate,
                                          'rubrics': rubrics, 'independent_repeat': i},
                           lambda x: validate_values(x, 'judgments', 'preserved', ids, True))
                 for i in range(1, 4)]
        return {**majority(votes, ids), 'votes': votes}
