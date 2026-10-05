# L0084-R1 DRAFT status

Last published DRAFT commit: `868e8c109de147908f4f8b71f58f49ac28dae9a5`; current workspace includes newer local changes awaiting publication.

- Gate: CLOSED. Registered market experiment: NOT RUN.
- Implemented: streamed raw trades; descriptive and per-asset metrics with registered synchronized bootstrap; raw/metric/half-year/control table persistence and independent rebuild comparison; matched random controls with independently recalculated paired seven-day CIs; Holm-adjustment and power overlay partitions per candidate family/window with independent raw recalculation.
- Pending: canonical join of adjustments into the required full-field metrics result; full no-signal/constituent/equal-book control tests and complete control/report outputs; full actual `measure --synthetic` and `audit --synthetic` CLI path/readiness record meeting every v7 fixture, injection, conflict, resource and exit-code check. Only then may measurement proceed.
- Latest checks: `py_compile` passed; pytest 23/23; module self-test 10/10; workspace 67,454,260 bytes (<125,000,000). Partial test readiness only.
