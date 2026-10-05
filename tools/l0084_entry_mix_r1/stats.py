#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0084-ENTRY-MIX — statistics: Wilson, 7-day block bootstrap, Holm, power.

Bootstrap: 2,000 moving-block replicates, synchronised seven-UTC-day blocks
across all 12 assets, empty days included, concatenation to original window
length then trim, seed 84.  Paired comparisons reuse identical blocks.
Holm family per window: m = 52 + 3*C(52,2) + 3*C(52,3) = 70,330, untested
members assigned p = 1.  One-sided 95% bounds are the 5th percentile.
"""
from __future__ import annotations

import numpy as np
from scipy import stats as sstats

SEED = 84
REPS = 2000
BLOCK_DAYS = 7
DAY = 86400.0

Z95 = 1.6448536269514722      # one-sided 95%
Z80 = 0.8416212335729143
Z975 = 1.959963984540054


def counts_per_day(days, net, n_days):
    """day index -> (sum net, count) arrays of length n_days."""
    s = np.zeros(n_days)
    c = np.zeros(n_days)
    if len(days):
        np.add.at(s, days, net)
        np.add.at(c, days, 1.0)
    return s, c


def _sample_index_matrix(rng, n_days, reps):
    """Vectorised bootstrap draw: (reps, n_days) day indices; 7-day blocks
    concatenated to the original length then trimmed (non-wrapping)."""
    if n_days <= BLOCK_DAYS:
        return rng.integers(0, n_days, size=(reps, n_days))
    nb = int(np.ceil(n_days / BLOCK_DAYS))
    starts = rng.integers(0, n_days - BLOCK_DAYS + 1, size=(reps, nb))
    idx = (starts[:, :, None] + np.arange(BLOCK_DAYS)[None, None, :])
    idx = idx.reshape(reps, -1)[:, :n_days]
    return idx


def block_ci(days, net, n_days, reps=REPS, seed=SEED):
    """One-sided lower bound (5%) and two-sided 95% interval of expectancy."""
    s, c = counts_per_day(days, net, n_days)
    if c.sum() == 0:
        return dict(expectancy=np.nan, lo5=np.nan, hi95=np.nan, se=np.nan,
                    n=0, n_days=n_days)
    rng = np.random.default_rng(seed)
    idx = _sample_index_matrix(rng, n_days, reps)
    ss = s[idx].sum(axis=1)
    cc = c[idx].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        vals = np.where(cc > 0, ss / cc, np.nan)
    vals = vals[np.isfinite(vals)]
    return dict(expectancy=float(s.sum() / c.sum()),
                lo5=float(np.percentile(vals, 5)),
                hi95=float(np.percentile(vals, 95)),
                se=float(np.std(vals, ddof=1)),
                n=int(c.sum()), n_days=n_days)


def paired_block_diff(days_a, net_a, days_b, net_b, n_days,
                      reps=REPS, seed=SEED):
    """Paired expectancy difference (A - B) on identical day blocks."""
    sa, ca = counts_per_day(days_a, net_a, n_days)
    sb, cb = counts_per_day(days_b, net_b, n_days)
    rng = np.random.default_rng(seed)
    idx = _sample_index_matrix(rng, n_days, reps)
    caa = ca[idx].sum(axis=1)
    cbb = cb[idx].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        diffs = np.where((caa > 0) & (cbb > 0),
                         sa[idx].sum(axis=1) / caa - sb[idx].sum(axis=1) / cbb,
                         np.nan)
    diffs = diffs[np.isfinite(diffs)]
    obs = (sa.sum() / ca.sum() if ca.sum() else np.nan) - \
          (sb.sum() / cb.sum() if cb.sum() else np.nan)
    return dict(diff=float(obs), lo5=float(np.percentile(diffs, 5)),
                hi95=float(np.percentile(diffs, 95)),
                se=float(np.std(diffs, ddof=1)) if len(diffs) > 1 else np.nan)


def wilson(k, n, z=Z975):
    if n == 0:
        return (np.nan, np.nan, np.nan)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return float(p), float(centre - half), float(centre + half)


def pf(net):
    pos = float(net[net > 0].sum())
    neg = -float(net[net < 0].sum())
    if neg == 0:
        return float("inf") if pos > 0 else np.nan
    return pos / neg


def two_proportion_z(k1, n1, k2, n2):
    if n1 == 0 or n2 == 0:
        return (np.nan, np.nan)
    p1, p2 = k1 / n1, k2 / n2
    p = (k1 + k2) / (n1 + n2)
    se = np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return (np.nan, np.nan)
    z = (p1 - p2) / se
    return float(z), float(2 * (1 - sstats.norm.cdf(abs(z))))


def holm(pvals, m):
    """Holm step-down with m hypotheses; untested members enter with p=1.

    Returns adjusted p-values aligned with the input order.
    """
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    for rank, idx in enumerate(order):
        val = min(1.0, p[idx] * (m - rank))
        running = max(running, val)
        adj[idx] = running
    return adj


def z_from_lb(lb, expectancy, se):
    """One-sided p-value from the bootstrap distribution summary."""
    if not np.isfinite(se) or se <= 0:
        return np.nan
    z = expectancy / se
    return float(1 - sstats.norm.cdf(z))


def power_n(effect, per_trade_sd, se_boot, n_obs, alpha):
    """Runnable 80%-power sample-size search (documented approximation).

    iid estimate n0 = ((z_a + z_80) * sd / effect)^2 scaled by the dependence
    factor k = (SE_boot / (sd/sqrt(n_obs)))^2, then a search verifies the
    normal-approximation power at the corrected alpha.
    """
    if (not np.isfinite(se_boot) or se_boot <= 0 or n_obs < 3
            or not np.isfinite(per_trade_sd) or per_trade_sd <= 0
            or not np.isfinite(effect)):
        return dict(n80=None, power_at_n=None, approximation="not available")
    iid_se = per_trade_sd / np.sqrt(n_obs)
    k = (se_boot / iid_se) ** 2
    z_a = sstats.norm.ppf(1 - alpha)
    n80 = int(np.ceil(((z_a + Z80) ** 2) * k * (per_trade_sd ** 2)
                      / (effect ** 2)))
    n80 = max(n80, 2)
    power = float(sstats.norm.cdf(effect * np.sqrt(n80 / k) / per_trade_sd
                                  - z_a))
    return dict(n80=n80, power_at_n=power, dependence_factor=float(k),
                approximation="normal; iid SE scaled by block-bootstrap "
                              "dependence factor")


def max_drawdown(equity):
    eq = np.asarray(equity, float)
    if len(eq) == 0:
        return 0.0, 0
    peak = np.maximum.accumulate(eq)
    dd = peak - eq
    mdd = float(dd.max())
    if mdd <= 0:
        return 0.0, 0
    end = int(np.argmax(dd))
    dur = 0
    for k in range(end, -1, -1):
        if eq[k] >= peak[end]:
            dur = end - k
            break
    return mdd, dur
