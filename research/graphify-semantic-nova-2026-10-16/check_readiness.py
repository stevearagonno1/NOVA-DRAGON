from pathlib import Path
import json,sys,io,zipfile,tempfile,sqlite3
import semantic_pipeline as p
root=Path(__file__).parent;tree=json.loads((root/'SOURCE-TREE.json').read_text())['tree'];out=[]
# Real pinned files, including Arabic PDF and DOCX; no market code execution.
for ext in ['.pdf','.docx','.zip','.rar','.parquet']:
 f=min((f for f in tree if f['type']=='blob' and f['path'].endswith(ext)),key=lambda x:x['size'])
 matches=json.loads((root/'LOCAL-MATCHES.json').read_text())
 b=Path(matches[f['sha']]).read_bytes() if f['sha'] in matches else p.download(f)
 r=list(p.convert(f['path'],b));out.append({'path':f['path'],'git_blob':f['sha'],'records':len(r),'statuses':[x['status'] for x in r]})
# Lossless segmentation, explicit failures, SQL schema, and rejection of fabricated edges.
c=sqlite3.connect(':memory:');c.execute('create table measurements (value real)');c.execute('insert into measurements values(1.0)');b=c.serialize();c.close()
assert list(p.convert('example.sqlite',b))[0]['status']=='DATA_SCHEMA'
assert list(p.convert('bad.zip',b'broken'))[-1]['status']=='BLOCKED'
with tempfile.TemporaryDirectory() as d:
 w=Path(d);(w/'batches').mkdir();(w/'fragments').mkdir()
 p.write(w/'INVENTORY.json',[{'path':'a.md','status':'TEXT'}])
 p.write(w/'batches/00000.json',[{'segment_id':'s1','source_file':'a.md','text':'RSI is measured on BTC.'}])
 p.write(w/'fragments/00000.json',{'reviews':[{'segment_id':'s1','read_complete':True,'summary':'RSI measurement on BTC','no_relationship_reason':None}], 'nodes':[{'id':'rsi','label':'RSI'}], 'edges':[{'source':p.gid('a.md'),'target':'rsi','confidence':'EXTRACTED','confidence_score':1.0,'segment_id':'s1','evidence_quote':'invented'}]})
 assert p.audit(w)==2
 f=json.loads((w/'fragments/00000.json').read_text());f['edges'][0]['evidence_quote']='RSI is measured on BTC.';p.write(w/'fragments/00000.json',f);assert p.audit(w)==0
 f['reviews']=[];p.write(w/'fragments/00000.json',f);assert p.audit(w)==2
p.write(root/'READINESS.json',{'status':'PARTIAL_READINESS_CHECKED','real_sources':out,'checks':['SQLite schema extraction','corrupt archive surfaced','fabricated quotation rejected','valid fixture accepted','unread segment rejected'],'not_checked':['whole repository ingestion','RAR conversion dependency','Parquet conversion dependency','full semantic extraction','independent semantic accuracy review','remote output publication']})
print('Readiness evidence saved; full semantic completion not claimed.')
