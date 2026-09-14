import pytest

from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.store import DomainError


def test_actual_command_projects_dated_coverage_and_preserves_authorization(tmp_path):
    engine = Engine(tmp_path / "state")
    actor = engine.store.provision("Learner", ["learner"])
    outsider = engine.store.provision("Other", ["learner"])
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="Neutral temporal fixture",
        phase="ACTIVE",
        simulated_at="2028-01-03T09:00:00+00:00",
        scope={
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "temporal_basis": "PERIOD",
            "boundaries": ["unit"],
        },
        controls=[{"id": "C1", "owner_ids": ["P1"], "implementation_version": "v1"}],
        people=[{"id": "P1"}],
        artifacts=[{"id": "A1", "status": "AVAILABLE", "received_at": "2028-01-02T09:00:00+00:00"}],
    )
    state = engine.store.create(actor["id"], state, "create")
    initial = engine._project(actor["id"], state)
    version = initial["temporal_current"]["versions"][0]["id"]
    assert not initial["temporal_reports"][0]["reported_work_complete"]
    command = {
        "command_id": "dated-work-1",
        "expected_revision": state["revision"],
        "kind": "coverage.record",
        "payload": {
            "implementation_id": version,
            "covered_start": "2027-01-01",
            "covered_end": "2027-06-30",
            "performed_at": "2028-01-03",
            "procedure_kind": "TOE",
            "result": "RECORDED",
            "evidence_ids": ["A1"],
            "rationale": "Interim records only",
            "methodology": "Explicit bounded inspection",
            "nature_timing_extent": "Inspected supplied original",
        },
    }
    with pytest.raises(DomainError):
        engine.command(outsider["id"], state["id"], command)
    revised = engine.command(actor["id"], state["id"], command)
    assert len(revised["temporal_current"]["work"]) == 1
    assert revised["temporal_reports"][0]["versions"][0]["gaps"][0]["start"].startswith(
        "2027-07-01"
    )
    assert engine.command(actor["id"], state["id"], command)["revision"] == revised["revision"]
