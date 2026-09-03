# SABLE HARBOR — CCF POLICY AND ARTIFACT INVENTORY v0.1

**Version:** 0.1.0  
**Date:** September 2, 2026  
**Status:** REQUIRED-ARTIFACT ARCHITECTURE

This inventory identifies the corporate documents and records that naturally follow from the Sable Harbor control environment. It is not a list of audit evidence fabricated for SOC testing. These artifacts should exist because the company needs them to operate.

## Tier 0 — Constitutional / governance instruments

| Artifact | Primary owner/governance body | Scope | 2026 state |
|---|---|---|---|
| Certificate/articles and bylaws | Board / Legal | Sable Harbor parent | existing/legal source to be modeled |
| Board Governance Guidelines | Governance & Nominating Committee | parent | required |
| Board Reserved Matters Schedule | Board | parent + group | required |
| Delegation of Authority Policy & Matrix | Board / CEO / CFO | group | required |
| Audit & Compliance Committee Charter | Board | parent/group | required |
| Compensation & Human Capital Committee Charter | Board | parent/group | required |
| Governance & Nominating Committee Charter | Board | parent/group | required |
| Finance & Investment Committee Charter | Board | parent/group | required |
| Technology & Operations Committee Charter | Board | parent/group | required |
| Director Independence & Conflict Standard | Governance & Nominating | board | required |
| Subsidiary Governance Standard | Board / Legal / Finance | ARU, BS&T, Red Wash | required |
| Intercompany Services & Governance Framework | Finance / Legal | group | required |

## Tier 1 — Enterprise policies

### Governance, risk, ethics, legal
- Enterprise Risk Management Policy
- Risk Appetite & Tolerance Statement
- Code of Business Conduct and Ethics
- Conflict of Interest & Related-Party Transactions Policy
- Speak-Up / Whistleblower & Non-Retaliation Policy
- Investigation & Case Management Standard
- Anti-Bribery / Anti-Corruption Policy
- Policy Governance and Document Control Policy
- Control Governance, Exception & Risk Acceptance Standard
- Contract Review and Signature Authority Policy
- Legal Hold and Records Preservation Policy
- Regulatory/Contractual Obligation Management Policy
- Insurance Governance Standard

### People and competence
- Employee Handbook
- Recruiting, Screening & Hiring Policy
- Worker Classification and Contractor Governance Standard
- Onboarding / Transfer / Offboarding Standard
- Compensation and Promotion Governance Policy
- Performance Management Standard
- Employee Discipline and Separation Standard
- Mandatory Training Policy
- Role Qualification & Competency Standard
- Field Qualification Standard
- Travel & Expense Policy
- Remote/Hybrid Work Policy

### Technology, security, data
- Information Security Policy
- Identity & Access Management Policy
- Privileged Access Standard
- Authentication / Credential / Secrets Standard
- Acceptable Use Policy
- Endpoint Security Standard
- Network / Cloud Security Standard
- Vulnerability & Patch Management Standard
- Security Logging & Monitoring Standard
- Secure Configuration Standard
- Technology Asset Management Policy
- Secure SDLC / Engineering Change Policy
- Production Change & Release Standard
- Emergency Change Standard
- Data Governance Policy
- Data Classification & Handling Standard
- Privacy Policy / Internal Privacy Standard
- Records Retention & Disposal Schedule
- Data Quality & Provenance Standard
- Data Rights & Licensing Standard
- Backup & Recovery Policy
- Business Continuity & Disaster Recovery Policy
- Incident Response & Crisis Management Policy
- Third-Party Risk Management Policy

### Product, model, research
- Product Governance Policy
- Customer Commitment & Nonstandard Terms Standard
- Foundry Source/Mapping/Transformation Governance Standard
- Foundry Field Deployment & Validation Standard
- Model Risk / AI Governance Policy
- Model Validation and Independent Challenge Standard
- Model Use, Human Oversight & Override Standard
- Research & Experimentation Governance Policy
- Technology Transfer / Production Qualification Standard

### Finance and operations
- Accounting Policy Manual
- Financial Close and Reconciliation Policy
- Journal Entry Standard
- Revenue Recognition Policy
- Customer Billing / Credit / Collections Standard
- Procurement Policy
- Vendor Master and Payment Change Standard
- Accounts Payable and Disbursement Policy
- Payroll Administration Standard
- Equity Administration Standard
- Treasury and Cash Management Policy
- Debt and Liquidity Management Standard
- Capital Expenditure and Investment Policy
- Fixed Asset Policy
- Inventory & Custody Policy
- Tax Governance Policy
- M&A and Integration Governance Policy
- Intercompany Accounting Policy

### Physical operations and business-line overlays
- Field Operations & Stop Authority Standard
- Maintenance / Inspection Governance Standard
- Environmental & Permit Compliance Policy
- Red Wash Site Governance Manual
- Red Wash Production / Inventory / Custody Standard
- Red Wash Environmental / ARO Governance Standard
- Pale Sun Federal/Security Applicability Standard
- ARU Integration Control Standard
- BS&T Railway Operations and Custody Standard
- BS&T Maintenance / Inspection Standard
- Cradle Host-Boundary & Participation Standard
- Cradle Measurement, Custody & Settlement Standard
- Advisory Engagement Acceptance & Quality Standard

### Assurance
- Control Self-Assessment Standard
- Compliance Monitoring Standard
- Internal Assurance Charter (if maturity model is canonized)
- Internal Assurance Methodology
- Issue / Finding / Remediation Management Standard
- External Assurance and Evidence Request Protocol

## Tier 2 — Procedures, playbooks, registers, and operational records

The CCF should ultimately produce or reference structured operational artifacts including:

- board/committee annual calendars;
- board-book templates;
- board and committee minutes;
- board action register;
- director questionnaire and independence file;
- enterprise risk register;
- risk acceptance register;
- policy register;
- control register;
- local implementation register;
- control exception register;
- legal/regulatory obligation register;
- contract repository and signature-authority register;
- employee/contractor roster;
- role and competency matrix;
- training matrix and completion records;
- identity and entitlement inventory;
- privileged-access register;
- access-review populations/results;
- asset/service/SaaS/cloud inventory;
- configuration baseline register;
- vulnerability/remediation register;
- data catalog and data-owner register;
- processing/privacy inventory;
- data-retention schedule;
- Foundry source registry;
- mapping and transformation registry;
- model registry;
- model validation register;
- experiment registry;
- field qualification register;
- incident register;
- problem/RCA register;
- remediation/action register;
- BIA and recovery dependency register;
- backup/restore test records;
- vendor inventory and tiering register;
- vendor diligence/monitoring records;
- customer commitment/deviation register;
- accounting close calendar;
- reconciliation inventory;
- journal-entry populations;
- revenue contract accounting memos;
- vendor master change log;
- payment authorization logs;
- payroll change and reconciliation files;
- bank account/signatory register;
- capital request register;
- post-investment review register;
- fixed asset register;
- inventory/custody ledgers;
- tax filing calendar;
- acquisition diligence and Day-1 control plans;
- intercompany agreement/register;
- ARU/BS&T operating records;
- Red Wash production/inventory/custody/environmental records;
- Cradle measurement/custody/settlement records;
- Advisory engagement files;
- assurance plans/workpapers/reports;
- external PBC/evidence request logs.

## Artifact life-cycle rules

1. Policy issuance and control existence are distinct. A policy can govern multiple controls and a control can depend on several policies/procedures.
2. Earlier-year artifacts must reflect what Sable Harbor actually had at the time; do not backdate the 2026 mature document set.
3. Historical superseded versions remain available for longitudinal simulation and audit-period reconstruction.
4. Business-line standards can be stricter than enterprise policy where local operating or regulatory conditions require.
5. A business-line policy must not silently contradict locked corporate authority boundaries.
6. External framework citations belong in mapping/assurance layers, not in every native corporate policy.

## Drafting priority

### Wave 1 — governance/control environment
Board governance instrument, governance constitution, five committee charters, and Assumption of Risk form are materialized in `docs/governance/`. ERM policy, code of conduct, broader policy governance, detailed numeric delegation matrix, control governance/exception standard, subsidiary governance implementation, and internal-assurance charter/maturity decision remain future or OPEN as applicable.

### Wave 2 — people/security/technology
Employee handbook; onboarding/offboarding; training; IAM; information security; vulnerability; logging; SDLC/change; data governance/privacy/records; incident; BCM; third-party risk.

### Wave 3 — finance
Accounting manual; close/reconciliation; JE; revenue; procurement/AP; payroll; treasury; capital; assets/inventory; tax; intercompany.

### Wave 4 — product/model/physical overlays
Foundry; Atlas/model governance; Willow/R&D transfer; field qualification; environmental; Red Wash; ARU/BS&T; Cradle; Advisory.
