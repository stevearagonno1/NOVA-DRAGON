from pathlib import Path
import urllib.request,concurrent.futures,json,hashlib,zipfile,io
R=Path(__file__).resolve().parent;head='ae57878017bc92c0e64a4c655c65160a6f1e0e7d';base='https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/'+head+'/'
dest='history/research/hyp_lab_out/L0087-timing-personalization/'
paths=[dest+p for p in ['evidence.zip','audit.json','delivery.json','REPORT.md','selection87.json']]+['tools/l0087/package_manifest.json','docs/lanes/L0087-TIMING-PERSONALIZATION-EXECUTION.md','LOG.md','docs/DECISIONS.md']
def fetch(path):
 for attempt in range(4):
  try:
   b=urllib.request.urlopen(base+path,timeout=60).read();p=R/'remote'/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);return path
  except OSError:
   if attempt==3:raise
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:list(ex.map(fetch,paths))
p=R/'remote'/dest;receipt=json.loads((p/'delivery.json').read_text());b=(p/'evidence.zip').read_bytes();assert hashlib.sha256(b).hexdigest()==receipt['archive_sha256'];assert len(b)==receipt['archive_bytes']
with zipfile.ZipFile(io.BytesIO(b)) as z:
 assert z.testzip() is None
 for name in z.namelist():assert '/' not in name and name not in ['.','..']
 z.extractall(R/'market')
manifest=json.loads((R/'remote/tools/l0087/package_manifest.json').read_text());local=R.parent/'l0087/package';assert all(hashlib.sha256((local/n).read_bytes()).hexdigest()==h for n,h in manifest.items());assert (local/'package_manifest.json').read_bytes()==(R/'remote/tools/l0087/package_manifest.json').read_bytes()
print('ARCHIVE_AND_MANIFEST_VERIFIED',len(b),receipt['archive_sha256'],flush=True)
(R/'download_verified.json').write_text(json.dumps({'head':head,'receipt':receipt,'package_matches_prepared':True},indent=2))
