"""CLI-level synthetic exercise of the shared R1 pipeline and remote writers.

The synthetic path injects the same commit/tree/blob API shape as the unit
transport fixture. It never calls the real GitHub transport and never reads
market outcomes. Its forced finalist is explicitly a fixture hook, not a
registered selection or research result.
"""
from __future__ import annotations
import itertools
import os
import tempfile
from types import SimpleNamespace
import numpy as np
import pandas as pd

from . import indicators as I, measure as M, pipeline as P
from .streaming import RemoteTradeWriter, BASE
from .audit import rebuild_all
from .test_streaming import MemoryTransport

SESSION=None

class SyntheticPanel:
    def __init__(self,symbol,settings):
        self.sym=symbol;self.ranges={};self._masks={name:[] for name in settings}
        opens=[];highs=[];lows=[];closes=[];atrs=[];segs=[];dates=[];day_ix=[]
        for segno,(window,start,end) in enumerate(M.HALF_YEARS):
            lo=len(opens);n=64;dt=pd.date_range(start,periods=n,freq='4h',tz='UTC').tz_localize(None)
            self.ranges[window]=(lo,lo+n-1)
            prices=np.full(n,100.0 if symbol=='SYNTH-A' else 50.0)
            h=prices+0.2;l=prices-0.2
            # Deterministic targets, stops, and timeouts cover the shared
            # execution writer without asserting any market result.
            h[22]=prices[22]+2.0
            if n>38:l[38]=prices[38]-2.0
            opens.extend(prices);highs.extend(h);lows.extend(l);closes.extend(prices)
            atrs.extend(np.ones(n));segs.extend(np.full(n,segno,dtype=np.int32));dates.extend(dt.to_numpy())
            days=(dt.to_numpy().astype('datetime64[D]')-np.datetime64('2021-01-01')).astype(int)
            day_ix.extend(days)
            for name in settings:
                mask=np.zeros(n,dtype=bool)
                if name==settings[0]:mask[20]=True
                if name==settings[1]:mask[20]=True;mask[21]=True
                self._masks[name].extend(mask)
        self.o=np.asarray(opens,dtype=float);self.h=np.asarray(highs,dtype=float);self.l=np.asarray(lows,dtype=float)
        self.c=np.asarray(closes,dtype=float);self.atr=np.asarray(atrs,dtype=float);self.seg=np.asarray(segs,dtype=np.int32)
        self.dt=np.asarray(dates);self.days=np.asarray(day_ix,dtype=np.int32)
        self.day0s={w:int(self.days[a]) for w,(a,b) in self.ranges.items()}
        self._masks={k:np.asarray(v,dtype=bool) for k,v in self._masks.items()}
    def mask_of(self,name):return self._masks.get(name,np.zeros(len(self.c),dtype=bool))
    def day0(self,window):return self.day0s[window]

class SyntheticMeasurer(M.Measurer):
    def __init__(self,settings):
        self.log=lambda *_a,**_k:None
        self.panels={s:SyntheticPanel(s,settings) for s in ('SYNTH-A','SYNTH-B')}
        self._baseline_cache={};self._base_trades={}

def _ensure_csv(path,header):
    if not os.path.exists(path):
        pd.DataFrame(columns=header).to_csv(path,index=False)

def measure_synthetic(run_id='synthetic-cli-v1'):
    global SESSION
    old={"settings":I.SETTINGS_52,"singles":P.SETTINGS_SINGLES,"extra":P.SETTINGS_EXTRA,
         "canonical":M.canonical_pairs,"m_out":M.O,"p_out":P.O}
    temp=tempfile.TemporaryDirectory(prefix='l0084-r1-synthetic-')
    try:
        settings=list(old['settings'][:3]);I.SETTINGS_52=settings;P.SETTINGS_SINGLES=settings[:];P.SETTINGS_EXTRA=settings[:]
        M.canonical_pairs=lambda:list(itertools.combinations(I.SETTINGS_52,2))
        M.O=temp.name;P.O=temp.name
        os.makedirs(temp.name,exist_ok=True)
        M.write_registries()
        triple_header=['prefix_id','triple_id','member_a','member_b','member_c','mode','parent_ids','eligible','reason']
        pd.DataFrame(columns=triple_header).to_csv(os.path.join(temp.name,'triples_registry.csv'),index=False)
        client=MemoryTransport();m=SyntheticMeasurer(settings);writer=RemoteTradeWriter(client,run_id=run_id)
        singles=P.stage_singles(m,writer=writer)
        pairs=P.stage_pairs(m,singles,writer=writer)
        regs=[];triples={}
        for prefix in M.OUTER:
            retained=P.select_retained(pairs,prefix);rr=P.register_triples(prefix,retained);regs.extend(rr)
        # Register files exist before triple runner calls even when the fixed
        # sample gate properly yields no eligible parents.
        if regs:pd.DataFrame(regs).to_csv(os.path.join(temp.name,'triples_registry.csv'),index=False)
        for prefix in M.OUTER:triples[prefix]=P.stage_triples(m,singles,pairs,prefix,[r for r in regs if r['prefix_id']==prefix],writer=writer)
        finalists,_=P.stage_selection(m,singles,pairs,triples)
        # Exercise outer/control writers without treating the fixture's forced
        # pair as a statistical selection. Its provenance stays synthetic.
        synthetic_pair='P0001|AND0'
        if synthetic_pair not in pairs:raise RuntimeError('synthetic pair fixture missing')
        rec=pairs[synthetic_pair]
        finalists['2023H1']['chosen']=synthetic_pair
        finalists['2023H1']['detail']={'id':synthetic_pair,'stage':'pair','member_names':tuple(rec['members']),
            'mode':rec['mode'],'eligible':False,'worst_bound':None,'minimum_count':0}
        sel_path=os.path.join(temp.name,'selection_log.csv');sel=pd.read_csv(sel_path)
        sel.loc[(sel['prefix']=='2023H1') & (sel['candidate']==synthetic_pair),'selected']=1
        sel.loc[(sel['prefix']=='2023H1') & (sel['candidate']==synthetic_pair),'reason']='synthetic fixture forced only for control-writer coverage'
        sel.to_csv(sel_path,index=False)
        outer=P.stage_outer(m,finalists,writer=writer)
        controls=P.stage_controls(m,finalists,singles,writer=writer)
        neighbors=P.stage_neighbours(m,finalists,singles,pairs,writer=writer)
        descriptive=P.stage_descriptive(m,singles,pairs,writer=writer)
        frozen=P.stage_freeze(finalists,triples)
        summary=writer.close()
        for filename,header in (
            ('pairs_registry.csv',['pair_id','member_a','member_b','mode']),
            ('triples_registry.csv',triple_header),
            ('selection_log.csv',['prefix','candidate','selected']),
            ('neighbors_registry.csv',['neighbour_id','prefix_id','base_candidate','member','neighbour_setting','mode'])):
            _ensure_csv(os.path.join(temp.name,filename),header)
        metadata_base=BASE+'/synthetic_cli_fixture'
        files={metadata_base+'/'+name:open(os.path.join(temp.name,name),'rb').read()
               for name in ('pairs_registry.csv','triples_registry.csv','selection_log.csv','neighbors_registry.csv')}
        client.commit_files(files,client.branch_head(),'synthetic CLI metadata fixture')
        # Verify that committed trade/table partitions are actually readable,
        # immutable and reconciled before returning a successful measure code.
        verified_head=client.branch_head()
        audit=rebuild_all(client,verified_head,run_id,m,metadata_base=metadata_base)
        SESSION={"transport":client,"measurer":m,"run_id":run_id,"head":client.branch_head(),
                 "measure_summary":summary,"measurement_audit":audit,"metadata_base":metadata_base,
                 "tempdir":temp}
        required=(audit.get('independent_execution_rebuild')=='PASS' and audit.get('raw_metric_reconciliation')=='PASS'
            and str(audit.get('metrics_reconciliation','')).startswith('PASS_CANONICAL_METRIC_TABLE')
            and str(audit.get('adjustment_reconciliation','')).startswith('PASS_HOLM_POWER_OVERLAY')
            and str(audit.get('controls_reconciliation','')).startswith('PASS_INDEPENDENT_CONTROL_REBUILD')
            and audit.get('violations')==0)
        if not required:raise RuntimeError('synthetic measurement failed raw/table/control reconciliation')
        tree=client.trees[verified_head]
        max_parquet=max((len(data) for path,data in tree.items() if path.endswith('.parquet')),default=0)
        evidence_bytes=sum(len(data) for path,data in tree.items() if '/run='+run_id+'/' in path)
        return {"status":"PASS_SYNTHETIC_MEASURE","run_id":run_id,"groups":summary['metrics']['groups'],
                "trade_rows":summary['rows'],"trade_partitions":summary['partitions'],
                "final_metric_rows":summary['metrics']['final_metric_rows'],
                "control_rows":audit['control_result_rows'],"audit_head":verified_head,
                "max_parquet_bytes":max_parquet,"remote_evidence_bytes":evidence_bytes,
                "peak_workspace_bytes":summary['peak_workspace_bytes'],"peak_memory_bytes":summary['peak_rss_bytes'],
                "peak_pending_bytes":summary['peak_pending_bytes'],
                "outer_rows":len(outer),"control_summary_rows":len(controls),"neighbor_rows":len(neighbors),
                "descriptive_rows":len(descriptive),"triple_registry_rows":len(regs),"frozen":frozen.get('frozen')}
    except Exception:
        temp.cleanup();SESSION=None;raise
    finally:
        I.SETTINGS_52=old['settings'];P.SETTINGS_SINGLES=old['singles'];P.SETTINGS_EXTRA=old['extra']
        M.canonical_pairs=old['canonical'];M.O=old['m_out'];P.O=old['p_out']

def audit_synthetic():
    global SESSION
    if SESSION is None:raise RuntimeError('synthetic measure session unavailable; use the synthetic-readiness command')
    s=SESSION;fixed=s['transport'].branch_head()
    res=rebuild_all(s['transport'],fixed,s['run_id'],s['measurer'],metadata_base=s['metadata_base'])
    if res.get('independent_execution_rebuild')!='PASS' or res.get('raw_metric_reconciliation')!='PASS' or not str(res.get('metrics_reconciliation','')).startswith('PASS_CANONICAL_METRIC_TABLE') or not str(res.get('controls_reconciliation','')).startswith('PASS_INDEPENDENT_CONTROL_REBUILD') or res.get('violations')!=0:
        raise RuntimeError('synthetic audit failed required independent reconciliation')
    s['head']=fixed;s['audit']=res
    return {"status":"PASS_SYNTHETIC_AUDIT","fixed_head":fixed,"run_id":s['run_id'],
            "trade_rows":res['trade_rows'],"groups_rebuilt":res['groups_rebuilt'],
            "final_metric_rows":res['final_metric_rows'],"control_rows":res['control_result_rows'],
            "zero_trade_groups":res['zero_trade_candidate_windows'],"violations":res['violations']}
