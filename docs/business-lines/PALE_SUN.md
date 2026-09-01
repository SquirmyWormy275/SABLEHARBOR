<p align="center"><img src="../../assets/brand/logos/pale-sun__primary-horizontal.svg" alt="Pale Sun" width="720" /></p>

# Pale Sun

**Classification:** current operating business line  
**Operating asset:** Red Wash Mine  
**Dossier state:** review candidate

Pale Sun owns the operating-control thesis around Red Wash. The mine is an asset and operating environment; Pale Sun is the business line through which the enterprise applies control, learning, and economic discipline.

## Status and scope

- Canon: locked name, role, and Red Wash relationship; legal structure, transaction terms, reserves, permits, workforce, mine plan, production/economics, and unit P&L remain open or scenario-controlled.
- Standalone Pale Sun/Red Wash database, reserve report, inventory register, financial package, and unit letterhead: **NOT MATERIALIZED**

## Canon and history

- [Corporate Lore Canon v0.2](../canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md)
- [Pale Sun and Red Wash narrative](../organization/PALE_SUN_AND_RED_WASH.md)
- [Red Wash Mine dossier](RED_WASH_MINE.md)

## Identity and collateral

- [Primary SVG](../../assets/brand/logos/pale-sun__primary-horizontal.svg) · [PNG](../../assets/brand/logos/pale-sun__primary-horizontal.png)
- [Stacked SVG](../../assets/brand/logos/pale-sun__stacked.svg) · [Mark SVG](../../assets/brand/logos/pale-sun__mark.svg)
- [Reverse SVG](../../assets/brand/logos/pale-sun__reverse-horizontal.svg) · [One-color SVG](../../assets/brand/logos/pale-sun__one-color-horizontal.svg)
- [Corporate collateral](../../assets/brand/collateral/README.md)

## Organization and authority

[![Pale Sun and Red Wash organization](../organization/assets/pale-sun-red-wash-organization-2026.svg)](../organization/PALE_SUN_RED_WASH_ORGANIZATION.md)

The chart is a combined functional view, not a reserve, ownership, or legal-entity statement.

## Financials and accounting

- Entity: `RWH`
- Segment: `PALE_SUN`
- Tables: `mine_production_batch`, `uranium_shipment`, `inventory_lot`, `production_record`, `environmental_obligation`, `fixed_asset`, `depreciation_record`, `journal_entry`, `journal_line`
- Queries: [`red_wash_unit_cost_bridge`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/red_wash_unit_cost_bridge.sql), [`mine_inventory_shipment_reconciliation`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/mine_inventory_shipment_reconciliation.sql), [`fixed_asset_rollforward`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/fixed_asset_rollforward.sql), [`debt_covenant_calculation`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/debt_covenant_calculation.sql), [`entity_trial_balance`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/entity_trial_balance.sql)
- Workbooks: industrial operations, GL/close, and capital/M&A/valuation suites

## Inventory, assets, and operations

Required perimeter: production batches, ore/feed/recovery records, concentrate inventory and shipments, environmental obligations and ARO, mine/mill fixed assets and depreciation/depletion, workforce and procurement where represented, debt, cash, receivables/payables, and ARU intercompany freight. Scenario rows are not reserve estimates or audited actuals.

## Database and exports

Target: allowlisted `pale-sun-red-wash.sqlite`, production/inventory/shipments CSVs, asset and ARO registers, financial statements, mine economics, controls, manifest, and checksums. Current state: **NOT MATERIALIZED**.

## Audit controls and unresolved facts

Controls must reconcile feed × grade × recovery to production, opening + production − shipment to closing inventory, shipment to revenue/receivable, production costs to inventory/COGS, assets/ARO to the ledger, intercompany freight to eliminations, and unit books to enterprise consolidation. Open technical, legal, environmental, reserve, asset, labor, transaction, and economic facts remain open.

## Download map

- [Combined organization](../organization/PALE_SUN_RED_WASH_ORGANIZATION.md)
- [Red Wash asset dossier](RED_WASH_MINE.md)
- [Brand system](../../assets/brand/README.md)
- [Finance register](../data/FINANCE_RELEASE_CANDIDATE.md)
- [Unit package standard](../audit/UNIT_PACKAGE_STANDARD.md)
- [Registry](registry.json)
