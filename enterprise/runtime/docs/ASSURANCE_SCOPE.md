# Runtime assurance scope and evidence dependencies

**Document ID:** SH-RT-ASSURANCE-001
**Version:** 1.0.0
**Status:** provisional scoping; operating effectiveness NOT_ASSERTED
**Prepared / effective design date:** 2026-09-11
**Owner:** Risk & Compliance with service owners and Finance
**Authority:** CCF and PR119 mandate
**Structured companion:** runtime source and `security.assess_evidence`

## System and reporting boundary

The system includes customer-controlled equipment, platform software, identities,
keys, data stores, recovery copies, operating people and procedures in the proposed
Reno/Boise estate. Switch and IDACORE supply facility layers, not Sable Harbor's
application controls or institutional judgment. Their subcontractors, carrier
routes, CUECs and report carve-outs remain evidence dependencies. The owned site
has no operating system boundary yet because it is preconstruction.

Alexandria is internal institutional use. Atlas and Foundry may create customer
service commitments within their hosted scopes; customer-hosted/edge operation
has different responsibility. No hosted contract or user-entity population is
invented here. Scope a future report from actual services, commitments, contracts,
period, customer dependencies, incidents and material changes.

[AICPA's SOC 1 topic](https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater-than-soc-1)
ties SOC 1 to controls relevant to user entities' internal control over financial
reporting. Sable Harbor's own project accounting alone does not establish SOC 1
service relevance. Atlas/Foundry reporting or transaction dependencies require
customer-specific assessment before claiming applicability.

For SOC 2, Security, Availability and Confidentiality are proposed categories
based on this design's intended commitments. Processing Integrity and Privacy
need a specific scoped commitment and processing inventory; all five categories
are not automatically selected or satisfied. The
[AICPA criteria resource](https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022)
identifies the 2017 criteria with revised 2022 points of focus. Its full download
requires account access in the inspected page. No paragraph-level validation or
complete criterion crosswalk is claimed. The
[SOC suite overview](https://www.aicpa-cima.com/resources/landing/system-and-organization-controls-soc-suite-of-services)
describes CPA assurance services; this repository creates neither a report nor a
certification. Type 1 design-at-a-date and Type 2 operation-over-a-period require
distinct evidence propositions and professional scoping.

## Provisional directional mapping

| Native controls | Proposed category support | Scope limitation |
|---|---|---|
| SH-IAM-002/004/005/007, SH-SEC-001/002 | Security | Customer access/configuration only; actual execution untested |
| SH-OPS-001/002, SH-BCM-001/002/003/004 | Availability | Recovery requirements and design; no proven RTO/RPO |
| SH-DAT-001/002/003/005, SH-REC-004 | Confidentiality | Rights/retention design; legal schedules and execution required |
| SH-REC-002/003, SH-TPR-002/003/004 | Supporting evidence | Not equivalent to practitioner requirements |

Direction is Sable Harbor control to category, partial/contextual support,
confidence low, review pending, non-equivalence true. Exact external requirement
IDs remain unassigned until validated full text and practitioner review; technical
practice or vendor labels do not become AICPA requirements.

## Evidence collection and assessment

Expected evidence includes executed instruments and acceptance, metering and
incident populations, complete access and change populations, backup job inventory,
restore/failback results, provider reports, subservice/CUEC mapping and exceptions.
For every extract retain authorized source, period, timezone, query/filters,
pagination, transformations, expected/observed count, reconciliation, hash scope,
preparer and independent reviewer. A hash proves acquired-byte integrity, not
population completeness. Empty required populations fail or remain not run.

Assess control definition, implementation, design assessment, operating assessment
and evidence origin independently. The current synthetic reference tests cannot
be relabeled actual evidence or operating effectiveness. Targeted high-risk
selections are not representative samples. Exceptions need owner, approver,
expiry, compensating measures, remediation and original-period retest by a
different reviewer; later unrelated PASS does not erase an original failure.

Provider reports require actual legal scope, service/site, period, auditor, opinion,
exceptions, subservice treatment, CUECs and changes review. A provider bridge letter
is an intervening management representation, not a new auditor opinion extending
testing. Report bytes and restricted material remain outside this public package.
Provider marketing assurance labels stay PUBLIC_CLAIM_ONLY.

## Source-access register, retrieved September 11, 2026

| Publisher / source | Valid use | Limitation / refresh owner |
|---|---|---|
| [IDACORE pricing](https://idacore.com/pricing) | Boise $300/kW/month, actual-draw power-inclusive public baseline | Quote, meter and term ambiguity; Procurement |
| [IDACORE Boise](https://idacore.com/boise) | Selected facility address and advertised facility characteristics | Reports, legal party and assigned space unverified; Security/Procurement |
| [Switch Tahoe Reno](https://www.switch.com/tahoe-reno/) | Selected campus identity | No customer reservation/contract; Procurement |
| [NVIDIA DGX B300 guide](https://docs.nvidia.com/dgx/dgxb300-user-guide/introduction-to-dgxb300.html) | Distinguish system specifications from PSU sums | Different reference class from synthetic 8 kW model; Technology |
| AICPA SOC 1 topic, criteria resource and suite above | Engagement purpose and criteria identity | Full licensed/account-controlled authority and exact mappings unvalidated; Risk & Compliance |
| PostgreSQL version policy in architecture record | Supported release policy | Exact deployed BOM/patch acceptance unperformed; Platform |

Public pages establish only their stated fields. Retrieval dates are not report
periods or acceptance dates. No private NAILEX implementation, licensed text,
hidden evaluator data, credentials, real attestation or real operating history
is included in this design package.
