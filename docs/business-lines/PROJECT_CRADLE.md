# Project Cradle

<p align="center">
  <img src="../../assets/brand/logos/project-cradle__primary-horizontal.svg" alt="Project Cradle logo" width="760" />
</p>

> **Dossier status: generated release candidate.** The finance branch generates scoped SQLite, financial, source-event, workbook, control, manifest, and checksum evidence for this unit.

[Company](../company/README.md) · [Business lines](README.md) · [Organization](../organization/PROJECT_CRADLE_ORGANIZATION.md) · [Wiki source](../wiki/Project%20Cradle.md) · [Repository audit](../audit/REPOSITORY_AUDIT_2026-09-01.md)

## Unit control record

| Field | Current record |
|---|---|
| Classification | Current business line |
| Parent | Sable Harbor |
| Operating role | Current core business line for host-safe recovery and participation economics. |
| Canon boundary | LOCKED identity, host-safe boundary, and recovery role; commercial structures, project pipeline, leadership, ownership, and economics remain OPEN or scenario-controlled. |
| Entity filter | `SHI` |
| Segment filter | `CRADLE` |
| Site filter | `SAC` |
| Standalone export | **RELEASE CANDIDATE GENERATED** — `shfin package-business-units`; publication remains acceptance-gated |
| Dossier date | September 1, 2026 |

## Purpose and controlling sources

Project Cradle recovers value from material streams the host system already creates. Its core audit boundary is host-safe participation: the model must distinguish host assets, recovered value, Sable Harbor economics, and the host’s contractual share.

- [SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md](../canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md)
- [PROJECT_CRADLE.md](../organization/PROJECT_CRADLE.md)

This page is a navigation and audit-control layer. It does not create legal entities, titles, locations, asset counts, economics, or other facts left OPEN by canon.

## Identity and letterhead

| Asset | Files |
|---|---|
| Primary logo | [SVG](../../assets/brand/logos/project-cradle__primary-horizontal.svg) · [PNG](../../assets/brand/logos/project-cradle__primary-horizontal.png) |
| Stacked logo | [SVG](../../assets/brand/logos/project-cradle__stacked.svg) · [PNG](../../assets/brand/logos/project-cradle__stacked.png) |
| Compact mark | [SVG](../../assets/brand/logos/project-cradle__mark.svg) · [PNG](../../assets/brand/logos/project-cradle__mark.png) |
| Reverse logo | [SVG](../../assets/brand/logos/project-cradle__reverse-horizontal.svg) · [PNG](../../assets/brand/logos/project-cradle__reverse-horizontal.png) |
| One-color logo | [SVG](../../assets/brand/logos/project-cradle__one-color-horizontal.svg) · [PNG](../../assets/brand/logos/project-cradle__one-color-horizontal.png) |
| Unit letterhead | [US Letter SVG](../../assets/brand/collateral/letterhead/business-lines/project-cradle-letterhead-us-letter.svg) |
| Standards | [Brand standards](../../assets/brand/BRAND_STANDARDS.md) · [Font provenance](../../assets/brand/FONT_PROVENANCE.md) |

The letterhead is a linked-logo working template with placeholders; editable DOCX/PDF variants remain future generated artifacts.

## Current organization and authority

[![Project Cradle organization chart](../organization/assets/project-cradle-organization-2026.svg)](../organization/PROJECT_CRADLE_ORGANIZATION.md)

The chart is canon-derived and intentionally preserves OPEN leadership, legal, workforce, footprint, and reporting details. It is not represented as a complete HR reporting tree.

## Operations, assets, and inventory

**Modeled operating population:** Recovery runs, host operator, host-asset ownership flag, feed, grade, recovery, recovered units, operating cost, gross sale, host share, and journal lineage.

**Inventory position:** Recovered units and host participation are modeled per run. Host assets must not be silently reclassified as Sable Harbor assets.

| Audit area | Present coverage |
|---|---|
| Workforce | Shared `worker`/payroll records or unit-domain labor records; synthetic/model population, not locked HR canon |
| Assets | Shared `site` and `fixed_asset` records plus unit-domain records; detailed register remains partial |
| Inventory/WIP | Unit-domain records listed below; not yet a complete unit inventory subsystem |
| Source-to-ledger trace | Journal `source_type`/`source_id` and named trace queries |
| Unit-only package | **Absent** |

## Database and finance map

A valid unit audit must filter by the entity, segment, and site keys above **and** by an explicit generation run, scenario, and fact state once those isolation controls are completed. Shared tables must never be treated as unit-exclusive merely because they are linked from this page.

**Relevant tables:** `recovery_run`, `customer`, `customer_contract`, `invoice`, `cash_receipt`, `worker`, `fixed_asset`, `purchase_order`, `vendor_bill`, `journal_entry`, `journal_line`, `scenario_value`

### Named analytical queries

- [`cradle_project_economics`](../../db/sql/cradle_project_economics.sql)
- [`customer_profitability`](../../db/sql/customer_profitability.sql)
- [`vendor_spend_concentration`](../../db/sql/vendor_spend_concentration.sql)
- [`fixed_asset_rollforward`](../../db/sql/fixed_asset_rollforward.sql)
- [`entity_trial_balance`](../../db/sql/entity_trial_balance.sql)
- [`journal_to_source_trace`](../../db/sql/journal_to_source_trace.sql)

### Workbook surfaces

- `SABLE_HARBOR_INDUSTRIAL_OPERATIONS_v0.1.xlsx` — `Cradle Assumptions`, `Cradle Pilot Build`, `Cradle Contract Structures`, `Cradle Project DCF`, `Industrial Intercompany`, `Checks`
- `SABLE_HARBOR_CAPITAL_MA_AND_VALUATION_v0.1.xlsx` — `Cradle Project Option Value`, `Sensitivities`, `Checks`

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
