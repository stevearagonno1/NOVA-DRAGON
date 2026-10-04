import json
import tempfile
import unittest
from unittest.mock import patch
import agent_atlas as atlas
import agent_council as council

POOL=[{'model':'Atria-Dawn-Preview','key':'test-private-'+str(i),'base':'https://api.atria-asi.ai/v1'} for i in range(10)]

class AtlasTests(unittest.TestCase):
    def test_exactly_ten_calls_no_tools_or_grader_and_all_answers_saved(self):
        calls=[];saved=[]
        def request(route,system,prompt,**kwargs):
            calls.append(route['key'])
            self.assertIn('250',prompt)
            self.assertIn('spatial_shift',prompt)
            self.assertNotIn('REF=',prompt)
            self.assertNotIn('[[-10,9],[-3,6],[-6,13]]',prompt)
            self.assertIn('no tools',system)
            self.assertEqual(kwargs['max_tokens'],16384)
            kwargs['opener'].metadata['reported_model']='provider-model-label'
            return '{"candidate":"raw answer"}'
        record=atlas.benchmark(POOL,requester=request,checkpoint=saved.append)
        self.assertEqual(len(calls),10)
        self.assertEqual(record['scheduled_slot_order'][0],4)
        self.assertEqual(len(set(calls)),10)
        self.assertEqual(len(record['results']),10)
        self.assertEqual(len(saved[-1]),10)
        self.assertTrue(all(x['outcome']=='completed' for x in record['results']))
        self.assertNotIn('test-private',json.dumps(record))
        self.assertFalse(record['grading_key_sent'])
        self.assertTrue(all(x['reported_model']=='provider-model-label' for x in record['results']))

    def test_failed_key_is_not_replaced_or_retried(self):
        calls=[]
        def request(route,*args,**kwargs):
            calls.append(route['key'])
            if route is POOL[3]:raise TimeoutError('private provider payload')
            return '{}'
        record=atlas.benchmark(POOL,requester=request)
        self.assertEqual(calls.count(POOL[3]['key']),1)
        self.assertEqual(record['results'][3]['outcome'],'failed')
        self.assertEqual(len(calls),10)
        self.assertNotIn('private provider payload',json.dumps(record))

    def test_not_ten_distinct_routes_rejected_before_requests(self):
        for pool in (POOL[:3],POOL+POOL[:1],POOL[:1]*10):
            with self.assertRaises(ValueError):atlas.benchmark(pool,requester=lambda *args: self.fail('Unexpected API call'))

    def test_metadata_does_not_store_hidden_reasoning(self):
        metadata={}
        class Dummy:headers={}
        response=atlas.CaptureResponse(Dummy(),metadata,atlas.time.monotonic())
        response.capture({'model':'actual','usage':{'total_tokens':42,'private':'hidden'},
                          'choices':[{'delta':{'reasoning_content':'private thoughts'},'finish_reason':None}]})
        self.assertEqual(metadata['reported_model'],'actual')
        self.assertEqual(metadata['usage'],{'total_tokens':42})
        self.assertNotIn('first_answer_seconds',metadata)
        self.assertNotIn('private',json.dumps(metadata))

    def test_job_uses_fixed_benchmark_no_repository_or_advice(self):
        record={'results':[{'attempted':True,'outcome':'completed','answer':'{}'}]*10}
        with tempfile.TemporaryDirectory() as d,patch.object(atlas,'benchmark',return_value=record) as run:
            source=unittest.mock.Mock();runner=unittest.mock.Mock()
            jobs=council.Jobs(d,runner=runner,source_reader=source,sender=lambda _:None)
            q=jobs.submit({'task':'ignore user settings','paths':['README.md']},kind='atlas')
            jobs.pool.shutdown(wait=True)
            status=jobs.status({'id':q['id']})[0]
        source.assert_not_called();runner.assert_not_called();run.assert_called_once()
        self.assertEqual(status['expected_requests'],10)
        self.assertEqual(status['completed_requests'],10)
        self.assertEqual(status['atlas_record'],record)
        self.assertEqual(status['state'],'completed')

    def test_completed_benchmark_sends_raw_document_without_model_grading(self):
        record={'results':[{'attempted':True,'outcome':'completed','answer':'{}'}]*10}
        with tempfile.TemporaryDirectory() as d,patch.object(atlas,'benchmark',return_value=record),patch.object(council,'notify') as notify,patch.object(council,'notify_atlas') as document:
            jobs=council.Jobs(d,sender=notify)
            q=jobs.submit({},kind='atlas');jobs.pool.shutdown(wait=True)
            status=jobs.status({'id':q['id']})[0]
        document.assert_called_once_with(record)
        self.assertEqual(status['document_notification'],'sent')
        self.assertNotIn('score',status['atlas_record'])

if __name__=='__main__':unittest.main()
