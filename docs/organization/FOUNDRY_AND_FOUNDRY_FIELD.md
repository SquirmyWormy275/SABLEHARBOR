# SABLE HARBOR — FOUNDRY AND FOUNDRY FIELD ORGANIZATION MAP

**Map ID:** `SH-ORG-006`  
**Version:** 0.2.0  
**Canonical date:** August 31, 2026  
**Map type:** Product, authority, and operating-interface map  
**Edge meaning:** Product lineage, documented authority, contribution, or operating interface. **No edge establishes a reporting line.**

## Product architecture

```mermaid
flowchart TB
    SERVICES["2016–2018 services work<br/>mappings · reconciliations · integrations · decision-support tools"]
    FOUNDRY["Foundry<br/>reusable relationship, meaning, integration, and workflow substrate<br/><b>begins in 2018</b>"]
    FIELD["Foundry Field<br/>deployable operational product and service configuration<br/><b>formal commercial identity during 2020–2021</b>"]

    subgraph APPLICATIONS["OPERATIONAL APPLICATION FAMILIES — NAMES PROVISIONAL, BEHAVIOR LOCKED"]
        OPS["Operations<br/>production · haulage · plan variance · current state"]
        MAINT["Maintenance<br/>work orders · equipment identity · downtime · operating consequence"]
        RECON["Reconciliation<br/>geology · mine · plant · laboratory · inventory · finance boundaries"]
        EXCEPT["Exceptions<br/>evidence or definitions requiring human attention"]
    end

    USERS["Operating users<br/>planners · superintendents · maintenance teams · metallurgists · managers"]

    SERVICES -->|reusable machinery extracted from repeated work| FOUNDRY
    FOUNDRY -->|commercial product built on the substrate| FIELD
    FIELD --> OPS
    FIELD --> MAINT
    FIELD --> RECON
    FIELD --> EXCEPT
    FIELD -->|used by| USERS
```

## Authority and contribution map

```mermaid
flowchart LR
    PRIYA["Priya Raman<br/><b>owns product and technical substrate</b><br/>primary product and architectural force"]
    MARCUS["Marcus Reed<br/><b>senior technical authority</b><br/>resolver; no sole-person knowledge dependency"]
    ELENA["Elena Torres<br/><b>deployment reality and customer-operating translation</b>"]
    CALEB["Caleb Hargrove<br/><b>field and operating translation</b>"]
    NADIA["Nadia<br/><b>Foundry engineer</b><br/>uncertain identity and competing-observation support<br/>FDR-27 / the Cole Memo<br/><i>surname and formal title OPEN</i>"]

    FOUNDRY["Foundry substrate"]
    FIELD["Foundry Field"]
    ATLAS["Atlas Meridian"]

    PRIYA -->|product and architecture authority| FOUNDRY
    MARCUS -.->|resolver lineage and documented technical contribution| FOUNDRY
    NADIA -->|documented product contribution| FOUNDRY
    ELENA -.->|deployment counterweight| FIELD
    CALEB -.->|operating reality input| FIELD

    FOUNDRY -->|underlies| FIELD
    FOUNDRY -->|represents the terrain| ATLAS
```

## Locked distinctions

- Foundry is the substrate; Foundry Field is the deployable commercial product and service configuration.
- Integrations are necessary plumbing, not the central invention. The invention is the knowledge layer preserving relationships and meaning.
- Authority is purpose-specific. Foundry records what a source is authoritative for, during which period, under which definition, and with which limitations.
- The mature loop is **Observe → relate → reconcile → surface → act → record → learn**.
- Foundry represents observations, records, claims, transformations, authority, and change. It does not certify the physical world as ground truth.
- Generalization must not erase the local meaning that made a variation useful.
- Exact team size, management hierarchy, application names, P&L, and legal form remain unresolved.

## Controlling canon

Primary anchors: corporate-lore canon sections 5.1, 6.1–6.8, 8.4–8.5, 9.1–9.2, 10.10, and 13.1; decision-register IDs `PPL-004`, `PPL-007`–`PPL-010`, `PPL-017`, `FF-001`–`FF-008`, `CRX-001`–`CRX-005`, `ATL-014`, and `PS-014`.
