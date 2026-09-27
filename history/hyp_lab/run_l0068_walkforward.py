#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0068 — المسار الثاني: البحث المتحرك القصير (6/3/3 أساسي · 12/3/3 حساس) بمكتبة 148 مرشحًا مسجلة مسبقًا.
    python3 run_l0068_walkforward.py pass1|pass2
"""
from __future__ import annotations
import hashlib, json, math, sys, zlib
import numpy as np, pandas as pd
sys.path.insert(0, "/home/user/work/history/hyp_lab")
import l0067_common as K
import l0068_sim as S
import l0068_replayer as RP

TAG = sys.argv[1] if len(sys.argv) > 1 else "pass1"
OUT = K.ROOT / "history/research/hyp_lab_out/L0068"
PRE = json.loads((OUT / "preregistration_l0068.json").read_text(encoding="utf-8"))
COINS = list(K.TARGET13)
T = K.T
START, END = T("2021-09-01"), T("2026-08-31")
LAYERS = ("gross", "c115", "c130", "intended", "s10", "s30")
SIZES = (2000, 4000, 6500, 10000, 13000)
ORDER = 20.0

h4s = {s: K.h4(s) for s in COINS}
MKT = S.market_by_day(h4s, COINS)
CN = {s: S.Coin(s, h4s[s], MKT) for s in COINS}

# ───────────── المرشحات ─────────────
Ls, Ds, Rs = (20, 30, 60, 90), (4, 8, 12, 16, 20), ("MSS3", "MSS6", "MSS12", "C>EMA20", "C>EMA50", "MSS6+EMA20")
CAND = {}
for L in Ls:
    for D in Ds:
        for R in Rs:
            CAND[f"core|L{L}|D{D}|{R}"] = {"fam": "core", "p": {"L": L, "D": D, "rec": R}}
B0 = {"L": 90, "D": 20, "rec": "MSS6+EMA20"}
FAM = {"market": [("market", x) for x in ("btc200", "btc200_50", "breadth40", "breadth50", "breadth60")],
       "trend": [("trend", x) for x in ("ema20", "ema50", "ema100", "ema200", "x20_50", "x50_200")],
       "aux": [("aux", "rsi30"), ("aux", "rsi40"), ("aux", "rsi50"), ("inv", "atr1"), ("inv", "atr1.5"), ("inv", "atr2"),
               ("aux", "bb10"), ("aux", "volup"), ("aux", "voldn")],
       "stages": [("stages", 2), ("stages", 3)], "exit": [("exit", "partial")], "tl": [("tl", x) for x in (30, 90, 180, 365)]}
for f, items in FAM.items():
    for k, v in items:
        CAND[f"{f}|{k}={v}"] = {"fam": f, "p": {**B0, k: v}}
CAND["L0064|raw"] = {"fam": "L0064", "p": None}
assert len(CAND) == PRE["library"]["total_candidates"], len(CAND)
NAMES = list(CAND)


def neighbors(name):
    c = CAND[name]
    if c["fam"] == "core":
        p = c["p"]; out = []
        for arr, key in ((Ls, "L"), (Ds, "D"), (Rs, "rec")):
            i = arr.index(p[key])
            for j in (i - 1, i + 1):
                if 0 <= j < len(arr):
                    q = dict(p); q[key] = arr[j]
                    out.append(f"core|L{q['L']}|D{q['D']}|{q['rec']}")
        return out
    if c["fam"] == "L0064":
        return ["_L0064_lag", "_L0064_v2"]
    return ["core|L90|D20|MSS6+EMA20"] + [n for n in NAMES if CAND[n]["fam"] == c["fam"] and n != name]


# ───────────── التشغيل الكامل مرة واحدة لكل مرشح (سببي) ─────────────
def from_rp(recs, sym):
    return [{"symbol": sym, "stage": r["stage"], "entry_bar": r["entry_bar"], "exit_bar": r["exit_bar"], "entry_ref": float(r["entry_px"]),
             "exit_px": float(r["exit_px"]), "reason": r["reason"], "signal_bar": r["signal_bar"]} for r in recs]


ROWS = {}
for n in NAMES:
    if CAND[n]["fam"] == "L0064":
        ROWS[n] = [r for s in COINS for r in from_rp(RP.replay(h4s[s], s), s)]
    else:
        ROWS[n] = [r for s in COINS for r in S.run(CN[s], CAND[n]["p"])]
ROWS["_L0064_lag"] = [r for s in COINS for r in from_rp(RP.replay(h4s[s], s, ctx_extra_lag=True), s)]
ROWS["_L0064_v2"] = [r for s in COINS for r in from_rp(RP.replay(h4s[s], s, gate=False), s)]
print("مرشحات:", len(NAMES), "· صفقات كلية:", sum(len(ROWS[n]) for n in NAMES), flush=True)


def seg(rows, s, e):
    out = []
    for r in rows:
        cn = CN[r["symbol"]]; t0 = cn.idx[r["entry_bar"]]
        if not (s <= t0 < e):
            continue
        q = dict(r)
        if cn.idx[r["exit_bar"]] >= e:
            j = int(cn.idx.searchsorted(e)) - 1
            q["exit_bar"] = j; q["exit_px"] = float(cn.c[j]); q["reason"] = "قطع-المقطع"
        out.append(q)
    return out


def stats(rows, layer="intended"):
    if not rows:
        return {"n": 0, "net": 0.0}
    p = S.pnl(rows, CN, layer)
    net = float(p.sum())
    t_ex = [CN[r["symbol"]].idx[r["exit_bar"]] for r in rows]
    t_en = [CN[r["symbol"]].idx[r["entry_bar"]] for r in rows]
    order = np.argsort(np.array(t_ex, dtype="datetime64[ns]"))
    cum = np.cumsum(p[order]); dd = float((cum - np.maximum.accumulate(np.concatenate([[0], cum]))[1:]).min())
    ev = sorted([(a, 1) for a in t_en] + [(b, -1) for b in t_ex], key=lambda x: (x[0], -x[1]))
    cur = peak = 0
    for _, d in ev:
        cur += d; peak = max(peak, cur)
    months = pd.Series(p, index=[t.strftime("%Y-%m") for t in t_ex]).groupby(level=0).sum()
    pos = net if net > 0 else np.nan
    return {"n": len(rows), "net": net, "avg": net / len(rows), "max_trade_share": float(p.max() / pos) if net > 0 else None,
            "max_month_share": float(months.max() / pos) if net > 0 else None, "dd": dd, "peak_dep": peak * ORDER,
            "dd_pct_peak": 100 * dd / (peak * ORDER) if peak else 0.0}


def windows(train_m, val_m, test_m, step_m):
    out = []; a = START
    while True:
        tr_e = a + pd.DateOffset(months=train_m); va_e = tr_e + pd.DateOffset(months=val_m); te_e = va_e + pd.DateOffset(months=test_m)
        if te_e > END + pd.Timedelta(days=1):
            break
        out.append((a, tr_e, va_e, min(te_e, END)))
        a = a + pd.DateOffset(months=step_m)
    return out


def select(a, tr_e, va_e):
    atr_pct_med = float(np.nanmedian(np.concatenate([CN[s].atr[(CN[s].idx >= a) & (CN[s].idx < tr_e)] /
                                                     CN[s].c[(CN[s].idx >= a) & (CN[s].idx < tr_e)] for s in COINS])))
    res = {}
    for n in NAMES + ["_L0064_lag", "_L0064_v2"]:
        tr = seg(ROWS[n], a, tr_e); va = seg(ROWS[n], tr_e, va_e)
        st_tr, st_va, st_all = stats(tr), stats(va), stats(tr + va)
        res[n] = {"train": st_tr["net"], "val": st_va["net"], "all": st_all["net"], "n": st_all["n"], "st": st_all}
    for n in NAMES:
        st = res[n]["st"]; rej = None
        p = CAND[n]["p"]
        if p and str(p.get("inv", "")).startswith("atr") and float(p["inv"][3:]) * atr_pct_med <= S.GAP:
            rej = "فاصل المرحلة ≥ مسافة الإلغاء"
        conds = {"train>0": res[n]["train"] > 0, "val>0": res[n]["val"] > 0, "avg>0": st.get("avg", 0) > 0,
                 "trade<=40%": st.get("max_trade_share") is not None and st["max_trade_share"] <= 0.40,
                 "month<=40%": st.get("max_month_share") is not None and st["max_month_share"] <= 0.40,
                 "dd<=35%": st.get("dd_pct_peak", 0) >= -35, "n>=5": st["n"] >= 5}
        nb = [res[m]["all"] for m in neighbors(n)]
        res[n]["plateau"] = float(np.median(nb)) if nb else res[n]["all"]
        res[n]["eligible"] = rej is None and all(conds.values()) and res[n]["plateau"] > 0
        res[n]["fail"] = rej or ",".join(k for k, v in conds.items() if not v) or ("جيران" if res[n]["plateau"] <= 0 else "")
    el = [n for n in NAMES if res[n]["eligible"]]
    if not el:
        return None, res
    rank = {n: i for i, n in enumerate(NAMES)}
    return max(el, key=lambda n: (round(res[n]["plateau"], 6), -rank[n])), res


def pause_allow(cn, mode):
    if mode == 1:
        return None
    if mode == 2:
        return cn.mkt["btc200_50"] == 1
    bear = pd.Series(MKT["btc_bear"]); up = pd.Series(MKT["btc200"])
    state, run_up, st = True, 0, {}
    for d in bear.index:
        if bear[d] == 1:
            state, run_up = False, 0
        elif not state:
            run_up = run_up + 1 if up[d] == 1 else 0
            if run_up >= 5:
                state = True
        st[d] = state
    ser = pd.Series(st).astype(float).shift(1)
    return ser.reindex(cn.idx.normalize()).fillna(0).to_numpy() == 1


def run_cfg(name, allow_mode=1):
    if allow_mode == 1:
        return ROWS[name]
    if CAND[name]["fam"] == "L0064":
        out = []
        for s in COINS:
            al = pause_allow(CN[s], allow_mode)
            out += [r for r in from_rp(RP.replay(h4s[s], s), s) if al[r["signal_bar"]]]  # تقريب: يحذف الدخول الممنوع (المحرك لا يقبل قناعًا)
        return out
    return [r for s in COINS for r in S.run(CN[s], CAND[name]["p"], pause_allow(CN[s], allow_mode))]


def random_books(rows, s, e, wcode):
    tab = {}
    cyc = {}
    for r in rows:
        cyc.setdefault((r["symbol"], r["signal_bar"] if r["stage"] == 0 else None), []).append(r)
    by = {}
    for r in sorted(rows, key=lambda r: (r["symbol"], r["entry_bar"], r["stage"])):
        by.setdefault(r["symbol"], []).append(r)
    for sym, rr in by.items():
        cur = []; cycles = []
        for r in rr:
            if r["stage"] == 0 and cur:
                cycles.append(cur); cur = []
            cur.append(r)
        if cur: cycles.append(cur)
        tab[sym] = [(max(max(x["exit_bar"] for x in g) - min(x["entry_bar"] for x in g), 1), len(g)) for g in cycles]
    nets = []
    for b in range(1000):
        tot = 0.0
        for sym, pairs in tab.items():
            cn = CN[sym]; ii = np.where((cn.idx >= s) & (cn.idx < e))[0]
            if len(ii) < 3: continue
            rng = np.random.default_rng(np.random.SeedSequence([68, wcode, b, zlib.crc32(sym.encode())]))
            for d, k in pairs:
                hi = len(ii) - 2 - d
                if hi < 0: continue
                a = ii[0] + 1 + int(rng.integers(0, hi + 1)); x = a + d
                ep = cn.o[a] * (1 + 0.0003 * float(S.slip_mult(np.nan_to_num(cn.vr[a - 1]))))
                xp = cn.c[x] * (1 - 0.0003 * float(S.slip_mult(np.nan_to_num(cn.vr[x - 1]))))
                tot += (((xp / ep) * 0.999 - 1.001) / 1.001) * ORDER * k
        nets.append(tot)
    return np.array(nets)


def buy_hold(s, e):
    tot, n = 0.0, 0
    for sym in COINS:
        cn = CN[sym]; ii = np.where((cn.idx >= s) & (cn.idx < e))[0]
        if len(ii) < 2: continue
        tot += (((cn.c[ii[-1]] / cn.o[ii[0]]) * 0.9987 - 1.0013) / 1.0013) * ORDER; n += 1
    return tot, n


def shared_portfolio(rows, capital, layer="intended"):
    """تتابع زمني؛ الدخول قبل الخروج في الشمعة نفسها (محافظ)؛ أمر 20$؛ نقص النقد = رفض مسجل."""
    ev = []
    for k, r in enumerate(rows):
        cn = CN[r["symbol"]]
        ev.append((cn.idx[r["entry_bar"]], 0, r["symbol"], k)); ev.append((cn.idx[r["exit_bar"]], 1, r["symbol"], k))
    ev.sort(key=lambda x: (x[0], x[1], x[2]))
    p = S.pnl(rows, CN, layer); cash = capital; taken = np.zeros(len(rows), bool); rej = 0; minc = cash
    for t, kind, sym, k in ev:
        if kind == 0:
            if cash >= ORDER - 1e-9:
                cash -= ORDER; taken[k] = True
            else:
                rej += 1
        elif taken[k]:
            cash += ORDER + p[k]
        minc = min(minc, cash)
    return taken, rej, minc, p


def mtm_curve(rows, taken, p, s, e):
    grid = pd.date_range(s, e, freq="4h", inclusive="left"); n = len(grid)
    eq = np.zeros(n); dep = np.zeros(n + 1)
    for k, r in enumerate(rows):
        if not taken[k]: continue
        cn = CN[r["symbol"]]
        a = int(grid.searchsorted(cn.idx[r["entry_bar"]])); b = int(grid.searchsorted(cn.idx[r["exit_bar"]]))
        a, b = min(a, n - 1), min(b, n - 1)
        if b > a:
            cl = pd.Series(cn.c, index=cn.idx).reindex(grid[a:b]).ffill().to_numpy()
            eq[a:b] += ((cl / r["entry_ref"]) - 1) * ORDER
        eq[b:] += p[k]; dep[a] += ORDER; dep[b] -= ORDER
    rm = np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]
    dd = eq - rm; longest = cur = 0
    for u in dd < -1e-9:
        cur = cur + 1 if u else 0; longest = max(longest, cur)
    return float(dd.min()), longest * 4 / 24, float(np.cumsum(dep)[:n].max())


def wilson(k, n, z=1.96):
    if n == 0: return None
    ph = k / n; d = 1 + z * z / n; c = (ph + z * z / (2 * n)) / d; h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return [round(100 * (c - h), 1), round(100 * (c + h), 1)]


def path(label, spec):
    W = windows(spec["train_m"], spec["val_m"], spec["test_m"], spec["step_m"])
    recs, oos, per_cand = [], [], {n: {"selected": 0, "eligible": 0, "val_nets": []} for n in NAMES}
    for wi, (a, tr_e, va_e, te_e) in enumerate(W):
        best, res = select(a, tr_e, va_e)
        for n in NAMES:
            per_cand[n]["eligible"] += int(res[n]["eligible"]); per_cand[n]["val_nets"].append(res[n]["val"])
        row = {"window": f"{label}{wi + 1:02d}", "train": f"{a.date()}→{tr_e.date()}", "val": f"{tr_e.date()}→{va_e.date()}",
               "test": f"{va_e.date()}→{te_e.date()}", "fixed": best, "eligible_count": sum(res[n]["eligible"] for n in NAMES)}
        te = seg(ROWS[best], va_e, te_e) if best else []
        if best:
            per_cand[best]["selected"] += 1
            row.update({"train_net": round(res[best]["train"], 2), "val_net": round(res[best]["val"], 2), "plateau": round(res[best]["plateau"], 2)})
        for L_ in LAYERS:
            row[f"test_{L_}"] = round(float(S.pnl(te, CN, L_).sum()), 2) if te else 0.0
        row["test_trades"] = len(te)
        ref = seg(ROWS["L0064|raw"], va_e, te_e)
        row["L0064_raw_intended"] = round(float(S.pnl(ref, CN, "intended").sum()), 2) if ref else 0.0
        bh, nb = buy_hold(va_e, te_e); row["buy_hold"] = round(bh, 2)
        if best:
            m2 = seg(run_cfg(best, 2), va_e, te_e); m3 = seg(run_cfg(best, 3), va_e, te_e)
            row["mode2_uptrend_only"] = round(float(S.pnl(m2, CN, "intended").sum()), 2) if m2 else 0.0
            row["mode3_pause_restart"] = round(float(S.pnl(m3, CN, "intended").sum()), 2) if m3 else 0.0
            k1 = {(r["symbol"], r["entry_bar"]) for r in te}; k3 = {(r["symbol"], r["entry_bar"]) for r in m3}
            row["mode3_missed_slices"] = len(k1 - k3)
            row["mode3_missed_pnl"] = round(float(S.pnl([r for r in te if (r["symbol"], r["entry_bar"]) not in k3], CN, "intended").sum()), 2) if k1 - k3 else 0.0
        if te:
            rb = random_books(te, va_e, te_e, wi + (0 if label == "P" else 100))
            row["random_median"] = round(float(np.median(rb)), 2); row["random_pct_below"] = round(float(100 * np.mean(rb < row["test_intended"])), 1)
        recs.append(row); oos += te
        print(label, row["window"], row["test"], best, row["test_intended"], row["test_trades"], flush=True)
    # ── المحفظة المشتركة على نتائج الاختبار المتصلة ──
    s0 = T(recs[0]["test"].split("→")[0]); e0 = T(recs[-1]["test"].split("→")[1])
    port = {}
    for cap in SIZES:
        taken, rej, minc, p = shared_portfolio(oos, cap)
        if oos:
            dd, uw, peak = mtm_curve(oos, taken, p, s0, e0)
        else:
            dd = uw = peak = 0.0
        port[cap] = {"net_intended": round(float(p[taken].sum()), 2) if oos else 0.0, "rejected": rej, "min_cash": round(minc, 2),
                     "dd_usd": round(dd, 2), "dd_pct_capital": round(100 * dd / cap, 2), "dd_pct_peak_dep": round(100 * dd / peak, 2) if peak else 0.0,
                     "underwater_days": round(uw, 1), "peak_deployed": peak}
    tests = np.array([r["test_intended"] for r in recs])
    years = (e0 - s0).days / 365.25
    net = float(tests.sum())
    per_coin = {}
    for sym in COINS:
        rr = [r for r in oos if r["symbol"] == sym]
        pc = S.pnl(rr, CN, "intended") if rr else np.zeros(0)
        per_coin[sym] = float(pc.sum())
    summ = {"windows": len(recs), "tests": len(recs), "net_intended": round(net, 2), "median_window": round(float(np.median(tests)), 2),
            "pct_positive": round(100 * float((tests > 0).mean()), 1), "no_trade_windows": int(sum(r["test_trades"] == 0 for r in recs)),
            "worst": min(recs, key=lambda r: r["test_intended"])["window"], "worst_net": float(tests.min()),
            "best": max(recs, key=lambda r: r["test_intended"])["window"], "best_net": float(tests.max()),
            "net_by_layer": {L_: round(sum(r[f"test_{L_}"] for r in recs), 2) for L_ in LAYERS},
            "avg_trade": round(net / len(oos), 4) if oos else None, "trades": len(oos),
            "best_window_share": round(float(tests.max() / net), 3) if net > 0 else None,
            "top_coin_share": round(max(per_coin.values()) / net, 3) if net > 0 else None,
            "coins_positive": int(sum(v > 0 for v in per_coin.values())), "per_coin": {k: round(v, 2) for k, v in per_coin.items()},
            "annual_net": round(net / years, 2), "monthly_net": round(net / years / 12, 2), "years": round(years, 2),
            "L0064_raw_sum": round(sum(r["L0064_raw_intended"] for r in recs), 2), "buy_hold_sum": round(sum(r["buy_hold"] for r in recs), 2),
            "mode2_sum": round(sum(r.get("mode2_uptrend_only", 0) for r in recs), 2), "mode3_sum": round(sum(r.get("mode3_pause_restart", 0) for r in recs), 2),
            "mode3_missed_slices": int(sum(r.get("mode3_missed_slices", 0) for r in recs)),
            "mode3_missed_pnl": round(sum(r.get("mode3_missed_pnl", 0) for r in recs), 2),
            "selected_configs": pd.Series([r["fixed"] for r in recs]).value_counts(dropna=False).to_dict(),
            "portfolio": port}
    # ── تقرير العملات ──
    coins_rep = {}
    for sym in COINS:
        rr = [r for r in oos if r["symbol"] == sym]
        if not rr:
            coins_rep[sym] = {"test_slices": 0, "class": "غير كافية البيانات" if len(K.h4(sym)) < 4000 else "غير مناسبة (لم تُتداول خارج العينة)"}
            continue
        pg, pc = S.pnl(rr, CN, "gross"), S.pnl(rr, CN, "intended")
        cum = np.cumsum(pc); dd = float((cum - np.maximum.accumulate(np.concatenate([[0], cum]))[1:]).min())
        streak = cur = 0
        for x in pc:
            cur = cur + 1 if x <= 0 else 0; streak = max(streak, cur)
        w = int((pc > 0).sum())
        cls = ("غير كافية البيانات" if len(rr) < 8 else "مناسبة" if pc.sum() > 0 and pc.mean() > 0 and w / len(rr) >= 0.5 else
               "واعدة" if pc.sum() > 0 else "غير مناسبة")
        coins_rep[sym] = {"test_slices": len(rr), "wins": w, "losses": len(rr) - w, "win_rate": round(100 * w / len(rr), 1), "wilson95": wilson(w, len(rr)),
                          "net_gross": round(float(pg.sum()), 2), "net_intended": round(float(pc.sum()), 2), "avg": round(float(pc.mean()), 3),
                          "median": round(float(np.median(pc)), 3), "dd": round(dd, 2), "longest_losing_streak": streak, "class": cls}
    cand_tab = {n: {"selected": v["selected"], "eligible_windows": v["eligible"], "median_val_net": round(float(np.median(v["val_nets"])), 2),
                    "pct_val_positive": round(100 * float(np.mean(np.array(v["val_nets"]) > 0)), 1)} for n, v in per_cand.items()}
    return recs, summ, coins_rep, cand_tab, oos


def gates(summ, coins_rep):
    P = summ["portfolio"][2000]
    net = summ["net_intended"]
    return {"1_median_pos": summ["median_window"] > 0, "2_ge60pct_pos": summ["pct_positive"] >= 60,
            "3_pos_at_stress": summ["net_by_layer"]["s30"] > 0 and summ["net_by_layer"]["c130"] > 0,
            "4_best_window_le40": summ["best_window_share"] is not None and summ["best_window_share"] <= 0.40,
            "5_top_coin_le35": summ["top_coin_share"] is not None and summ["top_coin_share"] <= 0.35,
            "6_avg_trade_pos": (summ["avg_trade"] or 0) > 0, "7_dd_le35": P["dd_pct_capital"] >= -35 and P["dd_pct_peak_dep"] >= -35,
            "8_underwater_le540": P["underwater_days"] <= 540, "9_opex_shown": f"يغطي حتى {max(summ['monthly_net'], 0):.2f}$ شهريًا",
            "10_ge3_coins_pos": summ["coins_positive"] >= 3, "11_every_coin_classified": len(coins_rep) == 13, "12_no_memes": True}


def main():
    R = {"pass": TAG, "prereg_sha": hashlib.sha256((OUT / "preregistration_l0068.json").read_bytes()).hexdigest()[:16],
         "candidates": len(NAMES)}
    for label, key in (("P", "primary"), ("S", "sensitive")):
        recs, summ, coins_rep, cand_tab, oos = path(label, PRE["windows"][key])
        R[key] = {"windows": recs, "summary": summ, "coins": coins_rep, "candidates": cand_tab, "gates": gates(summ, coins_rep)}
        pd.DataFrame(recs).to_csv(OUT / f"walkforward_{key}_{TAG}.csv", index=False, encoding="utf-8-sig")
        if TAG == "pass1" and oos:
            f = pd.DataFrame([{"symbol": r["symbol"], "entry_time": CN[r["symbol"]].idx[r["entry_bar"]].isoformat(),
                               "exit_time": CN[r["symbol"]].idx[r["exit_bar"]].isoformat(), "entry": r["entry_ref"], "exit": r["exit_px"],
                               "notional": ORDER, "pnl": round(float(p), 4), "reason": r["reason"], "stage": r["stage"],
                               "bars_held": r["exit_bar"] - r["entry_bar"]} for r, p in zip(oos, S.pnl(oos, CN, "intended"))])
            f.to_csv(OUT / f"trades_oos_{key}.csv", index=False, encoding="utf-8-sig")
        print(key, json.dumps({k: v for k, v in summ.items() if k not in ("per_coin", "portfolio")}, ensure_ascii=False), flush=True)
        print(key, "gates", R[key]["gates"], flush=True)
    # نتيجة كل مرشح على الفترة كلها (سياق فقط، ليست اختيارًا)
    R["full_period_context"] = {n: {"trades": len(ROWS[n]), "net_intended": round(float(S.pnl(ROWS[n], CN, "intended").sum()), 2) if ROWS[n] else 0.0}
                                for n in NAMES}
    txt = json.dumps(R, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    (OUT / f"walkforward_results_{TAG}.json").write_text(txt, encoding="utf-8")


if __name__ == "__main__":
    main()
