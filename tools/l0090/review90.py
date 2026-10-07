from pathlib import Path
import json,hashlib,gzip,math,time,argparse
P=Path(__file__).parent;args=argparse.ArgumentParser();args.add_argument('--out',default='l0090/market');M=Path(args.parse_args().out);load=lambda n:json.loads((M/n).read_text());r=load('results.json');rows=r['rows'];audit=load('audit.json');assert audit['status']=='PASS' and not audit['synthetic'];assert len(rows)==441;assert len({(x['asset'],x['candidate']) for x in rows})==441
old=json.loads((M/'prior-results89.json').read_text())['rows'];oldmap={(x['asset'],x['candidate']):x for x in old};checked=0
for x in rows:
 key=(x['asset'],x['candidate'])
 if key in oldmap:
  for k,v in oldmap[key].items():
   if k!='p_holm324':assert x[k]==v,(key,k)
  checked+=1
assert checked==360
pairs=[x for x in rows if x['pair']];states=[x for x in pairs if x['mode']=='STATE_NOW'];assert len(states)==81
# Independently reconstruct every recorded p-value and the full Holm405 family from raw null parts.
pvals=[]
for x in pairs:
 part=json.loads(gzip.decompress((M/(x['asset']+'-'+x['candidate']+'.json.gz')).read_bytes()));v=part['null_matched_by_period'];assert len(v)==10000 and all(len(q)==3 for q in v)
 p=(1+sum(sum(z)>=x['matched_events'] for z in v))/10001;assert p==x['p_phase_shift'];pvals.append(p)
order=sorted(range(405),key=lambda i:(pvals[i],i));a=0.
for rank,i in enumerate(order):a=max(a,min(1,(405-rank)*pvals[i]));assert a==pairs[i]['p_holm405']
summary={}
for asset in ['BTCUSDT','ETHUSDT','SOLUSDT']:
 subset=[x for x in states if x['asset']==asset];parents=[x for x in rows if x['asset']==asset and x['candidate'].startswith('PRICE_')];best=sorted(subset,key=lambda x:(-x['recall'],-x['precision'],int(x['candidate'])))[0]
 eligible=[x for x in pairs if x['asset']==asset and x['eligible']];assert not eligible
 for x in subset:
  parent=next(y for y in parents if y['a']==x['a']);assert x['signals']<=parent['signals'];assert x['matched_events']<=parent['matched_events'];assert x['added_events_vs_price']==0
  assert x['marginal_hypothesis_pass']==(x['precision']-parent['precision']>=.1 and x['recall']>=.8*parent['recall'] and parent['recall']>0)
 summary[asset]={'eligible_pairs':0,'maximum_new_state_recall':max(x['recall'] for x in subset),'maximum_new_state_signals':max(x['signals'] for x in subset),'max_recall_example':best,'price_parents':parents,'marginal_hypothesis_passes':sum(x['marginal_hypothesis_pass'] for x in subset)}
selection=load('selection.json');assert all(v is None for v in selection['selected_by_asset'].values());assert selection['quality']['status']=='INSUFFICIENT_SAMPLE'
review={'decision':'D-L0090-REVIEW-20261007','verdict':'Defer','scope_outcome':'valid negative for the81 tested persistent volume filters','source_commit':'c01b1d255acf6c1c167e3b87e64da3cbe34ea5d3','rows':441,'pairs':405,'new_states':81,'independent_scalar_audit':audit,'inherited_rows_regression_checked':checked,'independent_p_and_holm_parts_checked':405,'per_asset':summary,'state_marginal_hypothesis_passes':sum(x['marginal_hypothesis_pass'] for x in states),'adoption':'NOT AUTHORISED','discovery_only':True,'future_validation_run':False,'scope_metadata_notes':['pairs_each_asset108 is inherited pulse-control count; actual135 pairs per asset=108 controls+27 states,441 rows total','inference_warning literal Holm324 is inherited text; executable scope and all p-values useHolm405','market_authorisation NOT RUN is preparation snapshot; owner authorised execution on2026-10-07T20:01:58+03:00'],'next':'Diagnose CCI standalone false alerts and missed rise events to define a new causal price reversal trigger; do not add another volume filter blindly.'}
(M/'lead-review.json').write_text(json.dumps(review,indent=2)+'\n')
lines=['# مراجعة القائد L0090 — تأكيد الحجم المستمر','','**D-L0090-REVIEW-20261007 — Defer.** التنفيذ والتدقيق سليم؛لا مزيج مؤهل،ولا نجاح للفرضية الوصفية في أي من81 حالة حجم مستمر. النتيجة سلبية صالحة لهذه الشبكة فقط؛لا حكم على جميع استخدامات الحجم أو المؤشرات.','','المصدر المثبت قبل القياس: `c01b1d255acf6c1c167e3b87e64da3cbe34ea5d3`؛النطاق والمعايير فيPREPARATION.md وscope.json. إذن التشغيل:رسالةالمالك«نفذ»2026-10-07T20:01:58+03:00. القائد نفذ القياس الخفيف والتدقيق والتسليم؛لا مهمة للمنفّذ.','','## ما تحقق بالفعل','','441 صفًا (405 أزواج تشمل81حالة جديدة،و36منفردًا) عبر3عملات و3مقاطع تاريخية2025. أعادالمسارالمرجعي بناء12,150,000 عدًّا للضوابط؛PASS. قورنت360حالة موروثة بنتائجL0089 وطابقت كل مقاييسها وpالخام؛Holmأعيد تصحيحه على405حالات. أُعيدحساب405قيمةp وتصحيحHolm من ملفاتالضوابط فيبرنامجالمراجعة،وتحققت الأهلية والاختيارات والفرضية الهامشية منالعدّ والأحداثالمحفوظة. نجح108فحص حساب/بادئة على حالاتالحجم في الشموعالحقيقية.','','## الحالات الجديدة فقط — ليست اختيارات مؤهلة','','|العملة|الأزواج المؤهلة بين135 زوجًا|أعلى استرجاع بين27حالة جديدة|أعلى عدد تنبيهات للحالةالجديدة|نجاحات فرضيةزيادةالدقة10نقاط والاحتفاظ80%|','|---|---:|---:|---:|---:|']
for a,s in summary.items():lines.append(f"|{a}|0|{s['maximum_new_state_recall']:.2%}|{s['maximum_new_state_signals']}|{s['marginal_hypothesis_passes']}|")
lines+=['','أمثلة أعلى استرجاع،للتشخيص فقط،مرتبة بالاسترجاع والدقة؛ليست فائزين أو إعادة اختيار:','','|العملة|نبضة السعر|حالة الحجم|التنبيهات|الملتقط/الأحداث|الدقة|الاسترجاع|','|---|---|---|---:|---:|---:|---:|']
for a,s in summary.items():
 x=s['max_recall_example'];lines.append(f"|{a}|{x['a']}|{x['b']}|{x['signals']}|{x['matched_events']}/{x['events']}|{x['precision']:.2%}|{x['recall']:.2%}|")
lines+=['','كلحالة جديدة هي تقاطع مع نبضةالسعر نفسها،وبذلك لا يمكنها إضافة تنبيه أوحدث جديد خارج نبضاتالسعر؛الأحداثالمضافة صفر كما تحقق الحساب. بعضها رفع الدقة على حساب فقد معظم الأحداث،ولا واحدة حققت زيادة10نقاط مع الاحتفاظ80%من الاسترجاع. لا تتحقق بوابةالأهلية أوالدقة العالية.','','selection.json يحويnull لكلعملة،وINSUFFICIENT_SAMPLE حالة اختيار التجميع؛أصفاره ليست ادعاء عدم وجود أحداث سوق. الأحداث المرجعية106:BTC37،ETH33،SOL36. غياب الأهلية ليس نقصعينةفقط:أعلى استرجاع لكل الحالات الجديدة دون30%.','','## الحدود والتصحيحات','','جميع الفترات تاريخية سبق الاطلاع عليها؛اكتشاف فقط لا تحقق أعمى. Holm405 يختبر محاذاةالتوقيت المشروطة بالإزاحات،وليس دلالة التحسن الهامشي على السعر،ولا يصحح جميعمحاولاتالمشروع السابقة. لا مال أوتداول أوتكاليف أو ربحية مقاسة.','','scope.json احتفظ بثلاثة أوصاف زمنية قديمة:108 هو عددضوابطالنبضات لكلعملة،والعددالفعلي135؛نصتحذيرHolm324 القديم لا يحدد الحساب،الذي استعمل405؛NOT RUN وصفمرحلةالإعداد قبل إذنالتنفيذ. الحسابات وبصماتالنطاق صحيحة،والتوضيح هنا تصحيحعلني دون تغييرالنطاق بعدالنتيجة. لايعاد تفسيرهذهالأوصاف لتصغيرالميزانية.','','## التالي','','تشخيص التنبيهاتالكاذبة والأحداث التي فاتتCCI منفردًا،تمهيدًا لتثبيت إشارة انعكاس سعرية جديدة. لا مزيدمنمرشحاتالحجم فوق نفسالنبضة قبلالتشخيص،ولا تخفيفلشروطالدقة والاسترجاع. هذه ليست بداية تلقائية لتجربة جديدة.','','## إعادة الحساب','','```bash','python tools/l0090/experiment90.py measure --out l0090/market','python tools/l0090/experiment90.py audit --out l0090/market','python tools/l0090/review90.py','```','','المراجعةالكاملة والضوابط فيأرشيفالأدلة؛بصمته ومساحته وقياسالوقت فيdelivery.json.']
text='\n'.join(lines)+'\n';(M/'LEAD-REVIEW.md').write_text(text);Path('deliverables').mkdir(exist_ok=True);Path('deliverables/L0090-LEAD-REVIEW.md').write_text(text)
# Supplement the original seven-table report with actual measured retained-recall information.
report=(M/'REPORT.md').read_text().replace('6. الاحتفاظ: not measured؛المقارنة بالمنفرد مثبتة.','6. الاحتفاظ:Measured مقارنة باسترجاع السعر؛لا حالة جديدة حققت فرضيةزيادةالدقة10نقاط والاحتفاظ80%.')
report+='\n\n## نتيجة المراجعةالمثبتة\nلا مرشح مؤهل؛INSUFFICIENT_SAMPLE للاختيار،و0/81نجاحللفرضيةالوصفية. التفاصيل فيLEAD-REVIEW.md.\n';(M/'REPORT.md').write_text(report)
print(json.dumps({'per_asset':{a:{k:v for k,v in s.items() if k not in ['max_recall_example','price_parents']} for a,s in summary.items()},'audit':'PASS','verdict':'Defer'},indent=2))
