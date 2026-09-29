# Local worker lifecycle sources

`company_lifecycle_activity.generate_pair(new_destination, repository=...,
source_root=..., recipe=LifecycleRecipe(...))` creates two private independent
branches for SH-IAM-001/002/004. It creates no engagement, source grant, company
employment amendment, vendor connection or deployed account. Existing destinations
are rejected; there is no resume or overwrite. IAM005/006 remain unexercised.

The recipe names a separate `EXERCISE-` worker, an existing sponsor, two neutral
branch IDs, ordered request/start/expiry/checkpoint/correction times and an explicit
local requirement. The worker's fixed-term contract is fictional. Canonical People
and IAM contacts remain proposed exercise custodians. SAP SuccessFactors, Okta and
IBM Security Verify are the selected design direction, not the origin of these
local JSON records or an assertion that those systems are deployed.

`LifecycleSourceRef(company, branch, system, record, version, sha256)` identifies
an original. `read_inputs(source_root, source_refs)` returns only the declared two
to eight rows and a hash of their complete retained metadata. The required
`source_versions_sha256` is this selected-set hash, not a whole-store hash. Source
rows must be exact, available before the request, from one company/branch, and
correlate the existing sponsor's personnel and enabled directory records. An optional
application record may be included. These records establish a local reference
identity, not authority to hire or terminate a canonical employee. Copies preserve
exact bytes in `upstream/`; SOURCE_RECEIPT retains their metadata, physical source
identities and hashes. Reads use a bounded read-only SQLite transaction, with a
second exact check before publishing. A private source remains unchanged; no grants
are needed by this trusted local operator API.

Both branches use the same request, bounded role catalogue, resource-owner approval,
channel inventory and expiry inputs. A data-only state machine creates the identity,
adds only the approved read right, and records actual before/after handle states.
The declared local application caches its session independently of directory status.
At expiry one branch revokes all six channels; the other omits that session.
Checkpoints execute the same probes against each actual state. The remaining ALLOW
result generates a follow-up request, followed by a revocation and new DENY probes.
Original checkpoint records remain immutable. No branch name is used as a finding
or an automatic audit conclusion.

The simulated handles are identifiers and booleans, never real credentials. Local
correlation is not real-world identity proofing. The exercise covers only its six
explicit channels and one worker, not enterprise completeness or professional
control effectiveness. It does not assign Alexandria information authority.

The separate paired Engine collection test uses new audit state, exact issued PBC
requests to the actual registered system custodians, source discovery, future-date
denial and idempotent exact collection. Temporary source grants are revoked in a
finally block. It grants no testing credit and generates no model response or world.
The current activity-plan V1 change-source dependency contract is unchanged; this
new operator API must not silently be routed through that contract.

## Retained local verification

The dedicated private run is
`enterprise/generated/audit-suite/company-lifecycle-2026-09-14/`.
`v1/` contains 24 original lifecycle records across ten branch/system registrations,
plus only three explicitly selected upstream originals. `VALIDATION.json` pins the
actual generation and verifies zero initial grants/collections and unchanged upstream
SQLite bytes. `collection-v1/RECEIPT.json` records the separate two-engagement
collection: twelve original records per branch, no model/world generation or testing
credit, and all temporary source grants revoked. Source versions are unchanged;
the lifecycle source access journal correctly records the collection and revocations.

The initial actual generation receipt is preserved. A subsequent private-reader
review added source inode/permissions/ctime rechecks and actual UTF-8 byte quotas.
`REVIEW_TESTS.xml` records 18 focused passing tests; `REVIEW_VALIDATION.json` verifies
the exact actual input rows with the current reader and records both old generation
and current code pins. It does not falsely relabel the earlier generation as a
new run. No existing audit engagement, source branch, or live service was changed.
