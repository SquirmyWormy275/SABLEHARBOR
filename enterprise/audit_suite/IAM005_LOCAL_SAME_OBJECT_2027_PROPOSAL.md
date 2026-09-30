# One nonpersonal local IAM-005 human/service trace

This prospective fictional 2027 exercise uses one 59-byte nonpersonal local
object, `LOCAL-IAM005-TRACE-OBJECT`, with exact SHA-256
`6e4a4c6199c48f07bcbe4464bfb17f8abc1dd030ae167219ee36ba2e3278232f`.
The [source spec](iam005_local_same_object_spec_v1.json) fixes the bytes,
resource ID, inert service identity, local human principal, contact roles,
review due time and no-real-world limits. Separate `human/` and `service/`
CompanyStore databases hold the two ledgers; each contains an independently
hashed copy of those same bytes. This is one selected local fixture, not an
enterprise identity, customer, ePHI or service population.

The independently reviewed frozen documentary matrix (SHA-256
`e9477d2074bebce185e412a3ee7c424ded395c1a1128a7c918a94f6acbd1e327`)
and PASS review (SHA-256
`c4064f6217c0e7f69276adc71004d6da7971867ccf3d844a3e198145cec31ace`)
contain exactly five `SH-IAM-005` tasks per A/B side. Two have authored
clauses: approved emergency-mode ePHI availability/recovery and a human **and**
service identity trace across each trust boundary with unauthorized,
credential and privileged-path checks. The other three are generic
TOD/IMPLEMENTATION/TOE gates, with no authored clause. The producer verifies
their exact IDs, clause text and `NOT_STARTED`/`NOT_RUN`/no-credit state.
This local exercise can become bounded generic source-search context only;
**both authored clauses remain unsupported**.

The [control catalog](../../docs/controls/COMMON_CONTROL_CATALOG_v0.1.md)
defines IAM-005 as privileged/break-glass access; IAM-006, a separate control,
governs service accounts. The
[design procedure](../ccf/assurance/design_data/control_procedures.json) asks
for separately authorized privileged access, session activity, expiry and
review. Existing [privileged](PRIVILEGED_RUNTIME.md) and
[nonhuman](NONHUMAN_RUNTIME.md) local runtimes informed the exercise boundaries
but are **not** transplanted or represented as production sources. The
historical privileged runtime's current database bytes have drifted from its
earlier independent file pin after local journals; this exercise builds fresh
native ledgers from the exact tracked spec and makes no claim about that old
runtime's current reviewed bytes.

| Ledger and branch | Selected causal history |
| --- | --- |
| Human Clean | Local rule; finite lease; explicitly opened local session; exact-object read; timely revoke/session closure and distinct local-contact review. |
| Human Messy | The same successful read is followed by a post-expiry read attempt that returns zero bytes and remains retained; later revoke/session closure and late review leave a local timing exception. |
| Service Clean | Inert identity with exact read-only object scope; exact-byte read; integer credential version advances; stale-version attempt is denied; timely distinct local-contact review. |
| Service Messy | An excessive two-object request is denied before reading any bytes; a separate narrowing record precedes a successful exact-object read; rotation and stale-version denial follow; late review preserves an open timing exception. |

Every native version has event and availability timestamps plus the actual
CompanyStore import time, byte hash, source contact, prior source linkage,
canonical input pins and independent route pins. `AS-P007` and `AS-P008` are
source-pinned fictional contacts with pending appointment acceptance; their
local operations and review are neither authenticated human approval nor
qualified independent assurance. No usable secret, host account, production
trust boundary, external message, actual PHI, emergency ePHI use, complete
population or audit task credit is created. The active audit pair, tasks,
workpapers, Key and Atlas are untouched.
