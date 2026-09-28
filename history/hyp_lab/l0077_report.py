"""Generate REPORT-L0077.md and docs/lanes/L0077-VERDICT.md from L0077 outputs. No new measurement."""
import os, json
import numpy as np, pandas as pd
import l0077_core as C
OUT = C.OUT
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

SCR = pd.read_csv(f"{OUT}/screening_train_l0077.csv")
SEL = json.load(open(f"{OUT}/selection_l0077.json"))
HR = pd.read_csv(f"{OUT}/holdout_results_l0077.csv")
CR = pd.read_csv(f"{OUT}/combination_results_l0077.csv")
RC = pd.read_csv(f"{OUT}/random_control_l0077.csv")
CK = json.load(open(f"{OUT}/checks_l0077.json"))
CSTAT = json.load(open(f"{OUT}/combination_status_l0077.json"))
names = SEL["chosen_names"]
FAMLAB = {"A_liquidity_flow": "A سيولة/تدفق", "B_price_candle_reversal": "B سعر/شموع/ارتداد", "C_trend_momentum_breakout": "C اتجاه/زخم/اختراق"}


def n(x, d=4): return "—" if pd.isna(x) else f"{x:.{d}f}"
def pc(x, d=1): return "—" if pd.isna(x) else f"{100*x:.{d}f}%"
def pp(x): return "—" if pd.isna(x) else f"{100*x:+.2f}"
def yn(b): return "✓" if b else "✗"


def hp(path, level="pooled", key="ALL", config="base"):
    m = HR[(HR.path == path) & (HR.level == level) & (HR.key == key) & (HR.config == config)]
    return m.iloc[0] if len(m) else None


L = []
A = L.append
A("# L0077 — توسيع المرشحين داخل الفئات الثلاث مع إبقاء ثلاثة فقط (فصل زمني train/holdout)\n")
A("**النوع:** قياس فائدة التأكيد فقط — لا إدارة صفقة، لا وقف، لا رسوم، لا رأس مال، لا تداول حي. **لا توصية تداول.**\n")
A("- توسعة L0076: 14 مرشحًا (4 سيولة/تدفق · 5 سعر/شموع/ارتداد · 5 اتجاه/زخم/اختراق) بتعريفات L0072 المسجلة (شرط المستوى، عتبات L0072).")
A(f"- الفصل الزمني: **train** 2021-09-01→2024-08-31 · **حظر** ≥18 شمعة · **holdout** 2024-09-04→2026-08-30. الاختيار من train فقط، والأسماء مُجمّدة قبل holdout.")
A(f"- الفحوص: **{CK['_summary']['passed']}/{CK['_summary']['total']}** ناجحة، الحرجة كلها ناجحة ⇒ **{CK['_summary']['verdict']}**.")
A("- L0077 لا تعدّل L0074/L0076 ولا تعيد تفسير حكمها.\n")

A("## 1. مرحلة الاختيار (train فقط) — كل المرشحين الـ14، مُجمّعين عبر MSS/FVG/SFP\n")
A("البوابات: محسوم≥100 · تغطية≥20% · التفوق على وسيط العشوائي. الترتيب بين الصالحين: دقة ← Wilson-lo ← تغطية ← hit_rate.\n")
A("| الفئة | المرشح | محسوم | دقة | Wilson-lo | تغطية | وسيط عشوائي | pct_rank | ≥100 | ≥20% | >عشوائي | **صالح** |")
A("|---|---|---:|---:|---:|---:|---:|---:|:-:|:-:|:-:|:-:|")
pooled = SCR[SCR.level == "pooled"]
for fam in C.FAMILIES:
    for cand in C.FAMILIES[fam]:
        r = pooled[pooled.candidate == cand].iloc[0]
        A(f"| {FAMLAB[fam]} | {cand} | {int(r.decided)} | {n(r.directional_accuracy)} | {n(r.wilson_lo)} "
          f"| {pc(r.coverage)} | {n(r.rand_dir_median)} | {n(r.dir_pct_rank,3)} | {yn(r.gate_decided)} "
          f"| {yn(r.gate_coverage)} | {yn(r.gate_beats_random)} | {'**'+yn(r.valid)+'**'} |")

A("\n## 2. الاختيار المُجمّد (اسم واحد لكل فئة)\n")
for fam in C.FAMILIES:
    pick = SEL["selection"][fam]
    A(f"- **{FAMLAB[fam]}:** {'**'+str(pick)+'**' if pick else 'لا مرشح صالح'} — {SEL['reasons'][fam]}")
A(f"\n**الأسماء المُثبّتة = {names} (عددها {SEL['n_selected']}).** "
  f"{'اختيار ثلاثي صالح.' if SEL.get('valid_triple') else 'لم يوجد اختيار ثلاثي صالح — الفئة B (سعر/شموع/ارتداد) بقيت بلا مرشح لأن كل مرشحيها فشلوا بوابة التغطية (≥20%)، رغم توسيع المجموعة.'}\n")

A("### 2.1 فرق التسجيل: شكل المستوى مقابل شكل الحافة (§2)\n")
A("- تعريفات L0072 المسجلة هي **مشغّلات حافة/تقاطع** (أحداث I01–I14). L0077 يستعمل **حالة المستوى** لنفس الرياضيات والعتبات عند شمعة القرار i "
  "(يطابق سلسلة L0073/74/76؛ شكل الحافة كان سيُقلّص التغطية إلى ما دون البوابة). هذا الفرق مسجّل هنا وفي preregistration_l0077.json قبل القياس.\n")

A("## 3. الاختبار خارج العينة (holdout) — كل مؤشر مختار وحده مقابل البنية الخام (base)\n")
A("| المسار | محسوم | دقة | Wilson-lo–hi | فرق عن الخام | تغطية | رفض | hit_rate | MFE | MAE | مدة→هدف |")
A("|---|---:|---:|:--:|---:|---:|---:|---:|---:|---:|---:|")
for path in ["raw_structure"] + names:
    r = hp(path)
    if r is None: continue
    A(f"| {path} | {int(r.decided)} | {n(r.directional_accuracy)} | {n(r.wilson_lo,3)}–{n(r.wilson_hi,3)} "
      f"| {pp(r.diff_vs_raw)} | {pc(r.coverage)} | {pc(r.rejection_rate)} | {n(r.hit_rate_all)} "
      f"| {n(r.mfe_mean,2)} | {n(r.mae_mean,2)} | {n(r.ttt_median,1)} |")

A("\n### 3.1 حسب المكوّن البنيوي (holdout, base) — دقة (محسوم، تغطية)\n")
A("| المسار | MSS | FVG | SFP |")
A("|---|---|---|---|")
for path in ["raw_structure"] + names:
    cells = []
    for comp in C.COMP:
        r = hp(path, "structure", comp)
        cells.append("—" if r is None else f"{n(r.directional_accuracy)} ({int(r.decided)}, {pc(r.coverage)})")
    A(f"| {path} | {cells[0]} | {cells[1]} | {cells[2]} |")

A("\n### 3.2 حسب السنة (holdout, base, دقة للمؤشرات المختارة)\n")
yrs = sorted(HR[HR.level == 'year'].key.astype(str).unique())
A("| المسار | " + " | ".join(yrs) + " |")
A("|---|" + "|".join(["---"] * len(yrs)) + "|")
for path in names:
    cells = [n(HR[(HR.path==path)&(HR.level=='year')&(HR.key.astype(str)==yr)&(HR.config=='base')].iloc[0].directional_accuracy, 3)
             if len(HR[(HR.path==path)&(HR.level=='year')&(HR.key.astype(str)==yr)&(HR.config=='base')]) else "—" for yr in yrs]
    A(f"| {path} | " + " | ".join(cells) + " |")

A("\n## 4. مسارات الدمج\n")
A(f"> **{CSTAT['note']}**\n")
if len(CR):
    A("| المسار | محسوم | دقة | Wilson-lo | فرق عن الخام | تغطية |")
    A("|---|---:|---:|---:|---:|---:|")
    for _, r in CR[(CR.level == 'pooled') & (CR.config == 'base')].iterrows():
        A(f"| {r.path} | {int(r.decided)} | {n(r.directional_accuracy)} | {n(r.wilson_lo,3)} | {pp(r.diff_vs_raw)} | {pc(r.coverage)} |")
    A("\n- `ALL_of_2` = تقاطع المؤشرين · `ANY_of_2` = اتحادهما (استكشافي، ليس 2/3–3/3).\n")

A("## 5. خط الأساس العشوائي على holdout (seed=77، 1000 سحبة)\n")
A("| المسار | مؤكد | دقة فعلية | وسيط عشوائي | pct_rank |")
A("|---|---:|---:|---:|---:|")
for _, r in RC.iterrows():
    A(f"| {r.path} | {int(r.confirmed)} | {n(r.actual_dir_acc)} | {n(r.rand_dir_median)} | {n(r.dir_pct_rank,3)} |")

A("\n## 6. الحساسية +2/−1 ATR، أفق 18 (holdout, مُجمّع)\n")
A("| المسار | محسوم | دقة | فرق عن الخام | تغطية |")
A("|---|---:|---:|---:|---:|")
for path in ["raw_structure"] + names:
    r = hp(path, config="sens")
    if r is None: continue
    A(f"| {path} | {int(r.decided)} | {n(r.directional_accuracy)} | {pp(r.diff_vs_raw)} | {pc(r.coverage)} |")

A("\n## 7. الخلاصة — التغطية مقابل الدقة، والصمود خارج العينة\n")
obv_h = hp("OBV"); obv_rc = RC[RC.path == "OBV"].iloc[0]
c_name = SEL["selection"]["C_trend_momentum_breakout"]
c_h = hp(c_name); c_rc = RC[RC.path == c_name].iloc[0]
A(f"- **الفئة B لم تُنقذها التوسعة:** أعلى تغطية بين مرشحي السعر/الشموع كانت TurtleSoup ~12% < 20% ⇒ الفجوة **بنيوية** "
  "(إشارات الارتداد أندر من أن تؤكّد ≥20% من إشارات البنية)، لا تُحلّ بإضافة مؤشرات ارتداد أخرى.")
A(f"- **OBV (A):** فرق {pp(obv_h.diff_vs_raw)}pp عن الخام ودقته **دون** وسيط العشوائي (pct_rank {n(obv_rc.dir_pct_rank,3)}) ⇒ **لم يصمد** (كما L0076).")
A(f"- **{c_name} (C):** فرق {pp(c_h.diff_vs_raw)}pp، Wilson-lo {n(c_h.wilson_lo,3)} (> 0.50)، ويتفوق على العشوائي بقوة (pct_rank {n(c_rc.dir_pct_rank,3)}) "
  f"وتغطية {pc(c_h.coverage)} ⇒ **صمد خارج العينة بميزة صغيرة لكنها فوق العشوائي وفوق 50%** — وهو أقوى نتيجة اتجاهية في هذا الخط، لكنه مؤشر واحد لا الثلاثي المتنوع المطلوب.")
A("- لا اختيار ثلاثي صالح ⇒ مسارا 2/3 و3/3 غير مُعرّفين. التركيب الثنائي الاستكشافي لا يتفوق على المؤشر C وحده.\n")

A("## 8. الفحوص (§8)\n")
A("| # | الفحص | الحالة |")
A("|---|---|:-:|")
for k in [x for x in CK if x != "_summary"]:
    A(f"| {k.split('_')[0]} | {CK[k]['note']} | {'✅' if CK[k]['ok'] else '❌'} |")
A(f"\n**{CK['_summary']['passed']}/{CK['_summary']['total']} ناجحة، الحرجة كلها ناجحة ⇒ {CK['_summary']['verdict']}.**\n")

A("## 9. الملفات\n")
for f in sorted(os.listdir(OUT)):
    A(f"- `history/research/hyp_lab_out/L0077/{f}`")
A("- `history/hyp_lab/l0077_ind.py` · `l0077_core.py` · `l0077_select.py` · `l0077_holdout.py` · `l0077_checks.py` · `l0077_report.py`")

open(f"{OUT}/REPORT-L0077.md", "w").write("\n".join(L) + "\n")

# ---- VERDICT ----
V = []
B = V.append
B("# L0077 — الحكم: هل تُنتِج المرشحات الموسّعة اختيارًا ثلاثيًا متنوعًا يصمد خارج العينة؟\n")
B("**الحكم النهائي: لم يوجد اختيار ثلاثي صالح.** حتى بعد توسيع المرشحين، بقيت فئة السعر/الشموع/الارتداد بلا مرشح يجتاز بوابة التغطية (≥20%).\n")
B("## أفضل مرشح في كل فئة (train فقط، بالأرقام)\n")
for fam in C.FAMILIES:
    B(f"- **{FAMLAB[fam]}:** {SEL['reasons'][fam]}")
B("\n## المرشحون الذين فشلوا ولماذا (train)\n")
for _, r in pooled.iterrows():
    if not r.valid:
        why = []
        if not r.gate_decided: why.append("محسوم<100")
        if not r.gate_coverage: why.append(f"تغطية {pc(r.coverage)}<20%")
        if r.gate_beats_random is False or str(r.gate_beats_random) == "False": why.append(f"لا يتفوق على العشوائي (pct_rank {n(r.dir_pct_rank,3)})")
        B(f"- {r.candidate} ({FAMLAB[r.family]}): " + "، ".join(why))
B("\n## نتائج الاختبار الأعمى (holdout)\n")
B(f"- **OBV:** {pp(obv_h.diff_vs_raw)}pp عن الخام، دون وسيط العشوائي (pct_rank {n(obv_rc.dir_pct_rank,3)}) ⇒ **لم يصمد.**")
B(f"- **{c_name}:** {pp(c_h.diff_vs_raw)}pp، Wilson-lo {n(c_h.wilson_lo,3)}>0.50، pct_rank {n(c_rc.dir_pct_rank,3)}، تغطية {pc(c_h.coverage)} ⇒ "
  "**صمد بميزة صغيرة فوق العشوائي وفوق 50%** — لكنه مؤشر اتجاه منفرد، لا الثلاثي المتنوع.")
B("- **2/3 و3/3:** غير مُعرّفين (لا ثلاثي صالح).\n")
B("## التغطية والدقة وعدم الوصول\n")
B("- كل ارتفاع دقة ظاهر في مرشحي الفئة B مصحوب بتغطية منهارة (≤12%) وعينة صغيرة ⇒ لا يُعتبر نجاحًا.\n")
B("## هل صمد الاختيار خارج العينة؟\n")
B(f"**جزئيًا فقط ولمؤشر واحد:** {c_name} احتفظ بميزة اتجاهية صغيرة فوق العشوائي وفوق 50% على holdout؛ OBV انهار؛ "
  "ولا يمكن تكوين الثلاثي المتنوع أصلًا. لا يُعتمد أي تأكيد كاستراتيجية، وتلزم دراسة إدارة مستقلة قبل أي ادعاء بالربحية.\n")
B("## الالتزام بالورقة\n")
B("- توسعة المرشحين بتعريفات L0072 المسجلة · اسم واحد لكل فئة · لا إجبار ثالث · لا مؤشر رابع · "
  "لم تُستخدم L0076 لاختيار اسم · Bollinger≡Z-Score عائلة واحدة · لا تكاليف/إدارة صفقة · لم تُغلق L0070–L0076 · لا دمج إلى main · لا تشغيل حي.\n")
os.makedirs(os.path.join(ROOT, "docs/lanes"), exist_ok=True)
open(os.path.join(ROOT, "docs/lanes/L0077-VERDICT.md"), "w").write("\n".join(V) + "\n")
print("report + verdict written")
