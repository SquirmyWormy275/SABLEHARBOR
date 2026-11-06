# Use the CLEAN and MESSY company records in audit software

The accepted [company source library](company-records/README.md) contains the
records for two alternative fictional company histories. An ordinary clone can
read and verify them without a local workspace, external drive, credential or
company generator. Use one history per audit-software test run:

| Scenario | Company history | Native branch | Source versions | Systems |
| --- | --- | --- | ---: | ---: |
| CLEAN | [history-01](company-records/history-01/) | `HARBOR-OPERATIONS-A` | 5,556 | 698 |
| MESSY | [history-02](company-records/history-02/) | `HARBOR-OPERATIONS-B` | 5,642 | 726 |

These names describe the delivered local workroom bindings. The Git files are
company-side source records, not copies of learner workpapers, instructor answers
or the interactive workroom databases. Keep the two histories separate; their
counts do not form one company population.

## Verify the files before import

Pin the Git commit used for a test run. The verifier needs only Python 3.11 or
newer and its standard library; no project dependencies are needed. From the
repository root, run:

```sh
python3 -m tools.audit_suite.company_record_delivery verify --root docs/audit-suite/company-records
```

It prints one JSON line and exits with a non-zero status if anything differs.
For the current edition, which appends the authored extensions listed in the
[company records guide](company-records/README.md) to the accepted 18 October 2026 edition, its
`manifest_sha256` is
`b78c95a71a05e7e782d5cdb8d5784328ae6c024e01e2c1dee171696c754c4289`, with
`verified_source_versions` 11,198, `verified_source_systems` 1,424, `originals`
11,193 and `derivatives` 5. The 18 October 2026 edition's `manifest_sha256` was
`30cbdf23a68532e5026a87d0dddb06cd09242b87ea3a58d009b39aacddc629c7` (5,714
versions, 922 systems); the current manifest records it as the extended edition. The verifier checks every version, its provenance and
membership, and the exact-byte originals versus the five documented
routing-metadata derivatives.
If a later accepted commit changes the manifest, use its own hash and verification
result rather than silently treating it as this edition.

## Import one scenario

To get one scenario's records, verify and select in one step. Write the output
outside `company-records/`, because any extra file there fails verification:

```sh
python3 -m tools.audit_suite.company_record_delivery select --root docs/audit-suite/company-records --scenario CLEAN --output clean-records.jsonl
python3 -m tools.audit_suite.company_record_delivery select --root docs/audit-suite/company-records --scenario MESSY --output messy-records.jsonl
```

Each output line is one unchanged manifest record. The command refuses to write
if the delivery fails verification or the output file already exists. It prints a
summary to standard error: CLEAN is `history-01` with 5,556 records across 698
systems, and MESSY is `history-02` with 5,642 records across 726 systems. Without
`--output`, the records go to standard output.

The selection is a convenience over the manifest. To read the manifest directly,
open `company-records/manifest.json`. For CLEAN, select records whose
`history_id` is `history-01`; for MESSY, select `history-02`. Either way, resolve each
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
