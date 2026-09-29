# Explicit local recovery-period runner

`company_recovery_period` coordinates existing private configuration and backup
runtimes. It does not initialize company systems, generate an audit, grant access,
select a framework or claim an operating year. The scenario is a declared local
byte workflow. Native producer/consumer company, branch and service references
remain distinct; component roles do not assert equivalent legal entities or
shared deployed infrastructure.

## API

- `create(new_destination, plan=plan)` validates a detached bounded plan and the
  explicitly pinned opening states, then creates a private journal. Returns
  `runner_sha256`, `revision=0`, `status=READY`.
- `inspect(root, expected_runner_sha256=pin)` reads the hash chain without company
  operations. Returns current journal revision, completed step IDs, an exact
  pending intent if present, declared omissions and status.
- `execute_next(root, expected_runner_sha256=pin, expected_revision=n, step_id=id)`
  performs only the named next step. It requires no pending intent.
- `retry_pending(root, expected_runner_sha256=pin, expected_revision=n,
  intent_sha256=exact_inspected_pin)` explicitly retries the already retained
  command. It never recaptures parameters, chooses latest records or rebases.

Journal revisions count events: INTENT plus RESULT normally advances by two.
A step whose operation committed but whose outer result was lost has one durable
INTENT. Inspect it, then explicitly retry the same envelope. Native command
idempotence returns the original result without duplicate company operations.
Do not delete/recreate the journal or rerun the plan from the beginning. Opening
state checks occur at creation and before the first intent, not during retry of
an already started plan. Later legitimate runtime state does not invalidate an
exact historical replay, although every maintained operation retains its current
integrity checks.

## Immutable plan

The schema is `LOCAL_RECOVERY_PERIOD_PLAN_V1`, with exact fields:

- `id`, `period_id`, `format`.
- `bindings.configuration`: `root`, `runtime_sha256`, opening `revision`,
  `current_sha256`, and original native `definition_pin`.
- `bindings.backup`: `root`, `runtime_sha256`, opening `revision`.
- `omissions`: explicit `{occurrence_id, reason}` entries.
- `steps`: one to 64 `{id,kind,parameters,refs,expected_pins}` objects.

Roots are absolute private existing paths, disjoint from each other and the new
journal. The backup definition supplies the independent period and due schedule.
Every declared occurrence must be represented by BACKUP/RESTORE or explicitly
omitted, never silently dropped. Non-monitor commands must be within the declared
half-open period; a later monitor can observe the period using an explicit cutoff.
An omission is authored intent, not a source ticket or a performed operation.
The actual monitor and reconciliation determine missing due occurrences.

Kinds are exactly APPLY, EXPORT, ADMIT, LEASE, BACKUP, RESTORE, MONITOR. `PARAMS`
in the maintained module lists exact parameter sets. They match the corresponding
maintained APIs except runtime root/definition SHA, which come from the immutable
binding. Optional prior pins are supplied explicitly as null. Revisions and
command IDs are explicit and consecutive per component; command IDs cannot be
reused by another plan step. No arbitrary Python imports, SQL, expressions,
functions or result-supplied paths are supported.

EXPORT and ADMIT require their exact expected native output pins in
`expected_pins`, keyed respectively `native_pin` and `source_pin`. Optional
other expected output pins must match a supported native field. Content hashes
for deterministic dataset, lease and copied-object bytes can be computed from
those exact bytes; do not synthesize measured job receipts to predict hashes.

`refs` supplies typed native parameters in place of `parameters` entries:

```json
{"source_pin": {
  "step_id": "opening-export",
  "field": "native_pin",
  "expected_pin": {"company":"...","branch":"...","system":"...",
                   "record":"...","version":1,"sha256":"..."}
}}
```

Only preceding completed, native-verified outputs may be referenced. The runner
rechecks the selected native original before freezing it into the consumer intent.
For job hashes containing measured elapsed time, the one explicit capture form is:

```json
{"prior_attempt_pin": {
  "step_id": "first-copy",
  "field": "job_pin",
  "expected_identity": {"company":"...","branch":"...","system":"backup_job",
                        "record":"...","version":1},
  "sha256_policy":"CAPTURE_FROM_VERIFIED_PRODUCER_RESULT"
}}
```

This form is restricted to `job_pin`. It captures the verified completed producer's
actual hash once; it is not a predeclared expected hash, an independently approved
outcome or a lookup of latest. The entire resolved native six-field pin is retained
in the durable consumer intent.

ADMIT requires `metadata_capture=CAPTURE_EXACT_ONCE`: the completed selected
configuration original and definition are inspected, and their exact derived
routing identity/metadata digest are frozen into the intent. This is labeled
`CAPTURED_AFTER_OPERATION_NOT_PREDECLARED`. The admission API independently verifies
those pins when invoked or replayed. MONITOR requires
`jobs_capture=CAPTURE_EXACT_ONCE`; it checks the expected runtime revision and
freezes the exact inspected membership digest, labeled as captured at intent.
Neither capture silently substitutes a later value on retry.

## Durability and verification

The runner has a private SQLite append-only hash-chained journal, with a cooperating
process file lock and FULL synchronous intent commit before an external runtime
call. Plan bytes and selected maintained source-file hashes are pinned; changed
source files require a reviewed successor/frozen checkout, not silent rebinding.
These hashes do not attest loaded binaries or all Python dependencies. Every read
validates strict journal shapes and reconstructs the retained intent from the
immutable plan, exact earlier outputs and frozen capture fields. Completed results
are rechecked against their native command receipts and originals before another
step or a COMPLETE response. Rehashing a changed rationale or false result revision
does not authorize a different operation. SQLite connections close explicitly on
both successful reads and errors.

After an operation, the exact returned receipt must equal the native runtime's
retained command receipt. Its revision and native output bytes/timestamps are
verified, and expected output pins must match. Only then is RESULT appended. Native
runtime and outer journal transactions are separate: a receipt-validation,
publication or interruption error can leave a committed operation and pending
intent. That is not rollback. A failed backup job is a real recorded result and
can be followed by an explicit correction; absent copy objects are not fabricated.

`COMPLETE` means all planned commands have retained results. It does not mean all
due jobs were performed or restored bytes were suitable. The independent declared
omissions, failed attempts, comparison differences and OPEN tickets remain in the
native source systems. Period/enterprise completeness, approved BIA/RPO/RTO,
professional review and audit testing credit are not inferred.

Limits are 64 steps, 128 journal events, 512 KiB plan, 1 MiB per event and 16 MiB
journal content. The operator must inspect an interrupted file-copy attempt; the
runner does not clean orphan files, invent a new command ID or automatically skip
an unrecoverable step.

The genuine fixture in `tests/audit_suite/test_company_recovery_period.py::period`
shows deterministic native export/lease/object pins, cross-runtime dataset
admission and a missing due occurrence. Tests also cover committed-producer
interruption, explicit exact retry, captured measured-job correction lineage,
code/opening-state changes, locking and malformed plans. No actual company or
audit operations are run by these temporary-fixture tests.
