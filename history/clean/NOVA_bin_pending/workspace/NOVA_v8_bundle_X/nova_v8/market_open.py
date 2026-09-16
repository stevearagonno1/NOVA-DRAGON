"""Independent market-open expansion sleeve.

The crypto market is continuous, so this module uses explicit reference sessions
(Tokyo, London, New York) and their real local opening times, including DST.  A
60-minute pre-open range is built from completed 5m bars; a confirmed close
outside the range schedules a next-5m-open entry.  The sleeve is long-only by
default, one trade per session, with range protection, a time filter, and an ATR
trail.  It is not part of the default core Baseline.
"""
from __future__ import annotations

import json
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from . import config as C
from . import indicators as ind
from .execution import Position, market_cost_pct, market_fill, settle_directional


def _session_opens(idx: pd.DatetimeIndex):
    if len(idx) == 0:
        return []
    start = idx[0].tz_convert("UTC").date() - timedelta(days=2)
    end = idx[-1].tz_convert("UTC").date() + timedelta(days=2)
    out = []
    day = start
    while day <= end:
        for name, zone, hour, minute in C.MARKET_OPEN_SESSIONS:
            local = datetime.combine(day, time(hour, minute),
                                     tzinfo=ZoneInfo(zone))
            utc = pd.Timestamp(local.astimezone(timezone.utc))
            out.append((utc, name))
        day += timedelta(days=1)
    return sorted(out)


def _resample_5m(df: pd.DataFrame) -> pd.DataFrame:
    return df.resample(C.MARKET_OPEN_TIMEFRAME, label="left", closed="left").agg({
        "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum",
    }).dropna()


def _record(symbol, session, side, entry_i, exit_i, entry_ref, entry_px,
            entry_cost, exit_px, reason, notional, idx, hi, lo,
            exit_cost=None) -> dict:
    regime = C.REGIME_BULL if side == 1 else C.REGIME_BEAR
    pos = Position(symbol=symbol, side=side, entry=entry_px, entry_px=entry_px,
                   atr_pct=0.01, trigger=f"{session}-Expansion", regime=regime,
                   notional=notional, entry_bar=entry_i,
                   entry_ref_px=entry_ref, entry_cost_pct=entry_cost)
    net = settle_directional(pos, exit_px,
                             slip_pct=(C.SLIPPAGE_PCT if exit_cost is None
                                       else exit_cost))
    return {
        "category": C.CAT_MARKET_OPEN, "kind": "market_open",
        "strategy": "market_open", "symbol": symbol,
        "regime": regime, "trigger": f"{session}-Expansion", "side": side,
        "entry_bar": int(entry_i), "exit_bar": int(exit_i),
        "entry_time": pd.Timestamp(idx[entry_i]).isoformat(),
        "exit_time": pd.Timestamp(idx[exit_i]).isoformat(),
        "bars_held": int(exit_i - entry_i), "net_frac": net,
        "pnl_usd": net * notional, "notional_usd": notional,
        "reason": reason, "cycles": 0, "success": bool(net > 0),
        "risk_accepted": True, "risk_reason": "", "risk_would_block": False,
        "entry_px": entry_px, "entry_ref_px": entry_ref,
        "entry_cost_pct": entry_cost, "exit_px": exit_px,
        "mult": 1, "experiment": C.EXPERIMENT_NAME,
        "series": int(entry_i),
        "snapshot": json.dumps({"session": session, "pre_high": hi,
                                "pre_low": lo, "tf": C.MARKET_OPEN_TIMEFRAME},
                               ensure_ascii=False),
    }


def run(df1m: pd.DataFrame, symbol: str) -> list[dict]:
    """Run the independent session-expansion sleeve on one symbol."""
    h5 = _resample_5m(df1m)
    if len(h5) < 100:
        return []
    atr = ind.wilder_atr(h5, C.ATR_LEN)
    atr_pct = (atr / h5["close"].replace(0.0, np.nan)).to_numpy(float)
    idx = h5.index
    n = len(h5)
    o = h5["open"].to_numpy(float)
    hi_arr = h5["high"].to_numpy(float)
    lo_arr = h5["low"].to_numpy(float)
    c = h5["close"].to_numpy(float)
    records: list[dict] = []
    traded_sessions: set[tuple[str, str]] = set()

    def exit_cost_at(bar_i: int) -> float:
        ref = bar_i - 1 if bar_i > 0 else bar_i
        v = atr_pct[ref] if 0 <= ref < n and np.isfinite(atr_pct[ref]) else None
        return market_cost_pct(float(v) if v is not None else None, C.REGIME_BULL)

    for open_ts, session in _session_opens(idx):
        pre_start = open_ts - pd.Timedelta(minutes=C.MARKET_OPEN_PRE_MINUTES)
        post_end = open_ts + pd.Timedelta(minutes=C.MARKET_OPEN_POST_MINUTES)
        hold_end = open_ts + pd.Timedelta(minutes=5 * C.MARKET_OPEN_MAX_HOLD_BARS)
        pre_pos = np.where((idx >= pre_start) & (idx < open_ts))[0]
        post_pos = np.where((idx >= open_ts) & (idx < hold_end))[0]
        if len(pre_pos) < max(10, C.MARKET_OPEN_PRE_MINUTES // 5 - 2):
            continue
        if len(post_pos) < 2:
            continue
        pre_hi = float(np.max(hi_arr[pre_pos]))
        pre_lo = float(np.min(lo_arr[pre_pos]))
        if not np.isfinite(pre_hi) or not np.isfinite(pre_lo) or pre_hi <= pre_lo:
            continue
        session_key = (session, open_ts.isoformat())
        position = None
        pending = None
        for i in post_pos:
            i = int(i)
            # Execute a signal only at the next completed 5m bar's open.
            if pending is not None and pending["entry_i"] == i:
                side = pending["side"]
                if np.isfinite(o[i]) and o[i] > 0:
                    ref_atr = atr_pct[pending["decision_i"]]
                    ref_atr = float(ref_atr) if np.isfinite(ref_atr) else 0.01
                    ecost = market_cost_pct(ref_atr, C.REGIME_BULL)
                    entry_px = market_fill(float(o[i]), side, ecost)
                    position = {
                        "side": side, "entry_i": i, "entry_ref": float(o[i]),
                        "entry_px": entry_px, "entry_cost": ecost,
                        "atr": ref_atr, "stop": pre_hi if side == 1 else pre_lo,
                        "trail": 0.0, "active": False, "wm": entry_px,
                    }
                pending = None
            if position is not None:
                side = position["side"]
                ep = position["entry_px"]
                stop = position["stop"]
                if side == 1:
                    if lo_arr[i] <= stop:
                        fill = o[i] if o[i] < stop else stop
                        records.append(_record(symbol, session, side,
                                               position["entry_i"], i,
                                               position["entry_ref"], ep,
                                               position["entry_cost"], fill,
                                               "وقف-افتتاح", C.MARKET_OPEN_NOTIONAL,
                                               idx, pre_hi, pre_lo,
                                               exit_cost=exit_cost_at(i)))
                        position = None
                    else:
                        position["wm"] = max(position["wm"], hi_arr[i])
                else:
                    if hi_arr[i] >= stop:
                        fill = o[i] if o[i] > stop else stop
                        records.append(_record(symbol, session, side,
                                               position["entry_i"], i,
                                               position["entry_ref"], ep,
                                               position["entry_cost"], fill,
                                               "وقف-افتتاح", C.MARKET_OPEN_NOTIONAL,
                                               idx, pre_hi, pre_lo,
                                               exit_cost=exit_cost_at(i)))
                        position = None
                    else:
                        position["wm"] = min(position["wm"], lo_arr[i])

                if position is not None:
                    gain = ((position["wm"] - ep) / ep * side)
                    gain_atr = gain / max(position["atr"], 1e-9)
                    if not position["active"] and gain_atr >= C.MARKET_OPEN_TRAIL_ACT_ATR:
                        position["active"] = True
                        position["trail"] = ep
                    if position["active"]:
                        if side == 1:
                            position["trail"] = max(
                                position["trail"],
                                position["wm"] * (1.0 - C.MARKET_OPEN_TRAIL_DIST_ATR
                                                   * position["atr"]),
                            )
                            if lo_arr[i] <= position["trail"]:
                                fill = o[i] if o[i] < position["trail"] else position["trail"]
                                records.append(_record(symbol, session, side,
                                                       position["entry_i"], i,
                                                       position["entry_ref"], ep,
                                                       position["entry_cost"], fill,
                                                       "تتبع-افتتاح", C.MARKET_OPEN_NOTIONAL,
                                                       idx, pre_hi, pre_lo,
                                               exit_cost=exit_cost_at(i)))
                                position = None
                        else:
                            position["trail"] = min(
                                position["trail"] or float("inf"),
                                position["wm"] * (1.0 + C.MARKET_OPEN_TRAIL_DIST_ATR
                                                   * position["atr"]),
                            )
                            if hi_arr[i] >= position["trail"]:
                                fill = o[i] if o[i] > position["trail"] else position["trail"]
                                records.append(_record(symbol, session, side,
                                                       position["entry_i"], i,
                                                       position["entry_ref"], ep,
                                                       position["entry_cost"], fill,
                                                       "تتبع-افتتاح", C.MARKET_OPEN_NOTIONAL,
                                                       idx, pre_hi, pre_lo,
                                               exit_cost=exit_cost_at(i)))
                                position = None

                    if position is not None:
                        held = i - position["entry_i"]
                        if held >= C.MARKET_OPEN_TIME_STOP_BARS:
                            gain_atr = ((c[i] - ep) / ep * side
                                        / max(position["atr"], 1e-9))
                            if gain_atr < C.MARKET_OPEN_TIME_STOP_ATR:
                                records.append(_record(symbol, session, side,
                                                       position["entry_i"], i,
                                                       position["entry_ref"], ep,
                                                       position["entry_cost"], c[i],
                                                       "زمني-افتتاح", C.MARKET_OPEN_NOTIONAL,
                                                       idx, pre_hi, pre_lo,
                                               exit_cost=exit_cost_at(i)))
                                position = None
                        if position is not None and held >= C.MARKET_OPEN_MAX_HOLD_BARS:
                            records.append(_record(symbol, session, side,
                                                   position["entry_i"], i,
                                                   position["entry_ref"], ep,
                                                   position["entry_cost"], c[i],
                                                   "أفق-افتتاح", C.MARKET_OPEN_NOTIONAL,
                                                   idx, pre_hi, pre_lo,
                                               exit_cost=exit_cost_at(i)))
                            position = None

            # Detect the next signal only after the current bar is closed.
            if (position is None and pending is None
                    and not traded_sessions.__contains__(session_key)
                    and idx[i] < post_end):
                if i + 1 >= n or idx[i + 1] >= hold_end:
                    continue
                prev = c[i - 1] if i > 0 else c[i]
                ref_atr = atr_pct[i - 1] if i > 0 and np.isfinite(atr_pct[i - 1]) else 0.01
                buffer = max(0.0005, C.MARKET_OPEN_BREAK_BUFFER_ATR * float(ref_atr))
                long_break = (c[i] > pre_hi * (1.0 + buffer)
                              and prev <= pre_hi
                              and c[i] <= pre_hi * (1.0 + C.MARKET_OPEN_CHASE_BUFFER_ATR * buffer))
                short_break = (c[i] < pre_lo * (1.0 - buffer)
                               and prev >= pre_lo
                               and c[i] >= pre_lo * (1.0 - C.MARKET_OPEN_CHASE_BUFFER_ATR * buffer))
                side = 1 if long_break else (-1 if short_break else 0)
                if side == -1 and C.MARKET_OPEN_DIRECTION != "both":
                    side = 0
                if side:
                    pending = {"entry_i": i + 1, "decision_i": i, "side": side}
                    traded_sessions.add(session_key)

        if position is not None:
            final_i = int(post_pos[-1])
            records.append(_record(symbol, session, position["side"],
                                   position["entry_i"], final_i,
                                   position["entry_ref"], position["entry_px"],
                                   position["entry_cost"], c[final_i],
                                   "نهاية-نافذة-افتتاح", C.MARKET_OPEN_NOTIONAL,
                                   idx, pre_hi, pre_lo,
                                   exit_cost=exit_cost_at(final_i)))
    return records
