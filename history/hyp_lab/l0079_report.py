"""Generate REPORT-L0079.md and docs/lanes/L0079-VERDICT.md from L0079 outputs. No new measurement."""
import os, json
import numpy as np, pandas as pd
import l0079_variants as V
OUT = V.OUT
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

CAT = pd.read_csv(f"{OUT}/variant_catalog_l0079.csv")
TR = pd.read_csv(f"{OUT}/train_results_l0079.csv")
HO = pd.read_csv(f"{OUT}/holdout_results_l0079.csv")
RCd = pd.read_csv(f"{OUT}/random_control_l0079.csv")
RISE = pd.read_csv(f"{OUT}/rise_coverage_l0079.csv")
SEL = json.load(open(f"{OUT}/selection_l0079.json"))
CK = json.load(open(f"{OUT}/checks_l0079.json"))
chosen = {v for v in SEL["chosen_per_family"].values() if v}


def n(x, d=4): return "—" if pd.isna(x) else f"{x:.{d}f}"
def pc(x, d=1): return "—" if pd.isna(x) else f"{100*x:.{d}f}%"


def merged(period_df, period):
    b = period_df[period_df.config == "base"].merge(
        RCd[RCd.period == period][["variant_id", "rand_dir_median", "dir_pct_rank"]], on="variant_id", how="left")
    b = b.merge(RISE[RISE.period == period][["variant_id", "rise_start_coverage", "qualifying_starts", "preceded"]],
                on="variant_id", how="left")
    return b


TRb = TR[TR.config == "base"].merge(
    RCd[RCd.period == "train"][["variant_id", "rand_dir_median", "dir_pct_rank"]], on="variant_id", how="left") \
    if "train" in set(RCd.period) else TR[TR.config == "base"].assign(rand_dir_median=np.nan, dir_pct_rank=np.nan)
TRb = TRb.merge(RISE[RISE.period == "train"][["variant_id", "rise_start_coverage"]], on="variant_id", how="left")
HOb = merged(HO, "holdout")

L = []
A = L.append
A("# L0079 — مسح نسخ إعدادات المؤشرات (كل تعديل فرضية مستقلة مسمّاة)\n")
A("**النوع:** قياس جودة الإشارة فقط — لا دمج مؤشرات، لا إدارة صفقة، لا وقف، لا رسوم، لا رأس مال، لا تداول حي. **لا توصية تداول.**\n")
A(f"- **{len(CAT[CAT.track!='pending'])} نسخة مُقاسة** عبر {CAT[CAT.track!='pending'].family.nunique()} عائلة + `VPFR_PENDING` (لم يُشغّل، بلا مصدر).")
A("- مساران (كما في preregistration): **بنية** (MSS/FVG/SFP بمعاملاتها) تُقاس على إشاراتها الخام؛ **مؤشرات** تُقاس كتأكيد مستوى على البنى الأساسية المسجّلة (MSS_L5, FVG_3BAR, SFP_LOOK20).")
A(f"- الفصل الزمني: **train** 2021-09-01→2024-08-31 · **حظر** ≥18 شمعة · **holdout** 2024-09-04→2026-08-30. الاختيار من train فقط، مُجمّد قبل holdout.")
A(f"- الفحوص: **{CK['_summary']['passed']}/{CK['_summary']['total']}** ناجحة، الحرجة كلها ناجحة ⇒ **{CK['_summary']['verdict']}**.\n")

A("## 1. القائمتان المطلوبتان (train, base)\n")
A("### 1.1 أعلى دقة خام — مهما كان حجم العينة (لا تُخفى النسخ الصغيرة)\n")
A("| النسخة | العائلة | إشارات | محسوم | دقة | Wilson-lo | تغطية |")
A("|---|---|---:|---:|---:|---:|---:|")
for _, r in TRb.sort_values("directional_accuracy", ascending=False).head(8).iterrows():
    A(f"| {r.variant_id} | {r.family} | {int(r.signals)} | {int(r.decided)} | {n(r.directional_accuracy)} | {n(r.wilson_lo)} | {n(r.signal_coverage,3)} |")
A("\n> ⚠️ الصف الأعلى (`MSS_L8`) يبلغ دقة عالية على **عيّنة ضئيلة جدًا** — مثال حي على خطر «أعلى دقة خام». لذلك القائمة الثانية.\n")
A("### 1.2 أعلى دقة بين النسخ ذات العينة الكافية (محسوم ≥ 100) وتغطية موثقة\n")
A("| النسخة | العائلة | محسوم | دقة | Wilson-lo | تغطية | وسيط عشوائي | pct_rank | تغطية بدايات الصعود |")
A("|---|---|---:|---:|---:|---:|---:|---:|---:|")
suff = TRb[TRb.decided >= 100].sort_values("directional_accuracy", ascending=False)
for _, r in suff.head(12).iterrows():
    A(f"| {r.variant_id} | {r.family} | {int(r.decided)} | {n(r.directional_accuracy)} | {n(r.wilson_lo)} "
      f"| {n(r.signal_coverage,3)} | {n(r.rand_dir_median)} | {n(r.dir_pct_rank,3)} | {pc(r.rise_start_coverage)} |")

A("\n## 2. الاختيار المُجمّد (أفضل نسخة لكل عائلة من train، عينة كافية)\n")
A("> لا دمج ثلاثي في L0079 — الاختيار لكل عائلة على حدة، لتثبيته لورقة دمج لاحقة.\n")
A("| العائلة | النسخة المختارة | السبب |")
A("|---|---|---|")
for fam, vid in SEL["chosen_per_family"].items():
    A(f"| {fam} | {vid or '—'} | {SEL['reasons'][fam]} |")

A("\n## 3. الاختبار خارج العينة (holdout, base) — النسخ المُجمّدة\n")
A("| النسخة | العائلة | محسوم | دقة | Wilson-lo | تغطية | وسيط عشوائي | pct_rank | تغطية الصعود | صمد? |")
A("|---|---|---:|---:|---:|---:|---:|---:|---:|:--:|")
hc = HOb[HOb.variant_id.isin(chosen)].sort_values("directional_accuracy", ascending=False)
for _, r in hc.iterrows():
    survived = (pd.notna(r.dir_pct_rank) and r.dir_pct_rank >= 0.90 and pd.notna(r.wilson_lo) and r.wilson_lo > 0.50)
    A(f"| {r.variant_id} | {r.family} | {int(r.decided)} | {n(r.directional_accuracy)} | {n(r.wilson_lo)} "
      f"| {n(r.signal_coverage,3)} | {n(r.rand_dir_median)} | {n(r.dir_pct_rank,3)} | {pc(r.rise_start_coverage)} | {'✓' if survived else '✗'} |")
A("\n«صمد» = pct_rank ≥ 0.90 مقابل العشوائي **و** Wilson-lo > 0.50 على holdout.\n")

A("## 4. من يسبق بداية الصعود؟ (rise_start_coverage — المقياس الأهم في الورقة)\n")
A(f"بدايات صعود مؤهلة: train **{int(RISE[RISE.period=='train'].qualifying_starts.iloc[0])}** · holdout **{int(RISE[RISE.period=='holdout'].qualifying_starts.iloc[0])}** (تعريف L0073).\n")
A("أعلى 10 نسخ بتغطية بدايات الصعود على holdout (مع الدقة للتذكير أن التغطية العالية وحدها ليست ميزة):\n")
A("| النسخة | العائلة | تغطية الصعود | دقة holdout | pct_rank |")
A("|---|---|---:|---:|---:|")
top_rise = HOb.sort_values("rise_start_coverage", ascending=False).head(10)
for _, r in top_rise.iterrows():
    A(f"| {r.variant_id} | {r.family} | {pc(r.rise_start_coverage)} | {n(r.directional_accuracy)} | {n(r.dir_pct_rank,3)} |")
A("\n> تحذير أساسي: شروط المستوى الواسعة (مثل CMF>0، OBV>SMA) تغطي نسبة كبيرة من بدايات الصعود لأنها قريبة من **معدّلها الأساسي** في السوق، لا لأنها تنبؤية — ودقتها الاتجاهية عند/دون العشوائي تؤكد ذلك.\n")

A("## 5. أثر الإعداد داخل كل عائلة (train, base) — دقة | محسوم | تغطية\n")
for fam, g in TRb.groupby("family"):
    if fam == "VPFR":
        continue
    parts = " · ".join(f"**{r.variant_id}** {n(r.directional_accuracy)}|{int(r.decided)}|{n(r.signal_coverage,2)}"
                       for _, r in g.sort_values("directional_accuracy", ascending=False).iterrows())
    A(f"- **{fam}:** {parts}")

A("\n## 6. الحساسية +2/−1 ATR أفق 18 (holdout) — النسخ المُجمّدة\n")
A("| النسخة | محسوم | دقة | تغطية |")
A("|---|---:|---:|---:|")
hs = HO[(HO.config == "sens") & (HO.variant_id.isin(chosen))].sort_values("directional_accuracy", ascending=False)
for _, r in hs.iterrows():
    A(f"| {r.variant_id} | {int(r.decided)} | {n(r.directional_accuracy)} | {n(r.signal_coverage,3)} |")

A("\n## 7. الخلاصة\n")
surv = [r.variant_id for _, r in hc.iterrows() if (pd.notna(r.dir_pct_rank) and r.dir_pct_rank >= 0.90 and pd.notna(r.wilson_lo) and r.wilson_lo > 0.50)]
A(f"- **صمد خارج العينة (فوق العشوائي وفوق 50%):** {('، '.join(surv)) if surv else 'لا شيء'}.")
A("- التحسن بالإعداد حقيقي لكنه **صغير**: أفضل النسخ تتفوق على العشوائي بفارق ~1–3 نقاط مئوية فقط، وبعض «أفضل» نسخ train انهارت على holdout (SFP_LOOK10, RSI7, MSS_L5, BB).")
A("- **من يسبق الصعود:** نسخ التدفق/الاتجاه (OBV_SMA, CMF, MACD, EMA) تغطي أكثر بدايات الصعود، لكن التغطية العالية تعكس معدلها الأساسي لا قدرة تنبؤية — الدقة الاتجاهية هي الحكم.")
A("- **لا دمج ثلاثي هنا**؛ النسخ المختارة مُثبتة لورقة دمج لاحقة.\n")

A("## 8. الفحوص (§8)\n")
A("| # | الفحص | الحالة |")
A("|---|---|:-:|")
for k in [x for x in CK if x != "_summary"]:
    A(f"| {k.split('_')[0]} | {CK[k]['note']} | {'✅' if CK[k]['ok'] else '❌'} |")
A(f"\n**{CK['_summary']['passed']}/{CK['_summary']['total']} ناجحة ⇒ {CK['_summary']['verdict']}.**\n")

A("## 9. الملفات\n")
for f in sorted(os.listdir(OUT)):
    A(f"- `history/research/hyp_lab_out/L0079/{f}`")
A("- `history/hyp_lab/l0079_variants.py` · `l0079_checks.py` · `l0079_report.py`")
open(f"{OUT}/REPORT-L0079.md", "w").write("\n".join(L) + "\n")

# ---- VERDICT ----
Vd = []
B = Vd.append
B("# L0079 — الحكم: هل يحسّن ضبط الإعدادات جودة الإشارة، ويبقى خارج العينة؟\n")
B(f"**الخلاصة:** التحسن بالإعداد حقيقي لكنه صغير؛ القلة التي صمدت خارج العينة تتفوق على العشوائي بفارق ضيق فقط: **{('، '.join(surv)) if surv else 'لا شيء'}**.\n")
B("## أفضل نسخة لكل عائلة (train، عينة كافية)\n")
for fam, vid in SEL["chosen_per_family"].items():
    B(f"- **{fam}:** {vid or '—'} — {SEL['reasons'][fam]}")
B("\n## ماذا حدث على holdout؟\n")
for _, r in hc.iterrows():
    survived = (pd.notna(r.dir_pct_rank) and r.dir_pct_rank >= 0.90 and pd.notna(r.wilson_lo) and r.wilson_lo > 0.50)
    B(f"- **{r.variant_id}** ({r.family}): دقة {n(r.directional_accuracy)}، Wilson-lo {n(r.wilson_lo)}، pct_rank {n(r.dir_pct_rank,3)}، تغطية {n(r.signal_coverage,3)}، تغطية الصعود {pc(r.rise_start_coverage)} ⇒ {'صمد' if survived else 'لم يصمد'}")
B("\n## من بدأ الإشارة قبل الصعود؟\n")
B("نسخ التدفق/الاتجاه (OBV_SMA20، CMF14، MACD_8_21_5، EMA_10_30) لها أعلى تغطية بدايات صعود، لكنها قريبة من المعدل الأساسي لتلك الشروط الواسعة؛ الدقة الاتجاهية — لا التغطية وحدها — هي الفيصل، وهي عند/قرب العشوائي لبعضها (CMF14).\n")
B("## التغطية مقابل الدقة\n")
B("- عرضنا الدقة وحجم العينة والتغطية وWilson معًا. النسخ عالية الدقة على عينة ضئيلة (MSS_L8، BB_20_2.0) لا تُعتبر نجاحًا.\n")
B("## الالتزام بالورقة\n")
B("- كل نسخة لها variant_id ثابت وإعداد مسجّل · شبكة الإعدادات مقفلة قبل التشغيل · لا عتبات بعد رؤية النتائج · "
  "Bollinger/Z عائلة واحدة · VPFR بقي PENDING بلا اختراع · train منفصل عن holdout والاختيار مُجمّد قبله · "
  "لا دمج ثلاثي · لا رسوم/إدارة صفقة · لا دمج إلى main · لا تشغيل حي.\n")
os.makedirs(os.path.join(ROOT, "docs/lanes"), exist_ok=True)
open(os.path.join(ROOT, "docs/lanes/L0079-VERDICT.md"), "w").write("\n".join(Vd) + "\n")
print("report + verdict written")
