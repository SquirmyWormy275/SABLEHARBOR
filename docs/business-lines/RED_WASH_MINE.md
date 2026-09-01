<p align="center"><img src="../../assets/brand/logos/red-wash-mine__primary-horizontal.svg" alt="Red Wash Mine" width="720" /></p>

# Red Wash Mine

**Classification:** operating asset and environment under Pale Sun  
**Dossier state:** review candidate  
**Business-line home:** Pale Sun

Red Wash is the fictional uranium mine around which Pale Sun's operating-control thesis is expressed. A mine identity does not itself establish ownership, reserves, permits, production, economics, or a separate legal entity.

## Status and scope

- Canon: mine name and relationship to Pale Sun are locked.
- Detailed asset facts, reserves, mine plan, permits, production, workforce, closure liabilities, transaction structure, and economics remain open or scenario-controlled.
- Standalone mine database, inventory register, reserve report, financial package, and letterhead: **NOT MATERIALIZED**.

## Canon and history

- [Corporate Lore Canon v0.2](../canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md)
- [Pale Sun and Red Wash narrative](../organization/PALE_SUN_AND_RED_WASH.md)
- [Pale Sun dossier](PALE_SUN.md)

## Identity and collateral

- [Primary SVG](../../assets/brand/logos/red-wash-mine__primary-horizontal.svg) · [PNG](../../assets/brand/logos/red-wash-mine__primary-horizontal.png)
- [Mark SVG](../../assets/brand/logos/red-wash-mine__mark.svg) · [PNG](../../assets/brand/logos/red-wash-mine__mark.png)
- [Reverse SVG](../../assets/brand/logos/red-wash-mine__reverse-horizontal.svg) · [PNG](../../assets/brand/logos/red-wash-mine__reverse-horizontal.png)
- [Red Wash / Pale Sun endorsed lockup](RED_WASH_PALE_SUN.md)
- [Corporate collateral](../../assets/brand/collateral/README.md)

## Organization and authority

[![Pale Sun and Red Wash organization](../organization/assets/pale-sun-red-wash-organization-2026.svg)](../organization/PALE_SUN_RED_WASH_ORGANIZATION.md)

The combined chart shows supported operating interfaces. It is not a legal ownership chart, staffing plan, or technical-responsibility matrix.

## Financials and accounting

Release-candidate scope is shared with Pale Sun:

- Entity: `RWH`
- Segment: `PALE_SUN`
- Site: `RED_WASH`
- Tables: `mine_production_batch`, `uranium_shipment`, `inventory_lot`, `production_record`, `environmental_obligation`, `fixed_asset`, `depreciation_record`, `worker`, procurement/debt records, `journal_entry`, and `journal_line`
- Queries: [`red_wash_unit_cost_bridge`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/red_wash_unit_cost_bridge.sql), [`mine_inventory_shipment_reconciliation`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/mine_inventory_shipment_reconciliation.sql), [`fixed_asset_rollforward`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/fixed_asset_rollforward.sql), and [`entity_trial_balance`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/entity_trial_balance.sql).

These are synthetic/model release-candidate sources, not reserve estimates or audited actuals.

## Inventory, assets, and operations

Future mine audit scope includes mineral/technical source assumptions, production batches, ore/feed and recovery, concentrate inventory, shipments, consumables and spares, mobile/fixed plant, maintenance condition, workforce, environmental obligations, ARO, contracts, receivables/payables, debt, and intercompany freight.

## Database and exports

Target: `red-wash-mine.sqlite` plus production, inventory, asset, maintenance, environmental, financial, and control extracts; manifest and checksums; and reconciliation to the Pale Sun/RWH and enterprise books. Current state: **NOT MATERIALIZED**.

## Audit controls and unresolved facts

Controls must reconcile feed × grade × recovery, production and inventory, shipment and revenue, costs and COGS, assets and depreciation/depletion, ARO, intercompany freight, and unit books. Every technical, reserve, legal, permitting, asset, labor, transaction, and economic fact not explicitly locked remains open.

## Download map

- [Pale Sun dossier](PALE_SUN.md)
- [Combined organization](../organization/PALE_SUN_RED_WASH_ORGANIZATION.md)
- [Brand system](../../assets/brand/README.md)
- [Finance register](../data/FINANCE_RELEASE_CANDIDATE.md)
- [Unit package standard](../audit/UNIT_PACKAGE_STANDARD.md)
- [Registry](registry.json)
