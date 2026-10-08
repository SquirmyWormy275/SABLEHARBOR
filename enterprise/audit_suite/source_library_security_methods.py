"""Auditor reperformance over independently collected ordinary company records.

Logical aliases select a business family; exact projected custody stays in every
result. No branch expectations, authoring recipes or old audit observations are
inputs. These selected procedures always retain broader unperformed clauses.
"""

from __future__ import annotations

from datetime import datetime

from .company_store import _time
from .fresh_sec003_procedure import require
from .source_library_audit import BUSINESS_REFERENCE, exact_projected_reference


def custody(row):
    return {key: row["source"][key] for key in (*BUSINESS_REFERENCE, "imported_at")}


def selected(rows, family, system=None):
    return [
        row
        for row in rows
        if row["logical_family"] == family and (system is None or row["logical_system"] == system)
    ]


def one(rows, family, system, record=None):
    found = [
        row
        for row in selected(rows, family, system)
        if record is None or row["source"]["record"] == record
    ]
    require(len(found) == 1, "Selected method needs one exact native role/version")
    return found[0]


def before(row, cutoff):
    source = row["source"]
    return _time(source["available_at"]) <= _time(cutoff) and (
        source["event_at"] is None or _time(source["event_at"]) <= _time(cutoff)
    )


def model_scope(rows):
    require(
        all(
            isinstance(row["document"].get("operation_basis"), str)
            and row["document"]["operation_basis"].startswith("LOCAL_POLICY_AND_DATA_MODEL_ONLY")
            for row in rows
        ),
        "Selected security method requires explicit model-only source scope",
    )
    return sorted({row["document"]["operation_basis"] for row in rows})


def scalar_prior_joins(row, available_rows):
    """Resolve a native digest locator into separately collected actual custody."""
    joins = []
    for locator, digest in row["document"].get("local_prior_source_sha256", {}).items():
        parts = locator.rsplit(":", 2)
        record = parts[0]
        matches = [
            target
            for target in available_rows
            if target["source"]["record"] == record
            and target["source"]["sha256"] == digest
            and (
                len(parts) == 1
                or (
                    len(parts) == 3
                    and target["logical_system"] == parts[1]
                    and str(target["source"]["version"]) == parts[2]
                )
            )
        ]
        require(len(matches) == 1, "Native prior digest not uniquely collected")
        require(before(matches[0], row["source"]["event_at"]), "Prior source postdates event")
        joins.append({"locator": locator, "target": custody(matches[0])})
    return joins


def analyze_vulnerability(rows, plan):
    """Selected census + disclosed-advisory trace, preserving the OPS/EDGE gap."""
    inventory = one(rows, "sec005operated", "security_inventory", plan["inventory_record"])
    foundation = one(rows, "sec005operated", "security_baseline", plan["baseline_record"])
    assets = sorted(asset["id"] for asset in inventory["document"]["assets"])
    require(assets and len(set(assets)) == len(assets), "Selected inventory IDs must be distinct")
    require(
        sorted(foundation["document"]["selected_asset_ids"]) == assets,
        "Selected inventory and security baseline disagree",
    )
    sec = selected(rows, "sec003vuln")
    operation_basis = model_scope([*sec, inventory, foundation])
    records = {row["source"]["record"]: row for row in sec}
    require(len(records) == len(sec), "Vulnerability role has ambiguous native versions")
    initial = {
        role: one(sec, "sec003vuln", system, plan[role])
        for role, system in (
            ("census_record", "vulnerability_inventory"),
            ("scan_record", "vulnerability_scan"),
            ("scan_baseline_record", "vulnerability_baseline"),
            ("schedule_record", "vulnerability_schedule"),
            ("reconciliation_record", "vulnerability_reconciliation"),
        )
    }
    require(
        all(before(row, plan["snapshot_cutoff"]) for row in initial.values()),
        "Historical snapshot role unavailable at selected cutoff",
    )
    detail = {role: row["document"]["detail"] for role, row in initial.items()}
    sets = {
        "census": set(detail["census_record"]["observed_asset_ids"]),
        "baseline": set(detail["scan_baseline_record"]["covered_asset_ids"]),
        "schedule": set(detail["schedule_record"]["scheduled_asset_ids"]),
        "scan": set(detail["scan_record"]["observed_asset_ids"]),
    }
    require(
        all(values <= set(assets) for values in sets.values()),
        "Selected vulnerability population includes an unjoined asset",
    )
    advisory = one(sec, "sec003vuln", "vulnerability_advisory", plan["advisory_record"])
    affected = advisory["document"]["detail"]["advisory"]["affected_asset_id"]
    require(affected in assets, "Disclosed advisory is outside selected inventory")
    findings = set(detail["scan_record"]["finding_asset_ids"])
    missing = sorted(set(assets) - sets["scan"])
    contradictions = []
    for role, field, values in (
        ("census_record", "observed_count", sets["census"]),
        ("scan_record", "observed_count", sets["scan"]),
        ("scan_record", "reported_count", sets["scan"]),
        ("schedule_record", "reported_asset_count", sets["schedule"]),
    ):
        claimed = detail[role].get(field)
        if claimed is not None and claimed != len(values):
            contradictions.append(
                {
                    "source": custody(initial[role]),
                    "field": field,
                    "claimed": claimed,
                    "recalculated": len(values),
                }
            )
    scans = selected(sec, "sec003vuln", "vulnerability_scan")
    detections = [
        row for row in scans if affected in row["document"]["detail"].get("finding_asset_ids", [])
    ]
    require(detections, "Selected disclosed advisory has no collected detection")
    detection = min(detections, key=lambda row: row["source"]["event_at"])
    steps = []
    for system in ("vulnerability_triage", "vulnerability_approval", "vulnerability_remediation"):
        candidates = [
            row
            for row in selected(sec, "sec003vuln", system)
            if row["document"]["detail"].get("asset_id") == affected
        ]
        require(len(candidates) == 1, "Selected correction lacks unique native steps")
        steps.append(candidates[0])
    fix = steps[-1]
    retests = [
        row
        for row in scans
        if row["source"]["event_at"] > fix["source"]["event_at"]
        and affected not in row["document"]["detail"].get("finding_asset_ids", [])
    ]
    require(len(retests) == 1, "Selected correction lacks one exact later retest")
    trace = [advisory, detection, *steps, retests[0]]
    chronology = all(
        a["source"]["available_at"] <= b["source"]["event_at"]
        for a, b in zip(trace, trace[1:], strict=False)
    )
    advisory_available = before(advisory, initial["scan_record"]["source"]["event_at"])
    gap = advisory_available and affected in sets["scan"] and affected not in findings
    if gap:
        disposition = "UNEXPLAINED_FALSE_CLEAN"
        explanation = (
            "Omitted coverage and absence of a finding for an observed advisory target "
            "are distinct. No collected rule/parser mechanism proves a causal explanation."
        )
    elif not advisory_available:
        disposition = "ADVISORY_NOT_AVAILABLE_AT_INITIAL_SCAN"
        explanation = "The disclosed advisory was unavailable at the initial scan event."
    elif affected not in findings:
        disposition = "MISSED_ADVISORY_AND_COVERAGE_GAP_NO_PROVEN_CAUSE"
        explanation = "Coverage is missing; no collected mechanism establishes detection cause."
    else:
        disposition = "NO_SELECTED_DETECTION_CONTRADICTION"
        explanation = "The available selected advisory appears in the initial finding."
    upstream_joins = []
    for row in sec:
        for label, reference in (
            row["document"].get("upstream_native_refs_available_at_event", {}).items()
        ):
            target = exact_projected_reference(reference, rows)
            require(before(target, row["source"]["event_at"]), "Upstream source postdates event")
            upstream_joins.append(
                {"source": custody(row), "role": label, "target": custody(target)}
            )
    october_actor = initial["reconciliation_record"]["document"]["actor_id"]
    later_recons = [
        row
        for row in selected(sec, "sec003vuln", "vulnerability_reconciliation")
        if row["source"]["event_at"] > _time(plan["snapshot_cutoff"])
    ]
    return {
        "schema": "SH_LIBRARY_SEC003_REPERFORMANCE_V1",
        "population_anchor": inventory["artifact_id"],
        "population_rows": [{"id": asset} for asset in assets],
        "source_versions_tested": len(sec),
        "upstream_inventory": custody(inventory),
        "upstream_baseline": custody(foundation),
        "upstream_exact_version_joins": upstream_joins,
        "operation_basis": operation_basis,
        "snapshot_cutoff": _time(plan["snapshot_cutoff"]),
        "asset_census": [
            {"asset_id": asset, **{name: asset in values for name, values in sets.items()}}
            for asset in assets
        ],
        "count_contradictions": contradictions,
        "omitted_scan_assets": missing,
        "advisory_asset": affected,
        "advisory_asset_observed_in_snapshot": affected in sets["scan"],
        "advisory_asset_found_in_snapshot": affected in findings,
        "advisory_available_before_initial_scan": advisory_available,
        "causal_discrepancy": {
            "disposition": disposition,
            "omission_explains_missed_advisory": False if gap else None,
            "explanation": explanation,
        },
        "deep_trace": [custody(row) for row in trace],
        "approval_fix_retest_chronology_supported": chronology,
        "retest_selected_coverage_complete": set(
            retests[0]["document"]["detail"]["observed_asset_ids"]
        )
        == set(assets),
        "company_self_review_of_prior_reconciliation": any(
            row["document"]["actor_id"] == october_actor for row in later_recons
        ),
        "exception_history": [
            {"source": custody(row), "status": row["document"]["detail"].get("status")}
            for row in selected(sec, "sec003vuln", "vulnerability_exception")
        ],
        "conclusion": "LIMITATION",
        "actual_scanner_execution": False,
        "unperformed_clauses": [
            "Full enterprise/year inventory, baseline and scan populations",
            "Actual scanner/device execution and representative enterprise testing",
            "Independent reviewer acceptance and full exact-task scope acceptance",
        ],
    }


def analyze_security_publishers(rows, plan):
    """Compare selected baseline/application and publisher/collector/review populations.

    A native decision is a data-only model result, not an actual network connection
    or executed binary. Monitoring history does not perform a logging procedure.
    """
    sec = selected(rows, "sec005operated")
    operation_basis = model_scope(sec)
    inventory = one(sec, "sec005operated", "security_inventory", plan["inventory_record"])
    baseline = one(sec, "sec005operated", "security_baseline", plan["baseline_record"])
    application = one(sec, "sec005operated", "security_application", plan["application_record"])
    assets = sorted(asset["id"] for asset in inventory["document"]["assets"])
    required = set(baseline["document"]["agent_required_asset_ids"])
    require(required <= set(assets), "Required agents include an unjoined selected asset")
    interfaces = sorted(item["id"] for item in inventory["document"]["logical_interfaces"])
    probes = selected(sec, "sec005operated", "security_probe")
    monitor_results = []
    for monitor in selected(sec, "sec005operated", "security_monitor"):
        body = monitor["document"]
        month = monitor["source"]["event_at"][:7]
        published = [
            row
            for row in probes
            if row["source"]["event_at"][:7] == month and before(row, monitor["source"]["event_at"])
        ]
        published_ids = {row["source"]["record"] for row in published}
        require(len(published_ids) == len(published), "Ambiguous native publisher versions")
        received = set(body["received_probe_record_ids"])
        claimed = (
            set(body["publisher_probe_record_ids"])
            if "publisher_probe_record_ids" in body
            else None
        )
        agents = set(body["observed_agent_asset_ids"])
        monitor_results.append(
            {
                "source": custody(monitor),
                "month": month,
                "population_cutoff": monitor["source"]["event_at"],
                "native_publisher_ids": sorted(published_ids),
                "collector_ids": sorted(received),
                "publisher_claim_ids": sorted(claimed) if claimed is not None else None,
                "publisher_claim_available": claimed is not None,
                "unreceived_publisher_ids": sorted(published_ids - received),
                "collector_without_publisher_ids": sorted(received - published_ids),
                "publisher_claim_disagrees": claimed != published_ids
                if claimed is not None
                else None,
                "missing_required_agent_assets": sorted(required - agents),
                "unjoined_agent_assets": sorted(agents - set(assets)),
                "observed_interfaces": body.get("observed_interface_ids"),
                "independent_interface_coverage_tested": False,
                "published_versions": [custody(row) for row in published],
            }
        )
    review_results = []
    for review in selected(sec, "sec005operated", "security_reconciliation"):
        body = review["document"]
        if "reviewed_probe_record_ids" not in body:
            continue
        month = review["source"]["event_at"][:7]
        published = {
            row["source"]["record"]
            for row in probes
            if row["source"]["event_at"][:7] == month and before(row, review["source"]["event_at"])
        }
        reviewed = set(body["reviewed_probe_record_ids"])
        review_results.append(
            {
                "source": custody(review),
                "month": month,
                "population_cutoff": review["source"]["event_at"],
                "native_publisher_ids": sorted(published),
                "reviewed_publisher_ids": sorted(reviewed),
                "unreviewed_publisher_ids": sorted(published - reviewed),
                "reviewed_unjoined_ids": sorted(reviewed - published),
                "company_recorded_result": body.get("recorded_result"),
                "company_population_basis": body.get("population_basis"),
            }
        )
    approval_rows = [
        one(sec, "sec005operated", "security_approval", record)
        for record in plan["initial_approval_records"]
    ]
    require(approval_rows, "Preselected initial approval scope required")
    approval_clock = all(before(row, application["source"]["event_at"]) for row in approval_rows)
    application_joins = []
    for label, reference in application["document"].get("source_refs", {}).items():
        target = exact_projected_reference(reference, rows)
        require(before(target, application["source"]["event_at"]), "Application pointer is future")
        application_joins.append({"role": label, "target": custody(target)})
    return {
        "schema": "SH_LIBRARY_SEC005_PUBLISHER_REPERFORMANCE_V1",
        "population_anchor": inventory["artifact_id"],
        "population_rows": [{"id": asset} for asset in assets],
        "selected_asset_ids": assets,
        "selected_interface_ids": interfaces,
        "baseline": custody(baseline),
        "application": custody(application),
        "application_exact_version_joins": application_joins,
        "initial_selected_approvals": [custody(row) for row in approval_rows],
        "operation_basis": operation_basis,
        "approved_rule_intents": baseline["document"]["approved_rule_intents"],
        "applied_rule_intents": application["document"]["applied_rule_intents"],
        "initial_application_matches_approved_rules": application["document"][
            "applied_rule_intents"
        ]
        == baseline["document"]["approved_rule_intents"],
        "initial_missing_required_agent_assets": sorted(
            required - set(application["document"]["agent_covered_asset_ids"])
        ),
        "selected_approvals_available_before_application": approval_clock,
        "publisher_versions_tested": [custody(row) for row in probes],
        "monitor_reconciliations": monitor_results,
        "company_review_reconciliations": review_results,
        "exception_history": [
            {"source": custody(row), "document": row["document"]}
            for row in selected(sec, "sec005operated", "security_exception")
        ],
        "conclusion": "LIMITATION",
        "actual_packets_or_executable_execution": False,
        "logging_procedure_performed": False,
        "unperformed_clauses": [
            "Full enterprise/year host, endpoint, SaaS and network settings population",
            "Actual unauthorized connections across representative external interfaces (CC6.6)",
            "Actual installation restrictions, representative update coverage and "
            "unapproved executable test (CC6.8)",
            "Calendar-month tails after collector/review cutoff and full-period populations",
            "Log ingestion, clocks and detection/source-loss procedure under SEC002",
            "Independent reviewer acceptance and full exact-task scope acceptance",
        ],
    }


def analyze_continuity_timestamps(rows, plan):
    """Recompute recorded duration/target arithmetic without claiming a restore."""
    bcm = selected(rows, "bcm")
    results = [
        row
        for row in selected(bcm, "bcm", "exercise_result")
        if row["source"]["record"] == plan["exercise_record"]
    ]
    require(results, "Selected continuity exercise results are absent")
    bia = one(bcm, "bcm", "business_impact", plan["target_record"])
    technical = one(bcm, "bcm", "technical_objectives", plan["target_record"])
    authority = one(bcm, "bcm", "authority_decision", plan["authority_record"])
    local = bia["document"]["detail"]
    proposed = technical["document"]["detail"]
    prior_joins = [
        {"source": custody(row), "joins": scalar_prior_joins(row, bcm)}
        for row in [bia, technical, *results]
    ]
    observations = []
    for row in results:
        detail = row["document"]["detail"]
        start = datetime.fromisoformat(_time(detail["exercise_start_at"]))
        finish = datetime.fromisoformat(_time(detail["observed_finish_at"]))
        elapsed = (finish - start).total_seconds() / 60
        require(elapsed >= 0, "Recorded continuity finish precedes exercise start")
        recorded = detail["measured_restore_minutes_simulated"]
        observations.append(
            {
                "source": custody(row),
                "exercise_start_at": _time(detail["exercise_start_at"]),
                "observed_finish_at": _time(detail["observed_finish_at"]),
                "recalculated_minutes": elapsed,
                "company_recorded_minutes": recorded,
                "duration_claim_agrees": recorded == elapsed,
                "company_rto_target_minutes": detail["rto_target_minutes"],
                "company_rpo_target_minutes": detail["rpo_target_minutes"],
                "declared_targets_match_collected_local_bia": (
                    detail["rto_target_minutes"] == local["rto_minutes"]
                    and detail["rpo_target_minutes"] == local["rpo_minutes"]
                ),
                "collected_local_bia_available_before_exercise": before(
                    bia, detail["exercise_start_at"]
                ),
                "recorded_elapsed_within_declared_rto": elapsed <= detail["rto_target_minutes"],
                "company_reported_replay_gap_minutes": detail[
                    "measured_replay_gap_minutes_simulated"
                ],
                "independent_recovered_data_age_tested": False,
                "company_reported_data_usability": detail.get("data_usability"),
                "company_reported_marker_digest_match": detail.get("marker_digest_match"),
                "actual_restore_reperformed": False,
                "independent_data_usability_tested": False,
            }
        )
    return {
        "schema": "SH_LIBRARY_BCM_RECORDED_TIME_REPERFORMANCE_V1",
        "population_anchor": results[0]["artifact_id"],
        "population_rows": [
            {"id": f"{row['source']['record']}-v{row['source']['version']}"} for row in results
        ],
        "selected_exercise_record": plan["exercise_record"],
        "local_bia": {"source": custody(bia), "detail": local},
        "technical_objectives": {"source": custody(technical), "detail": proposed},
        "local_targets_match_technical_proposal": (
            local["rto_minutes"] == proposed["proposed_rto_minutes"]
            and local["rpo_minutes"] == proposed["proposed_rpo_minutes"]
        ),
        "local_authority": {
            "source": custody(authority),
            "detail": authority["document"]["detail"],
        },
        "prior_exact_digest_joins": prior_joins,
        "observations": observations,
        "target_authority_independently_accepted": False,
        "conclusion": "LIMITATION",
        "actual_restore_reperformed": False,
        "unperformed_clauses": [
            "Company-owned original marker/backup bytes not yet reachable through "
            "ordinary source collection",
            "Independent isolated restore, data age, integrity and usable recovered data tests",
            "Accepted BIA/target and scope authority reconciliation remains required",
            "Full corporate/ePHI recovery, identity/logging/supplier dependencies "
            "and actual site failure",
            "Independent reviewer acceptance and full exact-task scope acceptance",
        ],
    }
