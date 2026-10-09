# Synthetic package preparation report

Status: PASS

This is a deterministic synthetic fixture run only. No market data was downloaded, transformed, or evaluated; no performance claim is made. August validation was not run.

- Runtime: 3.13.16 (main, Oct  6 2026, 04:38:44) [GCC 14.2.0] (/usr/local/bin/python3)
- Run ID: singleton-package-fixture-r3
- Settings: 226; candidate cells: 2034; candidate summary rows: 4068; control rows: 36; total rows: 4104
- Zero-result rows preserved: 1410
- Independent indicator checks: 21
- Minute barrier checks: 83
- Causal prefix positions: 60; candidate mask comparisons: 13560
- Independent raw summary rebuild: PASS
- Elapsed seconds to report: 740.000
- Whole workspace bytes (measured): 37336692

## Scope notes

- Three assets: BTC, ETH, SOL; three fixed exclusive labels: BREAKOUT, PULLBACK, TURN. PULLBACK uses EMA context and TURN uses RSI; classifier overlap with those families is disclosed.
- 226 single-indicator settings are evaluated across 2,034 asset/state candidates and two synthetic outcome horizons.
- Complete grid retained: 4,068 candidate rows plus 36 controls = 4,104. A zero-alert row remains present with null precision/Wilson values where n=0.
- All fixture alerts and outcomes are synthetic. The exercise validates plumbing and declared calculations only; it does not estimate market performance, significance, or future returns.
- Data sourcing is not exercised. The market-source contract is metadata only; no local/remote market file was opened.

Generated at 2026-10-08T19:51:29Z UTC.

## Delivery status

Synthetic acceptance passed. The R2 Python 3.12 blocker is superseded by the R3 CPython 3.13.x permission; CPython 3.13.16 was verified and used. Remote publication is **BLOCKED** by the publisher’s payload-scan self-match: the scanner treats its own literal token-prefix guard (`ghp_` / `github_pat_`) as a credential. No remote API write was issued. No `PACKAGE_READY_LEAD_REVIEW_PENDING` status is claimed.

## Publication blocker

The real publication preflight stopped before any remote write. Exact secret comparison did not find the private credential, but the subsequent generic token-prefix heuristic falsely matched the publisher source itself. The in-memory draft archive was 1,240,865 bytes (SHA-256 2fb83e7588691fa11b14c264406b8a7c505c8d06308d3d26420b33442f510add), but is not final: it omitted explicit checkpoint/resume/tamper evidence entries. Two read-only API GETs were made; zero writes, no branch-head check, no ref change, and no immutable readback. Status remains BLOCKED_BEFORE_REMOTE_WRITE, not PACKAGE_READY_LEAD_REVIEW_PENDING.
