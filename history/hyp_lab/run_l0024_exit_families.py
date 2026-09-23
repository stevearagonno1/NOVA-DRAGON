# -*- coding: utf-8 -*-
"""L0024 — توسعة صندوق الخروج: عائلات خروج جديدة لم تُجرَّب.

آلة المختبر الحالية تدعم ثلاث آليات فقط: وقف قاسٍ · هدف ثابت · متتبّع مزدوج.
هذه الجولة تبني **محرك خروج موسّعًا** يضيف عائلات لم تُقَس قط:

  1) وقف زمني: أغلق بعد N شمعة مهما كان الوضع (الصفقة الميتة تكلّف فرصة).
  2) نقل الوقف للتعادل: بعد ربح معيّن، ارفع الوقف إلى سعر الدخول (صفقة بلا خسارة).
  3) جني جزئي: اقفل نصف المركز عند هدف قريب ودع الباقي يركض.
  4) متتبّع بالمدى الحقيقي: المسافة تتنفّس مع تقلّب السوق بدل نسبة ثابتة.
  5) تركيبات منها مع الفائزة الحالية.

🔒 **التحقق الإلزامي:** المحرك الجديد يُعاير أولًا — يُشغَّل بإعدادات تُطابق
الآلة الأصلية، ويجب أن يعطي نفس النتيجة حرفًا. فإن اختلف تتوقف الجولة.
فلا تُقارَن أرقام محرك جديد بأرقام محرك قديم قبل إثبات تطابقهما.

القاعدة: الفائزة الحالية (وقف 2.5 · تسليح 0.0015 · قفل 0.0060) = 1,898.85$.
كل عائلة تُقاس فوقها — والسؤال: هل تضيف فوق 1,898.85$؟

⚠️ لا إعادة اختيار للدخول · المسطرة 20$ · 0.13% لكل طرف · شراء فقط.

    python3 history/hyp_lab/run_l0024_exit_families.py
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
from measure_l0010_gate import drawdown_stats, psr_dsr
import run_l0019_unified as R19

OUT = HIST / "research" / "hyp_lab_out" / "L0024"
TS, TE = "2025-01-01", "2026-08-31"; BAR = 4*3600
YEARS = (pd.Timestamp(TE,tz="UTC")-pd.Timestamp(TS,tz="UTC")).days/365.25

WIN_STOP, WIN_TRIG, WIN_LOCK = 2.5, 0.0015, 0.0060   # الفائزة من L0022/L0023


# ─────────────────────── المحرك الموسّع ───────────────────────
def sim_ext(df, sig, atr_s, *, stop_atr=WIN_STOP, trig=WIN_TRIG, lock=WIN_LOCK,
            wide=0.0020, tight=0.0008, notional=20.0,
            time_bars=0, be_at=0.0, partial_at=0.0, partial_frac=0.0,
            atr_trail=0.0):
    """محرك خروج موسّع. الافتراضات تُعيد إنتاج المتتبّع المزدوج حرفًا.

    time_bars>0     : وقف زمني بعدد الشموع.
    be_at>0         : عند بلوغ هذا الربح، الوقف يصعد إلى سعر الدخول.
    partial_at>0    : عند بلوغ هذا الربح، يُقفل partial_frac من المركز.
    atr_trail>0     : المتتبّع يستعمل atr_trail×ATR بدل النسبة الثابتة.
    """
    o = df["open"].to_numpy(); h = df["high"].to_numpy()
    l = df["low"].to_numpy();  c = df["close"].to_numpy()
    a = atr_s.to_numpy(); n = len(df); idx = df.index
    sig_i = np.flatnonzero(sig.to_numpy())
    cost = C.COST_PER_SIDE
    trades = []
    pos = None

    def _open(i):
        e = i + 1
        if e >= n or not np.isfinite(a[i]):
            return None
        ef = o[e] * (1 + cost)
        return {"entry_j": e, "entry": ef, "entry_time": idx[e], "atr_sig": a[i],
                "notional": notional, "hard_stop": ef - stop_atr * a[i],
                "tp": ef + C.TP_ATR * a[i], "peak": o[e],
                "part_done": False, "part_pnl": 0.0, "done": False}

    def _close(p, j, price, side, frac=1.0, final=True):
        # محاسبة مطابقة حرفًا لـ_close_position في الآلة الأصلية
        fill = price * (1 - cost)
        qty = (p["notional"] / p["entry"]) * frac
        gross = qty * (fill - p["entry"])
        if final:                      # إغلاق الباقي مهما كانت حصته
            p["pnl"] = p["part_pnl"] + gross
            p["exit_fill"] = fill; p["exit_j"] = j
            p["exit_time"] = idx[j]; p["exit_side"] = side
            p["risk"] = None; p["done"] = True
        else:                          # جني جزئي: المركز يبقى مفتوحًا
            p["part_pnl"] += gross
            p["part_done"] = True

    def _run(p):
        j = p["entry_j"]
        while j < n and not p["done"]:
            held = j - p["entry_j"]
            eff = p["hard_stop"]
            gain = (p["peak"] - p["entry"]) / p["entry"]

            if be_at > 0 and gain >= be_at:                 # نقل للتعادل
                eff = max(eff, p["entry"])
            if gain >= trig:                                 # المتتبّع
                if atr_trail > 0:
                    local = max(p["entry"] * (1 + lock), p["peak"] - atr_trail * p["atr_sig"])
                else:
                    tr = wide if gain <= 0.01 else tight
                    local = max(p["entry"] * (1 + lock), p["peak"] * (1 - tr))
                eff = max(eff, local)

            if l[j] <= eff:                                  # ضربة الوقف
                rem = 1.0 - (partial_frac if p["part_done"] else 0.0)
                _close(p, j, eff, "stop", rem); break
            if (partial_at > 0 and not p["part_done"]
                    and h[j] >= p["entry"] * (1 + partial_at)):   # جني جزئي
                _close(p, j, p["entry"] * (1 + partial_at), "partial",
                       partial_frac, final=False)
            if time_bars > 0 and held >= time_bars:          # وقف زمني
                rem = 1.0 - (partial_frac if p["part_done"] else 0.0)
                _close(p, j, c[j], "time", rem); break
            p["peak"] = max(p["peak"], h[j])
            j += 1
        if not p["done"]:
            rem = 1.0 - (partial_frac if p["part_done"] else 0.0)
            jj = min(j, n-1)
            _close(p, jj, c[jj], "eod", rem)

    for i in sig_i:
        if pos is not None:
            if not pos.get("done"):
                _run(pos)
            trades.append(pos)
            busy = pos["exit_j"] > i
            pos = None
            if busy:
                continue
        p = _open(i)
        if p is not None:
            pos = p
    if pos is not None:
        if not pos.get("done"):
            _run(pos)
        trades.append(pos)
    return trades


VARIANTS = [
    ("الفائزة الحالية (مرجع)",      {}),
    ("وقف زمني 12 شمعة",           {"time_bars": 12}),
    ("وقف زمني 24 شمعة",           {"time_bars": 24}),
    ("وقف زمني 48 شمعة",           {"time_bars": 48}),
    ("تعادل عند 0.30%",            {"be_at": 0.0030}),
    ("تعادل عند 0.50%",            {"be_at": 0.0050}),
    ("جني نصف عند 0.50%",          {"partial_at": 0.0050, "partial_frac": 0.5}),
    ("جني نصف عند 1.00%",          {"partial_at": 0.0100, "partial_frac": 0.5}),
    ("جني ثلث عند 0.50%",          {"partial_at": 0.0050, "partial_frac": 0.33}),
    ("متتبّع بالمدى 1.0",           {"atr_trail": 1.0}),
    ("متتبّع بالمدى 2.0",           {"atr_trail": 2.0}),
    ("متتبّع بالمدى 0.5",           {"atr_trail": 0.5}),
]


def pf(p):
    g, l = p[p>0].sum(), -p[p<0].sum()
    return float(g/l) if l>0 else (np.inf if g>0 else 0.0)


def stat(name, rows):
    d = pd.DataFrame(rows)
    if d.empty: return {"التركيبة": name, "صفقات": 0, "صافي$": 0.0}
    d["exit_time"] = pd.to_datetime(d["exit_time"], utc=True); d = d.sort_values("exit_time")
    p = d["pnl"].to_numpy(float); dd, dys, _ = drawdown_stats(d["exit_time"], p)
    day = d.groupby(d["exit_time"].dt.date)["pnl"].sum()
    w, l = p[p>0], p[p<0]
    return {"التركيبة": name, "صفقات": len(d), "صافي$": round(float(p.sum()),2),
            "عامل الربح": round(pf(p),4), "فوز%": round(100*float((p>0).mean()),2),
            "متوسط الرابحة$": round(float(w.mean()),4) if len(w) else 0.0,
            "متوسط الخاسرة$": round(float(l.mean()),4) if len(l) else 0.0,
            "أقصى هبوط$": round(dd,2), "أسوأ يوم$": round(float(day.min()),2),
            "DSR": psr_dsr(p, YEARS, 720)["dsr"]}


def cell_sig(c, df, win):
    if c["driver"] == "F_213_breakers":
        import F_213_breakers as M
        return M.make_signals(df, trigger=c["combo"]["trigger"]).loc[win.index], c["combo"]["exit"]
    import run_l0017 as R17
    return R17.EXPS[c["driver"]].make_signals(df, **c["combo"]).loc[win.index], "dual"


def main():
    t0 = time.time()
    can = subprocess.run([sys.executable, str(ROOT/"tools"/"canary.py"), "--json"],
                         capture_output=True, text=True)
    cj = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
    if cj.get("canary") != "ok":
        print("الكاناري فشل — إيقاف L0024.", file=sys.stderr); return 1
    print(f"الكاناري: PASS (net={cj['got']['net']})\n", flush=True)
    OUT.mkdir(parents=True, exist_ok=True); pd.set_option("display.width", 250)

    cells = R19.breaker_cells() + R19.new_cells()
    syms = sorted({c["symbol"] for c in cells})

    # ═══ المعايرة الإلزامية: المحرك الجديد = الآلة الأصلية؟ ═══
    print("معايرة المحرك الموسّع مقابل الآلة الأصلية...", flush=True)
    import F_197_dual_trail as M197, F_213_breakers as M213
    old = C.STOP_ATR; C.STOP_ATR = WIN_STOP
    ref, new = [], []
    try:
        for s in syms[:4]:
            df = R19.frame(s); win = df[(df.index>=TS)&(df.index<=TE)]
            for c in [x for x in cells if x["symbol"]==s]:
                sig, mode = cell_sig(c, df, win)
                if mode != "dual":
                    continue
                spec = (M213.make_dual_spec() if c["driver"]=="F_213_breakers"
                        else M197.make_dual_spec())
                spec = {**spec, "trig": WIN_TRIG, "lock": WIN_LOCK}
                _, tr = simulate(win, sig, atr(win), notional=C.TRADE_USD,
                                 bar_secs=BAR, exit_mode="dual", dual=spec)
                ref.extend(trade_rows(c["symbol"], c["driver"], tr))
                t2 = sim_ext(win, sig, atr(win), wide=spec["wide"], tight=spec["tight"],
                             notional=C.TRADE_USD)
                new.extend(trade_rows(c["symbol"], c["driver"], t2))
            del df
    finally:
        C.STOP_ATR = old
    rn = round(sum(r["pnl"] for r in ref), 6)
    nn = round(sum(r["pnl"] for r in new), 6)
    print(f"  الأصلية: {rn}$ ({len(ref)} صفقة) · الموسّع: {nn}$ ({len(new)} صفقة)")
    if abs(rn - nn) > 0.01 or len(ref) != len(new):
        print("❌ المحرك الموسّع لا يطابق الأصلي — إيقاف الجولة (لا تُقارن أرقام محركين مختلفين).",
              file=sys.stderr)
        pd.DataFrame([{"ref_net": rn, "new_net": nn, "ref_n": len(ref), "new_n": len(new)}]
                     ).to_csv(OUT/"calibration_FAILED.csv", index=False, encoding="utf-8-sig")
        return 2
    print("  ✅ مطابق — الجولة تكمل\n", flush=True)

    old = C.STOP_ATR; C.STOP_ATR = WIN_STOP
    store = {v[0]: [] for v in VARIANTS}
    try:
        for s in syms:
            df = R19.frame(s); win = df[(df.index>=TS)&(df.index<=TE)]
            a_s = atr(win)
            for c in [x for x in cells if x["symbol"]==s]:
                sig, mode = cell_sig(c, df, win)
                if mode != "dual":
                    # خلايا الوقف/الهدف تبقى على آلتها الأصلية في كل التركيبات
                    _, tr = simulate(win, sig, a_s, notional=C.TRADE_USD,
                                     bar_secs=BAR, exit_mode="std")
                    rows = trade_rows(c["symbol"], c["driver"], tr)
                    for vn, _ in VARIANTS: store[vn].extend(rows)
                    continue
                for vn, kw in VARIANTS:
                    tr = sim_ext(win, sig, a_s, notional=C.TRADE_USD, **kw)
                    store[vn].extend(trade_rows(c["symbol"], c["driver"], tr))
            print(f"  {s}: تمّت {len(VARIANTS)} تركيبة", flush=True)
            del df
    finally:
        C.STOP_ATR = old

    rows = [stat(vn, store[vn]) for vn, _ in VARIANTS]
    summ = pd.DataFrame(rows); b = rows[0]
    summ["فرق الصافي$"] = [round(r["صافي$"]-b["صافي$"],2) for r in rows]
    summ["فرق الهبوط$"] = [round(r.get("أقصى هبوط$",0)-b["أقصى هبوط$"],2) for r in rows]
    summ.to_csv(OUT/"families_4h.csv", index=False, encoding="utf-8-sig")

    print("\n"+"="*140)
    print("عائلات الخروج الجديدة — فوق الفائزة الحالية · 4h · مسطرة 20$")
    print("="*140)
    print(summ[["التركيبة","صفقات","صافي$","فرق الصافي$","عامل الربح","فوز%",
                "متوسط الرابحة$","متوسط الخاسرة$","أقصى هبوط$","فرق الهبوط$",
                "أسوأ يوم$"]].to_string(index=False), flush=True)

    (OUT/"env_dump.txt").write_text(
        f"python={platform.python_version()}\npandas={pd.__version__}\nnumpy={np.__version__}\n"
        f"canary={cj['got']['net']}\nnotional={C.TRADE_USD}$\nwindow={TS}→{TE}\ncost=0.13%/side\n"
        f"base=stop{WIN_STOP}/trig{WIN_TRIG}/lock{WIN_LOCK}\nvariants={len(VARIANTS)}\n"
        f"calibration=ref {rn}$ == ext {nn}$ ✅\ncells={len(cells)} symbols={len(syms)}\n",
        encoding="utf-8")
    print(f"\n→ {OUT}\n{time.time()-t0:.1f} ث", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
