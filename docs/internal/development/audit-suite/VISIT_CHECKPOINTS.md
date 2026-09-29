# Explicit personal visit checkpoints

`enterprise/audit_suite/visit_checkpoints.py` supplies a private actor-and-engagement checkpoint companion. Saving or replacing a checkpoint is explicit. It does not acknowledge reading, inspecting or testing records, resolve work, or change formal engagement state. This supports the bounded UX06/CX03 resume workflow; it does not establish usability acceptance or cover every company update.

The inventory includes six existing personal-view record types: controls, tasks, available learner-audience retained artifacts, populations, selections and individually pinned retained workpaper versions. It uses only the caller's current authorized Engine projection and existing exact reference validation. No original bytes, native company reads, private Key stores, guidance, assessment, release or personal-draft content are read. Future-available originals and private-audience artifacts are excluded, including for instructors. Inventory rows contain only `{reference:{kind,id,version,sha256},record_sha256}`. Source metadata changes can therefore be detected even when the retained byte hash does not change. A new workpaper version appears separately; the old pinned version is never silently replaced.

## API

Construct `VisitCheckpoints(existing_private_directory, engine)`. Storage is separate `visit-checkpoints.sqlite3`, owned private regular file with no aliases. The schema does not alter personal views or formal audit tables.

- `status(actor, engagement)` returns checkpoint metadata, never inventory or change counts.
- `capture(actor, engagement, expected_version=0, expected_engagement_revision=N, command_id=...)` explicitly creates the first checkpoint. Replacing it requires its current version. Every replacement preserves immutable history. Exact retry of the current checkpoint checks current authorization and returns its metadata. Retrying an older command after checkpoint replacement conflicts; it never silently returns the newer checkpoint.
- `compare(actor, engagement, expected_version=N, expected_engagement_revision=M)` returns exact `ADDED` and `CHANGED` pin pairs and added/changed/unchanged counts only when the saved basis and every prior target remain available.
- `history(actor, engagement)` returns bounded checkpoint metadata only. No historical inventories or per-checkpoint item counts are exposed.

Metadata includes engagement ID/current revision, checkpoint version, saved timestamp/revision when present, status, six supported kinds, qualification, `formal_work_mutated:false` and backup status. Comparison rows are `{change,prior:null|pin,current:pin}`. Normal statuses are `NO_CHECKPOINT`, `CURRENT`, `CONTEXT_CHANGED`, `TARGET_UNAVAILABLE`, `INPUT_LIMIT_EXCEEDED` and `INPUT_DATA_UNAVAILABLE`. Revision mismatches reject with `CHECKPOINT_CONFLICT`/409. Inherited final personal-view context guards also reject authority or engagement races with `VIEW_CONTEXT_CONFLICT`/409.

The context basis pins scope, company-source binding, acquisition configuration, projected permissions and current membership. If that basis changes, or any prior target is now absent, private, quarantined or unavailable, the entire comparison omits both details and counts. There is intentionally no removed-record report that would disclose revoked record existence. Explicit replacement can establish a new baseline under current authority; it makes no assertion about the former records. Scope, source and membership checks are repeated before publication/return. A comparison is a bounded request snapshot, not a promise that another writer cannot change state after response.

## Limits and integrity

Inventory is limited to 10,000 exact pins and 2 MiB; no partial inventory or partial counts are returned. Invalid/ambiguous legacy metadata becomes an unavailable comparison; a capture fails without committing. Up to 100 explicit versions per actor/engagement, 10,000 total private history rows and 64 MiB history are allowed. SQL row counts, field types, individual field sizes and aggregate content/metadata bounds are checked before any private rows are materialized, including backup. SHA-pinned history links and command fingerprints are validated; immutable SQL triggers prevent maintained updates/deletes to history or commands. Replacements use the private database transaction plus final current Engine revision/context checks. No shared multi-database atomicity is asserted.

## Inert backup

`snapshot()` is a trusted companion backup operation, not a browser endpoint. It returns the exact logical archive `{format:'PRIVATE_VISIT_CHECKPOINT_ARCHIVE_V1',tables:{checkpoints,checkpoint_history,checkpoint_commands}}` under one validated read transaction. `validate_snapshot(value)` checks exact schemas, bounds, chains, ownership, head versions and command fingerprints. The archive is sensitive: it contains historical actor IDs and reference pins even when current interactive access is redacted. Store it only as a private verified companion archive. There is no operational rehydration, principal mapping or automatic checkpoint activation. The DTO reports `SNAPSHOT_AVAILABLE_INERT_ARCHIVE_ONLY`; the explicit companion backup integration below does not imply any live workspace has already been backed up.

Focused tests use disposable local state for exact version differences, replay/replacement, context/count redaction, revoked/missing originals, future availability, cross-actor isolation, instructor private-original exclusion, unchanged formal state, bounded malformed input, final race rollback and archive tamper rejection. No real workroom or model calls are involved.


## Workroom integration

With the existing `workspace_contexts` option enabled, the service advertises
`visit_checkpoints` and constructs a separate private companion. The default remains
disabled. Authenticated routes under `/api/engagements/{id}/visit-checkpoint` are:

- `GET` returns current personal metadata; `GET /history` returns metadata history.
- `POST` explicitly captures the supplied exact checkpoint/workspace revisions and command ID.
- `POST /compare` compares the supplied exact revisions without changing either store.

Mutation-style requests require the normal CSRF/actor checks and bounded request
rate. Unknown fields are rejected. All operations enforce current membership and
repeat context checks before returning.

“Changes since my checkpoint” appears beside personal saved views. Refresh,
comparison and replacement are explicit; navigation never automatically captures a
checkpoint. The panel preserves an unresolved save envelope for exact retry and
requires reload before starting a different save. It displays 100 differences per
page with full-result counts, keeps unavailable comparisons free of record details
and counts, and opens only currently resolvable exact record versions. Evidence
preview additionally requires the visible retained byte hash to match. A changed
engagement, revision or permission basis discards stale responses and transient UI
state. Metadata-only responses cannot supply comparison inventories.

`companion_recovery.backup(destination, visit_checkpoints=companion)` captures a
validated private snapshot. Restore writes `visit-checkpoints-ARCHIVE-ONLY.json`;
it creates no active checkpoint database and restores no credentials or grants.
Ordinary engagement backup alone does not include this separate companion.

Validation: 93 backend integration/regression tests passed, including routes,
redaction, exact retries, companion archive corruption, and existing personal views
and service behavior. The full frontend suite passed 235 tests; the compiled-App
checkpoint journey covers lost-response retry, artifact version changes, pagination,
hash-mismatched preview denial and late prior-context response isolation. These are
scripted checks, not owner usability acceptance.
