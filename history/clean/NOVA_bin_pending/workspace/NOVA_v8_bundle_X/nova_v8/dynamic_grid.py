"""Dynamic Grid (DGT) — independent research sleeve; a variant of the static
Spot Grid (approved design: ATR spacing + cash reserve + limited conditional
reset; detailed spec 8.7 of الملف الشامل الموحد).

Deliberately isolated (baseline untouched):
  * disabled by default; selected explicitly (--strategies dynamic_grid|all)
  * the static Grid sleeve, the next-open execution model, and the cost model
    are NOT modified; DGT is compared against Static in a separate experiment
  * recorded as ONE research unit per contiguous CHOP regime run — the same
    granularity as the static grid, so Static vs Dynamic compare directly

Mechanics (causal, no lookahead):
  * geometric levels inside a lookback range, spacing
        k = max(ATR(regime TF) * DGT_SPACING_ATR_MULT / P,
                DGT_SPACING_MIN_PCT, fit-to-range floor)
    (the cost floor guarantees a cell edge can clear the round-trip cost)
  * at activation a base position = capital * m/n_levels is bought at the
    next bar's open (market cost), m = levels strictly below the reference
    price; the remainder stays cash (cash reserve — approved design)
  * limit cells buy at the lower level / sell at the next (commission only)
  * range break (close beyond boundary + buffer): open cells and the base
    position are flattened at the market (gap-aware fill, effective cost); if
    the run is still CHOP and resets remain, the grid rebuilds around the new
    price after a cooldown (limited resets — approved); a regime change ends
    the run and the unit closes instead of resetting (no reset in
    Trend/Shock — approved, enforced by the segment structure)
  * hard unit stop when total net (realized + unrealized) <= -DGT_STOP_NET_PCT

Temporary assumptions (to be revisited in the one-variable phase): spacing
scale (ATR of the regime TF), cooldown length, and the hard stop level.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np
import pandas as pd

from . import config as C
from . import indicators as ind
from .execution import market_cost_pct


class _Cell:
    """One grid cell: buy at the lower level (limit, commission only), sell at
    the next higher level (limit, commission only)."""
    __slots__ = ("buy", "sell", "qty", "open", "realized_usd", "cycles")

    def __init__(self, buy: float, sell: float, notional: float):
        self.buy = buy
        self.sell = sell
        self.qty = notional / buy if buy > 0 else 0.0
        self.open = False
        self.realized_usd = 0.0
        self.cycles = 0

    def on_bar(self, o: float, h: float, l: float, c: float) -> None:
        if not self.open:
            if l <= self.buy:
                self.open = True
        elif h >= self.sell:
            buy_cost = self.qty * self.buy
            sell_gross = self.qty * self.sell
            fees = buy_cost * C.COMMISSION_PCT + sell_gross * C.COMMISSION_PCT
            self.realized_usd += (sell_gross - buy_cost) - fees
            self.cycles += 1
            self.open = False

    def unrealized_usd(self, cur: float) -> float:
        if not self.open:
            return 0.0
        buy_cost = self.qty * self.buy
        return (self.qty * cur - buy_cost) - buy_cost * C.COMMISSION_PCT

    def flatten_usd(self, cur: float, slip_pct: float) -> float:
        """Forced market exit of an open cell (commission + effective slip)."""
        if not self.open:
            return 0.0
        buy_cost = self.qty * self.buy
        exit_gross = self.qty * cur
        fees = (buy_cost * C.COMMISSION_PCT
                + exit_gross * (C.COMMISSION_PCT + slip_pct))
        self.open = False
        return (exit_gross - buy_cost) - fees


class DynamicGridUnit:
    """One dynamic grid research unit over a contiguous CHOP regime run."""

    STATE_GRID = "grid"
    STATE_FLAT = "flat"

    def __init__(self, symbol: str, start_bar: int, capital: float):
        self.symbol = symbol
        self.start_bar = start_bar
        self.capital = float(capital)
        self.state = self.STATE_FLAT
        self.closed = False
        self.close_bar: int | None = None
        self.close_reason = ""
        self.bars = 0
        self.built = False
        self.resets = 0
        self.realized_total = 0.0
        self.cycles_total = 0
        self.cells: list[_Cell] = []
        self.lo = 0.0
        self.hi = 0.0
        self.base_qty = 0.0
        self.base_px = 0.0
        self.rebuild_at = 0
        self._cur = 0.0

    # ------------------------------------------------------------- lifecycle
    def build(self, bar_i: int, ref_px: float, atr: float | None,
              lo: float, hi: float, exec_px: float, slip_pct: float,
              bias: int = 0) -> bool:
        """(Re)build levels around ref_px (info up to bar_i-1 only); the base
        position is executed at exec_px (bar_i open). Returns False — and
        closes the unit — when the range is unusable.

        ``bias`` (+1 up / -1 down, 0 flat) drives the optional asymmetric mode
        (spec 8.7): cell capital is skewed toward the cells on the bias side
        (up-bias -> upper sell cells; down-bias -> lower cells)."""
        P = float(ref_px)
        if not (math.isfinite(P) and P > 0):
            self.close(bar_i, "نطاق-غير-صالح", P, slip_pct)
            return False
        if not (math.isfinite(lo) and math.isfinite(hi) and hi > lo > 0):
            self.close(bar_i, "نطاق-غير-صالح", P, slip_pct)
            return False
        k = 0.0
        if atr is not None and math.isfinite(float(atr)) and float(atr) > 0:
            k = C.DGT_SPACING_ATR_MULT * float(atr) / P
        k = max(k, C.DGT_SPACING_MIN_PCT)
        cap = max(2, C.DGT_LEVELS_MAX - 1)
        k_fit = (hi / lo) ** (1.0 / cap) - 1.0     # span the whole range
        k = max(k, k_fit)
        if k <= 0:
            self.close(bar_i, "نطاق-غير-صالح", P, slip_pct)
            return False
        levels = [lo]
        while len(levels) - 1 < cap:
            nxt = levels[-1] * (1.0 + k)
            if nxt > hi:
                break
            levels.append(nxt)
        if len(levels) - 1 < 2:
            self.close(bar_i, "نطاق-غير-صالح", P, slip_pct)
            return False
        n_cells = len(levels) - 1
        if C.DGT_ASYMMETRIC and bias != 0:
            # skew cell capital toward the bias side of the reference price
            w = []
            for i in range(n_cells):
                on_bias_side = (levels[i] >= P) == (bias == 1)
                w.append(1.0 + (C.DGT_ASYM_BIAS if on_bias_side
                                else -C.DGT_ASYM_BIAS))
            w = [max(x, 0.25) for x in w]
            tot = sum(w)
            self.cells = [_Cell(levels[i], levels[i + 1],
                                self.capital * w[i] / tot)
                          for i in range(n_cells)]
        else:
            self.cells = [_Cell(levels[i], levels[i + 1],
                                self.capital / n_cells)
                          for i in range(n_cells)]
        self.lo, self.hi = float(lo), float(hi)
        # base position: m = levels strictly below P; cash reserve = the rest
        m = sum(1 for lv in levels if lv < P)
        base_notional = self.capital * (m / len(levels))
        self.base_qty = 0.0
        self.base_px = 0.0
        if base_notional > 0 and math.isfinite(exec_px) and exec_px > 0:
            self.base_px = exec_px * (1.0 + slip_pct)
            self.base_qty = base_notional / self.base_px
        self._cur = P
        if self.built:
            self.resets += 1
        self.built = True
        self.state = self.STATE_GRID
        return True

    def on_bar(self, o: float, h: float, l: float, c: float,
               bar_idx: int, slip_pct: float) -> None:
        if self.closed:
            return
        self.bars += 1
        self._cur = c
        if self.state != self.STATE_GRID:
            return
        for cell in self.cells:
            cell.on_bar(o, h, l, c)
        hi_b = self.hi * (1.0 + C.DGT_BREAK_BUFFER_PCT)
        lo_b = self.lo * (1.0 - C.DGT_BREAK_BUFFER_PCT)
        if c > hi_b or c < lo_b:
            # gap-through: if the bar opens beyond the boundary, the forced
            # market flatten fills at that open, not at the stale boundary
            gap_cur = o if (o > hi_b or o < lo_b) else c
            self._flatten(gap_cur, slip_pct)
            if self.resets >= C.DGT_MAX_RESETS:
                self.close(bar_idx, "استنفاد-إعادة", gap_cur, slip_pct)
            else:
                # still inside the CHOP run -> rebuild after a cooldown
                self.state = self.STATE_FLAT
                self.rebuild_at = bar_idx + C.DGT_RESET_COOLDOWN_BARS
            return
        # hard unit stop on total net (realized + unrealized)
        if self.total_net_usd() <= -C.DGT_STOP_NET_PCT * self.capital:
            self._flatten(c, slip_pct)
            self.close(bar_idx, "وقف-الوحدة", c, slip_pct)

    def _flatten(self, cur: float, slip_pct: float) -> None:
        if self.state != self.STATE_GRID:
            return
        for cell in self.cells:
            self.realized_total += cell.flatten_usd(cur, slip_pct)
            self.cycles_total += cell.cycles
        if self.base_qty > 0:
            exit_gross = self.base_qty * cur
            fees = (self.base_qty * self.base_px * C.COMMISSION_PCT
                    + exit_gross * (C.COMMISSION_PCT + slip_pct))
            self.realized_total += (exit_gross
                                    - self.base_qty * self.base_px) - fees
            self.base_qty = 0.0
        self.cells = []

    def close(self, bar_idx: int, reason: str, cur: float,
              slip_pct: float) -> None:
        if self.closed:
            return
        if self.state == self.STATE_GRID:
            self._flatten(cur, slip_pct)
        self.closed = True
        self.close_bar = bar_idx
        self.close_reason = reason
        self.state = self.STATE_FLAT

    # ------------------------------------------------------------- accounting
    @property
    def cycles(self) -> int:
        return self.cycles_total + sum(c.cycles for c in self.cells)

    @property
    def net_usd(self) -> float:
        """Realized $ over the whole unit life (all builds)."""
        return self.realized_total + sum(c.realized_usd for c in self.cells)

    def unrealized_usd(self, cur: float | None = None) -> float:
        cur = self._cur if cur is None else cur
        u = sum(c.unrealized_usd(cur) for c in self.cells)
        if self.base_qty > 0:
            cost = self.base_qty * self.base_px
            u += (self.base_qty * cur - cost) - cost * C.COMMISSION_PCT
        return u

    def total_net_usd(self) -> float:
        return self.net_usd + self.unrealized_usd()


def _spacing_atr_1m(df: pd.DataFrame) -> np.ndarray:
    """ATR at the regime timeframe (the decision scale), causally mapped onto
    the frame timeline (shared causal helper — no lookahead)."""
    return ind.atr_regime_tf_1m(df)


def _trend_bias_1m(df: pd.DataFrame) -> np.ndarray:
    """Causal trend bias at the regime timeframe: +1 if the close is above the
    EMA200 (higher TF), -1 below, 0 unknown. Same close-vs-EMA proxy class as
    the KAMA/ALMA read — only completed higher bars (shift(1) + ffill)."""
    rule = {"5m": "5min", "15m": "15min"}.get(C.REGIME_TF, C.REGIME_TF)
    r = ind.resample_higher(df, rule)
    e = ind.ema(r["close"], 200).shift(1).reindex(df.index, method="ffill")
    bias = np.zeros(len(df), dtype=np.int8)
    e = e.to_numpy(dtype=float)
    c = df["close"].to_numpy(dtype=float)
    ok = np.isfinite(e) & np.isfinite(c) & (e > 0)
    bias[ok] = np.where(c[ok] > e[ok], 1, -1)
    return bias


def replay_dynamic_grid(mat) -> list[dict]:
    """One DGT research unit per contiguous CHOP regime run (same granularity
    as the static grid replay, for direct Static vs Dynamic comparison)."""
    from .oracle import RegimeTransitions
    arr = mat.arr
    o, h, l, c = arr["open"], arr["high"], arr["low"], arr["close"]
    vr = arr.get("vr")
    idx = mat.df.index
    n = mat.n
    look = C.GRID_RANGE_LOOKBACK_BARS
    atr_tf = _spacing_atr_1m(mat.df)
    # trend bias for the optional asymmetric mode (causal 15m EMA200 proxy)
    bias_arr = _trend_bias_1m(mat.df) if C.DGT_ASYMMETRIC else None

    def _slip(bar_i: int) -> float:
        ref = bar_i - 1 if bar_i > 0 else bar_i
        value = None
        if vr is not None and 0 <= ref < n and np.isfinite(float(vr[ref])):
            value = float(vr[ref])
        return market_cost_pct(value, C.REGIME_CHOP)

    recs: list[dict] = []
    units_started = 0
    # NOVA-DGT-HARVESTER: pre-collect all eligible CHOP segments, rank by
    # quality (longer life + mid-tight span sweet-zone) and farm best N only.
    _qg = os.getenv("NOVA_DGT_QG", "1") == "1"
    _qg_min_bars = int(os.getenv("NOVA_DGT_QG_MINBARS", "576"))
    _qg_adx_max = float(os.getenv("NOVA_DGT_QG_ADXMAX", "22"))
    _adx_tf = None
    if _qg:
        from . import indicators as _ind
        _adx_tf = _ind.adx(mat.df, C.ADX_LEN).to_numpy(float)
    candidates = []
    for seg in RegimeTransitions.segments(mat.regime):
        if seg["regime"] not in C.CHOP_GRID_REGIMES:
            continue
        s_pos = int(idx.searchsorted(seg["start"], side="left"))
        e_pos = int(idx.searchsorted(seg["end"], side="right")) - 1
        if e_pos - s_pos < C.DGT_MIN_LIFE_BARS or s_pos < look:
            continue
        if _qg:
            if (e_pos - s_pos) < _qg_min_bars:
                continue
            adx_ref = (_adx_tf[s_pos - 1]
                       if 0 <= s_pos - 1 < n and np.isfinite(_adx_tf[s_pos - 1])
                       else None)
            if adx_ref is None or adx_ref > _qg_adx_max:
                continue
        lo0 = float(np.nanmin(l[s_pos - look:s_pos]))
        hi0 = float(np.nanmax(h[s_pos - look:s_pos]))
        mid0 = (lo0 + hi0) / 2.0
        span0 = (hi0 - lo0) / mid0 if mid0 > 0 else 0.0
        if not (C.GRID_RANGE_MIN_PCT <= span0 <= C.GRID_RANGE_MAX_PCT):
            continue
        life = e_pos - s_pos
        sweet = 1.0 - min(abs(span0 * 100 - 3.5) / 6.0, 1.0)
        candidates.append((life * (0.5 + sweet), s_pos, e_pos, lo0, hi0))
    candidates.sort(key=lambda t: t[0], reverse=True)
    for _score, s_pos, e_pos, lo, hi in candidates[:C.DGT_MAX_UNITS_PER_SYMBOL]:
        unit = DynamicGridUnit(mat.symbol, s_pos, C.DGT_CAPITAL_USD)
        a0 = (float(atr_tf[s_pos - 1])
              if 0 <= s_pos - 1 < n and np.isfinite(atr_tf[s_pos - 1])
              else None)
        b0 = (int(bias_arr[s_pos - 1]) if bias_arr is not None
              and 0 <= s_pos - 1 < n else 0)
        if not unit.build(s_pos, float(c[s_pos - 1]), a0, lo, hi,
                          float(o[s_pos]), _slip(s_pos), bias=b0):
            continue
        for j in range(s_pos, min(e_pos + 1, n)):
            if unit.closed:
                break
            if (unit.state == DynamicGridUnit.STATE_FLAT
                    and j >= unit.rebuild_at
                    and not getattr(unit, "_frozen", False)):
                lo2 = float(np.nanmin(l[max(0, j - look):j]))
                hi2 = float(np.nanmax(h[max(0, j - look):j]))
                mid2 = (lo2 + hi2) / 2.0
                span2 = (hi2 - lo2) / mid2 if mid2 > 0 else 0.0
                aj = (float(atr_tf[j - 1])
                      if 0 <= j - 1 < n and np.isfinite(atr_tf[j - 1])
                      else None)
                # NOVA-DGT-FLEX: before force-closing, try widening the
                # window once (20% more bars) — a borderline range often
                # becomes valid; avoids costly forced market exits.
                _lo2, _hi2 = lo2, hi2
                if not (C.GRID_RANGE_MIN_PCT <= span2 <= C.GRID_RANGE_MAX_PCT):
                    _w = int((j - max(0, j - look)) * 1.2) + 1
                    lo2b = float(np.nanmin(l[max(0, j - _w):j]))
                    hi2b = float(np.nanmax(h[max(0, j - _w):j]))
                    mid2b = (lo2b + hi2b) / 2.0
                    span2b = (hi2b - lo2b) / mid2b if mid2b > 0 else 0.0
                    if (C.GRID_RANGE_MIN_PCT <= span2b <= C.GRID_RANGE_MAX_PCT):
                        _lo2, _hi2 = lo2b, hi2b
                if not (C.GRID_RANGE_MIN_PCT <= span2 <= C.GRID_RANGE_MAX_PCT) \
                        and _lo2 == lo2:
                    # NOVA-DGT-FLEX2: a too-narrow range is still tradable if
                    # the price sits inside it — build a tighter grid there
                    # instead of a costly forced exit. Only a too-WILD range
                    # (span > MAX) stays a close reason.
                    if span2 < C.GRID_RANGE_MIN_PCT \
                            and _lo2 < float(c[j - 1]) < _hi2:
                        pass
                    elif os.getenv("NOVA_DGT_NOCLOSE", "0") == "1":
                        unit._frozen = True   # keep cells; stop rebuild attempts
                    else:
                        unit.close(j, "نطاق-غير-صالح", float(c[j - 1]), _slip(j))
                        break
                bj = (int(bias_arr[j - 1]) if bias_arr is not None
                      and 0 <= j - 1 < n else 0)
                unit.build(j, float(c[j - 1]), aj, _lo2, _hi2,
                           float(o[j]), _slip(j), bias=bj)
            unit.on_bar(float(o[j]), float(h[j]), float(l[j]),
                        float(c[j]), j, _slip(j))
        if not unit.closed:
            close_i = min(e_pos, n - 1)
            unit.close(close_i, "نهاية-الحالة", float(c[close_i]),
                       _slip(close_i))
        if unit.bars < C.DGT_MIN_LIFE_BARS:
            continue
        units_started += 1
        recs.append({
            "category": C.CAT_DYNAMIC_GRID, "kind": "dynamic_grid",
            "strategy": "dynamic_grid", "symbol": mat.symbol,
            "regime": C.REGIME_CHOP, "trigger": "", "side": 0,
            "entry_bar": s_pos, "exit_bar": unit.close_bar or e_pos,
            "entry_time": pd.Timestamp(idx[s_pos]).isoformat(),
            "exit_time": pd.Timestamp(idx[unit.close_bar or e_pos]).isoformat(),
            "bars_held": (unit.close_bar or e_pos) - s_pos,
            "net_frac": (float(unit.net_usd) / C.DGT_CAPITAL_USD if C.DGT_CAPITAL_USD > 0 else 0.0),
            "pnl_usd": unit.net_usd,
            "notional_usd": C.DGT_CAPITAL_USD,
            "reason": unit.close_reason, "cycles": unit.cycles,
            "success": bool(unit.net_usd > 0),
            "risk_accepted": True, "risk_reason": "",
            "risk_would_block": False,
            "entry_px": None, "entry_ref_px": None, "entry_cost_pct": None,
            "exit_px": None, "mult": 1, "experiment": C.EXPERIMENT_NAME,
            "series": 0,
            "snapshot": json.dumps({"resets": unit.resets,
                                    "capital": C.DGT_CAPITAL_USD},
                                   ensure_ascii=False),
        })
    return recs
