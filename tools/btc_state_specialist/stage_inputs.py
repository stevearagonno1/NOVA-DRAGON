"""Stage only pinned compressed inputs. Connector fallback accepts one JSON item on stdin."""
from pathlib import Path
import argparse,base64,hashlib,json,os,sys,urllib.request
ROOT=Path(__file__).resolve().parent
def stage(item,data):
    from specialist import atomic
    assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'],'input hash/size'
    atomic(ROOT/item['local_path'],data)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['download','connector','check']);a=p.parse_args();items=json.loads((ROOT/'inputs.json').read_text())
    if a.mode=='connector':
        payload=json.load(sys.stdin);item=next(x for x in items if x['month']==payload['month']);stage(item,base64.b64decode(payload['content'],validate=False))
    elif a.mode=='download':
        for item in items:
            target=ROOT/item['local_path']
            if target.exists():stage(item,target.read_bytes());continue
            url='https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/'+item['source_commit']+'/'+item['repository_path']
            with urllib.request.urlopen(url,timeout=60) as r:data=r.read(item['bytes']+1)
            stage(item,data);print('STAGED',item['month'],flush=True)
    else:
        for item in items:
            path=ROOT/item['local_path'];assert path.stat().st_size==item['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
        print('INPUTS_OK',len(items))
