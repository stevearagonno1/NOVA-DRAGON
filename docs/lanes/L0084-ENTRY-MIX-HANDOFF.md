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

## next step

- Lead re-derives from `trades_keys.parquet` with `cli audit --rebuild-sample 400`, then decides.
