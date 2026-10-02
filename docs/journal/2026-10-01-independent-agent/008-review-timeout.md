# Correct background timeout and task state

Decided: the Telegram test proves a background job started but was blocked by TimeoutError; no collective recommendation was produced. The failing phase is not known from the old error message.
Executed: raised the council HTTP read timeout from 120 to 360 seconds to permit gateway retry latency; added source/reviewer/cross-review/synthesis phases and completed-request counts, with safe HTTP error codes.
Produced: coordinator instructions now prohibit config inspection for council setup and require a prompt acknowledgment, with a status check before any delayed claim that work still runs. Local regression tests cover timeout configuration, phase tracking and blocked status.
Next: deploy the work branch, test a small review, and inspect its exact phase if it stops. Real provider behavior after this change remains unmeasured; no model or account settings were changed.
