import json

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.companion_recovery import backup, restore
from enterprise.audit_suite.engine import COLLECTIONS
from enterprise.audit_suite.service import create_app
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_workspace_context import change


def setup(tmp_path, enabled=True):
    app = create_app(tmp_path / "audit", workspace_contexts=enabled, allowed_hosts=["testserver"])
    engine = app.state.engine
    owner = engine.store.provision("Checkpoint owner", ["learner"])
    other = engine.store.provision("Other checkpoint owner", ["learner"])
    state = {k: [] for k in COLLECTIONS}
    state.update(
        title="Neutral checkpoint",
        phase="ACTIVE",
        mode="CLEAN",
        discipline="IT",
        scope={"boundaries": ["corporate"]},
        simulated_at="2027-01-01T00:00:00Z",
        configuration={},
    )
    state["controls"] = [{"id": "C1", "title": "Neutral control"}]
    state["artifacts"] = [{"id": "A1", "status": "AVAILABLE", "sha256": "a" * 64, "version": 1}]
    state = engine.store.create(owner["id"], state, "create")
    engine.store.grant(state["id"], other["id"], "learn")
    client = TestClient(app, base_url="https://testserver")
    return app, client, owner, other, state


def test_routes_exact_capture_private_history_and_redacted_comparison(tmp_path):
    app, client, owner, other, state = setup(tmp_path)
    engine = app.state.engine
    path = f"/api/engagements/{state['id']}/visit-checkpoint"
    headers = {"authorization": "Bearer " + owner["credential"]}
    others = {"authorization": "Bearer " + other["credential"]}
    assert client.get(path).status_code == 401
    assert client.get(path, headers=headers).json()["status"] == "NO_CHECKPOINT"
    assert client.get("/api/bootstrap", headers=headers).json()["capabilities"]["visit_checkpoints"]
    body = {
        "command_id": "save-first",
        "expected_version": 0,
        "expected_engagement_revision": state["revision"],
    }
    response = client.post(path, headers=headers, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["version"] == 1
    assert client.post(path, headers=headers, json=body).json() == response.json()
    assert client.get(path, headers=others).json()["version"] == 0
    assert client.get(path + "/history", headers=others).json()["checkpoints"] == []
    comparison = {"expected_version": 1, "expected_engagement_revision": state["revision"]}
    result = client.post(path + "/compare", headers=headers, json=comparison).json()
    assert result["counts"] == {"added": 0, "changed": 0, "unchanged": 2}
    assert engine.store.get(owner["id"], state["id"])["revision"] == state["revision"]
    changed = change(
        engine, owner["id"], state, lambda s: s["artifacts"][0].update(status="QUARANTINED")
    )
    assert client.post(path + "/compare", headers=headers, json=comparison).status_code == 409
    comparison["expected_engagement_revision"] = changed["revision"]
    result = client.post(path + "/compare", headers=headers, json=comparison).json()
    assert result["status"] == "TARGET_UNAVAILABLE"
    assert not {"counts", "changes", "inventory"} & result.keys()
    assert "A1" not in json.dumps(result)
    assert client.post(path, headers=headers, json={**body, "extra": True}).status_code == 422
    assert (
        client.post(
            path + "/compare", headers=headers, json={**comparison, "expected_version": True}
        ).status_code
        == 409
    )
    with engine.store.connect() as db:
        db.execute(
            "DELETE FROM members WHERE principal=? AND engagement=?", (owner["id"], state["id"])
        )
    assert client.get(path, headers=headers).status_code in (403, 404)


def test_optional_companion_disabled_by_default(tmp_path):
    _, client, owner, _, state = setup(tmp_path, enabled=False)
    headers = {"authorization": "Bearer " + owner["credential"]}
    assert (
        client.get(f"/api/engagements/{state['id']}/visit-checkpoint", headers=headers).status_code
        == 503
    )
    assert (
        client.get("/api/bootstrap", headers=headers).json()["capabilities"]["visit_checkpoints"]
        is False
    )


def test_backup_preserves_exact_checkpoint_history_without_active_restore(tmp_path):
    app, _, owner, _, state = setup(tmp_path)
    visits = app.state.visit_checkpoints
    visits.capture(
        owner["id"],
        state["id"],
        command_id="capture",
        expected_version=0,
        expected_engagement_revision=state["revision"],
    )
    root = tmp_path / "recovery"
    root.mkdir(mode=0o700)
    manifest = backup(root / "backup", visit_checkpoints=visits)
    assert manifest["visit_checkpoints_restore_mode"] == "ARCHIVE_ONLY_NOT_OPERATIONALLY_REHYDRATED"
    receipt = restore(root / "backup", root / "restored")
    assert receipt["visit_checkpoints"] == "ARCHIVE_ONLY_NOT_OPERATIONALLY_REHYDRATED"
    assert receipt["credentials_or_grants_restored"] is False
    assert (root / "restored/visit-checkpoints-ARCHIVE-ONLY.json").read_bytes() == (
        root / "backup/visit-checkpoints.json"
    ).read_bytes()
    assert not list((root / "restored").rglob("*.sqlite3"))
    assert visits.status(owner["id"], state["id"])["version"] == 1
    with (root / "backup/visit-checkpoints.json").open("ab") as out:
        out.write(b" ")
    with pytest.raises(DomainError):
        restore(root / "backup", root / "corrupt")
    assert not (root / "corrupt").exists()
