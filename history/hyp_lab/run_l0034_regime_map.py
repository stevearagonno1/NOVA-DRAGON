# -*- coding: utf-8 -*-
"""L0034 — خريطة الأعمدة × مناخات السوق: أين الضعف؟

أمر القائد (2026-09-23): «قسّم الاستراتيجيات حسب حالة السوق، وجرّبها على
الحالات المعروفة والمجرَّبة مسبقًا، لنعلم أين الضعف ونطوّره.»

المصدر: صفقات L0032 الموسومة بمناخ السوق (27,051 صفقة · 5 سنوات).
لا إعادة محاكاة — نفس الصفقات، تحليل أعمق.

ما تقيسه الجولة:
  ① كل عمود × كل مناخ: دخل · جودة الصفقة · عامل الربح · نسبة الخسارة.
  ② **مؤشر الضعف**: أين يعمل العمود بأقل من نصف جودته القصوى؟
  ③ **الفرصة المهدرة**: مناخ فيه صفقات كثيرة ودخل قليل = طاقة مهدورة.
  ④ **اختبار الإسناد**: لو شغّلنا كل عمود في مناخه القوي فقط — هل نربح أكثر؟

🔒 **حماية من الانتقاء بأثر رجعي:** قرار «أي مناخ لكل عمود» يُتَّخذ على
   النصف الأول (2021-09→2023-12) **وحده**، ويُحكم عليه على النصف الثاني
   (2024-01→2026-08) الذي لم يشارك في القرار. من يختار ويحكم على نفس
   البيانات يخدع نفسه — وهو خطأ L0020 الذي اعترفنا به.

🔒 سقف المحاولات المعلَن = 1 (تحليل وصفي + اختبار إسناد واحد).

    python3 history/hyp_lab/run_l0034_regime_map.py
"""
from __future__ import annotations
import json, os, pathlib, platform, subprocess, sys, time
import numpy as np, pandas as pd

_S = pathlib.Path(os.environ.get("NOVA_SCRATCH", "~/.nova_scratch")).expanduser()
os.environ.setdefault("NOVA_HOME", str(_S / "home"))
HIST = pathlib.Path(__file__).resolve().parents[1]; ROOT = HIST.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

OUT = HIST / "research" / "hyp_lab_out" / "L0034"
SRC = HIST / "research" / "hyp_lab_out" / "L0032" / "trades_5y.csv"
SPLIT = "2024-01-01"

AR = {"F_213_breakers": "كاسرة النطاق", "F_192_ext_entry": "انحراف الدخول",
      "F_165_score_entry": "التنقيط التعويضي"}


def pf(p):
    g, l = p[p > 0].sum(), -p[p < 0].sum()
    return float(g/l) if l > 0 else (np.inf if g > 0 else 0.0)


def block(g):
    p = g["pnl"].to_numpy(float)
    if not len(p):
        return None
    w, l = p[p > 0], p[p < 0]
    return {"صفقات": len(p), "صافي$": round(float(p.sum()), 2),
            "ربح الصفقة$": round(float(p.mean()), 4),
            "عامل الربح": round(pf(p), 4),
            "فوز%": round(100*float((p > 0).mean()), 2),
            "متوسط الخاسرة$": round(float(l.mean()), 4) if len(l) else 0.0,
            "أسوأ صفقة$": round(float(p.min()), 2)}


def main():
    t0 = time.time()
    can = subprocess.run([sys.executable, str(ROOT/"tools"/"canary.py"), "--json"],
                         capture_output=True, text=True)
    cj = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
    if cj.get("canary") != "ok":
        print("الكاناري فشل — إيقاف.", file=sys.stderr); return 1
    print("الكاناري: PASS · سقف المحاولات المعلن: 1\n", flush=True)
    OUT.mkdir(parents=True, exist_ok=True); pd.set_option("display.width", 260)

    d = pd.read_csv(SRC, encoding="utf-8-sig")
    d["exit_time"] = pd.to_datetime(d["exit_time"], utc=True)
    d["entry_time"] = pd.to_datetime(d["entry_time"], utc=True)
    d["العمود"] = d["exp"].map(lambda x: AR.get(x, x))
    print(f"المصدر: {len(d)} صفقة · {d['entry_time'].min().date()} → {d['exit_time'].max().date()}\n")

    climates = ["صاعد", "عرضي", "هابط"]

    # ① الخريطة الكاملة: عمود × مناخ
    rows = []
    for col, g in d.groupby("العمود"):
        for cl in climates:
            b = block(g[g["market"] == cl])
            if b:
                rows.append({"العمود": col, "المناخ": cl, **b})
    mp = pd.DataFrame(rows)
    mp.to_csv(OUT/"map_column_climate.csv", index=False, encoding="utf-8-sig")
    print("="*140); print("① خريطة الأعمدة × مناخات السوق (خمس سنوات)"); print("="*140)
    print(mp.to_string(index=False), flush=True)

    # ② مؤشر الضعف: جودة الصفقة نسبةً لأفضل مناخ للعمود نفسه
    print("\n" + "="*140); print("② أين الضعف؟ (جودة الصفقة نسبةً لأقوى مناخ للعمود)"); print("="*140)
    weak = []
    for col, g in mp.groupby("العمود"):
        best = g["ربح الصفقة$"].max()
        for _, r in g.iterrows():
            ratio = r["ربح الصفقة$"] / best if best else 0.0
            tag = ("🔴 ضعف شديد" if ratio < 0.5 else
                   "🟡 أضعف من طاقته" if ratio < 0.8 else "✅ قوي")
            weak.append({"العمود": col, "المناخ": r["المناخ"],
                         "ربح الصفقة$": r["ربح الصفقة$"],
                         "نسبة لأقوى مناخ%": round(100*ratio, 1),
                         "صافي$": r["صافي$"], "صفقات": r["صفقات"], "الحال": tag})
    wdf = pd.DataFrame(weak).sort_values(["العمود", "نسبة لأقوى مناخ%"])
    wdf.to_csv(OUT/"weakness.csv", index=False, encoding="utf-8-sig")
    print(wdf.to_string(index=False), flush=True)

    # ③ الفرصة المهدرة: حصة الصفقات مقابل حصة الدخل داخل كل عمود
    print("\n" + "="*140); print("③ الفرصة المهدرة (حصة الجهد مقابل حصة العائد)"); print("="*140)
    opp = []
    for col, g in mp.groupby("العمود"):
        tt, tn = g["صفقات"].sum(), g["صافي$"].sum()
        for _, r in g.iterrows():
            se = 100*r["صفقات"]/tt; sn = 100*r["صافي$"]/tn if tn else 0
            opp.append({"العمود": col, "المناخ": r["المناخ"],
                        "حصة الصفقات%": round(se, 1), "حصة الدخل%": round(sn, 1),
                        "الفجوة": round(sn-se, 1),
                        "القراءة": "⚠️ جهد بلا عائد" if sn-se < -5 else
                                   ("✅ عائد فوق الجهد" if sn-se > 5 else "متوازن")})
    odf = pd.DataFrame(opp)
    odf.to_csv(OUT/"opportunity.csv", index=False, encoding="utf-8-sig")
    print(odf.to_string(index=False), flush=True)

    # ④ اختبار الإسناد — قرار على النصف الأول، حكم على الثاني
    print("\n" + "="*140)
    print("④ اختبار الإسناد: هل تشغيل كل عمود في مناخه القوي فقط أفضل؟")
    print("="*140)
    tr = d[d["exit_time"] < SPLIT]; te = d[d["exit_time"] >= SPLIT]
    print(f"القرار على: {tr['exit_time'].min().date()} → {tr['exit_time'].max().date()} ({len(tr)} صفقة)")
    print(f"الحكم على : {te['exit_time'].min().date()} → {te['exit_time'].max().date()} ({len(te)} صفقة)\n")

    plan = {}
    for col, g in tr.groupby("العمود"):
        keep = [cl for cl in climates
                if len(g[g["market"] == cl]) and g[g["market"] == cl]["pnl"].mean() > 0]
        plan[col] = keep
        det = " · ".join(f"{cl}:{g[g['market']==cl]['pnl'].mean():+.4f}$"
                         for cl in climates if len(g[g["market"] == cl]))
        print(f"  {col}: يُشغَّل في {keep or 'لا شيء'}   [{det}]")

    base = te["pnl"].sum()
    mask = te.apply(lambda r: r["market"] in plan.get(r["العمود"], []), axis=1)
    routed = te[mask]["pnl"].sum()
    print(f"\n  بلا إسناد (كل الأعمدة في كل المناخات): {base:.2f}$ · {len(te)} صفقة")
    print(f"  مع الإسناد (كل عمود في مناخه المختار) : {routed:.2f}$ · {int(mask.sum())} صفقة")
    print(f"  الفرق: {routed-base:+.2f}$ · الصفقات المحذوفة: {len(te)-int(mask.sum())}")
    if len(te) - int(mask.sum()) == 0:
        verdict = ("⚪ الإسناد بلا أثر — كل عمود مربح في كل مناخ، "
                   "فلا مناخ يستحق الحجب أصلًا")
    elif routed - base > 0:
        verdict = "✅ الإسناد يضيف مالًا"
    else:
        verdict = "❌ الإسناد يخسر مالًا — الحجب يأكل الربح كعادته"
    print(f"  الحكم: {verdict}")
    pd.DataFrame([{"بلا إسناد$": round(float(base), 2), "مع الإسناد$": round(float(routed), 2),
                   "الفرق$": round(float(routed-base), 2),
                   "صفقات محذوفة": int(len(te)-mask.sum()), "الحكم": verdict}]
                 ).to_csv(OUT/"routing_test.csv", index=False, encoding="utf-8-sig")

    # ④-ب اختبار أشدّ: الاقتصار على **أقوى مناخ واحد** لكل عمود
    print("\n=== ④-ب اختبار مشدَّد: الاقتصار على أقوى مناخ واحد لكل عمود ===")
    top = {}
    for col, g in tr.groupby("العمود"):
        means = {cl: g[g["market"] == cl]["pnl"].mean()
                 for cl in climates if len(g[g["market"] == cl])}
        top[col] = max(means, key=means.get)
        print(f"  {col}: أقوى مناخ على فترة القرار = {top[col]}")
    m2 = te.apply(lambda r: r["market"] == top.get(r["العمود"]), axis=1)
    r2 = te[m2]["pnl"].sum()
    print(f"\n  بلا تركيز: {base:.2f}$ ({len(te)} صفقة)")
    print(f"  مع التركيز على أقوى مناخ: {r2:.2f}$ ({int(m2.sum())} صفقة)")
    print(f"  الفرق: {r2-base:+.2f}$ ⇒ " +
          ("التركيز يضيف" if r2 > base else "❌ التركيز يهدم الدخل"))
    pd.DataFrame([{"بلا تركيز$": round(float(base), 2), "مع التركيز$": round(float(r2), 2),
                   "الفرق$": round(float(r2-base), 2), "أقوى مناخ": str(top)}]
                 ).to_csv(OUT/"routing_strict.csv", index=False, encoding="utf-8-sig")

    (OUT/"env_dump.txt").write_text(
        f"python={platform.python_version()}\npandas={pd.__version__}\nnumpy={np.__version__}\n"
        f"canary={cj['got']['net']}\nsource=L0032/trades_5y.csv\ntrades={len(d)}\n"
        f"split={SPLIT}\nplan={plan}\nbase={base:.4f}\nrouted={routed:.4f}\n"
        f"measurements=1 (declared cap)\n", encoding="utf-8")
    print(f"\n→ {OUT}\n{time.time()-t0:.1f} ث", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
