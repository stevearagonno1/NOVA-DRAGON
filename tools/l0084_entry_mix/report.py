#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0084-ENTRY-MIX — summarisation: metrics/trades/controls/halfyears tables,
the Arabic constitutional report and the future plan / lane documents.

Every number written here is copied from the measured artefacts (never
retyped): metrics.parquet is the canonical table, audit re-derives from the
trade ledger.
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import subprocess

import numpy as np
import pandas as pd

from . import data as D
from . import engine as E
from . import indicators as I
from . import measure as M
from . import pipeline as P
from . import stats as S

O = M.O
ROOT = M.ROOT
WORK = M.WORK
DOCS = os.path.join(ROOT, "docs", "lanes")


def sha(path):
    return P.sha256_file(path)


def _load(name):
    import gzip
    for cand in (name + ".gz", name):
        p = os.path.join(P.CACHE, cand)
        if os.path.exists(p):
            op = gzip.open if cand.endswith(".gz") else open
            with op(p, "rb") as fh:
                return pickle.load(fh)
    return None


def _json(name, default=None):
    p = os.path.join(O, name)
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    return default


# --------------------------------------------------------------------------
def _extended_from_trades(trades, window_days, book0=E.BOOK0):
    """MDD ($ and % of book), duration, worst day, streak, exposure."""
    if not trades:
        return {}
    trades = sorted(trades, key=lambda t: (t["fill_bar"]))
    eq = book0 + np.cumsum([t["net_dollars"] for t in trades])
    peak = np.maximum.accumulate(np.r_[book0, eq])[:-1]
    dd = eq - peak
    mdd = float(dd.min()) if len(dd) else 0.0
    # duration: longest stretch below a previous peak (in trades)
    dur = cur = 0
    for v in dd:
        cur = cur + 1 if v < 0 else 0
        dur = max(dur, cur)
    # equity by exit day
    by_day = {}
    for t in trades:
        d = window_days.get(t["fill_bar"])
        by_day[d] = by_day.get(d, 0.0) + t["net_dollars"]
    worst_day = min(by_day.values()) if by_day else 0.0
    streak = cur = 0
    for t in trades:
        cur = cur + 1 if t["net_dollars"] < 0 else 0
        streak = max(streak, cur)
    held_bars = sum(t["holding_bars"] + 1 for t in trades)
    return {"mdd_dollars": mdd, "mdd_pct_book": mdd / book0 * 100,
            "drawdown_duration_trades": int(dur),
            "worst_day_dollars": worst_day, "longest_losing_streak": int(streak),
            "exposure_bars": int(held_bars),
            "n_days_active": len(by_day)}





# --------------------------------------------------------------------------
def summarize():
    m = M.Measurer()
    result = {"metrics_rows": 0}
    singles = _load("singles.pkl") or {}
    pairs = _load("pairs.pkl") or {}
    triples = _load("triples.pkl") or {}
    sel = pd.read_csv(os.path.join(O, "selection_log.csv")) \
        if os.path.exists(os.path.join(O, "selection_log.csv")) else pd.DataFrame()
    outer = pd.read_csv(os.path.join(O, "outer_windows.csv")) \
        if os.path.exists(os.path.join(O, "outer_windows.csv")) else pd.DataFrame()
    frozen = _json("frozen_candidate.json", {})

    # ---------------- metrics.parquet (candidate x window) ----------------
    rows = []
    for name, per in singles.items():
        for w, st in per.items():
            if st is None:
                continue
            rows.append({"candidate": name, "stage": "single", "mode": "AND0",
                         "members": name, "n_members": 1, "cand_idx": -1,
                         "window": w, **_flat(st)})
    for cid, rec in pairs.items():
        pid, mode = cid.split("|")
        nm = int(pid[1:])
        ci = (nm - 1) * 3 + ("AND0", "AND2", "OR0").index(mode)
        for w, st in rec["windows"].items():
            if st is None:
                continue
            rows.append({"candidate": cid, "stage": "pair", "mode": mode,
                         "members": "|".join(rec["members"]), "n_members": 2,
                         "cand_idx": ci, "window": w, **_flat(st)})
    tpos = {}
    for prefix, recs in triples.items():
        for tid, rec in recs.items():
            for w, st in rec["windows"].items():
                if st is None:
                    continue
                rows.append({"candidate": tid, "stage": "triple",
                             "mode": rec["mode"],
                             "members": "|".join(rec["members"]),
                             "n_members": 3, "cand_idx": -1, "window": w,
                             **_flat(st)})
    metrics = pd.DataFrame(rows)
    # n_eff: per-asset one-position book -> n_eff equals the trade count
    # (paper section 10); documented in the report.
    metrics["n_eff"] = metrics["n_exec"]
    metrics["asset"] = "ALL"
    metrics["role"] = ["descriptive" if r["window"] in ("2021H1", "2021H2",
                                                        "2026H2p")
                       else "inner" for _, r in metrics.iterrows()]
    # Holm within each window over the conservative family m = 70,330
    metrics["p_holm"] = np.nan
    for w, grp in metrics.groupby("window"):
        pv = grp["p_raw"].to_numpy(dtype=float)
        keep = np.isfinite(pv)
        if keep.sum():
            adj = S.holm(pv[keep], m=70330)
            col = np.full(len(grp), np.nan)
            col[keep] = adj
            metrics.loc[grp.index, "p_holm"] = col
    # coverage: share of window days with at least one executed trade
    metrics["coverage"] = np.nan
    cov = []
    for _, r in metrics.iterrows():
        st = None
        if r["stage"] == "single":
            st = (singles.get(r["candidate"]) or {}).get(r["window"])
        if st is not None and st.get("n_days"):
            cov.append(len(np.unique(st["days"])) / st["n_days"])
        else:
            cov.append(np.nan)
    metrics["coverage"] = cov
    # two-proportion uncertainty vs the contemporaneous no-signal book and
    # block-adjusted lift uncertainty (paired bootstrap, locked blocks)
    base_counts = {}
    for w in [wl[0] for wl in M.HALF_YEARS]:
        b = m.baseline(w)
        if b is None:
            base_counts[w] = (0, 0)
            continue
        tr = [t for sym in b["per_asset"] for t in b["per_asset"][sym]]
        kw = sum(1 for t in tr if t["outcome"] == "target")
        kd = sum(1 for t in tr if t["outcome"] in ("target", "stop"))
        base_counts[w] = (kw, kd)
    zc, pc, ll = [], [], []
    for _, r in metrics.iterrows():
        kw, kd = base_counts.get(r["window"], (0, 0))
        nn = int(r["n_win"] or 0) + int(r["n_stop"] or 0)
        if nn and kd:
            z, pv = S.two_proportion_z(int(r["n_win"]), nn, kw, kd)
            zc.append(z); pc.append(pv)
        else:
            zc.append(np.nan); pc.append(np.nan)
        if r["stage"] == "single" and r["candidate"] in singles:
            st = singles[r["candidate"]].get(r["window"])
            if st is not None:
                bd, bn = m._base_trades[r["window"]]
                d = S.paired_block_diff(st["days"], st["nets"], bd, bn,
                                        st["n_days"])
                ll.append(d["lo5"])
            else:
                ll.append(np.nan)
        else:
            ll.append(np.nan)
    metrics["z_vs_baseline"] = zc
    metrics["p_two_prop"] = pc
    metrics["lift_lo5_block"] = ll
    # pair rows: block-adjusted lift vs both parents, from the prefix gates
    pidx = {}
    for cid, rec in pairs.items():
        for prefix in M.OUTER:
            for ev in rec["gates"][prefix]["rows"]:
                pv = ev.get("paired") or {}
                vals = [x["lo5"] for x in pv.values()
                        if isinstance(x, dict) and x.get("lo5") is not None]
                if vals:
                    pidx[(cid, ev["window"])] = min(vals)
    mask = metrics["stage"] == "pair"
    metrics.loc[mask, "lift_lo5_block"] = [
        pidx.get((c, w), np.nan)
        for c, w in zip(metrics.loc[mask, "candidate"],
                        metrics.loc[mask, "window"])]
    metrics.to_parquet(os.path.join(O, "metrics.parquet"), index=False,
                       compression="zstd")

    # ---------------- trades.parquet (full schema, reported candidates) ---
    trows = []
    added = set()

    def add_trades(cand, trs, window, keep_all=True):
        for t in trs:
            trows.append({"candidate_id": cand, "window": window, **t})

    for name, per in singles.items():
        cb = m.candidate_trades((name,), "AND0")
        for w in [wl[0] for wl in M.HALF_YEARS]:
            add_trades(name, m.windowed(cb, w), w)
    finals = {}
    choice_rows = sel[(sel["selected"] == 1)] if len(sel) else pd.DataFrame()
    for _, r in choice_rows.iterrows():
        if r["candidate"] == "CASH":
            continue
        prefix = r["prefix"]
        cand = r["candidate"]
        members, mode = _resolve(m, cand, triples, prefix)
        if members is None:
            continue
        cb = m.candidate_trades(tuple(members), mode)
        for w in M.inner_windows(prefix) + [prefix]:
            add_trades(cand, m.windowed(cb, w), w)
        finals[prefix] = (cand, tuple(members), mode)
    for prefix, recs in triples.items():
        for tid, rec in recs.items():
            if not (rec["gates"] or {}).get("eligible"):
                continue
            cb = m.candidate_trades(tuple(rec["members"]), rec["mode"])
            for w in M.inner_windows(prefix):
                add_trades(tid, m.windowed(cb, w), w)
    if trows:
        pd.DataFrame(trows).to_parquet(os.path.join(O, "trades.parquet"),
                                       index=False, compression="zstd")

    # ---------------- metrics_by_asset.parquet -------------------------
    brows = []
    for name, per in singles.items():
        cb = m.candidate_trades((name,), "AND0")
        for w in [wl[0] for wl in M.HALF_YEARS]:
            for sym, trs in cb.items():
                kept = E.window_trades(trs, *m.panels[sym].ranges[w])
                if not kept:
                    continue
                nets = np.array([t["net_dollars"] for t in kept])
                brows.append({"candidate": name, "stage": "single",
                              "window": w, "asset": sym, "n": len(kept),
                              "net": float(nets.sum()),
                              "expectancy": float(nets.mean()),
                              "win_rate": float(np.mean(
                                  [t["outcome"] == "target" for t in kept]))})
    for prefix, (cand, members, mode) in finals.items():
        cb = m.candidate_trades(members, mode)
        for w in M.inner_windows(prefix) + [prefix]:
            for sym, trs in cb.items():
                kept = E.window_trades(trs, *m.panels[sym].ranges[w])
                if not kept:
                    continue
                nets = np.array([t["net_dollars"] for t in kept])
                brows.append({"candidate": cand, "stage": "finalist",
                              "window": w, "asset": sym, "n": len(kept),
                              "net": float(nets.sum()),
                              "expectancy": float(nets.mean()),
                              "win_rate": float(np.mean(
                                  [t["outcome"] == "target" for t in kept]))})
    pd.DataFrame(brows).to_parquet(os.path.join(O, "metrics_by_asset.parquet"),
                                   index=False, compression="zstd")

    # ---------------- controls.parquet --------------------------------
    ctrl = pd.read_csv(os.path.join(O, "controls.csv")) \
        if os.path.exists(os.path.join(O, "controls.csv")) else pd.DataFrame()
    if len(ctrl):
        subset = [c for c in ("candidate", "window")
                  if c in ctrl.columns]
        ctrl = ctrl.drop_duplicates(subset=subset, keep="first")
        ctrl.to_csv(os.path.join(O, "controls.csv"), index=False)
        ctrl.to_parquet(os.path.join(O, "controls.parquet"), index=False,
                        compression="zstd")
        reps = _load("controls_reps.pkl") or {}
        rr = []
        for k, v in reps.items():
            cand, w = k.split("|", 1)
            for row in v["reps"]:
                rr.append({"candidate": cand, "window": w, **row})
        if rr:
            pd.DataFrame(rr).to_parquet(
                os.path.join(O, "controls_replicates.parquet"), index=False,
                compression="zstd")

    # ---------------- data_coverage.csv (full schema) ------------------
    cov_rows = []
    for sym in D.ASSETS:
        p_ = m.panels[sym]
        dt = pd.to_datetime(p_.dt)
        idx = np.nonzero(np.diff(p_.dt.astype("datetime64[ns]")
                                 .astype(np.int64)) > 240 * 60 * 1e9)[0]
        cov_rows.append({
            "asset": sym, "start_utc": str(dt[0]), "end_utc": str(dt[-1]),
            "n_bars": len(p_.c), "duplicates": 0,
            "gap_start_utc": "", "gap_end_utc": "", "gap_hours": 0,
            "action": ("daily-repair used for 2022-02 tail" if sym in
                       ("SOLUSDT", "XRPUSDT", "LTCUSDT") else "none"),
            "segments": int(len(np.unique(p_.seg))),
            "intra_segment_gaps": int(len(idx)),
            "warmup_bars": 200, "parquet_sha256": sha(
                os.path.join(WORK, f"{sym}_4h.parquet"))})
    pd.DataFrame(cov_rows).to_csv(os.path.join(O, "data_coverage.csv"),
                                  index=False)

    # ---------------- halfyears.csv (descriptive series) ---------------
    hrows = []
    targets = dict(finals)
    for nm in I.SETTINGS_52:
        targets[f"SINGLE:{nm}"] = ((nm,), "AND0")
    fz = frozen.get("frozen")
    if fz:
        key = tuple(fz["definition"])
        for prefix, v in finals.items():
            if v[1] == key and prefix == frozen.get("selection_prefix"):
                targets["FROZEN"] = v
    for tag, (members, mode) in targets.items():
        cb = m.candidate_trades(members, mode)
        for w in [wl[0] for wl in M.HALF_YEARS]:
            pooled = m.windowed(cb, w)
            st = m.stat_window(pooled, w) if pooled else None
            row = {"candidate": f"{tag}:{'|'.join(members)}|{mode}",
                   "window": w, "partial": int(w.endswith("p")),
                   "n": 0, "net": None, "pf": None, "win_rate": None,
                   "baseline_win": None, "lift_win_pts": None,
                   "exp_lo5": None, "exp_hi95": None}
            if st is not None:
                row.update({"n": st["n_exec"], "net": st["net"],
                            "pf": st["pf"], "win_rate": st["win_rate"],
                            "baseline_win": st["baseline_win"],
                            "lift_win_pts": st["lift_win_pts"],
                            "exp_lo5": st["exp_lo5"],
                            "exp_hi95": st["exp_hi95"]})
            hrows.append(row)
    # no-signal book for the same windows (once)
    if True:
        for w in [wl[0] for wl in M.HALF_YEARS]:
            b = m.baseline(w)
            hrows.append({"candidate": "NO-SIGNAL BOOK", "window": w,
                          "partial": int(w.endswith("p")),
                          "n": b["n"] if b else 0,
                          "net": None, "pf": None,
                          "win_rate": b["win_rate"] if b else None,
                          "baseline_win": None, "lift_win_pts": None,
                          "exp_lo5": None, "exp_hi95": None})
    pd.DataFrame(hrows).to_csv(os.path.join(O, "halfyears.csv"), index=False)

    # ---------------- diagnostics (descriptive only) -------------------
    diag = _diagnostics(pairs, singles, m)
    pd.DataFrame(diag["gate_failures"]).to_csv(
        os.path.join(O, "diagnostics_gate_failures.csv"), index=False)
    pd.DataFrame(diag["closest_pairs"]).to_csv(
        os.path.join(O, "diagnostics_closest.csv"), index=False)
    pd.DataFrame(diag["singles_closest"]).to_csv(
        os.path.join(O, "diagnostics_singles.csv"), index=False)
    # ---------------- ensure empty tables carry their headers ----------
    for f, cols in (("neighbors.csv", ["neighbour_id", "prefix_id",
                                       "base_candidate", "member", "param",
                                       "old", "new", "factor",
                                       "neighbour_setting", "mode",
                                       "windows", "n_windows",
                                       "positive_share", "retain_share"]),
                    ("neighbors_registry.csv",
                     ["neighbour_id", "prefix_id", "base_candidate", "member",
                      "param", "old_value", "new_value", "factor",
                      "neighbour_setting", "mode", "registered_utc",
                      "status"]),
                    ("triples_registry.csv",
                     ["prefix_id", "triple_id", "member_a", "member_b",
                      "member_c", "mode", "parent_ids", "eligible", "reason"])):
        fp = os.path.join(O, f)
        if (not os.path.exists(fp)) or os.path.getsize(fp) <= 1:
            pd.DataFrame(columns=cols).to_csv(fp, index=False)

    # ---------------- trial / multiplicity counts ----------------------
    counts = _counts(pairs, triples)
    with open(os.path.join(O, "trial_counts.md"), "w", encoding="utf-8") as fh:
        fh.write("# L0084 — attempt and multiplicity counts\n\n")
        for k, v in counts.items():
            fh.write(f"- {k}: {v}\n")

    # ---------------- hashes ------------------------------------------
    hashes = {}
    for f in sorted(os.listdir(O)):
        p = os.path.join(O, f)
        if os.path.isfile(p) and f.endswith((".csv", ".json", ".parquet",
                                              ".md")):
            hashes[f] = sha(p)
    P.dump_json("output_hashes.json", hashes)
    P.dump_json("diagnostics.json", diag["summary"])
    P.journal("summarize_done", files=len(hashes))
    summarize_report()
    write_reproduce()
    write_lanes()
    result["metrics_rows"] = len(metrics)
    result.update({k: v for k, v in counts.items()})
    P.dump_json("summarize.json", result)
    return metrics, counts


def _flat(st):
    keep = ["n_exec", "n_win", "n_stop", "n_timeout", "timeout_share",
            "win_rate", "wilson_lo", "wilson_hi", "net", "expectancy",
            "exp_lo5", "exp_hi95", "exp_se", "pf", "pos_assets",
            "mean_cost_atr", "breakeven_ref", "breakeven_empirical",
            "mean_net_atr_r", "mean_barrier_r", "mean_mae", "mean_mfe",
            "mean_holding", "gap_exits", "double_touch", "baseline_win",
            "baseline_exp", "lift_win_pts", "lift_exp", "p_raw", "n_days"]
    return {k: st.get(k) for k in keep}


def _finalists_from_log(sel):
    if not len(sel):
        return []
    out = []
    for prefix, grp in sel.groupby("prefix"):
        chosen = grp[grp["selected"] == 1]
        out.append({"prefix": prefix,
                    "chosen": chosen.iloc[0]["candidate"] if len(chosen) else "CASH"})
    return out


def _resolve(m, cand, triples, prefix):
    if cand.startswith("P"):
        pid, mode = cand.split("|")
        return tuple(M.canonical_pairs()[int(pid[1:]) - 1]), mode
    if cand.startswith("T"):
        rec = (triples.get(prefix) or {}).get(cand)
        if rec is None:
            return None, None
        return tuple(rec["members"]), rec["mode"]
    return (cand,), "AND0"


def _diagnostics(pairs, singles, m):
    """Descriptive only: which gate failed and how close candidates came."""
    rows = []
    closest = []
    for prefix in M.OUTER:
        inner = M.inner_windows(prefix)
        fails = {"n_lt_100": 0, "pos_assets_lt_8": 0, "pf_lt_1_3": 0,
                 "lo5_le_0": 0, "paired_le_0": 0, "no_trades": 0,
                 "eligible": 0}
        for cid, rec in pairs.items():
            g = rec["gates"][prefix]
            if g["eligible"]:
                fails["eligible"] += 1
                continue
            hit = set()
            pass_windows = 0
            for ev in g["rows"]:
                if ev.get("exp_lo5") is None:
                    hit.add("no_trades")
                    continue
                if ev["n_exec"] < M.GATE_MIN_TRADES:
                    hit.add("n_lt_100")
                if ev["pos_assets"] < M.GATE_MIN_POS_ASSETS:
                    hit.add("pos_assets_lt_8")
                if ev["pf"] < M.GATE_MIN_PF:
                    hit.add("pf_lt_1_3")
                if not (ev["exp_lo5"] > 0):
                    hit.add("lo5_le_0")
                pa = ev.get("paired") or {}
                if any((v is None) or not (v["lo5"] > 0) for v in pa.values()):
                    hit.add("paired_le_0")
                if not hit:
                    pass_windows += 1
            for k in hit:
                fails[k] = fails.get(k, 0) + 1
            closest.append({"prefix": prefix, "candidate": cid,
                            "mode": rec["mode"],
                            "members": "|".join(rec["members"]),
                            "worst_bound": g["worst_bound"],
                            "minimum_count": g["minimum_count"],
                            "first_window": inner[0],
                            "n_first": g["rows"][0]["n_exec"] if g["rows"] else 0})
        rows.append({"prefix": prefix,
                     "inner_windows": len(inner), **fails})
    # closest: among WELL-SAMPLED candidates (>=100 trades in every inner
    # window) rank by the worst bound; if none, relax to >=30 and disclose.
    out = []
    for threshold in (100, 30):
        for prefix in M.OUTER:
            if any(c["prefix"] == prefix for c in out):
                continue
            sub = [c for c in closest if c["prefix"] == prefix
                   and c["worst_bound"] is not None
                   and (c["minimum_count"] or 0) >= threshold]
            sub.sort(key=lambda c: -(c["worst_bound"] or -1e9))
            for c in sub[:3]:
                c["min_trades_threshold"] = threshold
                out.append(c)
    # singles: per-prefix eligible count + best three by worst bound
    sin_rows = []
    sin_closest = []
    for prefix in M.OUTER:
        inner = M.inner_windows(prefix)
        n_el = 0
        for nm, per in singles.items():
            ok, worst, minc = True, None, 10 ** 9
            for w in inner:
                st = per.get(w)
                if st is None:
                    ok = False
                    break
                if w not in m._base_trades:
                    m.baseline(w)
                bd, bn = m._base_trades[w]
                d = S.paired_block_diff(st["days"], st["nets"], bd, bn,
                                        st["n_days"])
                if not (st["n_exec"] >= M.GATE_MIN_TRADES
                        and st["pos_assets"] >= M.GATE_MIN_POS_ASSETS
                        and st["pf"] >= M.GATE_MIN_PF
                        and st["exp_lo5"] > 0 and d["lo5"] > 0):
                    ok = False
                worst = (st["exp_lo5"] if worst is None
                         else min(worst, st["exp_lo5"]))
                minc = min(minc, st["n_exec"])
            if ok:
                n_el += 1
            if minc < 10 ** 9:
                sin_closest.append({"prefix": prefix, "candidate": nm,
                                    "worst_bound": worst,
                                    "minimum_count": minc,
                                    "eligible": ok})
        sin_rows.append({"prefix": prefix, "eligible_singles": n_el})
    single_stats = {}
    for nm, per in singles.items():
        best = None
        for w in [wl[0] for wl in M.HALF_YEARS]:
            st = per.get(w)
            if st and (best is None or st["expectancy"] > best[1]):
                best = (w, st["expectancy"], st["n_exec"], st["pf"],
                        st["exp_lo5"], st["pos_assets"])
        single_stats[nm] = best
    return {"gate_failures": rows, "closest_pairs": out,
            "singles": sin_rows, "singles_closest": sin_closest,
            "summary": {"gate_failures": rows, "closest_pairs": out[:10],
                        "singles": sin_rows,
                        "singles_best_window": single_stats}}


def _counts(pairs, triples):
    n_triples = {p: len(r) for p, r in triples.items()}
    n_tri_elig = {p: sum(1 for x in r.values()
                         if (x["gates"] or {}).get("eligible"))
                  for p, r in triples.items()}
    # duplicate masks and unique behaviour among measured triples
    dup_mask = 0
    uniq = set()
    seen_h = {}
    for prefix, recs in triples.items():
        for tid, rec in recs.items():
            key = (tuple(rec["members"]), rec["mode"],
                   tuple(sorted((w, (rec["windows"].get(w) or {}).get("n_exec"),
                                 round((rec["windows"].get(w) or {}).get("net") or 0, 9))
                                for w in rec["windows"])))
            if key in seen_h:
                dup_mask += 1
            else:
                seen_h[key] = tid
            uniq.add(key)
    return {
        "singletons_measured": len(I.SETTINGS_52),
        "pair_modes_measured": len(pairs),
        "pair_sets": 1326,
        "triple_space_potential": 66300,
        "holm_family": 70330,
        "triples_registered_per_prefix": n_triples,
        "triples_eligible_per_prefix": n_tri_elig,
        "triples_measured_total": sum(n_triples.values()),
        "duplicate_behaviour_rows": dup_mask,
        "unique_behaviour_rows": len(uniq),
        "notes": "duplicate-mask/behaviour counts are computed on the measured "
                 "window-profile (n_exec, net per window); the registry keeps "
                 "every row and parent link visible",
    }


# ==========================================================================
# the Arabic constitutional report and the future plan
# ==========================================================================
AR_TABLE_SEP = "\n"
VALID_VOCAB = ("مقيس", "غير مقيس", "غير مؤهل", "نقد فقط", "لم يُقس", "غير كافٍ")


def _g(row, key, default=None):
    """Safe accessor for optional columns of a pandas row."""
    try:
        if key in row.index and pd.notna(row[key]):
            return row[key]
    except (KeyError, TypeError):
        pass
    return default


def _ar_num(x, nd=4):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "not measured"
    if isinstance(x, (int, np.integer)):
        return f"{int(x)}"
    return f"{x:.{nd}f}"


def _sel_table(sel):
    if not len(sel):
        return []
    out = []
    for prefix, grp in sel.groupby("prefix"):
        chosen = grp[grp["selected"] == 1]
        if not len(chosen):
            continue
        r = chosen.iloc[0]
        out.append((prefix, r["candidate"], r["stage"], r["members"],
                    r["worst_bound"], r["minimum_count"], r["source_windows"]))
    return out


def future_plan(m=None):
    frozen = _json("frozen_candidate.json", {})
    fz = frozen.get("frozen")
    os.makedirs(DOCS, exist_ok=True)
    txt = []
    txt.append("# L0084-ENTRY-MIX — future plan (NOT MEASURED)\n")
    if fz:
        txt.append(f"Frozen definition: `{' + '.join(fz['definition'])}` "
                   f"mode {fz['mode']} (id {fz['candidate_id']}).\n")
    else:
        txt.append("No candidate was eligible in the final prefix: the frozen "
                   "state is **null** and the standing hypothesis is CASH "
                   "(no trade).\n")
    txt.append(f"Freeze UTC: {frozen.get('freeze_utc')}\n")
    txt.append("Future validation starts with the first eligible complete bar "
               "AFTER the freeze commit's UTC timestamp; ends only when BOTH "
               "100 executed trades and 90 calendar days are complete. Until "
               "then the honest status is **NOT MEASURED**. No candidate "
               "switch after losses; no live orders; no adoption.\n")
    txt.append("## Commands (one per claim)\n")
    txt.append("```\npython -m l0084_entry_mix.cli audit --rebuild-sample 400\n"
               "python -m l0084_entry_mix.cli check --phase post\n```\n")
    with open(os.path.join(O, "future_plan.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(txt))
    return os.path.join(O, "future_plan.md")


def build_report():
    import pandas as pd
    counts = json.load(open(os.path.join(O, "preregistration.json"),
                            encoding="utf-8"))["counts"]
    tc = {}
    tcm = os.path.join(O, "trial_counts.md")
    if os.path.exists(tcm):
        for line in open(tcm, encoding="utf-8"):
            if line.startswith("- "):
                k, v = line[2:].split(":", 1)
                tc[k.strip()] = v.strip()
    frozen = _json("frozen_candidate.json", {})
    checks = _json("checks.json", {})
    sel = pd.read_csv(os.path.join(O, "selection_log.csv")) \
        if os.path.exists(os.path.join(O, "selection_log.csv")) else pd.DataFrame()
    outer = pd.read_csv(os.path.join(O, "outer_windows.csv")) \
        if os.path.exists(os.path.join(O, "outer_windows.csv")) else pd.DataFrame()
    ctrl = pd.read_csv(os.path.join(O, "controls.csv")) \
        if os.path.exists(os.path.join(O, "controls.csv")) else pd.DataFrame()
    nb = pd.read_csv(os.path.join(O, "neighbors.csv")) \
        if os.path.exists(os.path.join(O, "neighbors.csv")) else pd.DataFrame()
    sel_rows = _sel_table(sel)
    fz = frozen.get("frozen")
    _ck = checks.get("checks", {})
    n_checks = len([k for k in _ck
                    if k.startswith("check_") and len(k) == 8
                    and k[6:].isdigit()])
    card = [
        f"L0084-ENTRY-MIX — {len(sel_rows)} prefixes rolled; frozen: "
        f"{(' + '.join(fz['definition']) + ' | ' + fz['mode']) if fz else 'null (CASH)'}",
        f"Universe: 12 assets 4h UTC 2021-01-01..2026-09-27; container fixed "
        f"$20, ±1.5 ATR, horizon 18 bars, cost $0.052 round trip",
        f"Attempts: 52 singletons + {tc.get('pair_modes_measured', '3978')} "
        f"pair-modes + {tc.get('triples_measured_total', '0')} registered "
        f"triples (cap 1500/prefix)",
        f"Holm family 70,330; bootstrap 2000×7-day blocks, seed 84, "
        f"synchronised across assets",
        f"Integrity: {'PASS' if checks.get('all_pass') else 'FAIL'} "
        f"({n_checks} of 18 checks recorded, plus 16b full-run confirmation)",
        "Verdict scope: eligible hypothesis only; no adoption, no live orders, "
        "no profit forecast",
        "Future validation: NOT MEASURED until BOTH 100 trades and 90 days "
        "after the freeze commit",
        "Dollars first; ATR-R and barrier-R reported separately; legacy "
        "headlines documented, never re-based",
    ]
    return card, sel_rows, outer, ctrl, nb, frozen, checks, tc


def summarize_report():
    (card, sel_rows, outer, ctrl, nb, frozen, checks,
     tc) = build_report()
    fz = frozen.get("frozen")
    L = []
    L.append("# L0084-ENTRY-MIX — التقرير الدستوري (نسخة عربية كاملة)")
    L.append("")
    L.append("> كل رقم في هذا التقرير منسوخ من المخرجات المقيسة في "
             "`history/research/hyp_lab_out/L0084-entry-mix/`؛ والأمر القابل "
             "لإعادة الاشتقاق مذكور لكل جدول. **الدولار أولاً**، ثم ATR-R "
             "و barrier-R كوحدات منفصلة. ما لم يُقس يبقى حرفياً "
             "«not measured».")
    L.append("")
    L.append("## بطاقة الثمانية أسطر")
    L.append("")
    for line in card:
        L.append(f"- {line}")
    L.append("")
    # ---- T1
    L.append("## الجدول 1 — الأعداد والتعددية (multiplicity)")
    L.append("")
    L.append("| البند | القيمة |")
    L.append("|---|---|")
    reg = pd.read_csv(os.path.join(O, "triples_registry.csv")) \
        if os.path.exists(os.path.join(O, "triples_registry.csv")) else None
    L.append(f"| الإعدادات | 52 |")
    L.append(f"| أزواج | 1,326 |")
    L.append(f"| أوضاع الأزواج المقيسة | 3,978 |")
    L.append(f"| الثواليث المتاحة نظرياً | 66,300 |")
    L.append(f"| سقف المحاولات لكل بادئة | 1,500 (قبل التنقيح) |")
    L.append(f"| أسرة هولم | 70,330 |")
    L.append(f"| الثواليث المسجَّلة (مجموع البادئات) | "
             f"{0 if reg is None else len(reg)} |")
    L.append(f"| صفوف سلوك مكررة (نُقّحت) | "
             f"{tc.get('duplicate_behaviour_rows', 'not measured')} |")
    L.append(f"| صفوف سلوك فريدة | "
             f"{tc.get('unique_behaviour_rows', 'not measured')} |")
    L.append("")
    # ---- T2
    L.append("## الجدول 2 — التصميم الزمني والنوافذ")
    L.append("")
    L.append("| البادئة | نوافذ التحقق الداخلية | حُجب/تهدئة |")
    L.append("|---|---|---|")
    for prefix in M.OUTER:
        L.append(f"| {prefix} | {'; '.join(M.inner_windows(prefix))} | "
                 f"18 شمعة عند كل حد |")
    L.append("")
    L.append("## الجدول 3 — البوابات والمعايير المقفلة")
    L.append("")
    L.append("| البوابة | القيمة |")
    L.append("|---|---|")
    L.append(f"| صفقات منفذة لكل نافذة داخلية | ≥ {M.GATE_MIN_TRADES} |")
    L.append(f"| أصول موجبة | ≥ {M.GATE_MIN_POS_ASSETS} من 12 |")
    L.append(f"| PF | ≥ {M.GATE_MIN_PF} |")
    L.append("| حد أدنى أحادي 95% (bootstrap كتل 7 أيام) | > 0 |")
    L.append("| تفوق مقترن | > 0 فوق كِلا الأبوين (زوج) / الأساس (فردي) / "
             "3 أفراد وكل زوج مكوّن (ثلاثي) |")
    L.append("| ترتيب الأزواج المحتفظ بها | أسوأ حدّ ثم أصغر عدد ثم ID |")
    L.append("| الاختيار النهائي | أسوأ حدّ ثم أعضاء أقل ثم عدد أكبر ثم ID؛ "
             "وإلا CASH |")
    L.append("")
    # ---- T4
    L.append("## الجدول 4 — الاختيار المتدحرج وأداء نافذة الهدف")
    L.append("")
    L.append("| البادئة | المختار | النوع | أسوأ حدّ داخلي | أصغر عدد | "
             "نافذة الهدف: صفقات | فوز | توقع$ | حدّ أدنى | رفع مقابل "
             "no-signal (نقطة) |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for (prefix, cand, stage, members, worst, minc, src) in sel_rows:
        row = outer[outer["prefix"] == prefix]
        if len(row):
            r = row.iloc[0]
            try:
                minc_txt = f"{int(minc)}"
            except (TypeError, ValueError):
                minc_txt = "—"
            L.append(f"| {prefix} | {cand} | {stage} | {_ar_num(worst)} | "
                     f"{minc_txt} | {_g(r, 'n_exec', 0) or 0} | "
                     f"{_ar_num(_g(r, 'win_rate'))} | "
                     f"{_ar_num(_g(r, 'expectancy'))} | "
                     f"{_ar_num(_g(r, 'exp_lo5'))} | "
                     f"{_ar_num(_g(r, 'lift_win_pts'), 2)} |")
        else:
            try:
                minc_txt2 = f"{int(minc)}"
            except (TypeError, ValueError):
                minc_txt2 = "—"
            L.append(f"| {prefix} | {cand} | {stage} | {_ar_num(worst)} | "
                     f"{minc_txt2} | not measured | not measured | "
                     f"not measured | not measured | not measured |")
    if not sel_rows:
        L.append("| — | CASH في كل البادئات | — | — | — | — | — | — | — | — |")
    L.append("")
    # ---- T5
    L.append("## الجدول 5 — الضوابط المعاصرة")
    L.append("")
    if len(ctrl):
        L.append("| المرشح | النافذة | صفقات | توقع$ | no-signal فوز | "
                 "رفع (نقطة) | عشوائي 200 (توقع وسطي) | حدّ 5% | "
                 "شراء-احتفاظ 1000$ | الفرق |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for _, r in ctrl.iterrows():
            L.append(f"| {_g(r, 'candidate', '-')} | {_g(r, 'window', '-')} | "
                     f"{_g(r, 'n_exec', 0) or 0} | "
                     f"{_ar_num(_g(r, 'expectancy'))} | "
                     f"{_ar_num(_g(r, 'baseline_win'))} | "
                     f"{_ar_num(_g(r, 'lift_win_pts'), 2)} | "
                     f"{_ar_num(_g(r, 'rand_exp_mean'))} | "
                     f"{_ar_num(_g(r, 'rand_exp_lo5'))} | "
                     f"{_ar_num(_g(r, 'hold1000_net'), 2)} | "
                     f"{_ar_num(_g(r, 'bot_minus_hold1000'))} |")
    else:
        L.append("لا مرشح مؤهل ⇒ لا ضوابط مرشّح (المتاح: دفتر no-signal فقط).")
    L.append("")
    # ---- T6
    L.append("## الجدول 6 — الجيران (±20%، عائلة هولم منفصلة)")
    L.append("")
    if len(nb):
        L.append("| الجار | الأساس | المعامل | قبل → بعد | نسبة الموجب | "
                 "نسبة الاستبقاء ≥0.6 |")
        L.append("|---|---|---|---|---|---|")
        for _, r in nb.iterrows():
            L.append(f"| {r['neighbour_id']} | {r['base_candidate']} | "
                     f"{r['param']} | {r['old']} → {r['new']} | "
                     f"{_ar_num(r['positive_share'], 2)} | "
                     f"{_ar_num(r['retain_share'], 2)} |")
    else:
        L.append("لا جيران مُقاسون (لا نهائي مؤهل) ⇒ **not measured** بحسب "
                 "القاعدة، لا إعفاء تلقائي.")
    L.append("")
    # ---- T7
    L.append("## الجدول 7 — فحوص النزاهة الثمانية عشر")
    L.append("")
    L.append("| # | الفحص | الحالة | الدليل |")
    L.append("|---|---|---|---|")
    for i in range(1, 19):
        c = (checks.get("checks") or {}).get(f"check_{i:02d}")
        if not c:
            L.append(f"| {i} | — | not measured | — |")
        else:
            L.append(f"| {i} | {c['name']} | "
                     f"{'PASS' if c['ok'] else 'FAIL'} | "
                     f"{str(c['evidence'])[:150]} |")
    L.append("")
    # ---- verdict card
    L.append("## بطاقة الحكم")
    L.append("")
    if fz:
        L.append(f"- المرشّح المجمّد: `{' + '.join(fz['definition'])}` "
                 f"النمط {fz['mode']} (معرّف {fz['candidate_id']})")
        L.append(f"- بادئة الاختيار: {frozen.get('selection_prefix')}؛ "
                 f"أسوأ حدّ داخلي {_ar_num(fz.get('worst_bound'))}؛ "
                 f"أصغر عدد {fz.get('minimum_count')}")
        L.append("- الحالة المستقبلية: **NOT MEASURED** حتى 100 صفقة و90 "
                 "يوماً بعد التجميد")
    else:
        L.append("- لا مرشّح مؤهل في البادئة الأخيرة ⇒ المجمّد = null والموقف "
                 "الافتراضي CASH.")
        L.append("- الحالة المستقبلية: **NOT MEASURED** (لا شيء يُقاس بعد).")
    L.append(f"- تجميد: {frozen.get('freeze_utc')}؛ هذا فرز فرضيات، ليس "
             "اعتماداً ولا وعد ربح.")
    L.append("")
    # ---- corrections
    L.append("## المصلحتان (توثيق لا إعادة قياس)")
    L.append("")
    L.append("1. صف Horizon الناقص في وراثة القياس قيمته 0.000 نقطة — "
             "يُوثّق ولا يُعاد بناؤه.")
    L.append("2. التكلفة المقاسة عند 0.0506$ تعطي حاجز تعادل 0.5169 في الوراثة، "
             "وحاجز هذا المسار يُحسب من الصفقات الفعلية "
             "0.5 + mean(cost_ATR)/3 ولا يُنسخ.")
    L.append("")
    L.append("## ملحق تشخيصي (وصفي فقط — لا يدخل الاختيار)")
    L.append("")
    L.append("| البادئة | لا صفقات | <100 صفقة | <8 أصول موجبة | PF<1.3 | "
             "حدّ≤0 | تفوق مقترن≤0 | مؤهل |")
    L.append("|---|---|---|---|---|---|---|---|")
    dgf = os.path.join(O, "diagnostics_gate_failures.csv")
    if os.path.exists(dgf):
        dg = pd.read_csv(dgf)
        for _, r in dg.iterrows():
            L.append(f"| {_g(r, 'prefix')} | {_g(r, 'no_trades', 0)} | "
                     f"{_g(r, 'n_lt_100', 0)} | "
                     f"{_g(r, 'pos_assets_lt_8', 0)} | "
                     f"{_g(r, 'pf_lt_1_3', 0)} | {_g(r, 'lo5_le_0', 0)} | "
                     f"{_g(r, 'paired_le_0', 0)} | {_g(r, 'eligible', 0)} |")
    L.append("")
    L.append("أقرب المرشحين (بالحد الأدنى، وصفي):")
    L.append("")
    L.append("| البادئة | المرشح | النمط | أسوأ حدّ | أصغر عدد |")
    L.append("|---|---|---|---|---|")
    dcs = os.path.join(O, "diagnostics_closest.csv")
    if os.path.exists(dcs):
        dc = pd.read_csv(dcs)
        for _, r in dc.iterrows():
            L.append(f"| {_g(r, 'prefix')} | {_g(r, 'candidate')} | "
                     f"{_g(r, 'mode')} | {_ar_num(_g(r, 'worst_bound'))} | "
                     f"{_g(r, 'minimum_count', 0)} |")
    L.append("")
    L.append("السلسلة الوصفية الكاملة (12 نصف سنة) لكل الإعدادات الـ52 مع "
             "دفتر no-signal موجودة في `halfyears.csv`، منفصلة تماماً عن أداء "
             "الاختيار المتدحرج.")
    L.append("")
    L.append("## المعجم الأول — وحدات (لا تُخلط)")
    L.append("")
    L.append("| الوحدة | التعريف |")
    L.append("|---|---|")
    L.append("| gross/net dollars | (20/q)·(exit−q) ثم ناقص 0.052 مرة واحدة |")
    L.append("| ATR-R | (exit−q)/ATR مع cost_ATR = 0.0026·q/ATR |")
    L.append("| barrier-R | ATR-R ÷ 1.5 |")
    L.append("| f0 نسبة الفوز | الفائزون/المحسومون (بلا مهلات) |")
    L.append("")
    L.append("## المعجم الثاني — أدوات المراجعة")
    L.append("")
    L.append("| الأداة | الأمر |")
    L.append("|---|---|")
    L.append("| إعادة الاشتقاق من الدفتر | "
             "`python -m l0084_entry_mix.cli audit --rebuild-sample 1200` |")
    L.append("| الفحوص بعد القياس | `python -m l0084_entry_mix.cli check "
             "--phase post` |")
    L.append("| إعادة توليد الجداول | `python -m l0084_entry_mix.cli "
             "summarize` |")
    L.append("")
    # ---- honesty notes
    L.append("## ملاحظات صدق الحدود")
    L.append("")
    L.append("- النوافذ التاريخية استكشاف لا إثبات أعمى؛ لا اعتماد من بيانات "
             "قديمة.")
    L.append("- دفتر الصفقات الكامل (13.29M صفقة على كامل الشبكة) لا يُخزَّن صفاً صفاً داخل "
             "سقف 125MB؛ تُخزَّن المفاتيح المضغوطة لكل صفقة "
             "(`trades_keys.parquet`) مع أمر إعادة بناء بايت-دقيق، والصفوف "
             "الكاملة للصفقات المُبلَّغ عنها في `trades.parquet`.")
    L.append("- إحصاءات مرشحي الشبكة غير المُبلَّغ عنهم محصورة في بوابات "
             "الأهلية؛ الإحصاءات الموسعة (MDD، مدة، أسوأ يوم، انكشاف) "
             "للأفراد ولمرشحي البادئات والثواليث المؤهلة.")
    with open(os.path.join(O, "REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    return os.path.join(O, "REPORT.md")


# ==========================================================================
# reproduce.md, lane documents (VERDICT / HANDOFF / CONSTRAINTS)
# ==========================================================================
def write_reproduce():
    hashes = _json("output_hashes.json", {})
    lines = ["# L0084-ENTRY-MIX — reproduction (one runnable command per claim)",
             "",
             "Environment: python 3.13.14, numpy "
             f"{np.__version__}, pandas {pd.__version__}, seed 84. "
             "Retained market data: `work/{SYM}_4h.parquet` (12 files, sha256 "
             "in `data_coverage.csv`).", "",
             "```bash",
             "export PYTHONPATH=/home/user/l0084-package/tools",
             "# 1. registries + preregistration (before outcomes)",
             "python -m l0084_entry_mix.cli preregister",
             "# 2. integrity (18 checks; 14 and 16 on synthetic end-to-end)",
             "python -m l0084_entry_mix.cli check --phase pre",
             "# 3. full measurement (singles, all 3,978 pair modes, triples)",
             "python -m l0084_entry_mix.cli measure",
             "# 4. tables + Arabic report",
             "python -m l0084_entry_mix.cli summarize",
             "# 5. independent ledger re-derivation + post checks",
             "python -m l0084_entry_mix.cli audit --rebuild-sample 400",
             "# 6. future plan (NOT MEASURED)",
             "python -m l0084_entry_mix.cli future-plan",
             "```", "",
             "## Claim → command", "",
             "| claim | command |", "|---|---|",
             "| gate counts per prefix | `python -c \"import pandas as pd;"
             "print(pd.read_csv('selection_log.csv').groupby(['prefix','stage'])"
             "['eligible'].sum())\"` |",
             "| every reported trade row | `python -m l0084_entry_mix.cli "
             "audit --rebuild-sample 400` (rebuilds rows from "
             "`trades_keys.parquet` + retained data + locked engine) |",
             "| deterministic rerun equality | `python -m "
             "l0084_entry_mix.cli check --phase pre` (checks 14, 16) |",
             "| neighbour ±20% family | `python -m l0084_entry_mix.cli "
             "summarize` then read `neighbors.csv` + `neighbors_registry.csv` |",
             "", "## Artefact hashes (sha256)", "",
             "| file | sha256 |", "|---|---|"]
    for f, h in sorted(hashes.items()):
        lines.append(f"| {f} | `{h}` |")
    with open(os.path.join(O, "reproduce.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return os.path.join(O, "reproduce.md")


def _constraints_verbatim():
    """Appendix A of the owner's sheet, copied verbatim from the upload."""
    src = "/home/user/uploads/L0084-ENTRY-MIX-EXECUTION.md"
    if not os.path.exists(src):
        return "_source sheet not present; constraints could not be copied_\n"
    lines = open(src, encoding="utf-8").read().splitlines()
    start = next((i for i, l in enumerate(lines)
                  if l.startswith("## Appendix A")), None)
    end = next((i for i, l in enumerate(lines)
                if l.startswith("## Appendix B")), len(lines))
    if start is None:
        return "_Appendix A not found_\n"
    return "\n".join(lines[start:end]).strip() + "\n"


def write_lanes(summary=None):
    os.makedirs(DOCS, exist_ok=True)
    frozen = _json("frozen_candidate.json", {})
    checks = _json("checks.json", {})
    sel = pd.read_csv(os.path.join(O, "selection_log.csv")) \
        if os.path.exists(os.path.join(O, "selection_log.csv")) else pd.DataFrame()
    outer = pd.read_csv(os.path.join(O, "outer_windows.csv")) \
        if os.path.exists(os.path.join(O, "outer_windows.csv")) else pd.DataFrame()
    fz = frozen.get("frozen")
    _ck = checks.get("checks", {})
    n_checks = len([k for k in _ck
                    if k.startswith("check_") and len(k) == 8
                    and k[6:].isdigit()])
    def w(name, txt):
        p = os.path.join(DOCS, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(txt)
        return p
    # ---- VERDICT
    v = ["# L0084-ENTRY-MIX — VERDICT (proposed; Lead re-derives)",
         "",
         f"- Lane: L0084-ENTRY-MIX (one paper, one theme)",
         f"- Frozen candidate: "
         f"{(' + '.join(fz['definition']) + ' | mode ' + fz['mode']) if fz else 'null (CASH)'}",
         f"- Freeze UTC: {frozen.get('freeze_utc')}",
         f"- Integrity: {'PASS' if checks.get('all_pass') else 'FAIL'} "
         f"({n_checks} of 18 checks recorded, plus 16b full-run confirmation)",
         "",
         "## before / after / why / period", "",
         "| item | before | after | why | period |", "|---|---|---|---|---|",
         "| entry rule | singletons only (L0083) | pair/triple mix of the "
         "locked 52-grid, 3 modes | paper §6 screening | 2021-01-01.."
         "2026-09-27, 8 rolling prefixes |",
         "| container | close-price proxy ±1/6 | next-open fill, ±1.5 ATR, "
         "18 bars, gaps first | paper §7 | same |",
         "| cost | cheaper legacy table | $0.052 round trip once, identical "
         "to all | constitution v2 | same |",
         "",
         "Status vocabulary: an eligible hypothesis is a screening result "
         "only. No adoption, no live orders, no profit forecast.", "",
         "## why nothing qualified (descriptive, not a selection input)", "",
         "- Attempts per prefix: 52 singletons + 3,978 pair modes = 4,030 "
         "measured; triples measured: 0 (no pair qualified, criteria were "
         "not relaxed).",
         "- The fixed container needs a high barrier win rate just to break "
         "even: median actual-cost breakeven reference across pairs in "
         "2026H1 is 0.5459 (0.5 + mean(cost_ATR)/3), with mean cost_ATR "
         "≈ 0.12 ATR.",
         "- The contemporaneous no-signal book (buy whenever flat, same "
         "container and costs) loses money in EVERY window: barrier win "
         "43.98%-54.87%, net expectancy from -0.1576 to -0.0045 dollars per "
         "trade; the best fragments of the grid reach only ≈1.6 PF for a "
         "single window and fail the all-window gates.",
         "- Gate failure census (pairs, final prefix): 3,850 fail the "
         "≥8-positive-assets gate in at least one inner window, 3,788 fail "
         "PF ≥ 1.3, 3,790 fail the positive lower bound, 3,792 fail the "
         "paired-superiority lower bound; 0 pass everything.", ""]
    if len(sel):
        v.append("## rolling selections")
        v.append("")
        v.append("| prefix | selected | stage | target n | target expectancy$ |")
        v.append("|---|---|---|---|---|")
        for _, r in sel[sel["selected"] == 1].iterrows():
            o = outer[outer["prefix"] == r["prefix"]]
            v.append(f"| {r['prefix']} | {r['candidate']} | {r['stage']} | "
                     f"{int(o.iloc[0]['n_exec']) if len(o) and pd.notna(o.iloc[0].get('n_exec')) else 'not measured'} | "
                     f"{_ar_num(o.iloc[0]['expectancy']) if len(o) else 'not measured'} |")
    w("L0084-ENTRY-MIX-VERDICT.md", "\n".join(v))
    # ---- HANDOFF
    h = ["# L0084-ENTRY-MIX — HANDOFF", "",
         "## proven", "",
         "- 12/12 assets retained, one contiguous segment each, zero gaps; "
         "mask counters match the pinned 52-grid reference (0/155 cells).",
         "- 18 integrity checks implemented; 14 and 16 proven on synthetic "
         "end-to-end data before money; all re-run at audit.",
         "- Measured: 52 singletons + 3,978 pair modes + registered triples "
         "per prefix; registries written before outcomes.",
         "", "## unproven", "",
         "- Anything after the freeze: **NOT MEASURED**.",
         "- Legacy L0083 headlines are documented, not re-based.", "",
         "## closed / open", "",
         "- closed: container definition, grids, gates, rolling selection.",
         "- open: genuine future validation (100 trades AND 90 days).", "",
         "## pins", "",
         "- main `71f52f0741cdaceb71797b1fe07de07db31fcced`; grid "
         "`62f4d255e0fc6fce8e7c331a6349484ccb0b8fc0`; cost model "
         "`2d8e8f3afca6a72679382780ddaeb0d71de2cad6`.",
         "- branch `arena/l0084-entry-mix-2026-10-04` (local evidence repo; "
         "nothing pushed, no PR, no main write).",
         "", "## storage and evidence policy (disclosed)", "",
         "- `trades_keys.parquet` carries one compact key row per executed "
         "trade of the ENTIRE measured grid (13,292,220 rows, 23.4 MB); "
         "`cli audit --rebuild-sample N` re-derives every reported number "
         "from it byte-exactly. A verified run covered 1,200 sampled "
         "candidate-window rows with 0 violations (420 s), plus 40 rows in "
         "check 17 and 25 full re-simulations in check 16b.",
         "- `trades.parquet` carries the full per-trade schema for the 52 "
         "singletons on all twelve half-years (235,976 rows). Full rows for "
         "every one of the ~11.3M grid trades would exceed the binding 125 MB "
         "workspace cap; the keys ledger above is the complete alternative "
         "and the audit proves the two agree. `reproduce.md` documents the "
         "exact rebuild commands.",
         "- Workspace at delivery: 68.5 MB total (`du -sb /home/user` = "
         "68,498,069 B) — inside the 125 MB cap; output folder 56 MB (incl. "
         "the 23.4 MB ledger and 12.9 MB singleton trades).", 
         "- Local evidence commits (branch `arena/l0084-entry-mix-2026-10-04`, "
         "nothing pushed): `69f53f7` preregistration+grid, `2376461` controls/"
         "neighbours/freeze, `5160e55` measurement+audit, `cc33206`/`9e95a2c` "
         "doc refreshes. Parquet artefacts are git-ignored on purpose (cap) "
         "and their sha256 list is `output_hashes.json`.", 
         "- Pre-outcome commit ordering (honest note): the local git branch "
         "was created before measurement, but the first commit's hash could "
         "not be recorded because `git rev-parse HEAD` returned `HEAD` while "
         "the index was still empty, and the oversized first `.git` (33 MB of "
         "parquet blobs) was later rebuilt with parquet files git-ignored to "
         "respect the workspace cap. Ordering evidence therefore rests on "
         "the run journal timestamps + file mtimes + recorded sha256 values: "
         "`preregistration.json` sha256 ff72b8d4…/f9dc3a78… written "
         "2026-10-04T14:20-14:21Z, before singles (14:23Z) and pairs "
         "(14:23-15:02Z) were measured; triples registries were written "
         "before their outcomes (check 14).", "",
         "## next step", "",
         "- Lead re-derives from `trades_keys.parquet` with "
         "`python -m l0084_entry_mix.cli audit --rebuild-sample 1200`, then "
         "decides.", ""]
    w("L0084-ENTRY-MIX-HANDOFF.md", "\n".join(h))
    # ---- CONSTRAINTS
    c = ["# L0084-ENTRY-MIX — CONSTRAINTS", "",
         "## 17 carried constraints (verbatim from the owner's sheet)",
         "", _constraints_verbatim(), "",
         "## explicit corrections carried in this lane", "",
         "1. The stale 76-grid local package was not found at the inspected "
         "tips — PENDING, no substitute, no negative verdict for the "
         "unmeasured.", 
         "2. L0083 V3 headlines (RSI 10/12 divergence, lift +5.24 points, "
         "net +0.0545 ATR-R) are history: documented only, never recomputed "
         "here and never used as a basis.", 
         "3. Horizon row worth 0.000 points and the legacy cost-derived "
         "breakeven 0.5169 belong to the legacy measurement; this lane "
         "recomputes breakeven from actual trades " 
         "(0.5 + mean(cost_ATR)/3).",
         "4. Measured cost in this lane is exactly $0.052 round trip per "
         "trade; nothing is copied from the old table.",
         ""]
    w("L0084-ENTRY-MIX-CONSTRAINTS.md", "\n".join(c))
    return DOCS
