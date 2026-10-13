"""Package admitted frame data and metadata; retain source ZIPs locally, publish checksum URLs."""
import argparse,json,zipfile,time
from pathlib import Path
import collect
p=argparse.ArgumentParser();p.add_argument('--scope',type=Path,default=Path('execution'));p.add_argument('--output',type=Path,default=Path('BTC-year-minute-and-frames.zip'));p.add_argument('--allow-rehearsal',action='store_true');a=p.parse_args();s=a.scope
m=json.loads((s/'manifest.json').read_text());audit=json.loads((s/'audit.json').read_text());assert audit['status']=='PASS_AUTOMATED_DATA_CHECKS_LEAD_REVIEW_PENDING';assert not m.get('rehearsal_only') or a.allow_rehearsal, 'Do not present rehearsal as year data'
collect.budget(Path.cwd())
with zipfile.ZipFile(a.output,'w',zipfile.ZIP_STORED) as z:
 for f in sorted((s/'frames').glob('*.gz')):z.write(f,'frames/'+f.name)
 for name in ['manifest.json','audit.json','execution-timing.json']:
  if (s/name).exists():z.write(s/name,name)
 for f in sorted((s/'raw').glob('*.CHECKSUM')):z.write(f,'source-checksums/'+f.name)
 for name in ['collect.py','pack_delivery.py','EXECUTOR_PAPER.md']:z.write(Path(__file__).parent/name,'code/'+name)
collect.budget(Path.cwd());receipt={'status':'DATA_COLLECTED_LEAD_REVIEW_PENDING','artifact':str(a.output.resolve()),'artifact_sha256':collect.sha(a.output),'artifact_bytes':a.output.stat().st_size,'cwd_bytes':collect.size(Path.cwd()),'source_raw_archives_retained':True,'raw_source_urls_in_manifest':True,'frames_in_artifact':[1,5,15,60],'indicators_and_states_measured':False}
(s/'delivery.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
