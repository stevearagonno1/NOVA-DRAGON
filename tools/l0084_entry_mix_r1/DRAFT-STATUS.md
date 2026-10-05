# L0084-R1 DRAFT status

Latest published R1 commit: `7cfd480a958a098b25363f9b4f29282b22d62f49`. New local synthetic CLI, pipeline, audit, resume, and test changes are not yet published.

- Gate: CLOSED. Registered market experiment: NOT RUN.
- Implemented locally: streamed full-field trade pipeline; raw/per-asset/final metrics with Holm/power join; no-signal, matched-random, constituent-singleton/pair and equal-book controls; independent raw-trade, metric, control and half-year audit. `audit --rebuild-all` fails closed unless all reconciliations pass.
- Synthetic CLI path: implemented locally using the shared pipeline stages, remote trade/metric writers, injected in-memory Git API and independent `rebuild_all`. Latest observed `synthetic-readiness` run returned measure exit 0, audit exit 0, 765 groups, 1,442 persisted trades, 697 raw partitions, 2,295 final metric rows, 1,248 control rows, 68 zero-trade windows, zero audit violations. Temporary 3-setting grid and forced finalist are synthetic fixture only; no registered selection or market outcome was read. This run's source is still local/unpublished and must be rerun against the published code SHA.
- Latest validation after some later local resume/audit edits: py_compile and pytest 24/24 passed; module tests 10/10 passed. The 90-second synthetic CLI pass preceded those last edits; rerun required.
- Resource observations from that synthetic run: peak workspace 121,232,446 bytes (<125,000,000); peak RSS 236,105,728 bytes; largest Parquet 28,885 bytes; synthetic remote artifacts 7,344,200 bytes. The hard disk headroom was narrow.
- Pending: publish local implementation; rerun synthetic CLI after commit; verify small labelled synthetic remote write/readback; capture readiness evidence. Full readiness and market measurement remain unapproved until those checks and remaining v7 checks pass.
