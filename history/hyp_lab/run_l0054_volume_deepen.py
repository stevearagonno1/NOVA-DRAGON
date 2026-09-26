# -*- coding: utf-8 -*-
"""L0054 — تعميق فلتر الحجم وتركيبه. قياس وحكم.

المتغيّر الوحيد: مرشّحات الدخول. الخريطة تُنسخ. تعريف الحجم منسوخ من L0053
حرفيًا: حجم شمعة الإشارة > k × متوسط الـ20 السابقة (shift(1)، لا تضمّ نفسها).

القواعد مكتوبة هنا قبل أي رقم حكم.

السقف 40.
  مرحلة 0 (لا تُحسب): أربعة مراجع الورقة.
  مرحلة 1 (5 من سقف 8): k = 2.0 2.2 2.5 3.0 3.5 على الاختيار عند 0.10%.
      k=1.8 من المرحلة 0 ولا يُعاد عدّه. ثلاثة مقاعد لا تُملأ بعد الرؤية.
  مرحلة 2 (حتى 6 من سقف 14): أفضل k مؤهّل (≥300) + كل عائلة (4)
      ثم + أفضل عائلتين بحسب حركة التركيب + ثم + أفضل ثلاث.
      لا تركيب حجم مع حجم. لا عائلة رابعة تُستدعى بعد الرؤية.
  مرحلة 3 (13 من سقف 18) إن وُجد فائز:
      حكم 0.10% و0.13% و0.075% · عشوائي 0.10% حكم ×5 · عشوائي 0.10% اختيار ×5.
      اختيار الفائز عند 0.10% من المرحلة 1 أو 2، لا يُعاد عدّه.
      اختيار الفائز عند 0.13% و0.075% لم يُقَس. لا يُضاف بعد الرؤية.
  إن لم يَفُز أحد: لا حكم.

بذور: 110054 210054 310054 410054 510054.
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

ROOT = pathlib.Path("/home/user/l0054")
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

OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0054"
OUT.mkdir(parents=True, exist_ok=True)
DAILY = pathlib.Path.home() / ".cache" / "l0054_daily"
DAILY.mkdir(parents=True, exist_ok=True)
MAP_SRC = ROOT / "history" / "research" / "hyp_lab_out" / "L0051" / "routing_map.json"

DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
WARM = "2021-06-01"
SEEDS = (110054, 210054, 310054, 410054, 510054)
CAP = 40
DEFAULT_COST = 0.0013
COST_REF = 0.0010
STOP = 2.5
TRAIL = 4.0
BAR = 4 * 3600
REGIMES = ("صاعد", "عرضي", "هابط")
MIN_SEL = 300
MIN_JUD = 400
MOVE_TARGET = 0.055

# بوابة المرحلة 0. ±0.5$ على الدولار، وعدد الصفقات حرفيًا، والحركة ضمن 1.5e-5.
P0 = {
    ("base", "SEL"): {"net": 34.56, "n": 1041, "move": None, "gross": None},
    ("base", "JUD"): {"net": -14.36, "n": 1605, "move": 0.03104, "gross": None},
    ("k18", "SEL"): {"net": 106.03, "n": 884, "move": 0.16006, "gross": 141.49},
    ("k18", "JUD"): {"net": 5.01, "n": 1242, "move": 0.04404, "gross": 54.69},
}

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

# k=1.8 مرجع المرحلة 0. الخمسة الجديدة فقط تُحسب. الترتيب كسر تعادل.
K_AXIS = [
    {"id": "vol_k1.8", "label": "حجم k=1.8", "k": 1.8, "order": 0, "counted": False},
    {"id": "vol_k2.0", "label": "حجم k=2.0", "k": 2.0, "order": 1, "counted": True},
    {"id": "vol_k2.2", "label": "حجم k=2.2", "k": 2.2, "order": 2, "counted": True},
    {"id": "vol_k2.5", "label": "حجم k=2.5", "k": 2.5, "order": 3, "counted": True},
    {"id": "vol_k3.0", "label": "حجم k=3.0", "k": 3.0, "order": 4, "counted": True},
    {"id": "vol_k3.5", "label": "حجم k=3.5", "k": 3.5, "order": 5, "counted": True},
]
ADDONS = [
    {"id": "body_b0.4", "label": "جسم b=0.4", "parts": (("body", 0.4),), "order": 0},
    {"id": "atr_v0.010", "label": "تقلب v=0.010", "parts": (("atr", 0.010),), "order": 1},
    {"id": "cool_n3", "label": "تهدئة n=3", "parts": (("cool", 3),), "order": 2},
    {"id": "confirm", "label": "شمعة التأكيد", "parts": (("confirm",),), "order": 3},
]

LEDGER: list[dict] = []
MEASURED: list[dict] = []
REG4H: dict[str, pd.Series] = {}
SYMS: list[str] = []
ENABLED: set[tuple[str, str]] = set()
RULE = (
    "أفضل k = أعلى حركة اختيار بين {1.8 والخمسة} بشرط صفقات ≥ 300. "
    "الفائز = أعلى حركة اختيار بين {أفضل k ومركّباته المقيسة مع عائلات مختلفة}، "
    "بشرط ≥ 300 وصافٍ مُقرَّب > 0. "
    "كسر التعادل: صافٍ أعلى، ثم صفقات أكثر، ثم ترتيب القياس. "
    "لا فائز ⇒ لا حكم. لا استبدال بعد الرؤية. لا حجم مع حجم."
)


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
        return {
            "net": 0.0, "trades": 0, "per": 0.0, "gross": 0.0, "gross_raw": 0.0,
            "costs": 0.0, "move": None, "cost_per": None, "median_hold": 0.0,
            "overlap_ratio": 0.0, "max_concurrent": 0, "overlapping_trades": 0,
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
    hold = t["bars_held"].to_numpy(float)
    au = psa.audit_frame(t)
    return {
        "net": net, "trades": int(n),
        "per": round(net / n, 5) if n else 0.0,
        "gross": round(gross_raw, 2), "gross_raw": gross_raw,
        "costs": round(costs_raw, 2),
        "move": (gross_raw / n) if n else None,
        "cost_per": (costs_raw / n) if n else None,
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


def fmt_move(st: dict) -> str:
    return "—" if st["move"] is None else f"{st['move']:.5f}"


def record(name: str, window: str, rows: list[dict], cost: float, seed, counted: bool,
           extra: dict | None = None) -> dict:
    st = summarize(rows, cost)
    if st["overlapping_trades"] != 0:
        save_trades(name + "_OVERLAP", rows)
        raise SystemExit(f"تداخل ≠ 0 في {name} {window}: {st}")
    rec = {"القياس": name, "الفترة": window, "counted": counted, "cost": cost, "seed": seed, **st}
    if extra:
        rec.update(extra)
    if counted:
        log_measurement(name, window, {"cost": cost, "seed": "" if seed is None else seed})
        MEASURED.append(rec)
    tag = f"{len(LEDGER)}/{CAP}" if counted else "لا يُحسب"
    print(
        f"  [{tag}] {name} {window}: net={st['net']} صفقات={st['trades']} "
        f"حركة={fmt_move(st)} إجمالي={st['gross']} كلفة={st['costs']} وسيط={st['median_hold']}",
        flush=True,
    )
    return rec


def gate(label: str, st: dict, spec: dict) -> None:
    ok_net = abs(st["net"] - spec["net"]) <= 0.5
    ok_n = st["trades"] == spec["n"]
    ok_m = True if spec["move"] is None else (
        st["move"] is not None and abs(st["move"] - spec["move"]) <= 1.5e-5
    )
    ok_g = True if spec["gross"] is None else abs(st["gross"] - spec["gross"]) <= 0.5
    print(
        f"  تحقق {label}: {st['net']}$ / {st['trades']} حركة={fmt_move(st)} إجمالي={st['gross']} "
        f"مرجع net={spec['net']} n={spec['n']} move={spec['move']}",
        flush=True,
    )
    if not (ok_net and ok_n and ok_m and ok_g) or st["overlapping_trades"]:
        raise SystemExit(
            f"الواقع خالف الورقة: {label} = {st['net']}$ / {st['trades']} حركة {st['move']} "
            f"إجمالي {st['gross']}. المرجع {spec}. أوقف. لا تعميق."
        )


def run_canary() -> dict:
    can = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "canary.py"), "--json"],
        capture_output=True, text=True,
    )
    raw = can.stdout
    cj = json.loads(raw[raw.index("{"):]) if "{" in raw else {}
    print(f"  كاناري المحرك الحي: {cj.get('canary')} net={cj.get('got', {}).get('net')}")
    if cj.get("canary") != "ok":
        print((can.stdout or "")[-800:])
        print((can.stderr or "")[-400:])
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
            raise SystemExit(f"{tool} selftest فشل — أوقف")


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
    print(st.stdout.strip() or st.stderr[-400:])
    return st.stdout.strip()


def load_frozen_map() -> set[tuple[str, str]]:
    if not MAP_SRC.exists():
        raise SystemExit("خريطة L0051 غير موجودة. لا أولّدها.")
    mp = json.loads(MAP_SRC.read_text(encoding="utf-8"))
    enabled = {tuple(x) for x in mp["enabled"]}
    if enabled != FROZEN_ENABLED or len(enabled) != 11:
        raise SystemExit(f"الخريطة ليست المجمَّدة: {sorted(enabled)}")
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
    print("\n══ مصنّف يومي shift(1) ══")
    for sym in SYMS:
        path = DAILY / f"{sym}_1d.parquet"
        if not path.exists():
            t0 = time.time()
            d1 = C.load(str(ROOT / "crypto_archive" / f"{sym}_1m.parquet"), start=WARM, end=JUD_E)
            C.to_bars(d1, 1440).to_parquet(path)
            del d1
            print(f"  يومي {sym} ({time.time() - t0:.1f}s)", flush=True)
        dly = pd.read_parquet(path)
        if dly.index.tz is None:
            dly.index = dly.index.tz_localize("UTC")
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
            index=f.index, dtype=object,
        )


def entry_regime(sym: str, index: pd.DatetimeIndex) -> pd.Series:
    return REG4H[sym].reindex(index).shift(-1)


def routed_signal(df, sym) -> pd.Series:
    sig = pd.Series(False, index=df.index)
    er = entry_regime(sym, df.index)
    for col, regime in ENABLED:
        sg = R48.column_signal(df, sym, col).reindex(df.index, fill_value=False).fillna(False).astype(bool)
        sig = sig | (sg & (er == regime))
    return sig


def shift_confirm(df: pd.DataFrame, base: pd.Series) -> pd.Series:
    prev_sig = base.shift(1)
    prev_sig = prev_sig.where(prev_sig.notna(), False).astype(bool)
    prev_close = df["close"].shift(1)
    ok = prev_sig & prev_close.notna() & (df["close"] > prev_close)
    return ok.fillna(False)


def apply_static(df: pd.DataFrame, sig: pd.Series, parts: tuple) -> pd.Series:
    out = sig.fillna(False).astype(bool).copy()
    if not parts:
        return out
    vol = df["volume"]
    vol_ma = vol.shift(1).rolling(20, min_periods=20).mean()
    a = C.atr(df)
    body = (df["close"] - df["open"]).abs()
    rng = df["high"] - df["low"]
    for part in parts:
        kind = part[0]
        if kind == "vol":
            out = out & vol_ma.notna() & (vol > float(part[1]) * vol_ma)
        elif kind == "atr":
            out = out & a.notna() & (df["close"] > 0) & (a / df["close"] >= float(part[1]))
        elif kind == "body":
            out = out & (rng > 0) & (body / rng >= float(part[1]))
        elif kind in ("confirm", "cool"):
            continue
        else:
            raise SystemExit(f"جزء غير معروف: {part}")
    return out.fillna(False)


def machine_signal(df, sym, parts: tuple) -> pd.Series:
    base = routed_signal(df, sym)
    if sum(1 for p in parts if p[0] == "confirm") > 1:
        raise SystemExit("تأكيد مكرر")
    if any(p[0] == "confirm" for p in parts):
        base = shift_confirm(df, base)
    static = tuple(p for p in parts if p[0] not in ("confirm", "cool"))
    return apply_static(df, base, static)


def cool_n(parts: tuple) -> int | None:
    ns = [int(p[1]) for p in parts if p[0] == "cool"]
    return max(ns) if ns else None


def norm_parts(parts) -> list:
    out = []
    for p in parts:
        head = p[0]
        tail = [x if isinstance(x, str) else float(x) for x in p[1:]]
        out.append([head, *tail])
    return out


def simulate_mask(parts: tuple, s0: str, s1: str, exp: str) -> tuple[list[dict], dict]:
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
            sig_in += int(routed_signal(df, sym).reindex(win.index, fill_value=False).fillna(False).astype(bool).sum())
            full = machine_signal(df, sym, parts)
            sg = full.reindex(win.index, fill_value=False).fillna(False).astype(bool)
            sig_out += int(sg.sum())
            if ncool is None:
                _, tr = C.simulate(
                    win, sg, C.atr(win), notional=C.TRADE_USD, bar_secs=BAR,
                    strict_single=True, atr_trail=TRAIL,
                )
                rows.extend(C.trade_rows(sym, exp, tr))
            else:
                outcomes = R48.outcomes_for(sym, s0, s1)
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


def assert_equivalent(s0: str, s1: str, cost: float, parts: tuple, label: str) -> None:
    set_cost(cost)
    try:
        direct, _ = simulate_mask(parts, s0, s1, "eq")
        cached = []
        for sym in SYMS:
            df = R46.frames(sym)
            win = R48.window(df, s0, s1)
            if len(win) < 100:
                continue
            table = R48.outcomes_for(sym, s0, s1)
            sg = machine_signal(df, sym, parts).reindex(win.index, fill_value=False).fillna(False).astype(bool).to_numpy()
            cached.extend(R48.rows_from_chosen(sym, "eq", R48.greedy(table, sg)))
        ds, cs = summarize(direct, cost), summarize(cached, cost)
        if abs(ds["net"] - cs["net"]) > 0.01 or ds["trades"] != cs["trades"]:
            raise SystemExit(f"تكافؤ فشل {label}: {ds['net']}/{ds['trades']} ≠ {cs['net']}/{cs['trades']}")
        print(f"  ✅ تكافؤ {label}: {ds['net']}$ / {ds['trades']}")
    finally:
        restore_cost()


def reject_rate(trades: int, base: int) -> float | None:
    return None if not base else round(1.0 - trades / base, 4)


def run_spec(spec: dict, s0: str, s1: str, wname: str, cost: float, counted: bool,
             base_trades: int, order: int, fname: str) -> tuple[dict, list[dict]]:
    set_cost(cost)
    try:
        rows, meta = simulate_mask(tuple(spec["parts"]), s0, s1, spec["id"])
        save_trades(fname, rows)
        rec = record(spec["label"], wname, rows, cost, None, counted, {
            "id": spec["id"], "label": spec["label"], "parts": list(spec["parts"]),
            "order": order, "sig_in": meta["sig_in"], "sig_out": meta["sig_out"],
            "cool_blocked": meta["cool_blocked"],
        })
        rec["reject"] = reject_rate(rec["trades"], base_trades)
        rec["order"] = order
        print(f"      رفض={rec['reject']} إشارات {meta['sig_in']}→{meta['sig_out']} تهدئة_منعت={meta['cool_blocked']}")
        return rec, rows
    finally:
        restore_cost()


def pick_best_k(rows: list[dict]) -> dict | None:
    qual = [r for r in rows if r["trades"] >= MIN_SEL and r["move"] is not None]
    if not qual:
        return None
    qual.sort(key=lambda r: (-r["move"], -r["net"], -r["trades"], r["order"]))
    return qual[0]


def rank_addons(pair_recs: list[dict]) -> list[dict]:
    qual = [r for r in pair_recs if r["trades"] >= MIN_SEL and r["move"] is not None]
    qual.sort(key=lambda r: (-r["move"], -r["net"], -r["trades"], r["order"]))
    return qual


def pick_winner(cands: list[dict]) -> dict | None:
    qual = [r for r in cands if r["trades"] >= MIN_SEL and r["net"] > 0 and r["move"] is not None]
    if not qual:
        return None
    qual.sort(key=lambda r: (-r["move"], -r["net"], -r["trades"], r["order"]))
    return qual[0]


def seeds_for(rows_direct: list[dict], s0: str, s1: str, wname: str, cost: float, tag: str) -> list[dict]:
    print(f"\n══ بذور {wname} عند {cost:.3%} ══")
    set_cost(cost)
    out = []
    try:
        outs = {}
        for sym in SYMS:
            win = R48.window(R46.frames(sym), s0, s1)
            if len(win) < 100:
                continue
            outs[sym] = R48.outcomes_for(sym, s0, s1)
        t = pd.DataFrame(rows_direct) if rows_direct else pd.DataFrame(columns=["symbol"])
        tgt = {sym: int((t["symbol"] == sym).sum()) if len(t) else 0 for sym in outs}
        for seed in SEEDS:
            rows = []
            for sym, table in outs.items():
                u = R48.uniforms(seed, sym, len(table))
                p = R48.match_p(table, u, tgt.get(sym, 0))
                rows.extend(R48.rows_from_chosen(sym, f"rnd{seed}", R48.greedy(table, u < p)))
            save_trades(f"rnd_{tag}_{cost_tag(cost)}_s{seed}", rows)
            out.append(record(f"عشوائي {cost:.3%} بذرة {seed}", wname, rows, cost, seed, True))
    finally:
        restore_cost()
    return out


def decompositions(books: list[tuple[str, float, str, list[dict]]]) -> None:
    contrib = []
    for name, cost, lbl, rows in books:
        for reg in list(REGIMES) + ["غير مصنّف"]:
            part = [r for r in rows if r.get("regime") == reg]
            contrib.append({"القياس": name, "cost": cost, "الفترة": lbl, "المناخ": reg, **summarize(part, cost)})
    pd.DataFrame(contrib).to_csv(OUT / "regime_contribution.csv", index=False, encoding="utf-8-sig")
    print("  تفكيك المناخ كُتب (ليس قياسًا جديدًا)")


def guards() -> None:
    print("\n══ حرّاس ══")
    bad = []
    frames = pathlib.Path.home() / ".cache" / "l0046_frames"
    for f in sorted(OUT.glob("trades_*.csv")):
        cost = 0.0010
        for tag, c in (("c00075", 0.00075), ("c00100", 0.0010), ("c00130", 0.0013)):
            if tag in f.name:
                cost = c
                break
        st = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "fill_invariant_check.py"),
             "--trades", str(f), "--frames", str(frames),
             "--cost", str(cost), "--bar-tag", "4h"],
            capture_output=True, text=True,
        )
        if st.returncode != 0 or "تُخطّي=0" not in st.stdout or "شموع ناقصة=0" not in st.stdout:
            bad.append(f.name + " fill")
            print(" FAIL", f.name, (st.stdout or "")[-250:])
        else:
            line = next((ln for ln in st.stdout.splitlines() if f.name in ln), "")
            print(" ", line.strip())
        au = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "position_sequencing_audit.py"),
             "--trades", str(f), "--require-zero"],
            capture_output=True, text=True,
        )
        if au.returncode != 0:
            bad.append(f.name + " seq")
    if bad:
        raise SystemExit("حارس فشل: " + ", ".join(bad))
    print("  ✅ التعبئة والتسلسل")


def dump_json(path: pathlib.Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")


def _json_default(o):
    if isinstance(o, tuple):
        return list(o)
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    raise TypeError(type(o))


def slim(rec: dict) -> dict:
    keep = (
        "القياس", "الفترة", "cost", "seed", "net", "trades", "per", "gross", "move",
        "cost_per", "costs", "median_hold", "id", "label", "reject", "order",
        "sig_in", "sig_out", "cool_blocked", "parts", "members", "k",
    )
    out = {}
    for k in keep:
        if k in rec and rec[k] is not None:
            v = rec[k]
            if isinstance(v, float) and k in ("move", "cost_per"):
                v = round(v, 8)
            out[k] = v
    return out


def write_precommit() -> None:
    text = "\n".join([
        "مكتوب قبل أي رقم حكم.",
        RULE,
        "تعريف الحجم = L0053 حرفيًا: حجم شمعة إشارة الآلة > k × متوسط 20 شمعة سابقة بـ shift(1).",
        "الجسم: |إغلاق-افتتاح|/المدى ≥ 0.4. المدى 0 يُرفض.",
        "التقلب: ATR(14)/الإغلاق ≥ 0.010.",
        "التهدئة: بعد pnl مُقرَّب < 0، منع تعبئة n=3 شموع بعد شمعة الخروج.",
        "التأكيد: إزاحة شمعة إن أغلقَت التالية فوق إغلاق الإشارة. ثم تُطبَّق المرشّحات الساكنة على شمعة إشارة الآلة.",
        "أفضل عائلتين/ثلاث = أعلى حركة لتركيب (k + عائلة) على الاختيار، بشرط ≥ 300. لا تُختار من جدول L0053 بعد الرؤية.",
        "الحركة = الإجمالي الخام / الصفقات. الهدف 0.055 على حكم 0.10%، بلا تقريب إلى الأعلى.",
        "نسبة الرفض = 1 - صفقات المرشّح / صفقات المسنَدة بلا مرشّح في الفترة نفسها.",
        "بذور: 110054 210054 310054 410054 510054. عشوائي دخول حرّ بعدد الصفقات لكل عملة، لا خلط إشارات الفائز.",
        "اختيار الفائز عند 0.13% و0.075% لم يُقَس. لا يُضاف بعد الرؤية.",
        "المقاعد الفارغة لا تُملأ بعد الرؤية.",
    ]) + "\n"
    (OUT / "grid_precommitted.txt").write_text(text, encoding="utf-8")


def write_outputs(canary: dict, lab: str, winner, axis, pairs, multis, judged, break_note: str) -> None:
    pd.DataFrame([slim(r) for r in MEASURED]).to_csv(OUT / "measurements.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(LEDGER).to_csv(OUT / "attempt_ledger.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([slim(r) for r in axis]).to_csv(OUT / "volume_axis.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([slim(r) for r in pairs + multis]).to_csv(OUT / "combos.csv", index=False, encoding="utf-8-sig")
    meas = pd.DataFrame(MEASURED)
    rnd = meas[meas["seed"].notna()] if len(meas) else meas.iloc[0:0]
    rows = []
    if len(rnd):
        for (cost, window), g in rnd.groupby(["cost", "الفترة"]):
            rows.append({
                "cost": cost, "الفترة": window,
                "mean": round(float(g["net"].mean()), 2),
                "min": round(float(g["net"].min()), 2),
                "max": round(float(g["net"].max()), 2),
                "n": int(len(g)),
            })
    pd.DataFrame(rows).to_csv(OUT / "random_summary.csv", index=False, encoding="utf-8-sig")
    if not (OUT / "filter_choice_l0054.json").exists():
        raise SystemExit("filter_choice_l0054.json مفقود")
    env = {
        "python": platform.python_version(), "pandas": pd.__version__,
        "numpy": np.__version__, "platform": platform.platform(),
        "cost_default_file": DEFAULT_COST, "stop": STOP, "trail": TRAIL,
        "seeds": list(SEEDS), "cap": CAP, "counted": len(LEDGER),
        "map": "copied from L0051/routing_map.json", "map_regenerated": False,
        "canary": canary.get("canary"),
        "canary_net": canary.get("got", {}).get("net"),
        "canary_lab": lab, "regime_py_used": False, "alternative_loader": False,
        "volume_def": "signal bar volume > k * mean(volume.shift(1), 20)",
        "move_target": MOVE_TARGET, "threshold_note": break_note, "rule": RULE,
    }
    (OUT / "env_dump.txt").write_text(json.dumps(env, ensure_ascii=False, indent=2), encoding="utf-8")
    facts = {
        "counted": len(LEDGER), "cap": CAP, "threshold_note": break_note,
        "axis": [slim(r) for r in axis],
        "pairs": [slim(r) for r in pairs],
        "multis": [slim(r) for r in multis],
        "winner": None if winner is None else slim(winner),
        "judged": [slim(r) for r in judged],
        "random": rows, "rule": RULE,
    }
    dump_json(OUT / "facts.json", facts)
    blobs = []
    for name in (
        "measurements.csv", "random_summary.csv", "attempt_ledger.csv",
        "routing_map.json", "filter_choice_l0054.json", "volume_axis.csv",
        "combos.csv", "facts.json",
    ):
        data = (OUT / name).read_bytes()
        blobs.append(f"{name} {hashlib.sha256(data).hexdigest()}")
    (OUT / "sha256.txt").write_text("\n".join(blobs) + "\n", encoding="utf-8")
    print("\n".join(blobs))
    restore_cost()
    if abs(C.COST_PER_SIDE - DEFAULT_COST) > 1e-15:
        raise SystemExit("لم تُعَد الكلفة")


def main() -> int:
    t0 = time.time()
    print("═" * 74)
    print(" L0054 — تعميق الحجم. خريطة مجمَّدة. السقف 40.")
    print("═" * 74)
    write_precommit()
    canary = run_canary()
    run_selftests()
    lab = lab_canary_status()
    prepare()
    build_regimes()

    print("\n══ مرحلة 0: أربعة مراجع (لا تُحسب) ══")
    store = {}
    set_cost(COST_REF)
    try:
        for lbl, s0, s1, key in (
            ("SEL", DEC_S, DEC_E, "base"),
            ("JUD", JUD_S, JUD_E, "base"),
        ):
            rows, _ = simulate_mask((), s0, s1, "base")
            save_trades(f"p0_base_{cost_tag(COST_REF)}_{lbl}", rows)
            st = summarize(rows, COST_REF)
            gate(f"بلا مرشّح {lbl}", st, P0[(key, lbl)])
            store[("base", lbl)] = rows
        k18 = {"id": "vol_k1.8", "label": "حجم k=1.8", "parts": (("vol", 1.8),)}
        for lbl, s0, s1 in (("SEL", DEC_S, DEC_E), ("JUD", JUD_S, JUD_E)):
            rows, _ = simulate_mask(tuple(k18["parts"]), s0, s1, "k18")
            save_trades(f"p0_vol_k1.8_{cost_tag(COST_REF)}_{lbl}", rows)
            st = summarize(rows, COST_REF)
            gate(f"k=1.8 {lbl}", st, P0[("k18", lbl)])
            store[("k18", lbl)] = rows
    finally:
        restore_cost()
    print("  ✅ الأربعة طابقت")

    print("\n══ تكافؤ قبل أي تهدئة ══")
    assert_equivalent(DEC_S, DEC_E, COST_REF, (), "أساس اختيار")
    assert_equivalent(DEC_S, DEC_E, COST_REF, (("vol", 1.8),), "k=1.8 اختيار")

    print("\n══ مرحلة 1: تعميق k على الاختيار ══")
    base_sel = summarize(store[("base", "SEL")], COST_REF)["trades"]
    axis = []
    axis_rows = {}
    # k=1.8 من المرحلة 0، يُدرج في المحور ولا يُعاد.
    rec18 = record("حجم k=1.8", "اختيار", store[("k18", "SEL")], COST_REF, None, False, {
        "id": "vol_k1.8", "label": "حجم k=1.8", "parts": [("vol", 1.8)], "order": 0, "k": 1.8,
    })
    rec18["reject"] = reject_rate(rec18["trades"], base_sel)
    rec18["order"] = 0
    rec18["k"] = 1.8
    axis.append(rec18)
    axis_rows["vol_k1.8"] = store[("k18", "SEL")]
    for spec in K_AXIS:
        if not spec["counted"]:
            continue
        full = {
            "id": spec["id"], "label": spec["label"],
            "parts": (("vol", spec["k"]),), "k": spec["k"],
        }
        rec, rows = run_spec(
            full, DEC_S, DEC_E, "اختيار", COST_REF, True, base_sel, spec["order"],
            f"{spec['id']}_{cost_tag(COST_REF)}_SEL",
        )
        rec["k"] = spec["k"]
        axis.append(rec)
        axis_rows[spec["id"]] = rows
    below = [r for r in axis if r["trades"] < MIN_SEL]
    if below:
        first = min(below, key=lambda r: r["k"])
        break_note = f"عتبة 300 تُكسر عند k={first['k']} ({first['trades']} صفقة)."
    else:
        break_note = "عتبة 300 لم تُكسر داخل المحور المقيس (حتى 3.5)."
    print(" ", break_note)

    best = pick_best_k(axis)
    print("\n══ أفضل k ══")
    if best is None:
        print("  لا k مؤهّل. لا تركيب ولا حكم.")
        dump_json(OUT / "filter_choice_l0054.json", {
            "rule": RULE, "written_before_judgement": True, "winner_id": None,
        })
        write_outputs(canary, lab, None, axis, [], [], [], break_note)
        guards()
        return 0
    print(f"  {best['label']}: حركة={best['move']:.5f} صفقات={best['trades']} صافٍ={best['net']}")
    best_k = float(best["k"])
    best_parts = (("vol", best_k),)

    print("\n══ مرحلة 2: الحجم + عائلات مختلفة ══")
    pairs = []
    pair_rows = {}
    pair_specs = []
    for addon in ADDONS:
        spec = {
            "id": f"k{best_k}+{addon['id']}",
            "label": f"حجم k={best_k} + {addon['label']}",
            "parts": best_parts + tuple(addon["parts"]),
            "members": [addon["id"]],
        }
        rec, rows = run_spec(
            spec, DEC_S, DEC_E, "اختيار", COST_REF, True, base_sel, 10 + addon["order"],
            f"{spec['id']}_{cost_tag(COST_REF)}_SEL",
        )
        rec["members"] = spec["members"]
        pairs.append(rec)
        pair_rows[spec["id"]] = rows
        pair_specs.append(spec)
    ranked = rank_addons(pairs)
    print("  ترتيب التركيبات المؤهّلة:")
    for r in ranked:
        print(f"    {r['label']}: حركة={r['move']:.5f} صفقات={r['trades']}")

    multis = []
    multi_rows = {}
    multi_specs = []
    by_id = {s["id"]: s for s in pair_specs}
    groups = []
    if len(ranked) >= 2:
        groups.append([ranked[0], ranked[1]])
    if len(ranked) >= 3:
        groups.append([ranked[0], ranked[1], ranked[2]])
    for gi, group in enumerate(groups):
        parts = list(best_parts)
        members = []
        labels = [f"حجم k={best_k}"]
        for r in group:
            parts.extend(by_id[r["id"]]["parts"][1:])  # دون تكرار الحجم
            members.append(r["members"][0])
            labels.append(r["label"].split(" + ", 1)[1])
        spec = {
            "id": f"k{best_k}+" + "+".join(members),
            "label": " + ".join(labels),
            "parts": tuple(parts),
            "members": members,
        }
        rec, rows = run_spec(
            spec, DEC_S, DEC_E, "اختيار", COST_REF, True, base_sel, 20 + gi,
            f"{spec['id']}_{cost_tag(COST_REF)}_SEL",
        )
        rec["members"] = members
        multis.append(rec)
        multi_rows[spec["id"]] = rows
        multi_specs.append(spec)

    cands = [best] + pairs + multis
    winner = pick_winner(cands)
    choice = {
        "rule": RULE,
        "written_before_judgement": True,
        "best_k": best_k,
        "best_k_id": best["id"],
        "ranked_pair_ids": [r["id"] for r in ranked],
        "winner_id": None if winner is None else winner["id"],
        "winner_parts": None if winner is None else norm_parts(winner["parts"]),
        "winner_label": None if winner is None else winner.get("label"),
        "selection_net": None if winner is None else winner["net"],
        "selection_trades": None if winner is None else winner["trades"],
        "selection_move": None if winner is None else winner["move"],
    }
    choice_path = OUT / "filter_choice_l0054.json"
    dump_json(choice_path, choice)
    frozen = json.loads(choice_path.read_text(encoding="utf-8"))
    print(f"\n══ الفائز المجمَّد قبل الحكم: {frozen['winner_id']} ══")

    judged = []
    books = []
    if frozen["winner_id"] is None:
        print("  لا فائز. الحكم لم يُقَس.")
    else:
        spec = None
        pool = [{"id": best["id"], "label": best["label"], "parts": tuple(best["parts"])}]
        pool.extend(pair_specs)
        pool.extend(multi_specs)
        for s in pool:
            if s["id"] == frozen["winner_id"]:
                spec = s
                break
        if spec is None or norm_parts(spec["parts"]) != norm_parts(frozen["winner_parts"]):
            raise SystemExit("الفائز المجمَّد لا يطابق المواصفات")
        sel_rows = axis_rows.get(spec["id"]) or pair_rows.get(spec["id"]) or multi_rows.get(spec["id"])
        if sel_rows is None:
            raise SystemExit("صفوف اختيار الفائز غير موجودة")
        print("\n══ مرحلة 3: الحكم ══")
        base_jud = summarize(store[("base", "JUD")], COST_REF)["trades"]
        for cost, order in ((0.0010, 200), (0.0013, 201), (0.00075, 202)):
            rec, rows = run_spec(
                spec, JUD_S, JUD_E, "حكم", cost, True, base_jud, order,
                f"{spec['id']}_{cost_tag(cost)}_JUD",
            )
            judged.append(rec)
            books.append((spec["label"], cost, "حكم", rows))
            if cost == 0.0010:
                jud_rows = rows
        judged.extend(seeds_for(jud_rows, JUD_S, JUD_E, "حكم", COST_REF, "JUD"))
        judged.extend(seeds_for(sel_rows, DEC_S, DEC_E, "اختيار", COST_REF, "SEL"))
        books.append((spec["label"], COST_REF, "اختيار", sel_rows))
    if books:
        decompositions(books)
    else:
        print("  تفكيك الحكم: لم يُقَس")

    n_combo = len(pairs) + len(multis)
    n_p3 = 13 if frozen["winner_id"] else 0
    expected = 5 + n_combo + n_p3
    if len(LEDGER) != expected:
        raise SystemExit(f"العدّ {len(LEDGER)} ≠ القاعدة {expected}")
    write_outputs(canary, lab, winner, axis, pairs, multis, judged, break_note)
    guards()
    print(f"انتهى في {time.time() - t0:.0f}s  العدّ={len(LEDGER)}/{CAP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
