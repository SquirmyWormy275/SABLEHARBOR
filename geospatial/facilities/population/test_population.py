"""Mutation tests target substantive double-counting and authority failures."""

import copy
import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "population_build", Path(__file__).with_name("build.py")
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_current_bridge_reconciles():
    data = MODULE.build()
    assert not MODULE.validate(data)
    assert data["totals"]["current_named_people"] == 51
    assert data["totals"]["current_named_employees"] == 44
    assert data["j2"]["unnamed_authorized_billets"] == 231


def test_duplicate_person_is_rejected():
    data = MODULE.build()
    data["people"].append(copy.deepcopy(data["people"][0]))
    assert "duplicate person_id" in MODULE.validate(data)


def test_board_employee_conflation_is_rejected():
    data = MODULE.build()
    data["totals"]["current_named_employees"] = 51
    assert any("named rollup" in e for e in MODULE.validate(data))


def test_education_cannot_be_added_twice():
    data = MODULE.build()
    data["j2"]["authorized_billets"] += 35
    assert any("vertical rollup" in e for e in MODULE.validate(data))


def test_shared_person_cannot_occupy_two_j2_groups():
    data = MODULE.build()
    data["j2"]["groups"][1]["named_person_ids"].append("P065")
    assert "J2 person assigned to multiple arms" in MODULE.validate(data)


def test_unnamed_is_not_vacant():
    data = MODULE.build()
    data["j2"]["groups"][0]["confirmed_vacancies"] = 77
    assert "unnamed billets conflated with vacancy/occupancy" in MODULE.validate(data)


def test_forecast_cannot_be_promoted_to_current_year():
    data = MODULE.build()
    data["conditional_forecast"]["year"] = 2026
    assert "forecast promoted into actuals" in MODULE.validate(data)


def test_industrial_horizontal_rollup():
    data = MODULE.build()
    data["industrial"]["values"]["bst"] += 1
    assert "ARU overlap" in MODULE.validate(data)


def test_unknown_company_population_cannot_be_filled_by_sum():
    data = MODULE.build()
    data["totals"]["actual_company_headcount"] = 44 + 271 + 237
    assert any("unsupported actual total" in e for e in MODULE.validate(data))


def test_source_drift_is_rejected():
    data = MODULE.build()
    path = next(iter(data["source_revision"]["source_sha256"]))
    data["source_revision"]["source_sha256"][path] = "0" * 64
    assert any("stale source" in e for e in MODULE.validate(data))


def test_runtime_requirement_is_not_payroll():
    data = MODULE.build()
    rt = data["runtime"]
    assert rt["proposed_technical_fte"] == 20
    assert rt["sacramento_workstations_required"] == 16
    assert rt["site_roving_positions"] == 4
    assert rt["owned_conditional_facilities_fte"] == 2
    assert rt["owned_conditional_guard_positions"] == 6
    assert data["totals"]["current_named_employees"] == 44
    rt["actual_runtime_employees"] = 20
    assert "runtime proposed workforce conflated with actual" in MODULE.validate(data)


def test_runtime_location_rollup_rejects_double_count():
    data = MODULE.build()
    data["runtime"]["site_roving_positions"] = 20
    assert "runtime location rollup" in MODULE.validate(data)


def test_runtime_compute_population_is_not_census():
    data = MODULE.build()
    data["runtime"]["compute_users_are_employee_census"] = True
    assert "runtime compute users conflated with census" in MODULE.validate(data)


def test_runtime_seat_allocation_cannot_invent_capacity():
    data = MODULE.build()
    data["runtime"]["conditional_seat_allocation"]["allocations"][1]["workstations"] = 16
    assert "runtime seat allocation exceeds existing capacity" in MODULE.validate(data)


def test_runtime_proposal_cannot_authorize_hires():
    data = MODULE.build()
    data["runtime"]["authorized_new_positions"] = 20
    assert any("runtime unsupported employment" in e for e in MODULE.validate(data))
