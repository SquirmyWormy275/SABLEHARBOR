import copy

import pytest

from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.store import DomainError


def test_retest_preserves_original_and_rejects_retrospective_or_future_dates(tmp_path):
    engine = Engine(tmp_path / "state")
    finding = {
        "id": "F1",
        "status": "OPEN",
        "condition": "Original period exception",
        "original_period": {"period_start": "2027-01-01", "period_end": "2027-12-31"},
        "remediations": [
            {"id": "R1", "simulated_at": "2028-01-02T09:00:00Z", "action": "Implemented new review"}
        ],
    }
    state = {
        "phase": "ACTIVE",
        "simulated_at": "2028-02-05T09:00:00Z",
        "findings": [finding],
        "artifacts": [{"id": "A1", "status": "AVAILABLE"}],
    }
    original = copy.deepcopy(finding)
    payload = {
        "finding_id": "F1",
        "remediation_id": "R1",
        "test_date": "2028-02-05",
        "period_start": "2028-01-02",
        "period_end": "2028-01-31",
        "result": "SUPPORTED_FOR_RETEST_PERIOD",
        "procedures": "Inspect January reviews",
        "rationale": "All supplied reviews inspected; no claim about prior period",
        "evidence_ids": ["A1"],
    }
    engine._workspace_command(
        state,
        "remediation.retest",
        payload,
        {"actor": "learner", "simulated_at": state["simulated_at"]},
    )
    assert {k: v for k, v in finding.items() if k != "retests"} == original
    assert finding["retests"][0]["original_finding_unchanged"] is True
    for changed in (
        {"period_start": "2027-01-01"},
        {"test_date": "2028-02-06"},
        {"evidence_ids": []},
    ):
        with pytest.raises(DomainError):
            engine._workspace_command(
                state, "remediation.retest", {**payload, **changed}, {"actor": "learner"}
            )
    assert len(finding["retests"]) == 1
