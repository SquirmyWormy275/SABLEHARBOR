"""Pre-audit reference-runtime incident activity, not deployed-service evidence."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _id, _time
from .operating_source_bridge import encoded, sha
from .organization import snapshot


@dataclass(frozen=True)
class IncidentRecipe:
    company_id: str
    clean_branch: str
    messy_branch: str
    incident_id: str
    service_id: str
    period_start: str
    period_end_exclusive: str
    discovered_at: str
    request_count: int = 20
    error_count: int = 20
    local_error_threshold_percent: int = 50
    local_escalation_due_minutes: int = 10
    delayed_delivery_minutes: int = 35


def generate_incident(store: CompanyStore, *, repository: Path, recipe: IncidentRecipe):
    """Materialize matching inventories with one delayed escalation causal difference."""
    for value in [recipe.company_id, recipe.clean_branch, recipe.messy_branch, recipe.incident_id]:
        _id(value)
    if recipe.clean_branch == recipe.messy_branch:
        raise CompanyStoreError("Distinct isolated branches required")
    for field, low, high in [
        ("request_count", 1, 100),
        ("error_count", 1, 100),
        ("local_error_threshold_percent", 1, 100),
        ("local_escalation_due_minutes", 5, 30),
        ("delayed_delivery_minutes", 31, 120),
    ]:
        value = getattr(recipe, field)
        if type(value) is not int or not low <= value <= high:
            raise CompanyStoreError("Explicit bounded integer incident thresholds required")
    if (
        recipe.error_count > recipe.request_count
        or recipe.error_count * 100 < recipe.local_error_threshold_percent * recipe.request_count
    ):
        raise CompanyStoreError(
            "This incident adapter requires an observed local outage threshold breach"
        )
    start, end, discovered = [
        datetime.fromisoformat(_time(value))
        for value in [recipe.period_start, recipe.period_end_exclusive, recipe.discovered_at]
    ]
    if not start <= discovered - timedelta(days=1) < discovered + timedelta(days=4) < end:
        raise CompanyStoreError(
            "Inventory, incident and four-day action window must fit the source period"
        )
    service_data = json.loads((repository / "enterprise/services/source/services.json").read_text())
    service = next(
        (
            dict(zip(service_data["columns"], r, strict=True))
            for r in service_data["services"]
            if r[0] == recipe.service_id
        ),
        None,
    )
    if service is None or recipe.service_id != "SVC-compute":
        raise CompanyStoreError(
            "This reference slice is bounded to canonical production-compute service"
        )
    site_data = json.loads(
        (repository / "enterprise/services/source/runtime_sites_2026-09-11.json").read_text()
    )
    sites = {s["id"]: s for s in site_data["sites"]}
    source_sites = [sites["RUNTIME-RENO-COLO"], sites["RUNTIME-BOISE-DR"]]
    org = snapshot(repository, as_of=start.date().isoformat())
    assignments = {a["control_id"]: a for a in org["control_assignments"]}
    responder = assignments["SH-ENG-002"]["primary_person_id"]
    commander = assignments["SH-INC-001"]["primary_person_id"]
    reviewer = assignments["SH-INC-003"]["operating_reviewer_person_id"]
    if len({responder, commander, reviewer}) != 3:
        raise CompanyStoreError("Distinct response actors and outside-response reviewer required")
    pins = dict(org["source_sha256"])
    for p in [
        "enterprise/ccf/assurance/design_data/control_procedures.json",
        "enterprise/services/source/services.json",
        "enterprise/services/source/runtime_sites_2026-09-11.json",
        "docs/canon/RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md",
        "docs/internal/development/CCF_ASSURANCE_SCOPE_PROPOSAL_2026-09-11.md",
        "enterprise/audit_suite/company_incident_activity.py",
    ]:
        pins[p] = sha((repository / p).read_bytes())
    common = {
        "incident_id": recipe.incident_id,
        "service_id": recipe.service_id,
        "boundary_id": "corporate",
        "period_start": start.isoformat(),
        "period_end_exclusive": end.isoformat(),
        "origin": "FICTIONAL_REFERENCE_RUNTIME_ACTIVITY_NOT_PRODUCTION_EVIDENCE",
        "sites": [
            {
                "runtime_site_id": s["id"],
                "facility_id": s["facility_id"],
                "geospatial_site_id": s["geospatial_site_id"],
                "canonical_operating": s["operating"],
                "canonical_status": s["status"],
            }
            for s in source_sites
        ],
        "scenario_operating_basis": "Reference exercise only; no deployment assertion",
        "data_scope": "Synthetic nonpersonal probe payloads; no PHI/ePHI processing asserted",
        "actor_authority": "Scoped exercise contacts; no appointment acceptance",
        "local_policy_basis": "Fictional branch rules, not accepted corporate SLA/policy",
    }
    policy = {
        "id": recipe.incident_id + "-LOCAL-RULES",
        "error_threshold_percent": recipe.local_error_threshold_percent,
        "escalation_due_minutes": recipe.local_escalation_due_minutes,
        "response_requires_commander_ack": True,
        "recovery_probe_required_successes": 20,
        "recovery_checkpoint_age_limit_minutes": 5,
        "recovery_objective_minutes": 60,
        "outside_response_review_required": True,
        "action_completion_rule": "Demonstrate queued-page timeout escalation with a timed replay",
    }
    rows = []
    owners = {
        "inventory": commander,
        "monitoring": responder,
        "incident_ticket": commander,
        "escalation": responder,
        "status_updates": commander,
        "recovery": responder,
        "postincident_review": reviewer,
        "corrective_action": responder,
        "action_validation": reviewer,
        "dispatch_replay": responder,
    }
    for branch, send in [
        (recipe.clean_branch, 5),
        (recipe.messy_branch, recipe.delayed_delivery_minutes),
    ]:
        created = {}
        versions = {}

        def timestamp(minutes):
            return (discovered + timedelta(minutes=minutes)).isoformat()

        def add(system, minutes, body, links=(), created=created, versions=versions, branch=branch):
            version = versions.get(system, 0) + 1
            versions[system] = version
            references = [
                {
                    "system": name,
                    "record": f"{recipe.incident_id}-{name}",
                    "version": v,
                    "sha256": created[name, v]["sha256"],
                }
                for name, v in links
            ]
            content = {
                **common,
                "record_id": f"{recipe.incident_id}-{system}",
                "recorded_at": timestamp(minutes),
                "source_refs": references,
                **body,
            }
            raw = encoded(content)
            entry = {
                "branch": branch,
                "system": system,
                "record": content["record_id"],
                "version": version,
                "event_at": timestamp(minutes),
                "content": raw,
                "sha256": sha(raw),
            }
            created[system, version] = entry
            rows.append(entry)

        add(
            "inventory",
            -1440,
            {
                "local_rules": policy,
                "service_definition_state": service_data["record_defaults"],
                "scenario_assets": [
                    {"id": "LOCAL-RENO-PROBE", "site": "RUNTIME-RENO-COLO"},
                    {"id": "LOCAL-BOISE-PROBE", "site": "RUNTIME-BOISE-DR"},
                ],
                "recovery_administration": "Separate exercise credentials; no actual credentials",
                "responder": responder,
                "commander": commander,
                "outside_response_reviewer": reviewer,
            },
        )
        add(
            "monitoring",
            0,
            {
                "observation_id": recipe.incident_id + "-OBS1",
                "asset_id": "LOCAL-RENO-PROBE",
                "window_ends_at": timestamp(0),
                "requests": [
                    {
                        "request_id": f"PROBE-{i + 1:03d}",
                        "observed_at": timestamp(-(recipe.request_count - i) / 60),
                        "http_status": 503 if i < recipe.error_count else 200,
                    }
                    for i in range(recipe.request_count)
                ],
                "total_requests": recipe.request_count,
                "error_requests": recipe.error_count,
            },
            [("inventory", 1)],
        )
        add(
            "incident_ticket",
            1,
            {
                "state": "OPEN",
                "discovered_at": timestamp(0),
                "local_severity": "SEV1",
                "severity_basis": "Observed error percentage meets the local exercise threshold",
                "assigned_responder": responder,
                "commander": commander,
                "escalation_due_at": timestamp(recipe.local_escalation_due_minutes),
                "decision": "Initiate escalation; preserve probe and dispatch records",
            },
            [("monitoring", 1), ("inventory", 1)],
        )
        add(
            "escalation",
            5,
            {
                "dispatch_id": recipe.incident_id + "-PAGE",
                "queued_at": timestamp(5),
                "recipient": commander,
                "delivery_state": "DELIVERED" if send == 5 else "QUEUED",
                "delivered_at": timestamp(5) if send == 5 else None,
                "route": "local-primary-oncall",
                "actor": responder,
            },
            [("incident_ticket", 1)],
        )
        add(
            "escalation",
            send + 1,
            {
                "dispatch_id": recipe.incident_id + "-PAGE",
                "queued_at": timestamp(5),
                "delivered_at": timestamp(send),
                "acknowledged_at": timestamp(send + 1),
                "recipient": commander,
                "delivery_state": "ACKNOWLEDGED",
                "route": "local-primary-oncall" if send == 5 else "local-timeout-retry",
                "actor": responder,
            },
            [("escalation", 1)],
        )
        add(
            "incident_ticket",
            send + 2,
            {
                "state": "RECOVERING",
                "commander": commander,
                "decision": "Authorize simulated independent-site recovery",
                "authorized_at": timestamp(send + 2),
                "affected_runtime_site": "RUNTIME-RENO-COLO",
                "recovery_runtime_site": "RUNTIME-BOISE-DR",
            },
            [("escalation", 2)],
        )
        add(
            "status_updates",
            send + 3,
            {
                "audience": "Internal exercise service stakeholders",
                "sent_by": commander,
                "service_state": "UNAVAILABLE"
                if recipe.error_count == recipe.request_count
                else "DEGRADED",
                "recovery_state": "AUTHORIZED",
            },
            [("incident_ticket", 2)],
        )
        add(
            "recovery",
            send + 4,
            {
                "state": "STARTED",
                "performed_by": responder,
                "source_site": "RUNTIME-RENO-COLO",
                "target_site": "RUNTIME-BOISE-DR",
                "recovery_credential_ref": "LOCAL-SEPARATE-BOISE-ADMIN",
                "operation": "Activate scenario recovery endpoint",
            },
            [("incident_ticket", 2), ("inventory", 1)],
        )
        add(
            "monitoring",
            send + 19,
            {
                "observation_id": recipe.incident_id + "-OBS2",
                "asset_id": "LOCAL-BOISE-PROBE",
                "loaded_checkpoint_id": recipe.incident_id + "-CHECKPOINT",
                "checkpoint_captured_at": timestamp(send + 17),
                "checkpoint_observed_at": timestamp(send + 19),
                "total_requests": 20,
                "error_requests": 0,
                "requests": [
                    {
                        "request_id": f"RECOVERY-{i + 1:03d}",
                        "http_status": 200,
                        "observed_at": timestamp(send + 18 + i / 60),
                    }
                    for i in range(20)
                ],
            },
            [("recovery", 1)],
        )
        add(
            "recovery",
            send + 20,
            {
                "state": "VERIFIED_BY_RESPONDER",
                "verified_by": responder,
                "successful_probes": 20,
                "checkpoint_age_minutes": 2,
                "restored_at": timestamp(send + 19),
                "elapsed_minutes_from_discovery": send + 19,
                "independent_validation": "NOT_CLAIMED",
            },
            [("monitoring", 2), ("inventory", 1)],
        )
        add(
            "status_updates",
            send + 21,
            {
                "audience": "Internal exercise service stakeholders",
                "sent_by": commander,
                "service_state": "AVAILABLE",
                "restoration_observed_at": timestamp(send + 19),
            },
            [("recovery", 2)],
        )
        add(
            "incident_ticket",
            send + 22,
            {
                "state": "SERVICE_RESTORED_ACTIONS_PENDING",
                "commander": commander,
                "restored_at": timestamp(send + 19),
                "preserved_source_records": [r["record"] for r in created.values()],
            },
            [("status_updates", 2)],
        )
        add(
            "postincident_review",
            1440,
            {
                "reviewed_by": reviewer,
                "local_escalation_due_at": timestamp(recipe.local_escalation_due_minutes),
                "observed_delivery_at": timestamp(send),
                "observed_ack_at": timestamp(send + 1),
                "delivery_delay_minutes": send - 5,
                "observed_service_restoration_minutes": send + 19,
                "causal_assessment_status": "MANAGEMENT_INTERPRETATION_NOT_INDEPENDENT_ASSURANCE",
                "outage_cause": "NOT_ESTABLISHED_FROM_PROBE_RECORDS",
                "remaining_investigation": (
                    "Obtain authorized network/application diagnostic records"
                ),
                "contributing_condition": "Immediate route delivery"
                if send == 5
                else "Queued primary dispatch required delayed retry",
                "proposed_preventive_action": "Add queued-dispatch timeout and timed route replay",
                "risk_update": "Review dispatch dependency for this local service",
                "notification_applicability": "No regulated-data notice determination asserted",
            },
            [("escalation", 2), ("recovery", 2)],
        )
        add(
            "corrective_action",
            1441,
            {
                "state": "PLANNED",
                "owner": responder,
                "due_at": timestamp(4320),
                "completion_condition": policy["action_completion_rule"],
                "change": "Configure local queued-page timeout at three minutes",
            },
            [("postincident_review", 1)],
        )
        add(
            "corrective_action",
            2880,
            {
                "state": "IMPLEMENTED_PENDING_VALIDATION",
                "owner": responder,
                "change_record": recipe.incident_id + "-ROUTE-CHANGE",
                "timeout_minutes": 3,
            },
            [("corrective_action", 1)],
        )
        add(
            "dispatch_replay",
            2939,
            {
                "dispatch_id": recipe.incident_id + "-REPLAY",
                "actor": responder,
                "target": "LOCAL-TEST-RECEIVER",
                "queued_at": timestamp(2936),
                "fallback_delivered_at": timestamp(2939),
                "route": "LOCAL-QUEUED-PAGE-TIMEOUT",
                "timeout_minutes": 3,
                "delivery_state": "DELIVERED",
                "production_dispatch": False,
            },
            [("corrective_action", 2)],
        )
        add(
            "action_validation",
            2940,
            {
                "validated_by": reviewer,
                "procedure": "Replay a queued synthetic dispatch; inspect fallback timing",
                "replay_dispatch_id": recipe.incident_id + "-REPLAY",
                "queued_at": timestamp(2936),
                "fallback_delivered_at": timestamp(2939),
                "elapsed_minutes": 3,
                "expected_timeout_minutes": 3,
                "qualification_status": "NOT_ASSERTED",
            },
            [("corrective_action", 2), ("dispatch_replay", 1)],
        )
        add(
            "corrective_action",
            2941,
            {
                "state": "CLOSED_WITH_REPLAY_RECORD",
                "owner": responder,
                "completion_evidence": recipe.incident_id + "-action_validation",
            },
            [("action_validation", 1)],
        )
    expected = {(r["branch"], r["system"], r["record"], r["version"]) for r in rows}
    with store._db() as db:
        for r in db.execute("SELECT * FROM versions"):
            if (
                r["company"] != recipe.company_id
                or (r["branch"], r["system"], r["record"], r["version"]) not in expected
            ):
                raise CompanyStoreError("Dedicated empty or exact-replay source store required")
    for branch in (recipe.clean_branch, recipe.messy_branch):
        for system, owner in owners.items():
            store.register_system(recipe.company_id, branch, system, owner)
    receipts = []
    for r in rows:
        receipts.append(
            store.append_version(
                recipe.company_id,
                r["branch"],
                r["system"],
                r["record"],
                expected_version=r["version"] - 1,
                command_id="INC-"
                + sha(encoded([recipe.company_id, r["branch"], r["record"], r["version"]])),
                event_at=r["event_at"],
                available_at=r["event_at"],
                content=r["content"],
                provenance={
                    "source_reference": recipe.incident_id,
                    "source_sha256": pins,
                    "recipe_sha256": sha(encoded(asdict(recipe))),
                    "classification": "FICTIONAL_REFERENCE_EXERCISE_NOT_DEPLOYMENT",
                    "control_ids": ["SH-INC-001", "SH-INC-002", "SH-INC-003", "SH-INC-004"],
                },
            )
        )
    return {
        "source_versions": len(receipts),
        "receipts": receipts,
        "source_sha256": pins,
        "recipe_sha256": sha(encoded(asdict(recipe))),
        "audit_created": False,
        "grants_created": False,
        "professional_validation": "UNVALIDATED",
        "gaps": [
            "No deployment, PHI processing or legal notification determination.",
            "One incident and declared local service/asset inventory only.",
            "Outage root cause is not established; response-delay records do not diagnose it.",
            "Recovery probes are synthetic; production RTO/RPO acceptance remains separate.",
        ],
    }
