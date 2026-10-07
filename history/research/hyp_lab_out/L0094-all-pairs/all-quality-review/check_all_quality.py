from pathlib import Path
import csv,gzip,hashlib,json,math,statistics,time
p=Path('l0094/remote-market');start=time.monotonic();m=json.loads((p/'checkpoint.json').read_text());raw=json.loads(gzip.decompress((p/'raw_signals.json.gz').read_bytes()));sel=json.loads((p/'selection.json').read_text());assets=['BTCUSDT','ETHUSDT','SOLUSDT'];top={a:{r['candidate'] for r in sel['top20_eligible_pairs_by_asset'][a]} for a in assets}
counts={a:{'pairs':0,'sample20':0,'sample20_recall30':0,'eligible':0,'eligible_precision70':0,'eligible_precision70_wilson60':0,'quality_pass':0,'outside_top20_quality_pass':0} for a in assets};best={a:None for a in assets};passing=[];seen=0
for rec in m['parts']:
 f=p/rec['file'];assert hashlib.sha256(f.read_bytes()).hexdigest()==rec['sha256']
 with gzip.open(f,'rt',newline='') as stream:
  for row in csv.DictReader(stream):
   seen+=1
   if row['mode']=='S':continue
   for asset in assets:
    ns=[int(row[asset+'_P'+str(i)+'_signals']) for i in range(3)];tp=[int(row[asset+'_P'+str(i)+'_matched']) for i in range(3)];ne=[len(raw['assets'][asset+'_P'+str(i)]['events']) for i in range(3)];N=sum(ne);NS=sum(ns);TP=sum(tp);P=TP/NS if NS else 0;R=TP/N;c=counts[asset];c['pairs']+=1
    if NS>=20:c['sample20']+=1
    if NS>=20 and R>=.3:c['sample20_recall30']+=1
    eligible=NS>=20 and R>=.3 and all(n>=3 and t/e>=.15 for n,t,e in zip(ns,tp,ne))
    if not eligible:continue
    c['eligible']+=1;cid=int(row['candidate']);a=int(row['a']);b=int(row['b']);minp=min(t/n for t,n in zip(tp,ns));d=dict(asset=asset,candidate=cid,mode=row['mode'],a=a,b=b,rule=[raw['grid'][a],raw['grid'][b]],signals=NS,matched_events=TP,events=N,precision=P,recall=R,minimum_period_precision=minp,periods=[dict(signals=n,matched_events=t,events=e,precision=t/n,recall=t/e) for n,t,e in zip(ns,tp,ne)],outside_top20=cid not in top[asset])
    # Explicit diagnostic ranking by precision, not a change to registered top20 selection.
    rank=(P,R,minp,-cid)
    if best[asset] is None or rank>best[asset][0]:best[asset]=(rank,d)
    if P<.7:continue
    c['eligible_precision70']+=1;z=1.959963984540054;den=1+z*z/NS;center=(P+z*z/(2*NS))/den;half=z*math.sqrt(P*(1-P)/NS+z*z/(4*NS*NS))/den;low=center-half
    if low<.6:continue
    c['eligible_precision70_wilson60']+=1;lags=[]
    for pi in range(3):
     r=raw['assets'][asset+'_P'+str(pi)];x=int(r['masks'][a],16);y=int(r['masks'][b],16);truth=x&y if row['mode']=='AND0' else x|y if row['mode']=='OR0' else (x|x<<1|x<<2)&(y|y<<1|y<<2);x=truth&~(truth<<1)&int(r['valid'],16)
     for e in r['events']:
      first=next((i for i in range(e['onset']-2,e['onset']+3) if x>>i&1),None)
      if first is not None:lags.append(first-e['onset'])
    assert len(lags)==TP
    if statistics.median(lags)<=1:
     c['quality_pass']+=1;c['outside_top20_quality_pass']+=int(d['outside_top20']);d.update(wilson95=[low,center+half],median_lag=statistics.median(lags));passing.append(d)
assert seen==348245 and all(c['pairs']==347763 for c in counts.values())
result=dict(status='PASS',classification='post-hoc diagnostic scan of existing scores;not new discovery selection or validation',source_commit='bbad466f573f7b94052a22f6abc00d0dee7104d7',decision='D-L0094-ALL-QUALITY-20261007',verdict='Defer',counts=counts,highest_precision_eligible_diagnostic={a:v[1] for a,v in best.items()},quality_passes_all_pairs=passing,adoption='NOT AUTHORISED',elapsed_compute_seconds=time.monotonic()-start)
Path('l0094/all-quality-review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
