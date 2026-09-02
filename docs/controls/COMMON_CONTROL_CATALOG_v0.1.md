# SABLE HARBOR — COMMON CONTROL CATALOG v0.1

**Framework:** `SH-CCF`  
**Version:** 0.1.0  
**Date:** September 2, 2026  
**Status:** INITIAL COMMON-CONTROL POPULATION

This catalog defines Sable Harbor controls in business language. Local implementation records, exact systems, named control owners, evidence populations, thresholds, and external-framework mappings are separate layers.

## GOV — Corporate Governance & Oversight
| ID | Control | Objective | Default owner role | Trigger/frequency | Natural evidence |
|---|---|---|---|---|---|
| SH-GOV-001 | Board governance guidelines and committee charters are maintained and approved. | GOV-001 | Corporate Secretary / Governance Lead | annual + event | approved charters, board resolutions, version history |
| SH-GOV-002 | Board and committee calendars require regular meetings and defined information packages. | GOV-001/003 | Corporate Secretary | annual calendar + each meeting | calendars, agendas, board books, minutes |
| SH-GOV-003 | Reserved matters and delegated authority are documented and reviewed. | GOV-002 | Board / CEO / Finance leadership | annual + transaction/change | delegation matrix, reserved-matters schedule, approvals |
| SH-GOV-004 | Director independence, conflicts, recusal, and committee eligibility are assessed. | GOV-001/004 | Governance & Nominating Committee | annual + event | questionnaires, determinations, recusals, minutes |
| SH-GOV-005 | Material board actions and follow-up commitments are recorded and tracked. | GOV-003/004 | Corporate Secretary | each meeting | minutes, action register, closure records |

## ERM — Enterprise Risk Management
| SH-ERM-001 | Enterprise risk register is refreshed from business, product, technology, finance, people, legal, and operating inputs. | ERM-001/004 | Enterprise Risk Lead | quarterly + emerging risk | risk register, workshops, source inputs |
| SH-ERM-002 | Risk appetite and tolerance statements are approved and translated into escalation rules. | ERM-002 | Board / Executive leadership | annual + major change | appetite statement, thresholds, approvals |
| SH-ERM-003 | Material residual risks and accepted risks are reviewed at the appropriate governance level. | ERM-002/003 | Risk owners / Audit & Compliance Committee | quarterly + threshold breach | risk acceptances, reports, committee minutes |
| SH-ERM-004 | New ventures, acquisitions, major products, and physical operations receive cross-functional risk assessment. | ERM-004 | Enterprise Risk Lead + accountable sponsor | stage gate | risk assessment, approvals, conditions |

## ETH — Ethics, Conduct & Fraud Risk
| SH-ETH-001 | Code of conduct and core ethics expectations are approved, distributed, and attested to. | ETH-001 | Legal/People leadership | annual + onboarding | code, attestations, distribution logs |
| SH-ETH-002 | Conflict-of-interest disclosures are collected, reviewed, resolved, and retained. | ETH-002 | Legal/Compliance | annual + event | disclosures, decisions, recusals |
| SH-ETH-003 | Speak-up reports are independently triaged and investigated with anti-retaliation protections. | ETH-002 | Compliance / Audit & Compliance Committee | event-driven | hotline cases, investigation files, closure approvals |
| SH-ETH-004 | Fraud and related-party risk is explicitly considered in high-risk financial and contracting processes. | ETH-003 | Finance/Compliance | annual + transaction | fraud-risk assessment, related-party register, approvals |

## POL — Policy & Control Governance
| SH-POL-001 | Enterprise policies and standards use a controlled hierarchy, owner, approver, effective date, and review date. | POL-001 | Policy Governance Lead | continuous / annual review | policy register, approvals, versions |
| SH-POL-002 | Common controls maintain stable IDs, business rationale, ownership, applicability, evidence expectation, and change history. | POL-001/003 | Control Governance Lead | continuous | CCF records, change log |
| SH-POL-003 | Exceptions and waivers require documented scope, risk, approver, compensating measures, and expiration/closure. | POL-002 | Control owner + risk approver | event-driven | exception register, approvals, expiry reports |
| SH-POL-004 | Local control variations are documented rather than silently diverging from enterprise controls. | POL-003 | Local owner + Control Governance | event + periodic review | implementation records, variance rationale |

## LEG — Legal, Regulatory & Contractual
| SH-LEG-001 | Legal/regulatory/contractual obligation inventory is maintained by business boundary. | LEG-001 | Legal/Compliance | quarterly + event | obligation register, owner assignments |
| SH-LEG-002 | Contracts receive risk-based legal, security, privacy, finance, insurance, data-rights, and authority review before signature. | LEG-002 | Legal / Contract owner | each material contract | redlines, approvals, signed contract |
| SH-LEG-003 | Signature authority is restricted to delegated signatories and verified before execution. | LEG-002 | Legal / Finance | transaction | signature matrix, executed agreements |
| SH-LEG-004 | Legal holds and material disputes are issued, preserved, tracked, and released under legal authority. | LEG-003 | Legal | event-driven | hold notices, custodian lists, release records |

## PPL — People, HR & Workforce
| SH-PPL-001 | New hires and contractors require approved requisition, role, manager, compensation/rate, and employment/engagement terms. | PPL-001/002 | People Operations | each hire | requisition, offer/contract, approvals |
| SH-PPL-002 | Background or qualification screening is performed where role, law, customer, field, or trust requirements warrant. | PPL-002 | People / Security | pre-start + recheck where required | screening results, exceptions |
| SH-PPL-003 | Role, manager, location, employment status, and termination changes are recorded timely and distributed to dependent processes. | PPL-001 | People Operations | event-driven | HRIS changes, workflow logs |
| SH-PPL-004 | Sensitive compensation and executive personnel actions receive independent approval. | PPL-003 | Compensation/Human Capital governance | event | approvals, compensation records |
| SH-PPL-005 | Critical-role succession and capacity risks are periodically reviewed. | PPL-004 | Executive/People leadership | semiannual | succession plans, workforce-risk review |

## TRN — Training & Competence
| SH-TRN-001 | Mandatory enterprise training matrix defines required courses by worker class and role. | TRN-001 | People/Compliance | annual + onboarding | training matrix, assignments |
| SH-TRN-002 | Completion and overdue mandatory training are monitored and escalated. | TRN-001 | People/Compliance | monthly | completion reports, escalations |
| SH-TRN-003 | Critical roles maintain documented qualifications, licenses, certifications, or competency evidence. | TRN-002 | Functional owner | event + periodic | competency records, license register |
| SH-TRN-004 | Field qualification is documented before experimental/technical work receives operating authorization. | TRN-003 | Field qualification authority / operating owner | each transfer | qualification package, acceptance decision |

## IAM — Identity & Access Management
| SH-IAM-001 | Identity creation originates from an authoritative personnel/service-account request and unique identifier. | IAM-001 | IAM / IT | event | request, identity record, provisioning log |
| SH-IAM-002 | Access provisioning requires approved role/business need and least-privilege assignment. | IAM-001/002 | Manager + system owner | event | access request, approval, entitlement record |
| SH-IAM-003 | Movers trigger review and adjustment of existing access, not only addition of new access. | IAM-002 | Manager / IAM | event | mover workflow, before/after access |
| SH-IAM-004 | Terminations and contract expirations trigger timely disablement and credential/access revocation. | IAM-002 | People / IAM | event | termination feed, disablement logs |
| SH-IAM-005 | Privileged and break-glass access is separately authorized, logged, monitored, and periodically reviewed. | IAM-003 | Security / system owner | continuous + quarterly | privileged groups, logs, reviews |
| SH-IAM-006 | Service accounts and non-human identities have named ownership, purpose, credential governance, and lifecycle review. | IAM-003 | System owner | quarterly + change | inventory, ownership attestations, secrets rotation |
| SH-IAM-007 | Periodic user-access reviews identify stale, excessive, conflicting, or inappropriate access. | IAM-004 | System/data owner | quarterly/semiannual based on risk | review population, decisions, remediation |

## SEC — Cybersecurity & Security Operations
| SH-SEC-001 | Security architecture and minimum security requirements are defined for enterprise and product environments. | SEC-001 | Security leadership | annual + material architecture change | standards, architecture reviews |
| SH-SEC-002 | Security logging and detection coverage is defined for material systems and monitored for collection gaps. | SEC-003/004 | Security Operations | continuous | log-source inventory, alerts, gap reports |
| SH-SEC-003 | Vulnerabilities are identified from scanning, testing, advisories, incidents, and engineering input and tracked to remediation/acceptance. | SEC-002 | Security/Engineering | continuous | scanner results, tickets, exceptions |
| SH-SEC-004 | Risk-based remediation targets govern critical/high vulnerabilities and overdue items escalate. | SEC-002 | Security + system owner | continuous/monthly | aging report, escalations, risk acceptances |
| SH-SEC-005 | Endpoint, network, cloud, and SaaS security baselines are enforced or deviations governed. | SEC-003 | Security/IT | continuous | baseline reports, deviations |
| SH-SEC-006 | Material threats/security events enter incident response with preserved evidence and accountable command. | SEC-004 | Security Operations | event | incident records, evidence links |

## DAT — Data Governance, Privacy & Information Lifecycle
| SH-DAT-001 | Data domains and material datasets identify accountable owners/stewards and classification. | DAT-001 | Data Governance | continuous | data catalog, owner register |
| SH-DAT-002 | Privacy and restricted-data processing is inventoried and tied to purpose, authority, sharing, retention, and safeguards. | DAT-002 | Privacy/Legal/Data | continuous | processing inventory, assessments |
| SH-DAT-003 | Data retention and deletion rules are defined by data class and obligation. | DAT-002 | Legal/Data Governance | annual + change | retention schedule, deletion jobs |
| SH-DAT-004 | Material data quality rules and known limitations are documented where decisions or reporting depend on the data. | DAT-003 | Data owner | continuous | quality checks, issue logs, limitations |
| SH-DAT-005 | Data licensing and rights are reviewed before model training, external sharing, customer reuse, or new product use. | DAT-004 | Legal/Data/Product | event | license review, approvals |

## REC — Records, Provenance & Evidence Integrity
| SH-REC-001 | Material control, approval, transaction, incident, and decision records identify actor, time, scope, and outcome. | REC-001 | Process owner | continuous | system records, approvals, logs |
| SH-REC-002 | Evidence extracts used for assurance preserve source, query/report, parameters, period, timezone, transformations, and completeness limitations. | REC-002 | Evidence preparer / Control owner | each extraction | extraction manifest, source artifact |
| SH-REC-003 | Material transformed evidence keeps source and transformed artifacts separately identifiable and integrity-checkable. | REC-002 | Evidence custodian | each transformation | hashes/manifests, transformation log |
| SH-REC-004 | Retention/disposal execution respects legal holds and documented exceptions. | REC-003 | Records/Legal | scheduled + event | disposal logs, hold overrides |

## ENG — Engineering, SDLC & Change
| SH-ENG-001 | Material engineering work begins from traceable issue/requirement/change intent and accountable owner. | ENG-001 | Engineering/Product | each change | ticket, requirement, design |
| SH-ENG-002 | Code/configuration/model changes receive peer review before protected production merge/deployment, subject to documented emergency process. | ENG-002/004 | Engineering | each change | PR review, approvals |
| SH-ENG-003 | Automated/manual tests appropriate to change risk must pass or exceptions be approved before release. | ENG-002 | Engineering/QA | each release | test results, exceptions |
| SH-ENG-004 | Production deployment is attributable to approved artifacts and controlled pipeline/release authority. | ENG-002/004 | Release/Platform Engineering | each deployment | build provenance, deploy logs |
| SH-ENG-005 | Emergency changes are logged, limited, approved by emergency authority, and retrospectively reviewed. | ENG-003 | Engineering/Operations | event | emergency ticket, review |
| SH-ENG-006 | Rollback/recovery paths are defined for material production changes where technically feasible. | ENG-002 | Engineering | each material change | release plan, rollback evidence |

## CFG — Technology Configuration & Asset Management
| SH-CFG-001 | Material hardware, software, SaaS, cloud resources, environments, and owners are inventoried. | CFG-001 | IT/Platform | continuous | asset/service inventory |
| SH-CFG-002 | Baseline configurations are defined for critical technologies and material drift is detected. | CFG-002 | IT/Security/Platform | continuous | baseline-as-code, drift reports |
| SH-CFG-003 | Patch and lifecycle status is monitored, with unsupported/end-of-life systems governed as exceptions or remediated. | CFG-003 | IT/Platform | monthly | patch reports, lifecycle register |
| SH-CFG-004 | Secrets/certificates/keys have ownership, approved storage, rotation/expiry monitoring, and revocation processes. | CFG-003 | Security/Platform | continuous | secret inventory, expiry alerts |

## OPS — IT & Service Operations
| SH-OPS-001 | Critical services, integrations, batch jobs, and pipelines have health monitoring and accountable on-call/owner response. | OPS-001 | Service owner | continuous | monitors, alerts, runbooks |
| SH-OPS-002 | Availability, latency, error, capacity, queue/backlog, and dependency indicators are reviewed against operational needs. | OPS-002 | Service owner | continuous/weekly | dashboards, reviews |
| SH-OPS-003 | Repeated incidents and recurring failures enter problem-management analysis and corrective action. | OPS-003 | Operations/Engineering | threshold/event | problem records, RCA |
| SH-OPS-004 | Manual operational procedures for critical recurring activities are documented and reviewed after material change. | OPS-001 | Service/process owner | annual + change | runbooks, version history |

## INC — Incident, Problem & Crisis Management
| SH-INC-001 | Incident severity, commander/owner, escalation, communication, and response expectations are defined. | INC-001 | Incident Management | annual + each incident | incident standard, case record |
| SH-INC-002 | Material incidents preserve chronology, impact, decisions, evidence, communications, and affected boundaries. | INC-002 | Incident commander | each incident | timeline, artifacts, communications |
| SH-INC-003 | Root cause/contributing-factor review is required for defined incident classes. | INC-003 | Incident/Problem Management | post-incident | RCA, action plan |
| SH-INC-004 | Corrective actions have owners, due dates, risk severity, validation, and escalation for overdue status. | INC-003 | Action owners / governance | continuous | remediation tracker |
| SH-INC-005 | Physical-operation incidents assign immediate consequence to the operating owner while technical/capital investigations proceed separately. | INC-004 | Operating owner | event | incident decision log, handoffs |

## BCM — Business Continuity, Backup & Disaster Recovery
| SH-BCM-001 | Business impact analyses identify critical processes, dependencies, recovery priorities, and tolerable interruption. | BCM-001 | BCM/Business owners | annual + material change | BIA, dependency map |
| SH-BCM-002 | Critical systems/data have defined backup/recovery requirements and monitored backup execution. | BCM-002 | IT/Service owner | continuous | backup jobs, failures |
| SH-BCM-003 | Restore tests demonstrate recoverability of critical data/systems at defined cadence. | BCM-002 | IT/Service owner | quarterly/annual risk-based | restore test evidence |
| SH-BCM-004 | Continuity/DR exercises are performed and findings tracked to closure. | BCM-003 | BCM | annual + major changes | exercise reports, remediation |

## TPR — Third-Party & Supply-Chain Risk
| SH-TPR-001 | New third parties receive inherent-risk tiering based on service criticality, data, access, operational, legal, financial, and concentration exposure. | TPR-001 | Procurement/TPRM | onboarding | risk questionnaire, tier |
| SH-TPR-002 | Due diligence depth is proportional to vendor tier and identified risk. | TPR-001 | TPRM / SMEs | onboarding/renewal | diligence evidence, review decisions |
| SH-TPR-003 | Contracts include risk-appropriate service, security, privacy, incident, evidence, data, continuity, and termination terms. | TPR-002 | Legal/Procurement | contract | contract clauses, exceptions |
| SH-TPR-004 | Critical vendors are periodically monitored for performance, risk change, incidents, financial health, and concentration. | TPR-003 | Vendor owner/TPRM | quarterly/annual | monitoring reports, reviews |
| SH-TPR-005 | Third-party offboarding revokes access, addresses data return/destruction, transitions service, and closes financial obligations. | TPR-004 | Vendor owner/IT/Legal | termination | offboarding checklist, confirmations |

## PRD — Product Governance & Customer Service
| SH-PRD-001 | Product decisions with material security, data, AI, operational, contractual, or financial effect receive cross-functional review. | PRD-001/003 | Product leadership | stage gate | decision record, reviews |
| SH-PRD-002 | Customer commitments and nonstandard product/service terms are documented and assigned accountable delivery ownership. | PRD-001 | Sales/Product/Legal | contract/change | commitment register, approvals |
| SH-PRD-003 | Material customer-impacting changes receive impact analysis and communication appropriate to commitments. | PRD-002 | Product/Customer Operations | change | impact assessment, notices |
| SH-PRD-004 | Support incidents and recurring customer issues are linked to product/engineering corrective action where warranted. | PRD-002 | Customer Operations | threshold | support analytics, linked problems |

## FND — Foundry / Foundry Field Data Representation
| SH-FND-001 | Source-system and dataset onboarding captures source owner, authority, semantics, timezone/effective-date logic, and known limitations. | FND-001/002 | Foundry implementation/data owner | source onboarding | source registry, mapping package |
| SH-FND-002 | Field/semantic mappings preserve customer/local definitions and explicitly identify unresolved ambiguity. | FND-001/004 | Data mapping owner | mapping creation/change | mapping records, review notes |
| SH-FND-003 | Transformation logic is versioned, reviewed, tested, and linked to source/target definitions. | FND-003 | Data Engineering | each change | code/config, tests, lineage |
| SH-FND-004 | Reconciliations or validation checks confirm material integrations behave as intended before/after deployment. | FND-002/003 | Implementation/Data owner | deployment/change | reconciliation evidence |
| SH-FND-005 | Conflicting source claims remain represented with source/authority context instead of being silently collapsed. | FND-004 | Foundry/Data Governance | continuous | relationship registry, conflict records |

## AIM — AI, Model & Decision-Support Governance
| SH-AIM-001 | Material models and analytical methods are registered with purpose, owner, version, data lineage, use boundaries, and validation state. | AIM-001 | Model Governance/Product | onboarding/change | model registry, model card |
| SH-AIM-002 | Independent validation/challenge is performed before high-consequence model use and after material change. | AIM-002 | Independent model challenge | pre-use/change | validation report, issues |
| SH-AIM-003 | Training/evaluation datasets, third-party models, prompts/system instructions, and material model dependencies are versioned and rights/security reviewed. | AIM-001/003 | Model owner/Data/Legal/Security | change | lineage, approvals, evaluations |
| SH-AIM-004 | Model performance, drift, failure patterns, overrides, and material user feedback are monitored after deployment. | AIM-003 | Model owner | continuous/periodic | monitoring reports, override logs |
| SH-AIM-005 | Human decision authority and prohibited autonomous uses are explicit for material decision-support workflows. | AIM-004 | Product/Business owner | design + review | use policy, workflow controls |

## RND — Research, Experimentation & Technology Transfer
| SH-RND-001 | Material experiments have documented question, hypothesis, scope, owner, methods, data, risks, and success/kill criteria. | RND-001 | Research lead | each experiment | experiment charter |
| SH-RND-002 | Results, negative outcomes, deviations, and uncertainty are retained and reviewed before continuation/transfer decisions. | RND-002 | Research lead/challenge role | each milestone | lab records, decision memo |
| SH-RND-003 | Production transfer requires field qualification, accountable operating ownership, technical/change review, and explicit remaining-risk acceptance. | RND-003 | Qualification authority + operating owner | each transfer | transfer package, approvals |

## FLD — Field Operations, Qualification & Safety
| SH-FLD-001 | Every material physical operation has an accountable operating owner and defined stop/constrain authority. | FLD-001 | Operating leadership | continuous | role assignment, procedures |
| SH-FLD-002 | Field qualification is required before material experimental/technical/model-driven change enters operations. | FLD-002 | Field qualification authority | each material change | qualification records |
| SH-FLD-003 | Safety-critical inspections, maintenance, abnormal-condition response, and operating records are performed and retained. | FLD-003 | Site/operations | scheduled/event | inspection/maintenance logs |
| SH-FLD-004 | Operating deviations and temporary workarounds are time-bounded, risk-reviewed, and escalated according to consequence. | FLD-001/003 | Operating owner | event | deviation register, approvals |

## ENV — Environmental, Permitting & Resource Compliance
| SH-ENV-001 | Applicable permits, environmental obligations, limits, monitoring, reporting, and responsible owners are maintained by site/activity. | ENV-001 | Environmental/Legal | continuous | permit register, obligations |
| SH-ENV-002 | Required monitoring/sampling is scheduled, performed, quality-checked, and submitted/reported when required. | ENV-002 | Environmental operations | scheduled | sampling records, reports |
| SH-ENV-003 | Environmental excursions, permit deviations, notices, and corrective actions are escalated and tracked. | ENV-003 | Environmental/Operating owner | event | incident/deviation records |

## FIN — Financial Governance & Close
| SH-FIN-001 | Chart of accounts, accounting policies, close calendar, and ownership are controlled and reviewed. | FIN-001 | Controller | annual + change | COA, policy, close calendar |
| SH-FIN-002 | Material balance-sheet and key P&L accounts are reconciled with preparer/reviewer accountability. | FIN-002 | Accounting | monthly/quarterly | reconciliations, reviewer signoff |
| SH-FIN-003 | Manual journal entries require support, preparer identity, appropriate approval, and post-close monitoring for unusual activity. | FIN-003 | Accounting/Controller | each JE + periodic analytics | JE package, approvals |
| SH-FIN-004 | Estimates and judgments have documented assumptions, source data, review, and sensitivity/materiality consideration. | FIN-003 | Accounting/Finance | close/estimate event | estimate memo, approvals |
| SH-FIN-005 | Consolidation and intercompany elimination logic is reviewed and reconciled across legal entities. | FIN-003 | Consolidation owner | monthly/quarterly | consolidation workbook/system records |
| SH-FIN-006 | Financial statements and management reports receive analytical review for completeness, consistency, material variance, and unusual activity. | FIN-004 | CFO/Controller | monthly/quarterly | review package, comments |

## REV — Revenue, Contract-to-Cash & Receivables
| SH-REV-001 | Customer master and billing attributes are created/changed from authorized contractual/business information. | REV-001 | Revenue Operations | event | customer master requests |
| SH-REV-002 | Nonstandard pricing, discounts, credits, and commercial terms require delegated approval. | REV-001 | Sales/Finance | transaction | deal approvals |
| SH-REV-003 | Billing is generated from approved contracts, milestones, usage, acceptance, or other valid source events and reconciled to subledger/GL. | REV-001/002 | Billing/Revenue Accounting | billing cycle | invoices, source data, reconciliation |
| SH-REV-004 | Revenue recognition judgments and contract modifications are reviewed under accounting policy. | REV-002 | Revenue Accounting | contract/close | revenue memo, review |
| SH-REV-005 | Aged receivables, collections, credit memos, write-offs, and refunds are reviewed and authorized. | REV-003 | Finance | monthly/event | aging, approvals |

## PRC — Procurement, Payables & Spend
| SH-PRC-001 | Vendor master creation/change requires independent validation of identity, payment instructions, tax data, and conflict/due-diligence prerequisites. | PRC-001 | Procurement/AP | event | vendor request, validation |
| SH-PRC-002 | Purchase commitments require approval under delegated authority before obligation, except governed emergency paths. | PRC-002 | Requester/approver | transaction | requisition, PO, approval |
| SH-PRC-003 | Invoice payment requires evidence of valid vendor, obligation, receipt/service, coding, approval, and duplicate checks. | PRC-003 | AP | transaction | invoice package, match results |
| SH-PRC-004 | Changes to vendor bank details receive out-of-band verification and restricted approval. | PRC-003 | AP/Treasury | event | verification log |
| SH-PRC-005 | Non-PO, emergency, corporate-card, and expense spend is monitored for policy exceptions and repeat bypass patterns. | PRC-004 | Procurement/Finance | monthly | exception analytics |

## PAY — Payroll, Benefits & Equity Administration
| SH-PAY-001 | Payroll master changes originate from approved HR/compensation actions and are independently reviewed for sensitive fields. | PAY-001/003 | Payroll/People | event | change report, approval |
| SH-PAY-002 | Payroll inputs and output are reconciled to authorized workforce, compensation, time, benefits, and prior-period expectations. | PAY-002 | Payroll/Accounting | each payroll | payroll reconciliation |
| SH-PAY-003 | Payroll bank/payment file release requires restricted access and dual control appropriate to risk. | PAY-003 | Payroll/Treasury | each payroll | release approvals, bank records |
| SH-PAY-004 | Equity grants, vesting, exercises, cancellations, and executive compensation are reconciled to approved board/committee actions and plan terms. | PAY-001/003 | Equity admin/Legal/Finance | event + quarterly | grant records, approvals, cap table |

## TRY — Treasury, Cash, Debt & Capital
| SH-TRY-001 | Bank accounts and treasury systems maintain approved signers/users and periodic access review. | TRY-001 | Treasury | quarterly | bank signer list, access review |
| SH-TRY-002 | Material cash disbursements/transfers require delegated approval and independent verification appropriate to amount/risk. | TRY-002 | Treasury/Finance | transaction | payment approvals, confirmation |
| SH-TRY-003 | Bank/cash balances are reconciled to accounting records and unexplained differences investigated. | TRY-002 | Accounting/Treasury | monthly | bank reconciliations |
| SH-TRY-004 | Liquidity forecast, debt/covenant compliance, maturities, and concentration are reviewed and escalated. | TRY-003 | CFO/Treasury | monthly/quarterly | treasury report, covenant calc |
| SH-TRY-005 | Capital requests use a common business-case package and approval path based on amount and risk. | TRY-004 | Business sponsor/Finance | each request | capital memo, approvals |
| SH-TRY-006 | Material approved investments receive post-investment review against assumptions and outcomes. | TRY-004 | Finance & Investment governance | milestone/annual | post-investment review |

## AST — Fixed Assets, Inventory & Custody
| SH-AST-001 | Capital assets are recorded with class, cost basis, location/custodian, useful life, and source transaction. | AST-001/003 | Fixed Assets | acquisition | asset register |
| SH-AST-002 | Material inventory/materials are recorded with quantity, location/custody, movement, and valuation basis appropriate to operation. | AST-001 | Operations/Accounting | continuous | inventory ledger, movement records |
| SH-AST-003 | Physical counts/inspections are performed at defined cadence and differences reconciled. | AST-002 | Operations/Accounting | periodic | count sheets, adjustments |
| SH-AST-004 | Asset transfers, disposals, retirements, impairments, and write-offs require approval and accounting update. | AST-003 | Asset owner/Accounting | event | disposal forms, JE |

## TAX — Tax & Statutory Reporting
| SH-TAX-001 | Tax/statutory obligation calendar is maintained by entity and jurisdiction. | TAX-001 | Tax/Legal | quarterly + change | filing calendar |
| SH-TAX-002 | Tax returns and provisions reconcile to financial/source records and receive review before filing. | TAX-002 | Tax/Finance | filing/close | workpapers, review |
| SH-TAX-003 | Nexus, indirect-tax, property/mineral/resource tax, and other material positions are periodically reassessed as operations change. | TAX-002/003 | Tax/Legal | quarterly/annual + event | position memos |
| SH-TAX-004 | Tax notices, audits, exposures, and uncertain positions are tracked and escalated. | TAX-003 | Tax/Legal | event | notice register, responses |

## MNA — M&A, Integration & Intercompany
| SH-MNA-001 | Acquisition proposals require cross-functional diligence and a documented risk/assumption register before approval. | MNA-001 | Corporate Development | transaction | diligence reports, risk register |
| SH-MNA-002 | Transaction approval follows board/committee reserved matters and delegated authority. | MNA-001 | CEO/CFO/Board | transaction | resolutions, approvals |
| SH-MNA-003 | Day-1 control plan defines entity ownership, banking, finance, access, security, payroll, legal, vendor, incident, and reporting responsibilities. | MNA-002 | Integration lead | pre-close/day 1 | Day-1 checklist |
| SH-MNA-004 | Inherited controls/exceptions are inventoried and assigned convergence, retain-local, remediate, or accept decisions. | MNA-003 | Integration/Control Governance | first 90/180 days | inherited-control register |
| SH-MNA-005 | Intercompany services, allocations, transactions, balances, and settlements are governed by documented arrangements and reconciled. | MNA-004 | Finance/Legal | monthly/quarterly | agreements, reconciliations |

## ARU — ARU / BS&T Operating Controls
| SH-ARU-001 | ARU and BS&T legal/entity/system/operating boundaries are maintained in the enterprise registry during integration. | ARU-001 | ARU leadership/Integration | continuous | entity map, system register |
| SH-ARU-002 | Waybill/freight/custody records reconcile shipment events, customer, rate, route, quantity, custody, and billing data. | ARU-002 | BS&T operations/Finance | transaction/daily | waybills, movement logs, reconciliation |
| SH-ARU-003 | Rail/utility critical assets and maintenance/inspection requirements are scheduled, completed, and escalated when overdue. | ARU-002 | ARU/BS&T operations | scheduled | maintenance records |
| SH-ARU-004 | Common Sable Harbor controls adopted by ARU/BS&T retain local variations required by regulation or operations. | ARU-003 | Integration/Control Governance | periodic | inheritance matrix, exceptions |

## PSN — Pale Sun / Red Wash Controls
| SH-PSN-001 | Red Wash legal/site authority, operating ownership, technical authority, and capital authority are explicitly separated. | PSN-001 | Pale Sun/Red Wash governance | continuous | authority map, delegations |
| SH-PSN-002 | Production, inventory, movement/custody, shipment/sale, and accounting records reconcile through the operating chain. | PSN-002 | Red Wash Operations/Finance | daily/monthly | production ledger, inventory, sales reconciliation |
| SH-PSN-003 | Environmental, permitting, regulated-material, monitoring, and site obligations are tied to accountable owners and evidence. | PSN-002 | Site Environmental/Legal | scheduled | permit/monitoring records |
| SH-PSN-004 | Asset-retirement/remediation obligations and related estimates are periodically reassessed from operating/environmental evidence. | PSN-002 | Finance/Operations/Environmental | quarterly/annual + event | ARO memo, estimates |
| SH-PSN-005 | Federal/security controls are activated only against defined contract/data/system boundaries and controlled applicability decisions. | PSN-003 | Security/Legal/Pale Sun | event + review | applicability memo, boundary definition |

## CRD — Cradle Participation & Recovery Controls
| SH-CRD-001 | Each Cradle arrangement documents host/operator, Sable Harbor, ownership, process/equipment, custody, measurement, and settlement rights. | CRD-001 | Cradle/Legal/Finance | contract | participation agreement, boundary memo |
| SH-CRD-002 | Recovered material measurement and allocation use controlled methods and reconcile host/Sable Harbor records. | CRD-002 | Operations/Finance | batch/settlement | measurement records, reconciliation |
| SH-CRD-003 | Custody transfers and settlement calculations are attributable, approved, and supportable. | CRD-002 | Operations/Finance | transaction | custody docs, settlement statements |
| SH-CRD-004 | Host operating authority remains with the host/operator unless explicitly contracted and legally established otherwise. | CRD-003 | Legal/Operating governance | continuous | contracts, operating boundary record |

## ADV — Advisory & Professional Services
| SH-ADV-001 | Advisory engagement acceptance documents customer, scope, conflicts, competence, data, terms, pricing, and accountable partner/leader. | ADV-001 | Advisory leadership | engagement start | acceptance form, contract |
| SH-ADV-002 | Engagement plans identify staffing, review, deliverables, dependencies, and customer responsibilities. | ADV-002 | Engagement lead | engagement start/change | project plan |
| SH-ADV-003 | Material deliverables receive technical/quality review proportionate to consequence before issuance. | ADV-002 | Reviewer / engagement lead | deliverable | review record, final artifact |
| SH-ADV-004 | Engagement closure confirms delivery, billing, records retention, data return/disposition, and open commitments. | ADV-002/003 | Engagement lead | close | closure checklist |

## ASS — Assurance, Compliance & Control Monitoring
| SH-ASS-001 | Management performs periodic control-owner certification/self-assessment without labeling it independent assurance. | ASS-001 | Control owners | quarterly/annual | attestations, exceptions |
| SH-ASS-002 | Second-line compliance/control monitoring follows documented scope, criteria, evidence, results, and escalation. | ASS-001/002 | Compliance/Control Monitoring | risk-based | monitoring workpapers |
| SH-ASS-003 | Independent assurance engagements maintain organizational independence, approved scope, evidence, findings, review, and direct escalation rights. | ASS-001/002 | Internal Assurance | risk-based | charter, workpapers, reports |
| SH-ASS-004 | Control testing defines the population/source, period, method, evidence, exceptions, and limitations before concluding. | ASS-002 | Tester/reviewer | each test | test plan, population manifest, results |
| SH-ASS-005 | Findings and remediation items maintain owner, severity, due date, action, validation, risk acceptance, and governance escalation. | ASS-003 | Issue Management | continuous | issue register, closure evidence |
| SH-ASS-006 | External-audit/assurance evidence requests are coordinated through controlled PBC/evidence workflows with source provenance. | ASS-004 | Assurance/Control owners | engagement | request log, evidence package |

## Catalog-wide rules

1. No control exists merely because an external framework contains a similarly named requirement.
2. Every control requires at least one local implementation before it can be treated as operating in a specific business boundary.
3. Control ownership is role-based. Named individuals may occupy the role, but personnel changes do not change the control ID.
4. A common control can be inherited, locally varied, supplemented, temporarily excepted, or declared not applicable with rationale.
5. Controls with direct financial-reporting relevance, customer-service relevance, security/privacy relevance, or operating/safety relevance are tagged in the structured register during the next data-population phase.
6. Evidence listed here is an expectation, not proof of control operation or audit sufficiency.
7. Frequencies may vary by local implementation where risk and business process warrant.
