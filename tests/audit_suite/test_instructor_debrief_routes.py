"""Selected explanation HTTP confirmation and verified binary download."""

import hashlib
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.service import create_app
from tests.audit_suite.test_bound_instructor import configured
from tests.audit_suite.test_explanation_binding import workspace as base_workspace
from tests.audit_suite.test_instructor_debrief import payload


@pytest.fixture
def debrief_http(tmp_path):
    engine, args = base_workspace.__wrapped__(tmp_path)
    state = engine.store.command(
        args["instructor_id"],
        args["engagement_id"],
        {
            "kind": "fixture.metadata",
            "command_id": "metadata",
            "expected_revision": 0,
            "payload": {},
        },
        lambda s, c, a: {
            **s,
            "title": "Selected debrief HTTP",
            "discipline": "COMPLIANCE",
            "mode": "CLEAN",
            "phase": "ACTIVE",
        },
        permissions={"instruct"},
    )
    config, _ = configured(engine, args)
    teacher = engine.store.provision("Teacher", ["instructor"])
    student = engine.store.provision("Student", ["learner"])
    other = engine.store.provision("Other", ["learner"])
    for person, role in [(teacher, "instruct"), (student, "learn"), (other, "learn")]:
        engine.store.grant(state["id"], person["id"], role)
    app = create_app(engine.store.root, instructor_bindings=config, allowed_hosts=["testserver"])
    client = TestClient(app, base_url="https://testserver")
    def headers(person):
        return {"Authorization": "Bearer " + person["credential"]}
    draft = payload(args)
    draft.update(
        recipient_id=student["id"], expected_revision=state["revision"], learner_revision=0
    )
    return app, client, state, teacher, student, other, headers, draft


def release(context):
    app, client, state, teacher, student, other, headers, draft = context
    base = f"/api/engagements/{state['id']}"
    p = client.post(
        base + "/instructor-releases/debrief-preview", headers=headers(teacher), json=draft
    )
    assert p.status_code == 200, p.text
    p = p.json()
    confirmed = client.post(
        base + "/instructor-releases",
        headers=headers(teacher),
        json={
            "preview_id": p["preview"]["id"],
            "preview_sha256": p["preview_sha256"],
            "command_id": "confirm",
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    return base, confirmed.json()


def test_debrief_http_selected_preview_binary_export_replay_and_revoke(debrief_http):
    app, client, state, teacher, student, other, headers, draft = debrief_http
    base = f"/api/engagements/{state['id']}"
    assert (
        client.get(
            base + "/instructor-releases/debrief-options", headers=headers(student)
        ).status_code
        == 403
    )
    options = client.get(base + "/instructor-releases/debrief-options", headers=headers(teacher))
    assert options.status_code == 200, options.text
    assert "claim" not in options.json()["issues"][0]
    base, confirmed = release(debrief_http)
    path = base + "/assistance/" + confirmed["release_id"]
    body = {"release_sha256": confirmed["release_sha256"]}
    assert client.post(path + "/export-preview", headers=headers(other), json=body).status_code in (
        403,
        404,
    )
    content = client.get(path, headers=headers(student))
    assert content.status_code == 200
    assert content.json()["content"]["document"]["learner"]["revision"] == 0
    ep = client.post(path + "/export-preview", headers=headers(student), json=body)
    assert ep.status_code == 200, ep.text
    ep = ep.json()
    command = {
        "preview_id": ep["preview"]["id"],
        "preview_sha256": ep["preview_sha256"],
        "command_id": "export",
    }
    exported = client.post(path + "/export", headers=headers(student), json=command)
    assert exported.status_code == 200, exported.text
    assert exported.headers["content-type"] == "application/zip"
    assert (
        exported.headers["x-content-sha256"]
        == hashlib.sha256(exported.content).hexdigest()
        == ep["preview"]["sha256"]
    )
    assert (
        int(exported.headers["content-length"]) == len(exported.content) == ep["preview"]["bytes"]
    )
    assert "no-store" in exported.headers["cache-control"]
    assert "attachment;" in exported.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        assert set(archive.namelist()) == {"debrief.html", "manifest.json"}
    assert (
        client.post(path + "/export", headers=headers(student), json=command).content
        == exported.content
    )
    revoked = client.post(
        base + "/instructor-releases/" + confirmed["release_id"] + "/revoke",
        headers=headers(teacher),
        json={
            "release_id": confirmed["release_id"],
            "command_id": "revoke",
            "reason": "Withdraw fixture",
        },
    )
    assert revoked.status_code == 200
    assert client.post(path + "/export", headers=headers(student), json=command).status_code in (
        403,
        409,
    )
    assert app.state.engine.store.get(teacher["id"], state["id"])["revision"] == state["revision"]


def test_debrief_preview_and_export_require_csrf_and_exact_context(debrief_http):
    _, client, state, teacher, student, _, headers, draft = debrief_http
    base, confirmed = release(debrief_http)
    assert (
        client.post("/api/session", json={"credential": student["credential"]}).status_code == 200
    )
    path = base + "/assistance/" + confirmed["release_id"] + "/export-preview"
    body = {"release_sha256": confirmed["release_sha256"]}
    assert client.post(path, json=body).status_code == 403
    assert (
        client.post(
            path + "?recipient_id=" + student["id"], headers=headers(student), json=body
        ).status_code
        == 422
    )
    assert (
        client.post(path, headers=headers(student), json={**body, "include_all": True}).status_code
        == 400
    )
    assert (
        client.post(
            base + "/instructor-releases/debrief-preview", headers=headers(student), json=draft
        ).status_code
        == 403
    )
