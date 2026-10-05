# L0084-R1 tick 010 — selected-pair constituent-control audit

- UTC: 2026-10-05T13:46:24Z
- Asia/Aden: 2026-10-05T16:46:24+03:00
- Question: does independent control reconciliation cover an actual selected pair and both singleton constituents, not merely hand-labelled rows?
- Validity: synthetic-only fixture, unchanged registered parameters; no market outcomes read.
- Result: expanded the remote rebuild fixture to select a registered pair, independently regenerate constituent singletons, random controls, no-signal, and equal-capital/$20 holds; audit rejects control tampering. Paired bootstrap reference now accepts unequal constituent trade counts.
- Checks: `py_compile` PASS; pytest 24/24 PASS; module tests 10/10 PASS; workspace 67,502,756 bytes.
- Limitation: still no actual CLI synthetic measure/audit mode/readiness record. Measurement gate CLOSED.
- Next: build synthetic invocation through the same measure/audit CLI runner and complete v7 persistence/readback/injection/conflict/resource checks before any market measurement.
