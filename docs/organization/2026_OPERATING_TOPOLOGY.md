# SABLE HARBOR — AUGUST 31, 2026 OPERATING TOPOLOGY

**Map ID:** `SH-ORG-001`  
**Version:** 0.2.0  
**Canonical date:** August 31, 2026  
**Map type:** Operating topology  
**Edge meaning:** Portfolio relationship, product lineage, operating ownership in the narrative canon, or documented institutional interface. **No edge in this map means “reports to.”**

```mermaid
flowchart TB
    SH["SABLE HARBOR<br/>Industrial-systems company<br/><i>sometimes owns the thing it studies when control of the constraint is essential</i>"]

    subgraph PRODUCT["PRODUCT AND KNOWLEDGE SYSTEM"]
        FOUNDRY["Foundry<br/>Underlying relationship, meaning, integration, and workflow substrate"]
        FIELD["Foundry Field<br/>Deployable commercial product and service configuration<br/><b>encounters, connects, and represents</b>"]
        ATLAS["Atlas Meridian<br/>Controlled 2026 product expression of the Atlas lineage<br/><b>investigates across represented evidence</b>"]
    end

    subgraph EXPERIMENT["BOUNDED EXPERIMENTAL CAPABILITY"]
        WILLOW["Project Willow / Willow Labs<br/>Pittsburgh experimental authority<br/>Sacramento institutional seam<br/><b>tests consequential unknowns</b>"]
    end

    subgraph OPERATIONS["OPERATING VENTURES AND PHYSICAL CONSTRAINTS"]
        PALE["Pale Sun<br/>Uranium operating business<br/><b>Pale Sun first; proving ground second</b>"]
        REDWASH["Red Wash Mine<br/>Fictional underground Wyoming uranium operation"]
        CRADLE["Project Cradle<br/>Rare-earth recovery from process streams<br/><b>generally avoids owning the host mine</b>"]
        ARU["American Resource Utility<br/>Acquired resource-logistics operator<br/><b>operationally distinct during integration</b>"]
        BST["Blood, Sweat & Tears Railway<br/>ARU railway / short-line operating component"]
    end

    ADVISORY["Emerging Advisory<br/>Operating and analytical method transfer<br/><b>final name, leader, P&L, and organizational home OPEN</b>"]

    SH -->|underlying product substrate| FOUNDRY
    FOUNDRY -->|commercial product built on the substrate| FIELD

    SH -->|bounded experimental capability| WILLOW
    SH -->|controlled product expression| ATLAS
    FOUNDRY -->|represents the terrain Atlas can investigate| ATLAS
    WILLOW -->|experimental and agent lineage| ATLAS

    SH -->|uranium operating business| PALE
    PALE -->|owns and operates in the narrative canon| REDWASH

    SH -->|rare-earth recovery line| CRADLE

    SH -->|acquired operator| ARU
    ARU -->|railway / short-line operating component| BST

    SH -.->|emerging practice| ADVISORY
    FIELD -.->|mature product and deployment method| ADVISORY
    PALE -.->|operating-method source| ADVISORY
    ARU -.->|operating-method source| ADVISORY
```

## Canonical reading

The seven top-level 2026 lines of work—and the Foundry substrate beneath Foundry Field—retain distinct purposes:

| Line | Canonical role |
|---|---|
| **Foundry** | Underlying relationship-and-meaning substrate. |
| **Foundry Field** | Mature deployable commercial product and service configuration built on Foundry. |
| **Willow** | Bounded experimental capability whose unit of work is a consequential industrial question. |
| **Atlas Meridian** | Disciplined investigative product operating across represented evidence; decision support, not autonomous decision authority. |
| **Pale Sun** | Uranium operating business centered on ownership and operation of Red Wash. |
| **Cradle** | Rare-earth recovery line that seeks value in host-created process seams rather than generally owning the host mine. |
| **ARU / BS&T** | Acquired logistics operator and its railway or short-line component. |
| **Advisory** | Emerging transfer of Sable Harbor's method to operators who should own the resulting system. |

## Deliberately unresolved

This map does not choose the legal form of Foundry, Willow, Atlas Meridian, Pale Sun, Red Wash, Cradle, ARU, BS&T, or Advisory. It does not assign executive titles, direct reports, headcount, P&Ls, ownership percentages, intercompany agreements, or final ARU and Advisory leadership.

## Controlling canon

Primary anchors: corporate-lore canon sections 6, 7, 9, 10, 11, 12, and 13; decision-register IDs `FF-001`–`FF-007`, `WIL-011`–`WIL-014`, `ATL-012`–`ATL-015`, `PS-001`, `PS-006`, `PS-015`, `CRD-001`–`CRD-002`, `ARU-001`–`ARU-006`, `ADV-001`–`ADV-002`, and `ID-001`–`ID-003`.
