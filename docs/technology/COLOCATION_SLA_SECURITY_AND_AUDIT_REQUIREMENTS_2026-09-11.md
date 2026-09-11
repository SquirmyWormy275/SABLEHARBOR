# Colocation SLA, Security, Audit, and Contract Requirements

**Document ID:** SH-RT-SLA-001
**Version:** 1.0.0
**Prepared:** 2026-09-11
**Owner:** Enterprise Technology Services with Legal, Finance, Procurement and Facilities
**Authority:** Owner-authorized PR119 runtime mandate, pending repository acceptance
**Structured companion:** `enterprise/services/source/runtime_sites_2026-09-11.json`; `runtime_capital_plan_2026-09-11.json`

**Applies to:** Reno primary colocation and Boise independent recovery colocation.
**Status:** mandatory procurement and control baseline; not an executed vendor agreement.

## 1. Contract structure

Each facility agreement must include: master services agreement; site/service order; SLA schedule; security schedule; data-processing/confidentiality schedule where applicable; audit/evidence schedule; business-continuity schedule; insurance; incident notification; subcontractor/subservice register; exit/transition schedule; pricing/escalator schedule; and an asset-access/removal clause preserving Sable Harbor ownership of all customer equipment.

The provider supplies facility services. Sable Harbor retains ownership and authority over servers, storage, network/security appliances, HSMs/keys, operating systems, workloads, data classification, identities, authorization, logging, backup policy, and application recovery.

## 2. Required Reno primary service

- Dedicated private cage or equivalent independently controlled enclosure; initial 75–100 kW usable IT commitment with contractual expansion to 200–250 kW without forced relocation.
- Dual independent A/B power to every production cabinet; independently metered feeds; UPS and generator-backed; maintenance must preserve required redundancy.
- High-density/liquid-cooling capability for AI rows; ordinary air-cooled rows permitted.
- Two physically diverse building fiber entrances and at least two upstream carriers. Provider must disclose shared conduit/manhole/meet-me-room dependencies.
- 10 Gbps initial external/replication capability with 100 Gbps upgrade path.
- Customer-controlled network edge, HSM/key hardware, out-of-band management, monitoring, and approved cage cameras.
- 24x7 authorized physical access and 24x7 remote hands.

## 3. Required Boise recovery service

- Separate provider/control plane from Reno unless formally risk-accepted; different customer-admin credentials and independent emergency contacts.
- 25 kW provisional initial recovery footprint, with 50/100 kW expansion sensitivities as recovery design grows; dual A/B power; independent network carriers; 100% durable protected data capacity required even where recovery compute is reduced.
- Recovery keys, DNS, identity, artifacts, runbooks, and break-glass access must not require the Reno environment to function.
- Replication routes must be documented end to end. A private circuit is not assumed diverse merely because it is sold by a different carrier.

## 4. SLA minimums

| Service | Minimum contractual requirement | Evidence |
|---|---|---|
| Critical power | 100% facility critical-power availability, subject only to tightly bounded exclusions | Monthly SLA report, incident tickets, maintenance logs |
| Environmental control | Temperature/humidity maintained within contracted equipment envelope | Sensor reports and excursion tickets |
| Remote hands | P1 acknowledgement <=15 min; technician engagement <=30 min; 24x7 | Ticket timestamps |
| Physical access | 24x7 for approved personnel; emergency access procedure | Access logs |
| Incident notification | Security/availability incident affecting Sable Harbor: initial notice <=30 min for P1 availability, <=1 hour for confirmed/suspected security incident | Notification record |
| Planned maintenance | >=14 days ordinary notice; >=30 days for material electrical/network work where practicable | Maintenance notices |
| Service reporting | Monthly availability, incidents, maintenance, access anomalies, capacity, SLA credits | Monthly service pack |
| Evidence delivery | Current assurance reports and requested control evidence within 10 business days unless legally restricted | Evidence register |
| Exit access | Uninterrupted reasonable access to remove customer equipment following termination; no lien over data or keys | Exit test / contract clause |

SLA credits are not the control objective. Chronic SLA failure, repeated near misses, or loss of redundancy triggers supplier risk escalation regardless of credits.

## 5. Physical security

Minimum layered controls: staffed/monitored perimeter appropriate to facility; controlled vehicle/loading access; visitor identification and escort; anti-tailgating control; MFA/biometric or equivalent controlled entry to secured data-hall zone; separate cage control; CCTV covering approaches and cage perimeter with synchronized time; access-event logging; alarm response; secure receiving/staging; chain of custody; prohibited photography except approved work; background-screened provider personnel with access; immediate revocation capability.

Sable Harbor cage access is least privilege, named-person, time-bounded where practical, reviewed quarterly, and reconciled to HR/vendor status. Provider master access to the cage must be contractually restricted, logged, and limited to emergency or authorized remote-hands activity.

## 6. Logical and network controls

Provider facility systems must not administer Sable Harbor production systems. Cross-connects terminate on Sable Harbor-controlled edge equipment. Management interfaces use separate networks. Internet, replication, OOB, and provider-management paths are segmented. BGP/route changes, carrier additions, and cross-connect changes require change records. DDoS and carrier protections are documented but do not substitute for Sable Harbor network controls.

## 7. Security and privacy incident requirements

Provider must preserve relevant logs/evidence; notify Sable Harbor; identify affected site/system/time window; maintain an incident commander; provide containment and restoration updates; support forensic preservation; provide root-cause analysis and corrective action for material incidents; and notify before destroying relevant evidence. Contract must define regulator/customer cooperation without giving the provider authority to speak for Sable Harbor.

## 8. Audit and assurance package

Before production and annually thereafter obtain, where applicable: SOC 1 Type II; SOC 2 Type II; bridge letter when report period is stale; ISO 27001 certificate/scope where maintained; penetration/physical-security summary where contractually available; BCP/DR test summary; insurance certificates; subservice organization list; complementary user entity controls (CUECs); exceptions and management responses; uptime/SLA history; material incident history; access-control evidence; maintenance evidence; generator/UPS load-test evidence; fire/life-safety inspection evidence.

A provider SOC report is evidence about the provider control environment, not proof that Sable Harbor controls operated. CUECs must be mapped to Sable Harbor controls and tested separately.

## 9. SOC 1 / SOC 2 evidence requirements

Maintain a vendor evidence manifest recording source, report period, retrieval date, hash, reviewer, scope, exceptions, CUECs, mapped CCF controls, disposition, and next refresh. Evidence populations must preserve completeness parameters and provenance. Sampling, targeted selections, and whole-population tests remain explicitly distinguished. Synthetic exercises never become operating-effectiveness assertions.

## 10. Business continuity and recovery

Provider must disclose utility feeds, UPS topology, generator topology, fuel contracts, cooling redundancy, carrier entrances, material single points of failure, flood/fire/seismic/wildfire exposures, staffing model, and emergency procedures. Reno and Boise recovery exercises occur at least annually, with component tests more frequently. Sable Harbor recovery testing includes key recovery, identity, DNS, data integrity, service start, failover, failback, and provider exit.

## 11. Capacity and change

Monthly service review records contracted kW, measured peak/95th percentile, rack density, cooling margin, cross-connect utilization, storage/replication growth, and committed pipeline. Expansion planning starts before 65% of constrained facility capacity or when lead time exceeds forecast exhaustion date.

## 12. Termination and portability

Sable Harbor retains title to equipment and data. Provider must support orderly de-installation, secure shipping, media custody, cross-connect termination, access-log export, evidence preservation, and final billing reconciliation. Provider-held copies of Sable Harbor confidential data, if any, require certified deletion subject to legal hold. Keys remain Sable Harbor-controlled and are never surrendered as an exit condition.

## 13. Procurement red lines

Reject or escalate any offer that lacks: dual power; credible carrier diversity; customer-owned HSM/network support; audit evidence; defined incident notification; controlled provider access; expansion rights; equipment removal rights; material subcontractor transparency; or recovery/exit cooperation.

## Implemented draft and calculations

The substantive customer-proposed [contract dossier](../../enterprise/runtime/docs/CONTRACT_DOSSIER.md) defines order hierarchy, measurement, graduated credits and negotiation gaps. `enterprise/runtime/security.py` re-performs the proposed SLA calculations. Neither document asserts vendor acceptance.
