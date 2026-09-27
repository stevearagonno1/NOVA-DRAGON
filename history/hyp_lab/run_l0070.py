#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0070 — Walk-Forward للعائلات المسجلة، المقارنات، رأس المال المشترك، العملات، البوابات. الاستعمال: run_l0070.py pass1|pass2"""
from __future__ import annotations
import hashlib, json, math, sys, zlib
import numpy as np, pandas as pd
sys.path.insert(0, "/home/user/work/history/hyp_lab")
import l0070_core as C
TAG = sys.argv[1] if len(sys.argv) > 1 else "pass1"
RULE = {"prereg": True}
ROOT = __import__("pathlib").Path("/home/user/work")
OUT = ROOT / "history/research/hyp_lab_out/L0070"
PRE = json.loads((OUT / "preregistration_l0070.json").read_text(encoding="utf-8"))
BASE = PRE["base_config"]
T = lambda s: pd.Timestamp(s, tz="UTC")
WF_START, WF_END = T("2021-09-01"), T("2026-08-31")
FIRST_TEST_OK = T("2022-06-01")
CAP0 = 2000.0
SIZES = (2000, 4000, 6500, 10000, 13000)

# ───────── العائلات ─────────
def key(c): return "|".join(f"{k}={c[k]}" for k in ("L", "method", "K", "market", "trend", "rebalance", "exit", "weights", "liq_q"))
FAM = {}
core = []
for meth in ("simple", "exp", "voladj"):
    for L in (20, 65, 150, 200):
        for K_ in (2, 3, 5):
            core.append({**BASE, "method": meth, "L": L, "K": K_})
for K_ in (2, 3, 5):
    core.append({**BASE, "method": "blend", "L": 65, "K": K_})
FAM["core"] = core
FAM["market"] = [{**BASE, "market": x} for x in ("always", "btc200", "btc200_50", "breadth50")]
FAM["trend"] = [{**BASE, "trend": x} for x in ("c50", "c100", "c200", "e50_200", "posmom")]
FAM["rebalance"] = [{**BASE, "rebalance": x} for x in (7, 14, 28)]
FAM["exit"] = [{**BASE, "exit": x} for x in ("base", "H5", "H20", "H65", "weak10")]
FAM["weights"] = [{**BASE, "weights": x} for x in ("equal", "iv40", "iv30", "iv20")]
FAM["liquidity"] = [{**BASE, "liq_q": x} for x in (25, 50, 75)]
assert all(len(v) <= PRE["families"]["declared_limit_per_family"] for v in FAM.values())

def neighbors(fam, c):
    if fam == "core":
        out = []
        if c["method"] == "blend":
            ks = [2, 3, 5]; i = ks.index(c["K"])
            return [key({**c, "K": ks[x]}) for x in (i - 1, i + 1) if 0 <= x < 3]
        Ls, ks = [20, 65, 150, 200], [2, 3, 5]
        a, b = Ls.index(c["L"]), ks.index(c["K"])
        for x in (a - 1, a + 1):
            if 0 <= x < 4: out.append(key({**c, "L": Ls[x]}))
        for x in (b - 1, b + 1):
            if 0 <= x < 3: out.append(key({**c, "K": ks[x]}))
        return out
    mem = [key(x) for x in FAM[fam]]; i = mem.index(key(c))
    return [mem[x] for x in (i - 1, i + 1) if 0 <= x < len(mem)]

# ───────── تشغيل كل الإعدادات ─────────
P = C.Panel(C.TARGET13)
IDX = P.idx
ALLC = {}
for fam, lst in FAM.items():
    for c in lst: ALLC[key(c)] = c
RUN = {}
for k, c in ALLC.items():
    tr, pnl, orders, dep = C.run(P, c, CAP0)
    RUN[k] = {"trades": tr, "daily": {L: pnl[L].sum(1) for L in C.LAYERS}, "coin_daily": pnl["measured"], "orders": orders, "dep": dep}
print("إعدادات:", len(ALLC), flush=True)

def win_mask(s, e): return (IDX >= s) & (IDX < e)
def net(k, s, e, L="measured"): return float(RUN[k]["daily"][L][win_mask(s, e)].sum())
def trades_in(k, s, e):
    return [t for t in RUN[k]["trades"] if s <= IDX[t["entry_i"]] < e]
def dd_of(series):
    cum = np.cumsum(series); rm = np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:]
    dd = cum - rm; longest = cur = 0
    for u in dd < -1e-9:
        cur = cur + 1 if u else 0; longest = max(longest, cur)
    return float(dd.min()) if len(dd) else 0.0, longest

def train_stats(k, s, e):
    n_ = net(k, s, e); tr = trades_in(k, s, e)
    pn = [t["measured"] for t in tr]
    dd, _ = dd_of(RUN[k]["daily"]["measured"][win_mask(s, e)])
    return {"net": n_, "avg": (sum(pn) / len(pn)) if pn else 0.0, "max_share": (max(pn) / n_) if pn and n_ > 0 else None, "dd": dd, "n": len(pn)}

def windows(tm, vm, sm, step):
    out = []; a = WF_START
    while True:
        tr_e = a + pd.DateOffset(months=tm); va_e = tr_e + pd.DateOffset(months=vm); te_e = va_e + pd.DateOffset(months=sm)
        if te_e > WF_END + pd.Timedelta(days=1): break
        if va_e >= FIRST_TEST_OK:
            out.append((a, tr_e, va_e, min(te_e, WF_END)))
        a = a + pd.DateOffset(months=step)
    return out

def select(fam, a, tr_e, va_e, rule="prereg"):
    res = {}
    for c in FAM[fam]:
        k = key(c); st = train_stats(k, a, tr_e)
        ok = st["net"] > 0 and st["avg"] > 0 and st["n"] > 0 and (rule == "A1" or (st["max_share"] is not None and st["max_share"] <= 0.40)) and st["dd"] >= -0.35 * CAP0
        res[k] = {"train": st["net"], "ok_train": ok, "val": net(k, tr_e, va_e)}
    for k in res:
        nb = [res[x]["train"] for x in neighbors(fam, ALLC[k]) if x in res]
        res[k]["nb_med"] = float(np.median(nb)) if nb else 0.0
        res[k]["eligible"] = res[k]["ok_train"] and res[k]["val"] > 0 and res[k]["nb_med"] > 0
    el = [k for k in res if res[k]["eligible"]]
    best = max(el, key=lambda k: res[k]["train"]) if el else None
    return best, res

def buy_hold_basket(s, e, cap):
    m = win_mask(s, e); ii = np.where(m)[0]
    if len(ii) < 2: return 0.0, {}
    per = {}
    avail = [j for j in range(len(P.coins)) if np.isfinite(P.o[ii[0], j]) and P.age[ii[0], j] >= 1]
    for j in avail:
        cl = P.c[ii, j]; last = cl[np.isfinite(cl)][-1]
        per[P.coins[j]] = ((last / P.o[ii[0], j]) * 0.9987 / 1.0013 - 1) * cap / len(avail)
    return float(sum(per.values())), per

def random_books(k, s, e, wcode, nb=1000):
    """نفس عدد المراكز وأوزانها عند كل يوم إعادة توازن للإعداد المقفل، بعملات عشوائية من المؤهلة؛ كلفة مقاسة على الدوران."""
    c = ALLC[k]; m = np.where(win_mask(s, e))[0]
    if len(m) < 2: return np.zeros(nb)
    days_from = ((IDX - C.ANCHOR).days).to_numpy(); rbd = [i for i in m if days_from[i] >= 0 and days_from[i] % c["rebalance"] == 0]
    if not rbd or rbd[0] != m[0]: rbd = [m[0]] + rbd
    held = RUN[k]["dep"]
    # تعرض الإعداد عند كل يوم (بالدولار) — العشوائي يطابقه
    out = np.zeros(nb)
    elig_any = (P.age >= 250) & np.isfinite(P.c)
    for b in range(nb):
        rng = np.random.default_rng(np.random.SeedSequence([70, wcode, b]))
        tot = 0.0
        for q, i0 in enumerate(rbd):
            i1 = rbd[q + 1] if q + 1 < len(rbd) else m[-1] + 1
            exposure = held[i0]
            if exposure <= 0 or i1 - i0 < 1: continue
            npos = max(1, int(round(exposure / (CAP0 / c["K"]))))
            cand = np.where(elig_any[i0])[0]
            if len(cand) == 0: continue
            pick = rng.choice(cand, size=min(npos, len(cand)), replace=False)
            for j in pick:
                o0 = P.o[min(i0 + 1, len(IDX) - 1), j]; cl = P.c[min(i1, len(IDX) - 1), j]
                if not (np.isfinite(o0) and np.isfinite(cl)): continue
                tot += ((cl / o0) * (1 - 0.0013) / (1 + 0.0013) - 1) * exposure / len(pick)
        out[b] = tot
    return out

L0064 = None
def l0064_windows(W):
    """مرجع تاريخي فقط: كود V3 الحالي (L0068 replayer)، 20$، كلفة مقاسة، مقطع عند نهاية النافذة."""
    global L0064
    import l0067_common as K
    import l0068_replayer as RP
    import l0068_sim as S
    h4s = {s: K.h4(s) for s in C.TARGET13}
    mk = S.market_by_day(h4s, list(C.TARGET13)); CN = {s: S.Coin(s, h4s[s], mk) for s in C.TARGET13}
    rows = []
    for s in C.TARGET13:
        for r in RP.replay(h4s[s], s):
            rows.append({"symbol": s, "stage": r["stage"], "entry_bar": r["entry_bar"], "exit_bar": r["exit_bar"], "entry_ref": float(r["entry_px"]), "exit_px": float(r["exit_px"])})
    out = []
    for (_, _, va_e, te_e) in W:
        seg = []
        for r in rows:
            cn = CN[r["symbol"]]; t0 = cn.idx[r["entry_bar"]]
            if not (va_e <= t0 < te_e): continue
            q = dict(r)
            if cn.idx[r["exit_bar"]] >= te_e:
                j = int(cn.idx.searchsorted(te_e)) - 1; q["exit_bar"] = j; q["exit_px"] = float(cn.c[j])
            seg.append(q)
        out.append(round(float(S.pnl(seg, CN, "intended").sum()), 2) if seg else 0.0)
    return out

def wilson(k, n, z=1.96):
    if n == 0: return None
    ph = k / n; d = 1 + z * z / n; c = (ph + z * z / (2 * n)) / d; h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return [round(100 * (c - h), 1), round(100 * (c + h), 1)]

def path(fam, label, spec, with_extras=False, rule="prereg"):
    W = windows(spec["train_m"], spec["val_m"], spec["test_m"], spec["step_m"])
    recs, prev = [], None
    oos_daily = {L: np.zeros(len(IDX)) for L in C.LAYERS}; coin_oos = np.zeros(len(P.coins)); oos_trades = []
    ref = l0064_windows(W) if with_extras else [None] * len(W)
    for wi, (a, tr_e, va_e, te_e) in enumerate(W):
        best, res = select(fam, a, tr_e, va_e, rule)
        row = {"window": f"{label}{wi + 1:02d}", "train": f"{a.date()}→{tr_e.date()}", "val": f"{tr_e.date()}→{va_e.date()}", "test": f"{va_e.date()}→{te_e.date()}",
               "fixed": best, "eligible": int(sum(r["eligible"] for r in res.values()))}
        m = win_mask(va_e, te_e); i0 = int(np.where(m)[0][0])
        switch = 0.0
        if best:
            if best != prev:
                switch = 2 * 0.0013 * float(RUN[best]["dep"][i0 - 1]) if i0 > 0 else 0.0
            for L in C.LAYERS:
                row[f"test_{L}"] = round(float(RUN[best]["daily"][L][m].sum()) - switch, 2)
                oos_daily[L][m] += RUN[best]["daily"][L][m]
                oos_daily[L][i0] -= switch
            coin_oos += RUN[best]["coin_daily"][m].sum(0)
            tt = trades_in(best, va_e, te_e); oos_trades += [{**t, "window": row["window"], "cfg": best} for t in tt]
            row.update({"train_net": round(res[best]["train"], 2), "val_net": round(res[best]["val"], 2), "trades": len(tt), "switch_cost": round(switch, 2)})
            nb = neighbors(fam, ALLC[best]); row["neighbors_test"] = {x: round(net(x, va_e, te_e), 2) for x in nb}
        else:
            for L in C.LAYERS: row[f"test_{L}"] = 0.0
            row["trades"] = 0
        prev = best
        if with_extras:
            bh, per = buy_hold_basket(va_e, te_e, CAP0); row["buy_hold_basket"] = round(bh, 2); row["buy_hold_coin"] = {k: round(v * len(per), 2) for k, v in per.items()}
            row["L0064_raw_ref"] = ref[wi]
            if best:
                rb = random_books(best, va_e, te_e, wi + (0 if label == "P" else 100))
                row["random_median"] = round(float(np.median(rb)), 2); row["random_pct_below"] = round(100 * float((rb < row["test_measured"]).mean()), 1)
            row["cash"] = 0.0
        recs.append(row)
        print(fam, row["window"], row["test"], best, row["test_measured"], row["trades"], flush=True)
    t = np.array([r["test_measured"] for r in recs]); tot = float(t.sum())
    s0 = T(recs[0]["test"].split("→")[0]); e0 = T(recs[-1]["test"].split("→")[1]); span = win_mask(s0, e0)
    dd, uw = dd_of(oos_daily["measured"][span])
    pc = {P.coins[j]: round(float(coin_oos[j]), 2) for j in range(len(P.coins))}
    yrs = (e0 - s0).days / 365.25
    avg_tr = (sum(x["measured"] for x in oos_trades) / len(oos_trades)) if oos_trades else None
    summ = {"windows": len(recs), "positive": int((t > 0).sum()), "pct_positive": round(100 * float((t > 0).mean()), 1), "median": round(float(np.median(t)), 2),
            "worst": min(recs, key=lambda r: r["test_measured"])["window"], "worst_net": round(float(t.min()), 2),
            "best": max(recs, key=lambda r: r["test_measured"])["window"], "best_net": round(float(t.max()), 2),
            "net": {L: round(sum(r[f"test_{L}"] for r in recs), 2) for L in C.LAYERS}, "trades": len(oos_trades), "avg_trade": round(avg_tr, 3) if avg_tr is not None else None,
            "best_window_share": round(float(t.max() / tot), 3) if tot > 0 else None,
            "top_coin": max(pc, key=pc.get), "top_coin_share": round(max(pc.values()) / tot, 3) if tot > 0 else None, "coins_positive": int(sum(v > 0 for v in pc.values())),
            "per_coin": pc, "dd_usd": round(dd, 2), "dd_pct_capital": round(100 * dd / CAP0, 2), "underwater_days": uw,
            "years": round(yrs, 2), "monthly": round(tot / yrs / 12, 2), "annual": round(tot / yrs, 2), "per_1000_annual": round(tot / yrs / CAP0 * 1000, 2),
            "no_trade_windows": int(sum(r["fixed"] is None for r in recs)),
            "selected": pd.Series([r["fixed"] for r in recs]).value_counts(dropna=False).to_dict()}
    nb_all = {}
    for r in recs:
        for x, v in r.get("neighbors_test", {}).items(): nb_all[x] = nb_all.get(x, 0.0) + v
    summ["neighbors_oos_sum"] = {k: round(v, 2) for k, v in nb_all.items()}
    summ["neighbors_not_all_losing"] = bool(any(v > 0 for v in nb_all.values())) if nb_all else False
    if with_extras:
        summ["buy_hold_basket_sum"] = round(sum(r["buy_hold_basket"] for r in recs), 2)
        summ["L0064_raw_sum"] = round(sum(r["L0064_raw_ref"] for r in recs), 2)
        summ["windows_beating_random_median"] = int(sum(1 for r in recs if "random_median" in r and r["test_measured"] > r["random_median"]))
    return recs, summ, oos_trades, (s0, e0)

def replay_sequence(recs, cap):
    """نفس تسلسل الإعدادات المقفلة على رأس مال آخر (إعادة تشغيل كاملة لكل إعداد عند ذلك الحجم)."""
    tot, rej, minc, conc, bmin, execu, dep_sum, days = 0.0, 0, float("inf"), 0, 0, 0, 0.0, 0
    cache = {}
    for r in recs:
        k = r["fixed"]
        if not k: continue
        if k not in cache: cache[k] = C.run(P, ALLC[k], cap)
        tr, pnl, o, dep = cache[k]
        a, b = [T(x) for x in r["test"].split("→")]; m = win_mask(a, b)
        tot += float(pnl["measured"].sum(1)[m].sum())
        tt = [t for t in tr if a <= IDX[t["entry_i"]] < b]
        execu += sum(t["units"] for t in tt); dep_sum += float(dep[m].sum()); days += int(m.sum())
    for k, (tr, pnl, o, dep) in cache.items():
        rej += o["rejected_units"]; minc = min(minc, o["min_cash"]); conc = max(conc, o["max_concurrent"]); bmin += o["below_min"]
    return {"capital": cap, "net_measured": round(tot, 2), "rejected_units_in_selected_runs": rej, "below_min_orders": bmin, "min_cash": round(minc, 2) if cache else cap,
            "max_concurrent": conc, "units_entered_oos": execu, "avg_deployed_oos": round(dep_sum / days, 2) if days else 0.0,
            "unused_cash_pct": round(100 * (1 - (dep_sum / days) / cap), 1) if days else 100.0}

def coin_report(recs, oos_trades, fam_summ, span):
    rep = {}
    for j, sym in enumerate(P.coins):
        tt = [t for t in oos_trades if t["coin"] == sym]
        inwin = [r["window"] for r in recs if any(t["window"] == r["window"] for t in tt)]
        rk = []  # الترتيب التاريخي للأساس (قوة 65 يومًا) في أيام الاختبار
        S_ = P.strength("simple", 65); m = win_mask(*span)
        ranks = pd.DataFrame(S_).rank(axis=1, ascending=False).to_numpy()[m, j]
        d = {"windows_entered": inwin, "median_rank_65d_in_oos": float(np.nanmedian(ranks)) if np.isfinite(ranks).any() else None,
             "trades": len(tt), "orders_units": int(sum(t["units"] for t in tt))}
        if not tt:
            d["class"] = "غير كافية البيانات"; rep[sym] = d; continue
        pm = np.array([t["measured"] for t in tt]); pg = np.array([t["units"] * C.UNIT * (t["exit_px"] / t["entry_px"] - 1) for t in tt])
        cum = np.cumsum(pm); dd = float((cum - np.maximum.accumulate(np.concatenate([[0], cum]))[1:]).min())
        streak = cur = 0
        for x in pm:
            cur = cur + 1 if x <= 0 else 0; streak = max(streak, cur)
        w = int((pm > 0).sum())
        cls = ("غير كافية البيانات" if len(tt) < 8 else "مناسبة" if pm.sum() > 0 and pm.mean() > 0 and w / len(tt) >= 0.5 else "واعدة" if pm.sum() > 0 else "غير مناسبة")
        d.update({"wins": w, "losses": len(tt) - w, "win_prob_hist_pct": round(100 * w / len(tt), 1), "wilson95": wilson(w, len(tt)),
                  "net_gross": round(float(pg.sum()), 2), "net_measured": round(float(pm.sum()), 2), "avg": round(float(pm.mean()), 2), "median": round(float(np.median(pm)), 2),
                  "dd": round(dd, 2), "longest_losing_streak": streak, "oos_pnl_attribution": fam_summ["per_coin"][sym], "class": cls})
        rep[sym] = d
    return rep

def main():
    res = {"pass": TAG, "prereg_sha": hashlib.sha256((OUT / "preregistration_l0070.json").read_bytes()).hexdigest()[:16],
           "n_configs": len(ALLC), "families": {f: len(v) for f, v in FAM.items()}}
    res["full_period_context"] = {k: {"net_measured": round(float(RUN[k]["daily"]["measured"].sum()), 2), "trades": len(RUN[k]["trades"])} for k in ALLC}
    res["wf"] = {}; keep = {}
    for lab, spec in (("primary", PRE["walk_forward"]["primary"]), ("sensitive", PRE["walk_forward"]["sensitive"])):
        res["wf"][lab] = {}
        for fam in FAM:
            for rule in ("prereg", "A1"):
                recs, summ, oos, span = path(fam, "P" if lab == "primary" else "S", spec, with_extras=(fam == "core"), rule=rule)
                res["wf"][lab][f"{fam}|{rule}"] = {"summary": summ, "windows": recs}; keep[(lab, fam, rule)] = (recs, oos, span, summ)
                pd.DataFrame(recs).to_csv(OUT / f"wf_{lab}_{fam}_{rule}_{TAG}.csv", index=False, encoding="utf-8-sig")
    res["by_rule"] = {}
    for rule in ("prereg", "A1"):
        res_r = {}
        recs, oos, span, summ = keep[("primary", "core", rule)]
        res_r["shared_capital"] = {cap: replay_sequence(recs, cap) for cap in SIZES}
        res_r["coins"] = coin_report(recs, oos, summ, span)
        # أثر المرشح والحجم لكل عملة: الأساس مقابل «دائمًا» ومقابل «equal»
        kb = key(BASE); ka = key({**BASE, "market": "always"}); ke = key({**BASE, "weights": "equal"})
        m = win_mask(*span)
        for j, sym in enumerate(P.coins):
            res_r["coins"][sym]["market_filter_effect"] = round(float(RUN[kb]["coin_daily"][m, j].sum() - RUN[ka]["coin_daily"][m, j].sum()), 2)
            res_r["coins"][sym]["vol_sizing_effect"] = round(float(RUN[kb]["coin_daily"][m, j].sum() - RUN[ke]["coin_daily"][m, j].sum()), 2)
        # السلة الكاملة 16: بحث منفصل (نواة بإعداد الأساس فقط، الفترة الكاملة)
        P16 = C.Panel(C.FULL16); tr16, p16, o16, _ = C.run(P16, BASE, CAP0)
        res_r["full16_research_base"] = {"net_measured": round(float(p16["measured"].sum()), 2), "per_coin": {P16.coins[j]: round(float(p16["measured"][:, j].sum()), 2) for j in range(len(P16.coins))},
                                       "note": "بحث منفصل؛ لا يثبت السلة الأساسية"}
        # الاقتصاد
        s = summ; yrs = s["years"]
        tt = oos
        res_r["economics"] = {"per_1000_annual": s["per_1000_annual"], "shared_2000_monthly": s["monthly"], "shared_2000_annual": s["annual"],
                            "orders_units_per_year": round(sum(t["units"] for t in tt) * 2 / yrs, 1), "round_trips_per_year": round(len(tt) / yrs, 1),
                            "trading_cost_per_year_measured": round((s["net"]["c115"] * 0 + sum(t["units"] * C.UNIT * 2 * 0.0013 for t in tt)) / yrs, 2),
                            "opex_covered_max_per_month": round(max(s["monthly"], 0), 2),
                            "days_in_trade_median": float(np.median([t["exit_i"] - t["entry_i"] for t in tt])) if tt else None,
                            "unused_cash_pct": res_r["shared_capital"][2000]["unused_cash_pct"]}
        # هل قلل تقليل التداول الربح بعد الكلفة؟ عائلة إعادة التوازن (الفترة الكاملة)
        res_r["economics"]["rebalance_family_full_period"] = {x: {"net_measured": res["full_period_context"][key({**BASE, "rebalance": x})]["net_measured"],
                                                                "trades": res["full_period_context"][key({**BASE, "rebalance": x})]["trades"]} for x in (7, 14, 28)}
        # البوابات (عائلة النواة، الرئيسي)
        sc = res_r["shared_capital"][2000]
        g = {"1_median_pos": s["median"] > 0, "2_ge60pct": s["pct_positive"] >= 60, "3_pos_base_and_mid": s["net"]["measured"] > 0 and s["net"]["stress_mid"] > 0,
             "4_avg_trade_pos": (s["avg_trade"] or 0) > 0, "5_best_window_le40": s["best_window_share"] is not None and s["best_window_share"] <= 0.40,
             "6_top_coin_le35": s["top_coin_share"] is not None and s["top_coin_share"] <= 0.35, "7_dd_le35": s["dd_pct_capital"] >= -35,
             "8_uw_le540": s["underwater_days"] <= 540, "9_monthly_pos": s["monthly"] > 0, "10_ge3_coins": s["coins_positive"] >= 3, "11_no_memes": True,
             "12_shared_capital_clean": all(v["min_cash"] >= 0 for v in res_r["shared_capital"].values()),
             "13_checks": "انظر checks_l0070.json", "14_pos_stress_high": s["net"]["stress_high"] > 0, "15_neighbors": s["neighbors_not_all_losing"]}
        res_r["gates_core_primary"] = g
        res_r["gates_failed"] = [k for k, v in g.items() if v is False]
        print("GATES failed", rule, res_r["gates_failed"], flush=True)
        res["by_rule"][rule] = res_r
    recs, oos, span, summ = keep[("primary", "core", "A1")]
    if TAG == "pass1":
        rows = [{"symbol": t["coin"], "entry_time": IDX[t["entry_i"]].isoformat(), "exit_time": IDX[t["exit_i"]].isoformat(), "entry": t["entry_px"], "exit": t["exit_px"],
                 "units": t["units"], "reason": t["reason"], "window": t["window"], "cfg": t["cfg"]} for t in oos]
        pd.DataFrame(rows).to_csv(OUT / "trades_oos_core_primary.csv", index=False, encoding="utf-8-sig")
    (OUT / f"results_l0070_{TAG}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("تم", TAG, json.dumps({k: v for k, v in summ.items() if k not in ("per_coin", "neighbors_oos_sum", "selected")}, ensure_ascii=False))

if __name__ == "__main__":
    main()
