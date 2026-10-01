"""Neutral company originals are actually collected before twenty B03 inspections."""

import copy
import json

import pytest
from test_collected_byte_recovery_method import fixture, ordinary_inputs, reseal_document, row

from enterprise.audit_suite.collected_byte_recovery_method import reference
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.source_continuity_methods import History, contracts, examine, task_plan


def bcm(role, record, at, detail, priors=(), *, version=1):
    return row(
        "bcm." + role,
        record,
        at,
        {
            "schema": "NEUTRAL-DOCUMENTARY-CONTINUITY",
            "detail": detail,
            "local_prior_source_sha256": {
                (
                    f"{r['source']['record']}:"
                    f"{r['source']['system'].split('.', 1)[1]}:{r['source']['version']}"
                ): r["source"]["sha256"]
                for r in priors
            },
        },
        version=version,
    )


def neutral_originals():
    records, _ = fixture()
    inventory = bcm(
        "service_inventory",
        "SVC-COMPUTE",
        "2027-03-01T01:00:00Z",
        {
            "service_id": "SVC-COMPUTE",
            "dependencies": ["BACKUP-SELECTED", "BOISE-SELECTED"],
            "usable_it_kw": {"RENO": 30, "BOISE": 20},
            "population": "ONE_NEUTRAL_SERVICE_ONLY",
        },
    )
    forecast = bcm(
        "demand_forecast",
        "SVC-COMPUTE",
        "2027-03-02T01:00:00Z",
        {
            "expected_kw": {"RENO": 25, "BOISE": 15},
            "peak_kw": {"RENO": 35, "BOISE": 18},
            "action_threshold_kw": {"RENO": 29, "BOISE": 19},
            "measurement_status": "FORECAST_ONLY",
            "threshold_exceeded": False,
        },
        [inventory],
    )
    authority = bcm(
        "authority_decision",
        "SELECTED-SERVICE",
        "2027-03-03T01:00:00Z",
        {
            "scope": "NEUTRAL_LOCAL_TECHNICAL_TARGET_ONLY",
            "qualification": "NO_CUSTOMER_COMMITMENT",
        },
    )
    technical = bcm(
        "technical_objectives",
        "SVC-COMPUTE",
        "2027-03-04T01:00:00Z",
        {
            "proposed_rto_minutes": 30,
            "proposed_rpo_minutes": 5,
            "recovery_priority": 1,
            "capacity_action": "Investigate projected capacity shortage",
        },
        [forecast],
    )
    bia = bcm(
        "business_impact",
        "SVC-COMPUTE",
        "2027-03-05T01:00:00Z",
        {
            "rto_minutes": 30,
            "rpo_minutes": 5,
            "tolerable_interruption_minutes": 40,
            "accepted_local_objectives": True,
            "business_unit_and_customer_objectives_accepted": False,
        },
        [authority, technical],
    )
    plan = bcm(
        "exercise_plan",
        "MARKER-RECOVERY",
        "2027-03-06T01:00:00Z",
        {
            "scope": "ONE_NEUTRAL_NONPERSONAL_MARKER",
            "approved_emergency_ephi_access": False,
            "supplier_and_customer_participation": False,
        },
        [bia],
    )
    first = bcm(
        "exercise_result",
        "MARKER-RECOVERY",
        "2027-08-01T02:00:00Z",
        {
            "exercise_start_at": "2027-08-01T01:00:00Z",
            "observed_finish_at": "2027-08-01T02:00:00Z",
            "measured_restore_minutes_simulated": 60,
            "rto_target_minutes": 30,
            "rpo_target_minutes": 5,
            "measured_replay_gap_minutes_simulated": 1,
            "numeric_targets_met": True,
            "marker_digest_match": True,
            "data_usability": "COMPANY_CLAIM",
            "real_application_restored": False,
        },
        [plan],
    )
    second = bcm(
        "exercise_result",
        "MARKER-RECOVERY",
        "2027-08-02T01:20:00Z",
        {
            "exercise_start_at": "2027-08-02T01:00:00Z",
            "observed_finish_at": "2027-08-02T01:20:00Z",
            "measured_restore_minutes_simulated": 20,
            "rto_target_minutes": 30,
            "rpo_target_minutes": 5,
            "measured_replay_gap_minutes_simulated": 1,
            "numeric_targets_met": True,
            "marker_digest_match": True,
            "data_usability": "COMPANY_CLAIM",
            "real_application_restored": False,
        },
        [plan],
        version=2,
    )
    closure = bcm(
        "closure_gate",
        "CAPACITY-AND-KEY",
        "2027-08-03T01:00:00Z",
        {
            "corrective_action_validated": False,
            "historical_bypass_exception_open": True,
            "risk_acceptance": "NOT_PERFORMED",
            "capacity_treatment_open": True,
        },
        [second],
    )
    records += [inventory, forecast, authority, technical, bia, plan, first, second, closure]
    schedule = {
        "period_id": "NEUTRAL-BACKUP-DECLARATION",
        "period_start": "2027-05-01T00:00:00Z",
        "period_end_exclusive": "2027-05-03T00:00:00Z",
        "schedule": [
            {
                "id": "FAILED-BACKUP",
                "control_id": "SH-BCM-002",
                "inventory_ids": ["LOCAL-CONFIG"],
                "due_at": "2027-05-01T01:00:00Z",
                "window_start": "2027-05-01T00:00:00Z",
                "window_end_exclusive": "2027-05-02T00:00:00Z",
            },
            {
                "id": "MISSING-BACKUP",
                "control_id": "SH-BCM-002",
                "inventory_ids": ["LOCAL-CONFIG"],
                "due_at": "2027-05-02T01:00:00Z",
                "window_start": "2027-05-02T00:00:00Z",
                "window_end_exclusive": "2027-05-03T00:00:00Z",
            },
        ],
    }
    period = row(
        "period-history.operating_period_ledger",
        "OTHER-PERIOD",
        "2027-04-30T01:00:00Z",
        {"plan": schedule},
    )
    runtime = row(
        "backup-runtime-history.runtime_definition",
        "OTHER-RUNTIME",
        "2027-04-30T02:00:00Z",
        {
            "plan": schedule,
            "runtime_id": "NEUTRAL-OTHER-RUNTIME",
            "datasets": {"LOCAL-CONFIG": "NOT_OPENED"},
            "declaration_original_sha256": period["source"]["sha256"],
            "bindings": {
                "FAILED-BACKUP": {
                    "dataset_id": "LOCAL-CONFIG",
                    "occurrence_id": "FAILED-1",
                    "operation": "BACKUP",
                }
            },
        },
    )
    failed = row(
        "backup-runtime-history.backup_job",
        "FAILED-BACKUP",
        "2027-05-01T01:00:00Z",
        {
            "runtime_id": "NEUTRAL-OTHER-RUNTIME",
            "dataset_id": "LOCAL-CONFIG",
            "occurrence_id": "FAILED-1",
            "operation": "BACKUP",
            "business_attempted_at": "2027-05-01T01:00:00Z",
            "performed_by": "LOCAL-OPERATOR",
            "object_pin": None,
            "lease_pin": None,
            "error_code": "LOCAL_LEASE_UNAVAILABLE",
            "status": "FAILED",
        },
    )
    corrected = row(
        "backup-runtime-history.backup_job",
        "FAILED-BACKUP",
        "2027-05-01T01:30:00Z",
        {
            **json.loads(failed["content"]),
            "business_attempted_at": "2027-05-01T01:30:00Z",
            "error_code": None,
            "status": "CORRECTION_CLAIM_ONLY",
            "prior_attempt_pin": reference(failed["source"]),
        },
        version=2,
    )
    ticket = row(
        "backup-runtime-history.failure_ticket",
        "FAILED-BACKUP",
        "2027-05-01T01:01:00Z",
        {
            "job_pin": reference(failed["source"]),
            "status": "OPEN",
            "resolution": "NOT_RECORDED",
        },
    )
    return records + [period, runtime, failed, corrected, ticket]


def collect(tmp_path, originals):
    actual, context = ordinary_inputs(tmp_path, originals)
    return [
        dict(
            r,
            retained_bytes=r["content"],
            content_type="application/json",
            logical_family=r["source"]["system"].split(".", 1)[0],
            logical_system=r["source"]["system"].split(".", 1)[1],
        )
        for r in actual
    ], context


def by_clause(inspections, control, clause):
    return next(
        i for i in inspections if i["task_id"] == f"TASK-SH-BCM-{control}-corporate-{clause}"
    )


def test_exact_twenty_task_vector_has_distinct_kind_clause_contracts():
    plan = task_plan()
    assert len(plan) == len(contracts()) == 20
    assert [
        sum(t["control_id"] == f"SH-BCM-{c}" for t in plan) for c in ("001", "002", "003", "004")
    ] == [5, 4, 5, 6]
    assert len({c["performed"] for c in contracts().values()}) == 20
    assert len({t["task_id"] for t in plan}) == 20
    assert "TASK-SH-BCM-003-corporate-CHECK-SOC2:A1.3" in contracts()


def test_genuine_collection_reperformance_preserves_failures_and_missing_marker(tmp_path):
    rows, context = collect(tmp_path, neutral_originals())
    tmp_path.chmod(0o700)
    inspections = examine(rows, as_of=context.simulated_at, scratch_root=tmp_path)
    assert [i["task_id"] for i in inspections] == [t["task_id"] for t in task_plan()]
    capacity = by_clause(inspections, "001", "CHECK-SOC2:A1.1")
    assert capacity["disposition"]["conclusion"] == "FAIL"
    assert capacity["result"]["exceptions"][0]["facts"]["peak_exceeds_capacity"]
    timestamp = by_clause(inspections, "003", "CHECK-SOC2:A1.3")
    timing = timestamp["result"]["examined_attributes"]["recorded_timestamp_reperformance"]
    assert [o["recorded_elapsed_within_declared_rto"] for o in timing["observations"]] == [
        False,
        True,
    ]
    assert timestamp["disposition"]["conclusion"] == "FAIL"
    toe = by_clause(inspections, "003", "TOE")["result"]["examined_attributes"]
    performed = toe["actual_local_configuration_reperformance"]["selected_occurrences"][0]
    assert performed["real_isolated_byte_restore_performed"]
    assert not toe["actual_local_configuration_reperformance"][
        "august_marker_bytes_independently_restored"
    ]
    assert not performed["attributable_local_age"]["application_or_ephi_data_as_of_established"]
    backup = by_clause(inspections, "002", "TOE")["result"]["examined_attributes"]
    assert (
        backup["denominator_before_selection"]["missing_occurrences"][0]["occurrence_id"]
        == "MISSING-BACKUP"
    )
    population = backup["denominator_before_selection"]["population"][0]
    assert len(population["attempts"]) == 2 and population["attempts"][0]["recorded_failure"]
    assert backup["failure_and_monitor_lineage"]["recorded_failures"][-2]["exact_tickets"]
    emergency = by_clause(inspections, "004", "ACTION-H-EMERGENCY")["result"]["examined_attributes"]
    assert not emergency["ephi_access_activity_and_authorized_operator_execution_tested"]
    assert (
        len({json.dumps(i["result"]["examined_attributes"], sort_keys=True) for i in inspections})
        == 20
    )
    for inspection in inspections:
        assert inspection["disposition"]["status"] == "IN_PROGRESS"
        assert inspection["disposition"]["conclusion"] != "PASS"
        cited = set(inspection["artifact_ids"])
        assert all(
            e["artifact_id"] in cited for o in inspection["observations"] for e in o["evidence"]
        )
        assert all(0 < len(o["evidence"]) <= 20 for o in inspection["observations"])


@pytest.mark.parametrize("field", ["version", "content_bytes"])
def test_boolean_native_version_and_receipt_size_are_rejected_after_real_collection(
    tmp_path, field
):
    records, context = collect(tmp_path, neutral_originals())
    if field == "version":
        records[0]["source"]["version"] = True
    else:
        records[0]["receipt"]["content_bytes"] = True
    with pytest.raises(ProcedureError, match="custody"):
        History(records, context.simulated_at)


def test_body_cache_is_ignored_and_missing_bia_is_explicit_support_limit(tmp_path):
    records, context = collect(tmp_path, neutral_originals())
    for item in records:
        item["document"] = {
            "detail": {"measured_restore_minutes_simulated": 1},
            "cached_verdict": "PASS",
        }
    records = [r for r in records if r["source"]["system"] != "bcm.business_impact"]
    tmp_path.chmod(0o700)
    inspections = examine(records, as_of=context.simulated_at, scratch_root=tmp_path)
    result = by_clause(inspections, "003", "CHECK-SOC2:A1.3")["result"]["examined_attributes"]
    assert result["recorded_timestamp_reperformance"]["status"] == "SUPPORT_UNAVAILABLE"
    assert all(i["disposition"]["conclusion"] != "PASS" for i in inspections)


def test_resealed_backup_after_restore_stops_local_scratch_before_copy(tmp_path):
    originals = neutral_originals()
    selected = next(
        r
        for r in originals
        if r["source"]["system"] == "backup-runtime-history.backup_job"
        and r["source"]["record"] == "B1"
    )
    document = json.loads(selected["content"])
    document["business_attempted_at"] = "2027-02-07T01:00:00Z"
    reseal_document(selected, document)
    records, context = collect(tmp_path, originals)
    tmp_path.chmod(0o700)
    result = by_clause(
        examine(records, as_of=context.simulated_at, scratch_root=tmp_path), "003", "TOE"
    )
    restore = result["result"]["examined_attributes"]["actual_local_configuration_reperformance"][
        "selected_occurrences"
    ][0]
    assert restore["status"] == "SUPPORT_UNAVAILABLE"
    assert not restore["real_isolated_byte_restore_performed"]
    assert not (tmp_path / "BCM003-LOCAL-RESTORE-001").exists()


def test_wrong_native_restore_role_cannot_gain_copy_credit(tmp_path):
    originals = neutral_originals()
    selected = next(
        r for r in originals if r["source"]["system"] == "backup-runtime-history.restore_job"
    )
    selected["source"]["system"] = "backup-runtime-history.meeting_note"
    records, context = collect(tmp_path, originals)
    tmp_path.chmod(0o700)
    result = by_clause(
        examine(records, as_of=context.simulated_at, scratch_root=tmp_path), "003", "TOE"
    )
    assert (
        result["result"]["examined_attributes"]["actual_local_configuration_reperformance"][
            "selected_occurrences"
        ]
        == []
    )
    assert not (tmp_path / "BCM003-LOCAL-RESTORE-001").exists()


def test_reference_to_equal_body_wrong_role_remains_explicit_native_role_limit(tmp_path):
    originals = neutral_originals()
    ticket = next(
        r for r in originals if r["source"]["system"] == "backup-runtime-history.failure_ticket"
    )
    body = json.loads(ticket["content"])
    failed = next(
        r
        for r in originals
        if r["source"]["record"] == "FAILED-BACKUP" and r["source"]["version"] == 1
    )
    copied = copy.deepcopy(failed)
    copied["source"]["system"] = "backup-runtime-history.support_note"
    body["job_pin"] = reference(copied["source"])
    reseal_document(ticket, body)
    records, context = collect(tmp_path, originals + [copied])
    history = History(records, context.simulated_at)
    assert any(
        j["path"] == "$.job_pin" and j["status"] == "ACTUAL_NATIVE_ROLE_DIFFERS"
        for j in history.joins
    )


def test_retained_receipt_clock_cannot_exceed_actual_examination_clock(tmp_path):
    records, context = collect(tmp_path, neutral_originals())
    records[0]["receipt"]["simulated_as_of"] = "2028-01-04T09:00:00Z"
    with pytest.raises(ProcedureError, match="custody"):
        History(records, context.simulated_at)


def test_late_business_target_is_not_used_for_earlier_company_exercise(tmp_path):
    originals = neutral_originals()
    bia = next(r for r in originals if r["source"]["system"] == "bcm.business_impact")
    bia["source"]["available_at"] = "2027-09-01T09:00:00.000000+00:00"
    records, context = collect(tmp_path, originals)
    tmp_path.chmod(0o700)
    inspections = examine(records, as_of=context.simulated_at, scratch_root=tmp_path)
    result = by_clause(inspections, "003", "CHECK-SOC2:A1.3")["result"]["examined_attributes"]
    assert result["recorded_timestamp_reperformance"]["status"] == "SUPPORT_UNAVAILABLE"
    assert any(
        j["status"] == "SOURCE_UNAVAILABLE_AT_COMPANY_EVENT"
        for i in inspections
        for j in i["result"]["native_support"]
    )


def test_operation_body_cannot_override_real_native_job_type(tmp_path):
    originals = neutral_originals()
    original = next(
        r for r in originals if r["source"]["system"] == "backup-runtime-history.restore_job"
    )
    document = json.loads(original["content"])
    document["operation"] = "BACKUP"
    reseal_document(original, document)
    records, context = collect(tmp_path, originals)
    with pytest.raises(ProcedureError, match="operation kind"):
        examine(records, as_of=context.simulated_at, scratch_root=tmp_path)
    assert not (tmp_path / "BCM003-LOCAL-RESTORE-001").exists()


def test_runtime_job_agreement_cannot_satisfy_another_declared_due_occurrence(tmp_path):
    originals = neutral_originals()
    corrected = next(
        r
        for r in originals
        if r["source"]["record"] == "FAILED-BACKUP"
        and r["source"]["system"] == "backup-runtime-history.backup_job"
        and r["source"]["version"] == 2
    )
    raw_configuration = {"attempts": 2, "timeout_ms": 100, "max_total_ms": 200}
    captured = row(
        "backup-runtime-history.source_dataset",
        "LOCAL-CONFIG",
        "2027-05-01T01:29:00Z",
        raw_configuration,
    )
    copied = row(
        "backup-runtime-history.backup_object",
        "OTHER-COPY",
        "2027-05-01T01:30:00Z",
        raw_configuration,
    )
    lease = row(
        "backup-runtime-history.credential_event",
        "MAY-LEASE",
        "2027-04-30T03:00:00Z",
        {
            "enabled": True,
            "principal_id": "LOCAL-OPERATOR",
            "valid_from": "2027-04-30T00:00:00Z",
            "expires_at": "2027-05-03T00:00:00Z",
            "authority": "LOCAL_BYTE_BACKUP_ONLY",
        },
    )
    body = json.loads(corrected["content"])
    body.update(
        source_pin=reference(captured["source"]),
        object_pin=reference(copied["source"]),
        lease_pin=reference(lease["source"]),
    )
    reseal_document(corrected, body)
    records, context = collect(tmp_path, originals + [captured, copied, lease])
    tmp_path.chmod(0o700)
    inspection = by_clause(
        examine(records, as_of=context.simulated_at, scratch_root=tmp_path), "002", "TOE"
    )
    census = inspection["result"]["examined_attributes"]["denominator_before_selection"]
    second = census["population"][0]["attempts"][1]
    assert second["binding_matches"] and second["lease_enabled_bound_and_current"]
    assert second["input_output_bytes_equal"] and not second["recorded_failure"]
    assert not second["matches_exact_declared_due_occurrence"]
    assert any(e["attempt"]["source"]["version"] == 2 for e in census["exceptions"])
    assert any(o["id"].startswith("DECLARED-DUE-") for o in inspection["observations"])


def test_task_plan_pin_is_checked_before_any_scratch_copy(tmp_path, monkeypatch):
    from enterprise.audit_suite import source_continuity_methods as methods

    records, context = collect(tmp_path, neutral_originals())
    monkeypatch.setattr(methods, "PLAN_SHA", "0" * 64)
    with pytest.raises(ProcedureError, match="Exact B03 task instruction plan"):
        examine(records, as_of=context.simulated_at, scratch_root=tmp_path)
    assert not (tmp_path / "BCM003-LOCAL-RESTORE-001").exists()


@pytest.mark.parametrize(
    "interval",
    [
        ("2028-01-01T01:00:00Z", "2028-01-01T01:20:00Z"),
        ("2027-08-01T02:10:00Z", "2027-08-01T02:30:00Z"),
        ("2027-08-01T02:00:00Z", "2027-08-01T01:40:00Z"),
    ],
)
def test_reported_exercise_outside_native_occurrence_is_not_a_performed_interval(
    tmp_path, interval
):
    originals = neutral_originals()
    exercise = next(
        r
        for r in originals
        if r["source"]["system"] == "bcm.exercise_result" and r["source"]["version"] == 1
    )
    body = json.loads(exercise["content"])
    body["detail"]["exercise_start_at"], body["detail"]["observed_finish_at"] = interval
    body["detail"]["measured_restore_minutes_simulated"] = 20
    reseal_document(exercise, body)
    records, context = collect(tmp_path, originals)
    tmp_path.chmod(0o700)
    inspection = by_clause(
        examine(records, as_of=context.simulated_at, scratch_root=tmp_path),
        "003",
        "CHECK-SOC2:A1.3",
    )
    arithmetic = inspection["result"]["examined_attributes"]["recorded_timestamp_reperformance"]
    assert len(arithmetic["recorded_interval_chronology_exceptions"]) == 1
    assert (
        len(arithmetic["observations"]) == 1
        and arithmetic["observations"][0]["source"]["version"] == 2
    )
    refused = next(
        o for o in inspection["observations"] if o["id"].startswith("UNAVAILABLE-EXERCISE")
    )
    assert refused["status"] == "SUPPORT_UNAVAILABLE"
