# Per-control legacy documentary custody

`company_migration.plan_documentary_custody(private_root, legacy_plan, *, scoped_state,
company_id, branch_id, owner_ids)` prepares a complete, explicit mapping. The trusted
local operator supplies the actual original engagement state, whose ID must match
the legacy plan, and the exact mapping `{control_id: primary_person_id}` for every
control with a retained original. Every owner must exist in that scoped state's
people and match its control assignment. Missing, extra, unknown and swapped owners
are rejected. The organization snapshot, scope and relevant assignments are pinned.
No HTTP route accepts these trusted inputs.

`import_documentary_custody(private_root, custody_plan, *, scoped_state, destination)`
revalidates source and ownership pins, stages a fresh CompanyStore, and publishes to
a new directory under an existing private 0700 parent. It rejects existing targets.
A failed import before publication leaves no target; retry starts a new staged store.
Treat a filesystem failure during publication as incomplete and retain it for operator
inspection rather than overwriting it. The original single-archive
`import_legacy_documents` API remains unchanged.

Each source control receives a stable `DOC-<control digest>` system registered to
its mapped owner. The exact native document bytes, original identity/hash, original
availability and organization/assignment pins are retained. Business event dates
remain `None`; actual import time is recorded separately. Origins remain
`MIGRATED_SYNTHETIC_HISTORY`, classified `LEGACY_SYNTHETIC_DOCUMENTARY_SOURCE`, with
`REQUIRES_SOURCE_RECONCILIATION` and `PROVISIONAL_DOCUMENTARY_CUSTODY` provenance.
This is present documentary routing, not a historical system ownership assertion,
backdated appointment, reconstructed operating event, or verified business fact.

No grant is created. Old legacy and operating stores, audit work, source originals,
hidden facts, actor beliefs and rubrics are not changed or imported. Counts are
reported from the actual verified plan, not hardcoded. The intended full source set
is 359 originals across 70 control archives; this implementation's focused test uses
two independent controls. A full migration is a separate local operator action.
