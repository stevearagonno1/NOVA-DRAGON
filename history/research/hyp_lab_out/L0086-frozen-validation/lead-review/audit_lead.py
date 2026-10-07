from pathlib import Path
import json,gzip,csv,math,hashlib,sys,os
R=Path(__file__).resolve().parent;E=R/'market';P=Path(os.environ.get('NOVA86_PACKAGE',str(R.parent/'l0086/package')))
if not P.exists():P=next(parent/'tools/l0086' for parent in R.parents if (parent/'tools/l0086').is_dir())
def read(n):return json.loads((E/n).read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b):return math.isclose(a,b,rel_tol=1e-11,abs_tol=1e-12)
raw=json.loads(gzip.decompress((E/'raw_signals.json.gz').read_bytes()));res=read('validation.json');checkpoint=read('checkpoint.json');assert raw['synthetic'] is False
for n,h in checkpoint['outputs'].items():assert digest(E/n)==h,('file hash',n)
assert raw['scope_sha256']==digest(P/'scope.json') and raw['frozen_sha256']==digest(P/'frozen_selection.json')
frozen=json.loads((P/'frozen_selection.json').read_text());assert read('frozen_selection.json')==frozen
original=json.loads((P/'original_grid.json').read_text());parents=sorted({q[k] for q in frozen['rules'] for k in ['a','b']});assert raw['parents_original_ids']==parents
assert raw['grid']==[original[i] for i in parents];keys=[[i,parents.index(i),-1,'S'] for i in parents]+[[q['candidate'],parents.index(q['a']),parents.index(q['b']),q['mode']] for q in frozen['rules']];assert raw['keys']==keys
assets=['BTCUSDT','ETHUSDT','SOLUSDT'];data={};mask_checks=0
for sym in assets:
 meta=next(x for x in json.loads((P/'inputs.json').read_text()) if x['asset']==sym);assert digest(P/meta['file'])==meta['sha256'];rows=list(csv.DictReader((P/meta['file']).open()));a=raw['assets'][sym];assert a['times']==[q['dt'] for q in rows] and len(rows)==2190 and a['start']==1668 and a['end']==2190
 h,l,c,v=[[float(q[k]) for q in rows] for k in ['high','low','close','volume']];tp=[(x+y+z)/3 for x,y,z in zip(h,l,c)];atr=[];smooth=None;gain=loss=None;rsi=[float('nan')]*len(c)
 for i in range(len(c)):
  tr=max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) if i else h[i]-l[i];smooth=tr if smooth is None else smooth*13/14+tr/14;atr.append(smooth)
  if i:
   diff=c[i]-c[i-1];g=max(diff,0);d=max(-diff,0);gain=g if gain is None else gain*13/14+g/14;loss=d if loss is None else loss*13/14+d/14
   if i>=14 and loss>0:rsi[i]=100-100/(1+gain/loss)
 events=[];last=-1000
 for t in range(1675,2164):
  if t-last<25 or min(range(t-5,t+6),key=lambda k:l[k])!=t:continue
  up=next((k for k in range(t+1,t+25) if h[k]>=c[t]+2*atr[t]),None);down=next((k for k in range(t+1,t+25) if l[k]<=c[t]-atr[t]),None)
  if up is not None and (down is None or up<down):events.append((t,up));last=t
 assert events==[(e['onset'],e['hit']) for e in a['events']],('independent labels',sym)
 for e in a['events']:
  assert close(e['atr'],atr[e['onset']]) and e['close']==c[e['onset']] and e['window']==list(range(e['onset']-2,e['onset']+3)) and e['mask']==sum(1<<k for k in e['window'])
 valid=set(range(1673,2166));assert int(a['valid'],16)==sum(1<<k for k in valid);masks=[]
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
expected={};alertsets={}
for kid,a,b,mode in keys:
 per=[];lagcounts={};sets=[]
 for sym,d in data.items():
  bits=alerts(d,a,b,mode);counts,m,matches=score(bits,d);sets.append(bits);m['asset']=sym;per.append(m)
  for n,v in zip(['signals','matched','lag_sum'],counts):lagcounts[sym+'_'+n]=v
 ns=sum(x['signals'] for x in per);tp=sum(x['matched_events'] for x in per);ne=sum(x['events'] for x in per)
 expected[kid]={'candidate':kid,'a':a,'b':b,'mode':mode,'signals':ns,'matched_events':tp,'events':ne,'precision':tp/ns if ns else 0,'recall':tp/ne if ne else 0,'f1':2*tp/(ns+ne) if ns+ne else 0,'macro_f1':sum(x['f1'] for x in per)/3,'per_asset':per,**lagcounts};alertsets[kid]=sets
for row in res['parents']+res['pairs_original_order']:
 e=expected[row['candidate']]
 for k,v in e.items():
  if k=='per_asset':
   for x,y in zip(v,row[k]):
    for n,val in x.items():assert val==y[n] if isinstance(val,str) else close(val,y[n]),(row['candidate'],n)
  else:assert close(v,row[k]) if isinstance(v,float) else v==row[k],(row['candidate'],k)
base=[]
for name in ['NONE','EVERY_BAR','EVERY_5_BARS']:
 counts=[];f=[]
 for d in data.values():
  bits=set() if name=='NONE' else d['valid'] if name=='EVERY_BAR' else {i for i in d['valid'] if (i-1673)%5==0};c,m,_=score(bits,d);counts.append(c);f.append(m['f1'])
 entry={'name':name,'counts':counts,'macro_f1':sum(f)/3};base.append(entry)
assert base==res['baselines']
controls=iter(res['cyclic_controls']);pvals=[]
for q in frozen['rules']:
 null=[]
 for shift in range(493):
  cc=[];ff=[]
  for bits,d in zip(alertsets[q['candidate']],data.values()):
   shifted={1673+(i-1673+shift)%493 for i in bits};c,m,_=score(shifted,d);cc.append(c);ff.append(m['f1'])
  f=sum(ff)/3;row=next(controls);assert row['candidate']==q['candidate'] and row['offset']==shift and row['counts']==cc and close(row['macro_f1'],f);null.append(f)
 pvals.append(sum(x>=expected[q['candidate']]['macro_f1']-1e-12 for x in null)/493)
assert next(controls,None) is None
order=sorted(range(10),key=lambda i:(pvals[i],i));adjusted=[0]*10;last=0
for rank,i in enumerate(order):last=max(last,min(1,(10-rank)*pvals[i]));adjusted[i]=last
failures={}
for i,(q,row) in enumerate(zip(frozen['rules'],res['pairs_original_order'])):
 d=expected[q['candidate']];pr=[expected[q['a']],expected[q['b']]];sample=d['signals']>=15 and d['matched_events']>=6 and all(x['signals']>=3 and x['events']>=3 for x in d['per_asset'])
 checks={'sample':sample,'precision_at_least_050':d['precision']>=.5,'recall_at_least_030':d['recall']>=.3,'retain_80pct_discovery_macro_f1':d['macro_f1']>=.8*q['macro_f1'],'beat_both_parents':d['macro_f1']>max(x['macro_f1'] for x in pr),'beat_periodic_baseline':d['macro_f1']>base[2]['macro_f1'],'two_assets_not_below_best_parent':sum(d['per_asset'][j]['f1']>=max(x['per_asset'][j]['f1'] for x in pr) for j in range(3))>=2,'holm_at_most_005':adjusted[i]<=.05}
 status='INSUFFICIENT_SAMPLE' if not sample else 'CONDITIONAL_TRANSFER_PASS' if all(checks.values()) else 'NOT_CONFIRMED';assert row['status']==status and row['checks']==checks and close(row['p_cyclic'],pvals[i]) and close(row['p_holm'],adjusted[i]) and close(row['retention_ratio'],d['macro_f1']/q['macro_f1']);failures[str(q['candidate'])]=[k for k,v in checks.items() if not v]
records={};months={}
for q in frozen['rules']:
 for sym,bits in zip(assets,alertsets[q['candidate']]):
  d=data[sym];_,_,matches=score(bits,d)
  for i in sorted(bits):
   j=matches.get(i);onset=d['events'][j][0] if j is not None else None
   record={'candidate':q['candidate'],'asset':sym,'bar':i,'time':d['times'][i],'event':j,'onset':onset,'lag':i-onset if j is not None else None,'mae_atr_24':min(0,min(d['l'][i+1:i+25])-d['c'][i])/d['atr'][i],'mfe_atr_24':max(0,max(d['h'][i+1:i+25])-d['c'][i])/d['atr'][i]};records[(q['candidate'],sym,i)]=record
   if q['candidate']==17312:
    month=d['times'][i][:7];m=months.setdefault(month,{'alerts':0,'matched':0});m['alerts']+=1;m['matched']+=j is not None
seen=set()
for row in read('alerts.json'):
 key=(row['candidate'],row['asset'],row['bar']);assert key not in seen;seen.add(key);e=records[key];assert row.keys()==e.keys()
 for k,v in e.items():assert close(v,row[k]) if isinstance(v,float) else v==row[k],('diagnostic',key,k)
assert len(seen)==len(records)
primary=res['pairs_original_order'][0];lags=[r['lag'] for r in records.values() if r['candidate']==17312 and r['event'] is not None];primaryparents=[expected[11],expected[454]]
report={'status':'PASS','delivery_commit':'a3da7ba6f43fedfe42687e8383490bc724c1f6da','independent_scalar_indicator_masks':mask_checks,'independent_events_by_asset':{s:len(d['events']) for s,d in data.items()},'candidate_asset_rows':66,'cyclic_controls':4930,'cyclic_asset_counts':14790,'alert_diagnostics_checked':len(records),'all_numeric_gates_recomputed':True,'all_pairs_not_confirmed':all(x['status']=='NOT_CONFIRMED' for x in res['pairs_original_order']),'failures':failures,'primary':primary,'primary_parent_metrics':primaryparents,'baselines':base,'primary_lags':lags,'primary_months':months,'pairs':res['pairs_original_order'],'parents':res['parents'],'new_experiment_run':False}
(R/'lead_audit.json').write_text(json.dumps(report,indent=2));print('LEAD_AUDIT_PASS',json.dumps({k:report[k] for k in ['independent_scalar_indicator_masks','independent_events_by_asset','candidate_asset_rows','cyclic_controls','alert_diagnostics_checked','failures']},indent=2),flush=True)
