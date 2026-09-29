"""Neutral immutable source-pair backup and restore regression cases."""

import hashlib
import json

import pytest

from enterprise.audit_suite.recovery import backup, restore
from enterprise.audit_suite.store import DomainError, Store


@pytest.fixture
def source_store(tmp_path):
    tmp_path.chmod(0o700)
    store = Store(tmp_path / "state")
    for epoch in ("", "scope-00001/"):
        directory = store.root / "worlds" / "ENG-abcdef" / epoch / "parent-support"
        directory.mkdir(parents=True, mode=0o700)
        data = json.dumps({"source_id": "neutral", "epoch": epoch}).encode()
        for name, content in (
            ("source.json", data),
            ("source.sha256", (hashlib.sha256(data).hexdigest() + "\n").encode()),
        ):
            path = directory / name
            path.write_bytes(content)
            path.chmod(0o600)
    return store


def test_all_scope_epoch_source_pins_restored_exactly(source_store, tmp_path):
    manifest = backup(source_store, tmp_path / "backup")
    restore(tmp_path / "backup", tmp_path / "restored")
    pins = [p for p in manifest["files"] if p.endswith("source.sha256")]
    assert len(pins) == 2
    for relative in pins:
        path = tmp_path / "restored" / relative
        assert path.read_bytes() == (source_store.root / relative).read_bytes()
        assert not path.stat().st_mode & 0o077


@pytest.mark.parametrize("problem", ["missing_pin", "wrong_pin", "orphan_pin", "symlink_pin"])
def test_backup_rejects_incomplete_or_changed_source_pair(source_store, tmp_path, problem):
    directory = source_store.root / "worlds/ENG-abcdef/parent-support"
    pin = directory / "source.sha256"
    if problem == "missing_pin":
        pin.unlink()
    elif problem == "wrong_pin":
        pin.write_text("0" * 64 + "\n")
    elif problem == "orphan_pin":
        (directory / "source.json").unlink()
    else:
        pin.unlink()
        pin.symlink_to(directory / "source.json")
    with pytest.raises(DomainError):
        backup(source_store, tmp_path / "backup")
    assert not (tmp_path / "backup/backup-manifest.json").exists()


@pytest.mark.parametrize("problem", ["missing_pin", "wrong_pin", "orphan_pin", "unrelated_pin"])
def test_restore_checks_source_pair_beyond_member_hashes(source_store, tmp_path, problem):
    backup(source_store, tmp_path / "backup")
    directory = tmp_path / "backup"
    path = directory / "backup-manifest.json"
    manifest = json.loads(path.read_text())
    prefix = "worlds/ENG-abcdef/parent-support/"
    if problem in {"missing_pin", "orphan_pin"}:
        del manifest["files"][
            prefix + ("source.sha256" if problem == "missing_pin" else "source.json")
        ]
    else:
        relative = (
            prefix + "source.sha256"
            if problem == "wrong_pin"
            else "worlds/ENG-abcdef/unrelated.sha256"
        )
        data = b"0" * 64 + b"\n"
        (directory / relative).write_bytes(data)
        manifest["files"][relative] = {
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
        }
    path.write_text(json.dumps(manifest))
    with pytest.raises(DomainError):
        restore(directory, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()
