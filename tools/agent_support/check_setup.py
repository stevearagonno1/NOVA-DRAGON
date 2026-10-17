"""Offline integrity check for the repository agent-support files; no trading imports."""
from pathlib import Path
import hashlib
import json

def check(root):
    root = Path(root)
    manifest = json.loads((root / ".agents/UPSTREAM.json").read_text(encoding="utf-8"))
    if len(manifest["commit"]) != 40:
        raise ValueError("upstream commit must be pinned")
    for entry in manifest["files"]:
        path = root / entry["path"]
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != entry["sha256"]:
            raise ValueError("upstream integrity mismatch: " + entry["path"])
    for name in ("code-review-and-quality", "test-driven-development"):
        body = (root / ".agents/skills" / name / "SKILL.md").read_text(encoding="utf-8")
        if not body.startswith("---\n") or "\nname: " + name + "\n" not in body or "\ndescription: " not in body:
            raise ValueError("invalid skill metadata: " + name)
    for name in ("security-checklist.md", "performance-checklist.md"):
        if not (root / ".agents/references" / name).is_file():
            raise ValueError("missing shared reference: " + name)
    config = json.loads((root / "tools/agent_support/context7.mcp.example.json").read_text(encoding="utf-8"))
    if config != {"mcpServers": {"context7": {"type": "http", "url": "https://mcp.context7.com/mcp"}}}:
        raise ValueError("unexpected Context7 example; review transport or credential changes")
    print("PASS: imported skills, hashes, shared references and Context7 example")
    print("Host discovery, MCP connection, optional tool runtimes and market outcomes: NOT TESTED")

if __name__ == "__main__":
    check(Path(__file__).resolve().parents[2])

