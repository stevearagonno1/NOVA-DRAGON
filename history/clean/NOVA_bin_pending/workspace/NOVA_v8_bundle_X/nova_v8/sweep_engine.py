#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
محرك البحث الشامل — Parameter Sweep Engine (NOVA_V8)
====================================================
يفحص كل تركيبات الإعدادات لاستراتيجية على نافذة تدريب، يفرز النتائج،
ثم يعيد اختبار أفضل N على نافذة اختبار منفصلة (لم تُرَ أثناء البحث).
مضاد فرط الملاءمة: الاعتماد فقط من نافذة الاختبار + فحص الهضبة (جيران الإعداد).

الاستخدام على جهاز المستخدم:
  python nova_v8/sweep_engine.py --strategy donchian --symbol BTCUSDT \
      --train 2023-09:2024-12 --test 2025-01:2026-08
النتائج: ~/sweep_results/<strategy>/sweep_train.csv + sweep_test.csv + best_on_test.txt
"""
import argparse, functools, itertools, os, sys, time
print = functools.partial(print, flush=True)  # إخراج حي حتى مع الأنابيب | tee

import numpy as np
import pandas as pd

# يجعل الاستيراد يعمل سواء شُغّل من ~/nova أو من داخل nova_v8 أو بأي مسار آخر
_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.dirname(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ------------------------------------------------------------------ شبكات البحث لكل استراتيجية
SWEEPS = {
    "donchian": {
        "env": {
            "NOVA_DON_ENTRY1": ["48", "96", "192", "288", "576"],      # قناة دخول (5m bars)
            "NOVA_DON_EXIT1":  ["24", "48", "96", "192"],              # قناة خروج
            "NOVA_DON_FILTER": ["1", "0"],                              # حاجز الدب/الصدمة (المحور الحقيقي)
        },
    },
    "adaptive_trend": {
        "env": {
            "NOVA_AT_TRAIL": ["3.0", "4.0", "5.0", "6.0", "8.0"],      # مسافة التريلينغ ×ATR-4h
            "NOVA_AT_STOP":  ["0.5", "0.8", "1.2", "1.6"],             # هامش الوقف ×ATR-5m
            "NOVA_AT_PB":    ["288", "576", "864", "1440"],            # نافذة الارتداد (5m bars)
            "NOVA_AT_TRIG":  ["6", "12", "24"],                        # نافذة التفعيل
            "NOVA_AT_V3A":   ["0", "1"],                               # فرضية (أ) دخول بلاصق القمة
            "NOVA_AT_V3B":   ["0", "1"],                               # فرضية (ب) تخطي الشمعة المجنونة
            "NOVA_AT_V3C":   ["0", "1"],                               # فرضية (ج) هيكل أعمق
        },
    },
    "dynamic_grid": {
        "env": {
            "NOVA_DGT_UNITS":  ["2", "4", "8"],
            "NOVA_DGT_LEVELS": ["12", "16", "24", "32"],
            "NOVA_DGT_CAP":    ["250", "500", "1000"],
            "NOVA_DGT_STOP":   ["0.04", "0.06", "0.10", "0.15"],
        },
    },
}


def _month_bounds(m: str):
    """'2024-11' أو '2024-11-15' → (بداية الشهر، نهايته شاملة) حتى لا يُحذف آخر شهر."""
    per = pd.Period(m, "M")
    return str(per.start_time.date()), str(per.end_time.date())


# ------------------------------------------------------------------ مشغل التركيبة
def run_combo(strategy: str, env_over: dict, start: str, end: str, symbol: str):
    """يشغّل نسخة NOVA بإعدادات env معينة ويعيد dict (صافي$, عدد الصفقات، نسبة الفوز)."""
    keys = list(SWEEPS[strategy]["env"].keys())
    for k in keys:                      # نظافة env: لا تسريب بين التركيبات
        os.environ.pop(k, None)
    os.environ.update(env_over)
    for mod in list(sys.modules):       # إعادة تحميل نظيف (الثوابت تُقرأ وقت الاستيراد)
        if mod.startswith("nova_v8"):
            del sys.modules[mod]
    from nova_v8 import config as C
    C.START_DATE, _ = _month_bounds(start)
    _, C.END_DATE = _month_bounds(end)
    from nova_v8 import feeds
    m = feeds.load_all([symbol], lazy=True)[symbol]

    if strategy == "donchian":
        from nova_v8 import donchian
        recs = donchian.replay_donchian(m)
    elif strategy == "adaptive_trend":
        from nova_v8 import adaptive_trend
        recs = adaptive_trend.replay_adaptive_trend(m)
    elif strategy == "dynamic_grid":
        from nova_v8 import dynamic_grid
        recs = dynamic_grid.replay_dynamic_grid(m)
    else:
        raise ValueError(strategy)
    net = sum(r.get("pnl_usd", 0.0) for r in recs)
    wins = sum(1 for r in recs if r.get("pnl_usd", 0) > 0)
    return {"net": net, "trades": len(recs),
            "win_pct": (100 * wins / len(recs)) if recs else 0.0}


def sweep(args):
    spec = SWEEPS[args.strategy]
    keys = list(spec["env"].keys())
    combos = list(itertools.product(*[spec["env"][k] for k in keys]))
    total = len(combos)
    print(f"البحث الشامل: {args.strategy} — {total} تركيبة × نافذتين (تدريب+اختبار)")
    tr_from, tr_to = args.train.split(":")
    te_from, te_to = args.test.split(":")
    base_out = os.path.join(args.out, args.strategy)
    os.makedirs(base_out, exist_ok=True)

    # 1) نافذة التدريب — كل التركيبات (الأولى تبني الكاش، والبقية تلتقطه فوراً)
    # RESUME: إن ماتت الجولة في المنتصف، تعيد التشغيل وتكمل من حيث توقفت
    partial = os.path.join(base_out, "sweep_train_partial.csv")
    rows, done = [], set()
    if os.path.exists(partial):
        try:
            prev = pd.read_csv(partial)
            rows = prev.to_dict("records")
            done = {tuple(str(r[k]) for k in keys) for r in rows}
            print(f"▶ استكمال: {len(done)} تركيبة منجزة سابقاً — سيُكمل الباقي فقط")
        except Exception:
            rows, done = [], set()
    t0 = time.time()
    todo = [c for c in combos if c not in done]
    for i, combo in enumerate(todo, len(done) + 1):
        env = dict(zip(keys, combo))
        try:
            r = run_combo(args.strategy, env, tr_from, tr_to, args.symbol)
            _tag = " ".join(f"{k[5:]}={v}" for k, v in env.items())
            print(f"  {i}/{total} | {_tag} → net={r['net']:.1f}$ صفقات={r['trades']} | {time.time()-t0:.0f}s")
        except Exception as ex:
            r = {"net": float("nan"), "trades": 0, "win_pct": 0.0, "err": str(ex)[:80]}
            print(f"  {i}/{total} | فشلت: {str(ex)[:60]}")
        rows.append({**env, **r})
        pd.DataFrame(rows).to_csv(partial, index=False, encoding="utf-8-sig")  # حفظ بعد كل تركيبة
    eta = (time.time() - t0) / max(len(todo), 1) * (total - len(rows))
    print(f"اكتمل التدريب ({len(rows)}/{total})")
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(base_out, "sweep_train.csv"), index=False, encoding="utf-8-sig")

    # 2) الفرز: صافي موجب + صفقات كافية
    df_ok = df[(df.trades >= args.min_trades) & np.isfinite(df.net)]
    if df_ok.empty:
        print("لا تركيبة تحقق الحد الأدنى من الصفقات — وسّع النافذة أو الشبكة")
        return
    top = df_ok.sort_values("net", ascending=False).head(args.top)
    print(f"\nأفضل {len(top)} على التدريب (قبل الهضبة):")
    print(top.to_string(index=False))

    # 3) الهضبة الحقيقية: متوسط الجيران — لكل محور، بدّله مع تثبيت البقية وخذ متوسط الصافي
    def plateau_score(row):
        neighbor_nets = []
        for k in keys:
            others = {kk: row[kk] for kk in keys if kk != k}
            sel = df_ok
            for kk, vv in others.items():
                sel = sel[sel[kk] == vv]
            neighbor_nets.extend(sel["net"].tolist())   # يشمل الصف نفسه وجيرانه على هذا المحور
        return float(np.mean(neighbor_nets)) if neighbor_nets else float(row["net"])

    top = top.copy()
    top["plateau_mean"] = top.apply(plateau_score, axis=1)
    top = top.sort_values(["plateau_mean", "net"], ascending=False)
    print("\nبعد الهضبة (الأثبت فوق الأعلى المعزول):")
    print(top.head(args.top_test).to_string(index=False))

    # 4) نافذة الاختبار — أعلى N بعد الهضبة (لم ترَها مرحلة البحث إطلاقاً)
    test_rows = []
    for i, (_, row) in enumerate(top.head(args.top_test).iterrows(), 1):
        env = {k: str(row[k]) for k in keys}
        try:
            r = run_combo(args.strategy, env, te_from, te_to, args.symbol)
        except Exception as ex:
            r = {"net": float("nan"), "trades": 0, "win_pct": 0.0, "err": str(ex)[:80]}
        test_rows.append({**env, "train_net": row["net"], "plateau": row["plateau_mean"], **r})
        print(f"  اختبار {i}/{min(args.top_test, len(top))} | {time.time()-t0:.0f}s")
    tdf = pd.DataFrame(test_rows)
    tdf.to_csv(os.path.join(base_out, "sweep_test.csv"), index=False, encoding="utf-8-sig")

    # الفائز: الأفضل على الاختبار بشرط الصفقات الدنيا (صدقاً قبل المجد)
    cand = tdf[(tdf.trades >= args.min_trades) & np.isfinite(tdf.net)]
    if cand.empty:
        cand = tdf[np.isfinite(tdf.net)]
    if cand.empty:
        print("لا نتائج صالحة على الاختبار — أرفع sweep_test.csv للفحص")
        return
    winner = cand.sort_values("net", ascending=False).head(1)
    print("\n" + "=" * 60)
    print("🏆 الفائز على نافذة الاختبار (القرار الرسمي):")
    print(winner.to_string(index=False))
    with open(os.path.join(base_out, "best_on_test.txt"), "w", encoding="utf-8") as f:
        f.write(winner.to_string(index=False) + "\n")
        f.write(f"\nنافذة التدريب: {tr_from}→{tr_to} | الاختبار: {te_from}→{te_to}\n")
        f.write(f"إجمالي التركيبات: {total} | صفقات دنيا: {args.min_trades}\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", required=True, choices=list(SWEEPS))
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--train", required=True, help="YYYY-MM:YYYY-MM")
    ap.add_argument("--test", required=True, help="YYYY-MM:YYYY-MM")
    ap.add_argument("--top", type=int, default=20, help="عدد الأفضل للتدقيق بالهضبة")
    ap.add_argument("--top-test", type=int, default=8, dest="top_test")
    ap.add_argument("--min-trades", type=int, default=15, dest="min_trades")
    ap.add_argument("--out", default=os.path.expanduser("~/sweep_results"))
    args = ap.parse_args()
    sweep(args)
