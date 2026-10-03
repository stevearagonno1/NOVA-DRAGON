import json
import threading
import unittest
from agent_leaders import Workspace,coordinate_leaders,MAX_REQUESTS

SOURCES=[{'path':'README.md','commit':'fixed','blob_sha':'blob','content':'first evidence\nsecond fact\nthird detail'}]
def finish(decision='approve',blockers=None):
    return json.dumps({'action':'finish','summary':'finding README.md:L1-L2 @fixed',
                       'decision':decision,'blockers':blockers or [],'needs_consultation':False})

class LeaderTests(unittest.TestCase):
    def test_each_leader_uses_tools_and_shared_board_without_unneeded_consultation(self):
        barrier=threading.Barrier(2);calls=[];saved=[]
        def call(system,user,slot,deadline):
            payload=json.loads(user);calls.append((slot,payload))
            if slot==0:return 'final answer'
            if payload['step']==1:
                barrier.wait(timeout=1)
                return json.dumps({'action':'read','path':'README.md','start':1,'end':2})
            self.assertEqual(payload['recent_tool_results'][0]['result']['commit'],'fixed')
            self.assertIn('README.md:L1-L2',payload['workspace']['evidence'])
            return finish()
        result,counts=coordinate_leaders('task','',SOURCES,call,'rules',checkpoint=lambda *args:saved.append(args),require_tool=True)
        self.assertEqual(counts['model_requests'],5)
        self.assertEqual(counts['tool_steps'],2)
        self.assertEqual(counts['discussion_rounds'],0)
        self.assertFalse(counts['unresolved_disagreement'])
        self.assertEqual(len(saved[-1][0]),2)
        self.assertIn('README.md:L1-L2',saved[-1][2]['evidence'])

    def test_decision_conflict_triggers_one_targeted_consultation(self):
        calls=[]
        def call(system,user,slot,deadline):
            payload=json.loads(user);calls.append(payload)
            if slot==0:return 'final'
            if 'peer_report' in payload:
                self.assertNotEqual(payload['own_report']['decision'],payload['peer_report']['decision'])
                self.assertEqual(payload['evidence']['source_excerpts'][0]['commit'],'fixed')
                return finish('approve')
            return finish('approve' if slot==1 else 'reject')
        _,counts=coordinate_leaders('task','',SOURCES,call,'rules')
        self.assertEqual(counts['model_requests'],5)
        self.assertEqual(counts['discussion_rounds'],1)
        self.assertFalse(counts['unresolved_disagreement'])

    def test_persistent_dissent_stops_at_two_rounds_without_forcing_agreement(self):
        def call(system,user,slot,deadline):
            payload=json.loads(user)
            if slot==0:
                self.assertTrue(payload['unresolved_disagreement']);return 'dissent remains'
            return finish('approve' if slot==1 else 'reject',['source gap'] if slot==2 else [])
        result,counts=coordinate_leaders('task','',SOURCES,call,'rules')
        self.assertEqual(counts['discussion_rounds'],2)
        self.assertEqual(counts['model_requests'],7)
        self.assertIn('لا يُدّعى اتفاق نهائي',result)

    def test_consultation_failure_keeps_prior_findings(self):
        checkpoints=[]
        def call(system,user,slot,deadline):
            payload=json.loads(user)
            if slot==0:
                self.assertEqual(len(payload['leaders']),2);return 'partial audit'
            if 'peer_report' in payload and slot==2:raise TimeoutError('private provider message')
            return finish('approve' if slot==1 else 'reject')
        _,counts=coordinate_leaders('task','',SOURCES,call,'rules',checkpoint=lambda *args:checkpoints.append(args))
        self.assertTrue(counts['partial'])
        self.assertTrue(counts['unresolved_disagreement'])
        self.assertEqual(len(checkpoints[-1][0]),2)
        self.assertNotIn('private provider',json.dumps(checkpoints))

    def test_read_search_publish_are_scoped_and_literal(self):
        board=Workspace(SOURCES)
        self.assertEqual(board.execute(1,{'action':'search','query':'evidence'})['hits'][0]['line'],1)
        self.assertEqual(board.execute(1,{'action':'search','query':'.*'})['hits'],[])
        board.execute(1,{'action':'publish','note':'question with README.md:L1-L1'})
        self.assertIn('question',board.snapshot()['notes']['1'])
        for action in [{'action':'shell','command':'delete'}, {'action':'read','path':'keys.toml','start':1,'end':1},
                       {'action':'search','query':'test','path':'../README.md'},
                       {'action':'read','path':'README.md','start':True,'end':2},
                       {'action':'read','path':'README.md','start':1,'end':99}]:
            with self.assertRaises(ValueError):board.execute(1,action)

    def test_never_ending_tool_loop_is_bounded_and_cannot_block_successful_peer(self):
        def call(system,user,slot,deadline):
            if slot==0:return 'partial answer'
            if slot==1:return json.dumps({'action':'publish','note':'still checking'})
            return finish()
        _,counts=coordinate_leaders('task','',SOURCES,call,'rules')
        self.assertEqual(counts['completed_subagents'],1)
        self.assertTrue(counts['partial'])
        self.assertEqual(counts['tool_steps'],8)
        self.assertLessEqual(counts['model_requests'],MAX_REQUESTS)

    def test_diagnostic_requires_actual_tool_use(self):
        with self.assertRaises(TimeoutError):
            coordinate_leaders('task','',SOURCES,lambda *args:finish(),'rules',require_tool=True)

if __name__=='__main__':unittest.main()
