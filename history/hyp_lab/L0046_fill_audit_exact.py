# -*- coding: utf-8 -*-
"""L0046 — اختبار الاستحالة بدقة كاملة (المرحلة 2): كل صفقة، بلا تقريب.

بخلاف ملفات الصفقات (أسعارها مقرَّبة إلى 6 خانات)، هذا التدقيق يقرأ قيم المحرك **الخام**
من موضع الإغلاق نفسه: سعر السوق للدخول والخروج مقابل [low, high] لشمعة التعبئة.
"""
from __future__ import annotations
import pathlib, sys, time
import numpy as np, pandas as pd

ROOT = pathlib.Path("/home/user/work")
sys.path.insert(0, str(ROOT / "history" / "hyp_lab")); sys.path.insert(0, str(ROOT))
import common as C
from common import atr, simulate
import run_l0019_unified as R19, run_l0036_more as L36, F_213_breakers as M213
import F_197_dual_trail as M197, L0017_F_001_rsi2_snap as E001, nova_v8.indicators as ind
import nova_v8.config as NC, run_l0017 as R17
import run_l0046_basis_repair as R46

OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0046"
COST = C.COST_PER_SIDE


def main():
    L36.set_core(); NC.EMA_FAST = 8; M213._cache.clear(); C.STOP_ATR = R46.WIN["stop"]
    cells = R19.breaker_cells() + R19.new_cells()
    syms = sorted({c["symbol"] for c in cells})
    kw = {"exit_mode": "dual", "dual": {**M197.make_dual_spec(), "trig": R46.WIN["trig"],
                                        "lock": R46.WIN["lock"]}}
    tot_v = 0
    for tag, (s0, s1) in (("DEC", (R46.DEC_S, R46.DEC_E)), ("JUD", (R46.JUD_S, R46.JUD_E))):
        rows = []
        for sym in syms:
            df = R46.frames(sym)
            win = df[(df.index >= s0) & (df.index <= s1)]
            if len(win) < 100:
                continue
            a_s = atr(win)
            lo = win["low"].to_numpy(); hi = win["high"].to_numpy()
            idx = win.index
            sigs = []
            for c in [x for x in cells if x["symbol"] == sym]:
                if c["driver"] == "F_213_breakers":
                    sigs.append(M213.make_signals(df, trigger=c["combo"]["trigger"]).loc[win.index])
                else:
                    sigs.append(R17.EXPS[c["driver"]].make_signals(df, **c["combo"]).loc[win.index])
            for nm, fn in R46.NEW_COLS.items():
                sigs.append(fn(df).loc[win.index])
            for sg in sigs:
                _, tr = simulate(win, sg, a_s, notional=C.TRADE_USD, bar_secs=R46.BAR, **kw)
                for p in tr:
                    ej, xj = p["entry_j"], p["exit_j"]
                    m_entry = p["entry"] / (1 + COST)          # سعر السوق الخام للدخول
                    m_exit = p["exit_fill"] / (1 - COST)       # سعر السوق الخام للخروج
                    v_e = (m_entry < lo[ej] - 1e-15) or (m_entry > hi[ej] + 1e-15)
                    v_x = (m_exit < lo[xj] - 1e-15) or (m_exit > hi[xj] + 1e-15)
                    tot_v += int(v_e) + int(v_x)
                    rows.append({"symbol": sym, "entry_bar": str(idx[ej]), "exit_bar": str(idx[xj]),
                                 "entry_market": m_entry, "entry_low": lo[ej], "entry_high": hi[ej],
                                 "exit_market": m_exit, "exit_low": lo[xj], "exit_high": hi[xj],
                                 "exit_side": p["exit_side"], "pnl": round(p["pnl"], 4),
                                 "viol_entry": v_e, "viol_exit": v_x})
        t = pd.DataFrame(rows)
        t.to_csv(OUT / f"exact_fills_{tag}.csv", index=False, encoding="utf-8-sig")
        print(f"{tag}: صفقات={len(t)} · مخالفات دخول={int(t.viol_entry.sum())} · "
              f"مخالفات خروج={int(t.viol_exit.sum())} · "
              f"أقصى تجاوز للخروج={float(np.max(np.maximum(t.exit_market - t.exit_high, t.exit_low - t.exit_market))):.3e}",
              flush=True)
    print(f"\nمجموع المخالفات في الجولتين: {tot_v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
