# Organization chart governance

**Revision 1.1.0 · September 10, 2026**

## Card contract

Entity cards contain only name, location and a brief description of actual work. People cards contain only name, title and joining year. Existing approved business logos appear within their cards. Biographies, authority narratives, headcounts, status labels and qualifications belong outside the cards.

## Authority

[MAINTAINERS.md](../../MAINTAINERS.md) controls source precedence. The [approved design decision](../canon/ORG_CHART_DESIGN_AND_CLEANUP_2026-09-09.md) controls presentation. Charts do not create entities, appointments, dates, locations, reporting lines or staffing. Missing years remain unrecorded; functional display titles do not create formal appointments. Acquired-company employment years are not replaced by acquisition dates. Board years mean board appointment, as stated on their pages.

Membership and page placement do not establish reporting. The industrial ownership chart shows only the accepted 100% ownership edges. The Board collectively oversees the CEO. J2 remains outside ESS; the Head of J2 reports administratively to the CEO and has protected Board access under the headquarters doctrine. Internal Audit retains its functional independence to the Board Audit & Compliance Committee. Advisory practices use one common bench.

## Publication source

The approved vector PDF is the visual authoring master. [Display data](source/chartbook.json) retains the exact card fields, source evidence, page bounds and qualifications. Neither overrides canonical source documents. The exporter checks every printed card against that data and generates SVG/PNG views, chart pages and inventories. An updated publication requires matching source data and visual review; it cannot be made current by changing a checksum alone.

The recovered September 9 PDF is preserved in history/v1.0.0. The September 10 successor retains its typography, spacing, connectors and logos, adds the approved J2 people page and Head of J2 enterprise card, and updates publication footers. Outlined SVG text preserves appearance across viewers; accessible descriptions and Markdown tables retain searchable text. The exporter leaves the master and all historical publications unchanged.

## Change control

Run the exporter, organization validator, repository hygiene, governance/publication checks and tests before merge. Validate every changed card, all affected relationships and current-source qualifications. Preserve [immutable history](CHART_MIGRATION.md) and [pinned sources](SOURCE_LOCK_EXCEPTIONS.md). No legacy generator may restore retired artwork to current navigation.
