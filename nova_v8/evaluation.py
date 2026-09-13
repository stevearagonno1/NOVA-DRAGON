"""Evaluation layer — post-hoc statistics on research trade records.

Works on the RESULTS of any research run (per-trade net fractions), so it is
data-source-agnostic: point it at a synthetic or a real archive's CSV. It is
the statistical half of the research-first rule: a result is not approved
before Monte-Carlo drawdown, PSR/DSR (multiplicity-aware), CPCV (out-of-sample
folds) and a minimum-backtest-length check. Nothing here gates live trading;
it quantifies how fragile a research result is.

Methods:
  * Monte Carlo permutation: reshuffle trade ORDER n_sim times -> distribution
    of the equity path -> worst-case drawdown percentiles and best-run size.
    (The sum is permutation-invariant, so final PnL is not percentile-tested.)
  * PSR (probabilistic Sharpe, Bailey & Lopez de Prado 2014) with skew/kurtosis.
  * DSR (deflated Sharpe): PSR corrected for M independent trials (the
    multiple-testing inflation of trying many variants); E[max SR] uses the
    documented normal extreme-value approximation.
  * CPCV (combinatorial purged cross-validation, AIFM): the trade sequence is
    cut into S segments; every C(S, T) choice of T test segments is scored
    out-of-sample with a purge/embargo band around the test boundaries; the
    fold mean/variance shows OOS stability.
  * MinBTL (minimum backtest time length, AIFM): the trade count needed for
    the Sharpe estimate to be statistically distinguishable from zero.

All inputs are per-trade net fractions in chronological order.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import config as C


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _sharpe(returns: np.ndarray) -> float:
    sd = float(np.std(returns, ddof=1))
    if sd <= 0 or len(returns) < 3:
        return 0.0
    return float(np.mean(returns)) / sd


def _skew(returns: np.ndarray) -> float:
    n = len(returns)
    m = float(np.mean(returns))
    sd = float(np.std(returns, ddof=1))
    if n < 4 or sd <= 0:
        return 0.0
    return float(np.sum(((returns - m) / sd) ** 3) * n / ((n - 1) * (n - 2)))


def _excess_kurt(returns: np.ndarray) -> float:
    n = len(returns)
    m = float(np.mean(returns))
    sd = float(np.std(returns, ddof=1))
    if n < 5 or sd <= 0:
        return 0.0
    k = float(np.sum(((returns - m) / sd) ** 4) * n * (n + 1)
              / ((n - 1) * (n - 2) * (n - 3)))
    return k - 3.0 * (n - 1) ** 2 / ((n - 2) * (n - 3))


def psr(returns: np.ndarray, sr0: float = 0.0) -> float:
    """Probabilistic Sharpe Ratio: P(true SR > sr0) given the sample."""
    n = len(returns)
    if n < 10:
        return float("nan")
    sr = _sharpe(returns)
    g3, g4 = _skew(returns), _excess_kurt(returns)
    denom = math.sqrt(max(1e-12, 1.0 - g3 * sr + (g4 / 4.0) * sr * sr))
    z = (sr - sr0) * math.sqrt(n - 1) / denom
    return _norm_cdf(z)


def dsr(returns: np.ndarray, trials: int = 1, sr0: float = 0.0) -> float:
    """Deflated Sharpe Ratio: PSR corrected for M independent trials.

    Deflation is implemented as lifting the null threshold: the sample SR must
    beat not just ``sr0`` but ``sr0 + E[max SR under the null over M trials]``.
    E[max] uses the normal extreme-value approximation
    sigma_sr*sqrt(2 ln M)*(1 - 0.5772/(2 ln M + 0.5772)), where sigma_sr is
    the standard error of the SR (std/sqrt(n-1)) — a documented approximation
    for independent, ~normal trial Sharpe estimates.
    """
    n = len(returns)
    if n < 10 or trials < 1:
        return float("nan")
    sr = _sharpe(returns)
    g3, g4 = _skew(returns), _excess_kurt(returns)
    denom = math.sqrt(max(1e-12, 1.0 - g3 * sr + (g4 / 4.0) * sr * sr))
    sigma_sr = float(np.std(returns, ddof=1)) / math.sqrt(n - 1)
    m = max(2, int(trials))
    ln_m = math.log(m)
    em = sigma_sr * math.sqrt(2.0 * ln_m) * (1.0 - 0.5772
                                             / (2.0 * ln_m + 0.5772))
    z = (sr - (sr0 + em)) * math.sqrt(n - 1) / denom
    return _norm_cdf(z)


def min_btl(returns: np.ndarray) -> float:
    """Minimum backtest length (in trades) for the Sharpe to clear zero at the
    usual 95% band: T* = (sigma/mean)^2 (AIFM)."""
    n = len(returns)
    m = float(np.mean(returns))
    sd = float(np.std(returns, ddof=1))
    if n < 10 or abs(m) <= 1e-15:
        return float("inf")
    return (sd / m) ** 2


def monte_carlo(returns: np.ndarray, n_sim: int = 2000,
                seed: int = 12345) -> dict:
    """Permutation MC: trade ORDER is the uncertainty; amounts are kept.

    Note: permuting preserves the SUM, so the final PnL is identical in every
    permutation by construction and is reported once (history_final), not as a
    percentile. The path-shape statistics (MaxDD percentiles, best cumulative
    run) are the meaningful outputs."""
    n = len(returns)
    out = {"n_sim": int(n_sim),
           "maxdd_p5": float("nan"), "maxdd_p1": float("nan"),
           "maxdd_p01": float("nan"),
           "best_run_p95": float("nan"), "history_best_run": float("nan"),
           "frac_paths_worse_than_history": float("nan")}
    if n < 20:
        return out
    rng = np.random.default_rng(seed)
    maxdds = np.empty(n_sim)
    best_runs = np.empty(n_sim)
    hist_final = float(np.sum(returns))

    def _maxdd(path: np.ndarray) -> float:
        peak = np.maximum.accumulate(path)
        return float(np.max(np.maximum(0.0, peak - path))) if len(path) else 0.0

    for s in range(n_sim):
        perm = rng.permutation(n)
        path = np.concatenate([[0.0], np.cumsum(returns[perm])])
        maxdds[s] = _maxdd(path)
        best_runs[s] = float(np.max(path)) if len(path) else 0.0
    dds = np.sort(maxdds)
    out["maxdd_p5"] = float(dds[int(0.95 * n_sim)])
    out["maxdd_p1"] = float(dds[int(0.99 * n_sim)])
    out["maxdd_p01"] = float(dds[int(0.999 * n_sim)])
    out["best_run_p95"] = float(np.sort(best_runs)[int(0.95 * n_sim)])
    hist_path = np.concatenate([[0.0], np.cumsum(returns)])
    hist_dd = _maxdd(hist_path)
    out["history_final"] = hist_final
    out["history_maxdd"] = hist_dd
    out["history_best_run"] = float(np.max(hist_path)) if len(hist_path) else 0.0
    out["frac_paths_worse_than_history"] = float(
        np.mean(maxdds > hist_dd))
    return out


def cpcv(returns: np.ndarray, entry_bars: np.ndarray | None = None,
         segments: int = 6, test_size: int = 3,
         purge: int = 2) -> dict:
    """Combinatorial purged CV over the time-ordered trade sequence.

    ``entry_bars`` (optional, chronological) enables bar-distance purging:
    trades within ``purge`` bars of a test boundary are removed from the
    training side (standard CPCV purge/embargo). Without bars, the purge
    removes the ``purge`` trades adjacent to each boundary.
    """
    n = len(returns)
    out = {"segments": int(segments), "test_size": int(test_size),
           "folds": 0, "oos_sharpes": [], "oos_mean": float("nan"),
           "oos_std": float("nan"), "oos_final": float("nan")}
    if n < segments * 3:
        return out
    edges = np.linspace(0, n, segments + 1).astype(int)
    seg_of = np.repeat(np.arange(segments),
                       [edges[k + 1] - edges[k] for k in range(segments)])

    def bar_of(i: int) -> int:
        return int(entry_bars[i]) if entry_bars is not None else i

    import itertools
    folds = list(itertools.combinations(range(segments), test_size))
    for combo in folds:
        test_mask = np.isin(seg_of, list(combo))
        train_mask = ~test_mask
        # purge/embargo: drop training trades within `purge` bars of any
        # test trade (bar distance when entry_bars given, else trade index)
        t_idx = np.where(test_mask)[0]
        if len(t_idx):
            dist = (np.abs(
                np.subtract.outer(
                    np.array([bar_of(i) for i in np.where(train_mask)[0]]),
                    np.array([bar_of(i) for i in t_idx])))
                if entry_bars is not None
                else np.abs(
                    np.subtract.outer(
                        np.where(train_mask)[0], t_idx)))
            drop_flags = (np.min(dist, axis=1) <= purge)
            if drop_flags.any():
                train_mask = train_mask.copy()
                train_mask[np.where(train_mask)[0][drop_flags]] = False
        if train_mask.sum() < 10 or test_mask.sum() < 3:
            continue
        out["folds"] += 1
        out["oos_sharpes"].append(_sharpe(returns[test_mask]))
        out["oos_final"] = float(np.sum(returns[test_mask])
                                 / max(1, out["folds"]))
        if out["folds"] == 1:
            out["oos_mean"] = float(np.mean(returns[test_mask]))
            out["oos_std"] = float(np.std(returns[test_mask], ddof=1))
        else:
            # running aggregate across folds (equal-weight)
            k = out["folds"]
            out["oos_mean"] = ((out["oos_mean"] * (k - 1)
                                + float(np.mean(returns[test_mask]))) / k)
            out["oos_std"] = ((out["oos_std"] * (k - 1)
                               + float(np.std(returns[test_mask], ddof=1))) / k)
    if out["folds"]:
        out["oos_sharpe_mean"] = float(np.mean(out["oos_sharpes"]))
        out["oos_sharpe_std"] = float(np.std(out["oos_sharpes"], ddof=1))
    return out


def evaluate(records: list[dict], sims: int = 2000, trials: int = 1,
             seed: int = 12345) -> dict:
    """Full evaluation bundle over chronological trade records."""
    recs = sorted(records, key=lambda r: (r.get("entry_bar", 0),
                                          r.get("entry_time", "")))
    rets = np.array([float(r.get("net_frac", 0.0)) for r in recs],
                    dtype=float)
    bars = np.array([int(r.get("entry_bar", i)) for i, r in enumerate(recs)],
                    dtype=np.int64)
    n = len(rets)
    res = {
        "n_trades": int(n),
        "net_frac_sum": float(np.sum(rets)) if n else 0.0,
        "sharpe_per_trade": _sharpe(rets) if n >= 3 else 0.0,
        "t_stat": (float(np.mean(rets))
                   / (float(np.std(rets, ddof=1)) / math.sqrt(n))
                   if n >= 3 and float(np.std(rets, ddof=1)) > 0 else 0.0),
        "psr": psr(rets),
        "dsr": dsr(rets, trials=trials),
        "min_btl_trades": min_btl(rets),
    }
    res["monte_carlo"] = monte_carlo(rets, n_sim=sims, seed=seed)
    res["cpcv"] = cpcv(rets, entry_bars=bars)
    return res


def load_records(csv_path: str, strategy: str | None = None) -> list[dict]:
    """Load research records from a results CSV (chronological)."""
    frame = pd.read_csv(csv_path)
    if "net_frac" not in frame.columns:
        raise ValueError("the CSV must contain a net_frac column")
    recs = frame.to_dict("records")
    if strategy:
        recs = [r for r in recs if str(r.get("strategy", "")) == strategy]
    return recs


def _interpret(res: dict, trials: int) -> str:
    """Short, value-based reading of the bundle (never a generic boilerplate)."""
    lines = []
    sr = res["sharpe_per_trade"]
    if math.isnan(res["psr"]):
        lines.append("PSR/DSR: عينة صغيرة (أقل من 10 صفقات) — لا حكم.")
    elif sr <= 0:
        lines.append("Sharpe العينة سالب/صفر — PSR وDSR عند الصفر متوقعان؛ "
                     "النتيجة لا تدعم الترقية.")
    else:
        if res["dsr"] < res["psr"]:
            lines.append(f"DSR < PSR مع {trials} تجربة — جزء من الأثر منفوخ "
                         "بالاختبارات المتعددة.")
        lines.append("PSR/DSR هما احتمال تفوق Sharpe الحقيقي على الصفر "
                     "(بعد التعديل للعدد من التجارب).")
    mbtl = res["min_btl_trades"]
    n = res["n_trades"]
    if math.isfinite(mbtl):
        need = max(1, math.ceil(mbtl))
        if n >= need:
            lines.append(f"MinBTL محقق: {n} صفقة >= المطلوب "
                         f"~{need} ({mbtl:.1f}).")
        else:
            lines.append(f"MinBTL غير محقق: {n} صفقة < المطلوب "
                         f"~{need} — العينة أقصر مما يكفي للحكم على Sharpe.")
    else:
        lines.append("MinBTL غير محدد (متوسط الصافي ≈ 0 أو عينة صغيرة).")
    mc = res["monte_carlo"]
    if math.isnan(mc["maxdd_p5"]):
        lines.append("Monte Carlo: عينة صغيرة (أقل من 20 صفقة).")
    else:
        lines.append(f"MaxDD التاريخي {mc['history_maxdd']:.4f} مقابل "
                     f"p99={mc['maxdd_p1']:.4f} من المسارات المعاد ترتيبها؛ "
                     f"نسبة المسارات الأسوأ من التاريخي "
                     f"{100*mc['frac_paths_worse_than_history']:.1f}%.")
    cv = res["cpcv"]
    if cv["folds"]:
        lines.append(f"CPCV: متوسط Sharpe خارج العينة "
                     f"{cv.get('oos_sharpe_mean', float('nan')):+.3f} "
                     f"على {cv['folds']} ثنية.")
    else:
        lines.append("CPCV: عينة صغيرة — لا ثنيات.")
    return "\n".join(lines)


def render(res: dict, source: str, trials: int = 1) -> str:
    L = ["NOVA_V8 — تقييم النتائج / Evaluation Layer",
         f"المصدر: {source}",
         f"الصفقات (زمنياً): {res['n_trades']}   "
         f"مجموع الصافي النسبي: {res['net_frac_sum']:+.4f}",
         "",
         f"Sharpe (لكل صفقة): {res['sharpe_per_trade']:+.4f}   "
         f"t: {res['t_stat']:+.2f}",
         f"PSR: {res['psr']:.3f}   DSR: {res['dsr']:.3f}",
         f"أدنى طول اختبار (MinBTL): "
         + (f"{res['min_btl_trades']:.1f} صفقة"
            if math.isfinite(res['min_btl_trades']) else "غير محدد"),
         "",
         "Monte Carlo (إعادة ترتيب الترتيب الزمني):"]
    mc = res["monte_carlo"]
    if math.isnan(mc["maxdd_p5"]):
        L.append("  عينة صغيرة (أقل من 20 صفقة) — لا توزيع.")
    else:
        L.append(f"  n_sim={mc['n_sim']}   "
                 f"final (ثابت بالبنية): {mc.get('history_final', float('nan')):+.4f}")
        L.append(f"  MaxDD p5={mc['maxdd_p5']:.4f} p1={mc['maxdd_p1']:.4f} "
                 f"p0.1={mc['maxdd_p01']:.4f}   "
                 f"(تاريخياً: {mc.get('history_maxdd', float('nan')):.4f})")
        L.append(f"  أفضل مسار تراكمي p95={mc['best_run_p95']:+.4f}   "
                 f"(تاريخياً: {mc.get('history_best_run', float('nan')):+.4f})")
    cv = res["cpcv"]
    L.append("")
    L.append(f"CPCV: {cv['folds']} ثنية (S={cv['segments']}, "
             f"T={cv['test_size']})   OOS Sharpe mean="
             f"{cv.get('oos_sharpe_mean', float('nan')):+.4f} "
             f"std={cv.get('oos_sharpe_std', float('nan')):.4f}")
    L.append("")
    L.append("التفسير:")
    L.append("  " + _interpret(res, trials).replace("\n", "\n  "))
    return "\n".join(L)
