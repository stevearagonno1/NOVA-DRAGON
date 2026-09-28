"""L0077 shared core — structure fires (L0073) + expanded classic candidates (l0077_ind,
registered L0072 math), labelled by train / embargo / holdout time-split. No trade mgmt/costs.
Reused unchanged: l0073_study.fires/outcome_arrays/summarize/wilson."""
import os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import l0073_study as L
import l0077_ind as IND

OUT = os.path.join(ROOT, "history/research/hyp_lab_out/L0077")
SYMS = L.SYMS
COMP = ["MSS", "FVG", "SFP"]
FAMILIES = IND.FAMILIES
ALL_CANDIDATES = IND.ALL_CANDIDATES
CFG = L.CFG                     # base (1,1,6), sens (2,1,18)
SEED = 77
NDRAW = 1000
EMBARGO_BARS = 18

TRAIN_START = pd.Timestamp("2021-09-01", tz="UTC")
TRAIN_END = pd.Timestamp("2024-08-31", tz="UTC")      # exclusive
HOLDOUT_START = pd.Timestamp("2024-09-04", tz="UTC")  # inclusive
HOLDOUT_END = pd.Timestamp("2026-08-31", tz="UTC")    # exclusive (data end)

CODE = {"positive_before_negative": 0, "negative_before_positive": 1,
        "neither_within_window": 2, "ambiguous_same_bar": 3}


def period_of(ts):
    t = pd.Timestamp(ts)
    if TRAIN_START <= t < TRAIN_END:
        return "train"
    if HOLDOUT_START <= t < HOLDOUT_END:
        return "holdout"
    return "embargo"


def load_all():
    data = {}
    for s in SYMS:
        df = L.load(s)
        F, atr = L.fires(df)
        cond = IND.candidate_conditions(df)
        OA = {(cn, d): L.outcome_arrays(df, atr, d, tg, ad, H)
              for cn, (tg, ad, H) in CFG.items() for d in (1, -1)}
        data[s] = dict(df=df, F=F, atr=atr, cond=cond, OA=OA, n=len(df))
    return data


def build_fires(data):
    rows = []
    for s, D in data.items():
        df, cond, n = D["df"], D["cond"], D["n"]
        for comp in COMP:
            for d in (1, -1):
                dirn = "long" if d == 1 else "short"
                for i in np.flatnonzero(D["F"][(comp, d)]):
                    i = int(i); ts = str(df.index[i]); per = period_of(df.index[i])
                    cbits = {f"c_{name}": bool(cond[(name, d)][i]) for name in ALL_CANDIDATES}
                    for cn in CFG:
                        st, ttt, mfe, mae = D["OA"][(cn, d)]
                        rows.append(dict(sym=s, bar=i, time=ts, structure=comp, direction=dirn,
                                         period=per, config=cn, state=st[i], bars_to_target=ttt[i],
                                         mfe=mfe[i], mae=mae[i], **cbits))
    return pd.DataFrame(rows)


def summarize_frame(g):
    return L.summarize(g)


def candidate_metrics(FIRES, cand, period, config, structure=None):
    m = FIRES[(FIRES.period == period) & (FIRES.config == config)]
    if structure is not None:
        m = m[m.structure == structure]
        raw_valid = int(m.state.isin(list(CODE)).sum())
    else:
        raw_valid = int(FIRES[(FIRES.period == period) & (FIRES.config == config)].state.isin(list(CODE)).sum())
    conf = m[m[f"c_{cand}"]]
    sm = summarize_frame(conf)
    sm["coverage"] = sm["valid"] / raw_valid if raw_valid else np.nan
    sm["rejection_rate"] = (1 - sm["coverage"]) if pd.notna(sm["coverage"]) else np.nan
    sm["raw_valid"] = raw_valid
    return sm, conf


def consensus_bits(FIRES, names):
    return FIRES[[f"c_{n}" for n in names]].sum(axis=1)


def random_control(data, confirmed_selector, period, config="base", scope_dirs=(1, -1),
                   structures=COMP, seed=SEED, ndraw=NDRAW):
    rng = np.random.default_rng(seed)
    per_sym = []
    P_act = D_act = V_act = 0
    for s, D in data.items():
        for d in scope_dirs:
            stc = D["OA"][(config, d)][0]
            codes = np.array([CODE.get(x, -1) for x in stc])
            for comp in structures:
                Bf = np.flatnonzero(D["F"][(comp, d)])
                Bf = np.array([b for b in Bf if period_of(D["df"].index[b]) == period and codes[b] >= 0], dtype=int)
                if len(Bf) == 0:
                    continue
                real = np.array([confirmed_selector(D["cond"], d, b) for b in Bf], dtype=bool)
                rc = codes[Bf][real]
                per_sym.append((codes[Bf], int(real.sum())))
                P_act += int((rc == 0).sum()); D_act += int(((rc == 0) | (rc == 1)).sum()); V_act += int((rc >= 0).sum())
    if V_act == 0 or D_act == 0:
        return dict(confirmed=int(V_act), actual_dir_acc=np.nan, actual_hit=np.nan,
                    rand_dir_mean=np.nan, rand_dir_median=np.nan, rand_dir_p5=np.nan, rand_dir_p95=np.nan,
                    dir_pct_rank=np.nan)
    act_dir = P_act / D_act; act_hit = P_act / V_act
    P = np.zeros(ndraw); Dd = np.zeros(ndraw); V = np.zeros(ndraw)
    for Bcodes, k in per_sym:
        if k == 0:
            continue
        for t in range(ndraw):
            pick = Bcodes[rng.choice(len(Bcodes), k, replace=False)]
            P[t] += (pick == 0).sum(); Dd[t] += ((pick == 0) | (pick == 1)).sum(); V[t] += (pick >= 0).sum()
    dacc = P / np.maximum(Dd, 1)
    return dict(confirmed=int(V_act), actual_dir_acc=act_dir, actual_hit=act_hit,
                rand_dir_mean=float(dacc.mean()), rand_dir_median=float(np.median(dacc)),
                rand_dir_p5=float(np.percentile(dacc, 5)), rand_dir_p95=float(np.percentile(dacc, 95)),
                dir_pct_rank=float((dacc < act_dir).mean()))
