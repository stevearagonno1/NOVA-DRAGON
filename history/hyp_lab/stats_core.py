"""stats_core — reusable statistical primitives for the NOVA-DRAGON hypothesis lab (L0081 P0).

Everything here is generic and side-effect free so it can be unit-tested on known cases
and reused across lanes. No lane-specific logic, no data loading, no I/O.

Primitives (López de Prado / Bailey lineage):
  concurrency(starts, ends, n_bars)              -> per-bar count of simultaneously-open labels
  average_uniqueness(starts, ends, n_bars)       -> (per_label_uniqueness, mean_uniqueness)
  effective_n(starts, ends, n_bars)              -> sum of per-label uniqueness  (N_eff)
  wilson(k, n, z)                                -> (lo, hi) Wilson score interval
  cpcv_splits(n_groups, k_test, purge, embargo)  -> combinatorial purged CV group partitions + n_paths
  deflated_sharpe_ratio(...)                      -> DSR (Bailey & López de Prado 2014)
  probability_of_backtest_overfitting(M, s)      -> PBO via CSCV (Bailey et al. 2015)
  effective_n_trials(corr)                        -> Li & Ji (2005) effective number of independent tests
  free_filter_bound(concurrency)                 -> 1 / concurrency  (independence-preserving retain fraction)

Run `python3 stats_core.py` to execute the unit tests (G0 gate).
"""
from __future__ import annotations
import math
from itertools import combinations
import numpy as np

EULER_GAMMA = 0.5772156649015329


# --------------------------------------------------------------------------- labels / uniqueness
def concurrency(starts, ends, n_bars):
    """Number of labels overlapping each bar. A label spans bars [start, end] inclusive.
    starts/ends are integer bar indices (same length). Counts are within ONE series
    (e.g. one symbol) — caller loops symbols and never counts cross-symbol overlap."""
    starts = np.asarray(starts, dtype=int)
    ends = np.asarray(ends, dtype=int)
    c = np.zeros(int(n_bars) + 1, dtype=float)
    for s, e in zip(starts, ends):
        s = max(0, s); e = min(int(n_bars) - 1, e)
        if e < s:
            continue
        c[s] += 1.0
        c[e + 1] -= 1.0
    return np.cumsum(c)[:int(n_bars)]


def average_uniqueness(starts, ends, n_bars):
    """Per-label average uniqueness = mean over the label's bars of 1/concurrency(bar).
    Returns (uniqueness_per_label array, mean_uniqueness)."""
    starts = np.asarray(starts, dtype=int)
    ends = np.asarray(ends, dtype=int)
    c = concurrency(starts, ends, n_bars)
    inv = np.zeros_like(c)
    nz = c > 0
    inv[nz] = 1.0 / c[nz]
    u = np.empty(len(starts), dtype=float)
    for i, (s, e) in enumerate(zip(starts, ends)):
        s = max(0, s); e = min(int(n_bars) - 1, e)
        if e < s:
            u[i] = np.nan
            continue
        u[i] = inv[s:e + 1].mean()
    mean_u = float(np.nanmean(u)) if len(u) else np.nan
    return u, mean_u


def effective_n(starts, ends, n_bars):
    """Effective number of ~independent observations = sum of per-label uniqueness."""
    u, _ = average_uniqueness(starts, ends, n_bars)
    return float(np.nansum(u))


def effective_n_multi(per_series):
    """N_eff aggregated across independent series (symbols).
    per_series: iterable of (starts, ends, n_bars). Returns (N_eff_total, N_labels_total, mean_uniqueness)."""
    tot_neff = 0.0; tot_n = 0
    for starts, ends, n_bars in per_series:
        if len(starts) == 0:
            continue
        u, _ = average_uniqueness(starts, ends, n_bars)
        tot_neff += float(np.nansum(u))
        tot_n += int(np.isfinite(u).sum())
    mean_u = tot_neff / tot_n if tot_n else np.nan
    return tot_neff, tot_n, mean_u


# --------------------------------------------------------------------------- Wilson
def wilson(k, n, z=1.96):
    """Wilson score confidence interval for a binomial proportion k/n."""
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    rad = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((centre - rad) / denom, (centre + rad) / denom)


def wilson_p(p, n, z=1.96):
    """Wilson interval given a proportion p and an (effective) sample size n (may be fractional)."""
    if n <= 0:
        return (float("nan"), float("nan"))
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    rad = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((centre - rad) / denom, (centre + rad) / denom)


# --------------------------------------------------------------------------- CPCV
def cpcv_splits(n_groups, k_test, purge, embargo):
    """Combinatorial Purged Cross-Validation group partitions.
    Returns dict with:
      combos: list of dicts {test_groups, train_groups}
      n_paths: number of backtest paths = C(N,k)*k/N
      params: echoed purge/embargo (in BARS; applied by caller when mapping groups->bars)
    Group->bar mapping and the purge/embargo bar removal are done by the caller because
    only it knows the per-symbol bar layout; this returns the group-level design."""
    groups = list(range(n_groups))
    combos = []
    for test in combinations(groups, k_test):
        test = set(test)
        train = [g for g in groups if g not in test]
        combos.append({"test_groups": sorted(test), "train_groups": train})
    n_paths = int(math.comb(n_groups, k_test) * k_test / n_groups)
    return {"combos": combos, "n_combinations": len(combos), "n_paths": n_paths,
            "purge_bars": int(purge), "embargo_bars": int(embargo),
            "n_groups": n_groups, "k_test": k_test}


def purge_embargo_mask(ts_group, test_group_ids, group_of_bar, purge, embargo, n_bars):
    """Return a boolean 'is_train' mask over bars: True where a bar may be used for training
    given the test groups, with purge+embargo bars around each contiguous test block removed."""
    group_of_bar = np.asarray(group_of_bar)
    is_test = np.isin(group_of_bar, list(test_group_ids))
    is_train = ~is_test
    # remove purge+embargo window around test blocks
    idx = np.flatnonzero(is_test)
    guard = int(purge) + int(embargo)
    for i in idx:
        lo = max(0, i - int(purge))
        hi = min(n_bars - 1, i + guard)
        is_train[lo:hi + 1] = False
    is_train[is_test] = False
    return is_train


# --------------------------------------------------------------------------- Deflated Sharpe
def expected_max_sharpe(sr_std, n_trials):
    """Expected maximum of n_trials i.i.d. Sharpe estimates with cross-trial std sr_std
    (Bailey & López de Prado 2014). Returns the benchmark SR0."""
    if n_trials < 2 or sr_std <= 0:
        return 0.0
    inv = _norm_ppf
    a = inv(1 - 1.0 / n_trials)
    b = inv(1 - 1.0 / (n_trials * math.e))
    return sr_std * ((1 - EULER_GAMMA) * a + EULER_GAMMA * b)


def probabilistic_sharpe_ratio(sr, sr_benchmark, n_obs, skew=0.0, kurt=3.0):
    """PSR: probability that true SR exceeds sr_benchmark, given sample estimate sr.
    sr and sr_benchmark are per-observation (same frequency). kurt is raw kurtosis (normal=3)."""
    if n_obs < 2:
        return float("nan")
    denom = math.sqrt(max(1e-12, 1 - skew * sr + (kurt - 1) / 4.0 * sr * sr))
    z = (sr - sr_benchmark) * math.sqrt(n_obs - 1) / denom
    return _norm_cdf(z)


def deflated_sharpe_ratio(sr, sr_std_trials, n_trials, n_obs, skew=0.0, kurt=3.0):
    """DSR = PSR evaluated against the expected-maximum Sharpe from n_trials (Bailey & LdP 2014).
    sr: observed Sharpe of the selected strategy (per-observation).
    sr_std_trials: std of Sharpe estimates across the trials that were searched.
    Returns DSR in [0,1]; > 0.95 is the lane's bar."""
    sr0 = expected_max_sharpe(sr_std_trials, n_trials)
    return probabilistic_sharpe_ratio(sr, sr0, n_obs, skew, kurt), sr0


# --------------------------------------------------------------------------- PBO via CSCV
def probability_of_backtest_overfitting(M, n_splits=8):
    """CSCV Probability of Backtest Overfitting (Bailey, Borwein, López de Prado, Zhu 2015).
    M: 2D array of per-bar performance, shape (T observations, N strategies/configs).
    Splits the T rows into n_splits contiguous groups; for every way of choosing half the
    groups as IS and the complement as OOS, picks the IS-best strategy and records its OOS
    relative rank. PBO = P(logit(OOS rank of IS-best) <= 0) = fraction of splits where the
    in-sample winner lands in the bottom half out of sample. Returns (pbo, logits list)."""
    M = np.asarray(M, dtype=float)
    T, N = M.shape
    if N < 2:
        return float("nan"), []
    s = n_splits - (n_splits % 2)  # even
    s = max(2, s)
    bounds = np.linspace(0, T, s + 1, dtype=int)
    groups = [np.arange(bounds[i], bounds[i + 1]) for i in range(s)]
    logits = []
    for is_sel in combinations(range(s), s // 2):
        is_idx = np.concatenate([groups[g] for g in is_sel])
        oos_idx = np.concatenate([groups[g] for g in range(s) if g not in is_sel])
        if len(is_idx) == 0 or len(oos_idx) == 0:
            continue
        is_perf = M[is_idx].mean(axis=0)
        oos_perf = M[oos_idx].mean(axis=0)
        n_star = int(np.argmax(is_perf))
        # relative rank of the IS winner among OOS performances
        ranks = oos_perf.argsort().argsort()  # 0..N-1, higher = better
        w = (ranks[n_star] + 1) / (N + 1)     # in (0,1)
        w = min(max(w, 1e-6), 1 - 1e-6)
        logits.append(math.log(w / (1 - w)))
    if not logits:
        return float("nan"), []
    pbo = float(np.mean([1.0 if lam <= 0 else 0.0 for lam in logits]))
    return pbo, logits


# --------------------------------------------------------------------------- effective # trials
def effective_n_trials(corr):
    """Li & Ji (2005) effective number of independent tests from a correlation matrix.
    M_eff = sum_i [ I(|lambda_i| >= 1) + (|lambda_i| - floor(|lambda_i|)) ]."""
    corr = np.asarray(corr, dtype=float)
    if corr.ndim != 2 or corr.shape[0] != corr.shape[1]:
        raise ValueError("corr must be square")
    corr = np.nan_to_num(corr, nan=0.0)
    np.fill_diagonal(corr, 1.0)
    eig = np.linalg.eigvalsh(corr)
    eig = np.abs(eig)
    meff = np.sum((eig >= 1).astype(float) + (eig - np.floor(eig)))
    return float(min(max(meff, 1.0), corr.shape[0]))


def free_filter_bound(conc):
    """Independence-preserving retain fraction = 1/concurrency. Below this you are mostly
    discarding correlated duplicates (nearly free); above it you start discarding
    independent information."""
    if conc is None or conc <= 0:
        return float("nan")
    return 1.0 / conc


# --------------------------------------------------------------------------- normal helpers
def _norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _norm_ppf(p):
    """Acklam's rational approximation to the inverse normal CDF."""
    if p <= 0:
        return -math.inf
    if p >= 1:
        return math.inf
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


# =========================================================================== UNIT TESTS (G0)
def _tests():
    ok = 0; fail = 0; msgs = []

    def check(name, cond):
        nonlocal ok, fail
        if cond:
            ok += 1; msgs.append(f"PASS {name}")
        else:
            fail += 1; msgs.append(f"FAIL {name}")

    # 1. non-overlapping labels -> uniqueness 1.0
    starts = [0, 5, 10]; ends = [4, 9, 14]
    u, mu = average_uniqueness(starts, ends, 15)
    check("uniqueness=1.0 for non-overlapping labels", np.allclose(u, 1.0) and abs(mu - 1.0) < 1e-9)
    check("effective_n == n_labels for non-overlapping", abs(effective_n(starts, ends, 15) - 3.0) < 1e-9)

    # 2. identical labels -> uniqueness -> 1/N ; N_eff -> 1
    N = 20
    s2 = [0] * N; e2 = [9] * N
    u2, mu2 = average_uniqueness(s2, e2, 10)
    check("uniqueness -> 1/N for identical labels", abs(mu2 - 1.0 / N) < 1e-9)
    check("N_eff -> 1 for N identical labels", abs(effective_n(s2, e2, 10) - 1.0) < 1e-9)

    # 3. concurrency correctness
    c = concurrency([0, 2], [3, 5], 6)
    check("concurrency counts overlap", list(c) == [1, 1, 2, 2, 1, 1])

    # 4. Wilson sanity: shrinks toward p as n grows; lo<p<hi
    lo1, hi1 = wilson(60, 100); lo2, hi2 = wilson(600, 1000)
    check("Wilson lo<p<hi", lo1 < 0.6 < hi1)
    check("Wilson tightens with n", (hi2 - lo2) < (hi1 - lo1))
    # smaller n => lower Wilson lower bound (the whole point of the N_eff correction)
    loA, _ = wilson_p(0.52, 6581); loB, _ = wilson_p(0.52, 2015)
    check("Wilson_lo drops when N_eff < nominal", loB < loA)

    # 5. free_filter_bound
    check("free_filter_bound(3.27)~0.306", abs(free_filter_bound(3.27) - 0.30581) < 1e-3)

    # 6. cpcv splits: C(6,2)=15 combos, paths = 15*2/6 = 5
    sp = cpcv_splits(6, 2, 18, 18)
    check("cpcv n_combinations C(6,2)=15", sp["n_combinations"] == 15)
    check("cpcv n_paths = 5", sp["n_paths"] == 5)
    # no leakage: purge+embargo removes bars adjacent to test block from train
    group_of_bar = np.repeat(np.arange(6), 100)  # 600 bars, 6 groups of 100
    tr = purge_embargo_mask(None, [2], group_of_bar, 18, 18, 600)
    test_bars = np.flatnonzero(group_of_bar == 2)
    # bars within purge before and embargo after test group must be excluded from train
    check("cpcv no test bars in train", not tr[test_bars].any())
    check("cpcv purges before test block", not tr[test_bars[0] - 18:test_bars[0]].any())
    check("cpcv embargoes after test block", not tr[test_bars[-1] + 1:test_bars[-1] + 19].any())

    # 7. effective_n_trials: identity corr -> N ; all-ones corr -> 1
    check("effective_n_trials(I_5)=5", abs(effective_n_trials(np.eye(5)) - 5.0) < 1e-6)
    check("effective_n_trials(ones)~1", effective_n_trials(np.ones((5, 5))) < 1.05)

    # 8. DSR: higher n_trials lowers DSR; strong SR still passes vs few trials
    dsr_many, sr0_many = deflated_sharpe_ratio(0.10, 0.03, 100, 1500, 0.0, 3.0)
    dsr_few, sr0_few = deflated_sharpe_ratio(0.10, 0.03, 3, 1500, 0.0, 3.0)
    check("DSR decreases with more trials", dsr_many < dsr_few)
    check("DSR in [0,1]", 0.0 <= dsr_many <= 1.0 and 0.0 <= dsr_few <= 1.0)

    # 9. PBO: independent noise -> ~0.5 ; a genuinely dominant strategy -> low PBO
    rng = np.random.default_rng(0)
    noise = rng.normal(size=(800, 20))
    pbo_noise, _ = probability_of_backtest_overfitting(noise, 8)
    good = rng.normal(size=(800, 20)) * 0.01
    good[:, 0] += 0.05  # strategy 0 dominates everywhere
    pbo_good, _ = probability_of_backtest_overfitting(good, 8)
    check("PBO(noise) ~ 0.5", 0.3 <= pbo_noise <= 0.7)
    check("PBO(dominant) low", pbo_good < 0.2)

    # 10. norm ppf/cdf round-trip
    check("norm_ppf/cdf roundtrip", abs(_norm_cdf(_norm_ppf(0.975)) - 0.975) < 1e-4)

    print("\n".join(msgs))
    print(f"\nstats_core unit tests: {ok} passed, {fail} failed")
    return fail == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if _tests() else 1)
