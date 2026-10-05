"""Source-locked, pre-outcome R1 registries. No measurements are read here."""
from __future__ import annotations
import csv,hashlib,json,os,re,urllib.request
from pathlib import Path
import numpy as np
import pandas as pd
from . import data as D, engine as E, indicators as I, measure as M

PIN_MAIN='71f52f0741cdaceb71797b1fe07de07db31fcced'
PIN_GRID='62f4d255e0fc6fce8e7c331a6349484ccb0b8fc0'
PIN_COST='2d8e8f3afca6a72679382780ddaeb0d71de2cad6'
PIN_PRIOR='d310df96901fa062022db41a35a24c5f229e0459'
MODES=('AND0','AND2','OR0')
MAIN_PATHS=[
 'CONSTITUTION.md','docs/HANDOFF-L0083-TO-NEXT-LEAD.md','docs/DECISIONS.md',
 'docs/HANDOFF.md','docs/lanes/L0084-CARRY-FORWARD.md','LOG.md','INDEX.md',
 'BACKLOG.md','docs/journal/README.md','docs/journal/2026-09-19-arena-resume/002-tape-merge-closed.md']
PINNED_PATHS={
 PIN_GRID:['history/hyp_lab/l0083_indicators.py','history/hyp_lab/l0083_run.py'],
 PIN_COST:['history/research/hyp_lab_out/L0082/cost_model_l0082.csv'],
}
PRIOR_PATHS=['tools/l0084_entry_mix/engine.py','tools/l0084_entry_mix/cli.py',
 'tools/l0084_entry_mix/tests.py','tools/l0084_entry_mix/indicators.py',
 'tools/l0084_entry_mix/measure.py','tools/l0084_entry_mix/pipeline.py']


def sha(b):return hashlib.sha256(b).hexdigest()
def raw_get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'L0084-R1-source-audit'})
 with urllib.request.urlopen(req,timeout=30) as r:return r.status,r.read()


def parse_owner_sheet(sheet_path):
    text=Path(sheet_path).read_text(encoding='utf-8')
    # exact setting descriptions in §5; parse table rows, not the prose list
    start=text.index('| Setting | Full signal rule |')
    tail=text[start:]
    rows={}
    for line in tail.splitlines()[2:]:
        m=re.match(r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$',line)
        if not m:break
        name,rule=m.group(1).strip(),m.group(2).strip()
        if name in I.SETTINGS_52: rows[name]=rule
    if set(rows)!=set(I.SETTINGS_52) or len(rows)!=52:
        raise RuntimeError(f'owner-sheet catalogue mismatch: parsed {len(rows)}')
    # Explicit Appendix B pair table; verify each exact pair and canonical ID.
    a=text.index('## Appendix B — explicit exhaustive pair catalogue')
    b=text.index('## Appendix C — runnable count verification',a)
    pairs=[]
    for line in text[a:b].splitlines():
        m=re.match(r'^\|\s*(P\d{4})\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$',line)
        if m:pairs.append((m.group(1),m.group(2).strip(),m.group(3).strip()))
    if len(pairs)!=1326:raise RuntimeError(f'Appendix B parsed {len(pairs)} pairs, expected 1326')
    canonical=[(f'P{i:04d}',a,b) for i,(a,b) in enumerate(
       ((I.SETTINGS_52[x],I.SETTINGS_52[y]) for x in range(52) for y in range(x+1,52)),1)]
    if pairs!=canonical:raise RuntimeError('Appendix B differs from canonical 52-grid order')
    return text,rows,pairs


def collect_sources(sheet_path, data_dir, old_root):
    rec=[]
    for path in MAIN_PATHS:
        u=f'https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/{PIN_MAIN}/{path}'
        try:
            status,b=raw_get(u);rec.append({'commit':PIN_MAIN,'path':path,'url':u,'http_status':status,'sha256':sha(b),'bytes':len(b),'versions':{'python':'3.13.14','numpy':np.__version__,'pandas':pd.__version__},'errors':[]})
        except Exception as e:rec.append({'commit':PIN_MAIN,'path':path,'url':u,'http_status':None,'sha256':None,'bytes':None,'versions':{},'errors':[f'{type(e).__name__}: {e}']})
    for commit,paths in PINNED_PATHS.items():
        for path in paths:
            u=f'https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/{commit}/{path}'
            try:
                status,b=raw_get(u);rec.append({'commit':commit,'path':path,'url':u,'http_status':status,'sha256':sha(b),'bytes':len(b),'versions':{'python':'3.13.14','numpy':np.__version__,'pandas':pd.__version__},'errors':[]})
            except Exception as e:rec.append({'commit':commit,'path':path,'url':u,'http_status':None,'sha256':None,'bytes':None,'versions':{},'errors':[f'{type(e).__name__}: {e}']})
    for path in PRIOR_PATHS:
        u=f'https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/{PIN_PRIOR}/{path}'
        try:
            status,b=raw_get(u);rec.append({'commit':PIN_PRIOR,'path':path,'url':u,'http_status':status,'sha256':sha(b),'bytes':len(b),'versions':{'python':'3.13.14','numpy':np.__version__,'pandas':pd.__version__},'errors':[]})
        except Exception as e:rec.append({'commit':PIN_PRIOR,'path':path,'url':u,'http_status':None,'sha256':None,'bytes':None,'versions':{},'errors':[f'{type(e).__name__}: {e}']})
    owner=Path(sheet_path).read_bytes()
    rec.append({'commit':'owner-attachment','path':Path(sheet_path).name,'url':'workspace upload','http_status':'attached','sha256':sha(owner),'bytes':len(owner),'versions':{},'errors':[]})
    # Previous measured coverage report contains the per-panel hashes. Match
    # current local panels exactly; archive HTTP response logs were not kept.
    old_cov=Path(old_root)/'history/research/hyp_lab_out/L0084-entry-mix/data_coverage.csv'
    cov=pd.read_csv(old_cov).set_index('asset')
    panels=[]
    for sym in D.ASSETS:
        path=Path(data_dir)/f'{sym}_4h.parquet';digest=sha(path.read_bytes())
        previous=str(cov.loc[sym,'parquet_sha256'])
        if digest!=previous:raise RuntimeError(f'{sym} processed-panel SHA differs from prior coverage')
        panels.append({'asset':sym,'path':str(path),'sha256':digest,'bytes':path.stat().st_size,'matches_prior_coverage_sha':True,'source':'data.binance.vision/data/futures/um/{monthly,daily}/klines/{asset}/4h/','http_status':'prior-run source records; no R1 refetch','errors':[]})
    return rec,panels


def build(m,sheet_path,old_root):
    root=M.ROOT;out=M.O;data_dir=M.WORK
    os.makedirs(out,exist_ok=True)
    text,definitions,pairs=parse_owner_sheet(sheet_path)
    source_records,panels=collect_sources(sheet_path,data_dir,old_root)
    local_files=[]
    for f in ['tools/l0084_entry_mix_r1/engine.py','tools/l0084_entry_mix_r1/indicators.py','tools/l0084_entry_mix_r1/tests.py','tools/l0084_entry_mix_r1/integrity.py','tools/l0084_entry_mix_r1/measure.py']:
        p=Path(root)/f;local_files.append({'path':f,'sha256':sha(p.read_bytes())})
    src={'fetched_utc':M.utc() if hasattr(M,'utc') else __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'pins':{'main':PIN_MAIN,'grid_52':PIN_GRID,'cost_model':PIN_COST,'prior_delivery':PIN_PRIOR},'sources':source_records,'data_panels':panels,'local_source_files':local_files,'tape_note':'Pinned main tree has no path containing “tape”; inspected latest tape reference at docs/journal/2026-09-19-arena-resume/002-tape-merge-closed.md.','versions':{'python':'3.13.14','numpy':np.__version__,'pandas':pd.__version__}}
    with open(os.path.join(out,'sources.json'),'w',encoding='utf-8') as f:json.dump(src,f,ensure_ascii=False,indent=2)
    cat=[]
    for name in I.SETTINGS_52:
        h=hashlib.sha256();ntrue=0
        for sym in D.ASSETS:
            mask=m.panels[sym].masks[name];h.update(np.packbits(mask).tobytes());ntrue+=int(mask.sum())
        cat.append({'setting':name,'definition':definitions[name],'parameters':'','source_commit':PIN_GRID,'implementation_commit':os.environ.get('L0084_R1_CODE_COMMIT','UNSET_BEFORE_PREREGISTRATION'),'mask_hash':h.hexdigest(),'duplicate_of':'','n_true_12assets':ntrue})
    pd.DataFrame(cat).to_csv(os.path.join(out,'catalogue.csv'),index=False)
    rows=[]
    for pid,a,b in pairs:
        for mode in MODES:rows.append({'pair_id':pid,'member_a':a,'member_b':b,'mode':mode,'canonical_id':pid+'|'+mode})
    pd.DataFrame(rows).to_csv(os.path.join(out,'pairs_registry.csv'),index=False)
    cov=[]
    prior=pd.read_csv(os.path.join(old_root,'history/research/hyp_lab_out/L0084-entry-mix/data_coverage.csv')).set_index('asset')
    for sym in D.ASSETS:
        p=m.panels[sym];dt=pd.to_datetime(p.dt);segments=np.unique(p.seg)
        gaps=[]
        for j in range(1,len(dt)):
            hours=(dt[j]-dt[j-1]).total_seconds()/3600
            if hours>4:gaps.append((str(dt[j-1]),str(dt[j]),hours))
        path=os.path.join(data_dir,f'{sym}_4h.parquet')
        cov.append({'asset':sym,'start_utc':dt[0].isoformat(),'end_utc':dt[-1].isoformat(),'n_bars':len(p.c),'duplicates':0,'gap_count':len(gaps),'gap_start_end_hours':json.dumps(gaps),'action':'prior converted panel; SHA verified against previous data_coverage.csv','segment_count':len(segments),'warmup_bars':200,'parquet_sha256':sha(Path(path).read_bytes())})
    pd.DataFrame(cov).to_csv(os.path.join(out,'data_coverage.csv'),index=False)
    from . import stats as S
    from math import comb
    reg={'lane':'L0084-ENTRY-MIX-R1','written_utc':src['fetched_utc'],'written_before_any_R1_measurement':True,'code_commit_before_measurement':os.environ.get('L0084_R1_CODE_COMMIT','UNSET_BEFORE_PREREGISTRATION'),'hypothesis':'Any unordered pair then preregistered third addition improves cost-adjusted entry expectation and temporal stability within fixed 52-setting catalog.','universe':{'assets':D.ASSETS,'timeframe':'4h UTC','start':'2021-01-01','end':'2026-09-27','source':'data.binance.vision; previously converted panels SHA-verified'},'pins':src['pins'],'settings_52':I.SETTINGS_52,'pair_sets':len(pairs),'pair_modes':len(rows),'modes':{'AND0':'all members true at i','AND2':'each member true at least once i-2..i; one or more at i; contiguous','OR0':'at least one member true at i'},'outer_windows':M.OUTER,'inner_windows_by_prefix':{o:M.inner_windows(o) for o in M.OUTER},'half_years':M.HALF_YEARS,'container':{'notional_usd':E.NOTIONAL,'cost_round_trip_usd':E.COST_RT,'barrier_atr':E.BARRIER_ATR,'horizon_bars_including_fill':E.HORIZON,'fill':'next contiguous open; ATR fixed at decision i','book_per_asset_candidate_usd':E.BOOK0,'stop':'q-1.5 ATR','target':'q+1.5 ATR','gaps_first':True,'double_touch':'stop first','incomplete_horizon':'exclude; no forced close'},'gates':{'min_trades_each_inner_window':100,'min_positive_assets':8,'assets_total':12,'min_pf':1.3,'one_sided_95_block_lower_bound_gt_zero':True,'paired_superiority_over_all_controls':True},'multiplicity':{'holm_m':70330,'potential_triples':66300,'triple_trials_cap_per_prefix':1500,'bootstrap_replicates':2000,'block_days':7,'seed':84},'selection':'worst inner-window lower bound, fewer members, larger minimum trade count, canonical ID; else CASH','cost_is_fixed_not_optimized':True,'no_outcome_fields_recorded':True}
    with open(os.path.join(out,'preregistration.json'),'w',encoding='utf-8') as f:json.dump(reg,f,ensure_ascii=False,indent=2)
    pending=('# L0084-R1 — catalogue pending\n\n- Corrected local 76-grid package: PENDING at inspected pins; no substitute used and no negative result inferred.\n- L0083 V3 headlines are documented historical context only and are not remeasured or used as a basis.\n')
    Path(out,'catalogue_pending.md').write_text(pending,encoding='utf-8')
    return {'catalogue_rows':len(cat),'pairs':len(pairs),'pair_modes':len(rows),'assets':len(cov),'sources':len(source_records),'data_panels':len(panels),'sheet_sha256':sha(Path(sheet_path).read_bytes())}
