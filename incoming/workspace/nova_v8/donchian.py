"""Donchian long-only sleeve — classic Turtle-style Donchian breakout as an
independent research sleeve and a public null-hypothesis mirror (breakouts vs
the NOVA regime/trigger logic).

Deliberately isolated (baseline untouched):
  * disabled by default; selected explicitly (--strategies donchian|all)
  * core signals, the next-open execution model, and the cost model are NOT
    modified — this sleeve reuses the same execution/cost primitives
  * long-only, one unit at a time per (symbol, system), equal research
    notional per unit (DONCHIAN_CAPITAL_USD), no pyramiding

Mechanics (causal, no lookahead):
  * channels computed on the regime TF from COMPLETED higher bars only
    (resample -> rolling max/min -> shift(1) -> ffill onto the 1m timeline;
    the currently-forming higher bar is never part of the channel)
  * entry: first 1m closed bar whose close is beyond the N-bar channel HIGH,
    executed at the NEXT bar's open (market, effective execution cost)
  * exit:  first 1m closed bar whose close is below the M-bar channel LOW,
    executed at the NEXT bar's open (gap-aware market fill, effective cost)
  * no new entries while the state reads Shock (design rule: Shock = no
    trading); an open unit still exits
  * an open unit at the end of data closes at the last close

Temporary assumptions (to be revisited in the one-variable phase): the channel
timeframe (regime TF) and the two lookback systems (20/10 and 55/20, the
classic Turtle daily numbers rescaled to the decision frame).
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


def _channel_1m(df: pd.DataFrame, lookback: int, which: str) -> np.ndarray:
    """Highest-high (which='high') / lowest-low (which='low') of the last
    ``lookback`` COMPLETED regime-TF bars, causally mapped onto the 1m
    timeline (no lookahead). NaN until the window is warm."""
    rule = {"5m": "5min", "15m": "15min"}.get(C.REGIME_TF, C.REGIME_TF)
    r = ind.resample_higher(df, rule)
    ch = (r["high"].rolling(lookback).max() if which == "high"
          else r["low"].rolling(lookback).min())
    ch = ch.shift(1)                       # only completed bars
    out = ch.reindex(df.index, method="ffill")
    return out.to_numpy(dtype=float)


def replay_donchian(mat) -> list[dict]:
    """One long-only Donchian replay per system: each completed entry/exit
    cycle is one research record."""
    arr = mat.arr
    o, c = arr["open"], arr["close"]
    vr = arr.get("vr")
    idx = mat.df.index
    n = mat.n
    regA = mat.regime.to_numpy(dtype=object)

    def _slip(i: int, regime: str) -> float:
        ref = i - 1 if i > 0 else i
        value = None
        if vr is not None and 0 <= ref < n and np.isfinite(float(vr[ref])):
            value = float(vr[ref])
        return market_cost_pct(value, regime)

    def _cycle(trig_name: str, entry_i: int, entry_px: float, entry_ref: float,
               entry_cost: float, regime: str, exit_bar: int, reason: str,
               exit_ref: float, exit_slip: float) -> None:
        pos = Position(symbol=mat.symbol, side=1, entry=entry_px,
                       entry_px=entry_px, atr_pct=0.0, trigger=trig_name,
                       regime=regime, notional=C.DONCHIAN_CAPITAL_USD,
                       entry_bar=entry_i, entry_ref_px=entry_ref,
                       entry_cost_pct=entry_cost)
        net = settle_directional(pos, exit_ref, exit_slip)
        recs.append({
            "category": C.CAT_DONCHIAN, "kind": "donchian",
            "strategy": "donchian", "symbol": mat.symbol,
            "regime": regime, "trigger": trig_name, "side": 1,
            "entry_bar": entry_i, "exit_bar": exit_bar,
            "entry_time": pd.Timestamp(idx[entry_i]).isoformat(),
            "exit_time": pd.Timestamp(idx[exit_bar]).isoformat(),
            "bars_held": exit_bar - entry_i,
            "net_frac": net, "pnl_usd": net * C.DONCHIAN_CAPITAL_USD,
            "notional_usd": C.DONCHIAN_CAPITAL_USD,
            "reason": reason, "cycles": 0,
            "success": bool(net > 0),
            "risk_accepted": True, "risk_reason": "",
            "risk_would_block": False,
            "entry_px": entry_px, "entry_ref_px": entry_ref,
            "entry_cost_pct": entry_cost, "exit_px": exit_ref,
            "mult": 1, "experiment": C.EXPERIMENT_NAME, "series": 0,
            "snapshot": json.dumps(
                {"system": trig_name, "channel_tf": C.REGIME_TF,
                 "capital": C.DONCHIAN_CAPITAL_USD}, ensure_ascii=False),
        })

    recs: list[dict] = []
    for (e_lb, x_lb) in C.DONCHIAN_SYSTEMS:
        hh = _channel_1m(mat.df, e_lb, "high")
        ll = _channel_1m(mat.df, x_lb, "low")
        trig_name = f"Donchian-{e_lb}/{x_lb}"
        pos: dict | None = None            # open unit state
        for i in range(1, n):
            if pos is None:
                # entry decision on the closed bar i-1 (channel as of i-1)
                # NOVA-DON-FILTER: long entries only outside bear/shock states
                # (approved fix: -18.4k$ bleed in 2022 bear, -11.4k$ in 2025-26
                # chop-crash; profitable run only in the 2024 uptrend).
                _allow = getattr(C, "DONCHIAN_TREND_FILTER", True) or \
                    os.getenv("NOVA_DON_FILTER", "1") == "1"
                if (_allow
                        and np.isfinite(hh[i - 1]) and float(c[i - 1]) > hh[i - 1]
                        and regA[i - 1] != C.REGIME_SHOCK
                        and regA[i - 1] != C.REGIME_BEAR):
                    regime = str(regA[i - 1]) if regA[i - 1] else C.REGIME_BULL
                    ref = float(o[i])
                    if math.isfinite(ref) and ref > 0:
                        cost = _slip(i, regime)
                        px = market_fill(ref, 1, cost)
                        if px > 0:
                            pos = {"bar": i, "px": px, "ref": ref,
                                   "cost": cost, "regime": regime}
            else:
                # exit decision on the closed bar i-1
                if np.isfinite(ll[i - 1]) and float(c[i - 1]) < ll[i - 1]:
                    p, pos = pos, None
                    _cycle(trig_name, p["bar"], p["px"], p["ref"], p["cost"],
                           p["regime"], i, "كسر-سفلي", float(o[i]),
                           _slip(i, str(regA[i - 1])))
        # close any open unit at the last close
        if pos is not None:
            p, pos = pos, None
            _cycle(trig_name, p["bar"], p["px"], p["ref"], p["cost"],
                   p["regime"], n - 1, "نهاية-البيانات", float(c[n - 1]),
                   _slip(n - 1, str(regA[n - 2])))
    return recs
