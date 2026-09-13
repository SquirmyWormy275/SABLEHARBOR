# Bounded control test contracts

These 24 adapters compute assertions over retained source exports. A passing assertion is not full control effectiveness, source authenticity, authorized policy, framework mapping acceptance or an external assessment opinion. Every plan retains its original BASE test and all additional framework duties as mandatory evidence-citing human tests. Negative fixtures never become accepted actual evidence.

The authoritative draft procedure anchors are `../assurance/design_data/control_procedures.json` and `../assurance/completion_data/control_procedures.json`, keyed by the stable control IDs below. Selection of these checks does not change those procedures or approve their mappings. The source-backed assessment checklist binds all 70 baseline controls across three boundaries; only the specifically listed assertions are automated.

## Collection and input rules

Each export is a JSON array of records with `id`, `origin`, `boundary_id`, `occurred_at`, `kind` and `data`. `kind` must match the plan adapter for every population record; unstructured supporting material must be retained separately and cited through an appropriate record contract rather than hidden among skipped rows. Record IDs must exactly reconcile to the independently registered population. Boundary, origin, period, collection chronology and freshness are checked before assertions. An empty collection does not establish operation of an automated control.

Timestamps require explicit time zones. Numeric thresholds must be finite nonnegative numbers; booleans cannot substitute for numbers. Boolean observations require JSON booleans. Identifiers require nonblank text; ID arrays must be unique. SHA256 values require 64 lowercase hexadecimal characters. Ordinary ordered timestamps permit equality for atomic events; exception and delegation expiry are exclusive. An expired exception is not automatically converted into an accepted deviation.

The example values below are entirely invented, including limits, due dates, authority IDs, roles and approval lists. Operators must obtain those inputs from separately reviewed actual policy and source records, not copy the example values. Inner identifier sets (rights, assets, copies, tests and recipients) require independent source validation as a mandatory human duty; this program compares supplied sets and cannot prove a vendor export is complete. No secret values are collected. Missing/malformed structured fields produce NOT_RUN through evaluate; substantive violated assertions produce FAIL. Human failures remain failures even if every computed check passes.

For normal-path release/change adapters, emergency approvals and exceptions require their own qualified manual disposition; they are not automatic bypasses of failing assertions. An extra runtime grant or uncovered asset is treated as a failure, not silently excluded. Log aggregate measurements must be derived from retained raw events with reviewed calculations; this adapter alone does not independently compute their maxima.

## Per-control contracts

### SH-IAM-004: `termination`

Draft procedure: At termination or contract expiry, use the authorized effective time to disable accounts, sessions, tokens, remote access and physical credentials; reconcile every connected system; escalate missed revocations immediately.

Computed assertions: `disabled`, `rights_removed`, `timely`.

Required `data` fields and invented positive values:

```json
{
  "enabled": false,
  "active_entitlements": 0,
  "terminated_at": "2026-09-09T09:00:00+00:00",
  "disabled_at": "2026-09-09T09:10:00+00:00",
  "due_at": "2026-09-09T09:30:00+00:00"
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-IAM-007: `access_review`

Draft procedure: Quarterly for privileged access and at a risk-approved cadence for other rights, reconcile HR/contractor records to actual entitlements; require owner decisions per account; independently confirm removals and overdue escalation.

Computed assertions: `independent`, `timely_review`, `valid_decision`, `decision_enforced`, `removal_timely`.

Required `data` fields and invented positive values:

```json
{
  "reviewer": "DEMO-REVIEWER",
  "account_owner": "DEMO-WORKER",
  "reviewed_at": "2026-09-09T09:10:00+00:00",
  "due_at": "2026-09-09T09:30:00+00:00",
  "decision": "REMOVE",
  "active": false,
  "removed_at": "2026-09-09T09:10:00+00:00",
  "removal_due_at": "2026-09-09T09:30:00+00:00"
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-BCM-002: `backup_job`

Draft procedure: Assign each dataset a schedule derived from its approved RPO; record retention and isolation; monitor every scheduled job; ticket missed or failed runs and reconcile protected datasets to inventory.

Computed assertions: `completed`, `timely`, `artifact_matches`.

Required `data` fields and invented positive values:

```json
{
  "status": "SUCCESS",
  "scheduled_at": "2026-09-09T09:00:00+00:00",
  "completed_at": "2026-09-09T09:10:00+00:00",
  "due_at": "2026-09-09T09:30:00+00:00",
  "expected_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "observed_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-BCM-003: `restore`

Draft procedure: Select critical datasets and recovery paths using documented risk; restore into an isolated environment; measure recovery time and recovered data age; validate integrity and usability against the BIA; record failures and retest.

Computed assertions: `rto`, `rpo`, `content`, `dependencies`, `suppressed_data_absent`.

Required `data` fields and invented positive values:

```json
{
  "started_at": "2026-09-09T09:00:00+00:00",
  "completed_at": "2026-09-09T09:10:00+00:00",
  "recovery_point_at": "2026-09-09T09:00:00+00:00",
  "rto_seconds": 1800,
  "rpo_seconds": 300,
  "expected_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "observed_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "dependencies_ready": true,
  "suppressed_data_absent": true
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-CFG-002: `configuration_drift`

Draft procedure: Version the intended configuration for each technology; compare deployed settings to the approved baseline; investigate drift and link correction or an expiring exception.

Computed assertions: `authorized_baseline`, `no_unresolved_drift`.

Required `data` fields and invented positive values:

```json
{
  "approved_baseline": "DEMO-BASELINE-1",
  "observed_baseline": "DEMO-BASELINE-1",
  "unresolved_drift_count": 0
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-INC-001: `incident_escalation`

Draft procedure: Assign severity and commander at discovery; activate escalation, preservation and communications; for suspected PHI breaches route discovery time and upstream notification requirements to legal/privacy; exercise contacts annually.

Computed assertions: `timely`, `required_recipients`.

Required `data` fields and invented positive values:

```json
{
  "detected_at": "2026-09-09T09:00:00+00:00",
  "escalated_at": "2026-09-09T09:10:00+00:00",
  "due_at": "2026-09-09T09:30:00+00:00",
  "required_recipient_ids": [
    "DEMO-ONCALL",
    "DEMO-SECURITY"
  ],
  "notified_recipient_ids": [
    "DEMO-ONCALL",
    "DEMO-SECURITY"
  ]
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-SEC-003: `vulnerability`

Draft procedure: Reconcile asset coverage across scanners, testing and advisories; validate findings; assign remediation against approved severity/exploitability SLAs; verify fixes by rescan or record expiring acceptance.

Computed assertions: `remediated`, `timely`, `independent`, `verification_clear`.

Required `data` fields and invented positive values:

```json
{
  "status": "REMEDIATED",
  "detected_at": "2026-09-09T09:00:00+00:00",
  "verified_at": "2026-09-09T09:10:00+00:00",
  "due_at": "2026-09-09T09:30:00+00:00",
  "verifier": "DEMO-REVIEWER",
  "remediator": "DEMO-ENGINEER",
  "verification_clear": true
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-TRN-002: `training`

Draft procedure: Monthly, reconcile required learners to course completions; notify overdue learners and managers; escalate persistent gaps and record approved exceptions.

Computed assertions: `correct_course`, `timely`, `assessment_passed`.

Required `data` fields and invented positive values:

```json
{
  "required_course_version": "DEMO-COURSE-2",
  "completed_course_version": "DEMO-COURSE-2",
  "assigned_at": "2026-09-09T09:00:00+00:00",
  "completed_at": "2026-09-09T09:10:00+00:00",
  "due_at": "2026-09-09T09:30:00+00:00",
  "assessment_passed": true
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-IAM-001: `identity_creation`

Draft procedure: Create a unique identity only from an approved worker, contractor or service request; bind sponsor, start/end dates and identity proofing; reconcile creations with authoritative requests.

Computed assertions: `approved_request`, `sponsor`, `identity_proofed`, `authorized_window`.

Required `data` fields and invented positive values:

```json
{
  "approved_request_id": "DEMO-REQUEST",
  "creation_request_id": "DEMO-REQUEST",
  "sponsor_id": "DEMO-SPONSOR",
  "identity_id": "DEMO-WORKER",
  "identity_proofed": true,
  "approved_at": "2026-09-09T09:00:00+00:00",
  "start_at": "2026-09-09T09:00:00+00:00",
  "created_at": "2026-09-09T09:10:00+00:00",
  "end_at": "2026-09-09T09:30:00+00:00"
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-IAM-002: `access_grant`

Draft procedure: Record business need, role, boundary and duration; obtain resource-owner approval; check conflicting privileges; provision only approved rights and confirm actual grants.

Computed assertions: `exact_approved_rights`, `owner_approved`, `independent`, `no_conflicts`, `authorized_window`.

Required `data` fields and invented positive values:

```json
{
  "approved_right_ids": [
    "DEMO-READ"
  ],
  "actual_right_ids": [
    "DEMO-READ"
  ],
  "approver_id": "DEMO-OWNER",
  "resource_owner_id": "DEMO-OWNER",
  "requester_id": "DEMO-WORKER",
  "conflicting_right_ids": [],
  "approved_at": "2026-09-09T09:00:00+00:00",
  "granted_at": "2026-09-09T09:10:00+00:00",
  "expires_at": "2026-09-09T09:30:00+00:00"
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-IAM-003: `mover_access`

Draft procedure: On role change, compare old and new required rights; revoke obsolete entitlements as well as grant approved additions; reconcile applications and site access to the change.

Computed assertions: `exact_new_rights`, `obsolete_removed`, `timely_change`.

Required `data` fields and invented positive values:

```json
{
  "old_right_ids": [
    "DEMO-OLD"
  ],
  "approved_new_right_ids": [
    "DEMO-NEW"
  ],
  "actual_right_ids": [
    "DEMO-NEW"
  ],
  "approved_at": "2026-09-09T09:00:00+00:00",
  "effective_at": "2026-09-09T09:00:00+00:00",
  "reconciled_at": "2026-09-09T09:10:00+00:00",
  "due_at": "2026-09-09T09:30:00+00:00"
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-IAM-005: `privilege_expiry`

Draft procedure: Issue privileged access separately with purpose and duration; record emergency activation and session activity; expire access, rotate exposed credentials and review each emergency use plus quarterly privilege population.

Computed assertions: `separate_identity`, `limited_duration`, `inactive`, `sessions_retained`, `independent_review`, `review_after_use`.

Required `data` fields and invented positive values:

```json
{
  "privileged_identity_id": "DEMO-PRIV",
  "ordinary_identity_id": "DEMO-ORDINARY",
  "approved_at": "2026-09-09T09:00:00+00:00",
  "activated_at": "2026-09-09T09:00:00+00:00",
  "revoked_at": "2026-09-09T09:10:00+00:00",
  "expires_at": "2026-09-09T09:30:00+00:00",
  "active": false,
  "session_record_ids": [
    "DEMO-SESSION"
  ],
  "reviewer_id": "DEMO-REVIEWER",
  "operator_id": "DEMO-OPERATOR",
  "reviewed_at": "2026-09-09T09:30:00+00:00",
  "review_due_at": "2026-09-09T11:00:00+00:00"
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-IAM-006: `service_account`

Draft procedure: Record owner, workload, permissions, dependencies and credential lifecycle for every non-human account; constrain grants and rotation according to approved risk requirements; review quarterly and on ownership change.

Computed assertions: `owner_assigned`, `workload_assigned`, `exact_approved_rights`, `rotation_current`, `review_current`.

Required `data` fields and invented positive values:

```json
{
  "owner_id": "DEMO-OWNER",
  "workload_id": "DEMO-WORKLOAD",
  "approved_right_ids": [
    "DEMO-READ"
  ],
  "actual_right_ids": [
    "DEMO-READ"
  ],
  "rotated_at": "2026-09-09T09:00:00+00:00",
  "observed_at": "2026-09-09T09:10:00+00:00",
  "rotation_due_at": "2026-09-09T09:30:00+00:00",
  "reviewed_at": "2026-09-09T09:00:00+00:00",
  "review_due_at": "2026-09-09T09:30:00+00:00"
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-ENG-002: `revision_review`

Draft procedure: Require peer review of the exact proposed revision; check separation from author and protected-branch rules; route emergency bypasses to the documented emergency workflow.

Computed assertions: `exact_revision`, `independent`, `approved`, `protected_branch`, `review_before_merge`.

Required `data` fields and invented positive values:

```json
{
  "reviewed_revision_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "merged_revision_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "reviewer_id": "DEMO-REVIEWER",
  "author_id": "DEMO-AUTHOR",
  "decision": "APPROVE",
  "protected_branch": true,
  "proposed_at": "2026-09-09T09:00:00+00:00",
  "reviewed_at": "2026-09-09T09:10:00+00:00",
  "merged_at": "2026-09-09T09:30:00+00:00"
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-ENG-003: `release_tests`

Draft procedure: Choose tests from change risk including security, privacy, recovery and data effects; bind results to the release artifact; block release on failed mandatory tests unless an authorized exception applies.

Computed assertions: `complete_mandatory_population`, `all_mandatory_passed`, `no_failed_mandatory`, `consistent_results`, `results_belong_to_execution`, `exact_artifact`, `before_release`.

Required `data` fields and invented positive values:

```json
{
  "required_test_ids": [
    "DEMO-SECURITY",
    "DEMO-RECOVERY"
  ],
  "executed_test_ids": [
    "DEMO-SECURITY",
    "DEMO-RECOVERY"
  ],
  "passed_test_ids": [
    "DEMO-SECURITY",
    "DEMO-RECOVERY"
  ],
  "failed_test_ids": [],
  "tested_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "released_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "built_at": "2026-09-09T09:00:00+00:00",
  "tested_at": "2026-09-09T09:10:00+00:00",
  "released_at": "2026-09-09T09:30:00+00:00"
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-ENG-004: `deployment_artifact`

Draft procedure: Release only approved artifacts using attributable deployment identities; reconcile pipeline runs with actual runtime versions and out-of-band changes; record target environment and rollback reference.

Computed assertions: `exact_artifact`, `authorized_deployer`, `environment`, `rollback_reference`, `chronology`.

Required `data` fields and invented positive values:

```json
{
  "approved_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "pipeline_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "runtime_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "deployment_identity_id": "DEMO-PIPELINE",
  "authorized_identity_ids": [
    "DEMO-PIPELINE"
  ],
  "approved_environment": "DEMO-PROD",
  "actual_environment": "DEMO-PROD",
  "rollback_reference": "DEMO-ROLLBACK",
  "approved_at": "2026-09-09T09:00:00+00:00",
  "deployed_at": "2026-09-09T09:10:00+00:00",
  "observed_at": "2026-09-09T09:30:00+00:00"
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-CFG-001: `asset_inventory`

Draft procedure: Record assets, software, services, owners, locations and lifecycle states at onboarding/change/retirement; reconcile identity, endpoint, network, provider and deployment discovery to inventory; resolve unowned resources.

Computed assertions: `discovery_reconciles`, `ownership_complete`, `current_reconciliation`.

Required `data` fields and invented positive values:

```json
{
  "discovered_asset_ids": [
    "DEMO-ASSET-A",
    "DEMO-ASSET-B"
  ],
  "registered_asset_ids": [
    "DEMO-ASSET-A",
    "DEMO-ASSET-B"
  ],
  "owned_asset_ids": [
    "DEMO-ASSET-A",
    "DEMO-ASSET-B"
  ],
  "discovered_at": "2026-09-09T09:00:00+00:00",
  "reconciled_at": "2026-09-09T09:10:00+00:00",
  "due_at": "2026-09-09T09:30:00+00:00"
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-REC-004: `disposal`

Draft procedure: At scheduled disposal or exit, check retention and holds; execute authorized deletion or destruction across active copies and documented backup lifecycle; retain certificates and investigate failed deletions.

Computed assertions: `no_hold`, `authorized`, `retention_elapsed`, `authorized_before_execution`, `active_copies_deleted`, `backup_lifecycle_recorded`, `certificate`.

Required `data` fields and invented positive values:

```json
{
  "legal_hold": false,
  "approver_id": "DEMO-RECORDS-OWNER",
  "authorized_approver_ids": [
    "DEMO-RECORDS-OWNER"
  ],
  "retention_ends_at": "2026-09-09T09:00:00+00:00",
  "disposed_at": "2026-09-09T09:10:00+00:00",
  "approved_at": "2026-09-09T09:00:00+00:00",
  "active_copy_ids": [
    "DEMO-COPY"
  ],
  "deleted_copy_ids": [
    "DEMO-COPY"
  ],
  "backup_lifecycle_reference": "DEMO-BACKUP-LIFECYCLE",
  "destruction_certificate_id": "DEMO-CERTIFICATE"
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-POL-003: `exception_validity`

Draft procedure: Record the exact requirement, rationale, risk, alternatives, compensating measure, approver and expiry; for HIPAA addressable measures document reasonableness and equivalent alternatives; block silent waivers and escalate expiry.

Computed assertions: `specific_requirement`, `authorized`, `unexpired`, `compensation_recorded`, `compensation_observed`.

Required `data` fields and invented positive values:

```json
{
  "requirement_id": "DEMO-REQUIREMENT",
  "approver_id": "DEMO-RISK-OWNER",
  "authorized_approver_ids": [
    "DEMO-RISK-OWNER"
  ],
  "approved_at": "2026-09-09T09:00:00+00:00",
  "effective_at": "2026-09-09T09:00:00+00:00",
  "observed_at": "2026-09-09T09:10:00+00:00",
  "expires_at": "2026-09-09T09:30:00+00:00",
  "compensating_measure_id": "DEMO-MEASURE",
  "compensation_operating": true
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-GOV-003: `delegated_decision`

Draft procedure: Publish reserved matters and approval limits; verify approving authority at each material decision; resolve conflicting or expired delegations before execution.

Computed assertions: `authorized_actor`, `matter_in_scope`, `within_limit`, `same_currency`, `unexpired`, `not_revoked`.

Required `data` fields and invented positive values:

```json
{
  "approver_id": "DEMO-DELEGATE",
  "delegate_id": "DEMO-DELEGATE",
  "matter_id": "DEMO-PURCHASE",
  "permitted_matter_ids": [
    "DEMO-PURCHASE"
  ],
  "decision_amount": 50,
  "delegated_limit": 100,
  "decision_currency": "DEMO-USD",
  "limit_currency": "DEMO-USD",
  "delegation_starts_at": "2026-09-09T09:00:00+00:00",
  "decided_at": "2026-09-09T09:10:00+00:00",
  "delegation_expires_at": "2026-09-09T09:30:00+00:00",
  "revoked": false
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-ETH-001: `conduct_acknowledgment`

Draft procedure: Distribute approved conduct expectations at onboarding and annually; reconcile the recipient population; follow up missing acknowledgments and route reported violations through protected channels.

Computed assertions: `exact_version`, `correct_recipient`, `timely`.

Required `data` fields and invented positive values:

```json
{
  "required_version": "DEMO-CODE-2",
  "acknowledged_version": "DEMO-CODE-2",
  "required_recipient_id": "DEMO-WORKER",
  "acknowledger_id": "DEMO-WORKER",
  "distributed_at": "2026-09-09T09:00:00+00:00",
  "acknowledged_at": "2026-09-09T09:10:00+00:00",
  "due_at": "2026-09-09T09:30:00+00:00"
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-SEC-002: `log_coverage`

Draft procedure: Inventory required log sources and detections; monitor ingestion and clock gaps; route alerts with severity and ownership; test representative detections and collection-loss alerts.

Computed assertions: `required_sources_reporting`, `ingestion_gap`, `clock_skew`, `measured_window`.

Required `data` fields and invented positive values:

```json
{
  "required_source_ids": [
    "DEMO-IDP",
    "DEMO-ENDPOINT"
  ],
  "reporting_source_ids": [
    "DEMO-IDP",
    "DEMO-ENDPOINT"
  ],
  "max_observed_gap_seconds": 10,
  "approved_gap_seconds": 60,
  "max_observed_skew_seconds": 1,
  "approved_skew_seconds": 5,
  "window_start": "2026-09-09T09:00:00+00:00",
  "window_end": "2026-09-09T09:10:00+00:00",
  "measured_at": "2026-09-09T09:30:00+00:00"
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-ASS-005: `corrective_retest`

Draft procedure: Assign severity, accountable role and due date when a finding opens; link corrective work and independent retest; escalate overdue items; retain original failures after closure.

Computed assertions: `assigned`, `independent_retest`, `timely_retest`, `retest_passed`, `original_failure_retained`.

Required `data` fields and invented positive values:

```json
{
  "owner_id": "DEMO-OWNER",
  "retester_id": "DEMO-REVIEWER",
  "implementer_id": "DEMO-ENGINEER",
  "opened_at": "2026-09-09T09:00:00+00:00",
  "fixed_at": "2026-09-09T09:10:00+00:00",
  "retested_at": "2026-09-09T09:30:00+00:00",
  "due_at": "2026-09-09T11:00:00+00:00",
  "retest_passed": true,
  "original_failure_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "retained_failure_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

### SH-PRD-003: `change_notice`

Draft procedure: Before material change, assess affected users, AI purposes and dependencies, limitations and contractual notice duties. Approve the change and communication plan; issue accurate notices to affected parties and retain delivery evidence. Reassess significant unplanned changes and failures.

Computed assertions: `all_required_recipients`, `exact_notice`, `approved_and_timely`, `required_lead_time`.

Required `data` fields and invented positive values:

```json
{
  "required_recipient_ids": [
    "DEMO-CUSTOMER-A",
    "DEMO-CUSTOMER-B"
  ],
  "delivered_recipient_ids": [
    "DEMO-CUSTOMER-A",
    "DEMO-CUSTOMER-B"
  ],
  "approved_notice_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "delivered_notice_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "approved_at": "2026-09-09T09:00:00+00:00",
  "delivered_at": "2026-09-09T09:10:00+00:00",
  "notice_due_at": "2026-09-09T09:30:00+00:00",
  "change_at": "2026-09-09T11:00:00+00:00",
  "required_lead_seconds": 1800
}
```

Human review remains required for the full draft procedure above, policy and authority validity, original source authenticity, independently reconciled populations, material exceptions, local boundary execution, and every BASE/additional criterion in the test plan. Each computed assertion is defined in `testing.automated`; the retained positive/negative records and tests permit reperformance.

## Demonstration and verification

`examples.build` produces two cases per adapter plus the existing prospective termination case (49 cases at 24 adapters). Its deliberate failures include exact revision/artifact substitution, excess or obsolete rights, expired access and exceptions, missing inventory/recipients, legal holds, excessive delegated amounts and modified original failure digests. Same-period retest preserves the original failed period. Independent prospective closure references a later passed case and retains failure history.

`tests/test_ccf_expanded_controls.py` additionally removes every new contract field, rejects null and wrong boolean/numeric/list/timestamp types, challenges inverted chronology and exclusive expiry, omitted inner populations, contradictory test outcomes and wrong record kinds. Existing workflow tests retain population, authentication, independent review and remediation coverage. The exact number of executed tests belongs to the closeout receipt rather than this document.
