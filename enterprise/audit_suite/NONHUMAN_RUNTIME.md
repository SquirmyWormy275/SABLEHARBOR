# Persistent local nonhuman identity operations

`company_nonhuman_runtime` continues one exact fictional Q2 copy identity into a new independently declared period. It preserves credential and consumer state between operations. It does not create vendor accounts, usable secrets, host identities, deployment or accepted enterprise credential policy.

## Admission

`initialize(destination, repository, prior_root, prior_recipe, prior_branch, prior_refs, expected_prior_metadata_sha256, backup_source_root, declaration_root, declaration_pin, as_of)` requires keyword inputs after the destination. The repository must match the loaded maintained checkout.

The typed prior recipe is `NonhumanIdentityRecipe`. The full selected original branch contains 18 or 17 native records, including original copied bytes and failed attempts; four exact original backup inputs are separately verified. A pure replay of the existing `LocalCopyIdentity` resolver/rotation/copy primitive reproduces every original body and sequence link. Native identity, byte hash, origin, provenance, command identity, input digest and event/availability times must match. Historical implementation/document pins remain historical and are not rewritten to current code. Initial credential version 2, retired version 1 and consumer version 2 are admitted only after this complete replay.

An independent native operating-period declaration identifies the new company branch, the one identity, the scoped owner, period and due occurrences. Its metadata and actual import time are pinned separately from its native content reference. The new period starts at the original quarter's end, contains one to four full calendar quarters and must declare exactly one `REVIEW-` due occurrence per quarter. Additional `ROTATION-` occurrences are explicit local declarations, not an inferred corporate rotation frequency. Schedule windows/dependencies remain controlling; a missing review cannot disappear because a caller omitted the quarter's due slot.

Initial historical source actors are retained as a verified historical basis. Current governance changes cannot substitute another author for old Q2 records. The new runtime independently resolves its scoped owner and distinct operating reviewer at initialization. This remains a fictional scoped assignment, not corporate appointment acceptance.

## Operations

`execute(runtime, expected_runtime_sha256, expected_revision, expected_state_sha256, command_id, action, payload, actor_id, event_at)` uses keyword arguments. Inspect first to obtain the exact current state digest. Supported exact payloads are:

| Action | Payload | Local result |
|---|---|---|
| ROTATE | expected_credential_version, occurrence_id | Retires the current inert integer version and advances it; requires an unperformed declared ROTATION- occurrence. |
| UPDATE_CONSUMER | credential_version | Changes the one consumer to the exact currently active version. |
| COPY | principal_id, source_id, target_id | Calls the real local resolver. A stale credential or wrong principal/resource denies; success copies exact source bytes to a native copied_dataset original. |
| REVIEW | occurrence_id | Distinct scoped reviewer records computed current owner, purpose/dependency and credential mismatch facts for the declared REVIEW- occurrence. |
| RECONCILE | empty object | Compares actual recorded occurrences with every independently declared due slot; retains missing review/rotation dates. |

All operations require the owner except REVIEW, which requires the separate scoped operating reviewer. There is no automatic professional judgment. Denied copies persist as native observations with no output bytes. Updating a consumer or successfully copying never substitutes for a quarterly review.

`inspect(runtime, expected_runtime_sha256, as_of)` is read-only and replays all retained native operations before returning revision, state, state_sha256 and reconciliation. It only projects current state at or after the latest retained event; it does not substitute current state for an earlier requested cutoff. Reconciliation reports the selected declared inventory only, with enterprise population completeness and professional review explicitly unestablished.

## Integrity and storage

Initialization publishes a new private staged company store. Operation state, immutable command receipt, operation original and any successful copied bytes commit in one SQLite transaction. There are no external mailbox/file writes, orphan adoption or network/model/audit operations. Exact retries return the original receipt after rechecking sources, native history and current maintained code. Changed retries, stale state/revision, backwards event time and typed-version substitution fail.

`imported_at` is actual local creation time, separate from the fictional business event clock. Genesis rows bind one actual timestamp in the retained definition. Each command binds one actual timestamp in its receipt and operation body, shared by operation/copy native rows; history validates exact metadata and monotonic actual import times. Original prior/backup import metadata is pinned separately without changing the established selected-source recipe digest. Native declaration metadata also includes its retained import time.

The four registered source systems and custody owners must match the definition. Native/body metadata, command history and current-state scalars are bounded in SQL before materialization; corrupt noninteger native versions/state revisions fail before fetch. Writer bounds mirror reader limits. Limits are 128 commands, 512 KiB per native body/state/receipt, 32 MiB aggregate native content/receipts, and bounded scalar/provenance metadata. Initialization validates original selected sources under separate bounded read quotas. Reaching a command quota does not invalidate exact replay of a previously accepted command.

No old sources, source authority journals or audit state are modified. No whole-year control completeness, actual vendor operation, accepted policy, human comprehension or professional assurance is inferred from these local operations.
