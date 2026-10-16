"""Fetch explicit text/code blobs only, verify Git identities; never execute them."""
from pathlib import Path
import json,hashlib,urllib.request,urllib.parse,concurrent.futures,time
ROOT=Path(__file__).resolve().parent
def main():
    manifest=json.loads((ROOT/'SOURCE-FILES.json').read_text());files=manifest['files'];out=ROOT/'corpus';out.mkdir(exist_ok=True)
    def one(item):
        p=out/item['path'];p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists():b=p.read_bytes()
        else:
            url='https://raw.githubusercontent.com/'+manifest['repo']+'/'+manifest['commit']+'/'+urllib.parse.quote(item['path'],safe='/')
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(url,timeout=30) as r:b=r.read()
                    break
                except Exception:
                    if attempt==2:raise
                    time.sleep(0.5+attempt)
        assert len(b)==item['size'] and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==item['sha'],item['path']
        p.write_bytes(b)
        return {'path':item['path'],'bytes':len(b),'git_blob':item['sha'],'sha256':hashlib.sha256(b).hexdigest()}
    started=time.monotonic();result=[];errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
        tasks={pool.submit(one,i):i for i in files}
        for f in concurrent.futures.as_completed(tasks):
            try:result.append(f.result())
            except Exception as e:errors.append({'path':tasks[f]['path'],'error':str(e)})
    report={'status':'PASS' if not errors else 'BLOCKED','source_commit':manifest['commit'],'expected_files':len(files),'verified_files':len(result),'files':sorted(result,key=lambda x:x['path']),'errors':errors,'seconds':time.monotonic()-started}
    (ROOT/'SOURCE-AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['files']}),flush=True)
    if errors:raise SystemExit(2)
if __name__=='__main__':main()
