# Local non-human credential lifecycle

`company_nonhuman_identity_activity.generate_pair(new_destination, repository=...,
source_root=..., recipe=NonhumanIdentityRecipe(...))` creates one explicitly fictional
backup-copy service identity in two new private branches. It exercises the bounded
owner/workload/permissions/dependencies, credential-change and quarter-end review
parts of SH-IAM-006. It does not exercise ownership change, every enterprise service
identity, a full operating year, privileged/break-glass access, or vendor deployment.

`NonhumanSourceRef` is an alias of the existing six-field `LifecycleSourceRef`.
The shared `read_inputs` API returns only declared exact original rows and their
selected metadata digest. Four source records are required: inventory and dataset
as direct inputs; original credential event and failed backup job as historical
motivation. The historical job must reference the exact selected dataset and
credential bytes. Other historical links are retained, not recursively resolved or
represented as inputs. Original human principal AS-P007 is not relabeled as the new
`EXERCISE-SVC-` identity. Original raw bytes and complete metadata are preserved under
`upstream/` and the source receipt. Input availability must precede the new quarter.

Both branches have the same new identity, scoped owner, read-source/write-isolated-
target permissions, consumer and local timetable. A data-only authenticator accepts
only the exact identity, active integer credential version and declared operation/
resource pair. These integers are inert test values, not usable passwords or keys.
A copy operation creates new bytes only after both read and target-write checks.
Actual native copied bytes are retained separately from attempt metadata.

Both branches retire version 1 and issue version 2 at rotation. One consumer misses
its update and still presents version 1. Its actual authorization fails, copied-byte
count is zero, and no output record exists. A common reconciliation compares consumer
and credential versions. The missing update is recorded and applied, and a fresh
copy succeeds. The failure is preserved. Separate probes confirm that retired
versions and undeclared delete operations remain denied after recovery. Quarter-end
review records the one declared identity, owner, grants, consumer version and
rotation history; it does not turn those comparisons into professional assurance.

The recipe must cover one UTC calendar quarter, with ordered rotation, reconciliation,
correction and a checkpoint on its final date. Rotation cadence and role requirements
are explicit local assumptions, not accepted enterprise credential policy. Canonical
site/service qualifications remain design/procurement pending, with no PHI processing
or asserted vendor connection. No network, actual host account, credential or model
is used. Publication is private and new-only; existing outputs cannot be resumed or
overwritten. The original source tree is never an output destination.

Separate Engine collection uses new audit state and temporary source grants, revoked
in a finally block. Because credentials and consumer configurations have actual
versions, collection inspects baseline, change, correction and quarter-end states;
final discovery alone would omit earlier versions. Source-record counts are not
identity counts or an enterprise completeness conclusion. Collection creates no
model, generated world, workpaper, finding, population acceptance or testing credit.
The current activity-plan V1 dependency contract is not extended by this module.

A `copied_dataset` source row's outer event/availability timestamps describe the new
copy operation. Its byte-identical payload retains the original backup dataset's
classification, source period and any original fields. Those inner historical
fields are not rewritten as current identity events. The provenance explicitly
marks `original_payload_unchanged` and links the new identity/control; the separate
copy-attempt record reports source hash, copy result and output reference. Consumers
must distinguish those two contexts when interpreting dates or control coverage.

## Actual local verification

Private artifacts are retained under
`enterprise/generated/audit-suite/company-nonhuman-identity-2026-09-14/`.
`VALIDATION.json` verifies 35 original versions, four exact upstream inputs, five
byte-identical dataset copies, a retained denied attempt without an output, and
unchanged upstream database bytes. The new company store initially had zero source
grants or collections. Original generator/reader/canon pins and explicit recipe
are retained with it.

`collection-v1/RECEIPT.json` records two new isolated Engine engagements retaining
18 and 17 versions respectively, including initial and updated credential/consumer
records. Every command replay was identical, future collection was denied, and all
temporary grants were revoked after collection. Original versions remain unchanged;
source collection journals correctly retain the performed access. `TESTS.xml`
records 14 focused passing tests. This evidence supports the bounded local mechanism,
not professional validation or production identity operation.
