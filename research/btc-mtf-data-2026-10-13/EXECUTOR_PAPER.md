# BTC-MTF-DATA-01 — ورقة جمع بيانات السنة وتجهيز الفريمات

هذه المهمة تجمع بيانات البيتكوين الدقيقة وتبني منها فريمات1 و5 و15 و60 دقيقة. لا تختبر إشارات ولا تختار حالات صعود؛ تأتي دراسة الحالات بعد قبول البيانات المستقل. مؤشرات الدراسة التالية ثابتةATR14،EMA20،MACD12/26/9،RSI14 والحجم. لا يعود شرط0.3% أو الساعة معيارًا للحكم على الحالات.

## 1. Question
Collect and verify contiguous BTCUSDT Spot minute data, then construct UTC closed frames. One topic: data admission preparation.
## 2. Why now
Six selected days cannot establish recurrence. Multi-frame analysis needs continuous prehistory and exact closed-bar timing.
## 3. What we already know
One actual Binance source month was processed:43200 minute rows,8640 five-minute,2880 fifteen-minute,720 hourly. Source SHA256 is in readiness receipts. No year result exists.
## 4. Hypothesis
No predictive hypothesis; data quality only.
## 5. Data
Planned collection2025-09-01T00:00Z through2026-10-01T00:00Z exclusive. Analysis2025-10-01 through2026-10-01:525600 minute bars. September2025 warmup43200 minutes. Source monthly Binance BTCUSDT1m zip and CHECKSUM. Expected total568800/113760/37920/9480 bars at1/5/15/60min. Source inventory must prove every planned month available; any unavailable month blocks release. No silently reduced or shifted period.
## 6. Container
Not measured: future events, barriers, horizons, positions and costs. No future labels in this task. The later state study must describe observed movements without one mandatory rise percentage or one mandatory duration.
## 7. Baseline
Not measured: no-signal/financial baseline outside data collection.
## 8. Grid
Exactly four frames1,5,15,60minutes. UTC-aligned complete buckets only; open=first, high=max, low=min, close=last, additive volumes/trades. No indicator parameter grid.
## 9. Splits
Warmup and analysis calendar are registered; no candidate selection or blind validation. Historical exposure remains declared. Never claim untouched data.
## 10. Attempt budget
13 monthly archives,13 checksum texts, four frame outputs. No strategy attempts.
## 11. Required statistics
Row counts, coverage, duplicate/gap rejection, original decimal preservation, checksums, full higher-frame reconciliation, actual bytes and elapsed duration. All financial fields: not measured — outside this phase.
## 12. Integrity checks
Reject any checksum mismatch, wrong column count, bad timestamp unit, gap/duplicate, impossible OHLC or volume, partial bucket, frame mismatch or resource exceedance. Microseconds normalize to milliseconds; close_time=end-1ms. Frame available_at=open+duration. Use latest available_at<=decision, never the still-open current higher frame. Closed-alignment test cases are in readiness.py.
## 13. Acceptance criterion
Exact four expected counts and calendar, zero integrity defects, PASS automated audit; status stays Lead-review-pending until independent admission. No predictive or financial adoption.
## 14. Rejection criterion
Any integrity or resource defect. Missing archives stop the task, not permission to manufacture bars. Checkpoint and report actual reason.
## 15. What will not be measured
Indicators, recurrence, forecast precision, orderbook, profit, exits, fees, other coins and frame optimization.
## 16. Deliverables
execution/raw/*.zip and *.CHECKSUM retained; execution/frames/BTCUSDT-{1,5,15,60}m.csv.gz; execution/manifest.json; execution/audit.json; execution/execution-timing.json. CSV12 fields:open_time_ms,open,high,low,close,volume_base,close_time_ms,volume_quote,number_of_trades,taker_buy_volume_base,taker_buy_volume_quote,ignore. Manifest records source URLs, original source SHA256, frame SHA256, counts and availability semantics.
## 17. Delivery format
Save all raw evidence and report, publish manifest/audit/timing/readiness plus source code on a work branch only; no main writes or merge. Executor chat ends تم or خطأ: actual reason. Data admission is separate Lead judgment.
## 18. Runnable package
Python3 standard library only. Extract into a NEW dedicated workspace, cd into the directory containing collect.py. Production command:

```bash
python3 collect.py run --scope execution
```

Resume reruns the same command: existing raw archives are checksum verified, no duplicate request for a complete file. Incomplete own .part outputs can be overwritten by the same fetch function; no historic raw evidence deleted. A partially generated canonical frame is rebuilt from retained immutable archives, not appended. Scope cannot be relocated merely to hide storage size.
## 19. Readiness evidence
Actual command run successfully:

```bash
python3 collect.py run --scope rehearsal --rehearsal-month 2025-09
```

Real source one-month pipeline and independent aggregation reconciliation passed. Four closed-only timing cases and two timestamp unit cases passed. This is not a year measurement. Full year source availability and publication readback are release gates recorded separately; do not call the paper final if either remains pending.
## 20. Storage and upload
Repository stevearagonno1/NOVA-DRAGON; preparation branch agent/btc-mtf-data-2026-10-13. Executor work branch agent/btc-mtf-data-execution-2026-10-13, created from the verified preparation commit. Paths:research/btc-mtf-data-2026-10-13/. Publish source and metadata using the available GitHub connector, fetch them back at the returned exact commit and compare bytes before claiming delivery. No credentials in files or chat. Run python3 pack_delivery.py --scope execution --output BTC-year-minute-and-frames.zip. Save that artifact using the available Library create_library_file(file=absolute_path, library_artifact_type="report") tool, then apply returned metadata using the fresh Library skill helper. The existing Library tool route was successfully tested on the one-month4.7MB archive; yearly artifact size is estimated below50MB. If at least50MB, use Library prepared-upload skill route. No uploader development is delegated. Preserve source archives and attach canonical frames plus original checksums and source URLs. Publish delivery.json and manifest/audit metadata on the executor work branch and fetch back at exact commit.

Fresh workspace total125000000bytes maximum. Check before collection, after each download, during frame writing and before delivery. Current old shared conversation workspace exceeds this limit and is not an admitted executor environment. Actual source-size HEAD inventory is recorded; total derived/storage size is an estimate until full execution. Do not delete owner history to force a resource PASS. Expected complete task, including setup, audit and publication, exceeds600seconds and belongs to the executor after all release gates pass.

## Current release status
READY DATA-COLLECTION STAGE — see release-status.json. All13 source archives returned HTTP200 in source-inventory.json; real source one-month CLI completed and audited. Prepared code and existing Library artifact route are available. Actual yearly data and measured artifact/resource sizes are executor outputs, not readiness facts. No indicator engine is delegated: this paper covers data collection only.
