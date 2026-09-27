"""L0076 selection phase — TRAIN period only. Screens all 7 candidates (pooled over
MSS/FVG/SFP), applies validity gates + ranking, picks ONE indicator per family, and
FREEZES the names into selection_l0076.json BEFORE any holdout result is read.
Writes: screening_train_l0076.csv, selection_l0076.json."""
import os, json
import numpy as np, pandas as pd
import l0076_core as C

DECIDED_MIN = 100
COVERAGE_MIN = 0.20


def main():
    os.makedirs(C.OUT, exist_ok=True)
    data = C.load_all()
    FIRES = C.build_fires(data)
    FIRES.to_csv(f"{C.OUT}/fires_l0076.csv", index=False)

    rows = []
    # pooled (all structures) + per-structure screening on TRAIN, base config
    for cand in C.ALL_CANDIDATES:
        fam = next(f for f, lst in C.FAMILIES.items() if cand in lst)
        # pooled
        sm, conf = C.candidate_metrics(FIRES, cand, "train", "base")
        rc = C.random_control(data, (lambda name: (lambda cond, d, i: bool(cond[(name, d)][i])))(cand),
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
        # per-structure (context, §2)
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
    SCR.to_csv(f"{C.OUT}/screening_train_l0076.csv", index=False)

    # ---- selection: one per family from pooled, valid candidates only ----
    pooled = SCR[SCR.level == "pooled"].copy()
    selection = {}
    reasons = {}
    for fam, cands in C.FAMILIES.items():
        cf = pooled[pooled.candidate.isin(cands) & (pooled.valid == True)].copy()
        if len(cf) == 0:
            selection[fam] = None
            reasons[fam] = "لا مرشح اجتاز البوابات (≥100 محسوم، ≥20% تغطية، يتفوق على وسيط العشوائي)"
            continue
        cf = cf.sort_values(["directional_accuracy", "wilson_lo", "coverage", "hit_rate_all"],
                            ascending=False)
        best = cf.iloc[0]
        selection[fam] = best.candidate
        reasons[fam] = (f"اختير {best.candidate}: دقة اتجاهية {best.directional_accuracy:.4f} على {int(best.decided)} حالة محسومة، "
                        f"تغطية {best.coverage:.3f}، Wilson-lo {best.wilson_lo:.4f}، وسيط العشوائي {best.rand_dir_median:.4f}"
                        + ("" if len(cf) == 1 else f"؛ تصدّر {len(cf)} مرشحًا صالحًا في الفئة"))

    chosen = [v for v in selection.values() if v]
    sel = dict(
        train_period=[str(C.TRAIN_START), str(C.TRAIN_END)],
        gates=dict(decided_min=DECIDED_MIN, coverage_min=COVERAGE_MIN, beats_random_median=True),
        ranking=["directional_accuracy", "wilson_lo", "coverage", "hit_rate_all"],
        selection=selection, reasons=reasons, chosen_names=chosen,
        n_selected=len(chosen),
        frozen_note="هذه الأسماء مُثبتة من train فقط، وتُودَع في commit قبل قراءة أي نتيجة holdout.")
    json.dump(sel, open(f"{C.OUT}/selection_l0076.json", "w"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(dict(selection=selection, n_selected=len(chosen)), ensure_ascii=False, indent=1))
    return SCR, sel


if __name__ == "__main__":
    main()
