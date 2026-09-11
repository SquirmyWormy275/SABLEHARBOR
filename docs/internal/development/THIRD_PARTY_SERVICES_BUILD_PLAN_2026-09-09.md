# Third-party services — build plan for discussion

**Date:** September 9, 2026

**State:** OPEN PROPOSAL — discussion and implementation planning only

**Scope:** Enterprise-wide service sourcing, internal delivery capacity, external counterparties and management

**Authorization boundary:** The user authorized a draft PR and a reminder to address this in the next extended voice session. This record does not approve sourcing choices, suppliers, hiring, spending, facilities, contracts, deployments or a full implementation. Accepting this planning document does not make its proposed operating model canon.

## Objective

Determine which services Sable Harbor should operate itself, which it should contract out, and which require a combination. Every internally delivered service must identify the people, working environment, equipment, supporting services, funding and recovery capability required to deliver it. Every contracted service must retain an accountable internal owner.

Shared support is permissible and should be explicit. Several services may use the same team or hosting environment; their combined demand must fit that capacity. A team, server or cost cannot be counted repeatedly merely because it appears in several business records.

## Current source boundaries

- [Corporate headquarters closeout](../../canon/CORPORATE_HEADQUARTERS_CLOSEOUT_2026-09-03.md) establishes ESS, enterprise technology, independent CISO authority, business-owned product engineering, Sacramento headquarters and the separation of J2 and Internal Audit.
- [Enterprise Technology Services doctrine](../../governance/ENTERPRISE_TECHNOLOGY_SERVICES_DOCTRINE.md) permits cloud/compute, local/private models, Sable Harbor-hosted models as capability grows, and frontier models. It does not select a provider, hosting topology or data-center estate.
- [J2 establishment](../../j2/J2_ESTABLISHMENT.md) defines 237 design billets. That is not proof of occupied positions or a spare technology operations workforce.
- [Alexandria charter](../../j2/alexandria/ALEXANDRIA_CHARTER.md) and [disclosure architecture](../../j2/alexandria/INFORMATION_ACCESS_AND_DISCLOSURE.md) preserve open runtime, entitlement, retention and enforcement decisions. Institutional read authority does not grant unrestricted disclosure to users, suppliers or model providers.
- [Advisory/Atlas closeout](../../canon/ADVISORY_ATLAS_MERIDIAN_CLOSEOUT_2026-09-08.md) and [Atlas professional platform](../../advisory/ATLAS_MERIDIAN_PROFESSIONAL_PLATFORM.md) preserve dedicated product staff, professional/client separation and client-ownable derivatives. Atlas staff are not an Advisory staffing reserve; client access does not grant Alexandria Collection rights.
- [Geographic site register](../../../geospatial/registers/SITE_REGISTER.csv) and [open geographic questions](../../../geospatial/registers/OPEN_GEOGRAPHIC_QUESTIONS_v0.1.md) preserve unresolved hosting geography, J2 Education location and exact site/title questions. Existing campus and laboratory descriptions do not establish data-center capacity.
- [Business successor policy](../../../enterprise/business/source/policy.json), [assets](../../../enterprise/business/source/assets.json) and [business finance interfaces](../../business-lines/BUSINESS_FINANCE_AND_ALEXANDRIA_INTERFACES.md) distinguish conditional forecasts, authoritative books, occupied positions and source access. Current generic vendor/facility/compute allowances are not a complete sourcing cost model.
- [Common Control Catalog](../../controls/COMMON_CONTROL_CATALOG_v0.1.md) already provides service, asset, identity, continuity, third-party, contract and operating controls. Local implementation and operating evidence remain distinct from control design.
- [Maintainer rules](../../../MAINTAINERS.md) govern source authority and acceptance. A discussion, plausible design, generated chart or committed proposal does not resolve open canon.

## Three linked registers

These are proposed schemas for later implementation. No register population, provider selection or staffing approval is created here. Existing entity, business, person, site, asset and control identifiers should be reused where available. New identifiers should be stable references and must not imply approval or operation.

### 1. Service register

One record describes an outcome delivered to an internal or external customer. Application names alone are insufficient where a service also includes staffing, field work or continuing support.

| Field group | Required contents |
|---|---|
| Identity and scope | Service ID; plain-language name; brief description of the work; recipient businesses/entities; inclusions and exclusions |
| Accountability | Accountable business/service-owner role; operational decision owner; control/data owners where distinct; contract owner if external |
| Sourcing decision | Current evidenced arrangement; proposed arrangement; decision state; rationale; alternatives; source/approval reference and effective date |
| Delivery requirements | Demand and units; service hours; response/restoration requirements; capacity assumptions; critical dependencies; tolerable interruption and data loss where applicable |
| Internal support links | Team, facility, environment and equipment component IDs; required allocation/capacity; shared-service relationships |
| External dependency links | Counterparty/service IDs, contracted scope, subcontracting dependencies, replacement/exit requirements |
| Information and authority | Data classes, source rights, client/entity boundaries, permitted human/service/agent actions and disclosure limits |
| Economics | Cost-center/entity attribution; labor, operating cost, capital and renewal assumptions; allocation basis; source/version; confidence and exclusions |
| Readiness and lifecycle | Staffing/contract/dependency gaps; acceptance evidence; recovery/exit owner; review trigger; retirement or transfer requirements |

A sourcing decision may distinguish internally built software, internally operated services on contracted infrastructure, vendor-operated services, and owned physical infrastructure. A single label such as "in-house" must not conceal those differences.

### 2. Internal teams and facilities register

Use one support-component schema with explicit component types: **team, facility, hosting environment, equipment pool or operational support arrangement**. An environment can be internally operated while its physical site is vendor-owned.

| Field group | Required contents |
|---|---|
| Identity and type | Component ID; component type; existing canonical references; description and status |
| Responsibility | Owning entity/business; accountable role; service/operator role; maintenance and recovery owner |
| Team details | Required skills and qualifications; service hours; proposed authorized capacity versus evidenced occupied capacity; contractor capacity separately; coverage, absence and escalation arrangements |
| Facility details | Purpose; owned/leased/hosted/customer-site arrangement; geographic precision supported by evidence; operator; occupancy/title status; utilities, physical access and specialist maintenance dependencies |
| Environment details | Who owns and operates physical plant, hardware, operating systems and application layers; location/residency constraints; separation boundaries; backup and recovery environments |
| Equipment/capacity | Relevant assets; usable capacity and units; constraints; spares; maintenance/refresh cycle; reservations and capacity shared with other services |
| Dependencies | Linked internal component IDs and external counterparty IDs; connectivity, power, software, logistics or other required support |
| Economics and evidence | Labor/capital/operating costs and cost attribution; assumption state; evidence of capability; unresolved requirements |

Facility evidence depends on the delivery model:

| Arrangement | Sable Harbor must account for | External party supplies |
|---|---|---|
| Vendor-operated software/service | Internal service/application owner, configuration/integration, access, retained records, continuity and exit capability | Vendor application operations and underlying infrastructure within the contracted scope |
| Internally operated software on cloud infrastructure | Application/platform staff; responsibility for every retained technical layer; capacity, isolation, monitoring and recovery | The specific infrastructure and managed-service layers covered by contract |
| Sable Harbor equipment in contracted colocation | Hardware, network/platform operations, spares, remote-hands arrangements and recovery; application teams remain accountable for their services | Agreed space, power, cooling, physical security and facility services |
| Sable Harbor-owned hosting facility | Site and plant as well as technology operations: power/cooling, maintenance, physical access, specialist support, connectivity, hardware and recovery | Only the utilities, equipment, specialist work and other services actually contracted |
| Local industrial, laboratory or field service | Competent operating team, qualified equipment, working space, spares and local continuity appropriate to the work | Any explicitly contracted premises, OEM support, specialist testing, carriers or other support |

No row assumes that every service needs its own building. No row assumes that an existing building can support a new service without capacity and operating evidence.

### 3. External counterparties and contracted services register

One counterparty may supply several separately scoped services. Preserve the distinction between a legal counterparty, a brand, a particular contract and a subcontractor.

| Field group | Required contents |
|---|---|
| Identity | Counterparty ID; verified legal identity or explicitly fictional case identity; role; existing source; proposed/current/historical state |
| Relationship | Service IDs supplied; accountable internal relationship owner; contracting entity; agreement and effective-period references |
| Supplied resources | Work performed; supplied team/facility/environment where relevant; provider-operated versus Sable Harbor-operated layers; material subcontractors |
| Exposure | Operational criticality; data/access/authority; concentration and substitution constraints; geography/residency relevant to the service |
| Agreement requirements | Scope and deliverables; performance; incident notification; data and IP rights; support/access boundaries; evidence; continuity; return/deletion and termination |
| Economics | Pricing basis, commitments, pass-throughs, renewal/termination costs and applicable allocation; distinguish assumptions from executed terms |
| Lifecycle | Diligence state; approval/contract state; performance review; material changes; access removal; transition and exit evidence |

Existing hosts, customers, carriers and other named parties retain their actual roles. An external host does not become a Sable Harbor subsidiary or newly approved supplier merely by appearing in this register. No new supplier identity is selected in this proposal.

## Dependency order and staged work

| Stage | Work after the relevant scope is agreed | Completion evidence |
|---|---|---|
| 1. Establish the baseline | Inventory current service needs across corporate support, products, Advisory, J2, laboratories and physical operations. Attach accepted sources and distinguish present arrangements, modeled assumptions and open facts. | Each service has a plain description, recipient, owner role and source state; omissions and conflicts are visible. |
| 2. Set service requirements | Determine what must operate, when, at what scale, with what authority, data and recovery needs. Define which obligations remain internal even when work is contracted. | Demand and criticality support the sourcing comparison; no assumed round-the-clock promise or capacity is hidden. |
| 3. Compare sourcing alternatives | Compare buying a service, operating supported components, building differentiated capability and owning physical infrastructure. Include people, sites, dependencies, lifecycle and exit costs. | Comparable alternatives, explicit assumptions, residual dependencies and a proposed decision owner. |
| 4. Design shared support | Link proposed services to teams, environments, facilities and external dependencies. Aggregate demand before proposing new capacity. | No orphan internal service, unsupported facility claim, double-counted person or duplicated shared cost. |
| 5. Reconcile finance and corporate records | Build cost and staffing scenarios, entity/service arrangements and proposed geography changes. Preserve historical releases and distinguish proposals from current organization. | Finance, organization, assets and geography reconcile to the same proposed scope and effective dates. |
| 6. Obtain and preserve decisions | Record the specific accepted choices, unresolved questions and implementation authority. Seek separate decisions for material new structures, commitments and locations. | An accepted controlling record identifies what was actually approved; open alternatives remain open. |
| 7. Implement in bounded tranches | Create the authorized records, contracts, staffing and operating components; verify inherited and local controls; test readiness and handover. | Named owners accept services against their requirements with actual evidence; gaps remain visible. |

Do not select a data-center site before defining the workloads and recovery requirements. Do not hire against an organization chart before determining service ownership and shared capacity. Do not label a service operational because its proposal, contract template or control description exists.

## Cross-repository reconciliation

Once sourcing decisions are approved, the later implementation should reconcile:

- **Finance:** replace or bridge generic vendor, compute and facilities allowances with supported scenarios; distinguish capital from operating costs, conditional forecasts from history, and internal allocations from external revenue. Preserve immutable finance-release sources. Reconcile shared costs and intercompany services without duplicate charges.
- **People and organization:** separate authorized positions, occupied employees, borrowed allocations and contractors. Add only approved roles and teams. Preserve dedicated Atlas staffing, J2 independence, CISO authority and Internal Audit independence. Charts must follow accepted records and the user's separate chart-approval process.
- **Geography and assets:** link approved facilities and equipment to existing IDs; record ownership/operator distinctions, source precision, utilities and capacity. Keep uncertain locations uncertain. Update the geographic program only for approved scope, not to make diagrams look complete.
- **Technology and data:** assign responsibilities across provider, platform and application layers; preserve corporate/client/industrial boundaries, source entitlements, legal holds and lawful disposition. A provider relationship does not authorize source disclosure or model training.
- **Contracts and third parties:** maintain contracting-entity and internal-owner references; distinguish independent operators and hosts from acquired entities; preserve operating rights and qualification requirements.
- **Controls and publications:** use existing CCF IDs with local implementations and evidence requirements. Regenerate affected representations from their controlling sources and run applicable repository validation before acceptance.

## Acceptance criteria for the eventual sourcing model

The full model is ready for institutional acceptance only when:

1. Every service in the agreed scope has an accountable owner, explicit sourcing state and traceable source or decision.
2. Every internal service has linked delivery capacity: people, working environment, equipment, external dependencies, funding and proportionate recovery arrangements.
3. Every contracted service identifies retained internal responsibility and its actual provider scope; subcontractor and concentration dependencies are recorded where material.
4. Shared teams, facilities and costs reconcile across services. Proposed capacity is not described as occupied or operational.
5. Public cloud, colocation, owned plant and vendor-operated software are described accurately, including which party operates each layer.
6. Internal, client, restricted institutional and physical-operating boundaries survive integration. Neither model access nor platform administration creates operating or disclosure authority.
7. Financial, workforce, asset, entity and geographic records agree on scope and effective dates. Historical releases remain intact.
8. Open decisions, unbuilt capabilities and missing evidence remain explicit; documentation does not substitute for tested delivery capability.

These are eventual acceptance criteria. The current draft PR is complete as a discussion artifact without satisfying operational criteria or authorizing subsequent implementation.

## Agenda for the next extended voice session

The session should decide sourcing direction and the next bounded implementation tranche. It should not imply approval of unspecified suppliers, headcounts or facilities.

1. **Scope:** Which service families should we settle first, and what must the enterprise-wide inventory include?
2. **Internal capabilities:** Which services must Sable Harbor retain because they contain its product IP, institutional knowledge, operating judgment or customer responsibility?
3. **Commodity services:** Which services should be bought, and how much configuration, integration and oversight should remain internal?
4. **Hosting ownership:** For each workload class, should Sable Harbor buy managed infrastructure, operate its own equipment in colocation, or evaluate an owned facility? What specific need would justify owning physical plant?
5. **Shared support:** Which teams and environments can serve several businesses, and which must remain dedicated because of operating, customer or information boundaries?
6. **Service and recovery expectations:** Which services require continuous operation or rapid response, and what interruptions or data loss are tolerable?
7. **Economics and capacity:** What cost, staffing, maintenance and recovery assumptions should the first comparison include? Which current generic forecast allowances need to be replaced?
8. **Third-party management:** Which responsibilities belong to the service owner, Procurement, Legal, Security, Risk & Compliance and the operating business? Where is independent assurance required?
9. **Implementation authority:** Which specific decisions should be preserved as canon, which remain exploratory, and what exact work should the next PR implement?

Record the session's decisions in the repository, with remaining questions and the authorized next step. The reminder is a separate scheduling action; this document does not assert that a reminder has been created or that the session is scheduled.
