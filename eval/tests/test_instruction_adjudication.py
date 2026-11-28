"""Regression checks for bounded adjudication and calibrated fractional semantics."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from eval.evaluate_instructions import Evaluator, make_report
from src.utils.instruction_eval.adjudication import pending_items, apply_adjudication
from src.utils.instruction_eval.corpus import Pair
from src.utils.instruction_eval.scoring import InvalidEvaluation, validate_forward, score
from src.utils.instruction_eval.runtime import ModelCallFailure

TEXT = 'Collect recent messages. Summarize them.'
CANDIDATE = 'Collect messages. Summarize them.'


def fixtures():
    tree = {'actions': [
        {'id': 'collect', 'text': 'COLLECT', 'evidence': 'Collect', 'groups': [
            {'id': 'time', 'kind': 'group', 'role': 'specification', 'text': 'Time', 'evidence': 'recent',
             'children': [{'id': 'recent', 'kind': 'atom', 'match': 'semantic', 'text': 'recent messages', 'evidence': 'recent messages'}]}]},
        {'id': 'summarize', 'text': 'SUMMARIZE', 'evidence': 'Summarize', 'groups': []}],
        'global_context': [], 'dependencies': [{'from': 'collect', 'to': 'summarize', 'required_atoms': ['recent'],
        'evidence': 'Summarize them', 'reason': 'Needs collected messages'}], 'review_reasons': []}
    verdict = {'gates': {k: {'value': 1, 'evidence': q, 'reason': 'Retained'} for k, q in [('collect', 'Collect'), ('summarize', 'Summarize')]},
               'atoms': {'recent': {'value': 1, 'evidence': 'messages', 'reason': 'Retained'}}, 'review_reasons': []}
    return tree, verdict


class RuntimeStub:
    def __init__(self, output, forward, adjudication=None):
        self.output = Path(output)
        self.forward, self.adjudication = forward, adjudication
        self.calls = []

    def call(self, stage, model, prompt, data, validate):
        self.calls.append((stage, deepcopy(data)))
        value = self.forward if stage == 'forward' else self.adjudication
        if isinstance(value, Exception):
            raise value
        if value is None:
            raise AssertionError(f'Unexpected stage {stage}')
        value = deepcopy(value)
        validate(value)
        return value, stage + '-call'


class AdjudicationTests(unittest.TestCase):
    def setUp(self):
        self.tree, self.verdict = fixtures()
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)

    def evaluator(self, patch=None):
        rt = RuntimeStub(self.folder.name, self.verdict, patch)
        ev = Evaluator(rt, {k: 'test-model' for k in ['decompose', 'audit', 'forward', 'reverse']})
        return ev, rt

    def uncertain(self):
        self.verdict['atoms']['recent'] = {'value': None, 'evidence': None, 'reason': 'Unresolved omission'}

    def patch(self, value=.5):
        row = {'value': value, 'evidence': None, 'reason': 'Vague reference qualifier omitted'}
        if value == .5:
            row['loss_type'] = 'vague_qualifier_omitted'
        return {'gates': {}, 'atoms': {'recent': row}, 'issues': {}}

    def test_half_is_local_even_on_required_dependency_atom(self):
        self.verdict['atoms']['recent'] = self.patch()['atoms']['recent']
        validate_forward(self.tree, self.verdict, CANDIDATE)
        result = score(self.tree, {**self.verdict, 'candidate_actions': {}})
        self.assertEqual(result['effective_action_scores'], {'collect': .5, 'summarize': 1})
        self.assertEqual(result['retention'], .75)
        self.assertEqual(result['propagation']['summarize'], [])

    def test_half_without_specific_loss_type_is_rejected(self):
        self.verdict['atoms']['recent']['value'] = .5
        with self.assertRaises(InvalidEvaluation):
            validate_forward(self.tree, self.verdict, CANDIDATE)

    def test_gate_cannot_be_half(self):
        self.verdict['gates']['collect'].update(value=.5, loss_type='vague_qualifier_omitted')
        with self.assertRaises(InvalidEvaluation):
            validate_forward(self.tree, self.verdict, CANDIDATE)

    def test_other_fraction_cannot_be_smuggled_in(self):
        self.verdict['atoms']['recent'].update(value=.25, loss_type='vague_qualifier_omitted')
        with self.assertRaises(InvalidEvaluation):
            validate_forward(self.tree, self.verdict, CANDIDATE)

    def test_known_judgments_never_trigger_adjudication(self):
        ev, rt = self.evaluator()
        result = ev.check_forward(TEXT, CANDIDATE, self.tree)
        self.assertEqual([s for s, _ in rt.calls], ['forward'])
        self.assertEqual(result['score']['status'], 'scored')

    def test_only_unknown_atom_is_patched_and_original_is_immutable(self):
        self.uncertain()
        before = deepcopy(self.verdict)
        ev, rt = self.evaluator(self.patch())
        result = ev.check_forward(TEXT, CANDIDATE, self.tree)
        self.assertEqual([s for s, _ in rt.calls], ['forward', 'adjudicate_forward'])
        self.assertEqual(rt.calls[1][1]['candidate_text'], CANDIDATE)
        self.assertEqual(result['score']['retention'], .75)
        self.assertEqual(result['judgment']['gates'], before['gates'])
        self.assertEqual(result['initial_judgment'], before)
        self.assertEqual(self.verdict, before)

    def test_known_gate_cannot_be_overwritten(self):
        self.uncertain()
        patch = self.patch()
        patch['gates']['collect'] = {'value': 0, 'evidence': None, 'reason': 'Tamper'}
        with self.assertRaises(InvalidEvaluation):
            apply_adjudication(self.tree, self.verdict, pending_items(self.tree, self.verdict), patch, TEXT, CANDIDATE)

    def test_adjudicator_cannot_assign_aggregate(self):
        self.uncertain()
        patch = self.patch();patch['retention'] = 1
        with self.assertRaises(InvalidEvaluation):
            apply_adjudication(self.tree, self.verdict, pending_items(self.tree, self.verdict), patch, TEXT, CANDIDATE)

    def test_unresolved_after_single_adjudication_is_failure(self):
        self.uncertain()
        ev, rt = self.evaluator(self.patch(None))
        result = ev.check_forward(TEXT, CANDIDATE, self.tree)
        self.assertEqual(len(rt.calls), 2)
        self.assertEqual(result['score']['status'], 'failed')
        self.assertEqual(result['score']['failure_kind'], 'semantic_unresolved_after_adjudication')
        self.assertIsNone(result['score']['retention'])

    def test_adjudication_transport_failure_is_explicit(self):
        self.uncertain()
        ev, rt = self.evaluator(ModelCallFailure('bounded transport failure'))
        result = ev.check_forward(TEXT, CANDIDATE, self.tree)
        self.assertEqual(result['score']['failure_kind'], 'adjudication_request_failed')
        self.assertEqual(len(rt.calls), 2)

    def test_preserved_reference_ambiguity_becomes_note_not_new_score(self):
        self.tree['review_reasons'] = ['Recent is undefined']
        patch = {'gates': {}, 'atoms': {}, 'issues': {'reference_0': {'status': 'nonblocking',
                 'reason': 'Assess stated requirement, not operational completeness',
                 'reference_evidence': 'recent messages', 'candidate_evidence': 'messages'}}}
        ev, rt = self.evaluator(patch)
        result = ev.check_forward(TEXT, CANDIDATE, self.tree)
        self.assertEqual(result['judgment']['atoms'], self.verdict['atoms'])
        self.assertEqual(result['score']['status'], 'scored')
        self.assertEqual(len(self.tree['review_reasons']), 1)
        self.assertTrue(result['scoring_tree']['diagnostic_notes'])

    def test_uncertain_issue_cannot_silently_be_cleared(self):
        self.tree['review_reasons'] = ['Cannot express required alternatives']
        patch = {'gates': {}, 'atoms': {}, 'issues': {'reference_0': {'status': 'unresolved',
                 'reason': 'Requires structural repair', 'reference_evidence': None, 'candidate_evidence': None}}}
        ev, _ = self.evaluator(patch)
        self.assertEqual(ev.check_forward(TEXT, CANDIDATE, self.tree)['score']['status'], 'failed')

    def test_gate_zero_skipped_atom_does_not_trigger_adjudication(self):
        self.verdict['gates']['collect']['value'] = 0
        self.verdict['atoms']['recent'] = {'value': None, 'evidence': None, 'reason': 'gate failed', 'skipped': True}
        ev, rt = self.evaluator()
        self.assertEqual(ev.check_forward(TEXT, CANDIDATE, self.tree)['score']['retention'], 0)
        self.assertEqual(len(rt.calls), 1)

    def test_forward_only_entry_and_report_do_not_call_reverse(self):
        self.uncertain()
        ev, rt = self.evaluator(self.patch())
        ev.tree = lambda text, audited: (self.tree, ['existing-tree'])
        pair = Pair('test', 'task', 'example', TEXT, CANDIDATE, 'reference', 'candidate')
        result = ev.evaluate(pair, forward_only=True)
        self.assertEqual(result['score']['retention'], .75)
        self.assertNotIn('human_review_status', result)
        make_report(rt.output, [result], 1)
        self.assertTrue((rt.output / 'report.md').exists())
        ev.evaluate(pair, forward_only=True)
        self.assertEqual(len(rt.calls), 2, 'Successful result must be reused, not readjudicated')


if __name__ == '__main__':
    unittest.main()
