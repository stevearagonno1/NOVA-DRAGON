#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0067 — محرك مختبر لدورة القاع (L0064/V3) على إطارات 4س/يومية من الكاش، بلا تغيير في تعريف الدورة،
مع عنصرين اختياريين فقط: بوابة سوق BTC (M1/M2) على قرار الشراء، وحد زمني للدورة (حد-زمني).
هوية النسخة مع L0064 (M0، بلا حد) تُثبَت بـsha256 قبل أي قياس (run_l0067_match).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

BOOK_USD = 1000.0
WEIGHTS = (0.15, 0.25, 0.30, 0.30)      # LONG_CYCLE_STAGE_WEIGHTS
LOOKBACK_D = 90                          # LONG_CYCLE_DAILY_LOOKBACK
ZONE_BUF_V2 = 0.08
TOP_BUF = 0.03                           # LONG_CYCLE_ZONE_BUFFER_PCT
GAP = 0.015                              # LONG_CYCLE_STAGE_GAP_PCT
HARD = 0.08                              # LONG_CYCLE_HARD_INVALIDATION_PCT
CONFIRM = 6                              # LONG_CYCLE_CONFIRM_BARS_4H
BARS_PER_DAY = 6


def regime_labels_shifted(daily: pd.DataFrame) -> pd.Series:
    """مصنّف المادة 13 (EMA50/EMA200 يومي، ميل 10 أيام) مع shift(1) — كما في L0061."""
    c = daily["close"]
    e50 = c.ewm(span=50, adjust=False).mean()
    e200 = c.ewm(span=200, adjust=False).mean()
    slope = e50.diff(10)
    lab = pd.Series("عرضي", index=daily.index)
    lab[(e50 > e200) & (slope > 0)] = "صاعد"
    lab[(e50 < e200) & (slope < 0)] = "هابط"
    return lab.shift(1)


def btc_market_ok(btc_daily: pd.DataFrame) -> dict:
    """وسوم يومية مزاحة بيوم: M1 = close > EMA200 · M2 = M1 و EMA50 > EMA200 و EMA50 صاعد على 10 أيام."""
    c = btc_daily["close"]
    e50 = c.ewm(span=50, adjust=False).mean()
    e200 = c.ewm(span=200, adjust=False).mean()
    m1 = (c > e200)
    m2 = m1 & (e50 > e200) & (e50 > e50.shift(10))
    return {"M0": None, "M1": m1.shift(1, fill_value=False), "M2": m2.shift(1, fill_value=False)}


class CoinContext:
    """إشارات L0064 محسوبة بنفس تعابير pandas في الأصل، ثم مصفوفات للحلقة."""

    def __init__(self, sym: str, h4: pd.DataFrame, daily: pd.DataFrame, btc_ok: dict):
        self.sym = sym
        self.idx = h4.index
        self.n = len(h4)
        self.valid = len(h4) >= 200 and len(daily) >= max(40, LOOKBACK_D // 2)
        self.o = h4["open"].to_numpy(float)
        self.h = h4["high"].to_numpy(float)
        self.l = h4["low"].to_numpy(float)
        self.c = h4["close"].to_numpy(float)
        if not self.valid:
            return
        prior_low = daily["low"].shift(1).rolling(LOOKBACK_D, min_periods=max(30, LOOKBACK_D // 3)).min()
        prior_high = daily["high"].shift(1).rolling(LOOKBACK_D, min_periods=max(30, LOOKBACK_D // 3)).max()
        known = pd.DataFrame({"prior_low": prior_low, "prior_high": prior_high}, index=daily.index + pd.Timedelta(days=1))
        dctx = known.reindex(h4.index, method="ffill")
        close, low = h4["close"], h4["low"]
        ema20 = close.ewm(span=20, adjust=False).mean()
        prior6_high = h4["high"].shift(1).rolling(CONFIRM).max()
        prior3_low = h4["low"].shift(1).rolling(3).min()
        mss = close > prior6_high
        zone = close <= dctx["prior_low"] * (1.0 + ZONE_BUF_V2)
        zone_seen = zone.shift(1).rolling(CONFIRM, min_periods=1).max().astype(bool)
        self.entry_signal = (zone_seen & mss & (close > ema20)).to_numpy(bool)
        self.prior_low = dctx["prior_low"].to_numpy(float)
        self.top_zone = (close >= dctx["prior_high"] * (1.0 - TOP_BUF)).to_numpy(bool)
        weakness = ((close < prior3_low) | (close < ema20)).fillna(False).astype(bool)
        self.weak_event = (weakness & ~weakness.shift(1, fill_value=False)).to_numpy(bool)
        days = h4.index.normalize()
        lab = regime_labels_shifted(daily)
        lut = {ts.normalize(): (v == "هابط") for ts, v in lab.items()}
        self.bear_ok = np.array([lut.get(d, False) for d in days], dtype=bool)
        self.market_ok = {"M0": np.ones(self.n, dtype=bool)}
        for m in ("M1", "M2"):
            s = btc_ok[m]
            lutm = {ts.normalize(): bool(v) for ts, v in s.items()}
            # يوم بلا بيانات BTC = غير كافٍ ⇒ لا شراء (لا تخمين)
            self.market_ok[m] = np.array([lutm.get(d, False) for d in days], dtype=bool)


def run(ctx: CoinContext, market: str = "M0", time_limit_days: int | None = None) -> list[dict]:
    if not ctx.valid:
        return []
    o, h, l, c, n, idx = ctx.o, ctx.h, ctx.l, ctx.c, ctx.n, ctx.idx
    entry_signal, prior_low, top_zone, weak = ctx.entry_signal, ctx.prior_low, ctx.top_zone, ctx.weak_event
    allowed = ctx.bear_ok & ctx.market_ok[market]
    tl_bars = None if time_limit_days is None else int(time_limit_days) * BARS_PER_DAY
    records: list[dict] = []
    tranches: list[list] = []           # [stage, entry_i, entry_px, notional]
    pending: tuple | None = None        # (exec_i, stage)
    cycle = 0
    first_entry_i = -1
    top_seen = False
    next_stage = 0

    def rec(tr, exit_i, px, reason):
        stage, ei, epx, notional = tr
        records.append({"symbol": ctx.sym, "stage": int(stage), "series": 0, "cycle": int(cycle), "entry_bar": int(ei), "exit_bar": int(exit_i),
                        "entry_time": idx[ei].isoformat(), "exit_time": idx[exit_i].isoformat(), "bars_held": int(exit_i - ei),
                        "pnl_usd": 0.0, "notional_usd": float(notional), "reason": reason, "entry_px": float(epx),
                        "entry_ref_px": float(epx), "exit_px": float(px)})

    def close_all(exit_i, reason, px):
        nonlocal tranches, top_seen, next_stage, first_entry_i
        for t in list(tranches):
            rec(t, exit_i, px, reason)
        tranches = []
        top_seen = False
        next_stage = 0
        first_entry_i = -1

    for i in range(1, n):
        if pending is not None and pending[0] == i:
            stage = pending[1]
            pending = None
            if len(tranches) < len(WEIGHTS) and math.isfinite(o[i]) and o[i] > 0:
                if not tranches:
                    cycle += 1
                    first_entry_i = i
                tranches.append([stage, i, o[i], BOOK_USD * WEIGHTS[stage]])
                next_stage = max(next_stage, stage + 1)
        if not tranches:
            if entry_signal[i] and allowed[i] and pending is None:
                pending = (i + 1, 0)
            continue
        min_entry = min(t[2] for t in tranches)
        bl = prior_low[i]
        invalid = min(min_entry * (1.0 - HARD), bl * (1.0 - 0.02) if math.isfinite(bl) else -math.inf)
        if math.isfinite(l[i]) and l[i] <= invalid:
            fill = o[i] if o[i] < invalid else invalid
            close_all(i, "إلغاء-دورة", fill)
            continue
        if tl_bars is not None and (i - first_entry_i) >= tl_bars:
            close_all(i, "حد-زمني", c[i])
            continue
        if top_zone[i]:
            top_seen = True
        if top_seen and weak[i] and tranches:
            t = tranches.pop()
            rec(t, i, c[i], "توزيع-قمة")
            if not tranches:
                top_seen = False
                next_stage = 0
                first_entry_i = -1
            continue
        if (not top_seen and next_stage < len(WEIGHTS) and entry_signal[i] and allowed[i] and pending is None
                and c[i] <= min_entry * (1.0 - GAP)):
            pending = (i + 1, next_stage)
    if tranches:
        close_all(n - 1, "نهاية-العينة", c[n - 1])
    return records


def price_pnl(records: list[dict], cost: float) -> None:
    for r in records:
        g = r["exit_px"] / r["entry_px"]
        r["pnl_usd"] = float(((g * (1.0 - cost) - (1.0 + cost)) / (1.0 + cost)) * r["notional_usd"])
