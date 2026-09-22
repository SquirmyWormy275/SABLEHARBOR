"""Bounded public-package identity guards; no portal runtime or service required."""

import json
import zipfile

import pytest

from tools.company_closeout.public_copy_disposal import MEMBERS, digest, file_digest, read_release


def package(tmp_path, *, size=1, duplicate=False, wrong_member=False):
    destination = tmp_path / "public.zip"
    payload = b"x" * size
    members = [{"path": p, "bytes": size, "sha256": digest(payload)} for p in MEMBERS.values()]
    if duplicate:
        members.append(members[0])
    if wrong_member:
        members[0]["sha256"] = "0" * 64
    contract = b"{}"
    manifest = {
        "status": "ACCEPTED_SCOPED_EDITION",
        "contract_sha256": digest(contract),
        "members": members,
    }
    with zipfile.ZipFile(destination, "w") as archive:
        archive.writestr("CONTRACT.json", contract)
        archive.writestr("MANIFEST.json", json.dumps(manifest))
        for path in MEMBERS.values():
            archive.writestr("content/" + path, payload)
    return destination


def test_exact_selected_originals(tmp_path):
    path = package(tmp_path)
    _, _, selected = read_release(path, file_digest(path))
    assert set(selected) == set(MEMBERS)
    assert all(value == b"x" for value in selected.values())


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"size": 65537}, "byte bound"),
        ({"size": 0}, "byte bound"),
        ({"duplicate": True}, "Duplicate"),
        ({"wrong_member": True}, "member mismatch"),
    ],
)
def test_invalid_selected_originals(tmp_path, changes, reason):
    path = package(tmp_path, **changes)
    with pytest.raises(ValueError, match=reason):
        read_release(path, file_digest(path))


def test_external_package_digest_rejects_changed_release(tmp_path):
    path = package(tmp_path)
    with pytest.raises(ValueError, match="digest mismatch"):
        read_release(path, "0" * 64)
