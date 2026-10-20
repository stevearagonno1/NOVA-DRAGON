"""Direct GitHub REST transport. Token comes only from GH_TOKEN, never output or URL."""
from pathlib import Path
import argparse,base64,hashlib,io,json,os,sys,time,traceback,urllib.request,urllib.error,urllib.parse,zipfile
REPO='/repos/stevearagonno1/NOVA-DRAGON'
CODE='cd161f8313cb2e3e135437f1e66109399b703272'
BRANCH='agent/btc-state-specialist-results-2026-10-18'
DEST='history/research/hyp_lab_out/BTC-STATE-SPECIALIST-2026-10-18/'
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args):raise RuntimeError('GitHub redirect refused; credentials were not forwarded')
class API:
    def __init__(self):
        self.token=os.environ.get('GH_TOKEN','').strip()
        if not self.token:raise RuntimeError('GH_TOKEN is not initialized')
        self.opener=urllib.request.build_opener(NoRedirect())
    def call(self,method,path,data=None,missing=False):
        assert path.startswith('/') and not path.startswith('//')
        url='https://api.github.com'+REPO+path
        body=None if data is None else json.dumps(data).encode()
        for attempt in range(6):
            req=urllib.request.Request(url,data=body,method=method,headers={'Authorization':'Bearer '+self.token,'Accept':'application/vnd.github+json','Content-Type':'application/json','User-Agent':'NOVA-executor-private-transport','X-GitHub-Api-Version':'2022-11-28'})
            try:
                with self.opener.open(req,timeout=60) as r:return json.load(r)
            except urllib.error.HTTPError as e:
                if missing and e.code==404:return None
                detail=e.read().decode(errors='replace').replace(self.token,'[REDACTED]')
                if e.code in [429,502,503,504] or (e.code==403 and e.headers.get('Retry-After')):
                    delay=float(e.headers.get('Retry-After',2**attempt));print('SERVER_BACKOFF_SECONDS',delay,flush=True);time.sleep(delay);continue
                raise RuntimeError('GitHub HTTP '+str(e.code)+': '+detail) from None
        raise RuntimeError('GitHub retry budget exhausted; preserve checkpoint and retry later')
    def ref(self,branch):return self.call('GET','/git/ref/heads/'+urllib.parse.quote(branch,safe='/'),missing=True)
    def branch(self,branch,parent):
        assert branch.startswith('agent/') and branch!='main'
        r=self.ref(branch)
        if r:return r['object']['sha']
        self.call('POST','/git/refs',{'ref':'refs/heads/'+branch,'sha':parent});return parent
    def commit(self,branch,parent,files,message):
        assert branch.startswith('agent/') and branch!='main'
        before=self.ref(branch);assert before['object']['sha']==parent,'work branch changed before upload'
        base=self.call('GET','/git/commits/'+parent)['tree']['sha'];entries=[]
        for name,b in files.items():
            if self.token.encode() in b:raise RuntimeError('private credential detected in public payload: '+name)
            if name.endswith('.zip'):
                with zipfile.ZipFile(io.BytesIO(b)) as z:
                    for n in z.namelist():
                        if self.token.encode() in z.read(n):raise RuntimeError('private credential detected in archive')
            blob=self.call('POST','/git/blobs',{'encoding':'base64','content':base64.b64encode(b).decode()})
            expected=hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest();assert blob['sha']==expected
            entries.append({'path':name,'mode':'100644','type':'blob','sha':blob['sha']})
            print('BLOB_VERIFIED',name,flush=True)
        tree=self.call('POST','/git/trees',{'base_tree':base,'tree':entries})
        commit=self.call('POST','/git/commits',{'parents':[parent],'tree':tree['sha'],'message':message})
        assert self.ref(branch)['object']['sha']==parent,'work branch changed; no force update'
        self.call('PATCH','/git/refs/heads/'+urllib.parse.quote(branch,safe='/'),{'sha':commit['sha'],'force':False})
        return commit['sha'],tree['sha']
    def tree(self,commit):
        c=self.call('GET','/git/commits/'+commit);r=self.call('GET','/git/trees/'+c['tree']['sha']+'?recursive=1');assert not r['truncated'];r['commit']=commit;return r
    def document(self,path,ref):
        d=self.call('GET','/contents/'+urllib.parse.quote(path,safe='/')+'?ref='+ref)
        assert d['encoding']=='base64','GitHub file exceeds contents reader limits'
        return base64.b64decode(d['content'])
def dump(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2))
def verify_files(api,commit,files):
    r=api.tree(commit);entries={x['path']:x for x in r['tree'] if x['type']=='blob'}
    for name,b in files.items():
        expected=hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest();assert entries[name]['sha']==expected and entries[name]['size']==len(b),name
    return r
def main(a):
    api=API();package=Path(a.package).resolve();sys.path.insert(0,str(package))
    if a.mode=='probe':
        branch='agent/btc-private-transport-2026-10-20';parent=api.branch(branch,CODE)
        content=json.dumps({'purpose':'nonfinancial direct REST write/readback probe','contains_credentials':False},sort_keys=True).encode();buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('probe.json',content)
        files={'tools/btc_state_specialist/REST_PROBE.json':content,'tools/btc_state_specialist/REST_PROBE.zip':buf.getvalue()}
        commit,tree=api.commit(branch,parent,files,'Verify private-token REST transport without secrets or market measurement');verify_files(api,commit,files)
        result={'status':'DIRECT_REST_WRITE_AND_IMMUTABLE_READBACK_PASS','commit':commit,'branch':branch,'verified_files':2,'no_credentials_uploaded':True};dump(Path(a.out)/'REST_PROBE.json',result);print(json.dumps(result));return
    import specialist as S,stage_inputs
    if a.mode=='inputs':
        for item in json.loads((package/'inputs.json').read_text()):
            path=package/item['local_path']
            data=path.read_bytes() if path.exists() else api.document(item['repository_path'],item['source_commit'])
            stage_inputs.stage(item,data);print('INPUT_VERIFIED',item['month'],flush=True)
        S.validate_source_inputs();return
    import delivery as D
    out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True);S.audit(out)
    checkpoint=json.loads((out/'checkpoint.json').read_text());assert not checkpoint['fixture'],'synthetic output is not a market delivery'
    started=json.loads(Path(a.started).read_text())['task_started_epoch']
    head=api.branch(BRANCH,CODE);statefile=out/'REST_UPLOAD_STATE.json';state=json.loads(statefile.read_text()) if statefile.exists() else {}
    if state.get('receipt_commit'):
        raw=api.document(DEST+'VERIFIED_DELIVERY.json',state['receipt_commit']);assert raw==(out/'VERIFIED_DELIVERY.json').read_bytes();assert api.ref(BRANCH)['object']['sha']==state['receipt_commit'];print('ALREADY_VERIFIED');return
    if state.get('payload_commit') and head!=state['payload_commit']:
        # A crash after receipt commit but before its local checkpoint is recoverable.
        remote=api.document(DEST+'VERIFIED_DELIVERY.json',head);r=json.loads(remote)
        assert r['payload_commit']==state['payload_commit'] and r['code_commit']==CODE and not r['fixture'],'unexpected remote receipt'
        payload=json.loads((out/'publish_payload.json').read_text());verify_files(api,head,{x['path']:base64.b64decode(x['content']) for x in payload['files']})
        (out/'VERIFIED_DELIVERY.json').write_bytes(remote);state['receipt_commit']=head;state['task_elapsed_through_verified_delivery_seconds']=time.time()-started;dump(statefile,state);print('ALREADY_VERIFIED_AFTER_INTERRUPTION');return
    payloadfile=out/'publish_payload.json'
    if not payloadfile.exists():
        c=api.call('GET','/git/commits/'+head);docs={p:api.document(p,head).decode() for p in ['LOG.md','docs/DECISIONS.md','docs/HANDOFF.md']}
        ctx={'head':head,'tree':c['tree']['sha'],'documents':docs,'task_started_epoch':started,'compute_only_seconds':'not measured; see measurement stdout'};dump(out/'remote_context.json',ctx);D.build(out,out/'remote_context.json',CODE)
    payload=json.loads(payloadfile.read_text());assert not payload['fixture'];files={x['path']:base64.b64decode(x['content']) for x in payload['files']}
    if state.get('payload_commit'):commit=state['payload_commit'];verify_files(api,commit,files)
    elif head==payload['expected_head']:
        commit,tree=api.commit(BRANCH,head,files,'Measure and audit registered BTC conditional-state discovery');state={'payload_commit':commit};dump(statefile,state)
    else:
        # Lost local commit response: accept only the exact already-published payload.
        verify_files(api,head,files);commit=head;state={'payload_commit':commit};dump(statefile,state)
    readback=verify_files(api,commit,files);dump(out/'remote_readback.json',readback);D.verify(out,out/'remote_readback.json')
    receipt_path=out/'VERIFIED_DELIVERY.json';receipt=json.loads(receipt_path.read_text());assert receipt['status']=='REMOTE_PAYLOAD_VERIFIED_LEAD_REVIEW_PENDING'
    receipt['elapsed_to_payload_verification_seconds']=time.time()-started;receipt['transport']='direct GitHub REST; GH_TOKEN never stored in public files';dump(receipt_path,receipt)
    tick='القرار: إثبات وصول النتائج قبل إعلان تم.\nالتنفيذ: رفع REST مباشر والتحقق من كل الملفات من مرجع ثابت.\nالناتج: إيصال الوصول مع مرجع الكود والقياس؛ الحكم المستقل للقائد.\nالتالي: مراجعة القائد، دون اعتماد أو دمج أو دفع إلىmain.\n'.encode()
    finalfiles={DEST+'VERIFIED_DELIVERY.json':receipt_path.read_bytes(),'docs/journal/2026-10-18-btc-state-specialist-execution/002-verified-upload.md':tick}
    parent=api.ref(BRANCH)['object']['sha'];assert parent==commit,'unexpected results branch head'
    receipt_commit,tree=api.commit(BRANCH,parent,finalfiles,'Record verified BTC delivery through direct private-token transport');verify_files(api,receipt_commit,finalfiles)
    assert api.document(DEST+'VERIFIED_DELIVERY.json',receipt_commit)==receipt_path.read_bytes()
    assert api.ref(BRANCH)['object']['sha']==receipt_commit
    state.update(receipt_commit=receipt_commit,task_elapsed_through_verified_delivery_seconds=time.time()-started);dump(statefile,state);dump(out/'COMPLETION.json',{'status':'VERIFIED_DELIVERY_COMPLETE','receipt_commit':receipt_commit,'task_elapsed_through_verified_delivery_seconds':state['task_elapsed_through_verified_delivery_seconds'],'compute_only_seconds':'not measured; see measurement stdout','token_saved_publicly':False})
    print(json.dumps({'status':'VERIFIED_DELIVERY_COMPLETE','receipt_commit':receipt_commit}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['probe','inputs','publish']);p.add_argument('--package',default='btc-specialist');p.add_argument('--out',default='private-btc-executor/checks');p.add_argument('--started',default='private-btc-executor/TASK_START.json');a=p.parse_args()
    try:main(a)
    except Exception as e:
        token=os.environ.get('GH_TOKEN','');reason=(type(e).__name__+': '+str(e)).replace(token,'[REDACTED]') if token else type(e).__name__+': '+str(e)
        dump(Path(a.out)/'REST_ERROR.json',{'status':'BLOCKED','actual_error':reason,'market_result':'not inferred from operational failure'});print(reason,file=sys.stderr);sys.exit(1)
