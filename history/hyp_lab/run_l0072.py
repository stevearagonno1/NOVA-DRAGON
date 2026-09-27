import json, sys, os, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import l0072_core as C, l0072_ind as X
import run_l0071 as R
R.C = C  # reuse window/summary helpers on the L0072 engine
OUT = os.path.join(os.path.dirname(__file__), "../research/hyp_lab_out/L0072")
WP, WS = R.windows(6, 3, 3), R.windows(12, 3, 3)
END = R.END


def wilson(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); r = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def rand_dist(T, t0, n=1000, seed=72):
    rng = np.random.default_rng(seed); T = T[pd.to_datetime(T.exit_t) >= t0] if len(T) else T; tot = np.zeros(n)
    for s, g in (T.groupby("sym") if len(T) else []):
        P = C.prep(s); o, t, m = P["o"], P["t"], P["mult"]
        lo = int(np.searchsorted(t, t0)); hi = len(o) - 1
        for _, r in g.iterrows():
            b = max(int(r.bars), 1); ks = rng.integers(lo + 1, max(hi - b, lo + 2), n); ke = np.minimum(ks + b, hi)
            tot += r.cost * (o[ke] * (1 - .0003 * m[ke]) * (1 - C.FEE) / (o[ks] * (1 + .0003 * m[ks]) * (1 + C.FEE)) - 1)
    return tot


def cfg_of(nm, **kw):
    return dict(dict(sigfn=X.make_sigfn(nm, kw.pop("thr", None)), tr=(1.0,)), **kw)


def book(nm, **kw):
    r = C.run(cfg_of(nm, **kw), capital=kw.pop("capital", 2000) if "capital" in kw else 2000)
    return r


def run_cfg(names, capital=2000, thr=None, **kw):
    cfg = dict(sigfn=X.make_sigfn(names, thr), tr=(1.0,)); cfg.update(kw)
    return C.run(cfg, capital=capital)


def short(s):
    return {k: s[k] for k in ["net_oos", "pos_windows", "n_windows", "median_window", "n_trades", "avg_trade", "median_trade", "mdd", "layers"]}


def analyse(nm, r, ws, gross=True):
    s, T, eq = R.summarize(r, ws)
    t0 = ws[0][2]; To = T[pd.to_datetime(T.exit_t) >= t0] if len(T) else T
    if len(To):
        g = To.qty * (To.raw_exit - To.raw_entry)
        s["gross_no_cost"] = float(g.sum())
        k = int((To.pnl > 0).sum()); s["win_ci95"] = wilson(k, len(To))
        s["avg_hold_bars"] = float(To.bars.mean())
        s["remove_best_trade"] = float(To.pnl.sum() - To.pnl.max())
        cs = To.groupby("sym").pnl.sum(); s["remove_best_asset"] = float(To.pnl.sum() - cs.max()); s["best_asset"] = cs.idxmax()
        s["avg_notional"] = float(To.cost.mean()); s["cost_paid_est"] = float(s["gross_no_cost"] - To.pnl.sum())
    s["signals_total"] = int(len(r["sigrows"])); s["signals_rejected"] = int(sum(x["status"] != "filled" for x in r["sigrows"]))
    s["reject_reasons"] = pd.Series([x["status"] for x in r["sigrows"]]).value_counts().to_dict() if r["sigrows"] else {}
    return s, T, eq


def classify(sp, ss, rp, rs):
    g = dict(
        c1=sp["net_oos"] > 0, c2=sp["layers"].get("stress_high", -1) > 0, c3=sp["median_window"] > 0,
        c4=sp["pos_windows"] >= .6 * sp["n_windows"], c5=sp["avg_trade"] > 0 and sp["median_trade"] > 0, c6=sp["mdd"] >= -.35,
        c7=sp["max_window_share"] is not None and sp["max_window_share"] <= .4,
        c8=sp["max_coin_share"] is not None and sp["max_coin_share"] <= .35,
        c9=sp["top_trade_share"] is not None and sp["top_trade_share"] < .5,
        c10=sp["net_oos"] > np.percentile(rp, 95) and ss["net_oos"] > np.percentile(rs, 95))
    if all(g.values()): c = "مستقر"
    elif (sp["net_oos"] > np.median(rp) and ss["net_oos"] > np.median(rs)) or sp["net_oos"] > 0 or ss["net_oos"] > 0: c = "واعد غير مثبت"
    else: c = "غير مناسب"
    return c, {k: bool(v) for k, v in g.items()}


def main():
    os.makedirs(OUT, exist_ok=True)
    p1, p2, all_trades, all_sigs, eqs = {}, {}, [], [], {}
    for nm in X.NAMES:
        r = run_cfg(nm)
        sp, T, eq = analyse(nm, r, WP); ss, _, _ = analyse(nm, r, WS)
        rp = rand_dist(T, WP[0][2]); rs = rand_dist(T, WS[0][2])
        cls, gates = classify(sp, ss, rp, rs)
        rnd = dict(primary=dict(median=float(np.median(rp)), p95=float(np.percentile(rp, 95)), pct_rank=float((rp < sp["net_oos"]).mean())),
                   sensitive=dict(median=float(np.median(rs)), p95=float(np.percentile(rs, 95)), pct_rank=float((rs < ss["net_oos"]).mean())))
        caps = {}
        for cap in (4000, 6500, 10000, 13000):
            rc = run_cfg(nm, capital=cap); sc, _, _ = R.summarize(rc, WP)
            caps[cap] = dict(net=sc["net_oos"], pct=sc["net_oos"] / cap, mdd=sc["mdd"], exec=rc["nexec"], rej=rc["nrej"])
        caps[2000] = dict(net=sp["net_oos"], pct=sp["net_oos"] / 2000, mdd=sp["mdd"], exec=r["nexec"], rej=r["nrej"])
        B = R.bh(WP)
        p1[nm] = dict(primary=sp, sensitive=short(ss), random=rnd, classification=cls, gates=gates, capital=caps)
        eqs[nm] = eq
        T.insert(0, "book", nm); all_trades.append(T)
        S = pd.DataFrame(r["sigrows"]); S.insert(0, "book", nm); all_sigs.append(S)
        # pass2: ablations, staged, first touch, mgmt & threshold sensitivity
        v = {}
        v["fixed_stop_only"] = short(R.summarize(run_cfg(nm, protect=False, trail=False), WP)[0])
        v["protect_no_trail"] = short(R.summarize(run_cfg(nm, trail=False), WP)[0])
        v["staged_15_25_30_30"] = short(R.summarize(run_cfg(nm, tr=(0.15, 0.25, 0.30, 0.30)), WP)[0])
        v["first_touch"] = short(R.summarize(run_cfg(X.FT[nm]), WP)[0]) if nm in X.FT else "غير معرّف"
        for k, vals in {"k_stop": (0.75, 1.25), "margin": (0.001, 0.003), "k_trail": (1.0, 2.0)}.items():
            for x in vals: v[f"{k}={x}"] = short(R.summarize(run_cfg(nm, **{k: x}), WP)[0])
        for x in {"I01": (10, 5), "I02": (25, 35), "I03": (30,), "I08": (15, 25), "I10": (14,), "I12": (-1.5, -2.5), "I13": (55,)}.get(nm, ()):
            v[f"thr={x}"] = short(R.summarize(run_cfg(nm, thr=x), WP)[0])
        p2[nm] = v
        print(nm, round(sp["net_oos"], 2), sp["pos_windows"], cls, flush=True)
    B = R.bh(WP)
    union = run_cfg(X.NAMES); su, _, _ = R.summarize(union, WP)
    meta = dict(windows_primary=[[str(x.date()) for x in w] for w in WP], n_sensitive=len(WS), buy_hold_per_coin=B, buy_hold_total=sum(B.values()),
                l0071_reference_only="L0071 الكاملة: −17.50$ (مرجع تاريخي مستقل فقط)", note_I11_I12="I11 وI12 متطابقان رياضيًا: z=−2 ⇔ الحد السفلي BB(20,2) بنفس المتوسط والانحراف (ddof=0)")
    json.dump(dict(meta=meta, books=p1), open(f"{OUT}/results_l0072_pass1.json", "w"), ensure_ascii=False, indent=1, default=float)
    json.dump(dict(variants=p2, union_OR_exploratory=short(su) | dict(max_conc=su["max_conc"], exits=su["exits"])),
              open(f"{OUT}/results_l0072_pass2.json", "w"), ensure_ascii=False, indent=1, default=float)
    pd.concat(all_trades).to_csv(f"{OUT}/trades_l0072.csv", index=False)
    pd.concat(all_sigs).to_csv(f"{OUT}/signals_l0072.csv", index=False)


if __name__ == "__main__":
    main()
