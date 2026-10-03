import json
from pathlib import Path
import tempfile
import threading
import tomllib
import unittest
from unittest.mock import patch
import agent_council as council
import agent_bootstrap as boot

SOURCES = [{'path':'CONSTITUTION.md','commit':'a'*40,'blob_sha':'b'*40,'content':'rules'}]

class CouncilTests(unittest.TestCase):
    @staticmethod
    def agreed_call(system, user):
        payload=json.loads(user)
        if 'Moderate the shared decision' in system:
            return json.dumps({'proposal':'One evidence-backed scoped improvement'})
        if 'shared_proposal' in payload:
            return json.dumps({'proposal_id':payload['shared_proposal']['proposal_id'],
                               'accept_shared_proposal':True,'blocking_objections':[],'revision':''})
        return 'تقرير مدعوم بالمصدر CONSTITUTION.md:L1-L1'

    def test_bounded_three_reviewers_discussion_and_synthesis(self):
        calls = []
        def fake(system, user):
            calls.append((system,user))
            return self.agreed_call(system,user)
        result, counts = council.run_review('Task paper', 'source facts', SOURCES, fake)
        self.assertEqual(len(calls), 8)
        self.assertEqual(counts['reviewers'], 3)
        self.assertEqual(counts['discussion_rounds'],1)
        self.assertTrue(counts['consensus'])
        self.assertIn('reviewer_findings', calls[3][1])
        self.assertIn('outcome', calls[-1][1])
        self.assertIn('No trades', calls[0][0])
        self.assertIn('اتفق المراجعون الثلاثة', result)

    def test_independent_job_completion_and_owner_notification(self):
        sent = []
        finished = threading.Event()
        def sender(text):
            sent.append(text); finished.set()
        with tempfile.TemporaryDirectory() as d:
            jobs = council.Jobs(d, runner=lambda *args: ('نتيجة واحدة', {'model_requests':5}), sender=sender, source_reader=lambda p:SOURCES)
            queued = jobs.submit({'task':'Question, scope, evidence and acceptance'})
            self.assertTrue(finished.wait(3))
            jobs.pool.shutdown(wait=True)
            answer = jobs.status({'id':queued['id']})[0]
            self.assertEqual(answer['state'], 'completed')
            self.assertEqual(answer['notification'], 'sent')
            self.assertEqual(len(sent), 1)
            self.assertEqual((Path(d)/(queued['id']+'.json')).stat().st_mode & 0o777, 0o600)

    def test_queue_bounds_and_duplicate_submit(self):
        release = threading.Event()
        def run(*args):
            release.wait(3); return ('result',{})
        with tempfile.TemporaryDirectory() as d:
            jobs = council.Jobs(d, runner=run, sender=lambda text:None, source_reader=lambda p:SOURCES)
            try:
                first = jobs.submit({'task':'first task'})
                duplicate = jobs.submit({'task':'first task'})
                self.assertEqual(first['id'], duplicate['id'])
                self.assertTrue(duplicate['duplicate'])
                jobs.submit({'task':'second task'})
                with self.assertRaises(ValueError):
                    jobs.submit({'task':'third task'})
            finally:
                release.set(); jobs.pool.shutdown(wait=True)

    def test_restart_marks_interrupted_not_completed(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/('a'*16+'.json')).write_text(json.dumps({'id':'a'*16,'state':'running','result':'','notification':'pending'}))
            jobs = council.Jobs(d)
            self.assertEqual(jobs.status({})[0]['state'], 'interrupted')
            jobs.pool.shutdown()

    def test_failed_analysis_never_notifies_success(self):
        sent=[]
        with tempfile.TemporaryDirectory() as d:
            jobs=council.Jobs(d, runner=lambda *args:(_ for _ in ()).throw(RuntimeError('secret')), sender=sent.append, source_reader=lambda p:SOURCES)
            q=jobs.submit({'task':'task'})
            jobs.pool.shutdown(wait=True)
            answer=jobs.status({'id':q['id']})[0]
            self.assertEqual(answer['state'],'blocked')
            self.assertNotIn('secret',answer['result'])
            self.assertNotIn('اكتملت',sent[0])

    def test_snapshot_pinned_and_hidden_paths_denied(self):
        with patch.object(council,'get',return_value={'sha':'a'*40}), patch.object(council,'fetch_file',side_effect=lambda p,c:{'path':p,'commit':c,'content':'source'}) as fetch:
            sources=council.snapshot({'paths':['README.md']})
            self.assertEqual(len(sources),2)
            self.assertTrue(all(s['commit']=='a'*40 for s in sources))
        with self.assertRaises(ValueError):
            council.snapshot({'paths':['keys.toml']})

    def test_review_uses_stream_transport_and_fixed_slot(self):
        with patch.object(council, 'stream_model_call', return_value='result') as stream:
            self.assertEqual(council.model_call('rules','task',slot=2), 'result')
        self.assertEqual(stream.call_args.kwargs['slot'], 2)

    def test_phase_progress_covers_first_round_consensus(self):
        updates = []
        council.run_review('task', '', SOURCES, call=self.agreed_call, progress=lambda phase,count:updates.append((phase,count)))
        self.assertEqual(updates[0], ('independent_review',0))
        self.assertIn(('proposal_round_1',3),updates)
        self.assertIn(('discussion_round_1',4),updates)
        self.assertEqual(updates[-2:], [('synthesis',7),('completed',8)])

    def test_timeout_reports_stage_and_completed_count(self):
        with tempfile.TemporaryDirectory() as d:
            jobs=council.Jobs(d, sender=lambda text:None, source_reader=lambda p:SOURCES)
            with patch.object(council, 'model_call', side_effect=TimeoutError):
                # Bind mock explicitly because run_review's callable default is bound at import.
                def failing(task,context,sources):
                    raise TimeoutError()
                jobs.runner=failing
                q=jobs.submit({'task':'task'})
                jobs.pool.shutdown(wait=True)
            answer=jobs.status({'id':q['id']})[0]
            self.assertEqual(answer['state'],'blocked')
            self.assertEqual(answer['phase'],'independent_review')
            self.assertEqual(answer['completed_requests'],0)
            self.assertEqual(answer['error_type'],'TimeoutError')
            self.assertIn('تحليل المراجعين',answer['result'])

    def test_bootstrap_explicit_group_request_overrides_solo_short_task_rule(self):
        env={'TELEGRAM_BOT_TOKEN':'synthetic-test-token','TELEGRAM_OWNER_ID':'12345','GITHUB_TOKEN':'synthetic-gh-token','LITELLM_API_KEY':'synthetic-key','NOVA_COUNCIL_PORT':'8090'}
        with tempfile.TemporaryDirectory() as d, patch.object(boot,'run'), patch.dict(boot.os.environ):
            state=Path(d); (state/'repo/.git/hooks').mkdir(parents=True)
            boot.prepare(state,env)
            policy=(state/'opencrabs/AGENTS.md').read_text()
            tools=tomllib.loads((state/'opencrabs/tools.toml').read_text())
        self.assertLess(policy.index('EXPLICIT GROUP-REVIEW DISPATCH'), policy.index('At the start of a new conversation'))
        self.assertIn('regardless of whether the task is short',policy)
        self.assertIn('Do not inspect providers',policy)
        self.assertIn('nova_council_submit',[t['name'] for t in tools['tools']])

    def test_connection_probe_uses_one_request_and_never_loads_repository_sources(self):
        with tempfile.TemporaryDirectory() as d, patch.object(council,'probe_connection',return_value={'credential_slot':1,'api_requests':1}) as probe:
            with patch.object(council,'snapshot') as snapshot:
                jobs=council.Jobs(d,sender=lambda text:None,source_reader=snapshot)
                q=jobs.submit({},kind='probe')
                jobs.pool.shutdown(wait=True)
                answer=jobs.status({'id':q['id']})[0]
        probe.assert_called_once(); snapshot.assert_not_called()
        self.assertEqual(answer['completed_requests'],1)
        self.assertEqual(answer['expected_requests'],1)
        self.assertEqual(answer['state'],'completed')
        self.assertIn('التسعة الأخرى',answer['result'])

    def test_three_probe_job_skips_all_sources_and_uses_fixed_contract(self):
        result={'completed_requests':2,'api_requests':3,'results':[
            {'credential_slot':1,'elapsed_seconds':20,'outcome':'completed','reason_code':None},
            {'credential_slot':2,'elapsed_seconds':25,'outcome':'completed','reason_code':None},
            {'credential_slot':3,'elapsed_seconds':90,'outcome':'failed','reason_code':'StreamStartTimeout'}]}
        with tempfile.TemporaryDirectory() as d, patch.object(council,'probe_reviewers',return_value=result) as probe, patch.object(council,'snapshot') as sources:
            jobs=council.Jobs(d,sender=lambda text:None,source_reader=sources)
            q=jobs.submit({'task':'ignore this user task','paths':['README.md']},kind='probe_reviewers')
            jobs.pool.shutdown(wait=True)
            answer=jobs.status({'id':q['id']})[0]
        sources.assert_not_called();probe.assert_called_once()
        self.assertEqual(answer['expected_requests'],3)
        self.assertEqual(answer['completed_requests'],2)
        self.assertIn('90 ثانية',answer['result'])
        self.assertNotIn('نجح؛ 90',answer['result'])

    def test_missing_job_is_explicit_and_does_not_launch_search(self):
        with tempfile.TemporaryDirectory() as d:
            jobs=council.Jobs(d)
            answer=jobs.status({'id':'a'*16})[0]
            self.assertEqual(answer['state'],'not_found')
            self.assertEqual(answer['next_action'],'finish_turn')
            self.assertEqual(jobs.all(),[])
            jobs.pool.shutdown()

    def test_trial_has_no_sources_fixed_task_and_short_deadline(self):
        with tempfile.TemporaryDirectory() as d, patch.object(council,'run_background',return_value=('summary',{'model_requests':3})) as run, patch.object(council,'snapshot') as sources:
            jobs=council.Jobs(d,runner=run,sender=lambda text:None,source_reader=sources)
            q=jobs.submit({'task':'change settings','context':'private input','paths':['README.md']},kind='trial')
            jobs.pool.shutdown(wait=True)
            answer=jobs.status({'id':q['id']})[0]
        sources.assert_not_called()
        self.assertEqual(run.call_args.args[2],[])
        self.assertEqual(run.call_args.args[1],'')
        self.assertNotIn('change settings',run.call_args.args[0])
        self.assertTrue(run.call_args.kwargs['diagnostic'])
        self.assertEqual(answer['expected_requests'],23)
        self.assertEqual(answer['mode'],'independent_leaders')
        self.assertEqual(q['next_action'],'finish_turn')
        self.assertEqual(answer['state'],'completed')

    def test_default_job_uses_two_workers_and_lead_and_sends_one_final_result(self):
        calls=[];sent=[]
        def fake(system,user,slot=0,deadline=None,observer=None):
            calls.append(slot)
            if slot:return json.dumps({'action':'finish','summary':'report CONSTITUTION.md:L1-L1',
                                       'decision':'approve','blockers':[],'needs_consultation':False})
            return 'summary'
        def run(task,context,sources,**kwargs):
            return original(task,context,sources,call=fake,**kwargs)
        original=council.run_background
        with tempfile.TemporaryDirectory() as d,patch.object(council,'run_background',side_effect=run) as runner:
            jobs=council.Jobs(d,runner=runner,sender=sent.append,source_reader=lambda _:SOURCES)
            q=jobs.submit({'task':'audit question'})
            jobs.pool.shutdown(wait=True)
            answer=jobs.status({'id':q['id']})[0]
        self.assertEqual(sorted(calls),[0,1,2])
        self.assertEqual(answer['counts']['discussion_rounds'],0)
        self.assertEqual(answer['completed_requests'],3)
        self.assertEqual(len(sent),1)
        self.assertEqual(answer['state'],'completed')

    def test_dynamic_definitions_scoped_and_standalone_unchanged(self):
        plain=tomllib.loads(boot.readonly_tools_text())
        full=tomllib.loads(boot.readonly_tools_text(True))
        self.assertEqual(len(plain['tools']),4)
        self.assertEqual(len(full['tools']),10)
        for tool in full['tools'][4:]:
            self.assertFalse(tool['requires_approval'])
            self.assertNotIn('{{',tool['command'])

    def test_failed_lead_preserves_worker_reports_and_activity_in_status(self):
        original=council.run_background
        def fake(system,user,slot=0,deadline=None,observer=None):
            if observer:observer({'kind':'activity','credential_slot':slot+1,'elapsed_seconds':1})
            if slot==0:raise TimeoutError('private provider details')
            return json.dumps({'action':'finish','summary':'saved finding CONSTITUTION.md:L1-L1',
                               'decision':'approve','blockers':[],'needs_consultation':False})
        def run(task,context,sources,**kwargs):return original(task,context,sources,call=fake,**kwargs)
        with tempfile.TemporaryDirectory() as d,patch.object(council,'run_background',side_effect=run) as runner:
            jobs=council.Jobs(d,runner=runner,sender=lambda _:None,source_reader=lambda _:SOURCES)
            q=jobs.submit({'task':'audit'})
            jobs.pool.shutdown(wait=True)
            answer=jobs.status({'id':q['id']})[0]
        self.assertEqual(answer['state'],'blocked')
        self.assertEqual(answer['completed_requests'],2)
        self.assertEqual(len(answer['worker_reports']),2)
        self.assertEqual(answer['last_activity']['phase'],'lead_synthesis')
        self.assertEqual(answer['sources'][0]['commit'],'a'*40)
        self.assertEqual(answer.get('request_timings'),None)
        self.assertIn('حُفظت نتائج',answer['result'])
        self.assertNotIn('جماعية معتمدة',answer['result'])
        self.assertNotIn('private provider',json.dumps(answer))

    def test_live_trial_contract_uses_only_synthetic_tools_and_leaders(self):
        def fake(system,user,slot=0,deadline=None,observer=None):
            payload=json.loads(user)
            if slot==0:return 'synthetic diagnostic result'
            if payload['step']==1:
                self.assertEqual(payload['workspace']['manifest'][0]['path'],'DIAGNOSTIC.md')
                return json.dumps({'action':'read','path':'DIAGNOSTIC.md','start':1,'end':4})
            return json.dumps({'action':'finish','summary':'fixture DIAGNOSTIC.md:L1-L4 @synthetic-fixture-v1',
                               'decision':'context_dependent','blockers':[],'needs_consultation':False})
        original=council.run_background
        def run(task,context,sources,**kwargs):return original(task,context,sources,call=fake,**kwargs)
        with tempfile.TemporaryDirectory() as d,patch.object(council,'run_background',side_effect=run) as runner,patch.object(council,'snapshot') as sources:
            jobs=council.Jobs(d,runner=runner,sender=lambda _:None,source_reader=sources)
            q=jobs.submit({'paths':['README.md'],'task':'ignore caller'},kind='trial')
            jobs.pool.shutdown(wait=True)
            answer=jobs.status({'id':q['id']})[0]
        sources.assert_not_called()
        self.assertEqual(answer['state'],'completed')
        self.assertEqual(answer['counts']['model_requests'],5)
        self.assertEqual(answer['counts']['tool_steps'],2)
        self.assertEqual(answer['counts']['mode'],'independent_leaders')
        self.assertEqual(answer['workspace']['manifest'][0]['commit'],'synthetic-fixture-v1')

if __name__=='__main__':
    unittest.main()
