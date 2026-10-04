#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0084-ENTRY-MIX — command line.

    python -m l0084_entry_mix.cli preregister
    python -m l0084_entry_mix.cli check --phase pre|post
    python -m l0084_entry_mix.cli measure [--skip-triples] [--force]
    python -m l0084_entry_mix.cli summarize
    python -m l0084_entry_mix.cli audit [--rebuild-sample N] [--rebuild-all]
    python -m l0084_entry_mix.cli future-plan

Every command appends to O/run_journal.jsonl and re-derives its numbers from
the retained market data and the locked engine, never from prose.
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

from . import data as D
from . import engine as E
from . import indicators as I
from . import measure as M
from . import pipeline as P
from . import stats as S
from . import tests as T


# ==========================================================================
def cmd_preregister(args):
    m = M.Measurer()
    P.stage_preregister(m)
    print("preregister: ok")


def cmd_check(args):
    m = M.Measurer() if args.phase == "post" else None
    res = T.run_all(args.phase, m=m)
    if not res["all_pass"]:
        print("CRITICAL: integrity failures —", res["failures"])
        return 2
    return 0


def _cache(name):
    return os.path.join(P.CACHE, name)


def _load(name):
    import gzip
    for cand in (name + ".gz", name):
        p = _cache(cand)
        if os.path.exists(p):
            op = gzip.open if cand.endswith(".gz") else open
            with op(p, "rb") as fh:
                return pickle.load(fh)
    return None


def cmd_measure(args):
    t0 = time.time()
    os.makedirs(P.CACHE, exist_ok=True)
    m = M.Measurer()
    # ---- singles
    singles = None if args.force else _load("singles.pkl")
    if singles is None:
        singles = P.stage_singles(m)
    # ---- pairs (the full grid)
    pairs = None if args.force else _load("pairs.pkl")
    if pairs is None:
        pairs = P.stage_pairs(m, singles)
    P.git_commit("L0084 pair grid measured (3,978 candidates)")
    # ---- triples per prefix (registry first)
    triples = {} if args.force else (_load("triples.pkl") or {})
    for prefix in M.OUTER:
        if prefix in triples:
            continue
        retained = P.select_retained(pairs, prefix)
        reg = P.register_triples(prefix, retained)
        P.journal("triples_registered", prefix=prefix, n=len(reg),
                  retained={k: [r["cid"] for r in v]
                            for k, v in retained.items()})
        if args.skip_triples:
            triples[prefix] = {}
            continue
        triples[prefix] = P.stage_triples(m, singles, pairs, prefix, reg)
        P.journal("triples_measured", prefix=prefix,
                  n=len(triples[prefix]),
                  eligible=sum(1 for r in triples[prefix].values()
                               if (r["gates"] or {}).get("eligible")))
        import gzip as _gz
        with _gz.open(_cache("triples.pkl.gz"), "wb") as fh:
            pickle.dump(triples, fh, protocol=4)
    P.git_commit("L0084 triples registered and measured per prefix")
    # ---- selection + rolling outer evaluation (target windows read here,
    #      strictly after the selection is written)
    finalists, _u = P.stage_selection(m, singles, pairs, triples)
    P.git_commit("L0084 rolling selection per prefix (targets unread)")
    P.stage_outer(m, finalists)
    P.journal("outer_targets_read", note="after selection_log.csv written")
    # ---- controls and neighbours
    P.stage_controls(m, finalists, singles)
    P.stage_neighbours(m, finalists, singles, pairs)
    frozen = P.stage_freeze(finalists, triples)
    P.git_commit("L0084 controls, neighbours, frozen candidate")
    P.journal("measure_done", elapsed_s=round(time.time() - t0, 1),
              frozen=frozen.get("frozen"))
    print("measure: done in %.0fs" % (time.time() - t0))
    return 0


# ==========================================================================
def cmd_summarize(args):
    from . import report
    report.summarize()
    print("summarize: ok")


def cmd_audit(args):
    m = M.Measurer()
    # ---- independent rebuild of the pair grid from the keys ledger
    keys_path = os.path.join(P.O, "trades_keys.parquet")
    summary = {"rebuild": None}
    if os.path.exists(keys_path):
        keys = pd.read_parquet(keys_path)
        metrics_path = os.path.join(P.O, "metrics.parquet")
        metrics = pd.read_parquet(metrics_path) if os.path.exists(
            metrics_path) else pd.DataFrame()
        rows = metrics[metrics["stage"] == "pair"]
        if args.rebuild_sample and args.rebuild_sample > 0:
            rows = rows.sample(min(args.rebuild_sample, len(rows)),
                               random_state=84)
        t0 = time.time()
        bad = []
        checked = 0
        for _, row in rows.iterrows():
            cand = row["candidate"]
            pid = cand.split("|")[0]
            members = tuple(M.canonical_pairs()[int(pid[1:]) - 1])
            window = row["window"]
            ci = int(row["cand_idx"])
            n = 0
            nets = []
            for sym_i, sym in enumerate(D.ASSETS):
                sub = keys[(keys["candidate_idx"] == ci)
                           & (keys["asset_idx"] == sym_i)]
                if len(sub) == 0:
                    continue
                p = m.panels[sym]
                lo, hi = p.ranges[window]
                recs, _b = E.execute_many(p.o, p.h, p.l, p.c, p.atr, p.seg,
                                          sub["signal_bar"].to_numpy(), sym,
                                          cand)
                kept = E.window_trades(recs, lo, hi)
                n += len(kept)
                nets.extend(t["net_dollars"] for t in kept)
            checked += 1
            if n != int(row["n_exec"]):
                bad.append((cand, window, "n", n, int(row["n_exec"])))
            elif abs(sum(nets) - float(row["net"])) > 1e-9:
                bad.append((cand, window, "net", sum(nets), row["net"]))
        summary["rebuild"] = {"rows_checked": checked, "violations": bad[:5],
                              "violations_n": len(bad),
                              "elapsed_s": round(time.time() - t0, 1)}
        P.journal("audit_rebuild", **summary["rebuild"])
    res = T.run_all("post", m=m)
    obj = T.load_json("checks.json") if hasattr(T, "load_json") else None
    with open(os.path.join(P.O, "audit.json"), "w", encoding="utf-8") as fh:
        import json
        json.dump({"rebuild": summary["rebuild"],
                   "checks": {"all_pass": res["all_pass"],
                              "failures": res["failures"]}}, fh, indent=1)
    if not res["all_pass"]:
        print("CRITICAL: post-phase integrity failures —", res["failures"])
        return 2
    return 0


def cmd_future_plan(args):
    from . import report
    report.future_plan()
    print("future-plan: ok")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="l0084_entry_mix")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("preregister")

    c = sub.add_parser("check")
    c.add_argument("--phase", choices=["pre", "post"], default="pre")

    ms = sub.add_parser("measure")
    ms.add_argument("--force", action="store_true")
    ms.add_argument("--skip-triples", action="store_true")

    sub.add_parser("summarize")

    au = sub.add_parser("audit")
    au.add_argument("--rebuild-sample", type=int, default=400)
    au.add_argument("--rebuild-all", action="store_true")

    sub.add_parser("future-plan")

    args = ap.parse_args(argv)
    fn = {"preregister": cmd_preregister, "check": cmd_check,
          "measure": cmd_measure, "summarize": cmd_summarize,
          "audit": cmd_audit, "future-plan": cmd_future_plan}[args.cmd]
    return fn(args) or 0


if __name__ == "__main__":
    sys.exit(main())
