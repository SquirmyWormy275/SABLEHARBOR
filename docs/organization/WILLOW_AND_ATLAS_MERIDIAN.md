# SABLE HARBOR — WILLOW AND ATLAS MERIDIAN ORGANIZATION MAP

**Map ID:** `SH-ORG-007`  
**Version:** 0.2.0  
**Canonical date:** August 31, 2026  
**Map type:** Laboratory composition, institutional seam, and product-lineage map  
**Edge meaning:** Documented membership, contribution, authority, or lineage. **Edges are not reporting lines unless explicitly stated as “runs.”**

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

The membership lines show documented participation in Willow, not a direct-report hierarchy. The exact August 31, 2026 laboratory headcount, the identities of the remaining early staff, and formal titles other than the locked role descriptions remain open.

## Atlas lineage and 2026 bridge

```mermaid
flowchart TB
    THESIS["2022–2023<br/>Atlas thesis<br/>cross-system investigation beyond integration"]
    REBOOT["2024 reboot<br/>language-model experiments and improved representation"]
    HOUND["Hound — 2025<br/>Theo's crude tool-using investigative agent"]
    RANGER["Ranger — 2025<br/>Owen + Layla<br/>intent · authority · constraints · stop conditions · evidence"]
    GAUNTLET["Twenty-five-case investigation gauntlet<br/>approximately nine meaningfully reproducible in part by late 2025"]
    ANOMALY["Early-2026 anomaly<br/>Mara field-validates enough to show it is not only a plausible story<br/>Gid freezes expansion"]
    BRIDGE["Twelve-month Atlas bridge program<br/>repeatability · product boundaries · ownership"]
    ATLAS["ATLAS MERIDIAN<br/>controlled commercialization<br/><b>investigate, do not merely answer</b>"]

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

## Production and decision boundaries

- Willow's unit of work is a consequential problem, not a discipline.
- Failure is survivable; quiet drift into unsupported production is not.
- Gid can freeze experimental expansion but cannot unilaterally deploy Willow work into a production operation.
- Rachel Sloane is the Sacramento institutional seam, not Gid's manager.
- Simone's role is to stop uncontrolled capability growth long enough to prove repeatability and define product boundaries.
- Atlas Meridian is a disciplined investigative system. It preserves provenance, stops when authority is missing, and admits when evidence does not support an answer.
- Atlas Meridian supports human decisions; it does not autonomously make acquisition, capital, or operating decisions.

## Controlling canon

Primary anchors: corporate-lore canon sections 7.4–7.8, 8, 9, and 13.1; decision-register IDs `PPL-016`, `WIL-004`–`WIL-018`, and `ATL-001`–`ATL-015`.
