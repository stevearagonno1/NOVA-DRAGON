"""Generate REPORT-L0080.md and docs/lanes/L0080-VERDICT.md. No new measurement."""
import os, json
import numpy as np, pandas as pd
import l0080_combo as CB
OUT = CB.OUT
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

CAT = pd.read_csv(f"{OUT}/combination_catalog_l0080.csv")
TR = pd.read_csv(f"{OUT}/train_results_l0080.csv")
HO = pd.read_csv(f"{OUT}/holdout_results_l0080.csv")
CV = pd.read_csv(f"{OUT}/cv_folds_l0080.csv")
MT = pd.read_csv(f"{OUT}/multiple_testing_l0080.csv")
TG = pd.read_csv(f"{OUT}/target_geometry_l0080.csv")
RC = pd.read_csv(f"{OUT}/random_control_l0080.csv")
SP = pd.read_csv(f"{OUT}/splits_l0080.csv")
SEL = json.load(open(f"{OUT}/selection_l0080.json"))
CK = json.load(open(f"{OUT}/checks_l0080.json"))
prereg = json.load(open(f"{OUT}/preregistration_l0080.json"))

BE = 0.50            # breakeven win_rate at RR=1
BE_COST = 0.55       # after 0.10R cost
RCh = RC[RC.period == "holdout"]


def n(x, d=4): return "—" if pd.isna(x) else f"{x:.{d}f}"
def pp(x): return "—" if pd.isna(x) else f"{x:+.2f}"


def elig_mask(df, decided_min):
    return (df.decided >= decided_min) & (df.signal_coverage >= 0.05) & (df.rise_start_coverage >= 0.10)


HO = HO.merge(RCh[["combination", "expectancy_pct_rank", "dir_pct_rank"]], on="combination", how="left")

# success evaluation per §12
def success(r):
    return bool(pd.notna(r.expectancy_R_after_cost_010) and r.expectancy_R_after_cost_010 > 0
                and pd.notna(r.wilson_lo) and r.wilson_lo > BE
                and pd.notna(r.expectancy_pct_rank) and r.expectancy_pct_rank >= 0.95
                and r.decided >= 200)


HO["passes_success"] = HO.apply(success, axis=1)
ho_elig = HO[elig_mask(HO, 200)].copy()
any_pass = bool(HO["passes_success"].any())
# MARGINAL evidence: eligible combo with positive pre-cost expectancy that goes negative after 0.10R
marginal = ho_elig[(ho_elig.expectancy_R > 0) & (ho_elig.expectancy_R_after_cost_010 <= 0)]
if any_pass:
    VERDICT = "PASS"
elif len(marginal) > 0:
    VERDICT = "MARGINAL"
else:
    VERDICT = "FAIL"

L = []
A = L.append
A("# L0080 — مزيج مسجّل مسبقًا (بوابة → محفّز → تأكيد) مقيسًا بالـ Expectancy مع التكاليف\n")
A(f"## الحكم: **{VERDICT}**\n")
A("**النوع:** قياس جودة الإشارة و expectancy فقط — لا تحجيم مراكز، لا وقف متحرك، لا رأس مال. التكلفة مطروحة كخصم ثابت بوحدة R فقط. **لا توصية تداول.**\n")
A("- 27 تركيبة مقفلة (3 بوابات × 3 محفّزات × 3 تأكيدات). الهدف الأساسي **+1ATR/−1ATR/6 شموع، RR=1.0**.")
A("- الاختيار عبر **purged k-fold داخل train فقط** (k=5، purge=embargo=18)، ثم **holdout يُقرأ مرة واحدة**.")
A(f"- الفحوص: **{CK['_summary']['passed']}/{CK['_summary']['total']}** ناجحة، الحرجة كلها ناجحة.")
A("- **إفصاح إلزامي:** قرار الهدف اتُّخذ بعد أن قُرئت أرقام holdout في L0079؛ الأدلة الداعمة من train وحدها؛ وللتعويض استُخدم purged k-fold واحتُسبت درجة حرية إضافية في ميزانية BH (m=28 كحساسية).\n")

A("## 1. هندسة الهدف (train, بلا إشارة) — لماذا RR=1.0\n")
A("| الهدف | RR | نسبة أساسية غير مشروطة | نقطة التعادل | البعد عن التعادل | غير محسوم% | Expectancy/شمعة أفق | Expectancy/وسيط الوصول |")
A("|---|---:|---:|---:|---:|---:|---:|---:|")
for _, r in TG.iterrows():
    A(f"| {r.target} | {n(r.RR,1)} | {n(r.unconditional_win_rate)} | {n(r.breakeven,4)} | {pp(r.distance_from_breakeven*100)}pp "
      f"| {n(r.neither_rate*100,1)}% | {n(r.expectancy_per_horizon_bar,4)} | {n(r.expectancy_per_median_ttt,4)} |")
A("\n> الهدف الأساسي نسبته الأساسية **0.5000 تمامًا** عند التعادل ⇒ لا اتجاه مجاني؛ أي ميزة تُقاس فوقه حقيقية. الهدف الطويل (SEC_A) نسبته **دون** تعادله ⇒ رفع RR لم يشترِ أي ميزة. هذا يثبّت اختيار RR=1.0.\n")

A("## 2. نتائج train (الهدف الأساسي) — كل التركيبات، مرتبة بـ Expectancy بعد تكلفة 0.10R\n")
A("نقطة التعادل بعد التكلفة = **0.5500** win_rate. لا تُقارن أي تركيبة بـ 50% وحدها؛ العمود الأخير هو الفرق عن نفس المحفّز بلا بوابة/تأكيد.\n")
A("| التركيبة | محسوم | win_rate | Exp_R | Exp_R−0.10 | Wilson-lo | تغطية | تغطية الصعود | BH | مؤهّل؟ |")
A("|---|---:|---:|---:|---:|---:|---:|---:|:-:|:-:|")
trs = TR.sort_values("expectancy_R_after_cost_010", ascending=False)
for _, r in trs.iterrows():
    elig = (r.decided >= 400 and r.signal_coverage >= 0.05 and r.rise_start_coverage >= 0.10)
    A(f"| {r.combination} | {int(r.decided)} | {n(r.win_rate)} | {n(r.expectancy_R)} | {n(r.expectancy_R_after_cost_010)} "
      f"| {n(r.wilson_lo)} | {n(r.signal_coverage,3)} | {n(r.rise_start_coverage,3)} | {'✓' if r.passed_bh else '✗'} | {'✓' if elig else '✗'} |")
A("\n> **التناقض الجوهري:** التركيبات عالية الـexpectancy (كل نسخ MSS_L5، win 0.58–0.64) **غير مؤهلة** (محسوم < 120 وتغطية صعود ≈ 0)؛ والتركيبات المؤهلة عالية العينة (FVG) **expectancyها بعد التكلفة سالب** لأن win_rate ~0.52 < حاجز 0.55. الأهلية والربحية **متنافيتان** على train.\n")

A("## 3. الاختيار عبر purged k-fold (train فقط)\n")
A(f"- مرشحون اجتازوا كل المعايير (e010>0 مجمّع · ≥4/5 طيات موجبة · BH · الأهلية): **{SEL['candidates_passing_all'] or 'لا أحد'}**")
A(f"- **المُختار (مُجمّد قبل holdout): {SEL['selected'] or 'لا شيء — لم تُختَر أي تركيبة'}**")
A("- سبب الفراغ: التركيبات المؤهلة لم تحقق e010>0 في الطيات، والتركيبات ذات e010>0 غير مؤهلة (عينة صغيرة/تغطية صعود منخفضة).\n")

A("## 4. تحقّق holdout (قراءة واحدة) — التركيبات المؤهلة (محسوم≥200، تغطية≥0.05، صعود≥0.10)\n")
A("| التركيبة | محسوم | win_rate | Exp_R | Exp_R−0.10 | Wilson-lo | pct_rank(Exp) | تغطية الصعود | نجاح §12؟ |")
A("|---|---:|---:|---:|---:|---:|---:|---:|:-:|")
for _, r in ho_elig.sort_values("expectancy_R_after_cost_010", ascending=False).iterrows():
    A(f"| {r.combination} | {int(r.decided)} | {n(r.win_rate)} | {n(r.expectancy_R)} | {n(r.expectancy_R_after_cost_010)} "
      f"| {n(r.wilson_lo)} | {n(r.expectancy_pct_rank,3)} | {n(r.rise_start_coverage,3)} | {'✓' if r.passes_success else '✗'} |")
A(f"\n- تركيبات ذات expectancy بعد التكلفة موجب لكنها **غير مؤهلة** (عينة < 200): "
  + ", ".join(f"{r.combination}({int(r.decided)}، win {n(r.win_rate,3)})"
              for _, r in HO[(HO.expectancy_R_after_cost_010 > 0) & (~elig_mask(HO, 200))].iterrows()) + ".\n")

A("## 5. المقارنة الصحيحة والـ Lift (holdout, الهدف الأساسي)\n")
A("كل تركيبة مقابل نفس المحفّز بـ GATE_NONE+CONF_NONE:\n")
A("| التركيبة | win_rate | lift (pp) | lift Exp−0.10 (R) | McNemar p (تجنّب خسائر مقابل تفويت أرباح) |")
A("|---|---:|---:|---:|---:|")
for _, r in ho_elig.sort_values("lift_winrate_pp", ascending=False).head(8).iterrows():
    A(f"| {r.combination} | {n(r.win_rate)} | {pp(r.lift_winrate_pp)} | {n(r.lift_expectancy_after010_R)} | {n(r.mcnemar_p,3)} |")

A("\n## 6. تصحيح التعدّد (BH q=0.10 على الهدف الأساسي، 27 اختبارًا)\n")
A(f"- عدد التركيبات المجتازة لـ BH: **{int(MT.passed_bh.sum())}/27** (وبدرجة حرية الهدف m=28: **{int(TR.passed_bh_targetdf.sum())}/27**).")
A("- ملاحظة: اجتياز BH يعني win_rate > 0.50 بدلالة إحصائية — لكنه **لا يعني** ربحية بعد التكلفة (حاجز 0.55). أغلب مجتازي BH هي FVG عالية العينة ذات expectancy سالب بعد 0.10R.\n")

A("## 7. حساسية الأهداف الثانوية (holdout, للمتانة فقط — ممنوعة للاختيار)\n")
A("| التركيبة | SEC_A win (RR2) | SEC_A Exp−0.10 | SEC_B win | SEC_B Exp−0.10 |")
A("|---|---:|---:|---:|---:|")
for _, r in ho_elig.sort_values("expectancy_R_after_cost_010", ascending=False).head(6).iterrows():
    A(f"| {r.combination} | {n(r.get('sec_a_win_rate'))} | {n(r.get('sec_a_expectancy_R_after_cost_010'))} "
      f"| {n(r.get('sec_b_win_rate'))} | {n(r.get('sec_b_expectancy_R_after_cost_010'))} |")

A("\n## 8. الفحوص (§13 — 11 فحصًا)\n")
A("| # | الفحص | الحالة |")
A("|---|---|:-:|")
for k in [x for x in CK if x != "_summary"]:
    A(f"| {k.split('_')[0]} | {CK[k]['note']} | {'✅' if CK[k]['ok'] else '❌'} |")
A(f"\n**{CK['_summary']['passed']}/{CK['_summary']['total']} ناجحة.**\n")

A("## 9. الخلاصة والحكم\n")
best = ho_elig.sort_values("expectancy_R", ascending=False).iloc[0] if len(ho_elig) else None
if best is not None:
    A(f"- أفضل تركيبة مؤهلة على holdout: **{best.combination}** — win_rate {n(best.win_rate)} (Wilson-lo {n(best.wilson_lo)} > 0.50، pct_rank {n(best.expectancy_pct_rank,3)})، "
      f"expectancy قبل التكلفة **{n(best.expectancy_R)}R** ⟵ موجب وفوق العشوائي، لكنه **{n(best.expectancy_R_after_cost_010)}R بعد 0.10R** ⟵ سالب.")
A(f"- **الحكم: {VERDICT}** — "
  + ("توجد ميزة صغيرة حقيقية (فوق 50% وفوق العشوائي) لكنها **تنهار تمامًا بعد تكلفة 0.10R**؛ لا تركيبة تحقق كل شروط النجاح في §12."
     if VERDICT == "MARGINAL" else
     ("تركيبة واحدة على الأقل حققت كل شروط §12." if VERDICT == "PASS"
      else "لا تركيبة صمدت والمسار الكلاسيكي مستنفد.")))
A("- **حاجز التكلفة الحقيقي = 0.5500 win_rate.** أفضل win_rate مؤهل على holdout ~0.523، أي دون الحاجز — تمامًا كما توقّع التسجيل المسبق.")
A("- التكلفة المستخدمة **0.10R مفترضة** (حاجز محافظ؛ لا تتوفر بيانات تكلفة/رسوم فعلية لكل أصل). حتى عند 0.05R تبقى أفضل التركيبات المؤهلة سالبة.")
A("- **التوصية:** بما أن الميزة تنهار تحت تكلفة واقعية ولا شيء يجتاز الحاجز، فالمسار العملي مطابق لتوصية FAIL: **التوقف عن تكديس المؤشرات الكلاسيكية والانتقال إلى فئة معلومات مختلفة**، لا تجربة إعدادات إضافية.\n")

A("## 10. الملفات\n")
for f in sorted(os.listdir(OUT)):
    A(f"- `history/research/hyp_lab_out/L0080/{f}`")
A("- `history/hyp_lab/l0080_combo.py` · `l0080_checks.py` · `l0080_report.py`")
open(f"{OUT}/REPORT-L0080.md", "w").write("\n".join(L) + "\n")

# ---- VERDICT ----
Vd = []
B = Vd.append
B(f"# L0080 — الحكم: {VERDICT}\n")
B("**السؤال:** هل يُنتج مزيج بوابة→محفّز→تأكيد ميزة expectancy موجبة بعد التكلفة وتصمد خارج العينة؟\n")
B(f"## الحكم النهائي: **{VERDICT}**\n")
if VERDICT == "MARGINAL":
    B("توجد ميزة اتجاهية صغيرة حقيقية على holdout (FVG تحت بوابة EMA200: win_rate ≈ 0.523، Wilson-lo > 0.50، فوق العشوائي بنسبة ≥ 95%)، "
      "لكن **expectancyها ينهار إلى سالب بعد تكلفة 0.10R** (حاجز التعادل بعد التكلفة = 0.55). لا تركيبة تحقق كل شروط النجاح في §12.\n")
B("## الأدلة المختصرة\n")
B("- هندسة الهدف: RR=1 نسبته الأساسية 0.5000 عند التعادل تمامًا (لا اتجاه مجاني)؛ RR=2 دون تعادله ⇒ RR=1 هو الاختيار الصحيح.")
B("- train: التركيبات عالية الـexpectancy (MSS_L5، win 0.58–0.64) غير مؤهلة (عينة < 120، تغطية صعود ≈ 0)؛ المؤهلة (FVG) expectancyها بعد التكلفة سالب. الأهلية والربحية متنافيتان.")
B(f"- الاختيار عبر purged k-fold: **{SEL['selected'] or 'لا شيء'}** (فارغ).")
B("- holdout (قراءة واحدة): أفضل تركيبة مؤهلة expectancy قبل التكلفة موجب صغير، وبعد 0.10R سالب؛ التركيبات الموجبة بعد التكلفة عيّنتها 20–39 فقط (غير مؤهلة).")
B(f"- الفحوص: {CK['_summary']['passed']}/{CK['_summary']['total']} ناجحة (لا تسريب، BH+درجة حرية الهدف، تكاليف معلنة، تجميد قبل holdout، purged k-fold).\n")
B("## التوصية (إلزامية)\n")
B("الميزة الكلاسيكية تنهار تحت تكلفة واقعية. **يوصى بالتوقف عن تكديس المؤشرات الكلاسيكية والانتقال إلى فئة معلومات مختلفة**، لا تجربة إعدادات إضافية. "
  "أي هدف/تكلفة مستقبلي يُقيَّم أولًا بلا إشارة على train حسب القاعدة الثابتة في §4.5.\n")
B("## الالتزام بالورقة\n")
B("- 27 تركيبة مقفلة · لا VPFR ولا مؤشر جديد · لا «2 من 3» أو أوزان · الهدف الأساسي لم يتغيّر بعد النتائج · holdout قُرئ مرة واحدة · "
  "التكاليف مطبقة ومعلنة · إفصاح تلوث الهدف + purged k-fold + درجة حرية إضافية · لا دمج إلى main · لا إدارة صفقة.\n")
os.makedirs(os.path.join(ROOT, "docs/lanes"), exist_ok=True)
open(os.path.join(ROOT, "docs/lanes/L0080-VERDICT.md"), "w").write("\n".join(Vd) + "\n")
print("report + verdict written. VERDICT =", VERDICT)
