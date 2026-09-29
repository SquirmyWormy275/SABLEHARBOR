import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "source_bundle",
    Path(__file__).resolve().parents[2] / "tools/audit_suite/private_source_bundle.py",
)
bundle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bundle)


def test_deterministic_private_bundle_verify_restore_and_no_overwrite(tmp_path, monkeypatch):
    tmp_path.chmod(0o700)
    monkeypatch.setattr(bundle, "inventory", lambda root: {"private/source.json": b'{"fact":true}'})
    first, second = tmp_path / "first.zip", tmp_path / "second.zip"
    bundle.build(tmp_path, first)
    bundle.build(tmp_path, second)
    assert first.read_bytes() == second.read_bytes()
    assert first.stat().st_mode & 0o777 == 0o600
    restored = tmp_path / "restored"
    bundle.restore(first, restored)
    assert (restored / "private/source.json").read_bytes() == b'{"fact":true}'
    assert restored.stat().st_mode & 0o777 == 0o700
    assert (restored / "private/source.json").stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        bundle.restore(first, restored)
    with pytest.raises(FileExistsError):
        bundle.build(tmp_path, first)


@pytest.mark.parametrize("name,mode", [("../escape", 0o100600), ("source", 0o120600)])
def test_bundle_rejects_traversal_and_symlink_member(tmp_path, name, mode):
    path = tmp_path / "bad.zip"
    with zipfile.ZipFile(path, "w") as archive:
        info = zipfile.ZipInfo(name)
        info.external_attr = mode << 16
        archive.writestr(info, b"data")
    with pytest.raises(ValueError):
        bundle.verify(path)


def test_source_alias_and_corrupt_content_rejected(tmp_path, monkeypatch):
    (tmp_path / "real").write_bytes(b"source")
    (tmp_path / "alias").symlink_to(tmp_path / "real")
    with pytest.raises(ValueError, match="symlink"):
        bundle.read_source(tmp_path, "alias")
    monkeypatch.setattr(bundle, "inventory", lambda root: {"source": b"original"})
    source = tmp_path / "source.zip"
    bundle.build(tmp_path, source)
    corrupt = tmp_path / "corrupt.zip"
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(corrupt, "w") as new:
        for info in old.infolist():
            data = old.read(info.filename)
            if info.filename == "MANIFEST.json":
                manifest = json.loads(data)
                manifest["members"]["source"]["sha256"] = "0" * 64
                data = json.dumps(manifest).encode()
            new.writestr(info, data)
    with pytest.raises(ValueError, match="digest"):
        bundle.verify(corrupt)
