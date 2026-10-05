# L0084-R1 — ورقة المرحلة الأولى المفحوصة، الإصدار 4 — إصلاح المتابعة والاستئناف

**المطلوب:** تشغيل قياس الإعدادات الـ52 منفردة ورفع أدلته وتدقيقه، ثم التوقف عند تسليم هذه المرحلة. لا أزواج ولا ثلاثيات الآن. الكود وتجهيز البيئة جاهزان؛ إصلاح البرمجيات وتحليل النتائج وكتابة التقرير المالي من عمل Lead.

**هذه الورقة تستبدل تعليمات المرحلة الأولى السابقة.** احتفظ بكل الأعمال القديمة. نفّذ الأمر الواحد أدناه بعد التأكد من عدم وجود تشغيل قديم نشط؛ لا تحتاج ورقة أخرى بين الفحص والقياس والتدقيق والتسليم.

## إلزام المنفّذ: المتابعة حتى التسليم أو عائق فعلي

هذه الورقة كاملة وتحل محل النسخة السابقة. **لا تُنهِ دورك برسالة IN PROGRESS أو «مستمر» أو بمجرد استلام معرّف عملية.** بعد بدء الأمر، تابع معرّف العملية بأداة الانتظار/المتابعة المتاحة في المنصة إلى أن ينتهي، ثم تحقّق من التسليم. التحديثات تكون أثناء المتابعة ولا تستبدلها. البطء أو الانتظار وفق GitHub ليس سببًا لإنهاء العمل. لا تفترض أن Arena تواصل العمل بعد انتهاء ردك؛ لم نتحقق من ضمان كهذا.

إذا أعادت الأداة `not_found`، افحص العمليات الفعلية وسجلات `supervision` أولًا. وجود عملية قياس حيّة يعني متابعتها وعدم بدء نسخة ثانية. إذا ثبت عدم وجود عملية حيّة، فغياب رمز الخروج القديم **ليس مانعًا من الاستئناف**: أعد الأمر نفسه بالفرع والمعرّف نفسيهما؛ الكاتب يتحقق من الأدلة المحفوظة قبل إعادة استخدامها. لا تمسح الأدلة ولا تخترع سبب الانقطاع. إذا تعذّر تحديد حالة العمليات فعلًا، فهذا عائق محدد يُذكر كما هو، ولا يُحل بتشغيل ناشرين متنافسين.

لا تنهِ الدور إلا عند التسليم المكتمل المتحقق منه، أو عائق فعلي لا يمكن تجاوزه ضمن الأوامر المصرّح بها. إذا فرضت المنصة حدًا قاطعًا للمدة أو أغلقت العملية، اذكر الدليل والخطأ أو القيد المشاهد، وآخر سجل/التزام متحقق منه. لا تجعل غياب خطأ قديم شرطًا مستحيلًا للاستمرار. لا ترسل سؤال إذن جديدًا للاستئناف المعتاد.

**التغيير التقني:** مشغّل المتابعة الجديد يكتب سجلًا منذ البداية ويُفرغه إلى القرص أثناء التنفيذ، مع سجل حالة قبل بدء الطفل، ورقم PID، وملاحظة حياة كل 30 ثانية، ورمز الخروج حين يكون متاحًا. ملاحظة الحياة مؤرخة وليست دليلًا على أن العملية ما زالت تعمل بعد ذلك. يحتفظ بكل محاولة في ملف مستقل، ويورّث قفل الاستئناف للعملية التابعة لمنع تكرارها إذا اختفى المشغّل وحده. يعيد استخدام نجاح الفحص الاصطناعي محليًا فقط إذا تطابقت بصمات النطاق والمفسّر وإصدارات المكتبات؛ لا يتجاوز القياس أو التدقيق اعتمادًا على سجل محلي.

**مصادر الإصلاح:** `tools/launch_stage1_recovery.py` في الالتزام `059de27feec44d50cc464e69d586eec8d822bf8e`، وفرع التجهيز `agent/l0084-stage1-supervision-2026-10-05`. هذا فرع نشر الإصلاح فقط؛ **نتائج القياس تبقى على `agent/l0084-stage1-checked-2026-10-05`** والمعرّف `stage1-singletons-v1`. المحرك والنطاق ومصدرهما `74bc4cba32c083f34b6588b685f93216aaa580c9` لم تتغير.

**تحقق Lead:** أربعة اختبارات إصلاح ناجحة تشمل قتلًا فعليًا بـSIGKILL، وبقاء القفل مع الطفل، وحفظ النص قبل انتهاء العملية ولو بلا سطر جديد، والاستئناف بعد فقدان رمز الخروج، وحجب التوكن، ورفض إعادة استخدام فحص تغيّر نطاقه. نجح مسار الفحص الاصطناعي عبر المشغّل الجديد. وفي الرأس `4db5769519147f67a50f942ffef1a8590b29ba04` وجدت 168 جزء صفقات و7 شظايا إيصالات؛ تحققت من تطابق بصمات Git لكود المحرك والمدخلات الـ12. هذا جرد أدلة جزئية، **وليس تدقيقًا ماليًا أو إثبات اكتمال**. تحقق SHA256 ومحتوى الأجزاء عند الاستئناف من عمل الكاتب القائم ولم يُلغَ.

السجلات المحلية الجديدة: `/home/user/nova-stage1-checked-v3/supervision/<phase>-<attempt>.log` وملف JSON بالاسم نفسه؛ `synthetic-passed.json` إيصال فحص وليس حكمًا على السوق. عند فقد العملية لا تعتمد على وجود كلمة RUNNING قديمة؛ افحص PID والعمليات والقفل. يحتفظ السجل بما كُتب قبل الانقطاع إذا بقي القرص؛ لا يستطيع البرنامج ضمان بقاء قرص تمسحه المنصة. الأدلة البعيدة محفوظة في الفرع الأصلي ولا تُحذف.

## 1. Objective and boundary

Question: how does each locked entry signal behave historically, separately, after the fixed costs versus its contemporaneous no-signal book? **No prior hypothesis of a profitable winner.** The scope is one descriptive stage, not an exhaustive combination search or trading approval.

Why this revision: the executor reported the prior attempt stopped at `ModuleNotFoundError: No module named 'pyarrow'`, before market measurement. The earlier paper prohibited routine dependency recovery; this revision explicitly permits and automates the prepared recovery outside the workspace. Lead additionally reproduced a resume defect that could leave metric tables incomplete, repaired it, and added full table-coverage checks. Executor does no implementation or repair.

The executor's former observation of 71,379,799 workspace bytes and absence of running tasks is **reported history**, not a current measurement. Recheck the workspace and active tasks before running. The old run `r1-20261005T145115Z` and both old branches remain untouched. Check the old scheduled ID `r1-measurement-retry-after-rate--74824206`; `not_found` plus no active old process is an acceptable quiescence result, not a new blocker. If a previous attempt is still active, let it stop safely before starting this publisher. Never run both papers together.

## 2. Sources, exact code and destination

- Official constitution/main verified by Lead: `8e966404e77a97cd32cd19b7b574b55809e743ab`.
- Previous stage source base: `5e0e9121c5a382638072f7cec83f3b002a701f87`.
- **Executable source commit:** `74bc4cba32c083f34b6588b685f93216aaa580c9`.
- Repository: https://github.com/stevearagonno1/NOVA-DRAGON
- **Only write destination:** `agent/l0084-stage1-checked-2026-10-05`.
- **Run ID:** `stage1-singletons-v1` on that new branch. Same scientific scope; a corrected implementation isolated from old partial branches.
- Stage directory, denoted **S** below: `history/research/hyp_lab_out/L0084-entry-mix-r1/stages/01-singletons`.
- Evidence root, denoted **R** below: `history/research/hyp_lab_out/L0084-entry-mix-r1`.
- Scope at the executable source commit: `S/scope.json`; SHA-256 `93dcc3e5d8eb0c4deb54b7fe6b58be2cbe0760e27c846ec221c809f7861ebcd7`. It lists all code hashes and the 12 input panel paths, byte counts and hashes.
- Launcher: `tools/launch_stage1_checked.py`; SHA-256 `b534e24d98045da55ac167171bfdbd76d1ae39a9d0cbfcaf47d037c6b8119207`.
- Runtime installer: `tools/prepare_stage1_runtime.py`; package: `tools/l0084_entry_mix_r1/`.

All source files were uploaded and read back byte-for-byte from their immutable commit. Read public sources without credentials; authenticate only the GitHub API write/read route. No `gh`, clone, local `origin`, extra service or manual new environment design is required. No PR, main push or merge.

Reused unchanged by SHA-256: `engine.py`, `indicators.py`, `data.py`, `measure.py`, `stats.py`. Changes are prepared runtime admission, a sequential launcher, recovery of unfinished metric tables, metric coverage checks and resource-path handling. No signal, fill, exit, cost, date or candidate threshold is changed.

## 3. What Lead actually checked

| Check actually performed | Observed result |
|---|---|
| Package test suite | 39/39 passed, exit 0 |
| Launcher order/failure gate tests | 4/4 passed; a failed step cannot start the following one |
| Native clean dependency restoration | Python 3.12.14: missing PyArrow restored; Python 3.13.14: all four libraries initially missing and installed successfully |
| Native Parquet/zstd encode/decode | Passed in both environments |
| Actual `stage1 --synthetic` shared measure/write/independent-audit path | Passed on Python 3.12.14 and 3.13.14; 636 groups, 12 assets, 12 windows; 720 synthetic trades and 600 zero-trade groups |
| Derived table coverage | 636 summary + 7,632 asset + 8,268 final rows; missing/duplicate groups rejected |
| Interruption and restart | Nine publication boundaries, including lost acknowledgement after a committed index; no missing/duplicated rows; complete repeat unchanged |
| Missing or changed evidence and HTTP 403 listing | Rejected; a rate limit is not interpreted as an empty directory |
| Pinned-source launcher preflight | Immutable remote download, dependency admission and synthetic CLI passed; market not started |
| Actual work-branch upload and immutable readback | Passed through the launcher's logging/upload method at `56dccc25aff0fb1ef7fc942c209f009b28366286` |

Evidence: `S/lead-readiness-v3/`. Reproducible short commands are `python -m unittest discover -s tools/l0084_entry_mix_r1 -t tools`, `python -m l0084_entry_mix_r1.stage1 --synthetic`, and `python tools/launch_stage1_checked.py --source 74bc4cba32c083f34b6588b685f93216aaa580c9 --workspace <empty-small-workspace> --preflight-only` with the prepared runtime. Executor uses only the full command in §7, which contains its own preflight.

These are synthetic/readiness results, **not market performance**. There is no new market result, indicator ranking, profitability verdict, or guarantee against future network/platform failures. Raw trade reconstruction is independent; draft financial/inferential values still require Lead's financial audit. Storage size and duration of the long run have not been measured by this rehearsal.

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



## 6. Environment, resources and restart

Python supported and tested here: 3.12.14 and 3.13.14. Prepared libraries: NumPy 2.3.5, Pandas 2.2.3, SciPy 1.17.0 or 1.17.1, PyArrow 25.0.1. The installer first checks imports and a native Parquet round trip. If needed, it installs the pinned binary wheels using the existing interpreter's pip, without cache, into `/tmp/nova-stage1-runtime-<python-cache-tag>` **outside `/home/user`**. This exact recovery is authorised setup, not forbidden code repair. Do not assume a temporary dependency folder from an earlier session survives.

The recovery supervisor wraps the unchanged stage launcher and performs setup and all subsequent commands in one invocation and supplies the same runtime path to each. Source lives at `/home/user/nova-stage1-checked-v3`. It checks scope and source SHA-256; refuses different pre-existing source files; locks against a second checked launcher in the same workspace; reserves 1 MB for source/small records; enforces the actual workspace limit of 125,000,000 bytes before materialisation, during writing and before delivery. Keep old evidence; no deletion or full repository download. Do not duplicate market panels locally: read the 12 existing immutable panels into memory with byte/hash checks.

Full trade evidence goes from bounded memory to the exact work branch: Parquet parts ≤8,000,000 bytes, batch threshold 5,000,000 bytes, up to 5,000 rows per raw chunk. Keep complete raw fields and zero groups, never sample or replace the ledger with aggregates. No enormous local ledger. The writer may use up to its 8 MB hard batch ceiling when adding a chunk; the 5 MB value is a flush threshold, not a stronger ceiling.

Paced measurement/audit/normal status publication spaces API calls ≥2 seconds and writes ≥15 seconds. Bounded transport retries can add a request. This is a client throttle, not a guarantee against GitHub account-wide limits. If runtime admission itself fails, the prepared status path uses stdlib only and may upload the actual error without PyArrow. The new `supervision/<phase>-<attempt>.log` and JSON records are written during execution. `last_error.txt` is additional evidence only when the parent catches an error. An uncatchable SIGKILL can leave the last status RUNNING with no exit code; this is not proof of current liveness or a ban on recovery.

For a recoverable network error, honour the actual server `Retry-After`, verify no previous process remains, and rerun **the same §7 command**, same source, branch and run ID. No new paper or owner confirmation is needed. The writer rereads committed partitions and deterministically reconstructs both raw and metric output; recovery may take time because evidence is reverified. Do not increment the run ID, overwrite mismatched evidence or invent an empty remote directory when a read fails. A critical hash, schema, causality or independent-reconstruction mismatch stops the affected work and goes to Lead for repair with the exact error.

Do not use `python -m l0084_entry_mix_r1.cli measure`: that is the old multi-stage route. Do not resume the old comprehensive run or execute another stage after this delivery.

## 7. One execution command — private credential included

Run the following **entire block once** in the executor's terminal. The owner-supplied token is initialised directly. Never echo it or put this private block in source, LOG, ticks, outputs or public repository files. The repository copy is redacted. Preserve this private paper for restarts.

```sh
set +x
export GH_TOKEN='[OWNER_TOKEN_REDACTED]'
python3 - <<'PYCODE'
import hashlib, sys, time, urllib.request
commit = '059de27feec44d50cc464e69d586eec8d822bf8e'
url = 'https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/' + commit + '/tools/launch_stage1_recovery.py'
for attempt in range(3):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'NOVA-Stage1-Recovery'}), timeout=40) as response:
            code = response.read()
        break
    except Exception:
        if attempt == 2: raise
        time.sleep(2*(attempt+1))
if hashlib.sha256(code).hexdigest() != '1c411a5d963fdb80311ebcefda32a4fdc8426aef31f57900dc400f554de09f20':
    raise RuntimeError('recovery launcher SHA256 mismatch')
sys.argv = ['launch_stage1_recovery.py', '--workspace', '/home/user']
exec(compile(code, 'launch_stage1_recovery.py', 'exec'), {'__name__':'__main__'})
PYCODE
```

Execution sequence, automatic and gated: source checks → dependency restoration/probe → synthetic acceptance → long singleton measurement → independent raw audit plus metric coverage → final handoff, LOG and numbered tick → verified remote head. The next step executes only after the previous one succeeds. Do not stop merely after synthetic PASS; the same authorised command continues through final delivery. Keep waiting on the active tool/process; a progress update does not end the executor assignment. A long-running process is IN PROGRESS, not BLOCKED simply because no final result has printed yet.

## 8. Exact deliverables and acceptance

| Repository path | Required content |
|---|---|
| `S/scope.json` | Locked settings, assets, windows, source/helper hashes, input panel paths/hashes |
| `S/measurement.json` | Status, run ID, complete scope, raw-writer counts/partition receipts and derived-output manifest |
| `S/raw_audit.json` | PASS, immutable audited head, 636 groups, raw row/partition reconciliation and metric coverage counts |
| `S/delivery.json` | `STAGE1_RAW_COMPLETE_LEAD_REVIEW_PENDING`, branch, run ID, executable source, verified parent, audited head, 52/12/12 scope, workspace bytes and remaining Lead review |
| `S/environment.json` | Interpreter, library versions, initial missing imports, native probe and external runtime path |
| `S/HANDOFF.md` | Raw completion, financial review pending, no strategy adoption |
| `R/trades/run=stage1-singletons-v1/role=…/candidate=…/window=…/part-*.parquet` | Every raw trade, schema below |
| `R/measurement_index/run=stage1-singletons-v1/part-*.jsonl` | Every candidate/role/window including zero groups; trade/partition counts, schema version and partition paths |
| `R/storage_journal/run=stage1-singletons-v1/part-*.jsonl` and `R/storage_journal.jsonl` | Immutable part receipt shards and their pointers: path, bytes, hashes, commit and readback status |
| `R/metrics_raw/run=stage1-singletons-v1/part-*.parquet` | 636 draft summary rows |
| `R/metrics_by_asset/run=stage1-singletons-v1/part-*.parquet` | 7,632 draft per-asset rows |
| `R/metrics/run=stage1-singletons-v1/part-*.parquet` | 8,268 draft final-format rows; values not yet financially endorsed |
| `R/controls/run=stage1-singletons-v1/part-*.parquet` | Baseline no-signal bookkeeping only; no random controls |
| `R/metric_adjustments/run=stage1-singletons-v1/part-*.parquet` | Draft inferential adjustment fields, schema below |
| `R/halfyears.csv/run=stage1-singletons-v1/part-*.csv` | Draft half-year rows, columns below |
| `LOG.md` and `docs/journal/2026-10-05-l0084-entry-mix-r1/NNN-*.md` | Automatic append/new numbered tick after each successful phase and final delivery; actual failure if interrupted |

Here S and R expand to the exact paths in §2; they are not literal directory names. Existing source files are already present at the destination; execute them unchanged. The locked `labels.py` evaluation labels are forbidden as signal inputs. No centred/future-defined label, leverage, shorts, live order, all-in sizing or exit optimisation.

**Numeric technical acceptance:** exactly 636 unique candidate/window groups including zero groups; all 12 fixed assets, 52 settings and 12 windows retained; all raw partition bytes/SHA/schema/receipts verified; every trade field agrees with the independent fill/exit/portfolio reconstruction; derived coverage exactly 636/7,632/8,268 with no missing or duplicate key; workspace ≤125,000,000 bytes; final handoff/LOG/tick uploaded and remote head verified. No pair/triple groups. Zero trades or losses are valid measured outcomes, not technical failure.

**Reject completion** if any required group/partition/output is missing, duplicated or altered, any independent raw field fails, any required upload is unverified, or any gate failed. Use IN PROGRESS/BLOCKED with the actual error, never COMPLETE. No profitability acceptance criterion is being passed in this descriptive evidence stage. Random controls, final inference, winner selection and future evaluation remain **NOT RUN**.

## 9. Completion response and Lead handoff

After the launcher prints `STAGE1_RAW_COMPLETE_LEAD_REVIEW_PENDING` with a verified commit, return that commit link, branch, run ID, coverage and workspace size; include the small judgment contents from `S/raw_audit.json` and `S/delivery.json`, and the unresolved limits. Do not call a setup-only/DRAFT upload or ZIP the completed experiment. If blocked, return the command/operation, actual error, last verified remote head and available local logs; never disclose the token.

The owner may then send Lead only **تم**. Lead will read the branch and paths in §2, derive statistics from the complete raw evidence, audit the draft summaries and write the Arabic financial report with the constitution's summary and seven tables. That includes win rate/Wilson, actual breakeven and baseline lift, dollar/R expectancy after costs, MAE/MFE, durations, per-asset/year/half-year coverage and the registered bootstrap: 2,000 moving-block replicates of seven UTC days, synchronised across all 12 assets including empty days, seed 84; one-sided 95% lower bound at the fifth percentile. Holm retains the 70,330 full-search family with untested members set to p=1. These inferential calculations are Lead review work after raw delivery, not a claim that this stage computed them. This paper does not delegate unfinished financial review to the executor. The next stage requires Lead review and a new single-stage paper; do not start it automatically.

## 10. File schemas

### Raw trade Parquet

```text
candidate_id: string
role: string
window: string
asset: string
signal_bar: int64
fill_bar: int64
exit_bar: int64
signal_time_utc: string
fill_time_utc: string
exit_time_utc: string
entry: double
exit: double
atr: double
quantity: double
notional: double
outcome: string
gap_flag: bool
double_touch: bool
holding_bars: int64
gross_dollars: double
cost_dollars: double
net_dollars: double
gross_atr_r: double
cost_atr: double
net_atr_r: double
barrier_r: double
mae_atr_r: double
mfe_atr_r: double
seg: int64
```

### Draft metric Parquet

```text
candidate_id: string
members: string
mode: string
role: string
window: string
asset: string
scope: string
n_exec: int64
n_win: int64
n_stop: int64
n_timeout: int64
n_resolved: int64
n_eff: int64
n_signals: int64
n_incomplete: int64
win_rate: double
wilson_lo: double
wilson_hi: double
gross_dollars: double
cost_dollars: double
net_dollars: double
expectancy_dollars: double
profit_factor: double
gross_atr_r: double
cost_atr: double
net_atr_r: double
barrier_r: double
mae_atr_r: double
mfe_atr_r: double
mean_holding_bars: double
mean_time_to_hit_bars: double
gap_count: int64
double_touch_count: int64
n_active_days: int64
coverage: double
mdd_dollars: double
mdd_pct_book: double
drawdown_duration_trades: int64
worst_day_dollars: double
longest_losing_streak: int64
exposure_bars: int64
baseline_win_rate: double
breakeven_rate: double
lift_win_points: double
p_raw: double
p_adjusted: double
ci_lo: double
ci_hi: double
power80: double
metric_status: string
```

### Draft adjustment Parquet

```text
candidate_id: string
role: string
window: string
p_raw: double
p_adjusted: double
power80: double
n80: int64
alpha: double
family_m: int64
```

### Baseline control bookkeeping Parquet

```text
candidate: string
control_type: string
replicate: int64
asset: string
window: string
n: int64
matched_count: int64
net: double
expectancy: double
paired_difference: double
ci_lo: double
ci_hi: double
seed: uint64
```

Half-year CSV columns: `candidate, asset, halfyear, partial, n, net, pf, win, baseline, lift, ci_lo, ci_hi`. JSON/JSONL manifests use the explicit fields described in §8; their emitted files remain the authoritative machine-readable records. No random-control output is required or claimed in this stage.

---

## 11. Complete signal definitions

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


