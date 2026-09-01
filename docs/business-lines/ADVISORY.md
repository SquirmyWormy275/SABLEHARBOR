# Advisory

<p align="center">
  <img src="../../assets/brand/logos/advisory__primary-horizontal.svg" alt="Advisory logo" width="760" />
</p>

> **Dossier status: release-candidate index.** Canon, identity, organization, database, finance, and operational references are gathered here. A standalone unit database, inventory package, unit-only workbook, and checksummed audit bundle are **not yet implemented**.

[Company](../company/README.md) · [Business lines](README.md) · [Organization](../organization/ARU_BST_AND_ADVISORY.md) · [Wiki source](../wiki/Advisory.md) · [Repository audit](../audit/REPOSITORY_AUDIT_2026-09-01.md)

## Unit control record

| Field | Current record |
|---|---|
| Classification | Current business line |
| Parent | Sable Harbor |
| Operating role | Emerging current business line for method transfer where the client should own the system. |
| Canon boundary | LOCKED emerging role and method-transfer boundary; name treatment, scale, leadership, customers, legal structure, and economics remain OPEN or scenario-controlled. |
| Entity filter | `SHI` |
| Segment filter | `ADVISORY` |
| Site filter | `SAC` |
| Standalone export | **NOT IMPLEMENTED** — current database and workbooks are enterprise-wide |
| Dossier date | September 1, 2026 |

## Purpose and controlling sources

Advisory transfers the Sable Harbor method where the client can and should own the resulting system. The boundary is deliberate: Advisory supports transfer and adoption without converting the client’s operating authority into Sable Harbor’s authority.

- [SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md](../canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md)
- [ARU_BST_AND_ADVISORY.md](../organization/ARU_BST_AND_ADVISORY.md)

This page is a navigation and audit-control layer. It does not create legal entities, titles, locations, asset counts, economics, or other facts left OPEN by canon.

## Identity and letterhead

| Asset | Files |
|---|---|
| Primary logo | [SVG](../../assets/brand/logos/advisory__primary-horizontal.svg) · [PNG](../../assets/brand/logos/advisory__primary-horizontal.png) |
| Stacked logo | [SVG](../../assets/brand/logos/advisory__stacked.svg) · [PNG](../../assets/brand/logos/advisory__stacked.png) |
| Compact mark | [SVG](../../assets/brand/logos/advisory__mark.svg) · [PNG](../../assets/brand/logos/advisory__mark.png) |
| Reverse logo | [SVG](../../assets/brand/logos/advisory__reverse-horizontal.svg) · [PNG](../../assets/brand/logos/advisory__reverse-horizontal.png) |
| One-color logo | [SVG](../../assets/brand/logos/advisory__one-color-horizontal.svg) · [PNG](../../assets/brand/logos/advisory__one-color-horizontal.png) |
| Unit letterhead | [US Letter SVG](../../assets/brand/collateral/letterhead/business-lines/advisory-letterhead-us-letter.svg) |
| Standards | [Brand standards](../../assets/brand/BRAND_STANDARDS.md) · [Font provenance](../../assets/brand/FONT_PROVENANCE.md) |

The letterhead is a linked-logo working template with placeholders; editable DOCX/PDF variants remain future generated artifacts.

## Current organization and authority

[![Advisory organization chart](../organization/briefing/images/08_advisory_organization.png)](../organization/ARU_BST_AND_ADVISORY.md)

The chart is canon-derived and intentionally preserves OPEN leadership, legal, workforce, footprint, and reporting details. It is not represented as a complete HR reporting tree.

## Operations, assets, and inventory

**Modeled operating population:** Client contracts, engagements, tasks, approved time, project cost, billing, revenue, collections, utilization, and margin.

**Inventory position:** Advisory inventory is a portfolio of engagements, obligations, approved work, WIP, and receivables rather than physical stock.

| Audit area | Present coverage |
|---|---|
| Workforce | Shared `worker`/payroll records or unit-domain labor records; synthetic/model population, not locked HR canon |
| Assets | Shared `site` and `fixed_asset` records plus unit-domain records; detailed register remains partial |
| Inventory/WIP | Unit-domain records listed below; not yet a complete unit inventory subsystem |
| Source-to-ledger trace | Journal `source_type`/`source_id` and named trace queries |
| Unit-only package | **Absent** |

## Database and finance map

A valid unit audit must filter by the entity, segment, and site keys above **and** by an explicit generation run, scenario, and fact state once those isolation controls are completed. Shared tables must never be treated as unit-exclusive merely because they are linked from this page.

**Relevant tables:** `customer`, `customer_contract`, `performance_obligation`, `invoice`, `invoice_line`, `revenue_recognition`, `cash_receipt`, `engagement`, `project_task`, `time_entry`, `project_cost`, `engagement_invoice_link`, `worker`, `journal_entry`, `journal_line`, `scenario_value`

### Named analytical queries

- [`engagement_margin_wip`](../../db/sql/engagement_margin_wip.sql)
- [`customer_profitability`](../../db/sql/customer_profitability.sql)
- [`ar_ap_aging`](../../db/sql/ar_ap_aging.sql)
- [`employee_loaded_cost`](../../db/sql/employee_loaded_cost.sql)
- [`entity_trial_balance`](../../db/sql/entity_trial_balance.sql)
- [`journal_to_source_trace`](../../db/sql/journal_to_source_trace.sql)

### Workbook surfaces

- `SABLE_HARBOR_SOFTWARE_AND_SERVICES_v0.1.xlsx` — `Emerging Advisory`, `Services Utilization`, `Engagement Margin`, `Checks`
- `SABLE_HARBOR_CAPITAL_MA_AND_VALUATION_v0.1.xlsx` — `Advisory Valuation`, `Sensitivities`, `Checks`

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
