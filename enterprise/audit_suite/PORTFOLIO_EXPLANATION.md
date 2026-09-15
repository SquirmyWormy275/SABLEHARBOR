# Protected portfolio source snapshots

The existing local `explanation_binding.bind_snapshot` API now accepts portfolio
sources when each explicit reference carries all six native identity fields plus
`source_store_id`, `source_system_alias`, and `registry_sha256`. These fields must
resolve to the exact physical company/branch/system in the frozen portfolio profile.
An identical native ID/version/hash in another component is a different source.
Existing concrete-source snapshots and unbound instructor libraries are unchanged.

Capture requires current scoped instructor membership and independently granted
source-operator access. The audited actor's permission, source availability, latest
visible version, and retained audit-copy hashes are captured separately. A revoked
source grant does not retroactively erase an already-retained audit copy; a future
version is explicitly unavailable to the actor even if the operator can inspect it.
Each component uses its own read transaction and access-event watermark. Aggregate
native bytes are bounded to64MiB and references to256. Final route/access checks and
staged publication prevent a failed capture leaving a usable partial snapshot.
There is no global transaction across source stores, and capture-time status is not
a permanent entitlement or proof of inspection/understanding.

Portfolio snapshots add `snapshot_isolation: PER_COMPONENT_NOT_GLOBAL` and a
`component_snapshots` list with capture times, aliases and access-event watermarks.
They retain exact engagement revision, scope, state/history hashes, existing source
bytes, and independent authored interpretations. No model, automatic grading,
professional conclusion, or newly authored truth is required. Empty issue and
expectation lists are supported for a technical source-binding demonstration.

The existing protected bound-snapshot and comparison routes keep their response
contract. They require instructor membership; review-only and learner members cannot
read them. Portfolio snapshots additionally validate current routing pins before
return, and comparisons use physical route identity as well as native source fields.
Changed routing fails closed. Changed audit scope yields an explicit historical
context mismatch rather than treating old expectations as current. Archive access
continues to depend on instructor authority, not the audited learner retaining a
live source grant. All captured grants/visibility remain historical labels.

A local operator may configure a new immutable snapshot through the existing
private instructor binding config after reviewing its manifest. This implementation
does not change a live registry, grant, service binding, or old archive. The actual
read-only demonstration under
`enterprise/generated/audit-suite/portfolio-instructor-2026-09-14/` captures two
existing reference-v3 sources into a new private output; it authors no issues or
expected conclusions. Tests additionally cover colliding native identities,
future/retained distinction, revocation during capture, changed routing, instructor
route access, interrupted publication, and historical scope mismatch.

## Optional exact authored procedure links

New authored expectations may include `task_ids: ["exact-scoped-task-id"]`.
The operator binder validates each ID against the captured engagement's current
control and boundary scope and the controls explicitly referenced by that
expectation's issues. Explicitly non-current task applicability is rejected.
A task's recorded `NOT_APPLICABLE` outcome is preserved as an outcome; it does
not silently remove the task or substitute for scope validation. No task ID is
inferred from procedure prose, control titles, or workpaper text.

Older expectations omit this optional field and retain their original snapshot
bytes and schema. Comparison reports `task_mapping_status: UNMAPPED` for them
(or an explicit empty list). New links are reported as `authored_task_ids` and
revalidated against the explicitly selected historical state. Invalid historical
scope references are marked `UNRESOLVED_IN_SELECTED_SCOPE`, retaining the authored
IDs without associating current work.

`task_linked_workpaper_versions` is separate from the existing source-linked
inventory. Each entry records the exact workpaper ID, version, version SHA,
intersecting task IDs and exact bound-source artifact IDs, plus recorded authorship
and conclusion. The source intersection can be empty: a procedure reference alone
does not establish source inspection. Later workpaper versions do not inherit a
procedure association unless that version explicitly records its ID. These links
neither grade performance nor assert that the recorded work implements the
expectation, is sufficient, or has been professionally accepted.
