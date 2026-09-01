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
| Planning | Base, low, high and stress scenarios; assumptions and sensitivities; 2023–2026 monthly standard profile; 2016–2026 history |
| Reporting | Reconciled statements, named SQL queries, six-workbook suite and valuation/QoE bridge |
| Release control | Deterministic SQLite public package, checksums, manifest, limitations and public-safety scan |
| Portability | Alembic migrations; SQLite verified locally; PostgreSQL 16 service job defined in CI |

## Verified controls

- Clean migrations apply through revision `0002`.
- Full-history generation produces 48 monthly planning periods plus annual history from 2016.
- Full-history trial balance reconciles at `$1,172,100,000.0000` debit and credit.
- Standard consolidated statements balance with zero difference after ARU–Red Wash eliminations.
- Six XLSX files generate and pass structural tests.
- Public release manifest and checksums generate deterministically.
- Ruff, strict mypy, canon/privacy checks, and all 27 local tests pass.

## Open acceptance boundary

Passing the legacy commands above does not establish acceptance. The controlling P0/P1 findings are
in `docs/handoffs/SABLE_HARBOR_CODEX_EXECUTION_HANDOFF_2026-09-01.md`. Migration immutability
is implemented at `4cb7671918d81b8093d2a4828e84a65fd1a93bcc` for SQLite. Initial
same-database base/stress journal and scenario-value isolation is implemented at
`05314a7f18828bb58e98ae68ed2568570d8c1013`; applicable subledgers and every reporting/export
surface are not yet fully run-scoped. PostgreSQL
upgrade/downgrade/upgrade and schema-equivalence evidence remains required. Run/scenario isolation,
workbook semantics, public export allowlisting, generated-artifact scanning, integrated monthly
statements and rollforwards, driver-based scenarios, accurate historical claims, and CI review
artifacts remain open. This synthetic platform is not accepted, integration-ready, production-ready,
or independently auditable.
