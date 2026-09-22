# -*- coding: utf-8 -*-
"""L0019 — المحفظة الموحدة: القواطع القديمة + نجما دفعة الجرد (انحراف الدخول · التنقيط).

السؤال الواحد بلغة المال: هل يضيف السائقان الجديدان دخلاً حقيقياً فوق ما عندنا،
أم يشتريان نفس الشيء في نفس اللحظة فيضاعفان الخطر بلا أن يضاعفا الربح؟

⚠️ تصحيح مسطرة إلزامي (الدستور §27 · D-0044):
  صفقات المحفظة القديمة المودعة مسجلة على **1000$ للصفقة** — وهي مسطرة **ملغاة**.
  صفقات L0017/L0018 مسجلة على **20$** — المسطرة الشرعية.
  جمعهما كما هما = جمع ريال على دولار. لذلك **تُعاد القواطع القديمة تشغيلاً**
  بإعداداتها المقفلة نفسها حرفاً على 20$، فيصير الجمع على مسطرة واحدة.
  لا إعادة اختيار ولا تحريك إعداد: الإعدادات تُقرأ من إيداع L0009-tf4h و L0012.

النطاق: فريم الأربع ساعات · نافذة الامتحان 2025-01-01→2026-08-31 · شراء فقط 🔒
السائقون:
  - القواطع F-213: 13 عملة عابرة (ستة L0010 + سبعة L0013) بإعداداتها المقفلة
  - انحراف الدخول F-192: خلاياه العابرة الخمس من L0017
  - التنقيط التعويضي F-165: خلاياه العابرة الست من L0017

المقاييس: الصافي · عامل الربح · أقصى هبوط ومدته · أسوأ يوم · الترابط اليومي بين
السائقين · التداخل الزمني (هل يشترون معاً؟) · DSR · ومقارنة الاحتفاظ.

    python3 history/hyp_lab/run_l0019_unified.py
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

_SCRATCH = pathlib.Path(os.environ.get("NOVA_SCRATCH", "~/.nova_scratch")).expanduser()
os.environ.setdefault("NOVA_HOME", str(_SCRATCH / "home"))

HIST = pathlib.Path(__file__).resolve().parents[1]
ROOT = HIST.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import common as C  # noqa: E402
from common import load, to_bars, TF_MINUTES, atr, simulate, trade_rows  # noqa: E402
from measure_l0010_gate import drawdown_stats, longest_losing_streak, psr_dsr  # noqa: E402
import F_197_dual_trail as M197  # noqa: E402
import F_213_breakers as M213  # noqa: E402
import run_l0017 as R17  # noqa: E402

O = HIST / "research" / "hyp_lab_out"
OUT = O / "L0019"
TEST_START, TEST_END = "2025-01-01", "2026-08-31"
WARM = "2023-06-01"
TF, BAR_SECS = "4h", 4 * 3600
YEARS = (pd.Timestamp(TEST_END, tz="UTC") - pd.Timestamp(TEST_START, tz="UTC")).days / 365.25

NEW_DRIVERS = ["F_192_ext_entry", "F_165_score_entry"]   # النجمان فقط (حكم L0018)


def pf_of(p: np.ndarray) -> float:
    g, lo = p[p > 0].sum(), -p[p < 0].sum()
    return float(g / lo) if lo > 0 else (np.inf if g > 0 else 0.0)


def breaker_cells() -> list[dict]:
    """الثلاث عشرة عملة العابرة بإعداداتها المقفلة من الإيداع (بلا إعادة اختيار)."""
    cells = []
    for src in (O / "L0009-tf4h" / "F_213" / "all_symbols_test.csv",
                O / "L0012" / "F_213" / "all_symbols_test.csv"):
        if not src.exists():
            continue
        t = pd.read_csv(src, encoding="utf-8-sig")
        for _, r in t[t["gate"] == True].iterrows():          # noqa: E712
            cells.append({"driver": "F_213_breakers", "symbol": r["symbol"],
                          "combo": {"exit": str(r["sel_NOVA_EXIT"]),
                                    "trigger": str(r["sel_NOVA_TRIGGER"])},
                          "dep_net_1000": float(r["test_net"])})
    # إزالة التكرار إن وُجد رمز في الإيداعين
    seen, out = set(), []
    for c in cells:
        if c["symbol"] not in seen:
            seen.add(c["symbol"])
            out.append(c)
    return out


def new_cells() -> list[dict]:
    cells = []
    base = O / "L0017-tf4h"
    for exp in NEW_DRIVERS:
        f = base / exp / "all_symbols_test.csv"
        if not f.exists():
            continue
        t = pd.read_csv(f, encoding="utf-8-sig")
        for _, r in t[t["gate"] == True].iterrows():          # noqa: E712
            keys = list(R17.EXPS[exp].SWEEP_PARAMS.keys())
            combo = {}
            for k in keys:
                ref = R17.EXPS[exp].SWEEP_PARAMS[k][0]
                v = r[f"sel_NOVA_{k.upper()}"]
                combo[k] = int(v) if isinstance(ref, int) else float(v)
            cells.append({"driver": exp, "symbol": r["symbol"], "combo": combo,
                          "dep_net_20": float(r["test_net"])})
    return cells


def frame(sym: str) -> pd.DataFrame:
    p = ROOT / "crypto_archive" / f"{sym}_1m.parquet"
    return to_bars(load(str(p), start=WARM, end=TEST_END), TF_MINUTES[TF])


def run_cell(c: dict, df: pd.DataFrame) -> list[dict]:
    win = df[(df.index >= TEST_START) & (df.index <= TEST_END)]
    if c["driver"] == "F_213_breakers":
        sig = M213.make_signals(df, trigger=c["combo"]["trigger"]).loc[win.index]
        kw = ({"exit_mode": "dual", "dual": M213.make_dual_spec()}
              if c["combo"]["exit"] == "dual" else {"exit_mode": "std"})
    else:
        sig = R17.EXPS[c["driver"]].make_signals(df, **c["combo"]).loc[win.index]
        kw = {"exit_mode": "dual",
              "dual": M197.make_dual_spec(trig=0.0025, lock=0.0045)}
    st, tr = simulate(win, sig, atr(win), notional=C.TRADE_USD, bar_secs=BAR_SECS, **kw)
    rows = trade_rows(c["symbol"], c["driver"], tr)
    for r in rows:
        r["driver"] = c["driver"]
    return rows


def block(name: str, d: pd.DataFrame, n_trials: int) -> dict:
    d = d.copy()
    d["exit_time"] = pd.to_datetime(d["exit_time"], utc=True)
    d = d.sort_values("exit_time")
    p = d["pnl"].to_numpy(float)
    dd, dd_days, _ = drawdown_stats(d["exit_time"], p)
    day = d.groupby(d["exit_time"].dt.date)["pnl"].sum()
    r = {"المحفظة": name, "عملات": int(d["symbol"].nunique()), "صفقات": len(d),
         "صافي$": round(float(p.sum()), 2),
         "عامل الربح": round(pf_of(p), 4),
         "فوز%": round(100 * float((p > 0).mean()), 2),
         "نصيب الصفقة$": round(float(p.sum() / len(d)), 4),
         "أقصى هبوط$": round(dd, 2), "مدة الهبوط(يوم)": round(dd_days, 1),
         "أسوأ يوم$": round(float(day.min()), 2),
         "أطول سلسلة خسائر": longest_losing_streak(p),
         "عمولات$": round(2 * 0.0013 * C.TRADE_USD * len(d), 2)}
    z = psr_dsr(p, YEARS, n_trials)
    r["DSR"] = z["dsr"]; r["z"] = z["dsr_z"]
    return r


def main() -> int:
    t0 = time.time()
    can = subprocess.run([sys.executable, str(ROOT / "tools" / "canary.py"), "--json"],
                         capture_output=True, text=True)
    cj = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
    if cj.get("canary") != "ok":
        print("الكاناري فشل — إيقاف L0019.", file=sys.stderr)
        return 1
    print(f"الكاناري: PASS (net={cj['got']['net']})\n", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.width", 250)

    cells = breaker_cells() + new_cells()
    syms = sorted({c["symbol"] for c in cells})
    print(f"السائقون: القواطع {sum(1 for c in cells if c['driver']=='F_213_breakers')} عملة · "
          f"انحراف الدخول {sum(1 for c in cells if c['driver']=='F_192_ext_entry')} · "
          f"التنقيط {sum(1 for c in cells if c['driver']=='F_165_score_entry')}")
    print(f"عملات فريدة: {len(syms)}\n", flush=True)

    allr = []
    for sym in syms:
        df = frame(sym)
        for c in [x for x in cells if x["symbol"] == sym]:
            rows = run_cell(c, df)
            allr.extend(rows)
            note = ""
            if c["driver"] == "F_213_breakers":
                note = f" | إيداع على مسطرة ملغاة {c['dep_net_1000']:.2f}$ ⇒ ×0.02 = {c['dep_net_1000']*0.02:.2f}$"
            print(f"  {c['driver']}/{sym}: {len(rows)} صفقة · "
                  f"صافٍ {sum(r['pnl'] for r in rows):.2f}${note}", flush=True)
        del df

    t = pd.DataFrame(allr)
    t.to_csv(OUT / "trades_all_4h.csv", index=False, encoding="utf-8-sig")

    n_old = sum(1 for c in cells if c["driver"] == "F_213_breakers")
    n_new = len(cells) - n_old
    rows = [
        block("القديمة وحدها (القواطع 13)", t[t["driver"] == "F_213_breakers"], 32 * n_old),
        block("الجديدان وحدهما", t[t["driver"].isin(NEW_DRIVERS)], (36 + 27) * 8),
        block("الموحدة (القديم + الجديد)", t, 32 * n_old + (36 + 27) * 8),
    ]
    for d_ in NEW_DRIVERS:
        rows.append(block(f"— {d_} وحده", t[t["driver"] == d_],
                          len(R17.combos_for(d_)) * 8))
    summ = pd.DataFrame(rows)
    summ.to_csv(OUT / "portfolio_compare_4h.csv", index=False, encoding="utf-8-sig")

    print("\n" + "=" * 110)
    print("مقارنة المحافظ — كلها على المسطرة الشرعية 20$/صفقة")
    print("=" * 110)
    print(summ.to_string(index=False), flush=True)

    # الترابط اليومي بين السائقين الثلاثة
    t["exit_time"] = pd.to_datetime(t["exit_time"], utc=True)
    daily = t.assign(day=t["exit_time"].dt.date).groupby(["day", "driver"])["pnl"].sum().unstack(fill_value=0.0)
    corr = daily.corr().round(4)
    corr.to_csv(OUT / "corr_drivers_4h.csv", encoding="utf-8-sig")
    print("\n— الترابط اليومي بين السائقين (0 = مستقلان · 1 = توأمان) —")
    print(corr.to_string(), flush=True)

    # التداخل الزمني: هل يشترون في نفس اليوم؟
    days_by = {d_: set(t[t["driver"] == d_]["exit_time"].dt.date) for d_ in t["driver"].unique()}
    ov = []
    ks = list(days_by)
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            a, b = days_by[ks[i]], days_by[ks[j]]
            ov.append({"أ": ks[i], "ب": ks[j], "أيام أ": len(a), "أيام ب": len(b),
                       "أيام مشتركة": len(a & b),
                       "تداخل%": round(100 * len(a & b) / len(a | b), 1)})
    ovd = pd.DataFrame(ov)
    ovd.to_csv(OUT / "overlap_days_4h.csv", index=False, encoding="utf-8-sig")
    print("\n— التداخل الزمني (هل يشترون في نفس الأيام؟) —")
    print(ovd.to_string(index=False), flush=True)

    (OUT / "env_dump.txt").write_text(
        f"python={platform.python_version()}\npandas={pd.__version__}\nnumpy={np.__version__}\n"
        f"canary={cj['got']['net']}\nbar={TF}\nnotional={C.TRADE_USD}$ (الدستور §27)\n"
        f"window={TEST_START}→{TEST_END}\ncost=0.13%/side\n"
        f"breaker_cells={n_old} (أعيد تشغيلها على 20$ — إيداعها كان على 1000$ الملغاة)\n"
        f"new_cells={n_new} (النجمان بحكم L0018)\n"
        f"locked=إعدادات مقروءة من الإيداع بلا إعادة اختيار\n", encoding="utf-8")

    print(f"\n→ {OUT}\nالكل: {time.time()-t0:.1f} ث", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
