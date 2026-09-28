#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0082 · P3 — بناء النسخة المحسّنة · G3  (ثلاث نسخ فقط)

اختيار الخصائص (ملحق 15): أعلى أثر = فرق أعلى/أدنى شريحة في نسبة الفوز، بشرط
رتابة الاتجاه (أو طرف واضح) وعينة ≥300 في الطرفين، وبعد إسقاط المتلازمات (r>0.7).
- A6 (الأعلى أثرًا خامًا) inverted-U ذو ذروة وسطى (Q4) لا طرفًا واضحًا ⇒ يُستبعد كمرشّح عتبة
  (قاعدة 4: رابح في شريحة وسطى = ضجيج محتمل)، ويُبلَّغ كأقوى شريحة مفردة.
- A7 يُسقط لارتباطه بـA6 (r=0.77). أعلى خاصيتين بطرف واضح ورتابة: A8 (ADX منخفض) و A1 (فجوة كبيرة).

FVG_V1 = A1 كبيرة (≥ حد Q4) و A8 منخفض (≤ حد Q1)  +  أفضل نقطة دخول (E1 — الأعلى تنفيذًا ونسبةً)
FVG_V2 = V1 + عدم التكتّل من A5 (إشارة واحدة لكل تجمّع = تباعد ≥ الأفق 6 شموع لكل أصل)
FVG_V3 = V2 + أفضل بوابة اتجاه من A6/A7/A8 (GATE: close>EMA200 ⇔ A7>0)

CPCV: N=6 · K=2 · purge=18 · embargo=18 · seed=82.
G3 يمر إذا ≥1 نسخة: تداخل ≤1.15 ونسبة فوز ≥53.5% وربحية موجبة بعد التكلفة في CPCV.
"""
from __future__ import annotations

import json
import sys
import pathlib
from itertools import combinations
import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import l0082_common as C  # noqa: E402
import l0082_engine as E  # noqa: E402

CACHE = C.OUT / "_cache"
np.random.seed(C.SEED)


def decluster(sig: pd.DataFrame, spacing: int) -> pd.DataFrame:
    """إبقاء إشارة واحدة لكل تجمّع: لكل أصل، احتفظ بالإشارة إن بعُدت ≥spacing شمعة عن آخر محتفظ بها."""
    keep_idx = []
    for sym, g in sig.groupby("symbol"):
        g = g.sort_values("i")
        last = -10**9
        for idx, i in zip(g.index, g["i"].to_numpy()):
            if i - last >= spacing:
                keep_idx.append(idx); last = i
    return sig.loc[keep_idx].sort_index()


def variant_filters(S: pd.DataFrame, bounds: dict):
    a1_hi = bounds["A1"][3]   # حد Q4 السفلي (bound الرابع = 80th pct)
    a8_lo = bounds["A8"][0]   # حد Q1 العلوي (bound الأول = 20th pct)
    base = S.copy()
    v1 = base[(base["A1"] >= a1_hi) & (base["A8"] <= a8_lo)]
    v2 = decluster(v1, C.REF_HORIZON)
    v3 = v2[v2["A7"] > 0.0]
    meta = {"A1_ge": round(float(a1_hi), 6), "A8_le": round(float(a8_lo), 6), "A7_gt": 0.0}
    return v1, v2, v3, meta


def cpcv_paths(sub: pd.DataFrame, overlaps, cost_look, n=6, k=2):
    """N مجموعات زمنية متساوية على TRAIN لكل أصل، C(N,K) توليفات اختبار.
    purge=embargo=18 شمعة حول حدود مجموعات الاختبار (إسقاط إشارات النطاق الفاصل)."""
    # تعيين المجموعة الزمنية لكل إشارة داخل أصلها
    sub = sub.copy()
    sub["grp"] = -1
    bin_edges = {}
    for sym, g in sub.groupby("symbol"):
        imin, imax = g["i"].min(), g["i"].max()
        edges = np.linspace(imin, imax + 1, n + 1)
        bin_edges[sym] = edges
        gid = np.clip(np.digitize(g["i"].to_numpy(), edges) - 1, 0, n - 1)
        sub.loc[g.index, "grp"] = gid
    rows = []
    for combo in combinations(range(n), k):
        test = sub[sub["grp"].isin(combo)]
        # embargo/purge: أسقط إشارات على بعد <18 شمعة من حدود مجموعة اختبار (داخل نفس الأصل)
        keep = []
        for sym, g in test.groupby("symbol"):
            edges = bin_edges[sym]
            bad = np.zeros(len(g), bool)
            ii = g["i"].to_numpy()
            for c in combo:
                lo, hi = edges[c], edges[c + 1]
                bad |= (np.abs(ii - lo) < C.PURGE) | (np.abs(ii - hi) < C.PURGE)
            keep.append(g[~bad])
        test_clean = pd.concat(keep) if keep else test
        st = E.slice_stats(test_clean, overlaps, cost_look, C.REF_R_MULT, C.REF_RR)
        rows.append({"combo": "".join(map(str, combo)), **st})
    return pd.DataFrame(rows)


def main():
    S = pd.read_parquet(CACHE / "signals_ref.parquet").rename(
        columns={"e1_outcome": "outcome", "e1_rr": "rr"})
    overlaps = json.loads((CACHE / "overlaps_ref.json").read_text())
    bounds = json.loads((CACHE / "slice_boundaries.json").read_text())
    cost_look = E.cost_lookup_factory()
    train = E.in_period(S, *C.TRAIN)

    v1, v2, v3, meta = variant_filters(train, bounds)
    variants = {"FVG_V1": v1, "FVG_V2": v2, "FVG_V3": v3}

    rows = []
    cpcv_all = []
    for name, sub in variants.items():
        st = E.slice_stats(sub, overlaps, cost_look, C.REF_R_MULT, C.REF_RR)
        # التغطية لهذه النسخة (نسبة الشموع المغطاة) — تقدير عبر التداخل والعدد
        cp = cpcv_paths(sub, overlaps, cost_look)
        cp.insert(0, "variant", name)
        cpcv_all.append(cp)
        wr_paths = cp["win_rate"].dropna()
        prof_paths = cp["prof_after_cost_scen1"].dropna()
        rows.append({
            "variant": name,
            "n_signals": st["n_signals"], "n_decided": st["n_decided"],
            "win_rate": st["win_rate"], "overlap": st["overlap"],
            "n_effective": st["n_effective"], "lower_bound": st["lower_bound"],
            "p_value": st["p_value"],
            "prof_after_cost_scen1": st["prof_after_cost_scen1"],
            "prof_after_cost_scen3": st["prof_after_cost_scen3"],
            "cpcv_win_mean": round(float(wr_paths.mean()), 4) if len(wr_paths) else None,
            "cpcv_win_std": round(float(wr_paths.std()), 4) if len(wr_paths) else None,
            "cpcv_win_min": round(float(wr_paths.min()), 4) if len(wr_paths) else None,
            "cpcv_prof_mean": round(float(prof_paths.mean()), 5) if len(prof_paths) else None,
        })

    var_df = pd.DataFrame(rows)
    var_df.to_csv(C.OUT / "fvg_variants_l0082.csv", index=False)
    pd.concat(cpcv_all, ignore_index=True).to_csv(C.OUT / "cpcv_paths_l0082.csv", index=False)

    # بوابة G3
    passers = []
    for r in rows:
        ok = (r["overlap"] is not None and r["overlap"] <= 1.15 and
              r["cpcv_win_mean"] is not None and r["cpcv_win_mean"] >= 0.535 and
              r["cpcv_prof_mean"] is not None and r["cpcv_prof_mean"] > 0)
        if ok:
            passers.append(r["variant"])
    g3 = "PASS" if passers else "FAIL-NO-VARIANT"
    # اختيار الفائز: أعلى ربحية CPCV بين من مرّ (أو أعلى ربحية عمومًا إن لم يمر أحد)
    winner = None
    if passers:
        winner = max(passers, key=lambda v: [r for r in rows if r["variant"] == v][0]["cpcv_prof_mean"])
    summary = {"filters": meta, "G3": g3, "passers": passers, "winner": winner,
               "variants": rows}
    (C.OUT / "_p3_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return g3


if __name__ == "__main__":
    main()
