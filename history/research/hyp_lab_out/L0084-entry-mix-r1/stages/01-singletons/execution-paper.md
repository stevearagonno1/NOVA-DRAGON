# L0084-R1 — المرحلة الأولى فقط: إشارات المؤشرات منفردة — الإصدار 2

**تصحيح تجهيز البيئة:** أبلغ الوكيل عن `ModuleNotFoundError: No module named 'pyarrow'` قبل قياس السوق. كان منع إعادة التثبيت خطأ في الورقة. هذا الإصدار يجيز ويعدّ تثبيت الاعتماديات المفقودة خارج مساحة العمل، ويعيد التحقق منها في كل جلسة جديدة. كود البحث ونطاق المرحلة والفرع ومعرّف التشغيل لم تتغير.

هذه ورقة واحدة لمرحلة واحدة. تقيس الإعدادات الـ52 الحالية كلًّا على حدة، مقابل الدخول دون إشارة، ثم تنتهي. لا تجمع مؤشرين ولا تبدأ ثلاثيات. أنا أراجع الأدلة وأكتب التقرير وأحدد المرحلة التالية.

**هذه الورقة تحلّ محل أمر التشغيل الشامل السابق، ولا تلغي نتائجه الجزئية أو تحذفها.** لا تشغّل الأمر القديم معها. اكتمال هذه المرحلة ليس اكتمال L0084 كله، وليس توصية بتداول أي مؤشر.

## 1. Binding assignment

Execute the prepared long stage only. Do not develop, repair, redesign or modify any code. Setup below only materializes the Lead's already prepared files. Do not run the old `cli measure`: it automatically proceeds to pairs and triples.

Question: what is the measured historical behaviour of each locked singleton signal, separately, after costs against its contemporaneous no-signal book?
Why now: the owner requested separate stages after the all-stage run encountered GitHub API limits. No hypothesis of a profitable singleton is asserted. Historical results are descriptive, not new blind evidence.

The executor already reported cancellation returned `not_found` and confirmed no R1/Stage1 process was active. Treat that combination as quiescent, not a new blocker; recheck only if a new process has started. Before starting, cancel your previously scheduled retry `r1-measurement-retry-after-rate--74824206` using the scheduling capability that created it, verify cancellation, and verify that its old measurement process is no longer writing. Preserve its run `r1-20261005T145115Z` and all remote/local evidence; no deletion or main write. If you cannot verify quiescence, report the actual obstacle and do not run competing publishers. No separate paper is needed for routine progress within this stage.

## 2. Pinned sources and destination

| Item | Identifier |
|---|---|
| Official constitution in main | `8e966404e77a97cd32cd19b7b574b55809e743ab` |
| Prior R1 engine/readiness code | `8a7c81fd91f1984d799c13f7484f89a43712c22d` |
| Retained partial R1 snapshot | `f66ce8b411f0e226ab3203dc37af6729b632960d` |
| Prepared stage-1 source and fixed scope | `005e9eed558542ce6f0468ecd6786dc71d3dce57` |
| Tested paced upload and immutable readback | `f313674937d7d3f764bd5a7cda6cd5be82d89561` |
| Stage work branch | `agent/l0084-r1-stage1-2026-10-05` |
| New stage run ID | `stage1-singletons-v1` |
| Stage manifest/audit/delivery root | `history/research/hyp_lab_out/L0084-entry-mix-r1/stages/01-singletons/` |
| Full raw trades | `history/research/hyp_lab_out/L0084-entry-mix-r1/trades/run=stage1-singletons-v1/` |
| Coverage index | `history/research/hyp_lab_out/L0084-entry-mix-r1/measurement_index/run=stage1-singletons-v1/` |

The new work branch already exists. Do not create it from scratch, overwrite it, switch to main, open a PR or merge. The prepared stage source hashes are in `scope.json`; engine/indicator/writer/statistics files inherited from the partial snapshot were verified by Git blob SHA and remain unchanged. Only the stage-specific entry point and its tests were added.

## 3. What is verified, and what is not

Lead executed the stage's actual synthetic CLI: **636 candidate-window groups**, all 52 settings, all 12 assets and all 12 half-years, with 720 synthetic trades and 600 zero-trade groups. Full independent raw execution rebuilding, completed-run resume, interruption/resume and rejection of altered evidence passed. **36 existing/new short tests passed**. A virtual-clock test checked 1,000 write/read cycles for pacing; cached immutable reads checked blob SHA and rejected changed bytes.

Lead also ran the actual paced GitHub publication route on the named branch with a non-financial artifact, LOG/tick recording and immutable readback. This is an actual upload check, not a market result or an assurance against all future platform failures.

Lead test runtime: Python 3.12.14, NumPy 2.3.5, Pandas 2.2.3, SciPy 1.17.0, PyArrow 25.0.1. The previous executor readiness reported Python 3.13.14/SciPy 1.17.1 and the same NumPy/Pandas/PyArrow; this report is not a fresh runtime measurement. Run the prepared short synthetic command below once in the existing executor runtime before the long stage; dependency installation through the exact prepared bootstrap in §8 is now explicitly authorised outside `/home/user`; do not repair research code or install packages inside the workspace.

Market stage-1 outcomes: **NOT RUN by Lead**. Wall-clock duration and full-run peak storage/memory: **not measured**. Current executor free space is checked at admission; its earlier 121,423,124-byte peak is historical evidence only.

## 4. Data, scope, baseline and chronology

Read the 12 immutable converted panels already uploaded in R1, one asset at a time into memory, verified against bytes/SHA256 in scope.json; no downloads of original market archives and no second local panel copy.

Assets: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT, ADAUSDT, DOGEUSDT, AVAXUSDT, LINKUSDT, DOTUSDT, LTCUSDT, ATOMUSDT. Data source: Binance futures/UM public archive candles used as a historical research proxy; this is no permission for futures or leverage. Timeframe 4h UTC; dates 2021-01-01 through 2026-09-27.

Windows: 2021H1, 2021H2, 2022H1, 2022H2, 2023H1, 2023H2, 2024H1, 2024H2, 2025H1, 2025H2, 2026H1, 2026H2p. The last is partial: 2026-07-01 through 2026-09-27. Preserve the pinned implementation's exact window endpoints: the upper search boundary is 00:00 UTC on each listed final date (the remaining five 4h candles of that final date are excluded), not an unverified claim of inclusion through 23:59:59. Record this endpoint limitation in the Lead report; no redefining windows during execution. Reset paper books for every asset/candidate/window. Require the entire 18-bar signal-to-exit horizon within the window and contiguous segment, with 18-bar start embargo.

52 singleton candidates × 12 windows = 624 groups, plus 12 no-signal baseline groups = **636**. With 12 assets, there are **7,632 asset/window groups including baseline**, including zero-trade groups. The same OHLC, segment integrity, input hashes and full asset universe remain binding. Never drop an asset, window, setting or zero group.

The baseline accepts each eligible decision bar without an indicator, uses the same book, eligibility, fill, exit, cost and one-position-per-asset rules. Report win rate among decided target/stop trades separately from timeout share; dollar expectancy includes every trade. Compare to contemporaneous baseline and actual breakeven, never to 50% alone. Scalar ±1.5-ATR breakeven reference is `0.5 + mean(cost_atr)/3`; the Lead independently checks the interpretation after the raw evidence is complete.

This is a descriptive measurement stage; no setting is selected for trading. Preserve the prior chronological design (2021 descriptive; past complete half-years from 2022 for inner development; 2023H1..2026H2p historical outer series). None is renamed a genuinely unseen blind test. Pair/triple selection, random-entry comparisons, final inferential gates and future-data freeze are **not performed by this paper**; their necessity is retained for later stages. The full research multiplicity budget remains 70,330, not 52; do not weaken correction or adoption gates.

## 5. Fixed trading model

Decision at close of signal bar i; fill at open i+1; fix Wilder ATR14 measured at i. Target +1.5 ATR and stop −1.5 ATR; examine i+1 through i+18 inclusive, including the fill bar. If both barriers occur in one candle, stop first. An opening gap below stop exits at the worse open; a gap above target receives the target price, not a better open. Timeout exits at close i+18. Reject incomplete horizons, invalid ATR/prices and segment-crossing horizons. One position per asset; preserve existing same-bar exit/re-entry ordering and cash eligibility.

Fresh $1,000 paper book per asset/candidate/window; fixed $20 trade notional; 0.13% per side including fees/slippage, $0.052 round trip per executed trade. No leverage, shorts, live orders, all-in, dynamic sizing, exit experiments, indicator inputs from future labels, universe changes or new services.

The existing draft metric writer emits per-asset and summary partitions. **Only independently rebuilt full raw trades are accepted as finished evidence here.** Summary metrics and inferential fields remain DRAFT until the Lead re-derives them. In particular, pooled drawdown percentages must not be quoted from the inherited single-$1,000 denominator; the Lead checks against $1,000 per asset. Do not issue an adoption verdict or present these draft summaries as final financial conclusions.

## 6. Resource and publication rules

Use the prepared stage entry point, which bounds raw Parquet parts to 8,000,000 bytes and batches to 5,000,000 bytes; 5,000 rows is a chunk ceiling, not a guarantee of file size. Full raw fields are retained; no sampling, deletion or compressed summary substitutes for the full ledger. Parquet is written from bounded memory directly to the registered work branch. No giant local ledger.

Source setup reserves 750,000 local bytes; total workspace cap remains 125,000,000 bytes. Dependencies already importable and matching the accepted versions are reused. Missing dependencies are installed by the prepared bootstrap outside the workspace, with installer temporary files outside it and no pip download cache. Do not presume a previous `/tmp` installation survived a new session. No full clone/fetch, dependency cache inside the workspace, market archive download or deletion. The bootstrap may install/replace generated packages inside its own external runtime directory; this grants no authority over research code, datasets or main. Existing runtime memory guard remains active. Larger-run duration/storage estimates are not acceptance results.

Publication is serial. The prepared client spaces total requests by at least 2 seconds and writes by at least 15 seconds; branch reads and immutable tree/blob reads are cached/bounded. Parent transport's bounded retry can add one request; these pacing values are not claims about shared-account usage or GitHub's unpublished secondary limits. Respect any actual Retry-After. Do not change the token, thresholds or code to bypass a rate limit.

If HTTP 403/429 or another platform error interrupts execution, preserve work; record the exact operation, code, message and Retry-After without the secret. Verify branch head and scope hashes on restart, then repeat the same prepared command for the same run ID after the server wait. The writer verifies recovered partitions and coverage; no new run ID or second experiment is needed. Only one active publisher. A critical integrity mismatch stops the affected measurement; send the error to Lead for repair, not executor code changes.

## 7. Private authentication

This is the owner-supplied token, included directly as requested. Initialise it in the execution process; never print it, enable shell tracing, put it in code, LOG, ticks, raw outputs, remote URLs or the repository copy of this paper. The public copy redacts only the value. No `gh` or local `origin` is required.

```sh
set +x
export GH_TOKEN='[OWNER_TOKEN_REDACTED]'
```

## 8. Exact execution commands — dependency admission before synthetic readiness

### Prepared dependency bootstrap: allowed setup, not executor development

On every fresh session/resume, execute the following prepared code using the same Python that will run the stage. It probes NumPy/Pandas/SciPy/PyArrow imports and accepted versions, tests Parquet with Zstandard, installs a missing PyArrow wheel (or a missing numeric environment) into its versioned external runtime, then repeats the probe. Pip uses the official PyPI index, binary wheels, no cache and an external temporary directory. GH_TOKEN is removed from the installer environment. Dependency installation is explicitly authorised by this correction; no new paper/owner confirmation is needed.

Do not remove existing files or reinstall the research engine. No full clone or original market download. Only the prepared package installer may maintain its generated external runtime. Preserve the previously prepared stage sources and partial R1 evidence.

Lead checks actually executed: native PyArrow 25.0.1 import and Parquet/Zstandard round-trip on Python 3.12.14; the complete 636-group synthetic stage; standard-library-only transport import with Python `-S`; real pip resolution (`--dry-run`) of the CPython 3.13 x86_64 wheel from PyPI. The missing-dependency/installation control flow and forbidden workspace-path case were simulated. **A fresh native Python 3.13 installation was not executed by Lead**, and the executor runtime has not been remeasured yet. Final environment PASS must come from this probe in the executor runtime; dry-run is not installation.

Run this prepared bootstrap before the previous source/synthetic steps. Its code needs only the Python standard library and invokes the existing `python -m pip` only when a dependency is missing or mismatched:

```sh
python - <<'PY'
"""Prepared dependency setup; no research-code or market-data modification."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

VERSIONS = {'numpy': ['2.3.5'], 'pandas': ['2.2.3'],
            'scipy': ['1.17.0', '1.17.1'], 'pyarrow': ['25.0.1']}
PROBE = r'''
import json, importlib
allowed = %s
versions = {}; issues = {}
for name, accepted in allowed.items():
    try:
        m = importlib.import_module(name); versions[name] = m.__version__
        if m.__version__ not in accepted: issues[name] = 'version: '+m.__version__
    except Exception as e: issues[name] = type(e).__name__+': '+str(e)
if not issues:
    try:
        import pyarrow as pa, pyarrow.parquet as pq
        table = pa.table({'asset':['fixture','fixture'], 'gross':[1.0,-0.3], 'cost':[0.052,0.052]})
        sink = pa.BufferOutputStream(); pq.write_table(table,sink,compression='zstd',version='2.6')
        if not pq.read_table(pa.BufferReader(sink.getvalue())).equals(table):
            raise RuntimeError('Parquet round-trip mismatch')
    except Exception as e: issues['pyarrow'] = type(e).__name__+': '+str(e)
print(json.dumps({'versions':versions,'issues':issues,'parquet_roundtrip':'PASS' if not issues else 'NOT RUN'}))
''' % repr(VERSIONS)


def prepare(target, workspace, runner=subprocess.run):
    target=Path(target).resolve(); workspace=Path(workspace).resolve()
    if target == workspace or workspace in target.parents:
        raise RuntimeError('dependency directory must be outside the experiment workspace')
    target.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ); env.pop('GH_TOKEN',None)
    env['PYTHONPATH']=str(target)+os.pathsep+env.get('PYTHONPATH','')
    env['PYTHONDONTWRITEBYTECODE']='1'
    temporary=target/'installer-temporary';temporary.mkdir(exist_ok=True)
    env['TMPDIR']=str(temporary)
    def probe():
        result=runner([sys.executable,'-c',PROBE],env=env,text=True,capture_output=True)
        if result.returncode:
            raise RuntimeError('dependency probe exit '+str(result.returncode)+': '+result.stderr)
        return json.loads(result.stdout.strip().splitlines()[-1])
    before=probe()
    if before['issues']:
        requirements=(['pyarrow==25.0.1'] if set(before['issues'])=={'pyarrow'}
                      else ['numpy==2.3.5','pandas==2.2.3','scipy==1.17.1','pyarrow==25.0.1'])
        command=[sys.executable,'-m','pip','install','--index-url','https://pypi.org/simple',
                 '--target',str(target),'--upgrade','--only-binary=:all:',
                 '--no-cache-dir','--disable-pip-version-check']
        if requirements==['pyarrow==25.0.1']:command.append('--no-deps')
        result=runner(command+requirements,env=env,text=True,capture_output=True)
        if result.returncode:
            raise RuntimeError('prepared dependency install exit '+str(result.returncode)+': '+result.stdout+'\n'+result.stderr)
    after=probe()
    if after['issues']:raise RuntimeError('dependency setup incomplete: '+json.dumps(after['issues']))
    return {'status':'PASS','external_runtime':str(target),'python':sys.version.split()[0],
            **after,'initial_issues':before['issues'],'market_outcomes_read':False}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--target',default='/tmp/nova-stage1-runtime-'+sys.implementation.cache_tag)
    parser.add_argument('--workspace',default='/home/user')
    args=parser.parse_args();print(json.dumps(prepare(args.target,args.workspace),indent=2))


if __name__=='__main__':main()

PY
export NOVA_STAGE1_RUNTIME="$(python -c 'import sys; print("/tmp/nova-stage1-runtime-"+sys.implementation.cache_tag)')"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="${NOVA_STAGE1_RUNTIME}:${PYTHONPATH:-}"
```

Continue only if this code exits 0 and prints `status: PASS`. Keep its exact version/probe output as environment evidence in final delivery. Never substitute a pip exit alone for the fresh native probe. If the session is reset later, repeat this bootstrap before synthetic/measure/audit, not the entire experiment under a new run ID.

### Stage source and synthetic admission


Run in the existing executor workspace `/home/user`, using its existing working Python/dependencies. Cancel and verify the old scheduled/process execution first (§1). Then materialise the fixed prepared source (this is setup, not implementation):

```sh
cd /home/user
python - <<'PY'
from pathlib import Path
import os, json, hashlib, urllib.request, time, sys
root=Path('/home/user/nova-stage1-20261005')
workspace=Path('/home/user')
def disk_bytes():
    total=0
    for directory, _, files in os.walk(workspace):
        for name in files:
            try:total+=(Path(directory)/name).stat().st_size
            except FileNotFoundError:pass
    return total
before=disk_bytes()
if before+750000>125000000:
    raise RuntimeError(f'workspace admission guard: {before} bytes; need 750000 bytes for prepared source and small records; no deletion permitted')
commit='005e9eed558542ce6f0468ecd6786dc71d3dce57'
url='https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/'+commit+'/'
def read(path):
    for attempt in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(url+path,headers={'User-Agent':'NOVA-Stage1-Setup'}),timeout=40).read()
        except Exception:
            if attempt==2:raise
            time.sleep(2*(attempt+1))
raw=read('history/research/hyp_lab_out/L0084-entry-mix-r1/stages/01-singletons/scope.json')
if hashlib.sha256(raw).hexdigest()!='08739a72ab49b244a8db8f1e8fc080b0e85a27817c34e7711bf3dfe515c5628a':raise RuntimeError('scope SHA256 mismatch')
scope=json.loads(raw)
package=root/'tools/l0084_entry_mix_r1';package.mkdir(parents=True,exist_ok=True)
for name,digest in scope['code_sha256'].items():
    data=read('tools/l0084_entry_mix_r1/'+name)
    if hashlib.sha256(data).hexdigest()!=digest:raise RuntimeError('source hash mismatch: '+name)
    target=package/name
    if target.exists() and target.read_bytes()!=data:raise RuntimeError('existing stage source differs: '+name)
    if not target.exists():target.write_bytes(data)
if disk_bytes()>125000000:raise RuntimeError('workspace disk guard exceeded after source setup')
print('STAGE1_PREPARED_SOURCE_VERIFIED',len(scope['settings']),len(scope['assets']),len(scope['windows']))
PY
export L0084_R1_ROOT=/home/user/nova-stage1-20261005
export L0084_R1_OUTPUT=/home/user/nova-stage1-20261005/local-record
export PYTHONPATH="/home/user/nova-stage1-20261005/tools:${NOVA_STAGE1_RUNTIME}:${PYTHONPATH:-}"
python -m l0084_entry_mix_r1.stage1 --synthetic
```

Do not start market measurement unless setup and the prepared synthetic command both exit 0. The command never reads market outcomes. Preserve the output; a failure goes to Lead with the actual error. No development task is delegated.

After initialising GH_TOKEN exactly as above, run **only**:

```sh
python -m l0084_entry_mix_r1.stage1 --mode measure
python -m l0084_entry_mix_r1.stage1 --mode audit
```

Run the second command only after the first exits 0. It independently rebuilds every raw trade using the separate reference portfolio/exit loop. Neither command runs pairs, triples or chooses winners. A publication interruption is resumable with the same run ID and verified bytes; retain actual errors and honour the server wait.

After both return 0, record the final handoff, LOG and new numbered tick with this prepared command:

```sh
python - <<'PY'
import json
from l0084_entry_mix_r1.stage1 import PacedTransport,BRANCH,BASE,RUN
from l0084_entry_mix_r1 import transport as T
from l0084_entry_mix_r1.evidence import commit_evidence
T.BRANCH=BRANCH
client=PacedTransport();head=client.branch_head()
audit=json.loads(client.blob_from_commit(head,BASE+'/raw_audit.json'))
measurement=json.loads(client.blob_from_commit(head,BASE+'/measurement.json'))
if audit.get('status')!='PASS' or audit.get('groups')!=636:
    raise RuntimeError('stage1 full raw audit is absent or incomplete')
if measurement.get('status')!='RAW_MEASUREMENT_COMPLETE_AUDIT_PENDING':
    raise RuntimeError('stage1 measurement manifest is absent or unexpected')
delivery={'status':'STAGE1_RAW_COMPLETE_LEAD_REVIEW_PENDING','run_id':RUN,'branch':BRANCH,
          'verified_results_parent':head,'independent_raw_audit_head':audit['fixed_head'],
          'report':'Lead will derive and audit the financial report; no executor adoption judgment',
          'next_stage':'NOT STARTED','unresolved':['Final metric/inference review by Lead; no random-control or final strategy-adoption verdict in this stage'],
          'measurement_manifest':BASE+'/measurement.json','raw_audit':BASE+'/raw_audit.json',
          'raw_trade_path':'history/research/hyp_lab_out/L0084-entry-mix-r1/trades/run='+RUN,
          'coverage_groups':636,'assets':12,'settings':52,'windows':12}
handoff=('Stage 1 only is complete as raw measurement and independent raw audit.\n'
         'Pairs, triples, random-entry controls, final financial report and strategy adoption are NOT COMPLETED in this delivery.\n'
         'The Lead reviews the immutable evidence and prepares the report before issuing another stage.\n')
receipt=commit_evidence({BASE+'/delivery.json':json.dumps(delivery,indent=2).encode(),BASE+'/HANDOFF.md':handoff.encode()},
    'L0084 stage 1: deliver singleton evidence for Lead review',
    'Stage-1 raw measurement and full independent execution audit completed; remaining stages not started. Final financial/statistical judgment belongs to Lead.',
    'stage1 raw evidence delivered',
    '- Decision: stop at the boundary of stage 1.\n- Execution: all 636 registered candidate-window groups measured and independently reconciled.\n- Produced: immutable full raw evidence, coverage, audit and delivery; not an adoption verdict.\n- Next: Lead reviews results and writes the financial report before another stage.',client=client)
print(json.dumps({'status':delivery['status'],'verified_remote_commit':receipt['head'],'branch':BRANCH},indent=2))
PY
```

### Recording an environment obstruction without PyArrow

The package `__init__`, `transport` and `evidence` modules use only the standard library. The absent PyArrow prevents importing `stage1`, **not** this status transport. With the prepared source directory on PYTHONPATH and GH_TOKEN initialised, this prepared command records the current known dependency recovery, append-only LOG and a new numbered tick without importing the market runner. It may be run before the bootstrap if required. Do not claim a future different error matches this old message; preserve and report the full actual future error.

```sh
export PYTHONPATH="/home/user/nova-stage1-20261005/tools:${PYTHONPATH:-}"
python - <<'PY'
import sys,json
from l0084_entry_mix_r1 import transport as T
from l0084_entry_mix_r1.evidence import commit_evidence
T.BRANCH='agent/l0084-r1-stage1-2026-10-05'
path='history/research/hyp_lab_out/L0084-entry-mix-r1/stages/01-singletons/runtime-recovery-status.json'
obj={'status':'ENVIRONMENT_RECOVERY_IN_PROGRESS_MARKET_NOT_STARTED',
     'previous_error':"ModuleNotFoundError: No module named 'pyarrow'",
     'action':'Prepared external runtime setup authorised; synthetic acceptance remains mandatory',
     'scope_unchanged':True,'run_id':'stage1-singletons-v1'}
r=commit_evidence({path:json.dumps(obj,indent=2).encode()},
    'L0084 stage 1: record dependency recovery before market measurement',
    'Executor reported PyArrow absent before synthetic acceptance; no stage market measurement started. Prepared dependency recovery is authorised outside the workspace.',
    'stage1 dependency recovery',
    '- Decision: retain stage scope and fix its dependency setup.\n- Execution: preserve the old run and use the prepared external installer.\n- Produced: actual prior missing-dependency error and recovery status; no market result.\n- Next: require native environment and synthetic PASS before measurement.',client=T.GitHubTransport())
print(json.dumps({'recorded_commit':r['head'],'pyarrow_loaded':'pyarrow' in sys.modules}))
PY
```

A publishing HTTP error still honours its server wait. Failure of the package installer never grants permission to bypass the synthetic measurement admission.

## 9. Required files and stage acceptance

At the registered destination require: `scope.json`, `measurement.json`, `raw_audit.json`, `delivery.json`, `HANDOFF.md`; complete raw trade partitions; coverage and receipt shards; draft per-asset/summary/half-year metric partitions; append-only `LOG.md` entry and new numbered activity tick. The measurement manifest contains all partition paths, counts and hashes. Do not deliver only tests, setup, DRAFT source or a ZIP while calling the stage complete.

Accept **STAGE1_RAW_COMPLETE_LEAD_REVIEW_PENDING** only if: all 636 unique candidate/window groups including zero groups exist; all 12 assets and fixed settings/windows are retained; all raw partitions have verified immutable bytes/hash/schema; every raw field agrees with independent execution rebuilding; no pair/triple group is present in this new run; delivery/LOG/tick are uploaded and final remote head is verified. Zero trades or negative expectancy do not make technical completion fail. No profitability or adoption criterion is weakened or considered passed by this stage.

An incomplete upload or audit is **IN PROGRESS/BLOCKED**, not complete. The old all-stage run may retain its independent IN PROGRESS state; this delivery does not rewrite its history.

## 10. Completion and Lead responsibilities

Return the final remote commit and exact stage status once uploaded; the owner then needs to tell Lead only **تم**. Do not open a PR, merge, push to main or start any next stage. Lead reads this named branch, re-derives statistics from the raw evidence, audits draft metrics and writes the complete Arabic financial report with the constitution's summary/seven tables and explicit unmeasured fields. No executor software repair or strategy judgment.

The next stage is not executable under this paper. The Lead issues one subsequent stage only after reviewing this one. The registered pairs/triples and remaining controls are deferred execution, not dropped research possibilities.

---

## 5. Complete definitions

O,H,L,C,V=open,high,low,close,BASEvolume. TP=(H+L+C)/3. EMA(n) alpha2/(n+1),adjust=False,min_periods=n; Wilder(n) alpha1/n,adjust=False,min_periods=n. Series-cross: previous A<=B/current A>B. Scalar upwardcross: previous<t/current>=t. First previous invalid. Trailing windows include current unless specified.

RSI(n): d=C-Cprev; U=Wilder(max(d,0),n),D=Wilder(max(-d,0),n),100-100/(1+U/D); preserve reference D=0=>NaN=>false, not silent100. StochK=100*(C-min(L,n))/(max(H,n)-min(L,n)); D=SMA(K,d), UNUSED by these triggers. Bollinger std ddof0. Aroon n uses n+1 trailingbars: Up=100*argmax(H)/n,Down=100*argmin(L)/n, positions0..n, earliesttie.

CCI=(TP-SMA(TP,n))/(0.015*mean(abs(TP-windowmean),n)). WilliamsR=-100*(max(H,n)-C)/(max(H,n)-min(L,n)). MFI14: TP*V summed where TP rises vs falls over14bars; unchangedTPzero;100-100/(1+positive/negative),zero negative=>NaN. z=(current-trailing50mean)/populationstd50, INCLUDINGcurrent, all50 required;zero denominator=>NaN.

Body=abs(C-O);lowerwick=min(O,C)-L;upperwick=H-max(O,C);range=H-L.
Pivot at decisioni confirms c=i-2: L[c]=minimumL[c-2..c+2], strictlybelow L[c-1],L[c+1]. Compare immediately previous confirmedpivot, c-prev_c<=20, currentprice low strictlylower,currentRSI strictlyhigher and finite. Emit at i, never c. Update previouspivot every time. No minimumfivebar separation or0.25ATRdepth.

ATR14: TR=max(H-L,abs(H-Cprev),abs(L-Cprev)),firstTR=H-L,Wilder14. Signal ATR fixed for trade; asset-specific arrays. No centered feature inputs.

| Setting | Full signal rule |
|---|---|
| Aroon14_bull_x | AroonUp crosses above AroonDown, n=14. |
| Aroon25_bull_x | AroonUp crosses above AroonDown, n=25. |
| BB20_2.0_reenter | Close crosses above SMA(C,20) minus 2.0 times population std(C,20). |
| BB20_2.5_reenter | Close crosses above SMA(C,20) minus 2.5 times population std(C,20). |
| BB20_3.0_reenter | Close crosses above SMA(C,20) minus 3.0 times population std(C,20). |
| BullEngulfing | Previous close < previous open; current close > current open; current open <= previous close; current close >= previous open. |
| CCI14_xup_-100 | CCI length 14 crosses upward through -100. |
| CCI20_xup_-100 | CCI length 20 crosses upward through -100. |
| Donchian10_break | Close > maximum high of previous 10 bars, excluding current. State, not crossing-only. |
| Donchian20_break | Close > maximum high of previous 20 bars, excluding current. State, not crossing-only. |
| Donchian20_fail | High > maximum high of previous20 bars; close <= same maximum. Upper-channel failure, not lower recovery. |
| Donchian55_break | Close > maximum high of previous 55 bars, excluding current. State, not crossing-only. |
| EMA_x_20_200 | EMA(20) crosses above EMA(200). |
| EMA_x_20_50 | EMA(20) crosses above EMA(50). |
| EMA_x_50_200 | EMA(50) crosses above EMA(200). |
| FVG_single | Current low > high two bars earlier; first two bars false. |
| Hammer | Positive body and range; lower wick >=2*body; upper wick <=body. No pivot/midpoint filter. |
| MACD_12_26_9_xup | EMA(12) minus EMA(26) crosses above its EMA(9) signal. |
| MACD_5_35_5_xup | EMA(5) minus EMA(35) crosses above its EMA(5) signal. |
| MFI14_xup_20 | MFI14 crosses upward through20. |
| PX_x_EMA200 | Close crosses above EMA(200). |
| PX_x_EMA50 | Close crosses above EMA(50). |
| RSI14_bull_divergence | RSI length 14 divergence between successive confirmed pivots, lookback20, defined below. |
| RSI14_xup_20 | RSI length 14 crosses upward through 20. |
| RSI14_xup_25 | RSI length 14 crosses upward through 25. |
| RSI14_xup_30 | RSI length 14 crosses upward through 30. |
| RSI21_bull_divergence | RSI length 21 divergence between successive confirmed pivots, lookback20, defined below. |
| RSI21_xup_20 | RSI length 21 crosses upward through 20. |
| RSI21_xup_25 | RSI length 21 crosses upward through 25. |
| RSI21_xup_30 | RSI length 21 crosses upward through 30. |
| RSI7_xup_20 | RSI length 7 crosses upward through 20. |
| RSI7_xup_25 | RSI length 7 crosses upward through 25. |
| RSI7_xup_30 | RSI length 7 crosses upward through 30. |
| Stoch14_3_xup_15 | Raw stochastic K length 14 crosses upward through 15. D length 3 is UNUSED. |
| Stoch14_3_xup_20 | Raw stochastic K length 14 crosses upward through 20. D length 3 is UNUSED. |
| Stoch14_3_xup_25 | Raw stochastic K length 14 crosses upward through 25. D length 3 is UNUSED. |
| Stoch21_5_xup_15 | Raw stochastic K length 21 crosses upward through 15. D length 5 is UNUSED. |
| Stoch21_5_xup_20 | Raw stochastic K length 21 crosses upward through 20. D length 5 is UNUSED. |
| Stoch21_5_xup_25 | Raw stochastic K length 21 crosses upward through 25. D length 5 is UNUSED. |
| TakerRatioZ_ge_1.5 | Trailing50 z-score of BASE taker_buy_volume / volume including current >= 1.5. |
| TakerRatioZ_ge_2.0 | Trailing50 z-score of BASE taker_buy_volume / volume including current >= 2.0. |
| TakerRatioZ_ge_2.5 | Trailing50 z-score of BASE taker_buy_volume / volume including current >= 2.5. |
| TakerRatio_gt_0.48 | BASE taker_buy_volume / volume > 0.48. |
| TakerRatio_gt_0.5 | BASE taker_buy_volume / volume > 0.5. |
| TakerRatio_gt_0.52 | BASE taker_buy_volume / volume > 0.52. |
| TakerRatio_gt_0.55 | BASE taker_buy_volume / volume > 0.55. |
| VolSpike_z1.5 | Volume trailing50 z-score INCLUDING current >= 1.5. No close-location filter. |
| VolSpike_z2.0 | Volume trailing50 z-score INCLUDING current >= 2.0. No close-location filter. |
| VolSpike_z2.5 | Volume trailing50 z-score INCLUDING current >= 2.5. No close-location filter. |
| VolSpike_z3.0 | Volume trailing50 z-score INCLUDING current >= 3.0. No close-location filter. |
| WilliamsR14_xup_-80 | WilliamsR length 14 crosses upward through -80. |
| WilliamsR21_xup_-80 | WilliamsR length 21 crosses upward through -80. |

### Differences from the earlier 76-setting paper

| Item | Proposed 76-setting paper | Executable 52-setting grid here |
|---|---|---|
| Stochastic | K crosses D below a level | K crosses the scalar level; D is unused |
| Volume z-score | Previous 100 bars and close-position condition | Trailing 50 including current bar; no close-position filter |
| Taker ratio | Quote volumes | Base volumes |
| Divergence | Depth and separation requirements | Successive confirmed pivots as defined above |
| Hammer | Upper wick at most half the body, plus position conditions | Upper wick at most the body; no pivot/position condition |

The 52 settings are not an identical-definition subset of the 76. Missing families and the corrected local package remain PENDING in catalogue_pending.md. No substitutes or negative verdicts for unmeasured definitions. Do not claim to exhaust all indicators.


