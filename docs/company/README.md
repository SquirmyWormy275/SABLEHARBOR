# Sable Harbor — enterprise dossier

<p align="center">
  <img src="../../assets/brand/logos/sable-harbor__primary-horizontal.svg" alt="Sable Harbor logo" width="820" />
</p>

> **Repository control status, September 1, 2026:** corporate lore v0.2, the production logo system, and the organization-chart/briefing package are on `main`. The enterprise finance/data platform is a release candidate in PR #9. Business-line dossiers and recovered collateral are on the stacked integration branch and must not be read as canonizing OPEN facts.

## Enterprise view

Sable Harbor is a synthetic enterprise and reusable business-world sandbox spanning enterprise software, research, mining, recovery, logistics, advisory, finance, governance, security, incident response, and professional training. Business activity produces records and consequences; downstream systems consume explicit, versioned exports rather than hidden dependencies.

- [Corporate lore canon](../canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md)
- [Decision register](../canon/DECISION_REGISTER.md)
- [Enterprise organization](../organization/README.md)
- [Organization briefing](../organization/briefing/README.md)
- [Brand system](../../assets/brand/README.md)
- [Corporate collateral](../../assets/brand/collateral/README.md)
- [Finance/data platform](../finance/README.md)
- [Repository audit](../audit/REPOSITORY_AUDIT_2026-09-01.md)

[![Sable Harbor enterprise organization](../organization/assets/enterprise-organization-2026.svg)](../organization/README.md)

## Business-line map

| Mark | Unit | Operating role | Working accounting scope |
|---|---|---|---|
| [<img src="../../assets/brand/logos/foundry-field__mark.svg" width="52" alt="Foundry Field mark" />](../business-lines/FOUNDRY_FIELD.md) | [Foundry Field](../business-lines/FOUNDRY_FIELD.md) | Current core business line and principal operating/economic interface. | SHI |
| [<img src="../../assets/brand/logos/willow__mark.svg" width="52" alt="Willow mark" />](../business-lines/WILLOW.md) | [Willow](../business-lines/WILLOW.md) | Current core business line for bounded experiments and consequential unknowns. | SHI |
| [<img src="../../assets/brand/logos/atlas-meridian__mark.svg" width="52" alt="Atlas Meridian mark" />](../business-lines/ATLAS_MERIDIAN.md) | [Atlas Meridian](../business-lines/ATLAS_MERIDIAN.md) | Current core business line for investigation across represented evidence. | SHI |
| [<img src="../../assets/brand/logos/pale-sun__mark.svg" width="52" alt="Pale Sun mark" />](../business-lines/PALE_SUN.md) | [Pale Sun](../business-lines/PALE_SUN.md) | Current operating business line responsible for Red Wash and the uranium operating thesis. | RWH |
| [<img src="../../assets/brand/logos/project-cradle__mark.svg" width="52" alt="Project Cradle mark" />](../business-lines/PROJECT_CRADLE.md) | [Project Cradle](../business-lines/PROJECT_CRADLE.md) | Current core business line for host-safe recovery and participation economics. | SHI |
| [<img src="../../assets/brand/logos/american-resource-utility__mark.svg" width="52" alt="American Resource Utility mark" />](../business-lines/AMERICAN_RESOURCE_UTILITY.md) | [American Resource Utility](../business-lines/AMERICAN_RESOURCE_UTILITY.md) | Current distinct operating company and core resource-logistics line; BS&T is an operating component. | ARU |
| [<img src="../../assets/brand/logos/advisory__mark.svg" width="52" alt="Advisory mark" />](../business-lines/ADVISORY.md) | [Advisory](../business-lines/ADVISORY.md) | Emerging current business line for method transfer where the client should own the system. | SHI |

## Enterprise data control plane

| Layer | Controlling location | Current status |
|---|---|---|
| Canon and decisions | `docs/canon/` | Accepted on `main`; OPEN facts remain OPEN |
| Organization and authority | `docs/organization/` | Accepted canon-derived maps; not complete HR/legal trees |
| Logos and corporate collateral | `assets/brand/` | Logos accepted; recovered collateral is production-oriented candidate material |
| Unit dossiers | `docs/business-lines/` | Release-candidate indexes over shared sources |
| Unit registry | `config/enterprise/business_units.json` | Machine-readable navigation and filter map |
| Database schema and SQL | `db/`, `src/sable_harbor/` | Finance PR #9 release candidate |
| Assumptions and scenarios | `config/finance/` | Model-proposed/scenario-controlled |
| Generated workbooks/releases | ignored output directories and future CI artifacts | Not durable source files; unit packages absent |
| Wiki source | `docs/wiki/` | Versioned source exists; GitHub Wiki is disabled |

## Enterprise audit boundary

The repository can currently prove where the canon, identity assets, organization maps, code, schema, assumptions, tests, queries, and planned workbook surfaces live. It cannot yet prove independent unit auditability because generated records lack completed run/scenario isolation, unit-specific release bundles are absent, and workbook/public-release acceptance gaps remain open.

No business-line page should be interpreted as an audited financial statement, reserve report, legal entity schedule, asset register, HR roster, or operating-safety system.
