"""Frozen historical transfer validation. Reuses L0085 definitions; no grid search."""
from pathlib import Path
import json,gzip,hashlib,csv,io,math,sys
import numpy as np
import research85 as R
import signals85 as S
ROOT=Path(__file__).resolve().parent

def registration():
 frozen=json.loads((ROOT/'frozen_selection.json').read_text());original=json.loads((ROOT/'original_grid.json').read_text());assert original==S.catalogue()
 assert frozen['frozen_candidate_ids']==[17312,338952,48501,43187,48543,338754,9899,17334,17292,16893]
 parents=sorted({k for q in frozen['rules'] for k in [q['a'],q['b']]});grid=[original[i] for i in parents];keys=[(i,parents.index(i),-1,'S') for i in parents]
 for q in frozen['rules']:
  assert q['rule']==[original[q['a']],original[q['b']]]
  keys.append((q['candidate'],parents.index(q['a']),parents.index(q['b']),q['mode']))
 return frozen,parents,grid,keys

def holm(values):
 order=sorted(range(len(values)),key=lambda i:(values[i],i));out=[0.]*len(values);last=0.
 for k,i in enumerate(order):last=max(last,min(1.,values[i]*(len(values)-k)));out[i]=last
 return out

def rotate(x,offset,mask):
 first=(mask&-mask).bit_length()-1;n=mask.bit_count();local=x>>first
 return (((local<<offset)|(local>>(n-offset)))&((1<<n)-1))<<first

def setup(synthetic):
 frozen,parents,grid,keys=registration();panels=R.fixture() if synthetic else R.load_market();raw={'synthetic':synthetic,'grid':grid,'keys':[list(k) for k in keys],'parents_original_ids':parents,'frozen_sha256':R.sha(ROOT/'frozen_selection.json'),'scope_sha256':R.sha(ROOT/'scope.json'),'assets':{}}
 for sym,d in panels.items():
  start=260 if synthetic else d['dt'].index('2025-04-05T00:00:00Z');end=len(d['c']);masks=S.build(d,grid);cuts=[300,355] if synthetic else [1750,2000];nchecks=0
  for cut in cuts:
   shorter=S.build({k:v[:cut] for k,v in d.items()},grid)
   for q in grid:assert np.array_equal(shorter[q['id']],masks[q['id']][:cut]);nchecks+=1
  ev=R.labels(d,start,end);assert [(e['onset'],e['hit']) for e in ev]==R.labels_reference(d,start,end)
  for e in ev:e['mask']=sum(1<<i for i in e['window'])
  valid=sum(1<<i for i in range(start+5,end-24));raw['assets'][sym]={'start':start,'end':end,'times':d['dt'],'valid':hex(valid),'masks':[hex(R.pack(masks[q['id']])) for q in grid],'events':ev,'prefix_checks':nchecks}
 return raw,panels

def metrics(key,raw,reference=False):
 row=R.row_for(tuple(key),R.inflate(raw),reference);d=R.detail(raw,dict(zip(R.HEADER,row)))
 return d

def rescore(bits,raw,reference=False):
 fs=[];counts=[]
 for x,a in zip(bits,raw['assets'].values()):
  ns,tp,lag=(R.score_reference if reference else R.score)(x,a['events']);ne=len(a['events']);fs.append(2*tp/(ns+ne) if ns+ne else 0);counts.append([ns,tp,lag])
 return sum(fs)/3,counts

def gate(d,discovery,parent_rows,baseline,adjusted):
 eligible=d['signals']>=15 and d['matched_events']>=6 and all(v['signals']>=3 and v['events']>=3 for v in d['per_asset'])
 checks={'sample':eligible,'precision_at_least_050':d['precision']>=.5,'recall_at_least_030':d['recall']>=.3,'retain_80pct_discovery_macro_f1':d['macro_f1']>=.8*discovery,'beat_both_parents':d['macro_f1']>max(p['macro_f1'] for p in parent_rows),'beat_periodic_baseline':d['macro_f1']>baseline,'two_assets_not_below_best_parent':sum(d['per_asset'][i]['f1']>=max(p['per_asset'][i]['f1'] for p in parent_rows) for i in range(3))>=2,'holm_at_most_005':adjusted<=.05}
 status='INSUFFICIENT_SAMPLE' if not eligible else 'CONDITIONAL_TRANSFER_PASS' if all(checks.values()) else 'NOT_CONFIRMED'
 return status,checks

def derive(raw,reference=False):
 frozen,parents,grid,keys=registration();assert raw['keys']==[list(k) for k in keys] and raw['grid']==grid
 rows={k[0]:metrics(k,raw,reference) for k in keys};data=R.inflate(raw);ns={int(a['valid'],16).bit_count() for a in raw['assets'].values()};assert len(ns)==1;n=ns.pop();all_controls=[];pvalues=[];baselines=[]
 for name in ['NONE','EVERY_BAR','EVERY_5_BARS']:
  arrays=[]
  for valid,_,ev in data:
   first=(valid&-valid).bit_length()-1;arrays.append(0 if name=='NONE' else valid if name=='EVERY_BAR' else sum(1<<i for i in R.bits(valid) if (i-first)%5==0))
  f,c=rescore(arrays,raw,reference);baselines.append({'name':name,'macro_f1':f,'counts':c})
 for q,key in zip(frozen['rules'],keys[len(parents):]):
  arrays=[R.combine(masks[key[1]],masks[key[2]],key[3],valid) for valid,masks,_ in data];observed=rows[key[0]]['macro_f1'];null=[]
  for offset in range(n):
   if reference:
    shifted=[]
    for x,(valid,_,_) in zip(arrays,data):
     first=(valid&-valid).bit_length()-1;shifted.append(sum(1<<(first+(i-first+offset)%n) for i in R.bits(x)))
   else:shifted=[rotate(x,offset,valid) for x,(valid,_,_) in zip(arrays,data)]
   score,counts=rescore(shifted,raw,reference);null.append(score);all_controls.append({'candidate':key[0],'offset':offset,'macro_f1':score,'counts':counts})
  # Entire cyclic group including offset zero; upper-tail ties retained.
  pvalues.append(sum(v>=observed-1e-12 for v in null)/n)
 adjusted=holm(pvalues);result=[]
 for i,q in enumerate(frozen['rules']):
  d=rows[q['candidate']];parents_rows=[rows[q['a']],rows[q['b']]];status,checks=gate(d,q['macro_f1'],parents_rows,baselines[2]['macro_f1'],adjusted[i]);d.update(discovery_rank=i+1,discovery_macro_f1=q['macro_f1'],retention_ratio=d['macro_f1']/q['macro_f1'],best_parent_macro_f1=max(p['macro_f1'] for p in parents_rows),p_cyclic=pvalues[i],p_holm=adjusted[i],status=status,checks=checks);result.append(d)
 return {'pairs_original_order':result,'parents':[rows[k] for k in parents],'baselines':baselines,'cyclic_controls':all_controls,'cyclic_group_size':n}

def run(out,synthetic=False,stop_after_raw=False):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);raw,panels=setup(synthetic);b=gzip.compress(json.dumps(raw,sort_keys=True).encode(),mtime=0)
 if (out/'raw_signals.json.gz').exists():assert (out/'raw_signals.json.gz').read_bytes()==b,'changed raw evidence'
 else:R.atomic(out/'raw_signals.json.gz',b)
 R.write_json(out/'checkpoint.json',{'raw_sha256':R.sha(out/'raw_signals.json.gz'),'source_scope_sha256':raw['scope_sha256'],'state':'RAW_READY'})
 if stop_after_raw:print('SYNTHETIC_INTERRUPTION_AT_RAW',flush=True);return
 derived=derive(raw);reference=derive(raw,True);assert derived==reference,'independent logical/count/rotation audit mismatch'
 R.write_json(out/'validation.json',derived);R.write_json(out/'frozen_selection.json',json.loads((ROOT/'frozen_selection.json').read_text()));alerts=[]
 for row in derived['pairs_original_order']:
  for sym,(valid,masks,ev) in zip(R.ASSETS,R.inflate(raw)):
   x=R.combine(masks[row['a']],masks[row['b']],row['mode'],valid);used=set();d=panels[sym];atr=R.I.wilder_atr(d['h'],d['l'],d['c'],14)
   for bar in R.bits(x):
    j=next((j for j,e in enumerate(ev) if j not in used and abs(e['onset']-bar)<=2),None)
    if j is not None:used.add(j)
    alerts.append({'candidate':row['candidate'],'asset':sym,'bar':bar,'time':raw['assets'][sym]['times'][bar],'event':j,'onset':ev[j]['onset'] if j is not None else None,'lag':bar-ev[j]['onset'] if j is not None else None,'mae_atr_24':float(min(0,np.min(d['l'][bar+1:bar+25])-d['c'][bar])/atr[bar]),'mfe_atr_24':float(max(0,np.max(d['h'][bar+1:bar+25])-d['c'][bar])/atr[bar])})
 R.write_json(out/'alerts.json',alerts)
 audit={'status':'PASS','synthetic':synthetic,'pairs':10,'parents':12,'candidate_asset_rows':66,'full_scalar_mode_and_matching_audit':True,'all_cyclic_controls_recomputed':len(derived['cyclic_controls']),'raw_sha256':R.sha(out/'raw_signals.json.gz')};R.write_json(out/'audit.json',audit)
 primary=derived['pairs_original_order'][0];delivery={'status':'VALIDATION_COMPLETE_LEAD_REVIEW_PENDING','synthetic':synthetic,'rows':22,'primary_id':17312,'primary_result':primary['status'],'any_secondary_pass':[r['candidate'] for r in derived['pairs_original_order'][1:] if r['status']=='CONDITIONAL_TRANSFER_PASS'],'no_reselection':True,'adoption':'NOT AUTHORISED'};R.write_json(out/'delivery.json',delivery)
 report(out,derived,synthetic);R.write_json(out/'checkpoint.json',{'raw_sha256':R.sha(out/'raw_signals.json.gz'),'state':'AUDITED_COMPLETE','outputs':{p.name:R.sha(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!='checkpoint.json'}})
 print(json.dumps({'status':delivery['status'],'synthetic':synthetic,'pairs':10,'parents':12,'audit':'PASS'}),flush=True)

def audit_only(out):
 out=Path(out);check=json.loads((out/'checkpoint.json').read_text());assert check['state']=='AUDITED_COMPLETE'
 for name,h in check['outputs'].items():assert R.sha(out/name)==h,('altered evidence',name)
 raw=json.loads(gzip.decompress((out/'raw_signals.json.gz').read_bytes()));assert raw['frozen_sha256']==R.sha(ROOT/'frozen_selection.json') and raw['scope_sha256']==R.sha(ROOT/'scope.json');assert derive(raw,True)==json.loads((out/'validation.json').read_text());print('INDEPENDENT_AUDIT_PASS',flush=True)

def report(out,d,synthetic):
 first=d['pairs_original_order'][0];lines=['# L0086 — التحقق من الأزواج المجمدة','',
 '1. تحقق تاريخي من عشرة أزواج على BTC وETH وSOL، أربع ساعات، 5 أبريل–30 يونيو 2025.' if not synthetic else '1. فحص اصطناعي فقط؛ السوق not measured.',
 '2. صافي المال: not measured؛ خارج الهدف.','3. الصفقات: not measured؛ الأعداد إشارات وأحداث.','4. معامل الربح: not measured.',
 '5. التحقق: الأرقام أدناه؛ التاريخ منظور سابقًا وليس أعمى.','6. الاحتفاظ: not measured.',
 '7. الحكم الأولي للمرشح الرئيسي: '+first['status']+'؛ اعتماد التداول مؤجل.',
 '8. التالي: Lead يعيد الحساب ويحكم؛ لا اختيار بديل تلقائي.','',
 '## 1. الهوية','| الحقل | القيمة |','|---|---|','| المصدر والقواعد | scope.json + frozen_selection.json |','| الرئيسي الثابت | 17312: BB_20_2.5 + VWAP_30_1.5 AND0 |',
 '## 2. المال','| المقاييس | الحالة |','|---|---|','| الربحية والتكاليف والتوقع المالي | not measured |',
 '## 3. النتائج بترتيب الاكتشاف الثابت','| الترتيب | المرشح | إشارات | ملتقط | الدقة | الاسترجاع | Macro F1 | Holm | الحالة |','|---|---|---:|---:|---:|---:|---:|---:|---|']
 for q in d['pairs_original_order']:lines.append(f"| {q['discovery_rank']} | {q['candidate']} | {q['signals']} | {q['matched_events']} | {q['precision']:.6f} | {q['recall']:.6f} | {q['macro_f1']:.6f} | {q['p_holm']:.6f} | {q['status']} |")
 lines+=['## 4. الحركة والمخاطر','| المقياس | الدليل |','|---|---|','| توقيت كل تنبيه وMAE/MFE بوحدة ATR | alerts.json |','| مخاطر رأس المال | not measured |',
 '## 5. المكوّنات والجوار','| المقياس | الدليل |','|---|---|','| المقارنة بكل مكوّن منفرد | validation.json: parents, best_parent_macro_f1 |','| جوار ±20% جديد | not measured؛ ممنوع إعادة الضبط |',
 '## 6. الفترات','| الفترة | الوصف |','|---|---|','| يناير–مارس | discovery_macro_f1 المثبت |','| 5 أبريل–30 يونيو | هذه الجولة |','| فترة مستقبلية عمياء | not measured |','| الاحتفاظ | not measured |',
 '## 7. شروط القرار','| الشرط | الدليل |','|---|---|','| العينة والدقة والاسترجاع والاحتفاظ بنسبة80% والتفوق والمضاعفات | checks لكل زوج |','| اعتماد التداول | NOT AUTHORISED |',
 '## المصطلحات','| المصطلح | المعنى |','|---|---|','| Precision | الملتقط ÷ التنبيهات |','| Recall | الملتقط ÷ الأحداث |','| Macro F1 | متوسط 2×الملتقط/(التنبيهات+الأحداث) للعملات |','| Holm | تصحيح القيم الاحتمالية لعشرة أزواج |',
 '## الأسماء','| الاسم | المعنى |','|---|---|','| primary | متصدر الاكتشاف الثابت |','| cyclic null | إزاحة متزامنة دائرية للتنبيهات؛ استدلال مشروط بفرضية ملاءمة الإزاحة وليس ضمانًا مستقبليًا |',
 '', 'لا توصية تداول. إن أخفق الرئيسي ونجح زوج آخر فلا يُستبدل به تلقائيًا؛ ذلك سؤال متابعة جديد.',
 'إعادة التدقيق: python validate86.py audit --out PATH','']
 R.atomic(Path(out)/'REPORT.md','\n'.join(lines).encode())

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['synthetic','measure','audit']);p.add_argument('--out',required=True);p.add_argument('--stop-after-raw',action='store_true');a=p.parse_args()
 if a.mode=='audit':audit_only(a.out)
 else:run(a.out,a.mode=='synthetic',stop_after_raw=a.stop_after_raw)
