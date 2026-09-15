"""Independent recipient isolation and receipt-integrity review, no live releases."""

import json
import sqlite3

import pytest

from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_instructor_releases import confirm, preview
from tests.audit_suite.test_instructor_releases import release as release_fixture


@pytest.fixture
def source(tmp_path):
    return release_fixture.__wrapped__(tmp_path)


def test_other_scoped_learner_cannot_read_or_ack_and_original_audit_stays_unmodified(source):
    core, engine, args = source
    result = confirm(core, args, preview(core, args))
    rid = result["release_id"]
    other = engine.store.provision("Other participant", ["learner"])["id"]
    engine.store.grant(args["engagement_id"], other, "learn")
    before = core.path.read_bytes()
    audit = engine.store.get(args["instructor_id"], args["engagement_id"])
    assert core.list(other, args["engagement_id"]) == []
    with pytest.raises(DomainError):
        core.read(other, args["engagement_id"], rid)
    with pytest.raises(DomainError):
        core.acknowledge(
            other, args["engagement_id"], {"release_id": rid, "command_id": "wrong-person"}
        )
    assert core.path.read_bytes() == before
    assert engine.store.get(args["instructor_id"], args["engagement_id"]) == audit
    assert "release_id" not in json.dumps(audit)


def test_role_change_during_delivery_rolls_back_delivery_event(source, monkeypatch):
    core, engine, args = source
    result = confirm(core, args, preview(core, args))
    rid = result["release_id"]
    original = core._check
    calls = 0
    before = core.path.read_bytes()

    def interrupted(value, exact=False):
        nonlocal calls
        calls += 1
        if calls == 2:
            engine.store.grant(args["engagement_id"], args["audited_actor_id"], "review")
        return original(value, exact=exact)

    monkeypatch.setattr(core, "_check", interrupted)
    with pytest.raises(DomainError):
        core.read(args["audited_actor_id"], args["engagement_id"], rid)
    assert core.path.read_bytes() == before
    with core._db() as db:
        assert core._actions(db, rid) == ["RELEASED"]


def test_acknowledgement_replay_checks_receipt_identity(source):
    core, engine, args = source
    result = confirm(core, args, preview(core, args))
    rid = result["release_id"]
    core.read(args["audited_actor_id"], args["engagement_id"], rid)
    payload = {"release_id": rid, "command_id": "ack"}
    core.acknowledge(args["audited_actor_id"], args["engagement_id"], payload)
    # Command receipt rows are immutable through the application-owned SQLite schema.
    with sqlite3.connect(core.path) as db:
        with pytest.raises(sqlite3.IntegrityError, match="Immutable release receipt"):
            db.execute(
                "UPDATE commands SET result=? WHERE command=?",
                (json.dumps({"release_id": "OTHER-RELEASE", "status": "ACKNOWLEDGED"}), "ack"),
            )
    replay = core.acknowledge(args["audited_actor_id"], args["engagement_id"], payload)
    assert replay["release_id"] == rid and replay["understanding"] == "NOT_INFERRED"
