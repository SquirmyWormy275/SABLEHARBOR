# Overnight run state

- **Status note (2026-09-05):** this file is a chronological engineering log, not live branch or
  canon authority. Resolve the current implementation commit with `git rev-parse HEAD`; references
  below to a tranche being “uncommitted” describe its state when that historical entry was written.
- Current canon source: `main` at `712076751a31534cd9e6e41458336cdc7b6585b5`, including corporate
  lore v0.3 and the September 3 decision-register addendum.
- Historical knowledge snapshot: v0.2 at
  `5137c5abc025ad757a4e1af2a57279e4964578cf`, authoritative only for the August 31 knowledge state.
- Calibration: `origin/architecture/corporate-operating-model-v0.1` at `f12d359f3c3f009a1eea1d290f61be0462ca1f2e`
- Implementation branch: `finance/enterprise-financial-platform-v0.1`
- PR: `https://github.com/SquirmyWormy275/SABLEHARBOR/pull/9`
- Final implementation evidence commit: `3fb7fc7d5ae3b138760e64560d3143fde18a8a47`.
- Current phase: local acceptance passed; current remote PR checks and merge remain. Authoritative
  acceptance status is in `PLATFORM_ACCEPTANCE_v0.1.md` and current CI, not an older checkpoint
  below.
- Current migration target: `0015`. Fresh SQLite and PostgreSQL 16.6/18.6 migration, generation,
  validation, query, workbook, unit-package, release, checksum, direct-guard, and artifact-safety
  evidence passed at the implementation evidence commit. Both PostgreSQL versions produced schema
  SHA-256 `68d35c79bc07b59e8697e40cfdf5c7f49bc3e88e0a5ebd593a5dd26426d0a4b7`.
- Final local suite: Ruff format/lint PASS; strict mypy PASS across 37 source files; all 128 collected
  tests exercised, with 125 local passes and three PostgreSQL-only local skips that passed on each
  certified PostgreSQL version. A clean standard/base run passed all ten financial controls and all
  21 named-query paths, with final balance-sheet difference `$0.0000`.
- Final artifact evidence: six workbooks plus suite manifest/checksums (9 files), one public release
  (26 files), and seven unit evidence packages (149 files) passed manifests, hashes, enterprise
  bridges, recursive safety, and same-persisted-snapshot byte-determinism checks on SQLite,
  PostgreSQL 16.6, and PostgreSQL 18.6.
- Classification: every generated 2023–2026 numeric record is synthetic scenario/calibration data.
  The current shared-layer profile is `synthetic_common`; deprecated database columns containing
  `actual` are internal migration/storage aliases only. Current APIs and outputs use
  synthetic-calibration semantics and do not assert observed company results or audited books.
- Implemented surfaces under review: source lock and collisions; alternatives A/B/C; Alternative B
  operating model; legal/entity scenario; dimensional chart; accounting kernel and migrations;
  commercial, professional-services engagement, and corporate subledgers; Red Wash, ARU/BS&T,
  Cradle, Willow, and Atlas causal flows; deterministic base/low/high/stress scenarios; synthetic
  2023–2026 monthly standard model; 2016–2022 calibration anchors; intercompany eliminations;
  statements; named queries; six-workbook suite with a valuation scope limitation; public release
  generator; privacy/canon guardrails; and SQLite/PostgreSQL CI definitions.
- Historical local synthetic-release evidence: clean migration; `full_history` generation; trial
  balance debit = credit = `$1,172,100,000.0000`; six workbooks; public package; a model-proposed
  valuation output; statement balance difference `$0.0000`; lint/type checks; 29 tests passed.
  Migration `0004` and the engagement margin integration test also passed from a clean SQLite
  database. These are historical technical reconciliation totals, not current `0015` evidence or
  company financial history.
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
- Architecture: one deterministic shared synthetic-calibration run per seed owns synthetic
  opening balances and shared pre-cutoff calibration records; scenario runs reference it and own
  scenario journals/values. Synthetic periods through August 2026 are invariant. See
  `GENERATION_RUN_ARCHITECTURE.md`.
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
- Per-run matrix: shared synthetic calibration run `29c8676e-e1c0-5df6-b598-4f1c23d32914` has 3 journals/2 scenario
  values; base `ebfc4f02-2242-58b8-bd75-fc1b88af8587`, low
  `80d8be73-0b23-5b38-8107-5fb64f09a598`, high
  `4f360ca5-2d70-5d8e-bcb9-97dd95479ee9`, and stress
  `3d2164c6-9c69-5144-b574-768ef203e062` each have 80 journals/156 scenario values.
- Synthetic reconciliation including the shared calibration layer: base `$1,184,100,000.0000`; low
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
  generator version `0.1.0`, shared-calibration dataset identity, source/assumption/canon digests,
  a synthetic cutoff of `2026-08-31`, `forecast_from=2026-09-01`, source commit, and schema head.
  Completed runs reject build-identity mismatches; lifecycle markers use `RUN`; the required schema
  head is derived from Alembic; validation no longer seeds an empty database. Profile generation
  markers and their descendant standard journals/lines/events/values are run-owned.
- Milestone 4 local evidence: Ruff PASS; strict mypy PASS (33 source files); pytest PASS
  (49 passed, one PostgreSQL-only test skipped). One Alembic-installed SQLite database proved
  `standard/base` and `full_history/base` each owned nonzero distinct journals; the checkpoint also
  exercised an evaluator-only path that was subsequently removed. Remote CI at `de9fab8` PASS:
  PostgreSQL 28s/31s, SQLite 53s/56s, and organization
  render validation 6s. The PostgreSQL jobs cover migration `0008`, standard generation, and
  validation; the expanded all-profile/two-seed PostgreSQL matrix remains open.
  Stage 1 remained open. The then-uncommitted tranche added SQLite two-seed namespacing;
  cross-run database ownership constraints/tests remain the next dependency before cutoff
  partitioning and comparison-query work.
- Human/canon review: the legal relationship shapes and nine-member/five-committee board are now
  locked and are not reversible model options. Exact legal names, jurisdictions, acquisition/PPA
  and financing terms, mine/ARU driver ranges, occupancy, and unresolved executive details remain
  open or scenario-classified as applicable.
- Historical tranche then under review advanced migration head through `0012`. It added a complete
  repository-relative generation-input manifest, content-addressed build and shared-dataset IDs,
  explicit profile/scenario contracts, and idempotent immutable completion timestamps. Local
  validation: Ruff PASS; strict mypy PASS (33 source files); pytest PASS (55 passed, one
  PostgreSQL-only test skipped because `SHFIN_POSTGRES_TEST_URL` is not configured). SQLite
  two-seed natural-key namespacing now passes. Revision `0011` makes all generated ownership
  non-null, adds same-run composite parent/child constraints and compatible shared-dataset
  attachment, guards lifecycle combinations, and prevents completed identity mutation in the
  database. Revision `0012` adds run-scoped close state and scoped accounting/lineage APIs. Cutoff
  partitioning, broader comparison APIs, and the expanded PostgreSQL matrix remain open.
- The profile contract includes the CLI-default `smoke/base` profile. Semantic tests exercise both
  the no-option default and explicit `--profile smoke` generation, verify the persisted completed
  run context and owned journals, and reject incompatible `smoke/stress` requests.
- Historical worktree state was recorded with `git status --short`; it is not a claim about the
  current worktree.
- At that checkpoint migration head was `0012`. Generated natural keys and shared-calibration
  primary keys are seed/run namespaced. A migrated SQLite database proves two `standard/base`
  seeds coexist with 1,538 separately owned workers and each scenario run references its own
  calibration layer. Run IDs now include the complete input-manifest digest, allowing changed builds to
  coexist rather than collide. A populated downgrade preflight refuses the lossy return to global
  natural keys and preserves the `0010` data/schema. SQLite semantic violations now prove rejection
  of null ownership, cross-run generated links, incompatible calibration layers, invalid lifecycle
  combinations, and mutation of completed run identity, including source/canon/assumption digests
  and start time. Trial balance, lineage, and close APIs pass a two-run contamination test.
  PostgreSQL two-seed/violation proof, cutoff auditing, and broader comparison APIs remain open.
- Follow-up correction evidence: run-context close now records closure for both the selected
  scenario and its included shared calibration run; semantic tests prove both owners reject later
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
- Cutoff partition increment: standard-profile synthetic monthly journals and revenue/cost driver
  values through `2026-08-31` are owned once by the shared synthetic-calibration
  run; forecast records from `2026-09-01` remain scenario-owned. The calibration run is completed only after these monthly records are written,
  and sibling scenarios reuse it. A semantic test rejects scenario-owned pre-cutoff monthly facts
  and calibration-owned post-cutoff records. A migration-backed regression persists a deliberately
  different June 30 / July 1 contract and proves journals, driver values, production, freight, and
  ending-inventory ownership follow it. Broader comparison APIs and PostgreSQL `0009`–`0012`
  matrices remain open.
- Profile-order correction: every profile that completes the shared calibration layer first
  populates the same deterministic monthly synthetic pre-cutoff superset. The bidirectional
  baseline→standard and standard→baseline regression proves both orders succeed and yield identical
  shared-calibration and
  standard journal counts and debit totals without enriching a completed layer.
- Semantic comparison increment: `compare_trial_balances` requires two explicit, distinct,
  completed runs with the same profile, shared dataset, cutoff, forecast start, and schema. A
  SQLite base/stress regression proves a nonzero scenario delta and rejects same-run and
  cross-seed comparisons. Broader comparison reports, remaining dated-fact cutoff auditing, and
  PostgreSQL `0009`–`0012` parity remain open.
- Comparison-matrix correction: one-variable-at-a-time SQLite regressions now prove rejection of
  profile, shared-dataset, cutoff, forecast-start, and schema-head mismatches, plus
  an explicit incomplete-run rejection. Local validation after this correction: Ruff PASS;
  strict mypy PASS (33 source files); pytest PASS (77 passed, one PostgreSQL-only skip). The
  then-uncommitted `0009`–`0012` PostgreSQL matrix, remaining dated-record cutoff review, and broader
  comparison reports remain open.
- Dated-record cutoff correction: synthetic Red Wash production and BS&T freight movements through
  August 2026 are owned once by the shared synthetic-calibration run;
  September–December production and movements and the December
  ending-inventory lot are scenario-owned. A two-scenario semantic audit rejects both post-cutoff
  calibration-owned post-cutoff records and pre-cutoff scenario records across all three registers. A December 31 cutoff
  boundary regression additionally proves that the ending-inventory lot is materialized exactly
  once by the shared synthetic-calibration run, with its expected date,
  quantity, and carrying value, rather than being
  omitted when the lot enters the shared calibration layer. Local validation after this correction: Ruff PASS; strict
  mypy PASS (33 source files); pytest PASS (78 passed, one PostgreSQL-only skip). Effective-dated
  master and commitment records are not periodic facts and remain whole records. Broader
  comparison reports and PostgreSQL `0009`–`0012` parity remain open.
- PostgreSQL acceptance-matrix increment: at this historical checkpoint, the PostgreSQL 16 CI job
  ran an explicit Stage 1 matrix after the migration cycle. It generated the public profiles,
  base/low/high/stress siblings, a second standard seed, and a then-present evaluator-only profile. It
  proved duplicate natural keys coexist and deliberately attempted null ownership, cross-run
  generated linkage, incompatible calibration attachment, and completed identity mutation, then reviewed
  production, freight, and inventory cutoff ownership. The matrix exposed and corrected a real
  portability defect in that evaluator-only path. That profile and its environment switch were later
  removed; current PR #9 has no active private evaluator-generation interface. Local
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
- PostgreSQL portability correction: CI proved that the explicit cutoff marker exceeds the legacy
  16-character `scenario_value.period_code` width, a defect SQLite does not enforce. Forward migration
  `0013` widens the field to 64 characters and refuses a lossy downgrade when populated values exceed
  the old limit. The tracked-file scanner now excludes only its two signature-definition source files
  while continuing to scan all generated artifacts. Remote PostgreSQL and SQLite CI are pending.
- Driver-scenario increment: `operating.yml` now defines business-line revenue and cost drivers for
  SHI, Red Wash, ARU/BS&T, Cradle, Research, Advisory, and Capital/liquidity. The v0.1 implementation
  applies forecast multipliers only for SHI, `RWH`, and ARU. Cradle, Research, Advisory, and Capital
  are persisted with `application_status=RECORDED_ONLY_NOT_APPLIED`; no generated-output causality is
  attributed to those four families. Tests prove all seven families persist with explicit
  application status and that selected-run low/high/stress totals differ. Resume at causal
  implementation for the recorded-only families and broader monthly subledger rollforwards.
- Monthly-reporting increment: `monthly_statements` derives 48 scoped periods of P&L, balance sheet,
  cash flow, changes in equity, working capital, debt, net fixed assets, and inventory directly from
  the posted GL. Every monthly balance sheet balances at zero difference; cash-flow changes sum to
  ending cash; final assets, liabilities, equity, and cash reconcile to the consolidated snapshot.
  The corresponding workbook sheets use these report-specific semantic sources. PostgreSQL CI
  passes the full Stage 1 matrix in both push and PR runs (39s and 38s); SQLite artifact jobs remain
  in progress. Resume at causal monthly subledger event generation and unit-package reconciliation.
- Causal-subledger increment: every forecast month now replaces a controlled portion of the SHI,
  Red Wash, and ARU summary journal with source-linked economic events while preserving total driver
  economics. SHI generates contract, obligation, invoice, ratable recognition, AR, and collection;
  Red Wash generates production batch, inventory lot, shipment, COGS, receivable, and collection;
  ARU generates waybill, ton-miles, fuel/crew cost, receivable, and collection. The base run contains
  four complete forecast chains per line, all run-owned and idempotent. SHI forecast months also
  generate a run-owned payroll cohort, payroll/benefit posting, purchase order, receipt, matched bill,
  vendor payment, fixed asset, depreciation, debt draw, and interest accrual. Explicit parent flushes
  make every chain portable under enforced SQLite/PostgreSQL foreign keys. Resume by expanding Cradle,
  research, and Advisory into the monthly chain and adding debt repayment/covenant schedules.
- Specialist-line monthly integration: each forecast month now includes an Advisory engagement,
  approved time, project cost, invoice and margin link; a Willow experiment with explicit gate; an
  Atlas evaluation with compute/validation cost and customer fee; and a host-safe Cradle recovery
  run with operating cost, recovered value, host share, inventory and sale. All four families are
  run-owned, source-linked, idempotent, and preserve the controlling summary economics. Resume at
  debt repayment/covenant schedules, AR/AP exposure reconciliation, and unit export packages.
- Debt-repayment increment: migration `0014` adds an explicit run-owned repayment subledger linked
  to each debt draw and its posted journal. Every SHI forecast month now draws $100,000 and repays
  $25,000 through balanced debt/cash entries; validation rejects non-positive and over-principal
  repayments. A clean SQLite migration reached `0014` at that checkpoint. Resume at covenant
  calculations and AR/AP exposure reconciliation before constructing unit export packages.
- Exposure/covenant-control increment: the AR/AP exposure view reports document totals, settlement
  totals, document open balances, AR due-date buckets, AP due-date-unavailable exposure, and a
  separately labeled residual source-event bridge; its total exposure reconciles to scoped GL
  accounts 1100 and 2100. The debt calculation now
  reports draw, repayment, principal outstanding, interest, availability, and a provisional status
  for every facility. A separately labeled `GL_UNALLOCATED_CONTROL` row exposes the summary-model
  debt not yet represented by causal facility records, and the complete schedule reconciles to the
  monthly debt rollforward. No unavailable covenant threshold is presented as LOCKED canon.
- PostgreSQL/public-safety correction: remote PostgreSQL exposed four externally visible industrial
  identifiers longer than their 40-character schema contract. Mine lots, production batches,
  shipments, and waybills now use deterministic compact numbers while retaining full stable UUID
  identity and lineage; a regression caps all four. Pull-request CI also inherits Blackridge's
  18.9 MiB public SQLite database from current `main`, so the tracked-file gate now permits only
  that exact path, a 20 MiB ceiling, and its pinned SHA-256; every other tracked file retains the
  10 MiB ceiling. Resume after both PostgreSQL and SQLite jobs confirm these corrections.
- Historical PR #10/#13 overlap note: those branches were inspected during reconciliation, but the
  overlapping enterprise portal, dossier, wiki, registry, brand, template, and organization-chart
  collateral was subsequently removed from PR #9. Current `main` is the authority for that material;
  this finance branch does not claim to carry or supersede it. The public Blackridge case build is
  present on current `main` but remains a separate case world outside Sable Harbor's entities,
  books, and consolidation.
- Scoped-unit evidence-package increment: `shfin package-business-units` implements seven fresh,
  run-pinned entity/segment-scoped evidence packages, with ARU/BS&T governed by the same control path
  as Foundry Field, Willow, Atlas Meridian, Pale Sun, Project Cradle, and Advisory. Each contains a
  two-table SQLite journal/trial-balance evidence extract, journal CSV, scoped financial extracts,
  source-event lineage, asset/inventory/workforce extracts where selected, a unit-specific primary
  operating register, a one-sheet trial-balance workbook, reconciliation and safety results,
  manifest, and SHA-256 inventory. Generation requires a completed validated `standard` run,
  recreates stale output, validates each included journal and aggregate balance, proves the unit
  union plus disclosed excluded activity bridges to the enterprise without duplicate/unknown lines,
  and runs two recursive safety scans. Final current-tree CI evidence for all seven packages remains
  required. The primary registers cover Foundry contracts, Willow experiments, Atlas evaluations, Red Wash
  production batches, Cradle recovery runs, ARU waybills, and Advisory engagements.
- Exposure/debt classification closure: the reconciliations distinguish formal invoice/vendor-bill
  documents from other source-event operational receivables and accruals, disclose that residual
  bridge explicitly, and leave zero reconciliation difference to the GL. The debt schedule
  separately identifies forecast facilities and provisional acquisition
  opening balances while keeping unavailable covenant thresholds OPEN. This closes the allocation
  classification finding without inventing agreements or relabeling opening balances as new draws.
- Current `0015` integrity tranche: adds generated customer and
  vendor ownership, same-run links, journal-line equations, fiscal-period/book/date constraints,
  completed-run content immutability, and database-side run-completion guards. The central validation
  registry gates workbook and release producers, and the unit-package generator records the
  enterprise validation result. Final clean SQLite and PostgreSQL 16.6/18.6 execution plus workbook,
  unit, release, checksum, direct-guard, and artifact-safety evidence passed at `3fb7fc7`.
