"""Frozen six causal price-recovery rules; separate scalar readiness/audit."""
from pathlib import Path
import argparse,json,gzip,hashlib,time,sys,collections,math
import numpy as np
p=argparse.ArgumentParser();p.add_argument('mode',choices=['readiness','measure','audit']);p.add_argument('--package',default='l0090/package');p.add_argument('--out',default='l0092/market');p.add_argument('--source',default='SYNTHETIC');args=p.parse_args();package=Path(args.package).resolve();sys.path.insert(0,str(package));import research85 as R,signals88 as S
scope=json.loads(Path(__file__).with_name('scope.json').read_text())
from candles92 import definitions,signals
grid=[{**q,'id':str(i*3+j),'mode':mode} for i,q in enumerate(definitions()) for j,mode in enumerate(['STANDALONE','CCI_AND_CURRENT','CCI_THEN_CANDLE2'])]
def compute(raw,D,reference=False):
 rows=[];cases=[]
 for asset,a in raw['assets'].items():
  configs=[{**q,'asset':asset} for q in grid]+[{'id':'CCI_CONTROL','mask':'CCI_21_-150' if asset=='SOLUSDT' else 'CCI_14_-150'}]
  for q in configs:
   pulse=set(R.bits(int(a['masks'][q['mask']],16))) if 'mask' in q else set(np.flatnonzero(signals(D[asset],q,reference)))
   per=[];captured=[];lags=[]
   for pi,period in enumerate(a['periods']):
    alerts=sorted(pulse.intersection(period['valid']));claimed=set();hits=[]
    for i in alerts:
     hit=next((j for j,e in enumerate(period['events']) if j not in claimed and abs(i-e['onset'])<=2),None)
     if hit is not None:claimed.add(hit);hits.append(period['events'][hit]['onset']);lags.append(i-period['events'][hit]['onset'])
     cases.append({'asset':asset,'candidate':q['id'],'period':pi,'bar':int(i),'time':D[asset]['dt'][i],'matched_onset':period['events'][hit]['onset'] if hit is not None else None})
    
    if reference:
     events=[{**e,'mask':sum(1<<i for i in e['window'])} for e in period['events']]
     assert R.score(sum(1<<i for i in alerts),events)[:2]==(len(alerts),len(claimed))
    per.append(R.metric(len(alerts),len(claimed),len(period['events'])));captured.append(hits)
   ns=sum(x['signals'] for x in per);tp=sum(x['matched_events'] for x in per);ne=sum(x['events'] for x in per)
   rows.append({'asset':asset,'candidate':q['id'],'definition':q,**R.metric(ns,tp,ne),'periods':per,'captured_onsets_by_period':captured,'minimum_period_precision':min(x['precision'] for x in per),'median_lag':float(np.median(lags)) if lags else None,'eligible':ns>=20 and tp/ne>=.30 and all(x['signals']>=3 and x['recall']>=.15 for x in per)})
 for x in rows:
  baseline=next(r for r in rows if r['asset']==x['asset'] and r['candidate']=='CCI_CONTROL');x['added_events_vs_cci']=sum(len(set(a)-set(b)) for a,b in zip(x['captured_onsets_by_period'],baseline['captured_onsets_by_period']));x['lost_events_vs_cci']=sum(len(set(b)-set(a)) for a,b in zip(x['captured_onsets_by_period'],baseline['captured_onsets_by_period']))
 return rows,cases
begin=time.monotonic()
if args.mode=='readiness':
 D=R.fixture();raw={'assets':{}};checks=0
 for asset,d in D.items():
  for q in grid:
   a=signals(d,{**q,'asset':asset});assert np.array_equal(a,signals(d,{**q,'asset':asset},True));checks+=1
   for cut in [80,160,300]:assert np.array_equal(signals({k:v[:cut] for k,v in d.items()},{**q,'asset':asset}),a[:cut]);checks+=1
  ev=R.labels(d,180,340);assert [e['onset'] for e in ev]==[e[0] for e in R.labels_reference(d,180,340)];raw['assets'][asset]={'masks':{k:hex(R.pack(v)) for k,v in S.primitives(d).items()},'periods':[{'valid':list(range(185,316)),'events':ev}]}
 fast=compute(raw,D);assert fast==compute(raw,D,True)
 print(json.dumps({'status':'PASS','synthetic_only':True,'mask_and_prefix_checks':checks,'synthetic_rows':len(fast[0]),'scalar_matching_and_labels':'PASS','elapsed_seconds':time.monotonic()-begin}));sys.exit()
for n,h in scope['input_sha256'].items():assert hashlib.sha256((package/n).read_bytes()).hexdigest()==h,n
D=R.load_market();raw=json.loads(gzip.decompress((package/'parent_raw.json.gz').read_bytes()));out=Path(args.out);out.mkdir(parents=True,exist_ok=True);rows,cases=compute(raw,D,args.mode=='audit');assert len(rows)==57 and len({(x['asset'],x['candidate']) for x in rows})==57
payload={'round':'L0092','source_commit':args.source,'discovery_only':True,'rows':rows};encode=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
if args.mode=='audit':
 assert (out/'results.json').read_bytes()==encode(payload);assert (out/'alerts.json').read_bytes()==encode(cases)
else:(out/'results.json').write_bytes(encode(payload));(out/'alerts.json').write_bytes(encode(cases))
selected={}
for asset in raw['assets']:
 eligible=sorted([x for x in rows if x['asset']==asset and x['candidate']!='CCI_CONTROL' and x['eligible']],key=lambda x:(-x['minimum_period_precision'],-x['precision'],-x['recall'],int(x['candidate'])));selected[asset]=eligible[0]['candidate'] if eligible else None
selection={'selected_by_asset':selected,'eligibility_and_ranking_frozen':True,'adoption':'NOT AUTHORISED','conditional_inference':'not measured;no null/MCMC controls in this descriptive stage'}
if args.mode=='audit':assert json.loads((out/'selection.json').read_text())==selection
else:(out/'selection.json').write_bytes(encode(selection))
checks=0
for asset,d in D.items():
 for q in grid:
  a=signals(d,{**q,'asset':asset});assert np.array_equal(a,signals(d,{**q,'asset':asset},True));checks+=1
  for cut in [1200,1800,2400]:assert np.array_equal(signals({k:v[:cut] for k,v in d.items()},{**q,'asset':asset}),a[:cut]);checks+=1
 for period in raw['assets'][asset]['periods']:
  # Compare evaluation labels against independent recurrence as well as reused frozen raw.
  assert [e['onset'] for e in period['events']]==[e[0] for e in R.labels_reference(d,period['start'],period['end'])]
status={'status':'PASS' if args.mode=='audit' else 'MEASURED_AUDIT_PENDING','rows':57,'asset_period_evaluations':171,'new_rules':18,'real_mask_and_prefix_checks':checks,'labels_reference_checks':9,'elapsed_seconds':time.monotonic()-begin,'scope_sha256':hashlib.sha256(Path(__file__).with_name('scope.json').read_bytes()).hexdigest(),'source_commit':args.source}
(out/('audit.json' if args.mode=='audit' else 'measure.json')).write_bytes(encode(status));print(json.dumps(status))
