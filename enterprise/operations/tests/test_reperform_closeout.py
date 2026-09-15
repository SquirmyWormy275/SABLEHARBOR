import copy
import hashlib

import pytest

from enterprise.operations.reperform_closeout import verify_hashes, verify_identity


def test_composite_identity_requires_one_clean_revision():
    manifest = {"source_commit": "abc"}
    edition = {
        "repository_source_commit": "abc",
        "publishable_source_snapshot": True,
        "effective_through": "2026-08-31",
    }
    finance = {"source_revision": "abc", "dirty_development_build": False}
    september = {"repository_source_commit": "abc", "publishable_source_snapshot": True}
    verify_identity(manifest, edition, finance, september, "abc")
    for key, value in [("source_revision", "different"), ("dirty_development_build", True)]:
        changed = copy.deepcopy(finance)
        changed[key] = value
        with pytest.raises(ValueError):
            verify_identity(manifest, edition, changed, september, "abc")
    for item in [edition, september]:
        item["publishable_source_snapshot"] = False
        with pytest.raises(ValueError, match="Dirty preview"):
            verify_identity(manifest, edition, finance, september, "abc")
        item["publishable_source_snapshot"] = True


def test_missing_changed_and_path_escaping_artifacts_fail(tmp_path):
    path = tmp_path / "records.json"
    path.write_text("original")
    expected = {"records.json": hashlib.sha256(path.read_bytes()).hexdigest()}
    verify_hashes(tmp_path, expected)
    path.write_text("stale")
    with pytest.raises(ValueError, match="stale"):
        verify_hashes(tmp_path, expected)
    with pytest.raises(ValueError, match="unsafe"):
        verify_hashes(tmp_path, {"../outside.json": "x"})
