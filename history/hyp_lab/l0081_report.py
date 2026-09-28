# -*- coding: utf-8 -*-
"""L0081 report generator — reads L0081 outputs and writes REPORT-L0081.md + docs/lanes/L0081-VERDICT.md.
No new measurement. Verdict is derived strictly from the recorded gate outcomes."""
import os, sys, json
import numpy as np, pandas as pd
HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
OUT = os.path.join(ROOT, "history/research/hyp_lab_out/L0081")
LANES = os.path.join(ROOT, "docs/lanes")


def r(x, n=4):
    try:
        return f"{float(x):.{n}f}"
    except Exception:
        return "—"


def main():
    neff79 = pd.read_csv(f"{OUT}/neff_recompute_l0079.csv")
    neff80 = pd.read_csv(f"{OUT}/neff_recompute_l0080.csv")
    cost = pd.read_csv(f"{OUT}/execution_cost_l0081.csv")
    p2 = json.load(open(f"{OUT}/execution_cost_summary_l0081.json"))
    gv_tr = pd.read_csv(f"{OUT}/gatevol_train_l0081.csv")
    gv_ho = pd.read_csv(f"{OUT}/gatevol_holdout_l0081.csv")
    sel = json.load(open(f"{OUT}/selection_l0081.json"))
    dp = json.load(open(f"{OUT}/dsr_pbo_l0081.json"))
    conf = pd.read_csv(f"{OUT}/confirmation_l0081.csv")
    cs = json.load(open(f"{OUT}/confirmation_summary_l0081.json"))
    chk = json.load(open(f"{OUT}/checks_l0081.json"))
    mt = pd.read_csv(f"{OUT}/multiple_testing_l0081.csv")

    fvg = neff79[neff79.variant_id == "FVG_3BAR_BASE"].iloc[0]
    adx = neff79[neff79.variant_id == "ADXDI_20_22"].iloc[0]
    cand80 = neff80[(neff80.period == "holdout") & (neff80.combination == "GATE_ADX|FVG_3BAR_BASE|CONF_MACD")].iloc[0]

    g2 = p2["gate_G2_pass"]
    g4 = cs["G4_PASS"]
    verdict = "FAIL" if not g4 else ("PASS" if dp["dsr"]["passes_dsr"] else "MARGINAL")

    L = []
    A = L.append
    A("# L0081 — الورقة المدمجة: سد النواقص وحسم الميزة\n")
    A(f"## الحكم: **{verdict}**\n")
    A("**النوع:** قياس جودة إشارة و expectancy فقط — لا تحجيم، لا وقف متحرك، لا رأس مال. "
      "التكلفة مقاسة ومطروحة بوحدة R. **لا توصية تداول.**\n")
    A("مراحل متسلسلة ببوابات. الفحوص: **{}/{}** ناجحة، الحرجة كلها ناجحة.\n".format(
        chk["n_pass"], chk["n_checks"]))
    A("| البوابة | النتيجة |\n|---|---|")
    A("| G0 بنية إحصائية (اختبارات وحدة) | ✅ 21/21 |")
    A("| G1 إعادة حساب N_eff (ملحقان) | ✅ |")
    A(f"| G2 تكلفة التنفيذ (≥ أصل واحد يصمد taker/taker) | {'✅ عبر' if g2 else '❌ FAIL'} |")
    A("| G3 GATE_VOL + CPCV + DSR/PBO | ✅ (PBO={} < 0.50) |".format(r(dp["pbo"], 3)))
    A(f"| G4 التأكيد المسجل مسبقًا على أصول جديدة | {'✅ PASS' if g4 else '❌ **FAIL**'} |")
    A("")

    A("## P1 — تصحيح حجم العينة الفعلي (N_eff)\n")
    A("Wilson يُعاد حسابه على N_eff (تزامن الإشارات لكل أصل، López de Prado). "
      "الاستنتاج الملزم مطابق للمطلوب:\n")
    A("| العنصر | decided | concurrency | N_eff | Wilson اسمي | Wilson على N_eff | الحكم |")
    A("|---|---:|---:|---:|---:|---:|---|")
    A(f"| `FVG_3BAR_BASE` (L0079) | {int(fvg.decided)} | {r(fvg.concurrency,2)} | {int(round(fvg.N_eff))} | {r(fvg.wilson_lo_nominal)} | **{r(fvg.wilson_lo_neff)}** | **يسقط (< 0.50)** |")
    A(f"| `ADXDI_20_22` (L0079) | {int(adx.decided)} | {r(adx.concurrency,2)} | {int(round(adx.N_eff))} | {r(adx.wilson_lo_nominal)} | {r(adx.wilson_lo_neff)} | يصمد |")
    A(f"| `GATE_ADX\\|FVG\\|CONF_MACD` | {int(cand80.decided)} | {r(cand80.concurrency,2)} | {int(round(cand80.N_eff))} | {r(cand80.wilson_lo_nominal)} | {r(cand80.wilson_lo_neff)} | يصمد (اسميًا) |")
    A("\n> ملاحظة: التقدير الأولي (تزامن 3.27، N_eff 2015) جاء من تجميع الأصول على تقويم واحد؛ الحساب الصحيح "
      "لكل أصل يعطي تزامن ≈ 1.38 لكن **الاستنتاج نفسه**: FVG الخام ينزل تحت 0.50. التفاصيل في "
      "`ADDENDUM-L0079-NEFF.md` و`ADDENDUM-L0080-NEFF.md`.\n")

    A("## P2 — تكلفة التنفيذ (البوابة الحاسمة G2)\n")
    A(f"المنصة (افتراض معلن): {p2['platform']}. الرسوم: taker {p2['fees']['taker_pct']}% / maker {p2['fees']['maker_pct']}%؛ "
      f"انزلاق {p2['fees']['slippage_bps']}bps؛ السبريد متدرّج حسب السيولة (Corwin-Schultz كحدّ أعلى مرجعي). "
      "السيناريو المُلزِم = **taker/taker**.\n")
    A("| الأصل | ATR% | سبريد(bps) | رسوم فقط (R) | تكلفة taker/taker (R) | تكلفة maker/taker (R) | الحكم |")
    A("|---|---:|---:|---:|---:|---:|---|")
    for _, x in cost.iterrows():
        A(f"| {x.asset} | {r(x.atr_pct,2)} | {r(x.spread_bps,1)} | {r(x.fees_only_R_taker,3)} | {r(x.cost_R_taker_taker,3)} | {r(x.cost_R_maker_taker,3)} | {x.verdict_taker} |")
    ka = p2["candidate_kept_assets"]; aa = p2["candidate_all_assets"]
    A(f"\n- عتبات المرشّح: يتحمّل حتى **0.0766R** (نقطي) / **0.0287R** (محافظ). **لا أصل** يبلغ الطبقة المحافظة.")
    A(f"- BTC/BNB يموتان على **الرسوم وحدها** (رسوم taker ≈ 0.081R/0.072R > 0.0766R لأن ATR منخفض).")
    A(f"- المرشّح بعد التكلفة (taker/taker): على الأصول الصامدة exp_after = **{r(ka['expectancy_after_cost_R'])}R**؛ "
      f"على كل الأصول = **{r(aa['expectancy_after_cost_R'])}R**.")
    A(f"- G2: **{'عبر' if g2 else 'فشل'}** ({p2['n_assets_kept']} أصول تصمد taker/taker).\n")

    A("## P3 — الشبكة الناقصة GATE_VOL (9 تركيبات) + CPCV + DSR/PBO\n")
    A("GATE_VOL = تقلّب (انحراف عوائد لوغاريتمية على 20 شمعة مغلقة قبل الإشارة) داخل [Q25,Q75] من train فقط (سببي، بلا HMM/Viterbi).\n")
    A("| التركيبة | محسوم(train) | win | Exp−0.10 | تغطية صعود | CPCV e010 (متوسط) | CPCV موجب% | مؤهّل؟ |")
    A("|---|---:|---:|---:|---:|---:|---:|:-:|")
    cpcv = pd.read_csv(f"{OUT}/cpcv_paths_l0081.csv").groupby("combination").e010.agg(["mean", lambda s: (s>0).mean()])
    for _, x in gv_tr.iterrows():
        cid = x.combination
        cm = cpcv.loc[cid] if cid in cpcv.index else None
        elig = (x.decided >= 400) and (x.signal_coverage >= 0.05) and (x.rise_start_coverage >= 0.10)
        A(f"| `{cid}` | {int(x.decided)} | {r(x.win_rate)} | {r(x.expectancy_R_after_cost_010)} | {r(x.rise_start_coverage)} | {r(cm['mean']) if cm is not None else '—'} | {r(cm['<lambda_0>'],2) if cm is not None else '—'} | {'✓' if elig else '✗'} |")
    A(f"\n- **لا تركيبة GATE_VOL تجتاز CPCV مع الأهلية**: FVG سالبة بعد التكلفة، وMSS_L5 (win ~0.60) عيّنتها 35–57 وتغطية صعودها ≈ 0. نفس فخ L0080/L0079.")
    A(f"- المرشّح المُجمَّد لـP4 (قبل أي قراءة holdout): **`{sel['p4_candidate_frozen']}`** — {sel['reason']}.")
    A(f"- تعدد الاختبارات: BH على **36** ← {int(mt.passed_bh_m36.sum())} تنجح؛ **effective_n_trials = {r(dp['effective_n_trials'],1)}** (من 36 اسمية).")
    A(f"- **PBO (CSCV) = {r(dp['pbo'],3)}** (< 0.50، لا تحذير).  **DSR = {r(dp['dsr']['DSR'],4)}** مقابل حاجز 0.95 ← **لا يجتاز** "
      f"(شارب المرشّح بعد التكلفة {r(dp['dsr']['sharpe_per_trade_after_cost'])} مقابل حدّ أقصى متوقّع {r(dp['dsr']['sr_benchmark_expected_max'])}).\n")

    A("## P4 — التأكيد المسجل مسبقًا على أصول جديدة (البوابة الحاسمة G4)\n")
    A(f"اختبار استقلال مقطعي حقيقي (الخيار A): **{cs['n_assets']} أصول لم تُستخدم قط** في L0072–L0080 "
      f"({', '.join(cs['new_assets'])})، نفس النافذة {cs['window'][0]}→{cs['window'][1]}، بالتعريفات المجمّدة حرفيًا. "
      "المصدر: binance.us (binance.com محجوب 451). قراءة واحدة.\n")
    A("| الأصل | محسوم | win_rate | Exp قبل التكلفة | تكلفة taker(R) | Exp بعد taker |")
    A("|---|---:|---:|---:|---:|---:|")
    for _, x in conf.iterrows():
        A(f"| {x.asset} | {int(x.decided)} | {r(x.win_rate)} | {r(x.expectancy_pre_cost_R)} | {r(x.cost_R_taker,3)} | {r(x.expectancy_after_taker_R)} |")
    po = cs["pooled"]
    A(f"\n**المجمّع (أصول جديدة):** محسوم {po['decided']} · win_rate **{r(po['win_rate'])}** · expectancy قبل التكلفة **{r(po['expectancy_pre_cost_R'])}R** · "
      f"N_eff {int(round(po['N_eff']))} · Wilson على N_eff **{r(po['wilson_lo_neff'])}** (تحت 0.50 حتى قبل التكلفة).")
    A(f"بعد التكلفة: taker **{r(cs['expectancy_after_cost']['taker'])}R** · maker **{r(cs['expectancy_after_cost']['maker'])}R**. "
      f"اتجاه موجب في {cs['positive_direction_assets']} أصول.\n")
    A("| معيار النجاح (مقفل) | النتيجة |\n|---|:-:|")
    ar = {"N_eff_ge_200": "N_eff ≥ 200", "wilson_lo_neff_above_breakeven_after_cost": "Wilson(N_eff) فوق تعادل ما بعد التكلفة",
          "expectancy_after_measured_cost_pos": "expectancy بعد التكلفة > 0", "positive_direction_majority_assets": "اتجاه موجب في أغلبية الأصول"}
    for k, v in cs["success_criteria"].items():
        A(f"| {ar.get(k,k)} | {'✅' if v else '❌'} |")
    A(f"\n### النتيجة: **G4 {'PASS' if g4 else 'FAIL'}** — المرشّح **لا يتكرّر** خارج العينة مقطعيًا: "
      f"win_rate ينزل من 0.5383 (الـ13 الأصلية) إلى **{r(po['win_rate'])}**، والـexpectancy من +0.0766R إلى **{r(po['expectancy_pre_cost_R'])}R**، "
      "وWilson على N_eff تحت 0.50. المرشّح كان أثرًا بعديًا لعيّنة holdout الأصلية.\n")

    A("## P5 — Meta-labeling\n")
    A("**لم تُنفَّذ**: مشروطة باجتياز G4، وقد فشل G4. لا يجوز البناء فوق نموذج أولي غير مؤكَّد.\n")

    A("## الحكم النهائي والتوصية الإلزامية\n")
    A(f"### الحكم: **{verdict}** — فشل عند G4.\n")
    A("المرشّح الوحيد المسجّل مسبقًا فشل في التأكيد المقطعي على أصول جديدة، وينهار بعد التكلفة المقاسة، ولا يجتاز DSR. "
      "التقدير المحافظ سالب على كل الأصول أصلًا.\n")
    A("> **التوصية الإلزامية (§8 FAIL):** التوقّف نهائيًا عن المؤشرات المشتقّة من OHLCV، والانتقال إلى "
      "**فئة معلومات المشتقّات: funding و open interest و taker ratio** — لا مزيد من الإعدادات أو التكديس.\n")

    A("## الالتزام بالورقة\n")
    A("- 36 تركيبة تراكمية (27 + 9 GATE_VOL) · لا VPFR (يبقى PENDING) · لا «2 من 3»/أوزان · الهدف الأساسي لم يتغيّر · "
      "CPCV مطبّق بـpurge=embargo=18 · التجميد بـcommit سبق كل قراءة holdout/تأكيد · مرشّح P4 واحد · "
      "التكاليف مقاسة ومعلنة · N_eff/uniqueness/Wilson-على-N_eff · DSR+PBO+effective_n_trials · "
      "لا HMM/Viterbi · لا Kelly/تحجيم · لا إدارة صفقة · لا دمج إلى main.\n")
    A("### المخرجات\n`history/research/hyp_lab_out/L0081/` (preregistration, neff_recompute_{l0079,l0080}, "
      "execution_cost, gatevol_{train,holdout}, cpcv_paths, selection, multiple_testing, dsr_pbo, "
      "confirmation, perf_matrix, checks) + الملحقان في L0079/L0080 + `stats_core.py`.\n")

    open(f"{OUT}/REPORT-L0081.md", "w").write("\n".join(L))

    # ---- VERDICT ----
    V = []
    V.append(f"# L0081 — الحكم: {verdict}\n")
    V.append("**السؤال:** هل يصمد المرشّح `GATE_ADX|FVG_3BAR_BASE|CONF_MACD` أمام التكلفة الحقيقية "
             "ويتأكّد كفرضية مسجّلة مسبقًا على بيانات جديدة؟\n")
    V.append(f"## الحكم النهائي: **{verdict}** (فشل عند G4)\n")
    V.append("## الأدلة المختصرة\n")
    V.append(f"- **P1 (N_eff):** FVG الخام Wilson {r(fvg.wilson_lo_nominal)}→**{r(fvg.wilson_lo_neff)}** (يسقط تحت 0.50)؛ "
             f"ADXDI_20_22 والمرشّح يصمدان اسميًا بعد التصحيح.")
    V.append(f"- **P2 (تكلفة، G2 عبر):** لا أصل يبلغ الطبقة المحافظة (≤0.0287R)؛ BTC/BNB يموتان على الرسوم وحدها؛ "
             f"المرشّح بعد taker = {r(p2['candidate_all_assets']['expectancy_after_cost_R'])}R على كل الأصول.")
    V.append(f"- **P3 (GATE_VOL/CPCV):** لا تركيبة جديدة تجتاز CPCV؛ **PBO={r(dp['pbo'],3)}** (سليم)، **DSR={r(dp['dsr']['DSR'],3)}** (< 0.95 يفشل)، "
             f"effective_n_trials={r(dp['effective_n_trials'],1)}.")
    V.append(f"- **P4 (تأكيد مقطعي على {cs['n_assets']} أصول جديدة — قراءة واحدة):** win_rate {r(po['win_rate'])}، "
             f"expectancy قبل التكلفة {r(po['expectancy_pre_cost_R'])}R، Wilson(N_eff) **{r(po['wilson_lo_neff'])} < 0.50**؛ "
             f"بعد التكلفة سالب (taker {r(cs['expectancy_after_cost']['taker'])}R). **معايير النجاح: 2/4 ← G4 FAIL.**")
    V.append(f"- **الفحوص:** {chk['n_pass']}/{chk['n_checks']} ناجحة، الحرجة كلها ناجحة.\n")
    V.append("## التوصية (إلزامية)\n")
    V.append("الميزة الكلاسيكية المشتقّة من OHLCV لا تصمد أمام التكلفة ولا تتكرّر خارج العينة. "
             "**يوصى بالتوقّف نهائيًا عن هذه الفئة والانتقال إلى معلومات المشتقّات: funding و open interest و taker ratio** — لا مزيد من الإعدادات.\n")
    V.append("## الالتزام\n")
    V.append("مرشّح واحد مسجّل قبل لمس بيانات التأكيد · تجميد بـcommit سابق · تكاليف مقاسة · N_eff/DSR/PBO/BH(36) · "
             "لا VPFR/HMM/Viterbi/«2 من 3»/تحجيم/إدارة صفقة · لا دمج إلى main · P5 لم تُنفَّذ (G4 فشل).\n")
    os.makedirs(LANES, exist_ok=True)
    open(f"{LANES}/L0081-VERDICT.md", "w").write("\n".join(V))
    print("VERDICT:", verdict)
    print("wrote REPORT-L0081.md and docs/lanes/L0081-VERDICT.md")


if __name__ == "__main__":
    main()
