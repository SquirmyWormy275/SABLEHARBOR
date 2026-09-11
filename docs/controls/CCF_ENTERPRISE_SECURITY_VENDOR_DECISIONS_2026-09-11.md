# SABLE HARBOR — Enterprise Security & Identity Vendor Decisions

**Date:** September 11, 2026  
**Decision state:** OWNER-APPROVED VENDOR DIRECTION  
**Scope:** Enterprise identity, IGA, HR identity source, endpoint management, endpoint/security operations, network security, zero-trust/SASE, DLP, and cloud workload protection  
**Implementation state:** DESIGN / PROCUREMENT PENDING — this record does **not** assert executed contracts, licenses, deployment, operating effectiveness, or evidence populations

## Purpose

Record the enterprise vendor decisions made by the owner so that SH-CCF local implementations, third-party service records, procurement planning, architecture, recovery planning, and evidence design can proceed without repeatedly returning routine control mechanics for owner approval.

This is a vendor-selection and architectural-direction record. It is not evidence that any control is operating.

## Governing decision principles

1. **Palo Alto Networks is the preferred enterprise security vendor wherever it has a direct, credible product fit.** The preference is intended to reduce integration seams, telemetry fragmentation, policy duplication, and operational complexity.
2. The Palo Alto preference is **not** a requirement to force-fit Palo Alto into categories it does not natively cover well. Where no direct product fit exists, select a best-fit third party and integrate it into the enterprise security/control architecture.
3. **Microslop products are excluded from the candidate set by owner direction** for future third-party service selections unless the owner explicitly reverses that decision.
4. Vendor selection does not transfer accountability. Sable Harbor retains internal service ownership, configuration authority, access governance, evidence responsibility, continuity/exit responsibility, and control ownership where applicable.
5. Product/SKU details may be refined during implementation where the owner selected a vendor/ecosystem rather than a precise SKU, provided the refinement does not reopen the vendor decision or materially change architecture, risk, cost, or service commitments.

## Locked decisions

| Domain | Selected vendor / platform | Decision status | Implementation note |
|---|---|---|---|
| Enterprise IAM / identity provider | **Okta** | LOCKED | Enterprise identity and authentication platform. Local implementation must integrate lifecycle, privileged-access, service-identity, break-glass, logging, and evidence requirements. |
| Identity Governance & Administration (IGA) | **IBM Security Verify** | LOCKED | Enterprise IGA platform. Integrate governance/certification with Okta identity, SAP SuccessFactors lifecycle authority, SH-CCF evidence requirements, and Alexandria information-authority boundaries. |
| Authoritative HR lifecycle source | **SAP SuccessFactors** | LOCKED | Authoritative source for workforce lifecycle events feeding IAM joiner/mover/leaver logic. HR authority does not by itself grant application or restricted-information entitlement. |
| Unified endpoint management | **IBM MaaS360** | LOCKED | Enterprise endpoint/device management platform. Integrate device posture and compliance state into access/security decisions where appropriate. |
| EDR / endpoint security | **Palo Alto Networks — Cortex XDR** | LOCKED | Selected endpoint detection/response platform; use the Palo Alto security ecosystem for correlation and response where practical. |
| Endpoint protection platform | **Palo Alto Networks — Cortex XDR / integrated endpoint protection capability** | LOCKED | Treat as part of the Cortex endpoint stack rather than procure a duplicate standalone EPP unless a documented gap requires it. |
| Network security / NGFW | **Palo Alto Networks** | LOCKED | Standard enterprise next-generation firewall ecosystem. Exact appliance/virtual form factors follow site/workload requirements. |
| Zero Trust Network Access / SASE | **Palo Alto Networks — Prisma Access** | LOCKED | Enterprise ZTNA/SASE direction. Integrate identity, endpoint posture, application access policy, telemetry, and remote-access controls. |
| SIEM / security operations analytics | **Palo Alto Networks security-operations ecosystem** | VENDOR LOCKED; PRODUCT MAPPING PENDING | Palo Alto is the selected vendor. Architecture may select the appropriate Cortex security-operations product/SKU without reopening vendor choice; document the final product and ingestion boundaries before implementation. |
| Data loss prevention | **Palo Alto Networks — integrated Enterprise DLP capability** | LOCKED | Apply through the Palo Alto ecosystem where technically applicable; local data-classification and Alexandria disclosure authority remain Sable Harbor policy decisions, not vendor decisions. |
| Cloud workload / cloud-native protection | **Palo Alto Networks — Prisma Cloud** | LOCKED | Cloud workload/CNAPP direction. Exact modules follow actual workloads and deployment topology. |

## IGA implementation direction

IBM Security Verify is the approved enterprise IGA vendor. Routine implementation design is delegated and should not be returned to the owner control-by-control.

Implementation should integrate IBM Security Verify with:

- Okta as the enterprise identity and authentication platform;
- SAP SuccessFactors as the authoritative workforce lifecycle source;
- IBM MaaS360 for endpoint/device posture where useful and technically appropriate;
- the Palo Alto Networks security stack for telemetry, policy context, investigation and response where useful;
- Sable Harbor's native SH-CCF entitlement/evidence model;
- Alexandria's separate information-authority doctrine.

IBM Security Verify governance must not become the authority for Alexandria disclosure. It may enforce approved entitlements and certification workflows, but the underlying institutional information-authority rules remain Sable Harbor policy.

## Control-engineering delegation

The following implementation mechanics are delegated and **do not require individual owner approval** unless they create a material business, cost, legal, information-authority, or risk-acceptance decision:

- joiner/mover/leaver workflow details;
- identity and account correlation;
- IGA certification campaign mechanics and standard cadence;
- privileged-access workflow mechanics;
- break-glass implementation;
- service-account lifecycle;
- standard access-review cadence and evidence format;
- endpoint compliance policy mechanics;
- telemetry routing, normalization and retention implementation;
- firewall rule lifecycle and ordinary policy review;
- standard ZTNA policy mechanics;
- DLP enforcement implementation consistent with approved information policy;
- cloud-workload policy and evidence mechanics;
- standard alerting, ticketing, escalation and remediation workflow;
- evidence source mapping and CCF implementation IDs;
- routine API/integration configuration between approved platforms.

Return to the owner only when implementation requires one of the following:

1. a new material vendor selection;
2. a material change in service level or risk appetite;
3. an Alexandria/information-authority policy decision;
4. a material capital/headcount commitment;
5. a fundamental internal-vs-external operating-model change;
6. explicit above-tolerance risk acceptance; or
7. a voluntary external assurance/regulatory commitment that materially changes the company.

## CCF implementation consequences

The next SH-CCF implementation tranche should instantiate local records for the selected platforms and link them to existing common controls rather than creating vendor-named common controls. At minimum, the implementation layer should cover:

- identity lifecycle and authentication;
- identity governance, entitlement certification and access review;
- access authorization and periodic certification;
- privileged and service identities;
- endpoint inventory, configuration, compliance and response;
- network segmentation, policy administration and firewall governance;
- remote access / ZTNA;
- centralized security telemetry and detection/response;
- DLP and controlled disclosure enforcement;
- cloud workload posture/protection;
- third-party due diligence, contract obligations, continuity and exit;
- evidence provenance and operating-state distinctions.

External-framework mappings remain downstream of native SH-CCF control design. Vendor capabilities are implementation mechanisms, not governing authority.

## Relationship to existing third-party-service planning

This record advances the September 9 third-party-services planning work from an open vendor-neutral proposal into specific owner-approved vendor direction for the domains above. All other sourcing rules in `docs/internal/development/THIRD_PARTY_SERVICES_BUILD_PLAN_2026-09-09.md` remain in force, especially:

- internal accountability remains required for contracted services;
- proposed/selected is not the same as contracted/deployed/operating;
- shared dependencies and concentration risk must be recorded;
- data, information authority and disclosure boundaries survive vendor integration;
- finance, people, assets, geography and controls must reconcile to the same implementation state.

## Acceptance boundary

This decision record may be treated as canon for **vendor selection and preferred-vendor direction only**. It must not be cited as evidence that:

- a contract was executed;
- procurement was completed;
- licenses were purchased;
- integrations exist;
- systems are deployed;
- controls are operating effectively;
- SOC/ISO/NIST or other assurance requirements are satisfied;
- Palo Alto Networks, IBM, Okta, or SAP has been granted access to Alexandria information or other restricted data beyond separately approved entitlements.
