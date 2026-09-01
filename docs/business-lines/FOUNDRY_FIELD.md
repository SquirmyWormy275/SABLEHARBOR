<p align="center"><img src="../../assets/brand/logos/foundry-field__primary-horizontal.svg" alt="Foundry Field" width="720" /></p>

# Foundry Field

**Classification:** current core business line  
**Dossier state:** review-candidate index  
**Finance/data state:** PR #9 release candidate; not accepted

Foundry Field is Sable Harbor's primary operating and product application layer. Foundry is the underlying substrate; Foundry Field is the business line through which the system is applied to real operating environments.

## Status and scope

- Canon: locked name and distinction from Foundry; detailed legal treatment, leadership, customer roster, headcount, and unit P&L remain open.
- Standalone database, inventory, and financial package: **NOT MATERIALIZED**
- Unit-specific letterhead: **NOT MATERIALIZED**

## Canon and history

- [Corporate Lore Canon v0.2](../canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md) — Foundry and Foundry Field sections
- [Decision Register](../canon/DECISION_REGISTER.md)
- [Foundry / Foundry Field organization narrative](../organization/FOUNDRY_AND_FOUNDRY_FIELD.md)

## Identity and collateral

- [Primary SVG](../../assets/brand/logos/foundry-field__primary-horizontal.svg) · [PNG](../../assets/brand/logos/foundry-field__primary-horizontal.png)
- [Stacked SVG](../../assets/brand/logos/foundry-field__stacked.svg) · [PNG](../../assets/brand/logos/foundry-field__stacked.png)
- [Mark SVG](../../assets/brand/logos/foundry-field__mark.svg) · [PNG](../../assets/brand/logos/foundry-field__mark.png)
- [Reverse SVG](../../assets/brand/logos/foundry-field__reverse-horizontal.svg) · [One-color SVG](../../assets/brand/logos/foundry-field__one-color-horizontal.svg)
- [Corporate collateral and stationery](../../assets/brand/collateral/README.md)

Corporate stationery exists; a distinct Foundry Field letterhead remains ungenerated and unaccepted.

## Organization and authority

[![Foundry Field organization](../organization/assets/foundry-field-organization-2026.svg)](../organization/FOUNDRY_FIELD_ORGANIZATION.md)

- [Organization page](../organization/FOUNDRY_FIELD_ORGANIZATION.md)
- [Leadership and authority map](../organization/2026_LEADERSHIP_AND_AUTHORITY_MAP.md)

## Financials and accounting

Release-candidate entity/segment scope:

- Entity: `SHI`
- Segments: `FOUNDRY_FIELD`, `CORE`, `DELIVERY`
- Tables: `customer`, `customer_contract`, `performance_obligation`, `invoice`, `invoice_line`, `revenue_recognition`, `cash_receipt`, `engagement`, `project_task`, `time_entry`, `project_cost`, `engagement_invoice_link`, `journal_entry`, `journal_line`
- Workbooks: `SABLE_HARBOR_SOFTWARE_AND_SERVICES_v0.1.xlsx`, `SABLE_HARBOR_GL_CLOSE_AND_SUBLEDGERS_v0.1.xlsx`

Queries: [`customer_arr_bridge`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/customer_arr_bridge.sql), [`customer_profitability`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/customer_profitability.sql), [`engagement_margin_wip`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/engagement_margin_wip.sql), [`deferred_revenue_rollforward`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/deferred_revenue_rollforward.sql), [`entity_trial_balance`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/entity_trial_balance.sql).

## Inventory, assets, and operations

Customer contracts, deployments, implementation backlog, engagement WIP, time and cost records, delivery labor, software/service operating records, and linked journals define the current source perimeter. This is not yet a complete standalone product/customer inventory.

## Database and exports

Target: allowlisted `foundry-field.sqlite`, CSV extracts, contract/revenue and engagement schedules, unit statements, controls, manifest, and checksums. Current state: **NOT MATERIALIZED**.

## Audit controls and unresolved facts

Controls must reconcile contracts → invoices → revenue/receipts, engagement time/cost/WIP → invoices, unit trial balance → enterprise ledger, and any scoped release → manifest/checksums. Open: legal treatment, leader/reporting line, accepted customer roster, headcount, unit P&L, unit letterhead, and standalone package.

## Download map

- [Organization](../organization/FOUNDRY_FIELD_ORGANIZATION.md)
- [Brand system](../../assets/brand/README.md)
- [Finance register](../data/FINANCE_RELEASE_CANDIDATE.md)
- [Unit package standard](../audit/UNIT_PACKAGE_STANDARD.md)
- [Registry](registry.json)
