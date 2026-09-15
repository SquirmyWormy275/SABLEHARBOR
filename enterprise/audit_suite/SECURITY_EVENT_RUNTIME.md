# Persistent local security-event intake

`company_security_event_runtime.py` consumes existing qualified logging originals and records separate, explicit local workflow operations. It does not regenerate logging, perform network actions, create an audit, assert an attack or breach, or close an enterprise incident. The independent outage exercise remains separate.

## API

- `read_sources(source_root, source_pins, as_of)` returns exact selected rows and their metadata SHA. `source_pins` is a list of native `{company,branch,system,record,version,sha256}` objects. Selection must cover the complete bounded logging branch, including its independent publisher checkpoint and declared inventory. Native versions are positive exact integers. Metadata includes native identity, event/availability, origin and provenance, but excludes content and import time. This read is not permission to derive a replacement for an existing expected pin silently.
- `initialize(destination, *, repository, source_root, source_pins, expected_source_metadata_sha256, as_of, runtime_id, period_start, period_end, local_rules)` creates a **new** private company runtime. `local_rules` must explicitly equal exported `RULES`. The period is UTC, start-inclusive/end-exclusive. Returns `runtime_sha256`, revision `0`, and `state_sha256`. The initialized runtime contains no received subjects or performed responses.
- `inspect(runtime, *, expected_runtime_sha256)` verifies retained sources, native definition, state history and command receipts, returning current state and declared subjects.
- `execute(runtime, *, expected_runtime_sha256, expected_revision, expected_state_sha256, command_id, operator_id, event_at, action, payload)` uses exact compare-and-swap state/revision and command idempotency. Identical retry returns the retained result; changed input under an old command or stale state fails. The local operator must equal the retained scoped primary source owner.

| Action | Exact payload | Performed operation |
|---|---|---|
| `INTAKE` | `{subject_id}` | Adds that declared original to the persistent received set. |
| `TRIAGE` | `{subject_id}` | Computes the local classification from the pinned original decision/rule; no caller outcome. |
| `HANDOFF` | `{subject_id,person_id}` | Records explicit local routing to the retained operating-review contact, qualified as an exercise assignment. Required only for local response classifications. |
| `RECORD_ACTION` | `{subject_id,source_pins}` | Reads and rehashes the exact retained original bytes. Requires prior handoff and the subject original among the unique selected inspection sources. Records `company_remediation_performed=false`. |
| `RECONCILE` | `{}` | Computes missing intake, triage, required handoff and inspection against the independent declared denominator. Does not perform missing actions. |

The subjects are publisher events plus actual declared detection alerts. `EVENT-1` is a local publisher sequence identity, not an upstream native sequence. Alert subject IDs are `ALERT-` followed by the retained alert record ID. The source inventory/checkpoint determines expected events and detections; omitting supplied evidence does not shrink the denominator.

`BLOCKED` yields `INFORMATIONAL`; `ALLOWED` yields `NO_LOCAL_FOLLOWUP`; `OVERRIDE_USED` and a proved `LOCAL-COLLECTION-GAP` require explicit local follow-up. No numeric severity is invented. A's prevented attempt does not become a B override or fabricated alert. Existing ACK tickets are validated as historical acknowledgments, never treated as newly performed intake or completed incident response.

## Source and authority limits

The complete current producer branch is bounded to 8–32 exact originals and 4 MiB including UTF-8 provenance. Count alone is not acceptance: validation checks source systems, native gate copies, publisher sequence/hash chain, independent checkpoint membership, declared source identity, collected event equivalence, collector filters, coverage membership, alert correlations and acknowledgment backlinks/chronology. The selected physical logging rows are reverified. Original change-store identity/version is **publisher-declared**; its exact retained gate bytes and preserved producer label are checked, but this API does not query that separate original database. The runtime definition preserves this distinction and the exact selected metadata.

Input sources are read-only and rechecked before staged publication. Runtime output must be a new private directory outside the source. No grants, collection receipts or access history are copied. Source native content is retained byte-for-byte in private files; subsequent native operations refer to the immutable runtime definition and source metadata pin. The runtime uses an application-owned schema and append-only CompanyStore originals. State, operation, immutable state snapshot and command result commit in one transaction. A failed command rolls back; inspection checks current state against immutable native history.

AS-P008/AS-P007 are resolved from the actual scoped organization snapshot in current fixtures; the API does not hardcode their identity as permanent corporate authority. The retained local handoff is explicitly not a new corporate command appointment. The full organization source pins and implementation-file hashes are retained. Later implementation versions are execution provenance, not retroactive provenance of historical logging originals.

Every state retains `incident_closed=false` and `whole_period_coverage=false`. Successful source inspection is an actual byte-read operation, not company remediation, audit testing credit, professional review closure or acceptance of a corporate response plan. The runtime declaration cannot prove missing source systems or no-event intervals outside its original publisher scope. Separate fresh collection through existing owner grants is a later explicit activity; sealed producer capsules must not receive runtime journals.

## Validation

`tests/audit_suite/test_company_security_event_runtime.py` uses newly generated actual A/B temporary logging sources to exercise independent populations, source availability, causal transitions, preserved history/source bytes, replay/conflict, role restrictions, rollback/retry, private boundaries and malformed source predicates. Independent review tests live separately. No actual company source run is performed by this implementation task.

## Trusted CLI and receipt recovery

Run from the repository root with private, owned JSON inputs and new private output paths:

```bash
.venv/bin/python -m tools.audit_suite.company_security_event_runtime initialize \
  --configuration /private/initialize.json --destination /private/new-runtime \
  --output /private/new-initialize-receipt.json
.venv/bin/python -m tools.audit_suite.company_security_event_runtime operate \
  --runtime /private/new-runtime --action /private/action.json \
  --output /private/new-operation-receipt.json
.venv/bin/python -m tools.audit_suite.company_security_event_runtime inspect \
  --runtime /private/new-runtime --runtime-sha256 EXACT_DEFINITION_SHA256 \
  --output /private/new-inspection-receipt.json
```

Initialization JSON has exactly `source_root`, `source_pins`, `expected_source_metadata_sha256`, `as_of`, `runtime_id`, `period_start`, `period_end`, and `local_rules`. The CLI supplies the repository path (override with `--repository` only on initialization). An action file has exactly `{kind,parameters}`: `kind` is an action listed above; `parameters` contains exactly `expected_runtime_sha256`, `expected_revision`, `expected_state_sha256`, `command_id`, `operator_id`, `event_at`, and `payload`. Runtime/state pins come from the verified initialization or preceding result, not a guessed digest or a freshly substituted state after a conflict. Receipt format is `COMPANY_SECURITY_EVENT_OPERATOR_RECEIPT_V1`.

Receipts must be new private files outside the runtime/source trees. Runtime mutation and separate receipt publication are not globally atomic. `RUNTIME_CREATED_RECEIPT_NOT_PUBLISHED` means preserve the created runtime, hash its exact `RUNTIME.json`, and inspect it; never initialize over it. `OPERATION_COMMITTED_RECEIPT_NOT_PUBLISHED` means retain the exact original action file and replay **that unchanged action** into a new receipt destination. Do not replace its command ID, revision, state pin, timestamp or payload: that would be a new operation, not receipt recovery. Source/state conflicts require explicit review; they do not authorize automatic retry against newer state.
