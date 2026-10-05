import unittest
import pyarrow as pa
import pyarrow.parquet as pq
from .stage1 import measure_stage,audit_stage
from .synthetic import SyntheticMeasurer
from .indicators import SETTINGS_52
from .test_streaming import MemoryTransport
from .streaming import RemoteTradeWriter,BASE
from .transport import TransportError


class InterruptAfterCommit(MemoryTransport):
    def __init__(self,fragment):super().__init__();self.fragment=fragment;self.stopped=False
    def commit_files(self,files,expected_head,message):
        answer=super().commit_files(files,expected_head,message)
        if not self.stopped and any(self.fragment in path for path in files):
            self.stopped=True;raise RuntimeError('injected lost acknowledgement after '+self.fragment)
        return answer


class ResumeTests(unittest.TestCase):
    def writer(self,c,run):
        w=RemoteTradeWriter(c,run_id=run,max_rows=5000)
        w.metric_writer.rows_per_part=20
        return w

    def test_every_publication_boundary_preserves_raw_and_metric_coverage(self):
        settings=SETTINGS_52[:3];m=SyntheticMeasurer(settings)
        for fragment in ['/trades/','/storage_journal/run=','/storage_journal.jsonl',
                         '/metrics_raw/','/metrics_by_asset/','/halfyears.csv/',
                         '/measurement_index/','/metric_adjustments/','/metrics/']:
            with self.subTest(fragment=fragment):
                c=InterruptAfterCommit(fragment);run='resume-fixture'
                with self.assertRaisesRegex(RuntimeError,'injected'):
                    measure_stage(m,self.writer(c,run),settings)
                result=measure_stage(m,self.writer(c,run),settings)
                self.assertEqual(audit_stage(c,c.branch_head(),run,m,settings)['groups'],48)
                self.assertEqual(result['metrics']['groups'],48)
                for kind,expected in [('metrics_raw',48),('metrics_by_asset',96),('metrics',144)]:
                    prefix=f'{BASE}/{kind}/run={run}/';rows=[]
                    for path,raw in c.trees[c.branch_head()].items():
                        if path.startswith(prefix):rows.extend(pq.read_table(pa.BufferReader(raw)).to_pylist())
                    keys=[(r['candidate_id'],r['role'],r['window'],r['asset'],r['scope']) for r in rows]
                    self.assertEqual(len(keys),expected)
                    self.assertEqual(len(set(keys)),expected)
                before=dict(c.trees[c.branch_head()])
                repeat=measure_stage(m,self.writer(c,run),settings)
                self.assertEqual(repeat['metrics']['groups'],48)
                self.assertEqual(c.trees[c.branch_head()],before)

    def test_missing_derived_table_is_not_a_complete_delivery(self):
        settings=SETTINGS_52[:3];m=SyntheticMeasurer(settings);c=MemoryTransport();run='missing-metric'
        measure_stage(m,self.writer(c,run),settings)
        tree=c.trees[c.branch_head()]
        path=next(p for p in tree if '/metrics_raw/' in p)
        del tree[path]
        with self.assertRaises(TransportError):audit_stage(c,c.branch_head(),run,m,settings)

    def test_rate_limit_on_listing_never_becomes_missing_evidence(self):
        class RateLimited(MemoryTransport):
            def list_directory(self,*args):raise TransportError('GitHub API HTTP 403: rate limit; Retry-After=1753.1s')
        with self.assertRaisesRegex(TransportError,'HTTP 403'):
            self.writer(RateLimited(),'resume-fixture')


if __name__=='__main__':unittest.main()
