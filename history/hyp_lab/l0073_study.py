"""L0073 — MSS / FVG / SFP signal-quality study (signals only; no trade management, no costs, no capital).
Definitions are imported unchanged from nova_v8 (microstructure.py / indicators.py / triggers.py rules).
Rules: history/research/hyp_lab_out/L0073/preregistration_l0073.json
"""
import os, sys, json, hashlib, numpy as np, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT)
from nova_v8 import microstructure as M, indicators as IND

SYMS = ["ATOM", "BNB", "BTC", "ETH", "FIL", "GRAM", "HNT", "IMX", "LINK", "RENDER", "SOL", "VET", "XLM"]
CACHE = os.path.expanduser(os.environ.get("L0073_4H", "~/l007x_4h"))
OUT = os.path.join(ROOT, "history/research/hyp_lab_out/L0073")
END = pd.Timestamp("2026-08-31", tz="UTC")
COMP = ["MSS", "FVG", "SFP"]
COMBOS = {"MSS+FVG": ("MSS", "FVG"), "MSS+SFP": ("MSS", "SFP"), "FVG+SFP": ("FVG", "SFP"), "MSS+FVG+SFP": ("MSS", "FVG", "SFP")}
CFG = {"base": (1.0, 1.0, 6), "sens": (2.0, 1.0, 18)}  # (target ATR, adverse ATR, horizon)
COMBO_WIN = 3; PRE = 3; SEED = 73; NDRAW = 1000


def load(sym, df=None):
    if df is None:
        df = pd.read_parquet(f"{CACHE}/{sym}USDT_4h.parquet")
        df = df[(df.index < END)]
        if "minutes" in df: df = df[df.minutes > 0]
        df = df[["open", "high", "low", "close", "volume"]].dropna()
    return df


def conditions(df):
    """Raw long/short conditions exactly as nova_v8 compute_matrix + build_triggers."""
    o, h, l, c = df.open, df.high, df.low, df.close
    atr = IND.wilder_atr(df, 14)
    mss = M.mss_signal(o.to_numpy(float), h.to_numpy(float), l.to_numpy(float), c.to_numpy(float), atr.to_numpy(float))
    sfp = M.sfp_signal(o, h, l, c).to_numpy()
    bt, bb, st, sb = M.fvg_levels(h.to_numpy(float), l.to_numpy(float))
    fb, fs = np.isfinite(bt), np.isfinite(st)
    co, cc = o.to_numpy(float), c.to_numpy(float)
    cond = {("MSS", 1): mss == 1, ("MSS", -1): mss == -1, ("FVG", 1): fb, ("FVG", -1): fs,
            ("SFP", 1): (sfp == 1) & (cc > co), ("SFP", -1): (sfp == -1) & (cc < co)}
    return cond, atr.to_numpy(float)


def edge(x):
    x = np.asarray(x, bool); return x & ~np.r_[False, x[:-1]]


def fires(df):
    cond, atr = conditions(df)
    F = {k: edge(v) for k, v in cond.items()}
    n = len(df)
    for name, parts in COMBOS.items():
        for d in (1, -1):
            recent = []
            for p in parts:
                f = F[(p, d)].astype(int)
                recent.append(pd.Series(f).rolling(COMBO_WIN, min_periods=1).max().to_numpy() > 0)  # fired in [i-2, i]
            allp = np.logical_and.reduce(recent)
            last_now = np.logical_or.reduce([F[(p, d)] for p in parts])  # one required component fires at i
            F[(name, d)] = edge(allp & last_now)
    return F, atr


def outcome_arrays(df, atr, d, tgt, adv, H):
    """For every bar i: state, bars_to_target, MFE, MAE (ATR units) from bars i+1..i+H."""
    h, l, c = df.high.to_numpy(float), df.low.to_numpy(float), df.close.to_numpy(float)
    n = len(c); st = np.full(n, "invalid_horizon", object); ttt = np.full(n, np.nan); mfe = np.full(n, np.nan); mae = np.full(n, np.nan)
    for i in range(n):
        a = atr[i]
        if not np.isfinite(a) or a <= 0: st[i] = "invalid_atr"; continue
        pt = c[i] + d * tgt * a; nt = c[i] - d * adv * a
        j1 = min(i + H, n - 1); res = None
        for j in range(i + 1, j1 + 1):
            hp = h[j] >= pt if d == 1 else l[j] <= pt
            hn = l[j] <= nt if d == 1 else h[j] >= nt
            if hp and hn: res = ("ambiguous_same_bar", np.nan); break
            if hp: res = ("positive_before_negative", j - i); break
            if hn: res = ("negative_before_positive", np.nan); break
        if res is None:
            res = ("neither_within_window", np.nan) if i + H <= n - 1 else ("invalid_horizon", np.nan)
        st[i], ttt[i] = res
        if j1 >= i + 1:
            hh, ll = h[i + 1:j1 + 1], l[i + 1:j1 + 1]
            if d == 1: mfe[i] = (hh.max() - c[i]) / a; mae[i] = (c[i] - ll.min()) / a
            else: mfe[i] = (c[i] - ll.min()) / a; mae[i] = (hh.max() - c[i]) / a
    return st, ttt, mfe, mae


def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k / n; dd = 1 + z * z / n; ce = p + z * z / (2 * n); r = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((ce - r) / dd, (ce + r) / dd)


def summarize(g):
    s = g.state.value_counts(); n = len(g)
    P, N_, Ne, A = (int(s.get(k, 0)) for k in ["positive_before_negative", "negative_before_positive", "neither_within_window", "ambiguous_same_bar"])
    V = P + N_ + Ne + A; D = P + N_
    t = g.loc[g.state == "positive_before_negative", "bars_to_target"]
    w1, w2 = wilson(P, V), wilson(P, D)
    return dict(signals=n, valid=V, positive_before_negative=P, negative_before_positive=N_, neither_within_window=Ne, ambiguous_same_bar=A,
                invalid=n - V, hit_rate_all=P / V if V else np.nan, hit_all_ci_lo=w1[0], hit_all_ci_hi=w1[1],
                directional_accuracy=P / D if D else np.nan, dir_ci_lo=w2[0], dir_ci_hi=w2[1],
                ambiguous_rate=A / V if V else np.nan, neither_rate=Ne / V if V else np.nan,
                ttt_mean=t.mean(), ttt_median=t.median(), ttt_q1=t.quantile(.25), ttt_q3=t.quantile(.75),
                mfe_mean=g.mfe.mean(), mfe_median=g.mfe.median(), mae_mean=g.mae.mean(), mae_median=g.mae.median())


def build_signals(data):
    rows = []
    for s, (df, F, atr) in data.items():
        for (name, d), f in F.items():
            for i in np.flatnonzero(f):
                rows.append(dict(sym=s, bar=int(i), time=str(df.index[i]), signal=name, kind="combo" if "+" in name else "component",
                                 direction="long" if d == 1 else "short", close=float(df.close.iat[i]), atr14=float(atr[i])))
    return pd.DataFrame(rows).sort_values(["sym", "bar", "signal", "direction"]).reset_index(drop=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    data = {}
    for s in SYMS:
        df = load(s); F, atr = fires(df); data[s] = (df, F, atr)
    S = build_signals(data)
    sig_hash_before = hashlib.sha256(S.to_csv(index=False).encode()).hexdigest()
    S.to_csv(f"{OUT}/signals_l0073.csv", index=False)
    # outcome arrays for every bar (used for signals, rise starts and random control)
    OA = {}
    for s, (df, F, atr) in data.items():
        for cn, (tg, ad, H) in CFG.items():
            for d in (1, -1):
                OA[(s, cn, d)] = outcome_arrays(df, atr, d, tg, ad, H)
    rows = []
    for _, r in S.iterrows():
        d = 1 if r.direction == "long" else -1
        for cn in CFG:
            st, ttt, mfe, mae = OA[(r.sym, cn, d)]
            rows.append(dict(sym=r.sym, bar=r.bar, time=r.time, signal=r.signal, kind=r.kind, direction=r.direction, config=cn,
                             year=r.time[:4], state=st[r.bar], bars_to_target=ttt[r.bar], mfe=mfe[r.bar], mae=mae[r.bar]))
    O = pd.DataFrame(rows); O.to_csv(f"{OUT}/outcomes_l0073.csv", index=False)
    sig_hash_after = hashlib.sha256(build_signals(data).to_csv(index=False).encode()).hexdigest()
    # summaries
    summ = []
    for keys, lvl in [(["config", "signal", "direction"], "all"), (["config", "signal", "direction", "sym"], "asset"),
                      (["config", "signal", "direction", "year"], "year"), (["config", "signal"], "both_directions")]:
        for k, g in O.groupby(keys):
            k = k if isinstance(k, tuple) else (k,)
            summ.append(dict(dict(zip(keys, k)), level=lvl, **summarize(g)))
    SU = pd.DataFrame(summ)
    SU[~SU.signal.str.contains(r"\+")].to_csv(f"{OUT}/summary_l0073.csv", index=False)
    SU[SU.signal.str.contains(r"\+")].to_csv(f"{OUT}/combinations_l0073.csv", index=False)
    mm = O.groupby(["config", "signal", "direction"]).agg(n=("mfe", "size"), mfe_mean=("mfe", "mean"), mfe_median=("mfe", "median"),
            mfe_q1=("mfe", lambda x: x.quantile(.25)), mfe_q3=("mfe", lambda x: x.quantile(.75)), mae_mean=("mae", "mean"),
            mae_median=("mae", "median"), mae_q1=("mae", lambda x: x.quantile(.25)), mae_q3=("mae", lambda x: x.quantile(.75))).reset_index()
    mm.to_csv(f"{OUT}/mae_mfe_l0073.csv", index=False)
    # overlap of components (same bar & within ±2 bars, same direction)
    ov = []
    for d in (1, -1):
        for a in COMP:
            for b in COMP:
                same = near = na = 0
                for s, (df, F, atr) in data.items():
                    fa, fb = F[(a, d)], F[(b, d)]
                    na += int(fa.sum()); same += int((fa & fb).sum())
                    fbn = pd.Series(fb.astype(int)).rolling(5, center=True, min_periods=1).max().to_numpy() > 0
                    near += int((fa & fbn).sum())
                ov.append(dict(direction="long" if d == 1 else "short", a=a, b=b, a_signals=na, same_bar=same, within_2bars=near,
                               same_bar_share=same / na if na else np.nan, within_2_share=near / na if na else np.nan))
    OV = pd.DataFrame(ov)
    # rise starts, coverage, precedence
    pre, starts_n = [], {}
    for s, (df, F, atr) in data.items():
        st = OA[(s, "base", 1)][0]; pos = st == "positive_before_negative"; last = -10 ** 9; cnt = 0
        for i in range(1, len(pos)):
            if pos[i] and not pos[i - 1] and i - last >= 6:
                last = i; cnt += 1
                row = dict(sym=s, start_bar=i, time=str(df.index[i]))
                lags = {}
                for c in COMP:
                    f = F[(c, 1)]; w = np.flatnonzero(f[max(0, i - PRE):i + 1])
                    row[f"{c}_in_window"] = bool(len(w)); first = (max(0, i - PRE) + w[0]) if len(w) else None
                    row[f"{c}_lag"] = (i - first) if first is not None else np.nan  # bars before start (0 = at start)
                    aft = np.flatnonzero(f[i + 1:i + 1 + PRE]); row[f"{c}_after_only"] = bool(len(aft)) and not len(w)
                    if first is not None: lags[c] = first
                if lags:
                    m = min(lags.values()); fst = [c for c, v in lags.items() if v == m]
                    row["first"] = fst[0] if len(fst) == 1 else "tie:" + "+".join(fst)
                else: row["first"] = "none"
                for a, b in [("MSS", "FVG"), ("MSS", "SFP"), ("FVG", "SFP")]:
                    row[f"gap_{a}_{b}"] = (lags[b] - lags[a]) if a in lags and b in lags else np.nan
                pre.append(row)
        starts_n[s] = cnt
    PR = pd.DataFrame(pre); PR.to_csv(f"{OUT}/precedence_l0073.csv", index=False)
    cov = {c: float(PR[f"{c}_in_window"].mean()) for c in COMP}
    cov_asset = PR.groupby("sym")[[f"{c}_in_window" for c in COMP]].mean().round(4).to_dict()
    PR["year"] = PR.time.str[:4]; cov_year = PR.groupby("year")[[f"{c}_in_window" for c in COMP]].mean().round(4).to_dict()
    # random control
    rng = np.random.default_rng(SEED); rc = []
    base_sig = O.copy()
    for (cn, name, dirn), g in base_sig.groupby(["config", "signal", "direction"]):
        d = 1 if dirn == "long" else -1
        hit = np.zeros(NDRAW); dacc = np.zeros(NDRAW); P = np.zeros(NDRAW); V = np.zeros(NDRAW); D = np.zeros(NDRAW)
        for s, gs in g.groupby("sym"):
            st = OA[(s, cn, d)][0]
            lo, hi = int(gs.bar.min()), int(gs.bar.max())
            elig = np.flatnonzero((np.arange(len(st)) >= lo) & (np.arange(len(st)) <= hi) & ~np.isin(st, ["invalid_atr"]))
            k = min(len(gs), len(elig))
            for t in range(NDRAW):
                pick = st[rng.choice(elig, k, replace=False)]
                p = (pick == "positive_before_negative").sum(); ng = (pick == "negative_before_positive").sum()
                v = p + ng + (pick == "neither_within_window").sum() + (pick == "ambiguous_same_bar").sum()
                P[t] += p; V[t] += v; D[t] += p + ng
        hit = P / np.maximum(V, 1); dacc = P / np.maximum(D, 1)
        act = SU[(SU.level == "all") & (SU.config == cn) & (SU.signal == name) & (SU.direction == dirn)].iloc[0]
        rc.append(dict(config=cn, signal=name, direction=dirn, signals=len(g), actual_hit_rate_all=act.hit_rate_all,
                       rand_hit_mean=hit.mean(), rand_hit_median=np.median(hit), rand_hit_p5=np.percentile(hit, 5), rand_hit_p95=np.percentile(hit, 95),
                       hit_pct_rank=float((hit < act.hit_rate_all).mean()),
                       actual_directional_accuracy=act.directional_accuracy, rand_dir_mean=dacc.mean(), rand_dir_median=np.median(dacc),
                       rand_dir_p5=np.percentile(dacc, 5), rand_dir_p95=np.percentile(dacc, 95), dir_pct_rank=float((dacc < act.directional_accuracy).mean())))
    RC = pd.DataFrame(rc); RC.to_csv(f"{OUT}/random_control_l0073.csv", index=False)
    extra = dict(signal_hash_before_outcomes=sig_hash_before, signal_hash_after_outcomes=sig_hash_after, rise_starts_per_asset=starts_n,
                 rise_starts_total=int(sum(starts_n.values())), coverage=cov, coverage_by_asset=cov_asset, coverage_by_year=cov_year,
                 precedence_first_counts=PR["first"].value_counts().to_dict(),
                 after_start_only={c: int(PR[f"{c}_after_only"].sum()) for c in COMP},
                 gap_medians={k: float(PR[k].median()) for k in PR.columns if k.startswith("gap_")},
                 overlap=OV.to_dict("records"), bars_per_asset={s: len(v[0]) for s, v in data.items()},
                 period={s: [str(v[0].index[0]), str(v[0].index[-1])] for s, v in data.items()})
    json.dump(extra, open(f"{OUT}/aux_l0073.json", "w"), ensure_ascii=False, indent=1, default=float)
    return data, S, O, SU, RC, extra


if __name__ == "__main__":
    main()
