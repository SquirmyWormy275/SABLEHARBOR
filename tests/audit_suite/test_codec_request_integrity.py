"""Request-local reuse cannot survive writes, source/auth changes or delivery."""

import pytest

from enterprise.audit_suite import request_integrity
from enterprise.audit_suite.canonical_state_codec import VerifiedInvocationGraph
from enterprise.audit_suite.sealed_history_store import SealedHistoryStore, prepare_tail
from enterprise.audit_suite.store import Store
from tests.audit_suite.test_persistent_company_service import http_command, login
from tests.audit_suite.test_sealed_retained_service import explained, seal

pytest_plugins = [
    "tests.audit_suite.test_persistent_company_service",
    "tests.audit_suite.test_retained_explanation_service",
]


def test_nested_real_private_request_checks_graph_once_and_clears_after_delivery(
    keycase, monkeypatch
):
    case = keycase["case"]
    seal(case, state_codec=True)
    app = explained(keycase)
    client, headers = login(app, case, "operator")
    scopes = []
    finish = request_integrity.finish

    def record(scope, token):
        scopes.append((scope, scope.fresh_graphs, scope.graph_reuses))
        return finish(scope, token)

    monkeypatch.setattr(request_integrity, "finish", record)
    url = "/api/engagements/" + case["engagement"] + "/instructor-binding"
    for _ in range(2):
        response = client.get(url)
        assert response.status_code == 200, response.text
        scope, fresh, reuse = scopes[-1]
        assert fresh == 1 and reuse >= 1
        assert scope.closed and not scope._entries
    assert scopes[-1][0] is not scopes[-2][0]
    assert request_integrity.current() is None
    after = http_command(
        client,
        headers,
        case,
        "note.create",
        {"title": "Actual append", "text": "Reverify the new graph image"},
    )
    assert after.status_code == 200
    response = client.get(url)
    assert response.status_code == 200, response.text
    assert scopes[-1][1] == 1 and scopes[-1][2] >= 1


@pytest.mark.parametrize("change", ["native_original", "key", "logout", "membership"])
def test_request_local_graph_cannot_hide_in_handler_source_key_or_current_auth_change(
    keycase, monkeypatch, change
):
    case = keycase["case"]
    seal(case, state_codec=True)
    app = explained(keycase)
    client, _ = login(app, case, "operator")
    url = "/api/engagements/" + case["engagement"] + "/instructor-binding"
    assert client.get(url).status_code == 200
    route = next(
        r
        for r in app.router.routes
        if getattr(r, "path", None) == "/api/engagements/{engagement_id}/instructor-binding"
    )
    original = route.dependant.call

    async def changed(*args, **kwargs):
        response = await original(*args, **kwargs)
        if change == "logout":
            token = next(
                v for k, v in kwargs["request"].cookies.items() if k.startswith("sh_audit_session_")
            )
            app.state.engine.store.logout(token)
        elif change == "membership":
            app.state.engine.store.grant(case["engagement"], case["ids"]["operator"], "learn")
        elif change == "key":
            path = keycase["snapshot"] / "snapshot.json"
            path.write_bytes(path.read_bytes() + b" ")
        else:
            path = case["root"] / "artifacts" / keycase["before"]["artifacts"][0]["sha256"]
            path.write_bytes(path.read_bytes() + b" ")
        return response

    route.dependant.call = changed
    response = client.get(url)
    assert response.status_code in (401, 403, 503), response.text
    assert "snapshot" not in response.json()


def test_same_http_scope_real_tail_append_invalidates_all_node_proof(tmp_path):
    tmp_path.chmod(0o700)
    original = Store(tmp_path / "original")
    person = original.provision("Original operator", ["instructor"])
    state = original.create(person["id"], {"mode": "CLEAN", "scope": {}, "notes": []}, "birth")
    choice = prepare_tail(original, person["id"], state["id"], tmp_path / "tail", state_codec=True)
    store = SealedHistoryStore(original.root, choice["path"], choice["sha256"])
    scope, token = request_integrity.begin()
    try:
        for _ in range(2):
            with store.connect() as db:
                store.verify_projection(db)
                first = db._codec_invocation
                store.verify_projection(db)
                assert db._codec_invocation is first
                assert type(first) is VerifiedInvocationGraph
        assert scope.fresh_graphs == 1 and scope.graph_reuses == 1
        store.command(
            person["id"],
            state["id"],
            {
                "command_id": "ordinary-note",
                "kind": "neutral.note",
                "expected_revision": 0,
                "payload": {},
            },
            lambda old, *_: old | {"notes": ["New exact note"]},
            permissions={"instruct"},
        )
        with store.connect() as db:
            store.verify_projection(db)
        assert scope.fresh_graphs == 2
    finally:
        request_integrity.finish(scope, token)
    assert scope.closed and not scope._entries
    with store.connect() as db:
        store.verify_projection(db)
    assert request_integrity.current() is None


def test_tail_clock_cannot_go_back_before_latest_original_prefix_clock(keycase):
    from tests.audit_suite.test_persistent_company_service import command

    case = keycase["case"]
    command(
        case["engine"],
        case["ids"]["operator"],
        case["engagement"],
        "clock.advance",
        {"mode": "TARGET_DATE", "target": "2027-01-12T09:00:00Z"},
    )
    seal(case, state_codec=True)
    app = explained(keycase)
    client, _headers = login(app, case, "operator")
    store = app.state.engine.store
    state = store.get(case["ids"]["operator"], case["engagement"])
    # Own engineering Store counter emits a fully hash-valid tail state; no
    # source, principal, original history or Key bytes are altered.
    store.command(
        case["ids"]["operator"],
        case["engagement"],
        {
            "command_id": "backwards-clock-probe",
            "kind": "engineering.clock.counter",
            "expected_revision": state["revision"],
            "payload": {},
        },
        lambda old, *_: old | {"simulated_at": "2027-01-10T09:00:00Z"},
        permissions={"instruct"},
    )
    response = client.get("/api/engagements/" + case["engagement"] + "/instructor-binding")
    assert response.status_code == 503 and "snapshot" not in response.json()
