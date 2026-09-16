"""Wyckoff/SMC entry-confirmation gate (specs 8.9/8.10) — an optional,
toggleable feature (NOVA_SMC_GATE) applied inside Directional and Long-Cycle.

The approved design keeps Wyckoff/SMC as *context features*, not new
strategies, and without duplicating the existing MSS/FVG/SFP trigger set.
This module implements the strictest, most testable subset of the two specs:

  1) SWEEP FIRST (spec 8.10): within the lookback window some bar broke the
     recent swing extreme (liquidity above highs / below lows) and closed
     back inside it — a stop-run that the market absorbed;
  2) DISCOUNT / PREMIUM (spec 8.10): the decision close sits in the cheap
     half (long) or the rich half (short) of the recent range;
  3) SOS / SOW (spec 8.9 "لا دخول قبل SOS"): a close beyond the prior
     window extreme (a strength / weakness break) has already occurred —
     no entries inside a structureless range.

All three are required (the "quadruple-confluence" spirit: Sweep + location
+ structure). Everything is causal: evaluated on the decision bar's closed
values only; the frame's own bars (1m for Directional, 4h for Long-Cycle).
Off by default — the Baseline is untouched.
"""
from __future__ import annotations

import numpy as np


def _swept_long(l: np.ndarray, c: np.ndarray, k0: int, j: int) -> bool:
    for m in range(k0 + 1, j + 1):
        prior = float(np.nanmin(l[k0:m]))
        if l[m] < prior and c[m] > prior:
            return True
    return False


def _swept_short(h: np.ndarray, c: np.ndarray, k0: int, j: int) -> bool:
    for m in range(k0 + 1, j + 1):
        prior = float(np.nanmax(h[k0:m]))
        if h[m] > prior and c[m] < prior:
            return True
    return False


def smc_confirm(h: np.ndarray, l: np.ndarray, c: np.ndarray, j: int,
                side: int, lookback: int = 50) -> bool:
    """Causal Wyckoff/SMC entry confirmation on closed bar ``j``.

    Returns True only when ALL three conditions hold on the window
    [j-lookback, j]; False otherwise (including NaN/incomplete windows).
    """
    k0 = max(0, j - lookback)
    if j - k0 < 10:                              # need a real window
        return False
    win = np.concatenate([h[k0:j + 1], l[k0:j + 1], c[k0:j + 1]])
    if not np.all(np.isfinite(win)):
        return False
    if side == 1:
        sweep = _swept_long(l, c, k0, j)
        win_lo = float(np.nanmin(l[k0:j + 1]))
        win_hi = float(np.nanmax(h[k0:j + 1]))
        discount = c[j] < (win_lo + win_hi) / 2.0
        sos = False
        for m in range(k0 + 1, j + 1):
            if c[m] > float(np.nanmax(h[k0:m])):
                sos = True
                break
        return bool(sweep and discount and sos)
    sweep = _swept_short(h, c, k0, j)
    win_lo = float(np.nanmin(l[k0:j + 1]))
    win_hi = float(np.nanmax(h[k0:j + 1]))
    premium = c[j] > (win_lo + win_hi) / 2.0
    sow = False
    for m in range(k0 + 1, j + 1):
        if c[m] < float(np.nanmin(l[k0:m])):
            sow = True
            break
    return bool(sweep and premium and sow)
