# L0084-R1 DRAFT status

Last published R1 head: `e5cff075a7841f0418137974b958a57481c98067`; parent `868e8c109de147908f4f8b71f58f49ac28dae9a5`. Current workspace contains newer, untested/unpublished edits.

- Gate: CLOSED. Registered market experiment: NOT RUN.
- Implemented locally: streamed full-field trades; descriptive and per-asset metrics with registered synchronized bootstrap; raw, per-asset, control and half-year output; Holm/power partitions; canonical full-field metrics table assembled from raw summary/per-asset tables and adjustment partitions; independent raw-trade rebuild and final-table join audit.
- Latest validation after canonical-table implementation: `py_compile` passed; pytest 23/23. No complete synthetic CLI readiness run has passed.
- Pending: complete control-family outputs and audits (constituents, equal-capital book and fully matched random controls), a documented synthetic mode invoking actual `measure` and `audit` command paths with persistence/readback and observed zero exit codes, all v7 fixture/injection/conflict/resource checks, readiness evidence, preregistration amendment, real measurement, complete independent audit, report and handoff.
- Measurement gate remains deliberately closed. Do not infer readiness from the unit-test fixture. No market outcomes have been read in this continuation.
