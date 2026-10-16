# استئناف القراءة الدلالية الشاملة — لم تُنجز بعد

طلب المالك: إدخال كل محتوى المستودع وربطه بدقة وفحص العلاقات والعناصر المعزولة. لا تُبدّل هذا الطلب بفهرسة الكلمات ثم تسمّيها فهمًا دلاليًا شاملًا.

## Proven versus pending

The pinned manifest is SOURCE-TREE.json. The executable ingestion handles repository files and archive members, preserves explicit conversion failures, and creates exact text segments. link_evidence.py produces conservative term mentions, explicit references, Pine declarations and preserved prior AST edges. That evidence graph is useful, but it does not complete semantic reading. No zero-failure or full-semantic claim is authorized by its existence.

## Reproduce source preparation

Use an isolated working directory and Python 3.12. Install PyMuPDF, numpy, libarchive-c 5.3 and pyarrow 26.0.0. libarchive-c needs the system libarchive library. For optional prior code graph linkage, recover the prior Graphify output and SOURCE-FILES.json from research/graphify-nova-2026-10-16 at the pinned commit. The current scripts expect their sibling folder graphify_integration_2026_10_16; this local-layout assumption must be retained explicitly, not guessed. The full workspace size must be measured; the old workspace already exceeded 125 MB, so no budget PASS is claimed.

Run semantic_pipeline.py ingest to fetch hash-verified source blobs with restart checkpoints. ingest_bulk.py is an alternative transport using a single pinned GitHub archive in RAM; it performs the same per-file Git identity checks. Never run both writers concurrently. It requires substantial RAM (the observed compressed repository archive is about 823 MB). Do not delete existing original files to meet a budget.

A source classified DATA_SCHEMA is numeric-data metadata, not a language review. Non-market CSV and SQLite tables retain textual contents in converter version 2. SQLite generated views remain symbolic definitions; do not expand millions of variants into millions of graph nodes or silently reduce them to the 134-setting prototype.

## Mandatory semantic reading

Read every complete segment in execution/batches/*.json. Segmentation is an internal checkpoint, not a reduced scope or a new owner task. The status of every segment must be accounted for. A duplicate source may reuse semantic work only after byte/text identity is verified and every source path remains traceable. Never mark a file read from its filename, keywords, a summary, or an excerpt alone.

Write execution/fragments/*.json with exactly these top-level arrays: reviews, nodes, edges.

Each review has segment_id, read_complete (true only after full reading), summary, and no_relationship_reason when no relationship is extracted. Each node has a stable path-scoped id, label, file_type, and source_file. Keep different implementations and different settings separate. Do not merge on a shared display name.

Each edge has source, target, relation, confidence, confidence_score, source_file, segment_id, and evidence_quote copied verbatim from that segment. INFERRED or AMBIGUOUS also requires rationale. EXTRACTED is 1.0; this is an evidence label, not a probability that a trading claim is true. For cross-file inferences retain evidence from both sources in a supplemental evidence list and independently verify both.

Read for: indicator → equation → source implementation → inputs/defaults/ranges → independent variant generator; confirmation → trigger and direction; dataset → asset/span/timeframe/provenance → experiment → raw result → review → decision; constitution → current authority versus historical/draft proposals. Record contradiction and supersession only when the text supports the direction. A historical paper that suggests a rule is not proof that the code implements it or that the rule works.

Distinguish mentions, defines, implements, configures, tests, supports, contradicts, supersedes, depends_on and cites. A bare mention is not a causal relationship, adoption, or buy signal. Never infer profitable behavior from indicator popularity. Never execute trading code to understand it.

## Review conversion limitations

Inspect every unresolved entry and preserve its original bytes/hash. Several deliberately invalid compressed files live inside synthetic test fixtures. They may be modeled as invalid fixtures only after reading the test that constructs/uses them; do not repair original evidence. Compiled executables have only binary metadata until independently inspected; do not claim their internal implementation was read. Images or unreadable pages require visual reading; OCR absence is not an empty document.

## Audit and delivery

Run semantic_pipeline.py audit after fragments exist. An empty fragment set must fail. Missing sources, missing segment reviews, conflicting identities, dangling endpoints, unsupported evidence quotations and unreviewed conversions prevent full completion. Then independently inspect relationship direction, version identity, negation, authority, contradiction and cross-file evidence. Structural correctness alone cannot certify semantic correctness.

Do not add artificial links simply to reduce isolated nodes. Report isolated files separately from files merely linked by containment, duplicates, or generic terms. Preserve both earlier and revised claims with provenance; do not rewrite history.

Merge audited semantic fragments with the original Graphify structural graph, retaining source pins and original confidence labels. Regenerate the visualization and a reconciliation table: requested sources, fetched sources, decoded sources, fully reviewed sources, accepted relations, ambiguous relations and remaining limitations. Publish only to agent/graphify-nova-2026-10-16, with expected-head protection, an append-only Tape entry, LOG and handoff update, followed by immutable byte readback. No main write, PR, merge, live trade or public credential.

A final “complete” is allowed only after this actual reading, independent relation review and verified delivery. Until then report the status as partial.
