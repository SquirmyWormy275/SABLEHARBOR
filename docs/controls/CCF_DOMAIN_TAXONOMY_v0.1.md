# SABLE HARBOR — CCF DOMAIN TAXONOMY

**Framework:** `SH-CCF`  
**Version:** 0.1.0  
**Status:** PROVISIONAL taxonomy for population

The domains below organize Sable Harbor's control universe. They are business/risk domains, not copied framework sections. External mappings are attached later at the control level.

| ID | Domain | Core scope |
|---|---|---|
| GOV | Corporate Governance & Oversight | Board/committee oversight, charters, delegations, reserved matters, management accountability, governance records |
| ERM | Enterprise Risk Management | Risk identification, assessment, appetite/tolerance, monitoring, escalation, risk acceptance, emerging risk |
| ETH | Ethics, Conduct & Fraud Risk | Code of conduct, conflicts, speak-up, investigations, anti-fraud, anti-bribery, related parties |
| POL | Policy & Control Governance | Policy hierarchy, control ownership, exceptions, attestations, review cycles, change/version control |
| LEG | Legal, Regulatory & Contractual | Contract authority, legal review, obligations, regulatory inventory, licenses, claims, litigation, legal holds |
| PPL | People, HR & Workforce | Hiring, screening, onboarding, performance, compensation, termination, contractors, workforce records |
| TRN | Training & Competence | Required training, role competence, technical qualifications, field qualification, continuing education |
| IAM | Identity & Access Management | Joiner/mover/leaver, authentication, authorization, privileged access, service accounts, access reviews |
| SEC | Cybersecurity & Security Operations | Security governance, vulnerability management, endpoint/network/cloud security, monitoring, threat response |
| DAT | Data Governance, Privacy & Information Lifecycle | Classification, ownership, quality, privacy, retention, deletion, lineage, data rights, cross-border considerations |
| REC | Records, Provenance & Evidence Integrity | Records of authority/decision, source provenance, immutable history, evidence custody, transformation history |
| ENG | Engineering, SDLC & Change | Requirements, design, code, review, testing, CI/CD, segregation, release, emergency change, rollback |
| CFG | Technology Configuration & Asset Management | Inventory, baselines, configuration, secrets, patching, infrastructure, software/SaaS assets, lifecycle |
| OPS | IT & Service Operations | Jobs, interfaces, monitoring, capacity, batch/data pipelines, operational procedures, problem management |
| INC | Incident, Problem & Crisis Management | Detection, triage, response, communications, root cause, corrective action, lessons learned |
| BCM | Business Continuity, Backup & Disaster Recovery | BIA, continuity plans, backup, restoration, disaster recovery, exercises, dependency resilience |
| TPR | Third-Party & Supply-Chain Risk | Due diligence, contracting, security/privacy review, performance, concentration, monitoring, termination |
| PRD | Product Governance & Customer Service | Product decisions, service commitments, customer configuration, support, implementation, customer-impact change |
| FND | Foundry / Foundry Field Data Representation | Relationship registry, mappings, provenance, transformations, effective dates, deployment integrity |
| AIM | AI, Model & Decision-Support Governance | Model/data lineage, validation, challenge, human oversight, change, limitations, monitoring, output use |
| RND | Research, Experimentation & Technology Transfer | Willow/experimental boundaries, hypotheses, test plans, evidence, kill/continue/transfer decisions |
| FLD | Field Operations, Qualification & Safety | Physical operating consequence, field qualification, stop authority, operating ownership, site controls |
| ENV | Environmental, Permitting & Resource Compliance | Environmental obligations, permits, monitoring, regulated materials/resources, remediation commitments |
| FIN | Financial Governance & Close | Chart of accounts, close, reconciliations, journal entries, consolidation, estimates, financial statements |
| REV | Revenue, Contract-to-Cash & Receivables | Customer master, pricing, contracts, billing, revenue recognition inputs, collections, credits |
| PRC | Procurement, Payables & Spend | Vendor master, requisition, approval, purchase, receipt, invoice, payment, expense, purchasing authority |
| PAY | Payroll, Benefits & Equity Administration | Payroll changes, time/inputs, approvals, benefits, payroll reconciliation, equity/compensation administration |
| TRY | Treasury, Cash, Debt & Capital | Bank access, payments, cash forecasting, debt, investments, financing, capital approvals |
| AST | Fixed Assets, Inventory & Custody | Capitalization, tagging, depreciation, physical inventory, consumables, custody, impairment, disposal |
| TAX | Tax & Statutory Reporting | Tax data, filings, provision inputs, nexus, indirect taxes, statutory reports, retention |
| MNA | M&A, Integration & Intercompany | Due diligence, acquisition approval, Day-1 controls, integration, intercompany, inherited exceptions, convergence |
| ARU | ARU / BS&T Operating Controls | Distinct acquired-company and railway/utility operations, integration boundaries, custody, waybill/freight operations |
| PSN | Pale Sun / Red Wash Controls | Uranium operating business, Red Wash site, regulated boundary evolution, production and operating ownership |
| CRD | Cradle Participation & Recovery Controls | Host-site participation, recovery rights, measurement, settlement, custody, host/operator boundary |
| ADV | Advisory & Professional Services | Engagement acceptance, scope, staffing, deliverables, customer data, independence/conflict where relevant, billing |
| ASS | Assurance, Compliance & Control Monitoring | Self-assessment, control testing, compliance monitoring, issue management, internal audit, external assurance interface |

## Domain rules

- Domain ownership does not imply executive reporting lines.
- Unit-specific domains do not replace common enterprise controls; they hold controls unique to that operating reality.
- A control receives one primary domain and may carry secondary-domain tags.
- Financial-reporting relevance is a separate field, not a separate copy of every control.
- SOC 1/SOC 2 relevance is a mapping attribute, not a domain.
- Framework mappings occur after the control objective and business rationale exist.

## Expected population order

Population should proceed in dependency order rather than alphabetically:

1. GOV, ERM, ETH, POL, LEG;
2. PPL, TRN, IAM;
3. SEC, DAT, REC, CFG, ENG, OPS, INC, BCM, TPR;
4. FIN, REV, PRC, PAY, TRY, AST, TAX;
5. PRD, FND, AIM, RND;
6. FLD, ENV, PSN, CRD, ARU;
7. MNA, ADV, ASS.

This order lets governance and ownership semantics exist before implementation controls are populated, while still allowing unresolved board/executive titles to remain placeholders.
