# -*- coding: utf-8 -*-
"""L0035 — تطوير الأعمدة الثلاثة: محاور لم تُسوَّ قط.

أمر القائد: «ابحث في كل المستودع عن طرق أو تقنيات لتطوير الثلاث،
وجرّب احتمالات في تغيير إعدادات المؤشرات.»

التفتيش الشامل للمستودع كشف **ثلاث فجوات حقيقية**:

  ① **نواة كسر البنية** (F_126) — هي القلب المشترك للأعمدة الثلاثة كلها —
     تعلن شبكة تسوية من 27 تركيبة (body_ratio × range_atr × lookback)
     **لم تُسوَّ ولا مرة واحدة**. كل قياساتنا استعملت الافتراضات (0.50/0.80/20).
  ② **إعدادات المؤشرات** في nova_v8/config.py (طول RSI · متوسطات · ماكد ·
     بولنجر · قوة الاتجاه) مجمّدة منذ البداية ولم تُختبر بديلة قط.
  ③ **بوابة التمدّد** (F_127) لبنة مبنية بشبكة معلنة ولم تدخل أي محفظة.

🔒 **سقف المحاولات المعلَن قبل البدء = 46 قياسًا**
     (27 نواة + 15 مؤشرات + 4 بوابة تمدّد). يُسجَّل ولا يُرفع.

🔒 **الحماية من الانتقاء (بروتوكول الثقة):**
   القرار على فترة **2021-09→2023-12** وحدها.
   الحكم على **2024-01→2026-08** التي لم تشارك في القرار.
   أي مرشّح لا يتفوّق على الأساس في فترة الحكم = يُرفض.

⚠️ المسطرة 20$ · 0.13%/طرف · شراء فقط · 4h · خروج الفائزة المثبَّت.

    python3 history/hyp_lab/run_l0035_tuning.py
"""
from __future__ import annotations
import itertools, json, os, pathlib, platform, subprocess, sys, time
import numpy as np, pandas as pd

_S = pathlib.Path(os.environ.get("NOVA_SCRATCH", "~/.nova_scratch")).expanduser()
os.environ.setdefault("NOVA_HOME", str(_S / "home"))
HIST = pathlib.Path(__file__).resolve().parents[1]; ROOT = HIST.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))

import common as C
from common import atr, simulate, trade_rows
import run_l0019_unified as R19
import run_l0017 as R17
import F_126_mss_core as M126
import L0017_F_192_ext_entry as M192mod
import L0017_F_165_score_entry as M165mod
import F_197_dual_trail as M197, F_213_breakers as M213
from nova_v8 import config as NC
from nova_v8 import indicators as NI

OUT = HIST / "research" / "hyp_lab_out" / "L0035"
DEC_S, DEC_E = "2021-09-01", "2023-12-31"     # فترة القرار
JUD_S, JUD_E = "2024-01-01", "2026-08-31"     # فترة الحكم
WARM = "2021-06-01"
BAR = 4*3600
WIN = {"stop": 2.5, "trig": 0.0015, "lock": 0.0060}
DECLARED_CAP = 46

AR = {"F_213_breakers": "كاسرة النطاق", "F_192_ext_entry": "انحراف الدخول",
      "F_165_score_entry": "التنقيط التعويضي"}


def pf(p):
    g, l = p[p > 0].sum(), -p[p < 0].sum()
    return float(g/l) if l > 0 else (np.inf if g > 0 else 0.0)


_FRAMES = {}


def frames(sym):
    if sym not in _FRAMES:
        from common import load, to_bars
        d1 = load(str(ROOT/"crypto_archive"/f"{sym}_1m.parquet"), start=WARM, end=JUD_E)
        _FRAMES[sym] = to_bars(d1, 240)
        del d1
    return _FRAMES[sym]


def run_all(cells, s0, s1):
    """يشغّل كل الخلايا على نافذة، بالإعدادات العامة السارية وقت الاستدعاء."""
    old = C.STOP_ATR; C.STOP_ATR = WIN["stop"]
    rows = []
    try:
        for sym in sorted({c["symbol"] for c in cells}):
            df = frames(sym)
            win = df[(df.index >= s0) & (df.index <= s1)]
            if len(win) < 100:
                continue
            a_s = atr(win)
            for c in [x for x in cells if x["symbol"] == sym]:
                if c["driver"] == "F_213_breakers":
                    sig = M213.make_signals(df, trigger=c["combo"]["trigger"]).loc[win.index]
                    kw = ({"exit_mode": "dual", "dual": {**M213.make_dual_spec(),
                           "trig": WIN["trig"], "lock": WIN["lock"]}}
                          if c["combo"]["exit"] == "dual" else {"exit_mode": "std"})
                else:
                    sig = R17.EXPS[c["driver"]].make_signals(df, **c["combo"]).loc[win.index]
                    kw = {"exit_mode": "dual", "dual": {**M197.make_dual_spec(),
                          "trig": WIN["trig"], "lock": WIN["lock"]}}
                _, tr = simulate(win, sig, a_s, notional=C.TRADE_USD, bar_secs=BAR, **kw)
                rows.extend(trade_rows(c["symbol"], c["driver"], tr))
            del win
    finally:
        C.STOP_ATR = old
    return pd.DataFrame(rows)


def summary(d):
    if d.empty:
        return {"صافي$": 0.0, "صفقات": 0, "عامل الربح": 0.0}
    p = d["pnl"].to_numpy(float)
    return {"صافي$": round(float(p.sum()), 2), "صفقات": len(d),
            "عامل الربح": round(pf(p), 4)}


def per_col(d):
    out = {}
    for k, g in d.groupby("exp"):
        out[AR.get(k, k)] = round(float(g["pnl"].sum()), 2)
    return out


def main():
    t0 = time.time()
    can = subprocess.run([sys.executable, str(ROOT/"tools"/"canary.py"), "--json"],
                         capture_output=True, text=True)
    cj = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
    if cj.get("canary") != "ok":
        print("الكاناري فشل — إيقاف.", file=sys.stderr); return 1
    print(f"الكاناري: PASS · سقف المحاولات المعلن: {DECLARED_CAP}")
    print(f"القرار: {DEC_S}→{DEC_E} · الحكم: {JUD_S}→{JUD_E}\n", flush=True)
    OUT.mkdir(parents=True, exist_ok=True); pd.set_option("display.width", 250)

    cells = R19.breaker_cells() + R19.new_cells()
    used = 0

    # ═══ الأساس على فترة القرار ═══
    base_dec = summary(run_all(cells, DEC_S, DEC_E)); used += 1
    print(f"الأساس (فترة القرار): {base_dec['صافي$']}$ · {base_dec['صفقات']} صفقة\n", flush=True)

    results = []

    # ═══ ① نواة كسر البنية — 27 تركيبة لم تُسوَّ قط ═══
    print("① نواة كسر البنية (القلب المشترك للأعمدة الثلاثة) — 27 تركيبة", flush=True)
    d_body = M126.mss_signal.__defaults__
    grid = list(itertools.product([0.40, 0.50, 0.60], [0.60, 0.80, 1.00], [10, 20, 50]))
    orig = M126.mss_signal
    for br, ra, lb in grid:
        if (br, ra, lb) == (0.50, 0.80, 20):
            results.append({"المحور": "نواة كسر البنية", "الإعداد": "الأساس 0.50/0.80/20",
                            **base_dec}); continue
        def patched(df, body_ratio=br, range_atr=ra, lookback=lb, _o=orig):
            return _o(df, body_ratio=body_ratio, range_atr=range_atr, lookback=lookback)
        M126.mss_signal = patched
        M192mod.mss_signal = patched      # الوحدات تستورد الاسم لا الوحدة
        M165mod.mss_signal = patched
        try:
            r = summary(run_all(cells, DEC_S, DEC_E)); used += 1
            results.append({"المحور": "نواة كسر البنية",
                            "الإعداد": f"جسم{br}/مدى{ra}/نظر{lb}", **r})
            print(f"   جسم{br} مدى{ra} نظر{lb}: {r['صافي$']:>8.2f}$ ({r['صفقات']})", flush=True)
        finally:
            M126.mss_signal = orig
            M192mod.mss_signal = orig
            M165mod.mss_signal = orig

    # ═══ ② إعدادات المؤشرات — 15 تركيبة ═══
    print("\n② إعدادات المؤشرات (مجمّدة منذ البداية)", flush=True)
    ind_grid = [
        ("RSI_LEN", 7), ("RSI_LEN", 10), ("RSI_LEN", 21),
        ("EMA_FAST", 21), ("EMA_FAST", 34), ("EMA_FAST", 100),
        ("EMA_SLOW", 100), ("EMA_SLOW", 150), ("EMA_SLOW", 300),
        ("ADX_LEN", 7), ("ADX_LEN", 21),
        ("ADX_TREND", 18.0), ("ADX_TREND", 28.0),
        ("BB_STD", 1.5), ("BB_STD", 2.5),
    ]
    for key, val in ind_grid:
        if not hasattr(NC, key):
            print(f"   (تخطٍّ: {key} غير موجود)"); continue
        old = getattr(NC, key)
        setattr(NC, key, val)
        M213._cache.clear()
        try:
            r = summary(run_all(cells, DEC_S, DEC_E)); used += 1
            results.append({"المحور": "إعدادات المؤشرات",
                            "الإعداد": f"{key}={val} (أصل {old})", **r})
            print(f"   {key}={val}: {r['صافي$']:>8.2f}$ ({r['صفقات']})", flush=True)
        finally:
            setattr(NC, key, old); M213._cache.clear()

    df_res = pd.DataFrame(results)
    df_res.to_csv(OUT/"decision_sweep.csv", index=False, encoding="utf-8-sig")

    print("\n" + "="*120)
    print(f"نتائج فترة القرار — أفضل عشرة (الأساس {base_dec['صافي$']}$)")
    print("="*120)
    top = df_res.sort_values("صافي$", ascending=False).head(10)
    print(top.to_string(index=False), flush=True)

    # ═══ ③ الحكم على المرشّحين على فترة لم تشارك في القرار ═══
    cands = df_res[df_res["صافي$"] > base_dec["صافي$"]].sort_values(
        "صافي$", ascending=False).head(3)
    print("\n" + "="*120)
    print("③ الحكم على فترة مستقلة (2024-01→2026-08)")
    print("="*120)
    base_jud = summary(run_all(cells, JUD_S, JUD_E)); used += 1
    print(f"الأساس على فترة الحكم: {base_jud['صافي$']}$ · {base_jud['صفقات']} صفقة\n")

    jud = [{"المرشّح": "الأساس", "قرار$": base_dec["صافي$"],
            "حكم$": base_jud["صافي$"], "فرق الحكم$": 0.0}]
    for _, row in cands.iterrows():
        lbl = row["الإعداد"]
        if row["المحور"] == "نواة كسر البنية" and "الأساس" not in lbl:
            br = float(lbl.split("جسم")[1].split("/")[0])
            ra = float(lbl.split("مدى")[1].split("/")[0])
            lb = int(lbl.split("نظر")[1])
            def patched(df, body_ratio=br, range_atr=ra, lookback=lb, _o=orig):
                return _o(df, body_ratio=body_ratio, range_atr=range_atr, lookback=lookback)
            M126.mss_signal = patched
            M192mod.mss_signal = patched
            M165mod.mss_signal = patched
            try:
                r = summary(run_all(cells, JUD_S, JUD_E)); used += 1
            finally:
                M126.mss_signal = orig
                M192mod.mss_signal = orig
                M165mod.mss_signal = orig
        elif row["المحور"] == "إعدادات المؤشرات":
            key = lbl.split("=")[0]; val = float(lbl.split("=")[1].split(" ")[0])
            if key in ("RSI_LEN", "EMA_FAST", "EMA_SLOW", "ADX_LEN"):
                val = int(val)
            old = getattr(NC, key); setattr(NC, key, val); M213._cache.clear()
            try:
                r = summary(run_all(cells, JUD_S, JUD_E)); used += 1
            finally:
                setattr(NC, key, old); M213._cache.clear()
        else:
            continue
        jud.append({"المرشّح": lbl, "قرار$": row["صافي$"], "حكم$": r["صافي$"],
                    "فرق الحكم$": round(r["صافي$"] - base_jud["صافي$"], 2)})
        print(f"  {lbl}: قرار {row['صافي$']}$ → حكم {r['صافي$']}$ "
              f"({r['صافي$']-base_jud['صافي$']:+.2f}$)", flush=True)

    jdf = pd.DataFrame(jud)
    jdf.to_csv(OUT/"judgement.csv", index=False, encoding="utf-8-sig")

    print("\n=== الخلاصة ===")
    win_rows = jdf[jdf["فرق الحكم$"] > 0]
    if len(win_rows):
        b = win_rows.iloc[0]
        print(f"✅ مرشّح صمد: {b['المرشّح']} ⇒ {b['فرق الحكم$']:+.2f}$ على فترة مستقلة")
    else:
        print("❌ لا مرشّح صمد على فترة الحكم — الإعدادات الحالية تبقى")
    print(f"\nالمحاولات المستهلكة: {used} / {DECLARED_CAP} المعلنة")

    (OUT/"env_dump.txt").write_text(
        f"python={platform.python_version()}\npandas={pd.__version__}\nnumpy={np.__version__}\n"
        f"canary={cj['got']['net']}\ndecision={DEC_S}→{DEC_E}\njudgement={JUD_S}→{JUD_E}\n"
        f"declared_cap={DECLARED_CAP}\nused={used}\nexit={WIN}\nnotional={C.TRADE_USD}\n",
        encoding="utf-8")
    print(f"\n→ {OUT}\n{time.time()-t0:.1f} ث", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
