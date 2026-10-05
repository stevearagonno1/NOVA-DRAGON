# L0084-R1 tick 012 — published synthetic zero-exit condition

- UTC: 2026-10-05T14:05:57Z
- Asia/Aden: 2026-10-05T17:05:57+03:00
- Question: did the published code complete the actual shared synthetic CLI measure/audit path and real transport readback?
- Validity: published code SHA `35995aac29ad3132b1cdc92795c3a39abf63658f`; synthetic only; real outcomes not read.
- Result: synthetic-readiness command exit 0, measured/audit handlers both 0, full raw and canonical tables reconciled; separate labelled 651-byte real-branch artifact committed/read back at `bd8c8141b172758527323fda5931d68f5e048782`.
- Gate: local draft opens the runner only past the synthetic check; real command still requires a code-pinned preregistration amendment and passing prechecks. The gate change itself is unpublished; real market measurement remains NOT RUN.
- Next: publish the narrowly scoped gate change, rerun tests/readiness on the resulting code SHA, create the amendment and prechecks, then start the registered run if all remain PASS.
