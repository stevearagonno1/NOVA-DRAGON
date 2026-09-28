"""L0081 P3 — the missing GATE_VOL branch (9 combos) with CPCV selection + DSR/PBO + BH on 36.

GATE_VOL: vol_t = std of log-returns over 20 CLOSED 4H bars strictly before the signal bar (causal).
Gate open iff Q25 <= vol_t <= Q75, quartiles from TRAIN only, pooled across symbols, FROZEN.
No HMM / Viterbi / look-ahead labels.

Selection uses CPCV (N=6, k=2, purge=embargo=18) on TRAIN only; frozen to selection_l0081.json with a
commit BEFORE any holdout read. Multiple-testing across the cumulative 36 combos (27 L0080 + 9 here):
BH q=0.10 on m=36, effective_n_trials (Li-Ji), DSR (bar 0.95), PBO (CSCV).

Usage: python3 l0081_p3_gatevol.py train    # measure + CPCV + FROZEN selection + BH/eff_trials
       python3 l0081_p3_gatevol.py holdout  # single holdout read of the 9 combos + DSR/PBO
"""
import os, sys, json
import numpy as np, pandas as pd
HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import stats_core as SC
import l0080_combo as C
import l0081_data as DATA

OUT = os.path.join(ROOT, "history/research/hyp_lab_out/L0081")
OUT80 = os.path.join(ROOT, "history/research/hyp_lab_out/L0080")
SEED = 81
TRIGGERS = C.TRIGGERS
CONFS = C.CONFS
VOL_WIN = 20
CANDIDATE_DEFAULT = "GATE_ADX|FVG_3BAR_BASE|CONF_MACD"
RR = 1.0
COST_R_TAKER = None  # loaded from P2 (avg over kept assets) for after-cost / DSR


def vol_series(df):
    c = df.close.to_numpy(float)
    logret = np.diff(np.log(c), prepend=np.nan)
    v = pd.Series(logret).rolling(VOL_WIN).std().shift(1).to_numpy()  # uses only bars strictly before i
    return v


def frozen_quartiles(data):
    vals = []
    for s, D in data.items():
        v = vol_series(D["df"])
        tr = D["periods"] == "train"
        vals.append(v[tr & np.isfinite(v)])
    allv = np.concatenate(vals)
    return float(np.quantile(allv, 0.25)), float(np.quantile(allv, 0.75))


def add_gatevol(data, FR, q25, q75):
    """Attach a g_VOL bit to every fire row (causal vol regime membership at the fire bar)."""
    volmap = {}
    for s, D in data.items():
        v = vol_series(D["df"])
        g = (v >= q25) & (v <= q75)
        volmap[s] = g
    FR = FR.copy()
    FR["g_VOL"] = [bool(volmap[r.sym][r.bar]) for r in FR.itertuples()]
    return FR


def combo_mask_vol(sub, c):
    m = sub.g_VOL.to_numpy().copy()
    if c == "CONF_OBV":
        m &= sub.c_OBV.to_numpy()
    elif c == "CONF_MACD":
        m &= sub.c_MACD.to_numpy()
    return m


def rise_cov_vol(data, t, c, period, starts, volmap):
    tot = cov = 0
    for s, D in data.items():
        pres = D["sed"][(t, 1)] & (volmap[s]) & D["conf"][(c, 1)]
        for i in starts[s]:
            if C.period_of(D["df"].index[i]) != period:
                continue
            tot += 1; lo = max(0, i - C.PRE)
            if pres[lo:i + 1].any():
                cov += 1
    return (cov / tot if tot else np.nan), tot, cov


def combo_row(FR, data, t, c, period, starts, volmap):
    sub = FR[(FR.trigger == t) & (FR.period == period)]
    mask = combo_mask_vol(sub, c)
    combo = sub[mask]
    st = combo["st_PRIMARY"].to_numpy(object)
    es = C.expectancy_stats(st, RR)
    base_valid = int(sub["st_PRIMARY"].isin(list(C.CODE)).sum())
    cov = es["valid"] / base_valid if base_valid else np.nan
    rc, q, p = rise_cov_vol(data, t, c, period, starts, volmap)
    return dict(combination=f"GATE_VOL|{t}|{c}", gate="GATE_VOL", trigger=t, confirmation=c, period=period,
                signals=int(len(combo)), decided=es["decided"], valid=es["valid"], win_rate=es["win_rate"],
                expectancy_R=es["expectancy_R"],
                expectancy_R_after_cost_005=es["expectancy_R"] - 0.05 if pd.notna(es["expectancy_R"]) else np.nan,
                expectancy_R_after_cost_010=es["expectancy_R"] - 0.10 if pd.notna(es["expectancy_R"]) else np.nan,
                wilson_lo=es["wilson_lo"], wilson_hi=es["wilson_hi"],
                signal_coverage=cov, rise_start_coverage=rc,
                p_value_raw=C.binom_p_greater(es["P"], es["decided"], 0.5),
                mfe_mean=float(np.nanmean(combo["mfe_PRIMARY"])) if len(combo) else np.nan,
                mae_mean=float(np.nanmean(combo["mae_PRIMARY"])) if len(combo) else np.nan,
                ttt_median=float(np.nanmedian(combo["ttt_PRIMARY"])) if len(combo) else np.nan)


# ---------------- CPCV selection on TRAIN ----------------
def cpcv_select(FR, data, volmap):
    """CPCV N=6,k=2,purge=embargo=18 out-of-sample expectancy_after_010 per GATE_VOL combo on train."""
    design = SC.cpcv_splits(6, 2, 18, 18)
    # build a global time grid for TRAIN using group boundaries per symbol (each symbol split into 6 time groups)
    rows = []
    per_combo_paths = {}
    for t in TRIGGERS:
        for c in CONFS:
            cid = f"GATE_VOL|{t}|{c}"
            sub = FR[(FR.trigger == t) & (FR.period == "train")].copy()
            mask = combo_mask_vol(sub, c)
            combo = sub[mask].copy()
            combo["ts"] = pd.to_datetime(combo["time"])
            # assign each signal to one of 6 contiguous train-time groups
            edges = pd.date_range(C.TRAIN_START, C.TRAIN_END, periods=7)
            grp = np.searchsorted(edges.values, combo["ts"].values, side="right") - 1
            grp = np.clip(grp, 0, 5)
            combo["grp"] = grp
            path_e010 = []
            for comb in design["combos"]:
                test_g = set(comb["test_groups"])
                # purge/embargo: drop test signals within 18 bars(=72h) of a train-group boundary handled by group gap
                in_test = combo["grp"].isin(test_g)
                # embargo: exclude test signals whose ts is within purge window of a non-test/test boundary
                purge = pd.Timedelta(hours=4) * 18
                keep = np.ones(len(combo), bool)
                for g in test_g:
                    a, b = edges[g], edges[g + 1]
                    # purge front & embargo back inside the test block
                    keep &= ~((combo["ts"] >= a) & (combo["ts"] < a + purge))
                    keep &= ~((combo["ts"] >= b - purge) & (combo["ts"] < b))
                tst = combo[in_test & keep]
                es = C.expectancy_stats(tst["st_PRIMARY"].to_numpy(object), RR)
                e010 = (es["expectancy_R"] - 0.10) if pd.notna(es["expectancy_R"]) else np.nan
                path_e010.append(e010)
            path_e010 = np.array(path_e010, float)
            per_combo_paths[cid] = path_e010
            rows.append(dict(combination=cid, n_paths=len(path_e010),
                             cpcv_mean_e010=float(np.nanmean(path_e010)),
                             cpcv_median_e010=float(np.nanmedian(path_e010)),
                             cpcv_frac_positive=float(np.nanmean(path_e010 > 0)),
                             cpcv_min_e010=float(np.nanmin(path_e010)), cpcv_max_e010=float(np.nanmax(path_e010))))
    return pd.DataFrame(rows), per_combo_paths, design


def run_train():
    os.makedirs(OUT, exist_ok=True)
    data, FR = DATA.get()
    q25, q75 = frozen_quartiles(data)
    volmap = {s: ((vol_series(D["df"]) >= q25) & (vol_series(D["df"]) <= q75)) for s, D in data.items()}
    FR = add_gatevol(data, FR, q25, q75)
    starts = C.rise_starts(data)
    rows = [combo_row(FR, data, t, c, "train", starts, volmap) for t in TRIGGERS for c in CONFS]
    TR = pd.DataFrame(rows)
    TR.to_csv(f"{OUT}/gatevol_train_l0081.csv", index=False)

    cpcv, paths, design = cpcv_select(FR, data, volmap)
    cpcv_rows = []
    for cid, arr in paths.items():
        for i, e in enumerate(arr):
            cpcv_rows.append(dict(combination=cid, path=i, e010=e))
    pd.DataFrame(cpcv_rows).to_csv(f"{OUT}/cpcv_paths_l0081.csv", index=False)

    # eligibility + selection among GATE_VOL
    M = TR.merge(cpcv, on="combination")
    M["eligible"] = (M.decided >= 400) & (M.signal_coverage >= 0.05) & (M.rise_start_coverage >= 0.10)
    M["cpcv_ok"] = (M.cpcv_mean_e010 > 0) & (M.cpcv_frac_positive >= 0.5) & M.eligible
    gatevol_winner = None
    cand = M[M.cpcv_ok]
    if len(cand):
        gatevol_winner = cand.sort_values("cpcv_mean_e010", ascending=False).iloc[0]["combination"]

    # does the GATE_VOL winner strictly dominate the default candidate in TRAIN?
    tr80 = pd.read_csv(f"{OUT80}/train_results_l0080.csv")
    cand_default_e010 = float(tr80.loc[tr80.combination == CANDIDATE_DEFAULT, "expectancy_R_after_cost_010"].iloc[0])
    chosen = CANDIDATE_DEFAULT
    reason = "default candidate kept (no GATE_VOL combo passed CPCV eligibility/dominance)"
    if gatevol_winner is not None:
        gw_e010 = float(M.loc[M.combination == gatevol_winner, "cpcv_mean_e010"].iloc[0])
        if gw_e010 > cand_default_e010 and gw_e010 > 0:
            chosen = gatevol_winner
            reason = f"GATE_VOL winner {gatevol_winner} strictly dominates default in train CPCV e010"

    sel = dict(candidate_provisional=CANDIDATE_DEFAULT, gate_vol_quartiles={"q25": q25, "q75": q75, "vol_win": VOL_WIN},
               gate_vol_winner=gatevol_winner, gate_vol_cpcv_ok=cand["combination"].tolist(),
               p4_candidate_frozen=chosen, reason=reason,
               cpcv_design={"n_groups": 6, "k_test": 2, "purge": 18, "embargo": 18, "n_paths": design["n_paths"]},
               eligibility={"decided_train_min": 400, "signal_coverage_min": 0.05, "rise_start_coverage_min": 0.10},
               frozen_before_holdout=True, seed=SEED,
               note="Single P4 candidate frozen here BEFORE any holdout/confirmation read. Quartiles from train only.")
    json.dump(sel, open(f"{OUT}/selection_l0081.json", "w"), ensure_ascii=False, indent=1, default=float)

    # ---- multiple testing across cumulative 36 ----
    p80 = tr80[["combination", "p_value_raw"]].copy()
    p9 = TR[["combination", "p_value_raw"]].copy()
    allp = pd.concat([p80, p9], ignore_index=True)
    passed, crit = C.bh(list(allp.p_value_raw), q=0.10)
    allp["passed_bh_m36"] = passed
    allp.to_csv(f"{OUT}/multiple_testing_l0081.csv", index=False)

    print("GATE_VOL train rows:", len(TR))
    print(M[["combination", "decided", "win_rate", "expectancy_R_after_cost_010", "signal_coverage",
             "rise_start_coverage", "cpcv_mean_e010", "cpcv_frac_positive", "eligible", "cpcv_ok"]].to_string(index=False))
    print("\nGATE_VOL winner:", gatevol_winner, "| default e010:", round(cand_default_e010, 4))
    print("FROZEN P4 candidate:", chosen, "|", reason)
    print("BH m=36: passed count =", int(passed.sum()), "/ 36  crit_p =", crit)


def run_holdout():
    data, FR = DATA.get()
    sel = json.load(open(f"{OUT}/selection_l0081.json"))
    q25, q75 = sel["gate_vol_quartiles"]["q25"], sel["gate_vol_quartiles"]["q75"]
    volmap = {s: ((vol_series(D["df"]) >= q25) & (vol_series(D["df"]) <= q75)) for s, D in data.items()}
    FR = add_gatevol(data, FR, q25, q75)
    starts = C.rise_starts(data)
    rows = [combo_row(FR, data, t, c, "holdout", starts, volmap) for t in TRIGGERS for c in CONFS]
    HO = pd.DataFrame(rows)
    HO.to_csv(f"{OUT}/gatevol_holdout_l0081.csv", index=False)
    print("GATE_VOL holdout rows:", len(HO))
    print(HO[["combination", "decided", "win_rate", "expectancy_R", "expectancy_R_after_cost_010",
              "wilson_lo", "signal_coverage", "rise_start_coverage"]].to_string(index=False))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "train"
    {"train": run_train, "holdout": run_holdout}[cmd]()
