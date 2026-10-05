"""Memory-only GitHub Git database transport for R1 evidence partitions.

Never writes payloads or credentials to disk. Requires GH_TOKEN in the process
environment. Each update is a single-parent, compare-before-update commit.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

API = "https://api.github.com/repos/stevearagonno1/NOVA-DRAGON"
BRANCH = "arena/l0084-entry-mix-r1-2026-10-05"


class TransportError(RuntimeError):
    pass


class HeadConflict(TransportError):
    pass


@dataclass(frozen=True)
class BlobReceipt:
    path: str
    blob_sha: str
    content_sha256: str
    size_bytes: int
    commit_sha: str


def verify_bytes(content: bytes, expected_sha256: str, expected_size: int) -> None:
    if len(content) != expected_size:
        raise TransportError("byte-count mismatch")
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        raise TransportError("SHA256 mismatch")


class GitHubTransport:
    def __init__(self, token: str | None = None,
                 opener: Callable[..., Any] | None = None):
        self._token = token if token is not None else os.environ.get("GH_TOKEN")
        if not self._token:
            raise TransportError("GH_TOKEN unavailable")
        self._open = opener or urllib.request.urlopen

    def _request(self, path: str, method: str = "GET",
                 payload: dict | None = None) -> tuple[int, dict]:
        body = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(
            API + path,
            data=body,
            method=method,
            headers={
                "Authorization": "Bearer " + self._token,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                "User-Agent": "L0084-R1-evidence-transport",
            },
        )
        try:
            with self._open(req, timeout=30) as response:
                raw = response.read()
                status = response.status
        except urllib.error.HTTPError as exc:
            raw, status = exc.read(), exc.code
        except Exception as exc:
            raise TransportError(f"network failure: {type(exc).__name__}") from None
        try:
            obj = json.loads(raw.decode()) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            obj = {}
        if status < 200 or status >= 300:
            # Avoid echoing request headers, payloads, or credentials.
            msg = obj.get("message", "HTTP error") if isinstance(obj, dict) else "HTTP error"
            raise TransportError(f"GitHub API HTTP {status}: {msg}")
        return status, obj

    def branch_head(self) -> str:
        path = "/git/ref/heads/" + urllib.parse.quote(BRANCH, safe="/")
        return self._request(path)[1]["object"]["sha"]

    def commit_files(self, files: dict[str, bytes], expected_head: str,
                     message: str) -> tuple[str, list[BlobReceipt]]:
        """Commit small byte buffers without local git objects or temp files."""
        if not files:
            raise ValueError("empty commit")
        if self.branch_head() != expected_head:
            raise HeadConflict("branch head changed before write")
        _, parent = self._request("/git/commits/" + expected_head)
        base_tree = parent["tree"]["sha"]
        tree_entries, pending = [], []
        for path, content in files.items():
            if path.startswith("/") or ".." in path.split("/"):
                raise ValueError("unsafe repository path")
            if not isinstance(content, bytes):
                raise TypeError("file content must be bytes")
            _, blob = self._request("/git/blobs", "POST", {
                "content": base64.b64encode(content).decode("ascii"),
                "encoding": "base64",
            })
            tree_entries.append({"path": path, "mode": "100644",
                                 "type": "blob", "sha": blob["sha"]})
            pending.append((path, content, blob["sha"]))
        _, tree = self._request("/git/trees", "POST", {
            "base_tree": base_tree, "tree": tree_entries,
        })
        _, commit = self._request("/git/commits", "POST", {
            "message": message, "tree": tree["sha"], "parents": [expected_head],
        })
        new_sha = commit["sha"]
        if self.branch_head() != expected_head:
            raise HeadConflict("branch head changed while preparing commit")
        ref_path = "/git/refs/heads/" + urllib.parse.quote(BRANCH, safe="/")
        self._request(ref_path, "PATCH", {"sha": new_sha, "force": False})
        if self.branch_head() != new_sha:
            raise HeadConflict("branch head did not advance to created commit")
        receipts = [BlobReceipt(p, bsha, hashlib.sha256(buf).hexdigest(),
                                len(buf), new_sha)
                    for p, buf, bsha in pending]
        return new_sha, receipts

    def blob_from_commit(self, commit_sha: str, path: str) -> bytes:
        """Resolve a path from the commit tree and read its Git blob in memory."""
        _, commit = self._request("/git/commits/" + commit_sha)
        tree_sha = commit["tree"]["sha"]
        parts = path.split("/")
        for i, part in enumerate(parts):
            _, tree = self._request("/git/trees/" + tree_sha)
            matches = [x for x in tree.get("tree", []) if x.get("path") == part]
            if len(matches) != 1:
                raise TransportError(f"path resolution failed at {part}")
            entry = matches[0]
            if i < len(parts) - 1:
                if entry.get("type") != "tree":
                    raise TransportError("intermediate path is not a tree")
                tree_sha = entry["sha"]
            else:
                if entry.get("type") != "blob":
                    raise TransportError("path is not a blob")
                _, blob = self._request("/git/blobs/" + entry["sha"])
                return base64.b64decode(blob["content"])
        raise TransportError("empty path")
