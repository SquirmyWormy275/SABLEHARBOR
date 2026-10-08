"""Meaningful row-level and claim-boundary tests for the read-only gate."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from enterprise.audit_suite import audit_readiness_gate_v2 as gate

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def inputs() -> dict:
    loaded, _ = gate._load_pins(REPOSITORY, PRIVATE)
    gate._assert_review_boundaries(loaded)
    return loaded


def _assemble(data: dict) -> dict:
    return gate._assemble(
        data["v13_portfolio"],
        data["v13_candidate_report"],
        data["v11_route"],
        data["pbc_v9"],
    )


def test_gate_keeps_full_roster_and_blockers(inputs: dict) -> None:
    report = _assemble(inputs)
    assert (report["source_complete"], report["fresh_pair_eligible"], report["audit_ready"]) == (
        False,
        False,
        False,
    )
    assert len(report["source_roster"]) == 34
    assert len(report["candidate_source_pins"]["A"]) == 35
    assert report["sides"]["A"] == {
        "source_cohorts": 34,
        "native_business_versions": 780,
        "routes": 283,
        "targeted_routes": 174,
        "partial_routes": 135,
        "design_routes": 27,
        "unsupported_exact_clauses": 121,
        "unaccepted_no_event_candidates": 53,
        "p1_tasks_not_started_not_run": 409,
    }
    assert report["sides"]["A"] == report["sides"]["B"]
    assert report["sides"]["A"]["unaccepted_no_event_candidates"] == 53
    assert len(report["request_groups"]) == 30
    assert sum(len(controls) for controls in report["blockers_by_family_control"].values()) == 43
    assert "SH-POL-003" in report["blockers_by_family_control"]["policy_and_hipaa_addressable"]
    control = report["blockers_by_family_control"]["policy_and_hipaa_addressable"]["SH-POL-003"]
    assert any(key.startswith("A:") for key in control["route_limits"])
    assert any(key.startswith("B:") for key in control["route_limits"])
    assert "Messy" in " ".join(report["readiness_blockers"])
    assert "audit_ready=false" in gate.markdown(report)
    assert all(
        report[key] is False
        for key in (
            "fresh_audit_pair_created",
            "audit_task_credit",
            "audit_conclusion_issued",
            "key_issued",
            "grade_issued",
            "actual_operation_claimed",
            "grants_or_collections_created",
        )
    )


def test_selected_sec001_native_leads_preserve_open_gates(inputs: dict) -> None:
    report = _assemble(inputs)
    control = report["blockers_by_family_control"]["architecture_configuration_and_change"][
        "SH-SEC-001"
    ]
    for side, component_count, transfer_count in (("A", 10, 10), ("B", 15, 16)):
        cc52 = f"{side}:{gate.requests.CC52_TASK}"
        cc67 = f"{side}:{gate.requests.CC67_TASK}"
        assert {cc52, cc67} <= set(control["unsupported_task_ids"])
        assert (
            len(
                control["route_limits"][cc52]["pbc_v9_source_record_refs"][
                    gate.requests.COMP_SOURCE
                ]
            )
            == component_count
        )
        assert (
            len(
                control["route_limits"][cc67]["pbc_v9_source_record_refs"][
                    gate.requests.TRANSFER_SOURCE
                ]
            )
            == transfer_count
        )
        assert control["route_limits"][cc52]["targeted_source_ids"] == [
            "SEC003_SELECTED_VULNERABILITY_V1"
        ]
        assert control["route_limits"][cc67]["targeted_source_ids"] == [
            gate.requests.TRANSFER_SOURCE
        ]
    assert (
        next(
            group for group in report["request_groups"] if group["request_group_id"] == "SH-SEC-001"
        )["status"]
        == "DRAFT_NOT_SENT"
    )


def test_exact_pin_change_fails_before_replay(inputs: dict) -> None:
    changed = copy.deepcopy(inputs)
    changed["v11_route_review"]["main_tracked_sha256"][gate.PINS["v11_route"][1]] = "0" * 64
    with pytest.raises(gate.GateError, match="review or exact output join"):
        gate._assert_review_boundaries(changed)


def test_same_count_route_clause_drift_fails_join(inputs: dict) -> None:
    changed = copy.deepcopy(inputs)
    row = next(
        row
        for row in changed["v11_route"]["rows"]
        if row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
    )
    row["authored_test_clause"] += " invented"
    with pytest.raises(gate.GateError, match="route/PBC clause join"):
        _assemble(changed)


def test_same_count_candidate_source_drift_fails_join(inputs: dict) -> None:
    changed = copy.deepcopy(inputs)
    changed["v13_candidate_report"]["sides"]["A"]["source_pins"][0]["receipt_sha256"] = "0" * 64
    with pytest.raises(gate.GateError, match="candidate/native source pin join"):
        _assemble(changed)
    changed = copy.deepcopy(inputs)
    pin = next(
        pin
        for pin in changed["v13_candidate_report"]["sides"]["B"]["source_pins"]
        if pin["source"] == "sec001component"
    )
    pin["database_sha256"] = "0" * 64
    with pytest.raises(gate.GateError, match="candidate/native source pin join"):
        _assemble(changed)


def test_selected_sec001_source_or_route_drift_fails_join(inputs: dict) -> None:
    changed = copy.deepcopy(inputs)
    row = next(
        row for row in changed["v13_portfolio"]["sources"] if row["source"] == "sec001transfer"
    )
    row["actual_network_transmission"] = True
    with pytest.raises(gate.GateError, match="deployment boundary"):
        _assemble(changed)
    changed = copy.deepcopy(inputs)
    row = next(
        row
        for row in changed["pbc_v9"]["rows"]
        if row["side"] == "B" and row["task_id"] == gate.requests.CC67_TASK
    )
    row["v9_source_record_refs"][gate.requests.TRANSFER_SOURCE].pop()
    with pytest.raises(gate.GateError, match="selected SEC001 route/request/native lead"):
        _assemble(changed)


def test_no_event_acceptance_or_draft_request_mutation_fails(inputs: dict) -> None:
    changed = copy.deepcopy(inputs)
    changed["pbc_v9"]["rows"][0]["accepted_nonoccurrence_status"] = "ACCEPTED"
    with pytest.raises(gate.GateError, match="request acceptance or credit"):
        _assemble(changed)
    changed = copy.deepcopy(inputs)
    changed["pbc_v9"]["request_groups"][0]["request_status"] = "SENT"
    with pytest.raises(gate.GateError, match="draft group boundary"):
        _assemble(changed)


def test_p1_task_status_claim_fails(inputs: dict) -> None:
    changed = copy.deepcopy(inputs)
    changed["v11_route"]["active_p1_tasks"]["B"]["status"] = "STARTED"
    with pytest.raises(gate.GateError, match="frozen P1 task status"):
        _assemble(changed)


def test_private_report_bytes_verify_after_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, inputs: dict
) -> None:
    expected = _assemble(inputs)
    monkeypatch.setattr(gate, "build", lambda *_: expected)
    output = tmp_path / "REPORT"
    output.parent.chmod(0o700)
    assert gate.write(REPOSITORY, PRIVATE, output) == expected
    assert {p.name for p in output.iterdir()} == {"REPORT.json", "REPORT.md"}
    (output / "REPORT.json").write_text(json.dumps({**expected, "audit_ready": True}))
    with pytest.raises(gate.GateError, match="output differs"):
        gate.verify(output, REPOSITORY, PRIVATE)


def test_symlinked_private_ancestor_rejected(tmp_path: Path) -> None:
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    alias = tmp_path / "alias"
    alias.symlink_to(private, target_is_directory=True)
    with pytest.raises(gate.GateError, match="Symlinked path component"):
        gate._reject_symlink_chain(alias / "REPORT.json")
    with pytest.raises(gate.GateError, match="Symlinked path component"):
        gate.verify(alias / "REPORT", REPOSITORY, PRIVATE)


def test_preexisting_nonprivate_parent_is_not_chmodded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, inputs: dict
) -> None:
    parent = tmp_path / "public"
    parent.mkdir(mode=0o755)
    parent.chmod(0o755)
    monkeypatch.setattr(gate, "build", lambda *_: _assemble(inputs))
    with pytest.raises(gate.GateError, match="must already be private"):
        gate.write(REPOSITORY, PRIVATE, parent / "REPORT")
    assert parent.stat().st_mode & 0o777 == 0o755
