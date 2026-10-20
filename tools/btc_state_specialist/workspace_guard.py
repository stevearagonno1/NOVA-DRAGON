"""Whole-workspace budget. Never cleans, relocates or hides existing files."""
import os
from pathlib import Path
LIMIT = 125000000

def workspace_root():
    value = os.environ.get('NOVA_WORKSPACE')
    if not value:
        raise RuntimeError('NOVA_WORKSPACE must name the actual complete workspace root')
    root = Path(value).resolve(strict=True)
    if not root.is_dir():
        raise RuntimeError('workspace root is not a directory')
    return root

def workspace_bytes(root):
    return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file() and not p.is_symlink())

def preflight(extra_bytes=0, target=None):
    root = workspace_root()
    if target is not None and not Path(target).resolve().is_relative_to(root):
        raise RuntimeError('write target is outside the declared whole workspace')
    used = workspace_bytes(root)
    if used + extra_bytes > LIMIT:
        raise RuntimeError(f'125 MB workspace limit: existing={used}, requested={extra_bytes}; use a genuinely clean execution workspace; no automatic deletion or narrower accounting root')
    return used
