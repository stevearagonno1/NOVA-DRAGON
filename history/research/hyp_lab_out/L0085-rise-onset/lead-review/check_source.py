from pathlib import Path
import json,urllib.request,hashlib,concurrent.futures
R=Path(__file__).resolve().parent;m=json.load(open(R/'package_manifest.json'));head='d1fe9978bee6bc7e3478f53d07633f9fabd198cf'
def verify(item):
 name,h=item
 for attempt in range(3):
  try:b=urllib.request.urlopen('https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/'+head+'/tools/l0085/'+name,timeout=40).read();break
  except OSError:
   if attempt==2:raise
 assert hashlib.sha256(b).hexdigest()==h,name
 return name
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:files=list(ex.map(verify,m.items()))
(R/'source_check.json').write_text(json.dumps({'status':'PASS','head':head,'files':files},indent=2));print('SOURCE_AT_DELIVERY_VERIFIED',len(files),flush=True)
