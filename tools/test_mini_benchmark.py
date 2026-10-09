import json
import unittest
import tempfile
import agent_council as council
from unittest.mock import patch
import agent_mini_benchmark as mini
import agent_atlas as atlas

POOL=[{'key':'fake-key-'+str(i),'model':'same-model','base':'https://example.invalid'} for i in range(10)]
class MiniTests(unittest.TestCase):
    def test_independent_arithmetic_and_grade(self):
        # Flat round-trip loses 0.26% approximately; rise case independently rounded.
        self.assertEqual(mini.expected()['net_micro_usd'],[-51984,1944817])
        self.assertEqual(mini.grade(json.dumps(mini.expected()))['score'],100)
        bad=mini.expected();bad['net_micro_usd'][0]=True
        self.assertIsNone(mini.grade(json.dumps(bad))['score'])
        self.assertFalse(mini.grade('{"bugs":[],"bugs":[]}')['format_valid'])
    def test_budget_routes_and_no_grading_key(self):
        calls=[]
        def request(route,system,prompt,**kw):
            calls.append(route);self.assertEqual(kw['max_tokens'],8192)
            self.assertNotIn('1944817',prompt);return json.dumps(mini.expected())
        r=mini.benchmark(POOL,requester=request)
        self.assertEqual(calls,[POOL[3],POOL[4],POOL[6]])
        self.assertEqual(r['ranking'],[x['credential_slot'] for x in sorted(r['results'],key=lambda x:x['elapsed_seconds'])])
        self.assertEqual(r['maximum_generation_tokens'],24576)
    def test_failure_is_not_retried_or_ranked(self):
        calls=[]
        def request(route,*args,**kw):
            calls.append(route)
            if route is POOL[4]:raise TimeoutError()
            return '{}'
        r=mini.benchmark(POOL,requester=request)
        self.assertEqual(len(calls),3);self.assertEqual(r['ranking'],[])
        self.assertIsNone(r['results'][1]['grading']['score'])
    def test_background_mini_counts_and_summary(self):
        record=mini.benchmark(POOL,requester=lambda *a,**kw:json.dumps(mini.expected()))
        with tempfile.TemporaryDirectory() as d, patch.object(atlas,'benchmark',return_value=record):
            jobs=council.Jobs(d,sender=lambda _:None)
            q=jobs.submit({'scope':'mini'},kind='atlas')
            jobs.pool.shutdown(wait=True)
            status=jobs.status({'id':q['id']})[0]
        self.assertEqual(status['expected_requests'],3)
        self.assertEqual(status['state'],'completed')
        self.assertIn('100/100',status['result'])
        self.assertEqual(status['atlas_record']['test'],'MINI-WORK-1')

    def test_atlas_mini_dispatch(self):
        with patch.object(mini,'benchmark',return_value={'test':'MINI-WORK-1'}) as run:
            self.assertEqual(atlas.benchmark(POOL,scope='mini')['test'],'MINI-WORK-1')
            self.assertEqual(run.call_args.kwargs['pool'],POOL)
if __name__=='__main__':unittest.main()
