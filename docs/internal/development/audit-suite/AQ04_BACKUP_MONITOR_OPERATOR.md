# Explicit backup due-job monitoring operator

`enterprise/audit_suite/company_backup_monitor.py` adds a bounded operational scan to the existing local backup runtime. The BCM002 design procedure in `enterprise/ccf/assurance/design_data/control_procedures.json` requires monitoring scheduled jobs, recording missed/failed runs, and reconciling protected datasets to inventory. This implementation observes only the explicitly declared local schedule; it does not supply approved RPO/RTO, BIA, corporate critical inventory, retention, isolation, continuous monitoring or independent review.

The scan runs independently of an audit. It reads existing immutable runtime definition, retained declaration, job versions and failure-ticket versions; no audit state, Key, model or expected-answer input exists. It is an explicit operator action, not a scheduler. Native records retain the runtime's exercise provenance and add the narrower `OPERATOR_TRIGGERED_LOCAL_BACKUP_MONITOR_NOT_CONTINUOUS_OR_DEPLOYED_MONITORING` qualification in their content.

## API and transaction contract

`inspect(runtime, expected_runtime_sha256=..., as_of=...)` reads one SQLite snapshot and returns its explicit visible job/failure-ticket membership and `jobs_sha256`. Exact native six-field pins, event/availability times and provenance digests are retained. The declaration supplies the due denominator; observed job rows never generate that denominator. The inspection does not append source records or authority journals.

`scan(runtime, expected_runtime_sha256=..., expected_revision=..., command_id=..., expected_jobs_sha256=..., as_of=..., recorded_at=..., operator_id=..., rationale=...)` requires the inspected membership digest and explicit configured local operator. The source cutoff cannot follow scan recording. Recording must follow the existing runtime's global business timestamp and compare-and-swap revision; future-dating a scan intentionally prevents later operations with earlier timestamps.

The adapter reuses `company_backup_runtime._execute` and `_insert`: system registration, native scan/observation/ticket insertion, command receipt and revision increment share the same `BEGIN IMMEDIATE` transaction. There is no second journal or independent monitor revision. Command IDs share the existing runtime namespace; exact replay returns the prior receipt without creating another scan. Changed replay parameters fail. Original declaration integrity is checked even on replay. Source-file hashes are recorded and rechecked before publication; these are source pins, not loaded-binary attestation.

Three systems are registered inside that same transaction, with the existing configured operator as local custodian: `monitor_scan`, `monitor_observation`, `monitor_ticket`. Existing conflicting ownership fails. Frozen portfolio registries need an explicit successor listing these systems; no registry is silently expanded and no source grant is created.

## Observations and ticket preservation

- Every declared slot due at the inclusive cutoff is reconciled to visible exact job versions. A due slot without a selected job generates a missing-declared-execution observation. This does not prove absence of evidence across the company.
- Every recorded failed job version generates a historical failure observation even when a later version succeeded.
- An exact existing native `failure_ticket.job_pin` is reused with its original status; that ticket's identity and metadata are included in the input digest. Ambiguous or inconsistent source-ticket linkage fails closed.
- A missing slot receives one deterministic monitor ticket. A failed attempt receives a monitor ticket only when no exact existing source ticket is available. Later scans append new observations and reuse the ticket; they do not silently close, resolve or overwrite it.
- A successful later operation changes the current reconciliation but never erases an earlier observation, ticket or failed original. Root cause, severity, BIA impact and independent review remain unassigned/unperformed.

The scan checks recorded source hashes and chronology. It does not reread copied files or rerun restoration, so it cannot certify current recoverability. Native records are retrievable through ordinary CompanyStore grants and time cutoffs. No real corporate operation, deployment, offsite recovery, continuous monitoring or whole-period effectiveness is claimed.

Tests use disposable genuine backup runtimes and cover exact existing-ticket reuse, missing-ticket deduplication, failed/retried history, native-batch rollback, stale source/revision/operator rejection, historical cutoffs, shared command collisions, declaration corruption on replay and standard native access/future denial. Actual private runtime execution remains a separately reviewed operator step.


## Trusted local command line

The existing `tools.audit_suite.company_backup_runtime` command exposes
`monitor-inspect --runtime PATH --runtime-sha256 HASH --as-of TIME --output NEW_PRIVATE_DIR`.
It publishes the read-only inspection through the same private, anchored receipt
writer as backup operations. Use its exact `jobs_sha256` and `runtime_revision`
for a reviewed `operate` action with `kind: MONITOR`. Parameters are
`expected_runtime_sha256`, `expected_revision`, `command_id`,
`expected_jobs_sha256`, `as_of`, `recorded_at`, `operator_id` and `rationale`.
The operator must match the existing runtime configuration.

Inspection alone creates no company scan or ticket. `operate` explicitly performs
the scan and publishes its request, result and checksum manifest outside the
source runtime. If publication fails after a committed operation, preserve the
runtime and request, then replay the exact action into a new private receipt
directory. A replay does not perform another monitoring scan. The existing backup
commands continue using the same incremented runtime revision.
