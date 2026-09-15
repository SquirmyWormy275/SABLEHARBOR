# Company edition to existing audit portal

Record date September 15, 2026 UTC. This contract supplies public company originals to
the existing workstream; it does not create a competing portal or company schema.

## Ownership and observed source

The local `SABLEHARBOR-audit-suite` worktree, branch `build/audit-training-suite`, had
running company-source servers and uncommitted activity/access changes at discovery.
Its observed committed source was `548cb5d2be82ec11877e298c2c8d00aa1e555b7f`.
The closeout does not edit that worktree, its private data or live servers. The owner confirmed this is the active portal workflow. Reserved paths are recorded
in REGISTER.json; no overlapping portal edits are required by this input work.
The source module is a concurrent dependency, not accepted main by implication.

A later read-only refresh observed portal head
`0afa29a15af5b345a4929a9324cb8a58f2582641`. Its committed `company_store.py` is
byte-identical to the rehearsal pin (SHA-256
`38a1aebcebde53051e306465dc2d807a3cd0e60fb8cc974da2235fa268c88292`). The portal
has continued developing assistance and backup-monitoring workflows. That work
remains with its owner; this source compatibility check does not certify those
additional workflows or inspect their private live records.

## Existing schema and bounded import

`tools/company_closeout/portal_rehearsal.py` loads the exact Git-committed existing
`enterprise/audit_suite/company_store.py`. It uses `register_system` and
`append_version` with existing origin `REPOSITORY_SYNTHETIC_DOCUMENT`. Each original
retains its exact bytes, path, hash, component fact/period role and population scope.
A deterministic document ID derives from the path; native IDs inside payloads remain
unchanged. A document version is not a person, transaction or control occurrence.
No arbitrary wrapper is presented as a native activity producer capsule.

The pinned store accepts 1 byte through 25 MiB per record. The dated adapter
`tools/company_closeout/transport.py` therefore keeps ordinary originals intact,
splits larger originals into ordered exact byte parts, and supplies an explicit
transport manifest for multipart or empty originals. The manifest retains whole
source path/hash/length and ordered part IDs/hashes/lengths. Empty source files
have zero parts; no fabricated byte is added to the original. Transport metadata
and parts are not additional business events, people or company documents.
Readback independently reconstructs and hashes every original. Native business IDs
inside the reconstructed CSV/SQLite/JSON remain unchanged. This is a transport
adapter, not native activity ingestion or a new portal database schema.

Component ID supplies system ID; the explicit edition ID supplies branch identity.
Company ID is SH; legal entity, unit, scenario and time units remain in the declared
component and original records. Source custodian is SH-COMPANY-RECORDS-CUSTODIAN, a
synthetic interface role rather than a newly appointed officer. Authority/evidence
relationships use original paths, source versions and hashes. Current permissions
and collection receipts remain the existing portal's responsibility.

Document `event_at` is null: an original containing multiple historical events is
not assigned one invented business-event date. `available_at` is explicitly declared
at/after retrospective authoring; `imported_at` is set by the software's real clock.
No September-authored original becomes available to an August-known-on view. Record
acceptance is separate and remains pending until actual repository integration.

## Actual rehearsal and reproducibility

`PORTAL_REHEARSAL.json` records an actual isolated six-original import using the
module hash `38a1aebcebde53051e306465dc2d807a3cd0e60fb8cc974da2235fa268c88292`.
All six exact originals read successfully after scoped grants and their availability
time; all six ungranted, future and revoked reads failed. Actual SQLite backup into
a new private directory preserved systems, versions, grants and access history.
All six restored revoked reads remained denied. No live source was touched.

`PORTAL_TRANSPORT_REHEARSAL.json` adds an actual eight-original rehearsal: six
current public source documents, an explicitly empty fixture, and a 25 MiB plus
one byte fixture. Ten bounded store records reconstruct all eight originals;
ten future, ungranted, revoked and restored-revoked reads each fail. Actual SQLite
backup preserves history/content. This validates the adapter boundary, not the
pending final full-edition import, HTTP download behavior or native file browsing.

```sh
python -m tools.company_closeout.edition --contract CONTRACT.json --output /new/edition
python -m tools.company_closeout.portal_rehearsal \
  --edition /new/edition --portal /existing/SABLEHARBOR-audit-suite \
  --revision 548cb5d2be82ec11877e298c2c8d00aa1e555b7f --output /new/private/rehearsal
```

The destination must be new. Use the existing workflow's checked-out history to
resolve that exact module; a current branch name does not replace its pin. Exported
records remain PUBLIC_SYNTHETIC, while runtime database/access receipts stay private.
The rehearsal has no HTTP, instructor-key, model-inference, professional-audit or
external-deployment claim. The backup is after revocation; older-backup replay,
retention/deletion/hold and indirect disclosure require separate evidence. The
CCF reference restore harness exercises its own scoped older-snapshot reconciliation,
not an unimplemented full portal deletion capability.
