"""Module — directional trade lifecycle: entry fill, ATR-based exit engine,
fee/slippage settlement, and the "new-signal" re-entry rule.

Execution rules (no-lookahead):
  * signal on closed bar t -> entry attempt on bar t+1.
  * entry is a market-style execution at the next bar's open, with an adverse
    effective spread/slippage proxy — never at the signal close.
  * stops / time / trail / harvest exits: worst-case inside a candle (stop
    fills before any gain line) and slippage is applied on market-ish exits.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import config as C


def _round_trip_cost_fraction() -> float:
    """Conservative base cost of one market round trip.

    The research model now treats Directional/BTC entries and exits as market
    executions: commission and the base effective spread/slippage proxy apply
    on both sides.  This is only a threshold estimate; actual settlement uses
    the regime/volatility-aware effective cost at each execution.
    """
    return 2.0 * C.COMMISSION_PCT + 2.0 * C.SLIPPAGE_PCT


# "good profit" = covers the cost of a number of round trips (config, default 2)
# plus a small margin, per design ch.6.
GOOD_PROFIT_THRESHOLD = (_round_trip_cost_fraction() * C.GOOD_PROFIT_COST_COVER
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
    entry_ref_px: float = 0.0 # raw next-open reference, for audit/sensitivity
    entry_cost_pct: float = 0.0  # effective entry cost applied to the reference

    def gain(self, px: float) -> float:
        return (px - self.entry_px) / self.entry_px * self.side

    def gain_atr(self, px: float) -> float:
        """Profit measured in ATR multiples."""
        if self.atr_pct <= 0:
            return 0.0
        return self.gain(px) / self.atr_pct


_PROFILE_CACHE: dict = {}


def clear_profile_cache() -> None:
    """Invalidate the per-regime exit-profile cache (used after config edits)."""
    _PROFILE_CACHE.clear()


def exit_profile(regime: str | None) -> dict:
    """Resolve the effective exit parameters for a market regime.

    Starts from the global defaults in config and overlays any per-regime
    override from C.REGIME_EXIT_OVERRIDES[regime]. This is the single place the
    exit engine reads its numbers from, so per-regime tuning (design ch.5) needs
    no code change — only a config entry. Cached per regime.
    """
    key = regime or ""
    cached = _PROFILE_CACHE.get(key)
    if cached is not None:
        return cached
    p = {
        "hard_stop_mult": C.HARD_STOP_ATR_MULT,
        "hard_stop_min": C.HARD_STOP_MIN_PCT,
        "hard_stop_max": C.HARD_STOP_MAX_PCT,
        "be_trigger": C.BE_TRIGGER_ATR_MULT,
        "be_lock": C.BE_LOCK_ATR_MULT,
        "trail_basis": C.TRAIL_BASIS,
        "trail_act": C.TRAIL_ACT_ATR_MULT,
        "trail_p1": C.TRAIL_PHASE1_DIST,
        "trail_p2": C.TRAIL_PHASE2_DIST,
        "trail_p2_profit": C.TRAIL_PHASE2_PROFIT,
        "fib_act": C.FIB_ACT_ATR_MULT,
        "fib_p1": C.FIB_RETRACE_P1,
        "fib_p2": C.FIB_RETRACE_P2,
        "fib_p2_trigger": C.FIB_P2_TRIGGER,
        "time_bars": C.TIME_STOP_BARS,
        "time_min_profit": C.TIME_STOP_MIN_PROFIT_ATR,
    }
    over = C.REGIME_EXIT_OVERRIDES.get(key) or {}
    p.update({k: v for k, v in over.items() if k in p})
    _PROFILE_CACHE[key] = p
    return p


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
        p = exit_profile(pos.regime)
        mult = min(max(p["hard_stop_mult"] * pos.atr_pct,
                       p["hard_stop_min"]), p["hard_stop_max"])
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
        p = exit_profile(pos.regime)

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
        if bar_idx - pos.entry_bar >= p["time_bars"] + pos.time_grace:
            probe = bar_close if bar_close is not None else \
                (lo if pos.side == 1 else hi)
            if pos.gain_atr(probe) < p["time_min_profit"]:
                return self.TIME, probe

        # ---- 3) advance BE / trailing ----
        fav = hi if pos.side == 1 else lo
        gain_atr = pos.gain_atr(fav)
        pos.peak_profit_atr = max(pos.peak_profit_atr, gain_atr)

        if not pos.be_locked and gain_atr >= p["be_trigger"]:
            # move stop up to protect ~ entry (lock break-even)
            lift = min(p["be_lock"] * pos.atr_pct, 0.5 * pos.atr_pct)
            pos.be_stop = pos.entry_px * (1.0 + lift * pos.side)
            pos.be_locked = True

        fib = (p["trail_basis"] == "fib")
        act_mult = p["fib_act"] if fib else p["trail_act"]
        if not pos.trail_active and gain_atr >= act_mult:
            pos.trail_active = True
            pos.trail_stop = pos.entry_px

        if pos.side == 1:
            pos.watermark = max(pos.watermark, hi)
        else:
            pos.watermark = min(pos.watermark, lo)

        if not pos.trail_active:
            return None

        if fib:
            # golden-ratio retracement trail: protect a fraction of the run
            # measured from entry to the running peak (watermark).
            if pos.side == 1:
                run = pos.watermark - pos.entry_px
                if run > 0 and pos.peak_profit_atr >= p["fib_p2_trigger"]:
                    pos.trail_phase2 = True
                retrace = p["fib_p2"] if pos.trail_phase2 else p["fib_p1"]
                if run > 0:
                    pos.trail_stop = max(pos.trail_stop,
                                         pos.watermark - retrace * run)
            else:
                run = pos.entry_px - pos.watermark
                if run > 0 and pos.peak_profit_atr >= p["fib_p2_trigger"]:
                    pos.trail_phase2 = True
                retrace = p["fib_p2"] if pos.trail_phase2 else p["fib_p1"]
                if run > 0:
                    pos.trail_stop = min(pos.trail_stop or math.inf,
                                         pos.watermark + retrace * run)
        else:
            # non-linear ATR-distance trailing distance
            if gain_atr >= p["trail_p2_profit"]:
                pos.trail_phase2 = True
            dist = p["trail_p2"] if pos.trail_phase2 else p["trail_p1"]
            if pos.side == 1:
                pos.trail_stop = max(pos.trail_stop,
                                     pos.watermark * (1.0 - dist * pos.atr_pct))
            else:
                pos.trail_stop = min(pos.trail_stop or math.inf,
                                     pos.watermark * (1.0 + dist * pos.atr_pct))
        return None


def net_fraction(entry_px: float, exit_px: float, side: int,
                 slip_pct: float = C.SLIPPAGE_PCT) -> float:
    """Net fractional return after conservative market execution costs.

    ``entry_px`` is the *effective executed entry price* after entry-side
    spread/slippage. ``exit_px`` is the raw stop/market reference price; the
    exit-side effective cost is applied here.  Keeping this distinction makes a
    recorded trade auditable without pretending to know the order book.
    """
    if entry_px <= 0:
        return 0.0
    raw = (exit_px - entry_px) / entry_px * side
    gross_factor = 1.0 + raw
    entry_fee = C.COMMISSION_PCT
    exit_fee = C.COMMISSION_PCT + slip_pct
    net = (gross_factor * (1.0 - exit_fee) - (1.0 + entry_fee)) / (1.0 + entry_fee)
    return net


def market_cost_pct(vr: float | None = None, regime: str | None = None,
                    base: float | None = None) -> float:
    """Effective market execution cost per side.

    This is deliberately an *effective cost proxy* for spread plus slippage;
    it is not a claim about a measured order-book spread.  It is used for
    Directional/BTC market orders and forced Grid flattening.
    """
    raw = C.SLIPPAGE_PCT if base is None else float(base)
    return raw * spread_multiplier(vr, regime)


def market_fill(price: float, side: int, cost_pct: float) -> float:
    """Apply adverse effective execution cost to a market entry reference.

    Long entry buys above the reference; short entry sells below it.  Exit
    costs are applied by :func:`net_fraction` so they are not double-counted.
    """
    if price <= 0:
        return price
    return price * (1.0 + cost_pct * (1 if side == 1 else -1))


def spread_multiplier(vr: float | None = None, regime: str | None = None) -> float:
    """Execution-realism slippage multiplier for the exit.

    When SPREAD_MODE == "vol", the model/effective slippage widens as liquidity
    thins: a high volatility ratio (crisis) widens it most (x3), and a merely
    elevated VR widens it moderately (x2). This captures sudden spread widening
    at times of weak liquidity/panic without a hard-coded time schedule.
    """
    if C.SPREAD_MODE != "vol":
        return 1.0
    if regime is not None and regime == C.REGIME_SHOCK:
        return C.SPREAD_SHOCK_MULT
    if vr is not None and math.isfinite(vr):
        if vr >= C.VR_SHOCK:                       # crisis-scale volatility
            return C.SPREAD_SHOCK_MULT
        if vr >= C.SPREAD_HIGHVOL_VR:
            return C.SPREAD_HIGHVOL_MULT
    return 1.0


def settle_directional(pos: Position, exit_px: float,
                       slip_pct: float | None = None) -> float:
    """Settle using effective entry price plus exit-side market cost."""
    slip = C.SLIPPAGE_PCT if slip_pct is None else slip_pct
    return net_fraction(pos.entry_px, exit_px, pos.side, slip)
