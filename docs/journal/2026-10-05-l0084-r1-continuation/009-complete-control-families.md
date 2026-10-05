# L0084-R1 tick 009 — independent control-family rows

- UTC: 2026-10-05T13:42:41Z
- Asia/Aden: 2026-10-05T16:42:41+03:00
- Question: are finalist control-result rows present and independently rebuilt from raw candidate/control trades?
- Validity: implementation-only; shared control writer and independent audit updated; no market outcomes read.
- Result: added constituent singleton/pair comparisons with synchronized seven-day bootstrap intervals, equal-capital $1000 and separate $20 hold rows, and strict CLI audit reconciliation criteria. Pair-selection synthetic fixture now checks no-signal, random, constituent, and equal-book control families and tamper rejection.
- Checks: `py_compile` PASS; pytest 24/24 PASS; module tests 10/10 PASS; workspace package 67,500,394 bytes.
- Limitation: actual synthetic CLI measure/audit readiness still absent; measurement gate remains CLOSED.
- Next: expose synthetic execution through the actual CLI paths, verify persistence/readback/zero exit statuses and all v7 injections, then publish the resulting evidence before considering measurement.
