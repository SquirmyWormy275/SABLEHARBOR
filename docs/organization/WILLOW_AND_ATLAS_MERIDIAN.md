# SABLE HARBOR — WILLOW AND ATLAS MERIDIAN ORGANIZATION MAP

**Map ID:** `SH-ORG-007`  
**Version:** 0.3.0  
**Canonical date:** September 8, 2026  
**Map type:** Laboratory composition, product lineage, and current product-organization boundary  
**Edge meaning:** Documented membership, contribution, authority, lineage, or product/professional interface. **Edges are not reporting lines unless explicitly stated as “runs.”**

## Willow's two centers of gravity

```mermaid
flowchart TB
    WILLOW["PROJECT WILLOW / WILLOW LABS<br/>bounded industrial experimentation<br/><b>Question → belief → experiment → observation → decision</b>"]

    GID["Gid Voss<br/><b>runs Willow from Pittsburgh</b><br/>experimental and epistemic authority"]
    SLOANE["Rachel Sloane<br/><b>Sacramento institutional seam</b><br/>budget · legal · security · product · executive translation<br/><i>not Gid's boss</i>"]

    subgraph EARLY["PITTSBURGH CORE — DOCUMENTED 2021 TEAM"]
        MARA["Mara Aquil<br/>embedded and field systems<br/>field reliability"]
        THEO["Theo Bell<br/>applied mathematics<br/>proxy-signal discovery"]
        BENJI["Benji Rao<br/>mechanical systems<br/>prototypes"]
        JUN["Jun Park<br/>human-computer interaction<br/>operator-centered design"]
        ELI["Eli — surname OPEN<br/>RF and communications"]
        TWO["Approximately two additional early staff<br/><b>identities OPEN</b>"]
    end

    subgraph LATER["DOCUMENTED 2025 HIRES"]
        OWEN["Owen Kessler<br/>junior research engineering<br/>joined August 2025"]
        LAYLA["Layla Haddad<br/>evidence, rules, and accountable rails<br/>joined September 2025"]
    end

    GID -->|runs| WILLOW
    SLOANE -.->|institutional connection and accountability| WILLOW

    WILLOW --- MARA
    WILLOW --- THEO
    WILLOW --- BENJI
    WILLOW --- JUN
    WILLOW --- ELI
    WILLOW --- TWO
    WILLOW --- OWEN
    WILLOW --- LAYLA
```

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

The historical bridge remains part of Atlas's formation. The September 8 closeout changes the **current organizational interpretation**, not the lineage: the dedicated Atlas organization is now a product-development organization rather than a cross-functional professional-services bench.

## Current Atlas Meridian organization boundary

```mermaid
flowchart LR
    ATL["ATLAS MERIDIAN PRODUCT ORGANIZATION<br/>commercial product + professional platform"]
    ENG["Product engineering<br/>runtime · workflows · integrations · reliability"]
    PM["Product management + design<br/>requirements · UX · product boundaries"]
    EVAL["AI / agent evaluation<br/>tests · safety · provenance · authority rails"]
    SEC["Security / tenancy / entitlements<br/>client isolation · data controls"]
    TRANSFER["Transfer + developer tooling<br/>client-owned derivatives · export · runbooks"]
    ADV["SABLE HARBOR ADVISORY<br/>client-facing professional business<br/>three practices · one bench"]
    CLIENT["CLIENT PLANE<br/>client data · matters · workflows · agents · transfer"]
    PRO["SABLE HARBOR PROFESSIONAL PLANE<br/>protected methods · cross-matter learning · firm-only capabilities"]
    FF["FOUNDRY FIELD<br/>flagship deployable operational product"]

    ATL --- ENG
    ATL --- PM
    ATL --- EVAL
    ATL --- SEC
    ATL --- TRANSFER
    ATL --> CLIENT
    ATL --> PRO
    ATL -.->|product substrate and matter system| ADV
    FF -.->|represented operational terrain where licensed| ADV
    ADV -->|professional intervention + client-safe transfer| CLIENT
    PRO -.->|controlled firm-only capability| ADV
```

The nodes inside the Atlas product organization are capability groupings, not locked departments or headcount allocations. Exact org structure, titles and staffing remain implementation decisions unless separately canonized.

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

- [`SH-ADV-ATL-DR-001`](../canon/ADVISORY_ATLAS_MERIDIAN_CLOSEOUT_2026-09-08.md)
- [`SH-ATL-016`](../advisory/ATLAS_MERIDIAN_PROFESSIONAL_PLATFORM.md)
- [`SH-ADV-001`](../advisory/OPERATING_MODEL.md)
