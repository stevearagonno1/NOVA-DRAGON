# L0084-R1 DRAFT status

Latest published code commit: `35995aac29ad3132b1cdc92795c3a39abf63658f`; latest R1 branch head after verified synthetic network smoke: `bd8c8141b172758527323fda5931d68f5e048782`. New gate/test changes are local and unpublished.

- Market outcomes: NOT READ. Market experiment: NOT RUN.
- Synthetic CLI readiness path on published code commit `35995aac29ad3132b1cdc92795c3a39abf63658f`: command exit 0; internal measure=0 and audit=0; 765 groups, 1,442 persisted trade rows/697 raw partitions, 2,295 final metric rows, 1,248 control rows, 68 zero-trade groups, zero audit violations. Synthetic runner temporarily used 3 settings and a forced finalist solely to exercise all writer/control paths; no registered selection or market conclusion was produced.
- Real Git transport: a 651-byte synthetic-only artifact was committed on the R1 work branch and read back byte/hash-identically; commit `bd8c8141b172758527323fda5931d68f5e048782`; SHA256 `7ba1410a40844ac92d741bfa00a0683cce7c80110ec20014ed230c5fbb9c16f2`.
- Tests on the pre-gate-change tree: py_compile PASS; pytest 24/24; module tests 10/10. Synthetic resources: peak workspace 121,236,146 bytes (<125,000,000); peak RSS 233,140,224; max Parquet 28,885 bytes; remote synthetic data 7,344,200 bytes.
- Gate: opened in the current local draft only after the published synthetic zero-exit/readback/audit pass. Real `measure` remains guarded by the required implementation amendment and matching prechecks; neither exists yet. No real measurement has started.
- Pending immediate steps: publish the gate/test change; rerun full checks and synthetic path on that SHA; freeze the amendment and prechecks; only then run the registered experiment. Final audit/report/handoffs remain outstanding.
