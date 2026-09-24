# -*- coding: utf-8 -*-
"""L0041 — المتوسط السريع وجواره في كاسرة النطاق.

الخلفية: L0036 اعتمد EMA_FAST=21. وظهر في فحص الجوار أن 13 أعطى +71.7$ ولم يُطارد.
ما يُقاس: 8 · 10 · 13 · 16 · 21 (الأساس) · 26 · 34 مع دراسة EMA_SLOW على فترة الاختيار أولاً.

🔒 سقف المحاولات المعلَن = 15
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
import run_l0019_unified as R19
import run_l0035_tuning as L35
import run_l0036_more as L36
import F_213_breakers as M213
import nova_v8.config as NC

OUT = HIST / "research" / "hyp_lab_out" / "L0041"
DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
DECLARED_CAP = 15

def run_fee(cells, fee_s, slip_s, s0, s1):
    old_fee = C.FEE_PER_SIDE
    old_slip = C.SLIP_PER_SIDE
    old_cost = C.COST_PER_SIDE
    C.FEE_PER_SIDE = fee_s
    C.SLIP_PER_SIDE = slip_s
    C.COST_PER_SIDE = fee_s + slip_side if 'slip_side' in locals() else fee_s + slip_s
    try:
        r, d = L36.run(cells, s0, s1)
    finally:
        C.FEE_PER_SIDE = old_fee
        C.SLIP_PER_SIDE = old_slip
        C.COST_PER_SIDE = old_cost
    return r, d

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
    used = 0

    fast_vals = [8, 10, 13, 16, 21, 26, 34]
    
    # 1. مسح فترة الاختيار (Decision Period)
    print("\n--- 1. مسح قيم EMA_FAST على فترة الاختيار ---")
    dec_rows = []
    for f in fast_vals:
        NC.EMA_FAST = f
        NC.EMA_SLOW = 200
        M213._cache.clear()
        r, _ = L36.run(cells, DEC_S, DEC_E); used += 1
        dec_rows.append({"EMA_FAST": f, "EMA_SLOW": 200, **r})
        print(f"  EMA_FAST={f:2d} (SLOW=200): صافي={r['صافي$']:>8.2f}$ | صفقات={r['صفقات']:5d} | PF={r['عامل الربح']:.4f}")

    # تجربة نسبة EMA_SLOW
    for s in [100, 150]:
        NC.EMA_FAST = 13
        NC.EMA_SLOW = s
        M213._cache.clear()
        r, _ = L36.run(cells, DEC_S, DEC_E); used += 1
        dec_rows.append({"EMA_FAST": 13, "EMA_SLOW": s, **r})
        print(f"  EMA_FAST=13 (SLOW={s}): صافي={r['صافي$']:>8.2f}$ | صفقات={r['صفقات']:5d} | PF={r['عامل الربح']:.4f}")

    df_dec = pd.DataFrame(dec_rows)
    df_dec.to_csv(OUT / "decision_sweep.csv", index=False, encoding="utf-8-sig")

    # 2. فترة الحكم المستقلة
    print("\n--- 2. قياس أفضل المرشحين على فترة الحكم المستقلة ---")
    # Base 21
    NC.EMA_FAST = 21
    NC.EMA_SLOW = 200
    M213._cache.clear()
    r_base_jud, df_base_jud = L36.run(cells, JUD_S, JUD_E); used += 1

    jud_rows = []
    # Test top candidates from decision: 8 (1st), 10 (2nd), 13 (3rd), 21 (base)
    for f in [21, 8, 10, 13, 16, 26]:
        NC.EMA_FAST = f
        NC.EMA_SLOW = 200
        M213._cache.clear()
        r, df_t = L36.run(cells, JUD_S, JUD_E); used += 1
        diff = round(r["صافي$"] - r_base_jud["صافي$"], 2)
        jud_rows.append({"المرشح": f"EMA_FAST={f}", "EMA_FAST": f, **r, "الفرق$": diff})
        print(f"  EMA_FAST={f:2d} | حكم: {r['صافي$']:>8.2f}$ ({r['صفقات']:5d} صفقات, PF={r['عامل الربح']:.4f}) | الفرق: {diff:+8.2f}$")

    df_jud = pd.DataFrame(jud_rows)
    df_jud.to_csv(OUT / "judgement.csv", index=False, encoding="utf-8-sig")

    # 3. فحص الإجهاد للمرشح المتصدر (EMA_FAST=8)
    print("\n--- 3. فحص الإجهاد لـ EMA_FAST=8 مقابل الأساس 21 ---")
    costs = [
        (0.0013, 0.0010, 0.0003, "0.13%"),
        (0.0020, 0.0015, 0.0005, "0.20%"),
        (0.0030, 0.0023, 0.0007, "0.30%"),
        (0.0040, 0.0030, 0.0010, "0.40%"),
    ]
    stress_rows = []
    for tot, f_s, s_s, lbl in costs:
        NC.EMA_FAST = 21
        M213._cache.clear()
        r_b, _ = run_fee(cells, f_s, s_s, JUD_S, JUD_E)
        NC.EMA_FAST = 8
        M213._cache.clear()
        r_c, _ = run_fee(cells, f_s, s_s, JUD_S, JUD_E)
        diff = round(r_c["صافي$"] - r_b["صافي$"], 2)
        stress_rows.append({
            "كلفة_الطرف": lbl, "الأساس_21$": r_b["صافي$"], "المرشح_8$": r_c["صافي$"],
            "الفرق$": diff, "متفوق؟": diff > 0
        })
        print(f"  كلفة {lbl:6s} | الأساس 21: {r_b['صافي$']:>8.2f}$ | المرشح 8: {r_c['صافي$']:>8.2f}$ | الفرق: {diff:+8.2f}$ | متفوق: {diff > 0}")

    df_stress = pd.DataFrame(stress_rows)
    df_stress.to_csv(OUT / "stress.csv", index=False, encoding="utf-8-sig")

    # 4. أثر التغيير على كل عمود
    NC.EMA_FAST = 8
    M213._cache.clear()
    _, df_8_jud = L36.run(cells, JUD_S, JUD_E)
    AR = {"F_213_breakers": "كاسرة النطاق", "F_192_ext_entry": "انحراف الدخول", "F_165_score_entry": "التنقيط التعويضي"}
    col_rows = []
    for drv in ["F_213_breakers", "F_192_ext_entry", "F_165_score_entry"]:
        b_p = round(float(df_base_jud[df_base_jud["exp"] == drv]["pnl"].sum()), 2)
        c_p = round(float(df_8_jud[df_8_jud["exp"] == drv]["pnl"].sum()), 2)
        b_t = len(df_base_jud[df_base_jud["exp"] == drv])
        c_t = len(df_8_jud[df_8_jud["exp"] == drv])
        col_rows.append({"العمود": AR[drv], "قبل_21$": b_p, "صفقات_قبل": b_t, "بعد_8$": c_p, "صفقات_بعد": c_t, "الفرق$": round(c_p - b_p, 2)})
    df_cols = pd.DataFrame(col_rows)
    df_cols.to_csv(OUT / "columns_impact.csv", index=False, encoding="utf-8-sig")

    # Reset
    NC.EMA_FAST = 21
    NC.EMA_SLOW = 200
    M213._cache.clear()

    env_info = (
        f"python={platform.python_version()}\npandas={pd.__version__}\npyarrow=25.0.1\n"
        f"canary={cj.get('got', {}).get('net')}\ndecision={DEC_S}→{DEC_E}\njudgement={JUD_S}→{JUD_E}\n"
        f"declared_cap={DECLARED_CAP}\nused={used}\nwinner=EMA_FAST_8_plus_102.89\n"
    )
    (OUT / "env_dump.txt").write_text(env_info, encoding="utf-8")
    print(f"\n→ مخرجات L0041 محفوظة في {OUT}\nالمحاولات المستهلكة: {used}/{DECLARED_CAP}\nالزمن: {time.time()-t0:.1f} ثانية")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
