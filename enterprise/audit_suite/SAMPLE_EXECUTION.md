# Explicit sampled-item procedure trace

`sample_execution.handle(state, kind, payload, stamped, artifacts)` is a reducer helper for `sample.execution.record` and `sample.execution.correct`. The Engine must invoke it only inside the existing Store transaction with current `learn` or `instruct` membership, command ID and exact expected engagement revision. It is not an independently authenticated API. Store provides exact replay and atomic persistence. No model is involved.

The exact record payload contains:

- `task_id`, `task_digest`: exact current scoped procedure record and `store.digest(task)`.
- `selection_id`, `selection_digest`, `population_id`, `population_digest`: immutable dataclass digests, not mutable API-wrapper digests.
- `workpaper_id`, `workpaper_version`, `workpaper_digest`: an explicitly selected retained workpaper version and its `store.digest(version)`. Historical versions are supported; the chosen version must explicitly list this task in `task_ids`, with the same control. No latest-version substitution occurs.
- `purpose`, `procedure`: author-supplied descriptions.
- `items`: one to500 distinct exact selected item IDs. Each item is `{item_id, observation, status, evidence}`. Status is `OBSERVED`, `EXCEPTION_RECORDED`, `SUPPORT_UNAVAILABLE` or `NOT_PERFORMED`. These are manual assertions, not system test results.
- Each evidence reference is `{artifact_id, sha256, locator}`. The locator is explicitly author supplied; software verifies retained bytes and reference membership, not whether the locator or observation accurately describes the document. Observed/exception items need at least one retained support reference. Unavailable/not-performed items may have none.

Only currently available learner-visible retained artifacts may support this public trace, including when an instructor records it. The handler verifies actual originals and preserves exact source row digests, sampled versus targeted basis, nested parent selection/population digests, population reliability/provisional status, current scope and company source context. A source-record-version sampling unit remains that unit; it is not promoted to an independent employee/business population.

A correction adds `predecessor_id`, `predecessor_digest`, and `correction_rationale`. It appends a new trace ID/revision, preserving the exact prior record, task/selection/population identity and item set. Forking an already-corrected predecessor or moving to another scope/company source context is rejected. Changed samples require new execution records. A correction can explicitly reference a different retained workpaper version with the same task link.

Records append only to `sample_executions`. No task status, control conclusion, finding, workpaper version, source content, population acceptance or independent review changes. Missing observations remain missing; partial item traces are allowed and never imply all selected items were tested. `automatic_testing_credit` is false and `independent_review` is `NOT_PERFORMED`.

Limits are512KiB per payload,500 items,20 references per item,100 distinct artifacts,16MiB per artifact and32MiB total distinct retained evidence read per command. Text limits are explicit and reject oversize values rather than truncating. The collection retains at most10,000 trace revisions. Source content is not duplicated into the trace.

Tests exercise actual retained bytes, historical workpaper links, scope and authorization failures, nested lineage, no-reference unavailable observations, provisional populations, correction history, exact Store replay/CAS and role isolation. These verify engineering traceability, not professional evidence sufficiency or substantive grading.

## Authorized UI input pins

`input_pins(state)` computes read-only server pins after the Engine has applied current authorization and artifact audience filtering. Attach its result as `sample_execution_inputs`; it is not a new HTTP API. It returns engagement ID/revision, phase availability, current task digests, immutable selection/population digests and status/count metadata, eligible historical workpaper-version digests and explicit task links, and available learner-visible artifact IDs/hashes/sizes. The UI must send these exact pins, rather than reconstruct Python canonical JSON hashes from JavaScript numbers. Selected item IDs/rows remain in the already authorized population/selection state.

The projection excludes duplicate identities, stale-scope tasks/populations, invalid lineage, private artifacts, and workpaper versions without an explicit eligible task link. It does not read original bytes or decide whether inputs provide adequate support; actual originals are rechecked on record. Oversized projection collections return `INPUT_LIMIT_EXCEEDED` with every choice list empty; malformed legacy projection fields return `INPUT_DATA_UNAVAILABLE` likewise. This optional index cannot break authorized engagement reads or make a committed command appear to fail. No partial index is presented as complete. Mutation-handler limits still reject oversized commands. Ordinary number representation such as1.0 and1e20 is tested using server object digests. The helper does not mutate the engagement.

`sample_execution_inputs.correctable_executions` contains `{execution_id, predecessor_digest}` for current leaf trace records only. The digest is computed on the exact retained server record. Superseded revisions remain in history but are not offered for another correction. Changed scope, company binding/acquisition, unavailable current task/sample identities or inactive engagement suppress correction pins. Receiving a pin does not bypass fresh command authorization, CAS, original-byte verification or correction validation.
