"""Pinned repository ingestion and evidence-checked semantic assembly.
No model is simulated: model-authored fragments are an explicit input.
"""
from pathlib import Path
import argparse, base64, concurrent.futures, csv, gzip, hashlib, io, json, os, re, sqlite3, sys, time, urllib.parse, urllib.request, zipfile
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'runtime'))
REPO='stevearagonno1/NOVA-DRAGON'
PIN='d1b4cb1ded30cc22049d33b5f146081405e81443'
SECRET=re.compile(r'(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})')
def write(p,x):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def digest(b):return hashlib.sha256(b).hexdigest()
def gid(s):return 'n_'+hashlib.sha256(s.encode()).hexdigest()[:24]
def download(f):
 u=f'https://raw.githubusercontent.com/{REPO}/{PIN}/'+urllib.parse.quote(f['path'],safe='/')
 for attempt in range(4):
  try:
   with urllib.request.urlopen(u,timeout=90) as r:b=r.read()
   assert len(b)==f['size'],'size mismatch'
   assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==f['sha'],'Git hash mismatch'
   return b
  except Exception:
   if attempt==3:raise
   time.sleep(2**attempt)
def textdecode(b):
 for enc in ['utf-8-sig','utf-16','cp1256']:
  try:
   s=b.decode(enc)
   if '\x00' not in s:return s
  except UnicodeError:pass
 raise ValueError('unrecognized text encoding')
def convert(name,b,depth=0):
 """Yield every member; opaque/failed items remain visible and block completion."""
 if depth>16:
  yield {'path':name,'status':'BLOCKED','reason':'archive nesting >16; lead review required'};return
 ext=Path(name).suffix.lower();identity={'path':name,'sha256':digest(b),'bytes':len(b)}
 try:
  if ext=='.zip':
   yield dict(identity,status='CONTAINER',text='ZIP archive; members listed as separate sources.')
   with zipfile.ZipFile(io.BytesIO(b)) as z:
    for i in z.infolist():
     if not i.is_dir():yield from convert(name+'!/'+i.filename,z.read(i),depth+1)
   return
  if ext=='.gz':
   yield dict(identity,status='CONTAINER',text='GZIP container.')
   yield from convert(name+'!/'+Path(name[:-3]).name,gzip.decompress(b),depth+1);return
  if ext=='.rar':
   import libarchive
   yield dict(identity,status='CONTAINER',text='RAR archive.')
   with libarchive.memory_reader(b) as a:
    for e in a:
     if e.isfile:yield from convert(name+'!/'+e.pathname,b''.join(e.get_blocks()),depth+1)
   return
  if ext=='.pdf':
   import fitz
   with fitz.open(stream=b,filetype='pdf') as doc:
    pages=[];empty=[]
    for n,p in enumerate(doc):
     t=p.get_text(sort=True);pages.append(f'\n[PAGE {n+1}]\n'+t)
     if len(t.strip())<20:empty.append(n+1)
    yield dict(identity,status='NEEDS_VISUAL_REVIEW' if empty else 'TEXT',text=''.join(pages),pages=len(pages),visual_pages=empty)
   return
  if ext in ['.docx','.xlsx','.pptx']:
   import xml.etree.ElementTree as ET
   with zipfile.ZipFile(io.BytesIO(b)) as z:
    selected=[n for n in z.namelist() if n.endswith('.xml') and (n.startswith('word/') or n.startswith('ppt/slides/') or n.startswith('xl/'))]
    text='\n'.join('['+n+']\n'+' '.join(ET.fromstring(z.read(n)).itertext()) for n in selected)
    media=[n for n in z.namelist() if '/media/' in n]
   yield dict(identity,status='NEEDS_VISUAL_REVIEW' if media else 'TEXT',text=text,media=media);return
  if ext in ['.sqlite','.sqlite3','.db'] or b.startswith(b'SQLite format 3'):
   c=sqlite3.connect(':memory:');c.deserialize(b)
   c.execute('PRAGMA query_only=ON');c.execute('PRAGMA trusted_schema=OFF')
   schema=c.execute("select type,name,sql from sqlite_master where type in ('table','view') order by name").fetchall()
   # Schema and table counts convey data meaning; record cells are not language documents.
   counts={};contents={}
   for kind,n,sql in schema:
    if kind=='table':
     quoted='\"'+n.replace('\"','\"\"')+'\"'
     cur=c.execute('select * from '+quoted);cols=[d[0] for d in cur.description];rows=cur.fetchall();counts[n]=len(rows)
     if not {'open','high','low','close'}.issubset(set(x.lower() for x in cols)):contents[n]={'columns':cols,'rows':rows}
   c.close();yield dict(identity,status='DATA_SCHEMA',text=json.dumps({'schema':schema,'table_rows':counts,'non_market_table_contents':contents},ensure_ascii=False,default=lambda v: {'binary_sha256':digest(v),'bytes':len(v)}));return
  if ext=='.parquet':
   import pyarrow.parquet as pq
   p=pq.ParquetFile(io.BytesIO(b));yield dict(identity,status='DATA_SCHEMA',text=json.dumps({'schema':str(p.schema_arrow),'rows':p.metadata.num_rows,'row_groups':p.metadata.num_row_groups}));return
  if ext=='.csv':
   s=textdecode(b);r=csv.reader(io.StringIO(s));first=next(r,[]);rows=0;widths=set()
   for row in r:rows+=1;widths.add(len(row))
   names={x.strip().lower() for x in first}
   numeric_candles=False
   try:numeric_candles=len(first) in [6,7,12] and float(first[0])>1e9 and all(float(x)>=0 for x in first[1:6])
   except (ValueError,TypeError):pass
   market={'open','high','low','close'}.issubset(names) or numeric_candles
   yield dict(identity,status='DATA_SCHEMA' if market else 'TEXT',text=json.dumps({'first_record':first,'following_records':rows,'following_widths':sorted(widths),'numeric_market_data':market},ensure_ascii=False) if market else s);return
  if ext in ['.npz','.npy']:
   import numpy as np
   arrays=np.load(io.BytesIO(b),allow_pickle=False)
   details={k:{'shape':list(arrays[k].shape),'dtype':str(arrays[k].dtype)} for k in arrays.files} if ext=='.npz' else {'array':{'shape':list(arrays.shape),'dtype':str(arrays.dtype)}}
   yield dict(identity,status='DATA_SCHEMA',text=json.dumps(details));return
  if b.startswith(b'\x7fELF') or b.startswith(b'MZ'):
   yield dict(identity,status='BINARY_METADATA_ONLY',text=json.dumps({'binary_format':'ELF' if b.startswith(b'\x7fELF') else 'PE','execution':'never executed','semantics':'compiled machine code not decompiled; unresolved implementation'}));return
  if ext in ['.png','.jpg','.jpeg','.gif','.webp','.mp4','.mp3','.wav']:
   yield dict(identity,status='NEEDS_VISUAL_REVIEW',reason='image/audio/video requires host vision or transcription');return
  t=textdecode(b)
  if SECRET.search(t):
   t=SECRET.sub('[REDACTED_CREDENTIAL]',t)
   yield dict(identity,status='TEXT_REDACTED',text=t);return
  yield dict(identity,status='TEXT',text=t)
 except Exception as e:yield dict(identity,status='BLOCKED',reason=type(e).__name__+': '+str(e)[:400])
def ingest(work):
 tree=json.loads((ROOT/'SOURCE-TREE.json').read_text());assert tree['sha']==PIN and not tree.get('truncated')
 files=[f for f in tree['tree'] if f['type']=='blob'];work.mkdir(parents=True,exist_ok=True)
 import fcntl
 lock=open(work/'RUN.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 matches=json.loads((ROOT/'LOCAL-MATCHES.json').read_text()) if (ROOT/'LOCAL-MATCHES.json').exists() else {}
 (work/'sources').mkdir(exist_ok=True)
 # Atomic checkpoint per source; files are fetched once, decoded in memory, retained compressed.
 def one(f):
  target=work/'sources'/(f['sha']+'.json.gz')
  if target.exists():
   with gzip.open(target,'rt',encoding='utf-8') as z:old=json.load(z)
   assert old['blob']==f['sha']
   if old.get('converter_version')==2:return
  if re.search(r'\.part\d+$',f['path']):return
  local=Path(matches[f['sha']]) if f['sha'] in matches else ROOT.parent/'graphify_integration_2026_10_16/corpus'/f['path']
  b=local.read_bytes() if local.exists() else None
  if b is None or hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()!=f['sha']:b=download(f)
  records=list(convert(f['path'],b));payload={'converter_version':2,'blob':f['sha'],'original_path':f['path'],'records':records}
  temp=target.with_suffix('.tmp')
  with gzip.open(temp,'wt',encoding='utf-8') as z:json.dump(payload,z,ensure_ascii=False)
  temp.replace(target)
 import threading
 large_lock=threading.Semaphore(2)
 original_one=one
 def bounded(f):
  if f['size']>10000000:
   with large_lock:return original_one(f)
  return original_one(f)
 unique={f['sha']:f for f in files if not re.search(r'\.part\d+$',f['path'])}
 failures=[]
 # Bounded workers: binary datasets are large; no uncompressed disk copies.
 with concurrent.futures.ThreadPoolExecutor(max_workers=24) as ex:
  futures={ex.submit(bounded,f):f for f in unique.values()}
  for future in concurrent.futures.as_completed(futures):
   try:future.result()
   except Exception as e:failures.append({'path':futures[future]['path'],'reason':str(e)[:400]})
 # Multipart archive reassembly in RAM, each part verified against pinned Git identity.
 parts=sorted([f for f in files if re.search(r'\.part\d+$',f['path'])],key=lambda f:f['path'])
 if parts and not (work/'multipart.json.gz').exists():
  combined=b''.join(download(f) for f in parts)
  rec=list(convert(parts[0]['path'].rsplit('.part',1)[0],combined))
  with gzip.open(work/'multipart.json.gz','wt',encoding='utf-8') as z:json.dump(rec,z,ensure_ascii=False)
 write(work/'FETCH-ERRORS.json',failures)
 inventory=[];segments=[]
 for f in files:
  target=work/'sources'/(f['sha']+'.json.gz')
  if re.search(r'\.part\d+$',f['path']):inventory.append(dict(f,status='MULTIPART_MEMBER'));continue
  if not target.exists():inventory.append(dict(f,status='FETCH_FAILED'));continue
  with gzip.open(target,'rt',encoding='utf-8') as z:obj=json.load(z)
  for r0 in obj['records']:
   r=dict(r0);r['path']=f['path']+r['path'][len(obj['original_path']):];t=r.pop('text','');r['git_blob']=f['sha'];inventory.append(r)
   # Content hash canonicalization reduces identical copies, while all paths remain in inventory.
   if t:
    for offset in range(0,len(t),18000):
     piece=t[offset:offset+18000];sid=gid(r['path']+':'+str(offset)+':'+digest(piece.encode()))
     segments.append({'segment_id':sid,'source_file':r['path'],'offset':offset,'text':piece,'source_sha256':r['sha256']})
 if (work/'multipart.json.gz').exists():
  with gzip.open(work/'multipart.json.gz','rt',encoding='utf-8') as z:records=json.load(z)
  for r in records:
   t=r.pop('text','');inventory.append(r)
   for offset in range(0,len(t),18000):
    piece=t[offset:offset+18000];segments.append({'segment_id':gid(r['path']+':'+str(offset)+':'+digest(piece.encode())),'source_file':r['path'],'offset':offset,'text':piece,'source_sha256':r['sha256']})
 write(work/'INVENTORY.json',inventory)
 # Packed batches are never truncated. Each individual segment requires a signed-off review.
 batches=work/'batches';batches.mkdir(exist_ok=True)
 for i in range(0,len(segments),12):write(batches/f'{i//12:05d}.json',segments[i:i+12])
 write(work/'BATCH-MANIFEST.json',[f'{i:05d}.json' for i in range((len(segments)+11)//12)])
 write(work/'INGEST-RECEIPT.json',{'source_commit':PIN,'tracked_blobs':len(files),'inventory_records':len(inventory),'segments':len(segments),'batch_count':(len(segments)+11)//12,'failed_fetches':len(failures),'unresolved':[r['path'] for r in inventory if r['status'] in ['BLOCKED','FETCH_FAILED','NEEDS_VISUAL_REVIEW']],'semantic_complete':False})
 print('Ingest checkpoint written; semantic review is a separate mandatory input.')
def audit(work):
 batch_paths=[work/'batches'/n for n in json.loads((work/'BATCH-MANIFEST.json').read_text())] if (work/'BATCH-MANIFEST.json').exists() else sorted((work/'batches').glob('*.json'))
 segments={s['segment_id']:s for p in batch_paths for s in json.loads(p.read_text())}
 if not segments:raise ValueError('No ingestion segments; cannot validate empty completion')
 inventory=json.loads((work/'INVENTORY.json').read_text());nodes={};edges=[];reviews={};errors=[]
 def node(n):
  if n['id'] in nodes and nodes[n['id']]!=n:errors.append('Conflicting node identity '+n['id'])
  nodes[n['id']]=n
 for r in inventory:node({'id':gid(r['path']),'label':r['path'],'file_type':'document','source_file':r['path'],'status':r['status']})
 for p in sorted((work/'fragments').glob('*.json')):
  f=json.loads(p.read_text())
  for review in f['reviews']:
   sid=review['segment_id']
   if sid not in segments or sid in reviews:errors.append('Missing or duplicate review identity '+sid);continue
   if not review.get('summary'):errors.append('Missing semantic summary '+sid)
   if review.get('read_complete') is not True:errors.append('Incomplete reading '+sid)
   reviews[sid]=review
  for n in f['nodes']:node(n)
  for e in f['edges']:
   sid=e.get('segment_id');s=segments.get(sid);quote=e.get('evidence_quote','')
   if not s or not quote or quote not in s['text']:errors.append('Unsupported evidence '+str(sid))
   if e.get('confidence') not in ['EXTRACTED','INFERRED','AMBIGUOUS']:errors.append('Invalid confidence')
   if e.get('confidence')=='EXTRACTED' and e.get('confidence_score')!=1:errors.append('Extracted confidence mismatch')
   if e.get('confidence')!='EXTRACTED' and not e.get('rationale'):errors.append('Missing inference rationale')
   edges.append(e)
 for e in edges:
  if e['source'] not in nodes or e['target'] not in nodes:errors.append('Dangling endpoint')
  if e['source']==e['target']:errors.append('Unreviewed self edge')
 missing=sorted(set(segments)-set(reviews));unresolved=[r['path'] for r in inventory if r['status'] in ['BLOCKED','FETCH_FAILED','NEEDS_VISUAL_REVIEW']]
 # Semantic isolation is reported separately: containment must not disguise it.
 linked={e[k] for e in edges for k in ['source','target']};isolated=sorted(set(nodes)-linked)
 result={'status':'PASS' if not errors and not missing and not unresolved else 'INCOMPLETE','source_commit':PIN,'segments':len(segments),'reviewed_segments':len(reviews),'missing_segments':missing,'errors':errors,'unresolved_sources':unresolved,'isolated_nodes':isolated,'nodes':len(nodes),'edges':len(edges),'meaning_accuracy':'Requires independent evidence review; structural PASS alone is not semantic truth'}
 write(work/'RELATION-AUDIT.json',result);write(work/'semantic-graph.json',{'nodes':list(nodes.values()),'edges':edges})
 print(json.dumps({k:v for k,v in result.items() if k not in ['missing_segments','errors','unresolved_sources','isolated_nodes']}))
 return 0 if result['status']=='PASS' else 2
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('command',choices=['ingest','audit']);a.add_argument('--work',type=Path,default=ROOT/'execution');args=a.parse_args()
 if args.command=='ingest':ingest(args.work)
 else:sys.exit(audit(args.work))
