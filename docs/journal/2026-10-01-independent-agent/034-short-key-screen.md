# Short key screening (owner requested, 2026-10-09)

`nova_council_atlas` scope=mini performs one fresh synthetic request on slots 4,
5 and 7, sequentially: cost arithmetic, three code defects and three evidence
judgments. Same prompt/settings, 8192 generation tokens and 600 seconds per
request, no retries/fallback/tools, at most 24576 generation tokens plus input.
Provider-default reasoning is retained; truncated replies remain ungraded.

Local deterministic grader: 40 arithmetic + 30 defects + 30 decisions; strict
JSON shape/types and duplicate-key rejection. Only complete valid replies rank,
correctness first, elapsed time only as a tie breaker. One sample is screening,
not a definitive intelligence ranking or evidence that credentials themselves
change model capability. No automatic role/config changes. Owner receives JSON
with raw visible answers, reported model, duration, usage and score.

Validated with rational arithmetic and 142 local tests, no paid API requests.
Use scope=mini explicitly; existing full ATLAS pilot/all remain unchanged.
