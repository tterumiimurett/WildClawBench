"""One bounded adjudication of unresolved Forward items; no changes to known verdicts."""
from copy import deepcopy

from .scoring import index_tree, quote, require, score, validate_forward


def pending_items(tree: dict, judgment: dict) -> dict:
    _, _, owners = index_tree(tree)
    gates = [key for key, row in judgment['gates'].items() if row['value'] is None]
    atoms = [key for key, row in judgment['atoms'].items()
             if row['value'] is None and not row.get('skipped')
             and (owners[key] is None or judgment['gates'][owners[key]]['value'] != 0)]
    issues = []
    for scope, value in [('reference', tree), ('forward', judgment)]:
        for i, reason in enumerate(value.get('review_reasons', [])):
            issues.append({'id': f'{scope}_{i}', 'scope': scope, 'reason': reason})
    return {'gates': gates, 'atoms': atoms, 'issues': issues}


def has_pending(pending: dict) -> bool:
    return any(pending.values())


def validate_adjudication(tree: dict, initial: dict, pending: dict, patch: dict,
                          reference: str, candidate: str) -> None:
    require(isinstance(patch, dict) and set(patch) == {'gates', 'atoms', 'issues'},
            'Adjudication returns only gates, atoms, issues; no tree or aggregate scores')
    for field in ('gates', 'atoms'):
        require(isinstance(patch[field], dict) and set(patch[field]) == set(pending[field]),
                f'Adjudication {field} may contain exactly the unresolved IDs')
    require(isinstance(patch['issues'], dict)
            and set(patch['issues']) == {row['id'] for row in pending['issues']},
            'Adjudication issue coverage mismatch')
    for row in patch['issues'].values():
        require(isinstance(row, dict) and row.get('status') in ('nonblocking', 'unresolved'),
                'Issue status must be nonblocking or unresolved')
        require(isinstance(row.get('reason'), str) and bool(row['reason'].strip()),
                'Missing adjudication issue reason')
        quote(row.get('reference_evidence'), reference, optional=row['status'] == 'unresolved')
        quote(row.get('candidate_evidence'), candidate, optional=row['status'] == 'unresolved')
    merged = deepcopy(initial)
    for field in ('gates', 'atoms'):
        merged[field].update(patch[field])
    validate_forward(tree, merged, candidate)


def apply_adjudication(tree: dict, initial: dict, pending: dict, patch: dict,
                       reference: str, candidate: str) -> tuple[dict, dict]:
    validate_adjudication(tree, initial, pending, patch, reference, candidate)
    resolved_tree, judgment = deepcopy(tree), deepcopy(initial)
    for field in ('gates', 'atoms'):
        judgment[field].update(deepcopy(patch[field]))
    resolved_tree['review_reasons'] = []
    judgment['review_reasons'] = []
    for issue in pending['issues']:
        decision = patch['issues'][issue['id']]
        destination = resolved_tree if issue['scope'] == 'reference' else judgment
        if decision['status'] == 'nonblocking':
            destination.setdefault('diagnostic_notes', []).append(
                {'original_reason': issue['reason'], 'adjudication': deepcopy(decision)})
        else:
            destination['review_reasons'].append(decision['reason'])
    return resolved_tree, judgment


def final_forward_score(tree: dict, judgment: dict) -> dict:
    """Production Forward exits with a score or explicit failure, never pending review."""
    result = score(tree, {**judgment, 'candidate_actions': {}})
    if result['status'] == 'needs_review':
        result['status'] = 'failed'
        result['failure_kind'] = 'semantic_unresolved_after_adjudication'
        result['failure_reasons'] = list(result['review_reasons'])
    return result
