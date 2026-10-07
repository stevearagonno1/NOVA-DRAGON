"""Audit persisted raw evidence; independent counting, policy selection and gates."""
from pathlib import Path
import argparse,json,gzip,math,statistics,sys,hashlib
import numpy as np
import signals88 as S

def run(inputs,out):
 inputs=Path(inputs).resolve();out=Path(out);sys.path.insert(0,str(inputs));import research85 as R
 R.ROOT=inputs;load=lambda n:json.loads((out/n).read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 for n,h in load('checkpoint.json')['hashes'].items():assert sha(out/n)==h,('hash',n)
 raw=json.loads(gzip.decompress((out/'raw.json.gz').read_bytes()));scope=json.loads((Path(__file__).parent/'scope.json').read_text());assert raw['scope_sha256']==sha(Path(__file__).parent/'scope.json');assert raw['catalogue']==S.catalogue()
 data=R.fixture() if raw['synthetic'] else R.load_market();rows=[];records=[];bases=[]
 def m(ns,tp,n):return {'signals':ns,'matched':tp,'events':n,'precision':tp/ns if ns else 0.,'recall':tp/n if n else 0.,'f1':2*tp/(ns+n) if ns+n else 0.}
 def match(bits,ev):
  x={}
  for j,e in enumerate(ev):
   hit=min((i for i in bits if e['onset']-2<=i<=e['onset']+2),default=None)
   if hit is not None:x[hit]=j
  return x
 for s,a in raw['assets'].items():
  d=data[s];assert a['times']==d['dt'];ref=S.primitives(d,True);atr=R.I.wilder_atr(d['h'],d['l'],d['c'],14)
  for q in raw['catalogue']:assert int(a['masks'][q['id']],16)==sum(1<<int(i) for i in np.flatnonzero(ref[q['id']]))
  for pi,p in enumerate(a['periods']):
   ev=p['events'];assert [(e['onset'],e['hit']) for e in ev]==R.labels_reference(d,p['start'],p['end']);valid=set(range(p['start']+5,p['end']-24));assert valid==set(p['valid'])
   for q in raw['catalogue']:
    key=q['id'];bits={i for i in valid if int(a['masks'][key],16)&(1<<i)};matched=match(bits,ev);rows.append({'candidate':key,'asset':s,'period':pi,**m(len(bits),len(matched),len(ev))})
    for i in sorted(bits):
     j=matched.get(i);t=ev[j]['onset'] if j is not None else None;records.append({'candidate':key,'asset':s,'period':pi,'bar':i,'time':d['dt'][i],'event':j,'onset':t,'lag':i-t if t is not None else None,'mae_atr24':float(min(0,min(d['l'][i+1:i+25])-d['c'][i])/atr[i]),'mfe_atr24':float(max(0,max(d['h'][i+1:i+25])-d['c'][i])/atr[i])})
   for name,bits in [('NONE',set()),('EVERY_BAR',valid),('EVERY_5_BARS',{i for i in valid if (i-p['start']-5)%5==0})]:bases.append({'name':name,'asset':s,'period':pi,**m(len(bits),len(match(bits,ev)),len(ev))})
 assert rows==load('results.json') and bases==load('baselines.json') and records==load('alerts.json')
 def lower(tp,n):
  if n==0:return 0.
  z=1.959963984540054;p=tp/n;return (2*n*p+z*z-z*math.sqrt(z*z+4*n*p*(1-p)))/(2*(n+z*z))
 def summary(rr):
  x=m(sum(q['signals'] for q in rr),sum(q['matched'] for q in rr),sum(q['events'] for q in rr));x.update(min_period_precision=min(q['precision'] for q in rr),min_period_recall=min(q['recall'] for q in rr),wilson95_low_descriptive=lower(x['matched'],x['signals']));return x
 def compare(x,y):
  if isinstance(x,dict):
   assert set(x)==set(y)
   for k in x:compare(x[k],y[k])
  elif isinstance(x,list):
   assert len(x)==len(y)
   for a,b in zip(x,y):compare(a,b)
  elif isinstance(x,float):assert math.isclose(x,y,rel_tol=1e-12,abs_tol=1e-12),(x,y)
  else:assert x==y,(x,y)
 aa=[];ss=[]
 for asset in data:
  for q in raw['catalogue']:
   rr=[x for x in rows if x['candidate']==q['id'] and x['asset']==asset];x={'candidate':q['id'],'family':q['family'],'asset':asset,**summary(rr)};x['eligible']=x['signals']>=20 and x['recall']>=.3 and all(y['signals']>=3 and y['recall']>=.15 for y in rr);lags=[r['lag'] for r in records if r['candidate']==q['id'] and r['asset']==asset and r['lag'] is not None];x['median_lag']=statistics.median(lags) if lags else None;aa.append(x)
 for q in raw['catalogue']:
  per=[x for x in aa if x['candidate']==q['id']];pr=[]
  for p in range(3):
   z=[x for x in rows if x['candidate']==q['id'] and x['period']==p];pr.append(m(sum(a['signals'] for a in z),sum(a['matched'] for a in z),sum(a['events'] for a in z)))
  x={'candidate':q['id'],'family':q['family'],**summary(pr),'eligible':all(y['eligible'] for y in per),'macro_f1':statistics.mean(y['f1'] for y in per),'per_asset':per};lags=[r['lag'] for r in records if r['candidate']==q['id'] and r['lag'] is not None];x['median_lag']=statistics.median(lags) if lags else None;x['quality_checks']={'sample':x['signals']>=100 and all(y['signals']>=20 for y in per),'precision070':x['precision']>=.7,'recall030':x['recall']>=.3,'asset_precision055':all(y['precision']>=.55 for y in per),'wilson060':x['wilson95_low_descriptive']>=.6,'lag1':x['median_lag'] is not None and x['median_lag']<=1};x['quality']='INSUFFICIENT_SAMPLE' if not x['quality_checks']['sample'] else 'DISCOVERY_TARGET_ONLY' if all(x['quality_checks'].values()) else 'TARGET_NOT_MET';ss.append(x)
 compare(aa,load('asset_summary.json'));compare(ss,load('shared_summary.json'));selection=load('selection.json')
 def best(rr):
  z=sorted([x for x in rr if x['eligible']],key=lambda x:(-x['min_period_precision'],-x['wilson95_low_descriptive'],-x['recall'],-x['signals'],x['candidate']));return z[0]['candidate'] if z else None
 for asset in data:
  for f,v in selection['per_asset'][asset].items():assert v==best([x for x in aa if x['asset']==asset and x['family']==f])
 for f,v in selection['shared'].items():assert v==best([x for x in ss if x['family']==f])
 result={'status':'PASS','synthetic':raw['synthetic'],'rows_checked':len(rows),'scalar_masks_checked':108,'asset_summaries_checked':108,'shared_summaries_checked':36,'alert_rows_checked':len(records),'baselines_checked':27,'selection_and_quality_recomputed':True,'new_experiment_run':False};(out.parent/'lead_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--inputs',required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.inputs,a.out)
