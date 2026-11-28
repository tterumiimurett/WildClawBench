import unittest
from src.utils.instruction_eval.evidence import catalog, prepare, resolve
from src.utils.instruction_eval.scoring import InvalidEvaluation


class EvidenceTests(unittest.TestCase):
    def test_lossless_and_unsplit_url(self):
        source = '  下载 ' + 'https://example.org/' + 'x' * 300 + '\n\n结束'
        rows = catalog(source, 'C', 30)
        self.assertEqual(''.join(r['text'] for r in rows), source)
        self.assertTrue(any('https://example.org/' + 'x' * 300 in r['text'] for r in rows))
        for row in rows:
            self.assertEqual(source[row['start']:row['end']], row['text'])

    def test_range_and_null(self):
        data = prepare({'candidate_text': 'word ' * 150, 'reference_text': 'reference'})
        result = resolve({'evidence': 'C0001:C0002', 'other': {'evidence': None}}, data)
        self.assertEqual(result['evidence'], data['candidate_text'][:data['evidence_catalog']['C'][1]['end']])
        self.assertIsNone(result['other']['evidence'])

    def test_wrong_source_and_unknown_id(self):
        data = prepare({'candidate_text': 'candidate', 'reference_text': 'reference'})
        for evidence in ['R0001', 'C9999', 'invented quotation']:
            with self.assertRaises(InvalidEvaluation):
                resolve({'evidence': evidence}, data)

    def test_unicode_and_no_whitespace(self):
        source = '下载论文然后保存。' * 100
        self.assertEqual(catalog(source, 'I')[0]['text'], source)
        self.assertEqual(resolve({'evidence': 'I0001'}, prepare({'instruction': source}))['evidence'], source)


class RequestBudgetTests(unittest.TestCase):
    def test_qpm_blocks_even_with_tokens_available(self):
        from unittest.mock import patch
        from src.utils.instruction_eval.runtime import TokenBudget
        clock = [0.0]
        def sleep(seconds):
            clock[0] += seconds
        with patch('src.utils.instruction_eval.runtime.time.monotonic', side_effect=lambda: clock[0]), patch('src.utils.instruction_eval.runtime.time.sleep', side_effect=sleep):
            budget = TokenBudget(1_000_000, qpm=2)
            budget.reserve(1)
            budget.reserve(1)
            budget.reserve(1)
            self.assertEqual(clock[0], 60.0)
            self.assertEqual(len(budget.entries), 1)


class PersistentAttemptTests(unittest.TestCase):
    def test_exhausted_call_does_not_restart_on_resume(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch, Mock
        from src.utils.instruction_eval.runtime import ModelRuntime, ModelCallFailure
        with tempfile.TemporaryDirectory() as tmp:
            runtime = ModelRuntime.__new__(ModelRuntime)
            runtime.output = Path(tmp)
            runtime.backend_hash = 'test'
            runtime.max_tokens = 100
            runtime.retries = 3
            runtime.wait = Mock(side_effect=AssertionError('No request should start'))
            (runtime.output/'failures').mkdir()
            (runtime.output/'failures'/'key-3.json').write_text(json.dumps({'error':{'attempt':3,'stage':'audit','type':'InvalidEvaluation'},'raw_output':'{}'}))
            with patch('src.utils.instruction_eval.runtime.digest', return_value='key'):
                with self.assertRaises(ModelCallFailure):
                    runtime.call('audit','test','test',{'instruction':'test'},lambda obj:None)
                runtime.wait.assert_not_called()
                (runtime.output/'calls').mkdir()
                (runtime.output/'calls'/'key.json').write_text(json.dumps({'result':{'valid':True}}))
                self.assertEqual(runtime.call('audit','test','test',{'instruction':'test'},lambda obj:None)[0],{'valid':True})
