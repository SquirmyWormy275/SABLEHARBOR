# Business-line control index

<p align="center">
  <img src="../../assets/brand/logos/sable-harbor__primary-horizontal.svg" alt="Sable Harbor" width="800" />
</p>

This directory is the controlled navigation layer for Sable Harbor's current business lines. Shared source files remain in normalized locations—canon under `docs/canon`, organization under `docs/organization`, identity under `assets/brand`, and data/finance under `db`, `src`, `config`, and generated release outputs. Dossiers index those sources rather than duplicating them.

## Current business lines

| Mark | Business line | Role | Working accounting scope | Auditability |
|---|---|---|---|---|
| [<img src="../../assets/brand/logos/foundry-field__mark.svg" width="58" alt="Foundry Field mark" />](FOUNDRY_FIELD.md) | [Foundry Field](FOUNDRY_FIELD.md) | Current core business line and principal operating/economic interface. | `SHI` | RC index; standalone export absent |
| [<img src="../../assets/brand/logos/willow__mark.svg" width="58" alt="Willow mark" />](WILLOW.md) | [Willow](WILLOW.md) | Current core business line for bounded experiments and consequential unknowns. | `SHI` | RC index; standalone export absent |
| [<img src="../../assets/brand/logos/atlas-meridian__mark.svg" width="58" alt="Atlas Meridian mark" />](ATLAS_MERIDIAN.md) | [Atlas Meridian](ATLAS_MERIDIAN.md) | Current core business line for investigation across represented evidence. | `SHI` | RC index; standalone export absent |
| [<img src="../../assets/brand/logos/pale-sun__mark.svg" width="58" alt="Pale Sun mark" />](PALE_SUN.md) | [Pale Sun](PALE_SUN.md) | Current operating business line responsible for Red Wash and the uranium operating thesis. | `RWH` | RC index; standalone export absent |
| [<img src="../../assets/brand/logos/project-cradle__mark.svg" width="58" alt="Project Cradle mark" />](PROJECT_CRADLE.md) | [Project Cradle](PROJECT_CRADLE.md) | Current core business line for host-safe recovery and participation economics. | `SHI` | RC index; standalone export absent |
| [<img src="../../assets/brand/logos/american-resource-utility__mark.svg" width="58" alt="American Resource Utility mark" />](AMERICAN_RESOURCE_UTILITY.md) | [American Resource Utility](AMERICAN_RESOURCE_UTILITY.md) | Current distinct operating company and core resource-logistics line; BS&T is an operating component. | `ARU` | RC index; standalone export absent |
| [<img src="../../assets/brand/logos/advisory__mark.svg" width="58" alt="Advisory mark" />](ADVISORY.md) | [Advisory](ADVISORY.md) | Emerging current business line for method transfer where the client should own the system. | `SHI` | RC index; standalone export absent |

## Coverage states

- **CANONICAL:** controlling lore or governance is accepted.
- **PRODUCTION ASSET:** an accepted logo or publication artifact exists.
- **RELEASE CANDIDATE:** implementation exists on the active finance/integration branches but is not accepted for production use.
- **PARTIAL:** some records exist, but the complete unit subsystem or register does not.
- **NOT IMPLEMENTED:** the requested unit artifact is absent; a link or planned filename is not evidence that it exists.

## Supplemental and historical identities

- [Foundry](FOUNDRY.md) — shared product substrate, distinct from Foundry Field.
- [Red Wash Mine](RED_WASH_MINE.md) — operating asset under Pale Sun.
- [Blood, Sweat & Tears Railway](BLOOD_SWEAT_AND_TEARS_RAILWAY.md) — ARU railway component.
- [Emberline](EMBERLINE.md) — historical line absorbed into enduring work.
- [Evalon](EVALON.md) — historical outpost rechartered as Willow.
- [Red Wash / Pale Sun endorsed lockup](RED_WASH_PALE_SUN.md).

## Independent-audit standard

A dossier becomes independently auditable only when its generated package identifies the source commit, canon commit, generation run, scenario, seed, period coverage, fact states, entity/segment/site filters, included tables and columns, row counts, financial and operational reconciliations, validation results, and checksums. The current finance platform does not yet emit those seven standalone packages.

- [Company dossier](../company/README.md)
- [Unit export specification](../audit/UNIT_EXPORT_SPECIFICATION.md)
- [Repository audit](../audit/REPOSITORY_AUDIT_2026-09-01.md)
- [Machine-readable unit registry](../../config/enterprise/business_units.json)
