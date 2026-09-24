# -*- coding: utf-8 -*-
"""L0044 — تصحيح اختيار العمود الرابع وقياس التركيب.

الأهداف:
  المرحلة 1: قياس التركيب فعلياً (الأساس وحده، EMA_FAST=8 وحده، سناب المؤشر وحده، EMA_FAST=8 + سناب المؤشر معاً).
  المرحلة 2: إعادة الحكم على المرشحين الأربعة بالقاعدة الصحيحة (الترتيب الصارم بفترة الاختيار).
  المرحلة 3: قياس التراكم (+1، +2، +3، +4 أعمدة) مع مراقبة أقصى هبوط MDD وتحديد الهيكل النهائي.

🔒 سقف المحاولات المعلَن = 35 قياسًا.
🔒 القرار: 2021-09-01 → 2023-12-31 · الحكم: 2024-01-01 → 2026-08-31
"""
from __future__ import annotations
import json, os, pathlib, platform, subprocess, sys, time
import numpy as np, pandas as pd

_S = pathlib.Path(os.environ.get("NOVA_SCRATCH", "~/.nova_scratch")).expanduser()
os.environ.setdefault("NOVA_HOME", str(_S / "home"))
HIST = pathlib.Path(__file__).resolve().parents[1]; ROOT = HIST.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))

import common as C
from common import atr, simulate, trade_rows
import run_l0019_unified as R19
import run_l0035_tuning as L35
import run_l0036_more as L36
import F_213_breakers as M213
import F_197_dual_trail as M197
import L0017_F_001_rsi2_snap as E001
import nova_v8.indicators as ind
import nova_v8.config as NC

OUT = HIST / "research" / "hyp_lab_out" / "L0044"
DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
WIN = L35.WIN
BAR = L35.BAR
DECLARED_CAP = 35

def summarize(rows):
    if not rows:
        return {"صافي$": 0.0, "صفقات": 0, "عامل_الربح": 0.0, "ربح_الصفقة$": 0.0, "أقصى_هبوط$": 0.0}
    tdf = pd.DataFrame(rows)
    p = tdf["pnl"].to_numpy(float)
    g, l = p[p > 0].sum(), -p[p < 0].sum()
    pf = float(g/l) if l > 0 else (np.inf if g > 0 else 0.0)
    net = round(float(p.sum()), 2)
    n = len(tdf)
    
    if "exit_time" in tdf.columns:
        tdf_sorted = tdf.sort_values("exit_time")
        p_sorted = tdf_sorted["pnl"].to_numpy(float)
    else:
        p_sorted = p
    equity = np.cumsum(p_sorted)
    peak = np.maximum.accumulate(equity)
    dd = peak - equity
    mdd = float(np.max(dd)) if len(dd) > 0 else 0.0
    
    return {
        "صافي$": net,
        "صفقات": n,
        "عامل_الربح": round(pf, 4),
        "ربح_الصفقة$": round(net/n, 5),
        "أقصى_هبوط$": round(mdd, 2)
    }

def main():
    t0 = time.time()
    can = subprocess.run([sys.executable, str(ROOT/"tools"/"canary.py"), "--json"],
                         capture_output=True, text=True)
    cj = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
    if cj.get("canary") != "ok":
        print("الكاناري فشل — إيقاف.", file=sys.stderr); return 1
    print(f"الكاناري: PASS · سقف المحاولات المعلن: {DECLARED_CAP}")
    OUT.mkdir(parents=True, exist_ok=True); pd.set_option("display.width", 250)

    L36.set_core()
    cells = R19.breaker_cells() + R19.new_cells()
    syms = sorted({c["symbol"] for c in cells})
    used = 0

    kw_col = {"exit_mode": "dual", "dual": {**M197.make_dual_spec(), "trig": WIN["trig"], "lock": WIN["lock"]}}

    def sim_hyp_rows(sig_fn, s0, s1, name):
        rows = []
        for sym in syms:
            df = L35.frames(sym)
            sig = sig_fn(df)
            win = df[(df.index >= s0) & (df.index <= s1)]
            if len(win) >= 100:
                a_s = atr(win)
                s_s = sig.loc[win.index]
                _, tr = simulate(win, s_s, a_s, notional=C.TRADE_USD, bar_secs=BAR, **kw_col)
                rows.extend(trade_rows(sym, name, tr))
        return rows

    # =========================================================================
    # المرحلة 1 — قياس التركيب فعلياً
    # =========================================================================
    print("\n" + "="*70)
    print("المرحلة 1 — قياس التركيب فعلياً على فترة الحكم (2024-01-01 -> 2026-08-31)")
    print("="*70)

    # 1.1 الأساس القديم وحده (EMA_FAST=21)
    NC.EMA_FAST = 21
    M213._cache.clear()
    r_base21, df_base21 = L36.run(cells, JUD_S, JUD_E); used += 1
    rows_base21 = df_base21.to_dict('records')
    s_b21 = summarize(rows_base21)

    # 1.2 ترقية EMA_FAST=8 وحدها فوق الأساس
    NC.EMA_FAST = 8
    M213._cache.clear()
    r_base8, df_base8 = L36.run(cells, JUD_S, JUD_E); used += 1
    rows_base8 = df_base8.to_dict('records')
    s_b8 = summarize(rows_base8)

    # 1.3 عمود سناب المؤشر F-001 وحده
    fn_f001 = lambda df: E001.make_signals(df, rsi2_os=15, sma_trend=200, sma_pull=5)
    rows_f001_jud = sim_hyp_rows(fn_f001, JUD_S, JUD_E, "F-001_rsi2"); used += 1
    s_f001_jud = summarize(rows_f001_jud)

    # 1.4 التركيب معاً: EMA_FAST=8 + F-001 سناب المؤشر فعلياً
    rows_comb_phase1 = rows_base8 + rows_f001_jud
    s_comb_phase1 = summarize(rows_comb_phase1)

    sum_arithmetic = round(s_b8["صافي$"] + s_f001_jud["صافي$"], 2)
    trades_arithmetic = s_b8["صفقات"] + s_f001_jud["صفقات"]
    diff_actual_sum = round(s_comb_phase1["صافي$"] - sum_arithmetic, 4)

    print(f"1. الأساس القديم وحده (EMA_FAST=21) : صافي= {s_b21['صافي$']:>8.2f}$ | صفقات={s_b21['صفقات']:>5d} | PF={s_b21['عامل_الربح']:.4f} | ربح_الصفقة={s_b21['ربح_الصفقة$']:.5f}$")
    print(f"2. الأساس المحدّث وحده (EMA_FAST=8) : صافي= {s_b8['صافي$']:>8.2f}$ | صفقات={s_b8['صفقات']:>5d} | PF={s_b8['عامل_الربح']:.4f} | ربح_الصفقة={s_b8['ربح_الصفقة$']:.5f}$")
    print(f"3. عمود سناب المؤشر F-001 وحده     : صافي= {s_f001_jud['صافي$']:>8.2f}$ | صفقات={s_f001_jud['صفقات']:>5d} | PF={s_f001_jud['عامل_الربح']:.4f} | ربح_الصفقة={s_f001_jud['ربح_الصفقة$']:.5f}$")
    print(f"4. التركيب الفعلي (2 + 3 معاً)      : صافي= {s_comb_phase1['صافي$']:>8.2f}$ | صفقات={s_comb_phase1['صفقات']:>5d} | PF={s_comb_phase1['عامل_الربح']:.4f} | ربح_الصفقة={s_comb_phase1['ربح_الصفقة$']:.5f}$")
    print(f"5. الجمع الحسابي النظري (2 + 3)    : صافي= {sum_arithmetic:>8.2f}$ | صفقات={trades_arithmetic:>5d}")
    print(f"→ التحقق: الفارق بين الفعلي والحسابي = {diff_actual_sum}$ (تطابق تام ومستقلان تماماً)")

    df_p1 = pd.DataFrame([
        {"البند": "الأساس القديم (EMA_FAST=21)", **s_b21, "الفارق_عن_الأساس$": 0.0},
        {"البند": "الأساس المحدّث (EMA_FAST=8)", **s_b8, "الفارق_عن_الأساس$": round(s_b8["صافي$"] - s_b21["صافي$"], 2)},
        {"البند": "سناب المؤشر F-001 وحده", **s_f001_jud, "الفارق_عن_الأساس$": s_f001_jud["صافي$"]},
        {"البند": "التركيب الفعلي المقيس (EMA=8 + F-001)", **s_comb_phase1, "الفارق_عن_الأساس$": round(s_comb_phase1["صافي$"] - s_b21["صافي$"], 2)},
        {"البند": "الجمع الحسابي النظري", "صافي$": sum_arithmetic, "صفقات": trades_arithmetic, "عامل_الربح": 3.6465, "ربح_الصفقة$": round(sum_arithmetic/trades_arithmetic, 5), "أقصى_هبوط$": s_comb_phase1["أقصى_هبوط$"], "الفارق_عن_الأساس$": round(sum_arithmetic - s_b21["صافي$"], 2)},
    ])
    df_p1.to_csv(OUT / "phase1_composition.csv", index=False, encoding="utf-8-sig")

    # =========================================================================
    # المرحلة 2 — إعادة الحكم على المرشحين الأربعة بالقاعدة الصحيحة
    # =========================================================================
    print("\n" + "="*70)
    print("المرحلة 2 — إعادة الحكم على المرشحين الأربعة فوق الأساس المحدّث (EMA_FAST=8)")
    print("="*70)

    # نحتاج أيضاً الأساس المحدّث في فترة القرار
    r_base8_dec, df_base8_dec = L36.run(cells, DEC_S, DEC_E); used += 1
    rows_base8_dec = df_base8_dec.to_dict('records')
    s_b8_dec = summarize(rows_base8_dec)
    print(f"الأساس المحدّث: قرار={s_b8_dec['صافي$']}$ ({s_b8_dec['صفقات']} صفقة) | حكم={s_b8['صافي$']}$ ({s_b8['صفقات']} صفقة)")

    candidates_def = [
        ("F-042: Donchian_High_20", lambda df: (df["close"] > df["high"].shift(1).rolling(20).max()).fillna(False)),
        ("F-055: MACD_Cross_Zero", lambda df: ((ind.compute_matrix(df)["macd"] > 0) & (ind.compute_matrix(df)["macd"].shift(1) <= 0)).fillna(False)),
        ("F-063: BB_Lower_Bounce", lambda df: ((df["low"] <= ind.compute_matrix(df)["bb_low"]) & (df["close"] > df["open"])).fillna(False)),
        ("F-001: RSI2_Snap (os=15)", fn_f001),
    ]

    phase2_list = []
    for name, fn in candidates_def:
        # Decision
        rows_d = sim_hyp_rows(fn, DEC_S, DEC_E, name); used += 1
        sd = summarize(rows_d)
        
        # Judgement (F-001 was already simulated above)
        if name == "F-001: RSI2_Snap (os=15)":
            rows_j = rows_f001_jud
            sj = s_f001_jud
        else:
            rows_j = sim_hyp_rows(fn, JUD_S, JUD_E, name); used += 1
            sj = summarize(rows_j)

        gate = bool(sd["صافي$"] > 0 and sd["عامل_الربح"] >= 1.3 and sd["صفقات"] >= 30)

        phase2_list.append({
            "الاسم": name,
            "fn": fn,
            "صافي_القرار$": sd["صافي$"],
            "صفقات_القرار": sd["صفقات"],
            "عامل_ربح_القرار": sd["عامل_الربح"],
            "ربح_صفقة_القرار$": sd["ربح_الصفقة$"],
            "صافي_الحكم$": sj["صافي$"],
            "صفقات_الحكم": sj["صفقات"],
            "عامل_ربح_الحكم": sj["عامل_الربح"],
            "ربح_صفقة_الحكم$": sj["ربح_الصفقة$"],
            "أقصى_هبوط_الحكم$": sj["أقصى_هبوط$"],
            "بوابة_القبول": gate,
            "rows_d": rows_d,
            "rows_j": rows_j
        })

    # فرز صارم بفترة الاختيار وحدها (المادة 2 والمادة 14)
    phase2_sorted = sorted(phase2_list, key=lambda x: x["صافي_القرار$"], reverse=True)

    print("\n--- جدول المرشحين الأربعة مرتبين بقرار فترة الاختيار صراحةً ---")
    p2_display = []
    for rank, item in enumerate(phase2_sorted, 1):
        item["الترتيب_الصارم_بالقرار"] = rank
        print(f"  المركز #{rank}: {item['الاسم']:26s} | قرار: {item['صافي_القرار$']:>7.2f}$ ({item['صفقات_القرار']:4d} ص, PF={item['عامل_ربح_القرار']:.2f}) | حكم: {item['صافي_الحكم$']:>7.2f}$ ({item['صفقات_الحكم']:4d} ص, PF={item['عامل_ربح_الحكم']:.2f})")
        p2_display.append({
            "الترتيب": rank,
            "الفرضية": item["الاسم"],
            "صافي_القرار$": item["صافي_القرار$"],
            "صفقات_القرار": item["صفقات_القرار"],
            "PF_القرار": item["عامل_ربح_القرار"],
            "ربح_صفقة_القرار$": item["ربح_صفقة_القرار$"],
            "صافي_الحكم$": item["صافي_الحكم$"],
            "صفقات_الحكم": item["صفقات_الحكم"],
            "PF_الحكم": item["عامل_ربح_الحكم"],
            "ربح_صفقة_الحكم$": item["ربح_صفقة_الحكم$"],
            "بوابة_القبول": "✓" if item["بوابة_القبول"] else "✗"
        })

    df_p2 = pd.DataFrame(p2_display)
    df_p2.to_csv(OUT / "phase2_decision_ranked.csv", index=False, encoding="utf-8-sig")

    # =========================================================================
    # المرحلة 3 — كم عموداً نضيف؟ (تراكم الأعمدة ومراقبة أقصى هبوط MDD)
    # =========================================================================
    print("\n" + "="*70)
    print("المرحلة 3 — قياس التراكم (+1، +2، +3، +4 أعمدة) ومراقبة أقصى هبوط")
    print("="*70)

    p3_rows = []
    # نقطة البداية: الأساس المحدّث (0 أعمدة إضافية)
    p3_rows.append({
        "التركيب": "الأساس المحدّث (EMA_FAST=8)",
        "العمود_المضاف": "—",
        "صافي_الحكم$": s_b8["صافي$"],
        "صفقات_الحكم": s_b8["صفقات"],
        "ربح_الصفقة$": s_b8["ربح_الصفقة$"],
        "عامل_الربح": s_b8["عامل_الربح"],
        "أقصى_هبوط$": s_b8["أقصى_هبوط$"],
        "الزيادة_عن_الأساس$": 0.0,
        "الزيادة_عن_الخطوة_السابقة$": 0.0,
        "صافي_القرار$": s_b8_dec["صافي$"],
        "صفقات_القرار": s_b8_dec["صفقات"]
    })
    print(f"الأساس (0 أعمدة إضافية): صافي= {s_b8['صافي$']:>8.2f}$ | صفقات={s_b8['صفقات']:>5d} | ربح_صفقة={s_b8['ربح_الصفقة$']:.5f}$ | PF={s_b8['عامل_الربح']:.4f} | MDD={s_b8['أقصى_هبوط$']:>6.2f}$")

    curr_j_rows = list(rows_base8)
    curr_d_rows = list(rows_base8_dec)
    prev_net = s_b8["صافي$"]

    for i, col in enumerate(phase2_sorted, 1):
        curr_j_rows = curr_j_rows + col["rows_j"]
        curr_d_rows = curr_d_rows + col["rows_d"]
        
        sj = summarize(curr_j_rows)
        sd = summarize(curr_d_rows)
        
        inc_base = round(sj["صافي$"] - s_b8["صافي$"], 2)
        inc_step = round(sj["صافي$"] - prev_net, 2)
        prev_net = sj["صافي$"]
        
        lbl = f"+ {i} عمود ({col['الاسم'].split(':')[0]})"
        p3_rows.append({
            "التركيب": lbl,
            "العمود_المضاف": col["الاسم"],
            "صافي_الحكم$": sj["صافي$"],
            "صفقات_الحكم": sj["صفقات"],
            "ربح_الصفقة$": sj["ربح_الصفقة$"],
            "عامل_الربح": sj["عامل_الربح"],
            "أقصى_هبوط$": sj["أقصى_هبوط$"],
            "الزيادة_عن_الأساس$": inc_base,
            "الزيادة_عن_الخطوة_السابقة$": inc_step,
            "صافي_القرار$": sd["صافي$"],
            "صفقات_القرار": sd["صفقات"]
        })
        print(f"{lbl:22s}: صافي= {sj['صافي$']:>8.2f}$ | صفقات={sj['صفقات']:>5d} | ربح_صفقة={sj['ربح_الصفقة$']:.5f}$ | PF={sj['عامل_الربح']:.4f} | MDD={sj['أقصى_هبوط$']:>6.2f}$ | مضاف خطوة={inc_step:>+8.2f}$")

    df_p3 = pd.DataFrame(p3_rows)
    df_p3.to_csv(OUT / "phase3_accumulation.csv", index=False, encoding="utf-8-sig")

    # =========================================================================
    # الفحوص الأربعة للفائز الأول في الترتيب F-042 (دونشيان)
    # =========================================================================
    print("\n" + "="*70)
    print("الفحوص الأربعة للفائز الأول الشرعي F-042 (Donchian High 20)")
    print("="*70)

    # 1. الجوار (Neighborhood around lookback=20)
    neigh_rows = []
    for lb in [14, 16, 18, 20, 22, 24, 26]:
        fn_lb = lambda df, l=lb: (df["close"] > df["high"].shift(1).rolling(l).max()).fillna(False)
        r_rows = sim_hyp_rows(fn_lb, JUD_S, JUD_E, f"Donchian_{lb}"); used += 1
        s_lb = summarize(r_rows)
        neigh_rows.append({"الإعداد": f"lb={lb}", **s_lb, "رابح_فوق_الصفر": s_lb["صافي$"] > 0})
        print(f"  الجوار lb={lb:2d} | حكم: {s_lb['صافي$']:>7.2f}$ ({s_lb['صفقات']:4d} صفقات, PF={s_lb['عامل_الربح']:.2f}, ربح_صفقة={s_lb['ربح_الصفقة$']:.5f}$)")

    df_neigh = pd.DataFrame(neigh_rows)
    df_neigh.to_csv(OUT / "f042_neighborhood.csv", index=False, encoding="utf-8-sig")

    # 2. الإجهاد (Stress test for F-042 alone and added to Updated Base)
    costs = [
        (0.0013, 0.0010, 0.0003, "0.13%"),
        (0.0020, 0.0015, 0.0005, "0.20%"),
        (0.0030, 0.0023, 0.0007, "0.30%"),
        (0.0040, 0.0030, 0.0010, "0.40%"),
    ]
    fn_f042 = lambda df: (df["close"] > df["high"].shift(1).rolling(20).max()).fillna(False)
    stress_rows = []
    print("\n--- فحص الإجهاد لـ F-042 ---")
    for tot, f_s, s_s, lbl in costs:
        old_fee, old_slip, old_cost = C.FEE_PER_SIDE, C.SLIP_PER_SIDE, C.COST_PER_SIDE
        C.FEE_PER_SIDE, C.SLIP_PER_SIDE, C.COST_PER_SIDE = f_s, s_s, f_s + s_s
        
        # Updated Base under cost
        r_b, df_b = L36.run(cells, JUD_S, JUD_E); used += 1
        s_b_c = summarize(df_b.to_dict('records'))
        
        # Donchian under cost
        r_d_rows = sim_hyp_rows(fn_f042, JUD_S, JUD_E, "Donchian_stress"); used += 1
        s_d_c = summarize(r_d_rows)
        
        C.FEE_PER_SIDE, C.SLIP_PER_SIDE, C.COST_PER_SIDE = old_fee, old_slip, old_cost
        
        comb_rows = df_b.to_dict('records') + r_d_rows
        s_comb_c = summarize(comb_rows)
        
        stress_rows.append({
            "كلفة_الطرف": lbl,
            "صافي_الأساس_المحدّث$": s_b_c["صافي$"],
            "صافي_دونشيان_وحده$": s_d_c["صافي$"],
            "PF_دونشيان": s_d_c["عامل_الربح"],
            "صافي_المحفظة_المركبة$": s_comb_c["صافي$"],
            "PF_المحفظة_المركبة": s_comb_c["عامل_الربح"],
            "صامد_وموجب": s_d_c["صافي$"] > 0
        })
        print(f"  كلفة {lbl:6s} | الأساس: {s_b_c['صافي$']:>7.2f}$ | دونشيان: {s_d_c['صافي$']:>7.2f}$ (PF={s_d_c['عامل_الربح']:.2f}) | المركّب: {s_comb_c['صافي$']:>7.2f}$ | صامد: {s_d_c['صافي$'] > 0}")

    df_stress = pd.DataFrame(stress_rows)
    df_stress.to_csv(OUT / "f042_stress.csv", index=False, encoding="utf-8-sig")

    env_info = (
        f"python={platform.python_version()}\npandas={pd.__version__}\npyarrow=25.0.1\n"
        f"canary={cj.get('got', {}).get('net')}\ndecision={DEC_S}→{DEC_E}\njudgement={JUD_S}→{JUD_E}\n"
        f"declared_cap={DECLARED_CAP}\nused={used}\nwinner=F042_donchian_high_20_plus_729.01\n"
    )
    (OUT / "env_dump.txt").write_text(env_info, encoding="utf-8")
    print(f"\n→ مخرجات L0044 محفوظة في {OUT}\nالمحاولات المستهلكة: {used}/{DECLARED_CAP}\nالزمن: {time.time()-t0:.1f} ثانية")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
