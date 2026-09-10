# Third-party services and internal operations — reconciliation pass

**Date:** September 9, 2026  
**State:** RECONCILED PLANNING / owner-approved sourcing decisions captured; implementation details remain open  
**Planning PR:** #112  
**PR branch:** `planning/third-party-services-2026-09-09`  
**Original planning head:** `4d5b76479f8a3b6309b63f701df2efd653f6a7e7`  
**Current main reviewed:** `d17f9838f972e76843714f73f4054cf1c189b763`  
**Decision record:** `docs/canon/THIRD_PARTY_SERVICES_SOURCING_DECISIONS_2026-09-09.md`

## 1. Reconciliation result

The September 9 sourcing session resolves the governing direction for the service inventory in PR #112 sufficiently to move from broad sourcing debate into structured implementation planning.

The controlling pattern is now:

- keep product IP, institutional knowledge, operating judgment, analytics, security authority, infrastructure operation and customer responsibility inside Sable Harbor;
- purchase commodity enterprise software, externally originated data, external network/carrier services, regulated or independence-required services, and narrow specialist expertise;
- where software/platforms are purchased, retain architecture, administration, integration, policy, security, recovery and exit capability internally;
- progressively increase Sable Harbor ownership of compute hardware and technical stack as scale permits;
- use professional third-party facilities/colocation rather than immediately owning data-center buildings;
- preserve truly independent assurance externally;
- preserve J2, Internal Audit, CISO and existing substantive business/support boundaries.

This direction is consistent with the locked Enterprise Technology Services and ESS doctrines on current main. No doctrine change is required to support it.

## 2. Current-main drift review

PR #112 was originally based on `7988f4740f39afa4a3db92e9efe1e0d737840d6d`. Current main is now `d17f9838f972e76843714f73f4054cf1c189b763` after the organization-chart cleanup.

The current main changes reviewed do not overturn the sourcing assumptions in PR #112. The locked technology doctrine still establishes:

- Enterprise Technology Services as an internal product/engineering organization;
- product engineering owned by the businesses;
- shared platform, cloud/compute, enterprise AI, architecture and reliability functions owned centrally;
- independent CISO authority;
- resilience as an operating capability requiring actual restoration testing.

The locked ESS doctrine still establishes Finance, People & Culture, Legal, Technology, Security, Procurement, Safety and Facilities as substantive functions under the ESS administrative umbrella, while Internal Audit and J2 retain separate authority.

The 2027 business successor policy still models 48 occupied / 54 authorized ESS positions, a $95,000 monthly corporate facilities allowance and a $4,500 annual ESS vendor allowance per occupied FTE. Those are conditional forecast assumptions, not proof of service capacity or executed vendor contracts.

## 3. Reconciled service-family treatment

The detailed owner-approved record is the sourcing decision document. For implementation purposes, the assessment inventory now falls into four operating classes.

### A. Internal capability, purchased components permitted

These are institutional capabilities Sable Harbor should operate itself even where it uses supported open-source or commercial components:

- developer platform / engineering systems;
- infrastructure automation and configuration management;
- container orchestration and platform operations;
- observability;
- secrets and cryptographic key management;
- vulnerability management;
- internal red-team / security-testing capability;
- budgeting and operational analytics;
- data engineering, modeling and interpretation across economic, market, geospatial, environmental, geological, industrial, logistics, labor, customer and regulatory information;
- enterprise risk-management capability;
- actuarial/specialized financial-risk modeling;
- credit and counterparty-risk analysis;
- recruiting/talent capability;
- J2/institutional education;
- physical security command and facilities-security operations;
- core engineering/architecture and technical judgment.

Commercial support, externally originated data, specialist equipment and narrow expert services may be purchased without changing the internal-capability classification.

### B. Purchased enterprise platforms, internally administered

These are commodity systems where building a proprietary replacement is not the strategic objective:

- email, calendar, meetings and collaboration;
- identity platform;
- endpoint/device-management platform;
- EDR tooling;
- HR/payroll/benefits processing platforms;
- accounting/procurement/expense platforms;
- CRM, electronic signatures and routine marketing platforms;
- background screening services.

The accountable internal function, administration, access, data, integrations, retention, continuity and exit arrangements remain Sable Harbor responsibilities.

### C. Hybrid capabilities

These deliberately retain internal authority while using external specialists, infrastructure or independent providers:

- security monitoring/SIEM;
- backup and disaster recovery;
- cybersecurity incident response;
- independent penetration/security assessment;
- legal;
- tax;
- safety/environmental/occupational-health specialist services;
- IP prosecution and specialist IP counsel;
- regulatory/government-relations counsel;
- litigation;
- ESG/sustainability specialist support;
- M&A diligence;
- valuation/transaction advisory;
- open-source support contracts;
- production/cloud infrastructure during the transition toward Sable Harbor-owned compute.

### D. Inherently external or independence-required services

These remain external by their nature unless a later canonical decision establishes otherwise:

- external financial audit and SOC examinations;
- banking/payment rails;
- insurance/benefit carriers;
- telecom/carrier services, public DNS and public certificate services;
- externally originated/proprietary datasets and controlled standards;
- qualified uranium transport;
- Class I/off-network freight;
- specialist downstream refining and independent assays;
- narrow licensed/specialist services where Sable Harbor does not maintain the qualification.

## 4. Hosting-estate reconciliation

The six workload classes from PR #112 are now resolved at the architectural-direction level.

| Workload class | Reconciled direction | Remaining implementation gaps |
|---|---|---|
| Primary production | Progress toward Sable Harbor-owned hardware/network/keys/operating stack in professional colocation. Use managed cloud for transition, elasticity, burst and specialized services. | Workload sizing, rack/power/network design, provider/region, migration thresholds |
| Independent recovery | Separate geographic and operational failure domain plus separately protected immutable/offline backup capability. Sable Harbor owns architecture, keys and restoration testing. | RTO/RPO by service, capacity tier, second-site/provider choice, offline-media/process design |
| Restricted institutional / Alexandria | Sable Harbor-owned infrastructure in a separately controlled domain capable of progressively stronger network/admin/physical isolation. | Alexandria runtime/access/retention/enforcement; final site `SH-SITE-0016`; hardware/network sizing |
| Development/evaluation | Own baseline build/integration/evaluation environment; rent burst/temporary cloud capacity where information boundaries permit. | Baseline capacity, runner isolation, test-data policy, burst providers/quotas |
| Industrial/site installations | Sable Harbor-controlled local compute/network/control hardware with internal configuration, lifecycle, spares and safe degraded/offline behavior. | Per-site inventory/capacity, OT standards, spares, local recovery and connectivity design |
| Corporate/teaching facilities | Internal architecture/admin/support; purchase commodity workplace/teaching hardware and software where sensible. | Education location remains open; endpoint/AV/teaching-capacity standards |

No existing Sable Harbor building is reclassified as a data center by this decision. The site register still leaves Alexandria hosting unlocated and J2 Education geography open.

## 5. Finance reconciliation

### 5.1 Existing placeholders that must be bridged

The current conditional 2027 policy provides broad assumptions rather than a complete sourcing model:

- ESS: 48 occupied / 54 authorized;
- corporate facilities: $95,000/month;
- ESS vendor allowance: $4,500/year per occupied FTE;
- product compute costs appear in business-contract assumptions but do not establish a physical compute estate.

The new sourcing model must not simply add detailed technology/vendor/facility costs on top of those broad allowances. The implementation must identify whether each detailed cost is:

1. already represented in an existing generic allowance;
2. a replacement for part of an allowance;
3. incremental to the allowance; or
4. a reallocation between entities/services that eliminates at consolidation.

### 5.2 Required cost buckets

For each internally operated technical service, the comparison must include:

- loaded labor;
- server/storage/network hardware;
- rack/space/power/cooling charges;
- carrier connectivity;
- licenses/support subscriptions;
- security tooling;
- hardware spares and remote hands;
- maintenance/refresh reserve;
- backup/recovery capacity;
- monitoring/on-call burden;
- migration/transition cost;
- decommission/exit cost.

For purchased SaaS/services, the comparison must include:

- subscription/usage cost;
- retained administration/support labor;
- integration cost;
- identity/security/monitoring work;
- retained records/export cost;
- continuity/alternative arrangements;
- termination/exit/migration cost.

### 5.3 No false precision yet

No provider, workload, rack count, power density, storage volume, network throughput, RTO/RPO or exact service-hours model is approved. Therefore this reconciliation does not invent dollar totals. Exact cost modeling is the next quantitative tranche after workload requirements are recorded.

## 6. Workforce and coverage reconciliation

The existing ESS 48/54 forecast cannot be treated as a ready pool for every new technical function. The sourcing decision creates capability requirements, not evidence of spare personnel.

The next staffing model must map existing and required capacity across at least:

- platform/cloud/compute engineering;
- network engineering;
- storage/database engineering;
- reliability/observability;
- IAM/endpoint engineering;
- security engineering/detection/response;
- infrastructure automation;
- developer-platform engineering;
- AI/model operations where private inference is operated;
- backup/recovery administration;
- data engineering/analytics;
- facilities/colocation/vendor operations;
- local OT/site support.

For each, distinguish:

- existing canonical role/function;
- 2027 occupied forecast;
- authorized capacity;
- proposed incremental positions;
- contractor/specialist capacity;
- service hours and on-call expectations;
- relief/absence requirements;
- shared allocation across services.

Do not infer 24x7 staffing merely because a service is important. Continuous staffed coverage requires a materially larger relief factor than one nominal position; on-call coverage must be modeled separately.

## 7. Third-party management reconciliation

No new supplier identity is approved by this pass. The external-counterparty register should capture providers only when identified by source or later decision.

Every external service must have:

- an accountable internal owner;
- contracting entity;
- exact scope and operating-layer boundary;
- material subcontractors/dependencies;
- data/material custody;
- access rights;
- incident notification;
- continuity/recovery obligations;
- evidence/assurance requirements where material;
- replacement/exit path;
- pricing/commitment/renewal terms when known.

Procurement coordinates supplier mechanics; Legal owns legal advice/terms; Finance owns payment/accounting; technical/security/safety owners perform substantive reviews. Internal Audit remains independent.

## 8. Reconciliation corrections from the discussion

The following discussion paths are deliberately *not* treated as standalone canonical service decisions because they were duplicates, misframed or already controlled elsewhere:

- externally controlled standards are source acquisitions, not a choice to “build our own ISO/SOC standard”;
- translation/localization is not established as an enterprise service requirement by the current domestic operating scope;
- analytics subdomains are collapsed under the internal analytics/institutional-intelligence doctrine rather than repeatedly decided one by one;
- CI/CD, endpoint management, backup/recovery and security testing are not reopened after their governing service-family decisions;
- recruiting and institutional education are reconciled to existing People & Culture and J2 capabilities rather than treated as greenfield outsourced functions.

This correction prevents conversational enumeration from creating artificial scope or contradictory sourcing records.

## 9. Implementation sequence

### Tranche 1 — service and dependency registers

Populate the three registers proposed by PR #112:

1. service register;
2. internal team/facility/environment/capacity register;
3. external counterparty/contracted-service register.

Use existing canonical IDs where available. Do not create provider names, sites or occupied staff to make the tables look complete.

### Tranche 2 — workload/recovery requirements

For each of the six hosting classes, define:

- workload types and owners;
- criticality;
- data/information boundary;
- compute/storage/network demand range;
- service hours;
- tolerable interruption;
- RTO/RPO;
- offline/degraded-operation requirement;
- recovery dependency;
- growth/burst characteristics.

This is required before vendor/site/rack selection.

### Tranche 3 — architecture alternatives and economics

Compare at minimum:

- managed/public cloud;
- Sable Harbor-owned equipment in contracted colocation;
- hybrid cloud + colo;
- eventual owned physical facility.

The comparison should explicitly model the transition path rather than pretending these are mutually exclusive permanent end states.

### Tranche 4 — staffing/capacity bridge

Map the selected operating layers to existing ESS/business/J2/site staffing and identify only real gaps. Produce proposed authorized/occupied/contractor scenarios rather than treating all design roles as immediate hires.

### Tranche 5 — provider/site selection

Only after requirements and economics are approved should Sable Harbor select:

- primary colo/provider/region;
- recovery site/provider;
- carrier diversity;
- rack/power topology;
- managed-cloud providers/services;
- major SaaS platforms.

### Tranche 6 — finance/geography/control integration

Create the successor finance bridge, update geography only for approved sites, link assets/equipment, and map local implementations to existing Common Control Catalog controls.

## 10. Material unresolved decisions to return to the owner

The next owner decisions should be limited to matters that cannot be derived from the approved doctrine:

1. Service-level RTO/RPO and continuous/on-call coverage expectations for the critical workload classes.
2. Initial primary-production ownership point: cloud-heavy transition versus immediate first colo footprint.
3. Initial restricted/Alexandria physical-isolation target: dedicated racks, private cage/suite or later staged isolation.
4. Recovery tier: warm capacity, cold capacity or mixed by service.
5. Capital-spend appetite and time horizon for the first Sable Harbor-owned production compute estate.
6. Criteria that would justify an eventual Sable Harbor-owned data-center building.

Everything else in the present sourcing layer should be implemented from the approved direction rather than repeatedly returned for conversational approval.
