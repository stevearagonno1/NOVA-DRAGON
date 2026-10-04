# L0084-ENTRY-MIX — reproduction (one runnable command per claim)

Environment: python 3.13.14, numpy 2.3.5, pandas 2.2.3, seed 84. Retained market data: `work/{SYM}_4h.parquet` (12 files, sha256 in `data_coverage.csv`).

```bash
export PYTHONPATH=/home/user/l0084-package/tools
# 1. registries + preregistration (before outcomes)
python -m l0084_entry_mix.cli preregister
# 2. integrity (18 checks; 14 and 16 on synthetic end-to-end)
python -m l0084_entry_mix.cli check --phase pre
# 3. full measurement (singles, all 3,978 pair modes, triples)
python -m l0084_entry_mix.cli measure
# 4. tables + Arabic report
python -m l0084_entry_mix.cli summarize
# 5. independent ledger re-derivation + post checks
python -m l0084_entry_mix.cli audit --rebuild-sample 400
# 6. future plan (NOT MEASURED)
python -m l0084_entry_mix.cli future-plan
```

## Claim → command

| claim | command |
|---|---|
| gate counts per prefix | `python -c "import pandas as pd;print(pd.read_csv('selection_log.csv').groupby(['prefix','stage'])['eligible'].sum())"` |
| every reported trade row | `python -m l0084_entry_mix.cli audit --rebuild-sample 400` (rebuilds rows from `trades_keys.parquet` + retained data + locked engine) |
| deterministic rerun equality | `python -m l0084_entry_mix.cli check --phase pre` (checks 14, 16) |
| neighbour ±20% family | `python -m l0084_entry_mix.cli summarize` then read `neighbors.csv` + `neighbors_registry.csv` |

## Artefact hashes (sha256)

| file | sha256 |
|---|---|
| REPORT.md | `dd17449d668433d550a897d36029317af4a9baebc5f5efb09b7b0a6de2a94a6b` |
| catalogue.csv | `2cba5b93691f03ff7ec86e7050bd7560d9a0bbd6246b6539843cfdd72c079405` |
| catalogue_pending.md | `c2278743bd88410168e5c56cb240a4ef5c5a37e5481e05159aa48bccb1a92ab6` |
| checks.json | `b66dc976cc384f16e5fa900220c95fb782f4b45b992a167c7badbe632aa231de` |
| controls.csv | `b899c5e9816bdcae95ba429be80e9f08c695b0a36187c33941dc8613ca1c27bd` |
| controls.parquet | `e10221ad99fb529285888177482285216f71de089da5e12de8e47b489a335b8c` |
| data_coverage.csv | `f9848510f67855417ddf9c5ea0adcaa3caab464c6ba07f955b93b48cf9264487` |
| diagnostics.json | `ce8f8fcf374fdf378f0c63b3381a63e34f87ff9d4de57259078de987bed60fbf` |
| diagnostics_closest.csv | `e0f8c1ba225168c64991f384446c02f755c1cc66ab13506e18b0b83199868e7f` |
| diagnostics_gate_failures.csv | `84f450c00c57aee396f0a6ccf72da9629bbface6b0ab6b8b88ce25a12157d9a8` |
| diagnostics_singles.csv | `4eea139f82b827ae9295b20fe31a442d7b14217ad9d14e5c95315d45362e69e3` |
| frozen_candidate.json | `7aaeceadab6140c00afa969a7a8c3c8db6872fd4cbcee4137191b912edb6b7bd` |
| future_plan.md | `44151046354b73d1a9f16a796229e4af3f2d582086ddc8176cb96c565d2e286a` |
| halfyears.csv | `c3b5013e0ccb48946a6eb4c989b1533ff53945e54903cb61ca1c6a8e3c227844` |
| metrics.parquet | `134823e433ac6ddaa8ead91062805fdb1fd0a381556a8766e476cac468c2aa2d` |
| metrics_by_asset.parquet | `6fcf1f4c442c706f492d911792f2603c49c2b797ea548b8d0bd07ff5442ed863` |
| neighbors.csv | `ef70a71fbb27a7f2c674efcde54df5b55fe05ae87b306f77b834aa50602a8ff8` |
| neighbors_registry.csv | `da9e64b11e78468639566e07511b98a07ac5d3f4b61f24adc7220be37cca410a` |
| outer_windows.csv | `506dc18926bb0c4487f4f277f22e67e0b71e6be8c80b20e481894bae6ffac566` |
| output_hashes.json | `3b8c3503dca2b886b45a98a438caa1904db216b2c5ce3181a9ac34059a6ddc8f` |
| pairs_registry.csv | `a51ee080456c0708722d6732008d5f1fe6e322541d0817ec634d1602619a7d79` |
| preregistration.json | `f9dc3a78aa03bcaa1bbad2ffe7c9dc7a547956daef8344722989b9d39a1f883a` |
| reproduce.md | `e8def0ed8f5e0a8b3284f060e8f47c0639751fb1c769fd820a177935606da742` |
| selection_log.csv | `bc31d50fcb4fb5fddb80052da2c6fab1bb30f788899d778d563e4d8c03340e76` |
| sources.json | `9eb227da435ad61232dfa2d718035d4809c18836d7441ee60988c275fe2f4822` |
| summarize.json | `13b7365a0347274346ee1d158e5a25a55ca529f8dcf5beab716684cdbfb5514b` |
| trades.parquet | `ef0dc3804f553b829776595e2217aaee4aeeeda1fca35f216fa5e001761911f9` |
| trades_keys.index.json | `77b9a5001da03a0cdce165be74f66e84e88d14faf07977bf6ca8f03bf0deb7b3` |
| trades_keys.parquet | `56083b62cce3fdf59fbeade794f63cb876ab9c899be7d87da491f1f09e5bd1a2` |
| trial_counts.md | `eeb209958744cd6c426f267e697ac8120c276252787f7201b9e06631a55a7a1c` |
| triples_registry.csv | `efb2689a5f01fec2e9f1d384b8a9280f0ff2cd5768bfb69aa756b31df083e164` |