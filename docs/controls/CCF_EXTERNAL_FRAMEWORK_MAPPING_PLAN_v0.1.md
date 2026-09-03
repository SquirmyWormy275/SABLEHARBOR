# SABLE HARBOR — CCF EXTERNAL FRAMEWORK MAPPING PLAN v0.1

**Version:** 0.1.0  
**Date:** September 2, 2026  
**Status:** FOUNDATION MAPPING ARCHITECTURE — NOT AN EQUIVALENCE CROSSWALK

## Governing principle

Sable Harbor controls exist because Sable Harbor has business objectives and risks. External frameworks are mapped **after** native control design. A mapping does not mean that satisfying a Sable Harbor control automatically satisfies an external requirement, nor that an external requirement governs a particular engagement.

Exact requirement-level mappings require version-pinned source text and review. This file establishes the mapping workbench and initial domain-to-source-family coverage only.

## Source families to support

### Assurance / attestation lenses
- AICPA SOC 1 / applicable AT-C authority and relevant financial-reporting criteria;
- AICPA SOC 2 Trust Services Criteria and description criteria;
- COSO Internal Control — Integrated Framework;
- applicable AICPA quality/ethics/independence layers for the auditor are intentionally **not** treated as Sable Harbor corporate controls.

### Security / technology / governance frameworks
- NIST Cybersecurity Framework 2.0;
- NIST SP 800-53 Rev. 5 and SP 800-53A assessment procedures;
- ISO/IEC 27001:2022 and ISO/IEC 27002:2022;
- COBIT 2019;
- CIS Controls v8.1;
- CSA Cloud Controls Matrix v4.1.

### Privacy / AI / specialist frameworks
- NIST Privacy Framework (current final baseline until superseded);
- ISO/IEC 27701 current applicable edition;
- NIST AI RMF;
- ISO/IEC 42001;
- ISACA ITAF as supplemental audit execution guidance rather than corporate criteria;
- IIA GIAS for internal-audit mode if/when Sable Harbor’s internal-assurance function is canonically established.

### Program overlays when actually applicable
- FedRAMP;
- CMMC;
- PCI DSS;
- HITRUST;
- BSI C5;
- IRAP/ACSC ISM;
- CSA STAR;
- ISO certification overlays.

These overlays are activated by actual contracts, data, systems, jurisdictions, customer/program participation, or certification choices. They are not globally applicable merely because Sable Harbor wishes to benchmark against them.

## Initial domain-to-framework-family coverage

Legend: **P** primary/high relevance; **S** supporting/secondary relevance; blank = not a normal first-order mapping.

| SH domain | SOC 2 | SOC 1 / COSO | NIST CSF/800-53 | ISO 27001/27002 | COBIT | CIS | CSA CCM | Privacy | AI RMF / 42001 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GOV | P | P | S | S | P |  | S | S | P |
| ERM | P | P | P | P | P | S | P | S | P |
| ETH | P | P | S | S | S |  | S | S | S |
| POL | P | P | P | P | P | S | P | P | P |
| LEG | P | S | S | P | S |  | S | P | S |
| PPL | P | P | P | P | S | S | P | P | S |
| TRN | P | P | P | P | S | P | P | P | P |
| IAM | P | P | P | P | S | P | P | P | S |
| SEC | P | S | P | P | P | P | P | P | S |
| DAT | P | P | P | P | P | S | P | P | P |
| REC | P | P | P | P | P | S | P | P | P |
| ENG | P | P | P | P | P | P | P | S | P |
| CFG | P | P | P | P | P | P | P | S | S |
| OPS | P | P | P | P | P | P | P | S | S |
| INC | P | S | P | P | P | P | P | P | P |
| BCM | P | P | P | P | P | P | P | S | S |
| TPR | P | P | P | P | P | P | P | P | P |
| PRD | P | S | S | S | P | S | P | P | P |
| FND | P | P | P | P | P | S | P | P | P |
| AIM | P | S | S | S | P |  | S | P | P |
| RND | S |  | S | S | S |  | S | S | P |
| FLD | S | P | S | S | S |  | S |  | S |
| ENV | S | P |  | S | S |  |  |  | S |
| FIN | S | P | S | S | P |  | S | S | S |
| REV | S | P |  |  | S |  |  | P |  |
| PRC | S | P | S | S | P |  | S | P | S |
| PAY | S | P | S | S | S |  | S | P |  |
| TRY | S | P | S | S | P |  | S | S |  |
| AST | S | P | S | S | S | S | S | S |  |
| TAX |  | P |  |  | S |  |  | S |  |
| MNA | P | P | P | P | P | S | P | P | P |
| ARU | S | P | S | S | S |  | S | S | S |
| PSN | S | P | S | S | S |  | S | S | S |
| CRD | S | P | S | S | S |  | S | S | S |
| ADV | P | P | S | S | S |  | S | P | P |
| ASS | P | P | P | P | P | S | P | P | P |

## Mapping record requirements

Every exact mapping must record:

- Sable Harbor `control_id`;
- external source/framework ID and exact version;
- external criterion/control/requirement ID;
- direction (`SH-to-external` or `external-to-SH`);
- mapping type (`exact-support`, `partial-support`, `related`, `contextual`);
- coverage notes, including what is not covered;
- confidence;
- source/effective date;
- reviewer;
- explicit non-equivalence warning unless scope/text are genuinely identical;
- applicability conditions for program-specific mappings.

## Mapping quality gates

A mapping is not production-ready if:

1. the external version is missing or superseded for the intended use;
2. only metadata/marketing material was reviewed for a requirement-level claim;
3. the mapping silently turns criteria into practitioner obligations;
4. a comparative framework is presented as governing authority;
5. the mapping claims full equivalence without gap analysis;
6. the source is licensed/inaccessible and exact text has not been validated;
7. applicability depends on a future contract/program boundary that does not yet exist;
8. the mapping lacks a reviewer and rationale.

## SOC 1 and SOC 2 posture

The CCF deliberately keeps separate fields for financial-reporting relevance, customer-service relevance, security/privacy relevance, and operational/safety relevance. This permits future SOC 1 and SOC 2 scoping without cloning controls into separate “SOC” catalogs.

- A control with direct/potentially material financial-reporting relevance may become part of a SOC 1 control population when it is relevant to user entities’ ICFR and the service/system scope.
- A control may support SOC 2 criteria when the relevant system/service and Trust Services categories are scoped.
- Neither classification alone proves that a control belongs in a specific report; system boundaries, customer commitments, criteria, period, and actual implementation matter.

## Next mapping population

Exact mappings should be populated in controlled waves:

1. COSO + SOC 2 TSC at the control-objective level;
2. NIST CSF 2.0 / SP 800-53 + ISO 27001/27002 for security/data/technology controls;
3. COBIT, CIS and CSA CCM supporting mappings;
4. Privacy and AI mappings;
5. SOC 1 relevance after service/financial-reporting scope is defined;
6. program overlays only when applicability is real.

The exact crosswalk population is source-validation work, not a reason to hold up the native Sable Harbor CCF.
