"""Independent publication-boundary checks using actual native store fixtures."""

from pathlib import Path

import pytest
from test_company_source_register import fixture, put

from enterprise.audit_suite import company_source_register as register


def test_changed_predecessor_member_during_successor_capture_rejects(tmp_path, monkeypatch):
    repo, _, config, pin = fixture(tmp_path)
    prior = tmp_path / "prior"
    register.write_register(Path(pin["path"]), prior, repository=repo)
    config["previous"] = {
        "path": str(prior / "MANIFEST.json"),
        "sha256": register.sha((prior / "MANIFEST.json").read_bytes()),
    }
    put(Path(pin["path"]), config)
    original = register.build

    def capture(*args, **kwargs):
        result = original(*args, **kwargs)
        put(prior / "MIGRATION_REGISTER.json", {"changed": True})
        return result

    monkeypatch.setattr(register, "build", capture)
    with pytest.raises(ValueError):
        register.write_register(Path(pin["path"]), tmp_path / "successor", repository=repo)
    assert not (tmp_path / "successor").exists()


def test_current_finance_source_change_after_capture_rejects(tmp_path, monkeypatch):
    repo, _, _, pin = fixture(tmp_path)
    original = register.build

    def capture(*args, **kwargs):
        result = original(*args, **kwargs)
        put(repo / "docs/old.md", b"another current revision after capture")
        return result

    monkeypatch.setattr(register, "build", capture)
    with pytest.raises(ValueError):
        register.write_register(Path(pin["path"]), tmp_path / "report", repository=repo)
    assert not (tmp_path / "report").exists()


def test_output_parent_swap_cannot_publish_private_bytes_external(tmp_path, monkeypatch):
    repo, _, _, pin = fixture(tmp_path)
    parent = tmp_path / "reports"
    parent.mkdir(mode=0o700)
    external = tmp_path / "external"
    external.mkdir(mode=0o700)
    original = register.build

    def capture(*args, **kwargs):
        result = original(*args, **kwargs)
        parent.rename(tmp_path / "original-reports")
        parent.symlink_to(external, target_is_directory=True)
        return result

    monkeypatch.setattr(register, "build", capture)
    try:
        register.write_register(Path(pin["path"]), parent / "report", repository=repo)
    except (ValueError, OSError):
        pass
    assert list(external.iterdir()) == []


def test_re_pinned_registry_cannot_substitute_other_native_branch(tmp_path):
    import json

    repo, _, config, _ = fixture(tmp_path)
    path = Path(config["profiles"][0]["registry"]["path"])
    registry = json.loads(path.read_text())
    registry["components"]["documents"]["branch"] = "other-branch"
    pin = put(path, registry)
    for profile in config["profiles"]:
        profile["registry"] = pin
    with pytest.raises(ValueError, match="Inventory/registry identity differs"):
        register.build(config, repository=repo)


def test_missing_historical_git_object_preserves_unknown_and_finance_bytes(tmp_path):
    repo, store, config, _ = fixture(tmp_path)
    lock = Path(config["finance"]["source_lock"]["path"])
    config["finance"]["source_lock"] = put(
        lock, {"controlling_source": {"commit": "f" * 40, "files": ["docs/old.md"]}}
    )
    native_before = store.path.read_bytes()
    finance_before = (repo / "docs/old.md").read_bytes()
    result = register.build(config, repository=repo)
    item = result["finance_references"]["historical_source_lock"][0]
    assert item["historical_blob_sha256"] is None
    assert item["current_matches_historical"] is None
    assert item["disposition"] == "HISTORICAL_OBJECT_NOT_AVAILABLE_LOCALLY_UNRESOLVED"
    assert store.path.read_bytes() == native_before
    assert (repo / "docs/old.md").read_bytes() == finance_before
