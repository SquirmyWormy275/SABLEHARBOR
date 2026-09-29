import hashlib
import json

import pytest

from enterprise.audit_suite.companion_recovery import backup, restore
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_personal_view_routes import setup as setup


def offer(setup):
    app, client, owner, other, state, _, headers, _ = setup
    path = f"/api/engagements/{state['id']}/handoffs"
    reference = client.post(
        path + "/link",
        headers=headers,
        json={
            "recipient_id": other["id"],
            "kind": "control",
            "id": "C1",
            "version": None,
        },
    )
    assert reference.status_code == 200, reference.text
    body = {
        "command_id": "offer",
        "expected_engagement_revision": state["revision"],
        "payload": {
            "recipient_id": other["id"],
            "title": "Inspect the referenced control",
            "question": "What support should we request?",
            "next_step": "Review this exact control record",
            "links": [reference.json()],
        },
    }
    created = client.post(path, headers=headers, json=body)
    assert created.status_code == 200, created.text
    return path, body, created.json()


def test_participant_only_offer_accept_complete_and_exact_retry_leave_audit_unchanged(setup):
    app, client, owner, other, state, _, headers, _ = setup
    engine = app.state.engine
    before = engine.store.get(owner["id"], state["id"])
    path, body, offered = offer(setup)
    directory = client.get(path + "/members", headers=headers).json()
    assert directory["engagement_id"] == state["id"]
    assert directory["members"] == [
        {"id": other["id"], "display_name": "Other learner", "permission": "learn"}
    ]
    outsider = engine.store.provision("Uninvolved learner", ["learner"])
    engine.store.grant(state["id"], outsider["id"], "learn")
    outsider_headers = {"Authorization": "Bearer " + outsider["credential"]}
    url = path + "/" + offered["id"]
    assert client.get(path, headers=outsider_headers).json() == {"handoffs": []}
    assert client.get(url, headers=outsider_headers).status_code == 404
    assert client.get(path).status_code == 401
    assert client.post(path, headers=headers, json=body).json() == offered
    transition = {
        "action": "ACCEPT",
        "response": "",
        "expected_version": 1,
        "expected_engagement_revision": state["revision"],
        "command_id": "accept",
    }
    assert client.post(url + "/transition", headers=headers, json=transition).status_code == 403
    recipient = {"Authorization": "Bearer " + other["credential"]}
    accepted = client.post(url + "/transition", headers=recipient, json=transition)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "ACCEPTED"
    assert (
        client.post(url + "/transition", headers=recipient, json=transition).json()
        == accepted.json()
    )
    assert (
        client.post(
            url + "/transition", headers=recipient, json={**transition, "command_id": "stale"}
        ).status_code
        == 409
    )
    completed = client.post(
        url + "/transition",
        headers=recipient,
        json={
            **transition,
            "action": "COMPLETE",
            "response": "Request the dated source register; substantive testing remains open.",
            "expected_version": 2,
            "command_id": "complete",
        },
    )
    assert completed.status_code == 200, completed.text
    value = completed.json()
    assert value["status"] == "COMPLETED" and value["coordination_only"]
    assert value["content"]["response_author_id"] == other["id"]
    assert not value["formal_work_mutated"]
    assert engine.store.get(owner["id"], state["id"]) == before


def test_handoff_routes_csrf_exact_body_and_revoked_counterpart_redaction(setup):
    app, client, owner, other, state, _, headers, _ = setup
    path, body, offered = offer(setup)
    assert (
        client.post(path, headers=headers, json={**body, "recipient_id": other["id"]}).status_code
        == 422
    )
    login = client.post("/api/session", json={"credential": owner["credential"]})
    url = path + "/" + offered["id"]
    transition = {
        "action": "WITHDRAW",
        "response": "",
        "expected_version": 1,
        "expected_engagement_revision": state["revision"],
        "command_id": "withdraw",
    }
    assert client.post(url + "/transition", json=transition).status_code == 403
    app.state.engine.store.revoke(other["id"])
    redacted = client.get(url).json()
    assert not redacted["shared_content_visible"] and "content" not in redacted
    assert redacted["allowed_actions"] == ["WITHDRAW"]
    assert client.get(path + "/members").json()["members"] == []
    csrf = {"X-CSRF-Token": login.json()["csrf_token"]}
    assert client.post(url + "/transition", headers=csrf, json=transition).status_code == 200


def test_handoff_companion_is_verified_inert_archive_and_rejects_orphan_commands(setup, tmp_path):
    app, _, _, _, _, _, _, _ = setup
    offer(setup)
    handoffs = app.state.investigation_handoffs
    source = tmp_path / "handoff-backup"
    manifest = backup(source, investigation_handoffs=handoffs)
    assert (
        manifest["investigation_handoffs_restore_mode"]
        == "ARCHIVE_ONLY_NOT_OPERATIONALLY_REHYDRATED"
    )
    destination = tmp_path / "handoff-restore"
    receipt = restore(source, destination)
    assert receipt["investigation_handoffs"] == "ARCHIVE_ONLY_NOT_OPERATIONALLY_REHYDRATED"
    assert not receipt["credentials_or_grants_restored"]
    assert (destination / "investigation-handoffs-ARCHIVE-ONLY.json").read_bytes() == (
        source / "investigation-handoffs.json"
    ).read_bytes()
    assert not list(destination.rglob("*.sqlite3"))
    body = json.loads((source / "investigation-handoffs.json").read_text())
    body["commands"] = []
    raw = json.dumps(body).encode()
    (source / "investigation-handoffs.json").write_bytes(raw)
    manifest["members"]["investigation-handoffs.json"] = {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }
    (source / "MANIFEST.json").write_text(json.dumps(manifest))
    with pytest.raises(DomainError):
        restore(source, tmp_path / "invalid-handoff-restore")
    assert not (tmp_path / "invalid-handoff-restore").exists()
