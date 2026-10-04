#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0084-ENTRY-MIX — measurement core: registries, prefixes, gates, selection.

Temporal design (paper section 9):
  outer windows      : 2023H1..2026H1 (seven complete half-years) + 2026H2p
                       (2026-07-01..2026-09-27)
  inner validation   : every complete half-year starting 2022H1 and ending
                       before the target outer window
  descriptive series : 2021H1 .. 2026H2p (twelve rows per candidate/asset)
Purge: signal-to-horizon-end must lie inside the window; embargo 18 bars.

Eligibility gate per inner window (paper section 6): >=100 executed trades,
positive net in at least 8 of 12 assets, PF >= 1.3, one-sided 95% block
bootstrap expectancy lower bound > 0, and paired expectancy improvement over
BOTH constituent singleton controls (pairs) / the no-signal book (singles)
with lower bound > 0.  Rank by worst-window bound, then minimum trade count,
then canonical ID; keep <=10 pairs per mode; triples = retained parent pair x
each remaining setting (cap 1,500 trials before dedup).  Provisional choice:
worst-window bound, then member count, then larger minimum count, then ID.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
import time

import numpy as np
import pandas as pd

from . import engine as E
from . import indicators as I
from . import stats as S
from . import data as D

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
O = os.path.join(ROOT, "history", "research", "hyp_lab_out", "L0084-entry-mix")
WORK = os.path.join(ROOT, "work")

HALF_YEARS = [
    ("2021H1", "2021-01-01", "2021-06-30"), ("2021H2", "2021-07-01", "2021-12-31"),
    ("2022H1", "2022-01-01", "2022-06-30"), ("2022H2", "2022-07-01", "2022-12-31"),
    ("2023H1", "2023-01-01", "2023-06-30"), ("2023H2", "2023-07-01", "2023-12-31"),
    ("2024H1", "2024-01-01", "2024-06-30"), ("2024H2", "2024-07-01", "2024-12-31"),
    ("2025H1", "2025-01-01", "2025-06-30"), ("2025H2", "2025-07-01", "2025-12-31"),
    ("2026H1", "2026-01-01", "2026-06-30"),
    ("2026H2p", "2026-07-01", "2026-09-27"),
]
COMPLETE = [w for w in HALF_YEARS if not w[0].endswith("p")]
OUTER = ["2023H1", "2023H2", "2024H1", "2024H2", "2025H1", "2025H2",
         "2026H1", "2026H2p"]
WIN_RANGE = {name: (a, b) for name, a, b in HALF_YEARS}


def inner_windows(outer):
    """Complete half-years 2022H1..(outer-1), per section 9."""
    out = []
    for name, _a, _b in COMPLETE:
        if name >= "2022H1" and name < outer:
            out.append(name)
    return out


def canonical_pairs():
    """All unordered pairs in Appendix B order; 3 modes each."""
    pairs = []
    for i in range(len(I.SETTINGS_52)):
        for j in range(i + 1, len(I.SETTINGS_52)):
            pairs.append((I.SETTINGS_52[i], I.SETTINGS_52[j]))
    assert len(pairs) == 1326
    return pairs


def canonical_id(kind, seq, mode, members):
    return f"{kind}{seq:04d}|{mode}"


def sha_seed(text):
    """Seed from first 8 bytes of SHA256(UTF-8 text), unsigned big-endian."""
    return int.from_bytes(
        hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")


# --------------------------------------------------------------------------
# per-asset prepared panel
# --------------------------------------------------------------------------
class Panel:
    def __init__(self, sym):
        df = D.load_asset(WORK, sym)
        self.sym = sym
        self.dt = pd.to_datetime(df["dt"]).dt.tz_localize(None).to_numpy()
        self.days = (self.dt.astype("datetime64[D]") -
                     np.datetime64("2021-01-01")).astype(int)
        self.o = df["open"].to_numpy()
        self.h = df["high"].to_numpy()
        self.l = df["low"].to_numpy()
        self.c = df["close"].to_numpy()
        self.seg = df["seg"].to_numpy()
        self.v = df["volume"].to_numpy()
        self.tbv = df["taker_buy_volume"].to_numpy()
        d = dict(o=self.o, h=self.h, l=self.l, c=self.c, v=self.v,
                 tbv=self.tbv)
        self._raw = d
        self.masks = I.build_masks(d)
        self._mask_cache = dict(self.masks)
        self.atr = I.wilder_atr(self.h, self.l, self.c, 14)
        # bar ranges per half-year (timestamps naive UTC)
        self.ranges = {}
        for name, a, b in HALF_YEARS:
            lo = np.searchsorted(self.dt, np.datetime64(a))
            hi = np.searchsorted(self.dt, np.datetime64(b), side="right") - 1
            self.ranges[name] = (int(lo), int(hi))

    def mask_of(self, name):
        """Mask for a (possibly perturbed) setting name; cached."""
        if name not in self._mask_cache:
            self._mask_cache[name] = I.build_one(self._raw, name)
        return self._mask_cache[name]

    def day0(self, window):
        a = WIN_RANGE[window][0]
        return int((np.datetime64(a) - np.datetime64("2021-01-01")).astype(int))


def trade_stats(trades, days, n_days, base):
    """Aggregate stats of one trade list inside one window + bootstrap."""
    if not trades:
        return None
    net = np.array([t["net_dollars"] for t in trades])
    dnum = np.array(days)
    wins = np.array([t["outcome"] == "target" for t in trades])
    stops = np.array([t["outcome"] == "stop" for t in trades])
    timeouts = np.array([t["outcome"] == "timeout" for t in trades])
    decided = wins | stops
    ci = S.block_ci(dnum, net, n_days)
    pf = S.pf(net)
    k = int(wins.sum())
    n = int(decided.sum())
    p, wlo, whi = S.wilson(k, n)
    pos_assets = sum(1 for s in set(t["symbol"] for t in trades)
                     if sum(t["net_dollars"] for t in trades
                            if t["symbol"] == s) > 0)
    mean_cost_atr = float(np.mean([t["cost_atr"] for t in trades]))
    be_ref = 0.5 + mean_cost_atr / 3.0
    gross = np.array([t["gross_dollars"] for t in trades])
    gw = float(gross[gross > 0].mean()) if (gross > 0).any() else np.nan
    gl = float(-gross[gross < 0].mean()) if (gross < 0).any() else np.nan
    be_emp = ((gl + 0.052) / (gw + gl)) if (np.isfinite(gw) and np.isfinite(gl)
                                            and (gw + gl) > 0) else np.nan
    z = S.z_from_lb(ci["lo5"], ci["expectancy"], ci["se"])
    base_win = base["win_rate"] if base else np.nan
    base_exp = base["expectancy"] if base else np.nan
    return dict(
        n_exec=len(trades), n_win=int(wins.sum()), n_stop=int(stops.sum()),
        n_timeout=int(timeouts.sum()), timeout_share=float(timeouts.mean()),
        win_rate=p, wilson_lo=wlo, wilson_hi=whi,
        net=float(net.sum()), expectancy=ci["expectancy"],
        exp_lo5=ci["lo5"], exp_hi95=ci["hi95"], exp_se=ci["se"],
        gross=float(gross.sum()), cost=float(0.052 * len(trades)),
        pf=pf, pos_assets=pos_assets,
        mean_cost_atr=mean_cost_atr, breakeven_ref=be_ref,
        breakeven_empirical=be_emp,
        mean_net_atr_r=float(np.mean([t["net_atr_r"] for t in trades])),
        mean_barrier_r=float(np.mean([t["barrier_r"] for t in trades])),
        mean_mae=float(np.mean([t["mae_atr_r"] for t in trades])),
        mean_mfe=float(np.mean([t["mfe_atr_r"] for t in trades])),
        mean_holding=float(np.mean([t["holding_bars"] for t in trades])),
        gap_exits=int(sum(t["gap_flag"] for t in trades)),
        double_touch=int(sum(t["double_touch"] for t in trades)),
        baseline_win=base_win, baseline_exp=base_exp,
        lift_win_pts=(p - base_win) * 100 if np.isfinite(base_win) else np.nan,
        lift_exp=(ci["expectancy"] - base_exp) if np.isfinite(base_exp) else np.nan,
        p_raw=z, days=dnum, nets=net,
    )


class Measurer:
    """Loads all panels once; measures candidates window by window."""

    def __init__(self, log=print):
        self.log = log
        t0 = time.time()
        self.panels = {s: Panel(s) for s in D.ASSETS}
        self.log(f"[measure] panels ready ({time.time() - t0:.1f}s)")
        self._baseline_cache = {}
        self._base_trades = {}

    # ---------------- baseline no-signal book ---------------------------
    def baseline(self, window):
        key = window
        if key in self._baseline_cache:
            return self._baseline_cache[key]
        first, last = WIN_RANGE[window]
        n_days = int((np.datetime64(last) - np.datetime64(first)
                      ).astype(int)) + 1
        all_trades = []
        per_asset = {}
        day_list = []
        for sym, p in self.panels.items():
            trades, cnt = E.simulate(p.o, p.h, p.l, p.c, p.atr, p.seg,
                                     None, sym, "baseline")
            lo, hi = p.ranges[window]
            tw = E.window_trades(trades, lo, hi)
            per_asset[sym] = tw
            all_trades.extend(tw)
            day_list.extend([p.days[t["fill_bar"]] - p.day0(window)
                             for t in tw])
        if not all_trades:
            self._baseline_cache[key] = None
            return None
        wins = sum(1 for t in all_trades if t["outcome"] == "target")
        stops = sum(1 for t in all_trades if t["outcome"] == "stop")
        p = wins / (wins + stops) if (wins + stops) else np.nan
        exp = float(np.mean([t["net_dollars"] for t in all_trades]))
        days = np.array(day_list)
        self._base_trades[key] = (days, np.array([t["net_dollars"]
                                                  for t in all_trades]))
        self._baseline_cache[key] = dict(win_rate=float(p), expectancy=exp,
                                         n=len(all_trades),
                                         per_asset=per_asset)
        return self._baseline_cache[key]

    # ---------------- candidate measurement -----------------------------
    def candidate_trades(self, members, mode):
        """Simulate on all assets; returns per-window trade lists."""
        out = {}
        for sym, p in self.panels.items():
            masks = {m: p.masks[m] for m in members}
            comb = E.combine(masks, mode, p.seg)
            trades, cnt = E.simulate(p.o, p.h, p.l, p.c, p.atr, p.seg,
                                     comb, sym, "cand")
            out[sym] = trades
        return out

    def windowed(self, trades_by_asset, window):
        lo_hi = {}
        for sym, p in self.panels.items():
            lo_hi[sym] = p.ranges[window]
        pooled = []
        for sym, trades in trades_by_asset.items():
            lo, hi = lo_hi[sym]
            pooled.extend(E.window_trades(trades, lo, hi))
        return pooled

    def stat_window(self, trades, window, with_days=False):
        first, last = WIN_RANGE[window]
        n_days = int((np.datetime64(last) - np.datetime64(first)
                      ).astype(int)) + 1
        d0 = self.panels[trades[0]["symbol"]].day0(window)
        days = np.array([self.panels[t["symbol"]].days[t["fill_bar"]] - d0
                         for t in trades])
        base = self.baseline(window)
        st = trade_stats(trades, days, n_days, base)
        if st is not None:
            st["window"] = window
            st["n_days"] = n_days
        return st


# --------------------------------------------------------------------------
# registry files (written BEFORE outcomes)
# --------------------------------------------------------------------------
def write_registries():
    os.makedirs(O, exist_ok=True)
    pairs = canonical_pairs()
    rows = []
    for n, (a, b) in enumerate(pairs, start=1):
        for mode in ("AND0", "AND2", "OR0"):
            rows.append({"pair_id": f"P{n:04d}", "member_a": a,
                         "member_b": b, "mode": mode})
    pd.DataFrame(rows).to_csv(os.path.join(O, "pairs_registry.csv"),
                              index=False)
    cat = pd.DataFrame([{"setting": s, "definition": "",
                         "parameters": "", "source_commit": "62f4d255",
                         "mask_hash": "", "duplicate_of": ""}
                        for s in I.SETTINGS_52])
    cat.to_csv(os.path.join(O, "catalogue.csv"), index=False)
    return len(rows)


def counts_check():
    from math import comb
    n = 52
    return dict(singletons=n, pairs=comb(n, 2), pair_modes=3 * comb(n, 2),
                triple_cap=30 * (n - 2), triple_space=3 * comb(n, 3),
                holm_family=n + 3 * comb(n, 2) + 3 * comb(n, 3))


# --------------------------------------------------------------------------
# full measurement pipeline
# --------------------------------------------------------------------------
GATE_MIN_TRADES = 100
GATE_MIN_POS_ASSETS = 8
GATE_MIN_PF = 1.3
BASE_ROLES = ("single", "pair", "triple")


def _pair_stats(m, members, mode, windows):
    """Stats for one candidate over given windows + per-window trade lists."""
    trades = m.candidate_trades(members, mode)
    out = {}
    for w in windows:
        pooled = m.windowed(trades, w)
        st = m.stat_window(pooled, w) if pooled else None
        out[w] = st
    return trades, out


def _pooled_day_arrays(m, trades_by_asset, window):
    p0 = None
    days = []
    net = []
    for sym, trades in trades_by_asset.items():
        p = m.panels[sym]
        lo, hi = p.ranges[window]
        for t in E.window_trades(trades, lo, hi):
            days.append(p.days[t["fill_bar"]] - p.day0(window))
            net.append(t["net_dollars"])
    return np.array(days), np.array(net)


def _win_days(window):
    first, last = WIN_RANGE[window]
    return int((np.datetime64(last) - np.datetime64(first)).astype(int)) + 1


def pair_gate(m, members, mode, windows, single_stats):
    """Evaluate section 6 gate; returns (eligible, detail per window)."""
    trades_by_asset = m.candidate_trades(members, mode)
    detail = {}
    ok = True
    worst = np.inf
    min_count = np.inf
    for w in windows:
        pooled = m.windowed(trades_by_asset, w)
        base = m.baseline(w)
        if pooled:
            st = m.stat_window(pooled, w)
        else:
            st = None
        rec = {"n_exec": 0, "exp_lo5": -np.inf, "pf": 0.0, "pos_assets": 0,
               "n": 0, "paired": {}}
        if st is not None:
            rec.update(n_exec=st["n_exec"], exp_lo5=st["exp_lo5"],
                       pf=st["pf"], pos_assets=st["pos_assets"],
                       n=st["n_exec"], expectancy=st["expectancy"])
            worst = min(worst, st["exp_lo5"])
            min_count = min(min_count, st["n_exec"])
            if st["n_exec"] < GATE_MIN_TRADES:
                ok = False
            if st["pos_assets"] < GATE_MIN_POS_ASSETS:
                ok = False
            if not (st["pf"] >= GATE_MIN_PF):
                ok = False
            if not (st["exp_lo5"] > 0):
                ok = False
            days_a, net_a = _pooled_day_arrays(m, trades_by_asset, w)
            n_days = _win_days(w)
            for ctrl in members:                      # constituent singletons
                cs = single_stats.get(ctrl, {}).get(w)
                if cs is None:
                    ok = False
                    rec["paired"][ctrl] = dict(diff=-np.inf, lo5=-np.inf)
                    continue
                pd_ = S.paired_block_diff(
                    days_a, net_a, cs["days"], cs["nets"], n_days)
                rec["paired"][ctrl] = dict(diff=pd_["diff"], lo5=pd_["lo5"])
                if not (pd_["lo5"] > 0):
                    ok = False
        else:
            ok = False
        detail[w] = rec
    return ok, detail, (worst if np.isfinite(worst) else -np.inf), \
        (min_count if np.isfinite(min_count) else 0), trades_by_asset


def single_gate(m, name, windows, stats):
    """Single gate: same temporal/sample/PF/cost gates + superiority over
    the no-signal book (paired lower bound above zero)."""
    good = True
    for w in windows:
        st = stats.get(w)
        if st is None or st["n_exec"] < GATE_MIN_TRADES \
                or st["pos_assets"] < GATE_MIN_POS_ASSETS \
                or not (st["pf"] >= GATE_MIN_PF) or not (st["exp_lo5"] > 0):
            good = False
            break
        base = m.baseline(w)
        bd, bn = m._base_trades[w]
        pd_ = S.paired_block_diff(st["days"], st["nets"], bd, bn, st["n_days"])
        if not (pd_["lo5"] > 0):
            good = False
            break
    return good


def triple_id(members, mode, seq):
    return f"T{seq:05d}|{mode}"


def register_triples(prefix, retained, seq_start):
    """Retained pairs (<=10 per mode) x each remaining setting; sorted names;
    dedup identical triple+mode ids; keep parent links."""
    rows = []
    seen = {}
    seq = seq_start
    for prow in retained:
        members = [prow["member_a"], prow["member_b"]]
        mode = prow["mode"]
        for extra in I.SETTINGS_52:
            if extra in members:
                continue
            tri = tuple(sorted(members + [extra]))
            key = (tri, mode)
            if key in seen:
                seen[key]["parent_ids"].append(prow["pair_id"])
                continue
            seq += 1
            row = {"prefix_id": prefix, "triple_id": triple_id(tri, mode, seq),
                   "member_a": tri[0], "member_b": tri[1], "member_c": tri[2],
                   "mode": mode, "parent_ids": prow["pair_id"],
                   "eligible": "", "reason": "registered before outcomes"}
            seen[key] = row
            rows.append(row)
    for row in rows:
        row["parent_ids"] = "+".join(row["parent_ids"]) if \
            isinstance(row["parent_ids"], list) else row["parent_ids"]
    return rows
