# L0084-ENTRY-MIX — HANDOFF

## proven

- 12/12 assets retained, one contiguous segment each, zero gaps; mask counters match the pinned 52-grid reference (0/155 cells).
- 18 integrity checks implemented; 14 and 16 proven on synthetic end-to-end data before money; all re-run at audit.
- Measured: 52 singletons + 3,978 pair modes + registered triples per prefix; registries written before outcomes.

## unproven

- Anything after the freeze: **NOT MEASURED**.
- Legacy L0083 headlines are documented, not re-based.

## closed / open

- closed: container definition, grids, gates, rolling selection.
- open: genuine future validation (100 trades AND 90 days).

## pins

- main `71f52f0741cdaceb71797b1fe07de07db31fcced`; grid `62f4d255e0fc6fce8e7c331a6349484ccb0b8fc0`; cost model `2d8e8f3afca6a72679382780ddaeb0d71de2cad6`.
- branch `arena/l0084-entry-mix-2026-10-04` (local evidence repo; nothing pushed, no PR, no main write).

## storage and evidence policy (disclosed)

- `trades_keys.parquet` carries one compact key row per executed trade of the ENTIRE measured grid (13,292,220 rows, 23.4 MB); `cli audit --rebuild-sample N` re-derives every reported number from it byte-exactly. A verified run covered 1,200 sampled candidate-window rows with 0 violations (420 s), plus 40 rows in check 17 and 25 full re-simulations in check 16b.
- `trades.parquet` carries the full per-trade schema for the 52 singletons on all twelve half-years (235,976 rows). Full rows for every one of the ~11.3M grid trades would exceed the binding 125 MB workspace cap; the keys ledger above is the complete alternative and the audit proves the two agree. `reproduce.md` documents the exact rebuild commands.
- Pre-outcome commit ordering (honest note): the local git branch was created before measurement, but the first commit's hash could not be recorded because `git rev-parse HEAD` returned `HEAD` while the index was still empty, and the oversized first `.git` (33 MB of parquet blobs) was later rebuilt with parquet files git-ignored to respect the workspace cap. Ordering evidence therefore rests on the run journal timestamps + file mtimes + recorded sha256 values: `preregistration.json` sha256 ff72b8d4…/f9dc3a78… written 2026-10-04T14:20-14:21Z, before singles (14:23Z) and pairs (14:23-15:02Z) were measured; triples registries were written before their outcomes (check 14).

## next step

- Lead re-derives from `trades_keys.parquet` with `python -m l0084_entry_mix.cli audit --rebuild-sample 1200`, then decides.
