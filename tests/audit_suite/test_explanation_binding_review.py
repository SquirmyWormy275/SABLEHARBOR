import copy

import pytest

from enterprise.audit_suite.explanation_binding import _authored, bind_snapshot, verify_snapshot
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_explanation_binding import workspace as binding_workspace


@pytest.fixture
def workspace(tmp_path):
    return binding_workspace.__wrapped__(tmp_path)


def test_manifest_permissions_fail_closed(workspace):
    engine, args = workspace
    receipt = bind_snapshot(engine, **args)
    (args["output"] / "manifest.json").chmod(0o644)
    with pytest.raises(DomainError):
        verify_snapshot(args["output"], expected_manifest_sha256=receipt["manifest_sha256"])


def test_binding_change_during_source_read_cannot_publish_mixed_snapshot(workspace, monkeypatch):
    engine, args = workspace
    original = engine.company_store._read

    def changed(*a, **k):
        row = original(*a, **k)
        engine.company_bindings[args["engagement_id"]]["branch"] = "DIFFERENT"
        return row

    monkeypatch.setattr(engine.company_store, "_read", changed)
    with pytest.raises(DomainError):
        bind_snapshot(engine, **args)
    assert not args["output"].exists()


def test_authored_reference_lists_are_typed(tmp_path):
    authored = {
        "issues": [
            {
                "id": "I",
                "control_ids": "C",
                "source_ids": "R",
                "claim": "Claim",
                "uncertainty": "Unvalidated",
            }
        ],
        "expectations": [],
        "uncertainty": ["Unknown"],
        "source_pins": {},
    }
    with pytest.raises(DomainError):
        _authored(authored, {"R"}, {"C"}, tmp_path)


def test_snapshot_preserves_captured_scope_and_history_after_changes(workspace):
    engine, args = workspace
    receipt = bind_snapshot(engine, **args)
    original = verify_snapshot(args["output"], expected_manifest_sha256=receipt["manifest_sha256"])
    before = copy.deepcopy(original)
    state = engine.store.get(args["instructor_id"], args["engagement_id"])

    def revise(s, c, who):
        s["scope"]["period_end"] = "2028-12-31"
        return s

    engine.store.command(
        args["instructor_id"],
        args["engagement_id"],
        {
            "kind": "test",
            "command_id": "scope-revision",
            "expected_revision": state["revision"],
            "payload": {},
        },
        revise,
        permissions={"instruct"},
    )
    assert (
        verify_snapshot(args["output"], expected_manifest_sha256=receipt["manifest_sha256"])
        == before
    )
    assert original["engagement"]["scope"]["period_end"] == "2027-12-31"


def test_revoked_source_grant_does_not_erase_retained_copy(workspace):
    engine, args = workspace
    record = engine.company_store.read_version(
        "OPERATOR",
        args["engagement_id"],
        "C",
        "B",
        "SYS",
        "R1",
        version=1,
        as_of=args["source_as_of"],
    )
    artifact = engine.artifacts.retain(
        args["engagement_id"],
        "original.json",
        record["content"],
        source={"kind": "COLLECTED_COMPANY_SOURCE", "receipt": {"source": record}},
        coverage={},
    )
    # Receipt metadata contains no source byte value; native bytes remain in artifact store.
    artifact["source"]["receipt"]["source"].pop("content")
    state = engine.store.get(args["instructor_id"], args["engagement_id"])

    def retained(s, c, who):
        s["artifacts"].append(artifact)
        return s

    engine.store.command(
        args["instructor_id"],
        args["engagement_id"],
        {
            "kind": "test",
            "command_id": "retained",
            "expected_revision": state["revision"],
            "payload": {},
        },
        retained,
        permissions={"instruct"},
    )
    engine.company_store.grant(
        args["audited_actor_id"], args["engagement_id"], "C", "B", "SYS", active=False
    )
    receipt = bind_snapshot(engine, **args)
    snapshot = verify_snapshot(args["output"], expected_manifest_sha256=receipt["manifest_sha256"])
    source = snapshot["sources"][0]
    assert source["actor_visibility_at_binding"] == "ACCESS_NOT_GRANTED"
    assert source["retained_audit_artifact_ids"] == [artifact["id"]]


def test_instructor_role_downgrade_during_binding_fails(workspace, monkeypatch):
    engine, args = workspace
    original = engine.company_store._read

    def downgrade(*a, **k):
        row = original(*a, **k)
        engine.store.grant(args["engagement_id"], args["instructor_id"], "review")
        return row

    monkeypatch.setattr(engine.company_store, "_read", downgrade)
    with pytest.raises(DomainError):
        bind_snapshot(engine, **args)
    assert not args["output"].exists()
