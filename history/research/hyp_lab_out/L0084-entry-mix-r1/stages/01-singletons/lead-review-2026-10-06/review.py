"""Reproducible Lead review. Reads only the immutable delivered run; no new grid."""
from pathlib import Path
import hashlib,json,sys,itertools,time,os
import numpy as np,pandas as pd,pyarrow as pa,pyarrow.parquet as pq
from scipy.stats import norm
ROOT=Path(__file__).resolve().parent
CODE=Path(os.environ.get('NOVA_STAGE1_CODE',str(ROOT.parent/'stage1_review_v3/tools'))).resolve()
sys.path.insert(0,str(CODE))
from l0084_entry_mix_r1 import indicators as I,measure as M,data as D,audit as A,streaming as W,stats as S
HEAD='2d67a6593a34c0b46e7e4f686efc57db435982a9';RUN='stage1-singletons-v1';BASE=W.BASE
meta=json.loads((ROOT/'remote.json').read_text());tree={x['path']:x for x in meta['tree']['tree'] if x['type']=='blob'}
manifest=json.loads((ROOT/'download_manifest.json').read_text());files={x['path']:x for x in manifest['files']};scope=json.loads((ROOT/'scope.json').read_text())
def blob(path):
 row=tree[path];b=(ROOT/'blobs'/row['sha']).read_bytes()
 assert len(b)==row['size'] and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==row['sha'],path
 return b
for name,h in scope['code_sha256'].items():
 p=CODE/'l0084_entry_mix_r1'/name;b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==h
 assert tree['tools/l0084_entry_mix_r1/'+name]['sha']==hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def rows_under(kind):
 return sorted(p for p in files if p.startswith(BASE+'/'+kind+'/run='+RUN+'/'))
coverage=[json.loads(line) for path in rows_under('measurement_index') for line in blob(path).decode().splitlines()]
wanted=set(itertools.product(['NO-SIGNAL',*I.SETTINGS_52],[w[0] for w in M.HALF_YEARS]));assert len(coverage)==636 and {(x['candidate_id'],x['window']) for x in coverage}==wanted
pointers=[json.loads(x) for x in blob(BASE+'/storage_journal.jsonl').decode().splitlines() if x];pointers=[x for x in pointers if x.get('run_id')==RUN];receipts=[]
for p in pointers:
 b=blob(p['path']);assert len(b)==p['bytes'] and hashlib.sha256(b).hexdigest()==p['sha256'] and tree[p['path']]['sha']==p['git_blob_sha'];receipts.extend(json.loads(x) for x in b.decode().splitlines())
assert len({x['path'] for x in receipts})==len(receipts)==635
assert {x['path'] for x in receipts}==set(rows_under('trades'))
chunks=[]
for rec in receipts:
 b=blob(rec['path']);assert len(b)==rec['bytes'] and hashlib.sha256(b).hexdigest()==rec['sha256'] and tree[rec['path']]['sha']==rec['git_blob_sha']
 table=pq.read_table(pa.BufferReader(b));assert table.schema.equals(W.TRADE_SCHEMA,check_metadata=False) and table.num_rows==rec['rows']
 d=table.to_pandas()
 for col in ['candidate_id','role','window']:assert (d[col]==rec[col]).all()
 chunks.append(d)
raw=pd.concat(chunks,ignore_index=True);assert len(raw)==265255
assert not raw.duplicated(['candidate_id','role','window','asset','signal_bar']).any()
assert np.allclose(raw.notional,20,rtol=0,atol=1e-12) and np.allclose(raw.cost_dollars,.052,rtol=0,atol=1e-12)
assert np.allclose(raw.gross_dollars-raw.cost_dollars,raw.net_dollars,rtol=0,atol=1e-9)
assert (raw.fill_bar==raw.signal_bar+1).all() and (raw.holding_bars==raw.exit_bar-raw.fill_bar+1).all()
for cov in coverage:
 parts=[x for x in receipts if x['path'] in cov['partition_paths']]
 assert len(parts)==cov['partition_count'] and sum(x['rows'] for x in parts)==cov['trade_rows']
# Load immutable input panels and independently reconstruct all trade fields.
panels_input={}
for inp in scope['input_panels']:
 b=blob(inp['path']);assert hashlib.sha256(b).hexdigest()==inp['sha256'] and len(b)==inp['bytes'];panels_input[inp['asset']]=pq.read_table(pa.BufferReader(b)).to_pandas()
loader=D.load_asset;D.load_asset=lambda work,symbol:panels_input[symbol]
try:panels={s:M.Panel(s) for s in D.ASSETS}
finally:D.load_asset=loader
prefix_checks=0
for p in panels.values():
 for cut in (512,4096,min(10080,len(p.c)-1)):
  prefix=I.build_masks({key:values[:cut] for key,values in p._raw.items()})
  for name in I.SETTINGS_52:
   assert np.array_equal(prefix[name],p.masks[name][:cut]),('prefix causality',p.sym,name,cut)
   prefix_checks+=1
print('PREFIX_CAUSALITY_PASS',prefix_checks,flush=True)
actual_groups={key:g for key,g in raw.groupby(['candidate_id','window'],sort=False)};rebuild=0
for k,cov in enumerate(coverage):
 cid,win,role=cov['candidate_id'],cov['window'],cov['role'];expected=[]
 for sym,p in panels.items():
  trades=A.independent_simulate_window(p.o,p.h,p.l,p.c,p.atr,p.seg,None if cid=='NO-SIGNAL' else p.mask_of(cid),sym,cid,*p.ranges[win])
  expected.extend(W._row(t,cid,role,win,panels) for t in trades)
 actual=actual_groups.get((cid,win),raw.iloc[:0]);assert len(actual)==len(expected)
 if expected:
  a=actual.sort_values(['asset','signal_bar','fill_bar']).reset_index(drop=True);e=pd.DataFrame(expected).sort_values(['asset','signal_bar','fill_bar']).reset_index(drop=True)
  for field in W.TRADE_SCHEMA:
   if pa.types.is_floating(field.type):assert np.allclose(a[field.name],e[field.name],rtol=1e-10,atol=1e-10,equal_nan=True),(cid,win,field.name)
   else:assert a[field.name].equals(e[field.name]),(cid,win,field.name)
 rebuild+=len(actual)
 if (k+1)%100==0:print('REBUILT_GROUPS',k+1,flush=True)
for field in ['signal_time_utc','fill_time_utc','exit_time_utc']:raw[field]=pd.to_datetime(raw[field],utc=True)
# Dollar statistics are recomputed rather than copied from executor summaries.
def describe(d,book=12000.):
 n=len(d);net=d.net_dollars.to_numpy();pos=net[net>0];neg=net[net<0];resolved=int(d.outcome.isin(['target','stop']).sum());target=int((d.outcome=='target').sum())
 wr,lo,hi=S.wilson(target,resolved)
 # Risk is realised P&L ordered by UTC exit, with simultaneous exits aggregated.
 pnl=d.groupby('exit_time_utc').net_dollars.sum().sort_index();cum=pnl.cumsum().to_numpy();eq=np.r_[book,book+cum];peak=np.maximum.accumulate(eq);dd=peak-eq
 day=d.groupby(d.exit_time_utc.dt.floor('D')).net_dollars.sum()
 streak=0
 for _,group in d.groupby(['asset','window']):
  cur=0
  for x in group.sort_values(['exit_time_utc','signal_bar']).net_dollars:
   cur=cur+1 if x<0 else 0;streak=max(streak,cur)
 perasset=d.groupby('asset').net_dollars.sum()
 return dict(n=n,gross=float(d.gross_dollars.sum()),cost=float(d.cost_dollars.sum()),net=float(net.sum()),expectancy=float(net.mean()) if n else np.nan,pf=float(pos.sum()/-neg.sum()) if len(neg) else np.nan,win_net_pct=100*len(pos)/n if n else np.nan,win_target_pct=100*wr,wilson_lo_pct=100*lo,wilson_hi_pct=100*hi,n_target=target,n_stop=int((d.outcome=='stop').sum()),n_timeout=int((d.outcome=='timeout').sum()),avg_win=float(pos.mean()) if len(pos) else np.nan,avg_loss=float(neg.mean()) if len(neg) else np.nan,holding_hours=float(d.holding_bars.mean()*4) if n else np.nan,mae_atr=float(d.mae_atr_r.mean()) if n else np.nan,mfe_atr=float(d.mfe_atr_r.mean()) if n else np.nan,net_atr=float(d.net_atr_r.mean()) if n else np.nan,mdd_realised_dollars=float(dd.max()),mdd_realised_peak_pct=float(np.max(np.divide(dd,peak))*100),worst_realised_day=float(min(0,day.min())) if n else 0,longest_loss_streak=streak,positive_assets=int((perasset>0).sum()),breakeven_atr_ref_pct=float((.5+d.cost_atr.mean()/3)*100) if n else np.nan)
summary=pd.DataFrame([{'candidate':c,**describe(d)} for c,d in raw.groupby('candidate_id')]);summary=summary.sort_values('net',ascending=False)
window_rows=[];asset_rows=[]
for cid in ['NO-SIGNAL',*I.SETTINGS_52]:
 for win,_,_ in M.HALF_YEARS:
  d=actual_groups.get((cid,win),raw.iloc[:0]).copy()
  for col in ['fill_time_utc','exit_time_utc']:d[col]=pd.to_datetime(d[col],utc=True)
  window_rows.append({'candidate':cid,'window':win,**describe(d)})
 for asset in D.ASSETS:
  d=raw[(raw.candidate_id==cid)&(raw.asset==asset)];asset_rows.append({'candidate':cid,'asset':asset,**describe(d,1000.)})
windows=pd.DataFrame(window_rows);assets=pd.DataFrame(asset_rows)
# Registered 7-day / 2000 / seed-84 synchronized bootstrap, using each asset's own UTC fill dates.
candidates=['NO-SIGNAL',*I.SETTINGS_52];inference=[]
for win,start,end in M.HALF_YEARS:
 nd=int((np.datetime64(end)-np.datetime64(start)).astype(int))+1
 chosen=S._sample_index_matrix(np.random.default_rng(84),nd,2000)
 weights=np.zeros((2000,nd),dtype=float)
 for i,row in enumerate(chosen):weights[i]=np.bincount(row,minlength=nd)
 daily=np.zeros((nd,len(candidates)));counts=np.zeros_like(daily)
 for j,cid in enumerate(candidates):
  d=raw[(raw.candidate_id==cid)&(raw.window==win)];ix=(d.fill_time_utc.dt.tz_localize(None).dt.normalize()-pd.Timestamp(start)).dt.days.to_numpy()
  np.add.at(daily[:,j],ix,d.net_dollars);np.add.at(counts[:,j],ix,1)
 den=weights@counts;num=weights@daily
 boot=np.divide(num,den,out=np.full_like(num,np.nan),where=den>0)
 observed=np.divide(daily.sum(0),counts.sum(0),out=np.full(len(candidates),np.nan),where=counts.sum(0)>0)
 rows=[]
 for j,cid in enumerate(candidates):
  vals=boot[:,j];vals=vals[np.isfinite(vals)];diff=boot[:,j]-boot[:,0];diff=diff[np.isfinite(diff)]
  se=float(np.std(vals,ddof=1)) if len(vals)>1 else np.nan
  row={'candidate':cid,'window':win,'n':int(counts[:,j].sum()),'expectancy':observed[j],'lo5':float(np.percentile(vals,5)) if len(vals) else np.nan,'hi95':float(np.percentile(vals,95)) if len(vals) else np.nan,'se':se,'p_approx':float(norm.sf(observed[j]/se)) if se>0 else np.nan,'baseline_delta':observed[j]-observed[0],'paired_lo5':float(np.percentile(diff,5)) if len(diff) else np.nan,'paired_hi95':float(np.percentile(diff,95)) if len(diff) else np.nan}
  rows.append(row)
 adjusted=S.holm([r['p_approx'] if np.isfinite(r['p_approx']) else 1 for r in rows[1:]],70330)
 for row,p in zip(rows[1:],adjusted):row['holm_70330']=p
 inference.extend(rows)
inf=pd.DataFrame(inference);windows=windows.merge(inf,on=['candidate','window','n','expectancy'],how='left') if False else windows.merge(inf.drop(columns=['n','expectancy']),on=['candidate','window'],how='left')
windows['basic_window_gate']=(windows.n>=100)&(windows.pf>=1.3)&(windows.positive_assets>=8)&(windows.lo5>0)&(windows.paired_lo5>0)
summary['positive_windows']=summary.candidate.map(windows.groupby('candidate').net.apply(lambda x:int((x>0).sum())))
summary['basic_gate_windows']=summary.candidate.map(windows.groupby('candidate').basic_window_gate.sum())
summary['holm_positive_windows']=summary.candidate.map(windows.assign(ok=(windows.holm_70330<=.05)&(windows.lo5>0)&(windows.n>=100)).groupby('candidate').ok.sum())
# Reconcile additive/dimensioned fields with the draft tables. Inference and
# pooled timeline/drawdown are evaluated from the raw output above, not endorsed.
draft={}
for kind in ['metrics_raw','metrics_by_asset','metrics']:
 draft[kind]=pd.concat([pq.read_table(pa.BufferReader(blob(p))).to_pandas() for p in rows_under(kind)],ignore_index=True)
 assert not draft[kind].duplicated(['candidate_id','role','window','asset']).any()
 assert len(draft[kind])=={'metrics_raw':636,'metrics_by_asset':7632,'metrics':8268}[kind]
mismatch=[]
for rec in draft['metrics_raw'].itertuples():
 d=raw[(raw.candidate_id==rec.candidate_id)&(raw.window==rec.window)]
 for col,expected in [('n_exec',len(d)),('net_dollars',d.net_dollars.sum()),('gross_dollars',d.gross_dollars.sum()),('cost_dollars',d.cost_dollars.sum())]:
  if not np.isclose(getattr(rec,col),expected,rtol=1e-10,atol=1e-10):mismatch.append([rec.candidate_id,rec.window,col])
assert not mismatch
# Compare draft inferential and risk fields with the corrected UTC exit-based view.
check=draft['metrics_raw'].merge(windows,left_on=['candidate_id','window'],right_on=['candidate','window'],suffixes=('_draft','_lead'))
comparison={'draft_summary_missing_baseline':int(check.baseline_win_rate.isna().sum()),
 'draft_summary_null_adjusted_p':int(check.p_adjusted.isna().sum()),
 'draft_ci_lower_differences':int((~np.isclose(check.ci_lo.astype(float),check.lo5.astype(float),rtol=1e-9,atol=1e-9,equal_nan=True)).sum()),
 'draft_risk_dollar_differences':int((~np.isclose(-check.mdd_dollars,check.mdd_realised_dollars,rtol=1e-9,atol=1e-9)).sum()),
 'risk_basis':'Lead: chronological UTC exit bars, simultaneous exits pooled, $12000 total for 12 independent $1000 books. Draft uses fill-bar order and $1000 pooled denominator. Neither is mark-to-market.'}
(ROOT/'draft_comparison.json').write_text(json.dumps(comparison,indent=2))
# Export small derived tables, never another copy of the full raw ledger.
summary.to_csv(ROOT/'summary.csv',index=False);windows.to_csv(ROOT/'windows.csv',index=False);assets.to_csv(ROOT/'assets.csv',index=False)
period_rows=[]
for cid,d in raw.groupby('candidate_id'):
 for label,mask in [('2021 descriptive',d.window.str.startswith('2021')),('2022 development',d.window.str.startswith('2022')),('2023-2026 historical outer',d.window>='2023H1')]:
  period_rows.append({'candidate':cid,'period':label,**describe(d[mask])})
pd.DataFrame(period_rows).to_csv(ROOT/'periods.csv',index=False)
raw.groupby(['candidate_id',raw.exit_time_utc.dt.year]).net_dollars.agg(['count','sum']).reset_index().to_csv(ROOT/'years.csv',index=False)
recon={'status':'PASS','head':HEAD,'raw_parts':len(receipts),'rows':len(raw),'groups':len(coverage),'zero_groups':[x for x in coverage if x['trade_rows']==0],'receipt_shards':len(pointers),'independently_rebuilt_trade_rows':rebuild,'prefix_causality_checks':prefix_checks,'numeric_fields_tolerance':{'rtol':1e-10,'atol':1e-10},'receipt_check':'hash/size/schema at fixed delivery head; historical commit membership not separately re-fetched','additive_summary_mismatches':mismatch,'draft_derived_counts':{k:len(v) for k,v in draft.items()},'market_new_experiment':False,'inference':'registered per-window 2000 seven-day synchronized block bootstrap, seed84; normal-approximation p and Holm m70330; not blind evidence'}
(ROOT/'lead_audit.json').write_text(json.dumps(recon,indent=2))
print(summary[['candidate','n','net','pf','expectancy','positive_windows','positive_assets','basic_gate_windows','holm_positive_windows']].head(12).to_string(index=False),flush=True)
print('LEAD_AUDIT_FINISHED',flush=True)
