# Third-party services and internal operations — assessment for discussion

**Date:** September 9, 2026

**State:** OPEN — planning proposal for the next extended voice session

**Reviewed source revision:** `7988f4740f39afa4a3db92e9efe1e0d737840d6d`

**Companion:** [Build plan and voice-session agenda](THIRD_PARTY_SERVICES_BUILD_PLAN_2026-09-09.md)

## Purpose and authorization

The repository owner asked which services Sable Harbor should contract out and which it can build or host internally, with a corresponding team, data center, facility or other operating resources for every internal service. The follow-up instruction authorizes opening a PR and returning to this substantial build in the next extended voice session.

This PR preserves the assessment and prepares that discussion. It does not approve the proposed sourcing choices, appoint suppliers, create occupied positions, select hosting sites, change released financial models, or establish deployed capabilities. Existing accepted sources continue to control. Decisions made in the later session must be recorded and accepted into the repository before being treated as canon.

## Proposed direction

Keep product engineering, institutional intelligence, research, recovery work, mine operation and qualified ARU/BS&T services inside Sable Harbor. Purchase standard business software, external networks, specialist physical infrastructure, independent assurance and specialized or intermittent services.

Make three decisions separately for each technology service:

1. Who develops or supplies the software?
2. Who operates and supports the service?
3. Who owns and operates its physical infrastructure?

Internally developed and operated software can use contracted cloud capacity or Sable Harbor servers in contracted colocation. Multiple services may share a team or facility, provided capacity and cost are explicitly allocated. A shared platform does not erase customer, institutional, personnel, legal, industrial or development access boundaries.

## Source-backed starting point

| Finding | Source | Consequence for this build |
|---|---|---|
| Enterprise Technology Services owns seven shared technology service lines; product engineering remains with the businesses. | [Technology doctrine](../../governance/ENTERPRISE_TECHNOLOGY_SERVICES_DOCTRINE.md) | Develop the service catalog and operating resources beneath the existing organization. |
| ESS includes procurement/vendor support, facilities, Finance, P&C, Technology, Legal and other support functions; Internal Audit and J2 retain separate authority. | [ESS doctrine](../../governance/ENTERPRISE_SUPPORT_SERVICES_AND_INDEPENDENCE.md) | Use existing accountable functions; administrative coordination does not create a new operating command. |
| Alexandria runtime, detailed access, retention and enforcement remain open or deferred. | [Open issue index](../OPEN_CANON_AND_HYGIENE_ISSUE_INDEX.md); [Alexandria charter](../../j2/alexandria/ALEXANDRIA_CHARTER.md) | Architecture and documentation do not establish deployed enforcement. |
| Alexandria physical hosting, site `SH-SITE-0016`, is UNKNOWN and unlocated. | [Site register](../../../geospatial/registers/SITE_REGISTER.csv) | Select hosting through this work; existing campus names supply no data-center capacity. |
| J2 has 237 authorized design billets, with occupancy distinct. | [J2 establishment](../../j2/J2_ESTABLISHMENT.md) | These billets do not establish an additional platform, security-operations or data-center workforce. |
| The 2027 conditional scenario has 48 occupied/54 authorized ESS positions, a $95,000 monthly corporate facilities allowance and a generic $4,500 annual ESS vendor allowance per occupied FTE. | [Business policy inputs](../../../enterprise/business/source/policy.json) | Decompose and reconcile the assumptions; do not treat them as current actual staffing or vendor contracts. |
| Product contracts include monthly compute cost assumptions; the business asset input lists Fort/Cradle equipment rather than a compute estate. | [Contract inputs](../../../enterprise/business/source/contracts.json); [Asset inputs](../../../enterprise/business/source/assets.json) | Add a capacity, provider, asset, staffing and recovery cost bridge before claiming funded internal hosting. |

## Business services — proposed sourcing

The proposed allocations below preserve current authority. Sources are the [seven current dossiers](../../business-lines/README.md) and the specific operating sources linked below.

| Business or institution | Retain internally | Contract externally | Internal resources to identify and fund |
|---|---|---|---|
| Foundry Field | Product engineering, architecture, deployment acceptance, integration standards and advanced support | Hosting, selected installation/integration specialists, licensed components, independent security testing | Product/deployment teams, production capacity, development/test environments, field equipment and support coverage |
| Atlas Meridian | Product engineering, client workspaces, orchestration, evaluation, transfer tooling and product support | Hosting, approved external models and information, specialist testing | Dedicated product staff, production/evaluation capacity, tenant separation, product reliability/security and support |
| Advisory | Matter leadership, professional delivery, acceptance, independent review and outcome measurement | Bounded specialist expertise, local assistance, translation, travel and justified contractor capacity | Common bench, distinct review/value duties, Atlas workspaces and matter-specific field resources |
| J2 / Alexandria | Collection direction, analysis, institutional records, education, access decisions and domain applications | Licensed sources, specialist research access, travel, selected external instruction and infrastructure components | J2 establishment plus separately assigned technology capacity; restricted systems, records, teaching and field support |
| Willow | Experiments, prototypes, methods, qualification and transfer | Specialized fabrication, calibration, testing, machining and equipment support | Fort laboratory/workshop resources; researchers, technicians, fabrication, maintenance and facilities coverage |
| Cradle | Recovery equipment, bounded field intervention, process development, module maintenance and Bedford upgrading/blending | Host production/treatment, specialist downstream refining, transport, independent assays and exceptional repairs | Bedford labs, receiving/storage and workshops; field skids; operators, analytical staff, maintenance, shipping and EHS capacity |
| Pale Sun / Red Wash | Mine/mill operation, geology, ordinary maintenance, environmental management, preparation and shipment release | Qualified uranium transport, downstream conversion, specialist engineering, construction and independent assays | Existing 12 business-level/128 site positions and mine, mill, laboratory, storage, water/tailings and maintenance facilities; further work requires explicit capacity |
| ARU / BS&T | Qualified railway, terminal, trucking, warehouse, dispatch and routine maintenance services | Class I linehaul, off-network freight, major overhauls, bulk track rehabilitation, major truck repairs and revenue-car supply | Existing 131-person model, railway, Taylor/Rawlins estate, Wamsutter interchange, fleet and shops; assignments constrained by capacity |

### Industrial limits to preserve

- Uranium transport remains with qualified external carriers. ARU/BS&T ordinary inbound service from July 7, 2026 does not establish uranium custody authority. Alternate carrier qualification is work to complete, not existing redundancy.
- Major locomotive overhaul and bulk track work already use specialists. In-house mechanics and maintenance-of-way staff still perform ordinary work, protection, inspection and acceptance.
- Off-network transport, Class I linehaul and externally supplied revenue cars remain real dependencies. Rawlins is truck served and off BS&T.
- Cradle's Kelly Gang Mining and Demotte hosts retain their operating and treatment responsibilities. Bedford's mixed concentrate/oxide output does not establish internal individual-element refining or magnet manufacture.
- Willow's research estate is not unlimited free engineering capacity. Cradle's four named founders do not establish a complete operating roster.
- Existing industrial staffing must be reconciled before additional assignments. Red Wash's four combined security/medical/emergency billets do not establish three separately staffed 24-hour departments.

Sources: [Industrial operations and capacity](../../../industrial/source/operations.json), [Red Wash/ARU interface](../../../red_wash/logistics/ARU_BST_INTERFACE_AND_DEPENDENCY_RECORD.md), [Cradle closeout](../../canon/CRADLE_CLOSEOUT_2026-09-06.md), [Willow finance/corporate model](../../finance/WILLOW_KLEIN_FINANCE_AND_CORPORATE_MODEL_2026-09-06.md).

## Shared services — proposed sourcing

| Service | Proposed arrangement | Internal operating resources |
|---|---|---|
| Production compute, databases and storage | Rent infrastructure initially; operate applications and selected supported platform components | Platform/network/storage engineering, database responsibility, monitoring, patching, incident coverage and capacity budget |
| Private AI inference | Operate selected models when confidentiality, stable demand or total cost justify it; purchase additional frontier capability | AI/model operations, evaluation, funded GPU/storage/network capacity, licenses and hardware support |
| Developer platform | Use supported components; build pipelines and integrations | Platform engineers, isolated build/test runners, artifact storage, release and recovery ownership |
| Identity and device management | Buy supported platforms; administer internally | IAM/endpoint staff, lifecycle integrations, privileged-access administration, support and recovery |
| Backup and disaster recovery | Own recovery internally; use separately administered storage and recovery arrangements | Backup administration, protected credentials, usable replacement capacity and restoration testing |
| Security operations | Keep CISO, security engineering and incident authority; contract coverage augmentation and specialist response initially | Internal escalation/responders, detection tooling, incident command, provider management and response retainer |
| Email, calendars, meetings and collaboration | Buy managed services | Application administration, identity integration, retention/export arrangements and employee support |
| HR, payroll and benefits administration | Buy established platforms/processing | People Operations/payroll staff, reconciliations, payment approvals, employee help and provider oversight |
| Accounting, procurement and expenses | Buy established platforms; build integrations | Finance systems owner, Accounting/AP/Procurement, access administration and reconciled interfaces |
| Budgeting and operational analytics | Build business-specific models on supported tools | Analysts, data engineers, model ownership, source stewardship and analytical compute |
| CRM, electronic signatures and routine marketing systems | Buy managed services | Functional owners, administration and integrations with products/matters |
| Banking, payments, insurance and benefit coverage | Contract institutions/providers | Treasury/Finance/Legal/P&C ownership, reconciliations, claims and renewal management |
| Legal | Internal General Counsel/corporate records with external specialist or local counsel | Internal legal capacity, secure records, budget and outside-counsel management |
| External audit and SOC examinations | Contract independent qualified firms | Internal control owners, evidence and remediation; preserve independent Internal Audit |
| Recruiting and development | Internal assessment, selection, career management and institutional education; selective search/instruction contracts | Talent staff, assessors, instructors, systems and teaching facilities |
| Connectivity, public DNS, certificates and telecom | Contract providers | Network engineering, provider ownership, justified route diversity and outage alternatives |
| Workplace and facilities | Internal accountable facilities staff; contract appropriate trades, cleaning, catering and grounds services | Site ownership, work orders, inspections, spares, funding and supervision |
| Safety, environmental and occupational health | Internal professionals with specialist testing, medical, waste and response providers | Site staff, equipment, inspection/sampling schedules and explicit coverage |
| Industrial controls and instrumentation | Internal operating authority/integration; purchase engineered equipment and specialist support | Qualified site or allocated shared OT capacity, local spares, configuration records and controlled vendor access |

Self-hosting email, chat, collaboration, Git, ticketing and corporate applications remains a possible alternative. Compare full operating costs and support obligations before selecting it. Application build ownership does not require rewriting databases, identity products or other supported infrastructure components.

## Proposed hosting and physical service estate

Exact sites, providers, regions, rack counts, power, capacity and staffing remain OPEN.

| Environment | Purpose | Resources and boundaries |
|---|---|---|
| Primary production | Foundry, Atlas and selected shared services | Identified capacity, platform operators, monitoring, maintenance and infrastructure support |
| Independent recovery | Restore designated critical services | Recoverable data, sufficient replacement capacity, protected administration, connectivity and tested restoration |
| Restricted institutional | Alexandria, sensitive records and selected private AI | Domain/data engineers, access administration, controlled egress and protected storage; physical sharing requires adequate isolation |
| Development/evaluation | Product builds, integration tests and model evaluations | Separate execution/permissions, appropriate test data, tooling and support |
| Industrial/site installations | Red Wash, ARU/BS&T, Bedford, Fort and field work | Local networking/compute/control equipment, spares, support and safe behavior during connectivity loss |
| Corporate/teaching facilities | ESS, Advisory, J2 administration and Education | Employee technology, meeting/teaching equipment, records protection and workplace support; Education location remains separately open |

For colocation, Sable Harbor owns/maintains the selected servers and software while the provider supplies contracted building services. An owned data-center building additionally requires facilities engineering, physical coverage, power/cooling systems, UPS/generator maintenance, fire-system support, spares and operating funding. Compare these alternatives through a capital case rather than treating an existing campus illustration as installed infrastructure.

## Third-party relationships and management

Use the existing procurement/ESS structure. Every service has one accountable operating owner. Procurement coordinates supplier work; Legal owns legal advice/terms; Finance owns payment and accounting; technical/security/safety specialists own their respective reviews. Internal Audit remains independent. Risk review should scale with consequence and existing authority.

| Existing party or relationship | Correct treatment |
|---|---|
| Kelly Gang Mining | External Cradle host with defined stream, rights, title and settlement boundaries |
| Demotte Reclamation Services | External treatment host retaining ordinary treatment/compliance and stop/bypass rights |
| Northstar Minerals | Red Wash seller; historical transition service for up to six months from July 18, 2025 does not establish current ongoing service |
| Union Pacific | External network/interface in the synthetic industrial model; no actual real-world Sable Harbor contract asserted |
| ARU/BS&T serving Red Wash | Internal group service with capacity, commitments, legal books and eliminations |
| Qualified carriers, assay providers, refiners, repair firms and lessors | Service classes requiring precise identity, scope, term, qualification and capacity records; modeled names do not silently become selected suppliers |

Historical programs, personal activity and external hosts do not become Sable Harbor legal entities. Blackridge remains separate. Emberline and Klein remain historical. Quality Forest Communications remains biographical unless a supported transaction establishes otherwise. See [historical/external boundaries](../../business-lines/HISTORICAL_AND_EXTERNAL_BOUNDARIES.md).

Capture provider identity, relationship type, service, internal owner, site/system/lane, scope, labor/equipment, capacity, hours, rates, term, renewals, data/material custody, qualification, subcontractors, performance, incidents, alternatives and exit. Significant underlying providers belong in the dependency view even when reached through another vendor. The existing [CCF](../../controls/COMMON_CONTROL_CATALOG_v0.1.md) already supplies TPR/PRC/BCM/IAM and other relevant controls; their listed evidence does not prove actual operation.

## Financial and workforce consequence

For each internal service, model people, facilities, equipment, software, connectivity, external support, recovery, maintenance/refresh and transition costs. For each contracted service, include retained internal administration, integration and exit costs as well as the invoice.

Count shared people/assets once and allocate their costs and capacity. Preserve authorized positions, occupied positions, contractors, assignments and paid FTE separately. Replace or reconcile broad cost allowances when adding detailed costs. Internal charges eliminate at consolidation. Frozen releases retain their bytes; new decisions require a separately versioned successor with an exclusion/addition bridge where applicable.

A continuously staffed position requires 168/40 = 4.2 nominal FTE at a 40-hour week before leave, training or absence. On-call coverage is a different service commitment. Headcount recommendations must follow service hours, workload, qualified coverage and relief assumptions.

## External references used for the assessment

These sources support operating principles; their inclusion selects no supplier or certification scope.

- [AWS shared responsibility](https://aws.amazon.com/compliance/shared-responsibility-model/): cloud customers retain responsibilities that depend on the selected service.
- [NIST CSF 2.0](https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf), GV.SC: supplier criticality, due diligence, contracts, monitoring, incident/recovery coordination and termination planning.
- [NIST SP 1305](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.1305.pdf): supplier inventories, internal responsibilities and sub-tier supplier requirements.
- [AICPA SOC services](https://www.aicpa-cima.com/resources/landing/system-and-organization-controls-soc-suite-of-services): SOC examinations are CPA assurance services; internal control operation and evidence remain separate activities.

## Next discussion

Use the [build plan and agenda](THIRD_PARTY_SERVICES_BUILD_PLAN_2026-09-09.md) in the next extended voice session. Resolve service priorities, sourcing choices, staffing/coverage, hosting alternatives, industrial dependencies and cost treatment before implementation. No date/time for that session is established by this document.
