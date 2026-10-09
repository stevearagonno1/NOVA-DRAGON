# Entry singletons fixture package (R3)

This package is a bounded, standard-library-only, **synthetic fixture and acceptance path**. It does not read, download, or score market data, and it makes no market-performance claim. `market_run` must remain false.

## Reproducible commands

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m tools.entry_singletons_v1.run --synthetic --run-id singleton-package-fixture-r3 --out run --no-source-download
PYTHONDONTWRITEBYTECODE=1 python3 -m tools.entry_singletons_v1.tests
```

Run from the package workspace root. The runner requires both `--synthetic` and `--no-source-download`; no market mode or external data reader is implemented. Outputs are compact and budget-checked before writes. The synthetic candle generator yields rows only in memory; it never persists minute fixtures.

The closed registry contains 226 unique single-indicator settings, tested across 3 assets × 3 exclusive labels (2,034 cells), with 24h and 168h outcomes (4,068 candidate rows), plus 36 state controls, for 4,104 fixed summary rows. Empty cells are retained. The 15m trigger uses only the last fully closed hourly context. Outcomes use synthetic minute bars, fixed ATR barriers, adverse-first same-minute handling, and explicit censored rows.

See `scope.json` for the contract, `registry.json` for the exact network, and `checksums.json` for source and package hashes. `tools/entry_singletons_v1` is new research tooling only; no locked engine, bot, original tools, or prior evidence is changed.
