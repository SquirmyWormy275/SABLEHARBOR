"""V18/V17/V15 reviewed leads leave every frozen audit control blocked."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import audit_readiness_gate_v6 as gate

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


@pytest.fixture(scope="module")
def snapshots():
    data = {}
    for key in ("v5_report", "v18_portfolio", "v18_candidate_report", "v17_route", "pbc_v15"):
        scope, relative, _ = gate.PINS[key]
        data[key] = json.loads(
            ((PRIVATE if scope == "private" else REPOSITORY) / relative).read_text()
        )
    return data


def _assemble(data):
    return gate._assemble(
        data["v5_report"],
        data["v18_portfolio"],
        data["v18_candidate_report"],
        data["v17_route"],
        data["pbc_v15"],
    )


def test_v6_retains_v5_blockers_false_readiness_and_frozen_pair(snapshots):
    base = snapshots["v5_report"]
    report = _assemble(snapshots)
    assert report["schema"] == gate.SCHEMA
    assert report["as_of"] == "2026-10-01"
    assert report["p1_freeze"] == gate.P1_FREEZE
    assert report["route_pbc_synchronization_pending_task_ids"] == []
    assert sum(map(len, report["blockers_by_family_control"].values())) == 43
    assert set(report["blockers_by_family_control"]) == set(base["blockers_by_family_control"])
    for family, controls in base["blockers_by_family_control"].items():
        assert set(report["blockers_by_family_control"][family]) == set(controls)
        for control, item in controls.items():
            updated = report["blockers_by_family_control"][family][control]
            assert updated["remaining_gates"] == item["remaining_gates"]
            assert updated["route_classes"] == item["route_classes"]
            assert updated["unsupported_task_ids"] == item["unsupported_task_ids"]
            assert updated["partial_task_ids"] == item["partial_task_ids"]
            assert updated["design_task_ids"] == item["design_task_ids"]
            assert updated["draft_request_group_ids"] == item["draft_request_group_ids"]
            assert updated["unaccepted_no_event_task_ids"] == item["unaccepted_no_event_task_ids"]
            assert updated["route_pbc_sync_pending_task_ids"] == []
    assert report["readiness_blockers"][:-2] == base["readiness_blockers"]
    assert report["readiness_blockers"][-2:] == list(gate.NEW_BLOCKERS)
    assert all(report[key] is False for key in gate.READINESS_FALSE)
    assert report["external_messages_sent"] == report["accepted_na_determinations"] == 0


def test_selected_source_and_candidate_prefixes_and_denominators(snapshots):
    report = _assemble(snapshots)
    assert report["source_roster"][:37] == snapshots["v5_report"]["source_roster"]
    assert [row["source"] for row in report["source_roster"][-4:]] == [
        "eng005operating",
        "govoversight",
        "legprovision",
        "dat002rights",
    ]
    assert len(report["source_roster"]) == 41
    for side in "AB":
        assert (
            report["candidate_source_pins"][side][:38]
            == snapshots["v5_report"]["candidate_source_pins"][side]
        )
        assert len(report["candidate_source_pins"][side]) == 42
        count = report["sides"][side]
        assert (count["source_cohorts"], count["native_business_versions"]) == (41, 948)
        assert (count["targeted_routes"], count["partial_routes"], count["design_routes"]) == (
            201,
            141,
            21,
        )
        assert (
            count["unsupported_exact_clauses"],
            count["route_targeted_unsupported_clauses"],
            count["pbc_targeted_unsupported_clauses"],
            count["source_affected_unsupported_clauses"],
        ) == (121, 55, 55, 47)
        assert (
            count["draft_unsent_request_groups"],
            count["unaccepted_no_event_candidates"],
            count["p1_tasks_not_started_not_run"],
        ) == (30, 53, 409)


def test_exact_paired_leg_dat_leads_and_only_two_draft_group_actions(snapshots):
    base = snapshots["v5_report"]
    report = _assemble(snapshots)
    route = snapshots["v17_route"]
    pbc = snapshots["pbc_v15"]
    selected = {
        f"{row['side']}:{row['task_id']}": row
        for row in route["rows"]
        if row["v17_reviewed_source_ids"]
    }
    pbc_rows = {f"{row['side']}:{row['task_id']}": row for row in pbc["rows"]}
    assert len(selected) == 36
    for side in "AB":
        assert sum(key.startswith(f"{side}:") for key in selected) == 18
    for key, route_row in selected.items():
        side = route_row["side"]
        old = base["blockers_by_family_control"][route_row["family"]][route_row["control_id"]]
        item = report["blockers_by_family_control"][route_row["family"]][route_row["control_id"]]
        limit = item["route_limits"][key]
        assert key not in old["targeted_task_ids"]
        assert key in item["targeted_task_ids"]
        assert key in item["unsupported_task_ids"]
        assert route_row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
        assert limit["v17_source_record_refs"] == pbc_rows[key]["v15_source_record_refs"]
        assert limit["pbc_v15_source_record_refs"] == route_row["v17_source_record_refs"]
        assert limit["pbc_v15_targeted_source_ids"] == limit["targeted_source_ids"]
        assert pbc_rows[key]["current_task_status"] == "NOT_STARTED"
        assert pbc_rows[key]["current_task_conclusion"] == "NOT_RUN"
        assert pbc_rows[key]["task_credit"] is False
        if route_row["task_id"] in gate.DAT_TASKS:
            assert limit["targeted_source_ids"] == [gate.DAT_SOURCE]
            assert route_row["control_id"] == "SH-DAT-002"
        else:
            assert limit["targeted_source_ids"] == [gate.LEG_SOURCE]
            assert route_row["control_id"] == "SH-LEG-001"
        assert key.startswith(f"{side}:")
    before_groups = {g["request_group_id"]: g for g in base["request_groups"]}
    after_groups = {g["request_group_id"]: g for g in report["request_groups"]}
    assert set(after_groups) == set(before_groups)
    assert {
        name
        for name, group in after_groups.items()
        if group["next_action"] != before_groups[name]["next_action"]
    } == gate.SELECTED_GROUPS
    assert all(group["status"] == "DRAFT_NOT_SENT" for group in after_groups.values())


def test_tampered_route_pbc_source_or_readiness_is_rejected(snapshots):
    changed = deepcopy(snapshots)
    row = next(
        row
        for row in changed["v17_route"]["rows"]
        if row["side"] == "A" and row["v17_reviewed_source_ids"]
    )
    row["v17_source_record_refs"][row["v17_reviewed_source_ids"][0]].pop()
    with pytest.raises(gate.GateError, match="source or draft join"):
        _assemble(changed)
    changed = deepcopy(snapshots)
    row = next(
        row
        for row in changed["pbc_v15"]["rows"]
        if row["side"] == "B" and row["v15_reviewed_source_ids"]
    )
    row["task_credit"] = True
    with pytest.raises(gate.GateError, match="source or draft join"):
        _assemble(changed)
    changed = deepcopy(snapshots)
    changed["v5_report"]["audit_ready"] = True
    with pytest.raises(gate.GateError, match="blocked prefix"):
        _assemble(changed)
    changed = deepcopy(snapshots)
    changed["pbc_v15"]["request_groups"][0]["v15_next_action"] = "SENT"
    with pytest.raises(gate.GateError, match="draft action"):
        _assemble(changed)


def test_main_review_pin_drift_fails_before_build(monkeypatch):
    pins = dict(gate.PINS)
    scope, relative, _ = pins["v18_review"]
    pins["v18_review"] = (scope, relative, "0" * 64)
    monkeypatch.setattr(gate, "PINS", pins)
    with pytest.raises(gate.GateError, match="pinned SHA-256 differs"):
        gate._load_pins(REPOSITORY, PRIVATE)


def test_read_only_build_and_private_round_trip(snapshots, tmp_path, monkeypatch):
    expected = _assemble(snapshots)
    assert gate.build(REPOSITORY, PRIVATE) == expected
    monkeypatch.setattr(gate, "build", lambda *_: expected)
    destination = tmp_path / "REPORT"
    destination.parent.chmod(0o700)
    assert gate.write(REPOSITORY, PRIVATE, destination) == expected
    assert gate.verify(destination, REPOSITORY, PRIVATE) == expected
    (destination / "REPORT.json").write_text(json.dumps({**expected, "audit_ready": True}))
    with pytest.raises(gate.GateError, match="output differs"):
        gate.verify(destination, REPOSITORY, PRIVATE)
