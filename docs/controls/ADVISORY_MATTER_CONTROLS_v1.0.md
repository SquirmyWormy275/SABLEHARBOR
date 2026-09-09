# SABLE HARBOR — ADVISORY MATTER CONTROL STANDARD

**Document ID:** `SH-ADV-CTRL-001`  
**Version:** 1.1.0  
**Effective:** September 9, 2026  
**State:** `LOCKED DIRECTION`  
**Control owner:** Advisory President with Enterprise Risk/Controls  
**Related:** `SH-OBJ-ADV-001`–`003`; `SH-ADV-002`–`018`; `SH-ADV-ATL-DR-003`

## Purpose

This standard operationalizes the Advisory control objectives for an AI-native, outcome-priced professional-services business. It supplements the Common Control Framework; it does not replace enterprise Legal, Security, Finance, People, Records, Product or J2 controls.

## Control objectives

### ADV-ACC — Matter acceptance

**Objective:** Sable Harbor accepts only matters it can perform competently, lawfully, independently enough for the requested work, and within explicit authority.

| Control | Requirement | Evidence |
|---|---|---|
| ADV-ACC-01 | Acceptance Principal approves the matter before substantive delivery | `SH-ADV-TPL-001` / Atlas acceptance record |
| ADV-ACC-02 | Client, counterparty, decision owner, scope and authority boundary are documented | Atlas matter header / contract |
| ADV-ACC-03 | Conflicts, operating-business/J2 proximity and independence implications are dispositioned | conflict record |
| ADV-ACC-04 | Competence and staffing plan are supportable | matter staffing rationale |
| ADV-ACC-05 | Data rights, security, privacy and residency conditions are accepted before access | data/security acceptance |
| ADV-ACC-06 | Purchased-conclusion risk is explicitly considered | acceptance assertion |
| ADV-ACC-07 | Matter receives Q1–Q4 quality tier and required review plan | quality-tier record |
| ADV-ACC-08 | Material changes trigger reacceptance | reacceptance/version record |

### ADV-VAL — Outcome economics

**Objective:** Variable fees are measured against an independently governed baseline and cannot be manipulated by the delivery team.

| Control | Requirement | Evidence |
|---|---|---|
| ADV-VAL-01 | Value Office approves baseline, metrics, attribution and payout curve before substantive work | `SH-ADV-TPL-003` |
| ADV-VAL-02 | Baseline changes require independent disposition and version history | baseline change record |
| ADV-VAL-03 | Delivery team cannot self-certify variable payout | Value Office certification |
| ADV-VAL-04 | Client dependencies and external exclusions are defined | signed Outcome Schedule |
| ADV-VAL-05 | Final value calculation is reproducible from retained source data | calculation package / Atlas lineage |
| ADV-VAL-06 | Safety/compliance countermetrics are used where narrow value metrics could reward harmful behavior | metric design/review |
| ADV-VAL-07 | Outcome-fee recognition and carry calculation exclude uncertified/uncollectible economics | Finance certification |

### ADV-PRF — Professional quality

**Objective:** Consequential matters receive independent challenge without diffusing Matter Principal accountability.

| Control | Requirement | Evidence |
|---|---|---|
| ADV-PRF-01 | One Matter Principal is named | matter record |
| ADV-PRF-02 | Independent Reviewer is appointed when risk criteria require | review assignment |
| ADV-PRF-03 | Material contrary evidence and uncertainty are retained | evidence/model record |
| ADV-PRF-04 | Professional conclusions identify accountable human authorship/adoption | signed/adopted work product |
| ADV-PRF-05 | Client pressure to alter unsupported conclusions is escalated | issue/escalation record |
| ADV-PRF-06 | Q2–Q4 matters complete required review gates and after-action review | `SH-ADV-TPL-005` / AAR |
| ADV-PRF-07 | Material errors are corrected with historical trace rather than silent overwrite | correction record |

### ADV-AI — Agent and workflow governance

**Objective:** AI and agent systems increase professional capacity without obscuring provenance, authority or accountability.

| Control | Requirement | Evidence |
|---|---|---|
| ADV-AI-01 | Material agents/tools are versioned and attributable | Atlas agent registry |
| ADV-AI-02 | Data and action scopes are bounded | entitlement/action policy |
| ADV-AI-03 | Stop conditions and human owner are defined for consequential automations | workflow policy |
| ADV-AI-04 | Material agent outputs adopted into professional conclusions are reviewable to source | provenance graph |
| ADV-AI-05 | Client-transfer classification is defined for matter-specific agents/workflows | transfer classification |
| ADV-AI-06 | Production changes pass relevant task/evaluation regressions before release | evaluation record |
| ADV-AI-07 | Transferred packages disclose model/runtime/tool dependencies and rollback | package manifest |

### ADV-XFR — Capability transfer

**Objective:** A matter promising transfer leaves the client with an operable, governed capability without leaking protected Sable Harbor IP.

| Control | Requirement | Evidence |
|---|---|---|
| ADV-XFR-01 | Client owner is named before transfer acceptance | owner record |
| ADV-XFR-02 | Client-owned, licensed, reserved and restricted components are distinguished | transfer manifest |
| ADV-XFR-03 | Transferred workflow/agent passes agreed tests | acceptance test record |
| ADV-XFR-04 | Runbook, stop conditions, support and maintenance ownership are documented | operating package |
| ADV-XFR-05 | Protected professional-plane and cross-client material are excluded | transfer scan/review |
| ADV-XFR-06 | Client can operate promised capability without undisclosed Sable Harbor dependency | acceptance demonstration |
| ADV-XFR-07 | Transfer Owner issues `SH-ADV-TPL-004` before matter close | transfer certificate |

### ADV-J2 — J2 firewall

**Objective:** Advisory cannot create a commercial incentive path that contaminates serving J2 personnel.

| Control | Requirement | Evidence |
|---|---|---|
| ADV-J2-01 | No serving J2 professional may enter an Advisory applicant pipeline | applicant control / audit |
| ADV-J2-02 | No Advisory role or carry economics may be discussed with serving J2 personnel | attestation / investigation evidence if triggered |
| ADV-J2-03 | Former J2 applicant records confirm qualifying service ended before application began | service-completion verification |
| ADV-J2-04 | Carry eligibility uses the controlling service gate, not recruiter discretion | eligibility record |
| ADV-J2-05 | Orientation anti-line-authority restrictions are checked before role approval | role-authority review |
| ADV-J2-06 | J2 Headquarters service cannot independently create carry eligibility | carry eligibility check |
| ADV-J2-07 | No matter is accepted because protected J2 content can be commercially exploited | acceptance record |

### ADV-CAR — Carry governance

**Objective:** Carry rewards long-duration Advisory value without contaminating J2 service, professional judgment or firm governance.

| Control | Requirement | Evidence |
|---|---|---|
| ADV-CAR-01 | Eligibility and allocation are separately approved | eligibility + grant records |
| ADV-CAR-02 | Pool calculation follows 20% Excess Advisory Economic Profit after losses, reserves and hurdle | Finance carry schedule |
| ADV-CAR-03 | Grants use notional units and do not confer automatic governance/line rights | grant instrument |
| ADV-CAR-04 | Vesting, holdback, leaver, clawback and malus are administered consistently | plan administration record |
| ADV-CAR-05 | Matter-level fixed percentage carry is prohibited | compensation review |
| ADV-CAR-06 | No serving J2 person is discussed as a prospective individual grantee | annual allocation review record |

### ADV-IP — Confidentiality, IP and productization

**Objective:** Client work may inform generalized product development without unauthorized transfer of client IP, and client transfer may occur without disclosure of Sable Harbor crown-jewel material.

| Control | Requirement | Evidence |
|---|---|---|
| ADV-IP-01 | Contract establishes data, background/foreground IP and product-improvement rights | executed agreement |
| ADV-IP-02 | Client-specific confidential content cannot silently enter generalized Atlas assets | productization review |
| ADV-IP-03 | Sable Harbor operating-business trade secrets remain outside client transfer unless expressly authorized | transfer review |
| ADV-IP-04 | J2 records/protected institutional material remain outside client workspaces | access/transfer controls |
| ADV-IP-05 | Client-owned/licensed/reserved/restricted classification is completed for material deliverables | IP classification |
| ADV-IP-06 | Atlas productization from client work requires rights/confidentiality generalization review | product backlog approval |

### ADV-3P — Experts and third parties

**Objective:** External specialists extend capability without creating hidden conflicts, uncontrolled access or outsourced accountability.

| Control | Requirement | Evidence |
|---|---|---|
| ADV-3P-01 | Material experts/providers receive proportionate competence, conflict, security and integrity diligence | third-party review |
| ADV-3P-02 | Access is least-necessary, time-bounded and revocable | entitlement record |
| ADV-3P-03 | Data/IP/transfer rights permit intended client use | contract/license review |
| ADV-3P-04 | Material expert assertions relied upon are attributable and documented | source/interview record |
| ADV-3P-05 | Critical provider concentration/fallback is considered for Q3/Q4 matters | continuity plan |

### ADV-COM — Commercial governance

**Objective:** Proposals and contracts accurately state what Sable Harbor can deliver and do not convert procurement pressure into professional distortion.

| Control | Requirement | Evidence |
|---|---|---|
| ADV-COM-01 | Matter class and commercial instrument match the professional product | proposal/SOW review |
| ADV-COM-02 | Atlas product and Advisory fees are separately visible | pricing schedule |
| ADV-COM-03 | Below-minimum matter pricing requires explicit strategic exception | approval record |
| ADV-COM-04 | Major scope/value/authority changes follow change control and reacceptance | change record |
| ADV-COM-05 | Proposal credentials/staffing are truthful and available | proposal review |
| ADV-COM-06 | Liability/indemnity terms outside delegated policy require reserved approval | legal approval |

## Matter risk triggers

Independent review and enhanced acceptance should be presumed for matters involving one or more of:

- physical safety or environmental consequence;
- regulated operations;
- material capital allocation;
- acquisition/disposition recommendation;
- outcome fee large enough to create material incentive conflict;
- public-company or board-level decision use;
- highly sensitive personal, security or government information;
- autonomous/semi-autonomous action in a physical or production environment;
- novel agent capability without established evaluation pattern;
- material reliance on evidence the client cannot independently inspect;
- cross-client model/IP contamination risk;
- direct competition with a Sable Harbor operating business;
- critical third-party/model dependency without fallback.

## Control philosophy

The control system should make the dangerous thing difficult without turning every matter into compliance theater. Evidence may live natively in Atlas Meridian rather than duplicate forms where the platform can preserve the same control state more reliably.
