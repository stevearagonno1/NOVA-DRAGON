# Workspace workflow — current owner ruling 2026-10-20

Read the complete root README.md constitution first. This workflow implements §17.

- Check the actual complete workspace against 125000000 bytes before any setup write, dependency install or input request. Do not silently narrow NOVA_WORKSPACE.
- Keep only necessary lightweight code/configuration and compact reproducible evidence locally.
- Read pinned, hash-verified price inputs one at a time in memory. No local price copies, full repository clone, archive extraction or duplicate package is needed.
- If the inherited workspace is already oversized, preserve its evidence and use a genuinely fresh execution environment. A subfolder of that same oversized workspace is not a fresh environment.
- Never delete owner files, original data, historical evidence or tests to pass a budget check.
- Publish authorized work only on a work branch; verify immutable remote files. No PR, merge or main push.
- Synthetic checks prove execution behavior only. Market measurement remains a separate explicitly authorized stage.
