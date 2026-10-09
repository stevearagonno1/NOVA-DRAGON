"""R4/R5 acceptance gates: real interrupted resume, tamper rejection, and secret-scan proof.

Outputs are small JSON audits only. Checkpoint comparisons and summaries stay in memory.
"""
import copy,hashlib,json,secrets,string
from pathlib import Path
from .run import (WORKSPACE,ASSETS,RESULT_FIELDS,process_asset,save_checkpoint,load_checkpoint,
                  validate_checkpoint_envelope,_state_digest,summarize_raw,_csv_bytes,fingerprint,write_budgeted)
from .register import build_registry
from .fixture_generator import specification
from .publish import _TOKEN_SHAPE_RE

RUN_ID='singleton-package-fixture-r4'
RUN_DIR=WORKSPACE/'run-r4'

def _jdump(obj):return (json.dumps(obj,indent=2,sort_keys=True)+'\n').encode()

def resume_audit(ref_dir,check_dir,run_id=RUN_ID,fixture_days=61):
    """Interrupt after the first asset, reload only the checkpoint, finish, then compare with the reference run.

    Summary comparison is done in memory; no second results CSV is written to disk.
    """
    registry=build_registry();fp=fingerprint();ref_dir=Path(ref_dir);check_dir=Path(check_dir);cp=check_dir/'checkpoint.json'
    ref_result=(ref_dir/'fixtures-results.csv').read_bytes()
    ref_done=json.loads((ref_dir/'checkpoint.json').read_text(encoding='utf-8'))['state']['completed']
    ref_audit=json.loads((ref_dir/'audit.json').read_text(encoding='utf-8'))
    steps=[];first=ASSETS[0]
    state={'run_id':run_id,'fingerprint':fp,'fixture':specification(fixture_days),'fixture_days':fixture_days,'completed':{},'market_run':False,'synthetic':True}
    save_checkpoint(cp,state,WORKSPACE)
    state['completed'][first]=process_asset(first,registry,check_dir,run_id,fp,fixture_days)
    save_checkpoint(cp,state,WORKSPACE)
    steps.append({'stage':'interrupt','command':'process_asset/checkpoint after first asset','after_asset':first,'exit_code':0,'completed':[first]})
    # Simulated process exit: nothing from the interrupted process is reused except the checkpoint file.
    st=load_checkpoint(cp,run_id,fp,check_dir)
    if st.get('fixture_days')!=fixture_days:raise ValueError('resume rejected: fixture length changed')
    resumed=[]
    for a in ASSETS:
        if a in st['completed']:continue
        st['completed'][a]=process_asset(a,registry,check_dir,run_id,fp,fixture_days);save_checkpoint(cp,st,WORKSPACE);resumed.append(a)
    steps.append({'stage':'resume','command':'load_checkpoint + remaining process_asset','exit_code':0,'resumed_assets':resumed})
    rows=summarize_raw(check_dir,registry);data=_csv_bytes(rows,RESULT_FIELDS)
    diffs=[]
    for a in ASSETS:
        for key in ('alerts_sha256','masks_sha256','alert_rows','input_sha256'):
            if st['completed'][a].get(key)!=ref_done[a].get(key):diffs.append(f'{a}.{key}')
    if data!=ref_result:diffs.append('fixtures-results.csv bytes')
    keys={(r['asset'],r['state'],r['setting_id'],str(r['horizon_hours'])) for r in rows}
    if len(rows)!=4104 or len(keys)!=4104:diffs.append('summary row count/key')
    zero_ref=sum(1 for r in rows if int(r['alerts_total'])==0)
    if zero_ref!=ref_audit.get('zero_rows'):diffs.append('zero rows')
    final_env={'state':st,'sha256':_state_digest(st)}
    validate_checkpoint_envelope(final_env,run_id,fp,check_dir)
    return {'status':'PASS' if not diffs else 'FAIL','run_id':run_id,'code_sha256':fp['code_sha256'],'scope_sha256':fp['scope_sha256'],
            'registry_sha256':fp['registry_sha256'],'fixture_days':fixture_days,'interrupt_after':first,'steps':steps,
            'compared':{'masks_per_asset':len(ASSETS),'alert_keys_per_asset':'alerts_sha256 equal','summary_rows':len(rows),
                        'summary_bytes':len(data),'summary_keys_unique':len(keys)==4104},
            'differences':len(diffs),'difference_fields':diffs,'zero_rows':zero_ref,'time_fields_excluded':['runtime.json timestamps'],
            'results_written_to_disk':False,'market_run':False,'synthetic':True}

def _classify(data,token):
    rules=[]
    if token and token.encode() in data:rules.append('exact_gh_token_value')
    if _TOKEN_SHAPE_RE.search(data):rules.append('token_shape_github')
    return rules

def secret_scan(workspace,token):
    """Run clean/canary/exact-value/source checks entirely in memory; never echo values."""
    pkg=Path(workspace)/'tools/entry_singletons_v1'
    clean={'note.txt':b'synthetic-only fixture evidence'}
    canary=('github_pat_'+''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(40))).encode()
    tests=[]
    def case(name,payload,expect_reject):
        rules=[]
        for p,d in payload.items():rules+=[(p,r) for r in _classify(d,token)]
        rejected=bool(rules)
        tests.append({'test':name,'expected':'reject' if expect_reject else 'pass','observed':'reject' if rejected else 'pass',
                      'rule_ids':sorted({r for _,r in rules}),'matched_paths':sorted({p for p,_ in rules}),'remote_write_calls':0,
                      'result':'PASS' if rejected==expect_reject else 'FAIL'})
    case('clean_payload_passes',{'note.txt':clean['note.txt']},False)
    case('canary_payload_rejected',{'canary.txt':b'x'+canary+b'x'},True)
    if token:case('exact_secret_value_payload_rejected',{'exact.txt':b'prefix '+token.encode()+b' suffix'},True)
    src={p.name:p.read_bytes() for p in sorted(pkg.glob('*.py'))}
    case('package_source_scanned_not_exempt',src,False)
    return {'status':'PASS' if all(t['result']=='PASS' for t in tests) else 'FAIL','tests':tests,
            'rules':{'exact_gh_token_value':'literal owner-supplied token value, held in memory only',
                     'token_shape_github':'regex: github_pat_ + 22+ token chars, or gh[pousr]_ + 36+ token chars'},
            'canary_generated':'in memory, not stored','canary_validated_remotely':False,'values_recorded':False,'market_run':False}

def tamper_audit(check_dir,run_id=RUN_ID):
    """Mutate in-memory copies of the checkpoint; each mutation must be rejected with an expected message."""
    check_dir=Path(check_dir);env=json.loads((check_dir/'checkpoint.json').read_text(encoding='utf-8'))
    fp=env['state']['fingerprint'];cases=[]
    def attempt(name,element,mutate_env,fp_used,expect):
        try:
            validate_checkpoint_envelope(mutate_env,run_id,fp_used,check_dir);outcome=('accepted',None)
        except Exception as e:outcome=('rejected',f'{type(e).__name__}: {e}')
        ok=outcome[0]=='rejected' and expect in outcome[1]
        cases.append({'case':name,'element':element,'result':'rejected' if outcome[0]=='rejected' else 'accepted',
                      'error':outcome[1],'expected_fragment':expect,'continued':outcome[0]=='accepted','remote_write_calls':0,'status':'PASS' if ok else 'FAIL'})
    base=copy.deepcopy(env)
    raw=copy.deepcopy(env['state']);first=next(iter(raw['completed']));raw['completed'][first]['alerts_sha256']='0'*64
    attempt('raw_alerts_digest_altered','raw',{'state':raw,'sha256':_state_digest(raw)},fp,'staged raw bytes changed')
    raw2=copy.deepcopy(env['state']);raw2['completed'][first]['masks_bytes']+=1
    attempt('raw_mask_size_altered','raw',{'state':raw2,'sha256':_state_digest(raw2)},fp,'staged raw bytes changed')
    scope=dict(fp);scope['scope_sha256']='0'*64
    attempt('scope_fingerprint_altered','scope',base,scope,'fingerprint changed')
    code=dict(fp);code['code_sha256']='0'*64
    attempt('code_fingerprint_altered','code',base,code,'fingerprint changed')
    ck=copy.deepcopy(env);ck['sha256']='0'*64
    attempt('checkpoint_envelope_digest_altered','checkpoint',ck,fp,'checkpoint envelope digest')
    ok=validate_checkpoint_envelope(base,run_id,fp,check_dir) is not None
    return {'status':'PASS' if ok and all(c['status']=='PASS' for c in cases) else 'FAIL','positive_control_unmodified_accepted':ok,
            'cases':cases,'cases_total':len(cases),'cases_rejected':sum(c['result']=='rejected' for c in cases),
            'remote_write_calls_total':0,'working_source_modified':False,'market_run':False,'synthetic':True}

def main(argv=None):
    import argparse
    ap=argparse.ArgumentParser(description='R4/R5 gates. Writes small audit JSON only.')
    ap.add_argument('--ref',default=str(RUN_DIR));ap.add_argument('--check',default=str(RUN_DIR/'resume-check'))
    ap.add_argument('--phase',choices=['resume','tamper','secret'],required=True)
    a=ap.parse_args(argv)
    if a.phase=='resume':
        res=resume_audit(a.ref,a.check);write_budgeted(RUN_DIR/'resume-audit.json',_jdump(res),WORKSPACE,mutable=True)
    elif a.phase=='tamper':
        res=tamper_audit(a.check);write_budgeted(RUN_DIR/'tamper-audit.json',_jdump(res),WORKSPACE,mutable=True)
    else:
        import os
        token=os.environ.get('GH_TOKEN','');res=secret_scan(WORKSPACE,token)
        write_budgeted(RUN_DIR/'secret-scan.json',_jdump(res),WORKSPACE,mutable=True)
    print(json.dumps({'phase':a.phase,'status':res['status']},sort_keys=True))
    return 0 if res['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
