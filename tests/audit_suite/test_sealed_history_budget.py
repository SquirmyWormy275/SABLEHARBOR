"""Interactive selection cannot materialize an entire retained state journal."""

import json
import re

import pytest

from enterprise.audit_suite.sealed_history_store import SealedHistoryStore, prepare_tail
from enterprise.audit_suite.store import DomainError, Store, canonical
from tests.audit_suite.test_persistent_company_service import login
from tests.audit_suite.test_sealed_retained_service import explained, seal

pytest_plugins = [
    "tests.audit_suite.test_persistent_company_service",
    "tests.audit_suite.test_retained_explanation_service",
]


def test_eager_history_refuses_before_even_a_declared_giant_state_is_decoded(tmp_path, monkeypatch):
    tmp_path.chmod(0o700)
    original = Store(tmp_path / "original")
    person = original.provision("Original operator", ["instructor"])
    state = original.create(person["id"], {"mode": "CLEAN", "scope": {}, "notes": []}, "birth")
    choice = prepare_tail(original, person["id"], state["id"], tmp_path / "tail", state_codec=True)
    store = SealedHistoryStore(original.root, choice["path"], choice["sha256"])
    # Own negative engineering fixture: no giant state bytes are created. The
    # unbounded API must refuse even if a frame claims a 238 MB state, before
    # any decode, array assembly or acceptance of its malformed root.
    with store.connect() as db:
        db.execute(
            "INSERT INTO main.event_frames VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                state["id"],
                1,
                "giant-declared-frame",
                "a" * 64,
                person["id"],
                0.0,
                store.prefix["last_hash"],
                "b" * 64,
                canonical({"root": "c" * 64, "bytes": 238_423_640, "sha256": "d" * 64}),
                "{}",
            ),
        )
    queries = []
    connect = store.connect

    def refusing_decode(_raw):
        pytest.fail("An eager history refusal must never decode a state")

    def traced():
        db = connect()
        db.set_trace_callback(queries.append)
        db.create_function("canonical_state_decode", 1, refusing_decode)
        return db

    monkeypatch.setattr(store, "connect", traced)
    with pytest.raises(DomainError) as raised:
        store.history(person["id"], state["id"])
    assert raised.value.code == "HISTORY_STREAM_REQUIRED" and raised.value.status == 413
    assert not any(
        query.lstrip().upper().startswith("SELECT")
        and re.search(
            r"\bFROM\s+(?:(?:main|sealed_prefix)\.)?"
            r"(?:events|event_tail|event_frames|engagements)\b",
            query,
            re.IGNORECASE,
        )
        for query in queries
    )
    with pytest.raises(DomainError) as foreign:
        store.history("unregistered-person", state["id"])
    assert foreign.value.status in (401, 403, 503)
    assert foreign.value.code != "HISTORY_STREAM_REQUIRED"


def test_selected_http_comparison_and_compact_workspace_do_not_use_eager_history(
    keycase, monkeypatch
):
    case = keycase["case"]
    seal(case, state_codec=True)
    app = explained(keycase)
    client, _ = login(app, case, "operator")

    def never_eager(*_args, **_kwargs):
        pytest.fail("Selected UI reads cannot use eager full history")

    monkeypatch.setattr(app.state.engine.store, "history", never_eager)
    prefix = "/api/engagements/" + case["engagement"]
    revision = keycase["before"]["revision"]
    response = client.get(prefix + "/instructor-comparison", params={"revision": revision})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["selected_history_revision"] == revision
    assert data["selected_state_sha256"] and data["selected_history_sha256"]
    assert "state" not in data and "history" not in data
    assert len(response.content) < app.state.engine.store.PRIVATE_VIEW_MAX_BYTES
    assert client.get(prefix + "/instructor-comparison").status_code == 422
    assert (
        client.get(prefix + "/instructor-comparison", params={"revision": 10**12}).status_code
        == 404
    )
    workspace = client.get(prefix, headers={"X-Workspace-View": "summary-v1"})
    assert workspace.status_code == 200, workspace.text
    assert workspace.json()["revision"] == revision
    assert "history" not in workspace.json()


def test_oversized_selected_view_is_refused_whole_while_company_access_continues(
    keycase, monkeypatch
):
    case = keycase["case"]
    seal(case, state_codec=True)
    app = explained(keycase)
    client, _ = login(app, case, "operator")
    prefix = "/api/engagements/" + case["engagement"]
    url = prefix + "/instructor-comparison"
    params = {"revision": keycase["before"]["revision"]}
    positive = client.get(url, params=params)
    assert positive.status_code == 200, positive.text
    monkeypatch.setattr(app.state.engine.store, "PRIVATE_VIEW_MAX_BYTES", len(positive.content) - 1)
    refused = client.get(url, params=params)
    assert refused.status_code == 413, refused.text
    assert refused.json()["code"] == "VIEW_BUDGET_EXCEEDED"
    assert (
        "expectations" not in refused.json() and "selected_history_revision" not in refused.json()
    )
    assert client.get(prefix + "/company/systems").status_code == 200


def test_budget_counts_serialized_utf8_and_keeps_exact_typed_metadata(tmp_path):
    # Isolated pure budget method: no source or audit outcome is supplied.
    store = object.__new__(SealedHistoryStore)
    value = {"typed": [False, 0, True, 1, -0.0], "label": "é🙂"}
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    store.PRIVATE_VIEW_MAX_BYTES = len(raw)
    assert store.check_private_view_budget(value) is value
    store.PRIVATE_VIEW_MAX_BYTES -= 1
    with pytest.raises(DomainError, match="response budget") as refused:
        store.check_private_view_budget(value)
    assert refused.value.status == 413
