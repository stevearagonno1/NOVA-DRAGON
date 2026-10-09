import io
import json
import socket
import tempfile
import threading
import tomllib
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from unittest.mock import patch
import agent_failover as relay
import agent_bootstrap as boot
from agent_router import build_router_config

class Response(io.BytesIO):
    headers = {'Content-Type':'application/json'}
class Opener:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes); self.requests=[]
    def open(self, req, timeout):
        self.requests.append(json.loads(req.data))
        result = next(self.outcomes)
        if isinstance(result, Exception): raise result
        return result

def error(code):
    return HTTPError('http://local',code,'private-error-secret',{},io.BytesIO(b'private'))

class FailoverTests(unittest.TestCase):
    def test_only_technical_codes_trigger_backup(self):
        for code in (401,402,403,408,429,500,502,503,504):
            opener=Opener([error(code),Response(b'{}')])
            response,slot=relay.open_response({'messages':[]},'http://local','key','lead',opener)
            self.assertEqual(slot,7)
            self.assertEqual([r['model'] for r in opener.requests],['lead',relay.RESERVE_ALIAS])
            response.close()
        for code in (400,404,413,422):
            opener=Opener([error(code)])
            with self.assertRaises(relay.RelayError) as exc:
                relay.open_response({'messages':[]},'http://local','key','lead',opener)
            self.assertEqual(exc.exception.status,code)
            self.assertNotIn('private',str(exc.exception))
            self.assertEqual(len(opener.requests),1)

    def test_healthy_primary_no_extra_call_and_no_caller_fallback_chain(self):
        opener=Opener([Response(b'{}')])
        result,slot=relay.open_response({'messages':[],'fallbacks':['unknown'],
            'num_retries':20,'disable_fallbacks':False,'max_fallbacks':30},'http://local','key','lead',opener)
        self.assertEqual(slot,4);self.assertEqual(len(opener.requests),1)
        self.assertNotIn('fallbacks',opener.requests[0])
        self.assertTrue(opener.requests[0]['disable_fallbacks'])
        self.assertEqual(opener.requests[0]['num_retries'],0)
        result.close()

    def test_two_failed_connections_stop_no_third_slot(self):
        opener=Opener([URLError('secret'),socket.timeout('secret')])
        with self.assertRaises(relay.RelayError):
            relay.open_response({'messages':[]},'http://local','key','lead',opener)
        self.assertEqual(len(opener.requests),2)

    def test_installed_context_with_output_reserve_and_inactivity_controls(self):
        cfg=tomllib.loads(boot.config_text('1','http://127.0.0.1:1/v1','lead',8080))
        provider=cfg['providers']['custom']['nova']
        self.assertEqual(provider['context_window'],240000)
        self.assertLess(cfg['agent']['context_limit']+cfg['agent']['max_tokens'],256000)
        self.assertTrue(cfg['agent']['silent_compaction'])
        self.assertEqual(provider['stream_idle_timeout_secs'],300)
        self.assertNotIn('timeout_secs',provider)  # No total streaming wall-clock cap.

    def test_aliases_only_selected_reserve_and_source_immutable(self):
        source={'model_list':[{'model_name':'opencrabs-model','litellm_params':
            {'model':'openai/test','api_key':'key'+str(i)}} for i in range(10)],
            'litellm_settings':{'fallbacks':[{'opencrabs-model':['other']} ]}}
        cfg=build_router_config(source,{},lead_slot=4,reserve_slot=7)
        reserve=[x for x in cfg['model_list'] if x['model_name']==relay.RESERVE_ALIAS]
        self.assertEqual(len(reserve),1)
        self.assertEqual(reserve[0]['litellm_params']['api_key'],'key6')
        self.assertEqual(cfg['router_settings']['max_fallbacks'],0)
        self.assertEqual(cfg['router_settings']['retry_policy']['DefaultRetries'],0)
        self.assertNotIn('fallbacks',cfg['litellm_settings'])
        self.assertIn('fallbacks',source['litellm_settings'])
        self.assertTrue(all(x['model_name']=='opencrabs-model' for x in source['model_list']))

    def test_metrics_never_keep_conversation_or_mix_requests(self):
        with tempfile.TemporaryDirectory() as d,patch.object(relay,'STATUS_PATH',Path(d)/'status.json'),patch('builtins.print'):
            relay.update_status(phase='request',request_id='a',request_bytes=123,messages='SECRET')
            relay.update_status(phase='complete',request_id='a',prompt_tokens=90000)
            relay.update_status(phase='request',request_id='b',request_bytes=40)
            relay.update_status(phase='complete',request_id='a',prompt_tokens=90001)
            data=json.loads(relay.STATUS_PATH.read_text())
            self.assertNotIn('prompt_tokens',data)
            self.assertNotIn('SECRET',relay.STATUS_PATH.read_text())
            self.assertEqual(data['request_id'],'b')
            self.assertEqual(relay.STATUS_PATH.stat().st_mode & 0o777,0o600)

    def test_local_http_stream_preserved_and_interrupted_stream_never_replayed(self):
        for complete in (True,False):
            calls=[];events=[]
            class Upstream(BaseHTTPRequestHandler):
                def log_message(self,*args): pass
                def do_POST(self):
                    body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    calls.append(body['model'])
                    if len(calls)==1:
                        self.send_response(503);self.end_headers();return
                    self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                    self.wfile.write(b'data: {"choices":[{"delta":{"content":"ok"}}]}\n\n')
                    if complete:
                        self.wfile.write(b'data: {"choices":[],"usage":{"prompt_tokens":123,"completion_tokens":4,"total_tokens":127}}\n\ndata: [DONE]\n\n')
            gateway=ThreadingHTTPServer(('127.0.0.1',0),Upstream)
            front=ThreadingHTTPServer(('127.0.0.1',0),relay.RelayHandler)
            front.api_key='test-key';front.gateway=f'http://127.0.0.1:{gateway.server_port}/v1'
            front.primary='lead';front.capacity=threading.BoundedSemaphore(2)
            threads=[threading.Thread(target=s.serve_forever,daemon=True) for s in (gateway,front)]
            for t in threads:t.start()
            try:
                with patch.object(relay,'update_status',side_effect=lambda **x:events.append(x)):
                    model_req=Request(f'http://127.0.0.1:{front.server_port}/v1/models',
                                      headers={'Authorization':'Bearer test-key'})
                    with urlopen(model_req,timeout=5) as response:
                        self.assertEqual(json.load(response)['data'][0]['id'],'lead')
                    self.assertEqual(calls,[])  # Listing models is local; no upstream inference.
                    req=Request(f'http://127.0.0.1:{front.server_port}/v1/chat/completions',
                        data=b'{"messages":[],"stream":true}',headers={'Authorization':'Bearer test-key'})
                    with urlopen(req,timeout=5) as response:
                        raw=response.read();self.assertEqual(response.headers['X-NOVA-Credential-Slot'],'7')
                    self.assertIn(b'"content":"ok"',raw)
                    self.assertEqual(calls,['lead',relay.RESERVE_ALIAS])
                    self.assertEqual(events[-1]['phase'],'complete' if complete else 'stream_interrupted')
            finally:
                for s in (gateway,front):s.shutdown();s.server_close()
                for t in threads:t.join(timeout=2)

if __name__=='__main__':unittest.main()
