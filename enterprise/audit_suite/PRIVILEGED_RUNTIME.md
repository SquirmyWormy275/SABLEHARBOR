# Local privileged-session runtime

`company_privileged_runtime` executes protected reads of one nonpersonal byte object. It creates no host accounts, credentials, network sessions, corporate approvals, grants, audit records or model calls. Its `AUTHORED_TRAINING_SOURCE` originals are explicitly qualified `LOCAL_PROTECTED_READ_SESSION_NOT_PRODUCTION_PRIVILEGE_OR_MANAGER_APPROVAL` and reference SH-IAM-005. A canonical coordination owner is not represented as appointed management or an independent professional reviewer.

Existing lifecycle code supports account/handle grant and revocation, nonhuman activity supports credential rotation and copies, and backup runtime has operation leases. They do not implement this separate persistent lease/session/action history. The new module reuses private original readers, CompanyStore schemas, native pins, the independent period declaration and atomic publication/transaction primitives.

## Admission

`initialize(destination, repository=..., source_root=..., source_pins=..., expected_source_metadata_sha256=..., declaration_root=..., declaration_pin=..., object_id=..., object_bytes=..., max_lease_seconds=..., local_rule_basis=..., as_of=...)` creates a new private runtime. Source/declaration/output roots must be canonical, private and disjoint from the output; reading an original never constructs a CompanyStore there.

Eligibility accepts exactly the existing fictional mover HR, directory and application native source contract. Supply exact native six-field pins and the selected metadata digest from `company_lifecycle_activity.read_inputs`. Subject/cause, explicit authorization ID and approved right, enabled state, distinct source approver/provisioner, native registered owner identities, event/availability order and latest-visible selected versions must agree. This is eligibility from a narrow local source snapshot, not independent evidence of a real employee, enterprise account completeness or corporate privileged-access approval. Other source schemas require an explicit future adapter; they are not guessed from prose.

The separately created SH-IAM-005 operating-period declaration identifies exactly the subject and object, its local owner, and explicit reconciliation occurrences. Initialization must precede the period. The maximum lease duration is an explicit local exercise rule of at most one day, not an accepted corporate policy. Protected bytes are capped at 64 KiB and retained as one immutable original. No personal/production data should be supplied to this local fixture API.

## Operations and actual boundaries

`execute(runtime, expected_runtime_sha256=..., expected_revision=..., command_id=..., action=..., payload=..., actor_id=..., event_at=...)` accepts only:

| Action | Exact payload |
| --- | --- |
| ISSUE_LEASE | lease_id, principal_id, object_id, right, purpose, expires_at |
| OPEN_SESSION | session_id, lease_id, principal_id |
| READ_OBJECT | session_id, principal_id, object_id |
| REVOKE_LEASE | lease_id, reason |
| EXPIRE | empty object |
| RECONCILE | occurrence_id |

Lease/revoke/expire/reconcile require the declared local operator ID. Session/read actor must equal the stated principal; this trusted local operator API records explicit actor assertions and is not an internet authentication endpoint. A lease cannot widen the pinned approved source right, subject or object. Lease validity is `[issued_at, expires_at)`. Session opening or reading without a matching effective lease produces a retained DENIED observation. A successful read actually retrieves the bounded native object bytes and computes their hash/length. No arbitrary file paths or shell commands are accepted.

Expiry denies access immediately by time comparison. An explicit EXPIRE operation records state cleanup; until then reconciliation exposes expired but unclosed sessions. Revocation closes matching sessions. Later source supersession blocks new leases/access, while explicit revocation/expiry/reconciliation and inspection remain possible against intact original eligibility pins. Mutation of those exact original bytes or metadata still fails closed. Only supersession of the explicitly selected source records is checked; no unseen enterprise identity discovery is claimed.

All operation originals, receipt, local state and revision commit in one SQLite transaction. Exact command replay preserves original output and performs no second operation. Changed parameters, stale revision, backward event times, receipt/native/state corruption and source changes at the final check reject. Original operation history is retained; no successful retry erases a failed/denied attempt. Source reads and consumer writes are separate databases, so final source checks are per-source checks, not a global atomic snapshot.

Inspection and replay recompute local state/observations from every retained operation and verify native bytes against receipts before returning. Bounds are 256 commands, 512 KiB per native original and 32 MiB aggregate native content. `inspect(runtime, expected_runtime_sha256=..., as_of=...)` supports a current-or-later cutoff only, and compares recorded reconciliation occurrences to the independent due schedule. It does not mark ledger assertions executed, close a quarterly control, accept a population, or claim professional review. Local reconciliation remains an operator operation, not independent assurance.

All paths, routing and original pins are private. The public CompanyStore discovery/read/collect APIs can collect these native originals using ordinary explicit grants; the runtime itself creates none. Existing append/lease/identity implementations are unchanged. No actual private runtime is generated as part of this module's tests or documentation.


## Retained implementation and native custody

New runtime definitions retain a separate `code_sha256` map for this module and
its directly used maintained source, declaration, organization, parser, storage,
publication and integrity helpers. Initialization checks these pins again before
publication; inspection and every operation, including exact retry, compare the
retained map to current implementation bytes. Changed implementation requires an
explicit successor runtime. Historical organization-document `source_sha256`
pins remain provenance of the original scoped assignment: later governance edits
are not silently treated as either retroactive approval or a code-pin change.

The definition, protected object and every operation are checked against their
expected native identity, content, event/availability timestamps, origin,
provenance, command ID and input digest. Inspection also independently reperforms
the recorded operations and compares current state with their immutable chain.
Actual import timestamps remain separately retained recording metadata; they are
not reinterpreted as operating event times.

SQL count and byte-size preflights run before loading native originals, native
metadata, command receipts or current state. Receipts and state are limited to
512 KiB per row, with a 32 MiB aggregate receipt bound; additional bounded metadata
checks precede row retrieval. The writer enforces the same receipt/state quotas
transactionally, so a successful operation remains inspectable. These checks do
not grant access or authenticate an asserted operator outside the trusted local
runtime interface.
