"""Registered marginal volume confirmation; checkpointed compute and scalar audit."""
from pathlib import Path
import json,gzip,hashlib,math,time,argparse
import numpy as np
import research85 as R
import signals88 as S
ROOT=Path(__file__).parent

def load(n):return json.loads((ROOT/n).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):R.write_json(p,x)
def raw(synthetic):
 scope=load('scope.json');assert sha(ROOT/'parent_raw.json.gz')==scope['raw_parent_sha256'] and sha(ROOT/'selection88.json')==scope['selection_sha256']
 if not synthetic:return json.loads(gzip.decompress((ROOT/'parent_raw.json.gz').read_bytes()))
 out={'synthetic':True,'assets':{}}
 for asset,d in R.fixture().items():
  masks=S.primitives(d);periods=[]
  for start,end in [(180,260),(260,340),(340,420)]:
   ev=R.labels(d,start,end)
   for e in ev:e['mask']=sum(1<<i for i in e['window'])
   periods.append({'start':start,'end':end,'valid':list(range(start+5,end-24)),'events':ev})
  out['assets'][asset]={'masks':{k:hex(R.pack(v)) for k,v in masks.items()},'periods':periods,'times':d['dt']}
 return out

def keys():
 s=load('scope.json');out=[]
 for asset in s['assets']:
  for ai,a in enumerate(s['price'][asset]):
   out.append({'asset':asset,'candidate':'PRICE_'+str(ai),'a':a,'b':None,'mode':'S','pair':False})
  for bi,b in enumerate(s['volumes']):out.append({'asset':asset,'candidate':'VOLUME_'+str(bi),'a':b['id'],'b':None,'mode':'S','pair':False})
  for ai,a in enumerate(s['price'][asset]):
   for bi,b in enumerate(s['volumes']):
    for mi,mode in enumerate(s['modes']):out.append({'asset':asset,'candidate':str(ai*36+bi*4+mi),'a':a,'b':b['id'],'mode':mode,'pair':True})
 assert len(out)==360;return out

def combine(a,b,mode,valid,reference=False):
 if reference:
  aa=set(R.bits(a));bb=set(R.bits(b)) if b is not None else set();truth=[]
  for i in range(valid.bit_length()):
   v=i in aa if mode=='S' else i in aa and i in bb if mode=='AND0' else any(i-z in aa for z in range(3)) and any(i-z in bb for z in range(3)) if mode=='AND2' else i in bb and any(i-z in aa for z in [1,2]) if mode=='PRICE_THEN_VOLUME2' else i in aa and any(i-z in bb for z in [1,2]);truth.append(v)
  return sum(1<<i for i,v in enumerate(truth) if v and (i==0 or not truth[i-1]) and valid&(1<<i))
 if mode=='S':truth=a
 elif mode=='AND0':truth=a&b
 elif mode=='AND2':truth=(a|(a<<1)|(a<<2))&(b|(b<<1)|(b<<2))
 elif mode=='PRICE_THEN_VOLUME2':truth=b&((a<<1)|(a<<2))
 elif mode=='VOLUME_THEN_PRICE2':truth=a&((b<<1)|(b<<2))
 else:raise ValueError(mode)
 return truth&~(truth<<1)&valid

def rotate(bits,first,n,offset):
 x=bits>>first;mask=(1<<n)-1;return (((x<<offset)|(x>>(n-offset)))&mask)<<first

def data_for(q,a,reference=False):
 masks=a['masks'];aa=int(masks[q['a']],16);bb=int(masks[q['b']],16) if q['b'] else None;out=[]
 for p in a['periods']:
  v=sum(1<<i for i in p['valid']);bits=combine(aa,bb,q['mode'],v,reference);ev=p['events']
  for e in ev:e['mask']=sum(1<<i for i in e['window'])
  out.append((bits,ev,p['valid'][0],len(p['valid'])))
 return out

def row(q,d,reference=False):
 c=[(R.score_reference if reference else R.score)(bits,ev) for bits,ev,_,_ in d];per=[R.metric(z[0],z[1],len(x[1])) for z,x in zip(c,d)];ns=sum(x['signals'] for x in per);tp=sum(x['matched_events'] for x in per);ne=sum(x['events'] for x in per);out={**q,**R.metric(ns,tp,ne),'periods':per,'lag_sum':sum(x[2] for x in c)};out['eligible']=ns>=20 and out['recall']>=.3 and all(x['signals']>=3 and x['recall']>=.15 for x in per);out['minimum_period_precision']=min(x['precision'] for x in per)
 captured=[];lag=[]
 for bits,ev,_,_ in d:
  hits=[]
  for e in ev:
   candidates=[i for i in R.bits(bits) if abs(i-e['onset'])<=2] if reference else list(R.bits(bits&e['mask']))
   if candidates:hits.append(e['onset']);lag.append(min(candidates)-e['onset'])
  captured.append(hits)
 out['captured_onsets_by_period']=captured;out['median_lag']=float(np.median(lag)) if lag else None;out['matched_lags']=lag
 return out

def nulls(d,offsets,reference=False):
 out=[]
 score=R.score_reference if reference else R.score
 for offsets3 in offsets:
  value=[]
  for off,(bits,ev,first,n) in zip(offsets3,d):
   if reference:
    moved={first+(i-first+int(off))%n for i in R.bits(bits)};shifted=sum(1<<i for i in moved)
   else:shifted=rotate(bits,first,n,int(off))
   value.append(score(shifted,ev)[1])
  out.append(value)
 return out

def run(out,synthetic=False,audit=False,stop_after=None):
 begin=time.monotonic();out=Path(out);out.mkdir(parents=True,exist_ok=True);rr=raw(synthetic);k=64 if synthetic else 10000;s=load('scope.json');seed=89007;rng=np.random.default_rng(seed);first=next(iter(rr['assets'].values()));lengths=[len(p['valid']) for p in first['periods']];offsets=np.column_stack([rng.integers(0,n,size=k) for n in lengths]);write(out/'control_offsets.json',offsets.tolist()) if not audit else None
 if audit:assert json.loads((out/'control_offsets.json').read_text())==offsets.tolist()
 rawbytes=gzip.compress(json.dumps(rr,sort_keys=True).encode(),mtime=0);rp=out/'raw.json.gz'
 if rp.exists():assert rp.read_bytes()==rawbytes,'changed raw; do not overwrite'
 else:assert not audit;rp.write_bytes(rawbytes)
 results=[];done=0
 for q in keys():
  path=out/(q['asset']+'-'+q['candidate']+'.json.gz');d=data_for(q,rr['assets'][q['asset']],audit);x=row(q,d,audit)
  if q['pair']:
   if path.exists() and not audit:
    saved=json.loads(gzip.decompress(path.read_bytes()));assert saved['row']==x and saved['offset_sha256']==sha(out/'control_offsets.json');x=saved['row']
   else:
    receipt=out/('audited-'+q['asset']+'-'+q['candidate']+'.json')
    cached=audit and receipt.exists() and json.loads(receipt.read_text())=={'part_sha256':sha(path),'offset_sha256':sha(out/'control_offsets.json'),'scope_sha256':sha(ROOT/'scope.json')}
    values=json.loads(gzip.decompress(path.read_bytes()))['null_matched_by_period'] if cached else nulls(d,offsets,audit)
    if audit:
     saved=json.loads(gzip.decompress(path.read_bytes()));assert saved['row']==x and saved['null_matched_by_period']==values and saved['offset_sha256']==sha(out/'control_offsets.json'),('null audit',q)
     write(receipt,{'part_sha256':sha(path),'offset_sha256':sha(out/'control_offsets.json'),'scope_sha256':sha(ROOT/'scope.json')})
    else:R.atomic(path,gzip.compress(json.dumps({'row':x,'offset_sha256':sha(out/'control_offsets.json'),'null_matched_by_period':values},sort_keys=True).encode(),mtime=0))
  results.append(x);done+=1
  if done%12==0:print('AUDIT' if audit else 'MEASURE',done,'/',360,flush=True)
  if stop_after is not None and done>=stop_after:return
 pairs=[x for x in results if x['pair']];pvals=[]
 for x in pairs:
  saved=json.loads(gzip.decompress((out/(x['asset']+'-'+x['candidate']+'.json.gz')).read_bytes()));obs=x['matched_events'];pvals.append((1+sum(sum(v)>=obs for v in saved['null_matched_by_period']))/(k+1))
 order=sorted(range(324),key=lambda i:(pvals[i],i));last=0;adjusted=[0.]*324
 for rank,i in enumerate(order):last=max(last,min(1,(324-rank)*pvals[i]));adjusted[i]=last
 for x,p,h in zip(pairs,pvals,adjusted):
  x['p_phase_shift']=p;x['p_holm324']=h
  parent=next(r for r in results if r['asset']==x['asset'] and r['candidate']=='PRICE_'+str(int(x['candidate'])//36))
  x['precision_delta_vs_price']=x['precision']-parent['precision'];x['recall_delta_vs_price']=x['recall']-parent['recall']
  x['added_events_vs_price']=sum(len(set(a)-set(b)) for a,b in zip(x['captured_onsets_by_period'],parent['captured_onsets_by_period']));x['lost_events_vs_price']=sum(len(set(b)-set(a)) for a,b in zip(x['captured_onsets_by_period'],parent['captured_onsets_by_period']))
 summary={'synthetic':synthetic,'settings_asset':360,'pairs_asset':324,'control_draws_each':k,'null_asset_period_counts':324*k*3,'seed':seed,'family':324,'no_adoption':True,'data_previously_observed':True,'rows':results};payload=(json.dumps(summary,sort_keys=True,indent=2)+'\n').encode()
 if audit:assert (out/'results.json').read_bytes()==payload
 else:R.atomic(out/'results.json',payload)
 selections={}
 for asset in s['assets']:
  eligible=sorted([x for x in pairs if x['asset']==asset and x['eligible']],key=lambda x:(-x['minimum_period_precision'],-x['precision'],-x['recall'],int(x['candidate'])));selections[asset]=eligible[0]['candidate'] if eligible else None
 chosen=[next(x for x in pairs if x['asset']==asset and x['candidate']==kid) for asset,kid in selections.items() if kid is not None]
 ns=sum(x['signals'] for x in chosen);tp=sum(x['matched_events'] for x in chosen);ne=sum(x['events'] for x in chosen);p=tp/ns if ns else 0.;z=1.959963984540054;lower=(p+z*z/(2*ns)-z*math.sqrt(p*(1-p)/ns+z*z/(4*ns*ns)))/(1+z*z/ns) if ns else 0.;lags=[v for x in chosen for v in x['matched_lags']]
 checks={'all_assets':len(chosen)==3,'sample':ns>=100 and all(x['signals']>=20 for x in chosen),'precision070':p>=.7,'recall030':ne>0 and tp/ne>=.3,'asset_precision055':len(chosen)==3 and all(x['precision']>=.55 for x in chosen),'wilson060':lower>=.6,'median_lag1':bool(lags) and float(np.median(lags))<=1,'conditional_holm005':len(chosen)==3 and all(x['p_holm324']<=.05 for x in chosen)}
 selection={'quality':{'status':'INSUFFICIENT_SAMPLE' if not checks['sample'] else 'DISCOVERY_CANDIDATE_ONLY' if all(checks.values()) else 'NOT_CONFIRMED','checks':checks,'signals':ns,'matched_events':tp,'events':ne,'precision':p,'recall':tp/ne if ne else 0.,'wilson95_low_descriptive':lower},'selected_by_asset':selections,'discovery_only':True,'no_reselection_from_validation':True,'adoption':'NOT AUTHORISED'}
 if audit:assert json.loads((out/'selection.json').read_text())==selection
 else:write(out/'selection.json',selection);report(out,results,selections)
 status={'status':'PASS' if audit else 'MEASUREMENT_COMPLETE_AUDIT_PENDING','synthetic':synthetic,'rows':360,'pairs':324,'control_draws_each':k,'null_asset_period_counts':324*k*3,'elapsed_seconds':time.monotonic()-begin,'scope_sha256':sha(ROOT/'scope.json'),'raw_sha256':sha(rp),'adoption':'NOT AUTHORISED'};write(out/('audit.json' if audit else 'measure.json'),status)
 if audit:write(out/'checkpoint.json',{'status':'DISCOVERY_COMPLETE_LEAD_REVIEW_PENDING','files':{p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='checkpoint.json'}})
 print(json.dumps(status),flush=True)

def report(out,rows,selected):
 lines=['# L0089 — أثر تأكيد الحجم','', '1.108 وصفات دمج لكل عملة،3 عملات،ثلاث فترات تطوير2025.','2. المال: not measured.','3. الصفقات: not measured؛تنبيهات وأحداث فقط.','4. الربحية: not measured.','5. تحقق أعمى: not measured؛كل المقاطع تاريخية سبق الاطلاع عليها.','6. الاحتفاظ: not measured؛المقارنة بالمنفرد مثبتة.','7. اعتماد: Defer؛مراجعة Lead مطلوبة.','8. التالي: مراجعة Lead فقط،لا مرحلة تلقائية.','','## 1. الهوية','| الحقل | القيمة |','|---|---|','| النطاق |scope.json|','','## 2. المال','| الحقل | الحالة |','|---|---|','| جميع المقاييس المالية |not measured|','','## 3. جميع النتائج','| العملة |ID|الإشارة A|تأكيد B|الوضع|تنبيهات|ملتقط/أحداث|الدقة|الاسترجاع|Holm|','|---|---|---|---|---|---:|---:|---:|---:|---:|']
 for x in rows:lines.append(f"|{x['asset']}|{x['candidate']}|{x['a']}|{x['b']}|{x['mode']}|{x['signals']}|{x['matched_events']}/{x['events']}|{x['precision']:.6f}|{x['recall']:.6f}|{x.get('p_holm324','not measured')}|")
 for n,title,content in [(4,'التوقيت','lag_sum بالمخرجات؛MAE/MFE للدمج not measured'),(5,'الثبات','counts ومقاييس كل فترة محفوظة؛الصفرية لا تسقط'),(6,'المقارنات','PRICE وVOLUME منفردان لكل عملة،ولااعتماد من أفضلية اكتشاف'),(7,'الشروط','الدقة70% والاسترجاع30% والعينة100/20 لكلعملة هدففقط؛Holmمشروطولايمحوتاريخالاختيار')]:lines+=['',f'## {n}. {title}','| الحقل | القيمة |','|---|---|',f'| الدليل |{content}|']
 lines+=['','## المصطلحات','|الاسم|المعنى|','|---|---|','|Precision|TP/NS|','|Recall|TP/N|','','## الأوضاع','|الاسم|التعريف|','|---|---|','|AND0|نبضتا المنفردين فيالحالية|','|AND2|نبضة كلمنفرد بالحالية أوالسابقتين،ثمfalse→true|','|PRICE_THEN_VOLUME2|نبضةAفي إحدىالسابقتين وBحاليًا|','|VOLUME_THEN_PRICE2|العكس دون تزامن|','','اختياراتالتطوير: '+str(selected)+'. لاAdopt. الأمر:python3 experiment89.py measure/audit --out market.']
 R.atomic(out/'REPORT.md','\n'.join(lines).encode())
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['synthetic','measure','audit']);p.add_argument('--out',required=True);p.add_argument('--synthetic-audit',action='store_true');p.add_argument('--stop-after',type=int);a=p.parse_args();run(a.out,a.mode=='synthetic' or a.synthetic_audit,a.mode=='audit',a.stop_after)
