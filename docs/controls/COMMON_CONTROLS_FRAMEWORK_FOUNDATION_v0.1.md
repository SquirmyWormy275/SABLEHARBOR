# SABLE HARBOR — COMMON CONTROLS FRAMEWORK FOUNDATION

**Framework ID:** `SH-CCF`  
**Version:** 0.1.0  
**Canonical date:** September 2, 2026  
**Status:** FOUNDATION / PROVISIONAL  
**Purpose:** Define the enterprise control architecture from Sable Harbor's own business, risk, governance, financial, operational, technical, and regulatory reality. External frameworks are mappings and validation lenses; they do not define the company.

## 1. Design rule

Sable Harbor exists independently of NAILEX, SOC 1, SOC 2, ISO, NIST, ISACA, or any other assessment regime. The CCF therefore follows this direction:

`business reality -> objectives -> risks -> controls -> implementation -> evidence -> external-framework mappings -> audit/assessment`

It must never silently reverse into:

`audit checklist -> invented company behavior`.

NAILEX is an eventual external consumer of deliberately exported Sable Harbor evidence and benchmark packages. It is not the design authority for this framework.

## 2. Corporate posture

The working posture accepted for v0.1 is:

- federated operating model with strong corporate governance;
- credible but imperfect maturity;
- enterprise policies establish minimum requirements and reserved authority;
- operating businesses and product/program teams implement those requirements in ways appropriate to their risk, systems, customers, and field reality;
- legacy practices, acquired-company controls, technical debt, local exceptions, and compensating controls may coexist when documented;
- control maturity is longitudinal rather than magically uniform;
- control failures should arise from realistic organizational conditions rather than theatrical incompetence;
- controls must preserve the canon's separation of technical, scientific, operational, and capital authority.

## 3. CCF objectives

The CCF exists to:

1. protect Sable Harbor's ability to operate safely and reliably;
2. support trustworthy financial reporting and stewardship of assets;
3. protect customer, employee, proprietary, regulated, and operational data;
4. preserve product and model integrity;
5. ensure changes and operating interventions have accountable owners and appropriate gates;
6. maintain resilience and recoverability;
7. establish legal, contractual, ethical, and regulatory compliance mechanisms;
8. govern third parties and acquired operations without pretending they are instantly standardized;
9. preserve provenance, records, decisions, exceptions, and evidence over time;
10. create a coherent control system that can later be evaluated under multiple external criteria without being designed to pass a particular test.

## 4. Control architecture

The CCF has six layers.

### Layer 0 — Canon and enterprise objectives

Corporate purpose, operating model, business portfolio, historical constraints, authority boundaries, and accepted risk posture.

### Layer 1 — Risk universe

Enterprise risks are expressed independently of control frameworks. Each risk has causes, events, consequences, affected objectives, inherent exposure, ownership, and business applicability.

### Layer 2 — Control objectives

Control objectives state the condition Sable Harbor seeks to maintain. They are stable enough to survive implementation changes.

### Layer 3 — Common controls

Reusable enterprise controls with unique IDs, owners, frequencies/triggers, control type, preventive/detective/corrective character, evidence expectations, and applicability rules.

### Layer 4 — Implementations

A common control can have multiple implementations: corporate, Foundry/Foundry Field, Willow, Atlas Meridian, Pale Sun/Red Wash, Cradle, ARU/BS&T, Advisory, or another future unit. An implementation records local owner, system/process, procedure, evidence, deviations, inherited elements, and compensating controls.

### Layer 5 — External mappings

Mappings to COSO, AICPA Trust Services Criteria, NIST CSF/800-53, ISO/IEC 27001/27002, COBIT, CIS Controls, CSA CCM, ITAF, IIA, FedRAMP, CMMC, PCI DSS, HITRUST, C5, IRAP/ISM, ISO/IEC 42001, NIST AI RMF, and other sources are directional metadata. Mapping does not establish equivalence and does not make the external source governing authority for Sable Harbor.

## 5. Applicability and inheritance

Every control has an applicability expression. The baseline can be:

- `ENTERPRISE` — expected across Sable Harbor subject to documented scope;
- `CORPORATE_SHARED_SERVICE` — implemented centrally and consumed by units;
- `TECHNOLOGY` — applicable to systems/products meeting defined conditions;
- `FINANCIAL_REPORTING` — applicable where transactions or systems can affect financial reporting;
- `CUSTOMER_SERVICE` — applicable to customer-facing services and supporting processes;
- `AI_MODEL` — applicable to model development, validation, deployment, or use;
- `FIELD_OPERATION` — applicable where Sable Harbor owns or directs physical operating consequence;
- `REGULATED_BOUNDARY` — activated by jurisdiction, contract, data type, customer, or authorization boundary;
- `UNIT_SPECIFIC` — deliberately local and not represented as enterprise-wide.

Inheritance is explicit. A business unit never receives a control merely because it shares a parent name. It inherits only when the applicability rule is true and the implementation state is recorded.

## 6. Implementation states

Each control implementation must be one of:

- `NOT_APPLICABLE`
- `PLANNED`
- `DESIGNING`
- `IMPLEMENTED_NOT_STABILIZED`
- `OPERATING`
- `OPERATING_WITH_EXCEPTION`
- `COMPENSATING_CONTROL`
- `REMEDIATION`
- `SUSPENDED`
- `RETIRED`

The framework must preserve effective dates so a 2026 assessment does not retroactively impose a later control state on 2023 behavior.

## 7. Control design principles

1. **One control, one primary objective.** Secondary objectives may be mapped but should not turn a control into an omnibus paragraph.
2. **Business language first.** Control text describes what Sable Harbor does, not what an auditor wants to see.
3. **Evidence is an output, not the purpose.** Evidence should arise naturally from operation wherever possible.
4. **Human judgment is explicit.** Reviews, approvals, challenge, and overrides identify the accountable role and retained rationale.
5. **System behavior is not automatically control effectiveness.** Configuration, population completeness, retention, permissions, and transformations matter.
6. **Targeted and representative testing remain distinct.** The CCF stores control operation; audit sampling belongs to the evaluator.
7. **No false equivalence.** A mapping between frameworks is directional and qualified.
8. **Exceptions are first-class objects.** Waivers, risk acceptances, compensating controls, overdue remediation, and temporary operating exceptions are versioned.
9. **Acquisitions are not instantly normalized.** ARU/BS&T may retain local controls during integration with explicit convergence plans and residual risks.
10. **Production consequence requires accountable ownership.** The existing field-qualification and operating-owner boundary remains controlling for Red Wash and other physical interventions.

## 8. Risk universe structure

Every risk record should contain:

- risk ID and title;
- objective(s) threatened;
- risk statement in cause-event-impact form;
- risk category and subcategory;
- affected units, processes, systems, data, and jurisdictions;
- inherent likelihood and impact;
- velocity and persistence;
- owner and challenge function;
- existing controls;
- residual assessment;
- accepted appetite/tolerance statement;
- key risk indicators;
- linked incidents/findings/exceptions;
- effective dates and review history.

Initial enterprise risk families are: governance/strategy, financial reporting, liquidity/capital, revenue/customer, legal/contractual, people, technology, cybersecurity, privacy/data, product, AI/model, third party, resilience, physical/field operations, environmental/regulatory, acquisition/integration, fraud/ethics, records/provenance, and reputation/trust.

## 9. Framework governance

### Enterprise CCF owner

The exact executive title remains open in canon. Until the operating-model workstream resolves titles and board delegation, v0.1 uses role placeholders rather than inventing officers.

Required roles are:

- `CCF Executive Sponsor`
- `Enterprise Risk Owner`
- `Control Domain Owner`
- `Control Owner`
- `Implementation Owner`
- `Evidence Custodian`
- `Independent Challenge/Second-Line Reviewer`
- `Internal Assurance Reviewer` when established
- `Board/Committee Oversight Body` once canonized

### Change classes

- **Class 1 — editorial:** no objective, scope, owner, or operating change;
- **Class 2 — implementation:** local procedure/system/evidence change without changing the common control objective;
- **Class 3 — control design:** changes control wording, frequency, owner, applicability, or required outcome;
- **Class 4 — framework architecture:** changes domains, inheritance, risk model, governance, or control-ID semantics.

Class 3 and 4 changes require retained rationale, effective date, impact analysis, and approval under the future governance delegation.

## 10. External framework mapping posture

The external research corpus is used as a census and crosswalk source, not as Sable Harbor canon. In particular:

- SOC 1 and SOC 2 are future assurance contexts, not certifications and not the corporate design authority;
- COSO is a useful internal-control architecture and financial-reporting lens;
- TSC provides SOC 2 criteria;
- NIST, ISO, COBIT, CIS, CSA, and related sources provide control/criteria lenses;
- ITAF and IIA inform professional audit execution and internal assurance but do not define Sable Harbor's business controls;
- program-specific regimes such as FedRAMP, CMMC, PCI DSS, HITRUST, C5, IRAP, and ISO certification require overlays when actually applicable;
- vendor documentation can establish technical mechanics but cannot prove Sable Harbor's tenant configuration or control operation.

## 11. Longitudinal model

The framework is explicitly temporal. For each control and implementation, preserve:

- introduced date;
- effective date;
- superseded date;
- prior version;
- policy/procedure dependencies;
- system migrations;
- ownership changes;
- exceptions and remediation;
- incidents that changed the control;
- acquisitions or product launches that changed applicability.

This allows Sable Harbor's 2016–2026 control environment to mature naturally: founder-led practices, Crossing-era emergency controls, 2021 scale pressure, 2022 reliability lessons, 2023 formalization, 2024 Atlas reboot, and 2025–2026 expansion/regulatory complexity.

## 12. Required downstream artifacts

The CCF should eventually drive, without being defined by:

- board and committee charters;
- delegations of authority;
- enterprise risk management framework;
- code of conduct and employee handbook;
- policy hierarchy and policy library;
- security and privacy program;
- finance/accounting policies and close controls;
- revenue, procurement, payroll, treasury, asset, inventory, tax, and reporting procedures;
- HR lifecycle and training;
- vendor/third-party risk management;
- SDLC/change/release controls;
- incident, continuity, backup, and disaster recovery;
- product and customer-operations controls;
- AI/model governance;
- field/operating qualification and safety controls;
- acquisition/integration controls;
- records, retention, evidence, and legal hold;
- control testing, self-assessment, internal audit, and external-assurance interfaces.

## 13. Foundation completion criteria

CCF Foundation v0.1 is complete when the following exist together:

1. this architecture;
2. the domain taxonomy;
3. the canonical control-record schema;
4. a decision memo identifying only the genuinely world-shaping open decisions that block the next population phase.

The next phase is **CCF Population v0.1**: create the control objectives, risk-to-control relationships, and initial common-control catalog while preserving all open corporate-governance questions as explicit placeholders rather than invented canon.
