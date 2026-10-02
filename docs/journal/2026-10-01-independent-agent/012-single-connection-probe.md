# Isolate one real provider connection from full review

Decided: actual local diagnostics found ten unique credentials and valid endpoint/model configuration, but did not test provider acceptance. Do not repeat all five collective calls to isolate a connection problem.
Executed: added nova_council_probe: one small streaming request with only the first configured credential, no fallback and no repository sources. It shares the bounded background queue and reports completion or the safe failure reason to the owner.
Produced: forty-six local tests pass. Probe tests assert one request, a 512-token cap, no source reads, no credential disclosure, and no claim that the remaining nine credentials or full council were verified.
Next: deploy this work branch and run nova_council_probe once. Its actual provider result determines whether to investigate transport or larger review input/output.
