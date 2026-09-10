# SABLE HARBOR — THIRD-PARTY SERVICES AND INTERNAL OPERATIONS SOURCING DECISIONS

**Document ID:** `SH-CANON-TP-SVC-20260909-001`  
**Version:** 0.1.0  
**Decision date:** September 9, 2026  
**Owner:** Repository owner  
**State:** OWNER-APPROVED DECISIONS; canonical promotion pending repository acceptance  
**Related planning PR:** #112  
**Planning sources:** `docs/internal/development/THIRD_PARTY_SERVICES_ASSESSMENT_2026-09-09.md`; `docs/internal/development/THIRD_PARTY_SERVICES_BUILD_PLAN_2026-09-09.md`

## 1. Purpose and authority

This record reconciles the owner-approved sourcing and hosting decisions made during the September 9, 2026 extended planning session against the service families and workload classes in PR #112. It intentionally excludes pseudo-decisions that were discussed conversationally but do not represent a real enterprise sourcing choice, duplicate an already-settled capability, or merely restate the need to license externally controlled standards/data.

The repository remains the source of truth. These decisions become controlling only when this record is accepted into the repository's canonical layer. Until then, PR #112 remains a draft planning artifact and this file is a pending integration record.

## 2. Enterprise sourcing doctrine

### 2.1 Internal capability versus purchased components

Sable Harbor retains internally the capabilities that embody product IP, institutional knowledge, operating judgment, security authority, analytics, internal standards, and customer responsibility.

Commodity software, externally originated data, regulated or independence-required services, network/carrier services, specialist external infrastructure, and narrowly bounded expert services may be purchased.

The default rule is **internal ownership of the capability, external purchase only of components or services that are genuinely external by nature or uneconomic to recreate**.

### 2.2 Enterprise-scale interpretation

For enterprise services, “buy” does not mean outsource accountability. Where a supported platform is purchased, Sable Harbor retains the internal owner, administration, architecture, integration, policy, security, recovery, and exit responsibility appropriate to the service.

### 2.3 Progressive infrastructure ownership

Sable Harbor should progressively own more of its compute estate as scale, economics, security, resilience, or confidentiality justify it. The long-term direction is toward Sable Harbor ownership of hardware, network design, orchestration, keys, operating stack, and recovery architecture, while third parties may continue to supply building space, power, cooling, carrier connectivity, and other facilities services.

An owned Sable Harbor data-center building is an eventual option rather than an immediate requirement. The organization should design its colocation and infrastructure architecture so that it can evolve toward greater physical ownership without requiring a forced future migration of every workload.

## 3. Shared enterprise service decisions

| Service family | Approved sourcing direction | Retained internal responsibility |
|---|---|---|
| Email, calendars, meetings and collaboration | Buy managed enterprise services | Administration, identity integration, retention/export, support and governance |
| Identity and access management | Buy supported enterprise platforms | IAM engineering, lifecycle, privileged access, policy, review and recovery |
| Endpoint/device management | Buy supported enterprise platforms | Endpoint engineering, configuration, lifecycle, security integration and support |
| Endpoint security / EDR | Buy mature enterprise tooling | Detection engineering, response authority, policy, tuning and escalation remain internal |
| Backup and disaster recovery | Hybrid | Sable Harbor owns recovery architecture, policy, execution, credentials and restoration testing; external storage/facility services may be used |
| Security monitoring / SIEM | Hybrid | Platform components may be bought; alert logic, security engineering, incident command and response ownership remain internal |
| HR, payroll and benefits administration | Buy enterprise-grade platforms/processing | Existing People & Culture/payroll capability owns policy, approvals, reconciliations, employee support and provider oversight |
| Accounting, procurement and expense systems | Buy enterprise-grade platforms and build integrations | Existing Finance/Procurement functions remain the owners; no new finance organization is implied |
| Legal services | Hybrid | Internal General Counsel / OGC retains legal authority and corporate records; outside counsel is used for specialist, local, litigation, patent/trademark, regulatory or surge matters |
| External financial audit and SOC examinations | Contract independent qualified firms | Internal control ownership, evidence, remediation and independent Internal Audit remain internal |
| Production/cloud infrastructure | Hybrid with progressive internal ownership | Platform, network, storage, database, orchestration, security and reliability engineering remain internal |
| Developer platform and engineering systems | Internal capability using mature supported/open components | SDLC architecture, CI/CD design, artifact/release systems, automation, recovery and engineering standards remain internal |
| CRM, electronic signatures and routine marketing systems | Buy managed enterprise services | Commercial/functional ownership, data governance and integrations remain internal |
| Banking, payments, insurance and benefit coverage | Contract external institutions/providers | Treasury, Finance, Legal and People & Culture retain governance, reconciliations, approvals, claims and renewal ownership |
| Tax compliance and advisory | Hybrid | Internal Finance owns tax position and decisions; specialist firms may support complex filings and advice |
| Recruiting and talent acquisition | Internal capability | Existing People & Culture / enterprise talent capability owns recruiting; external search is selective and exceptional rather than the operating model |
| Background checks and employment screening | Buy external screening service | Policy, adjudication and hiring decisions remain internal |
| Training, learning and institutional education | Internal | Existing J2 / institutional Education capability is the core; external content or instructors may supplement it |
| Physical security and facilities security | Internal operating capability | External trades/equipment may support the function, but command, standards and operating authority remain internal |
| Workplace and facilities operations | Internal accountable facilities function | Cleaning, trades, catering, grounds and specialist maintenance may be contracted |
| Safety, environmental and occupational health | Hybrid with internal lead | Internal professionals own standards and operations; specialist testing, medical, waste and response services may be external |
| Cybersecurity incident response | Hybrid | Incident command, security authority and core response remain internal; specialist forensics/surge retainers may be external |
| Penetration testing / independent security assessment | Hybrid | Ongoing security testing/red teaming remains internal; independent assessments are external where independence is required |
| Vulnerability management | Internal capability | Mature third-party/open tooling may be used as components |
| Secrets and cryptographic key management | Internal | Sable Harbor retains key custody, rotation, access policy and operation using proven components rather than inventing cryptography |
| Container orchestration and platform operations | Internal | Operated by Sable Harbor using mature components; orchestration itself need not be invented from scratch |
| Infrastructure automation / configuration management | Internal | Sable Harbor owns automation, configuration state, controls and operations using mature components |
| Observability — metrics, logs, traces and alerting | Internal | Operate the stack internally and retain operational data under Sable Harbor control, while using mature components |
| Open-source software support | Hybrid, strong internal bias | Own and operate the stack; purchase commercial support only for selected mission-critical components |
| Engineering / architecture / specialist technical consulting | Internal first | External specialists are limited to narrow licensed, uniquely specialized or surge needs |
| IP services | Hybrid | IP strategy and ownership remain internal; external patent/trademark counsel may handle prosecution and specialist matters |
| Regulatory / government relations counsel | Hybrid | Strategy and relationships stay internal; external specialist counsel is used when needed |
| Litigation and dispute resolution | Hybrid | Internal Legal controls strategy and decisions; external litigation counsel handles courts and specialist matters |
| ESG / sustainability reporting and advisory | Hybrid, internal lead | Ownership and reporting remain internal; specialist outside support may be used narrowly |
| M&A due diligence | Hybrid | Sable Harbor owns process and decisions; specialist support is brought in selectively |
| Valuation and transaction advisory | Hybrid | Internal valuation capability is retained; independent external work is used when independence or unique expertise is required |
| Actuarial and specialized financial risk | Internal | Modeling, judgment and financial-risk ownership remain internal |
| Credit rating and counterparty risk | Internal | Internal models and decisions control; external ratings are only inputs |
| Enterprise risk-management systems | Internal capability | Risk governance and decisions remain internal; purchased components do not define the risk function |

## 4. Analytics and information doctrine

Analytics is an internal institutional capability. Sable Harbor may buy externally originated information, APIs, imagery, standards, feeds, or proprietary datasets, but does not outsource the conversion of information into institutional knowledge.

This applies to economic and market data, geospatial/satellite data, weather and environmental data, geological/resource data, commodity and energy data, transportation/logistics data, supply-chain/industrial intelligence, demographic/labor data, customer/market intelligence, and regulatory/policy intelligence.

The operating rule is **internal-first for data engineering, analysis, modeling and interpretation; buy external data only when it is externally originated, proprietary, legally controlled, or impractical to recreate**.

Externally published standards such as ISO/IEC or other controlled technical standards are not a build-versus-buy decision. Sable Harbor licenses or obtains them as source material where required and develops its own internal interpretation, controls, methods and implementation guidance.

## 5. Hosting and physical service estate decisions

### 5.1 Primary production

**Approved direction:** Sable Harbor should move toward owning the production compute stack while using professional third-party colocation/facilities services rather than immediately owning a data-center building.

Foundry Field, Atlas Meridian and selected shared production services should be designed for Sable Harbor-owned hardware, networking, orchestration, keys and operating stack as practical. Managed cloud remains available for transition, elasticity, specialized managed services and burst capacity; it is not the assumed permanent center of gravity.

### 5.2 Independent recovery

**Approved direction:** Recovery must not depend on the same primary failure domain.

Use a geographically and operationally separate recovery domain, preferably a separate colocation/facility failure domain as the internal estate matures, plus separately protected immutable/offline backup capability. Sable Harbor owns the recovery architecture, keys, priorities and restoration tests. Recovery capacity is sized to approved recovery objectives rather than assumed to be a full production mirror.

### 5.3 Restricted institutional / Alexandria

**Approved direction:** Sable Harbor-owned infrastructure in a separately controlled domain.

Alexandria, sensitive institutional records and selected private AI require a distinct administrative and network boundary capable of progressively stronger isolation. Dedicated racks/private suite or equivalent physical segregation should be evaluated as capacity matures. There is no default dependency on public cloud for restricted institutional operation. Recovery must preserve the same information-authority and security boundaries.

This decision does not resolve Alexandria's still-open runtime, entitlement, retention, enforcement or final geographic-site decisions.

### 5.4 Development and evaluation

**Approved direction:** Hybrid by design.

Own the baseline development, integration, build and evaluation environment. Use external cloud capacity freely for temporary experiments, burst compute and short-lived evaluation where information boundaries permit. Development environments may not silently become production environments.

### 5.5 Industrial and site installations

**Approved direction:** Internal hardware and lifecycle control.

Red Wash, ARU/BS&T, Bedford, Fort and field installations use Sable Harbor-controlled local compute/network/control hardware under internal configuration, lifecycle, spares and support standards. Vendor/OEM equipment and specialist support may be purchased where appropriate. Local systems must fail safely and continue proportionately during connectivity loss.

### 5.6 Corporate and teaching facilities

**Approved direction:** Internal ownership of the workplace/education capability with commodity technology purchased where sensible.

Corporate and teaching facilities do not require bespoke reinvention of standard employee technology. Sable Harbor retains architecture, administration, information protection, support and teaching-system ownership while purchasing commodity hardware/software/services where appropriate.

## 6. Industrial and external dependency boundaries retained from the planning source

The sourcing decisions above do not overturn the industrial limits already identified in PR #112:

- qualified external carriers remain required for uranium transport unless later authority establishes an internal qualified capability;
- Class I linehaul and off-network freight remain external dependencies where the network requires them;
- major locomotive overhaul, bulk track rehabilitation and certain major repairs remain specialist external work while ordinary maintenance stays internal;
- Kelly Gang Mining and Demotte Reclamation Services retain their external-host roles in Cradle's defined process;
- specialized downstream refining, independent assays, fabrication/calibration and other externally originated specialist services remain valid external dependencies;
- external providers do not become Sable Harbor entities merely because they appear in the service register.

## 7. Reconciliation against existing locked doctrine

These decisions align with the locked Enterprise Technology Services doctrine: Technology Services remains an internal product/engineering organization, product engineering remains with the businesses, central technology owns shared platforms and infrastructure, the CISO retains independent security authority, and resilience is an operating capability with tested restoration.

They also align with the locked ESS doctrine: Finance, People & Culture, Legal, Technology, Security, Procurement, Safety and Facilities retain their existing substantive ownership; Internal Audit remains independent; J2 remains a separate institution and is not converted into IT, Compliance, Security or Internal Audit.

No decision in this record creates a new enterprise command structure, substitutes a vendor for accountable internal ownership, or treats an existing building as a data center without demonstrated capacity.

## 8. Finance, staffing and capacity reconciliation requirements

The next implementation pass must convert these sourcing decisions into explicit cost and capacity assumptions without double counting.

For every internal service, model at least:

- authorized and occupied staffing separately;
- service hours and relief/coverage requirements;
- hardware and usable capacity;
- colocation/facility space, power and connectivity;
- software/support/licensing;
- maintenance, spares and refresh;
- monitoring and operational support;
- recovery capacity and restoration testing;
- external specialist retainers where retained;
- transition/migration cost.

For every contracted service, include internal administration, integration, security, records, continuity and exit costs in addition to the vendor invoice.

Current broad vendor, compute and facilities allowances are planning placeholders and must be bridged to the more detailed sourcing model rather than silently stacked on top of it.

## 9. Remaining open questions

The following remain open and should not be invented during reconciliation:

1. Specific vendors/providers for purchased services.
2. Exact colocation providers, regions, facilities, rack counts, power envelopes and carrier paths.
3. Exact primary-production workload/capacity requirements.
4. Exact recovery objectives and resulting recovery capacity.
5. Alexandria's final physical hosting site and still-open runtime/access/retention/enforcement details.
6. Exact hardware standards for each hosting class.
7. Exact new staffing required after shared-capacity modeling against existing authorized/occupied positions.
8. Detailed capital-versus-operating cost model and timing of the progression from managed cloud to owned colo hardware.
9. Thresholds that would justify Sable Harbor ownership of a physical data-center building.

## 10. Next bounded implementation tranche

The next implementation tranche should not reopen the sourcing principles above. It should:

1. create the service register populated from the approved sourcing table;
2. create the internal teams/facilities/capacity register with existing canonical owners and explicit gaps;
3. create the external counterparties/dependencies register without inventing suppliers;
4. build workload and recovery requirement records for the six hosting classes;
5. build a cost/capacity/staffing comparison for managed cloud, Sable Harbor-owned colocation equipment and eventual owned physical plant;
6. reconcile the result against Finance, organization, assets, geography and the Common Control Catalog;
7. preserve unresolved provider/site/headcount choices as OPEN;
8. return only material unresolved decisions to the owner.

The implementation should treat the progressively owned compute estate as a design direction, not as evidence that any hardware, racks, facilities, contracts or staff presently exist.