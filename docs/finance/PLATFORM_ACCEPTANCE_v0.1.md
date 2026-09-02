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
| Reporting | Reconciled monthly P&L, balance sheet, cash flow, equity, working-capital, debt, fixed-asset and inventory rollforwards; named SQL queries; six-workbook suite; valuation/QoE bridge |
| Release control | Versioned table/column allowlist; new-database construction; deterministic stale-safe packaging; recursive generated-artifact scan |
| Portability | Explicit Alembic migrations through `0014`; local SQLite cycle passes; PostgreSQL matrix is encoded and under remote CI validation |

## Verified controls

- Clean SQLite migrations apply through revision `0014`; the expanded PostgreSQL 16 profile,
  scenario, two-seed, constraint-violation, migration, generation, and validation matrix passes.
- Full-history generation produces 48 monthly planning periods plus seven 2016–2022 revenue
  calibration anchors, not complete historical statements.
- Full-history trial balance reconciles at `$1,172,100,000.0000` debit and credit.
- Standard consolidated statements balance with zero difference after ARU–Red Wash eliminations.
- Six XLSX files generate and pass structural tests.
- The public release implementation builds a new database containing only versioned allowlisted
  tables and columns, removes stale outputs, supports controlled timestamps, and recursively scans
  generated CSV, SQLite, XLSX, manifests, and nested archives. CI publishes the reviewed package
  and six workbooks only after these gates pass.
- The committed platform passes Ruff, strict mypy, 86 local tests, and all enterprise, brand,
  organization, link, and public-safety validators; two PostgreSQL-only tests are skipped locally
  because `SHFIN_POSTGRES_TEST_URL` is not configured. Remote PostgreSQL 16 and SQLite jobs passed
  at checkpoint `9e29668` and are refreshed by every branch checkpoint.
- Seven standalone business-line generators produce fresh scoped SQLite evidence, financial and
  operational registers, workbooks, reconciliation/safety results, manifests, and checksums.

## Open acceptance boundary

This branch is a release candidate, not an accepted or audited production system. Remaining P1 is
explicitly visible in the aging/debt controls: legacy acquisition and summary balances are not all
represented by causal document-level subledgers, although the schedules bridge them exactly to the
GL. The generated unit packages are independently inspectable release-candidate evidence, but final
publication still requires the latest remote PostgreSQL/SQLite artifact jobs to pass and reviewer
acceptance. GitHub Wiki publication is also gated by integration to `main`; this mandate does not
authorize merging PR #9, #10, or #13. OPEN and scenario facts remain labeled and must not be promoted
to LOCKED canon through acceptance.
