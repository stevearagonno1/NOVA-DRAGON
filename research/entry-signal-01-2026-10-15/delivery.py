import base64,hashlib,json,time,urllib.request,urllib.error
REPO="stevearagonno1/NOVA-DRAGON"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class API:
 def __init__(self,token):
  if not token or token.startswith('PENDING'):raise RuntimeError('GH_TOKEN missing: require owner-authorised current token')
  self.token=token
 def call(self,method,path,data=None):
  url='https://api.github.com'+path
  req=urllib.request.Request(url,data=None if data is None else json.dumps(data).encode(),method=method,headers={'Authorization':'Bearer '+self.token,'Accept':'application/vnd.github+json','Content-Type':'application/json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'NOVA-registration-publisher'})
  if method!='GET':time.sleep(0.4)
  try:
   with urllib.request.urlopen(req,timeout=45) as r:return json.load(r)
  except urllib.error.HTTPError as e:
   msg=e.read().decode(errors='replace').replace(self.token,'[REDACTED]')
   retry=e.headers.get('Retry-After','unspecified')
   raise RuntimeError(f'GitHub {method} {path}: HTTP{e.code}; Retry-After={retry}; {msg[:1200]}') from None
 def ref(self):return self.call('GET',f'/repos/{REPO}/git/ref/heads/'+urllib.parse.quote(BRANCH,safe=''))['object']['sha']
def publish(api,branch,parent,files):
 prefix=f'/repos/{REPO}'
 try:head=api.call('GET',prefix+'/git/ref/heads/'+branch)['object']['sha']
 except RuntimeError as e:
  if 'HTTP404' not in str(e):raise
  api.call('POST',prefix+'/git/refs',{'ref':'refs/heads/'+branch,'sha':parent});head=parent
 base=api.call('GET',prefix+'/git/commits/'+head);entries=[];blobs={}
 for path,file in files.items():
  assert file.stat().st_size<25000000
  b=file.read_bytes();s=api.call('POST',prefix+'/git/blobs',{'content':base64.b64encode(b).decode(),'encoding':'base64'})['sha'];entries.append({'path':path,'mode':'100644','type':'blob','sha':s});blobs[path]=(s,sha(file))
 tree=api.call('POST',prefix+'/git/trees',{'base_tree':base['tree']['sha'],'tree':entries})['sha'];commit=api.call('POST',prefix+'/git/commits',{'message':'BTC fixed causal measurements; no state search','parents':[head],'tree':tree})['sha']
 assert api.call('GET',prefix+'/git/ref/heads/'+branch)['object']['sha']==head
 api.call('PATCH',prefix+'/git/refs/heads/'+branch,{'sha':commit,'force':False})
 for path,(s,expected) in blobs.items():
  import hashlib
  b=base64.b64decode(api.call('GET',prefix+'/git/blobs/'+s)['content']);assert hashlib.sha256(b).hexdigest()==expected
 assert api.call('GET',prefix+'/git/commits/'+commit)['tree']['sha']==tree
 return {'commit':commit,'files_verified':len(files),'branch':branch}
