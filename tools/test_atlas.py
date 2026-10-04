import json
import io
import tempfile
import unittest
from unittest.mock import patch
import agent_atlas as atlas
import agent_council as council

POOL=[{'model':'Atria-Dawn-Preview','key':'test-private-'+str(i),'base':'https://api.atria-asi.ai/v1'} for i in range(10)]

class AtlasTests(unittest.TestCase):
    def test_default_pilot_is_only_slot_four_original_full_exam(self):
        calls=[]
        def request(route,system,prompt,**kwargs):
            calls.append(route)
            self.assertEqual(prompt,atlas.EXAM.read_text())
            self.assertEqual(kwargs['max_tokens'],65536)
            self.assertEqual(kwargs['max_stream_bytes'],16*1024*1024)
            return '{}'
        record=atlas.benchmark(POOL,requester=request)
        self.assertEqual(calls,[POOL[3]])
        self.assertEqual(record['requested_slots'],1)
        self.assertEqual(record['parallelism'],1)
        self.assertEqual(record['scheduled_slot_order'],[4])

    def test_actual_stream_length_preserves_only_visible_partial_and_usage(self):
        events=[{'choices':[{'delta':{'reasoning_content':'private reasoning'}}]},
                {'choices':[{'delta':{'content':'{"partial":'}}]},
                {'choices':[{'delta':{},'finish_reason':'length'}],
                 'usage':{'completion_tokens':65536,'completion_tokens_details':{'reasoning_tokens':65000}}}]
        data=b''.join(b'data: '+json.dumps(x).encode()+b'\n\n' for x in events)+b'data: [DONE]\n'
        class Response(io.BytesIO):
            headers={'Content-Type':'text/event-stream'}
        class Opener:
            def open(self,request,**kwargs):
                body=json.loads(request.data)
                self.outer.assertEqual(body['max_tokens'],65536)
                self.outer.assertNotIn('reasoning_effort',body)
                return Response(data)
        opener=Opener();opener.outer=self
        with patch.object(atlas,'build_opener',return_value=opener):
            record=atlas.benchmark(POOL)
        item=record['results'][0]
        self.assertEqual(item['reason_code'],'output_limit_reached')
        self.assertEqual(item['outcome'],'failed')
        self.assertIsNone(item['answer'])
        self.assertEqual(item['partial_answer'],'{"partial":')
        self.assertEqual(item['reasoning_tokens'],65000)
        self.assertIsNotNone(item['first_answer_seconds'])
        self.assertNotIn('private reasoning',json.dumps(record))

    def test_pilot_job_counts_and_invalid_scope(self):
        record={'results':[{'attempted':True,'outcome':'completed','answer':'{}'}]}
        with tempfile.TemporaryDirectory() as d,patch.object(atlas,'benchmark',return_value=record) as run:
            jobs=council.Jobs(d,sender=lambda _:None)
            with self.assertRaises(ValueError):jobs.submit({'scope':'unknown'},kind='atlas')
            q=jobs.submit({},kind='atlas');jobs.pool.shutdown(wait=True)
            status=jobs.status({'id':q['id']})[0]
        self.assertEqual(run.call_args.kwargs['scope'],'pilot')
        self.assertEqual(status['expected_requests'],1)
        self.assertEqual(status['completed_requests'],1)
        self.assertEqual(status['atlas_scope'],'pilot')
        self.assertFalse(status['counts']['partial'])

    def test_exactly_ten_calls_no_tools_or_grader_and_all_answers_saved(self):
        calls=[];saved=[]
        def request(route,system,prompt,**kwargs):
            calls.append(route['key'])
            self.assertIn('250',prompt)
            self.assertIn('spatial_shift',prompt)
            self.assertNotIn('REF=',prompt)
            self.assertNotIn('[[-10,9],[-3,6],[-6,13]]',prompt)
            self.assertIn('no tools',system)
            self.assertEqual(kwargs['max_tokens'],65536)
            kwargs['opener'].metadata['reported_model']='provider-model-label'
            return '{"candidate":"raw answer"}'
        record=atlas.benchmark(POOL,requester=request,checkpoint=saved.append,scope="all")
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
        record=atlas.benchmark(POOL,requester=request,scope="all")
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
            q=jobs.submit({'scope':'all','task':'ignore user settings','paths':['README.md']},kind='atlas')
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
