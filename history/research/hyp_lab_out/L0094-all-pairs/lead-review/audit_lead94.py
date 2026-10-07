from pathlib import Path
import collections,csv,gzip,hashlib,heapq,json,math,statistics,sys,time
p=Path('l0094/remote-market');start=time.monotonic();raw=json.loads(gzip.decompress((p/'raw_signals.json.gz').read_bytes()));m=json.loads((p/'checkpoint.json').read_text());source=json.loads(Path('l0094/package/source.json').read_text())
assert m['source_sha256']==hashlib.sha256(Path('l0094/package/source.json').read_bytes()).hexdigest()=='c05f574bb298f9021ba9826e3e6e23b654b17b37b13596af1aa582d6c930cb62'
assert not raw['synthetic'] and len(raw['grid'])==482 and m['budget']==348245
assert hashlib.sha256((p/'raw_signals.json.gz').read_bytes()).hexdigest()==m['raw_sha256']=='551918480f66ae32257b5bd4115451ec1f6d9351fbec202f046a0ff7949e547b'
# Compare the raw frozen masks, eligible bars and evaluation events against original L0093 evidence.
parent=json.loads(gzip.decompress(Path('l0094/package/parent93.json.gz').read_bytes()));assert raw['grid']==parent['grid']
assets=['BTCUSDT','ETHUSDT','SOLUSDT'];data=[]
for asset in assets:
 for pi in range(3):
  a=raw['assets'][asset+'_P'+str(pi)];original=parent['assets'][asset]['periods'][pi]
  mm=[int(parent['assets'][asset]['masks'][q['id']],16) for q in raw['grid']]
  assert a['masks']==[hex(x) for x in mm]
  valid=sum(1<<b for b in original['valid']);assert int(a['valid'],16)==valid
  assert [{k:v for k,v in e.items() if k!='mask'} for e in a['events']]==original['events']
  data.append((valid,mm,[e['onset'] for e in a['events']]))
# Candidate keys independently enumerated; no production writer or audit function imported.
import itertools
keys=itertools.chain(((i,i,-1,'S') for i in range(482)),((482+3*k+j,a,b,mode) for k,(a,b) in enumerate(itertools.combinations(range(482),2)) for j,mode in enumerate(['AND0','AND2','OR0'])))
heaps={a:[] for a in assets};parents={};seen=0;zero=0;eligible=collections.Counter();samplechecks=0
for rec in m['parts']:
 path=p/rec['file'];assert path.stat().st_size==rec['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==rec['sha256'] and rec['first']==seen
 with gzip.open(path,'rt',newline='') as f:
  rows=csv.reader(f);header=next(rows);count=0
  assert len(header)==31
  for row in rows:
   key=next(keys);got=[int(v) if j!=3 else v for j,v in enumerate(row)];assert tuple(got[:4])==key
   _,i,j,mode=key;values=[]
   for k,(valid,mm,onsets) in enumerate(data):
    a=mm[i];b=mm[j] if j>=0 else 0
    if mode=='S':truth=a
    elif mode=='AND0':truth=a&b
    elif mode=='OR0':truth=a|b
    else:truth=(a|(a<<1)|(a<<2))&(b|(b<<1)|(b<<2))
    x=(truth&~(truth<<1))&valid
    ns=x.bit_count();tp=lag=0
    for onset in onsets:
     # Explicit chronological five-bar check, independent of event bit-mask score().
     first=next((bar for bar in range(onset-2,onset+3) if (x>>bar)&1),None)
     if first is not None:tp+=1;lag+=first-onset
    assert got[4+3*k:7+3*k]==[ns,tp,lag],('row mismatch',seen,k)
    values.append((ns,tp,len(onsets)))
    if seen%10000==0 or seen==348244:
     aset={t for t in range(valid.bit_length()) if (a>>t)&1};bset={t for t in range(valid.bit_length()) if (b>>t)&1}
     previous=False;z=0
     for t in range(valid.bit_length()):
      v=t in aset if mode=='S' else (t in aset and t in bset) if mode=='AND0' else (t in aset or t in bset) if mode=='OR0' else any(t-d in aset for d in range(3)) and any(t-d in bset for d in range(3))
      if v and not previous and (valid>>t)&1:z|=1<<t
      previous=v
     assert z==x;samplechecks+=1
   for ai,asset in enumerate(assets):
    qq=values[3*ai:3*ai+3];ns=sum(v[0] for v in qq);tp=sum(v[1] for v in qq);ne=sum(v[2] for v in qq);prec=tp/ns if ns else 0;recall=tp/ne
    if not ns:zero+=1
    d=dict(candidate=seen,a=i,b=j,mode=mode,asset=asset,signals=ns,matched_events=tp,events=ne,precision=prec,recall=recall,minimum_period_precision=min(v[1]/v[0] if v[0] else 0 for v in qq),eligible=ns>=20 and recall>=.3 and all(v[0]>=3 and v[1]/v[2]>=.15 for v in qq))
    if mode=='S':parents[asset,seen]=d
    elif d['eligible']:
     eligible[asset]+=1;rank=(d['minimum_period_precision'],prec,recall,-seen);h=heaps[asset];item=(rank,seen,d)
     if len(h)<20:heapq.heappush(h,item)
     elif item[:2]>h[0][:2]:heapq.heapreplace(h,item)
   count+=1;seen+=1
 assert count==rec['rows'];print('LEAD_CHECKED',seen,flush=True)
assert seen==348245
try:next(keys);raise AssertionError('missing rows')
except StopIteration:pass
selection=json.loads((p/'selection.json').read_text());details=json.loads((p/'parent_comparison.json').read_text());quality=[]
for asset in assets:
 ranked=[v[2] for v in sorted(heaps[asset],reverse=True)];saved=selection['top20_eligible_pairs_by_asset'][asset]
 assert [d['candidate'] for d in ranked]==[d['candidate'] for d in saved]
 for simple,d in zip(ranked,saved):
  for k in simple:assert d[k]==simple[k],(asset,d['candidate'],k)
  lags=[];pairs=[];par={d['a']:[],d['b']:[]}
  for pi in range(3):
   valid,mm,onsets=data[assets.index(asset)*3+pi];a=mm[d['a']];b=mm[d['b']]
   t=a&b if d['mode']=='AND0' else a|b if d['mode']=='OR0' else (a|a<<1|a<<2)&(b|b<<1|b<<2)
   x=t&~(t<<1)&valid;matched=set()
   for onset in onsets:
    first=next((bar for bar in range(onset-2,onset+3) if x>>bar&1),None)
    if first is not None:matched.add(onset);lags.append(first-onset)
   pairs.append(matched)
   for parentid in par:
    x=mm[parentid]&valid;par[parentid].append({o for o in onsets if any(x>>bar&1 for bar in range(o-2,o+3))})
  assert d['median_lag']==statistics.median(lags)
  for comp in d['parent_comparison']:
   v=parents[asset,comp['parent']];assert comp['precision']==v['precision'] and comp['recall']==v['recall']
   assert comp['added']==sum(len(x-y) for x,y in zip(pairs,par[comp['parent']]))
   assert comp['lost']==sum(len(y-x) for x,y in zip(pairs,par[comp['parent']]))
  ns=d['signals'];tp=d['matched_events'];z=1.959963984540054;den=1+z*z/ns;ph=tp/ns;center=(ph+z*z/(2*ns))/den;half=z*math.sqrt(ph*(1-ph)/ns+z*z/(4*ns*ns))/den
  assert max(abs(x-y) for x,y in zip(d['wilson95'],[center-half,center+half]))<1e-12
  assert d['quality_pass']==(ph>=.7 and d['recall']>=.3 and ns>=20 and center-half>=.6 and statistics.median(lags)<=1)
  assert d['marginal_gain']==all(ph>=v['precision']+.05 and d['recall']>=.8*v['recall'] for v in d['parent_comparison'])
  if d['quality_pass'] and d['marginal_gain']:quality.append({'asset':asset,'candidate':d['candidate']})
summary={'status':'PASS','decision':'D-L0094-REVIEW-20261007','verdict':'Defer','adoption':'NOT AUTHORISED','candidate_rows':seen,'period_evaluations':seen*9,'logical_mode_sample_checks':samplechecks,'zero_signal_asset_rows':zero,'eligible_pair_counts':dict(eligible),'quality_and_marginal_passes_top20':quality,'leaders':{a:selection['top20_eligible_pairs_by_asset'][a][0] for a in assets},'limitations':'quality only top20 per asset;historical development;no inference or adoption','elapsed_compute_seconds':time.monotonic()-start}
assert len(details)==sum(len(v) for v in selection['top20_eligible_pairs_by_asset'].values())
Path('l0094/lead-review.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({'status':'PASS','quality':quality,'leaders':{a:{k:d[k] for k in ['candidate','rule','signals','matched_events','events','precision','recall','quality_pass','marginal_gain']} for a,d in summary['leaders'].items()},'elapsed':summary['elapsed_compute_seconds']},indent=2))
