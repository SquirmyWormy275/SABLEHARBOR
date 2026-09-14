import os

import pytest

from enterprise.audit_suite.artifacts import Artifacts
from enterprise.audit_suite.recovery import backup, restore
from enterprise.audit_suite.store import DomainError, Store


def test_restore_preserves_native_files_failures_and_invalidates_old_access(tmp_path):
    os.chmod(tmp_path, 0o700)
    store = Store(tmp_path / "source")
    principal = store.provision("Original owner", ["instructor"])
    state = store.create(principal["id"], {"title": "Recovery exercise", "artifacts": []}, "create")
    artifacts = Artifacts(store.root)
    original = artifacts.retain(
        state["id"], "original.txt", b"Retained original failure", source={}, coverage={}
    )
    state = store.command(
        principal["id"],
        state["id"],
        {
            "command_id": "record",
            "expected_revision": 0,
            "kind": "work",
            "payload": {},
        },
        lambda s, c, who: {**s, "artifacts": [original], "finding": "FAIL"},
        permissions={"instruct"},
    )
    original_history = store.history(principal["id"], state["id"])
    session = store.login(principal["credential"])
    manifest = backup(store, tmp_path / "backup")
    store.revoke(principal["id"])
    receipt = restore(tmp_path / "backup", tmp_path / "restored")
    recovered = Store(tmp_path / "restored")
    with pytest.raises(DomainError):
        recovered.login(principal["credential"])
    with pytest.raises(DomainError):
        recovered.session(session["token"])
    new = recovered.provision("Recovery reviewer", ["reviewer"])
    recovered.grant(state["id"], new["id"], "review")
    assert recovered.history(new["id"], state["id"]) == original_history
    assert recovered.get(new["id"], state["id"])["finding"] == "FAIL"
    assert Artifacts(recovered.root).read(original) == b"Retained original failure"
    assert receipt["engagements"] == manifest["engagements"]
    with pytest.raises(FileExistsError):
        restore(tmp_path / "backup", tmp_path / "restored")


def test_corrupt_backup_does_not_restore(tmp_path):
    os.chmod(tmp_path, 0o700)
    store = Store(tmp_path / "source")
    backup(store, tmp_path / "backup")
    path = tmp_path / "backup" / "engagements.sqlite3"
    with path.open("ab") as stream:
        stream.write(b"corruption")
    with pytest.raises(DomainError, match="integrity failure"):
        restore(tmp_path / "backup", tmp_path / "restored")
    assert not (tmp_path / "restored").exists()
