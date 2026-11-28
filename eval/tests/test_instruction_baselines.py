import unittest
from pathlib import Path
from src.utils.instruction_eval.baselines import (chunks,edit_rate,lexical_scores,majority,LLMBaselines,validate_values)
from src.utils.instruction_eval.scoring import InvalidEvaluation

class BaselineTests(unittest.TestCase):
    def test_identity_and_insertion(self):
        self.assertEqual(edit_rate(['a'],['a']),0)
        self.assertEqual(edit_rate(['a'],['a','b','c']),2)
    def test_chinese_not_one_word(self):
        s=lexical_scores('删除文件','保留文件')
        self.assertEqual(s['lexical_unit'],'character')
        self.assertEqual(s['lexical_error'],.5)
    def test_lexical_does_not_fix_meaning(self):
        self.assertGreater(lexical_scores('do not delete','do delete')['lexical_error'],0)
    def test_full_token_coverage(self):
        ids=list(range(1001));parts=chunks(ids,126)
        self.assertEqual(sum(parts,[]),ids)
        self.assertTrue(all(len(p)<=126 for p in parts))
    def test_majority_per_atom(self):
        def v(a,b):return {'judgments':[{'id':'r1','preserved':a},{'id':'r2','preserved':b}]}
        r=majority([v(True,False),v(False,True),v(True,False)],['r1','r2'])
        self.assertEqual(r['atomic_score'],.5)
        self.assertEqual(r['disagreement_count'],2)
    def test_no_missing_votes(self):
        with self.assertRaises(InvalidEvaluation):majority([],['r1'])
    def test_duplicate_ids(self):
        with self.assertRaises(InvalidEvaluation):validate_values({'answers':[{'id':'q1','answer':'a'},{'id':'q1','answer':'a'}]},'answers','answer',['q1','q2'],False)
    def test_null_explicit_but_missing_field_invalid(self):
        validate_values({'answers':[{'id':'q1','answer':None}]},'answers','answer',['q1'],False)
        with self.assertRaises(InvalidEvaluation):validate_values({'answers':[{'id':'q1'}]},'answers','answer',['q1'],False)
    def test_three_votes_have_distinct_cache_inputs(self):
        class Fake:
            def __init__(self):self.inputs=[]
            def call(self,stage,model,prompt,data,validate):
                self.inputs.append(data)
                out={'judgments':[{'id':'r1','preserved':True}]}
                validate(out);return out,'id'
        f=Fake();llm=LLMBaselines(f,'test',Path('eval/prompts/instruction_baselines'))
        result=llm.atomic('reference','candidate',[{'id':'r1','requirement':'Keep a file'}])
        self.assertEqual([d['independent_repeat'] for d in f.inputs],[1,2,3])
        self.assertEqual(result['atomic_score'],1)

    def test_candidate_qa_cannot_receive_reference_answer(self):
        class Fake:
            def call(self,stage,model,prompt,data,validate):
                self.data=data
                out={'answers':[{'id':'q1','answer':None}]};validate(out);return out,'id'
        f=Fake();llm=LLMBaselines(f,'test',Path('eval/prompts/instruction_baselines'))
        llm.answer('candidate only',[{'id':'q1','question':'Which file?'}])
        self.assertEqual(set(f.data),{'context','questions'})
        self.assertEqual(f.data['context'],'candidate only')

if __name__=='__main__':unittest.main()
