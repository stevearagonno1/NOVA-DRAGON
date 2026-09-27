#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0066 — قياس الإعداد المثبَّت (درجة الهضبة من مسح الاختيار) في الاختيار والحكم والدورة الكاملة على السلّتين،
مع الضوابط (1000 دفتر عشوائي × A/B × نافذتان × سلّتان، تسويتان)، الاحتفاظ، تسرّب المستقبل، الاقتصاد، تقرير كل عملة،
والبوابات الأربع عشرة. يعيد استعمال أدوات L0065/L0064/L0063.
    python3 history/hyp_lab/run_l0066_measure.py pass1
    python3 history/hyp_lab/run_l0066_measure.py pass2
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
import pullback_engine66 as PE  # noqa: E402
import run_l0066_sweep as S  # noqa: E402
import run_l0065_measure as M65  # noqa: E402
import run_l0064_measure as Y  # noqa: E402

X, M = Y.X, Y.M
OUT = S.OUT
(OUT / "samples").mkdir(exist_ok=True)
BOOKS_DIR = pathlib.Path.home() / ".cache" / "l0066_books"
BOOKS_DIR.mkdir(parents=True, exist_ok=True)
Y.SEED_BASE = 66
FULL16, TARGET13, MEMES = S.FULL16, S.TARGET13, S.MEMES
BASKETS = {"FULL16": FULL16, "TARGET13": TARGET13}
WINDOWS = ("SEL", "JUD")
N_BOOKS = 1000
COST, COST_130 = 0.00115, 0.00130
CUT, END = S.CUT, pd.Timestamp("2026-08-31", tz="UTC")
YEARS = M65.YEARS
L64 = M65.L64
GATES = {"max_dd_pct": 35.0, "max_underwater_days": 540, "mult": 1.5, "top_share_pct": 35.0, "min_win_rate_pct": 35.0, "max_best_trade_share": 0.25, "max_best_month_share": 0.40}
TRUNC_DATES = ("2022-09-01", "2023-06-01", "2025-03-01")
TRUNC_COINS = ("BTCUSDT", "ETHUSDT", "ATOMUSDT", "XLMUSDT")


def cfg_from_key(key: str) -> PE.Config:
    for c in PE.all_configs():
        if c.key == key:
            return c
    raise KeyError(key)


def strategy_rows(cfg: PE.Config) -> dict[str, dict[str, list[dict]]]:
    out = {}
    for sym in FULL16:
        rows = {"SEL": [], "JUD": [], "FULL": []}
        ctx_cut = S.load_ctx(sym, CUT)
        if ctx_cut is not None:
            r = PE.run_config(ctx_cut, cfg); PE.price_pnl(r, COST); rows["SEL"] = r
        ctx_full = S.load_ctx(sym, END + pd.Timedelta(days=1))
        if ctx_full is not None:
            r = PE.run_config(ctx_full, cfg); PE.price_pnl(r, COST); rows["FULL"] = r
            rows["JUD"] = [q for q in r if pd.Timestamp(q["entry_time"]) >= CUT]
        out[sym] = rows
    return out


def wilson(p: float, n: int, z: float = 1.96) -> tuple:
    if n == 0:
        return (None, None)
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(100 * (c - h), 1), round(100 * (c + h), 1))


def strat_block(rows: list[dict], w: X.Window, coins, wname: str) -> dict:
    blk = M65.strat_block(rows, w, coins, wname)
    if blk.get("empty"):
        return blk
    pnls = np.array([r["pnl_usd"] for r in rows])
    cyc = M.cycles(rows)
    cyc_pnl = np.array([sum(r["pnl_usd"] for r in g) for g in cyc])
    blk["median_slice_pnl"] = round(float(np.median(pnls)), 2)
    blk["best_slice"] = round(float(pnls.max()), 2)
    blk["best_slice_share_of_net"] = round(float(pnls.max() / blk["net115"]), 3) if blk["net115"] > 0 else None
    blk["best_month_share_of_net"] = round(max(blk["monthly"]["series"].values()) / blk["net115"], 3) if blk["net115"] > 0 else None
    blk["cycle_win_rate_pct"] = round(100 * float((cyc_pnl > 0).mean()), 1)
    blk["slices_per_cycle"] = round(len(rows) / len(cyc), 3)
    blk["annual_trading_cost"] = round(sum(r["notional_usd"] * 2 * COST for r in rows) / YEARS[wname], 2)
    blk["net_per_1000_per_year"] = round(blk["annualized_net"] / (PE.BOOK_USD * len(coins)) * 1000, 2)
    blk["wilson_win_rate_ci"] = wilson(blk["win_rate_slices_pct"] / 100, len(rows))
    pf = [r for r in rows if r["reason"] == "هدف-جزئي"]
    blk["E2_partial_target_slices"] = len(pf)
    blk["E2_partial_was_full_exit_cycles"] = len({(r["symbol"], r["series"]) for r in pf if r.get("partial_full")})
    blk["E2_true_two_part_cycles"] = len({(r["symbol"], r["series"]) for r in pf if not r.get("partial_full")})
    top = max(blk["per_coin"], key=blk["per_coin"].get)
    blk["top_coin"] = top
    blk["top_coin_share_pct"] = round(100 * blk["per_coin"][top] / blk["net115"], 1) if blk["net115"] > 0 else None
    return blk


def per_coin_report(per_sym: dict, wins: dict, basket_net: dict) -> dict:
    rep = {}
    for sym in FULL16:
        e = {"meme": sym in MEMES}
        total_cycles = 0
        ok_data = True
        for wname in WINDOWS:
            rows = per_sym[sym][wname]
            w = wins[wname]
            fr = M.FR[sym]
            sub = fr[(fr.index >= w.s) & (fr.index < w.e)]
            span_days = (sub.index[-1] - sub.index[0]).days if len(sub) else 0
            if span_days < 365:
                ok_data = False
            if rows:
                ev = Y.evaluate_raw(rows, w)
                cyc = M.cycles(rows)
                total_cycles += len(cyc)
                pn = np.array([r["pnl_usd"] for r in rows])
                wins_n = int((pn > 0).sum())
                mp = M65.monthly_pnl(rows, w)
                e[wname] = {"net": round(ev["net115"], 2), "cycles": len(cyc), "slices": len(rows), "wins": wins_n, "losses": int(len(rows) - wins_n),
                            "win_rate_pct": round(100 * wins_n / len(rows), 1), "win_rate_ci95": wilson(wins_n / len(rows), len(rows)),
                            "avg_slice": round(float(pn.mean()), 2), "median_slice": round(float(np.median(pn)), 2), "best_slice": round(float(pn.max()), 2),
                            "best_slice_share": round(float(pn.max() / ev["net115"]), 2) if ev["net115"] > 0 else None,
                            "dd": round(ev["dd"], 2), "dd_pct_book": round(100 * ev["dd"] / PE.BOOK_USD, 1), "underwater_days": round(ev["underwater_days"], 1),
                            "winning_months_pct_active": mp["winning_months_pct_active"], "months_active": mp["months_active"],
                            "share_of_basket_pct": round(100 * ev["net115"] / basket_net[wname], 1) if basket_net[wname] > 0 else None, "span_days": span_days}
            else:
                e[wname] = {"net": 0.0, "cycles": 0, "slices": 0, "wins": 0, "losses": 0, "win_rate_pct": None, "win_rate_ci95": (None, None), "avg_slice": None,
                            "median_slice": None, "best_slice": None, "best_slice_share": None, "dd": 0.0, "dd_pct_book": 0.0, "underwater_days": 0.0,
                            "winning_months_pct_active": None, "months_active": 0, "share_of_basket_pct": None, "span_days": span_days}
                ok_data = False
        sel, jud = e["SEL"], e["JUD"]
        total = sel["net"] + jud["net"]
        enough = ok_data and sel["cycles"] >= 5 and jud["cycles"] >= 5 and total_cycles >= 10
        if not enough:
            cls = "غير كافية البيانات"
        elif sel["net"] > 0 and jud["net"] > 0 and (sel["best_slice_share"] or 0) < 0.5 and (jud["best_slice_share"] or 0) < 0.5 \
                and sel["dd_pct_book"] >= -35 and jud["dd_pct_book"] >= -35 and sel["underwater_days"] <= 540 and jud["underwater_days"] <= 540:
            cls = "مناسبة"
        elif jud["net"] <= 0 or jud["dd_pct_book"] < -35 or jud["underwater_days"] > 540:
            cls = "غير مناسبة"
        elif jud["net"] > 0 and total > 0:
            cls = "واعدة"
        else:
            cls = "غير مناسبة"
        e["total_net"] = round(total, 2)
        e["class"] = cls
        rep[sym] = e
    return rep


def leakage_test(cfg: PE.Config) -> dict:
    out = {}
    for sym in TRUNC_COINS:
        ctx_full = S.load_ctx(sym, END + pd.Timedelta(days=1))
        full = PE.run_config(ctx_full, cfg)
        ent = {}
        for T in TRUNC_DATES:
            Tt = pd.Timestamp(T, tz="UTC")
            ctx_tr = S.load_ctx(sym, Tt)
            if ctx_tr is None:
                ent[T] = {"skipped": True}; continue
            tr = PE.run_config(ctx_tr, cfg)
            keyf = lambda r: (r["entry_time"], r["stage"], round(r["entry_px"], 8), round(r["notional_usd"], 4))
            before = [r for r in full if pd.Timestamp(r["entry_time"]) < Tt]
            same_entries = sorted(map(keyf, tr)) == sorted(map(keyf, before))
            trk = {(r["entry_time"], r["stage"]): r for r in tr}
            closed = [r for r in before if pd.Timestamp(r["exit_time"]) < Tt]
            same_exits = all((k := (r["entry_time"], r["stage"])) in trk and trk[k]["exit_time"] == r["exit_time"] and trk[k]["reason"] == r["reason"]
                             and abs(trk[k]["exit_px"] - r["exit_px"]) < 1e-9 for r in closed)
            open_at = [r for r in before if pd.Timestamp(r["exit_time"]) >= Tt]
            open_ok = all(trk.get((r["entry_time"], r["stage"]), {}).get("reason") == "نهاية-العينة" for r in open_at)
            n_common = ctx_tr.n
            sig_equal = bool(np.array_equal(ctx_tr.not_downtrend[cfg.trend], ctx_full.not_downtrend[cfg.trend][:n_common])
                             and np.array_equal(ctx_tr.pullback_seen[(cfg.ref, cfg.depth)], ctx_full.pullback_seen[(cfg.ref, cfg.depth)][:n_common])
                             and np.array_equal(ctx_tr.recovery, ctx_full.recovery[:n_common]))
            ent[T] = {"same_entries_before_T": same_entries, "same_exits_closed_before_T": same_exits, "open_at_T_closed_as_end": open_ok,
                      "signals_equal_on_common_bars": sig_equal, "n_before_T": len(before), "n_open_at_T": len(open_at)}
        out[sym] = ent
    out["ALL_PASSED"] = all(v.get("same_entries_before_T", True) and v.get("same_exits_closed_before_T", True) and v.get("open_at_T_closed_as_end", True)
                            and v.get("signals_equal_on_common_bars", True) for sym in TRUNC_COINS for v in out[sym].values())
    return out


def save_rows(name: str, rows: list[dict]) -> pathlib.Path:
    M.OUT = OUT
    return M.save_trades(name, rows)


def main(pass_tag: str) -> int:
    rule = json.loads((OUT / "acceptance_rule_l0066.json").read_text(encoding="utf-8"))
    sel = json.loads((OUT / "selection.json").read_text(encoding="utf-8"))
    chosen_key = sel["chosen_by_plateau"]["key"]
    sweep = pd.read_csv(OUT / "sweep_SEL.csv")
    pos = sweep[sweep.t13_net > 0].sort_values("t13_net", ascending=False)
    ref_key = str(pos.iloc[0].key) if len(pos) else None
    wins = {w: X.Window(w) for w in WINDOWS}; wins["FULL"] = X.Window("FULL")
    results = {"pass": pass_tag, "chosen": chosen_key, "single_peak_reference": ref_key, "strategy": {}, "hold": {}, "books": {}, "concentration": {},
               "per_coin": {}, "guard": [], "determinism": {}, "L0064_reference_target13": L64, "gates_params": GATES}
    keys = [chosen_key] + ([ref_key] if ref_key and ref_key != chosen_key else [])
    per_sym_all = {}
    for key in keys:
        cfg = cfg_from_key(key)
        per_sym = strategy_rows(cfg); per_sym_all[key] = per_sym
        results["strategy"][key] = {"config": cfg.__dict__ | {"weights": cfg.weights, "partial_target_mult": 1 + cfg.depth / 2, "stage_spacing": cfg.depth / cfg.stages}}
        for bname, coins in BASKETS.items():
            results["strategy"][key][bname] = {}
            for wname in ("SEL", "JUD", "FULL"):
                rows = M65.basket_rows(per_sym, coins, wname)
                blk = strat_block(rows, wins[wname], coins, wname)
                results["strategy"][key][bname][wname] = blk
                tag = "strategy" if key == chosen_key else "reference"
                if key == chosen_key or wname != "FULL":
                    save_rows(f"{tag}_{bname}_{wname}", rows)
                if not blk.get("empty"):
                    print(f"  {key} · {bname} · {wname}: صافي={blk['net115']} (0.130: {blk['net130']}) دورات={blk['cycles']} ({blk['cycles_per_year']}/سنة) ذروة={blk['peak']} "
                          f"عائد%={blk['ret_pct_peak']} هبوط={blk['dd']} ({blk['dd_pct_peak']}%) تحت القمة={blk['underwater_days']} متوسط الصفقة={blk['avg_slice_pnl']} "
                          f"رابحة%={blk['win_rate_slices_pct']} أعلى عملة={blk['top_coin']} {blk['top_coin_share_pct']}%", flush=True)
            s = results["strategy"][key][bname]
            s["FULL_equals_SEL_plus_JUD"] = abs(s["FULL"]["net115"] - s["SEL"]["net115"] - s["JUD"]["net115"]) < 0.01
    per_sym = per_sym_all[chosen_key]
    ST = results["strategy"][chosen_key]
    results["per_coin"] = per_coin_report(per_sym, wins, {w: ST["TARGET13"][w]["net115"] for w in WINDOWS})
    results["meme_effect"] = {w: {"full16": ST["FULL16"][w]["net115"], "target13": ST["TARGET13"][w]["net115"], "meme": round(ST["FULL16"][w]["net115"] - ST["TARGET13"][w]["net115"], 2)} for w in ("SEL", "JUD", "FULL")}
    results["leakage"] = leakage_test(cfg_from_key(chosen_key))
    print(f"  تسرّب المستقبل: {'✅' if results['leakage']['ALL_PASSED'] else '❌'}", flush=True)

    for bname, coins in BASKETS.items():
        results["hold"][bname] = {}
        for wname in WINDOWS:
            rows_h, st = M.buyhold(coins, ST[bname][wname]["peak"], wname)
            results["hold"][bname][wname] = {k: v for k, v in st.items() if k != "spans"}

    tables = {b: {w: X.cycle_table(M65.basket_rows(per_sym, BASKETS[b], w)) for w in WINDOWS} for b in BASKETS}
    summaries = {}
    overlap_total = fail_total = 0
    for design in ("A", "B"):
        for wname in WINDOWS:
            win = wins[wname]
            Sref = {b: ST[b][wname] for b in BASKETS}
            print(f"══ عشوائي {design} · {wname} · {N_BOOKS} دفتر ══", flush=True)
            per_book = {b: [] for b in BASKETS}
            big = BOOKS_DIR / f"random_books_FULL16_{design}_{wname}.csv"
            fh = big.open("w", encoding="utf-8-sig", newline=""); wr = csv.writer(fh)
            wr.writerow(["book", "symbol", "entry_time", "exit_time", "entry", "exit", "notional", "pnl", "reason", "stage", "bars_held"])
            for b in range(1, N_BOOKS + 1):
                rows16, fails = Y.make_book(design, win, tables["FULL16"][wname], FULL16, b)
                fail_total += fails; ov = X.overlap_violations(rows16); overlap_total += ov
                for r in rows16:
                    wr.writerow([b, r["symbol"], r["entry_time"], r["exit_time"], r["entry_px"], r["exit_px"], r["notional_usd"],
                                 round(float(X.pnl_vec(r["entry_px"], r["exit_px"], r["notional_usd"], COST)), 4), r["reason"], 0, r["bars_held"]])
                if b <= 3:
                    pd.DataFrame([{"symbol": r["symbol"], "entry_time": r["entry_time"], "exit_time": r["exit_time"], "entry": r["entry_px"], "exit": r["exit_px"],
                                   "notional": r["notional_usd"], "pnl": round(float(X.pnl_vec(r["entry_px"], r["exit_px"], r["notional_usd"], COST)), 4),
                                   "reason": r["reason"], "stage": 0, "bars_held": r["bars_held"]} for r in rows16]).to_csv(OUT / "samples" / f"trades_random_{design}_{wname}_book{b}.csv", index=False, encoding="utf-8-sig")
                for bname, coins in BASKETS.items():
                    rows = rows16 if bname == "FULL16" else [r for r in rows16 if r["symbol"] not in MEMES]
                    if not rows:
                        continue
                    ev = Y.evaluate_raw(rows, win)
                    fp = Sref[bname]["peak"] / ev["peak"]; fm = Sref[bname]["avg_dep"] / ev["avg_dep"]
                    rec = {"book": b, "slices": ev["slices"], "peak_raw": round(ev["peak"], 2), "avg_dep_raw": round(ev["avg_dep"], 2), "f_peak": round(fp, 6), "f_mean": round(fm, 6),
                           "net115_raw": round(ev["net115"], 2), "net115_peak": round(ev["net115"] * fp, 2), "net130_peak": round(ev["net130"] * fp, 2),
                           "net115_mean": round(ev["net115"] * fm, 2), "net130_mean": round(ev["net130"] * fm, 2), "ret_pct_peak": round(100 * ev["net115"] * fp / Sref[bname]["peak"], 3),
                           "dd_peak": round(ev["dd"] * fp, 2), "dd_mean": round(ev["dd"] * fm, 2), "underwater_days": round(ev["underwater_days"], 1), "overlap_violations": ov, "placement_failures": fails}
                    for s_ in coins:
                        rec[f"coin_{s_}"] = round(ev["per_coin"].get(s_, 0.0) * fp, 2); rec[f"coinm_{s_}"] = round(ev["per_coin"].get(s_, 0.0) * fm, 2)
                    per_book[bname].append(rec)
                if b % 250 == 0:
                    print(f"    {b}/{N_BOOKS}", flush=True)
            fh.close()
            results["determinism"][f"sha_random_books_FULL16_{design}_{wname}"] = hashlib.sha256(big.read_bytes()).hexdigest()[:16]
            for bname in BASKETS:
                df = pd.DataFrame(per_book[bname]); summaries[(bname, design, wname)] = df
                df.to_csv(OUT / f"books_{bname}_{design}_{wname}.csv", index=False, encoding="utf-8-sig")
                s_ = Sref[bname]
                blk = {"n_books": int(len(df)), "peak_scaled_to": s_["peak"], "avgdep_scaled_to": s_["avg_dep"], "peak_raw": X.dist(df.peak_raw.to_numpy()),
                       "f_peak": X.dist(df.f_peak.to_numpy()), "f_mean": X.dist(df.f_mean.to_numpy()), "underwater_days": X.dist(df.underwater_days.to_numpy())}
                for scal in ("peak", "mean"):
                    for ct, sn in (("115", s_["net115"]), ("130", s_["net130"])):
                        v = df[f"net{ct}_{scal}"].to_numpy(); blk[f"net{ct}_{scal}"] = X.dist(v); blk[f"pct_below_{ct}_{scal}"] = X.pct_below(v, sn); blk[f"n_above_{ct}_{scal}"] = int((v >= sn).sum())
                    blk[f"dd_{scal}"] = X.dist(df[f"dd_{scal}"].to_numpy()); blk[f"pct_books_dd_smaller_than_strategy_{scal}"] = X.pct_below(-df[f"dd_{scal}"].to_numpy(), -s_["dd"])
                blk["ret_pct_peak"] = X.dist(df.ret_pct_peak.to_numpy()); blk["pct_below_115_raw"] = X.pct_below(df.net115_raw.to_numpy(), s_["net115"])
                blk["median_per_coin_peak"] = {c_: round(float(df[f"coin_{c_}"].median()), 2) for c_ in BASKETS[bname] if f"coin_{c_}" in df}
                results["books"][f"{bname}_{design}_{wname}"] = blk
                print(f"    {bname}: وسيط(ذروة) {blk['net115_peak']['median']}$ · فوق {100*blk['pct_below_115_peak']:.1f}% | وسيط(متوسط) {blk['net115_mean']['median']}$ · فوق {100*blk['pct_below_115_mean']:.1f}% | الاستراتيجية {s_['net115']}$", flush=True)
    results["overlap_violations_total"] = overlap_total; results["placement_failures_total"] = fail_total

    for bname in BASKETS:
        results["concentration"][bname] = {}
        for wname in WINDOWS:
            s_ = ST[bname][wname]; pc = s_["per_coin"]; top = max(pc, key=pc.get); s_wo = round(s_["net115"] - pc[top], 2)
            ent = {"top_coin": top, "top_coin_net": pc[top], "top_share_pct": s_["top_coin_share_pct"], "strategy_net_without_top": s_wo}
            for design in ("A", "B"):
                df = summaries[(bname, design, wname)]
                for scal, col in (("peak", "coin_"), ("mean", "coinm_")):
                    wo = (df[f"net115_{scal}"] - df[f"{col}{top}"]).to_numpy()
                    ent[f"{design}_{scal}_median_without_top"] = round(float(np.median(wo)), 2); ent[f"{design}_{scal}_pct_below_without_top"] = X.pct_below(wo, s_wo)
            results["concentration"][bname][wname] = ent

    def judge(bname: str) -> dict:
        s = ST[bname]; A = {w: results["books"][f"{bname}_A_{w}"] for w in WINDOWS}; H = results["hold"][bname]
        g = {}
        g["1"] = all(s[w]["net115"] > 0 for w in WINDOWS)
        g["2"] = all(s[w]["net115"] > 0 and s[w]["net130"] > 0 for w in WINDOWS)
        g["3"] = all(s[w]["net115"] > A[w]["net115_peak"]["median"] for w in WINDOWS)
        g["3_mean"] = all(s[w]["net115"] > A[w]["net115_mean"]["median"] for w in WINDOWS)
        g["4"] = s["JUD"]["net115"] >= H["JUD"]["net"]
        need = {w: GATES["mult"] * L64[w]["cycles"] / YEARS[w] for w in WINDOWS}
        g["5"] = all(s[w]["cycles_per_year"] >= need[w] for w in WINDOWS)
        g["6"] = all(s[w]["dd_pct_peak"] >= -GATES["max_dd_pct"] for w in WINDOWS)
        g["7"] = all(s[w]["underwater_days"] <= GATES["max_underwater_days"] for w in WINDOWS)
        g["8"] = all((s[w]["top_coin_share_pct"] is None) or (s[w]["top_coin_share_pct"] <= GATES["top_share_pct"]) for w in WINDOWS) and all(s[w]["net115"] > 0 for w in WINDOWS)
        g["9"] = s["JUD"]["avg_slice_pnl"] > 0
        bs, bm = s["JUD"]["best_slice_share_of_net"], s["JUD"]["best_month_share_of_net"]
        g["10"] = s["JUD"]["win_rate_slices_pct"] >= GATES["min_win_rate_pct"] and bs is not None and bs < GATES["max_best_trade_share"] and bm is not None and bm < GATES["max_best_month_share"]
        g["11"] = True
        ann = s["JUD"]["annualized_net"]
        g["12"] = ann > 0
        g["13"] = overlap_total == 0 and results["leakage"]["ALL_PASSED"]
        g["14"] = True
        core_fail = not (g["1"] and g["2"] and g["3"] and g["4"] and g["9"] and g["12"])
        if not g["13"]:
            verdict = "القياس غير صالح"
        elif all(g[k] for k in ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "12")):
            verdict = "يمرّ"
        elif not core_fail:
            verdict = "يطوَّر"
        else:
            verdict = "لا يمرّ"
        return {"gates": g, "verdict": verdict, "details": {
            "net": {w: s[w]["net115"] for w in WINDOWS}, "net130": {w: s[w]["net130"] for w in WINDOWS},
            "random_median_peak": {w: A[w]["net115_peak"]["median"] for w in WINDOWS}, "pct_below_peak": {w: A[w]["pct_below_115_peak"] for w in WINDOWS},
            "pct_below_mean": {w: A[w]["pct_below_115_mean"] for w in WINDOWS}, "hold_JUD": H["JUD"]["net"], "hold_SEL": H["SEL"]["net"],
            "cycles_per_year": {w: s[w]["cycles_per_year"] for w in WINDOWS}, "required_cpy": {w: round(need[w], 1) for w in WINDOWS},
            "dd_pct": {w: s[w]["dd_pct_peak"] for w in WINDOWS}, "underwater_days": {w: s[w]["underwater_days"] for w in WINDOWS},
            "top_share_pct": {w: s[w]["top_coin_share_pct"] for w in WINDOWS}, "top_coin": {w: s[w]["top_coin"] for w in WINDOWS},
            "avg_slice_JUD": s["JUD"]["avg_slice_pnl"], "win_rate_JUD": s["JUD"]["win_rate_slices_pct"], "best_slice_share_JUD": bs, "best_month_share_JUD": bm,
            "annualized_net_JUD": ann, "max_monthly_ops_cost": round(ann / 12, 2), "net_per_1000_per_year_JUD": s["JUD"]["net_per_1000_per_year"],
            "annual_trading_cost_JUD": s["JUD"]["annual_trading_cost"]}}
    results["acceptance"] = {b: judge(b) for b in BASKETS}
    results["final"] = {"verdict_target13": results["acceptance"]["TARGET13"]["verdict"], "verdict_full16_research": results["acceptance"]["FULL16"]["verdict"]}
    for b in BASKETS:
        a = results["acceptance"][b]
        print(f"  {b}: " + " ".join(f"{k}={'✓' if v else '✗'}" for k, v in a["gates"].items()) + f" ⇒ {a['verdict']}", flush=True)

    files = sorted(OUT.glob("trades_strategy_*.csv")) + sorted(OUT.glob("trades_reference_*.csv")) + \
        [BOOKS_DIR / f"random_books_FULL16_{d}_{w}.csv" for d in ("A", "B") for w in WINDOWS] + sorted((OUT / "samples").glob("*.csv"))
    for p in files:
        results["guard"].append(X.guard(p))
    seq = subprocess.run([sys.executable, str(ROOT / "tools" / "position_sequencing_audit.py"), "--dir", str(OUT / "samples"), "--json"], capture_output=True, text=True)
    (OUT / "sequencing_audit_samples.json").write_text(seq.stdout, encoding="utf-8")
    seq2 = subprocess.run([sys.executable, str(ROOT / "tools" / "position_sequencing_audit.py"), "--trades", str(OUT / "trades_strategy_TARGET13_FULL.csv"), "--json"], capture_output=True, text=True)
    (OUT / "sequencing_audit_strategy.json").write_text(seq2.stdout, encoding="utf-8")
    import pandas, numpy, pyarrow  # noqa
    results["env"] = {"date": "2026-09-27", "python": platform.python_version(), "pandas": pandas.__version__, "numpy": numpy.__version__, "pyarrow": pyarrow.__version__,
                      "platform": platform.platform(), "base_branch": "arena/l0065-normal-pullback-2026-09-27 @ d6847ae", "n_books": N_BOOKS, "seed_base": Y.SEED_BASE,
                      "cost": {"base": COST, "stress": COST_130, "slippage": "0 — غير مقاس"}, "years": YEARS,
                      "file_fingerprints": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:16] for p in [ROOT / "history" / "hyp_lab" / "pullback_engine66.py", ROOT / "history" / "hyp_lab" / "run_l0066_sweep.py", OUT / "sweep_SEL.csv", OUT / "acceptance_rule_l0066.json"]}}
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
