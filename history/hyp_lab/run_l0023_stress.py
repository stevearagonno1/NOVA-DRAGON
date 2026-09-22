# -*- coding: utf-8 -*-
"""L0023 — ضغط تركيبة الخروج الفائزة (وقف 2.5 · تسليح 0.0015 · قفل 0.0060).

الشرطان المكتوبان في تقرير L0022 قبل أي كلمة «نعتمد»:
  1) الانزلاق المجهد: هل تبقى موجبة حين يسوء التنفيذ؟ (0.03% أساس · 0.10% · 0.30%)
  2) جوار ±20% على المحاور الثلاثة: هل هي هضبة أم قمة حادة؟

نقارن دائمًا بالأساس (وقف 2.0 · تسليح 0.0025 · قفل 0.0045) تحت نفس الضغط —
فالسؤال ليس «هل تنجو» بل «هل تبقى أفضل من الذي عندنا».

⚠️ لا إعادة اختيار ولا تحريك محاور بحثًا عن نجاح (القسم 27 بند 6).
⚠️ المسطرة 20$ للصفقة ثابتة.

    python3 history/hyp_lab/run_l0023_stress.py
"""
from __future__ import annotations
import json, os, pathlib, platform, subprocess, sys, time, itertools
import numpy as np, pandas as pd

_S = pathlib.Path(os.environ.get("NOVA_SCRATCH", "~/.nova_scratch")).expanduser()
os.environ.setdefault("NOVA_HOME", str(_S / "home"))
HIST = pathlib.Path(__file__).resolve().parents[1]; ROOT = HIST.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import common as C
from common import atr, simulate, trade_rows
from measure_l0010_gate import drawdown_stats, psr_dsr
import run_l0019_unified as R19

OUT = HIST / "research" / "hyp_lab_out" / "L0023"
TS, TE = "2025-01-01", "2026-08-31"; BAR = 4*3600
YEARS = (pd.Timestamp(TE,tz="UTC")-pd.Timestamp(TS,tz="UTC")).days/365.25

BASE = ("الأساس", 2.0, 0.0025, 0.0045)
WIN  = ("الفائزة", 2.5, 0.0015, 0.0060)
SLIPS = [0.0003, 0.0010, 0.0030]     # الانزلاق لكل جهة

def pf(p):
    g,l = p[p>0].sum(), -p[p<0].sum()
    return float(g/l) if l>0 else (np.inf if g>0 else 0.0)

def run_cell(c, df, stop_atr, trig, lock):
    win = df[(df.index>=TS)&(df.index<=TE)]
    old = C.STOP_ATR; C.STOP_ATR = stop_atr
    try:
        if c["driver"] == "F_213_breakers":
            import F_213_breakers as M
            sig = M.make_signals(df, trigger=c["combo"]["trigger"]).loc[win.index]
            kw = ({"exit_mode":"dual","dual":{**M.make_dual_spec(),"trig":trig,"lock":lock}}
                  if c["combo"]["exit"]=="dual" else {"exit_mode":"std"})
        else:
            import F_197_dual_trail as M197, run_l0017 as R17
            sig = R17.EXPS[c["driver"]].make_signals(df, **c["combo"]).loc[win.index]
            kw = {"exit_mode":"dual","dual":M197.make_dual_spec(trig=trig, lock=lock)}
        _, tr = simulate(win, sig, atr(win), notional=C.TRADE_USD, bar_secs=BAR, **kw)
    finally:
        C.STOP_ATR = old
    return trade_rows(c["symbol"], c["driver"], tr)

def stat(name, rows, nt=720):
    d = pd.DataFrame(rows)
    if d.empty: return {"التركيبة":name,"صفقات":0,"صافي$":0.0}
    d["exit_time"]=pd.to_datetime(d["exit_time"],utc=True); d=d.sort_values("exit_time")
    p = d["pnl"].to_numpy(float); dd,dys,_ = drawdown_stats(d["exit_time"],p)
    day = d.groupby(d["exit_time"].dt.date)["pnl"].sum()
    return {"التركيبة":name,"صفقات":len(d),"صافي$":round(float(p.sum()),2),
            "عامل الربح":round(pf(p),4),"فوز%":round(100*float((p>0).mean()),2),
            "أقصى هبوط$":round(dd,2),"أسوأ يوم$":round(float(day.min()),2),
            "DSR":psr_dsr(p,YEARS,nt)["dsr"]}

def main():
    t0=time.time()
    can = subprocess.run([sys.executable, str(ROOT/"tools"/"canary.py"), "--json"],
                         capture_output=True, text=True)
    cj = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
    if cj.get("canary")!="ok":
        print("الكاناري فشل — إيقاف L0023.", file=sys.stderr); return 1
    print(f"الكاناري: PASS (net={cj['got']['net']})\n", flush=True)
    OUT.mkdir(parents=True, exist_ok=True); pd.set_option("display.width",250)

    cells = R19.breaker_cells() + R19.new_cells()
    syms = sorted({c["symbol"] for c in cells})
    print(f"خلايا: {len(cells)} على {len(syms)} عملة\n", flush=True)

    # ===== المحور 1: الانزلاق المجهد =====
    slip_rows=[]
    for slip in SLIPS:
        old_s, old_c = C.SLIP_PER_SIDE, C.COST_PER_SIDE
        C.SLIP_PER_SIDE = slip; C.COST_PER_SIDE = C.FEE_PER_SIDE + slip
        try:
            for nm, st, tg, lk in (BASE, WIN):
                acc=[]
                for s in syms:
                    df = R19.frame(s)
                    for c in [x for x in cells if x["symbol"]==s]:
                        acc.extend(run_cell(c, df, st, tg, lk))
                    del df
                r = stat(f"{nm} @ انزلاق {slip*100:.2f}%", acc)
                r["الانزلاق%"]=round(slip*100,2); r["أي تركيبة"]=nm
                slip_rows.append(r)
                print(f"  انزلاق {slip*100:.2f}% · {nm}: {r['صافي$']}$", flush=True)
        finally:
            C.SLIP_PER_SIDE, C.COST_PER_SIDE = old_s, old_c
    sd = pd.DataFrame(slip_rows)
    sd.to_csv(OUT/"slip_4h.csv", index=False, encoding="utf-8-sig")
    print("\n— الانزلاق المجهد —")
    print(sd[["التركيبة","صفقات","صافي$","عامل الربح","أقصى هبوط$","أسوأ يوم$"]].to_string(index=False), flush=True)

    # ===== المحور 2: الجوار ±20% حول الفائزة =====
    _, WS, WT, WL = WIN
    grid=[]
    for fs, ft, fl in itertools.product([0.8,1.0,1.2], repeat=3):
        st, tg, lk = round(WS*fs,4), round(WT*ft,6), round(WL*fl,6)
        acc=[]
        for s in syms:
            df = R19.frame(s)
            for c in [x for x in cells if x["symbol"]==s]:
                acc.extend(run_cell(c, df, st, tg, lk))
            del df
        r = stat(f"وقف {st} · تسليح {tg} · قفل {lk}", acc)
        r.update({"وقف":st,"تسليح":tg,"قفل":lk,
                  "هو المركز": (fs==1.0 and ft==1.0 and fl==1.0)})
        grid.append(r)
        print(f"  جوار {st}/{tg}/{lk}: {r['صافي$']}$", flush=True)
    gd = pd.DataFrame(grid)
    gd.to_csv(OUT/"plateau_4h.csv", index=False, encoding="utf-8-sig")
    pos = int((gd["صافي$"]>0).sum())
    center = float(gd[gd["هو المركز"]]["صافي$"].iloc[0])
    base_net = 1578.37
    above = int((gd["صافي$"]>base_net).sum())
    print(f"\n— الجوار ±20% ({len(gd)} جار) —")
    print(f"موجب: {pos}/{len(gd)} · فوق الأساس ({base_net}$): {above}/{len(gd)}")
    print(f"المركز: {center}$ · الأدنى: {gd['صافي$'].min()}$ · الأعلى: {gd['صافي$'].max()}$", flush=True)

    (OUT/"env_dump.txt").write_text(
        f"python={platform.python_version()}\npandas={pd.__version__}\nnumpy={np.__version__}\n"
        f"canary={cj['got']['net']}\nnotional={C.TRADE_USD}$\nwindow={TS}→{TE}\n"
        f"base=stop2.0/trig0.0025/lock0.0045\nwinner=stop2.5/trig0.0015/lock0.0060\n"
        f"slips={SLIPS}\nplateau=3^3=27 جار ±20%\ncells={len(cells)} symbols={len(syms)}\n",
        encoding="utf-8")
    print(f"\n→ {OUT}\n{time.time()-t0:.1f} ث", flush=True); return 0

if __name__ == "__main__": raise SystemExit(main())
