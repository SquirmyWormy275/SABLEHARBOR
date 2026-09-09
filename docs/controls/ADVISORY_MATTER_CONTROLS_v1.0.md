# SABLE HARBOR — ADVISORY MATTER CONTROL STANDARD

**Document ID:** `SH-ADV-CTRL-001`  
**Version:** 1.0.0  
**Effective:** September 8, 2026  
**State:** `LOCKED DIRECTION`  
**Control owner:** Advisory President with Enterprise Risk/Controls  
**Related:** `SH-OBJ-ADV-001`–`003`; `SH-ADV-002`; `SH-ADV-ATL-DR-001`

## Purpose

This standard operationalizes the Advisory control objectives for an AI-native, outcome-priced professional-services business. It supplements the Common Control Framework; it does not replace enterprise Legal, Security, Finance, People, Records, Product or J2 controls.

## Control objectives

### ADV-ACC — Matter acceptance

**Objective:** Sable Harbor accepts only matters it can perform competently, lawfully, independently enough for the requested work, and within explicit authority.

| Control | Requirement | Evidence |
|---|---|---|
| ADV-ACC-01 | Acceptance Principal approves the matter before substantive delivery | signed/recorded matter acceptance |
| ADV-ACC-02 | Client, counterparty, decision owner, scope and authority boundary are documented | Atlas matter header / contract |
| ADV-ACC-03 | Conflicts and independence implications are dispositioned | conflict record |
| ADV-ACC-04 | Competence and staffing plan are supportable | matter staffing rationale |
| ADV-ACC-05 | Data rights, security and residency conditions are accepted before access | data/security acceptance |
| ADV-ACC-06 | Purchased-conclusion risk is explicitly considered | acceptance assertion |

### ADV-VAL — Outcome economics

**Objective:** Variable fees are measured against an independently governed baseline and cannot be manipulated by the delivery team.

| Control | Requirement | Evidence |
|---|---|---|
| ADV-VAL-01 | Value Office approves baseline, metrics, attribution and payout curve before substantive work | value schedule |
| ADV-VAL-02 | Baseline changes require independent disposition and version history | baseline change record |
| ADV-VAL-03 | Delivery team cannot self-certify variable payout | Value Office certification |
| ADV-VAL-04 | Client dependencies and external exclusions are defined | signed measurement schedule |
| ADV-VAL-05 | Final value calculation is reproducible from retained source data | calculation package / Atlas lineage |

### ADV-PRF — Professional quality

**Objective:** Consequential matters receive independent challenge without diffusing Matter Principal accountability.

| Control | Requirement | Evidence |
|---|---|---|
| ADV-PRF-01 | One Matter Principal is named | matter record |
| ADV-PRF-02 | Independent Reviewer is appointed when risk criteria require | review assignment |
| ADV-PRF-03 | Material contrary evidence and uncertainty are retained | evidence/model record |
| ADV-PRF-04 | Professional conclusions identify accountable human authorship/adoption | signed/adopted work product |
| ADV-PRF-05 | Client pressure to alter unsupported conclusions is escalated | issue/escalation record |

### ADV-AI — Agent and workflow governance

**Objective:** AI and agent systems increase professional capacity without obscuring provenance, authority or accountability.

| Control | Requirement | Evidence |
|---|---|---|
| ADV-AI-01 | Material agents/tools are versioned and attributable | Atlas agent registry |
| ADV-AI-02 | Data and action scopes are bounded | entitlement/action policy |
| ADV-AI-03 | Stop conditions and human owner are defined for consequential automations | workflow policy |
| ADV-AI-04 | Material agent outputs adopted into professional conclusions are reviewable to source | provenance graph |
| ADV-AI-05 | Client-transfer classification is defined for matter-specific agents/workflows | transfer classification |

### ADV-XFR — Capability transfer

**Objective:** A matter promising transfer leaves the client with an operable, governed capability without leaking protected Sable Harbor IP.

| Control | Requirement | Evidence |
|---|---|---|
| ADV-XFR-01 | Client owner is named before transfer acceptance | owner record |
| ADV-XFR-02 | Client-owned, licensed and Sable Harbor-retained components are distinguished | transfer manifest |
| ADV-XFR-03 | Transferred workflow/agent passes agreed tests | acceptance test record |
| ADV-XFR-04 | Runbook, stop conditions, support and maintenance ownership are documented | operating package |
| ADV-XFR-05 | Protected professional-plane and cross-client material are excluded | transfer scan/review |
| ADV-XFR-06 | Client can operate promised capability without undisclosed Sable Harbor dependency | acceptance demonstration |

### ADV-J2 — J2 firewall

**Objective:** Advisory cannot create a commercial incentive path that contaminates serving J2 personnel.

| Control | Requirement | Evidence |
|---|---|---|
| ADV-J2-01 | No serving J2 professional may enter an Advisory applicant pipeline | applicant control / audit |
| ADV-J2-02 | No Advisory role or carry economics may be discussed with serving J2 personnel | attestation / investigation evidence if triggered |
| ADV-J2-03 | Former J2 applicant records confirm qualifying service ended before application began | service-completion verification |
| ADV-J2-04 | Carry eligibility uses the controlling service gate, not recruiter discretion | eligibility record |
| ADV-J2-05 | Orientation anti-line-authority restrictions are checked before role approval | role-authority review |

### ADV-IP — Confidentiality and productization

**Objective:** Client work may inform generalized product development without unauthorized transfer of client IP, and client transfer may occur without disclosure of Sable Harbor crown-jewel material.

| Control | Requirement | Evidence |
|---|---|---|
| ADV-IP-01 | Contract establishes data, work-product and product-improvement rights | executed agreement |
| ADV-IP-02 | Client-specific confidential content cannot silently enter generalized Atlas assets | productization review |
| ADV-IP-03 | Sable Harbor operating-business trade secrets remain outside client transfer unless expressly authorized | transfer review |
| ADV-IP-04 | J2 records and protected internal institutional material remain outside client workspaces | access/transfer controls |

## Matter risk triggers

Independent review and enhanced acceptance should be presumed for matters involving one or more of:

- physical safety or environmental consequence;
- regulated operations;
- material capital allocation;
- acquisition/disposition recommendation;
- outcome fee large enough to create a material incentive conflict;
- public-company or board-level decision use;
- highly sensitive personal, security or government information;
- autonomous or semi-autonomous action in a physical or production environment;
- novel agent capability without an established evaluation pattern;
- material reliance on evidence the client cannot independently inspect;
- cross-client model or IP contamination risk.

## Control philosophy

The control system should make the dangerous thing difficult without turning every matter into a compliance ceremony. Evidence may live natively in Atlas Meridian rather than in duplicate forms where the platform can preserve the same control state more reliably.
