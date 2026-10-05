# L0084-R1 DRAFT status

Last published DRAFT commit: `67020fb3118f4a51eabf64544b7ab684c4985d3d`; this workspace contains newer local code awaiting its next authorized API publication.

- Gate: CLOSED. Experiment: NOT RUN.
- Newly implemented locally: raw-derived summary/per-asset metrics with candidate synchronized bootstrap handoff and independent raw-trade recalculation; partitioned controls result Parquet (matched counts, seeds, per-asset paired block differences/CIs where counts match); partitioned half-year CSV with per-asset raw stats; independent audit of metric, control and half-year rows and tamper detection.
- Still incomplete: true Holm adjustments across the preregistered 70,330 family, power fields, complete paired no-signal/constituent controls and mandatory control coverage, complete runnable shared synthetic measure/audit CLI/readiness, actual experiment, full audit and report.
- Validation: `py_compile` passed; pytest 23/23; module self-test 10/10. Synthetic writer/auditor unit fixture uses two assets and four groups, but does not satisfy the full v7 readiness protocol.
