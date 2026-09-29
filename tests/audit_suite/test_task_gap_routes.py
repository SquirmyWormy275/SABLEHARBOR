"""Isolated HTTP command/projection boundary for an authored task gap."""

import hashlib

from fastapi.testclient import TestClient

from enterprise.audit_suite.engine import COLLECTIONS
from enterprise.audit_suite.service import create_app


def test_task_gap_command_route_replay_projection_and_permissions(tmp_path):
    app = create_app(tmp_path / "audit", allowed_hosts=["testserver"])
    engine = app.state.engine
    author = engine.store.provision("Gap author", ["learner"])
    reviewer = engine.store.provision("Independent reviewer", ["reviewer"])
    outsider = engine.store.provision("Unassigned learner", ["learner"])
    original = b"retained native source for route-level gap test\n"
    source_sha = hashlib.sha256(original).hexdigest()
    retained = engine.artifacts.root / source_sha
    retained.write_bytes(original)
    retained.chmod(0o600)
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="Task gap HTTP boundary",
        phase="ACTIVE",
        discipline="IT",
        mode="CLEAN",
        simulated_at="2027-12-31T00:00:00Z",
        scope={
            "boundaries": ["corporate"],
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "timezone": "UTC",
        },
        configuration={"selections": []},
    )
    state["controls"] = [{"id": "C1", "title": "Declared local logging control"}]
    state["tasks"] = [
        {
            "id": "T1",
            "control_id": "C1",
            "title": "Inspect collection and clock gaps",
            "status": "NOT_STARTED",
            "conclusion": "NOT_RUN",
            "history": [],
        }
    ]
    state["artifacts"] = [
        {
            "id": "A1",
            "sha256": source_sha,
            "bytes": len(original),
            "status": "AVAILABLE",
            "audience": "LEARNER",
            "source": {
                "receipt": {
                    "source": {
                        "company": "SH",
                        "branch": "local",
                        "system": "security_logs",
                        "record": "R1",
                        "version": 1,
                        "sha256": source_sha,
                    }
                }
            },
        }
    ]
    state = engine.store.create(author["id"], state, "create-task-gap-http-test")
    engine.store.grant(state["id"], reviewer["id"], "review")
    client = TestClient(app, base_url="https://testserver")
    base = f"/api/engagements/{state['id']}"
    learner_headers = {"authorization": "Bearer " + author["credential"]}
    reviewer_headers = {"authorization": "Bearer " + reviewer["credential"]}
    outsider_headers = {"authorization": "Bearer " + outsider["credential"]}
    initial = client.get(base, headers=learner_headers)
    assert initial.status_code == 200, initial.text
    assert initial.json()["task_gaps"] == []
    command = {
        "command_id": "route-gap-1",
        "expected_revision": state["revision"],
        "kind": "task.gap.record",
        "payload": {
            "task_id": "T1",
            "cause": "INSUFFICIENT_SOURCE",
            "owner_id": author["id"],
            "disposition": "OPEN",
            "narrative": "The retained source does not prove the exact clock-gap procedure.",
            "artifact_pin": {"id": "A1", "sha256": source_sha},
            "retest": None,
            "predecessor_id": None,
        },
    }
    posted = client.post(base + "/commands", headers=learner_headers, json=command)
    assert posted.status_code == 200, posted.text
    saved = posted.json()
    assert saved["revision"] == state["revision"] + 1
    assert saved["tasks"] == initial.json()["tasks"]
    assert saved["tasks"][0]["status"] == "NOT_STARTED"
    assert saved["tasks"][0]["conclusion"] == "NOT_RUN"
    assert len(saved["task_gaps"]) == 1
    gap = saved["task_gaps"][0]
    assert gap["revision"] == saved["revision"]
    assert gap["actor"] == author["id"]
    assert gap["artifact_pin"]["sha256"] == source_sha
    assert gap["artifact_pin"]["native_source_pin"]["record"] == "R1"
    assert gap["qualification"] == "AUTHOR_RECORDED_GAP_NOT_EVIDENCE_OR_AUDIT_CONCLUSION"
    replay = client.post(base + "/commands", headers=learner_headers, json=command)
    assert replay.status_code == 200 and replay.json() == saved
    assert client.get(base, headers=learner_headers).json()["task_gaps"] == [gap]
    reviewer_view = client.get(base, headers=reviewer_headers)
    assert reviewer_view.status_code == 200 and reviewer_view.json()["task_gaps"] == [gap]
    assert client.get(base, headers=outsider_headers).status_code in (403, 404)
    assert client.get(base).status_code == 401
    rejected = client.post(
        base + "/commands",
        headers=reviewer_headers,
        json={**command, "command_id": "reviewer-write", "expected_revision": saved["revision"]},
    )
    assert rejected.status_code == 403
    after = client.get(base, headers=learner_headers).json()
    assert after["revision"] == saved["revision"]
    assert after["task_gaps"] == [gap]
    assert after["tasks"] == initial.json()["tasks"]
