# Persistent local backup byte operations

`company_backup_runtime` executes bounded local copies and restores before any audit exists. Its expected occurrences come from one exact immutable `company_operating_period` declaration. It introduces no competing cadence, inferred BIA target or calendar expansion. The earlier two-checkpoint backup generator and its capsules are unchanged.

## Initialization

```python
initialize(
    destination,
    repository=repository,
    declaration_root=period_store,
    declaration_ref=native_six_field_pin,
    bindings=[{"occurrence_id": "BACKUP-01", "dataset_id": "DATA", "operation": "BACKUP"}],
    datasets=[{"id": "DATA", "format": "JSON_RECORDS"}],
    service_id="SVC-compute",
)
```

The declaration uses the existing period-plan schema. Every slot must bind exactly once: BACKUP to SH-BCM-002 or RESTORE to SH-BCM-003. Each slot identifies one declared dataset; all declaration inventory items require a format binding. Mixed unrelated-control schedules are unsupported in this first adapter. Supported formats are `JSON_RECORDS` (one object containing a `records` array with unique string `id` fields) and `BYTES`.

The new private runtime contains an ordinary CompanyStore database, immutable definition/declaration files, and private copy-attempt directories. Its initialization receipt returns `runtime_sha256`: the immutable configuration identity, including a unique runtime ID. It is **not** the changing database byte hash. Commands and reports verify this configuration against its original native definition row. The source period ledger is read-only and is not automatically updated with execution assertions.

The retained definition pins the original declaration, its physical-location digest, dated operating contacts, service and runtime-site sources. Management review contact is separate from the restore operator; recording that contact does not claim review occurred. Site planning references do not assert deployment, offsite recovery or PHI processing.

## Explicit commands

Every mutation takes `runtime`, `expected_runtime_sha256`, `expected_revision` and `command_id`. Revisions start at zero after initialization. All business timestamps require explicit offsets and new commands cannot move backward in business time.

- `append_dataset(..., dataset_id, content: bytes, expected_sha256, event_at, previous_pin=None)` retains exact original bytes. A replacement version requires the exact latest native pin.
- `record_lease(..., operation, enabled: bool, valid_from, expires_at, event_at, previous_pin=None)` records local adapter permission for BACKUP_WRITE or RESTORE_READ. The half-open validity window and latest available lease are enforced by the adapter. These are local synthetic leases, not cloud credentials or physical isolation controls.
- `run_backup(..., occurrence_id, source_pin, lease_pin, attempted_at, rationale, prior_attempt_pin=None)` executes the chosen declared occurrence. The source must be the latest available exact dataset version at that instant.
- `run_restore(..., occurrence_id, backup_pin, comparison_source_pin, lease_pin, attempted_at, rationale, prior_attempt_pin=None)` restores an explicitly selected historical backup. The comparison source must be the explicitly pinned current dataset at the operation instant. Selection rationale is operator supplied; no risk or criticality rationale is generated.

A native pin is exactly `{company, branch, system, record, version, sha256}`. Returned receipts identify new dataset/lease/job/object pins and the new runtime revision. Prior-attempt pins preserve correction lineage. Changing an input, revision, timestamp or rationale under an existing command ID is rejected; exact replay returns its historical receipt without rerunning the copy.

## Actual operations and failure history

A backup writes actual dataset bytes to an exclusively created controlled path, flushes the file and directory, rereads it and compares its hash and bytes. A restore reads the persisted backup file, verifies it against the exact retained original, and writes/rereads a separate restore file. Corrupted or missing backup files do not fall back silently to the native database blob.

Copy elapsed seconds are measured using the monotonic host clock. They cover the local copy, durability and reread operation only. Authored business event timestamps and checkpoint age are separate fields; no fabricated wall-duration or production RTO measurement is reported. Restore content reconciliation computes missing, unexpected and changed JSON records, or byte equality for opaque data. COMPLETED means the local copy operation completed: discrepancies remain explicit and do not become a passing control test.

An unavailable local lease produces a FAILED native job and failure ticket, with no copied object. A corrected lease and explicit retry create new versions and preserve original failures. Missing due jobs remain absent observations until an operator actually acts; a report never invents failure tickets or execution records. Existing tickets are not automatically closed by a later successful copy.

Native objects, job/ticket rows, command receipt and runtime revision commit together in one SQLite write transaction. This does not use separately committed CompanyStore append calls. Copy files precede that commit. An interruption can leave a private `INTENT.json` and incomplete or uncatalogued bytes, but cannot publish a completed native job without its object. Reusing that interrupted command directory fails closed; inspect it and issue an explicit new command. There is no automatic resume, deletion or orphan cleanup. An error after a committed receipt is recovered by exact command replay.

## Read-only reconciliation and limits

`reconcile(runtime, expected_runtime_sha256=..., as_of=...)` reads the original declaration and one scoped native job snapshot. It reports declared and due counts, missing due occurrences, failed/latest completed copy states, complete historical attempts and prior failure counts. Expected membership comes exclusively from the declaration; it is not reconstructed from job rows. Its completed-copy count is not evidence sufficiency or approved population acceptance. Reports do not perform fresh restore tests or change the source ledger, runtime records, grants or audit state.

Limits: 64 datasets, the existing declaration's 512 slots, 16 MiB per native record/copy, 512 MiB total retained native bytes, 20,000 source rows, and 10,000 records per JSON dataset. No network/cloud execution, deletion/retention expiry, encryption claim, production isolation, approved BIA/RPO/RTO, operating review, audit, model call or whole-period effectiveness conclusion is implemented.

Focused tests exercise actual copied/restored bytes, expiry failure, correction history, explicit source replay, independent due census and file/batch interruption boundaries. Independent review tests cover configuration/source isolation and native-source consumers.

## Local operator workflow

Run `python -m tools.audit_suite.company_backup_runtime` from the repository:

```text
initialize --config PRIVATE.json --destination NEW_RUNTIME --repository REPO --output NEW_RECEIPT
operate --runtime EXISTING_RUNTIME --action PRIVATE.json --output NEW_RECEIPT
reconcile --runtime EXISTING_RUNTIME --runtime-sha256 CONFIG_SHA256 --as-of OFFSET_TIME --output NEW_RECEIPT
```

Initialization configuration has exactly `declaration_root`, `declaration_ref`, `bindings`, `datasets` and `service_id`. An action has exactly `kind` and `parameters`. Kinds are DATASET, LEASE, BACKUP and RESTORE; parameters match the corresponding functions above. DATASET takes a private `content_path` instead of inline content. Every action carries its expected configuration hash, revision and command ID. Inputs use bounded, strict JSON; all paths are absolute private paths without aliases.

Each new receipt directory contains REQUEST.json, RESULT.json and a hash manifest. Receipt paths must be outside the runtime; initialization receipts also remain outside the declaration store. The operator pins the receipt parent directory before acting, rechecks it and anchors writes to its open directory descriptor. This implementation uses Linux's `/proc/self/fd` view.

A command that records a failed backup exits successfully with `status=RECEIPT_WRITTEN` and `result_status=FAILED`. Inspect the result status; a successfully written receipt does not mean a successful backup. If publication fails after a committed command, `OPERATION_COMMITTED_RECEIPT_NOT_PUBLISHED` instructs exact action replay with a new output directory. The native command journal prevents duplicate operations. If initialization completed but its receipt publication failed, `RUNTIME_CREATED_RECEIPT_NOT_PUBLISHED` requires preserving the runtime, inspecting RUNTIME.json and using its exact file SHA256 for reconciliation. Initialization cannot be replayed over an existing runtime. Neither recovery deletes company history.
