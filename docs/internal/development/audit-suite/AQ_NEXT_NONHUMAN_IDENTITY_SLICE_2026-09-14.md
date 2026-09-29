# Next source-gap slice: non-human credential lifecycle

Recommend one next implementation: **SH-IAM-006, a local backup-copy workload identity with credential rotation and dependent-consumer reconciliation**. This extends an already inspectable backup dependency with computed authentication and copied dataset bytes. It does not relabel earlier human principals as service accounts.

| Candidate | Existing support | Next missing causal work | Priority |
|---|---|---|---|
| IAM-006 | Backup inventory, native dataset bytes, credential-expiry event and failed job | Explicit non-human identity, named owner, dependency inventory, constrained grants, credential rotation and review | First: direct source dependency and useful authentication/data-copy consequences |
| IAM-005 | Local lifecycle handles and release authorization records | Separately approved privileged session, finite emergency activation, session audit, expiry/credential exposure handling and review | Next; current ordinary worker access and release override are not break-glass authorization |
| SEC-003 | Exact proposed/corrected build and test artifacts in change-release sources | Defined local vulnerable condition, coverage reconciliation, validated finding, local remediation timing and actual rescan | Feasible later; current performance/approval failures are not automatically security vulnerabilities or CVEs |
| SEC-001 | Canon design/procurement and site records | Explicit local trust-zone/data-flow/admin/key-custody model, threat scenario and minimum requirement review | Keep source-backed design work separate from asserted deployed architecture |

The catalog calls IAM-006 quarterly plus change. The authored procedure requires owner, workload, permissions, dependencies and credential lifecycle; constrained grants/rotation according to approved risk requirements; quarterly and ownership-change review. The proposed slice exercises one declared local workload and a credential-change review plus one quarter-end review. An ownership change, full-year operation, every enterprise identity and professional effectiveness remain outside this slice.

Use a **new** `EXERCISE-SVC-BACKUP-COPY` identity in new paired company branches, starting after the latest selected upstream availability (proposed April 2027). Existing backup records identify human `AS-P007`; preserve that original fact. The new identity is a declared local simulation assumption, never an inference that an Okta account or production service principal already exists. Current IAM-006 scoped contact mapping is primary/custodian AS-P007 and operating reviewer AS-P008, status PROPOSED_CURRENT_ASSIGNMENT; no appointment, hiring or professional qualification follows.

Both branches use the same source dataset, new workload/dependency inventory, owner, read-source/write-isolated-target permissions and local rotation timetable. A data-only local authenticator accepts a credential version for that identity and denies undeclared operations; no usable external credentials or network calls. At rotation, both issue the new version and retire the old version. In the second branch only, one explicitly recorded dependency-update operation is omitted. The consumer's next authenticated copy fails from the actual version mismatch, not an audit mode or prewritten result. Reconcile credential and consumer versions, preserve failed attempt and empty/absent output, then apply the missing update and retain a successful new copy with independently recomputed byte hash. An old-version probe remains denied after recovery. Quarter-end review reconciles the one declared identity, named owner, allowed operations, dependencies and retained rotation history. Local timing/role rules are explicitly exercise assumptions, not accepted enterprise secret policy.

Exact existing source selection (read-only verified SHA; physical company **SH**, branch **backup-messy**, root `enterprise/generated/audit-suite/company-backup-period-2026-09-14/v1/company`):

| System | Record | Version | Native SHA256 | Available at |
|---|---|---:|---|---|
| `backup_job` | `BACKUP-01-backup_job` | 2 | `6a7e7cdec8dd222c18e00d4d8e0c08126ebf55454934c55384fcc6b73346131b` | 2027-03-13T00:02:00.000000+00:00 |
| `credential_event` | `BACKUP-01-credential_event` | 2 | `be4d6ac4d3bf8587909b8d657cc2b701d6e504d5c1ce981a14627b27f808d6e2` | 2027-03-12T23:55:00.000000+00:00 |
| `inventory` | `BACKUP-01-inventory` | 1 | `d3fe939b7c7a1624d2eefc7b0ad75f5d46b6bcb0b92a101503be1b029bdf0abd` | 2027-03-11T00:00:00.000000+00:00 |
| `source_dataset` | `BACKUP-01-source_dataset` | 2 | `23197336849134907caf776cf6981e9f8d8c560dbaf2454c4abe4ad0fc1aa01f` | 2027-03-12T23:50:00.000000+00:00 |

The inventory/dataset are direct dependency inputs. The credential-expiry/job records are pinned historical motivation only: do not transplant their human principal, pretend they were caused by the new identity, or rewrite their chronology. Preserve site qualifiers: Reno/Boise provider-selected and procurement-pending, not operating; SVC-compute is a design reference; small nonpersonal data and no PHI processing.

Expected new operational systems: identity inventory, credential metadata, consumer configuration, authentication/copy attempts, reconciliation, remediation and review. Store original record versions before any audit; retain initial failure and later correction. No hidden expected conclusions belong in these records. Tests must verify the same initial conditions, actual credential-version authorization, permission denials, native copy/hash equality, unchanged upstream versions, source availability, changed-input rejection and private non-overwriting publication.

AQ-06 integration can use the existing one-system `company.census.collect` route, explicit alias, event window and version policy. Credential/inventory versions are source-record units, not counts proving business or identity completeness. Review the exact query manifest and explicitly import only a PROVISIONAL population; no automatic acceptance, sampling or test credit. Cross-system dependency reconciliation remains an explicit procedure, not an unsupported cross-store population union.

Controlling source pins inspected for this proposal:

- `docs/controls/COMMON_CONTROL_CATALOG_v0.1.md`: `6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433`
- `enterprise/ccf/assurance/design_data/control_procedures.json`: `258f5c868e16f3dc197594857dc86a4f2b3ef11e3e5a36dd0a80a9fc6d40c679`
- `docs/controls/CCF_ENTERPRISE_SECURITY_VENDOR_DECISIONS_2026-09-11.md`: `e293c99136c61c1742547849d833610ca0f70bed0968d380cd49c31ea7721762`

This note is an implementation proposal only. No generator/schema, grants, company records, audit state, service, model or external account changed.
