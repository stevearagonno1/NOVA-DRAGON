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
    """
    btc = matrices[C.BTC_SYMBOL]
    if btc is None:
        return []
    recs: list[dict] = []
    idx = btc.index
    btc_ret = _returns(btc["close"])

    # precompute needed per-alt aligned arrays on BTC index
    alts = {s: df for s, df in matrices.items()
            if s != C.BTC_SYMBOL and s not in C.BTC_EXCLUDE}
    # gather correlation series
    corr = {}
    for s, df in alts.items():
        alt = df["close"].reindex(idx, method="ffill")
        alt_ret = alt.pct_change()
        corr[s] = _rolling_corr(btc_ret, alt_ret, C.BTC_CORR_WINDOW_BARS)

    # which alts pass correlation most of the time in recent window
    active = {}
    for s, cs in corr.items():
        recent = cs.dropna().tail(60 * 24 * 3)
        if len(recent) >= C.BTC_MIN_CORR_SAMPLES and recent.mean() >= C.BTC_CORR_MIN:
            active[s] = True

    # build per-alt data reindexed on BTC timeline
    altd = {}
    for s in active:
        df = alts[s]
        altd[s] = {
            "close": df["close"].reindex(idx, method="ffill"),
            "mss": df["mss"].reindex(idx, method="ffill").fillna(0).astype(int),
            "atr": (df["atr14"] / df["close"]).reindex(idx, method="ffill"),
        }

    btc_close = btc["close"].to_numpy(float)
    n = len(idx)

    lookback = 60 * 24 * 5          # 5-day move window for BTC confirmation
    stabil_bars = 60 * 6            # ~6h range check for "stabilized"
    chase_cap = 0.05                # alt must not already be >5% ahead of move

    # open positions per alt
    open_pos = {}                   # symbol -> (entry_px, entry_bar, atr, horizon)

    for i in range(n):
        if i < lookback + C.BTC_MIN_CORR_SAMPLES:
            continue
        # ---- BTC confirmation + stabilisation ----
        if np.isfinite(btc_close[i]) and i >= lookback:
            base = btc_close[i - lookback]
            move = (btc_close[i] - base) / base
        else:
            move = 0.0
        hi = btc_close[max(0, i - stabil_bars):i + 1].max()
        lo = btc_close[max(0, i - stabil_bars):i + 1].min()
        stable = (hi - lo) / max(lo, 1e-9) < 0.01     # <1% over last 6h

        confirmed_up = move >= C.BTC_MOVE_THRESH_PCT and stable

        # ---- manage open BTC positions (time-based horizon exits) ----
        for s in list(open_pos):
            ep, ebar, atr, horizon = open_pos[s]
            if i - ebar >= horizon:
                # horizon reached -> exit at current alt price
                exit_px = _alt_now(altd[s]["close"], i)
                rec = _make_rec(s, ep, exit_px, "أفق-BTC", ebar, i)
                if rec:
                    recs.append(rec)
                del open_pos[s]

        # ---- open new positions on confirmation ----
        if not confirmed_up:
            continue
        # compute how far BTC rose vs each alt's move since same base to find laggards
        for s, d in altd.items():
            if s in open_pos:
                continue
            c_alt = d["close"].to_numpy(float)
            if not np.isfinite(c_alt[i]):
                continue
            base_alt = c_alt[i - lookback] if (i - lookback) >= 0 and np.isfinite(c_alt[i - lookback]) else c_alt[i]
            if base_alt <= 0:
                continue
            alt_move = (c_alt[i] - base_alt) / base_alt
            if alt_move > move + chase_cap:
                continue               # already ran too far (not lagging)
            # structure confirmation on the alt itself (recent MSS long)
            if C.BTC_STRUCTURE_CONFIRM:
                mss_ok = bool((d["mss"].iloc[max(0, i - 3):i + 1] == 1).any())
                if not mss_ok:
                    continue
            atr = d["atr"].iloc[i]
            horizon = C.BTC_HORIZON_BY_COIN.get(s, C.BTC_EXIT_HORIZON_MED)
            open_pos[s] = (float(c_alt[i]), i, atr if np.isfinite(atr) else 0.02, horizon)
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
