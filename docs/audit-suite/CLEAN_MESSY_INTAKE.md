# Use the CLEAN and MESSY company records in audit software

The accepted [company source library](company-records/README.md) contains the
records for two alternative fictional company histories. An ordinary clone can
read and verify them without a local workspace, external drive, credential or
company generator. Use one history per audit-software test run:

| Scenario | Company history | Native branch | Source versions | Systems |
| --- | --- | --- | ---: | ---: |
| CLEAN | [history-01](company-records/history-01/) | `HARBOR-OPERATIONS-A` | 2,793 | 447 |
| MESSY | [history-02](company-records/history-02/) | `HARBOR-OPERATIONS-B` | 2,921 | 475 |

These names describe the delivered local workroom bindings. The Git files are
company-side source records, not copies of learner workpapers, instructor answers
or the interactive workroom databases. Keep the two histories separate; their
counts do not form one company population.

## Verify the files before import

Pin the Git commit used for a test run. From the repository root, run:

```sh
python -m tools.audit_suite.company_record_delivery verify --root docs/audit-suite/company-records
sha256sum docs/audit-suite/company-records/manifest.json
```

For the accepted 18 October 2026 edition, the manifest SHA-256 is
`30cbdf23a68532e5026a87d0dddb06cd09242b87ea3a58d009b39aacddc629c7`.
The verifier checks all 5,714 versions, their provenance and membership, and the
5,709 exact-byte originals versus five documented routing-metadata derivatives.
If a later accepted commit changes the manifest, use its own hash and verification
result rather than silently treating it as this edition.

## Import one scenario

Read `company-records/manifest.json`. For CLEAN, select records whose
`history_id` is `history-01`; for MESSY, select `history-02`. Resolve each
manifest `path` below `company-records/` and ingest the file's exact bytes with
its `media_type`. Carry `company`, `branch`, `system`, `record` and `version` as
the source identity. Carry `event_at`, `available_at` and `imported_at` as
different clocks. A file imported in October 2026 may describe a fictional 2027
event, and a record may not have been available at an earlier exercise cutoff.

Keep both `source_sha256` and `sha256`. They match for originals. For five
derivatives, `sha256` identifies the portable delivered bytes while
`source_sha256` identifies the original before absolute workstation routing
metadata was replaced. The manifest's `redactions` and `relationship` explain
that change. The history's `provenance.jsonl` retains source qualifications,
relationships and input digests. Do not infer a completed control from the
presence of a source file or from the scenario name.

The [November client submissions](demo-2026-11/client-records/README.md) are a
separate, narrower three-stage exercise. Preserve initial, follow-up and
correction as three submissions with their own manifests and fictional cutoff;
do not append them to either broad history as if they were extra source versions.

## Interactive workrooms

The [local workspace guide](LOCAL_WORKSPACE.md) covers the installed CLEAN and
MESSY browser workrooms, including their separate audit histories and role
permissions. Those live databases and access material remain private. A clone
supplies the company records above, not a running copy of that installation.
