from pathlib import Path
import json,hashlib,collections,datetime,gzip,zipfile,re
p=Path(__file__).parent;w=p/'execution';u=p/'updates';prefix='research/graphify-semantic-nova-2026-10-16'
def write(rel,text):
 f=u/rel;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(text,encoding='utf-8')
a=json.loads((w/'FINAL-RELATION-AUDIT.json').read_text());i=json.loads((w/'INGEST-RECEIPT.json').read_text())
status={'status':'PARTIAL_EVIDENCE_GRAPH_COMPLETE_SEMANTIC_REVIEW_PENDING','source_commit':'d1b4cb1ded30cc22049d33b5f146081405e81443','tracked_files':i['tracked_blobs'],'canonical_source_records':i['inventory_records'],'nodes':a['nodes'],'edges':a['edges'],'structural_audit':a['status'],'all_content_semantically_read':False,'all_inferred_relations_reviewed':False,'opaque_binary_count':len(i.get('binary_metadata_only',[])),'semantic_segments_pending':i['segments'],'source_fetch_errors':i['failed_fetches'],'unresolved_conversion_errors':len(i['unresolved']),'delivery_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'total_elapsed_seconds':'not measured: exact first tool time not captured; work exceeded 600 seconds','market_experiments_run':False,'main_modified':False,'remaining':'Full semantic reading and independent relation review; do not claim task complete.'}
(p/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
# Persist exact pending reading identities; source content remains pinned in repository archives.
with gzip.open(p/'SEGMENT-INDEX.jsonl.gz','wt',encoding='utf-8') as f:
 for name in json.loads((w/'BATCH-MANIFEST.json').read_text()):
  for s in json.loads((w/'batches'/name).read_text()):
   t=s.pop('text');s.update(characters=len(t),decoded_text_sha256=hashlib.sha256(t.encode()).hexdigest(),batch=name,semantic_review='pending');f.write(json.dumps(s,ensure_ascii=False)+'\n')
base=p.parent/'graphify_integration_2026_10_16/updates'
for rel in ['LOG.md','docs/HANDOFF.md','INDEX.md']:
 original=(base/rel).read_text()
 addition=f'\n\n## 2026-10-16 — توسيع مخزون Graphify وروابطه مع بيان النقص\n\nطلب المالك إدخال كل المحتوى وفحص العلاقات. المصدر {status["source_commit"]}؛ {i["tracked_blobs"]} ملفًا متعقبًا، {i["inventory_records"]} مصدرًا فريدًا مع الأرشيفات. خريطة أدلة {a["nodes"]} عنصرًا و{a["edges"]} علاقة. تدقيق الاقتباسات والأطراف ناجح؛ القراءة الدلالية الكاملة ومراجعة الاستنتاجات لم تكتمل. إصلاح مسارات GZIP وتجميع سجلات الفشل المؤقت وشرح ملفات الاختبار الاصطناعية موثق. لا نتائج تداول جديدة ولا تعديل main. التقرير: {prefix}/README_AR.md؛ الحالة: {prefix}/STATUS.json. التالي: إكمال القراءة الدلالية من قائمة المقاطع، دون تسمية فهرسة المصطلحات فهمًا شاملًا.\n'
 write(rel,original+addition)
ledger='research/session-work-archive-2026-10-16/REQUEST-EXECUTION-LEDGER.json';x=json.loads((base/ledger).read_text());x['requests'].append({'id':'R082','request':'إدخال كل الملفات في التحليل الدلالي وربطها جيدًا والتحقق من العلاقات ومتابعة التنفيذ','status':'جزئي','execution':f'جرد وجلب {i["tracked_blobs"]} ملفًا، فك الأرشيفات وتفسير الصيغ، خريطة أدلة {a["nodes"]} عنصرًا و{a["edges"]} علاقة مع تدقيق بنيوي واقتباسات؛ لم تتم القراءة الدلالية لكل المحتوى','evidence_codes':['M'],'remaining_or_rule':'القراءة الدلالية الكاملة ومراجعة الاستنتاجات؛ لا إعلان اكتمال أو خلو كل العلاقات من الخطأ'});x['status_counts']=dict(collections.Counter(v['status'] for v in x['requests']));write(ledger,json.dumps(x,ensure_ascii=False,indent=2)+'\n')
md=ledger.replace('.json','_AR.md');write(md,(base/md).read_text()+f'\n\n## R082 — التوسعة الدلالية الشاملة\n\nالحالة: **جزئي**. الدليل M: [{prefix}/README_AR.md](../../{prefix}/README_AR.md). اكتمل الجلب والفهرسة والربط بالأدلة، ولم تكتمل القراءة الدلالية ومراجعة جميع الاستنتاجات. تفاصيل STATUS.json تفصل المرحلتين؛ لا يساوي عدد الروابط اكتمال الفهم.\n')
write('docs/journal/2026-10-16-graphify/003-semantic-expansion-checkpoint.md',f'القرار: تنفيذ طلب المالك بتوسيع النطاق لكل ملفات المصدر والأرشيفات مع فصل المعنى المثبت عن المستنتج.\nالتنفيذ: جلب {i["tracked_blobs"]} ملفًا، وتصحيح مشكلات التحويل ومسارات GZIP وتدقيق روابط الأدلة.\nالناتج: {a["nodes"]} عنصرًا و{a["edges"]} علاقة؛ سلامة بنيوية واقتباسات، مع بقاء المراجعة الدلالية الشاملة غير مكتملة.\nالتالي: القراءة الدلالية ومراجعة العلاقات المستنتجة والمعزولة من {prefix}/SEMANTIC-REVIEW.md.\n')
# Complete output bundle; source data and private credentials are not republished.
with zipfile.ZipFile(p/'EVIDENCE-GRAPH.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for name in ['evidence-graph.json','EVIDENCE-AUDIT.json','FINAL-RELATION-AUDIT.json','TOPOLOGY-AUDIT.json','UNRESOLVED-REFERENCES.json','INVENTORY.json','INGEST-RECEIPT.json','BULK-RECEIPT.json','RELATION-BROWSER.html','CURATED-RELATIONS.json','EXTRACTION-GAP-REVIEW.json','CACHE-REPAIR.json','MEMBER-PATH-CORRECTION.json']:
  z.write(w/name,name)
 z.write(p/'SEGMENT-INDEX.jsonl.gz','SEGMENT-INDEX.jsonl.gz')
with zipfile.ZipFile(p/'EVIDENCE-GRAPH.zip') as z:
 assert z.testzip() is None
 for name in z.namelist():
  if not name.endswith('.gz'):assert not re.search(rb'ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}',z.read(name)),name
print(json.dumps(status));print('ZIP bytes', (p/'EVIDENCE-GRAPH.zip').stat().st_size)
