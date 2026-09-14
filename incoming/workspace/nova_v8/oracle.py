"""Module — Structure Truth Oracle + regime transition record.

Design decisions implemented here:
  * MSS/FVG structure breaks act as a *truth reference* for entry indicators.
  * For each indicator signal, if a structurally "profitable break" follows
    within a short confirmation window (3-5 bars), the indicator is credited
    as truthful in that market state.
  * Truth is computed on a rolling recent window (self-adapting).
  * "Learning from precedents": recurring, validated patterns become a basis
    for reading the market (regime stability signal).
  * Regime-transition detector: tags the exact bars where a regime begins /
    ends so results can be grouped into clean per-regime periods.
"""
from __future__ import annotations

from collections import deque

import numpy as np
import pandas as pd

from . import config as C


class TruthOracle:
    """Rolling (recent-window) truth statistics per (regime, trigger).

    Each key keeps a ring buffer of the last C.TRUTH_ROLL credit outcomes, so
    "truth" reflects the *recent* window only (self-adapting), as the design
    requires ("نسبة الصدق تتجدّد زمنياً بنافذة متحركة حديثة"). Bounded memory.
    """

    def __init__(self):
        self._buf: dict[tuple, deque] = {}     # (regime, trig) -> deque of bool
        self.truth_ratio: dict[tuple, float] = {}

    def reset(self) -> None:
        self._buf = {}
        self.truth_ratio = {}

    def _key(self, regime, trig):
        return (regime, trig)

    def _buf_for(self, k):
        b = self._buf.get(k)
        if b is None:
            b = deque(maxlen=C.TRUTH_ROLL)
            self._buf[k] = b
        return b

    def record(self, regime, trig, credited: bool) -> None:
        self._buf_for(self._key(regime, trig)).append(1.0 if credited else 0.0)

    def _samples(self, k):
        b = self._buf.get(k)
        return (len(b), float(sum(b))) if b else (0, 0.0)

    def finalize(self) -> None:
        for k, b in self._buf.items():
            if b and len(b) >= C.MIN_CONFIRM_SAMPLES:
                self.truth_ratio[k] = float(sum(b)) / len(b)

    def truthful(self, regime, trig,
                 min_samples: int = C.MIN_CONFIRM_SAMPLES) -> bool:
        k = self._key(regime, trig)
        n, cred = self._samples(k)
        if n < min_samples:
            return True          # not enough evidence -> do not filter out
        return (cred / n) >= 0.5

    def stability(self, regime, trig) -> float:
        k = self._key(regime, trig)
        n, cred = self._samples(k)
        if n < C.MIN_CONFIRM_SAMPLES:
            return 0.5
        return cred / n


class RegimeTransitions:
    """Detect regime start/end boundaries to build clean per-regime segments."""

    @staticmethod
    def segments(regime_series: pd.Series):
        segs = []
        if len(regime_series) == 0:
            return segs
        values = regime_series.to_numpy()
        idx = regime_series.index
        start = 0
        cur = values[0]
        for i in range(1, len(values) + 1):
            if i == len(values) or values[i] != cur:
                segs.append({
                    "regime": cur, "start": idx[start], "end": idx[i - 1],
                    "bars": i - start,
                })
                if i < len(values):
                    cur = values[i]
                    start = i
        return segs


def run_truth_labeling(df1m: pd.DataFrame, entry_side: pd.Series,
                       entry_trigger: pd.Series, regime1m: pd.Series,
                       oracle: TruthOracle) -> None:
    """Label each signal with whether it led to a *profitable* structure break.

    For a long signal at bar i: within the confirmation window a bullish
    structure event (an MSS up-shift OR a fresh bullish FVG imbalance) must
    appear, and THEN price must actually move up profitably within a short
    extra window. Only then is the indicator credited as truthful. This looks
    ahead by a fixed, bounded window — allowed for *research scoring* only (no
    trade decision uses it). Results are kept in the oracle's rolling buffer.
    """
    mss = df1m["mss"].to_numpy(float)
    fvg_bull = df1m.get("fvg_bull")
    fvg_bear = df1m.get("fvg_bear")
    fvg_bull = fvg_bull.fillna(False).to_numpy(bool) if fvg_bull is not None else None
    fvg_bear = fvg_bear.fillna(False).to_numpy(bool) if fvg_bear is not None else None
    close = df1m["close"].to_numpy(float)
    side = entry_side.to_numpy(np.int8)
    trig = entry_trigger.to_numpy(dtype=object)
    reg = regime1m.to_numpy(dtype=object)
    n = len(df1m)
    lo, hi = C.TRUTH_WINDOW_MIN, C.TRUTH_WINDOW_MAX
    extra = C.TRUTH_PROFIT_EXTRA_BARS
    margin = C.TRUTH_PROFIT_MIN_MOVE

    for i in np.nonzero(side != 0)[0]:
        if i + lo >= n:
            continue
        reg_at = reg[i] if reg[i] else C.REGIME_CHOP
        s = int(side[i])
        # 1) find a favourable structure break within the confirmation window
        found = -1
        for j in range(i + lo, min(i + hi + 1, n)):
            if s == 1:
                ok = (mss[j] == 1) or (fvg_bull is not None and fvg_bull[j])
            else:
                ok = (mss[j] == -1) or (fvg_bear is not None and fvg_bear[j])
            if ok:
                found = j
                break
        credited = False
        if found != -1:
            # 2) the break must actually be followed by a profitable move
            entry_ref = close[i]
            scan_end = min(found + extra + 1, n)
            for k in range(found + 1, scan_end):
                if not np.isfinite(close[k]):
                    continue
                if s == 1 and (close[k] - entry_ref) / max(entry_ref, 1e-12) > margin:
                    credited = True
                    break
                if s == -1 and (entry_ref - close[k]) / max(entry_ref, 1e-12) > margin:
                    credited = True
                    break
        oracle.record(reg_at, trig[i], credited)
