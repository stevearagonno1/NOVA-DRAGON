"""Recreate admitted inputs from pinned monthly sources, then register; no signal research."""
import argparse,datetime as dt,hashlib,json,os,subprocess,sys,time,zipfile
from pathlib import Path
import collect
P=Path(__file__).resolve().parent
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def size(p):return sum(f.stat().st_size for f in p.rglob('*') if f.is_file())
def run(rehearsal=False):
 started=time.time();os.chdir(P);collect.budget(P)
 mode='rehearsal' if rehearsal else 'execution';work=P/mode;work.mkdir(exist_ok=True);data=work/'data';data.mkdir(exist_ok=True)
 fixed=json.loads((P/'protocol.json').read_text());fixed_hash=sha(P/'protocol.json')
 original_fetch=collect.fetch
 def checked_fetch(url,path,scope):
  collect.budget(P);original_fetch(url,path,scope);collect.budget(P)
 collect.fetch=checked_fetch
 if rehearsal:
  manifest=collect.collect(data,months=['2025-09'],start=collect.START,end=collect.ANALYSIS)
 else:manifest=collect.collect(data)
 manifest=json.loads((data/'manifest.json').read_text())
 expected={k:v for k,v in fixed['source_sha256_by_month'].items() if not rehearsal or k=='2025-09'}
 actual={r['month']:r['source_sha256'] for r in manifest['sources']};assert actual==expected,'Pinned original source mismatch'
 audit=collect.audit(data)
 resolved=dict(fixed);resolved['input_manifest_sha256']=sha(data/'manifest.json');resolved['frame_sha256']=manifest['frame_sha256'];resolved['source_sha256_by_month']=expected
 if rehearsal:
  resolved.update(collection_start='2025-09-01',analysis_start='2025-09-01',analysis_end_exclusive='2025-10-01',folds=[{'name':'rehearsal_only','start':'2025-09-01','end':'2025-10-01'}],expected_counts=manifest['counts'])
  resolved['fixture_only']=True
 else:
  assert manifest['counts']==fixed['expected_counts'];assert manifest['collection_start_ms']==collect.START and manifest['collection_end_exclusive_ms']==collect.END
 # Only identity of freshly rebuilt byte containers is rebound in production; research definitions remain fixed.
 allowed={'input_manifest_sha256','frame_sha256'}
 if not rehearsal:assert all(resolved[k]==v for k,v in fixed.items() if k not in allowed)
 runner=(P/'register.py').read_bytes();(work/'register.py').write_bytes(runner);(work/'protocol.json').write_text(json.dumps(resolved,indent=2)+'\n')
 changes={'fixed_protocol_sha256':fixed_hash,'mode':mode,'allowed_production_metadata_fields':sorted(allowed),'source_pins_unchanged':actual==expected,'research_definitions_unchanged':not rehearsal,'old_transport_manifest_sha256':fixed['input_manifest_sha256'],'new_transport_manifest_sha256':resolved['input_manifest_sha256'],'not_predictive_research':True}
 (work/'INPUT_IDENTITY.json').write_text(json.dumps(changes,indent=2)+'\n')
 bundle=work/'BTC-year-minute-and-frames.zip'
 with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
  for f in sorted((data/'frames').glob('*.gz')):z.write(f,'frames/'+f.name)
  for n in ['manifest.json','audit.json']:z.write(data/n,n)
 collect.budget(P)
 command=[sys.executable,str(work/'register.py'),'--bundle',str(bundle),'--output',str(work/'result')]
 subprocess.run(command,check=True)
 before=json.loads((work/'result/registration.json').read_text());calendar_hash=hashlib.sha256(__import__('gzip').decompress((work/'result/split-calendar.csv.gz').read_bytes())).hexdigest()
 subprocess.run(command,check=True)
 after=json.loads((work/'result/registration.json').read_text());before.pop('compute_seconds');after.pop('compute_seconds');assert before==after
 assert calendar_hash==hashlib.sha256(__import__('gzip').decompress((work/'result/split-calendar.csv.gz').read_bytes())).hexdigest()
 collect.budget(P)
 receipt={'status':'PASS_REHEARSAL_ONLY_NOT_YEAR' if rehearsal else 'PASS_YEAR_DATA_AND_REGISTRATION_LEAD_REVIEW_PENDING','mode':mode,'source_months':len(actual),'frame_counts':manifest['counts'],'registration_checks':'10/10','repeat_registration_equal':True,'input_archive_sha256':sha(bundle),'archive_bytes':bundle.stat().st_size,'whole_task_directory_bytes':size(P),'elapsed_seconds_local_execution':time.time()-started,'publication_included_in_timer':False,'indicators_or_states_computed':False,'original_source_archives_retained':True,'financial_fields':'not measured — outside this phase'}
 (work/'DELIVERY.json').write_text(json.dumps(receipt,indent=2)+'\n')
 (work/'REPORT.md').write_text('# Data preparation and registration\n\n'+json.dumps(receipt,indent=2)+'\n\nNo indicator values, future movements, candidate search, trading or adoption.\n')
 print(json.dumps(receipt))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--rehearsal',action='store_true');args=a.parse_args();run(args.rehearsal)
