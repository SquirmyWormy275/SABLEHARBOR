# SABLE HARBOR — CCF BUSINESS-LINE APPLICABILITY MATRIX v0.1

**Version:** 0.1.0  
**Date:** September 2, 2026  
**Status:** FOUNDATION APPLICABILITY MODEL

## Legend
- **C** = common enterprise control expected to apply substantially as designed.
- **I** = inherited common control with local implementation/owner/system evidence.
- **L** = substantial local variation or additional local control required.
- **S** = specialized domain primarily applicable to that business boundary.
- **N/A** = ordinarily not applicable absent a specific transaction or boundary change.

Boundaries: **CORP** corporate shared functions; **FF** Foundry/Foundry Field; **ATL** Atlas Meridian; **WIL** Willow/R&D; **ADV** Advisory; **PS** Pale Sun strategic business line; **RW** Red Wash operating company/site; **CRD** Cradle; **ARU** American Resource Utility; **BST** Blood, Sweat & Tears Railway.

| Domain | CORP | FF | ATL | WIL | ADV | PS | RW | CRD | ARU | BST | Key implementation note |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| GOV | C | I | I | I | I | I | L | I | L | L | Subsidiary boards/delegations and site authority require local implementation. |
| ERM | C | I | L | L | I | L | L | L | L | L | Local risks roll into enterprise risk without erasing operating context. |
| ETH | C | I | I | I | L | I | L | L | L | L | Field/regulated/vendor/customer conflict risks vary locally. |
| POL | C | I | I | I | I | I | L | I | L | L | Local standards may be stricter but remain linked to enterprise policy. |
| LEG | C | L | L | I | L | L | L | L | L | L | Contracts, permits, data rights, acquisition/regulatory obligations differ. |
| PPL | C | I | I | I | I | I | L | I | L | L | Industrial/rail/site worker categories and qualifications differ. |
| TRN | C | I | L | L | L | L | L | L | L | L | Technical, model, professional, safety, rail and field training overlays. |
| IAM | C | I | L | I | I | I | L | I | L | L | Distinct systems/OT/site and acquired-company identities require local implementations. |
| SEC | C | L | L | I | I | L | L | I | L | L | Product, model, OT, acquired and future federal boundaries differ materially. |
| DAT | C | L | L | L | L | L | L | L | L | L | Customer, model, experiment, operational and regulated data classes vary. |
| REC | C | L | L | L | L | L | L | L | L | L | Provenance/evidence is universally important but source mechanics differ. |
| ENG | C | L | L | L | I | L | L | I | L | L | Software-heavy in FF/ATL; OT/configuration change needed in physical operations. |
| CFG | C | L | L | I | I | L | L | I | L | L | Technology/OT/SaaS inventories remain boundary-specific. |
| OPS | C | L | L | I | I | L | L | I | L | L | Service operations versus industrial operations require different runbooks/evidence. |
| INC | C | L | L | L | I | L | L | L | L | L | Common severity/escalation with specialized response playbooks. |
| BCM | C | L | L | I | I | L | L | L | L | L | Recovery dependencies differ across cloud, field, rail, mine and host-site operations. |
| TPR | C | L | L | L | L | L | L | L | L | L | Vendor classes differ but enterprise tiering/contract principles apply. |
| PRD | C | S | S | I | L | L | I | I | I | I | FF/ATL are product-heavy; other units consume/adapt product governance. |
| FND | I | S | L | L | L | L | L | L | L | L | Foundry is central substrate; other units use it with local source semantics. |
| AIM | I | I | S | L | L | L | L | L | I | I | Atlas highest model-risk concentration; decision-support controls propagate where used. |
| RND | I | I | L | S | I | L | L | L | I | I | Willow owns bounded experimentation but transfer gates apply enterprise-wide. |
| FLD | N/A | I | I | L | I | L | S | L | L | S | Operating-owner/qualification logic strongest in Red Wash and BS&T. |
| ENV | N/A | N/A | N/A | L | N/A | L | S | L | L | L | Environmental obligations activate where physical/material operations exist. |
| FIN | C | I | I | I | I | I | L | L | L | L | Legal-entity, inventory, revenue and intercompany differences need local evidence. |
| REV | C | L | L | L | L | L | L | L | L | L | SaaS/services/commodity/freight/participation revenue streams differ. |
| PRC | C | I | I | I | I | I | L | L | L | L | Local purchasing authority/vendor classes while common AP principles remain. |
| PAY | C | I | I | I | I | I | L | I | L | L | Union/shift/field/rail/site payroll complexity can require local controls. |
| TRY | C | I | I | I | I | I | L | I | L | L | Subsidiary bank/debt/capital structures require local treasury implementations. |
| AST | C | I | I | I | I | L | S | L | L | S | Material physical assets/inventory dominate Red Wash and BS&T. |
| TAX | C | I | I | I | I | I | L | L | L | L | Entity/jurisdiction/resource/property tax differs locally. |
| MNA | C | I | I | I | I | I | L | I | S | L | ARU acquisition/integration is the primary current use case. |
| ARU | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | S | S | Acquired-company and railway/utility specific controls. |
| PSN | N/A | N/A | N/A | N/A | N/A | S | S | I | N/A | N/A | Pale Sun/Red Wash uranium and site-specific controls. |
| CRD | N/A | N/A | N/A | N/A | N/A | I | I | S | N/A | N/A | Host-boundary, recovery, custody and settlement controls. |
| ADV | N/A | I | I | I | S | I | N/A | I | I | I | Professional-services acceptance, quality and deliverable controls. |
| ASS | C | I | I | I | I | I | L | I | L | L | Common monitoring/assurance architecture with local populations and specialists. |

## Inheritance rules

1. `C` does not mean one centralized person performs the control; it means the control definition is common.
2. `I` requires a local implementation record with actual owner, systems, procedures, evidence sources, and review cycle.
3. `L` requires explicit local variation/additional controls and a reason for the variation.
4. `S` marks a domain where most relevant controls are purpose-built for that boundary.
5. `N/A` is never permanent merely from this matrix. Applicability can change through contract, system, data, acquisition, regulation, or operating model.
6. ARU and BS&T do not lose necessary controls merely to converge with Sable Harbor common controls.
7. Red Wash physical operating authority remains distinct from Pale Sun analytical/strategic authority.
8. Cradle host/operator boundaries must be evaluated arrangement by arrangement.
9. Any future federal boundary for Pale Sun is separately scoped; FedRAMP or equivalent controls are not inherited solely from the business-line name.
