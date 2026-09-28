"""L0080 — preregistered gate -> structural trigger -> single confirmation combinations,
judged by expectancy (RR-aware) with transaction costs. 3 gates x 3 triggers x 3 confirmations
= 27 combos (locked). Selection by purged k-fold within TRAIN; holdout read once.
Reuses L0079 structure_edges / indicator_levels and L0073 outcome machinery. No trade mgmt.

Usage: python3 l0080_combo.py train     # train metrics + CV + BH + FROZEN selection
       python3 l0080_combo.py holdout   # OOS holdout (single read) + report inputs
"""
import os, sys, json, math
import numpy as np, pandas as pd
HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import l0073_study as L
import l0079_variants as V

OUT = os.path.join(ROOT, "history/research/hyp_lab_out/L0080")
SYMS = L.SYMS
SEED = 80
NDRAW = 1000
EMBARGO_BARS = 18
PURGE_BARS = 18
KFOLD = 5
PRE = 3
CODE = {"positive_before_negative": 0, "negative_before_positive": 1,
        "neither_within_window": 2, "ambiguous_same_bar": 3}

TRAIN_START = pd.Timestamp("2021-09-01", tz="UTC")
TRAIN_END = pd.Timestamp("2024-08-31", tz="UTC")
HOLDOUT_START = pd.Timestamp("2024-09-04", tz="UTC")
HOLDOUT_END = pd.Timestamp("2026-08-31", tz="UTC")

# target geometries (tgt ATR, adverse ATR, horizon, RR)
TARGETS = {"PRIMARY": (1.0, 1.0, 6, 1.0), "SEC_A": (2.0, 1.0, 18, 2.0), "SEC_B": (1.0, 1.0, 12, 1.0)}
COSTS = [0.05, 0.10]
GATES = ["GATE_NONE", "GATE_EMA200", "GATE_ADX"]
TRIGGERS = ["FVG_3BAR_BASE", "MSS_L5", "SFP_LOOK20"]
CONFS = ["CONF_NONE", "CONF_OBV", "CONF_MACD"]


def period_of(ts):
    t = pd.Timestamp(ts)
    if TRAIN_START <= t < TRAIN_END:
        return "train"
    if HOLDOUT_START <= t < HOLDOUT_END:
        return "holdout"
    return "embargo"


def _ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


# ----------------------------- load & per-symbol arrays -----------------------------
def load_all():
    data = {}
    for s in SYMS:
        df = L.load(s)
        sed, atr = V.structure_edges(df)          # edges for MSS_L5, FVG_3BAR_BASE, SFP_LOOK20 (+others)
        cond = V.indicator_levels(df)             # levels for OBV_SMA20, MACD_8_21_5, ADXDI_20_22 (+others)
        c = df.close.to_numpy(float); ema200 = _ema(c, 200)
        gate = {}
        for d in (1, -1):
            gate[("GATE_NONE", d)] = np.ones(len(df), bool)
            gate[("GATE_EMA200", d)] = (c > ema200) if d == 1 else (c < ema200)
            gate[("GATE_ADX", d)] = cond[("ADXDI_20_22", d)]
        conf = {}
        for d in (1, -1):
            conf[("CONF_NONE", d)] = np.ones(len(df), bool)
            conf[("CONF_OBV", d)] = cond[("OBV_SMA20", d)]
            conf[("CONF_MACD", d)] = cond[("MACD_8_21_5", d)]
        OA = {(tn, d): L.outcome_arrays(df, atr, d, tg, ad, H)
              for tn, (tg, ad, H, rr) in TARGETS.items() for d in (1, -1)}
        data[s] = dict(df=df, sed=sed, gate=gate, conf=conf, OA=OA, n=len(df),
                       times=df.index, periods=np.array([period_of(t) for t in df.index]))
    return data


def combo_id(g, t, c):
    return f"{g}|{t}|{c}"


# ----------------------------- fires frame -----------------------------
def build_fires(data):
    """One row per (trigger fire bar, direction) with gate/conf bits + outcomes for all targets."""
    rows = []
    for s, D in data.items():
        df = D["df"]
        for trig in TRIGGERS:
            for d in (1, -1):
                for i in np.flatnonzero(D["sed"][(trig, d)]):
                    i = int(i)
                    row = dict(sym=s, bar=i, trigger=trig, direction=d, period=D["periods"][i],
                               time=str(df.index[i]), year=str(df.index[i])[:4],
                               g_EMA200=bool(D["gate"][("GATE_EMA200", d)][i]),
                               g_ADX=bool(D["gate"][("GATE_ADX", d)][i]),
                               c_OBV=bool(D["conf"][("CONF_OBV", d)][i]),
                               c_MACD=bool(D["conf"][("CONF_MACD", d)][i]))
                    for tn in TARGETS:
                        st, ttt, mfe, mae = D["OA"][(tn, d)]
                        row[f"st_{tn}"] = st[i]; row[f"ttt_{tn}"] = ttt[i]
                        row[f"mfe_{tn}"] = mfe[i]; row[f"mae_{tn}"] = mae[i]
                    rows.append(row)
    return pd.DataFrame(rows)


def combo_mask(FR, g, c):
    m = np.ones(len(FR), bool)
    if g == "GATE_EMA200":
        m &= FR.g_EMA200.to_numpy()
    elif g == "GATE_ADX":
        m &= FR.g_ADX.to_numpy()
    if c == "CONF_OBV":
        m &= FR.c_OBV.to_numpy()
    elif c == "CONF_MACD":
        m &= FR.c_MACD.to_numpy()
    return m


# ----------------------------- expectancy metrics -----------------------------
def expectancy_stats(states, rr):
    P = int((states == "positive_before_negative").sum())
    N = int((states == "negative_before_positive").sum())
    Ne = int((states == "neither_within_window").sum())
    A = int((states == "ambiguous_same_bar").sum())
    V_ = P + N + Ne + A
    dec = P + N
    wr = P / dec if dec else np.nan
    exp = (wr * rr - (1 - wr)) if dec else np.nan
    lo, hi = L.wilson(P, dec) if dec else (np.nan, np.nan)
    return dict(P=P, N=N, neither=Ne, ambiguous=A, valid=V_, decided=dec, win_rate=wr,
                expectancy_R=exp, wilson_lo=lo, wilson_hi=hi)


def _phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def binom_p_greater(P, n, p0=0.5):
    """One-sided P(X>=P) under Binom(n,p0), normal approx w/ continuity correction."""
    if n == 0:
        return np.nan
    mu = n * p0; sd = math.sqrt(n * p0 * (1 - p0))
    if sd == 0:
        return 1.0
    z = (P - 0.5 - mu) / sd
    return 1 - _phi(z)


def bh(pvals, q=0.10):
    """Benjamini-Hochberg; returns (passed bool array aligned to input, crit_p)."""
    idx = [i for i, p in enumerate(pvals) if not (p is None or (isinstance(p, float) and np.isnan(p)))]
    m = len(idx)
    passed = np.zeros(len(pvals), bool)
    if m == 0:
        return passed, np.nan
    order = sorted(idx, key=lambda i: pvals[i])
    crit = np.nan; kmax = 0
    for rank, i in enumerate(order, 1):
        if pvals[i] <= (rank / m) * q:
            kmax = rank; crit = (rank / m) * q
    for rank, i in enumerate(order, 1):
        if rank <= kmax:
            passed[i] = True
    return passed, crit


# ----------------------------- per-combo metric row -----------------------------
def combo_metrics(FR, data, g, t, c, period, starts):
    sub = FR[(FR.trigger == t) & (FR.period == period)]
    mask = combo_mask(sub, g, c)
    combo = sub[mask]
    base = sub  # GATE_NONE + CONF_NONE for this trigger/period
    out = {"combination": combo_id(g, t, c), "gate": g, "trigger": t, "confirmation": c, "period": period}
    for tn, (tg, ad, H, rr) in TARGETS.items():
        st = combo[f"st_{tn}"].to_numpy(object)
        es = expectancy_stats(st, rr)
        for cost in COSTS:
            es[f"expectancy_R_after_cost_{int(round(cost*100)):03d}"] = (es["expectancy_R"] - cost) if pd.notna(es["expectancy_R"]) else np.nan
        pref = "" if tn == "PRIMARY" else f"{tn.lower()}_"
        out[f"{pref}signals"] = int(len(combo))
        out[f"{pref}decided"] = es["decided"]; out[f"{pref}valid"] = es["valid"]
        out[f"{pref}win_rate"] = es["win_rate"]; out[f"{pref}expectancy_R"] = es["expectancy_R"]
        out[f"{pref}expectancy_R_after_cost_005"] = es["expectancy_R_after_cost_005"]
        out[f"{pref}expectancy_R_after_cost_010"] = es["expectancy_R_after_cost_010"]
        out[f"{pref}wilson_lo"] = es["wilson_lo"]; out[f"{pref}wilson_hi"] = es["wilson_hi"]
        out[f"{pref}neither"] = es["neither"]
        if tn == "PRIMARY":
            out["mfe_mean"] = float(np.nanmean(combo["mfe_PRIMARY"])) if len(combo) else np.nan
            out["mae_mean"] = float(np.nanmean(combo["mae_PRIMARY"])) if len(combo) else np.nan
            out["ttt_median"] = float(np.nanmedian(combo["ttt_PRIMARY"])) if len(combo) else np.nan
            # coverage vs same-trigger baseline
            base_valid = int(base["st_PRIMARY"].isin(list(CODE)).sum())
            out["signal_coverage"] = es["valid"] / base_valid if base_valid else np.nan
            out["raw_ref_valid"] = base_valid
            # lift vs GATE_NONE+CONF_NONE (baseline)
            bes = expectancy_stats(base["st_PRIMARY"].to_numpy(object), rr)
            out["lift_winrate_pp"] = (es["win_rate"] - bes["win_rate"]) * 100 if pd.notna(es["win_rate"]) and pd.notna(bes["win_rate"]) else np.nan
            out["lift_expectancy_after010_R"] = ((es["expectancy_R"] - 0.10) - (bes["expectancy_R"] - 0.10)) if pd.notna(es["expectancy_R"]) and pd.notna(bes["expectancy_R"]) else np.nan
            out["baseline_win_rate"] = bes["win_rate"]
            # p-value (primary)
            out["p_value_raw"] = binom_p_greater(es["P"], es["decided"], 0.5)
            # McNemar vs baseline (filter as directional classifier)
            out.update(mcnemar_vs_baseline(sub, mask))
    # rise start coverage (long combo decision presence)
    out["rise_start_coverage"], out["rise_qualifying"], out["rise_preceded"] = rise_cov_combo(data, g, t, c, period, starts)
    return out


def mcnemar_vs_baseline(sub, mask):
    """Baseline takes every trigger bar (predict dir); combo takes only masked bars (else 'flat').
    correct = win for taker; not-taken correct iff bar was a loss (correctly avoided).
    n01 = base right & combo wrong = not-taken & win ; n10 = combo right & base wrong = not-taken & loss."""
    st = sub["st_PRIMARY"].to_numpy(object)
    dec = np.isin(st, ["positive_before_negative", "negative_before_positive"])
    win = st == "positive_before_negative"
    not_taken = (~mask) & dec
    n01 = int((not_taken & win).sum())      # missed wins
    n10 = int((not_taken & ~win).sum())     # avoided losses
    b = n01 + n10
    if b == 0:
        return dict(mcnemar_stat=0.0, mcnemar_p=1.0, mcnemar_missed_wins=n01, mcnemar_avoided_losses=n10)
    stat = (abs(n10 - n01) - 1) ** 2 / b
    p = math.erfc(math.sqrt(stat / 2)) if stat > 0 else 1.0   # chi-sq(1) survival
    return dict(mcnemar_stat=float(stat), mcnemar_p=float(p), mcnemar_missed_wins=n01, mcnemar_avoided_losses=n10)


# ----------------------------- rise-start coverage -----------------------------
def rise_starts(data):
    starts = {}
    for s, D in data.items():
        st = D["OA"][("PRIMARY", 1)][0]; pos = st == "positive_before_negative"
        last = -10 ** 9; idxs = []
        for i in range(1, len(pos)):
            if pos[i] and not pos[i - 1] and i - last >= 6:
                last = i; idxs.append(i)
        starts[s] = idxs
    return starts


def combo_long_presence(D, g, t, c):
    a = D["sed"][(t, 1)] & D["gate"][(g, 1)] & D["conf"][(c, 1)]
    return a


def rise_cov_combo(data, g, t, c, period, starts):
    tot = cov = 0
    for s, D in data.items():
        pres = combo_long_presence(D, g, t, c)
        for i in starts[s]:
            if period_of(D["df"].index[i]) != period:
                continue
            tot += 1; lo = max(0, i - PRE)
            if pres[lo:i + 1].any():
                cov += 1
    return (cov / tot if tot else np.nan), tot, cov


# ----------------------------- random control -----------------------------
def random_control(FR, data, g, t, c, period, rng):
    sub = FR[(FR.trigger == t) & (FR.period == period)]
    mask = combo_mask(sub, g, c)
    combo = sub[mask]
    rr = TARGETS["PRIMARY"][3]
    act = expectancy_stats(combo["st_PRIMARY"].to_numpy(object), rr)
    if act["decided"] == 0:
        return dict(confirmed=0, actual_win_rate=np.nan, actual_expectancy=np.nan,
                    rand_win_median=np.nan, dir_pct_rank=np.nan, expectancy_pct_rank=np.nan)
    # per-symbol pool: all this-trigger decided bars in period (matched temporal pool), draw k=combo decided
    per_sym = []
    for s, gs in combo.groupby("sym"):
        pool = sub[(sub.sym == s)]
        codes = np.array([CODE.get(x, -1) for x in pool["st_PRIMARY"]])
        codes = codes[codes >= 0]  # decided+neither+amb pool
        k = int(gs["st_PRIMARY"].isin(list(CODE)).sum())
        per_sym.append((codes, k))
    winr = None
    # decided-matched resample per symbol
    P = np.zeros(NDRAW); Dd = np.zeros(NDRAW)
    for pool, k in per_sym:
        if k == 0 or len(pool) == 0:
            continue
        k = min(k, len(pool))
        for i in range(NDRAW):
            pick = pool[rng.choice(len(pool), k, replace=False)]
            P[i] += (pick == 0).sum(); Dd[i] += ((pick == 0) | (pick == 1)).sum()
    wr = P / np.maximum(Dd, 1)
    exp = wr * rr - (1 - wr)
    return dict(confirmed=int(act["decided"]), actual_win_rate=act["win_rate"], actual_expectancy=act["expectancy_R"],
                rand_win_median=float(np.median(wr)), rand_exp_median=float(np.median(exp)),
                dir_pct_rank=float((wr < act["win_rate"]).mean()),
                expectancy_pct_rank=float((exp < act["expectancy_R"]).mean()))


# ----------------------------- purged k-fold (train) -----------------------------
def fold_bounds():
    edges = pd.date_range(TRAIN_START, TRAIN_END, periods=KFOLD + 1)
    return [(edges[i], edges[i + 1]) for i in range(KFOLD)]


def cv_expectancy(FR, data, g, t, c):
    """Per-fold expectancy_after_010 on validation bars (purged near fold edges)."""
    sub = FR[(FR.trigger == t) & (FR.period == "train")].copy()
    mask = combo_mask(sub, g, c)
    combo = sub[mask].copy()
    combo["ts"] = pd.to_datetime(combo["time"])
    bounds = fold_bounds(); rr = TARGETS["PRIMARY"][3]
    rows = []
    for fi, (a, b) in enumerate(bounds):
        purge = pd.Timedelta(hours=4) * PURGE_BARS
        infold = (combo.ts >= a) & (combo.ts < b) & (combo.ts < (b - purge)) & (combo.ts >= (a + (purge if fi > 0 else pd.Timedelta(0))))
        st = combo.loc[infold, "st_PRIMARY"].to_numpy(object)
        es = expectancy_stats(st, rr)
        e010 = (es["expectancy_R"] - 0.10) if pd.notna(es["expectancy_R"]) else np.nan
        rows.append(dict(combination=combo_id(g, t, c), fold=fi, decided=es["decided"],
                         win_rate=es["win_rate"], expectancy_R=es["expectancy_R"],
                         expectancy_R_after_cost_010=e010, positive=bool(pd.notna(e010) and e010 > 0)))
    return rows


# ----------------------------- target geometry (train) -----------------------------
def target_geometry(data):
    rows = []
    for tn, (tg, ad, H, rr) in TARGETS.items():
        states = []
        ttts = []
        for s, D in data.items():
            for d in (1, -1):
                st, ttt, mfe, mae = D["OA"][(tn, d)]
                for i in range(len(st)):
                    if D["periods"][i] != "train":
                        continue
                    states.append(st[i]); ttts.append(ttt[i])
        states = np.array(states, object); ttts = np.array(ttts, float)
        es = expectancy_stats(states, rr)
        be = 1 / (1 + rr)
        med_ttt = float(np.nanmedian(ttts[~np.isnan(ttts)])) if np.isfinite(ttts).any() else np.nan
        exp_per_bar_H = es["expectancy_R"] / H if pd.notna(es["expectancy_R"]) else np.nan
        exp_per_bar_ttt = es["expectancy_R"] / med_ttt if pd.notna(es["expectancy_R"]) and med_ttt else np.nan
        rows.append(dict(target=tn, RR=rr, tgt_atr=tg, adv_atr=ad, horizon=H,
                         unconditional_win_rate=es["win_rate"], breakeven=be,
                         distance_from_breakeven=(es["win_rate"] - be) if pd.notna(es["win_rate"]) else np.nan,
                         decided=es["decided"], valid=es["valid"],
                         neither_rate=es["neither"] / es["valid"] if es["valid"] else np.nan,
                         unconditional_expectancy_R=es["expectancy_R"],
                         expectancy_per_horizon_bar=exp_per_bar_H,
                         expectancy_per_median_ttt=exp_per_bar_ttt, median_ttt=med_ttt))
    return pd.DataFrame(rows)


# ----------------------------- by asset / year -----------------------------
def by_split(FR, g, t, c, period, level):
    sub = FR[(FR.trigger == t) & (FR.period == period)]
    mask = combo_mask(sub, g, c)
    combo = sub[mask]
    rr = TARGETS["PRIMARY"][3]
    rows = []
    for key, grp in combo.groupby("sym" if level == "asset" else "year"):
        es = expectancy_stats(grp["st_PRIMARY"].to_numpy(object), rr)
        rows.append(dict(combination=combo_id(g, t, c), period=period, level=level, key=str(key),
                         decided=es["decided"], win_rate=es["win_rate"],
                         expectancy_R=es["expectancy_R"],
                         expectancy_R_after_cost_010=(es["expectancy_R"] - 0.10) if pd.notna(es["expectancy_R"]) else np.nan))
    return rows


# ----------------------------- catalog -----------------------------
def write_catalog():
    rows = []
    for g in GATES:
        for t in TRIGGERS:
            for c in CONFS:
                rows.append(dict(combination=combo_id(g, t, c), gate=g, trigger=t, confirmation=c,
                                 primary_target="1ATR/-1ATR/6bars RR1.0",
                                 train_period=f"{TRAIN_START.date()}..{TRAIN_END.date()}",
                                 holdout_period=f"{HOLDOUT_START.date()}..{HOLDOUT_END.date()}"))
    df = pd.DataFrame(rows)
    df.to_csv(f"{OUT}/combination_catalog_l0080.csv", index=False)
    assert len(df) == 27, f"expected 27 combos, got {len(df)}"
    return df


# ----------------------------- drivers -----------------------------
def run_train():
    os.makedirs(OUT, exist_ok=True)
    write_catalog()
    data = load_all()
    FR = build_fires(data)
    starts = rise_starts(data)
    target_geometry(data).to_csv(f"{OUT}/target_geometry_l0080.csv", index=False)

    rng = np.random.default_rng(SEED)
    rows = []; cv_rows = []; rc_rows = []; rise_rows = []; split_rows = []
    for g in GATES:
        for t in TRIGGERS:
            for c in CONFS:
                m = combo_metrics(FR, data, g, t, c, "train", starts)
                rows.append(m)
                cv_rows += cv_expectancy(FR, data, g, t, c)
                rc_rows.append(dict(combination=combo_id(g, t, c), period="train",
                                    **random_control(FR, data, g, t, c, "train", rng)))
                rise_rows.append(dict(combination=combo_id(g, t, c), period="train",
                                      rise_start_coverage=m["rise_start_coverage"],
                                      qualifying=m["rise_qualifying"], preceded=m["rise_preceded"]))
                split_rows += by_split(FR, g, t, c, "train", "asset")
                split_rows += by_split(FR, g, t, c, "train", "year")
    TR = pd.DataFrame(rows)
    # BH on primary p-values across the 27 combos
    passed, crit = bh(list(TR["p_value_raw"]), q=0.10)
    TR["passed_bh"] = passed
    # BH p_value_bh (adjusted) = min over ranks
    pv = list(TR["p_value_raw"]); m = 27
    order = np.argsort([x if pd.notna(x) else 2 for x in pv])
    adj = [np.nan] * len(pv); running = 1.0
    for rank_pos in range(len(order) - 1, -1, -1):
        i = order[rank_pos]; r = rank_pos + 1
        if pd.isna(pv[i]):
            adj[i] = np.nan; continue
        val = pv[i] * m / r
        running = min(running, val); adj[i] = min(running, 1.0)
    TR["p_value_bh"] = adj
    # sensitivity BH with target df (m=28)
    passed28, _ = bh(list(TR["p_value_raw"]), q=0.10 * 27 / 28)  # equivalent stricter line for m=28
    TR["passed_bh_targetdf"] = passed28

    TR.to_csv(f"{OUT}/train_results_l0080.csv", index=False)
    pd.DataFrame(cv_rows).to_csv(f"{OUT}/cv_folds_l0080.csv", index=False)
    pd.DataFrame(rc_rows).to_csv(f"{OUT}/random_control_l0080.csv", index=False)
    pd.DataFrame(rise_rows).to_csv(f"{OUT}/rise_coverage_l0080.csv", index=False)
    pd.DataFrame(split_rows).to_csv(f"{OUT}/splits_l0080.csv", index=False)
    # expectancy summary file (all combos, all targets, train)
    exp_cols = ["combination", "gate", "trigger", "confirmation"] + \
        [k for k in TR.columns if k.startswith(("win_rate", "expectancy", "sec_a_", "sec_b_", "wilson"))]
    TR[[c for c in exp_cols if c in TR.columns]].to_csv(f"{OUT}/expectancy_l0080.csv", index=False)
    # multiple testing file
    TR[["combination", "decided", "win_rate", "expectancy_R", "p_value_raw", "p_value_bh",
        "passed_bh", "passed_bh_targetdf"]].to_csv(f"{OUT}/multiple_testing_l0080.csv", index=False)

    # ----- selection via purged k-fold -----
    CV = pd.DataFrame(cv_rows)
    sel = do_selection(TR, CV)
    json.dump(sel, open(f"{OUT}/selection_l0080.json", "w"), ensure_ascii=False, indent=1, default=float)
    print("TRAIN done.", len(TR), "combos.", "selected:", sel["selected"])


def do_selection(TR, CV):
    elig = (TR.decided >= 400) & (TR.signal_coverage >= 0.05) & (TR.rise_start_coverage >= 0.10)
    TR = TR.assign(eligible_train=elig)
    cand = {}
    reasons = {}
    for _, r in TR.iterrows():
        cid = r.combination
        folds = CV[CV.combination == cid]
        pooled_e010 = r["expectancy_R_after_cost_010"]
        n_pos = int(folds.positive.sum()); nf = len(folds)
        crit = {
            "1_pooled_e010_pos": bool(pd.notna(pooled_e010) and pooled_e010 > 0),
            "2_pos_ge_4of5": bool(n_pos >= 4),
            "3_passed_bh": bool(r.passed_bh),
            "4_eligible": bool(r.eligible_train),
        }
        reasons[cid] = dict(crit, folds_positive=n_pos, pooled_e010=float(pooled_e010) if pd.notna(pooled_e010) else None,
                            decided=int(r.decided), signal_coverage=float(r.signal_coverage),
                            rise_start_coverage=float(r.rise_start_coverage) if pd.notna(r.rise_start_coverage) else None,
                            e010_per_bar=(float(pooled_e010 / r.ttt_median) if pd.notna(pooled_e010) and pd.notna(r.ttt_median) and r.ttt_median else None))
        if all(crit.values()):
            cand[cid] = reasons[cid]
    # at most one per trigger; pick highest e010 per holding bar; max 3
    chosen = {}
    for cid, info in cand.items():
        trig = cid.split("|")[1]
        cur = chosen.get(trig)
        val = info["e010_per_bar"] if info["e010_per_bar"] is not None else -1e9
        if cur is None or val > cur[1]:
            chosen[trig] = (cid, val)
    picked = [v[0] for v in sorted(chosen.values(), key=lambda x: -x[1])][:3]
    return dict(train_period=[str(TRAIN_START), str(TRAIN_END)],
                selection_order=["e010>0 pooled 5 folds", ">=4/5 folds positive", "passed BH q=0.10",
                                 "eligibility (decided>=400, cov>=0.05, rise>=0.10)", "highest e010 per holding bar"],
                eligibility={"decided_train_min": 400, "signal_coverage_min": 0.05, "rise_start_coverage_min": 0.10},
                candidates_passing_all=list(cand.keys()), per_combo=reasons,
                selected=picked, n_selected=len(picked),
                note="اختيار من train فقط عبر purged k-fold؛ يُجمّد قبل قراءة holdout. تركيبة واحدة كحد أقصى لكل محفّز، وحد أقصى 3.")


def run_holdout():
    data = load_all()
    FR = build_fires(data)
    starts = rise_starts(data)
    sel = json.load(open(f"{OUT}/selection_l0080.json"))
    rng = np.random.default_rng(SEED)
    rows = []; rc_rows = []; rise_rows = []; split_rows = []
    for g in GATES:
        for t in TRIGGERS:
            for c in CONFS:
                m = combo_metrics(FR, data, g, t, c, "holdout", starts)
                rows.append(m)
                rc_rows.append(dict(combination=combo_id(g, t, c), period="holdout",
                                    **random_control(FR, data, g, t, c, "holdout", rng)))
                rise_rows.append(dict(combination=combo_id(g, t, c), period="holdout",
                                      rise_start_coverage=m["rise_start_coverage"],
                                      qualifying=m["rise_qualifying"], preceded=m["rise_preceded"]))
                split_rows += by_split(FR, g, t, c, "holdout", "asset")
                split_rows += by_split(FR, g, t, c, "holdout", "year")
    HO = pd.DataFrame(rows)
    HO.to_csv(f"{OUT}/holdout_results_l0080.csv", index=False)
    # append holdout to shared files
    for fn, new in [("random_control_l0080.csv", pd.DataFrame(rc_rows)),
                    ("rise_coverage_l0080.csv", pd.DataFrame(rise_rows)),
                    ("splits_l0080.csv", pd.DataFrame(split_rows))]:
        p = f"{OUT}/{fn}"
        if os.path.exists(p):
            old = pd.read_csv(p); old = old[old.period != "holdout"] if "period" in old else old
            new = pd.concat([old, new], ignore_index=True)
        new.to_csv(p, index=False)
    print("HOLDOUT done.", len(HO), "combos; selected:", sel["selected"])


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "train"
    if cmd == "train":
        run_train()
    elif cmd == "holdout":
        run_holdout()
    else:
        raise SystemExit("usage: l0080_combo.py [train|holdout]")
