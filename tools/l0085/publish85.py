"""Few-request, paced Git Data upload; no gh/origin, no per-candidate API calls."""
from pathlib import Path
import base64,hashlib,json,os,time,urllib.request,urllib.error,zipfile
REPO='stevearagonno1/NOVA-DRAGON';BRANCH='agent/l0085-rise-onset-2026-10-06';DEST='history/research/hyp_lab_out/L0085-rise-onset';LAST=0

def api(path,method='GET',body=None):
    global LAST
    token=os.environ.get('GH_TOKEN','');headers={'User-Agent':'NOVA-L0085','Accept':'application/vnd.github+json','Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    if method!='GET' and not token:raise RuntimeError('GH_TOKEN unavailable')
    for attempt in range(5):
        if method!='GET':
            while time.monotonic()-LAST<15:time.sleep(min(1,15-(time.monotonic()-LAST)))
            LAST=time.monotonic()
        req=urllib.request.Request('https://api.github.com/repos/'+REPO+path,data=None if body is None else json.dumps(body).encode(),headers=headers,method=method)
        try:
            with urllib.request.urlopen(req,timeout=60) as f:return json.load(f)
        except urllib.error.HTTPError as e:
            msg=e.read().decode().replace(token,'[REDACTED]') if token else e.read().decode();retry=e.headers.get('Retry-After')
            if e.code not in (429,500,502,503,504) and not(e.code==403 and (retry or 'rate limit' in msg.lower())):raise RuntimeError('HTTP '+str(e.code)+': '+msg) from None
            if attempt==4:raise RuntimeError('HTTP '+str(e.code)+': '+msg+' retries exhausted') from None
            seconds=float(retry) if retry else max(60,float(e.headers.get('X-RateLimit-Reset',0))-time.time()+2)
            until=time.monotonic()+seconds;print('SERVER_WAIT',e.code,'seconds',seconds,flush=True)
            while time.monotonic()<until:time.sleep(min(30,max(0,until-time.monotonic())));print('WAITING allowed server retry',flush=True)
        except (TimeoutError,OSError) as e:
            if attempt==4:raise RuntimeError(type(e).__name__+': '+str(e).replace(token,'[REDACTED]') if token else str(e)) from None
            time.sleep(3)

def get_file(commit,path):
    row=api('/contents/'+path+'?ref='+commit);assert row['encoding']=='base64';return base64.b64decode(row['content'])
def blob_sha(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()

def publish(files,message,expected):
    assert api('/git/ref/heads/'+BRANCH)['object']['sha']==expected,'remote head changed; no overwrite'
    commit=api('/git/commits/'+expected);entries=[]
    for path,b in files.items():
        token=os.environ.get('GH_TOKEN','').encode()
        if token and token in b:raise RuntimeError('secret found in publication payload')
        if path.endswith('.zip'):
            row=api('/git/blobs','POST',{'encoding':'base64','content':base64.b64encode(b).decode()});assert row['sha']==blob_sha(b);entries.append({'path':path,'mode':'100644','type':'blob','sha':row['sha']})
        else:entries.append({'path':path,'mode':'100644','type':'blob','content':b.decode()})
    tree=api('/git/trees','POST',{'base_tree':commit['tree']['sha'],'tree':entries})['sha']
    head=api('/git/commits','POST',{'parents':[expected],'tree':tree,'message':message})['sha']
    assert api('/git/ref/heads/'+BRANCH)['object']['sha']==expected,'concurrent publisher detected'
    try:api('/git/refs/heads/'+BRANCH,'PATCH',{'sha':head,'force':False})
    except RuntimeError:
        if api('/git/ref/heads/'+BRANCH)['object']['sha']!=head:raise
    assert api('/git/ref/heads/'+BRANCH)['object']['sha']==head
    # Fetch Git blobs by SHA, including archives >1 MB; verify full bytes rather than headers.
    for path,b in files.items():
        row=api('/git/blobs/'+blob_sha(b));actual=base64.b64decode(row['content']);assert actual==b,('immutable readback',path)
    return head

def preflight(root,source):
    root=Path(root);head=api('/git/ref/heads/'+BRANCH)['object']['sha']
    # branch may have its public paper commit after source; verify immutable package manifest on current branch.
    assert get_file(head,'tools/l0085/package_manifest.json')==(root/'package_manifest.json').read_bytes(),'different source package on result branch'
    proof={'round':'L0085','source':source,'kind':'NON_FINANCIAL_UPLOAD_READBACK','market':'NOT RUN'}
    data=(json.dumps(proof,sort_keys=True)+'\n').encode();path=DEST+'/readiness/upload-proof.json'
    try:already=get_file(head,path)
    except RuntimeError as e:
        if 'HTTP 404' not in str(e):raise
    else:
        if already==data:return head
        raise RuntimeError('different upload proof already exists')
    return publish({path:data},'L0085: non-financial upload/readback readiness',head)

def complete(root,out,source):
    root=Path(root);out=Path(out);head=api('/git/ref/heads/'+BRANCH)['object']['sha'];assert get_file(head,'tools/l0085/package_manifest.json')==(root/'package_manifest.json').read_bytes()
    delivery=json.loads((out/'delivery.json').read_text());assert not delivery['synthetic'];assert json.loads((out/'audit.json').read_text())['status']=='PASS'
    archive=out.parent/'L0085-evidence.zip'
    # deterministic archive permits idempotent publication after uncertain network exit.
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.iterdir()):
            if p.is_file() and not p.name.endswith('.pending'):
                info=zipfile.ZipInfo(p.name,(2026,10,6,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes())
    digest=hashlib.sha256(archive.read_bytes()).hexdigest();receipt={'status':delivery['status'],'source':source,'archive_sha256':digest,'archive_bytes':archive.stat().st_size,'rows':delivery['rows'],'branch':BRANCH,'market_scope':'discovery only; validation NOT RUN'}
    path=DEST+'/delivery.json';b=(json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode()
    try:prior=get_file(head,path)
    except RuntimeError as e:
        if 'HTTP 404' not in str(e):raise
    else:
        if prior==b:
            recorded=api('/git/blobs/'+blob_sha(archive.read_bytes()));assert base64.b64decode(recorded['content'])==archive.read_bytes();return head,receipt
        raise RuntimeError('different completed delivery already exists; Lead review required')
    log=get_file(head,'LOG.md');tick='docs/journal/2026-10-06-l0085-rise-onset/002-executor-complete.md'
    files={DEST+'/evidence.zip':archive.read_bytes(),path:b,DEST+'/REPORT.md':(out/'REPORT.md').read_bytes(),DEST+'/audit.json':(out/'audit.json').read_bytes(),DEST+'/selection.json':(out/'selection.json').read_bytes(),
        'LOG.md':log+b'\n\n## L0085 completed discovery\nFull registered signal grid scored, raw matching audited, results uploaded for Lead review. No validation or trading.\n',
        tick:b'- Decision: execute the registered onset-discovery search only.\n- Execution: all candidates scored; raw evidence reconciled.\n- Produced: history/research/hyp_lab_out/L0085-rise-onset/evidence.zip and audit/report/selection.\n- Next: Lead independently reviews; no adoption or validation run.\n'}
    return publish(files,'L0085: complete registered onset discovery, raw evidence and audit',head),receipt
