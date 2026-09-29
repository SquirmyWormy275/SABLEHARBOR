"""Private release custody never reactivates recipient access or delivery."""

import hashlib
import json
import os

import pytest

from enterprise.audit_suite.companion_recovery import backup, restore
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_instructor_releases import confirm, preview
from tests.audit_suite.test_instructor_releases import release as release_fixture


@pytest.fixture
def source(tmp_path):
    return release_fixture.__wrapped__(tmp_path)


def test_release_archive_preserves_originals_and_remains_inert_without_principal_mapping(
    source, tmp_path
):
    core, engine, args = source
    item = confirm(core, args, preview(core, args))
    core.read(args["audited_actor_id"], args["engagement_id"], item["release_id"])
    core.revoke(
        args["instructor_id"],
        args["engagement_id"],
        {
            "release_id": item["release_id"],
            "command_id": "revoke",
            "reason": "Withdraw neutral hint.",
        },
    )
    before = core.path.read_bytes()
    audit = engine.store.get(args["instructor_id"], args["engagement_id"])
    root = tmp_path / "recovery"
    root.mkdir(mode=0o700)
    manifest = backup(root / "backup", instructor_releases=core)
    assert core.path.read_bytes() == before
    raw = (root / "backup/instructor-releases.json").read_bytes()
    assert manifest["members"]["instructor-releases.json"] == {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }
    receipt = restore(root / "backup", root / "restored")
    assert (root / "restored/instructor-releases-ARCHIVE-ONLY.json").read_bytes() == raw
    assert not list((root / "restored").rglob("*.sqlite3"))
    assert receipt["instructor_releases"] == "ARCHIVE_ONLY_NOT_OPERATIONALLY_REHYDRATED"
    assert not receipt["release_principals_or_bindings_rehydrated"]
    assert not receipt["credentials_or_grants_restored"] and not receipt["automatic_execution"]
    assert engine.store.get(args["instructor_id"], args["engagement_id"]) == audit
    assert core.path.read_bytes() == before
    with pytest.raises(DomainError):
        core.read(args["audited_actor_id"], args["engagement_id"], item["release_id"])
    for file in (root / "restored").iterdir():
        assert file.stat().st_mode & 0o777 == 0o600


def test_release_archive_byte_corruption_and_private_path_fail_closed(source, tmp_path):
    core, _, args = source
    preview(core, args)
    root = tmp_path / "recovery"
    root.mkdir(mode=0o700)
    backup(root / "backup", instructor_releases=core)
    file = root / "backup/instructor-releases.json"
    original = file.read_bytes()
    file.write_bytes(original + b" ")
    with pytest.raises(DomainError, match="integrity"):
        restore(root / "backup", root / "bad")
    assert not (root / "bad").exists()
    file.write_bytes(original)
    file.chmod(0o644)
    with pytest.raises(DomainError, match="Private"):
        restore(root / "backup", root / "public")
    assert not (root / "public").exists()
    file.chmod(0o600)
    file.rename(root / "original.json")
    os.symlink(root / "original.json", file)
    with pytest.raises(DomainError, match="aliases"):
        restore(root / "backup", root / "aliased")
    assert not (root / "aliased").exists()


def test_rehashed_structurally_invalid_release_archive_is_rejected(source, tmp_path):
    core, _, args = source
    preview(core, args)
    root = tmp_path / "recovery"
    root.mkdir(mode=0o700)
    backup(root / "backup", instructor_releases=core)
    raw = b'{"format":"not-a-release-snapshot"}'
    (root / "backup/instructor-releases.json").write_bytes(raw)
    path = root / "backup/MANIFEST.json"
    manifest = json.loads(path.read_bytes())
    manifest["members"]["instructor-releases.json"] = {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }
    path.write_text(json.dumps(manifest))
    with pytest.raises(DomainError):
        restore(root / "backup", root / "invalid")
    assert not (root / "invalid").exists()


def test_rehashed_outer_manifest_does_not_hide_inner_document_corruption(source, tmp_path):
    core, _, args = source
    confirm(core, args, preview(core, args))
    root = tmp_path / "recovery"
    root.mkdir(mode=0o700)
    backup(root / "backup", instructor_releases=core)
    file = root / "backup/instructor-releases.json"
    snapshot = json.loads(file.read_bytes())
    snapshot["tables"]["documents"][0]["content"] = "{}"
    raw = json.dumps(snapshot).encode()
    file.write_bytes(raw)
    manifest_path = root / "backup/MANIFEST.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["members"]["instructor-releases.json"] = {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(DomainError, match="Invalid private release archive"):
        restore(root / "backup", root / "rejected")
    assert not (root / "rejected").exists()
