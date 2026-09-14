"""Adaptive Trend sleeve — spec 8.2 "الاتجاه + الارتداد إلى القيمة" (trend +
pullback to value) as an independent research sleeve.

The idea (spec 8.2): do not buy an explosive candle just because it is up.
Wait for a proven trend, a cheap pullback, then a confirmed resumption —
Gate / Setup / Trigger / Invalidation, without trying to pick the bottom.

Deliberately isolated (baseline untouched):
  * disabled by default; selected explicitly (--strategies adaptive_trend|all)
  * core signals, the next-open execution model, and the cost model are NOT
    modified — the same execution/cost primitives are reused
  * one position at a time per symbol (long or short as research), equal
    research notional, no pyramiding; no new entries in Shock

Mechanics (causal, no lookahead — decisions on closed 1m bars, execution at
the next open; higher-TF reads use completed bars only, shift(1)+ffill):
  * GATE (4h): EMA50 above/below EMA200 + EMA50 slope in direction +
    higher-high/higher-low (lower mirror) on completed 4h bars
  * SETUP: within the pullback window the price traded into the 4h
    EMA20-EMA50 zone, and the current close is still on the right side of
    EMA20 (a pullback, not a break of the trend)
  * TRIGGER (closed bar): close beyond the local-high (low) of the last
    ADAPTIVE_TREND_TRIGGER_BARS bars, bullish (bearish) body, close in the
    upper (lower) half of the bar (no long wick against the move), volume at
    or above its 20-bar average (resumption expansion)
  * ABSTAIN: close extended beyond ADAPTIVE_TREND_MAX_EXT_ATR x ATR from the
    4h EMA50, or the 4h range is dead narrow (MIN_RANGE_PCT)
  * INVALIDATION/EXIT: stop under (above) the pullback structure minus
    (plus) the ATR margin; afterwards an ATR trail ratchets behind the
    running peak. A stop/trail touch on a bar's extreme exits at the NEXT
    bar's open (market, effective cost, gap-aware).

Temporary assumptions (uncalibrated flags): the 4h trend frame, the window
lengths, and the ATR margins — the one-variable phase on real data decides.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np
import pandas as pd

from . import config as C
from . import indicators as ind
from .execution import (Position, settle_directional, market_cost_pct,
                        market_fill)


def _map_to_1m(s: pd.Series, idx: pd.DatetimeIndex) -> np.ndarray:
    return s.reindex(idx, method="ffill").to_numpy(dtype=float)


def _trend_frame_1m(df: pd.DataFrame) -> dict:
    """Causal 4h trend readings mapped onto the 1m timeline (completed 4h
    bars only — a 4h bar's EMA/structure is known only after it closes)."""
    rule = {"5m": "5min", "15m": "15min"}.get(C.ADAPTIVE_TREND_TF,
                                               C.ADAPTIVE_TREND_TF)
    r = ind.resample_higher(df, rule)
    e50 = ind.ema(r["close"], 50)
    e200 = ind.ema(r["close"], 200)
    e20 = ind.ema(r["close"], 20)
    atr_tf = ind.wilder_atr(r, 14)
    # ema() is recursive and "valid" from bar 0; an EMA200 trend read is only
    # trustworthy after ~200 higher bars — mask the warm-up (no lookahead,
    # just a conservative no-trade warm-up on the trend frame)
    for s in (e50, e200, e20):
        s.iloc[:200] = np.nan
    atr_tf.iloc[:200] = np.nan
    idx = df.index
    return {
        "ema50": _map_to_1m(e50.shift(1), idx),
        "ema200": _map_to_1m(e200.shift(1), idx),
        "ema20": _map_to_1m(e20.shift(1), idx),
        "ema50_prev": _map_to_1m(e50.shift(2), idx),   # slope on 4h steps
        "hi_prev": _map_to_1m(r["high"].shift(1), idx),
        "hi_prev2": _map_to_1m(r["high"].shift(2), idx),
        "lo_prev": _map_to_1m(r["low"].shift(1), idx),
        "lo_prev2": _map_to_1m(r["low"].shift(2), idx),
        # trend-frame ATR: the right yardstick for "extended from the average"
        "atr_tf": _map_to_1m(atr_tf.shift(1), idx),
    }


def replay_adaptive_trend(mat) -> list[dict]:
    """One Adaptive Trend replay per symbol: each completed entry/exit cycle
    is one research record (long and short are research sides)."""
    arr = mat.arr
    o, h, l, c, v = (arr["open"], arr["high"], arr["low"], arr["close"],
                     arr["volume"])
    vol_sma = arr.get("vol_sma20")
    atr = arr.get("atr14")
    vr = arr.get("vr")
    idx = mat.df.index
    n = mat.n
    regA = mat.regime.to_numpy(dtype=object)
    tf = _trend_frame_1m(mat.df)

    pb = C.ADAPTIVE_TREND_PULLBACK_BARS
    tg = C.ADAPTIVE_TREND_TRIGGER_BARS

    def _slip(i: int, regime: str) -> float:
        ref = i - 1 if i > 0 else i
        value = None
        if vr is not None and 0 <= ref < n and np.isfinite(float(vr[ref])):
            value = float(vr[ref])
        return market_cost_pct(value, regime)

    recs: list[dict] = []

    def _cycle(side: int, entry_i: int, entry_px: float, entry_ref: float,
               entry_cost: float, regime: str, exit_bar: int, reason: str,
               exit_ref: float, exit_slip: float) -> None:
        pos = Position(symbol=mat.symbol, side=side, entry=entry_px,
                       entry_px=entry_px, atr_pct=0.0,
                       trigger="AdaptiveTrend-4h", regime=regime,
                       notional=C.ADAPTIVE_TREND_CAPITAL_USD,
                       entry_bar=entry_i, entry_ref_px=entry_ref,
                       entry_cost_pct=entry_cost)
        net = settle_directional(pos, exit_ref, exit_slip)
        recs.append({
            "category": C.CAT_ADAPTIVE_TREND, "kind": "adaptive_trend",
            "strategy": "adaptive_trend", "symbol": mat.symbol,
            "regime": regime, "trigger": "AdaptiveTrend-4h", "side": side,
            "entry_bar": entry_i, "exit_bar": exit_bar,
            "entry_time": pd.Timestamp(idx[entry_i]).isoformat(),
            "exit_time": pd.Timestamp(idx[exit_bar]).isoformat(),
            "bars_held": exit_bar - entry_i,
            "net_frac": net, "pnl_usd": net * C.ADAPTIVE_TREND_CAPITAL_USD,
            "notional_usd": C.ADAPTIVE_TREND_CAPITAL_USD,
            "reason": reason, "cycles": 0,
            "success": bool(net > 0),
            "risk_accepted": True, "risk_reason": "",
            "risk_would_block": False,
            "entry_px": entry_px, "entry_ref_px": entry_ref,
            "entry_cost_pct": entry_cost, "exit_px": exit_ref,
            "mult": 1, "experiment": C.EXPERIMENT_NAME, "series": 0,
            "snapshot": json.dumps(
                {"tf": C.ADAPTIVE_TREND_TF, "capital":
                    C.ADAPTIVE_TREND_CAPITAL_USD}, ensure_ascii=False),
        })

    pos: dict | None = None
    for i in range(1, n):
        j = i - 1                                   # decision bar (closed)
        if pos is None:
            e50, e200, e20 = tf["ema50"][j], tf["ema200"][j], tf["ema20"][j]
            a = atr[j]
            if not (np.isfinite(e50) and np.isfinite(e200) and np.isfinite(e20)
                    and np.isfinite(a) and a > 0):
                continue
            if regA[j] == C.REGIME_SHOCK:
                continue
            side = 0
            # ---- GATE (completed 4h bars only) ----
            slope_up = np.isfinite(tf["ema50_prev"][j]) and \
                e50 >= tf["ema50_prev"][j]
            slope_dn = np.isfinite(tf["ema50_prev"][j]) and \
                e50 <= tf["ema50_prev"][j]
            hh = np.isfinite(tf["hi_prev2"][j]) and \
                tf["hi_prev"][j] > tf["hi_prev2"][j]
            hl = np.isfinite(tf["lo_prev2"][j]) and \
                tf["lo_prev"][j] > tf["lo_prev2"][j]
            lh = np.isfinite(tf["hi_prev2"][j]) and \
                tf["hi_prev"][j] < tf["hi_prev2"][j]
            ll = np.isfinite(tf["lo_prev2"][j]) and \
                tf["lo_prev"][j] < tf["lo_prev2"][j]
            if e50 > e200 and slope_up and hh and hl:
                side = 1
            elif e50 < e200 and slope_dn and lh and ll:
                side = -1
            if side == -1 and not getattr(C, "ADAPTIVE_TREND_ALLOW_SHORT", False):
                side = 0          # Spot long-only constraint (config default)
            if side == 0:
                continue
            # ---- ABSTAIN: over-extended (trend-frame ATR yardstick) ----
            a_tf = tf["atr_tf"][j]
            if np.isfinite(a_tf) and (c[j] - e50) * side \
                    > C.ADAPTIVE_TREND_MAX_EXT_ATR * a_tf:
                continue
            s0 = max(0, j - pb)
            seg_h = float(np.nanmax(h[s0:j + 1]))
            seg_l = float(np.nanmin(l[s0:j + 1]))
            if seg_h > 0 and (seg_h - seg_l) / seg_h < C.ADAPTIVE_TREND_MIN_RANGE_PCT:
                continue
            # ---- SETUP: pulled into the EMA20-EMA50 zone, still intact ----
            band_top = max(e20, e50)
            band_bot = min(e20, e50)
            zone_lo = band_bot - 0.5 * a
            zone_hi = band_top + 0.5 * a
            lo_win = float(np.nanmin(l[max(0, j - pb):j + 1]))
            if not (zone_lo <= lo_win <= zone_hi and c[j] * side > e20 * side):
                continue
            # ---- TRIGGER: confirmed resumption bar (closed) ----
            # AT-ENTRY-V3 hypotheses (each individually env-switchable):
            _v3a = os.getenv("NOVA_AT_V3A", "0") == "1"   # (a) enter near lower part of local high
            _v3b = os.getenv("NOVA_AT_V3B", "0") == "1"   # (b) skip explosive trigger bars
            _v3c = os.getenv("NOVA_AT_V3C", "0") == "1"   # (c) deeper structure: higher low second confirmation
            k = max(0, j - tg)
            if side == 1:
                local_hi = float(np.nanmax(c[k:j]))      # prior local-high closes
                ok = (c[j] > local_hi and c[j] > o[j]
                      and (c[j] - l[j]) >= 0.5 * (h[j] - l[j])
                      and (vol_sma is None or not np.isfinite(vol_sma[j])
                           or v[j] >= vol_sma[j]))
                if ok and _v3a:
                    # (a) close must sit in lower 40% between EMA20 and local high
                    _top = float(np.nanmax(c[k:j]))
                    if (c[j] - e20) > 0.6 * max(_top - e20, 1e-9):
                        ok = False
                if ok and _v3b:
                    # (b) skip runaway trigger bars (body <= 1.5×ATR-4h)
                    _a4 = tf["atr_tf"][j]
                    if np.isfinite(_a4) and _a4 > 0 and abs(c[j] - o[j]) > 1.5 * _a4:
                        ok = False
                if ok and _v3c:
                    # (c) require a second higher low within the trigger window
                    _lows = l[max(0, j - tg):j + 1]
                    _ll = _lows[-3:]
                    ok = bool(np.all(np.diff(_ll) > 0)) if len(_ll) == 3 else False
            else:
                local_lo = float(np.nanmin(c[k:j]))
                ok = (c[j] < local_lo and c[j] < o[j]
                      and (h[j] - c[j]) >= 0.5 * (h[j] - l[j])
                      and (vol_sma is None or not np.isfinite(vol_sma[j])
                           or v[j] >= vol_sma[j]))
            if not ok:
                continue
            regime = str(regA[j])
            ref = float(o[i])
            if not (math.isfinite(ref) and ref > 0):
                continue
            cost = _slip(i, regime)
            px = market_fill(ref, side, cost)
            if px <= 0:
                continue
            # ---- stop: under the pullback structure + ATR margin ----
            # AT-STOP-WIDE: wider structural margin (0.5 ATR-5m is hair-thin)
            _stop_mult = float(os.getenv("NOVA_AT_STOP", str(C.ADAPTIVE_TREND_STOP_ATR)))
            if side == 1:
                stop = float(np.nanmin(l[max(0, j - pb):j + 1])) \
                    - _stop_mult * a
            else:
                stop = float(np.nanmax(h[max(0, j - pb):j + 1])) \
                    + _stop_mult * a
            # AT-FRAME-FIX: trail distance must breathe on the 4h yardstick
            # (5×ATR-5m ≈ 0.75% — instant choke; 5×ATR-4h ≈ 6% — intended)
            _a_trail = a
            _a_tf_arr = tf.get("atr_tf")
            if _a_tf_arr is not None and np.isfinite(_a_tf_arr[j]) and _a_tf_arr[j] > 0:
                _a_trail = _a_tf_arr[j]
            pos = {"side": side, "bar": i, "px": px, "ref": ref,
                   "cost": cost, "regime": regime, "stop": stop,
                   "peak": px, "atr_pct": _a_trail / ref}
        else:
            s = pos["side"]
            # trail ratchets behind the running peak (ATR distance)
            if s == 1:
                pos["peak"] = max(pos["peak"], float(h[j]))
                trail = pos["peak"] * (1.0 - C.ADAPTIVE_TREND_TRAIL_ATR *
                                       pos["atr_pct"])
                line = max(pos["stop"], trail)
                touched = float(l[j]) <= line
            else:
                pos["peak"] = min(pos["peak"], float(l[j]))
                trail = pos["peak"] * (1.0 + C.ADAPTIVE_TREND_TRAIL_ATR *
                                       pos["atr_pct"])
                line = min(pos["stop"], trail)
                touched = float(h[j]) >= line
            if touched:
                p = pos
                # line == the raw structure stop iff the stop (not the trail)
                # is the binding constraint
                reason = "وقف" if line == p["stop"] else "تتبع"
                pos = None
                _cycle(p["side"], p["bar"], p["px"], p["ref"], p["cost"],
                       p["regime"], i, reason, float(o[i]),
                       _slip(i, str(regA[j])))
    if pos is not None:
        p = pos
        pos = None
        _cycle(p["side"], p["bar"], p["px"], p["ref"], p["cost"], p["regime"],
               n - 1, "نهاية-البيانات", float(c[n - 1]),
               _slip(n - 1, str(regA[n - 2])))
    return recs
