from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite import workspace_transport as transport
from enterprise.audit_suite.engine import COLLECTIONS
from enterprise.audit_suite.service import create_app
from enterprise.audit_suite.store import DomainError, digest


def fixture_state():
    state = {key: [] for key in COLLECTIONS}
    state.update(
        id="ENG-TRANSPORT",
        revision=8,
        title="Transport fixture only",
        mode="CLEAN",
        discipline="IT",
        phase="ACTIVE",
        configuration={},
        permissions=["learn"],
        simulated_at="2028-01-03T00:00:00Z",
        scope={
            "boundaries": ["corporate"],
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
        },
        company_source_binding={"company": "NEUTRAL", "branch": "A", "source_revision": 2},
    )
    state["workpapers"] = [
        {
            "id": "WP-1",
            "title": "Two exact versions",
            "prepared_by": "PREPARER",
            "versions": [
                {
                    "version": 1,
                    "actor": "PREPARER",
                    "text": "Old 🧭 retained quote",
                    "task_ids": ["TASK-1"],
                    "evidence_ids": ["ART-1"],
                },
                {
                    "version": 2,
                    "actor": "PREPARER",
                    "text": "Current body\n" * 10000,
                    "task_ids": ["TASK-1"],
                    "evidence_ids": ["ART-1"],
                },
            ],
        }
    ]
    state["artifacts"] = [
        {"id": "ART-1", "status": "AVAILABLE", "sha256": "a" * 64, "audience": "LEARNER"},
        {"id": "ART-PRIVATE", "status": "AVAILABLE", "sha256": "b" * 64, "audience": "INSTRUCTOR"},
    ]
    state["sample_executions"] = [
        {
            "id": "TRACE-1",
            "revision": 1,
            "workpaper_id": "WP-1",
            "workpaper_version": 1,
            "workpaper_digest": "c" * 64,
            "items": [
                {
                    "item_id": "ITEM-1",
                    "status": "EXCEPTION",
                    "observation": "Earlier exception",
                    "evidence": [
                        {
                            "artifact_id": "ART-1",
                            "sha256": "a" * 64,
                            "locator": "Exact original field",
                        }
                    ],
                }
            ],
        },
        {
            "id": "TRACE-2",
            "revision": 2,
            "predecessor_id": "TRACE-1",
            "workpaper_id": "WP-1",
            "workpaper_version": 2,
            "workpaper_digest": "d" * 64,
            "items": [
                {
                    "item_id": "ITEM-1",
                    "status": "LIMITATION",
                    "observation": "Correction does not cite original",
                    "evidence": [],
                }
            ],
        },
        {
            "id": "TRACE-3",
            "revision": 1,
            "workpaper_id": "WP-1",
            "workpaper_version": 2,
            "workpaper_digest": "d" * 64,
            "items": [
                {
                    "item_id": "ITEM-OTHER",
                    "status": "OBSERVED",
                    "observation": "Another original",
                    "evidence": [],
                }
            ],
        },
    ]
    return state


def read_pins(state, row, collection):
    pin = transport.summary(state)[collection][0]["_workspace_detail"]
    return dict(
        revision=state["revision"],
        source_epoch=pin["source_epoch_sha256"],
        object_sha256=digest(row),
    )


def test_all_rows_relationships_and_exact_bodies_survive_without_mutating_storage():
    state = fixture_state()
    before = deepcopy(state)
    view = transport.summary(state)
    assert state == before
    assert [r["id"] for r in view["workpapers"]] == ["WP-1"]
    assert [r["id"] for r in view["sample_executions"]] == ["TRACE-1", "TRACE-2", "TRACE-3"]
    for original, projected in zip(
        state["workpapers"][0]["versions"], view["workpapers"][0]["versions"], strict=True
    ):
        assert "text" not in projected and projected["_workspace_text"]["loaded"] is False
        assert (
            projected["task_ids"] == original["task_ids"]
            and projected["evidence_ids"] == original["evidence_ids"]
        )
        assert projected["_workspace_version_sha256"] == digest(original)
    pins = read_pins(state, state["workpapers"][0], "workpapers")
    old = transport.detail(state, "workpapers", "WP-1", version=1, **pins)["row"]
    assert old["versions"][0]["text"] == before["workpapers"][0]["versions"][0]["text"]
    assert (
        "text" not in old["versions"][1]
        and old["versions"][1]["_workspace_text"]["loaded"] is False
    )
    new = transport.detail(state, "workpapers", "WP-1", version=2, **pins)["row"]
    assert new["versions"][1]["text"] == before["workpapers"][0]["versions"][1]["text"]
    assert "text" not in new["versions"][0]
    trace = transport.detail(
        state,
        "sample_executions",
        "TRACE-1",
        **read_pins(state, state["sample_executions"][0], "sample_executions"),
    )["row"]
    assert trace["items"] == before["sample_executions"][0]["items"]
    assert state == before


@pytest.mark.parametrize(
    "change", ["revision", "scope", "clock", "role", "source", "engagement", "object"]
)
def test_stale_or_foreign_pins_cannot_hydrate(change):
    state = fixture_state()
    pins = read_pins(state, state["workpapers"][0], "workpapers")
    if change == "revision":
        state["revision"] += 1
    elif change == "scope":
        state["scope"]["period_end"] = "2028-12-31"
    elif change == "clock":
        state["simulated_at"] = "2028-01-04T00:00:00Z"
    elif change == "role":
        state["permissions"] = ["review"]
    elif change == "source":
        state["company_source_binding"]["source_revision"] += 1
    elif change == "engagement":
        state["id"] = "ENG-FOREIGN"
    else:
        state["workpapers"][0]["versions"][0]["text"] += " changed"
    with pytest.raises(DomainError) as refused:
        transport.detail(state, "workpapers", "WP-1", version=1, **pins)
    assert refused.value.status == 409


def test_boolean_version_does_not_substitute_for_integer_or_expose_text():
    state = fixture_state()
    state["workpapers"][0]["versions"][0]["version"] = True
    pins = read_pins(state, state["workpapers"][0], "workpapers")
    assert "text" not in transport.summary(state)["workpapers"][0]["versions"][0]
    with pytest.raises(DomainError):
        transport.detail(state, "workpapers", "WP-1", version=1, **pins)
    with pytest.raises(DomainError):
        transport.detail(state, "workpapers", "WP-1", version=True, **pins)
    with pytest.raises(DomainError):
        transport.detail(state, "workpapers", "WP-1", version=2, **{**pins, "revision": True})


def test_exact_original_selection_preserves_earlier_exception_and_non_citing_successor():
    state = fixture_state()
    result = transport.sample_original_context(
        state, "ART-1", revision=8, source_epoch=transport.epoch(state), artifact_sha256="a" * 64
    )
    assert [r["id"] for r in result["traces"]] == ["TRACE-1", "TRACE-2"]
    assert result["traces"][0]["items"][0]["observation"] == "Earlier exception"
    assert result["traces"][1]["items"][0]["evidence"] == []
    assert (
        result["retained_trace_count"] == 3 and result["complete_exact_original_selection"] is True
    )


def test_http_read_mutation_replay_authority_epoch_and_source_exclusion(tmp_path):
    app = create_app(tmp_path / "state", allowed_hosts=["testserver"])
    engine = app.state.engine
    owner = engine.store.provision("Transport learner", ["learner"])
    outsider = engine.store.provision("Transport outsider", ["learner"])
    fixture = fixture_state()
    fixture.pop("id")
    fixture.pop("revision")
    fixture.pop("permissions")
    state = engine.store.create(owner["id"], fixture, "transport-fixture")
    client = TestClient(app, base_url="https://testserver")
    auth = {"Authorization": "Bearer " + owner["credential"]}
    compact = {**auth, "X-Workspace-View": "summary-v1"}
    base = "/api/engagements/" + state["id"]
    before = engine.store.get(owner["id"], state["id"])
    view_response = client.get(base, headers=compact)
    assert view_response.status_code == 200, view_response.text
    view = view_response.json()
    assert "text" not in view["workpapers"][0]["versions"][0]
    full = client.get(base, headers=auth).json()
    assert full["workpapers"][0]["versions"][0]["text"] == "Old 🧭 retained quote"
    pin = view["workpapers"][0]["_workspace_detail"]
    params = dict(
        observed_revision=view["revision"],
        source_epoch=pin["source_epoch_sha256"],
        object_sha256=pin["object_sha256"],
        version=1,
    )
    route = base + "/workspace/workpapers/WP-1"
    detailed = client.get(route, headers=auth, params=params)
    assert (
        detailed.status_code == 200
        and detailed.json()["row"]["versions"][0]["text"] == "Old 🧭 retained quote"
    )
    assert (
        client.get(
            route, headers={"Authorization": "Bearer " + outsider["credential"]}, params=params
        ).status_code
        == 403
    )
    original = base + "/workspace/sample-original-context/ART-PRIVATE"
    assert (
        client.get(
            original,
            headers=auth,
            params=dict(
                observed_revision=view["revision"],
                source_epoch=pin["source_epoch_sha256"],
                artifact_sha256="b" * 64,
            ),
        ).status_code
        == 404
    )
    assert client.get(route, headers=auth, params={**params, "version": "true"}).status_code == 422
    assert engine.store.get(owner["id"], state["id"]) == before
    engine.store.grant(state["id"], owner["id"], "review")
    assert client.get(route, headers=auth, params=params).status_code == 409
    engine.store.grant(state["id"], owner["id"], "learn")
    envelope = dict(
        command_id="transport-note",
        expected_revision=state["revision"],
        kind="note.create",
        payload={"text": "Ordinary command"},
    )
    assert (
        client.post(
            base + "/commands", headers={**auth, "X-Workspace-View": "invalid"}, json=envelope
        ).status_code
        == 422
    )
    assert engine.store.get(owner["id"], state["id"]) == before
    result = client.post(base + "/commands", headers=compact, json=envelope)
    assert result.status_code == 200, result.text
    assert result.json()["workspace_transport"]["stored_records_or_history_changed"] is False
    assert "text" not in result.json()["workpapers"][0]["versions"][0]
    stored = engine.store.get(owner["id"], state["id"])
    assert "workspace_transport" not in stored and stored["workpapers"] == before["workpapers"]
    replay = client.post(base + "/commands", headers=compact, json=envelope)
    assert replay.status_code == 200 and replay.json()["revision"] == result.json()["revision"]
    assert client.get(route, headers=auth, params=params).status_code == 409
    uploaded = client.post(
        base + "/uploads",
        headers=compact,
        data={
            "kind": "workpaper",
            "expected_revision": str(stored["revision"]),
            "command_id": "transport-upload",
        },
        files={"file": ("manual-original.txt", b"Manual uploaded original", "text/plain")},
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["workspace_transport"]["stored_records_or_history_changed"] is False
    assert all(
        "text" not in v for paper in uploaded.json()["workpapers"] for v in paper["versions"]
    )
    engine.store.revoke(owner["id"])
    assert client.get(route, headers=auth, params=params).status_code == 401
