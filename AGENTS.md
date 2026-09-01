# SABLE HARBOR — AGENT OPERATING INSTRUCTIONS

These instructions apply to every automated coding agent working in this repository. More specific `AGENTS.md` files may add constraints for their subtrees but may not weaken the rules below.

## 1. Repository purpose

Sable Harbor is a canonical synthetic enterprise and reusable business-world sandbox spanning industrial software, mining, research, logistics, professional services, finance, governance, security, assurance, incident response, and training.

The repository contains several different evidence classes. Do not blur them:

- **LOCKED** — accepted canon; preserve unless the user explicitly changes it.
- **PROVISIONAL** — accepted working direction; implementation details remain revisable.
- **OPEN** — unresolved; do not silently invent a permanent answer.
- **SUPERSEDED** — historical material preserved for provenance but no longer controlling.
- **MODEL_PROPOSED** — a reversible quantitative or structural proposal.
- **SCENARIO_INPUT** — a scenario-specific assumption.
- **SYNTHETIC_INSTANCE** — generated fictional records consistent with the model.
- **DERIVED** — calculated from recorded inputs.

## 2. Canon precedence

When sources conflict, use this order:

1. Current LOCKED entries in `docs/canon/DECISION_REGISTER.md`.
2. Current canonical documents in `docs/canon/`, especially corporate lore v0.2.
3. Current governance policies in `docs/governance/`.
4. Current PROVISIONAL decisions, clearly identified as provisional.
5. OPEN decisions, which may receive reversible scenario assumptions but may not be silently canonized.
6. Older handovers and operating-model documents only where compatible with the above.
7. General accounting, data-modeling, and software-engineering practice for implementation mechanics only.

The older 426-FTE / $124.5M operating model is historical calibration, not controlling current canon.

Current enterprise scope includes Foundry/Foundry Field, Willow, Atlas Meridian, Pale Sun/Red Wash, Project Cradle, American Resource Utility/BS&T, emerging Advisory, shared corporate functions, and relevant historical obligations or lineage. Emberline is not a standalone 2026 division. Evalon is historical and was rechartered into Willow.

## 3. Public-repository boundary

The repository is intentionally public.

Do not commit:

- secrets, credentials, tokens, or private keys;
- personal or sensitive private data;
- proprietary NAILEX implementation details;
- hidden benchmark truth, answer keys, scoring oracles, or unreleased scenario answers;
- local absolute paths or workstation-specific credentials;
- raw source databases containing non-allowlisted material.

Public synthetic data, safe schemas, generators, documentation, sample queries, manifests, checksums, and reviewed release artifacts are permitted only after the applicable validation and safety gates pass.

## 4. Database architecture

The enterprise database and ledger are the source of truth. Excel, CSV, SQLite unit packages, dashboards, and Wiki pages are derivative reporting or audit surfaces.

Do not create independently maintained shadow ledgers for business units. Business-unit packages must be deterministic, read-only slices generated from an explicit enterprise generation run and reconciled to the consolidated source.

Every generated financial or operational record must be attributable to an explicit data context including, where applicable:

- generation run;
- scenario;
- profile;
- seed;
- generator version;
- source commit;
- actual/forecast/model state;
- effective period;
- fact state.

Unfiltered aggregation across multiple generation runs or scenarios must fail rather than silently combine incompatible records.

## 5. Accounting invariants

Preserve double-entry accounting and auditability:

- every posted journal balances;
- posted journals and lines are immutable;
- corrections use reversals and replacement entries;
- closed periods reject ordinary posting;
- subledgers reconcile to control accounts;
- unit statements reconcile to unit trial balances;
- intercompany activity matches counterparties and eliminates on consolidation;
- monthly balance sheets balance;
- cash, receivables, deferred revenue, payables, inventory, fixed assets, debt, equity, and other rollforwards reconcile by period;
- source events trace to journal entries and journal entries trace back to source events.

Passing debit/credit arithmetic alone is not sufficient evidence that the model is complete or economically coherent.

## 6. Migrations

Committed Alembic migrations must be explicit and immutable.

- Do not make historical migrations call current application metadata or `Base.metadata.create_all()`.
- Use explicit Alembic operations and explicit downgrade behavior.
- Test SQLite and PostgreSQL upgrades, downgrades, and schema equivalence.
- Do not rewrite a released migration. Before the first accepted release, a reviewed baseline squash is permitted when it produces a stronger immutable history.

## 7. Workbooks and generated artifacts

Workbook sheets must be mapped through explicit semantic specifications. Do not route data by sheet-name substring or populate unrelated sheets with placeholders disguised as final content.

Every workbook sheet specification should define its purpose, query/report source, selected generation run and scenario, required columns, units, sort order, formulas, checks, tolerances, and empty-state behavior.

Tests must compare important workbook outputs directly with database/report values.

Generated databases, recurring workbooks, CSV exports, and release bundles normally belong in ignored output directories and CI/release artifacts, not repeatedly committed to source. Reviewed static publications may be committed only with source builders, manifests, and checksums.

## 8. Business-unit audit packages

A dossier is a navigation page. It is not proof that a unit is independently auditable.

Do not claim independent auditability until the unit has a validated package containing the required filtered database, extracts, financial statements, operational registers, intercompany bridge, lineage, validation results, workbook, manifest, and checksums, and until the package reconciles to the enterprise consolidation.

Use the controlling unit-package specification under `docs/audit/` when present.

## 9. Workflow and Git discipline

Before modifying files:

1. inspect `git status --short --branch`;
2. inspect the current branch, current head, open PR, and relevant CI state;
3. read this file and the current handoff/state documents;
4. identify controlling canon and explicit acceptance criteria;
5. inspect existing code before proposing replacement architecture.

While working:

- execute, do not stop after producing a plan;
- make the smallest coherent change that advances an acceptance gate;
- use atomic commits with meaningful messages;
- run focused tests after each slice and the full applicable suite before reporting completion;
- push completed commits to the intended branch;
- keep state and handoff documents current;
- preserve evidence before deleting or retiring branches or files;
- do not merge, close, delete, force-push, rewrite history, enable auto-merge, or change canon unless expressly authorized for that action.

Leave the worktree clean unless a documented external limitation prevents it.

## 10. Required validation posture

Do not infer completion from green CI alone. Determine what the tests actually assert.

For a material release candidate, report:

- exact commit SHA;
- changed-file inventory or summary;
- exact commands run;
- test counts and failures/skips;
- SQLite and PostgreSQL results;
- reconciliation results and tolerances;
- generated-artifact inventory;
- safety-scan scope;
- remaining limitations;
- exact resume point.

Never use `PASS` as a hardcoded release status. Derive status from real validations.

## 11. Completion language

Do not say `complete`, `integration-ready`, `production-ready`, `deterministic public release`, or `independently auditable` unless the documented acceptance gate has been fully met and independently reviewable evidence exists.

Use precise states such as:

- architecture scaffold;
- proof of concept;
- implementation in progress;
- release candidate;
- review blocked;
- accepted;
- superseded.

When an exact value or corporate fact is unavailable, make the smallest reversible assumption, label it correctly, record provenance, and continue with work that does not require canon invention.
