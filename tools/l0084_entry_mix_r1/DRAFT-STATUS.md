# L0084-R1 DRAFT status

Latest published code commit: `85bb089a5125a365baed5556f22455bbc583b44f`; latest published synthetic artifact commit: `bd8c8141b172758527323fda5931d68f5e048782`. The compatible preregistration-schema fix and updated status are local, pending publication.

- Synthetic CLI readiness on published code SHA `85bb089a5125a365baed5556f22455bbc583b44f`: command exit 0; measure=0 and audit=0; 765 groups, 1,442 trades, 697 raw partitions, 2,295 final metric rows, 1,248 control rows, 68 zero-trade groups, zero audit violations. The synthetic fixture temporarily exercises 3 settings and a forced finalist; it does not alter the registered experiment or count as a market result.
- Real Git transport: a labelled 651-byte synthetic artifact was commit/readback verified at `bd8c8141b172758527323fda5931d68f5e048782`, SHA256 `7ba1410a40844ac92d741bfa00a0683cce7c80110ec20014ed230c5fbb9c16f2`.
- Tests on published code: py_compile PASS; pytest 24/24; module tests 10/10. Synthetic resources: peak workspace 121,239,203 bytes (<125,000,000); peak RSS 234,373,120; max Parquet 28,885 bytes; synthetic run artifacts 7,344,200 bytes.
- Actual experiment has NOT RUN; no market outcomes read. `MEASUREMENT_GATE_READY` is true in code, but `measure` additionally refuses unless the amendment pins the exact source SHA and matching prechecks pass.
- Amendment attempt: blocked before writing because `cmd_amend_prereg` expected a nonexistent `previous['bootstrap']` key. The remote locked preregistration stores those fixed parameters under `multiplicity`. Local remediation now preserves `selection` and `multiplicity`; `py_compile`, pytest 24/24, and module tests 10/10 passed, but amendment has not yet been retried.
- Next: publish the compatible schema fix, retry the implementation-only amendment before outcomes, run matching prechecks, write truthful readiness evidence, and proceed only if all guards pass.
