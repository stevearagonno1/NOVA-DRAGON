"""Registered BB/AND0/AND2 comparison; fixed development choices, no holdout selection."""
from pathlib import Path
import json,gzip,hashlib,math
import numpy as np
import research85 as R
import signals85 as S
ROOT=Path(__file__).resolve().parent
KEYS=[(11,0,-1,'S'),(17312,0,1,'AND0'),(17313,0,1,'AND2')]
def load(n):return json.loads((ROOT/n).read_text())
def setup(synthetic):
 grid=load('grid87.json');frozen=load('selection87.json');scope=load('scope.json');assert R.sha(ROOT/'selection87.json')==scope['selection_sha256']
 panels=R.fixture() if synthetic else R.load_market();raw={'synthetic':synthetic,'grid':grid,'keys':[list(k) for k in KEYS],'selection_sha256':R.sha(ROOT/'selection87.json'),'scope_sha256':R.sha(ROOT/'scope.json'),'assets':{}}
 for sym,d in panels.items():
  start=260 if synthetic else d['dt'].index('2025-07-05T00:00:00Z');end=len(d['c']);m=S.build(d,grid);checks=0
  for cut in ([300,355] if synthetic else [2250,2600]):
   short=S.build({k:v[:cut] for k,v in d.items()},grid)
   for q in grid:assert np.array_equal(short[q['id']],m[q['id']][:cut]);checks+=1
  ev=R.labels(d,start,end);assert [(x['onset'],x['hit']) for x in ev]==R.labels_reference(d,start,end)
  for e in ev:e['mask']=sum(1<<i for i in e['window'])
  raw['assets'][sym]={'start':start,'end':end,'times':d['dt'],'valid':hex(sum(1<<i for i in range(start+5,end-24))),'masks':[hex(R.pack(m[q['id']])) for q in grid],'events':ev,'prefix_checks':checks}
 return raw,panels

def evaluate_alerts(bits,events):
 used=set();matches={}
 for i in R.bits(bits):
  j=next((j for j,e in enumerate(events) if j not in used and abs(e['onset']-i)<=2),None)
  if j is not None:used.add(j);matches[i]=j
 return matches

def counts_metric(ns,tp,ne):return {'signals':int(ns),'matched_events':int(tp),'events':int(ne),'precision':tp/ns if ns else 0.,'recall':tp/ne if ne else 0.,'f1':2*tp/(ns+ne) if ns+ne else 0.}

def quality(row):
 sample=row['signals']>=100 and all(x['signals']>=20 and x['events']>=3 for x in row['per_asset']);p=row['precision'];n=row['signals'];z=1.959963984540054
 low=(p+z*z/(2*n)-z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n) if n else 0.
 checks={'lag_median_at_most_1':row.get('lag_median') is not None and row['lag_median']<=1,'sample':sample,'precision_070':p>=.7,'recall_030':row['recall']>=.3,'precision_each_055':all(x['precision']>=.55 for x in row['per_asset']),'wilson_low_060':low>=.6}
 return {'status':'INSUFFICIENT_SAMPLE' if not sample else 'QUALITY_CANDIDATE_ONLY' if all(checks.values()) else 'NOT_CONFIRMED','wilson95_low_descriptive':low,'checks':checks}

def infer(blocks,reference=False):
 # Synchronous fixed week clusters for all assets. Successful alerts assigned
 # to matched onset's week, false alerts to alert's week, keeping ratios bounded.
 x=np.asarray(blocks,float);k=x.shape[1];rng=np.random.default_rng(87007);indices=rng.integers(0,k,size=(10000,k));sums=x[:,indices,:].sum(axis=2)
 if reference:
  direct=np.zeros_like(sums)
  for s in range(5):
   for b in range(k):direct[s]+=x[s,indices[:,b]]
  assert np.array_equal(direct,sums)
 def rates(a):return np.divide(a[...,1],a[...,0],out=np.zeros_like(a[...,1]),where=a[...,0]>0),np.divide(a[...,1],a[...,2],out=np.zeros_like(a[...,1]),where=a[...,2]>0)
 bp,br=rates(sums);op,orr=rates(x.sum(axis=1));alpha=.05/3
 tests=[('AND2_precision_vs_BB',bp[2]-bp[0],op[2]-op[0],.1),('AND2_recall_vs_AND0',br[2]-br[1],orr[2]-orr[1],.1),('PERSONAL_precision_vs_SHARED',bp[4]-bp[3],op[4]-op[3],0.)];out=[]
 for name,diff,obs,margin in tests:
  lo,hi=np.quantile(diff,[alpha/2,1-alpha/2],method='linear');identical=name.startswith('PERSONAL') and np.array_equal(x[3],x[4]);status='IDENTICAL_FROZEN_POLICIES' if identical else 'INSUFFICIENT_BLOCKS' if k<8 else 'CONDITIONAL_GAIN' if lo>margin and (not name.startswith('PERSONAL') or orr[4]>=orr[3]-.05) else 'NOT_CONFIRMED'
  out.append({'hypothesis':name,'observed_delta':float(obs),'required_delta':margin,'simultaneous_interval':[float(lo),float(hi)],'status':status})
 return {'seed':87007,'repetitions':10000,'block_bars':42,'blocks':k,'family':3,'interval_level':1-.05/3,'assumption':'week-cluster resampling approximately exchangeable; historical data previously observed; descriptive ratios and conditional intervals are not adoption','tests':out,'personal_recall_delta':float(orr[4]-orr[3])}

def derive(raw,reference=False):
 assert raw['grid']==load('grid87.json') and raw['keys']==[list(k) for k in KEYS]
 data=R.inflate(raw);frozen=load('selection87.json');valids=[v for v,_,_ in data];starts=[(v&-v).bit_length()-1 for v in valids];assert len(set(starts))==1;first=starts[0];n=valids[0].bit_count();assert all(v.bit_count()==n for v in valids);blocks_n=(n+41)//42
 cases=[R.detail(raw,dict(zip(R.HEADER,R.row_for(k,data,reference)))) for k in KEYS];rowmap={x['candidate']:x for x in cases};arrays=[]
 for key in KEYS:
  group=[]
  for valid,m,ev in data:
   if reference:
    aa=[bool(m[key[1]]&(1<<i)) for i in range(valid.bit_length())];bb=[bool(m[key[2]]&(1<<i)) for i in range(valid.bit_length())] if key[2]>=0 else None
    truth=[aa[i] if key[3]=='S' else aa[i] and bb[i] if key[3]=='AND0' else any(aa[max(0,i-2):i+1]) and any(bb[max(0,i-2):i+1]) for i in range(len(aa))];bits=sum(1<<i for i in range(len(aa)) if truth[i] and (i==0 or not truth[i-1]) and valid&(1<<i))
   else:bits=R.combine(m[key[1]],m[key[2]] if key[2]>=0 else None,key[3],valid)
   group.append(bits)
  arrays.append(group)
 policies=[]
 for name,choices in [('SHARED',{s:frozen['shared']['selected'] for s in R.ASSETS}),('PERSONAL',{s:frozen['per_asset'][s]['selected'] for s in R.ASSETS})]:
  per=[rowmap[choices[s]]['per_asset'][i] for i,s in enumerate(R.ASSETS)];row=counts_metric(sum(x['signals'] for x in per),sum(x['matched_events'] for x in per),sum(x['events'] for x in per));row.update(name=name,choices=choices,per_asset=per,macro_f1=sum(x['f1'] for x in per)/3);policies.append(row);arrays.append([arrays[[k[0] for k in KEYS].index(choices[s])][i] for i,s in enumerate(R.ASSETS)])
 totals=[]
 for group in arrays:
  cells=np.zeros((blocks_n,3),dtype=np.int64)
  for bits,(_,_,ev) in zip(group,data):
   matches=evaluate_alerts(bits,ev)
   for e in ev:cells[(e['onset']-first)//42,2]+=1
   for bar in R.bits(bits):
    j=matches.get(bar);anchor=ev[j]['onset'] if j is not None else bar;b=(anchor-first)//42;cells[b,0]+=1;cells[b,1]+=j is not None
  totals.append(cells.tolist())
 for row,cells in zip(cases+policies,totals):
  assert [sum(q[i] for q in cells) for i in range(3)]==[row['signals'],row['matched_events'],row['events']], 'weekly counts do not reconcile'
 for row,group in zip(cases+policies,arrays):
  lag=[]
  for bits,(_,_,ev) in zip(group,data):
   for i,j in evaluate_alerts(bits,ev).items():lag.append(i-ev[j]['onset'])
  row['lag_median']=float(np.median(lag)) if lag else None;row['quality']=quality(row)
 baselines=[]
 for name in ['NONE','EVERY_BAR','EVERY_5_BARS']:
  per=[]
  for valid,m,ev in data:
   bits=0 if name=='NONE' else valid if name=='EVERY_BAR' else sum(1<<i for i in R.bits(valid) if (i-first)%5==0);ns,tp,lag=(R.score_reference if reference else R.score)(bits,ev);per.append(counts_metric(ns,tp,len(ev)))
  baselines.append({'name':name,'per_asset':per,'macro_f1':sum(x['f1'] for x in per)/3})
 return {'cases_fixed_order':cases,'policies':policies,'weekly_counts':totals,'inference':infer(totals,reference),'baselines':baselines,'no_holdout_reselection':True,'specialization_identical_choices':policies[0]['choices']==policies[1]['choices']}

def run(out,synthetic=False,stop_after_raw=False):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);raw,panels=setup(synthetic);b=gzip.compress(json.dumps(raw,sort_keys=True).encode(),mtime=0)
 if (out/'raw_signals.json.gz').exists():assert (out/'raw_signals.json.gz').read_bytes()==b,'changed raw evidence'
 else:R.atomic(out/'raw_signals.json.gz',b)
 R.write_json(out/'checkpoint.json',{'state':'RAW_READY','raw_sha256':R.sha(out/'raw_signals.json.gz')})
 if stop_after_raw:return
 d=derive(raw);assert d==derive(raw,True),'independent scalar/cluster audit failed';R.write_json(out/'comparison.json',d);R.write_json(out/'selection87.json',load('selection87.json'));alerts=[]
 for key in KEYS:
  for sym,(valid,m,ev) in zip(R.ASSETS,R.inflate(raw)):
   x=R.combine(m[key[1]],m[key[2]] if key[2]>=0 else None,key[3],valid);matches=evaluate_alerts(x,ev);p=panels[sym];atr=R.I.wilder_atr(p['h'],p['l'],p['c'],14)
   for i in R.bits(x):
    j=matches.get(i);alerts.append({'candidate':key[0],'asset':sym,'bar':i,'time':raw['assets'][sym]['times'][i],'event':j,'onset':ev[j]['onset'] if j is not None else None,'lag':i-ev[j]['onset'] if j is not None else None,'mae_atr_24':float(min(0,np.min(p['l'][i+1:i+25])-p['c'][i])/atr[i]),'mfe_atr_24':float(max(0,np.max(p['h'][i+1:i+25])-p['c'][i])/atr[i])})
 R.write_json(out/'alerts.json',alerts);audit={'status':'PASS','synthetic':synthetic,'cases':3,'policies':2,'candidate_asset_rows':9,'policy_asset_rows':6,'reference_counts_and_clusters':True,'bootstrap_reps':10000,'raw_sha256':R.sha(out/'raw_signals.json.gz')};R.write_json(out/'audit.json',audit);delivery={'status':'COMPARISON_COMPLETE_LEAD_REVIEW_PENDING','synthetic':synthetic,'rows':5,'no_reselection':True,'adoption':'NOT AUTHORISED','policy_identity':d['specialization_identical_choices']};R.write_json(out/'delivery.json',delivery);report(out,d,synthetic)
 R.write_json(out/'checkpoint.json',{'state':'AUDITED_COMPLETE','raw_sha256':R.sha(out/'raw_signals.json.gz'),'outputs':{p.name:R.sha(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!='checkpoint.json'}});print(json.dumps({'status':delivery['status'],'synthetic':synthetic,'audit':'PASS','cases':3,'policies':2}),flush=True)

def audit_only(out):
 out=Path(out);c=json.loads((out/'checkpoint.json').read_text());assert c['state']=='AUDITED_COMPLETE'
 for name,h in c['outputs'].items():assert R.sha(out/name)==h,('altered evidence',name)
 raw=json.loads(gzip.decompress((out/'raw_signals.json.gz').read_bytes()));assert raw['selection_sha256']==R.sha(ROOT/'selection87.json') and raw['scope_sha256']==R.sha(ROOT/'scope.json');assert derive(raw,True)==json.loads((out/'comparison.json').read_text());print('INDEPENDENT_AUDIT_PASS',flush=True)

def report(out,d,synthetic):
 lines=['# L0087 — التزامن والتخصيص المحدود','', '1. '+('فحص اصطناعي؛ السوق not measured.' if synthetic else 'مقارنة3 إشارات على BTC/ETH/SOL،5 يوليو–30 سبتمبر2025،4h.'),'2. صافي المال: not measured.','3. الصفقات: not measured؛ أعداد تنبيهات وأحداث فقط.','4. معامل الربح: not measured.','5. التحقق: هذه الفترة،لا إعادة اختيار.','6. الاحتفاظ: not measured.','7. اعتماد الإشارة: Defer؛ NOT AUTHORISED.','8. التالي: مراجعة Lead من الخام.','','## 1. الهوية','| الحقل | القيمة |','|---|---|','| المصدر | scope.json وselection87.json |','','## 2. المال','| المقاييس المالية | الحالة |','|---|---|','| كلها | not measured |','','## 3. الحالات والخيارات المجمدة','| الحالة | تنبيهات | ملتقط | دقة | استرجاع | Macro F1 | الجودة |','|---|---:|---:|---:|---:|---:|---|']
 for x in d['cases_fixed_order']+d['policies']:lines.append(f"| {x.get('candidate',x.get('name'))} | {x['signals']} | {x['matched_events']} | {x['precision']:.6f} | {x['recall']:.6f} | {x['macro_f1']:.6f} | {x['quality']['status']} |")
 lines+=['','## 4. الحركة والمخاطر','| القياس | الدليل |','|---|---|','| وقت كل تنبيه وMAE/MFE | alerts.json |','','## 5. المقارنة والاستدلال','| الفرضية | الفرق | مجال متزامن98.333% | الحكم المشروط |','|---|---:|---|---|']
 for x in d['inference']['tests']:lines.append(f"| {x['hypothesis']} | {x['observed_delta']:.6f} | {x['simultaneous_interval']} | {x['status']} |")
 lines+=['','## 6. الفترات','| الفترة | الوصف |','|---|---|','| يناير–يونيو2025 | اختيار تطوير فقط؛ ليس تحققًا جديدًا |','|5 يوليو–30 سبتمبر2025|هذه المقارنة|','|فترة عمياء مستقبلية|not measured|','','## 7. شروط الحكم','| الشرط | الحالة |','|---|---|','| جودة70% وعينة100 | quality لكل حالة؛ لا تعويض للشروط الفاشلة |','|التخصيص|الاختيارات المجمدة متطابقة؛ الشبكة الصغيرة لم تفرق العملات في التطوير|','|اختيار فائز من التحقق|ممنوع|','','## المصطلحات','| المصطلح | المعنى |','|---|---|','|Precision|الملتقط/التنبيهات|','|Recall|الملتقط/الأحداث|','|Macro F1|متوسط F1 للعملات|','','## الأسماء','| الرمز | المعنى |','|---|---|','|11|BB20_2.5 منفردًا|','|17312|BB20_2.5 + VWAP30_1.5 AND0|','|17313|الزوج نفسه AND2|','','مجالات الكتل الزمنية مشروطة بملاءمة إعادة المعاينة،وليست ضمانًا مستقبليًا. Wilson وصفي يفترض استقلال التنبيهات. هذه3 خيارات فقط؛لا استنتاج أن التخصيص غير مفيد عمومًا.','']
 R.atomic(Path(out)/'REPORT.md','\n'.join(lines).encode())

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['synthetic','measure','audit']);p.add_argument('--out',required=True);p.add_argument('--stop-after-raw',action='store_true');a=p.parse_args()
 if a.mode=='audit':audit_only(a.out)
 else:run(a.out,a.mode=='synthetic',stop_after_raw=a.stop_after_raw)
