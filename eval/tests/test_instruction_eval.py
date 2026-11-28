"""Behavioral checks for the agreed measurement rules, not model self-reports."""
from copy import deepcopy
import unittest

from src.utils.instruction_eval.scoring import InvalidEvaluation, score, validate_judgment, validate_tree

SOURCE = 'Download paper A to P. Then summarize these papers as JSON. Send a greeting after downloading. Existing files must be kept.'


def atom(key, text, mode='semantic'):
    return {'id': key, 'kind': 'atom', 'text': text, 'match': mode, 'evidence': 'paper A'}


def group(key, children):
    return {'id': key, 'kind': 'group', 'role': 'specification', 'text': key,
            'evidence': 'paper A', 'children': children}


def tree():
    return {'actions': [
        {'id': 'fetch', 'text': 'DOWNLOAD', 'evidence': 'Download',
         'groups': [group('target', [atom('paper', 'paper A')]), group('dest', [atom('path', 'P', 'literal')])]},
        {'id': 'summary', 'text': 'SUMMARIZE', 'evidence': 'summarize',
         'groups': [group('format', [atom('json', 'JSON')])]},
        {'id': 'greet', 'text': 'SEND GREETING', 'evidence': 'Send a greeting',
         'groups': [group('order', [atom('after', 'after downloading', 'ordering')])]},
    ], 'global_context': [], 'dependencies': [
        {'from': 'fetch', 'to': 'summary', 'required_atoms': ['paper'],
         'evidence': 'Then summarize these papers', 'reason': 'Summary needs fetched paper identity'}
    ], 'review_reasons': []}


def judgment():
    def row():
        return {'value': 1, 'evidence': 'paper A', 'reason': 'Retained'}
    return {'gates': {key: row() for key in ('fetch', 'summary', 'greet')},
            'atoms': {key: row() for key in ('paper', 'path', 'json', 'after')},
            'candidate_actions': {key: {'classification': 'supported', 'reference_action_ids': [key],
                'candidate_evidence': 'paper A', 'reference_evidence': 'paper A', 'reason': 'Same action'}
                for key in ('fetch', 'summary', 'greet')}, 'review_reasons': []}


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.tree, self.judgment = tree(), judgment()

    def changed(self, key, value=0):
        self.judgment['atoms'][key]['value'] = value

    def result(self):
        return score(self.tree, self.judgment)

    def test_identical_is_one(self):
        validate_tree(self.tree, SOURCE)
        validate_judgment(self.tree, self.tree, self.judgment, SOURCE, SOURCE)
        self.assertEqual(self.result()['final_score'], 1)

    def test_wrong_target_propagates_but_parallel_action_survives(self):
        self.changed('paper')
        result = self.result()
        self.assertEqual(result['effective_action_scores'], {'fetch': .5, 'summary': 0, 'greet': 1})
        self.assertAlmostEqual(result['retention'], .5)

    def test_unreferenced_path_does_not_destroy_summary(self):
        self.changed('path')
        self.assertEqual(self.result()['effective_action_scores']['summary'], 1)

    def test_explicit_read_path_does_destroy_summary(self):
        self.tree['dependencies'][0]['required_atoms'].append('path')
        self.changed('path')
        self.assertEqual(self.result()['effective_action_scores']['summary'], 0)

    def test_final_output_format_does_not_propagate_backward(self):
        self.changed('json')
        self.assertEqual(self.result()['effective_action_scores']['fetch'], 1)

    def test_order_atom_penalty_not_a_gate(self):
        self.tree['actions'][2]['groups'].append(group('recipient', [atom('person', 'recipient')]))
        self.judgment['atoms']['person'] = {'value': 1, 'evidence': 'paper A', 'reason': 'retained'}
        self.changed('after')
        self.assertEqual(self.result()['effective_action_scores']['greet'], .5)

    def test_gate_zero_skips_descendants(self):
        self.judgment['gates']['fetch']['value'] = 0
        del self.judgment['atoms']['paper']
        del self.judgment['atoms']['path']
        validate_judgment(self.tree, self.tree, self.judgment, SOURCE, SOURCE)
        self.assertEqual(self.result()['effective_action_scores']['summary'], 0)

    def test_action_without_groups_equals_gate(self):
        self.tree['actions'][2]['groups'] = []
        del self.judgment['atoms']['after']
        self.assertEqual(self.result()['local_action_scores']['greet'], 1)

    def test_recursive_macro_not_flat_leaves(self):
        self.tree['actions'][0]['groups'][0]['children'] = [group('nested', [atom('paper', 'paper')]),
                                                                  atom('source', 'source')]
        self.judgment['atoms']['source'] = {'value': 1, 'evidence': 'paper A', 'reason': 'retained'}
        self.changed('paper')
        self.assertEqual(self.result()['local_action_scores']['fetch'], .75)

    def test_global_context_counts_once(self):
        self.tree['global_context'] = [group('ctx1', [atom('ctx', 'context')]),
                                       group('ctx2', [atom('ctxb', 'context2')])]
        for key in ('ctx', 'ctxb'):
            self.judgment['atoms'][key] = {'value': 0, 'evidence': None, 'reason': 'missing'}
        self.assertEqual(self.result()['retention'], .75)

    def test_harmful_replacement_has_forward_and_reverse_penalty(self):
        self.judgment['gates']['fetch']['value'] = 0
        self.judgment['candidate_actions']['fetch']['classification'] = 'harmful_extra'
        result = self.result()
        self.assertAlmostEqual(result['retention'], 1 / 3)
        self.assertEqual(result['final_score'], 0)
        self.assertEqual(result['harmful_extra_count'], 1)

    def test_benign_extra_no_penalty(self):
        self.judgment['candidate_actions']['extra'] = {'classification': 'benign_extra'}
        self.assertEqual(self.result()['final_score'], 1)

    def test_unknown_is_not_zero(self):
        self.changed('paper', None)
        self.assertEqual(self.result()['status'], 'needs_review')
        self.assertIsNone(self.result()['final_score'])

    def test_uncertain_extra_blocks_final_score(self):
        self.judgment['candidate_actions']['fetch']['classification'] = 'uncertain'
        self.assertIsNone(self.result()['final_score'])

    def test_propagation_is_transitive(self):
        self.tree['dependencies'].append({'from': 'summary', 'to': 'greet', 'required_atoms': [],
                                         'evidence': 'paper A', 'reason': 'test dependent result'})
        self.changed('paper')
        self.assertEqual(self.result()['effective_action_scores']['greet'], 0)

    def test_cycle_rejected(self):
        self.tree['dependencies'].append({'from': 'summary', 'to': 'fetch', 'required_atoms': [],
                                         'evidence': 'paper A', 'reason': 'cycle'})
        with self.assertRaisesRegex(InvalidEvaluation, 'cycle'):
            validate_tree(self.tree, SOURCE)

    def test_dangling_dependency_rejected(self):
        self.tree['dependencies'][0]['required_atoms'] = ['nope']
        with self.assertRaises(InvalidEvaluation):
            validate_tree(self.tree, SOURCE)

    def test_fabricated_evidence_rejected(self):
        self.judgment['atoms']['paper']['evidence'] = 'not in the candidate'
        with self.assertRaises(InvalidEvaluation):
            validate_judgment(self.tree, self.tree, self.judgment, SOURCE, SOURCE)

    def test_missing_active_verdict_rejected(self):
        del self.judgment['atoms']['paper']
        with self.assertRaises(InvalidEvaluation):
            validate_judgment(self.tree, self.tree, self.judgment, SOURCE, SOURCE)

    def test_fractional_leaf_rejected(self):
        self.changed('paper', .5)
        with self.assertRaises(InvalidEvaluation):
            validate_judgment(self.tree, self.tree, self.judgment, SOURCE, SOURCE)

    def test_duplicate_node_rejected(self):
        self.tree['actions'][1]['groups'][0]['children'].append(atom('paper', 'duplicate'))
        with self.assertRaises(InvalidEvaluation):
            validate_tree(self.tree, SOURCE)

    def test_harmful_extra_requires_context_evidence(self):
        self.judgment['candidate_actions']['fetch']['classification'] = 'harmful_extra'
        self.judgment['candidate_actions']['fetch']['reference_evidence'] = None
        with self.assertRaises(InvalidEvaluation):
            validate_judgment(self.tree, self.tree, self.judgment, SOURCE, SOURCE)


if __name__ == '__main__':
    unittest.main()

class AggregateImportTests(unittest.TestCase):
    def test_duplicate_condition_names_keep_distinct_source_rows(self):
        import tempfile
        from pathlib import Path
        from src.utils.instruction_eval.osworld import read_aggregate_scores
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'scores.csv'
            path.write_text('Agent: Test,1,2,3,4,5,Average,Std Dev\n'
                            'Whisper,50%,50%,50%,50%,50%,50%,0%\n'
                            'Whisper,60%,60%,60%,60%,60%,60%,0%\n')
            result = read_aggregate_scores(path)
            self.assertEqual(result['condition_rows'], 2)
            self.assertEqual([row['source_row'] for row in result['entries']], [2, 3])
            self.assertEqual(result['duplicate_labels'][0]['count'], 2)
            self.assertFalse(result['has_task_ids'])
            self.assertTrue(all(row['take_mapping'] is None for row in result['entries']))

    def test_reported_mean_is_reconciled_not_trusted(self):
        import tempfile
        from pathlib import Path
        from src.utils.instruction_eval.osworld import read_aggregate_scores
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'scores.csv'
            path.write_text('Agent: Test,1,2,3,4,5,Average,Std Dev\n'
                            'Text,50%,50%,50%,50%,50%,99%,0%\n')
            result = read_aggregate_scores(path)
            self.assertFalse(result['entries'][0]['average_reconciles'])

class TokenBudgetTests(unittest.TestCase):
    def test_single_oversized_request_is_rejected(self):
        from src.utils.instruction_eval.runtime import ModelCallFailure, TokenBudget
        with self.assertRaises(ModelCallFailure):
            TokenBudget(10).reserve(11)

    def test_concurrent_budget_waits_for_previous_minute_to_expire(self):
        from unittest.mock import patch
        from src.utils.instruction_eval.runtime import TokenBudget
        clock = [0.0]
        def sleep(seconds):
            clock[0] += seconds
        with patch('src.utils.instruction_eval.runtime.time.monotonic', side_effect=lambda: clock[0]), \
             patch('src.utils.instruction_eval.runtime.time.sleep', side_effect=sleep):
            budget = TokenBudget(10)
            budget.reserve(6)
            budget.reserve(6)
            self.assertEqual(clock[0], 60.0)
            self.assertEqual(sum(n for _, n in budget.entries), 6)

class SplitCheckerTests(unittest.TestCase):
    def run_evaluator(self, failure=None):
        import tempfile
        from pathlib import Path
        from eval.evaluate_instructions import Evaluator
        from src.utils.instruction_eval.corpus import Pair
        from src.utils.instruction_eval.runtime import ModelCallFailure
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        class Runtime:
            output = Path(folder.name)
            requests = []
            def call(self, stage, model, prompt, data, validate):
                self.requests.append((stage, deepcopy(data)))
                if stage == failure:
                    raise ModelCallFailure('Simulated checker failure')
                full = judgment()
                if stage in ('decompose', 'audit'):
                    value = tree()
                elif stage == 'forward':
                    value = {k: full[k] for k in ('gates', 'atoms', 'review_reasons')}
                else:
                    value = {k: full[k] for k in ('candidate_actions', 'review_reasons')}
                validate(value)
                return value, f'{stage}-call'
        runtime = Runtime()
        evaluator = Evaluator(runtime, dict.fromkeys(('decompose','audit','forward','reverse'), 'test'))
        pair = Pair('test', 'task', 'condition', SOURCE, SOURCE, '/ref', '/candidate')
        return evaluator.evaluate(pair), runtime.requests

    def test_checker_inputs_are_isolated(self):
        result, requests = self.run_evaluator()
        forward = next(data for stage, data in requests if stage == 'forward')
        reverse = next(data for stage, data in requests if stage == 'reverse')
        self.assertEqual(set(forward), {'reference_text','candidate_text','reference_tree'})
        self.assertEqual(set(reverse), {'reference_text','candidate_text','reference_tree','candidate_tree'})
        self.assertEqual(result['score']['final_score'], 1)
        self.assertIn('forward', result['calls'])
        self.assertIn('reverse', result['calls'])
        self.assertNotIn('check', result['calls'])

    def test_reverse_failure_does_not_erase_forward(self):
        result, _ = self.run_evaluator('reverse')
        self.assertEqual(result['score']['status'], 'failed')
        self.assertEqual(result['forward_score']['retention'], 1)
        self.assertIn('forward_judgment', result)

    def test_forward_failure_does_not_prevent_reverse(self):
        result, requests = self.run_evaluator('forward')
        self.assertEqual(result['score']['status'], 'failed')
        self.assertIn('reverse_judgment', result)
        self.assertIn('reverse', [stage for stage, _ in requests])
