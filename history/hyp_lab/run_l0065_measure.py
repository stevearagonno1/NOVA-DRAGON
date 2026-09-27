#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0065 — قياس الإعداد المختار (من المسح على الاختيار) في الاختيار والحكم والدورة الكاملة، على السلّتين،
مع الضوابط (1000 دفتر عشوائي × A/B × نافذتان × سلّتان بتسويتين، والاحتفاظ)، والاقتصاد، وتقرير كل عملة، ومعيار القبول.

    python3 history/hyp_lab/run_l0065_measure.py pass1
    python3 history/hyp_lab/run_l0065_measure.py pass2
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
import pullback_engine as PE  # noqa: E402
import run_l0065_sweep as S  # noqa: E402
import run_l0064_measure as Y  # noqa: E402  (evaluate_raw, make_book, X, M)

X, M = Y.X, Y.M
OUT = S.OUT
(OUT / "samples").mkdir(exist_ok=True)
BOOKS_DIR = pathlib.Path.home() / ".cache" / "l0065_books"
BOOKS_DIR.mkdir(parents=True, exist_ok=True)
Y.SEED_BASE = 65
FULL16, TARGET13, MEMES = S.FULL16, S.TARGET13, S.MEMES
BASKETS = {"FULL16": FULL16, "TARGET13": TARGET13}
WINDOWS = ("SEL", "JUD")
N_BOOKS = 1000
COST, COST_130 = 0.00115, 0.00130
CUT = S.CUT
END = pd.Timestamp("2026-08-31", tz="UTC")
YEARS = {"SEL": (CUT - S.SEL_S).days / 365.25, "JUD": (END - CUT).days / 365.25, "FULL": (END - S.SEL_S).days / 365.25}
L64 = {"SEL": {"net": 113.22, "cycles": 92, "dd": -2467.69, "underwater_days": 640.7, "ret_pct": 3.652, "peak": 3100.0},
       "JUD": {"net": 1314.38, "cycles": 97, "dd": -743.95, "underwater_days": 291.0, "ret_pct": 36.01, "peak": 3650.0},
       "FULL": {"net": 1427.6, "cycles": 189}}
LIMITS = {"max_dd_pct": 25.0, "max_underwater_days": 365, "mult": 1.5}


def cfg_from_key(key: str) -> PE.Config:
    for c in PE.all_configs():
        if c.key == key:
            return c
    raise KeyError(key)


def strategy_rows(cfg: PE.Config) -> dict[str, dict[str, list[dict]]]:
    """لكل عملة: صفوف الاختيار (تشغيل مقطوع) والحكم (تشغيل متصل، دخول ≥ 2024-01-01) والدورة الكاملة."""
    out = {}
    for sym in FULL16:
        rows = {"SEL": [], "JUD": [], "FULL": []}
        ctx_cut = S.load_ctx(sym, CUT)
        if ctx_cut is not None:
            r = PE.run_config(ctx_cut, cfg)
            PE.price_pnl(r, COST)
            rows["SEL"] = r
        ctx_full = S.load_ctx(sym, END + pd.Timedelta(days=1))
        if ctx_full is not None:
            r = PE.run_config(ctx_full, cfg)
            PE.price_pnl(r, COST)
            rows["FULL"] = r
            rows["JUD"] = [q for q in r if pd.Timestamp(q["entry_time"]) >= CUT]
        out[sym] = rows
    return out


def basket_rows(per_sym: dict, coins, w: str) -> list[dict]:
    return [q for s in coins for q in per_sym[s][w]]


def monthly_pnl(rows: list[dict], w: X.Window) -> dict:
    months = pd.period_range(w.s, w.e - pd.Timedelta(hours=4), freq="M")
    ser = pd.Series(0.0, index=months)
    for r in rows:
        ser[pd.Timestamp(r["exit_time"]).to_period("M")] += r["pnl_usd"]
    active = ser[ser != 0.0]
    years = ser.groupby(ser.index.year).sum()
    return {"months_total": int(len(ser)), "months_active": int(len(active)),
            "winning_months_pct_all": round(100 * float((ser > 0).mean()), 1),
            "winning_months_pct_active": round(100 * float((active > 0).mean()), 1) if len(active) else None,
            "monthly_mean": round(float(ser.mean()), 2), "monthly_median": round(float(ser.median()), 2),
            "monthly_min": round(float(ser.min()), 2), "monthly_max": round(float(ser.max()), 2),
            "by_year": {str(k): round(float(v), 2) for k, v in years.items()},
            "series": {str(k): round(float(v), 2) for k, v in ser.items()}}


def strat_block(rows: list[dict], w: X.Window, coins, wname: str) -> dict:
    ev = Y.evaluate_raw(rows, w)
    if ev.get("empty"):
        return {"empty": True, "net115": 0.0, "cycles": 0}
    cyc = M.cycles(rows)
    yrs = YEARS[wname]
    per_coin = {k: round(v, 2) for k, v in sorted(ev["per_coin"].items(), key=lambda x: -x[1])}
    durs = [max(int(r["exit_bar"]) for r in g) - min(int(r["entry_bar"]) for r in g) for g in cyc]
    reasons = {}
    for r in rows:
        reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    win = float(np.mean([r["pnl_usd"] > 0 for r in rows]))
    mp = monthly_pnl(rows, w)
    blk = {"net115": round(ev["net115"], 2), "net130": round(ev["net130"], 2), "cycles": len(cyc), "slices": len(rows),
           "peak": round(ev["peak"], 2), "avg_dep": round(ev["avg_dep"], 2),
           "ret_pct_peak": round(100 * ev["net115"] / ev["peak"], 3), "ret_pct_peak_130": round(100 * ev["net130"] / ev["peak"], 3),
           "ret_pct_avgdep": round(100 * ev["net115"] / ev["avg_dep"], 3),
           "dd": round(ev["dd"], 2), "dd_pct_peak": round(100 * ev["dd"] / ev["peak"], 2), "underwater_days": round(ev["underwater_days"], 1),
           "peak_equity": round(ev["peak_equity"], 2), "years": round(yrs, 3), "cycles_per_year": round(len(cyc) / yrs, 1),
           "annualized_net": round(ev["net115"] / yrs, 2), "monthly_net_mean": round(ev["net115"] / yrs / 12, 2),
           "avg_net_per_coin_traded": round(ev["net115"] / len(per_coin), 2), "symbols_traded": len(per_coin), "coins_in_basket": len(coins),
           "mean_cycle_days": round(float(np.mean(durs)) * 4 / 24, 1) if durs else None,
           "median_cycle_days": round(float(np.median(durs)) * 4 / 24, 1) if durs else None,
           "win_rate_slices_pct": round(100 * win, 1), "avg_slice_pnl": round(ev["net115"] / len(rows), 2),
           "time_in_market_pct": None, "reasons": reasons, "per_coin": per_coin, "monthly": mp}
    # نسبة الشموع التي فيها مركز
    gi0 = np.array([w.gi(r["entry_time"]) for r in rows]); gi1 = np.array([w.gi(r["exit_time"]) for r in rows])
    dep = np.zeros(w.n + 1); np.add.at(dep, gi0, 1); np.add.at(dep, gi1, -1); dep = np.cumsum(dep)[: w.n]
    blk["time_in_market_pct"] = round(100 * float((dep > 0).mean()), 1)
    return blk


def per_coin_report(per_sym: dict, wins: dict) -> dict:
    rep = {}
    for sym in FULL16:
        e = {"meme": sym in MEMES}
        total_cycles = 0
        ok_data = True
        for wname in ("SEL", "JUD"):
            rows = per_sym[sym][wname]
            w = wins[wname]
            fr = M.FR[sym]
            span_days = 0
            sub = fr[(fr.index >= w.s) & (fr.index < w.e)]
            if len(sub):
                span_days = (sub.index[-1] - sub.index[0]).days
            if span_days < 365:
                ok_data = False
            if rows:
                ev = Y.evaluate_raw(rows, w)
                cyc = len(M.cycles(rows))
                total_cycles += cyc
                mp = monthly_pnl(rows, w)
                e[wname] = {"net": round(ev["net115"], 2), "net130": round(ev["net130"], 2), "cycles": cyc, "slices": len(rows),
                            "win_rate_pct": round(100 * float(np.mean([r["pnl_usd"] > 0 for r in rows])), 1),
                            "avg_slice": round(ev["net115"] / len(rows), 2), "dd": round(ev["dd"], 2), "dd_pct_book": round(100 * ev["dd"] / PE.BOOK_USD, 1),
                            "underwater_days": round(ev["underwater_days"], 1), "winning_months_pct_active": mp["winning_months_pct_active"],
                            "months_active": mp["months_active"], "span_days": span_days}
            else:
                e[wname] = {"net": 0.0, "net130": 0.0, "cycles": 0, "slices": 0, "win_rate_pct": None, "avg_slice": None, "dd": 0.0,
                            "dd_pct_book": 0.0, "underwater_days": 0.0, "winning_months_pct_active": None, "months_active": 0, "span_days": span_days}
        sel, jud = e["SEL"], e["JUD"]
        total = sel["net"] + jud["net"]
        if (not ok_data) or total_cycles < 8:
            cls = "غير كافية البيانات"
        elif sel["net"] > 0 and jud["net"] > 0 and sel["dd_pct_book"] >= -30 and jud["dd_pct_book"] >= -30 \
                and (sel["win_rate_pct"] or 0) >= 40 and (jud["win_rate_pct"] or 0) >= 40:
            cls = "مناسبة"
        elif jud["net"] > 0 and total > 0:
            cls = "واعدة"
        else:
            cls = "غير مناسبة"
        e["total_net"] = round(total, 2)
        e["class"] = cls
        rep[sym] = e
    return rep


def save_rows(name: str, rows: list[dict]) -> pathlib.Path:
    M.OUT = OUT
    return M.save_trades(name, rows)


def main(pass_tag: str) -> int:
    rule = json.loads((OUT / "acceptance_rule_l0065.json").read_text(encoding="utf-8"))
    sel = json.loads((OUT / "selection.json").read_text(encoding="utf-8"))
    chosen_key = sel["chosen"]["key"]
    finalists = {e: (f["key"] if f else None) for e, f in sel["finalists_by_exit"].items()}
    wins = {w: X.Window(w) for w in WINDOWS}
    wins["FULL"] = X.Window("FULL")
    results = {"pass": pass_tag, "chosen": chosen_key, "finalists": finalists, "strategy": {}, "hold": {}, "books": {}, "concentration": {},
               "per_coin": {}, "guard": [], "determinism": {}, "L0064_reference_target13": L64}

    # ───── الاستراتيجية: المختار + المرشّحان الآخران ─────
    keys = [chosen_key] + [k for e, k in finalists.items() if k and k != chosen_key]
    per_sym_all = {}
    for key in keys:
        cfg = cfg_from_key(key)
        per_sym = strategy_rows(cfg)
        per_sym_all[key] = per_sym
        results["strategy"][key] = {"config": cfg.__dict__ | {"weights": cfg.weights}}
        for bname, coins in BASKETS.items():
            results["strategy"][key][bname] = {}
            for wname in ("SEL", "JUD", "FULL"):
                rows = basket_rows(per_sym, coins, wname)
                blk = strat_block(rows, wins[wname], coins, wname)
                results["strategy"][key][bname][wname] = blk
                if key == chosen_key:
                    save_rows(f"strategy_{bname}_{wname}", rows)
                elif wname != "FULL":
                    save_rows(f"finalist_{cfg.exit}_{bname}_{wname}", rows)
                if not blk.get("empty"):
                    print(f"  {key} · {bname} · {wname}: صافي={blk['net115']} (0.130: {blk['net130']}) دورات={blk['cycles']} ({blk['cycles_per_year']}/سنة) "
                          f"ذروة={blk['peak']} عائد%={blk['ret_pct_peak']} هبوط={blk['dd']} ({blk['dd_pct_peak']}%) تحت القمة={blk['underwater_days']} يوم "
                          f"ربح/شهر={blk['monthly_net_mean']} أشهر رابحة={blk['monthly']['winning_months_pct_all']}%", flush=True)
            s = results["strategy"][key][bname]
            s["FULL_equals_SEL_plus_JUD"] = abs(s["FULL"]["net115"] - s["SEL"]["net115"] - s["JUD"]["net115"]) < 0.01
    per_sym = per_sym_all[chosen_key]
    results["per_coin"] = per_coin_report(per_sym, wins)
    results["meme_effect"] = {w: {"full16": results["strategy"][chosen_key]["FULL16"][w]["net115"], "target13": results["strategy"][chosen_key]["TARGET13"][w]["net115"],
                                  "meme": round(results["strategy"][chosen_key]["FULL16"][w]["net115"] - results["strategy"][chosen_key]["TARGET13"][w]["net115"], 2)}
                             for w in ("SEL", "JUD", "FULL")}

    # ───── الاحتفاظ بنفس الذروة ─────
    for bname, coins in BASKETS.items():
        results["hold"][bname] = {}
        for wname in WINDOWS:
            peak = results["strategy"][chosen_key][bname][wname]["peak"]
            rows_h, st = M.buyhold(coins, peak, wname)
            results["hold"][bname][wname] = {k: v for k, v in st.items() if k != "spans"}

    # ───── الدفاتر العشوائية للإعداد المختار ─────
    tables = {b: {w: X.cycle_table(basket_rows(per_sym, BASKETS[b], w)) for w in WINDOWS} for b in BASKETS}
    summaries = {}
    overlap_total = fail_total = 0
    for design in ("A", "B"):
        for wname in WINDOWS:
            win = wins[wname]
            Sref = {b: results["strategy"][chosen_key][b][wname] for b in BASKETS}
            print(f"══ عشوائي {design} · {wname} · {N_BOOKS} دفتر ══", flush=True)
            per_book = {b: [] for b in BASKETS}
            big = BOOKS_DIR / f"random_books_FULL16_{design}_{wname}.csv"
            fh = big.open("w", encoding="utf-8-sig", newline=""); wr = csv.writer(fh)
            wr.writerow(["book", "symbol", "entry_time", "exit_time", "entry", "exit", "notional", "pnl", "reason", "stage", "bars_held"])
            for b in range(1, N_BOOKS + 1):
                rows16, fails = Y.make_book(design, win, tables["FULL16"][wname], FULL16, b)
                fail_total += fails
                ov = X.overlap_violations(rows16); overlap_total += ov
                for r in rows16:
                    wr.writerow([b, r["symbol"], r["entry_time"], r["exit_time"], r["entry_px"], r["exit_px"], r["notional_usd"],
                                 round(float(X.pnl_vec(r["entry_px"], r["exit_px"], r["notional_usd"], COST)), 4), r["reason"], 0, r["bars_held"]])
                if b <= 3:
                    pd.DataFrame([{"symbol": r["symbol"], "entry_time": r["entry_time"], "exit_time": r["exit_time"], "entry": r["entry_px"], "exit": r["exit_px"],
                                   "notional": r["notional_usd"], "pnl": round(float(X.pnl_vec(r["entry_px"], r["exit_px"], r["notional_usd"], COST)), 4),
                                   "reason": r["reason"], "stage": 0, "bars_held": r["bars_held"]} for r in rows16]
                                 ).to_csv(OUT / "samples" / f"trades_random_{design}_{wname}_book{b}.csv", index=False, encoding="utf-8-sig")
                for bname, coins in BASKETS.items():
                    rows = rows16 if bname == "FULL16" else [r for r in rows16 if r["symbol"] not in MEMES]
                    if not rows:
                        continue
                    ev = Y.evaluate_raw(rows, win)
                    fp = Sref[bname]["peak"] / ev["peak"]; fm = Sref[bname]["avg_dep"] / ev["avg_dep"]
                    rec = {"book": b, "slices": ev["slices"], "peak_raw": round(ev["peak"], 2), "avg_dep_raw": round(ev["avg_dep"], 2),
                           "f_peak": round(fp, 6), "f_mean": round(fm, 6), "net115_raw": round(ev["net115"], 2),
                           "net115_peak": round(ev["net115"] * fp, 2), "net130_peak": round(ev["net130"] * fp, 2),
                           "net115_mean": round(ev["net115"] * fm, 2), "net130_mean": round(ev["net130"] * fm, 2),
                           "ret_pct_peak": round(100 * ev["net115"] * fp / Sref[bname]["peak"], 3),
                           "dd_peak": round(ev["dd"] * fp, 2), "dd_mean": round(ev["dd"] * fm, 2), "underwater_days": round(ev["underwater_days"], 1),
                           "overlap_violations": ov, "placement_failures": fails}
                    for s_ in coins:
                        rec[f"coin_{s_}"] = round(ev["per_coin"].get(s_, 0.0) * fp, 2)
                        rec[f"coinm_{s_}"] = round(ev["per_coin"].get(s_, 0.0) * fm, 2)
                    per_book[bname].append(rec)
                if b % 250 == 0:
                    print(f"    {b}/{N_BOOKS}", flush=True)
            fh.close()
            results["determinism"][f"sha_random_books_FULL16_{design}_{wname}"] = hashlib.sha256(big.read_bytes()).hexdigest()[:16]
            for bname in BASKETS:
                df = pd.DataFrame(per_book[bname]); summaries[(bname, design, wname)] = df
                df.to_csv(OUT / f"books_{bname}_{design}_{wname}.csv", index=False, encoding="utf-8-sig")
                s_ = Sref[bname]
                blk = {"n_books": int(len(df)), "peak_scaled_to": s_["peak"], "avgdep_scaled_to": s_["avg_dep"],
                       "peak_raw": X.dist(df.peak_raw.to_numpy()), "f_peak": X.dist(df.f_peak.to_numpy()), "f_mean": X.dist(df.f_mean.to_numpy()),
                       "underwater_days": X.dist(df.underwater_days.to_numpy())}
                for scal in ("peak", "mean"):
                    for ct, sn in (("115", s_["net115"]), ("130", s_["net130"])):
                        v = df[f"net{ct}_{scal}"].to_numpy()
                        blk[f"net{ct}_{scal}"] = X.dist(v); blk[f"pct_below_{ct}_{scal}"] = X.pct_below(v, sn); blk[f"n_above_{ct}_{scal}"] = int((v >= sn).sum())
                    blk[f"dd_{scal}"] = X.dist(df[f"dd_{scal}"].to_numpy())
                    blk[f"pct_books_dd_smaller_than_strategy_{scal}"] = X.pct_below(-df[f"dd_{scal}"].to_numpy(), -s_["dd"])
                blk["ret_pct_peak"] = X.dist(df.ret_pct_peak.to_numpy())
                blk["pct_below_115_raw"] = X.pct_below(df.net115_raw.to_numpy(), s_["net115"])
                blk["median_per_coin_peak"] = {c_: round(float(df[f"coin_{c_}"].median()), 2) for c_ in BASKETS[bname] if f"coin_{c_}" in df}
                results["books"][f"{bname}_{design}_{wname}"] = blk
                print(f"    {bname}: وسيط(ذروة) {blk['net115_peak']['median']}$ · فوق {100*blk['pct_below_115_peak']:.1f}% | وسيط(متوسط) {blk['net115_mean']['median']}$ "
                      f"· فوق {100*blk['pct_below_115_mean']:.1f}% | الاستراتيجية {s_['net115']}$", flush=True)
    results["overlap_violations_total"] = overlap_total; results["placement_failures_total"] = fail_total

    # ───── التركيز (6): حذف الأعلى مساهمة ─────
    for bname in BASKETS:
        results["concentration"][bname] = {}
        for wname in WINDOWS:
            s_ = results["strategy"][chosen_key][bname][wname]; pc = s_["per_coin"]; top = max(pc, key=pc.get)
            s_wo = round(s_["net115"] - pc[top], 2)
            ent = {"top_coin": top, "top_coin_net": pc[top], "top_share_pct": round(100 * pc[top] / s_["net115"], 1) if s_["net115"] else None, "strategy_net_without_top": s_wo}
            for design in ("A", "B"):
                df = summaries[(bname, design, wname)]
                for scal, col in (("peak", "coin_"), ("mean", "coinm_")):
                    wo = (df[f"net115_{scal}"] - df[f"{col}{top}"]).to_numpy()
                    ent[f"{design}_{scal}_median_without_top"] = round(float(np.median(wo)), 2); ent[f"{design}_{scal}_pct_below_without_top"] = X.pct_below(wo, s_wo)
            results["concentration"][bname][wname] = ent

    # ───── معيار القبول ─────
    def judge(bname: str) -> dict:
        s = results["strategy"][chosen_key][bname]; A = {w: results["books"][f"{bname}_A_{w}"] for w in WINDOWS}; conc = results["concentration"][bname]
        c1 = all(s[w]["net115"] > 0 for w in WINDOWS)
        c2 = all(s[w]["net130"] > 0 for w in WINDOWS)
        c3p = all(s[w]["net115"] > A[w]["net115_peak"]["median"] and s[w]["ret_pct_peak"] > A[w]["ret_pct_peak"]["median"] for w in WINDOWS)
        c3m = all(s[w]["net115"] > A[w]["net115_mean"]["median"] for w in WINDOWS)
        need = {w: LIMITS["mult"] * L64[w]["cycles"] / YEARS[w] for w in WINDOWS}
        c4 = all(s[w]["cycles_per_year"] >= need[w] for w in WINDOWS)
        c5 = all(s[w]["dd_pct_peak"] >= -LIMITS["max_dd_pct"] and s[w]["underwater_days"] <= LIMITS["max_underwater_days"] for w in WINDOWS)
        c6 = all(conc[w]["strategy_net_without_top"] > 0 and conc[w]["strategy_net_without_top"] > conc[w]["A_peak_median_without_top"] for w in WINDOWS)
        c7 = {"annualized_net_JUD": s["JUD"]["annualized_net"], "breakeven_monthly_cost": round(s["JUD"]["annualized_net"] / 12, 2),
              "owner_monthly_cost": "لم تُحدَّد في الورقة",
              "coverage_table": {f"{c}$/شهر": ("يغطي" if s["JUD"]["annualized_net"] >= 12 * c else "لا يغطي") for c in (10, 25, 50, 100, 200)}}
        c8 = c1 and c3p if bname == "TARGET13" else None
        integrity = overlap_total == 0
        core = c1 and c2 and c3p
        if not integrity:
            verdict = "القياس غير صالح"
        elif core and c4 and c5 and c6:
            verdict = "يمرّ"
        elif core:
            verdict = "يطوَّر"
        else:
            verdict = "لا يمرّ"
        return {"1_pos_0115": {"pass": c1, "SEL": s["SEL"]["net115"], "JUD": s["JUD"]["net115"]},
                "2_pos_0130": {"pass": c2, "SEL": s["SEL"]["net130"], "JUD": s["JUD"]["net130"]},
                "3_above_random_median": {"peak": c3p, "mean": c3m, "median_peak": {w: A[w]["net115_peak"]["median"] for w in WINDOWS},
                                          "pct_below_peak": {w: A[w]["pct_below_115_peak"] for w in WINDOWS}, "pct_below_mean": {w: A[w]["pct_below_115_mean"] for w in WINDOWS}},
                "4_opportunities": {"pass": c4, "cycles_per_year": {w: s[w]["cycles_per_year"] for w in WINDOWS}, "required": {w: round(need[w], 1) for w in WINDOWS},
                                    "L0064_cycles_per_year": {w: round(L64[w]["cycles"] / YEARS[w], 1) for w in WINDOWS}},
                "5_limits": {"pass": c5, "dd_pct": {w: s[w]["dd_pct_peak"] for w in WINDOWS}, "underwater_days": {w: s[w]["underwater_days"] for w in WINDOWS}, "limits": LIMITS},
                "6_without_top": {"pass": c6, **{w: conc[w] for w in WINDOWS}},
                "7_economics": c7, "8_target_without_memes": c8, "verdict": verdict}
    results["acceptance"] = {b: judge(b) for b in BASKETS}
    results["final"] = {"verdict_target13": results["acceptance"]["TARGET13"]["verdict"], "verdict_full16_research": results["acceptance"]["FULL16"]["verdict"]}
    for b in BASKETS:
        a = results["acceptance"][b]
        print(f"  {b}: 1={a['1_pos_0115']['pass']} 2={a['2_pos_0130']['pass']} 3={a['3_above_random_median']['peak']}/{a['3_above_random_median']['mean']} "
              f"4={a['4_opportunities']['pass']} 5={a['5_limits']['pass']} 6={a['6_without_top']['pass']} ⇒ {a['verdict']}", flush=True)

    # ───── الحارس والتتابع ─────
    files = sorted(OUT.glob("trades_strategy_*.csv")) + sorted(OUT.glob("trades_finalist_*.csv")) + \
        [BOOKS_DIR / f"random_books_FULL16_{d}_{w}.csv" for d in ("A", "B") for w in WINDOWS] + sorted((OUT / "samples").glob("*.csv"))
    for p in files:
        line = X.guard(p); results["guard"].append(line)
    seq = subprocess.run([sys.executable, str(ROOT / "tools" / "position_sequencing_audit.py"), "--dir", str(OUT / "samples"), "--json"], capture_output=True, text=True)
    (OUT / "sequencing_audit_samples.json").write_text(seq.stdout, encoding="utf-8")
    seq2 = subprocess.run([sys.executable, str(ROOT / "tools" / "position_sequencing_audit.py"), "--trades", str(OUT / "trades_strategy_TARGET13_FULL.csv"), "--json"], capture_output=True, text=True)
    (OUT / "sequencing_audit_strategy.json").write_text(seq2.stdout, encoding="utf-8")
    import pandas, numpy, pyarrow  # noqa
    results["env"] = {"date": "2026-09-27", "python": platform.python_version(), "pandas": pandas.__version__, "numpy": numpy.__version__, "pyarrow": pyarrow.__version__,
                      "platform": platform.platform(), "base_branch": "arena/l0064-long-cycle-full-2026-09-27 @ 6affd58", "n_books": N_BOOKS, "seed_base": Y.SEED_BASE,
                      "cost": {"base": COST, "stress": COST_130, "slippage": 0.0}, "years": YEARS}
    text = json.dumps(results, ensure_ascii=False, indent=2, default=str)
    (OUT / f"results_{pass_tag}.json").write_text(text, encoding="utf-8")
    if pass_tag == "pass1":
        (OUT / "results.json").write_text(text, encoding="utf-8")
        (OUT / "env_dump.txt").write_text(json.dumps(results["env"], ensure_ascii=False, indent=2), encoding="utf-8")
        (OUT / "guard_log.json").write_text(json.dumps(results["guard"], ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"اكتمل ({pass_tag}). تداخل={overlap_total} فشل وضع={fail_total} · الحكم المستهدفة: {results['final']['verdict_target13']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "pass1"))
