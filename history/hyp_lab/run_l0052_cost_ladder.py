# -*- coding: utf-8 -*-
"""L0052 — سلّم الكلفة على المحفظة المسنَدة. قياس فقط.

متغيّر واحد: الكلفة. الخريطة تُنسخ من L0051 ولا تُعاد اشتقاقها.
لا استكمال خطي لنقطة تعادل. لا محمّل بديل. لا لمس لإشارة أو خروج.

شبكة مكتوبة قبل أي رقم حكم. السقف 40. المستهلك المعلَن 34.
  مرحلة 0 (لا تُحسب): بلا إسناد 0.13% ×2 · مسنَدة 0.13% ×2.
  سلّم (12): 0.10% 0.085% 0.075% 0.06% 0.04% 0.00% × فترتين.
      0.13% في الجدول من المرحلة 0، لا يُعاد عدّه.
  بذور (20): 0.075% و 0.00% × 5 بذور × فترتين.
      عشوائي عند 0.13% و 0.10% و 0.085% و 0.06% و 0.04% لم يُقَس.
      موجب بلا بذور لا يُحتسب فوزًا، ولا تُضاف بذور بعد الرؤية.
  احتفاظ (2): عند 0.00% × فترتين.
  تفكيك المناخ والأعمدة: من الملفات، ليس قياسًا جديدًا.
  سقف المرحلة 1 في الورقة (28) لا يتسع لـ 12 + 20. البذور لا تُقطع.
  المقاعد الستة الباقية لا تُملأ بعد الرؤية.

بذور: 110052 210052 310052 410052 510052.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import platform
import shutil
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

OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0052"
OUT.mkdir(parents=True, exist_ok=True)
DAILY = pathlib.Path.home() / ".cache" / "l0052_daily"
DAILY.mkdir(parents=True, exist_ok=True)
MAP_SRC = ROOT / "history" / "research" / "hyp_lab_out" / "L0051" / "routing_map.json"

DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
WARM = "2021-06-01"
SEEDS = (110052, 210052, 310052, 410052, 510052)
CAP = 40
PLANNED = 34
DEFAULT_COST = 0.0013
STOP = 2.5
TRAIL = 4.0
BAR = 4 * 3600
REGIMES = ("صاعد", "عرضي", "هابط")

# مستويات السلّم عدا 0.13% (مرحلة 0). البذور فقط عند الاثنين المأمور بهما.
LADDER = (0.0010, 0.00085, 0.00075, 0.0006, 0.0004, 0.0)
SEED_AT = (0.00075, 0.0)
P0_UNROUTED = {"SEL": (10.76, 1067), "JUD": (-154.84, 1791)}
P0_ROUTED = {"SEL": (22.81, 1045), "JUD": (-36.45, 1610)}
FROZEN_ENABLED = {
    ("كاسرة النطاق", "صاعد"), ("كاسرة النطاق", "هابط"),
    ("انحراف الدخول", "صاعد"), ("التنقيط التعويضي", "صاعد"),
    ("دونشيان", "صاعد"), ("ماكد", "هابط"),
    ("بولنجر", "صاعد"), ("بولنجر", "هابط"),
    ("سناب المؤشر", "صاعد"), ("سناب المؤشر", "عرضي"), ("سناب المؤشر", "هابط"),
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
ENABLED: set[tuple[str, str]] = set()


def cost_tag(cost: float) -> str:
    return f"c{int(round(cost * 100000)):05d}"


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
    costs = float((qty * float(cost) * (entry + exit_)).sum())
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
        print((can.stdout or "")[-1200:])
        print((can.stderr or "")[-600:])
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
        msg = "لم يُشغَّل: phase3_basis_repaired.csv غير موجود. لم يُصنَّع بديل."
        print(f"  كاناري المختبر: {msg}")
        return msg
    st = subprocess.run([sys.executable, str(ROOT / "tools" / "canary_lab.py"), "--json"],
                        capture_output=True, text=True)
    print(st.stdout.strip() or st.stderr[-400:])
    return st.stdout.strip()


def load_frozen_map() -> set[tuple[str, str]]:
    if not MAP_SRC.exists():
        raise SystemExit("خريطة L0051 غير موجودة. لا أولّدها.")
    raw = MAP_SRC.read_text(encoding="utf-8")
    mp = json.loads(raw)
    enabled = {tuple(x) for x in mp["enabled"]}
    if enabled != FROZEN_ENABLED or len(enabled) != 11:
        raise SystemExit(f"الخريطة المودعة ليست الخريطة المجمَّدة المعروفة: {sorted(enabled)}")
    shutil.copyfile(MAP_SRC, OUT / "routing_map.json")
    print(f"  خريطة منسوخة لا مولَّدة: {len(enabled)} خانات")
    return enabled


def prepare() -> None:
    global SYMS, ENABLED
    L36.set_core()
    NC.EMA_FAST = 8
    M213._cache.clear()
    R48._SIG.clear()
    C.STOP_ATR = STOP
    restore_cost()
    if abs(C.COST_PER_SIDE - DEFAULT_COST) > 1e-15:
        raise SystemExit("كلفة الملف في الذاكرة ليست 0.0013")
    cells = R48._cells()
    SYMS = sorted({c["symbol"] for c in cells})
    R48.SYMS = SYMS
    R48.BAR = BAR
    R48.frames = R46.frames
    print(f"  خلايا={len(cells)} عملات={len(SYMS)}")
    if set(SYMS) != L0048_COINS:
        raise SystemExit(f"سلة تختلف عن L0048: {sorted(set(SYMS) ^ L0048_COINS)}")
    ENABLED = load_frozen_map()
    R46.build_cache(SYMS)


def build_regimes() -> None:
    print("\n══ مصنّف يومي shift(1) — كاش 4 ساعات الرسمي ══")
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
            raise SystemExit(f"شمعة اليوم ليست منتصف الليل: {sym} {dly.index.min()}")
        close = dly["close"]
        e50 = close.ewm(span=50, adjust=False).mean()
        e200 = close.ewm(span=200, adjust=False).mean()
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


def entry_regime(sym: str, index: pd.DatetimeIndex) -> pd.Series:
    return REG4H[sym].reindex(index).shift(-1)


def routed_signal(df, sym):
    sig = pd.Series(False, index=df.index)
    er = entry_regime(sym, df.index)
    for col, regime in ENABLED:
        sg = R48.column_signal(df, sym, col).reindex(df.index, fill_value=False).fillna(False).astype(bool)
        sig = sig | (sg & (er == regime))
    return sig


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


def phase0() -> dict:
    print("\n══ مرحلة 0: أربعة مراجع (لا تُحسب) ══")
    out = {}
    set_cost(0.0013)
    try:
        for lbl, s0, s1, exp_map, name in (
            ("SEL", DEC_S, DEC_E, P0_UNROUTED, "unrouted"),
            ("JUD", JUD_S, JUD_E, P0_UNROUTED, "unrouted"),
        ):
            rows = simulate_mask(R48.portfolio_signal, s0, s1, name)
            save_trades(f"phase0_unrouted_{lbl}", rows)
            st = summarize(rows, 0.0013)
            exp_net, exp_n = exp_map[lbl]
            print(f"  بلا إسناد {lbl}: {st['net']}$ / {st['trades']}  مرجع {exp_net}$ / {exp_n}")
            if abs(st["net"] - exp_net) > 0.5 or st["trades"] != exp_n or st["overlapping_trades"]:
                raise SystemExit("أساس بلا إسناد لم يُطابق. أوقف.")
        routed = {}
        for lbl, s0, s1 in (("SEL", DEC_S, DEC_E), ("JUD", JUD_S, JUD_E)):
            rows = simulate_mask(routed_signal, s0, s1, "routed")
            bad = [r for r in rows if r.get("regime") not in {reg for _, reg in ENABLED}]
            if bad:
                raise SystemExit(f"صفقة خارج الخريطة المجمَّدة: {len(bad)}")
            save_trades(f"phase0_routed_{lbl}", rows)
            st = summarize(rows, 0.0013)
            exp_net, exp_n = P0_ROUTED[lbl]
            print(f"  مسنَدة {lbl}: {st['net']}$ / {st['trades']}  مرجع {exp_net}$ / {exp_n}")
            if abs(st["net"] - exp_net) > 0.5 or st["trades"] != exp_n or st["overlapping_trades"]:
                raise SystemExit("أساس المسنَدة لم يُطابق. أوقف. لا سلّم.")
            routed[lbl] = rows
        out["routed"] = {0.0013: routed}
    finally:
        restore_cost()
    print("  ✅ الأربعة طابقت")
    return out


def ladder(store: dict) -> None:
    print("\n══ سلّم الكلفة — الخريطة نفسها ══")
    windows = (("SEL", DEC_S, DEC_E, "اختيار"), ("JUD", JUD_S, JUD_E, "حكم"))
    for cost in LADDER:
        set_cost(cost)
        try:
            store.setdefault(cost, {})
            for lbl, s0, s1, wname in windows:
                rows = simulate_mask(routed_signal, s0, s1, "routed")
                save_trades(f"routed_{cost_tag(cost)}_{lbl}", rows)
                record(f"مسنَدة {cost:.3%}", wname, rows, cost, None, True)
                store[cost][lbl] = rows
        finally:
            restore_cost()


def seeds_for(store: dict, cost: float) -> None:
    print(f"\n══ بذور عند {cost:.3%} ══")
    set_cost(cost)
    try:
        windows = (("SEL", DEC_S, DEC_E, "اختيار"), ("JUD", JUD_S, JUD_E, "حكم"))
        for lbl, s0, s1, wname in windows:
            direct = store[cost][lbl]
            outs = {}
            for sym in SYMS:
                win = R48.window(R46.frames(sym), s0, s1)
                if len(win) < 100:
                    continue
                outs[sym] = R48.outcomes_for(sym, s0, s1)
            cached = []
            for sym, table in outs.items():
                df = R46.frames(sym)
                win = R48.window(df, s0, s1)
                sg = routed_signal(df, sym).reindex(win.index, fill_value=False).fillna(False).astype(bool).to_numpy()
                cached.extend(R48.rows_from_chosen(sym, "cache", R48.greedy(table, sg)))
            ds, cs = summarize(direct, cost), summarize(cached, cost)
            if abs(ds["net"] - cs["net"]) > 0.01 or ds["trades"] != cs["trades"]:
                raise SystemExit(f"تكافؤ فشل عند {cost} {lbl}: {ds} ≠ {cs}")
            print(f"  ✅ تكافؤ {cost:.3%} {lbl}")
            tgt = {}
            t = pd.DataFrame(direct) if direct else pd.DataFrame(columns=["symbol"])
            for sym in outs:
                tgt[sym] = int((t["symbol"] == sym).sum()) if len(t) else 0
            for seed in SEEDS:
                rows = []
                for sym, table in outs.items():
                    u = R48.uniforms(seed, sym, len(table))
                    p = R48.match_p(table, u, tgt.get(sym, 0))
                    rows.extend(R48.rows_from_chosen(sym, f"rnd{seed}", R48.greedy(table, u < p)))
                save_trades(f"rnd_{cost_tag(cost)}_s{seed}_{lbl}", rows)
                record(f"عشوائي {cost:.3%} بذرة {seed}", wname, rows, cost, seed, True)
    finally:
        restore_cost()


def buyhold() -> None:
    print("\n══ احتفاظ عند كلفة صفر ══")
    set_cost(0.0)
    try:
        for lbl, s0, s1, wname in (("SEL", DEC_S, DEC_E, "اختيار"), ("JUD", JUD_S, JUD_E, "حكم")):
            rows = []
            for sym in SYMS:
                w = R48.window(R46.frames(sym), s0, s1)
                if len(w) < 2:
                    continue
                e = float(w["open"].iloc[0])
                x = float(w["close"].iloc[-1])
                pnl = C.TRADE_USD * (x / e - 1.0)
                rows.append({
                    "symbol": sym, "exp": "buyhold",
                    "entry_time": w.index[0].isoformat(),
                    "exit_time": w.index[-1].isoformat(),
                    "entry": float(f"{e:.12g}"), "exit": float(f"{x:.12g}"),
                    "notional": C.TRADE_USD, "pnl": round(pnl, 4),
                    "bars_held": int(len(w) - 1), "exit_side": "eod", "regime": "",
                })
            save_trades(f"buyhold_c00000_{lbl}", rows)
            record("احتفاظ كلفة 0%", wname, rows, 0.0, None, True)
    finally:
        restore_cost()


def decompositions(store: dict) -> None:
    """تفكيك ملفات مقيسة. ليس قياسًا جديدًا."""
    contrib, cols = [], []
    for cost in (0.00075, 0.0, 0.0013):
        for lbl in ("SEL", "JUD"):
            rows = store[cost][lbl]
            for reg in list(REGIMES) + ["غير مصنّف"]:
                part = [r for r in rows if r.get("regime") == reg]
                contrib.append({"cost": cost, "الفترة": lbl, "المناخ": reg, **summarize(part, cost)})
            # نسبة أول عمود أطلق الإشارة. التقسيم يجمع إلى الكتاب. ليس تشغيلًا منفردًا.
            by_sym = {}
            for sym in {r["symbol"] for r in rows}:
                df = R46.frames(sym)
                by_sym[sym] = {col: R48.column_signal(df, sym, col) for col in R48.COL_ORDER}
            buckets = {col: [] for col in R48.COL_ORDER}
            buckets["بلا عمود"] = []
            multi = 0
            for r in rows:
                ts = pd.Timestamp(r["entry_time"])
                if ts.tzinfo is None:
                    ts = ts.tz_localize("UTC")
                sig_ts = ts - pd.Timedelta(hours=4)
                fired = []
                sigs = by_sym.get(r["symbol"], {})
                for col in R48.COL_ORDER:
                    s = sigs.get(col)
                    if s is not None and sig_ts in s.index and bool(s.loc[sig_ts]):
                        fired.append(col)
                if len(fired) > 1:
                    multi += 1
                key = fired[0] if fired else "بلا عمود"
                buckets[key].append(r)
            for col, part in buckets.items():
                st = summarize(part, cost)
                cols.append({"cost": cost, "الفترة": lbl, "العمود": col, "متعدد_الإطلاق": multi, **st})
    pd.DataFrame(contrib).to_csv(OUT / "regime_contribution.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(cols).to_csv(OUT / "column_partition.csv", index=False, encoding="utf-8-sig")
    print("  تفكيك كُتب (ليس قياسًا جديدًا)")


def guards() -> None:
    print("\n══ حرّاس ══")
    bad = []
    frames = pathlib.Path.home() / ".cache" / "l0046_frames"
    for f in sorted(OUT.glob("trades_*.csv")):
        name = f.name
        if "c00000" in name or name.endswith("_c00000_SEL.csv") or "buyhold_c00000" in name:
            cost = 0.0
        elif "c00040" in name:
            cost = 0.0004
        elif "c00060" in name:
            cost = 0.0006
        elif "c00075" in name:
            cost = 0.00075
        elif "c00085" in name:
            cost = 0.00085
        elif "c00100" in name:
            cost = 0.0010
        else:
            cost = 0.0013
        # وسم الكلفة في الاسم أدق من التخمين
        for tag, c in (
            ("c00000", 0.0), ("c00040", 0.0004), ("c00060", 0.0006),
            ("c00075", 0.00075), ("c00085", 0.00085), ("c00100", 0.0010),
            ("c00130", 0.0013),
        ):
            if tag in name:
                cost = c
                break
        st = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "fill_invariant_check.py"),
             "--trades", str(f), "--frames", str(frames),
             "--cost", str(cost), "--bar-tag", "4h"],
            capture_output=True, text=True)
        line = next((ln for ln in st.stdout.splitlines() if f.name in ln), "")
        if st.returncode != 0 or "تُخطّي=0" not in st.stdout or "شموع ناقصة=0" not in st.stdout:
            bad.append(name + " fill")
            print(" FAIL", name, st.stdout[-250:])
        else:
            print(" ", line.strip())
        au = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "position_sequencing_audit.py"),
             "--trades", str(f), "--require-zero"],
            capture_output=True, text=True)
        if au.returncode != 0:
            bad.append(name + " seq")
    if bad:
        raise SystemExit("حارس فشل: " + ", ".join(bad))
    print("  ✅ التعبئة والتسلسل")


def write_outputs(canary: dict, lab: str) -> None:
    pd.DataFrame(MEASURED).to_csv(OUT / "measurements.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(LEDGER).to_csv(OUT / "attempt_ledger.csv", index=False, encoding="utf-8-sig")
    meas = pd.DataFrame(MEASURED)
    rnd = meas[meas["seed"].notna()] if len(meas) else meas.iloc[0:0]
    rows = []
    if len(rnd):
        for (cost, window), g in rnd.groupby(["cost", "الفترة"]):
            rows.append({"cost": cost, "الفترة": window,
                         "mean": round(float(g["net"].mean()), 2),
                         "min": round(float(g["net"].min()), 2),
                         "max": round(float(g["net"].max()), 2), "n": int(len(g))})
    pd.DataFrame(rows).to_csv(OUT / "random_summary.csv", index=False, encoding="utf-8-sig")
    env = {
        "python": platform.python_version(), "pandas": pd.__version__,
        "numpy": np.__version__, "platform": platform.platform(),
        "cost_default_file": DEFAULT_COST, "stop": STOP, "trail": TRAIL,
        "seeds": list(SEEDS), "cap": CAP, "counted": len(LEDGER),
        "map": "copied from L0051/routing_map.json", "map_regenerated": False,
        "canary": canary.get("canary"),
        "canary_net": canary.get("got", {}).get("net"),
        "canary_lab": lab, "regime_py_used": False, "alternative_loader": False,
    }
    (OUT / "env_dump.txt").write_text(json.dumps(env, ensure_ascii=False, indent=2), encoding="utf-8")
    blobs = []
    for name in ("measurements.csv", "random_summary.csv", "attempt_ledger.csv", "routing_map.json"):
        data = (OUT / name).read_bytes()
        blobs.append(f"{name} {hashlib.sha256(data).hexdigest()}")
    (OUT / "sha256.txt").write_text("\n".join(blobs) + "\n", encoding="utf-8")
    print("\n".join(blobs))
    if len(LEDGER) != PLANNED:
        raise SystemExit(f"العدّ {len(LEDGER)} ≠ {PLANNED}")
    restore_cost()
    if abs(C.COST_PER_SIDE - DEFAULT_COST) > 1e-15:
        raise SystemExit("لم تُعَد كلفة الافتراضي")


def main() -> int:
    t0 = time.time()
    print("═" * 74)
    print(" L0052 — سلّم كلفة. خريطة مجمَّدة. السقف 40. المستهلك المعلَن 34.")
    print("═" * 74)
    (OUT / "grid_precommitted.txt").write_text(
        "قبل أي رقم حكم:\n"
        "الخريطة تُنسخ من L0051 ولا تُولَّد. 11 خانة.\n"
        "0.13% يُعاد في المرحلة 0 ولا يُحسب.\n"
        "12 سلّم (ستة مستويات × فترتين) + 20 بذرة (0.075% و 0.00% ×5 ×فترتين) + 2 احتفاظ عند صفر = 34.\n"
        "عشوائي عند 0.10% و 0.085% و 0.06% و 0.04% و 0.13% لم يُقَس. لا يُضاف بعد الرؤية.\n"
        "لا استكمال خطي. الانقلاب يُقال «بين مستويين» فقط إن انعكست الإشارة.\n"
        "بذور: 110052 210052 310052 410052 510052.\n"
        "المقاعد الباقية (6) لا تُملأ بعد الرؤية.\n",
        encoding="utf-8")
    canary = run_canary()
    run_selftests()
    lab = lab_canary_status()
    prepare()
    build_regimes()
    store = phase0()["routed"]
    ladder(store)
    for cost in SEED_AT:
        seeds_for(store, cost)
    buyhold()
    decompositions(store)
    write_outputs(canary, lab)
    guards()
    print(f"انتهى في {time.time()-t0:.0f}s  العدّ={len(LEDGER)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
