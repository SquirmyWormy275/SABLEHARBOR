# SABLE HARBOR — DECISION RIGHTS AND OPERATING GATES

**Map ID:** `SH-ORG-011`  
**Version:** 0.2.0  
**Canonical date:** August 31, 2026  
**Map type:** Cross-company authority and operating-gate map  
**Edge meaning:** Contribution to the locked operating sequence, documented authority, required qualification, retained operating ownership, or a separation of authority. **This map does not assign direct reports or identify an unresolved capital-authority holder.**

## Operating sequence and the production boundary

The sequence below is the canon's analytical model, not a claim that every engagement follows one rigid workflow.

```mermaid
flowchart LR
    ENCOUNTER["ENCOUNTER"]
    REPRESENT["REPRESENT"]
    TEST["TEST"]
    GATE["FIELD-QUALIFICATION + OPERATING-OWNER GATE"]
    INTERVENE["INTERVENE"]
    MEASURE["MEASURE"]
    REMEMBER["REMEMBER"]

    FIELD["Foundry Field<br/>encounters, connects, and represents"]
    FOUNDRY["Foundry<br/>preserves relationships, provenance, authority, decisions, and later outcomes"]
    WILLOW["Willow<br/>bounded experiments"]
    ATLAS["Atlas Meridian<br/>investigates across represented evidence<br/>decision support only"]
    OPERATIONS["Pale Sun, ARU, or another accountable operating owner"]
    ADVISORY["Emerging Advisory<br/>transfers the method"]

    ENCOUNTER --> REPRESENT --> TEST --> GATE --> INTERVENE --> MEASURE --> REMEMBER
    REMEMBER -.->|changes what can be encountered and represented next| ENCOUNTER

    FIELD -.-> ENCOUNTER
    FIELD -.-> REPRESENT
    FOUNDRY -.-> REPRESENT
    FOUNDRY -.-> REMEMBER
    WILLOW -.-> TEST
    ATLAS -.->|investigates across represented evidence| REPRESENT
    OPERATIONS -->|provides the accountable operating owner| GATE
    OPERATIONS -.-> INTERVENE
    OPERATIONS -.-> MEASURE
    ADVISORY -.->|transfers the method into client-owned practice| REMEMBER
```

The gate is the canonically locked boundary: Willow, Foundry, Atlas, or any other Sable Harbor unit may test work at Red Wash only through field qualification and an operating owner. The chart does not invent a universal detailed gate procedure.

## Named authority domains

```mermaid
flowchart TB
    PRIYA["Priya Raman<br/>product and technical substrate"]
    ELENA["Elena Torres<br/>deployment reality and customer-operating translation"]
    CALEB["Caleb Hargrove<br/>field operations and experimental qualification"]
    MAYA["Dr. Maya Okafor<br/>independent scientific and model challenge"]
    MARCUS["Marcus Reed<br/>senior technical authority"]
    GID["Gid Voss<br/>Willow experimental and epistemic authority"]
    MARI["Mari Varela<br/>Pale Sun operating leadership"]
    COLE["Cole<br/>Red Wash site authority and temporary stop authority"]
    SIMONE["Simone Vale<br/>Atlas transition and repeatability"]
    CAPITAL["Capital authority<br/><b>holder and structure OPEN</b>"]

    PRODUCT["Product and representation"]
    DEPLOY["Deployment and customer reality"]
    QUAL["Field qualification"]
    CLAIM["Scientific and model claims"]
    EXPERIMENT["Bounded experimentation"]
    OPERATION["Operating consequence"]
    INVESTIGATION["Controlled investigation"]
    CAPDEC["Capital decision"]

    PRIYA --> PRODUCT
    MARCUS -.->|senior technical contribution; exact domain boundary not further specified| PRODUCT
    ELENA --> DEPLOY
    CALEB --> QUAL
    MAYA --> CLAIM
    GID --> EXPERIMENT
    MARI --> OPERATION
    COLE --> OPERATION
    SIMONE --> INVESTIGATION
    CAPITAL -.-> CAPDEC

    EXPERIMENT -.->|cannot enter production without| QUAL
    PRODUCT -.->|operating change requires qualification| QUAL
    INVESTIGATION -.->|supports but does not own| OPERATION
    CLAIM -.->|independent challenge| INVESTIGATION
    QUAL -->|qualified handoff| OPERATION
```

## Immediate-consequence rule

```mermaid
flowchart LR
    EVENT["Operating event or evidence mismatch"]
    OPERATING["Operational accountability<br/><b>owns the immediate consequence</b>"]
    TECHNICAL["Technical authority<br/>investigates evidence and representation"]
    CAPITAL["Capital authority<br/><b>separate; exact holder OPEN</b>"]
    OUTCOME["Conservative action, investigation, preserved history, and later learning"]

    EVENT --> OPERATING --> OUTCOME
    EVENT -.-> TECHNICAL -.-> OUTCOME
    EVENT -.-> CAPITAL
```

## Non-negotiable boundaries

- No source or model is authoritative for every purpose.
- Foundry may represent a claim and its authority without declaring the claim physically true.
- Willow experiments require a bounded question loop and a continue, change, transfer, or kill decision.
- A successful laboratory result is not automatically operationally viable.
- Gid cannot unilaterally place an experiment into production.
- Red Wash accepts tests only through field qualification and an operating owner.
- Atlas Meridian investigates and supports decisions; it does not own final acquisition, capital, or operating decisions.
- When records disagree during an operating event, operational accountability owns the immediate consequence. Technical and capital authority remain distinct.
- Exact unresolved executive titles, reporting lines, and numeric management thresholds remain open. Board delegation bands and committee/capital oversight identities are controlled by the current governance instruments.

## Controlling canon

Primary anchors: corporate-lore canon sections 6.2–6.4, 7.7–7.8, 9.8–9.9, 10.9–10.11, 12.4–12.5, 13.1, and 14; decision-register IDs `FF-006`, `WIL-012`–`WIL-013`, `ATL-010`–`ATL-015`, `PS-012`–`PS-015`, `ARU-008`–`ARU-009`, `PPL-004`, and `PPL-007`–`PPL-010`.
