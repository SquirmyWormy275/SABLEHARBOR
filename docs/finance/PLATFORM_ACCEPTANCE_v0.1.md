# Enterprise platform v0.1 acceptance

**Status:** Implementation complete; quantitative and legal assumptions remain noncanonical.  
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

## Completion boundary

Platform v0.1 is complete when the above commands pass. Changes to `OPEN` legal, transaction, reserve, physical-asset, board, or quantitative facts are scenario/configuration revisions, not missing software functionality. Production use would require qualified accounting, legal, engineering, environmental, tax, security, and assurance review.

