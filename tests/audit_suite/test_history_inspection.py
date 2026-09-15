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
