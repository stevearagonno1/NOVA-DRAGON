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