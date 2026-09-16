"""Long-horizon cycle accumulation/distribution research sleeve.

This is deliberately a causal approximation of "buy the bottom / sell the top":
no module can know the absolute future low or high.  It uses a daily broad-zone
context, 4h structure confirmation, bounded staged entries, staged distribution,
and hard invalidation.  It is independent from the core Directional/Grid/BTC
sleeves and is disabled from the default Baseline.
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd

from . import config as C
from . import indicators as ind
from .execution import Position, market_cost_pct, market_fill, settle_directional


def _resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    out = df.resample(rule, label="left", closed="left").agg({
        "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum",
    }).dropna()
    return out


def _record(symbol, stage, series, entry_i, exit_i, entry_ref, entry_px,
            entry_cost, exit_px, reason, notional, idx, exit_slip=None) -> dict:
    pos = Position(symbol=symbol, side=1, entry=entry_px, entry_px=entry_px,
                   atr_pct=0.02, trigger="CycleBottom", regime=C.REGIME_BULL,
                   notional=notional, entry_bar=entry_i,
                   entry_ref_px=entry_ref, entry_cost_pct=entry_cost,
                   series=series)
    net = settle_directional(pos, exit_px,
                             slip_pct=(C.SLIPPAGE_PCT if exit_slip is None
                                       else exit_slip))
    return {
        "category": C.CAT_LONG_CYCLE, "kind": "long_cycle",
        "strategy": "long_cycle", "symbol": symbol,
        "regime": "دورة-طويلة", "trigger": "CycleBottom",
        "side": 1, "entry_bar": int(entry_i), "exit_bar": int(exit_i),
        "entry_time": pd.Timestamp(idx[entry_i]).isoformat(),
        "exit_time": pd.Timestamp(idx[exit_i]).isoformat(),
        "bars_held": int(exit_i - entry_i),
        "net_frac": net, "pnl_usd": net * notional,
        "notional_usd": notional, "reason": reason, "cycles": 0,
        "success": bool(net > 0), "risk_accepted": True,
        "risk_reason": "", "risk_would_block": False,
        "entry_px": entry_px, "entry_ref_px": entry_ref,
        "entry_cost_pct": entry_cost, "exit_px": exit_px,
        "mult": 1, "experiment": C.EXPERIMENT_NAME,
        "series": int(series),
        "snapshot": json.dumps({"stage": int(stage), "tf": "4h"},
                                ensure_ascii=False),
    }


def run(df1m: pd.DataFrame, symbol: str) -> list[dict]:
    """Run the independent long-cycle sleeve on one symbol's 1m frame."""
    if symbol not in {"BTCUSDT", "BNBUSDT", "SOLUSDT", "LINKUSDT"}:
        return []
    h4 = _resample(df1m, "4h")
    daily = _resample(df1m, "1D")
    if len(h4) < 200 or len(daily) < max(40, C.LONG_CYCLE_DAILY_LOOKBACK // 2):
        return []

    # A daily bar is only known at the next UTC day.  Shift its derived context
    # forward before mapping it to 4h, so the current day cannot leak into a
    # decision made inside that day.
    prior_low = daily["low"].shift(1).rolling(
        C.LONG_CYCLE_DAILY_LOOKBACK,
        min_periods=max(30, C.LONG_CYCLE_DAILY_LOOKBACK // 3),
    ).min()
    prior_high = daily["high"].shift(1).rolling(
        C.LONG_CYCLE_DAILY_LOOKBACK,
        min_periods=max(30, C.LONG_CYCLE_DAILY_LOOKBACK // 3),
    ).max()
    known = pd.DataFrame({"prior_low": prior_low, "prior_high": prior_high},
                         index=daily.index + pd.Timedelta(days=1))
    dctx = known.reindex(h4.index, method="ffill")

    atr = ind.wilder_atr(h4, C.ATR_LEN)
    atr_pct = (atr / h4["close"].replace(0.0, np.nan)).to_numpy(float)
    ema20 = ind.ema(h4["close"], 20)
    prior6_high = h4["high"].shift(1).rolling(C.LONG_CYCLE_CONFIRM_BARS_4H).max()
    prior3_low = h4["low"].shift(1).rolling(3).min()
    close = h4["close"]
    low = h4["low"]
    mss = close > prior6_high
    zone = close <= dctx["prior_low"] * (1.0 + C.LONG_CYCLE_ZONE_BUFFER_PCT)
    zone_seen = zone.shift(1).rolling(C.LONG_CYCLE_CONFIRM_BARS_4H,
                                      min_periods=1).max().astype(bool)
    stabilised = (close > close.shift(1)) & (low >= low.shift(1))
    entry_signal = zone_seen & stabilised & mss & (close > ema20)
    top_zone = close >= dctx["prior_high"] * (1.0 - C.LONG_CYCLE_ZONE_BUFFER_PCT)
    weakness = ((close < prior3_low) | (close < ema20)).fillna(False).astype(bool)
    weakness_event = weakness & ~weakness.shift(1, fill_value=False)

    idx = h4.index
    n = len(h4)
    weights = C.LONG_CYCLE_STAGE_WEIGHTS
    tranches: list[dict] = []
    pending: dict[int, list[tuple]] = {}
    records: list[dict] = []
    series = 0
    top_seen = False
    next_stage = 0

    def cost_at(i: int) -> float:
        ref = i - 1 if i > 0 else i
        v = atr_pct[ref] if 0 <= ref < n and np.isfinite(atr_pct[ref]) else None
        return market_cost_pct(v, C.REGIME_BULL)

    def schedule_buy(stage: int, decision_i: int):
        if stage >= len(weights) or any(a[0] == "buy" for vals in pending.values() for a in vals):
            return
        pending.setdefault(decision_i + 1, []).append(("buy", stage, decision_i))

    def close_tranches(exit_i: int, reason: str, px: float):
        nonlocal tranches, top_seen, next_stage
        for tr in list(tranches):
            records.append(_record(symbol, tr["stage"], series, tr["entry_i"],
                                   exit_i, tr["entry_ref"], tr["entry_px"],
                                   tr["entry_cost"], px, reason,
                                   tr["notional"], idx, cost_at(exit_i)))
        tranches = []
        top_seen = False
        next_stage = 0

    for i in range(1, n):
        o, h, l, c = (float(h4.iloc[i][x]) for x in ("open", "high", "low", "close"))
        # Execute decisions made on the prior closed 4h bar at this bar's open.
        for action, stage, decision_i in pending.pop(i, []):
            if action != "buy" or len(tranches) >= len(weights):
                continue
            if not np.isfinite(o) or o <= 0:
                continue
            ecost = cost_at(i)
            epx = market_fill(o, 1, ecost)
            notional = C.LONG_CYCLE_CAPITAL_USD * float(weights[stage])
            tranches.append({"stage": stage, "entry_i": i, "entry_ref": o,
                             "entry_px": epx, "entry_cost": ecost,
                             "notional": notional, "peak": epx})
            next_stage = max(next_stage, stage + 1)

        if not tranches:
            if bool(entry_signal.iloc[i]):
                schedule_buy(0, i)
            continue

        # Hard invalidation uses the lower of a broad structural failure and a
        # bounded cycle-loss cap.  It is intentionally not a tight scalping stop.
        broad_low = dctx["prior_low"].iloc[i]
        invalid_level = min(
            min(t["entry_px"] for t in tranches) * (1.0 - C.LONG_CYCLE_HARD_INVALIDATION_PCT),
            float(broad_low) * (1.0 - 0.02) if np.isfinite(broad_low) else float("-inf"),
        )
        if np.isfinite(l) and l <= invalid_level:
            fill = o if o < invalid_level else invalid_level
            close_tranches(i, "إلغاء-دورة", fill)
            continue

        for tr in tranches:
            tr["peak"] = max(tr["peak"], h)
        if bool(top_zone.iloc[i]):
            top_seen = True

        # Distribution is staged: one tranche per confirmed weakness event.
        if top_seen and bool(weakness_event.iloc[i]) and tranches:
            tr = tranches.pop()  # distribute the latest tranche first
            records.append(_record(symbol, tr["stage"], series, tr["entry_i"],
                                   i, tr["entry_ref"], tr["entry_px"],
                                   tr["entry_cost"], c, "توزيع-قمة",
                                   tr["notional"], idx, cost_at(i)))
            if not tranches:
                top_seen = False
                next_stage = 0
            continue

        # Add only on a controlled retest/renewed structure confirmation; never
        # keep buying a falling market merely because it is cheaper.
        if (not top_seen and next_stage < len(weights)
                and bool(entry_signal.iloc[i])
                and c <= min(t["entry_px"] for t in tranches)
                * (1.0 - C.LONG_CYCLE_STAGE_GAP_PCT)):
            schedule_buy(next_stage, i)

    if tranches:
        final_i = n - 1
        final_px = float(h4["close"].iloc[final_i])
        close_tranches(final_i, "نهاية-العينة", final_px)
    return records
