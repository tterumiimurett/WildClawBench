"""Validate requirement graphs and score them without model-assigned weights."""
from __future__ import annotations

from statistics import mean
from typing import Any


class InvalidEvaluation(ValueError):
    """An artifact violates the evaluation contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidEvaluation(message)


def quote(text: Any, source: str, *, optional: bool = False) -> None:
    if optional and text is None:
        return
    require(isinstance(text, str) and bool(text.strip()),
            f'Evidence must be a nonempty exact source substring; received {text!r}')
    require(text in source,
            f'Evidence is not an exact source substring: {text[:240]!r}. Copy a shorter verbatim span; do not normalize spelling, punctuation or case.')


def check_quote(text: Any, source: str, errors: list[str], label: str,
                *, optional: bool = False) -> None:
    """Collect all citation defects so one repair can address them together."""
    try:
        quote(text, source, optional=optional)
    except InvalidEvaluation as exc:
        errors.append(f'{label}: {exc}')


def index_tree(tree: dict) -> tuple[dict, dict, dict]:
    """Return action, atom and atom-owner indices."""
    actions = {a['id']: a for a in tree['actions']}
    atoms, owners = {}, {}

    def visit(node: dict, owner: str | None) -> None:
        if node['kind'] == 'atom':
            atoms[node['id']] = node
            owners[node['id']] = owner
        else:
            for child in node['children']:
                visit(child, owner)

    for action in tree['actions']:
        for group in action['groups']:
            visit(group, action['id'])
    for group in tree['global_context']:
        visit(group, None)
    return actions, atoms, owners


def validate_tree(tree: dict, source: str) -> None:
    require(isinstance(tree, dict), 'Tree must be an object')
    require(isinstance(tree.get('actions'), list), 'actions must be a list')
    require(isinstance(tree.get('global_context'), list), 'global_context must be a list')
    require(isinstance(tree.get('dependencies'), list), 'dependencies must be a list')
    require(isinstance(tree.get('review_reasons'), list)
            and all(isinstance(x, str) and x.strip() for x in tree['review_reasons']),
            'review_reasons must be a string list')
    seen = set()
    evidence_errors = []

    def identify(node: dict) -> None:
        require(isinstance(node, dict), 'Node must be an object')
        key = node.get('id')
        require(isinstance(key, str) and bool(key) and key not in seen, f'Duplicate/invalid node ID: {key!r}')
        seen.add(key)
        require(isinstance(node.get('text'), str) and bool(node['text'].strip()), 'Missing node text')
        check_quote(node.get('evidence'), source, evidence_errors, f'node {key}')

    def visit(node: dict, depth: int = 0) -> None:
        require(depth < 16, 'Tree exceeds depth limit')
        identify(node)
        if node.get('kind') == 'atom':
            require(node.get('match') in ('semantic', 'literal', 'ordering'), 'Invalid atom match mode')
            require('children' not in node, 'Atom cannot have children')
        else:
            require(node.get('kind') == 'group', 'Invalid node kind')
            require(isinstance(node.get('children'), list) and bool(node['children']), 'Empty group')
            for child in node['children']:
                visit(child, depth + 1)

    for action in tree['actions']:
        identify(action)
        require(isinstance(action.get('groups'), list), 'Missing action groups')
        for group in action['groups']:
            require(group.get('kind') == 'group', 'Action children must be groups')
            require(group.get('role') in ('specification', 'local_context'), 'Missing group role')
            visit(group)
    for group in tree['global_context']:
        require(group.get('kind') == 'group', 'Global context children must be groups')
        visit(group)
    actions, atoms, owners = index_tree(tree)
    require(bool(actions or atoms), 'Empty reference is unscorable')
    adjacency = {key: [] for key in actions}
    edges = set()
    for edge in tree['dependencies']:
        before, after = edge.get('from'), edge.get('to')
        require(before in actions and after in actions and before != after, 'Invalid dependency endpoints')
        require((before, after) not in edges, 'Duplicate dependency')
        edges.add((before, after))
        require(isinstance(edge.get('required_atoms'), list), 'Missing dependency requirements')
        required = edge['required_atoms']
        require(len(required) == len(set(required)), 'Duplicate required atom')
        require(all(key in atoms and owners[key] == before for key in required),
                'Dependency requirements must belong to upstream action')
        require(isinstance(edge.get('reason'), str) and bool(edge['reason'].strip()), 'Missing dependency reason')
        check_quote(edge.get('evidence'), source, evidence_errors, f'dependency {before}->{after}')
        adjacency[before].append(after)
    active, done = set(), set()

    def dfs(key: str) -> None:
        require(key not in active, 'Dependency cycle')
        if key in done:
            return
        active.add(key)
        for child in adjacency[key]:
            dfs(child)
        active.remove(key)
        done.add(key)

    for key in actions:
        dfs(key)
    require(not evidence_errors, "\n".join(evidence_errors))


def validate_forward(tree: dict, judgment: dict, candidate: str) -> None:
    actions, atoms, owners = index_tree(tree)
    require(isinstance(judgment, dict), 'Judgment must be an object')
    require(isinstance(judgment.get('gates'), dict)
            and set(judgment['gates']) == set(actions), 'Gate coverage mismatch')
    require(isinstance(judgment.get('atoms'), dict), 'Missing atom judgments')
    require(set(judgment['atoms']) <= set(atoms), 'Unknown atom judgments')
    gates = judgment['gates']
    evidence_errors = []

    def verdict(row: dict, label: str, allow_skip: bool = False, *, atom: bool = False) -> None:
        require(isinstance(row, dict), 'Invalid verdict')
        value = row.get('value')
        half = type(value) is float and value == .5
        require(value is None or type(value) is int and value in (0, 1) or atom and half,
                'Gate must be binary; atom may additionally use the specified 0.5 exception or null')
        if half:
            require(row.get('loss_type') == 'vague_qualifier_omitted',
                    '0.5 requires loss_type=vague_qualifier_omitted, not uncertainty')
        require(isinstance(row.get('reason'), str) and bool(row['reason'].strip()), 'Missing verdict reason')
        check_quote(row.get('evidence'), candidate, evidence_errors, label, optional=value != 1)
        if row.get('skipped', False):
            require(allow_skip and value is None, 'Invalid skipped verdict')

    for key, row in gates.items():
        verdict(row, f'gate {key}')
    for key in atoms:
        owner = owners[key]
        skipped = owner is not None and gates[owner]['value'] == 0
        if key not in judgment['atoms']:
            require(skipped, f'Missing active atom verdict for {key}')
        else:
            verdict(judgment['atoms'][key], f'atom {key}', allow_skip=skipped, atom=True)
    require(not evidence_errors, '\n'.join(evidence_errors))
    require(isinstance(judgment.get('review_reasons'), list)
            and all(isinstance(x, str) and x.strip() for x in judgment['review_reasons']), 'Invalid forward review reasons')


def validate_reverse(tree: dict, candidate_tree: dict, judgment: dict,
                     reference: str, candidate: str) -> None:
    require(isinstance(judgment, dict), 'Reverse judgment must be an object')
    actions, _, _ = index_tree(tree)
    candidate_actions, _, _ = index_tree(candidate_tree)
    reverse = judgment.get('candidate_actions')
    require(isinstance(reverse, dict) and set(reverse) == set(candidate_actions), 'Reverse action coverage mismatch')
    evidence_errors = []
    for key, row in reverse.items():
        require(row.get('classification') in ('supported', 'benign_extra', 'harmful_extra', 'uncertain'),
                'Invalid reverse action class')
        require(isinstance(row.get('reference_action_ids'), list)
                and all(key in actions for key in row['reference_action_ids']), 'Invalid reverse alignment')
        require(isinstance(row.get('reason'), str) and bool(row['reason'].strip()), 'Missing reverse reason')
        check_quote(row.get('candidate_evidence'), candidate, evidence_errors, f'candidate action {key}')
        check_quote(row.get('reference_evidence'), reference, evidence_errors, f'reference support for {key}',
                    optional=row['classification'] != 'harmful_extra')
    require(not evidence_errors, '\n'.join(evidence_errors))
    require(isinstance(judgment.get('review_reasons'), list)
            and all(isinstance(x, str) and x.strip() for x in judgment['review_reasons']), 'Invalid review reasons')


def validate_judgment(tree: dict, candidate_tree: dict, judgment: dict,
                      reference: str, candidate: str) -> None:
    """Validate a merged artifact, including legacy combined judgments."""
    validate_forward(tree, judgment, candidate)
    validate_reverse(tree, candidate_tree, judgment, reference, candidate)


def merge_judgments(forward: dict, reverse: dict) -> dict:
    """Join independent checker outputs only after both have been validated."""
    return {'gates': forward['gates'], 'atoms': forward['atoms'],
            'candidate_actions': reverse['candidate_actions'],
            'review_reasons': [f'Forward: {r}' for r in forward['review_reasons']]
                              + [f'Reverse: {r}' for r in reverse['review_reasons']]}


def score(tree: dict, judgment: dict, candidate_tree: dict | None = None) -> dict:
    """Aggregate validated judgments; unknowns never become zero or silently disappear."""
    actions, atoms, owners = index_tree(tree)
    gates = {key: row['value'] for key, row in judgment['gates'].items()}
    values = {key: row['value'] for key, row in judgment['atoms'].items()}
    reasons = list(tree.get('review_reasons', [])) + list(judgment.get('review_reasons', []))
    if candidate_tree:
        reasons += candidate_tree.get('review_reasons', [])
    reasons += [f'Uncertain extra action: {key}' for key, row in judgment['candidate_actions'].items()
                if row['classification'] == 'uncertain']
    reverse = judgment['candidate_actions']
    harmful = [key for key, row in reverse.items() if row['classification'] == 'harmful_extra']
    nodes = {}

    def node_score(node: dict) -> float | None:
        if node['kind'] == 'atom':
            result = values.get(node['id'])
        else:
            children = [node_score(child) for child in node['children']]
            result = None if None in children else mean(children)
        nodes[node['id']] = result
        return result

    local = {}
    for key, action in actions.items():
        if gates[key] == 0:
            local[key] = 0.0
        elif gates[key] is None:
            local[key] = None
        elif not action['groups']:
            local[key] = 1.0
        else:
            children = [node_score(group) for group in action['groups']]
            local[key] = None if None in children else mean(children)
    context_groups = [node_score(group) for group in tree['global_context']]
    global_score = None if None in context_groups else mean(context_groups) if context_groups else None
    incoming = {key: [] for key in actions}
    for edge in tree['dependencies']:
        incoming[edge['to']].append(edge)
    effective, unavailable, propagation = {}, {}, {}

    def evaluate(key: str) -> None:
        if key in effective:
            return
        causes, unknown = [], gates[key] is None
        for edge in incoming[key]:
            parent = edge['from']
            evaluate(parent)
            if unavailable[parent] is True:
                causes.append({'from': parent, 'failed_atoms': [], 'reason': 'upstream_action_unavailable'})
            elif unavailable[parent] is None:
                unknown = True
            else:
                # The calibrated 0.5 omission penalty is local, not a corrupted input.
                failed = [atom for atom in edge['required_atoms'] if values.get(atom) == 0]
                if failed:
                    causes.append({'from': parent, 'failed_atoms': failed, 'reason': 'required_input_corrupted'})
                elif any(values.get(atom) is None for atom in edge['required_atoms']):
                    unknown = True
        if gates[key] == 0 or causes:
            unavailable[key], effective[key] = True, 0.0
        elif unknown:
            unavailable[key], effective[key] = None, None
        else:
            unavailable[key], effective[key] = False, local[key]
        propagation[key] = causes

    for key in actions:
        evaluate(key)
    components = list(effective.values()) + ([global_score] if context_groups else [])
    baseline = list(local.values()) + ([global_score] if context_groups else [])
    if None in components:
        reasons.append('Unresolved active retention judgment')
    if not components:
        reasons.append('Empty task')
    retention = None if not components or None in components else mean(components)
    raw = None if retention is None else retention - len(harmful) / len(components)
    status = 'needs_review' if reasons else 'scored'
    return {
        'status': status, 'review_reasons': reasons,
        'local_action_scores': local, 'effective_action_scores': effective,
        'node_scores': nodes, 'propagation': propagation, 'global_context_score': global_score,
        'local_retention': None if not baseline or None in baseline else mean(baseline),
        'retention': retention if status == 'scored' else None,
        'harmful_extra_action_ids': harmful, 'harmful_extra_count': len(harmful),
        'reference_component_count': len(components),
        'unclipped_score': raw if status == 'scored' else None,
        'final_score': max(0.0, raw) if status == 'scored' else None,
    }
