from copy import deepcopy

import pytest

from enterprise.audit_suite import artifact_inspection
from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.history_inspection import inspect_history
from enterprise.audit_suite.store import DomainError, digest


@pytest.fixture
def work(tmp_path):
    engine = Engine(tmp_path / "audit")
    actor = engine.store.provision("Author", ["instructor"])["id"]
    learner = engine.store.provision("Learner", ["learner"])["id"]
    reviewer = engine.store.provision("Reviewer", ["reviewer"])["id"]
    eid = "ENG-" + digest([actor, "create"])[:24]
    original = engine.artifacts.retain(
        eid, "source.txt", b"Original retained bytes", source={}, coverage={}, generated=False
    )
    state = {key: [] for key in COLLECTIONS}
    state.pop("artifact_inspections")
    state.update(
        title="Neutral",
        phase="ACTIVE",
        simulated_at="2027-02-02T09:00:00Z",
        scope={"programs": ["SOC2"], "boundaries": ["Corporate"]},
        artifacts=[original],
        controls=[{"id": "C"}],
        tasks=[{"id": "T", "control_id": "C", "status": "NOT_STARTED", "conclusion": "NOT_RUN"}],
    )
    engine.store.create(actor, state, "create")
    engine.store.grant(eid, learner, "learn")
    engine.store.grant(eid, reviewer, "review")
    payload = {
        "artifact_id": original["id"],
        "sha256": original["sha256"],
        "version": None,
        "locator": "Lines 1–2",
        "observation": "Author reports inspecting the stated text",
        "task_id": "T",
    }
    return engine, actor, learner, reviewer, eid, original, payload


def command(payload, revision=0, ident="inspect"):
    return {
        "command_id": ident,
        "expected_revision": revision,
        "kind": "artifact.inspection.record",
        "payload": payload,
    }


def test_explicit_assertion_authority_replay_history_and_no_task_credit(work):
    engine, actor, learner, reviewer, eid, original, payload = work
    before = engine.store.get(actor, eid)
    assert engine.get(learner, eid)["artifact_inspections"] == []
    with pytest.raises(DomainError):
        engine.command(reviewer, eid, command(payload))
    saved = engine.command(learner, eid, command(payload))
    assert saved["tasks"] == before["tasks"]
    assert saved["workpapers"] == before["workpapers"]
    row = saved["artifact_inspections"][0]
    assert row["actor"] == learner and row["classification"] == "SELF_REPORTED_INSPECTION"
    assert row["recorded_revision"] == 1
    assert engine.command(learner, eid, command(payload))["artifact_inspections"] == [row]
    with pytest.raises(DomainError):
        engine.command(learner, eid, command(payload, ident="stale"))
    engine.command(actor, eid, command(payload, revision=1, ident="other"))
    history = inspect_history(engine.store, actor, eid, revisions=[0, 1, 2])
    for revision, own, others in [(0, 0, 0), (1, 1, 0), (2, 1, 1)]:
        result = artifact_inspection.inventory(
            history["selected"][revision]["state"], history["activity"][: revision + 1], learner
        )
        assert (result["audited_actor_count"], result["other_actor_count"]) == (own, others)
    forged = deepcopy(history["latest"]["state"])
    forged["artifact_inspections"][0]["actor"] = actor
    assert (
        artifact_inspection.inventory(forged, history["activity"], learner)[
            "unresolved_record_count"
        ]
        == 1
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("sha256", "0" * 64),
        ("version", True),
        ("version", 0),
        ("version", 1.0),
        ("locator", ""),
        ("locator", " " * 1001 + "x"),
        ("observation", "x" + " " * 4001),
        ("sha256", True),
        ("observation", " "),
        ("task_id", "UNKNOWN"),
        ("actor", "forged"),
    ],
)
def test_rejected_input_does_not_commit(work, field, value):
    engine, actor, learner, _, eid, _, payload = work
    before = engine.store.history(actor, eid)
    payload[field] = value
    with pytest.raises(DomainError):
        engine.command(learner, eid, command(payload))
    assert engine.store.history(actor, eid) == before


@pytest.mark.parametrize(
    "patch",
    [{"status": "QUARANTINED"}, {"audience": "REVIEWER"}, {"available_at": "2028-01-01T00:00:00Z"}],
)
def test_unavailable_original_denied(work, patch):
    engine, actor, learner, _, eid, _, payload = work

    def mutate(state, _c, _a):
        state["artifacts"][0].update(patch)
        return state

    engine.store.command(
        actor,
        eid,
        {"command_id": "fixture", "expected_revision": 0, "kind": "fixture", "payload": {}},
        mutate,
        permissions={"instruct"},
    )
    with pytest.raises(DomainError):
        engine.command(learner, eid, command(payload, revision=1))


def test_bytes_corruption_denied(work):
    engine, actor, learner, _, eid, original, payload = work
    (engine.artifacts.root / original["sha256"]).write_bytes(b"Different")
    with pytest.raises(DomainError):
        engine.command(learner, eid, command(payload))
    assert engine.store.get(actor, eid)["revision"] == 0


def test_exact_completed_retry_at_record_limit(work, monkeypatch):
    engine, actor, learner, _, eid, _, payload = work
    monkeypatch.setattr(artifact_inspection, "LIMIT", 1)
    saved = engine.command(learner, eid, command(payload))
    assert (
        engine.command(learner, eid, command(payload))["artifact_inspections"]
        == saved["artifact_inspections"]
    )
    with pytest.raises(DomainError):
        engine.command(learner, eid, command(payload, revision=1, ident="new"))


def test_altered_assertion_cannot_reuse_real_command_attribution(work):
    engine, actor, learner, _, eid, _, payload = work
    engine.command(learner, eid, command(payload))
    history = inspect_history(engine.store, actor, eid)
    for field, value in [
        ("observation", "Changed after command"),
        ("locator", "Other page"),
        ("task_id", None),
    ]:
        altered = deepcopy(history["latest"]["state"])
        altered["artifact_inspections"][0][field] = value
        result = artifact_inspection.inventory(altered, history["activity"], learner)
        assert result["records"] == [] and result["unresolved_record_count"] == 1


def test_final_bytes_recheck_rolls_back_assertion(work, monkeypatch):
    engine, actor, learner, _, eid, original, payload = work
    real = engine.artifacts.read
    calls = 0

    def read(row):
        nonlocal calls
        result = real(row)
        calls += 1
        if calls == 1:
            (engine.artifacts.root / original["sha256"]).write_bytes(b"Changed after first read")
        return result

    monkeypatch.setattr(engine.artifacts, "read", read)
    with pytest.raises(DomainError):
        engine.command(learner, eid, command(payload))
    assert engine.store.get(actor, eid)["revision"] == 0


def test_protected_comparison_uses_only_selected_historical_assertions(tmp_path):
    from enterprise.audit_suite.explanation_binding import bind_snapshot
    from enterprise.audit_suite.instructor_comparison import compare
    from tests.audit_suite.test_explanation_binding import workspace as base
    from tests.audit_suite.test_instructor_comparison import advance

    engine, args = base.__wrapped__(tmp_path)
    receipt = bind_snapshot(engine, **args)
    eid = args["engagement_id"]
    original = engine.artifacts.retain(
        eid, "inspection.txt", b"Bounded original", source={}, coverage={}, generated=False
    )
    advance(
        engine,
        args,
        lambda state: {
            **state,
            "artifacts": [original],
            "company_source_binding": {"company": "C", "branch": "B"},
        },
    )
    payload = {
        "artifact_id": original["id"],
        "sha256": original["sha256"],
        "version": None,
        "locator": "Line 1",
        "observation": "Self-reported observation",
    }
    actor = args["audited_actor_id"]

    def reduce(state, envelope, actual_actor):
        artifact_inspection.handle(
            state,
            envelope["payload"],
            {
                "actor": actual_actor,
                "recorded_at": "2027-08-01T00:00:00Z",
                "simulated_at": state["simulated_at"],
            },
            engine.artifacts,
            envelope["command_id"],
        )
        return state

    engine.store.command(actor, eid, command(payload, revision=1), reduce, permissions={"learn"})
    bindings = {eid: {"path": args["output"], "manifest_sha256": receipt["manifest_sha256"]}}
    for revision, count in [(1, 0), (2, 1)]:
        result = compare(engine, {"id": args["instructor_id"]}, eid, bindings, revision=revision)
        assert result["inspection"]["audited_actor_count"] == count
        assert result["grading"] == "NOT_PERFORMED"
        assert result["expectations"][0]["testing"] == "NOT_ASSESSED"


@pytest.mark.parametrize(
    "patch",
    [
        {"status": "EXCLUDED"},
        {"status": "NOT_APPLICABLE"},
        {"boundary_id": "Outside"},
        {"applicable": False},
    ],
)
def test_task_must_be_active_and_scoped(work, patch):
    engine, actor, learner, _, eid, _, payload = work

    def reduce(state, _command, _actor):
        state["tasks"][0].update(patch)
        return state

    engine.store.command(
        actor,
        eid,
        {"command_id": "fixture", "expected_revision": 0, "kind": "fixture", "payload": {}},
        reduce,
        permissions={"instruct"},
    )
    with pytest.raises(DomainError):
        engine.command(learner, eid, command(payload, revision=1))


def test_oversized_legacy_inspection_payload_not_retained_in_activity(work):
    engine, actor, _, _, eid, _, _ = work
    engine.store.command(
        actor,
        eid,
        {
            "command_id": "legacy",
            "expected_revision": 0,
            "kind": "artifact.inspection.record",
            "payload": {"observation": "x" * 40000},
        },
        lambda state, _command, _actor: state,
        permissions={"instruct"},
    )
    history = inspect_history(engine.store, actor, eid)
    assert history["activity"][-1]["command"] == {"kind": "artifact.inspection.record"}


def test_exact_present_integer_version_admitted(work):
    engine, actor, learner, _, eid, _, payload = work

    def reduce(state, _command, _actor):
        state["artifacts"][0]["version"] = 2
        return state

    engine.store.command(
        actor,
        eid,
        {"command_id": "fixture", "expected_revision": 0, "kind": "fixture", "payload": {}},
        reduce,
        permissions={"instruct"},
    )
    payload["version"] = 2
    saved = engine.command(learner, eid, command(payload, revision=1))
    assert saved["artifact_inspections"][0]["version"] == 2
