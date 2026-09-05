# Enterprise platform v0.1 acceptance

**Status:** RELEASE CANDIDATE — REVIEW BLOCKED — NOT ACCEPTED.
**Branch:** `finance/enterprise-financial-platform-v0.1`
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
| Portability | Current Alembic target `0015`; final clean SQLite and PostgreSQL migration/generation evidence for this worktree is pending |

## Implemented controls and evidence boundary

- The current `0015` migration target implements additional run ownership, ledger constraints,
  completed-evidence immutability, and completion guards. A fresh current-tree SQLite cycle and the
  PostgreSQL 16 profile/scenario/two-seed/constraint matrix are required before acceptance; this
  document does not claim that final evidence has run.
- Earlier checkpoints showed that full-history generation produced 48 monthly planning periods plus
  seven 2016–2022 revenue calibration anchors, not complete historical statements, and reconciled a
  trial balance at `$1,172,100,000.0000` debit and credit. Those totals are historical technical
  evidence, not current `0015` acceptance evidence or company history.
- The current implementation requires monthly and final balance sheets to reconcile and exposes
  reciprocal intercompany controls. Final current-tree results remain to be recorded from the
  acceptance run.
- The scenario registry applies driver multipliers only to SHI, `RWH`, and the ARU-group railway
  driver family in v0.1; railway economics are booked to BS&T. Cradle,
  Research, Advisory, and Capital driver families are recorded as governed inputs but are not
  applied to generated outputs; no causal attribution is claimed for them.
- The workbook generator implements six run-pinned XLSX files, exact semantic sheet specifications,
  explicit empty/limitation states, formula-backed local checks, and the database validation
  registry. Final current-tree workbook generation and structural/semantic tests remain required.
- The public release implementation builds a new database containing only versioned allowlisted
  tables and columns, removes stale outputs, requires a completed validated `standard` run, records
  selected-run and period/cutoff metadata, and marks its manifest `PASS` only after recursive safety
  scanning. Final current-tree package/checksum/safety evidence remains required.
- Ruff, strict mypy, 86 local tests, and remote SQLite/PostgreSQL jobs at checkpoint `9e29668` are
  historical checkpoint evidence only. They must not be represented as proof of the current
  uncommitted integration state.
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
to the GL. The generated unit packages are scoped release-candidate evidence, but final publication
and merge still require the latest current-tree PostgreSQL/SQLite artifact jobs and reviewer gates to
pass. This acceptance scope is PR #9 only; it does not authorize importing or changing PR #10/#13
collateral. OPEN and scenario facts remain labeled and must not be promoted to LOCKED canon through
acceptance.

All generated 2023–2026 numbers are synthetic scenario/calibration records. Passing technical
controls does not make them observed company results, historical books, or audited statements.
