# ورقة المنفذ — الدفعة الأولى لالتقاط حالة اختراق صاعد في البيتكوين

هذه ورقة تشغيل للمنفذ الوحيد، وليست تكليفًا بتصميم الأدوات أو إصلاحها. يشغّل الحزمة المرفقة كما هي، يقيس، يدقق، يكتب التقرير ويرفع الأدلة على فرع النتائج ثم يتحقق من وصولها. القائد وحده يراجع الحكم لاحقًا.

نقيس الإشارات داخل حالة صعود واحدة في BTCUSDT Spot على15دقيقة. يجوز ظهور الإشارة وسط الحالة؛ لا حد نجاح مفروض مثل70%. هذه الدفعة تشمل548 سجل نسخة مسجلًا له حساب قائم، منها12 تأكيدًا مركبًا موروثًا. ليست اختبارًا لكل الفهرس ولا لكل نطاقات إعداداته. لا حذف لما بقي: سجل التغطية يضعه «غير مقاس» إلى أن يجهزه القائد. لا يصنع المنفذ مؤشرات أو مزيجًا جديدًا في هذه الدفعة.

اختبار الحالة وحدها يقيس الالتقاط والتوقيت والتكرار داخلها. الإشارات الكاذبة والدقة خارجها غير مقاسة؛ لا تصف التغطية بأنها دقة، ولا تعتمد هذا النظام للتشغيل طوال الوقت.

## 1. Question

Measure all548 registered source-backed BTC version records in this package on one precisely defined intraday rise state. Report conditional episode coverage, alert delay, repetition and observed closing-price movement remaining within the same state. Do not select a winner, invent a mixture, apply a success-rate gate, evaluate profitability or expand to other assets/states.

## 2. Why now

The owner approved a BTC state specialist, including mid-rise alerts and eventual mixtures/custom causal signals. The first structural catalogue is complete but contains records requiring implementation, data or semantic review. This is its first executable cohort, chosen by source readiness before market measurement, not by performance. Subsequent sweeps, mixtures, invention and frozen validation require separate prepared stage papers under constitution§11.9; they remain part of the larger objective, not claims of completion here.

## 3. What is already known

Read the current complete constitution at https://github.com/stevearagonno1/NOVA-DRAGON/blob/main/CONSTITUTION.md and follow its resume/tool protocol. For this paper the verified source main is8af2aae214f65a370110921928eaabf07771a6d1 and constitution file blob8e999304b33755ca9dd7383f0a86586f1d729df6. Read the relevant current tape and distinguish new owner instructions from old historical criteria.

The earlier seven-month recurrence study is under history/research/hyp_lab_out/BTC-INTRADAY-2026-10-17/ at that source main. Its reported802 rises/311 overlapping breakout flags belong to its old pulse-and-spacing definition; they are not expected counts for the new continuous episodes below. This paper does not remeasure or reinterpret old results as predictive accuracy.

The supplied source archive SHA256 is d536b7d84ea94f93f080d81086b3ffbe3f2803a8d413fabaaf268c0f7cd1298a, and SQLite SHA256 is19d730d9d4b7f537d0591a55786370331712c9aacb520229714e2cc9f7c60cfc. The prior coverage ledger contains131408 physical records, including utilities/conditions/settings; these are not131408 runnable indicators. The reviewed candidate cohort has596 version IDs:548 permitted BTC/unassigned-asset records and48 other-asset records excluded without transferring their asset-specific settings. Axis-indexed17800618 changes are not swept in this stage. Read coverage_scope.json; preserve these limitations in every result.

## 4. Hypothesis

No predetermined strongest indicator or mixture. This is descriptive discovery: version records may differ in coverage and timing within the fixed state. No significance claim or independent-validation claim is authorized. Repeating an idea across aliases does not create independent evidence.

## 5. Data

BTCUSDT spot, completed15-minute OHLCV candles, Asia/Aden local dates. Use exactly2021-12,2023-05,2023-12,2024-01,2025-05,2025-12,2026-03. Each saved input has3360 bars including four calendar days of warm-up; score only the named month. Input names, immutable repository paths, compressed byte lengths and SHA256 hashes are in inputs.json and the appended table below. No full repository or89MB original Parquet download is needed.

Both verified saved timestamp names, time_utc and close_time_utc, denote candle closes. The reader accepts exactly one of them, validates900-second continuity, finite OHLCV, positive prices, nonnegative volume and15 minute samples per candle. Recompute state conditions from OHLCV; do not trust precomputed feature columns as signals. Native calculations use the complete contiguous warm-up/month history, not concatenated selected intervals.

Taker-buy data are absent. They remain NaN for unused imported interfaces, never a synthetic buy/sell proxy. All evaluated versions are independent of that field. No taker/CVD/profile surrogate is measured.

## 6. Container and exact state

For a completed decision bar i, membership is true if and only if all these conditions hold: i>=260 from the saved input start; every bar in i−60 through i is complete15-minute data; i is inside the named local month; close[i] and close[i−4] belong to the same Asia/Aden date; close[i]/close[i−4]−1 >=0.005; and close[i] is strictly greater than the maximum high of bars i−12 through i−1. The current high is excluded from that maximum. Compare saved floating values directly; no post-result rounding or threshold adjustment.

One episode is a maximal consecutive run of member bars. Split at each local-date change even if both adjacent bars satisfy membership. Its first member bar is its start and its last member bar is its end. There is no additional60-minute spacing or manually selected chart interval. A run still true at the saved input end is retained and flagged right-censored. All alerts inside its observed interval are eligible, including later/middle alerts. State membership is observable at close; a run's eventual end is evaluation metadata, not a trigger input or an early prediction.

Match on inclusive observed bar indices [start,end]. The first alert of each version catches that episode once. Later alerts of that version in the same episode count as repetitions. Disjoint episodes prevent an alert catching two. No before-state or outside-state alert contributes to scoring. Existing pulses are formed from full contiguous indicator history before state masking; never manufacture a fresh pulse because the state turns on.

Observed remaining movement is100×(maximum close from first alert through observed episode end / alert close−1), including the alert close. It can be zero; it is retrospective and is not a fill, net return or completed trade. No future horizon extends beyond the local day/observed episode. Financial container, exits, fill/tie rules and financial cost model: not measured — outside this phase.

| Earlier descriptive study | This registered stage |
|---|---|
| >=0.5%/60min rise events with false→true pulses and60min separation | Consecutive bars satisfying both rise and previous3h-high breakout form episodes |
| Overlapping breakout flag at accepted event | Breakout is a condition of every member bar |
| One observation timestamp per accepted event | Inclusive start/end supports alerts during the episode |
| Descriptive recurrence counts | Conditional detection coverage/timing, no full-stream precision |

## 7. Baselines

Include three explicit evaluation controls: an alert at every member bar; one at each episode's first bar; and no alerts. Episode-entry control is a contemporaneous membership baseline, not a predicted start before the price rise. All-member alerts trivially attain full coverage and demonstrate why positive-only coverage is not specificity.

For every version/month also draw the same number of selected alerts uniformly without replacement over member bars, using18102026 plus the first8 hexadecimal digits of SHA256(candidate_id). Record its conditional coverage. It is an evaluation timing control, never a live signal or a significance test. No full-stream no-signal success rate or financial breakeven rate can be estimated in this restricted sample; mark them not measured, not50%.

## 8. Grid and implementations

grid.json enumerates every evaluated ID, original family, origin, exact settings, definition ID, signal, asset, timing, provenance and original-row SHA256. The appendices embed all548 settings and all referenced original definitions, so there is no hidden rule name. definitions.json is also delivered for machine-readable audit.

The548 records are446 L0085 grid variants,45 older L0084 variants,30 L0088 variants,3 persistent OBV states,6 BTC price-recovery rules and18 BTC candle rules. Of the18 candle rules,6 are standalone and12 are registered candle/CCI confirmations. They are explicitly composites, not independent single indicators. They are inherited definitions, not a new all-pairs search. Aliases remain separate source IDs; do not count their common alerts as independent rises.

Use specialist.masks exactly. L0085 and legacy L0084 raw truths are converted false→true on the complete history, matching their singleton research emission. L0088, price recovery and candle routines already emit pulses. Persistent OBV states retain every true decision bar. Cross-up-through uses previous<threshold/current>=threshold; cross-above two series uses previous<=/current>. EMA uses adjust=False with alpha2/(n+1), minimum n nonmissing observations. Wilder smoothing uses alpha1/n and its imported first-observation seed, not an invented SMA seed. The older RSI/MFI zero-denominator behavior is NaN/no alert, not a silent100 replacement. Bollinger deviation is population ddof0. Preserve tie handling and pivot confirmation latency in the embedded definitions and pinned implementations.

These formulas were previously used on4h futures in other rounds. Applying the pinned formulas at15m on BTC spot is a newly scoped application; do not transfer their old performance or bury the original indicator family if this application is weak. Full parameter axes and other source records remain unmeasured, with reasons in the earlier coverage attachment and coverage_scope.json. Do not silently trim or expand this548-row run.

## 9. Splits

All seven months are descriptive discovery and are already inspected historical data. No holdout, blind future test, candidate replacement, validation or adoption occurs in this paper. Show each month separately. A later validation paper must freeze candidates and apply its own horizon/overlap embargo before reading its results. No present claim of out-of-sample performance.

## 10. Attempt budget

548 candidate records ×7 months =3836 candidate-month rows;3 baseline rows ×7 months =21; total3857 retained rows. Zero-alert rows remain. Per-version matched-count controls and1000 day-bootstrap draws are registered descriptive controls, not additional trading rules. There are no unregistered pairs/triples, no adaptive thresholds, no optimizing on a validation month and no peak-based winner selection. Since this paper makes no significance claim or automatic selection, it reports no p-values or multiplicity-corrected superiority. A later inferential search must register its correction before it begins.

## 11. Required statistics

For every candidate/month retain: episode count, member-bar count, selected alerts, caught/missed episodes, repeated alerts, coverage, first-alert indices, delays in bars, median delay, Wilson95% interval, day-bootstrap95% coverage interval, matched-count random conditional coverage and median observed remaining closing-price gain. Raw timestamp/close/state/alert evidence is mandatory. Coverage=episodes caught/episodes, not true alerts/all market alerts. Wilson intervals assume independence; bootstrap samples active local days with replacement,1000 draws and seed18102026, acknowledging the small number of months and conditional sample. No guarantees or invented probability of future profit.

Full-stream false alerts, precision, specificity, financial expectancy, MAE/MFE of trades, time-to-profit, costs and profit are not measured. Never output precision100% from the all-positive selection. No aggregate-only winner is prescribed; all rows and per-month differences are returned for Lead review.

## 12. Integrity checks

Before scoring each month the real path rechecks every candidate's prefix at two registered cuts: max(260,N//2) and N−20. Every one of the548 past masks must match full-history masks exactly. State labels are not arguments to masks(). Source input hashes/schema must pass. Unit checks include independent EMA20/ATR14/Bollinger20 calculations, future perturbation of all candidate inputs, accepted late alerts, duplicate accounting, day boundaries, missing signals and the two real time-column schemas. Additional scalar source comparisons cover30 L0088,3 OBV and18 candle records. Changing the state threshold from0.005 to0.5 must be detected by the state test.

The audit rebuilds alert membership and first matches using an independent per-bar loop for every row, verifies part hashes and keeps zeros. It does not independently certify every mathematical formula or the whole source catalogue; source-comparison checks are not an independent human reviewer. Preserve exact pass/fail/not-run evidence. On critical discrepancy stop the affected measurement and preserve its error; the executor does not repair code or alter criteria.

## 13. Acceptance criterion

Technical completion only:3857 rows, all seven registered months, all548 candidate IDs plus3 controls per month, zero missing IDs, zero mismatched independent-count rows, all required integrity tests passing, full report and raw evidence present, and every published blob verified at an immutable commit. No accuracy/coverage percentage gate and no financial adoption gate. This is not acceptance of a trading system. Independent Lead review remains pending.

## 14. Rejection criterion

A source mismatch, future leakage, duplicate/missing part, changed configuration on restart, output disagreement, scope expansion or false full-stream precision claim invalidates the affected measurement. An absent publishing capability blocks verified delivery; preserve safe local work and report the actual error. An unimplemented catalogue record is not a valid negative result. Do not lower checks to obtain completion.

## 15. Not measured

Other coins/states; full-stream false alarms or real-time state-gate quality; all remaining physical source records and indexed axis changes; new combinations and invention; frozen validation, safe-neighbourhood performance, future-market survival; trades, exits, order types, profit and live money. These remain explicitly unmeasured; nothing in this paper permits changing live code, locked engines, original archives or the constitution.

## 16. Deliverables and paths

Run directory: the extracted btc-specialist folder. Set NOVA_WORKSPACE to the absolute session workspace, not a smaller folder chosen to hide other files. No full repository clone. Destination results branch: agent/btc-state-specialist-results-2026-10-18. Destination root: history/research/hyp_lab_out/BTC-STATE-SPECIALIST-2026-10-18/. Code is stored under tools/btc_state_specialist/ on the prepared work branch agent/btc-state-specialist-2026-10-18. Never create a PR, merge or push to main.

Per-month MONTH.raw.json.gz contains timestamps, close prices, inclusive state_runs, state_mask and each candidate's selected-alert bit mask. Bit i means the saved completed bar i. It also records prefix-check count and right-censoring. MONTH.rows.json.gz retains all nested statistics and first-alert evidence. results.csv.gz has candidate_id,month,states,state_bars,alerts,caught,missed,repeated,coverage,median_delay_bars,median_remaining_close_gain_pct,matched_count_random_state_coverage,precision. checkpoint.json pins source/code fingerprint, month list and hashes. audit.json records the independent count audit. REPORT_AR.md retains the constitutional summary and all seven tables; financial fields say not measured — outside this phase.

Also deliver registration/grid/definitions/coverage/input/package manifests, requirements, readiness evidence, this paper, DELIVERY.json, EVIDENCE.zip, VERIFIED_DELIVERY.json and new dated journal entries with LOG/DECISIONS/HANDOFF updates. No secret or private owner source archive is included in a public upload.

## 17. Executor instructions and final reply

You are the executor, not another coordinator. Do not design, implement, repair, select candidates, change scope or adopt anything. Begin a task-start timestamp before setup, record total elapsed separately from compute time, and keep polling the same foreground worker to a known exit. Respect Retry-After; one worker and one publisher. Slow progress is not failure. A platform not_found is not an exit code: inspect checkpoint and OS process/lock state; if no worker remains, rerun the identical command on the identical output path. The file lock rejects concurrent workers. Completed parts are hash-verified and reused; mismatches stop rather than overwrite evidence.

The owner currently specifies the final reply as تم or فشل. Record the full actual error, attempted action, pending work and safe restart state in files; do not leak credentials. Reply تم only after real seven-month measurement, audit, report, remote payload readback and verified receipt upload/readback. Synthetic setup success or a draft upload is not completion. On a blocked completion reply فشل, preserving evidence. The Lead reads the named results branch and issues the independent judgment.

## 18. Runnable package — direct REST, no GitHub connector needed

CODE_COMMIT = cd161f8313cb2e3e135437f1e66109399b703272. This private transport update changes no calculation, grid, state, month, matching rule or result criterion. The original core package_manifest.json still verifies the calculation files. The additional helper is outside btc-specialist so it does not change the calculation fingerprint or invalidate a matching prior checkpoint.

Run every command below from the workspace root containing the two extracted folders btc-specialist and private-btc-executor. These are executor commands, not instructions for the owner's phone. They initialize access, stage the pinned data, run the fixed experiment and deliver it; retain process logs and return only the final completion word. No gh installation, local origin or GitHub connector is required. The helper calls only api.github.com for stevearagonno1/NOVA-DRAGON and permits work-branch writes only.

GH_TOKEN is supplied only in the private owner-to-executor paper/credentials.env. This public copy intentionally contains no token. The private initialization sets GH_TOKEN, PYTHONDONTWRITEBYTECODE=1 and NOVA_WORKSPACE to the full workspace root before these commands. Do not upload the private initialization or private bundle.

Record a task-start epoch before setup and never reset it on restart. Use this tested setup command:

python -c "import pathlib,json,time; p=pathlib.Path('private-btc-executor/TASK_START.json'); p.exists() or p.write_text(json.dumps({'task_started_epoch':time.time()}))"

For a resumed older attempt whose original start was never captured, this timestamp covers the resumed session only; do not invent the older total. Set PYTHONDONTWRITEBYTECODE=1 and NOVA_WORKSPACE to the actual complete workspace root. Do not print GH_TOKEN, use shell tracing, or serialize the environment into logs.

Execute in this order, keeping the same folders/checkpoints if prior work exists:

1. Verify core hashes in btc-specialist/package_manifest.json. Use Python3.12/POSIX with numpy2.3.5 and pandas2.2.3. Install the pinned requirements only if absent; do not alter versions or code. Run python btc-specialist/test_specialist.py.
2. Run python private-btc-executor/rest_publish.py probe --package btc-specialist --out private-btc-executor/checks. This checks the actual host/token using two harmless nonfinancial work-branch files and immutable readback. The prepared route already passed at c0f226d45e4a268e2b7b78582d25a0eb659c5ef9, but current host access still must work. If it fails, preserve checks/REST_ERROR.json; do not ask for a connector as a prerequisite.
3. Run python private-btc-executor/rest_publish.py inputs --package btc-specialist. It fetches exactly the seven pinned source files through REST and verifies byte lengths/SHA256; existing valid files are reused. Run python btc-specialist/stage_inputs.py check.
4. Run python btc-specialist/specialist.py fixture --out btc-specialist/readiness-executor --stop-after 1, then python btc-specialist/specialist.py fixture --out btc-specialist/readiness-executor, then python btc-specialist/specialist.py audit --out btc-specialist/readiness-executor. This is a setup test, not market completion.
5. Run python btc-specialist/specialist.py measure --out btc-specialist/market. Keep polling the same process to a known exit; save stdout/stderr. Resume the identical command only after confirming no worker holds the lock. Do not delete or rerun completed parts from scratch. Run python btc-specialist/specialist.py audit --out btc-specialist/market.
6. Run python private-btc-executor/rest_publish.py publish --package btc-specialist --out btc-specialist/market --started private-btc-executor/TASK_START.json. It creates the authorized results branch from the pinned calculation code if needed, reads the actual branch documents, builds the prepared public payload, uploads it, verifies every blob at the actual immutable commit, publishes the verified receipt and execution tick, reads them back, and records COMPLETION.json. The helper rejects actual token material in plain files and compressed ZIP entries before upload. No private credentials or private paper are included in delivery.py's public payload.

Results branch: agent/btc-state-specialist-results-2026-10-18. Result root: history/research/hyp_lab_out/BTC-STATE-SPECIALIST-2026-10-18/. REST_UPLOAD_STATE.json preserves payload/receipt commit checkpoints. Repeating the publish command resumes that state; no force updates or scope changes. A lost final receipt response can be recovered only after comparing the actual remote receipt/payload identity.

The final word تم is permitted only after the actual seven-month measurement,3857-row audit, report and verified remote receipt. A synthetic fixture, probe or local-only calculation is not completion. If blocked, preserve the actual error, logs and partial files and reply exactly فشل. Do not propose options or ask to authorize an already authorized stage.

## 19. Readiness evidence

Read readiness.json and reference_checks.json for actual commands and limits. The prepared code path was tested on420 synthetic bars through measurement, all551 conditional result rows, checkpoint stop/resume, independent count audit, full report generation and publishing-payload construction. A separate uninterrupted fixture is compared with the resumed one. Numerical source comparisons and independent recurrences are separately identified; no synthetic result is called market performance. Eight unit tests pass. Actual staged source bytes are rehashed before resume and audit, not merely their manifest. Seven pinned market inputs were checked only for identity/schema, not scored by the Lead. A small real work-branch upload/readback confirms the connector route; a local synthetic transport check does not replace it.

## 20. Storage, errors and authority

Whole workspace ceiling125000000 bytes, checked before writes, downloads and final delivery. Inputs total about2.15MB compressed, source package is small; actual final sizes are recorded, estimates are not passed checks. Preserve historical evidence and owner files; no deletion to force a pass. The owner separately authorized deletion of generated caches and two previously delivered duplicate local ZIPs on2026-10-18; that is not blanket cleanup permission for this executor.

A critical integrity defect stops measurement; preserve error/partial files and let the Lead repair. Transport failure blocks remote completion but does not invalidate safe local arithmetic. No PR/main merge, live account operation, locked-code change or source-data rewrite. Write new ticks, append decisions/LOG and update handoff with scope, code/result references, actual checks, limits and Lead-review-pending status. Record total task duration including setup, waits and upload; compute-only duration is separate. No metric is guessed and no future work is described as completed.

## Appendix A — exact input paths and identities

| الشهر | ملف المستودع عند8af2aae | الحجم المضغوط بالبايت | SHA256 |
|---|---|---|---|
| 2021-12 | [history/research/hyp_lab_out/BTC-INTRADAY-2026-10-17/btc-seven-month-study/2021-12/bars15m.csv.gz](https://github.com/stevearagonno1/NOVA-DRAGON/blob/8af2aae214f65a370110921928eaabf07771a6d1/history/research/hyp_lab_out/BTC-INTRADAY-2026-10-17/btc-seven-month-study/2021-12/bars15m.csv.gz) | 328775 | 9a19b0df029919dad5d2fb3c4050f58fb957ecaf5f74a92562d3af2c221f791c |
| 2023-05 | [history/research/hyp_lab_out/BTC-INTRADAY-2026-10-17/btc-seven-month-study/2023-05/bars15m.csv.gz](https://github.com/stevearagonno1/NOVA-DRAGON/blob/8af2aae214f65a370110921928eaabf07771a6d1/history/research/hyp_lab_out/BTC-INTRADAY-2026-10-17/btc-seven-month-study/2023-05/bars15m.csv.gz) | 323044 | 2880b20c59e6567a6d014ca01b04d5460bfac68c30894fd9bebf20dd3f251d6f |
| 2023-12 | [history/research/hyp_lab_out/BTC-INTRADAY-2026-10-17/btc-seven-month-study/2023-12/bars15m.csv.gz](https://github.com/stevearagonno1/NOVA-DRAGON/blob/8af2aae214f65a370110921928eaabf07771a6d1/history/research/hyp_lab_out/BTC-INTRADAY-2026-10-17/btc-seven-month-study/2023-12/bars15m.csv.gz) | 324926 | 0c8ac3dfd2ab2586a36f472993fcd934be1479698fbe029f45414819217c3706 |
| 2024-01 | [history/research/hyp_lab_out/BTC-INTRADAY-2026-10-17/btc-month-study/bars15m.csv.gz](https://github.com/stevearagonno1/NOVA-DRAGON/blob/8af2aae214f65a370110921928eaabf07771a6d1/history/research/hyp_lab_out/BTC-INTRADAY-2026-10-17/btc-month-study/bars15m.csv.gz) | 257692 | 61089ea15afbe6cb61a8a11384ae12317bfe7b2c50c802167681f0244d732aa4 |
| 2025-05 | [history/research/hyp_lab_out/BTC-INTRADAY-2026-10-17/btc-seven-month-study/2025-05/bars15m.csv.gz](https://github.com/stevearagonno1/NOVA-DRAGON/blob/8af2aae214f65a370110921928eaabf07771a6d1/history/research/hyp_lab_out/BTC-INTRADAY-2026-10-17/btc-seven-month-study/2025-05/bars15m.csv.gz) | 322951 | 4c33bd0952350c154c032945dd2dd7632ab8a5384a9139a8cfae27ac30650a52 |
| 2025-12 | [history/research/hyp_lab_out/BTC-INTRADAY-2026-10-17/btc-month-comparison/bars15m.csv.gz](https://github.com/stevearagonno1/NOVA-DRAGON/blob/8af2aae214f65a370110921928eaabf07771a6d1/history/research/hyp_lab_out/BTC-INTRADAY-2026-10-17/btc-month-comparison/bars15m.csv.gz) | 257649 | 8a2aec6656356ab6c31dd597646ccdfe1a66ca3e7b2c2e06563a0c3db6eadf9b |
| 2026-03 | [history/research/hyp_lab_out/BTC-INTRADAY-2026-10-17/btc-seven-month-study/2026-03/bars15m.csv.gz](https://github.com/stevearagonno1/NOVA-DRAGON/blob/8af2aae214f65a370110921928eaabf07771a6d1/history/research/hyp_lab_out/BTC-INTRADAY-2026-10-17/btc-seven-month-study/2026-03/bars15m.csv.gz) | 330189 | e8bb16789b0e2c1b7518113c3a99c5f6856380ad5f24f5196a145cc577ee59df |

## Appendix B — all registered version records

| ID | Origin / family | Exact settings | Definition | Emission / asset |
|---|---|---|---|---|
| V-0004300 | registered_L0085_setting / AROON | {"n": 14} | DEF-2d73dd02c356d7d5 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004301 | registered_L0085_setting / AROON | {"n": 21} | DEF-2d73dd02c356d7d5 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004302 | registered_L0085_setting / AROON | {"n": 25} | DEF-2d73dd02c356d7d5 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004303 | registered_L0085_setting / AROON | {"n": 50} | DEF-2d73dd02c356d7d5 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004304 | registered_L0085_setting / AROON | {"n": 7} | DEF-2d73dd02c356d7d5 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004305 | registered_L0085_setting / BB | {"k": 1.5, "n": 10} | DEF-7db3e0575bc7d1c8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004306 | registered_L0085_setting / BB | {"k": 2, "n": 10} | DEF-7db3e0575bc7d1c8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004307 | registered_L0085_setting / BB | {"k": 2.5, "n": 10} | DEF-7db3e0575bc7d1c8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004308 | registered_L0085_setting / BB | {"k": 3, "n": 10} | DEF-7db3e0575bc7d1c8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004309 | registered_L0085_setting / BB | {"k": 1.5, "n": 20} | DEF-7db3e0575bc7d1c8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004310 | registered_L0085_setting / BB | {"k": 2, "n": 20} | DEF-7db3e0575bc7d1c8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004311 | registered_L0085_setting / BB | {"k": 2.5, "n": 20} | DEF-7db3e0575bc7d1c8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004312 | registered_L0085_setting / BB | {"k": 3, "n": 20} | DEF-7db3e0575bc7d1c8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004313 | registered_L0085_setting / BB | {"k": 1.5, "n": 30} | DEF-7db3e0575bc7d1c8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004314 | registered_L0085_setting / BB | {"k": 2, "n": 30} | DEF-7db3e0575bc7d1c8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004315 | registered_L0085_setting / BB | {"k": 2.5, "n": 30} | DEF-7db3e0575bc7d1c8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004316 | registered_L0085_setting / BB | {"k": 3, "n": 30} | DEF-7db3e0575bc7d1c8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004317 | registered_L0085_setting / BB | {"k": 1.5, "n": 50} | DEF-7db3e0575bc7d1c8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004318 | registered_L0085_setting / BB | {"k": 2, "n": 50} | DEF-7db3e0575bc7d1c8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004319 | registered_L0085_setting / BB | {"k": 2.5, "n": 50} | DEF-7db3e0575bc7d1c8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004320 | registered_L0085_setting / BB | {"k": 3, "n": 50} | DEF-7db3e0575bc7d1c8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004321 | registered_L0085_setting / BOS | {"look": 10, "n": 10} | DEF-311e07cf1274e7cd | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004322 | registered_L0085_setting / BOS | {"look": 20, "n": 10} | DEF-311e07cf1274e7cd | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004323 | registered_L0085_setting / BOS | {"look": 40, "n": 10} | DEF-311e07cf1274e7cd | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004324 | registered_L0085_setting / BOS | {"look": 10, "n": 3} | DEF-311e07cf1274e7cd | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004325 | registered_L0085_setting / BOS | {"look": 20, "n": 3} | DEF-311e07cf1274e7cd | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004326 | registered_L0085_setting / BOS | {"look": 40, "n": 3} | DEF-311e07cf1274e7cd | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004327 | registered_L0085_setting / BOS | {"look": 10, "n": 5} | DEF-311e07cf1274e7cd | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004328 | registered_L0085_setting / BOS | {"look": 20, "n": 5} | DEF-311e07cf1274e7cd | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004329 | registered_L0085_setting / BOS | {"look": 40, "n": 5} | DEF-311e07cf1274e7cd | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004330 | registered_L0085_setting / CCI | {"n": 10, "t": -100} | DEF-7c477eea1de8ef48 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004331 | registered_L0085_setting / CCI | {"n": 10, "t": -150} | DEF-7c477eea1de8ef48 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004332 | registered_L0085_setting / CCI | {"n": 10, "t": -50} | DEF-7c477eea1de8ef48 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004333 | registered_L0085_setting / CCI | {"n": 14, "t": -100} | DEF-7c477eea1de8ef48 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004334 | registered_L0085_setting / CCI | {"n": 14, "t": -150} | DEF-7c477eea1de8ef48 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004335 | registered_L0085_setting / CCI | {"n": 14, "t": -50} | DEF-7c477eea1de8ef48 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004336 | registered_L0085_setting / CCI | {"n": 21, "t": -100} | DEF-7c477eea1de8ef48 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004337 | registered_L0085_setting / CCI | {"n": 21, "t": -150} | DEF-7c477eea1de8ef48 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004338 | registered_L0085_setting / CCI | {"n": 21, "t": -50} | DEF-7c477eea1de8ef48 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004339 | registered_L0085_setting / CCI | {"n": 28, "t": -100} | DEF-7c477eea1de8ef48 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004340 | registered_L0085_setting / CCI | {"n": 28, "t": -150} | DEF-7c477eea1de8ef48 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004341 | registered_L0085_setting / CCI | {"n": 28, "t": -50} | DEF-7c477eea1de8ef48 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004342 | registered_L0085_setting / CCI | {"n": 7, "t": -100} | DEF-7c477eea1de8ef48 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004343 | registered_L0085_setting / CCI | {"n": 7, "t": -150} | DEF-7c477eea1de8ef48 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004344 | registered_L0085_setting / CCI | {"n": 7, "t": -50} | DEF-7c477eea1de8ef48 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004345 | registered_L0085_setting / CMF | {"n": 10, "t": 0} | DEF-2dcf9f06b0b67c07 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004346 | registered_L0085_setting / CMF | {"n": 10, "t": 0.05} | DEF-2dcf9f06b0b67c07 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004347 | registered_L0085_setting / CMF | {"n": 10, "t": 0.1} | DEF-2dcf9f06b0b67c07 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004348 | registered_L0085_setting / CMF | {"n": 14, "t": 0} | DEF-2dcf9f06b0b67c07 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004349 | registered_L0085_setting / CMF | {"n": 14, "t": 0.05} | DEF-2dcf9f06b0b67c07 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004350 | registered_L0085_setting / CMF | {"n": 14, "t": 0.1} | DEF-2dcf9f06b0b67c07 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004351 | registered_L0085_setting / CMF | {"n": 20, "t": 0} | DEF-2dcf9f06b0b67c07 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004352 | registered_L0085_setting / CMF | {"n": 20, "t": 0.05} | DEF-2dcf9f06b0b67c07 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004353 | registered_L0085_setting / CMF | {"n": 20, "t": 0.1} | DEF-2dcf9f06b0b67c07 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004354 | registered_L0085_setting / CMF | {"n": 30, "t": 0} | DEF-2dcf9f06b0b67c07 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004355 | registered_L0085_setting / CMF | {"n": 30, "t": 0.05} | DEF-2dcf9f06b0b67c07 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004356 | registered_L0085_setting / CMF | {"n": 30, "t": 0.1} | DEF-2dcf9f06b0b67c07 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004357 | registered_L0085_setting / CMF | {"n": 50, "t": 0} | DEF-2dcf9f06b0b67c07 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004358 | registered_L0085_setting / CMF | {"n": 50, "t": 0.05} | DEF-2dcf9f06b0b67c07 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004359 | registered_L0085_setting / CMF | {"n": 50, "t": 0.1} | DEF-2dcf9f06b0b67c07 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004360 | registered_L0085_setting / DIV_MACD | {"look": 20, "right": 2} | DEF-42a338e665f5c5e5 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004361 | registered_L0085_setting / DIV_MACD | {"look": 20, "right": 3} | DEF-42a338e665f5c5e5 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004362 | registered_L0085_setting / DIV_MACD | {"look": 40, "right": 2} | DEF-42a338e665f5c5e5 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004363 | registered_L0085_setting / DIV_MACD | {"look": 40, "right": 3} | DEF-42a338e665f5c5e5 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004364 | registered_L0085_setting / DIV_MACD | {"look": 60, "right": 2} | DEF-42a338e665f5c5e5 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004365 | registered_L0085_setting / DIV_MACD | {"look": 60, "right": 3} | DEF-42a338e665f5c5e5 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004366 | registered_L0085_setting / DIV_OBV | {"look": 20, "right": 2} | DEF-f3ab1ae9536994ac | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004367 | registered_L0085_setting / DIV_OBV | {"look": 20, "right": 3} | DEF-f3ab1ae9536994ac | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004368 | registered_L0085_setting / DIV_OBV | {"look": 40, "right": 2} | DEF-f3ab1ae9536994ac | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004369 | registered_L0085_setting / DIV_OBV | {"look": 40, "right": 3} | DEF-f3ab1ae9536994ac | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004370 | registered_L0085_setting / DIV_OBV | {"look": 60, "right": 2} | DEF-f3ab1ae9536994ac | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004371 | registered_L0085_setting / DIV_OBV | {"look": 60, "right": 3} | DEF-f3ab1ae9536994ac | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004372 | registered_L0085_setting / DIV_RSI | {"look": 20, "right": 2} | DEF-1f8fbb11d59afc04 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004373 | registered_L0085_setting / DIV_RSI | {"look": 20, "right": 3} | DEF-1f8fbb11d59afc04 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004374 | registered_L0085_setting / DIV_RSI | {"look": 40, "right": 2} | DEF-1f8fbb11d59afc04 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004375 | registered_L0085_setting / DIV_RSI | {"look": 40, "right": 3} | DEF-1f8fbb11d59afc04 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004376 | registered_L0085_setting / DIV_RSI | {"look": 60, "right": 2} | DEF-1f8fbb11d59afc04 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004377 | registered_L0085_setting / DIV_RSI | {"look": 60, "right": 3} | DEF-1f8fbb11d59afc04 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004384 | registered_L0085_setting / DMI | {"n": 14, "t": 15} | DEF-46fa966c949d7bf6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004385 | registered_L0085_setting / DMI | {"n": 14, "t": 20} | DEF-46fa966c949d7bf6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004386 | registered_L0085_setting / DMI | {"n": 14, "t": 25} | DEF-46fa966c949d7bf6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004387 | registered_L0085_setting / DMI | {"n": 14, "t": 30} | DEF-46fa966c949d7bf6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004388 | registered_L0085_setting / DMI | {"n": 21, "t": 15} | DEF-46fa966c949d7bf6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004389 | registered_L0085_setting / DMI | {"n": 21, "t": 20} | DEF-46fa966c949d7bf6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004390 | registered_L0085_setting / DMI | {"n": 21, "t": 25} | DEF-46fa966c949d7bf6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004391 | registered_L0085_setting / DMI | {"n": 21, "t": 30} | DEF-46fa966c949d7bf6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004392 | registered_L0085_setting / DMI | {"n": 7, "t": 15} | DEF-46fa966c949d7bf6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004393 | registered_L0085_setting / DMI | {"n": 7, "t": 20} | DEF-46fa966c949d7bf6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004394 | registered_L0085_setting / DMI | {"n": 7, "t": 25} | DEF-46fa966c949d7bf6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004395 | registered_L0085_setting / DMI | {"n": 7, "t": 30} | DEF-46fa966c949d7bf6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004396 | registered_L0085_setting / DONCHIAN_BREAK | {"n": 10} | DEF-afb6526f76afaf79 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004397 | registered_L0085_setting / DONCHIAN_BREAK | {"n": 20} | DEF-afb6526f76afaf79 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004398 | registered_L0085_setting / DONCHIAN_BREAK | {"n": 40} | DEF-afb6526f76afaf79 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004399 | registered_L0085_setting / DONCHIAN_BREAK | {"n": 5} | DEF-afb6526f76afaf79 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004400 | registered_L0085_setting / DONCHIAN_BREAK | {"n": 55} | DEF-afb6526f76afaf79 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004401 | registered_L0085_setting / DONCHIAN_FAIL | {"n": 10} | DEF-e77a6f975b62cdb0 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004402 | registered_L0085_setting / DONCHIAN_FAIL | {"n": 20} | DEF-e77a6f975b62cdb0 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004403 | registered_L0085_setting / DONCHIAN_FAIL | {"n": 40} | DEF-e77a6f975b62cdb0 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004404 | registered_L0085_setting / DONCHIAN_FAIL | {"n": 55} | DEF-e77a6f975b62cdb0 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004405 | registered_L0085_setting / EMA | {"fast": 10, "slow": 100} | DEF-95296421f35e5003 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004406 | registered_L0085_setting / EMA | {"fast": 10, "slow": 20} | DEF-95296421f35e5003 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004407 | registered_L0085_setting / EMA | {"fast": 10, "slow": 200} | DEF-95296421f35e5003 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004408 | registered_L0085_setting / EMA | {"fast": 10, "slow": 30} | DEF-95296421f35e5003 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004409 | registered_L0085_setting / EMA | {"fast": 10, "slow": 50} | DEF-95296421f35e5003 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004410 | registered_L0085_setting / EMA | {"fast": 20, "slow": 100} | DEF-95296421f35e5003 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004411 | registered_L0085_setting / EMA | {"fast": 20, "slow": 200} | DEF-95296421f35e5003 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004412 | registered_L0085_setting / EMA | {"fast": 20, "slow": 30} | DEF-95296421f35e5003 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004413 | registered_L0085_setting / EMA | {"fast": 20, "slow": 50} | DEF-95296421f35e5003 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004414 | registered_L0085_setting / EMA | {"fast": 50, "slow": 100} | DEF-95296421f35e5003 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004415 | registered_L0085_setting / EMA | {"fast": 50, "slow": 200} | DEF-95296421f35e5003 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004416 | registered_L0085_setting / EMA | {"fast": 5, "slow": 100} | DEF-95296421f35e5003 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004417 | registered_L0085_setting / EMA | {"fast": 5, "slow": 20} | DEF-95296421f35e5003 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004418 | registered_L0085_setting / EMA | {"fast": 5, "slow": 200} | DEF-95296421f35e5003 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004419 | registered_L0085_setting / EMA | {"fast": 5, "slow": 30} | DEF-95296421f35e5003 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004420 | registered_L0085_setting / EMA | {"fast": 5, "slow": 50} | DEF-95296421f35e5003 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004421 | registered_L0085_setting / ENGULF | {"bottom": 10} | DEF-d8db39e18c56de13 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004422 | registered_L0085_setting / ENGULF | {"bottom": 3} | DEF-d8db39e18c56de13 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004423 | registered_L0085_setting / ENGULF | {"bottom": 5} | DEF-d8db39e18c56de13 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004424 | registered_L0085_setting / FORCE | {"n": 13} | DEF-a76277fe5b107c2a | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004425 | registered_L0085_setting / FORCE | {"n": 2} | DEF-a76277fe5b107c2a | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004426 | registered_L0085_setting / FORCE | {"n": 21} | DEF-a76277fe5b107c2a | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004427 | registered_L0085_setting / FORCE | {"n": 7} | DEF-a76277fe5b107c2a | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004428 | registered_L0085_setting / FVG | {"gap": 0} | DEF-9421265064ad85be | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004429 | registered_L0085_setting / FVG | {"gap": 0.1} | DEF-9421265064ad85be | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004430 | registered_L0085_setting / FVG | {"gap": 0.25} | DEF-9421265064ad85be | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004431 | registered_L0085_setting / FVG | {"gap": 0.5} | DEF-9421265064ad85be | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004432 | registered_L0085_setting / HAMMER | {"bottom": 10, "lower": 1.5, "upper": 0.25} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004433 | registered_L0085_setting / HAMMER | {"bottom": 3, "lower": 1.5, "upper": 0.25} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004434 | registered_L0085_setting / HAMMER | {"bottom": 5, "lower": 1.5, "upper": 0.25} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004435 | registered_L0085_setting / HAMMER | {"bottom": 10, "lower": 1.5, "upper": 0.5} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004436 | registered_L0085_setting / HAMMER | {"bottom": 3, "lower": 1.5, "upper": 0.5} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004437 | registered_L0085_setting / HAMMER | {"bottom": 5, "lower": 1.5, "upper": 0.5} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004438 | registered_L0085_setting / HAMMER | {"bottom": 10, "lower": 1.5, "upper": 1} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004439 | registered_L0085_setting / HAMMER | {"bottom": 3, "lower": 1.5, "upper": 1} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004440 | registered_L0085_setting / HAMMER | {"bottom": 5, "lower": 1.5, "upper": 1} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004441 | registered_L0085_setting / HAMMER | {"bottom": 10, "lower": 2, "upper": 0.25} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004442 | registered_L0085_setting / HAMMER | {"bottom": 3, "lower": 2, "upper": 0.25} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004443 | registered_L0085_setting / HAMMER | {"bottom": 5, "lower": 2, "upper": 0.25} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004444 | registered_L0085_setting / HAMMER | {"bottom": 10, "lower": 2, "upper": 0.5} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004445 | registered_L0085_setting / HAMMER | {"bottom": 3, "lower": 2, "upper": 0.5} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004446 | registered_L0085_setting / HAMMER | {"bottom": 5, "lower": 2, "upper": 0.5} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004447 | registered_L0085_setting / HAMMER | {"bottom": 10, "lower": 2, "upper": 1} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004448 | registered_L0085_setting / HAMMER | {"bottom": 3, "lower": 2, "upper": 1} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004449 | registered_L0085_setting / HAMMER | {"bottom": 5, "lower": 2, "upper": 1} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004450 | registered_L0085_setting / HAMMER | {"bottom": 10, "lower": 3, "upper": 0.25} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004451 | registered_L0085_setting / HAMMER | {"bottom": 3, "lower": 3, "upper": 0.25} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004452 | registered_L0085_setting / HAMMER | {"bottom": 5, "lower": 3, "upper": 0.25} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004453 | registered_L0085_setting / HAMMER | {"bottom": 10, "lower": 3, "upper": 0.5} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004454 | registered_L0085_setting / HAMMER | {"bottom": 3, "lower": 3, "upper": 0.5} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004455 | registered_L0085_setting / HAMMER | {"bottom": 5, "lower": 3, "upper": 0.5} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004456 | registered_L0085_setting / HAMMER | {"bottom": 10, "lower": 3, "upper": 1} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004457 | registered_L0085_setting / HAMMER | {"bottom": 3, "lower": 3, "upper": 1} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004458 | registered_L0085_setting / HAMMER | {"bottom": 5, "lower": 3, "upper": 1} | DEF-4927c79acae44c61 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004459 | registered_L0085_setting / KELTNER | {"k": 1, "n": 10} | DEF-534271228b4a59e9 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004460 | registered_L0085_setting / KELTNER | {"k": 1.5, "n": 10} | DEF-534271228b4a59e9 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004461 | registered_L0085_setting / KELTNER | {"k": 2, "n": 10} | DEF-534271228b4a59e9 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004462 | registered_L0085_setting / KELTNER | {"k": 2.5, "n": 10} | DEF-534271228b4a59e9 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004463 | registered_L0085_setting / KELTNER | {"k": 1, "n": 20} | DEF-534271228b4a59e9 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004464 | registered_L0085_setting / KELTNER | {"k": 1.5, "n": 20} | DEF-534271228b4a59e9 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004465 | registered_L0085_setting / KELTNER | {"k": 2, "n": 20} | DEF-534271228b4a59e9 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004466 | registered_L0085_setting / KELTNER | {"k": 2.5, "n": 20} | DEF-534271228b4a59e9 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004467 | registered_L0085_setting / KELTNER | {"k": 1, "n": 30} | DEF-534271228b4a59e9 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004468 | registered_L0085_setting / KELTNER | {"k": 1.5, "n": 30} | DEF-534271228b4a59e9 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004469 | registered_L0085_setting / KELTNER | {"k": 2, "n": 30} | DEF-534271228b4a59e9 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004470 | registered_L0085_setting / KELTNER | {"k": 2.5, "n": 30} | DEF-534271228b4a59e9 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004471 | registered_L0085_setting / KELTNER | {"k": 1, "n": 50} | DEF-534271228b4a59e9 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004472 | registered_L0085_setting / KELTNER | {"k": 1.5, "n": 50} | DEF-534271228b4a59e9 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004473 | registered_L0085_setting / KELTNER | {"k": 2, "n": 50} | DEF-534271228b4a59e9 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004474 | registered_L0085_setting / KELTNER | {"k": 2.5, "n": 50} | DEF-534271228b4a59e9 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004475 | registered_L0085_setting / MACD | {"fast": 12, "signal": 5, "slow": 21} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004476 | registered_L0085_setting / MACD | {"fast": 12, "signal": 9, "slow": 21} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004477 | registered_L0085_setting / MACD | {"fast": 12, "signal": 5, "slow": 26} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004478 | registered_L0085_setting / MACD | {"fast": 12, "signal": 9, "slow": 26} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004479 | registered_L0085_setting / MACD | {"fast": 12, "signal": 5, "slow": 35} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004480 | registered_L0085_setting / MACD | {"fast": 12, "signal": 9, "slow": 35} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004481 | registered_L0085_setting / MACD | {"fast": 12, "signal": 5, "slow": 39} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004482 | registered_L0085_setting / MACD | {"fast": 12, "signal": 9, "slow": 39} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004483 | registered_L0085_setting / MACD | {"fast": 19, "signal": 5, "slow": 21} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004484 | registered_L0085_setting / MACD | {"fast": 19, "signal": 9, "slow": 21} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004485 | registered_L0085_setting / MACD | {"fast": 19, "signal": 5, "slow": 26} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004486 | registered_L0085_setting / MACD | {"fast": 19, "signal": 9, "slow": 26} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004487 | registered_L0085_setting / MACD | {"fast": 19, "signal": 5, "slow": 35} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004488 | registered_L0085_setting / MACD | {"fast": 19, "signal": 9, "slow": 35} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004489 | registered_L0085_setting / MACD | {"fast": 19, "signal": 5, "slow": 39} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004490 | registered_L0085_setting / MACD | {"fast": 19, "signal": 9, "slow": 39} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004491 | registered_L0085_setting / MACD | {"fast": 5, "signal": 5, "slow": 21} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004492 | registered_L0085_setting / MACD | {"fast": 5, "signal": 9, "slow": 21} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004493 | registered_L0085_setting / MACD | {"fast": 5, "signal": 5, "slow": 26} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004494 | registered_L0085_setting / MACD | {"fast": 5, "signal": 9, "slow": 26} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004495 | registered_L0085_setting / MACD | {"fast": 5, "signal": 5, "slow": 35} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004496 | registered_L0085_setting / MACD | {"fast": 5, "signal": 9, "slow": 35} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004497 | registered_L0085_setting / MACD | {"fast": 5, "signal": 5, "slow": 39} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004498 | registered_L0085_setting / MACD | {"fast": 5, "signal": 9, "slow": 39} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004499 | registered_L0085_setting / MACD | {"fast": 8, "signal": 5, "slow": 21} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004500 | registered_L0085_setting / MACD | {"fast": 8, "signal": 9, "slow": 21} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004501 | registered_L0085_setting / MACD | {"fast": 8, "signal": 5, "slow": 26} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004502 | registered_L0085_setting / MACD | {"fast": 8, "signal": 9, "slow": 26} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004503 | registered_L0085_setting / MACD | {"fast": 8, "signal": 5, "slow": 35} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004504 | registered_L0085_setting / MACD | {"fast": 8, "signal": 9, "slow": 35} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004505 | registered_L0085_setting / MACD | {"fast": 8, "signal": 5, "slow": 39} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004506 | registered_L0085_setting / MACD | {"fast": 8, "signal": 9, "slow": 39} | DEF-9450d3b5ba89a76c | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004507 | registered_L0085_setting / MFI | {"form": "cross", "n": 10, "t": 15} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004508 | registered_L0085_setting / MFI | {"form": "state", "n": 10, "t": 15} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004509 | registered_L0085_setting / MFI | {"form": "cross", "n": 10, "t": 20} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004510 | registered_L0085_setting / MFI | {"form": "state", "n": 10, "t": 20} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004511 | registered_L0085_setting / MFI | {"form": "cross", "n": 10, "t": 25} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004512 | registered_L0085_setting / MFI | {"form": "state", "n": 10, "t": 25} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004513 | registered_L0085_setting / MFI | {"form": "cross", "n": 10, "t": 30} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004514 | registered_L0085_setting / MFI | {"form": "state", "n": 10, "t": 30} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004515 | registered_L0085_setting / MFI | {"form": "cross", "n": 14, "t": 15} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004516 | registered_L0085_setting / MFI | {"form": "state", "n": 14, "t": 15} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004517 | registered_L0085_setting / MFI | {"form": "cross", "n": 14, "t": 20} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004518 | registered_L0085_setting / MFI | {"form": "state", "n": 14, "t": 20} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004519 | registered_L0085_setting / MFI | {"form": "cross", "n": 14, "t": 25} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004520 | registered_L0085_setting / MFI | {"form": "state", "n": 14, "t": 25} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004521 | registered_L0085_setting / MFI | {"form": "cross", "n": 14, "t": 30} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004522 | registered_L0085_setting / MFI | {"form": "state", "n": 14, "t": 30} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004523 | registered_L0085_setting / MFI | {"form": "cross", "n": 21, "t": 15} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004524 | registered_L0085_setting / MFI | {"form": "state", "n": 21, "t": 15} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004525 | registered_L0085_setting / MFI | {"form": "cross", "n": 21, "t": 20} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004526 | registered_L0085_setting / MFI | {"form": "state", "n": 21, "t": 20} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004527 | registered_L0085_setting / MFI | {"form": "cross", "n": 21, "t": 25} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004528 | registered_L0085_setting / MFI | {"form": "state", "n": 21, "t": 25} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004529 | registered_L0085_setting / MFI | {"form": "cross", "n": 21, "t": 30} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004530 | registered_L0085_setting / MFI | {"form": "state", "n": 21, "t": 30} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004531 | registered_L0085_setting / MFI | {"form": "cross", "n": 28, "t": 15} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004532 | registered_L0085_setting / MFI | {"form": "state", "n": 28, "t": 15} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004533 | registered_L0085_setting / MFI | {"form": "cross", "n": 28, "t": 20} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004534 | registered_L0085_setting / MFI | {"form": "state", "n": 28, "t": 20} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004535 | registered_L0085_setting / MFI | {"form": "cross", "n": 28, "t": 25} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004536 | registered_L0085_setting / MFI | {"form": "state", "n": 28, "t": 25} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004537 | registered_L0085_setting / MFI | {"form": "cross", "n": 28, "t": 30} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004538 | registered_L0085_setting / MFI | {"form": "state", "n": 28, "t": 30} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004539 | registered_L0085_setting / MFI | {"form": "cross", "n": 7, "t": 15} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004540 | registered_L0085_setting / MFI | {"form": "state", "n": 7, "t": 15} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004541 | registered_L0085_setting / MFI | {"form": "cross", "n": 7, "t": 20} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004542 | registered_L0085_setting / MFI | {"form": "state", "n": 7, "t": 20} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004543 | registered_L0085_setting / MFI | {"form": "cross", "n": 7, "t": 25} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004544 | registered_L0085_setting / MFI | {"form": "state", "n": 7, "t": 25} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004545 | registered_L0085_setting / MFI | {"form": "cross", "n": 7, "t": 30} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004546 | registered_L0085_setting / MFI | {"form": "state", "n": 7, "t": 30} | DEF-d0c28a7ff8b0b063 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004547 | registered_L0085_setting / PXEMA | {"n": 10} | DEF-65548741fb006754 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004548 | registered_L0085_setting / PXEMA | {"n": 100} | DEF-65548741fb006754 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004549 | registered_L0085_setting / PXEMA | {"n": 20} | DEF-65548741fb006754 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004550 | registered_L0085_setting / PXEMA | {"n": 200} | DEF-65548741fb006754 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004551 | registered_L0085_setting / PXEMA | {"n": 30} | DEF-65548741fb006754 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004552 | registered_L0085_setting / PXEMA | {"n": 50} | DEF-65548741fb006754 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004553 | registered_L0085_setting / RSI | {"form": "cross", "n": 10, "t": 15} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004554 | registered_L0085_setting / RSI | {"form": "state", "n": 10, "t": 15} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004555 | registered_L0085_setting / RSI | {"form": "cross", "n": 10, "t": 20} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004556 | registered_L0085_setting / RSI | {"form": "state", "n": 10, "t": 20} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004557 | registered_L0085_setting / RSI | {"form": "cross", "n": 10, "t": 25} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004558 | registered_L0085_setting / RSI | {"form": "state", "n": 10, "t": 25} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004559 | registered_L0085_setting / RSI | {"form": "cross", "n": 10, "t": 30} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004560 | registered_L0085_setting / RSI | {"form": "state", "n": 10, "t": 30} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004561 | registered_L0085_setting / RSI | {"form": "cross", "n": 10, "t": 35} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004562 | registered_L0085_setting / RSI | {"form": "state", "n": 10, "t": 35} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004563 | registered_L0085_setting / RSI | {"form": "cross", "n": 10, "t": 40} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004564 | registered_L0085_setting / RSI | {"form": "state", "n": 10, "t": 40} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004565 | registered_L0085_setting / RSI | {"form": "cross", "n": 14, "t": 15} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004566 | registered_L0085_setting / RSI | {"form": "state", "n": 14, "t": 15} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004567 | registered_L0085_setting / RSI | {"form": "cross", "n": 14, "t": 20} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004568 | registered_L0085_setting / RSI | {"form": "state", "n": 14, "t": 20} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004569 | registered_L0085_setting / RSI | {"form": "cross", "n": 14, "t": 25} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004570 | registered_L0085_setting / RSI | {"form": "state", "n": 14, "t": 25} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004571 | registered_L0085_setting / RSI | {"form": "cross", "n": 14, "t": 30} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004572 | registered_L0085_setting / RSI | {"form": "state", "n": 14, "t": 30} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004573 | registered_L0085_setting / RSI | {"form": "cross", "n": 14, "t": 35} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004574 | registered_L0085_setting / RSI | {"form": "state", "n": 14, "t": 35} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004575 | registered_L0085_setting / RSI | {"form": "cross", "n": 14, "t": 40} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004576 | registered_L0085_setting / RSI | {"form": "state", "n": 14, "t": 40} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004577 | registered_L0085_setting / RSI | {"form": "cross", "n": 21, "t": 15} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004578 | registered_L0085_setting / RSI | {"form": "state", "n": 21, "t": 15} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004579 | registered_L0085_setting / RSI | {"form": "cross", "n": 21, "t": 20} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004580 | registered_L0085_setting / RSI | {"form": "state", "n": 21, "t": 20} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004581 | registered_L0085_setting / RSI | {"form": "cross", "n": 21, "t": 25} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004582 | registered_L0085_setting / RSI | {"form": "state", "n": 21, "t": 25} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004583 | registered_L0085_setting / RSI | {"form": "cross", "n": 21, "t": 30} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004584 | registered_L0085_setting / RSI | {"form": "state", "n": 21, "t": 30} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004585 | registered_L0085_setting / RSI | {"form": "cross", "n": 21, "t": 35} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004586 | registered_L0085_setting / RSI | {"form": "state", "n": 21, "t": 35} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004587 | registered_L0085_setting / RSI | {"form": "cross", "n": 21, "t": 40} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004588 | registered_L0085_setting / RSI | {"form": "state", "n": 21, "t": 40} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004589 | registered_L0085_setting / RSI | {"form": "cross", "n": 28, "t": 15} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004590 | registered_L0085_setting / RSI | {"form": "state", "n": 28, "t": 15} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004591 | registered_L0085_setting / RSI | {"form": "cross", "n": 28, "t": 20} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004592 | registered_L0085_setting / RSI | {"form": "state", "n": 28, "t": 20} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004593 | registered_L0085_setting / RSI | {"form": "cross", "n": 28, "t": 25} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004594 | registered_L0085_setting / RSI | {"form": "state", "n": 28, "t": 25} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004595 | registered_L0085_setting / RSI | {"form": "cross", "n": 28, "t": 30} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004596 | registered_L0085_setting / RSI | {"form": "state", "n": 28, "t": 30} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004597 | registered_L0085_setting / RSI | {"form": "cross", "n": 28, "t": 35} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004598 | registered_L0085_setting / RSI | {"form": "state", "n": 28, "t": 35} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004599 | registered_L0085_setting / RSI | {"form": "cross", "n": 28, "t": 40} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004600 | registered_L0085_setting / RSI | {"form": "state", "n": 28, "t": 40} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004601 | registered_L0085_setting / RSI | {"form": "cross", "n": 7, "t": 15} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004602 | registered_L0085_setting / RSI | {"form": "state", "n": 7, "t": 15} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004603 | registered_L0085_setting / RSI | {"form": "cross", "n": 7, "t": 20} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004604 | registered_L0085_setting / RSI | {"form": "state", "n": 7, "t": 20} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004605 | registered_L0085_setting / RSI | {"form": "cross", "n": 7, "t": 25} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004606 | registered_L0085_setting / RSI | {"form": "state", "n": 7, "t": 25} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004607 | registered_L0085_setting / RSI | {"form": "cross", "n": 7, "t": 30} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004608 | registered_L0085_setting / RSI | {"form": "state", "n": 7, "t": 30} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004609 | registered_L0085_setting / RSI | {"form": "cross", "n": 7, "t": 35} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004610 | registered_L0085_setting / RSI | {"form": "state", "n": 7, "t": 35} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004611 | registered_L0085_setting / RSI | {"form": "cross", "n": 7, "t": 40} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004612 | registered_L0085_setting / RSI | {"form": "state", "n": 7, "t": 40} | DEF-da7323d0c286eabc | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004613 | registered_L0085_setting / STOCHRSI | {"n": 14, "t": 0.1} | DEF-4396d5b63ca6a8b1 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004614 | registered_L0085_setting / STOCHRSI | {"n": 14, "t": 0.2} | DEF-4396d5b63ca6a8b1 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004615 | registered_L0085_setting / STOCHRSI | {"n": 14, "t": 0.3} | DEF-4396d5b63ca6a8b1 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004616 | registered_L0085_setting / STOCHRSI | {"n": 21, "t": 0.1} | DEF-4396d5b63ca6a8b1 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004617 | registered_L0085_setting / STOCHRSI | {"n": 21, "t": 0.2} | DEF-4396d5b63ca6a8b1 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004618 | registered_L0085_setting / STOCHRSI | {"n": 21, "t": 0.3} | DEF-4396d5b63ca6a8b1 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004619 | registered_L0085_setting / STOCHRSI | {"n": 7, "t": 0.1} | DEF-4396d5b63ca6a8b1 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004620 | registered_L0085_setting / STOCHRSI | {"n": 7, "t": 0.2} | DEF-4396d5b63ca6a8b1 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004621 | registered_L0085_setting / STOCHRSI | {"n": 7, "t": 0.3} | DEF-4396d5b63ca6a8b1 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004622 | registered_L0085_setting / STOCH | {"d": 3, "n": 10, "t": 15} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004623 | registered_L0085_setting / STOCH | {"d": 3, "n": 10, "t": 20} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004624 | registered_L0085_setting / STOCH | {"d": 3, "n": 10, "t": 25} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004625 | registered_L0085_setting / STOCH | {"d": 3, "n": 10, "t": 30} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004626 | registered_L0085_setting / STOCH | {"d": 5, "n": 10, "t": 15} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004627 | registered_L0085_setting / STOCH | {"d": 5, "n": 10, "t": 20} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004628 | registered_L0085_setting / STOCH | {"d": 5, "n": 10, "t": 25} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004629 | registered_L0085_setting / STOCH | {"d": 5, "n": 10, "t": 30} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004630 | registered_L0085_setting / STOCH | {"d": 3, "n": 14, "t": 15} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004631 | registered_L0085_setting / STOCH | {"d": 3, "n": 14, "t": 20} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004632 | registered_L0085_setting / STOCH | {"d": 3, "n": 14, "t": 25} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004633 | registered_L0085_setting / STOCH | {"d": 3, "n": 14, "t": 30} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004634 | registered_L0085_setting / STOCH | {"d": 5, "n": 14, "t": 15} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004635 | registered_L0085_setting / STOCH | {"d": 5, "n": 14, "t": 20} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004636 | registered_L0085_setting / STOCH | {"d": 5, "n": 14, "t": 25} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004637 | registered_L0085_setting / STOCH | {"d": 5, "n": 14, "t": 30} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004638 | registered_L0085_setting / STOCH | {"d": 3, "n": 21, "t": 15} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004639 | registered_L0085_setting / STOCH | {"d": 3, "n": 21, "t": 20} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004640 | registered_L0085_setting / STOCH | {"d": 3, "n": 21, "t": 25} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004641 | registered_L0085_setting / STOCH | {"d": 3, "n": 21, "t": 30} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004642 | registered_L0085_setting / STOCH | {"d": 5, "n": 21, "t": 15} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004643 | registered_L0085_setting / STOCH | {"d": 5, "n": 21, "t": 20} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004644 | registered_L0085_setting / STOCH | {"d": 5, "n": 21, "t": 25} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004645 | registered_L0085_setting / STOCH | {"d": 5, "n": 21, "t": 30} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004646 | registered_L0085_setting / STOCH | {"d": 3, "n": 28, "t": 15} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004647 | registered_L0085_setting / STOCH | {"d": 3, "n": 28, "t": 20} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004648 | registered_L0085_setting / STOCH | {"d": 3, "n": 28, "t": 25} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004649 | registered_L0085_setting / STOCH | {"d": 3, "n": 28, "t": 30} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004650 | registered_L0085_setting / STOCH | {"d": 5, "n": 28, "t": 15} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004651 | registered_L0085_setting / STOCH | {"d": 5, "n": 28, "t": 20} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004652 | registered_L0085_setting / STOCH | {"d": 5, "n": 28, "t": 25} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004653 | registered_L0085_setting / STOCH | {"d": 5, "n": 28, "t": 30} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004654 | registered_L0085_setting / STOCH | {"d": 3, "n": 7, "t": 15} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004655 | registered_L0085_setting / STOCH | {"d": 3, "n": 7, "t": 20} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004656 | registered_L0085_setting / STOCH | {"d": 3, "n": 7, "t": 25} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004657 | registered_L0085_setting / STOCH | {"d": 3, "n": 7, "t": 30} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004658 | registered_L0085_setting / STOCH | {"d": 5, "n": 7, "t": 15} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004659 | registered_L0085_setting / STOCH | {"d": 5, "n": 7, "t": 20} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004660 | registered_L0085_setting / STOCH | {"d": 5, "n": 7, "t": 25} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004661 | registered_L0085_setting / STOCH | {"d": 5, "n": 7, "t": 30} | DEF-18314caa30c99a7b | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004662 | registered_L0085_setting / SUPERTREND | {"k": 1.5, "n": 10} | DEF-a91fdff95940f8e8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004663 | registered_L0085_setting / SUPERTREND | {"k": 2, "n": 10} | DEF-a91fdff95940f8e8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004664 | registered_L0085_setting / SUPERTREND | {"k": 2.5, "n": 10} | DEF-a91fdff95940f8e8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004665 | registered_L0085_setting / SUPERTREND | {"k": 3, "n": 10} | DEF-a91fdff95940f8e8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004666 | registered_L0085_setting / SUPERTREND | {"k": 1.5, "n": 14} | DEF-a91fdff95940f8e8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004667 | registered_L0085_setting / SUPERTREND | {"k": 2, "n": 14} | DEF-a91fdff95940f8e8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004668 | registered_L0085_setting / SUPERTREND | {"k": 2.5, "n": 14} | DEF-a91fdff95940f8e8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004669 | registered_L0085_setting / SUPERTREND | {"k": 3, "n": 14} | DEF-a91fdff95940f8e8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004670 | registered_L0085_setting / SUPERTREND | {"k": 1.5, "n": 21} | DEF-a91fdff95940f8e8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004671 | registered_L0085_setting / SUPERTREND | {"k": 2, "n": 21} | DEF-a91fdff95940f8e8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004672 | registered_L0085_setting / SUPERTREND | {"k": 2.5, "n": 21} | DEF-a91fdff95940f8e8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004673 | registered_L0085_setting / SUPERTREND | {"k": 3, "n": 21} | DEF-a91fdff95940f8e8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004674 | registered_L0085_setting / SUPERTREND | {"k": 1.5, "n": 7} | DEF-a91fdff95940f8e8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004675 | registered_L0085_setting / SUPERTREND | {"k": 2, "n": 7} | DEF-a91fdff95940f8e8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004676 | registered_L0085_setting / SUPERTREND | {"k": 2.5, "n": 7} | DEF-a91fdff95940f8e8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004677 | registered_L0085_setting / SUPERTREND | {"k": 3, "n": 7} | DEF-a91fdff95940f8e8 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004678 | registered_L0085_setting / SWEEP | {"depth": 0, "n": 10} | DEF-dd3627030fb3a285 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004679 | registered_L0085_setting / SWEEP | {"depth": 0.25, "n": 10} | DEF-dd3627030fb3a285 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004680 | registered_L0085_setting / SWEEP | {"depth": 0.5, "n": 10} | DEF-dd3627030fb3a285 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004681 | registered_L0085_setting / SWEEP | {"depth": 0, "n": 20} | DEF-dd3627030fb3a285 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004682 | registered_L0085_setting / SWEEP | {"depth": 0.25, "n": 20} | DEF-dd3627030fb3a285 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004683 | registered_L0085_setting / SWEEP | {"depth": 0.5, "n": 20} | DEF-dd3627030fb3a285 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004684 | registered_L0085_setting / SWEEP | {"depth": 0, "n": 40} | DEF-dd3627030fb3a285 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004685 | registered_L0085_setting / SWEEP | {"depth": 0.25, "n": 40} | DEF-dd3627030fb3a285 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004686 | registered_L0085_setting / SWEEP | {"depth": 0.5, "n": 40} | DEF-dd3627030fb3a285 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004687 | registered_L0085_setting / SWEEP | {"depth": 0, "n": 55} | DEF-dd3627030fb3a285 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004688 | registered_L0085_setting / SWEEP | {"depth": 0.25, "n": 55} | DEF-dd3627030fb3a285 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004689 | registered_L0085_setting / SWEEP | {"depth": 0.5, "n": 55} | DEF-dd3627030fb3a285 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004690 | registered_L0085_setting / SWEEP | {"depth": 0, "n": 5} | DEF-dd3627030fb3a285 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004691 | registered_L0085_setting / SWEEP | {"depth": 0.25, "n": 5} | DEF-dd3627030fb3a285 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004692 | registered_L0085_setting / SWEEP | {"depth": 0.5, "n": 5} | DEF-dd3627030fb3a285 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004717 | registered_L0085_setting / VOLZ | {"n": 100, "t": 1.5, "upper": 0.5} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004718 | registered_L0085_setting / VOLZ | {"n": 100, "t": 1.5, "upper": 0.6666666666666666} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004719 | registered_L0085_setting / VOLZ | {"n": 100, "t": 2.5, "upper": 0.5} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004720 | registered_L0085_setting / VOLZ | {"n": 100, "t": 2.5, "upper": 0.6666666666666666} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004721 | registered_L0085_setting / VOLZ | {"n": 100, "t": 2, "upper": 0.5} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004722 | registered_L0085_setting / VOLZ | {"n": 100, "t": 2, "upper": 0.6666666666666666} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004723 | registered_L0085_setting / VOLZ | {"n": 100, "t": 3, "upper": 0.5} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004724 | registered_L0085_setting / VOLZ | {"n": 100, "t": 3, "upper": 0.6666666666666666} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004725 | registered_L0085_setting / VOLZ | {"n": 20, "t": 1.5, "upper": 0.5} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004726 | registered_L0085_setting / VOLZ | {"n": 20, "t": 1.5, "upper": 0.6666666666666666} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004727 | registered_L0085_setting / VOLZ | {"n": 20, "t": 2.5, "upper": 0.5} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004728 | registered_L0085_setting / VOLZ | {"n": 20, "t": 2.5, "upper": 0.6666666666666666} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004729 | registered_L0085_setting / VOLZ | {"n": 20, "t": 2, "upper": 0.5} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004730 | registered_L0085_setting / VOLZ | {"n": 20, "t": 2, "upper": 0.6666666666666666} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004731 | registered_L0085_setting / VOLZ | {"n": 20, "t": 3, "upper": 0.5} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004732 | registered_L0085_setting / VOLZ | {"n": 20, "t": 3, "upper": 0.6666666666666666} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004733 | registered_L0085_setting / VOLZ | {"n": 50, "t": 1.5, "upper": 0.5} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004734 | registered_L0085_setting / VOLZ | {"n": 50, "t": 1.5, "upper": 0.6666666666666666} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004735 | registered_L0085_setting / VOLZ | {"n": 50, "t": 2.5, "upper": 0.5} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004736 | registered_L0085_setting / VOLZ | {"n": 50, "t": 2.5, "upper": 0.6666666666666666} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004737 | registered_L0085_setting / VOLZ | {"n": 50, "t": 2, "upper": 0.5} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004738 | registered_L0085_setting / VOLZ | {"n": 50, "t": 2, "upper": 0.6666666666666666} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004739 | registered_L0085_setting / VOLZ | {"n": 50, "t": 3, "upper": 0.5} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004740 | registered_L0085_setting / VOLZ | {"n": 50, "t": 3, "upper": 0.6666666666666666} | DEF-8267afbc7048fdb6 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004741 | registered_L0085_setting / VORTEX | {"n": 14} | DEF-14ed5bd873934243 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004742 | registered_L0085_setting / VORTEX | {"n": 21} | DEF-14ed5bd873934243 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004743 | registered_L0085_setting / VORTEX | {"n": 28} | DEF-14ed5bd873934243 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004744 | registered_L0085_setting / VORTEX | {"n": 7} | DEF-14ed5bd873934243 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004745 | registered_L0085_setting / VWAP | {"k": 1, "n": 10} | DEF-591bf146fa9a1479 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004746 | registered_L0085_setting / VWAP | {"k": 1.5, "n": 10} | DEF-591bf146fa9a1479 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004747 | registered_L0085_setting / VWAP | {"k": 2, "n": 10} | DEF-591bf146fa9a1479 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004748 | registered_L0085_setting / VWAP | {"k": 2.5, "n": 10} | DEF-591bf146fa9a1479 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004749 | registered_L0085_setting / VWAP | {"k": 1, "n": 20} | DEF-591bf146fa9a1479 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004750 | registered_L0085_setting / VWAP | {"k": 1.5, "n": 20} | DEF-591bf146fa9a1479 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004751 | registered_L0085_setting / VWAP | {"k": 2, "n": 20} | DEF-591bf146fa9a1479 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004752 | registered_L0085_setting / VWAP | {"k": 2.5, "n": 20} | DEF-591bf146fa9a1479 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004753 | registered_L0085_setting / VWAP | {"k": 1, "n": 30} | DEF-591bf146fa9a1479 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004754 | registered_L0085_setting / VWAP | {"k": 1.5, "n": 30} | DEF-591bf146fa9a1479 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004755 | registered_L0085_setting / VWAP | {"k": 2, "n": 30} | DEF-591bf146fa9a1479 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004756 | registered_L0085_setting / VWAP | {"k": 2.5, "n": 30} | DEF-591bf146fa9a1479 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004757 | registered_L0085_setting / VWAP | {"k": 1, "n": 50} | DEF-591bf146fa9a1479 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004758 | registered_L0085_setting / VWAP | {"k": 1.5, "n": 50} | DEF-591bf146fa9a1479 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004759 | registered_L0085_setting / VWAP | {"k": 2, "n": 50} | DEF-591bf146fa9a1479 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004760 | registered_L0085_setting / VWAP | {"k": 2.5, "n": 50} | DEF-591bf146fa9a1479 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004761 | registered_L0085_setting / WR | {"n": 10, "t": -70} | DEF-60512811e5d91de0 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004762 | registered_L0085_setting / WR | {"n": 10, "t": -80} | DEF-60512811e5d91de0 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004763 | registered_L0085_setting / WR | {"n": 10, "t": -90} | DEF-60512811e5d91de0 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004764 | registered_L0085_setting / WR | {"n": 14, "t": -70} | DEF-60512811e5d91de0 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004765 | registered_L0085_setting / WR | {"n": 14, "t": -80} | DEF-60512811e5d91de0 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004766 | registered_L0085_setting / WR | {"n": 14, "t": -90} | DEF-60512811e5d91de0 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004767 | registered_L0085_setting / WR | {"n": 21, "t": -70} | DEF-60512811e5d91de0 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004768 | registered_L0085_setting / WR | {"n": 21, "t": -80} | DEF-60512811e5d91de0 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004769 | registered_L0085_setting / WR | {"n": 21, "t": -90} | DEF-60512811e5d91de0 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004770 | registered_L0085_setting / WR | {"n": 28, "t": -70} | DEF-60512811e5d91de0 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004771 | registered_L0085_setting / WR | {"n": 28, "t": -80} | DEF-60512811e5d91de0 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004772 | registered_L0085_setting / WR | {"n": 28, "t": -90} | DEF-60512811e5d91de0 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004773 | registered_L0085_setting / WR | {"n": 7, "t": -70} | DEF-60512811e5d91de0 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004774 | registered_L0085_setting / WR | {"n": 7, "t": -80} | DEF-60512811e5d91de0 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004775 | registered_L0085_setting / WR | {"n": 7, "t": -90} | DEF-60512811e5d91de0 | decision close; source uses causal inputs; combined pulse applied by research85.combine / None |
| V-0004776 | registered_older_52_grid / Aroon14 | {"numeric_tokens": ["14"], "setting_name": "Aroon14_bull_x"} | DEF-972814915c1f6dcb |  / None |
| V-0004777 | registered_older_52_grid / Aroon25 | {"numeric_tokens": ["25"], "setting_name": "Aroon25_bull_x"} | DEF-972814915c1f6dcb |  / None |
| V-0004778 | registered_older_52_grid / BB20 | {"numeric_tokens": ["20", "2.0"], "setting_name": "BB20_2.0_reenter"} | DEF-972814915c1f6dcb |  / None |
| V-0004779 | registered_older_52_grid / BB20 | {"numeric_tokens": ["20", "2.5"], "setting_name": "BB20_2.5_reenter"} | DEF-972814915c1f6dcb |  / None |
| V-0004780 | registered_older_52_grid / BB20 | {"numeric_tokens": ["20", "3.0"], "setting_name": "BB20_3.0_reenter"} | DEF-972814915c1f6dcb |  / None |
| V-0004781 | registered_older_52_grid / BullEngulfing | {"numeric_tokens": [], "setting_name": "BullEngulfing"} | DEF-972814915c1f6dcb |  / None |
| V-0004782 | registered_older_52_grid / CCI14 | {"numeric_tokens": ["14", "-100"], "setting_name": "CCI14_xup_-100"} | DEF-972814915c1f6dcb |  / None |
| V-0004783 | registered_older_52_grid / CCI20 | {"numeric_tokens": ["20", "-100"], "setting_name": "CCI20_xup_-100"} | DEF-972814915c1f6dcb |  / None |
| V-0004784 | registered_older_52_grid / Donchian10 | {"numeric_tokens": ["10"], "setting_name": "Donchian10_break"} | DEF-972814915c1f6dcb |  / None |
| V-0004785 | registered_older_52_grid / Donchian20 | {"numeric_tokens": ["20"], "setting_name": "Donchian20_break"} | DEF-972814915c1f6dcb |  / None |
| V-0004786 | registered_older_52_grid / Donchian20 | {"numeric_tokens": ["20"], "setting_name": "Donchian20_fail"} | DEF-972814915c1f6dcb |  / None |
| V-0004787 | registered_older_52_grid / Donchian55 | {"numeric_tokens": ["55"], "setting_name": "Donchian55_break"} | DEF-972814915c1f6dcb |  / None |
| V-0004788 | registered_older_52_grid / EMA | {"numeric_tokens": ["20", "200"], "setting_name": "EMA_x_20_200"} | DEF-972814915c1f6dcb |  / None |
| V-0004789 | registered_older_52_grid / EMA | {"numeric_tokens": ["20", "50"], "setting_name": "EMA_x_20_50"} | DEF-972814915c1f6dcb |  / None |
| V-0004790 | registered_older_52_grid / EMA | {"numeric_tokens": ["50", "200"], "setting_name": "EMA_x_50_200"} | DEF-972814915c1f6dcb |  / None |
| V-0004791 | registered_older_52_grid / FVG | {"numeric_tokens": [], "setting_name": "FVG_single"} | DEF-972814915c1f6dcb |  / None |
| V-0004792 | registered_older_52_grid / Hammer | {"numeric_tokens": [], "setting_name": "Hammer"} | DEF-972814915c1f6dcb |  / None |
| V-0004793 | registered_older_52_grid / MACD | {"numeric_tokens": ["12", "26", "9"], "setting_name": "MACD_12_26_9_xup"} | DEF-972814915c1f6dcb |  / None |
| V-0004794 | registered_older_52_grid / MACD | {"numeric_tokens": ["5", "35", "5"], "setting_name": "MACD_5_35_5_xup"} | DEF-972814915c1f6dcb |  / None |
| V-0004795 | registered_older_52_grid / MFI14 | {"numeric_tokens": ["14", "20"], "setting_name": "MFI14_xup_20"} | DEF-972814915c1f6dcb |  / None |
| V-0004796 | registered_older_52_grid / PX | {"numeric_tokens": ["200"], "setting_name": "PX_x_EMA200"} | DEF-972814915c1f6dcb |  / None |
| V-0004797 | registered_older_52_grid / PX | {"numeric_tokens": ["50"], "setting_name": "PX_x_EMA50"} | DEF-972814915c1f6dcb |  / None |
| V-0004798 | registered_older_52_grid / RSI14 | {"numeric_tokens": ["14"], "setting_name": "RSI14_bull_divergence"} | DEF-972814915c1f6dcb |  / None |
| V-0004799 | registered_older_52_grid / RSI14 | {"numeric_tokens": ["14", "20"], "setting_name": "RSI14_xup_20"} | DEF-972814915c1f6dcb |  / None |
| V-0004800 | registered_older_52_grid / RSI14 | {"numeric_tokens": ["14", "25"], "setting_name": "RSI14_xup_25"} | DEF-972814915c1f6dcb |  / None |
| V-0004801 | registered_older_52_grid / RSI14 | {"numeric_tokens": ["14", "30"], "setting_name": "RSI14_xup_30"} | DEF-972814915c1f6dcb |  / None |
| V-0004802 | registered_older_52_grid / RSI21 | {"numeric_tokens": ["21"], "setting_name": "RSI21_bull_divergence"} | DEF-972814915c1f6dcb |  / None |
| V-0004803 | registered_older_52_grid / RSI21 | {"numeric_tokens": ["21", "20"], "setting_name": "RSI21_xup_20"} | DEF-972814915c1f6dcb |  / None |
| V-0004804 | registered_older_52_grid / RSI21 | {"numeric_tokens": ["21", "25"], "setting_name": "RSI21_xup_25"} | DEF-972814915c1f6dcb |  / None |
| V-0004805 | registered_older_52_grid / RSI21 | {"numeric_tokens": ["21", "30"], "setting_name": "RSI21_xup_30"} | DEF-972814915c1f6dcb |  / None |
| V-0004806 | registered_older_52_grid / RSI7 | {"numeric_tokens": ["7", "20"], "setting_name": "RSI7_xup_20"} | DEF-972814915c1f6dcb |  / None |
| V-0004807 | registered_older_52_grid / RSI7 | {"numeric_tokens": ["7", "25"], "setting_name": "RSI7_xup_25"} | DEF-972814915c1f6dcb |  / None |
| V-0004808 | registered_older_52_grid / RSI7 | {"numeric_tokens": ["7", "30"], "setting_name": "RSI7_xup_30"} | DEF-972814915c1f6dcb |  / None |
| V-0004809 | registered_older_52_grid / Stoch14 | {"numeric_tokens": ["14", "3", "15"], "setting_name": "Stoch14_3_xup_15"} | DEF-972814915c1f6dcb |  / None |
| V-0004810 | registered_older_52_grid / Stoch14 | {"numeric_tokens": ["14", "3", "20"], "setting_name": "Stoch14_3_xup_20"} | DEF-972814915c1f6dcb |  / None |
| V-0004811 | registered_older_52_grid / Stoch14 | {"numeric_tokens": ["14", "3", "25"], "setting_name": "Stoch14_3_xup_25"} | DEF-972814915c1f6dcb |  / None |
| V-0004812 | registered_older_52_grid / Stoch21 | {"numeric_tokens": ["21", "5", "15"], "setting_name": "Stoch21_5_xup_15"} | DEF-972814915c1f6dcb |  / None |
| V-0004813 | registered_older_52_grid / Stoch21 | {"numeric_tokens": ["21", "5", "20"], "setting_name": "Stoch21_5_xup_20"} | DEF-972814915c1f6dcb |  / None |
| V-0004814 | registered_older_52_grid / Stoch21 | {"numeric_tokens": ["21", "5", "25"], "setting_name": "Stoch21_5_xup_25"} | DEF-972814915c1f6dcb |  / None |
| V-0004822 | registered_older_52_grid / VolSpike | {"numeric_tokens": ["1.5"], "setting_name": "VolSpike_z1.5"} | DEF-972814915c1f6dcb |  / None |
| V-0004823 | registered_older_52_grid / VolSpike | {"numeric_tokens": ["2.0"], "setting_name": "VolSpike_z2.0"} | DEF-972814915c1f6dcb |  / None |
| V-0004824 | registered_older_52_grid / VolSpike | {"numeric_tokens": ["2.5"], "setting_name": "VolSpike_z2.5"} | DEF-972814915c1f6dcb |  / None |
| V-0004825 | registered_older_52_grid / VolSpike | {"numeric_tokens": ["3.0"], "setting_name": "VolSpike_z3.0"} | DEF-972814915c1f6dcb |  / None |
| V-0004826 | registered_older_52_grid / WilliamsR14 | {"numeric_tokens": ["14", "-80"], "setting_name": "WilliamsR14_xup_-80"} | DEF-972814915c1f6dcb |  / None |
| V-0004827 | registered_older_52_grid / WilliamsR21 | {"numeric_tokens": ["21", "-80"], "setting_name": "WilliamsR21_xup_-80"} | DEF-972814915c1f6dcb |  / None |
| V-0004828 | registered_L0088_setting / BB | {"k": 2, "n": 10} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004829 | registered_L0088_setting / BB | {"k": 2.5, "n": 10} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004830 | registered_L0088_setting / BB | {"k": 2, "n": 20} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004831 | registered_L0088_setting / BB | {"k": 2.5, "n": 20} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004832 | registered_L0088_setting / BB | {"k": 2, "n": 30} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004833 | registered_L0088_setting / BB | {"k": 2.5, "n": 30} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004834 | registered_L0088_setting / CCI | {"n": 10, "t": -150} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004835 | registered_L0088_setting / CCI | {"n": 10, "t": -100} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004836 | registered_L0088_setting / CCI | {"n": 14, "t": -150} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004837 | registered_L0088_setting / CCI | {"n": 14, "t": -100} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004838 | registered_L0088_setting / CCI | {"n": 21, "t": -150} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004839 | registered_L0088_setting / CCI | {"n": 21, "t": -100} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004840 | registered_L0088_setting / EMA_RECLAIM | {"n": 10} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004841 | registered_L0088_setting / EMA_RECLAIM | {"n": 20} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004842 | registered_L0088_setting / EMA_RECLAIM | {"n": 30} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004843 | registered_L0088_setting / DONCHIAN_RECLAIM | {"n": 10} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004844 | registered_L0088_setting / DONCHIAN_RECLAIM | {"n": 20} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004845 | registered_L0088_setting / DONCHIAN_RECLAIM | {"n": 40} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004846 | registered_L0088_setting / OBV_EMA | {"fast": 5, "slow": 20} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004847 | registered_L0088_setting / OBV_EMA | {"fast": 10, "slow": 30} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004848 | registered_L0088_setting / OBV_EMA | {"fast": 20, "slow": 50} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004855 | registered_L0088_setting / SQUEEZE_BREAK | {"n": 20} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004856 | registered_L0088_setting / SQUEEZE_BREAK | {"n": 30} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004857 | registered_L0088_setting / RSI_RECLAIM | {"n": 10, "t": 30} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004858 | registered_L0088_setting / RSI_RECLAIM | {"n": 10, "t": 40} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004859 | registered_L0088_setting / RSI_RECLAIM | {"n": 14, "t": 30} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004860 | registered_L0088_setting / RSI_RECLAIM | {"n": 14, "t": 40} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004861 | registered_L0088_setting / RSI_RECLAIM | {"n": 21, "t": 30} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004862 | registered_L0088_setting / RSI_RECLAIM | {"n": 21, "t": 40} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004863 | registered_L0088_setting / MACD_REFERENCE | {"fast": 12, "signal": 9, "slow": 26} | DEF-2eb9ed4752203dd6 | current close; false-to-true pulse; CCI rounded to10 decimals before crossing / None |
| V-0004870 | registered_L0090_volume_state / OBV_EMA | {"fast": 5, "operator": ">", "round_decimals": 10, "slow": 20} | DEF-61434560613f9b68 | current close persistent state; no pulse conversion / None |
| V-0004871 | registered_L0090_volume_state / OBV_EMA | {"fast": 10, "operator": ">", "round_decimals": 10, "slow": 30} | DEF-61434560613f9b68 | current close persistent state; no pulse conversion / None |
| V-0004872 | registered_L0090_volume_state / OBV_EMA | {"fast": 20, "operator": ">", "round_decimals": 10, "slow": 50} | DEF-61434560613f9b68 | current close persistent state; no pulse conversion / None |
| V-0004873 | registered_L0091_setting / PRICE_RECOVERY | {"n": 2, "no_lower_low": false} | DEF-6a2858ffd72ce86a | current close false-to-true / BTCUSDT |
| V-0004876 | registered_L0091_setting / PRICE_RECOVERY | {"n": 2, "no_lower_low": true} | DEF-6a2858ffd72ce86a | current close false-to-true / BTCUSDT |
| V-0004879 | registered_L0091_setting / PRICE_RECOVERY | {"n": 3, "no_lower_low": false} | DEF-6a2858ffd72ce86a | current close false-to-true / BTCUSDT |
| V-0004882 | registered_L0091_setting / PRICE_RECOVERY | {"n": 3, "no_lower_low": true} | DEF-6a2858ffd72ce86a | current close false-to-true / BTCUSDT |
| V-0004885 | registered_L0091_setting / PRICE_RECOVERY | {"n": 5, "no_lower_low": false} | DEF-6a2858ffd72ce86a | current close false-to-true / BTCUSDT |
| V-0004888 | registered_L0091_setting / PRICE_RECOVERY | {"n": 5, "no_lower_low": true} | DEF-6a2858ffd72ce86a | current close false-to-true / BTCUSDT |
| V-0004891 | registered_L0092_setting / CANDLE:HAMMER | {"CCI_period": 14, "CCI_threshold": -150, "kind": "HAMMER", "mode": "STANDALONE", "prior_context": "close[t-1]<close[t-7]", "ratio": 2.0} | DEF-0c52b2761d322e46 | candle completes at current close; pulse / BTCUSDT |
| V-0004892 | registered_L0092_setting / CANDLE:HAMMER | {"CCI_period": 14, "CCI_threshold": -150, "kind": "HAMMER", "mode": "CCI_AND_CURRENT", "prior_context": "close[t-1]<close[t-7]", "ratio": 2.0} | DEF-0c52b2761d322e46 | CCI pulse and candle pulse at current close / BTCUSDT |
| V-0004893 | registered_L0092_setting / CANDLE:HAMMER | {"CCI_period": 14, "CCI_threshold": -150, "kind": "HAMMER", "mode": "CCI_THEN_CANDLE2", "prior_context": "close[t-1]<close[t-7]", "ratio": 2.0} | DEF-0c52b2761d322e46 | CCI pulse strictly 1 or 2 bars before current candle completion; alert timestamp now / BTCUSDT |
| V-0004900 | registered_L0092_setting / CANDLE:HAMMER | {"CCI_period": 14, "CCI_threshold": -150, "kind": "HAMMER", "mode": "STANDALONE", "prior_context": "close[t-1]<close[t-7]", "ratio": 3.0} | DEF-0c52b2761d322e46 | candle completes at current close; pulse / BTCUSDT |
| V-0004901 | registered_L0092_setting / CANDLE:HAMMER | {"CCI_period": 14, "CCI_threshold": -150, "kind": "HAMMER", "mode": "CCI_AND_CURRENT", "prior_context": "close[t-1]<close[t-7]", "ratio": 3.0} | DEF-0c52b2761d322e46 | CCI pulse and candle pulse at current close / BTCUSDT |
| V-0004902 | registered_L0092_setting / CANDLE:HAMMER | {"CCI_period": 14, "CCI_threshold": -150, "kind": "HAMMER", "mode": "CCI_THEN_CANDLE2", "prior_context": "close[t-1]<close[t-7]", "ratio": 3.0} | DEF-0c52b2761d322e46 | CCI pulse strictly 1 or 2 bars before current candle completion; alert timestamp now / BTCUSDT |
| V-0004909 | registered_L0092_setting / CANDLE:ENGULF | {"CCI_period": 14, "CCI_threshold": -150, "kind": "ENGULF", "mode": "STANDALONE", "prior_context": "close[t-1]<close[t-7]", "ratio": 1.0} | DEF-0c52b2761d322e46 | candle completes at current close; pulse / BTCUSDT |
| V-0004910 | registered_L0092_setting / CANDLE:ENGULF | {"CCI_period": 14, "CCI_threshold": -150, "kind": "ENGULF", "mode": "CCI_AND_CURRENT", "prior_context": "close[t-1]<close[t-7]", "ratio": 1.0} | DEF-0c52b2761d322e46 | CCI pulse and candle pulse at current close / BTCUSDT |
| V-0004911 | registered_L0092_setting / CANDLE:ENGULF | {"CCI_period": 14, "CCI_threshold": -150, "kind": "ENGULF", "mode": "CCI_THEN_CANDLE2", "prior_context": "close[t-1]<close[t-7]", "ratio": 1.0} | DEF-0c52b2761d322e46 | CCI pulse strictly 1 or 2 bars before current candle completion; alert timestamp now / BTCUSDT |
| V-0004918 | registered_L0092_setting / CANDLE:ENGULF | {"CCI_period": 14, "CCI_threshold": -150, "kind": "ENGULF", "mode": "STANDALONE", "prior_context": "close[t-1]<close[t-7]", "ratio": 1.25} | DEF-0c52b2761d322e46 | candle completes at current close; pulse / BTCUSDT |
| V-0004919 | registered_L0092_setting / CANDLE:ENGULF | {"CCI_period": 14, "CCI_threshold": -150, "kind": "ENGULF", "mode": "CCI_AND_CURRENT", "prior_context": "close[t-1]<close[t-7]", "ratio": 1.25} | DEF-0c52b2761d322e46 | CCI pulse and candle pulse at current close / BTCUSDT |
| V-0004920 | registered_L0092_setting / CANDLE:ENGULF | {"CCI_period": 14, "CCI_threshold": -150, "kind": "ENGULF", "mode": "CCI_THEN_CANDLE2", "prior_context": "close[t-1]<close[t-7]", "ratio": 1.25} | DEF-0c52b2761d322e46 | CCI pulse strictly 1 or 2 bars before current candle completion; alert timestamp now / BTCUSDT |
| V-0004927 | registered_L0092_setting / CANDLE:MORNING | {"CCI_period": 14, "CCI_threshold": -150, "kind": "MORNING", "mode": "STANDALONE", "prior_context": "close[t-1]<close[t-7]", "recovery": 0.5} | DEF-0c52b2761d322e46 | candle completes at current close; pulse / BTCUSDT |
| V-0004928 | registered_L0092_setting / CANDLE:MORNING | {"CCI_period": 14, "CCI_threshold": -150, "kind": "MORNING", "mode": "CCI_AND_CURRENT", "prior_context": "close[t-1]<close[t-7]", "recovery": 0.5} | DEF-0c52b2761d322e46 | CCI pulse and candle pulse at current close / BTCUSDT |
| V-0004929 | registered_L0092_setting / CANDLE:MORNING | {"CCI_period": 14, "CCI_threshold": -150, "kind": "MORNING", "mode": "CCI_THEN_CANDLE2", "prior_context": "close[t-1]<close[t-7]", "recovery": 0.5} | DEF-0c52b2761d322e46 | CCI pulse strictly 1 or 2 bars before current candle completion; alert timestamp now / BTCUSDT |
| V-0004936 | registered_L0092_setting / CANDLE:MORNING | {"CCI_period": 14, "CCI_threshold": -150, "kind": "MORNING", "mode": "STANDALONE", "prior_context": "close[t-1]<close[t-7]", "recovery": 1.0} | DEF-0c52b2761d322e46 | candle completes at current close; pulse / BTCUSDT |
| V-0004937 | registered_L0092_setting / CANDLE:MORNING | {"CCI_period": 14, "CCI_threshold": -150, "kind": "MORNING", "mode": "CCI_AND_CURRENT", "prior_context": "close[t-1]<close[t-7]", "recovery": 1.0} | DEF-0c52b2761d322e46 | CCI pulse and candle pulse at current close / BTCUSDT |
| V-0004938 | registered_L0092_setting / CANDLE:MORNING | {"CCI_period": 14, "CCI_threshold": -150, "kind": "MORNING", "mode": "CCI_THEN_CANDLE2", "prior_context": "close[t-1]<close[t-7]", "recovery": 1.0} | DEF-0c52b2761d322e46 | CCI pulse strictly 1 or 2 bars before current candle completion; alert timestamp now / BTCUSDT |

## Appendix C — complete inherited signal definitions

The original definition text below is English/Python pseudocode specifying the calculations; delivered pinned primitives provide the explicitly described numerical conventions above. Preserve each distinct definition and its original ID; do not replace a name with an assumed familiar recipe. Legacy definitions include their complete registry and dispatch body. Settings in Appendix B bind the parameters; no unregistered axis is implied.

### DEF-2d73dd02c356d7d5 — AROON / L0085.build.AROON

reviewed_indicator_signal

> if f == 'AROON':
> x, y = get(('aroon', n), lambda: I.aroon(h, l, n))
> a = I.cross_above(x, y)

### DEF-7db3e0575bc7d1c8 — BB / L0085.build.BB

reviewed_indicator_signal

> if f == 'BB':
> x, _, _ = get(('bb', n, q['k']), lambda: I.bollinger(c, n, q['k']))
> a = (l <= x) & (c > x)

### DEF-311e07cf1274e7cd — BOS / L0085.build.BOS

reviewed_indicator_signal

> if f == 'BOS':
> lower = l < roll(shift(l), q['look'], 'min')
> recent = roll(shift(lower.astype(float)), q['look'], 'max') > 0
> a = (c > roll(shift(h), n, 'max')) & recent

### DEF-7c477eea1de8ef48 — CCI / L0085.build.CCI

reviewed_indicator_signal

> if f == 'CCI':
> a = I.cross_up_through(get(('cci', n), lambda: I.cci(h, l, c, n)), t)

### DEF-2dcf9f06b0b67c07 — CMF / L0085.build.CMF

reviewed_indicator_signal

> if f == 'CMF':
> flow = np.nan_to_num(div(2 * c - h - l, h - l)) * v
> x = div(roll(flow, n, 'sum'), roll(v, n, 'sum'))
> a = I.cross_up_through(x, t)

### DEF-42a338e665f5c5e5 — DIV_MACD / L0085.build.DIV_MACD

reviewed_indicator_signal

> if f.startswith('DIV_'):
> if f == 'DIV_RSI':
>     x = rs(14)
> elif f == 'DIV_MACD':
>     x, y = mac(12, 26, 9)
>     x = x - y
> elif f == 'DIV_OBV':
>     x = get('obv', lambda: np.cumsum(np.nan_to_num(np.sign(c - shift(c))) * v))
> else:
>     x = ratio
> a = divergence(l, x, atr, q['look'], q['right'])
> if f == 'DIV_MACD':
> x, y = mac(12, 26, 9)
> x = x - y

### DEF-f3ab1ae9536994ac — DIV_OBV / L0085.build.DIV_OBV

reviewed_indicator_signal

> if f.startswith('DIV_'):
> if f == 'DIV_RSI':
>     x = rs(14)
> elif f == 'DIV_MACD':
>     x, y = mac(12, 26, 9)
>     x = x - y
> elif f == 'DIV_OBV':
>     x = get('obv', lambda: np.cumsum(np.nan_to_num(np.sign(c - shift(c))) * v))
> else:
>     x = ratio
> a = divergence(l, x, atr, q['look'], q['right'])
> if f == 'DIV_OBV':
> x = get('obv', lambda: np.cumsum(np.nan_to_num(np.sign(c - shift(c))) * v))

### DEF-1f8fbb11d59afc04 — DIV_RSI / L0085.build.DIV_RSI

reviewed_indicator_signal

> if f.startswith('DIV_'):
> if f == 'DIV_RSI':
>     x = rs(14)
> elif f == 'DIV_MACD':
>     x, y = mac(12, 26, 9)
>     x = x - y
> elif f == 'DIV_OBV':
>     x = get('obv', lambda: np.cumsum(np.nan_to_num(np.sign(c - shift(c))) * v))
> else:
>     x = ratio
> a = divergence(l, x, atr, q['look'], q['right'])
> if f == 'DIV_RSI':
> x = rs(14)

### DEF-46fa966c949d7bf6 — DMI / L0085.build.DMI

reviewed_indicator_signal

> if f == 'DMI':
> up = h - shift(h)
> dn = shift(l) - l
> plus = np.where((up > dn) & (up > 0), up, 0)
> minus = np.where((dn > up) & (dn > 0), dn, 0)
> an = I.wilder_atr(h, l, c, n)
> p = 100 * div(ew(plus, n), an)
> m = 100 * div(ew(minus, n), an)
> adx = ew(100 * div(abs(p - m), p + m), n)
> a = I.cross_above(p, m) & (adx >= t) & (adx > shift(adx))

### DEF-afb6526f76afaf79 — DONCHIAN_BREAK / L0085.build.DONCHIAN_BREAK

reviewed_indicator_signal

> if f == 'DONCHIAN_BREAK':
> a = c > roll(shift(h), n, 'max')

### DEF-e77a6f975b62cdb0 — DONCHIAN_FAIL / L0085.build.DONCHIAN_FAIL

reviewed_indicator_signal

> if f in ['SWEEP', 'DONCHIAN_FAIL']:
> bottom = roll(shift(l), n, 'min')
> a = (l < bottom - q.get('depth', 0) * atr) & (c > bottom)

### DEF-95296421f35e5003 — EMA / L0085.build.EMA

reviewed_indicator_signal

> if f == 'EMA':
> a = I.cross_above(em(q['fast']), em(q['slow']))

### DEF-d8db39e18c56de13 — ENGULF / L0085.build.ENGULF

reviewed_indicator_signal

> if f in ['HAMMER', 'ENGULF']:
> bottom = l <= roll(l, q['bottom'], 'min')
> if f == 'ENGULF':
>     a = I.bullish_engulfing(o, c) & bottom
> else:
>     body = abs(c - o)
>     a = (body > 0) & (np.minimum(c, o) - l >= q['lower'] * body) & (h - np.maximum(c, o) <= q['upper'] * body) & (c >= (h + l) / 2) & bottom
> if f == 'ENGULF':
> a = I.bullish_engulfing(o, c) & bottom

### DEF-a76277fe5b107c2a — FORCE / L0085.build.FORCE

reviewed_indicator_signal

> if f == 'FORCE':
> a = I.cross_up_through(I.ema((c - shift(c)) * v, n), 0)

### DEF-9421265064ad85be — FVG / L0085.build.FVG

reviewed_indicator_signal

> if f == 'FVG':
> a = l - shift(h, 2) > q['gap'] * atr

### DEF-4927c79acae44c61 — HAMMER / L0085.build.HAMMER

reviewed_indicator_signal

> if f in ['HAMMER', 'ENGULF']:
> bottom = l <= roll(l, q['bottom'], 'min')
> if f == 'ENGULF':
>     a = I.bullish_engulfing(o, c) & bottom
> else:
>     body = abs(c - o)
>     a = (body > 0) & (np.minimum(c, o) - l >= q['lower'] * body) & (h - np.maximum(c, o) <= q['upper'] * body) & (c >= (h + l) / 2) & bottom

### DEF-534271228b4a59e9 — KELTNER / L0085.build.KELTNER

reviewed_indicator_signal

> if f == 'KELTNER':
> x = em(n) - q['k'] * I.wilder_atr(h, l, c, n)
> a = (l <= x) & (c > x)

### DEF-9450d3b5ba89a76c — MACD / L0085.build.MACD

reviewed_indicator_signal

> if f == 'MACD':
> x, y = mac(q['fast'], q['slow'], q['signal'])
> a = I.cross_above(x, y)

### DEF-d0c28a7ff8b0b063 — MFI / L0085.build.MFI

reviewed_indicator_signal

> if f in ['RSI', 'MFI', 'TAKER']:
> x = rs(n) if f == 'RSI' else get(('mfi', n), lambda: I.mfi(h, l, c, v, n)) if f == 'MFI' else ratio
> a = I.cross_up_through(x, t) if q['form'] == 'cross' else x < t if f != 'TAKER' else x > t

### DEF-65548741fb006754 — PXEMA / L0085.build.PXEMA

reviewed_indicator_signal

> if f == 'PXEMA':
> a = I.cross_above(c, em(n))

### DEF-da7323d0c286eabc — RSI / L0085.build.RSI

reviewed_indicator_signal

> if f in ['RSI', 'MFI', 'TAKER']:
> x = rs(n) if f == 'RSI' else get(('mfi', n), lambda: I.mfi(h, l, c, v, n)) if f == 'MFI' else ratio
> a = I.cross_up_through(x, t) if q['form'] == 'cross' else x < t if f != 'TAKER' else x > t

### DEF-4396d5b63ca6a8b1 — STOCHRSI / L0085.build.STOCHRSI

reviewed_indicator_signal

> if f == 'STOCHRSI':
> x = rs(n)
> z = div(x - roll(x, n, 'min'), roll(x, n, 'max') - roll(x, n, 'min'))
> a = I.cross_up_through(z, t)

### DEF-18314caa30c99a7b — STOCH / L0085.build.STOCH

reviewed_indicator_signal

> if f == 'STOCH':
> x, y = get(('stoch', n, q['d']), lambda: I.stochastic(h, l, c, n, q['d']))
> a = I.cross_above(x, y) & (x < t) & (y < t)

### DEF-a91fdff95940f8e8 — SUPERTREND / L0085.build.SUPERTREND

reviewed_indicator_signal

> if f == 'SUPERTREND':
> a = supertrend(h, l, c, n, q['k'])

### DEF-dd3627030fb3a285 — SWEEP / L0085.build.SWEEP

reviewed_indicator_signal

> if f in ['SWEEP', 'DONCHIAN_FAIL']:
> bottom = roll(shift(l), n, 'min')
> a = (l < bottom - q.get('depth', 0) * atr) & (c > bottom)

### DEF-8267afbc7048fdb6 — VOLZ / L0085.build.VOLZ

reviewed_indicator_signal

> if f in ['VOLZ', 'TAKERZ']:
> x = v if f == 'VOLZ' else ratio
> y = shift(x)
> mu = roll(y, n, 'mean')
> sd = pd.Series(y).rolling(n, min_periods=n).std(ddof=0).to_numpy()
> z = div(x - mu, sd)
> a = z >= t
> if f == 'VOLZ':
>     a &= c >= l + q['upper'] * (h - l)
> if f == 'VOLZ':
> a &= c >= l + q['upper'] * (h - l)

### DEF-14ed5bd873934243 — VORTEX / L0085.build.VORTEX

reviewed_indicator_signal

> if f == 'VORTEX':
> tr = np.maximum.reduce([h - l, abs(h - shift(c)), abs(l - shift(c))])
> den = roll(tr, n, 'sum')
> x = div(roll(abs(h - shift(l)), n, 'sum'), den)
> y = div(roll(abs(l - shift(h)), n, 'sum'), den)
> a = I.cross_above(x, y)

### DEF-591bf146fa9a1479 — VWAP / L0085.build.VWAP

reviewed_indicator_signal

> if f == 'VWAP':
> mean = div(roll(tp * v, n, 'sum'), roll(v, n, 'sum'))
> second = div(roll(tp * tp * v, n, 'sum'), roll(v, n, 'sum'))
> sd = np.sqrt(np.maximum(0, second - mean * mean))
> x = mean - q['k'] * sd
> a = (l <= x) & (c > x)

### DEF-60512811e5d91de0 — WR / L0085.build.WR

reviewed_indicator_signal

> if f == 'WR':
> a = I.cross_up_through(get(('wr', n), lambda: I.williams_r(h, l, c, n)), t)

### DEF-972814915c1f6dcb — L0084_52_GRID / L0084.build_one

reviewed_grid_definition

> #!/usr/bin/env python3
> # -*- coding: utf-8 -*-
> """L0084-ENTRY-MIX — indicators library (executable 52-grid).
> 
> Port of the pinned executable 52-grid `history/hyp_lab/l0083_indicators.py`
> @ 62f4d255e0fc6fce8e7c331a6349484ccb0b8fc0, reconciled line-by-line against
> the L0084 paper section 5 (full textual definitions).  Every mask returns a
> boolean array with True at decision bar i (decision at close i, fill at the
> next contiguous open).  Purely causal: no centred/forward-looking input.
> 
> Additions required by L0084 (not in the L0083 library):
>   - wilder_atr: TR=max(H-L,|H-Cprev|,|L-Cprev|), first TR=H-L, Wilder-14.
>   - build_masks: the complete 52-setting catalogue in canonical order.
> """
> from __future__ import annotations
> 
> import numpy as np
> import pandas as pd
> 
> # Canonical order == section 5 table order == Appendix B enumeration order.
> SETTINGS_52 = [
>     "Aroon14_bull_x", "Aroon25_bull_x",
>     "BB20_2.0_reenter", "BB20_2.5_reenter", "BB20_3.0_reenter",
>     "BullEngulfing", "CCI14_xup_-100", "CCI20_xup_-100",
>     "Donchian10_break", "Donchian20_break", "Donchian20_fail",
>     "Donchian55_break", "EMA_x_20_200", "EMA_x_20_50", "EMA_x_50_200",
>     "FVG_single", "Hammer", "MACD_12_26_9_xup", "MACD_5_35_5_xup",
>     "MFI14_xup_20", "PX_x_EMA200", "PX_x_EMA50",
>     "RSI14_bull_divergence", "RSI14_xup_20", "RSI14_xup_25", "RSI14_xup_30",
>     "RSI21_bull_divergence", "RSI21_xup_20", "RSI21_xup_25", "RSI21_xup_30",
>     "RSI7_xup_20", "RSI7_xup_25", "RSI7_xup_30",
>     "Stoch14_3_xup_15", "Stoch14_3_xup_20", "Stoch14_3_xup_25",
>     "Stoch21_5_xup_15", "Stoch21_5_xup_20", "Stoch21_5_xup_25",
>     "TakerRatioZ_ge_1.5", "TakerRatioZ_ge_2.0", "TakerRatioZ_ge_2.5",
>     "TakerRatio_gt_0.48", "TakerRatio_gt_0.5", "TakerRatio_gt_0.52",
>     "TakerRatio_gt_0.55",
>     "VolSpike_z1.5", "VolSpike_z2.0", "VolSpike_z2.5", "VolSpike_z3.0",
>     "WilliamsR14_xup_-80", "WilliamsR21_xup_-80",
> ]
> assert len(SETTINGS_52) == 52
> assert len(set(SETTINGS_52)) == 52
> 
> 
> def _s(a):
>     return pd.Series(a, dtype="float64")
> 
> 
> # --------------------------------------------------------------------------
> # series primitives (verbatim semantics of the pinned 52-grid)
> # --------------------------------------------------------------------------
> def rsi(close, n=14):
>     c = _s(close)
>     d = c.diff()
>     up = d.clip(lower=0.0)
>     dn = (-d).clip(lower=0.0)
>     ru = up.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
>     rd = dn.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
>     rs = ru / rd.replace(0, np.nan)          # D=0 => NaN => false, never 100
>     out = 100 - 100 / (1 + rs)
>     return out.to_numpy()
> 
> 
> def cross_up_through(series, thr):
>     a = np.asarray(series, float)
>     prev = np.roll(a, 1)
>     prev[0] = np.nan                          # first previous is invalid
>     return (prev < thr) & (a >= thr)
> 
> 
> def cross_down_through(series, thr):
>     a = np.asarray(series, float)
>     prev = np.roll(a, 1)
>     prev[0] = np.nan
>     return (prev > thr) & (a <= thr)
> 
> 
> def cross_above(a, b):
>     a = np.asarray(a, float)
>     b = np.asarray(b, float)
>     pa = np.roll(a, 1)
>     pb = np.roll(b, 1)
>     pa[0] = np.nan
>     pb[0] = np.nan
>     return (pa <= pb) & (a > b)
> 
> 
> def stochastic(high, low, close, n=14, d=3):
>     h = _s(high)
>     l = _s(low)
>     c = _s(close)
>     ll = l.rolling(n, min_periods=n).min()
>     hh = h.rolling(n, min_periods=n).max()
>     k = 100 * (c - ll) / (hh - ll).replace(0, np.nan)
>     dd = k.rolling(d, min_periods=d).mean()
>     return k.to_numpy(), dd.to_numpy()
> 
> 
> def bollinger(close, n=20, k=2.0):
>     c = _s(close)
>     mid = c.rolling(n, min_periods=n).mean()
>     sd = c.rolling(n, min_periods=n).std(ddof=0)     # population std
>     lower = mid - k * sd
>     upper = mid + k * sd
>     return lower.to_numpy(), mid.to_numpy(), upper.to_numpy()
> 
> 
> def aroon(high, low, n=14):
>     h = _s(high)
>     l = _s(low)
>     up = h.rolling(n + 1, min_periods=n + 1).apply(
>         lambda x: 100 * (n - (n - np.argmax(x))) / n, raw=True)
>     dn = l.rolling(n + 1, min_periods=n + 1).apply(
>         lambda x: 100 * (n - (n - np.argmin(x))) / n, raw=True)
>     return up.to_numpy(), dn.to_numpy()
> 
> 
> def donchian(high, low, close, n=20):
>     h = _s(high)
>     l = _s(low)
>     upper = h.shift(1).rolling(n, min_periods=n).max()
>     lower = l.shift(1).rolling(n, min_periods=n).min()
>     return lower.to_numpy(), upper.to_numpy()
> 
> 
> def rolling_z(x, n=50):
>     s = _s(x)
>     m = s.rolling(n, min_periods=n).mean()
>     sd = s.rolling(n, min_periods=n).std(ddof=0)
>     return ((s - m) / sd.replace(0, np.nan)).to_numpy()
> 
> 
> def cci(high, low, close, n=20):
>     tp = (_s(high) + _s(low) + _s(close)) / 3
>     ma = tp.rolling(n, min_periods=n).mean()
>     md = tp.rolling(n, min_periods=n).apply(
>         lambda x: np.mean(np.abs(x - x.mean())), raw=True)
>     return ((tp - ma) / (0.015 * md.replace(0, np.nan))).to_numpy()
> 
> 
> def williams_r(high, low, close, n=14):
>     h = _s(high)
>     l = _s(low)
>     c = _s(close)
>     hh = h.rolling(n, min_periods=n).max()
>     ll = l.rolling(n, min_periods=n).min()
>     return (-100 * (hh - c) / (hh - ll).replace(0, np.nan)).to_numpy()
> 
> 
> def mfi(high, low, close, volume, n=14):
>     tp = (_s(high) + _s(low) + _s(close)) / 3
>     rmf = tp * _s(volume)
>     dtp = tp.diff()
>     pos = rmf.where(dtp > 0, 0.0).rolling(n, min_periods=n).sum()
>     neg = rmf.where(dtp < 0, 0.0).rolling(n, min_periods=n).sum()
>     mr = pos / neg.replace(0, np.nan)         # zero negative => NaN
>     return (100 - 100 / (1 + mr)).to_numpy()
> 
> 
> def ema(close, n):
>     return _s(close).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy()
> 
> 
> def macd(close, fast=12, slow=26, signal=9):
>     ef = _s(close).ewm(span=fast, adjust=False, min_periods=fast).mean()
>     es = _s(close).ewm(span=slow, adjust=False, min_periods=slow).mean()
>     line = ef - es
>     sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
>     return line.to_numpy(), sig.to_numpy()
> 
> 
> def hammer(open_, high, low, close):
>     o = np.asarray(open_, float)
>     h = np.asarray(high, float)
>     l = np.asarray(low, float)
>     c = np.asarray(close, float)
>     body = np.abs(c - o)
>     lower = np.minimum(o, c) - l
>     upper = h - np.maximum(o, c)
>     rng = h - l
>     ok = (body > 0) & (rng > 0)
>     return ok & (lower >= 2 * body) & (upper <= body)
> 
> 
> def bullish_engulfing(open_, close):
>     o = np.asarray(open_, float)
>     c = np.asarray(close, float)
>     po = np.roll(o, 1)
>     pc = np.roll(c, 1)
>     po[0] = np.nan
>     pc[0] = np.nan
>     prev_red = pc < po
>     cur_green = c > o
>     engulf = (o <= pc) & (c >= po)
>     return prev_red & cur_green & engulf
> 
> 
> def fvg_bull(high, low):
>     h = np.asarray(high, float)
>     l = np.asarray(low, float)
>     out = np.zeros(len(h), bool)
>     out[2:] = l[2:] > h[:-2]
>     return out
> 
> 
> def pivot_low(low, left=2, right=2):
>     """Confirmed pivot low. Emitted at i = c + right (never at c)."""
>     l = np.asarray(low, float)
>     n = len(l)
>     out = np.zeros(n, bool)
>     for i in range(left + right, n):
>         c = i - right
>         if (l[c] == np.min(l[c - left:c + right + 1])
>                 and l[c] < l[c - 1] and l[c] < l[c + 1]):
>             out[i] = True
>     return out
> 
> 
> def rsi_bull_divergence(low, close, n=14, lookback=20, left=2, right=2):
>     """Bullish RSI divergence between successive confirmed pivots.
> 
>     Previous pivot is updated at EVERY confirmed pivot; emission only when
>     current pivot low is strictly lower and RSI strictly higher+finite and
>     (c - prev_c) <= lookback.
>     """
>     l = np.asarray(low, float)
>     r = rsi(close, n)
>     piv = pivot_low(low, left, right)
>     n_ = len(l)
>     out = np.zeros(n_, bool)
>     last_pl_idx = None
>     last_pl_low = None
>     last_pl_rsi = None
>     for i in range(n_):
>         if piv[i]:
>             c = i - right
>             cur_low = l[c]
>             cur_rsi = r[c]
>             if last_pl_idx is not None and (c - last_pl_idx) <= lookback:
>                 if (cur_low < last_pl_low
>                         and not np.isnan(cur_rsi) and not np.isnan(last_pl_rsi)
>                         and cur_rsi > last_pl_rsi):
>                     out[i] = True
>             last_pl_idx, last_pl_low, last_pl_rsi = c, cur_low, cur_rsi
>     return out
> 
> 
> def wilder_atr(high, low, close, n=14):
>     """ATR-14 Wilder: TR=max(H-L,|H-Cprev|,|L-Cprev|); first TR=H-L.
> 
>     alpha=1/n, adjust=False, min_periods=n (first ATR readable at bar n-1).
>     """
>     h = _s(high)
>     l = _s(low)
>     pc = _s(close).shift(1)
>     tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
>     tr.iloc[0] = (h - l).iloc[0]                 # first TR = H-L exactly
>     atr = tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
>     return atr.to_numpy()
> 
> 
> # --------------------------------------------------------------------------
> # the complete 52-setting catalogue
> # --------------------------------------------------------------------------
> def build_masks(d):
>     """d: dict of arrays o,h,l,c,v,tbv (floats).  Returns {name: bool array}.
> 
>     Definition order and formulas identical to the pinned executable 52-grid.
>     """
>     o, h, l, c, v, tbv = (d["o"], d["h"], d["l"], d["c"], d["v"], d["tbv"])
>     S = {}
>     for per in (7, 14, 21):
>         r = rsi(c, per)
>         for thr in (20, 25, 30):
>             S[f"RSI{per}_xup_{thr}"] = cross_up_through(r, thr)
>     for (n, dd) in ((14, 3), (21, 5)):
>         k, _ = stochastic(h, l, c, n, dd)
>         for thr in (15, 20, 25):
>             S[f"Stoch{n}_{dd}_xup_{thr}"] = cross_up_through(k, thr)
>     for k in (2.0, 2.5, 3.0):
>         low_b, _, _ = bollinger(c, 20, k)
>         S[f"BB20_{k}_reenter"] = cross_above(c, low_b)
>     for (a, b) in ((20, 50), (50, 200), (20, 200)):
>         S[f"EMA_x_{a}_{b}"] = cross_above(ema(c, a), ema(c, b))
>     for p in (50, 200):
>         S[f"PX_x_EMA{p}"] = cross_above(c, ema(c, p))
>     for (f, s, sg) in ((12, 26, 9), (5, 35, 5)):
>         ml, sl = macd(c, f, s, sg)
>         S[f"MACD_{f}_{s}_{sg}_xup"] = cross_above(ml, sl)
>     for n in (14, 25):
>         au, ad = aroon(h, l, n)
>         S[f"Aroon{n}_bull_x"] = cross_above(au, ad)
>     for n in (10, 20, 55):
>         lo, up = donchian(h, l, c, n)
>         S[f"Donchian{n}_break"] = np.asarray(c, float) > up      # state
>     lo, up = donchian(h, l, c, 20)
>     S["Donchian20_fail"] = ((np.asarray(h, float) > up)
>                             & (np.asarray(c, float) <= up))
>     vz = rolling_z(v, 50)
>     for z in (1.5, 2.0, 2.5, 3.0):
>         S[f"VolSpike_z{z}"] = vz >= z
>     v_arr = np.asarray(v, float)
>     ratio = np.divide(np.asarray(tbv, float), v_arr,
>                       out=np.full(len(v_arr), np.nan), where=v_arr > 0)
>     for thr in (0.48, 0.50, 0.52, 0.55):
>         S[f"TakerRatio_gt_{thr}"] = ratio > thr
>     rz = rolling_z(ratio, 50)
>     for z in (1.5, 2.0, 2.5):
>         S[f"TakerRatioZ_ge_{z}"] = rz >= z
>     for n in (14, 20):
>         S[f"CCI{n}_xup_-100"] = cross_up_through(cci(h, l, c, n), -100)
>     for n in (14, 21):
>         S[f"WilliamsR{n}_xup_-80"] = cross_up_through(williams_r(h, l, c, n), -80)
>     for n in (14,):
>         S[f"MFI{n}_xup_20"] = cross_up_through(mfi(h, l, c, v, n), 20)
>     S["Hammer"] = hammer(o, h, l, c)
>     S["BullEngulfing"] = bullish_engulfing(o, c)
>     S["FVG_single"] = fvg_bull(h, l)
>     for per in (14, 21):
>         S[f"RSI{per}_bull_divergence"] = rsi_bull_divergence(l, c, per)
>     # canonical order + exact 52 membership
>     assert set(S) == set(SETTINGS_52), sorted(set(S) ^ set(SETTINGS_52))
>     return {name: np.asarray(S[name], dtype=bool) for name in SETTINGS_52}
> 
> 
> # --------------------------------------------------------------------------
> # name-driven construction (used by neighbour perturbation): rebuild any
> # setting mask from its name alone; equivalence to build_masks is tested.
> # --------------------------------------------------------------------------
> def build_one(d, name):
>     """Mask for one setting name (possibly perturbed); same primitives."""
>     import re
>     o, h, l, c, v, tbv = (d["o"], d["h"], d["l"], d["c"], d["v"], d["tbv"])
>     o = np.asarray(o, float); h = np.asarray(h, float)
>     l = np.asarray(l, float); c = np.asarray(c, float)
>     v = np.asarray(v, float); tbv = np.asarray(tbv, float)
>     def f(t):
>         return float(t)
>     m = re.fullmatch(r"RSI(\d+)_xup_(-?\d+)", name)
>     if m:
>         return cross_up_through(rsi(c, int(m.group(1))), f(m.group(2)))
>     m = re.fullmatch(r"RSI(\d+)_bull_divergence", name)
>     if m:
>         return rsi_bull_divergence(l, c, int(m.group(1)))
>     m = re.fullmatch(r"Stoch(\d+)_(\d+)_xup_(\d+)", name)
>     if m:
>         k, _ = stochastic(h, l, c, int(m.group(1)), int(m.group(2)))
>         return cross_up_through(k, f(m.group(3)))
>     m = re.fullmatch(r"BB(\d+)_([\d.]+)_reenter", name)
>     if m:
>         low_b, _, _ = bollinger(c, int(m.group(1)), f(m.group(2)))
>         return cross_above(c, low_b)
>     m = re.fullmatch(r"EMA_x_(\d+)_(\d+)", name)
>     if m:
>         return cross_above(ema(c, int(m.group(1))), ema(c, int(m.group(2))))
>     m = re.fullmatch(r"PX_x_EMA(\d+)", name)
>     if m:
>         return cross_above(c, ema(c, int(m.group(1))))
>     m = re.fullmatch(r"MACD_(\d+)_(\d+)_(\d+)_xup", name)
>     if m:
>         ml, sl = macd(c, int(m.group(1)), int(m.group(2)), int(m.group(3)))
>         return cross_above(ml, sl)
>     m = re.fullmatch(r"Aroon(\d+)_bull_x", name)
>     if m:
>         au, ad = aroon(h, l, int(m.group(1)))
>         return cross_above(au, ad)
>     m = re.fullmatch(r"Donchian(\d+)_break", name)
>     if m:
>         _lo, up = donchian(h, l, c, int(m.group(1)))
>         return np.asarray(c, float) > up
>     m = re.fullmatch(r"Donchian(\d+)_fail", name)
>     if m:
>         _lo, up = donchian(h, l, c, int(m.group(1)))
>         return (np.asarray(h, float) > up) & (np.asarray(c, float) <= up)
>     m = re.fullmatch(r"VolSpike_z([\d.]+)", name)
>     if m:
>         return rolling_z(v, 50) >= f(m.group(1))
>     m = re.fullmatch(r"TakerRatio_gt_([\d.]+)", name)
>     if m:
>         ratio = np.divide(tbv, v, out=np.full(len(v), np.nan), where=v > 0)
>         return ratio > f(m.group(1))
>     m = re.fullmatch(r"TakerRatioZ_ge_([\d.]+)", name)
>     if m:
>         ratio = np.divide(tbv, v, out=np.full(len(v), np.nan), where=v > 0)
>         return rolling_z(ratio, 50) >= f(m.group(1))
>     m = re.fullmatch(r"CCI(\d+)_xup_(-?\d+)", name)
>     if m:
>         return cross_up_through(cci(h, l, c, int(m.group(1))), f(m.group(2)))
>     m = re.fullmatch(r"WilliamsR(\d+)_xup_(-?\d+)", name)
>     if m:
>         return cross_up_through(williams_r(h, l, c, int(m.group(1))),
>                                 f(m.group(2)))
>     m = re.fullmatch(r"MFI(\d+)_xup_(\d+)", name)
>     if m:
>         return cross_up_through(mfi(h, l, c, v, int(m.group(1))),
>                                 f(m.group(2)))
>     if name == "Hammer":
>         return hammer(o, h, l, c)
>     if name == "BullEngulfing":
>         return bullish_engulfing(o, c)
>     if name == "FVG_single":
>         return fvg_bull(h, l)
>     raise KeyError(f"unrecognised setting name: {name}")
> 
> 
> def numeric_tokens(name):
>     """Numeric tokens of a setting name as [(text, value, kind, decimals)].
> 
>     kind: 'period' (integer bars), 'threshold' or 'band' (multiplicative),
>     'z' (z-score threshold).  Structural names return [].
>     """
>     import re
>     out = []
>     pats = [
>         (r"^RSI(\d+)_xup_(-?\d+)$", ["period", "threshold"]),
>         (r"^RSI(\d+)_bull_divergence$", ["period"]),
>         (r"^Stoch(\d+)_(\d+)_xup_(\d+)$", ["period", "period", "threshold"]),
>         (r"^BB(\d+)_([\d.]+)_reenter$", ["period", "band"]),
>         (r"^EMA_x_(\d+)_(\d+)$", ["period", "period"]),
>         (r"^PX_x_EMA(\d+)$", ["period"]),
>         (r"^MACD_(\d+)_(\d+)_(\d+)_xup$", ["period", "period", "period"]),
>         (r"^Aroon(\d+)_bull_x$", ["period"]),
>         (r"^Donchian(\d+)_(break|fail)$", ["period"]),
>         (r"^VolSpike_z([\d.]+)$", ["z"]),
>         (r"^TakerRatio_gt_([\d.]+)$", ["threshold"]),
>         (r"^TakerRatioZ_ge_([\d.]+)$", ["z"]),
>         (r"^CCI(\d+)_xup_(-?\d+)$", ["period", "threshold"]),
>         (r"^WilliamsR(\d+)_xup_(-?\d+)$", ["period", "threshold"]),
>         (r"^MFI(\d+)_xup_(\d+)$", ["period", "threshold"]),
>     ]
>     for pat, kinds in pats:
>         m = re.fullmatch(pat, name)
>         if m:
>             for txt, kind in zip(m.groups(), kinds):
>                 dec = len(txt.split(".")[1]) if "." in txt else 0
>                 out.append((txt, float(txt), kind, dec))
>             return out
>     return out
> 
> 
> def perturb_name(name, idx, factor):
>     """Perturb numeric token idx of a setting name by factor (+-20% steps).
> 
>     Periods are rounded half-up with a minimum of two; thresholds/bands keep
>     their original decimal precision.  Returns (new_name, spec) or (None,
>     spec) when the perturbation is invalid (ordering broken or unchanged).
>     """
>     import re
>     toks = numeric_tokens(name)
>     if idx >= len(toks):
>         return None, {"reason": "no such numeric token"}
>     txt, val, kind, dec = toks[idx]
>     new_val = val * factor
>     if kind == "period":
>         new_val = int(np.floor(new_val + 0.5))
>         if new_val < 2:
>             new_val = 2
>         new_txt = str(new_val)
>     else:
>         new_val = round(new_val + 0.0, dec) if dec else int(np.floor(new_val + 0.5))
>         new_txt = f"{new_val:.{dec}f}" if dec else str(new_val)
>     spec = {"index": idx, "old": val, "new": new_val, "kind": kind,
>             "factor": factor}
>     if new_txt == txt:
>         spec["reason"] = "rounds to the same value"
>         return None, spec
>     # rebuild the name with the token replaced
>     spans = [m.span() for m in re.finditer(r"-?\d+(?:\.\d+)?", name)]
>     if idx >= len(spans):
>         return None, {"reason": "span mismatch"}
>     a, b = spans[idx]
>     new_name = name[:a] + new_txt + name[b:]
>     # keep fast < slow for EMA / MACD
>     if new_name.startswith("EMA_x_") or new_name.startswith("MACD_"):
>         nums = [float(t) for t in re.findall(r"\d+(?:\.\d+)?", new_name)]
>         if new_name.startswith("EMA_x_") and not (nums[0] < nums[1]):
>             return None, {"reason": "fast>=slow", **spec}
>         if new_name.startswith("MACD_") and not (nums[0] < nums[1]):
>             return None, {"reason": "fast>=slow", **spec}
>     return new_name, spec

### DEF-2eb9ed4752203dd6 — L0088_SINGLETONS / L0088.primitives

reviewed_indicator_signal

> """36 preregistered causal singleton signals; separate scalar reference."""
> import math
> import numpy as np
> import pandas as pd
> 
> def catalogue():
>  out=[]
>  def add(f,**q):out.append({'id':f+'_'+ '_'.join(str(v) for v in q.values()),'family':f,**q})
>  for n in [10,20,30]:
>   for k in [2,2.5]:add('BB',n=n,k=k)
>  for n in [10,14,21]:
>   for t in [-150,-100]:add('CCI',n=n,t=t)
>  for n in [10,20,30]:add('EMA_RECLAIM',n=n)
>  for n in [10,20,40]:add('DONCHIAN_RECLAIM',n=n)
>  for f,s in [(5,20),(10,30),(20,50)]:add('OBV_EMA',fast=f,slow=s)
>  for n in [1,3,6]:
>   for t in [.52,.56]:add('TAKER_PRESSURE',n=n,t=t)
>  for n in [20,30]:add('SQUEEZE_BREAK',n=n)
>  for n in [10,14,21]:
>   for t in [30,40]:add('RSI_RECLAIM',n=n,t=t)
>  add('MACD_REFERENCE',fast=12,slow=26,signal=9)
>  assert len(out)==36 and len({x['id'] for x in out})==36
>  return out
> 
> def primitives(d,scalar=False):
>  c,h,l,v,t=[np.asarray(d[k],float) for k in ['c','h','l','v','tbv']];N=len(c)
>  def roll(x,n,kind):
>   if not scalar:return getattr(pd.Series(x).rolling(n,min_periods=n),kind)().to_numpy()
>   a=np.full(N,np.nan)
>   for i in range(n-1,N):
>    z=x[i-n+1:i+1]
>    if not np.isfinite(z).all():continue
>    a[i]=sum(z)/n if kind=='mean' else sum(z) if kind=='sum' else min(z) if kind=='min' else max(z)
>   return a
>  def ema(x,n,alpha=None):
>   alpha=2/(n+1) if alpha is None else alpha
>   if not scalar:return pd.Series(x).ewm(alpha=alpha,adjust=False,min_periods=n).mean().to_numpy()
>   a=np.full(N,np.nan);s=None;count=0
>   for i,val in enumerate(x):
>    if not math.isfinite(val):continue
>    s=val if s is None else (1-alpha)*s+alpha*val;count+=1
>    if count>=n:a[i]=s
>   return a
>  def cross(x,y,through=False):
>   if np.isscalar(y):y=np.full(N,y)
>   return np.r_[False,(x[:-1]<y[:-1] if through else x[:-1]<=y[:-1])&(x[1:]>=y[1:] if through else x[1:]>y[1:])]
>  def shift(x):return np.r_[np.nan,x[:-1]]
>  tp=(h+l+c)/3;obv=np.cumsum(np.r_[0,np.sign(np.diff(c))]*v);out={}
>  for q in catalogue():
>   f=q['family'];n=q.get('n')
>   if f in ['BB','SQUEEZE_BREAK']:
>    mean=roll(c,n,'mean')
>    if scalar:sd=np.array([math.sqrt(sum((z-mean[i])**2 for z in c[i-n+1:i+1])/n) if i>=n-1 else np.nan for i in range(N)])
>    else:sd=pd.Series(c).rolling(n,min_periods=n).std(ddof=0).to_numpy()
>    if f=='BB':band=mean-q['k']*sd;truth=(l<=band)&(c>band)
>    else:
>     width=4*sd/mean;prev=shift(width)
>     if scalar:
>      threshold=np.array([float(np.quantile(prev[i-119:i+1],.2,method='linear')) if i>=119 and np.isfinite(prev[i-119:i+1]).all() else np.nan for i in range(N)])
>     else:threshold=pd.Series(prev).rolling(120,min_periods=120).quantile(.2,interpolation='linear').to_numpy()
>     squeeze=width<=threshold;breakout=c>roll(shift(h),20,'max');truth=np.zeros(N,bool)
>     if not scalar:
>      armed=None
>      for i in range(N):
>       if squeeze[i] and (i==0 or not squeeze[i-1]):armed=i
>       if armed is not None and i-armed>2:armed=None
>       if armed is not None and breakout[i]:truth[i]=True;armed=None
>     else:
>      deadline=-1;previous=False
>      for i,(sq,bk) in enumerate(zip(squeeze,breakout)):
>       if sq and not previous:deadline=i+2
>       if i<=deadline and bk:truth[i]=True;deadline=-1
>       previous=bool(sq)
>   elif f=='CCI':
>    mean=roll(tp,n,'mean')
>    dev=np.array([sum(abs(z-mean[i]) for z in tp[i-n+1:i+1])/n if i>=n-1 else np.nan for i in range(N)])
>    x=np.divide(tp-mean,.015*dev,out=np.full(N,np.nan),where=dev>0);truth=cross(np.round(x,10),q['t'],True)
>   elif f=='EMA_RECLAIM':truth=cross(c,ema(c,n))
>   elif f=='DONCHIAN_RECLAIM':bottom=roll(shift(l),n,'min');truth=(l<bottom)&(c>bottom)
>   elif f=='OBV_EMA':truth=cross(ema(obv,q['fast']),ema(obv,q['slow']))
>   elif f=='TAKER_PRESSURE':total=roll(v,n,'sum');x=roll(t,n,'sum')/total;truth=cross(x,q['t'],True)
>   elif f=='RSI_RECLAIM':
>    delta=np.r_[np.nan,np.diff(c)];up=ema(np.maximum(delta,0),n,1/n);dn=ema(np.maximum(-delta,0),n,1/n);rs=np.divide(up,dn,out=np.full(N,np.nan),where=dn>0);x=100-100/(1+rs);truth=cross(x,q['t'],True)
>   elif f=='MACD_REFERENCE':
>    line=ema(c,q['fast'])-ema(c,q['slow']);truth=cross(line,ema(line,q['signal']))
>   else:raise ValueError(f)
>   out[q['id']]=truth & ~np.r_[False,truth[:-1]]
>  return out

### DEF-61434560613f9b68 — OBV_EMA / L0090.states

persistent_volume_state

> """Causal persistent states, independent rolling/EMA scalar reference."""
> import numpy as np
> import pandas as pd
> 
> def states(d,scalar=False):
>  c,v,t=[np.asarray(d[k],float) for k in ['c','v','tbv']];N=len(c);out={}
>  for n in [1,3,6]:
>   if scalar:
>    total=np.array([sum(v[i-n+1:i+1]) if i>=n-1 else np.nan for i in range(N)])
>    buys=np.array([sum(t[i-n+1:i+1]) if i>=n-1 else np.nan for i in range(N)])
>   else:
>    total=pd.Series(v).rolling(n,min_periods=n).sum().to_numpy();buys=pd.Series(t).rolling(n,min_periods=n).sum().to_numpy()
>   ratio=np.divide(buys,total,out=np.full(N,np.nan),where=total>0)
>   for threshold in [.52,.56]:out[f'TAKER_PRESSURE_{n}_{threshold}']=np.isfinite(ratio)&(np.round(ratio,10)>=threshold)
>  if scalar:
>   obv=np.zeros(N)
>   for i in range(1,N):obv[i]=obv[i-1]+(1 if c[i]>c[i-1] else -1 if c[i]<c[i-1] else 0)*v[i]
>  else:obv=np.cumsum(np.r_[0,np.sign(np.diff(c))]*v)
>  def ema(span):
>   if not scalar:return pd.Series(obv).ewm(span=span,adjust=False,min_periods=span).mean().to_numpy()
>   x=np.full(N,np.nan);current=None;a=2/(span+1)
>   for i,val in enumerate(obv):
>    current=val if current is None else (1-a)*current+a*val
>    if i+1>=span:x[i]=current
>   return x
>  for f,s in [(5,20),(10,30),(20,50)]:
>   fast,slow=ema(f),ema(s);out[f'OBV_EMA_{f}_{s}']=np.isfinite(fast)&np.isfinite(slow)&(np.round(fast-slow,10)>0)
>  return out

### DEF-6a2858ffd72ce86a — PRICE_RECOVERY / L0091

registered_rule

> At close,close>max(high of strictly prior n bars);optional current low>=min(low of strictly prior2 bars);alert only false-to-true of that full condition. No future-confirmed pivots,CCI orvolume gates.

### DEF-0c52b2761d322e46 — CANDLE_L0092 / L0092.pattern_and_signals

registered_candle_confirmation

> import numpy as np
> 
> def definitions():
>  return [{'kind':'HAMMER','ratio':r} for r in [2.,3.]]+[{'kind':'ENGULF','ratio':r} for r in [1.,1.25]]+[{'kind':'MORNING','recovery':r} for r in [.5,1.]]
> def pattern(d,q,scalar=False):
>  o,h,l,c=[np.asarray(d[k],float) for k in ['o','h','l','c']];N=len(c);body=abs(c-o);span=h-l;upper=h-np.maximum(o,c);lower=np.minimum(o,c)-l;truth=np.zeros(N,bool)
>  for i in range(7,N):
>   down=c[i-1]<c[i-7]
>   if q['kind']=='HAMMER':v=body[i]>0 and span[i]>0 and lower[i]>=q['ratio']*body[i] and upper[i]<=body[i] and body[i]<=.35*span[i] and (c[i]-l[i])/span[i]>=.6
>   elif q['kind']=='ENGULF':v=c[i-1]<o[i-1] and c[i]>o[i] and o[i]<=c[i-1] and c[i]>=o[i-1] and body[i]>=q['ratio']*body[i-1]
>   else:v=c[i-2]<o[i-2] and span[i-2]>0 and body[i-2]>=.5*span[i-2] and body[i-1]<=.3*body[i-2] and c[i]>o[i] and span[i]>0 and body[i]>=.5*span[i] and c[i]>=c[i-2]+q['recovery']*body[i-2]
>   truth[i]=down and v
>  if scalar:
>   ref=np.zeros(N,bool)
>   for i in range(7,N):
>    if not d['c'][i-1]<d['c'][i-7]:continue
>    O,H,L,C=map(float,[d[k][i] for k in ['o','h','l','c']]);B=abs(C-O);S=H-L
>    if q['kind']=='HAMMER':ref[i]=B>0 and S>0 and min(O,C)-L>=q['ratio']*B and H-max(O,C)<=B and B/S<=.35 and (C-L)/S>=.6
>    elif q['kind']=='ENGULF':po,pc=float(d['o'][i-1]),float(d['c'][i-1]);ref[i]=pc<po and C>O and O<=pc and C>=po and B>=q['ratio']*abs(pc-po)
>    else:
>     po,pc,ph,pl=[float(d[k][i-2]) for k in ['o','c','h','l']];mid=abs(float(d['c'][i-1])-float(d['o'][i-1]));ref[i]=pc<po and ph>pl and po-pc>=.5*(ph-pl) and mid<=.3*(po-pc) and C>O and S>0 and B>=.5*S and C>=pc+q['recovery']*(po-pc)
>   truth=ref
>  return truth&~np.r_[False,truth[:-1]]
> 
> def signals(d,q,scalar=False):
>  import signals88 as S
>  a=pattern(d,q,scalar);mode=q['mode']
>  if mode=='STANDALONE':return a
>  name='CCI_21_-150' if q['asset']=='SOLUSDT' else 'CCI_14_-150';b=S.primitives(d,scalar)[name]
>  if mode=='CCI_AND_CURRENT':truth=a&b
>  elif scalar:truth=np.array([bool(a[i] and any(i-j>=0 and b[i-j] for j in [1,2])) for i in range(len(a))])
>  else:truth=a&(np.r_[False,b[:-1]]|np.r_[False,False,b[:-2]])
>  return truth&~np.r_[False,truth[:-1]]

