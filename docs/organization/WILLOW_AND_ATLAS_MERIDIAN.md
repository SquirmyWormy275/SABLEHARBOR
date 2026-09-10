# SABLE HARBOR — WILLOW AND ATLAS MERIDIAN ORGANIZATION MAP

**Map ID:** `SH-ORG-007`  
**Version:** 0.4.0  
**Canonical date:** September 9, 2026  
**Map type:** Laboratory composition, product lineage, and current product-organization boundary  
**Edge meaning:** Documented membership, contribution, authority, lineage, or product/professional interface. **Edges are not reporting lines unless explicitly stated as “runs.”**

## Willow's two centers of gravity

See [Willow leadership](charts/people-willow-leadership.md) and the [research team](charts/people-willow-team.md). Rachel Sloane’s institutional role does not make her Gid Voss’s supervisor.

The membership lines show documented participation in Willow, not a direct-report hierarchy. The exact August 31, 2026 laboratory headcount, the identities of the remaining early staff, and formal titles other than locked role descriptions remain open.

## Atlas lineage

```mermaid
flowchart TB
    THESIS["2022–2023<br/>Atlas thesis<br/>cross-system investigation beyond integration"]
    REBOOT["2024 reboot<br/>language-model experiments and improved representation"]
    HOUND["Hound — 2025<br/>Theo's crude tool-using investigative agent"]
    RANGER["Ranger — 2025<br/>Owen + Layla<br/>intent · authority · constraints · stop conditions · evidence"]
    GAUNTLET["Twenty-five-case investigation gauntlet<br/>approximately nine meaningfully reproducible in part by late 2025"]
    ANOMALY["Early-2026 anomaly<br/>Mara field-validates enough to show it is not only a plausible story<br/>Gid freezes expansion"]
    BRIDGE["Twelve-month Atlas bridge program<br/>repeatability · product boundaries · ownership"]
    ATLAS["ATLAS MERIDIAN<br/>commercial enterprise product<br/><b>investigate, do not merely answer</b>"]

    FOUNDRY["Foundry<br/>represented terrain, mappings, provenance, exceptions"]
    WILLOW["Willow<br/>experimental and agent lineage"]
    SLOANE["Rachel Sloane<br/>recognizes cross-functional convergence"]
    SIMONE["Simone Vale<br/>transition / product leader<br/>proves what can repeat"]
    PRIYA["Priya Raman<br/>product and technical substrate"]
    JUN["Jun Park<br/>adds “Meridian” to the lineage name"]

    FOUNDRY --> THESIS
    WILLOW --> THESIS
    THESIS --> REBOOT
    REBOOT --> HOUND
    HOUND --> GAUNTLET
    RANGER --> GAUNTLET
    GAUNTLET --> ANOMALY --> BRIDGE --> ATLAS

    SLOANE -.->|institutional synthesis| BRIDGE
    SIMONE -->|transition and repeatability leadership| BRIDGE
    PRIYA -.->|product and substrate authority| BRIDGE
    JUN -.->|name contribution| ATLAS
    FOUNDRY -->|represents the terrain| ATLAS
    WILLOW -->|experimental lineage| ATLAS
```

The historical bridge remains part of Atlas's formation. The September 8/9 closeouts change the **current organizational interpretation**, not the lineage: the dedicated Atlas organization is now a product-development organization rather than a cross-functional professional-services bench.

## Current Atlas Meridian organization boundary

See [Atlas Meridian product organization](charts/atlas-meridian.md) and [named product leadership](charts/people-atlas-meridian.md).

The nodes inside the Atlas product organization are capability groupings, not locked departments or headcount allocations. Exact reporting lines and staffing remain product implementation decisions unless separately canonized.

## Commercial product architecture

Atlas now has four controlled commercial configurations:

- **Core** — evidence, provenance, investigation/matter workspace, controlled agents and transferable workflows;
- **Enterprise** — enterprise tenancy, advanced entitlements, connectors/APIs, evaluation, audit export, SSO/SCIM and governance;
- **Professional** — Sable Harbor-controlled professional plane used by Advisory and not generally sold as a client edition;
- **Managed** — client-plane capability operated by Sable Harbor under explicit managed-continuity terms.

Default licensing is institutional/tenant-based. Product pricing, support, security, export, agent packaging and evaluation are controlled by `SH-ATL-017`.

## Product and professional boundaries

- Willow's unit of work is a consequential problem, not a discipline.
- Failure is survivable; quiet drift into unsupported production is not.
- Gid can freeze experimental expansion but cannot unilaterally deploy Willow work into a production operation.
- Rachel Sloane is the Sacramento institutional seam, not Gid's manager.
- Simone's historical bridge role remains to stop uncontrolled capability growth long enough to prove repeatability and define product boundaries.
- Atlas Meridian remains a disciplined investigative system. It preserves provenance, stops when authority is missing, and admits when evidence does not support an answer.
- Atlas Meridian supports human decisions; it does not autonomously make acquisition, capital, or operating decisions.
- Atlas Meridian is both client product and Sable Harbor Advisory's professional workbench.
- The Atlas team builds the machine; Advisory owns client professional work.
- Product developers may support product incidents, requirements and controlled design partnerships but do not become a shadow consulting bench.
- Where Advisory creates a durable agent/workflow capability, Atlas must support a hardened client-ownable derivative without leaking Sable Harbor's protected professional plane.
- Foundry Field remains the flagship deployable operational product and is not reduced to an Atlas feature.

## Controlling canon

Primary historical anchors remain corporate-lore canon sections 7.4–7.8, 8, 9 and 13.1; decision-register IDs `PPL-016`, `WIL-004`–`WIL-018`, and `ATL-001`–`ATL-015`.

Current product/advisory interpretation is controlled by:

- [`SH-ADV-ATL-DR-003`](../canon/DECISION_REGISTER_ADDENDUM_2026-09-09_ADVISORY_TIER1.md)
- [`SH-ATL-016`](../advisory/ATLAS_MERIDIAN_PROFESSIONAL_PLATFORM.md)
- [`SH-ATL-017`](../advisory/ATLAS_MERIDIAN_COMMERCIAL_PRODUCT_STANDARD.md)
- [`SH-ADV-MAN-001`](../advisory/SABLE_HARBOR_ADVISORY_FIRM_MANUAL_2026-09-09.md)
