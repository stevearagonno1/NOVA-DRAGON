from pathlib import Path
import collections,gzip,hashlib,json,math,statistics,sys,time
p=Path('l0093/remote-market');begin=time.monotonic();raw=json.loads(gzip.decompress((p/'raw.json.gz').read_bytes()));rows=json.loads((p/'results.json').read_text());audit=json.loads((p/'audit.json').read_text());checkpoint=json.loads((p/'checkpoint.json').read_text())
assert not raw['synthetic'] and not audit['synthetic']
assert hashlib.sha256((p/'raw.json.gz').read_bytes()).hexdigest()==audit['raw_sha256']==checkpoint['raw_sha256']
source=json.loads(Path('l0093/package/source.json').read_text());assert source==checkpoint['source'];assert hashlib.sha256(Path('l0093/package/source.json').read_bytes()).hexdigest()=='3298e2fe3365286db1f3cc5eb863877fcf6704136a8cc5541483360c3d401ca4'
sys.path.insert(0,str(Path('l0093/package').resolve()));import run93 as M,research85 as R,signals85 as S
assert raw['grid']==M.grid() and len(rows)==1446 and len({(r['asset'],r['id']) for r in rows})==1446
bykey={(r['asset'],r['id']):r for r in rows};checks=0
for asset,a in raw['assets'].items():
 assert len(a['periods'])==3
 for q in raw['grid']:
  got=bykey[asset,q['id']];pulse=int(a['masks'][q['id']],16);lags=[];counts=[]
  for pi,period in enumerate(a['periods']):
   alerts=[i for i in period['valid'] if (pulse>>i)&1];claimed=set();ll=[];hh=[]
   for bar in alerts:
    for j,event in enumerate(period['events']):
     if j not in claimed and abs(bar-event['onset'])<=2:
      claimed.add(j);ll.append(bar-event['onset']);hh.append(event['onset']);break
   ns=len(alerts);tp=len(claimed);ne=len(period['events']);z=got['periods'][pi]
   assert (z['signals'],z['matched_events'],z['events'])==(ns,tp,ne)
   assert got['captured_onsets'][pi]==hh
   for name,value in [('precision',tp/ns if ns else 0),('recall',tp/ne if ne else 0),('f1',2*tp/(ns+ne) if ns+ne else 0)]:assert abs(z[name]-value)<1e-12
   counts.append((ns,tp,ne));lags+=ll;checks+=1
  ns=sum(c[0] for c in counts);tp=sum(c[1] for c in counts);ne=sum(c[2] for c in counts)
  assert (got['signals'],got['matched_events'],got['events'],got['false_or_duplicate'])==(ns,tp,ne,ns-tp)
  assert got['median_lag']==(statistics.median(lags) if lags else None)
  assert got['eligible']==(ns>=20 and tp/ne>=.3 and all(c[0]>=3 and c[1]/c[2]>=.15 for c in counts))
  if ns:
   z=1.959963984540054;den=1+z*z/ns;ph=tp/ns;mid=(ph+z*z/(2*ns))/den;half=z*math.sqrt(ph*(1-ph)/ns+z*z/(4*ns*ns))/den
   assert max(abs(x-y) for x,y in zip(got['wilson95'],[mid-half,mid+half]))<1e-12
  else:assert got['wilson95'] is None
# Engine consistency check; label calculation is a separate scalar recurrence.
D=R.load_market();maskchecks=0
for asset,d in D.items():
 for q,k in M.masks(d).items():assert int(raw['assets'][asset]['masks'][q],16)==k;maskchecks+=1
 for period in raw['assets'][asset]['periods']:
  assert [(e['onset'],e['hit']) for e in period['events']]==R.labels_reference(d,period['start'],period['end'])
assert M.select(rows)==json.loads((p/'selection.json').read_text())
quality=[]
for r in rows:
 ok=r['precision']>=.7 and r['recall']>=.3 and r['signals']>=20 and r['eligible'] and r['wilson95'][0]>=.6 and r['median_lag']<=1
 quality.append(dict(asset=r['asset'],id=r['id'],target_pass=ok))
assert quality==json.loads((p/'quality.json').read_text())
top=[]
for asset in R.ASSETS:
 eligible=sorted([r for r in rows if r['asset']==asset and r['eligible']],key=lambda r:(-r['minimum_period_precision'],-r['wilson95'][0],-r['recall'],-r['signals'],r['id']))
 top.append(eligible[0] if eligible else None)
summary={'status':'PASS','decision':'D-L0093-REVIEW-20261007','verdict':'Defer','adoption':'NOT AUTHORISED','asset_period_counts_checked':checks,'mask_consistency_checks':maskchecks,'scalar_label_checks':9,'quality_passes':[q for q in quality if q['target_pass']],'top_eligible_per_asset':top,'zero_signal_rows':sum(r['signals']==0 for r in rows),'eligible_per_asset':dict(collections.Counter(r['asset'] for r in rows if r['eligible'])),'elapsed_compute_seconds':time.monotonic()-begin,'limits':'same-period discovery;Wilson descriptive;all masks rebuilt with same indicator engine,not all numeric definitions independently reimplemented','next':'prepare frozen pair-search scope for executor;no new search in this review'}
Path('l0093/lead-review.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
