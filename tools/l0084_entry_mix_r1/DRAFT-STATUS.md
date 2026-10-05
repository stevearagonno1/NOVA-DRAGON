# L0084-R1 DRAFT status

Last published DRAFT commit: `ed8ab5aeafdb63d9ab13b878718dcc3c2c9ee6d9`; this local workspace has newer changes awaiting the next API publication.

- Gate: CLOSED. Experiment: NOT RUN.
- Current local implementation adds per-asset synchronized bootstrap/breakeven/lift fields, raw-derived controls Parquet with matched counts/seeds/per-asset paired differences and intervals when exact counts match, partitioned half-year CSV, and independent raw-ledger verification for these outputs.
- Synthetic unit audit now uses two assets and candidate, zero-trade, and random-control groups; it verifies saved/read-back artifacts, independent execution and statistical reconstruction, raw metrics/control/half-year reconciliation, and rejects tampered metric/control/half-year rows.
- Remaining: true Holm across 70,330 and power fields; complete no-signal/constituent/equal-book controls and coverage; full shared synthetic measure/audit CLI plus readiness record, including all v7 edge cases/resources/network synthetic evidence; then full experiment/audit/report.
- Validation: `py_compile` passed; pytest 23/23; module self-test 10/10; workspace 67,425,562 bytes (<125,000,000). This is partial progress, not readiness.
