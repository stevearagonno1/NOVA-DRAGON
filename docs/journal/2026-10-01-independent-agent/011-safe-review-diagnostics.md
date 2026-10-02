# Safe configuration diagnostics after ValueError

Decided: streaming trial submitted correctly but stopped at independent review with ValueError and zero completed requests. The generic exception name is insufficient to identify its cause; no speculative provider/key changes.
Executed: added nova_council_diagnostics for local endpoint/model validation and unique credential count, with zero upstream requests. Added safe enumerated failure reasons, credential slot numbers, and exception source location without exception bodies, keys or locals. Trim outer credential whitespace; reject internal whitespace/control/non-ASCII characters with a safe slot-specific error.
Produced: regression tests ensure diagnostic output cannot disclose keys, does not claim provider acceptance, and never forwards arbitrary exception/header text.
Next: deploy this branch and run local diagnostics first. Successful live collective output and acceptance of all credentials remain unmeasured.
