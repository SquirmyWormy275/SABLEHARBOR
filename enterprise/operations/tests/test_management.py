"""Behavioral evidence for staffing, cost consumption and genuine forecast revisions."""

import copy
import json
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path

import pytest

from enterprise.business.model import BusinessModel, money
from enterprise.operations import management, workforce


class WorkforceModel(workforce.WorkforceMixin, BusinessModel):
    def __init__(self, inputs=None, operations_inputs=None):
        self.operations_inputs = (
            copy.deepcopy(operations_inputs)
            if operations_inputs is not None
            else {
                name: json.loads(
                    (Path(workforce.__file__).parent / "source" / f"{name}.json").read_text()
                )
                for name in ("workforce", "management")
            }
        )
        super().__init__(inputs)


@pytest.fixture(scope="module")
def model():
    return WorkforceModel().build()


def _position(model, month, position):
    return next(
        r
        for r in model.tables["workforce_positions_history"]
        if r["scenario"] == "base" and r["month_index"] == month and r["position_id"] == position
    )


def _result(model):
    months = defaultdict(lambda: defaultdict(D))
    journals = []
    for row in model.tables["journal"]:
        if row["unit"] != "corporate":
            continue
        key = row["scenario"], row["year"], row["month"]
        if row["account_type"] == "expense":
            months[key]["expense_usd"] += D(row["signed_usd"])
        elif row["account_type"] == "revenue":
            months[key]["revenue_usd"] -= D(row["signed_usd"])
    monthly = []
    for (scenario, year, month), values in months.items():
        for entity, fee in (("ARU", 50000), ("PS", 33333)):
            journals.append(
                {
                    "scenario": scenario,
                    "year": year,
                    "month": month,
                    "entity": entity,
                    "account": "SHARED_EXP",
                    "signed_usd": str(fee),
                }
            )
            journals.append(
                {
                    "scenario": scenario,
                    "year": year,
                    "month": month,
                    "entity": "SHI",
                    "account": "SHARED_REV",
                    "signed_usd": str(-fee),
                }
            )
            values["revenue_usd"] += fee
        monthly.append(
            {
                "scenario": scenario,
                "year": year,
                "month": month,
                "unit": "corporate",
                **{k: money(v) for k, v in values.items()},
            }
        )
    return {"journal_rows": journals, "unit_monthly_rows": monthly}


@pytest.fixture(scope="module")
def managed(model):
    candidate = copy.deepcopy(model)
    management.build(candidate, _result(candidate), model_factory=WorkforceModel)
    return candidate


def test_staffing_reconciles_and_preserves_canonical_authorization(model):
    result = workforce.validate(model)
    assert result["position_months"] == 591 * 60 * 3
    assert result["changes"] == 30
    assert len(model.roster) == 591
    assert sum(r["occupied"] for r in model.roster) == 506


def test_leave_is_paid_but_has_no_delivery_capacity(model):
    row = _position(model, 3, "SYN-ADVISORY-010")
    assert D(row["expected_loaded_cost_usd"]) > 0
    assert D(row["capacity_hours"]) == 0
    assert _position(model, 5, "SYN-ADVISORY-010")["leave_state"] == "ACTIVE"


def test_ramp_lowers_capacity_without_double_payroll(model):
    first = _position(model, 7, "SYN-FOUNDRY-FIELD-161")
    final = _position(model, 9, "SYN-FOUNDRY-FIELD-161")
    assert 0 < D(first["capacity_hours"]) < D(final["capacity_hours"])
    assert first["expected_loaded_cost_usd"] == final["expected_loaded_cost_usd"]
    assert D(final["ramp_fraction"]) == 1


def test_exit_and_replacement_are_effective_dated(model):
    exit_row = _position(model, 9, "SYN-FOUNDRY-FIELD-005")
    replacement = _position(model, 10, "SYN-FOUNDRY-FIELD-005")
    assert not exit_row["occupied"] and D(exit_row["expected_loaded_cost_usd"]) == 0
    assert replacement["person_id"] == "SYN-PERSON-FF-REPLACEMENT-005"


def test_borrowed_assignment_changes_capacity_without_second_salary(model):
    rows = [
        r
        for r in model.tables["workforce_assignments"]
        if r["scenario"] == "base"
        and r["month_index"] == 8
        and r["position_id"] == "SYN-WILLOW-003"
    ]
    assert {r["unit"] for r in rows} == {"willow", "advisory"}
    assert sum(D(r["assignment_fte"]) for r in rows) == 1
    assert sum(D(r["loaded_cost_usd"]) for r in rows) == D(12500)


@pytest.mark.parametrize(
    "change, message",
    [
        (
            {
                "month": 1,
                "action": "JOIN",
                "position_id": "SYN-FOUNDRY-FIELD-001",
                "person_id": "NEW",
            },
            "vacant",
        ),
        (
            {
                "month": 1,
                "action": "JOIN",
                "position_id": "SYN-FOUNDRY-FIELD-161",
                "person_id": "SYN-PERSON-FOUNDRY-FIELD-001",
            },
            "already occupies",
        ),
        (
            {"month": 1, "action": "RETURN", "position_id": "SYN-ADVISORY-010"},
            "transition",
        ),
        (
            {
                "month": 1,
                "action": "ASSIGNMENT_TRANSFER",
                "position_id": "SYN-J2-001",
                "assignments": {"advisory": "1"},
            },
            "staffing reserve",
        ),
        (
            {
                "month": 1,
                "action": "ASSIGNMENT_TRANSFER",
                "position_id": "SYN-WILLOW-003",
                "assignments": {"willow": "0.9"},
            },
            "sum to one",
        ),
        ({"month": 61, "action": "LEAVE", "position_id": "SYN-ADVISORY-010"}, "period"),
    ],
)
def test_invalid_workforce_changes_fail_before_authorizing_capacity(change, message):
    candidate = WorkforceModel()
    candidate.operations_inputs["workforce"]["events"] = [dict(change, change_id="BAD")]
    with pytest.raises(ValueError, match=message):
        candidate.build()


def test_payroll_tamper_is_detected(model):
    candidate = copy.deepcopy(model)
    candidate.tables["workforce_assignments"][0]["loaded_cost_usd"] = "99999"
    with pytest.raises(ValueError, match="payroll"):
        workforce.validate(candidate)


def test_missing_position_month_is_detected(model):
    candidate = copy.deepcopy(model)
    candidate.tables["workforce_positions_history"].pop()
    with pytest.raises(ValueError, match="population is incomplete"):
        workforce.validate(candidate)


def test_unreciprocated_statutory_fee_is_rejected(model):
    candidate = copy.deepcopy(model)
    result = _result(candidate)
    result["journal_rows"] = [r for r in result["journal_rows"] if r["account"] != "SHARED_REV"]
    with pytest.raises(ValueError, match="not reciprocal"):
        management._services(candidate, result)


def test_all_four_cost_pools_reconcile_and_do_not_post(managed, model):
    assert managed.tables["journal"] == model.tables["journal"]
    assert len(managed.tables["service_cost_pools"]) == 720
    assert len(managed.tables["service_consumption_allocations"]) == 5760
    assert all(
        D(r["difference_usd"]) == 0 for r in managed.tables["management_cost_reconciliation"]
    )
    assert all(
        D(r["retained_j2_mission_usd"]) > 0
        for r in managed.tables["management_cost_reconciliation"]
    )


def test_statutory_fees_credited_only_to_original_recipients(managed):
    credits = defaultdict(D)
    for row in managed.tables["service_consumption_allocations"]:
        if row["scenario"] == "base" and row["period"].startswith("2027-01"):
            credits[row["unit"]] += D(row["statutory_fee_credit_usd"])
    assert credits["pale-sun"] == 33333
    assert credits["american-resource-utility"] == 50000
    assert sum(credits.values()) == 83333


def test_rebuilt_vintages_are_distinct_and_first_six_months_frozen(managed):
    register = managed.tables["forecast_vintage_register"]
    assert len({r["input_sha256"] for r in register}) == 3
    assert all(r["rebuild_state"] == "MODEL_EXECUTED" for r in register)
    for row in managed.tables["forecast_variance_contributions"]:
        if row["period"] <= "2027-06-30":
            assert row["prior_usd"] == row["revised_usd"]
    for driver in ("price", "volume", "timing", "workforce"):
        assert any(
            D(r[f"{driver}_contribution_usd"])
            for r in managed.tables["forecast_variance_contributions"]
        )


def test_forecast_waterfall_tamper_is_detected(managed):
    candidate = copy.deepcopy(managed)
    candidate.tables["forecast_variance_contributions"][-1]["price_contribution_usd"] = "10"
    with pytest.raises(ValueError, match="attribution"):
        management.validate(candidate)


def test_cash_vintage_is_explicitly_requested_core_cash(managed):
    assert all(
        r["cash_basis"] == "CORE_REQUESTED_CASH_BEFORE_ENTERPRISE_TREASURY"
        for r in managed.tables["forecast_vintage_register"]
    )
    assert "requested_cash_flow_usd" in {
        r["metric"] for r in managed.tables["forecast_vintage_metrics"]
    }


def test_missing_or_negative_service_consumption_is_rejected():
    with pytest.raises(ValueError, match="positive"):
        management._allocate(D(100), {"a": D(0)})
    with pytest.raises(ValueError, match="nonnegative"):
        management._allocate(D(100), {"a": D(-1), "b": D(3)})


def test_monthly_allocation_tamper_is_detected(managed):
    candidate = copy.deepcopy(managed)
    candidate.tables["service_consumption_allocations"][0]["allocation_usd"] = "99999"
    with pytest.raises(ValueError, match="credit bridge"):
        management.validate(candidate)
