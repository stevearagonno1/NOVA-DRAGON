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
    def test_bounded_three_reviewers_cross_review_and_synthesis(self):
        calls = []
        def fake(system, user):
            calls.append((system,user))
            return 'تقرير مدعوم بالمصدر'
        result, counts = council.run_review('Task paper', 'source facts', SOURCES, fake)
        self.assertEqual(len(calls), 5)
        self.assertEqual(counts['reviewers'], 3)
        self.assertIn('reviewer_findings', calls[3][1])
        self.assertIn('Cross-review:', calls[4][1])
        self.assertIn('No trades', calls[0][0])
        self.assertEqual(result, 'تقرير مدعوم بالمصدر')

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
            j…1796 tokens truncated…=transport.stream({'base':'https://api.atria-asi.ai/v1','model':'Atria-Dawn-Preview','key':'synthetic'},'rules','task',opener)
        body=json.loads(opener.req.data)
        self.assertTrue(body['stream'])
        self.assertEqual(body['max_tokens'],6144)
        self.assertEqual(out,'ok')

    def test_distinct_role_preferences_with_reserve_failover(self):
        pool=[{'key':'synthetic-'+str(i)} for i in range(10)]
        selected=[]
        def request(route,*args): selected.append(route['key']); return 'done'
        for slot in range(5):
            transport.model_call('rules','task',slot,pool,request)
        self.assertEqual(selected,[r['key'] for r in pool[:5]])
        selected=[]
        def failure(route,*args):
            selected.append(route['key'])
            if route is pool[0]:
                raise HTTPError('fixed',429,'quota',{'Retry-After':'120'},None)
            return 'done'
        self.assertEqual(transport.model_call('rules','task',0,pool,failure,clock=lambda:100),'done')
        self.assertEqual(selected,[pool[0]['key'],pool[5]['key']])
        self.assertGreaterEqual(transport.cooldowns[0],220)

    def test_attempts_bounded_and_nonretryable_errors_not_rotated(self):
        pool=[{'key':str(i)} for i in range(10)]; calls=[]
        def request(route,*args):
            calls.append(route); raise transport.StreamStartTimeout()
        with self.assertRaises(transport.StreamStartTimeout):
            transport.model_call('rules','task',0,pool,request)
        self.assertEqual(len(calls),3)
        transport.cooldowns.clear(); calls=[]
        def bad(route,*args):
            calls.append(route); raise HTTPError('fixed',400,'invalid',{},None)
        with self.assertRaises(HTTPError):
            transport.model_call('rules','task',0,pool,bad)
        self.assertEqual(len(calls),1)

    def test_route_file_only_uses_existing_validated_endpoint_and_unique_keys(self):
        def entry(key): return {'model_name':'opencrabs-model','litellm_params':{'model':'openai/Atria-Dawn-Preview','api_base':'https://api.atria-asi.ai/v1','api_key':key}}
        env={'TOKEN_1':'synthetic-one','TOKEN_2':'synthetic-two'}
        routes=transport.configured_routes({'model_list':[entry('os.environ/TOKEN_1'),entry('os.environ/TOKEN_2'),entry('synthetic-one')]},env)
        self.assertEqual(len(routes),2)
        bad=entry('synthetic'); bad['litellm_params']['api_base']='https://other.test/v1'
        with self.assertRaises(ValueError):
            transport.configured_routes({'model_list':[bad]},env)

    def test_diagnostics_reports_count_without_keys_or_api_calls(self):
        with patch.object(transport,'routes',return_value=[{'key':'private-'+str(i)} for i in range(10)]), patch.object(transport,'stream') as request:
            result=transport.diagnostics()
        self.assertEqual(result['unique_credentials'],10)
        self.assertEqual(result['api_requests_made'],0)
        self.assertFalse(result['provider_acceptance_verified'])
        self.assertNotIn('private',json.dumps(result))
        request.assert_not_called()

    def test_configuration_errors_report_slot_without_secret_value(self):
        entry={'model_name':'opencrabs-model','litellm_params':{'model':'openai/Atria-Dawn-Preview','api_base':'https://api.atria-asi.ai/v1','api_key':'private\ninvalid'}}
        with self.assertRaises(transport.TransportConfigurationError) as caught:
            transport.configured_routes({'model_list':[entry]}, {})
        reason=transport.safe_reason(caught.exception)
        self.assertEqual(reason,{'code':'credential_invalid_format','slot':1})
        with patch.object(transport,'routes',side_effect=caught.exception):
            result=transport.diagnostics()
        self.assertFalse(result['configuration_valid'])
        self.assertNotIn('private',json.dumps(result))

    def test_unexpected_error_message_cannot_disclose_header_token(self):
        reason=transport.safe_reason(ValueError('Invalid header containing private-secret'))
        self.assertEqual(reason['code'],'ValueError')
        self.assertNotIn('private-secret',json.dumps(reason))

    def test_connection_probe_has_small_output_and_no_failover(self):
        pool=[{'key':'synthetic-first'},{'key':'synthetic-reserve'}]
        with patch.object(transport,'routes',return_value=pool), patch.object(transport,'stream',return_value='READY') as call:
            result=transport.probe_connection()
        call.assert_called_once()
        self.assertEqual(call.call_args.args[0],pool[0])
        self.assertEqual(call.call_args.kwargs['max_tokens'],512)
        self.assertEqual(result['api_requests'],1)

if __name__=='__main__': unittest.main()
