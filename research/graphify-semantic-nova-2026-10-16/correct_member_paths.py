"""Correct a converter path bug without changing any source or decoded content."""
import json
from pathlib import Path
import semantic_pipeline as p
w=p.ROOT/'execution';inv=json.loads((w/'INVENTORY.json').read_text());mapping={}
if not (w/'INVENTORY-OBSERVATIONS.json').exists():p.write(w/'INVENTORY-OBSERVATIONS.json',inv)
canonical={}
for r in inv:
 if r['path'] in canonical:
  old=canonical[r['path']];assert old.get('sha256')==r.get('sha256');r['conversion_observations']=[old['status'],r['status']]
 canonical[r['path']]=r
inv=list(canonical.values())
for r in inv:
 name=r['path']
 if r['status']=='CONTAINER' and name.endswith('.gz'):
  correct=name+'!/'+Path(name[:-3]).name
  wrong=name[:-3]+'!/'+Path(name[:-3]).name
  alternatives=[wrong,name+wrong[len(name):]]
  for item in inv:
   for old in alternatives:
    if item['path']==old or item['path'].startswith(old+'!/'):
     mapping[item['path']]=correct+item['path'][len(old):]
assert len(set(mapping.values()))==len(mapping)
for r in inv:
 if r['path'] in mapping:r['original_converter_path']=r['path'];r['path']=mapping[r['path']]
assert len(set(r['path'] for r in inv))==len(inv)
p.write(w/'INVENTORY.json',inv)
for name in json.loads((w/'BATCH-MANIFEST.json').read_text()):
 file=w/'batches'/name;original=json.loads(file.read_text());batch=[s for s in original if s['text'] not in ['ZIP archive; members listed as separate sources.','GZIP container.','RAR archive.']];changed=len(batch)!=len(original)
 for s in batch:
  if s['source_file'] in mapping:
   s['original_converter_path']=s['source_file'];s['source_file']=mapping[s['source_file']];s['segment_id']=p.gid(s['source_file']+':'+str(s['offset'])+':'+p.digest(s['text'].encode()));changed=True
 if changed:p.write(file,batch)
p.write(w/'MEMBER-PATH-CORRECTION.json',{'cause':'GZIP child name incorrectly omitted .gz, and top-level alias rebasing assumed a preserved prefix','corrected_paths':mapping,'source_bytes_changed':False})
receipt=json.loads((w/'INGEST-RECEIPT.json').read_text());receipt['inventory_records']=len(inv);receipt['segments']=sum(len(json.loads((w/'batches'/n).read_text())) for n in json.loads((w/'BATCH-MANIFEST.json').read_text()));p.write(w/'INGEST-RECEIPT.json',receipt)
print('Corrected archive member paths',len(mapping),'canonical source records',len(inv))
