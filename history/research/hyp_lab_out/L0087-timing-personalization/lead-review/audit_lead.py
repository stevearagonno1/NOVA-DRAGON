from pathlib import Path
import json,gzip,csv,math,hashlib,sys,os
R=Path(__file__).resolve().parent;E=R/'market';P=Path(os.environ.get('NOVA87_PACKAGE',str(R.parent/'l0087/package')))
if not P.exists():P=next(parent/'tools/l0087' for parent in R.parents if (parent/'tools/l0087').is_dir())
def read(n):return json.loads((E/n).read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b):return math.isclose(a,b,rel_tol=1e-11,abs_tol=1e-12)
raw=json.loads(gzip.decompress((E/'raw_signals.json.gz').read_bytes()));res=read('comparison.json');checkpoint=read('checkpoint.json');assert raw['synthetic'] is False
for n,h in checkpoint['outputs'].items():assert digest(E/n)==h,('file hash',n)
assert raw['scope_sha256']==digest(P/'scope.json') and raw['selection_sha256']==digest(P/'selection87.json')
frozen=json.loads((P/'selection87.json').read_text());assert read('selection87.json')==frozen
keys=[[11,0,-1,'S'],[17312,0,1,'AND0'],[17313,0,1,'AND2']];assert raw['keys']==keys
assert raw['grid']==json.loads((P/'grid87.json').read_text())
assets=['BTCUSDT','ETHUSDT','SOLUSDT'];data={};mask_checks=0
for sym in assets:
 meta=next(x for x in json.loads((P/'inputs.json').read_text()) if x['asset']==sym);assert digest(P/meta['file'])==meta['sha256'];rows=list(csv.DictReader((P/meta['file']).open()));a=raw['assets'][sym];assert a['times']==[q['dt'] for q in rows] and len(rows)==2742 and a['start']==2214 and a['end']==2742
 h,l,c,v=[[float(q[k]) for q in rows] for k in ['high','low','close','volume']];tp=[(x+y+z)/3 for x,y,z in zip(h,l,c)];atr=[];smooth=None;gain=loss=None;rsi=[float('nan')]*len(c)
 for i in range(len(c)):
  tr=max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) if i else h[i]-l[i];smooth=tr if smooth is None else smooth*13/14+tr/14;atr.append(smooth)
  if i:
   diff=c[i]-c[i-1];g=max(diff,0);d=max(-diff,0);gain=g if gain is None else gain*13/14+g/14;loss=d if loss is None else loss*13/14+d/14
   if i>=14 and loss>0:rsi[i]=100-100/(1+gain/loss)
 events=[];last=-1000
 for t in range(2221,2716):
  if t-last<25 or min(range(t-5,t+6),key=lambda k:l[k])!=t:continue
  up=next((k for k in range(t+1,t+25) if h[k]>=c[t]+2*atr[t]),None);down=next((k for k in range(t+1,t+25) if l[k]<=c[t]-atr[t]),None)
  if up is not None and (down is None or up<down):events.append((t,up));last=t
 assert events==[(e['onset'],e['hit']) for e in a['events']],('independent labels',sym)
 for e in a['events']:
  assert close(e['atr'],atr[e['onset']]) and e['close']==c[e['onset']] and e['window']==list(range(e['onset']-2,e['onset']+3)) and e['mask']==sum(1<<k for k in e['window'])
 valid=set(range(2219,2718));assert int(a['valid'],16)==sum(1<<k for k in valid);masks=[]
 for q in raw['grid']:
  n=q['n'];family=q['family'];condition=[False]*len(c);values=[float('nan')]*len(c)
  for i in range(n-1,len(c)):
   ids=range(i-n+1,i+1)
   if family=='BB':
    mean=sum(c[k] for k in ids)/n;sd=math.sqrt(sum((c[k]-mean)**2 for k in ids)/n);band=mean-q['k']*sd;condition[i]=l[i]<=band<c[i]
   elif family=='VWAP':
    total=sum(v[k] for k in ids);mean=sum(tp[k]*v[k] for k in ids)/total;sd=math.sqrt(sum(v[k]*(tp[k]-mean)**2 for k in ids)/total);band=mean-q['k']*sd;condition[i]=l[i]<=band<c[i]
   elif family=='CCI':
    mean=sum(tp[k] for k in ids)/n;dev=sum(abs(tp[k]-mean) for k in ids)/n;values[i]=(tp[i]-mean)/(.015*dev) if dev else float('nan')
   elif family=='WR':
    high=max(h[k] for k in ids);low=min(l[k] for k in ids);values[i]=-100*(high-c[i])/(high-low) if high!=low else float('nan')
   elif family=='STOCHRSI':
    z=[rsi[k] for k in ids]
    if all(math.isfinite(x) for x in z) and max(z)>min(z):values[i]=(rsi[i]-min(z))/(max(z)-min(z))
   else:raise AssertionError(family)
  if family in ['CCI','WR','STOCHRSI']:condition=[i>0 and values[i-1]<q['t']<=values[i] for i in range(len(c))]
  bits={i for i,x in enumerate(condition) if x};assert sum(1<<i for i in bits)==int(a['masks'][len(masks)],16),(sym,q['id'],'scalar indicator');masks.append(bits);mask_checks+=1
 data[sym]={'h':h,'l':l,'c':c,'atr':atr,'times':a['times'],'events':events,'valid':valid,'masks':masks}
print('INDEPENDENT_INDICATORS_LABELS_PASS',mask_checks,{s:len(d['events']) for s,d in data.items()},flush=True)
def alerts(d,aa,bb,mode):
 a=d['masks'][aa]
 if mode=='S':truth=a
 elif mode=='AND0':truth=a&d['masks'][bb]
 else:
  b=d['masks'][bb];truth={i+k for i in a for k in range(3)}&{i+k for i in b for k in range(3)}
 return {i for i in truth if i-1 not in truth and i in d['valid']}
def score(bits,d):
 matches={};used=set()
 for i in sorted(bits):
  for j,(onset,hit) in enumerate(d['events']):
   if j not in used and abs(i-onset)<=2:matches[i]=j;used.add(j);break
 ns=len(bits);tp=len(used);ne=len(d['events']);return [ns,tp,sum(i-d['events'][j][0] for i,j in matches.items())],{'signals':ns,'matched_events':tp,'events':ne,'precision':tp/ns if ns else 0,'recall':tp/ne if ne else 0,'f1':2*tp/(ns+ne) if ns+ne else 0},matches
import statistics,numpy as np
expected=[];groups=[];records=[]
for kid,aa,bb,mode in keys:
 per=[];group=[];lags=[]
 for sym,d in data.items():
  bits=alerts(d,aa,bb,mode);_,m,matches=score(bits,d);m['asset']=sym;per.append(m);group.append(bits)
  for i in sorted(bits):
   j=matches.get(i);onset=d['events'][j][0] if j is not None else None
   if j is not None:lags.append(i-onset)
   records.append({'candidate':kid,'asset':sym,'bar':i,'time':d['times'][i],'event':j,'onset':onset,'lag':i-onset if j is not None else None,'mae_atr_24':min(0,min(d['l'][i+1:i+25])-d['c'][i])/d['atr'][i],'mfe_atr_24':max(0,max(d['h'][i+1:i+25])-d['c'][i])/d['atr'][i]})
 ns=sum(x['signals'] for x in per);tp=sum(x['matched_events'] for x in per);ne=sum(x['events'] for x in per)
 row={'candidate':kid,'signals':ns,'matched_events':tp,'events':ne,'precision':tp/ns if ns else 0.,'recall':tp/ne if ne else 0.,'f1':2*tp/(ns+ne) if ns+ne else 0.,'macro_f1':statistics.mean(x['f1'] for x in per),'per_asset':per,'lag_median':statistics.median(lags) if lags else None};expected.append(row);groups.append(group)
for name in ['SHARED','PERSONAL']:
 choices={s:frozen['shared']['selected'] if name=='SHARED' else frozen['per_asset'][s]['selected'] for s in assets}
 assert all(v==17312 for v in choices.values());row=dict(expected[1]);row.pop('candidate');row.update(name=name,choices=choices);expected.append(row);groups.append(groups[1])
def compare(x,y,path=''):
 if isinstance(x,dict):
  for k,v in x.items():compare(v,y[k],path+'/'+k)
 elif isinstance(x,list):
  assert len(x)==len(y),path
  for i,(a,b) in enumerate(zip(x,y)):compare(a,b,path+'/'+str(i))
 elif isinstance(x,float):assert close(x,y),(path,x,y)
 else:assert x==y,(path,x,y)
for row in expected:
 n=row['signals'];p=row['precision'];z=1.959963984540054;low=(p+z*z/(2*n)-z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n) if n else 0.
 checks={'lag_median_at_most_1':row['lag_median'] is not None and row['lag_median']<=1,'sample':n>=100 and all(q['signals']>=20 and q['events']>=3 for q in row['per_asset']),'precision_070':p>=.7,'recall_030':row['recall']>=.3,'precision_each_055':all(q['precision']>=.55 for q in row['per_asset']),'wilson_low_060':low>=.6}
 row['quality']={'status':'INSUFFICIENT_SAMPLE' if not checks['sample'] else 'QUALITY_CANDIDATE_ONLY' if all(checks.values()) else 'NOT_CONFIRMED','wilson95_low_descriptive':low,'checks':checks}
compare(expected,res['cases_fixed_order']+res['policies'])
cells=[]
for group in groups:
 a=[[0,0,0] for _ in range(12)]
 for bits,d in zip(group,data.values()):
  _,_,matches=score(bits,d)
  for onset,_ in d['events']:a[(onset-2219)//42][2]+=1
  for i in bits:
   j=matches.get(i);anchor=d['events'][j][0] if j is not None else i;b=(anchor-2219)//42;a[b][0]+=1;a[b][1]+=j is not None
 cells.append(a)
assert cells==res['weekly_counts']
rng=np.random.default_rng(87007);indices=rng.integers(0,12,size=(10000,12));sums=np.zeros((5,10000,3))
for s in range(5):
 for slot in range(12):sums[s]+=np.asarray(cells[s])[indices[:,slot]]
pp=np.divide(sums[:,:,1],sums[:,:,0],out=np.zeros((5,10000)),where=sums[:,:,0]>0);rr=np.divide(sums[:,:,1],sums[:,:,2],out=np.zeros((5,10000)),where=sums[:,:,2]>0)
for i,(diff,obs,margin) in enumerate([(pp[2]-pp[0],expected[2]['precision']-expected[0]['precision'],.1),(rr[2]-rr[1],expected[2]['recall']-expected[1]['recall'],.1),(pp[4]-pp[3],0.,0.)]):
 lo,hi=np.quantile(diff,[.05/6,1-.05/6],method='linear');status='IDENTICAL_FROZEN_POLICIES' if i==2 else 'CONDITIONAL_GAIN' if lo>margin else 'NOT_CONFIRMED'
 compare({'observed_delta':obs,'required_delta':margin,'simultaneous_interval':[float(lo),float(hi)],'status':status},res['inference']['tests'][i])
compare({'seed':87007,'repetitions':10000,'block_bars':42,'blocks':12,'family':3,'interval_level':1-.05/3,'personal_recall_delta':0.},res['inference'])
for row in res['baselines']:
 per=[]
 for d in data.values():
  name=row['name'];bits=set() if name=='NONE' else d['valid'] if name=='EVERY_BAR' else {i for i in d['valid'] if (i-2219)%5==0};_,m,_=score(bits,d);per.append(m)
 compare({'per_asset':per,'macro_f1':statistics.mean(x['f1'] for x in per)},row)
compare(records,read('alerts.json'));assert res['no_holdout_reselection'] and res['specialization_identical_choices']
report={'status':'PASS','delivery_commit':'ae57878017bc92c0e64a4c655c65160a6f1e0e7d','independent_indicator_masks':mask_checks,'events_by_asset':{s:len(d['events']) for s,d in data.items()},'candidate_asset_rows':9,'policy_asset_rows':6,'weekly_cells_checked':180,'bootstrap_repetitions':10000,'alert_diagnostics_checked':len(records),'cases':expected[:3],'policies':expected[3:],'inference':res['inference'],'baselines':res['baselines'],'new_experiment_run':False}
(R/'lead_audit.json').write_text(json.dumps(report,indent=2));print('LEAD_AUDIT_PASS',json.dumps({k:v for k,v in report.items() if k not in ['cases','policies','baselines']},indent=2),flush=True)
