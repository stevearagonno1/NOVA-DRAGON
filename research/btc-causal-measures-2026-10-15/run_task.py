import argparse,base64,json,os,time
from pathlib import Path
import source_collect as src
from features import acquire,compute,ms,sha
from audit_features import audit
from api import API,preflight,REPO
P=Path(__file__).resolve().parent
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
def run(args):
 started=time.time();os.chdir(P);spec=json.loads((P/'protocol.json').read_text());mode='rehearsal' if args.rehearsal else 'execution';out=P/mode;out.mkdir(exist_ok=True);api=None
 if args.publish:api=API(os.environ.get('GH_TOKEN',''));preflight(api)
 if not args.rehearsal:assert args.publish,'Production must preflight and publish, not stop locally'
 inputs=args.inputs.resolve() if args.inputs else acquire(P,spec)
 input_bytes=sum(f.stat().st_size for f in inputs.glob('*.gz'))
 src.budget(P)
 begin=ms('2025-09-30') if args.rehearsal else ms(spec['analysis_start']);end=ms('2025-10-01') if args.rehearsal else ms(spec['analysis_end_exclusive'])
 manifest=compute(inputs,out,spec,begin,end);checked=audit(inputs,out,manifest)
 count=sum(manifest['counts'].values());assert count==(3696 if args.rehearsal else 676368)
 expected_size=count*120;actual_size=sum((out/x['file']).stat().st_size for x in manifest['files']);assert actual_size==expected_size
 total=src.size(P)+(0 if inputs.is_relative_to(P) else input_bytes);assert total<=125000000
 receipt={'status':'PASS_REHEARSAL_ONLY_NOT_YEAR' if args.rehearsal else 'PASS_FIXED_CAUSAL_MEASUREMENTS_LEAD_REVIEW_PENDING','native_records_with_one_day_history':count,'analysis_native_records':(1848 if args.rehearsal else 674520),'fields_per_record':14,'timeframe_count':4,'trajectory_positions_read_lazily':168,'files':len(manifest['files']),'binary_bytes':actual_size,'task_and_external_input_bytes':total,'local_compute_seconds':time.time()-started,'whole_task_duration_including_publication':'not measured yet','audit':checked['status'],'future_labels_or_state_search':False,'prediction_and_profit':'not measured','source_commit':args.source_commit}
 (out/'RESULT.json').write_text(json.dumps(receipt,indent=2)+'\n');(out/'REPORT.md').write_text('# Fixed causal measurements\n\nIntegrity '+checked['status']+'; no predictive or financial result.\n\n'+json.dumps(receipt,indent=2)+'\n')
 if args.publish:
  branch='agent/btc-causal-measures-readiness-2026-10-15' if args.rehearsal else 'agent/btc-causal-measures-execution-2026-10-15';base='research/btc-causal-measures-2026-10-15/'+mode+'/'
  files={base/f.name:f for f in out.iterdir() if f.is_file() and f.name not in ['DELIVERY.json','LOCAL-RECEIPT.json','LOG_APPEND.txt','TICK.md']}
  for n in ['features.py','audit_features.py','source_collect.py','api.py','run_task.py','protocol.json']:files['research/btc-causal-measures-2026-10-15/code/'+n]=P/n
  source_tree=api.call('GET',f'/repos/{REPO}/git/commits/{args.source_commit}')['tree']['sha'];root=api.call('GET',f'/repos/{REPO}/git/trees/{source_tree}');entry=next(x for x in root['tree'] if x['path']=='LOG.md');old=base64.b64decode(api.call('GET',f'/repos/{REPO}/git/blobs/{entry["sha"]}')['content'])
  (out/'LOG_APPEND.txt').write_bytes(old+b'\n\n## Fixed causal measurements -2026-10-15\nCalculated14fixed fields at4native frames; no state search or predictive/financial adoption. See result and audit in work branch.\n');files['LOG.md']=out/'LOG_APPEND.txt'
  (out/'TICK.md').write_text('Decision: fixed causal measurement calculation only.\nExecution: fixed parameters,closed frames,numeric and timing audit.\nProduced: monthly native feature records and reports; no future outcomes.\nNext: Lead independent review before any recurring-state discovery.\n');files['docs/journal/2026-10-15-btc-registration-from-repo/'+('006-feature-rehearsal.md' if args.rehearsal else '006-causal-measures-calculated.md')]=out/'TICK.md'
  result=publish(api,branch,args.source_commit,files);receipt.update(publication=result,whole_task_duration_including_publication=time.time()-started)
  (out/'DELIVERY.json').write_text(json.dumps(receipt,indent=2)+'\n')
  final=publish(api,branch,result['commit'],{base+'DELIVERY.json':out/'DELIVERY.json'});receipt['receipt_commit']=final['commit']
 (out/'LOCAL-RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--rehearsal',action='store_true');p.add_argument('--inputs',type=Path);p.add_argument('--publish',action='store_true');p.add_argument('--source-commit',required=True);args=p.parse_args();assert len(args.source_commit)==40 and all(c in '0123456789abcdef' for c in args.source_commit);run(args)
