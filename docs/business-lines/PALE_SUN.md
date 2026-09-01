# Pale Sun

<p align="center">
  <img src="../../assets/brand/logos/pale-sun__primary-horizontal.svg" alt="Pale Sun logo" width="760" />
</p>

> **Dossier status: release-candidate index.** Canon, identity, organization, database, finance, and operational references are gathered here. A standalone unit database, inventory package, unit-only workbook, and checksummed audit bundle are **not yet implemented**.

[Company](../company/README.md) · [Business lines](README.md) · [Organization](../organization/PALE_SUN_RED_WASH_ORGANIZATION.md) · [Wiki source](../wiki/Pale%20Sun.md) · [Repository audit](../audit/REPOSITORY_AUDIT_2026-09-01.md)

## Unit control record

| Field | Current record |
|---|---|
| Classification | Current business line |
| Parent | Sable Harbor |
| Operating role | Current operating business line responsible for Red Wash and the uranium operating thesis. |
| Canon boundary | LOCKED identity, Red Wash relationship, and operating-control thesis; reserves, production plan, legal chain, exact estate, workforce, economics, and technical assumptions remain OPEN or scenario-controlled. |
| Entity filter | `RWH` |
| Segment filter | `PALE_SUN` |
| Site filter | `RED_WASH` |
| Standalone export | **NOT IMPLEMENTED** — current database and workbooks are enterprise-wide |
| Dossier date | September 1, 2026 |

## Purpose and controlling sources

Pale Sun owns the operating thesis around Red Wash: the value proposition depends on operating control, disciplined boundaries, and the consequences of physical production rather than a purely analytical claim.

- [SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md](../canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md)
- [PALE_SUN_AND_RED_WASH.md](../organization/PALE_SUN_AND_RED_WASH.md)

This page is a navigation and audit-control layer. It does not create legal entities, titles, locations, asset counts, economics, or other facts left OPEN by canon.

## Identity and letterhead

| Asset | Files |
|---|---|
| Primary logo | [SVG](../../assets/brand/logos/pale-sun__primary-horizontal.svg) · [PNG](../../assets/brand/logos/pale-sun__primary-horizontal.png) |
| Stacked logo | [SVG](../../assets/brand/logos/pale-sun__stacked.svg) · [PNG](../../assets/brand/logos/pale-sun__stacked.png) |
| Compact mark | [SVG](../../assets/brand/logos/pale-sun__mark.svg) · [PNG](../../assets/brand/logos/pale-sun__mark.png) |
| Reverse logo | [SVG](../../assets/brand/logos/pale-sun__reverse-horizontal.svg) · [PNG](../../assets/brand/logos/pale-sun__reverse-horizontal.png) |
| One-color logo | [SVG](../../assets/brand/logos/pale-sun__one-color-horizontal.svg) · [PNG](../../assets/brand/logos/pale-sun__one-color-horizontal.png) |
| Unit letterhead | [US Letter SVG](../../assets/brand/collateral/letterhead/business-lines/pale-sun-letterhead-us-letter.svg) |
| Standards | [Brand standards](../../assets/brand/BRAND_STANDARDS.md) · [Font provenance](../../assets/brand/FONT_PROVENANCE.md) |

The letterhead is a linked-logo working template with placeholders; editable DOCX/PDF variants remain future generated artifacts.

## Current organization and authority

[![Pale Sun organization chart](../organization/assets/pale-sun-red-wash-organization-2026.svg)](../organization/PALE_SUN_RED_WASH_ORGANIZATION.md)

The chart is canon-derived and intentionally preserves OPEN leadership, legal, workforce, footprint, and reporting details. It is not represented as a complete HR reporting tree.

## Operations, assets, and inventory

**Modeled operating population:** Mine and mill production, ore/feed, grade, recovery, concentrate, inventory lots, shipments, realized pricing, costs, fixed assets, debt, and ARO records.

**Inventory position:** Physical inventory is represented through inventory lots, production batches, production records, and uranium shipments. Reserve and technical-report conclusions are not established by these synthetic model records.

| Audit area | Present coverage |
|---|---|
| Workforce | Shared `worker`/payroll records or unit-domain labor records; synthetic/model population, not locked HR canon |
| Assets | Shared `site` and `fixed_asset` records plus unit-domain records; detailed register remains partial |
| Inventory/WIP | Unit-domain records listed below; not yet a complete unit inventory subsystem |
| Source-to-ledger trace | Journal `source_type`/`source_id` and named trace queries |
| Unit-only package | **Absent** |

## Database and finance map

A valid unit audit must filter by the entity, segment, and site keys above **and** by an explicit generation run, scenario, and fact state once those isolation controls are completed. Shared tables must never be treated as unit-exclusive merely because they are linked from this page.

**Relevant tables:** `site`, `worker`, `fixed_asset`, `inventory_lot`, `production_record`, `environmental_obligation`, `mine_production_batch`, `uranium_shipment`, `purchase_order`, `goods_receipt`, `vendor_bill`, `vendor_payment`, `depreciation_record`, `debt_facility`, `debt_draw`, `interest_accrual`, `journal_entry`, `journal_line`, `scenario_value`

### Named analytical queries

- [`red_wash_unit_cost_bridge`](../../db/sql/red_wash_unit_cost_bridge.sql)
- [`mine_inventory_shipment_reconciliation`](../../db/sql/mine_inventory_shipment_reconciliation.sql)
- [`fixed_asset_rollforward`](../../db/sql/fixed_asset_rollforward.sql)
- [`vendor_spend_concentration`](../../db/sql/vendor_spend_concentration.sql)
- [`debt_covenant_calculation`](../../db/sql/debt_covenant_calculation.sql)
- [`entity_trial_balance`](../../db/sql/entity_trial_balance.sql)
- [`journal_to_source_trace`](../../db/sql/journal_to_source_trace.sql)
- [`intercompany_mismatch_elimination`](../../db/sql/intercompany_mismatch_elimination.sql)

### Workbook surfaces

- `SABLE_HARBOR_INDUSTRIAL_OPERATIONS_v0.1.xlsx` — `Red Wash Assumptions`, `Red Wash Operating Schedule`, `Red Wash Production Inv`, `Red Wash Revenue`, `Red Wash Operating Cost`, `Red Wash Capex and ARO`, `Red Wash DCF-NAV`, `Red Wash Sensitivities`, `Industrial Intercompany`, `Checks`
- `SABLE_HARBOR_GL_CLOSE_AND_SUBLEDGERS_v0.1.xlsx` — `Fixed Assets`, `Inventory Rollforward`, `Debt Schedule`, `Intercompany Matches`, `Checks`
- `SABLE_HARBOR_CAPITAL_MA_AND_VALUATION_v0.1.xlsx` — `Red Wash Acquisition`, `Purchase Price Allocation`, `Red Wash Mine NAV`, `Sensitivities`, `Checks`

Workbook definitions are in [`src/sable_harbor/workbooks/suite.py`](../../src/sable_harbor/workbooks/suite.py). Generated `.xlsx` files are ignored source outputs and are not durable downloads until CI publishes validated artifacts.

### Reproduce the enterprise model

```bash
uv sync --all-extras
SHFIN_DATABASE_URL=sqlite:///var/release.db uv run alembic upgrade head
SHFIN_DATABASE_URL=sqlite:///var/release.db uv run shfin generate \
  --profile full_history --scenario base --seed 20260831
SHFIN_DATABASE_URL=sqlite:///var/release.db uv run shfin validate
SHFIN_DATABASE_URL=sqlite:///var/release.db uv run shfin workbooks
```

After generation, apply the documented unit filters. Do not label the unfiltered enterprise database as a unit database.

## Standalone-audit acceptance boundary

Before this unit can be called independently auditable, it needs a filtered SQLite/PostgreSQL extract, CSV exports, unit financial statements, inventory/asset register, source-to-ledger reconciliation, intercompany bridge, manifest, checksums, validation report, and CI artifact. See [Unit export specification](../audit/UNIT_EXPORT_SPECIFICATION.md).

Remaining legal, leadership, route/site, asset, workforce, technical, or economic facts stay OPEN or scenario-controlled until deliberately approved.
