# Repository documentary sync

`company_repository_documents.plan_repository_documents(repository, *, manifest,
organization_snapshot)` prepares a detached, hash-pinned plan. The manifest contains
`company`, `branch`, and `documents`. Each entry explicitly supplies `document_id`,
`path`, `expected_version`, `control_ids`, `owner_id`, `source_authority`,
`source_version`, `effective_date`, `revision_date`, `supersedes`, and
`mapping_rationale`. Dates may be null. Every control must exist in the supplied
trusted organization snapshot and have that primary owner. Preserve the snapshot's
proposed assignment status: custody is not historical authorship or appointment.

`sync_repository_documents(store, *, repository, plan, organization_snapshot,
command_id)` revalidates all pins, reads exact originals, registers document-specific
systems, and appends versions. Use only from a trusted local operator workflow with
an existing private CompanyStore. There is no HTTP route, scheduling, grant creation,
audit initialization, or automatic source discovery. A manifest is an operator mapping,
not an approval of source assertions. Source-stated authority remains separately pinned.

The initial path boundary allows committed native Markdown only in docs/governance,
docs/controls, and docs/canon, excluding structured/publication/generated/internal
subtrees. It is not a semantic classifier: the operator must exclude financing records,
audit-prepared material, and derivative documents even if placed in an allowed directory.
No finance directory imports or source modifications occur. Current accepted authority
and explicit supersession must follow MAINTAINERS.md; Git commits do not approve canon.
Only documents matching committed blob bytes are accepted. Unrelated Git HEAD changes
require replanning. Existing immutable finance releases and originals remain untouched.

Repository origin is `REPOSITORY_SYNTHETIC_DOCUMENT`; business event time remains
unknown. Effective/revision dates are documentary metadata, not proof of historical
availability. Availability starts at actual ingestion. No old audit gains access to a
newly imported document merely because its effective date is old. Append corrections
with the next expected version and explicit supersession references; old versions stay
retrievable under grants. Custody changes fail system registration rather than silently
forking document identity; a future explicit transfer workflow is required.

Writes are individually durable, not globally atomic. On interruption retry the identical
plan and command; original availability and exact receipts are retained, while changed
payloads conflict. Previously completed entries are not rolled back. If repository pins
have changed since an interrupted import, first restore the pinned checkout; do not
pretend a different plan is the same operation. Existing company backup covers these
versions; source repository and manifest retention remain separate operator duties.

No corpus has been imported by this implementation. Tests use isolated temporary Git
repositories and company stores and exercise original bytes, corrections, retries,
unknown event dates, conservative availability, custody/pin failures, unsafe paths,
and absence of new grants or collections.
