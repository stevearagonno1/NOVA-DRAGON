"""Publish existing registered BTC evidence; never rerun research or access old tokens."""
import argparse,base64,csv,gzip,hashlib,json,os,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
REPO='stevearagonno1/NOVA-DRAGON'
SOURCE='b0b8064c64f75d9a028d30e03b6bb9a898423b65'
BRANCH='agent/btc-registration-from-repo-execution-2026-10-15'
DEST='research/btc-registration-from-repo-2026-10-15/executor'
MONTHS=['2025-09','2025-10','2025-11','2025-12']+[f'2026-{n:02}' for n in range(1,10)]
COUNTS={'1':568800,'5':113760,'15':37920,'60':9480}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def digest(b):return hashlib.sha256(b).hexdigest()
def decode(blob):return base64.b64decode(blob['content'])
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
def preflight(api):
 repo=api.call('GET',f'/repos/{REPO}');assert repo.get('permissions',{}).get('push') is True,'Token does not confirm repository write permission'
 c=api.call('GET',f'/repos/{REPO}/git/commits/{SOURCE}');assert c['sha']==SOURCE
 probe=b'NOVA authorised publication preflight; no market measurement'
 h=api.call('POST',f'/repos/{REPO}/git/blobs',{'content':base64.b64encode(probe).decode(),'encoding':'base64'})['sha']
 assert decode(api.call('GET',f'/repos/{REPO}/git/blobs/{h}'))==probe,'Write/read credential probe failed'
 return c
