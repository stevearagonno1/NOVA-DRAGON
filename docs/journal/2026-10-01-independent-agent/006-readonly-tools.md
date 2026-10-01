# Scoped automatic repository reads

Owner requested fewer repeated shell approval prompts in Telegram.
Added four fixed-repository GET-only dynamic tools for fresh main status,
commit history, supported text listing, and file reads with pinned provenance.
Ordinary bash and state-changing tools retain approval. No provider or paid
service changes. Main is unchanged; deployment code remains on agent branch.

Validation: 15 Python tests pass, including credential/path restrictions,
size/binary limits, immutable provenance, secret redaction and redirect rejection.
OpenCrabs v0.5.4 dynamic executor source supports requires_approval=false and
OPENCRABS_PARAMS JSON transfer. Render/Telegram runtime test remains pending.
