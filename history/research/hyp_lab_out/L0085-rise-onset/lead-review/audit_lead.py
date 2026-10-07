from pathlib import Path
import sys,csv,json,gzip,hashlib,math,itertools,heapq,os
import numpy as np
ROOT=Path(__file__).resolve().parent;E=ROOT/'evidence';P=Path(os.environ.get('NOVA85_PACKAGE',str(ROOT.parent/'l0085/package')))
if not P.exists():P=next(parent/'tools/l0085' for parent in ROOT.parents if (parent/'tools/l0085').is_dir())
sys.path.insert(0,str(P));import signals85 as S

def read(n):return json.loads((E/n).read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
raw=json.loads(gzip.decompress((E/'raw_signals.json.gz').read_bytes()));m=read('checkpoint.json');assert digest(E/'raw_signals.json.gz')==m['raw_sha256'];assert raw['synthetic'] is False
assert raw['grid']==S.catalogue() and len(raw['grid'])==476
assets=['BTCUSDT','ETHUSDT','SOLUSDT'];data={};checks=0;onsets={};source_masks={}
manifest=json.loads((P/'package_manifest.json').read_text());assert manifest==json.loads((ROOT/'package_manifest.json').read_text())
for name,h in manifest.items():assert digest(P/name)==h
for asset in assets:
 inp=next(x for x in json.loads((P/'inputs.json').read_text()) if x['asset']==asset);assert digest(P/inp['file'])==inp['sha256']
 rows=list(csv.DictReader((P/inp['file']).open()));d={k:[float(x[col]) for x in rows] for k,col in zip('ohlcvt',['open','high','low','close','volume','taker_buy_volume'])};ts=[x['dt'] for x in rows];a=raw['assets'][asset];assert ts==a['times'] and a['start']==1104 and a['end']==1644
 o,h,l,c,v,t=[d[k] for k in 'ohlcvt'];atr=[];value=None
 for i in range(len(c)):
  tr=max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) if i else h[i]-l[i];value=tr if value is None else value+(tr-value)/14;atr.append(value)
 events=[];last=-999
 for i in range(1111,1618):
  if i-last<25 or min(range(i-5,i+6),key=lambda k:l[k])!=i:continue
  up=next((k for k in range(i+1,i+25) if h[k]>=c[i]+2*atr[i]),None);down=next((k for k in range(i+1,i+25) if l[k]<=c[i]-atr[i]),None)
  if up is not None and (down is None or up<down):events.append((i,up));last=i
 assert events==[(x['onset'],x['hit']) for x in a['events']]
 for e in a['events']:
  assert math.isclose(e['atr'],atr[e['onset']],rel_tol=1e-12);assert e['close']==c[e['onset']];assert e['window']==list(range(e['onset']-2,e['onset']+3));assert e['mask']==sum(1<<k for k in e['window'])
 valid=sum(1<<i for i in range(1109,1620));assert int(a['valid'],16)==valid
 arrays=dict(zip(['o','h','l','c','v','tbv'],map(np.asarray,[o,h,l,c,v,t])));built=S.build(arrays)
 for j,g in enumerate(raw['grid']):
  actual=int(a['masks'][j],16);expected=sum(1<<int(k) for k in np.flatnonzero(built[g['id']]));assert actual==expected,(asset,g['id']);checks+=1
 # Independently authored scalar BB20_2.5 and volume-weighted VWAP30_1.5 conditions.
 bb=[];vw=[]
 for i in range(len(c)):
  if i<19:bb.append(False)
  else:
   q=c[i-19:i+1];mean=sum(q)/20;sd=math.sqrt(sum((x-mean)**2 for x in q)/20);band=mean-2.5*sd;bb.append(l[i]<=band<c[i])
  if i<29:vw.append(False)
  else:
   ids=range(i-29,i+1);vv=sum(v[k] for k in ids);mean=sum((h[k]+l[k]+c[k])/3*v[k] for k in ids)/vv;var=sum(v[k]*(((h[k]+l[k]+c[k])/3)-mean)**2 for k in ids)/vv;band=mean-1.5*math.sqrt(max(0,var));vw.append(l[i]<=band<c[i])
 for name,mask in [('BB_20_2.5',bb),('VWAP_30_1.5',vw)]:assert np.array_equal(mask,built[name]),(asset,name,'scalar reference')
 data[asset]={'raw':a,'valid':valid,'masks':[int(x,16) for x in a['masks']],'events':events,'d':d,'atr':atr,'bb':bb,'vw':vw};onsets[asset]=len(events)
print('SOURCE_MASKS_AND_INDEPENDENT_LABELS_PASS',checks,onsets,flush=True)
# Separate scoring and ranking implementation, no research85 score/audit/report call.
def alerts(a,b,mode,valid):
 if mode=='S':truth=a
 elif mode=='AND0':truth=a&b
 elif mode=='OR0':truth=a|b
 else:truth=sum([]) if False else (a|(a<<1)|(a<<2))&(b|(b<<1)|(b<<2))
 return truth & ~(truth<<1)&valid

def evaluate(x,events):
 tp=0;lag=0
 for onset,_ in events:
  matches=[i for i in range(onset-2,onset+3) if x&(1<<i)]
  if matches:tp+=1;lag+=matches[0]-onset
 return x.bit_count(),tp,lag

def keys():
 for i in range(476):yield i,-1,'S'
 for i,j in itertools.combinations(range(476),2):
  for mode in ['AND0','AND2','OR0']:yield i,j,mode
expected_keys=iter(keys());best=[];bestpairs=[];qualified=[];bestoverall=[];single={};zero=0;seen=0

def top(heap,row):
 val=(row['macro_f1'],-row['candidate'],row)
 if len(heap)<20:heapq.heappush(heap,val)
 elif val[:2]>heap[0][:2]:heapq.heapreplace(heap,val)
for part in m['parts']:
 p=E/part['file'];assert digest(p)==part['sha256'] and p.stat().st_size==part['bytes'] and part['first']==seen
 rows=csv.DictReader(gzip.open(p,'rt'));n=0
 for row in rows:
  num=int(row['candidate']);i,j,mode=int(row['a']),int(row['b']),row['mode'];assert num==seen and (i,j,mode)==next(expected_keys);values=[]
  for asset in assets:
   d=data[asset];ns,tp,lag=evaluate(alerts(d['masks'][i],d['masks'][j] if j>=0 else 0,mode,d['valid']),d['events']);assert [ns,tp,lag]==[int(row[asset+'_'+k]) for k in ['signals','matched','lag_sum']]
   ne=len(d['events']);values.append({'asset':asset,'signals':ns,'matched':tp,'events':ne,'precision':tp/ns if ns else 0,'recall':tp/ne if ne else 0,'f1':2*tp/(ns+ne) if ns+ne else 0})
  total=sum(v['signals'] for v in values);tp=sum(v['matched'] for v in values);zero+=total==0
  r={'candidate':num,'a':i,'b':j,'mode':mode,'signals':total,'matched':tp,'macro_f1':sum(v['f1'] for v in values)/3,'per_asset':values,'eligible':total>=15 and tp>=6 and all(v['signals']>=3 and v['events']>=3 for v in values),'rules':[raw['grid'][k]['id'] for k in [i,j] if k>=0]}
  top(bestoverall,r)
  if mode=='S':single[i]=r
  else:
   top(bestpairs,r)
   if r['eligible']:top(qualified,r)
  n+=1;seen+=1
 assert n==part['rows'];print('INDEPENDENTLY_RECONCILED',seen,flush=True)
assert seen==339626 and next(expected_keys,None) is None
order=lambda h:[x[2] for x in sorted(h,reverse=True)];top10=order(qualified or bestpairs)[:10];selection=read('selection.json');assert selection['frozen_candidate_ids']==[x['candidate'] for x in top10] and selection['validation_read'] is False
ranking=read('ranking.json');assert [x['candidate'] for x in ranking['pair_top20']]==[x['candidate'] for x in order(bestpairs)]
assert [x['candidate'] for x in ranking['all_top20']]==[x['candidate'] for x in order(bestoverall)]
for r in top10:
 remote=next(v for v in selection['rules'] if v['candidate']==r['candidate']);assert r['macro_f1']==remote['macro_f1'] and r['signals']==remote['signals'] and r['matched']==remote['matched_events'];assert [g['id'] for g in remote['rule']]==r['rules']
 r['parents']=[single[k] for k in [r['a'],r['b']]];r['parent_improvement']=r['macro_f1']-max(x['macro_f1'] for x in r['parents'])
# Every saved alert diagnostic reconciled to source prices, raw masks and one-to-one matches.
AA=read('alerts_top20.json');aa_count=0
for z in AA:
 d=data[z['asset']];i=z['bar'];assert 1109<=i<=1619 and d['raw']['times'][i]==z['time'];price=d['d']['c'][i];atr=d['atr'][i]
 for field,value in [('mae_atr_24',min(0,min(d['d']['l'][i+1:i+25])-price)/atr),('mfe_atr_24',max(0,max(d['d']['h'][i+1:i+25])-price)/atr)]:assert math.isclose(z[field],value,abs_tol=1e-9)
 aa_count+=1
winner=top10[0];winner_alerts=[]
for asset in assets:
 d=data[asset];truth=[a and b for a,b in zip(d['bb'],d['vw'])];inds=[i for i in range(1109,1620) if truth[i] and not truth[i-1]];saved=[a for a in AA if a['asset']==asset and a['candidate']==winner['candidate']];assert inds==[a['bar'] for a in saved];winner_alerts+=saved
assert winner['rules']==['BB_20_2.5','VWAP_30_1.5'] and winner['mode']=='AND0'
json.dump({'status':'PASS','delivery':'d1fe9978bee6bc7e3478f53d07633f9fabd198cf','rows':seen,'asset_rows':seen*3,'zero_signal_candidates':zero,'all_raw_masks_rebuilt':checks,'events_per_asset':onsets,'independent_winner_indicators':['BB20_2.5','VWAP30_1.5'],'diagnostic_alert_rows':aa_count,'winner':winner,'top10':top10,'best_overall':order(bestoverall)[0],'winner_alerts':winner_alerts,'not_measured':['reserved validation','new blind period','multiplicity-adjusted significance','profitability']},open(ROOT/'lead_audit.json','w'),indent=2)
print('LEAD_AUDIT_PASS',winner['rules'],winner['signals'],winner['matched'],winner['macro_f1'],flush=True)
