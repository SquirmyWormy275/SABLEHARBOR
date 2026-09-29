# Persistent local configuration runtime

`company_configuration_runtime.py` runs a private data-only configuration target independently of audits, models and network services. It exercises a local retry-budget configuration; it does not configure the host operating system or deploy a company service.

The earlier change generator actually evaluated and changed an in-memory model. This runtime preserves a separate file target across processes. Reconciliation reads that file rather than reconstructing current state from a release record.

## Exact source admission

`initialize(destination, source_root=..., source_pins=..., as_of=..., target_id=...)` requires a new private destination and seven original native six-field pins: `baseline`, `configuration`, `build`, `tests`, `review`, `gate`, `rollback_plan`. Use the reviewed `change-release-a` source set. The API validates one original company/branch/cycle, native SHA and availability, exact dependency links, the package's configuration, schema and combined-limit test scope, matching local approval and allowed gate, and distinct operating author/reviewer identities. It retains the original bytes and a metadata digest; source bytes are rechecked before publication.

The source approval is a fictional local exercise record. It is not a newly obtained human approval, enterprise release authority, emergency exception, employment history, or accepted corporate policy. Rollback is an explicit operator action to the pinned original recovery-plan baseline; it does not invent a peer approval for that baseline. `SVC-developer` and selected facilities remain design references from the original source qualification.

## Commands

`inspect(runtime, expected_runtime_sha256=...)` returns the current revision, actual file SHA and decoded configuration. The runtime SHA identifies immutable configuration, not the changing database file.

`execute` accepts `expected_runtime_sha256`, `expected_revision`, `command_id`, `operation`, `expected_current_sha256`, `operator_id`, `event_at`, and `rationale`.

- `APPLY`: requires `expected_target_sha256` equal to the exact approved configuration. Reapplication is a separately recorded correction.
- `DRIFT`: requires an explicit `configuration` with the three positive integer fields. It is labeled an authored local change, without emergency-approval inference.
- `ROLLBACK`: requires `expected_target_sha256` equal to the original recovery baseline.
- `RECONCILE`: reads current bytes and records field differences against the pinned approved configuration, without changing those bytes.

Every operation retains before/after SHA, original pins, authored event time and separately measured real elapsed time. Comparison fields describe the **pre-operation** file, including on apply/rollback; run a new reconciliation for a post-operation observation. Comparisons use canonical typed values; booleans and floating-point values are rejected by the local target schema. No operation resolves a ticket or provides assurance credit.

## Persistence and failure boundaries

The company database contains immutable native operation/observation records, immutable command receipts, and an atomic current-file pointer/revision. A new file is written through anchored directory descriptors, flushed, fsynced and reread before the database transaction commits the native record, receipt and pointer together. A failed command may leave an immutable unreferenced file. It is not current and not a completed native operation. An interrupted attempt with such a file is not silently resumed: inspect the runtime and use an explicit new command ID if another attempt is authorized.

Exact committed replay returns its retained receipt after current integrity and operator checks. Changed command content or stale revision/current hash fails. A corrupt current file fails closed even if release records still describe the expected configuration. Original sources and old object files are never rewritten or deleted by this API. Native records use ordinary CompanyStore schema and immutable version triggers; no grants, collections, audit records or model state are created.

This is a trusted local operator API, not an authenticated application endpoint. Filesystem administrators can alter its private store; hashes do not provide an external signature. The database transaction is the authoritative current-pointer boundary; there is no claim of a globally atomic external filesystem snapshot or whole-period/enterprise coverage. The current slice supports one target and one pinned approved revision, not a generalized deployment pipeline or approval authoring workflow.

Tests cover actual apply/drift/reconciliation/correction/rollback, fresh-process reread, exact replay/CAS, wrong operator and malformed typed input, source cutoff/cross-branch rejection, corrupt current files, aliased output parents, file/directory flush failures and native-insert rollback.

Caller-owned mutable source pins and drift configuration are detached before validation and command fingerprinting. Upstream link versions require exact positive integers; Python boolean/numeric equality does not establish a version match. Registered source-system owners must match the original scoped operating roles. Each operation pins the executing module bytes separately from the initialization-time code pin and rechecks them before commit.

## Maintained local CLI

Use `python -m tools.audit_suite.company_configuration_runtime` with `initialize --configuration <private-json> --destination <new-runtime> --output <new-receipt>`, `operate --runtime <runtime> --action <private-json> --output <new-receipt>`, or `inspect --runtime <runtime> --runtime-sha256 <pin> --output <new-receipt>`.

Initialization JSON has exactly `source_root`, `source_pins`, `as_of`, `target_id`. Operation JSON is `{kind, parameters}`, where kind is one of the four operations above and parameters contain the matching explicit API arguments, excluding `operation`. The maintained CLI validates exact fields and publishes separate anchored private receipts. A committed operation with failed receipt publication must be inspected or exactly replayed into a new receipt directory; it must not be described as rolled back. The CLI reuses the private receipt writer in `tools/audit_suite/company_backup_runtime.py`, which belongs in the implementation source-pin inventory.
