"""Authenticated explicit reassessment inputs and ordinary command boundary."""

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.service import create_app
from tests.audit_suite.test_company_collection import envelope, workspace


@pytest.fixture
def context(tmp_path, monkeypatch):
    engine, _, state = workspace.__wrapped__(tmp_path)
    principal = engine.store.provision("Reassessment author", ["learner"])
    actor = principal["id"]
    engine.store.grant(state["id"], actor, "learn")
    engine.company_store.grant(actor, state["id"], "SH", "base", "identity")
    state = engine.command(actor, state["id"], envelope(state))
    artifact = state["artifacts"][0]
    state = engine.command(
        actor,
        state["id"],
        {
            "command_id": "workpaper",
            "expected_revision": state["revision"],
            "kind": "workpaper.add",
            "payload": {
                "title": "Original inspection",
                "evidence_ids": [artifact["id"]],
                "text": "Recorded original observation, subject to reassessment.",
            },
        },
    )
    engine.company_store.append_version(
        "SH",
        "base",
        "identity",
        "record",
        expected_version=1,
        command_id="correction",
        event_at="2027-01-01T00:00:00Z",
        available_at="2027-05-01T00:00:00Z",
        content=b"corrected company original\n",
        provenance={"source_reference": "attributed correction"},
    )
    app = create_app(engine.store.root, engine_factory=lambda: engine, allowed_hosts=["testserver"])
    client = TestClient(app, base_url="https://testserver")
    headers = {"authorization": "Bearer " + principal["credential"]}
    return engine, state, principal, artifact, client, headers


def test_explicit_inputs_command_retry_and_source_revocation(context):
    engine, state, principal, artifact, client, headers = context
    base = f"/api/engagements/{state['id']}"
    path = base + "/company/impact/disposition-inputs"
    assert client.get(path).status_code == 401
    for query in ("", "?artifact_id=", "?artifact_id=A&artifact_id=B", "?artifact_id=A&as_of=2030"):
        assert client.get(path + query, headers=headers).status_code == 422
    response = client.get(path, params={"artifact_id": artifact["id"]}, headers=headers)
    assert response.status_code == 200, response.text
    options = response.json()
    assert engine.store.get(principal["id"], state["id"])["revision"] == state["revision"]
    target = next(c for c in options["targets"] if c["reference"]["collection"] == "workpapers")
    command = {
        "command_id": "reassessment",
        "expected_revision": state["revision"],
        "kind": "source.impact.disposition.record",
        "payload": {
            "artifact_id": artifact["id"],
            "comparison_sha256": options["comparison"]["sha256"],
            "target_sha256": target["sha256"],
            "disposition": "REASSESSMENT_NEEDED",
            "rationale": "The corrected original requires an explicit review.",
            "intended_action": "Inspect the correction before revising this workpaper.",
            "retest_sha256": None,
            "predecessor": None,
        },
    }
    response = client.post(base + "/commands", json=command, headers=headers)
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["revision"] == state["revision"] + 1
    assert saved["workpapers"] == state["workpapers"]
    assert len(saved["source_impact_dispositions"]) == 1
    engine.company_store.grant(principal["id"], state["id"], "SH", "base", "identity", active=False)
    replay = client.post(base + "/commands", json=command, headers=headers)
    assert replay.status_code == 200 and replay.json() == saved
    denied = client.get(path, params={"artifact_id": artifact["id"]}, headers=headers)
    assert denied.status_code == 409
    assert (
        client.post("/api/session", json={"credential": principal["credential"]}).status_code == 200
    )
    assert client.post(base + "/commands", json=command).status_code == 403
