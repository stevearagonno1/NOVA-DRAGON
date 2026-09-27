#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0066 — محرك مختبر «دورة التراجع المتوسط» (نسخة بحثية خارج nova_v8؛ مستقلة عن L0065).

التعريف الكامل في hyp_lab_out/L0066/acceptance_rule_l0066.json (كُتب قبل التشغيل). لا وقف متحرك.
السجلات بصيغة سجلات المختبر (مفاتيح L0061) + حقل partial_full (E2: الجزء الأول كان المركز كله).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

BOOK_USD = 1000.0
CONFIRM = 6
STRENGTH_BUF = 0.03            # عازل الوحدة الأصلية LONG_CYCLE_ZONE_BUFFER_PCT
REF_WINDOWS = {"30d": 180, "60d": 360, "90d": 540}
DEPTHS = (0.08, 0.12, 0.16, 0.20)
TRENDS = {"ema20": 20, "ema50": 50, "ema100": 100}
CANCELS = (0.06, 0.08, 0.10, 0.12)
TEMPLATES = {
    2: {"50/50": (0.50, 0.50), "40/60": (0.40, 0.60), "60/40": (0.60, 0.40)},
    3: {"30/30/40": (0.30, 0.30, 0.40), "40/30/30": (0.40, 0.30, 0.30), "20/35/45": (0.20, 0.35, 0.45)},
    4: {"25/25/25/25": (0.25, 0.25, 0.25, 0.25), "15/25/30/30": (0.15, 0.25, 0.30, 0.30), "30/30/25/15": (0.30, 0.30, 0.25, 0.15)},
}
EXITS = ("E1", "E2")


@dataclass
class Config:
    ref: str
    depth: float
    trend: str
    cancel: float
    stages: int
    template: str
    exit: str

    @property
    def key(self) -> str:
        return f"r{self.ref}_d{int(round(self.depth*100))}_{self.trend}_x{int(round(self.cancel*100))}_k{self.stages}_{self.template}_{self.exit}"

    @property
    def weights(self) -> tuple:
        return TEMPLATES[self.stages][self.template]


def all_configs() -> list[Config]:
    out = []
    for e in EXITS:
        for r in REF_WINDOWS:
            for d in DEPTHS:
                for t in TRENDS:
                    for x in CANCELS:
                        for k, temps in TEMPLATES.items():
                            for name in temps:
                                out.append(Config(r, d, t, x, k, name, e))
    return out


class CoinContext:
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
        self.recovery = ((close > prior6_high) & (close > ema20)).fillna(False).to_numpy(bool)
        weakness = ((close < prior3_low) | (close < ema20)).fillna(False).astype(bool)
        self.weak_event = (weakness & ~weakness.shift(1, fill_value=False)).to_numpy(bool)
        self.ref_high, self.pullback_seen = {}, {}
        for rname, bars in REF_WINDOWS.items():
            ref = h4["high"].shift(1).rolling(bars, min_periods=30).max()
            self.ref_high[rname] = ref.to_numpy(float)
            pb = 1.0 - close / ref
            for d in DEPTHS:
                hit = (pb >= d).fillna(False).astype(float)
                seen = hit.shift(1).rolling(CONFIRM, min_periods=1).max().fillna(0.0).astype(bool)
                self.pullback_seen[(rname, d)] = seen.to_numpy(bool)
        days = self.idx.normalize()
        dc = daily["close"]
        self.not_downtrend = {}
        for tname, W in TRENDS.items():
            ema = dc.ewm(span=W, adjust=False).mean()
            clear_down = ((dc < ema) & (ema < ema.shift(10))).fillna(False)
            blocked = clear_down.shift(1, fill_value=False)          # وسم اليوم D = حال D−1
            lut = {ts.normalize(): bool(v) for ts, v in blocked.items()}
            self.not_downtrend[tname] = np.array([not lut.get(d, False) for d in days], dtype=bool)


def run_config(ctx: CoinContext, cfg: Config) -> list[dict]:
    o, h, l, c, n = ctx.o, ctx.h, ctx.l, ctx.c, ctx.n
    entry_ok = ctx.not_downtrend[cfg.trend] & ctx.pullback_seen[(cfg.ref, cfg.depth)] & ctx.recovery
    sig_idx = np.flatnonzero(entry_ok)
    weak = ctx.weak_event
    ref_high = ctx.ref_high[cfg.ref]
    weights = cfg.weights
    k = cfg.stages
    X = cfg.cancel
    depth = cfg.depth
    spacing = depth / k
    target_mult = 1.0 + depth / 2.0
    exit_m = cfg.exit
    idx = ctx.idx
    records: list[dict] = []
    tranches: list[list] = []
    pending: tuple | None = None
    series = 0
    top_seen = False
    partial_done = False
    partial_was_full = False
    next_stage = 0
    sp = 0

    def rec(tr, exit_i, exit_px, reason, pfull=False):
        stage, ei, epx, notional = tr
        records.append({"symbol": ctx.sym, "stage": int(stage), "series": int(series), "entry_bar": int(ei), "exit_bar": int(exit_i),
                        "entry_time": idx[ei].isoformat(), "exit_time": idx[exit_i].isoformat(), "bars_held": int(exit_i - ei),
                        "pnl_usd": 0.0, "notional_usd": float(notional), "reason": reason, "entry_px": float(epx),
                        "entry_ref_px": float(epx), "exit_px": float(exit_px), "partial_full": bool(pfull)})

    def reset():
        nonlocal tranches, top_seen, partial_done, partial_was_full, next_stage
        tranches = []
        top_seen = False
        partial_done = False
        partial_was_full = False
        next_stage = 0

    i = 1
    while i < n:
        if pending is not None and pending[0] == i:
            stage = pending[1]
            pending = None
            if len(tranches) < k and math.isfinite(o[i]) and o[i] > 0:
                if not tranches:
                    series += 1
                tranches.append([stage, i, o[i], BOOK_USD * weights[stage]])
                next_stage = max(next_stage, stage + 1)
        if not tranches:
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
        last_entry = tranches[-1][2]
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
        if exit_m == "E1":
            if math.isfinite(ref_high[i]) and c[i] >= ref_high[i] * (1.0 - STRENGTH_BUF):
                top_seen = True
            if top_seen and weak[i]:
                t = tranches.pop()
                rec(t, i, c[i], "توزيع-قمة")
                if not tranches:
                    reset()
                exited = True
        else:
            if not partial_done and c[i] >= avg_entry * target_mult:
                m = math.ceil(len(tranches) / 2)
                pfull = (m == len(tranches))
                for _ in range(m):
                    t = tranches.pop()
                    rec(t, i, c[i], "هدف-جزئي", pfull)
                partial_done = True
                if not tranches:
                    reset()
                exited = True
            elif partial_done and weak[i]:
                for t in tranches:
                    rec(t, i, c[i], "توزيع-قمة")
                reset()
                exited = True
        if exited:
            i += 1
            continue
        blocked = top_seen or partial_done
        if (not blocked and next_stage < k and entry_ok[i] and pending is None and i + 1 < n
                and c[i] <= last_entry * (1.0 - spacing)):
            pending = (i + 1, next_stage)
        i += 1
    if tranches:
        for t in tranches:
            rec(t, n - 1, c[n - 1], "نهاية-العينة")
        reset()
    return records


def price_pnl(records: list[dict], cost: float) -> None:
    for r in records:
        g = r["exit_px"] / r["entry_px"]
        r["pnl_usd"] = float(((g * (1.0 - cost) - (1.0 + cost)) / (1.0 + cost)) * r["notional_usd"])
