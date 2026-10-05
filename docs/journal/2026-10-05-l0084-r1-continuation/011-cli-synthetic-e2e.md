# L0084-R1 tick 011 — synthetic measure/audit CLI path

- UTC: 2026-10-05T14:01:12Z
- Asia/Aden: 2026-10-05T17:01:12+03:00
- Question: can the actual measure and audit CLI handlers run the shared candidate pipeline, writers, persistence/readback and independent rebuild on injected synthetic panels?
- Validity: synthetic-only; no market data/outcomes or GitHub network writes; finalist is forced only for control-path coverage and is not a research selection.
- Result: `synthetic-readiness` observed both handler exit codes as zero; 765 candidate-window groups, 1,442 trades, 697 raw partitions, 2,295 final metric rows, 1,248 control rows, 68 zero-trade groups; independent audit violations 0.
- Resources: peak workspace 121,232,446 bytes; peak RSS 236,105,728 bytes; largest Parquet 28,885 bytes; run artifacts 7,344,200 bytes.
- Limitation: run preceded the latest resume/audit fixes and used unpublished code. Rerun after publication, test a labelled immutable real-branch synthetic upload/readback, and complete readiness checks. Gate stays CLOSED.
- Next: publish this implementation, rerun synthetic readiness on its commit, then perform only the authorized small R1 network artifact test before considering the experiment.
