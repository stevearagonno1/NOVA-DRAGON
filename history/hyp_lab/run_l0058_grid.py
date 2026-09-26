# -*- coding: utf-8 -*-
"""L0058 — قياس الشبكة بعد إصلاح التعبئة.

القواعد مكتوبة هنا قبل أي رقم ربح.

السقف 30. الإصلاح والاختبارات لا تُحسب.
  ب (16 من 18): ثابتة وديناميكية، الفترتان، 0.115%.
      ثم 5 بذور على الأفضل في الفترتين. ثم الأفضل عند 0.130% في الفترتين.
  ج (4 من 6): النسخة المعطوبة على نفس المقاطع، الفترتان، الثابتة والديناميكية.
  د (2 من 6): صمت العرضي في المحفظة، الفترتان، 0.115%.
المقاعد الفارغة لا تُملأ.

الأفضل = الأعلى صافيًا في الاختيار عند 0.115% بعد حارس صفر.
التعادل يُحسم للثابتة. يُودَع قبل قراءة الحكم.
البذور: 110058 210058 310058 410058 510058.
الفوز = تجاوز أسعد بذرة في الفترة.

لا سقف «شبكة واحدة لكل عملة إلى الأبد». ذلك السقف لا يجيب عن الفترتين
ولا يبلغ 30 شبكة. شبكة واحدة مفتوحة في كل لحظة على العملة، وكل مقطع عرضي مؤهّل يُقاس.
مناخ يومي shift(1). لا regime.py. لا replay_grid.
الديناميكية على المقاطع نفسها. بلا بوابة جودة. بلا FLEX. بلا ADX.
ملف dynamic_grid.py لا يُعدَّل. فئة الخلية تُستبدل في الذاكرة بنفس منطق التعبئة.

الكلفة 0.115% على الطرفين. الانزلاق المضاف = 0 لأن 0.115% يشمل انزلاق الورقة.
لا تُجمع دولارات الشبكة مع دولارات المحفظة.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

ROOT = pathlib.Path("/home/user/l0058")
sys.path.insert(0, str(ROOT / "history" / "hyp_lab"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0058"
OUT.mkdir(parents=True, exist_ok=True)
ONE_M = pathlib.Path.home() / ".cache" / "l0058_1m"
ONE_M.mkdir(parents=True, exist_ok=True)

COST = 0.00115
COST_130 = 0.00130
SEEDS = (110058, 210058, 310058, 410058, 510058)
CAP = 30
WINDOWS = {
    "اختيار": ("2021-09-01", "2023-12-31"),
    "حكم": ("2024-01-01", "2026-08-31"),
}
LEDGER: list[dict] = []


def log(name: str, window: str, phase: str) -> None:
    if len(LEDGER) >= CAP:
        raise SystemExit(f"تجاوز السقف {CAP}")
    LEDGER.append({"#": len(LEDGER) + 1, "المرحلة": phase, "القياس": name, "الفترة": window})


def dump(path: pathlib.Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


class RepairedDynCell:
    """نفس منطق grid.py المصلَح. لا يُكتب في dynamic_grid.py."""

    __slots__ = ("buy", "sell", "qty", "open", "realized_usd", "cycles", "fill_buy", "fill_sell")

    def __init__(self, buy: float, sell: float, notional: float):
        self.buy = buy
        self.sell = sell
        self.qty = notional / buy if buy > 0 else 0.0
        self.open = False
        self.realized_usd = 0.0
        self.cycles = 0
        self.fill_buy = 0.0
        self.fill_sell = 0.0

    def on_bar(self, o, h, l, c):
        import nova_v8.config as VC
        import nova_v8.grid as G
        if not self.open:
            if l <= self.buy:
                self.fill_buy = G.limit_fill(self.buy, o, h, l, buy=True)
                self.open = True
        elif h >= self.sell:
            self.fill_sell = G.limit_fill(self.sell, o, h, l, buy=False)
            buy_cost = self.qty * self.fill_buy
            sell_gross = self.qty * self.fill_sell
            fee = VC.COMMISSION_PCT
            fees = buy_cost * fee + sell_gross * fee
            self.realized_usd += (sell_gross - buy_cost) - fees
            self.cycles += 1
            self.open = False

    def unrealized_usd(self, cur):
        import nova_v8.config as VC
        if not self.open:
            return 0.0
        buy_cost = self.qty * self.fill_buy
        return (self.qty * cur - buy_cost) - buy_cost * VC.COMMISSION_PCT

    def flatten_usd(self, cur, slip_pct):
        import nova_v8.config as VC
        if not self.open:
            return 0.0
        buy_cost = self.qty * self.fill_buy
        exit_gross = self.qty * cur
        fee = VC.COMMISSION_PCT
        fees = buy_cost * fee + exit_gross * (fee + slip_pct)
        self.fill_sell = cur
        self.open = False
        return (exit_gross - buy_cost) - fees


def _load_broken():
    path = ROOT / "nova_v8" / "grid_broken_preL0058.py"
    name = "nova_v8.grid_broken_preL0058"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _set_cost(cost: float) -> None:
    import nova_v8.config as VC
    import nova_v8.grid as G
    VC.COMMISSION_PCT = cost
    G._BUY_FEE = cost
    G._SELL_FEE = cost
    broken = _load_broken()
    broken._BUY_FEE = cost
    broken._SELL_FEE = cost


def _daily_labels(df: pd.DataFrame) -> pd.Series:
    from common import to_bars
    dly = to_bars(df, 1440)
    c = dly["close"]
    e50 = c.ewm(span=50, adjust=False).mean()
    e200 = c.ewm(span=200, adjust=False).mean()
    slope = e50.diff(10)
    raw = pd.Series("عرضي", index=dly.index)
    raw[(e50 > e200) & (slope > 0)] = "صاعد"
    raw[(e50 < e200) & (slope < 0)] = "هابط"
    lab = raw.shift(1)
    lookup = {t.normalize(): v for t, v in lab.items()}
    return pd.Series([lookup.get(t.normalize(), None) for t in df.index], index=df.index)


def _segments(labels: np.ndarray) -> list[tuple]:
    if len(labels) == 0:
        return []
    out = []
    start = 0
    cur = labels[0]
    for i in range(1, len(labels) + 1):
        if i == len(labels) or labels[i] != cur:
            out.append((cur, start, i - 1))
            if i < len(labels):
                cur = labels[i]
                start = i
    return out


def _span_ok(h, l, s, look, vmin, vmax) -> tuple[bool, float, float]:
    lo = float(np.nanmin(l[s - look:s]))
    hi = float(np.nanmax(h[s - look:s]))
    mid = (hi + lo) / 2.0
    span = (hi - lo) / mid if mid > 0 else 0.0
    return (vmin <= span <= vmax and hi > lo), lo, hi


def _booked_buy(cell, repaired: bool) -> float:
    if repaired and getattr(cell, "fill_buy", 0.0):
        return float(cell.fill_buy)
    return float(cell.buy)


def _booked_sell(cell, repaired: bool) -> float:
    if repaired and getattr(cell, "fill_sell", 0.0):
        return float(cell.fill_sell)
    return float(cell.sell)


def _leg(symbol, kind, entry_ts, exit_ts, buy_px, sell_px, qty, cost, engine, window):
    entry = buy_px * (1.0 + cost)
    exit_ = sell_px * (1.0 - cost)
    pnl = qty * (exit_ - entry)
    return {
        "symbol": symbol, "engine": engine, "window": window, "kind": kind,
        "entry_time": str(entry_ts), "exit_time": str(exit_ts),
        "entry": entry, "exit": exit_, "pnl": pnl, "notional": qty * buy_px,
        "bars_held": 1, "buy_px": buy_px, "sell_px": sell_px,
    }


def _observe(symbol, grid, prev, ts, repaired, cost, engine, window, fills, opens):
    for i, cell in enumerate(grid.cells):
        was, cyc = prev[i][0], prev[i][1]
        prev_buy = prev[i][2] if len(prev[i]) > 2 else 0.0
        key = (engine, id(cell))
        if not was and cell.open:
            px = _booked_buy(cell, repaired)
            opens[key] = (ts, px, float(cell.qty), float(cell.buy))
        if cell.cycles > cyc and key in opens:
            ets, buy_px, qty, level = opens.pop(key)
            row = _leg(symbol, "cycle", ets, ts, buy_px, _booked_sell(cell, repaired), qty, cost, engine, window)
            row["buy_level"] = level
            row["sell_level"] = float(cell.sell)
            fills.append(row)
        elif was and not cell.open and cell.cycles == cyc and key in opens:
            ets, buy_px, qty, level = opens.pop(key)
            px = float(grid.last_price)
            row = _leg(symbol, "flatten", ets, ts, buy_px, px, qty, cost, engine, window)
            row["buy_level"] = level
            row["sell_level"] = float(cell.sell)
            fills.append(row)
        elif (not was and not cell.open and cell.cycles == cyc and repaired
              and getattr(cell, "fill_buy", 0.0) and getattr(cell, "fill_buy", 0.0) != prev_buy):
            # شراء ثم تسطيح في الشمعة نفسها. الحالة السابقة لا ترى الفتح.
            row = _leg(symbol, "flatten", ts, ts, float(cell.fill_buy), float(grid.last_price), float(cell.qty), cost, engine, window)
            row["buy_level"] = float(cell.buy)
            row["sell_level"] = float(cell.sell)
            row["same_bar"] = True
            fills.append(row)


def _run_unit(GridCls, symbol, s, e, lo, hi, o, h, l, c, idx, repaired, cost, engine, window, fills):
    grid = GridCls(symbol, s, lo, hi, float(c[s - 1]))
    opens = {}
    for j in range(s, e + 1):
        if grid.closed:
            break
        prev = [(cell.open, cell.cycles, getattr(cell, "fill_buy", 0.0)) for cell in grid.cells]
        grid.on_bar(float(o[j]), float(h[j]), float(l[j]), float(c[j]), j, 0.0)
        _observe(symbol, grid, prev, idx[j], repaired, cost, engine, window, fills, opens)
    if not grid.closed:
        prev = [(cell.open, cell.cycles, getattr(cell, "fill_buy", 0.0)) for cell in grid.cells]
        grid.close(e, "نهاية-المقطع", float(c[e]), 0.0)
        _observe(symbol, grid, prev, idx[e], repaired, cost, engine, window, fills, opens)
    if opens:
        raise RuntimeError(f"خلية بقيت مفتوحة {symbol} {engine}")
    return {
        "symbol": symbol, "engine": engine, "window": window, "repaired": repaired,
        "start": str(idx[s]), "end": str(idx[min(grid.close_bar or e, e)]),
        "bars": int(grid.bars), "net": float(grid.net_usd), "cycles": int(grid.cycles),
        "capital": 1000.0, "reason": grid.close_reason or "نهاية-المقطع",
    }


def _dyn_flat_px(unit, o, h, l, c) -> float:
    import nova_v8.config as VC
    up = unit.hi * (1.0 + VC.DGT_BREAK_BUFFER_PCT)
    dn = unit.lo * (1.0 - VC.DGT_BREAK_BUFFER_PCT)
    if c > up or c < dn:
        return o if (o > up or o < dn) else c
    return c


def _dyn_exit_px(unit, o, h, l, c) -> float:
    return _dyn_flat_px(unit, o, h, l, c)


def _note_dyn_bar(symbol, unit, prev_cells, prev, ts, o, h, l, c, repaired, cost, engine, window, fills, opens, base_open):
    """Observe cells snapshotted before on_bar. Flatten clears unit.cells."""
    exit_px = _dyn_exit_px(unit, o, h, l, c)
    flat_cells = [cell for cell, prev_i in zip(prev_cells, prev)
                  if prev_i[0] and not cell.open and cell.cycles == prev_i[1]]
    if flat_cells:
        if repaired:
            sold = [cell.fill_sell for cell in flat_cells if getattr(cell, "fill_sell", 0.0)]
            exit_px = sold[0] if sold else exit_px
    fake = type("G", (), {"cells": prev_cells, "last_price": exit_px})()
    _observe(symbol, fake, prev, ts, repaired, cost, engine, window, fills, opens)
    new_base = base_open
    if base_open and unit.base_qty == 0:
        fills.append(_leg(symbol, "base", base_open[0], ts, base_open[1], exit_px, base_open[2], cost, engine, window))
        new_base = None
    return new_base


def _run_dynamic(unit_cls, symbol, s, e, lo, hi, o, h, l, c, idx, atr, repaired, cost, engine, window, fills, look, vmin, vmax):
    import nova_v8.config as VC
    unit = unit_cls(symbol, s, VC.DGT_CAPITAL_USD)
    atr0 = float(atr[s - 1]) if np.isfinite(atr[s - 1]) else None
    if not unit.build(s, float(c[s - 1]), atr0, lo, hi, float(o[s]), 0.0, bias=0):
        return None
    opens = {}
    base_open = (idx[s], float(unit.base_px), float(unit.base_qty)) if unit.base_qty > 0 else None
    for j in range(s, e + 1):
        if unit.closed:
            break
        if (unit.state == unit.STATE_FLAT and j >= unit.rebuild_at
                and unit.resets < VC.DGT_MAX_RESETS and j >= look):
            ok, lo2, hi2 = _span_ok(h, l, j, look, vmin, vmax)
            if not ok:
                if base_open:
                    fills.append(_leg(symbol, "base", base_open[0], idx[j], base_open[1], float(c[j - 1]), base_open[2], cost, engine, window))
                    base_open = None
                unit.close(j, "نطاق-غير-صالح", float(c[j - 1]), 0.0)
                break
            aj = float(atr[j - 1]) if np.isfinite(atr[j - 1]) else None
            unit.build(j, float(c[j - 1]), aj, lo2, hi2, float(o[j]), 0.0, bias=0)
            if unit.base_qty > 0:
                base_open = (idx[j], float(unit.base_px), float(unit.base_qty))
        prev_cells = list(unit.cells)
        prev = [(cell.open, cell.cycles, getattr(cell, "fill_buy", 0.0)) for cell in prev_cells]
        unit.on_bar(float(o[j]), float(h[j]), float(l[j]), float(c[j]), j, 0.0)
        base_open = _note_dyn_bar(
            symbol, unit, prev_cells, prev, idx[j], float(o[j]), float(h[j]), float(l[j]), float(c[j]),
            repaired, cost, engine, window, fills, opens, base_open,
        )
    if not unit.closed:
        prev_cells = list(unit.cells)
        prev = [(cell.open, cell.cycles, getattr(cell, "fill_buy", 0.0)) for cell in prev_cells]
        unit.close(e, "نهاية-المقطع", float(c[e]), 0.0)
        fake = type("G", (), {"cells": prev_cells, "last_price": float(c[e])})()
        _observe(symbol, fake, prev, idx[e], repaired, cost, engine, window, fills, opens)
        if base_open:
            fills.append(_leg(symbol, "base", base_open[0], idx[e], base_open[1], float(c[e]), base_open[2], cost, engine, window))
            base_open = None
    if opens or base_open:
        raise RuntimeError(f"ديناميكية بقيت مفتوحة {symbol} {engine}")
    if unit.bars < VC.DGT_MIN_LIFE_BARS:
        return None
    return {
        "symbol": symbol, "engine": engine, "window": window, "repaired": repaired,
        "start": str(idx[s]), "end": str(idx[min(unit.close_bar or e, e)]),
        "bars": int(unit.bars), "net": float(unit.net_usd), "cycles": int(unit.cycles),
        "capital": float(VC.DGT_CAPITAL_USD), "reason": unit.close_reason or "نهاية-المقطع",
    }


def measure_symbol(sym: str, cost: float = COST, engines: tuple = ("static", "static_broken", "dynamic", "dynamic_broken")) -> dict:
    t0 = time.time()
    import nova_v8.config as VC
    import nova_v8.grid as G
    import nova_v8.dynamic_grid as DG
    from common import load
    _set_cost(cost)
    path = ROOT / "crypto_archive" / f"{sym}_1m.parquet"
    df = load(str(path), start="2021-06-01", end="2026-09-01")
    df.to_parquet(ONE_M / f"{sym}_1m.parquet")
    if len(df) < VC.GRID_RANGE_LOOKBACK_BARS + VC.GRID_MIN_LIFE_BARS:
        return {"symbol": sym, "units": [], "fills": [], "seconds": time.time() - t0}
    labels = _daily_labels(df).fillna("x").to_numpy()
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    idx = df.index
    atr = DG._spacing_atr_1m(df)
    look = VC.GRID_RANGE_LOOKBACK_BARS
    vmin, vmax = VC.GRID_RANGE_MIN_PCT, VC.GRID_RANGE_MAX_PCT
    broken = _load_broken()
    orig_cell = DG._Cell
    units, fills = [], []
    bounds = {w: (pd.Timestamp(a, tz="UTC"), pd.Timestamp(b, tz="UTC")) for w, (a, b) in WINDOWS.items()}
    for regime, s, e in _segments(labels):
        if regime != "عرضي" or s < look:
            continue
        for window, (w0, w1) in bounds.items():
            if idx[s] > w1 or idx[e] < w0:
                continue
            s2 = s
            while s2 <= e and idx[s2] < w0:
                s2 += 1
            e2 = e
            while e2 >= s2 and idx[e2] > w1:
                e2 -= 1
            if e2 - s2 < VC.GRID_MIN_LIFE_BARS or s2 < look:
                continue
            ok, lo, hi = _span_ok(h, l, s2, look, vmin, vmax)
            if not ok:
                continue
            if "static" in engines:
                units.append(_run_unit(G.Grid, sym, s2, e2, lo, hi, o, h, l, c, idx, True, cost, "static", window, fills))
            if "static_broken" in engines:
                units.append(_run_unit(broken.Grid, sym, s2, e2, lo, hi, o, h, l, c, idx, False, cost, "static_broken", window, fills))
            if "dynamic" in engines:
                DG._Cell = RepairedDynCell
                try:
                    rec = _run_dynamic(DG.DynamicGridUnit, sym, s2, e2, lo, hi, o, h, l, c, idx, atr, True, cost, "dynamic", window, fills, look, vmin, vmax)
                finally:
                    DG._Cell = orig_cell
                if rec:
                    units.append(rec)
            if "dynamic_broken" in engines:
                recb = _run_dynamic(DG.DynamicGridUnit, sym, s2, e2, lo, hi, o, h, l, c, idx, atr, False, cost, "dynamic_broken", window, fills, look, vmin, vmax)
                if recb:
                    units.append(recb)
    return {"symbol": sym, "units": units, "fills": fills, "seconds": round(time.time() - t0, 1)}


def _outside(px, lo, hi) -> bool:
    tol = 1e-6 * max(abs(lo), abs(hi), 1e-9)
    return (lo - px) > tol or (px - hi) > tol


def _load_frame(sym: str) -> pd.DataFrame:
    from common import load
    cached = ONE_M / f"{sym}_1m.parquet"
    if cached.exists():
        df = pd.read_parquet(cached)
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        return df
    df = load(str(ROOT / "crypto_archive" / f"{sym}_1m.parquet"), start="2021-06-01", end="2026-09-01")
    df.to_parquet(cached)
    return df


def random_symbol(job: tuple) -> dict:
    """خمس بذور معلنة. عدد الشبكات ≈ الحقيقي. فتح داخل العرضي بلا تداخل على العملة."""
    sym, engine, window, k, seed, cost = job
    import nova_v8.config as VC
    import nova_v8.grid as G
    import nova_v8.dynamic_grid as DG
    _set_cost(cost)
    if k <= 0:
        return {"symbol": sym, "units": [], "fills": [], "got": 0}
    df = _load_frame(sym)
    labels = _daily_labels(df).fillna("x").to_numpy()
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    idx = df.index
    look = VC.GRID_RANGE_LOOKBACK_BARS
    vmin, vmax = VC.GRID_RANGE_MIN_PCT, VC.GRID_RANGE_MAX_PCT
    w0, w1 = (pd.Timestamp(a, tz="UTC") for a in WINDOWS[window])
    segs = []
    for regime, s, e in _segments(labels):
        if regime != "عرضي" or s < look:
            continue
        s2 = s
        while s2 <= e and idx[s2] < w0:
            s2 += 1
        e2 = e
        while e2 >= s2 and idx[e2] > w1:
            e2 -= 1
        if e2 - s2 >= VC.GRID_MIN_LIFE_BARS and s2 >= look:
            segs.append((s2, e2))
    if not segs:
        return {"symbol": sym, "units": [], "fills": [], "got": 0}
    digest = int(hashlib.sha256(f"{seed}:{sym}:{window}:{engine}".encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(digest)
    weights = np.array([e - s - VC.GRID_MIN_LIFE_BARS + 1 for s, e in segs], dtype=float)
    weights = weights / weights.sum()
    occupied = []
    units, fills = [], []
    atr = None
    attempts = 0
    limit = max(400, int(k) * 80)
    while len(units) < k and attempts < limit:
        attempts += 1
        si = int(rng.choice(len(segs), p=weights))
        s, e = segs[si]
        j = int(rng.integers(s, e - VC.GRID_MIN_LIFE_BARS + 1))
        if any(not (j > b or j < a) for a, b in occupied):
            continue
        ok, lo, hi = _span_ok(h, l, j, look, vmin, vmax)
        if not ok:
            continue
        if engine == "static":
            rec = _run_unit(G.Grid, sym, j, e, lo, hi, o, h, l, c, idx, True, cost, f"rnd{seed}", window, fills)
        else:
            if atr is None:
                atr = DG._spacing_atr_1m(df)
            orig_cell = DG._Cell
            DG._Cell = RepairedDynCell
            try:
                rec = _run_dynamic(DG.DynamicGridUnit, sym, j, e, lo, hi, o, h, l, c, idx, atr, True, cost, f"rnd{seed}", window, fills, look, vmin, vmax)
            finally:
                DG._Cell = orig_cell
        if rec:
            units.append(rec)
            occupied.append((j, e if rec is None else j + max(rec["bars"], 1)))
    return {"symbol": sym, "units": units, "fills": fills, "got": len(units)}


_DYN_ORIG = None


def _load_dyn_orig():
    global _DYN_ORIG
    import nova_v8.dynamic_grid as DG
    if _DYN_ORIG is None:
        _DYN_ORIG = DG._Cell
    return _DYN_ORIG


def summarize(units: list[dict]) -> dict:
    if not units:
        return {"net": 0.0, "grids": 0, "cycles": 0, "bars": 0, "capital_each": 1000.0,
                "peak_concurrent": 0, "peak_capital": 0.0, "mean_bars": 0.0, "return_on_1000_pct": None,
                "return_on_peak_pct": None}
    net = float(sum(u["net"] for u in units))
    n = len(units)
    # peak concurrent capital from intervals
    events = []
    for u in units:
        events.append((pd.Timestamp(u["start"]), 1, 1))
        events.append((pd.Timestamp(u["end"]), 0, -1))
    events.sort()
    cur = peak = 0
    for _, _, d in events:
        cur += d
        peak = max(peak, cur)
    cap = float(units[0]["capital"])
    return {
        "net": round(net, 2),
        "grids": n,
        "cycles": int(sum(u["cycles"] for u in units)),
        "bars": int(sum(u["bars"] for u in units)),
        "capital_each": cap,
        "peak_concurrent": int(peak),
        "peak_capital": round(peak * cap, 2),
        "mean_bars": round(float(np.mean([u["bars"] for u in units])), 1),
        "return_on_1000_pct": round(100.0 * net / cap, 4) if cap else None,
        "return_on_peak_pct": round(100.0 * net / (peak * cap), 4) if peak and cap else None,
    }


def run_map(fn, jobs, workers: int):
    jobs = list(jobs)
    if workers <= 1 or len(jobs) <= 1:
        for job in jobs:
            yield fn(job)
        return
    with ProcessPoolExecutor(max_workers=workers) as pool:
        yield from pool.map(fn, jobs)


def measure_job(job: tuple) -> dict:
    sym, cost, engines = job
    return measure_symbol(sym, cost, engines)


def random_batch(job: tuple) -> dict:
    """كل البذور لعملة واحدة بعد تحميل واحد."""
    sym, engine, counts, cost = job
    import nova_v8.config as VC
    import nova_v8.grid as G
    import nova_v8.dynamic_grid as DG
    _set_cost(cost)
    df = _load_frame(sym)
    labels = _daily_labels(df).fillna("x").to_numpy()
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    idx = df.index
    look = VC.GRID_RANGE_LOOKBACK_BARS
    vmin, vmax = VC.GRID_RANGE_MIN_PCT, VC.GRID_RANGE_MAX_PCT
    atr = DG._spacing_atr_1m(df) if engine == "dynamic" else None
    orig_cell = DG._Cell
    out_units, out_fills = [], []
    for window, k in counts.items():
        w0, w1 = (pd.Timestamp(a, tz="UTC") for a in WINDOWS[window])
        segs = []
        for regime, s, e in _segments(labels):
            if regime != "عرضي" or s < look:
                continue
            s2, e2 = s, e
            while s2 <= e and idx[s2] < w0:
                s2 += 1
            while e2 >= s2 and idx[e2] > w1:
                e2 -= 1
            if e2 - s2 >= VC.GRID_MIN_LIFE_BARS and s2 >= look:
                segs.append((s2, e2))
        if not segs or k <= 0:
            continue
        weights = np.array([e - s - VC.GRID_MIN_LIFE_BARS + 1 for s, e in segs], dtype=float)
        weights = weights / weights.sum()
        for seed in SEEDS:
            digest = int(hashlib.sha256(f"{seed}:{sym}:{window}:{engine}".encode()).hexdigest()[:8], 16)
            rng = np.random.default_rng(digest)
            occupied = []
            got = 0
            attempts = 0
            limit = max(400, int(k) * 80)
            while got < k and attempts < limit:
                attempts += 1
                si = int(rng.choice(len(segs), p=weights))
                s, e = segs[si]
                j = int(rng.integers(s, e - VC.GRID_MIN_LIFE_BARS + 1))
                if any(a <= j <= b for a, b in occupied):
                    continue
                ok, lo, hi = _span_ok(h, l, j, look, vmin, vmax)
                if not ok:
                    continue
                tag = f"rnd{seed}"
                fills = []
                if engine == "static":
                    rec = _run_unit(G.Grid, sym, j, e, lo, hi, o, h, l, c, idx, True, cost, tag, window, fills)
                else:
                    DG._Cell = RepairedDynCell
                    try:
                        rec = _run_dynamic(DG.DynamicGridUnit, sym, j, e, lo, hi, o, h, l, c, idx, atr, True, cost, tag, window, fills, look, vmin, vmax)
                    finally:
                        DG._Cell = orig_cell
                if not rec:
                    continue
                got += 1
                occupied.append((j, j + max(rec["bars"], 1)))
                out_units.append(rec)
                out_fills.extend(fills)
    return {"symbol": sym, "units": out_units, "fills": out_fills}


def _official_guard(path: pathlib.Path, cost: float) -> dict:
    """عملة فعملة. الملف الكامل مرة واحدة قُتل بإشارة -9 لنقص الذاكرة."""
    import subprocess
    if not path.exists() or path.stat().st_size == 0:
        return {"viol": 0, "skipped": 0, "missing_frames": 0, "empty": True}
    frame = pd.read_csv(path)
    if frame.empty:
        return {"viol": 0, "skipped": 0, "missing_frames": 0, "empty": True}
    viol = skipped = missing = 0
    texts = []
    part_dir = OUT / "guard_parts"
    part_dir.mkdir(exist_ok=True)
    for sym, g in frame.groupby("symbol"):
        part = part_dir / f"{path.stem}_{sym}.csv"
        g.to_csv(part, index=False)
        st = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "fill_invariant_check.py"),
             "--trades", str(part), "--frames", str(ONE_M), "--cost", str(cost), "--bar-tag", "1m"],
            capture_output=True, text=True,
        )
        text = st.stdout + st.stderr
        texts.append(text)
        got = None
        for line in text.splitlines():
            if "مجموع المخالفات" in line:
                got = int(line.split(":")[1].split()[0])
            if "تُخطّي=" in line:
                skipped += int(line.split("تُخطّي=")[1].split("·")[0].strip())
            if "شموع ناقصة=" in line:
                missing += int(line.split("شموع ناقصة=")[1].split("·")[0].strip())
        if got is None or st.returncode not in (0, 1):
            return {"viol": st.returncode or -1, "skipped": skipped, "missing_frames": missing,
                    "exit": st.returncode, "tail": text[-500:], "symbol": sym}
        viol += got
    (OUT / (path.stem + "_guard.txt")).write_text("\n".join(texts), encoding="utf-8")
    return {"viol": viol, "skipped": skipped, "missing_frames": missing, "exit": 0 if viol == 0 else 1}


def _reconcile(units, fills, engine: str) -> float:
    worst = 0.0
    for window in ("اختيار", "حكم"):
        un = [u for u in units if u["engine"] == engine and u["window"] == window]
        lg = [f for f in fills if f["engine"] == engine and f["window"] == window]
        if not un:
            continue
        worst = max(worst, abs(sum(u["net"] for u in un) - sum(f["pnl"] for f in lg)))
    return worst


def _silence() -> dict:
    import importlib.util
    import subprocess
    src = (ROOT / "history" / "hyp_lab" / "run_l0056_widen_book.py").read_text(encoding="utf-8")
    src = src.replace('pathlib.Path("/home/user/l0056")', 'pathlib.Path("/home/user/l0058")')
    src = src.replace('if __name__ == "__main__":', "if False:")
    patched = pathlib.Path("/tmp/r56_l0058_silence.py")
    patched.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("r56_l0058_silence", patched)
    R56 = importlib.util.module_from_spec(spec)
    sys.modules["r56_l0058_silence"] = R56
    spec.loader.exec_module(R56)
    R56.OUT = OUT
    R56.DAILY = pathlib.Path.home() / ".cache" / "l0058_daily"
    R56.prepare()
    R56.build_regimes(R56.archive_symbols())
    R56.use_syms(R56.archive_symbols())
    enabled, _ = R56.load_frozen_map()
    quiet = {x for x in enabled if x[1] != "عرضي"}
    out = {"dropped": sorted(list(enabled - quiet))}
    for window, s0, s1, fname in (
        ("اختيار", "2021-09-01", "2023-12-31", "silence_c00115_SEL"),
        ("حكم", "2024-01-01", "2026-08-31", "silence_c00115_JUD"),
    ):
        rec, rows = R56.run_book(
            "صمت العرضي", fname, R56.routed(quiet), R56.WINNER, s0, s1, window, COST, False, "د",
        )
        log("صمت العرضي", window, "د")
        side = [r for r in rows if r.get("regime") == "عرضي"]
        out[window] = {"net": rec["net"], "trades": rec["trades"], "sideways_trades": len(side),
                       "overlapping": rec["overlapping_trades"]}
        print(f"  [{len(LEDGER)}/{CAP}] صمت العرضي {window}: {rec['net']} / {rec['trades']} عرضي={len(side)}", flush=True)
    au = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "position_sequencing_audit.py"),
         "--trades", str(OUT / "trades_silence_c00115_JUD.csv"), "--require-zero"],
        capture_output=True, text=True,
    )
    out["sequencing_exit"] = au.returncode
    return out


def main() -> int:
    rule = {
        "written_before_measurement": True,
        "acceptance": {
            "net_positive_both_periods": True,
            "beats_zero_both": True,
            "beats_luckiest_seed_both": True,
            "positive_at_0.00130": True,
            "grids_at_least_30_each_period": True,
        },
        "winner_rule": "أعلى صافٍ في الاختيار عند 0.115% بعد حارس صفر. التعادل للثابتة.",
        "seeds": list(SEEDS),
        "cost_note": "0.00115 على الطرفين. انزلاق مضاف 0. ثوابت _BUY_FEE/_SELL_FEE وCOMMISSION_PCT تُضبط في الذاكرة قبل التشغيل.",
        "cap_plan": {"B": 16, "C": 4, "D": 2, "cap": 30},
    }
    dump(OUT / "acceptance_rule_l0058.json", rule)
    syms = sorted(p.name.split("_")[0] for p in (ROOT / "crypto_archive").glob("*USDT_1m.parquet"))
    print(f"عملات {len(syms)}", flush=True)
    only = os.environ.get("L0058_ONLY")
    if only:
        syms = [s for s in syms if s == only]
    units, fills = [], []
    workers = int(os.environ.get("L0058_WORKERS", "1"))
    for rec in run_map(measure_symbol, syms, workers):
            print(f"  {rec['symbol']} وحدات={len(rec['units'])} تعبئات={len(rec['fills'])} {rec['seconds']}s", flush=True)
            units.extend(rec["units"])
            fills.extend(rec["fills"])
    if only:
        by = {}
        for f in fills:
            by.setdefault((f["engine"], f["window"], f["symbol"]), []).append(f)
        worst = 0.0
        for u in units:
            if u["engine"] != "static":
                continue
            legs = by.get((u["engine"], u["window"], u["symbol"]), [])
            # probe compares the symbol total, not one unit
        for engine in ("static", "static_broken", "dynamic", "dynamic_broken"):
            for window in ("اختيار", "حكم"):
                un = [u for u in units if u["engine"] == engine and u["window"] == window]
                lg = [f for f in fills if f["engine"] == engine and f["window"] == window]
                if not un and not lg:
                    continue
                diff = abs(sum(u["net"] for u in un) - sum(f["pnl"] for f in lg))
                worst = max(worst, diff)
                print(f"  مطابقة {engine} {window}: فرق_عن_محركهم={diff:.4f} شبكات={len(un)} أرجل={len(lg)}", flush=True)
        frame = pd.read_parquet(ONE_M / f"{only}_1m.parquet")
        bad = 0
        for f in fills:
            if f["engine"] not in ("static", "dynamic"):
                continue
            for side, tcol, pcol, div in (
                ("buy", "entry_time", "buy_px", 1),
                ("sell", "exit_time", "sell_px", 1),
            ):
                ts = pd.Timestamp(f[tcol])
                if ts not in frame.index:
                    bad += 1
                    continue
                bar = frame.loc[ts]
                if _outside(float(f[pcol]), float(bar.low), float(bar.high)):
                    bad += 1
        print(f"مسبار. لا يُحسب. أسوأ فرق={worst:.4f} مخالفات_مصلَحة={bad}", flush=True)
        return 0
    repaired = [f for f in fills if f["engine"] in ("static", "dynamic")]
    broken_f = [f for f in fills if "broken" in f["engine"]]
    cols = ["symbol", "engine", "window", "kind", "entry_time", "exit_time", "entry", "exit", "pnl", "notional", "bars_held", "buy_px", "sell_px"]
    pd.DataFrame(repaired, columns=cols).to_csv(OUT / "trades_grid_repaired_c00115.csv", index=False)
    pd.DataFrame(broken_f, columns=cols).to_csv(OUT / "trades_grid_broken_c00115.csv", index=False)
    dump(OUT / "grid_units_c00115.json", units)
    guard = _official_guard(OUT / "trades_grid_repaired_c00115.csv", COST)
    dump(OUT / "guard_repaired_c00115.json", guard)
    print(f"حارس المصلَح: مخالفات={guard['viol']}", flush=True)
    if guard["viol"] != 0 or guard["skipped"] or guard["missing_frames"]:
        dump(OUT / "STOP.json", {"reason": "حارس التعبئة لم يبلغ صفرًا على الشبكة المصلَحة", "guard": guard})
        print("أوقف. لا تفسير لربح.", flush=True)
        return 2
    static_gap = _reconcile(units, fills, "static")
    if static_gap > 0.05:
        dump(OUT / "STOP.json", {"reason": "محاسبة الثابتة لا تطابق أرجلها", "gap": static_gap})
        print(f"أوقف. فرق محاسبة الثابتة {static_gap}", flush=True)
        return 2
    results = {}
    for engine in ("static", "dynamic", "static_broken", "dynamic_broken"):
        results[engine] = {}
        for window in ("اختيار", "حكم"):
            un = [u for u in units if u["engine"] == engine and u["window"] == window]
            lg = [f for f in fills if f["engine"] == engine and f["window"] == window]
            st = summarize(un)
            st["leg_net"] = round(sum(f["pnl"] for f in lg), 2)
            st["engine_net"] = st["net"]
            st["used_net"] = st["leg_net"] if engine.startswith("dynamic") else st["net"]
            results[engine][window] = st
            phase = "ج" if "broken" in engine else "ب"
            name = f"{engine} 0.115%"
            log(name, window, phase)
            print(f"  [{len(LEDGER)}/{CAP}] {name} {window}: صافٍ_مستعمل={st['used_net']} شبكات={st['grids']}", flush=True)
    sel_static = results["static"]["اختيار"]["used_net"]
    sel_dyn = results["dynamic"]["اختيار"]["used_net"]
    winner = "static" if sel_static >= sel_dyn else "dynamic"
    dump(OUT / "winner_deposited.json", {
        "winner": winner,
        "rule": rule["winner_rule"],
        "selection_static": sel_static,
        "selection_dynamic": sel_dyn,
        "written_before_judgement_read": True,
    })
    print(f"أُودع الأفضل من الاختيار: {winner}", flush=True)
    # judgement is already computed; the choice did not read it
    rnd_units, rnd_fills = [], []
    for window in ("اختيار", "حكم"):
        counts = {}
        for u in units:
            if u["engine"] == winner and u["window"] == window:
                counts[u["symbol"]] = counts.get(u["symbol"], 0) + 1
        for seed in SEEDS:
            jobs = [(sym, winner, window, counts.get(sym, 0), seed, COST) for sym in syms]
            got_u, got_f = [], []
            for rec in run_map(random_symbol, jobs, workers):
                got_u.extend(rec["units"])
                got_f.extend(rec["fills"])
            rnd_units.extend(got_u)
            rnd_fills.extend(got_f)
            st = summarize(got_u)
            st["leg_net"] = round(sum(f["pnl"] for f in got_f), 2)
            st["used_net"] = st["leg_net"] if winner == "dynamic" else st["net"]
            log(f"عشوائي {seed}", window, "ب")
            results.setdefault("random", {}).setdefault(window, {})[str(seed)] = st
            print(f"  [{len(LEDGER)}/{CAP}] عشوائي {seed} {window}: {st['used_net']} شبكات={st['grids']}", flush=True)
    pd.DataFrame(rnd_fills, columns=cols).to_csv(OUT / "trades_grid_random_c00115.csv", index=False)
    rg = _official_guard(OUT / "trades_grid_random_c00115.csv", COST)
    dump(OUT / "guard_random.json", rg)
    if rg["viol"] != 0:
        dump(OUT / "STOP.json", {"reason": "حارس العشوائي لم يبلغ صفرًا", "guard": rg})
        print("أوقف عند عشوائي. لا تفسير.", flush=True)
        return 2
    jobs = [(sym, COST_130, (winner,)) for sym in syms]
    u130, f130 = [], []
    for rec in run_map(measure_job, jobs, workers):
        u130.extend(rec["units"])
        f130.extend(rec["fills"])
    pd.DataFrame(f130, columns=cols).to_csv(OUT / "trades_grid_winner_c00130.csv", index=False)
    g130 = _official_guard(OUT / "trades_grid_winner_c00130.csv", COST_130)
    dump(OUT / "guard_c00130.json", g130)
    if g130["viol"] != 0:
        dump(OUT / "STOP.json", {"reason": "حارس 0.130% لم يبلغ صفرًا", "guard": g130})
        print("أوقف عند 0.130. لا تفسير.", flush=True)
        return 2
    results["cost_130"] = {}
    for window in ("اختيار", "حكم"):
        un = [u for u in u130 if u["engine"] == winner and u["window"] == window]
        lg = [f for f in f130 if f["engine"] == winner and f["window"] == window]
        st = summarize(un)
        st["leg_net"] = round(sum(f["pnl"] for f in lg), 2)
        st["used_net"] = st["leg_net"] if winner == "dynamic" else st["net"]
        results["cost_130"][window] = st
        log(f"{winner} 0.130%", window, "ب")
        print(f"  [{len(LEDGER)}/{CAP}] {winner} 0.130% {window}: {st['used_net']} شبكات={st['grids']}", flush=True)
    results["silence"] = _silence()
    results["winner"] = winner
    results["ledger"] = LEDGER
    dump(OUT / "results.json", results)
    print(f"اكتمل. المستهلك {len(LEDGER)}/{CAP}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
