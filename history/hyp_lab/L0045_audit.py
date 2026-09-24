# -*- coding: utf-8 -*-
"""L0045 — تدقيق آلة التنفيذ + طبقة دفاعية (تنفيذ ممكن فقط).

المشكلة المقيسة: في common.simulate، عند تفعيل «قفل الربح» lock=0.0060 (+0.60%) مع
تسليح مبكر trig=0.0015 (+0.15%)، يصبح سعر الخروج (الوقف الفعّال) أعلى من السوق،
والآلة تبيع عند هذا السعر لأن شرط الخروج هو (low ≤ eff) — وهو شرط يتحقق أيضاً حين
يكون السوق كله تحت eff. النتيجة: صفقات تُغلق بسعر لم يلمسه السوق قط.

التدقيق: نسبة الصفقات التي سعر خروجها > أعلى سعر في كل نافذة الصفقة [entry_j..exit_j].
الطبقة الدفاعية: نفس المحرك بقاعدة تعبئة واحدة مختلفة: fill = min(eff, open[j]).
هذه ليست فرضية جديدة ولا انتقاء — بل معايرة آلة (خارج سقف انتقاء الفرضيات، مُعلَنة صراحة).
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

OUT = HIST / "research" / "hyp_lab_out" / "L0045"
AUD = OUT / "audit"; AUD.mkdir(parents=True, exist_ok=True)
CACHE = ROOT / ".cache" / "l0045_frames"
DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
BAR = 4 * 3600
WIN = {"stop": 2.5, "trig": 0.0015, "lock": 0.0060}
_FR = {}
def frames(sym):
    if sym not in _FR:
        _FR[sym] = pd.read_parquet(CACHE / f"{sym}_4h.parquet")
    return _FR[sym]


def simulate_fixed(df, sig, atr_s, dual=None, notional=C.TRADE_USD, bar_secs=BAR):
    """نسخة common.simulate (exit_mode='dual') بقاعدة تعبئة واحدة: fill = min(eff, open[j])."""
    o = df["open"].to_numpy(); h = df["high"].to_numpy()
    l = df["low"].to_numpy(); c = df["close"].to_numpy()
    a = atr_s.to_numpy(); n = len(df); idx = df.index
    sig_i = np.flatnonzero(sig.to_numpy())
    if sig_i.size == 0:
        return []
    STOP_ATR = C.STOP_ATR; COST = C.COST_PER_SIDE
    trades = []

    def close_at(p, j, price, side):
        eff_fill = min(price, o[j])                      # ← التصحيح الوحيد
        fill = eff_fill * (1 - COST)
        qty = p["notional"] / p["entry"]
        p["pnl"] = qty * (fill - p["entry"]) if qty * (fill - p["entry"]) or True else 0.0
        p["exit_fill"] = fill; p["exit_j"] = j; p["exit_time"] = idx[j]
        p["exit_side"] = side; p["done"] = True

    def open_(i):
        e = i + 1
        if e >= n or not np.isfinite(a[i]):
            return None
        ef = o[e] * (1 + COST)
        return {"entry_j": e, "entry": ef, "entry_time": idx[e], "notional": notional, "risk": None,
                "hard_stop": ef - STOP_ATR * a[i], "peak": o[e], "done": False, "pnl": 0.0,
                "idx": idx, "trig": dual["trig"], "lock": dual["lock"],
                "wide": dual["wide"], "tight": dual["tight"]}

    def step(p, j):
        eff = p["hard_stop"]
        peak = p["peak"]; gain = (peak - p["entry"]) / p["entry"]
        if gain >= p["trig"]:
            trail = p["wide"] if gain <= 0.01 else p["tight"]
            eff = max(eff, p["entry"] * (1 + p["lock"]), peak * (1 - trail))
        if l[j] <= eff:
            close_at(p, j, eff, "stop"); return True
        p["peak"] = max(p["peak"], h[j])
        return False

    pos = None
    for i in sig_i:
        if pos is not None:
            j = pos["entry_j"]
            while j < n and not step(pos, j):
                j += 1
            if not pos["done"]:
                close_at(pos, n - 1, c[-1], "eod")
            trades.append(pos)
            if pos["exit_j"] > i:
                pos = None; continue
            pos = None
        p = open_(i)
        if p is None:
            continue
        pos = p
    if pos is not None:
        j = pos["entry_j"]
        while j < n and not step(pos, j):
            j += 1
        if not pos["done"]:
            close_at(pos, n - 1, c[-1], "eod")
        trades.append(pos)
    return trades


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
    subprocess.run([sys.executable, str(ROOT / "tools" / "canary.py"), "--json"], capture_output=True)
    L36.set_core(); NC.EMA_FAST = 8; M213._cache.clear(); C.STOP_ATR = WIN["stop"]
    cells = R19.breaker_cells() + R19.new_cells()
    syms = sorted({c["symbol"] for c in cells})
    kw_col = {"dual": {**M197.make_dual_spec(), "trig": WIN["trig"], "lock": WIN["lock"]}}

    # ─── 1) تدقيق التنفيذ على المحرك الحالي ───
    print("=" * 78); print("1) تدقيق التنفيذ — المحرك الحالي (common.simulate)"); print("=" * 78)
    from common import simulate
    aud = []
    for sym in syms:
        df = frames(sym)
        win = df[(df.index >= JUD_S) & (df.index <= JUD_E)]
        h = win["high"].to_numpy(); l = win["low"].to_numpy()
        for c in [x for x in cells if x["symbol"] == sym]:
            if c["driver"] == "F_213_breakers":
                sg = M213.make_signals(df, trigger=c["combo"]["trigger"]).loc[win.index]
            else:
                sg = R17.EXPS[c["driver"]].make_signals(df, **c["combo"]).loc[win.index]
            _, tr = simulate(win, sg, atr(win), notional=C.TRADE_USD, bar_secs=BAR,
                             exit_mode="dual", **kw_col)
            for p in tr:
                j = p["exit_j"]; eff = p["exit_fill"] / (1 - C.COST_PER_SIDE)
                hi = float(h[p["entry_j"]:j + 1].max())
                aud.append({"symbol": sym, "driver": c["driver"], "pnl": p["pnl"],
                            "never_traded": bool(eff > hi + 1e-12),
                            "above_bar_high": bool(eff > float(h[j]) + 1e-12),
                            "at_lock": bool(abs((eff - p["entry"]) / p["entry"] - WIN["lock"]) < 1e-9)})
    A = pd.DataFrame(aud)
    tot = len(A); fant = int(A["never_traded"].sum()); above = int(A["above_bar_high"].sum())
    locks = int(A["at_lock"].sum())
    pnl_fant = round(float(A.loc[A["never_traded"], "pnl"].sum()), 2)
    pnl_all = round(float(A["pnl"].sum()), 2)
    print(f"  صفقات الأساس في فترة الحكم: {tot}")
    print(f"  خروج بسعر فوق أعلى سعر لشمعة الخروج : {above} ({100*above/tot:.1f}%)")
    print(f"  خروج بسعر لم يُلمس أبداً في نافذة الصفقة: {fant} ({100*fant/tot:.1f}%)  ← تنفيذ مستحيل")
    print(f"  خروج عند قفل الربح +0.60% بالضبط     : {locks} ({100*locks/tot:.1f}%)")
    print(f"  صافي الأساس كما تقيسه الآلة: {pnl_all}$ · ومنه {pnl_fant}$ في صفقات تنفيذها مستحيل")
    A.to_csv(AUD / "fill_audit_base_judgement.csv", index=False, encoding="utf-8-sig")

    # ─── 2) الطبقة الدفاعية: إعادة القياس بقاعدة تنفيذ ممكنة ───
    print("\n" + "=" * 78); print("2) الطبقة الدفاعية — fill = min(eff, open)"); print("=" * 78)

    def sim_fixed(sig_fn, s0, s1, name):
        rows = []
        for sym in syms:
            df = frames(sym)
            win = df[(df.index >= s0) & (df.index <= s1)]
            if len(win) >= 100:
                tr = simulate_fixed(win, sig_fn(df).loc[win.index], atr(win), notional=C.TRADE_USD, **kw_col)
                rows.extend(trade_rows(sym, name, tr))
        return rows

    base = {"DEC": None, "JUD": None}
    for tag, (s0, s1) in (("DEC", (DEC_S, DEC_E)), ("JUD", (JUD_S, JUD_E))):
        _, d = L36.run(cells, s0, s1)          # الأساس القديم: آلة المحرك كما هي
        base[tag] = d.to_dict("records")

    # الأساس بالأعمدة الثلاثة عبر الآلة المصححة: نعيد تنفيذ خلاياها بالقاعدة المصححة
    rows3 = {"DEC": [], "JUD": []}
    for tag, (s0, s1) in (("DEC", (DEC_S, DEC_E)), ("JUD", (JUD_S, JUD_E))):
        for sym in syms:
            df = frames(sym)
            win = df[(df.index >= s0) & (df.index <= s1)]
            if len(win) < 100: continue
            for c in [x for x in cells if x["symbol"] == sym]:
                if c["driver"] == "F_213_breakers":
                    sg = M213.make_signals(df, trigger=c["combo"]["trigger"]).loc[win.index]
                else:
                    sg = R17.EXPS[c["driver"]].make_signals(df, **c["combo"]).loc[win.index]
                tr = simulate_fixed(win, sg, atr(win), notional=C.TRADE_USD, **kw_col)
                for r in trade_rows(sym, c["driver"], tr):
                    r["driver"] = c["driver"]; rows3[tag].append(r)

    EX = [
        ("F-042 Donchian_High_20", lambda df: (df["close"] > df["high"].shift(1).rolling(20).max()).fillna(False)),
        ("F-055 MACD_Cross_Zero", lambda df: ((ind.compute_matrix(df)["macd"] > 0) & (ind.compute_matrix(df)["macd"].shift(1) <= 0)).fillna(False)),
        ("F-063 BB_Lower_Bounce", lambda df: ((df["low"] <= ind.compute_matrix(df)["bb_low"]) & (df["close"] > df["open"])).fillna(False)),
        ("F-001 RSI2_Snap os15", lambda df: E001.make_signals(df, rsi2_os=15, sma_trend=200, sma_pull=5)),
    ]
    for nm, fn in EX:
        for tag, (s0, s1) in (("DEC", (DEC_S, DEC_E)), ("JUD", (JUD_S, JUD_E))):
            rows3[tag] += sim_fixed(fn, s0, s1, nm)

    basis_fix = {t: summarize(rows3[t]) for t in ("DEC", "JUD")}
    print(f"  الأساس الدفاعي (7 أعمدة): قرار={basis_fix['DEC']} | حكم={basis_fix['JUD']}")

    # الفرضيات العشر
    dec_rows, res = {}, []
    for hid, name, fn in S.HYPOTHESES:
        r = sim_fixed(fn, DEC_S, DEC_E, f"{hid} {name}")
        s = summarize(r)
        gate = bool(s["net"] > 0 and s["pf"] >= 1.3 and s["trades"] >= 30)
        res.append({"الرمز": hid, "الاسم": name, "fn": fn, "d": s, "gate": gate, "rows_dec": r})
        print(f"  {hid} {name[:34]:34s} دفاعي/قرار: {s['net']:>8.2f}$ ({s['trades']:5d} ص, PF={s['pf']:.3f}) "
              f"| بوابة: {'✓' if gate else '✗'}")
    res.sort(key=lambda x: x["d"]["net"], reverse=True)
    for it in res:
        if not it["gate"]:
            it["j"] = None; continue
        r = sim_fixed(it["fn"], JUD_S, JUD_E, f"{it['hid']} {it['name']}")
        it["rows_jud"] = r; it["j"] = summarize(r)
        print(f"    ↳ {it['hid']} دفاعي/حكم: {it['j']}")
    out2 = [{"الترتيب": i, "الرمز": it["hid"], "الاسم": it["name"],
             "صافي_القرار$": it["d"]["net"], "صفقات_القرار": it["d"]["trades"], "PF_القرار": it["d"]["pf"],
             "بوابة": "✓" if it["gate"] else "✗",
             "صافي_الحكم$": (it["j"] or {}).get("net"), "صفقات_الحكم": (it["j"] or {}).get("trades")}
            for i, it in enumerate(res, 1)]
    pd.DataFrame(out2).to_csv(AUD / "defensive_phase2_ranked.csv", index=False, encoding="utf-8-sig")

    # التراكم الدفاعي
    passers = [x for x in res if x["gate"] and x.get("j")]
    acc, prev = [], basis_fix["JUD"]["net"]
    acc.append({"التركيب": "الأساس الدفاعي (7 أعمدة)", **basis_fix["JUD"], "مضاف$": 0.0})
    cur = list(rows3["JUD"])
    for i, it in enumerate(passers[:5], 1):
        cur = cur + it["rows_jud"]
        s = summarize(cur)
        acc.append({"التركيب": f"+{i} {it['hid']}", **s, "مضاف$": round(s["net"] - prev, 2)})
        print(f"  +{i} {it['hid']:6s} دفاعي: {s['net']:>8.2f}$ | هبوط={s['mdd']:>6.2f}$ | مضاف={s['net']-prev:>+8.2f}$")
        prev = s["net"]
    pd.DataFrame(acc).to_csv(AUD / "defensive_phase3_accumulation.csv", index=False, encoding="utf-8-sig")

    # فحوص الفائز الدفاعي
    if passers:
        w = passers[0]
        print(f"\n  الفائز الدفاعي: {w['hid']} {w['name']}")
        nb = []
        for lb in (5, 8, 12):
            s = summarize(sim_fixed(lambda d, _l=lb: w["fn"](d, lookback=_l), JUD_S, JUD_E, "nb"))
            nb.append({"الإعداد": f"lookback={lb}", **s, "رابح": s["net"] > 0})
            print(f"    جوار دفاعي lookback={lb}: {s}")
        pd.DataFrame(nb).to_csv(AUD / "defensive_neighborhood.csv", index=False, encoding="utf-8-sig")
        st = []
        for tot, f_s, s_s, lbl in [(0.0020, 0.0015, 0.0005, "0.20%"), (0.0030, 0.0023, 0.0007, "0.30%"),
                                   (0.0040, 0.0030, 0.0010, "0.40%")]:
            of, osl, oc = C.FEE_PER_SIDE, C.SLIP_PER_SIDE, C.COST_PER_SIDE
            C.FEE_PER_SIDE, C.SLIP_PER_SIDE, C.COST_PER_SIDE = f_s, s_s, f_s + s_s
            try:
                s = summarize(sim_fixed(w["fn"], JUD_S, JUD_E, "st"))
            finally:
                C.FEE_PER_SIDE, C.SLIP_PER_SIDE, C.COST_PER_SIDE = of, osl, oc
            st.append({"كلفة_الطرف": lbl, **s, "صامد": s["net"] > 0})
            print(f"    إجهاد دفاعي {lbl}: {s}")
        pd.DataFrame(st).to_csv(AUD / "defensive_winner_stress.csv", index=False, encoding="utf-8-sig")

    summ = (f"audit_trades={tot}\nfantasy_fills={fant} ({100*fant/tot:.1f}%)\n"
            f"above_bar_high={above} ({100*above/tot:.1f}%)\nat_lock={locks} ({100*locks/tot:.1f}%)\n"
            f"net_current_engine_base_jud={pnl_all}\nnet_in_fantasy_trades={pnl_fant}\n")
    (AUD / "audit_summary.txt").write_text(summ, encoding="utf-8")
    print(f"\n→ {AUD}\nالزمن: {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
