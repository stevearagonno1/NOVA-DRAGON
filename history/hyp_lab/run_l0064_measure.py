#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0064 — قياس النسخة المطوّرة (NOVA_LC_V3=1) بعد بوابة المطابقة: السلة البحثية الكاملة (16) والسلة
المستهدفة (13، بلا DOGE/SHIB/PEPE)، الفترتان + الدورة الكاملة كسياق، الكلفتان، 1000 دفتر عشوائي لكل تصميم
(A، B) ولكل فترة ولكل سلة، وتسويتان لرأس المال (الذروة — الأساسية؛ متوسط المنشور — الحساسية).

يعتمد على: run_l0064_match.py (سجلات المحرك في ~/.cache/l0064_records)، run_l0063_random_fair.py (الأدوات).
    python3 history/hyp_lab/run_l0064_measure.py pass1
    python3 history/hyp_lab/run_l0064_measure.py pass2      # إعادة مستقلة للحتمية
"""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import platform
import subprocess
import sys
import zlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path("/home/user/work")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "history" / "hyp_lab"))

import run_l0063_random_fair as X  # noqa: E402  (Window, pnl_vec, cycle_table, dist, pct_below, overlap_violations)
import run_l0061_lc as L  # noqa: E402

M = X.M
OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0064"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "samples").mkdir(exist_ok=True)
BOOKS_DIR = pathlib.Path.home() / ".cache" / "l0064_books"
BOOKS_DIR.mkdir(parents=True, exist_ok=True)
RECS64 = pathlib.Path.home() / ".cache" / "l0064_records"

MEMES = ("DOGEUSDT", "SHIBUSDT", "PEPEUSDT")
FULL16 = tuple(L.UNIVERSE)
TARGET13 = tuple(s for s in FULL16 if s not in MEMES)
BASKETS = {"FULL16": FULL16, "TARGET13": TARGET13}
WINDOWS = ("SEL", "JUD")
N_BOOKS = 1000
SEED_BASE = 64
COST, COST_130 = X.COST, X.COST_130
MAX_TRIES = 200
WCODE, DCODE = X.WCODE, X.DCODE


def sha_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def evaluate_raw(rows: list[dict], w: X.Window) -> dict:
    """تقييم بلا تسوية: الذروة، متوسط المنشور، الصافي عند الكلفتين، الهبوط، أطول فترة تحت القمة، مساهمة كل عملة."""
    if not rows:
        return {"empty": True}
    sym = np.array([r["symbol"] for r in rows])
    entry = np.array([float(r["entry_px"]) for r in rows])
    exit_ = np.array([float(r["exit_px"]) for r in rows])
    notional = np.array([float(r["notional_usd"]) for r in rows])
    gi0 = np.array([w.gi(r["entry_time"]) for r in rows])
    gi1 = np.array([w.gi(r["exit_time"]) for r in rows])
    dep = np.zeros(w.n + 1)
    np.add.at(dep, gi0, notional)
    np.add.at(dep, gi1, -notional)
    dep = np.cumsum(dep)[: w.n]
    peak = float(dep.max())
    avg_dep = float(dep.mean())
    p115 = X.pnl_vec(entry, exit_, notional, COST)
    p130 = X.pnl_vec(entry, exit_, notional, COST_130)
    eq = np.zeros(w.n)
    for k in range(len(rows)):
        a, b = int(gi0[k]), int(gi1[k])
        if b > a:
            eq[a:b] += X.pnl_vec(entry[k], w.close[sym[k]][a:b], notional[k], COST)
        eq[b:] += p115[k]
    run_max = np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]
    dd = eq - run_max
    under = dd < -1e-9
    longest = cur = 0
    for u in under:
        cur = cur + 1 if u else 0
        longest = max(longest, cur)
    per_coin = {str(s_): float(p115[sym == s_].sum()) for s_ in np.unique(sym)}
    return {"empty": False, "peak": peak, "avg_dep": avg_dep, "net115": float(p115.sum()), "net130": float(p130.sum()),
            "dd": float(dd.min()), "peak_equity": float(run_max.max()), "underwater_days": longest * 4 / 24,
            "max_cycle_notional": float(notional.max()), "per_coin": per_coin, "slices": len(rows), "_p115": p115, "_p130": p130}


def make_book(design: str, w: X.Window, table: dict, coins, book_index: int) -> tuple[list[dict], int]:
    rows, failures = [], 0
    for sym in coins:
        pairs = table.get(sym, [])
        n = len(pairs)
        if n == 0:
            continue
        fr = w.frames[sym]
        ln = len(fr)
        if ln < 3:
            continue
        rng = np.random.default_rng(np.random.SeedSequence([SEED_BASE, WCODE[w.name], DCODE[design], int(book_index),
                                                            zlib.crc32(sym.encode()) & 0xFFFFFFFF]))
        if design == "B":
            d_med = max(int(np.median([d for d, _ in pairs])), 1)
            n_mean = float(np.mean([x for _, x in pairs]))
            pairs = [(d_med, n_mean)] * n
        taken: list[tuple[int, int]] = []
        opens = fr["open"].to_numpy(dtype=float)
        closes = fr["close"].to_numpy(dtype=float)
        idx = fr.index
        for _ in range(n):
            placed = False
            for _try in range(MAX_TRIES):
                d, notional = pairs[int(rng.integers(0, len(pairs)))] if design == "A" else pairs[0]
                hi = ln - 2 - d
                if hi < 0:
                    continue
                i = int(rng.integers(0, hi + 1))
                a, b = i + 1, i + 1 + d
                if all(a > tb or b < ta for ta, tb in taken):
                    taken.append((a, b))
                    rows.append({"symbol": sym, "entry_time": idx[a].isoformat(), "exit_time": idx[b].isoformat(),
                                 "entry_ref_px": float(opens[a]), "entry_px": float(opens[a]), "exit_px": float(closes[b]),
                                 "notional_usd": float(notional), "reason": "عشوائي", "stage": 0, "bars_held": int(d),
                                 "entry_bar": a, "exit_bar": b})
                    placed = True
                    break
            if not placed:
                failures += 1
    return rows, failures


def strategy_block(rows: list[dict], w: X.Window, coins) -> dict:
    ev = evaluate_raw(rows, w)
    cyc = M.cycles(rows)
    out = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in ev.items() if not k.startswith("_") and k != "per_coin"}
    out["per_coin"] = {k: round(v, 2) for k, v in sorted(ev["per_coin"].items(), key=lambda x: -x[1])}
    out["cycles"] = len(cyc)
    out["ret_pct_peak"] = round(100 * ev["net115"] / ev["peak"], 3)
    out["ret_pct_peak_130"] = round(100 * ev["net130"] / ev["peak"], 3)
    out["ret_pct_avgdep"] = round(100 * ev["net115"] / ev["avg_dep"], 3)
    out["dd_pct_peak"] = round(100 * ev["dd"] / ev["peak"], 2)
    out["symbols_traded"] = len(ev["per_coin"])
    out["coins_in_basket"] = len(coins)
    return out


def main(pass_tag: str) -> int:
    rule = json.loads((OUT / "acceptance_rule_l0064.json").read_text(encoding="utf-8"))
    match = json.loads((OUT / "match_report.json").read_text(encoding="utf-8"))
    if not match.get("MATCH_GATE_PASSED"):
        raise SystemExit("بوابة المطابقة لم تنجح — لا قياس")
    assert tuple(rule["baskets"]["target_13"]) == TARGET13 and rule["random_control"]["books_per_design_per_window_per_basket"] == N_BOOKS
    R64 = {sym: json.loads((RECS64 / f"{sym}.json").read_text(encoding="utf-8")) for sym in FULL16}
    WIN = {w: X.Window(w) for w in WINDOWS}
    WIN_FULL = X.Window("FULL")
    L.set_cost(COST)

    results = {"pass": pass_tag, "match_gate": {"passed": True, "files": match["files"], "legacy": match["legacy"],
                                                 "long_cycle_py_sha256": match["long_cycle_py_sha256"]},
               "strategy": {}, "books": {}, "concentration": {}, "guard": [], "determinism": {}, "meme_effect": {}}

    # ───── الاستراتيجية لكل سلة: الفترتان + الدورة الكاملة ─────
    print("══ الاستراتيجية V3 — السلّتان ══", flush=True)
    strat_rows: dict[str, dict[str, list[dict]]] = {}
    for bname, coins in BASKETS.items():
        results["strategy"][bname] = {}
        strat_rows[bname] = {}
        for w in ("SEL", "JUD", "FULL"):
            rows, _ = M.rows_for(R64, "bear", coins, w)
            strat_rows[bname][w] = rows
            win = WIN[w] if w in WIN else WIN_FULL
            blk = strategy_block(rows, win, coins)
            results["strategy"][bname][w] = blk
            M.OUT = OUT
            p = M.save_trades(f"strategy_{bname}_{w}", rows)
            print(f"  {bname} {w}: صافي={blk['net115']} (0.130%: {blk['net130']}) دورات={blk['cycles']} شرائح={blk['slices']} "
                  f"ذروة={blk['peak']} متوسط المنشور={blk['avg_dep']} عائد%={blk['ret_pct_peak']} هبوط={blk['dd']} "
                  f"أطول تحت القمة={blk['underwater_days']:.1f} يوم", flush=True)
        s = results["strategy"][bname]
        s["FULL_equals_SEL_plus_JUD"] = abs(s["FULL"]["net115"] - s["SEL"]["net115"] - s["JUD"]["net115"]) < 0.01
    for w in ("SEL", "JUD", "FULL"):
        f16, t13 = results["strategy"]["FULL16"][w], results["strategy"]["TARGET13"][w]
        results["meme_effect"][w] = {"full16_net": f16["net115"], "target13_net": t13["net115"],
                                     "meme_contribution": round(f16["net115"] - t13["net115"], 2),
                                     "per_meme": {m: f16["per_coin"].get(m, 0.0) for m in MEMES},
                                     "cycles_full16": f16["cycles"], "cycles_target13": t13["cycles"],
                                     "peak_full16": f16["peak"], "peak_target13": t13["peak"]}

    # ───── الدفاتر العشوائية ─────
    tables = {bname: {w: X.cycle_table(strat_rows[bname][w]) for w in WINDOWS} for bname in BASKETS}
    summaries: dict[tuple, pd.DataFrame] = {}
    overlap_total = fail_total = 0
    identical_subset_check = True
    for design in ("A", "B"):
        for w in WINDOWS:
            win = WIN[w]
            table16 = tables["FULL16"][w]
            S = {b: results["strategy"][b][w] for b in BASKETS}
            print(f"══ التصميم {design} · {w} · {N_BOOKS} دفتر (16 عملة؛ المستهدفة = الدفتر نفسه بلا الميم) ══", flush=True)
            per_book = {b: [] for b in BASKETS}
            big = BOOKS_DIR / f"random_books_FULL16_{design}_{w}.csv"
            fh = big.open("w", encoding="utf-8-sig", newline="")
            wr = csv.writer(fh)
            wr.writerow(["book", "symbol", "entry_time", "exit_time", "entry", "exit", "notional", "pnl", "reason", "stage", "bars_held"])
            for b in range(1, N_BOOKS + 1):
                rows16, fails = make_book(design, win, table16, FULL16, b)
                fail_total += fails
                ov = X.overlap_violations(rows16)
                overlap_total += ov
                if b <= 3:  # الاستقلال لكل عملة: توليد السلة المستهدفة مباشرة = حذف الميم من دفتر السلة الكاملة
                    rows13_direct, _ = make_book(design, win, tables["TARGET13"][w], TARGET13, b)
                    rows13_sub = [r for r in rows16 if r["symbol"] not in MEMES]
                    identical_subset_check &= (json.dumps(rows13_direct, sort_keys=True) == json.dumps(rows13_sub, sort_keys=True))
                for r in rows16:
                    wr.writerow([b, r["symbol"], r["entry_time"], r["exit_time"], r["entry_px"], r["exit_px"], r["notional_usd"],
                                 round(float(X.pnl_vec(r["entry_px"], r["exit_px"], r["notional_usd"], COST)), 4), r["reason"], 0, r["bars_held"]])
                if b <= 3:
                    pd.DataFrame([{"symbol": r["symbol"], "entry_time": r["entry_time"], "exit_time": r["exit_time"], "entry": r["entry_px"],
                                   "exit": r["exit_px"], "notional": r["notional_usd"], "pnl": round(float(X.pnl_vec(r["entry_px"], r["exit_px"], r["notional_usd"], COST)), 4),
                                   "reason": r["reason"], "stage": 0, "bars_held": r["bars_held"]} for r in rows16]
                                 ).to_csv(OUT / "samples" / f"trades_random_{design}_{w}_book{b}.csv", index=False, encoding="utf-8-sig")
                for bname, coins in BASKETS.items():
                    rows = rows16 if bname == "FULL16" else [r for r in rows16 if r["symbol"] not in MEMES]
                    ev = evaluate_raw(rows, win)
                    f_peak = S[bname]["peak"] / ev["peak"]
                    f_mean = S[bname]["avg_dep"] / ev["avg_dep"]
                    rec = {"book": b, "slices": ev["slices"], "peak_raw": round(ev["peak"], 2), "avg_dep_raw": round(ev["avg_dep"], 2),
                           "f_peak": round(f_peak, 6), "f_mean": round(f_mean, 6),
                           "net115_raw": round(ev["net115"], 2), "net130_raw": round(ev["net130"], 2),
                           "net115_peak": round(ev["net115"] * f_peak, 2), "net130_peak": round(ev["net130"] * f_peak, 2),
                           "net115_mean": round(ev["net115"] * f_mean, 2), "net130_mean": round(ev["net130"] * f_mean, 2),
                           "ret_pct_peak": round(100 * ev["net115"] * f_peak / S[bname]["peak"], 3),
                           "ret_pct_mean": round(100 * ev["net115"] * f_mean / S[bname]["avg_dep"], 3),
                           "dd_peak": round(ev["dd"] * f_peak, 2), "dd_mean": round(ev["dd"] * f_mean, 2),
                           "dd_pct_peak": round(100 * ev["dd"] * f_peak / S[bname]["peak"], 2),
                           "underwater_days": round(ev["underwater_days"], 1),
                           "max_cycle_notional_peak": round(ev["max_cycle_notional"] * f_peak, 2),
                           "max_cycle_notional_mean": round(ev["max_cycle_notional"] * f_mean, 2),
                           "overlap_violations": ov, "placement_failures": fails}
                    for s_ in coins:
                        rec[f"coin_{s_}"] = round(ev["per_coin"].get(s_, 0.0) * f_peak, 2)      # مساهمة بتسوية الذروة
                        rec[f"coinm_{s_}"] = round(ev["per_coin"].get(s_, 0.0) * f_mean, 2)     # وبتسوية المتوسط
                    per_book[bname].append(rec)
                if b % 250 == 0:
                    print(f"    {b}/{N_BOOKS}", flush=True)
            fh.close()
            results["determinism"][f"sha_random_books_FULL16_{design}_{w}"] = sha_file(big)
            for bname in BASKETS:
                df = pd.DataFrame(per_book[bname])
                summaries[(bname, design, w)] = df
                df.to_csv(OUT / f"books_{bname}_{design}_{w}.csv", index=False, encoding="utf-8-sig")
                s = S[bname]
                blk = {"n_books": int(len(df)), "peak_scaled_to": s["peak"], "avgdep_scaled_to": s["avg_dep"],
                       "peak_raw": X.dist(df.peak_raw.to_numpy()), "avg_dep_raw": X.dist(df.avg_dep_raw.to_numpy()),
                       "f_peak": X.dist(df.f_peak.to_numpy()), "f_mean": X.dist(df.f_mean.to_numpy()),
                       "underwater_days": X.dist(df.underwater_days.to_numpy()),
                       "placement_failures": int(df.placement_failures.sum()), "overlap_violations": int(df.overlap_violations.sum())}
                for scal in ("peak", "mean"):
                    for cost_tag, s_net in (("115", s["net115"]), ("130", s["net130"])):
                        v = df[f"net{cost_tag}_{scal}"].to_numpy()
                        blk[f"net{cost_tag}_{scal}"] = X.dist(v)
                        blk[f"pct_below_{cost_tag}_{scal}"] = X.pct_below(v, s_net)
                        blk[f"n_above_{cost_tag}_{scal}"] = int((v >= s_net).sum())
                    blk[f"ret_pct_{scal}"] = X.dist(df[f"ret_pct_{scal}"].to_numpy())
                    blk[f"dd_{scal}"] = X.dist(df[f"dd_{scal}"].to_numpy())
                    blk[f"pct_books_dd_smaller_than_strategy_{scal}"] = X.pct_below(-df[f"dd_{scal}"].to_numpy(), -s["dd"])
                    blk[f"max_cycle_notional_{scal}"] = X.dist(df[f"max_cycle_notional_{scal}"].to_numpy())
                    blk[f"books_exceeding_1000_per_cycle_{scal}"] = int((df[f"max_cycle_notional_{scal}"] > 1000 + 1e-6).sum())
                blk["pct_below_115_raw"] = X.pct_below(df.net115_raw.to_numpy(), s["net115"])
                blk["median_per_coin_peak"] = {c_: round(float(df[f"coin_{c_}"].median()), 2) for c_ in BASKETS[bname]}
                results["books"][f"{bname}_{design}_{w}"] = blk
                print(f"    {bname}: وسيط(ذروة) {blk['net115_peak']['median']}$ · فوق {100*blk['pct_below_115_peak']:.1f}% | "
                      f"وسيط(متوسط) {blk['net115_mean']['median']}$ · فوق {100*blk['pct_below_115_mean']:.1f}% | الاستراتيجية {s['net115']}$", flush=True)
    results["overlap_violations_total"] = overlap_total
    results["placement_failures_total"] = fail_total
    results["target13_equals_full16_minus_memes"] = identical_subset_check

    # ───── الشرط 6: حذف العملة الأعلى مساهمة ─────
    for bname in BASKETS:
        results["concentration"][bname] = {}
        for w in WINDOWS:
            s = results["strategy"][bname][w]
            pc = s["per_coin"]
            top = max(pc, key=pc.get)
            s_wo = round(s["net115"] - pc[top], 2)
            ent = {"top_coin": top, "top_coin_net": pc[top], "top_share_pct": round(100 * pc[top] / s["net115"], 1) if s["net115"] else None,
                   "strategy_net_without_top": s_wo}
            for design in ("A", "B"):
                df = summaries[(bname, design, w)]
                for scal, col in (("peak", "coin_"), ("mean", "coinm_")):
                    wo = (df[f"net115_{scal}"] - df[f"{col}{top}"]).to_numpy()
                    ent[f"{design}_{scal}_median_without_top"] = round(float(np.median(wo)), 2)
                    ent[f"{design}_{scal}_pct_below_without_top"] = X.pct_below(wo, s_wo)
            results["concentration"][bname][w] = ent

    # ───── معيار القبول ─────
    def judge(bname: str) -> dict:
        s = results["strategy"][bname]
        A = {w: results["books"][f"{bname}_A_{w}"] for w in WINDOWS}
        Bk = {w: results["books"][f"{bname}_B_{w}"] for w in WINDOWS}
        conc = results["concentration"][bname]
        c1 = all(s[w]["net115"] > 0 for w in WINDOWS)
        c2 = all(s[w]["net130"] > 0 for w in WINDOWS)
        c3 = all(s[w]["ret_pct_peak"] > 0 for w in WINDOWS)
        c4p = all(s[w]["net115"] > A[w]["net115_peak"]["median"] and s[w]["ret_pct_peak"] > A[w]["ret_pct_peak"]["median"] for w in WINDOWS)
        c5p = A["JUD"]["pct_below_115_peak"] >= 0.75
        c6p = all(conc[w]["strategy_net_without_top"] > conc[w]["A_peak_median_without_top"] for w in WINDOWS)
        c4m = all(s[w]["net115"] > A[w]["net115_mean"]["median"] and s[w]["ret_pct_avgdep"] > A[w]["ret_pct_mean"]["median"] for w in WINDOWS)
        c5m = A["JUD"]["pct_below_115_mean"] >= 0.75
        c6m = all(conc[w]["strategy_net_without_top"] > conc[w]["A_mean_median_without_top"] for w in WINDOWS)
        c7 = (overlap_total == 0 and fail_total <= 0.01 * N_BOOKS * 2 * sum(s[w]["cycles"] for w in WINDOWS))
        peak_pass = all([c1, c2, c3, c4p, c5p, c6p, c7])
        mean_pass = all([c1, c2, c3, c4m, c5m, c6m, c7])
        if peak_pass and mean_pass:
            verdict, cls = "يمرّ", None
        elif peak_pass != mean_pass:
            verdict, cls = "لا يمرّ", "حساسة لرأس المال (مرّت بتسوية واحدة فقط)"
        else:
            verdict, cls = "لا يمرّ", None
        return {"1_pos_0115": {"pass": c1, "SEL": s["SEL"]["net115"], "JUD": s["JUD"]["net115"]},
                "2_pos_0130": {"pass": c2, "SEL": s["SEL"]["net130"], "JUD": s["JUD"]["net130"]},
                "3_ret_pos": {"pass": c3, "SEL": s["SEL"]["ret_pct_peak"], "JUD": s["JUD"]["ret_pct_peak"]},
                "4_above_median": {"peak": c4p, "mean": c4m, "median_peak": {w: A[w]["net115_peak"]["median"] for w in WINDOWS},
                                   "median_mean": {w: A[w]["net115_mean"]["median"] for w in WINDOWS}},
                "5_above_75pct_JUD": {"peak": c5p, "mean": c5m, "pct_peak": A["JUD"]["pct_below_115_peak"], "pct_mean": A["JUD"]["pct_below_115_mean"],
                                      "pct_peak_SEL": A["SEL"]["pct_below_115_peak"], "pct_mean_SEL": A["SEL"]["pct_below_115_mean"],
                                      "B_pct_peak": Bk["JUD"]["pct_below_115_peak"], "B_pct_mean": Bk["JUD"]["pct_below_115_mean"]},
                "6_without_top": {"peak": c6p, "mean": c6m, **{w: conc[w] for w in WINDOWS}},
                "7_integrity": {"pass": c7, "overlap_violations": overlap_total, "placement_failures": fail_total},
                "pass_peak": peak_pass, "pass_mean": mean_pass, "verdict": verdict, "classification": cls}
    results["acceptance"] = {b: judge(b) for b in BASKETS}
    t, f = results["acceptance"]["TARGET13"], results["acceptance"]["FULL16"]
    final = t["verdict"]
    note = t["classification"]
    if t["verdict"] != "يمرّ" and f["verdict"] == "يمرّ":
        note = (note + " · " if note else "") + "إشارة خاصة بالأسواق السريعة أو بعملات الميم، وليست صالحة للسلة المستهدفة"
    results["final"] = {"verdict_target13": final, "classification": note, "verdict_full16_research": f["verdict"]}
    for b in BASKETS:
        a = results["acceptance"][b]
        print(f"  {b}: 1={a['1_pos_0115']['pass']} 2={a['2_pos_0130']['pass']} 3={a['3_ret_pos']['pass']} 4(ذروة/متوسط)={a['4_above_median']['peak']}/{a['4_above_median']['mean']} "
              f"5={a['5_above_75pct_JUD']['peak']}/{a['5_above_75pct_JUD']['mean']} ({a['5_above_75pct_JUD']['pct_peak']}/{a['5_above_75pct_JUD']['pct_mean']}) "
              f"6={a['6_without_top']['peak']}/{a['6_without_top']['mean']} 7={a['7_integrity']['pass']} ⇒ {a['verdict']} {a['classification'] or ''}", flush=True)
    print(f"  الحكم النهائي (المستهدفة): {final} {note or ''}", flush=True)

    # ───── الحارس والتتابع ─────
    guard_files = [OUT / f"trades_strategy_{b}_{w}.csv" for b in BASKETS for w in ("SEL", "JUD", "FULL")]
    guard_files += [BOOKS_DIR / f"random_books_FULL16_{d}_{w}.csv" for d in ("A", "B") for w in WINDOWS]
    guard_files += sorted((OUT / "samples").glob("*.csv"))
    for p in guard_files:
        line = X.guard(p)
        results["guard"].append(line)
        print("    " + line, flush=True)
    seq = subprocess.run([sys.executable, str(ROOT / "tools" / "position_sequencing_audit.py"), "--dir", str(OUT / "samples"), "--json"],
                         capture_output=True, text=True)
    (OUT / "sequencing_audit_samples.json").write_text(seq.stdout, encoding="utf-8")

    import pandas, numpy, pyarrow  # noqa
    results["env"] = {"date": "2026-09-27", "python": platform.python_version(), "pandas": pandas.__version__, "numpy": numpy.__version__,
                      "pyarrow": pyarrow.__version__, "platform": platform.platform(), "base_branch": "arena/l0063-random-control-fair-2026-09-27 @ ce130cd",
                      "NOVA_LC_V3": "1 عند القياس؛ 0 للنسخة القديمة", "n_books": N_BOOKS, "designs": ["A", "B"], "baskets": {k: list(v) for k, v in BASKETS.items()},
                      "memes_excluded": list(MEMES), "cost": {"base": COST, "stress": COST_130, "slippage": 0.0}, "seed_base": SEED_BASE}
    text = json.dumps(results, ensure_ascii=False, indent=2, default=str)
    (OUT / f"results_{pass_tag}.json").write_text(text, encoding="utf-8")
    if pass_tag == "pass1":
        (OUT / "results.json").write_text(text, encoding="utf-8")
        (OUT / "env_dump.txt").write_text(json.dumps(results["env"], ensure_ascii=False, indent=2), encoding="utf-8")
        (OUT / "guard_log.json").write_text(json.dumps(results["guard"], ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"اكتمل ({pass_tag}). دفاتر مولَّدة={2 * 2 * N_BOOKS} (× سلّتان) · تداخل={overlap_total} · فشل وضع={fail_total}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "pass1"))
