# -*- coding: utf-8 -*-
"""L0036 — مواصلة التطوير: بوابة التمدّد + المحاور المتبقية.

أمر القائد: «نفّذ (ب)» — مواصلة التطوير بعد L0035.

يبني على فائز L0035 المعتمد: نواة كسر البنية **جسم 0.40 · مدى 0.60 · نظر 10**.
كل قياس هنا يجري فوق هذا الأساس الجديد، لا فوق القديم.

ما يُقاس (المحاور التي بقيت «لم تُقَس»):
  ① **بوابة التمدّد** (F_127) — لبنة مبنية بشبكة معلنة، لم تدخل أي محفظة قط.
     تشترط أن يكون مدى شمعة الكسر ≥ مضاعف من متوسط الحركة.
  ② **محاور المؤشرات المتبقية:** ماكد · بولنجر · ستوكاستك · ألما · متوسطات.
  ③ **محاور العمودين الصغيرين نفسها** — لم تُعَد تسويتها منذ L0017،
     أي قبل ترقية الخروج وقبل نواة L0035. الشرط تبدّل مرتين.

🔒 **سقف المحاولات المعلَن = 40** (4 بوابة + 16 مؤشرات + 20 عمودين). لا يُرفع.
🔒 القرار 2021-09→2023-12 · الحكم 2024-01→2026-08 (لم تشارك).

⚠️ 20$ · 0.13%/طرف · شراء فقط · 4h · خروج الفائزة المثبَّت.

    python3 history/hyp_lab/run_l0036_more.py
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
import run_l0019_unified as R19
import run_l0017 as R17
import F_126_mss_core as M126
import F_213_breakers as M213
import L0017_F_192_ext_entry as M192mod
import L0017_F_165_score_entry as M165mod
import run_l0035_tuning as L35
from nova_v8 import config as NC

OUT = HIST / "research" / "hyp_lab_out" / "L0036"
DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
DECLARED_CAP = 40

# فائز L0035 — الأساس الجديد
CORE = {"body_ratio": 0.40, "range_atr": 0.60, "lookback": 10}
_ORIG = M126.mss_signal


def set_core(body_ratio=None, range_atr=None, lookback=None, disp_min=None):
    """يثبّت نواة L0035، مع إمكانية إضافة بوابة التمدّد فوقها."""
    br = CORE["body_ratio"] if body_ratio is None else body_ratio
    ra = CORE["range_atr"] if range_atr is None else range_atr
    lb = CORE["lookback"] if lookback is None else lookback

    def patched(df, body_ratio=br, range_atr=ra, lookback=lb,
                _o=_ORIG, _d=disp_min):
        sig = _o(df, body_ratio=body_ratio, range_atr=range_atr, lookback=lookback)
        if _d is not None:
            h, l, c = df["high"], df["low"], df["close"]
            pc = c.shift(1)
            tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
            atr14 = tr.rolling(14, min_periods=14).mean()
            disp = (h - l).replace(0, np.nan) / atr14
            sig = sig & (disp >= _d)
        return sig.fillna(False)

    M126.mss_signal = M192mod.mss_signal = M165mod.mss_signal = patched


def pf(p):
    g, l = p[p > 0].sum(), -p[p < 0].sum()
    return float(g/l) if l > 0 else (np.inf if g > 0 else 0.0)


def run(cells, s0, s1):
    d = L35.run_all(cells, s0, s1)
    if d.empty:
        return {"صافي$": 0.0, "صفقات": 0, "عامل الربح": 0.0}, d
    p = d["pnl"].to_numpy(float)
    return {"صافي$": round(float(p.sum()), 2), "صفقات": len(d),
            "عامل الربح": round(pf(p), 4)}, d


def main():
    t0 = time.time()
    can = subprocess.run([sys.executable, str(ROOT/"tools"/"canary.py"), "--json"],
                         capture_output=True, text=True)
    cj = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
    if cj.get("canary") != "ok":
        print("الكاناري فشل — إيقاف.", file=sys.stderr); return 1
    print(f"الكاناري: PASS · سقف المحاولات المعلن: {DECLARED_CAP}")
    print(f"الأساس الجديد (فائز L0035): {CORE}\n", flush=True)
    OUT.mkdir(parents=True, exist_ok=True); pd.set_option("display.width", 250)

    cells = R19.breaker_cells() + R19.new_cells()
    used = 0
    res = []

    set_core()
    base_dec, _ = run(cells, DEC_S, DEC_E); used += 1
    print(f"الأساس على فترة القرار: {base_dec['صافي$']}$ ({base_dec['صفقات']} صفقة)\n")

    # ① بوابة التمدّد
    print("① بوابة التمدّد (لم تدخل أي محفظة قط)", flush=True)
    for d in [1.00, 1.50, 1.60, 2.00]:
        set_core(disp_min=d)
        r, _ = run(cells, DEC_S, DEC_E); used += 1
        res.append({"المحور": "بوابة التمدّد", "الإعداد": f"تمدّد≥{d}", **r})
        print(f"   تمدّد≥{d}: {r['صافي$']:>8.2f}$ ({r['صفقات']})", flush=True)
    set_core()

    # ② محاور المؤشرات المتبقية
    print("\n② محاور المؤشرات المتبقية", flush=True)
    grid = [("MACD_FAST", 8), ("MACD_FAST", 16), ("MACD_SLOW", 20), ("MACD_SLOW", 34),
            ("MACD_SIG", 5), ("MACD_SIG", 14), ("BB_LEN", 14), ("BB_LEN", 30),
            ("STOCH_K", 7), ("STOCH_K", 21), ("ALMA_LEN", 100), ("ALMA_LEN", 300),
            ("EMA_FAST", 21), ("EMA_FAST", 34), ("EMA_SLOW", 150), ("VOL_SMA_LEN", 10)]
    for key, val in grid:
        if not hasattr(NC, key):
            print(f"   (تخطٍّ: {key})"); continue
        old = getattr(NC, key); setattr(NC, key, val); M213._cache.clear()
        try:
            r, _ = run(cells, DEC_S, DEC_E); used += 1
            res.append({"المحور": "مؤشرات", "الإعداد": f"{key}={val}", **r})
            print(f"   {key}={val}: {r['صافي$']:>8.2f}$ ({r['صفقات']})", flush=True)
        finally:
            setattr(NC, key, old); M213._cache.clear()

    # ③ محاور العمودين الصغيرين (لم تُعَد تسويتها منذ L0017)
    print("\n③ محاور العمودين الصغيرين فوق الأساس الجديد", flush=True)
    orig_cells = {id(c): dict(c["combo"]) for c in cells}
    for axis, vals, drv in [
        ("ext_max", [-0.15, 0.10, 0.50, 1.00], "F_192_ext_entry"),
        ("ema_pct", [0.05, 0.08, 0.10], "F_192_ext_entry"),
        ("score_th", [70, 72, 75], "F_165_score_entry"),
        ("flow_mom", [2.5, 3.0, 4.0], "F_165_score_entry"),
        ("vol_mom", [2.0, 2.5, 3.0], "F_165_score_entry"),
    ]:
        for v in vals:
            for c in cells:
                if c["driver"] == drv:
                    c["combo"][axis] = v
            try:
                r, _ = run(cells, DEC_S, DEC_E); used += 1
                res.append({"المحور": f"{drv}·{axis}", "الإعداد": f"{axis}={v}", **r})
                print(f"   {drv} {axis}={v}: {r['صافي$']:>8.2f}$", flush=True)
            finally:
                for c in cells:
                    c["combo"] = dict(orig_cells[id(c)])

    df = pd.DataFrame(res)
    df.to_csv(OUT/"decision_sweep.csv", index=False, encoding="utf-8-sig")
    print("\n" + "="*115)
    print(f"أفضل ثمانية على فترة القرار (الأساس {base_dec['صافي$']}$)")
    print("="*115)
    print(df.sort_values("صافي$", ascending=False).head(8).to_string(index=False), flush=True)

    # ④ الحكم على فترة مستقلة
    print("\n" + "="*115); print("④ الحكم على فترة مستقلة"); print("="*115)
    set_core(); base_jud, _ = run(cells, JUD_S, JUD_E); used += 1
    print(f"الأساس على فترة الحكم: {base_jud['صافي$']}$\n")

    cands = df[df["صافي$"] > base_dec["صافي$"]].sort_values("صافي$", ascending=False).head(3)
    jud = [{"المرشّح": "الأساس (فائز L0035)", "قرار$": base_dec["صافي$"],
            "حكم$": base_jud["صافي$"], "فرق$": 0.0}]
    if cands.empty:
        print("  لا مرشّح تفوّق على الأساس في فترة القرار.")
    for _, row in cands.iterrows():
        ax, lbl = row["المحور"], row["الإعداد"]
        if ax == "بوابة التمدّد":
            set_core(disp_min=float(lbl.split("≥")[1]))
            r, _ = run(cells, JUD_S, JUD_E); used += 1; set_core()
        elif ax == "مؤشرات":
            k, v = lbl.split("="); v = float(v)
            if k in ("MACD_FAST","MACD_SLOW","MACD_SIG","BB_LEN","STOCH_K",
                     "ALMA_LEN","EMA_FAST","EMA_SLOW","VOL_SMA_LEN"):
                v = int(v)
            old = getattr(NC, k); setattr(NC, k, v); M213._cache.clear()
            try:
                r, _ = run(cells, JUD_S, JUD_E); used += 1
            finally:
                setattr(NC, k, old); M213._cache.clear()
        else:
            drv, axis = ax.split("·"); v = float(lbl.split("=")[1])
            if axis == "score_th":
                v = int(v)
            for c in cells:
                if c["driver"] == drv:
                    c["combo"][axis] = v
            try:
                r, _ = run(cells, JUD_S, JUD_E); used += 1
            finally:
                for c in cells:
                    c["combo"] = dict(orig_cells[id(c)])
        jud.append({"المرشّح": f"{ax} · {lbl}", "قرار$": row["صافي$"],
                    "حكم$": r["صافي$"], "فرق$": round(r["صافي$"]-base_jud["صافي$"], 2)})
        print(f"  {ax} · {lbl}: قرار {row['صافي$']}$ → حكم {r['صافي$']}$ "
              f"({r['صافي$']-base_jud['صافي$']:+.2f}$)", flush=True)

    jdf = pd.DataFrame(jud)
    jdf.to_csv(OUT/"judgement.csv", index=False, encoding="utf-8-sig")
    w = jdf[jdf["فرق$"] > 0]
    print("\n=== الخلاصة ===")
    print(f"✅ صمد: {w.iloc[0]['المرشّح']} ⇒ {w.iloc[0]['فرق$']:+.2f}$" if len(w)
          else "❌ لا مرشّح صمد — الأساس الحالي يبقى")
    print(f"المحاولات: {used} / {DECLARED_CAP}")

    (OUT/"env_dump.txt").write_text(
        f"python={platform.python_version()}\npandas={pd.__version__}\n"
        f"canary={cj['got']['net']}\nbase_core={CORE}\ndecision={DEC_S}→{DEC_E}\n"
        f"judgement={JUD_S}→{JUD_E}\ndeclared_cap={DECLARED_CAP}\nused={used}\n",
        encoding="utf-8")
    print(f"\n→ {OUT}\n{time.time()-t0:.1f} ث", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
