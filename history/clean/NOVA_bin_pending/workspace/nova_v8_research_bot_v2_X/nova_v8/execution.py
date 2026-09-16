"""Module — directional trade lifecycle: entry fill, ATR-based exit engine,
fee/slippage settlement, and the "new-signal" re-entry rule.

Execution rules (no-lookahead):
  * signal on closed bar t -> entry attempt on bar t+1.
  * entry is a limit at the signal close; fills if that bar's low/high touches
    it; otherwise it is cancelled (hanging-bullet ≈ 1 bar) — never chase.
  * stops / time / trail / harvest exits: worst-case inside a candle (stop
    fills before any gain line) and slippage is applied on market-ish exits.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import config as C


def _round_trip_cost_fraction() -> float:
    """Approx fraction cost of one round trip = 2 commissions + slippage."""
    return 2.0 * C.COMMISSION_PCT + C.SLIPPAGE_PCT


GOOD_PROFIT_THRESHOLD = (_round_trip_cost_fraction() * 2.0
                         + C.GOOD_PROFIT_MARGIN)


@dataclass
class Position:
    symbol: str
    side: int                 # +1 long / -1 short
    entry: float
    entry_px: float
    atr_pct: float            # ATR14/entry at fill (frozen yardstick)
    trigger: str
    regime: str
    notional: float = C.NOTIONAL_BASE
    hard_stop: float = 0.0
    be_stop: float = 0.0
    be_locked: bool = False
    trail_active: bool = False
    trail_phase2: bool = False
    trail_stop: float = 0.0
    watermark: float = 0.0
    entry_bar: int = 0
    exit_reason: str = ""
    peak_profit_atr: float = 0.0
    multi: int = 1            # doubling step: 1 (1x),2(2x),4(4x)
    time_grace: int = 0       # extra bars granted (ch6 case b) before time-stop
    series: int = 0           # re-entry series id (>=1 when a harvested continue)

    def gain(self, px: float) -> float:
        return (px - self.entry_px) / self.entry_px * self.side

    def gain_atr(self, px: float) -> float:
        """Profit measured in ATR multiples."""
        if self.atr_pct <= 0:
            return 0.0
        return self.gain(px) / self.atr_pct


class ExitEngine:
    """Deterministic ATR-based exit state machine for a single open position."""

    # exit reasons
    HARD = "وقف"
    BE = "قفل-ربح"
    TRAIL = "تتبع"
    TIME = "زمني"
    HARVEST = "حصد-اعادة"
    REGIME_EXIT = "خروج-حالة"

    def arm(self, pos: Position) -> None:
        mult = min(max(C.HARD_STOP_ATR_MULT * pos.atr_pct,
                       C.HARD_STOP_MIN_PCT), C.HARD_STOP_MAX_PCT)
        pos.hard_stop = pos.entry_px * (1.0 - mult * pos.side)
        pos.watermark = pos.entry_px

    def _lines(self, pos: Position):
        lines = [(pos.hard_stop, self.HARD)]
        if pos.be_locked:
            lines.append((pos.be_stop, self.BE))
        if pos.trail_active:
            lines.append((pos.trail_stop, self.TRAIL))
        return lines

    def update(self, pos: Position, bar_open: float, hi: float, lo: float,
               bar_idx: int, current_regime: str, bar_close: float | None = None):
        """Advance one bar. Returns (reason, fill_px) if the position exits.

        Evaluation order is conservative:
          1) test already-armed stop lines vs this bar's low/high
             (worst-case fills — a stop fills before any gain line);
          2) micro time-stop (a discretionary cut, modelled at the bar CLOSE,
             not the bar's adverse extreme, which would be unrealistically
             pessimistic);
          3) advance BE / trailing lines using this bar's extremes.
        """
        # ---- 1) stop lines ----
        hit = None
        if pos.side == 1:
            cand = [x for x in self._lines(pos) if lo <= x[0]]
            if cand:
                px = min(x[0] for x in cand)          # worst (lowest) stop
                reason = next(r for p_, r in cand if p_ == px)
                if bar_open < px:                     # gapped through -> open
                    px = bar_open
                hit = (reason, min(px, hi))
        else:
            cand = [x for x in self._lines(pos) if hi >= x[0]]
            if cand:
                px = max(x[0] for x in cand)          # worst (highest) stop
                reason = next(r for p_, r in cand if p_ == px)
                if bar_open > px:
                    px = bar_open
                hit = (reason, max(px, lo))
        if hit:
            return hit

        # ---- 2) micro time-stop (fill at bar close) ----
        if bar_idx - pos.entry_bar >= C.TIME_STOP_BARS + pos.time_grace:
            probe = bar_close if bar_close is not None else \
                (lo if pos.side == 1 else hi)
            if pos.gain_atr(probe) < C.TIME_STOP_MIN_PROFIT_ATR:
                return self.TIME, probe

        # ---- 3) advance BE / trailing ----
        fav = hi if pos.side == 1 else lo
        gain_atr = pos.gain_atr(fav)
        pos.peak_profit_atr = max(pos.peak_profit_atr, gain_atr)

        if not pos.be_locked and gain_atr >= C.BE_TRIGGER_ATR_MULT:
            # move stop up to protect ~ entry (lock break-even)
            lift = min(C.BE_LOCK_ATR_MULT * pos.atr_pct, 0.5 * pos.atr_pct)
            pos.be_stop = pos.entry_px * (1.0 + lift * pos.side)
            pos.be_locked = True

        if not pos.trail_active and gain_atr >= C.TRAIL_ACT_ATR_MULT:
            pos.trail_active = True
            pos.trail_stop = pos.entry_px

        # non-linear trailing distance
        if gain_atr >= C.TRAIL_PHASE2_PROFIT:
            pos.trail_phase2 = True
        dist = (C.TRAIL_PHASE2_DIST if pos.trail_phase2
                else C.TRAIL_PHASE1_DIST)

        if pos.side == 1:
            pos.watermark = max(pos.watermark, hi)
            if pos.trail_active:
                pos.trail_stop = max(pos.trail_stop,
                                     pos.watermark * (1.0 - dist * pos.atr_pct))
        else:
            pos.watermark = min(pos.watermark, lo)
            if pos.trail_active:
                pos.trail_stop = min(pos.trail_stop or math.inf,
                                     pos.watermark * (1.0 + dist * pos.atr_pct))
        return None


def settle_directional(pos: Position, exit_px: float) -> float:
    """Net fractional return after commission + slippage for one leg of trade.

    exit_px is the raw fill; we subtract entry commission, exit commission and
    slippage symmetrically on notional. Equal notional sizing -> returns the
    per-unit net fraction.
    """
    raw = pos.gain(exit_px)
    gross_factor = 1.0 + raw
    # entry fee on notional; exit fee+slippage on exit value
    entry_fee = C.COMMISSION_PCT
    exit_fee = C.COMMISSION_PCT + C.SLIPPAGE_PCT
    net = (gross_factor * (1.0 - exit_fee) - (1.0 + entry_fee)) / (1.0 + entry_fee)
    return net
