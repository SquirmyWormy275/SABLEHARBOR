# Sable Harbor organization charts

**39 chart families · 56 pages · Revision 1.0.0 · September 9, 2026**

[![Business lines](assets/current/business-lines.png)](charts/business-lines.md)

[Complete chart book](assets/current/Sable-Harbor-Organization-Charts.pdf) · [All displayed wording](DISPLAY_INVENTORY.md) · [Unresolved and excluded records](UNRESOLVED_AND_EXCLUDED.md)

Business and asset cards show name, location and actual work. People cards show name, title and joining year. Missing facts remain explicitly unrecorded. Board appointment years are identified separately from employment years.

## Chart index

| Chart | Type |
| --- | --- |
| [Business lines](charts/business-lines.md) | entity |
| [Industrial ownership](charts/industrial-ownership.md) | entity |
| [Board and Chief Executive](charts/people-board.md) | people |
| [Sable Harbor Advisory](charts/advisory.md) | entity |
| [ARU operating facilities](charts/aru-facilities.md) | entity |
| [ARU businesses and services](charts/aru-services.md) | entity |
| [Atlas Meridian](charts/atlas-meridian.md) | entity |
| [BS&T railway and facilities](charts/bst-network.md) | entity |
| [Alexandria systems and publications](charts/corporate-alexandria.md) | entity |
| [Board committees](charts/corporate-board-committees.md) | entity |
| [Contact collection disciplines](charts/corporate-contact-disciplines.md) | entity |
| [J2 Education programs](charts/corporate-education-programs.md) | entity |
| [Enterprise support services](charts/corporate-enterprise-support.md) | entity |
| [Corporate headquarters](charts/corporate-headquarters.md) | entity |
| [J2 organization](charts/corporate-j2.md) | entity |
| [Pinakes portals](charts/corporate-pinakes-portals.md) | entity |
| [Enterprise technology capabilities](charts/corporate-technology-capabilities.md) | entity |
| [Foundry and Foundry Field](charts/foundry-field.md) | entity |
| [Pale Sun and Red Wash](charts/pale-sun-red-wash.md) | entity |
| [American Resource Utility Leadership](charts/people-aru-leadership.md) | people |
| [American Resource Utility Operations](charts/people-aru-operations.md) | people |
| [Atlas Meridian Product Leadership](charts/people-atlas-meridian.md) | people |
| [Board Committees](charts/people-board-committees.md) | people |
| [Blood, Sweat & Tears Railway](charts/people-bst.md) | people |
| [Project Cradle Team](charts/people-cradle.md) | people |
| [Enterprise Leadership](charts/people-enterprise.md) | people |
| [Foundry and Customer Delivery](charts/people-foundry-field.md) | people |
| [Pale Sun and Red Wash Leadership](charts/people-pale-sun-red-wash.md) | people |
| [Willow and Advanced Programs](charts/people-willow-leadership.md) | people |
| [Willow Research Team](charts/people-willow-team.md) | people |
| [Project Cradle](charts/project-cradle.md) | entity |
| [Willow and the Fort](charts/willow-fort.md) | entity |
| [Project Cradle — external hosts](charts/external-cradle-hosts.md) | entity |
| [External investors](charts/external-investors.md) | entity |
| [Historical opportunities](charts/historical-opportunities.md) | historical |
| [The Original Eight](charts/people-original-eight.md) | historical |
| [Research artifacts](charts/research-artifacts.md) | historical |
| [Research history](charts/research-history.md) | historical |
| [Business origins and former counterparties](charts/external-counterparties.md) | historical |

## Sources and maintenance

[Display source](source/chartbook.json) · [Chart register](ORGANIZATION_MAP_REGISTER.json) · [Governance](CHART_GOVERNANCE.md) · [Source traceability](CANON_TRACEABILITY_MATRIX.md) · [Migration and preserved history](CHART_MIGRATION.md) · [Pinned-source exceptions](SOURCE_LOCK_EXCEPTIONS.md)

Install `tools/organization/requirements.txt`, then run `python scripts/build_organization_charts.py`. The exporter reproduces page artwork and supporting records from the approved vector PDF and validates every card against the display source. It leaves the visual master and historical publications unchanged. Changes to a chart require an updated visual master and matching sourced display data.
