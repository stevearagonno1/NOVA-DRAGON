"""Standard-library-only acceptance, boundaries, restart, tamper and publisher transport tests."""
import copy,csv,gzip,hashlib,json,math,os
from pathlib import Path
from .register import build_registry,EXPECTED
from .classify import normalize_open_time,read_rows,aggregate
from .indicators import ema,rsi,stochastic,williams,mfi,cmf,aroon,adx,conditions
from .evaluate import JULY_START,BarrierIndex,label_signal
from .audit import direct_barrier_audit
from .run import (WORKSPACE,PACKAGE,ASSETS,RESULT_FIELDS,validate_checkpoint_envelope,_state_digest,run_pipeline,sha256_file,workspace_bytes,BASE_WORKSPACE_BYTES,MAX_WORKSPACE,MAX_TASK_OUTPUT)

def require(ok,message):
 if not ok:raise AssertionError(message)
def throws(fn,fragment):
 try:fn()
 except Exception as e:
  require(fragment.lower() in str(e).lower(),f'wrong error: {e}')
  return
 raise AssertionError(f'expected error containing {fragment!r}')
def bars(n,close=100.0,volume=0.0):
 return [{'time':JULY_START+i*60,'open':close,'high':close,'low':close,'close':close,'volume':volume} for i in range(n)]
def barrier_fixture(touch=None):
 out=bars(24*60,close=100.0,volume=1.0)
 if touch:
  at,kind=touch
  if kind in ('SUCCESS','BOTH'):out[at]['high']=102.0
  if kind in ('FAIL','BOTH'):out[at]['low']=99.0
 e={'entry_time':JULY_START,'horizon_hours':24,'entry_reference':100.0,'atr1h':1.0,'_minute_index':0}
 return out,e

def run_tests():
 checks={}
 reg=build_registry();ids=[x['setting_id'] for x in reg]
 require(len(reg)==226 and len(set(ids))==226,'226 unique settings')
 require(sum(EXPECTED.values())==226 and len(EXPECTED)==17,'17 fixed family counts')
 require(226*3*3==2034 and 2034*2+36==4104,'fixed matrix arithmetic')
 checks['registry']='PASS'
 # Exact unit conversion is explicit; no magnitude guessing.
 ts=JULY_START
 require(normalize_open_time(ts,'seconds')==ts,'seconds conversion')
 require(normalize_open_time(ts*1000,'milliseconds')==ts,'millisecond conversion')
 require(normalize_open_time(ts*1000000,'microseconds')==ts,'microsecond conversion')
 throws(lambda:normalize_open_time(ts*1000+1,'seconds'),'minute aligned')
 throws(lambda:normalize_open_time(ts,'guessed'),'unit')
 checks['time_units']='PASS'
 # Constant price/volume zero, zero range, incomplete windows, tied extremes, and Wilder edge cases.
 flat=bars(70,close=100.0,volume=0.0);c=[x['close'] for x in flat]
 rr=rsi(c,14);require(all(x is None for x in rr[:14]) and all(abs(x-50)<1e-12 for x in rr[14:]),'flat RSI zero-gain/zero-loss convention')
 require(all(x is None for x in stochastic(flat,14)) and all(x is None for x in williams(flat,14)),'zero price range is invalid')
 require(all(x is None for x in cmf(flat,14)),'zero volume CMF is invalid')
 mf=mfi(flat,14);require(mf[13] is None and all(x==50 for x in mf[14:]),'zero-flow MFI convention')
 e=ema(c,14);require(all(x is None for x in e[:13]) and e[13]==100,'EMA warmup')
 aroon_up,aroon_dn=aroon(flat,14);require(aroon_up[14]==100 and aroon_dn[14]==100,'Aroon latest tie wins')
 ad,pi,mi=adx(flat,14);require(all(x is None for x in ad) and all(x is None for x in pi),'zero ATR makes ADX invalid')
 require(all(x is None for x in ema([1.0,2.0,None,3.0,4.0],3)[:5]),'missing EMA values reset warmup')
 checks['indicator_boundaries']='PASS'
 # Reader validation preserves strict continuity and rejects malformed OHLCV.
 good=[{'open_time_seconds':ts+i*60,'open':1,'high':2,'low':0.5,'close':1.5,'volume':0} for i in range(3)]
 require(len(read_rows(good))==3,'reader accepts valid zero-volume stream')
 throws(lambda:read_rows([good[0],{**good[1],'open_time_seconds':good[1]['open_time_seconds']+60}]),'duplicate or missing')
 throws(lambda:read_rows([{**good[0],'high':0.25}]),'invalid OHLCV')
 require(len(aggregate(read_rows(good),180))==1 and len(aggregate(read_rows(good[:2]),180))==0,'only complete buckets aggregate')
 checks['reader_and_buckets']='PASS'
 # Labels: success, fail, no-hit, incomplete horizon and adverse-first same-minute dual touch.
 for name,touch,expected,expected_min in [('success',(17,'SUCCESS'),'SUCCESS',17),('fail',(3,'FAIL'),'FAIL',3),('both',(8,'BOTH'),'FAIL',8),('nohit',None,'FAIL',1440)]:
  minute_rows,event=barrier_fixture(touch);status,mins=label_signal(event,minute_rows,24,2,-1,BarrierIndex(minute_rows))
  require((status,mins)==(expected,expected_min),f'barrier {name} production result')
  require(direct_barrier_audit(event,minute_rows)==(expected,expected_min),f'barrier {name} independent reference')
 minute_rows,event=barrier_fixture();require(label_signal(event,minute_rows[:100],24,2,-1,BarrierIndex(minute_rows[:100]))==('CENSORED',None),'incomplete horizon censored')
 late=JULY_START+(31*24*60-60)*60
 minute_rows=bars(24*60,close=100,volume=1);event={'entry_time':late,'horizon_hours':24,'entry_reference':100,'atr1h':1,'_minute_index':0}
 require(label_signal(event,minute_rows,24,2,-1,BarrierIndex(minute_rows))==('CENSORED',None),'horizon past August boundary censored')
 checks['barriers']='PASS'
 # Required production fixture has completed; verify full grid, zero rows and synthetic-only status.
 out=WORKSPACE/'run-r4';runid='singleton-package-fixture-r4';result_path=out/'fixtures-results.csv';audit_path=out/'audit.json';cp=out/'checkpoint.json'
 require(result_path.is_file() and audit_path.is_file() and cp.is_file(),'prescribed synthetic run artifacts exist')
 require(not (WORKSPACE/'run/fixtures-results.csv').exists(),'R3 duplicate CSV removed after verified gzip')
 with result_path.open(newline='',encoding='utf-8') as f:
  rows=list(csv.DictReader(f))
 require(len(rows)==4104 and tuple(rows[0])==tuple(RESULT_FIELDS),'4,104 summary rows and schema')
 keys={(r['asset'],r['state'],r['setting_id'],r['horizon_hours']) for r in rows};require(len(keys)==4104,'no duplicate summary key')
 zeros=[r for r in rows if int(r['alerts_total'])==0]
 require(bool(zeros),'zero-result rows retained')
 require(all(r['precision']=='' and r['wilson_lower']=='' and r['wilson_upper']=='' for r in zeros if int(r['n_evaluable'])==0),'n=0 precision and Wilson are null, not zero')
 audit=json.loads(audit_path.read_text());manifest=json.loads((out/'run-manifest.json').read_text())
 require(audit['status']=='PASS' and audit['rows_rebuilt']==4104 and audit['synthetic'] and not audit['market_run'],'independent audit status')
 require(manifest['settings']==226 and manifest['candidate_cells']==2034 and manifest['summary_rows']==4104 and manifest['synthetic'] and not manifest['market_run'],'manifest fixed counts')
 require(all(manifest['assets'][a]['minute_rows']==87840 for a in ASSETS),'in-memory fixture dimensions')
 checks['production_grid']='PASS'
 # Reopening a completed checkpoint is an actual no-loss resume path; bytes stay identical.
 before=sha256_file(result_path);again=run_pipeline(runid,out,resume=True,fixture_days=61);require(again['status']=='COMPLETE' and sha256_file(result_path)==before,'completed checkpoint resume')
 checks['completed_resume']='PASS'
 # Deliberate in-memory tamper models: envelope/checkpoint, code, scope, and raw staged digest must reject.
 env=json.loads(cp.read_text());base=env['state'];fp=base['fingerprint']
 bad=copy.deepcopy(env);bad['sha256']='0'*64;throws(lambda:validate_checkpoint_envelope(bad,runid,fp,out),'checkpoint envelope digest')
 changed_code=dict(fp);changed_code['code_sha256']='0'*64;throws(lambda:validate_checkpoint_envelope(env,runid,changed_code,out),'fingerprint changed')
 changed_scope=dict(fp);changed_scope['scope_sha256']='0'*64;throws(lambda:validate_checkpoint_envelope(env,runid,changed_scope,out),'fingerprint changed')
 raw=copy.deepcopy(base);first=next(iter(raw['completed']));raw['completed'][first]['alerts_sha256']='0'*64;tampered={'state':raw,'sha256':_state_digest(raw)};throws(lambda:validate_checkpoint_envelope(tampered,runid,fp,out),'staged raw bytes changed')
 checks['tamper_rejection']='PASS'
 from .gate import tamper_audit
 require(tamper_audit(out)['status']=='PASS','gate tamper audit')
 checks['tamper_audit_gate']='PASS'
 # True interrupted two-stage run on a tiny synthetic fixture, retained under output cap.
 short=out/'resume-contract-r4'
 partial=run_pipeline('singleton-package-resume-test-r4',short,stop_after_assets=1,fixture_days=2)
 require(partial['status']=='PAUSED' and partial['completed']==['BTC'],'pause after first asset')
 cpstate=json.loads((short/'checkpoint.json').read_text())['state'];require(set(cpstate['completed'])=={'BTC'} and cpstate['run_id']=='singleton-package-resume-test-r4','interrupted checkpoint holds exactly the first asset')
 # Full interrupted-then-resumed comparison is run by gate.resume_audit (in memory, no second results CSV).
 checks['interrupted_checkpoint']='PASS'
 # Publication transport tests operate only on in-memory fake responses; no fake write reaches remote.
 from .publish import test_transport
 checks['publisher_transport']=test_transport()
 # Payload scanner: real credential shapes (built at runtime, never stored literally) must be refused;
 # bare prefix words and the publisher's own guard text must pass; exact-secret match still applies.
 from .publish import _safe_payload_scan
 from .publish import _TOKEN_SHAPE_RE
 fake_pat='github_pat_'+'A'*40;fake_gh='ghp_'+'B'*36
 throws(lambda:_safe_payload_scan({'x':fake_pat.encode()},'Z'*40),'token-like')
 throws(lambda:_safe_payload_scan({'x':fake_gh.encode()},'Z'*40),'token-like')
 throws(lambda:_safe_payload_scan({'x':b'value '+('X'*40).encode()},'X'*40),'private credential')
 _safe_payload_scan({'publish.py':(PACKAGE/'publish.py').read_bytes()},'Q'*40)
 _safe_payload_scan({'note':b'guard names ghp_ and github_pat_ alone are not credentials'},'Q'*40)
 require(_TOKEN_SHAPE_RE.search(b'github_pat_') is None,'bare prefix must not match')
 checks['payload_scanner']='PASS'
 # Recalculate the actual whole workspace and output accounting without deleting/relocating files.
 total=workspace_bytes();delta=total-BASE_WORKSPACE_BYTES
 require(total<=MAX_WORKSPACE,f'workspace ceiling: {total}')
 require(delta<=MAX_TASK_OUTPUT,f'R3 local-output ceiling: delta {delta}')
 require(125000000-total>=13000000,f'prepublication 13MB margin: {125000000-total}')
 checks['storage']={'status':'PASS','workspace_bytes':total,'r3_output_bytes':delta,'available_bytes':125000000-total}
 return {'status':'PASS','checks':checks,'checks_passed':len(checks),'market_run':False,'synthetic':True}

def main():
 result=run_tests();print(json.dumps(result,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
