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
| Release control | Review-blocked package scaffold; allowlisted SQLite construction and generated-artifact scan remain open |
| Portability | Explicit Alembic migrations and SQLite/PostgreSQL migration-cycle CI through `0007` |

## Verified controls

- Clean migrations apply through revision `0007`; SQLite and PostgreSQL
  upgrade/downgrade/upgrade cycles pass.
- Full-history generation produces 48 monthly planning periods plus seven 2016–2022 revenue
  calibration anchors, not complete historical statements.
- Full-history trial balance reconciles at `$1,172,100,000.0000` debit and credit.
- Standard consolidated statements balance with zero difference after ARU–Red Wash eliminations.
- Six XLSX files generate and pass structural tests.
- The current public release package is review blocked pending allowlist construction and generated
  artifact scanning.
- Ruff, strict mypy, canon/privacy checks, and 43 local tests pass; one PostgreSQL-only test runs in
  CI and passes there.

## Open acceptance boundary

Passing the legacy commands above does not establish acceptance. The controlling P0/P1 findings are
in `docs/handoffs/SABLE_HARBOR_CODEX_EXECUTION_HANDOFF_2026-09-01.md`. Migration immutability
is implemented through `8f61b43382fd9adfcc05059bd6efbf3686af9e11`. Run/scenario isolation,
common-actual inclusion, operational-fact ownership, explicit read contexts, migration cycles, and
schema fingerprints are implemented through migration `0007`. Workbook semantics, public export
allowlisting, generated-artifact scanning, integrated monthly
statements and rollforwards, driver-based scenarios, accurate historical claims, and CI review
artifacts remain open. This synthetic platform is not accepted, integration-ready, production-ready,
or independently auditable.
