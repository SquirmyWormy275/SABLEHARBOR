<p align="center"><img src="../../assets/brand/logos/american-resource-utility__primary-horizontal.svg" alt="American Resource Utility" width="720" /></p>

# American Resource Utility

**Classification:** current distinct operating company and core business line  
**Dossier state:** review-candidate index  
**Finance/data state:** PR #9 release candidate; not accepted  
**Parent:** Sable Harbor

ARU is an established acquired regional resource-logistics operator with legacy customers, employees, dispatch practices, terminals, equipment, and operating knowledge. Blood, Sweat & Tears Railway remains an operating component within the ARU system.

## Status and scope

This dossier is the ARU audit portal. It links ARU identity, shared stationery, organization, logistics and finance records, inventory/asset scope, controls, and unresolved facts. It does not create legal, route, asset, workforce, or quantitative facts absent from canon.

- Canon state: **LOCKED name and operating role**; detailed history, routes, assets, workforce, legal structure, and economics remain `OPEN` or scenario-controlled.
- Standalone ARU SQLite database: **NOT MATERIALIZED**
- Standalone ARU inventory register: **NOT MATERIALIZED**
- Standalone ARU financial workbook/statements: **NOT MATERIALIZED**
- ARU-specific letterhead: **NOT MATERIALIZED**

## Canon and history

- [Corporate Lore Canon v0.2](../canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md) — search for **American Resource Utility**, **Blood, Sweat & Tears Railway**, and **Logistics and Advisory**.
- [Decision Register](../canon/DECISION_REGISTER.md)
- [Continuity Audit](../canon/SABLE_HARBOR_CONTINUITY_AUDIT_v0.2.md)
- [ARU, BS&T, and Advisory organization narrative](../organization/ARU_BST_AND_ADVISORY.md)

## Identity and collateral

| Asset | SVG | PNG |
|---|---|---|
| Primary horizontal | [SVG](../../assets/brand/logos/american-resource-utility__primary-horizontal.svg) | [PNG](../../assets/brand/logos/american-resource-utility__primary-horizontal.png) |
| Stacked | [SVG](../../assets/brand/logos/american-resource-utility__stacked.svg) | [PNG](../../assets/brand/logos/american-resource-utility__stacked.png) |
| Mark | [SVG](../../assets/brand/logos/american-resource-utility__mark.svg) | [PNG](../../assets/brand/logos/american-resource-utility__mark.png) |
| Reverse | [SVG](../../assets/brand/logos/american-resource-utility__reverse-horizontal.svg) | [PNG](../../assets/brand/logos/american-resource-utility__reverse-horizontal.png) |
| One color | [SVG](../../assets/brand/logos/american-resource-utility__one-color-horizontal.svg) | [PNG](../../assets/brand/logos/american-resource-utility__one-color-horizontal.png) |

Shared corporate collateral available for ARU adaptation:

- [Collateral index](../../assets/brand/collateral/README.md)
- [US Letter letterhead](../../assets/brand/collateral/letterhead/sable-harbor-letterhead-us-letter.docx)
- [A4 letterhead](../../assets/brand/collateral/letterhead/sable-harbor-letterhead-a4.docx)
- [Memorandum template](../../assets/brand/collateral/memo/sable-harbor-memorandum-us-letter.docx)
- [Report templates](../../assets/brand/collateral/report/)
- [Presentation template](../../assets/brand/collateral/presentation/sable-harbor-presentation-template-16x9.pptx)

A corporate template carrying the ARU logo is not yet an accepted ARU letterhead. A unit release must be proofed, registered, and checksummed.

## Organization and authority

[![ARU and BS&T organization](../organization/assets/aru-bst-organization-2026.svg)](../organization/ARU_BST_ORGANIZATION.md)

- [ARU/BS&T organization page](../organization/ARU_BST_ORGANIZATION.md)
- [Leadership and authority map](../organization/2026_LEADERSHIP_AND_AUTHORITY_MAP.md)

The chart is a canon-supported combined view. Exact legal entity chain, named management, reporting lines, vacancies, and workforce composition remain open unless the source explicitly locks them.

## Financials and accounting

**Release-candidate scope at `1f294440a11e724e5f1bdcd3a7f59f7342169bfe`:**

- Entity code: `ARU`
- Segment code: `ARU_BST`
- Core tables: `waybill`, `freight_movement`, `fixed_asset`, `depreciation_record`, `worker`, `payroll_run`, `payroll_line`, `vendor`, `purchase_order`, `goods_receipt`, `vendor_bill`, `vendor_payment`, `debt_facility`, `debt_draw`, `interest_accrual`, `journal_entry`, `journal_line`
- Workbook classes: `SABLE_HARBOR_INDUSTRIAL_OPERATIONS_v0.1.xlsx`, `SABLE_HARBOR_GL_CLOSE_AND_SUBLEDGERS_v0.1.xlsx`, `SABLE_HARBOR_CAPITAL_MA_AND_VALUATION_v0.1.xlsx`

Named query entry points:

- [`aru_route_customer_margin`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/aru_route_customer_margin.sql)
- [`fixed_asset_rollforward`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/fixed_asset_rollforward.sql)
- [`employee_loaded_cost`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/employee_loaded_cost.sql)
- [`vendor_spend_concentration`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/vendor_spend_concentration.sql)
- [`ar_ap_aging`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/ar_ap_aging.sql)
- [`debt_covenant_calculation`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/debt_covenant_calculation.sql)
- [`intercompany_mismatch_elimination`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/intercompany_mismatch_elimination.sql)
- [`entity_trial_balance`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/entity_trial_balance.sql)
- [`journal_to_source_trace`](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/1f294440a11e724e5f1bdcd3a7f59f7342169bfe/db/sql/journal_to_source_trace.sql)

These links expose source coverage, not accepted ARU statements.

## Inventory, assets, and operations

The auditable ARU perimeter includes waybills, freight movements, custody status, route/customer economics, rolling-stock and terminal assets represented in the shared platform, depreciation, employees and payroll, vendors and procurement, debt, and intercompany movements. Exact route map, interchanges, terminal list, locomotive/car counts, ownership, condition, and maintenance history remain open.

## Database and exports

Target standalone package:

```text
releases/<version>/american-resource-utility/
├── manifest.json
├── american-resource-utility.sqlite
├── csv/
├── financials/
├── inventory/
├── controls/
└── SHA256SUMS.txt
```

The database must be constructed from an explicit ARU table/column allowlist and entity/segment/run/scenario scope. It must retain reconciliation keys but exclude unrelated units. It may not be a raw backup of the enterprise source.

## Audit controls and unresolved facts

Required controls: canon trace; logo/collateral provenance; chart scope; entity/segment/run/scenario filtering; source-to-journal lineage; unit trial balance; intercompany matching; consolidation reconciliation; asset/inventory rollforwards; generated-artifact safety; manifest and checksums.

Open items:

- Exact legal entity and acquisition structure
- Route map, interchange relationships, terminal list, and asset counts
- Named management and detailed workforce
- Standalone accepted ARU financial statements and inventory register
- Unit-specific letterhead and materialized ARU release package

## Download map

- [Brand system](../../assets/brand/README.md)
- [ARU/BS&T organization](../organization/ARU_BST_ORGANIZATION.md)
- [Finance/data register](../data/FINANCE_RELEASE_CANDIDATE.md)
- [Independent unit package standard](../audit/UNIT_PACKAGE_STANDARD.md)
- [Business-line audit matrix](../audit/BUSINESS_LINE_AUDIT_MATRIX.md)
- [Machine-readable unit registry](registry.json)
