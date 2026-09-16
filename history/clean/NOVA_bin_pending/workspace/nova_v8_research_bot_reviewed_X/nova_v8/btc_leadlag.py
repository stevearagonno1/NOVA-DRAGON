"""Module — BTC lead-lag for lagging altcoins (separate research unit).

Design (from the correlation report + final doc):
  * Only the UP-side lag is exploited (down-moves transfer ~instantly).
  * Trade altcoins with high rolling correlation to BTC that have NOT yet
    caught up, once BTC has confirmed + stabilised its up-move.
  * Entry requires a structure (MSS) bullish break on the altcoin itself.
  * Exit horizon varies per coin (fast BNB/SOL vs slow XLM/VET/FIL).
This module is causal and evaluated on the historical data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .execution import settle_directional
from .execution import Position


def _returns(s: pd.Series) -> pd.Series:
    return s.pct_change()


def _rolling_corr(a: pd.Series, b: pd.Series, window: int) -> pd.Series:
    return a.rolling(window).corr(b)


def run_btc_pass(matrices: dict) -> list[dict]:
    """matrices: {symbol: df} trade-TF OHLCV+features aligned on DatetimeIndex.
    Returns a list of trade records for the BTC unit (category BTC).

    Causality & performance:
      * Rolling BTC range (for the 'stabilised' test) is precomputed once with
        pandas rolling max/min instead of re-slicing per bar (O(n) not O(n*w)).
      * All per-alt lookups on the BTC timeline are O(1) array reads.
      * Positions are long-only and are exited by either a protective ATR stop
        or the coin's exit horizon, whichever comes first.
    """
    btc = matrices[C.BTC_SYMBOL]
    if btc is None:
        return []
    recs: list[dict] = []
    idx = btc.index
    btc_ret = _returns(btc["close"])

    alts = {s: df for s, df in matrices.items()
            if s != C.BTC_SYMBOL and s not in C.BTC_EXCLUDE}
    if not alts:
        return []

    # ---- correlation (causal rolling) -> active laggards ----
    active = {}
    for s, df in alts.items():
        alt = df["close"].reindex(idx, method="ffill")
        corr = _rolling_corr(btc_ret, alt.pct_change(), C.BTC_CORR_WINDOW_BARS)
        recent = corr.dropna().tail(60 * 24 * 3)
        if len(recent) >= C.BTC_MIN_CORR_SAMPLES and recent.mean() >= C.BTC_CORR_MIN:
            active[s] = True

    # ---- BTC reference arrays on its own timeline ----
    btc_close = btc["close"].to_numpy(float)
    n = len(idx)
    lookback = 60 * 24 * 5           # 5-day move window for BTC confirmation
    stabil_bars = 60 * 6             # ~6h range check for "stabilised"
    chase_cap = 0.05                 # alt must not already be >5% ahead

    btc_s = btc["close"]
    roll_hi = btc_s.rolling(stabil_bars + 1, min_periods=1).max().to_numpy(float)
    roll_lo = btc_s.rolling(stabil_bars + 1, min_periods=1).min().to_numpy(float)

    # ---- per-alt O(1) arrays reindexed on the BTC timeline ----
    altd = {}
    for s in active:
        df = alts[s]
        close_s = df["close"].reindex(idx, method="ffill")
        mss_s = (df["mss"].reindex(idx, method="ffill").fillna(0).astype(int))
        # boolean "bullish MSS fired within last 4 bars (i-3..i)" — rolling causal
        mss_recent = (mss_s.rolling(4, min_periods=1).max() >= 1).to_numpy(bool)
        atr_f = (df["atr14"] / df["close"].replace(0.0, float("nan"))).reindex(idx, method="ffill")
        altd[s] = {
            "close": close_s.to_numpy(float),
            "mss_ok": mss_recent,
            "atr": atr_f.to_numpy(float),
        }

    # ---- replay (per-bar O(1)) ----
    open_pos = {}                    # symbol -> [entry_px, entry_bar, atr, horizon]
    for i in range(n):
        if i < lookback + C.BTC_MIN_CORR_SAMPLES:
            continue

        # ---- BTC confirmation + stabilisation (precomputed rolling) ----
        bc = btc_close[i]
        if np.isfinite(bc):
            base = btc_close[i - lookback]
            move = (bc - base) / base if np.isfinite(base) and base > 0 else 0.0
        else:
            move = 0.0
        hi, lo = roll_hi[i], roll_lo[i]
        stable = (hi - lo) / max(lo, 1e-9) < 0.01 if np.isfinite(hi) and np.isfinite(lo) else False
        confirmed_up = move >= C.BTC_MOVE_THRESH_PCT and stable

        # ---- manage open positions: stop first, then horizon ----
        for s in list(open_pos):
            ep, ebar, atr, horizon = open_pos[s]
            cur = _alt_now(altd[s]["close"], i)
            if cur <= 0:
                continue
            stopf = (C.BTC_STOP_ATR_MULT * atr) if np.isfinite(atr) else C.BTC_STOP_FALLBACK_PCT
            if (ep - cur) / ep >= stopf:
                rec = _make_rec(s, ep, cur, "وقف-BTC", ebar, i)
                if rec:
                    recs.append(rec)
                del open_pos[s]
                continue
            if i - ebar >= horizon:
                rec = _make_rec(s, ep, cur, "أفق-BTC", ebar, i)
                if rec:
                    recs.append(rec)
                del open_pos[s]

        if not confirmed_up:
            continue
        # ---- open new laggard positions ----
        for s, d in altd.items():
            if s in open_pos:
                continue
            c_i = d["close"][i]
            if not np.isfinite(c_i) or c_i <= 0:
                continue
            b_i = d["close"][i - lookback]
            if not (np.isfinite(b_i) and b_i > 0):
                continue
            alt_move = (c_i - b_i) / b_i
            if alt_move > move + chase_cap:
                continue               # already ran too far (not lagging)
            if C.BTC_STRUCTURE_CONFIRM and not bool(d["mss_ok"][i]):
                continue
            atr = d["atr"][i]
            atr = atr if np.isfinite(atr) else 0.02
            horizon = C.BTC_HORIZON_BY_COIN.get(s, C.BTC_EXIT_HORIZON_MED)
            open_pos[s] = [float(c_i), i, float(atr), horizon]
    return recs


def _alt_now(cser: pd.Series, i: int) -> float:
    v = cser.iloc[i]
    return float(v) if np.isfinite(v) else 0.0


def _make_rec(symbol, entry_px, exit_px, reason, ebar, xbar):
    if entry_px <= 0 or exit_px <= 0:
        return None
    pos = Position(symbol=symbol, side=1, entry=entry_px, entry_px=entry_px,
                   atr_pct=0.02, trigger="BTC-LeadLag", regime=C.REGIME_BULL)
    net = settle_directional(pos, exit_px)
    return {
        "symbol": symbol, "category": C.CAT_BTC, "side": 1,
        "entry_px": entry_px, "exit_px": exit_px, "net": net,
        "reason": reason, "entry_bar": ebar, "exit_bar": xbar,
        "trigger": "BTC-LeadLag",
    }
