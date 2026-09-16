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


def run_btc_pass(matrices: dict, mss_truth: dict | None = None) -> list[dict]:
    """matrices: {symbol: df} aligned 1m OHLCV+features (close/atr14/mss).
    Returns a list of trade records for the BTC unit (category BTC).

    Chapter-9c fidelity:
      * only the UP-side lag is traded (long-only);
      * active laggards are chosen by a rolling dynamic correlation window;
      * entry requires BOTH a strong+stabilised BTC up-move AND, optionally, an
        MSS bullish break on BTC itself (BTC_STRUCTURE_ON_BTC);
      * a real entry needs an MSS bullish break on the altcoin, gated by the
        unified structure Oracle when that data is supplied (mss_truth);
      * exits are long-only protective ATR stop OR a trailing profit stop OR
        the coin-specific horizon (no short time-stop), whichever comes first.
    Causality/performance: per-bar work is O(1); rolling windows are precomputed.
    """
    btc = matrices[C.BTC_SYMBOL]
    if btc is None:
        return []
    mss_truth = mss_truth or {}
    recs: list[dict] = []
    idx = btc.index
    btc_ret = _returns(btc["close"])

    alts = {s: df for s, df in matrices.items()
            if s != C.BTC_SYMBOL and s not in C.BTC_EXCLUDE}
    if not alts:
        return []

    # ---- active laggards by rolling dynamic correlation ----
    active = {}
    for s, df in alts.items():
        alt = df["close"].reindex(idx, method="ffill")
        corr = _rolling_corr(btc_ret, alt.pct_change(), C.BTC_CORR_WINDOW_BARS)
        recent = corr.dropna().tail(60 * 24 * 3)
        if len(recent) >= C.BTC_MIN_CORR_SAMPLES and recent.mean() >= C.BTC_CORR_MIN:
            active[s] = True

    btc_close = btc["close"].to_numpy(float)
    n = len(idx)
    lookback = 60 * 24 * 5            # 5-day move window for confirmation
    stabil_bars = 60 * 6              # ~6h range check for "stabilised"
    chase_cap = 0.05

    # ---- BTC reference arrays (precomputed rolling) ----
    btc_s = btc["close"]
    roll_hi = btc_s.rolling(stabil_bars + 1, min_periods=1).max().to_numpy(float)
    roll_lo = btc_s.rolling(stabil_bars + 1, min_periods=1).min().to_numpy(float)
    # bullish MSS on BTC within recent window (rolling max >= 1)
    btc_mss_s = btc["mss"] if "mss" in btc.columns else None
    btc_mss_recent = None
    if btc_mss_s is not None:
        btc_mss_recent = (btc_mss_s.fillna(0).rolling(6, min_periods=1).max() >= 1
                          ).to_numpy(bool)

    # ---- per-alt O(1) arrays on the BTC timeline ----
    altd = {}
    for s in active:
        df = alts[s]
        close_s = df["close"].reindex(idx, method="ffill")
        mss_s = (df["mss"].reindex(idx, method="ffill").fillna(0).astype(int))
        mss_ok = (mss_s.rolling(4, min_periods=1).max() >= 1).to_numpy(bool)
        atr_f = (df["atr14"] / df["close"].replace(0.0, float("nan"))
                 ).reindex(idx, method="ffill")
        hi_s = df["high"].reindex(idx, method="ffill")
        lo_s = df["low"].reindex(idx, method="ffill")
        altd[s] = {
            "close": close_s.to_numpy(float),
            "high": hi_s.to_numpy(float),
            "low": lo_s.to_numpy(float),
            "mss_ok": mss_ok,
            "atr": atr_f.to_numpy(float),
        }

    # open position state: [entry_px, entry_bar, atr, horizon, active, stop, wm]
    open_pos = {}
    for i in range(n):
        if i < lookback + C.BTC_MIN_CORR_SAMPLES:
            continue

        # ---- BTC confirmation (strong move + stabilised [+ MSS on BTC]) ----
        bc = btc_close[i]
        if np.isfinite(bc):
            base = btc_close[i - lookback]
            move = (bc - base) / base if np.isfinite(base) and base > 0 else 0.0
        else:
            move = 0.0
        hi, lo = roll_hi[i], roll_lo[i]
        stable = ((hi - lo) / max(lo, 1e-9) < 0.01
                  if np.isfinite(hi) and np.isfinite(lo) else False)
        confirmed_up = move >= C.BTC_MOVE_THRESH_PCT and stable
        if confirmed_up and C.BTC_STRUCTURE_ON_BTC and btc_mss_recent is not None:
            confirmed_up = bool(btc_mss_recent[i])

        # ---- manage open positions: stop / trailing / horizon ----
        for s in list(open_pos):
            ep, ebar, atr, horizon, t_active, t_stop, wm = open_pos[s]
            hb, lb, cb = altd[s]["high"][i], altd[s]["low"][i], altd[s]["close"][i]
            ob = cb                                # approximation for gap check
            if not np.isfinite(hb):
                continue
            stopf = (C.BTC_STOP_ATR_MULT * atr) if np.isfinite(atr) else C.BTC_STOP_FALLBACK_PCT
            prot_level = ep * (1.0 - stopf)
            triggered = []
            if np.isfinite(lb) and lb <= prot_level:
                triggered.append((prot_level, "وقف-BTC"))
            if t_active and np.isfinite(lb) and lb <= t_stop:
                triggered.append((t_stop, "تتبع-BTC"))
            reason = None
            fill = None
            if triggered:
                # conservative: use the highest triggered line (realistic stop)
                fill, reason = max(triggered)
                if ob < fill:
                    fill = ob
            elif (i - ebar) >= horizon:
                fill, reason = cb, "أفق-BTC"
            if reason is not None and np.isfinite(fill) and fill > 0:
                rec = _make_rec(s, ep, fill, reason, ebar, i)
                if rec:
                    recs.append(rec)
                del open_pos[s]
                continue
            # ---- advance trailing (long) ----
            if np.isfinite(hb):
                gain_atr = ((hb - ep) / ep / atr) if np.isfinite(atr) and atr > 0 else 0.0
                wm = max(wm, hb)
                if not t_active and gain_atr >= C.BTC_TRAIL_ACT_ATR:
                    t_active, t_stop = 1, ep
                if t_active:
                    cand = wm * (1.0 - C.BTC_TRAIL_DIST_ATR * atr)
                    t_stop = max(t_stop, cand)
                open_pos[s] = [ep, ebar, atr, horizon, t_active, t_stop, wm]

        if not confirmed_up:
            continue
        # ---- open new laggard long positions ----
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
                continue
            if C.BTC_STRUCTURE_CONFIRM and not bool(d["mss_ok"][i]):
                continue
            # unified-Oracle gate for structure-based entries (default allow)
            truth = mss_truth.get(s, {}).get(C.REGIME_BULL, True)
            if not truth:
                continue
            atr = d["atr"][i]
            atr = atr if np.isfinite(atr) else 0.02
            horizon = C.BTC_HORIZON_BY_COIN.get(s, C.BTC_EXIT_HORIZON_MED)
            open_pos[s] = [float(c_i), i, float(atr), horizon, 0, 0.0, float(c_i)]
    return recs


def _alt_now(cser, i):
    return float(cser[i]) if np.isfinite(cser[i]) else 0.0


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
        "trigger": "BTC-LeadLag", "mult": 1, "series": 0,
    }
