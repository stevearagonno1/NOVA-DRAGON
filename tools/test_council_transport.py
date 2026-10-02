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

    def test_empty_and_reasoning_only_answers_have_distinct_safe_reasons(self):
        samples=[(self.event({},'stop'),'empty_final_answer'),
                 (self.event({'reasoning_content':'private-secret'},'stop'),'reasoning_without_final_answer'),
                 (self.event({'content':'partial'},'length'),'output_limit_reached'),
                 (self.event({},'content_filter'),'response_filtered'),
                 (self.event({'refusal':'private refusal'},'stop'),'response_refused')]
        for data,code in samples:
            with self.assertRaises(transport.FinalAnswerError) as caught:
                transport.collect_sse(io.BytesIO(data+b'data: [DONE]\n'))
            self.assertEqual(transport.safe_reason(caught.exception)['code'],code)
            self.assertNotIn('private',str(transport.safe_reason(caught.exception)))

    def test_content_parts_are_supported_without_reasoning_parts(self):
        data=self.event({'content':[{'type':'reasoning','text':'hidden'}, {'type':'text','text':'answer'}]},'stop')
        self.assertEqual(transport.collect_sse(io.BytesIO(data+b'data: [DONE]\n')),'answer')

    def test_empty_response_rotates_to_reserve_with_existing_attempt_bound(self):
        pool=[{'key':str(i)} for i in range(10)]; selected=[]
        def request(route,*args):
            selected.append(route)
            if len(selected)==1: raise transport.FinalAnswerError('empty_final_answer')
            return 'answer'
        self.assertEqual(transport.model_call('s','u',0,pool,request),'answer')
        self.assertEqual(selected,[pool[0],pool[5]])
        transport.cooldowns.clear(); selected.clear()
        def always_empty(route,*args):
            selected.append(route); raise transport.FinalAnswerError('reasoning_without_final_answer')
        with self.assertRaises(transport.FinalAnswerError) as caught:
            transport.model_call('s','u',0,pool,always_empty)
        self.assertEqual(len(selected),3)
        self.assertEqual(transport.safe_reason(caught.exception)['slot'],7)

    def test_refusal_filter_and_length_never_rotate(self):
        pool=[{'key':str(i)} for i in range(10)]
        for code in ['response_refused','response_filtered','output_limit_reached']:
            selected=[]
            def request(route,*args):
                selected.append(route); raise transport.FinalAnswerError(code)
            with self.assertRaises(transport.FinalAnswerError):
                transport.model_call('s','u',0,pool,request)
            self.assertEqual(len(selected),1)

    def test_json_stream_fallback_has_same_output_validation(self):
        class Response(io.BytesIO): headers={'Content-Type':'application/json'}
        class Opener:
            def open(self,*args,**kwargs):
                return Response(json.dumps({'choices':[{'finish_reason':'length','message':{'content':'partial'}}]}).encode())
        with self.assertRaises(transport.FinalAnswerError) as caught:
            transport.stream({'base':'https://api.atria-asi.ai/v1','model':'Atria-Dawn-Preview','key':'synthetic'},'s','u',Opener())
        self.assertEqual(caught.exception.code,'output_limit_reached')

    def test_connection_probe_has_small_output_and_no_failover(self):
        pool=[{'key':'synthetic-first'},{'key':'synthetic-reserve'}]
        with patch.object(transport,'routes',return_value=pool), patch.object(transport,'stream',return_value='READY') as call:
            result=transport.probe_connection()
        call.assert_called_once()
        self.assertEqual(call.call_args.args[0],pool[0])
        self.assertEqual(call.call_args.kwargs['max_tokens'],512)
        self.assertEqual(result['api_requests'],1)

if __name__=='__main__': unittest.main()
