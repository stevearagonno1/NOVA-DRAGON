"""L0077 selection phase — TRAIN only. Screens all 14 expanded candidates (pooled over
MSS/FVG/SFP), applies validity gates + ranking, picks ONE per family, FREEZES names into
selection_l0077.json BEFORE any holdout result is read.
Writes: screening_train_l0077.csv, selection_l0077.json, fires_l0077.csv."""
import os, json
import numpy as np, pandas as pd
import l0077_core as C

DECIDED_MIN = 100
COVERAGE_MIN = 0.20


def main():
    os.makedirs(C.OUT, exist_ok=True)
    data = C.load_all()
    FIRES = C.build_fires(data)
    FIRES.to_csv(f"{C.OUT}/fires_l0077.csv", index=False)

    rows = []
    for fam, cands in C.FAMILIES.items():
        for cand in cands:
            sm, _ = C.candidate_metrics(FIRES, cand, "train", "base")
            rc = C.random_control(data, (lambda nm: (lambda cond, d, i: bool(cond[(nm, d)][i])))(cand),
                                  "train", "base")
            decided = sm["positive_before_negative"] + sm["negative_before_positive"]
            gate_decided = decided >= DECIDED_MIN
            gate_cov = pd.notna(sm["coverage"]) and sm["coverage"] >= COVERAGE_MIN
            gate_rand = pd.notna(rc["rand_dir_median"]) and pd.notna(sm["directional_accuracy"]) and \
                sm["directional_accuracy"] > rc["rand_dir_median"]
            valid = bool(gate_decided and gate_cov and gate_rand)
            rows.append(dict(candidate=cand, family=fam, level="pooled", structure="ALL",
                decided=int(decided), directional_accuracy=sm["directional_accuracy"], hit_rate_all=sm["hit_rate_all"],
                wilson_lo=sm["dir_ci_lo"], wilson_hi=sm["dir_ci_hi"], coverage=sm["coverage"], rejection_rate=sm["rejection_rate"],
                neither=sm["neither_within_window"], ambiguous=sm["ambiguous_same_bar"], raw_valid=sm["raw_valid"],
                rand_dir_median=rc["rand_dir_median"], dir_pct_rank=rc["dir_pct_rank"],
                gate_decided=gate_decided, gate_coverage=gate_cov, gate_beats_random=gate_rand, valid=valid))
            for comp in C.COMP:
                sm2, _ = C.candidate_metrics(FIRES, cand, "train", "base", structure=comp)
                d2 = sm2["positive_before_negative"] + sm2["negative_before_positive"]
                rows.append(dict(candidate=cand, family=fam, level="structure", structure=comp,
                    decided=int(d2), directional_accuracy=sm2["directional_accuracy"], hit_rate_all=sm2["hit_rate_all"],
                    wilson_lo=sm2["dir_ci_lo"], wilson_hi=sm2["dir_ci_hi"], coverage=sm2["coverage"], rejection_rate=sm2["rejection_rate"],
                    neither=sm2["neither_within_window"], ambiguous=sm2["ambiguous_same_bar"], raw_valid=sm2["raw_valid"],
                    rand_dir_median=np.nan, dir_pct_rank=np.nan,
                    gate_decided=(d2 >= DECIDED_MIN), gate_coverage=(pd.notna(sm2["coverage"]) and sm2["coverage"] >= COVERAGE_MIN),
                    gate_beats_random=np.nan, valid=np.nan))
    SCR = pd.DataFrame(rows)
    SCR.to_csv(f"{C.OUT}/screening_train_l0077.csv", index=False)

    pooled = SCR[SCR.level == "pooled"].copy()
    selection, reasons = {}, {}
    for fam, cands in C.FAMILIES.items():
        cf = pooled[pooled.candidate.isin(cands) & (pooled.valid == True)].copy()
        if len(cf) == 0:
            selection[fam] = None
            reasons[fam] = "لا مرشح اجتاز البوابات (≥100 محسوم، ≥20% تغطية، يتفوق على وسيط العشوائي)"
            continue
        cf = cf.sort_values(["directional_accuracy", "wilson_lo", "coverage", "hit_rate_all"], ascending=False)
        best = cf.iloc[0]
        selection[fam] = best.candidate
        others = ", ".join(f"{r.candidate}({r.directional_accuracy:.4f}/cov{r.coverage:.2f})"
                           for _, r in cf.iloc[1:].iterrows())
        reasons[fam] = (f"اختير {best.candidate}: دقة {best.directional_accuracy:.4f} على {int(best.decided)} محسوم، "
                        f"تغطية {best.coverage:.3f}، Wilson-lo {best.wilson_lo:.4f}، وسيط عشوائي {best.rand_dir_median:.4f}"
                        + (f"؛ منافسون صالحون: {others}" if others else "؛ الوحيد الصالح في الفئة"))

    chosen = [v for v in selection.values() if v]
    sel = dict(train_period=[str(C.TRAIN_START), str(C.TRAIN_END)],
        gates=dict(decided_min=DECIDED_MIN, coverage_min=COVERAGE_MIN, beats_random_median=True),
        ranking=["directional_accuracy", "wilson_lo", "coverage", "hit_rate_all"],
        selection=selection, reasons=reasons, chosen_names=chosen, n_selected=len(chosen),
        valid_triple=(len(chosen) == 3),
        frozen_note="أسماء مُثبتة من train فقط، تُودَع في commit قبل قراءة holdout.")
    json.dump(sel, open(f"{C.OUT}/selection_l0077.json", "w"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(dict(selection=selection, n_selected=len(chosen), valid_triple=len(chosen) == 3), ensure_ascii=False, indent=1))
    return SCR, sel


if __name__ == "__main__":
    main()
