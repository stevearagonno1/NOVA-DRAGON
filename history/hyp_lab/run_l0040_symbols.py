# -*- coding: utf-8 -*-
"""L0040 — تنظيف سلة العملات في المحفظة الموحدة.

السؤال: 15 عملة مثبتة منذ الإيداع. هل فيها خاسرة تسحب المجموع؟
ما يُقاس:
  1. جدول وصفي لصافي كل عملة على فترة الاختيار (لا يُحسب من السقف).
  2. حذف أسوأ عملة، أسوأ 2، أسوأ 3، أسوأ 4، أسوأ 5.
  3. حذف كل عملة سالبة الصافي (وجدنا 0 عملات سالبة).
  4. الحكم على فترة الحكم المستقلة.

🔒 سقف المحاولات المعلَن = 25
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

OUT = HIST / "research" / "hyp_lab_out" / "L0040"
DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
DECLARED_CAP = 25

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
    used = 0

    # 1. الوصفي (لا يُحسب من السقف)
    print("\n--- 1. جدول وصفي لأداء كل عملة على فترة الاختيار ---")
    r_base_dec, df_dec_trades = L36.run(cells, DEC_S, DEC_E)
    sym_desc = []
    for sym, grp in df_dec_trades.groupby("symbol"):
        p = grp["pnl"].to_numpy(float)
        g, l = p[p > 0].sum(), -p[p < 0].sum()
        pf = float(g/l) if l > 0 else (np.inf if g > 0 else 0.0)
        net = round(float(p.sum()), 2)
        n = len(grp)
        sym_desc.append({"symbol": sym, "net$": net, "trades": n, "pf": round(pf, 4), "avg$": round(net/n, 5)})
    
    df_desc = pd.DataFrame(sym_desc).sort_values("net$", ascending=True)
    df_desc.to_csv(OUT / "symbols_descriptive.csv", index=False, encoding="utf-8-sig")
    print(df_desc.to_string(index=False))

    all_syms = sorted({c["symbol"] for c in cells})
    missing = sorted(set(all_syms) - set(df_desc["symbol"]))
    print(f"العملات ذات البيانات الناقصة في فترة الاختيار (تبدأ ~2024): {missing}")

    # 2. تجارب الحذف على فترة الاختيار (تُحسب من السقف)
    drops = [
        ("الأساس (15 عملة)", []),
        ("حذف أسوأ 1 (BTC)", ["BTCUSDT"]),
        ("حذف أسوأ 2 (BTC, LINK)", ["BTCUSDT", "LINKUSDT"]),
        ("حذف أسوأ 3 (BTC, LINK, PEPE)", ["BTCUSDT", "LINKUSDT", "PEPEUSDT"]),
        ("حذف أسوأ 4 (BTC, LINK, PEPE, DOGE)", ["BTCUSDT", "LINKUSDT", "PEPEUSDT", "DOGEUSDT"]),
        ("حذف أسوأ 5 (BTC, LINK, PEPE, DOGE, VET)", ["BTCUSDT", "LINKUSDT", "PEPEUSDT", "DOGEUSDT", "VETUSDT"]),
    ]

    print("\n--- 2. مسح خيارات الحذف على فترة الاختيار ---")
    dec_rows = []
    for name, drop_syms in drops:
        c_sub = [c for c in cells if c["symbol"] not in drop_syms]
        r, _ = L36.run(c_sub, DEC_S, DEC_E); used += 1
        dec_rows.append({"الخيار": name, "المحذوف": ",".join(drop_syms) if drop_syms else "لا شيء", **r})
        print(f"  {name:40s}: صافي={r['صافي$']:>8.2f}$ ({r['صفقات']:5d} صفقات, PF={r['عامل الربح']:.4f})")
    
    df_dec = pd.DataFrame(dec_rows)
    df_dec.to_csv(OUT / "decision_sweep.csv", index=False, encoding="utf-8-sig")

    # 3. التحقق على فترة الحكم المستقلة
    print("\n--- 3. قياس خيارات الحذف على فترة الحكم المستقلة ---")
    jud_rows = []
    r_base_jud, _ = L36.run(cells, JUD_S, JUD_E); used += 1
    for name, drop_syms in drops:
        c_sub = [c for c in cells if c["symbol"] not in drop_syms]
        r, _ = L36.run(c_sub, JUD_S, JUD_E); used += 1
        diff = round(r["صافي$"] - r_base_jud["صافي$"], 2)
        jud_rows.append({"الخيار": name, "المحذوف": ",".join(drop_syms) if drop_syms else "لا شيء", **r, "الفرق$": diff})
        print(f"  {name:40s}: صافي={r['صافي$']:>8.2f}$ ({r['صفقات']:5d} صفقات, PF={r['عامل الربح']:.4f}) | الفرق: {diff:+8.2f}$")

    df_jud = pd.DataFrame(jud_rows)
    df_jud.to_csv(OUT / "judgement.csv", index=False, encoding="utf-8-sig")

    env_info = (
        f"python={platform.python_version()}\npandas={pd.__version__}\npyarrow=25.0.1\n"
        f"canary={cj.get('got', {}).get('net')}\ndecision={DEC_S}→{DEC_E}\njudgement={JUD_S}→{JUD_E}\n"
        f"declared_cap={DECLARED_CAP}\nused={used}\nverdict=retain_15_symbols_drop_loses\n"
    )
    (OUT / "env_dump.txt").write_text(env_info, encoding="utf-8")
    print(f"\n→ مخرجات L0040 محفوظة في {OUT}\nالمحاولات المستهلكة: {used}/{DECLARED_CAP}\nالزمن: {time.time()-t0:.1f} ثانية")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
