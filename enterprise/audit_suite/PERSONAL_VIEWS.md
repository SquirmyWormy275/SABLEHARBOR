# Personal saved views

`personal_views.PersonalViews(private_root, engine, max_active=16)` stores explicitly saved navigation in a separate `saved-views.sqlite3`. The existing directory must be private and owned; the database is 0600, nonsymlink and not hardlinked. No record content, draft, instructor-Key content or formal audit event is stored or generated.

The exact payload is:

```json
{
  "title": "Backup originals",
  "section": "pbc",
  "query": "backup",
  "framework": "all",
  "table": {"id": "artifacts", "query": "job", "sort": "name", "page": 2},
  "reference": {"kind": "artifact", "id": "ACTUAL_ID", "version": 2, "sha256": "ACTUAL_SHA256"},
  "scroll_top": 410
}
```

`table` and `reference` may be null. Title is 1–120 characters, queries at most 1000, page is an exact integer 0–10000, scroll_top an exact integer 0–1000000. Framework is `all` or a current `scope.programs` member. Sections are the ten existing learner workspace sections: kickoff, controls, pbc, meetings, people, populations, notes, calendar, findings, review. No arbitrary URL, path, Key section or table header fallback is accepted.

Table IDs and sort columns are allowlisted against actual current `Table.memoryKey` contracts in App. Procedures/controls belong to controls; requests/artifacts to pbc; people to people; populations/selections to populations; calendar/events to calendar; findings to findings; workpapers/reviews/exports to review. Sort is empty or one of that table's actual columns. Page and scroll are navigation hints: the client may need to clamp them to the current visible rows/viewport and should make any change apparent. They do not pin the entire table population.

References reuse the workspace-context kinds: control, task, artifact, population, selection, workpaper. They pin exact authorized metadata/version; workpapers require an exact retained version. Artifacts must currently be AVAILABLE. Excluded/not-applicable procedures and duplicate identities are unavailable. `make_reference(actor, engagement, kind=..., record_id=..., version=...)` obtains the authoritative pin. The saved section must match the reference kind. No nearest match or latest-version substitution is performed; this is not a native-byte download/read assertion.

## Explicit APIs

- `create(actor, engagement, payload, expected_engagement_revision=..., command_id=...)`
- `save(actor, engagement, view_id, payload, expected_version=..., expected_engagement_revision=..., command_id=...)`
- `read(actor, engagement, view_id)` and `listing(actor, engagement)`
- `restore(actor, engagement, view_id, expected_version=..., expected_engagement_revision=...)`
- `clear(actor, engagement, view_id, expected_version=..., expected_engagement_revision=..., command_id=...)`

All methods recheck current principal membership and authorized engagement context. Save/clear use exact version CAS and an engagement revision supplied by the current UI. Reads return `navigation:null`; only explicit restore returns `navigation` containing the payload minus title. Reading or listing never restores UI state automatically. A restored historical workpaper reference still names its exact old version.

Responses retain `engagement_revision` as the saved watermark and report `current_engagement_revision` plus `revision_status`. A later revision alone does not destroy a valid personal view. Scope, company binding, evidence acquisition or permissions/membership changes produce `CONTEXT_CHANGED`, `restorable:false`, and metadata only: saved title/query/reference are omitted. If the basis remains current but a target becomes unavailable or changes, the owner can still see the personal payload, but restore fails explicitly. An explicit save of a newly reviewed payload records a new basis; no stale content is automatically revalidated or rewritten.

Clear writes a tombstone and preserves private immutable history. Replaying an older successful command returns the current projection or tombstone, so an old transport retry cannot resurrect cleared personal text. Changed input under the same command ID conflicts. Maximum active views is 16 by default (configurable 1–32), lifetime 32 per principal/engagement, 200 editable versions per view plus a final clear tombstone at 201, 16 KiB per stored version and 64 MiB of history per private store. No cross-principal listing or reuse is exposed.

## Recovery boundary

The store is separate from ordinary engagement backup. Explicit `companion_recovery.backup(destination, personal_views=views)` now captures its application-owned tables in one read transaction, with a per-component capture timestamp and manifest pins. `restore(..., engine=current_engine, principal_map={old:new})` creates a new `personal-views/` store using the application schema, validates typed identities and contiguous history/command ownership, and requires current authority for every mapped principal/engagement. No credentials or grants are copied.

Hashed personal content and history remain byte-identical. A separate immutable ownership-receipt chain records each old→new owner mapping, source manifest and exact history-version boundary; operational reads validate this chain. A subsequent edit is a new version authored by the mapped principal. Repeated restore preserves all earlier ownership receipts. Changed scope/permission/source basis still redacts personal content and prevents restore; mapping does not override current authorization.

The response is `EXPLICIT_COMPANION_SUPPORTED_NOT_AUTOMATICALLY_BACKED_UP`. Support does not mean a backup was actually taken, nor that separately captured components form a globally atomic checkpoint. Old companion bundles without personal views do not cover them. Jobs and instructor-release archive-only recovery semantics remain unchanged. No existing module's unrelated stale recovery wording was promoted to a full-rehydration claim.

Focused tests exercise actual isolated Engine principals, reload/restore, exact historical versions, changed authority and source context, unavailable artifacts, CAS/retry/clear, quotas, private-path aliases, current-row tampering, expired principals and permission revocation. Service/UI routes are separate work; focused recovery tests additionally cover explicit mappings, preserved hashes, repeated restore, orphan/foreign ownership rejection and publication-time authority/source changes.
