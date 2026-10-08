"""Reviewed V14 GOV draft joins clear synchronization, not audit blockers."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import audit_readiness_gate_v5 as gate

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def snapshots():
    return (
        json.loads((PRIVATE / gate.PINS["v4_report"][1]).read_text()),
        json.loads((REPOSITORY / gate.PINS["pbc_v14"][1]).read_text()),
    )


def test_reviewed_v4_prefix_and_exact_v14_delta(snapshots):
    base, pbc = snapshots
    report = gate._assemble(base, pbc)
    assert report["schema"] == gate.SCHEMA
    assert report["as_of"] == "2026-10-01"
    assert report["route_pbc_synchronization_pending_task_ids"] == []
    assert sum(map(len, report["blockers_by_family_control"].values())) == 43
    assert report["source_roster"] == base["source_roster"]
    assert report["candidate_source_pins"] == base["candidate_source_pins"]
    assert report["p1_freeze"] == gate.P1_FREEZE
    assert all(report[key] is False for key in gate.READINESS_FALSE)
    assert report["external_messages_sent"] == report["accepted_na_determinations"] == 0
    assert report["sides"]["A"] == report["sides"]["B"]
    for side in "AB":
        before = base["sides"][side]
        after = report["sides"][side]
        assert {
            key: value
            for key, value in after.items()
            if key
            not in {"pbc_targeted_unsupported_clauses", "source_affected_unsupported_clauses"}
        } == {
            key: value
            for key, value in before.items()
            if key
            not in {"pbc_targeted_unsupported_clauses", "source_affected_unsupported_clauses"}
        }
        assert (after["source_cohorts"], after["native_business_versions"]) == (37, 840)
        assert (after["targeted_routes"], after["partial_routes"], after["design_routes"]) == (
            183,
            141,
            21,
        )
        assert (
            after["unsupported_exact_clauses"],
            after["route_targeted_unsupported_clauses"],
        ) == (121, 37)
        assert (
            after["pbc_targeted_unsupported_clauses"],
            after["source_affected_unsupported_clauses"],
        ) == (37, 29)
        assert (
            after["draft_unsent_request_groups"],
            after["unaccepted_no_event_candidates"],
            after["p1_tasks_not_started_not_run"],
        ) == (30, 53, 409)
    assert report["readiness_blockers"][:-1] == base["readiness_blockers"][:-1]
    assert report["readiness_blockers"][-1] == gate.NEW_GOV_BLOCKER


def test_only_selected_gov_authored_leads_gain_refs_and_groups(snapshots):
    base, pbc = snapshots
    report = gate._assemble(base, pbc)
    rows = {f"{r['side']}:{r['task_id']}": r for r in pbc["rows"]}
    for family, controls in base["blockers_by_family_control"].items():
        for control, old in controls.items():
            new = report["blockers_by_family_control"][family][control]
            assert new["remaining_gates"] == old["remaining_gates"]
            assert new["targeted_task_ids"] == old["targeted_task_ids"]
            assert new["unsupported_task_ids"] == old["unsupported_task_ids"]
            assert new["draft_request_group_ids"] == old["draft_request_group_ids"]
            assert new["unaccepted_no_event_task_ids"] == old["unaccepted_no_event_task_ids"]
            assert new["route_pbc_sync_pending_task_ids"] == []
            for key, limit in old["route_limits"].items():
                updated = new["route_limits"][key]
                assert {k: v for k, v in updated.items() if not k.startswith("pbc_v14_")} == limit
                if key in rows:
                    row = rows[key]
                    assert updated["pbc_v14_reviewed_source_ids"] == row["v14_reviewed_source_ids"]
                    assert updated["pbc_v14_targeted_source_ids"] == row["v14_targeted_source_ids"]
                    assert updated["pbc_v14_source_record_refs"] == row["v14_source_record_refs"]
                    if key in base["route_pbc_synchronization_pending_task_ids"]:
                        assert updated["pbc_v14_reviewed_source_ids"] == [gate.SOURCE]
                        assert (
                            updated["pbc_v14_source_record_refs"]
                            == updated["v16_source_record_refs"]
                        )
    before_groups = {g["request_group_id"]: g for g in base["request_groups"]}
    after_groups = {g["request_group_id"]: g for g in report["request_groups"]}
    assert set(after_groups) == set(before_groups)
    assert (
        sum(
            g["next_action"] != before_groups[name]["next_action"]
            for name, g in after_groups.items()
        )
        == 2
    )
    for name, group in after_groups.items():
        assert group["status"] == "DRAFT_NOT_SENT"
        assert group["task_ids_per_side"] == before_groups[name]["task_ids_per_side"]
        assert {
            k: v for k, v in group.items() if not k.startswith("v14_") and k != "next_action"
        } == {k: v for k, v in before_groups[name].items() if k != "next_action"}


def test_changed_source_join_and_credit_are_rejected(snapshots):
    base, pbc = snapshots
    changed = deepcopy(pbc)
    row = next(r for r in changed["rows"] if r["side"] == "A" and r["task_id"] in gate.GOV_AUTHORED)
    row["v14_source_record_refs"][gate.SOURCE].pop()
    with pytest.raises(gate.GateError, match="source join"):
        gate._assemble(base, changed)
    changed = deepcopy(pbc)
    row = next(r for r in changed["rows"] if r["side"] == "B" and r["task_id"] in gate.GOV_AUTHORED)
    row["task_credit"] = True
    with pytest.raises(gate.GateError, match="source join"):
        gate._assemble(base, changed)
    changed_base = deepcopy(base)
    changed_base["audit_ready"] = True
    with pytest.raises(gate.GateError, match="no-credit prefix"):
        gate._assemble(changed_base, pbc)
    changed_base = deepcopy(base)
    changed_base["route_pbc_synchronization_pending_task_ids"].pop()
    with pytest.raises(gate.GateError, match="pending IDs"):
        gate._assemble(changed_base, pbc)


def test_review_pin_and_read_only_build(snapshots, monkeypatch):
    pins = dict(gate.PINS)
    scope, path, _ = pins["pbc_v14_review"]
    pins["pbc_v14_review"] = (scope, path, "0" * 64)
    monkeypatch.setattr(gate, "PINS", pins)
    with pytest.raises(gate.GateError, match="pinned SHA-256 differs"):
        gate._load_pins(REPOSITORY, PRIVATE)
    monkeypatch.undo()
    assert gate.build(REPOSITORY, PRIVATE) == gate._assemble(*snapshots)


def test_private_output_round_trip_and_tamper_rejection(tmp_path, monkeypatch, snapshots):
    expected = gate._assemble(*snapshots)
    monkeypatch.setattr(gate, "build", lambda *_: expected)
    destination = tmp_path / "REPORT"
    destination.parent.chmod(0o700)
    assert gate.write(REPOSITORY, PRIVATE, destination) == expected
    assert gate.verify(destination, REPOSITORY, PRIVATE) == expected
    (destination / "REPORT.json").write_text(json.dumps({**expected, "audit_ready": True}))
    with pytest.raises(gate.GateError, match="output differs"):
        gate.verify(destination, REPOSITORY, PRIVATE)
