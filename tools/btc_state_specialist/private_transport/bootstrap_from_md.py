import os,json,base64,hashlib,urllib.request,pathlib,time
CODE='cd161f8313cb2e3e135437f1e66109399b703272'
TRANSPORT='18f97ea8c0df5149ebb82c1d502700b79db295a7'
ROOT='https://api.github.com/repos/stevearagonno1/NOVA-DRAGON/contents/'
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args): raise RuntimeError('Redirect refused')
opener=urllib.request.build_opener(NoRedirect())
def fetch(name,ref):
    req=urllib.request.Request(ROOT+name+'?ref='+ref,headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'NOVA-MD-bootstrap','Accept':'application/vnd.github+json'})
    with opener.open(req,timeout=60) as response: item=json.load(response)
    assert item['encoding']=='base64'
    data=base64.b64decode(item['content'])
    assert hashlib.sha1(('blob '+str(len(data))+'\0').encode()+data).hexdigest()==item['sha']
    return data
def save(name,data):
    p=pathlib.Path(name);p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists(): assert p.read_bytes()==data,'Existing file differs: '+name
    else: p.write_bytes(data)
pathlib.Path('private-btc-executor').mkdir(exist_ok=True)
p=pathlib.Path('private-btc-executor/TASK_START.json')
if not p.exists(): p.write_text(json.dumps({'task_started_epoch':time.time()}))
manifest=fetch('tools/btc_state_specialist/package_manifest.json',CODE)
for name,entry in json.loads(manifest)['files'].items():
    assert pathlib.PurePosixPath(name).name==name
    data=fetch('tools/btc_state_specialist/'+name,CODE)
    assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256']
    save('btc-specialist/'+name,data)
save('btc-specialist/package_manifest.json',manifest)
for name in ['readiness.json','reference_checks.json']:
    save('btc-specialist/'+name,fetch('tools/btc_state_specialist/'+name,CODE))
save('btc-specialist/paper.md',fetch('tools/btc_state_specialist/paper.md',TRANSPORT))
save('private-btc-executor/rest_publish.py',fetch('tools/btc_state_specialist/private_transport/rest_publish.py',TRANSPORT))
print('BOOTSTRAP_VERIFIED: source files downloaded from pinned repository commits')
