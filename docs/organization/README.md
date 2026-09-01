# SABLE HARBOR — ORGANIZATION MAPS

**Version:** 0.2.0  
**Canonical date represented:** August 31, 2026  
**Status:** Canon-derived presentation layer  
**Controlling sources:** [`SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md`](../canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md), [`DECISION_REGISTER.md`](../canon/DECISION_REGISTER.md), and [`SABLE_HARBOR_CONTINUITY_AUDIT_v0.2.md`](../canon/SABLE_HARBOR_CONTINUITY_AUDIT_v0.2.md)

This package converts the locked corporate-history spine into reusable GitHub-rendered Mermaid diagrams for the repository README, the public wiki, and future operating-model work. It preserves the difference among:

- operating topology;
- product and institutional lineage;
- domain authority;
- documented team composition;
- operating ownership;
- qualification and decision gates;
- legal entities and direct reporting lines, which remain open.

## Recommended reading order

| Map | What it answers | Best use |
|---|---|---|
| [`2026_OPERATING_TOPOLOGY.md`](2026_OPERATING_TOPOLOGY.md) | What are Sable Harbor's major 2026 lines of work, and how do they relate? | Root README and wiki organization landing page |
| [`2026_LEADERSHIP_AND_AUTHORITY_MAP.md`](2026_LEADERSHIP_AND_AUTHORITY_MAP.md) | Which named people hold canonically defined stewardship, authority, leadership, challenge, or institutional-interface roles? | Wiki leadership and governance pages |
| [`DECISION_RIGHTS_AND_OPERATING_GATES.md`](DECISION_RIGHTS_AND_OPERATING_GATES.md) | How does work move from question or prototype to qualified operating action, and who retains decision authority? | Governance, safety, product, and operating pages |
| [`ORIGINAL_EIGHT.md`](ORIGINAL_EIGHT.md) | Who are the three founders and five early employees, and what is their 2026 status? | History and people pages |
| [`ORGANIZATIONAL_LINEAGE_2015_2026.md`](ORGANIZATIONAL_LINEAGE_2015_2026.md) | How did services, Foundry, Evalon, Emberline, Willow, Atlas, Pale Sun, Cradle, ARU, and Advisory emerge? | Timeline and portfolio-history pages |

## Detailed product, laboratory, and operating-line maps

| Map | Canonical scope |
|---|---|
| [`FOUNDRY_AND_FOUNDRY_FIELD.md`](FOUNDRY_AND_FOUNDRY_FIELD.md) | Separates the Foundry substrate from the Foundry Field commercial product and maps documented product authorities and contributors. |
| [`WILLOW_AND_ATLAS_MERIDIAN.md`](WILLOW_AND_ATLAS_MERIDIAN.md) | Maps Willow's Pittsburgh laboratory, Sacramento seam, documented team, and the cross-functional lineage into Atlas Meridian. |
| [`PALE_SUN_AND_RED_WASH.md`](PALE_SUN_AND_RED_WASH.md) | Maps Pale Sun, Red Wash, Mari, Cole, the external Walt Sutter evidence relationship, and the field-qualification gate. |
| [`PROJECT_CRADLE.md`](PROJECT_CRADLE.md) | Maps Cradle's four-person founding team and its recovery-system boundary with external host operations. |
| [`ARU_BST_AND_ADVISORY.md`](ARU_BST_AND_ADVISORY.md) | Maps the acquired ARU operating estate, BS&T component, custody authority rule, and emerging Advisory lineage. |

## Control and traceability

| Artifact | Purpose |
|---|---|
| [`LEGAL_AND_REPORTING_STRUCTURE_STATUS.md`](LEGAL_AND_REPORTING_STRUCTURE_STATUS.md) | States what the current canon supports and what a conventional legal-entity or reporting tree may not yet claim. |
| [`CHART_GOVERNANCE.md`](CHART_GOVERNANCE.md) | Defines chart authority, edge vocabulary, prohibited visual shortcuts, and wiki synchronization rules. |
| [`ORGANIZATION_MAP_REGISTER.json`](ORGANIZATION_MAP_REGISTER.json) | Machine-readable chart index with source decisions and prohibited interpretations. |
| [`CANON_TRACEABILITY_MATRIX.md`](CANON_TRACEABILITY_MATRIX.md) | Human-readable trace from load-bearing chart claims to canon sections and decision IDs. |
| [`../../scripts/validate_organization_maps.py`](../../scripts/validate_organization_maps.py) | Standard-library validation of chart IDs, metadata, register paths, decision references, and high-risk visual shortcuts. |

## Canon-preserving interpretation rules

1. **A line has only the meaning stated in that chart.** It is never an implied reporting relationship.
2. **Distinct canon concepts remain distinct.** Foundry is not Foundry Field; Pale Sun is not Red Wash; ARU is not BS&T.
3. **Operating ownership is not a finalized legal entity chain.** The narrative can lock that Pale Sun owns and operates Red Wash while transaction entities and jurisdictions remain open.
4. **Named participation is not a direct report.** Willow and Cradle team maps show documented membership and roles, not management hierarchy.
5. **Institutional connection is not supervision.** Rachel Sloane is explicitly not Gid Voss's boss.
6. **OPEN nodes remain visible.** ARU leadership, Advisory structure, exact titles, reporting lines, legal forms, and quantitative allocations are not filled with plausible inventions.
7. **Historical units remain historical.** Evalon and Emberline appear in lineage maps but not as standalone August 31, 2026 core divisions.
8. **Repository sources control wiki reproductions.** A wiki edit must not create a relationship that has not first been accepted in the repository canon.

## Publication pattern

The root README uses a compact version of `SH-ORG-001`. Wiki pages should reproduce the relevant Mermaid block directly or use a rendered derivative while preserving:

- chart ID and version;
- canonical date;
- edge meaning;
- OPEN and PROVISIONAL labels;
- source repository path;
- a statement that repository canon controls.

When canon changes, update the controlling canon first, then the applicable chart, the register, the README summary if necessary, and finally the wiki.
