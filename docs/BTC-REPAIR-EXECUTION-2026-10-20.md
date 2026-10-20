# Repaired BTC execution route — 2026-10-20

Read the complete constitution in root README.md first. Until the owner merges, use README.md at the delivered repair branch; main still has the prior state. This document supersedes the old local-input bootstrap and cd161f8 execution route. The approved research scope is unchanged: 548 records, seven months, descriptive conditional-state study. This repair does not itself authorize a new market run or establish signal quality.

## Verified source

- Repaired executable source: `10d70f119f19f08b81c6f324495840290743372d`.
- Bootstrap: `tools/btc_state_specialist/private_transport/bootstrap_from_md.py`.
- Bootstrap SHA256: `0cf76cef33d5124c4b39037a2b74eb7ec9fad860ee20295fbb5f6595c95253f0`.
- Exact package files and hashes: `tools/btc_state_specialist/package_manifest.json` at that source.
- Evidence: `tools/btc_state_specialist/REPAIR_VERIFICATION.json`; historical readiness files are not new market completion.
- Result branch: `agent/btc-state-specialist-results-r2-2026-10-20`. New output root: `history/research/hyp_lab_out/BTC-STATE-SPECIALIST-R2-2026-10-20/`.

## Environment admission

Use a genuinely fresh execution environment if the previous whole workspace is already195MB. Preserve its EXECUTION-BLOCKED.md, stage_download.log and all owner files. Do not delete, relocate them or point accounting at a smaller subfolder. This repair cannot clean or inspect that other host.

NOVA_WORKSPACE must already identify the actual complete workspace root, and the command below must run from that root. Python3.12, numpy2.3.5 and pandas2.2.3 must already be available. No blind pip install or full clone. Public code/data reading needs no publishing credential. Only final publication needs GH_TOKEN in the executor's private environment; never place its value in repository files or command output.

## Bootstrap without a saved downloader or price archive

This command checks the entire workspace and runtime before its first network request. It verifies the downloaded bootstrap in memory, then fetches only the lightweight manifest-listed package. It creates no local price archive.

```bash
export PYTHONDONTWRITEBYTECODE=1
python - <<'NOVA_BOOTSTRAP'
import hashlib, os, sys, urllib.request
from pathlib import Path
root = Path(os.environ['NOVA_WORKSPACE']).resolve(strict=True)
if Path.cwd().resolve() != root:
    raise RuntimeError('Run from the actual complete workspace root; do not narrow accounting')
used = sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and not p.is_symlink())
if used > 125000000:
    raise RuntimeError(f'125 MB workspace limit before bootstrap: {used}; preserve evidence and use a genuinely fresh environment')
if sys.version_info[:2] != (3,12):
    raise RuntimeError('Python3.12 required')
import numpy, pandas
assert (numpy.__version__, pandas.__version__) == ('2.3.5','2.2.3'), 'provision the pinned runtime before execution'
ref = '10d70f119f19f08b81c6f324495840290743372d'
url = 'https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/'+ref+'/tools/btc_state_specialist/private_transport/bootstrap_from_md.py'
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args): raise RuntimeError('redirect refused')
with urllib.request.build_opener(NoRedirect()).open(url,timeout=60) as response:
    source = response.read(16385)
assert len(source) <= 16384
assert hashlib.sha256(source).hexdigest() == '0cf76cef33d5124c4b39037a2b74eb7ec9fad860ee20295fbb5f6595c95253f0'
sys.argv = ['bootstrap','--ref',ref,'--out','btc-specialist']
exec(compile(source,'verified-bootstrap','exec'),{'__name__':'__main__'})
NOVA_BOOTSTRAP
```

Then follow §18 of the downloaded btc-specialist/paper.md. Its code_commit comes from source_release.json. Do not reuse an old package checkpoint: code changes intentionally invalidate it. Once the package is frozen, restart the identical command in the identical output directory; completed parts are reused after verification.

Remote price reads transfer one bounded compressed file into memory at a time, verify its length and SHA256 and release it after use. They do not save price files. Reports and raw **signal evidence** are necessary compact outputs, not duplicate price archives.

## Failure reporting

Keep the actual error and attempted command. An oversized workspace can also prevent writing a local error report; in that case preserve stdout/stderr in the executor host's existing log rather than claiming a file was saved. A local or synthetic pass is not complete market delivery. No PR, agent merge, main push, original-data mutation or live trade is permitted.
