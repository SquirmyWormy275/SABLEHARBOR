# SABLE HARBOR — PROJECT CRADLE ORGANIZATION MAP

**Map ID:** `SH-ORG-009`  
**Version:** 0.2.0  
**Canonical date:** August 31, 2026  
**Map type:** Program team and business-boundary map  
**Edge meaning:** Documented team participation, program leadership, process flow, or commercial/technical interface. **No edge means that Cradle owns the host mine or that one team member reports to another.**

## Founding team

```mermaid
flowchart TB
    SH["SABLE HARBOR"]
    CRADLE["PROJECT CRADLE<br/>rare-earth recovery from host-created process streams<br/><b>do not break the host system</b>"]

    KENJI["Kenji Arakawa<br/><b>program lead</b><br/>extractive metallurgy<br/>“Where does the value die?”"]
    TESSA["Tessa Quinn<br/><b>economic geology</b><br/>chemistry cannot negotiate with geology"]
    LUIS["Luis Ortega<br/><b>process engineering and operating reality</b><br/>“Where does it go?”"]
    MAEVE["Maeve Donnelly<br/><b>data engineering and material genealogy</b><br/>source → process → stream → discard → destination"]

    SH -->|rare-earth recovery line| CRADLE
    KENJI -->|leads| CRADLE
    TESSA ---|documented founding-team role| CRADLE
    LUIS ---|documented founding-team role| CRADLE
    MAEVE ---|documented founding-team role| CRADLE
```

## Business boundary

```mermaid
flowchart LR
    HOST["External host mine or processing plant<br/><b>generally not owned by Cradle</b>"]
    PROCESS["Existing host process<br/>already pays for crushing · separation · pumping · other work"]
    STREAM["Concentrated side stream, reject, residue, or discard"]
    RECOVERY["Cradle recovery intervention<br/>equipment · process right · access · participation · stream-specific interest"]
    VALUE["Saleable or further-processable recovered stream"]

    HOST --> PROCESS --> STREAM
    STREAM --> RECOVERY --> VALUE
    CRADLE["Project Cradle"] -.->|designs, controls, or commercially participates in| RECOVERY
    CRADLE -.->|must not interrupt| PROCESS
```

## Locked distinctions

- Cradle is not a conventional rare-earth mining company.
- The orebody is not necessarily the business boundary.
- Cradle generally seeks the smallest recovery intervention that creates value without breaking the host operation.
- The business may own or control equipment, process rights, access, recovery rights, a royalty, or another stream-specific interest; exact legal structures remain open.
- Ned Kelly, Wallaby, and Stream 17 are program and product-development history, not separate departments.
- The first host customer, material, process, economics, agreement, and legal structure remain open.

## Controlling canon

Primary anchors: corporate-lore canon sections 10.6 and 11; decision-register IDs `AUS-004` and `CRD-001`–`CRD-010`.
