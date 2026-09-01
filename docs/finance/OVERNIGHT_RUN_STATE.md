# Overnight run state

- Source: `origin/canon/corporate-lore-v0.2` at `5137c5abc025ad757a4e1af2a57279e4964578cf`
- Calibration: `origin/architecture/corporate-operating-model-v0.1` at `f12d359f3c3f009a1eea1d290f61be0462ca1f2e`
- Implementation branch: `finance/enterprise-financial-platform-v0.1`
- Current implementation checkpoint: `05314a7f18828bb58e98ae68ed2568570d8c1013`
- Draft PR: `https://github.com/SquirmyWormy275/SABLEHARBOR/pull/9`
- Current phase: Stage 1 finance/accounting kernel remediation; extend run isolation through
  subledgers and reporting surfaces next
- Completed: source lock and collisions; alternatives A/B/C; Alternative B operating model; legal/entity scenario; dimensional chart; immutable accounting kernel; migrations; commercial, professional-services engagement, and corporate subledgers; Red Wash, ARU/BS&T, Cradle, Willow and Atlas causal flows; deterministic base/low/high/stress profiles; 2023–2026 monthly standard model; 2016–2026 history; intercompany eliminations; reconciled statements; named queries; six-workbook suite; valuation; public release package; privacy/canon guardrails; SQLite and PostgreSQL CI definitions
- Last successful local release: clean migration; `full_history` generation; trial balance debit = credit = `$1,172,100,000.0000`; six workbooks; public package; valuation; statement balance difference `$0.0000`; lint/type checks; 29 tests passed. Migration `0004` and the engagement margin integration test also pass from a clean SQLite database.
- Milestone 1 changed files: replaced migrations `0001`–`0004` with
  `db/migrations/versions/0004_frozen_explicit_baseline.py`; expanded
  `tests/integration/test_migrations.py`.
- Milestone 1 tests: `uv run ruff check .` PASS; `uv run mypy src` PASS (32 source
  files); `uv run pytest -ra` PASS (30 passed); SQLite
  upgrade/downgrade/upgrade PASS; migrated-schema versus ORM-schema fingerprint PASS;
  unrelated-live-model immunity PASS; full-history/base generation PASS (48 monthly periods);
  trial balance PASS with debit = credit = `$1,184,100,000.0000`; tracked-source public-safety
  scan PASS.
- Baseline findings: standalone organization-map validator FAILS because the generated register
  exposes `page`/`asset` while the validator requires `path`; local PostgreSQL is unavailable
  (`/var/run/docker.sock` permission denied; no server on port 5432). Remote PR #9 PostgreSQL
  checks were green before this milestone; the new checkpoint still requires remote CI evidence.
- Generated artifacts: six workbooks under `workbooks/outputs/`; public package under
  `releases/generated/public-demo-v0.1/`; temporary reconciled baseline databases under `/tmp`
  are local evidence only and are not committed.
- Remaining P0: PostgreSQL migration proof; generation-run/scenario isolation; workbook semantic
  registry; public allowlisted rebuild; generated-artifact safety scanning. Remaining P1:
  integrated monthly statements/rollforwards; driver-based scenarios; historical-claim correction;
  CI review artifacts.
- Milestone 2 changed files: `src/sable_harbor/accounting/{models,ledger}.py`,
  `src/sable_harbor/{cli,generation}.py`, `src/sable_harbor/provenance/service.py`, explicit
  migration `0005_generation_context.py`, and three integration-test files.
- Milestone 2 behavior: generation runs begin before facts are created; journals and scenario
  values carry run foreign keys; shared enterprise dimensions are reused; lineage is current-run
  scoped; ambiguous validation fails unless a run ID is supplied.
- Milestone 2 tests: Ruff PASS; strict mypy PASS (32 source files); pytest PASS (31 passed);
  SQLite migration PASS; same-database base+stress coexistence and base idempotency PASS;
  unfiltered validation rejected with two runs; explicit base reconciliation PASS at
  `$1,184,100,000.0000` debit/credit; explicit stress reconciliation PASS at
  `$884,718,000.0000` debit/credit; tracked-source safety PASS.
- Milestone 2 generated evidence: `/tmp/sableharbor-isolation-K4FUyV.db` contains base run
  `ebfc4f02-2242-58b8-bd75-fc1b88af8587` (83 journals, 155 scenario values) and stress run
  `3d2164c6-9c69-5144-b574-768ef203e062` (80 journals, 154 scenario values). This temporary
  database is not committed.
- Milestone 2 remaining P0: direct run keys on applicable subledger/operational facts, selectors
  across all reports/queries/workbooks/exports, run-scoped uniqueness for repeat scenarios with
  different seeds/versions, and PostgreSQL downgrade/upgrade plus schema-fingerprint proof. Remote
  checkpoint CI passed two PostgreSQL upgrade/generate/validate jobs (27s and 29s), two SQLite jobs
  (31s and 32s), and organization validation (7s). Resume in the subledger models and reporting
  interfaces before expanding the monthly three-statement chains.
- Human/canon review: legal entity chain, acquisition/PPA and financing terms, mine/ARU driver ranges, board and named executive structure. These remain deliberately reversible and do not block platform operation.
- Uncommitted files: inspect with `git status --short`
