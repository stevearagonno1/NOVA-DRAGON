"""Module — Spot Grid mode for choppy/quiet markets.

A grid opens when a symbol's regime turns CHOP. It buys at lower price levels
inside a recently-defined range and sells at the next higher level, harvesting
repeated small profits from oscillation (no directional view).

Accounting is in US dollars on a fixed per-grid deployed capital
(C.GRID_CAPITAL_USD) split evenly across the cells. Each cell buys a fixed
quantity at its lower level and sells the same quantity at the next higher
level; each completed buy->sell cycle books a realized net $. Open cells are
flattened at the last price when the grid closes, so a grid is recorded as ONE
research unit with a single net P&L (per design).
"""
from __future__ import annotations

from . import config as C

# fees on one completed buy+sell cycle are applied on both notional legs
_BUY_FEE = C.COMMISSION_PCT
_SELL_FEE = C.COMMISSION_PCT + C.SLIPPAGE_PCT


class _Cell:
    __slots__ = ("buy", "sell", "qty", "open", "realized_usd", "cycles")

    def __init__(self, buy: float, sell: float, notional: float):
        self.buy = buy
        self.sell = sell
        self.qty = notional / buy if buy > 0 else 0.0
        self.open = False
        self.realized_usd = 0.0   # net $ realized from completed cycles
        self.cycles = 0

    def on_bar(self, o: float, h: float, l: float, c: float) -> None:
        if not self.open:
            if l <= self.buy:
                self.open = True          # buy fills at limit -> held qty
        else:
            if h >= self.sell:
                # sell the held qty at the upper limit -> realized cycle
                buy_cost = self.qty * self.buy
                sell_gross = self.qty * self.sell
                fees = buy_cost * _BUY_FEE + sell_gross * _SELL_FEE
                self.realized_usd += (sell_gross - buy_cost) - fees
                self.cycles += 1
                self.open = False

    # unrealized $ of a currently-open (bought, unsold) position at price `cur`
    def unrealized_usd(self, cur: float) -> float:
        if not self.open:
            return 0.0
        buy_cost = self.qty * self.buy
        return (self.qty * cur - buy_cost) - buy_cost * _BUY_FEE

    def flatten_usd(self, cur: float) -> float:
        """Book the exit of an open cell at market (adds exit fee+slippage)."""
        if not self.open:
            return 0.0
        buy_cost = self.qty * self.buy
        exit_gross = self.qty * cur
        fees = buy_cost * _BUY_FEE + exit_gross * _SELL_FEE
        pnl = (exit_gross - buy_cost) - fees
        self.open = False
        return pnl


class Grid:
    """One active spot grid on a symbol (recorded as a single research unit)."""

    def __init__(self, symbol: str, start_bar: int, lo: float, hi: float,
                 start_price: float):
        self.symbol = symbol
        self.start_bar = start_bar
        self.lo = lo
        self.hi = hi
        self.start_price = start_price
        self.bars = 0
        self.last_price = start_price
        self.cells: list[_Cell] = []
        self.closed = False
        self.close_bar = None
        self.close_reason = ""
        self._flat_usd = 0.0          # realized losses of forced flatten events
        self._build()

    def _nlevels(self) -> int:
        # number of price levels is configurable, clamped into GRID_LEVELS_MIN/MAX
        return max(C.GRID_LEVELS_MIN, min(C.GRID_LEVELS_DEFAULT, C.GRID_LEVELS_MAX))

    def _build(self) -> None:
        nlevels = self._nlevels()
        span = self.hi - self.lo
        step = span / (nlevels - 1) if nlevels > 1 and span > 0 else span
        levels = [self.lo + step * i for i in range(nlevels)]
        notional = C.GRID_CAPITAL_USD / (nlevels - 1)
        for i in range(nlevels - 1):
            self.cells.append(_Cell(levels[i], levels[i + 1], notional))

    # ------------------------------------------------------------- computed
    @property
    def cycles(self) -> int:
        return sum(c.cycles for c in self.cells)

    @property
    def open_cells(self) -> int:
        return sum(1 for c in self.cells if c.open)

    @property
    def net_usd(self) -> float:
        """Net $ over the grid life: realized cycles + flatten of open cells."""
        return self._flat_usd + sum(c.realized_usd for c in self.cells)

    # --------------------------------------------------------------- update
    def on_bar(self, o: float, h: float, l: float, c: float,
               bar_idx: int) -> None:
        if self.closed:
            return
        self.bars += 1
        self.last_price = c
        for cell in self.cells:
            cell.on_bar(o, h, l, c)
        # range-break: price escaping the band is no longer a range -> flatten
        if c > self.hi * 1.02 or c < self.lo * 0.98:
            self.close(bar_idx, "خروج-من-النطاق", c)

    def close(self, bar_idx: int, reason: str, cur: float) -> None:
        if self.closed:
            return
        self.last_price = cur
        for cell in self.cells:
            self._flat_usd += cell.flatten_usd(cur)
        self.closed = True
        self.close_bar = bar_idx
        self.close_reason = reason
