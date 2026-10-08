"""The recheck reads disposable retained copies; it never alters source/audit state."""

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite import procedure_original_integrity as integrity
from enterprise.audit_suite import sample_execution
from enterprise.audit_suite.service import create_app
from enterprise.audit_suite.store import DomainError, digest
from tests.audit_suite.test_sample_execution import trace as trace


def recorded(fixture):
    state, artifacts, stamp, payload = fixture
    sample_execution.handle(state, "sample.execution.record", payload, stamp, artifacts)
    return state, artifacts


def test_exact_retained_bytes_are_rechecked_without_procedure_credit(trace):
    state, artifacts = recorded(trace)
    before = deepcopy(state)
    result = integrity.summarize(state, artifacts.read)
    assert result["status"] == "VERIFIED_RETAINED_BYTES_ONLY"
    assert result["counts"]["verified"] == 1
    assert result["artifacts"][0]["status"] == "VERIFIED_RETAINED_BYTES"
    assert result["traces"][0]["status"] == "VERIFIED_RETAINED_BYTES"
    assert not result["automatic_testing_credit"]
    assert result["period_and_procedure_sufficiency"] == "NOT_ESTABLISHED"
    assert state == before


def test_missing_and_tampered_disposable_bytes_are_distinct_from_uncaptured(trace):
    state, artifacts = recorded(trace)
    original = artifacts.root / state["artifacts"][0]["sha256"]
    saved = original.read_bytes()
    original.unlink()
    missing = integrity.summarize(state, artifacts.read)
    assert missing["counts"]["missing"] == 1
    assert missing["artifacts"][0]["status"] == "MISSING_RETAINED_BYTES"
    assert missing["status"] == "PARTIAL_UNAVAILABLE"
    original.write_bytes(b"tampered disposable copy")
    changed = integrity.summarize(state, artifacts.read)
    assert changed["counts"]["integrity_failure"] == 1
    assert changed["artifacts"][0]["status"] == "RETAINED_BYTE_INTEGRITY_FAILURE"
    original.write_bytes(saved)
    assert integrity.summarize(state, artifacts.read)["counts"]["verified"] == 1


def test_no_reference_is_not_reported_as_missing_bytes(trace):
    state, artifacts, stamp, payload = trace
    for item in payload["items"]:
        item["status"] = "NOT_PERFORMED"
        item["evidence"] = []
    sample_execution.handle(state, "sample.execution.record", payload, stamp, artifacts)
    result = integrity.summarize(state, artifacts.read)
    assert result["status"] == "NO_RETAINED_ORIGINAL_REFERENCED"
    assert result["counts"]["referenced"] == result["counts"]["missing"] == 0
    assert result["traces"][0]["status"] == "NO_RETAINED_ORIGINAL_REFERENCED"


def test_metadata_failure_does_not_trigger_artifact_read(trace):
    state, artifacts = recorded(trace)
    state["sample_executions"][0]["items"][0]["item_digest"] = "f" * 64
    calls = []
    result = integrity.summarize(state, lambda manifest: calls.append(manifest))
    assert result["status"] == "PARTIAL_UNAVAILABLE"
    assert result["counts"]["referenced"] == 0
    assert result["traces"][0]["status"] == "METADATA_UNAVAILABLE"
    assert calls == []


def test_ambiguous_correction_lineage_does_not_recheck_as_valid(trace):
    state, artifacts, stamp, payload = trace
    sample_execution.handle(state, "sample.execution.record", payload, stamp, artifacts)
    first = state["sample_executions"][0]
    sample_execution.handle(
        state,
        "sample.execution.correct",
        {
            **payload,
            "predecessor_id": first["id"],
            "predecessor_digest": digest(first),
            "correction_rationale": "Rechecked author note",
        },
        stamp,
        artifacts,
    )
    fork = deepcopy(state["sample_executions"][-1])
    fork["id"] = "FORK"
    state["sample_executions"].append(fork)
    calls = []
    result = integrity.summarize(state, lambda manifest: calls.append(manifest))
    assert result["status"] == "PARTIAL_UNAVAILABLE"
    assert result["counts"]["referenced"] == 0
    assert all(row["status"] == "METADATA_UNAVAILABLE" for row in result["traces"])
    assert calls == []


def test_report_authorizes_projection_before_original_read(trace):
    state, artifacts = recorded(trace)
    calls = []

    class Engine:
        def get(self, actor, engagement_id):
            calls.append(("get", actor, engagement_id))
            return state

    engine = Engine()
    engine.artifacts = artifacts
    assert integrity.report(engine, "learner", state["id"])["counts"]["verified"] == 1
    assert calls == [("get", "learner", state["id"])]


def test_explicit_bounded_recheck_does_not_claim_success(trace, monkeypatch):
    state, artifacts = recorded(trace)
    monkeypatch.setattr(integrity, "MAX_ORIGINALS", 0)
    result = integrity.summarize(state, artifacts.read)
    assert result["status"] == "RECHECK_INPUT_UNAVAILABLE"
    assert result["counts"] is None


def test_reader_bytes_are_hashed_independently_and_ambiguous_manifests_fail_closed(trace):
    state, _ = recorded(trace)
    checked = integrity.summarize(state, lambda manifest: b"wrong retained content")
    assert checked["counts"]["integrity_failure"] == 1
    state["artifacts"].append(deepcopy(state["artifacts"][0]))
    calls = []
    ambiguous = integrity.summarize(state, lambda manifest: calls.append(manifest))
    assert ambiguous["status"] == "RECHECK_INPUT_UNAVAILABLE"
    assert ambiguous["counts"] is None and calls == []


def test_physically_oversized_disposable_original_is_rejected_before_read(trace):
    state, artifacts = recorded(trace)
    original = artifacts.root / state["artifacts"][0]["sha256"]
    saved = original.read_bytes()
    manifest = state["artifacts"][0]

    class Engine:
        def get(self, actor, engagement_id):
            return state

    engine = Engine()
    engine.artifacts = artifacts
    try:
        with original.open("r+b") as stream:
            stream.truncate(integrity.MAX_SINGLE_BYTES + 1)
        with pytest.raises(DomainError, match="bounded read"):
            artifacts.read_bounded(manifest, max_bytes=manifest["bytes"])
        result = integrity.report(engine, "learner", state["id"])
        assert result["status"] == "PARTIAL_UNAVAILABLE"
        assert result["counts"]["integrity_failure"] == 1
    finally:
        original.write_bytes(saved)
    assert integrity.report(engine, "learner", state["id"])["counts"]["verified"] == 1


def test_read_only_route_requires_engagement_membership(tmp_path):
    app = create_app(tmp_path / "service", allowed_hosts=["testserver"])
    owner = app.state.engine.store.provision("Owner", ["learner"])
    other = app.state.engine.store.provision("Other", ["learner"])
    state = app.state.engine.store.create(
        owner["id"],
        {
            "title": "Disposable test",
            "simulated_at": "2027-01-01",
            "discipline": "IT",
            "mode": "CLEAN",
            "phase": "CONFIGURING",
            "artifacts": [],
        },
        "create",
    )
    route = f"/api/engagements/{state['id']}/procedure-original-integrity"
    client = TestClient(app, base_url="https://testserver")
    assert client.get(route).status_code == 401
    assert (
        client.get(route, headers={"Authorization": "Bearer " + other["credential"]}).status_code
        == 403
    )
    response = client.get(route, headers={"Authorization": "Bearer " + owner["credential"]})
    assert response.status_code == 200
    assert response.json()["status"] == "NO_RECORDED_TRACES"
    assert not response.json()["automatic_testing_credit"]
