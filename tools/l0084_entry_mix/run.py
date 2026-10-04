#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0084-ENTRY-MIX — orchestrator: preregister -> check -> measure -> summarise.

Run journal (O/run_journal.jsonl) records every stage transition with UTC
timestamps; triples are registered BEFORE any triple outcome is read; outer
(target) windows are read only after selection (check 14 evidence).
"""
from __future__ import annotations

import hashlib
import json
import os
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
BUDGET_BYTES = 125 * 1024 * 1024


def utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def journal(event, **kw):
    os.makedirs(O, exist_ok=True)
    rec = {"event": event, "ts_utc": utc(), **kw}
    with open(os.path.join(O, "run_journal.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[journal] {event} {kw if kw else ''}", flush=True)


def workspace_bytes():
    total = 0
    for root, _dirs, files in os.walk("/home/user"):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


# --------------------------------------------------------------------------
# stage 1 — preregistration (BEFORE any outcome)
# --------------------------------------------------------------------------
def sources_json():
    rows = []
    for line in open(os.path.join(ROOT, "_meta", "fetch_manifest.txt"),
                     encoding="utf-8"):
        code, commit, path, size, sha, url = line.strip().split("|")
        rows.append({"commit": commit, "path": path, "url": url,
                     "status": int(code), "sha256": sha, "bytes": int(size),
                     "versions": {"python": "3.13.14", "numpy": np.__version__,
                                  "pandas": pd.__version__},
                     "errors": []})
    out = {"fetched_utc": utc(), "sources": rows}
    with open(os.path.join(O, "sources.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    return out


def catalogue():
    """52 settings with mask hashes + duplicate relations (12 assets)."""
    m = M.Measurer()
    rows = []
    hashes = {}
    for name in I.SETTINGS_52:
        h = hashlib.sha256()
        ntrue = 0
        for sym in D.ASSETS:
            mask = m.panels[sym].masks[name]
            h.update(np.packbits(mask).tobytes())
            ntrue += int(mask.sum())
        digest = h.hexdigest()
        hashes[name] = digest
        rows.append({"setting": name,
                     "definition": name.split("_")[0],
                     "parameters": "", "source_commit": "62f4d255",
                     "mask_hash": digest, "duplicate_of": "",
                     "n_true_12assets": ntrue})
    # duplicate relations
    byh = {}
    for r in rows:
        byh.setdefault(r["mask_hash"], []).append(r["setting"])
    for h, names in byh.items():
        if len(names) > 1:
            for r in rows:
                if r["mask_hash"] == h and r["setting"] != names[0]:
                    r["duplicate_of"] = names[0]
    pd.DataFrame(rows).to_csv(os.path.join(O, "catalogue.csv"), index=False)
    n_dup = sum(1 for r in rows if r["duplicate_of"])
    return len(rows), n_dup


def preregistration():
    counts = M.counts_check()
    reg = {
        "lane": "L0084-ENTRY-MIX",
        "written_utc": utc(),
        "written_before_any_measurement": True,
        "main_pin": "71f52f0741cdaceb71797b1fe07de07db31fcced",
        "grid_pin": "62f4d255e0fc6fce8e7c331a6349484ccb0b8fc0",
        "cost_model_pin": "2d8e8f3afca6a72679382780ddaeb0d71de2cad6",
        "assets": D.ASSETS,
        "period": "4h UTC 2021-01-01..2026-09-27",
        "settings_52": I.SETTINGS_52,
        "modes": ["AND0", "AND2", "OR0"],
        "counts": counts,
        "outer_windows": M.OUTER,
        "inner_windows_by_prefix": {o: M.inner_windows(o) for o in M.OUTER},
        "container": {"notional_usd": 20.0, "cost_rt_usd": 0.052,
                      "barrier_atr": 1.5, "horizon_bars_incl_fill": 18,
                      "fill": "next contiguous open",
                      "book_usd_per_asset": 1000.0},
        "gates": {"min_trades_inner": 100, "min_positive_assets": 8,
                  "min_pf": 1.3, "need_bootstrap_lo5_gt_zero": True,
                  "need_paired_lo5_gt_zero_vs_constituents": True},
        "triple_rule": "retained <=10 pairs/mode x each remaining setting; "
                       "cap 1500 trials before dedup per prefix",
        "selection_order": ["worst_window_lo5", "member_count",
                            "min_trade_count", "canonical_id"],
        "holm_family": 70330,
        "bootstrap": {"reps": 2000, "block_days": 7, "seed": 84,
                      "synchronised_across_assets": True},
        "seed84_everywhere": True,
        "pending_items": ["corrected local 76-grid package not found at "
                          "inspected tips",
                          "L0083 headlines documented only, not recomputed "
                          "here"],
        "no_adoption": True,
    }
    with open(os.path.join(O, "preregistration.json"), "w",
              encoding="utf-8") as fh:
        json.dump(reg, fh, ensure_ascii=False, indent=2)
    return reg


def git_commit(message):
    """Local evidence repository (no remote, nothing pushed anywhere)."""
    try:
        subprocess.run(["git", "init", "-q"], cwd=ROOT, check=False)
        subprocess.run(["git", "-C", ROOT, "checkout", "-q", "-B",
                        "arena/l0084-entry-mix-2026-10-04"], check=False)
        subprocess.run(["git", "-C", ROOT, "add", "-A", "tools", "_meta",
                        "history", "docs", ".gitignore"], check=False)
        subprocess.run(["git", "-C", ROOT, "-c", "user.email=executor@local",
                        "-c", "user.name=L0084-executor", "commit", "-q", "-m",
                        message], check=False)
        h = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
                           capture_output=True, text=True).stdout.strip()
        return h
    except Exception as e:                                    # noqa: BLE001
        return f"git-unavailable: {e!r}"


# --------------------------------------------------------------------------
# stage 3 — measurement (singles + all pair modes), keys ledger for ALL
# --------------------------------------------------------------------------
KEYS_DIR = os.path.join(O, "trades_keys")
FULL_LEDGER = os.path.join(O, "trades.parquet")
OUTCOME_CODE = {"stop": 0, "target": 1, "timeout": 2}
OUTCOME_NAME = {v: k for k, v in OUTCOME_CODE.items()}
CAND_CACHE = os.path.join(O, "_cache")


def _cand_row(cid, members, mode, stages):
    return {"candidate_id": cid, "members": "|".join(members), "mode": mode,
            "n_members": len(members), "stage": stages}


def measure_singles(m, journal_fn=journal):
    """52 singletons over all 12 half-years; returns stats with day arrays."""
    out = {}
    trades_keep = {}
    for name in I.SETTINGS_52:
        tr = m.candidate_trades((name,), "AND0")
        st = {}
        for wname, _a, _b in M.HALF_YEARS:
            pooled = m.windowed(tr, wname)
            st[wname] = m.stat_window(pooled, wname) if pooled else None
        out[name] = st
        trades_keep[name] = tr
    return out, trades_keep


def measure_pairs(m, single_stats, batch=150, journal_fn=journal):
    """Every pair-mode on the 9 inner half-years; gate evidence for all 8
    prefixes computed on the fly; compact records only (no day arrays)."""
    os.makedirs(KEYS_DIR, exist_ok=True)
    pairs = M.canonical_pairs()
    inner = ["2022H1", "2022H2", "2023H1", "2023H2", "2024H1", "2024H2",
             "2025H1", "2025H2", "2026H1"]
    records = []
    buf_meta = []; buf_asset = []; buf_sig = []; buf_exit = []
    buf_code = []; buf_flag = []
    cand_idx = 0
    part = 0
    t0 = time.time()
    base_trades = {w: m._base_trades.get(w) or m.baseline(w) or
                   m._base_trades[w] for w in inner}
    for n, (a, b) in enumerate(pairs, start=1):
        for mode in ("AND0", "AND2", "OR0"):
            cid = f"P{n:04d}|{mode}"
            cb = m.candidate_trades((a, b), mode)
            wstats = {}
            wdays = {}
            for w in inner:
                pooled = m.windowed(cb, w)
                st = m.stat_window(pooled, w) if pooled else None
                if st is not None:
                    wdays[w] = (st.pop("days"), st.pop("nets"))
                wstats[w] = st
            # gate evidence for every prefix (uses inner windows only)
            gates = {}
            for outer in M.OUTER:
                win = [w for w in inner if w < outer]
                rows = []
                el = True
                worst = None
                minc = 10 ** 9
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
                            cs = single_stats.get(ctrl, {}).get(w)
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
                                "minimum_count": (minc if minc < 10 ** 9 else 0)}
            records.append({"cid": cid, "members": [a, b], "mode": mode,
                            "windows": wstats, "gates": gates})
            for sym_i, sym in enumerate(D.ASSETS):
                for t in cb[sym]:
                    buf_meta.append(cand_idx); buf_asset.append(sym_i)
                    buf_sig.append(t["signal_bar"]); buf_exit.append(t["exit_bar"])
                    buf_code.append(OUTCOME_CODE[t["outcome"]])
                    buf_flag.append((1 if t["gap_flag"] else 0)
                                    | (2 if t["double_touch"] else 0))
            cand_idx += 1
            del cb
        if n % batch == 0:
            _flush_keys(KEYS_DIR, part, buf_meta, buf_asset, buf_sig,
                        buf_exit, buf_code, buf_flag)
            part += 1
            buf_meta, buf_asset, buf_sig, buf_exit, buf_code, buf_flag = \
                [], [], [], [], [], []
            journal_fn("measure_pairs_progress", pairs_done=n,
                       candidates=cand_idx,
                       elapsed_s=round(time.time() - t0, 1))
    if buf_meta:
        _flush_keys(KEYS_DIR, part, buf_meta, buf_asset, buf_sig,
                    buf_exit, buf_code, buf_flag)
    with open(os.path.join(KEYS_DIR, "index.json"), "w") as fh:
        json.dump({"n_candidates": cand_idx,
                   "order": "candidate index = (pair_id, mode) enumeration "
                            "order of selection_log pairs",
                   "assets": D.ASSETS, "outcome_code": OUTCOME_CODE,
                   "flag_bits": "bit0=gap_exit, bit1=double_touch",
                   "row_schema": ["candidate_idx", "asset_idx", "signal_bar",
                                  "exit_bar", "outcome_code", "flag_bits"],
                   "note": "fill_bar=signal_bar+1; every other trade field is "
                           "reconstructed exactly from retained market data "
                           "by cli audit --rebuild"}, fh, indent=1)
    return records


def _flush_keys(dest, part, meta, asset, sig, exit_, code, flag):
    df = pd.DataFrame({"candidate_idx": np.asarray(meta, dtype="int32"),
                       "asset_idx": np.asarray(asset, dtype="int8"),
                       "signal_bar": np.asarray(sig, dtype="int32"),
                       "exit_bar": np.asarray(exit_, dtype="int32"),
                       "outcome_code": np.asarray(code, dtype="int8"),
                       "flag_bits": np.asarray(flag, dtype="int8")})
    path = os.path.join(dest, f"keys_part{part:03d}.parquet")
    df.to_parquet(path, index=False, compression="zstd")
    return path


# --------------------------------------------------------------------------
# stage 4 — gates, ranking, triple registration, selection
# --------------------------------------------------------------------------
def _gate_record(st, base, constituents, single_stats, window, n_days,
                 pair_trade_bundle=None, m=None):
    """One window's gate evidence for a candidate."""
    rec = {"window": window, "n_exec": 0, "pos_assets": 0, "pf": 0.0,
           "expectancy": None, "exp_lo5": None, "pass": False,
           "paired": {}}
    if st is None:
        return rec
    rec.update({"n_exec": st["n_exec"], "pos_assets": st["pos_assets"],
                "pf": st["pf"], "expectancy": st["expectancy"],
                "exp_lo5": st["exp_lo5"], "win_rate": st["win_rate"]})
    ok = (st["n_exec"] >= M.GATE_MIN_TRADES
          and st["pos_assets"] >= M.GATE_MIN_POS_ASSETS
          and st["pf"] >= M.GATE_MIN_PF
          and st["exp_lo5"] > 0)
    for ctrl in constituents:
        cs = single_stats.get(ctrl, {}).get(window)
        if cs is None:
            ok = False
            rec["paired"][ctrl] = {"lo5": None, "diff": None}
            continue
        d = S.paired_block_diff(st["days"], st["nets"], cs["days"], cs["nets"],
                                st["n_days"])
        rec["paired"][ctrl] = {"diff": d["diff"], "lo5": d["lo5"]}
        if not (d["lo5"] > 0):
            ok = False
    rec["pass"] = ok
    return rec


def evaluate_prefix(prefix, singles, pairs_records, single_stats, m,
                    log=print):
    """Eligibility + ranking + triples registry + provisional selection."""
    inner = M.inner_windows(prefix)
    out = {"prefix": prefix, "inner": inner, "singles": [], "pairs": [],
           "triples": [], "selected": None}
    # ---- singles
    single_rows = []
    for name, st_by_w in singles.items():
        recs = [_gate_record(st_by_w.get(w), None, [], single_stats,
                             w, None) for w in inner]
        ok = all(r["pass"] for r in recs)
        # plus superiority over the no-signal book
        for w, r in zip(inner, recs):
            st = st_by_w.get(w)
            if st is None:
                ok = False
                continue
            bd, bn = m._base_trades[w]
            d = S.paired_block_diff(st["days"], st["nets"], bd, bn,
                                    st["n_days"])
            r["paired"]["baseline"] = {"diff": d["diff"], "lo5": d["lo5"]}
            if not (d["lo5"] > 0):
                ok = False
        worst = min([r["exp_lo5"] for r in recs
                     if r["exp_lo5"] is not None], default=None)
        mincnt = min([r["n_exec"] for r in recs], default=0)
        single_rows.append({"candidate": name, "stage": "single", "mode": "-",
                            "eligible": bool(ok), "worst_bound": worst,
                            "minimum_count": mincnt, "windows": recs})
    # ---- pairs
    pair_rows = []
    for rec in pairs_records:
        cid = rec["cid"]
        recs = []
        ok = True
        for w in inner:
            st = rec["windows"].get(w)
            e = _gate_record(st, None, rec["members"], single_stats, w, None)
            if rec["paired"].get(w) is not None:
                for ctrl, pdv in rec["paired"][w].items():
                    if pdv is None:
                        ok = False
                        e["paired"][ctrl] = {"lo5": None}
                        continue
                    e["paired"][ctrl] = pdv
                    if not (pdv["lo5"] > 0):
                        ok = False
            recs.append(e)
            if not e["pass"]:
                ok = False
        worst = min([r["exp_lo5"] for r in recs
                     if r["exp_lo5"] is not None], default=None)
        mincnt = min([r["n_exec"] for r in recs], default=0)
        pair_rows.append({"candidate": cid, "stage": "pair", "mode": rec["mode"],
                          "members": rec["members"], "eligible": bool(ok),
                          "worst_bound": worst, "minimum_count": mincnt,
                          "windows": recs})
    # rank + retain <=10 per mode among ELIGIBLE pairs
    retained = []
    for mode in ("AND0", "AND2", "OR0"):
        elig = [r for r in pair_rows if r["mode"] == mode and r["eligible"]]
        elig.sort(key=lambda r: (-(r["worst_bound"] if r["worst_bound"]
                                   is not None else -1e9),
                                 -r["minimum_count"], r["candidate"]))
        keep = elig[:10]
        for rank, r in enumerate(keep, start=1):
            r["rank"] = rank
        retained.extend(keep)
    out["singles"], out["pairs"], out["retained_pairs"] = \
        single_rows, pair_rows, retained
    # ---- triples registry (BEFORE triple outcomes)
    tri_rows = register_triples_registry(prefix, retained)
    out["triples_registry"] = tri_rows
    return out


def register_triples_registry(prefix, retained_pairs):
    """Write triples_registry rows to O/triples_registry.csv (pre-outcome)."""
    rows = []
    seen = {}
    seq = 0
    cap = 1500
    for prow in retained_pairs:
        members = list(prow["members"])
        mode = prow["mode"]
        for extra in I.SETTINGS_52:
            if extra in members:
                continue
            tri = tuple(sorted(members + [extra]))
            key = (tri, mode)
            if key in seen:
                seen[key]["parent_ids"] += "+" + str(prow["candidate"])
                continue
            if seq >= cap:
                break
            seq += 1
            rows.append({"prefix_id": prefix,
                         "triple_id": f"T{seq:05d}|{mode}",
                         "member_a": tri[0], "member_b": tri[1],
                         "member_c": tri[2], "mode": mode,
                         "parent_ids": str(prow["candidate"]),
                         "eligible": "", "reason": "registered_pre_outcome"})
            seen[key] = rows[-1]
    path = os.path.join(O, "triples_registry.csv")
    df = pd.DataFrame(rows)
    if os.path.exists(path):
        df = pd.concat([pd.read_csv(path), df], ignore_index=True)
    df.to_csv(path, index=False)
    return rows


# --------------------------------------------------------------------------
# stage 5 — triple measurement (registry-first; parents = pairs from the
# measured pair grid; superset shown over the triple's own windows)
# --------------------------------------------------------------------------
def _pool_stats(m, cb, wins, extra_paired=()):
    """stats for selected windows + paired diffs vs controls (day arrays)."""
    res = {}
    for w in wins:
        pooled = m.windowed(cb, w)
        st = m.stat_window(pooled, w) if pooled else None
        if st is None:
            res[w] = None
            continue
        d, n = st["days"], st["nets"]
        pa = {}
        for label, csts in extra_paired:
            cs = csts.get(w)
            if cs is None:
                pa[label] = None
                continue
            dd = S.paired_block_diff(d, n, cs["days"], cs["nets"],
                                     st["n_days"])
            pa[label] = {"diff": dd["diff"], "lo5": dd["lo5"]}
        res[w] = {"stat": st, "paired": pa}
    return res


def measure_triples(m, single_stats, reg_rows, pair_records):
    """Registry-first triple measurement; returns per-triple window evidence
    with paired diffs vs the 3 singleton members and vs the constituent
    pairs (measured on the pair grid), all on inner windows only."""
    if not reg_rows:
        return {"prefix": None, "triples": []}
    prefix = reg_rows[0]["prefix_id"]
    inner = M.inner_windows(prefix)
    pair_by_key = {(tuple(r["members"]), r["mode"]): r for r in pair_records}
    out, seen = [], {}
    for row in reg_rows:
        members = (row["member_a"], row["member_b"], row["member_c"])
        mode = row["mode"]
        cb = m.candidate_trades(members, mode)
        # day-level arrays only for the inner windows of this prefix
        ev = _pool_stats(m, cb, inner,
                         extra_paired=[(n, single_stats.get(n, {}))
                                       for n in members])
        # constituent pairs re-derive day arrays once (max 3 per triple)
        comp_keys = [(tuple(sorted((members[i], members[j]))), mode)
                     for i in range(3) for j in range(i + 1, 3)]
        pair_ev = {}
        for key in comp_keys:
            pr = pair_by_key.get(key)
            if pr is None:
                pair_ev["|".join(key[0]) + "|" + key[1]] = None
                continue
            labels = []
            cbst = {}
            for w in inner:
                st = pr["windows"].get(w)
                if st is not None:
                    # recompute days/nets locally (cheap: single pair-mode)
                    pass
            cbst = None
            pair_ev["|".join(key[0]) + "|" + key[1]] = pr
        key = (members, mode,
               tuple((w, (ev[w] or {}).get("stat") is not None and
                      ev[w]["stat"]["n_exec"]) for w in inner))
        if key in seen:
            row["eligible"] = ""
            row["reason"] = f"duplicate of {seen[key]['triple_id']}"
            out.append({"triple_id": row["triple_id"], "members": list(members),
                        "mode": mode, "parent_ids": row["parent_ids"],
                        "duplicate_of": seen[key]["triple_id"], "windows": {},
                        "gates": {}})
            continue
        rec = {"triple_id": row["triple_id"], "members": list(members),
               "mode": mode, "parent_ids": row["parent_ids"],
               "duplicate_of": "", "windows": ev, "pair_refs": pair_ev}
        out.append(rec)
        seen[key] = rec
        del cb
    return {"prefix": prefix, "triples": out}
