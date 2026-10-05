# L0084-R1 tick 013 — locked preregistration field mismatch

- UTC: 2026-10-05T14:09:48Z
- Asia/Aden: 2026-10-05T17:09:48+03:00
- Question: can the implementation-only amendment pin the tested code without changing the frozen research plan?
- Validity: the attempt stopped before producing an amendment or reading outcomes.
- Error: `cmd_amend_prereg` indexed `previous['bootstrap']`; the immutable remote preregistration schema instead stores the fixed 2000-draw/7-day/seed/family values under `multiplicity` and has a textual `selection` field.
- Compatible remediation: preserve the existing container/gates/selection/multiplicity exactly; replace the absent `bootstrap` access. Local `py_compile`, pytest 24/24, and module tests 10/10 pass. No market outcomes read.
- Limitation: remediation is not yet published or exercised; no amendment or prechecks exist, so real measurement remains blocked despite the synthetic CLI pass.
- Next: publish the field-name correction, rerun the amendment command pinned to that exact source commit, and continue only after matching prechecks pass.
