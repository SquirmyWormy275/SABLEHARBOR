<p align="center">
  <img src="assets/brand/logos/sable-harbor__primary-horizontal.svg" alt="Sable Harbor" width="860" />
</p>

# SABLE HARBOR

Sable Harbor is the canonical synthetic enterprise and reusable business-world sandbox for enterprise software, research, mining, resource recovery, logistics, advisory, finance, governance, assurance, security, incident response, and professional training.

> **Status as of September 1, 2026:** corporate lore v0.2, the production logo system, and the organization publication package are accepted on `main`. The finance/data platform in PR #9 and the company/business-line dossier layer on the stacked integration branch are release candidates, not accepted production systems.

## View the company

- [Enterprise dossier](docs/company/README.md)
- [Corporate lore and decision register](docs/canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md)
- [Enterprise organization chart](docs/organization/README.md)
- [Official organization briefing](docs/organization/briefing/README.md)
- [Brand assets and collateral](assets/brand/README.md)
- [Finance/database platform](docs/finance/README.md)
- [Repository audit](docs/audit/REPOSITORY_AUDIT_2026-09-01.md)

## Enterprise organization

This is the canon-derived August 31, 2026 **functional enterprise organization chart**. It shows company-wide authorities, operating lines, named leaders and known ownership/component relationships. Exact HR reporting lines and final legal entities remain deliberately open.

[![Sable Harbor enterprise organization chart](docs/organization/assets/enterprise-organization-2026.svg)](docs/organization/README.md)

The full package contains dedicated charts for [leadership and authority](docs/organization/2026_LEADERSHIP_AND_AUTHORITY_MAP.md), [Foundry Field](docs/organization/FOUNDRY_FIELD_ORGANIZATION.md), [Project Willow](docs/organization/WILLOW_ORGANIZATION.md), [Atlas Meridian](docs/organization/ATLAS_MERIDIAN_BRIDGE_ORGANIZATION.md), [Pale Sun and Red Wash](docs/organization/PALE_SUN_RED_WASH_ORGANIZATION.md), [Project Cradle](docs/organization/PROJECT_CRADLE_ORGANIZATION.md), [ARU and BS&T](docs/organization/ARU_BST_ORGANIZATION.md), and [the Original Eight](docs/organization/ORIGINAL_EIGHT.md).

### Official organization briefing

The briefing-grade publication package uses the approved production logo system and includes one rendered 16:9 image per chart, an editable PowerPoint deck, a PDF, a packaged ZIP, a source builder, and a validation manifest.

- [Organization briefing index](docs/organization/briefing/README.md)
- [Editable PowerPoint](docs/organization/briefing/SABLE_HARBOR_Organization_Briefing_v1.0.pptx)
- [Briefing PDF](docs/organization/briefing/SABLE_HARBOR_Organization_Briefing_v1.0.pdf)
- [Complete briefing package](docs/organization/briefing/SABLE_HARBOR_Organization_Briefing_v1.0.zip)

## Explore by business line

| Mark | Business line | Operating role | Current audit state |
|---|---|---|---|
| [<img src="assets/brand/logos/foundry-field__mark.svg" width="52" alt="Foundry Field mark" />](docs/business-lines/FOUNDRY_FIELD.md) | [Foundry Field](docs/business-lines/FOUNDRY_FIELD.md) | Current core business line and principal operating/economic interface. | RC dossier; unit bundle absent |
| [<img src="assets/brand/logos/willow__mark.svg" width="52" alt="Willow mark" />](docs/business-lines/WILLOW.md) | [Willow](docs/business-lines/WILLOW.md) | Current core business line for bounded experiments and consequential unknowns. | RC dossier; unit bundle absent |
| [<img src="assets/brand/logos/atlas-meridian__mark.svg" width="52" alt="Atlas Meridian mark" />](docs/business-lines/ATLAS_MERIDIAN.md) | [Atlas Meridian](docs/business-lines/ATLAS_MERIDIAN.md) | Current core business line for investigation across represented evidence. | RC dossier; unit bundle absent |
| [<img src="assets/brand/logos/pale-sun__mark.svg" width="52" alt="Pale Sun mark" />](docs/business-lines/PALE_SUN.md) | [Pale Sun](docs/business-lines/PALE_SUN.md) | Current operating business line responsible for Red Wash and the uranium operating thesis. | RC dossier; unit bundle absent |
| [<img src="assets/brand/logos/project-cradle__mark.svg" width="52" alt="Project Cradle mark" />](docs/business-lines/PROJECT_CRADLE.md) | [Project Cradle](docs/business-lines/PROJECT_CRADLE.md) | Current core business line for host-safe recovery and participation economics. | RC dossier; unit bundle absent |
| [<img src="assets/brand/logos/american-resource-utility__mark.svg" width="52" alt="American Resource Utility mark" />](docs/business-lines/AMERICAN_RESOURCE_UTILITY.md) | [American Resource Utility](docs/business-lines/AMERICAN_RESOURCE_UTILITY.md) | Current distinct operating company and core resource-logistics line; BS&T is an operating component. | RC dossier; unit bundle absent |
| [<img src="assets/brand/logos/advisory__mark.svg" width="52" alt="Advisory mark" />](docs/business-lines/ADVISORY.md) | [Advisory](docs/business-lines/ADVISORY.md) | Emerging current business line for method transfer where the client should own the system. | RC dossier; unit bundle absent |

Each dossier gathers the unit's logo variants, letterhead, canon sources, current organization view, entity/segment/site filters, relevant tables, named SQL queries, workbook surfaces, operational/inventory coverage, reproduction commands, and explicit gaps. Shared source assets remain normalized rather than duplicated.

## Audit coverage

| Layer | Location | Status |
|---|---|---|
| Controlling lore | `docs/canon/` | Accepted; OPEN decisions remain OPEN |
| Organization/authority | `docs/organization/` | Accepted canon-derived maps; not full HR/legal trees |
| Logos | `assets/brand/logos/` | Production assets |
| Collateral | `assets/brand/collateral/` | Production-oriented candidate templates |
| Business-line dossiers | `docs/business-lines/` | Release-candidate control indexes |
| Unit registry | `config/enterprise/business_units.json` | Machine-readable source map |
| Finance/database implementation | `src/`, `db/`, `config/finance/`, `tests/` | PR #9 release candidate; acceptance blockers remain |
| Unit databases/workbooks | `shfin package-business-units` | Seven RC generators; publication acceptance pending |
| Wiki | `docs/wiki/` | Versioned source; live GitHub Wiki disabled |

## Repository map

```text
assets/brand/          logos, standards, collateral, manifests, packages
docs/canon/            controlling lore, continuity, changelog, decisions
docs/company/          enterprise dossier
docs/business-lines/   one audit-control dossier per business line
docs/organization/     organization sources, charts, briefing publications
docs/finance/          finance/data-platform architecture and limitations
docs/audit/            repository audit, branch register, unit export contract
docs/governance/       public and repository governance
docs/wiki/             versioned source for the derivative GitHub Wiki
config/enterprise/     machine-readable business-unit registry
config/finance/        model assumptions and scenarios
db/                    migrations and named SQL queries
src/sable_harbor/      accounting and domain implementation
tests/                 unit, integration, canon, and reconciliation tests
```

## Reproduce the finance release candidate

```bash
uv sync --all-extras
SHFIN_DATABASE_URL=sqlite:///var/release.db uv run alembic upgrade head
SHFIN_DATABASE_URL=sqlite:///var/release.db uv run shfin generate \
  --profile full_history --scenario base --seed 20260831
SHFIN_DATABASE_URL=sqlite:///var/release.db uv run shfin validate
SHFIN_DATABASE_URL=sqlite:///var/release.db uv run shfin workbooks
SHFIN_DATABASE_URL=sqlite:///var/release.db uv run shfin package-business-units \
  --generation-run-id "$(SHFIN_DATABASE_URL=sqlite:///var/release.db uv run shfin run-id full_history --scenario base --seed 20260831)"
```

Generated databases, workbooks, and release bundles are ignored source outputs. They must be published as validated, checksummed CI/release artifacts rather than committed repeatedly. See the [unit export specification](docs/audit/UNIT_EXPORT_SPECIFICATION.md).

## Fact and publication boundaries

Repository material distinguishes accepted canon from provisional/open facts and model states. A logo, chart, model, workbook title, or dossier link does not independently establish a legal entity, reporting line, employee count, asset count, route, reserve, financial result, or commercial claim.

The repository is public. Hidden benchmark truth, evaluation oracles, credentials, unreleased scenario answers, proprietary NAILEX implementation, and other nonpublic material must remain outside it. NAILEX consumes deliberate, versioned exports rather than the entire repository.

## License and use

No open-source license is granted. Repository visibility does not grant permission to copy, modify, distribute, sublicense, or commercialize the contents. All rights are reserved unless a specific file states otherwise.
