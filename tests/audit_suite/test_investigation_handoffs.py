"""Explicit peer coordination in disposable actual Engine workspaces."""

import json
from copy import deepcopy

import pytest

from enterprise.audit_suite.investigation_handoffs import InvestigationHandoffs, validate_snapshot
from enterprise.audit_suite.store import DomainError, canonical, digest
from tests.audit_suite.test_workspace_context import change
from tests.audit_suite.test_workspace_context import workspace as workspace


@pytest.fixture
def handoffs(workspace, tmp_path):
    _, engine, sender, state = workspace
    state = change(engine, sender, state, lambda s: s["artifacts"][0].update(status="AVAILABLE"))
    recipient = engine.store.provision("Selected colleague", ["learner"])["id"]
    outsider = engine.store.provision("Other colleague", ["learner"])["id"]
    engine.store.grant(state["id"], recipient, "learn")
    engine.store.grant(state["id"], outsider, "learn")
    path = tmp_path / "handoffs"
    path.mkdir(mode=0o700)
    return InvestigationHandoffs(path, engine), engine, sender, recipient, outsider, state


def payload(fixture):
    h, _, sender, recipient, _, state = fixture
    return {
        "recipient_id": recipient,
        "title": "Inspect an explicit original",
        "question": "What supports the retained observation?",
        "next_step": "Read this exact workpaper version",
        "links": [
            h.make_reference(
                sender,
                state["id"],
                recipient_id=recipient,
                kind="workpaper",
                record_id="W1",
                version=1,
            )
        ],
    }


def offer(fixture, data=None, command="offer"):
    h, _, sender, _, _, state = fixture
    return h.offer(
        sender,
        state["id"],
        data or payload(fixture),
        expected_engagement_revision=state["revision"],
        command_id=command,
    )


def transition(fixture, saved, actor, action, response="", command=None, revision=None):
    h, _, _, _, _, state = fixture
    return h.transition(
        actor,
        state["id"],
        saved["id"],
        action=action,
        response=response,
        expected_version=saved["version"],
        expected_engagement_revision=state["revision"] if revision is None else revision,
        command_id=command or action,
    )


def test_authored_offer_accept_complete_history_replay_no_formal_mutation(handoffs):
    h, engine, sender, recipient, _, state = handoffs
    before = engine.store.get(sender, state["id"])
    data = payload(handoffs)
    first = offer(handoffs, data)
    assert first["allowed_actions"] == ["WITHDRAW"]
    assert h.read(recipient, state["id"], first["id"])["allowed_actions"] == ["ACCEPT", "DECLINE"]
    accepted = transition(handoffs, first, recipient, "ACCEPT", "I will inspect the pinned version")
    assert accepted["status"] == "ACCEPTED" and accepted["version"] == 2
    completed = transition(
        handoffs,
        accepted,
        recipient,
        "COMPLETE",
        "My coordination response; assessment remains open",
    )
    assert completed["status"] == "COMPLETED" and completed["coordination_only"]
    assert completed["content"]["links"][0]["version"] == 1
    assert not completed["formal_work_mutated"]
    replay = offer(handoffs, data)
    assert replay["status"] == "COMPLETED" and replay["version"] == 3
    assert engine.store.get(sender, state["id"]) == before
    snapshot = h.snapshot()
    assert len(snapshot["documents"]) == len(snapshot["commands"]) == 3
    assert validate_snapshot(snapshot) == snapshot
    restarted = InvestigationHandoffs(h.root, engine)
    assert restarted.read(recipient, state["id"], first["id"]) == completed
    assert h.path.stat().st_mode & 0o777 == 0o600


def test_directory_has_only_active_auditor_id_name_permission_and_participant_reads(handoffs):
    h, engine, sender, recipient, outsider, state = handoffs
    members = h.directory(sender, state["id"])["members"]
    assert {row["id"] for row in members} == {recipient, outsider}
    assert all(set(row) == {"id", "display_name", "permission"} for row in members)
    first = offer(handoffs)
    assert h.listing(outsider, state["id"]) == []
    with pytest.raises(DomainError):
        h.read(outsider, state["id"], first["id"])
    with pytest.raises(DomainError):
        offer(handoffs, {**payload(handoffs), "recipient_id": "AS-P005"}, "persona")
    engine.store.revoke(outsider)
    assert {row["id"] for row in h.directory(sender, state["id"])["members"]} == {recipient}


def test_reference_requires_both_authorized_projections(handoffs, monkeypatch):
    h, engine, sender, recipient, _, state = handoffs
    data = payload(handoffs)
    real = engine.get

    def filtered(actor, eid):
        value = real(actor, eid)
        if actor == recipient:
            value["workpapers"] = []
        return value

    monkeypatch.setattr(engine, "get", filtered)
    with pytest.raises(DomainError):
        h.make_reference(
            sender, state["id"], recipient_id=recipient, kind="workpaper", record_id="W1", version=1
        )
    with pytest.raises(DomainError):
        offer(handoffs, data)
    assert h.snapshot()["documents"] == []


def test_stale_basis_redacts_replays_but_recipient_can_decline(handoffs):
    h, engine, sender, recipient, _, state = handoffs
    data = payload(handoffs)
    first = offer(handoffs, data)
    updated = change(
        engine,
        sender,
        state,
        lambda s: s.update(company_source_binding={"company": "C", "branch": "new"}),
    )
    hidden = h.read(recipient, state["id"], first["id"])
    assert hidden["context_status"] == "CONTEXT_CHANGED" and "content" not in hidden
    assert hidden["allowed_actions"] == ["DECLINE"]
    with pytest.raises(DomainError):
        transition(handoffs, first, recipient, "ACCEPT", revision=updated["revision"])
    declined = transition(
        handoffs,
        first,
        recipient,
        "DECLINE",
        "Cannot use this old context",
        revision=updated["revision"],
    )
    assert declined["status"] == "DECLINED" and "content" not in declined
    replay = h.offer(
        sender,
        state["id"],
        data,
        expected_engagement_revision=state["revision"],
        command_id="offer",
    )
    assert replay["status"] == "DECLINED" and "content" not in replay


@pytest.mark.parametrize("unavailable", ["recipient_expired", "sender_revoked"])
def test_counterpart_unavailable_redacts_and_allows_only_current_owner_disposal(
    handoffs, unavailable
):
    h, engine, sender, recipient, _, state = handoffs
    first = offer(handoffs)
    if unavailable == "recipient_expired":
        with engine.store.connect() as db:
            db.execute("UPDATE principals SET expires=0 WHERE id=?", (recipient,))
        actor, action = sender, "WITHDRAW"
        with pytest.raises(DomainError):
            h.read(recipient, state["id"], first["id"])
    else:
        engine.store.revoke(sender)
        actor, action = recipient, "DECLINE"
    view = h.read(actor, state["id"], first["id"])
    assert view["context_status"] == "PARTICIPANT_UNAVAILABLE" and "content" not in view
    assert view["allowed_actions"] == [action]
    result = transition(handoffs, first, actor, action)
    assert result["status"] in {"WITHDRAWN", "DECLINED"} and "content" not in result


def test_cas_actor_status_and_changed_idempotency_reject(handoffs):
    h, _, sender, recipient, _, state = handoffs
    first = offer(handoffs)
    with pytest.raises(DomainError):
        transition(handoffs, first, sender, "ACCEPT")
    accepted = transition(handoffs, first, recipient, "ACCEPT")
    with pytest.raises(DomainError):
        transition(handoffs, first, recipient, "COMPLETE", "Stale version")
    with pytest.raises(DomainError):
        transition(handoffs, accepted, sender, "WITHDRAW")
    with pytest.raises(DomainError):
        transition(handoffs, accepted, recipient, "COMPLETE", "")
    with pytest.raises(DomainError):
        offer(handoffs, {**payload(handoffs), "question": "changed"})
    assert h.read(recipient, state["id"], first["id"])["version"] == 2


def test_missing_or_changed_exact_target_prevents_acceptance(handoffs):
    h, engine, sender, recipient, _, state = handoffs
    first = offer(handoffs)
    current = change(
        engine,
        sender,
        state,
        lambda s: s["workpapers"][0]["versions"][0].update(text="Different retained version"),
    )
    view = h.read(recipient, state["id"], first["id"])
    assert view["context_status"] == "TARGET_UNAVAILABLE" and not view["shared_content_visible"]
    with pytest.raises(DomainError):
        transition(handoffs, first, recipient, "ACCEPT", revision=current["revision"])


def test_counterpart_revoked_during_publication_rolls_back(handoffs, monkeypatch):
    h, engine, _, recipient, _, _ = handoffs
    data = payload(handoffs)
    real = h._projection

    def revoke(*args):
        engine.store.revoke(recipient)
        return real(*args)

    monkeypatch.setattr(h, "_projection", revoke)
    with pytest.raises(DomainError):
        offer(handoffs, data)
    assert h.snapshot()["documents"] == h.snapshot()["commands"] == []


def test_inert_snapshot_rejects_rehashed_invalid_transition_and_missing_receipt(handoffs):
    h, _, _, recipient, _, _ = handoffs
    first = offer(handoffs)
    transition(handoffs, first, recipient, "ACCEPT")
    original = h.snapshot()
    corrupt = deepcopy(original)
    value = json.loads(corrupt["documents"][1]["content"])
    value["author_id"] = value["sender_id"]
    corrupt["documents"][1].update(content=canonical(value), sha256=digest(value))
    with pytest.raises(DomainError):
        validate_snapshot(corrupt)
    corrupt = deepcopy(original)
    corrupt["commands"].pop()
    with pytest.raises(DomainError):
        validate_snapshot(corrupt)
    assert h.snapshot() == original


def test_private_store_alias_or_public_mode_rejected(handoffs, tmp_path):
    h, engine, sender, _, _, state = handoffs
    alias = tmp_path / "alias"
    alias.symlink_to(h.root, target_is_directory=True)
    with pytest.raises(DomainError):
        InvestigationHandoffs(alias, engine)
    h.path.chmod(0o644)
    with pytest.raises(DomainError):
        h.listing(sender, state["id"])


def test_active_quota_covers_recipient_and_disposal_frees_active_slot(handoffs):
    h, engine, sender, recipient, outsider, state = handoffs
    h.max_active = 1
    first = offer(handoffs)
    data = payload(handoffs)
    with pytest.raises(DomainError, match="active handoff quota"):
        h.offer(
            outsider,
            state["id"],
            data,
            expected_engagement_revision=state["revision"],
            command_id="other-offer",
        )
    transition(handoffs, first, recipient, "DECLINE")
    second = offer(handoffs, data, command="new-reviewed-offer")
    assert second["status"] == "OFFERED"
    assert len(h.snapshot()["documents"]) == 3


def test_exact_reference_types_and_unknown_payload_never_import_private_context(handoffs):
    h, _, _, _, _, _ = handoffs
    data = payload(handoffs)
    for bad in (True, 1.0):
        changed = deepcopy(data)
        changed["links"][0]["version"] = bad
        with pytest.raises(DomainError):
            offer(handoffs, changed, command=str(bad))
    with pytest.raises(DomainError):
        offer(handoffs, {**data, "private_notes": "Do not implicitly share"})
    assert h.snapshot()["documents"] == []


def test_revoked_actor_cannot_replay_former_success(handoffs):
    h, engine, sender, _, _, state = handoffs
    data = payload(handoffs)
    offer(handoffs, data)
    engine.store.revoke(sender)
    with pytest.raises(DomainError):
        h.offer(
            sender,
            state["id"],
            data,
            expected_engagement_revision=state["revision"],
            command_id="offer",
        )
