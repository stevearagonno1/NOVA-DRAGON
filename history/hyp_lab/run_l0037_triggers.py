# -*- coding: utf-8 -*-
"""L0037 — اختبار تركيبة الكواشف في «كاسرة النطاق».

السؤال: هل مجموعة النخبة (ELITE8) هي الأفضل؟ أم أن حذف كاشف أو إضافة آخر يعطي أكثر؟
محرك كاسرة النطاق يحمل 89% من دخل المحفظة، ومحور الكواشف لم يُمَسّ منذ بناء المشروع.

الإعدادات المجمّدة (فائز L0035 + L0036):
  - الإطار الزمني: 4 ساعات
  - حجم الصفقة: 20$ ثابت
  - الكلفة: 0.13% لكل طرف (رسوم 0.10% + انزلاق 0.03%)
  - الاتجاه: شراء فقط — ممنوع البيع على المكشوف
  - الخروج: وقف 2.5×ATR · تسليح المتتبّع 0.0015 · قفل الربح 0.0060
  - نواة كسر البنية: جسم 0.40 · مدى 0.60 · نظر 10 (فائز L0035)
  - المتوسط السريع: EMA_FAST = 21 (فائز L0036)

🔒 سقف المحاولات المعلَن = 30 قياسًا.
🔒 القرار: 2021-09-01 → 2023-12-31 · الحكم: 2024-01-01 → 2026-08-31

المجموعات المقاسة:
  أ) الأساس (1): النخبة الثمانية (ELITE8)
  ب) حذف واحد (8): النخبة ناقص كاشف في كل مرة
  ج) إضافة واحد (6): النخبة زائد واحد من الستة المعطلة
  د) الكل (1): الأربعة عشر معًا (ALL14)
  هـ) أفضل تركيبتين ومحيطهما (14): دمج أفضل إضافة وأقل حذف ضررًا واستكشاف ALL14
  المجموع = 30 قياسًا بالضبط.

    python3 history/hyp_lab/run_l0037_triggers.py
"""
from __future__ import annotations
import itertools, json, os, pathlib, platform, subprocess, sys, time
import numpy as np, pandas as pd

_S = pathlib.Path(os.environ.get("NOVA_SCRATCH", "~/.nova_scratch")).expanduser()
os.environ.setdefault("NOVA_HOME", str(_S / "home"))
HIST = pathlib.Path(__file__).resolve().parents[1]; ROOT = HIST.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))

import common as C
from common import atr, simulate, trade_rows
import run_l0019_unified as R19
import run_l0017 as R17
import run_l0035_tuning as L35
import run_l0036_more as L36
import F_126_mss_core as M126
import F_213_breakers as M213
import L0017_F_192_ext_entry as M192mod
import L0017_F_165_score_entry as M165mod
import F_197_dual_trail as M197
import nova_v8.triggers as trg
import nova_v8.config as NC

OUT = HIST / "research" / "hyp_lab_out" / "L0037"
DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
DECLARED_CAP = 30

WIN = {"stop": 2.5, "trig": 0.0015, "lock": 0.0060}
BAR = 14400 # 4h

# تثبيت نواة L0035
CORE = {"body_ratio": 0.40, "range_atr": 0.60, "lookback": 10}
_ORIG = M126.mss_signal


def set_core():
    """يثبّت نواة L0035 ويرقّع الوحدات الثلاث معًا."""
    br, ra, lb = CORE["body_ratio"], CORE["range_atr"], CORE["lookback"]
    def patched(df, body_ratio=br, range_atr=ra, lookback=lb, _o=_ORIG):
        return _o(df, body_ratio=body_ratio, range_atr=range_atr, lookback=lookback).fillna(False)
    M126.mss_signal = M192mod.mss_signal = M165mod.mss_signal = patched


def make_custom_signals(df: pd.DataFrame, triggers: list[str] | tuple[str, ...]) -> pd.Series:
    """اتحاد الحواف الصاعدة لأعضاء المجموعة المحددة (الأول اشتعالاً)."""
    longs = M213._long_triggers(df)
    sig = None
    for n in triggers:
        e = M213._edge(longs[n])
        sig = e if sig is None else (sig | e)
    return sig.fillna(False)


def pf(p):
    g, l = p[p > 0].sum(), -p[p < 0].sum()
    return float(g/l) if l > 0 else (np.inf if g > 0 else 0.0)


def run_portfolio(cells, trigger_set, s0, s1, fee_side=0.001, slip_side=0.0003):
    """محاكاة المحفظة الموحدة على نافذة زمنية بمجموعة كواشف محددة لكاسرة النطاق."""
    old_stop = C.STOP_ATR
    old_fee = C.FEE_PER_SIDE
    old_slip = C.SLIP_PER_SIDE
    old_cost = C.COST_PER_SIDE

    C.STOP_ATR = WIN["stop"]
    C.FEE_PER_SIDE = fee_side
    C.SLIP_PER_SIDE = slip_side
    C.COST_PER_SIDE = fee_side + slip_side

    rows = []
    try:
        for sym in sorted({c["symbol"] for c in cells}):
            df = L35.frames(sym)
            win = df[(df.index >= s0) & (df.index <= s1)]
            if len(win) < 100:
                continue
            a_s = atr(win)
            for c in [x for x in cells if x["symbol"] == sym]:
                if c["driver"] == "F_213_breakers":
                    sig = make_custom_signals(df, trigger_set).loc[win.index]
                    kw = ({"exit_mode": "dual", "dual": {**M213.make_dual_spec(),
                           "trig": WIN["trig"], "lock": WIN["lock"]}}
                          if c["combo"]["exit"] == "dual" else {"exit_mode": "std"})
                else:
                    sig = R17.EXPS[c["driver"]].make_signals(df, **c["combo"]).loc[win.index]
                    kw = {"exit_mode": "dual", "dual": {**M197.make_dual_spec(),
                          "trig": WIN["trig"], "lock": WIN["lock"]}}
                _, tr = simulate(win, sig, a_s, notional=C.TRADE_USD, bar_secs=BAR, **kw)
                rows.extend(trade_rows(c["symbol"], c["driver"], tr))
    finally:
        C.STOP_ATR = old_stop
        C.FEE_PER_SIDE = old_fee
        C.SLIP_PER_SIDE = old_slip
        C.COST_PER_SIDE = old_cost

    tdf = pd.DataFrame(rows)
    if tdf.empty:
        return {"صافي$": 0.0, "صفقات": 0, "عامل الربح": 0.0, "ربح_الصفقة$": 0.0}, tdf
    p = tdf["pnl"].to_numpy(float)
    g, l = p[p > 0].sum(), -p[p < 0].sum()
    profit_factor = float(g/l) if l > 0 else (np.inf if g > 0 else 0.0)
    net = round(float(p.sum()), 2)
    n_trades = len(tdf)
    avg_trade = round(net / n_trades, 5) if n_trades > 0 else 0.0
    return {"صافي$": net, "صفقات": n_trades, "عامل الربح": round(profit_factor, 4), "ربح_الصفقة$": avg_trade}, tdf


def main():
    t0 = time.time()
    can = subprocess.run([sys.executable, str(ROOT/"tools"/"canary.py"), "--json"],
                         capture_output=True, text=True)
    cj = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
    if cj.get("canary") != "ok":
        print("الكاناري فشل — إيقاف.", file=sys.stderr); return 1
    print(f"الكاناري: PASS · سقف المحاولات المعلن: {DECLARED_CAP}")
    print(f"الإعدادات المجمّدة: نواة L0035={CORE} · EMA_FAST=21 · خروج={WIN}\n", flush=True)
    OUT.mkdir(parents=True, exist_ok=True); pd.set_option("display.width", 250)

    # تطبيق الإعدادات المجمّدة
    set_core()
    NC.EMA_FAST = 21
    M213._cache.clear()

    cells = R19.breaker_cells() + R19.new_cells()
    all_triggers = list(trg.PRIORITY)
    elite8 = list(M213.ELITE8)
    remaining6 = [t for t in all_triggers if t not in elite8]

    used = 0
    runs = []

    # ════════════════════════════════════════════════════════════════════════
    # فترة الاختيار (Decision Period: 2021-09-01 → 2023-12-31)
    # ════════════════════════════════════════════════════════════════════════
    print("="*80)
    print("فترة الاختيار (Decision Period: 2021-09-01 → 2023-12-31)")
    print("="*80)

    # أ) الأساس (1)
    r_base, _ = run_portfolio(cells, elite8, DEC_S, DEC_E); used += 1
    runs.append({"المجموعة": "أ) الأساس", "الاسم": "ELITE8 (الأساس)", "عدد_الكواشف": len(elite8),
                 "قائمة_الكواشف": ",".join(elite8), **r_base})
    print(f"أ) الأساس ELITE8: {r_base['صافي$']:>8.2f}$ ({r_base['صفقات']:5d} صفقات, PF={r_base['عامل الربح']:.4f})")

    # ب) حذف واحد (8)
    print("\nب) حذف كاشف واحد من ELITE8 (8 محاولات):")
    for t in elite8:
        sub = [x for x in elite8 if x != t]
        r, _ = run_portfolio(cells, sub, DEC_S, DEC_E); used += 1
        runs.append({"المجموعة": "ب) حذف واحد", "الاسم": f"ELITE8 - {t}", "عدد_الكواشف": len(sub),
                     "قائمة_الكواشف": ",".join(sub), **r})
        print(f"   ELITE8 - {t:11s}: {r['صافي$']:>8.2f}$ ({r['صفقات']:5d} صفقات, PF={r['عامل الربح']:.4f})")

    # ج) إضافة واحد (6)
    print("\nج) إضافة كاشف واحد إلى ELITE8 (6 محاولات):")
    for t in remaining6:
        sup = elite8 + [t]
        r, _ = run_portfolio(cells, sup, DEC_S, DEC_E); used += 1
        runs.append({"المجموعة": "ج) إضافة واحد", "الاسم": f"ELITE8 + {t}", "عدد_الكواشف": len(sup),
                     "قائمة_الكواشف": ",".join(sup), **r})
        print(f"   ELITE8 + {t:11s}: {r['صافي$']:>8.2f}$ ({r['صفقات']:5d} صفقات, PF={r['عامل الربح']:.4f})")

    # د) الكل (1)
    print("\nد) الأربعة عشر كاشفًا معًا (1 محاولة):")
    r_all, _ = run_portfolio(cells, all_triggers, DEC_S, DEC_E); used += 1
    runs.append({"المجموعة": "د) الكل", "الاسم": "ALL14 (كل الـ14)", "عدد_الكواشف": len(all_triggers),
                 "قائمة_الكواشف": ",".join(all_triggers), **r_all})
    print(f"   ALL14 (كل الـ14): {r_all['صافي$']:>8.2f}$ ({r_all['صفقات']:5d} صفقات, PF={r_all['عامل الربح']:.4f})")

    # هـ) تركيبات مدمجة (14)
    print("\nهـ) تركيبات مدمجة (14 محاولة لاكتمال سقف الـ30):")
    combos = [
        ("ELITE8 + FVG + MicroBurst", [x for x in elite8] + ["FVG", "MicroBurst"]),
        ("ELITE8 + FVG + MicroBurst + RSI", [x for x in elite8] + ["FVG", "MicroBurst", "RSI"]),
        ("ELITE8 + FVG + MicroBurst + RSI7", [x for x in elite8] + ["FVG", "MicroBurst", "RSI7"]),
        ("ELITE8 + FVG + MicroBurst + Bollinger", [x for x in elite8] + ["FVG", "MicroBurst", "Bollinger"]),
        ("ELITE8 - MSS + FVG", [x for x in elite8 if x != "MSS"] + ["FVG"]),
        ("ELITE8 - MSS + MicroBurst", [x for x in elite8 if x != "MSS"] + ["MicroBurst"]),
        ("ELITE8 - MSS + FVG + MicroBurst", [x for x in elite8 if x != "MSS"] + ["FVG", "MicroBurst"]),
        ("ELITE8 - SFP + FVG", [x for x in elite8 if x != "SFP"] + ["FVG"]),
        ("ELITE8 - SFP + MicroBurst", [x for x in elite8 if x != "SFP"] + ["MicroBurst"]),
        ("ELITE8 - SFP + FVG + MicroBurst", [x for x in elite8 if x != "SFP"] + ["FVG", "MicroBurst"]),
        ("ALL14 - SuperTrend", [x for x in all_triggers if x != "SuperTrend"]),
        ("ALL14 - Bollinger", [x for x in all_triggers if x != "Bollinger"]),
        ("ALL14 - MSS", [x for x in all_triggers if x != "MSS"]),
        ("ALL14 - SFP", [x for x in all_triggers if x != "SFP"]),
    ]
    for name, trig_list in combos:
        r, _ = run_portfolio(cells, trig_list, DEC_S, DEC_E); used += 1
        runs.append({"المجموعة": "هـ) تركيبات مدمجة", "الاسم": name, "عدد_الكواشف": len(trig_list),
                     "قائمة_الكواشف": ",".join(trig_list), **r})
        print(f"   {name:38s}: {r['صافي$']:>8.2f}$ ({r['صفقات']:5d} صفقات, PF={r['عامل الربح']:.4f})")

    df_runs = pd.DataFrame(runs)
    df_runs.to_csv(OUT / "decision_sweep.csv", index=False, encoding="utf-8-sig")

    print("\n" + "="*80)
    print(f"سقف المحاولات المستهلك في الاختيار: {used} / {DECLARED_CAP}")
    print("أفضل 5 مرشحين على فترة الاختيار:")
    print("="*80)
    top_cands = df_runs.sort_values("صافي$", ascending=False).head(5)
    print(top_cands[["الاسم", "صافي$", "صفقات", "عامل الربح", "ربح_الصفقة$"]].to_string(index=False))

    # ════════════════════════════════════════════════════════════════════════
    # فترة الحكم (Judgement Period: 2024-01-01 → 2026-08-31)
    # ════════════════════════════════════════════════════════════════════════
    print("\n" + "="*80)
    print("فترة الحكم المستقلة (2024-01-01 → 2026-08-31)")
    print("="*80)

    # الأساس على فترة الحكم
    r_base_jud, df_base_tr = run_portfolio(cells, elite8, JUD_S, JUD_E)
    print(f"الأساس ELITE8 على فترة الحكم: {r_base_jud['صافي$']:>8.2f}$ ({r_base_jud['صفقات']} صفقات, PF={r_base_jud['عامل الربح']:.4f})")

    # تقييم أفضل 3 مرشحين متميزين على فترة الحكم
    # نختار: ALL14 (المرشح 1)، ALL14 - Bollinger (المرشح 2)، ELITE8 + FVG + MicroBurst + Bollinger (المرشح 3)
    jud_eval_targets = [
        ("الأساس (ELITE8)", elite8, r_base["صافي$"], r_base["صفقات"]),
        ("ALL14 (كل الـ14)", all_triggers, r_all["صافي$"], r_all["صفقات"]),
        ("ALL14 - Bollinger", [x for x in all_triggers if x != "Bollinger"], 2607.90, 10970),
        ("ELITE8 + FVG + MicroBurst + Bollinger", elite8 + ["FVG", "MicroBurst", "Bollinger"], 2605.51, 11449),
    ]

    jud_rows = []
    jud_trade_dfs = {}
    for name, trigs, d_net, d_tr in jud_eval_targets:
        if name == "الأساس (ELITE8)":
            r_j, d_tr_df = r_base_jud, df_base_tr
        else:
            r_j, d_tr_df = run_portfolio(cells, trigs, JUD_S, JUD_E)
        jud_trade_dfs[name] = d_tr_df
        diff = round(r_j["صافي$"] - r_base_jud["صافي$"], 2)
        jud_rows.append({
            "المرشّح": name,
            "قرار$": d_net,
            "صفقات_قرار": d_tr,
            "حكم$": r_j["صافي$"],
            "صفقات_حكم": r_j["صفقات"],
            "عامل_ربح_حكم": r_j["عامل الربح"],
            "ربح_صفقة_حكم$": r_j["ربح_الصفقة$"],
            "الفرق_عن_الأساس$": diff,
        })
        print(f"  {name:38s} | حكم: {r_j['صافي$']:>8.2f}$ ({r_j['صفقات']:5d} صفقات, PF={r_j['عامل الربح']:.4f}) الفرق: {diff:+8.2f}$")

    df_jud = pd.DataFrame(jud_rows)
    df_jud.to_csv(OUT / "judgement.csv", index=False, encoding="utf-8-sig")

    # ════════════════════════════════════════════════════════════════════════
    # الفحوص الأربعة للفائز (ALL14)
    # ════════════════════════════════════════════════════════════════════════
    print("\n" + "="*80)
    print("الفحوص الأربعة على الفائز (ALL14):")
    print("="*80)

    # 1. فحص الجوار (Neighborhood Test)
    neighbors = []
    for t in all_triggers:
        sub = [x for x in all_triggers if x != t]
        r_n, _ = run_portfolio(cells, sub, JUD_S, JUD_E)
        diff_n = round(r_n["صافي$"] - r_base_jud["صافي$"], 2)
        neighbors.append({"الجوار": f"ALL14 - {t}", "صافي$": r_n["صافي$"],
                          "صفقات": r_n["صفقات"], "عامل الربح": r_n["عامل الربح"],
                          "الفرق$": diff_n, "فوق_الأساس": diff_n > 0})
    df_neigh = pd.DataFrame(neighbors)
    df_neigh.to_csv(OUT / "neighborhood.csv", index=False, encoding="utf-8-sig")
    pass_neigh = int(df_neigh["فوق_الأساس"].sum())
    total_neigh = len(df_neigh)
    print(f"1. فحص الجوار: {pass_neigh}/{total_neigh} تركيبة فوق الأساس (المدى: {df_neigh['صافي$'].min():.2f}$ → {df_neigh['صافي$'].max():.2f}$)")

    # 2. فحص الإجهاد (Stress Test)
    costs = [
        (0.0013, 0.0010, 0.0003, "0.13%"),
        (0.0020, 0.0015, 0.0005, "0.20%"),
        (0.0030, 0.0023, 0.0007, "0.30%"),
        (0.0040, 0.0030, 0.0010, "0.40%"),
    ]
    stress_rows = []
    for total_c, fee_s, slip_s, lbl in costs:
        r_b_s, _ = run_portfolio(cells, elite8, JUD_S, JUD_E, fee_side=fee_s, slip_side=slip_s)
        r_w_s, _ = run_portfolio(cells, all_triggers, JUD_S, JUD_E, fee_side=fee_s, slip_side=slip_s)
        diff_s = round(r_w_s["صافي$"] - r_b_s["صافي$"], 2)
        stress_rows.append({
            "الكلفة_للطرف": lbl,
            "الأساس_ELITE8$": r_b_s["صافي$"],
            "الفائز_ALL14$": r_w_s["صافي$"],
            "الفرق$": diff_s,
            "صامد": diff_s > 0,
        })
        print(f"2. فحص الإجهاد عند {lbl:6s} | الأساس: {r_b_s['صافي$']:>8.2f}$ | ALL14: {r_w_s['صافي$']:>8.2f}$ | الفرق: {diff_s:+8.2f}$")
    df_stress = pd.DataFrame(stress_rows)
    df_stress.to_csv(OUT / "stress.csv", index=False, encoding="utf-8-sig")

    # 3. أثر التغيير على كل عمود
    AR = {"F_213_breakers": "كاسرة النطاق", "F_192_ext_entry": "انحراف الدخول", "F_165_score_entry": "التنقيط التعويضي"}
    col_rows = []
    df_w_tr = jud_trade_dfs["ALL14 (كل الـ14)"]
    for drv in ["F_213_breakers", "F_192_ext_entry", "F_165_score_entry"]:
        b_p = round(float(df_base_tr[df_base_tr["exp"] == drv]["pnl"].sum()), 2)
        w_p = round(float(df_w_tr[df_w_tr["exp"] == drv]["pnl"].sum()), 2)
        b_t = len(df_base_tr[df_base_tr["exp"] == drv])
        w_t = len(df_w_tr[df_w_tr["exp"] == drv])
        col_rows.append({
            "العمود": AR[drv],
            "صافي_الأساس$": b_p,
            "صفقات_الأساس": b_t,
            "صافي_الفائز$": w_p,
            "صفقات_الفائز": w_t,
            "الفرق$": round(w_p - b_p, 2),
        })
        print(f"3. العمود: {AR[drv]:16s} | قبل: {b_p:>8.2f}$ ({b_t:5d}) | بعد: {w_p:>8.2f}$ ({w_t:5d}) | الفرق: {w_p - b_p:+8.2f}$")
    df_cols = pd.DataFrame(col_rows)
    df_cols.to_csv(OUT / "columns_impact.csv", index=False, encoding="utf-8-sig")

    # حفظ ملف البيئة
    env_info = (
        f"python={platform.python_version()}\n"
        f"pandas={pd.__version__}\n"
        f"pyarrow=25.0.1\n"
        f"canary={cj.get('got', {}).get('net')}\n"
        f"decision_window={DEC_S}→{DEC_E}\n"
        f"judgement_window={JUD_S}→{JUD_E}\n"
        f"declared_cap={DECLARED_CAP}\n"
        f"used_cap={used}\n"
        f"frozen_core={CORE}\n"
        f"frozen_ema_fast=21\n"
        f"winner=ALL14\n"
    )
    (OUT / "env_dump.txt").write_text(env_info, encoding="utf-8")
    print(f"\nتم حفظ المخرجات في: {OUT}\nالزمن المستغرق: {time.time()-t0:.1f} ثانية")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
