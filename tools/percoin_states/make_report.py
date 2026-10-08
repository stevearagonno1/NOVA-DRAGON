import pathlib,json,statistics
P=pathlib.Path(__file__).parent;M=P/'market';rows=json.loads((M/'results.json').read_text());sel=json.loads((M/'selection.json').read_text());S={'BREAKOUT':'اختراق بعد نطاق محدود','PULLBACK':'استئناف بعد تراجع داخل اتجاه','TURN':'تحول صعود أولي خارج الاتجاه المثبت'}
def get(asset,state,h,i):return next((r for r in rows if (r['asset'],r['state'],r['hours'],r['id'])==(asset,state,h,i)),None)
def pct(x):return 'لم يُقَس' if x is None else f'{x:.2%}'
def meaning(i):
 if i is None:return 'لا مرشح مؤهل للعينة المبدئية'
 c=i//4;v=(i%4)//2;m=i%2
 return ['شرط الحالة فقط','شمعة قوية','إغلاق فوق قمة السابقة','شمعة قوية وإغلاق فوق قمة السابقة'][c]+(' +حجم1.5' if v else '')+(' +RSI≥50 وصاعد' if m else '')
comparison=[]
for p in sel['personal']:
 s=next(s for s in sel['shared'] if (s['state'],s['hours'])==(p['state'],p['hours']));r=get(p['asset'],p['state'],p['hours'],p['id']);b=get(p['asset'],p['state'],p['hours'],s['id'])
 comparison.append({'asset':p['asset'],'state':p['state'],'hours':p['hours'],'personal_id':p['id'],'shared_id':s['id'],'personal':r,'shared':b,'same_candidate':p['id']==s['id']})
(M/'comparison.json').write_text(json.dumps(comparison,ensure_ascii=False,indent=2)+'\n')
lines=['# اكتشاف مزيج لكل عملة وحالة — PERCOIN-STATE-DISCOVERY-20261008','',
'1. BTC وETH وSOL؛ثلاث حالات سببية،16تركيبًا لكل خلية،دخول15دقيقة،يوليو2026؛يونيو تسخين.',
'2. صافي الأموال:لم يُقَس؛لا تداول أو خروج مالي.',
'3.144حالة مرشحة و288صف تقييم؛10036نتيجة تنبيه تشمل التكرار بين المرشحين والأفقين،وليست10036صفقة أو إشارة مستقلة.',
'4.الربحية والتكاليف:لم تُقَس.',
'5.تحقق أغسطس:لم يُشغّل؛الاختيارات مجمدة فيselection.json.',
'6.شراء واحتفاظ:خارج مرحلة الإشارات.',
'7.Defer اعتماد التخصيص أو أي مرشح؛العينة والثبات خارج الاكتشاف لم يتحققا.',
'8.التالي:Lead يتحقق من الاختيارات المجمدة على أغسطس دون إعادة اختيار؛المقارنة خفيفة،لا ورقة للوكيل الآن.']
def table(title,heads,rr):
 lines.extend(['','## '+title,'|'+'|'.join(heads)+'|','|'+'|'.join(['---']*len(heads))+'|']);lines.extend('|'+'|'.join(str(x) for x in r)+'|' for r in rr)
table('1.هوية التجربة',['البند','القيمة'],[['العملات','BTC/ETH/SOL'],['الحالات','اختراق،استئناف،تحول أولي؛ترتيب أولوية ثابت'],['الإطار','15m؛سياق آخر1hمكتملة'],['تعريف النجاح اليومي','+2ATR قبل−1ATR خلال24h'],['تعريف النجاح الأسبوعي','+4ATR قبل−2ATR خلال168h'],['سعر المرجع','افتتاح الدقيقة التالية للإشارة'],['النطاق','يوليو تقويمي،لا اختيار فترة بناء على أفضل مؤشر'],['المصادر','sources.json؛main6d0226a03b84656e14b94dd8a37e39332cc2f68f']])
table('2.المال',['المقياس','القيمة'],[['الربح/الخسارة/رسوم/انزلاق/خروج','لم يُقَس؛خارج النطاق']])
for h,label in [(24,'3.نتائج اليوم'),(168,'3ب.نتائج أفق الأسبوع')]:
 table(label,['العملة','الحالة','المزيج المخصص','ناجح/صالح','دقته','المزيج المشترك','ناجح/صالح','دقته'],[[c['asset'],S[c['state']],meaning(c['personal_id']),f"{c['personal']['success']}/{c['personal']['n']}" if c['personal'] else 'لا اختيار',pct(c['personal']['precision']) if c['personal'] else 'لا اختيار',meaning(c['shared_id']),f"{c['shared']['success']}/{c['shared']['n']}" if c['shared'] else 'لا اختيار',pct(c['shared']['precision']) if c['shared'] else 'لا اختيار'] for c in comparison if c['hours']==h])
table('4.العينة وعدم اليقين',['العملة','الحالة','الأفق','Nمخصص','Wilson95وصفي','مستبعد لقصر المستقبل'],[[c['asset'],S[c['state']],c['hours'],c['personal']['n'] if c['personal'] else None,[pct(v) for v in c['personal']['wilson95_descriptive']] if c['personal'] else None,c['personal']['censored'] if c['personal'] else None] for c in comparison])
table('5.الثبات والجيران',['الفحص','الحالة'],[['التخصيص مقابل المشترك على اكتشاف واحد','وصف فقط؛التخصيص مستفيد من اختيار نفس البيانات'],['جيران ±20%','لم يُقَس في هذه الشبكة'],['تغطية موجات القيعان وتأخر البداية','لم يُقَس في المرحلة الحالية؛لا ننقل أرقام تجربةSOLالسابقة'],['التأخير التشغيلي','إشارة عند الإغلاق؛لا كاشف لحظي قبل إغلاق15m'],['استقلال التنبيهات','غير مثبت؛فصل6hلكلعملة/حالة/مرشح وليس لكل محفظة'],['تسمية الحالة','فرضية تشغيلية سببية؛ليست إثباتًا لموجة ناجحة']])
table('6.الفترات والمقارنة الإجمالية',['الأفق','المخصص نجاح/صالح','دقته','المشترك نجاح/صالح','دقته'],[[h,f"{sum(c['personal']['success'] for c in comparison if c['hours']==h and c['personal'])}/{sum(c['personal']['n'] for c in comparison if c['hours']==h and c['personal'])}",pct(sum(c['personal']['success'] for c in comparison if c['hours']==h and c['personal'])/sum(c['personal']['n'] for c in comparison if c['hours']==h and c['personal'])),f"{sum(c['shared']['success'] for c in comparison if c['hours']==h and c['shared'])}/{sum(c['shared']['n'] for c in comparison if c['hours']==h and c['shared'])}",pct(sum(c['shared']['success'] for c in comparison if c['hours']==h and c['shared'])/sum(c['shared']['n'] for c in comparison if c['hours']==h and c['shared']))] for h in (24,168)])
table('7.شروط الحكم',['الشرط','المطلوب','الحالة'],[['دقة عالية','≥70%','بعض نقاط الاكتشاف قد تبلغها؛لا حكم خارج البحث'],['عينة تحقق','≥100تنبيه صالح لكل مرشح','لم تتحقق؛N≥5للانتقاء المبدئي فقط'],['Wilsonسفلي','≥60%وصفي مع تدقيق الاعتماد','لا مرشح منتخب اجتاز'],['اختيارات مجمدة','18مخصصًا و6مشتركة','تحققت وأعيد اشتقاقها مستقلاً'],['تحقق مستقل','أغسطس بالقواعد والاختيارات نفسها','لم يُشغّل'],['تفوق التخصيص','مقارنة ثابتة خارج الاكتشاف','غير مثبت'],['اعتماد تداول أو مال','إذن ومرحلة مالية مستقلة','غير مأذون']])
table('قاموس التنفيذ',['الرمز','المعنى'],[['TURN','تحول أولي محتمل:السياق ليس صاعدًا،شمعةخضراء،الإغلاق أعلىالسابق،RSIصاعد'],['PULLBACK','سياقEMA20>50صاعد،تراجع لEMA20في4شموع سابقة ثم استرداد أخضر'],['BREAKOUT','إغلاق فوق قمة20شمعةسابقة،وعرضنطاقها≤4ATRساعة'],['شمعة قوية','جسم≥نصفالمدى،إغلاقفيالربعالعلوي،خضراء'],['الحجم','الحجم الحالي≥1.5متوسط20شمعةسابقة'],['مشترك','اختيار واحد لكل حالة وأفق يطبق على العملات الثلاث'],['مخصص','اختيار مختلف ممكن لكل عملة/حالة/أفق'],['Wilson','حد وصفي؛ليس ضمانًا أوتصحيحًا للبحث المتعدد']])
lines+=['','## التدقيق المستقل والحكم','independent-audit.json أعاد اشتقاق10036نتيجة تنبيه،288صفًا،18اختيارًا مخصصًا و6مشتركة من الدقائق الخام،دون استيراد محرك القياس. تحققATRبصيغةأُسّية مستقلة،وحواجز الدقيقة،والعد،ومعيار الاختيار. فحصscalarللحالات داخل المحرك مشترك في المؤشرات؛ليس تدقيقًا مستقلًا كاملاً لتعريف كل مؤشر.',
'أبرز نتيجة منتخبة:ETH/تحول أولي/أفق أسبوع/حجم1.5+RSI≥50وصاعد=11/15=73.33%؛Wilsonسفلي48.05%فقط،ولا ادعاء باكتمال موجة لمدةأسبوع؛الأفق هوحد الانتظار. لا توصية بالتداول أو تبنّي الحالة. تصنيفكلشمعة بالحالة يستخدمالماضي فقط؛الشمعات غير المصنفة لا تولدإشارة،ولا تُسقط تنبيهات مصنفة بسبب فشلها اللاحق.',
'نستنتج إمكانية تنظيم البحث حسب العملة والحالة،لا أن التخصيص أقوى. فشل هذه الشبكة في شروطالاعتماد لا يغلق كل المؤشرات أوكلالتأكيدات. لاشرطاحتفاظ80%بالاسترجاع؛الأولوية للدقة،مع بقاءالعينة والصدق خارج فترة البحث.',
'قرار D-PERCOIN-STATE-DISCOVERY-20261008:Defer اعتماد أي مرشح أو التخصيص. تجميدselection.json شرط قبل تحققأغسطس؛يُختبر الجميع المختارون،ولا يُستبدل الفاشل ببديل رآهLeadعلىالتحقق.',
'إعادة التشغيل:python download_inputs.py؛PYTHONPATH=<PyArrowالمجهز> python prepare_inputs.py؛python test_pilot.py؛python pilot.py --out market؛python independent_audit.py؛python make_report.py. SOL-source الأصلي يصل عبرdata/SOLUSDT_1m.parquetبالالتزامالمثبت؛prepare_inputs.pyيسجل البصمة والمسار. لا تشغيل البوت الأصلي أو طلب بيانات مالية خاصة.']
(M/'REPORT.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'different_personal_from_shared':sum(not c['same_candidate'] for c in comparison),'pairs':len(comparison),'daily_personal':[(c['asset'],c['state'],c['personal']['success'],c['personal']['n']) for c in comparison if c['hours']==24],'selected_quality_pass':sum(c['personal']['descriptive_quality'] for c in comparison if c['personal'])}))
