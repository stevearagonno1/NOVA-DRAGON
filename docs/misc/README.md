# NOVA_V8_QUANT_LAB

Institutional-grade, purely **asynchronous** algorithmic trading engine and
forward-profiling backtester, designed to run natively on **Termux** (Android
edge). Toggles between a high-speed historical Parquet simulator
(*Proactive Backtester*) and a live Binance WebSocket execution engine
(*Zero-Wait HFT*) through one shared analytical pipeline.

## Architecture

```
nova_v8/
├── config.py          # env-driven config (modes, endpoints, risk constants)
├── indicators.py      # Module 2 — vectorized math: Wilder ATR, ALMA(200,0.85,5),
│                      #   Cardwell RSI zones, Anchored Powered KAMA + Welford bands,
│                      #   ε-midpoint hysteresis (2.8×ATR53), rolling Hurst(100), ADX, MACD
├── microstructure.py  # Module 5 — Liquidity Sweep (SFP), Monotonic MSS (L=5,
│                      #   body/range>50%, range>0.8×ATR14), Shrink-on-Fill FVG registry
├── orderflow.py       # Module 4 — tick CVD engine + O(1) online Naive-Bayes
│                      #   (z-scored cvdRoc, divergence, slopeR; Bull/Bear/Diverged)
├── regime.py          # Module 3 — 4-state regime tagger (observer ONLY, never blocks)
├── strategies.py      # Module 6 — tournament dispatcher → (Action, Name, Trigger_Price)
│                      #   A: Monotonic_MSS_FVG · B: Liquidity_Sweep_Reversal · C: Micro_Burst_Momentum
├── risk.py            # Module 7 — confidence/volatility sizing + Symbol Governor (600 s)
├── execution.py       # Modules 8/9 — LIMIT_MAKER pegging, 12 s hanging bullet,
│                      #   hard stop 1.15×ATR clamped [0.30%, 3.0%], break-even lock
│                      #   +0.50→+0.45%, synthetic ATR trailing (1.5/1.2×ATR), 60 s time-stop
├── telemetry.py       # Module 10 — SQLite master_log.db, CSV export ordered
│                      #   by Market_Regime ASC, Net_Outcome DESC
├── telegram_bot.py    # Modules 11/12 — stealth long-poll, milestone alerts,
│                      #   inline keyboard dashboard, sendDocument export
data_fetcher.py        # Standalone: downloads 5y×12 × 1m klines → Parquet archives
├── feeds.py           # Module 1 — Parquet precompute+k-way merge replay /
│                      #   multiplexed live WebSocket → asyncio.Queue
├── engine.py          # orchestrator: per-symbol asyncio.Lock, one pipeline, both modes
└── main.py            # entrypoint
```

## Design guarantees

- **Async purity** — no `requests`, no threads except `asyncio.to_thread` for
  parquet/CSV I/O and vectorized precompute. Live mode keeps the loop in deep
  idle: WebSocket → `asyncio.Queue` → decoupled worker task.
- **No repaint / no lookahead** — only closed bars are evaluated; every
  indicator is causal; strategy evaluation reads row `i` strictly after it is final.
- **Zero-threshold profiling** — regime and Naive-Bayes outputs are observers;
  they tag telemetry, they never veto a direction.
- **Friction honesty** — backtest charges 0.1 % maker + 0.1 % taker exactly.
- **Race safety** — per-symbol `asyncio.Lock` around evaluate→open; aiosqlite
  guarded by a lock; single-fire position bookkeeping.

## Termux install

```bash
pkg update && pkg install python tur-repo
pkg install python-pandas python-numpy        # prebuilt wheels (fast, no C-build)
pip install pyarrow aiohttp websockets aiosqlite --no-build-isolation
```

## Run

```bash
# Backtest (reads ~/crypto_archive/{SYMBOL}_1m.parquet, GRAM/RNDR aliases ok)
export NOVA_MODE=backtest NOVA_AUTOSTART=1
python -m nova_v8.main                      # run from the folder CONTAINING nova_v8/

# Live forward-profiling on TESTNET (market data stays on the LIVE ws endpoint)
export NOVA_MODE=live BINANCE_ENV=testnet
export BINANCE_API_KEY=... BINANCE_API_SECRET=...
export TELEGRAM_TOKEN=... TELEGRAM_CHAT_ID=...
python -m nova_v8.main
```

Useful knobs: `NOVA_START/NOVA_END` (slice replay window),
`NOVA_TARGET_TRADES` (milestone denominator), `NOVA_HOME` (db/export dir).

## Notes & documented approximations

- **Hanging bullet in backtest:** 12 s cannot resolve inside 1 m bars; the
  LIMIT_MAKER fill window is approximated as 1 bar (`BACKTEST_FILL_BARS`).
- **Backtest order flow:** true `@aggTrade` delta is unavailable historically;
  the wick-split proxy `V·(C−O)/(H−L)` feeds CVD/NB in replay, and CLV proxies
  book imbalance for Strategy B. Live mode uses the real tick streams.
- **Memory:** 5 y × 12 symbols of 1 m data is heavy for a phone. Indicator
  matrices are computed once per symbol and **cached** as
  `{SYMBOL}__matrix.parquet` next to your archives; use `NOVA_START/NOVA_END`
  to profile smaller windows.
- Trading crypto futures can lose money. Testnet first. This is a quant lab,
  not financial advice.
