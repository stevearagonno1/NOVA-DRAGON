#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0084-ENTRY-MIX — execution container engine.

Fixed container (paper section 7, not optimised):
  decision at signal close i -> fill at next contiguous OPEN q (bar i+1)
  ATR from i, fixed for the trade; stop = q - 1.5*ATR; target = q + 1.5*ATR
  18 complete bars INCLUDING the fill bar (bars i+1 .. i+18)
  barrier checks on the seventeen future bars after the fill bar (i+2..i+18):
    opening gap at/below stop  -> exit at open
    opening gap at/above target-> exit at target (windfall withheld)
    otherwise both touched     -> stop first
    stop only / target only    -> at that barrier
  neither reached in 18 bars   -> exit at the eighteenth close
  $20 fixed notional, qty=20/q, independent $1000 paper book per asset
  one position per asset per candidate, skip while occupied/illiquid-cash
  constitutional cost $0.026 per side ($0.052 round trip) charged ONCE.

Rejections (no trade): non-finite ATR, non-positive stop, missing/incomplete
18-bar horizon, horizon bridging a data gap/segment, cash < 20.052.
"""
from __future__ import annotations

import numpy as np

NOTIONAL = 20.0
COST_RT = 0.052          # 0.13% of $20 per side, charged once round trip
BARRIER_ATR = 1.5
HORIZON = 18             # complete bars INCLUDING the fill bar
BOOK0 = 1000.0

OUTCOME_TARGET = "target"
OUTCOME_STOP = "stop"
OUTCOME_TIMEOUT = "timeout"


def _trade_record(symbol, cand, sig_i, f_i, exit_i, q, exit_px, atr, outcome,
                  gap_flag, double_touch, seg, o, h, l, c):
    """Assemble one executed-trade record (units never mixed)."""
    qty = NOTIONAL / q
    gross = (NOTIONAL / q) * (exit_px - q)
    net = gross - COST_RT
    gross_atr_r = (exit_px - q) / atr
    cost_atr = 0.0026 * q / atr
    net_atr_r = gross_atr_r - cost_atr
    lo = float(np.min(l[f_i:exit_i + 1]))
    hi = float(np.max(h[f_i:exit_i + 1]))
    return {
        "candidate_id": cand,
        "symbol": symbol,
        "signal_bar": int(sig_i),
        "fill_bar": int(f_i),
        "exit_bar": int(exit_i),
        "entry": float(q),
        "exit": float(exit_px),
        "atr": float(atr),
        "quantity": float(qty),
        "notional": NOTIONAL,
        "outcome": outcome,
        "gap_flag": bool(gap_flag),
        "double_touch": bool(double_touch),
        "holding_bars": int(exit_i - f_i),
        "gross_dollars": float(gross),
        "cost_dollars": COST_RT,
        "net_dollars": float(net),
        "gross_atr_r": float(gross_atr_r),
        "cost_atr": float(cost_atr),
        "net_atr_r": float(net_atr_r),
        "barrier_r": float(net_atr_r / BARRIER_ATR),
        "mae_atr_r": float((lo - q) / atr),
        "mfe_atr_r": float((hi - q) / atr),
        "seg": int(seg),
    }


def simulate(o, h, l, c, atr, seg_id, mask, symbol, cand):
    """Sequential one-position simulation of one mask on one asset.

    mask: boolean decision array; None => always-in no-signal book (fill at
    the next eligible bar whenever flat).  Returns (trades, counters).
    """
    n = len(c)
    trades = []
    signals = 0
    rejected = 0
    incomplete = 0
    skipped_occupied = 0
    busy_until = -1                      # last exit bar index (flat from there)
    cash = BOOK0
    always = mask is None
    if always:
        accept_at = np.ones(n, dtype=bool)
    else:
        accept_at = mask
    for i in range(n - 1):
        if not accept_at[i]:
            continue
        if always and i < busy_until:
            continue
        if i < busy_until:
            skipped_occupied += 1
            continue
        signals += 1
        f = i + 1
        last = i + HORIZON               # i+18: eighteenth complete bar
        if last >= n or seg_id[f] != seg_id[i] or seg_id[last] != seg_id[i]:
            incomplete += 1
            continue
        a = atr[i]
        q = o[f]
        if not np.isfinite(a) or a <= 0 or not np.isfinite(q) or q <= 0:
            rejected += 1
            continue
        stop = q - BARRIER_ATR * a
        target = q + BARRIER_ATR * a
        if not np.isfinite(stop) or stop <= 0:
            rejected += 1
            continue
        if cash < NOTIONAL + COST_RT:
            rejected += 1
            continue
        js = slice(i + 2, i + HORIZON + 1)          # 17 future bars
        op = o[js]
        hi = h[js]
        lo = l[js]
        gap_stop = op <= stop
        gap_tgt = op >= target
        stop_t = lo <= stop
        tgt_t = hi >= target
        # per-bar exit code with the paper's priority inside each bar
        code = np.select([gap_stop, gap_tgt, stop_t, tgt_t],
                         [1, 2, 3, 4], default=0)
        nz = np.nonzero(code)[0]
        double = int(np.sum(stop_t & tgt_t))
        if nz.size:
            k = int(nz[0])
            j = k + i + 2
            cc = int(code[k])
            if cc == 1:
                exit_px, outcome, gapflag = float(op[k]), OUTCOME_STOP, True
            elif cc == 2:
                exit_px, outcome, gapflag = float(target), OUTCOME_TARGET, True
            elif cc == 3:
                exit_px, outcome, gapflag = float(stop), OUTCOME_STOP, False
            else:
                exit_px, outcome, gapflag = float(target), OUTCOME_TARGET, False
        else:
            j = last
            exit_px, outcome, gapflag = float(c[last]), OUTCOME_TIMEOUT, False
        rec = _trade_record(symbol, cand, i, f, j, q, exit_px, a, outcome,
                            gapflag, double > 0, seg_id[i], o, h, l, c)
        trades.append(rec)
        cash += rec["net_dollars"]
        busy_until = j
    return trades, {
        "signals": signals, "executed": len(trades), "rejected": rejected,
        "incomplete": incomplete, "skipped_occupied": skipped_occupied,
    }


# --------------------------------------------------------------------------
# combination modes
# --------------------------------------------------------------------------
def combine(masks, mode, seg_id):
    """AND0 / AND2 / OR0 over member boolean arrays (dict name->array)."""
    arrs = list(masks.values())
    any_now = np.zeros_like(arrs[0])
    for a in arrs:
        any_now |= a
    if mode == "OR0":
        return any_now
    if mode == "AND0":
        out = np.ones_like(arrs[0])
        for a in arrs:
            out &= a
        return out
    if mode == "AND2":
        # EVERY member true at least once in i-2..i (AND across members);
        # at least one member true at i; the three bars contiguous.
        import pandas as pd
        ever = None
        for a in arrs:
            s = pd.Series(a.astype(float)).rolling(
                3, min_periods=3).max().to_numpy()
            r = s > 0
            ever = r if ever is None else (ever & r)
        contig = np.zeros_like(arrs[0])
        if len(arrs[0]) >= 3:
            contig[2:] = (seg_id[2:] == seg_id[:-2])
        return ever & any_now & contig
    raise ValueError(mode)


# --------------------------------------------------------------------------
# window assignment (purge + embargo)
# --------------------------------------------------------------------------
def window_trades(trades, win_first_bar, win_last_bar, embargo=HORIZON):
    """Trades belonging to an evaluation window.

    Purge: the whole signal-to-horizon-end interval must lie inside the
    window (never an early close).  Embargo: no fill within `embargo` bars
    after the window opens.
    """
    out = []
    for t in trades:
        f = t["fill_bar"]
        horizon_end = t["signal_bar"] + HORIZON
        if horizon_end > win_last_bar:
            continue
        if f < win_first_bar + embargo:
            continue
        if t["signal_bar"] < win_first_bar:
            continue
        out.append(t)
    return out


# --------------------------------------------------------------------------
# vectorised single-bar execution (used by random-entry controls); the
# scalar path in simulate() remains the reference implementation
# --------------------------------------------------------------------------
def execute_many(o, h, l, c, atr, seg_id, starts, symbol, cand):
    """Execute one trade at each start bar (vectorised over starts).

    Returns (records, masks) where masks flags ineligible starts; identical
    record semantics to simulate() (verified by tests.test_exec_equivalence).
    """
    starts = np.asarray(starts, dtype=np.int64)
    n = len(c)
    if starts.size == 0:
        return [], np.zeros(0, dtype=bool)
    f = starts + 1
    last = starts + HORIZON
    ok = (last < n) & (seg_id[f] == seg_id[starts]) & \
         (seg_id[last] == seg_id[starts])
    a = atr[starts]
    q = o[f]
    ok &= np.isfinite(a) & (a > 0) & np.isfinite(q) & (q > 0)
    stop = q - BARRIER_ATR * a
    target = q + BARRIER_ATR * a
    ok &= np.isfinite(stop) & (stop > 0)
    offs = np.arange(2, HORIZON + 1)                 # i+2 .. i+18
    OP = o[starts[:, None] + offs[None, :]]
    HI = h[starts[:, None] + offs[None, :]]
    LO = l[starts[:, None] + offs[None, :]]
    gap_stop = OP <= stop[:, None]
    gap_tgt = OP >= target[:, None]
    stop_t = LO <= stop[:, None]
    tgt_t = HI >= target[:, None]
    code = np.select([gap_stop, gap_tgt, stop_t, tgt_t],
                     [1, 2, 3, 4], default=0)
    hit = code > 0
    anyhit = hit.any(axis=1)
    k = np.argmax(hit, axis=1)
    rows = np.nonzero(ok)[0]
    recs = []
    bad = ~ok
    for r in rows:
        i = int(starts[r])
        f_i = i + 1
        if anyhit[r]:
            kk = int(k[r])
            j = i + 2 + kk
            cc = int(code[r, kk])
            if cc == 1:
                exit_px, outcome, gapflag = float(OP[r, kk]), OUTCOME_STOP, True
            elif cc == 2:
                exit_px, outcome, gapflag = (float(target[r]), OUTCOME_TARGET,
                                             True)
            elif cc == 3:
                exit_px, outcome, gapflag = float(stop[r]), OUTCOME_STOP, False
            else:
                exit_px, outcome, gapflag = (float(target[r]), OUTCOME_TARGET,
                                             False)
        else:
            j = i + HORIZON
            exit_px, outcome, gapflag = float(c[j]), OUTCOME_TIMEOUT, False
        dbl = bool((stop_t[r] & tgt_t[r]).any())
        recs.append(_trade_record(symbol, cand, i, f_i, j, float(q[r]),
                                  exit_px, float(a[r]), outcome, gapflag, dbl,
                                  seg_id[i], o, h, l, c))
    return recs, bad
