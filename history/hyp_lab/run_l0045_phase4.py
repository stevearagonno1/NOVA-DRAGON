# -*- coding: utf-8 -*-
"""L0045 — المرحلة 4: محور الجوار الثاني + ضابط البيتا (هل العمود مهارة أم مجرد تعرّض؟).

يستهلك 5 قياسات (الميزانية المتبقية: 40→45 من السقف المعلَن 45).
  1) جوار محور lookback للفائز F-130: [5, 8, 12]  (3 قياسات) — ±20% على المحور الثاني.
  2) ضابط «الشراء الدائم» (always-in): إشارة صحيحة على كل شمعة بنفس قانون الخروج —
     يقيس عائد مجرّد التعرّض للسوق. على فترتي الحكم (1) والاختيار (1).
"""
from __future__ import annotations
import json, os, pathlib, subprocess, sys, time
import numpy as np, pandas as pd

ROOT = pathlib.Path("/home/user/work")
os.environ.setdefault("NOVA_SCRATCH", "/home/user/.nova_scratch")
HIST = ROOT / "history"
sys.path.insert(0, str(HIST / "hyp_lab")); sys.path.insert(0, str(ROOT))

import common as C
from common import atr, simulate, trade_rows
import run_l0019_unified as R19
import run_l0036_more as L36
import F_213_breakers as M213
import F_197_dual_trail as M197
import L0045_signals as S

OUT = HIST / "research" / "hyp_lab_out" / "L0045"
CACHE = ROOT / ".cache" / "l0045_frames"
DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
BAR = 4 * 3600
WIN = {"stop": 2.5, "trig": 0.0015, "lock": 0.0060}
USED_AFTER_P3 = 40

_FR = {}
def frames(sym):
    if sym not in _FR:
        _FR[sym] = pd.read_parquet(CACHE / f"{sym}_4h.parquet")
    return _FR[sym]


def summarize(rows):
    if not rows:
        return {"net": 0.0, "trades": 0, "pf": 0.0, "per": 0.0, "mdd": 0.0}
    t = pd.DataFrame(rows); p = t["pnl"].to_numpy(float)
    g, l = p[p > 0].sum(), -p[p < 0].sum()
    pf = float(g / l) if l > 0 else (np.inf if g > 0 else 0.0)
    eq = np.cumsum(t.sort_values("exit_time")["pnl"].to_numpy(float))
    peak = np.maximum.accumulate(eq)
    net = round(float(p.sum()), 2)
    return {"net": net, "trades": len(t), "pf": round(pf, 4),
            "per": round(net / len(t), 5), "mdd": round(float(np.max(peak - eq)), 2)}


def main():
    t0 = time.time()
    can = subprocess.run([sys.executable, str(ROOT / "tools" / "canary.py"), "--json"],
                         capture_output=True, text=True)
    cj = json.loads(can.stdout[can.stdout.index("{"):]) if "{" in can.stdout else {}
    if cj.get("canary") != "ok":
        print("الكاناري فشل — إيقاف.", file=sys.stderr); return 1

    L36.set_core(); import nova_v8.config as NC; NC.EMA_FAST = 8; M213._cache.clear()
    C.STOP_ATR = WIN["stop"]
    cells = R19.breaker_cells() + R19.new_cells()
    syms = sorted({c["symbol"] for c in cells})
    kw_col = {"exit_mode": "dual",
              "dual": {**M197.make_dual_spec(), "trig": WIN["trig"], "lock": WIN["lock"]}}

    def sim_rows(sig_fn, s0, s1, name):
        rows = []
        for sym in syms:
            win = frames(sym)
            win = win[(win.index >= s0) & (win.index <= s1)]
            if len(win) >= 100:
                _, tr = simulate(win, sig_fn(win).loc[win.index], atr(win),
                                 notional=C.TRADE_USD, bar_secs=BAR, **kw_col)
                rows.extend(trade_rows(sym, name, tr))
        return rows

    used = USED_AFTER_P3
    f130 = S.f130_fvg

    print("=" * 78); print("جوار المحور الثاني للفائز F-130 — lookback"); print("=" * 78)
    nb2, prev = [], pd.read_csv(OUT / "winner_neighborhood.csv", encoding="utf-8-sig")
    for lb in (5, 8, 12):
        s = summarize(sim_rows(lambda w, _lb=lb: f130(w, lookback=_lb), JUD_S, JUD_E, f"F130_lb{lb}"))
        used += 1
        nb2.append({"الإعداد": f"lookback={lb}", **s, "رابح": s["net"] > 0})
        print(f"  lookback={lb}: {s}")
    nb2df = pd.DataFrame(nb2)
    nb2df.to_csv(OUT / "winner_neighborhood_axis2.csv", index=False, encoding="utf-8-sig")

    print("\n" + "=" * 78); print("ضابط البيتا — الشراء الدائم بقانون الخروج نفسه"); print("=" * 78)
    beta_rows = []
    for tag, (s0, s1) in (("JUD", (JUD_S, JUD_E)), ("DEC", (DEC_S, DEC_E))):
        s = summarize(sim_rows(lambda w: pd.Series(True, index=w.index), s0, s1, f"ALWAYS_{tag}"))
        used += 1
        beta_rows.append({"الفترة": tag, **s})
        print(f"  الشراء الدائم {tag}: {s}")
    pd.DataFrame(beta_rows).to_csv(OUT / "beta_control_always_in.csv", index=False, encoding="utf-8-sig")

    print(f"\nالسقف: {used}/45 · الزمن {time.time()-t0:.1f}s")
    p = OUT / "env_dump.txt"
    t = p.read_text(encoding="utf-8")
    t = t.replace("used_p3=11\n", "used_p3=16\n").replace("used_total=40\n", f"used_total={used}\n")
    t += "phase4=5 (جوار محور lookback 3 + ضابط الشراء الدائم 2)\n"
    p.write_text(t, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
