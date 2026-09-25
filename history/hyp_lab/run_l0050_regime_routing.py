# -*- coding: utf-8 -*-
"""L0050 — هل يربح البوت لو شُغّل كل عمود في مناخه فقط؟

قياس وحكم فقط. لا تحسين. لا لمس لإشارة أو لخروج أو لـ nova_v8.
مصنّف المناخ يومي كما في الورقة، مع shift(1). لا يُستعمل nova_v8/regime.py.

خريطة الإسناد تُشتق من فترة الاختيار وحدها، عند 0.13% للطرف،
وتُكتب في routing_map.json قبل أي قياس حكم.
القاعدة مكتوبة هنا ولا تتغير:
    يُشغَّل العمود في المناخ إذا كان صافي الاختيار > 0 وعدد الصفقات ≥ 30.

السقف 35. شبكة مُعلَنة قبل أي رقم حكم:
    مرحلة 1 (21): 7 أعمدة × 3 مناخات على الاختيار فقط.
    ثم الخريطة تُجمَّد.
    مرحلة 2 (12): المسنَدة × فترتين + 5 بذور × فترتين.
        سقف المرحلة 2 في الورقة (8) لا يتسع لخمس بذور × فترتين.
        البذور لا تُقطع. المحفظة بلا إسناد عند 0.13% تُعاد في المرحلة 0
        (رقم منشور) ولا تُحسب قياسًا جديدًا.
    مرحلة 3 (2): الشراء والاحتفاظ × فترتين.
    المجموع 35.
    تفكيك المناخ، والصفقات المحذوفة، ونسبة الوقت العاطل: من ملفات مقيسة،
    ليست قياسات جديدة.

المناخ يُقرأ عند شمعة الدخول (الإشارة على i، الدخول على i+1) ويثبت للصفقة.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import platform
import subprocess
import sys
import time

import numpy as np
import pandas as pd

ROOT = pathlib.Path("/home/user/nova")
os.environ.setdefault("NOVA_SCRATCH", "/home/user/.nova_scratch")
os.environ.setdefault("NOVA_HOME", "/home/user/.nova_scratch/home")
sys.path.insert(0, str(ROOT / "history" / "hyp_lab"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

import run_l0046_basis_repair as R46
import run_l0048_entry_value as R48
import run_l0036_more as L36
import nova_v8.config as NC
import F_213_breakers as M213
import common as C
import position_sequencing_audit as psa

R46.ROOT = ROOT
R48.ROOT = ROOT

OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0050"
OUT.mkdir(parents=True, exist_ok=True)
DAILY = pathlib.Path.home() / ".cache" / "l0050_daily"
DAILY.mkdir(parents=True, exist_ok=True)

DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
WARM = "2021-06-01"
SEEDS = (110050, 210050, 310050, 410050, 510050)
CAP = 35
DEFAULT_COST = 0.0013
REAL_COST = 0.0013
STOP = 2.5
TRAIL = 4.0
BAR = 4 * 3600
MIN_TRADES = 30
REGIMES = ("صاعد", "عرضي", "هابط")

P0_ZERO = {"SEL": (67.80, 1053), "JUD": (-64.88, 1779)}
P0_REAL = {"SEL": (10.76, 1067), "JUD": (-154.84, 1791)}

# جدول الورقة بكلفة صفر. للتحقق فقط. لا يُستخدم في الإسناد.
PAPER_BOOK = {
    "SEL": {"صاعد": 98.63, "عرضي": -86.02, "هابط": 55.19},
    "JUD": {"صاعد": -72.44, "عرضي": -91.67, "هابط": 99.22},
}
PAPER_COL = {
    "كاسرة النطاق": {"صاعد": (99.2, -87.0), "عرضي": (-82.9, -114.5), "هابط": (30.5, 73.1)},
    "انحراف الدخول": {"صاعد": (10.6, -9.7), "عرضي": (-12.9, -5.1), "هابط": (-24.5, -6.0)},
    "التنقيط التعويضي": {"صاعد": (9.8, 10.5), "عرضي": (-3.9, -5.1), "هابط": (-15.5, -6.6)},
    "دونشيان": {"صاعد": (13.0, -0.3), "عرضي": (-30.3, -47.2), "هابط": (-30.7, 46.3)},
    "ماكد": {"صاعد": (-1.2, -108.4), "عرضي": (-96.7, -93.5), "هابط": (49.4, 41.8)},
    "بولنجر": {"صاعد": (28.6, -101.9), "عرضي": (-104.1, -105.1), "هابط": (49.3, 88.0)},
    "سناب المؤشر": {"صاعد": (64.1, 17.3), "عرضي": (0.8, -19.0), "هابط": (18.0, -12.3)},
}

L0048_COINS = {
    "ATOMUSDT", "BTCUSDT", "DOGEUSDT", "ETHUSDT", "FILUSDT", "GRAMUSDT",
    "IMXUSDT", "LINKUSDT", "PEPEUSDT", "RENDERUSDT", "SHIBUSDT", "SOLUSDT",
    "TONUSDT", "VETUSDT", "XLMUSDT",
}

LEDGER: list[dict] = []
MEASURED: list[dict] = []
REG4H: dict[str, pd.Series] = {}
SYMS: list[str] = []


def log_measurement(name: str, window: str, extra: dict | None = None) -> int:
    if len(LEDGER) >= CAP:
        raise SystemExit(f"تجاوز السقف: محاولة تسجيل قياس بعد {CAP}")
    row = {"#": len(LEDGER) + 1, "القياس": name, "الفترة": window}
    if extra:
        row.update(extra)
    LEDGER.append(row)
    return row["#"]


def set_cost(cost: float) -> None:
    C.COST_PER_SIDE = float(cost)
    R48.COST = float(cost)


def restore_cost() -> None:
    set_cost(DEFAULT_COST)


def summarize(rows: list[dict], cost: float) -> dict:
    if not rows:
        return {"net": 0.0, "trades": 0, "per": 0.0, "gross": 0.0, "costs": 0.0,
                "median_hold": 0.0, "overlap_ratio": 0.0, "max_concurrent": 0,
                "overlapping_trades": 0}
    t = pd.DataFrame(rows)
    p = t["pnl"].to_numpy(float)
    net = round(float(p.sum()), 2)
    qty = t["notional"].to_numpy(float) / t["entry"].to_numpy(float)
    entry = t["entry"].to_numpy(float)
    exit_ = t["exit"].to_numpy(float)
    costs = float((qty * cost * (entry + exit_)).sum())
    gross = round(float((qty * (exit_ - entry)).sum() + costs), 2)
    hold = t["bars_held"].to_numpy(float)
    au = psa.audit_frame(t)
    n = len(t)
    return {
        "net": net, "trades": int(n),
        "per": round(net / n, 5) if n else 0.0,
        "gross": gross, "costs": round(costs, 2),
        "median_hold": float(np.median(hold)) if n else 0.0,
        "overlap_ratio": au["overlap_ratio"],
        "max_concurrent": au["max_concurrent"],
        "overlapping_trades": au["overlapping_trades"],
    }


def save_trades(name: str, rows: list[dict]) -> pathlib.Path:
    path = OUT / f"trades_{name}.csv"
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def tag_regime(rows: list[dict]) -> list[dict]:
    for r in rows:
        ts = pd.Timestamp(r["entry_time"])
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        series = REG4H[r["symbol"]]
        val = series.get(ts, np.nan) if ts in series.index else np.nan
        r["regime"] = val if isinstance(val, str) else "غير مصنّف"
    return rows


def record(name: str, window: str, rows: list[dict], cost: float, seed, counted: bool,
           extra: dict | None = None) -> dict:
    st = summarize(rows, cost)
    if st["overlapping_trades"] != 0:
        save_trades(name + "_OVERLAP", rows)
        raise SystemExit(f"تداخل ≠ 0 في {name} {window}: {st}")
    rec = {"القياس": name, "الفترة": window, "counted": counted, "cost": cost,
           "seed": seed, **st}
    if extra:
        rec.update(extra)
    if counted:
        log_measurement(name, window, {"cost": cost, "seed": seed})
        MEASURED.append(rec)
    tag = f"{len(LEDGER)}/{CAP}" if counted else "مرحلة0"
    print(f"  [{tag}] {name} {window}: net={st['net']} صفقات={st['trades']} "
          f"للصفقة={st['per']} إجمالي={st['gross']} كلفة={st['costs']} "
          f"وسيط={st['median_hold']}", flush=True)
    return rec


def run_canary() -> dict:
    can = subprocess.run([sys.executable, str(ROOT / "tools" / "canary.py"), "--json"],
                         capture_output=True, text=True)
    raw = can.stdout
    cj = json.loads(raw[raw.index("{"):]) if "{" in raw else {}
    print(f"  كاناري المحرك الحي: {cj.get('canary')} net={cj.get('got', {}).get('net')}")
    if cj.get("canary") != "ok":
        print(can.stdout[-1500:])
        print(can.stderr[-800:])
        raise SystemExit("الكاناري لم يُرجع canary=ok — أوقف")
    return cj


def run_selftests() -> None:
    for tool in ("fill_invariant_check.py", "position_sequencing_audit.py"):
        st = subprocess.run([sys.executable, str(ROOT / "tools" / tool), "--selftest"],
                            capture_output=True, text=True)
        tail = (st.stdout or st.stderr).strip().splitlines()
        print(f"  {tool}: {(tail[-1] if tail else 'بلا مخرج')} (exit={st.returncode})")
        if st.returncode != 0:
            raise SystemExit(f"{tool} selftest فشل — أوقف")


def lab_canary_status() -> str:
    csv = ROOT / "history" / "research" / "hyp_lab_out" / "L0046" / "phase3_basis_repaired.csv"
    if not csv.exists():
        msg = "لم يُشغَّل: phase3_basis_repaired.csv غير موجود في المستودع. لم يُصنَّع بديل."
        print(f"  كاناري المختبر: {msg}")
        return msg
    st = subprocess.run([sys.executable, str(ROOT / "tools" / "canary_lab.py"), "--json"],
                        capture_output=True, text=True)
    print(st.stdout.strip() or st.stderr[-400:])
    return st.stdout.strip()


def prepare() -> list[str]:
    global SYMS
    L36.set_core()
    NC.EMA_FAST = 8
    M213._cache.clear()
    R48._SIG.clear()
    C.STOP_ATR = STOP
    restore_cost()
    if abs(C.COST_PER_SIDE - DEFAULT_COST) > 1e-15:
        raise SystemExit("كلفة الافتراضي في الذاكرة ليست 0.0013")
    cells = R48._cells()
    SYMS = sorted({c["symbol"] for c in cells})
    R48.SYMS = SYMS
    R48.BAR = BAR
    R48.frames = R46.frames
    print(f"  خلايا={len(cells)} عملات={len(SYMS)}: {', '.join(SYMS)}")
    if set(SYMS) != L0048_COINS:
        raise SystemExit(f"سلة العملات تختلف عن L0048: {sorted(set(SYMS) ^ L0048_COINS)}")
    R46.build_cache(SYMS)
    return SYMS


def build_regimes() -> None:
    """المصنّف الحرفي من الورقة. shift(1) إلزامي. لكل عملة على حدتها."""
    print("\n══ مصنّف المناخ اليومي (shift 1) ══")
    for sym in SYMS:
        path = DAILY / f"{sym}_1d.parquet"
        if not path.exists():
            t0 = time.time()
            d1 = C.load(str(ROOT / "crypto_archive" / f"{sym}_1m.parquet"),
                        start=WARM, end=JUD_E)
            C.to_bars(d1, 1440).to_parquet(path)
            del d1
            print(f"  يومي {sym} ({time.time()-t0:.1f}s)", flush=True)
        dly = pd.read_parquet(path)
        if dly.index.tz is None:
            dly.index = dly.index.tz_localize("UTC")
        if dly.index.min().hour != 0 or dly.index.min().minute != 0:
            raise SystemExit(f"شمعة اليوم ليست على منتصف الليل: {sym} {dly.index.min()}")
        c = dly["close"]
        e50 = c.ewm(span=50, adjust=False).mean()
        e200 = c.ewm(span=200, adjust=False).mean()
        slope = e50.diff(10)
        raw = pd.Series("عرضي", index=dly.index)
        raw[(e50 > e200) & (slope > 0)] = "صاعد"
        raw[(e50 < e200) & (slope < 0)] = "هابط"
        lab = raw.shift(1)
        # إثبات الإزاحة: تسمية اليوم = خام الأمس، لا خام اليوم.
        if not (lab.iloc[1:] .reset_index(drop=True).equals(raw.iloc[:-1].reset_index(drop=True))):
            raise SystemExit("shift(1) لم يُطبَّق كما كُتب")
        f = R46.frames(sym)
        lookup = {ts.normalize(): val for ts, val in lab.items()}
        mapped = pd.Series(
            [lookup.get(ts.normalize(), np.nan) for ts in f.index],
            index=f.index, dtype=object)
        REG4H[sym] = mapped
    btc = REG4H["BTCUSDT"]
    vc = btc.dropna().astype(str).value_counts()
    print(f"  BTC 4h بعد الإزاحة: {vc.to_dict()}  غير مصنّف={int(btc.isna().sum())}")
    # لا استشراف: تسمية يوم D لا تعتمد على إغلاق D. فُحص بالمساواة مع خام D-1.


def entry_regime(sym: str, index: pd.DatetimeIndex) -> pd.Series:
    """مناخ شمعة الدخول: الإشارة على i تدخل على i+1."""
    reg = REG4H[sym].reindex(index)
    return reg.shift(-1)


def simulate_mask(sig_of, s0: str, s1: str, exp: str) -> list[dict]:
    old = C.STOP_ATR
    C.STOP_ATR = STOP
    rows = []
    try:
        for sym in SYMS:
            df = R46.frames(sym)
            win = R48.window(df, s0, s1)
            if len(win) < 100:
                continue
            sg = sig_of(df, sym).reindex(win.index, fill_value=False).fillna(False).astype(bool)
            _, tr = C.simulate(win, sg, C.atr(win), notional=C.TRADE_USD, bar_secs=BAR,
                               strict_single=True, atr_trail=TRAIL)
            rows.extend(C.trade_rows(sym, exp, tr))
    finally:
        C.STOP_ATR = old
    return tag_regime(rows)


def portfolio_signal(df, sym):
    return R48.portfolio_signal(df, sym)


def column_regime_signal(col: str, regime: str):
    def sig_of(df, sym):
        sg = R48.column_signal(df, sym, col).reindex(df.index, fill_value=False).fillna(False).astype(bool)
        er = entry_regime(sym, df.index)
        return sg & (er == regime)
    return sig_of


def routed_signal_factory(enabled: set[tuple[str, str]]):
    def sig_of(df, sym):
        sig = pd.Series(False, index=df.index)
        er = entry_regime(sym, df.index)
        for col, regime in enabled:
            sg = R48.column_signal(df, sym, col).reindex(df.index, fill_value=False).fillna(False).astype(bool)
            sig = sig | (sg & (er == regime))
        return sig
    return sig_of


def split_by_regime(rows: list[dict]) -> dict[str, dict]:
    out = {}
    for reg in list(REGIMES) + ["غير مصنّف"]:
        part = [r for r in rows if r.get("regime") == reg]
        st = summarize(part, C.COST_PER_SIDE)
        out[reg] = st
    return out


def phase0() -> dict:
    print("\n══ مرحلة 0: أساس كلفة صفر (لا تُحسب) ══")
    set_cost(0.0)
    books = {}
    for lbl, s0, s1 in (("SEL", DEC_S, DEC_E), ("JUD", JUD_S, JUD_E)):
        rows = simulate_mask(portfolio_signal, s0, s1, "zero")
        save_trades(f"phase0_zero_{lbl}", rows)
        st = summarize(rows, 0.0)
        exp_net, exp_n = P0_ZERO[lbl]
        print(f"  صفر {lbl}: {st['net']}$ / {st['trades']}  مرجع {exp_net}$ / {exp_n}")
        if abs(st["net"] - exp_net) > 0.5 or st["trades"] != exp_n:
            raise SystemExit("أساس L0049 بكلفة صفر لم يُطابق. أوقف. لا قياس.")
        if st["overlapping_trades"] != 0:
            raise SystemExit("تداخل في أساس الكلفة الصفرية")
        books[lbl] = rows

    print("  تفكيك المحفظة حسب مناخ الدخول (تحقق من جدول الورقة)")
    book_cmp = []
    book_fail = False
    for lbl in ("SEL", "JUD"):
        parts = split_by_regime(books[lbl])
        for reg in REGIMES:
            got = parts[reg]["net"]
            exp = PAPER_BOOK[lbl][reg]
            d = round(got - exp, 2)
            ok = abs(got - exp) <= 0.02
            book_fail = book_fail or not ok
            book_cmp.append({"البند": "محفظة", "الفترة": lbl, "المناخ": reg,
                             "مقيس": got, "الورقة": exp, "الفرق": d, "صفقات": parts[reg]["trades"],
                             "غير_مصنف_صافي": parts["غير مصنّف"]["net"]})
            print(f"    {lbl} {reg}: {got} مقابل {exp} فرق={d} صفقات={parts[reg]['trades']}")
        unk = parts["غير مصنّف"]
        if unk["trades"]:
            print(f"    {lbl} غير مصنّف: {unk['net']}$ / {unk['trades']}")
            if abs(unk["net"]) > 0.5:
                book_fail = True
    pd.DataFrame(book_cmp).to_csv(OUT / "phase0_book_regime.csv", index=False, encoding="utf-8-sig")

    print("  أعمدة × مناخ بكلفة صفر (تشغيل مفلتر، تحقق، لا يُحسب)")
    col_cmp = []
    col_fail = False
    for col in R48.COL_ORDER:
        for reg in REGIMES:
            got = {}
            for lbl, s0, s1 in (("SEL", DEC_S, DEC_E), ("JUD", JUD_S, JUD_E)):
                rows = simulate_mask(column_regime_signal(col, reg), s0, s1, f"{col}-{reg}")
                bad = [r for r in rows if r.get("regime") != reg]
                if bad:
                    raise SystemExit(f"وسم الدخول لا يطابق المرشح: {col} {reg} {len(bad)}")
                st = summarize(rows, 0.0)
                got[lbl] = st["net"]
                side = 0 if lbl == "SEL" else 1
                exp = PAPER_COL[col][reg][side]
                d = round(st["net"] - exp, 2)
                ok = abs(st["net"] - exp) <= 0.06
                col_fail = col_fail or not ok
                col_cmp.append({"العمود": col, "المناخ": reg, "الفترة": lbl,
                                "مقيس": st["net"], "الورقة": exp, "الفرق": d,
                                "صفقات": st["trades"]})
            print(f"    {col} {reg}: اختيار {got['SEL']} / حكم {got['JUD']}", flush=True)
    pd.DataFrame(col_cmp).to_csv(OUT / "phase0_column_regime.csv", index=False, encoding="utf-8-sig")

    print("\n══ مرحلة 0ب: إعادة إنتاج 0.13% بلا إسناد (لا تُحسب) ══")
    set_cost(REAL_COST)
    real = {}
    for lbl, s0, s1 in (("SEL", DEC_S, DEC_E), ("JUD", JUD_S, JUD_E)):
        rows = simulate_mask(portfolio_signal, s0, s1, "unrouted")
        save_trades(f"phase0_real_{lbl}", rows)
        st = summarize(rows, REAL_COST)
        exp_net, exp_n = P0_REAL[lbl]
        print(f"  0.13% {lbl}: {st['net']}$ / {st['trades']}  مرجع {exp_net}$ / {exp_n}")
        if abs(st["net"] - exp_net) > 0.5 or st["trades"] != exp_n:
            raise SystemExit("أساس 0.13% لم يُطابق L0048/L0049. أوقف.")
        real[lbl] = rows

    if book_fail or col_fail:
        (OUT / "STOP.txt").write_text(
            "جدول الورقة للمناخ لم يطابق المصنّف الحرفي عند الدخول.\n"
            f"محفظة_فشلت={book_fail} أعمدة_فشلت={col_fail}\n"
            "لا إسناد. لا قياس محسوب.\n", encoding="utf-8")
        raise SystemExit("جدول المناخ في الورقة خالف الواقع. أوقف. لا إسناد.")
    print("  ✅ جدول الورقة طابق المصنّف الحرفي")
    return {"zero": books, "real": real}


def phase1() -> list[dict]:
    print("\n══ مرحلة 1: 7×3 على الاختيار فقط، كلفة 0.13% ══")
    set_cost(REAL_COST)
    cells = []
    for col in R48.COL_ORDER:
        for reg in REGIMES:
            rows = simulate_mask(column_regime_signal(col, reg), DEC_S, DEC_E, f"{col}-{reg}")
            bad = [r for r in rows if r.get("regime") != reg]
            if bad:
                raise SystemExit(f"وسم لا يطابق المرشح في المرحلة 1: {col} {reg}")
            code = {"صاعد": "up", "عرضي": "side", "هابط": "down"}[reg]
            save_trades(f"p1_{R48.COL_ORDER.index(col)}_{code}_SEL", rows)
            st = record(f"عمود {col} · {reg}", "اختيار", rows, REAL_COST, None, True,
                        {"column": col, "regime": reg})
            cells.append({"column": col, "regime": reg, "net": st["net"], "trades": st["trades"],
                          "per": st["per"], "gross": st["gross"], "costs": st["costs"],
                          "median_hold": st["median_hold"]})
    return cells


def write_map(cells: list[dict]) -> dict:
    enabled = []
    for c in cells:
        c["enabled"] = bool(c["net"] > 0 and c["trades"] >= MIN_TRADES)
        if c["enabled"]:
            enabled.append([c["column"], c["regime"]])
    payload = {
        "rule": "صافي الاختيار > 0 وعدد الصفقات ≥ 30، كلفة 0.0013، فترة الاختيار فقط",
        "cost": REAL_COST,
        "min_trades": MIN_TRADES,
        "period": [DEC_S, DEC_E],
        "cells": cells,
        "enabled": enabled,
        "written_before_judgement_measurement": True,
    }
    path = OUT / "routing_map.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n══ خريطة الإسناد كُتبت قبل الحكم: {len(enabled)} تركيبات ══")
    for col, reg in enabled:
        print(f"    تشغيل: {col} · {reg}")
    if not enabled:
        print("    لا تركيب نجا. المسنَدة ستكون فارغة. لا أغيّر القاعدة.")
    return payload


def targets_of(rows: list[dict]) -> dict[str, int]:
    t = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["symbol"])
    return {sym: int((t["symbol"] == sym).sum()) if len(t) else 0 for sym in SYMS}


def build_outcomes(s0: str, s1: str) -> dict:
    outs = {}
    for sym in SYMS:
        win = R48.window(R46.frames(sym), s0, s1)
        if len(win) < 100:
            continue
        outs[sym] = R48.outcomes_for(sym, s0, s1)
    return outs


def cache_rows(sig_of, outs, s0, s1) -> list[dict]:
    rows = []
    for sym, table in outs.items():
        df = R46.frames(sym)
        win = R48.window(df, s0, s1)
        sg = sig_of(df, sym).reindex(win.index, fill_value=False).fillna(False).astype(bool).to_numpy()
        rows.extend(R48.rows_from_chosen(sym, "cache", R48.greedy(table, sg)))
    return tag_regime(rows)


def random_rows(outs, seed: int, target: dict[str, int]) -> list[dict]:
    rows = []
    for sym, table in outs.items():
        u = R48.uniforms(seed, sym, len(table))
        p = R48.match_p(table, u, target.get(sym, 0))
        rows.extend(R48.rows_from_chosen(sym, f"rnd{seed}", R48.greedy(table, u < p)))
    return tag_regime(rows)


def assert_equiv(name, direct, cached) -> None:
    ds, cs = summarize(direct, REAL_COST), summarize(cached, REAL_COST)
    if abs(ds["net"] - cs["net"]) > 0.01 or ds["trades"] != cs["trades"]:
        raise SystemExit(f"تكافؤ الجدول فشل عند {name}: مباشر {ds} ≠ جدول {cs}")
    print(f"  ✅ تكافؤ {name}: {ds['net']}$ / {ds['trades']}")


def phase2(enabled: set[tuple[str, str]]) -> dict:
    print("\n══ مرحلة 2: المسنَدة + البذور، الفترتان ══")
    set_cost(REAL_COST)
    sig = routed_signal_factory(enabled)
    out = {}
    for lbl, s0, s1, wname in (
        ("SEL", DEC_S, DEC_E, "اختيار"),
        ("JUD", JUD_S, JUD_E, "حكم"),
    ):
        rows = simulate_mask(sig, s0, s1, "routed")
        save_trades(f"routed_{lbl}", rows)
        record("المحفظة المسنَدة", wname, rows, REAL_COST, None, True)
        outs = build_outcomes(s0, s1)
        cached = cache_rows(sig, outs, s0, s1)
        assert_equiv(f"routed-{lbl}", rows, cached)
        tgt = targets_of(rows)
        for seed in SEEDS:
            rrows = random_rows(outs, seed, tgt)
            save_trades(f"routed_s{seed}_{lbl}", rrows)
            record(f"عشوائي مسنَد بذرة {seed}", wname, rrows, REAL_COST, seed, True)
        out[lbl] = rows
    return out


def phase3_buyhold() -> None:
    print("\n══ مرحلة 3: الشراء والاحتفاظ ══")
    set_cost(REAL_COST)
    for lbl, s0, s1, wname in (
        ("SEL", DEC_S, DEC_E, "اختيار"),
        ("JUD", JUD_S, JUD_E, "حكم"),
    ):
        rows = []
        for sym in SYMS:
            w = R48.window(R46.frames(sym), s0, s1)
            if len(w) < 2:
                continue
            e = float(w["open"].iloc[0]) * (1 + REAL_COST)
            x = float(w["close"].iloc[-1]) * (1 - REAL_COST)
            pnl = C.TRADE_USD * (x / e - 1.0)
            rows.append({
                "symbol": sym, "exp": "buyhold",
                "entry_time": w.index[0].isoformat(),
                "exit_time": w.index[-1].isoformat(),
                "entry": float(f"{e:.12g}"),
                "exit": float(f"{x:.12g}"),
                "notional": C.TRADE_USD,
                "pnl": round(pnl, 4),
                "bars_held": int(len(w) - 1),
                "exit_side": "eod",
                "regime": "",
            })
        save_trades(f"buyhold_{lbl}", rows)
        record("الشراء والاحتفاظ", wname, rows, REAL_COST, None, True)


def decompositions(routed: dict, real: dict, mp: dict) -> None:
    enabled_regs = {reg for _, reg in mp["enabled"]}
    idle_rows = []
    for lbl, s0, s1 in (("SEL", DEC_S, DEC_E), ("JUD", JUD_S, JUD_E)):
        total = side = blocked = labeled = 0
        for sym in SYMS:
            win = R48.window(R46.frames(sym), s0, s1)
            reg = REG4H[sym].reindex(win.index)
            known = reg.dropna()
            labeled += int(len(known))
            total += int(len(reg))
            side += int((known == "عرضي").sum())
            blocked += int((~known.isin(list(enabled_regs))).sum()) if enabled_regs else int(len(known))
        idle_rows.append({
            "الفترة": lbl, "شموع": total, "مصنّف": labeled,
            "عرضي": side, "نسبة_العرضي": round(side / labeled, 4) if labeled else None,
            "ممنوع_الدخول": blocked,
            "نسبة_بلا_دخول": round(blocked / labeled, 4) if labeled else None,
            "مناخات_فيها_عمود": sorted(enabled_regs),
        })
    pd.DataFrame(idle_rows).to_csv(OUT / "idle_time.csv", index=False, encoding="utf-8-sig")
    print("  وقت بلا دخول جديد:", idle_rows)

    contrib = []
    deleted = []
    for lbl in ("SEL", "JUD"):
        rt = routed[lbl]
        for reg in list(REGIMES) + ["غير مصنّف"]:
            part = [r for r in rt if r.get("regime") == reg]
            st = summarize(part, REAL_COST)
            contrib.append({"الفترة": lbl, "المناخ": reg, **st})
        un = real[lbl]
        un_keys = {(r["symbol"], r["entry_time"]): r for r in un}
        rt_keys = {(r["symbol"], r["entry_time"]): r for r in rt}
        gone = [un_keys[k] for k in un_keys.keys() - rt_keys.keys()]
        added = [rt_keys[k] for k in rt_keys.keys() - un_keys.keys()]
        gs, ad = summarize(gone, REAL_COST), summarize(added, REAL_COST)
        deleted.append({"الفترة": lbl, "حُذفت": gs["trades"], "صافي_المحذوف": gs["net"],
                        "إجمالي_المحذوف": gs["gross"], "ظهرت_بسبب_الإسناد": ad["trades"],
                        "صافي_الظاهر": ad["net"]})
        print(f"  {lbl}: حُذفت {gs['trades']} صافيها {gs['net']} | ظهرت {ad['trades']} صافيها {ad['net']}")
    pd.DataFrame(contrib).to_csv(OUT / "regime_contribution.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(deleted).to_csv(OUT / "deleted_trades.csv", index=False, encoding="utf-8-sig")


def guards() -> None:
    print("\n══ حرّاس ══")
    bad = []
    frames = pathlib.Path.home() / ".cache" / "l0046_frames"
    for f in sorted(OUT.glob("trades_*.csv")):
        cost = 0.0 if "phase0_zero_" in f.name or "phase0_column" in f.name else REAL_COST
        # ملفات الأعمدة في المرحلة 0 لم تُحفظ (تحقق في الذاكرة فقط). الباقي 0.13% إلا صفر المحفظة.
        if f.name.startswith("trades_phase0_zero_"):
            cost = 0.0
        st = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "fill_invariant_check.py"),
             "--trades", str(f), "--frames", str(frames),
             "--cost", str(cost), "--bar-tag", "4h"],
            capture_output=True, text=True)
        line = next((ln for ln in st.stdout.splitlines() if f.name in ln), "")
        if st.returncode != 0 or "تُخطّي=0" not in st.stdout or "شموع ناقصة=0" not in st.stdout:
            bad.append(f.name + " fill")
            print(" FAIL", f.name, st.stdout[-300:])
        else:
            print(" ", line.strip())
        au = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "position_sequencing_audit.py"),
             "--trades", str(f), "--require-zero"],
            capture_output=True, text=True)
        if au.returncode != 0:
            bad.append(f.name + " seq")
    if bad:
        raise SystemExit("حارس فشل: " + ", ".join(bad))
    print("  ✅ التعبئة والتسلسل")


def write_outputs(canary: dict, lab: str) -> None:
    pd.DataFrame(MEASURED).to_csv(OUT / "measurements.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(LEDGER).to_csv(OUT / "attempt_ledger.csv", index=False, encoding="utf-8-sig")
    meas = pd.DataFrame(MEASURED)
    rnd = meas[meas["seed"].notna()] if len(meas) and "seed" in meas.columns else meas.iloc[0:0]
    rows = []
    if len(rnd):
        for window, g in rnd.groupby("الفترة"):
            rows.append({"الفترة": window, "mean": round(float(g["net"].mean()), 2),
                         "min": round(float(g["net"].min()), 2),
                         "max": round(float(g["net"].max()), 2), "n": int(len(g))})
    pd.DataFrame(rows).to_csv(OUT / "random_summary.csv", index=False, encoding="utf-8-sig")
    env = {
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "platform": platform.platform(),
        "cost_default_file": DEFAULT_COST,
        "stop": STOP, "trail": TRAIL,
        "seeds": list(SEEDS), "cap": CAP, "counted": len(LEDGER),
        "canary": canary.get("canary"),
        "canary_net": canary.get("got", {}).get("net"),
        "canary_lab": lab,
        "classifier": "daily EMA50/EMA200/slope10 shift(1), per symbol, entry bar",
        "regime_py_used": False,
    }
    (OUT / "env_dump.txt").write_text(json.dumps(env, ensure_ascii=False, indent=2), encoding="utf-8")
    blobs = []
    for name in ("measurements.csv", "random_summary.csv", "attempt_ledger.csv", "routing_map.json"):
        data = (OUT / name).read_bytes()
        blobs.append(f"{name} {hashlib.sha256(data).hexdigest()}")
    (OUT / "sha256.txt").write_text("\n".join(blobs) + "\n", encoding="utf-8")
    print("\n".join(blobs))
    if len(LEDGER) != CAP:
        raise SystemExit(f"العدّ {len(LEDGER)} ≠ {CAP}")
    restore_cost()


def main() -> int:
    t0 = time.time()
    print("═" * 74)
    print(" L0050 — إسناد مناخي. قياس فقط. السقف 35.")
    print("═" * 74)
    (OUT / "grid_precommitted.txt").write_text(
        "قبل أي رقم حكم:\n"
        "القاعدة: تشغيل العمود في المناخ إذا صافي الاختيار > 0 والصفقات ≥ 30. لا تُغيَّر.\n"
        "الخريطة من الاختيار فقط، وتُكتب قبل الحكم.\n"
        "21 (أعمدة×مناخ على الاختيار) + 2 مسنَدة + 10 بذور + 2 احتفاظ = 35.\n"
        "سقف المرحلة 2 في الورقة (8) لا يتسع لخمس بذور × فترتين. البذور لم تُقطع.\n"
        "بلا إسناد عند 0.13% يُعاد في المرحلة 0 ولا يُحسب.\n"
        "بذور: 110050 210050 310050 410050 510050.\n"
        "لم يُقَس كقياس جديد: تفكيك المناخ، الصفقات المحذوفة، نسبة الوقت — من الملفات.\n",
        encoding="utf-8")
    canary = run_canary()
    run_selftests()
    lab = lab_canary_status()
    prepare()
    build_regimes()
    p0 = phase0()
    cells = phase1()
    mp = write_map(cells)
    enabled = {tuple(x) for x in mp["enabled"]}
    routed = phase2(enabled)
    phase3_buyhold()
    decompositions(routed, p0["real"], mp)
    write_outputs(canary, lab)
    guards()
    print(f"انتهى في {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
