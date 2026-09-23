# -*- coding: utf-8 -*-
"""L0027 — منحنى الكلفة: عند أي كلفة تنفيذ يموت كل عمود؟

القياس الحي (المسبار L0011) محجوز بإذن القائد وحده بحكم D-0042.
لكن السؤال الحاكم له وجه تاريخي **لم يُقَس قط**:

  لسنا بحاجة لمعرفة الكلفة الحية بالضبط كي نقرّر.
  يكفي أن نعرف **كم هامش الأمان**: عند أي كلفة يتوقف كل عمود عن الربح؟

هذا يقلب السؤال من «كم الكلفة؟» (يحتاج مالًا حيًّا) إلى
«كم نحتمل؟» (يُقاس من التاريخ الآن). والفرق بين الرقمين = هامش الأمان.

يُقاس أيضًا **سناب المؤشر القصير** المجمّد ظلمًا (حكم L0018 الحرفي: «يُطوّر»)
كي نعرف: هل يعود كعمود رابع، وعند أي كلفة؟

المخرج: كلفة الانهيار لكل عمود + هامش الأمان مقابل آخر كلفة مرصودة (0.123%).

⚠️ لا إعادة اختيار · المسطرة 20$ · 4h · شراء فقط · خروج الفائزة الموحّد.

    python3 history/hyp_lab/run_l0027_costcurve.py
"""
from __future__ import annotations
import json, os, pathlib, platform, subprocess, sys, time
import numpy as np, pandas as pd

_S = pathlib.Path(os.environ.get("NOVA_SCRATCH", "~/.nova_scratch")).expanduser()
os.environ.setdefault("NOVA_HOME", str(_S / "home"))
HIST = pathlib.Path(__file__).resolve().parents[1]; ROOT = HIST.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import common as C
from common import atr, simulate, trade_rows
import run_l0019_unified as R19
import run_l0017 as R17
import F_197_dual_trail as M197, F_213_breakers as M213

OUT = HIST / "research" / "hyp_lab_out" / "L0027"
TS, TE = "2025-01-01", "2026-08-31"; BAR = 4*3600
WIN = {"stop": 2.5, "trig": 0.0015, "lock": 0.0060}

# الكلفة الكلية للطرف = رسوم 0.10% + انزلاق. نُثبّت الرسوم ونحرّك الانزلاق.
FEE = 0.0010
SLIPS = [0.0000, 0.0003, 0.0010, 0.0015, 0.0020, 0.0025, 0.0030, 0.0040, 0.0050]
LAST_OBSERVED = 0.00123        # آخر كلفة مرصودة للطرف (0.123%) من سجل L0010

AR = {"F_213_breakers": "كاسرة النطاق", "F_192_ext_entry": "انحراف الدخول",
      "F_165_score_entry": "التنقيط التعويضي", "F_001_rsi2_snap": "سناب المؤشر القصير"}


def frozen_cells():
    """خلايا سناب المؤشر التي عبرت بوابة L0017 — مجمّدة لا مدفونة."""
    f = HIST/"research"/"hyp_lab_out"/"L0017-tf4h"/"F_001_rsi2_snap"/"all_symbols_test.csv"
    if not f.exists():
        return []
    t = pd.read_csv(f, encoding="utf-8-sig"); cells = []
    keys = list(R17.EXPS["F_001_rsi2_snap"].SWEEP_PARAMS.keys())
    for _, r in t[t["gate"] == True].iterrows():          # noqa: E712
        combo = {}
        for k in keys:
            ref = R17.EXPS["F_001_rsi2_snap"].SWEEP_PARAMS[k][0]
            v = r[f"sel_NOVA_{k.upper()}"]
            combo[k] = int(v) if isinstance(ref, int) else float(v)
        cells.append({"driver": "F_001_rsi2_snap", "symbol": r["symbol"], "combo": combo})
    return cells


def run_at(cells, slip):
    old_s, old_st = C.SLIP_PER_SIDE, C.STOP_ATR
    C.SLIP_PER_SIDE = slip; C.STOP_ATR = WIN["stop"]
    C.COST_PER_SIDE = FEE + slip
    rows = []
    try:
        for s in sorted({c["symbol"] for c in cells}):
            df = R19.frame(s); win = df[(df.index >= TS) & (df.index <= TE)]
            a_s = atr(win)
            for c in [x for x in cells if x["symbol"] == s]:
                if c["driver"] == "F_213_breakers":
                    sig = M213.make_signals(df, trigger=c["combo"]["trigger"]).loc[win.index]
                    if c["combo"]["exit"] == "dual":
                        kw = {"exit_mode": "dual",
                              "dual": {**M213.make_dual_spec(), "trig": WIN["trig"], "lock": WIN["lock"]}}
                    else:
                        kw = {"exit_mode": "std"}
                else:
                    sig = R17.EXPS[c["driver"]].make_signals(df, **c["combo"]).loc[win.index]
                    kw = {"exit_mode": "dual",
                          "dual": {**M197.make_dual_spec(), "trig": WIN["trig"], "lock": WIN["lock"]}}
                _, tr = simulate(win, sig, a_s, notional=C.TRADE_USD, bar_secs=BAR, **kw)
                rows.extend(trade_rows(c["symbol"], c["driver"], tr))
            del df
    finally:
        C.SLIP_PER_SIDE = old_s; C.STOP_ATR = old_st
        C.COST_PER_SIDE = FEE + old_s
    return pd.DataFrame(rows)


def breakeven(xs, ys):
    """أول كلفة يصير عندها الصافي ≤ 0، بتقريب خطي بين نقطتي القياس."""
    for i in range(1, len(ys)):
        if ys[i] <= 0 < ys[i-1]:
            x0, x1, y0, y1 = xs[i-1], xs[i], ys[i-1], ys[i]
            return x0 + (x1-x0) * y0/(y0-y1)
    return None


def main():
    t0 = time.time()
    can = subprocess.run([sys.executable, str(ROOT/"tools"/"canary.py"), "--json"],
                         capture_output=True, text=True)
    cj = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
    if cj.get("canary") != "ok":
        print("الكاناري فشل — إيقاف.", file=sys.stderr); return 1
    print(f"الكاناري: PASS (net={cj['got']['net']})\n", flush=True)
    OUT.mkdir(parents=True, exist_ok=True); pd.set_option("display.width", 250)

    live = R19.breaker_cells() + R19.new_cells()
    froz = frozen_cells()
    cells = live + froz
    print(f"أعمدة عاملة: {len(live)} خلية · سناب المؤشر المجمّد: {len(froz)} خلية\n", flush=True)

    recs = {}
    for sl in SLIPS:
        d = run_at(cells, sl)
        per = {AR.get(k, k): round(float(g["pnl"].sum()), 2) for k, g in d.groupby("exp")}
        act = d[d["exp"] != "F_001_rsi2_snap"]
        per["— الأعمدة العاملة —"] = round(float(act["pnl"].sum()), 2)
        recs[sl] = per
        print(f"  انزلاق {sl*100:.2f}% ⇒ العاملة {per['— الأعمدة العاملة —']:>9.2f}$ "
              f"· سناب {per.get('سناب المؤشر القصير', 0):>7.2f}$", flush=True)

    cols = ["كاسرة النطاق", "انحراف الدخول", "التنقيط التعويضي",
            "— الأعمدة العاملة —", "سناب المؤشر القصير"]
    tbl = pd.DataFrame(
        [{"انزلاق للطرف%": round(sl*100, 3), "الكلفة الكلية للطرف%": round((FEE+sl)*100, 3),
          **{c: recs[sl].get(c, 0.0) for c in cols}} for sl in SLIPS])
    tbl.to_csv(OUT/"cost_curve_4h.csv", index=False, encoding="utf-8-sig")

    print("\n"+"="*135)
    print("منحنى الكلفة — صافي كل عمود بالدولار عند كل مستوى كلفة · 4h · مسطرة 20$")
    print("="*135)
    print(tbl.to_string(index=False), flush=True)

    tot = [(FEE+s) for s in SLIPS]
    print("\n=== كلفة الانهيار وهامش الأمان ===")
    be_rows = []
    for c in cols:
        ys = [recs[s].get(c, 0.0) for s in SLIPS]
        be = breakeven(tot, ys)
        be_rows.append({
            "العمود": c,
            "صافي عند الكلفة المرصودة$": round(float(np.interp(LAST_OBSERVED, tot, ys)), 2),
            "كلفة الانهيار للطرف%": round(be*100, 3) if be else "أعلى من 0.60",
            "هامش الأمان (ضعف)": round(be/LAST_OBSERVED, 2) if be else "—"})
    be_df = pd.DataFrame(be_rows)
    be_df.to_csv(OUT/"breakeven_4h.csv", index=False, encoding="utf-8-sig")
    print(be_df.to_string(index=False), flush=True)
    print(f"\n(الكلفة المرصودة سابقًا = {LAST_OBSERVED*100:.3f}% للطرف)")

    (OUT/"env_dump.txt").write_text(
        f"python={platform.python_version()}\npandas={pd.__version__}\nnumpy={np.__version__}\n"
        f"canary={cj['got']['net']}\nnotional={C.TRADE_USD}$\nwindow={TS}→{TE}\n"
        f"fee={FEE}\nslips={SLIPS}\nlast_observed={LAST_OBSERVED}\n"
        f"exit={WIN}\ncells_live={len(live)} cells_frozen={len(froz)}\n", encoding="utf-8")
    print(f"\n→ {OUT}\n{time.time()-t0:.1f} ث", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
