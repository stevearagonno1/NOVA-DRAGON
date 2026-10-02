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

    def test_model_wait_exceeds_gateway_retry_window(self):
        env = {'LITELLM_BASE_URL':'http://127.0.0.1:10000/v1', 'LITELLM_API_KEY':'synthetic-key'}
        with patch.dict(council.os.environ, env), patch.object(council, 'post_json', return_value={'choices':[{'message':{'content':'result'}}]}) as post:
            self.assertEqual(council.model_call('rules','task'), 'result')
        self.assertEqual(post.call_args.kwargs['timeout'], 360)

    def test_phase_progress_covers_all_five_requests(self):
        updates = []
        council.run_review('task', '', SOURCES, call=lambda *args:'findings', progress=lambda phase,count:updates.append((phase,count)))
        self.assertEqual(updates[0], ('independent_review',0))
        self.assertEqual(updates[-3:], [('cross_review',3),('synthesis',4),('completed',5)])

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

    def test_dynamic_definitions_scoped_and_standalone_unchanged(self):
        plain=tomllib.loads(boot.readonly_tools_text())
        full=tomllib.loads(boot.readonly_tools_text(True))
        self.assertEqual(len(plain['tools']),4)
        self.assertEqual(len(full['tools']),6)
        for tool in full['tools'][4:]:
            self.assertFalse(tool['requires_approval'])
            self.assertNotIn('{{',tool['command'])

if __name__=='__main__':
    unittest.main()
