import unittest
import base64
import hashlib
from unittest.mock import patch
from .stage1 import PacedTransport
from .transport import GitHubTransport


class PacingTest(unittest.TestCase):
    def test_long_request_schedule_with_virtual_clock(self):
        clock = [0.0]; records = []
        def sleep(seconds): clock[0] += seconds
        def request(_self, path, method='GET', payload=None):
            records.append((clock[0], method)); return 200, {}
        client = PacedTransport(token='fixture', clock=lambda:clock[0], sleeper=sleep)
        with patch.object(GitHubTransport, '_request', request):
            for _ in range(1000):
                client._request('/fixture', 'POST'); client._request('/fixture')
        writes = [t for t, method in records if method != 'GET']
        self.assertTrue(all(b-a >= 15 for a,b in zip(writes,writes[1:])))
        self.assertTrue(all(b[0]-a[0] >= 2 for a,b in zip(records,records[1:])))
        for start, _ in records:
            self.assertLessEqual(sum(start <= t < start+3600 for t in writes), 240)

    def test_cached_tree_and_byte_identity(self):
        data = b'raw evidence'; sha = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        responses = {'/git/commits/c':{'tree':{'sha':'tree'}},
                     '/git/trees/tree?recursive=1':{'tree':[{'path':'raw/p','type':'blob','sha':sha}]},
                     '/git/blobs/'+sha:{'encoding':'base64','content':base64.b64encode(data).decode()}}
        calls=[]
        def request(_self,path,method='GET',payload=None):calls.append(path);return 200,responses[path]
        client=PacedTransport(token='fixture')
        with patch.object(GitHubTransport,'_request',request):
            self.assertEqual(client.blob_from_commit('c','raw/p'),data)
            self.assertEqual(client.list_directory('c','raw'),['p'])
            self.assertEqual(client.blob_from_commit('c','raw/p'),data)
        self.assertEqual(calls.count('/git/trees/tree?recursive=1'),1)
        responses['/git/blobs/'+sha]['content']=base64.b64encode(b'changed').decode()
        with patch.object(GitHubTransport,'_request',request):
            with self.assertRaisesRegex(RuntimeError,'Git blob SHA mismatch'):
                client.blob_from_commit('c','raw/p')


if __name__ == '__main__': unittest.main()
