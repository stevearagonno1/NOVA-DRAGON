# L0084-R1 tick 003 — premeasurement engine correction

- UTC: 2026-10-05T06:27:48Z
- Asia/Aden: 2026-10-05T09:27:48+03:00
- Engine/test code SHA256: `532e381e539342d1028eee356ec343387f65e004d994e03341d3cd84aa76ea7a` / `eddbceed195d6be2abcff5568b074dc45702c18542d410ec3a8a2629ffd7a0a7`.
- Corrected both scalar and per-start execution paths; included fill bar and all 18 complete bars, guarded incomplete horizon before indexing, and limited ambiguity to the exit bar.
- Independent audit harness 4/4; focused unit suite 16/16 (9 engine + 7 transport).
- Corrected code committed before any measurement. Full 18 integrity checks are NOT RUN; no financial measurement.
- Next: independently verify 52 settings/3,978 pairs and finish all pre-outcome checks.
