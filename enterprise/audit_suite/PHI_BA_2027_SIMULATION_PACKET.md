# Fictional 2027 customer ePHI/BA flow: field-level implementation packet

Status: isolated native exercise for a **training-only 2027 branch**, bound to
the independently reviewed Reno/Boise transition V3. It does not amend 2026 company canon or
assert a real customer, contract, legal status, PHI processing, deployment, or
audit result. The active A349/B324 audit registry and tasks are untouched.

## Fixed boundary and source pins

| Source | SHA-256 | Use |
|---|---|---|
| `docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md` | `15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496` | Owner-selected fictional 2027 sites and ePHI/BA direction; nonpersonal, payload-free simulation only. |
| `docs/internal/development/CCF_ASSURANCE_SCOPE_PROPOSAL_2026-09-11.md` | `0ea41553d1f8bc975242f7ea8939f8750ec6f74e3aceb43f2e82101421a8b25a` | Approved *hypothetical* BA/subcontractor reference, SOC 2 categories and Reno/Boise shared controls; no actual PHI or period. |
| `docs/canon/RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md` | `fd309a9bdf596ea96498b7207b60ea3bea70a35d8c418371aa96c06d928bb17b` | Selected providers and 2026 nonoperating truth. |
| `enterprise/services/source/runtime_sites_2026-09-11.json` | `fa216f629762503865fd9f1a3207e87691cd484cec9885bf25ce045b4525519c` | Exact Reno/Boise site, provider, dependency and draft-contract IDs. |
| `enterprise/ccf/assurance/design_data/SERVICE_DESCRIPTION.md` | `d4697f8c01a9311cc208c2e4b1bd4bf1067bd02a001d4acb33cde29f15d30e89` | Proposed shared service, not a management assertion. |
| `enterprise/ccf/assurance/design_data/control_procedures.json` | `258f5c868e16f3dc197594857dc86a4f2b3ef11e3e5a36dd0a80a9fc6d40c679` | Candidate SH-DAT-002, SH-LEG-001/002, SH-TPR-003, SH-REC-004 procedures. |
| `enterprise/ccf/assurance/design_data/hipaa_analysis.json` | `27bb69cffd19e266abd56149db33da710dba07078328361fe9aca7293daa17c8` | Separate legal-role/design analysis, not an applicability decision. |
| `enterprise/audit_suite/phi_ba_2027_contract_spec_v1.json` | `557cd3ddf09195207de93be2441710f38be9aa8693de729c07d8cf45e45a081f` | Proposed exact fictional SHI/customer/support parties, BA-only limited delegation, reviewers, counterparty personas and eight structured synthetic obligations per contract; independent review still required. |

The official [45 CFR 164.308(b)](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-C/section-164.308),
[45 CFR 164.504(e)](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.504), and
[HHS business-associate guidance](https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/business-associates/index.html)
were checked on 2026-09-29 for candidate written-assurance and subcontractor
flow-down context. The scenario's legal-role decision is an expressly fictional
training assumption; no actual Sable Harbor or provider applicability is inferred.

The only permitted runtime dependency is the Reno/Boise agent's independently
reviewed **native 2027 transition V3 receipt** (review SHA-256
`f1acaeaea963055f99b0de120fd1b0347ee984edf085d353e7af1e427234d5a9`;
receipt `0a0a448f619e490870f69959d196eb6d5ca3747af0d4fb68056195910ce6cc11`,
manifest `f7c6ec3ab460f204f69cf6b50df66399687034b3b63cb38aaee84841daedcbd4`,
database `428b5c740cb8fc627b38f2aa6847e450fd166e62be52a6309d4f5a7b284988fd`).
Implementation verifies its
branch-specific native IDs/hashes, both Reno and Boise release states and
availability clocks. The ePHI exercise must use a separate branch for each
Clean/Messy path and derive all flow clocks strictly after that branch's Boise
release. The earlier
prospective metadata-flow and provider-draft exercises are design predecessors,
not operational source records to transplant into this branch.

## Scenario-only entities and fields

All identifiers below have `SIM-` prefixes and `truth_class =
TRAINING_SCENARIO_ONLY`. An implementation must not use real names, patient
identifiers, PHI or external communications.

| Record/system | Required fields and source relationships |
|---|---|
| `scenario_scope` | `scenario_id`, `branch_id`, `sim_customer_id=SIM-COVERED-CUSTOMER-01`, `sim_service_id=SIM-RESTRICTED-HOSTING-01`, `sim_subcontractor_id=SIM-RECOVERY-SUPPORT-01`, `data_class=SYNTHETIC_EPHI_ANALOG`, `fixture_contains_real_phi=false`, `actual_legal_applicability=UNDETERMINED`, exact 2026 canon pins, exact transition receipt/native release pins, and a statement that Switch/IDACORE are site dependencies, **not automatically BA subcontractors**. |
| `role_decision` | Fictional case facts (customer assumed covered entity; Sable Harbor assumed to maintain the synthetic analog on its behalf; scenario-only support party assumed to maintain a recovery copy), proposed Legal contact `AS-P003` acting only in the training branch, decision `BA_AND_SUBCONTRACTOR_FOR_TRAINING_ONLY`, rationale and cited candidate rule locators, event/availability/import clocks, and `real_world_decision=false`. |
| `contract_authority` | Scenario-only Daniel Mercer CEO delegation `DA-PHI-BA-2027` to Adrian Lowe (`AS-P002`), limited to the two `SIM-BAA` IDs. This is separate from the two-site runtime delegation and grants no real signature authority. |
| `contract_approval` and `counterparty_acceptance` | Per-BAA legal, technology, security and data-governance review by Helena Ward (`AS-P003`), Elliot Tran (`AS-P007`), Dana West (`AS-P008`) and Omar Vale (`AS-P014`), followed by distinct fictional customer/support signatory acceptance. Exact source and availability times precede in-simulation execution. |
| `contract` | Upstream `SIM-BAA-CUST-01` and downstream `SIM-BAA-SUB-01`; party IDs, service/data scope, eight contract-specific structured synthetic obligations, matching terms hashes on each individual reviewer and counterparty acceptance, scenario-only signer IDs, simulated execution/effective times, `real_signature=false`, and prior-record hash. A signed-in-simulation state must never be rendered as an actual agreement. |
| `flow_event` | Synthetic record token with **no payload**; Reno source and Boise recovery dependency IDs; action, before/after state, site-release/role/upstream/downstream gate references, `payload_bytes=0` and a metadata-marker digest, source event time, source availability time, actual import time, causal prior hash, destination acknowledgement and exception ID. The source operation is a simulation of ePHI handling, not actual PHI transfer. |
| `exception_event` | Stable single exception ID in Messy, detected-at and available-at separately, affected synthetic token, missing/late downstream flow-down, quarantine decision, owner/cure proposal, current open status, and whether any simulated copy reached the support role. No breach or real notice conclusion is automatic. |

Clean must record the fictional role decision, distinct limited delegation,
reviewer and counterparty approvals, and both in-simulation BAAs before the
synthetic token is admitted at Reno or copied to Boise. The gate checks
branch-specific release evidence, both contract effective **and available**
clocks, authorized flow purpose and marker digest reconciliation. Its state is
`RECONCILED` in the training branch, not an audit PASS.

Messy must preserve a causal defect rather than plant an answer: a local
recovery-routing marker advances before downstream review, acceptance and
flow-down are effective; the later gate detects the mismatch, quarantines the
marker, records a delayed source-availability clock and leaves one exception
open even if the downstream agreement is backfilled afterward. The support
copy acknowledgement remains `NOT_ESTABLISHED`; uncertainty is not silently
converted into a confirmed transfer or a breach finding.

Every native row needs `event_at`, `available_at`, real `imported_at`, source
origin `AUTHORED_TRAINING_SOURCE`, immutable identity/version/SHA, and exact
provenance pins. The receipt must separately count native versions, event rows,
and distinct open exceptions. `verify()` must reject source-pin drift,
non-private paths, sidecars, causally impossible order, missing prior hashes,
pre-release flows, and a report that upgrades simulated facts into actual
operation. No grant, audit collection, workpaper, task command, Key or release
is part of this slice.

## Dependency and acceptance gates

1. Check the reviewed V3 transition receipt's exact original native rows,
   branch IDs, release status and available-at clocks. V1/V2 schemas and
   differing bytes fail closed.
2. Build the smallest `CompanyStore` source with two isolated branches,
   source-pin every decision/contract/flow row, and run focused Clean/Messy,
   chronology, privacy, gate and tamper tests.
3. Seal a private run and obtain independent review. Inclusion in a future
   full-source registry requires a fresh zero-evidence audit pair and separate
   ordinary collections and exact procedures. Real management/legal decisions
   and qualified sufficiency remain separate.
