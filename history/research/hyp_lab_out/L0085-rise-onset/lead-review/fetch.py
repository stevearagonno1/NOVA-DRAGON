from pathlib import Path
import urllib.request,json,hashlib,zipfile,io,concurrent.futures
R=Path(__file__).resolve().parent;HEAD='d1fe9978bee6bc7e3478f53d07633f9fabd198cf';BASE='history/research/hyp_lab_out/L0085-rise-onset/'
paths=[BASE+n for n in ['delivery.json','audit.json','REPORT.md','selection.json','evidence.zip']]+['docs/journal/2026-10-06-l0085-rise-onset/003-executor-complete.md','docs/lanes/L0085-RISE-ONSET-EXECUTION.md','tools/l0085/package_manifest.json']
def get(p):
 for attempt in range(3):
  try:
   b=urllib.request.urlopen('https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/'+HEAD+'/'+p,timeout=45).read();break
  except OSError:
   if attempt==2:raise
 f=R/('paper.md' if '/lanes/' in p else 'tick.md' if '/journal/' in p else p.split('/')[-1]);f.write_bytes(b);return p,len(b)
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
 for x in ex.map(get,paths):print(x,flush=True)
b=(R/'evidence.zip').read_bytes();assert len(b)==3059541 and hashlib.sha256(b).hexdigest()=='5fa745d440e5455d345a9c95f3191c0f922a31aaa846c01dd901dd713fde915a'
with zipfile.ZipFile(io.BytesIO(b)) as z:
 assert all(Path(n).name==n for n in z.namelist());z.extractall(R/'evidence')
print('ARCHIVE_HASH_SIZE_PASS',flush=True)
