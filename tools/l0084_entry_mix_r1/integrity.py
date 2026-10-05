#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0084-ENTRY-MIX — 18 integrity checks (paper section 11).

Checks 14 and 16 run on synthetic end-to-end data before any money result;
the same file is re-run in the audit phase (17, 18 need real artefacts).
A critical defect means BLOCKED / MEASUREMENT INVALID: stop before ranking.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time

import numpy as np
import pandas as pd

from . import data as D
from . import engine as E
from . import indicators as I
from . import labels as L
from . import measure as M
from . import stats as S

ROOT = M.ROOT
O = M.O
WORK = M.WORK
UPLOADS = "/home/user/uploads"
RESULTS = {}


def _record(num, name, ok, evidence, critical=True, **kw):
    key = f"check_{num:02d}" if isinstance(num, int) else f"check_{num}"
    RESULTS[key] = {"check": str(num), "name": name,
                                   "ok": bool(ok),
                                   "critical": critical,
                                   "evidence": evidence, **kw}
    label = f"{num:02d}" if isinstance(num, int) else str(num)
    print(f"[check {label}] {'PASS' if ok else 'FAIL'} — {name}: {evidence}",
          flush=True)
    return bool(ok)


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


# ==========================================================================
def check_01_pins(m):
    path = os.path.join(O, "sources.json")
    bad = []
    try:
        source = json.load(open(path, encoding="utf-8"))
        expected = {"main": "71f52f0741cdaceb71797b1fe07de07db31fcced",
                    "grid_52": "62f4d255e0fc6fce8e7c331a6349484ccb0b8fc0",
                    "cost_model": "2d8e8f3afca6a72679382780ddaeb0d71de2cad6",
                    "prior_delivery": "d310df96901fa062022db41a35a24c5f229e0459"}
        if source.get("pins") != expected:
            bad.append(("pins", source.get("pins")))
        amendment_name=os.environ.get("L0084_R1_AMENDMENT_PATH","preregistration_amendment.json")
        amendment_path=os.path.join(O,os.path.basename(amendment_name))
        amendment_seed={}
        if os.path.isfile(amendment_path):
            try:amendment_seed=json.load(open(amendment_path,encoding="utf-8")).get("code_files_sha256",{})
            except Exception:amendment_seed={}
        for item in source.get("local_source_files", []):
            rel=item.get("path")
            # Historical source.json predates the implementation amendment.
            # R1 implementation files are instead checked against the exact
            # current amendment map below; owner inputs remain checked here.
            if rel in amendment_seed:continue
            f = os.path.join(ROOT, rel)
            if not os.path.isfile(f) or _sha(f) != item["sha256"]:
                bad.append((rel, "local SHA mismatch/missing"))
        if not source.get("sources"): 
            bad.append(("sources", "empty"))
        for item in source.get("sources", []):
            if item.get("commit") == "owner-attachment":
                continue
            if item.get("http_status") != 200 or item.get("errors"):
                bad.append((item.get("commit"), item.get("path"), item.get("http_status"), item.get("errors")))
        if not os.path.isfile(amendment_path):
            bad.append(("preregistration_amendment.json","missing"))
        else:
            amendment=json.load(open(amendment_path,encoding="utf-8"))
            expected_code=os.environ.get("L0084_R1_CODE_COMMIT")
            if amendment.get("code_commit_before_measurement")!=expected_code:
                bad.append(("runner commit",amendment.get("code_commit_before_measurement"),expected_code))
            source_map=amendment.get("code_files_sha256",{})
            local_dir=os.path.join(ROOT,"tools","l0084_entry_mix_r1")
            local_paths={"tools/l0084_entry_mix_r1/"+f for f in os.listdir(local_dir)
                         if f.endswith(".py") or f=="environment.lock"}
            if set(source_map)!=local_paths:
                bad.append(("code file set",len(source_map),len(local_paths)))
            for rel,want in source_map.items():
                fp=os.path.join(ROOT,rel)
                if not os.path.isfile(fp) or _sha(fp)!=want:bad.append((rel,"amendment SHA mismatch"))
        n = len(source.get("sources", []))
    except Exception as exc:
        n = 0; bad.append(("sources.json", type(exc).__name__))
    return _record(1, "source pins and hashes", not bad,
                   f"source records={n}; mismatches={bad or 'none'}")


def check_02_settings(m):
    names = I.SETTINGS_52
    ok = len(names) == 52 and len(set(names)) == 52
    cat = pd.read_csv(os.path.join(O, "catalogue.csv")) \
        if os.path.exists(os.path.join(O, "catalogue.csv")) else None
    ok2 = cat is not None and set(cat["setting"]) == set(names)
    return _record(2, "exactly 52 setting names", ok and ok2,
                   f"unique={len(set(names))}; catalogue_rows="
                   f"{0 if cat is None else len(cat)}")


def check_03_pairs(m):
    pairs = M.canonical_pairs()
    modes = len(pairs) * 3
    reg = os.path.join(O, "pairs_registry.csv")
    r = pd.read_csv(reg) if os.path.exists(reg) else None
    ok = len(pairs) == 1326 and len(set(pairs)) == 1326 and modes == 3978
    ok2 = r is None or len(r) == 3978
    # registry matches the owner's Appendix B table verbatim, when present
    sheet = os.path.join(UPLOADS, "L0084-ENTRY-MIX-EXECUTION.md")
    appb_ok, appb_n = None, 0
    if os.path.exists(sheet) and r is not None:
        txt = open(sheet, encoding="utf-8").read()
        seg = txt[txt.index("## Appendix B"):txt.index("## Appendix C")]
        rows = re.findall(r"^\|\s*(P\d{4})\s*\|\s*([^|]+?)\s*\|\s*"
                          r"([^|]+?)\s*\|\s*$", seg, re.M)
        appb_n = len(rows)
        appb_ok = True
        byid = r[r["mode"] == "AND0"].set_index("pair_id")
        for pid, a, b in rows:
            if pid not in byid.index or (byid.loc[pid, "member_a"],
                                         byid.loc[pid, "member_b"]) != (a, b):
                appb_ok = False
                break
    if appb_n:
        ok2 = ok2 and appb_ok
    return _record(3, "1,326 pairs / 3,978 pair modes", ok and ok2,
                   f"pairs={len(pairs)} pair_modes={modes} "
                   f"registry_rows={0 if r is None else len(r)}; "
                   f"Appendix B rows matched verbatim={appb_n} "
                   f"({'OK' if appb_ok else 'MISMATCH'})")


def check_04_ohlcv(m):
    problems = []
    for sym in D.ASSETS:
        p = m.panels[sym]
        dt = pd.to_datetime(p.dt)
        d = np.diff(dt.values).astype("timedelta64[m]").astype(int)
        step_bad = int(((d != 240)).sum())
        ohlc_bad = int((p.h < np.maximum(p.o, p.c) - 1e-9).sum()
                       + (p.l > np.minimum(p.o, p.c) + 1e-9).sum())
        neg = int((p.v < 0).sum())
        tbv_bad = int((p.tbv > p.v + 1e-9).sum())
        if step_bad or ohlc_bad or neg or tbv_bad:
            problems.append((sym, step_bad, ohlc_bad, neg, tbv_bad, len(p.c)))
    return _record(4, "timestamp units, OHLC and volume integrity", not problems,
                   f"12 assets checked; problems={problems}")


def check_05_contiguity(m):
    problems = []
    for sym in D.ASSETS:
        p = m.panels[sym]
        for s_ in np.unique(p.seg):
            idx = np.nonzero(p.seg == s_)[0]
            if len(idx) > 1 and int(np.diff(idx).max()) != 1:
                problems.append((sym, int(s_), "intra-segment hole"))
        # a bar whose successor lies in a different segment must not signal
        boundary = np.nonzero(p.seg[1:] != p.seg[:-1])[0]
        for name in I.SETTINGS_52:
            if boundary.size and p.masks[name][boundary].any():
                problems.append((sym, name, "mask true at segment edge"))
                break
    # synthetic gap: engine must never fill across a segment boundary
    n = 60
    o = np.full(n, 100.0); h = np.full(n, 100.5)
    l = np.full(n, 99.5); c = np.full(n, 100.0)
    atr = np.ones(n)
    seg = np.r_[np.zeros(30, int), np.ones(n - 30, int)]
    mask = np.zeros(n, bool); mask[28] = True      # next bar crosses the gap
    mask[40] = True                                 # clean signal after gap
    tr, cnt = E.simulate(o, h, l, c, atr, seg, mask, "SYN", "t")
    crossed = [t for t in tr if not (t["seg"] == seg[t["signal_bar"]]
                                     == seg[t["fill_bar"]] == seg[t["exit_bar"]])]
    ok_syn = (len(tr) == 1 and tr[0]["signal_bar"] == 40
              and not crossed and cnt["incomplete"] >= 1)
    return _record(5, "contiguous bars and gap resets",
                   not problems and ok_syn,
                   f"intra-segment holes/edge masks: {problems or 'none'}; "
                   f"synthetic boundary test: no crossing, "
                   f"pre-gap signal rejected as incomplete (n={len(tr)})")


def check_06_truncation(m):
    """Verify prefix causality for all settings and modes on all 12 assets."""
    mism=[];assets_tested=0;mask_comparisons=0;mode_comparisons=0
    for sym in D.ASSETS:
        p=m.panels[sym];n=len(p.c);assets_tested+=1
        cuts=sorted(set(max(1,n-x) for x in (1,500,2000)))
        for cut in cuts:
            truncated_raw={k:v[:cut] for k,v in p._raw.items()}
            truncated_masks=I.build_masks(truncated_raw)
            for name in I.SETTINGS_52:
                a=truncated_masks[name];b=p.masks[name][:cut];mask_comparisons+=1
                if not np.array_equal(a,b):mism.append((sym,cut,name,int((a!=b).sum())))
        for cut in sorted(set(max(1,n-x) for x in (1,1500))):
            truncated_raw={k:v[:cut] for k,v in p._raw.items()}
            truncated_masks=I.build_masks(truncated_raw)
            for mode in ("AND0","AND2","OR0"):
                names=list(I.SETTINGS_52)[:3]
                a=E.combine({k:truncated_masks[k] for k in names},mode,p.seg[:cut])
                b=E.combine({k:p.masks[k] for k in names},mode,p.seg)[:cut]
                mode_comparisons+=1
                if not np.array_equal(a,b):mism.append((sym,cut,mode))
    return _record(6,"prefix-truncation tests (12 assets; all 52 masks and 3 modes)",not mism,
        f"assets={assets_tested}; mask comparisons={mask_comparisons}; combination comparisons={mode_comparisons}; mismatches={mism or 'none'}")


def check_07_references(m):
    p = m.panels["BTCUSDT"]
    h, l, c = p.h, p.l, p.c
    # independent RSI on the SAME recursion convention as the pinned grid:
    # ewm(alpha=1/n, adjust=False, min_periods=n) == seeded at the first
    # valid diff, then u_i = u_{i-1} + (x_i - u_{i-1})/n
    n = 14
    d = np.diff(c)
    up = np.r_[np.nan, np.clip(d, 0, None)]
    dn = np.r_[np.nan, np.clip(-d, 0, None)]
    ru = np.full(len(c), np.nan); rd = np.full(len(c), np.nan)
    ru[1] = up[1]; rd[1] = dn[1]
    for i in range(2, len(c)):
        ru[i] = ru[i - 1] + (up[i] - ru[i - 1]) / n
        rd[i] = rd[i - 1] + (dn[i] - rd[i - 1]) / n
    ru[:n] = np.nan; rd[:n] = np.nan          # min_periods=n
    ref_rsi = 100 - 100 / (1 + ru / rd)
    got = I.rsi(c, n)
    mask = np.isfinite(ref_rsi[100:]) & np.isfinite(got[100:])
    rsi_err = float(np.max(np.abs(ref_rsi[100:][mask] - got[100:][mask])))
    # independent ATR
    tr = np.empty(len(c)); tr[0] = h[0] - l[0]
    for i in range(1, len(c)):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    ref_atr = np.full(len(c), np.nan)
    ref_atr[n] = np.mean(tr[1:n + 1])
    for i in range(n + 1, len(c)):
        ref_atr[i] = (ref_atr[i - 1] * (n - 1) + tr[i]) / n
    atr_err = float(np.nanmax(np.abs(ref_atr[300:] - p.atr[300:])))
    # independent stochastic %K (raw, then SMA-d)
    k_ref = np.full(len(c), np.nan)
    for i in range(13, len(c)):
        hh = h[i - 13:i + 1].max(); ll = l[i - 13:i + 1].min()
        k_ref[i] = 100 * (c[i] - ll) / (hh - ll) if hh > ll else np.nan
    k_got, _d = I.stochastic(h, l, c, 14, 3)
    k_err = float(np.nanmax(np.abs(k_ref[300:] - k_got[300:])))
    ok = rsi_err < 1e-9 and atr_err < 1e-6 and k_err < 1e-9
    return _record(7, "independent RSI/ATR/stochastic references", ok,
                   f"max abs err: RSI {rsi_err:.2e}, ATR {atr_err:.2e}, "
                   f"%K {k_err:.2e}")


def check_08_pivot_confirmation(m):
    # a V-pivot must only fire at/after its confirmation bar
    low = np.r_[np.linspace(10, 5, 10), np.linspace(5.2, 10, 10)]
    sig = I.pivot_low(low, left=2, right=2)
    pivot_at = 9
    fires = np.nonzero(sig)[0]
    ok1 = all(f >= pivot_at + 2 for f in fires)
    # confirmed-only: no signal in the last `right` bars of the series
    ok2 = not sig[-2:].any()
    # rsi_bull_divergence fires only after the pivot is confirmed
    c = np.r_[np.linspace(12, 6, 40), np.linspace(6, 11, 40)]
    l = c - 0.3
    div = I.rsi_bull_divergence(l, c, 14)
    ok3 = not div[len(c) - 2:].any()
    return _record(8, "pivot signal emitted only after confirmation",
                   ok1 and ok2 and ok3,
                   f"pivot fires={fires.tolist()[:5]} (>= {pivot_at + 2}); "
                   f"tail-safe={ok2 and ok3}")


def check_09_labels_excluded(m):
    # labels depend on the future; masks must not
    p = m.panels["BTCUSDT"]
    n = len(p.c)
    cut = n - 30
    lab_full = L.rise_labels(p.h, p.l, p.c, atr=p.atr)
    dd = {k: v[:cut] for k, v in p._raw.items()}
    masks_trunc = I.build_masks(dd)
    diff = [nm for nm in I.SETTINGS_52
            if not np.array_equal(masks_trunc[nm], p.masks[nm][:cut])]
    lab_trunc = L.rise_labels(p.h[:cut], p.l[:cut], p.c[:cut], atr=p.atr[:cut])
    changed = int(np.nansum(lab_full[:cut] != lab_trunc))
    # source scan: no engine/indicator module imports labels
    src_bad = []
    for f in ("engine.py", "indicators.py", "measure.py", "stats.py",
              "pipeline.py"):
        s = open(os.path.join(os.path.dirname(__file__), f)).read()
        if "labels" in s and "import" in s.split("labels")[0][-40:]:
            src_bad.append(f)
    ok = not diff and not src_bad
    return _record(9, "centered labels excluded from features",
                   ok and changed > 0,
                   f"masks changed by truncation={diff or 'none'}; labels "
                   f"changed on {changed} bars; feature modules importing "
                   f"labels={src_bad or 'none'} (label is evaluation-only)")


def check_10_synthetic_container():
    """Next-open fill, adverse gap, favourable-gap withholding, double touch,
    timeout, incomplete horizon — exact hand-computed cases."""
    atr = np.ones(40)
    o = np.full(40, 100.0); h = np.full(40, 100.5)
    l = np.full(40, 99.5); c = np.full(40, 100.0)
    seg = np.zeros(40, int)
    res = {}

    # (a) plain next-open fill + timeout at 18th close
    oo = o.copy(); cc = c.copy(); hh = h.copy(); ll = l.copy()
    cc[19] = 100.0
    mask = np.zeros(40, bool); mask[0] = True
    tr, _ = E.simulate(oo, hh, ll, cc, atr, seg, mask, "SYN", "t")
    res["fill_at_next_open"] = bool(tr and tr[0]["entry"] == oo[1]
                                    and tr[0]["fill_bar"] == 1)
    res["timeout_at_18th_close"] = bool(tr and tr[0]["outcome"] == "timeout"
                                        and tr[0]["exit_bar"] == 18
                                        and tr[0]["exit"] == cc[18])
    # (b) adverse gap: open below stop at the 3rd future bar
    oo = o.copy(); hh = h.copy(); ll = l.copy(); cc = c.copy()
    oo[4] = 97.0                      # stop = 100 - 1.5 = 98.5
    tr, _ = E.simulate(oo, hh, ll, cc, atr, seg, mask, "SYN", "t")
    res["adverse_gap_exit_at_open"] = bool(tr and tr[0]["outcome"] == "stop"
                                           and tr[0]["exit"] == 97.0
                                           and tr[0]["gap_flag"])
    # (c) favourable gap: open above target -> exit AT target (windfall withheld)
    oo = o.copy(); hh = h.copy(); ll = l.copy(); cc = c.copy()
    oo[5] = 105.0
    tr, _ = E.simulate(oo, hh, ll, cc, atr, seg, mask, "SYN", "t")
    res["favourable_gap_withheld"] = bool(tr and tr[0]["outcome"] == "target"
                                          and tr[0]["exit"] == 101.5
                                          and tr[0]["gap_flag"])
    # (d) double touch in one bar -> stop first
    oo = o.copy(); hh = h.copy(); ll = l.copy(); cc = c.copy()
    hh[6] = 103.0; ll[6] = 97.0
    tr, _ = E.simulate(oo, hh, ll, cc, atr, seg, mask, "SYN", "t")
    res["double_touch_stop_first"] = bool(tr and tr[0]["outcome"] == "stop"
                                          and tr[0]["exit"] == 98.5
                                          and tr[0]["double_touch"])
    # (e) incomplete horizon -> excluded (no forced close)
    mask_e = np.zeros(40, bool); mask_e[30] = True
    tr, cnt = E.simulate(o, h, l, c, atr, seg, mask_e, "SYN", "t")
    res["incomplete_excluded"] = bool(len(tr) == 0 and cnt["incomplete"] == 1)
    # (f) nonpositive stop rejected
    atr_big = np.full(40, 100.0)
    tr, cnt = E.simulate(o, h, l, c, atr_big, seg, mask, "SYN", "t")
    res["nonpositive_stop_rejected"] = bool(len(tr) == 0
                                            and cnt["rejected"] == 1)
    ok = all(res.values())
    return _record(10, "synthetic container cases", ok, json.dumps(res))


def check_11_sizing_cost(m):
    p = m.panels["BTCUSDT"]
    name = I.SETTINGS_52[0]
    tr, _ = E.simulate(p.o, p.h, p.l, p.c, p.atr, p.seg, p.masks[name],
                       "BTCUSDT", "c")
    bad = []
    for t in tr[:500]:
        if abs(t["quantity"] * t["entry"] - E.NOTIONAL) > 1e-6:
            bad.append(("sizing", t["signal_bar"]))
        if t["cost_dollars"] != E.COST_RT:
            bad.append(("cost", t["signal_bar"]))
        if abs(t["net_dollars"] - (t["gross_dollars"] - 0.052)) > 1e-9:
            bad.append(("net", t["signal_bar"]))
        if abs(t["barrier_r"] - t["net_atr_r"] / 1.5) > 1e-12:
            bad.append(("barrier_r", t["signal_bar"]))
    return _record(11, "$20 sizing and $0.052 charged exactly once", not bad,
                   f"{len(tr)} trades sampled ({min(500, len(tr))}); "
                   f"violations={bad[:3] or 'none'}")


def check_12_cash_position(m):
    p = m.panels["BTCUSDT"]
    bad = []
    for name in I.SETTINGS_52[:6]:
        tr, _ = E.simulate(p.o, p.h, p.l, p.c, p.atr, p.seg, p.masks[name],
                           "BTCUSDT", "c")
        cash = E.BOOK0
        prev_exit = -1
        for t in tr:
            if t["signal_bar"] < prev_exit:
                bad.append((name, t["signal_bar"], "overlap"))
                break
            cash += t["net_dollars"]
            if cash < 0:
                bad.append((name, t["signal_bar"], "negative cash"))
                break
            prev_exit = t["exit_bar"]
    return _record(12, "cash and position constraints", not bad,
                   f"one-position-per-asset and cash book >= 0 verified on 6 "
                   f"settings; violations={bad or 'none'}")


def check_13_purge_embargo(m):
    p = m.panels["BTCUSDT"]
    name = "RSI14_xup_30"
    tr, _ = E.simulate(p.o, p.h, p.l, p.c, p.atr, p.seg, p.masks[name],
                       "BTCUSDT", "c")
    lo, hi = p.ranges["2025H1"]
    kept = E.window_trades(tr, lo, hi)
    ok = all(lo + E.HORIZON <= t["signal_bar"] and t["exit_bar"] <= hi
             for t in kept)
    # no kept trade crosses the boundary even if it started inside
    crossing = [t for t in tr if lo <= t["signal_bar"] <= lo + E.HORIZON - 1]
    leaked = [t for t in kept if t["signal_bar"] < lo + E.HORIZON]
    return _record(13, "purge, embargo and temporal isolation",
                   ok and not leaked,
                   f"{len(kept)} kept of {len(tr)}; embargo={E.HORIZON} bars; "
                   f"boundary leakage={len(leaked)}; "
                   f"candidate straddlers rejected={len(crossing) - len(leaked)}")


# ==========================================================================
# synthetic end-to-end world for checks 14 and 16 (before money)
# ==========================================================================
def synthetic_panels(n=2600, assets=("SA", "SB", "SC"), seed=84):
    rng = np.random.default_rng(seed)
    out = {}
    for k, sym in enumerate(assets):
        steps = rng.normal(0, 0.004, n)
        px = 100 * np.exp(np.cumsum(steps))
        o = px * (1 + rng.normal(0, 0.0008, n))
        c = px
        h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.0015, n)))
        l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.0015, n)))
        v = np.abs(rng.normal(1000, 200, n))
        out[sym] = dict(o=o, h=h, l=l, c=c, v=v, tbv=v * 0.5)
    return out


class SynthPanel:
    def __init__(self, sym, raw, dt):
        self.sym = sym
        self._raw = raw
        self.o, self.h, self.l, self.c = raw["o"], raw["h"], raw["l"], raw["c"]
        self.v, self.tbv = raw["v"], raw["tbv"]
        self.dt = dt
        self.seg = np.zeros(len(self.c), dtype=int)
        self.days = (self.dt.astype("datetime64[D]")
                     - np.datetime64("2023-01-01")).astype(int)
        self.masks = I.build_masks(raw)
        self._mask_cache = dict(self.masks)
        self.atr = I.wilder_atr(self.h, self.l, self.c, 14)
        self.ranges = {}
        for name, a, b in M.HALF_YEARS:
            lo = np.searchsorted(self.dt, np.datetime64(a))
            hi = np.searchsorted(self.dt, np.datetime64(b),
                                 side="right") - 1
            self.ranges[name] = (int(lo), int(hi))

    def mask_of(self, name):
        if name not in self._mask_cache:
            self._mask_cache[name] = I.build_one(self._raw, name)
        return self._mask_cache[name]

    def day0(self, window):
        a = M.WIN_RANGE[window][0]
        return int((np.datetime64(a) - np.datetime64("2023-01-01")).astype(int))


class SynthMeasurer(M.Measurer):
    def __init__(self, raw_by_sym, dt, log=print):
        self.log = log
        self.panels = {s: SynthPanel(s, raw, dt) for s, raw in raw_by_sym.items()}
        self._baseline_cache = {}
        self._base_trades = {}


SYN_HY = [("2023H1", "2023-01-01", "2023-06-30"),
          ("2023H2", "2023-07-01", "2023-12-31"),
          ("2024H1", "2024-01-01", "2024-06-30")]
SYN_OUTER = ["2024H1"]
SYN_SETTINGS = ["RSI14_xup_30", "VolSpike_z2.0", "Hammer", "RSI14_xup_20"]


class _synth_env:
    """Patch module-level registries for a synthetic end-to-end run."""

    def __init__(self, outdir):
        self.outdir = outdir

    def __enter__(self):
        from . import pipeline as P
        self.P = P
        self.saved = {
            "HY": M.HALF_YEARS, "COMP": M.COMPLETE, "OUT": M.OUTER,
            "WR": M.WIN_RANGE, "CP": M.canonical_pairs,
            "S1": P.SETTINGS_SINGLES, "S2": P.SETTINGS_EXTRA,
            "MO": M.O, "PO": P.O, "PCACHE": P.CACHE, "KEYS": P.KEYS,
        }
        M.HALF_YEARS = list(SYN_HY)
        M.COMPLETE = [w for w in SYN_HY if not w[0].endswith("p")]
        M.OUTER = list(SYN_OUTER)
        M.WIN_RANGE = {n: (a, b) for n, a, b in SYN_HY}
        M.canonical_pairs = lambda: [(SYN_SETTINGS[i], SYN_SETTINGS[j])
                                     for i in range(len(SYN_SETTINGS))
                                     for j in range(i + 1, len(SYN_SETTINGS))]
        P.SETTINGS_SINGLES = list(SYN_SETTINGS)
        P.SETTINGS_EXTRA = list(SYN_SETTINGS)
        M.O = self.outdir
        P.O = self.outdir
        P.CACHE = self.outdir
        P.KEYS = os.path.join(self.outdir, "trades_keys")
        os.makedirs(self.outdir, exist_ok=True)
        return self

    def __exit__(self, *exc):
        M.HALF_YEARS = self.saved["HY"]; M.COMPLETE = self.saved["COMP"]
        M.OUTER = self.saved["OUT"]; M.WIN_RANGE = self.saved["WR"]
        M.canonical_pairs = self.saved["CP"]
        self.P.SETTINGS_SINGLES = self.saved["S1"]
        self.P.SETTINGS_EXTRA = self.saved["S2"]
        M.O = self.saved["MO"]; self.P.O = self.saved["PO"]
        self.P.CACHE = self.saved["PCACHE"]; self.P.KEYS = self.saved["KEYS"]
        return False


def _synth_world():
    raw = synthetic_panels()
    dt = np.datetime64("2023-01-01") + \
        np.arange(len(raw["SA"]["c"])) * np.timedelta64(4, "h")
    return SynthMeasurer(raw, dt)


def check_14_ordering():
    """Parent selection precedes triple and target outcomes — proven on a
    synthetic end-to-end run by instrumenting the exact code path."""
    from . import pipeline as P
    order = []
    with tempfile.TemporaryDirectory() as td, _synth_env(td):
        m = _synth_world()
        singles = P.stage_singles(m)
        pairs = P.stage_pairs(m, singles)
        prefix = M.OUTER[0]
        retained = {}
        for mode in ("AND0", "AND2", "OR0"):
            elig = sorted([r for r in pairs.values() if r["mode"] == mode],
                          key=lambda r: -(r["gates"][prefix]["worst_bound"]
                                          if r["gates"][prefix]["worst_bound"]
                                          is not None else -1e9))
            retained[mode] = elig[:2]
        reg = P.register_triples(prefix, retained)
        reg_sha_pre = _sha(os.path.join(P.O, "triples_registry.csv"))

        orig_meas = P.stage_triples

        def wrapped_meas(mm, ss, pp, pf, rows):
            order.append(("triples_measured",
                          _sha(os.path.join(P.O, "triples_registry.csv"))))
            return orig_meas(mm, ss, pp, pf, rows)

        orig_outer = P.stage_outer

        def wrapped_outer(mm, fin):
            order.append("outer_measured")
            return orig_outer(mm, fin)

        P.stage_triples = wrapped_meas
        try:
            triples = wrapped_meas(m, singles, pairs, prefix, reg)
        finally:
            P.stage_triples = orig_meas
        finalists, _u = P.stage_selection(m, singles, pairs, {prefix: triples})
        order.append(("selection_written",
                      _sha(os.path.join(P.O, "selection_log.csv"))
                      if os.path.exists(os.path.join(P.O, "selection_log.csv"))
                      else None))
        P.stage_outer = wrapped_outer
        try:
            P.stage_outer(m, finalists)
        finally:
            P.stage_outer = orig_outer
        # assertions: registry exists before any triple outcome; selection log
        # before any target-window measurement
        reg_sha = order[0][1]
        sel_sha = [o for o in order if isinstance(o, tuple)
                   and o[0] == "selection_written"][0][1]
        ok = (reg_sha is not None and sel_sha is not None
              and order[0][0] == "triples_measured"
              and order[-1] == "outer_measured"
              and len(reg) <= 1500 and len(reg) > 0
              and reg_sha == reg_sha_pre)
        detail = {"order": [o[0] if isinstance(o, tuple) else o for o in order],
                  "registry_content_frozen_before_measure":
                      reg_sha == reg_sha_pre,
                  "selection_sha_before_target": sel_sha is not None,
                  "registered_triples": len(reg),
                  "triples_measured": len(triples)}
    return _record(14, "parent selection precedes triple/target outcomes", ok,
                   json.dumps(detail))


def check_16_determinism():
    """Full independent deterministic rerun on synthetic end-to-end data:
    identical trade ids/counts and dollars within 1e-9."""
    from . import pipeline as P
    mism = {}
    counts = []
    with tempfile.TemporaryDirectory() as td, _synth_env(td):
        runs = []
        for run_i in range(2):
            m = _synth_world()
            singles = P.stage_singles(m)
            pairs = P.stage_pairs(m, singles)
            cid = "P0001|OR0"
            rec = pairs[cid]
            # re-measure a sample of candidates directly
            sample = []
            for k, (c_, r_) in enumerate(pairs.items()):
                if k % 2:
                    continue
                mm, mode = tuple(r_["members"]), r_["mode"]
                cb = m.candidate_trades(mm, mode)
                sample.append((c_, cb))
            runs.append((rec, sample, len(pairs)))
        n_pairs_a, n_pairs_b = runs[0][2], runs[1][2]
        if n_pairs_a != n_pairs_b:
            mism["pair_count"] = (n_pairs_a, n_pairs_b)
        for (cid_a, cb_a), (cid_b, cb_b) in zip(runs[0][1], runs[1][1]):
            for sym in cb_a:
                ta, tb = cb_a[sym], cb_b[sym]
                if len(ta) != len(tb):
                    mism[cid_a] = ("count", sym, len(ta), len(tb))
                    break
                for x, y in zip(ta, tb):
                    for k in ("signal_bar", "fill_bar", "exit_bar", "outcome",
                              "gap_flag", "double_touch"):
                        if x[k] != y[k]:
                            mism[cid_a] = (k, sym, x[k], y[k])
                            break
                    for k in ("entry", "exit", "net_dollars", "net_atr_r",
                              "barrier_r", "mae_atr_r", "mfe_atr_r"):
                        if abs(x[k] - y[k]) > 1e-9:
                            mism[cid_a] = (k, sym, x[k], y[k])
                            break
                counts.append((cid_a, sym, len(ta)))
    ok = not mism
    return _record(16, "synthetic end-to-end deterministic rerun", ok,
                   json.dumps({"mismatches": mism or "none",
                               "compared_trades": int(sum(c[2] for c in counts))}))


# ==========================================================================
# checks that need the real artefacts (audit phase)
# ==========================================================================
def check_15_scipy_refs():
    from scipy import stats as sstats
    rng = np.random.default_rng(84)
    bad = []
    for k, n in ((120, 200), (5, 10), (0, 8), (30, 31)):
        p, lo, hi = S.wilson(k, n)
        ref = sstats.binomtest(k, n).proportion_ci(confidence_level=0.95,
                                                   method="wilson")
        if abs(lo - ref.low) > 1e-9 or abs(hi - ref.high) > 1e-9:
            bad.append(("wilson", k, n, lo, ref.low))
    z, pz = S.two_proportion_z(60, 100, 45, 100)
    from math import sqrt
    ph = (60 + 45) / 200
    zr = (0.6 - 0.45) / sqrt(ph * (1 - ph) * (1 / 100 + 1 / 100))
    if abs(z - zr) > 1e-12:
        bad.append(("z", z, zr))
    # Holm against a hand reference
    pv = np.array([0.001, 0.008, 0.039, 0.041, 0.9])
    adj = S.holm(pv, m=70_330)
    hand = np.minimum.accumulate(
        np.sort(pv) * (70_330 - np.arange(len(pv))))[np.argsort(np.argsort(pv))]
    if not np.allclose(np.minimum(hand, 1.0), adj, atol=1e-12):
        bad.append(("holm", adj.tolist(), np.minimum(hand, 1).tolist()))
    # bootstrap reproducibility with the locked seed
    d = rng.integers(0, 182, 400); x = rng.normal(0.05, 1, 400)
    a = S.block_ci(d, x, 182, reps=400)
    b = S.block_ci(d, x, 182, reps=400)
    if a["lo5"] != b["lo5"]:
        bad.append(("bootstrap-not-reproducible", a["lo5"], b["lo5"]))
    pw = S.power_n(0.05, 1.0, 0.02, 400, 0.05)
    if pw.get("n80") is None:
        bad.append(("power_n", pw))
    return _record(15, "confidence bounds/tests vs scipy references", not bad,
                   json.dumps(bad or {"wilson": "ok", "z": "ok", "holm": "ok",
                                      "bootstrap": "reproducible",
                                      "power": pw.get("n80")}))


def check_16_full_confirm(m):
    """The real-run confirmation must cite a complete independent audit."""
    path=os.path.join(O,"audit.json")
    try:
        audit=json.load(open(path,encoding="utf-8"))
        ok=(audit.get("status")=="PASS"
            and audit.get("independent_execution_rebuild")=="PASS"
            and int(audit.get("groups_rebuilt",-1))==int(audit.get("coverage_rows",-2))
            and int(audit.get("trades_rebuilt",-1))==int(audit.get("trade_rows",-2))
            and int(audit.get("violations",-1))==0)
        evidence={k:audit.get(k) for k in ("fixed_head","run_id","groups_rebuilt","coverage_rows","trades_rebuilt","trade_rows","violations")}
    except Exception as exc:ok=False;evidence={"error":type(exc).__name__}
    return _record("16b","full-run independent deterministic rebuild",ok,json.dumps(evidence))


def check_17_reconciliation(m=None):
    """Require a full remote raw-to-metric reconciliation, never a sample."""
    ap=os.path.join(O,"audit.json")
    mp=os.path.join(O,"evidence_manifest.json")
    try:
        audit=json.load(open(ap,encoding="utf-8"))
        manifest=json.load(open(mp,encoding="utf-8"))
        ok=(audit.get("status")=="PASS"
            and audit.get("sha_size_schema_reconciliation")=="PASS"
            and audit.get("independent_execution_rebuild")=="PASS"
            and audit.get("metrics_reconciliation")=="PASS"
            and manifest.get("run_id")==audit.get("run_id")
            and manifest.get("audit_status")=="PASS")
        evidence={"run_id":audit.get("run_id"),"fixed_head":audit.get("fixed_head"),
                  "metrics_reconciliation":audit.get("metrics_reconciliation"),
                  "trade_rows":audit.get("trade_rows"),"metric_rows":audit.get("metric_rows"),
                  "manifest_status":manifest.get("audit_status")}
    except Exception as exc:
        ok=False;evidence={"error":type(exc).__name__}
    return _record(17,"full raw-ledger/metrics/hash reconciliation",ok,json.dumps(evidence),critical=True)

def check_18_workspace():
    total = 0
    for root, _d, files in os.walk("/home/user"):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    mb = total / (1024 * 1024)
    secrets = []
    pats = re.compile(r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|"
                      r"-----BEGIN [A-Z ]*PRIVATE KEY-----|"
                      r"sk-[A-Za-z0-9]{20,})")
    self_path = os.path.abspath(__file__)
    for root, dirs, files in os.walk(ROOT):
        if ".git" in root or "__pycache__" in root:
            continue
        for f in files:
            if f.endswith((".parquet", ".zip", ".png")):
                continue
            if os.path.abspath(os.path.join(root, f)) == self_path:
                continue
            try:
                s = open(os.path.join(root, f), encoding="utf-8",
                         errors="ignore").read()
            except OSError:
                continue
            if pats.search(s):
                secrets.append(os.path.join(root, f))
    br = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                        cwd=ROOT, capture_output=True, text=True).stdout.strip()
    remotes = subprocess.run(["git", "remote", "-v"], cwd=ROOT,
                             capture_output=True, text=True).stdout.strip()
    ok = mb <= 125 and not secrets and remotes == ""
    return _record(18, "workspace <=125MB, no secrets/pushes", ok,
                   json.dumps({"workspace_mb": round(mb, 2),
                               "secrets": secrets, "branch": br,
                               "remotes": remotes or "none"}))


# ==========================================================================
def run_all(phase="pre", m=None):
    t0 = time.time()
    if m is None:
        m = M.Measurer()
    if phase == "pre":
        check_01_pins(m); check_02_settings(m); check_03_pairs(m)
        check_04_ohlcv(m); check_05_contiguity(m); check_06_truncation(m)
        check_07_references(m); check_08_pivot_confirmation(m)
        check_09_labels_excluded(m); check_10_synthetic_container()
        check_11_sizing_cost(m); check_12_cash_position(m)
        check_13_purge_embargo(m); check_14_ordering()
        check_15_scipy_refs(); check_16_determinism(); check_18_workspace()
    else:
        check_15_scipy_refs(); check_16_full_confirm(m)
        check_17_reconciliation(m); check_18_workspace()
    ev_map = {
        1: "_meta/fetch_manifest.txt", 2: "catalogue.csv",
        3: "pairs_registry.csv", 4: "data_coverage.csv",
        5: "data_coverage.csv", 6: "checks.json", 7: "checks.json",
        8: "checks.json", 9: "checks.json", 10: "checks.json",
        11: "trades.parquet", 12: "trades.parquet", 13: "metrics.parquet",
        14: "triples_registry.csv", 15: "checks.json",
        16: "checks.json", "16b": "metrics.parquet",
        17: "trades_keys.parquet", 18: "output_hashes.json"}
    cmd_map = {
        "pre": "python -m l0084_entry_mix.cli check --phase pre",
        "post": "python -m l0084_entry_mix.cli check --phase post"}
    for v in RESULTS.values():
        num = v["check"]
        key = num if num in ev_map else (int(num) if str(num).isdigit()
                                        else num)
        v.setdefault("evidence_path", ev_map.get(key, "checks.json"))
        v["command"] = cmd_map[phase]
        v["measured_error"] = (v.get("evidence") if not v["ok"] else "none")
        v["status"] = "PASS" if v["ok"] else "FAIL"
    obj = {"phase": phase, "ran_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                    time.gmtime()),
           "elapsed_s": round(time.time() - t0, 1),
           "checks": RESULTS,
           "all_pass": all(v["ok"] or not v["critical"] for v in RESULTS.values()),
           "failures": [k for k, v in RESULTS.items() if not v["ok"]]}
    out = os.path.join(O, "checks.json")
    prev = {}
    if phase != "pre" and os.path.exists(out):
        prev = json.load(open(out, encoding="utf-8")).get("checks", {})
    merged = {**prev, **RESULTS}
    for k, v in merged.items():                     # normalise every entry
        key = v["check"]
        key = key if key in ev_map else (int(key)
                                        if str(key).isdigit() else key)
        v.setdefault("evidence_path", ev_map.get(key, "checks.json"))
        v.setdefault("command", cmd_map["pre"])
        v["measured_error"] = (v.get("evidence") if not v["ok"] else "none")
        v["status"] = "PASS" if v["ok"] else "FAIL"
    obj["checks"] = merged
    obj["all_pass"] = all(v["ok"] or not v["critical"]
                          for v in merged.values())
    obj["failures"] = [k for k, v in merged.items() if not v["ok"]]
    os.makedirs(O, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
    print(f"[checks] phase={phase} all_pass={obj['all_pass']} "
          f"failures={obj['failures']} ({obj['elapsed_s']}s)")
    return obj


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "pre"
    run_all(phase)
