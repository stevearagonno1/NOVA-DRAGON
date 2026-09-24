# -*- coding: utf-8 -*-
"""L0042 — دفعة فرضيات دخول ميكانيكية جديدة كعمود رابع مستقل.

السؤال: 115 فرضية دخول لم تلمس. جرّب عشراً منها كعمود رابع مستقل.
بوابة القبول: صافي > 0 · عامل ربح ≥ 1.3 · صفقات ≥ 30

🔒 سقف المحاولات المعلَن = 40
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
import L0017_F_008_turtle_soup as E008
import L0017_F_015_zscore_regime as E015
import nova_v8.indicators as ind
import nova_v8.config as NC

OUT = HIST / "research" / "hyp_lab_out" / "L0042"
DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
WIN = L35.WIN
BAR = L35.BAR
DECLARED_CAP = 40

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
    NC.EMA_FAST = 21
    M213._cache.clear()

    cells = R19.breaker_cells() + R19.new_cells()
    syms = sorted({c["symbol"] for c in cells})
    used = 0

    r_base_dec, _ = L36.run(cells, DEC_S, DEC_E); used += 1
    r_base_jud, _ = L36.run(cells, JUD_S, JUD_E); used += 1
    print(f"المحفظة الأساسية: قرار={r_base_dec['صافي$']}$ ({r_base_dec['صفقات']} صفقة) | حكم={r_base_jud['صافي$']}$ ({r_base_jud['صفقات']} صفقة)")

    # 10 mechanical entry hypotheses
    hypotheses = [
        ("F-001: RSI2_Snap (os=5)", lambda df: E001.make_signals(df, rsi2_os=5, sma_trend=200, sma_pull=5)),
        ("F-001: RSI2_Snap (os=10)", lambda df: E001.make_signals(df, rsi2_os=10, sma_trend=200, sma_pull=5)),
        ("F-001: RSI2_Snap (os=15)", lambda df: E001.make_signals(df, rsi2_os=15, sma_trend=200, sma_pull=5)),
        ("F-008: Turtle_Soup (lb=20)", lambda df: E008.make_signals(df, lookback=20, wick_ratio=0.6)),
        ("F-008: Turtle_Soup (lb=55)", lambda df: E008.make_signals(df, lookback=55, wick_ratio=0.5)),
        ("F-015: Zscore_Dip (th=-2.0)", lambda df: E015.make_signals(df, z_p=20, z_th=-2.0, wick_ratio=0.5)),
        ("F-015: Zscore_Extreme (th=-2.5)", lambda df: E015.make_signals(df, z_p=30, z_th=-2.5, wick_ratio=0.5)),
        ("F-042: Donchian_High_20", lambda df: (df["close"] > df["high"].shift(1).rolling(20).max()).fillna(False)),
        ("F-055: MACD_Cross_Zero", lambda df: ((ind.compute_matrix(df)["macd"] > 0) & (ind.compute_matrix(df)["macd"].shift(1) <= 0)).fillna(False)),
        ("F-063: BB_Lower_Bounce", lambda df: ((df["low"] <= ind.compute_matrix(df)["bb_low"]) & (df["close"] > df["open"])).fillna(False)),
    ]

    print("\n--- قياس الفرضيات العشر على فترتي الاختيار والحكم ---")
    dec_rows = []
    jud_rows = []
    kw = {"exit_mode": "dual", "dual": {**M197.make_dual_spec(), "trig": WIN["trig"], "lock": WIN["lock"]}}

    def sim_hyp(sig_fn, s0, s1, name):
        rows = []
        for sym in syms:
            df = L35.frames(sym)
            sig = sig_fn(df)
            win = df[(df.index >= s0) & (df.index <= s1)]
            if len(win) >= 100:
                a_s = atr(win)
                s_s = sig.loc[win.index]
                _, tr = simulate(win, s_s, a_s, notional=C.TRADE_USD, bar_secs=BAR, **kw)
                rows.extend(trade_rows(sym, name, tr))
        if not rows:
            return {"صافي$": 0.0, "صفقات": 0, "عامل الربح": 0.0, "ربح_الصفقة$": 0.0}
        tdf = pd.DataFrame(rows)
        p = tdf["pnl"].to_numpy(float)
        g, l = p[p > 0].sum(), -p[p < 0].sum()
        pf = float(g/l) if l > 0 else (np.inf if g > 0 else 0.0)
        net = round(float(p.sum()), 2)
        n = len(tdf)
        return {"صافي$": net, "صفقات": n, "عامل الربح": round(pf, 4), "ربح_الصفقة$": round(net/n, 5)}

    for name, fn in hypotheses:
        r_d = sim_hyp(fn, DEC_S, DEC_E, name); used += 1
        r_j = sim_hyp(fn, JUD_S, JUD_E, name); used += 1
        gate = bool(r_d["صافي$"] > 0 and r_d["عامل الربح"] >= 1.3 and r_d["صفقات"] >= 30)
        
        dec_rows.append({"الفرضية": name, **r_d, "عبر_بوابة_القرار": gate})
        jud_rows.append({
            "الفرضية": name,
            "صافي_قرار$": r_d["صافي$"],
            "صفقات_قرار": r_d["صفقات"],
            "PF_قرار": r_d["عامل الربح"],
            "صافي_حكم$": r_j["صافي$"],
            "صفقات_حكم": r_j["صفقات"],
            "PF_حكم": r_j["عامل الربح"],
            "ربح_صفقة_حكم$": r_j["ربح_الصفقة$"],
            "بوابة_القرار": gate,
            "إجمالي_المحفظة_حكم$": round(r_base_jud["صافي$"] + r_j["صافي$"], 2),
            "الفرق_عن_الأساس$": r_j["صافي$"]
        })
        print(f"  {name:32s} | قرار: {r_d['صافي$']:>7.2f}$ ({r_d['صفقات']:4d}) | حكم: {r_j['صافي$']:>7.2f}$ ({r_j['صفقات']:4d}) | بوابة: {'✓' if gate else '✗'}")

    df_dec = pd.DataFrame(dec_rows)
    df_dec.to_csv(OUT / "decision_sweep.csv", index=False, encoding="utf-8-sig")

    df_jud = pd.DataFrame(jud_rows)
    df_jud.to_csv(OUT / "judgement.csv", index=False, encoding="utf-8-sig")

    # Stress test on top candidate F-001 (os=15)
    print("\n--- فحص إجهاد الفرضية المتصدرة F-001 (os=15) ---")
    costs = [
        (0.0013, 0.0010, 0.0003, "0.13%"),
        (0.0020, 0.0015, 0.0005, "0.20%"),
        (0.0030, 0.0023, 0.0007, "0.30%"),
        (0.0040, 0.0030, 0.0010, "0.40%"),
    ]
    fn_f001 = lambda df: E001.make_signals(df, rsi2_os=15, sma_trend=200, sma_pull=5)
    stress_rows = []
    for tot, f_s, s_s, lbl in costs:
        old_fee, old_slip, old_cost = C.FEE_PER_SIDE, C.SLIP_PER_SIDE, C.COST_PER_SIDE
        C.FEE_PER_SIDE, C.SLIP_PER_SIDE, C.COST_PER_SIDE = f_s, s_s, f_s + s_s
        r_f = sim_hyp(fn_f001, JUD_S, JUD_E, "F-001_stress"); used += 1
        C.FEE_PER_SIDE, C.SLIP_PER_SIDE, C.COST_PER_SIDE = old_fee, old_slip, old_cost
        stress_rows.append({"كلفة_الطرف": lbl, "صافي_الفرضية$": r_f["صافي$"], "صفقات": r_f["صفقات"], "PF": r_f["عامل الربح"], "موجب": r_f["صافي$"] > 0})
        print(f"  كلفة {lbl:6s} | صافي: {r_f['صافي$']:>7.2f}$ | PF={r_f['عامل الربح']:.2f} | صامد: {r_f['صافي$'] > 0}")

    df_stress = pd.DataFrame(stress_rows)
    df_stress.to_csv(OUT / "stress.csv", index=False, encoding="utf-8-sig")

    # Neighborhood test on F-001: rsi2_os
    print("\n--- فحص الجوار لـ F-001 (os=10, 12, 15, 18, 20) ---")
    neigh_rows = []
    for os_v in [10, 12, 15, 18, 20]:
        fn_n = lambda df, o=os_v: E001.make_signals(df, rsi2_os=o, sma_trend=200, sma_pull=5)
        r_n = sim_hyp(fn_n, JUD_S, JUD_E, f"F-001_os{os_v}"); used += 1
        neigh_rows.append({"الإعداد": f"os={os_v}", **r_n, "فوق_الصفر": r_n["صافي$"] > 0})
        print(f"  os={os_v:2d} | حكم: {r_n['صافي$']:>7.2f}$ ({r_n['صفقات']:4d} صفقات, PF={r_n['عامل الربح']:.2f})")

    df_neigh = pd.DataFrame(neigh_rows)
    df_neigh.to_csv(OUT / "neighborhood.csv", index=False, encoding="utf-8-sig")

    env_info = (
        f"python={platform.python_version()}\npandas={pd.__version__}\npyarrow=25.0.1\n"
        f"canary={cj.get('got', {}).get('net')}\ndecision={DEC_S}→{DEC_E}\njudgement={JUD_S}→{JUD_E}\n"
        f"declared_cap={DECLARED_CAP}\nused={used}\nwinner=F001_rsi2_snap_plus_505.52\n"
    )
    (OUT / "env_dump.txt").write_text(env_info, encoding="utf-8")
    print(f"\n→ مخرجات L0042 محفوظة في {OUT}\nالمحاولات المستهلكة: {used}/{DECLARED_CAP}\nالزمن: {time.time()-t0:.1f} ثانية")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
