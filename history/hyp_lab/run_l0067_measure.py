#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0067 — المرحلة 2: المسح على الاختيار، التثبيت، الحكم، Walk-Forward، العشوائي، الشراء والاحتفاظ، البوابات.

    python3 run_l0067_measure.py pass1      (يكتب results.json)
    python3 run_l0067_measure.py pass2      (إعادة مستقلة للحتمية؛ سجلات recs_pass2)
قاعدة الاختيار مكتوبة مسبقًا في preregistration_l0067.json. لا يُقرأ أي رقم حكم قبل تثبيت الإعداد.
"""
from __future__ import annotations
import hashlib, json, math, pickle, sys, zlib
import numpy as np, pandas as pd
sys.path.insert(0, "/home/user/work/history/hyp_lab")
import l0067_common as K

TAG = sys.argv[1] if len(sys.argv) > 1 else "pass1"
RECDIR = K.CACHE / f"recs_{TAG}"
OUT = K.ROOT / "history/research/hyp_lab_out/L0067"
PRE = json.loads((OUT / "preregistration_l0067.json").read_text(encoding="utf-8"))
MS, CS, TLS = ("M0", "M1", "M2"), ("C0", "C1", "C2"), (None, 365, 180, 90)
CAPITAL, CAP = 13000.0, 1000.0
BAR = pd.Timedelta(hours=4)
N_BOOKS, SEED = 1000, 67
_R: dict = {}


def recs(m, tl, cut):
    name = f"{m}_{tl}_{'FULL' if cut is None or cut >= K.JUD[1] else cut.date()}.pkl"
    if name not in _R:
        _R[name] = pickle.load(open(RECDIR / name, "rb"))
    return _R[name]


def window_rows(m, tl, coins, s, e):
    """صفقات دخلت في [s,e) من تشغيل مقصوص عند e (المفتوح يُغلق نهاية-العينة)."""
    R = recs(m, tl, e)
    return [r for c in coins for r in K.rows_in(R[c], s, e)]


# ───────────────────────── الإطار الموحد والتقييم ─────────────────────────
_GRID: dict = {}


def grid(s, e):
    key = (s, e)
    if key not in _GRID:
        idx = pd.date_range(s, e, freq="4h", inclusive="left")
        close = {sym: K.h4(sym)["close"].reindex(idx).ffill().to_numpy(float) for sym in K.FULL16}
        _GRID[key] = (idx, close)
    return _GRID[key]


def evaluate(rows, s, e, shared: bool, capital=CAPITAL):
    idx, close = grid(s, e)
    n = len(idx)
    if not rows:
        return {"empty": True, "net115": 0.0, "net130": 0.0, "slices": 0, "cycles": 0}
    rows = sorted(rows, key=lambda r: (r["entry_time"], r["symbol"], r["stage"]))
    sym = np.array([r["symbol"] for r in rows])
    ep = np.array([r["entry_px"] for r in rows]); xp = np.array([r["exit_px"] for r in rows])
    no = np.array([r["notional_usd"] for r in rows])
    gi0 = np.clip(idx.searchsorted([pd.Timestamp(r["entry_time"]) for r in rows]), 0, n - 1)
    gi1 = np.clip(idx.searchsorted([pd.Timestamp(r["exit_time"]) for r in rows]), 0, n - 1)
    f115 = K.pnl(ep, xp, 1.0, K.COST); f130 = K.pnl(ep, xp, 1.0, K.COST_130)
    scale = np.ones(len(rows)); log = {"scaled_bars": 0, "scaled_slices": 0, "requested_usd": 0.0, "cut_usd": 0.0,
                                       "cap_violations": 0, "min_cash": capital, "overdraft": 0}
    if shared:  # تتابع النقد المشترك: الدخول (على الافتتاح) قبل الخروج (على الإغلاق) في الشمعة نفسها — محافظ
        cash = capital
        open_coin = {}
        ev = {}
        for k in range(len(rows)):
            ev.setdefault(gi0[k], [[], []])[0].append(k)
            ev.setdefault(gi1[k], [[], []])[1].append(k)
        for t in sorted(ev):
            ins, outs = ev[t]
            req = sum(no[k] for k in ins)
            if req > 0:
                sc = min(1.0, cash / req) if cash > 0 else 0.0
                log["requested_usd"] += req
                if sc < 1.0 - 1e-12:
                    log["scaled_bars"] += 1; log["scaled_slices"] += len(ins); log["cut_usd"] += req * (1 - sc)
                for k in ins:
                    scale[k] = sc
                    open_coin[sym[k]] = open_coin.get(sym[k], 0.0) + no[k] * sc
                    if open_coin[sym[k]] > CAP + 1e-6:
                        log["cap_violations"] += 1
                    cash -= no[k] * sc
                if cash < -1e-6:
                    log["overdraft"] += 1
                log["min_cash"] = min(log["min_cash"], cash)
            for k in outs:
                cash += no[k] * scale[k] * (1 + f115[k])
                open_coin[sym[k]] -= no[k] * scale[k]
    p115 = f115 * no * scale; p130 = f130 * no * scale
    dep = np.zeros(n + 1); np.add.at(dep, gi0, no * scale); np.add.at(dep, gi1, -no * scale)
    dep = np.cumsum(dep)[:n]
    eq = np.zeros(n)
    for k in range(len(rows)):
        a, b = gi0[k], gi1[k]
        if b > a:
            eq[a:b] += K.pnl(ep[k], close[sym[k]][a:b], no[k] * scale[k], K.COST)
        eq[b:] += p115[k]
    run_max = np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]
    dd = eq - run_max
    longest = cur = 0
    for u in dd < -1e-9:
        cur = cur + 1 if u else 0; longest = max(longest, cur)
    cyc = K.cycles([dict(r, _p=float(p)) for r, p in zip(rows, p115)])
    cyc_p = [sum(x["_p"] for x in g) for g in cyc]
    months = pd.Series(p115, index=[pd.Timestamp(r["exit_time"]).strftime("%Y-%m") for r in rows]).groupby(level=0).sum()
    per_coin = {str(c): float(p115[sym == c].sum()) for c in np.unique(sym)}
    peak = float(dep.max()); years = (e - s).days / 365.25
    held_days = float(((gi1 - gi0) * no * scale).sum() * 4 / 24 / max(no.dot(scale), 1e-9))
    fees = float((no * scale * (K.COST + K.COST * (1 + f115))).sum())
    net = float(p115.sum())
    best_c = max(per_coin.values()) if per_coin else 0.0
    return {"empty": False, "net115": net, "net130": float(p130.sum()), "slices": len(rows), "cycles": len(cyc),
            "avg_slice": net / len(rows), "median_slice": float(np.median(p115)), "avg_cycle": float(np.mean(cyc_p)),
            "median_cycle": float(np.median(cyc_p)), "cycle_wins": int(sum(p > 0 for p in cyc_p)),
            "peak_dep": peak, "avg_dep": float(dep.mean()), "dd": float(dd.min()),
            "dd_pct_peak": 100 * float(dd.min()) / peak if peak else 0.0, "dd_pct_capital": 100 * float(dd.min()) / capital,
            "underwater_days": longest * 4 / 24, "per_coin": per_coin,
            "top_coin_share": (best_c / net) if net > 0 else None,
            "best_month": float(months.max()), "net_ex_best_month": net - float(months.max()),
            "per_month": {k: float(v) for k, v in months.items()},
            "years": years, "annual_net": net / years, "monthly_net": net / years / 12,
            "per_1000_annual": 1000 * net / years / (capital if shared else max(peak, 1e-9)),
            "held_days_weighted": held_days, "fees_annual": fees / years,
            "ret_pct_capital": 100 * net / capital, "ret_pct_peak": 100 * net / peak if peak else 0.0,
            "shared_log": log if shared else None, "_p115": p115, "_rows": rows, "_eq": eq}


def strip(d):
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items() if not k.startswith("_")}


# ───────────────────────── اختيار العملات ─────────────────────────
def coin_sets(m, tl, s, e):
    """C0/C1/C2 من فترة الاختيار [s,e) وحدها، كلفة 0.130%."""
    C0 = list(K.TARGET13)
    C1, C2, why = [], [], {}
    for c in K.TARGET13:
        fr = K.h4(c)
        first = fr.index[0]
        rows = window_rows(m, tl, [c], s, e)
        rows0 = window_rows("M0", None, [c], s, e)
        months = (e - max(first, s)).days / 30.44 if first < e else 0
        ok_data = months >= PRE["C1"]["min_months_in_selection"] and len(fr[(fr.index >= s) & (fr.index < e)]) > 0
        n_cyc0 = len(K.cycles(rows0))
        if not ok_data or n_cyc0 < PRE["C1"]["min_cycles_M0_in_selection"]:
            why[c] = f"C0 فقط: بيانات {months:.1f} شهرًا · دورات M0 {n_cyc0}"
            continue
        C1.append(c)
        if not rows:
            why[c] = "C1: لا صفقات بهذا الإعداد في الاختيار"; continue
        ev = evaluate(rows, s, e, shared=False)
        f130 = K.pnl([r["entry_px"] for r in rows], [r["exit_px"] for r in rows], [r["notional_usd"] for r in rows], K.COST_130)
        net130 = float(f130.sum())
        cyc = K.cycles([dict(r, _p=float(p)) for r, p in zip(rows, f130)])
        cp = sorted((sum(x["_p"] for x in g) for g in cyc), reverse=True)
        conds = {"net>0": net130 > 0, "avg>0": net130 / len(rows) > 0, "dd<=400": ev["dd"] >= -PRE["C2"]["max_coin_drawdown_usd"],
                 "ex_best_cycle>=0": (net130 - cp[0]) >= 0 if cp else False}
        if all(conds.values()):
            C2.append(c); why[c] = f"C2: صافي {net130:.0f}$ · هبوط {ev['dd']:.0f}$ · بلا أفضل دورة {net130 - cp[0]:.0f}$"
        else:
            why[c] = "C1: فشل " + ",".join(k for k, v in conds.items() if not v) + f" (صافي {net130:.0f}$)"
    return {"C0": C0, "C1": C1, "C2": C2}, why


# ───────────────────────── المسح والتثبيت ─────────────────────────
def sweep(s, e):
    res = {}
    sets_cache = {}
    for m in MS:
        for tl in TLS:
            sets, why = coin_sets(m, tl, s, e)
            sets_cache[(m, tl)] = (sets, why)
            for c in CS:
                rows = window_rows(m, tl, sets[c], s, e)
                ev = evaluate(rows, s, e, shared=True)
                elig = (not ev["empty"]) and ev["net115"] > 0 and ev["net130"] > 0 and ev["avg_slice"] > 0 and ev["dd_pct_peak"] >= -50
                res[(m, c, tl)] = {"net130": ev["net130"], "net115": ev["net115"], "eligible": bool(elig),
                                   "dd_pct_peak": ev.get("dd_pct_peak"), "cycles": ev["cycles"], "coins": sets[c]}
    for (m, c, tl), v in res.items():
        nb = [res[(m, c, tl)]["net130"]]
        for dim, seq, cur in ((0, MS, m), (1, CS, c), (2, TLS, tl)):
            i = seq.index(cur)
            for j in (i - 1, i + 1):
                if 0 <= j < len(seq):
                    key = [m, c, tl]; key[dim] = seq[j]
                    nb.append(res[tuple(key)]["net130"])
        v["plateau"] = float(np.median(nb)); v["n_neighbors"] = len(nb) - 1
    order = lambda k: (MS.index(k[0]), CS.index(k[1]), TLS.index(k[2]))
    elig = [k for k, v in res.items() if v["eligible"]]
    if elig:
        best = max(elig, key=lambda k: (round(res[k]["plateau"], 6), -order(k)[0], -order(k)[1], -order(k)[2]))
        why_pick = "أعلى هضبة جيران بين المؤهلة"
    else:
        best = ("M0", "C0", None); why_pick = "لا إعداد مؤهل ⇒ المرجع"
    top = max(res, key=lambda k: res[k]["net130"])
    return res, best, why_pick, top, sets_cache


def key_s(k):
    return f"{k[0]}·{k[1]}·{'بلا حد' if k[2] is None else str(k[2]) + 'ي'}"


# ───────────────────────── العشوائي ─────────────────────────
def cycle_table(rows):
    out = {}
    for g in K.cycles(rows):
        t0 = min(pd.Timestamp(r["entry_time"]) for r in g); t1 = max(pd.Timestamp(r["exit_time"]) for r in g)
        out.setdefault(g[0]["symbol"], []).append((max(int((t1 - t0) / BAR), 1), float(sum(r["notional_usd"] for r in g))))
    return out


def random_books(rows, s, e, wcode):
    table = cycle_table(rows)
    res = {}
    for design in ("A", "B"):
        nets_p, nets_a, n130_p, peaks, fails = [], [], [], [], 0
        for b in range(N_BOOKS):
            brows = []
            for sym, pairs in table.items():
                fr = K.h4(sym); fr = fr[(fr.index >= s) & (fr.index < e)]
                ln = len(fr)
                if ln < 3:
                    continue
                rng = np.random.default_rng(np.random.SeedSequence([SEED, wcode, ord(design), b, zlib.crc32(sym.encode())]))
                pp = pairs if design == "A" else [(max(int(np.median([d for d, _ in pairs])), 1), float(np.mean([x for _, x in pairs])))] * len(pairs)
                taken = []
                op, cl, ix = fr["open"].to_numpy(float), fr["close"].to_numpy(float), fr.index
                for _ in range(len(pp)):
                    for _t in range(200):
                        d, no = pp[int(rng.integers(0, len(pp)))]
                        hi = ln - 2 - d
                        if hi < 0:
                            continue
                        i = int(rng.integers(0, hi + 1)); a, bb = i + 1, i + 1 + d
                        if all(a > tb or bb < ta for ta, tb in taken):
                            taken.append((a, bb))
                            brows.append({"symbol": sym, "entry_time": ix[a].isoformat(), "exit_time": ix[bb].isoformat(),
                                          "entry_px": op[a], "exit_px": cl[bb], "notional_usd": no, "stage": 0, "entry_bar": a})
                            break
                    else:
                        fails += 1
            if not brows:
                nets_p.append(0.0); nets_a.append(0.0); n130_p.append(0.0); peaks.append(0.0); continue
            ev = evaluate(brows, s, e, shared=False)
            nets_p.append(ev["net115"] / ev["peak_dep"]); nets_a.append(ev["net115"] / ev["avg_dep"])
            n130_p.append(ev["net130"] / ev["peak_dep"]); peaks.append(ev["peak_dep"])
        res[design] = {"ret_per_peak": np.array(nets_p), "ret_per_avg": np.array(nets_a), "ret130_per_peak": np.array(n130_p), "fails": fails}
    return res


def vs_random(ev, rb):
    out = {}
    for d, r in rb.items():
        sp, sa = ev["net115"] / ev["peak_dep"], ev["net115"] / ev["avg_dep"]
        s130 = ev["net130"] / ev["peak_dep"]
        out[d] = {"median_usd_peak": float(np.median(r["ret_per_peak"]) * ev["peak_dep"]),
                  "median_usd_avg": float(np.median(r["ret_per_avg"]) * ev["avg_dep"]),
                  "median_usd_peak_130": float(np.median(r["ret130_per_peak"]) * ev["peak_dep"]),
                  "pct_below_peak": float(100 * np.mean(r["ret_per_peak"] < sp)),
                  "pct_below_avg": float(100 * np.mean(r["ret_per_avg"] < sa)),
                  "pct_below_peak_130": float(100 * np.mean(r["ret130_per_peak"] < s130)), "fails": r["fails"]}
    return out


def buy_hold(coins, s, e):
    tot, per = 0.0, {}
    for c in coins:
        fr = K.h4(c); fr = fr[(fr.index >= s) & (fr.index < e)]
        if len(fr) < 2:
            continue
        per[c] = float(K.pnl(fr["open"].iloc[0], fr["close"].iloc[-1], 1000.0, K.COST))
        tot += per[c]
    return {"net": tot, "deployed": 1000.0 * len(per), "per_coin": per}


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(100 * (c - h), 1), round(100 * (c + h), 1)]


# ───────────────────────── التشغيل ─────────────────────────
def main():
    R = {"pass": TAG, "prereg_sha": hashlib.sha256((OUT / "preregistration_l0067.json").read_bytes()).hexdigest()[:16]}
    # (1) المسح على الاختيار الأساسي وحده ثم التثبيت
    res, best, why_pick, top, sets_cache = sweep(*K.SEL)
    vals = [v["net130"] for v in res.values()]
    R["sweep_SEL"] = {key_s(k): {kk: (round(vv, 2) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in res.items()}
    R["fixed"] = {"config": key_s(best), "why": why_pick, "top_single": key_s(top), "top_single_net130": round(res[top]["net130"], 2),
                  "median_all_36": round(float(np.median(vals)), 2), "eligible_count": sum(v["eligible"] for v in res.values()),
                  "fixed_plateau": round(res[best]["plateau"], 2), "fixed_net130_SEL": round(res[best]["net130"], 2)}
    m, c, tl = best
    sets, why = sets_cache[(m, tl)]
    coins = sets[c]
    R["coins_fixed"] = coins; R["coin_reasons_SEL"] = why
    pd.DataFrame([{"config": key_s(k), **{kk: vv for kk, vv in v.items() if kk != "coins"}, "n_coins": len(v["coins"])} for k, v in res.items()]
                 ).to_csv(OUT / f"sweep_SEL_{TAG}.csv", index=False, encoding="utf-8-sig")
    print("مثبت:", key_s(best), why_pick, "· القمة المنفردة", key_s(top), "· العملات", len(coins), flush=True)

    # (2) الاختيار والحكم: المثبت مقابل المرجع L0064، بالمقاييس الثلاثة
    blocks = {}
    for label, (mm, cc, tt, co) in {"L0064": ("M0", "C0", None, list(K.TARGET13)), "fixed": (m, c, tl, coins)}.items():
        blocks[label] = {}
        for w, (s, e) in (("SEL", K.SEL), ("JUD", K.JUD)):
            rows = window_rows(mm, tt, co, s, e)
            ind = evaluate(rows, s, e, shared=False)
            sh = evaluate(rows, s, e, shared=True)
            rb = random_books(rows, s, e, 1 if w == "SEL" else 2)
            blocks[label][w] = {"independent": strip(ind), "shared": strip(sh), "shared_capped": "مطابقة للمشتركة: سقف 1000$ للعملة لا يُتجاوز بالبناء (أوزان الشرائح مجموعها 1.0)",
                                "random_vs_shared": vs_random(sh, rb), "random_vs_independent": vs_random(ind, rb),
                                "buy_hold": buy_hold(co, s, e)}
            if label == "fixed":
                K.save_trades(OUT / f"trades_fixed_TARGET13_{w}.csv", sh["_rows"])
                blocks[label][w]["_ev"] = sh
            print(label, w, "مستقل", round(ind["net115"], 2), "مشترك", round(sh["net115"], 2), "/", round(sh["net130"], 2),
                  "هبوط%", round(sh["dd_pct_peak"], 1), "تحت القمة", round(sh["underwater_days"]), flush=True)
    # السلة الكاملة 16 للبحث فقط (المرجع والمثبت بقائمة C0+الميم)
    R["research_FULL16"] = {}
    for label, (mm, tt) in {"L0064": ("M0", None), "fixed_M_TL": (m, tl)}.items():
        R["research_FULL16"][label] = {w: round(evaluate(window_rows(mm, tt, K.FULL16, s, e), s, e, shared=True, capital=16000)["net115"], 2)
                                       for w, (s, e) in (("SEL", K.SEL), ("JUD", K.JUD))}

    # (3) Walk-Forward
    wf = []
    for i, (name, ts_, te_) in enumerate(K.WF):
        r_w, b_w, why_w, top_w, sc_w = sweep(K.SEL[0], ts_)
        sets_w, _ = sc_w[(b_w[0], b_w[2])]
        co_w = sets_w[b_w[1]]
        rows = window_rows(b_w[0], b_w[2], co_w, ts_, te_)
        ev = evaluate(rows, ts_, te_, shared=True)
        ref = evaluate(window_rows("M0", None, list(K.TARGET13), ts_, te_), ts_, te_, shared=True)
        wf.append({"window": name, "test": f"{ts_.date()}→{te_.date()}", "fixed": key_s(b_w), "coins": len(co_w),
                   "net115": round(ev["net115"], 2), "net130": round(ev["net130"], 2), "cycles": ev["cycles"],
                   "dd_pct_peak": round(ev.get("dd_pct_peak", 0.0), 2), "underwater_days": round(ev.get("underwater_days", 0.0), 1),
                   "L0064_net115": round(ref["net115"], 2), "buy_hold": round(buy_hold(co_w, ts_, te_)["net"], 2)})
        if not ev["empty"]:
            K.save_trades(OUT / f"trades_wf_{name}.csv", ev["_rows"])
        print("WF", wf[-1], flush=True)
    R["walk_forward"] = wf

    # (4) تقرير العملات (المثبت، M/TL المثبتان، كل عملات المستهدفة تظهر)
    coins_rep = {}
    for cn in K.TARGET13:
        d = {"in_C0": True, "in_C1": cn in sets["C1"], "in_C2": cn in sets["C2"], "reason": why.get(cn)}
        for w, (s, e) in (("SEL", K.SEL), ("JUD", K.JUD)):
            rows = window_rows(m, tl, [cn], s, e)
            ev = evaluate(rows, s, e, shared=False)
            if ev["empty"]:
                d[w] = {"cycles": 0, "net115": 0.0}; continue
            d[w] = {"cycles": ev["cycles"], "wins": ev["cycle_wins"], "losses": ev["cycles"] - ev["cycle_wins"],
                    "win_rate": round(100 * ev["cycle_wins"] / ev["cycles"], 1), "wilson95": wilson(ev["cycle_wins"], ev["cycles"]),
                    "net115": round(ev["net115"], 2), "net130": round(ev["net130"], 2), "avg_cycle": round(ev["avg_cycle"], 2),
                    "median_cycle": round(ev["median_cycle"], 2), "dd": round(ev["dd"], 2), "underwater_days": round(ev["underwater_days"], 1)}
        fj = blocks["fixed"]["JUD"]["shared"]
        d["share_of_basket_JUD"] = round(fj["per_coin"].get(cn, 0.0) / fj["net115"], 3) if fj["net115"] > 0 and cn in coins else None
        d["shared_pnl_JUD"] = round(fj["per_coin"].get(cn, 0.0), 2) if cn in coins else None
        sel_ok = d["SEL"].get("net115", 0) > 0; jud_ok = d["JUD"].get("net115", 0) > 0
        n_all = d["SEL"].get("cycles", 0) + d["JUD"].get("cycles", 0)
        d["class"] = ("غير كافية البيانات" if not d["in_C1"] or n_all < 6 else
                      "مناسبة" if sel_ok and jud_ok and cn in coins else "واعدة" if (sel_ok or jud_ok) and (d["JUD"].get("net115", 0) + d["SEL"].get("net115", 0)) > 0 else "غير مناسبة")
        coins_rep[cn] = d
    R["coins"] = coins_rep

    # (5) البوابات
    fs, fj = blocks["fixed"]["SEL"], blocks["fixed"]["JUD"]
    S, J = fs["shared"], fj["shared"]
    wfn = [x["net115"] for x in wf]
    pos = sum(1 for x in wfn if x > 0)
    bh_gap = J["net115"] - fj["buy_hold"]["net"]
    g = {
        "1_net_pos_SEL_JUD": S["net115"] > 0 and J["net115"] > 0,
        "2_net_pos_both_costs": min(S["net115"], S["net130"], J["net115"], J["net130"]) > 0,
        "3_beats_random_median": all(x["random_vs_shared"][d]["median_usd_peak"] < x["shared"]["net115"] for x in (fs, fj) for d in ("A", "B")),
        "4_not_materially_worse_than_BH": bh_gap >= -0.25 * max(J["peak_dep"], 1.0),
        "5_avg_trade_pos_JUD": J["avg_slice"] > 0,
        "6_dd_JUD_le35_WF_le50": J["dd_pct_peak"] >= -35 and all(x["dd_pct_peak"] >= -50 for x in wf),
        "7_underwater_JUD_le540_WF_le720": J["underwater_days"] <= 540 and all(x["underwater_days"] <= 720 for x in wf),
        "8_top_coin_le35pct": J["top_coin_share"] is not None and J["top_coin_share"] <= 0.35,
        "9_WF_pos_ge60pct_and_median_pos": pos >= 0.6 * len(wf) and float(np.median(wfn)) > 0,
        "10_not_one_month_or_window": J["net_ex_best_month"] > 0 and (sum(wfn) - max(wfn)) > 0,
        "11_every_coin_reported": len(coins_rep) == 13,
        "12_annual_net_pos": J["annual_net"] > 0,
        "13_stress_cost_shared_ok": J["net130"] > 0 and S["net130"] > 0,
        "14_leak_fill_seq_determinism": None,  # يُملأ من فحوص منفصلة
        "15_memes_excluded": not any(x in coins for x in K.MEMES),
    }
    R["gates"] = g
    R["blocks"] = {lab: {w: {k: v for k, v in blk.items() if k != "_ev"} for w, blk in d.items()} for lab, d in blocks.items()}
    R["economics"] = {"per_1000_annual_JUD": round(J["per_1000_annual"], 2), "monthly_net_JUD": round(J["monthly_net"], 2),
                      "annual_net_JUD": round(J["annual_net"], 2), "held_days_weighted_JUD": round(J["held_days_weighted"], 1),
                      "fees_annual_JUD": round(J["fees_annual"], 2), "max_monthly_opex_covered": round(max(J["monthly_net"], 0.0), 2),
                      "independent_minus_shared_JUD": round(fj["independent"]["net115"] - J["net115"], 2),
                      "L0064_shared_JUD": round(blocks["L0064"]["JUD"]["shared"]["net115"], 2)}
    txt = json.dumps(R, ensure_ascii=False, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    (OUT / f"results_{TAG}.json").write_text(txt, encoding="utf-8")
    if TAG == "pass1":
        (OUT / "results.json").write_text(txt, encoding="utf-8")
    print("البوابات:", {k: v for k, v in g.items()}, flush=True)


if __name__ == "__main__":
    main()
