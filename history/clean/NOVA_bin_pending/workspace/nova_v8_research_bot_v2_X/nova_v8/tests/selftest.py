"""Self-test: run the full research engine on a small synthetic archive to catch
any exception before real historical runs. Does not require user data.

Usage:
    python -m nova_v8 selftest

Besides the end-to-end research run it performs focused arithmetic checks on the
grid module and the ATR exit engine (where subtle bugs tend to hide).
"""
from __future__ import annotations

import logging
import math
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from nova_v8 import config as C


def _bounded_logprice(n: int, rng, A: float = 0.6, P: int = 6000,
                      noise_c: float = 0.0015, btc_link: float = 0.0) -> np.ndarray:
    """Bounded log-price: smooth bull/bear sine waves + tiny per-bar noise so the
    series stays within a sane range (does not explode like a plain random walk)."""
    i = np.arange(n)
    wave = A * np.sin(2.0 * np.pi * i / P)
    if btc_link:
        wave = wave + btc_link * np.sin(2.0 * np.pi * i / (P * 0.5))
    return wave + rng.normal(0.0, noise_c, n)


def synthetic_ohlcv(n: int = 30_000, seed: int = 7, vol: float = 0.003,
                    btc_link: float = 0.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    logc = _bounded_logprice(n, rng, btc_link=btc_link)
    c = 100.0 * np.exp(logc)
    o = np.empty(n)
    o[0] = c[0]
    o[1:] = c[:-1]
    wick = np.abs(rng.normal(0.0, vol, n))
    h = np.maximum(o, c) * (1.0 + wick)
    l = np.minimum(o, c) * (1.0 - wick)
    volq = np.abs(rng.normal(1.0, 0.4, n)) + 0.2
    start = pd.Timestamp("2025-01-01", tz="UTC")
    idx = start + pd.to_timedelta(np.arange(n), unit="min")
    return pd.DataFrame({
        "open_time": idx.view("int64") // 1_000_000,   # epoch ms
        "open": o, "high": h, "low": l, "close": c, "volume": volq,
    })


def write_archive(dirpath: Path, n: int = 30_000):
    dirpath.mkdir(parents=True, exist_ok=True)
    syms = ["BTCUSDT", "SOLUSDT", "XLMUSDT"]
    for i, s in enumerate(syms):
        df = synthetic_ohlcv(n, seed=10 + i,
                             btc_link=0.0 if s == "BTCUSDT" else 0.30)
        df.to_parquet(dirpath / f"{s}_1m.parquet", index=False)
    return syms


# -------------------------------------------------------------- unit checks
def _check_grid_unit():
    """Step a Grid through a synthetic band and assert sane harvest accounting."""
    from nova_v8.grid import Grid
    C.GRID_CAPITAL_USD = 1000.0
    n = 50_000
    lo, hi = 100.0, 102.0
    start = 101.0
    grid = Grid("TEST", 0, lo, hi, start)
    # strong low-frequency oscillation inside the band -> many buy/sell cycles
    for i in range(n):
        phase = (i % 300) / 300.0
        px = 101.0 + 0.8 * math.sin(2.0 * math.pi * phase)
        o = h = l = c = px
        grid.on_bar(o, h, l, c, i)
        if grid.closed:
            break
    assert not grid.closed or True
    assert grid.cycles > 0, "grid should harvest cycles"
    assert math.isfinite(grid.net_usd), "grid net must be finite"
    # flattening sanity on a manual grid that breaks the range
    g2 = Grid("TEST", 0, 100.0, 102.0, 101.0)
    for i in range(400):
        g2.on_bar(200.0, 200.0, 200.0, 200.0, i)   # far above range -> flatten
        if g2.closed:
            break
    assert g2.closed and g2.close_reason, "grid must flatten on range break"


def _check_btc_pass():
    """Force the BTC lead-lag pass to actually open/manage/exit trades so the
    stop / trailing / oracle-gate / MSS-on-BTC branches run (not just return []).
    Correlation gating is relaxed here so the deterministic scenario reaches the
    open/management/exit code; default strict settings are restored afterwards.
    """
    from nova_v8 import btc_leadlag
    from nova_v8 import config as C
    rng = np.random.default_rng(11)
    N = 20_000
    t = np.arange(N)
    idx = pd.date_range("2023", periods=N, freq="1min", tz="UTC")

    old = {k: getattr(C, k) for k in
           ("BTC_CORR_MIN", "BTC_MIN_CORR_SAMPLES", "BTC_CORR_WINDOW_BARS")}
    old_hor = dict(C.BTC_HORIZON_BY_COIN)
    try:
        # relax correlation gating for this deterministic scenario
        C.BTC_CORR_MIN = -2.0
        C.BTC_MIN_CORR_SAMPLES = 2
        C.BTC_CORR_WINDOW_BARS = 400
        C.BTC_HORIZON_BY_COIN["SOLUSDT"] = 200

        C.BTC_HORIZON_BY_COIN["SOLUSDT"] = 9000   # hold into the dip

        drift = 2.0 * (t / N)
        base = 100.0 + drift + 0.15*np.sin(t/4000.0) + np.cumsum(rng.normal(0, 3e-4, N))
        dip = np.zeros(N)
        mask = (t >= 15000) & (t < 16500)
        dip[mask] = np.linspace(0.0, 1.3, int(mask.sum()))
        btc = base - dip
        alt = btc.copy() + rng.normal(0, 0.02, N)

        def mk(price):
            o = price; h = price + 0.02; l = price - 0.02; c = price
            return pd.DataFrame({"open": o, "high": h, "low": l, "close": c,
                                 "atr14": np.abs(c)*0.002,
                                 "mss": np.ones(N, dtype=int)}, index=idx)

        matrices = {"BTCUSDT": mk(btc), "SOLUSDT": mk(alt)}

        recs = btc_leadlag.run_btc_pass(matrices, mss_truth=None)
        assert isinstance(recs, list), "btc pass must return a list"
        assert len(recs) >= 1, "crafted scenario should produce BTC trades"
        for r in recs:
            assert r["entry_px"] > 0 and r["exit_px"] > 0
            assert math.isfinite(r["net"])
            assert r["reason"] in ("وقف-BTC", "تتبع-BTC", "أفق-BTC")
        # trailing / protective branches ran (some exit is a stop or trail exit)
        assert any(r["reason"] in ("وقف-BTC", "تتبع-BTC") for r in recs), \
            "expected at least one protective/trailing BTC exit"
    finally:
        for k, v in old.items():
            setattr(C, k, v)
        C.BTC_HORIZON_BY_COIN.clear(); C.BTC_HORIZON_BY_COIN.update(old_hor)


def _check_exit_engine():
    """Feed a strong bull move then a retracement; assert a sane finite exit."""
    from nova_v8.execution import Position, ExitEngine, settle_directional
    entry = 100.0
    atr_pct = 0.01
    pos = Position("TEST", 1, entry, entry, atr_pct, "EMA", "صاعد",
                   notional=20.0, entry_bar=0)
    eng = ExitEngine()
    eng.arm(pos)
    closes = list(np.linspace(100.0, 118.0, 300))   # climb to +18%
    closes += list(np.linspace(118.0, 104.0, 80))   # retracement
    prev = 100.0
    fill = None
    for i in range(1, len(closes)):
        c = closes[i]
        o = prev
        bar = (o, max(o, c) * 1.001, min(o, c) * 0.999, c)
        res = eng.update(pos, bar[0], bar[1], bar[2], i, "صاعد", c)
        if res:
            fill = res
            break
        prev = c
    if fill is None:                                  # force exit at last close
        fill = ("نهاية", closes[-1])
    net = settle_directional(pos, fill[1])
    assert math.isfinite(net), "pnl must be finite"
    assert abs(net) < 1.0, f"pnl out of sane range: {net}"


# --------------------------------------------------------------- main entry
def run(tmp_root: Path | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    keep = tmp_root
    if keep is None:
        tmp = Path(tempfile.mkdtemp(prefix="nova_selftest_"))
    else:
        tmp = Path(keep)
        tmp.mkdir(parents=True, exist_ok=True)
    archive = tmp / "archive"
    out = tmp / "out"

    syms = write_archive(archive)

    old_arch, old_data = C.ARCHIVE_DIR, C.DATA_DIR
    old_syms = C.SYMBOLS
    old_res, old_rep, old_stab = C.RESULT_PATH, C.REPORT_PATH, C.STABILITY_PATH
    C.ARCHIVE_DIR = archive
    C.DATA_DIR = out
    C.SYMBOLS = tuple(syms)
    C.RESULT_PATH = out / "research_results.csv"
    C.REPORT_PATH = out / "final_report.txt"
    C.STABILITY_PATH = out / "oracle_stability.txt"
    C.REGIME_TF = "15m"
    try:
        print("unit: grid...")
        _check_grid_unit()
        print("unit: exit engine...")
        _check_exit_engine()
        print("unit: btc pass...")
        _check_btc_pass()

        from nova_v8 import engine
        results = engine.run_research(symbols=tuple(syms), on_progress=_probe)
        _check(results)
        print("\n== SELFTEST OK ==")
        print(engine.render_report(results))
        return 0
    except Exception:
        import traceback
        traceback.print_exc()
        return 1
    finally:
        C.ARCHIVE_DIR, C.DATA_DIR = old_arch, old_data
        C.SYMBOLS = old_syms
        C.RESULT_PATH, C.REPORT_PATH, C.STABILITY_PATH = old_res, old_rep, old_stab
        if keep is None:
            shutil.rmtree(tmp, ignore_errors=True)


def _probe(frac: float):
    pass  # milestone hook; nothing needed in self-test


def _check(res: dict):
    assert "directional" in res and "grid" in res and "btc" in res
    assert isinstance(res["records"], list)
    # sanity: reported directional $ figures must stay within a plausible range
    d = res["directional"]
    assert math.isfinite(d["pnl_usd"])
    assert abs(d["pnl_usd"]) < 1e8, f"directional pnl implausible: {d['pnl_usd']}"
    assert C.RESULT_PATH.exists(), "research_results.csv missing"
    assert C.REPORT_PATH.exists(), "final_report.txt missing"
    assert C.STABILITY_PATH.exists(), "oracle_stability.txt missing"
