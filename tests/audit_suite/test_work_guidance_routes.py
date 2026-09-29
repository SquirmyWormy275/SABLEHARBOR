"""Explicit instructor policy plus private opted-in guidance over HTTP."""

import json

import pytest
import test_personal_view_routes as view_cases

from enterprise.audit_suite.companion_recovery import backup, restore


@pytest.fixture
def guide_context(tmp_path):
    app, client, owner, other, state, _, headers, _ = view_cases.setup.__wrapped__(tmp_path)
    engine = app.state.engine
    instructor = engine.store.provision("Instructor", ["instructor"])
    engine.store.grant(state["id"], instructor["id"], "instruct")
    return app, client, owner, other, instructor, state, headers


def enable(context):
    app, client, owner, other, instructor, state, headers = context
    base = f"/api/engagements/{state['id']}"
    result = client.post(
        base + "/commands",
        headers={"Authorization": "Bearer " + instructor["credential"]},
        json={
            "kind": "assistance.configure",
            "command_id": "allow",
            "expected_revision": state["revision"],
            "payload": {
                "work_guidance_allowed": True,
                "rationale": "Explicit guided technical fixture",
            },
        },
    )
    assert result.status_code == 200, result.text
    return result.json()


def opt(client, path, headers, state, version=0):
    body = {
        "enabled": True,
        "rationale": "I want visible-record administrative guidance",
        "expected_version": version,
        "expected_engagement_revision": state["revision"],
        "command_id": "personal-opt-in",
    }
    response = client.post(path + "/preference", headers=headers, json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_policy_opt_in_reveal_decision_are_private_and_inert_recovery(guide_context, tmp_path):
    app, client, owner, other, instructor, state, headers = guide_context
    path = f"/api/engagements/{state['id']}/work-guidance"
    before = client.get(path, headers=headers).json()
    assert before["status"] == "POLICY_DISABLED" and before["contexts"] == []
    assert "candidates" not in before
    state = enable(guide_context)
    enabled = opt(client, path, headers, state)
    assert enabled["status"] == "AVAILABLE" and enabled["contexts"]
    other_status = client.get(
        path, headers={"Authorization": "Bearer " + other["credential"]}
    ).json()
    assert other_status["status"] == "OPT_IN_REQUIRED" and other_status["contexts"] == []
    reveal = {
        "context_ref": enabled["contexts"][0]["reference"],
        "expected_engagement_revision": state["revision"],
        "command_id": "reveal",
    }
    response = client.post(path + "/reveal", headers=headers, json=reveal)
    assert response.status_code == 200, response.text
    shown = response.json()
    candidate = shown["candidates"][0]
    body = {
        "candidate_id": candidate["id"],
        "candidate_sha256": candidate["sha256"],
        "action": "DISMISS",
        "rationale": "I will review the request route in my separate investigation",
        "expected_engagement_revision": state["revision"],
        "command_id": "dismiss",
    }
    response = client.post(path + "/decision", headers=headers, json=body)
    assert response.status_code == 200, response.text
    assert client.post(path + "/decision", headers=headers, json=body).status_code == 200
    assert app.state.engine.store.get(owner["id"], state["id"])["revision"] == state["revision"]
    archive = tmp_path / "backup"
    destination = tmp_path / "restored"
    manifest = backup(archive, work_guidance=app.state.work_guidance)
    assert manifest["work_guidance_restore_mode"] == "ARCHIVE_ONLY_NOT_OPERATIONALLY_REHYDRATED"
    receipt = restore(archive, destination)
    assert receipt["work_guidance"] == "ARCHIVE_ONLY_NOT_OPERATIONALLY_REHYDRATED"
    assert not list(destination.rglob("*.sqlite3"))
    assert (archive / "work-guidance.json").read_bytes() == (
        destination / "work-guidance-ARCHIVE-ONLY.json"
    ).read_bytes()
    assert (
        json.loads((destination / "RESTORE_RECEIPT.json").read_text())[
            "credentials_or_grants_restored"
        ]
        is False
    )


def test_guidance_mutations_require_csrf_exact_body_and_current_policy(guide_context):
    app, client, owner, _, instructor, state, headers = guide_context
    state = enable(guide_context)
    path = f"/api/engagements/{state['id']}/work-guidance"
    body = {
        "enabled": True,
        "rationale": "Explicit local preference",
        "expected_version": 0,
        "expected_engagement_revision": state["revision"],
        "command_id": "opt",
    }
    assert client.get(path).status_code == 401
    assert (
        client.post(
            path + "/preference", headers=headers, json={**body, "actor": owner["id"]}
        ).status_code
        == 422
    )
    login = client.post("/api/session", json={"credential": owner["credential"]})
    assert login.status_code == 200
    assert client.post(path + "/preference", json=body).status_code == 403
    opted = opt(client, path, headers, state)
    policy = app.state.engine.command(
        instructor["id"],
        state["id"],
        {
            "kind": "assistance.configure",
            "command_id": "disable",
            "expected_revision": state["revision"],
            "payload": {"work_guidance_allowed": False, "rationale": "Unassisted phase"},
        },
    )
    current = client.get(path, headers=headers).json()
    assert current["status"] == "POLICY_DISABLED" and current["contexts"] == []
    assert "preference" not in current
    response = client.post(
        path + "/reveal",
        headers=headers,
        json={
            "context_ref": opted["contexts"][0]["reference"],
            "expected_engagement_revision": policy["revision"],
            "command_id": "denied-reveal",
        },
    )
    assert response.status_code in (403, 409), response.text
