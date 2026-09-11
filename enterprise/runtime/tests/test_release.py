import hashlib
import json
from zipfile import ZipFile
import pytest
from enterprise.runtime.release import verify_archive


def test_release_rejects_changed_missing_and_unlisted_bytes(tmp_path):
    manifest = {"files": {"source.json": hashlib.sha256(b"approved").hexdigest()}}
    for payload, extra, valid in [
        (b"approved", False, True),
        (b"changed", False, False),
        (None, False, False),
        (b"approved", True, False),
    ]:
        path = tmp_path / "release.zip"
        with ZipFile(path, "w") as archive:
            archive.writestr("MANIFEST.json", json.dumps(manifest))
            if payload is not None:
                archive.writestr("source.json", payload)
            if extra:
                archive.writestr("unlisted.json", b"unknown")
        if valid:
            assert verify_archive(path) == manifest
        else:
            with pytest.raises(ValueError):
                verify_archive(path)
