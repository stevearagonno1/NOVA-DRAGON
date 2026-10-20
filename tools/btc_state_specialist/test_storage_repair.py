import gzip, hashlib, io, json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import specialist as S
import stage_inputs
import delivery as D

class StorageRepairTests(unittest.TestCase):
    def test_bootstrap_checks_whole_workspace_before_fetch_or_write(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('bootstrap',Path(__file__).parent/'private_transport/bootstrap_from_md.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'NOVA_WORKSPACE':tmp}), patch.object(module,'LIMIT',0), patch.object(module,'fetch',side_effect=AssertionError('network started')):
            (Path(tmp)/'existing-owner-file').write_bytes(b'x')
            with self.assertRaisesRegex(RuntimeError,'125 MB workspace limit'):
                module.main('a'*40,Path(tmp)/'package')
            self.assertEqual([p.name for p in Path(tmp).iterdir()],['existing-owner-file'])

    def test_measure_path_reads_synthetic_remote_input_without_staging(self):
        import pandas as pd
        d=S.fixture()
        frame=pd.DataFrame({'close_time_utc':pd.to_datetime(d['dt'],unit='s',utc=True),'open':d['o'],'high':d['h'],'low':d['l'],'close':d['c'],'volume':d['v'],'minutes':d['minutes']})
        data=gzip.compress(frame.to_csv(index=False).encode(),mtime=0)
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'NOVA_WORKSPACE':tmp}), patch.object(S,'MONTHS',['2024-01']), patch.object(stage_inputs,'open_verified',side_effect=lambda item:io.BytesIO(data)):
            out=Path(tmp)/'evidence'
            S.run(out,synthetic=False)
            first=(out/'2024-01.raw.json.gz').read_bytes()
            S.run(out,synthetic=False)
            self.assertEqual((out/'2024-01.raw.json.gz').read_bytes(),first)
            self.assertEqual(json.loads((out/'audit.json').read_text())['independent_scalar_count_rows'],551)
            self.assertFalse((Path(tmp)/'inputs').exists())

    def test_over_budget_fails_before_network_or_output(self):
        import workspace_guard as W
        class Network:
            def open(self,*a,**kw):raise AssertionError('network must not start')
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'NOVA_WORKSPACE':tmp}), patch.object(W,'workspace_bytes',return_value=195000000):
            with self.assertRaisesRegex(RuntimeError,'125 MB workspace limit'):
                stage_inputs.read({},opener=Network())
            with self.assertRaisesRegex(RuntimeError,'125 MB workspace limit'):
                S.run(Path(tmp)/'output',synthetic=True)
            self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_remote_bytes_are_bounded_verified_and_never_cached(self):
        data=gzip.compress(b'sample',mtime=0)
        item={'month':'fixture','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'source_commit':'a'*40,'repository_path':'prices.csv.gz'}
        class Network:
            def __init__(self,data):self.data=data
            def open(self,*a,**kw):return io.BytesIO(self.data)
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'NOVA_WORKSPACE':tmp}):
            self.assertEqual(stage_inputs.read(item,Network(data)),data)
            with self.assertRaisesRegex(RuntimeError,'hash/size'):
                stage_inputs.read(item,Network(data+b'x'))
            with self.assertRaisesRegex(RuntimeError,'hash/size'):
                stage_inputs.read(item,Network(b'x'*len(data)))
            self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_validated_input_is_returned_without_disk_copy(self):
        data=gzip.compress(b'example',mtime=0)
        item={'month':'fixture','local_path':'inputs/fixture.csv.gz','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        with tempfile.TemporaryDirectory() as tmp, patch.object(stage_inputs,'ROOT',Path(tmp)), patch.dict(os.environ,{'NOVA_WORKSPACE':tmp}):
            self.assertEqual(stage_inputs.stage(item,data),data)
            self.assertEqual(list(Path(tmp).rglob('*')),[])

    def test_compressed_candles_are_read_from_memory(self):
        import pandas as pd
        d=S.fixture()
        frame=pd.DataFrame({'close_time_utc':pd.to_datetime(d['dt'],unit='s',utc=True),'open':d['o'],'high':d['h'],'low':d['l'],'close':d['c'],'volume':d['v'],'minutes':d['minutes']})
        loaded=S.load_data(io.BytesIO(gzip.compress(frame.to_csv(index=False).encode())),compression='gzip')
        self.assertEqual(len(loaded['c']),420)

    def test_receipt_verification_accepts_prior_transport_annotations(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'NOVA_WORKSPACE':tmp}):
            out=Path(tmp)
            payload={'files':[{'path':'a','git_blob_sha':'abc','bytes':1,'sha256':'x'}],'fixture':False,'code_commit':'code','archive_bytes':1,'archive_sha256':'x','destination_branch':'agent/test'}
            readback={'tree':[{'path':'a','sha':'abc','size':1,'type':'blob'}],'truncated':False,'commit':'payload'}
            (out/'publish_payload.json').write_text(json.dumps(payload));(out/'readback.json').write_text(json.dumps(readback))
            D.verify(out,out/'readback.json')
            p=out/'VERIFIED_DELIVERY.json';r=json.loads(p.read_text());r.update(elapsed_to_payload_verification_seconds=12,transport='direct REST');p.write_text(json.dumps(r))
            before=p.read_bytes();D.verify(out,out/'readback.json');self.assertEqual(p.read_bytes(),before)
            r['payload_commit']='different';p.write_text(json.dumps(r))
            with self.assertRaisesRegex((AssertionError,RuntimeError),'receipt'):
                D.verify(out,out/'readback.json')

if __name__=='__main__':unittest.main()
