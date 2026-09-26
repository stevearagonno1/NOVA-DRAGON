# -*- coding: utf-8 -*-
"""L0053 — مرشّحات جودة الدخول فوق المحفظة المسنَدة. قياس وحكم.

المتغيّر الوحيد: طبقة تمرير/رفض فوق الإشارة. الخريطة تُنسخ ولا تُولَّد.
لا لمس للآلة ولا للإشارات ولا للخروج. لا محمّل بديل.

القواعد مكتوبة هنا قبل أي رقم حكم. لا تُعدَّل بعد الرؤية.

السقف 45. المستهلك يحدده العدّ أدناه، لا النتيجة.
  مرحلة 0 (لا تُحسب): أربعة مراجع الورقة.
  تحقق المادة 1 (لا يُحسب): بلا إسناد 0.13% ×2 · مسنَدة 0.075% حكم
      · عشوائي L0052 عند 0.075% حكم (5 بذور معروفة) لمطابقة 156.53$.
      إن خالف الواقعُ الورقةَ: إيقاف. لا مرشّحات.
  مرحلة 1 (15 من سقف 24): كل مرشّح وحده على الاختيار عند 0.10%.
      المقاعد التسعة لا تُملأ بعد الرؤية. لا قيم k أو m أو v أو b أو n إضافية.
  مرحلة 2 (حتى 4 من سقف 12): أفضل 3 بحركة الصفقة بشرط ≥400 صفقة اختيار،
      ثم كل زوج، ثم الثلاثة. إن قلّ المؤهّلون قلّت التركيبات. لا رابع يُستدعى بعد الرؤية.
  مرحلة 3 (7 من سقف 9) إن وُجد فائز فقط:
      الفائز 0.10% حكم · الفائز 0.075% حكم · 5 بذور عند 0.10% حكم.
      أساس 0.10% حكم من المرحلة 0، لا يُعاد عدّه.
      لا بذور عند 0.075%. لا عشوائي على الاختيار.
  إن لم يَفُز أحد: لا حكم. لا يُستبدل الفائز بأعلى حركة سالبة.

بذور الحكم: 110053 210053 310053 410053 510053.
بذور التحقق (L0052، لا تُحسب): 110052 210052 310052 410052 510052.
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

ROOT = pathlib.Path("/home/user/repo")
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

OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0053"
OUT.mkdir(parents=True, exist_ok=True)
DAILY = pathlib.Path.home() / ".cache" / "l0053_daily"
DAILY.mkdir(parents=True, exist_ok=True)
MAP_SRC = ROOT / "history" / "research" / "hyp_lab_out" / "L0051" / "routing_map.json"

DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
WARM = "2021-06-01"
SEEDS = (110053, 210053, 310053, 410053, 510053)
VERIFY_SEEDS = (110052, 210052, 310052, 410052, 510052)
CAP = 45
DEFAULT_COST = 0.0013
COST_REF = 0.0010
STOP = 2.5
TRAIL = 4.0
BAR = 4 * 3600
REGIMES = ("صاعد", "عرضي", "هابط")
MIN_TRADES = 400
MOVE_TARGET = 0.042

# مراجع الورقة. ±0.5$ على الدولار، وعدد الصفقات حرفياً حيث ذُكر.
P0 = {
    ("routed", 0.0013, "SEL"): (22.81, 1045, None),
    ("routed", 0.0013, "JUD"): (-36.45, 1610, None),
    ("routed", 0.0010, "SEL"): (34.56, 1041, None),
    ("routed", 0.0010, "JUD"): (-14.36, 1605, 49.83),
}
# المادة 1 — أرقام الورقة خارج جدول المرحلة 0.
ART1 = {
    ("unrouted", 0.0013, "SEL"): (10.76, 1067, None),
    ("unrouted", 0.0013, "JUD"): (-154.84, 1791, None),
    ("routed", 0.00075, "JUD"): (-0.63, None, 47.49),
}
# عشوائي L0052 عند 0.075% حكم. الورقة: التفوق على الأسعد 156.53$.
ART1_RND = {"mean": -200.12, "min": -240.02, "max": -157.16, "gap": 156.53}

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

# 15 مرشّحًا. الترتيب كسر تعادل فقط. لا يُزاد عليه بعد الرؤية.
PHASE1 = [
    {"id": "vol_k1.2", "label": "حجم k=1.2", "parts": (("vol", 1.2),)},
    {"id": "vol_k1.5", "label": "حجم k=1.5", "parts": (("vol", 1.5),)},
    {"id": "vol_k1.8", "label": "حجم k=1.8", "parts": (("vol", 1.8),)},
    {"id": "confirm", "label": "شمعة التأكيد", "parts": (("confirm",),)},
    {"id": "zone_m0.3", "label": "منطقة m=0.3", "parts": (("zone", 0.3),)},
    {"id": "zone_m0.6", "label": "منطقة m=0.6", "parts": (("zone", 0.6),)},
    {"id": "zone_m1.0", "label": "منطقة m=1.0", "parts": (("zone", 1.0),)},
    {"id": "atr_v0.005", "label": "تقلب v=0.005", "parts": (("atr", 0.005),)},
    {"id": "atr_v0.010", "label": "تقلب v=0.010", "parts": (("atr", 0.010),)},
    {"id": "atr_v0.015", "label": "تقلب v=0.015", "parts": (("atr", 0.015),)},
    {"id": "body_b0.4", "label": "جسم b=0.4", "parts": (("body", 0.4),)},
    {"id": "body_b0.6", "label": "جسم b=0.6", "parts": (("body", 0.6),)},
    {"id": "cool_n3", "label": "تهدئة n=3", "parts": (("cool", 3),)},
    {"id": "cool_n6", "label": "تهدئة n=6", "parts": (("cool", 6),)},
    {"id": "cool_n12", "label": "تهدئة n=12", "parts": (("cool", 12),)},
]

LEDGER: list[dict] = []
MEASURED: list[dict] = []
REG4H: dict[str, pd.Series] = {}
SYMS: list[str] = []
ENABLED: set[tuple[str, str]] = set()
RULE = (
    "الفائز = أعلى حركة صفقة في الاختيار بين {الثلاثة الأولى ومركّباتها المقيسة}، "
    "بشرط صفقات ≥ 400 وصافٍ مُقرَّب > 0. "
    "كسر التعادل: صافٍ أعلى، ثم صفقات أكثر، ثم ترتيب القياس. "
    "لا فائز ⇒ لا حكم. لا استبدال بعد الرؤية."
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
    if st["move"] is None:
        return "—"
    return f"{st['move']:.5f}"


def record(name: str, window: str, rows: list[dict], cost: float, seed, counted: bool,
           extra: dict | None = None) -> dict:
    st = summarize(rows, cost)
    if st["overlapping_trades"] != 0:
        save_trades(name + "_OVERLAP", rows)
        raise SystemExit(f"تداخل ≠ 0 في {name} {window}: {st}")
    rec = {
        "القياس": name, "الفترة": window, "counted": counted, "cost": cost,
        "seed": seed, **st,
    }
    if extra:
        rec.update(extra)
    if counted:
        log_measurement(name, window, {"cost": cost, "seed": "" if seed is None else seed})
        MEASURED.append(rec)
    tag = f"{len(LEDGER)}/{CAP}" if counted else "لا يُحسب"
    print(
        f"  [{tag}] {name} {window}: net={st['net']} صفقات={st['trades']} "
        f"حركة={fmt_move(st)} إجمالي={st['gross']} كلفة={st['costs']} "
        f"وسيط={st['median_hold']}",
        flush=True,
    )
    return rec


def gate(kind: str, cost: float, lbl: str, st: dict, spec: tuple) -> None:
    exp_net, exp_n, exp_gross = spec
    ok_net = abs(st["net"] - exp_net) <= 0.5
    ok_n = True if exp_n is None else st["trades"] == exp_n
    ok_g = True if exp_gross is None else abs(st["gross"] - exp_gross) <= 0.5
    print(
        f"  تحقق {kind} {cost:.3%} {lbl}: {st['net']}$ / {st['trades']} "
        f"إجمالي={st['gross']} حركة={fmt_move(st)}  مرجع net={exp_net} n={exp_n} g={exp_gross}",
        flush=True,
    )
    if not (ok_net and ok_n and ok_g) or st["overlapping_trades"]:
        raise SystemExit(
            f"الواقع خالف الورقة: {kind} {cost} {lbl} = {st['net']}$ / {st['trades']} "
            f"إجمالي {st['gross']}. المرجع {spec}. أوقف. لا مرشّحات."
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
        print((can.stdout or "")[-1200:])
        print((can.stderr or "")[-600:])
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
    print("\n══ مصنّف يومي shift(1) — كاش 4 ساعات الرسمي + to_bars(1440) ══")
    for sym in SYMS:
        path = DAILY / f"{sym}_1d.parquet"
        if not path.exists():
            t0 = time.time()
            d1 = C.load(
                str(ROOT / "crypto_archive" / f"{sym}_1m.parquet"),
                start=WARM, end=JUD_E,
            )
            C.to_bars(d1, 1440).to_parquet(path)
            del d1
            print(f"  يومي {sym} ({time.time() - t0:.1f}s)", flush=True)
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
    """إزاحة شمعة: إشارة الآلة على شمعة التأكيد، والدخول على افتتاح التي بعدها.

    التأكيد عند j إن كانت الإشارة الأصلية عند j-1 وإغلاق j فوق إغلاق j-1.
    لا يُستخدم إغلاق مستقبلي. الآلة لا تُمس.
    """
    prev_sig = base.shift(1)
    prev_sig = prev_sig.where(prev_sig.notna(), False).astype(bool)
    prev_close = df["close"].shift(1)
    ok = prev_sig & prev_close.notna() & (df["close"] > prev_close)
    return ok.fillna(False)


def apply_static(df: pd.DataFrame, sig: pd.Series, parts: tuple) -> pd.Series:
    """قيود تُعرف عند إغلاق شمعة إشارة الآلة. لا نظرة إلى ما بعد ذلك الإغلاق إلا افتتاح التعبئة (ج)."""
    out = sig.fillna(False).astype(bool).copy()
    if not len(parts):
        return out
    vol = df["volume"]
    vol_ma = vol.shift(1).rolling(20, min_periods=20).mean()
    a = C.atr(df)
    body = (df["close"] - df["open"]).abs()
    rng = df["high"] - df["low"]
    nxt = df["open"].shift(-1)
    for part in parts:
        kind = part[0]
        if kind == "vol":
            k = float(part[1])
            out = out & vol_ma.notna() & (vol > k * vol_ma)
        elif kind == "atr":
            v = float(part[1])
            out = out & a.notna() & (df["close"] > 0) & (a / df["close"] >= v)
        elif kind == "body":
            b = float(part[1])
            out = out & (rng > 0) & (body / rng >= b)
        elif kind == "zone":
            m = float(part[1])
            # سعر التعبئة السوقي = افتتاح الشمعة التالية، لا سعر الكلفة المحاسبي.
            out = out & nxt.notna() & a.notna() & (nxt <= df["close"] + m * a)
        elif kind in ("confirm", "cool"):
            continue
        else:
            raise SystemExit(f"جزء مرشّح غير معروف: {part}")
    return out.fillna(False)


def machine_signal(df, sym, parts: tuple) -> pd.Series:
    base = routed_signal(df, sym)
    confirms = [p for p in parts if p[0] == "confirm"]
    if len(confirms) > 1:
        raise SystemExit("تأكيد مكرر في التركيب")
    if confirms:
        base = shift_confirm(df, base)
    static = tuple(p for p in parts if p[0] not in ("confirm", "cool"))
    return apply_static(df, base, static)


def norm_parts(parts) -> list:
    out = []
    for p in parts:
        if not isinstance(p, (list, tuple)) or not p:
            raise SystemExit(f"جزء تالف: {p}")
        head = p[0]
        tail = []
        for x in p[1:]:
            tail.append(x if isinstance(x, str) else float(x))
        out.append([head, *tail])
    return out


def cool_n(parts: tuple) -> int | None:
    ns = [int(p[1]) for p in parts if p[0] == "cool"]
    if not ns:
        return None
    # AND تهدئتين = الأطول. لا تمريرتان متتاليتان.
    return max(ns)


def simulate_mask(parts: tuple, s0: str, s1: str, exp: str) -> tuple[list[dict], dict]:
    old = C.STOP_ATR
    C.STOP_ATR = STOP
    rows: list[dict] = []
    sig_in = 0
    sig_out = 0
    cool_blocked = 0
    ncool = cool_n(parts)
    try:
        for sym in SYMS:
            df = R46.frames(sym)
            win = R48.window(df, s0, s1)
            if len(win) < 100:
                continue
            base_n = int(routed_signal(df, sym).reindex(win.index, fill_value=False).fillna(False).astype(bool).sum())
            sig_in += base_n
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
                mask = sg.to_numpy()
                accepted = np.zeros(len(win), dtype=bool)
                last_exit = -1
                cool_until = -1
                for i in np.flatnonzero(mask):
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
                        # منع الدخول n شمعة بعد شمعة الخروج: إشارات i حيث exit_j <= i <= exit_j+n-1
                        cool_until = max(cool_until, int(rec["exit_j"]) + ncool - 1)
                chosen = R48.greedy(outcomes, accepted)
                rows.extend(R48.rows_from_chosen(sym, exp, chosen))
    finally:
        C.STOP_ATR = old
    meta = {"sig_in": sig_in, "sig_out": sig_out, "cool_blocked": cool_blocked}
    return tag_regime(rows), meta


def assert_equivalent(s0: str, s1: str, cost: float, label: str) -> None:
    set_cost(cost)
    try:
        direct, _ = simulate_mask((), s0, s1, "eq")
        cached = []
        for sym in SYMS:
            df = R46.frames(sym)
            win = R48.window(df, s0, s1)
            if len(win) < 100:
                continue
            table = R48.outcomes_for(sym, s0, s1)
            sg = routed_signal(df, sym).reindex(win.index, fill_value=False).fillna(False).astype(bool).to_numpy()
            cached.extend(R48.rows_from_chosen(sym, "eq", R48.greedy(table, sg)))
        ds, cs = summarize(direct, cost), summarize(cached, cost)
        if abs(ds["net"] - cs["net"]) > 0.01 or ds["trades"] != cs["trades"]:
            raise SystemExit(f"تكافؤ المسار المستقل فشل {label}: {ds['net']}/{ds['trades']} ≠ {cs['net']}/{cs['trades']}")
        print(f"  ✅ تكافؤ simulate/outcomes {label}: {ds['net']}$ / {ds['trades']}")
    finally:
        restore_cost()


def phase0() -> dict:
    print("\n══ مرحلة 0: أربعة مراجع (لا تُحسب) ══")
    store = {}
    for cost, lbl, s0, s1 in (
        (0.0013, "SEL", DEC_S, DEC_E),
        (0.0013, "JUD", JUD_S, JUD_E),
        (0.0010, "SEL", DEC_S, DEC_E),
        (0.0010, "JUD", JUD_S, JUD_E),
    ):
        set_cost(cost)
        try:
            rows, _ = simulate_mask((), s0, s1, "routed")
            save_trades(f"p0_routed_{cost_tag(cost)}_{lbl}", rows)
            st = summarize(rows, cost)
            gate("routed", cost, lbl, st, P0[("routed", cost, lbl)])
            if cost == 0.0010 and lbl == "JUD":
                if st["move"] is None or not (0.0305 <= st["move"] < 0.0315):
                    raise SystemExit(
                        f"حركة الحكم عند 0.10% = {st['move']} لا تُقرَّب إلى 0.031$. أوقف."
                    )
            store[(cost, lbl)] = rows
        finally:
            restore_cost()
    print("  ✅ الأربعة طابقت")
    return store


def article1(store: dict) -> dict:
    print("\n══ مادة 1: أرقام الورقة خارج المرحلة 0 (لا تُحسب) ══")
    out = {}
    for cost, lbl, s0, s1, kind in (
        (0.0013, "SEL", DEC_S, DEC_E, "unrouted"),
        (0.0013, "JUD", JUD_S, JUD_E, "unrouted"),
    ):
        set_cost(cost)
        try:
            old = C.STOP_ATR
            C.STOP_ATR = STOP
            rows = []
            try:
                for sym in SYMS:
                    df = R46.frames(sym)
                    win = R48.window(df, s0, s1)
                    if len(win) < 100:
                        continue
                    sg = R48.portfolio_signal(df, sym).reindex(win.index, fill_value=False).fillna(False).astype(bool)
                    _, tr = C.simulate(
                        win, sg, C.atr(win), notional=C.TRADE_USD, bar_secs=BAR,
                        strict_single=True, atr_trail=TRAIL,
                    )
                    rows.extend(C.trade_rows(sym, "unrouted", tr))
            finally:
                C.STOP_ATR = old
            rows = tag_regime(rows)
            save_trades(f"art1_unrouted_{cost_tag(cost)}_{lbl}", rows)
            st = summarize(rows, cost)
            gate("unrouted", cost, lbl, st, ART1[("unrouted", cost, lbl)])
            out[(kind, cost, lbl)] = st
        finally:
            restore_cost()
    set_cost(0.00075)
    try:
        rows, _ = simulate_mask((), JUD_S, JUD_E, "routed")
        save_trades("art1_routed_c00075_JUD", rows)
        st = summarize(rows, 0.00075)
        gate("routed", 0.00075, "JUD", st, ART1[("routed", 0.00075, "JUD")])
        if st["move"] is None or not (0.0295 <= st["move"] < 0.0305):
            raise SystemExit(
                f"حركة الحكم عند 0.075% = {st['move']} لا تُقرَّب إلى 0.030$. أوقف. لا أغيّر الهدف."
            )
        out[("routed", 0.00075, "JUD")] = st
        store[(0.00075, "JUD")] = rows
        # عشوائي L0052 لإثبات 156.53$. نفس البذور ونفس مطابقة العدد لكل عملة.
        outs = {}
        for sym in SYMS:
            win = R48.window(R46.frames(sym), JUD_S, JUD_E)
            if len(win) < 100:
                continue
            outs[sym] = R48.outcomes_for(sym, JUD_S, JUD_E)
        t = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["symbol"])
        tgt = {sym: int((t["symbol"] == sym).sum()) if len(t) else 0 for sym in outs}
        nets = []
        for seed in VERIFY_SEEDS:
            rnd_rows = []
            for sym, table in outs.items():
                u = R48.uniforms(seed, sym, len(table))
                p = R48.match_p(table, u, tgt.get(sym, 0))
                rnd_rows.extend(R48.rows_from_chosen(sym, f"vfy{seed}", R48.greedy(table, u < p)))
            save_trades(f"art1_rnd_c00075_s{seed}_JUD", rnd_rows)
            rs = summarize(rnd_rows, 0.00075)
            nets.append(rs["net"])
            print(f"  [لا يُحسب] تحقق عشوائي 0.075% بذرة {seed} حكم: {rs['net']}$ / {rs['trades']}")
        mean = round(float(np.mean(nets)), 2)
        lo, hi = round(float(min(nets)), 2), round(float(max(nets)), 2)
        gap = round(st["net"] - hi, 2)
        print(f"  عشوائي 0.075% حكم: متوسط={mean} [{lo}، {hi}] تفوق على الأسعد={gap}")
        if abs(mean - ART1_RND["mean"]) > 0.5 or abs(lo - ART1_RND["min"]) > 0.5 or abs(hi - ART1_RND["max"]) > 0.5:
            raise SystemExit(
                f"عشوائي L0052 خالف الورقة: {mean} [{lo}، {hi}] المرجع {ART1_RND}. أوقف."
            )
        if abs(gap - ART1_RND["gap"]) > 0.5:
            raise SystemExit(f"تفوق 156.53$ لم يُطابق: {gap}. أوقف.")
        out["rnd_0.075_JUD"] = {"mean": mean, "min": lo, "max": hi, "gap": gap, "nets": nets}
        print("  ✅ مادة 1 طابقت، بما فيها 156.53$")
    finally:
        restore_cost()
    return out


def reject_rate(trades: int, base: int) -> float | None:
    if not base:
        return None
    return round(1.0 - trades / base, 4)


def run_spec(spec: dict, s0: str, s1: str, wname: str, cost: float, counted: bool,
             base_trades: int, order: int) -> tuple[dict, list[dict]]:
    set_cost(cost)
    try:
        rows, meta = simulate_mask(tuple(spec["parts"]), s0, s1, spec["id"])
        save_trades(f"{spec['id']}_{cost_tag(cost)}_{'SEL' if wname == 'اختيار' else 'JUD'}", rows)
        extra = {
            "id": spec["id"], "label": spec["label"], "parts": list(spec["parts"]),
            "order": order, "reject": reject_rate(0, 1),
            "sig_in": meta["sig_in"], "sig_out": meta["sig_out"],
            "cool_blocked": meta["cool_blocked"],
        }
        rec = record(spec["label"], wname, rows, cost, None, counted, extra)
        rec["reject"] = reject_rate(rec["trades"], base_trades)
        rec["order"] = order
        print(f"      رفض={rec['reject']} إشارات {meta['sig_in']}→{meta['sig_out']} تهدئة_منعت={meta['cool_blocked']}")
        return rec, rows
    finally:
        restore_cost()


def pick_top3(singles: list[dict]) -> list[dict]:
    qual = [r for r in singles if r["trades"] >= MIN_TRADES and r["move"] is not None]
    qual.sort(key=lambda r: (-r["move"], -r["trades"], r["order"]))
    return qual[:3]


def combos_of(top3: list[dict]) -> list[dict]:
    specs = []
    ids = [r["id"] for r in top3]
    by_id = {r["id"]: r for r in top3}
    pairs = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            pairs.append((ids[i], ids[j]))
    groups = list(pairs)
    if len(ids) == 3:
        groups.append(tuple(ids))
    for group in groups:
        parts = []
        labels = []
        for i in group:
            parts.extend(by_id[i]["parts"])
            labels.append(by_id[i]["label"])
        specs.append({
            "id": "combo_" + "+".join(group),
            "label": " + ".join(labels),
            "parts": tuple(parts),
            "members": list(group),
        })
    return specs


def pick_winner(cands: list[dict]) -> dict | None:
    qual = [r for r in cands if r["trades"] >= MIN_TRADES and r["net"] > 0 and r["move"] is not None]
    if not qual:
        return None
    qual.sort(key=lambda r: (-r["move"], -r["net"], -r["trades"], r["order"]))
    return qual[0]


def seeds_for(rows_direct: list[dict], cost: float) -> list[dict]:
    print(f"\n══ بذور الحكم عند {cost:.3%} — نفس عدد صفقات الفائز تقريبًا ══")
    set_cost(cost)
    out = []
    try:
        outs = {}
        for sym in SYMS:
            win = R48.window(R46.frames(sym), JUD_S, JUD_E)
            if len(win) < 100:
                continue
            outs[sym] = R48.outcomes_for(sym, JUD_S, JUD_E)
        # عشوائي L0048: دخول حرّ بعدد صفقات الفائز لكل عملة، لا خلط إشاراته.
        t = pd.DataFrame(rows_direct) if rows_direct else pd.DataFrame(columns=["symbol"])
        tgt = {sym: int((t["symbol"] == sym).sum()) if len(t) else 0 for sym in outs}
        for seed in SEEDS:
            rows = []
            for sym, table in outs.items():
                u = R48.uniforms(seed, sym, len(table))
                p = R48.match_p(table, u, tgt.get(sym, 0))
                rows.extend(R48.rows_from_chosen(sym, f"rnd{seed}", R48.greedy(table, u < p)))
            save_trades(f"rnd_{cost_tag(cost)}_s{seed}_JUD", rows)
            out.append(record(f"عشوائي {cost:.3%} بذرة {seed}", "حكم", rows, cost, seed, True))
    finally:
        restore_cost()
    return out


def decompositions(books: list[tuple[str, float, str, list[dict]]]) -> None:
    contrib = []
    for name, cost, lbl, rows in books:
        for reg in list(REGIMES) + ["غير مصنّف"]:
            part = [r for r in rows if r.get("regime") == reg]
            st = summarize(part, cost)
            contrib.append({"القياس": name, "cost": cost, "الفترة": lbl, "المناخ": reg, **st})
    pd.DataFrame(contrib).to_csv(OUT / "regime_contribution.csv", index=False, encoding="utf-8-sig")
    print("  تفكيك المناخ كُتب (ليس قياسًا جديدًا)")


def guards() -> None:
    print("\n══ حرّاس ══")
    bad = []
    frames = pathlib.Path.home() / ".cache" / "l0046_frames"
    for f in sorted(OUT.glob("trades_*.csv")):
        name = f.name
        cost = 0.0013
        for tag, c in (
            ("c00075", 0.00075), ("c00100", 0.0010), ("c00130", 0.0013),
        ):
            if tag in name:
                cost = c
                break
        st = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "fill_invariant_check.py"),
             "--trades", str(f), "--frames", str(frames),
             "--cost", str(cost), "--bar-tag", "4h"],
            capture_output=True, text=True,
        )
        line = next((ln for ln in st.stdout.splitlines() if f.name in ln), "")
        if st.returncode != 0 or "تُخطّي=0" not in st.stdout or "شموع ناقصة=0" not in st.stdout:
            bad.append(name + " fill")
            print(" FAIL", name, (st.stdout or "")[-300:], (st.stderr or "")[-200:])
        else:
            print(" ", line.strip())
        au = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "position_sequencing_audit.py"),
             "--trades", str(f), "--require-zero"],
            capture_output=True, text=True,
        )
        if au.returncode != 0:
            bad.append(name + " seq")
            print(" FAIL seq", name, (au.stdout or "")[-200:])
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
        "sig_in", "sig_out", "cool_blocked", "parts", "members",
    )
    out = {}
    for k in keep:
        if k in rec and rec[k] is not None:
            v = rec[k]
            if isinstance(v, float):
                v = round(v, 8) if k in ("move", "cost_per") else v
            out[k] = v
    return out


def write_outputs(canary: dict, lab: str, art1: dict, winner: dict | None,
                  singles: list[dict], top3: list[dict], combos: list[dict],
                  judged: list[dict]) -> None:
    pd.DataFrame([slim(r) for r in MEASURED]).to_csv(OUT / "measurements.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(LEDGER).to_csv(OUT / "attempt_ledger.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([slim(r) for r in singles]).to_csv(OUT / "singles.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([slim(r) for r in combos]).to_csv(OUT / "combos.csv", index=False, encoding="utf-8-sig")
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
    # filter_choice.json كُتب قبل الحكم ولا يُعاد كتابته هنا.
    if not (OUT / "filter_choice.json").exists():
        raise SystemExit("filter_choice.json مفقود")
    env = {
        "python": platform.python_version(), "pandas": pd.__version__,
        "numpy": np.__version__, "platform": platform.platform(),
        "cost_default_file": DEFAULT_COST, "stop": STOP, "trail": TRAIL,
        "seeds": list(SEEDS), "verify_seeds": list(VERIFY_SEEDS),
        "cap": CAP, "counted": len(LEDGER),
        "map": "copied from L0051/routing_map.json", "map_regenerated": False,
        "canary": canary.get("canary"),
        "canary_net": canary.get("got", {}).get("net"),
        "canary_lab": lab, "regime_py_used": False, "alternative_loader": False,
        "move_target": MOVE_TARGET, "min_trades": MIN_TRADES,
        "phase1_defined": 15, "phase1_ceiling": 24,
        "rule": RULE,
    }
    (OUT / "env_dump.txt").write_text(json.dumps(env, ensure_ascii=False, indent=2), encoding="utf-8")
    facts = {
        "counted": len(LEDGER),
        "cap": CAP,
        "article1": {str(k): v for k, v in art1.items() if k != "rnd_0.075_JUD"},
        "article1_rnd": art1.get("rnd_0.075_JUD"),
        "singles": [slim(r) for r in singles],
        "top3": [slim(r) for r in top3],
        "combos": [slim(r) for r in combos],
        "winner": None if winner is None else slim(winner),
        "judged": [slim(r) for r in judged],
        "random": rows,
        "rule": RULE,
    }
    dump_json(OUT / "facts.json", facts)
    blobs = []
    for name in (
        "measurements.csv", "random_summary.csv", "attempt_ledger.csv",
        "routing_map.json", "filter_choice.json", "singles.csv", "combos.csv", "facts.json",
    ):
        data = (OUT / name).read_bytes()
        blobs.append(f"{name} {hashlib.sha256(data).hexdigest()}")
    (OUT / "sha256.txt").write_text("\n".join(blobs) + "\n", encoding="utf-8")
    print("\n".join(blobs))
    restore_cost()
    if abs(C.COST_PER_SIDE - DEFAULT_COST) > 1e-15:
        raise SystemExit("لم تُعَد كلفة الافتراضي")


def write_precommit() -> None:
    lines = [
        "مكتوب قبل أي رقم حكم. لا يُعدَّل بعد الرؤية.",
        RULE,
        "تعريفات المرشّحات (مقفلة):",
        "أ الحجم: حجم شمعة إشارة الآلة > k × متوسط 20 شمعة سابقة (shift(1)، لا تضمّ الشمعة نفسها). k=1.2 1.5 1.8.",
        "ب التأكيد: إشارة الآلة تنتقل إلى الشمعة التالية فقط إن أغلقَت فوق إغلاق شمعة الإشارة. الدخول على افتتاح التي بعدها. الآلة لا تُمس.",
        "ج المنطقة: رفض إن كان افتتاح الشمعة التالية (سعر السوق، لا سعر الكلفة) أبعد من m×ATR(14) فوق إغلاق شمعة إشارة الآلة. m=0.3 0.6 1.0. الفجوة الهابطة لا تُرفض.",
        "د التقلب: رفض إن ATR(14)/إغلاق < v. v=0.005 0.010 0.015. المساواة تمرّ.",
        "هـ الجسم: رفض إن |إغلاق-افتتاح|/المدى < b. المدى 0 يُرفض. b=0.4 0.6. المساواة تمرّ.",
        "و التهدئة: بعد صفقة pnl مُقرَّب < 0، تُمنع إشارات الدخول التي تُعبّئ خلال n شمعة بعد شمعة الخروج. n=3 6 12.",
        "التركيب: التأكيد أولًا، ثم أ/ج/د/هـ على شمعة إشارة الآلة، ثم التهدئة في مرور أمامي واحد. AND تهدئتين = الأطول.",
        "الحركة = الإجمالي الخام قبل التقريب / الصفقات. النجاح ≥ 0.042 على حكم 0.10%، لا بالتقريب إلى ثلاث خانات.",
        "نسبة الرفض = 1 - صفقات المرشّح / صفقات المسنَدة في الفترة والكلفة نفسها.",
        "أعلى ثلاثة: حركة الصفقة، شرط ≥400 في الاختيار. كسر التعادل: صفقات أكثر، ثم ترتيب المرحلة 1.",
        "المرحلة 1 = 15. سقفها 24. لا تُملأ التسعة.",
        "المرحلة 2 = أزواج الثلاثة ثم الثلاثة. سقفها 12. لا رابع.",
        "المرحلة 3 = فائز 0.10% حكم + فائز 0.075% حكم + 5 بذور. الأساس من المرحلة 0 لا يُعاد. سقفها 9.",
        "بذور الحكم: 110053 210053 310053 410053 510053.",
        "عشوائي الاختيار لم يُقَس. عشوائي 0.075% على الفائز لم يُقَس. لا يُضاف بعد الرؤية.",
        "مقياس السطر الأول: حركة حكم 0.10%، وصافٍ موجب في الفترتين عند 0.10%.",
    ]
    (OUT / "grid_precommitted.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    t0 = time.time()
    print("═" * 74)
    print(" L0053 — مرشّحات جودة. خريطة مجمَّدة. السقف 45.")
    print("═" * 74)
    write_precommit()
    canary = run_canary()
    run_selftests()
    lab = lab_canary_status()
    prepare()
    build_regimes()
    store = phase0()
    art1 = article1(store)
    print("\n══ تكافؤ المسار المستقل قبل أي تهدئة ══")
    assert_equivalent(DEC_S, DEC_E, 0.0010, "اختيار 0.10%")
    assert_equivalent(JUD_S, JUD_E, 0.0010, "حكم 0.10%")
    assert_equivalent(JUD_S, JUD_E, 0.00075, "حكم 0.075%")
    assert_equivalent(DEC_S, DEC_E, 0.0013, "اختيار 0.13%")

    print("\n══ مرحلة 1: 15 مرشّحًا على الاختيار عند 0.10% ══")
    base_sel = summarize(store[(0.0010, "SEL")], 0.0010)["trades"]
    singles = []
    single_rows = {}
    for i, spec in enumerate(PHASE1):
        rec, rows = run_spec(spec, DEC_S, DEC_E, "اختيار", COST_REF, True, base_sel, i)
        singles.append(rec)
        single_rows[spec["id"]] = rows
    if len(LEDGER) != 15:
        raise SystemExit(f"مرحلة 1 عدّها {len(LEDGER)} ≠ 15")

    top3 = pick_top3(singles)
    print("\n══ الثلاثة الأولى (قاعدة مكتوبة، لا صافٍ) ══")
    for r in top3:
        print(f"  {r['label']}: حركة={r['move']:.5f} صفقات={r['trades']} صافٍ={r['net']}")
    dump_json(OUT / "top3_before_combos.json", {"rule_top3": "حركة، ≥400، لا شرط صافٍ", "top3": [slim(r) for r in top3]})

    print("\n══ مرحلة 2: التركيبات على الاختيار عند 0.10% ══")
    combo_specs = combos_of(top3)
    combos = []
    combo_rows = {}
    for j, spec in enumerate(combo_specs):
        rec, rows = run_spec(spec, DEC_S, DEC_E, "اختيار", COST_REF, True, base_sel, 100 + j)
        combos.append(rec)
        combo_rows[spec["id"]] = rows

    cands = []
    for r in top3:
        cands.append(r)
    cands.extend(combos)
    winner = pick_winner(cands)
    choice_path = OUT / "filter_choice.json"
    dump_json(choice_path, {
        "rule": RULE,
        "written_before_judgement": True,
        "top3_ids": [r["id"] for r in top3],
        "winner_id": None if winner is None else winner["id"],
        "winner_parts": None if winner is None else winner.get("parts"),
        "winner_label": None if winner is None else winner.get("label"),
        "selection_net": None if winner is None else winner["net"],
        "selection_trades": None if winner is None else winner["trades"],
        "selection_move": None if winner is None else winner["move"],
    })
    if not choice_path.exists():
        raise SystemExit("filter_choice.json لم يُكتب قبل الحكم")
    frozen = json.loads(choice_path.read_text(encoding="utf-8"))
    print(f"\n══ الفائز المجمَّد قبل الحكم: {frozen['winner_id']} ══")

    judged = []
    books = []
    if frozen["winner_id"] is None:
        print("  لا فائز بموجب القاعدة. الحكم لم يُقَس. لا استبدال.")
    else:
        spec = None
        for s in PHASE1 + combo_specs:
            if s["id"] == frozen["winner_id"]:
                spec = s
                break
        if spec is None or norm_parts(spec["parts"]) != norm_parts(frozen["winner_parts"]):
            raise SystemExit("الفائز المجمَّد لا يطابق المواصفات المكتوبة")
        print("\n══ مرحلة 3: الحكم بالمرشّح المجمَّد فقط ══")
        base10 = summarize(store[(0.0010, "JUD")], 0.0010)["trades"]
        base75 = summarize(store[(0.00075, "JUD")], 0.00075)["trades"]
        rec10, rows10 = run_spec(spec, JUD_S, JUD_E, "حكم", 0.0010, True, base10, 200)
        rec75, rows75 = run_spec(spec, JUD_S, JUD_E, "حكم", 0.00075, True, base75, 201)
        judged.extend([rec10, rec75])
        rnd = seeds_for(rows10, 0.0010)
        judged.extend(rnd)
        books.append((spec["label"], 0.0010, "اختيار", single_rows.get(spec["id"]) or combo_rows.get(spec["id"]) or []))
        books.append((spec["label"], 0.0010, "حكم", rows10))
        books.append((spec["label"], 0.00075, "حكم", rows75))
    if books:
        decompositions(books)
    else:
        print("  تفكيك الحكم: لم يُقَس (لا فائز)")

    expected = 15 + len(combos) + (7 if frozen["winner_id"] else 0)
    if len(LEDGER) != expected:
        raise SystemExit(f"العدّ {len(LEDGER)} ≠ القاعدة {expected}")
    if len(LEDGER) > CAP:
        raise SystemExit("تجاوز السقف")

    write_outputs(canary, lab, art1, winner, singles, top3, combos, judged)
    guards()
    print(f"انتهى في {time.time() - t0:.0f}s  العدّ={len(LEDGER)}/{CAP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
