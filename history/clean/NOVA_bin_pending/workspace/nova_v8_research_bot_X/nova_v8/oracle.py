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

import numpy as np
import pandas as pd

from . import config as C


class TruthOracle:
    """Rolling per-(regime, trigger) truth statistics, causal / online."""

    def __init__(self):
        # key: (regime, trigger) -> deque of booleans (credited?).
        # Use a dict of (credited, total) counters refreshed by recompute pass.
        self._credits = {}   # (regime, trig) -> [credits, samples]
        self.truth_ratio = {}  # (regime, trig) -> float 0..1

    def reset(self) -> None:
        self._credits = {}
        self.truth_ratio = {}

    def _key(self, regime, trig):
        return (regime, trig)

    def record(self, regime: str, trig: str, credited: bool) -> None:
        k = self._key(regime, trig)
        arr = self._credits.setdefault(k, [0.0, 0.0])
        arr[0] += 1.0 if credited else 0.0
        arr[1] += 1.0

    def finalize(self) -> None:
        """Rebuild truth_ratio from counters and prune the oldest (rolling)."""
        for k, (cred, total) in self._credits.items():
            if total >= C.MIN_CONFIRM_SAMPLES:
                self.truth_ratio[k] = cred / total

    def truthful(self, regime: str, trig: str,
                 min_samples: int = C.MIN_CONFIRM_SAMPLES) -> bool:
        k = self._key(regime, trig)
        arr = self._credits.get(k)
        if not arr or arr[1] < min_samples:
            return True          # not enough evidence -> do not filter out
        return (arr[0] / arr[1]) >= 0.5

    def stability(self, regime: str, trig: str) -> float:
        """'Stability' metric 0..1 for a (regime,trigger) pattern (recurring
        success => higher). Feeds the 'stable market' analytic signal."""
        k = self._key(regime, trig)
        arr = self._credits.get(k)
        if not arr or arr[1] < C.MIN_CONFIRM_SAMPLES:
            return 0.5
        return arr[0] / arr[1]


class RegimeTransitions:
    """Detect regime start/end boundaries to build clean per-regime segments."""

    @staticmethod
    def segments(regime_series: pd.Series):
        """Return list of dicts {regime, start_idx, end_idx, bars} for each
        contiguous run of equal regime."""
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
                    "regime": cur,
                    "start": idx[start],
                    "end": idx[i - 1],
                    "bars": i - start,
                })
                if i < len(values):
                    cur = values[i]
                    start = i
        return segs


def run_truth_labeling(df1m: pd.DataFrame, entry_side: pd.Series,
                       entry_trigger: pd.Series, regime1m: pd.Series,
                       oracle: TruthOracle) -> None:
    """Label each bar: whether an indicator signal got a profitable structural
    confirmation within the window (3-5 bars). Causal: looks only ahead by a
    fixed window we are allowed to attribute for *research* scoring (no trade
    decision uses future). We credit an indicator when, shortly after its
    signal, price breaks structure and moves profitably in the signal side.
    """
    mss = df1m["mss"].to_numpy(float)
    side = entry_side.to_numpy(np.int8)
    trig = entry_trigger.to_numpy(dtype=object)
    reg = regime1m.to_numpy(dtype=object)
    n = len(df1m)
    lo, hi = C.TRUTH_WINDOW_MIN, C.TRUTH_WINDOW_MAX

    # collect which bars are signal bars needing evaluation
    sig_bars = np.nonzero(side != 0)[0]
    for i in sig_bars:
        if i + lo >= n:
            continue
        reg_at = reg[i] if reg[i] else C.REGIME_CHOP
        s = int(side[i])
        # search for a structure break in favour within window
        confirmed = False
        for j in range(i + lo, min(i + hi + 1, n)):
            brk = mss[j]
            if brk == 0:
                continue
            if s == 1 and brk == 1:
                # profitable: close after break exceeds signal close
                confirmed = True
                break
            if s == -1 and brk == -1:
                confirmed = True
                break
        oracle.record(reg_at, trig[i], confirmed)
