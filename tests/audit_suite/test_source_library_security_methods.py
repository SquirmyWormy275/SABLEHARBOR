"""Neutral scoped records challenge conclusions, joins and model-only limits."""

import copy
import hashlib
import json

import pytest

from enterprise.audit_suite.company_store import _time
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.source_library_audit import BUSINESS_REFERENCE
from enterprise.audit_suite.source_library_security_execution import authored_instruction
from enterprise.audit_suite.source_library_security_methods import (
    analyze_continuity_timestamps,
    analyze_security_publishers,
    analyze_vulnerability,
)


def row(family, system, record, day, document, *, version=1):
    if family.startswith("sec"):
        document = {
            "operation_basis": "LOCAL_POLICY_AND_DATA_MODEL_ONLY; NO_LIVE_EXECUTION",
            **document,
        }
    raw = json.dumps(document, sort_keys=True).encode()
    return {
        "source": {
            "company": "EXAMPLE",
            "branch": "OPERATING",
            "system": family + "." + system,
            "record": record,
            "version": version,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "event_at": _time(day + "T10:00:00Z"),
            "available_at": _time(day + "T10:01:00Z"),
            "imported_at": _time("2026-09-30T10:00:00Z"),
        },
        "artifact_id": f"ART-{family}-{system}-{record}-v{version}",
        "artifact_sha256": hashlib.sha256(raw).hexdigest(),
        "logical_family": family,
        "logical_system": system,
        "document": document,
    }


def pointer(target):
    return {key: target["source"][key] for key in BUSINESS_REFERENCE}


def vulnerability_fixture():
    assets = ["EDGE", "OPS"]
    inventory = row(
        "sec005operated",
        "security_inventory",
        "INV",
        "2027-09-01",
        {"assets": [{"id": asset} for asset in assets]},
    )
    baseline = row(
        "sec005operated", "security_baseline", "BASE", "2027-09-02", {"selected_asset_ids": assets}
    )
    rows = [inventory, baseline]
    for system, record, day, detail in [
        (
            "vulnerability_inventory",
            "CENSUS",
            "2027-10-01",
            {"observed_asset_ids": ["EDGE"], "observed_count": 2},
        ),
        ("vulnerability_baseline", "SCAN-BASE", "2027-10-02", {"covered_asset_ids": ["EDGE"]}),
        (
            "vulnerability_schedule",
            "SCHEDULE",
            "2027-10-03",
            {"scheduled_asset_ids": ["EDGE"], "reported_asset_count": 2},
        ),
        (
            "vulnerability_advisory",
            "ADVISORY",
            "2027-10-04",
            {"advisory": {"affected_asset_id": "EDGE"}},
        ),
        (
            "vulnerability_scan",
            "SCAN",
            "2027-10-05",
            {
                "observed_asset_ids": ["EDGE"],
                "observed_count": 1,
                "reported_count": 2,
                "finding_asset_ids": [],
            },
        ),
        ("vulnerability_reconciliation", "REVIEW", "2027-10-06", {}),
        (
            "vulnerability_scan",
            "DETECTION",
            "2027-11-01",
            {"observed_asset_ids": assets, "finding_asset_ids": ["EDGE"]},
        ),
        ("vulnerability_triage", "TRIAGE", "2027-11-02", {"asset_id": "EDGE"}),
        ("vulnerability_approval", "APPROVE", "2027-11-03", {"asset_id": "EDGE"}),
        ("vulnerability_remediation", "FIX", "2027-11-04", {"asset_id": "EDGE"}),
        (
            "vulnerability_scan",
            "RETEST",
            "2027-11-05",
            {"observed_asset_ids": assets, "finding_asset_ids": []},
        ),
        ("vulnerability_reconciliation", "LATER-REVIEW", "2027-11-06", {}),
    ]:
        rows.append(
            row(
                "sec003vuln",
                system,
                record,
                day,
                {
                    "actor_id": "company-reviewer",
                    "detail": detail,
                    "upstream_native_refs_available_at_event": {
                        "inventory": pointer(inventory),
                        "baseline": pointer(baseline),
                    },
                },
            )
        )
    plan = {
        "inventory_record": "INV",
        "baseline_record": "BASE",
        "census_record": "CENSUS",
        "scan_record": "SCAN",
        "scan_baseline_record": "SCAN-BASE",
        "schedule_record": "SCHEDULE",
        "reconciliation_record": "REVIEW",
        "advisory_record": "ADVISORY",
        "snapshot_cutoff": "2027-10-31T23:59:59Z",
    }
    return rows, plan


def test_observed_edge_advisory_and_omitted_ops_do_not_get_an_invented_cause():
    rows, plan = vulnerability_fixture()
    result = analyze_vulnerability(rows, plan)
    assert result["omitted_scan_assets"] == ["OPS"]
    assert result["advisory_asset_observed_in_snapshot"]
    assert result["causal_discrepancy"]["disposition"] == "UNEXPLAINED_FALSE_CLEAN"
    assert result["causal_discrepancy"]["omission_explains_missed_advisory"] is False
    assert len(result["count_contradictions"]) == 3
    assert result["approval_fix_retest_chronology_supported"]
    assert result["company_self_review_of_prior_reconciliation"]
    assert len(result["upstream_exact_version_joins"]) == 24
    assert result["conclusion"] == "LIMITATION" and not result["actual_scanner_execution"]


def test_advisory_unavailable_at_initial_scan_does_not_become_a_missed_existing_rule():
    rows, plan = vulnerability_fixture()
    advisory = next(r for r in rows if r["source"]["record"] == "ADVISORY")
    advisory["source"]["available_at"] = _time("2027-10-07T10:00:00Z")
    result = analyze_vulnerability(rows, plan)
    assert not result["advisory_available_before_initial_scan"]
    assert result["causal_discrepancy"]["disposition"] == "ADVISORY_NOT_AVAILABLE_AT_INITIAL_SCAN"


def test_vulnerability_pointer_cannot_join_by_alias_or_changed_digest():
    rows, plan = vulnerability_fixture()
    target = rows[2]["document"]["upstream_native_refs_available_at_event"]["inventory"]
    target["sha256"] = "0" * 64
    with pytest.raises(ProcedureError, match="hash or clocks"):
        analyze_vulnerability(rows, plan)


def security_fixture():
    inventory = row(
        "sec005operated",
        "security_inventory",
        "INV",
        "2027-09-01",
        {
            "assets": [{"id": "EDGE"}, {"id": "OPS"}],
            "logical_interfaces": [{"id": "EGRESS"}],
        },
    )
    baseline = row(
        "sec005operated",
        "security_baseline",
        "BASE",
        "2027-09-02",
        {
            "agent_required_asset_ids": ["EDGE", "OPS"],
            "approved_rule_intents": ["FLOW-RULE"],
        },
    )
    approvals = [
        row("sec005operated", "security_approval", name, day, {})
        for name, day in [("TECH", "2027-09-03"), ("SEC", "2027-09-04"), ("LATE-FIX", "2027-11-01")]
    ]
    application = row(
        "sec005operated",
        "security_application",
        "APPLY",
        "2027-09-05",
        {
            "applied_rule_intents": ["FLOW-RULE"],
            "agent_covered_asset_ids": ["EDGE", "OPS"],
            "source_refs": {"SEC": pointer(approvals[1]), "BASE": pointer(baseline)},
        },
    )
    probes = [
        row("sec005operated", "security_probe", name, day, {"decision": "LOCAL_POLICY_MODEL_DENY"})
        for name, day in [("P1", "2027-10-06"), ("P2", "2027-10-07")]
    ]
    monitor = row(
        "sec005operated",
        "security_monitor",
        "MONITOR",
        "2027-10-08",
        {
            "publisher_probe_record_ids": ["P1"],
            "received_probe_record_ids": ["P1"],
            "observed_agent_asset_ids": ["EDGE"],
        },
    )
    review = row(
        "sec005operated",
        "security_reconciliation",
        "REVIEW",
        "2027-10-09",
        {
            "reviewed_probe_record_ids": ["P1"],
            "recorded_result": "company-selected-pass",
        },
    )
    return [inventory, baseline, *approvals, application, *probes, monitor, review], {
        "inventory_record": "INV",
        "baseline_record": "BASE",
        "application_record": "APPLY",
        "initial_approval_records": ["TECH", "SEC"],
    }


def test_publisher_population_is_independent_of_collector_and_late_correction_approval():
    rows, plan = security_fixture()
    result = analyze_security_publishers(rows, plan)
    monitor = result["monitor_reconciliations"][0]
    assert monitor["native_publisher_ids"] == ["P1", "P2"]
    assert monitor["unreceived_publisher_ids"] == ["P2"]
    assert monitor["publisher_claim_disagrees"]
    assert monitor["missing_required_agent_assets"] == ["OPS"]
    assert result["company_review_reconciliations"][0]["unreviewed_publisher_ids"] == ["P2"]
    assert result["selected_approvals_available_before_application"]
    assert result["conclusion"] == "LIMITATION"
    assert not result["actual_packets_or_executable_execution"]
    assert not result["logging_procedure_performed"]


def test_unqualified_source_cannot_be_treated_as_a_model_with_live_credit():
    rows, plan = security_fixture()
    del rows[-1]["document"]["operation_basis"]
    with pytest.raises(ProcedureError, match="model-only"):
        analyze_security_publishers(rows, plan)


def test_absent_publisher_claim_stays_unknown_while_native_publishers_still_reconcile():
    rows, plan = security_fixture()
    del rows[-2]["document"]["publisher_probe_record_ids"]
    monitor = analyze_security_publishers(rows, plan)["monitor_reconciliations"][0]
    assert monitor["publisher_claim_ids"] is None
    assert monitor["publisher_claim_disagrees"] is None
    assert monitor["publisher_claim_available"] is False
    assert monitor["native_publisher_ids"] == ["P1", "P2"]
    assert monitor["unreceived_publisher_ids"] == ["P2"]


def continuity_fixture():
    authority = row(
        "bcm",
        "authority_decision",
        "AUTH",
        "2027-04-01",
        {
            "detail": {
                "excludes": [
                    "customer SLA",
                    "ePHI emergency-mode authorization",
                    "enterprise risk acceptance",
                ],
            }
        },
    )
    technical = row(
        "bcm",
        "technical_objectives",
        "SERVICE",
        "2027-04-02",
        {
            "detail": {
                "proposed_rto_minutes": 240,
                "proposed_rpo_minutes": 15,
                "real_recovery_performance_proven": False,
            }
        },
    )
    bia = row(
        "bcm",
        "business_impact",
        "SERVICE",
        "2027-04-03",
        {
            "detail": {
                "rto_minutes": 240,
                "rpo_minutes": 15,
                "accepted_local_objectives": True,
                "business_unit_and_customer_objectives_accepted": False,
            },
            "local_prior_source_sha256": {
                "AUTH": authority["source"]["sha256"],
                "SERVICE:technical_objectives:1": technical["source"]["sha256"],
            },
        },
    )
    plan_source = row("bcm", "exercise_plan", "MARKER", "2027-07-01", {"detail": {}})
    results = []
    for version, finish, reported in [(1, "12:35:00", 156), (2, "11:00:00", 60)]:
        day = f"2027-08-0{version}"
        results.append(
            row(
                "bcm",
                "exercise_result",
                "MARKER",
                day,
                {
                    "detail": {
                        "exercise_start_at": day + "T10:00:00Z",
                        "observed_finish_at": day + "T" + finish + "Z",
                        "measured_restore_minutes_simulated": reported,
                        "measured_replay_gap_minutes_simulated": 8,
                        "rto_target_minutes": 240,
                        "rpo_target_minutes": 15,
                        "marker_digest_match": True,
                        "data_usability": "COMPANY_REPORTED_READABLE",
                        "numeric_targets_met": True,
                    },
                    "local_prior_source_sha256": {
                        "MARKER:exercise_plan:1": plan_source["source"]["sha256"]
                    },
                },
                version=version,
            )
        )
    other = copy.deepcopy(results[0])
    other["source"]["record"] = "OTHER"
    return [authority, technical, bia, plan_source, *results, other], {
        "exercise_record": "MARKER",
        "target_record": "SERVICE",
        "authority_record": "AUTH",
    }


def test_recorded_duration_and_exact_versions_do_not_establish_restore_or_data_usability():
    rows, plan = continuity_fixture()
    result = analyze_continuity_timestamps(rows, plan)
    assert result["population_rows"] == [{"id": "MARKER-v1"}, {"id": "MARKER-v2"}]
    assert result["observations"][0]["recalculated_minutes"] == 155
    assert not result["observations"][0]["duration_claim_agrees"]
    assert result["observations"][1]["duration_claim_agrees"]
    assert result["local_targets_match_technical_proposal"]
    assert all(o["declared_targets_match_collected_local_bia"] for o in result["observations"])
    assert not result["actual_restore_reperformed"]
    assert not result["target_authority_independently_accepted"]
    assert all(not o["independent_data_usability_tested"] for o in result["observations"])
    assert result["conclusion"] == "LIMITATION"


def test_continuity_prior_digest_join_rejects_a_replacement_or_absent_original():
    rows, plan = continuity_fixture()
    rows[2]["document"]["local_prior_source_sha256"]["AUTH"] = "0" * 64
    with pytest.raises(ProcedureError, match="prior digest"):
        analyze_continuity_timestamps(rows, plan)


def test_base_toe_and_additional_duty_instructions_use_their_authored_locations():
    state = {
        "tasks": [
            {"id": "BASE", "kind": "TOE", "control_id": "CONTROL"},
            {"id": "CHECK", "kind": "ADDITIONAL_DUTY", "test": "Exact additional duty"},
        ],
        "controls": [
            {
                "id": "CONTROL",
                "procedure": "Exact base procedure",
                "base_test": "Exact base test",
                "population_rule": "Exact population rule",
            }
        ],
    }
    assert authored_instruction(state, "BASE") == {
        "task_kind": "TOE",
        "procedure": "Exact base procedure",
        "base_test": "Exact base test",
        "population_rule": "Exact population rule",
    }
    assert authored_instruction(state, "CHECK") == {
        "task_kind": "ADDITIONAL_DUTY",
        "test": "Exact additional duty",
    }
    del state["controls"][0]["base_test"]
    with pytest.raises(ProcedureError, match="base control"):
        authored_instruction(state, "BASE")
