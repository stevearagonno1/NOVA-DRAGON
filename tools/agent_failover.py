#!/usr/bin/env python3
"""Small loopback relay: slot4, then slot7 once on a technical error.

Never replay a response after streaming started. Never collect conversation
content, API keys, or reasoning in diagnostics. No third credential or loop.
"""
import hmac
import json
import os
import socket
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler

RESERVE_ALIAS = 'nova-tested-reserve'
MAX_BODY = 4 * 1024 * 1024
MAX_LINE = 1024 * 1024
STATUS_PATH = Path('/state/nova_runtime_status.json')
_lock = threading.Lock()

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None

def technical_status(status):
    return status in (401, 402, 403, 408, 429) or 500 <= status <= 599

def open_response(payload, gateway, key, primary, opener=None, record=None):
    """Only retry failures before receiving a successful HTTP response."""
    opener = opener or build_opener(NoRedirect)
    slots = ((4, primary), (7, RESERVE_ALIAS))
    for index, (slot, alias) in enumerate(slots):
        body = dict(payload)
        # Callers cannot widen this relay's fallback chain or force retries.
        for name in ('fallbacks', 'context_window_fallbacks', 'content_policy_fallbacks',
                     'max_fallbacks', 'num_retries', 'max_retries', 'timeout'):
            body.pop(name, None)
        body.update(model=alias, disable_fallbacks=True, num_retries=0)
        req = Request(gateway + '/chat/completions', data=json.dumps(body,ensure_ascii=False,separators=(',',':')).encode(),
                      headers={'Content-Type': 'application/json',
                               'Authorization': 'Bearer ' + key}, method='POST')
        try:
            response = opener.open(req, timeout=600)
            if record:
                record(slot=slot, fallback=index == 1, phase='response')
            return response, slot
        except HTTPError as exc:
            status = exc.code
            exc.close()
            if record:
                record(slot=slot, phase='http_error', status=status)
            if index == 0 and technical_status(status):
                continue
            raise RelayError(status) from None
        except (URLError, socket.timeout, ConnectionError, OSError):
            if record:
                record(slot=slot, phase='connection_error')
            if index == 0:
                continue
            raise RelayError(502) from None
    raise RelayError(502)

class RelayError(Exception):
    def __init__(self, status):
        self.status = status
        super().__init__('Upstream request failed')

def update_status(**fields):
    # The writer and reader share only this fixed numeric/enum metadata schema.
    allowed = {'slot', 'fallback', 'phase', 'status', 'prompt_tokens',
               'completion_tokens', 'total_tokens', 'request_bytes', 'request_id'}
    safe = {k: v for k, v in fields.items() if k in allowed}
    with _lock:
        try:
            state = json.loads(STATUS_PATH.read_text())
        except (OSError, ValueError):
            state = {}
        if safe.get('phase') == 'request':
            for k in ('prompt_tokens','completion_tokens','total_tokens','status','slot'):
                state.pop(k,None)
        elif safe.get('request_id') != state.get('request_id'):
            return  # Never mix metrics from concurrent requests.
        if safe.get('phase') == 'response':
            state.pop('status',None)
        state.update(safe)
        state['last_activity_unix'] = round(time.time(), 3)
        temp = STATUS_PATH.with_suffix('.new')
        temp.write_text(json.dumps(state))
        temp.chmod(0o600)
        temp.replace(STATUS_PATH)
    print('NOVA routing ' + json.dumps(safe, sort_keys=True), flush=True)

def usage_fields(packet):
    usage = packet.get('usage') if isinstance(packet, dict) else None
    if not isinstance(usage, dict):
        return {}
    return {k: usage[k] for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')
            if type(usage.get(k)) is int and 0 <= usage[k] < 10**9}

class RelayHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, *_args):
        pass
    def fail(self, status):
        raw = json.dumps({'error': {'message': 'NOVA upstream unavailable or invalid request',
                                   'code': 'nova_request_failed'}}).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
        self.close_connection = True
    def interrupted(self, record):
        # Explicitly signal truncation rather than presenting partial output as success.
        try:
            self.wfile.write(b'data: {"error":{"message":"NOVA stream interrupted; not replayed","type":"api_connection_error","code":"nova_stream_interrupted"}}\n\n')
            self.wfile.flush()
        except OSError:
            pass
        self.close_connection = True
        record(phase='stream_interrupted')

    def do_GET(self):
        if not hmac.compare_digest(self.headers.get('Authorization', '').encode(),
                                   ('Bearer ' + self.server.api_key).encode()):
            return self.fail(401)
        if self.path != '/v1/models':
            return self.fail(404)
        raw = json.dumps({'object':'list','data':[{
            'id':self.server.primary,'object':'model','owned_by':'nova',
            'max_input_tokens':240000,'max_output_tokens':8192}]}).encode()
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        key = self.server.api_key
        if self.path != '/v1/chat/completions':
            return self.fail(404)
        if not hmac.compare_digest(self.headers.get('Authorization', '').encode(),
                                   ('Bearer ' + key).encode()):
            return self.fail(401)
        if not self.server.capacity.acquire(blocking=False):
            return self.fail(429)
        started = False
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_BODY or self.headers.get('Transfer-Encoding'):
                return self.fail(413)
            self.connection.settimeout(60)
            raw = self.rfile.read(length)
            if len(raw) != length:
                return self.fail(400)
            try:
                payload = json.loads(raw)
            except ValueError:
                return self.fail(400)
            if not isinstance(payload, dict) or not isinstance(payload.get('messages'), list):
                return self.fail(400)
            request_id = secrets.token_hex(6)
            def record(**fields):
                update_status(request_id=request_id, **fields)
            record(phase='request', request_bytes=length, fallback=False)
            response, slot = open_response(payload, self.server.gateway, key,
                                          self.server.primary, record=record)
            with response:
                is_stream = 'text/event-stream' in response.headers.get('Content-Type', '')
                if is_stream:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Cache-Control', 'no-cache')
                    self.send_header('Connection', 'close')
                    self.send_header('X-NOVA-Credential-Slot', str(slot))
                    self.end_headers()
                    started = True
                    done = False
                    while True:
                        line = response.readline(MAX_LINE + 1)
                        if not line:
                            break
                        if len(line) > MAX_LINE:
                            raise RelayError(502)
                        if line.strip() == b'data: [DONE]':
                            done = True
                        self.wfile.write(line)
                        self.wfile.flush()
                        if line.startswith(b'data: '):
                            try:
                                packet = json.loads(line[6:])
                                if isinstance(packet, dict) and packet.get('error'):
                                    raise RelayError(502)
                                fields = usage_fields(packet)
                                if fields:
                                    record(**fields)
                            except ValueError:
                                pass
                    if not done:
                        raise RelayError(502)
                    self.close_connection = True
                else:
                    raw = response.read(MAX_BODY + 1)
                    if len(raw) > MAX_BODY:
                        raise RelayError(502)
                    fields = usage_fields(json.loads(raw))
                    if fields:
                        record(**fields)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(raw)))
                    self.send_header('X-NOVA-Credential-Slot', str(slot))
                    self.end_headers()
                    started = True
                    self.wfile.write(raw)
                record(phase='complete', slot=slot)
        except RelayError as exc:
            if not started:
                self.fail(exc.status)
            else:
                self.interrupted(record)
        except (ValueError, OSError):
            if not started:
                self.fail(502)
            else:
                self.interrupted(record)
        finally:
            self.server.capacity.release()

def main():
    server = ThreadingHTTPServer(('127.0.0.1', int(os.environ['NOVA_RELAY_PORT'])), RelayHandler)
    server.daemon_threads = True
    server.capacity = threading.BoundedSemaphore(2)
    server.api_key = os.environ['LITELLM_API_KEY']
    server.gateway = os.environ['NOVA_GATEWAY_URL']
    server.primary = os.environ.get('AGENT_MODEL', 'opencrabs-model')
    server.serve_forever()

if __name__ == '__main__':
    main()
