# -*- coding: utf-8 -*-
"""L0056 — توسيع الكتاب مع حفظ الجودة. قياس وحكم. لا تطوير حرّ.

القواعد مكتوبة هنا قبل أي رقم. لا تُبدَّل بعد الرؤية.

السقف 38.
  مرحلة 0 (لا تُحسب): أربعة مراجع. أي فرق يوقف الجولة.
  مرحلة أ (2 من سقف 10): السلة الموسَّعة كلها، الفائز المرجعي، الخريطة المجمَّدة،
      0.10%، الاختيار ثم الحكم. لا 0.13% هنا. لا تفكيك يُعدّ قياسًا.
  مرحلة ب (10 من سقف 14، +1 إن تغيّرت الخريطة): كل خانة مُقصاة منفردة على الاختيار
      عند 0.10% مع المرشّح الكامل. إعادة الفتح: صافٍ > 0 وصفقات ≥ 30.
      الخريطة تُودَع قبل أي حكم لها. إن لم تُعَد خانة، لا يُعاد قياس المرجع.
  مرحلة ج (4 من سقف 8): أربعة تراكيب مكتوبة، اختيار، 0.10%، سلة 15، خريطة مجمَّدة.
      لا k جديد بعد الرؤية.
  مرحلة د (تتجاوز سقفها 6، وتبقى دون 38): حكم الفائز النهائي عند 0.10% و0.13%،
      ثم 5 بذور في الفترتين. البذور لا تُقطع. إن كان 0.10% مقيسًا سلفًا يُستشهَد به
      ولا يُعاد. مقاعد أ/ب/ج الفارغة لا تُملأ بعد الرؤية ولا تُستخدم لإخفاء التجاوز.

بذور جديدة: 110056 210056 310056 410056 510056.
لا تُستعمل إلا إذا كان الفائز النهائي تركيبًا غير مقيس عشوائيًا.
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

ROOT = pathlib.Path("/home/user/l0056")
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

OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0056"
OUT.mkdir(parents=True, exist_ok=True)
DAILY = pathlib.Path.home() / ".cache" / "l0056_daily"
DAILY.mkdir(parents=True, exist_ok=True)
MAP_SRC = ROOT / "history" / "research" / "hyp_lab_out" / "L0051" / "routing_map.json"

DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
WARM = "2021-06-01"
SEEDS = (110056, 210056, 310056, 410056, 510056)
CAP = 38
DEFAULT_COST = 0.0013
COST_REF = 0.0010
STOP = 2.5
TRAIL = 4.0
BAR = 4 * 3600
MIN_CELL = 30

P0 = {
    "win_sel": {"net": 48.98, "n": 302, "move": 0.20233},
    "win_jud": {"net": 22.72, "n": 434, "move": 0.09240},
    "win_013": {"net": 18.51, "n": 434, "move": None},
    "k34_jud": {"net": 58.90, "n": 462, "move": None},
}

FROZEN_ENABLED = {
    ("كاسرة النطاق", "صاعد"), ("كاسرة النطاق", "هابط"),
    ("انحراف الدخول", "صاعد"), ("التنقيط التعويضي", "صاعد"),
    ("دونشيان", "صاعد"), ("ماكد", "هابط"),
    ("بولنجر", "صاعد"), ("بولنجر", "هابط"),
    ("سناب المؤشر", "صاعد"), ("سناب المؤشر", "عرضي"), ("سناب المؤشر", "هابط"),
}
BASE_COINS = {
    "ATOMUSDT", "BTCUSDT", "DOGEUSDT", "ETHUSDT", "FILUSDT", "GRAMUSDT",
    "IMXUSDT", "LINKUSDT", "PEPEUSDT", "RENDERUSDT", "SHIBUSDT", "SOLUSDT",
    "TONUSDT", "VETUSDT", "XLMUSDT",
}
OLD_COLS = ("كاسرة النطاق", "انحراف الدخول", "التنقيط التعويضي")
PHASE_C = (
    ("c_k25_body", "k=2.5 + تهدئة 3 + جسم 0.4", (("vol", 2.5), ("cool", 3), ("body", 0.4))),
    ("c_k25_atr", "k=2.5 + تهدئة 3 + تقلب 0.010", (("vol", 2.5), ("cool", 3), ("atr", 0.010))),
    ("c_k30_body", "k=3.0 + تهدئة 3 + جسم 0.4", (("vol", 3.0), ("cool", 3), ("body", 0.4))),
    ("c_k30_atr", "k=3.0 + تهدئة 3 + تقلب 0.010", (("vol", 3.0), ("cool", 3), ("atr", 0.010))),
)
WINNER = (("vol", 3.5), ("cool", 3))

LEDGER: list[dict] = []
MEASURED: list[dict] = []
REG4H: dict[str, pd.Series] = {}
SYMS: list[str] = []
ENABLED: set[tuple[str, str]] = set()
OUTCOME_CACHE: dict[tuple, list] = {}

CHOICE_RULE = (
    "المرشّحون: نتيجة اختيار المرحلة أ، ومحفظة الخريطة الموسَّعة إن قيست، "
    "والتركيبات الأربع في المرحلة ج. لا يُدخل المرجع في المفاضلة. "
    "التأهيل: صافٍ موجب وحركة ≥ 0.10$ في الاختيار. "
    "الفائز = أعلى عدد صفقات، ثم أعلى حركة، ثم ترتيب الكتابة. "
    "حكم المرحلة أ لا يدخل المفاضلة. لا تعادل يُكسر بالحكم."
)
REOPEN_RULE = "تُعاد الخانة إذا صافيها المنفرد في الاختيار عند 0.10% مع المرشّح الكامل > 0 وصفقاتها ≥ 30."
ACCEPT_RULE = (
    "القبول يلزم الكل: صافٍ موجب في الفترتين عند 0.10%، وصافٍ موجب في الحكم عند 0.13%، "
    "وصفقات اختيار ≥ 400، وصفقات حكم 0.10% ≥ 550، وحركة حكم 0.10% ≥ 0.055$، "
    "وفوق أسعد بذرة 0.10% في الفترتين. صفقات 0.13% تُعرض ولا تُستبدل عن شرط 550."
)


def cost_tag(cost: float) -> str:
    return f"c{int(round(cost * 100000)):05d}"


def log_measurement(name: str, window: str, phase: str) -> int:
    if len(LEDGER) >= CAP:
        raise SystemExit(f"تجاوز السقف: محاولة تسجيل قياس بعد {CAP}")
    row = {"#": len(LEDGER) + 1, "المرحلة": phase, "القياس": name, "الفترة": window}
    LEDGER.append(row)
    return row["#"]


def set_cost(cost: float) -> None:
    C.COST_PER_SIDE = float(cost)
    R48.COST = float(cost)


def restore_cost() -> None:
    set_cost(DEFAULT_COST)


def summarize(rows: list[dict], cost: float) -> dict:
    if not rows:
        return {
            "net": 0.0, "trades": 0, "per": 0.0, "gross": 0.0, "gross_raw": 0.0,
            "costs": 0.0, "move": None, "cost_per": None, "median_hold": 0.0,
            "overlapping_trades": 0,
        }
    t = pd.DataFrame(rows)
    p = t["pnl"].to_numpy(float)
    net = round(float(p.sum()), 2)
    qty = t["notional"].to_numpy(float) / t["entry"].to_numpy(float)
    entry = t["entry"].to_numpy(float)
    exit_ = t["exit"].to_numpy(float)
    costs_raw = float((qty * float(cost) * (entry + exit_)).sum())
    gross_raw = float((qty * (exit_ - entry)).sum() + costs_raw)
    n = len(t)
    au = psa.audit_frame(t)
    return {
        "net": net, "trades": int(n),
        "per": round(net / n, 5) if n else 0.0,
        "gross": round(gross_raw, 2), "gross_raw": gross_raw,
        "costs": round(costs_raw, 2),
        "move": (gross_raw / n) if n else None,
        "cost_per": (costs_raw / n) if n else None,
        "median_hold": float(np.median(t["bars_held"].to_numpy(float))),
        "overlapping_trades": au["overlapping_trades"],
    }


TRADE_COLS = [
    "symbol", "exp", "entry_time", "exit_time", "entry", "exit", "notional",
    "pnl", "r_mult", "exit_side", "bars_held", "regime",
]


def save_trades(name: str, rows: list[dict]) -> None:
    frame = pd.DataFrame(rows)
    if frame.empty:
        frame = pd.DataFrame(columns=TRADE_COLS)
    frame.to_csv(OUT / f"trades_{name}.csv", index=False, encoding="utf-8-sig")


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


def fmt_move(st: dict) -> str:
    return "—" if st["move"] is None else f"{st['move']:.5f}"


def record(name: str, window: str, rows: list[dict], cost: float, seed, counted: bool,
           phase: str, extra: dict | None = None) -> dict:
    st = summarize(rows, cost)
    if st["overlapping_trades"] != 0:
        save_trades(name + "_OVERLAP", rows)
        raise SystemExit(f"تداخل ≠ 0 في {name}")
    rec = {
        "القياس": name, "الفترة": window, "counted": counted, "cost": cost,
        "seed": seed, "المرحلة": phase, **st,
    }
    if extra:
        rec.update(extra)
    if counted:
        log_measurement(name, window, phase)
        MEASURED.append(rec)
    tag = f"{len(LEDGER)}/{CAP}" if counted else "لا يُحسب"
    print(
        f"  [{tag}] {name} {window}: net={st['net']} صفقات={st['trades']} حركة={fmt_move(st)}",
        flush=True,
    )
    return rec


def gate(label: str, st: dict, spec: dict) -> None:
    ok_net = abs(st["net"] - spec["net"]) <= 0.5
    ok_n = st["trades"] == spec["n"]
    ok_m = True if spec["move"] is None else (
        st["move"] is not None and abs(st["move"] - spec["move"]) <= 1.5e-5
    )
    print(f"  تحقق {label}: {st['net']}$ / {st['trades']} حركة={fmt_move(st)}", flush=True)
    if not (ok_net and ok_n and ok_m) or st["overlapping_trades"]:
        raise SystemExit(f"الواقع خالف الورقة: {label} = {st}. أوقف.")


def run_canary() -> dict:
    can = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "canary.py"), "--json"],
        capture_output=True, text=True,
    )
    raw = can.stdout
    cj = json.loads(raw[raw.index("{"):]) if "{" in raw else {}
    print(f"  كاناري المحرك الحي: {cj.get('canary')} net={cj.get('got', {}).get('net')}")
    if cj.get("canary") != "ok":
        raise SystemExit("الكاناري لم يُرجع canary=ok — أوقف")
    return cj


def run_selftests() -> None:
    for tool in ("fill_invariant_check.py", "position_sequencing_audit.py"):
        st = subprocess.run(
            [sys.executable, str(ROOT / "tools" / tool), "--selftest"],
            capture_output=True, text=True,
        )
        tail = (st.stdout or st.stderr).strip().splitlines()
        print(f"  {tool}: {(tail[-1] if tail else 'بلا مخرج')} (exit={st.returncode})")
        if st.returncode != 0:
            raise SystemExit(f"{tool} selftest فشل")


def lab_canary_status() -> str:
    csv = ROOT / "history" / "research" / "hyp_lab_out" / "L0046" / "phase3_basis_repaired.csv"
    if not csv.exists():
        msg = "لم يُشغَّل: phase3_basis_repaired.csv غير موجود. لم يُصنَّع بديل."
        print(f"  كاناري المختبر: {msg}")
        return msg
    st = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "canary_lab.py"), "--json"],
        capture_output=True, text=True,
    )
    return st.stdout.strip()


def load_frozen_map() -> tuple[set[tuple[str, str]], dict]:
    mp = json.loads(MAP_SRC.read_text(encoding="utf-8"))
    enabled = {tuple(x) for x in mp["enabled"]}
    if enabled != FROZEN_ENABLED or len(enabled) != 11 or mp["n_excluded"] != 10:
        raise SystemExit("الخريطة ليست المجمَّدة")
    digest = hashlib.sha256(MAP_SRC.read_bytes()).hexdigest()
    if not digest.startswith("14df873e"):
        raise SystemExit(f"بصمة الخريطة {digest} ليست 14df873e")
    if any(len(x) != 2 for x in mp["enabled"]):
        raise SystemExit("الخريطة ليست (عمود × مناخ)")
    shutil.copyfile(MAP_SRC, OUT / "routing_map.json")
    return enabled, mp


def use_syms(syms: list[str]) -> None:
    global SYMS
    SYMS = list(syms)
    R48.SYMS = SYMS


def prepare() -> None:
    L36.set_core()
    NC.EMA_FAST = 8
    M213._cache.clear()
    R48._SIG.clear()
    C.STOP_ATR = STOP
    restore_cost()
    cells = R48._cells()
    got = sorted({c["symbol"] for c in cells})
    if set(got) != BASE_COINS:
        raise SystemExit(f"سلة الخلايا تختلف: {sorted(set(got) ^ BASE_COINS)}")
    use_syms(got)
    R48.BAR = BAR
    R48.frames = R46.frames
    global ENABLED
    ENABLED, _ = load_frozen_map()
    print(f"  خلايا={len(cells)} عملات الأساس={len(SYMS)} خريطة={len(ENABLED)}")
    R46.build_cache(sorted(archive_symbols()))


def archive_symbols() -> list[str]:
    return sorted(p.name.split("_")[0] for p in (ROOT / "crypto_archive").glob("*USDT_1m.parquet"))


def coin_span() -> pd.DataFrame:
    import pyarrow.parquet as pq
    rows = []
    for p in sorted((ROOT / "crypto_archive").glob("*USDT_1m.parquet")):
        pf = pq.ParquetFile(p)
        first = pf.read_row_group(0, columns=["open_time"]).column("open_time")[0].as_py()
        last = pf.read_row_group(pf.num_row_groups - 1, columns=["open_time"]).column("open_time")[-1].as_py()
        sym = p.name.split("_")[0]
        start = pd.to_datetime(first, unit="ms", utc=True)
        end = pd.to_datetime(last, unit="ms", utc=True)
        rows.append({
            "symbol": sym,
            "في_السلة_15": sym in BASE_COINS,
            "زائدة": sym not in BASE_COINS,
            "start": str(start),
            "end": str(end),
            "تبدأ_بعد_الاختيار": start > pd.Timestamp(DEC_S, tz="UTC"),
            "تنتهي_قبل_الحكم": end < pd.Timestamp(JUD_S, tz="UTC"),
            "rows": int(pf.metadata.num_rows),
        })
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "coin_span.csv", index=False, encoding="utf-8-sig")
    return df


def build_regimes(syms: list[str]) -> None:
    print("\n══ مصنّف يومي shift(1) ══")
    for sym in syms:
        path = DAILY / f"{sym}_1d.parquet"
        if not path.exists():
            d1 = C.load(str(ROOT / "crypto_archive" / f"{sym}_1m.parquet"), start=WARM, end=JUD_E)
            C.to_bars(d1, 1440).to_parquet(path)
            del d1
            print(f"  يومي {sym}", flush=True)
        dly = pd.read_parquet(path)
        if dly.index.tz is None:
            dly.index = dly.index.tz_localize("UTC")
        if len(dly) < 2:
            REG4H[sym] = pd.Series(dtype=object)
            print(f"  {sym}: يومي أقصر من شمعتين. لا يُسقط.")
            continue
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
        REG4H[sym] = pd.Series([lookup.get(ts.normalize(), np.nan) for ts in f.index], index=f.index, dtype=object)


def entry_regime(sym: str, index: pd.DatetimeIndex) -> pd.Series:
    return REG4H[sym].reindex(index).shift(-1)


def column_only(df, sym, col: str) -> pd.Series:
    return R48.column_signal(df, sym, col).reindex(df.index, fill_value=False).fillna(False).astype(bool)


def routed_signal(df, sym, enabled: set[tuple[str, str]]) -> pd.Series:
    sig = pd.Series(False, index=df.index)
    er = entry_regime(sym, df.index)
    for col, regime in enabled:
        sig = sig | (column_only(df, sym, col) & (er == regime))
    return sig


def apply_static(df: pd.DataFrame, sig: pd.Series, parts: tuple) -> pd.Series:
    out = sig.fillna(False).astype(bool).copy()
    vol = df["volume"]
    vol_ma = vol.shift(1).rolling(20, min_periods=20).mean()
    atr = C.atr(df)
    body = (df["close"] - df["open"]).abs()
    rng = df["high"] - df["low"]
    for part in parts:
        kind = part[0]
        if kind == "vol":
            out = out & vol_ma.notna() & (vol > float(part[1]) * vol_ma)
        elif kind == "atr":
            out = out & atr.notna() & (df["close"] > 0) & (atr / df["close"] >= float(part[1]))
        elif kind == "body":
            out = out & (rng > 0) & (body / rng >= float(part[1]))
        elif kind == "cool":
            continue
        else:
            raise SystemExit(f"جزء غير مسموح: {part}")
    return out.fillna(False)


def cool_n(parts: tuple) -> int | None:
    ns = [int(p[1]) for p in parts if p[0] == "cool"]
    return max(ns) if ns else None


def outcomes_for(sym: str, s0: str, s1: str) -> list:
    key = (sym, s0, s1, round(float(R48.COST), 6))
    if key not in OUTCOME_CACHE:
        OUTCOME_CACHE[key] = R48.outcomes_for(sym, s0, s1)
    return OUTCOME_CACHE[key]


def simulate_mask(sig_of, s0: str, s1: str, exp: str, parts: tuple) -> tuple[list[dict], dict]:
    old = C.STOP_ATR
    C.STOP_ATR = STOP
    rows: list[dict] = []
    sig_in = sig_out = cool_blocked = 0
    ncool = cool_n(parts)
    try:
        for sym in SYMS:
            df = R46.frames(sym)
            win = R48.window(df, s0, s1)
            if len(win) < 100:
                continue
            base = sig_of(df, sym).reindex(win.index, fill_value=False).fillna(False).astype(bool)
            sig_in += int(base.sum())
            sg = apply_static(df, base, parts).reindex(win.index, fill_value=False).fillna(False).astype(bool)
            sig_out += int(sg.sum())
            if ncool is None:
                _, tr = C.simulate(
                    win, sg, C.atr(win), notional=C.TRADE_USD, bar_secs=BAR,
                    strict_single=True, atr_trail=TRAIL,
                )
                rows.extend(C.trade_rows(sym, exp, tr))
            else:
                outcomes = outcomes_for(sym, s0, s1)
                accepted = np.zeros(len(win), dtype=bool)
                last_exit = -1
                cool_until = -1
                for i in np.flatnonzero(sg.to_numpy()):
                    if i >= len(outcomes) or outcomes[i] is None:
                        continue
                    if last_exit > i:
                        continue
                    if i <= cool_until:
                        cool_blocked += 1
                        continue
                    rec = outcomes[i]
                    accepted[i] = True
                    last_exit = int(rec["exit_j"])
                    if round(float(rec["pnl"]), 4) < 0:
                        cool_until = max(cool_until, int(rec["exit_j"]) + ncool - 1)
                rows.extend(R48.rows_from_chosen(sym, exp, R48.greedy(outcomes, accepted)))
    finally:
        C.STOP_ATR = old
    return tag_regime(rows), {"sig_in": sig_in, "sig_out": sig_out, "cool_blocked": cool_blocked}


def run_book(name: str, fname: str, sig_of, parts: tuple, s0: str, s1: str, window: str,
             cost: float, counted: bool, phase: str, extra: dict | None = None) -> tuple[dict, list[dict]]:
    set_cost(cost)
    try:
        rows, meta = simulate_mask(sig_of, s0, s1, name, parts)
        save_trades(fname, rows)
        rec = record(name, window, rows, cost, None, counted, phase, {**(extra or {}), **meta})
        return rec, rows
    finally:
        restore_cost()


def routed(enabled: set[tuple[str, str]]):
    def sig_of(df, sym, enabled=enabled):
        return routed_signal(df, sym, enabled)
    return sig_of


def cell_sig(col: str, regime: str):
    def sig_of(df, sym, col=col, regime=regime):
        return column_only(df, sym, col) & (entry_regime(sym, df.index) == regime)
    return sig_of


def qualifies(rec: dict) -> bool:
    return rec["net"] > 0 and rec["move"] is not None and rec["move"] >= 0.10


def seeds_for(rows_direct: list[dict], s0: str, s1: str, window: str, tag: str) -> list[dict]:
    set_cost(COST_REF)
    out = []
    try:
        outs = {}
        for sym in SYMS:
            win = R48.window(R46.frames(sym), s0, s1)
            if len(win) < 100:
                continue
            outs[sym] = outcomes_for(sym, s0, s1)
        t = pd.DataFrame(rows_direct) if rows_direct else pd.DataFrame(columns=["symbol"])
        tgt = {sym: int((t["symbol"] == sym).sum()) if len(t) else 0 for sym in outs}
        for seed in SEEDS:
            rows = []
            for sym, table in outs.items():
                u = R48.uniforms(seed, sym, len(table))
                p = R48.match_p(table, u, tgt.get(sym, 0))
                rows.extend(R48.rows_from_chosen(sym, f"rnd{seed}", R48.greedy(table, u < p)))
            save_trades(f"rnd_{tag}_s{seed}", rows)
            out.append(record(f"عشوائي بذرة {seed}", window, rows, COST_REF, seed, True, "د"))
    finally:
        restore_cost()
    return out


def verify_deposited() -> None:
    s = pd.read_csv(ROOT / "history/research/hyp_lab_out/L0055/neighborhood_selection.csv")
    j = pd.read_csv(ROOT / "history/research/hyp_lab_out/L0055/neighborhood_judgement.csv")
    paper = {
        3.1: (8.40, 383, 29.56, 569),
        3.2: (10.76, 367, 44.06, 529),
        3.3: (28.30, 345, 43.52, 492),
        3.4: (40.26, 327, 58.90, 462),
        3.5: (48.98, 302, 22.72, 434),
    }
    sj = {float(r.k): r for _, r in s.iterrows()}
    jj = {float(r.k): r for _, r in j.iterrows()}
    for k, (ns, nt, js, jt) in paper.items():
        if abs(float(sj[k].net) - ns) > 0.5 or int(sj[k].trades) != nt:
            raise SystemExit(f"اختيار L0055 خالف الورقة عند {k}")
        if abs(float(jj[k].net) - js) > 0.5 or int(jj[k].trades) != jt:
            raise SystemExit(f"حكم L0055 خالف الورقة عند {k}")
    m = pd.read_csv(ROOT / "history/research/hyp_lab_out/L0054/measurements.csv")
    hit = m[(m["القياس"].astype(str).str.contains("تهدئة")) & (m["الفترة"] == "حكم") & (np.isclose(m["cost"], 0.0013))]
    if hit.empty or abs(float(hit.iloc[0].net) - 18.51) > 0.5 or int(hit.iloc[0].trades) != 434:
        raise SystemExit("حكم 0.13% في ملف L0054 خالف الورقة")
    thin = s[s["k"] > 3.5]
    if list(thin.sort_values("k")["trades"].astype(int)) != [286, 259, 229, 184, 144]:
        raise SystemExit("صفقات ما فوق 3.5 خالفت الورقة")
    print("  ✅ ملفات L0054/L0055 تطابق جدول الورقة")


def old_column_silence(extras: list[str]) -> dict:
    out = {}
    for sym in extras:
        df = R46.frames(sym)
        counts = {}
        for col in OLD_COLS:
            counts[col] = int(column_only(df, sym, col).sum())
        out[sym] = counts
        if any(counts.values()):
            raise SystemExit(f"عمود قديم أطلق إشارة على {sym} بلا خلية مودَعة: {counts}")
    (OUT / "new_coin_old_columns.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  أعمدة قديمة على الزائدات = صفر: {out}")
    return out


def guards() -> None:
    print("\n══ حرّاس ══")
    bad = []
    frames = pathlib.Path.home() / ".cache" / "l0046_frames"
    files = sorted(OUT.glob("trades_*.csv"))
    for f in files:
        cost = 0.0013 if "c00130" in f.name else 0.0010
        st = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "fill_invariant_check.py"),
             "--trades", str(f), "--frames", str(frames), "--cost", str(cost), "--bar-tag", "4h"],
            capture_output=True, text=True,
        )
        if st.returncode != 0 or "تُخطّي=0" not in st.stdout or "شموع ناقصة=0" not in st.stdout:
            bad.append(f.name)
            print(" FAIL", f.name, (st.stdout or st.stderr)[-300:])
        au = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "position_sequencing_audit.py"),
             "--trades", str(f), "--require-zero"],
            capture_output=True, text=True,
        )
        if au.returncode != 0:
            bad.append(f.name + " seq")
    if bad:
        raise SystemExit("حارس فشل: " + ", ".join(bad))
    print(f"  ✅ {len(files)} ملفًا")


def dump_json(path: pathlib.Path, obj) -> None:
    def conv(o):
        if isinstance(o, (set, tuple)):
            return list(o)
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        raise TypeError(type(o))
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=conv), encoding="utf-8")


def slim(rec: dict) -> dict:
    keep = (
        "id", "القياس", "الفترة", "المرحلة", "cost", "seed", "net", "trades", "per",
        "gross", "move", "cost_per", "costs", "median_hold", "sig_in", "sig_out",
        "cool_blocked", "column", "regime", "basket",
    )
    out = {}
    for key in keep:
        if key in rec and rec[key] is not None:
            v = rec[key]
            if isinstance(v, float) and key in ("move", "cost_per"):
                v = round(v, 8)
            out[key] = v
    return out


def write_precommit() -> None:
    (OUT / "grid_precommitted.txt").write_text("\n".join([
        "مكتوب قبل أي رقم.",
        CHOICE_RULE,
        REOPEN_RULE,
        ACCEPT_RULE,
        "تعريف الحجم = L0055: حجم شمعة الإشارة > k × متوسط 20 سابقة shift(1).",
        "التهدئة = L0055: بعد pnl مُقرَّب < 0 تُمنع إشارات i حيث exit_j <= i <= exit_j+2.",
        "الجسم = L0054: |إغلاق-افتتاح|/المدى ≥ 0.4. المدى 0 يُرفض.",
        "التقلب = L0054: ATR/الإغلاق ≥ 0.010.",
        "الزائدات تُضاف كلها دفعة واحدة. لا انتقاء. لا حذف.",
        "الخريطة (عمود×مناخ) تُطبَّق كما هي. لا خلية قديمة تُختلق لعملة جديدة.",
        "عملة بلا بيانات في فترة تُذكر ولا تُسقط.",
        "مرحلة د تتجاوز سقف 6 لأن البذور لا تُقطع. المجموع دون 38.",
        "لا بحث عن k خارج الجدول. لا تغيير للخروج أو منطق الأعمدة.",
    ]) + "\n", encoding="utf-8")


def pick_choice(cands: list[dict]) -> dict | None:
    good = [c for c in cands if qualifies(c)]
    if not good:
        return None
    good.sort(key=lambda r: (-r["trades"], -(r["move"] or 0), r.get("order", 99), r["id"]))
    return good[0]


def article5(sel: dict, jud10: dict, jud13: dict, rnd_sel: list[dict], rnd_jud: list[dict]) -> dict:
    luck_s = max(r["net"] for r in rnd_sel) if rnd_sel else None
    luck_j = max(r["net"] for r in rnd_jud) if rnd_jud else None
    rows = [
        {"الشرط": "صافٍ موجب في الفترتين عند 0.10%", "الحد": "> 0 و > 0",
         "القيمة": f"{sel['net']} / {jud10['net']}",
         "مستوفى": bool(sel["net"] > 0 and jud10["net"] > 0)},
        {"الشرط": "صافٍ موجب في الحكم عند 0.13%", "الحد": "> 0",
         "القيمة": jud13["net"], "مستوفى": bool(jud13["net"] > 0)},
        {"الشرط": "صفقات الاختيار", "الحد": "≥ 400",
         "القيمة": sel["trades"], "مستوفى": bool(sel["trades"] >= 400)},
        {"الشرط": "صفقات الحكم", "الحد": "≥ 550",
         "القيمة": jud10["trades"], "مستوفى": bool(jud10["trades"] >= 550)},
        {"الشرط": "حركة الحكم", "الحد": "≥ 0.055$",
         "القيمة": None if jud10["move"] is None else round(jud10["move"], 5),
         "مستوفى": bool(jud10["move"] is not None and jud10["move"] >= 0.055)},
        {"الشرط": "فوق أسعد بذرة في الفترتين", "الحد": "اختيار وحكم",
         "القيمة": f"{sel['net']} مقابل {luck_s} · {jud10['net']} مقابل {luck_j}",
         "مستوفى": bool(luck_s is not None and luck_j is not None and sel["net"] > luck_s and jud10["net"] > luck_j)},
    ]
    return {"مقبول": all(r["مستوفى"] for r in rows), "الشروط": rows,
            "أسعد_اختيار": luck_s, "أسعد_حكم": luck_j}


def write_outputs(canary, lab, payload) -> None:
    pd.DataFrame([slim(r) for r in MEASURED]).to_csv(OUT / "measurements.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(LEDGER).to_csv(OUT / "attempt_ledger.csv", index=False, encoding="utf-8-sig")
    rnd = [r for r in MEASURED if r.get("seed") is not None]
    rows = []
    if rnd:
        for window, g in pd.DataFrame(rnd).groupby("الفترة"):
            rows.append({
                "الفترة": window,
                "mean": round(float(g["net"].mean()), 2),
                "min": round(float(g["net"].min()), 2),
                "max": round(float(g["net"].max()), 2),
                "n": int(len(g)),
            })
    pd.DataFrame(rows).to_csv(OUT / "random_summary.csv", index=False, encoding="utf-8-sig")
    env = {
        "python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
        "cap": CAP, "counted": len(LEDGER), "seeds": list(SEEDS),
        "canary": canary.get("canary"), "canary_net": canary.get("got", {}).get("net"),
        "canary_lab": lab, "regime_py_used": False, "alternative_loader": False,
        "phase_d_over_ceiling": True, "phase_d_ceiling": 6,
        "choice_rule": CHOICE_RULE, "reopen_rule": REOPEN_RULE,
    }
    (OUT / "env_dump.txt").write_text(json.dumps(env, ensure_ascii=False, indent=2), encoding="utf-8")
    dump_json(OUT / "facts.json", payload)
    blobs = []
    for name in (
        "measurements.csv", "attempt_ledger.csv", "coin_span.csv", "cells_excluded.csv",
        "phase_c.csv", "routing_map_l0056.json", "final_choice.json", "facts.json",
        "routing_map.json",
    ):
        path = OUT / name
        if path.exists():
            blobs.append(f"{name} {hashlib.sha256(path.read_bytes()).hexdigest()}")
    (OUT / "sha256.txt").write_text("\n".join(blobs) + "\n", encoding="utf-8")
    print("\n".join(blobs))
    restore_cost()


def main() -> int:
    t0 = time.time()
    print("═" * 74)
    print(" L0056 — توسيع الكتاب. لا تطوير حرّ. السقف 38.")
    print("═" * 74)
    write_precommit()
    verify_deposited()
    canary = run_canary()
    run_selftests()
    lab = lab_canary_status()
    span = coin_span()
    extras = sorted(span.loc[span["زائدة"], "symbol"])
    print("  أرشيف", len(span), "زائدات", extras)
    if len(span) != 17 or extras != ["BNBUSDT", "HNTUSDT"]:
        raise SystemExit(f"الأرشيف ليس 17 أو الزائدات ليست BNB وHNT: {extras}")
    prepare()
    build_regimes(archive_symbols())
    silence = old_column_silence(extras)

    print("\n══ مرحلة 0 ══")
    use_syms(sorted(BASE_COINS))
    win_sel, _ = run_book(
        "فائز 3.5+تهدئة", f"p0_win_{cost_tag(COST_REF)}_SEL", routed(ENABLED), WINNER,
        DEC_S, DEC_E, "اختيار", COST_REF, False, "0", {"id": "ref", "basket": 15},
    )
    gate("فائز اختيار", win_sel, P0["win_sel"])
    win_jud, _ = run_book(
        "فائز 3.5+تهدئة", f"p0_win_{cost_tag(COST_REF)}_JUD", routed(ENABLED), WINNER,
        JUD_S, JUD_E, "حكم", COST_REF, False, "0", {"id": "ref", "basket": 15},
    )
    gate("فائز حكم 0.10%", win_jud, P0["win_jud"])
    win_013, _ = run_book(
        "فائز 3.5+تهدئة", f"p0_win_{cost_tag(0.0013)}_JUD", routed(ENABLED), WINNER,
        JUD_S, JUD_E, "حكم", 0.0013, False, "0", {"id": "ref", "basket": 15},
    )
    gate("فائز حكم 0.13%", win_013, P0["win_013"])
    k34, _ = run_book(
        "k=3.4 + تهدئة", f"p0_k34_{cost_tag(COST_REF)}_JUD", routed(ENABLED),
        (("vol", 3.4), ("cool", 3)), JUD_S, JUD_E, "حكم", COST_REF, False, "0",
        {"id": "k34", "basket": 15},
    )
    gate("k=3.4 حكم", k34, P0["k34_jud"])
    print("  ✅ الأربعة طابقت")

    print("\n══ مرحلة أ: سلة 17 ══")
    use_syms(archive_symbols())
    a_sel, a_rows = run_book(
        "سلة 17 + فائز", f"a17_{cost_tag(COST_REF)}_SEL", routed(ENABLED), WINNER,
        DEC_S, DEC_E, "اختيار", COST_REF, True, "أ",
        {"id": "basket17", "order": 1, "basket": 17},
    )
    a_jud, _ = run_book(
        "سلة 17 + فائز", f"a17_{cost_tag(COST_REF)}_JUD", routed(ENABLED), WINNER,
        JUD_S, JUD_E, "حكم", COST_REF, True, "أ",
        {"id": "basket17", "basket": 17},
    )
    by_coin = []
    if a_rows:
        t = pd.DataFrame(a_rows)
        for sym, g in t.groupby("symbol"):
            by_coin.append({"symbol": sym, "الفترة": "اختيار", "net": round(float(g["pnl"].sum()), 2), "trades": int(len(g))})
    # تفكيك الحكم من الملف، لا قياس جديد. يُكتب بعد الحفظ.
    jud_path = OUT / f"trades_a17_{cost_tag(COST_REF)}_JUD.csv"
    if jud_path.exists() and jud_path.stat().st_size:
        tj = pd.read_csv(jud_path)
        if len(tj):
            for sym, g in tj.groupby("symbol"):
                by_coin.append({"symbol": sym, "الفترة": "حكم", "net": round(float(g["pnl"].sum()), 2), "trades": int(len(g))})
    pd.DataFrame(by_coin).to_csv(OUT / "basket17_by_coin.csv", index=False, encoding="utf-8-sig")

    print("\n══ مرحلة ب: الخانات المقصاة، منفردة ══")
    use_syms(sorted(BASE_COINS))
    frozen = json.loads(MAP_SRC.read_text(encoding="utf-8"))
    excluded = [c for c in frozen["cells"] if not c["enabled"]]
    if len(excluded) != 10:
        raise SystemExit(f"المقصاة {len(excluded)} ≠ 10")
    cell_rows = []
    reopened = []
    for c in excluded:
        rec, _ = run_book(
            f"{c['column']} × {c['regime']}",
            f"cell_{c['column']}_{c['regime']}_{cost_tag(COST_REF)}_SEL",
            cell_sig(c["column"], c["regime"]), WINNER,
            DEC_S, DEC_E, "اختيار", COST_REF, True, "ب",
            {"column": c["column"], "regime": c["regime"], "basket": 15},
        )
        opened = rec["net"] > 0 and rec["trades"] >= MIN_CELL
        row = {
            "column": c["column"], "regime": c["regime"],
            "إقصاء_صافي": c["net"], "إقصاء_صفقات": c["trades"], "إقصاء_كلفة": frozen["cost"],
            "جديد_صافي": rec["net"], "جديد_صفقات": rec["trades"],
            "جديد_حركة": None if rec["move"] is None else round(rec["move"], 5),
            "أُعيدت": opened,
        }
        cell_rows.append(row)
        if opened:
            reopened.append([c["column"], c["regime"]])
        print(f"      إقصاء {c['net']}$/{c['trades']} → الآن {rec['net']}$/{rec['trades']} أُعيدت={opened}")
    pd.DataFrame(cell_rows).to_csv(OUT / "cells_excluded.csv", index=False, encoding="utf-8-sig")
    expanded_enabled = [list(x) for x in sorted(FROZEN_ENABLED)] + reopened
    # ترتيب ثابت
    expanded_enabled = sorted(expanded_enabled, key=lambda x: (x[0], x[1]))
    map_payload = {
        "source": "L0051/routing_map.json",
        "source_sha256": hashlib.sha256(MAP_SRC.read_bytes()).hexdigest(),
        "rule": REOPEN_RULE,
        "filter": "vol k=3.5 + cool 3",
        "cost": COST_REF,
        "period": [DEC_S, DEC_E],
        "method": "الخانة منفردة: عمود × مناخ، ثم المرشّح، لا شريحة من عمود مختلط",
        "enabled_frozen": [list(x) for x in sorted(FROZEN_ENABLED)],
        "reopened": reopened,
        "enabled": expanded_enabled,
        "n_enabled": len(expanded_enabled),
        "cells_measured": cell_rows,
        "written_before_judgement_measurement": True,
        "note": "أرقام الإقصاء من L0051 عند 0.13% بلا مرشّح حجم. القياس الجديد عند 0.10% مع المرشّح. ليسا التجربة نفسها.",
    }
    dump_json(OUT / "routing_map_l0056.json", map_payload)
    reread = json.loads((OUT / "routing_map_l0056.json").read_text(encoding="utf-8"))
    if reread["reopened"] != reopened:
        raise SystemExit("الخريطة المكتوبة لا تطابق الحساب")
    print(f"  خريطة أُودعت. أُعيد فتح {len(reopened)} من 10.")
    b_port = None
    b_rows = None
    if reopened:
        use_syms(sorted(BASE_COINS))
        enabled_b = {tuple(x) for x in reread["enabled"]}
        b_port, b_rows = run_book(
            "خريطة موسَّعة + فائز", f"bmap_{cost_tag(COST_REF)}_SEL", routed(enabled_b), WINNER,
            DEC_S, DEC_E, "اختيار", COST_REF, True, "ب",
            {"id": "map_expanded", "order": 2, "basket": 15},
        )
    else:
        print("  لا إعادة فتح. محفظة الخريطة = المرجع. لا تُعاد.")

    print("\n══ مرحلة ج: k أخفّ مع معوّض ══")
    use_syms(sorted(BASE_COINS))
    c_recs = []
    for order, (cid, label, parts) in enumerate(PHASE_C, start=3):
        rec, rows = run_book(
            label, f"{cid}_{cost_tag(COST_REF)}_SEL", routed(ENABLED), parts,
            DEC_S, DEC_E, "اختيار", COST_REF, True, "ج",
            {"id": cid, "order": order, "basket": 15},
        )
        rec["_rows"] = rows
        c_recs.append(rec)
    pd.DataFrame([slim(r) for r in c_recs]).to_csv(OUT / "phase_c.csv", index=False, encoding="utf-8-sig")

    cands = [a_sel] + c_recs
    if b_port is not None:
        cands.append(b_port)
    choice = pick_choice(cands)
    choice_doc = {
        "rule": CHOICE_RULE,
        "written_before_judgement_of_choice": True,
        "candidates": [slim(r) for r in cands],
        "qualifying_ids": [r["id"] for r in cands if qualifies(r)],
        "choice_id": None if choice is None else choice["id"],
        "judgement_used": False,
    }
    dump_json(OUT / "final_choice.json", choice_doc)
    frozen_choice = json.loads((OUT / "final_choice.json").read_text(encoding="utf-8"))
    if frozen_choice["choice_id"] != choice_doc["choice_id"]:
        raise SystemExit("الاختيار المكتوب لا يطابق")
    print(f"\n══ الاختيار المجمَّد: {frozen_choice['choice_id']} ══")

    jud10 = jud13 = None
    rnd_sel: list[dict] = []
    rnd_jud: list[dict] = []
    choice_rows_sel = None
    if choice is None:
        print("  لا تركيب مؤهّل. لا حكم إضافي. لا بذور.")
    else:
        cid = choice["id"]
        if cid == "basket17":
            use_syms(archive_symbols())
            parts = WINNER
            enabled_d = ENABLED
            choice_rows_sel = a_rows
            jud10 = a_jud
            print("  حكم 0.10% للسلة 17 مقيس في المرحلة أ. لا يُعاد.")
        elif cid == "map_expanded":
            use_syms(sorted(BASE_COINS))
            parts = WINNER
            enabled_d = {tuple(x) for x in reread["enabled"]}
            choice_rows_sel = b_rows
        else:
            use_syms(sorted(BASE_COINS))
            parts = dict((x[0], x[2]) for x in PHASE_C)[cid]
            enabled_d = ENABLED
            choice_rows_sel = next(r["_rows"] for r in c_recs if r["id"] == cid)
        sig = routed(enabled_d)
        if jud10 is None:
            jud10, _ = run_book(
                f"فائز نهائي {cid}", f"d_{cid}_{cost_tag(COST_REF)}_JUD", sig, parts,
                JUD_S, JUD_E, "حكم", COST_REF, True, "د", {"id": cid},
            )
        jud13, _ = run_book(
            f"فائز نهائي {cid}", f"d_{cid}_{cost_tag(0.0013)}_JUD", sig, parts,
            JUD_S, JUD_E, "حكم", 0.0013, True, "د", {"id": cid},
        )
        print("  عشوائي الاختيار")
        rnd_sel = seeds_for(choice_rows_sel, DEC_S, DEC_E, "اختيار", f"{cid}_SEL")
        print("  عشوائي الحكم")
        # عدد صفقات الحكم عند 0.10%. نعيد بناء صفوف الحكم إن لم تكن في الذاكرة.
        if cid == "basket17":
            jud_rows = pd.read_csv(OUT / f"trades_a17_{cost_tag(COST_REF)}_JUD.csv").to_dict("records")
        else:
            jud_rows = pd.read_csv(OUT / f"trades_d_{cid}_{cost_tag(COST_REF)}_JUD.csv").to_dict("records")
        rnd_jud = seeds_for(jud_rows, JUD_S, JUD_E, "حكم", f"{cid}_JUD")

    accept = None if choice is None else article5(choice, jud10, jud13, rnd_sel, rnd_jud)
    if accept is not None:
        dump_json(OUT / "acceptance.json", accept)
        print(f"  القبول: {accept['مقبول']}")
    expected_min = 2 + 10 + 4
    if len(LEDGER) < expected_min or len(LEDGER) > CAP:
        raise SystemExit(f"العدّ خارج المتوقع: {len(LEDGER)}")
    write_outputs(canary, lab, {
        "counted": len(LEDGER),
        "extras": extras,
        "old_columns_on_extras": silence,
        "reopened": reopened,
        "choice_id": None if choice is None else choice["id"],
        "acceptance": accept,
        "reference_selection": slim(win_sel),
        "reference_judgement_010": slim(win_jud),
        "reference_judgement_013": slim(win_013),
        "basket17_selection": slim(a_sel),
        "basket17_judgement": slim(a_jud),
        "map_portfolio": None if b_port is None else slim(b_port),
        "phase_c": [slim(r) for r in c_recs],
        "cells": cell_rows,
    })
    guards()
    print(f"انتهى في {time.time()-t0:.0f}s  العدّ={len(LEDGER)}/{CAP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
