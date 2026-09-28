"""L0077 holdout phase — reads FROZEN names from selection_l0077.json and evaluates them
strictly out-of-sample. Produces holdout singles + combinations + random control. No name is
chosen here. If <3 families produced a candidate, the 2/3 & 3/3 paths are undefined; an
exploratory 2-way combination is emitted, clearly labelled."""
import os, json
import numpy as np, pandas as pd
import l0077_core as C

PERIOD = "holdout"


def base_raw(FIRES, config, structure=None):
    m = FIRES[(FIRES.period == PERIOD) & (FIRES.config == config)]
    if structure is not None:
        m = m[m.structure == structure]
    return C.summarize_frame(m)


def rows_for_mask(FIRES, mask_fn_or_col, label, path_kind, config, raw_pooled, raw_by_struct):
    m = FIRES[(FIRES.period == PERIOD) & (FIRES.config == config)].copy()
    raw_valid_pooled = int(m.state.isin(list(C.CODE)).sum())
    conf_all = m[mask_fn_or_col(m)] if callable(mask_fn_or_col) else m[m[mask_fn_or_col]]
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
        rv = int(m[m.structure == comp].state.isin(list(C.CODE)).sum())
        emit(conf_all[conf_all.structure == comp], "structure", comp, raw_by_struct[comp]["directional_accuracy"], rv)
    for sym, g in conf_all.groupby("sym"):
        rv = int(m[m.sym == sym].state.isin(list(C.CODE)).sum())
        emit(g, "asset", sym, np.nan, rv)
    conf_all = conf_all.assign(year=conf_all.time.str[:4])
    for yr, g in conf_all.groupby("year"):
        rv = int(m.assign(year=m.time.str[:4]).query("year==@yr").state.isin(list(C.CODE)).sum())
        emit(g, "year", yr, np.nan, rv)
    return out


def raw_rows(FIRES, raw_pooled, raw_by_struct):
    out = []
    for cn in C.CFG:
        sm = raw_pooled[cn]
        out.append(dict(path="raw_structure", path_kind="raw", config=cn, level="pooled", key="ALL",
            decided=int(sm["positive_before_negative"] + sm["negative_before_positive"]),
            directional_accuracy=sm["directional_accuracy"], hit_rate_all=sm["hit_rate_all"],
            wilson_lo=sm["dir_ci_lo"], wilson_hi=sm["dir_ci_hi"], diff_vs_raw=0.0, coverage=1.0, rejection_rate=0.0,
            neither=sm["neither_within_window"], ambiguous=sm["ambiguous_same_bar"],
            mfe_mean=sm["mfe_mean"], mae_mean=sm["mae_mean"], ttt_median=sm["ttt_median"], signals=sm["signals"], valid=sm["valid"]))
        for comp in C.COMP:
            smc = raw_by_struct[cn][comp]
            out.append(dict(path="raw_structure", path_kind="raw", config=cn, level="structure", key=comp,
                decided=int(smc["positive_before_negative"] + smc["negative_before_positive"]),
                directional_accuracy=smc["directional_accuracy"], hit_rate_all=smc["hit_rate_all"],
                wilson_lo=smc["dir_ci_lo"], wilson_hi=smc["dir_ci_hi"], diff_vs_raw=0.0, coverage=1.0, rejection_rate=0.0,
                neither=smc["neither_within_window"], ambiguous=smc["ambiguous_same_bar"],
                mfe_mean=smc["mfe_mean"], mae_mean=smc["mae_mean"], ttt_median=smc["ttt_median"], signals=smc["signals"], valid=smc["valid"]))
    return out


def main():
    sel = json.load(open(f"{C.OUT}/selection_l0077.json"))
    names = sel["chosen_names"]
    data = C.load_all()
    FIRES = pd.read_csv(f"{C.OUT}/fires_l0077.csv")
    raw_pooled = {cn: base_raw(FIRES, cn) for cn in C.CFG}
    raw_by_struct = {cn: {comp: base_raw(FIRES, cn, comp) for comp in C.COMP} for cn in C.CFG}

    hrows = raw_rows(FIRES, raw_pooled, raw_by_struct)
    for cn in C.CFG:
        for name in names:
            hrows += rows_for_mask(FIRES, f"c_{name}", name, "single", cn, raw_pooled[cn], raw_by_struct[cn])
    pd.DataFrame(hrows).to_csv(f"{C.OUT}/holdout_results_l0077.csv", index=False)

    n = len(names)
    valid_triple = bool(sel.get("valid_triple", n == 3))
    crows = []
    if valid_triple:
        note = "الفئات الثلاث قدّمت مرشحين ⇒ يُقاس 2/3 و3/3 على holdout."
        cnt = C.consensus_bits(FIRES, names); FIRES2 = FIRES.assign(_cnt=cnt)
        for cn in C.CFG:
            crows += rows_for_mask(FIRES2, (lambda mm: mm._cnt >= 2), "2of3", "combo_2of3", cn, raw_pooled[cn], raw_by_struct[cn])
            crows += rows_for_mask(FIRES2, (lambda mm: mm._cnt >= 3), "3of3", "combo_3of3", cn, raw_pooled[cn], raw_by_struct[cn])
    else:
        note = ("لم يوجد اختيار ثلاثي صالح (الأسماء الصالحة=%d؛ الفئة B بلا مرشح). "
                "مساري 2/3 و3/3 المسجلين غير مُعرّفين. يُعرض تركيب ثنائي استكشافي (both/either) موسوم بوضوح أنه ليس 2/3–3/3." % n)
        if n >= 2:
            cnt = C.consensus_bits(FIRES, names); FIRES2 = FIRES.assign(_cnt=cnt)
            for cn in C.CFG:
                crows += rows_for_mask(FIRES2, (lambda mm: mm._cnt >= n), f"ALL_of_{n}({'+'.join(names)})", "combo_all", cn, raw_pooled[cn], raw_by_struct[cn])
                crows += rows_for_mask(FIRES2, (lambda mm: mm._cnt >= 1), f"ANY_of_{n}({'+'.join(names)})", "combo_any", cn, raw_pooled[cn], raw_by_struct[cn])
    pd.DataFrame(crows).to_csv(f"{C.OUT}/combination_results_l0077.csv", index=False)
    json.dump(dict(note=note, valid_triple=valid_triple, n_selected=n, names=names),
              open(f"{C.OUT}/combination_status_l0077.json", "w"), ensure_ascii=False, indent=1)

    rc_rows = []
    for name in names:
        rc = C.random_control(data, (lambda nm: (lambda cond, d, i: bool(cond[(nm, d)][i])))(name), PERIOD, "base")
        rc_rows.append(dict(path=name, path_kind="single", **rc))
    if valid_triple:
        cnt_fn2 = (lambda nms: (lambda cond, d, i: sum(bool(cond[(x, d)][i]) for x in nms) >= 2))(names)
        rc_rows.append(dict(path="2of3", path_kind="combo_2of3", **C.random_control(data, cnt_fn2, PERIOD, "base")))
        cnt_fn3 = (lambda nms: (lambda cond, d, i: sum(bool(cond[(x, d)][i]) for x in nms) >= 3))(names)
        rc_rows.append(dict(path="3of3", path_kind="combo_3of3", **C.random_control(data, cnt_fn3, PERIOD, "base")))
    elif n >= 2:
        both_fn = (lambda nms: (lambda cond, d, i: all(bool(cond[(x, d)][i]) for x in nms)))(names)
        rc_rows.append(dict(path=f"ALL_of_{n}", path_kind="combo_all", **C.random_control(data, both_fn, PERIOD, "base")))
        any_fn = (lambda nms: (lambda cond, d, i: any(bool(cond[(x, d)][i]) for x in nms)))(names)
        rc_rows.append(dict(path=f"ANY_of_{n}", path_kind="combo_any", **C.random_control(data, any_fn, PERIOD, "base")))
    pd.DataFrame(rc_rows).to_csv(f"{C.OUT}/random_control_l0077.csv", index=False)
    print("holdout done. names:", names, "| valid_triple:", valid_triple)


if __name__ == "__main__":
    main()
