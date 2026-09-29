# Protected saved Key filters

`InstructorKeyViews(private_root, engine, bindings, archive_root=None)` persists only existing bound and archive explorer filters. It is a separate instructor-only private sidecar, not an ordinary learner personal view, audit command, explanation release, comparison, evidence grant or model input. It never changes audit state or source originals. Protected Key verification records access for the actual authenticated instructor through the existing access journal.

All routes require current scoped `instruct` membership. Another instructor cannot read someone else's saved view; learner and reviewer roles cannot use this store. Storage requires owned nonaliased directories and regular private files (0700/0600); no hardlinked database. Every operation validates the bounded immutable event/hash chain. Writes use a transaction, final authority/context/pin checks, private version CAS and expected current engagement revision.

Methods:

- `listing(actor, eid, kind)` returns `{engagement_id, current_engagement_revision, kind, views}`.
- `read(actor, eid, view_id)` returns one owned DTO.
- `save(actor, eid, payload)` takes exactly `{view_id, kind, key_pin, user, expected_version, expected_engagement_revision, command_id}`. Creation uses `view_id:null`, version zero; edits use the exact existing ID/version.
- `restore(actor, eid, view_id, payload)` takes exactly `{expected_version, expected_engagement_revision, expected_key_pin}`. Only this explicit operation returns navigation to apply; it performs no original/detail download or comparison.
- `delete(actor, eid, view_id, payload)` takes exactly `{expected_version, expected_engagement_revision, command_id}` and appends a tombstone. It remains possible when the saved Key is unavailable, provided current instructor authority and revision/version checks pass.

The strict user variants are:

```text
BOUND   {title,query,issue_id:null|string,scope_to_issue:boolean,
         source:null|{id,version,sha256},page}
ARCHIVE {title,query,selector,option,review,
         scenario:null|{id,key_sha256},page}
```

Title is 1–120 characters; query at most 1,000. Types are exact: booleans are not integer versions. Selected bound issues and sources must match the verified snapshot, and selected archive scenarios must match the immutable index. Archive filters support existing `all` and exact existing values. Bound issue scoping requires a selected issue. Persisted page must exist in the recomputed result set (10 sources per bound page, 25 scenarios per archive page; page zero for empty results). A deliberately selected original/scenario may remain outside the text filter, matching the existing explorer's qualified behavior. Archive options must belong to the selected selector. No silent page truncation, title-based remapping or latest-version substitution occurs.

DTO fields are `id`, `engagement_id`, `kind`, `version`, `status`, `saved_engagement_revision`, `current_engagement_revision`, `context_status`, `revision_status`, `restorable`, `personal_content_visible`, `navigation` and `backup_status`. Current active views additionally expose `user` and `key_pin`. Listing includes active views only; tombstones remain in immutable history and exact-ID reads. Ordinary list/read/save/delete responses have `navigation:null`; a successful explicit restore returns the exact validated user variant in `navigation`.

Context status is CURRENT, CONTEXT_CHANGED, KEY_CHANGED or KEY_UNAVAILABLE. Revision status separately distinguishes MATCHING_REVISION and ENGAGEMENT_ADVANCED: ordinary work can advance while filters remain usable under the same scope/company/acquisition/Key basis. Historical bound revision/state/history pins remain retained internally, never replaced with current-work pins. Changed Key, authority or source context cannot reveal saved titles, query terms, issue/source/scenario IDs or silently restore them. Deleted views also redact personal content. The immutable archive is pinned at construction like the protected archive route; swapping files causes unavailability until deliberately configured anew.

Exact command retries verify current authority/context. Reuse with different payload is rejected; replay after a later edit or deletion returns conflict rather than resurrecting an obsolete ACTIVE view. On conflict the client must explicitly reload/review, not automatically rewrite under a new revision. A changed context requires deliberate new valid selection/save.

Limits are 16 active views per principal/engagement across both variants, 200 editable versions per view plus a deletion tombstone, and 4,096 total private events. Capacity is reserved for deleting all active views, including across principals. Event-content bytes are bounded at 16 MiB and inert archive bytes at 32 MiB. There is no indefinite audit log, active principal remapping or hidden record-content persistence.

`snapshot()` and `validate_archive()` use `PRIVATE_INSTRUCTOR_KEY_VIEWS_V1`, explicitly `INERT_ONLY_NO_ACTIVE_REHYDRATION`. The archive contains sensitive private filters and immutable original actor/history identities. It is for explicit companion backup integration, not a learner download or operational restoration: no grants, credentials, Key bindings or active saved views are recreated. `backup_status: INERT_ARCHIVE_ONLY` describes supported format, not evidence that any actual backup has run.

Focused tests use a genuine bound snapshot and native generated Key archive to verify both variants, exact pins, reload, page limits, actor/role isolation, stale metadata redaction, current-revision restore, CAS/retry, final-role rollback, immutable-history/schema tamper, quotas, private aliases and unchanged audit state. This implements persistence for existing filters only. Broader authored search dimensions, full-corpus usability and qualified IK-06 acceptance remain separate requirements.

Archive preflight permits only indexed source/key members, index/receipt/ZIP and optional verification receipt. Unexpected files are rejected before their content is read. It bounds paths at 20,000, individual files at 256 MiB, total and expanded ZIP bytes at 512 MiB, and the index at 8 MiB before full protected archive verification. These bounds preserve the existing finite reference-library contract, not arbitrary directory ingestion.
