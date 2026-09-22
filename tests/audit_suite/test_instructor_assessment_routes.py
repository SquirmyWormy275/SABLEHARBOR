"""Explicit authored assessments remain private across HTTP and inert recovery."""

import pytest

from enterprise.audit_suite.companion_recovery import backup, restore
from enterprise.audit_suite.instructor_assessments import DIMENSIONS
from tests.audit_suite.test_instructor_debrief_routes import debrief_http as http_fixture


@pytest.fixture
def context(tmp_path):
    value = http_fixture.__wrapped__(tmp_path)
    app, _, state, *_ = value
    app.state.engine.company_bindings[state["id"]] = {"company": "C", "branch": "B"}
    return value


def recorded(context):
    app, client, state, teacher, student, other, headers, _ = context
    path = f"/api/engagements/{state['id']}/instructor-assessments"
    response = client.get(path + "/options?revision=1", headers=headers(teacher))
    assert response.status_code == 200, response.text
    options = response.json()
    body = {
        key: options[key]
        for key in ("learner_revision", "key_pin", "rubric_sha256", "inventory_sha256")
    }
    body.update(
        expected_engagement_revision=state["revision"],
        title="Selected shared-state assessment",
        issue_ids=["I1"],
        expectation_ids=["E1"],
        dimensions=[
            {
                "dimension": d,
                "assessment": "Not assessed",
                "rationale": "Support requires further review.",
                "reference_ids": [],
            }
            for d in DIMENSIONS
        ],
        alternatives=[],
        overrides=[],
        defects=[],
        predecessor=None,
        command_id="assessment-http",
    )
    response = client.post(path, headers=headers(teacher), json=body)
    assert response.status_code == 200, response.text
    return path, body, response.json()


def test_assessment_http_exact_retry_private_history_and_csrf(context):
    app, client, state, teacher, student, other, headers, _ = context
    before = app.state.engine.store.get(teacher["id"], state["id"])
    path, body, value = recorded(context)
    replay = client.post(path, headers=headers(teacher), json=body)
    assert replay.status_code == 200 and replay.json() == value
    listing = client.get(path, headers=headers(teacher))
    assert listing.status_code == 200, listing.text
    assert "document" not in listing.json()["assessments"][0]
    assert client.get(path + "/" + value["id"], headers=headers(teacher)).json() == value
    for suffix in ("", "/options?revision=0", "/" + value["id"]):
        assert client.get(path + suffix, headers=headers(student)).status_code == 403
    assert client.post(path, headers=headers(student), json=body).status_code == 403
    assert (
        client.get(path + "/options?revision=0&revision=1", headers=headers(teacher)).status_code
        == 422
    )
    assert (
        client.post("/api/session", json={"credential": teacher["credential"]}).status_code == 200
    )
    assert client.post(path, json=body).status_code == 403
    assert app.state.engine.store.get(teacher["id"], state["id"]) == before


def test_assessment_companion_restore_preserves_private_history_without_authority(
    context, tmp_path
):
    app, _, state, teacher, _, _, _, _ = context
    recorded(context)
    core = app.state.instructor_assessments
    before = app.state.engine.store.get(teacher["id"], state["id"])
    root = tmp_path / "assessment-recovery"
    root.mkdir(mode=0o700)
    backup(root / "backup", instructor_assessments=core)
    receipt = restore(root / "backup", root / "restored")
    original = (root / "backup/instructor-assessments.json").read_bytes()
    retained = root / "restored/instructor-assessments-ARCHIVE-ONLY.json"
    assert retained.read_bytes() == original
    assert retained.stat().st_mode & 0o777 == 0o600
    assert not list((root / "restored").rglob("*.sqlite3"))
    assert receipt["instructor_assessments"] == "ARCHIVE_ONLY_NOT_OPERATIONALLY_REHYDRATED"
    assert not receipt["credentials_or_grants_restored"]
    assert app.state.engine.store.get(teacher["id"], state["id"]) == before
