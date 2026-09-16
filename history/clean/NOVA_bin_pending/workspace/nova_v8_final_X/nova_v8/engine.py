"""Engine — research replay that turns a symbol's feature matrix into results.

Runs the three operating modes over a single symbol and aggregates everything
into per-condition records:

  * DIRECTIONAL: regime bull/bear -> trigger-driven long/short entries with the
    ATR exit engine (only one open position at a time, equal $ notional).
  * GRID:       contiguous CHOP regimes -> one spot grid unit per regime run.
  * BTC pass    runs across symbols in the orchestrator (run_research) because
    it needs cross-coin correlation alignment.

This file contains the per-symbol directional/grid replay and the result
accounting/reporting layer. No-lookahead is enforced: a signal on a closed bar
is acted on at the NEXT bar's open; exits use worst-case fills.
"""
from __future__ import annotations

import logging
import math

import numpy as np
import pandas as pd

from . import config as C
from .execution import (Position, ExitEngine, settle_directional,
    market_cost_pct, market_fill, net_fraction, GOOD_PROFIT_THRESHOLD)
from .oracle import TruthOracle, RegimeTransitions, run_truth_labeling
from . import feeds
from . import long_cycle, market_open
from .strategy_registry import ids as strategy_ids, active_ids

log = logging.getLogger("nova.engine")

# ----------------------------------------------------------------- record keys
D = {
    "category": "category", "kind": "kind", "symbol": "symbol",
    "regime": "regime", "trigger": "trigger", "side": "side",
    "entry_bar": "entry_bar", "exit_bar": "exit_bar", "net_frac": "net_frac",
    "pnl_usd": "pnl_usd", "reason": "reason", "cycles": "cycles",
    "success": "success", "bars_held": "bars_held",
    "strategy": "strategy", "entry_time": "entry_time",
    "exit_time": "exit_time", "notional_usd": "notional_usd",
    "risk_accepted": "risk_accepted", "risk_reason": "risk_reason",
    "risk_would_block": "risk_would_block",
    "entry_px": "entry_px", "entry_ref_px": "entry_ref_px",
    "entry_cost_pct": "entry_cost_pct", "exit_px": "exit_px", "mult": "mult",
    "experiment": "experiment", "series": "series", "snapshot": "snapshot",
}
CSV_COLUMNS = ["category", "kind", "strategy", "symbol", "regime", "trigger", "side",
               "entry_bar", "exit_bar", "entry_time", "exit_time", "bars_held",
               "net_frac", "pnl_usd", "notional_usd", "reason", "cycles",
               "success", "risk_accepted", "risk_reason", "risk_would_block",
               "entry_px", "entry_ref_px", "entry_cost_pct", "exit_px",
               "mult", "experiment", "series", "snapshot"]


def _allowed(trigger: str) -> bool:
    cfg = C.ENABLE_TRIGGERS
    if cfg == "all":
        return True
    return trigger in {t.strip() for t in cfg.split(",") if t.strip()}


def _snapshot(mat, i):
    """Indicator readings at the *decision* bar used to open (research record)."""
    arr = mat.arr

    def g(k):
        a = arr.get(k)
        if a is None or not (0 <= i < len(a)):
            return None
        v = a[i]
        if isinstance(v, (float, np.floating)) and not math.isfinite(float(v)):
            return None
        return float(v) if isinstance(v, (int, float, np.floating, np.integer)) else v

    out = {}
    for k in ("close", "rsi", "rsi7", "macd", "adx", "stoch_k", "stoch_d",
              "mss", "sfp", "vr", "hurst", "atr14", "vol_sma20", "volume"):
        out[k] = g(k)
    c_, v_ = out.get("close"), out.get("volume")
    if out.get("vol_sma20"):
        out["vol_ratio"] = (v_ / out["vol_sma20"]) if v_ is not None else None
    if c_ and out.get("atr14"):
        out["atr_pct"] = out["atr14"] / c_
    out.pop("volume", None)
    return out


def _open_position(mat, eng, i, side, trig, atr, c, r_open, reg_decision,
                   vr_ref=None, mult=1, series=0):
    """Open at bar ``i`` using only information known by bar ``i-1``.

    Market entries receive the adverse effective execution-cost proxy.  The
    entry price stored on Position is therefore the executed estimate, not an
    optimistic untouched candle price.
    """
    if atr[i - 1] is None or not math.isfinite(float(atr[i - 1])):
        return None
    pc = c[i - 1]
    if not (math.isfinite(float(pc)) and pc > 0):
        return None
    atr_pct = float(atr[i - 1]) / float(pc)
    if not (atr_pct > 0 and r_open > 0):
        return None
    entry_cost = (market_cost_pct(vr_ref, str(reg_decision))
                  if C.MARKET_COST_ON_ENTRY else 0.0)
    entry_fill = market_fill(float(r_open), int(side), entry_cost)
    pos = Position(symbol=mat.symbol, side=side, entry=entry_fill,
                   entry_px=entry_fill, atr_pct=atr_pct, trigger=str(trig),
                   regime=str(reg_decision),
                   notional=C.NOTIONAL_BASE * mult, entry_bar=i, multi=mult,
                   series=series, entry_ref_px=float(r_open),
                   entry_cost_pct=entry_cost)
    eng.arm(pos)
    return pos


def replay_directional(mat: feeds.Matrix) -> list[dict]:
    """Directional trigger trades + chapter-6 "new signal" re-entry rule.

    Whenever a *new, allowed, same-direction* signal fires while a position is
    open (both evaluated on a closed bar, acted on the next bar's open):
      (a) if the open trade has reached "good profit" (>= GOOD_PROFIT_THRESHOLD)
          we harvest it now and reopen a doubled position (chain 2x -> 4x then
          the series resets to 1x) — the realised win is banked separately so it
          can not be given back ("the winning path is kept");
      (b) if it is only at small / no profit, we do not open; we instead grant
          the open trade extra time before its short time-stop (succession of
          signals = evidence of continued improvement).
    """
    arr = mat.arr
    o, h, l, c = arr["open"], arr["high"], arr["low"], arr["close"]
    atr = arr.get("atr14")
    if atr is None:
        raise KeyError("matrix missing atr14 column")
    vrA = arr.get("vr")
    n = mat.n
    sideA = mat.side.to_numpy(np.int8)
    trigA = mat.trig.to_numpy(dtype=object)
    regA = mat.regime.to_numpy(dtype=object)

    def _slip_at(e, regime):
        """Effective market cost using only the last known bar's VR."""
        ref = e - 1 if e > 0 else e
        if vrA is not None and 0 <= ref < n and np.isfinite(float(vrA[ref])):
            vr = float(vrA[ref])
        else:
            vr = None
        return market_cost_pct(vr, regime)

    recs: list[dict] = []
    eng = ExitEngine()
    pos: Position | None = None
    snap: dict | None = None
    pending_side, pending_trig = 0, None
    dbl_cap = 1 << C.MAX_DOUBLE_STEPS           # 2 steps -> cap multiplier 4
    # latency bookkeeping (documented live constraint, not a trade input)
    lat_signals = 0
    lat_during_open = 0
    lat_age_sum = 0

    def _record(pos_, fill_px, net, reason, exit_bar, snap_, series_):
        recs.append({
            D["category"]: C.CAT_DIRECTIONAL, D["kind"]: "dir",
            D["strategy"]: "directional", D["symbol"]: pos_.symbol,
            D["regime"]: pos_.regime,
            D["trigger"]: pos_.trigger, D["side"]: pos_.side,
            D["entry_bar"]: pos_.entry_bar, D["exit_bar"]: exit_bar,
            D["entry_time"]: pd.Timestamp(mat.df.index[pos_.entry_bar]).isoformat(),
            D["exit_time"]: pd.Timestamp(mat.df.index[exit_bar]).isoformat(),
            D["bars_held"]: exit_bar - pos_.entry_bar,
            D["net_frac"]: net, D["pnl_usd"]: net * pos_.notional,
            D["notional_usd"]: pos_.notional,
            D["reason"]: reason, D["cycles"]: 0,
            D["success"]: bool(net > 0), D["risk_accepted"]: True,
            D["risk_reason"]: "", D["risk_would_block"]: False,
            D["entry_px"]: pos_.entry_px,
            D["entry_ref_px"]: pos_.entry_ref_px,
            D["entry_cost_pct"]: pos_.entry_cost_pct,
            D["exit_px"]: fill_px,
            D["mult"]: pos_.multi, D["experiment"]: C.EXPERIMENT_NAME,
            D["series"]: series_, D["snapshot"]: snap_,
        })

    for i in range(1, n):
        r_open, r_hi, r_lo, r_close = (float(o[i]), float(h[i]),
                                       float(l[i]), float(c[i]))
        reg_cur = regA[i]

        # ---- resolve a pending signal (closed on bar i-1), act at open[i] ----
        if pending_side != 0:
            lat_signals += 1
            lat_age_sum += (i - (i - 1))          # always 1 bar by design
            if pos is not None:
                lat_during_open += 1
            reg_decision = regA[i - 1] if regA[i - 1] else C.REGIME_CHOP
            side = int(pending_side)
            # direction must agree with the market state (ch.7 operating map)
            allowed_dir = (reg_decision in C.TRADE_REGIMES
                           and ((side == 1 and reg_decision == C.REGIME_BULL)
                                or (side == -1 and reg_decision == C.REGIME_BEAR)))
            allowed = allowed_dir and _allowed(str(pending_trig))

            if pos is None:
                if allowed:
                    newp = _open_position(mat, eng, i, side, pending_trig, atr,
                                          c, r_open, reg_decision,
                                          vr_ref=(float(vrA[i - 1])
                                                  if vrA is not None and
                                                  np.isfinite(float(vrA[i - 1]))
                                                  else None))
                    if newp is not None:
                        pos = newp
                        snap = _snapshot(mat, i - 1)
            else:
                # ---- chapter 6 re-entry while a position is already open ----
                if (allowed and C.REENTRY_ENABLED
                        and int(pending_side) == pos.side):
                    net_now = settle_directional(pos, r_open,
                                                 _slip_at(i, str(regA[i - 1])))
                    if net_now >= GOOD_PROFIT_THRESHOLD:
                        # (a) harvest the winning trade at this bar's open
                        _record(pos, r_open, net_now, ExitEngine.HARVEST, i,
                                snap, pos.series)
                        # open a continuation (doubled), or reset after the cap
                        new_mult = pos.multi * 2
                        if new_mult > dbl_cap:
                            new_mult = 1
                        newp = _open_position(mat, eng, i, pos.side,
                                              pending_trig, atr, c, r_open,
                                              reg_decision,
                                              vr_ref=(float(vrA[i - 1])
                                                      if vrA is not None and
                                                      np.isfinite(float(vrA[i - 1]))
                                                      else None),
                                              mult=new_mult, series=pos.series + 1)
                        if newp is not None:
                            pos = newp
                            snap = _snapshot(mat, i - 1)
                    else:
                        # (b) small profit -> give the open trade more time
                        pos.time_grace += C.FOLLOWUP_TIME_GRACE_BARS
            pending_side, pending_trig = 0, None

        # ---- manage the (possibly just-continued) position through bar i ----
        if pos is not None:
            res = eng.update(pos, r_open, r_hi, r_lo, i, str(reg_cur), r_close)
            if res:
                reason, fill_px = res
                net = settle_directional(pos, fill_px,
                                         _slip_at(i, str(regA[i - 1])))
                _record(pos, fill_px, net, reason, i, snap, pos.series)
                pos = None
                snap = None

        # ---- capture this bar's signal for next iteration ----
        pending_side = int(sideA[i])
        pending_trig = trigA[i]

    # close any still-open position at the last close
    if pos is not None:
        last_px = float(c[n - 1])
        net = settle_directional(pos, last_px,
                                 _slip_at(n - 1, str(regA[n - 2])))
        _record(pos, last_px, net, ExitEngine.TIME, n - 1, snap, pos.series)
    mat.latency = {
        "signals": lat_signals,
        "during_open": lat_during_open,
        "signal_age_bars": (lat_age_sum / lat_signals) if lat_signals else 1.0,
    }
    return recs



# ------------------------------------------------------------- grid replay
def replay_grid(mat: feeds.Matrix) -> list[dict]:
    """One spot-grid research unit per contiguous CHOP regime run."""
    from .grid import Grid
    arr = mat.arr
    o, h, l, c = arr["open"], arr["high"], arr["low"], arr["close"]
    vr = arr.get("vr")
    idx = mat.df.index
    n = mat.n

    def _grid_slip(bar_i: int) -> float:
        # Use only the last completed bar's VR for a forced market flatten.
        ref = bar_i - 1 if bar_i > 0 else bar_i
        value = None
        if vr is not None and 0 <= ref < n and np.isfinite(float(vr[ref])):
            value = float(vr[ref])
        return market_cost_pct(value, C.REGIME_CHOP)
    regime_s = mat.regime

    recs: list[dict] = []
    look = C.GRID_RANGE_LOOKBACK_BARS
    segs = RegimeTransitions.segments(regime_s)
    grids_started = 0
    for seg in segs:
        if seg["regime"] not in C.CHOP_GRID_REGIMES:
            continue
        if grids_started >= C.GRID_MAX_OPEN_GRIDS_PER_SYMBOL:
            break
        s_pos = int(idx.searchsorted(seg["start"], side="left"))
        e_pos = int(idx.searchsorted(seg["end"], side="right")) - 1
        if e_pos - s_pos < C.GRID_MIN_LIFE_BARS or s_pos < look:
            continue
        # range from the bars *before* the grid opens (no lookahead)
        lo = float(np.nanmin(l[s_pos - look:s_pos]))
        hi = float(np.nanmax(h[s_pos - look:s_pos]))
        mid = (hi + lo) / 2.0
        span_pct = (hi - lo) / mid if mid > 0 else 0.0
        if not (C.GRID_RANGE_MIN_PCT <= span_pct <= C.GRID_RANGE_MAX_PCT):
            continue
        start_price = float(c[s_pos - 1]) if s_pos >= 1 else float(c[s_pos])
        grid = Grid(mat.symbol, s_pos, lo, hi, start_price)
        for j in range(s_pos, min(e_pos + 1, n)):
            if grid.closed:
                break
            grid.on_bar(float(o[j]), float(h[j]), float(l[j]), float(c[j]), j,
                        market_slip_pct=_grid_slip(j))
        if not grid.closed:
            close_i = min(e_pos, n - 1)
            grid.close(close_i, "نهاية-الحالة", float(c[close_i]),
                       market_slip_pct=_grid_slip(close_i))
        if grid.bars < C.GRID_MIN_LIFE_BARS:
            continue
        grids_started += 1
        recs.append({
            D["category"]: C.CAT_GRID, D["kind"]: "grid",
            D["strategy"]: "grid", D["symbol"]: mat.symbol,
            D["regime"]: C.REGIME_CHOP,
            D["trigger"]: "", D["side"]: 0,
            D["entry_bar"]: s_pos, D["exit_bar"]: grid.close_bar or e_pos,
            D["entry_time"]: pd.Timestamp(mat.df.index[s_pos]).isoformat(),
            D["exit_time"]: pd.Timestamp(mat.df.index[grid.close_bar or e_pos]).isoformat(),
            D["bars_held"]: (grid.close_bar or e_pos) - s_pos,
            D["net_frac"]: 0.0, D["pnl_usd"]: grid.net_usd,
            D["notional_usd"]: C.GRID_CAPITAL_USD,
            D["reason"]: grid.close_reason, D["cycles"]: grid.cycles,
            D["success"]: bool(grid.net_usd > 0),
            D["risk_accepted"]: True, D["risk_reason"]: "",
            D["risk_would_block"]: False,
            D["entry_px"]: None, D["entry_ref_px"]: None,
            D["entry_cost_pct"]: None, D["exit_px"]: None,
            D["mult"]: 1, D["experiment"]: C.EXPERIMENT_NAME,
            D["series"]: 0, D["snapshot"]: None,
        })
    return recs


# ---------------------------------------------------------------- btc replay
def btc_records_from_pass(pass_recs: list[dict]) -> list[dict]:
    out = []
    for r in pass_recs:
        net = float(r["net"])
        out.append({
            D["category"]: C.CAT_BTC, D["kind"]: "btc",
            D["strategy"]: "btc_leadlag", D["symbol"]: r["symbol"],
            D["regime"]: C.REGIME_BULL,
            D["trigger"]: "BTC-LeadLag", D["side"]: int(r.get("side", 1)),
            D["entry_bar"]: int(r["entry_bar"]), D["exit_bar"]: int(r["exit_bar"]),
            D["entry_time"]: r.get("entry_time"), D["exit_time"]: r.get("exit_time"),
            D["bars_held"]: int(r["exit_bar"]) - int(r["entry_bar"]),
            D["net_frac"]: net, D["pnl_usd"]: net * C.NOTIONAL_BASE,
            D["notional_usd"]: C.NOTIONAL_BASE,
            D["reason"]: r["reason"], D["cycles"]: 0,
            D["success"]: bool(net > 0), D["risk_accepted"]: True,
            D["risk_reason"]: "", D["risk_would_block"]: False,
            D["entry_px"]: r.get("entry_px"),
            D["entry_ref_px"]: r.get("entry_ref_px"),
            D["entry_cost_pct"]: r.get("entry_cost_pct"),
            D["exit_px"]: r.get("exit_px"),
            D["mult"]: int(r.get("mult", 1)), D["experiment"]: C.EXPERIMENT_NAME,
            D["series"]: int(r.get("series", 0)), D["snapshot"]: None,
        })
    return out


# --------------------------------------------------------------- oracle stats
def oracle_analyze(mat: feeds.Matrix):
    """Run the post-hoc truth oracle for analytics only.

    Rows are per (regime, trigger) recent-window stability.  The second return
    value is retained as an empty compatibility placeholder; no Oracle result
    is allowed to gate historical trade decisions.
    """
    oracle = TruthOracle()
    run_truth_labeling(mat.df, mat.side, mat.trig, mat.regime, oracle)
    oracle.finalize()
    rows = []
    for k, ratio in sorted(oracle.truth_ratio.items(), key=lambda kv: -kv[1]):
        regime, trig = k
        n, _ = oracle._samples(k)
        rows.append({"regime": regime, "trigger": trig, "stability": ratio,
                     "samples": int(n)})
    # No truth score is returned for use as a trade gate.  The report is the
    # only consumer of this post-hoc/future-aware research label.
    return rows, {}


def oracle_stats(mat: feeds.Matrix) -> list[dict]:
    rows, _ = oracle_analyze(mat)
    return rows


def regime_segment_summary(mat: feeds.Matrix) -> list[dict]:
    from collections import Counter
    cnt = Counter(mat.regime.tolist())
    return [{"regime": r, "bars": cnt[r]} for r in cnt]


# ------------------------------------------------------------------ research
def _select_strategies(selection=None) -> set[str]:
    core = set(active_ids())
    if selection is None or selection == "":
        selected = set(core)
        if C.LONG_CYCLE_ENABLED:
            selected.add("long_cycle")
        if C.MARKET_OPEN_ENABLED:
            selected.add("market_open")
        return selected
    if isinstance(selection, (tuple, list, set)):
        raw = {str(x).strip() for x in selection if str(x).strip()}
    else:
        text = str(selection).strip()
        if text.lower() == "core":
            return core
        if text.lower() == "all":
            return set(strategy_ids())
        raw = {x.strip() for x in text.split(",") if x.strip()}
    unknown = raw - set(strategy_ids())
    if unknown:
        raise ValueError(f"استراتيجيات غير معروفة: {sorted(unknown)}")
    return raw


def run_research(symbols=None, on_progress=None, strategies=None) -> dict:
    """Full research pass over the symbol set. Returns a results structure and
    writes CSV + report under the output dir."""
    if C.MODE != "backtest":
        raise RuntimeError(
            f"الوضع '{C.MODE}' غير منفَّذ بعد. التشغيل الحي والتدريب مؤجَّلان "
            "حسب التصميم؛ استخدم NOVA_MODE=backtest."
        )
    symbols = symbols or C.SYMBOLS
    selected = _select_strategies(strategies)
    matrices = feeds.load_all(symbols, lazy=C.ONE_SYMBOL_AT_A_TIME)
    avail = list(matrices.keys())
    if not avail:
        raise RuntimeError(
            "لا توجد بيانات تاريخية في أرشيف العملات "
            f"({C.ARCHIVE_DIR}). ضع ملفات *_1m.parquet ثم أعد التشغيل."
        )
    all_recs: list[dict] = []
    lean = {}
    oracle_rows = []                 # analytic stability per symbol
    # Oracle is deliberately analytic-only; it never gates trade decisions.
    regime_rows = []
    quality_rows = []
    lat_stats = []                   # matrices, for the latency summary
    # We drive progress from total bars of the matrices we were able to load.
    if C.ONE_SYMBOL_AT_A_TIME:
        # lazy loading: estimate from parquet metadata (no full load)
        total_bars = sum(feeds.row_count(s) for s in avail) or 1
    else:
        total_bars = sum(m.n for m in matrices.values()) or 1
    done_bars = 0
    for s in avail:
        m = matrices[s]
        recs = replay_directional(m) if "directional" in selected else []
        all_recs.extend(recs)
        grid_u = replay_grid(m) if "grid" in selected else []
        all_recs.extend(grid_u)
        cycle_u = (long_cycle.run(m.df, s)
                   if "long_cycle" in selected else [])
        open_u = (market_open.run(m.df, s)
                  if "market_open" in selected else [])
        all_recs.extend(cycle_u)
        all_recs.extend(open_u)
        # keep only the tiny latency dict (never the full matrix) so the
        # one-symbol-at-a-time memory policy still holds
        lat_stats.append(getattr(m, "latency", {}) or {})
        if "btc_leadlag" in selected:
            lean[s] = m.df[["open", "high", "low", "close", "atr14", "vr", "mss"]]
        mss_rows = oracle_analyze(m)[0] if "directional" in selected else []
        for row in mss_rows:
            row["symbol"] = s
            oracle_rows.append(row)
        for row in regime_segment_summary(m):
            row["symbol"] = s
            regime_rows.append(row)
        quality = dict(getattr(m, "quality", {}) or {})
        quality["symbol"] = s
        quality_rows.append(quality)
        done_bars += m.n
        if on_progress:
            on_progress(done_bars / total_bars)
        log.info("symbol %s: %d directional + %d grid + %d cycle + %d open units",
                 s, len(recs), len(grid_u), len(cycle_u), len(open_u))
        # free the heavy matrix but keep the lean copy for the BTC pass
        del matrices[s]
        import gc
        gc.collect()

    # BTC lead-lag cross-coin pass (fed from the unified Oracle)
    from . import btc_leadlag
    if "btc_leadlag" in selected and C.BTC_SYMBOL in lean:
        btc_pass = btc_leadlag.run_btc_pass(lean, mss_truth=None)
        all_recs.extend(btc_records_from_pass(btc_pass))
    del lean

    # latency summary (documented live constraint: execution is next-bar by design)
    tot_sig = sum(d.get("signals", 0) for d in lat_stats)
    tot_open = sum(d.get("during_open", 0) for d in lat_stats)
    ages = [d.get("signal_age_bars", 1.0) for d in lat_stats]
    latency = {
        "mean_signal_age_bars": (sum(ages) / len(ages)) if ages else 1.0,
        "overlap_pct": (tot_open / tot_sig * 100.0) if tot_sig else 0.0,
        "signals": tot_sig,
    }

    from . import risk
    risk_result = risk.audit_records(all_recs, C.PORTFOLIO_RISK_MODE)
    reported_records = (all_recs if C.PORTFOLIO_RISK_MODE != "strict"
                        else [r for r in all_recs if r.get("risk_accepted", True)])
    result = build_result(reported_records)
    result["latency"] = latency
    result["risk"] = {k: v for k, v in risk_result.items()
                       if k not in ("accepted_records", "blocked_records")}
    result["selected_strategies"] = sorted(selected)
    # CSV keeps every raw record plus the guard verdict for auditability; the
    # rendered result obeys strict filtering when that mode is explicitly set.
    _write_csv(all_recs)
    _write_report(result)
    _write_stability(oracle_rows, regime_rows)
    _write_flip_report(result["records"])
    _write_strategy_reports(result["records"], selected)
    risk.write_report(risk_result, C.RISK_PATH)
    _write_quality(quality_rows)
    return result


# ---------------------------------------------------------------- accounting
def _win_lose(recs):
    wins = sum(1 for r in recs if r[D["success"]])
    decided = sum(1 for r in recs if r[D["pnl_usd"]] != 0.0)
    loses = decided - wins
    pnl = sum(r[D["pnl_usd"]] for r in recs)
    return wins, loses, pnl, decided


def summarize_category(recs):
    wins, loses, pnl, decided = _win_lose(recs)
    n = len(recs)
    win_pct = (wins / decided * 100.0) if decided else 0.0
    lose_pct = (loses / decided * 100.0) if decided else 0.0
    return {
        "total": n, "wins": wins, "loses": loses, "decided": decided,
        "pnl_usd": pnl, "win_pct": win_pct, "lose_pct": lose_pct,
    }


def by_condition(recs):
    """Per-(regime, trigger) directional results."""
    groups = {}
    for r in recs:
        k = (r[D["regime"]], r[D["trigger"]])
        groups.setdefault(k, []).append(r)
    return {k: summarize_category(v) for k, v in sorted(groups.items())}


def build_result(all_recs: list[dict]) -> dict:
    dir_recs = [r for r in all_recs if r[D["kind"]] == "dir"]
    grid_recs = [r for r in all_recs if r[D["kind"]] == "grid"]
    btc_recs = [r for r in all_recs if r[D["kind"]] == "btc"]
    cycle_recs = [r for r in all_recs if r[D["kind"]] == "long_cycle"]
    open_recs = [r for r in all_recs if r[D["kind"]] == "market_open"]
    return {
        "records": all_recs,
        "counts": {
            C.CAT_DIRECTIONAL: len(dir_recs),
            C.CAT_GRID: len(grid_recs),
            C.CAT_BTC: len(btc_recs),
            C.CAT_LONG_CYCLE: len(cycle_recs),
            C.CAT_MARKET_OPEN: len(open_recs),
        },
        "directional": summarize_category(dir_recs),
        "directional_by_condition": by_condition(dir_recs),
        "grid": summarize_category(grid_recs),
        "btc": summarize_category(btc_recs),
        "long_cycle": summarize_category(cycle_recs),
        "market_open": summarize_category(open_recs),
        "grid_cycles": sum(r[D["cycles"]] for r in grid_recs),
        "latency": None,
    }


# ------------------------------------------------------------------- writers
def _write_csv(records: list[dict]) -> None:
    import json as _json
    if not records:
        pd.DataFrame(columns=CSV_COLUMNS).to_csv(C.RESULT_PATH, index=False)
        return
    # serialise each record's entry snapshot (indicator readings) to JSON text
    rows = []
    for r in records:
        row = dict(r)
        snap = row.get("snapshot")
        row["snapshot"] = _json.dumps(snap, default=str) if snap else ""
        rows.append(row)
    frame = pd.DataFrame(rows)
    for col in CSV_COLUMNS:
        if col not in frame.columns:
            frame[col] = ""
    frame = frame[CSV_COLUMNS]
    C.RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(C.RESULT_PATH, index=False)
    log.info("wrote %d records -> %s", len(records), C.RESULT_PATH)


def _pct_line(title, s):
    return (f"{title}: إجمالي {s['total']} · 🟢 رابح {s['wins']} "
            f"({s['win_pct']:.1f}%) · 🟥 خاسر {s['loses']} ({s['lose_pct']:.1f}%) · "
            f"صافي {s['pnl_usd']:.2f}$")


def render_report(result: dict) -> str:
    """Final "تقرير الحالة" — exact approved 3-section format, then detail.

    Section 1 (📊 general / directional), section 2 (🟦 grid) and section 3
    (🟧 BTC-followers) follow the approved wording line-for-line; the optional
    per-(state, trigger) breakdown is appended after the general section, and a
    short header records the run context (experiment, trail basis, spread mode).
    """
    L: list[str] = []
    L.append("=" * 44)
    L.append("NOVA_V8 — تقرير الحالة (نتائج البحث)")
    L.append("=" * 44)
    L.append(f"التجربة: {C.EXPERIMENT_NAME} · أساس التتبّع: {C.TRAIL_BASIS} · "
             f"السبريد: {C.SPREAD_MODE} · إطار التنفيذ: {C.TF_TRADE}")

    d = result["directional"]
    L.append("")
    L.append("📊 التقرير العام")
    L.append(f"🟢 الناجحة: {d['win_pct']:.1f}%")
    L.append(f"🔴 الخاسرة: {d['lose_pct']:.1f}%")
    L.append(f"إجمالي المكاسب: {d['pnl_usd']:.2f} $")
    L.append(f"نسبة النجاح: {d['win_pct']:.1f}%")
    L.append(f"عدد الصفقات: {d['total']}")
    if d["total"]:
        L.append("")
        L.append("— تفصيل حسب (الحالة | الزناد):")
        for (regime, trig), st in result["directional_by_condition"].items():
            L.append(f"   [{regime} | {trig}] {_pct_line('', st)}")

    g = result["grid"]
    L.append("")
    L.append("🟦 نمط الشبكة (Grid)")
    L.append(f"عدد الشبكات المغلقة: {g['total']} · ناجحة: {g['win_pct']:.1f}% · "
             f"صافي: {g['pnl_usd']:.2f}$")
    L.append(f"(إجمالي دورات الحصاد: {result['grid_cycles']})")

    b = result["btc"]
    L.append("")
    L.append("🟧 تابعات البيتكوين (BTC)")
    L.append(f"عدد الصفقات: {b['total']} · ناجحة: {b['win_pct']:.1f}% · "
             f"صافي: {b['pnl_usd']:.2f}$")

    if result.get("latency"):
        lat = result["latency"]
        L.append("")
        L.append("⏱️ ملاحظة زمن الاستجابة (قيد حيّ):")
        L.append(f"   متوسط عمر الإشارة: {lat['mean_signal_age_bars']:.2f} شمعة · "
                 f"تداخل صفقات: {lat['overlap_pct']:.1f}%")

    L.append("")
    L.append("=" * 44)
    return "\n".join(L)


def _write_report(result: dict) -> None:
    C.REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    C.REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    log.info("report -> %s", C.REPORT_PATH)


def _write_flip_report(records: list[dict]) -> None:
    """Slippage sensitivity ('flip point') per trigger.

    Because every record stores entry/exit px and side, we recompute the net at
    each slippage tier WITHOUT re-running the backtest. The report shows, per
    trigger, the mean net frac (and implied profit) at base / 0.1% / 0.3% and
    flags the tier at which that trigger turns negative (its fragility under
    execution slippage — a key answer to 'can the bot execute at the prices the
    backtest assumed?').
    """
    dir_recs = [r for r in records if r[D["kind"]] == "dir"]
    by_trig: dict[str, list] = {}
    for r in dir_recs:
        if r.get("entry_px") and r.get("exit_px"):
            by_trig.setdefault(r[D["trigger"]], []).append(r)

    lines = ["NOVA_V8 — تقرير حساسية الانزلاق (نقطة الانقلاب لكل محفّز)\n"]
    lines.append("القيم = متوسط الصافي النسبي للصفقة عند مستوى انزلاق مفترض؛ "
                 "السالب يعني أن التكلفة تتآكل الصفقة.\n")
    tiers = C.SLIPPAGE_TIERS
    hdr = "المحفّز".ljust(12) + "".join(f"{t*100:.2f}%".rjust(12) for t in tiers)
    lines.append(hdr)
    lines.append("-" * len(hdr))
    for trig, grp in sorted(by_trig.items(), key=lambda kv: -len(kv[1])):
        row = trig.ljust(12)
        for t in tiers:
            nets = []
            for r in grp:
                side = int(r[D["side"]])
                ref = r.get(D["entry_ref_px"])
                entry = (float(ref) * (1.0 + t * side)
                         if ref is not None and float(ref) > 0
                         else float(r["entry_px"]))
                nets.append(net_fraction(entry, r["exit_px"], side, t))
            mean = float(sum(nets)) / len(nets)
            row += f"{mean*100:+.3f}%".rjust(12)
        lines.append(row)
    lines.append("")
    lines.append("n = عدد صفقات المحفّز (متوسط) لكل خلية.")
    lines.append("المحفّزات ذات صافي يقلب سالباً عند انزلاق منخفض هي الأكثر "
                 "هشاشةً تجاه واقعية التنفيذ.")
    C.FLIP_PATH.parent.mkdir(parents=True, exist_ok=True)
    C.FLIP_PATH.write_text("\n".join(lines), encoding="utf-8")
    log.info("slippage flip report -> %s", C.FLIP_PATH)


def _write_strategy_reports(records: list[dict], selected: set[str]) -> None:
    groups = {
        "long_cycle": [r for r in records if r.get("strategy") == "long_cycle"],
        "market_open": [r for r in records if r.get("strategy") == "market_open"],
    }
    for sid, path in (("long_cycle", C.LONG_CYCLE_PATH),
                      ("market_open", C.MARKET_OPEN_PATH)):
        stats = summarize_category(groups[sid])
        lines = [f"NOVA_V8 — {sid} sleeve report", "",
                 f"selected: {sid in selected}",
                 f"records: {stats['total']}",
                 f"wins: {stats['wins']} ({stats['win_pct']:.2f}%)",
                 f"losses: {stats['loses']} ({stats['lose_pct']:.2f}%)",
                 f"net_usd: {stats['pnl_usd']:.4f}",
                 "",
                 "هذه وحدة مستقلة؛ لا تدخل Baseline إلا عند اختيارها صراحة."]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary = ["NOVA_V8 — Strategy Sleeve Summary", ""]
    for sid in ("long_cycle", "market_open"):
        st = summarize_category(groups[sid])
        summary.append(f"{sid}: selected={sid in selected} records={st['total']} "
                       f"net={st['pnl_usd']:.4f} win_pct={st['win_pct']:.2f}")
    C.STRATEGY_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    C.STRATEGY_SUMMARY_PATH.write_text("\n".join(summary) + "\n", encoding="utf-8")


def _write_quality(rows: list[dict]) -> None:
    import json as _json
    C.QUALITY_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = ["NOVA_V8 — تقرير جودة البيانات / Data Quality", ""]
    for row in rows:
        sym = row.get("symbol", "?")
        lines.append(f"[{sym}] rows={row.get('rows', 0)} "
                     f"bad_ohlcv={row.get('bad_ohlcv_rows', 0)} "
                     f"negative_volume={row.get('negative_volume_rows', 0)} "
                     f"large_gaps={row.get('gap_count', 0)} "
                     f"max_gap_min={row.get('max_gap_minutes', 0.0):.2f} "
                     f"issues={_json.dumps(row.get('issues', []), ensure_ascii=False)}")
    lines.append("")
    lines.append(f"الوضع: {C.DATA_QUALITY_MODE}; strict يوقف التشغيل عند مشاكل البيانات.")
    C.QUALITY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_stability(oracle_rows: list[dict], regime_rows: list[dict]) -> None:
    """Analytic-only stability + regime-coverage report (never gates trades)."""
    C.STABILITY_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = ["NOVA_V8 — التقرير التحليلي للاستقرار (Oracle) — مرجع فقط، لا يُستخدم للترشيح\n"]
    # best stable (regime,trigger) per symbol
    by_sym: dict[str, list[dict]] = {}
    for r in oracle_rows:
        by_sym.setdefault(r["symbol"], []).append(r)
    for sym, rows in by_sym.items():
        rows = sorted(rows, key=lambda x: -x["stability"])
        lines.append(f"\n[{sym}] الأنماط الأكثر استقراراً:")
        for r in rows[:8]:
            lines.append(f"   {r['regime']} | {r['trigger']}: "
                         f"ثبات {r['stability']*100:.1f}% ({int(r['samples'])} عينات)")
    lines.append("\n[تغطية الحالات]")
    for r in regime_rows:
        lines.append(f"   {r['symbol']} [{r['regime']}]: {r['bars']} شريط")
    C.STABILITY_PATH.write_text("\n".join(lines), encoding="utf-8")
    log.info("stability report -> %s", C.STABILITY_PATH)
