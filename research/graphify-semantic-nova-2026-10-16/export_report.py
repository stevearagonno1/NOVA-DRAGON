from pathlib import Path
import collections,json,hashlib,zipfile
ROOT=Path(__file__).parent;w=ROOT/'execution'
a=json.loads((w/'EVIDENCE-AUDIT.json').read_text());ing=json.loads((w/'INGEST-RECEIPT.json').read_text());g=json.loads((w/'evidence-graph.json').read_text())
# The interactive browser loads the adjacent JSON selected locally; no external services.
h='''<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><title>NOVA — دليل العلاقات</title><style>body{font:17px system-ui;background:#0b1220;color:#e5edf9;margin:32px}input,select,button{padding:10px;margin:5px}article{padding:14px;border-bottom:1px solid #31425b}pre{white-space:pre-wrap;direction:ltr;text-align:left}small{color:#adbed4}</style><h1>دليل علاقات NOVA</h1><p>اختر evidence-graph.json من الحزمة. ذكر مؤشر لا يثبت نجاحه. العلاقات الأصلية والاستنتاجات ظاهرة بتصنيفها.</p><input type="file" id="file"><input id="q" placeholder="اسم المؤشر أو مسار الملف"><button id="search">بحث</button><div id="info"></div><main id="out"></main><script>
let g,byid;const $=s=>document.getElementById(s);function text(tag,s){let e=document.createElement(tag);e.textContent=s;return e}
$('file').onchange=async e=>{g=JSON.parse(await e.target.files[0].text());byid=new Map(g.nodes.map(n=>[n.id,n]));$('info').textContent=g.nodes.length+' عنصر / '+g.edges.length+' علاقة';};
$('search').onclick=()=>{if(!g)return;let q=$('q').value.toLowerCase(),a=g.nodes.filter(n=>(n.label||n.id).toLowerCase().includes(q));$('out').replaceChildren(text('p',a.length+' نتائج؛ يعرض أول 100، ضيّق البحث للباقي.'));a.slice(0,100).forEach(n=>{let el=text('article','');el.append(text('strong',n.label||n.id));el.append(text('small',' — '+(n.status||n.file_type||'')));let b=text('button','عرض الروابط');b.onclick=()=>{let es=g.edges.filter(e=>e.source===n.id||e.target===n.id);let box=text('div','');es.forEach(e=>{let other=byid.get(e.source===n.id?e.target:e.source);box.append(text('p',e.relation+' → '+(other?.label||other?.id)+' ['+e.confidence+']'));box.append(text('pre',e.evidence_quote||e.source_location||'دليل AST في الخريطة الأصلية'));});b.replaceWith(box)};el.append(b);$('out').append(el)})};</script></html>'''
(w/'RELATION-BROWSER.html').write_text(h)
relations=collections.Counter(e.get('relation','unspecified') for e in g['edges'])
report=f'''# توسعة خريطة المستودع: حالة فعلية وحدود واضحة

مصدر ثابت: `{ing['source_commit']}`. هذه توسعة فهرسة موثقة بالأدلة مع خريطة الكود السابقة، **وليست إعلان اكتمال القراءة الدلالية العميقة لكل المحتوى**.

- ملفات المصدر المتعقبة: {ing['tracked_blobs']}.
- سجلات الملفات ومحتويات الأرشيفات: {ing['inventory_records']}.
- العناصر: {a['nodes']}؛ العلاقات: {a['edges']}؛ أطراف العلاقات المفقودة: {a['dangling_endpoints']}.
- مصادر بلا روابط دلالية في هذه الطبقة: {len(a['semantic_isolates'])}؛ القائمة كاملة في EVIDENCE-AUDIT.json.
- مقاطع القراءة المطلوبة للمرحلة الدلالية: {ing['segments']}؛ لا تُحتسب المقاطع مقروءة لمجرد استخراج نصها.

## ما أُنجز

جلب كل ملفات الالتزام، والتحقق من بصمة Git لكل ملف. فتح ZIP وGZIP وRAR والأرشيف المجزأ؛ استخراج نصوص PDF وWord، وتمثيل البيانات الرقمية بهويتها وبنيتها. حفظ المخزون ومشكلات التحويل. ربط النصوص بالمصطلحات التي تذكرها، والمسارات والروابط الصريحة، وتعريفات Pine ومدخلاته المتاحة، والنسخ ذات البايتات المتطابقة. الحفاظ على خريطة Graphify السابقة مع فصل هوية مصدرها. لا دمج مؤشرين لأن اسميهما متشابهان.

## معنى العلاقات وحدودها

`mentions` يثبت ذكر المصطلح فقط؛ ليس تطبيقه أو صلاحيته للشراء. `references_path` يثبت إحالة نصية إلى مسار موجود. `same_bytes_as` يثبت تطابق المحتوى فقط. `declares_input` ينقل تصريح الإعداد كما ورد؛ لا يثبت قابلية تشغيل جميع التركيبات. العلاقات السابقة من Graphify تحتفظ بدرجة EXTRACTED أو INFERRED ومصدرها السابق. المصادر القديمة تبقى قديمة ولا تتحول إلى قواعد معتمدة بمجرد الربط.

## ما لم يكتمل

القراءة الدلالية الشاملة لكل مقطع، وفهم قرارات الأبحاث وتعارضاتها، والتحقق المستقل من صحة كل علاقة مستنتجة، ومراجعة العناصر المعزولة. لا تُعد هذه نسخة مكتملة من Graphify semantic extraction. الملفات الثنائية والمحتويات غير القابلة للفك مسجلة كما هي، ولا تُخترع لها معانٍ. لا توجد نتائج تداول جديدة.

## فتح النتائج

نزّل EVIDENCE-GRAPH.zip وافتح RELATION-BROWSER.html، ثم اختر evidence-graph.json من الحزمة. يمكن البحث باسم المؤشر أو مسار الملف ورؤية دليل كل رابط. لا تُحسب زيادة عدد الروابط أو غياب الأطراف المفقودة إثباتًا لفهم المعنى.

## الاستئناف

أكمل القراءة وفق SEMANTIC-REVIEW.md، ثم شغّل تدقيق semantic_pipeline.py audit. لا تُعلن اكتمال المهمة حتى تُغطى المقاطع والمصادر وتُراجع العلاقات. سجل الحالة الحالي جزئي صراحة؛ main ونتائج التداول الأصلية لم تتغير.

## أنواع العلاقات المحسوبة

'''+ '\n'.join(f'- {k}: {v}' for k,v in sorted(relations.items()))+'\n'
(ROOT/'README_AR.md').write_text(report)
with zipfile.ZipFile(ROOT/'EVIDENCE-GRAPH.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for name in ['evidence-graph.json','EVIDENCE-AUDIT.json','UNRESOLVED-REFERENCES.json','INVENTORY.json','INGEST-RECEIPT.json','BULK-RECEIPT.json','RELATION-BROWSER.html']:z.write(w/name,name)
print('Saved graph package', (ROOT/'EVIDENCE-GRAPH.zip').stat().st_size)
