# Reference service description workpaper

Status: proposed design, not management's assertion or an examiner's report. The approved reference boundary is corporate shared controls supporting Reno primary colocation and Boise recovery. Selected SOC 2 categories are Security, Availability and Confidentiality; the health-data scenario is business associate/subcontractor. Type 2 readiness is the destination. No actual PHI processing, signed agreement or operating period is asserted.

| Description criterion | Draft content and required factual completion |
|---|---|
| DC1 Services | Describe the actual service, users, delivery model and material functions. Reno/Boise are deployment boundaries, not a complete product description. |
| DC2 Commitments | Record each principal customer commitment and system requirement, its approved source, category and measurable target. Populate actual contracts before stating SLA, RTO or RPO values. |
| DC3 Components | Reconcile infrastructure, software, people, procedures and data to the native inventory. Explain corporate identity/security administration, Reno processing and Boise recovery only where supported by actual design facts. |
| DC4 Incidents | Reconcile the complete incident population for the chosen period. Assess effects on commitments; describe relevant incidents accurately. An empty intake is not a no-incidents assertion. |
| DC5 Controls | Reference the proposed procedures and technical supplements. Replace proposal language with operating descriptions only after actual implementation and management review. |
| DC6 Customer dependencies | Identify actions the customer must perform in combination with our controls. Distinguish contractual duties from complementary user-entity controls necessary for the criteria. |
| DC7 Subservices | Identify actual providers, functions, locations, evidence scope and complementary duties. Establish carve-out/inclusive treatment with the examiner; no treatment is selected here. |
| DC8 Relevance | Document a factual rationale for each criterion considered irrelevant. No exclusion is preapproved. |
| DC9 Changes | Reconcile changes to services, locations, personnel, providers, code/configuration and data processes throughout the operating period. Explain material effects. |

## Proposed data-flow review

These are candidate flows to confirm, not asserted deployments. For each, record data class, origin/destination, legal role, purpose/authority, location, protocol, identity/authentication, key custodian, logging, retention, provider duties and exception route.

| Flow | Design question and evidence required |
|---|---|
| Customer intake to service | Identify permitted data and the customer/associate agreement. Validate ingress authentication, authorization and rejection of unsupported data. |
| Corporate administration to sites | Identify authoritative identities, privileged paths, local fallback and the exact applications managed at each site. |
| Reno processing/storage | Identify tenant boundaries, assets, data owners, purpose and permitted access. |
| Reno to Boise replication | Identify protected datasets, lag monitoring, encryption/key availability, network paths and recovery objectives. |
| Backup and isolated recovery | Identify backup location, retention, immutability/isolation decision, restore dependencies and destruction lifecycle. |
| Support and subcontractors | Identify support access, approval, session records, downstream processing and agreement flow-down. |
| Incident and rights-support communications | Identify upstream/downstream recipients, authority, contractual turnaround and legally relevant clocks. |
| Exit and disposal | Identify return format, active and backup copies, legal holds, verification and any residual continuing safeguards. |

## Responsibility acceptance

Corporate control owners propose the shared process and evidence. Site/service owners validate local populations, configuration and dependencies. Providers supply scoped evidence and perform their contracted activities. The upstream covered entity or associate retains its applicable duties; delegated support must be explicit. A supplier report or shared evidence hash alone cannot establish our compliance.

Before external assessment, management confirms the actual service description, contracting entity, data flows, period, commitments, systems and personnel. Independent reviewers resolve source and mapping decisions; the examiner accepts the engagement basis. Customer-facing assertions require separate authorized disclosure records.
