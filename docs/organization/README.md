# SABLE HARBOR — ORGANIZATION CHARTS

**Version:** 0.2.0  
**Canonical date represented:** August 31, 2026  
**Status:** Canon-derived publication package

These are rendered organization charts for the repository README and public wiki. The charts preserve every locked organizational relationship currently available and display genuinely unresolved positions as OPEN rather than fabricating a polished hierarchy.

## Navigate

- [Enterprise dossier](../company/README.md)
- [Business-line control index](../business-lines/README.md)
- [Organization briefing](briefing/README.md)
- [Decision rights and operating gates](DECISION_RIGHTS_AND_OPERATING_GATES.md)
- [Legal and reporting structure status](LEGAL_AND_REPORTING_STRUCTURE_STATUS.md)
- [Chart governance](CHART_GOVERNANCE.md)
- [Machine-readable chart register](ORGANIZATION_MAP_REGISTER.json)

## Chart set

| ID | Chart | Scope | Business-line dossier |
|---|---|---|---|
| `SH-ORG-001` | [SABLE HARBOR — ENTERPRISE ORGANIZATION](2026_OPERATING_TOPOLOGY.md) | Company-wide authorities, operating lines, and known ownership/component relationships. | [Company](../company/README.md) |
| `SH-ORG-002` | [SABLE HARBOR — LEADERSHIP & AUTHORITY](2026_LEADERSHIP_AND_AUTHORITY_MAP.md) | Named leadership and domain authority; placement does not create direct-report relationships. | [Company](../company/README.md) |
| `SH-ORG-003` | [FOUNDRY / FOUNDRY FIELD — ORGANIZATION](FOUNDRY_FIELD_ORGANIZATION.md) | Product, technical authority, deployment counterweights, and application families. | [Foundry Field](../business-lines/FOUNDRY_FIELD.md) |
| `SH-ORG-004` | [PROJECT WILLOW — ORGANIZATION](WILLOW_ORGANIZATION.md) | Laboratory, institutional seam, and operating qualification gate. | [Willow](../business-lines/WILLOW.md) |
| `SH-ORG-005` | [ATLAS MERIDIAN — BRIDGE ORGANIZATION](ATLAS_MERIDIAN_BRIDGE_ORGANIZATION.md) | Cross-functional transition organization for repeatability and controlled commercialization. | [Atlas Meridian](../business-lines/ATLAS_MERIDIAN.md) |
| `SH-ORG-006` | [PALE SUN / RED WASH — ORGANIZATION](PALE_SUN_RED_WASH_ORGANIZATION.md) | Operating-business and mine-authority organization, including qualified interfaces. | [Pale Sun](../business-lines/PALE_SUN.md) |
| `SH-ORG-007` | [PROJECT CRADLE — ORGANIZATION](PROJECT_CRADLE_ORGANIZATION.md) | Founding team and the boundary among Cradle, its intervention, and the host operator. | [Project Cradle](../business-lines/PROJECT_CRADLE.md) |
| `SH-ORG-008` | [ARU / BS&T — ORGANIZATION](ARU_BST_ORGANIZATION.md) | Distinct acquired operator, known railway component, and open operating structure. | [American Resource Utility](../business-lines/AMERICAN_RESOURCE_UTILITY.md) |
| `SH-ORG-009` | [THE ORIGINAL EIGHT — FORMATION & STATUS](ORIGINAL_EIGHT.md) | Three founders plus five early employees, Blackridge continuity, and 2026 status. | [Company](../company/README.md) |

Advisory is represented in the [organization briefing](briefing/README.md) and its [business-line dossier](../business-lines/ADVISORY.md). It is not added as a tenth registered chart because the accepted v0.2 chart package contains nine controlled charts.

## Reading rule

The enterprise chart is a **functional organization chart**. It shows Sable Harbor's company-wide authorities, operating lines, known leaders, and known ownership/component relationships. It is not a conventional HR reporting tree because canon deliberately leaves exact executive titles and reporting lines open.

The unit charts go deeper wherever canon supports real team structure. They do not fill remaining gaps with plausible-sounding executives, mine departments, subsidiaries, locations, asset counts, or headcount. A chart is not an employee roster, legal-entity register, or financial consolidation schedule.

## Source and regeneration

- Controlling canon: [`SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md`](../canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md)
- Decision index: [`DECISION_REGISTER.md`](../canon/DECISION_REGISTER.md)
- Chart governance: [`CHART_GOVERNANCE.md`](CHART_GOVERNANCE.md)
- Deterministic renderer: [`scripts/build_organization_charts.py`](../../scripts/build_organization_charts.py)
- Validator: [`scripts/validate_organization_maps.py`](../../scripts/validate_organization_maps.py)
