"""Signal timing, minute barriers, resumable batches, and complete fixed summaries."""
import csv, hashlib, json, math, os
from statistics import median
from pathlib import Path
from .classify import iso
from .register import build_registry

ASSETS=('BTC','ETH','SOL'); STATES=('BREAKOUT','PULLBACK','TURN'); HORIZONS=(24,168)
JULY_START=1782864000 # 2026-07-01T00:00:00Z
AUG_START=1785542400 # 2026-08-01T00:00:00Z

def wilson(k,n):
 if n==0:return None,None
 z=1.959963984540054; p=k/n; den=1+z*z/n; mid=(p+z*z/(2*n))/den; half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
 return max(0,mid-half),min(1,mid+half)

class BarrierIndex:
 """Range-maximum/minimum trees return the earliest threshold touch in O(log n)."""
 def __init__(self, bars):
  n=1
  while n<len(bars): n*=2
  self.n=n; self.size=len(bars); self.hmax=[-float('inf')]*(2*n); self.lmin=[float('inf')]*(2*n)
  for i,b in enumerate(bars): self.hmax[n+i]=b['high']; self.lmin[n+i]=b['low']
  for i in range(n-1,0,-1): self.hmax[i]=max(self.hmax[2*i],self.hmax[2*i+1]); self.lmin[i]=min(self.lmin[2*i],self.lmin[2*i+1])
 def first(self, threshold, start, stop, maximum=True):
  tree=self.hmax if maximum else self.lmin
  def visit(node,lo,hi):
   if hi<=start or lo>=stop:return None
   if maximum:
    if tree[node]<threshold:return None
   elif tree[node]>threshold:return None
   if hi-lo==1:return lo if lo<self.size else None
   mid=(lo+hi)//2; a=visit(node*2,lo,mid)
   return a if a is not None else visit(node*2+1,mid,hi)
  return visit(1,0,self.n)

def label_signal(signal, minutes, horizon, target, stop, barrier_index=None):
 """minutes map by open_time; adverse barrier wins a same-minute double touch."""
 start=signal['entry_time']; deadline=start+horizon*3600
 if deadline>AUG_START: return 'CENSORED',None
 idx=signal['_minute_index']
 if idx>=len(minutes) or minutes[idx]['time']!=start or minutes[-1]['time']+60<deadline: return 'CENSORED',None
 entry=signal['entry_reference']; A=signal['atr1h']; up=entry+target*A; dn=entry+stop*A
 if barrier_index is not None:
  end=idx+horizon*60
  ix_up=barrier_index.first(up,idx,end,True); ix_dn=barrier_index.first(dn,idx,end,False)
  if ix_dn is not None and (ix_up is None or ix_dn<=ix_up):return 'FAIL',ix_dn-idx
  if ix_up is not None:return 'SUCCESS',ix_up-idx
  return 'FAIL',horizon*60
 for m in minutes[idx:]:
  if m['time']>=deadline: break
  hit_up=m['high']>=up; hit_dn=m['low']<=dn
  if hit_dn:return 'FAIL',(m['time']-start)//60
  if hit_up:return 'SUCCESS',(m['time']-start)//60
 return 'FAIL',horizon*60

def events_for_asset(asset, minutes, bars15, states, atr60, conditions, registry):
 bytime={r['time']:i for i,r in enumerate(minutes)}; out=[]
 for s in STATES:
  for reg in registry:
   sid=reg['setting_id']; cond=conditions[sid]; prev=False; last=None
   for i,b in enumerate(bars15):
    eligible=states[i]==s and cond[i]
    t=b['time']+900
    if eligible and not prev and t>=JULY_START and t<AUG_START and t in bytime and last is not None and t-last<21600: pass
    elif eligible and not prev and t>=JULY_START and t<AUG_START and t in bytime:
     # ATR attached at this 15m close by the causal state classifier.
     atr_value=states.atr_at_signal[i]
     out.append({'asset':asset,'state':s,'setting_id':sid,'family':reg['family'],'params_json':json.dumps(reg['params'],sort_keys=True,separators=(',',':')),'signal_time':t,'entry_time':t,'entry_reference':minutes[bytime[t]]['open'],'atr1h':atr_value,'_minute_index':bytime[t]})
     last=t
    prev=eligible
 # Baseline state-edge and first-of-UTC-day state daily.
 for s in STATES:
  last={'STATE_EDGE':None,'STATE_DAILY':None}; prev=False; days=set()
  for i,b in enumerate(bars15):
   t=b['time']+900; elig=states[i]==s
   edge=elig and not prev
   day=t//86400
   daily=elig and day not in days
   for base,yes in (('STATE_EDGE',edge),('STATE_DAILY',daily)):
    if yes and t>=JULY_START and t<AUG_START and t in bytime and (last[base] is None or t-last[base]>=21600):
     out.append({'asset':asset,'state':s,'setting_id':'BASELINE__'+base,'family':base,'params_json':'{}','signal_time':t,'entry_time':t,'entry_reference':minutes[bytime[t]]['open'],'atr1h':states.atr_at_signal[i],'_minute_index':bytime[t]})
     last[base]=t
   if daily and elig: days.add(day)
   prev=elig
 return out

def attach_states_atr(states, atr_at):
 class Vec(list): pass
 v=Vec(states); v.atr_at_signal=atr_at; return v

def iter_score_events(events, minutes, barrier_index=None):
 """Yield one outcome at a time so a single asset's labels need not accumulate."""
 barrier_index=barrier_index or BarrierIndex(minutes)
 for e in events:
  for h in HORIZONS:
   target,stop=(2,-1) if h==24 else (4,-2)
   status,mins=label_signal(e,minutes,h,target,stop,barrier_index)
   yield {**e,'horizon_hours':h,'status':status,'hit_or_fail_minutes':mins}

def score_events(events, minutes):
 return list(iter_score_events(events,minutes))

def summarize(outcomes):
 keys={}
 for e in outcomes: keys.setdefault((e['asset'],e['state'],e['setting_id'],e['family'],e['params_json'],e['horizon_hours']),[]).append(e)
 base={}
 for (a,s,sid,_,_,h),arr in keys.items():
  if sid.startswith('BASELINE__'):
   n=sum(x['status']!='CENSORED' for x in arr); k=sum(x['status']=='SUCCESS' for x in arr); base[(a,s,h,sid)]=k/n if n else None
 out=[]
 # Fixed universe preserves zero-result rows.
 reg=build_registry()
 for a in ASSETS:
  for s in STATES:
   candidates=[(r['setting_id'],r['family'],json.dumps(r['params'],sort_keys=True,separators=(',',':'))) for r in reg]
   for sid, fam, pjson in candidates:
    for h in HORIZONS: out.append(_summary_row(keys.get((a,s,sid,fam,pjson,h),[]),a,s,sid,fam,pjson,h,base))
   for name in ('STATE_EDGE','STATE_DAILY'):
    sid='BASELINE__'+name
    for h in HORIZONS: out.append(_summary_row(keys.get((a,s,sid,name,'{}',h),[]),a,s,sid,name,'{}',h,base))
 assert len(out)==4104
 return out

def _summary_row(arr,a,s,sid,fam,pjson,h,base):
 n=sum(x['status']!='CENSORED' for x in arr); k=sum(x['status']=='SUCCESS' for x in arr); c=sum(x['status']=='CENSORED' for x in arr); lo,hi=wilson(k,n); precision=k/n if n else None
 edge=base.get((a,s,h,'BASELINE__STATE_EDGE')); daily=base.get((a,s,h,'BASELINE__STATE_DAILY'))
 times=[x['hit_or_fail_minutes'] for x in arr if x['status']=='SUCCESS' and x['hit_or_fail_minutes'] is not None]
 return {'asset':a,'state':s,'setting_id':sid,'family':fam,'params_json':pjson,'horizon_hours':h,'alerts_total':len(arr),'censored':c,'n_evaluable':n,'n_success':k,'precision':precision,'wilson_lower':lo,'wilson_upper':hi,'baseline_edge_precision':edge,'baseline_daily_precision':daily,'delta_vs_edge':None if precision is None or edge is None else precision-edge,'delta_vs_daily':None if precision is None or daily is None else precision-daily,'median_time_to_hit_minutes':median(times) if times else None,'alert_days':len({x['signal_time']//86400 for x in arr}),'synthetic':True}

def write_csv(path, rows, fieldnames=None):
 if fieldnames is None: fieldnames=list(rows[0]) if rows else []
 with open(path,'w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fieldnames,extrasaction='ignore'); w.writeheader(); w.writerows(rows)

def checkpoint(path, state):
 payload=json.dumps(state,sort_keys=True,separators=(',',':')).encode(); Path(path).write_text(json.dumps({'state':state,'sha256':hashlib.sha256(payload).hexdigest()},indent=2)+'\n')
def load_checkpoint(path):
 obj=json.loads(Path(path).read_text()); payload=json.dumps(obj['state'],sort_keys=True,separators=(',',':')).encode()
 if hashlib.sha256(payload).hexdigest()!=obj['sha256']: raise ValueError('checkpoint digest mismatch')
 return obj['state']
