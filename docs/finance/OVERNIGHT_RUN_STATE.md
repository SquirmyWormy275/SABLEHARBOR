# Overnight run state

- Source: `origin/canon/corporate-lore-v0.2` at `5137c5abc025ad757a4e1af2a57279e4964578cf`
- Calibration: `origin/architecture/corporate-operating-model-v0.1` at `f12d359f3c3f009a1eea1d290f61be0462ca1f2e`
- Implementation branch: `finance/enterprise-financial-platform-v0.1`
- Current implementation checkpoint: `4cb7671918d81b8093d2a4828e84a65fd1a93bcc`
- Draft PR: `https://github.com/SquirmyWormy275/SABLEHARBOR/pull/9`
- Current phase: Stage 1 finance/accounting kernel remediation; run/scenario isolation next
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
- Exact resume point: add generation-run foreign keys and run-scoped uniqueness to generated
  journals and subledgers, require explicit run/scenario selectors in reporting, and add a same-DB
  base-plus-stress isolation/idempotency integration test.
- Human/canon review: legal entity chain, acquisition/PPA and financing terms, mine/ARU driver ranges, board and named executive structure. These remain deliberately reversible and do not block platform operation.
- Uncommitted files: inspect with `git status --short`
