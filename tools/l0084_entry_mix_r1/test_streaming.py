import hashlib
import json
import io
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

try:
    from . import engine as E
    from .streaming import RemoteTradeWriter, TRADE_SCHEMA, BASE, _row as trade_row
    from .transport import TransportError
    from .audit import verify_remote_partitions,rebuild_all,_independent_block_stats,_independent_paired_difference,_random_reference,independent_simulate_window
except ImportError:
    from l0084_entry_mix_r1 import engine as E
    from l0084_entry_mix_r1.streaming import RemoteTradeWriter, TRADE_SCHEMA, BASE, _row as trade_row
    from l0084_entry_mix_r1.transport import TransportError
    from l0084_entry_mix_r1.audit import verify_remote_partitions,rebuild_all,_independent_block_stats,_independent_paired_difference,_random_reference,independent_simulate_window


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
        self.panels={'X':SimpleNamespace(dt=dt,ranges={'2023H1':(0,len(dt)-1),'2023H2':(0,19)})}

    def test_roundtrip_schema_values_and_empty_window(self):
        t=MemoryTransport();w=RemoteTradeWriter(t,run_id='synthetic',max_rows=1,batch_bytes=100000)
        w.add_window('C0','pair','2023H1',{'X':[self.trade]},self.panels)
        w.add_window('C0','pair','2023H2',{'X':[]},self.panels)
        result=w.close()
        paths=[p for p in t.trees[t.head] if '/trades/' in p and p.endswith('.parquet')]
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
        self.assertEqual(result['metrics']['groups'],2)
        self.assertEqual(result['metrics']['halfyear_part_count'],1)
        hp=[x for x in t.trees[t.head] if '/halfyears.csv/run=synthetic/' in x and x.endswith('.csv')]
        self.assertEqual(len(hp),1)
        half=pd.concat([pd.read_csv(io.BytesIO(t.blob_from_commit(t.head,x))) for x in hp],ignore_index=True)
        self.assertEqual(list(half.columns),['candidate','asset','halfyear','partial','n','net','pf','win','baseline','lift','ci_lo','ci_hi'])
        self.assertEqual(sorted(half['n'].tolist()),[0,1])
        mp=[x for x in t.trees[t.head] if '/metrics_raw/run=synthetic/' in x and x.endswith('.parquet')]
        ap=[x for x in t.trees[t.head] if '/metrics_by_asset/run=synthetic/' in x and x.endswith('.parquet')]
        self.assertEqual(len(mp),1);self.assertEqual(len(ap),1)
        mt=pq.read_table(pa.BufferReader(t.blob_from_commit(t.head,mp[0]))).to_pylist()
        at=pq.read_table(pa.BufferReader(t.blob_from_commit(t.head,ap[0]))).to_pylist()
        self.assertEqual([x['n_exec'] for x in mt],[1,0])
        self.assertEqual([x['n_exec'] for x in at],[1,0])
        self.assertEqual(mt[1]['win_rate'],None)
        self.assertEqual(mt[1]['metric_status'],'ZERO_TRADES; inference_not_computed')

    def test_random_control_result_partition_has_matched_counts_and_seed(self):
        from .metrics import CONTROL_SCHEMA
        t=MemoryTransport();w=RemoteTradeWriter(t,run_id='controls')
        w.add_window('RAND:2023H1:C0:rep000','random_control','2023H1',{'X':[self.trade]},self.panels,
            control_info={'candidate':'C0','replicate':0,'matched_counts':{'X':1},'seeds':{'X':84}})
        result=w.close();self.assertEqual(result['metrics']['control_part_count'],1)
        path=next(p for p in t.trees[t.head] if '/controls/run=controls/' in p and p.endswith('.parquet'))
        tab=pq.read_table(pa.BufferReader(t.blob_from_commit(t.head,path)))
        self.assertTrue(tab.schema.equals(CONTROL_SCHEMA,check_metadata=False))
        row=tab.to_pylist()[0]
        self.assertEqual((row['candidate'],row['control_type'],row['replicate']),('C0','random_entry',0))
        self.assertEqual((row['n'],row['matched_count'],row['seed']),(1,1,84))
        self.assertIsNone(row['paired_difference'])

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
        self.assertEqual(sum(1 for p in t.trees[t.head] if '/trades/' in p and p.endswith('.parquet')),1)

    def test_restart_recovers_partition_committed_before_index(self):
        t=MemoryTransport();w=RemoteTradeWriter(t,run_id='orphan')
        w.add_window('C0','pair','2023H1',{'X':[self.trade]},self.panels)
        w.flush()  # simulated interruption before coverage index is committed
        partitions=sum(1 for p in t.trees[t.head] if '/trades/' in p and p.endswith('.parquet'))
        w2=RemoteTradeWriter(t,run_id='orphan')
        w2.add_window('C0','pair','2023H1',{'X':[self.trade]},self.panels)
        result=w2.close()
        self.assertEqual(result['rows'],1);self.assertEqual(result['partitions'],1)
        self.assertEqual(sum(1 for p in t.trees[t.head] if '/trades/' in p and p.endswith('.parquet')),partitions)
        reconciled=verify_remote_partitions(t,t.head,'orphan')
        self.assertEqual(reconciled['trade_rows'],1)

    def test_full_remote_journal_index_and_partition_audit(self):
        t=MemoryTransport();w=RemoteTradeWriter(t,run_id='audit')
        w.add_window('C0','pair','2023H1',{'X':[self.trade]},self.panels)
        w.add_window('C0','pair','2023H2',{'X':[]},self.panels);w.close()
        result=verify_remote_partitions(t,t.head,'audit')
        self.assertEqual(result['partitions'],1);self.assertEqual(result['trade_rows'],1)
        self.assertEqual(result['coverage_rows'],2);self.assertEqual(result['zero_trade_candidate_windows'],1)
        path=next(p for p in t.trees[t.head] if '/trades/' in p and p.endswith('.parquet'))
        del t.trees[t.head][path]
        with self.assertRaises(Exception):verify_remote_partitions(t,t.head,'audit')

    def test_full_independent_rebuild_matches_synthetic_window(self):
        class Panel:
            def __init__(self,sym,price):
                self.sym=sym;self.dt=pd.date_range('2023-01-01',periods=60,freq='4h',tz='UTC').to_numpy()
                self.o=np.full(60,price);self.h=self.o+.2;self.l=self.o-.2;self.c=self.o.copy()
                self.atr=np.ones(60);self.seg=np.zeros(60,dtype=int);self.ranges={'2023H1':(0,59),'2023H2':(0,19)}
                self.mask=np.zeros(60,dtype=bool);self.mask[20]=True;self.h[21]=price+2.0
            def mask_of(self,name):return self.mask
        class Measurer:
            def __init__(self,panels):self.panels=panels
        panels={'X':Panel('X',100.0),'Y':Panel('Y',50.0)};m=Measurer(panels)
        trades_by_asset={sym:E.simulate_window(p.o,p.h,p.l,p.c,p.atr,p.seg,p.mask,sym,'candidate',0,59)[0] for sym,p in panels.items()}
        base_by_asset={sym:independent_simulate_window(p.o,p.h,p.l,p.c,p.atr,p.seg,None,sym,'NO-SIGNAL',0,59) for sym,p in panels.items()}
        all_trades=[t for rows in trades_by_asset.values() for t in rows]
        matched_counts={sym:len(rows) for sym,rows in trades_by_asset.items()}
        t=MemoryTransport();meta_base=BASE+'/synthetic_fixture';meta={
          meta_base+'/pairs_registry.csv':b'pair_id,member_a,member_b\n',
          meta_base+'/triples_registry.csv':b'prefix_id,triple_id,member_a,member_b,member_c,mode,parent_ids\n',
          meta_base+'/selection_log.csv':b'prefix,candidate,selected\n2023H1,C0,1\n',
          meta_base+'/neighbors_registry.csv':b'neighbour_id,prefix_id,base_candidate,member,neighbour_setting,mode\n'}
        head=t.branch_head();head,_=t.commit_files(meta,head,'synthetic metadata')
        w=RemoteTradeWriter(t,run_id='full-audit')
        def runner_stats(cid,role='single'):
            audited=_independent_block_stats([trade_row(x,cid,role,'2023H1',m.panels) for x in all_trades],'2023H1',m.panels)
            return {"baseline_win":audited["baseline_win_rate"],"breakeven_ref":audited["breakeven_rate"],
                    "lift_win_pts":audited["lift_win_points"],"p_raw":audited["p_raw"],
                    "exp_lo5":audited["ci_lo"],"exp_hi95":audited["ci_hi"],
                    "expectancy":audited["expectancy"],"exp_se":audited["exp_se"]}
        w.add_window('2023H1:C0','outer','2023H1',trades_by_asset,m.panels,stats=runner_stats('2023H1:C0','outer'),baseline_by_asset=base_by_asset,members=('C0',),mode='AND0')
        w.add_window('C0','single','2023H2',{'X':[],'Y':[]},m.panels,baseline_by_asset={'X':[],'Y':[]},members=('C0',),mode='AND0')
        w.add_window('C1','single','2023H1',trades_by_asset,m.panels,stats=runner_stats('C1'),baseline_by_asset=base_by_asset,members=('C1',),mode='AND0')
        random_by_asset={sym:_random_reference(p,'2023H1',matched_counts[sym],'C0',0) for sym,p in panels.items()}
        seeds={sym:__import__('l0084_entry_mix_r1.measure',fromlist=['sha_seed']).sha_seed(f'84|{sym}|2023H1|C0|0') for sym in panels}
        paired_by_asset={sym:_independent_paired_difference(
            [trade_row(x,'C0','outer','2023H1',m.panels) for x in trades_by_asset[sym]],
            [trade_row(x,'C0','random_control','2023H1',m.panels) for x in random_by_asset[sym]],'2023H1',panels[sym])
            for sym in panels}
        w.add_window('RAND:2023H1:C0:rep000','random_control','2023H1',random_by_asset,m.panels,
            control_info={'candidate':'C0','replicate':0,'matched_counts':matched_counts,'seeds':seeds,
                          'paired_by_asset':paired_by_asset},baseline_by_asset=base_by_asset,members=('C0',),mode='AND0')
        w.close()
        result=rebuild_all(t,t.head,'full-audit',m,metadata_base=meta_base)
        self.assertEqual(result['independent_execution_rebuild'],'PASS')
        self.assertEqual(result['raw_metric_reconciliation'],'PASS')
        self.assertEqual(result['independent_inference_rows_reconciled'],2)
        self.assertEqual(result['metrics_reconciliation'],'PASS_CANONICAL_METRIC_TABLE; raw trades and adjustment join independently reconciled')
        self.assertEqual(result['adjustment_reconciliation'],'PASS_HOLM_POWER_OVERLAY_AND_CANONICAL_JOIN')
        self.assertEqual(result['groups_rebuilt'],4)
        self.assertEqual(result['zero_trade_candidate_windows'],1)
        self.assertEqual(result['controls_reconciliation'],'PASS_RAW_CONTROL_TABLE; paired_difference_and_CI_pending')
        self.assertEqual(result['control_result_rows'],2)
        self.assertEqual(result['halfyear_rows'],8)
        self.assertEqual(result['adjustment_rows'],2)
        self.assertEqual(result['final_metric_rows'],12)
        self.assertEqual(result['trades_rebuilt'],sum(map(len,trades_by_asset.values()))*2+sum(map(len,random_by_asset.values())))
        metric_path=next(x for x in t.trees[t.head] if '/metrics_raw/run=full-audit/' in x and x.endswith('.parquet'))
        original_metric=t.blob_from_commit(t.head,metric_path)
        metric=pq.read_table(pa.BufferReader(original_metric))
        altered=metric.to_pylist();altered[0]['net_dollars']+=1.0
        sink=pa.BufferOutputStream();pq.write_table(pa.Table.from_pylist(altered,schema=metric.schema),sink,compression='zstd')
        payload=sink.getvalue().to_pybytes();badhead=t.branch_head();t.commit_files({metric_path:payload},badhead,'synthetic changed-metric failure')
        with self.assertRaisesRegex(Exception,'metric value mismatch'):
            rebuild_all(t,t.head,'full-audit',m,metadata_base=meta_base)
        t.commit_files({metric_path:original_metric},t.branch_head(),'restore synthetic metric after tamper check')
        control_path=next(x for x in t.trees[t.head] if '/controls/run=full-audit/' in x and x.endswith('.parquet'))
        original_control=t.blob_from_commit(t.head,control_path)
        control=pq.read_table(pa.BufferReader(original_control))
        altered_control=control.to_pylist();altered_control[0]['matched_count']+=1
        sink=pa.BufferOutputStream();pq.write_table(pa.Table.from_pylist(altered_control,schema=control.schema),sink,compression='zstd')
        payload=sink.getvalue().to_pybytes();badhead=t.branch_head();t.commit_files({control_path:payload},badhead,'synthetic changed-control failure')
        with self.assertRaisesRegex(Exception,'control value mismatch'):
            rebuild_all(t,t.head,'full-audit',m,metadata_base=meta_base)
        t.commit_files({control_path:original_control},t.branch_head(),'restore synthetic control after tamper check')
        halfyear_path=next(x for x in t.trees[t.head] if '/halfyears.csv/run=full-audit/' in x and x.endswith('.csv'))
        half_raw=t.blob_from_commit(t.head,halfyear_path);half_df=pd.read_csv(io.BytesIO(half_raw));half_df.loc[0,'net']+=1.0
        half_bad=half_df.to_csv(index=False,lineterminator='\n').encode()
        t.commit_files({halfyear_path:half_bad},t.branch_head(),'synthetic changed halfyear failure')
        with self.assertRaisesRegex(Exception,'half-year value mismatch'):
            rebuild_all(t,t.head,'full-audit',m,metadata_base=meta_base)
        t.commit_files({halfyear_path:half_raw},t.branch_head(),'restore synthetic halfyear after tamper check')
        adj_path=next(x for x in t.trees[t.head] if '/metric_adjustments/run=full-audit/' in x and x.endswith('.parquet'))
        adj_raw=t.blob_from_commit(t.head,adj_path);adj_tab=pq.read_table(pa.BufferReader(adj_raw))
        altered_adj=adj_tab.to_pylist();altered_adj[0]['p_adjusted']=0.123
        sink=pa.BufferOutputStream();pq.write_table(pa.Table.from_pylist(altered_adj,schema=adj_tab.schema),sink,compression='zstd')
        t.commit_files({adj_path:sink.getvalue().to_pybytes()},t.branch_head(),'synthetic changed adjustment failure')
        with self.assertRaisesRegex(Exception,'metric adjustment mismatch'):
            rebuild_all(t,t.head,'full-audit',m,metadata_base=meta_base)


if __name__=='__main__':
    unittest.main()
