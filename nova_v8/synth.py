"""Synthetic 1m archive generator — a clearly-labeled stand-in for historical
data.

Purpose (per the 2026-09-10 user order "make it run as if the historical
backtest data were present"): exercise the ENTIRE pipeline — feeds, regime,
triggers, every sleeve, the evaluation layer — at research scale, on data with
all regime types (chop/bull/bear/shock) and a BTC-leading structure, WITHOUT
ever claiming the outputs are historical results. Every artifact produced from
this generator must be labeled synthetic (experiment name, report header).

Design notes (data realism):
- volatility transitions SMOOTHLY (EWMA toward the regime target) so the
  ATR/ATR-SMA100 shock ratio is not inflated by step changes;
- chop is genuinely non-trending (overlapping sines + mean-reverting walk) so
  ADX stays low and the regime map can actually read عرضي;
- shock is a real, short, deep vol spike (also visible in volume);
- deterministic (seeded); file format is the researcher's exact
  ``<SYMBOL>_1m.parquet`` with ``open_time`` epoch-ms + OHLCV, consumable by
  ``feeds.load_matrix`` as-is.

Scale: ``--days`` controls length (default 90). On the user's machine the same
command with ``--days 1825`` produces the 5-year x 12-coin research scale; the
sandbox demo uses a shorter span for runtime.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C

# regime cycle (days) — guarantees every regime type appears in the sample
REGIME_CYCLE: tuple[tuple[str, float], ...] = (
    ("chop", 4.0), ("bull", 3.0), ("chop", 2.0),
    ("bear", 3.0), ("shock", 0.5), ("chop", 2.0),
)
# (drift per 1m, TARGET vol per 1m) — trend segments additionally carry the
# gentle curvature from _market_log_returns (calibration, see its docstring)
REGIME_TARGETS: dict[str, tuple[float, float]] = {
    "chop": (0.0, 0.00050),
    "bull": (0.000022, 0.00070),
    "bear": (-0.000016, 0.00080),
    "shock": (0.0, 0.00350),
}
VOL_EWMA_ALPHA = 0.02          # ~50-min time constant: smooth transitions
MINUTES_PER_DAY = 1440
_CYCLE_DAYS = sum(d for _, d in REGIME_CYCLE)
_CYCLE_BARS = int(_CYCLE_DAYS * MINUTES_PER_DAY)


def _segment_plan(n_bars: int) -> np.ndarray:
    """Per-bar segment index into REGIME_CYCLE for the deterministic cycle."""
    out = np.zeros(n_bars, dtype=np.int8)
    i = 0
    k = 0
    while i < n_bars:
        length = int(REGIME_CYCLE[k][1] * MINUTES_PER_DAY)
        take = min(length, n_bars - i)
        out[i:i + take] = k
        i += take
        k = (k + 1) % len(REGIME_CYCLE)
    return out


def _market_log_returns(n_bars: int, seed: int):
    """BTC (leader) log returns + the smoothed vol path used for wicks/volume.

    Returns ``(ret, vol_path)`` where ``vol_path`` is the EWMA-smoothed
    per-bar volatility (deterministic given the seed).

    Synthetic design note (documented calibration): trend segments carry a
    gentle long-period curvature (sine level with a 5x-segment period) so the
    regime map's own hurst gate reads them as صاعد/هابط. The gate is part of
    the Baseline and is NOT modified here; the generator is calibrated to it.
    Chop segments stay i.i.d. so the gate reads عرضي."""
    rng = np.random.default_rng(seed)
    seg = _segment_plan(n_bars)
    i = np.arange(n_bars)
    drift = np.zeros(n_bars)
    target_vol = np.zeros(n_bars)
    curve = np.zeros(n_bars)
    for k, (name, d) in enumerate(REGIME_CYCLE):
        m = seg == k
        drift[m] = REGIME_TARGETS[name][0]
        target_vol[m] = REGIME_TARGETS[name][1]
        if name in ("bull", "bear"):
            seg_len = int(d * MINUTES_PER_DAY)
            pos = np.where(m)[0]
            t_local = pos - pos[0]
            T = 5.0 * seg_len                 # segment spans ~36 degrees
            A = 0.10 if name == "bull" else -0.10
            lvl = A * np.sin(2.0 * np.pi * t_local / T)
            curve[m] = np.diff(lvl, prepend=0.0)
    # smooth the volatility path (EWMA toward the per-bar target)
    vol = np.empty(n_bars)
    v = target_vol[0]
    for t in range(n_bars):
        v += VOL_EWMA_ALPHA * (target_vol[t] - v)
        vol[t] = v
    # chop texture: two incommensurate sines (no single trend to detect).
    # Applied ONLY inside chop segments.
    chop_idx = [k for k, (nm, _) in enumerate(REGIME_CYCLE) if nm == "chop"]
    chop_mask = np.isin(seg, chop_idx)
    chop = (0.020 * np.sin(2.0 * np.pi * i / 2880.0)
            + 0.012 * np.sin(2.0 * np.pi * i / 1103.0 + 1.3)) * chop_mask
    # mean-reverting AR(1) walk: wanders inside a band, never trends hard
    walk = np.zeros(n_bars)
    for t in range(1, n_bars):
        if chop_mask[t]:
            walk[t] = 0.998 * walk[t - 1] + 0.0004 * rng.standard_normal()
        else:
            walk[t] = walk[t - 1] * 0.9       # decay out of the band
    ret = (drift + vol * rng.standard_normal(n_bars) + curve
           + np.diff(chop, prepend=chop[0]) * 0.5
           + np.diff(walk, prepend=walk[0]))
    return ret, vol


def synth_symbol_ohlcv(n_bars: int, seed: int, start: pd.Timestamp,
                       market_ret: np.ndarray, vol_path: np.ndarray,
                       mkt_weight: float = 1.0) -> pd.DataFrame:
    """One symbol's 1m OHLCV frame (index = 1m DatetimeIndex UTC).

    ``market_ret`` (the leader's log returns) is blended with idiosyncratic
    noise at ``mkt_weight`` for the leader/lag structure of the research
    design."""
    rng = np.random.default_rng(seed)
    if mkt_weight < 1.0:
        idio = 0.0010 * rng.standard_normal(n_bars)
        idio[0] = 0.0
        ret = mkt_weight * market_ret + (1.0 - mkt_weight) * idio
    else:
        ret = market_ret
    lp = np.log(100.0) + np.cumsum(ret)
    c = np.exp(lp)
    o = np.empty(n_bars)
    o[0] = c[0]
    o[1:] = c[:-1]
    wick = (np.abs(rng.normal(0.0, 0.5, n_bars)) * vol_path + 1e-5)
    h = np.maximum(o, c) * (1.0 + wick)
    l = np.minimum(o, c) * (1.0 - wick)
    # volume: lognormal base, reacts to |return|, spikes in shock bars
    v = (1000.0 * np.exp(0.4 * rng.standard_normal(n_bars))
         * (1.0 + 15.0 * np.abs(ret)))
    shock_mask = vol_path > 2.5 * vol_path.min()
    v[shock_mask] *= 3.0
    idx = start + pd.to_timedelta(np.arange(n_bars), unit="min")
    return pd.DataFrame({
        "open_time": idx.view("int64") // 1_000_000,   # epoch ms
        "open": o, "high": h, "low": l, "close": c, "volume": v,
    })


def generate_archive(out_dir, days: int = 90, seed: int = 7,
                     symbols: tuple[str, ...] | None = None,
                     start: str = "2025-06-01") -> list[str]:
    """Write <symbol>_1m.parquet for every symbol under out_dir."""
    from pathlib import Path
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    symbols = list(symbols or C.SYMBOLS)
    n_bars = int(days * MINUTES_PER_DAY)
    start = pd.Timestamp(start, tz="UTC")
    btc_name = C.BTC_SYMBOL if C.BTC_SYMBOL in symbols else symbols[0]
    btc_ret, vol_path = _market_log_returns(n_bars, seed=seed)
    btc = synth_symbol_ohlcv(n_bars, seed=seed, start=start,
                             market_ret=btc_ret, vol_path=vol_path,
                             mkt_weight=1.0)
    written = []
    for k, s in enumerate(symbols):
        if s == btc_name:
            df = btc
        else:
            df = synth_symbol_ohlcv(
                n_bars, seed=seed + 100 + k, start=start,
                market_ret=btc_ret, vol_path=vol_path, mkt_weight=0.65)
        path = out_dir / f"{s}_1m.parquet"
        df.to_parquet(path, index=False)
        written.append(s)
    return written
