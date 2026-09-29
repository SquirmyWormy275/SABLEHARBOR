# Exact selected-source prerequisite for linked activity plans

`company_activity_plan_sources.resolve_source` is a read-only prerequisite, not a company-year generator. It accepts keyword arguments `source_root`, `source_manifest_path`, `expected_manifest_sha256`, `binding`, `consumed_at` and `destination`. The caller retains responsibility for job ordering, kind-specific cutoff selection and new-only output publication. Existing V1 activity-plan code and the shared native operator are unchanged by this module.

The binding has exactly:

```json
{
  "source_store_id": "explicit-producer-label",
  "expected_records": [
    {"company": "C", "branch": "B", "system": "hr", "record": "R1", "version": 1, "sha256": "<64 lowercase hex characters>"},
    {"company": "C", "branch": "B", "system": "directory", "record": "R2", "version": 2, "sha256": "<64 lowercase hex characters>"}
  ],
  "expected_selected_metadata_sha256": "<64 lowercase hex characters>"
}
```

Two to eight distinct exact native references must identify one physical company/branch. Positive integer versions reject booleans and floats. No missing hash, latest-version lookup, record-range expansion, resource scan or implicit identity mapping is supported. The caller's producer label remains an explicit claim for this binding, separate from any native provenance label; the resolver neither rewrites native identifiers nor asserts that matching names establish lineage.

The source manifest must be the expected private completed `PRIVATE_COMPANY_ACTIVITY_RUN_V1` manifest, with an explicitly listed `company/company.sqlite3`; `source_root` must be exactly that manifest's `company/` directory. Before and after the selected read, the resolver checks the expected manifest digest and every explicitly listed member digest. Manifest JSON is bounded to 512 KiB, member count to 5,000 and aggregate member bytes to 256 MiB. Private modes, nonsymlink paths, single-link regular files and read-time file identity checks apply. Caller trust in the expected manifest's origin remains explicit; this is not cryptographic proof of who produced it.

The hardened lifecycle reader performs one bounded selected-row transaction, preserving content hashes and exact metadata. The resulting metadata digest must equal the caller's expectation. Known source event and availability timestamps must both be no later than the supplied consumer cutoff, compared as instants. The caller selects the correct meaning: lifecycle `request_at`, nonhuman identity `period_start`, or risk `input_at`. This proves only that those selected input records were available by that declared cutoff; it does not prove continuous company operation.

The return value contains typed `source_refs`, `source_versions_sha256` and a JSON receipt with exact selected metadata, manifest pin, producer label, cutoff and explicit limits. The resolver writes nothing. `destination` may be absent or an existing private directory for post-generation checks, but it cannot contain the source job or be contained by it. The runner must separately enforce new-only consumer creation and rerun source checks before marking a consumer complete. Source read, consumer generation and later verification are not one global transaction.

Validation: 14 focused tests passed against genuine maintained-operator mover outputs. Tests cover exact selected pins, original-byte preservation, explicit label retention, repeated post-generation checks, wrong native/metadata/manifest hashes, future sources, malformed versions, duplicate references, wrong roots, aliases, both containment directions, changed manifest during selection and tampered manifest members. Ruff passed. No existing company/audit store, grant, model session, shared runner or source chronology was changed by this resolver task.
