import base64
import hashlib
import json
import io
import urllib.error
import unittest
from email.message import Message
from unittest.mock import patch
try:
    from .transport import GitHubTransport, HeadConflict, TransportError, verify_bytes
except ImportError:
    from transport import GitHubTransport, HeadConflict, TransportError, verify_bytes


class FakeResponse:
    def __init__(self, status=200, data=None):
        self.status = status
        self.data = json.dumps(data or {}).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return self.data


class MockTransport(GitHubTransport):
    def __init__(self, scenario="ok"):
        super().__init__(token="not-a-real-secret", opener=lambda *a, **k: None)
        self.scenario = scenario
        self.head = "a" * 40
        self.objects = {}
        self.calls = []
    def _request(self, path, method="GET", payload=None):
        self.calls.append((path, method))
        if self.scenario == "network":
            raise TransportError("network failure: TimeoutError")
        if self.scenario == "auth":
            raise TransportError("GitHub API HTTP 401: Requires authentication")
        if path.startswith("/git/ref/heads/") or path.startswith("/git/refs/heads/"):
            if method == "GET":
                return 200, {"object": {"sha": self.head}}
            if method == "PATCH":
                if self.scenario == "conflict":
                    raise HeadConflict("branch head changed while preparing commit")
                self.head = payload["sha"]
                return 200, {}
        if path == "/git/commits/" + self.head:
            return 200, {"tree": {"sha": "b" * 40}}
        if path == "/git/blobs" and method == "POST":
            raw = base64.b64decode(payload["content"])
            sha = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            self.objects[sha] = raw
            return 201, {"sha": sha}
        if path == "/git/trees":
            if self.scenario == "interrupt":
                raise TransportError("network failure: interrupted after blob")
            return 201, {"sha": "c" * 40}
        if path == "/git/commits" and method == "POST":
            return 201, {"sha": "d" * 40}
        raise AssertionError((path, method))


class TransportTests(unittest.TestCase):
    def test_success_tracks_sha_and_size(self):
        t = MockTransport()
        content = b"synthetic-only"
        commit, receipts = t.commit_files(
            {"transport_smoke/example.bin": content}, "a" * 40, "smoke")
        self.assertEqual(commit, "d" * 40)
        self.assertEqual(receipts[0].content_sha256, hashlib.sha256(content).hexdigest())
        self.assertEqual(receipts[0].size_bytes, len(content))
    def test_auth_failure_is_not_success(self):
        t = MockTransport("auth")
        with self.assertRaisesRegex(TransportError, "HTTP 401"):
            t.commit_files({"x": b"x"}, "a" * 40, "x")
    def test_network_failure_is_not_success(self):
        t = MockTransport("network")
        with self.assertRaisesRegex(TransportError, "network failure"):
            t.commit_files({"x": b"x"}, "a" * 40, "x")
    def test_head_conflict_stops(self):
        t = MockTransport("conflict")
        with self.assertRaises(HeadConflict):
            t.commit_files({"x": b"x"}, "a" * 40, "x")
    def test_preflight_conflict_stops(self):
        t = MockTransport()
        with self.assertRaises(HeadConflict):
            t.commit_files({"x": b"x"}, "z" * 40, "x")
    def test_sha_mismatch_is_not_accepted(self):
        with self.assertRaisesRegex(TransportError, "SHA256 mismatch"):
            verify_bytes(b"content", "0" * 64, 7)
    def test_interruption_after_blob_does_not_advance_ref(self):
        t = MockTransport("interrupt")
        with self.assertRaisesRegex(TransportError, "interrupted after blob"):
            t.commit_files({"x": b"x"}, "a" * 40, "x")
        self.assertEqual(t.head, "a" * 40)
    def test_retry_after_is_respected_once(self):
        calls=[];headers=Message();headers['Retry-After']='1'
        def opener(req,timeout=30):
            calls.append(1)
            if len(calls)==1:
                raise urllib.error.HTTPError(req.full_url,429,'rate limit',headers,io.BytesIO(b'{"message":"slow down"}'))
            return FakeResponse(200,{"ok":True})
        from l0084_entry_mix_r1.transport import GitHubTransport as GT
        t=GT(token='mock-only',opener=opener)
        with patch('l0084_entry_mix_r1.transport.time.sleep') as sleep:
            status,obj=t._request('/user')
        self.assertEqual((status,obj['ok']),(200,True));self.assertEqual(len(calls),2)
        sleep.assert_called_once_with(1.0)
    def test_long_retry_after_stops_without_sleep(self):
        headers=Message();headers['Retry-After']='900'
        def opener(req,timeout=30):
            raise urllib.error.HTTPError(req.full_url,429,'rate limit',headers,io.BytesIO(b'{"message":"limited"}'))
        from l0084_entry_mix_r1.transport import GitHubTransport as GT
        t=GT(token='mock-only',opener=opener)
        with patch('l0084_entry_mix_r1.transport.time.sleep') as sleep:
            with self.assertRaisesRegex(Exception,'HTTP 429'):
                t._request('/user')
        sleep.assert_not_called()

if __name__ == "__main__":
    unittest.main()
