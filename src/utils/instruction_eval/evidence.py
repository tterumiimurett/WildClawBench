"""Lossless source indexing; fragment boundaries carry no semantic meaning."""
from __future__ import annotations

import copy
import re
from .scoring import InvalidEvaluation

PROTOCOL = """
EVIDENCE TRANSPORT OVERRIDE (supersedes quoted-substring output instructions):
Full source texts and evidence_catalog are provided. Every output evidence,
candidate_evidence and reference_evidence field must contain a catalog ID, or
an inclusive contiguous ID range like C0001:C0003, instead of copying text.
Null remains allowed wherever the output contract allows it. Use I IDs for
instruction evidence, C IDs for candidate evidence (including all Forward
judgments), and R IDs for reference evidence. Select the smallest sufficient
span. Multiple requirements may cite the same span. Fragment boundaries are
NOT action, sentence, or requirement boundaries. Read the FULL text, including
negations and conditions outside the selected span. Input trees may contain
resolved quotations; output evidence must still use catalog IDs.
"""


def catalog(source: str, prefix: str, limit: int = 240) -> list[dict]:
    """Split on whitespace near the limit; never split a non-whitespace token."""
    pieces, start, end = [], 0, 0
    for match in re.finditer(r'\S+\s*|\s+', source):
        if end > start and match.end() - start > limit:
            pieces.append({'id': f'{prefix}{len(pieces)+1:04d}', 'start': start,
                           'end': end, 'text': source[start:end]})
            start = end
        end = match.end()
    if end > start:
        pieces.append({'id': f'{prefix}{len(pieces)+1:04d}', 'start': start,
                       'end': end, 'text': source[start:end]})
    return pieces


def prepare(data: dict) -> dict:
    result = copy.deepcopy(data)
    result['evidence_catalog'] = {prefix: catalog(data[key], prefix)
        for key, prefix in [('instruction', 'I'), ('reference_text', 'R'), ('candidate_text', 'C')]
        if key in data}
    return result


def resolve(result: dict, data: dict) -> dict:
    result = copy.deepcopy(result)
    sources = {prefix: data[key] for key, prefix in
               [('instruction', 'I'), ('reference_text', 'R'), ('candidate_text', 'C')] if key in data}
    catalogs = {prefix: {row['id']: row for row in rows}
                for prefix, rows in data['evidence_catalog'].items()}

    def walk(value):
        if isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for key, item in list(value.items()):
                if key in ('evidence', 'candidate_evidence', 'reference_evidence') and item is not None:
                    prefix = 'R' if key == 'reference_evidence' else ('I' if 'I' in sources else 'C')
                    if not isinstance(item, str):
                        raise InvalidEvaluation('Evidence must be a catalog ID or contiguous range')
                    ids = item.split(':')
                    rows = catalogs[prefix]
                    if len(ids) not in (1, 2) or any(i not in rows for i in ids):
                        raise InvalidEvaluation(f'Invalid {key} ID {item!r}; use {prefix} catalog IDs')
                    first, last = rows[ids[0]], rows[ids[-1]]
                    if first['start'] > last['start']:
                        raise InvalidEvaluation('Evidence range is reversed')
                    value[key] = sources[prefix][first['start']:last['end']]
                else:
                    walk(item)
    walk(result)
    return result
