# Overnight run state

- Source: `origin/canon/corporate-lore-v0.2` at `5137c5abc025ad757a4e1af2a57279e4964578cf`
- Calibration: `origin/architecture/corporate-operating-model-v0.1` at `f12d359f3c3f009a1eea1d290f61be0462ca1f2e`
- Implementation branch: `finance/enterprise-financial-platform-v0.1`
- Current implementation checkpoint: `6c629e3a68e0697fa97b20cc7ece0ca96aec8302`
- Draft PR: `https://github.com/SquirmyWormy275/SABLEHARBOR/pull/9`
- Current phase: Stage 1 correctness verification; integrated monthly expansion has not begun
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
- Milestone 3 implementation: `4d8d95965fd7427bf63c8063fccc4882821fee33`,
  `f1f8b2d40f8b9aa67e4e4dab4f4e3d9175e26161`, and
  `8f61b43382fd9adfcc05059bd6efbf3686af9e11`. Migration head is `0007`.
- Architecture: one deterministic common-actual run per seed owns opening balances and observed
  facts; scenario runs reference it and own scenario journals/values. Actual periods through August
  2026 are invariant. See `GENERATION_RUN_ARCHITECTURE.md`.
- Local suite: Ruff PASS; strict mypy PASS (32 source files); pytest PASS (43 passed, one
  PostgreSQL-only test skipped locally). SQLite migration cycle and comprehensive schema parity
  PASS. SQLite schema SHA-256:
  `32da4de800ced2bf8f90bafd9b06570062c057bbcc58ec3fa181731569164bdb`.
- Remote suite at `50dd167`: PostgreSQL PASS twice (29s/30s), including migration cycle,
  enum/fingerprint stability, generation and validation; SQLite PASS twice (48s/49s);
  render-drift PASS (5s). PostgreSQL schema SHA-256:
  `a0ab7750f7be88e30e4214a7c831afabe1576c3d3301b433a7e0938ac1eb93de`.
- Generation order: base→stress equals stress→base. Base, low, high, and stress are idempotent,
  including second-created and reverse-order reruns. Every run has one lifecycle marker and no
  null-owned generated facts.
- Per-run matrix: common actual `29c8676e-e1c0-5df6-b598-4f1c23d32914` has 3 journals/2 scenario
  values; base `ebfc4f02-2242-58b8-bd75-fc1b88af8587`, low
  `80d8be73-0b23-5b38-8107-5fb64f09a598`, high
  `4f360ca5-2d70-5d8e-bcb9-97dd95479ee9`, and stress
  `3d2164c6-9c69-5144-b574-768ef203e062` each have 80 journals/156 scenario values.
- Reconciliation including common actual: base `$1,184,100,000.0000`; low
  `$1,180,993,933.9189`; high `$1,190,440,128.0541`; stress `$1,176,056,227.1622`; debit equals
  credit in every scope. Base balance-sheet difference is `$0.0000`.
- Generated evidence: `/tmp/sableharbor-stage1-matrix-toueDP.db`, six workbooks under
  `/tmp/sableharbor-workbooks-4SfrY2`, and review-blocked package
  `/tmp/sableharbor-package-Pzrf5w`. These are uncommitted local evidence.
- Remaining blockers: public release still requires a new allowlisted database; generated
  artifacts require comprehensive safety scanning; workbook routing still uses title heuristics;
  driver-based scenarios and integrated monthly subledgers/rollforwards remain open. Exact resume
  point: implement the public table/column allowlist builder and artifact scanner, then semantic
  workbook specifications before monthly three-statement expansion.
- Milestone 4 implementation: `6c629e3a68e0697fa97b20cc7ece0ca96aec8302` at migration
  head `0008`. Centralized identity now normalizes profile/scenario (including stress), persists
  generator version `0.1.0`, actual dataset identity, source/assumption/canon digests,
  `actual_through=2026-08-31`, `forecast_from=2026-09-01`, source commit, and schema head.
  Completed runs reject build-identity mismatches; lifecycle markers use `RUN`; the required schema
  head is derived from Alembic; validation no longer seeds an empty database. Profile generation
  markers and their descendant standard journals/lines/events/values are run-owned.
- Milestone 4 local evidence: Ruff PASS; strict mypy PASS (33 source files); pytest PASS
  (49 passed, one PostgreSQL-only test skipped). One Alembic-installed SQLite database proved
  `standard/base`, `full_history/base`, and `benchmark_private/base` each own nonzero distinct
  journals. Remote CI at `de9fab8` PASS: PostgreSQL 28s/31s, SQLite 53s/56s, and organization
  render validation 6s. The PostgreSQL jobs cover migration `0008`, standard generation, and
  validation; the expanded all-profile/two-seed PostgreSQL matrix remains open.
  Stage 1 remains open. The subsequent uncommitted tranche adds SQLite two-seed namespacing;
  cross-run database ownership constraints/tests remain the next dependency before cutoff
  partitioning and comparison-query work.
- Human/canon review: legal entity chain, acquisition/PPA and financing terms, mine/ARU driver ranges, board and named executive structure. These remain deliberately reversible and do not block platform operation.
- Current uncommitted tranche advances migration head through `0012`. It adds a complete
  repository-relative generation-input manifest, content-addressed build and actual-dataset IDs,
  explicit profile/scenario contracts, and idempotent immutable completion timestamps. Local
  validation: Ruff PASS; strict mypy PASS (33 source files); pytest PASS (55 passed, one
  PostgreSQL-only test skipped because `SHFIN_POSTGRES_TEST_URL` is not configured). SQLite
  two-seed natural-key namespacing now passes. Revision `0011` makes all generated ownership
  non-null, adds same-run composite parent/child constraints and compatible actual-dataset
  attachment, guards lifecycle combinations, and prevents completed identity mutation in the
  database. Revision `0012` adds run-scoped close state and scoped accounting/lineage APIs. Cutoff
  partitioning, broader comparison APIs, and the expanded PostgreSQL matrix remain open.
- The profile contract includes the CLI-default `smoke/base` profile. Semantic tests exercise both
  the no-option default and explicit `--profile smoke` generation, verify the persisted completed
  run context and owned journals, and reject incompatible `smoke/stress` requests.
- Uncommitted files: inspect with `git status --short`
- The current uncommitted migration head is `0012`. Generated natural keys and common-actual
  primary keys are seed/run namespaced. A migrated SQLite database proves two `standard/base`
  seeds coexist with 1,538 separately owned workers and each scenario run references its own
  actual layer. Run IDs now include the complete input-manifest digest, allowing changed builds to
  coexist rather than collide. A populated downgrade preflight refuses the lossy return to global
  natural keys and preserves the `0010` data/schema. SQLite semantic violations now prove rejection
  of null ownership, cross-run generated links, incompatible actual layers, invalid lifecycle
  combinations, and mutation of completed run identity, including source/canon/assumption digests
  and start time. Trial balance, lineage, and close APIs pass a two-run contamination test.
  PostgreSQL two-seed/violation proof, cutoff auditing, and broader comparison APIs remain open.
- Follow-up correction evidence: run-context close now records closure for both the selected
  scenario and its included common-actual run; semantic tests prove both owners reject later
  posting. Explicit journal ownership and reversal are rejected when incompatible with the active
  session context. Local validation after this correction: Ruff PASS; strict mypy PASS (33 source
  files); pytest PASS (66 passed, one PostgreSQL-only skip). PostgreSQL `0009`–`0012` proof remains
  open.
- Migration `0012` correction: legacy globally closed fiscal periods are materialized for every
  existing run during upgrade and remain a compatibility posting guard. Downgrade projects only
  uniform run close state back to the global field and refuses mixed state. The regression test
  upgrades a populated closed-period database, proves posting is still rejected, proves a lossless
  downgrade preserves `CLOSED`, and proves a lossy downgrade is refused. Local validation after
  this correction: Ruff PASS; strict mypy PASS (33 source files); pytest PASS (68 passed, one
  PostgreSQL-only skip). PostgreSQL `0009`–`0012` proof remains open.
- Cutoff partition increment: standard-profile monthly journals and revenue/cost driver values
  through `2026-08-31` are owned once by the common-actual run; forecast records from `2026-09-01`
  remain scenario-owned. The actual run is completed only after these monthly records are written,
  and sibling scenarios reuse it. A semantic test rejects scenario-owned pre-cutoff monthly facts
  and actual-owned post-cutoff facts. A migration-backed regression persists a deliberately
  different June 30 / July 1 contract and proves journals, driver values, production, freight, and
  ending-inventory ownership follow it. Broader comparison APIs and PostgreSQL `0009`–`0012`
  matrices remain open.
- Profile-order correction: every profile that completes the common-actual layer first populates
  the same deterministic monthly actual superset. The bidirectional baseline→standard and
  standard→baseline regression proves both orders succeed and yield identical common-actual and
  standard journal counts and debit totals without enriching a completed layer.
- Semantic comparison increment: `compare_trial_balances` requires two explicit, distinct,
  completed runs with the same profile, actual dataset, cutoff, forecast start, and schema. A
  SQLite base/stress regression proves a nonzero scenario delta and rejects same-run and
  cross-seed comparisons. Broader comparison reports, remaining dated-fact cutoff auditing, and
  PostgreSQL `0009`–`0012` parity remain open.
- Comparison-matrix correction: one-variable-at-a-time SQLite regressions now prove rejection of
  profile, actual-dataset, actual-through cutoff, forecast-start, and schema-head mismatches, plus
  an explicit incomplete-run rejection. Local validation after this correction: Ruff PASS;
  strict mypy PASS (33 source files); pytest PASS (77 passed, one PostgreSQL-only skip). The
  uncommitted `0009`–`0012` PostgreSQL matrix, remaining dated-fact cutoff audit, and broader
  comparison reports remain open.
- Dated-fact cutoff correction: Red Wash production and ARU freight movements through August 2026
  are owned once by `actual_common`; September–December production and movements and the December
  ending-inventory lot are scenario-owned. A two-scenario semantic audit rejects both post-cutoff
  actual facts and pre-cutoff scenario facts across all three registers. A December 31 cutoff
  boundary regression additionally proves that the ending-inventory lot is materialized exactly
  once by `actual_common`, with its expected date, quantity, and carrying value, rather than being
  omitted when the lot becomes actual. Local validation after this correction: Ruff PASS; strict
  mypy PASS (33 source files); pytest PASS (78 passed, one PostgreSQL-only skip). Effective-dated
  master and commitment records are not periodic facts and remain whole records. Broader
  comparison reports and PostgreSQL `0009`–`0012` parity remain open.
- PostgreSQL acceptance-matrix increment: the PostgreSQL 16 CI job now runs an explicit Stage 1
  matrix after the migration cycle. It generates smoke, baseline, standard, full, full-history,
  and benchmark-private profiles; base/low/high/stress siblings; and a second standard seed. It
  proves duplicate natural keys coexist and deliberately attempts null ownership, cross-run
  generated linkage, incompatible actual attachment, and completed identity mutation, then audits
  production, freight, and inventory cutoff ownership. The matrix exposed and corrected a real
  portability defect: `benchmark_private` previously required a SQLite-style `var/private/` URL
  and therefore could not run on PostgreSQL. Server databases now require the explicit
  `SHFIN_PRIVATE_BENCHMARK=1` authorization while private-path SQLite remains supported. Local
  evidence after this increment: Ruff PASS; strict mypy PASS (33 source files); pytest PASS
  (78 passed, two PostgreSQL-only skips); the complete matrix PASS on a fresh migrated SQLite
  backend surrogate. PostgreSQL 16 execution remains pending because no local service is
  available and the outer controller owns commits/pushes that trigger CI.
- Public-release increment: the package is constructed into a fresh SQLite database from
  `config/releases/public-demo-v0.1.json`, which allowlists every exported table and column.
  Packaging removes stale output and accepts a controlled timestamp; same-input package hashes are
  deterministic. A recursive scanner inspects CSV headers/values, SQLite schema/text values,
  XLSX ZIP/XML and relationships, manifests, and nested archives for credentials, local paths,
  external relationships, macros, and embedded objects. CI scans and uploads the generated package
  plus six review workbooks after tests pass. Resume at semantic workbook specifications after the
  PostgreSQL `0010` constraint-name correction is green remotely.
- Semantic-workbook increment: all required sheet titles are covered exactly once by `SHEET_SPECS`;
  title substring routing has been removed. Each specification records purpose, named query, units,
  sort order, tolerance, and empty-state behavior. Workbook controls now use equality tolerance for
  journal balance and positive-count predicates for population controls. Tests compare database query
  headers directly with P&L, balance-sheet, and journal-lineage sheet headers and assert industrial
  sheets cannot inherit generic financial routing. Resume at business-line driver scenarios and the
  integrated monthly subledger/statement chains after CI confirms the release and workbook checkpoint.
