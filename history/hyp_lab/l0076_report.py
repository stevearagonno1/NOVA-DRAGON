"""Generate REPORT-L0076.md and docs/lanes/L0076-VERDICT.md from L0076 outputs. No new measurement."""
import os, json
import numpy as np, pandas as pd
import l0076_core as C
OUT = C.OUT
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

SCR = pd.read_csv(f"{OUT}/screening_train_l0076.csv")
SEL = json.load(open(f"{OUT}/selection_l0076.json"))
HR = pd.read_csv(f"{OUT}/holdout_results_l0076.csv")
CR = pd.read_csv(f"{OUT}/combination_results_l0076.csv")
RC = pd.read_csv(f"{OUT}/random_control_l0076.csv")
CK = json.load(open(f"{OUT}/checks_l0076.json"))
CSTAT = json.load(open(f"{OUT}/combination_status_l0076.json"))
names = SEL["chosen_names"]


def n(x, d=4): return "—" if pd.isna(x) else f"{x:.{d}f}"
def pc(x, d=1): return "—" if pd.isna(x) else f"{100*x:.{d}f}%"
def pp(x): return "—" if pd.isna(x) else f"{100*x:+.2f}"
def yn(b): return "✓" if b else "✗"


def hp(path, level="pooled", key="ALL", config="base"):
    m = HR[(HR.path == path) & (HR.level == level) & (HR.key == key) & (HR.config == config)]
    return m.iloc[0] if len(m) else None


L = []
A = L.append
A("# L0076 — مقارنة محايدة ثم اختيار ثلاثة مؤشرات متنوعة (فصل زمني train/holdout)\n")
A("**النوع:** قياس فائدة التأكيد فقط — لا إدارة صفقة، لا وقف، لا رسوم، لا رأس مال، لا تداول حي. **لا توصية تداول.**\n")
A(f"- خط الأساس: إشارات L0073 (MSS/FVG/SFP) + محرّك تأكيد L0074، دون تعديل. كاش 4H يُعيد إنتاج L0073 مطابقًا (hash `2cf2f60f…`).")
A(f"- الفصل الزمني: **train** {SEL['train_period'][0][:10]} → {SEL['train_period'][1][:10]} · **حظر** ≥18 شمعة (3 أيام) · "
  f"**holdout** 2024-09-04 → 2026-08-30. الاختيار من train فقط، والأسماء مُجمّدة في `selection_l0076.json` قبل قراءة holdout.")
A(f"- الفحوص: **{CK['_summary']['passed']}/{CK['_summary']['total']}** ناجحة، الحرجة كلها ناجحة ⇒ **{CK['_summary']['verdict']}**.\n")

A("## 1. مرحلة الاختيار (train فقط) — كل المرشحين السبعة، مُجمّعين عبر MSS/FVG/SFP\n")
A("البوابات: محسوم≥100 · تغطية≥20% · التفوق على وسيط العشوائي. الترتيب بين الصالحين: دقة اتجاهية ← Wilson-lo ← تغطية ← hit_rate.\n")
A("| الفئة | المرشح | محسوم | دقة | Wilson-lo | تغطية | وسيط عشوائي | pct_rank | ≥100 | ≥20% | >عشوائي | **صالح** |")
A("|---|---|---:|---:|---:|---:|---:|---:|:-:|:-:|:-:|:-:|")
fam_order = {"A_liquidity_flow": "A سيولة", "B_price_candle_vol": "B سعر/شموع", "C_trend_momentum": "C اتجاه/زخم"}
pooled = SCR[SCR.level == "pooled"]
for fam in C.FAMILIES:
    for cand in C.FAMILIES[fam]:
        r = pooled[pooled.candidate == cand].iloc[0]
        A(f"| {fam_order[fam]} | {cand} | {int(r.decided)} | {n(r.directional_accuracy)} | {n(r.wilson_lo)} "
          f"| {pc(r.coverage)} | {n(r.rand_dir_median)} | {n(r.dir_pct_rank,3)} | {yn(r.gate_decided)} "
          f"| {yn(r.gate_coverage)} | {yn(r.gate_beats_random)} | {'**'+yn(r.valid)+'**'} |")

A("\n## 2. الاختيار المُجمّد (اسم واحد لكل فئة)\n")
for fam in C.FAMILIES:
    pick = SEL["selection"][fam]
    A(f"- **{fam_order[fam]}:** {'**'+str(pick)+'**' if pick else 'لا مرشح صالح'} — {SEL['reasons'][fam]}")
A(f"\n**الأسماء المُثبّتة = {names} (عددها {SEL['n_selected']}).** "
  f"الفئة B (Bollinger) لم تجتز بوابة التغطية (≥20%) على train ⇒ لم تُقدّم مرشحًا، ولم يُجبَر اختيار مؤشر ضعيف.\n")

A("## 3. الاختبار خارج العينة (holdout) — كل مؤشر مختار وحده مقابل البنية الخام (base)\n")
A("| المسار | محسوم | دقة | Wilson-lo–hi | فرق عن الخام | تغطية | رفض | hit_rate | MFE | MAE | مدة→هدف |")
A("|---|---:|---:|:--:|---:|---:|---:|---:|---:|---:|---:|")
for path in ["raw_structure"] + names:
    r = hp(path)
    if r is None: continue
    A(f"| {path} | {int(r.decided)} | {n(r.directional_accuracy)} | {n(r.wilson_lo,3)}–{n(r.wilson_hi,3)} "
      f"| {pp(r.diff_vs_raw)} | {pc(r.coverage)} | {pc(r.rejection_rate)} | {n(r.hit_rate_all)} "
      f"| {n(r.mfe_mean,2)} | {n(r.mae_mean,2)} | {n(r.ttt_median,1)} |")

A("\n### 3.1 حسب المكوّن البنيوي (holdout, base)\n")
A("| المسار | MSS | FVG | SFP |")
A("|---|---|---|---|")
for path in ["raw_structure"] + names:
    cells = []
    for comp in C.COMP:
        r = hp(path, "structure", comp)
        cells.append("—" if r is None else f"{n(r.directional_accuracy)} ({int(r.decided)}, {pc(r.coverage)})")
    A(f"| {path} | {cells[0]} | {cells[1]} | {cells[2]} |")
A("\n*(الخلية = دقة اتجاهية (عدد محسوم، تغطية).)*\n")

A("### 3.2 حسب السنة (holdout, base, دقة اتجاهية للمؤشرات المختارة)\n")
A("| المسار | " + " | ".join(sorted(HR[(HR.level=='year')].key.astype(str).unique())) + " |")
yrs = sorted(HR[(HR.level=='year')].key.astype(str).unique())
A("|---|" + "|".join(["---"]*len(yrs)) + "|")
for path in names:
    cells = []
    for yr in yrs:
        r = HR[(HR.path==path)&(HR.level=='year')&(HR.key.astype(str)==yr)&(HR.config=='base')]
        cells.append("—" if not len(r) else f"{n(r.iloc[0].directional_accuracy,3)}")
    A(f"| {path} | " + " | ".join(cells) + " |")

A("\n## 4. مسارات الدمج\n")
A(f"> **{CSTAT['note']}**\n")
A("التركيب الثنائي الاستكشافي على holdout (base) — ليس مسار 2/3–3/3 المُسجّل:\n")
A("| المسار | محسوم | دقة | Wilson-lo | فرق عن الخام | تغطية |")
A("|---|---:|---:|---:|---:|---:|")
for _, r in CR[(CR.level=='pooled')&(CR.config=='base')].iterrows():
    A(f"| {r.path} | {int(r.decided)} | {n(r.directional_accuracy)} | {n(r.wilson_lo,3)} | {pp(r.diff_vs_raw)} | {pc(r.coverage)} |")
A("\n- `ALL_of_2` = OBV **و** EMA معًا (تقاطع) · `ANY_of_2` = OBV **أو** EMA (اتحاد).\n")

A("## 5. خط الأساس العشوائي على holdout (seed=76، 1000 سحبة)\n")
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

A("\n## 7. هل صمد الاختيار خارج العينة؟\n")
obv_h = hp("OBV"); ema_h = hp("EMA")
obv_rc = RC[RC.path=="OBV"].iloc[0]; ema_rc = RC[RC.path=="EMA"].iloc[0]
A(f"- **OBV:** على train +0.9pp فوق الخام وتصدّر العشوائي (pct_rank 0.997). على holdout الفرق **{pp(obv_h.diff_vs_raw)}pp** فقط "
  f"ودقته **دون** وسيط العشوائي (pct_rank {n(obv_rc.dir_pct_rank,3)}) ⇒ **لم يصمد؛ تلاشى تفوقه خارج العينة.**")
A(f"- **EMA:** على train +1.0pp. على holdout **{pp(ema_h.diff_vs_raw)}pp** وWilson-lo {n(ema_h.wilson_lo,3)} (< 0.50)، "
  f"يتفوق على وسيط العشوائي بهامش ضئيل (pct_rank {n(ema_rc.dir_pct_rank,3)}) ⇒ **ميزة هامشية غير مؤكدة (حد Wilson تحت 50%).**")
A("- **التركيب الثنائي** لا يضيف دقة ذات دلالة فوق EMA وحده، وبتغطية أقل.")
A("- **الفئة B لم تقدم مرشحًا** ⇒ شرط التنوّع بثلاث فئات لم يتحقق أصلًا، ومسارات 2/3–3/3 غير مُعرّفة.\n")

A("## 8. الفحوص (§9)\n")
A("| # | الفحص | الحالة |")
A("|---|---|:-:|")
for k in [x for x in CK if x != "_summary"]:
    A(f"| {k.split('_')[0]} | {CK[k]['note']} | {'✅' if CK[k]['ok'] else '❌'} |")
A(f"\n**{CK['_summary']['passed']}/{CK['_summary']['total']} ناجحة، الحرجة كلها ناجحة ⇒ {CK['_summary']['verdict']}.**\n")

A("## 9. الملفات\n")
for f in sorted(os.listdir(OUT)):
    A(f"- `history/research/hyp_lab_out/L0076/{f}`")
A("- `history/hyp_lab/l0076_core.py` · `l0076_select.py` · `l0076_holdout.py` · `l0076_checks.py` · `l0076_report.py`")

open(f"{OUT}/REPORT-L0076.md", "w").write("\n".join(L) + "\n")

# -------- VERDICT --------
V = []
B = V.append
B("# L0076 — الحكم: اختيار محايد لثلاثة مؤشرات متنوعة، واختبارها خارج العينة\n")
B("**الحكم النهائي: الاختيار لم يصمد خارج العينة، وشرط التنوّع بثلاث فئات لم يتحقق.**\n")
B("## أفضل مؤشر من كل فئة (من train فقط، بالأرقام)\n")
B(f"- **الفئة A (سيولة/تدفق): OBV** — دقة 0.5218 على 6458 محسوم، تغطية 64.2%، Wilson-lo 0.5096، تصدّر العشوائي (pct_rank 0.997).")
B(f"- **الفئة B (سعر/شموع): لا مرشح صالح** — Bollinger تغطيته 14.9% < 20% ⇒ رُفض ولم يُجبَر بديل.")
B(f"- **الفئة C (اتجاه/زخم): EMA** — دقة 0.5246 على 3849 محسوم، تغطية 38.2%، Wilson-lo 0.5088؛ "
  f"سقط RSI/MACD/Stochastic في بوابة التغطية، وسقط ADX في بوابة العشوائي (pct_rank 0.002).\n")
B("## نتائج الاختبار الخارجي (holdout)\n")
B(f"- **OBV:** فرق {pp(obv_h.diff_vs_raw)}pp عن الخام، ودقته **دون** وسيط العشوائي (pct_rank {n(obv_rc.dir_pct_rank,3)}) ⇒ **انهار التفوق.**")
B(f"- **EMA:** فرق {pp(ema_h.diff_vs_raw)}pp، Wilson-lo {n(ema_h.wilson_lo,3)} < 0.50 ⇒ **ميزة هامشية غير مؤكدة.**")
cr_all = CR[(CR.level=='pooled')&(CR.config=='base')&(CR.path.str.startswith('ALL'))]
cr_any = CR[(CR.level=='pooled')&(CR.config=='base')&(CR.path.str.startswith('ANY'))]
B(f"- **2/3 و 3/3:** غير مُعرّفين (اسمان فقط صالحان). التركيب الثنائي الاستكشافي: "
  f"both = {pp(cr_all.iloc[0].diff_vs_raw)}pp (تغطية {pc(cr_all.iloc[0].coverage)})، "
  f"any = {pp(cr_any.iloc[0].diff_vs_raw)}pp (تغطية {pc(cr_any.iloc[0].coverage)}) — بلا إضافة ذات دلالة.\n")
B("## التغطية مقابل الدقة\n")
B("- كل الأزواج التي أظهرت \"دقة أعلى\" فعلته عبر خفض التغطية؛ ولا يوجد ارتفاع دقة كبير مع تغطية محترمة يصمد خارج العينة.\n")
B("## هل صمد الاختيار خارج العينة؟\n")
B("**لا.** OBV تلاشى (دون العشوائي)، وEMA احتفظ بميزة هامشية فقط تحت عتبة Wilson؛ ولا تركيب صالح للفئات الثلاث. "
  "لا يُعتمد أي تأكيد كاستراتيجية، ويلزم دراسة إدارة مستقلة قبل أي ادعاء بالربحية.\n")
B("## الالتزام بالورقة\n")
B("- اسم واحد لكل فئة (لا ثلاثة من فئة واحدة) · الأسماء من train فقط ومُجمّدة قبل holdout · لا مؤشر رابع · "
  "لا تغيير لشرط 2/3–3/3 · لا حذف للمرشحات الفاشلة (كلها في الجدول) · لا تكاليف/إدارة صفقة · "
  "لم تُغلق L0070–L0074 · لا دمج إلى main · لا تشغيل حي.\n")
os.makedirs(os.path.join(ROOT, "docs/lanes"), exist_ok=True)
open(os.path.join(ROOT, "docs/lanes/L0076-VERDICT.md"), "w").write("\n".join(V) + "\n")
print("report + verdict written")
