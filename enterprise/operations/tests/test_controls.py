"""Negative checks for source evidence, completeness, and independent closure."""

import json
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from enterprise.operations.controls import (
    REQUIRED,
    TABLES,
    build_controls,
    date_for,
    evaluate,
    validate,
)


def model_fixture():
    source = Path(__file__).parents[1] / "source/controls.json"
    model = SimpleNamespace(
        operations_inputs={"controls": json.loads(source.read_text())},
        policy={"cases": {"base": {}}, "years": 1},
        tables=defaultdict(list),
    )
    for month in (2, 3, 5, 6):
        common = {"scenario": "base", "period": date_for(month), "unit": "advisory"}
        performance = f"ACCEPTANCE-{month}"
        invoice = f"INVOICE-{month}"
        model.tables["events"].extend(
            [
                common | {"event_id": performance, "kind": "OUTCOME_ACCEPTED"},
                common
                | {
                    "event_id": invoice,
                    "kind": "INVOICE",
                    "performance_source": performance,
                    "amount_usd": "100",
                },
            ]
        )
        model.tables["journal"].extend(
            [
                common
                | {
                    "journal_id": f"J-{month}",
                    "source_id": invoice,
                    "account": "BIZ_AR",
                    "signed_usd": "100",
                },
                common
                | {
                    "journal_id": f"J-{month}",
                    "source_id": invoice,
                    "account": "BIZ_REVENUE",
                    "signed_usd": "-100",
                },
            ]
        )
        model.tables["subledger_rollforward"].append(
            common | {"gross_ar_usd": "100", "deferred_revenue_usd": "0", "allowance_usd": "1"}
        )
    return model


def built():
    model = model_fixture()
    build_controls(model, {})
    return model


def result(model, month, control="LC-REVENUE", unit="advisory"):
    return next(
        r
        for r in model.tables["control_results"]
        if r["local_control_id"] == control and r["unit"] == unit and r["month_index"] == month
    )


def test_expected_population_is_scheduled_independently_of_evidence():
    model = built()
    assert len(model.tables["control_registry"]) == 42
    assert len(model.tables["control_occurrences"]) == 42 * 12
    assert result(model, 1)["result"] == "NOT_RUN"
    assert result(model, 2)["result"] == "PASS"
    assert result(model, 3)["result"] == "FAIL"
    assert validate(model)["source_population_integrity"] == "EXACT_REPERFORMANCE"


def test_all_ten_controls_keep_existing_ccf_mappings():
    model = built()
    rows = model.tables["control_registry"]
    assert {r["local_control_id"] for r in rows} == set(REQUIRED)
    assert all(r["common_control_id"].startswith("SH-") for r in rows)
    assert all(r["production_effectiveness"] == "NOT_ASSERTED" for r in rows)


def test_waiver_expires_and_self_review_cannot_close():
    model = built()
    states = {r["state"]: r for r in model.tables["control_actions"]}
    assert states["WAIVER_EXPIRED_ESCALATED"]["month_index"] == 4
    assert states["SELF_REVIEW_REJECTED"]["month_index"] == 5
    assert states["CLOSED_BY_INDEPENDENT_RETEST"]["month_index"] == 6
    rejected, accepted = model.tables["control_retests"]
    assert rejected["reperformed_outcome"] == accepted["reperformed_outcome"] == "PASS"
    assert rejected["independent"] is False
    assert accepted["independent"] is True
    assert accepted["original_period"] == date_for(3)
    assert result(model, 3)["result"] == "FAIL"


def test_bad_original_source_cannot_close_on_later_months_pass():
    model = model_fixture()
    model.tables["journal"][2]["signed_usd"] = "101"
    build_controls(model, {})
    assert result(model, 6)["result"] == "PASS"
    assert model.tables["control_retests"][-1]["state"] == "RETEST_FAILED_REMAINS_OPEN"
    assert model.tables["control_retests"][-1]["reperformed_outcome"] == "FAIL"


def test_configuration_pass_label_is_not_retest_evidence():
    model = model_fixture()
    model.operations_inputs["controls"]["exception_exercises"][0]["retest_result"] = "PASS"
    model.tables["journal"][2]["signed_usd"] = "101"
    build_controls(model, {})
    assert model.tables["control_retests"][-1]["state"] == "RETEST_FAILED_REMAINS_OPEN"


@pytest.mark.parametrize("table", TABLES)
def test_exported_records_cannot_be_relabelled_or_omitted(table):
    model = built()
    model.tables[table].pop()
    with pytest.raises(ValueError, match="changed"):
        validate(model)


def test_live_source_change_invalidates_frozen_population_hash():
    model = built()
    model.tables["journal"][0]["signed_usd"] = "101"
    with pytest.raises(ValueError, match="changed"):
        validate(model)


def test_validation_does_not_repair_tampered_output():
    model = built()
    result(model, 3)["result"] = "PASS"
    with pytest.raises(ValueError):
        validate(model)
    assert result(model, 3)["result"] == "PASS"


def test_empty_and_unsupported_evidence_never_passes():
    assert evaluate("LC-ESTIMATE", {})[0] == "NOT_RUN"
    assert (
        evaluate("LC-ESTIMATE", {"forecast_variance_contributions": [{"result": "PASS"}]})[0]
        == "NOT_RUN"
    )


def test_variance_is_recalculated_from_components():
    row = {
        "prior_usd": "100",
        "revised_usd": "110",
        "price_contribution_usd": "10",
        "volume_contribution_usd": "0",
        "timing_contribution_usd": "0",
        "workforce_contribution_usd": "0",
        "vintage_id": "revised",
        "difference_usd": "0",
    }
    assert evaluate("LC-ESTIMATE", {"forecast_variance_contributions": [row]})[0] == "PASS"
    row["price_contribution_usd"] = "11"
    assert evaluate("LC-ESTIMATE", {"forecast_variance_contributions": [row]})[0] == "FAIL"


def test_credit_equation_and_allowance_ignore_fabricated_pass():
    history = {
        "invoice_amount_usd": "100",
        "remaining_usd": "50",
        "collected_usd": "50",
        "refunded_usd": "0",
        "writtenoff_usd": "0",
        "recovered_usd": "0",
        "writtenoff_credit_usd": "0",
        "credit_usd": "0",
        "amount_usd": "50",
        "due_date": "2027-02-28",
        "result": "PASS",
    }
    pops = {
        "credit_history": [history],
        "credit_allowance": [{"gross_ar_usd": "50", "rate": "0.02", "allowance_usd": "1"}],
        "subledger_rollforward": [{"gross_ar_usd": "50", "allowance_usd": "1"}],
    }
    assert evaluate("LC-CREDIT", pops)[0] == "PASS"
    history["collected_usd"] = "51"
    assert evaluate("LC-CREDIT", pops)[0] == "FAIL"


def test_source_scope_does_not_borrow_other_units_evidence():
    model = built()
    assert result(model, 2, unit="foundry-field")["result"] == "NOT_RUN"
    assert result(model, 2, unit="advisory")["result"] == "PASS"


def test_expired_waiver_cannot_be_scheduled_after_retest():
    model = model_fixture()
    model.operations_inputs["controls"]["exception_exercises"][0]["waiver_end_month"] = 7
    with pytest.raises(ValueError, match="chronology"):
        build_controls(model, {})


def test_self_authorized_reviewer_is_rejected():
    model = model_fixture()
    exercise = model.operations_inputs["controls"]["exception_exercises"][0]
    exercise["reviewer"] = exercise["preparer"]
    with pytest.raises(ValueError, match="independent"):
        build_controls(model, {})


def test_missing_original_attachment_population_prevents_closure():
    model = model_fixture()
    model.tables["journal"] = [r for r in model.tables["journal"] if r["period"] != date_for(3)]
    build_controls(model, {})
    assert result(model, 3)["result"] == "NOT_RUN"
    assert model.tables["control_retests"][-1]["state"] == "RETEST_FAILED_REMAINS_OPEN"


def test_payroll_capitalization_does_not_create_false_payroll_exception():
    pops = {
        "workforce_positions_history": [
            {"position_id": "P1", "person_id": "S1", "occupied": True, "authorized": True}
        ],
        "workforce_assignments": [
            {
                "person_id": "S1",
                "assignment_fte": "1",
                "loaded_cost_usd": "100",
                "unit": "project-cradle",
                "home_group": "project-cradle",
            }
        ],
        "events": [
            {"event_id": "PAY", "kind": "PAYROLL_REQUEST"},
            {"event_id": "CAP", "kind": "RECOVERY_RUN"},
        ],
        "journal": [
            {"source_id": "PAY", "account": "BIZ_PAYROLL", "signed_usd": "100"},
            {"source_id": "CAP", "account": "BIZ_PAYROLL", "signed_usd": "-25"},
        ],
    }
    assert evaluate("LC-WORKFORCE", pops)[0] == "PASS"
    pops["journal"][0]["signed_usd"] = "101"
    assert evaluate("LC-WORKFORCE", pops)[0] == "FAIL"


def test_industrial_capacity_is_rederived_despite_status_label():
    service = {
        "segment": "TRUCKING",
        "service_date": "2027-01-02",
        "provider": "OWNED",
        "required_resource_hours": "8",
    }
    shift = {
        "segment": "TRUCKING",
        "service_date": "2027-01-02",
        "crew_hours_available": "10",
        "equipment_hours_available": "9",
        "interface_hours_reserved": "1",
        "maintenance_downtime_hours": "0",
        "net_available_hours": "8",
        "service_hours_requested": "8",
        "over_capacity_hours": "0",
        "capacity_state": "PASS",
    }
    reconciliation = {
        "source_quantity": "1",
        "detail_quantity": "1",
        "source_amount_usd": "100",
        "detail_amount_usd": "100",
    }
    pops = {
        "industrial_service_detail": [service],
        "industrial_shift_capacity": [shift],
        "industrial_detail_reconciliation": [reconciliation],
    }
    assert evaluate("LC-INDUSTRIAL", pops)[0] == "PASS"
    shift["maintenance_downtime_hours"] = "1"
    assert evaluate("LC-INDUSTRIAL", pops)[0] == "FAIL"


def test_rights_failure_blocks_work_even_when_gate_claims_allowed():
    names = (
        "acceptance",
        "scope",
        "competence",
        "conflicts",
        "rights",
        "economics",
        "review",
        "stop",
    )
    controls = [
        {"engagement_id": "E1", "control": name, "result": "PASS", "source_id": "ACCEPTANCE"}
        for name in names
    ]
    gate = {
        "engagement_id": "E1",
        "client_id": "C1",
        "gate_status": "ALLOWED",
        "work_allowed": True,
        "billing_allowed": True,
        "recognition_allowed": True,
    }
    pops = {"matter_gate_decisions": [gate], "matter_controls": controls}
    assert evaluate("LC-ATLAS", pops)[0] == "PASS"
    next(r for r in controls if r["control"] == "rights")["result"] = "FAIL"
    assert evaluate("LC-ATLAS", pops)[0] == "FAIL"
    gate.update(
        gate_status="BLOCKED", work_allowed=False, billing_allowed=False, recognition_allowed=False
    )
    assert evaluate("LC-ATLAS", pops)[0] == "PASS"


def test_recovered_material_cannot_escape_genealogy_reconciliation():
    assay = {
        "run_id": "RUN-1",
        "contained_kg": "10",
        "recovered_kg": "5",
        "allocated_cost_usd": "20",
        "bypass": False,
    }
    edge = {
        "edge_type": "CAPTURE_MERGE",
        "parent_id": "RUN-1",
        "mass_basis": "RECOVERED_KG",
        "quantity": "5",
        "cost_usd": "20",
    }
    pops = {
        "recovery_run_assays": [assay],
        "recovery_genealogy": [edge],
        "inventory_rollforward": [{"closing_cost_usd": "20"}],
    }
    assert evaluate("LC-RECOVERY", pops)[0] == "PASS"
    edge["quantity"] = "4"
    assert evaluate("LC-RECOVERY", pops)[0] == "FAIL"


def test_invalid_invoice_due_date_is_not_a_successful_test():
    pops = {
        "credit_history": [{"remaining_usd": "1", "due_date": "2027-02-31", "amount_usd": "1"}],
        "credit_allowance": [{"gross_ar_usd": "1", "rate": "0", "allowance_usd": "0"}],
        "subledger_rollforward": [{"gross_ar_usd": "1", "allowance_usd": "0"}],
    }
    assert evaluate("LC-CREDIT", pops)[0] == "NOT_RUN"
