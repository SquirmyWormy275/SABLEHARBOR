"""Accepted bytes cannot be replaced by resealing their current manifest."""

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[2] / "tools/documents/approval_guard.py"
spec = importlib.util.spec_from_file_location("approval_guard", MODULE)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


@pytest.fixture(params=["foundry-field", "visitor-v08", "sacramento-r01", "j2-originals"])
def accepted(tmp_path, request):
    kind = request.param
    digest = hashlib.sha256(b"accepted bytes").hexdigest()
    artifact = "image.png"
    row = {"path": artifact, "sha256": digest}
    if kind == "foundry-field":
        record = {"artifacts": {artifact: digest}, "status": "OWNER_ACCEPTED_EXACT_PACKET"}
    elif kind == "visitor-v08":
        record = {"artifacts": {"png": row}, "status": "OWNER_ACCEPTED_VISUAL"}
    elif kind == "sacramento-r01":
        record = {
            "id": "R01",
            "status": "APPROVED_VISUAL_REFERENCE",
            "immutable": True,
            "files": [{"filename": artifact, "sha256": digest, "successor_artifacts": []}],
        }
    else:
        row["canonical_status"] = "LOCKED; controlling user-approved source asset."
        record = {"assets": [row]}
    (tmp_path / artifact).write_bytes(b"accepted bytes")
    manifest = tmp_path / "record.json"
    manifest.write_text(json.dumps(record))
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "Existing acceptance",
        ],
        check=True,
    )
    revision = subprocess.check_output(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"], text=True
    ).strip()
    records = ((kind, revision, "record.json"),)
    assert guard.validate(tmp_path, records)["artifact_count"] == 1
    return tmp_path, records, digest


def test_changed_bytes_fail(accepted):
    root, records, _ = accepted
    (root / "image.png").write_bytes(b"replacement")
    with pytest.raises(guard.ApprovalError, match="Approved artifact missing or changed"):
        guard.validate(root, records)


def test_resealed_hash_and_changed_bytes_fail(accepted):
    root, records, digest = accepted
    replacement = b"replacement"
    (root / "image.png").write_bytes(replacement)
    manifest = root / "record.json"
    manifest.write_text(
        manifest.read_text().replace(digest, hashlib.sha256(replacement).hexdigest())
    )
    with pytest.raises(guard.ApprovalError, match="Approval record changed"):
        guard.validate(root, records)


def test_missing_artifact_fails(accepted):
    root, records, _ = accepted
    (root / "image.png").unlink()
    with pytest.raises(guard.ApprovalError, match="Approved artifact missing or changed"):
        guard.validate(root, records)


def test_missing_history_fails(accepted):
    root, records, _ = accepted
    kind, _, path = records[0]
    with pytest.raises(guard.ApprovalError, match="Missing approval history"):
        guard.validate(root, ((kind, "0" * 40, path),))


def test_record_removal_fails(accepted):
    root, records, _ = accepted
    (root / "record.json").unlink()
    with pytest.raises(FileNotFoundError):
        guard.validate(root, records)


def test_r01_successor_links_do_not_reapprove_original():
    original = {
        "id": "R01",
        "status": "APPROVED_VISUAL_REFERENCE",
        "immutable": True,
        "files": [{"filename": "image.png", "sha256": "original", "successor_artifacts": []}],
    }
    current = json.loads(json.dumps(original))
    current["files"][0]["successor_artifacts"] = [{"path": "new-draft.svg"}]
    assert guard.projection("sacramento-r01", current) == guard.projection(
        "sacramento-r01", original
    )
