"""L0081 P3 stats — DSR, PBO (CSCV), effective_n_trials across the cumulative 36 combos.
Builds a monthly performance matrix (rows=year-month, cols=36 combos, value=mean per-trade R),
then computes Li-Ji effective_n_trials, CSCV PBO, and the Deflated Sharpe Ratio of the frozen candidate.
"""
import os, sys, json
import numpy as np, pandas as pd
HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import stats_core as SC
import l0080_combo as C
import l0081_data as DATA
import l0081_p3_gatevol as P3

OUT = os.path.join(ROOT, "history/research/hyp_lab_out/L0081")


def trade_series(FR, gate, trig, conf):
    """Return DataFrame(time, R) of taken decided trades for a combo (R in {+1,-1}, pre-cost)."""
    both = FR[FR.trigger == trig]
    if gate == "GATE_VOL":
        m = P3.combo_mask_vol(both, conf)
    else:
        m = C.combo_mask(both, gate, conf)
    combo = both[m]
    dec = combo[combo.st_PRIMARY.isin(["positive_before_negative", "negative_before_positive"])].copy()
    dec["R"] = np.where(dec.st_PRIMARY == "positive_before_negative", 1.0, -1.0)
    dec["ym"] = pd.to_datetime(dec.time).dt.strftime("%Y-%m")
    return dec[["ym", "R", "time"]]


def main():
    data, FR = DATA.get()
    sel = json.load(open(f"{OUT}/selection_l0081.json"))
    q25, q75 = sel["gate_vol_quartiles"]["q25"], sel["gate_vol_quartiles"]["q75"]
    FR = P3.add_gatevol(data, FR, q25, q75)

    combos = []
    for g in C.GATES:
        for t in C.TRIGGERS:
            for c in C.CONFS:
                combos.append((g, t, c))
    for t in C.TRIGGERS:
        for c in C.CONFS:
            combos.append(("GATE_VOL", t, c))
    assert len(combos) == 36

    # monthly mean-R matrix
    series = {f"{g}|{t}|{c}": trade_series(FR, g, t, c) for (g, t, c) in combos}
    all_ym = sorted(set().union(*[set(s.ym) for s in series.values() if len(s)]))
    ym_index = {y: i for i, y in enumerate(all_ym)}
    M = np.full((len(all_ym), len(combos)), np.nan)
    cols = []
    for j, (g, t, c) in enumerate(combos):
        cid = f"{g}|{t}|{c}"; cols.append(cid)
        s = series[cid]
        if len(s):
            grp = s.groupby("ym").R.mean()
            for y, v in grp.items():
                M[ym_index[y], j] = v
    Mfilled = np.nan_to_num(M, nan=0.0)

    # correlation across combos (only months where both have trades) -> effective_n_trials
    dfM = pd.DataFrame(M, columns=cols)
    corr = dfM.corr(min_periods=6).to_numpy()
    corr = np.nan_to_num(corr, nan=0.0)
    np.fill_diagonal(corr, 1.0)
    eff_trials = SC.effective_n_trials(corr)

    # PBO via CSCV on the filled matrix
    pbo, logits = SC.probability_of_backtest_overfitting(Mfilled, n_splits=8)

    # DSR of the frozen candidate (holdout, after taker cost)
    p2 = json.load(open(f"{OUT}/execution_cost_summary_l0081.json"))
    cost_all = p2["candidate_all_assets"]["avg_cost_R_taker"]
    cand = sel["p4_candidate_frozen"]
    g, t, c = cand.split("|")
    both = FR[(FR.trigger == t) & (FR.period == "holdout")]
    mask = C.combo_mask(both, g, c) if g != "GATE_VOL" else P3.combo_mask_vol(both, c)
    combo = both[mask]
    dec = combo[combo.st_PRIMARY.isin(["positive_before_negative", "negative_before_positive"])]
    Rwin = np.where(dec.st_PRIMARY == "positive_before_negative", 1.0, -1.0) - cost_all
    n_obs = len(Rwin)
    sr = float(np.mean(Rwin) / np.std(Rwin)) if n_obs > 1 and np.std(Rwin) > 0 else 0.0
    def skew_kurt(x):
        x = np.asarray(x, float); m = x.mean(); s = x.std()
        if s == 0 or len(x) < 3:
            return 0.0, 3.0
        return float(np.mean(((x - m) / s) ** 3)), float(np.mean(((x - m) / s) ** 4))
    sk, ku = skew_kurt(Rwin)
    # cross-trial Sharpe std across the 36 combos (holdout per-trade Sharpe)
    trial_sr = []
    for (gg, tt, cc) in combos:
        b = FR[(FR.trigger == tt) & (FR.period == "holdout")]
        mm = C.combo_mask(b, gg, cc) if gg != "GATE_VOL" else P3.combo_mask_vol(b, cc)
        cc2 = b[mm]
        d2 = cc2[cc2.st_PRIMARY.isin(["positive_before_negative", "negative_before_positive"])]
        if len(d2) > 5:
            r = np.where(d2.st_PRIMARY == "positive_before_negative", 1.0, -1.0) - cost_all
            if np.std(r) > 0:
                trial_sr.append(np.mean(r) / np.std(r))
    sr_std = float(np.std(trial_sr)) if len(trial_sr) > 1 else 0.01
    dsr, sr0 = SC.deflated_sharpe_ratio(sr, sr_std, max(2, round(eff_trials)), n_obs, sk, ku)

    result = dict(
        n_combos=36, effective_n_trials=eff_trials,
        pbo=pbo, pbo_n_paths=len(logits), pbo_warning=bool(pbo > 0.50),
        candidate=cand, candidate_after_cost_used_R=cost_all,
        dsr={"sharpe_per_trade_after_cost": sr, "sr_benchmark_expected_max": sr0,
             "sr_std_across_trials": sr_std, "n_trials_effective": round(eff_trials),
             "n_obs": n_obs, "skew": sk, "kurtosis": ku, "DSR": dsr, "DSR_bar": 0.95,
             "passes_dsr": bool(dsr > 0.95)},
        note="PBO via CSCV on monthly mean-R matrix of the 36 combos; effective_n_trials via Li-Ji on their correlation.")
    json.dump(result, open(f"{OUT}/dsr_pbo_l0081.json", "w"), ensure_ascii=False, indent=1, default=float)
    # also persist the perf matrix for auditability
    dfM.insert(0, "year_month", all_ym)
    dfM.to_csv(f"{OUT}/perf_matrix_l0081.csv", index=False)

    print(f"effective_n_trials (of 36): {eff_trials:.2f}")
    print(f"PBO (CSCV, {len(logits)} paths): {pbo:.3f}  warning>0.5: {pbo>0.5}")
    print(f"candidate {cand}: per-trade Sharpe after cost = {sr:.4f} (n={n_obs}), skew={sk:.3f} kurt={ku:.3f}")
    print(f"DSR = {dsr:.4f}  (benchmark SR0={sr0:.4f}, sr_std_trials={sr_std:.4f}) -> passes 0.95: {dsr>0.95}")


if __name__ == "__main__":
    main()
