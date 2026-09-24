# -*- coding: utf-8 -*-
"""L0046 — إعادة قياس الأساس بالآلة المصلَحة (المرحلتان 3 و4) + حساسية نموذج التنفيذ.

🔒 السقف المعلَن = 25 قياسًا. هذا السكربت ينفّذ 25 بالضبط:
   المرحلة 3 (20): المحفظة (7 أعمدة) ×2 · كل عمود منفردًا (7×2) · الشراء والاحتفاظ ×2 ·
                   الشراء الدائم بقانون الخروج ×2.
   المرحلة 4 (4) : فلتر المتوسط 200 ×2 · تشديد الوقف 2.0×ATR ×2.
   حساسية (1)    : نموذج «الخروج على افتتاح الشمعة التالية» (كما في المحرك الحي) على المحفظة/الحكم.

الإعدادات المعتمدة: 4h · 15 عملة · 20$/صفقة · 0.13%/طرف · شراء فقط ·
خروج dual (وقف 2.5×ATR · تسليح 0.0015 · قفل 0.0060 · wide 0.0020 · tight 0.0008) ·
نواة 0.40/0.60/10 · ALL14 · EMA_FAST=8.
الفترتان: اختيار 2021-09-01→2023-12-31 · حكم 2024-01-01→2026-08-31.
"""
from __future__ import annotations
import json, os, pathlib, platform, subprocess, sys, time
import numpy as np, pandas as pd

ROOT = pathlib.Path("/home/user/work")
os.environ.setdefault("NOVA_SCRATCH", "/home/user/.nova_scratch")
HIST = ROOT / "history"
sys.path.insert(0, str(HIST / "hyp_lab")); sys.path.insert(0, str(ROOT))

import common as C
from common import atr, load, to_bars, simulate, trade_rows
import run_l0019_unified as R19
import run_l0036_more as L36
import F_213_breakers as M213
import F_197_dual_trail as M197
import L0017_F_001_rsi2_snap as E001
import nova_v8.indicators as ind
import nova_v8.config as NC
import run_l0017 as R17

OUT = HIST / "research" / "hyp_lab_out" / "L0046"
OUT.mkdir(parents=True, exist_ok=True)
CACHE = pathlib.Path.home() / ".cache" / "l0046_frames"
CACHE.mkdir(parents=True, exist_ok=True)
DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
WARM = "2021-06-01"
BAR = 4 * 3600
WIN = {"stop": 2.5, "trig": 0.0015, "lock": 0.0060, "wide": 0.0020, "tight": 0.0008}
CAP = 25
LEDGER = []


def log_measurement(name: str, window: str):
    LEDGER.append({"#": len(LEDGER) + 1, "القياس": name, "الفترة": window})


# ═══════════════════ كاش الإطارات (تحميل مرة واحدة) ═══════════════════
def build_cache(syms):
    todo = [s for s in syms if not (CACHE / f"{s}_4h.parquet").exists()]
    for sym in todo:
        t0 = time.time()
        d1 = load(str(ROOT / "crypto_archive" / f"{sym}_1m.parquet"), start=WARM, end=JUD_E)
        to_bars(d1, 240).to_parquet(CACHE / f"{sym}_4h.parquet")
        del d1
        print(f"  كاش {sym} ({time.time()-t0:.1f}s)", flush=True)


_FR = {}
def frames(sym):
    if sym not in _FR:
        _FR[sym] = pd.read_parquet(CACHE / f"{sym}_4h.parquet")
    return _FR[sym]


def summarize(rows):
    if not rows:
        return {"net": 0.0, "trades": 0, "pf": 0.0, "per": 0.0, "mdd": 0.0}
    t = pd.DataFrame(rows); p = t["pnl"].to_numpy(float)
    g, l = p[p > 0].sum(), -p[p < 0].sum()
    pf = float(g / l) if l > 0 else (np.inf if g > 0 else 0.0)
    eq = np.cumsum(t.sort_values("exit_time")["pnl"].to_numpy(float))
    peak = np.maximum.accumulate(eq)
    net = round(float(p.sum()), 2)
    return {"net": net, "trades": len(t), "pf": round(pf, 4), "per": round(net / len(t), 5),
            "mdd": round(float(np.max(peak - eq)), 2)}


# ═══════════════════ الأعمدة السبعة ═══════════════════
NEW_COLS = {
    "F-042 دونشيان": lambda df: (df["close"] > df["high"].shift(1).rolling(20).max()).fillna(False),
    "F-055 ماكد": lambda df: ((ind.compute_matrix(df)["macd"] > 0) &
                              (ind.compute_matrix(df)["macd"].shift(1) <= 0)).fillna(False),
    "F-063 بولنجر": lambda df: ((df["low"] <= ind.compute_matrix(df)["bb_low"]) &
                                (df["close"] > df["open"])).fillna(False),
    "F-001 سناب المؤشر": lambda df: E001.make_signals(df, rsi2_os=15, sma_trend=200, sma_pull=5),
}
OLD_COLS = {"كاسرة النطاق": "F_213_breakers", "انحراف الدخول": "F_192_ext_entry",
            "التنقيط التعويضي": "F_165_score_entry"}


def _cells(which=None):
    cells = R19.breaker_cells() + R19.new_cells()
    if which:
        cells = [c for c in cells if c["driver"] == which]
    return cells


def _lab_signal(df, cell):
    if cell["driver"] == "F_213_breakers":
        return M213.make_signals(df, trigger=cell["combo"]["trigger"])
    return R17.EXPS[cell["driver"]].make_signals(df, **cell["combo"])


def portfolio_rows(symbols, s0, s1, which=None, extra_filter=None, stop_atr=None, name="X"):
    """صفقات مجموعة أعمدة. extra_filter(df) → Series بوليانية تُضاف لِكل إشارة (فلتر)."""
    kw = {"exit_mode": "dual",
          "dual": {**M197.make_dual_spec(), "trig": WIN["trig"], "lock": WIN["lock"]}}
    old_stop = C.STOP_ATR
    if stop_atr is not None:
        C.STOP_ATR = stop_atr
    rows = []
    try:
        for sym in symbols:
            df = frames(sym)
            win = df[(df.index >= s0) & (df.index <= s1)]
            if len(win) < 100:
                continue
            a_s = atr(win)
            keep = extra_filter(win) if extra_filter is not None else None
            cells = _cells(which)
            for c in cells:
                if c["symbol"] != sym:
                    continue
                sg = _lab_signal(df, c).loc[win.index]
                if keep is not None:
                    sg = sg & keep
                _, tr = simulate(win, sg, a_s, notional=C.TRADE_USD, bar_secs=BAR, **kw)
                rows.extend(trade_rows(sym, c["driver"], tr))
            if which is None:                      # الأعمدة الأربعة (دوال)
                for nm, fn in NEW_COLS.items():
                    sg = fn(df).loc[win.index]
                    if keep is not None:
                        sg = sg & keep
                    _, tr = simulate(win, sg, a_s, notional=C.TRADE_USD, bar_secs=BAR, **kw)
                    rows.extend(trade_rows(sym, nm, tr))
    finally:
        C.STOP_ATR = old_stop
    return rows


def single_column_rows(symbols, s0, s1, col):
    if col in OLD_COLS:
        return portfolio_rows(symbols, s0, s1, which=OLD_COLS[col], name=col)
    kw = {"exit_mode": "dual",
          "dual": {**M197.make_dual_spec(), "trig": WIN["trig"], "lock": WIN["lock"]}}
    rows = []
    fn = NEW_COLS[col]
    for sym in symbols:
        df = frames(sym)
        win = df[(df.index >= s0) & (df.index <= s1)]
        if len(win) < 100:
            continue
        _, tr = simulate(win, fn(df).loc[win.index], atr(win), notional=C.TRADE_USD,
                         bar_secs=BAR, **kw)
        rows.extend(trade_rows(sym, col, tr))
    return rows


def always_in_rows(symbols, s0, s1):
    kw = {"exit_mode": "dual",
          "dual": {**M197.make_dual_spec(), "trig": WIN["trig"], "lock": WIN["lock"]}}
    rows = []
    for sym in symbols:
        df = frames(sym)
        win = df[(df.index >= s0) & (df.index <= s1)]
        if len(win) < 100:
            continue
        sg = pd.Series(True, index=win.index)
        _, tr = simulate(win, sg, atr(win), notional=C.TRADE_USD, bar_secs=BAR, **kw)
        rows.extend(trade_rows(sym, "ALWAYS", tr))
    return rows


def buyhold(symbols, s0, s1):
    tot, det = 0.0, []
    for sym in symbols:
        w = frames(sym)
        w = w[(w.index >= s0) & (w.index <= s1)]
        if len(w) < 2:
            continue
        e = float(w["open"].iloc[0]) * (1 + C.COST_PER_SIDE)
        x = float(w["close"].iloc[-1]) * (1 - C.COST_PER_SIDE)
        pnl = C.TRADE_USD * (x / e - 1.0)
        tot += pnl
        det.append({"symbol": sym, "pnl": round(pnl, 4), "ret_pct": round(100 * (x / e - 1), 2)})
    return round(tot, 2), det


# ═══════════════════ حساسية: الخروج على افتتاح الشمعة التالية ═══════════════════
def simulate_next_open(win, sig, atr_s, stop_atr, notional=C.TRADE_USD):
    """نموذج المحرك الحي: لمس الوقف/التتبّع على امتداد شمعة ⇒ تنفيذ على افتتاح التالية."""
    o = win["open"].to_numpy(); h = win["high"].to_numpy()
    l = win["low"].to_numpy(); c = win["close"].to_numpy()
    a = atr_s.to_numpy(); n = len(win); idx = win.index
    sig_i = np.flatnonzero(sig.to_numpy())
    if sig_i.size == 0:
        return []
    trades, busy = [], -1
    for i in sig_i:
        e = i + 1
        if e >= n or not np.isfinite(a[i]) or e <= busy:
            continue
        entry = o[e] * (1 + C.COST_PER_SIDE)
        hard = entry - stop_atr * a[i]
        peak = o[e]
        j = e
        exit_j, px, side = None, None, None
        while j < n:
            eff = hard
            gain = (peak - entry) / entry
            if gain >= WIN["trig"]:
                trail = WIN["wide"] if gain <= 0.01 else WIN["tight"]
                local = peak * (1 - trail)
                if peak >= entry * (1 + WIN["lock"]):
                    local = max(local, entry * (1 + WIN["lock"]))
                eff = max(eff, local)
            if l[j] <= eff:
                k = j + 1
                if k >= n:
                    exit_j, px, side = n - 1, c[-1], "eod"
                else:
                    exit_j, px, side = k, o[k], "stop"       # تنفيذ على افتتاح التالية
                break
            peak = max(peak, h[j])
            j += 1
        if exit_j is None:
            exit_j, px, side = n - 1, c[-1], "eod"
        lo, hi = float(l[exit_j]), float(h[exit_j])
        px = min(max(px, lo), hi)
        fill = px * (1 - C.COST_PER_SIDE)
        trades.append({"symbol": None, "exp": "NX", "entry_time": idx[e].isoformat(),
                       "exit_time": idx[exit_j].isoformat(),
                       "entry": float(f"{entry:.12g}"), "exit": float(f"{fill:.12g}"),
                       "notional": notional,
                       "pnl": round(notional / entry * (fill - entry), 4),
                       "r_mult": "", "exit_side": side, "bars_held": exit_j - e})
        busy = exit_j
    trades.sort(key=lambda p: p["entry_time"])
    return trades


# ═══════════════════ التشغيل ═══════════════════
def main():
    t0 = time.time()
    can = subprocess.run([sys.executable, str(ROOT / "tools" / "canary.py"), "--json"],
                         capture_output=True, text=True)
    cj = json.loads(can.stdout[can.stdout.index("{"):]) if "{" in can.stdout else {}
    print(f"الكاناري بعد الإصلاح: {cj.get('canary')} · net={cj.get('got',{}).get('net')}")
    L36.set_core(); NC.EMA_FAST = 8; M213._cache.clear(); C.STOP_ATR = WIN["stop"]
    cells = R19.breaker_cells() + R19.new_cells()
    syms = sorted({c["symbol"] for c in cells})
    print(f"خلايا: {len(cells)} · عملات: {len(syms)}")
    build_cache(syms)

    WINDOWS = [("الاختيار", DEC_S, DEC_E), ("الحكم", JUD_S, JUD_E)]
    table, trades_dump = [], {}

    # ── المرحلة 3-1: المحفظة (7 أعمدة) ──
    print("\n" + "=" * 80); print("المرحلة 3 · المحفظة الكاملة (7 أعمدة) — الآلة المصلَحة"); print("=" * 80)
    for lbl, s0, s1 in WINDOWS:
        r = portfolio_rows(syms, s0, s1)
        log_measurement("المحفظة (7 أعمدة)", lbl)
        st = summarize(r)
        table.append({"البند": "المحفظة (7 أعمدة)", "الفترة": lbl, **st})
        trades_dump[f"portfolio_{'DEC' if lbl=='الاختيار' else 'JUD'}"] = r
        print(f"  {lbl}: {st}")

    # ── المرحلة 3-2: كل عمود منفردًا ──
    print("\n" + "=" * 80); print("المرحلة 3 · كل عمود منفردًا"); print("=" * 80)
    for col in list(OLD_COLS) + list(NEW_COLS):
        for lbl, s0, s1 in WINDOWS:
            r = single_column_rows(syms, s0, s1, col)
            log_measurement(f"عمود: {col}", lbl)
            st = summarize(r)
            table.append({"البند": f"عمود: {col}", "الفترة": lbl, **st})
            print(f"  {col:22s} {lbl:9s}: {st}")

    # ── المرحلة 3-3: الشراء والاحتفاظ ──
    print("\n" + "=" * 80); print("المرحلة 3 · الضابط 1: الشراء والاحتفاظ"); print("=" * 80)
    for lbl, s0, s1 in WINDOWS:
        tot, det = buyhold(syms, s0, s1)
        log_measurement("الشراء والاحتفاظ", lbl)
        tbl = pd.DataFrame(det)
        tbl.to_csv(OUT / f"buyhold_{'DEC' if lbl=='الاختيار' else 'JUD'}.csv", index=False, encoding="utf-8-sig")
        win_n = int((tbl["pnl"] > 0).sum())
        table.append({"البند": "الضابط: الشراء والاحتفاظ", "الفترة": lbl, "net": tot, "trades": len(det),
                      "pf": None, "per": round(tot / max(len(det), 1), 5), "mdd": None})
        print(f"  {lbl}: {tot}$ · عملات رابحة {win_n}/{len(det)}")

    # ── المرحلة 3-4: الشراء الدائم بقانون الخروج ──
    print("\n" + "=" * 80); print("المرحلة 3 · الضابط 2: الشراء الدائم (إشارة كل شمعة)"); print("=" * 80)
    for lbl, s0, s1 in WINDOWS:
        r = always_in_rows(syms, s0, s1)
        log_measurement("الشراء الدائم بقانون الخروج", lbl)
        st = summarize(r)
        table.append({"البند": "الضابط: الشراء الدائم", "الفترة": lbl, **st})
        trades_dump[f"alwaysin_{'DEC' if lbl=='الاختيار' else 'JUD'}"] = r
        print(f"  {lbl}: {st}")

    pd.DataFrame(table).to_csv(OUT / "phase3_basis_repaired.csv", index=False, encoding="utf-8-sig")

    # ── المرحلة 4: إعادة اختبار قانون الكثرة ──
    print("\n" + "=" * 80); print("المرحلة 4 · قانون الكثرة — تجربتان فقط"); print("=" * 80)
    p4 = []
    flt = lambda win: (win["close"] > win["close"].rolling(200, min_periods=200).mean())
    for lbl, s0, s1 in WINDOWS:
        base = [x for x in table if x["البند"] == "المحفظة (7 أعمدة)" and x["الفترة"] == lbl][0]
        r = portfolio_rows(syms, s0, s1, extra_filter=flt)
        log_measurement("فلتر المتوسط 200", lbl)
        st = summarize(r)
        p4.append({"التجربة": "فلتر المتوسط 200 (لا شراء تحت المتوسط)", "الفترة": lbl, **st,
                   "الفارق_عن_الأساس$": round(st["net"] - base["net"], 2)})
        trades_dump[f"sma200_{'DEC' if lbl=='الاختيار' else 'JUD'}"] = r
        print(f"  فلتر SMA200 {lbl}: {st} (الفارق {st['net'] - base['net']:+.2f}$)")
    for lbl, s0, s1 in WINDOWS:
        base = [x for x in table if x["البند"] == "المحفظة (7 أعمدة)" and x["الفترة"] == lbl][0]
        r = portfolio_rows(syms, s0, s1, stop_atr=2.0)
        log_measurement("تشديد الوقف إلى 2.0×ATR", lbl)
        st = summarize(r)
        p4.append({"التجربة": "تشديد الوقف إلى 2.0×ATR", "الفترة": lbl, **st,
                   "الفارق_عن_الأساس$": round(st["net"] - base["net"], 2)})
        trades_dump[f"stop20_{'DEC' if lbl=='الاختيار' else 'JUD'}"] = r
        print(f"  وقف 2.0×ATR {lbl}: {st} (الفارق {st['net'] - base['net']:+.2f}$)")
    pd.DataFrame(p4).to_csv(OUT / "phase4_abundance_retest.csv", index=False, encoding="utf-8-sig")

    # ── حساسية نموذج التنفيذ (المحرك الحي) ──
    print("\n" + "=" * 80); print("حساسية · نموذج «الخروج على افتتاح الشمعة التالية» (الحكم)"); print("=" * 80)
    r = []
    for sym in syms:
        df = frames(sym)
        win = df[(df.index >= JUD_S) & (df.index <= JUD_E)]
        if len(win) < 100:
            continue
        a_s = atr(win)
        for c in _cells():
            if c["symbol"] != sym:
                continue
            for t in simulate_next_open(win, _lab_signal(df, c).loc[win.index], a_s, WIN["stop"]):
                t["symbol"] = sym; r.append(t)
        for nm, fn in NEW_COLS.items():
            for t in simulate_next_open(win, fn(df).loc[win.index], a_s, WIN["stop"]):
                t["symbol"] = sym; r.append(t)
    log_measurement("حساسية: نموذج تنفيذ المحرك الحي", "الحكم")
    st = summarize(r)
    print(f"  {st}")
    pd.DataFrame([{"القياس": "المحفظة بنموذج المحرك الحي (افتتاح التالية)", "الفترة": "الحكم", **st}]).to_csv(
        OUT / "sensitivity_live_exit_model.csv", index=False, encoding="utf-8-sig")

    # ── ملفات الصفقات (لفحص الحارس) ──
    for k, v in trades_dump.items():
        pd.DataFrame(v).to_csv(OUT / f"trades_{k}.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(r).to_csv(OUT / "trades_livemodel_JUD.csv", index=False, encoding="utf-8-sig")

    # ── سجل السقف + بصمة البيئة ──
    led = pd.DataFrame(LEDGER)
    led.to_csv(OUT / "attempt_ledger.csv", index=False, encoding="utf-8-sig")
    (OUT / "env_dump.txt").write_text(
        f"python={platform.python_version()}\npandas={pd.__version__}\npyarrow=25.0.1\n"
        f"engine=REPAIRED (common.py, L0046)\ncanary_field={cj.get('canary')}\n"
        f"canary_net={cj.get('got',{}).get('net')}\n"
        f"decision={DEC_S}→{DEC_E}\njudgement={JUD_S}→{JUD_E}\n"
        f"exit_law=stop{WIN['stop']}xATR/trig{WIN['trig']}/lock{WIN['lock']}/wide{WIN['wide']}/tight{WIN['tight']}\n"
        f"ema_fast=8\ncore=body0.40/range0.60/look10\ntriggers=ALL14\n"
        f"basket={len(syms)} symbols\nnotional=20$\ncost=0.13%/side\n"
        f"declared_cap={CAP}\nused={len(LEDGER)}\n", encoding="utf-8")
    print(f"\n→ {OUT}\nالسقف: {len(LEDGER)}/{CAP}\nالزمن: {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
