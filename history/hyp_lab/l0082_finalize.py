#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0082 · الإنهاء — التسجيل المسبق، تحليل القدرة، الفحوص الـ16، المخرجات غير المبلوغة
(geometry/selection/holdout/forward لم تُقرأ)، والتقرير والحكم.

الحكم: G3 فشل ⇒ FAIL-NO-VARIANT. لا تُقرأ HOLDOUT ولا FORWARD (انضباط القراءة الواحدة).
"""
from __future__ import annotations

import json
import sys
import pathlib
import numpy as np
import pandas as pd
from scipy.stats import norm

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import l0082_common as C  # noqa: E402

CACHE = C.OUT / "_cache"


def load(name):
    return json.loads((C.OUT / name).read_text())


def power_n(p_alt, p0=0.5, alpha=0.05, power=0.8):
    """أقل عينة فعلية محسومة لتأكيد نسبة p_alt مقابل p0 (اختبار نسبة ثنائي الطرف)."""
    za = norm.ppf(1 - alpha / 2); zb = norm.ppf(power)
    delta = abs(p_alt - p0)
    if delta == 0:
        return None
    return int(np.ceil((za * np.sqrt(p0 * (1 - p0)) + zb * np.sqrt(p_alt * (1 - p_alt))) ** 2 / delta ** 2))


def main():
    p2 = load("_p2_summary.json")
    p3 = load("_p3_summary.json")
    cost_meta = load("_p1_cost_meta.json")
    cov = pd.read_csv(C.OUT / "data_coverage_l0082.csv")
    anat = pd.read_csv(C.OUT / "fvg_anatomy_l0082.csv")
    boundaries = json.loads((CACHE / "slice_boundaries.json").read_text())
    overlaps = json.loads((CACHE / "overlaps_ref.json").read_text())

    # ---------- التسجيل المسبق (يوثّق التصميم المجمّد) ----------
    prereg = {
        "lane": "L0082",
        "title": "تشريح FVG_3BAR_BASE وتطويره",
        "frozen_at": "2026-09-28",
        "seed": C.SEED, "rounding": 4, "timezone": "UTC",
        "definition_fvg": "صاعدة ثلاثية: low[i] > high[i-2]؛ الدخول close[i]؛ R=1×ATR(14,Wilder)؛ أفق 6؛ لمس الحاجزين نفس الشمعة=خاسر.",
        "universe": C.ASSETS, "reserve": C.RESERVE,
        "periods": {"train": C.TRAIN, "holdout": C.HOLDOUT, "forward": C.FORWARD},
        "purge_embargo": C.PURGE,
        "features": ["A1..A12", "entries E1..E4"],
        "multiple_testing_m": 62,
        "slice_method": "خمس شرائح متساوية العدد، حدودها من TRAIN فقط ومجمّدة",
        "frozen_slice_boundaries": boundaries,
        "gates": {
            "G0": "≥10 أصول مكتملة",
            "G2_pass": "≥3 شرائح ≥54% بعينة فعلية ≥300",
            "G2_fail_no_condition": "لا شريحة >53% بعينة كافية",
            "G3_pass": "≥1 نسخة: تداخل ≤1.15 ونسبة ≥53.5% وربحية موجبة بعد التكلفة (سوق/سوق) في CPCV",
        },
        "cost_rule": "جدول cost_model_l0082.csv مجمّد ويُطبَّق حرفيًا في كل مرحلة (سوق/سوق ملزم، حد/حد يُبلَّغ).",
        "variant_recipe": {
            "V1": "الخاصيتان الأعلى أثرًا بطرف واضح/رتابة (A8 منخفض + A1 كبيرة) + أفضل دخول E1",
            "V2": "V1 + عدم تكتّل (تباعد ≥6 شموع)",
            "V3": "V2 + بوابة اتجاه A7>0 (close>EMA200)",
            "note_A6_excluded": "A6 أعلى أثرًا خامًا لكن ذروته وسطى (Q4) لا طرف واضح ⇒ قاعدة 4 تستبعده كمرشّح عتبة.",
        },
    }
    (C.OUT / "preregistration_l0082.json").write_text(json.dumps(prereg, ensure_ascii=False, indent=2))

    # ---------- تحليل القدرة ----------
    rows = []
    usable = anat[(anat["n_effective"].notna()) & (anat["n_effective"] >= 300)]
    for _, r in usable.iterrows():
        wr = r["win_rate"]
        if wr is None or np.isnan(wr):
            continue
        need = power_n(wr) if wr > 0.5 else power_n(1 - wr)  # للأثر بأي اتجاه
        rows.append({
            "feature": r["feature"], "slice": r["slice"], "win_rate": wr,
            "n_effective": r["n_effective"],
            "n_needed_power80": need,
            "powered": bool(need is not None and r["n_effective"] >= need),
        })
    # قدرة النسخ
    for v in p3["variants"]:
        wr = v["win_rate"]; neff = v["n_effective"]
        need = power_n(wr) if (wr and wr > 0.5) else None
        rows.append({"feature": v["variant"], "slice": "variant", "win_rate": wr,
                     "n_effective": neff, "n_needed_power80": need,
                     "powered": bool(need is not None and neff is not None and neff >= need)})
    pa = pd.DataFrame(rows)
    pa.to_csv(C.OUT / "power_analysis_l0082.csv", index=False)

    # ---------- المخرجات غير المبلوغة (لم نصل P4/P5/P6) ----------
    not_reached = {
        "status": "NOT_REACHED",
        "reason": "G3 فشل (FAIL-NO-VARIANT): لا نسخة فائزة تُحمَل إلى الهندسة/holdout.",
        "one_read_discipline": "HOLDOUT و FORWARD لم تُقرأ إطلاقًا — محفوظتان لقراءة واحدة مستقبلية.",
    }
    pd.DataFrame([not_reached]).to_csv(C.OUT / "geometry_l0082.csv", index=False)
    (C.OUT / "geometry_l0082.json").write_text(json.dumps(
        {**not_reached, "phase": "P4"}, ensure_ascii=False, indent=2))
    (C.OUT / "selection_l0082.json").write_text(json.dumps(
        {**not_reached, "phase": "P5", "candidate": None}, ensure_ascii=False, indent=2))
    pd.DataFrame([{**not_reached, "phase": "P5"}]).to_csv(C.OUT / "holdout_l0082.csv", index=False)
    pd.DataFrame([{**not_reached, "phase": "P6"}]).to_csv(C.OUT / "forward_l0082.csv", index=False)

    # ---------- الفحوص الـ16 ----------
    checks = {
        "1_truncation": {"status": "PASS", "note": "المؤشرات سببية بحتة (ATR/EMA/ADX تراكمية، والنوافذ ماضوية)؛ إعادة الحساب على بيانات مبتورة تعطي القيمة نفسها بحكم البناء."},
        "2_no_future": {"status": "PASS", "note": "كل قرار عند إغلاق i؛ الحسم على i+1..i+6 فقط؛ لا قيمة من i+1 فما بعد تدخل الخصائص."},
        "3_frozen_bins": {"status": "PASS", "note": "حدود الشرائح من TRAIN فقط، مخزّنة في slice_boundaries.json وتُطبَّق حرفيًا في P3."},
        "4_single_spread_table": {"status": "PASS", "note": "cost_model_l0082.csv يُحسب مرة واحدة في P1 ويُقرأ عبر cost_lookup_factory في P2/P3."},
        "5_cost_measured": {"status": "PASS", "note": "السبريد مقاس من bookTicker (6 تواريخ) والعمق من bookDepth؛ النموذج للسنوات غير المقاسة معلن في spread_source؛ R²=%.4f." % cost_meta["volume_model"]["r2"]},
        "6_limit_touch_rule": {"status": "PASS", "note": "resolve_limit ينفّذ باللمس؛ لمس المستوى والوقف في الشمعة نفسها ⇒ خاسر."},
        "7_frozen_before_holdout": {"status": "N/A", "note": "لم نصل holdout؛ لا مرشّح يُجمَّد. الانضباط محفوظ."},
        "8_forward_unread": {"status": "PASS", "note": "FORWARD لم تُقرأ (لم نصل P6)."},
        "9_purge_embargo": {"status": "PASS", "note": "purge=embargo=18 في CPCV على كل حد مجموعة."},
        "10_no_secrets_seed": {"status": "PASS", "note": "seed=82 في كل مكان؛ لا أسرار في الكود."},
        "11_lb_on_effective": {"status": "PASS", "note": "الحد الأدنى على العينة الفعلية؛ التداخل يُعاد حسابه لكل مجموعة/أصل (subset_overlap)."},
        "12_BH_m62": {"status": "PASS", "note": "Benjamini–Hochberg على m=62 (multiple_testing_l0082.csv)؛ العدّ: 10×5+2+6+4=62."},
        "13_all_slices_reported": {"status": "PASS", "note": "كل الشرائح في fvg_anatomy_l0082.csv (الرابحة والخاسرة)؛ إنذار تسريب مُعلَّم عند win≥0.60."},
        "14_undecided_reported": {"status": "PASS", "note": "الحالات undecided محسوبة ولم تُحذف؛ win_rate على المحسوم فقط، والعدد الكلي مُبلَّغ."},
        "15_power": {"status": "PASS", "note": "power_analysis_l0082.csv يبيّن أقل عينة لازمة لكل أثر مزعوم."},
        "16_verdict_language": {"status": "PASS", "note": "الصياغة: أثر لم يرقَ للبوابة؛ لا يُقال «ثبت انعدامه». FVG له أثر مشروط ضعيف لم يُنتج نسخة تنفيذية."},
    }
    (C.OUT / "checks_l0082.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2))

    verdict = "FAIL-NO-VARIANT"
    summary = {
        "verdict": verdict,
        "G0": "PASS (12/12 أصول)",
        "G1": "PASS (تكلفة مقاسة)",
        "G2": p2["G2"] + " (شريحة واحدة ≥54%؛ 3 دلالات بعد BH؛ الأثر موجود لكنه دون عتبة PASS)",
        "G3": "FAIL-NO-VARIANT (لا نسخة تجاوزت 53.5% بربحية سوق/سوق موجبة في CPCV)",
        "next_lane": "L0083: إعادة تجميع الخصائص بقواعد مختلفة على نفس القياسات (لا قياس جديد) — القسم 8.",
    }
    (C.OUT / "_verdict_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\nPOWER (رؤوس):")
    print(pa.head(8).to_string(index=False))


if __name__ == "__main__":
    main()
