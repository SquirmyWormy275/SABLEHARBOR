# Enterprise platform v0.1 acceptance

**Status:** RELEASE CANDIDATE — REVIEW BLOCKED — NOT ACCEPTED.
**Branch:** `finance/enterprise-financial-platform-v0.1`  
**Seed:** `20260831`

## Acceptance coverage

| Requirement | Implemented evidence |
|---|---|
| Canon discipline | Source lock, Markdown/JSON collision registers, fact states, canon guardrail tests |
| Enterprise perimeter | Parent, Red Wash, ARU, BS&T component, CoreCo products/programs, Cradle, Advisory, Emberline lineage and consolidation |
| Accounting | Multi-entity books, periods, dimensions, immutable balanced journals, reversals, close, currencies and eliminations |
| Corporate subledgers | Contract-to-cash, payroll, procurement/AP, fixed assets/depreciation and debt/interest |
| Industrial subledgers | Mine production/inventory/sales, logistics waybills/custody, Cradle host-safe recovery and research programs |
| Planning | Base, low, high and stress scenarios; invariant actual periods; 2023–2026 monthly standard profile; 2016–2022 revenue calibration anchors |
| Reporting | Reconciled statements, named SQL queries, six-workbook suite and valuation/QoE bridge |
| Release control | Versioned table/column allowlist; new-database construction; deterministic stale-safe packaging; recursive generated-artifact scan |
| Portability | Explicit Alembic migrations through uncommitted `0012`; local SQLite cycle passes; PostgreSQL `0012` matrix is encoded but remote evidence remains at committed `0008` |

## Verified controls

- Clean SQLite migrations apply through revision `0012`; PostgreSQL `0008` migration, generation,
  and validation CI passes. The expanded all-profile/two-seed PostgreSQL matrix is wired into CI
  and passes a local SQLite backend surrogate; acceptance remains open until PostgreSQL 16 runs it.
- Full-history generation produces 48 monthly planning periods plus seven 2016–2022 revenue
  calibration anchors, not complete historical statements.
- Full-history trial balance reconciles at `$1,172,100,000.0000` debit and credit.
- Standard consolidated statements balance with zero difference after ARU–Red Wash eliminations.
- Six XLSX files generate and pass structural tests.
- The public release implementation builds a new database containing only versioned allowlisted
  tables and columns, removes stale outputs, supports controlled timestamps, and recursively scans
  generated CSV, SQLite, XLSX, manifests, and nested archives. CI publishes the reviewed package
  and six workbooks only after these gates pass.
- The current uncommitted Stage 1 tranche passes Ruff, strict mypy, and 78 local tests; two
  PostgreSQL-only tests are skipped locally because `SHFIN_POSTGRES_TEST_URL` is not configured.
  At the committed PR head, two PostgreSQL jobs, two SQLite jobs, and organization render
  validation pass remotely; those checks do not cover uncommitted migrations `0009`–`0012`.

## Open acceptance boundary

Passing the legacy commands above does not establish acceptance. The controlling P0/P1 findings are
in `docs/handoffs/SABLE_HARBOR_CODEX_EXECUTION_HANDOFF_2026-09-01.md`. Migration immutability
is implemented through `8f61b43382fd9adfcc05059bd6efbf3686af9e11`. Run/scenario isolation,
common-actual inclusion, operational-fact ownership, explicit read contexts, migration cycles, and
schema fingerprints are implemented through migration `0007`. Migration `0008` adds centralized
run/build identity, cutoff fields, dynamic head discovery, read-only validation, and run-owned
profile generation. The uncommitted `0009`–`0012` tranche adds a portable complete input manifest,
content-addressed build and actual-dataset identity, explicit profile contracts, immutable
idempotent completion timestamps, content-addressed coexisting run IDs, and SQLite-proven two-seed
natural-key namespacing with explicit populated-downgrade refusal, non-null generation ownership,
same-run composite parent/child keys, compatible actual-dataset attachment, and database-guarded
lifecycle transitions. Revision `0012` adds run-scoped period-close state; accounting trial balance,
lineage, and close APIs now require or unambiguously resolve a compatible run context. Closing a
scenario context closes its included common-actual layer, and posting/reversal reject an unrelated
active session context. A same-seed base/stress regression proves that an existing shared-actual
marker remains unchanged while the sibling scenario receives its missing close marker; repeated
closure of the resulting compatible context is idempotent. Every profile that first completes the
common-actual layer persists the same standard-actual superset and completion marker; a
bidirectional baseline/standard regression proves profile-order-independent standard journal
counts and debit totals. Explicit trial-balance comparison rejects same-run, incomplete,
cross-seed, profile, actual-dataset, cutoff, forecast-start, and schema-incompatible contexts.
Each compatibility dimension has a one-variable-at-a-time semantic regression, and a base/stress
regression proves a scenario-attributable delta. The PostgreSQL two-seed and violation matrix is
implemented, including explicit private-profile authorization, but remote evidence remains open. Standard monthly accounting controls, driver
values, production, freight movements, and ending inventory now partition pre-cutoff actuals from
scenario-owned forecasts, with a two-scenario semantic ownership audit. Effective-dated master and
commitment records remain whole records rather than periodic facts. Workbook routing now uses an exact
semantic registry for every sheet, with purpose, query, units, deterministic ordering, tolerance, and
empty-state metadata; workbook tests compare database query headers to generated sheets and distinguish
balance-sheet, P&L, journal-lineage, and industrial routes. Integrated monthly
statements and rollforwards, driver-based scenarios, accurate historical claims, and CI review
artifacts remain open. This synthetic platform is not accepted, integration-ready, production-ready,
or independently auditable.
