import pytest

from enterprise.audit_suite.history_inspection import inspect_history
from enterprise.audit_suite.store import DomainError, digest
from tests.audit_suite.test_explanation_binding import workspace as base_workspace
from tests.audit_suite.test_instructor_comparison import advance


@pytest.fixture
def workspace(tmp_path):
    return base_workspace.__wrapped__(tmp_path)


def test_exact_unicode_prefixes_selected_states_and_actor_metadata(workspace):
    engine, args = workspace
    for index in range(4):
        advance(engine, args, lambda s, index=index: {**s, "title": f"Unicode 雪 é {index}"})
    old = engine.store.history(args["instructor_id"], args["engagement_id"])
    result = inspect_history(
        engine.store, args["instructor_id"], args["engagement_id"], revisions=[0, 2, 4, 9]
    )
    assert result["history_sha256"] == digest(old)
    assert result["latest"] == old[-1]
    assert set(result["selected"]) == {0, 2, 4}
    for revision in result["selected"]:
        assert result["selected"][revision] == old[revision]
        assert result["prefix_sha256"][revision] == digest(old[: revision + 1])
    assert all("state" not in row for row in result["activity"])
    for actual, original in zip(result["activity"], old, strict=True):
        assert actual == {
            k: original[k] for k in ("actor", "recorded_at", "command_id", "hash", "revision")
        } | {"command": {"kind": original["command"].get("kind")}}


@pytest.mark.parametrize(
    "field,value",
    [("hash", "bad"), ("request_hash", "bad"), ("previous_hash", "bad"), ("state", "{}")],
)
def test_corrupt_event_never_yields_inspection(workspace, field, value):
    engine, args = workspace
    with engine.store.connect() as db:
        db.execute("DROP TRIGGER events_no_update")
        db.execute(
            f"UPDATE events SET {field}=? WHERE engagement=?", (value, args["engagement_id"])
        )
    with pytest.raises(DomainError, match="integrity"):
        inspect_history(engine.store, args["instructor_id"], args["engagement_id"])


def test_state_tip_disagreement_fails(workspace):
    engine, args = workspace
    with engine.store.connect() as db:
        db.execute("UPDATE engagements SET state=? WHERE id=?", ("{}", args["engagement_id"]))
    with pytest.raises(DomainError, match="state mismatch"):
        inspect_history(engine.store, args["instructor_id"], args["engagement_id"])


def test_revoked_actor_denied(workspace):
    engine, args = workspace
    with engine.store.connect() as db:
        db.execute("UPDATE principals SET revoked=1 WHERE id=?", (args["instructor_id"],))
    with pytest.raises(DomainError):
        inspect_history(engine.store, args["instructor_id"], args["engagement_id"])


def test_revocation_after_stream_before_return_is_rechecked(workspace, monkeypatch):
    engine, args = workspace
    original = engine.store._authorize
    calls = 0

    def authorize(db, actor, engagement):
        nonlocal calls
        calls += 1
        if calls == 2:
            with engine.store.connect() as changed:
                changed.execute("UPDATE principals SET revoked=1 WHERE id=?", (actor,))
        return original(db, actor, engagement)

    monkeypatch.setattr(engine.store, "_authorize", authorize)
    with pytest.raises(DomainError) as error:
        inspect_history(engine.store, args["instructor_id"], args["engagement_id"])
    assert calls == 2
    assert error.value.status == 401


def test_key_capture_and_comparison_do_not_materialize_public_history(workspace, monkeypatch):
    from enterprise.audit_suite.explanation_binding import bind_snapshot
    from enterprise.audit_suite.instructor_comparison import compare

    engine, args = workspace

    def prohibited(*_args, **_kwargs):
        raise AssertionError("Full history materialization is prohibited in this path")

    monkeypatch.setattr(engine.store, "history", prohibited)
    receipt = bind_snapshot(engine, **args)
    bindings = {
        args["engagement_id"]: {
            "path": args["output"],
            "manifest_sha256": receipt["manifest_sha256"],
        }
    }
    result = compare(
        engine, {"id": args["instructor_id"]}, args["engagement_id"], bindings, revision=0
    )
    assert result["status"] == "DETERMINISTIC_LINK_INVENTORY_ONLY"


def test_legacy_noncanonical_json_preserves_exact_public_digest(workspace):
    import json

    engine, args = workspace
    values = {
        "numeric": [-0.0, 1.0, 1e30, 1e-8, 123456789012345678901234567890],
        "escaped": ["雪", "é", "\\n", "\n", '"},"state":{}'],
        "nested": {"z": True, "a": None, "empty": []},
    }
    advance(engine, args, lambda s: {**s, "legacy_values": values})
    expected = engine.store.history(args["instructor_id"], args["engagement_id"])
    with engine.store.connect() as db:
        db.execute("DROP TRIGGER events_no_update")
        for row in db.execute(
            "SELECT revision,state,command FROM events WHERE engagement=?", (args["engagement_id"],)
        ).fetchall():
            # Keep legacy json.loads last-key-wins behavior too: do not use stored
            # bytes as canonical or introduce a stricter parser in this optimization.
            state = json.loads(row["state"])
            pretty = json.dumps(state, ensure_ascii=True, indent=3)
            stored = json.dumps({next(iter(state)): "ignored duplicate"})[:-1] + "," + pretty[1:]
            # Physical JSON differs, while the parsed state and command retain their meaning.
            db.execute(
                "UPDATE events SET state=?,command=? WHERE engagement=? AND revision=?",
                (
                    stored,
                    json.dumps(json.loads(row["command"]), ensure_ascii=True, indent=2),
                    args["engagement_id"],
                    row["revision"],
                ),
            )
    result = inspect_history(
        engine.store,
        args["instructor_id"],
        args["engagement_id"],
        revisions=list(range(len(expected))),
    )
    assert result["history_sha256"] == digest(expected)
    for index, entry in enumerate(expected):
        assert result["selected"][index] == entry
        assert result["prefix_sha256"][index] == digest(expected[: index + 1])
    assert engine.store.history(args["instructor_id"], args["engagement_id"]) == expected


def test_each_parsed_full_state_canonicalized_once(workspace, monkeypatch):
    from enterprise.audit_suite import history_inspection as module

    engine, args = workspace
    for _index in range(3):
        advance(engine, args, lambda state: {**state, "title": "Large selected state"})
    expected = engine.store.history(args["instructor_id"], args["engagement_id"])
    original = module.canonical
    states = []

    def counted(value):
        if isinstance(value, dict) and value.get("id") == args["engagement_id"]:
            states.append(value["revision"])
        assert not (isinstance(value, dict) and "state" in value and "previous_hash" in value), (
            "Do not serialize a second whole-state envelope"
        )
        return original(value)

    monkeypatch.setattr(module, "canonical", counted)
    result = module.inspect_history(
        engine.store, args["instructor_id"], args["engagement_id"], revisions=[0, len(expected) - 1]
    )
    assert states == list(range(len(expected)))
    assert result["history_sha256"] == digest(expected)


def test_revision_advance_after_stream_is_rejected(workspace, monkeypatch):
    engine, args = workspace
    original = engine.store._authorize
    calls = 0

    def authorize(db, actor, engagement, permissions=None):
        nonlocal calls
        calls += 1
        if calls == 2:
            advance(engine, args, lambda state: {**state, "title": "Concurrent update"})
        return original(db, actor, engagement, permissions)

    monkeypatch.setattr(engine.store, "_authorize", authorize)
    with pytest.raises(DomainError, match="changed during history inspection") as error:
        inspect_history(engine.store, args["instructor_id"], args["engagement_id"], revisions=[0])
    assert error.value.status == 409


def test_tail_integrity_checked_even_when_only_first_state_requested(workspace):
    engine, args = workspace
    advance(engine, args, lambda state: {**state, "title": "Later state"})
    with engine.store.connect() as db:
        db.execute("DROP TRIGGER events_no_update")
        db.execute(
            "UPDATE events SET request_hash=? WHERE engagement=? AND revision=1",
            ("0" * 64, args["engagement_id"]),
        )
    with pytest.raises(DomainError, match="integrity"):
        inspect_history(engine.store, args["instructor_id"], args["engagement_id"], revisions=[0])
