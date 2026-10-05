import hashlib
import json
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

try:
    from . import engine as E
    from .streaming import RemoteTradeWriter, TRADE_SCHEMA
    from .transport import TransportError
    from .audit import verify_remote_partitions,rebuild_all
except ImportError:
    from l0084_entry_mix_r1 import engine as E
    from l0084_entry_mix_r1.streaming import RemoteTradeWriter, TRADE_SCHEMA
    from l0084_entry_mix_r1.transport import TransportError
    from l0084_entry_mix_r1.audit import verify_remote_partitions,rebuild_all


class MemoryTransport:
    def __init__(self, fail=None):
        self.head = 'head-0'
        self.trees = {self.head: {}}
        self.fail = fail
        self.calls = 0

    def branch_head(self):
        return self.head

    def commit_files(self, files, expected_head, message):
        self.calls += 1
        if expected_head != self.head:
            raise RuntimeError('head conflict')
        if self.fail == 'blob_before_ref':
            self.fail = None
            raise RuntimeError('interrupted after blobs before reference')
        if self.fail == 'conflict':
            self.fail = None
            raise RuntimeError('head conflict')
        new = f'head-{self.calls}'
        tree = dict(self.trees[self.head]); tree.update(files)
        self.trees[new] = tree
        self.head = new
        receipts = [SimpleNamespace(path=p, content_sha256=hashlib.sha256(b).hexdigest(),
                                    size_bytes=len(b), blob_sha=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest())
                    for p,b in files.items()]
        return new, receipts

    def list_directory(self, commit, path):
        prefix=path.rstrip('/')+'/'
        files=self.trees[commit]
        children=set()
        for full in files:
            if not full.startswith(prefix):continue
            rest=full[len(prefix):]
            if not rest:continue
            children.add(rest.split('/')[0])
        if not children:raise TransportError('directory resolution failed')
        return sorted(children)

    def blob_from_commit(self, commit, path):
        if self.fail == 'bad_readback':
            self.fail = None
            return b'corrupt'
        if path not in self.trees[commit]:
            raise TransportError('path resolution failed at storage_journal.jsonl')
        return self.trees[commit][path]


def synthetic_trade():
    n=24
    o=np.full(n,100.0);h=np.full(n,100.2);l=np.full(n,99.8);c=o.copy()
    atr=np.ones(n);seg=np.zeros(n,dtype=int);mask=np.zeros(n,dtype=bool);mask[0]=True
    h[3]=102.0
    trades,_=E.simulate(o,h,l,c,atr,seg,mask,'X','C0')
    return trades[0],pd.date_range('2023-01-01',periods=n,freq='4h',tz='UTC').to_numpy()


class StreamingTests(unittest.TestCase):
    def setUp(self):
        trade,dt=synthetic_trade()
        self.trade=trade
        self.panels={'X':SimpleNamespace(dt=dt)}

    def test_roundtrip_schema_values_and_empty_window(self):
        t=MemoryTransport();w=RemoteTradeWriter(t,run_id='synthetic',max_rows=1,batch_bytes=100000)
        w.add_window('C0','pair','2023H1',{'X':[self.trade]},self.panels)
        w.add_window('C0','pair','2023H2',{'X':[]},self.panels)
        result=w.close()
        paths=[p for p in t.trees[t.head] if p.endswith('.parquet')]
        self.assertEqual(len(paths),1)
        tab=pq.read_table(pa.BufferReader(t.blob_from_commit(t.head,paths[0])))
        self.assertTrue(tab.schema.equals(TRADE_SCHEMA,check_metadata=False))
        self.assertEqual(tab.num_rows,1)
        self.assertEqual(tab.column('outcome').to_pylist(),['target'])
        self.assertEqual(tab.column('holding_bars').to_pylist(),[3])
        index=[p for p in t.trees[t.head] if '/measurement_index/' in p]
        rows=[json.loads(line) for line in t.trees[t.head][index[0]].decode().splitlines()]
        self.assertEqual([r['trade_rows'] for r in rows],[1,0])
        self.assertEqual(result['rows'],1)
        self.assertLessEqual(result['peak_pending_bytes'],5_000_000)

    def test_readback_mismatch_fails_closed(self):
        t=MemoryTransport();w=RemoteTradeWriter(t,run_id='mismatch');t.fail='bad_readback'
        w.add_window('C0','pair','2023H1',{'X':[self.trade]},self.panels)
        with self.assertRaises(Exception):w.close()

    def test_workspace_disk_guard_stops_above_cap(self):
        t=MemoryTransport();w=RemoteTradeWriter(t,run_id='disk-guard')
        with patch('l0084_entry_mix_r1.streaming.os.walk',return_value=[('/fake',[],['large'])]), \
             patch('l0084_entry_mix_r1.streaming.os.path.getsize',return_value=125_000_001):
            with self.assertRaisesRegex(Exception,'disk guard exceeded'):
                w._resource_snapshot()

    def test_interrupt_before_ref_does_not_report_success(self):
        t=MemoryTransport(fail='blob_before_ref');w=RemoteTradeWriter(t,run_id='interrupt')
        w.add_window('C0','pair','2023H1',{'X':[self.trade]},self.panels)
        with self.assertRaises(Exception):w.close()
        self.assertEqual(t.head,'head-0')

    def test_compare_and_update_conflict_fails(self):
        t=MemoryTransport();w=RemoteTradeWriter(t,run_id='conflict')
        w.add_window('C0','pair','2023H1',{'X':[self.trade]},self.panels)
        t.fail='conflict'
        with self.assertRaises(Exception):w.close()

    def test_restart_replays_identical_window_without_duplicate(self):
        t=MemoryTransport();w=RemoteTradeWriter(t,run_id='resume')
        w.add_window('C0','pair','2023H1',{'X':[self.trade]},self.panels);first=w.close()
        head=t.head;w2=RemoteTradeWriter(t,run_id='resume')
        self.assertEqual(w2.completed_windows[('C0','pair','2023H1')]['trade_rows'],1)
        w2.add_window('C0','pair','2023H1',{'X':[self.trade]},self.panels);second=w2.close()
        self.assertEqual(second['rows'],1);self.assertEqual(second['partitions'],1)
        self.assertEqual(t.head,head)
        self.assertEqual(sum(1 for p in t.trees[t.head] if p.endswith('.parquet')),1)

    def test_restart_recovers_partition_committed_before_index(self):
        t=MemoryTransport();w=RemoteTradeWriter(t,run_id='orphan')
        w.add_window('C0','pair','2023H1',{'X':[self.trade]},self.panels)
        w.flush()  # simulated interruption before coverage index is committed
        partitions=sum(1 for p in t.trees[t.head] if p.endswith('.parquet'))
        w2=RemoteTradeWriter(t,run_id='orphan')
        w2.add_window('C0','pair','2023H1',{'X':[self.trade]},self.panels)
        result=w2.close()
        self.assertEqual(result['rows'],1);self.assertEqual(result['partitions'],1)
        self.assertEqual(sum(1 for p in t.trees[t.head] if p.endswith('.parquet')),partitions)
        reconciled=verify_remote_partitions(t,t.head,'orphan')
        self.assertEqual(reconciled['trade_rows'],1)

    def test_full_remote_journal_index_and_partition_audit(self):
        t=MemoryTransport();w=RemoteTradeWriter(t,run_id='audit')
        w.add_window('C0','pair','2023H1',{'X':[self.trade]},self.panels)
        w.add_window('C0','pair','2023H2',{'X':[]},self.panels);w.close()
        result=verify_remote_partitions(t,t.head,'audit')
        self.assertEqual(result['partitions'],1);self.assertEqual(result['trade_rows'],1)
        self.assertEqual(result['coverage_rows'],2);self.assertEqual(result['zero_trade_candidate_windows'],1)
        path=next(p for p in t.trees[t.head] if p.endswith('.parquet'))
        del t.trees[t.head][path]
        with self.assertRaises(Exception):verify_remote_partitions(t,t.head,'audit')

    def test_full_independent_rebuild_matches_synthetic_window(self):
        class Panel:
            def __init__(self):
                self.sym='X';self.dt=self.panels_dt
                self.o=np.full(60,100.0);self.h=np.full(60,100.2);self.l=np.full(60,99.8);self.c=self.o.copy()
                self.atr=np.ones(60);self.seg=np.zeros(60,dtype=int);self.ranges={'2023H1':(0,59),'2023H2':(0,19)}
                self.mask=np.zeros(60,dtype=bool);self.mask[20]=True;self.h[21]=102.0
            @property
            def panels_dt(self):return pd.date_range('2023-01-01',periods=60,freq='4h',tz='UTC').to_numpy()
            def mask_of(self,name):return self.mask
        class Measurer:
            def __init__(self,p):self.panels={'X':p}
        p=Panel();m=Measurer(p)
        trades,_=E.simulate_window(p.o,p.h,p.l,p.c,p.atr,p.seg,p.mask,'X','candidate',0,59)
        t=MemoryTransport();meta={
          'history/research/hyp_lab_out/L0084-entry-mix-r1/pairs_registry.csv':b'pair_id,member_a,member_b\n',
          'history/research/hyp_lab_out/L0084-entry-mix-r1/triples_registry.csv':b'prefix_id,triple_id,member_a,member_b,member_c,mode,parent_ids\n',
          'history/research/hyp_lab_out/L0084-entry-mix-r1/selection_log.csv':b'prefix,candidate,selected\n',
          'history/research/hyp_lab_out/L0084-entry-mix-r1/neighbors_registry.csv':b'neighbour_id,prefix_id,base_candidate,member,neighbour_setting,mode\n'}
        head=t.branch_head();head,_=t.commit_files(meta,head,'synthetic metadata')
        w=RemoteTradeWriter(t,run_id='full-audit')
        w.add_window('C0','single','2023H1',{'X':trades},m.panels)
        w.add_window('C0','single','2023H2',{'X':[]},m.panels)
        w.add_window('C1','single','2023H1',{'X':trades},m.panels);w.close()
        result=rebuild_all(t,t.head,'full-audit',m)
        self.assertEqual(result['independent_execution_rebuild'],'PASS')
        self.assertEqual(result['groups_rebuilt'],3)
        self.assertEqual(result['zero_trade_candidate_windows'],1)
        self.assertEqual(result['trades_rebuilt'],len(trades)*2)


if __name__=='__main__':
    unittest.main()
