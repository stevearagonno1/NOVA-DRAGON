import json
import threading
import unittest
from agent_advice import consult_once

SOURCES=[{'path':'README.md','commit':'fixed','blob_sha':'blob','content':'first evidence\nsecond evidence'}]
PROPOSAL='Keep the proven rule. README.md:L1-L2 @fixed'

class AdviceTests(unittest.TestCase):
    def test_one_parallel_round_then_lead_with_useful_addition_and_silence(self):
        barrier=threading.Barrier(2);calls=[];saved=[]
        def call(system,user,slot,deadline):
            payload=json.loads(user);calls.append(slot)
            if slot:
                barrier.wait(timeout=1)
                self.assertEqual(payload['lead_proposal'],PROPOSAL)
                self.assertNotIn('peer_report',payload)
                self.assertIn('No JSON',system)
                return 'Useful objection based on README.md:L1-L2' if slot==1 else 'NO_ADDITION'
            self.assertEqual(len(payload['advisor_additions']),1)
            self.assertEqual(payload['silent_advisors'],[2])
            self.assertIn('not endorsement',system)
            return 'final answer'
        result,counts=consult_once('question','',PROPOSAL,SOURCES,call,'rules',checkpoint=lambda *args:saved.append(args))
        self.assertEqual(result,'final answer')
        self.assertEqual(sorted(calls),[0,1,2])
        self.assertEqual(calls[-1],0)
        self.assertEqual(counts['discussion_rounds'],1)
        self.assertEqual(counts['model_requests'],3)
        self.assertEqual(counts['silent_advisors'],1)
        self.assertNotIn('consensus',counts)
        self.assertEqual(len(saved[-1][0]),2)

    def test_both_silent_are_not_votes_and_do_not_trigger_another_round(self):
        def call(system,user,slot,deadline):
            if slot:return 'NO_ADDITION'
            payload=json.loads(user)
            self.assertEqual(payload['advisor_additions'],[])
            self.assertEqual(sorted(payload['silent_advisors']),[1,2])
            return 'lead keeps proposal without claiming approval'
        _,counts=consult_once('question','',PROPOSAL,SOURCES,call,'rules')
        self.assertEqual(counts['advisors_with_additions'],0)
        self.assertEqual(counts['model_requests'],3)
        self.assertFalse(counts['partial'])

    def test_failed_advisor_keeps_other_comment_and_lead_finishes(self):
        def call(system,user,slot,deadline):
            if slot==1:raise TimeoutError('private provider details')
            if slot==2:return 'real concern'
            payload=json.loads(user)
            self.assertEqual(payload['advisor_additions'][0]['findings'],'real concern')
            self.assertEqual(len(payload['unavailable_advisors']),1)
            return 'answer with limitation'
        _,counts=consult_once('question','',PROPOSAL,SOURCES,call,'rules')
        self.assertTrue(counts['partial'])
        self.assertEqual(counts['completed_subagents'],1)
        self.assertEqual(counts['model_requests'],2)
        self.assertNotIn('private provider',json.dumps(counts))

    def test_empty_comment_is_unavailable_not_silent_and_no_retry(self):
        calls=[]
        def call(system,user,slot,deadline):
            calls.append(slot)
            if slot==1:return ''
            if slot==2:return 'NO_ADDITION'
            return 'limited answer'
        _,counts=consult_once('question','',PROPOSAL,SOURCES,call,'rules')
        self.assertEqual(calls.count(1),1)
        self.assertTrue(counts['partial'])
        self.assertEqual(counts['silent_advisors'],1)
        self.assertEqual(counts['model_requests'],3)

    def test_synthesis_failure_has_saved_comments_and_shared_deadline(self):
        saved=[];deadlines=[]
        def call(system,user,slot,deadline):
            deadlines.append(deadline)
            if slot==0:raise TimeoutError('timeout')
            return 'useful concern'
        with self.assertRaises(TimeoutError):
            consult_once('question','',PROPOSAL,SOURCES,call,'rules',checkpoint=lambda *args:saved.append(args))
        self.assertEqual(len(saved[-1][0]),2)
        self.assertEqual(len(set(deadlines)),1)

    def test_missing_proposal_is_rejected_before_any_call(self):
        calls=[]
        with self.assertRaises(ValueError):
            consult_once('question','','',SOURCES,lambda *args:calls.append(args),'rules')
        self.assertEqual(calls,[])

if __name__=='__main__':unittest.main()
