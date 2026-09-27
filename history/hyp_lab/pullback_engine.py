#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0065 — محرك مختبر «دورة التراجع العادي» (نسخة بحثية خارج nova_v8).

التعريف الكامل في history/research/hyp_lab_out/L0065/acceptance_rule_l0065.json (كُتب قبل التشغيل).
يعمل على شموع 4س ويومية جاهزة (كاش L0061)، ويعيد سجلات بصيغة سجلات المختبر (نفس مفاتيح L0061):
symbol, stage, series, entry_bar, exit_bar, entry_time, exit_time, bars_held, pnl_usd, notional_usd, reason,
entry_px, entry_ref_px, exit_px.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

BOOK_USD = 1000.0
STAGE_GAP = 0.015          # كما في الأصل LONG_CYCLE_STAGE_GAP_PCT
CONFIRM = 6                # كما في الأصل LONG_CYCLE_CONFIRM_BARS_4H
REF_BARS = 180             # 30 يومًا من شموع 4س
STRENGTH_BUF = 0.01        # منطقة القوة = ref_high × (1 − 1%)
DEPTHS = (0.02, 0.04, 0.06, 0.08)
WINDOWS_TREND = {"short": 20, "medium": 50, "long": 100}
SPLITS = {"25/25/25/25": (0.25, 0.25, 0.25, 0.25), "20/30/30/20": (0.20, 0.30, 0.30, 0.20),
          "30/30/25/15": (0.30, 0.30, 0.25, 0.15), "40/30/20/10": (0.40, 0.30, 0.20, 0.10),
          "15/25/30/30(ref)": (0.15, 0.25, 0.30, 0.30)}
STAGES = (2, 3, 4)
CANCELS = (0.03, 0.05, 0.07)
EXITS = ("E1", "E2", "E3")


def weights_for(split: tuple, k: int) -> tuple:
    w = split[:k]
    s = sum(w)
    return tuple(x / s for x in w)


@dataclass
class Config:
    depth: float
    trend: str
    split: str
    stages: int
    cancel: float
    exit: str

    @property
    def key(self) -> str:
        return f"d{int(self.depth*100)}_{self.trend}_{self.split}_k{self.stages}_x{int(self.cancel*100)}_{self.exit}"

    @property
    def weights(self) -> tuple:
        return weights_for(SPLITS[self.split], self.stages)


def all_configs() -> list[Config]:
    out = []
    for e in EXITS:
        for d in DEPTHS:
            for t in WINDOWS_TREND:
                for s in SPLITS:
                    for k in STAGES:
                        for x in CANCELS:
                            out.append(Config(d, t, s, k, x, e))
    return out


class CoinContext:
    """المصفوفات المحسوبة مسبقًا لعملة واحدة داخل نافذة (بيانات 4س ويومية حتى نهاية النافذة)."""

    def __init__(self, sym: str, h4: pd.DataFrame, daily: pd.DataFrame):
        self.sym = sym
        self.idx = h4.index
        self.n = len(h4)
        self.o = h4["open"].to_numpy(float)
        self.h = h4["high"].to_numpy(float)
        self.l = h4["low"].to_numpy(float)
        self.c = h4["close"].to_numpy(float)
        close = h4["close"]
        ema20 = close.ewm(span=20, adjust=False).mean()
        prior6_high = h4["high"].shift(1).rolling(CONFIRM).max()
        prior3_low = h4["low"].shift(1).rolling(3).min()
        mss = close > prior6_high
        self.recovery = (mss & (close > ema20)).fillna(False).to_numpy(bool)
        weakness = ((close < prior3_low) | (close < ema20)).fillna(False).astype(bool)
        self.weak_event = (weakness & ~weakness.shift(1, fill_value=False)).to_numpy(bool)
        ref = h4["high"].shift(1).rolling(REF_BARS, min_periods=30).max()
        self.ref_high = ref.to_numpy(float)
        pb = (1.0 - close / ref)
        self.pullback_seen = {}
        for d in DEPTHS:
            hit = (pb >= d).fillna(False).astype(float)
            seen = hit.shift(1).rolling(CONFIRM, min_periods=1).max().fillna(0.0).astype(bool)
            self.pullback_seen[d] = seen.to_numpy(bool)
        # الاتجاه اليومي السببي: اليوم D يستعمل قيم D−1
        days = self.idx.normalize()
        self.trend_ok = {}
        dc = daily["close"]
        for name, W in WINDOWS_TREND.items():
            ema = dc.ewm(span=W, adjust=False).mean()
            ok_day = ((dc > ema) & (ema > ema.shift(10))).fillna(False)
            ok_shift = ok_day.shift(1, fill_value=False)      # وسم اليوم D = حال D−1
            lut = {ts.normalize(): bool(v) for ts, v in ok_shift.items()}
            self.trend_ok[name] = np.array([lut.get(d, False) for d in days], dtype=bool)


def run_config(ctx: CoinContext, cfg: Config) -> list[dict]:
    o, h, l, c, n = ctx.o, ctx.h, ctx.l, ctx.c, ctx.n
    entry_ok = ctx.trend_ok[cfg.trend] & ctx.pullback_seen[cfg.depth] & ctx.recovery
    sig_idx = np.flatnonzero(entry_ok)
    weak = ctx.weak_event
    ref_high = ctx.ref_high
    weights = cfg.weights
    k = cfg.stages
    X = cfg.cancel
    depth = cfg.depth
    exit_m = cfg.exit
    idx = ctx.idx
    records: list[dict] = []
    tranches: list[list] = []      # [stage, entry_i, entry_px, notional]
    pending: tuple | None = None   # (exec_i, stage)
    series = 0
    top_seen = False
    partial_done = False
    trail_active = False
    trail_peak = 0.0
    next_stage = 0
    sp = 0                          # مؤشر على sig_idx

    def rec(tr, exit_i, exit_px, reason):
        stage, ei, epx, notional = tr
        records.append({"symbol": ctx.sym, "stage": int(stage), "series": int(series), "entry_bar": int(ei), "exit_bar": int(exit_i),
                        "entry_time": idx[ei].isoformat(), "exit_time": idx[exit_i].isoformat(), "bars_held": int(exit_i - ei),
                        "pnl_usd": 0.0, "notional_usd": float(notional), "reason": reason, "entry_px": float(epx),
                        "entry_ref_px": float(epx), "exit_px": float(exit_px)})

    def reset():
        nonlocal tranches, top_seen, partial_done, trail_active, trail_peak, next_stage
        tranches = []
        top_seen = False
        partial_done = False
        trail_active = False
        trail_peak = 0.0
        next_stage = 0

    i = 1
    while i < n:
        # 1) تنفيذ الشراء المعلّق عند الافتتاح
        if pending is not None and pending[0] == i:
            stage = pending[1]
            pending = None
            if len(tranches) < k and math.isfinite(o[i]) and o[i] > 0:
                if not tranches:
                    series += 1
                tranches.append([stage, i, o[i], BOOK_USD * weights[stage]])
                next_stage = max(next_stage, stage + 1)
        if not tranches:
            # القفز إلى إشارة الدخول التالية (بلا مركز لا يحدث شيء بين الإشارات)
            while sp < len(sig_idx) and sig_idx[sp] < i:
                sp += 1
            if sp >= len(sig_idx):
                break
            j = int(sig_idx[sp])
            if j == i:
                if pending is None and i + 1 < n:
                    pending = (i + 1, 0)
                i += 1
            else:
                i = j
            continue
        min_entry = min(t[2] for t in tranches)
        # 2) وقف الإلغاء
        level = min_entry * (1.0 - X)
        if math.isfinite(l[i]) and l[i] <= level:
            fill = o[i] if o[i] < level else level
            for t in tranches:
                rec(t, i, fill, "إلغاء-دورة")
            reset()
            i += 1
            continue
        tot_n = sum(t[3] for t in tranches)
        avg_entry = sum(t[2] * t[3] for t in tranches) / tot_n
        exited = False
        # 3) الخروج حسب الطريقة
        if exit_m == "E1":
            if math.isfinite(ref_high[i]) and c[i] >= ref_high[i] * (1.0 - STRENGTH_BUF):
                top_seen = True
            if top_seen and weak[i]:
                t = tranches.pop()
                rec(t, i, c[i], "توزيع-قمة")
                if not tranches:
                    reset()
                exited = True
        elif exit_m == "E2":
            if not partial_done and c[i] >= avg_entry * (1.0 + depth):
                m = math.ceil(len(tranches) / 2)
                for _ in range(m):
                    t = tranches.pop()
                    rec(t, i, c[i], "هدف-جزئي")
                partial_done = True
                if not tranches:
                    reset()
                exited = True
            elif partial_done and weak[i]:
                for t in tranches:
                    rec(t, i, c[i], "توزيع-قمة")
                reset()
                exited = True
        else:  # E3
            if trail_active:
                lvl = trail_peak * (1.0 - depth / 2.0)
                if math.isfinite(l[i]) and l[i] <= lvl:
                    fill = o[i] if o[i] < lvl else lvl
                    for t in tranches:
                        rec(t, i, fill, "وقف-متحرك")
                    reset()
                    exited = True
                else:
                    trail_peak = max(trail_peak, h[i])
            elif c[i] >= avg_entry * (1.0 + depth):
                trail_active = True
                trail_peak = h[i]
        if exited:
            i += 1
            continue
        # 4) الإضافة
        blocked = top_seen or partial_done or trail_active
        if (not blocked and next_stage < k and entry_ok[i] and pending is None and i + 1 < n
                and c[i] <= min_entry * (1.0 - STAGE_GAP)):
            pending = (i + 1, next_stage)
        i += 1
    if tranches:
        for t in tranches:
            rec(t, n - 1, c[n - 1], "نهاية-العينة")
        reset()
    return records


def price_pnl(records: list[dict], cost: float) -> None:
    """يملأ pnl_usd بصيغة net_fraction (side=1، انزلاق 0)."""
    for r in records:
        g = r["exit_px"] / r["entry_px"]
        r["pnl_usd"] = float(((g * (1.0 - cost) - (1.0 + cost)) / (1.0 + cost)) * r["notional_usd"])
