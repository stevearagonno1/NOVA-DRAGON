"""L0076 holdout phase — reads FROZEN names from selection_l0076.json and evaluates them
strictly out-of-sample (2024-09-04 .. 2026-08-30). Produces holdout singles + combinations
+ random control. No name is chosen here; names come only from the frozen selection file."""
import os, json
import numpy as np, pandas as pd
import l0076_core as C

PERIOD = "holdout"


def base_raw(FIRES, config, structure=None):
    m = FIRES[(FIRES.period == PERIOD) & (FIRES.config == config)]
    if structure is not None:
        m = m[m.structure == structure]
    return C.summarize_frame(m)


def rows_for_mask(FIRES, mask_col_or_fn, label, path_kind, config, raw_pooled, raw_by_struct):
    """Emit pooled / per-structure / per-asset / per-year rows for a confirmed subset."""
    m = FIRES[(FIRES.period == PERIOD) & (FIRES.config == config)].copy()
    raw_valid_pooled = int(m.state.isin(list(C.CODE)).sum())
    if callable(mask_col_or_fn):
        conf_all = m[mask_col_or_fn(m)]
    else:
        conf_all = m[m[mask_col_or_fn]]
    out = []

    def emit(g, level, key, raw_acc, raw_valid):
        sm = C.summarize_frame(g)
        dec = sm["positive_before_negative"] + sm["negative_before_positive"]
        gain = (sm["directional_accuracy"] - raw_acc) if pd.notna(sm["directional_accuracy"]) and pd.notna(raw_acc) else np.nan
        cov = sm["valid"] / raw_valid if raw_valid else np.nan
        out.append(dict(path=label, path_kind=path_kind, config=config, level=level, key=key,
            decided=int(dec), directional_accuracy=sm["directional_accuracy"], hit_rate_all=sm["hit_rate_all"],
            wilson_lo=sm["dir_ci_lo"], wilson_hi=sm["dir_ci_hi"], diff_vs_raw=gain, coverage=cov,
            rejection_rate=(1 - cov) if pd.notna(cov) else np.nan,
            neither=sm["neither_within_window"], ambiguous=sm["ambiguous_same_bar"],
            mfe_mean=sm["mfe_mean"], mae_mean=sm["mae_mean"], ttt_median=sm["ttt_median"],
            signals=sm["signals"], valid=sm["valid"]))

    emit(conf_all, "pooled", "ALL", raw_pooled["directional_accuracy"], raw_valid_pooled)
    for comp in C.COMP:
        g = conf_all[conf_all.structure == comp]
        rv = int(m[m.structure == comp].state.isin(list(C.CODE)).sum())
        emit(g, "structure", comp, raw_by_struct[comp]["directional_accuracy"], rv)
    for sym, g in conf_all.groupby("sym"):
        rv = int(m[m.sym == sym].state.isin(list(C.CODE)).sum())
        emit(g, "asset", sym, np.nan, rv)
    conf_all = conf_all.assign(year=conf_all.time.str[:4])
    for yr, g in conf_all.groupby("year"):
        rv = int(m.assign(year=m.time.str[:4]).query("year==@yr").state.isin(list(C.CODE)).sum())
        emit(g, "year", yr, np.nan, rv)
    return out


def main():
    sel = json.load(open(f"{C.OUT}/selection_l0076.json"))
    names = sel["chosen_names"]                       # FROZEN — not chosen here
    data = C.load_all()
    FIRES = pd.read_csv(f"{C.OUT}/fires_l0076.csv")

    # raw baselines on holdout
    raw_pooled = {cn: base_raw(FIRES, cn) for cn in C.CFG}
    raw_by_struct = {cn: {comp: base_raw(FIRES, cn, comp) for comp in C.COMP} for cn in C.CFG}

    # ---- holdout_results: raw + each single selected ----
    hrows = []
    for cn in C.CFG:
        # raw structure rows
        rvp = int(FIRES[(FIRES.period == PERIOD) & (FIRES.config == cn)].state.isin(list(C.CODE)).sum())
        sm = raw_pooled[cn]
        hrows.append(dict(path="raw_structure", path_kind="raw", config=cn, level="pooled", key="ALL",
            decided=int(sm["positive_before_negative"] + sm["negative_before_positive"]),
            directional_accuracy=sm["directional_accuracy"], hit_rate_all=sm["hit_rate_all"],
            wilson_lo=sm["dir_ci_lo"], wilson_hi=sm["dir_ci_hi"], diff_vs_raw=0.0, coverage=1.0,
            rejection_rate=0.0, neither=sm["neither_within_window"], ambiguous=sm["ambiguous_same_bar"],
            mfe_mean=sm["mfe_mean"], mae_mean=sm["mae_mean"], ttt_median=sm["ttt_median"],
            signals=sm["signals"], valid=sm["valid"]))
        for comp in C.COMP:
            smc = raw_by_struct[cn][comp]
            hrows.append(dict(path="raw_structure", path_kind="raw", config=cn, level="structure", key=comp,
                decided=int(smc["positive_before_negative"] + smc["negative_before_positive"]),
                directional_accuracy=smc["directional_accuracy"], hit_rate_all=smc["hit_rate_all"],
                wilson_lo=smc["dir_ci_lo"], wilson_hi=smc["dir_ci_hi"], diff_vs_raw=0.0, coverage=1.0,
                rejection_rate=0.0, neither=smc["neither_within_window"], ambiguous=smc["ambiguous_same_bar"],
                mfe_mean=smc["mfe_mean"], mae_mean=smc["mae_mean"], ttt_median=smc["ttt_median"],
                signals=smc["signals"], valid=smc["valid"]))
        for name in names:
            hrows += rows_for_mask(FIRES, f"c_{name}", name, "single", cn, raw_pooled[cn], raw_by_struct[cn])
    HR = pd.DataFrame(hrows)
    HR.to_csv(f"{C.OUT}/holdout_results_l0076.csv", index=False)

    # ---- combinations among selected names ----
    # Preregistered 2/3 & 3/3 need THREE names. Only len(names) selected -> record status.
    crows = []
    n = len(names)
    combo_note = ("الأسماء المختارة الصالحة = %d فقط (الفئة B لم تقدم مرشحًا صالحًا). "
                  "مساري 2/3 و3/3 المسجلين مسبقًا يتطلبان ثلاثة أسماء ⇒ غير مُعرّفين. "
                  "يُعرض بدلًا منهما تركيب ثنائي استكشافي (both/either) موسومًا بوضوح أنه ليس مسار 2/3–3/3 المسجل." % n)
    if n >= 2:
        cnt = C.consensus_bits(FIRES, names)
        FIRES2 = FIRES.assign(_cnt=cnt)
        for cn in C.CFG:
            crows += rows_for_mask(FIRES2, (lambda mm: mm._cnt >= n), f"ALL_of_{n}({'+'.join(names)})",
                                   "combo_all", cn, raw_pooled[cn], raw_by_struct[cn])
            crows += rows_for_mask(FIRES2, (lambda mm: mm._cnt >= 1), f"ANY_of_{n}({'+'.join(names)})",
                                   "combo_any", cn, raw_pooled[cn], raw_by_struct[cn])
    CR = pd.DataFrame(crows)
    CR.attrs["note"] = combo_note
    CR.to_csv(f"{C.OUT}/combination_results_l0076.csv", index=False)
    json.dump(dict(note=combo_note, three_way_2of3_3of3_defined=(n >= 3), n_selected=n, names=names),
              open(f"{C.OUT}/combination_status_l0076.json", "w"), ensure_ascii=False, indent=1)

    # ---- random control on holdout (base): singles + both ----
    rc_rows = []
    for name in names:
        sel_fn = (lambda nm: (lambda cond, d, i: bool(cond[(nm, d)][i])))(name)
        rc = C.random_control(data, sel_fn, PERIOD, "base")
        rc_rows.append(dict(path=name, path_kind="single", **rc))
    if n >= 2:
        both_fn = (lambda nms: (lambda cond, d, i: all(bool(cond[(x, d)][i]) for x in nms)))(names)
        rc = C.random_control(data, both_fn, PERIOD, "base")
        rc_rows.append(dict(path=f"ALL_of_{n}", path_kind="combo_all", **rc))
        any_fn = (lambda nms: (lambda cond, d, i: any(bool(cond[(x, d)][i]) for x in nms)))(names)
        rc = C.random_control(data, any_fn, PERIOD, "base")
        rc_rows.append(dict(path=f"ANY_of_{n}", path_kind="combo_any", **rc))
    RC = pd.DataFrame(rc_rows)
    RC.to_csv(f"{C.OUT}/random_control_l0076.csv", index=False)
    print("holdout done. names:", names, "| combos defined for 2/3-3/3:", n >= 3)
    return HR, CR, RC


if __name__ == "__main__":
    main()
