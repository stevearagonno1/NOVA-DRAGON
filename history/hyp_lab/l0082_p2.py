#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0082 · P2 — تشريح FVG · اثنتا عشرة خاصية + نقاط الدخول · G2

تُقاس على TRAIN فقط، على الهندسة المرجعية (1×ATR، أفق 6).
كل خاصية مستمرة: خمس شرائح متساوية العدد، حدودها من TRAIN فقط ومجمّدة.
تصحيح Benjamini–Hochberg على m=62. كل الشرائح تُبلَّغ (الرابحة والخاسرة).
"""
from __future__ import annotations

import json
import sys
import pathlib
import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import l0082_common as C  # noqa: E402
import l0082_engine as E  # noqa: E402

CACHE = C.OUT / "_cache"
CONT = ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A11"]  # 10 مستمرة
MIN_EFF = 300  # عينة فعلية دنيا للبناء
LEAK_ALARM = 0.60


def bh_correct(pvals, m):
    """Benjamini–Hochberg. يعيد q-values محاذية لترتيب الإدخال. m = مجموع الاختبارات."""
    idx = [i for i, p in enumerate(pvals) if p is not None and not (isinstance(p, float) and np.isnan(p))]
    ps = [(pvals[i], i) for i in idx]
    ps.sort()
    q = [None] * len(pvals)
    prev = 1.0
    for rank in range(len(ps) - 1, -1, -1):
        p, i = ps[rank]
        val = p * m / (rank + 1)
        prev = min(prev, val)
        q[i] = min(prev, 1.0)
    return q


def main():
    S = pd.read_parquet(CACHE / "signals_ref.parquet")
    overlaps = json.loads((CACHE / "overlaps_ref.json").read_text())
    cost_look = E.cost_lookup_factory()

    # الرمز outcome/rr للهندسة المرجعية
    S = S.rename(columns={"e1_outcome": "outcome", "e1_rr": "rr"})
    train = E.in_period(S, *C.TRAIN)
    print(f"[P2] TRAIN signals = {len(train)}")

    boundaries = {}
    anatomy_rows = []
    tests = []  # (test_id, win_rate, n_eff, p_value)

    def add_row(feature, slice_label, sub, rng=None):
        st = E.slice_stats(sub, overlaps, cost_look, stop_mult=C.REF_R_MULT, rr=C.REF_RR)
        row = {"feature": feature, "slice": slice_label,
               "range_low": None if rng is None else round(rng[0], 6),
               "range_high": None if rng is None else round(rng[1], 6)}
        row.update(st)
        row["leak_alarm"] = bool(st["win_rate"] is not None and st["win_rate"] >= LEAK_ALARM)
        row["usable"] = bool(st["n_effective"] is not None and st["n_effective"] >= MIN_EFF)
        anatomy_rows.append(row)
        tests.append((f"{feature}:{slice_label}", st["win_rate"], st["n_effective"], st["p_value"]))
        return row

    # --- الخصائص المستمرة: خمس شرائح متساوية العدد من TRAIN ---
    for feat in CONT:
        vals = train[feat].to_numpy(float)
        finite = vals[~np.isnan(vals)]
        qs = np.quantile(finite, [0.2, 0.4, 0.6, 0.8])
        boundaries[feat] = [float(x) for x in qs]
        edges = [-np.inf] + list(qs) + [np.inf]
        for s in range(5):
            lo, hi = edges[s], edges[s + 1]
            sub = train[(train[feat] >= lo) & (train[feat] < hi)] if s < 4 else \
                  train[(train[feat] >= lo) & (train[feat] <= hi)]
            add_row(feat, f"Q{s+1}", sub, (lo if np.isfinite(lo) else finite.min(),
                                            hi if np.isfinite(hi) else finite.max()))

    # --- A10: حالتان ---
    for val in [False, True]:
        sub = train[train["A10"] == val]
        add_row("A10", f"sweep={'yes' if val else 'no'}", sub)

    # --- A12: ست جلسات ---
    for hr in [0, 4, 8, 12, 16, 20]:
        sub = train[train["A12"] == hr]
        add_row("A12", f"h{hr:02d}", sub)

    # --- نقاط الدخول E1..E4 ---
    entry_rows = []
    # E1 من الكاش
    dec1 = train[train["outcome"].isin(["win", "loss"])]
    st1 = E.slice_stats(train.assign(outcome=train["outcome"], rr=train["rr"]),
                        overlaps, cost_look, C.REF_R_MULT, C.REF_RR)
    entry_rows.append({"entry": "E1_close_market", "exec_ratio": 1.0, **st1})
    tests.append(("E1", st1["win_rate"], st1["n_effective"], st1["p_value"]))

    # E2..E4 نعيد الحسم بأوامر حد على TRAIN لكل أصل
    lvl_map = {"E2_gap_high": "gap_high", "E3_gap_mid": "gap_mid", "E4_gap_low": "gap_low"}
    for ename, col in lvl_map.items():
        parts = []
        for sym in C.ASSETS:
            df = E.load_bars(sym)
            sig_sym = S[S["symbol"] == sym]
            sig_sym = E.in_period(sig_sym, *C.TRAIN)
            if len(sig_sym) == 0:
                continue
            lim = E.resolve_limit(df, sig_sym, col, C.REF_R_MULT, C.REF_HORIZON)
            tmp = sig_sym.copy()
            tmp["filled"] = lim["filled"].values
            tmp["outcome"] = lim["outcome"].values
            tmp["rr"] = lim["rr"].values
            parts.append(tmp)
        allp = pd.concat(parts, ignore_index=True)
        n_total = len(allp)
        filled = allp[allp["filled"]]
        exec_ratio = len(filled) / n_total if n_total else np.nan
        st = E.slice_stats(filled, overlaps, cost_look, C.REF_R_MULT, C.REF_RR)
        entry_rows.append({"entry": ename, "exec_ratio": round(exec_ratio, 4), **st})
        tests.append((ename, st["win_rate"], st["n_effective"], st["p_value"]))

    # --- BH على m=62 ---
    m = len(tests)
    pvals = [t[3] for t in tests]
    qvals = bh_correct(pvals, m)
    mt_rows = []
    for (tid, wr, neff, p), q in zip(tests, qvals):
        mt_rows.append({"test": tid, "win_rate": wr, "n_effective": neff,
                        "p_value": p, "q_value_BH": round(q, 5) if q is not None else None,
                        "significant_q05": bool(q is not None and q < 0.05)})

    # --- ارتباط الخصائص المستمرة (ملحق 14) ---
    corr = train[CONT].corr().round(3)
    high_corr = []
    for a in range(len(CONT)):
        for b in range(a + 1, len(CONT)):
            r = corr.iloc[a, b]
            if abs(r) > 0.7:
                high_corr.append({"f1": CONT[a], "f2": CONT[b], "corr": float(r)})

    # --- كتابة المخرجات ---
    anat = pd.DataFrame(anatomy_rows)
    anat.to_csv(C.OUT / "fvg_anatomy_l0082.csv", index=False)
    pd.DataFrame(entry_rows).to_csv(C.OUT / "fvg_entry_points_l0082.csv", index=False)
    pd.DataFrame(mt_rows).to_csv(C.OUT / "multiple_testing_l0082.csv", index=False)
    (CACHE / "slice_boundaries.json").write_text(json.dumps(boundaries, ensure_ascii=False, indent=2))
    (C.OUT / "_p2_corr.json").write_text(json.dumps(
        {"matrix": corr.to_dict(), "high_corr_pairs_gt_0.7": high_corr}, ensure_ascii=False, indent=2))

    # --- بوابة G2 ---
    usable = anat[(anat["n_effective"].notna()) & (anat["n_effective"] >= MIN_EFF)]
    win54 = usable[usable["win_rate"] >= 0.54]
    win53 = usable[usable["win_rate"] > 0.53]
    if len(win54) >= 3:
        g2 = "PASS"
    elif len(win53) == 0:
        g2 = "FAIL-NO-CONDITION"
    else:
        g2 = "MARGINAL-REVIEW"
    summary = {
        "m_tests": m,
        "train_signals": int(len(train)),
        "train_decided": int(len(dec1)),
        "usable_slices": int(len(usable)),
        "slices_ge_54_eff300": int(len(win54)),
        "slices_gt_53_eff300": int(len(win53)),
        "significant_after_BH": int(sum(1 for r in mt_rows if r["significant_q05"])),
        "high_corr_pairs": high_corr,
        "G2": g2,
    }
    (C.OUT / "_p2_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\n[P2] الشرائح ذات نسبة الفوز الأعلى (عينة فعلية ≥300):")
    top = usable.sort_values("win_rate", ascending=False).head(12)
    print(top[["feature", "slice", "n_decided", "win_rate", "n_effective",
               "lower_bound", "p_value"]].to_string(index=False))
    print("\n[P2] نقاط الدخول:")
    print(pd.DataFrame(entry_rows)[["entry", "exec_ratio", "n_decided", "win_rate",
                                     "n_effective", "lower_bound"]].to_string(index=False))
    return g2


if __name__ == "__main__":
    main()
