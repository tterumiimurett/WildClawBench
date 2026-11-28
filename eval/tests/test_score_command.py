"""Run the public scoring command with fixed judgments at the network seam."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.utils.instruction_eval.runtime import ModelCallFailure


class ScoreCommandTests(unittest.TestCase):
    def test_two_pairs_keep_ids_scores_and_failure_reason(self):
        from eval.score import main

        def judge(stage, model, prompt, data, validate):
            self.assertEqual(model, 'example/judge')
            if stage in ('decompose', 'audit'):
                if data['instruction'] == 'Unavailable':
                    raise ModelCallFailure('Judge unavailable')
                value = {'actions': [{'id': 'a', 'text': 'Save', 'evidence': 'Save', 'groups': []}],
                         'dependencies': [], 'global_context': [], 'review_reasons': []}
            elif stage == 'forward':
                value = {'gates': {'a': {'value': 1, 'evidence': 'Save', 'reason': 'Same action'}},
                         'atoms': {}, 'review_reasons': []}
            else:
                value = {'candidate_actions': {'a': {'classification': 'supported',
                         'candidate_evidence': 'Save', 'reference_evidence': 'Save',
                         'reference_action_ids': ['a'], 'reason': 'Same action'}}, 'review_reasons': []}
            validate(value)
            return value, stage

        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'pairs.jsonl'
            source.write_text('\n'.join(json.dumps({'id': i, 'reference': text, 'candidate': text})
                                         for i, text in [('valid', 'Save'), ('failed', 'Unavailable')]))
            output = Path(folder) / 'output'
            printed = io.StringIO()
            with patch('eval.score.ModelRuntime') as runtime, redirect_stdout(printed):
                runtime.return_value.output = output
                runtime.return_value.call.side_effect = judge
                code = main([str(source), '--model', 'example/judge', '--output', str(output)])
            rows = [json.loads(line) for line in printed.getvalue().splitlines()]
            self.assertEqual(code, 1)
            self.assertEqual(rows[0], {'id': 'valid', 'status': 'scored', 'retention': 1, 'final_score': 1})
            self.assertEqual(rows[1], {'id': 'failed', 'status': 'failed', 'retention': None,
                                       'final_score': None, 'reason': 'Judge unavailable'})

    def test_public_judge_connects_to_openrouter(self):
        from importlib.util import find_spec
        from src.utils.instruction_eval.runtime import ModelRuntime
        if not find_spec('openai') or not find_spec('dotenv'):
            self.skipTest('Install the judge dependencies to check the client configuration')
        with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test-only'}, clear=True):
            runtime = ModelRuntime(Path(folder), Path(folder))
            self.assertEqual(str(runtime.client.base_url).rstrip('/'), 'https://openrouter.ai/api/v1')
            self.assertEqual(runtime.client.api_key, 'test-only')
            runtime.client.close()
