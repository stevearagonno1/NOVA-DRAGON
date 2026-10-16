"""One pinned archive transfer; retain no whole repository on disk."""
import io,urllib.request,zipfile,hashlib,threading,json,time
import semantic_pipeline as p
started=time.monotonic()
u=f'https://codeload.github.com/{p.REPO}/zip/{p.PIN}'
print('Fetching pinned repository archive in memory',flush=True)
with urllib.request.urlopen(u,timeout=180) as r:body=r.read()
print('Archive transfer bytes',len(body),flush=True)
z=zipfile.ZipFile(io.BytesIO(body));prefix=z.namelist()[0].split('/')[0]+'/'
lock=threading.Lock()
def from_archive(f):
 with lock:b=z.read(prefix+f['path'])
 assert len(b)==f['size'],f['path']
 assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==f['sha'],f['path']
 return b
p.download=from_archive
p.ingest(p.ROOT/'execution')
p.write(p.ROOT/'execution/BULK-RECEIPT.json',{'pinned_commit':p.PIN,'archive_bytes':len(body),'transport':'GitHub codeload archive, per-blob Git SHA1 verification','seconds':time.monotonic()-started})
