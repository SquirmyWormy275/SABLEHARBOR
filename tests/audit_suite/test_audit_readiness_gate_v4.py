"""The reviewed V16/V13 delta remains blocked over V3's exact 43 controls."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import audit_readiness_gate_v4 as gate

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def inputs():
    return {
        key: json.loads(((PRIVATE if scope == "private" else REPOSITORY) / relative).read_text())
        for key, (scope, relative, _) in gate.PINS.items()
        if key in {"v3_report", "v16_portfolio", "v16_candidate_report", "v16_route", "pbc_v13"}
    }


def _assemble(data):
    return gate._assemble(
        data["v3_report"],
        data["v16_portfolio"],
        data["v16_candidate_report"],
        data["v16_route"],
        data["pbc_v13"],
    )


def test_v4_retains_all_v3_blockers_and_false_readiness(inputs):
    report = _assemble(inputs)
    old = inputs["v3_report"]
    assert report["schema"] == gate.SCHEMA
    assert report["as_of"] == "2026-10-01"
    assert set(report["blockers_by_family_control"]) == set(old["blockers_by_family_control"])
    for family, controls in old["blockers_by_family_control"].items():
        assert set(report["blockers_by_family_control"][family]) == set(controls)
        for control, item in controls.items():
            current = report["blockers_by_family_control"][family][control]
            assert current["remaining_gates"] == item["remaining_gates"]
            assert set(current["route_limits"]) == set(item["route_limits"])
    assert sum(len(x) for x in report["blockers_by_family_control"].values()) == 43
    assert all(report[key] is False for key in gate.READINESS_FALSE)
    assert report["accepted_na_determinations"] == report["external_messages_sent"] == 0
    assert report["p1_freeze"] == gate.P1_FREEZE


def test_new_source_route_request_denominators_and_gov_gap(inputs):
    report = _assemble(inputs)
    assert len(report["source_roster"]) == 37
    assert report["source_roster"][:36] == inputs["v3_report"]["source_roster"]
    assert report["source_roster"][-1]["source"] == "prdconcern"
    assert len(report["candidate_source_pins"]["A"]) == 38
    assert report["sides"]["A"] == report["sides"]["B"]
    for side in "AB":
        count = report["sides"][side]
        assert (count["source_cohorts"], count["native_business_versions"]) == (37, 840)
        assert (count["targeted_routes"], count["partial_routes"], count["design_routes"]) == (
            183,
            141,
            21,
        )
        assert count["unsupported_exact_clauses"] == 121
        assert count["route_targeted_unsupported_clauses"] == 37
        assert count["pbc_targeted_unsupported_clauses"] == 35
        assert count["source_affected_unsupported_clauses"] == 27
        assert count["draft_unsent_request_groups"] == 30
        assert count["unaccepted_no_event_candidates"] == 53
        assert count["p1_tasks_not_started_not_run"] == 409
        assert {
            task
            for task in report["route_pbc_synchronization_pending_task_ids"]
            if task.startswith(f"{side}:")
        } == {f"{side}:{task}" for task in gate.GOV_AUTHORED}
    assert all(group["status"] == "DRAFT_NOT_SENT" for group in report["request_groups"])


def test_prd_held_and_gov_source_limits_remain_visible(inputs):
    report = _assemble(inputs)
    for side in "AB":
        for task in gate.PRD_AUTHORED:
            control = task.split("-corporate-")[0][5:]
            item = report["blockers_by_family_control"]["product_customer_commitments"][control]
            row = item["route_limits"][f"{side}:{task}"]
            assert row["pbc_v13_reviewed_source_ids"] == ["PRD_CONCERN_HELD_V1"]
            assert row["v15_source_limits"]["PRD_CONCERN_HELD_V1"]
            assert f"{side}:{task}" in item["unsupported_task_ids"]
        for task in gate.GOV_AUTHORED:
            control = task.split("-corporate-")[0][5:]
            item = report["blockers_by_family_control"]["risk_assurance_governance"][control]
            row = item["route_limits"][f"{side}:{task}"]
            assert row["targeted_source_ids"] == ["GOV_SELECTED_OVERSIGHT_V1"]
            assert row["pbc_v13_reviewed_source_ids"] == []
            assert f"{side}:{task}" in item["route_pbc_sync_pending_task_ids"]


def test_tampered_readiness_or_source_snapshot_fails(inputs):
    changed = deepcopy(inputs)
    changed["v3_report"]["audit_ready"] = True
    with pytest.raises(gate.GateError, match="claim boundary"):
        _assemble(changed)
    changed = deepcopy(inputs)
    changed["v16_portfolio"]["sources"][-1]["fictional_accepted_deliveries"] = 1
    with pytest.raises(gate.GateError, match="held gate"):
        _assemble(changed)
    changed = deepcopy(inputs)
    changed["v16_candidate_report"]["sides"]["A"]["source_pins"][0]["sha256"] = "0" * 64
    with pytest.raises(gate.GateError, match="candidate/source prefix"):
        _assemble(changed)


def test_route_pbc_or_p1_drift_fails(inputs):
    changed = deepcopy(inputs)
    row = next(
        row
        for row in changed["v16_route"]["rows"]
        if row["side"] == "A" and row["task_id"] in gate.GOV_AUTHORED
    )
    row["targeted_integrated_source_ids"] = []
    with pytest.raises(gate.GateError, match="denominator differs"):
        _assemble(changed)
    changed = deepcopy(inputs)
    row = next(
        row
        for row in changed["pbc_v13"]["rows"]
        if row["side"] == "B" and row["task_id"] in gate.GOV_AUTHORED
    )
    row["v13_targeted_source_ids"] = ["GOV_SELECTED_OVERSIGHT_V1"]
    with pytest.raises(gate.GateError, match="denominator differs"):
        _assemble(changed)
    changed = deepcopy(inputs)
    changed["pbc_v13"]["active_p1_tasks"]["B"]["status"] = "STARTED"
    with pytest.raises(gate.GateError, match="frozen P1 task status"):
        _assemble(changed)


def test_changed_review_pin_fails_before_build(monkeypatch):
    pins = dict(gate.PINS)
    scope, relative, _ = pins["pbc_v13_review"]
    pins["pbc_v13_review"] = (scope, relative, "0" * 64)
    monkeypatch.setattr(gate, "PINS", pins)
    with pytest.raises(gate.GateError, match="pinned SHA-256 differs"):
        gate._load_pins(REPOSITORY, PRIVATE)


def test_read_only_build_matches_snapshot_join(inputs):
    assert gate.build(REPOSITORY, PRIVATE) == _assemble(inputs)


def test_private_output_round_trip_and_tamper_rejection(tmp_path, monkeypatch, inputs):
    expected = _assemble(inputs)
    monkeypatch.setattr(gate, "build", lambda *_: expected)
    destination = tmp_path / "REPORT"
    destination.parent.chmod(0o700)
    assert gate.write(REPOSITORY, PRIVATE, destination) == expected
    assert gate.verify(destination, REPOSITORY, PRIVATE) == expected
    (destination / "REPORT.json").write_text(json.dumps({**expected, "audit_ready": True}))
    with pytest.raises(gate.GateError, match="output differs"):
        gate.verify(destination, REPOSITORY, PRIVATE)
