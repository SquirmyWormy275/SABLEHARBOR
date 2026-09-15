# Explicit local operating-period ledger

`enterprise/audit_suite/company_operating_period.py` adds an independent due-occurrence ledger. A plan declares the local inventory and every scheduled occurrence before the period. The ledger retains missing due occurrences, explicit skips and later source-backed operator assertions. It does **not** execute the business operation represented by an assertion. An `EXECUTED` disposition is an operator assertion supported by selected native records, not a software conclusion about their business meaning or effectiveness.

The first version supports one company/branch per ledger. It does not merge the A/B portfolios, infer daily frequency, appoint personnel, claim deployed services, or declare an enterprise operating year complete. The declared owner must already own at least one selected canonical control. This is local custody of the exercise ledger, not a new accepted corporate appointment.

## Maintained interface

- `create_period(store, *, repository, plan)` initializes an existing, empty private CompanyStore. No grants, collections or audit are created. The declaration is immutable and pins organization/procedure sources and selected maintained module files. These source files are checked again before declaration publication; this is not loaded-binary or complete Python-dependency attestation.
- `record_occurrence(store, *, period_id, occurrence_id, expected_version, command_id, recorded_at, disposition, sources, reason, predecessor_refs)` appends at most32 versions per occurrence. Stable command replay retains the original receipt; changed input or stale expected versions fail.
- `report_period(store, *, period_id, as_of)` reads the declaration and visible occurrence history in one SQLite snapshot. Reporting does not modify source history. The report checks retained ledger hashes and explicitly does not rediscover or revalidate current upstream stores.

The exact plan fields are `period_id`, `company_id`, `branch_id`, `owner_id`, `control_ids`, `period_start`, `period_end_exclusive`, `declared_at`, `inventory`, `local_basis`, and `schedule`. Inventory is one to64 explicit `{id, description}` items. Schedule is one to512 explicit `{id, inventory_ids, control_id, due_at, window_start, window_end_exclusive, depends_on}` occurrences. Dependencies reference earlier schedule entries. Explicit-offset timestamps normalize to UTC; occurrence windows are half-open and inside the declared period. A due instant may equal the exclusive window boundary. Missing occurrence status starts at that due instant. No cadence is derived from a broad period label.

Each source group contains `{source_store_id, root, refs, expected_metadata_sha256}`. `refs` is two to eight exact native `{company, branch, system, record, version, sha256}` records; at most four groups are accepted. The existing bounded lifecycle reader verifies exact bytes and caller-pinned selected metadata twice before append. All records must have known event and availability times at or before recording. Physical roots must be distinct and outside the ledger tree; aliases remain prohibited. Company records retain the source label, an opaque location digest and exact metadata, never raw filesystem paths. The location digest binds routing, not producer authenticity or source independence. Source validation is per source and transaction, not a global snapshot.

For `EXECUTED`, `predecessor_refs` must contain exactly one `{occurrence_id, version, sha256}` pin for every declared dependency, selecting a current prior source-backed assertion available by the recording instant. There is no automatic latest selection. Historical replay may still point to its originally pinned predecessor after a later correction. A new action must explicitly inspect and pin the current predecessor. `SKIPPED` requires empty sources and predecessor pins, allowing a missing or skipped dependency to explain why a dependent occurrence was skipped. The original declared dependency list remains visible without claiming predecessor execution.

Recording lateness (`BY_DUE`/`AFTER_DUE`) is distinct from the retained native event and availability times. Late record capture does not independently establish late underlying operation. Source-backed assertions do not prove that every selected record concerns the declared inventory/control; that requires a typed business adapter and substantive reconciliation.

The maintained create/record APIs serialize cooperating ledger writers with a nonblocking private database file lock and retain CompanyStore optimistic version checks. This does not lock external source stores or authorize arbitrary direct database writes. Reports are bounded to64MiB of retained ledger content. Existing declarations, skipped attempts, corrections and predecessor references are never rewritten.

## Acceptance and next boundary

The trusted local CLI is `python -m tools.audit_suite.company_operating_period`:

```text
create --plan /private/plan.json --destination /private/new-company-ledger --repository /path/to/repository
record --store /private/new-company-ledger --action /private/action.json
report --store /private/new-company-ledger --period-id PERIOD-ID --as-of 2028-01-15T00:00:00Z --destination /private/new-report
```

Plan/action files must be private, bounded, strict finite JSON objects. Creation
publishes a new private store only after validation. Record and report commands
require an existing database and do not initialize missing stores. A report uses
a read-only connection and publishes `REPORT.json` plus a hash manifest outside
the source store. Its maintained-file pins include distinct repository-relative
paths for the core and CLI modules and active parser/publication helpers; changed
pins prevent publication. These pins are not loaded-binary attestation. Reports
never overwrite earlier receipts or create audit state.

Tests exercise real preexisting mover records, independent due counts, timezone equivalence, skip followed by late source assertion, immutable originals, exact replay, stale parent/version rejection, wrong-branch/hash/metadata/future/duplicate records, and invalid schedules without partial registration. Independent review adds source-routing, skipped-dependency and parser cases.

The maintained [access review continuation adapter](../../../../enterprise/audit_suite/ACCESS_REVIEW_CONTINUATION.md) now produces a later local review from the exact original inventory and completed-removal state/probes. The recorded local exercise generated three native company originals, collected those originals into a separate technical engagement, and then recorded one source-backed ledger assertion. The independent two-occurrence denominator still reports one missing due occurrence. The original declaration, earlier report and upstream originals remain preserved. Ledger creation itself did not manufacture the review. Business-population acceptance, procedure execution, sufficiency, independent assurance and coherent whole-company-year conclusions remain unperformed.

The [persistent backup runtime](../../../../enterprise/audit_suite/BACKUP_RUNTIME.md) is a second typed adapter: it consumes an exact backup/restore declaration and executes local byte operations against persistent datasets. It reconciles independent declared jobs with native attempts and preserves missing occurrences and failures. Its operator workflow remains separate from audit collection and professional assessment.
