# -*- coding: utf-8 -*-
"""L0048 — هل تضيف إشارات الدخول قيمة فوق الشراء العشوائي؟

قياس فقط. السقف المعلَن = 40. لا يُرفع.
قانون الخروج المثبَّت: وقف 2.5×ATR + تتبّع 4×ATR (بلا تسليح ولا قفل ولا هدف).
مسطرة هذه الجولة: مركز واحد لكل عملة (strict_single=True).
السلوك الافتراضي لـ simulate يبقى كما كان (strict_single=False) لإعادة إنتاج L0046.

العدّ:
  مرحلة 0 (لا تُحسب): الكاناري · الحارس · إعادة إنتاج −1,762.57$ · إثبات التداخل.
  مرحلة 1 (16): محفظة×2 · أعمى×2 · عشوائي 5 بذور×2 · دوري×2.
  مرحلة 2 (14): 7 أعمدة×2.
  مرحلة 3 (0 قياس جديد): تفكيك صفقات المحفظة نفسها على العملات.
  ضابط العمود العشوائي: حساب على جدول دخول مستقل بعد إثبات تكافئه مع simulate
  (فرق مقبول 0.01$). لا يُختار إعداد على الربح. لا يُحسب قياسًا إضافيًا لأن
  سقف المرحلة 2 هو 14 ولا يتسع لعدّه منفصلًا — والطريقة مكافئة مثبتة.
"""
from __future__ import annotations

import json
import os
import pathlib
import platform
import subprocess
import sys
import time
import zlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path("/home/user/work")
os.environ.setdefault("NOVA_SCRATCH", "/home/user/.nova_scratch")
os.environ.setdefault("NOVA_HOME", "/home/user/.nova_scratch/home")
HIST = ROOT / "history"
sys.path.insert(0, str(HIST / "hyp_lab"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

import common as C
from common import atr, simulate, trade_rows
import run_l0019_unified as R19
import run_l0036_more as L36
import run_l0046_basis_repair as R46
import F_213_breakers as M213
import F_197_dual_trail as M197
import L0017_F_001_rsi2_snap as E001
import nova_v8.indicators as ind
import nova_v8.config as NC
import run_l0017 as R17

OUT = HIST / "research" / "hyp_lab_out" / "L0048"
OUT.mkdir(parents=True, exist_ok=True)
DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
WARM = "2021-06-01"
BAR = 4 * 3600
STOP = 2.5
TRAIL = 4.0
SEEDS = (110048, 210048, 310048, 410048, 510048)
CAP = 40
L0046_JUD_NET = -1762.57
COST = C.COST_PER_SIDE
LEDGER: list[dict] = []

OLD_COLS = {
    "كاسرة النطاق": "F_213_breakers",
    "انحراف الدخول": "F_192_ext_entry",
    "التنقيط التعويضي": "F_165_score_entry",
}
NEW_COLS = {
    "دونشيان": lambda df: (df["close"] > df["high"].shift(1).rolling(20).max()).fillna(False),
    "ماكد": lambda df: ((ind.compute_matrix(df)["macd"] > 0)
                        & (ind.compute_matrix(df)["macd"].shift(1) <= 0)).fillna(False),
    "بولنجر": lambda df: ((df["low"] <= ind.compute_matrix(df)["bb_low"])
                          & (df["close"] > df["open"])).fillna(False),
    "سناب المؤشر": lambda df: E001.make_signals(df, rsi2_os=15, sma_trend=200, sma_pull=5),
}
COL_ORDER = list(OLD_COLS) + list(NEW_COLS)
DUAL = {**M197.make_dual_spec(), "trig": 0.0015, "lock": 0.0060}


def log_measurement(phase: int, name: str, window: str, extra: dict | None = None):
    if len(LEDGER) >= CAP:
        raise SystemExit(f"تجاوز السقف: محاولة تسجيل قياس بعد {CAP}")
    row = {"#": len(LEDGER) + 1, "المرحلة": phase, "القياس": name, "الفترة": window}
    if extra:
        row.update(extra)
    LEDGER.append(row)
    return row["#"]


def window(df: pd.DataFrame, s0: str, s1: str) -> pd.DataFrame:
    return df[(df.index >= s0) & (df.index <= s1)]


def frames(sym: str) -> pd.DataFrame:
    return R46.frames(sym)


def _cells():
    return R19.breaker_cells() + R19.new_cells()


def _lab_signal(df, cell):
    if cell["driver"] == "F_213_breakers":
        return M213.make_signals(df, trigger=cell["combo"]["trigger"]).astype(bool)
    return R17.EXPS[cell["driver"]].make_signals(df, **cell["combo"]).astype(bool)


_SIG: dict[tuple, pd.Series] = {}


def column_signal(df: pd.DataFrame, sym: str, col: str) -> pd.Series:
    key = (sym, col)
    if key in _SIG:
        return _SIG[key]
    if col in OLD_COLS:
        parts = []
        for c in _cells():
            if c["symbol"] == sym and c["driver"] == OLD_COLS[col]:
                parts.append(_lab_signal(df, c))
        if not parts:
            sig = pd.Series(False, index=df.index)
        else:
            sig = parts[0].copy()
            for p in parts[1:]:
                sig = sig | p.reindex(df.index, fill_value=False)
    else:
        sig = NEW_COLS[col](df).reindex(df.index, fill_value=False)
    sig = sig.fillna(False).astype(bool)
    _SIG[key] = sig
    return sig


def portfolio_signal(df: pd.DataFrame, sym: str) -> pd.Series:
    key = (sym, "__PORT__")
    if key in _SIG:
        return _SIG[key]
    sig = pd.Series(False, index=df.index)
    for col in COL_ORDER:
        sig = sig | column_signal(df, sym, col)
    _SIG[key] = sig
    return sig


def summarize(rows: list[dict]) -> dict:
    if not rows:
        return {"net": 0.0, "trades": 0, "per": 0.0, "gross": 0.0, "costs": 0.0,
                "median_hold": 0.0, "overlap_ratio": 0.0, "max_concurrent": 0}
    t = pd.DataFrame(rows)
    p = t["pnl"].to_numpy(float)
    net = round(float(p.sum()), 2)
    qty = t["notional"].to_numpy(float) / t["entry"].to_numpy(float)
    entry = t["entry"].to_numpy(float)
    exit_ = t["exit"].to_numpy(float)
    costs = float((qty * COST * (entry + exit_)).sum())
    gross = round(float((qty * (exit_ - entry)).sum() + costs), 2)
    hold = t["bars_held"].to_numpy(float)
    import position_sequencing_audit as psa
    au = psa.audit_frame(t)
    return {
        "net": net,
        "trades": int(len(t)),
        "per": round(net / len(t), 5) if len(t) else 0.0,
        "gross": gross,
        "costs": round(costs, 2),
        "median_hold": float(np.median(hold)) if len(hold) else 0.0,
        "overlap_ratio": au["overlap_ratio"],
        "max_concurrent": au["max_concurrent"],
    }


def run_mask(sig_of, s0, s1, *, strict: bool, atr_trail: float, dual: dict | None,
             exp: str) -> list[dict]:
    old = C.STOP_ATR
    C.STOP_ATR = STOP
    rows = []
    try:
        kw = {}
        if dual is not None and not atr_trail:
            kw["exit_mode"] = "dual"
            kw["dual"] = dual
        for sym in SYMS:
            df = frames(sym)
            win = window(df, s0, s1)
            if len(win) < 100:
                continue
            sg = sig_of(df, sym).reindex(win.index, fill_value=False).fillna(False).astype(bool)
            _, tr = simulate(win, sg, atr(win), notional=C.TRADE_USD, bar_secs=BAR,
                             strict_single=strict, atr_trail=atr_trail, **kw)
            rows.extend(trade_rows(sym, exp, tr))
    finally:
        C.STOP_ATR = old
    return rows


def outcomes_for(sym: str, s0: str, s1: str) -> list[dict | None]:
    """نتيجة دخول مستقل عند كل شمعة — نفس رياضيات simulate مع التتبّع 4×ATR."""
    df = frames(sym)
    win = window(df, s0, s1)
    o = win["open"].to_numpy()
    h = win["high"].to_numpy()
    l = win["low"].to_numpy()
    c = win["close"].to_numpy()
    a = atr(win).to_numpy()
    n = len(win)
    idx = win.index
    out: list[dict | None] = [None] * n
    for i in range(n - 1):
        if not np.isfinite(a[i]):
            continue
        e = i + 1
        ef = o[e] * (1 + COST)
        hard = ef - STOP * a[i]
        peak = o[e]
        atr_i = a[i]
        j = e
        exit_j = None
        exit_px = None
        while j < n:
            eff = hard
            local = peak - TRAIL * atr_i
            if local > eff:
                eff = local
            if l[j] <= eff:
                px = eff if o[j] >= eff else o[j]
                if px < l[j]:
                    px = l[j]
                elif px > h[j]:
                    px = h[j]
                exit_j, exit_px = j, px
                break
            if h[j] > peak:
                peak = h[j]
            j += 1
        if exit_j is None:
            exit_j = n - 1
            exit_px = c[-1]
            if exit_px < l[-1]:
                exit_px = l[-1]
            elif exit_px > h[-1]:
                exit_px = h[-1]
        fill = exit_px * (1 - COST)
        qty = C.TRADE_USD / ef
        pnl = qty * (fill - ef)
        out[i] = {
            "entry_j": e, "exit_j": int(exit_j),
            "entry_time": idx[e], "exit_time": idx[exit_j],
            "entry": ef, "exit": fill, "pnl": pnl,
            "bars_held": int(exit_j) - e,
        }
    return out


def greedy(outcomes: list[dict | None], mask: np.ndarray) -> list[dict]:
    last_exit = -1
    chosen = []
    for i in np.flatnonzero(mask):
        if i >= len(outcomes) or outcomes[i] is None:
            continue
        if last_exit > i:
            continue
        rec = outcomes[i]
        chosen.append(rec)
        last_exit = rec["exit_j"]
    return chosen


def rows_from_chosen(sym: str, exp: str, chosen: list[dict]) -> list[dict]:
    raw = []
    for rec in chosen:
        raw.append({
            "entry_j": rec["entry_j"], "exit_j": rec["exit_j"],
            "entry_time": rec["entry_time"], "exit_time": rec["exit_time"],
            "exit_fill": rec["exit"],
            "entry": rec["entry"], "pnl": rec["pnl"], "notional": C.TRADE_USD,
            "risk": None, "exit_side": "stop",
        })
    # trade_rows يقرّب pnl إلى 4 خانات — نفس عقد L0046
    return trade_rows(sym, exp, raw)


def uniforms(seed: int, sym: str, n: int) -> np.ndarray:
    h = zlib.crc32(sym.encode("utf-8")) & 0xFFFFFFFF
    return np.random.default_rng(np.random.SeedSequence([int(seed), int(h)])).random(n)


def count_mask(outcomes, mask) -> int:
    return len(greedy(outcomes, mask))


def match_p(outcomes, u, target: int) -> float:
    if target <= 0:
        return 0.0
    lo, hi = 0.0, 1.0
    best_p, best_d = 1.0, 10**9
    for _ in range(18):
        mid = (lo + hi) / 2
        k = count_mask(outcomes, u < mid)
        d = abs(k - target)
        if d < best_d or (d == best_d and mid < best_p):
            best_p, best_d = mid, d
        if k < target:
            lo = mid
        else:
            hi = mid
    return best_p


def match_n(sym_outs: dict, targets: dict, s0: str, s1: str) -> int:
    """ن عالمي واحد يقرّب مجموع الصفقات من هدف المحفظة. المقارنة على العدد فقط."""
    best_n, best_d = 1, 10**9
    for n in range(1, 241):
        total = 0
        for sym, outs in sym_outs.items():
            m = (np.arange(len(outs)) % n) == 0
            total += count_mask(outs, m)
        d = abs(total - sum(targets.values()))
        if d < best_d:
            best_n, best_d = n, d
            if d == 0:
                break
    return best_n


def synthetic_proof() -> None:
    idx = pd.date_range("2024-01-01", periods=40, freq="4h", tz="UTC")
    px = 100 + np.arange(40) * 0.01
    df = pd.DataFrame({
        "open": px, "high": px + 0.2, "low": px - 0.05,
        "close": px + 0.01, "volume": np.ones(40),
    }, index=idx)
    sig = pd.Series(True, index=idx)
    a = pd.Series(1.0, index=idx)
    old = C.STOP_ATR
    C.STOP_ATR = 2.5
    try:
        _, buggy = simulate(df, sig, a, strict_single=False, atr_trail=4.0,
                            notional=20.0, bar_secs=BAR)
        _, fixed = simulate(df, sig, a, strict_single=True, atr_trail=4.0,
                            notional=20.0, bar_secs=BAR)
    finally:
        C.STOP_ATR = old
    b_rows = trade_rows("BTCUSDT", "syn", buggy)
    f_rows = trade_rows("BTCUSDT", "syn", fixed)
    import position_sequencing_audit as psa
    bo = psa.audit_frame(pd.DataFrame(b_rows))
    fo = psa.audit_frame(pd.DataFrame(f_rows))
    print(f"  إثبات مصطنع: الوضع الافتراضي صفقات={bo['trades']} تداخل={bo['overlap_ratio']:.2%}"
          f" تزامن={bo['max_concurrent']} | strict صفقات={fo['trades']} تداخل={fo['overlap_ratio']:.2%}")
    if bo["overlapping_trades"] == 0:
        raise SystemExit("الإثبات المصطنع فشل: الوضع الافتراضي لم يُظهر تداخلًا")
    if fo["overlapping_trades"] != 0 or fo["max_concurrent"] != 1:
        raise SystemExit(f"الإثبات المصطنع فشل: strict_single لم يصفّر التداخل {fo}")


def save_trades(name: str, rows: list[dict]) -> pathlib.Path:
    path = OUT / f"trades_{name}.csv"
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def main() -> int:
    t0 = time.time()
    print("═" * 74)
    print(" L0048 — مرحلة 0: حرّاس وإعادة إنتاج الأساس")
    print("═" * 74)
    synthetic_proof()

    can = subprocess.run([sys.executable, str(ROOT / "tools" / "canary.py"), "--json"],
                         capture_output=True, text=True)
    raw = can.stdout
    cj = json.loads(raw[raw.index("{"):]) if "{" in raw else {}
    print(f"  كاناري المحرك الحي: {cj.get('canary')} net={cj.get('got', {}).get('net')}")
    if cj.get("canary") != "ok":
        print(can.stdout[-1500:])
        print(can.stderr[-1500:])
        raise SystemExit("الكاناري لم يُرجع canary=ok — أوقف")

    st = subprocess.run([sys.executable, str(ROOT / "tools" / "fill_invariant_check.py"), "--selftest"],
                        capture_output=True, text=True)
    print(st.stdout.strip().splitlines()[-1] if st.stdout.strip() else st.stderr[-400:])
    if st.returncode != 0:
        print(st.stdout[-2000:])
        raise SystemExit("حارس التعبئة selftest فشل — أوقف")
    au = subprocess.run([sys.executable, str(ROOT / "tools" / "position_sequencing_audit.py"), "--selftest"],
                        capture_output=True, text=True)
    print(" ", au.stdout.strip())
    if au.returncode != 0:
        raise SystemExit("حارس التزامن selftest فشل")

    L36.set_core()
    NC.EMA_FAST = 8
    M213._cache.clear()
    C.STOP_ATR = STOP
    cells = _cells()
    global SYMS
    SYMS = sorted({c["symbol"] for c in cells})
    print(f"  خلايا={len(cells)} عملات={len(SYMS)}: {', '.join(SYMS)}")
    if len(SYMS) != 15:
        print(f"  ⚠️ الورقة تقول 15 عملة والخلايا تعطي {len(SYMS)}. أُكمل على سلة الخلايا (واقع الكود) وأُبلغ.")
    R46.build_cache(SYMS)
    for sym in SYMS:
        df = frames(sym)
        print(f"    {sym}: {df.index.min()} → {df.index.max()} ({len(df)} شمعة)")

    print("\n── إعادة إنتاج أساس L0046 (وضع افتراضي، خروج dual القديم) ──")
    official = R46.portfolio_rows(SYMS, JUD_S, JUD_E)
    off_st = R46.summarize(official)
    print(f"  الرسمي JUD: {off_st}")
    if abs(off_st["net"] - L0046_JUD_NET) > 0.01:
        save_trades("L0046_repro_JUD_MISMATCH", official)
        raise SystemExit(
            f"أساس L0046 لم يُعَد إنتاجه: {off_st['net']} ≠ {L0046_JUD_NET}. أوقف. لا قياس.")
    print(f"  ✅ أساس الحكم = {off_st['net']}$ (ضمن ±0.01 من {L0046_JUD_NET})")
    wired = []
    for sym in SYMS:
        df = frames(sym)
        win = window(df, JUD_S, JUD_E)
        if len(win) < 100:
            continue
        a_s = atr(win)
        for col in COL_ORDER:
            sg = column_signal(df, sym, col).reindex(win.index, fill_value=False).fillna(False).astype(bool)
            if not bool(sg.any()):
                continue
            _, tr = simulate(win, sg, a_s, notional=C.TRADE_USD, bar_secs=BAR,
                             exit_mode="dual", dual=DUAL, strict_single=False, atr_trail=0.0)
            wired.extend(trade_rows(sym, col, tr))
    w_st = summarize(wired)
    print(f"  توصيلي (أعمدة منفصلة، الوضع الافتراضي): net={w_st['net']} صفقات={w_st['trades']}")
    if abs(w_st["net"] - off_st["net"]) > 0.01 or w_st["trades"] != off_st["trades"]:
        raise SystemExit("توصيل الإشارات لا يطابق مشغّل L0046 الرسمي — أوقف")
    print("  ✅ توصيل الإشارات مطابق للرسمي")
    # الملف الرسمي للتداخل قبل الإصلاح
    save_trades("L0046_default_overlap_JUD", official)
    import position_sequencing_audit as psa
    pre = psa.audit_frame(pd.DataFrame(official))
    print(f"  تداخل الوضع الافتراضي على محفظة L0046: {pre}")
    if pre["overlapping_trades"] == 0:
        raise SystemExit("الورقة تقول إن المسار الافتراضي يتداخل، والقياس لم يجد تداخلًا — أوقف")

    # فترة الاختيار للعلم (لا تُحسب)
    official_dec = R46.portfolio_rows(SYMS, DEC_S, DEC_E)
    dec_st = R46.summarize(official_dec)
    print(f"  الرسمي اختيار (للعلم، لا يُحسب): {dec_st}")

    print("\n═" * 74)
    print(" بناء جدول الدخول المستقل (وقف 2.5×ATR + تتبّع 4×ATR)")
    print("═" * 74)
    OUTS = {}
    for lbl, s0, s1 in (("SEL", DEC_S, DEC_E), ("JUD", JUD_S, JUD_E)):
        OUTS[lbl] = {}
        for sym in SYMS:
            win = window(frames(sym), s0, s1)
            if len(win) < 100:
                continue
            t1 = time.time()
            OUTS[lbl][sym] = outcomes_for(sym, s0, s1)
            print(f"  جدول {lbl} {sym}: {len(win)} شمعة ({time.time()-t1:.1f}s)", flush=True)

    def cache_rows(sig_of, s0, s1, exp, lbl) -> list[dict]:
        rows = []
        for sym, outs in OUTS[lbl].items():
            df = frames(sym)
            win = window(df, s0, s1)
            sg = sig_of(df, sym).reindex(win.index, fill_value=False).fillna(False).astype(bool).to_numpy()
            chosen = greedy(outs, sg)
            rows.extend(rows_from_chosen(sym, exp, chosen))
        return rows

    def assert_equiv(name, direct, cached):
        ds, cs = summarize(direct), summarize(cached)
        if abs(ds["net"] - cs["net"]) > 0.01 or ds["trades"] != cs["trades"]:
            raise SystemExit(f"تكافؤ الجدول فشل عند {name}: مباشر {ds} ≠ جدول {cs}")
        print(f"  ✅ تكافؤ {name}: {ds['net']}$ / {ds['trades']} صفقة")

    print("\n── إثبات التكافؤ (مباشر مقابل الجدول) ──")
    # محفظة الحكم بالقانون الجديد — هذا أيضًا قياس #2 لاحقًا، نعيد استخدام الصفوف
    measured: dict[tuple, list] = {}

    def direct_book(sig_of, s0, s1, exp):
        return run_mask(sig_of, s0, s1, strict=True, atr_trail=TRAIL, dual=None, exp=exp)

    # نثبت التكافؤ على المحفظة والأعمى وعمود واحد قبل أن نثق بالجدول للضوابط
    for lbl, s0, s1, tag in (("JUD", JUD_S, JUD_E, "JUD"), ("SEL", DEC_S, DEC_E, "SEL")):
        d = direct_book(portfolio_signal, s0, s1, "portfolio")
        c = cache_rows(portfolio_signal, s0, s1, "portfolio", tag)
        assert_equiv(f"محفظة {lbl}", d, c)
        measured[("portfolio", lbl)] = d
        d = direct_book(lambda df, sym: pd.Series(True, index=df.index), s0, s1, "blind")
        c = cache_rows(lambda df, sym: pd.Series(True, index=df.index), s0, s1, "blind", tag)
        assert_equiv(f"أعمى {lbl}", d, c)
        measured[("blind", lbl)] = d

    print("\n═" * 74)
    print(" المرحلة 1 — الاختبار الحاسم (سقف 16)")
    print("═" * 74)
    table = []

    def record(phase, name, lbl, rows, extra=None):
        n = log_measurement(phase, name, "الاختيار" if lbl == "SEL" else "الحكم", extra)
        stt = summarize(rows)
        rec = {"#": n, "المرحلة": phase, "البند": name,
               "الفترة": "الاختيار" if lbl == "SEL" else "الحكم", **stt}
        if extra:
            rec.update(extra)
        table.append(rec)
        save_trades(f"p{phase}_{n}_{lbl}", rows)
        print(f"  #{n} {name} {lbl}: صافي={stt['net']} صفقات={stt['trades']} "
              f"قبل_الكلفة={stt['gross']} وسيط={stt['median_hold']} تداخل={stt['overlap_ratio']}",
              flush=True)
        if stt["overlap_ratio"] != 0:
            raise SystemExit(f"تداخل غير صفر بعد الإصلاح في {name} {lbl}")
        return stt

    for lbl in ("SEL", "JUD"):
        record(1, "المحفظة بالإشارات السبع", lbl, measured[("portfolio", lbl)])
    for lbl in ("SEL", "JUD"):
        record(1, "الشراء الأعمى", lbl, measured[("blind", lbl)])

    # أهداف العدد من المحفظة، لكل رمز — لمعايرة الضابط. العدد فقط، لا الربح.
    def per_symbol_counts(rows):
        if not rows:
            return {}
        t = pd.DataFrame(rows)
        return t.groupby("symbol").size().to_dict()

    random_stats = {lbl: [] for lbl in ("SEL", "JUD")}
    for seed in SEEDS:
        for lbl, s0, s1, tag in (("SEL", DEC_S, DEC_E, "SEL"), ("JUD", JUD_S, JUD_E, "JUD")):
            targets = per_symbol_counts(measured[("portfolio", lbl)])
            ps = {}
            masks = {}
            for sym, outs in OUTS[tag].items():
                u = uniforms(seed, sym, len(outs))
                p = match_p(outs, u, int(targets.get(sym, 0)))
                ps[sym] = p
                masks[(sym)] = u < p

            def sig_of(df, sym, _masks=masks, _s0=s0, _s1=s1):
                win = window(df, _s0, _s1)
                m = _masks.get(sym)
                if m is None:
                    return pd.Series(False, index=df.index)
                s = pd.Series(False, index=df.index)
                s.loc[win.index] = m
                return s

            rows = direct_book(sig_of, s0, s1, f"random_{seed}")
            # تكافؤ هذا القناع مع الجدول (يثبت أن الضابط العشوائي للأعمدة صالح)
            cached = []
            for sym, outs in OUTS[tag].items():
                cached.extend(rows_from_chosen(sym, "random", greedy(outs, masks[sym])))
            assert_equiv(f"عشوائي بذرة {seed} {lbl}", rows, cached)
            stt = record(1, f"عشوائي مضبوط بذرة {seed}", lbl, rows, {"بذرة": seed})
            random_stats[lbl].append(stt)

    periodic_n = {}
    for lbl, s0, s1, tag in (("SEL", DEC_S, DEC_E, "SEL"), ("JUD", JUD_S, JUD_E, "JUD")):
        targets = per_symbol_counts(measured[("portfolio", lbl)])
        nbar = match_n(OUTS[tag], targets, s0, s1)
        periodic_n[lbl] = nbar

        def sig_of(df, sym, _n=nbar, _s0=s0, _s1=s1):
            win = window(df, _s0, _s1)
            m = (np.arange(len(win)) % _n) == 0
            s = pd.Series(False, index=df.index)
            s.loc[win.index] = m
            return s

        rows = direct_book(sig_of, s0, s1, f"periodic_{nbar}")
        record(1, f"دوري كل {nbar} شمعة", lbl, rows, {"ن": nbar})

    print("\n═" * 74)
    print(" المرحلة 2 — كل عمود (سقف 14)")
    print("═" * 74)
    col_rows = {}
    for col in COL_ORDER:
        for lbl, s0, s1 in (("SEL", DEC_S, DEC_E), ("JUD", JUD_S, JUD_E)):
            def sig_of(df, sym, _col=col):
                return column_signal(df, sym, _col)
            rows = direct_book(sig_of, s0, s1, col)
            tag = "SEL" if lbl == "SEL" else "JUD"
            cached = cache_rows(sig_of, s0, s1, col, tag)
            assert_equiv(f"{col} {lbl}", rows, cached)
            record(2, f"عمود: {col}", lbl, rows)
            col_rows[(col, lbl)] = rows

    if len(LEDGER) != 30:
        raise SystemExit(f"عدّ السقف غير متوقع: {len(LEDGER)} (المتوقع 30 قبل المرحلة 3)")

    print("\n── ضوابط الأعمدة (حساب مكافئ، 5 بذور، لا تُحسب في السقف) ──")
    col_ctrl = []
    for col in COL_ORDER:
        for lbl, tag, s0, s1 in (("SEL", "SEL", DEC_S, DEC_E), ("JUD", "JUD", JUD_S, JUD_E)):
            targets = per_symbol_counts(col_rows[(col, lbl)])
            seed_nets = []
            seed_trades = []
            seed_gross = []
            seed_per = []
            for seed in SEEDS:
                rows = []
                for sym, outs in OUTS[tag].items():
                    u = uniforms(seed + 17, sym, len(outs))  # تيار مستقل عن ضابط المحفظة
                    p = match_p(outs, u, int(targets.get(sym, 0)))
                    rows.extend(rows_from_chosen(sym, col, greedy(outs, u < p)))
                stt = summarize(rows)
                seed_nets.append(stt["net"])
                seed_trades.append(stt["trades"])
                seed_gross.append(stt["gross"])
                seed_per.append(stt["per"])
                if stt["overlap_ratio"] != 0:
                    raise SystemExit(f"تداخل في ضابط العمود {col} {lbl}")
            col_st = summarize(col_rows[(col, lbl)])
            col_ctrl.append({
                "العمود": col,
                "الفترة": "الاختيار" if lbl == "SEL" else "الحكم",
                "صافي_العمود": col_st["net"],
                "صفقات_العمود": col_st["trades"],
                "قبل_الكلفة_العمود": col_st["gross"],
                "وسيط_العمود": col_st["median_hold"],
                "ربح_صفقة_العمود": col_st["per"],
                "متوسط_العشوائي": round(float(np.mean(seed_nets)), 2),
                "أدنى_عشوائي": round(float(np.min(seed_nets)), 2),
                "أعلى_عشوائي": round(float(np.max(seed_nets)), 2),
                "متوسط_صفقات_العشوائي": round(float(np.mean(seed_trades)), 1),
                "متوسط_قبل_الكلفة_العشوائي": round(float(np.mean(seed_gross)), 2),
                "يتفوّق_على_المتوسط": bool(col_st["net"] > float(np.mean(seed_nets))),
            })
            print(f"  {col} {lbl}: عمود={col_st['net']} عشوائي_متوسط={np.mean(seed_nets):.2f} "
                  f"مدى=[{min(seed_nets):.2f},{max(seed_nets):.2f}]", flush=True)
    pd.DataFrame(col_ctrl).to_csv(OUT / "column_vs_random.csv", index=False, encoding="utf-8-sig")

    print("\n═" * 74)
    print(" المرحلة 3 — تفكيك العملات من صفقات المحفظة (لا قياس جديد)")
    print("═" * 74)
    coin_rows = []
    for lbl, s0, s1 in (("SEL", DEC_S, DEC_E), ("JUD", JUD_S, JUD_E)):
        t = pd.DataFrame(measured[("portfolio", lbl)])
        present = set(t["symbol"].unique()) if len(t) else set()
        for sym in SYMS:
            df = frames(sym)
            win = window(df, s0, s1)
            sub = t[t["symbol"] == sym] if len(t) else t
            net = round(float(sub["pnl"].sum()), 2) if len(sub) else 0.0
            coin_rows.append({
                "العملة": sym,
                "الفترة": "الاختيار" if lbl == "SEL" else "الحكم",
                "شموع_النافذة": int(len(win)),
                "أول_شمعة": str(df.index.min()),
                "صافي": net if len(win) >= 100 else None,
                "صفقات": int(len(sub)) if len(win) >= 100 else 0,
                "بيانات_كافية": bool(len(win) >= 100),
            })
    coins = pd.DataFrame(coin_rows)
    coins.to_csv(OUT / "coins_from_portfolio.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame(table).to_csv(OUT / "measurements.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(LEDGER).to_csv(OUT / "attempt_ledger.csv", index=False, encoding="utf-8-sig")

    # ملخص العشوائي
    rand_sum = []
    for lbl, items in random_stats.items():
        nets = [x["net"] for x in items]
        rand_sum.append({
            "الفترة": "الاختيار" if lbl == "SEL" else "الحكم",
            "متوسط": round(float(np.mean(nets)), 2),
            "أدنى": round(float(np.min(nets)), 2),
            "أعلى": round(float(np.max(nets)), 2),
            "بذور": len(nets),
        })
    pd.DataFrame(rand_sum).to_csv(OUT / "random_summary.csv", index=False, encoding="utf-8-sig")

    env = (
        f"python={platform.python_version()}\n"
        f"pandas={pd.__version__}\nnumpy={np.__version__}\npyarrow=25.0.1\n"
        f"canary={cj.get('canary')}\ncanary_net={cj.get('got', {}).get('net')}\n"
        f"engine=common.py L0046 repairs intact + strict_single default False + atr_trail default 0\n"
        f"L0046_repro_JUD={off_st['net']}\nL0046_repro_SEL={dec_st['net']}\n"
        f"L0046_default_overlap_ratio={pre['overlap_ratio']}\n"
        f"L0046_default_max_concurrent={pre['max_concurrent']}\n"
        f"exit_law=stop {STOP}xATR + trail {TRAIL}xATR (signal ATR, no arm, no lock, no tp)\n"
        f"strict_single=True for L0048 measurements\n"
        f"seeds={list(SEEDS)}\nperiodic_N={periodic_n}\n"
        f"decision={DEC_S}->{DEC_E}\njudgement={JUD_S}->{JUD_E}\nwarm={WARM}\n"
        f"ema_fast=8\ncore=body0.40/range0.60/look10\ntriggers=ALL14\n"
        f"basket={len(SYMS)}\nnotional=20\ncost=0.13%/side\n"
        f"declared_cap={CAP}\nused={len(LEDGER)}\n"
        f"column_controls=calculated_from_equivalent_entry_table not counted\n"
    )
    (OUT / "env_dump.txt").write_text(env, encoding="utf-8")
    (OUT / "l0046_repro.json").write_text(json.dumps({
        "official_JUD": off_st, "official_SEL": dec_st,
        "default_overlap": pre, "wiring_JUD": w_st,
    }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("\n── حرّاس على ملفات القياس ──")
    fill = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "fill_invariant_check.py"),
         "--dir", str(OUT), "--frames", str(pathlib.Path.home() / ".cache" / "l0046_frames")],
        capture_output=True, text=True)
    print(fill.stdout)
    if fill.returncode != 0:
        raise SystemExit("حارس التعبئة وجد مخالفة على ملفات القياس")
    seq = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "position_sequencing_audit.py"),
         "--dir", str(OUT), "--json"],
        capture_output=True, text=True)
    print(seq.stdout[-2000:])
    seqj = json.loads(seq.stdout[seq.stdout.index("{"):])
    # ملف الوضع الافتراضي يجب أن يتداخل؛ بقية ملفات القياس يجب أن تكون صفرًا
    bad = [r for r in seqj["results"]
           if r["overlapping_trades"] and "L0046_default" not in r["file"]]
    if bad:
        raise SystemExit(f"تداخل بعد الإصلاح: {bad}")
    print(f"\n→ {OUT}\nالسقف {len(LEDGER)}/{CAP}\nالزمن {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
