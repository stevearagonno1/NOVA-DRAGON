#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0067 — المسح على الاختيار (36 نسخة: M × C × T)، الاختيار بدرجة الهضبة على المحفظة المشتركة، Walk-Forward (8 نوافذ،
اختيار من الجزء الأول فقط)، ثم الحكم للنسخة المثبَّتة والمرجع L0064: دفاتر مستقلة ومحفظة مشتركة (13,000$ و5,000$ حساسية)،
الكلفتان، 1000 دفتر عشوائي × A/B، الاحتفاظ، تسرّب المستقبل، تقرير كل عملة، الاقتصاد، البوابات الخمس عشرة.
    python3 history/hyp_lab/run_l0067_measure.py pass1
    python3 history/hyp_lab/run_l0067_measure.py pass2
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import pathlib
import platform
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path("/home/user/work")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "history" / "hyp_lab"))
sys.path.insert(0, str(ROOT / "history" / "hyp_lab" / "l0067_replication_b"))  # التكرار المستقل (ب) يسبق ملفات التنفيذ الأول
import cycle_engine67 as CE  # noqa: E402
import run_l0067_match as MT  # noqa: E402  (frames, window_view, RECS, FULL16)
import run_l0065_measure as M65  # noqa: E402  (monthly_pnl)
import run_l0064_measure as Y  # noqa: E402  (evaluate_raw, make_book, X, M)

X, M = Y.X, Y.M
OUT = MT.OUT
(OUT / "samples").mkdir(exist_ok=True)
(OUT / "walkforward").mkdir(exist_ok=True)
BOOKS_DIR = pathlib.Path.home() / ".cache" / "l0067_books"
BOOKS_DIR.mkdir(parents=True, exist_ok=True)
Y.SEED_BASE = 67
FULL16 = MT.FULL16
MEMES = ("DOGEUSDT", "SHIBUSDT", "PEPEUSDT")
TARGET13 = tuple(s for s in FULL16 if s not in MEMES)
COST, COST_130 = 0.00115, 0.00130
POOL, POOL_SENS, CAP = 13000.0, 5000.0, 1000.0
MARKETS, TLIMITS, CSETS = ("M0", "M1", "M2"), ("none", "90", "180", "365"), ("C0", "C1", "C2")
N_BOOKS = 1000
T0 = pd.Timestamp("2021-09-01", tz="UTC")
CUT = pd.Timestamp("2024-01-01", tz="UTC")
END = pd.Timestamp("2026-08-31", tz="UTC")
WF = {"W1": ("2022-09-01", "2023-03-01"), "W2": ("2023-03-01", "2023-09-01"), "W3": ("2023-09-01", "2024-03-01"), "W4": ("2024-03-01", "2024-09-01"),
      "W5": ("2024-09-01", "2025-03-01"), "W6": ("2025-03-01", "2025-09-01"), "W7": ("2025-09-01", "2026-03-01"), "W8": ("2026-03-01", "2026-08-31")}
ELIG = {"min_cycles": 20, "max_dd_pct": 35.0, "max_uw_days": 540}
GATES = {"max_dd_pct": 35.0, "max_uw_days": 540, "wf_max_dd_pct": 50.0, "wf_max_uw_days": 720, "top_share_pct": 35.0, "wf_min_pos_share": 0.60,
         "hold_tolerance_pct_of_peak": 10.0, "max_best_month_share": 0.40, "max_best_window_share": 0.50}
L64 = {"SEL": {"net": 113.22, "cycles": 92}, "JUD": {"net": 1314.38, "cycles": 97, "dd": -743.95, "underwater_days": 291.0}}
TRUNC_DATES = ("2022-09-01", "2023-06-01", "2025-03-01")
TRUNC_COINS = ("BTCUSDT", "ETHUSDT", "ATOMUSDT", "XLMUSDT")
H4 = {sym: pd.read_parquet(MT.FRAMES / f"{sym}_4h.parquet") for sym in FULL16}
REC = {sym: json.loads((MT.RECS / f"{sym}.json").read_text(encoding="utf-8")) for sym in FULL16}


class Win:
    """نافذة عامة على شبكة 4س (تعميم X.Window لأي حدّين)."""

    def __init__(self, name: str, s, e):
        self.name = name
        self.s, self.e = M.ts(s), M.ts(e)
        self.grid = pd.date_range(self.s, self.e, freq="4h", tz="UTC", inclusive="left")
        self.n = len(self.grid)
        self.close = {sym: H4[sym]["close"].reindex(self.grid).ffill().to_numpy(float) for sym in FULL16}
        self.years = (self.e - self.s).days / 365.25

    def gi(self, t) -> int:
        k = (pd.Timestamp(t) - self.s) / pd.Timedelta(hours=4)
        return int(k)


def vkey(m: str, t: str) -> str:
    return f"{m}_{t}"


def rows_version(coins, m: str, t: str, w: Win) -> list[dict]:
    out = []
    for sym in coins:
        out.extend(MT.window_view(REC[sym][vkey(m, t)], H4[sym], w.s, w.e, COST))
    return out


def shared_portfolio(rows: list[dict], pool: float, cap: float) -> tuple[list[dict], dict]:
    """محفظة مشتركة: تخفيض تناسبي عند نقص النقد، سقف للعملة، المخارج قبل الدخولات عند الطابع نفسه."""
    rows = [dict(r) for r in rows]
    for i, r in enumerate(rows):
        r["_id"] = i; r["req_notional"] = r["notional_usd"]; r["exec_notional"] = 0.0
    events = []
    for r in rows:
        events.append((pd.Timestamp(r["entry_time"]), 1, r["_id"]))
        events.append((pd.Timestamp(r["exit_time"]), 0, r["_id"]))
    events.sort(key=lambda x: (x[0], x[1]))
    cash = pool; coin_open = {}; min_cash = pool; n_reduced = n_rejected = 0; log = []
    i = 0
    while i < len(events):
        t = events[i][0]
        j = i
        while j < len(events) and events[j][0] == t:
            j += 1
        batch = events[i:j]
        for _, kind, rid in batch:
            if kind == 0:
                r = rows[rid]
                if r["exec_notional"] > 0:
                    frac = r["exec_notional"] / r["req_notional"]
                    cash += r["exec_notional"] + r["pnl_usd"] * frac
                    coin_open[r["symbol"]] = coin_open.get(r["symbol"], 0.0) - r["exec_notional"]
        entries = [rows[rid] for _, kind, rid in batch if kind == 1]
        if entries:
            wants = []
            for r in entries:
                room = max(0.0, cap - coin_open.get(r["symbol"], 0.0))
                wants.append(min(r["req_notional"], room))
            total = sum(wants)
            scale = 1.0 if total <= cash + 1e-9 else (cash / total if total > 0 else 0.0)
            for r, want in zip(entries, wants):
                ex = want * scale
                r["exec_notional"] = ex
                cash -= ex
                coin_open[r["symbol"]] = coin_open.get(r["symbol"], 0.0) + ex
                if ex < r["req_notional"] - 1e-9:
                    if ex <= 1e-9:
                        n_rejected += 1
                    else:
                        n_reduced += 1
                    if len(log) < 50:
                        log.append({"time": t.isoformat(), "symbol": r["symbol"], "requested": round(r["req_notional"], 2), "executed": round(ex, 2), "cash_before": round(cash + ex, 2)})
            min_cash = min(min_cash, cash)
        i = j
    out = []
    for r in rows:
        if r["exec_notional"] <= 1e-9:
            continue
        q = dict(r)
        frac = r["exec_notional"] / r["req_notional"]
        q["notional_usd"] = r["exec_notional"]; q["pnl_usd"] = r["pnl_usd"] * frac
        for k in ("_id", "req_notional", "exec_notional"):
            q.pop(k, None)
        out.append(q)
    return out, {"pool": pool, "min_cash": round(min_cash, 2), "n_reduced": n_reduced, "n_rejected": n_rejected, "log": log,
                 "requested_total": round(sum(r["req_notional"] for r in rows), 2), "executed_total": round(sum(r["exec_notional"] for r in rows), 2)}


def metrics(rows: list[dict], w: Win, coins, pool: float | None = None) -> dict:
    if not rows:
        return {"empty": True, "net115": 0.0, "net130": 0.0, "cycles": 0, "slices": 0, "peak": 0.0, "avg_dep": 0.0, "ret_pct_peak": None, "ret_pct_pool": None, "dd": 0.0,
                "dd_pct_peak": None, "dd_pct_pool": None, "underwater_days": 0.0, "avg_slice": None, "median_slice": None, "win_rate_pct": None, "top_coin": None, "top_share_pct": None,
                "best_slice_share": None, "best_month_share": None, "per_coin": {}, "monthly": None, "cycles_per_year": 0.0, "years": round(w.years, 3), "annualized_net": 0.0,
                "mean_cycle_days": None, "time_in_market_pct": 0.0, "annual_trading_cost": 0.0, "reasons": {}, "symbols_traded": 0}
    ev = Y.evaluate_raw(rows, w)
    pn = np.array([r["pnl_usd"] for r in rows])
    cyc = len({(r["symbol"], r.get("cycle", 0), r["entry_bar"] if r.get("cycle") is None else 0) for r in rows}) if all("cycle" in r for r in rows) else len(M.cycles(rows))
    cyc = len({(r["symbol"], r["cycle"]) for r in rows})
    mp = M65.monthly_pnl(rows, w)
    per = {k: round(v, 2) for k, v in sorted(ev["per_coin"].items(), key=lambda x: -x[1])}
    top = max(per, key=per.get)
    net = ev["net115"]
    durs = {}
    for r in rows:
        k = (r["symbol"], r["cycle"]); a, b = durs.get(k, (r["entry_bar"], r["exit_bar"]))
        durs[k] = (min(a, r["entry_bar"]), max(b, r["exit_bar"]))
    mean_days = float(np.mean([b - a for a, b in durs.values()])) * 4 / 24 if durs else None
    reasons = {}
    for r in rows:
        reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    gi0 = np.array([w.gi(r["entry_time"]) for r in rows]); gi1 = np.array([w.gi(r["exit_time"]) for r in rows])
    dep = np.zeros(w.n + 1); np.add.at(dep, gi0, 1); np.add.at(dep, gi1, -1); dep = np.cumsum(dep)[: w.n]
    return {"empty": False, "net115": round(net, 2), "net130": round(ev["net130"], 2), "cycles": cyc, "slices": len(rows), "peak": round(ev["peak"], 2),
            "avg_dep": round(ev["avg_dep"], 2), "ret_pct_peak": round(100 * net / ev["peak"], 3) if ev["peak"] > 0 else None,
            "ret_pct_pool": round(100 * net / pool, 3) if pool else None, "dd": round(ev["dd"], 2),
            "dd_pct_peak": round(100 * ev["dd"] / ev["peak"], 2) if ev["peak"] > 0 else None, "dd_pct_pool": round(100 * ev["dd"] / pool, 2) if pool else None,
            "underwater_days": round(ev["underwater_days"], 1), "avg_slice": round(float(pn.mean()), 2), "median_slice": round(float(np.median(pn)), 2),
            "win_rate_pct": round(100 * float((pn > 0).mean()), 1), "top_coin": top, "top_share_pct": round(100 * per[top] / net, 1) if net > 0 else None,
            "best_slice_share": round(float(pn.max() / net), 3) if net > 0 else None,
            "best_month_share": round(max(mp["series"].values()) / net, 3) if net > 0 else None, "per_coin": per, "monthly": mp,
            "cycles_per_year": round(cyc / w.years, 1), "years": round(w.years, 3), "annualized_net": round(net / w.years, 2),
            "mean_cycle_days": round(mean_days, 1) if mean_days else None, "time_in_market_pct": round(100 * float((dep > 0).mean()), 1),
            "annual_trading_cost": round(sum(r["notional_usd"] * 2 * COST for r in rows) / w.years, 2), "reasons": reasons,
            "symbols_traded": len(per)}


def coin_sets(w_is: Win) -> dict:
    """C1 (أهلية بيانات) وC2 (اختيار تاريخي مقفل) على المرجع M0/none داخل الجزء الأول فقط."""
    c1, c2, why = [], [], {}
    for sym in TARGET13:
        sub = H4[sym][(H4[sym].index >= w_is.s) & (H4[sym].index < w_is.e)]
        span = (sub.index[-1] - sub.index[0]).days if len(sub) else 0
        rows = MT.window_view(REC[sym]["M0_none"], H4[sym], w_is.s, w_is.e, COST)
        cyc = len({r["cycle"] for r in rows})
        reasons = []
        if span < 365:
            reasons.append(f"بيانات {span} يومًا < 365")
        if cyc < 4:
            reasons.append(f"دورات {cyc} < 4")
        if not reasons:
            c1.append(sym)
            pn = np.array([r["pnl_usd"] for r in rows]); net = float(pn.sum())
            ev = Y.evaluate_raw(rows, w_is); mp = M65.monthly_pnl(rows, w_is)
            checks = {"net>0": net > 0, "avg>0": float(pn.mean()) > 0, "dd<=35%": ev["dd"] >= -0.35 * CE.BOOK_USD,
                      "best_trade<50%": (net > 0 and float(pn.max()) / net < 0.5), "best_month<60%": (net > 0 and max(mp["series"].values()) / net < 0.6)}
            if all(checks.values()):
                c2.append(sym)
            why[sym] = {"C1": True, "C2": all(checks.values()), "span_days": span, "cycles_is": cyc, "net_is": round(net, 2), "checks": checks}
        else:
            why[sym] = {"C1": False, "C2": False, "span_days": span, "cycles_is": cyc, "reasons": reasons}
    return {"C0": list(TARGET13), "C1": c1, "C2": c2, "why": why}


def evaluate_versions(w: Win, csets: dict, pool: float = POOL) -> dict:
    out = {}
    for m in MARKETS:
        for t in TLIMITS:
            for c in CSETS:
                rows = rows_version(csets[c], m, t, w)
                ind = metrics(rows, w, csets[c])
                srows, sstat = shared_portfolio(rows, pool, CAP)
                sh = metrics(srows, w, csets[c], pool)
                sh["shared"] = {k: v for k, v in sstat.items() if k != "log"}
                out[f"{m}_{c}_{t}"] = {"independent": ind, "shared": sh}
    return out


def select_version(vers: dict) -> dict:
    """المؤهَّل على المحفظة المشتركة ثم درجة الهضبة (جيران T وM)."""
    def elig(v):
        s = v["shared"]
        return (not s.get("empty")) and s["net115"] > 0 and s["cycles"] >= ELIG["min_cycles"] and (s["dd_pct_peak"] or -999) >= -ELIG["max_dd_pct"] \
            and s["underwater_days"] <= ELIG["max_uw_days"] and (s["avg_slice"] or 0) > 0
    def ret(k):
        s = vers[k]["shared"]
        return s["ret_pct_peak"] if (not s.get("empty") and s["ret_pct_peak"] is not None) else -999.0
    plateau = {}
    for k in vers:
        m, c, t = k.split("_")
        mi, ti = MARKETS.index(m), TLIMITS.index(t)
        ks = [k]
        for d in (-1, 1):
            if 0 <= mi + d < len(MARKETS):
                ks.append(f"{MARKETS[mi + d]}_{c}_{t}")
            if 0 <= ti + d < len(TLIMITS):
                ks.append(f"{m}_{c}_{TLIMITS[ti + d]}")
        plateau[k] = float(np.mean([ret(x) for x in ks]))
    eligible = [k for k in vers if elig(vers[k])]
    if eligible:
        chosen = max(eligible, key=lambda k: (plateau[k], vers[k]["shared"]["cycles"]))
        relaxed = False
    else:
        chosen, relaxed = "M0_C0_none", True
    single = max(vers, key=lambda k: ret(k))
    return {"chosen": chosen, "relaxed_to_reference": relaxed, "n_eligible": len(eligible), "eligible": eligible, "plateau": plateau,
            "single_peak": single, "chosen_plateau": plateau[chosen], "chosen_ret": ret(chosen),
            "neighbors_of_chosen": {x: ret(x) for x in vers if x != chosen and _is_neighbor(x, chosen)}}


def _is_neighbor(a: str, b: str) -> bool:
    ma, ca, ta = a.split("_"); mb, cb, tb = b.split("_")
    if ca != cb:
        return False
    dm = abs(MARKETS.index(ma) - MARKETS.index(mb)); dt = abs(TLIMITS.index(ta) - TLIMITS.index(tb))
    return (dm == 1 and dt == 0) or (dm == 0 and dt == 1)


def wilson(p: float, n: int, z: float = 1.96) -> tuple:
    if n == 0:
        return (None, None)
    d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(100 * (c - h), 1), round(100 * (c + h), 1))


def leakage(m: str, t: str) -> dict:
    btc_ok_full = CE.btc_market_ok(MT.frames("BTCUSDT")[1])
    tl = None if t == "none" else int(t)
    out = {}
    for sym in TRUNC_COINS:
        h4, d1 = MT.frames(sym)
        full = CE.run(CE.CoinContext(sym, h4, d1, btc_ok_full), m, tl)
        ent = {}
        for T in TRUNC_DATES:
            Tt = pd.Timestamp(T, tz="UTC")
            btc_ok_tr = CE.btc_market_ok(MT.frames("BTCUSDT", Tt)[1])
            h4t, d1t = MT.frames(sym, Tt)
            ctx_t = CE.CoinContext(sym, h4t, d1t, btc_ok_tr)
            tr = CE.run(ctx_t, m, tl)
            keyf = lambda r: (r["entry_time"], r["stage"], round(r["entry_px"], 8), round(r["notional_usd"], 4))
            before = [r for r in full if pd.Timestamp(r["entry_time"]) < Tt]
            trk = {(r["entry_time"], r["stage"]): r for r in tr}
            closed = [r for r in before if pd.Timestamp(r["exit_time"]) < Tt]
            ctx_f = CE.CoinContext(sym, h4, d1, btc_ok_full)
            nn = ctx_t.n
            ent[T] = {"same_entries_before_T": sorted(map(keyf, tr)) == sorted(map(keyf, before)),
                      "same_exits_closed_before_T": all((k := (r["entry_time"], r["stage"])) in trk and trk[k]["exit_time"] == r["exit_time"] and trk[k]["reason"] == r["reason"] and abs(trk[k]["exit_px"] - r["exit_px"]) < 1e-9 for r in closed),
                      "open_at_T_closed_as_end": all(trk.get((r["entry_time"], r["stage"]), {}).get("reason") == "نهاية-العينة" for r in before if pd.Timestamp(r["exit_time"]) >= Tt),
                      "gates_equal_common_bars": bool(np.array_equal(ctx_t.bear_ok, ctx_f.bear_ok[:nn]) and np.array_equal(ctx_t.market_ok[m], ctx_f.market_ok[m][:nn]) and np.array_equal(ctx_t.entry_signal, ctx_f.entry_signal[:nn])),
                      "n_before_T": len(before)}
        out[sym] = ent
    out["ALL_PASSED"] = all(all(v.values()) if False else (v["same_entries_before_T"] and v["same_exits_closed_before_T"] and v["open_at_T_closed_as_end"] and v["gates_equal_common_bars"]) for sym in TRUNC_COINS for v in out[sym].values())
    return out


def save_rows(name: str, rows: list[dict]) -> pathlib.Path:
    M.OUT = OUT
    return M.save_trades(name, rows)


def main(pass_tag: str) -> int:
    rule = json.loads((OUT / "acceptance_rule_l0067.json").read_text(encoding="utf-8"))
    match = json.loads((OUT / "match_report.json").read_text(encoding="utf-8"))
    if not match["MATCH_GATE_PASSED"]:
        raise SystemExit("بوابة المطابقة لم تنجح")
    W_SEL, W_JUD, W_FULL = Win("SEL", T0, CUT), Win("JUD", CUT, END), Win("FULL", T0, END)
    results = {"pass": pass_tag, "match_gate": match["files"], "engine_sha256": match["engine_sha256"]}

    # ───── 1) المسح على الاختيار ─────
    print("══ المسح على الاختيار (36 نسخة) ══", flush=True)
    csets_sel = coin_sets(W_SEL)
    vers_sel = evaluate_versions(W_SEL, csets_sel)
    sel = select_version(vers_sel)
    chosen = sel["chosen"]; cm, cc, ct = chosen.split("_")
    results["coin_sets_SEL"] = csets_sel
    results["sweep_SEL"] = {k: {"independent": {kk: v["independent"].get(kk) for kk in ("net115", "cycles", "peak", "ret_pct_peak", "dd_pct_peak", "underwater_days", "avg_slice", "top_share_pct")},
                                "shared": {kk: v["shared"].get(kk) for kk in ("net115", "net130", "cycles", "peak", "ret_pct_peak", "ret_pct_pool", "dd_pct_peak", "underwater_days", "avg_slice", "top_share_pct", "shared")}}
                            for k, v in vers_sel.items()}
    results["selection"] = sel
    nets = [v["shared"]["net115"] for v in vers_sel.values()]
    results["sweep_summary"] = {"n_versions": len(vers_sel), "share_positive_shared": round(float(np.mean([x > 0 for x in nets])), 3), "median_net_shared": round(float(np.median(nets)), 2),
                                "best_net_shared": round(max(nets), 2), "by_M": {m: round(float(np.median([vers_sel[k]["shared"]["net115"] for k in vers_sel if k.startswith(m + "_")])), 2) for m in MARKETS},
                                "by_C": {c: round(float(np.median([vers_sel[k]["shared"]["net115"] for k in vers_sel if k.split("_")[1] == c])), 2) for c in CSETS},
                                "by_T": {t: round(float(np.median([vers_sel[k]["shared"]["net115"] for k in vers_sel if k.split("_")[2] == t])), 2) for t in TLIMITS},
                                "best_by_M": {m: max([k for k in vers_sel if k.startswith(m + "_")], key=lambda k: vers_sel[k]["shared"]["net115"]) for m in MARKETS},
                                "best_by_C": {c: max([k for k in vers_sel if k.split("_")[1] == c], key=lambda k: vers_sel[k]["shared"]["net115"]) for c in CSETS},
                                "best_by_T": {t: max([k for k in vers_sel if k.split("_")[2] == t], key=lambda k: vers_sel[k]["shared"]["net115"]) for t in TLIMITS},
                                "independent_vs_shared_diff": {k: round(v["independent"]["net115"] - v["shared"]["net115"], 2) for k, v in vers_sel.items() if abs(v["independent"]["net115"] - v["shared"]["net115"]) > 0.005}}
    print(f"  المثبَّت: {chosen} (هضبة {sel['chosen_plateau']:.2f}%، مؤهَّل {sel['n_eligible']}/36، القمة المنفردة {sel['single_peak']}) · C1={csets_sel['C1']} C2={csets_sel['C2']}", flush=True)
    print(f"  اختيار المثبَّت (مشترك): {vers_sel[chosen]['shared']['net115']}$ · المرجع M0_C0_none: {vers_sel['M0_C0_none']['shared']['net115']}$", flush=True)

    # ───── 2) Walk-Forward ─────
    print("══ Walk-Forward (8 نوافذ) ══", flush=True)
    wf = {}
    for wname, (is_end, oos_end) in WF.items():
        w_is, w_oos = Win(wname + "_IS", T0, is_end), Win(wname + "_OOS", is_end, oos_end)
        cs = coin_sets(w_is)
        vers_is = evaluate_versions(w_is, cs)
        s = select_version(vers_is)
        k = s["chosen"]; m, c, t = k.split("_")
        oos_rows = rows_version(cs[c], m, t, w_oos)
        oos_shared_rows, oos_stat = shared_portfolio(oos_rows, POOL, CAP)
        oos = metrics(oos_shared_rows, w_oos, cs[c], POOL)
        ref_rows, _ = shared_portfolio(rows_version(cs["C0"], "M0", "none", w_oos), POOL, CAP)
        ref = metrics(ref_rows, w_oos, cs["C0"], POOL)
        main_rows, _ = shared_portfolio(rows_version(cs[cc] if cc != "C0" else cs["C0"], cm, ct, w_oos), POOL, CAP)
        mainv = metrics(main_rows, w_oos, cs[cc], POOL)
        wf[wname] = {"is_end": is_end, "oos_end": oos_end, "coin_sets": {"C1": cs["C1"], "C2": cs["C2"]}, "chosen_in_window": k, "n_eligible": s["n_eligible"],
                     "relaxed": s["relaxed_to_reference"], "is_shared_net": vers_is[k]["shared"]["net115"],
                     "oos_chosen": {kk: oos.get(kk) for kk in ("net115", "net130", "cycles", "peak", "ret_pct_peak", "dd", "dd_pct_peak", "underwater_days", "avg_slice", "win_rate_pct", "top_coin", "top_share_pct", "per_coin")},
                     "oos_reference_M0_C0_none": {kk: ref.get(kk) for kk in ("net115", "cycles", "peak", "dd_pct_peak", "underwater_days")},
                     "oos_main_chosen": {kk: mainv.get(kk) for kk in ("net115", "cycles", "peak", "dd_pct_peak", "underwater_days")}, "shared_stat": {kk: v for kk, v in oos_stat.items() if kk != "log"}}
        (OUT / "walkforward" / f"{wname}.json").write_text(json.dumps({"window": wf[wname], "selection": s, "versions_is": {kk: {"shared_net": v["shared"]["net115"], "shared_ret": v["shared"]["ret_pct_peak"], "cycles": v["shared"]["cycles"]} for kk, v in vers_is.items()}}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        print(f"  {wname}: IS→{k} (مؤهَّل {s['n_eligible']}) · OOS صافي={oos['net115']} دورات={oos['cycles']} هبوط={oos['dd_pct_peak']}% تحت القمة={oos['underwater_days']} · المرجع {ref['net115']} · المثبَّت الأساسي {mainv['net115']}", flush=True)
    oos_nets = [wf[w]["oos_chosen"]["net115"] for w in WF]
    ref_nets = [wf[w]["oos_reference_M0_C0_none"]["net115"] for w in WF]
    main_nets = [wf[w]["oos_main_chosen"]["net115"] for w in WF]
    pos_sum = sum(x for x in oos_nets if x > 0)
    results["walkforward"] = {"windows": wf, "n_positive": int(sum(x > 0 for x in oos_nets)), "n_windows": len(oos_nets), "median_oos": round(float(np.median(oos_nets)), 2),
                              "worst": round(min(oos_nets), 2), "best": round(max(oos_nets), 2), "sum": round(sum(oos_nets), 2),
                              "best_window_share_of_positive_sum": round(max(oos_nets) / pos_sum, 3) if pos_sum > 0 else None,
                              "max_dd_pct_any_window": round(min([wf[w]["oos_chosen"]["dd_pct_peak"] or 0 for w in WF]), 2),
                              "max_uw_days_any_window": round(max([wf[w]["oos_chosen"]["underwater_days"] for w in WF]), 1),
                              "reference": {"n_positive": int(sum(x > 0 for x in ref_nets)), "median": round(float(np.median(ref_nets)), 2), "sum": round(sum(ref_nets), 2), "nets": ref_nets},
                              "main_chosen": {"n_positive": int(sum(x > 0 for x in main_nets)), "median": round(float(np.median(main_nets)), 2), "sum": round(sum(main_nets), 2), "nets": main_nets},
                              "chosen_per_window": [wf[w]["chosen_in_window"] for w in WF], "oos_nets": oos_nets}

    # ───── 3) الحكم للنسخة المثبَّتة والمرجع ─────
    print("══ الحكم ══", flush=True)
    coins_c = csets_sel[cc]
    results["strategy"] = {}
    for tag, (m, c, t, coins) in {"chosen": (cm, cc, ct, coins_c), "reference": ("M0", "C0", "none", list(TARGET13))}.items():
        blk = {"version": f"{m}_{c}_{t}", "coins": coins}
        for wname, w in (("SEL", W_SEL), ("JUD", W_JUD), ("FULL", W_FULL)):
            rows = rows_version(coins, m, t, w)
            ind = metrics(rows, w, coins)
            sh_rows, sh_stat = shared_portfolio(rows, POOL, CAP); sh = metrics(sh_rows, w, coins, POOL); sh["shared"] = {k: v for k, v in sh_stat.items()}
            s5_rows, s5_stat = shared_portfolio(rows, POOL_SENS, CAP); s5 = metrics(s5_rows, w, coins, POOL_SENS); s5["shared"] = {k: v for k, v in s5_stat.items() if k != "log"}
            blk[wname] = {"independent": ind, "shared_13000": sh, "shared_5000": s5}
            save_rows(f"{tag}_independent_{wname}", rows); save_rows(f"{tag}_shared13000_{wname}", sh_rows)
            print(f"  {tag} {wname}: مستقل={ind['net115']} · مشترك13k={sh['net115']} (مخفَّض {sh_stat['n_reduced']}، مرفوض {sh_stat['n_rejected']}، أدنى نقد {sh_stat['min_cash']}) · مشترك5k={s5['net115']} (مخفَّض {s5_stat['n_reduced']}) "
                  f"· دورات={ind['cycles']} ذروة={ind['peak']} هبوط%={sh['dd_pct_peak']} تحت القمة={sh['underwater_days']} متوسط الصفقة={sh['avg_slice']}", flush=True)
        # الميم/السلة الكاملة للبحث
        rows16 = rows_version(FULL16 if c == "C0" else list(coins) + list(MEMES), m, t, W_JUD)
        blk["FULL16_JUD_independent_net"] = metrics(rows16, W_JUD, FULL16)["net115"]
        results["strategy"][tag] = blk
    ST = results["strategy"]["chosen"]

    # ───── 4) الاحتفاظ ─────
    results["hold"] = {}
    for wname, w in (("SEL", "SEL"), ("JUD", "JUD")):
        peak = ST[wname]["shared_13000"]["peak"]
        _, st_peak = M.buyhold(coins_c, peak, w)
        _, st_pool = M.buyhold(coins_c, POOL, w)
        results["hold"][wname] = {"same_peak": {k: v for k, v in st_peak.items() if k != "spans"}, "pool_13000": {k: v for k, v in st_pool.items() if k != "spans"}}

    # ───── 5) العشوائي (السلة المستهدفة، عملات النسخة المثبَّتة، دفاتر مستقلة ⇒ تسوية إلى ذروة المحفظة المشتركة) ─────
    summaries = {}
    overlap_total = fail_total = 0
    results["books"] = {}
    for design in ("A", "B"):
        for wname, w in (("SEL", W_SEL), ("JUD", W_JUD)):
            base_rows = rows_version(coins_c, cm, ct, w)
            table = X.cycle_table(base_rows)
            Sref = ST[wname]["shared_13000"]
            xw = X.Window(wname)
            print(f"══ عشوائي {design} · {wname} · {N_BOOKS} دفتر ══", flush=True)
            per_book = []
            big = BOOKS_DIR / f"random_books_{design}_{wname}.csv"
            fh = big.open("w", encoding="utf-8-sig", newline=""); wr = csv.writer(fh)
            wr.writerow(["book", "symbol", "entry_time", "exit_time", "entry", "exit", "notional", "pnl", "reason", "stage", "bars_held"])
            for b in range(1, N_BOOKS + 1):
                rows_b, fails = Y.make_book(design, xw, table, coins_c, b)
                fail_total += fails; ov = X.overlap_violations(rows_b); overlap_total += ov
                for r in rows_b:
                    wr.writerow([b, r["symbol"], r["entry_time"], r["exit_time"], r["entry_px"], r["exit_px"], r["notional_usd"], round(float(X.pnl_vec(r["entry_px"], r["exit_px"], r["notional_usd"], COST)), 4), r["reason"], 0, r["bars_held"]])
                if b <= 3:
                    pd.DataFrame([{"symbol": r["symbol"], "entry_time": r["entry_time"], "exit_time": r["exit_time"], "entry": r["entry_px"], "exit": r["exit_px"], "notional": r["notional_usd"],
                                   "pnl": round(float(X.pnl_vec(r["entry_px"], r["exit_px"], r["notional_usd"], COST)), 4), "reason": r["reason"], "stage": 0, "bars_held": r["bars_held"]} for r in rows_b]).to_csv(OUT / "samples" / f"trades_random_{design}_{wname}_book{b}.csv", index=False, encoding="utf-8-sig")
                if not rows_b:
                    continue
                ev = Y.evaluate_raw(rows_b, xw)
                fp = Sref["peak"] / ev["peak"]; fm = Sref["avg_dep"] / ev["avg_dep"]
                rec = {"book": b, "peak_raw": round(ev["peak"], 2), "f_peak": round(fp, 6), "f_mean": round(fm, 6), "net115_raw": round(ev["net115"], 2),
                       "net115_peak": round(ev["net115"] * fp, 2), "net130_peak": round(ev["net130"] * fp, 2), "net115_mean": round(ev["net115"] * fm, 2), "net130_mean": round(ev["net130"] * fm, 2),
                       "dd_peak": round(ev["dd"] * fp, 2), "underwater_days": round(ev["underwater_days"], 1), "overlap_violations": ov, "placement_failures": fails}
                for s_ in coins_c:
                    rec[f"coin_{s_}"] = round(ev["per_coin"].get(s_, 0.0) * fp, 2)
                per_book.append(rec)
                if b % 250 == 0:
                    print(f"    {b}/{N_BOOKS}", flush=True)
            fh.close()
            df = pd.DataFrame(per_book); summaries[(design, wname)] = df
            df.to_csv(OUT / f"books_{design}_{wname}.csv", index=False, encoding="utf-8-sig")
            results.setdefault("determinism", {})[f"sha_random_books_{design}_{wname}"] = hashlib.sha256(big.read_bytes()).hexdigest()[:16]
            blk = {"n_books": int(len(df)), "peak_scaled_to": Sref["peak"], "avgdep_scaled_to": Sref["avg_dep"]}
            for scal in ("peak", "mean"):
                for ct_, sn in (("115", Sref["net115"]), ("130", Sref["net130"])):
                    v = df[f"net{ct_}_{scal}"].to_numpy(); blk[f"net{ct_}_{scal}"] = X.dist(v); blk[f"pct_below_{ct_}_{scal}"] = X.pct_below(v, sn)
            blk["dd_peak"] = X.dist(df.dd_peak.to_numpy()); blk["pct_books_dd_smaller_than_strategy"] = X.pct_below(-df.dd_peak.to_numpy(), -Sref["dd"])
            blk["median_per_coin_peak"] = {s_: round(float(df[f"coin_{s_}"].median()), 2) for s_ in coins_c}
            results["books"][f"{design}_{wname}"] = blk
            print(f"    وسيط(ذروة) {blk['net115_peak']['median']}$ · فوق {100*blk['pct_below_115_peak']:.1f}% | وسيط(متوسط) {blk['net115_mean']['median']}$ · فوق {100*blk['pct_below_115_mean']:.1f}% | الاستراتيجية {Sref['net115']}$", flush=True)
    results["overlap_violations_total"] = overlap_total; results["placement_failures_total"] = fail_total

    # ───── 6) تقرير كل عملة (المرجع والمثبَّت في الاختيار والحكم) ─────
    per_coin = {}
    for sym in TARGET13:
        e = {"in_C1": sym in csets_sel["C1"], "in_C2": sym in csets_sel["C2"], "why": csets_sel["why"].get(sym), "traded_in_chosen": sym in coins_c}
        total_cycles = 0; ok_data = True
        for wname, w in (("SEL", W_SEL), ("JUD", W_JUD)):
            sub = H4[sym][(H4[sym].index >= w.s) & (H4[sym].index < w.e)]
            span = (sub.index[-1] - sub.index[0]).days if len(sub) else 0
            if span < 365:
                ok_data = False
            for vtag, (m, t) in (("reference", ("M0", "none")), ("chosen", (cm, ct))):
                rows = MT.window_view(REC[sym][vkey(m, t)], H4[sym], w.s, w.e, COST)
                if rows:
                    ev = Y.evaluate_raw(rows, w); pn = np.array([r["pnl_usd"] for r in rows]); wins_n = int((pn > 0).sum()); mp = M65.monthly_pnl(rows, w)
                    cyc = len({r["cycle"] for r in rows})
                    e[f"{vtag}_{wname}"] = {"net": round(ev["net115"], 2), "cycles": cyc, "slices": len(rows), "wins": wins_n, "losses": len(rows) - wins_n,
                                            "win_rate_pct": round(100 * wins_n / len(rows), 1), "win_rate_ci95": wilson(wins_n / len(rows), len(rows)),
                                            "avg_slice": round(float(pn.mean()), 2), "median_slice": round(float(np.median(pn)), 2), "best_slice_share": round(float(pn.max() / ev["net115"]), 2) if ev["net115"] > 0 else None,
                                            "dd": round(ev["dd"], 2), "dd_pct_book": round(100 * ev["dd"] / CE.BOOK_USD, 1), "underwater_days": round(ev["underwater_days"], 1),
                                            "winning_months_pct_active": mp["winning_months_pct_active"], "span_days": span}
                    if vtag == "chosen":
                        total_cycles += cyc
                else:
                    e[f"{vtag}_{wname}"] = {"net": 0.0, "cycles": 0, "slices": 0, "wins": 0, "losses": 0, "win_rate_pct": None, "win_rate_ci95": (None, None), "avg_slice": None, "median_slice": None,
                                            "best_slice_share": None, "dd": 0.0, "dd_pct_book": 0.0, "underwater_days": 0.0, "winning_months_pct_active": None, "span_days": span}
        sel_, jud_ = e["chosen_SEL"], e["chosen_JUD"]
        e["share_of_basket_JUD_pct"] = round(100 * jud_["net"] / ST["JUD"]["shared_13000"]["net115"], 1) if (ST["JUD"]["shared_13000"]["net115"] > 0 and sym in coins_c) else None
        e["shared_effect"] = "منفَّذ = مطلوب (القيد لم يُفعَّل)" if ST["JUD"]["shared_13000"]["shared"]["n_reduced"] == 0 else "انظر سجل التخصيص"
        total = sel_["net"] + jud_["net"]
        enough = ok_data and sel_["cycles"] >= 5 and jud_["cycles"] >= 5 and total_cycles >= 10
        if not enough:
            cls = "غير كافية البيانات"
        elif sel_["net"] > 0 and jud_["net"] > 0 and (sel_["best_slice_share"] or 0) < 0.5 and (jud_["best_slice_share"] or 0) < 0.5 and sel_["dd_pct_book"] >= -35 and jud_["dd_pct_book"] >= -35 and sel_["underwater_days"] <= 540 and jud_["underwater_days"] <= 540:
            cls = "مناسبة"
        elif jud_["net"] <= 0 or jud_["dd_pct_book"] < -35 or jud_["underwater_days"] > 540:
            cls = "غير مناسبة"
        elif jud_["net"] > 0 and total > 0:
            cls = "واعدة"
        else:
            cls = "غير مناسبة"
        e["class"] = cls
        per_coin[sym] = e
    results["per_coin"] = per_coin

    # ───── 7) تسرّب المستقبل ─────
    results["leakage"] = leakage(cm, ct)
    print(f"  تسرّب المستقبل ({chosen}): {'✅' if results['leakage']['ALL_PASSED'] else '❌'}", flush=True)

    # ───── 8) البوابات ─────
    s = ST; J, Ssel = s["JUD"]["shared_13000"], s["SEL"]["shared_13000"]
    A = {w: results["books"][f"A_{w}"] for w in ("SEL", "JUD")}
    H = results["hold"]["JUD"]["same_peak"]
    wfres = results["walkforward"]
    g = {}
    g["1"] = Ssel["net115"] > 0 and J["net115"] > 0
    g["2"] = g["1"] and Ssel["net130"] > 0 and J["net130"] > 0
    g["3"] = Ssel["net115"] > A["SEL"]["net115_peak"]["median"] and J["net115"] > A["JUD"]["net115_peak"]["median"]
    g["4"] = J["net115"] >= H["net"] - GATES["hold_tolerance_pct_of_peak"] / 100 * J["peak"]
    g["5"] = (J["avg_slice"] or 0) > 0
    g["6"] = (J["dd_pct_peak"] or -999) >= -GATES["max_dd_pct"] and wfres["max_dd_pct_any_window"] >= -GATES["wf_max_dd_pct"]
    g["7"] = J["underwater_days"] <= GATES["max_uw_days"] and wfres["max_uw_days_any_window"] <= GATES["wf_max_uw_days"]
    g["8"] = (J["top_share_pct"] is not None) and J["top_share_pct"] <= GATES["top_share_pct"]
    g["9"] = wfres["n_positive"] / wfres["n_windows"] >= GATES["wf_min_pos_share"] and wfres["median_oos"] > 0
    g["10"] = (J["best_month_share"] is not None and J["best_month_share"] < GATES["max_best_month_share"]) and (wfres["best_window_share_of_positive_sum"] is not None and wfres["best_window_share_of_positive_sum"] < GATES["max_best_window_share"])
    g["11"] = True
    g["12"] = J["annualized_net"] > 0
    g["13"] = g["2"] and (Ssel["net130"] > A["SEL"]["net130_peak"]["median"] and J["net130"] > A["JUD"]["net130_peak"]["median"])
    g["14"] = results["leakage"]["ALL_PASSED"] and overlap_total == 0
    g["15"] = True
    core = all(g[k] for k in ("1", "2", "3", "5", "9", "12"))
    if not g["14"]:
        verdict = "القياس غير صالح"
    elif all(g[k] for k in ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "12", "13")):
        verdict = "يمرّ"
    elif core:
        verdict = "يطوَّر"
    else:
        verdict = "لا يمرّ"
    ref = results["strategy"]["reference"]
    ref_pass_core = ref["SEL"]["shared_13000"]["net115"] > 0 and ref["JUD"]["shared_13000"]["net115"] > 0
    results["acceptance"] = {"gates": g, "verdict": verdict, "gates_params": GATES,
                             "note_reference": ("المرجع L0064 موجب في الفترتين" if ref_pass_core else "المرجع غير موجب في الفترتين"),
                             "improves_on_reference_JUD": J["net115"] > ref["JUD"]["shared_13000"]["net115"],
                             "economics": {"annualized_net_JUD": J["annualized_net"], "max_monthly_ops_cost": round(J["annualized_net"] / 12, 2), "net_per_1000_per_year_on_pool": round(J["annualized_net"] / POOL * 1000, 2),
                                           "pool_monthly": round(J["annualized_net"] / 12, 2), "annual_trading_cost": J["annual_trading_cost"], "mean_cycle_days": J["mean_cycle_days"], "time_in_market_pct": J["time_in_market_pct"], "avg_dep": J["avg_dep"],
                                           "independent_minus_shared_JUD": round(s["JUD"]["independent"]["net115"] - J["net115"], 2),
                                           "shared_5000_JUD": s["JUD"]["shared_5000"]["net115"], "reduced_orders_5000_JUD": s["JUD"]["shared_5000"]["shared"]["n_reduced"]}}
    print("  البوابات: " + " ".join(f"{k}={'✓' if v else '✗'}" for k, v in g.items()) + f" ⇒ {verdict}", flush=True)

    # ───── 9) الحارس والتتابع والبيئة ─────
    results["guard"] = []
    files = sorted(OUT.glob("trades_chosen_*.csv")) + sorted(OUT.glob("trades_reference_*.csv")) + [BOOKS_DIR / f"random_books_{d}_{w}.csv" for d in ("A", "B") for w in ("SEL", "JUD")] + sorted((OUT / "samples").glob("*.csv"))
    for p in files:
        results["guard"].append(X.guard(p))
    seq = subprocess.run([sys.executable, str(ROOT / "tools" / "position_sequencing_audit.py"), "--dir", str(OUT / "samples"), "--json"], capture_output=True, text=True)
    (OUT / "sequencing_audit_samples.json").write_text(seq.stdout, encoding="utf-8")
    seq2 = subprocess.run([sys.executable, str(ROOT / "tools" / "position_sequencing_audit.py"), "--trades", str(OUT / "trades_chosen_shared13000_FULL.csv"), "--json"], capture_output=True, text=True)
    (OUT / "sequencing_audit_strategy.json").write_text(seq2.stdout, encoding="utf-8")
    import pandas, numpy, pyarrow  # noqa
    results["env"] = {"date": "2026-09-27", "python": platform.python_version(), "pandas": pandas.__version__, "numpy": numpy.__version__, "pyarrow": pyarrow.__version__, "platform": platform.platform(),
                      "base_branch": "arena/l0066-medium-pullback-2026-09-27 @ 76aae73", "n_books": N_BOOKS, "seed_base": Y.SEED_BASE, "cost": {"base": COST, "stress": COST_130, "slippage": "0 — غير مقاس"},
                      "pool": POOL, "pool_sensitivity": POOL_SENS, "cap": CAP,
                      "file_fingerprints": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:16] for p in [ROOT / "history" / "hyp_lab" / "cycle_engine67.py", ROOT / "history" / "hyp_lab" / "run_l0067_match.py", OUT / "acceptance_rule_l0067.json", OUT / "match_report.json"]}}
    text = json.dumps(results, ensure_ascii=False, indent=2, default=str)
    (OUT / f"results_{pass_tag}.json").write_text(text, encoding="utf-8")
    if pass_tag == "pass1":
        (OUT / "results.json").write_text(text, encoding="utf-8")
        (OUT / "env_dump.txt").write_text(json.dumps(results["env"], ensure_ascii=False, indent=2), encoding="utf-8")
        (OUT / "guard_log.json").write_text(json.dumps(results["guard"], ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"اكتمل ({pass_tag}). تداخل={overlap_total} فشل وضع={fail_total} · الحكم: {verdict}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "pass1"))
