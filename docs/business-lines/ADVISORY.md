<p align="center"><img src="../../assets/brand/logos/advisory__primary-horizontal.svg" alt="Advisory" width="720" /></p>

# Advisory

**Classification:** emerging current business line  
**Dossier state:** review candidate

Advisory is the method-transfer line for situations where the client should own the operating system rather than purchase a permanent Sable Harbor-operated product. Its exact name, leader, launch date, service catalog, organizational home, staffing, and P&L remain open.

## Status and scope

- Canon: direction locked; operating details remain provisional/open.
- Finance coverage: partial release-candidate engagement, customer, time, cost, invoice, receipt, and journal records.
- Standalone database, engagement inventory, financial package, and unit letterhead: **NOT MATERIALIZED**

## Canon and history

- [Corporate Lore Canon v0.2](../canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md)
- [ARU, BS&T, and Advisory narrative](../organization/ARU_BST_AND_ADVISORY.md)
- [Decision Register](../canon/DECISION_REGISTER.md)

## Identity and collateral

- [Primary SVG](../../assets/brand/logos/advisory__primary-horizontal.svg) · [PNG](../../assets/brand/logos/advisory__primary-horizontal.png)
- [Stacked SVG](../../assets/brand/logos/advisory__stacked.svg) · [Mark SVG](../../assets/brand/logos/advisory__mark.svg)
- [Reverse SVG](../../assets/brand/logos/advisory__reverse-horizontal.svg) · [One-color SVG](../../assets/brand/logos/advisory__one-color-horizontal.svg)
- [Corporate collateral](../../assets/brand/collateral/README.md)

## Organization and authority

- [Advisory context narrative](../organization/ARU_BST_AND_ADVISORY.md)
- [Advisory briefing chart](../organization/briefing/images/08_advisory_organization.png)

No exact accepted reporting home or named leader is implied.

## Financials and accounting

- Entity: `SHI`
- Segment: `ADVISORY`
- Tables: `customer`, `customer_contract`, `engagement`, `project_task`, `time_entry`, `project_cost`, `engagement_invoice_link`, invoices, receipts, `journal_entry`, `journal_line`
- Queries: [`engagement_margin_wip`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/engagement_margin_wip.sql), [`customer_profitability`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/customer_profitability.sql), [`employee_loaded_cost`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/employee_loaded_cost.sql), [`entity_trial_balance`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/entity_trial_balance.sql)
- Workbooks: software/services, GL/close, and capital/M&A/valuation suites

## Inventory, assets, and operations

The operating perimeter includes engagement roster, scope and milestones, tasks, time, labor rates, direct costs, WIP, invoices, collections, client-owned versus Sable Harbor-owned deliverables, method-transfer status, and linked journals. No accepted engagement register is yet published.

## Database and exports

Target: allowlisted `advisory.sqlite`, engagement/time/cost/WIP extracts, client and contract schedules, unit statements, controls, manifest, and checksums. Current state: **NOT MATERIALIZED**.

## Audit controls and unresolved facts

Controls must reconcile time/cost/WIP to billing and revenue, preserve client ownership boundaries, isolate confidential engagement data, trace source records to journals, and reconcile unit results to enterprise statements. Open: name, leader, organization home, launch, catalog, staffing, P&L, letterhead, and standalone release.

## Download map

- [Advisory organization context](../organization/ARU_BST_AND_ADVISORY.md)
- [Brand system](../../assets/brand/README.md)
- [Finance register](../data/FINANCE_RELEASE_CANDIDATE.md)
- [Unit package standard](../audit/UNIT_PACKAGE_STANDARD.md)
- [Registry](registry.json)
