import io
import json
import unittest
from urllib.error import HTTPError
from unittest.mock import patch
import agent_council_transport as transport

class StreamTests(unittest.TestCase):
    def setUp(self):
        transport.cooldowns.clear()

    def event(self, delta=None, finish=None):
        return ('data: '+json.dumps({'choices':[{'delta':delta or {},'finish_reason':finish}]})+'\n\n').encode()

    def test_stream_collects_final_text_without_private_reasoning(self):
        data=self.event({'reasoning_content':'private internal text'})+self.event({'content':'Hello '})+self.event({'content':'world'},'stop')+b'data: [DONE]\n\n'
        self.assertEqual(transport.collect_sse(io.BytesIO(data)),'Hello world')
        tagged=self.event({'content':'<think>internal text</think>final answer'},'stop')+b'data: [DONE]\n'
        self.assertEqual(transport.collect_sse(io.BytesIO(tagged)), 'final answer')

    def test_partial_stream_is_not_reported_as_finished(self):
        with self.assertRaises(transport.StreamIncomplete):
            transport.collect_sse(io.BytesIO(self.event({'content':'unfinished'})))

    def test_stream_idle_timeout_is_distinct_from_start_timeout(self):
        class Response:
            def __init__(self, first=None): self.first=first
            def readline(self,*args):
                if self.first is not None:
                    value=self.first; self.first=None; return value
                raise TimeoutError()
        with self.assertRaises(transport.StreamStartTimeout):
            transport.collect_sse(Response())
        with self.assertRaises(transport.StreamIdleTimeout):
            transport.collect_sse(Response(self.event({'reasoning_content':'hidden'})))

    def test_request_uses_stream_and_known_model_only(self):
        class Response(io.BytesIO):
            headers={'Content-Type':'text/event-stream'}
        class Opener:
            def open(self,req,timeout):
                self.req=req; self.timeout=timeout
                return Response(b'data: {"choices":[{"delta":{"content":"ok"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n')
        opener=Opener()
        out=transport.stream({'base':'https://api.atria-asi.ai/v1','model':'Atria-Dawn-Preview','key':'synthetic'},'rules','task',opener)
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

if __name__=='__main__': unittest.main()
