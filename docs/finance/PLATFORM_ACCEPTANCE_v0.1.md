# Enterprise platform v0.1 acceptance

**Status:** LOCAL ACCEPTANCE PASS — CURRENT REMOTE PR CHECKS PENDING.
**Branch:** `finance/enterprise-financial-platform-v0.1`
**Implementation evidence commit:** `3fb7fc7d5ae3b138760e64560d3143fde18a8a47`
**Seed:** `20260831`

## Acceptance coverage

| Requirement | Implemented evidence |
|---|---|
| Canon discipline | Source lock, Markdown/JSON collision registers, fact states, canon guardrail tests |
| Enterprise perimeter | Principally one operating company; dedicated Red Wash legal operator; controlled ARU with wholly owned BS&T legal subsidiary; CoreCo products/programs, Cradle, Advisory, Emberline lineage, and non-entity consolidation |
| Accounting | Multi-entity books, periods, dimensions, immutable balanced journals, reversals, close, currencies and eliminations |
| Corporate subledgers | Contract-to-cash, payroll, procurement/AP, fixed assets/depreciation and debt/interest |
| Industrial subledgers | Mine production/inventory/sales, logistics waybills/custody, Cradle host-safe recovery and research programs |
| Planning | Base, low, high and stress scenarios; invariant shared synthetic pre-cutoff calibration periods; synthetic 2023–2026 monthly standard profile; 2016–2022 revenue calibration anchors |
| Reporting | Monthly P&L, balance sheet, simplified cash-flow/equity/working-capital, debt, fixed-asset and inventory views; named SQL queries; six-workbook suite with an explicit valuation scope limitation |
| Release control | Versioned table/column allowlist; new-database construction; stale-safe and same-persisted-run deterministic packaging; recursive generated-artifact scan |
| Portability | Alembic target `0015`; clean SQLite plus PostgreSQL 16.6/18.6 migration, populated-upgrade, generation, constraint, and artifact evidence passed at the implementation evidence commit |

## Implemented controls and evidence boundary

- The current `0015` migration target implements additional run ownership, ledger constraints,
  completed-evidence immutability, and completion guards. Fresh PostgreSQL 16.6 and 18.6 matrices
  each passed three migration/profile tests and produced the identical schema SHA-256
  `68d35c79bc07b59e8697e40cfdf5c7f49bc3e88e0a5ebd593a5dd26426d0a4b7`.
- A populated PostgreSQL 16 database upgraded from `0014` to `0015` while retaining 14 generation
  runs, 32 customers, 32 vendors, 1,061 journal entries, and 2,948 lines. It retained the stable
  consolidation book under SHI, reconciled the SHI/RWH/ARU/BST hierarchy and epistemic facets,
  reassigned ARU_HUB to BS&T, and left zero legacy `CONS` references across 19 entity foreign-key
  columns. A new current run generated, validated, balanced, and packaged from that upgraded database.
- Earlier checkpoints showed that full-history generation produced 48 monthly planning periods plus
  seven 2016–2022 revenue calibration anchors, not complete historical statements, and reconciled a
  trial balance at `$1,172,100,000.0000` debit and credit. Those totals are historical technical
  evidence, not current `0015` acceptance evidence or company history.
- The current implementation requires monthly and final balance sheets to reconcile and exposes
  reciprocal intercompany controls. The clean standard/base acceptance run passed all ten financial
  controls with assets `$216,450,437.8000`, liabilities `$140,653,104.4668`, total equity
  `$75,797,333.3332`, ending cash `$15,771,759.0333`, and balance-sheet difference `$0.0000`.
- The scenario registry applies driver multipliers only to SHI, `RWH`, and the ARU-group railway
  driver family in v0.1; railway economics are booked to BS&T. Cradle,
  Research, Advisory, and Capital driver families are recorded as governed inputs but are not
  applied to generated outputs; no causal attribution is claimed for them.
- The workbook generator implements six run-pinned XLSX files, exact semantic sheet specifications,
  explicit empty/limitation states, formula-backed local checks, and the database validation
  registry. The final SQLite, PostgreSQL 16.6, and PostgreSQL 18.6 runs generated and validated the
  complete six-workbook suite.
- The public release implementation builds a new database containing only versioned allowlisted
  tables and columns, removes stale outputs, requires a completed validated `standard` run, records
  selected-run and period/cutoff metadata, and marks its manifest `PASS` only after recursive safety
  scanning. Public packages (26 files), workbook suites (9 files), and seven unit-package trees (149
  files) passed manifest, checksum, bridge, and recursive-safety verification on both PostgreSQL
  versions. Repeated builds from each retained persisted snapshot were byte-identical. Independent
  fresh builds preserve real execution timestamps and therefore remain subject to the explicitly
  documented cross-build provenance boundary.
- The exact implementation evidence commit passed Ruff formatting/lint, strict mypy across 37 source
  files, and the complete 128-test collection: 125 passed locally and three PostgreSQL-only tests
  skipped locally; all three passed separately on each certified PostgreSQL version. All 21 named
  query paths passed against compatible base/comparison runs.
- One generator produces seven model-proposed, entity/segment-scoped evidence packages from the
  selected enterprise run. Each contains financial extracts, source lineage, scoped operational
  registers, a two-table SQLite evidence extract, a one-sheet trial-balance workbook, unit controls,
  an enterprise bridge, two safety scans, a manifest, and checksums. These are not standalone source
  databases or independently audited business-unit statements.

## Open acceptance boundary

This branch is a release candidate, not an audited production system. AR/AP exposure and debt
controls separately identify formal documents, disclosed residual source-event exposures, causal
facilities, and provisional acquisition opening balances. AR has due-date buckets; AP due dates are
unavailable in the current schema. Document exposure plus the disclosed residual bridge reconciles
to the GL. The generated unit packages are scoped release-candidate evidence. Local reviewer,
SQLite, PostgreSQL, workbook, release, reconciliation, and safety gates have passed; merge still
requires the current remote PR checks and mergeability gate to pass. This acceptance scope is PR #9
only; it does not authorize importing or changing PR #10/#13
collateral. OPEN and scenario facts remain labeled and must not be promoted to LOCKED canon through
acceptance.

All generated 2023–2026 numbers are synthetic scenario/calibration records. Passing technical
controls does not make them observed company results, historical books, or audited statements.
