import copy
import json

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.background_jobs import BackgroundJobs
from enterprise.audit_suite.service import create_app
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_persona_selection import context
from tests.audit_suite.test_company_source_census_collection import envelope
from tests.audit_suite.test_company_source_census_collection import workspace as census_workspace


def test_background_census_collects_originals_once_without_import(tmp_path):
    engine, actor, state = census_workspace.__wrapped__(tmp_path)
    root = tmp_path / "jobs"
    root.mkdir(mode=0o700)
    jobs = BackgroundJobs(root, engine)
    command = envelope(state)
    job = jobs.submit(actor, state["id"], command)
    jobs.start(actor, state["id"], job["id"])
    thread = jobs.threads.get(job["id"])
    if thread:
        thread.join(10)
        assert not thread.is_alive()
    completed = jobs.read(actor, state["id"], job["id"])
    assert (completed["status"], completed["attempts"]) == ("COMPLETED", 1)
    result = engine.store.get(actor, state["id"])
    receipt = result["requests"][0]["company_census_collections"][0]
    assert receipt["source_versions"] == 2
    assert receipt["registration"] == "AWAITING_EXPLICIT_IMPORT"
    assert not result["populations"] and not result["workpapers"]
    for native in receipt["native_artifacts"]:
        artifact = next(a for a in result["artifacts"] if a["id"] == native["artifact_id"])
        assert engine.artifacts.read(artifact) == b'{"source":"original"}'
        assert artifact["sha256"] == native["source"]["sha256"]
    assert BackgroundJobs(root, engine).submit(actor, state["id"], command)["id"] == job["id"]
    assert engine.store.get(actor, state["id"]) == result


def census_command(state):
    return {
        "command_id": "census-job",
        "expected_revision": state["revision"],
        "kind": "company.census.collect",
        "payload": {
            "request_id": "PBC-PRIVATE",
            "system_id": "z-operations",
            "query": {
                "version_policy": "LATEST_VISIBLE_PER_RECORD",
                "event_window": {
                    "start": "2027-01-01T00:00:00Z",
                    "end": "2027-02-01T00:00:00Z",
                },
                "unknown_event_policy": "INCLUDE_UNDATED_STRATUM",
            },
        },
    }


def test_census_envelope_survives_reload_and_rejects_changed_retry(tmp_path):
    engine, actor, state, _ = context.__wrapped__(tmp_path)
    root = tmp_path / "jobs"
    root.mkdir(mode=0o700)
    jobs = BackgroundJobs(root, engine)
    command = census_command(state)
    job = jobs.submit(actor, state["id"], command)
    assert job["kind"] == "company.census.collect"
    reloaded = BackgroundJobs(root, engine)
    assert reloaded.input(actor, state["id"], job["id"]) == command
    assert reloaded.submit(actor, state["id"], command)["id"] == job["id"]
    assert "PBC-PRIVATE" not in json.dumps(reloaded.listing(actor, state["id"]))
    changed = copy.deepcopy(command)
    changed["payload"]["query"]["unknown_event_policy"] = "EXCLUDE"
    with pytest.raises(DomainError) as failure:
        reloaded.submit(actor, state["id"], changed)
    assert failure.value.code == "IDEMPOTENCY_CONFLICT"
    other = engine.store.provision("Other investigator", ["learner"])["id"]
    engine.store.grant(state["id"], other, "learn")
    assert reloaded.listing(other, state["id"]) == []
    with pytest.raises(DomainError):
        reloaded.input(other, state["id"], job["id"])
    assert engine.store.get(actor, state["id"]) == state


@pytest.mark.parametrize("kind", ["population.import", "workpaper.add", "scenario.custom.accept"])
def test_census_support_does_not_enable_other_mutations(tmp_path, kind):
    engine, actor, state, _ = context.__wrapped__(tmp_path)
    root = tmp_path / "jobs"
    root.mkdir(mode=0o700)
    jobs = BackgroundJobs(root, engine)
    command = {**census_command(state), "kind": kind}
    with pytest.raises(DomainError, match="supported background"):
        jobs.submit(actor, state["id"], command)
    assert jobs.listing(actor, state["id"]) == []


@pytest.mark.parametrize("code", ["INVALID_CENSUS_QUERY", "SOURCE_CENSUS_UNAVAILABLE"])
def test_census_failures_preserve_specific_safe_error_without_retry(tmp_path, monkeypatch, code):
    engine, actor, state, _ = context.__wrapped__(tmp_path)
    root = tmp_path / "jobs"
    root.mkdir(mode=0o700)
    jobs = BackgroundJobs(root, engine)
    calls = []

    def fail(actor_id, engagement_id, command):
        calls.append(command)
        raise DomainError("PRIVATE QUERY DETAIL", code=code, status=409)

    monkeypatch.setattr(engine, "command", fail)
    command = census_command(state)
    job = jobs.submit(actor, state["id"], command)
    jobs.start(actor, state["id"], job["id"])
    thread = jobs.threads.get(job["id"])
    if thread:
        thread.join(5)
        assert not thread.is_alive()
    result = jobs.read(actor, state["id"], job["id"])
    assert (result["status"], result["error_code"], result["attempts"]) == ("FAILED", code, 1)
    assert calls == [command]
    assert "PRIVATE" not in json.dumps(result)
    assert engine.store.get(actor, state["id"]) == state


@pytest.mark.parametrize("sources,enabled", [(False, False), (False, True), (True, True)])
def test_bootstrap_advertises_only_configured_background_kinds(tmp_path, sources, enabled):
    company = tmp_path / "company"
    if sources:
        company.mkdir(mode=0o700)
    app = create_app(
        tmp_path / "audit",
        background_jobs=enabled,
        company_root=company if sources else None,
        allowed_hosts=["testserver"],
    )
    actor = app.state.engine.store.provision("Investigator", ["learner"])
    client = TestClient(app, base_url="https://testserver")
    result = client.get(
        "/api/bootstrap", headers={"Authorization": "Bearer " + actor["credential"]}
    )
    assert result.status_code == 200
    assert result.json()["background_command_kinds"] == (
        ["meeting.message", *(["company.census.collect"] if sources else [])] if enabled else []
    )
