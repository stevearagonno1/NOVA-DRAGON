# 003 — Rise-wave design and data feasibility
2026-10-08. Main source 6d0226a03b84656e14b94dd8a37e39332cc2f68f. Source review dfc51d2f81ff09622afefa7f2e0308120816506a.
Estimate 300s. Captured final analysis interval 203s; earlier pre-compaction interval unavailable, therefore total wall time NOT MEASURED. No market signal measurement.
Verified small SOL file Git blob, SHA256, schema, timestamps, no gaps/duplicates/invalid OHLCV; derived complete 15m/1h/4h July counts. Older MANIFEST describes full archive, not the small file. Default environment has no PyArrow; existing local rewrite84/deps 25.0.1 used successfully; executor dependency preflight still required.
Design uses owner sources, causal uptrend context, daily/weekly outcomes separately, precision-first, no 80% recall-retention condition. Deferred exact signal clauses, de-duplication, onset timing audit, prepared package and synthetic acceptance. This is not an execution paper.
Artifacts: docs/research/rise-waves-design-2026-10-08/. Next: Lead finishes bounded tooling and synthetic checks; executor only prepared long measurement.
