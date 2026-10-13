"""Registration only: audit immutable input, emit split masks; no market scoring."""
import argparse,csv,datetime as dt,gzip,hashlib,io,json,time,zipfile
from pathlib import Path
def ms(s):return int(dt.datetime.fromisoformat(s).replace(tzinfo=dt.timezone.utc).timestamp()*1000)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def run(bundle,output):
 started=time.time();spec=json.loads(Path(__file__).with_name('protocol.json').read_text());assert sha(bundle)==spec['input_bundle_sha256'],'Input hash mismatch'
 assert bundle.stat().st_size==spec['input_bundle_bytes']
 output.mkdir(parents=True,exist_ok=True)
 checks={};receipts={};folds=[(f['name'],ms(f['start']),ms(f['end'])) for f in spec['folds']]
 counts={name:{'feature_anchor_rows':0,'eligible_all_9_windows':0,'excluded_240min_boundary_rows':0,'eligible_by_window':{str(h):0 for h in spec['future_windows_minutes']}} for name,_,_ in folds}
 start,end=ms(spec['analysis_start']),ms(spec['analysis_end_exclusive']);hmax=spec['maximum_future_window_minutes']*60000
 with zipfile.ZipFile(bundle) as z:
  manifest=json.loads(z.read('manifest.json'));checks['manifest_expected_counts']=manifest['counts']==spec['expected_counts'];assert checks['manifest_expected_counts']
  for frame in spec['frames_minutes']:
   name=f'frames/BTCUSDT-{frame}m.csv.gz';h=hashlib.sha256()
   with z.open(name) as f:
    for b in iter(lambda:f.read(1048576),b''):h.update(b)
   assert h.hexdigest()==manifest['frame_sha256'][str(frame)]
   prev=None;n=0;first=None;last=None
   with z.open(name) as raw,gzip.GzipFile(fileobj=raw) as gf:
    rd=csv.reader(io.TextIOWrapper(gf));header=next(rd);assert len(header)==12
    sink=gzip.open(output/'split-calendar.csv.gz','wt',newline='') if frame==1 else None
    try:
     writer=csv.writer(sink) if sink else None
     if writer:writer.writerow(['anchor_open_ms','decision_ms','split','eligible_all_9_windows','boundary_excluded','split_end_exclusive_ms'])
     for row in rd:
      assert len(row)==12;t=int(row[0]);available=t+frame*60000;assert int(row[6])==available-1
      assert prev is None or t-prev==frame*60000;assert t%(frame*60000)==0
      if first is None:first=t
      last=t;prev=t;n+=1
      if writer and start<=t<end:
       fold=next((x for x in folds if x[1]<=t<x[2]),None);assert fold
       label,_,stop=fold;eligible=available+hmax<=stop;c=counts[label];c['feature_anchor_rows']+=1;c['eligible_all_9_windows']+=int(eligible);c['excluded_240min_boundary_rows']+=int(not eligible)
       for horizon in spec['future_windows_minutes']:c['eligible_by_window'][str(horizon)]+=int(available+horizon*60000<=stop)
       writer.writerow([t,available,label,int(eligible),int(not eligible),stop])
    finally:
     if sink:sink.close()
   assert n==spec['expected_counts'][str(frame)];assert first==ms(spec['collection_start']) and last+frame*60000==end
   receipts[str(frame)]={'rows':n,'sha256':h.hexdigest(),'first_open_ms':first,'end_exclusive_ms':last+frame*60000,'columns':header}
 assert sum(x['feature_anchor_rows'] for x in counts.values())==525600
 assert spec['features_count']==len(spec['features_per_frame'])*len(spec['frames_minutes'])==56
 assert spec['trajectory_positions_count']==spec['features_count']*len(spec['past_snapshot_offsets_minutes'])==168
 assert all(c['excluded_240min_boundary_rows']==240 for c in counts.values())
 checks.update({'input_sha256':True,'all_four_frame_sha256':True,'exact_calendars_and_counts':True,'no_gaps_or_duplicate_open_times':True,'closed_time_semantics':True,'feature_positions_count':True,'all_analysis_anchors_partitioned_once':True,'240min_boundary_masks':True,'no_feature_or_future_outcome_computed':True})
 result={'status':'PASS_PROTOCOL_REGISTRATION_ONLY','checks':checks,'passed':sum(checks.values()),'total':len(checks),'splits':counts,'inputs':receipts,'spec_sha256':sha(Path(__file__).with_name('protocol.json')),'compute_seconds':time.time()-started,'no_predictive_result':True,'historically_blind':False}
 for name,obj in [('registration.json',result),('frozen-protocol.json',spec)]: (output/name).write_text(json.dumps(obj,indent=2)+'\n')
 (output/'REPORT.md').write_text('# Protocol registration\n\nChecks '+str(result['passed'])+'/'+str(result['total'])+'; no indicators, state search, future labels or financial performance computed.\n\n'+json.dumps(counts,indent=2)+'\n')
 print(json.dumps({'status':result['status'],'checks':str(result['passed'])+'/'+str(result['total']),'splits':counts,'compute_seconds':result['compute_seconds']}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.bundle,a.output)
