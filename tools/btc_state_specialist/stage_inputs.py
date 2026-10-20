"""Read pinned public price inputs into memory; never stage prices on disk."""
from pathlib import Path
import argparse, hashlib, io, json, re, urllib.request
from workspace_guard import preflight
ROOT=Path(__file__).resolve().parent

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args):
        raise RuntimeError('price source redirect refused')

def stage(item,data):
    # Compatibility entry point: validation only, no disk write.
    if len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item['sha256']:
        raise RuntimeError('price input hash/size mismatch: '+item['month'])
    return data

def read(item, opener=None):
    preflight()
    ref=item['source_commit'];path=item['repository_path']
    if not re.fullmatch(r'[0-9a-f]{40}',ref) or '..' in Path(path).parts or path.startswith('/'):
        raise RuntimeError('invalid pinned input reference')
    if not 0 < item['bytes'] <= 1000000:
        raise RuntimeError('input exceeds registered bounded-memory reader')
    url='https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/'+ref+'/'+path
    request=urllib.request.Request(url,headers={'User-Agent':'NOVA-price-memory-reader'})
    client=opener or urllib.request.build_opener(NoRedirect())
    with client.open(request,timeout=60) as response:
        data=response.read(item['bytes']+1)
    return stage(item,data)

def open_verified(item):
    return io.BytesIO(read(item))

def check():
    items=json.loads((ROOT/'inputs.json').read_text())
    for item in items:
        read(item)
        print('REMOTE_INPUT_VERIFIED_NO_DISK_COPY',item['month'],flush=True)
    return len(items)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['check'])
    parser.parse_args()
    print('INPUTS_OK',check())

