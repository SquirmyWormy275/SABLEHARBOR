# Selected instructor debriefs

`InstructorReleases` adds a finite `EXPLANATION` document alongside unchanged HINT and POINTER releases. This is selected instructor-authored assistance, not grading, professional acceptance, proof of understanding, or a new evidence grant. No model calls, company-source collection, audit commands or automatic release occur.

`debrief_options(instructor, engagement)` returns authorized named learners, current revision, a historical revision range, the bound Key digest, issue/expectation selection IDs and titles, and current learner-visible artifact metadata. It does not disclose issue bodies or native bytes in its result. Existing bound-Key integrity verification still verifies the private binding. Titles fall back to stable IDs when the authored Key has no title.

`debrief_preview(instructor, engagement, payload)` accepts exactly:

```json
{
  "recipient_id": "explicit learner",
  "expected_revision": 12,
  "learner_revision": 8,
  "title": "Selected explanation",
  "predecessor_release_id": null,
  "sections": [{
    "issue_ids": ["explicit bound issue"],
    "expectation_ids": ["explicit bound expectation"],
    "explanation": "Instructor-authored analysis",
    "limitations": "Explicit uncertainty and limitations",
    "prompts": ["A discussion question"],
    "annotations": [{
      "artifact_id": "current learner-visible original",
      "sha256": "exact retained SHA256",
      "note": "Instructor annotation",
      "locator": {"kind": "LINE", "value": "2–4"},
      "attach": false
    }]
  }]
}
```

Locator kinds are PAGE, LINE, CELL, TIME and OTHER; locator may be null. Locators are authored, not independently verified. Every expectation's issue references must be explicitly selected in its section. Selected issue claims, uncertainty, procedures and alternatives are copied from verified authored Key fields only. Neighbor issues, hidden source directories, whole snapshot dictionaries, task links and source IDs are not implicitly released. Exact original navigation/attachment authority comes only from explicitly selected artifact annotations.

The server resolves Key and learner history pins using streamed `inspect_history`, retaining only the selected and Key-bound states. It verifies the bound history prefix and state digest. Document `learner` records actor, revision, simulated clock, state/event/history SHA256 and the shared-state qualification. Historical revision is not a submission or individual performance record; selected Key support may postdate it. Historical scope must match current scope. Current authorization and pointers are independently rechecked.

Document `source_references` contains only annotated artifact IDs and hashes. When a retained receipt establishes matching native SHA, an allowlist preserves company/branch/system/record/version/SHA and optional physical store, alias, registry and portfolio qualification. Otherwise the native identity remains null/UNRECORDED. No local paths, neighboring source IDs or raw provenance are copied. A later metadata mismatch suspends access rather than substituting another source.

Limits: 10 sections; 10 issues and expectations per section; 8 prompts of up to 1,000 characters; 4,000-character explanations/limitations; 200-character title; 8 distinct originals; each original at most 4 MiB and attached originals at most 16 MiB. Annotation notes are at most 1,000 characters, locator values 200. Conflicting duplicate original SHA/attachment choices are rejected. Document canonical bytes are capped at 256 KiB; aggregate private document storage at 8 MiB. Limits fail closed, without truncation.

Preview returns the exact document and digest, with 30-minute expiry. Existing `confirm`, explicit recipient `read`, `acknowledge`, metadata `list`/`history` and `revoke` apply. Confirmation does not mark delivered. A correction explicitly names a same-instructor/recipient/engagement explanation release; it creates a new immutable document version and pins its predecessor. Earlier content and delivery history remain unchanged. There is no implicit latest version selection.

## Portable export

`export_preview(actor, engagement, release_id, {release_sha256})` is permitted only for the original current instructor or named current learner. It returns a private export preview with exact filename, output SHA256, bytes, ordered member names/byte counts/hashes, current state digest and expiry. It does not return ZIP bytes or record an export.

`export_confirm(actor, engagement, release_id, {preview_id, preview_sha256, command_id})` rebuilds the same package, rechecks exact current state, Key, roles, source identities, originals and revocation, then journals EXPORTED with the output hash. The internal return includes binary `bytes`, `filename`, `sha256`, `byte_count`, `release_id` and `exported`. The HTTP integration emits an explicit binary response, not an automatic GET or token URL. Exact retries rebuild and verify bytes and return the same package without a duplicate journal event. Changed command payloads fail. Revocation prevents new exports and retries but cannot recall already downloaded files.

ZIP member ordering, timestamps, permissions and uncompressed storage are fixed, so identical immutable release content and attachments produce identical bytes. `debrief.html` uses escaped readable text, no scripts or network resources. `manifest.json` is canonical machine-readable content and pins. Only originals explicitly selected with `attach: true` are included under generated hash-based `.bin` names; user filenames and source paths are never ZIP paths. Users must treat original attachments as source files, not executable instructions. The ZIP is at most 20 MiB. No private Key archive or unreleased preview is a portable learner export.

Private snapshots remain `PRIVATE_INSTRUCTOR_RELEASE_ARCHIVE_V1`, now recognizing validated explanation documents, export previews and export events while preserving old HINT/POINTER archives. Snapshot preflight bounds allocation. These are sensitive inert operator archives, not an operational authority restore or learner ZIP. No release principals, source grants, credentials or bindings are restored by this module.

Focused tests cover selection limits and isolation, streamed historical pins, selected exact attachments, escaped deterministic exports, current-role/context races, revocation/replay, correction lineage, inert archive validation, legacy compatibility and metadata-only lists. Disposable technical fixtures do not establish IK-06 human calibration or authorize actual learner release.
