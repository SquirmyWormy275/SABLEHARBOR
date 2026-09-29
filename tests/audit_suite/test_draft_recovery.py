import json

import pytest

from enterprise.audit_suite.draft_recovery import backup, restore
from enterprise.audit_suite.draft_store import DraftStore
from enterprise.audit_suite.store import DomainError, Store


def test_companion_explicit_mapping_and_no_overwrite_or_formal_changes(tmp_path):
    tmp_path.chmod(0o700)
    store = Store(tmp_path / "source")
    old = store.provision("Original", ["learner"])["id"]
    new = store.provision("Replacement", ["learner"])["id"]
    state = store.create(old, {"title": "Draft", "scope": {}}, "create")
    store.grant(state["id"], new, "learn")
    drafts = DraftStore(store)
    drafts.write(
        old,
        state["id"],
        "note.create",
        "new",
        {
            "command_id": "write",
            "expected_version": 0,
            "fields": {"text": "Private draft"},
            "base_workpaper_version": None,
        },
    )
    snapshot = tmp_path / "companion"
    backup(drafts, snapshot)
    history = store.history(old, state["id"])
    with pytest.raises(DomainError):
        restore(snapshot, store, principal_map={old: new})
    # Preserve original DB; simulate companion recovery into the recovered engagement store.
    drafts.path.rename(tmp_path / "original-drafts.sqlite3")
    with pytest.raises(DomainError):
        restore(snapshot, store, principal_map={})
    receipt = restore(snapshot, store, principal_map={old: new})
    assert receipt["formal_records_modified"] is False
    restored = DraftStore(store)
    assert restored.get(new, state["id"], "note.create", "new")["fields"] == {
        "text": "Private draft"
    }
    assert restored.get(old, state["id"], "note.create", "new")["status"] == "EMPTY"
    assert store.history(old, state["id"]) == history
    assert "Private draft" not in json.dumps(history)


def test_tampered_companion_and_revoked_target_denied(tmp_path):
    tmp_path.chmod(0o700)
    store = Store(tmp_path / "source")
    actor = store.provision("Actor", ["learner"])["id"]
    state = store.create(actor, {"title": "Draft", "scope": {}}, "create")
    drafts = DraftStore(store)
    drafts.write(
        actor,
        state["id"],
        "note.create",
        "new",
        {
            "command_id": "write",
            "expected_version": 0,
            "fields": {"text": "private"},
            "base_workpaper_version": None,
        },
    )
    snapshot = tmp_path / "companion"
    backup(drafts, snapshot)
    drafts.path.rename(tmp_path / "original.sqlite3")
    store.revoke(actor)
    with pytest.raises(DomainError):
        restore(snapshot, store, principal_map={actor: actor})
    assert not drafts.path.exists()
    (snapshot / "drafts.json").write_bytes(b"tamper")
    with pytest.raises(DomainError):
        restore(snapshot, store, principal_map={actor: actor})
    assert not drafts.path.exists()
