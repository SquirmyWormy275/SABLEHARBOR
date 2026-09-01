<p align="center">
  <img src="assets/brand/logos/sable-harbor__primary-horizontal.svg" alt="Sable Harbor" width="820" />
</p>

# SABLE HARBOR

Sable Harbor is the canonical synthetic enterprise and reusable industrial business-world sandbox for mining, natural resources, logistics, enterprise software, research, analytics, assurance, finance, governance, security, incident response, and professional training.

This repository now supports two linked views:

1. **Company view** — corporate history, governing principles, enterprise organization, shared identity and collateral, consolidated data architecture, and repository controls.
2. **Business-line view** — a standardized dossier for each current line, operating component, historical identity, and separate case universe.

The dossier layer indexes authoritative source material. It does not duplicate canon or promote model, scenario, branch-only, or synthetic records into accepted corporate fact.

## Evidence-state dashboard — September 1, 2026

| Layer | State | Entry point |
|---|---|---|
| Corporate lore v0.2 | **ACCEPTED ON `main`** | [Canon](docs/canon/) |
| Production logo system v0.1.0 | **ACCEPTED ON `main`** | [Logos](assets/brand/logos/) |
| Organization charts and briefing | **ACCEPTED ON `main`** | [Organization](docs/organization/README.md) |
| Enterprise portal and unit dossiers | **REVIEW CANDIDATE** | [Company](docs/company/README.md) · [Business lines](docs/business-lines/README.md) |
| Brand standards and corporate collateral v0.2 | **REVIEW CANDIDATE** | [Brand system](assets/brand/README.md) |
| Financial/data platform v0.1 | **RELEASE CANDIDATE — PR #9; NOT ACCEPTED** | [Finance register](docs/data/FINANCE_RELEASE_CANDIDATE.md) |
| GitHub wiki | **SOURCE READY; REPOSITORY WIKI DISABLED AT AUDIT** | [Wiki source](docs/wiki/) |

Audit pins: accepted baseline `c111ec6f4900edea656a52a391c71c600b880be1`; finance candidate `1f294440a11e724e5f1bdcd3a7f59f7342169bfe`.

## Start here

| Need | Entry point |
|---|---|
| Understand Sable Harbor overall | [Company dossier](docs/company/README.md) |
| Browse by business line or component | [Business-line directory](docs/business-lines/README.md) |
| Inspect organization and authority | [Organization suite](docs/organization/README.md) |
| Download logos, letterhead, memo, report, and presentation templates | [Brand and collateral](assets/brand/README.md) |
| Inspect databases, financials, inventory scope, and releases | [Data and finance](docs/data/README.md) |
| Review controlling lore and decisions | [Corporate canon](docs/canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md) |
| Review repository findings and cleanup work | [Repository audit](docs/audit/README.md) |
| Review publication-ready wiki source | [Wiki mirror](docs/wiki/Home.md) |

## Enterprise organization

[![Sable Harbor enterprise organization](docs/organization/assets/enterprise-organization-2026.svg)](docs/organization/README.md)

The chart is a canon-derived functional map, not a fabricated legal-entity or HR reporting tree. Exact entities, titles, reporting lines, headcount, and unit P&Ls remain open or scenario-controlled unless explicitly locked.

## Current business lines

| Mark | Business line | Role |
|---|---|---|
| <img src="assets/brand/logos/foundry-field__mark.svg" width="46" alt="Foundry Field" /> | [Foundry Field](docs/business-lines/FOUNDRY_FIELD.md) | Core operating/product application layer |
| <img src="assets/brand/logos/willow__mark.svg" width="46" alt="Willow" /> | [Willow](docs/business-lines/WILLOW.md) | Research and experimental line |
| <img src="assets/brand/logos/atlas-meridian__mark.svg" width="46" alt="Atlas Meridian" /> | [Atlas Meridian](docs/business-lines/ATLAS_MERIDIAN.md) | Investigation and controlled-commercialization line |
| <img src="assets/brand/logos/pale-sun__mark.svg" width="46" alt="Pale Sun" /> | [Pale Sun](docs/business-lines/PALE_SUN.md) | Operating-control line around Red Wash |
| <img src="assets/brand/logos/project-cradle__mark.svg" width="46" alt="Project Cradle" /> | [Project Cradle](docs/business-lines/PROJECT_CRADLE.md) | Recovery and host-safe participation line |
| <img src="assets/brand/logos/american-resource-utility__mark.svg" width="46" alt="American Resource Utility" /> | [American Resource Utility](docs/business-lines/AMERICAN_RESOURCE_UTILITY.md) | Acquired regional resource-logistics operator |
| <img src="assets/brand/logos/advisory__mark.svg" width="46" alt="Advisory" /> | [Advisory](docs/business-lines/ADVISORY.md) | Emerging method-transfer line |

## Components, historical identities, and separate case material

| Mark | Identity | Classification |
|---|---|---|
| <img src="assets/brand/logos/foundry__mark.svg" width="38" alt="Foundry" /> | [Foundry](docs/business-lines/FOUNDRY.md) | Product substrate underlying Foundry Field |
| <img src="assets/brand/logos/red-wash-mine__mark.svg" width="38" alt="Red Wash Mine" /> | [Red Wash Mine](docs/business-lines/RED_WASH_MINE.md) | Operating asset under Pale Sun |
| <img src="assets/brand/logos/blood-sweat-and-tears-railway__mark.svg" width="38" alt="Blood, Sweat & Tears Railway" /> | [Blood, Sweat & Tears Railway](docs/business-lines/BLOOD_SWEAT_AND_TEARS_RAILWAY.md) | Railway component within ARU |
| <img src="assets/brand/logos/emberline__mark.svg" width="38" alt="Emberline" /> | [Emberline](docs/business-lines/EMBERLINE.md) | Historical coal-focused line, active through 2025 |
| <img src="assets/brand/logos/evalon__mark.svg" width="38" alt="Evalon" /> | [Evalon](docs/business-lines/EVALON.md) | Historical advanced-engineering outpost rechartered as Willow |
| — | [Blackridge](docs/business-lines/BLACKRIDGE.md) | Separate executable case universe; not a Sable Harbor unit |

## Unit audit model

Every dossier contains the same sections: status and scope; canon/history; identity and collateral; organization and authority; financials and accounting; inventory/assets/operations; database and exports; controls; unresolved facts; and download map. A machine-readable [unit registry](docs/business-lines/registry.json) keeps those mappings synchronized.

A dossier may say **NOT MATERIALIZED**. That is deliberate. No standalone ARU database, ARU inventory register, ARU financial workbook, or unit-specific letterhead is treated as available until it is scoped, generated, reconciled, validated, directly inspected, registered, and checksummed.

## Repository map

```text
SABLEHARBOR/
├── README.md
├── assets/brand/                  # logos, standards, collateral, packages
├── docs/
│   ├── company/                   # enterprise dossier and manifest
│   ├── business-lines/            # one auditable dossier per unit/component
│   ├── canon/                     # controlling lore and decisions
│   ├── organization/              # charts, authority maps, briefing
│   ├── data/                      # finance/data acceptance and release map
│   ├── audit/                     # findings, registers, matrices, backlog
│   ├── governance/                # evidence and information architecture
│   ├── legal/                     # preliminary name/mark screen
│   └── wiki/                      # controlled publication source
├── scripts/                       # validators/build support
└── tools/                         # deterministic builders
```

## Canon, privacy, and public-repository boundary

The repository is intentionally public, but visibility grants no license. Open legal entities, transaction terms, reserves, routes, physical assets, headcount, reporting lines, and quantitative values remain open or scenario-controlled unless canon explicitly locks them. NAILEX remains separate and consumes only deliberate, versioned exports.

## License

**All rights reserved.** See [LICENSE.md](LICENSE.md).
