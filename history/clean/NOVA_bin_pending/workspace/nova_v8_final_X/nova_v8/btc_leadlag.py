"""Module — BTC lead-lag for lagging altcoins (separate research unit).

Design:
  * only the UP-side lag is exploited (long-only);
  * eligibility is computed causally from a rolling BTC/alt correlation;
  * BTC must confirm a strong, stabilised up-move and (optionally) its own MSS;
  * the altcoin must confirm its structure directly;
  * entries execute on the next bar's open, just like the directional engine;
  * protective stop, trailing stop, or coin-specific horizon closes the trade.

The structure Oracle is intentionally analytic-only. It is accepted as an
argument for API compatibility, but it never gates an entry.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .execution import (Position, market_cost_pct, market_fill,
                        settle_directional)


def _returns(s: pd.Series) -> pd.Series:
    return s.pct_change()


def _rolling_corr(a: pd.Series, b: pd.Series, window: int) -> pd.Series:
    return a.rolling(window).corr(b)


def _series(df: pd.DataFrame, name: str, idx: pd.Index,
            default: float = float("nan")) -> pd.Series:
    if name not in df.columns:
        return pd.Series(default, index=idx, dtype=float)
    return df[name].reindex(idx, method="ffill")


def run_btc_pass(matrices: dict, mss_truth: dict | None = None) -> list[dict]:
    """Run the causal BTC lead-lag pass.

    ``mss_truth`` is accepted only for backward compatibility.  The Oracle is
    not a trading gate: using a post-hoc truth score to block historical entries
    would leak future information into the trade path.
    """
    if C.BTC_DIRECTION != "long_only":
        raise RuntimeError(
            f"BTC_DIRECTION='{C.BTC_DIRECTION}' غير منفَّذ؛ الطرف الطويل فقط "
            "(اللحاق مجدٍ في الصعود حسب التحليل)."
        )
    btc = matrices.get(C.BTC_SYMBOL)
    if btc is None:
        return []

    recs: list[dict] = []
    idx = btc.index
    btc_ret = _returns(btc["close"])
    alts = {s: df for s, df in matrices.items()
            if s != C.BTC_SYMBOL and s not in C.BTC_EXCLUDE}
    if not alts:
        return []

    # ---- causal, time-varying laggard eligibility ----
    # Do not classify a coin once from the final tail of the dataset.  Each bar
    # uses only correlation observations available by that bar.
    altd = {}
    for s, df in alts.items():
        close_s = _series(df, "close", idx)
        corr = _rolling_corr(btc_ret, close_s.pct_change(), C.BTC_CORR_WINDOW_BARS)
        corr_mean = corr.rolling(
            C.BTC_MIN_CORR_SAMPLES,
            min_periods=C.BTC_MIN_CORR_SAMPLES,
        ).mean()
        mss_s = _series(df, "mss", idx, 0.0).fillna(0).astype(int)
        mss_ok = (mss_s.rolling(4, min_periods=1).max() >= 1).to_numpy(bool)
        atr_f = (_series(df, "atr14", idx) /
                 close_s.replace(0.0, float("nan")))
        vr_f = _series(df, "vr", idx)
        altd[s] = {
            "close": close_s.to_numpy(float),
            "open": _series(df, "open", idx).to_numpy(float),
            "high": _series(df, "high", idx).to_numpy(float),
            "low": _series(df, "low", idx).to_numpy(float),
            "mss_ok": mss_ok,
            "atr": atr_f.to_numpy(float),
            "vr": vr_f.to_numpy(float),
            "corr_ok": (corr_mean >= C.BTC_CORR_MIN).fillna(False).to_numpy(bool),
        }

    btc_close = btc["close"].to_numpy(float)
    n = len(idx)
    lookback = 60 * 24 * 5            # 5-day move window for confirmation
    stabil_bars = 60 * 6              # ~6h range check for stabilisation
    chase_cap = 0.05
    warmup = lookback + C.BTC_MIN_CORR_SAMPLES

    # ---- BTC reference arrays (computed only from closed/current bar data) ----
    btc_s = btc["close"]
    roll_hi = btc_s.rolling(stabil_bars + 1, min_periods=1).max().to_numpy(float)
    roll_lo = btc_s.rolling(stabil_bars + 1, min_periods=1).min().to_numpy(float)
    btc_mss_s = btc["mss"] if "mss" in btc.columns else None
    btc_mss_recent = None
    if btc_mss_s is not None:
        btc_mss_recent = (
            btc_mss_s.fillna(0).rolling(6, min_periods=1).max() >= 1
        ).to_numpy(bool)

    # state: symbol -> entry effective px, execution bar, entry ATR, horizon,
    # trailing active, trailing stop, watermark
    open_pos: dict[str, list] = {}
    pending: dict[int, list[tuple[str, int]]] = {}

    def _cost_for(arr: dict, bar_i: int, decision_i: int | None = None) -> float:
        # For an entry scheduled from decision_i, use the last closed decision
        # bar. For an exit, use the previous bar, never the completed exit bar's
        # range, so the cost estimate itself does not look into the future.
        ref = decision_i if decision_i is not None else (bar_i - 1 if bar_i > 0 else bar_i)
        vr = arr["vr"][ref] if 0 <= ref < n else float("nan")
        value = float(vr) if np.isfinite(vr) else None
        return market_cost_pct(value, C.REGIME_BULL)

    for i in range(n):
        # ---- execute signals scheduled on the prior closed bar ----
        for s, decision_i in pending.pop(i, []):
            if s in open_pos:
                continue
            d = altd[s]
            raw_open = d["open"][i]
            if not np.isfinite(raw_open) or raw_open <= 0:
                continue
            raw_atr = d["atr"][decision_i]
            atr = float(raw_atr) if np.isfinite(raw_atr) and raw_atr > 0 else 0.02
            entry_cost = _cost_for(d, i, decision_i)
            entry_px = market_fill(float(raw_open), 1, entry_cost)
            horizon = C.BTC_HORIZON_BY_COIN.get(s, C.BTC_EXIT_HORIZON_MED)
            open_pos[s] = [entry_px, i, atr, horizon, 0, 0.0, entry_px]

        # ---- manage open positions through the current bar ----
        for s in list(open_pos):
            ep, ebar, atr, horizon, t_active, t_stop, wm = open_pos[s]
            d = altd[s]
            ob, hb, lb, cb = (d["open"][i], d["high"][i],
                              d["low"][i], d["close"][i])
            if not all(np.isfinite(x) for x in (ob, hb, lb, cb)):
                continue
            stopf = (C.BTC_STOP_ATR_MULT * atr
                     if np.isfinite(atr) else C.BTC_STOP_FALLBACK_PCT)
            prot_level = ep * (1.0 - stopf)
            triggered = []
            if lb <= prot_level:
                triggered.append((prot_level, "وقف-BTC"))
            if t_active and lb <= t_stop:
                triggered.append((t_stop, "تتبع-BTC"))
            reason = None
            fill = None
            if triggered:
                # The highest active long stop is reached first on a decline.
                # If price gaps below it, the open-price rule below dominates.
                fill, reason = max(triggered)
                # A gap through the line is filled at the actual bar open.
                if ob < fill:
                    fill = ob
            elif (i - ebar) >= horizon:
                fill, reason = cb, "أفق-BTC"
            if reason is not None and np.isfinite(fill) and fill > 0:
                rec = _make_rec(
                    s, ep, fill, reason, ebar, i,
                    slip_pct=_cost_for(d, i),
                )
                if rec:
                    rec["entry_time"] = pd.Timestamp(idx[ebar]).isoformat()
                    rec["exit_time"] = pd.Timestamp(idx[i]).isoformat()
                    recs.append(rec)
                del open_pos[s]
                continue

            gain_atr = ((hb - ep) / ep / atr
                        if np.isfinite(atr) and atr > 0 else 0.0)
            wm = max(wm, hb)
            if not t_active and gain_atr >= C.BTC_TRAIL_ACT_ATR:
                t_active, t_stop = 1, ep
            if t_active:
                cand = wm * (1.0 - C.BTC_TRAIL_DIST_ATR * atr)
                t_stop = max(t_stop, cand)
            open_pos[s] = [ep, ebar, atr, horizon, t_active, t_stop, wm]

        # ---- make a new decision only after the warm-up ----
        if i < warmup:
            continue
        bc = btc_close[i]
        if not np.isfinite(bc):
            continue
        base = btc_close[i - lookback]
        move = ((bc - base) / base
                if np.isfinite(base) and base > 0 else 0.0)
        hi, lo = roll_hi[i], roll_lo[i]
        stable = ((hi - lo) / max(lo, 1e-9) < 0.01
                  if np.isfinite(hi) and np.isfinite(lo) else False)
        confirmed_up = move >= C.BTC_MOVE_THRESH_PCT and stable
        if confirmed_up and C.BTC_STRUCTURE_ON_BTC and btc_mss_recent is not None:
            confirmed_up = bool(btc_mss_recent[i])
        if not confirmed_up:
            continue

        # ---- schedule laggard entries for the next bar, never this close ----
        for s, d in altd.items():
            if s in open_pos:
                continue
            if any(s == x[0] for vals in pending.values() for x in vals):
                continue
            if not d["corr_ok"][i]:
                continue
            c_i = d["close"][i]
            if not np.isfinite(c_i) or c_i <= 0:
                continue
            b_i = d["close"][i - lookback]
            if not (np.isfinite(b_i) and b_i > 0):
                continue
            alt_move = (c_i - b_i) / b_i
            if alt_move > move + chase_cap:
                continue
            if C.BTC_STRUCTURE_CONFIRM and not bool(d["mss_ok"][i]):
                continue
            # Direct MSS is the structural condition; Oracle remains analytic.
            pending.setdefault(i + 1, []).append((s, i))

    # Close positions left at the end of the available sample. No future open
    # exists, so the last close is the least-assumptive terminal reference.
    last_i = n - 1
    for s, state in list(open_pos.items()):
        ep, ebar, _atr, _horizon, _ta, _ts, _wm = state
        d = altd[s]
        last_close = d["close"][last_i]
        if np.isfinite(last_close) and last_close > 0:
            rec = _make_rec(s, ep, float(last_close), "نهاية-العينة",
                            ebar, last_i, slip_pct=_cost_for(d, last_i))
            if rec:
                rec["entry_time"] = pd.Timestamp(idx[ebar]).isoformat()
                rec["exit_time"] = pd.Timestamp(idx[last_i]).isoformat()
                recs.append(rec)
    return recs


def _make_rec(symbol, entry_px, exit_px, reason, ebar, xbar,
              slip_pct: float | None = None):
    if entry_px <= 0 or exit_px <= 0:
        return None
    pos = Position(symbol=symbol, side=1, entry=entry_px, entry_px=entry_px,
                   atr_pct=0.02, trigger="BTC-LeadLag", regime=C.REGIME_BULL)
    net = settle_directional(pos, exit_px, slip_pct=slip_pct)
    return {
        "symbol": symbol, "category": C.CAT_BTC, "side": 1,
        "entry_px": entry_px, "exit_px": exit_px, "net": net,
        "reason": reason, "entry_bar": ebar, "exit_bar": xbar,
        "trigger": "BTC-LeadLag", "mult": 1, "series": 0,
    }
