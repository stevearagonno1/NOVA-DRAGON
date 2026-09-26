# -*- coding: utf-8 -*-
"""L0058 synthetic fill tests and the BTC proof. Not a counted measurement."""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path("/home/user/l0058")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "history" / "hyp_lab"))

import nova_v8.grid as G
import nova_v8.config as VC
from common import load


def expect(name, cond, detail):
    print(f"  {'✅' if cond else '❌'} {name}: {detail}", flush=True)
    if not cond:
        raise SystemExit(f"فشل {name}: {detail}")


def cell_tests():
    print("══ خلايا مصطنعة ══", flush=True)
    c = G._Cell(100.0, 110.0, 1000.0)
    c.on_bar(102.0, 106.0, 99.0, 104.0)
    expect("شراء يحتوي المستوى", c.open and abs(c.fill_buy - 100.0) < 1e-9, c.fill_buy)

    c = G._Cell(100.0, 110.0, 1000.0)
    c.on_bar(90.0, 92.0, 88.0, 91.0)
    expect("شراء الشمعة كلها تحت", c.open and abs(c.fill_buy - 90.0) < 1e-9, c.fill_buy)
    expect("شراء داخل النطاق", 88.0 <= c.fill_buy <= 92.0, c.fill_buy)

    c = G._Cell(100.0, 110.0, 1000.0)
    c.on_bar(100.0, 100.0, 100.0, 100.0)
    c.on_bar(105.0, 112.0, 104.0, 108.0)
    expect("بيع يحتوي المستوى", c.cycles == 1 and abs(c.fill_sell - 110.0) < 1e-9, c.fill_sell)

    c = G._Cell(100.0, 110.0, 1000.0)
    c.on_bar(100.0, 100.0, 100.0, 100.0)
    c.on_bar(120.0, 125.0, 118.0, 122.0)
    expect("بيع الشمعة كلها فوق", c.cycles == 1 and abs(c.fill_sell - 120.0) < 1e-9, c.fill_sell)
    expect("بيع داخل النطاق", 118.0 <= c.fill_sell <= 125.0, c.fill_sell)

    # quantity stays notional/level. Gap buy must not change qty.
    c = G._Cell(100.0, 110.0, 1000.0)
    c.on_bar(90.0, 92.0, 88.0, 91.0)
    expect("الكمية لم تتغير", abs(c.qty - 10.0) < 1e-9, c.qty)


def force_tests():
    print("══ خروج قسري ══", flush=True)
    VC.COMMISSION_PCT = 0.00115
    G._BUY_FEE = G._SELL_FEE = 0.00115
    # upside gap: whole candle above 110*1.02 = 112.2 → open
    g = G.Grid("T", 0, 100.0, 110.0, 105.0)
    g.on_bar(113.0, 116.0, 112.5, 115.0, 1, 0.0)
    expect("فجوة فوق النطاق عند الافتتاح", g.closed and abs(g.last_price - 113.0) < 1e-9, g.last_price)
    expect("الفجوة داخل شمعتها", 112.5 <= g.last_price <= 116.0, g.last_price)

    # upside touch: close beyond, candle contains 112.2 → boundary
    g = G.Grid("T", 0, 100.0, 110.0, 105.0)
    g.on_bar(111.0, 114.0, 110.5, 113.0, 1, 0.0)
    expect("لمس الحد الأعلى عند الحد", g.closed and abs(g.last_price - 112.2) < 1e-9, g.last_price)
    expect("الحد داخل الشمعة", 110.5 <= g.last_price <= 114.0, g.last_price)

    # downside gap: whole candle below 98 → open
    g = G.Grid("T", 0, 100.0, 110.0, 105.0)
    g.on_bar(97.0, 97.5, 96.0, 96.5, 1, 0.0)
    expect("فجوة تحت النطاق عند الافتتاح", g.closed and abs(g.last_price - 97.0) < 1e-9, g.last_price)

    # downside touch → boundary 98
    g = G.Grid("T", 0, 100.0, 110.0, 105.0)
    g.on_bar(99.0, 100.0, 97.5, 97.8, 1, 0.0)
    expect("لمس الحد الأدنى عند الحد", g.closed and abs(g.last_price - 98.0) < 1e-9, g.last_price)
    expect("حد الهبوط داخل الشمعة", 97.5 <= g.last_price <= 100.0, g.last_price)


def load_broken():
    import nova_v8
    path = ROOT / "nova_v8" / "grid_broken_preL0058.py"
    spec = importlib.util.spec_from_file_location("nova_v8.grid_broken_preL0058", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["nova_v8.grid_broken_preL0058"] = mod
    spec.loader.exec_module(mod)
    return mod


def btc_proof():
    print("══ برهان BTC ══", flush=True)
    df = load(str(ROOT / "crypto_archive" / "BTCUSDT_1m.parquet"), start="2021-09-01", end="2021-12-01")
    ts = pd.Timestamp("2021-11-25 00:00:00", tz="UTC")
    if ts not in df.index:
        raise SystemExit(f"الشمعة غير موجودة: {ts}")
    bar = df.loc[ts]
    print(f"  الشمعة O={bar.open} H={bar.high} L={bar.low} C={bar.close}", flush=True)
    if abs(float(bar.high) - 57232.24) > 0.02 or abs(float(bar.low) - 57130.81) > 0.02:
        raise SystemExit(f"نطاق الشمعة خالف الورقة: {bar.low} {bar.high}")
    broken = load_broken()
    dly = load(str(ROOT / "crypto_archive" / "BTCUSDT_1m.parquet"), start="2021-06-01", end="2021-12-01")
    # daily labels from the official loader, shift(1), then the real broken Grid
    from common import to_bars
    dlyb = to_bars(dly, 1440)
    c = dlyb["close"]
    e50 = c.ewm(span=50, adjust=False).mean()
    e200 = c.ewm(span=200, adjust=False).mean()
    slope = e50.diff(10)
    lab = pd.Series("عرضي", index=dlyb.index)
    lab[(e50 > e200) & (slope > 0)] = "صاعد"
    lab[(e50 < e200) & (slope < 0)] = "هابط"
    lab = lab.shift(1)
    lookup = {t.normalize(): v for t, v in lab.items()}
    reg = pd.Series([lookup.get(t.normalize(), None) for t in df.index], index=df.index)
    vals = reg.fillna("x").to_numpy()
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    cl = df["close"].to_numpy(float)
    look = VC.GRID_RANGE_LOOKBACK_BARS
    found = None
    start = 0
    cur = vals[0]
    segs = []
    for i in range(1, len(vals) + 1):
        if i == len(vals) or vals[i] != cur:
            segs.append((cur, start, i - 1))
            if i < len(vals):
                cur = vals[i]
                start = i
    for regime, s, e in segs:
        if regime != "عرضي" or e - s < VC.GRID_MIN_LIFE_BARS or s < look:
            continue
        lo = float(np.nanmin(l[s - look:s]))
        hi = float(np.nanmax(h[s - look:s]))
        mid = (hi + lo) / 2.0
        span = (hi - lo) / mid if mid > 0 else 0.0
        if not (VC.GRID_RANGE_MIN_PCT <= span <= VC.GRID_RANGE_MAX_PCT):
            continue
        grid = broken.Grid("BTCUSDT", s, lo, hi, float(cl[s - 1]))
        for j in range(s, e + 1):
            if grid.closed:
                break
            prev = [(cell.open, cell.buy) for cell in grid.cells]
            grid.on_bar(float(o[j]), float(h[j]), float(l[j]), float(cl[j]), j, 0.0)
            for was, level in prev:
                if df.index[j] != ts:
                    continue
                cell_now = None
            for k, cell in enumerate(grid.cells):
                if not prev[k][0] and cell.open and df.index[j] == ts:
                    if cell.buy > h[j] + 1e-6:
                        found = (cell.buy, h[j], l[j], o[j], j)
                        break
            if found:
                break
        if found:
            break
    if not found:
        raise SystemExit("لم أجد شراء BTC خارج الشمعة في 2021-11-25 00:00. أوقف.")
    booked, hi_b, lo_b, op, j = found
    gap = booked - hi_b
    expect(
        "المعطوب: شراء 57463.86 فوق القمة",
        abs(booked - 57463.857142857) < 1e-3 and abs(gap - 231.62) < 0.05,
        f"booked={booked:.2f} high={hi_b:.2f} gap={gap:.2f}",
    )
    fixed = G._Cell(booked, booked + 1.0, 100.0)
    fixed.on_bar(float(op), float(hi_b), float(lo_b), float(cl[j]))
    expect(
        "المصلَح داخل النطاق وعند الافتتاح",
        abs(fixed.fill_buy - op) < 1e-6 and lo_b - 1e-6 <= fixed.fill_buy <= hi_b + 1e-6,
        f"fill={fixed.fill_buy} open={op}",
    )


if __name__ == "__main__":
    cell_tests()
    force_tests()
    btc_proof()
    print("  ✅ الاختبارات المصغّرة وبرهان BTC", flush=True)
