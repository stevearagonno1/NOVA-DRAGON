"""Evidence-preserving handling of known fixtures, NUL-bearing text and feature records."""
import json,struct,hashlib
from pathlib import Path
import semantic_pipeline as p
w=p.ROOT/'execution';inventory=json.loads((w/'INVENTORY.json').read_text());extra=[];resolved=[]
prefix='research/session-work-archive-2026-10-16/WORKSPACE-v2.zip!/'
for r in inventory:
 if (r['status']!='BLOCKED' and 'original_decode_error' not in r) or not r['path'].startswith(prefix):continue
 relative=r['path'][len(prefix):];local=p.ROOT.parent/relative
 if not local.is_file():continue
 b=local.read_bytes()
 if p.digest(b)!=r['sha256']:continue
 text=None;old=r.get('reason',r.get('original_decode_error'))
 if relative.startswith('publish_resume/synthetic-existing-run/'):
  text=b.decode('utf-8')
  assert text.startswith(('synthetic transport','synthetic source ','fixture-'))
  r['status']='INVALID_CONTAINER_FIXTURE';r['proof_source']=prefix+'publish_resume/test_publisher.py'
 elif relative.startswith('btc_comprehensive_prep/document_evidence/') and relative.endswith('.txt'):
  text=b.decode('utf-8').replace('\0','[NUL]');r['status']='TEXT_NORMALIZED';r['normalization']='NUL explicitly represented as [NUL]; original hash retained'
 elif relative.startswith('causal_features_prep/rehearsal/features-') and relative.endswith('.bin'):
  fmt=struct.Struct('<q14d');assert len(b)%fmt.size==0
  text=json.dumps({'record_format':'<q14d','record_bytes':fmt.size,'records':len(b)//fmt.size,'first_open_ms':fmt.unpack_from(b,0)[0],'last_open_ms':fmt.unpack_from(b,len(b)-fmt.size)[0],'producer_evidence':"RECORD=struct.Struct('<q14d')",'fixture':'rehearsal, not evidence of predictive trading accuracy'})
  r['status']='DATA_SCHEMA';r['proof_source']=prefix+'causal_features_prep/features.py'
 if text is not None:
  r['original_decode_error']=r.pop('reason',old);resolved.append({'path':r['path'],'status':r['status'],'sha256':r['sha256'],'original_decode_error':old,'proof_source':r.get('proof_source')})
  for off in range(0,len(text),18000):
   piece=text[off:off+18000];extra.append({'segment_id':p.gid(r['path']+':'+str(off)+':'+p.digest(piece.encode())),'source_file':r['path'],'offset':off,'text':piece,'source_sha256':r['sha256']})
p.write(w/'INVENTORY.json',inventory)
m=json.loads((w/'BATCH-MANIFEST.json').read_text());names=[]
for i in range(0,len(extra),12):
 name=f'resolved-{i//12:05d}.json';p.write(w/'batches'/name,extra[i:i+12]);names.append(name)
m=[n for n in m if not n.startswith('resolved-')]+names;p.write(w/'BATCH-MANIFEST.json',m)
r=json.loads((w/'INGEST-RECEIPT.json').read_text());r['segments']=sum(len(json.loads((w/'batches'/n).read_text())) for n in m);r['batch_count']=len(m);r['unresolved']=[x['path'] for x in inventory if x['status'] in ['BLOCKED','FETCH_FAILED','NEEDS_VISUAL_REVIEW']];r['binary_metadata_only']=[x['path'] for x in inventory if x['status']=='BINARY_METADATA_ONLY'];r['invalid_fixture_count']=sum(x['status']=='INVALID_CONTAINER_FIXTURE' for x in inventory);p.write(w/'INGEST-RECEIPT.json',r);p.write(w/'EXTRACTION-GAP-REVIEW.json',resolved)
print('Evidence-resolved extraction gaps',len(resolved),'remaining',len(r['unresolved']))
