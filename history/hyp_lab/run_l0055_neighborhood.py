# -*- coding: utf-8 -*-
"""L0055 — فحص جوار الفائز. فحص لا تحسين.

المتغيّر في المرحلة 1: قيمة k وحدها. التهدئة تبقى 3. الخريطة تُنسخ.
تعريف الحجم والتهدئة منسوخان من L0054 حرفيًا.

القواعد مكتوبة هنا قبل أي رقم.

السقف 32.
  مرحلة 0 (لا تُحسب): خمسة مراجع.
  مرحلة 1 (9 من سقف 14): الفائز كاملًا (k + تهدئة 3) على الاختيار عند 0.10%.
      k = 3.1 3.2 3.3 3.4 3.6 3.8 4.0 4.5 5.0.
      3.5 من المرحلة 0 ولا يُعاد. خمسة مقاعد لا تُملأ بعد الرؤية. لا k جديد.
  مرحلة 2 (حتى 9 من سقف 10): حكم 0.10% لكل جار صافيه موجب وصفقاته ≥ 300.
      3.5 حكمه من المرحلة 0 ولا يُعاد. لا انتقاء بعد الرؤية.
      إن زاد المؤهّلون على 10: الأقرب إلى 3.5 بالترتيب المقفول أدناه.
  مرحلة 3: التصنيف يُكتب قبل أي قياس إضافي.
      ≥ 70% من الجيران التسعة موجب في الفترتين ⇒ هضبة.
      40% حتى ما دون 70% ⇒ منطقة مضطربة. لا يُعتمد. لا جوار 1.8.
      دون 40% ⇒ قمة حظّ. يُدفن 3.5. ثم جوار 1.8 على الاختيار (4) وعشوائي اختياره (5).
      عشوائي 3.5 مقيس في L0054. لا يُعاد.
      سقف المرحلة 3 هو 8. إن سقط 3.5 فالبذور الأربع + الخمس = 9. البذور لا تُقطع.
      المجموع يبقى دون 32.

بذور جديدة، إن لزم: 110055 210055 310055 410055 510055.
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

ROOT = pathlib.Path("/home/user/l0055")
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

OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0055"
OUT.mkdir(parents=True, exist_ok=True)
DAILY = pathlib.Path.home() / ".cache" / "l0055_daily"
DAILY.mkdir(parents=True, exist_ok=True)
MAP_SRC = ROOT / "history" / "research" / "hyp_lab_out" / "L0051" / "routing_map.json"
L54 = ROOT / "history" / "research" / "hyp_lab_out" / "L0054"
L53 = ROOT / "history" / "research" / "hyp_lab_out" / "L0053"

DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
WARM = "2021-06-01"
SEEDS = (110055, 210055, 310055, 410055, 510055)
CAP = 32
DEFAULT_COST = 0.0013
COST_REF = 0.0010
STOP = 2.5
TRAIL = 4.0
BAR = 4 * 3600
MIN_SEL = 300
MIN_JUD = 400
BASE_TRADES = 1041  # مسنَدة بلا مرشّح، مُتحقَّق منها في ملفات L0054. المقام لنسبة الرفض.

# الجيران. 3.5 المركز وليس جارًا. الترتيب هو ترتيب الاقتراب إن امتلأ السقف.
NEIGHBORS = (3.1, 3.2, 3.3, 3.4, 3.6, 3.8, 4.0, 4.5, 5.0)
CLOSE_ORDER = (3.4, 3.6, 3.3, 3.8, 3.2, 4.0, 3.1, 4.5, 5.0)
FALLBACK_K = (1.6, 1.7, 1.9, 2.0)

P0 = {
    "win_sel": {"net": 48.98, "n": 302, "move": 0.20233},
    "win_jud": {"net": 22.72, "n": 434, "move": 0.09240},
    "win_013": {"net": 18.51, "n": 434, "move": None},
    "k35": {"net": 38.59, "n": 314, "move": 0.16301},
    "k30": {"net": -17.16, "n": 441, "move": None},
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

LEDGER: list[dict] = []
MEASURED: list[dict] = []
REG4H: dict[str, pd.Series] = {}
SYMS: list[str] = []
ENABLED: set[tuple[str, str]] = set()

RULE = (
    "جار = كل k في المرحلة 1 عدا 3.5. المقام = 9. "
    "موجب في الفترتين = صافٍ مُقرَّب > 0 في الاختيار والحكم، "
    "وصفقات الاختيار ≥ 300، وصفقات الحكم ≥ 400. "
    "من لا يُقاس حكمه لأنه رُفض في الاختيار ليس موجبًا في الفترتين. "
    "≥ 70% هضبة. من 40% حتى دون 70% مضطربة. دون 40% قمة حظّ. "
    "النسبة بلا تقريب إلى العتبة: 6/9 = 66.7% مضطربة، و7/9 = 77.8% هضبة. "
    "لا يُختار k جديد من الحكم. لا يُعتمد جار بدل 3.5."
)


def cost_tag(cost: float) -> str:
    return f"c{int(round(cost * 100000)):05d}"


def k_tag(k: float) -> str:
    return f"k{int(round(k * 10)):03d}"


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


def save_trades(name: str, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_csv(OUT / f"trades_{name}.csv", index=False, encoding="utf-8-sig")


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
        raise SystemExit(f"تداخل ≠ 0 في {name}")
    rec = {"القياس": name, "الفترة": window, "counted": counted, "cost": cost, "seed": seed, **st}
    if extra:
        rec.update(extra)
    if counted:
        log_measurement(name, window, {"cost": cost, "seed": "" if seed is None else seed})
        MEASURED.append(rec)
    tag = f"{len(LEDGER)}/{CAP}" if counted else "لا يُحسب"
    print(
        f"  [{tag}] {name} {window}: net={st['net']} صفقات={st['trades']} "
        f"حركة={fmt_move(st)} إجمالي={st['gross']}",
        flush=True,
    )
    return rec


def gate(label: str, st: dict, spec: dict) -> None:
    ok_net = abs(st["net"] - spec["net"]) <= 0.5
    ok_n = st["trades"] == spec["n"]
    ok_m = True if spec["move"] is None else (
        st["move"] is not None and abs(st["move"] - spec["move"]) <= 1.5e-5
    )
    print(f"  تحقق {label}: {st['net']}$ / {st['trades']} حركة={fmt_move(st)} مرجع {spec}", flush=True)
    if not (ok_net and ok_n and ok_m) or st["overlapping_trades"]:
        raise SystemExit(f"الواقع خالف الورقة: {label} = {st}. أوقف. لا جوار.")


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


def load_frozen_map() -> set[tuple[str, str]]:
    mp = json.loads(MAP_SRC.read_text(encoding="utf-8"))
    enabled = {tuple(x) for x in mp["enabled"]}
    if enabled != FROZEN_ENABLED or len(enabled) != 11:
        raise SystemExit("الخريطة ليست المجمَّدة")
    shutil.copyfile(MAP_SRC, OUT / "routing_map.json")
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
    if set(SYMS) != L0048_COINS:
        raise SystemExit(f"سلة تختلف: {sorted(set(SYMS) ^ L0048_COINS)}")
    ENABLED = load_frozen_map()
    print(f"  خلايا={len(cells)} عملات={len(SYMS)} خريطة={len(ENABLED)}")
    R46.build_cache(SYMS)


def build_regimes() -> None:
    print("\n══ مصنّف يومي shift(1) ══")
    for sym in SYMS:
        path = DAILY / f"{sym}_1d.parquet"
        if not path.exists():
            d1 = C.load(str(ROOT / "crypto_archive" / f"{sym}_1m.parquet"), start=WARM, end=JUD_E)
            C.to_bars(d1, 1440).to_parquet(path)
            del d1
            print(f"  يومي {sym}", flush=True)
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
        REG4H[sym] = pd.Series([lookup.get(ts.normalize(), np.nan) for ts in f.index], index=f.index, dtype=object)


def entry_regime(sym: str, index: pd.DatetimeIndex) -> pd.Series:
    return REG4H[sym].reindex(index).shift(-1)


def routed_signal(df, sym) -> pd.Series:
    sig = pd.Series(False, index=df.index)
    er = entry_regime(sym, df.index)
    for col, regime in ENABLED:
        sg = R48.column_signal(df, sym, col).reindex(df.index, fill_value=False).fillna(False).astype(bool)
        sig = sig | (sg & (er == regime))
    return sig


def apply_static(df: pd.DataFrame, sig: pd.Series, parts: tuple) -> pd.Series:
    out = sig.fillna(False).astype(bool).copy()
    vol = df["volume"]
    vol_ma = vol.shift(1).rolling(20, min_periods=20).mean()
    for part in parts:
        if part[0] == "vol":
            out = out & vol_ma.notna() & (vol > float(part[1]) * vol_ma)
        elif part[0] == "cool":
            continue
        else:
            raise SystemExit(f"جزء غير مسموح في هذه الجولة: {part}")
    return out.fillna(False)


def machine_signal(df, sym, parts: tuple) -> pd.Series:
    return apply_static(df, routed_signal(df, sym), parts)


def cool_n(parts: tuple) -> int | None:
    ns = [int(p[1]) for p in parts if p[0] == "cool"]
    return max(ns) if ns else None


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
            sg = machine_signal(df, sym, parts).reindex(win.index, fill_value=False).fillna(False).astype(bool)
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


def assert_equivalent(parts: tuple, label: str) -> None:
    set_cost(COST_REF)
    try:
        direct, _ = simulate_mask(parts, DEC_S, DEC_E, "eq")
        cached = []
        for sym in SYMS:
            df = R46.frames(sym)
            win = R48.window(df, DEC_S, DEC_E)
            if len(win) < 100:
                continue
            table = R48.outcomes_for(sym, DEC_S, DEC_E)
            sg = machine_signal(df, sym, parts).reindex(win.index, fill_value=False).fillna(False).astype(bool).to_numpy()
            cached.extend(R48.rows_from_chosen(sym, "eq", R48.greedy(table, sg)))
        ds, cs = summarize(direct, COST_REF), summarize(cached, COST_REF)
        if abs(ds["net"] - cs["net"]) > 0.01 or ds["trades"] != cs["trades"]:
            raise SystemExit(f"تكافؤ فشل {label}")
        print(f"  ✅ تكافؤ {label}: {ds['net']}$ / {ds['trades']}")
    finally:
        restore_cost()


def run_parts(parts: tuple, s0: str, s1: str, wname: str, cost: float, counted: bool,
              name: str, fname: str, extra: dict) -> tuple[dict, list[dict]]:
    set_cost(cost)
    try:
        rows, meta = simulate_mask(parts, s0, s1, name)
        save_trades(fname, rows)
        rec = record(name, wname, rows, cost, None, counted, {**extra, **meta})
        rec["reject"] = None if not BASE_TRADES else round(1.0 - rec["trades"] / BASE_TRADES, 4)
        flag = "تحت العتبة" if (wname == "اختيار" and rec["trades"] < MIN_SEL) else ""
        if flag:
            rec["عتبة"] = flag
            print(f"      {flag} رفض={rec['reject']}")
        else:
            print(f"      رفض={rec['reject']}")
        return rec, rows
    finally:
        restore_cost()


def winner_parts(k: float) -> tuple:
    return (("vol", float(k)), ("cool", 3))


def alone_parts(k: float) -> tuple:
    return (("vol", float(k)),)


def qualifies(rec: dict) -> bool:
    return rec["net"] > 0 and rec["trades"] >= MIN_SEL and rec["move"] is not None


def both_periods(sel: dict, jud: dict | None) -> bool:
    if jud is None:
        return False
    return (
        sel["net"] > 0 and sel["trades"] >= MIN_SEL
        and jud["net"] > 0 and jud["trades"] >= MIN_JUD
    )


def classify(n_ok: int, n_den: int) -> str:
    if n_den <= 0:
        raise SystemExit("لا مقام للتصنيف")
    ratio = n_ok / n_den
    if ratio >= 0.70:
        return "هضبة"
    if ratio >= 0.40:
        return "منطقة مضطربة"
    return "قمة حظّ"


def seeds_for(rows_direct: list[dict], s0: str, s1: str, wname: str, tag: str) -> list[dict]:
    set_cost(COST_REF)
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
            save_trades(f"rnd_{tag}_{cost_tag(COST_REF)}_s{seed}", rows)
            out.append(record(f"عشوائي 1.8 بذرة {seed}", wname, rows, COST_REF, seed, True))
    finally:
        restore_cost()
    return out


def verify_deposited_files() -> None:
    ax = pd.read_csv(L54 / "volume_axis.csv")
    by_k = {float(r.k): r for _, r in ax.iterrows()}
    checks = {
        1.8: (106.03, 884, 0.16006),
        2.0: (59.23, 803, 0.11383),
        2.2: (-8.88, 727, 0.02777),
        2.5: (4.57, 603, 0.04758),
        3.0: (-17.16, 441, 0.00105),
        3.5: (38.59, 314, 0.16301),
    }
    for k, (net, n, move) in checks.items():
        r = by_k[k]
        if abs(float(r.net) - net) > 0.5 or int(r.trades) != n or abs(float(r.move) - move) > 1.5e-5:
            raise SystemExit(f"ملف L0054 خالف الورقة عند k={k}: {r.net}/{r.trades}/{r.move}")
    comb = pd.read_csv(L54 / "combos.csv")
    hit = comb[comb["label"] == "حجم k=3.5 + تهدئة n=3"].iloc[0]
    if abs(float(hit.net) - 48.98) > 0.5 or int(hit.trades) != 302 or abs(float(hit.move) - 0.20233) > 1.5e-5:
        raise SystemExit("ملف تركيب L0054 خالف الورقة")
    print("  ✅ ملفات L0054 تطابق جدول الورقة")


def guards() -> None:
    print("\n══ حرّاس ══")
    bad = []
    frames = pathlib.Path.home() / ".cache" / "l0046_frames"
    for f in sorted(OUT.glob("trades_*.csv")):
        cost = 0.0013 if "c00130" in f.name else 0.0010
        st = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "fill_invariant_check.py"),
             "--trades", str(f), "--frames", str(frames), "--cost", str(cost), "--bar-tag", "4h"],
            capture_output=True, text=True,
        )
        if st.returncode != 0 or "تُخطّي=0" not in st.stdout or "شموع ناقصة=0" not in st.stdout:
            bad.append(f.name)
            print(" FAIL", f.name, (st.stdout or "")[-200:])
        au = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "position_sequencing_audit.py"),
             "--trades", str(f), "--require-zero"],
            capture_output=True, text=True,
        )
        if au.returncode != 0:
            bad.append(f.name + " seq")
    if bad:
        raise SystemExit("حارس فشل: " + ", ".join(bad))
    print(f"  ✅ {len(list(OUT.glob('trades_*.csv')))} ملفًا")


def dump_json(path: pathlib.Path, obj) -> None:
    def conv(o):
        if isinstance(o, tuple):
            return list(o)
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        raise TypeError(type(o))
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=conv), encoding="utf-8")


def slim(rec: dict) -> dict:
    keep = (
        "القياس", "الفترة", "cost", "seed", "net", "trades", "per", "gross", "move",
        "cost_per", "costs", "median_hold", "k", "reject", "عتبة", "sig_in", "sig_out",
        "cool_blocked", "both",
    )
    out = {}
    for key in keep:
        if key in rec and rec[key] is not None:
            v = rec[key]
            if isinstance(v, float) and key in ("move", "cost_per"):
                v = round(v, 8)
            out[key] = v
    return out


def write_outputs(canary: dict, lab: str, sel_rows: list, jud_rows: list, cls: dict, fallback: list) -> None:
    pd.DataFrame([slim(r) for r in MEASURED]).to_csv(OUT / "measurements.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(LEDGER).to_csv(OUT / "attempt_ledger.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([slim(r) for r in sel_rows]).to_csv(OUT / "neighborhood_selection.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([slim(r) for r in jud_rows]).to_csv(OUT / "neighborhood_judgement.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([slim(r) for r in fallback]).to_csv(OUT / "k18_neighborhood.csv", index=False, encoding="utf-8-sig")
    meas = pd.DataFrame(MEASURED)
    rnd = meas[meas["seed"].notna()] if len(meas) else meas.iloc[0:0]
    rows = []
    if len(rnd):
        for window, g in rnd.groupby("الفترة"):
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
        "cap": CAP, "counted": len(LEDGER), "seeds_if_needed": list(SEEDS),
        "canary": canary.get("canary"), "canary_net": canary.get("got", {}).get("net"),
        "canary_lab": lab, "regime_py_used": False, "alternative_loader": False,
        "volume_def": "signal volume > k * mean(volume.shift(1), 20)",
        "cool_def": "after rounded pnl < 0, block signals exit_j <= i <= exit_j+2",
        "rule": RULE, "classification": cls.get("label"), "ratio": cls.get("ratio"),
    }
    (OUT / "env_dump.txt").write_text(json.dumps(env, ensure_ascii=False, indent=2), encoding="utf-8")
    dump_json(OUT / "facts.json", {
        "counted": len(LEDGER), "classification": cls,
        "selection": [slim(r) for r in sel_rows],
        "judgement": [slim(r) for r in jud_rows],
        "fallback": [slim(r) for r in fallback],
        "random_new": rows,
    })
    blobs = []
    for name in (
        "measurements.csv", "attempt_ledger.csv", "neighborhood_selection.csv",
        "neighborhood_judgement.csv", "classification.json", "facts.json", "routing_map.json",
    ):
        blobs.append(f"{name} {hashlib.sha256((OUT / name).read_bytes()).hexdigest()}")
    (OUT / "sha256.txt").write_text("\n".join(blobs) + "\n", encoding="utf-8")
    print("\n".join(blobs))
    restore_cost()


def write_precommit() -> None:
    (OUT / "grid_precommitted.txt").write_text(
        "\n".join([
            "مكتوب قبل أي رقم.",
            RULE,
            "تعريف الحجم = L0054: حجم شمعة الإشارة > k × متوسط 20 سابقة shift(1).",
            "التهدئة = 3، لا تتغيّر. بعد pnl مُقرَّب < 0 تُمنع إشارات i حيث exit_j <= i <= exit_j+2.",
            "المرحلة 1: 3.1 3.2 3.3 3.4 3.6 3.8 4.0 4.5 5.0. لا غيرها.",
            "ترتيب الامتلاء إن لزم: 3.4 3.6 3.3 3.8 3.2 4.0 3.1 4.5 5.0.",
            "تحت 300 تُوسَم ولا تُحذف من جدول الاختيار، ولا تُقاس في الحكم.",
            "عشوائي 3.5 من L0054 لا يُعاد. بذور جديدة 110055..510055 لعشوائي 1.8 فقط إن سقط 3.5.",
            "جوار 1.8 إن سقط 3.5 فقط: حجم بلا تهدئة، k=1.6 1.7 1.9 2.0، اختيار، 0.10%.",
            "هضبة 1.8 = ≥ 70% من هؤلاء الأربعة موجب في الاختيار (≥300). حكمهم لم يُقَس.",
            "لا بحث عن k أفضل. لا تغيير للفائز إلا بجدول التصنيف.",
        ]) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    t0 = time.time()
    print("═" * 74)
    print(" L0055 — فحص جوار. لا تحسين. السقف 32.")
    print("═" * 74)
    write_precommit()
    verify_deposited_files()
    canary = run_canary()
    run_selftests()
    lab = lab_canary_status()
    prepare()
    build_regimes()

    print("\n══ مرحلة 0 ══")
    set_cost(COST_REF)
    try:
        win_sel, _ = run_parts(winner_parts(3.5), DEC_S, DEC_E, "اختيار", COST_REF, False,
                               "فائز 3.5+تهدئة", f"p0_win_{k_tag(3.5)}_{cost_tag(COST_REF)}_SEL", {"k": 3.5})
        gate("فائز اختيار", win_sel, P0["win_sel"])
        win_jud, _ = run_parts(winner_parts(3.5), JUD_S, JUD_E, "حكم", COST_REF, False,
                               "فائز 3.5+تهدئة", f"p0_win_{k_tag(3.5)}_{cost_tag(COST_REF)}_JUD", {"k": 3.5})
        gate("فائز حكم 0.10%", win_jud, P0["win_jud"])
        rec, _ = run_parts(winner_parts(3.5), JUD_S, JUD_E, "حكم", 0.0013, False,
                           "فائز 3.5+تهدئة", f"p0_win_{k_tag(3.5)}_{cost_tag(0.0013)}_JUD", {"k": 3.5})
        gate("فائز حكم 0.13%", rec, P0["win_013"])
        rec, _ = run_parts(alone_parts(3.5), DEC_S, DEC_E, "اختيار", COST_REF, False,
                           "k=3.5 وحده", f"p0_alone_{k_tag(3.5)}_{cost_tag(COST_REF)}_SEL", {"k": 3.5})
        gate("k=3.5 وحده", rec, P0["k35"])
        rec, _ = run_parts(alone_parts(3.0), DEC_S, DEC_E, "اختيار", COST_REF, False,
                           "k=3.0 وحده", f"p0_alone_{k_tag(3.0)}_{cost_tag(COST_REF)}_SEL", {"k": 3.0})
        gate("k=3.0 وحده", rec, P0["k30"])
    finally:
        restore_cost()
    print("  ✅ الخمسة طابقت")
    assert_equivalent(alone_parts(3.5), "k=3.5 بلا تهدئة")

    print("\n══ مرحلة 1: جوار الاختيار ══")
    sel = {3.5: win_sel}
    sel_list = [win_sel]
    for k in NEIGHBORS:
        rec, _ = run_parts(
            winner_parts(k), DEC_S, DEC_E, "اختيار", COST_REF, True,
            f"k={k} + تهدئة", f"nb_{k_tag(k)}_{cost_tag(COST_REF)}_SEL", {"k": k},
        )
        sel[k] = rec
        sel_list.append(rec)
    if len(LEDGER) != 9:
        raise SystemExit(f"مرحلة 1 عدّها {len(LEDGER)} ≠ 9")

    qual = [k for k in NEIGHBORS if qualifies(sel[k])]
    qual_sorted = sorted(qual, key=lambda k: CLOSE_ORDER.index(k))
    if len(qual_sorted) > 10:
        skipped = qual_sorted[10:]
        qual_sorted = qual_sorted[:10]
        print("  لم يُقَس لامتلاء السقف:", skipped)
    else:
        skipped = []
    print("  مؤهّلو الحكم:", qual_sorted)

    print("\n══ مرحلة 2: حكم المؤهّلين ══")
    jud = {3.5: win_jud}
    jud_list = [win_jud]
    for k in qual_sorted:
        rec, _ = run_parts(
            winner_parts(k), JUD_S, JUD_E, "حكم", COST_REF, True,
            f"k={k} + تهدئة", f"nb_{k_tag(k)}_{cost_tag(COST_REF)}_JUD", {"k": k},
        )
        jud[k] = rec
        jud_list.append(rec)

    n_ok = sum(1 for k in NEIGHBORS if both_periods(sel[k], jud.get(k)))
    label = classify(n_ok, len(NEIGHBORS))
    cls = {
        "label": label,
        "n_ok": n_ok,
        "n_den": len(NEIGHBORS),
        "ratio": n_ok / len(NEIGHBORS),
        "qualifying": qual_sorted,
        "skipped_for_cap": skipped,
        "rule": RULE,
        "written_before_extra": True,
    }
    dump_json(OUT / "classification.json", cls)
    frozen = json.loads((OUT / "classification.json").read_text(encoding="utf-8"))
    if frozen["label"] != label or frozen["n_ok"] != n_ok:
        raise SystemExit("التصنيف المكتوب لا يطابق الحساب")
    print(f"\n══ التصنيف المجمَّد: {label} ({n_ok}/{len(NEIGHBORS)} = {n_ok/len(NEIGHBORS):.1%}) ══")

    fallback = []
    if frozen["label"] == "قمة حظّ":
        print("\n══ سقوط 3.5: جوار k=1.8 على الاختيار، حجم بلا تهدئة ══")
        rec, rows18 = run_parts(
            alone_parts(1.8), DEC_S, DEC_E, "اختيار", COST_REF, False,
            "k=1.8 مرجع", f"ref_k18_{cost_tag(COST_REF)}_SEL", {"k": 1.8},
        )
        gate("k=1.8 مرجع", rec, {"net": 106.03, "n": 884, "move": 0.16006})
        for k in FALLBACK_K:
            rec, _ = run_parts(
                alone_parts(k), DEC_S, DEC_E, "اختيار", COST_REF, True,
                f"k={k} وحده", f"k18_{k_tag(k)}_{cost_tag(COST_REF)}_SEL", {"k": k},
            )
            fallback.append(rec)
            if k == 2.0 and (abs(rec["net"] - 59.23) > 0.5 or rec["trades"] != 803):
                raise SystemExit(f"k=2.0 خالف L0054: {rec['net']}/{rec['trades']}")
        print("  عشوائي اختيار k=1.8 — لم يُقَس في L0053")
        seeds_for(rows18, DEC_S, DEC_E, "اختيار", "k18_SEL")
        print("  عشوائي حكم k=1.8 مقيس في L0053. لا يُعاد.")
    else:
        print("  لا جوار لـ 1.8. القاعدة لا تفتحه إلا عند قمة حظّ.")
        rows18 = []

    expected = 9 + len(qual_sorted) + (9 if frozen["label"] == "قمة حظّ" else 0)
    if len(LEDGER) != expected:
        raise SystemExit(f"العدّ {len(LEDGER)} ≠ {expected}")
    if len(LEDGER) > CAP:
        raise SystemExit("تجاوز السقف")
    write_outputs(canary, lab, sel_list, jud_list, frozen, fallback)
    guards()
    print(f"انتهى في {time.time()-t0:.0f}s  العدّ={len(LEDGER)}/{CAP}  التصنيف={frozen['label']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
