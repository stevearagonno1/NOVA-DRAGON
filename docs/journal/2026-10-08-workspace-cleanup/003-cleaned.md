# Workspace cleanup report — 2026-10-08

**Status:** `CLEANUP_COMPLETE`. No experiment was run; `experiment_run=false`.

- Workspace root: `/home/user`. Fresh before: **171552512 bytes**; after: **33900182 bytes**. Required ceiling: 112,000,000 bytes.
- Authorized roots: `3`; recorded file paths: 418; unique content groups: 403; preserved backup parts: 44.
- Deleted files: 418; deleted bytes: 137652330; off-scope deletions: 0.
- Existing remote copies were Git-blob verified at pinned commits; remaining files were chunked, compressed in memory, and byte-read back before deletion.
- Root results: `[{"bytes_deleted": 67588993, "directories_removed": 142, "exceptions": [], "files_deleted": 304, "files_expected": 304, "remaining_bytes": 0, "root": "/home/user/l0084-package", "status": "DELETED", "workspace_after_bytes": 103963519}, {"bytes_deleted": 57579570, "directories_removed": 9, "exceptions": [], "files_deleted": 45, "files_expected": 45, "remaining_bytes": 0, "root": "/home/user/singleton-package-fixture-v1", "status": "DELETED", "workspace_after_bytes": 46383949}, {"bytes_deleted": 12483767, "directories_removed": 5, "exceptions": [], "files_deleted": 69, "files_expected": 69, "remaining_bytes": 0, "root": "/home/user/nova-l0094-workspace", "status": "DELETED", "workspace_after_bytes": 33900182}]`. Exceptions: `[]`.
- Local `.git` and credential files: no credential-named files were found; the L0084 local Git object content scan found zero credential-pattern hits; its `.git` content was preserved as regular parts before authorized deletion.
- The earlier space report was 171,538,117 bytes; the fresh pre-delete measurement was 171552512 bytes (difference 14395 bytes). The fresh measurement governs.
- Elapsed seconds from phase-2 preservation verification to final local measurement: 39.489; task-start timestamp was not instrumented, so full-task elapsed is left null rather than estimated.

No R2 package was started, and no main, PR, or merge was changed.
