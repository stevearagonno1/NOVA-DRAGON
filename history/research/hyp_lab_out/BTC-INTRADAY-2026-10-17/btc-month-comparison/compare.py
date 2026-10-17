from pathlib import Path
import json,hashlib,pandas as pd,zipfile
BASE=Path(__file__).parent
if (BASE/'january2024').exists():
 OLD=BASE/'january2024';P=BASE/'december2025'
else:
 P=BASE;OLD=P.parent/'btc-month-study'
a=json.loads((OLD/'summary.json').read_text());b=json.loads((P/'summary.json').read_text());assert a['source_sha256']==b['source_sha256'];assert (OLD/'analyze_month.py').read_bytes()==(P/'analyze_month.py').read_bytes();assert b['registration']['month']!='2024-01';audit=[]
for folder,s in [(OLD,a),(P,b)]:
 e=pd.read_csv(folder/'events.csv');d=pd.read_csv(folder/'daily_counts.csv');assert len(e)==s['events']==d.total.sum();assert e.category.value_counts().to_dict()=={k:v for k,v in s['category_counts'].items() if v};assert e[['rebound','breakout','trend']].sum().to_dict()==s['overlapping_flag_counts'];assert all(pd.to_datetime(e.time_aden,utc=True).diff().dropna().ge(pd.Timedelta(hours=1)));assert len(d)==31;assert s['month_minute_rows']==44640;assert s['audit']=='PASS';audit.append({'month':s['registration']['month'],'count_reconciliation':'PASS','events':len(e),'same_analyzer':True,'same_source_hash':True})
x=pd.read_csv(P/'bars15m.csv',index_col='close_time_utc');x.index=pd.to_datetime(x.index,utc=True);diff=[]
for row in json.loads((P/'external_check.json').read_text())['result']:
 z=x.loc[pd.to_datetime(row[6],unit='ms',utc=True)];delta=[abs(float(z[k])-float(row[j+1])) for j,k in enumerate(['open','high','low','close','volume'])];assert max(delta)<1e-7;diff.append(max(delta))
manifest={'source_commit':b['registration']['source_commit'],'source_sha256':b['source_sha256'],'retained_minute_slice_sha256':hashlib.sha256((P/'source_minutes.csv').read_bytes()).hexdigest(),'external_sample_count':3,'external_max_abs_difference':max(diff),'scope':'BTC Spot December2025; 3 external candles only'};(P/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
result={'first_month':a['registration']['month'],'second_month':b['registration']['month'],'events':[a['events'],b['events']],'change_pct':100*(b['events']/a['events']-1),'audit':audit,'same_primary_threshold_pct':0.5,'same_monitoring_minutes':15,'same_minimum_event_spacing_minutes':60,'same_intraday_lookback_minutes':60,'same_timezone':'Asia/Aden','flag_ranking_same':sorted(a['overlapping_flag_counts'],key=a['overlapping_flag_counts'].get,reverse=True)==sorted(b['overlapping_flag_counts'],key=b['overlapping_flag_counts'].get,reverse=True),'external_december_check':'PASS3candles','predictive_accuracy':'not measured','profitability':'not measured'};(P/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
lines=['# مقارنة صعود بيتكوين خلال اليوم في شهرين عشوائيين','',
'قورِن يناير 2024 بالشهر العشوائي الثاني، ديسمبر 2025، بالتعريف والأداة والسوق وطريقة العد نفسها. اختير الشهر الثاني مرة واحدة من 59 شهرًا متاحًا، بعد استبعاد يناير 2024، وقبل قراءة أدائه.','',
'سجّل يناير 124 حالة، وديسمبر 94 حالة: انخفاض قدره 24.19%. كلا الشهرين 31 يومًا، والمتوسط اليومي 4.00 مقابل 3.03. بقي ترتيب الأوصاف المصاحبة للصعود ثابتًا، لكن كثافة ظهور الحالات تغيّرت. هذه مقارنة وصفية؛ لا تقيس الربحية أو دقة التنبؤ.']
def table(title,heads,rows):
 lines.extend(['','## '+title,'','|'+'|'.join(heads)+'|','|'+'|'.join(['---']*len(heads))+'|']);lines.extend('|'+'|'.join(map(str,row))+'|' for row in rows)
table('1. تعريف الفحص',['البند','القيمة'],[
['السوق','بيتكوين مقابل USDT، السوق الفوري، من أرشيف المستودع نفسه'],
['الشهر الثاني','ديسمبر 2025؛ تسجيل السحب العشوائي قبل الحساب محفوظ في registration.json'],
['الصعود','الإغلاق أعلى 0.5% على الأقل من إغلاق قبل ساعة، وطرفا الساعة داخل اليوم المحلي نفسه'],
['الرصد','عند إغلاق كل 15 دقيقة بتوقيت عدن'],
['منع العد المتقارب','عدّ الانتقال إلى تحقق شرط الارتفاع، مع فصل ساعة على الأقل بين الحالات المقبولة'],
['ما حُفظ','الوقت والسعر وارتفاع الساعة والحجم وRSI وEMA والقمة السابقة، دون أي شمعة لاحقة'],
['النسخة المثبتة','6d0226a03b84656e14b94dd8a37e39332cc2f68f'],
['المدة','الحساب الثاني '+f"{b['compute_seconds']:.3f}"+' ثانية؛ مدة المهمة الكاملة غير مقاسة. التقدير السابق للتنفيذ 180 ثانية.']])
table('2. عدد الحالات',['المقياس','يناير 2024','ديسمبر 2025'],[
['أيام الشهر',31,31],['حالات الصعود ≥0.5% خلال ساعة',124,94],['متوسط الحالات في اليوم','4.00','3.03'],['أيام ظهرت فيها حالات',29,27],['أيام بلا حالة',2,4],['شموع تحقّق فيها الشرط قبل التخفيف',305,223],['انتقالات الشرط قبل منع التقارب',143,109],['انتقالات قريبة استُبعدت',19,15]])
flagrows=[]
for key,name in [('trend','وجود اتجاه صاعد'),('breakout','اختراق قمة آخر ثلاث ساعات'),('rebound','ضعف أو تشبع بيعي سابق')]:
 na=a['overlapping_flag_counts'][key];nb=b['overlapping_flag_counts'][key]
 flagrows.append([name,f'{na} / {na/124:.2%}',f'{nb} / {nb/94:.2%}',f'{100*(nb/94-na/124):+.2f}'])
flagrows.append(['دون الأوصاف الثلاثة','17 / 13.71%','12 / 12.77%',f'{100*(12/94-17/124):+.2f}'])
table('3. الأوصاف المصاحبة للصعود',['الوصف','يناير: عدد / نسبة','ديسمبر: عدد / نسبة','تغير النسبة بالنقاط'],flagrows)
lines+=['','الأوصاف متداخلة، فلا تُجمع أعداد هذا الجدول. يمكن أن تكون الحالة ضمن اتجاه صاعد وتخترق قمة أيضًا.','',
'الاتجاه الصاعد: EMA20 أعلى EMA50، والإغلاق فوق EMA20. الاختراق: الإغلاق فوق أعلى سعر للشموع الاثنتي عشرة السابقة، أي ثلاث ساعات. الضعف السابق: RSI14 بلغ 30 أو أقل في إحدى الشموع الأربع السابقة، أو أن الساعة التي سبقت ساعة الصعود هبطت 0.5% على الأقل. هذه أوصاف للحظة رصد صعود تكوّن بالفعل، ولا تثبت أنها تتنبأ ببدايته.']
table('4. تصنيف رئيسي واحد لكل حالة',['التصنيف حسب الأولوية','يناير','ديسمبر'],[
['بعد ضعف سابق',36,30],['وإلا: اختراق قمة',46,33],['وإلا: استمرار اتجاه صاعد',25,19],['وإلا: أخرى',17,12],['المجموع',124,94]])
lines+=['','الأولوية ثابتة منذ الفحص الأول، ولها غرض تنظيمي. لذلك تختلف أعداد الاختراق والاتجاه عن جدول الأوصاف المتداخلة. لا تعني الأولوية أن أحد الأوصاف أهم أو أقوى تنبؤيًا.']
table('5. أثر مقدار الصعود المطلوب',['الارتفاع خلال ساعة','يناير: حالات / أيام','ديسمبر: حالات / أيام','تغير عدد الحالات'],[
[f"{z['threshold_pct']}%",f"{z['events']} / {z['days']}",f"{w['events']} / {w['days']}",f"{100*(w['events']/z['events']-1):+.2f}%"] for z,w in zip(a['sensitivity'],b['sensitivity'])])
lines+=['','العتبات الثلاث محددة قبل الحساب. لكل عتبة عدّ مستقل ولا تُجمع النتائج. تكرار حركات 1% انخفض من 39 إلى 26، أي 33.33%، بينما انخفضت حركات 0.25% من 226 إلى 198، أي 12.39%. هذا وصف للشهرين فقط.']
da=pd.read_csv(OLD/'daily_counts.csv');db=pd.read_csv(P/'daily_counts.csv')
table('6. جميع أيام الشهر بما فيها الصفر',['رقم اليوم','يناير 2024','ديسمبر 2025'],[[i+1,int(da.iloc[i].total),int(db.iloc[i].total)] for i in range(31)])
table('7. التدقيق وحدود الحكم',['الفحص','النتيجة'],[
['تطابق التعريف والأداة','ملفا الحساب متطابقان بايتًا ببايت؛ لم تتغير الإعدادات'],
['اكتمال الدقائق','44,640 دقيقة لكل شهر، مع أربعة أيام سابقة لتسخين المؤشرات'],
['تسوية الأعداد','218 حالة تطابق مجاميع الأيام والتصنيفات في الشهرين'],
['عدم استخدام المستقبل','فحوص قطع التاريخ في أيام 7 و15 و23 تمر في كل شهر؛ أعيد حساب ارتفاع الساعة من الدقائق لكل حالة'],
['المصدر الخارجي','ثلاث شموع 15 دقيقة من ديسمبر تطابق OHLCV في Binance Spot تمامًا؛ فحص عينة فقط. عينة يناير موثقة أيضًا'],
['التنبؤ باستمرار الصعود','غير مقاس؛ لا متابعة لأهداف لاحقة'],
['الصفقات والمال والتكاليف والمخاطر المالية','غير مقاسة — خارج طلب المقارنة اللحظية'],
['التعميم','شهران لا يكفيان لإثبات الثبات في جميع الأشهر']])
lines+=['','## الحكم','',
'في هذين الشهرين بقي ترتيب الأوصاف: اتجاه صاعد، ثم اختراق قمة، ثم ضعف سابق. لكن العدد الإجمالي انخفض 24.19%، فلا يوجد معدل شهري ثابت. ارتفعت نسبة الحالات المصحوبة باتجاه صاعد من 45.97% إلى 51.06%، رغم انخفاض عددها من 57 إلى 48. هذا لا يثبت تحسن دقة التنبؤ أو زيادة الربحية.','',
'قد يُعد الصعود الطويل أكثر من مرة إذا زال شرط ارتفاع الساعة ثم عاد بعد ساعة أو أكثر. لذلك الأرقام حالات وفق قاعدة عد ثابتة، وليست دعوى حصر كل موجات الصعود المستقلة. لم تُنتظر أربعة أيام أو أي نتيجة لاحقة.','',
'## الأدلة وإعادة الحساب','',
'المجلدان january2024 وdecember2025 يحتويان لكل شهر: التسجيل السابق، وملف الدقائق، والشموع، والحالات، والأعداد اليومية، والملخص، وبصمات المصدر، وعينة المطابقة الخارجية. ملف comparison_audit.json يسجل تسويات المقارنة. بقيت البيانات الأصلية والمستودع البعيد دون تعديل.','',
'يمكن إعادة الحساب من الدقائق المرفقة باستخدام Python مع pandas وnumpy، دون تنزيل الأرشيف الكامل. شغّل الأمر الأول داخل كل مجلد شهر، ثم الثاني من جذر الحزمة:','',
'```bash','python analyze_month.py','python compare.py','```','',
'الخطوة التالية: مقارنة أشهر عشوائية إضافية بالتعريف نفسه قبل وصف أي نمط بأنه ثابت عبر الزمن.']
(P/'COMPARISON_REPORT.md').write_text('\n'.join(lines)+'\n')
(P/'comparison_audit.json').write_text(json.dumps({'status':'PASS','audits':audit,'external_december_max_abs_diff':max(diff),'analyzer_sha256':hashlib.sha256((P/'analyze_month.py').read_bytes()).hexdigest(),'source_sha256':b['source_sha256']},indent=2))
out=P.parent/'BTC_Two_Month_Comparison.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
 for f in [P/'COMPARISON_REPORT.md',P/'comparison.json',P/'comparison_audit.json',BASE/'compare.py']:z.write(f,f.name)
 for folder,name in [(OLD,'january2024'),(P,'december2025')]:
  for filename in ['registration.json','analyze_month.py','source_minutes.csv','bars15m.csv','events.csv','daily_counts.csv','summary.json','source_manifest.json','external_check.json']:
   f=folder/filename;z.write(f,name+'/'+filename)
with zipfile.ZipFile(out) as z:assert z.testzip() is None
print(out.resolve(),out.stat().st_size,'bytes');print(json.dumps(result,indent=2))
