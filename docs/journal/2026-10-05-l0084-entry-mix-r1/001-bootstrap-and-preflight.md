# L0084-R1 tick 001 — bootstrap and preflight

- UTC: 2026-10-05T06:25:16Z
- Asia/Aden: 2026-10-05T09:25:16+03:00
- main: `71f52f0741cdaceb71797b1fe07de07db31fcced`; previous delivery: `d310df96901fa062022db41a35a24c5f229e0459`; new R1 branch rooted at main.
- Workspace bytes at tick: 118,813,452; below the strict 125,000,000-byte limit.
- Local old Parquet files checked against the previous manifest: trades, keys, metrics, controls, metrics-by-asset matched. Several regenerated Markdown/JSON files differed; retained as previous-round artifacts, not R1 evidence.
- Environment: Python 3.13.14, NumPy 2.3.5, pandas 2.2.3, SciPy 1.17.1, pyarrow 25.0.1 (pyarrow installed outside workspace for smoke).
- Mock tests: 7/7 PASS before live smoke. No corrected engine or measurement run.
