# Durable supervision recovery

- Decision: repair missing logs and premature handoff after process loss.
- Work: wrapper only; unchanged source 74bc4cba32c083f34b6588b685f93216aaa580c9 and stage1-singletons-v1.
- Checks: actual SIGKILL, surviving-child lock, unknown-exit restart, output/secret handling and full synthetic CLI.
- Required agent behaviour: keep observing the active tool handle until verified delivery or a concrete obstacle; never claim background persistence without evidence. Missing exit status alone is not a restart ban.
- Destination: measurement stays on agent/l0084-stage1-checked-2026-10-05; tooling published separately to avoid disturbing a surviving publisher.
