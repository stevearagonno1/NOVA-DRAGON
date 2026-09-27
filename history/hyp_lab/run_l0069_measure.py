#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0069 — إعادة القياس المصححة: المسارات A/B/C/D، سلم الكلفة، SEL/JUD/FULL، Walk-Forward بلا اختيار،
رأس المال المشترك بخمسة أحجام، غلاف المخاطر، تقرير العملات، البوابات. الاستعمال: run_l0069_measure.py pass1|pass2"""
from __future__ import annotations
import hashlib, json, math, sys, zlib
import numpy as np, pandas as pd
sys.path.insert(0, "/home/user/work/history/hyp_lab")
import l0067_common as K
import l0068_replayer as RP
import l0068_sim as S
TAG = sys.argv[1] if len(sys.argv) > 1 else "pass1"
OUT = K.ROOT / "history/research/hyp_lab_out/L0069"
PRE = json.loads((OUT / "preregistration_l0069.json").read_text(encoding="utf-8"))
COINS = list(K.TARGET13); T = K.T
START, END = T("2021-09-01"), T("2026-08-31")
SIZES = (2000, 4000, 6500, 10000, 13000); ORDER = 20.0
LADDER = {"c115": "c115", "measured": "intended", "stress_mid": "s10", "stress_high": "s30"}
h4s = {s: K.h4(s) for s in COINS}
CN = {s: S.Coin(s, h4s[s], S.market_by_day(h4s, COINS)) for s in COINS} if False else None
MKT = S.market_by_day(h4s, COINS)
CN = {s: S.Coin(s, h4s[s], MKT) for s in COINS}
ATRP = {}
for s in COINS:  # ATR14%(4h) Wilder — لوقف الصفقة الموثق
    fr = h4s[s]; tr_ = pd.concat([fr.high - fr.low, (fr.high - fr.close.shift()).abs(), (fr.low - fr.close.shift()).abs()], axis=1).max(axis=1)
    ATRP[s] = (tr_.ewm(alpha=1 / 14, adjust=False).mean() / fr.close).to_numpy()


def from_rp(recs, sym, keep_notional=False):
    return [{"symbol": sym, "stage": r["stage"], "entry_bar": r["entry_bar"], "exit_bar": r["exit_bar"], "entry_ref": float(r["entry_px"]),
             "exit_px": float(r["exit_px"]), "reason": r["reason"], "signal_bar": r["signal_bar"],
             **({"notional": r["notional_usd"]} if keep_notional else {})} for r in recs]


def run_version(ctx_text: bool, gate: bool, end=None):
    out = []
    for s in COINS:
        fr = h4s[s] if end is None else h4s[s][h4s[s].index < end]
        out += from_rp(RP.replay(fr, s, gate=gate, ctx_extra_lag=ctx_text), s, keep_notional=True)
    return out


def wrap(rows, stop: bool, H: int):
    """غلاف الصفقة: وقف صلب موثق + أفق H يومًا. لا يغير الدخول."""
    out = []
    for r in rows:
        cn = CN[r["symbol"]]; e = r["entry_bar"]; q = dict(r)
        lim = cn.idx[e] + pd.Timedelta(days=H)
        sp = min(max(1.15 * np.nan_to_num(ATRP[r["symbol"]][max(e - 1, 0)], nan=0.01), 0.003), 0.030)
        lvl = r["entry_ref"] * (1 - sp)
        for j in range(e, r["exit_bar"] + 1):
            if j > e and cn.idx[j] >= lim:
                q.update(exit_bar=j, exit_px=float(cn.o[j]), reason="أفق-%dي" % H); break
            if stop and cn.l[j] <= lvl:
                q.update(exit_bar=j, exit_px=float(min(cn.o[j], lvl)) if j > e else float(lvl), reason="وقف-صفقة"); break
        out.append(q)
    return out


def in_win(rows, s, e):
    return [r for r in rows if s <= CN[r["symbol"]].idx[r["entry_bar"]] < e]


def seg(rows, s, e):
    out = []
    for r in in_win(rows, s, e):
        cn = CN[r["symbol"]]; q = dict(r)
        if cn.idx[r["exit_bar"]] >= e:
            j = int(cn.idx.searchsorted(e)) - 1
            q["exit_bar"] = j; q["exit_px"] = float(cn.c[j]); q["reason"] = "قطع-المقطع"
        out.append(q)
    return out


def ladder(rows, size=ORDER):
    return {k: round(float(S.pnl(rows, CN, v, size).sum()), 2) if rows else 0.0 for k, v in LADDER.items()}


def research_size_net(rows):  # أوزان البحث 150–300$ بكلفة 0.115% (للمقارنة فقط)
    if not rows: return 0.0
    ep = np.array([r["entry_ref"] for r in rows]); xp = np.array([r["exit_px"] for r in rows]); no = np.array([r["notional"] for r in rows])
    return round(float((((xp / ep) * (1 - 0.00115) - 1.00115) / 1.00115 * no).sum()), 2)


def mult_sample(rows):
    m = {"entry": {1: 0, 2: 0, 3: 0}, "exit": {1: 0, 2: 0, 3: 0}, "examples": []}
    for r in rows:
        cn = CN[r["symbol"]]
        for side, b in (("entry", r["entry_bar"]), ("exit", r["exit_bar"])):
            v = float(np.nan_to_num(cn.vr[max(b - 1, 0)], nan=0.0)); k = int(S.slip_mult(v))
            m[side][k] += 1
            if k > 1 and len(m["examples"]) < 6:
                m["examples"].append({"symbol": r["symbol"], "side": side, "bar_time": cn.idx[b].isoformat(), "VR_prev_bar": round(v, 3), "mult": k, "slip_pct": 0.03 * k})
    return m


def windows(train_m, val_m, test_m, step_m):
    out = []; a = START
    while True:
        tr_e = a + pd.DateOffset(months=train_m); va_e = tr_e + pd.DateOffset(months=val_m); te_e = va_e + pd.DateOffset(months=test_m)
        if te_e > END + pd.Timedelta(days=1): break
        out.append((a, tr_e, va_e, min(te_e, END))); a = a + pd.DateOffset(months=step_m)
    return out


def buy_hold(s, e):
    tot = 0.0
    for sym in COINS:
        cn = CN[sym]; ii = np.where((cn.idx >= s) & (cn.idx < e))[0]
        if len(ii) < 2: continue
        tot += (((cn.c[ii[-1]] / cn.o[ii[0]]) * 0.9987 - 1.0013) / 1.0013) * ORDER
    return tot


def random_books(rows, s, e, wcode, nb=1000):
    by = {}
    for r in sorted(rows, key=lambda r: (r["symbol"], r["entry_bar"], r["stage"])):
        by.setdefault(r["symbol"], []).append(r)
    tab = {}
    for sym, rr in by.items():
        cur = []; cyc = []
        for r in rr:
            if r["stage"] == 0 and cur: cyc.append(cur); cur = []
            cur.append(r)
        if cur: cyc.append(cur)
        tab[sym] = [(max(max(x["exit_bar"] for x in g) - min(x["entry_bar"] for x in g), 1), len(g)) for g in cyc]
    nets = []
    for b in range(nb):
        tot = 0.0
        for sym, pairs in tab.items():
            cn = CN[sym]; ii = np.where((cn.idx >= s) & (cn.idx < e))[0]
            if len(ii) < 3: continue
            rng = np.random.default_rng(np.random.SeedSequence([69, wcode, b, zlib.crc32(sym.encode())]))
            for d, k in pairs:
                hi = len(ii) - 2 - d
                if hi < 0: continue
                a = ii[0] + 1 + int(rng.integers(0, hi + 1)); x = a + d
                ep = cn.o[a] * (1 + 0.0003 * float(S.slip_mult(np.nan_to_num(cn.vr[a - 1]))))
                xp = cn.c[x] * (1 - 0.0003 * float(S.slip_mult(np.nan_to_num(cn.vr[x - 1]))))
                tot += (((xp / ep) * 0.999 - 1.001) / 1.001) * ORDER * k
        nets.append(tot)
    return np.array(nets)


def portfolio(rows, capital, wrapper=False, layer="intended"):
    """محفظة مشتركة بشبكة 4h. wrapper=True يطبق الحد اليومي −3% والقاطع −25% (نص قواعد الحي)."""
    p = S.pnl(rows, CN, layer) if rows else np.zeros(0)
    grid = pd.DatetimeIndex(sorted(set().union(*[set(CN[s].idx) for s in COINS])))
    gpos = {s: grid.get_indexer(CN[s].idx) for s in COINS}
    ent, ext = {}, {}
    for k, r in enumerate(rows):
        ent.setdefault(int(gpos[r["symbol"]][r["entry_bar"]]), []).append(k)
        ext.setdefault(int(gpos[r["symbol"]][r["exit_bar"]]), []).append(k)
    close_on_grid = {s: pd.Series(CN[s].c, index=CN[s].idx).reindex(grid).ffill().to_numpy() for s in COINS}
    open_on_grid = {s: pd.Series(CN[s].o, index=CN[s].idx).reindex(grid).to_numpy() for s in COINS}
    cash = float(capital); openk = set(); taken = np.zeros(len(rows), bool); real = np.zeros(len(rows)); rej = 0; blocked_day = 0; blocked_halt = 0
    minc = cash; peak_eq = cash; day0 = None; day_eq = cash; day_block = False; halted = False; trip = False; breaker_time = None; daily_hits = 0
    eq_curve = np.zeros(len(grid)); dep_curve = np.zeros(len(grid)); forced = 0; conc = 0
    for gi, t in enumerate(grid):
        if day0 is None or t.normalize() != day0:
            day0 = t.normalize(); day_block = False; day_eq = eq_curve[gi - 1] if gi else cash
        if trip:  # إغلاق الكل على افتتاح هذه الشمعة
            for k in list(openk):
                r = rows[k]; px = open_on_grid[r["symbol"]][gi]
                if not np.isfinite(px): px = close_on_grid[r["symbol"]][gi - 1]
                q = dict(r); q["exit_px"] = float(px)
                real[k] = float(S.pnl([q], CN, layer)[0]); cash += ORDER + real[k]; openk.discard(k); forced += 1
            trip = False; halted = True
        for k in sorted(ent.get(gi, []), key=lambda k: rows[k]["symbol"]):
            if halted and wrapper: blocked_halt += 1; continue
            if day_block and wrapper: blocked_day += 1; continue
            if cash >= ORDER - 1e-9:
                cash -= ORDER; taken[k] = True; openk.add(k); minc = min(minc, cash)
            else:
                rej += 1
        for k in ext.get(gi, []):
            if k in openk:
                real[k] = p[k]; cash += ORDER + p[k]; openk.discard(k)
        mv = sum(ORDER * close_on_grid[rows[k]["symbol"]][gi] / rows[k]["entry_ref"] for k in openk)
        eq = cash + mv; eq_curve[gi] = eq; dep_curve[gi] = ORDER * len(openk); conc = max(conc, len(openk)); minc = min(minc, cash)
        peak_eq = max(peak_eq, eq)
        if wrapper and not halted:
            if not day_block and eq <= day_eq * 0.97:
                day_block = True; daily_hits += 1
            if eq <= peak_eq * 0.75:
                trip = True; breaker_time = t.isoformat()
    rm = np.maximum.accumulate(eq_curve); dd = eq_curve - rm; longest = cur = 0
    for u in dd < -1e-9:
        cur = cur + 1 if u else 0; longest = max(longest, cur)
    peak_dep = float(dep_curve.max())
    return {"capital": capital, "net": round(float(real[taken].sum()), 2), "taken": int(taken.sum()), "rejected": rej,
            "blocked_daily": blocked_day, "blocked_breaker": blocked_halt, "daily_limit_hits": daily_hits, "breaker_trip": breaker_time,
            "forced_closes": forced, "min_cash": round(minc, 2), "cash_never_negative": bool(minc >= -1e-9),
            "dd_usd": round(float(dd.min()), 2), "dd_pct_capital": round(100 * float(dd.min()) / capital, 2),
            "dd_pct_peak_deployed": round(100 * float(dd.min()) / peak_dep, 2) if peak_dep else 0.0,
            "underwater_days": round(longest * 4 / 24, 1), "peak_deployed": peak_dep, "max_concurrent_orders": conc,
            "avg_deployed": round(float(dep_curve.mean()), 2)}


def wilson(k, n, z=1.96):
    if n == 0: return None
    ph = k / n; d = 1 + z * z / n; c = (ph + z * z / (2 * n)) / d; h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return [round(100 * (c - h), 1), round(100 * (c + h), 1)]


def cycles(rows):
    by = {}
    for r in sorted(rows, key=lambda r: (r["symbol"], r["entry_bar"], r["stage"])):
        by.setdefault(r["symbol"], []).append(r)
    n = 0
    for rr in by.values():
        n += sum(1 for r in rr if r["stage"] == 0)
    return n


def wf(rows_full, spec, label):
    W = windows(spec["train_m"], spec["val_m"], spec["test_m"], spec["step_m"])
    recs, oos = [], []
    for wi, (a, tr_e, va_e, te_e) in enumerate(W):
        te = seg(rows_full, va_e, te_e); tr_ = seg(rows_full, a, tr_e); va = seg(rows_full, tr_e, va_e)
        row = {"window": f"{label}{wi + 1:02d}", "test": f"{va_e.date()}→{te_e.date()}",
               "train_measured": ladder(tr_)["measured"], "val_measured": ladder(va)["measured"], "orders": len(te), **{f"test_{k}": v for k, v in ladder(te).items()},
               "buy_hold": round(buy_hold(va_e, te_e), 2)}
        recs.append(row); oos += te
    t = np.array([r["test_measured"] for r in recs]); net = float(t.sum())
    pc = {s: float(S.pnl([r for r in oos if r["symbol"] == s], CN, "intended").sum()) if any(r["symbol"] == s for r in oos) else 0.0 for s in COINS}
    return recs, oos, {"windows": len(recs), "positive": int((t > 0).sum()), "pct_positive": round(100 * float((t > 0).mean()), 1),
                       "median": round(float(np.median(t)), 2), "worst": min(recs, key=lambda r: r["test_measured"])["window"], "worst_net": round(float(t.min()), 2),
                       "best": max(recs, key=lambda r: r["test_measured"])["window"], "best_net": round(float(t.max()), 2),
                       "net_measured": round(net, 2), "net_stress_high": round(sum(r["test_stress_high"] for r in recs), 2),
                       "best_window_share": round(float(t.max() / net), 3) if net > 0 else None,
                       "top_coin": max(pc, key=pc.get), "top_coin_share": round(max(pc.values()) / net, 3) if net > 0 else None,
                       "coins_positive": int(sum(v > 0 for v in pc.values())), "per_coin": {k: round(v, 2) for k, v in pc.items()},
                       "buy_hold_sum": round(sum(r["buy_hold"] for r in recs), 2), "orders": len(oos)}


def coin_report(oos, sel_rows, jud_rows, wrapped_oos=None, port_rej=None):
    rep = {}
    for sym in COINS:
        rr = [r for r in oos if r["symbol"] == sym]
        base = {"orders_oos": len(rr), "cycles_oos": cycles(rr),
                "SEL_measured": round(float(S.pnl([r for r in sel_rows if r["symbol"] == sym], CN, "intended").sum()), 2) if any(r["symbol"] == sym for r in sel_rows) else 0.0,
                "JUD_measured": round(float(S.pnl([r for r in jud_rows if r["symbol"] == sym], CN, "intended").sum()), 2) if any(r["symbol"] == sym for r in jud_rows) else 0.0}
        if not rr:
            rep[sym] = {**base, "class": "غير كافية البيانات"}; continue
        pc = S.pnl(rr, CN, "intended"); p115 = S.pnl(rr, CN, "c115"); p30 = S.pnl(rr, CN, "s30")
        cum = np.cumsum(pc); dd = float((cum - np.maximum.accumulate(np.concatenate([[0], cum]))[1:]).min())
        streak = cur = 0
        for x in pc:
            cur = cur + 1 if x <= 0 else 0; streak = max(streak, cur)
        w = int((pc > 0).sum())
        cls = ("غير كافية البيانات" if len(rr) < 8 else "مناسبة" if pc.sum() > 0 and pc.mean() > 0 and w / len(rr) >= 0.5 else
               "واعدة" if pc.sum() > 0 else "غير مناسبة")
        d = {**base, "wins": w, "losses": len(rr) - w, "win_prob_hist_pct": round(100 * w / len(rr), 1), "wilson95": wilson(w, len(rr)),
             "net_oos_measured": round(float(pc.sum()), 2), "avg": round(float(pc.mean()), 3), "median": round(float(np.median(pc)), 3),
             "dd": round(dd, 2), "longest_losing_streak": streak, "cost_effect_c115_to_s30": round(float(p30.sum() - p115.sum()), 2), "class": cls}
        if wrapped_oos is not None:
            ww = [r for r in wrapped_oos if r["symbol"] == sym]
            d["wrapper_effect"] = round(float(S.pnl(ww, CN, "intended").sum() - pc.sum()), 2) if ww else 0.0
        if port_rej is not None:
            d["shared_capital_rejected"] = port_rej.get(sym, 0)
        rep[sym] = d
    return rep


def days_in_trade(rows):
    if not rows: return {}
    d = np.array([(CN[r["symbol"]].idx[r["exit_bar"]] - CN[r["symbol"]].idx[r["entry_bar"]]).total_seconds() / 86400 for r in rows])
    return {"median": round(float(np.median(d)), 1), "p75": round(float(np.percentile(d, 75)), 1), "max": round(float(d.max()), 1),
            "share_ge_90d": round(float((d >= 90).mean()), 3), "order_days_total": round(float(d.sum()), 1)}


def main():
    res = {"pass": TAG, "prereg_sha": hashlib.sha256((OUT / "preregistration_l0069.json").read_bytes()).hexdigest()[:16]}
    V = {}
    specs = {"A_current_code": (False, True), "B_V3_corrected": (True, True), "C_V2_corrected": (True, False)}
    for name, (ctx, gate) in specs.items():
        full = run_version(ctx, gate); cut = run_version(ctx, gate, end=K.SEL[1])
        V[name] = {"FULL": full, "SEL": in_win(cut, *K.SEL), "JUD": in_win(full, *K.JUD), "ALL": in_win(full, START, END)}
    for dn, (stop, H) in {"D_stop_H90": (True, 90), "D_stop_H180": (True, 180), "D_nostop_H90": (False, 90), "D_nostop_H180": (False, 180)}.items():
        b = V["B_V3_corrected"]
        V[dn] = {k: wrap(b[k], stop, H) for k in ("FULL", "SEL", "JUD", "ALL")}
    # ── A: إعادة إنتاج خط الأساس ──
    A = V["A_current_code"]
    res["A_reproduction"] = {"SEL_research_size_c115": research_size_net(A["SEL"]), "JUD_research_size_c115": research_size_net(A["JUD"]),
                             "expected_L0064": {"SEL": 113.22, "JUD": 1314.38}}
    res["A_reproduction"]["reproduced"] = bool(abs(res["A_reproduction"]["SEL_research_size_c115"] - 113.22) < 0.01 and abs(res["A_reproduction"]["JUD_research_size_c115"] - 1314.38) < 0.01)
    print("A:", res["A_reproduction"], flush=True)
    # ── الجدول الرئيسي: كل نسخة × فترة × سلم الكلفة (20$ لكل أمر) ──
    tab = {}
    for name, v in V.items():
        tab[name] = {}
        for per in ("SEL", "JUD", "ALL"):
            rows = v[per]; lad = ladder(rows)
            tab[name][per] = {"orders": len(rows), "cycles": cycles(rows), **lad,
                              "avg_order_measured": round(lad["measured"] / len(rows), 4) if rows else None,
                              "ret_pct_of_1000_book_per_coin_avg": round(100 * lad["measured"] / (1000 * 13), 3),
                              "win_rate": round(100 * float((S.pnl(rows, CN, "intended") > 0).mean()), 1) if rows else None}
            if "notional" in (rows[0] if rows else {}):
                tab[name][per]["research_size_c115"] = research_size_net(rows)
        print(name, {p: (tab[name][p]["measured"], tab[name][p]["stress_high"], tab[name][p]["orders"]) for p in ("SEL", "JUD", "ALL")}, flush=True)
    res["table"] = tab
    # D1 معزولًا (V3 عند 20$ والكلفة المقاسة): الكود مقابل النص
    res["D1_isolated_20usd_measured"] = {"code_V3": {p: ladder(V["A_current_code"][p])["measured"] for p in ("SEL", "JUD", "ALL")},
                                         "text_V3": {p: tab["B_V3_corrected"][p]["measured"] for p in ("SEL", "JUD", "ALL")}}
    # D2: عينة المضاعف
    res["D2_multiplier_sample"] = {n: mult_sample(V[n]["ALL"]) for n in ("B_V3_corrected", "C_V2_corrected")}
    # D3: هل غيّر الحجم النتيجة أم الدولار فقط؟
    res["D3_size"] = {n: {per: {"research_size_c115": research_size_net(V[n][per]), "20usd_c115": ladder(V[n][per])["c115"],
                                "research_avg_ret_pct_weighted": round(100 * research_size_net(V[n][per]) / sum(r["notional"] for r in V[n][per]), 4) if V[n][per] else None,
                                "20usd_avg_ret_pct": round(100 * ladder(V[n][per])["c115"] / (ORDER * len(V[n][per])), 4) if V[n][per] else None}
                          for per in ("SEL", "JUD")} for n in ("A_current_code", "B_V3_corrected", "C_V2_corrected")}
    # D6: الأفق
    res["D6_holding"] = {n: days_in_trade(V[n]["ALL"]) for n in V}
    res["D6_wrapper_exit_reasons"] = {n: pd.Series([r["reason"] for r in V[n]["ALL"]]).value_counts().to_dict() for n in V if n.startswith("D_")}
    # ── المقارنة في الحكم: العشوائي والاحتفاظ ──
    comp = {}
    for n in V:
        rb = random_books(V[n]["JUD"], *K.JUD, wcode=900 + list(V).index(n))
        comp[n] = {"JUD_measured": tab[n]["JUD"]["measured"], "random_median": round(float(np.median(rb)), 2),
                   "random_p95": round(float(np.percentile(rb, 95)), 2), "pct_random_below": round(100 * float((rb < tab[n]["JUD"]["measured"]).mean()), 1)}
    bh = round(buy_hold(*K.JUD), 2)
    for n in comp: comp[n]["buy_hold_JUD"] = bh
    res["JUD_comparators"] = comp
    # ── Walk-Forward (بلا اختيار) ──
    res["walk_forward"] = {}; OOS = {}
    for lab, spec in (("primary", PRE["walk_forward"] and {"train_m": 6, "val_m": 3, "test_m": 3, "step_m": 3}), ("sensitive", {"train_m": 12, "val_m": 3, "test_m": 3, "step_m": 3})):
        res["walk_forward"][lab] = {}
        for n in V:
            recs, oos, summ = wf(V[n]["FULL"], spec, "P" if lab == "primary" else "S")
            res["walk_forward"][lab][n] = {"summary": summ, "windows": recs}; OOS[(lab, n)] = oos
            pd.DataFrame(recs).to_csv(OUT / f"wf_{lab}_{n}_{TAG}.csv", index=False, encoding="utf-8-sig")
        print("WF", lab, {n: (res["walk_forward"][lab][n]["summary"]["median"], res["walk_forward"][lab][n]["summary"]["pct_positive"], res["walk_forward"][lab][n]["summary"]["net_measured"]) for n in V}, flush=True)
    # ── رأس المال المشترك (الفترة الكاملة، 20$) ──
    res["shared_capital"] = {}
    for n in V:
        res["shared_capital"][n] = {cap: portfolio(V[n]["ALL"], cap, wrapper=n.startswith("D_")) for cap in SIZES}
        print("PORT", n, {c: (d["net"], d["rejected"], d["min_cash"], d["dd_pct_capital"]) for c, d in res["shared_capital"][n].items()}, flush=True)
    res["shared_capital_pressed"] = {n: any(d["rejected"] > 0 for d in res["shared_capital"][n].values()) for n in V}
    # ── تقرير العملات (على اختبارات WF الرئيسية) ──
    res["coins"] = {n: coin_report(OOS[("primary", n)], V[n]["SEL"], V[n]["JUD"],
                                   wrapped_oos=OOS[("primary", "D_stop_H180")] if n == "B_V3_corrected" else None) for n in V}
    # ── الاقتصاد ──
    econ = {}
    yrs = (END - START).days / 365.25
    for n in V:
        net = tab[n]["ALL"]["measured"]; pt = res["shared_capital"][n][2000]
        econ[n] = {"net_20usd_per_order_all": net, "net_1000_book_per_coin_pct": round(100 * net / 13000, 3),
                   "shared_2000_net": pt["net"], "monthly": round(net / yrs / 12, 2), "annual": round(net / yrs, 2),
                   "opex_covered_max_per_month": round(max(net / yrs / 12, 0), 2), "order_days": res["D6_holding"][n].get("order_days_total"),
                   "avg_frozen_capital": pt["avg_deployed"], "peak_frozen_capital": pt["peak_deployed"]}
    res["economics"] = econ
    # ── البوابات لكل نسخة مصححة ──
    gates = {}
    for n in V:
        if n == "A_current_code": continue
        t = tab[n]; w = res["walk_forward"]["primary"][n]["summary"]; pt = res["shared_capital"][n][2000]; c = comp[n]
        gates[n] = {"1_SEL_JUD_pos": t["SEL"]["measured"] > 0 and t["JUD"]["measured"] > 0,
                    "2_pos_measured_and_stress_high": t["ALL"]["measured"] > 0 and t["ALL"]["stress_high"] > 0 and t["JUD"]["stress_high"] > 0,
                    "3_beats_random_and_hold_JUD": c["JUD_measured"] > c["random_median"] and c["JUD_measured"] > c["buy_hold_JUD"],
                    "4_avg_order_pos": (t["ALL"]["avg_order_measured"] or 0) > 0,
                    "5_wf_median_pos": w["median"] > 0, "6_ge60pct_windows": w["pct_positive"] >= 60,
                    "7_best_window_le40": w["best_window_share"] is not None and w["best_window_share"] <= 0.40,
                    "8_top_coin_le35": w["top_coin_share"] is not None and w["top_coin_share"] <= 0.35,
                    "9_dd_le35_uw_le540": pt["dd_pct_peak_deployed"] >= -35 and pt["underwater_days"] <= 540,
                    "10_monthly_pos": econ[n]["monthly"] > 0, "11_ge3_coins_pos": w["coins_positive"] >= 3, "12_coin_report": len(res["coins"][n]) == 13}
        gates[n]["PASS"] = all(v for v in gates[n].values())
        gates[n]["failed"] = [k for k, v in gates[n].items() if k not in ("PASS",) and v is False]
    res["gates"] = gates
    print("GATES", {n: g["failed"] for n, g in gates.items()}, flush=True)
    # ── صفقات للتحقق من التعبئة ──
    if TAG == "pass1":
        for n in ("B_V3_corrected", "C_V2_corrected", "D_stop_H180"):
            pd.DataFrame([{"symbol": r["symbol"], "entry_time": CN[r["symbol"]].idx[r["entry_bar"]].isoformat(), "exit_time": CN[r["symbol"]].idx[r["exit_bar"]].isoformat(),
                           "entry": r["entry_ref"], "exit": r["exit_px"], "notional": ORDER, "reason": r["reason"], "stage": r["stage"]} for r in V[n]["ALL"]]
                         ).to_csv(OUT / f"trades_{n}.csv", index=False, encoding="utf-8-sig")
    (OUT / f"results_l0069_{TAG}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("تم", TAG)


if __name__ == "__main__":
    main()
