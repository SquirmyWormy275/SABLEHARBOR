# One-system source-record census

`company_source_census.py` exports exactly one authorized source system. A portfolio alias resolves to one existing concrete component and database; it never joins component histories or creates a cross-store population. `company_source_census_collection.py` retains those originals through native collection receipts and proposes an explicit provisional population import. The existing OperatingModel population path remains separate.

The Engine advertises `company_source_census` when a company source connection is configured. The command is:

```json
{
  "kind": "company.census.collect",
  "payload": {
    "request_id": "existing-issued-request",
    "system_id": "explicit-native-system-or-portfolio-alias",
    "query": {
      "version_policy": "ALL_VISIBLE_VERSIONS",
      "event_window": {
        "start": "2027-01-01T00:00:00+00:00",
        "end": "2028-01-01T00:00:00+00:00"
      },
      "unknown_event_policy": "INCLUDE_UNDATED_STRATUM"
    }
  }
}
```

The ordinary command ID and expected engagement revision envelope remains required. Actor identity, source binding and visibility cutoff come from authenticated Engine state, not query fields. The request must already be issued and identify a scoped boundary. The half-open event window must fit the audit period and must have ended by the simulated clock. Offset timestamps are explicit; date-only audit bounds are interpreted in the scoped timezone with inclusive final calendar dates.

`ALL_VISIBLE_VERSIONS` retains every visible version whose event belongs to the window, plus explicitly included undated records. `LATEST_VISIBLE_PER_RECORD` first resolves the highest visible version per source record, then applies the event window. A correction outside the window cannot cause an older version to reappear. A future unavailable version does not displace an available predecessor. Both policies sample **source-record versions**, never inferred employees, tickets, changes, transactions or business events.

`unknown_event_policy` is either `EXCLUDE` or `INCLUDE_UNDATED_STRATUM`. Included unknown dates are preserved as null and labeled `date_stratum: UNDATED`; dated rows carry `IN_EVENT_WINDOW`. One provisional population contains these explicitly separated strata. Its declared query period does not establish an event date for undated rows. Availability, import dates and source-authored period descriptions are retained as separate metadata and never substituted for unknown event dates. Origin and provenance qualifications remain unchanged. Source-to-boundary applicability and business completeness remain unassessed.

The export reads a single SQLite snapshot across all pages. Queries use fixed SQL and bound parameters. It fetches bounded identity/size pages before loading selected originals, verifies every selected native hash and caps output at 2,000 members, 64 MiB native bytes and 8 MiB metadata. Page budgets fail explicitly without a partial successful export. The manifest pins exact physical identities, original hashes, ordered membership, pages, policy, exclusions and cutoff. A portfolio adds its frozen registry digest, component ID and system alias separately from original native metadata. Counts of inaccessible or future originals are not disclosed.

Current grants are rechecked after snapshot extraction; portfolio routing is rechecked against the frozen registry. Collection verifies original native receipts and rechecks grants/binding before adding artifacts to audit state. A revoked or changed source cannot silently fall back to another source. If failure follows native collection or filesystem retention, existing native collection receipts and private orphan files may remain; no audit mutation or population registration is committed. Explicit command retry uses normal command idempotence and exact source identities. It does not claim transactional atomicity across the audit database, source journal and filesystem.

Results appear in `request.company_census_collections`. They include `source_versions`, `distinct_source_records`, dated/undated `strata`, visible-candidate exclusions, native artifact references, query manifest and working-row artifacts, exact snapshot pins and `next_command`. The caller reviews and explicitly issues `population.import`; status begins `PROVISIONAL`. Empty censuses are valid observed empty exports with `registration: EMPTY_CENSUS` and no import proposal. Neither collection nor registration records test completion, source reliability acceptance, professional independence or effectiveness. Existing population review, revision and selection contracts continue to apply.

For a read-only operator export outside the UI:

```bash
uv run --extra audit-suite python tools/audit_suite/source_census.py \
  --config /absolute/private/config.json \
  --output /absolute/private/NEW-export
```

The private configuration contains exactly `audit_root`, `actor_id`, `engagement_id`, `source`, `system_id`, and `query`. `source` is either `{ "root": "/absolute/private/company" }` or `{ "registry": "/absolute/private/registry.json", "profile": "explicit-profile" }`. The selected audit must already have a frozen company binding. The command checks current audit membership, native source grants, audit period and simulated clock; it never accepts an independently supplied cutoff. It verifies that audit state and source access remain current before publishing. Output requires a new private directory outside all input roots and contains exact native copies, manifest, configuration and receipt. It creates no source collection journal entry, audit artifact, request or population. It does not expose private paths through an HTTP endpoint.

Neutral tests exercise latest-before-window semantics, undated policy, future visibility, empty systems, pagination and byte budgets, native/manifest corruption, concurrent append snapshot consistency, revocation during extraction and retention, changed portfolio routing, cross-component isolation, actual Engine original collection and explicit provisional import, ordinary replay, and the operator command's private non-overwriting export. Actual read-only validation exports under ignored `enterprise/generated/audit-suite/source-census-2026-09-14/` preserve their own source/code pins; they are technical census checks, not substantive audit conclusions.
