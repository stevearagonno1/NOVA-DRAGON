# -*- coding: utf-8 -*-
"""L0045 — معايرة آلة الخروج (تقدير الحقيقة) — ليست فرضية ولا انتقاء مرشّح.

ثلاث آلات على نفس الإشارات ونفس النوافذ:
  E0 (المحرك الحالي) : تسليح متأخر شمعة + تعبئة عند سعر الوقف مهما كان (تنفيذ مستحيل أحياناً).
  E1 (دفاعية)        : تسليح متأخر شمعة + تعبئة = min(eff, open) — حدّ أدنى متشائم.
  E2 (معايَرة)       : تسليح داخل الشمعة + قفل الربح لا يُفعّل إلا بعد بلوغه + تعبئة ممكنة.

E2 هي القراءة المقترحة للحقيقة: المتتبّع يعمل داخل الشمعة (كما في نظام حي)، والصفقة
لا تُغلق أبداً بسعر لم يلمسه السوق.
"""
from __future__ import annotations
import json, os, pathlib, platform, subprocess, sys, time
import numpy as np, pandas as pd

ROOT = pathlib.Path("/home/user/work")
os.environ.setdefault("NOVA_SCRATCH", "/home/user/.nova_scratch")
HIST = ROOT / "history"
sys.path.insert(0, str(HIST / "hyp_lab")); sys.path.insert(0, str(ROOT))

import common as C
from common import atr, trade_rows
import run_l0019_unified as R19
import run_l0036_more as L36
import F_213_breakers as M213
import F_197_dual_trail as M197
import L0017_F_001_rsi2_snap as E001
import nova_v8.indicators as ind
import nova_v8.config as NC
import L0045_signals as S
import run_l0017 as R17

OUT = HIST / "research" / "hyp_lab_out" / "L0045" / "calibration"
OUT.mkdir(parents=True, exist_ok=True)
CACHE = ROOT / ".cache" / "l0045_frames"
DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
WIN = {"stop": 2.5, "trig": 0.0015, "lock": 0.0060}
_FR = {}
def frames(s):
    if s not in _FR: _FR[s] = pd.read_parquet(CACHE / f"{s}_4h.parquet")
    return _FR[s]


def simulate_e(df, sig, atr_s, intrabar=False, notional=C.TRADE_USD, bar_secs=14400):
    o = df["open"].to_numpy(); h = df["high"].to_numpy()
    l = df["low"].to_numpy(); c = df["close"].to_numpy()
    a = atr_s.to_numpy(); n = len(df); idx = df.index
    sig_i = np.flatnonzero(sig.to_numpy())
    if sig_i.size == 0: return []
    STOP_ATR = C.STOP_ATR; COST = C.COST_PER_SIDE
    trig, lock, wide, tight = WIN["trig"], WIN["lock"], 0.0020, 0.0008
    trades = []

    def close_at(p, j, price, side):
        fill = min(price, o[j]) * (1 - COST)          # تعبئة ممكنة فقط
        qty = p["notional"] / p["entry"]
        p["pnl"] = qty * (fill - p["entry"]); p["exit_fill"] = fill; p["exit_j"] = j
        p["exit_time"] = idx[j]; p["exit_side"] = side; p["done"] = True

    def open_(i):
        e = i + 1
        if e >= n or not np.isfinite(a[i]): return None
        ef = o[e] * (1 + COST)
        return {"entry_j": e, "entry": ef, "entry_time": idx[e], "notional": notional,
                "risk": None, "hard_stop": ef - STOP_ATR * a[i], "peak": o[e], "done": False, "pnl": 0.0}

    def step(p, j):
        peak = max(p["peak"], h[j]) if intrabar else p["peak"]
        gain = (peak - p["entry"]) / p["entry"]
        eff = p["hard_stop"]
        if gain >= trig:
            trail = wide if gain <= 0.01 else tight
            eff = max(eff, peak * (1 - trail))
            if intrabar and peak >= p["entry"] * (1 + lock):
                eff = max(eff, p["entry"] * (1 + lock))
            elif not intrabar:
                eff = max(eff, p["entry"] * (1 + lock))     # سلوك المحرك الحالي
        if l[j] <= eff:
            close_at(p, j, eff, "stop"); return True
        p["peak"] = max(peak, h[j])      # (إصلاح) تحديث القمة في الوضعين
        return False

    pos = None
    for i in sig_i:
        if pos is not None:
            j = pos["entry_j"]
            while j < n and not step(pos, j): j += 1
            if not pos["done"]: close_at(pos, n - 1, c[-1], "eod")
            trades.append(pos)
            pos = None
            if trades[-1]["exit_j"] > i: continue
        p = open_(i)
        if p is not None: pos = p
    if pos is not None:
        j = pos["entry_j"]
        while j < n and not step(pos, j): j += 1
        if not pos["done"]: close_at(pos, n - 1, c[-1], "eod")
        trades.append(pos)
    return trades


def summarize(rows):
    if not rows: return {"net": 0.0, "trades": 0, "pf": 0.0, "per": 0.0, "mdd": 0.0}
    t = pd.DataFrame(rows); p = t["pnl"].to_numpy(float)
    g, l = p[p > 0].sum(), -p[p < 0].sum()
    pf = float(g / l) if l > 0 else (np.inf if g > 0 else 0.0)
    eq = np.cumsum(t.sort_values("exit_time")["pnl"].to_numpy(float))
    peak = np.maximum.accumulate(eq)
    net = round(float(p.sum()), 2)
    return {"net": net, "trades": len(t), "pf": round(pf, 4), "per": round(net / len(t), 5),
            "mdd": round(float(np.max(peak - eq)), 2)}


def main():
    t0 = time.time()
    subprocess.run([sys.executable, str(ROOT / "tools" / "canary.py"), "--json"], capture_output=True)
    L36.set_core(); NC.EMA_FAST = 8; M213._cache.clear(); C.STOP_ATR = WIN["stop"]
    cells = R19.breaker_cells() + R19.new_cells()
    syms = sorted({c["symbol"] for c in cells})
    kw = {"dual": {**M197.make_dual_spec(), "trig": WIN["trig"], "lock": WIN["lock"]}}

    def run_e1(fn, s0, s1, name, intrabar=False):
        rows = []
        for sym in syms:
            df = frames(sym)
            win = df[(df.index >= s0) & (df.index <= s1)]
            if len(win) >= 100:
                tr = simulate_e(win, fn(df).loc[win.index], atr(win), intrabar=intrabar)
                rows.extend(trade_rows(sym, name, tr))
        return rows

    EX = [
        ("F-042 Donchian_High_20", lambda df: (df["close"] > df["high"].shift(1).rolling(20).max()).fillna(False)),
        ("F-055 MACD_Cross_Zero", lambda df: ((ind.compute_matrix(df)["macd"] > 0) & (ind.compute_matrix(df)["macd"].shift(1) <= 0)).fillna(False)),
        ("F-063 BB_Lower_Bounce", lambda df: ((df["low"] <= ind.compute_matrix(df)["bb_low"]) & (df["close"] > df["open"])).fillna(False)),
        ("F-001 RSI2_Snap os15", lambda df: E001.make_signals(df, rsi2_os=15, sma_trend=200, sma_pull=5)),
    ]

    for tag_e, intr in (("E1_دفاعية", False), ("E2_معايَرة", True)):
        print("=" * 78); print(f"الآلة {tag_e}"); print("=" * 78)
        bl = {}
        for tag, (s0, s1) in (("DEC", (DEC_S, DEC_E)), ("JUD", (JUD_S, JUD_E))):
            rows = []
            for sym in syms:                       # الأعمدة الثلاثة القديمة
                df = frames(sym)
                win = df[(df.index >= s0) & (df.index <= s1)]
                if len(win) < 100: continue
                for c in [x for x in cells if x["symbol"] == sym]:
                    if c["driver"] == "F_213_breakers":
                        sg = M213.make_signals(df, trigger=c["combo"]["trigger"]).loc[win.index]
                    else:
                        sg = R17.EXPS[c["driver"]].make_signals(df, **c["combo"]).loc[win.index]
                    tr = simulate_e(win, sg, atr(win), intrabar=intr)
                    for r in trade_rows(sym, c["driver"], tr):
                        r["driver"] = c["driver"]; rows.append(r)
            exr = []
            for nm, fn in EX:
                exr += run_e1(fn, s0, s1, nm, intr)
            bl[tag] = summarize(rows + exr)
            print(f"  الأساس (7 أعمدة) {tag}: {bl[tag]}")
        res = []
        for hid, name, fn in S.HYPOTHESES:
            rd = run_e1(fn, DEC_S, DEC_E, f"{hid} {name}", intr)
            sd = summarize(rd)
            gate = bool(sd["net"] > 0 and sd["pf"] >= 1.3 and sd["trades"] >= 30)
            sj = None
            if gate:
                sj = summarize(run_e1(fn, JUD_S, JUD_E, f"{hid} {name}", intr))
            res.append({"الرمز": hid, "الاسم": name, "القرار$": sd["net"], "صفقات_القرار": sd["trades"],
                        "PF_القرار": sd["pf"], "بوابة": "✓" if gate else "✗",
                        "الحكم$": (sj or {}).get("net"), "صفقات_الحكم": (sj or {}).get("trades")})
            print(f"  {hid} {name[:32]:32s} | قرار {sd['net']:>8.2f}$ ({sd['trades']:5d}) gate={'✓' if gate else '✗'}"
                  f" | حكم {(sj or {}).get('net')}")
        pd.DataFrame(res).to_csv(OUT / f"phase2_{tag_e}.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame([{"الفترة": k, **v} for k, v in bl.items()]).to_csv(
            OUT / f"basis_{tag_e}.csv", index=False, encoding="utf-8-sig")

    print(f"\n→ {OUT}\nالزمن {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
