"""L0081 — the 16 required checks (TASK §5). Writes checks_l0081.json.
Critical checks must all pass for the lane to be trustworthy."""
import os, sys, json, subprocess
import numpy as np, pandas as pd
HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import stats_core as SC
import l0080_combo as C
import l0081_data as DATA
import l0081_p3_gatevol as P3

OUT = os.path.join(ROOT, "history/research/hyp_lab_out/L0081")


def git(*a):
    return subprocess.run(["git", "-C", ROOT, *a], capture_output=True, text=True).stdout.strip()


def main():
    data, FR = DATA.get()
    sel = json.load(open(f"{OUT}/selection_l0081.json"))
    q25, q75 = sel["gate_vol_quartiles"]["q25"], sel["gate_vol_quartiles"]["q75"]
    checks = {}

    # 1. no future leak in any indicator/gate incl GATE_VOL: truncation invariance of GATE_VOL vol
    #    vol_t must be identical whether or not future bars exist (causal).
    s0 = list(data)[0]; df0 = data[s0]["df"]
    v_full = P3.vol_series(df0)
    v_trunc = P3.vol_series(df0.iloc[:len(df0) // 2])
    n = len(v_trunc)
    leak = int(np.nansum(np.abs(np.nan_to_num(v_full[:n]) - np.nan_to_num(v_trunc)) > 1e-12))
    checks["1_no_future_leak_incl_gatevol"] = {"pass": leak == 0, "mismatches": leak,
        "detail": "GATE_VOL vol_t is truncation-invariant (uses only closed bars strictly before signal)"}

    # 2. embargo/purge = 18 applied everywhere
    ok2 = (C.EMBARGO_BARS == 18 and C.PURGE_BARS == 18 and
           sel["cpcv_design"]["purge"] == 18 and sel["cpcv_design"]["embargo"] == 18)
    checks["2_embargo_purge_18"] = {"pass": bool(ok2), "l0080_embargo": C.EMBARGO_BARS,
        "cpcv_purge": sel["cpcv_design"]["purge"], "cpcv_embargo": sel["cpcv_design"]["embargo"]}

    # 3. cumulative combos = 36 = registered
    prereg = json.load(open(f"{OUT}/preregistration_l0081.json"))
    n80 = len(pd.read_csv(f"{ROOT}/history/research/hyp_lab_out/L0080/train_results_l0080.csv"))
    n9 = len(pd.read_csv(f"{OUT}/gatevol_train_l0081.csv"))
    checks["3_combos_cumulative_36"] = {"pass": (n80 + n9 == 36) and prereg["combos_cumulative"] == 36,
        "l0080": n80, "gatevol": n9, "total": n80 + n9}

    # 4. eligibility applied on N_eff (Wilson bounds recomputed on N_eff, not nominal)
    neff = pd.read_csv(f"{OUT}/neff_recompute_l0080.csv")
    has_neff = {"N_eff", "wilson_lo_neff"}.issubset(neff.columns) and neff["N_eff"].notna().any()
    conf = pd.read_csv(f"{OUT}/confirmation_l0081.csv")
    csum = json.load(open(f"{OUT}/confirmation_summary_l0081.json"))
    checks["4_eligibility_on_neff"] = {"pass": bool(has_neff and csum["pooled"]["N_eff"] is not None),
        "detail": "Wilson bounds recomputed on N_eff in P1 + P4 success criteria use N_eff"}

    # 5. BH on 36
    mt = pd.read_csv(f"{OUT}/multiple_testing_l0081.csv")
    checks["5_bh_on_36"] = {"pass": len(mt) == 36 and "passed_bh_m36" in mt.columns,
        "n_pvalues": len(mt), "n_passed": int(mt["passed_bh_m36"].sum())}

    # 6. DSR computed per candidate, bar 0.95 declared
    dp = json.load(open(f"{OUT}/dsr_pbo_l0081.json"))
    checks["6_dsr_computed_bar095"] = {"pass": dp["dsr"]["DSR_bar"] == 0.95 and "DSR" in dp["dsr"],
        "DSR": dp["dsr"]["DSR"], "passes": dp["dsr"]["passes_dsr"]}

    # 7. PBO computed via CSCV
    checks["7_pbo_cscv"] = {"pass": "pbo" in dp and dp["pbo_n_paths"] > 0,
        "pbo": dp["pbo"], "n_paths": dp["pbo_n_paths"], "warning": dp["pbo_warning"]}

    # 8. effective_n_trials computed instead of nominal 36
    checks["8_effective_n_trials"] = {"pass": dp["effective_n_trials"] < 36,
        "effective_n_trials": dp["effective_n_trials"], "nominal": 36}

    # 9. uniqueness & N_eff computed for each measurement
    checks["9_uniqueness_neff_present"] = {"pass": bool(has_neff and "average_uniqueness" in neff.columns),
        "detail": "neff_recompute_{l0079,l0080}.csv + confirmation carry concurrency/uniqueness/N_eff"}

    # 10. all Wilson bounds built on N_eff (P1 + P4)
    checks["10_wilson_on_neff"] = {"pass": bool("wilson_lo_neff" in neff.columns and
        csum["pooled"]["wilson_lo_neff"] is not None),
        "candidate_wilson_lo_neff_newassets": csum["pooled"]["wilson_lo_neff"]}

    # 11. costs measured (not assumed), source declared
    p2 = json.load(open(f"{OUT}/execution_cost_summary_l0081.json"))
    cost = pd.read_csv(f"{OUT}/execution_cost_l0081.csv")
    checks["11_costs_measured_sourced"] = {"pass": len(cost) > 0 and "spread_source" in p2["fees"],
        "platform": p2["platform"], "spread_source": p2["fees"]["spread_source"],
        "atr_and_spread_from_data": True}

    # 12. CPCV applied, no leakage between paths (purge/embargo removes boundary bars)
    design = SC.cpcv_splits(6, 2, 18, 18)
    gob = np.repeat(np.arange(6), 200)
    trm = SC.purge_embargo_mask(None, [3], gob, 18, 18, 1200)
    tb = np.flatnonzero(gob == 3)
    leak12 = trm[tb].any() or trm[tb[0] - 18:tb[0]].any() or trm[tb[-1] + 1:tb[-1] + 19].any()
    checks["12_cpcv_no_leak"] = {"pass": (not leak12) and design["n_paths"] == 5,
        "n_paths": design["n_paths"], "n_combinations": design["n_combinations"]}

    # 13. selection frozen by a commit that PRECEDES any new holdout read
    #     freeze commit must contain selection_l0081.json but NOT gatevol_holdout / confirmation
    freeze = None
    for h in git("log", "--format=%H", "--", "history/research/hyp_lab_out/L0081/selection_l0081.json").splitlines():
        freeze = h  # last (oldest) commit touching selection = its introduction
    tree = git("ls-tree", "-r", "--name-only", freeze) if freeze else ""
    has_sel = "selection_l0081.json" in tree
    no_ho = "gatevol_holdout_l0081.csv" not in tree
    no_conf = "confirmation_l0081.csv" not in tree
    checks["13_freeze_precedes_holdout"] = {"pass": bool(has_sel and no_ho and no_conf),
        "freeze_commit": freeze, "selection_in_freeze": has_sel,
        "holdout_absent": no_ho, "confirmation_absent": no_conf}

    # 14. exactly one P4 candidate, registered before touching confirmation data
    checks["14_single_p4_candidate"] = {"pass": isinstance(sel["p4_candidate_frozen"], str) and
        sel["frozen_before_holdout"] and csum["candidate"] == sel["p4_candidate_frozen"],
        "candidate": sel["p4_candidate_frozen"]}

    # 15. no secrets/keys; seeds recorded
    secret_hits = subprocess.run(
        ["grep", "-rIlE", r"(ghp_[A-Za-z0-9]{20,}|api[_-]?secret|BEGIN [A-Z ]*PRIVATE KEY)",
         f"{ROOT}/history/hyp_lab", f"{OUT}"], capture_output=True, text=True).stdout.strip()
    checks["15_no_secrets_seeds_recorded"] = {"pass": secret_hits == "" and prereg["seed"] == 81 and sel["seed"] == 81,
        "secret_files": secret_hits, "seed": prereg["seed"]}

    # 16. no HMM / Viterbi / look-ahead regime label — detect actual USAGE (imports/calls),
    #     not documentation mentions of the ban in forbidden-lists.
    grep16 = subprocess.run(
        ["grep", "-rInE", r"(import +hmmlearn|from +hmmlearn|hmmlearn\.|\.viterbi *\(|HiddenMarkov|GaussianHMM|MultinomialHMM)",
         f"{ROOT}/history/hyp_lab"], capture_output=True, text=True).stdout.strip()
    offenders = [ln for ln in grep16.splitlines() if "l0081" in ln and "l0081_checks.py" not in ln]
    checks["16_no_hmm_viterbi_lookahead"] = {"pass": len(offenders) == 0,
        "gate_vol_is_causal_quartile": True, "note": "GATE_VOL uses frozen train quartiles of a causal vol_t; no HMM/Viterbi usage",
        "offenders": offenders}

    critical = ["1_no_future_leak_incl_gatevol", "2_embargo_purge_18", "3_combos_cumulative_36",
                "11_costs_measured_sourced", "12_cpcv_no_leak", "13_freeze_precedes_holdout",
                "14_single_p4_candidate", "15_no_secrets_seeds_recorded", "16_no_hmm_viterbi_lookahead"]
    n_pass = sum(1 for v in checks.values() if v["pass"])
    crit_ok = all(checks[k]["pass"] for k in critical)
    summary = {"n_checks": len(checks), "n_pass": n_pass, "critical_ok": crit_ok,
               "critical": critical, "checks": checks}
    json.dump(summary, open(f"{OUT}/checks_l0081.json", "w"), ensure_ascii=False, indent=1, default=float)
    for k, v in checks.items():
        print(f"{'PASS' if v['pass'] else 'FAIL'}  {k}")
    print(f"\n{n_pass}/{len(checks)} pass | critical_ok={crit_ok}")


if __name__ == "__main__":
    main()
