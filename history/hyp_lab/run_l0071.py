import json, sys, hashlib, numpy as np, pandas as pd, os
sys.path.insert(0, os.path.dirname(__file__))
import l0071_core as C

OUT = os.path.join(os.path.dirname(__file__), "../research/hyp_lab_out/L0071")
UTC = "UTC"
END = pd.Timestamp("2026-08-31", tz=UTC)


def windows(tr, va, te, step=3):
    ws = []; s = pd.Timestamp("2021-09-01", tz=UTC)
    while True:
        a = s + pd.DateOffset(months=tr); b = a + pd.DateOffset(months=va); e = b + pd.DateOffset(months=te)
        if b >= END: break
        ws.append((s, a, b, min(e, END))); s += pd.DateOffset(months=step)
    return ws


def wpnl(eq, a, b):
    x = eq[(eq.index >= a) & (eq.index < b)]
    if len(x) == 0: return 0.0
    prev = eq[eq.index < a]
    start = prev.iloc[-1] if len(prev) else x.iloc[0]
    return float(x.iloc[-1] - start)


def layer_pnl(T, layer):
    f = C.fee_layer(layer); sl = {"c115": 0, "measured": None, "stress_mid": 0.001, "stress_high": 0.003}[layer]
    if sl is None: return float(T.pnl.sum())
    return float((T.qty * (T.raw_exit * (1 - sl) * (1 - f) - T.raw_entry * (1 + sl) * (1 + f))).sum())


def dd_stats(eq):
    pk = eq.cummax(); dd = eq / pk - 1
    uw = 0; best = 0; start = None
    for t, v in dd.items():
        if v < -1e-9:
            start = start or t; best = max(best, (t - start).days)
        else: start = None
    return float(dd.min()), best


def summarize(res, ws):
    T = pd.DataFrame(res["trades"]); eq = C.eq_series(res)
    test = [wpnl(eq, b, e) for (_, _, b, e) in ws]
    t0 = ws[0][2]
    To = T[pd.to_datetime(T.exit_t) >= t0] if len(T) else T
    mdd, uw = dd_stats(eq[eq.index >= t0])
    net = float(sum(test)); months = (END - t0).days / 30.44
    pos_share = max([x for x in test if x > 0] or [0]) / net if net > 0 else None
    coin = To.groupby("sym").pnl.sum() if len(To) else pd.Series(dtype=float)
    out = dict(net_oos=net, windows=[round(x, 2) for x in test], n_windows=len(test), pos_windows=int(sum(x > 0 for x in test)),
               median_window=float(np.median(test)), worst=float(min(test)), best=float(max(test)),
               n_trades=int(len(To)), avg_trade=float(To.pnl.mean()) if len(To) else 0, median_trade=float(To.pnl.median()) if len(To) else 0,
               win_rate=float((To.pnl > 0).mean()) if len(To) else 0, mdd=mdd, longest_underwater_days=uw,
               monthly=net / months, annual=net / months * 12, max_window_share=pos_share,
               max_coin_share=(float(coin.max() / net) if net > 0 and len(coin) else None),
               top_trade_share=(float(To.pnl.max() / net) if net > 0 and len(To) else None),
               layers={L: layer_pnl(To, L) for L in ["c115", "measured", "stress_mid", "stress_high"]} if len(To) else {},
               protected_pct=float(To.protected.mean()) if len(To) else 0, trail_pct=float(To.trail.mean()) if len(To) else 0,
               exits=To.reason.value_counts().to_dict() if len(To) else {},
               per_coin={s: dict(n=int((To.sym == s).sum()), net=float(To[To.sym == s].pnl.sum()),
                                 avg=float(To[To.sym == s].pnl.mean()) if (To.sym == s).any() else 0,
                                 win=float((To[To.sym == s].pnl > 0).mean()) if (To.sym == s).any() else 0) for s in C.SYMS},
               per_regime=To.groupby("regime").pnl.agg(["count", "sum"]).round(2).to_dict() if len(To) else {},
               per_kind=To.groupby("kind").pnl.agg(["count", "sum"]).round(2).to_dict() if len(To) else {},
               orders_exec=res["nexec"], orders_rej=res["nrej"], max_conc=res["max_conc"], min_cash=res["min_cash"])
    return out, T, eq


def coin_class(pc):
    r = {}
    for s, v in pc.items():
        r[s] = "غير كافية البيانات" if v["n"] < 8 else ("مناسبة" if v["net"] > 0 and v["avg"] > 0 and v["win"] >= .5 else ("واعدة" if v["net"] > 0 else "غير مناسبة"))
    return r


def bh(ws):
    t0 = ws[0][2]; out = {}
    for s in C.SYMS:
        P = C.prep(s); c = pd.Series(P["c"], index=P["t"]); x = c[(c.index >= t0) & (c.index < END)]
        out[s] = float(2000 / 13 * (x.iloc[-1] * (1 - .0013) / (x.iloc[0] * 1.0013) - 1)) if len(x) else 0.0
    return out


def random_ctrl(T, ws, n=1000, seed=71):
    rng = np.random.default_rng(seed); t0 = ws[0][2]
    T = T[pd.to_datetime(T.exit_t) >= t0]; tot = np.zeros(n)
    for s, g in T.groupby("sym"):
        P = C.prep(s); c = P["c"]; o = P["o"]; t = P["t"]; m = P["mult"]
        lo = int(np.searchsorted(t, t0)); hi = int(np.searchsorted(t, END))
        for _, r in g.iterrows():
            b = max(int(r.bars), 1); ks = rng.integers(lo + 1, max(hi - b - 1, lo + 2), n)
            ein = o[ks] * (1 + .0003 * m[ks]) * (1 + C.FEE); ex = o[np.minimum(ks + b, len(o) - 1)]
            ex = ex * (1 - .0003 * m[np.minimum(ks + b, len(o) - 1)]) * (1 - C.FEE)
            tot += r.cost * (ex / ein - 1)
    return dict(mean=float(tot.mean()), median=float(np.median(tot)), p95=float(np.percentile(tot, 95)), p5=float(np.percentile(tot, 5)))


FAMILIES = {
    "drawdown": [dict(dd_L=L, dd_thr=t) for L in (90, 120, 180) for t in (.20, .25, .30, .40)],
    "k_stop": [dict(k_stop=x) for x in (.75, 1.0, 1.25)],
    "margin": [dict(margin=x) for x in (.001, .002, .003)],
    "trail_start": [dict(trail_start=x) for x in (1.0, 1.5, 2.0)],
    "k_trail": [dict(k_trail=x) for x in (1.0, 1.5, 2.0)],
    "eql": [dict(eql=x) for x in (.25, .5)],
    "risk": [dict(risk=x) for x in (.005, .01, .015)],
    "signal": [dict(cat=x) for x in ("cat1", "cat2", "cat3", "cat4")],
    "reclaim": [dict(reclaim=x) for x in (0.0, .10)],
    "bear_margin": [dict(bear_margin=x) for x in (0.0, .10)],
}


def neighbours(fam, i):
    if fam == "drawdown":
        L, t = divmod(i, 4); return [a * 4 + b for a in (L - 1, L, L + 1) for b in (t - 1, t, t + 1) if 0 <= a < 3 and 0 <= b < 4 and (a, b) != (L, t)]
    return [x for x in (i - 1, i + 1) if 0 <= x < len(FAMILIES[fam])]


def wf_select(runs, ws, base_eq):
    """runs: fam -> list of (eq, trades df). returns per family stitched test pnl & choices."""
    res = {}
    for fam, lst in runs.items():
        if fam == "_base": continue
        choice, test = [], []
        for (s, a, b, e) in ws:
            tr = []
            for i, (eq, T) in enumerate(lst):
                Tw = T[(pd.to_datetime(T.exit_t) >= s) & (pd.to_datetime(T.exit_t) < a)] if len(T) else T
                tr.append((wpnl(eq, s, a), len(Tw), float(Tw.pnl.mean()) if len(Tw) else 0))
            best = None
            for i, (eq, T) in enumerate(lst):
                net, n, avg = tr[i]
                if not (net > 0 and avg > 0 and n >= 3): continue
                if wpnl(eq, a, b) < 0: continue
                nb = neighbours(fam, i)
                if nb and np.median([tr[j][0] for j in nb]) <= 0: continue
                if best is None or net > tr[best][0]: best = i
            pick = best if best is not None else lst.index(lst[0]) if False else None
            if pick is None: pick = "base"
            choice.append(pick)
            eq = base_eq if pick == "base" else lst[pick][0]
            test.append(wpnl(eq, b, e))
        res[fam] = dict(choices=choice, windows=[round(x, 2) for x in test], net=float(sum(test)), pos=int(sum(x > 0 for x in test)), median=float(np.median(test)))
    return res


def main():
    os.makedirs(OUT, exist_ok=True)
    WP, WS = windows(6, 3, 3), windows(12, 3, 3)
    # ---------- pass1: locked base
    base = C.run({})
    sP, T, eq = summarize(base, WP); sS, _, _ = summarize(base, WS)
    caps = {}
    for cap in (2000, 4000, 6500, 10000, 13000):
        r = C.run({}, capital=cap); s, _, _ = summarize(r, WP)
        caps[cap] = dict(net=s["net_oos"], pct=s["net_oos"] / cap, mdd=s["mdd"], exec=r["nexec"], rej=r["nrej"], min_cash=r["min_cash"], max_conc=r["max_conc"])
    ctrls = {}
    for name, cfg in {"first_touch": dict(first_touch=True), "with_mss_cat2": dict(cat="cat2"), "fixed_stop_only": dict(protect=False, trail=False),
                      "protect_no_trail": dict(trail=False), "full": {}}.items():
        r = base if name == "full" else C.run(cfg); s, _, _ = summarize(r, WP)
        ctrls[name] = {k: s[k] for k in ["net_oos", "pos_windows", "median_window", "n_trades", "avg_trade", "median_trade", "mdd", "layers"]}
    B = bh(WP); rnd = random_ctrl(T, WP)
    classes = coin_class(sP["per_coin"])
    p1 = dict(windows_primary=[[str(x.date()) for x in w] for w in WP], windows_sensitive_n=len(WS), base_primary=sP, base_sensitive=sS,
              capital=caps, controls=ctrls, buy_hold_per_coin=B, buy_hold_total=sum(B.values()), random=rnd, coin_class=classes,
              l0064_reference_only="+131.33$ (L0064 الخام، مرجع تاريخي فقط)")
    json.dump(p1, open(f"{OUT}/results_l0071_pass1.json", "w"), ensure_ascii=False, indent=1, default=float)
    T.to_csv(f"{OUT}/trades_l0071.csv", index=False)
    pd.DataFrame(base["sigrows"]).to_csv(f"{OUT}/signals_l0071.csv", index=False)
    # ---------- pass2: families WF
    runs = {"_base": (eq, T)}
    for fam, lst in FAMILIES.items():
        runs[fam] = []
        for cfg in lst:
            r = C.run(cfg); runs[fam].append((C.eq_series(r), pd.DataFrame(r["trades"])))
    fr = {k: v for k, v in runs.items() if k != "_base"}
    selP = wf_select(fr, WP, eq)
    selS = wf_select(fr, WS, eq)
    grid = {fam: [dict(cfg=FAMILIES[fam][i], net_primary=sum(wpnl(e, b, x) for (_, _, b, x) in WP)) for i, (e, _) in enumerate(lst)] for fam, lst in fr.items()}
    selP.pop("_base", None); selS.pop("_base", None)
    p2 = dict(selection_primary=selP, selection_sensitive=selS, family_grid_info_only=grid)
    json.dump(p2, open(f"{OUT}/results_l0071_pass2.json", "w"), ensure_ascii=False, indent=1, default=float)
    # ---------- gates
    nb = {"margin": [grid["margin"][0]["net_primary"], grid["margin"][2]["net_primary"]], "k_trail": [grid["k_trail"][0]["net_primary"], grid["k_trail"][2]["net_primary"]]}
    g = sP; pos_coins = sum(v["net"] > 0 for v in g["per_coin"].values())
    gates = {
        "1_net_pos": g["net_oos"] > 0, "2_stress_high_pos": g["layers"].get("stress_high", -1) > 0, "3_median_window_pos": g["median_window"] > 0,
        "4_60pct_windows": g["pos_windows"] >= .6 * g["n_windows"], "5_avg_median_trade_pos": g["avg_trade"] > 0 and g["median_trade"] > 0,
        "6_window_share_le40": g["max_window_share"] is not None and g["max_window_share"] <= .4,
        "7_coin_share_le35": g["max_coin_share"] is not None and g["max_coin_share"] <= .35, "8_mdd_le35": g["mdd"] >= -.35,
        "9_underwater_le540": g["longest_underwater_days"] <= 540, "10_three_coins_pos": pos_coins >= 3,
        "11_not_single_coin": g["max_coin_share"] is not None and g["max_coin_share"] <= .5,
        "12_beats_first_touch": ctrls["full"]["median_window"] > ctrls["first_touch"]["median_window"] or ctrls["full"]["mdd"] > ctrls["first_touch"]["mdd"] and ctrls["full"]["net_oos"] >= ctrls["first_touch"]["net_oos"],
        "13_neighbours_hold": g["net_oos"] > 0 and min(nb["margin"] + nb["k_trail"]) > 0,
        "14_covers_run_cost": g["net_oos"] > 0, "15_not_single_trade": g["top_trade_share"] is not None and g["top_trade_share"] < .5,
    }
    return p1, p2, gates, base, T


if __name__ == "__main__":
    p1, p2, gates, base, T = main()
    json.dump({k: bool(v) for k, v in gates.items()}, open(f"{OUT}/gates_l0071.json", "w"), indent=1)
    print(json.dumps({k: bool(v) for k, v in gates.items()}, indent=0))
