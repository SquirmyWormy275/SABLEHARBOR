import pytest

from enterprise.audit_suite import visit_checkpoints as module
from enterprise.audit_suite.store import DomainError
from enterprise.audit_suite.visit_checkpoints import VisitCheckpoints
from tests.audit_suite.test_workspace_context import change
from tests.audit_suite.test_workspace_context import workspace as workspace


@pytest.fixture
def visits(workspace, tmp_path):
    _, engine, actor, state = workspace
    state = change(engine, actor, state, lambda s: s["artifacts"][0].update(status="AVAILABLE"))
    root = tmp_path / "visits"
    root.mkdir(mode=0o700)
    return VisitCheckpoints(root, engine), engine, actor, state


def capture(v, a, s, version=0, command="capture"):
    return v.capture(
        a,
        s["id"],
        expected_version=version,
        expected_engagement_revision=s["revision"],
        command_id=command,
    )


def compare(v, a, s, version=1):
    return v.compare(
        a, s["id"], expected_version=version, expected_engagement_revision=s["revision"]
    )


def test_explicit_checkpoint_exact_changes_history_and_replay(visits):
    v, e, a, s = visits
    before = e.store.get(a, s["id"])
    assert v.status(a, s["id"])["status"] == "NO_CHECKPOINT"
    first = capture(v, a, s)
    assert capture(v, a, s) == first
    assert compare(v, a, s)["counts"] == {"added": 0, "changed": 0, "unchanged": 4}
    assert e.store.get(a, s["id"]) == before

    def edit(state):
        state["tasks"][0]["note"] = "new formal note"
        state["workpapers"][0]["versions"].append({"version": 2, "text": "Second version"})

    changed = change(e, a, s, edit)
    result = compare(v, a, changed)
    assert result["counts"] == {"added": 1, "changed": 1, "unchanged": 3}
    assert {r["current"]["reference"]["kind"] for r in result["changes"]} == {"task", "workpaper"}
    wp = next(r for r in result["changes"] if r["change"] == "ADDED")
    assert wp["current"]["reference"]["version"] == 2 and wp["prior"] is None
    assert capture(v, a, changed, 1, "replace")["version"] == 2
    with pytest.raises(DomainError, match="command reused"):
        capture(v, a, s)  # Old retry cannot silently resolve to a replacement checkpoint.
    assert capture(v, a, changed, 1, "replace")["version"] == 2
    assert len(v.history(a, s["id"])["checkpoints"]) == 2
    assert VisitCheckpoints(v.root, e).status(a, s["id"])["version"] == 2
    assert compare(v, a, changed, 2)["counts"]["changed"] == 0


@pytest.mark.parametrize(
    "field", ["scope", "company_source_binding", "evidence_acquisition", "permissions"]
)
def test_changed_basis_redacts_all_counts_and_details(visits, field):
    v, e, a, s = visits
    capture(v, a, s)
    changed = change(
        e,
        a,
        s,
        lambda state: state.__setitem__(
            field, {"changed": True} if field != "permissions" else ["changed"]
        ),
    )
    if field == "permissions":
        e.store.grant(s["id"], a, "review")
    result = compare(v, a, changed)
    assert result["status"] == "CONTEXT_CHANGED"
    assert "counts" not in result and "changes" not in result
    assert "inventory" not in str(v.history(a, s["id"]))
    assert capture(v, a, s)["status"] == "CONTEXT_CHANGED"


@pytest.mark.parametrize(
    "edit",
    [
        lambda s: s["artifacts"].clear(),
        lambda s: s["artifacts"][0].update(audience="INSTRUCTOR"),
        lambda s: s["artifacts"][0].update(status="QUARANTINED"),
    ],
)
def test_revoked_or_missing_record_redacts_entire_comparison(visits, edit):
    v, e, a, s = visits
    capture(v, a, s)
    changed = change(e, a, s, edit)
    result = compare(v, a, changed)
    assert result["status"] == "TARGET_UNAVAILABLE"
    assert "A1" not in str(result) and "counts" not in result and "changes" not in result


def test_no_hidden_key_future_events_original_reads_or_formal_mutation(visits, monkeypatch):
    v, e, a, s = visits

    def edit(state):
        state["artifacts"].append(
            {"id": "SECRET", "audience": "INSTRUCTOR", "status": "AVAILABLE", "sha256": "b" * 64}
        )
        state["private_truth"] = {"hidden": "answer"}
        state["future_events"] = [{"id": "FUTURE", "content": "secret"}]

    s = change(e, a, s, edit)
    monkeypatch.setattr(e.artifacts, "read", lambda *args: pytest.fail("No original bytes read"))
    capture(v, a, s)
    with v._db() as db:
        text = db.execute("SELECT content FROM checkpoint_history").fetchone()[0]
    assert all(value not in text for value in ("SECRET", "FUTURE", "answer", "Original work"))
    assert e.store.get(a, s["id"])["revision"] == s["revision"]


def test_cross_actor_private_and_revoked_membership(visits):
    v, e, a, s = visits
    capture(v, a, s)
    other = e.store.provision("Other learner", ["learner"])["id"]
    e.store.grant(s["id"], other, "learn")
    assert v.status(other, s["id"])["version"] == 0
    assert v.history(other, s["id"])["checkpoints"] == []
    with e.store.connect() as db:
        db.execute("DELETE FROM members WHERE principal=? AND engagement=?", (a, s["id"]))
    with pytest.raises(DomainError):
        v.status(a, s["id"])


def test_limits_no_partial_counts_and_no_failed_capture_commit(visits, monkeypatch):
    v, e, a, s = visits
    capture(v, a, s)
    monkeypatch.setattr(module, "MAX_PINS", 4)
    changed = change(e, a, s, lambda state: state["tasks"].append({"id": "T2", "control_id": "C1"}))
    result = compare(v, a, changed)
    assert result["status"] == "INPUT_LIMIT_EXCEEDED" and "counts" not in result
    with pytest.raises(DomainError):
        capture(v, a, changed, 1, "overflow")
    assert v.status(a, s["id"])["version"] == 1


def test_capture_final_context_change_rolls_back(visits, monkeypatch):
    v, e, a, s = visits
    original = v._recheck
    calls = 0

    def raced(*args):
        nonlocal calls
        calls += 1
        if calls == 2:
            change(e, a, s, lambda state: state["scope"].update(boundaries=[]))
        return original(*args)

    monkeypatch.setattr(v, "_recheck", raced)
    with pytest.raises(DomainError):
        capture(v, a, s)
    with v._db() as db:
        assert db.execute("SELECT count(*) FROM checkpoint_history").fetchone()[0] == 0


def test_exact_cas_and_command_fingerprint(visits):
    v, e, a, s = visits
    capture(v, a, s)
    with pytest.raises(DomainError):
        capture(v, a, s, 1)  # same command, changed envelope
    with pytest.raises(DomainError):
        capture(v, a, s, 0, "stale")
    with pytest.raises(DomainError):
        compare(v, a, s, 0)


def test_future_available_original_excluded_and_later_visible_is_added(visits):
    v, e, a, s = visits
    s = change(
        e,
        a,
        s,
        lambda state: state["artifacts"].append(
            {
                "id": "FUTURE",
                "version": 1,
                "status": "AVAILABLE",
                "sha256": "f" * 64,
                "available_at": "2027-02-01T00:00:00Z",
            }
        ),
    )
    capture(v, a, s)
    with v._db() as db:
        assert "FUTURE" not in db.execute("SELECT content FROM checkpoint_history").fetchone()[0]
    s = change(e, a, s, lambda state: state.update(simulated_at="2027-02-01T00:00:00Z"))
    result = compare(v, a, s)
    assert result["counts"]["added"] == 1
    assert result["changes"][0]["current"]["reference"]["id"] == "FUTURE"


def test_inert_snapshot_roundtrip_and_tamper_rejection(visits):
    import json
    from copy import deepcopy

    from enterprise.audit_suite.store import canonical, digest
    from enterprise.audit_suite.visit_checkpoints import validate_snapshot

    v, e, a, s = visits
    capture(v, a, s)
    capture(v, a, s, 1, "replace")
    value = v.snapshot()
    assert validate_snapshot(deepcopy(value)) == value
    assert len(value["tables"]["checkpoint_history"]) == 2
    wrong = deepcopy(value)
    wrong["tables"]["checkpoint_commands"][0]["fingerprint"] = "0" * 64
    with pytest.raises(DomainError):
        validate_snapshot(wrong)
    wrong = deepcopy(value)
    row = wrong["tables"]["checkpoint_history"][1]
    body = json.loads(row["content"])
    body["predecessor_sha256"] = "0" * 64
    row.update(content=canonical(body), sha256=digest(body))
    with pytest.raises(DomainError):
        validate_snapshot(wrong)
    with v._db() as db:
        db.execute("UPDATE checkpoints SET version=1")
    with pytest.raises(DomainError):
        v.status(a, s["id"])


def test_no_silent_partial_inventory_on_duplicate_identity(visits):
    v, e, a, s = visits
    capture(v, a, s)
    s = change(e, a, s, lambda state: state["controls"].append(dict(state["controls"][0])))
    result = compare(v, a, s)
    assert result["status"] == "INPUT_DATA_UNAVAILABLE" and "counts" not in result


def test_instructor_checkpoint_also_excludes_private_originals(visits):
    v, e, a, s = visits
    s = change(
        e,
        a,
        s,
        lambda state: state["artifacts"].append(
            {
                "id": "PRIVATE-KEY-ORIGINAL",
                "audience": "INSTRUCTOR",
                "status": "AVAILABLE",
                "version": 1,
                "sha256": "f" * 64,
            }
        ),
    )
    e.store.grant(s["id"], a, "instruct")
    assert any(r["id"] == "PRIVATE-KEY-ORIGINAL" for r in e.get(a, s["id"])["artifacts"])
    capture(v, a, s)
    assert "PRIVATE-KEY-ORIGINAL" not in str(v.snapshot())


def test_exact_old_new_artifact_pins_and_late_authority_guard(visits, monkeypatch):
    v, e, a, s = visits
    capture(v, a, s)
    s = change(e, a, s, lambda state: state["artifacts"][0].update(version=3, sha256="b" * 64))
    result = compare(v, a, s)
    delta = result["changes"][0]
    assert delta["prior"]["reference"]["sha256"] == "a" * 64
    assert delta["current"]["reference"]["sha256"] == "b" * 64
    assert delta["prior"]["reference"]["version"] == 2
    assert delta["current"]["reference"]["version"] == 3
    original = v._recheck

    def changed(*args):
        e.store.grant(s["id"], a, "review")
        return original(*args)

    monkeypatch.setattr(v, "_recheck", changed)
    with pytest.raises(DomainError):
        compare(v, a, s)


def test_malformed_legacy_source_metadata_is_unavailable_not_partial(visits):
    v, e, a, s = visits
    capture(v, a, s)
    s = change(e, a, s, lambda state: state["artifacts"][0].update(source="not metadata"))
    result = compare(v, a, s)
    assert result["status"] == "INPUT_DATA_UNAVAILABLE"
    assert "counts" not in result and "changes" not in result


@pytest.mark.parametrize("column,value", [("command_id", "x" * 2048), ("fingerprint", "f" * 2048)])
def test_oversized_command_metadata_rejected_before_materialization(
    visits, monkeypatch, column, value
):
    from contextlib import contextmanager

    v, e, a, s = visits
    capture(v, a, s)
    with v._db() as db:
        fields = {"command_id": "bad", "fingerprint": "f" * 64}
        fields[column] = value
        db.execute(
            "INSERT INTO checkpoint_commands VALUES(?,?,?,?,?)",
            (a, s["id"], fields["command_id"], fields["fingerprint"], 1),
        )
    original = v._db
    queries = []

    @contextmanager
    def watched():
        with original() as db:
            db.set_trace_callback(queries.append)
            yield db

    monkeypatch.setattr(v, "_db", watched)
    with pytest.raises(DomainError, match="SQL field"):
        v.status(a, s["id"])
    assert not any(
        "SELECT *" in query or "SELECT version FROM checkpoints" in query for query in queries
    )
    queries.clear()
    with pytest.raises(DomainError, match="SQL field"):
        v.snapshot()
    assert not any("SELECT *" in query for query in queries)


@pytest.mark.parametrize("version", ["not-an-integer", 1.5, "x" * 2048])
def test_head_version_requires_bounded_sql_integer_before_fetch(visits, version):
    v, e, a, s = visits
    capture(v, a, s)
    with v._db() as db:
        db.execute("UPDATE checkpoints SET version=?", (version,))
    with pytest.raises(DomainError, match="SQL field"):
        v.status(a, s["id"])
    with pytest.raises(DomainError, match="SQL field"):
        v.snapshot()
