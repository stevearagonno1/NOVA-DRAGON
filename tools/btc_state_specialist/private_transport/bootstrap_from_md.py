"""Fetch only the pinned lightweight package after a whole-workspace preflight."""
import argparse,base64,hashlib,json,os,re,time,urllib.request
from pathlib import Path
LIMIT=125000000
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args):raise RuntimeError('redirect refused')
def preflight(extra=0,target=None):
    root=Path(os.environ['NOVA_WORKSPACE']).resolve(strict=True)
    if target is not None and not Path(target).resolve().is_relative_to(root):raise RuntimeError('target outside complete workspace')
    used=sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and not p.is_symlink())
    if used+extra>LIMIT:raise RuntimeError(f'125 MB workspace limit before bootstrap: {used} existing bytes; use a genuinely fresh environment; no deletion or narrower root')
    return used
def fetch(path,ref,opener):
    preflight()
    url='https://api.github.com/repos/stevearagonno1/NOVA-DRAGON/contents/tools/btc_state_specialist/'+path+'?ref='+ref
    request=urllib.request.Request(url,headers={'User-Agent':'NOVA-public-bootstrap','Accept':'application/vnd.github+json'})
    with opener.open(request,timeout=60) as response:
        data=response.read(1500001)
    if len(data)>1500000:raise RuntimeError('bootstrap response exceeds lightweight limit')
    item=json.loads(data)
    if item['encoding']!='base64':raise RuntimeError('unsupported source encoding')
    data=base64.b64decode(item['content'])
    if len(data)>1000000 or hashlib.sha1(('blob '+str(len(data))+'\0').encode()+data).hexdigest()!=item['sha']:raise RuntimeError('invalid source blob')
    return data
def save(path,data):
    path=Path(path);preflight(len(data),path)
    if path.exists():
        if path.read_bytes()!=data:raise RuntimeError('existing file differs; retain prior attempt: '+str(path))
    else:
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
def main(ref,out):
    started=time.time();preflight(target=out)
    if not re.fullmatch(r'[0-9a-f]{40}',ref):raise RuntimeError('exact source commit required')
    opener=urllib.request.build_opener(NoRedirect())
    raw=fetch('package_manifest.json',ref,opener);manifest=json.loads(raw)
    preflight(sum(x['bytes'] for x in manifest['files'].values())+len(raw)+1024,out)
    for name,entry in manifest['files'].items():
        path=Path(name)
        if path.is_absolute() or '..' in path.parts:raise RuntimeError('invalid package path')
        data=fetch(name,ref,opener)
        if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:raise RuntimeError('source hash mismatch: '+name)
        save(out/path,data)
    save(out/'package_manifest.json',raw)
    save(out/'source_release.json',json.dumps({'code_commit':ref},sort_keys=True).encode())
    if not (out/'TASK_START.json').exists():save(out/'TASK_START.json',json.dumps({'task_started_epoch':started}).encode())
    print('LIGHTWEIGHT_SOURCE_VERIFIED; no price inputs saved')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--ref',required=True);parser.add_argument('--out',type=Path,default=Path('btc-specialist'))
    args=parser.parse_args();main(args.ref,args.out)
