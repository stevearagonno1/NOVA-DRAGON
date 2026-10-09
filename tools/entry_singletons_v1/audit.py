"""Independent scalar and raw-to-summary audit.
FOREIGN_SOURCE: audit boundary cases reference the task's pinned pilot/math sources, but calculations here are separate scalar implementations.
"""
import hashlib, json, math, csv
from pathlib import Path
from .indicators import ema, rsi, cci, mfi, cmf, aroon, adx

def _direct_wilder(x,n):
 out=[None]*len(x); good=[]; prev=None
 for i,v in enumerate(x):
  if v is None: good=[]; prev=None; continue
  if prev is None:
   good.append(v)
   if len(good)==n: prev=sum(good)/n; out[i]=prev
  else: prev=(prev*(n-1)+v)/n; out[i]=prev
 return out

def _direct_ema(x,n):
 out=[None]*len(x); val=None; seen=0
 for i in range(len(x)):
  q=x[i]
  if q is None: val=None; seen=0; continue
  val=q if val is None else val* (1-2/(n+1))+q*2/(n+1); seen+=1
  if seen>=n:out[i]=val
 return out

def _direct_rsi(c,n):
 d=[None]+[c[i]-c[i-1] for i in range(1,len(c))]
 g=[None if x is None else max(x,0) for x in d]; l=[None if x is None else max(-x,0) for x in d]
 a=_direct_wilder(g,n); b=_direct_wilder(l,n); out=[None]*len(c)
 for i in range(len(c)):
  if a[i] is not None and b[i] is not None:out[i]=50 if a[i]==b[i]==0 else 100 if b[i]==0 else 100-100/(1+a[i]/b[i])
 return out

def _direct_cci(b,n):
 tp=[(x['high']+x['low']+x['close'])/3 for x in b]; out=[None]*len(b)
 for i in range(n-1,len(b)):
  w=tp[i-n+1:i+1]; m=sum(w)/n; d=sum(abs(x-m) for x in w)/n
  if d:out[i]=(tp[i]-m)/(.015*d)
 return out

def _direct_mfi(b,n):
 tp=[(x['high']+x['low']+x['close'])/3 for x in b]; v=[x['volume'] for x in b]; out=[None]*len(b)
 p=[0.0]*len(b); m=[0.0]*len(b)
 for i in range(1,len(b)):
  if tp[i]>tp[i-1]:p[i]=tp[i]*v[i]
  elif tp[i]<tp[i-1]:m[i]=tp[i]*v[i]
 for i in range(n,len(b)):
  a=sum(p[i-n+1:i+1]); z=sum(m[i-n+1:i+1]); out[i]=50 if a==z==0 else 100 if z==0 else 100-100/(1+a/z)
 return out

def _direct_cmf(b,n):
 mf=[]; vol=[]
 for x in b:
  r=x['high']-x['low']; mf.append(0 if r==0 else ((2*x['close']-x['high']-x['low'])/r)*x['volume']); vol.append(x['volume'])
 out=[None]*len(b)
 for i in range(n-1,len(b)):
  v=sum(vol[i-n+1:i+1]);
  if v:out[i]=sum(mf[i-n+1:i+1])/v
 return out

def _direct_aroon(b,n):
 u=[None]*len(b); d=[None]*len(b)
 for i in range(n,len(b)):
  hh=[x['high'] for x in b[i-n:i+1]]; ll=[x['low'] for x in b[i-n:i+1]]
  u[i]=100*max(j for j,x in enumerate(hh) if x==max(hh))/n
  d[i]=100*max(j for j,x in enumerate(ll) if x==min(ll))/n
 return u,d

def _direct_adx(b,n):
 tr=[]; p=[0.0]*len(b); m=[0.0]*len(b)
 for i,x in enumerate(b):
  tr.append(x['high']-x['low'] if i==0 else max(x['high']-x['low'],abs(x['high']-b[i-1]['close']),abs(x['low']-b[i-1]['close'])))
  if i:
   u=x['high']-b[i-1]['high']; d=b[i-1]['low']-x['low']
   p[i]=u if u>d and u>0 else 0.0; m[i]=d if d>u and d>0 else 0.0
 at=_direct_wilder(tr,n); pp=_direct_wilder(p,n); mm=_direct_wilder(m,n); dx=[None]*len(b)
 for i in range(len(b)):
  if at[i] is not None and at[i]>0:
   pi=100*pp[i]/at[i]; mi=100*mm[i]/at[i]; den=pi+mi; dx[i]=0 if den==0 else 100*abs(pi-mi)/den
 return _direct_wilder(dx,n)

def _series_equal(a,b,tol=1e-10):
 if len(a)!=len(b):return False
 for x,y in zip(a,b):
  if x is None or y is None:
   if x is not y:return False
  elif not math.isclose(x,y,rel_tol=tol,abs_tol=tol):return False
 return True

def independent_indicator_audit(bars):
 c=[x['close'] for x in bars]; checks={}
 checks['EMA']=_series_equal(ema(c,14),_direct_ema(c,14))
 checks['RSI']=_series_equal(rsi(c,14),_direct_rsi(c,14))
 checks['CCI']=_series_equal(cci(bars,14),_direct_cci(bars,14))
 checks['MFI']=_series_equal(mfi(bars,14),_direct_mfi(bars,14))
 checks['CMF']=_series_equal(cmf(bars,14),_direct_cmf(bars,14))
 a=aroon(bars,14); z=_direct_aroon(bars,14); checks['Aroon']=_series_equal(a[0],z[0]) and _series_equal(a[1],z[1])
 checks['ADX']=_series_equal(adx(bars,14)[0],_direct_adx(bars,14))
 return checks

def audit_summary(rows,events,expected=4104):
 from statistics import median
 if len(rows)!=expected: raise AssertionError(f'summary count {len(rows)} != {expected}')
 ids={(r['asset'],r['state'],r['setting_id'],r['horizon_hours']) for r in rows}
 if len(ids)!=expected:raise AssertionError('duplicate summary key')
 grouped={}
 for e in events:grouped.setdefault((e['asset'],e['state'],e['setting_id'],e['horizon_hours']),[]).append(e)
 base={}
 for r in rows:
  arr=grouped.get((r['asset'],r['state'],r['setting_id'],r['horizon_hours']),[])
  n=sum(x['status']!='CENSORED' for x in arr);k=sum(x['status']=='SUCCESS' for x in arr);c=sum(x['status']=='CENSORED' for x in arr);p=k/n if n else None
  z=1.959963984540054
  if n:
   den=1+z*z/n; mid=(p+z*z/(2*n))/den; half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den;lo=max(0,mid-half);hi=min(1,mid+half)
  else:lo=hi=None
  times=[x['hit_or_fail_minutes'] for x in arr if x['status']=='SUCCESS' and x['hit_or_fail_minutes'] is not None]
  fields={'alerts_total':len(arr),'censored':c,'n_evaluable':n,'n_success':k,'precision':p,'wilson_lower':lo,'wilson_upper':hi,'alert_days':len({x['signal_time']//86400 for x in arr}),'median_time_to_hit_minutes':median(times) if times else None}
  for key,val in fields.items():
   got=r[key]
   if val is None:
    if got is not None:raise AssertionError(f'{key} should be null')
   elif isinstance(val,float):
    if got is None or not math.isclose(got,val,rel_tol=1e-12,abs_tol=1e-12):raise AssertionError(f'{key} reconstruction mismatch')
   elif got!=val:raise AssertionError(f'{key} reconstruction mismatch')
  if r['setting_id'].startswith('BASELINE__'):base[(r['asset'],r['state'],r['horizon_hours'],r['setting_id'])]=p
 for r in rows:
  a,s,h=r['asset'],r['state'],r['horizon_hours'];p=r['precision']
  for field,name in [('baseline_edge_precision','BASELINE__STATE_EDGE'),('baseline_daily_precision','BASELINE__STATE_DAILY')]:
   val=base.get((a,s,h,name))
   if val is None and r[field] is not None:raise AssertionError('baseline null mismatch')
   if val is not None and (r[field] is None or not math.isclose(val,r[field],rel_tol=1e-12,abs_tol=1e-12)):raise AssertionError('baseline mismatch')
  for field,bf in [('delta_vs_edge','baseline_edge_precision'),('delta_vs_daily','baseline_daily_precision')]:
   val=None if p is None or r[bf] is None else p-r[bf]
   if val is None and r[field] is not None:raise AssertionError('delta null mismatch')
   if val is not None and (r[field] is None or not math.isclose(val,r[field],abs_tol=1e-12)):raise AssertionError('delta mismatch')
 return {'rows_rebuilt':len(rows),'zero_rows':sum(r['alerts_total']==0 for r in rows),'status':'PASS'}

def direct_barrier_audit(event,minutes):
 """Unoptimized minute-by-minute verifier, algorithmically distinct from the tree runner."""
 start=event['entry_time']; horizon=event['horizon_hours']; deadline=start+horizon*3600
 if deadline>1785542400:return ('CENSORED',None)
 idx=event.get('_minute_index')
 if idx is None or idx>=len(minutes) or minutes[idx]['time']!=start:
  import bisect
  idx=bisect.bisect_left([m['time'] for m in minutes],start)
  if idx>=len(minutes) or minutes[idx]['time']!=start:idx=None
 if idx is None or minutes[-1]['time']+60<deadline:return ('CENSORED',None)
 target,stop=(2,-1) if horizon==24 else (4,-2); upper=event['entry_reference']+target*event['atr1h']; lower=event['entry_reference']+stop*event['atr1h']
 for m in minutes[idx:idx+horizon*60]:
  if m['low']<=lower:return ('FAIL',(m['time']-start)//60)
  if m['high']>=upper:return ('SUCCESS',(m['time']-start)//60)
 return ('FAIL',horizon*60)


def independent_rebuild_from_files(rows,files):
 """Independently stream the compressed raw rows and verify their 4,104 aggregates."""
 import gzip
 from datetime import datetime
 from statistics import median
 expected=4104
 keys=[(r['asset'],r['state'],r['setting_id'],int(r['horizon_hours'])) for r in rows]
 if len(rows)!=expected or len(set(keys))!=expected:raise AssertionError('independent rebuild received a noncanonical summary grid')
 grouped={}; raw_count=0
 for path in files:
  with gzip.open(path,'rt',encoding='utf-8',newline='') as f:
   for e in csv.DictReader(f):
    if e.get('synthetic')!='true':raise AssertionError('non-synthetic raw row')
    k=(e['asset'],e['state'],e['setting_id'],int(e['horizon_hours']))
    s=grouped.setdefault(k,{'total':0,'censored':0,'n':0,'success':0,'times':[],'days':set()})
    raw_count+=1;s['total']+=1
    s['days'].add(int(datetime.fromisoformat(e['signal_time_utc'].replace('Z','+00:00')).timestamp())//86400)
    if e['status']=='CENSORED':s['censored']+=1
    elif e['status'] in ('SUCCESS','FAIL'):
     s['n']+=1
     if e['status']=='SUCCESS':
      s['success']+=1;s['times'].append(int(e['hit_or_fail_minutes']))
    else:raise AssertionError('unrecognized raw outcome')
 def wilson_ref(k,n):
  if not n:return None,None
  z=1.959963984540054;p=k/n;den=1+z*z/n;mid=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
  return max(0.0,mid-half),min(1.0,mid+half)
 bykey={}
 for r in rows:
  k=(r['asset'],r['state'],r['setting_id'],int(r['horizon_hours']));s=grouped.get(k,{'total':0,'censored':0,'n':0,'success':0,'times':[],'days':set()})
  n=s['n'];success=s['success'];precision=success/n if n else None;lo,hi=wilson_ref(success,n)
  actual={'alerts_total':s['total'],'censored':s['censored'],'n_evaluable':n,'n_success':success,'precision':precision,'wilson_lower':lo,'wilson_upper':hi,'median_time_to_hit_minutes':median(s['times']) if s['times'] else None,'alert_days':len(s['days'])}
  for f,v in actual.items():
   got=r[f]
   if v is None:
    if got is not None:raise AssertionError(f'independent summary {f} expected null')
   elif isinstance(v,float):
    if got is None or not math.isclose(float(got),v,rel_tol=1e-12,abs_tol=1e-12):raise AssertionError(f'independent summary {f} mismatch')
   elif int(got)!=v:raise AssertionError(f'independent summary {f} mismatch')
  bykey[k]=r
 baselines={}
 for k,r in bykey.items():
  if k[2].startswith('BASELINE__'):baselines[(k[0],k[1],k[3],k[2])]=r['precision']
 for k,r in bykey.items():
  a,state,_,h=k
  for field,bid in (('baseline_edge_precision','BASELINE__STATE_EDGE'),('baseline_daily_precision','BASELINE__STATE_DAILY')):
   v=baselines.get((a,state,h,bid))
   if v is None:
    if r[field] is not None:raise AssertionError('independent baseline mismatch')
   elif r[field] is None or not math.isclose(float(r[field]),v,rel_tol=1e-12,abs_tol=1e-12):raise AssertionError('independent baseline mismatch')
  for field,bf in (('delta_vs_edge','baseline_edge_precision'),('delta_vs_daily','baseline_daily_precision')):
   v=None if r['precision'] is None or r[bf] is None else r['precision']-r[bf]
   if v is None:
    if r[field] is not None:raise AssertionError('independent delta mismatch')
   elif r[field] is None or not math.isclose(float(r[field]),v,rel_tol=1e-12,abs_tol=1e-12):raise AssertionError('independent delta mismatch')
 return {'status':'PASS','rows_rebuilt':len(rows),'raw_alert_rows':raw_count,'zero_rows':sum(int(r['alerts_total'])==0 for r in rows),'method':'separate gzip stream aggregation and scalar Wilson reconstruction'}

