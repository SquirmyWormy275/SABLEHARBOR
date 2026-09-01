<p align="center"><img src="../../assets/brand/logos/blood-sweat-and-tears-railway__primary-horizontal.svg" alt="Blood, Sweat & Tears Railway" width="720" /></p>

# Blood, Sweat & Tears Railway

**Classification:** railway or short-line operating component within ARU  
**Dossier state:** review candidate  
**Operating-company home:** American Resource Utility

Blood, Sweat & Tears Railway—BS&T—is a locked piece of ARU corporate archaeology. Its exact legal name, route, asset count, interchange relationships, and history remain open.

## Status and scope

- Canon: BS&T name and relationship to ARU are locked.
- Separate legal entity, route system, fleet, terminals, management, workforce, and economics are not established.
- Standalone BS&T database, fleet/inventory register, financial package, and letterhead: **NOT MATERIALIZED**.

## Canon and history

- [Corporate Lore Canon v0.2](../canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md) — ARU and BS&T sections
- [ARU, BS&T, and Advisory narrative](../organization/ARU_BST_AND_ADVISORY.md)
- [ARU dossier](AMERICAN_RESOURCE_UTILITY.md)

## Identity and collateral

- [Primary SVG](../../assets/brand/logos/blood-sweat-and-tears-railway__primary-horizontal.svg) · [PNG](../../assets/brand/logos/blood-sweat-and-tears-railway__primary-horizontal.png)
- [Mark SVG](../../assets/brand/logos/blood-sweat-and-tears-railway__mark.svg) · [PNG](../../assets/brand/logos/blood-sweat-and-tears-railway__mark.png)
- [Reverse SVG](../../assets/brand/logos/blood-sweat-and-tears-railway__reverse-horizontal.svg) · [PNG](../../assets/brand/logos/blood-sweat-and-tears-railway__reverse-horizontal.png)
- [Corporate collateral](../../assets/brand/collateral/README.md)

## Organization and authority

[![ARU and BS&T organization](../organization/assets/aru-bst-organization-2026.svg)](../organization/ARU_BST_ORGANIZATION.md)

BS&T uses the combined ARU/BS&T functional view. No separate management or legal hierarchy is implied.

## Financials and accounting

The finance release candidate models logistics under entity `ARU` and segment `ARU_BST`; it does not provide a separate BS&T entity/segment discriminator. Relevant tables include `waybill`, `freight_movement`, assets, depreciation, workforce/payroll, procurement, debt, and journals. Relevant queries include [`aru_route_customer_margin`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/aru_route_customer_margin.sql), [`fixed_asset_rollforward`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/fixed_asset_rollforward.sql), and [`entity_trial_balance`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/entity_trial_balance.sql).

## Inventory, assets, and operations

Future BS&T scope includes route and interchange map, waybills, locomotives, rolling stock, track and right-of-way responsibility, terminals, maintenance condition, crews, fuel, custody, customers, rates, incidents, and linked financial records. None of those detailed facts is accepted merely because the logo or combined chart exists.

## Database and exports

A standalone component package requires a reliable BS&T discriminator within the ARU schema before `blood-sweat-and-tears-railway.sqlite` can be built without mixing unrelated ARU activity. Current state: **NOT MATERIALIZED**.

## Audit controls and unresolved facts

Controls must prove component scoping, waybill/custody completeness, revenue/cost and asset reconciliation, maintenance/availability lineage, and roll-up to ARU and enterprise books. Open: legal name, routes, interchanges, asset estate, management, workforce, history, economics, letterhead, and standalone release.

## Download map

- [ARU dossier](AMERICAN_RESOURCE_UTILITY.md)
- [Combined organization](../organization/ARU_BST_ORGANIZATION.md)
- [Brand system](../../assets/brand/README.md)
- [Finance register](../data/FINANCE_RELEASE_CANDIDATE.md)
- [Unit package standard](../audit/UNIT_PACKAGE_STANDARD.md)
- [Registry](registry.json)
