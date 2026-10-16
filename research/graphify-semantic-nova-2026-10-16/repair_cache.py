import semantic_pipeline as p,json,gzip,hashlib
from pathlib import Path
root=p.ROOT;sha='8e0f4d1b1097fc08d10d54cc3618b34147ab741e';f=next(x for x in json.loads((root/'SOURCE-TREE.json').read_text())['tree'] if x['sha']==sha)
b=p.download(f);obj={'converter_version':2,'blob':sha,'original_path':f['path'],'records':list(p.convert(f['path'],b))}
target=root/'execution/sources'/f'{sha}.json.gz';temp=target.with_suffix('.repair')
with gzip.open(temp,'wt',encoding='utf-8') as z:json.dump(obj,z,ensure_ascii=False)
with gzip.open(temp,'rt',encoding='utf-8') as z:check=json.load(z)
assert check==obj
backup=target.with_suffix('.corrupt-preserved')
if not backup.exists():target.rename(backup)
temp.replace(target)
p.write(root/'execution/CACHE-REPAIR.json',{'status':'PASS','source':f['path'],'git_blob':sha,'original_corrupt_cache_preserved':backup.name,'rebuilt_sha256':p.digest(target.read_bytes()),'record_count':len(obj['records']),'root_cause':'not established; corruption detected during full read, never treated as valid evidence'})
print('cache repaired and roundtrip verified')
