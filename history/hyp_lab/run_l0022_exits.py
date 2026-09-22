# -*- coding: utf-8 -*-
"""L0022 — صندوق الخروج: علاج «الخاسرة ثلاثة أضعاف الرابحة».

الخلل المقيس: المحفظة تربح 89.75% من صفقاتها، لكن متوسط الخاسرة −0.9047$
مقابل رابحة 0.2703$ ⇒ نسبة العائد 0.2989. الربح يأتي من الكثرة لا من الحجم،
وصفقة خاسرة واحدة تمحو ثلاث رابحات. جولتا الفلاتر والحصة أثبتتا أن الخلل
**ليس في الدخول**، فالعلاج في الخروج.

محاور الخروج في الآلة الحالية (لا اختراع — ما تدعمه `simulate` حرفًا):
  1) الوقف القاسي `STOP_ATR` (حاليًا 2.0 × المدى الحقيقي) — هو سقف الخسارة الواحدة.
  2) عتبة التسليح `trig` — متى يبدأ المتتبّع بحماية الربح.
  3) القفل `lock` — كم ربحًا يُضمن بعد التسليح.

الفرضية: وقف أضيق يقلّص الخاسرة الكبيرة. والثمن المحتمل أن يقطع رابحات
مبكرًا. القياس يحكم بالدولار.

⚠️ لا إعادة اختيار: إعدادات الدخول مقفلة من إيداعاتها. المتغيّر الخروج وحده.
⚠️ المسطرة 20$ للصفقة (القسم 27) ثابتة في كل الخلايا.

    python3 history/hyp_lab/run_l0022_exits.py
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
from measure_l0010_gate import drawdown_stats, longest_losing_streak, psr_dsr
import run_l0019_unified as R19

OUT = HIST / "research" / "hyp_lab_out" / "L0022"
TS, TE = "2025-01-01", "2026-08-31"; BAR = 4*3600
YEARS = (pd.Timestamp(TE, tz="UTC") - pd.Timestamp(TS, tz="UTC")).days / 365.25

# (اسم · الوقف القاسي بمضاعف المدى · عتبة التسليح · القفل)
# القيم الأساسية: stop=2.0 · trig=0.0025 · lock=0.0045 (إيداع المحفظة)
VARIANTS = [
    ("الأساس (كما هي)",            2.0,  0.0025, 0.0045),
    ("وقف أضيق 1.5",               1.5,  0.0025, 0.0045),
    ("وقف أضيق 1.0",               1.0,  0.0025, 0.0045),
    ("وقف أضيق 0.75",              0.75, 0.0025, 0.0045),
    ("وقف أوسع 2.5",               2.5,  0.0025, 0.0045),
    ("تسليح أبكر 0.0015",          2.0,  0.0015, 0.0045),
    ("تسليح أبطأ 0.0040",          2.0,  0.0040, 0.0045),
    ("قفل أعلى 0.0060",            2.0,  0.0025, 0.0060),
    ("قفل أدنى 0.0025",            2.0,  0.0025, 0.0025),
    ("وقف 1.0 + تسليح أبكر",       1.0,  0.0015, 0.0045),
    ("وقف 1.5 + قفل أعلى",         1.5,  0.0025, 0.0060),
    ("تسليح أبكر + قفل أعلى",      2.0,  0.0015, 0.0060),
    ("تسليح أبكر + وقف أوسع",      2.5,  0.0015, 0.0045),
    ("الثلاثة معًا",                2.5,  0.0015, 0.0060),
    ("تسليح 0.0010",               2.0,  0.0010, 0.0045),
    ("قفل 0.0075",                 2.0,  0.0025, 0.0075),
]

def pf(p):
    g, l = p[p>0].sum(), -p[p<0].sum()
    return float(g/l) if l>0 else (np.inf if g>0 else 0.0)

def run_cell(c, df, stop_atr, trig, lock):
    win = df[(df.index>=TS)&(df.index<=TE)]
    old = C.STOP_ATR
    C.STOP_ATR = stop_atr                      # الوقف القاسي محور الجولة
    try:
        if c["driver"] == "F_213_breakers":
            import F_213_breakers as M
            sig = M.make_signals(df, trigger=c["combo"]["trigger"]).loc[win.index]
            if c["combo"]["exit"] == "dual":
                spec = M.make_dual_spec(); spec = {**spec, "trig": trig, "lock": lock}
                kw = {"exit_mode": "dual", "dual": spec}
            else:
                kw = {"exit_mode": "std"}      # لا متتبّع: الوقف والهدف فقط
        else:
            import F_197_dual_trail as M197, run_l0017 as R17
            sig = R17.EXPS[c["driver"]].make_signals(df, **c["combo"]).loc[win.index]
            kw = {"exit_mode": "dual", "dual": M197.make_dual_spec(trig=trig, lock=lock)}
        _, tr = simulate(win, sig, atr(win), notional=C.TRADE_USD, bar_secs=BAR, **kw)
    finally:
        C.STOP_ATR = old
    rows = trade_rows(c["symbol"], c["driver"], tr)
    for r in rows: r["driver"] = c["driver"]
    return rows

def block(name, d, nt):
    if d.empty: return {"التركيبة": name, "صفقات": 0, "صافي$": 0.0}
    d = d.copy(); d["exit_time"] = pd.to_datetime(d["exit_time"], utc=True)
    d = d.sort_values("exit_time"); p = d["pnl"].to_numpy(float)
    dd, dys, _ = drawdown_stats(d["exit_time"], p)
    day = d.groupby(d["exit_time"].dt.date)["pnl"].sum(); z = psr_dsr(p, YEARS, nt)
    w, l = p[p>0], p[p<0]
    return {"التركيبة": name, "صفقات": len(d), "صافي$": round(float(p.sum()),2),
        "عامل الربح": round(pf(p),4), "فوز%": round(100*float((p>0).mean()),2),
        "متوسط الرابحة$": round(float(w.mean()),4) if len(w) else 0.0,
        "متوسط الخاسرة$": round(float(l.mean()),4) if len(l) else 0.0,
        "نسبة العائد": round(float(w.mean()/abs(l.mean())),4) if len(l) and len(w) else 0.0,
        "أسوأ صفقة$": round(float(p.min()),2),
        "أقصى هبوط$": round(dd,2), "مدة الهبوط(يوم)": round(dys,1),
        "أسوأ يوم$": round(float(day.min()),2),
        "أطول سلسلة خسائر": longest_losing_streak(p),
        "DSR": z["dsr"], "z": z["dsr_z"]}

def main():
    t0 = time.time()
    can = subprocess.run([sys.executable, str(ROOT/"tools"/"canary.py"), "--json"],
                         capture_output=True, text=True)
    cj = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
    if cj.get("canary") != "ok":
        print("الكاناري فشل — إيقاف L0022.", file=sys.stderr); return 1
    print(f"الكاناري: PASS (net={cj['got']['net']})\n", flush=True)
    OUT.mkdir(parents=True, exist_ok=True); pd.set_option("display.width", 250)

    cells = R19.breaker_cells() + R19.new_cells()
    syms = sorted({c["symbol"] for c in cells})
    print(f"خلايا: {len(cells)} على {len(syms)} عملة · تركيبات خروج: {len(VARIANTS)}\n", flush=True)

    store = {v[0]: [] for v in VARIANTS}
    for s in syms:
        df = R19.frame(s); mine = [x for x in cells if x["symbol"]==s]
        for vn, st, tg, lk in VARIANTS:
            for c in mine: store[vn].extend(run_cell(c, df, st, tg, lk))
        print(f"  {s}: تمّت {len(VARIANTS)} تركيبة", flush=True); del df

    nt = 32*13 + (36+27)*8
    rows = [block(vn, pd.DataFrame(store[vn]), nt) for vn, *_ in VARIANTS]
    summ = pd.DataFrame(rows); b = rows[0]
    summ["فرق الصافي$"] = [round(r["صافي$"]-b["صافي$"],2) for r in rows]
    summ["فرق الهبوط$"] = [round(r.get("أقصى هبوط$",0)-b["أقصى هبوط$"],2) for r in rows]
    summ.to_csv(OUT/"exits_compare_4h.csv", index=False, encoding="utf-8-sig")

    print("\n"+"="*140)
    print("صندوق الخروج — المحفظة الموحدة · 4h · مسطرة 20$")
    print("="*140)
    print(summ[["التركيبة","صفقات","صافي$","فرق الصافي$","عامل الربح","فوز%",
                "متوسط الرابحة$","متوسط الخاسرة$","نسبة العائد","أسوأ صفقة$",
                "أقصى هبوط$","فرق الهبوط$","أسوأ يوم$"]].to_string(index=False), flush=True)

    (OUT/"env_dump.txt").write_text(
        f"python={platform.python_version()}\npandas={pd.__version__}\nnumpy={np.__version__}\n"
        f"canary={cj['got']['net']}\nnotional={C.TRADE_USD}$\nwindow={TS}→{TE}\ncost=0.13%/side\n"
        f"base=stop2.0/trig0.0025/lock0.0045\nvariants={len(VARIANTS)}\n"
        f"cells={len(cells)} symbols={len(syms)}\n"
        f"note=لا إعادة اختيار — الخروج وحده المتغيّر\n", encoding="utf-8")
    print(f"\n→ {OUT}\n{time.time()-t0:.1f} ث", flush=True); return 0

if __name__ == "__main__": raise SystemExit(main())
