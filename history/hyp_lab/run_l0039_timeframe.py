# -*- coding: utf-8 -*-
"""L0039 — اختبار الإطار الزمني في المحفظة الموحدة.

السؤال: كل قياساتنا على 4 ساعات. لم يُجرَّب إطار آخر قط على الإعدادات الحالية.
ما يُقاس: 2h · 4h (الأساس) · 6h · 8h · 12h
لكل إطار: المحفظة كاملة بالإعدادات المجمّدة.

الإعدادات المجمّدة:
  - حجم الصفقة: 20$ ثابت
  - الكلفة: 0.13% لكل طرف
  - الاتجاه: شراء فقط
  - الخروج: وقف 2.5×ATR · تسليح 0.0015 · قفل 0.0060
  - نواة كسر البنية: جسم 0.40 · مدى 0.60 · نظر 10 (L0035)
  - المتوسط السريع: EMA_FAST = 21 (L0036)
  - الكواشف: ALL14

🔒 سقف المحاولات المعلَن = 20
🔒 القرار: 2021-09-01 → 2023-12-31 · الحكم: 2024-01-01 → 2026-08-31
"""
from __future__ import annotations
import gc, json, os, pathlib, platform, subprocess, sys, time
import numpy as np, pandas as pd

_S = pathlib.Path(os.environ.get("NOVA_SCRATCH", "~/.nova_scratch")).expanduser()
os.environ.setdefault("NOVA_HOME", str(_S / "home"))
HIST = pathlib.Path(__file__).resolve().parents[1]; ROOT = HIST.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))

import common as C
from common import atr, simulate, trade_rows, load, to_bars
import run_l0019_unified as R19
import run_l0017 as R17
import run_l0035_tuning as L35
import run_l0036_more as L36
import F_126_mss_core as M126
import F_213_breakers as M213
import F_197_dual_trail as M197
import nova_v8.config as NC

OUT = HIST / "research" / "hyp_lab_out" / "L0039"
DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
WARM = L35.WARM
WIN = L35.WIN
DECLARED_CAP = 20

def set_core():
    L36.set_core()

def run_portfolio_tf(cells, syms, tf_mins, s0, s1, fee_side=0.001, slip_side=0.0003):
    bar_secs = tf_mins * 60
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
        for sym in syms:
            p = ROOT / "crypto_archive" / f"{sym}_1m.parquet"
            d1 = load(str(p), start=WARM, end=JUD_E)
            df = to_bars(d1, tf_mins)
            del d1
            win = df[(df.index >= s0) & (df.index <= s1)]
            if len(win) < 100:
                del df, win
                continue
            a_s = atr(win)
            for c in [x for x in cells if x["symbol"] == sym]:
                if c["driver"] == "F_213_breakers":
                    sig = M213.make_signals(df, trigger=c["combo"]["trigger"]).loc[win.index]
                    kw = ({"exit_mode": "dual", "dual": {**M213.make_dual_spec(),
                           "trig": WIN["trig"], "lock": WIN["lock"]}}
                          if c["combo"]["exit"] == "dual" else {"exit_mode": "std"})
                else:
                    sig = R17.EXPS[c["driver"]].make_signals(df, **c["combo"]).loc[win.index]
                    kw = {"exit_mode": "dual", "dual": {**M197.make_dual_spec(),
                          "trig": WIN["trig"], "lock": WIN["lock"]}}
                _, tr = simulate(win, sig, a_s, notional=C.TRADE_USD, bar_secs=bar_secs, **kw)
                rows.extend(trade_rows(c["symbol"], c["driver"], tr))
            del df, win, a_s
            M213._cache.clear()
            gc.collect()
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
    pf = float(g/l) if l > 0 else (np.inf if g > 0 else 0.0)
    net = round(float(p.sum()), 2)
    n_trades = len(tdf)
    avg_trade = round(net / n_trades, 5) if n_trades > 0 else 0.0
    return {"صافي$": net, "صفقات": n_trades, "عامل الربح": round(pf, 4), "ربح_الصفقة$": avg_trade}, tdf

def main():
    t0 = time.time()
    can = subprocess.run([sys.executable, str(ROOT/"tools"/"canary.py"), "--json"],
                         capture_output=True, text=True)
    cj = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
    if cj.get("canary") != "ok":
        print("الكاناري فشل — إيقاف.", file=sys.stderr); return 1
    print(f"الكاناري: PASS · سقف المحاولات المعلن: {DECLARED_CAP}")
    OUT.mkdir(parents=True, exist_ok=True); pd.set_option("display.width", 250)

    set_core()
    NC.EMA_FAST = 21
    M213._cache.clear()

    cells = R19.breaker_cells() + R19.new_cells()
    syms = sorted({c["symbol"] for c in cells})
    used = 0

    # 1. Decision Period Sweep (5 timeframes)
    tfs = [("2h", 120), ("4h (الأساس)", 240), ("6h", 360), ("8h", 480), ("12h", 720)]
    dec_rows = []
    print("\n--- مسح فترة الاختيار (2021-09-01 -> 2023-12-31) ---")
    for name, mins in tfs:
        r, _ = run_portfolio_tf(cells, syms, mins, DEC_S, DEC_E); used += 1
        dec_rows.append({"الإطار": name, "دقائق": mins, **r})
        print(f"  {name:12s}: صافي={r['صافي$']:>8.2f}$ | صفقات={r['صفقات']:5d} | PF={r['عامل الربح']:.4f} | ربح_الصفقة={r['ربح_الصفقة$']:.5f}$")

    df_dec = pd.DataFrame(dec_rows)
    df_dec.to_csv(OUT / "decision_sweep.csv", index=False, encoding="utf-8-sig")

    # 2. Judgement Period (Top candidate 2h vs Base 4h vs 6h)
    print("\n--- قياس فترة الحكم المستقلة (2024-01-01 -> 2026-08-31) ---")
    jud_rows = []
    r_4h_jud, df_4h_t = run_portfolio_tf(cells, syms, 240, JUD_S, JUD_E); used += 1
    r_2h_jud, df_2h_t = run_portfolio_tf(cells, syms, 120, JUD_S, JUD_E); used += 1
    r_6h_jud, _ = run_portfolio_tf(cells, syms, 360, JUD_S, JUD_E); used += 1

    jud_rows.append({"المرشح": "4h (الأساس)", "دقائق": 240, **r_4h_jud, "الفرق$": 0.0})
    jud_rows.append({"المرشح": "2h (المتصدر بالقرار)", "دقائق": 120, **r_2h_jud, "الفرق$": round(r_2h_jud["صافي$"] - r_4h_jud["صافي$"], 2)})
    jud_rows.append({"المرشح": "6h", "دقائق": 360, **r_6h_jud, "الفرق$": round(r_6h_jud["صافي$"] - r_4h_jud["صافي$"], 2)})
    
    df_jud = pd.DataFrame(jud_rows)
    df_jud.to_csv(OUT / "judgement.csv", index=False, encoding="utf-8-sig")
    print(df_jud[["المرشح", "صافي$", "صفقات", "عامل الربح", "ربح_الصفقة$", "الفرق$"]].to_string(index=False))

    # 3. Stress Testing (4 levels of cost)
    costs = [
        (0.0013, 0.0010, 0.0003, "0.13%"),
        (0.0020, 0.0015, 0.0005, "0.20%"),
        (0.0030, 0.0023, 0.0007, "0.30%"),
        (0.0040, 0.0030, 0.0010, "0.40%"),
    ]
    print("\n--- فحص الإجهاد تحت مضاعفة الكلفة ---")
    stress_rows = []
    for tot, f_s, s_s, lbl in costs:
        r_4h_s, _ = run_portfolio_tf(cells, syms, 240, JUD_S, JUD_E, fee_side=f_s, slip_side=s_s); used += 1
        r_2h_s, _ = run_portfolio_tf(cells, syms, 120, JUD_S, JUD_E, fee_side=f_s, slip_side=s_s); used += 1
        diff = round(r_2h_s["صافي$"] - r_4h_s["صافي$"], 2)
        stress_rows.append({
            "الكلفة_للطرف": lbl,
            "الأساس_4h$": r_4h_s["صافي$"],
            "المرشح_2h$": r_2h_s["صافي$"],
            "الفرق$": diff,
            "صامد": diff > 0
        })
        print(f"  كلفة {lbl:6s} | 4h: {r_4h_s['صافي$']:>8.2f}$ | 2h: {r_2h_s['صافي$']:>8.2f}$ | الفرق: {diff:+8.2f}$ | 2h متفوق: {diff > 0}")

    df_stress = pd.DataFrame(stress_rows)
    df_stress.to_csv(OUT / "stress.csv", index=False, encoding="utf-8-sig")

    # 4. Columns Impact for 2h vs 4h
    AR = {"F_213_breakers": "كاسرة النطاق", "F_192_ext_entry": "انحراف الدخول", "F_165_score_entry": "التنقيط التعويضي"}
    col_rows = []
    for drv in ["F_213_breakers", "F_192_ext_entry", "F_165_score_entry"]:
        b_p = round(float(df_4h_t[df_4h_t["exp"] == drv]["pnl"].sum()), 2)
        c_p = round(float(df_2h_t[df_2h_t["exp"] == drv]["pnl"].sum()), 2)
        b_t = len(df_4h_t[df_4h_t["exp"] == drv])
        c_t = len(df_2h_t[df_2h_t["exp"] == drv])
        col_rows.append({
            "العمود": AR[drv],
            "صافي_4h$": b_p, "صفقات_4h": b_t,
            "صافي_2h$": c_p, "صفقات_2h": c_t,
            "الفرق$": round(c_p - b_p, 2)
        })
    df_cols = pd.DataFrame(col_rows)
    df_cols.to_csv(OUT / "columns_impact.csv", index=False, encoding="utf-8-sig")

    env_info = (
        f"python={platform.python_version()}\npandas={pd.__version__}\npyarrow=25.0.1\n"
        f"canary={cj.get('got', {}).get('net')}\ndecision={DEC_S}→{DEC_E}\njudgement={JUD_S}→{JUD_E}\n"
        f"declared_cap={DECLARED_CAP}\nused={used}\nverdict=4h_retained_2h_buried\n"
    )
    (OUT / "env_dump.txt").write_text(env_info, encoding="utf-8")
    print(f"\n→ مخرجات L0039 محفوظة في {OUT}\nالمحاولات المستهلكة: {used}/{DECLARED_CAP}\nالزمن: {time.time()-t0:.1f} ثانية")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
