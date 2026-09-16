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
from .execution import Position, ExitEngine, settle_directional
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
}
CSV_COLUMNS = ["category", "kind", "symbol", "regime", "trigger", "side",
               "entry_bar", "exit_bar", "bars_held", "net_frac", "pnl_usd",
               "reason", "cycles", "success"]


def _allowed(trigger: str) -> bool:
    cfg = C.ENABLE_TRIGGERS
    if cfg == "all":
        return True
    return trigger in {t.strip() for t in cfg.split(",") if t.strip()}


def replay_directional(mat: feeds.Matrix) -> list[dict]:
    """Directional trigger trades with the ATR exit engine over one symbol."""
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
    pending_side, pending_trig = 0, None

    for i in range(1, n):
        r_open, r_hi, r_lo, r_close = (float(o[i]), float(h[i]),
                                       float(l[i]), float(c[i]))
        reg_cur = regA[i]

        # ---- 1) open from a signal that closed on bar i-1 (causal) ----
        if pos is None and pending_side != 0:
            reg_decision = regA[i - 1] if regA[i - 1] else C.REGIME_CHOP
            # direction follows the market state: long in bull, short in bear
            side = int(pending_side)
            allowed_dir = ((side == 1 and reg_decision == C.REGIME_BULL)
                           or (side == -1 and reg_decision == C.REGIME_BEAR))
            if allowed_dir and _allowed(str(pending_trig)):
                # use previous-bar info only; fill at this bar's open
                pa = atr[i - 1]
                pc = c[i - 1]
                if (pa is not None and math.isfinite(float(pa))
                        and math.isfinite(float(pc)) and pc > 0):
                    atr_pct = float(pa) / float(pc)
                    if atr_pct > 0 and r_open > 0:
                        pos = Position(symbol=mat.symbol, side=side,
                                       entry=r_open, entry_px=r_open,
                                       atr_pct=atr_pct, trigger=str(pending_trig),
                                       regime=str(reg_decision),
                                       notional=C.NOTIONAL_BASE, entry_bar=i)
                        eng.arm(pos)
            pending_side, pending_trig = 0, None

        # ---- 2) manage the open position through bar i ----
        if pos is not None:
            res = eng.update(pos, r_open, r_hi, r_lo, i, str(reg_cur), r_close)
            if res:
                reason, fill_px = res
                net = settle_directional(pos, fill_px)
                recs.append(_dir_rec(pos, fill_px, net, reason, i))
                pos = None

        # ---- 3) remember this bar's signal for the next open ----
        pending_side = int(sideA[i])
        pending_trig = trigA[i]

    # close any still-open position at the last close
    if pos is not None:
        last_px = float(c[n - 1])
        net = settle_directional(pos, last_px)
        recs.append(_dir_rec(pos, last_px, net, ExitEngine.TIME, n - 1))
    return recs


def _dir_rec(pos: Position, exit_px: float, net: float, reason: str,
             exit_bar: int) -> dict:
    return {
        D["category"]: C.CAT_DIRECTIONAL, D["kind"]: "dir",
        D["symbol"]: pos.symbol, D["regime"]: pos.regime,
        D["trigger"]: pos.trigger, D["side"]: pos.side,
        D["entry_bar"]: pos.entry_bar, D["exit_bar"]: exit_bar,
        D["bars_held"]: exit_bar - pos.entry_bar,
        D["net_frac"]: net, D["pnl_usd"]: net * pos.notional,
        D["reason"]: reason, D["cycles"]: 0,
        D["success"]: bool(net > 0),
    }


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
        })
    return out


# --------------------------------------------------------------- oracle stats
def oracle_stats(mat: feeds.Matrix) -> list[dict]:
    """Analytic stability per (regime, trigger) — NOT used to gate trades."""
    oracle = TruthOracle()
    run_truth_labeling(mat.df, mat.side, mat.trig, mat.regime, oracle)
    oracle.finalize()
    rows = []
    for k, ratio in sorted(oracle.truth_ratio.items(), key=lambda kv: -kv[1]):
        regime, trig = k
        rows.append({"regime": regime, "trigger": trig, "stability": ratio,
                     "samples": oracle._credits[k][1]})
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
        lean[s] = m.df[["close", "atr14", "mss"]]
        for row in oracle_stats(m):
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

    # BTC lead-lag cross-coin pass
    from . import btc_leadlag
    btc_pass = btc_leadlag.run_btc_pass(lean)
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
    if not records:
        pd.DataFrame(columns=CSV_COLUMNS).to_csv(C.RESULT_PATH, index=False)
        return
    frame = pd.DataFrame(records)
    for col in CSV_COLUMNS:
        if col not in frame.columns:
            frame[col] = 0
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
