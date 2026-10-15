import collections,csv,gzip,json,math,random
from decimal import Decimal as D,localcontext
from features import FRAMES,RECORD,State,latest,sha
def audit(inputs,out,manifest):
 compared=0;timing=0;native=0;max_error=0.0
 for d in manifest['files']:
  p=out/d['file'];assert sha(p)==d['sha256'] and p.stat().st_size==d['records']*120
  with p.open('rb') as f:
   for i,r in enumerate(RECORD.iter_unpack(f.read())):assert r[0]==d['first_open_ms']+i*d['frame_minutes']*60000;native+=1
 for n in FRAMES:
  selected=set(random.Random(20261015+n).sample(range(manifest['counts'][str(n)]),min(24,manifest['counts'][str(n)])))|{0,manifest['counts'][str(n)]-1};sums={};v={};hist=collections.deque(maxlen=5);vol=collections.deque(maxlen=60);prev=None;k=0
  def smooth(key,x,period,wild=False):
   if x is None:return None
   if key not in v:
    buf=sums.setdefault(key,[]);buf.append(x)
    if len(buf)==period:v[key]=sum(buf)/D(period)
   else:v[key]=v[key]+(x-v[key])*(D(1)/period if wild else D(2)/(period+1))
   return v.get(key)
  with localcontext() as ctx,gzip.open(inputs/f'BTCUSDT-{n}m.csv.gz','rt',newline='') as f:
   ctx.prec=40;reader=csv.reader(f);next(reader)
   for row in reader:
    t=int(row[0]);o,h,l,c,q=map(D,row[1:6]);delta=None if prev is None else c-prev;tr=h-l if prev is None else max(h-l,abs(h-prev),abs(l-prev));a=smooth('a',tr,14,True);e=smooth('e',c,20);fast=smooth('f',c,12);slow=smooth('s',c,26);m=None if slow is None else fast-slow;signal=smooth('sig',m,9);hi=None if signal is None else m-signal;g=smooth('g',None if delta is None else max(delta,D(0)),14,True);loss=smooth('loss',None if delta is None else max(-delta,D(0)),14,True);r=None if g is None else D(50) if g==loss==0 else D(100) if loss==0 else D(100)-D(100)/(1+g/loss)
    old=hist[0] if len(hist)==5 else None
    div=lambda x,y:None if x is None or y in (None,0) else x/y
    ref=[a,div(None if a is None else 100*a,c),None if not old or not old[0] else a/old[0]-1,e,div(None if e is None else c-e,a),div(None if not old or e is None or old[1] is None else e-old[1],a),m,signal,div(hi,a),div(None if not old or hi is None or old[2] is None else hi-old[2],a),r,None if not old or r is None or old[3] is None else r-old[3],q,div(q,sum(vol)/60) if len(vol)==60 else None]
    if manifest['history_start_ms']<=t<manifest['analysis_end_exclusive_ms']:
     if k in selected:
      got=latest(out,manifest,n,t+n*60000);assert got and got[0]==t
      for expected,actual in zip(ref,got[1:]):
       if expected is None:assert math.isnan(actual)
       else:
        error=abs(float(expected)-actual);max_error=max(max_error,error);assert math.isclose(float(expected),actual,rel_tol=1e-10,abs_tol=1e-8),(n,t,expected,actual,error)
       compared+=1
     k+=1
    hist.append((a,e,hi,r));vol.append(q);prev=c
  assert k==manifest['counts'][str(n)]
  t=manifest['analysis_start_ms']
  for offset in [0,5,15]:
   for decision in [t+60000,t+n*60000-1,t+n*60000,t+2*n*60000]:
    record=latest(out,manifest,n,decision,offset);assert record is not None and record[0]+n*60000<=decision-offset*60000;assert record[0]+2*n*60000>decision-offset*60000;timing+=1
 # A streaming prefix and full path must preserve all already computed values.
 with gzip.open(inputs/'BTCUSDT-1m.csv.gz','rt',newline='') as f:
  r=csv.reader(f);next(r);rows=[next(r) for _ in range(600)]
 full=State();allvalues=[full.step(r) for r in rows];short=State();prefix=[short.step(r) for r in rows[:425]]
 for a,b in zip(prefix[200:],allvalues[200:425]):assert all(x==y or math.isnan(x) and math.isnan(y) for x,y in zip(a,b))
 result={'status':'PASS_NUMERIC_AND_CAUSAL_CHECKS','binary_records_checked':native,'decimal_field_comparisons':compared,'max_absolute_decimal_difference':max_error,'closed_only_timing_cases':timing,'prefix_records_equal':225,'future_outcomes_read':False,'predictive_accuracy':'not measured','decimal_tolerance':{'relative':1e-10,'absolute':1e-8}}
 (out/'AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');return result
