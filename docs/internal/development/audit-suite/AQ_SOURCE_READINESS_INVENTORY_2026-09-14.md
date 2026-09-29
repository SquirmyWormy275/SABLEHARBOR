# Explicit source-readiness inventory

`enterprise/audit_suite/source_readiness.py` inventories explicitly selected local company sources against one explicitly selected engagement. It preserves documentary, authored exercise, migrated reference and unknown provenance distinctions. None of these classes asserts actual company operation, independent corroboration, professional sufficiency or a coherent operating year.

The trusted operator runs:

```bash
uv run --extra audit-suite python tools/audit_suite/source_readiness.py \
  --config /absolute/private/config.json \
  --output /absolute/private/NEW-report
```

The public tool contains no populated company records or instructor keys. Input configuration and generated reports remain private. The API exposes `load_config(path)`, `inventory(config)` and `write_inventory(config, destination)`. It is not an authenticated learner endpoint: filesystem access is the trusted operator boundary. It does not grant access, collect sources, generate evidence, change audit state, or search unspecified workspaces.

Configuration has exactly three keys:

```json
{
  "target": {"root": "/absolute/private/audit", "engagement_id": "explicit-engagement"},
  "audits": [],
  "sources": [{
    "id": "explicit-component",
    "root": "/absolute/private/company",
    "company": "explicit-company",
    "branch": "explicit-branch",
    "systems": ["explicit-system"],
    "category": "OPERATOR_SUPPLIED_REFERENCE_LABEL"
  }]
}
```

Additional audits use the same exact selector shape as `target`. Work remains grouped by its originating engagement and snapshot revision; it is never credited to another engagement. Source categories are operator labels and cannot promote the native provenance classification. Source components retain separate roots, companies, branches and system memberships, including registered systems with no source versions. Duplicate physical routes are rejected.

Repository synthetic documents remain documentary design references with unknown business-event dates and recorded ingestion availability. Legacy sources explicitly classified as documentary remain documentary. Other migrated history remains a qualified migrated reference; authored training sources remain authored activity/reference exercises. Unknown origins remain unclassified. Source-authored qualifications and exact period fields are retained, rather than converted into claims of coverage.

Only typed `control_id`, `control_reference`, `control_ids` and `control_references` at native JSON object or provenance roots establish reference links. Prose, filenames, owner assignments and control names do not. Binary documents are not parsed for implied mappings. The complete target controls and assigned procedure metadata are preserved alongside these links. Missing links mean absent explicit references within this selected inventory, not missing company activity or a failed control. Declared dates do not establish whole-period coverage.

Each database is read using a bounded, read-only SQLite transaction without initializing schema. Native content hashes and selected native collection receipts are verified, including receipt identity, source metadata, input digest, byte count and availability cutoff. Selected audit event chains and their final state are verified. Retained company artifacts receive collection credit only when an exact selected native receipt matches and retained bytes match the original hash and size. Unmatched artifact receipts are reported separately as unverified; identical receipt identities present in multiple source stores are explicitly ambiguous. Historical receipts do not establish current grants.

`MATRIX.json` retains exact source/version membership and references; `MATRIX.csv` is only a compact control index. `CONFIG.json` preserves the explicit selection. `MANIFEST.json` pins each output and the implementation bytes. Capture timestamps and ordered logical membership digests describe separate database snapshots, not a global database transaction or the mutable on-disk SQLite file hash. Concurrent appends appear in a subsequent run, not halfway through a component snapshot. Retained filesystem artifact reads occur separately from database transactions.

Inputs require existing private roots and regular private files, without symbolic or hard links. Output requires a new destination beneath an existing private parent, outside all selected input roots. Reports are staged privately and published with file/directory flushes; existing destinations and historical inventories are not overwritten. Invalid or corrupted input fails the run rather than producing a successful verification report. The tool does not claim an externally anchored audit-log signature: hashes verify internal consistency against the selected local sources.

Neutral tests cover non-70-control scopes, explicit engagement and branch selection, documentary category spoofing, malformed typed references, unknown systems, registered empty systems, source and receipt corruption, audit-history tampering, retained-byte corruption, distinct stores with matching native identities, WAL snapshot consistency, private paths and new output requirements, and invocation outside the checkout working directory. Populated validation receipts and source inventories live only under ignored `enterprise/generated/audit-suite/source-readiness-maintained-2026-09-14/`; prior hardcoded matrices remain preserved.
