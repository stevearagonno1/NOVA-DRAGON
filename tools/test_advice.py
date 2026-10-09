import json
import unittest
from agent_advice import consult_once
SOURCES=[{'path':'README.md','commit':'fixed','blob_sha':'blob','content':'evidence'}]
class AdviceTests(unittest.TestCase):
    def run_advice(self,advisor):
        calls=[]
        def call(system,user,slot,deadline):
            calls.append(slot)
            if slot:return advisor()
            payload=json.loads(user)
            return json.dumps(payload)
        result,counts=consult_once('question','','proposal',SOURCES,call,'rules')
        self.assertEqual(calls,[1,0]);self.assertEqual(counts['subagents'],1)
        return json.loads(result),counts
    def test_addition_is_retained_once(self):
        payload,counts=self.run_advice(lambda:'verified objection')
        self.assertEqual(payload['advisor_additions'][0]['findings'],'verified objection')
        self.assertEqual(counts['model_requests'],2)
    def test_silence_is_not_approval(self):
        payload,counts=self.run_advice(lambda:'NO_ADDITION')
        self.assertEqual(payload['silent_advisors'],[1]);self.assertEqual(payload['advisor_additions'],[])
        self.assertEqual(counts['silent_advisors'],1)
    def test_failed_advisor_lead_finishes_with_limitation(self):
        def fail():raise TimeoutError('private text')
        payload,counts=self.run_advice(fail)
        self.assertTrue(counts['partial']);self.assertEqual(counts['completed_subagents'],0)
        self.assertEqual(len(payload['unavailable_advisors']),1)
        self.assertNotIn('private text',json.dumps(counts))
    def test_missing_proposal_prevents_calls(self):
        calls=[]
        with self.assertRaises(ValueError):consult_once('q','','',[],lambda *a:calls.append(a),'rules')
        self.assertEqual(calls,[])
