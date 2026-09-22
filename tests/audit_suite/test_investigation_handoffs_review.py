"""Independent privacy/replay and inert recovery boundary checks in disposable stores."""

import json

import pytest

from enterprise.audit_suite.companion_recovery import backup, restore
from enterprise.audit_suite.investigation_handoffs import InvestigationHandoffs
from enterprise.audit_suite.store import DomainError, canonical
from tests.audit_suite.test_investigation_handoffs import handoffs as handoffs
from tests.audit_suite.test_investigation_handoffs import offer, payload, transition
from tests.audit_suite.test_workspace_context import change
from tests.audit_suite.test_workspace_context import workspace as workspace


@pytest.mark.parametrize("operation", ["offer", "complete"])
def test_completed_command_replay_after_counterpart_revocation_returns_no_old_content(
    handoffs, operation
):
    h, engine, sender, recipient, _, state = handoffs
    data = payload(handoffs)
    first = offer(handoffs, data)
    accepted = transition(handoffs, first, recipient, "ACCEPT")
    transition(handoffs, accepted, recipient, "COMPLETE", "Private completed response")
    snapshot = h.snapshot()
    if operation == "offer":
        engine.store.revoke(recipient)
        result = offer(handoffs, data)
        actor = sender
    else:
        engine.store.revoke(sender)
        result = transition(handoffs, accepted, recipient, "COMPLETE", "Private completed response")
        actor = recipient
    assert result["version"] == 3 and result["status"] == "COMPLETED"
    assert result["context_status"] == "PARTICIPANT_UNAVAILABLE"
    assert "content" not in result and result["allowed_actions"] == []
    assert "Private completed response" not in canonical(h.listing(actor, state["id"]))
    assert data["question"] not in canonical(h.read(actor, state["id"], first["id"]))
    assert h.snapshot() == snapshot


def test_replayed_success_cannot_restore_a_removed_exact_target(handoffs):
    h, engine, sender, recipient, _, state = handoffs
    data = payload(handoffs)
    first = offer(handoffs, data)
    current = change(engine, sender, state, lambda s: s.update(workpapers=[]))
    before = h.snapshot()
    replay = offer(handoffs, data)
    assert replay["context_status"] == "TARGET_UNAVAILABLE" and "content" not in replay
    assert replay["allowed_actions"] == ["WITHDRAW"]
    with pytest.raises(DomainError):
        transition(handoffs, first, recipient, "ACCEPT", revision=current["revision"])
    assert h.snapshot() == before


def test_participant_replaced_after_transition_projection_rolls_back(handoffs, monkeypatch):
    h, engine, sender, recipient, _, state = handoffs
    first = offer(handoffs)
    before = h.snapshot()
    original = h._projection
    calls = 0

    def changed(*args):
        nonlocal calls
        calls += 1
        if calls == 2:
            engine.store.revoke(sender)
        return original(*args)

    monkeypatch.setattr(h, "_projection", changed)
    with pytest.raises(DomainError):
        transition(handoffs, first, recipient, "ACCEPT")
    assert h.snapshot() == before
    assert engine.store.get(recipient, state["id"])["revision"] == state["revision"]


def test_archived_private_content_is_inert_even_when_new_store_is_opened(handoffs, tmp_path):
    h, engine, sender, recipient, _, state = handoffs
    offer(handoffs)
    before = engine.store.get(sender, state["id"])
    bundle = tmp_path / "backup"
    backup(bundle, investigation_handoffs=h)
    engine.store.revoke(recipient)
    recovered = tmp_path / "recovered"
    receipt = restore(bundle, recovered)
    assert receipt["credentials_or_grants_restored"] is False
    assert receipt["investigation_handoffs"] == "ARCHIVE_ONLY_NOT_OPERATIONALLY_REHYDRATED"
    archive = recovered / "investigation-handoffs-ARCHIVE-ONLY.json"
    assert archive.read_bytes() == (bundle / "investigation-handoffs.json").read_bytes()
    assert json.loads(archive.read_text())["documents"]
    assert archive.stat().st_mode & 0o777 == 0o600
    # Even explicitly constructing an application store there does not import the archive.
    clean = InvestigationHandoffs(recovered, engine)
    assert clean.listing(sender, state["id"]) == []
    with pytest.raises(DomainError):
        clean.directory(recipient, state["id"])
    assert engine.store.get(sender, state["id"]) == before
