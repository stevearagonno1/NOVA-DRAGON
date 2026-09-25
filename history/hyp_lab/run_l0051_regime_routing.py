# -*- coding: utf-8 -*-
"""L0051 — هل يربح البوت لو شُغّل كل عمود في مناخه فقط؟

قياس وحكم فقط. لا تحسين. لا لمس لإشارة أو خروج أو nova_v8.
لا أبحث عن جدول أعمدة L0050 ولا أحاول مطابقته. ذلك الجدول محذوف.

الطريقة (أ)، مكتوبة قبل الرؤية:
    كل عمود يُشغَّل منفردًا على الاختيار عند 0.13%، ثم تُصنَّف صفقاته
    حسب مناخ شمعة الدخول. ليست 21 تشغيلًا مفلترًا، وليست نسبة من الدفتر المدمج.
    سبعة قياسات. الخلايا الـ21 تفكيك لهذه الملفات.

قاعدة الإسناد، لا تُغيَّر بعد الرؤية:
    يُشغَّل العمود في المناخ إذا كان صافي الاختيار > 0 وعدد الصفقات ≥ 30.

الخريطة تُكتب في routing_map.json قبل أي قياس حكم، والمرحلة 2 تقرأ الملف لا الذاكرة.

السقف 35. الشبكة قبل أي رقم حكم:
    7 أعمدة على الاختيار
    + مسنَدة × فترتين
    + 5 بذور × فترتين
    + احتفاظ × فترتين
    = 21.
    سقف المرحلة 2 في الورقة (8) لا يتسع لخمس بذور × فترتين. البذور لا تُقطع.
    بلا إسناد عند 0.13% يُعاد في المرحلة 0 (رقم منشور) ولا يُحسب من جديد.
    تفكيك المناخ، والصفقات المحذوفة، ونسبة الوقت: من ملفات مقيسة، ليست قياسات جديدة.
    المقاعد الباقية لا تُملأ بعد الرؤية.
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

OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0051"
OUT.mkdir(parents=True, exist_ok=True)
DAILY = pathlib.Path.home() / ".cache" / "l0051_daily"
DAILY.mkdir(parents=True, exist_ok=True)

DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
WARM = "2021-06-01"
SEEDS = (110051, 210051, 310051, 410051, 510051)
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
P0_SPLIT = {
    "SEL": {"صاعد": (98.63, 156), "عرضي": (-86.02, 328), "هابط": (55.19, 569)},
    "JUD": {"صاعد": (-72.44, 383), "عرضي": (-91.67, 588), "هابط": (99.22, 808)},
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
        if ts in series.index:
            val = series.loc[ts]
            r["regime"] = val if isinstance(val, str) else "غير مصنّف"
        else:
            r["regime"] = "غير مصنّف"
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
        print((can.stdout or "")[-1500:])
        print((can.stderr or "")[-800:])
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
    print("\n══ مصنّف المناخ اليومي (shift 1) — الكاش الرسمي لـ 4 ساعات ══")
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
        if int(dly.index.min().hour) != 0 or int(dly.index.min().minute) != 0:
            raise SystemExit(f"شمعة اليوم ليست على منتصف الليل: {sym} {dly.index.min()}")
        c = dly["close"]
        e50 = c.ewm(span=50, adjust=False).mean()
        e200 = c.ewm(span=200, adjust=False).mean()
        slope = e50.diff(10)
        raw = pd.Series("عرضي", index=dly.index)
        raw[(e50 > e200) & (slope > 0)] = "صاعد"
        raw[(e50 < e200) & (slope < 0)] = "هابط"
        lab = raw.shift(1)
        if not lab.iloc[1:].reset_index(drop=True).equals(raw.iloc[:-1].reset_index(drop=True)):
            raise SystemExit("shift(1) لم يُطبَّق")
        f = R46.frames(sym)
        lookup = {ts.normalize(): val for ts, val in lab.items()}
        REG4H[sym] = pd.Series(
            [lookup.get(ts.normalize(), np.nan) for ts in f.index],
            index=f.index, dtype=object)
    btc = REG4H["BTCUSDT"].dropna().astype(str).value_counts()
    print(f"  BTC 4h بعد الإزاحة: {btc.to_dict()}")


def entry_regime(sym: str, index: pd.DatetimeIndex) -> pd.Series:
    return REG4H[sym].reindex(index).shift(-1)


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


def split_rows(rows: list[dict], cost: float) -> dict[str, dict]:
    out = {}
    for reg in list(REGIMES) + ["غير مصنّف"]:
        out[reg] = summarize([r for r in rows if r.get("regime") == reg], cost)
    return out


def phase0() -> dict:
    print("\n══ مرحلة 0أ: أربعة مراجع (لا تُحسب) ══")
    books = {}
    set_cost(0.0)
    for lbl, s0, s1 in (("SEL", DEC_S, DEC_E), ("JUD", JUD_S, JUD_E)):
        rows = simulate_mask(R48.portfolio_signal, s0, s1, "zero")
        save_trades(f"phase0_zero_{lbl}", rows)
        st = summarize(rows, 0.0)
        exp_net, exp_n = P0_ZERO[lbl]
        print(f"  صفر {lbl}: {st['net']}$ / {st['trades']}  مرجع {exp_net}$ / {exp_n}")
        if abs(st["net"] - exp_net) > 0.5 or st["trades"] != exp_n or st["overlapping_trades"] != 0:
            raise SystemExit("أساس كلفة صفر لم يُطابق. أوقف. لا قياس.")
        books[lbl] = rows
    print("  تفكيك المحفظة حسب مناخ الدخول")
    cmp_rows = []
    for lbl in ("SEL", "JUD"):
        parts = split_rows(books[lbl], 0.0)
        for reg in REGIMES:
            got_n, got_t = parts[reg]["net"], parts[reg]["trades"]
            exp_n, exp_t = P0_SPLIT[lbl][reg]
            ok = abs(got_n - exp_n) <= 0.02 and got_t == exp_t
            cmp_rows.append({"الفترة": lbl, "المناخ": reg, "صافي": got_n, "مرجع": exp_n,
                             "صفقات": got_t, "مرجع_صفقات": exp_t, "يطابق": ok})
            print(f"    {lbl} {reg}: {got_n}$ / {got_t}  مرجع {exp_n}$ / {exp_t} {'✅' if ok else '❌'}")
        unk = parts["غير مصنّف"]
        if unk["trades"] or abs(unk["net"]) > 0.0:
            print(f"    {lbl} غير مصنّف: {unk['net']}$ / {unk['trades']}")
            if abs(unk["net"]) > 0.02 or unk["trades"]:
                cmp_rows.append({"الفترة": lbl, "المناخ": "غير مصنّف", "يطابق": False,
                                 "صافي": unk["net"], "صفقات": unk["trades"]})
    pd.DataFrame(cmp_rows).to_csv(OUT / "phase0_book_regime.csv", index=False, encoding="utf-8-sig")
    if not all(r.get("يطابق", False) for r in cmp_rows):
        raise SystemExit("تفكيك المناخ لم يُطابق. أوقف. لا إسناد.")
    print("  ✅ التفكيك طابق")

    print("\n══ مرحلة 0ب: 0.13% بلا إسناد (لا تُحسب، مرجع منشور) ══")
    set_cost(REAL_COST)
    real = {}
    for lbl, s0, s1 in (("SEL", DEC_S, DEC_E), ("JUD", JUD_S, JUD_E)):
        rows = simulate_mask(R48.portfolio_signal, s0, s1, "unrouted")
        save_trades(f"phase0_real_{lbl}", rows)
        st = summarize(rows, REAL_COST)
        exp_net, exp_n = P0_REAL[lbl]
        print(f"  0.13% {lbl}: {st['net']}$ / {st['trades']}  مرجع {exp_net}$ / {exp_n}")
        if abs(st["net"] - exp_net) > 0.5 or st["trades"] != exp_n:
            raise SystemExit("أساس 0.13% لم يُطابق. أوقف.")
        real[lbl] = rows
    return {"zero": books, "real": real}


def phase1() -> list[dict]:
    """الطريقة (أ): عمود منفرد على الاختيار، ثم تصنيف صفقاته. 7 قياسات."""
    print("\n══ مرحلة 1: الطريقة (أ) — 7 أعمدة على الاختيار، كلفة 0.13% ══")
    set_cost(REAL_COST)
    cells = []
    for i, col in enumerate(R48.COL_ORDER):
        def sig_of(df, sym, col=col):
            return R48.column_signal(df, sym, col)
        rows = simulate_mask(sig_of, DEC_S, DEC_E, col)
        save_trades(f"p1_{i}_SEL", rows)
        st = record(f"عمود {col} منفردًا", "اختيار", rows, REAL_COST, None, True, {"column": col})
        parts = split_rows(rows, REAL_COST)
        print(f"    تفكيك {col}: " + " | ".join(
            f"{reg} {parts[reg]['net']}$/{parts[reg]['trades']}" for reg in REGIMES))
        unk = parts["غير مصنّف"]
        if unk["trades"]:
            print(f"    غير مصنّف: {unk['net']}$ / {unk['trades']}")
        for reg in REGIMES:
            p = parts[reg]
            cells.append({
                "column": col, "regime": reg,
                "net": p["net"], "trades": p["trades"], "per": p["per"],
                "gross": p["gross"], "costs": p["costs"], "median_hold": p["median_hold"],
                "column_net": st["net"], "column_trades": st["trades"],
                "unclassified_trades": unk["trades"], "unclassified_net": unk["net"],
            })
    return cells


def write_map(cells: list[dict]) -> dict:
    enabled = []
    for c in cells:
        c["enabled"] = bool(c["net"] > 0 and c["trades"] >= MIN_TRADES)
        if c["enabled"]:
            enabled.append([c["column"], c["regime"]])
    payload = {
        "method": "أ — العمود منفردًا على الاختيار ثم تصنيف صفقاته حسب مناخ الدخول",
        "rule": "صافي الخلية > 0 وعدد صفقاتها ≥ 30. لا تُغيَّر بعد رؤية الحكم.",
        "cost": REAL_COST,
        "min_trades": MIN_TRADES,
        "period": [DEC_S, DEC_E],
        "cells": cells,
        "enabled": enabled,
        "n_enabled": len(enabled),
        "n_excluded": len(cells) - len(enabled),
        "written_before_judgement_measurement": True,
    }
    path = OUT / "routing_map.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n══ خريطة كُتبت في الملف قبل الحكم: {len(enabled)} خانات من {len(cells)} ══")
    for col, reg in enabled:
        print(f"    تشغيل: {col} · {reg}")
    if not enabled:
        print("    لا خانة نجت. المسنَدة ستكون فارغة. لا أغيّر القاعدة.")
    return payload


def load_enabled() -> set[tuple[str, str]]:
    mp = json.loads((OUT / "routing_map.json").read_text(encoding="utf-8"))
    return {tuple(x) for x in mp["enabled"]}


def routed_signal(enabled: set[tuple[str, str]]):
    def sig_of(df, sym):
        sig = pd.Series(False, index=df.index)
        er = entry_regime(sym, df.index)
        for col, regime in enabled:
            sg = R48.column_signal(df, sym, col).reindex(df.index, fill_value=False).fillna(False).astype(bool)
            sig = sig | (sg & (er == regime))
        return sig
    return sig_of


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


def phase2() -> dict:
    enabled = load_enabled()
    print(f"\n══ مرحلة 2: المسنَدة من الملف ({len(enabled)} خانات) + البذور ══")
    set_cost(REAL_COST)
    sig = routed_signal(enabled)
    out = {}
    for lbl, s0, s1, wname in (
        ("SEL", DEC_S, DEC_E, "اختيار"),
        ("JUD", JUD_S, JUD_E, "حكم"),
    ):
        rows = simulate_mask(sig, s0, s1, "routed")
        if enabled:
            bad = [r for r in rows if (r.get("exp"), r.get("regime")) and r.get("regime") not in {reg for _, reg in enabled}]
            # كل صفقة يجب أن يكون مناخ دخولها مناخًا مُفعَّلًا لعمود ما.
            bad = [r for r in rows if r.get("regime") not in {reg for _, reg in enabled}]
            if bad:
                raise SystemExit(f"صفقة خارج المناخات المفعّلة: {len(bad)} {bad[0].get('regime')}")
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
    print("\n══ احتفاظ 20$ من أول افتتاح إلى آخر إغلاق ══")
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


def decompositions(routed: dict, real: dict) -> None:
    mp = json.loads((OUT / "routing_map.json").read_text(encoding="utf-8"))
    enabled_regs = {reg for _, reg in mp["enabled"]}
    idle_rows = []
    for lbl, s0, s1 in (("SEL", DEC_S, DEC_E), ("JUD", JUD_S, JUD_E)):
        labeled = side = blocked = 0
        for sym in SYMS:
            win = R48.window(R46.frames(sym), s0, s1)
            reg = REG4H[sym].reindex(win.index).dropna()
            labeled += int(len(reg))
            side += int((reg == "عرضي").sum())
            if enabled_regs:
                blocked += int((~reg.isin(list(enabled_regs))).sum())
            else:
                blocked += int(len(reg))
        idle_rows.append({
            "الفترة": lbl, "شموع_مصنفة": labeled, "عرضي": side,
            "نسبة_العرضي": round(side / labeled, 4) if labeled else None,
            "شموع_بلا_دخول": blocked,
            "نسبة_بلا_دخول": round(blocked / labeled, 4) if labeled else None,
            "مناخات_مفعّلة": sorted(enabled_regs),
        })
    pd.DataFrame(idle_rows).to_csv(OUT / "idle_time.csv", index=False, encoding="utf-8-sig")
    print("  وقت بلا دخول جديد:", idle_rows)

    contrib, deleted = [], []
    for lbl in ("SEL", "JUD"):
        for reg in list(REGIMES) + ["غير مصنّف"]:
            part = [r for r in routed[lbl] if r.get("regime") == reg]
            contrib.append({"الفترة": lbl, "المناخ": reg, **summarize(part, REAL_COST)})
        un = {(r["symbol"], r["entry_time"]): r for r in real[lbl]}
        rt = {(r["symbol"], r["entry_time"]): r for r in routed[lbl]}
        gone = [un[k] for k in un.keys() - rt.keys()]
        added = [rt[k] for k in rt.keys() - un.keys()]
        gs, ad = summarize(gone, REAL_COST), summarize(added, REAL_COST)
        deleted.append({
            "الفترة": lbl, "حُذفت": gs["trades"], "صافي_المحذوف": gs["net"],
            "إجمالي_المحذوف": gs["gross"], "ظهرت_بسبب_الإسناد": ad["trades"],
            "صافي_الظاهر": ad["net"], "إجمالي_الظاهر": ad["gross"],
        })
        print(f"  {lbl}: حُذفت {gs['trades']} صافيها {gs['net']} | ظهرت {ad['trades']} صافيها {ad['net']}")
    pd.DataFrame(contrib).to_csv(OUT / "regime_contribution.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(deleted).to_csv(OUT / "deleted_trades.csv", index=False, encoding="utf-8-sig")


def guards() -> None:
    print("\n══ حرّاس ══")
    bad = []
    frames = pathlib.Path.home() / ".cache" / "l0046_frames"
    for f in sorted(OUT.glob("trades_*.csv")):
        cost = 0.0 if f.name.startswith("trades_phase0_zero_") else REAL_COST
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
        "method": "أ",
        "canary": canary.get("canary"),
        "canary_net": canary.get("got", {}).get("net"),
        "canary_lab": lab,
        "classifier": "daily EMA50/EMA200/slope10 shift(1), per symbol, entry bar",
        "regime_py_used": False,
        "alternative_loader": False,
    }
    (OUT / "env_dump.txt").write_text(json.dumps(env, ensure_ascii=False, indent=2), encoding="utf-8")
    blobs = []
    for name in ("measurements.csv", "random_summary.csv", "attempt_ledger.csv", "routing_map.json"):
        data = (OUT / name).read_bytes()
        blobs.append(f"{name} {hashlib.sha256(data).hexdigest()}")
    (OUT / "sha256.txt").write_text("\n".join(blobs) + "\n", encoding="utf-8")
    print("\n".join(blobs))
    if len(LEDGER) != 21:
        raise SystemExit(f"العدّ {len(LEDGER)} ≠ 21 المعلَن")
    restore_cost()


def main() -> int:
    t0 = time.time()
    print("═" * 74)
    print(" L0051 — إسناد مناخي. الطريقة (أ). السقف 35. المستهلك المعلَن 21.")
    print("═" * 74)
    (OUT / "grid_precommitted.txt").write_text(
        "قبل أي رقم حكم:\n"
        "الطريقة (أ): عمود منفرد على الاختيار ثم تصنيف صفقاته. 7 قياسات لا 21 تشغيلًا.\n"
        "القاعدة: صافي الخلية > 0 والصفقات ≥ 30. لا تُغيَّر.\n"
        "الخريطة من الاختيار فقط، وتُكتب في routing_map.json قبل الحكم.\n"
        "7 + مسنَدة×2 + بذور×10 + احتفاظ×2 = 21.\n"
        "سقف المرحلة 2 في الورقة (8) لا يتسع لخمس بذور × فترتين. البذور لم تُقطع.\n"
        "بلا إسناد عند 0.13% يُعاد في المرحلة 0 ولا يُحسب.\n"
        "بذور: 110051 210051 310051 410051 510051.\n"
        "لم يُقَس كقياس جديد: تفكيك المناخ، الصفقات المحذوفة، نسبة الوقت.\n"
        "لا أبحث عن جدول أعمدة L0050.\n",
        encoding="utf-8")
    canary = run_canary()
    run_selftests()
    lab = lab_canary_status()
    prepare()
    build_regimes()
    p0 = phase0()
    cells = phase1()
    write_map(cells)
    routed = phase2()
    phase3_buyhold()
    decompositions(routed, p0["real"])
    write_outputs(canary, lab)
    guards()
    print(f"انتهى في {time.time()-t0:.0f}s  العدّ={len(LEDGER)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
