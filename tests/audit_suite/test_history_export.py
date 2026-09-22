"""Complete bounded archive history without the materializing Store.history API."""

import json

import pytest

from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.history_export import history_json
from enterprise.audit_suite.store import DomainError, canonical


@pytest.fixture
def history_context(tmp_path):
    engine = Engine(tmp_path / "audit")
    actor = engine.store.provision("History preparer", ["learner"])["id"]
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="History fixture",
        phase="ACTIVE",
        scope={},
        configuration={"private_seed": "WITHHELD_SEED"},
        simulated_at="2027-01-01T00:00:00Z",
    )
    state = engine.store.create(actor, state, "create")
    for n in range(5):
        state = engine.store.command(
            actor,
            state["id"],
            {
                "kind": "fixture",
                "payload": {},
                "command_id": f"c{n}",
                "expected_revision": state["revision"],
            },
            lambda s, c, a: {**s, "title": s["title"] + "x"},
            permissions={"learn"},
        )
    return engine, actor, state


def test_streamed_history_is_byte_identical_and_prefix_exact(history_context, monkeypatch):
    engine, actor, state = history_context
    expected = engine.store.history(actor, state["id"])
    monkeypatch.setattr(
        engine.store, "history", lambda *a, **k: pytest.fail("Materialized all history")
    )
    raw = history_json(
        engine.store, actor, state["id"], revision=state["revision"], max_bytes=1024 * 1024
    )
    assert raw == canonical(expected).encode()
    prefix = history_json(engine.store, actor, state["id"], revision=2, max_bytes=1024 * 1024)
    assert json.loads(prefix) == expected[:3]


def test_byte_limit_stops_projection_early_without_partial_output(history_context):
    engine, actor, state = history_context
    seen = []

    def project(entry):
        seen.append(entry["revision"])
        return entry

    with pytest.raises(DomainError) as error:
        history_json(
            engine.store,
            actor,
            state["id"],
            revision=state["revision"],
            max_bytes=2,
            project=project,
        )
    assert error.value.code == "EXPORT_LIMIT" and error.value.status == 413
    assert seen == [0]


def test_final_access_recheck_denies_a_revoked_reader(history_context):
    engine, actor, state = history_context

    # Revoke the principal after the final row without deleting retained history.
    def project(entry):
        if entry["revision"] == state["revision"]:
            engine.store.revoke(actor)
        return entry

    with pytest.raises(DomainError):
        history_json(
            engine.store,
            actor,
            state["id"],
            revision=state["revision"],
            max_bytes=1024 * 1024,
            project=project,
        )


def test_ordinary_export_uses_stream_and_still_redacts_private_configuration(
    history_context, monkeypatch
):
    import io
    import zipfile

    engine, actor, state = history_context
    monkeypatch.setattr(
        engine.store, "history", lambda *a, **k: pytest.fail("Materialized all history")
    )
    before = engine.store.get(actor, state["id"])
    engine._export(state, {}, {"actor": actor, "recorded_at": state["simulated_at"]})
    with zipfile.ZipFile(io.BytesIO(engine.artifacts.read(state["artifacts"][-1]))) as archive:
        rows = json.loads(archive.read("history.json"))
        assert len(rows) == 6
        assert all("configuration" not in row["state"] for row in rows)
        assert b"WITHHELD_SEED" not in archive.read("history.json")
    assert engine.store.get(actor, state["id"]) == before


@pytest.mark.parametrize("damage", ["state", "request_hash", "previous_hash", "missing"])
def test_corrupt_retained_prefix_never_returns_export(history_context, damage):
    engine, actor, state = history_context
    # Deliberately corrupt only the disposable fixture to exercise offline integrity.
    with engine.store.connect() as db:
        db.execute("DROP TRIGGER events_no_update")
        db.execute("DROP TRIGGER events_no_delete")
        if damage == "missing":
            db.execute("DELETE FROM events WHERE engagement=? AND revision=2", (state["id"],))
        else:
            column, value = {
                "state": ("state", canonical({"forged": True})),
                "request_hash": ("request_hash", "0" * 64),
                "previous_hash": ("previous_hash", "0" * 64),
            }[damage]
            db.execute(
                "UPDATE events SET " + column + "=? WHERE engagement=? AND revision=2",
                (value, state["id"]),
            )
    with pytest.raises(DomainError) as error:
        history_json(
            engine.store, actor, state["id"], revision=state["revision"], max_bytes=1024 * 1024
        )
    assert error.value.code == "INTEGRITY"


def test_exact_utf8_byte_boundary_includes_array_delimiters(history_context):
    engine, actor, state = history_context

    def project(entry):
        return {"revision": entry["revision"], "text": "🙂漢字"}

    raw = history_json(
        engine.store,
        actor,
        state["id"],
        revision=state["revision"],
        max_bytes=1024 * 1024,
        project=project,
    )
    assert (
        history_json(
            engine.store,
            actor,
            state["id"],
            revision=state["revision"],
            max_bytes=len(raw),
            project=project,
        )
        == raw
    )
    with pytest.raises(DomainError) as error:
        history_json(
            engine.store,
            actor,
            state["id"],
            revision=state["revision"],
            max_bytes=len(raw) - 1,
            project=project,
        )
    assert error.value.code == "EXPORT_LIMIT"


def test_missing_requested_tail_is_integrity_error(history_context):
    engine, actor, state = history_context
    with pytest.raises(DomainError) as error:
        history_json(
            engine.store,
            actor,
            state["id"],
            revision=state["revision"] + 1,
            max_bytes=1024 * 1024,
        )
    assert error.value.code == "INTEGRITY"


def test_oversized_native_row_rejected_before_event_decode(history_context, monkeypatch):
    from enterprise.audit_suite import history_export

    engine, actor, state = history_context
    monkeypatch.setattr(history_export, "MAX_EVENT_BYTES", 1)
    original = history_export.json.loads

    def guarded_load(value, *args, **kwargs):
        # Authentication can decode principal roles, but no event state/command.
        if isinstance(value, str) and value.startswith("{"):
            pytest.fail("Oversized event fetched and decoded before quota rejection")
        return original(value, *args, **kwargs)

    monkeypatch.setattr(history_export.json, "loads", guarded_load)
    with pytest.raises(DomainError) as error:
        history_export.history_json(
            engine.store, actor, state["id"], revision=state["revision"], max_bytes=1024 * 1024
        )
    assert error.value.code == "EXPORT_LIMIT"


@pytest.mark.parametrize("budget", [2, 1024 * 1024])
def test_history_transaction_connection_closes_success_and_failure(
    history_context, monkeypatch, budget
):
    import sqlite3

    engine, actor, state = history_context
    connect = engine.store.connect
    connections = []

    def track():
        db = connect()
        connections.append(db)
        return db

    monkeypatch.setattr(engine.store, "connect", track)
    if budget == 2:
        with pytest.raises(DomainError):
            history_json(engine.store, actor, state["id"], revision=0, max_bytes=budget)
    else:
        history_json(engine.store, actor, state["id"], revision=0, max_bytes=budget)
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connections[0].execute("SELECT 1")
    # Membership uses its existing Store context; close test-retained spy references.
    for connection in connections[1:]:
        connection.close()
