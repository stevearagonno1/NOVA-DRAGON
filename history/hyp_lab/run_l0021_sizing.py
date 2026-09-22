# -*- coding: utf-8 -*-
"""L0021 — تصغير الحصة بدل المنع (توظيف درس جولة الفلاتر).

الدرس المقيس في L0020: فلتر حالة السوق الثلاثي يتعرّف على **28 من أسوأ 30 صفقة**
في المحفظة — تشخيصه ممتاز. لكن علاجه (منع الدخول) كلّف 89% من الربح مقابل
خفض 81% من الألم، فتراجعت الكفاءة من 64.42 إلى 35.90.

الفرضية هنا: **لا تمنع — صغّر.** ادخل الصفقة التي يرفضها الفلتر بحصة أصغر
بدل إلغائها. فيبقى جزء كبير من الربح ويخفّ الألم.

التنفيذ: الصفقة التي يمرّرها الفلتر ⇒ 20$ كاملة (المسطرة، القسم 27).
         الصفقة التي يرفضها الفلتر ⇒ 20$ × النسبة (0.75 / 0.50 / 0.25 / 0.00).
النسبة 0.00 = جولة الفلاتر نفسها (المنع الكامل) — نقطة مرجعية للتحقق.
النسبة 1.00 = المحفظة كما هي.

⚠️ حاجز الدستور §8 محفوظ: لا حصة تتجاوز 20$ أبدًا. التصغير ينزل فقط.
⚠️ لا إعادة اختيار: إعدادات المحفظة مقفلة من إيداعاتها، والمتغيّر هو الحصة وحدها.

    python3 history/hyp_lab/run_l0021_sizing.py
"""
from __future__ import annotations

import json
import os
import pathlib
import platform
import subprocess
import sys
import time

import numpy as np
import pandas as pd

_S = pathlib.Path(os.environ.get("NOVA_SCRATCH", "~/.nova_scratch")).expanduser()
os.environ.setdefault("NOVA_HOME", str(_S / "home"))

HIST = pathlib.Path(__file__).resolve().parents[1]
ROOT = HIST.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import common as C  # noqa: E402
from common import atr, simulate, trade_rows  # noqa: E402
from measure_l0010_gate import drawdown_stats, longest_losing_streak, psr_dsr  # noqa: E402
import run_l0019_unified as R19  # noqa: E402
import run_l0020_filters as F20  # noqa: E402

OUT = HIST / "research" / "hyp_lab_out" / "L0021"
TS, TE = "2025-01-01", "2026-08-31"
BAR = 4 * 3600
YEARS = (pd.Timestamp(TE, tz="UTC") - pd.Timestamp(TS, tz="UTC")).days / 365.25

# نِسَب الحصة حين يرفض الفلتر (1.00 = بلا تغيير · 0.00 = منع كامل)
RATIOS = [1.00, 0.75, 0.50, 0.25, 0.00]


def pf(p: np.ndarray) -> float:
    g, l = p[p > 0].sum(), -p[p < 0].sum()
    return float(g / l) if l > 0 else (np.inf if g > 0 else 0.0)


def regime_ok(df: pd.DataFrame) -> pd.Series:
    """الثلاثي الموثّق من L0020 — نفس المحاور حرفًا، بلا تحريك."""
    ok = pd.Series(True, index=df.index)
    for fn in F20.FILTERS.values():
        ok &= fn(df).reindex(df.index).fillna(False)
    return ok


def run_cell(c: dict, df: pd.DataFrame, ratio: float) -> list[dict]:
    """يشغّل الخلية مرتين: مرّة في الحالة الجيدة بحصة كاملة، ومرّة في السيئة بحصة مصغّرة."""
    win = df[(df.index >= TS) & (df.index <= TE)]
    if c["driver"] == "F_213_breakers":
        import F_213_breakers as M
        sig_full = M.make_signals(df, trigger=c["combo"]["trigger"])
        kw = ({"exit_mode": "dual", "dual": M.make_dual_spec()}
              if c["combo"]["exit"] == "dual" else {"exit_mode": "std"})
    else:
        import F_197_dual_trail as M197
        import run_l0017 as R17
        sig_full = R17.EXPS[c["driver"]].make_signals(df, **c["combo"])
        kw = {"exit_mode": "dual", "dual": M197.make_dual_spec(trig=0.0025, lock=0.0045)}

    ok = regime_ok(df)
    rows: list[dict] = []

    # (أ) الصفقات في الحالة الجيدة — حصة كاملة 20$
    s_good = sig_full.where(ok, 0).loc[win.index]
    _, tr = simulate(win, s_good, atr(win), notional=C.TRADE_USD, bar_secs=BAR, **kw)
    for r in trade_rows(c["symbol"], c["driver"], tr):
        r["driver"] = c["driver"]; r["bucket"] = "جيدة"
        rows.append(r)

    # (ب) الصفقات في الحالة السيئة — حصة مصغّرة
    if ratio > 0:
        s_bad = sig_full.where(~ok, 0).loc[win.index]
        _, tr = simulate(win, s_bad, atr(win), notional=C.TRADE_USD * ratio,
                         bar_secs=BAR, **kw)
        for r in trade_rows(c["symbol"], c["driver"], tr):
            r["driver"] = c["driver"]; r["bucket"] = "سيئة"
            rows.append(r)
    return rows


def block(name: str, d: pd.DataFrame, nt: int) -> dict:
    if d.empty:
        return {"الحصة في الحالة السيئة": name, "صفقات": 0, "صافي$": 0.0}
    d = d.copy()
    d["exit_time"] = pd.to_datetime(d["exit_time"], utc=True)
    d = d.sort_values("exit_time")
    p = d["pnl"].to_numpy(float)
    dd, dys, _ = drawdown_stats(d["exit_time"], p)
    day = d.groupby(d["exit_time"].dt.date)["pnl"].sum()
    z = psr_dsr(p, YEARS, nt)
    w, l = p[p > 0], p[p < 0]
    return {
        "الحصة في الحالة السيئة": name, "صفقات": len(d),
        "صافي$": round(float(p.sum()), 2),
        "عامل الربح": round(pf(p), 4),
        "فوز%": round(100 * float((p > 0).mean()), 2),
        "متوسط الخاسرة$": round(float(l.mean()), 4) if len(l) else 0.0,
        "نسبة العائد": round(float(w.mean() / abs(l.mean())), 4) if len(l) and len(w) else 0.0,
        "أقصى هبوط$": round(dd, 2), "مدة الهبوط(يوم)": round(dys, 1),
        "أسوأ يوم$": round(float(day.min()), 2),
        "أطول سلسلة خسائر": longest_losing_streak(p),
        "DSR": z["dsr"], "z": z["dsr_z"],
    }


def main() -> int:
    t0 = time.time()
    can = subprocess.run([sys.executable, str(ROOT / "tools" / "canary.py"), "--json"],
                         capture_output=True, text=True)
    cj = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
    if cj.get("canary") != "ok":
        print("الكاناري فشل — إيقاف L0021.", file=sys.stderr)
        return 1
    print(f"الكاناري: PASS (net={cj['got']['net']})\n", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.width", 250)

    cells = R19.breaker_cells() + R19.new_cells()
    syms = sorted({c["symbol"] for c in cells})
    print(f"خلايا المحفظة: {len(cells)} على {len(syms)} عملة · نِسَب: {RATIOS}\n", flush=True)

    store: dict[float, list[dict]] = {r: [] for r in RATIOS}
    for s in syms:
        df = R19.frame(s)
        mine = [x for x in cells if x["symbol"] == s]
        for ratio in RATIOS:
            for c in mine:
                store[ratio].extend(run_cell(c, df, ratio))
        print(f"  {s}: تمّت النِسَب الخمس", flush=True)
        del df

    nt = 32 * 13 + (36 + 27) * 8
    rows = []
    for ratio in RATIOS:
        t = pd.DataFrame(store[ratio])
        lbl = "كاملة 20$ (المحفظة كما هي)" if ratio == 1.0 else (
              "صفر (منع كامل — جولة الفلاتر)" if ratio == 0.0 else
              f"{ratio:.2f} ⇒ {C.TRADE_USD*ratio:.0f}$")
        rows.append(block(lbl, t, nt))

    summ = pd.DataFrame(rows)
    base = rows[0]
    summ["فرق الصافي$"] = [round(r["صافي$"] - base["صافي$"], 2) for r in rows]
    summ["فرق الهبوط$"] = [round(r.get("أقصى هبوط$", 0) - base["أقصى هبوط$"], 2) for r in rows]
    summ["ربح لكل دولار خطر"] = (summ["صافي$"] / summ["أقصى هبوط$"]).round(2)
    summ.to_csv(OUT / "sizing_compare_4h.csv", index=False, encoding="utf-8-sig")

    print("\n" + "=" * 135)
    print("تصغير الحصة بدل المنع — المحفظة الموحدة · 4h · مسطرة 20$")
    print("=" * 135)
    print(summ[["الحصة في الحالة السيئة", "صفقات", "صافي$", "فرق الصافي$", "عامل الربح",
                "نسبة العائد", "أقصى هبوط$", "فرق الهبوط$", "أسوأ يوم$",
                "ربح لكل دولار خطر", "DSR"]].to_string(index=False), flush=True)

    # تفصيل: كم يأتي من الحالة الجيدة وكم من السيئة
    det = []
    for ratio in RATIOS:
        t = pd.DataFrame(store[ratio])
        if t.empty:
            continue
        for b in ("جيدة", "سيئة"):
            s = t[t["bucket"] == b]
            if len(s):
                det.append({"النسبة": ratio, "الحالة": b, "صفقات": len(s),
                            "صافي$": round(s["pnl"].sum(), 2),
                            "نصيب الصفقة$": round(s["pnl"].mean(), 4)})
    dd = pd.DataFrame(det)
    dd.to_csv(OUT / "buckets_4h.csv", index=False, encoding="utf-8-sig")
    print("\n— من أين يأتي المال؟ —")
    print(dd.to_string(index=False), flush=True)

    (OUT / "env_dump.txt").write_text(
        f"python={platform.python_version()}\npandas={pd.__version__}\nnumpy={np.__version__}\n"
        f"canary={cj['got']['net']}\nbase_notional={C.TRADE_USD}$\nratios={RATIOS}\n"
        f"window={TS}→{TE}\ncost=0.13%/side\ncells={len(cells)} symbols={len(syms)}\n"
        f"filters=الثلاثي من L0020 بلا تحريك محاور\n"
        f"note=لا حصة تتجاوز 20$ (حاجز §8) — التصغير ينزل فقط\n", encoding="utf-8")

    print(f"\n→ {OUT}\n{time.time()-t0:.1f} ث", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
