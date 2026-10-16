from pathlib import Path
import json,collections,hashlib,zipfile,re,datetime
R=Path(__file__).resolve().parent
g=json.loads((R/'graphify-out/graph.json').read_text());nodes=g['nodes'];edges=g['links'];ids={n['id'] for n in nodes};known={f['path'] for f in json.loads((R/'SOURCE-FILES.json').read_text())['files']}
assert len(ids)==len(nodes) and all(e['source'] in ids and e['target'] in ids for e in edges)
sources={n['source_file'] for n in nodes if n.get('source_file')};assert sources.issubset(known)
audit={'status':'CODE_GRAPH_BUILT_WITH_SOURCE_WARNINGS','graphify_version':g['graph']['graphify_version'],'graph_schema_version':g['graph']['schema_version'],'upstream_documentation_commit':'10130e79ed9caf8f60d998073e097531eaa1a395','nova_source_commit':'14be41aafa52f714ec4ad2c11fee472bede69dc7','verified_input_files':610,'ast_input_files':608,'explicitly_skipped_yaml_files':2,'nodes':len(nodes),'edges':len(edges),'communities':len({n.get('community') for n in nodes}),'source_files_represented_in_nodes':len(sources),'sources_outside_verified_corpus':0,'duplicate_node_ids':0,'dangling_edge_endpoints':0,'confidence_counts':dict(collections.Counter(e.get('confidence') for e in edges)),'query_smoke_exit':0,'cluster_command_exit':0,'source_syntax_warning_files':4,'zero_symbol_files_reported':13,'html_view':'aggregated community view; full node graph in graph.json','semantic_documents_processed':False,'archives_expanded':False,'indicator_variant_enumeration_or_market_test':False,'source_code_executed':False,'global_assistant_hooks_or_skills_installed':False,'provider_api_called':False,'limits':'JSON settings are structurally modeled only where extractor supports them; no zero-symbol claim means parser success; Pine/scripts stored as TXT and PDFs are not semantically mapped; 608 inputs does not mean every input has graph nodes','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(R/'GRAPH-AUDIT.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
readme='''# Graphify على NOVA-DRAGON

طُبقت أداة Graphify الرسمية إصدار0.9.91فعليًا على نسخة المستودع المثبتة عند14be41aafa52f714ec4ad2c11fee472bede69dc7. هذا تطبيق محلي لعلاقات الكود والإعدادات، يساعد على معرفة أين توجد أدوات الحساب والتسجيل والتحقق وما الذي يستدعيها. لا يختبر دقة مؤشرات التداول ولا يعدد ملايين نسخها.

## النتيجة

| البند | النتيجة |
|---|---:|
| الملفات المجلوبة والتحقق من هويتها Git |610|
| ملفات PythonوShellوJSONالمدخلة للتحليل |608|
| YAMLمستبعد صراحة من المسار الدلالي |2|
| عناصر الخريطة |10,956|
| العلاقات |29,209|
| العلاقات المستخرجة EXTRACTED |28,766|
| العلاقات المستنتجة INFERRED |443|
| المجموعات |346|
| ملفات ذات رموز ممثلة في الخريطة |353|
| ملفات أبلغت الأداة عن أخطاء صياغة فيها |4|
| ملفات كود أبلغت عن غياب رموز مستخرجة منها |13|

لا يعني عدد608أن كل ملف ولّد رموزًا. ملفات JSONالبيانية قد لا تمثلها هذه المستخرجات كتعريفات؛ لذلك حُفظ عدد الملفات الممثلة فعلًا. الرسم المرئي يعرض346مجموعة و1439علاقة بين المجموعات لأن عدد العناصر تجاوز5000؛ جميع العناصر والعلاقات محفوظة في JSONالكامل.

## الملفات

- [تقرير Graphify الرسمي](graphify-out/GRAPH_REPORT.md).
- [الرسم التفاعلي](graphify-out/graph.html): نزّله وافتحه في المتصفح؛ GitHubيعرض الملف ولا يشغله كصفحة تلقائيًا.
- [حزمة النتائج الكاملة](GRAPHIFY-OUTPUTS.zip): تضمgraph.jsonالكامل والرسم والتقرير وبيان الاستخراج. افتحها في مجلدgraphify-outللاستعلام.
- [مثال استعلام فعلي عنread_base](QUERY-EXAMPLE.txt).
- [تدقيق الخريطة وحدودها](GRAPH-AUDIT.json)، [سجل الاستخراج](extract.log)، [سجل العرض](cluster.log).
- [هوية ملفات المستودع](SOURCE-AUDIT.json) و[SOURCE-FILES.json](SOURCE-FILES.json).
- [الإصدارات المثبتة](requirements-graphify.lock.txt)، [أداة التطبيق](../../tools/graphify_nova.py)، [إيصال النشر](DELIVERY.json).

## الاستعمال بعد تنزيل النتائج

يثبت المسؤول Python3.10أو أحدث ومتطلباتrequirements-graphify.lock.txtفي بيئة منفصلة، ثم يستخرج الحزمة في جذر عمله. أداةtools/graphify_nova.pyتقبل--queryو--outputللاستعلام، أو--rootلإعادة بناء خريطة كود من نسخة محلية من المستودع. المسار الرسمي المستعمل هوgraphify extract --code-onlyثمcluster-only --no-label. لم يُثبت أي hookعام أو إعداد في حساب المالك، ولم تُغيّر ملفاتAGENTSأو الدستور. التحديث يدوي عند تغيير المصدر؛ هذه الخريطة ثابتة للالتزام المذكور وليست خدمة تلقائية.

## الحدود وما يحتاج المرحلة التالية

لم يُنفذ التحليل الدلالي لوثائقMarkdownوTXTوPDFوDOCXأو محتوياتZIP. مؤشرات Pineالمحفوظة بصيغةTXTلم تُعطَ تفسيرًا مصطنعًا. يمكن إضافتها لاحقًا باستخراج دلالي موثق يربط كل علاقة بمصدرها، عبر الوكيل أو خلفية نموذج يختارها المالك؛ لا يلزم شراء خدمة Graphify Cloud لهذا التطبيق المحلي. المصادر لا تنفذ؛解析ها بنيوي فقط.

تحذيرات الصياغة: history/bot_versions/1/NOVA (2).pyعند179، وNOVA (3).pyعند193، وNOVA.pyعند168، وnova_v8/README.pyعند3. بعضها استخراج جزئي؛ لم أعدل الأصول أو الكود الحي لإرضاء المحلل. تحذير الصياغة من Graphifyليس حكمًا على نتيجة استراتيجية. الأسماء المتشابهة بين نسخ البوت القديمة قد تحتاج تضييق الاستعلام بمسار الملف.

الحساب والبيانات سابقًا تجاوزا125MBفي مساحة الجلسة؛ هذا التطبيق لا يقدم PASSلسقف مساحة منفذ جديد، ولا يطلب تحميل المستودع كله أو أرشيف البيانات. تُحفظ المتطلبات بدل رفع بيئةPythonوالاعتماديات والذاكرة المخبأة.

المصدر الرسمي: [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify/tree/10130e79ed9caf8f60d998073e097531eaa1a395). الحزمة المثبتة منPyPIهيgraphifyyبـyمزدوجة؛ تثبيت الإصدار والوثائق لا يدعي مطابقة بايتات الحزمة لشجرةGit. هذا تكامل مستقل مع NOVAوليس منتجًا تابعًا لـGraphify Labs.

التالي: استعمال الخريطة لتعقب مولدات النسخ والحسابات والاختبارات، ثم توسيعها دلاليًا إلى الوثائق والمؤشرات النصية مع بيان تغطية مستقل.
'''
(R/'README_AR.md').write_text(readme.replace('解析ها','تحليلها'))
pattern=re.compile(rb'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----')
members=['graph.json','graph.html','GRAPH_REPORT.md','manifest.json']
with zipfile.ZipFile(R/'GRAPHIFY-OUTPUTS.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for n in members:
        b=(R/'graphify-out'/n).read_bytes();assert not pattern.search(b),n;z.writestr('graphify-out/'+n,b)
with zipfile.ZipFile(R/'GRAPHIFY-OUTPUTS.zip') as z:
    for n in members:assert z.read('graphify-out/'+n)==(R/'graphify-out'/n).read_bytes()
audit['output_archive_bytes']=(R/'GRAPHIFY-OUTPUTS.zip').stat().st_size;audit['output_archive_sha256']=hashlib.sha256((R/'GRAPHIFY-OUTPUTS.zip').read_bytes()).hexdigest()
(R/'GRAPH-AUDIT.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(audit,ensure_ascii=False),flush=True)
