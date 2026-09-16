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
from .execution import Position, ExitEngine, settle_directional, \
    GOOD_PROFIT_THRESHOLD
from .oracle import TruthOracle, RegimeTransitions, run_truth_labeling
from . import feeds

log = logging.getLogger("nova.engine")

# ----------------------------------------------------------------- record keys
D = {
    "category": "category", "kind": "kind", "symbol": "symbol",
    "regime": "regime", "trigger": "trigger", "side": "side",
    "entry_bar": "entry_bar", "exit_bar": "exit_bar", "net_frac": "net_frac",
    "pnl_usd": "pnl_usd", "reason": "reason", "cycles": "cycles",
    "success": "success", "bars_held": "bars_held",
    "entry_px": "entry_px", "exit_px": "exit_px", "mult": "mult",
    "experiment": "experiment", "series": "series", "snapshot": "snapshot",
}
CSV_COLUMNS = ["category", "kind", "symbol", "regime", "trigger", "side",
               "entry_bar", "exit_bar", "bars_held", "net_frac", "pnl_usd",
               "reason", "cycles", "success", "entry_px", "exit_px",
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
                   mult=1, series=0):
    """Open a directional Position at bar open[i] using only bar i-1 info."""
    if atr[i - 1] is None or not math.isfinite(float(atr[i - 1])):
        return None
    pc = c[i - 1]
    if not (math.isfinite(float(pc)) and pc > 0):
        return None
    atr_pct = float(atr[i - 1]) / float(pc)
    if not (atr_pct > 0 and r_open > 0):
        return None
    pos = Position(symbol=mat.symbol, side=side, entry=r_open, entry_px=r_open,
                   atr_pct=atr_pct, trigger=str(trig), regime=str(reg_decision),
                   notional=C.NOTIONAL_BASE * mult, entry_bar=i, multi=mult,
                   series=series)
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
    n = mat.n
    sideA = mat.side.to_numpy(np.int8)
    trigA = mat.trig.to_numpy(dtype=object)
    regA = mat.regime.to_numpy(dtype=object)

    recs: list[dict] = []
    eng = ExitEngine()
    pos: Position | None = None
    snap: dict | None = None
    pending_side, pending_trig = 0, None
    dbl_cap = 1 << C.MAX_DOUBLE_STEPS           # 2 steps -> cap multiplier 4

    def _record(pos_, fill_px, net, reason, exit_bar, snap_, series_):
        recs.append({
            D["category"]: C.CAT_DIRECTIONAL, D["kind"]: "dir",
            D["symbol"]: pos_.symbol, D["regime"]: pos_.regime,
            D["trigger"]: pos_.trigger, D["side"]: pos_.side,
            D["entry_bar"]: pos_.entry_bar, D["exit_bar"]: exit_bar,
            D["bars_held"]: exit_bar - pos_.entry_bar,
            D["net_frac"]: net, D["pnl_usd"]: net * pos_.notional,
            D["reason"]: reason, D["cycles"]: 0,
            D["success"]: bool(net > 0),
            D["entry_px"]: pos_.entry_px, D["exit_px"]: fill_px,
            D["mult"]: pos_.multi, D["experiment"]: C.EXPERIMENT_NAME,
            D["series"]: series_, D["snapshot"]: snap_,
        })

    for i in range(1, n):
        r_open, r_hi, r_lo, r_close = (float(o[i]), float(h[i]),
                                       float(l[i]), float(c[i]))
        reg_cur = regA[i]

        # ---- resolve a pending signal (closed on bar i-1), act at open[i] ----
        if pending_side != 0:
            reg_decision = regA[i - 1] if regA[i - 1] else C.REGIME_CHOP
            side = int(pending_side)
            allowed_dir = ((side == 1 and reg_decision == C.REGIME_BULL)
                           or (side == -1 and reg_decision == C.REGIME_BEAR))
            allowed = allowed_dir and _allowed(str(pending_trig))

            if pos is None:
                if allowed:
                    newp = _open_position(mat, eng, i, side, pending_trig, atr,
                                          c, r_open, reg_decision)
                    if newp is not None:
                        pos = newp
                        snap = _snapshot(mat, i - 1)
            else:
                # ---- chapter 6 re-entry while a position is already open ----
                if (allowed and C.REENTRY_ENABLED
                        and int(pending_side) == pos.side):
                    net_now = settle_directional(pos, r_open)
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
                                              reg_decision, mult=new_mult,
                                              series=pos.series + 1)
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
                net = settle_directional(pos, fill_px)
                _record(pos, fill_px, net, reason, i, snap, pos.series)
                pos = None
                snap = None

        # ---- capture this bar's signal for next iteration ----
        pending_side = int(sideA[i])
        pending_trig = trigA[i]

    # close any still-open position at the last close
    if pos is not None:
        last_px = float(c[n - 1])
        net = settle_directional(pos, last_px)
        _record(pos, last_px, net, ExitEngine.TIME, n - 1, snap, pos.series)
    return recs



# ------------------------------------------------------------- grid replay
def replay_grid(mat: feeds.Matrix) -> list[dict]:
    """One spot-grid research unit per contiguous CHOP regime run."""
    from .grid import Grid
    arr = mat.arr
    o, h, l, c = arr["open"], arr["high"], arr["low"], arr["close"]
    idx = mat.df.index
    regime_s = mat.regime
    n = mat.n

    recs: list[dict] = []
    look = C.GRID_RANGE_LOOKBACK_BARS
    segs = RegimeTransitions.segments(regime_s)
    for seg in segs:
        if seg["regime"] != C.REGIME_CHOP:
            continue
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
            grid.on_bar(float(o[j]), float(h[j]), float(l[j]), float(c[j]), j)
        if not grid.closed:
            grid.close(min(e_pos, n - 1), "نهاية-الحالة", float(c[min(e_pos, n - 1)]))
        if grid.bars < C.GRID_MIN_LIFE_BARS:
            continue
        recs.append({
            D["category"]: C.CAT_GRID, D["kind"]: "grid",
            D["symbol"]: mat.symbol, D["regime"]: C.REGIME_CHOP,
            D["trigger"]: "", D["side"]: 0,
            D["entry_bar"]: s_pos, D["exit_bar"]: grid.close_bar or e_pos,
            D["bars_held"]: (grid.close_bar or e_pos) - s_pos,
            D["net_frac"]: 0.0, D["pnl_usd"]: grid.net_usd,
            D["reason"]: grid.close_reason, D["cycles"]: grid.cycles,
            D["success"]: bool(grid.net_usd > 0),
            D["entry_px"]: None, D["exit_px"]: None,
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
            D["symbol"]: r["symbol"], D["regime"]: C.REGIME_BULL,
            D["trigger"]: "BTC-LeadLag", D["side"]: int(r.get("side", 1)),
            D["entry_bar"]: int(r["entry_bar"]), D["exit_bar"]: int(r["exit_bar"]),
            D["bars_held"]: int(r["exit_bar"]) - int(r["entry_bar"]),
            D["net_frac"]: net, D["pnl_usd"]: net * C.NOTIONAL_BASE,
            D["reason"]: r["reason"], D["cycles"]: 0,
            D["success"]: bool(net > 0),
            D["entry_px"]: r.get("entry_px"), D["exit_px"]: r.get("exit_px"),
            D["mult"]: int(r.get("mult", 1)), D["experiment"]: C.EXPERIMENT_NAME,
            D["series"]: int(r.get("series", 0)), D["snapshot"]: None,
        })
    return out


# --------------------------------------------------------------- oracle stats
def oracle_analyze(mat: feeds.Matrix):
    """Run the truth oracle once and return (stability_rows, mss_truth_map).

    Rows are per (regime, trigger) recent-window stability (analytic only).
    mss_truth_map gates structure-based BTC entries through the *same* unified
    oracle (per ch9: "تأكيد البنية يأتي من مرجع الصدق العام").
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
    mss_truth = {}
    for reg in (C.REGIME_BULL, C.REGIME_BEAR, C.REGIME_CHOP):
        mss_truth[reg] = oracle.truthful(reg, "MSS")
    return rows, mss_truth


def oracle_stats(mat: feeds.Matrix) -> list[dict]:
    rows, _ = oracle_analyze(mat)
    return rows


def regime_segment_summary(mat: feeds.Matrix) -> list[dict]:
    from collections import Counter
    cnt = Counter(mat.regime.tolist())
    return [{"regime": r, "bars": cnt[r]} for r in cnt]


# ------------------------------------------------------------------ research
def run_research(symbols=None, on_progress=None) -> dict:
    """Full research pass over the symbol set. Returns a results structure and
    writes CSV + report under the output dir."""
    symbols = symbols or C.SYMBOLS
    matrices = feeds.load_all(symbols)
    avail = list(matrices.keys())
    if not avail:
        raise RuntimeError(
            "لا توجد بيانات تاريخية في أرشيف العملات "
            f"({C.ARCHIVE_DIR}). ضع ملفات *_1m.parquet ثم أعد التشغيل."
        )
    all_recs: list[dict] = []
    lean = {}
    oracle_rows = []                 # analytic stability per symbol
    mss_truth_map = {}               # unified-oracle MSS truth per symbol
    regime_rows = []
    # We drive progress from total bars of the matrices we were able to load.
    total_bars = sum(m.n for m in matrices.values()) or 1
    done_bars = 0
    for s in avail:
        m = matrices[s]
        recs = replay_directional(m)
        all_recs.extend(recs)
        grid_u = replay_grid(m)
        all_recs.extend(grid_u)
        lean[s] = m.df[["open", "high", "low", "close", "atr14", "mss"]]
        mss_rows, mss_truth = oracle_analyze(m)   # one truth-labeling pass
        mss_truth_map[s] = mss_truth
        for row in mss_rows:
            row["symbol"] = s
            oracle_rows.append(row)
        for row in regime_segment_summary(m):
            row["symbol"] = s
            regime_rows.append(row)
        done_bars += m.n
        if on_progress:
            on_progress(done_bars / total_bars)
        log.info("symbol %s: %d directional + %d grid units", s, len(recs), len(grid_u))
        # free the heavy matrix but keep the lean copy for the BTC pass
        del matrices[s]
        import gc
        gc.collect()

    # BTC lead-lag cross-coin pass (fed from the unified Oracle)
    from . import btc_leadlag
    btc_pass = btc_leadlag.run_btc_pass(lean, mss_truth_map)
    all_recs.extend(btc_records_from_pass(btc_pass))
    del lean

    result = build_result(all_recs)
    _write_csv(result["records"])
    _write_report(result)
    _write_stability(oracle_rows, regime_rows)
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
    return {
        "records": all_recs,
        "counts": {
            C.CAT_DIRECTIONAL: len(dir_recs),
            C.CAT_GRID: len(grid_recs),
            C.CAT_BTC: len(btc_recs),
        },
        "directional": summarize_category(dir_recs),
        "directional_by_condition": by_condition(dir_recs),
        "grid": summarize_category(grid_recs),
        "btc": summarize_category(btc_recs),
        "grid_cycles": sum(r[D["cycles"]] for r in grid_recs),
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
    lines = []
    lines.append("=" * 44)
    lines.append("NOVA_V8 — تقرير نتائج البحث (تقرير الحالة)")
    lines.append("=" * 44)

    d = result["directional"]
    lines.append("\n[1] 📊 التقرير العام (التداول الاتجاهي):")
    lines.append(f"    عدد الصفقات الكلي  : {d['total']}")
    lines.append(f"    🟢 نسبة الربح        : {d['win_pct']:.1f}%")
    lines.append(f"    🟥 نسبة الخسارة     : {d['lose_pct']:.1f}%")
    lines.append(f"    💵 إجمالي المكاسب    : {d['pnl_usd']:.2f}$")
    lines.append(f"    ✅ نسبة النجاح       : {d['win_pct']:.1f}%")
    if d["total"]:
        lines.append("")
        lines.append("    — تفصيل حسب (الحالة، الزناد):")
        for (regime, trig), s in result["directional_by_condition"].items():
            lines.append(f"      [{regime} | {trig}] {_pct_line('', s)}")

    g = result["grid"]
    lines.append("\n[2] 🟦 قسم الشبكة (Grid):")
    lines.append(f"    عدد الشبكات المغلقة : {g['total']}")
    lines.append(f"    نجحت بنسبة          : {g['win_pct']:.1f}%")
    lines.append(f"    صافي الشبكات        : {g['pnl_usd']:.2f}$")
    lines.append(f"    إجمالي دورات الحصاد : {result['grid_cycles']}")

    b = result["btc"]
    lines.append("\n[3] 🟧 قسم تابعي البيتكوين (BTC):")
    lines.append(f"    عدد الصفقات         : {b['total']}")
    lines.append(f"    نسبة النجاح         : {b['win_pct']:.1f}%")
    lines.append(f"    صافي                : {b['pnl_usd']:.2f}$")

    lines.append("\n" + "=" * 44)
    return "\n".join(lines)


def _write_report(result: dict) -> None:
    C.REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    C.REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    log.info("report -> %s", C.REPORT_PATH)


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
