"""R1 append-only branch evidence commits and collision-free journal ticks."""
from __future__ import annotations
import datetime
import hashlib
import json
import re
import zoneinfo
from pathlib import Path

from .transport import GitHubTransport, TransportError

JOURNAL_DIR = "docs/journal/2026-10-05-l0084-entry-mix-r1"
OUTPUT_PREFIX = "history/research/hyp_lab_out/L0084-entry-mix-r1/"


def next_tick(client: GitHubTransport, commit_sha: str | None = None) -> int:
    head = commit_sha or client.branch_head()
    names = client.list_directory(head, JOURNAL_DIR)
    nums = [int(m.group(1)) for name in names
            if (m := re.match(r"^(\d{3})-[^/]+\.md$", name))]
    return max(nums, default=0) + 1


def commit_evidence(files: dict[str, bytes], message: str, log_summary: str,
                    tick_title: str, tick_details: str,
                    client: GitHubTransport | None = None,
                    max_batch_bytes: int = 7_000_000) -> dict:
    client = client or GitHubTransport()
    parent = client.branch_head()
    tick_no = next_tick(client, parent)
    now = datetime.datetime.now(datetime.timezone.utc)
    aden = now.astimezone(zoneinfo.ZoneInfo("Asia/Aden"))
    tick_path = f"{JOURNAL_DIR}/{tick_no:03d}-{re.sub('[^a-z0-9-]+','-',tick_title.lower()).strip('-')}.md"
    payloads = dict(files)
    total = 0
    for path, data in payloads.items():
        if not path.startswith(OUTPUT_PREFIX) or path.startswith("/") or ".." in path.split("/"):
            raise ValueError("evidence path outside authorized R1 output")
        if not isinstance(data, bytes): raise TypeError("evidence files must be bytes")
        if len(data) > 8_000_000: raise TransportError(f"single evidence file exceeds 8MB: {path}")
        total += len(data)
    if total > max_batch_bytes: raise TransportError("evidence batch exceeds bounded memory size")
    old_log = client.blob_from_commit(parent, "LOG.md")
    log = (f"\n\n### {tick_title} ({now:%Y-%m-%dT%H:%M:%SZ})\n\n"
           f"{log_summary.rstrip()}\n")
    tick = (f"# L0084-R1 tick {tick_no:03d} — {tick_title}\n\n"
            f"- UTC: {now:%Y-%m-%dT%H:%M:%SZ}\n"
            f"- Asia/Aden: {aden:%Y-%m-%dT%H:%M:%S%:z}\n"
            f"{tick_details.rstrip()}\n")
    payloads["LOG.md"] = old_log + log.encode("utf-8")
    payloads[tick_path] = tick.encode("utf-8")
    commit, receipts = client.commit_files(payloads, parent, message)
    for path, expected in payloads.items():
        actual = client.blob_from_commit(commit, path)
        if len(actual) != len(expected) or hashlib.sha256(actual).digest() != hashlib.sha256(expected).digest():
            raise TransportError("committed evidence failed readback verification: " + path)
    if client.branch_head() != commit:
        raise TransportError("R1 branch head differs from evidence commit")
    return {"parent": parent, "commit": commit, "head": client.branch_head(),
            "tick_number": tick_no, "tick_path": tick_path,
            "files": [{"path": p, "bytes": len(b),
                       "sha256": hashlib.sha256(b).hexdigest(),
                       "git_blob_sha": next(r.blob_sha for r in receipts if r.path == p)}
                      for p,b in payloads.items()]}


def read_local_files(root: str, paths: list[str], limit: int = 7_000_000) -> dict[str, bytes]:
    base = Path(root).resolve(); out = {}; total = 0
    for rel in paths:
        p = Path(rel)
        if p.is_absolute() or ".." in p.parts: raise ValueError("unsafe path")
        full = (base/p).resolve()
        if base not in full.parents: raise ValueError("path escaped R1 root")
        data = full.read_bytes()
        total += len(data)
        if len(data) > 8_000_000 or total > limit:
            raise TransportError("local evidence batch exceeds bounded limit")
        out[rel] = data
    return out
