"""Fixed synthetic-only runner. No market source, download option, or input-file writer exists."""
import argparse,csv,gzip,hashlib,io,json,math,os,struct,sys,time
from datetime import datetime,timezone
from pathlib import Path
from statistics import median
from .register import build_registry
from .classify import aggregate,classify,iso
from .indicators import conditions
from .evaluate import ASSETS,STATES,HORIZONS,JULY_START,AUG_START,attach_states_atr,events_for_asset,iter_score_events,wilson
from .fixture_generator import build_fixture,specification
from .audit import independent_indicator_audit,direct_barrier_audit

WORKSPACE=Path(__file__).resolve().parents[2]
PACKAGE=Path(__file__).resolve().parent
BASE_WORKSPACE_BYTES=34032792
MAX_WORKSPACE=125000000
MAX_TASK_OUTPUT=8000000
CATEGORY_LIMITS={'code':1000000,'results':2000000,'raw':4000000,'logs':1000000}  # R5 section 15 table
ALERT_FIELDS=['asset','state','setting_id','signal_time_utc','entry_time_utc','entry_reference','atr1h','horizon_hours','status','hit_or_fail_minutes','synthetic']
RESULT_FIELDS=['asset','state','setting_id','family','params_json','horizon_hours','alerts_total','censored','n_evaluable','n_success','precision','wilson_lower','wilson_upper','baseline_edge_precision','baseline_daily_precision','delta_vs_edge','delta_vs_daily','median_time_to_hit_minutes','alert_days','synthetic']

def sha256_bytes(b):return hashlib.sha256(b).hexdigest()
def sha256_file(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def workspace_bytes(root=Path('/home/user')):
 total=0
 for d,ds,fs in os.walk(root,followlinks=False):
  for n in fs:
   p=Path(d)/n
   try:
    if p.is_file() and not p.is_symlink():total+=p.stat().st_size
   except OSError:pass
 return total
def task_bytes(root):
 return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file() and not p.is_symlink())
def _category(path):
 """Map each file to the R5 section 15 storage table by purpose; .gz/.bin/checkpoint are raw bitsets or state."""
 p=Path(path);parts=p.parts;n=p.name
 if 'tools' in parts and 'entry_singletons_v1' in parts:return 'code'
 if 'journal' in parts or n in ('LOG.md','HANDOFF.md') or n.startswith('remote-') or 'receipt' in n or 'delivery' in n:return 'logs'
 if n.startswith('fixtures-results') and n.endswith('.gz'):return 'results'
 if n.endswith(('.gz','.bin')) or n=='checkpoint.json':return 'raw'
 return 'results'
def write_budgeted(path,data,root,*,mutable=False):
 path=Path(path);data=bytes(data);root=Path(root)
 if not path.resolve().is_relative_to(root.resolve()):raise ValueError('output path escapes singleton workspace')
 exists=path.exists();old=path.stat().st_size if exists else 0
 if exists and not mutable:
  if sha256_file(path)==sha256_bytes(data):return
  raise ValueError('refusing to overwrite existing non-checkpoint output')
 now=workspace_bytes();delta=len(data)-old
 if now+delta>MAX_WORKSPACE:raise OSError('workspace limit would be exceeded; output refused before write')
 if now-BASE_WORKSPACE_BYTES+delta>MAX_TASK_OUTPUT:raise OSError('R2 task output cap would be exceeded; output refused before write')
 cat=_category(path);used=0
 for p in root.rglob('*'):
  if p.is_file() and not p.is_symlink() and _category(p)==cat:used+=p.stat().st_size
 if used+delta>CATEGORY_LIMITS[cat]:raise OSError(f'{cat} output cap would be exceeded; output refused before write')
 path.parent.mkdir(parents=True,exist_ok=True)
 with open(path,'wb') as f:f.write(data)
 if path.stat().st_size!=len(data):raise OSError('short output write')

def _code_digest():
 h=hashlib.sha256()
 for p in sorted(PACKAGE.glob('*.py')):
  h.update(p.name.encode()+b'\0');h.update(bytes.fromhex(sha256_file(p)))
 return h.hexdigest()
def fingerprint():
 return {'code_sha256':_code_digest(),'scope_sha256':sha256_file(PACKAGE/'scope.json'),'registry_sha256':sha256_file(PACKAGE/'registry.json'),'generator':'singleton-fixture-sines-v2','source_main':'6d0226a03b84656e14b94dd8a37e39332cc2f68f','source_tools':'86304b62bf9c7d0914572e100892fac66f3f09dd'}
def _state_digest(state):return sha256_bytes(json.dumps(state,sort_keys=True,separators=(',',':')).encode())
def save_checkpoint(path,state,root):
 env={'state':state,'sha256':_state_digest(state)}
 write_budgeted(path,(json.dumps(env,sort_keys=True,indent=2)+'\n').encode(),root,mutable=True)
def validate_checkpoint_envelope(env,run_id,fp,out):
 state=env['state']
 if env.get('sha256')!=_state_digest(state):raise ValueError('checkpoint envelope digest mismatch')
 if state.get('run_id')!=run_id or state.get('fingerprint')!=fp:raise ValueError('resume rejected: run-id/code/scope/registry/source fingerprint changed')
 for asset,rec in state.get('completed',{}).items():
  for key in ('alerts_path','masks_path'):
   p=Path(out)/rec[key]
   if not p.is_file() or p.stat().st_size!=rec[key.replace('_path','_bytes')] or sha256_file(p)!=rec[key.replace('_path','_sha256')]:raise ValueError('resume rejected: staged raw bytes changed')
 return state
def load_checkpoint(path,run_id,fp,out):
 env=json.loads(Path(path).read_text(encoding='utf-8'))
 return validate_checkpoint_envelope(env,run_id,fp,out)

def pack_bits(values):
 out=bytearray((len(values)+7)//8)
 for i,v in enumerate(values):
  if v:out[i>>3]|=1<<(i&7)
 return bytes(out)
def _state_code(x):return {'BREAKOUT':1,'PULLBACK':2,'TURN':3}.get(x,0)
def _mask_bytes(asset,bars15,labels,conds,registry):
 meta=json.dumps({'version':1,'asset':asset,'bar_count':len(bars15),'start_utc':iso(bars15[0]['time']) if bars15 else None,'setting_count':len(registry),'setting_order':[r['setting_id'] for r in registry],'state_codes':{'0':'UNCLASSIFIED','1':'BREAKOUT','2':'PULLBACK','3':'TURN'}},sort_keys=True,separators=(',',':')).encode()
 body=b'ESM1'+struct.pack('>I',len(meta))+meta+bytes(_state_code(x) for x in labels)
 for r in registry:body+=pack_bits(conds[r['setting_id']])
 return body

def process_asset(asset,registry,out,run_id,fp,fixture_days=61):
 minutes,input_sha=build_fixture(asset,fixture_days)
 bars15=aggregate(minutes,900);bars60=aggregate(minutes,3600)
 labels,atr,hmap=classify(bars15,bars60);atr_at=[atr[j] if j>=0 else None for j in hmap]
 labels=attach_states_atr(labels,atr_at);conds=conditions(bars15,registry)
 # 20 deterministic causal prefixes include warm-up edges, completed-hour boundaries, and UTC-day boundaries.
 n=len(bars15);rawpos=[0,1,2,3,4,19,20,23,24,55,56,79,80,95,96,191,192,287,288,n-1]
 positions=sorted(set(min(n-1,x) for x in rawpos if n))
 comparisons=0
 for ix in positions:
  pre=bars15[:ix+1];close_time=pre[-1]['time']+900;hrs=[q for q in bars60 if q['time']+3600<=close_time]
  short,_,_=classify(pre,hrs)
  if short[-1]!=labels[ix]:raise AssertionError(f'causal state prefix mismatch {asset}:{ix}')
  pc=conditions(pre,registry)
  for r in registry:
   if pc[r['setting_id']][-1]!=conds[r['setting_id']][ix]:raise AssertionError(f'causal candidate prefix mismatch {asset}:{ix}:{r["setting_id"]}')
   comparisons+=1
 # No hourly value later than the current 15m close may have entered the classifier.
 for i,j in enumerate(hmap):
  if j>=0 and bars60[j]['time']+3600>bars15[i]['time']+900:raise AssertionError('incomplete hourly candle used')
 if any(x not in (None,'BREAKOUT','PULLBACK','TURN') for x in labels):raise AssertionError('overlapping/unrecognized state')
 checks=independent_indicator_audit(bars15)
 if not all(checks.values()):raise AssertionError('independent indicator reference mismatch')
 signals=events_for_asset(asset,minutes,bars15,labels,atr,conds,registry)
 # CSV and masks are compact, one asset at a time; candle arrays never touch disk.
 text=io.StringIO(newline='');writer=csv.DictWriter(text,fieldnames=ALERT_FIELDS,lineterminator='\n');writer.writeheader()
 maskraw=_mask_bytes(asset,bars15,labels,conds,registry);maskgz=gzip.compress(maskraw,compresslevel=9,mtime=0)
 from .evaluate import BarrierIndex,iter_score_events
 tree=BarrierIndex(minutes);sample=[];row_count=0
 for e in iter_score_events(signals,minutes,tree):
  row={'asset':asset,'state':e['state'],'setting_id':e['setting_id'],'signal_time_utc':iso(e['signal_time']),'entry_time_utc':iso(e['entry_time']),'entry_reference':format(e['entry_reference'],'.12g'),'atr1h':format(e['atr1h'],'.12g'),'horizon_hours':e['horizon_hours'],'status':e['status'],'hit_or_fail_minutes':'' if e['hit_or_fail_minutes'] is None else e['hit_or_fail_minutes'],'synthetic':'true'}
  writer.writerow(row);row_count+=1
  if row_count%1201==0 and len(sample)<100:sample.append(e)
 alert_raw=text.getvalue().encode('utf-8');alert_gz=gzip.compress(alert_raw,compresslevel=9,mtime=0)
 barrier_checks=0
 for e in sample:
  rebuilt=direct_barrier_audit(e,minutes)
  if rebuilt!=(e['status'],e['hit_or_fail_minutes']):raise AssertionError(f'independent minute barrier mismatch {asset}')
  barrier_checks+=1
 times_by={m['time']:i for i,m in enumerate(minutes)}
 rec={'input_sha256':input_sha,'minute_rows':len(minutes),'bars15':len(bars15),'bars60':len(bars60),'causal_prefix_positions':positions,'causal_mask_comparisons':comparisons,'indicator_checks':checks,'barrier_checks':barrier_checks,'alert_rows':row_count,'masks_raw_sha256':sha256_bytes(maskraw),'masks_gzip_sha256':sha256_bytes(maskgz),'alerts_raw_sha256':sha256_bytes(alert_raw),'alerts_gzip_sha256':sha256_bytes(alert_gz),'alerts_gzip_bytes':len(alert_gz),'masks_gzip_bytes':len(maskgz)}
 rec['alerts_path']=f'asset-{asset}-fixture-alerts.csv.gz';rec['alerts_sha256']=rec['alerts_gzip_sha256'];rec['alerts_bytes']=len(alert_gz)
 rec['masks_path']=f'asset-{asset}-masks.bin.gz';rec['masks_sha256']=rec['masks_gzip_sha256'];rec['masks_bytes']=len(maskgz)
 write_budgeted(Path(out)/rec['alerts_path'],alert_gz,WORKSPACE)
 write_budgeted(Path(out)/rec['masks_path'],maskgz,WORKSPACE)
 del signals,conds,labels,atr_at,atr,hmap,bars15,bars60,minutes,tree,alert_raw,maskraw,alert_gz,maskgz,text,writer
 return rec

def _parse_utc_day(t):return int(datetime.fromisoformat(t.replace('Z','+00:00')).timestamp())//86400

def summarize_raw(out,registry):
 lookup={r['setting_id']:r for r in registry};stats={}
 for asset in ASSETS:
  path=Path(out)/f'asset-{asset}-fixture-alerts.csv.gz'
  with gzip.open(path,'rt',encoding='utf-8',newline='') as f:
   for e in csv.DictReader(f):
    key=(asset,e['state'],e['setting_id'],int(e['horizon_hours']))
    s=stats.setdefault(key,{'alerts_total':0,'censored':0,'n_evaluable':0,'n_success':0,'success_times':[],'days':set()})
    s['alerts_total']+=1;s['days'].add(_parse_utc_day(e['signal_time_utc']))
    if e['status']=='CENSORED':s['censored']+=1
    else:
     s['n_evaluable']+=1
     if e['status']=='SUCCESS':s['n_success']+=1;s['success_times'].append(int(e['hit_or_fail_minutes']))
 base={}
 for (a,state,sid,h),s in stats.items():
  if sid.startswith('BASELINE__'):base[(a,state,h,sid)]=s['n_success']/s['n_evaluable'] if s['n_evaluable'] else None
 rows=[]
 for a in ASSETS:
  for state in STATES:
   candidates=[(r['setting_id'],r['family'],json.dumps(r['params'],sort_keys=True,separators=(',',':'))) for r in registry]
   candidates += [('BASELINE__STATE_EDGE','STATE_EDGE','{}'),('BASELINE__STATE_DAILY','STATE_DAILY','{}')]
   for sid,fam,pjson in candidates:
    for h in HORIZONS:
     s=stats.get((a,state,sid,h),{'alerts_total':0,'censored':0,'n_evaluable':0,'n_success':0,'success_times':[],'days':set()})
     n=s['n_evaluable'];k=s['n_success'];p=k/n if n else None;lo,hi=wilson(k,n)
     edge=base.get((a,state,h,'BASELINE__STATE_EDGE'));daily=base.get((a,state,h,'BASELINE__STATE_DAILY'))
     rows.append({'asset':a,'state':state,'setting_id':sid,'family':fam,'params_json':pjson,'horizon_hours':h,'alerts_total':s['alerts_total'],'censored':s['censored'],'n_evaluable':n,'n_success':k,'precision':p,'wilson_lower':lo,'wilson_upper':hi,'baseline_edge_precision':edge,'baseline_daily_precision':daily,'delta_vs_edge':None if p is None or edge is None else p-edge,'delta_vs_daily':None if p is None or daily is None else p-daily,'median_time_to_hit_minutes':median(s['success_times']) if s['success_times'] else None,'alert_days':len(s['days']),'synthetic':True})
 if len(rows)!=4104:raise AssertionError('fixed summary row count mismatch')
 return rows

def _csv_bytes(rows,fields):
 text=io.StringIO(newline='');w=csv.DictWriter(text,fieldnames=fields,lineterminator='\n',extrasaction='ignore');w.writeheader();w.writerows(rows);return text.getvalue().encode('utf-8')

def _checkpoint_envelope(state):return {'state':state,'sha256':_state_digest(state)}

def run_pipeline(run_id,out,*,resume=False,stop_after_assets=None,fixture_days=61):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);registry=build_registry();fp=fingerprint();cp=out/'checkpoint.json'
 if resume:
  if not cp.is_file():raise ValueError('resume requires existing checkpoint')
  state=load_checkpoint(cp,run_id,fp,out)
  if state.get('fixture_days')!=fixture_days:raise ValueError('resume rejected: fixture length changed')
 else:
  preexisting=[p.name for p in out.iterdir() if p.name not in ('runtime.json',)]
  if preexisting:raise FileExistsError('output contains prior run artifacts; resume only with the same run-id')
  state={'run_id':run_id,'fingerprint':fp,'fixture':specification(fixture_days),'fixture_days':fixture_days,'completed':{},'market_run':False,'synthetic':True}
  save_checkpoint(cp,state,WORKSPACE)
 done=list(state['completed'])
 for asset in ASSETS:
  if asset in done:continue
  rec=process_asset(asset,registry,out,run_id,fp,fixture_days)
  state['completed'][asset]=rec
  save_checkpoint(cp,state,WORKSPACE)
  done.append(asset)
  if stop_after_assets and len(done)>=stop_after_assets:return {'status':'PAUSED','run_id':run_id,'completed':done,'summary_rows':None,'market_run':False}
 rows=summarize_raw(out,registry)
 results=_csv_bytes(rows,RESULT_FIELDS)
 write_budgeted(out/'fixtures-results.csv',results,WORKSPACE)
 # Independent audit re-aggregates the compact raw alert streams separately.
 from .audit import independent_rebuild_from_files
 audit=independent_rebuild_from_files(rows,[out/f'asset-{a}-fixture-alerts.csv.gz' for a in ASSETS])
 indicator_checks=sum(len(r['indicator_checks']) for r in state['completed'].values())
 causal_positions=sum(len(r['causal_prefix_positions']) for r in state['completed'].values())
 causal_masks=sum(r['causal_mask_comparisons'] for r in state['completed'].values())
 barrier_checks=sum(r['barrier_checks'] for r in state['completed'].values())
 if audit['status']!='PASS':raise AssertionError('independent raw-to-summary audit failed')
 source_hashes={'source_main':'6d0226a03b84656e14b94dd8a37e39332cc2f68f','source_tools':'86304b62bf9c7d0914572e100892fac66f3f09dd','scope_sha256':fp['scope_sha256'],'registry_sha256':fp['registry_sha256'],'code_sha256':fp['code_sha256']}
 audit.update({'status':'PASS','source_hashes':source_hashes,'rows_rebuilt':4104,'zero_rows':sum(r['alerts_total']==0 for r in rows),'independent_indicator_checks':indicator_checks,'barrier_checks':barrier_checks,'causal_prefix_checks':causal_positions,'causal_mask_comparisons':causal_masks,'checkpoint_checks':'checkpoint digest and staged-byte hashes verified','exceptions':[],'synthetic':True,'market_run':False})
 audit_bytes=(json.dumps(audit,indent=2,sort_keys=True)+'\n').encode();write_budgeted(out/'audit.json',audit_bytes,WORKSPACE)
 manifest={'status':'SYNTHETIC_FIXTURE_COMPLETE','run_id':run_id,'synthetic':True,'market_run':False,'fixture':specification(fixture_days),'assets':{a:state['completed'][a] for a in ASSETS},'settings':226,'candidate_cells':2034,'candidate_summary_rows':4068,'baseline_summary_rows':36,'summary_rows':len(rows),'alert_horizon_rows':sum(x['alerts_total'] for x in rows),'source':fp}
 mbytes=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode();write_budgeted(out/'run-manifest.json',mbytes,WORKSPACE)
 return {'status':'COMPLETE','run_id':run_id,'summary_rows':len(rows),'alerts':manifest['alert_horizon_rows'],'audit':audit,'manifest':manifest}

def main(argv=None):
 ap=argparse.ArgumentParser(description='Fixed, deterministic synthetic-only single-indicator fixture. Market mode is unavailable.')
 ap.add_argument('--synthetic',action='store_true',required=True,help='required synthetic-only mode')
 ap.add_argument('--no-source-download',action='store_true',required=True,help='required; prohibits source or market downloads')
 ap.add_argument('--run-id',required=True);ap.add_argument('--out',required=True);ap.add_argument('--resume',action='store_true')
 ap.add_argument('--stop-after-assets',type=int,help=argparse.SUPPRESS);ap.add_argument('--fixture-days',type=int,default=61,help=argparse.SUPPRESS)
 a=ap.parse_args(argv);root=Path(a.out).resolve()
 if not root.is_relative_to(WORKSPACE.resolve()):raise SystemExit('output must remain inside the assigned workspace')
 if a.fixture_days<2 or a.fixture_days>61:raise SystemExit('fixture test days must be in [2,61]')
 res=run_pipeline(a.run_id,root,resume=a.resume,stop_after_assets=a.stop_after_assets,fixture_days=a.fixture_days)
 print(json.dumps({k:v for k,v in res.items() if k not in ('audit','manifest')},sort_keys=True))
 return 0
if __name__=='__main__':raise SystemExit(main())
