from copy import deepcopy
from types import SimpleNamespace

import pytest

from enterprise.audit_suite.store import DomainError
from enterprise.audit_suite.temporal_workflow import current, handle, reports


def state():
    return {
        "phase": "ACTIVE",
        "simulated_at": "2028-01-03T09:00:00+00:00",
        "scope": {
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "temporal_basis": "PERIOD",
            "boundaries": ["corporate"],
        },
        "controls": [{"id": "C1", "owner_ids": ["P1"], "implementation_version": "v1"}],
        "people": [{"id": "P1"}, {"id": "P2"}],
        "tasks": [],
        "artifacts": [
            {"id": "A1", "status": "AVAILABLE", "received_at": "2028-01-02T09:00:00+00:00"}
        ],
        "requests": [
            {"id": "R1", "control_id": "C1", "boundary_id": "corporate", "status": "DRAFT"}
        ],
    }


def record(s, **overrides):
    payload = {
        "implementation_id": current(s)["versions"][0]["id"],
        "covered_start": "2027-01-01",
        "covered_end": "2027-06-30",
        "performed_at": "2028-01-03T08:00:00+00:00",
        "procedure_kind": "TOE",
        "result": "RECORDED",
        "evidence_ids": ["A1"],
        "rationale": "Dated occurrence testing",
        "methodology": "Exercise-specific risk assessment",
        "nature_timing_extent": "Inspected interim records",
        **overrides,
    }
    handle(None, s, "coverage.record", payload, {"actor": "learner"})


def test_interim_gap_and_no_change_claim_do_not_become_automatic_coverage():
    s = state()
    record(s)
    first = deepcopy(current(s)["work"])
    report = reports(s)[0]
    assert report["versions"][0]["gaps"] == [
        {"start": "2027-07-01T00:00:00+00:00", "end": "2028-01-01T00:00:00+00:00"}
    ]
    record(
        s,
        covered_start="2027-07-01",
        covered_end="2027-12-31",
        procedure_kind="INQUIRY",
        result="NO_CHANGE_REPORTED",
        evidence_ids=[],
    )
    assert not reports(s)[0]["reported_work_complete"]
    assert current(s)["work"][:1] == first
    record(s, covered_start="2027-07-01", covered_end="2027-12-31", procedure_kind="ROLL_FORWARD")
    assert reports(s)[0]["reported_work_complete"]
    assert reports(s)[0]["professional_sufficiency"] == "NOT_ASSERTED"


def test_late_change_preserves_original_work_but_requires_reassessment():
    s = state()
    record(s, covered_end="2027-12-31", result="EXCEPTION")
    original = deepcopy(current(s)["work"])
    handle(
        None,
        s,
        "implementation.change",
        {
            "implementation_id": current(s)["versions"][0]["id"],
            "effective_at": "2027-10-01",
            "owner_id": "P2",
            "implementation_version": "v2",
            "rationale": "New redesign source identified",
        },
        {"actor": "learner"},
    )
    assert current(s)["work"] == original
    assert len(current(s)["version_history"]) == 1
    assert reports(s)[0]["records_requiring_reassessment"] == [original[0]["id"]]
    assert reports(s)[0]["historical_exception_ids"] == [original[0]["id"]]
    assert not reports(s)[0]["reported_work_complete"]
    assert len(reports(s)[0]["versions"]) == 2


def test_remaining_request_requires_explicit_confirmation_and_future_work_rejected():
    s = state()
    calls = []
    engine = SimpleNamespace(_request_command=lambda *args: calls.append(args))
    handle(
        engine,
        s,
        "coverage.propose_remaining",
        {
            "control_id": "C1",
            "boundary_id": "corporate",
            "source_request_ids": ["R1"],
            "message": "Please provide final-period occurrences and changes",
            "rationale": "Unaddressed final period",
        },
        {"actor": "learner"},
    )
    assert not calls and s["requests"][0]["status"] == "DRAFT"
    proposal = current(s)["proposals"][0]
    handle(
        engine,
        s,
        "coverage.confirm_remaining",
        {
            "id": proposal["id"],
            "message": proposal["message"],
        },
        {"actor": "learner"},
    )
    assert calls[0][1] == "pbc.issue" and proposal["status"] == "ISSUED"
    with pytest.raises(DomainError, match="future procedure"):
        record(s, performed_at="2028-02-01T00:00:00+00:00")
    s["artifacts"][0]["audience"] = "REVIEWER"
    with pytest.raises(DomainError, match="observable"):
        record(s)


def test_point_in_time_does_not_require_full_period_toe():
    s = state()
    s["scope"].update(period_start="2027-12-31", temporal_basis="POINT_IN_TIME")
    record(s, covered_start="2027-12-31", covered_end="2027-12-31", procedure_kind="TOD")
    assert reports(s)[0]["missing_kinds"] == ["IMPLEMENTATION"]
    record(s, covered_start="2027-12-31", covered_end="2027-12-31", procedure_kind="IMPLEMENTATION")
    report = reports(s)[0]
    assert report["reported_work_complete"] and not report["full_period_toe_required"]
