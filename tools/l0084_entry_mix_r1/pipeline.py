#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0084-ENTRY-MIX — pipeline stages (orchestration, registries, measurement,
selection, neighbours, freeze, audit).  Every stage is re-runnable; heavy
intermediates are cached under O/_cache (evidence, kept).

Order of operations is itself evidence: preregistration and triple
registration are written to disk BEFORE the outcomes they precede.
"""
from __future__ import annotations

import hashlib
import json
import gzip
import os
import pickle
import subprocess
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import data as D
from . import engine as E
from . import indicators as I
from . import measure as M
from . import stats as S

ROOT = M.ROOT
O = M.O
WORK = M.WORK
CACHE = os.path.join(O, "_cache")
KEYS = os.path.join(O, "trades_keys")
INNER_ALL = ["2022H1", "2022H2", "2023H1", "2023H2", "2024H1", "2024H2",
             "2025H1", "2025H2", "2026H1"]
# patchable universes (synthetic end-to-end checks 14/16 shrink them)
SETTINGS_SINGLES = list(I.SETTINGS_52)
SETTINGS_EXTRA = list(I.SETTINGS_52)


def _all_windows():
    return [w[0] for w in M.HALF_YEARS]


def _inner_all():
    return M.inner_windows(M.OUTER[-1])
ALL_WINDOWS = [w[0] for w in M.HALF_YEARS]


def utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def journal(event, **kw):
    os.makedirs(O, exist_ok=True)
    rec = {"event": event, "ts_utc": utc()}
    rec.update(kw)
    with open(os.path.join(O, "run_journal.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[journal] {event} {kw if kw else ''}", flush=True)


def dump_json(name, obj):
    with open(os.path.join(O, name), "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, default=str)


def load_json(name, default=None):
    p = os.path.join(O, name)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def try_import_pyarrow():
    try:
        import pyarrow  # noqa: F401
        return True
    except Exception:                                         # noqa: BLE001
        subprocess.run(["pip", "install", "-q", "pyarrow"], check=False)
        try:
            import pyarrow  # noqa: F401
            return True
        except Exception:                                     # noqa: BLE001
            return False


# ==========================================================================
# stage 1 — registries and preregistration (before any outcome)
# ==========================================================================
def stage_preregister(m=None):
    os.makedirs(O, exist_ok=True)
    owns = m is None
    if owns:
        m = M.Measurer()
    # ---- sources.json
    src_rows = []
    for line in open(os.path.join(ROOT, "_meta", "fetch_manifest.txt"),
                     encoding="utf-8"):
        parts = line.strip().split("|")
        code, commit, path, size, sha = parts[:5]
        url = parts[5] if len(parts) > 5 else ""
        src_rows.append({"commit": commit, "path": path, "url": url,
                         "http_status": int(code), "sha256": sha,
                         "bytes": int(size),
                         "versions": {"python": "3.13.14",
                                      "numpy": np.__version__,
                                      "pandas": pd.__version__},
                         "errors": []})
    dump_json("sources.json", {"fetched_utc": utc(), "sources": src_rows})
    # ---- catalogue.csv (mask hashes over the 12 assets, duplicates visible)
    rows = []
    for name in I.SETTINGS_52:
        h = hashlib.sha256()
        ntrue = 0
        for sym in D.ASSETS:
            mask = m.panels[sym].masks[name]
            h.update(np.packbits(mask).tobytes())
            ntrue += int(mask.sum())
        rows.append({"setting": name, "definition": name, "parameters": "",
                     "source_commit": "62f4d255e0fc6fce8e7c331a6349484ccb0b8fc0",
                     "mask_hash": h.hexdigest(), "duplicate_of": "",
                     "n_true_12assets": ntrue})
    byh = {}
    for r in rows:
        byh.setdefault(r["mask_hash"], []).append(r["setting"])
    for h, names in byh.items():
        for r in rows:
            if r["mask_hash"] == h and r["setting"] != sorted(names)[0]:
                r["duplicate_of"] = sorted(names)[0]
    pd.DataFrame(rows).to_csv(os.path.join(O, "catalogue.csv"), index=False)
    # ---- pairs_registry.csv
    prows = []
    for n, (a, b) in enumerate(M.canonical_pairs(), start=1):
        for mode in ("AND0", "AND2", "OR0"):
            prows.append({"pair_id": f"P{n:04d}", "member_a": a,
                          "member_b": b, "mode": mode,
                          "canonical_id": f"P{n:04d}|{mode}"})
    pd.DataFrame(prows).to_csv(os.path.join(O, "pairs_registry.csv"),
                               index=False)
    # ---- data_coverage.csv
    cov = []
    for sym in D.ASSETS:
        p = m.panels[sym]
        path = os.path.join(WORK, f"{sym}_4h.parquet")
        dt = pd.to_datetime(p.dt)
        segs = np.unique(p.seg)
        gaps = 0
        for s in segs:
            idx = np.nonzero(p.seg == s)[0]
            if len(idx) > 1:
                d = np.diff(idx)
                gaps += int((d > 1).sum())
        cov.append({"symbol": sym, "rows": len(p.c), "segments": len(segs),
                    "intra_segment_gaps": gaps,
                    "first_utc": str(dt[0]), "last_utc": str(dt[-1]),
                    "parquet_sha256": sha256_file(path)})
    pd.DataFrame(cov).to_csv(os.path.join(O, "data_coverage.csv"), index=False)
    # ---- preregistration.json
    reg = {
        "lane": "L0084-ENTRY-MIX",
        "written_utc": utc(),
        "written_before_any_measurement": True,
        "universe": {"assets": D.ASSETS, "timeframe": "4h UTC",
                     "start": "2021-01-01", "end": "2026-09-27",
                     "source": "data.binance.vision"},
        "pins": {"main": "71f52f0741cdaceb71797b1fe07de07db31fcced",
                 "grid_52": "62f4d255e0fc6fce8e7c331a6349484ccb0b8fc0",
                 "cost_model_l0082": "2d8e8f3afca6a72679382780ddaeb0d71de2cad6"},
        "settings_52": I.SETTINGS_52,
        "modes": {"AND0": "all members true at i",
                  "AND2": "every member true in i-2..i; >=1 at i; contiguous",
                  "OR0": ">=1 member true at i"},
        "counts": M.counts_check(),
        "outer_windows": M.OUTER,
        "inner_windows_by_prefix": {o: M.inner_windows(o) for o in M.OUTER},
        "half_years": M.HALF_YEARS,
        "container": {"notional_usd": E.NOTIONAL, "cost_rt_usd": E.COST_RT,
                      "barrier_atr": E.BARRIER_ATR, "horizon_bars": E.HORIZON,
                      "fill": "next contiguous open q; ATR from i",
                      "book_usd_per_asset": E.BOOK0,
                      "stop": "q-1.5ATR", "target": "q+1.5ATR",
                      "gaps_first": True, "double_touch": "stop first",
                      "incomplete_horizon": "exclude, never force close"},
        "gates": {"min_executed_trades": M.GATE_MIN_TRADES,
                  "min_positive_assets": M.GATE_MIN_POS_ASSETS,
                  "min_pf": M.GATE_MIN_PF,
                  "bootstrap_lo5_gt_zero": True,
                  "paired_improvement_lo5_gt_zero": True},
        "ranking_pairs": ["worst_window_bound_desc", "minimum_count_desc",
                          "canonical_id_asc"],
        "retention": {"pairs_per_mode": 10, "triple_trials_cap_per_prefix": 1500},
        "selection": ["worst_window_bound_desc", "fewer_members",
                      "larger_minimum_count", "id_asc", "else CASH"],
        "bull": {"triple_cap_before_dedup": 1500, "potential_family": 66300,
                 "holm_family": 70330},
        "bootstrap": {"reps": S.REPS, "block_days": S.BLOCK_DAYS,
                      "seed": S.SEED, "synchronised_across_assets": True},
        "seed": 84,
        "freeze": {"max_provisional": 1, "future_start_rule":
                   "first eligible complete bar after freeze commit UTC",
                   "end_condition": "BOTH 100 executed trades and 90 days",
                   "until_then": "NOT MEASURED"},
        "neighbours": {"rule": "one numeric period/threshold/band per step "
                       "+-20%; register first; >=80% positive every window; "
                       "each positive >=0.6 of finalist net; separate Holm",
                       "promotion": False},
        "pending": ["corrected local 76-grid package not present at inspected "
                    "tips (PENDING, no substitute)",
                    "L0083 V3 headlines (RSI10/12, +5.24pt, +0.0545 ATR-R) "
                    "documented only, not recomputed nor used as a basis"],
        "no_adoption": True, "no_live_orders": True,
    }
    dump_json("preregistration.json", reg)
    # ---- catalogue_pending.md
    with open(os.path.join(O, "catalogue_pending.md"), "w",
              encoding="utf-8") as fh:
        fh.write("# L0084 — pending / not-found items\n\n"
                 "Status vocabulary: PENDING (not found at inspected pins; "
                 "no substitute used, no negative verdict implied).\n\n"
                 "| item | status | detail |\n|---|---|---|\n"
                 "| corrected local 76-grid package | PENDING | not present at "
                 "the inspected pins; the 52-grid pinned package is used |\n"
                 "| L0083 V3 headline numbers | DOCUMENTED ONLY | RSI10/12, "
                 "lift +5.24 pt, net +0.0545 ATR-R — carried as written "
                 "history; never re-based |\n")
    reg_sha = sha256_file(os.path.join(O, "preregistration.json"))
    head = git_commit("L0084 preregistration + registries (before outcomes)",
                      first=True)
    journal("preregister", preregistration_sha256=reg_sha,
            pairs=len(prows), catalogue=len(rows), commit=head)
    return m, reg


def git_commit(message, first=False):
    """Local git commits are forbidden in R1; publisher must use API commits."""
    raise RuntimeError("R1 repository writes must use the compare-and-update GitHub API publisher; local git commit disabled")


# ==========================================================================
# stage 3a — singletons (all twelve half-years; day arrays for pairing)
# ==========================================================================
def stage_singles(m):
    """Measure each singleton in isolated half-year books, resetting cash and
    position state at every window. No prior-window trade can alter a later one."""
    t0=time.time();out={}
    for name in SETTINGS_SINGLES:
        per={}
        for w in _all_windows():
            trades=m.candidate_trades((name,),"AND0",window=w)
            pooled=m.windowed(trades,w)
            per[w]=m.stat_window(pooled,w) if pooled else None
        out[name]=per
    journal("singles_done",n=len(out),elapsed_s=round(time.time()-t0,1),window_state="fresh $1,000 book per asset/candidate/window")
    return out


# ==========================================================================
# stage 3b — the full 52x51x3 pair grid
# ==========================================================================
def stage_pairs(m, singles, batch=150):
    t0 = time.time()
    os.makedirs(KEYS, exist_ok=True)
    pairs = M.canonical_pairs()
    records = {}
    buf = {k: [] for k in ("meta", "asset", "sig", "exit", "code", "flag")}
    cand_idx = 0
    part = 0
    t_last = time.time()
    for n, (a, b) in enumerate(pairs, start=1):
        for mode in ("AND0", "AND2", "OR0"):
            cid = f"P{n:04d}|{mode}"
            cb_all={sym:[] for sym in m.panels}
            wstats={};wdays={}
            for w in _all_windows():
                cb=m.candidate_trades((a,b),mode,window=w)
                for sym in cb_all:cb_all[sym].extend(cb[sym])
                pooled=m.windowed(cb,w)
                st=m.stat_window(pooled,w) if pooled else None
                if st is not None:wdays[w]=(st["days"],st["nets"])
                wstats[w]={k:v for k,v in (st or {}).items() if k not in ("days","nets")} if st else None
                del cb
            gates = {}
            for outer in M.OUTER:
                win = [w for w in _inner_all() if w < outer]
                rows = []
                el = True
                worst, minc = None, 10 ** 9
                for w in win:
                    st = wstats.get(w)
                    ev = {"window": w, "pass": False, "n_exec": 0,
                          "pos_assets": 0, "pf": 0.0, "exp_lo5": None,
                          "expectancy": None, "paired": {}}
                    if st is not None:
                        ev.update(n_exec=st["n_exec"],
                                  pos_assets=st["pos_assets"], pf=st["pf"],
                                  exp_lo5=st["exp_lo5"],
                                  expectancy=st["expectancy"])
                        ok = (st["n_exec"] >= M.GATE_MIN_TRADES
                              and st["pos_assets"] >= M.GATE_MIN_POS_ASSETS
                              and st["pf"] >= M.GATE_MIN_PF
                              and st["exp_lo5"] > 0)
                        da, na = wdays[w]
                        for ctrl in (a, b):
                            cs = (singles.get(ctrl) or {}).get(w)
                            if cs is None:
                                ok = False
                                ev["paired"][ctrl] = None
                                continue
                            d = S.paired_block_diff(da, na, cs["days"],
                                                    cs["nets"], st["n_days"])
                            ev["paired"][ctrl] = {"diff": d["diff"],
                                                  "lo5": d["lo5"]}
                            if not (d["lo5"] > 0):
                                ok = False
                        ev["pass"] = ok
                        if not ok:
                            el = False
                        if ev["exp_lo5"] is not None and (worst is None
                                                          or ev["exp_lo5"] < worst):
                            worst = ev["exp_lo5"]
                        minc = min(minc, st["n_exec"])
                    else:
                        el = False
                    rows.append(ev)
                gates[outer] = {"eligible": bool(el), "rows": rows,
                                "worst_bound": worst,
                                "minimum_count": minc if minc < 10 ** 9 else 0}
            records[cid] = {"cid": cid, "members": [a, b], "mode": mode,
                            "windows": wstats, "gates": gates}
            for sym_i, sym in enumerate(list(m.panels.keys())):
                for t in cb_all[sym]:
                    buf["meta"].append(cand_idx)
                    buf["asset"].append(sym_i)
                    buf["sig"].append(t["signal_bar"])
                    buf["exit"].append(t["exit_bar"])
                    buf["code"].append(OUTCOME_CODE[t["outcome"]])
                    buf["flag"].append((1 if t["gap_flag"] else 0)
                                       | (2 if t["double_touch"] else 0))
            cand_idx += 1
            del cb_all
        if n % batch == 0:
            _flush_keys(part, buf)
            part += 1
            buf = {k: [] for k in buf}
            journal("pairs_progress", pairs_done=n, candidates=cand_idx,
                    elapsed_s=round(time.time() - t0, 1),
                    step_s=round(time.time() - t_last, 1))
            t_last = time.time()
    if buf["meta"]:
        _flush_keys(part, buf)
    _merge_keys(part + 1)
    with gzip.open(os.path.join(CACHE, "pairs.pkl.gz"), "wb") as fh:
        pickle.dump(records, fh, protocol=4)
    journal("pairs_done", candidates=cand_idx, elapsed_s=round(time.time() - t0, 1))
    return records


OUTCOME_CODE = {"stop": 0, "target": 1, "timeout": 2}


def _flush_keys(part, buf):
    df = pd.DataFrame({"candidate_idx": np.asarray(buf["meta"], dtype="uint16"),
                       "asset_idx": np.asarray(buf["asset"], dtype="uint8"),
                       "signal_bar": np.asarray(buf["sig"], dtype="uint16")})
    df.sort_values(["candidate_idx", "asset_idx", "signal_bar"],
                   inplace=True, ignore_index=True)
    df.to_parquet(os.path.join(KEYS, f"parts-{part:03d}.parquet"),
                  index=False, compression="zstd")


def _merge_keys(n_parts):
    frames = []
    names = sorted(f for f in os.listdir(KEYS) if f.startswith("parts-"))
    for f in names:
        frames.append(pd.read_parquet(os.path.join(KEYS, f)))
    df = pd.concat(frames, ignore_index=True) if frames else \
        pd.DataFrame(columns=["candidate_idx", "asset_idx", "signal_bar"])
    if frames:
        df.sort_values(["candidate_idx", "asset_idx", "signal_bar"],
                       inplace=True, ignore_index=True)
        out = os.path.join(O, "trades_keys.parquet")
        df.to_parquet(out, index=False, compression="zstd")
        for f in names:
            os.remove(os.path.join(KEYS, f))
    index = {"n_candidates": (int(df["candidate_idx"].max()) + 1) if frames else 0,
             "order": "(pair_id, mode) enumeration of pairs_registry then "
                      "registered triples in registration order",
             "schema": ["candidate_idx uint16", "asset_idx uint8 "
                        "(index into data_coverage.assets order)",
                        "signal_bar uint16 (bar index in the asset series)"],
             "note": "fill_bar=signal_bar+1; outcome/exit/flags and every "
                     "other trade field are re-derived exactly from retained "
                     "market data + the locked engine by `cli audit --rebuild`"}
    dump_json("trades_keys.index.json", index)


# ==========================================================================
# stage 3c — triples per prefix (registered BEFORE outcomes)
# ==========================================================================
def select_retained(records, prefix):
    kept = {}
    for mode in ("AND0", "AND2", "OR0"):
        elig = [r for r in records.values()
                if r["mode"] == mode and r["gates"][prefix]["eligible"]]
        elig.sort(key=lambda r: (-(r["gates"][prefix]["worst_bound"]
                                   if r["gates"][prefix]["worst_bound"] is not None
                                   else -1e9),
                                 -r["gates"][prefix]["minimum_count"],
                                 r["cid"]))
        kept[mode] = elig[:10]
    return kept


def register_triples(prefix, retained):
    """triples_registry rows (before outcomes); cap 1500 before dedup."""
    rows, seen, seq = [], {}, 0
    for mode in ("AND0", "AND2", "OR0"):
        for pr in retained[mode]:
            members = pr["members"]
            for extra in SETTINGS_EXTRA:
                if extra in members:
                    continue
                tri = tuple(sorted(list(members) + [extra]))
                key = (tri, mode)
                if key in seen:
                    seen[key]["parent_ids"] += ";" + pr["cid"]
                    continue
                if seq >= 1500:
                    break
                seq += 1
                rows.append({"prefix_id": prefix,
                             "triple_id": f"T{seq:05d}|{mode}",
                             "member_a": tri[0], "member_b": tri[1],
                             "member_c": tri[2], "mode": mode,
                             "parent_ids": pr["cid"], "eligible": "",
                             "reason": "registered_pre_outcome"})
                seen[key] = rows[-1]
    path = os.path.join(O, "triples_registry.csv")
    df = pd.DataFrame(rows)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        try:
            prev = pd.read_csv(path)
            if "prefix_id" in prev.columns:
                prev = prev[prev["prefix_id"] != prefix]      # idempotent
            df = pd.concat([prev, df], ignore_index=True)
        except pd.errors.EmptyDataError:
            pass
    if len(df):
        df.to_csv(path, index=False)
    return rows


def stage_triples(m, singles, pairs, prefix, reg_rows):
    """Measure registered triples on the prefix's inner windows only, with
    paired superiority vs its 3 singleton members and vs every constituent
    pair (same mode) taken from the already-measured pair grid."""
    inner = M.inner_windows(prefix)
    pair_cache = {}
    out, seen = {}, {}
    for row in reg_rows:
        members = (row["member_a"], row["member_b"], row["member_c"])
        mode = row["mode"]
        cb_all={sym:[] for sym in m.panels}
        wstats,wdays={},{}
        for w in inner:
            cb=m.candidate_trades(members,mode,window=w)
            for sym in cb_all:cb_all[sym].extend(cb[sym])
            pooled=m.windowed(cb,w)
            st=m.stat_window(pooled,w) if pooled else None
            if st is not None:
                wdays[w]=(st["days"],st["nets"])
                wstats[w]={k:v for k,v in st.items() if k not in ("days","nets")}
            del cb
        prof = tuple((w, (wstats.get(w) or {}).get("n_exec"),
                      (wstats.get(w) or {}).get("net")) for w in inner)
        rec = {"triple_id": row["triple_id"], "members": list(members),
               "mode": mode, "parent_ids": row["parent_ids"],
               "duplicate_of": "", "windows": wstats, "gates": {},
               "paired_singles": {}, "paired_pairs": {}}
        if prof in seen:
            rec["duplicate_of"] = seen[prof]
            out[row["triple_id"]] = rec
            del cb_all
            continue
        seen[prof] = row["triple_id"]
        el, worst, minc, rows = True, None, 10 ** 9, []
        for w in inner:
            st = wstats.get(w)
            ev = {"window": w, "pass": False, "n_exec": 0, "pos_assets": 0,
                  "pf": 0.0, "exp_lo5": None, "expectancy": None,
                  "paired": {}}
            if st is not None:
                ev.update(n_exec=st["n_exec"], pos_assets=st["pos_assets"],
                          pf=st["pf"], exp_lo5=st["exp_lo5"],
                          expectancy=st["expectancy"])
                ok = (st["n_exec"] >= M.GATE_MIN_TRADES
                      and st["pos_assets"] >= M.GATE_MIN_POS_ASSETS
                      and st["pf"] >= M.GATE_MIN_PF
                      and st["exp_lo5"] > 0)
                da, na = wdays[w]
                for ctrl in members:
                    cs = (singles.get(ctrl) or {}).get(w)
                    if cs is None:
                        ok = False
                        rec["paired_singles"][f"{w}|{ctrl}"] = None
                        continue
                    d = S.paired_block_diff(da, na, cs["days"], cs["nets"],
                                            st["n_days"])
                    rec["paired_singles"][f"{w}|{ctrl}"] = {"diff": d["diff"],
                                                            "lo5": d["lo5"]}
                    if not (d["lo5"] > 0):
                        ok = False
                ev["pass"] = ok
                if not ok:
                    el = False
                if ev["exp_lo5"] is not None and (worst is None
                                                  or ev["exp_lo5"] < worst):
                    worst = ev["exp_lo5"]
                minc = min(minc, st["n_exec"])
            else:
                el = False
            rows.append(ev)
        for i in range(3):
            for j in range(i + 1, 3):
                pkey = tuple(sorted((members[i], members[j])))
                label = f"{pkey[0]}+{pkey[1]}"
                for w in inner:
                    st = wstats.get(w)
                    if st is None:
                        continue
                    if pkey not in pair_cache:
                        pc={}
                        for ww in inner:
                            cbp=m.candidate_trades(pkey,mode,window=ww)
                            pooled=m.windowed(cbp,ww)
                            pc[ww]=m.stat_window(pooled,ww) if pooled else None
                        pair_cache[pkey]=pc
                    s2 = pair_cache[pkey].get(w)
                    if s2 is None:
                        el = False
                        rec["paired_pairs"][f"{w}|{label}"] = None
                        continue
                    da, na = wdays[w]
                    d = S.paired_block_diff(da, na, s2["days"], s2["nets"],
                                            st["n_days"])
                    rec["paired_pairs"][f"{w}|{label}"] = {"diff": d["diff"],
                                                           "lo5": d["lo5"]}
                    if not (d["lo5"] > 0):
                        el = False
        rec["gates"] = {"eligible": bool(el), "rows": rows,
                        "worst_bound": worst,
                        "minimum_count": minc if minc < 10 ** 9 else 0}
        out[row["triple_id"]] = rec
        del cb_all
    return out
PairsIndex = {}


# ==========================================================================
# stage 4 — per-prefix selection, rolling outer evaluation, selection log
# ==========================================================================
def _worst_min(rows):
    vals = [r["exp_lo5"] for r in rows if r.get("exp_lo5") is not None]
    worst = min(vals) if vals else None
    minc = min([r["n_exec"] for r in rows], default=0)
    return worst, minc


def stage_selection(m, singles, pairs, triples_by_prefix):
    """Rolling selection inside every prefix; target-window outcomes are read
    only AFTER the choice (check 14 evidence)."""
    log_rows = []
    finalists = {}
    union_cache = {}
    for prefix in M.OUTER:
        inner = M.inner_windows(prefix)
        cands = []
        # ---- singles: gates + superiority over the no-signal book
        for name, per in singles.items():
            rows, ok = [], True
            for w in inner:
                st = per.get(w)
                ev = {"window": w, "n_exec": 0, "pos_assets": 0, "pf": 0.0,
                      "exp_lo5": None, "paired_base_lo5": None, "pass": False}
                if st is None:
                    ok = False
                else:
                    if w not in m._base_trades:
                        m.baseline(w)
                    bd, bn = m._base_trades[w]
                    d = S.paired_block_diff(st["days"], st["nets"], bd, bn,
                                            st["n_days"])
                    ev.update(n_exec=st["n_exec"], pos_assets=st["pos_assets"],
                              pf=st["pf"], exp_lo5=st["exp_lo5"],
                              paired_base_lo5=d["lo5"])
                    gate = (st["n_exec"] >= M.GATE_MIN_TRADES
                            and st["pos_assets"] >= M.GATE_MIN_POS_ASSETS
                            and st["pf"] >= M.GATE_MIN_PF
                            and st["exp_lo5"] > 0 and d["lo5"] > 0)
                    ev["pass"] = bool(gate)
                    if not gate:
                        ok = False
                rows.append(ev)
            worst, minc = _worst_min(rows)
            cands.append({"id": name, "stage": "single", "n_members": 1,
                          "member_names": (name,), "mode": "AND0",
                          "eligible": bool(ok), "worst_bound": worst,
                          "minimum_count": minc, "windows": rows})
        # ---- pairs
        for cid, rec in pairs.items():
            rows, ok = [], True
            for w in inner:
                st = rec["windows"].get(w)
                ev = {"window": w, "n_exec": 0, "pos_assets": 0, "pf": 0.0,
                      "exp_lo5": None, "paired": {}, "pass": False}
                g = rec["gates"][prefix]["rows"]
                mine = next((r for r in g if r["window"] == w), None)
                if mine is not None:
                    ev.update({k: mine[k] for k in
                               ("n_exec", "pos_assets", "pf", "exp_lo5",
                                "paired")})
                ev["pass"] = bool(mine and mine["pass"])
                if not ev["pass"]:
                    ok = False
                rows.append(ev)
            worst, minc = _worst_min(rows)
            cands.append({"id": cid, "stage": "pair", "n_members": 2,
                          "member_names": tuple(rec["members"]),
                          "mode": rec["mode"],
                          "eligible": bool(ok), "worst_bound": worst,
                          "minimum_count": minc, "windows": rows})
        # ---- triples (eligible = registry-measured + window dedup + superset)
        for tid, rec in (triples_by_prefix.get(prefix) or {}).items():
            g = rec["gates"] or {}
            rows = g.get("rows") or []
            prof = tuple((w, (rec["windows"].get(w) or {}).get("n_exec"))
                         for w in inner)
            dup = tuple((w, (rec["windows"].get(w) or {}).get("n_exec"),
                         (rec["windows"].get(w) or {}).get("net"))
                        for w in inner)
            cands.append({"id": tid, "stage": "triple", "n_members": 3,
                          "member_names": tuple(rec["members"]),
                          "mode": rec["mode"],
                          "eligible": bool(g.get("eligible")),
                          "duplicate_of": rec.get("duplicate_of", ""),
                          "worst_bound": g.get("worst_bound"),
                          "minimum_count": g.get("minimum_count", 0),
                          "windows": rows})
        # ---- rank + select
        elig = [c for c in cands if c["eligible"]]
        elig.sort(key=lambda c: (-(c["worst_bound"] if c["worst_bound"]
                                   is not None else -1e9),
                                 c["n_members"], -c["minimum_count"], c["id"]))
        for rank, c in enumerate(elig, start=1):
            c["rank"] = rank
        chosen = elig[0]["id"] if elig else "CASH"
        finalists[prefix] = {"chosen": chosen,
                             "detail": elig[0] if elig else None,
                             "inner": inner}
        journal("selection", prefix=prefix, chosen=chosen,
                eligible=len(elig), inner_windows=inner)
        union_cache[prefix] = cands
        for c in cands:
            log_rows.append({
                "prefix": prefix, "candidate": c["id"], "stage": c["stage"],
                "members": c["n_members"], "eligible": c["eligible"],
                "worst_bound": c["worst_bound"],
                "minimum_count": c["minimum_count"],
                "rank": c.get("rank", ""),
                "selected": int(c["id"] == chosen),
                "reason": ("selected" if c["id"] == chosen
                           else ("eligible_not_selected" if c["eligible"]
                                 else "ineligible")),
                "source_windows": ";".join(inner),
                "duplicate_of": c.get("duplicate_of", "")})
        if chosen == "CASH":
            log_rows.append({"prefix": prefix, "candidate": "CASH",
                             "stage": "cash", "members": 0, "eligible": True,
                             "worst_bound": "", "minimum_count": "",
                             "rank": 1, "selected": 1,
                             "reason": "no eligible candidate", "source_windows": ";".join(inner),
                             "duplicate_of": ""})
    pd.DataFrame(log_rows).to_csv(os.path.join(O, "selection_log.csv"),
                                  index=False)
    return finalists, union_cache


def candidate_bundle(m, cid):
    """Resolve a candidate id back to (members, mode)."""
    if cid.startswith("P"):
        pid, mode = cid.split("|")
        n = int(pid[1:])
        pairs = M.canonical_pairs()
        return tuple(pairs[n - 1]), mode
    if cid.startswith("T"):
        return None, None
    return (cid,), "AND0"


def candidate_trades_names(m, member_names, mode, window=None):
    """Measure original or perturbed setting under the same isolated window book."""
    out={}
    for sym,p in m.panels.items():
        masks={nm:p.mask_of(nm) for nm in member_names};comb=E.combine(masks,mode,p.seg)
        if window is None:trades,_cnt=E.simulate(p.o,p.h,p.l,p.c,p.atr,p.seg,comb,sym,"cand")
        else:
            lo,hi=p.ranges[window];trades,_cnt=E.simulate_window(p.o,p.h,p.l,p.c,p.atr,p.seg,comb,sym,"cand",lo,hi)
        out[sym]=trades
    return out


def stage_outer(m, finalists):
    """Measure each prefix finalist ON its target window (post-selection)."""
    rows = []
    for prefix, info in finalists.items():
        chosen = info["chosen"]
        base = m.baseline(prefix)
        r = {"prefix": prefix, "window": prefix, "selected": chosen,
             "inner_windows": ";".join(info["inner"])}
        if chosen == "CASH":
            r.update({"n_exec": 0, "win_rate": None, "expectancy": None,
                      "exp_lo5": None, "net": None, "pf": None,
                      "pos_assets": 0,
                      "baseline_win": base["win_rate"] if base else None,
                      "baseline_exp": base["expectancy"] if base else None,
                      "note": "CASH selection"})
            rows.append(r)
            continue
        det = info.get("detail") or {}
        members = tuple(det.get("member_names") or ())
        mode = det.get("mode")
        if not members or mode is None:
            r["note"] = "unresolved candidate id"
            rows.append(r)
            continue
        cb = m.candidate_trades(members, mode, window=prefix)
        pooled = m.windowed(cb, prefix)
        st = m.stat_window(pooled, prefix) if pooled else None
        if st is None:
            r["note"] = "no trades inside target window"
            rows.append(r)
            continue
        r.update({"mode": mode, "members": "|".join(members),
                  "n_exec": st["n_exec"], "win_rate": st["win_rate"],
                  "expectancy": st["expectancy"], "exp_lo5": st["exp_lo5"],
                  "net": st["net"], "pf": st["pf"],
                  "pos_assets": st["pos_assets"],
                  "baseline_win": st["baseline_win"],
                  "baseline_exp": st["baseline_exp"],
                  "lift_win_pts": st["lift_win_pts"],
                  "breakeven_ref": st["breakeven_ref"],
                  "timeout_share": st["timeout_share"]})
        rows.append(r)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(O, "outer_windows.csv"), index=False)
    return rows


# ==========================================================================
# stage 5 — controls: no-signal, random-entry (200), buy-and-hold
# ==========================================================================
def random_entries_for_asset(m, p, window, count, cand_label, replicate):
    """Uniform-without-replacement random starts, one-position rule enforced
    chronologically; returns executed trades (<= count) or [] if impossible."""
    lo, hi = p.ranges[window]
    n = len(p.c)
    first = lo + E.HORIZON                     # embargo at the left boundary
    last = hi - E.HORIZON                      # horizon must fit inside window
    elig = np.arange(first, last + 1)
    if elig.size == 0 or count == 0:
        return []
    rng = np.random.default_rng(M.sha_seed(
        f"84|{p.sym}|{window}|{cand_label}|{replicate}"))
    order = rng.permutation(elig)              # uniform without replacement
    chosen = []
    busy = -1
    for i in order:
        i = int(i)
        if i < busy:
            continue
        chosen.append(i)
        busy = i + E.HORIZON                   # signal at exit close, fill next open
        if len(chosen) >= count:
            break
    chosen.sort()
    recs, _bad = E.execute_many(p.o, p.h, p.l, p.c, p.atr, p.seg,
                                np.asarray(chosen), p.sym, cand_label)
    return recs


def stage_controls(m, finalists, singles):
    """Per finalist per window: baseline book, 200 random-entry replicates,
    equal-capital buy-and-hold and $20 hold.  Summaries only (compact)."""
    rows = []
    per = {}
    targets = {pfx: info for pfx, info in finalists.items()}
    # no-signal book rows for every prefix/window (available regardless of
    # whether any candidate qualified)
    for prefix in M.OUTER:
        for w in M.inner_windows(prefix) + [prefix]:
            b = m.baseline(w)
            if b is None:
                continue
            rows.append({"candidate": "NO-SIGNAL", "prefix": prefix,
                         "window": w, "n_exec": b["n"],
                         "expectancy": b["expectancy"],
                         "win_rate": b["win_rate"],
                         "baseline_win": b["win_rate"],
                         "note": "no-signal barrier book (buy whenever flat)"})
    for prefix, info in targets.items():
        det = info.get("detail") or {}
        if info["chosen"] == "CASH" or not det:
            continue
        members, mode = tuple(det["member_names"]), det["mode"]
        wins = list(info["inner"]) + [prefix]
        for w in wins:
            cb = m.candidate_trades(members, mode, window=w)
            pooled = m.windowed(cb, w)
            if not pooled:
                continue
            st = m.stat_window(pooled, w)
            counts = {}
            for t in pooled:
                counts[t["symbol"]] = counts.get(t["symbol"], 0) + 1
            # ---- random-entry controls (200 replicates, matched count)
            rep_rows = []
            unmatched = 0
            for rep in range(200):
                tr_all = []
                for sym, p in m.panels.items():
                    need = counts.get(sym, 0)
                    recs = random_entries_for_asset(m, p, w, need,
                                                    info["chosen"], rep)
                    if len(recs) < need:
                        unmatched += 1
                    tr_all.extend(recs)
                if not tr_all:
                    rep_rows.append({"replicate": rep, "n": 0,
                                     "expectancy": None, "net": None,
                                     "win_rate": None})
                    continue
                nets = np.array([t["net_dollars"] for t in tr_all])
                wins_ = sum(1 for t in tr_all if t["outcome"] == "target")
                dec = sum(1 for t in tr_all if t["outcome"] in
                          ("target", "stop"))
                rep_rows.append({"replicate": rep, "n": len(tr_all),
                                 "expectancy": float(nets.mean()),
                                 "net": float(nets.sum()),
                                 "win_rate": (wins_ / dec) if dec else None})
            rr = pd.DataFrame(rep_rows)
            rand_summary = {"reps": len(rr), "unmatched_assets_reps": unmatched,
                            "n_median": float(rr["n"].median()) if len(rr) else 0,
                            "expectancy_mean": float(rr["expectancy"].dropna().mean())
                            if len(rr) else None,
                            "expectancy_lo5": float(rr["expectancy"].dropna()
                                                    .quantile(0.05)) if len(rr) else None,
                            "expectancy_hi95": float(rr["expectancy"].dropna()
                                                     .quantile(0.95)) if len(rr) else None,
                            "win_rate_mean": float(rr["win_rate"].dropna().mean())
                            if len(rr) else None}
            # ---- buy-and-hold equal capital ($1000/asset) + $20 hold
            hold_1000, hold_20 = [], []
            for sym, p in m.panels.items():
                lo, hi = p.ranges[w]
                e = lo + 1 if lo + 1 <= hi else lo
                entry, exit_ = float(p.o[e]), float(p.c[hi])
                g = (1000.0 / entry) * (exit_ - entry)
                hold_1000.append(g - 2.6)                 # 0.13% each side
                g20 = (20.0 / entry) * (exit_ - entry)
                hold_20.append(g20 - 0.052)
            base = m.baseline(w)
            rows.append({
                "candidate": info["chosen"], "prefix": prefix, "window": w,
                "n_exec": st["n_exec"], "expectancy": st["expectancy"],
                "exp_lo5": st["exp_lo5"], "net": st["net"], "pf": st["pf"],
                "win_rate": st["win_rate"], "timeout_share": st["timeout_share"],
                "breakeven_ref": st["breakeven_ref"],
                "baseline_win": base["win_rate"] if base else None,
                "baseline_exp": base["expectancy"] if base else None,
                "lift_win_pts": st["lift_win_pts"], "lift_exp": st["lift_exp"],
                "rand_reps": rand_summary["reps"],
                "rand_unmatched": rand_summary["unmatched_assets_reps"],
                "rand_n_median": rand_summary["n_median"],
                "rand_exp_mean": rand_summary["expectancy_mean"],
                "rand_exp_lo5": rand_summary["expectancy_lo5"],
                "rand_exp_hi95": rand_summary["expectancy_hi95"],
                "rand_win_mean": rand_summary["win_rate_mean"],
                "hold1000_net": float(np.sum(hold_1000)),
                "hold20_net": float(np.sum(hold_20)),
                "bot_minus_hold1000": (st["net"] - float(np.sum(hold_1000))
                                       if st else None),
            })
            per[f"{info['chosen']}|{w}"] = {"reps": rep_rows,
                                            "summary": rand_summary}
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(O, "controls.csv"), index=False)
    with open(os.path.join(CACHE, "controls_reps.pkl"), "wb") as fh:
        pickle.dump(per, fh, protocol=4)
    return rows


# ==========================================================================
# stage 6 — neighbours (+-20%, registered first, separate Holm)
# ==========================================================================
def stage_neighbours(m, finalists, singles, pair_records):
    """Register numeric +-20% neighbours of each prefix finalist, then
    measure them on that prefix's inner windows."""
    from . import neighbours as NB
    regs = []
    seen_ids = set()
    for prefix, info in finalists.items():
        det = info.get("detail") or {}
        if info["chosen"] == "CASH" or not det:
            continue
        for vid, spec in NB.enumerate_neighbours(det["member_names"]):
            nid = f"N|{prefix}|{info['chosen']}|{vid}"
            row = {"neighbour_id": nid, "prefix_id": prefix,
                   "base_candidate": info["chosen"],
                   "member": spec["member"], "param": spec["param"],
                   "old_value": spec["old"], "new_value": spec["new"],
                   "factor": spec["factor"], "neighbour_setting":
                   spec["new_name"], "mode": det["mode"],
                   "registered_utc": utc(), "status": "registered"}
            regs.append(row)
    pd.DataFrame(regs).to_csv(os.path.join(O, "neighbors_registry.csv"),
                              index=False)
    journal("neighbours_registered", n=len(regs))
    out_rows = []
    fam_p = []
    fam_map = []
    for row in regs:
        prefix = row["prefix_id"]
        det = finalists[prefix].get("detail") or {}
        base_members = list(det["member_names"])
        mode = det["mode"]
        # base finalist's per-window nets for the retention rule
        base_stats={}
        for w in M.inner_windows(prefix):
            cb=m.candidate_trades(tuple(base_members),mode,window=w)
            pooled=m.windowed(cb,w)
            base_stats[w]=m.stat_window(pooled,w) if pooled else None
        # neighbour candidate: perturb the single numeric token
        new_members=[row["neighbour_setting"] if mname==row["member"] else mname for mname in base_members]
        windows=[]
        for w in M.inner_windows(prefix):
            nb=candidate_trades_names(m,tuple(new_members),mode,window=w)
            pooled=m.windowed(nb,w)
            st = m.stat_window(pooled, w) if pooled else None
            bs = base_stats.get(w)
            pos = bool(st and st["expectancy"] > 0)
            ratio = (st["expectancy"] / bs["expectancy"]
                     if (st and bs and bs["expectancy"] not in (0, None)
                         and np.isfinite(bs["expectancy"])) else None)
            windows.append({"window": w, "n": st["n_exec"] if st else 0,
                            "expectancy": st["expectancy"] if st else None,
                            "exp_lo5": st["exp_lo5"] if st else None,
                            "positive": pos, "retain_ratio": ratio,
                            "retain_ok": bool(ratio is not None and ratio >= 0.6)})
            if st is not None and st.get("p_raw") is not None:
                fam_p.append(float(st["p_raw"]))
                fam_map.append((row["neighbour_id"], w))
        out_rows.append({"neighbour_id": row["neighbour_id"],
                         "prefix_id": prefix, "base_candidate":
                         row["base_candidate"], "member": row["member"],
                         "param": row["param"], "old": row["old_value"],
                         "new": row["new_value"], "factor": row["factor"],
                         "neighbour_setting": row["neighbour_setting"],
                         "mode": mode, "windows": windows,
                         "n_windows": len(windows),
                         "positive_share": (np.mean([w["positive"]
                                                     for w in windows])
                                            if windows else None),
                         "retain_share": (np.mean([w["retain_ok"]
                                                   for w in windows])
                                          if windows else None)})
    if fam_p:
        pv_arr = pd.Series(fam_p).to_numpy()
        adj_arr = S.holm(pv_arr, m=len(pv_arr))
        for (nid, w), pv, adj in zip(fam_map, pv_arr, adj_arr):
            rej = adj < 0.05
            for r in out_rows:
                if r["neighbour_id"] == nid:
                    for ww in r["windows"]:
                        if ww["window"] == w:
                            ww["p_one_sided"] = float(pv)
                            ww["p_holm"] = float(adj)
                            ww["holm_reject"] = bool(rej)
    df = pd.DataFrame(out_rows)
    df.to_csv(os.path.join(O, "neighbors.csv"), index=False)
    with open(os.path.join(CACHE, "neighbours.pkl"), "wb") as fh:
        pickle.dump(out_rows, fh, protocol=4)
    journal("neighbours_measured", n=len(out_rows))
    return out_rows


# ==========================================================================
# stage 7 — freeze (one provisional hypothesis or null)
# ==========================================================================
def stage_freeze(finalists, triples_by_prefix):
    last_prefix = M.OUTER[-1]
    info = finalists.get(last_prefix) or {}
    det = info.get("detail")
    frozen = None
    if det:
        frozen = {"definition": list(det["member_names"]),
                  "mode": det["mode"], "candidate_id": det["id"],
                  "source_windows": info["inner"],
                  "worst_bound": det["worst_bound"],
                  "minimum_count": det["minimum_count"]}
    obj = {
        "lane": "L0084-ENTRY-MIX",
        "freeze_utc": utc(),
        "selection_prefix": last_prefix,
        "frozen": frozen,
        "hash_of_definition": (hashlib.sha256(
            json.dumps(frozen, sort_keys=True, ensure_ascii=False)
            .encode("utf-8")).hexdigest() if frozen else None),
        "future_start_rule": "first eligible complete bar AFTER this freeze "
                             "commit's UTC timestamp (not merely after "
                             "2026-09-27)",
        "acceptance": {"min_executed_trades": 100, "min_calendar_days": 90,
                       "end": "BOTH conditions, then report"},
        "status_until_then": "NOT MEASURED",
        "no_candidate_switch_after_losses": True,
        "honest_notes": [
            "historical splits are exploration, not blind proof",
            "no adoption, no live orders, no profit forecast"],
    }
    dump_json("frozen_candidate.json", obj)
    journal("freeze", frozen=frozen)
    return obj
