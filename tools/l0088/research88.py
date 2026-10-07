from pathlib import Path
import argparse,csv,gzip,hashlib,json,math,statistics,sys,time
import numpy as np
import signals88 as S
ROOT=Path(__file__).resolve().parent

def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);b=(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode();temp=p.with_suffix(p.suffix+'.pending');temp.write_bytes(b);temp.replace(p)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def metric(ns,tp,n):return {'signals':ns,'matched':tp,'events':n,'precision':tp/ns if ns else 0.,'recall':tp/n if n else 0.,'f1':2*tp/(ns+n) if ns+n else 0.}
def score(indices,events):
 used=set();matches={}
 for i in sorted(indices):
  for j,e in enumerate(events):
   if j not in used and abs(e['onset']-i)<=2:used.add(j);matches[i]=j;break
 return metric(len(indices),len(matches),len(events)),matches

def score_ref(indices,events):
 # Match from event side independently; 25-bar spacing makes event windows disjoint.
 used=set();matched={}
 for j,e in enumerate(events):
  a=sorted(i for i in indices if e['onset']-2<=i<=e['onset']+2 and i not in used)
  if a:used.add(a[0]);matched[a[0]]=j
 return metric(len(indices),len(used),len(events)),matched

def wilson(tp,n):
 if not n:return 0.
 p=tp/n;z=1.959963984540054
 return (p+z*z/(2*n)-z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n)

def summarize(rows):
 ns=sum(x['signals'] for x in rows);tp=sum(x['matched'] for x in rows);n=sum(x['events'] for x in rows);out=metric(ns,tp,n)
 out.update(min_period_precision=min(x['precision'] for x in rows),min_period_recall=min(x['recall'] for x in rows),wilson95_low_descriptive=wilson(tp,ns));return out

def rank(x):return (-x['min_period_precision'],-x['wilson95_low_descriptive'],-x['recall'],-x['signals'],x['candidate'])

def execute(inputs,out,synthetic=False):
 begin=time.monotonic();inputs=Path(inputs).resolve();out=Path(out);sys.path.insert(0,str(inputs));import research85 as R
 R.ROOT=inputs;scope=json.loads((ROOT/'scope.json').read_text());assert sha(inputs/'inputs.json')==scope['input_manifest_sha256']
 assert sha(inputs/'package_manifest.json')==scope['dependency_manifest_sha256']
 for n,h in json.loads((inputs/'package_manifest.json').read_text()).items():assert sha(inputs/n)==h,('dependency hash',n)
 panels=R.fixture() if synthetic else R.load_market();raw={'synthetic':synthetic,'scope_sha256':sha(ROOT/'scope.json'),'catalogue':S.catalogue(),'assets':{}};allrows=[];diagnostics=[];baselines=[];prefixes=0;reference_masks=0
 for asset,d in panels.items():
  a=S.primitives(d);ref=S.primitives(d,True)
  for key in a:assert np.array_equal(a[key],ref[key]),('scalar mismatch',asset,key);reference_masks+=1
  for cut in ([300,355] if synthetic else [1500,2600]):
   short=S.primitives({k:v[:cut] for k,v in d.items()})
   for key in a:assert np.array_equal(short[key],a[key][:cut]),('future leakage',asset,key);prefixes+=1
  if synthetic:periods=[(180,260),(260,340),(340,420)]
  else:periods=[(d['dt'].index(x),len(d['c']) if y=='2025-10-01T00:00:00Z' else d['dt'].index(y)) for x,y in scope['periods']]
  atr=R.I.wilder_atr(d['h'],d['l'],d['c'],14);ap={'masks':{k:hex(R.pack(v)) for k,v in a.items()},'periods':[],'times':d['dt']}
  for pi,(start,end) in enumerate(periods):
   ev=R.labels(d,start,end);assert [(e['onset'],e['hit']) for e in ev]==R.labels_reference(d,start,end)
   valid=set(range(start+5,end-24));ap['periods'].append({'start':start,'end':end,'events':ev,'valid':sorted(valid)})
   for key,v in a.items():
    idx=set(map(int,np.flatnonzero(v)))&valid;m,match=score(idx,ev);assert (m,match)==score_ref(idx,ev);allrows.append({'candidate':key,'asset':asset,'period':pi,**m})
    for i in sorted(idx):
     j=match.get(i);diagnostics.append({'candidate':key,'asset':asset,'period':pi,'bar':i,'time':d['dt'][i],'event':j,'onset':ev[j]['onset'] if j is not None else None,'lag':i-ev[j]['onset'] if j is not None else None,'mae_atr24':float(min(0,min(d['l'][i+1:i+25])-d['c'][i])/atr[i]),'mfe_atr24':float(max(0,max(d['h'][i+1:i+25])-d['c'][i])/atr[i])})
   for name,idx in [('NONE',set()),('EVERY_BAR',valid),('EVERY_5_BARS',{i for i in valid if (i-start-5)%5==0})]:
    m,match=score(idx,ev);assert (m,match)==score_ref(idx,ev);baselines.append({'name':name,'asset':asset,'period':pi,**m})
  raw['assets'][asset]=ap
 assert len(allrows)==324 and reference_masks==108 and prefixes==216
 assetrows=[];shared=[];selection={'synthetic':synthetic,'discovery_only':True,'no_adoption':True,'per_asset':{},'shared':{},'criteria':scope['eligibility'],'ranking':scope['ranking']}
 for asset in panels:
  selection['per_asset'][asset]={}
  for q in S.catalogue():
   rr=[x for x in allrows if x['candidate']==q['id'] and x['asset']==asset];x={'candidate':q['id'],'family':q['family'],'asset':asset,**summarize(rr)}
   x['eligible']=x['signals']>=20 and x['recall']>=.3 and all(y['signals']>=3 and y['recall']>=.15 for y in rr)
   lag=[r['lag'] for r in diagnostics if r['candidate']==q['id'] and r['asset']==asset and r['lag'] is not None];x['median_lag']=statistics.median(lag) if lag else None;assetrows.append(x)
  for family in sorted({q['family'] for q in S.catalogue()}):
   rr=sorted([x for x in assetrows if x['asset']==asset and x['family']==family and x['eligible']],key=rank);selection['per_asset'][asset][family]=rr[0]['candidate'] if rr else None
 for q in S.catalogue():
  rr=[x for x in assetrows if x['candidate']==q['id']];pr=[metric(sum(y['signals'] for y in allrows if y['candidate']==q['id'] and y['period']==p),sum(y['matched'] for y in allrows if y['candidate']==q['id'] and y['period']==p),sum(y['events'] for y in allrows if y['candidate']==q['id'] and y['period']==p)) for p in range(3)]
  x={'candidate':q['id'],'family':q['family'],**summarize(pr),'eligible':all(y['eligible'] for y in rr),'macro_f1':statistics.mean(y['f1'] for y in rr),'per_asset':rr}
  lag=[r['lag'] for r in diagnostics if r['candidate']==q['id'] and r['lag'] is not None];x['median_lag']=statistics.median(lag) if lag else None
  x['quality_checks']={'sample':x['signals']>=100 and all(y['signals']>=20 for y in rr),'precision070':x['precision']>=.7,'recall030':x['recall']>=.3,'asset_precision055':all(y['precision']>=.55 for y in rr),'wilson060':x['wilson95_low_descriptive']>=.6,'lag1':x['median_lag'] is not None and x['median_lag']<=1};x['quality']='INSUFFICIENT_SAMPLE' if not x['quality_checks']['sample'] else 'DISCOVERY_TARGET_ONLY' if all(x['quality_checks'].values()) else 'TARGET_NOT_MET';shared.append(x)
 for family in sorted({q['family'] for q in S.catalogue()}):
  rr=sorted([x for x in shared if x['family']==family and x['eligible']],key=rank);selection['shared'][family]=rr[0]['candidate'] if rr else None
 rawbytes=gzip.compress(json.dumps(raw,sort_keys=True).encode(),mtime=0);out.mkdir(parents=True,exist_ok=True)
 if (out/'raw.json.gz').exists():assert (out/'raw.json.gz').read_bytes()==rawbytes,'changed raw on restart'
 else:(out/'raw.json.gz').write_bytes(rawbytes)
 for name,value in [('results.json',allrows),('asset_summary.json',assetrows),('shared_summary.json',shared),('alerts.json',diagnostics),('baselines.json',baselines),('selection.json',selection)]:write(out/name,value)
 audit={'status':'PASS','synthetic':synthetic,'settings':36,'candidate_asset_period_rows':324,'scalar_masks':reference_masks,'prefix_masks':prefixes,'baselines':len(baselines),'alert_rows':len(diagnostics),'raw_sha256':sha(out/'raw.json.gz'),'elapsed_seconds':time.monotonic()-begin,'adoption':'NOT AUTHORISED','events_by_asset':{s:[len(p['events']) for p in z['periods']] for s,z in raw['assets'].items()}};write(out/'audit.json',audit)
 report(out,shared,assetrows,selection,audit,scope)
 write(out/'checkpoint.json',{'status':'DISCOVERY_COMPLETE_LEAD_REVIEW_PENDING','hashes':{p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='checkpoint.json'}})
 print(json.dumps(audit),flush=True);return audit

def report(out,shared,assetrows,selection,audit,scope):
 text=['# L0088 — اكتشاف إشارات منفردة لكل عملة','','1. شبكة36 إعدادًا،9 عائلات،BTC/ETH/SOL،4h،ثلاث فترات تطوير2025.','2. المال والتكاليف: not measured.','3. صفقات: not measured؛تنبيهات وأحداث فقط.','4. معامل الربح: not measured.','5. تحقق مستقل أو أعمى: not measured؛كل الفترات سبق الاطلاع عليها.','6. مقابل الاحتفاظ: not measured؛خطوط التنبيه في baselines.json.','7. القرار: Defer الاعتماد؛هذه نتائج اكتشاف فقط.','8. التالي: مراجعة مستقلة ثم تجهيز مرحلة واحدة تالية.','','## 1. هوية التجربة','| الحقل | القيمة |','|---|---|',f"| الحالات / تقييمات العملات والفترات |36 / {audit['candidate_asset_period_rows']} |",'|نوع البيانات|شموع العقود التاريخيةUSDT-M؛ليست دفتر أوامر|','','## 2. المال','| الحقل | الحالة |','|---|---|','|الربح/التوقع/الرسوم/معامل الربح|not measured|','','## 3. الإشارات المشتركة — جميع الحالات دون إسقاط','|الإشارة|تنبيهات|ملتقط / أحداث|الدقة|الاسترجاع|أضعف دقة فترة|الجودة|','|---|---:|---:|---:|---:|---:|---|']
 for x in shared:text.append(f"|{x['candidate']}|{x['signals']}|{x['matched']}/{x['events']}|{x['precision']:.2%}|{x['recall']:.2%}|{x['min_period_precision']:.2%}|{x['quality']}|")
 text+=['','## 4. الحركة والمخاطر','|القياس|المصدر|','|---|---|','|lag/MAE/MFE لكل تنبيه|alerts.json؛بوحدةATR دون تنفيذ مالي|','|السحب/الخسارة المالية|not measured|','','## 5. الفترات والثبات','|العملة|أحداث الفترات الثلاث|','|---|---|']
 for s,v in audit['events_by_asset'].items():text.append('|'+s+'|'+str(v)+'|')
 text+=['','تفاصيل324 تقييمًا،والحالات الصفرية،فيresults.json. الاختيار يرتب أدنى دقة فترة قبل حدWilson الوصفي والاسترجاع؛لا نختار قمة فترة منفردة.','','## 6. المقارنات وخيارات التطوير','|العملة|مرشحو العائلات المؤهلون|','|---|---|']
 for s,v in selection['per_asset'].items():text.append('|'+s+'|'+'، '.join(str(k)+':'+str(a) for k,a in v.items())+'|')
 text+=['','NONE/EVERY_BAR/EVERY_5_BARS محفوظة بكل أصل وفترة فيbaselines.json. المرشح العائلي يجهز بحثًا لاحقًا؛ليس تحققًا للتخصيص أو اعتمادًا.','','## 7. شروط الجودة والحدود','|الشرط|الحالة|','|---|---|','|الهدف|دقة70%،استرجاع30%،عينة100/20 لكلعملة،دقةعملة55%،Wilson60%،وسيطlag≤1|','|دلالة مصححة وتحقق مستقل|not measured؛لاp-value أو دعوى تفوق استدلالية من اكتشاف|','|نتيجة إيجابية|DISCOVERY_TARGET_ONLY إن تحققت؛لاAdopt|','','## المصطلحات','|المصطلح|المعنى|','|---|---|','|Precision|ملتقط/تنبيهات|','|Recall|ملتقط/كل أحداث الصعود|','|Wilson|حدوصفي يفترض استقلالًا؛لايصحح الاختيار|','','## أسماء العائلات','|العائلة|المعنى|','|---|---|','|OBV|حجم تراكمي موقّع باتجاه الإغلاق؛ليس تدفق أوامر فعليًا|','|TAKER_PRESSURE|نسبة حجم شراءtaker المجمع،دون إعادة بناء دفترالأوامر|','|SQUEEZE_BREAK|ضغط نطاق ثم اختراق خلالمهلةسببية|','','أمر الأرقام: python3 tools/l0088/research88.py --inputs tools/l0087 --out MARKET_DIR. تفاصيل التعريفات والتسجيل فيdocs/lanes/L0088-SINGLETON-DISCOVERY.md.']
 (out/'REPORT.md').write_text('\n'.join(text)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--inputs',required=True);p.add_argument('--out',required=True);p.add_argument('--synthetic',action='store_true');a=p.parse_args();execute(a.inputs,a.out,a.synthetic)
