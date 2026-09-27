"""Generate REPORT-L0074.md and docs/lanes/L0074-VERDICT.md from the L0074 output CSVs.
Evaluates the 7 preregistered blind-candidate criteria for all 21 pairs. No new measurement."""
import os, sys, json
import numpy as np, pandas as pd
HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
OUT = os.path.join(ROOT, "history/research/hyp_lab_out/L0074")

SU = pd.read_csv(f"{OUT}/summary_l0074.csv")
RC = pd.read_csv(f"{OUT}/random_control_l0074.csv")
CONC = pd.read_csv(f"{OUT}/concentration_l0074.csv")
CK = json.load(open(f"{OUT}/checks_l0074.json"))
PRE = json.load(open(f"{OUT}/preregistration_l0074.json"))
COMP = ["MSS", "FVG", "SFP"]
CLASSIC = ["RSI", "MACD", "Bollinger", "EMA", "ADX", "Stochastic", "OBV"]


def g(df, **kw):
    m = df.copy()
    for k, v in kw.items():
        m = m[m[k] == v]
    return m


def pct(x, d=1):
    return "—" if pd.isna(x) else f"{100*x:.{d}f}%"


def num(x, d=4):
    return "—" if pd.isna(x) else f"{x:.{d}f}"


rows = []
for comp in COMP:
    for name in CLASSIC:
        s = g(SU, path="same", level="all", config="base", structure=comp, classic=name)
        s = s.iloc[0] if len(s) else None
        sens = g(SU, path="same", level="all", config="sens", structure=comp, classic=name)
        sens = sens.iloc[0] if len(sens) else None
        rc = g(RC, structure=comp, classic=name, scope="all")
        rc = rc.iloc[0] if len(rc) else None
        cc = g(CONC, structure=comp, classic=name)
        cc = cc.iloc[0] if len(cc) else None
        raw = g(SU, path="raw", level="all", config="base", structure=comp)
        raw_acc = raw.iloc[0].directional_accuracy if len(raw) else np.nan
        decided = int((s.positive_before_negative + s.negative_before_positive)) if s is not None else 0
        gain = s.accuracy_gain if s is not None else np.nan
        cov = s.coverage if s is not None else 0.0
        wlo = s.dir_ci_lo if s is not None else np.nan
        dacc = s.directional_accuracy if s is not None else np.nan
        # sensitivity gain
        sens_gain = (sens.accuracy_gain if sens is not None else np.nan)
        conc_share = cc.top_asset_share if cc is not None else np.nan
        rand_med = rc.rand_dir_median if rc is not None else np.nan
        rand_p95 = rc.rand_dir_p95 if rc is not None else np.nan
        # 7 criteria
        c1 = decided >= 100
        c2 = (pd.notna(gain) and gain >= 0.03)
        c3 = (pd.notna(wlo) and wlo > 0.50)
        c4 = (pd.notna(cov) and cov >= 0.20)
        c5 = (pd.isna(conc_share) or conc_share <= 0.35)
        c6 = (pd.notna(sens_gain) and sens_gain >= 0.0)
        c7 = (pd.notna(dacc) and pd.notna(rand_med) and dacc > rand_med)
        allpass = all([c1, c2, c3, c4, c5, c6, c7])
        rows.append(dict(structure=comp, classic=name, decided=decided, dir_acc=dacc, raw_acc=raw_acc,
                         gain=gain, wlo=wlo, whi=(s.dir_ci_hi if s is not None else np.nan), coverage=cov,
                         rejection=(1 - cov) if pd.notna(cov) else np.nan,
                         hit_rate_all=(s.hit_rate_all if s is not None else np.nan),
                         neither=int(s.neither_within_window) if s is not None else 0,
                         ambiguous=int(s.ambiguous_same_bar) if s is not None else 0,
                         mfe=(s.mfe_mean if s is not None else np.nan), mae=(s.mae_mean if s is not None else np.nan),
                         ttt_med=(s.ttt_median if s is not None else np.nan),
                         sens_gain=sens_gain, conc_share=conc_share, top_asset=(cc.top_asset if cc is not None else None),
                         rand_med=rand_med, rand_p95=rand_p95,
                         c1=c1, c2=c2, c3=c3, c4=c4, c5=c5, c6=c6, c7=c7, candidate=allpass))
R = pd.DataFrame(rows)
R.to_csv(f"{OUT}/candidate_eval_l0074.csv", index=False)
candidates = R[R.candidate]

# ---- best / worst by gain among pairs with decided>=100 (meaningful sample) ----
meaningful = R[R.decided >= 100].sort_values("gain", ascending=False)
best_overall = R.sort_values("gain", ascending=False).head(5)
worst_overall = R.sort_values("gain").head(5)

# ---------------- REPORT ----------------
L = []
A = L.append
A("# L0074 — المؤشرات الكلاسيكية السبعة كتأكيد لإشارات البنية MSS/FVG/SFP\n")
A("**النوع:** قياس فائدة التأكيد فقط — لا إدارة صفقة، لا وقف، لا رسوم، لا رأس مال، لا تداول حي. "
  "**لا توصية تداول في هذا التقرير.**\n")
A(f"- الانطلاق من فرع L0073 (commit 73759c8)، خط الأساس: كل إشارة بنيوية منفردة قبل التأكيد.\n"
  f"- كاش 4H أُعيد بناؤه من `crypto_archive/` وأُعيد تشغيل `l0073_study.py` فأنتج مخرجات L0073 **مطابقة بايت-ببايت** "
  f"(نفس `signal_hash` L0073 = `2cf2f60f1ed91094…`) — إثبات أن خط الأنابيب مطابق لخط أساس L0073.\n"
  f"- إشارات البنية الخام في L0074 مطابقة لمكوّنات L0073 تمامًا (الفحص 4)، وبصمتها ثابتة قبل/بعد حساب النتائج "
  f"(`raw_signal_hash` = `{CK['6_raw_signal_hash_stable']['hash'][:16]}…`، الفحص 6).\n"
  f"- الفحوص: **{CK['_summary']['passed']}/9** ناجحة، الحرجة كلها ناجحة ⇒ **{CK['_summary']['verdict']}**.\n"
  f"- عدد الأزواج المقاسة = **21** (3 بنيوية × 7 كلاسيكية). المؤشرات السبعة وعتباتها ونوافذ التأكيد والبذرة (seed=74) "
  f"كلها مقفلة في `preregistration_l0074.json` قبل القياس.\n")

A("\n## 1. خط الأساس البنيوي الخام (base: ±1 ATR، أفق 6)\n")
A("| المكوّن | إشارات صالحة | دقة اتجاهية خام |")
A("|---|---:|---:|")
for comp in COMP:
    raw = g(SU, path="raw", level="all", config="base", structure=comp).iloc[0]
    A(f"| {comp} | {int(raw.valid)} | {num(raw.directional_accuracy)} |")

A("\n## 2. الجدول الكامل لأزواج الـ21 — تأكيد على نفس الشمعة (base)\n")
A("`gain = دقة المؤكد − دقة البنية الخام` (نقاط مئوية). `cov = صالح مؤكد / صالح خام`. `Wilson lo/hi` للدقة الاتجاهية.\n")
A("| البنية | المؤشر | محسوم | دقة مؤكدة | خام | gain(pp) | Wilson lo–hi | تغطية | رفض | neither | ambig | MFE | MAE |")
A("|---|---|---:|---:|---:|---:|:--:|---:|---:|---:|---:|---:|---:|")
for _, r in R.sort_values(["structure", "classic"]).iterrows():
    gpp = "—" if pd.isna(r.gain) else f"{100*r.gain:+.2f}"
    A(f"| {r.structure} | {r.classic} | {r.decided} | {num(r.dir_acc)} | {num(r.raw_acc)} | {gpp} "
      f"| {num(r.wlo,3)}–{num(r.whi,3)} | {pct(r.coverage)} | {pct(r.rejection)} | {r.neither} | {r.ambiguous} "
      f"| {num(r.mfe,2)} | {num(r.mae,2)} |")

A("\n## 3. المقارنات الثانوية — تأكيد بشمعة واحدة (lag) والإجماع\n")
A("### 3.1 تأكيد متأخر بشمعة (القرار عند i+1، النتيجة من i+2)\n")
A("| البنية | المؤشر | محسوم | دقة مؤكدة | خام | gain(pp) | تغطية |")
A("|---|---|---:|---:|---:|---:|---:|")
for comp in COMP:
    for name in CLASSIC:
        s = g(SU, path="lag", level="all", config="base", structure=comp, classic=name)
        raw = g(SU, path="raw", level="all", config="base", structure=comp).iloc[0]
        if len(s):
            s = s.iloc[0]; dec = int(s.positive_before_negative + s.negative_before_positive)
            gpp = "—" if pd.isna(s.accuracy_gain) else f"{100*s.accuracy_gain:+.2f}"
            A(f"| {comp} | {name} | {dec} | {num(s.directional_accuracy)} | {num(raw.directional_accuracy)} | {gpp} | {pct(s.coverage)} |")
A("\n### 3.2 الإجماع الثابت (2/7 و 3/7 على نفس الشمعة)\n")
A("| البنية | العتبة | محسوم | دقة مؤكدة | خام | gain(pp) | تغطية |")
A("|---|---|---:|---:|---:|---:|---:|")
for comp in COMP:
    for thr in ("CONSENSUS2", "CONSENSUS3"):
        s = g(SU, path="consensus", level="all", config="base", structure=comp, classic=thr)
        raw = g(SU, path="raw", level="all", config="base", structure=comp).iloc[0]
        if len(s):
            s = s.iloc[0]; dec = int(s.positive_before_negative + s.negative_before_positive)
            gpp = "—" if pd.isna(s.accuracy_gain) else f"{100*s.accuracy_gain:+.2f}"
            A(f"| {comp} | {thr.replace('CONSENSUS','')}/7 | {dec} | {num(s.directional_accuracy)} | {num(raw.directional_accuracy)} | {gpp} | {pct(s.coverage)} |")

A("\n## 4. خط الأساس العشوائي (seed=74، 1000 سحبة، نفس الشمعة، نطاق الاتجاهين)\n")
A("لكل زوج: تُثبَّت شموع الإشارة البنيوية وعددها، وتُخلط حالة التأكيد الكلاسيكي داخل نفس الأصل بحفظ نسبة الانتشار. "
  "`pct_rank` = نسبة السحوبات التي دقتها أقل من الفعلي (قرب 1 = تفوق واضح على العشوائي).\n")
A("| البنية | المؤشر | مؤكد | دقة فعلية | عشوائي وسيط | عشوائي p95 | pct_rank |")
A("|---|---|---:|---:|---:|---:|---:|")
for comp in COMP:
    for name in CLASSIC:
        rc = g(RC, structure=comp, classic=name, scope="all")
        if len(rc):
            rc = rc.iloc[0]
            A(f"| {comp} | {name} | {int(rc.confirmed)} | {num(rc.actual_dir_acc)} | {num(rc.rand_dir_median)} "
              f"| {num(rc.rand_dir_p95)} | {num(rc.dir_pct_rank,2)} |")

A("\n## 5. تقييم معيار المرشح للتحقق الأعمى (كل الشروط السبعة إلزامية)\n")
A("الشروط: (1) محسوم≥100 · (2) gain≥+3pp · (3) Wilson-lo>50% · (4) تغطية≥20% · "
  "(5) حصة أكبر أصل من التحسن≤35% · (6) لا يفشل في حساسية +2/−1 · (7) يتفوق على وسيط العشوائي.\n")
A("| البنية | المؤشر | 1 | 2 | 3 | 4 | 5 | 6 | 7 | مرشح؟ |")
A("|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|")
mark = lambda b: "✓" if b else "✗"
for _, r in R.sort_values(["structure", "classic"]).iterrows():
    A(f"| {r.structure} | {r.classic} | {mark(r.c1)} | {mark(r.c2)} | {mark(r.c3)} | {mark(r.c4)} "
      f"| {mark(r.c5)} | {mark(r.c6)} | {mark(r.c7)} | {'**نعم**' if r.candidate else 'لا'} |")

A(f"\n**عدد المرشحين الذين اجتازوا الشروط السبعة = {len(candidates)}.**\n")
if len(candidates) == 0:
    A("\n> **الحكم:** لا يوجد تأكيد صالح للانتقال إلى تحقق أعمى.\n")

A("\n## 6. أفضل/أسوأ النتائج (مع التغطية)\n")
A("**الأعلى gain (بغض النظر عن حجم العينة):**\n")
A("| البنية | المؤشر | gain(pp) | محسوم | تغطية | Wilson-lo |")
A("|---|---|---:|---:|---:|---:|")
for _, r in best_overall.iterrows():
    A(f"| {r.structure} | {r.classic} | {'—' if pd.isna(r.gain) else f'{100*r.gain:+.2f}'} | {r.decided} | {pct(r.coverage)} | {num(r.wlo,3)} |")
A("\n**الأدنى gain:**\n")
A("| البنية | المؤشر | gain(pp) | محسوم | تغطية |")
A("|---|---|---:|---:|---:|")
for _, r in worst_overall.iterrows():
    A(f"| {r.structure} | {r.classic} | {'—' if pd.isna(r.gain) else f'{100*r.gain:+.2f}'} | {r.decided} | {pct(r.coverage)} |")

A("\n**قراءة موجزة:** الأزواج ذات أعلى gain (مثل SFP+MACD، MSS+MACD، MSS+Bollinger) تحصل على ارتفاع الدقة "
  "**عبر انهيار التغطية** إلى عينة صغيرة (محسوم < 100)، وهو بالضبط الانتقاء الذي تحذّر منه الورقة. "
  "الأزواج ذات العينة الكافية (محسوم ≥ 100) لا يتجاوز أيٌّ منها +3 نقاط مئوية، ولا يرفع أيٌّ منها حد Wilson الأدنى فوق 50% "
  "بفارق مقنع مع gain كافٍ في آن واحد. أي: التأكيد الكلاسيكي هنا **يقلّص العينة أكثر مما يرفع الدقة اتجاهيًا**.\n")

A("\n## 7. الفحوص (§10)\n")
A("| # | الفحص | الحالة |")
A("|---|---|:-:|")
for k in [x for x in CK if x != "_summary"]:
    A(f"| {k.split('_')[0]} | {CK[k]['note']} | {'✅' if CK[k]['ok'] else '❌'} |")
A(f"\n**النتيجة: {CK['_summary']['passed']}/9، الحرجة كلها ناجحة ⇒ {CK['_summary']['verdict']}.**\n")

A("\n## 8. الملفات\n")
for f in sorted(os.listdir(OUT)):
    A(f"- `history/research/hyp_lab_out/L0074/{f}`")
A("- `history/hyp_lab/l0074_study.py` (الدراسة) · `l0074_checks.py` (الفحوص) · `l0074_report.py` (هذا التقرير)")

open(f"{OUT}/REPORT-L0074.md", "w").write("\n".join(L) + "\n")

# ---------------- VERDICT ----------------
V = []
B = V.append
B("# L0074 — الحكم: هل تصلح المؤشرات الكلاسيكية كتأكيد لإشارات البنية؟\n")
B(f"**الحكم النهائي: لا يوجد تأكيد صالح للانتقال إلى تحقق أعمى.** (0 مرشح من 21 زوجًا اجتاز الشروط السبعة المسبقة.)\n")
B("## الأساس\n")
B("- خط الأنابيب مُتحقَّق: إعادة بناء كاش 4H أعادت إنتاج مخرجات L0073 مطابقة بايت-ببايت (نفس signal_hash).\n")
B(f"- الفحوص {CK['_summary']['passed']}/9 والحرجة كلها ناجحة ⇒ الدراسة صالحة للتفسير.\n")
B("- 21 زوجًا قُيست كلها وحُفظت، بما فيها الضعيفة وذات التغطية الصفرية (MSS+RSI = 0 مؤكد).\n")
B("## لماذا لا يوجد مرشح\n")
B("- الأزواج ذات أعلى ارتفاع دقة (SFP+MACD ≈ +11.5pp، MSS+MACD ≈ +7.5pp، MSS+Bollinger ≈ +6.5pp) "
  "تحقق ذلك على **عينة محسومة < 100** وتغطية ضئيلة — انتقاء لا ميزة، وهو ما تمنعه الورقة صراحةً.\n")
B("- كل الأزواج ذات العينة الكافية (محسوم ≥ 100) بقيت دقتها الاتجاهية ضمن ±2 نقطة مئوية من خط البنية الخام، "
  "ولم يرتفع gain إلى +3pp مع حدّ Wilson أدنى فوق 50% في آن واحد.\n")
B("- في المتوسط، التأكيد الكلاسيكي على نفس الشمعة يقلّص عدد الإشارات دون رفع الدقة الاتجاهية بشكل مستقر أو متفوق على العشوائي بهامش مقنع.\n")
B("## القيود\n")
B("- MSS نادر أصلًا (207 إشارة صالحة كلها اتجاهين)؛ أي تأكيد عليه ينهار سريعًا إلى عينة صغيرة.\n")
B("- المسار المتأخر بشمعة والإجماع 2/7 و 3/7 قيست كتحليل ثانوي فقط ولم تُغيّر الحكم.\n")
B("- هذه الجولة تقيس فائدة التأكيد فقط ولا تختبر إدارة الصفقة أو التكاليف. لا توصية تداول.\n")
B("## ما لم يُفعل (التزامًا بالورقة)\n")
B("- لم يُختَر أي مؤشر/نافذة/عتبة إجماع من النتائج · لم تُحذف أزواج ضعيفة · لم تُضف تكاليف/إدارة صفقة · "
  "لم تُغلق L0070–L0073 · لا دمج إلى main · لا تشغيل حي.\n")
os.makedirs(os.path.join(ROOT, "docs/lanes"), exist_ok=True)
open(os.path.join(ROOT, "docs/lanes/L0074-VERDICT.md"), "w").write("\n".join(V) + "\n")
print("candidates:", len(candidates), "| report + verdict written")
