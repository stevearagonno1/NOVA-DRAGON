# -*- coding: utf-8 -*-
"""L0025 — تفكيك المحفظة إلى أعمدة: هل ترقية الخروج نفعت الجميع أم الكبير وحده؟

قرار القائد (2026-09-23): نعامل كل استراتيجية كعمود مستقل، نطوّرها على حدة،
لأن لكل واحدة طبيعة عمل مختلفة.

هذه الجولة تضع الأساس الكمّي للخطة: بدل رقم محفظة واحد مجمّع، نقيس
**كل عمود على حدة** تحت الأساس القديم وتحت الفائزة الجديدة.

السؤال الحاسم: ترقية الخروج (وقف 2.5 · تسليح 0.0015 · قفل 0.0060) أعطت
+320$ للمحفظة ككل. لكن المحفظة 89.6% منها عمود واحد. فهل:
  (أ) الترقية نفعت الأعمدة الثلاثة  ⇒ قاعدة عامة، تُطبَّق على أي عمود جديد.
  (ب) نفعت الكبير وحدها وأضرّت الصغار ⇒ دليل مباشر على صحة فكرة الأعمدة،
      وكل عمود يحتاج صندوق خروج خاصًّا به.

هذا فرق جوهري في المال وفي طريقة العمل القادمة كلها.

⚠️ لا إعادة اختيار للدخول · المسطرة 20$ · 0.13%/طرف · شراء فقط · 4h.

    python3 history/hyp_lab/run_l0025_columns.py
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
from measure_l0010_gate import drawdown_stats
import run_l0019_unified as R19
import run_l0017 as R17
import F_197_dual_trail as M197, F_213_breakers as M213

OUT = HIST / "research" / "hyp_lab_out" / "L0025"
TS, TE = "2025-01-01", "2026-08-31"; BAR = 4*3600

BASE = {"stop": 2.0, "trig": 0.0025, "lock": 0.0045}   # الأساس القديم
WIN  = {"stop": 2.5, "trig": 0.0015, "lock": 0.0060}   # فائزة L0022

AR = {"F_213_breakers": "كاسرة النطاق",
      "F_192_ext_entry": "انحراف الدخول",
      "F_165_score_entry": "التنقيط التعويضي"}


def pf(p):
    g, l = p[p > 0].sum(), -p[p < 0].sum()
    return float(g/l) if l > 0 else (np.inf if g > 0 else 0.0)


def run_cfg(cells, cfg):
    """يشغّل كل الخلايا بإعداد خروج واحد، ويعيد الصفقات موسومة بالعمود."""
    old = C.STOP_ATR; C.STOP_ATR = cfg["stop"]
    rows = []
    try:
        for s in sorted({c["symbol"] for c in cells}):
            df = R19.frame(s)
            win = df[(df.index >= TS) & (df.index <= TE)]
            a_s = atr(win)
            for c in [x for x in cells if x["symbol"] == s]:
                if c["driver"] == "F_213_breakers":
                    sig = M213.make_signals(df, trigger=c["combo"]["trigger"]).loc[win.index]
                    if c["combo"]["exit"] == "dual":
                        spec = {**M213.make_dual_spec(), "trig": cfg["trig"], "lock": cfg["lock"]}
                        kw = {"exit_mode": "dual", "dual": spec}
                    else:
                        kw = {"exit_mode": "std"}
                else:
                    sig = R17.EXPS[c["driver"]].make_signals(df, **c["combo"]).loc[win.index]
                    spec = {**M197.make_dual_spec(), "trig": cfg["trig"], "lock": cfg["lock"]}
                    kw = {"exit_mode": "dual", "dual": spec}
                _, tr = simulate(win, sig, a_s, notional=C.TRADE_USD, bar_secs=BAR, **kw)
                rows.extend(trade_rows(c["symbol"], c["driver"], tr))
            del df
            print(f"    {s}", flush=True)
    finally:
        C.STOP_ATR = old
    return pd.DataFrame(rows)


def stat(g):
    p = g["pnl"].to_numpy(float)
    t = pd.to_datetime(g["exit_time"], utc=True)
    dd, _, _ = drawdown_stats(t, p)
    day = g.assign(d=t.dt.date).groupby("d")["pnl"].sum()
    w, l = p[p > 0], p[p < 0]
    return {"صفقات": len(g), "صافي$": round(float(p.sum()), 2),
            "عامل الربح": round(pf(p), 4), "فوز%": round(100*float((p > 0).mean()), 2),
            "متوسط الرابحة$": round(float(w.mean()), 4) if len(w) else 0.0,
            "متوسط الخاسرة$": round(float(l.mean()), 4) if len(l) else 0.0,
            "أقصى هبوط$": round(dd, 2), "أسوأ يوم$": round(float(day.min()), 2)}


def main():
    t0 = time.time()
    can = subprocess.run([sys.executable, str(ROOT/"tools"/"canary.py"), "--json"],
                         capture_output=True, text=True)
    cj = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
    if cj.get("canary") != "ok":
        print("الكاناري فشل — إيقاف L0025.", file=sys.stderr); return 1
    print(f"الكاناري: PASS (net={cj['got']['net']})\n", flush=True)
    OUT.mkdir(parents=True, exist_ok=True); pd.set_option("display.width", 250)

    cells = R19.breaker_cells() + R19.new_cells()
    print(f"الخلايا: {len(cells)} · الأعمدة: {sorted({c['driver'] for c in cells})}\n")

    print("[1/2] الأساس القديم...", flush=True)
    d_base = run_cfg(cells, BASE)
    print("[2/2] الفائزة الجديدة...", flush=True)
    d_win = run_cfg(cells, WIN)

    d_base.to_csv(OUT/"trades_base.csv", index=False, encoding="utf-8-sig")
    d_win.to_csv(OUT/"trades_winner.csv", index=False, encoding="utf-8-sig")

    rows = []
    for drv in sorted(d_base["exp"].unique()):
        b = stat(d_base[d_base["exp"] == drv]); w = stat(d_win[d_win["exp"] == drv])
        rows.append({"العمود": AR.get(drv, drv),
                     "صافي الأساس$": b["صافي$"], "صافي الفائزة$": w["صافي$"],
                     "الفرق$": round(w["صافي$"]-b["صافي$"], 2),
                     "الفرق%": round(100*(w["صافي$"]-b["صافي$"])/abs(b["صافي$"]), 1) if b["صافي$"] else 0.0,
                     "ربح الأساس": b["عامل الربح"], "ربح الفائزة": w["عامل الربح"],
                     "هبوط الأساس$": b["أقصى هبوط$"], "هبوط الفائزة$": w["أقصى هبوط$"],
                     "صفقات": w["صفقات"]})
    pb, pw = stat(d_base), stat(d_win)
    rows.append({"العمود": "— المحفظة كلها —",
                 "صافي الأساس$": pb["صافي$"], "صافي الفائزة$": pw["صافي$"],
                 "الفرق$": round(pw["صافي$"]-pb["صافي$"], 2),
                 "الفرق%": round(100*(pw["صافي$"]-pb["صافي$"])/abs(pb["صافي$"]), 1),
                 "ربح الأساس": pb["عامل الربح"], "ربح الفائزة": pw["عامل الربح"],
                 "هبوط الأساس$": pb["أقصى هبوط$"], "هبوط الفائزة$": pw["أقصى هبوط$"],
                 "صفقات": pw["صفقات"]})
    cmp = pd.DataFrame(rows)
    cmp.to_csv(OUT/"columns_compare_4h.csv", index=False, encoding="utf-8-sig")

    print("\n"+"="*150)
    print("الأعمدة تحت الأساس القديم مقابل الفائزة الجديدة · 4h · مسطرة 20$")
    print("="*150)
    print(cmp.to_string(index=False), flush=True)

    # وزن كل عمود + حساسيته
    tot = pw["صافي$"]
    wt = []
    for drv in sorted(d_win["exp"].unique()):
        g = d_win[d_win["exp"] == drv]; s = stat(g)
        wt.append({"العمود": AR.get(drv, drv), "صافي$": s["صافي$"],
                   "حصة الدخل%": round(100*s["صافي$"]/tot, 1),
                   "صفقات": s["صفقات"], "عملات": g["symbol"].nunique(),
                   "قيمة 1% تحسين$": round(s["صافي$"]/100, 2)})
    w_df = pd.DataFrame(wt).sort_values("صافي$", ascending=False)
    w_df.to_csv(OUT/"column_weights.csv", index=False, encoding="utf-8-sig")
    print("\n=== وزن كل عمود (تحت الفائزة) — ترتيب أولوية العمل ===")
    print(w_df.to_string(index=False), flush=True)

    (OUT/"env_dump.txt").write_text(
        f"python={platform.python_version()}\npandas={pd.__version__}\nnumpy={np.__version__}\n"
        f"canary={cj['got']['net']}\nnotional={C.TRADE_USD}$\nwindow={TS}→{TE}\ncost=0.13%/side\n"
        f"base={BASE}\nwinner={WIN}\ncells={len(cells)}\n", encoding="utf-8")
    print(f"\n→ {OUT}\n{time.time()-t0:.1f} ث", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
