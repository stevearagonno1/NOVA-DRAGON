# L0084-R1 tick 010 — restart journal integrity correction

- UTC: 2026-10-05T08:39:54Z
- Asia/Aden: 2026-10-05T11:39:54+03:00
- Verified branch head before this documentation-only commit: `8783aa517ceafd2a5893c6d87af5f24f389af48f`.
- A new synthetic restart test exposed duplicate storage-journal receipts when resuming a committed partition whose coverage index had not yet been committed. The writer now reads and verifies existing journal shards, recognizes already-receipted partitions, and avoids duplicate receipts. The orphan-recovery test now continues through full remote reconciliation.
- Added the 125,000,000-byte disk-cap failure test and platform memory-limit/peak-RSS recording. The complete local suite remains 28/28 passing after the correction.
- No market measurement or market-result read. The code remains local/uncommitted. Metrics/report table generation and raw-to-metrics full audit reconciliation are still incomplete; the CLI audit gate now fails closed without that comparison.
- Workspace file bytes: 69,174,215; cap: 125,000,000 bytes.
- Next: implement and test complete candidate, per-asset, control, and summary metric partitions plus independent reconciliation; only then consider publishing code or running prechecks.
