#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0084-ENTRY-MIX — command line.

    python -m l0084_entry_mix.cli preregister
    python -m l0084_entry_mix.cli check --phase pre|post
    python -m l0084_entry_mix_r1.cli measure
    python -m l0084_entry_mix.cli summarize
    python -m l0084_entry_mix.cli audit [--rebuild-sample N] [--rebuild-all]
    python -m l0084_entry_mix.cli future-plan

Every command appends to O/run_journal.jsonl and re-derives its numbers from
the retained market data and the locked engine, never from prose.
"""
from __future__ import annotations

import argparse
import json
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

MEASUREMENT_GATE_READY=False  # reopen only after full metrics/report partitioning and raw-to-metrics audit pass the synthetic integration suite


# ==========================================================================
def cmd_preregister(args):
    raise RuntimeError("The original preregistration is already frozen; use the implementation-only amend-prereg command. It will not be overwritten.")
    import datetime, zoneinfo
    from . import preregister as R
    from .publisher import publish_files
    m = M.Measurer()
    result = R.build(m, os.environ.get("L0084_R1_SHEET", "/home/user/uploads/L0084-R1-FINAL-EXECUTION-v3.md"),
                     os.environ.get("L0084_R1_PRIOR_ROOT", "/home/user/l0084-package"))
    out = M.O
    rel = [f"history/research/hyp_lab_out/L0084-entry-mix-r1/{n}" for n in
           ("sources.json", "catalogue.csv", "pairs_registry.csv", "data_coverage.csv",
            "preregistration.json", "catalogue_pending.md")]
    now = datetime.datetime.now(datetime.timezone.utc); aden = now.astimezone(zoneinfo.ZoneInfo("Asia/Aden"))
    log = (f"\n\n### L0084-R1 preregistration ({now:%Y-%m-%dT%H:%M:%SZ})\n\n"
           f"- Pre-outcome registries frozen; {result['catalogue_rows']} settings, {result['pairs']} pairs, {result['pair_modes']} modes; input panels={result['assets']}.\n"
           f"- Preregistration SHA256 recorded in its file; code commit {os.environ.get('L0084_R1_CODE_COMMIT','UNSET')}.\n"
           f"- No candidate outcomes or selection read. Next: run the pre-measurement integrity suite.\n")
    tick = (f"# L0084-R1 tick 004 — preregistration frozen\n\n- UTC: {now:%Y-%m-%dT%H:%M:%SZ}\n- Asia/Aden: {aden:%Y-%m-%dT%H:%M:%S%:z}\n"
           f"- Counts: {result['catalogue_rows']} settings; {result['pairs']} Appendix-B pairs; {result['pair_modes']} pair modes; {result['assets']} fixed assets.\n"
           f"- Exact owner-sheet definitions and Appendix B were parsed and compared with canonical ordering.\n- R1 measurements remain NOT RUN.\n- Next: full pre-measurement checks.\n")
    receipt = publish_files(M.ROOT, rel, "L0084-R1: freeze preregistration and full pair registry", log,
       "docs/journal/2026-10-05-l0084-entry-mix-r1/004-preregistration-frozen.md", tick)
    print(json.dumps({"preregister": "ok", **result, "remote_commit": receipt["commit"]}))
    return 0


def cmd_amend_prereg(args):
    from .transport import GitHubTransport
    from .evidence import commit_evidence
    import hashlib, pathlib
    code_sha=os.environ.get("L0084_R1_CODE_COMMIT")
    if not code_sha:raise RuntimeError("L0084_R1_CODE_COMMIT is required for a preregistration amendment")
    client=GitHubTransport();head=client.branch_head()
    base="history/research/hyp_lab_out/L0084-entry-mix-r1/"
    old=client.blob_from_commit(head,base+"preregistration.json")
    previous=json.loads(old.decode("utf-8"))
    if len(previous.get("settings_52",[]))!=52 or previous.get("pair_sets")!=1326 or previous.get("pair_modes")!=3978:
        raise RuntimeError("previous preregistration does not match pinned grid")
    local=pathlib.Path(M.ROOT)/"tools"/"l0084_entry_mix_r1"
    files=sorted(p for p in local.iterdir() if p.is_file() and (p.suffix==".py" or p.name=="environment.lock"))
    source_hashes={}
    for p in files:
        rel="tools/l0084_entry_mix_r1/"+p.name
        data=p.read_bytes();remote=client.blob_from_commit(code_sha,rel)
        if hashlib.sha256(data).digest()!=hashlib.sha256(remote).digest():
            raise RuntimeError("local source differs from pinned runner commit: "+rel)
        source_hashes[rel]=hashlib.sha256(data).hexdigest()
    amendment={"lane":"L0084-ENTRY-MIX-R1","amendment_utc":__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
      "previous_preregistration_commit":head,"previous_preregistration_sha256":hashlib.sha256(old).hexdigest(),
      "code_commit_before_measurement":code_sha,"code_files_sha256":source_hashes,
      "unchanged":{"assets":previous["universe"]["assets"],"settings_52":previous["settings_52"],
        "pair_sets":1326,"pair_modes":3978,"modes":previous["modes"],"outer_windows":previous["outer_windows"],
        "container":previous["container"],"gates":previous["gates"],"bootstrap":previous["bootstrap"]},
      "reason":"implementation correction only: bounded remote full-trade Parquet streaming, exact readback, resumable index, and full independent rebuild audit; no methods, universe, gates, candidate network, inputs, or outcomes changed.",
      "written_before_any_R1_measurement":True,"results_read":False}
    data=json.dumps(amendment,indent=2,ensure_ascii=False).encode()+b"\n"
    local_out=pathlib.Path(M.O)/"preregistration_amendment.json";local_out.parent.mkdir(parents=True,exist_ok=True);local_out.write_bytes(data)
    receipt=commit_evidence({base+"preregistration_amendment.json":data},
      "L0084-R1: add implementation-only preregistration amendment before outcomes",
      "Amendment pins the complete runner/audit code SHA and explicitly preserves the original methods, parameters, source panels, 52 settings, 3,978 pair modes, and gates. No outcome read.",
      "implementation-only preregistration amendment frozen",
      f"- Original preregistration preserved at `{base}preregistration.json`; SHA256 `{amendment['previous_preregistration_sha256']}`.\n- Runner code commit `{code_sha}`.\n- Measurement remains NOT RUN.\n")
    print(json.dumps({"amendment":"PASS","code_commit":code_sha,"commit":receipt["commit"],"files":len(source_hashes)}))
    return 0


def cmd_check(args):
    from .evidence import commit_evidence
    code_sha=os.environ.get("L0084_R1_CODE_COMMIT","UNSET")
    m=M.Measurer();res=T.run_all(args.phase,m=m);res["code_commit"]=code_sha
    rel="history/research/hyp_lab_out/L0084-entry-mix-r1/checks.json"
    local=os.path.join(M.O,"checks.json")
    with open(local,"w",encoding="utf-8") as fh:json.dump(res,fh,ensure_ascii=False,indent=2)
    status="pre-measurement checks" if args.phase=="pre" else "post-measurement checks"
    nextstep="measurement may start only after all critical checks pass" if args.phase=="pre" else "complete report and delivery only if the full-ledger audit passes"
    receipt=commit_evidence({rel:open(local,"rb").read()},
        f"L0084-R1: {status} for code {code_sha}",
        f"Phase={args.phase}; all_pass={res['all_pass']}; failures={res['failures']}; code_commit={code_sha}.",
        status,
        f"- all_pass={res['all_pass']}; failures={res['failures']}; elapsed={res['elapsed_s']}s.\n- Next: {nextstep}.\n")
    print(json.dumps({"phase":args.phase,"all_pass":res["all_pass"],"failures":res["failures"],"code_commit":code_sha,"remote_commit":receipt["commit"]}))
    return 0 if res["all_pass"] else 2


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


def _read_remote_json(client, commit, path):
    return json.loads(client.blob_from_commit(commit, path).decode("utf-8"))


def _publish_local_file(name, label):
    from .evidence import commit_evidence
    from .transport import GitHubTransport,TransportError
    import hashlib
    rel=f"history/research/hyp_lab_out/L0084-entry-mix-r1/{name}"
    data=open(os.path.join(M.ROOT,rel),"rb").read();client=GitHubTransport();head=client.branch_head()
    try:
        existing=client.blob_from_commit(head,rel)
        if hashlib.sha256(existing).digest()==hashlib.sha256(data).digest():return {"commit":head,"already_committed":True}
        raise TransportError("refusing to overwrite a previously committed stage gate: "+name)
    except TransportError as exc:
        if "path resolution failed" not in str(exc):raise
    return commit_evidence({rel:data},"L0084-R1: publish preregistered stage gate",label,
                           label,"- This record is committed and verified before the next outcome stage.")


def cmd_measure(args):
    if not MEASUREMENT_GATE_READY:
        raise RuntimeError("measurement gate is intentionally closed: full metrics/report writers and independent raw-to-metrics audit remain incomplete")
    from datetime import datetime, timezone
    from .transport import GitHubTransport
    from .streaming import RemoteTradeWriter
    from .evidence import commit_evidence
    code_sha = os.environ.get("L0084_R1_CODE_COMMIT")
    if not code_sha:
        raise RuntimeError("L0084_R1_CODE_COMMIT is required; refusing measurement without pinned code")
    client = GitHubTransport(); head = client.branch_head()
    amendment = _read_remote_json(client, head, "history/research/hyp_lab_out/L0084-entry-mix-r1/preregistration_amendment.json")
    if amendment.get("code_commit_before_measurement") != code_sha:
        raise RuntimeError("preregistration amendment does not pin this runner commit")
    checks = _read_remote_json(client, head, "history/research/hyp_lab_out/L0084-entry-mix-r1/checks.json")
    if checks.get("phase") != "pre" or not checks.get("all_pass") or checks.get("code_commit") != code_sha:
        raise RuntimeError("current-code pre-measurement checks are absent or failing")
    t0=time.time(); now=datetime.now(timezone.utc)
    state_path="history/research/hyp_lab_out/L0084-entry-mix-r1/measurement_run_state.json"
    try:
        state=_read_remote_json(client,head,state_path)
    except Exception as exc:
        if "path resolution failed" not in str(exc):raise
        state=None
    if state is not None:
        if state.get("code_commit")!=code_sha:raise RuntimeError("unfinished measurement belongs to a different code SHA")
        if state.get("status")!="RUNNING":raise RuntimeError("measurement already reached terminal stage; refusing duplicate rerun")
        run_id=state["run_id"];started_utc=state["started_utc"]
    else:
        run_id="r1-"+now.strftime("%Y%m%dT%H%M%SZ");started_utc=now.isoformat()
        state={"run_id":run_id,"code_commit":code_sha,"started_utc":started_utc,"status":"RUNNING","resume_policy":"recompute candidate-window and verify identical committed partitions before continuation"}
        state_receipt=commit_evidence({state_path:json.dumps(state,indent=2).encode()+b"\n"},
            "L0084-R1: establish resumable measurement run state",
            f"Run {run_id} begins only after the current-code preregistration and all prechecks were verified.",
            "measurement run state initialized",
            f"- Run ID: {run_id}; code SHA: `{code_sha}`.\n- No partition is treated as complete without remote readback and index reconciliation.\n")
    os.environ["L0084_R1_RUN_STARTED_UTC"]=started_utc
    writer=RemoteTradeWriter(client,run_id=run_id)
    P.journal("measurement_started",run_id=run_id,code_commit=code_sha,
              preregistration_amendment_sha256=amendment.get("sha256"),
              status="market outcomes begin only after current-code prechecks")
    m=M.Measurer()
    singles=P.stage_singles(m,writer=writer)
    pairs=P.stage_pairs(m,singles,writer=writer)

    # Register every prefix's triple family and commit the frozen registry
    # before measuring any triple outcome.
    all_regs=[]
    for prefix in M.OUTER:
        retained=P.select_retained(pairs,prefix)
        reg=P.register_triples(prefix,retained)
        all_regs.extend(reg)
        P.journal("triples_registered_local",prefix=prefix,n=len(reg),
                  retained={k:[r["cid"] for r in v] for k,v in retained.items()})
    registry_path=os.path.join(M.O,"triples_registry.csv")
    if not os.path.exists(registry_path):
        pd.DataFrame(columns=["prefix_id","triple_id","member_a","member_b","member_c","mode","parent_ids","eligible","reason"]).to_csv(registry_path,index=False)
    reg_receipt=_publish_local_file("triples_registry.csv",f"triple registries committed before outcomes: {len(all_regs)} trials")
    # The above commit is a prerequisite gate; do not enter stage_triples if it fails.
    triples={}
    reg_by_prefix={p:[r for r in all_regs if r["prefix_id"]==p] for p in M.OUTER}
    for prefix in M.OUTER:
        triples[prefix]=P.stage_triples(m,singles,pairs,prefix,reg_by_prefix[prefix],writer=writer)
        P.journal("triples_measured",prefix=prefix,n=len(triples[prefix]),
                  eligible=sum(bool((r.get("gates") or {}).get("eligible")) for r in triples[prefix].values()))

    finalists,_=P.stage_selection(m,singles,pairs,triples)
    sel_rel="history/research/hyp_lab_out/L0084-entry-mix-r1/selection_log.csv"
    sel_receipt=_publish_local_file("selection_log.csv","rolling selection committed before outer target outcomes")
    outer=P.stage_outer(m,finalists,writer=writer)
    controls=P.stage_controls(m,finalists,singles,writer=writer)
    neighbours=P.stage_neighbours(m,finalists,singles,pairs,writer=writer,
        register_hook=lambda fp,label:_publish_local_file("neighbors_registry.csv",label))
    descriptive=P.stage_descriptive(m,singles,pairs,writer=writer)
    frozen=P.stage_freeze(finalists,triples)
    writer_summary=writer.close()
    P.journal("measurement_writer_closed",**writer_summary)
    finished_utc=datetime.now(timezone.utc).isoformat()
    state.update({"status":"MEASUREMENT_STAGES_COMPLETE_AUDIT_PENDING","finished_utc":finished_utc,
                  "trade_rows":writer_summary["rows"],"partition_count":writer_summary["partitions"]})
    run_info={"run_id":run_id,"code_commit":code_sha,"started_utc":started_utc,
        "measurement_finished_utc":finished_utc,
        "partition_rows":writer_summary["rows"],"partition_count":writer_summary["partitions"],
        "peak_pending_bytes":writer_summary["peak_pending_bytes"],
        "peak_pending_rows":writer_summary["peak_pending_rows"],
        "peak_workspace_bytes":writer_summary["peak_workspace_bytes"],
        "peak_rss_bytes":writer_summary["peak_rss_bytes"],
        "memory_limit_bytes":writer_summary["memory_limit_bytes"],
        "memory_limit_source":writer_summary["memory_limit_source"],
        "head_after_partitions":writer_summary["head"],
        "measurement_index_parts":writer_summary["index_parts"],
        "storage_journal_parts":writer_summary["journal_parts"],
        "triple_registry_commit":reg_receipt["commit"],
        "selection_commit":sel_receipt["commit"],
        "outer_windows":len(outer),"controls_rows":len(controls),
        "neighbor_rows":len(neighbours),"frozen":frozen.get("frozen"),
        "status":"MEASUREMENT_STAGES_COMPLETE_AUDIT_PENDING"}
    outroot=os.path.join(M.O)
    run_path=os.path.join(outroot,"measurement_run.json")
    manifest_path=os.path.join(outroot,"evidence_manifest.json")
    state_path_local=os.path.join(outroot,"measurement_run_state.json")
    manifest={"run_id":run_id,"code_commit":code_sha,"status":"RAW_PARTITIONS_COMMITTED_AUDIT_PENDING",
      "trade_schema_version":"l0084-r1-trade-v1","trade_schema_fields":["candidate_id","role","window","asset","signal_bar","fill_bar","exit_bar","signal_time_utc","fill_time_utc","exit_time_utc","entry","exit","atr","quantity","notional","outcome","gap_flag","double_touch","holding_bars","gross_dollars","cost_dollars","net_dollars","gross_atr_r","cost_atr","net_atr_r","barrier_r","mae_atr_r","mfe_atr_r","seg"],
      "trade_partition_count":writer_summary["partitions"],"trade_rows":writer_summary["rows"],
      "max_partition_bytes":8000000,"peak_pending_bytes":writer_summary["peak_pending_bytes"],
      "peak_workspace_bytes":writer_summary["peak_workspace_bytes"],"peak_rss_bytes":writer_summary["peak_rss_bytes"],
      "memory_limit_bytes":writer_summary["memory_limit_bytes"],"memory_limit_source":writer_summary["memory_limit_source"],
      "measurement_index_parts":writer_summary["index_parts"],"storage_journal_parts":writer_summary["journal_parts"],
      "input_panels_manifest":"input_panels_manifest.json","audit_status":"NOT RUN"}
    for path,obj in ((run_path,run_info),(manifest_path,manifest),(state_path_local,state)):
        with open(path,"w",encoding="utf-8") as fh:json.dump(obj,fh,indent=2,ensure_ascii=False)
    relbase="history/research/hyp_lab_out/L0084-entry-mix-r1/"
    payloads={relbase+name:open(path,"rb").read() for name,path in (("measurement_run.json",run_path),("evidence_manifest.json",manifest_path),("measurement_run_state.json",state_path_local))}
    final_receipt=commit_evidence(payloads,
        "L0084-R1: close market measurement stages and record remote partition manifest",
        f"Measurement stages completed for run {run_id}; full independent audit is still pending. No verdict/adoption is asserted.",
        "measurement stages closed; audit pending",
        f"- Candidate rows: {writer_summary['rows']}; Parquet partitions: {writer_summary['partitions']}.\n- Audit not yet complete; no final delivery status is asserted.\n")
    print(json.dumps({"measurement":"stages complete; audit pending","run_id":run_id,
        "rows":writer_summary["rows"],"partitions":writer_summary["partitions"],
        "branch_head":final_receipt["head"]},indent=2))
    return 0


# ==========================================================================
def cmd_summarize(args):
    raise RuntimeError("summary publishing is blocked until the complete remote metrics/controls partition reader and independent raw-ledger reconciliation are implemented; the legacy local-key summarizer is intentionally not used")


def cmd_audit(args):
    from .transport import GitHubTransport,TransportError
    from .audit import rebuild_all
    from .evidence import commit_evidence
    if not args.rebuild_all:
        raise RuntimeError("Only `audit --rebuild-all` is accepted; sample-only audit is not a full audit.")
    client=GitHubTransport();head=client.branch_head();base="history/research/hyp_lab_out/L0084-entry-mix-r1/"
    try:
        run=_read_remote_json(client,head,base+"measurement_run.json")
        if run.get("status") not in ("MEASUREMENT_STAGES_COMPLETE_AUDIT_PENDING","RUNNING"):
            raise TransportError("measurement run is not in an auditable state")
        m=M.Measurer();res=rebuild_all(client,head,run["run_id"],m)
        if res.get("metrics_reconciliation")!="PASS":
            raise TransportError("full raw-trade rebuild passed, but independent metrics/table reconciliation is not implemented or did not pass")
        obj={"status":"PASS","fixed_head":head,"run_id":run["run_id"],"code_commit":run["code_commit"],**res}
        code=0
    except Exception as exc:
        obj={"status":"FAIL","fixed_head":head,"error_type":type(exc).__name__,"error":str(exc)[:1000],"full_rebuild":True}
        code=2
    path=os.path.join(M.O,"audit.json");os.makedirs(M.O,exist_ok=True)
    with open(path,"w",encoding="utf-8") as fh:json.dump(obj,fh,indent=2,ensure_ascii=False)
    rel=base+"audit.json"
    receipt=commit_evidence({rel:open(path,"rb").read()},
        "L0084-R1: full remote ledger rebuild audit", 
        f"Full audit status={obj['status']}; fixed head={head}; run_id={obj.get('run_id','unknown')}; independent rebuild was requested for all indexed rows.",
        "full remote ledger audit "+obj["status"],
        f"- Status: {obj['status']}; fixed audit head: `{head}`.\n- Full rebuild flag was required; audit failures return nonzero.\n")
    print(json.dumps({**obj,"audit_commit":receipt["commit"]},indent=2))
    return code


def cmd_future_plan(args):
    from . import report
    report.future_plan()
    print("future-plan: ok")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="l0084_entry_mix")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("preregister")
    sub.add_parser("amend-prereg")

    c = sub.add_parser("check")
    c.add_argument("--phase", choices=["pre", "post"], default="pre")

    sub.add_parser("measure")

    sub.add_parser("summarize")

    au = sub.add_parser("audit")
    au.add_argument("--rebuild-sample", type=int, default=400)
    au.add_argument("--rebuild-all", action="store_true")

    sub.add_parser("future-plan")

    args = ap.parse_args(argv)
    fn = {"preregister": cmd_preregister, "amend-prereg":cmd_amend_prereg,
          "check": cmd_check, "measure": cmd_measure, "summarize": cmd_summarize,
          "audit": cmd_audit, "future-plan": cmd_future_plan}[args.cmd]
    return fn(args) or 0


if __name__ == "__main__":
    sys.exit(main())
