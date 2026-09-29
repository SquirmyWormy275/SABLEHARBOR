import copy
import json
import subprocess
from pathlib import Path

import pytest

from enterprise.audit_suite import company_source_register as register
from enterprise.audit_suite.company_store import CompanyStore


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode())
    path.chmod(0o600)
    return {"path": str(path), "sha256": register.sha(path.read_bytes())}


def fixture(tmp_path):
    tmp_path.chmod(0o700)
    repo = tmp_path / "repo"
    repo.mkdir(mode=0o700)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    old = repo / "docs/old.md"
    put(old, b"historical source")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "source",
        ],
        cwd=repo,
        check=True,
    )
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    put(old, b"later source preserved separately")
    packet = repo / "docs/packet.bin"
    put(packet, b"exact accepted packet")
    acceptance = put(
        repo / "docs/acceptance.json",
        {
            "status": "OWNER_ACCEPTED_EXACT_PACKET",
            "artifacts": {"docs/packet.bin": register.sha(packet.read_bytes())},
        },
    )
    lock = put(
        repo / "docs/lock.json",
        {"controlling_source": {"commit": commit, "files": ["docs/old.md"]}},
    )
    source = tmp_path / "source" / "company"
    source.parent.mkdir(mode=0o700)
    source.mkdir(mode=0o700)
    store = CompanyStore(source)
    store.register_system("NATIVE", "archive", "docs", "OWNER")
    content = b"original documentary bytes"
    content_sha = register.sha(content)
    provenance = {
        "source_reference": {"engagement": "OLD", "artifact": "ART"},
        "control_id": "CTRL",
        "custody_status": "PROVISIONAL_DOCUMENTARY_CUSTODY",
    }
    store.append_version(
        "NATIVE",
        "archive",
        "docs",
        "DOC",
        expected_version=0,
        command_id="IMPORT",
        event_at=None,
        available_at="2028-01-01T00:00:00Z",
        content=content,
        provenance=provenance,
        origin="MIGRATED_SYNTHETIC_HISTORY",
    )
    with store._db() as db:
        row = dict(db.execute("SELECT * FROM versions").fetchone())
    pin = {k: row[k] for k in register.IDENTITY}
    imported = {**pin, "imported_at": row["imported_at"], "provenance": provenance}
    legacy = tmp_path / "legacy"
    put(legacy / "artifacts" / content_sha, content)
    document = {
        "record_id": "DOC",
        "control_id": "CTRL",
        "sha256": content_sha,
        "original_relative_path": f"artifacts/{content_sha}",
        "available_at": row["available_at"],
        "source_identity": provenance["source_reference"],
    }
    plan = {
        "custody_plan_sha256": "a" * 64,
        "legacy_plan": {"documents": [document]},
        "archives": [
            {
                "control_id": "CTRL",
                "system_id": "docs",
                "record_ids": ["DOC"],
                "owner_id": "OWNER",
                "custody_status": "PROVISIONAL_DOCUMENTARY_CUSTODY",
                "custody_basis": "CURRENT_NOT_HISTORICAL",
            }
        ],
    }
    receipt = {"custody_plan_sha256": "a" * 64, "document_count": 1, "records": [imported]}
    reg = {
        "schema": "COMPANY_SOURCE_PORTFOLIO_V1",
        "profiles": {
            "a": {
                "company": "LOGICAL",
                "components": ["documents"],
                "qualification": "NOT_COHERENT_YEAR",
            }
        },
        "components": {
            "documents": {
                "root": str(source),
                "company": "NATIVE",
                "branch": "archive",
                "namespace": "DOC",
                "systems": ["docs"],
            }
        },
    }
    matrix = {
        "schema": "SOURCE_READINESS_INVENTORY_V1",
        "scope": {},
        "audit_snapshots": [],
        "controls": [
            {
                "control": {
                    "id": "CTRL",
                    "title": "Control",
                    "assignment": {"primary_person_id": "COORDINATOR"},
                }
            }
        ],
        "source_versions": [
            {
                **pin,
                "component_id": "documents",
                **{k: row[k] for k in ("event_at", "available_at", "origin")},
            }
        ],
    }
    regpin = put(tmp_path / "registry.json", reg)
    matrixpin = put(tmp_path / "matrix.json", matrix)
    profile = {
        "id": "a",
        "registry": regpin,
        "inventory": matrixpin,
        "profile_id": "a",
        "component_domains": {"documents": "documentary_cross_domain"},
    }
    config = {
        "schema": "COMPANY_SOURCE_REGISTER_INPUT_V1",
        "profiles": [profile, {**copy.deepcopy(profile), "id": "b"}],
        "migration": {
            "plan": put(tmp_path / "plan.json", plan),
            "receipt": put(tmp_path / "receipt.json", receipt),
            "legacy_root": str(legacy),
        },
        "finance": {"acceptance": acceptance, "source_lock": lock},
        "previous": None,
    }
    return repo, store, config, put(tmp_path / "config.json", config)


def test_actual_rows_shared_physical_history_and_finance_lock(tmp_path):
    repo, store, config, _ = fixture(tmp_path)
    before = store.path.read_bytes()
    result = register.build(config, repository=repo)
    assert result["counts"] == {
        "profile_native_references": 2,
        "unique_physical_versions": 1,
        "migration_documents": 1,
        "current_extra_versions_outside_historical_selection": 0,
    }
    row = result["source_snapshots"][0]["records"][0]
    assert row["registered_owner_id"] == "OWNER"
    assert row["scoped_control_routes"][0]["assignment"]["primary_person_id"] == "COORDINATOR"
    assert row["event_at"] is None and row["historical_owner_status"].startswith("NOT_ESTABLISHED")
    assert result["migration_register"][0]["historical_owner"] is None
    assert (
        result["finance_references"]["historical_source_lock"][0]["disposition"]
        == "CURRENT_DIFFERS_PRESERVE_HISTORICAL_LOCK"
    )
    assert store.path.read_bytes() == before


def test_extra_current_version_is_reported_not_silently_selected(tmp_path):
    repo, store, config, _ = fixture(tmp_path)
    store.append_version(
        "NATIVE",
        "archive",
        "docs",
        "NEW",
        expected_version=0,
        command_id="EXTRA",
        event_at="2028-01-02T00:00:00Z",
        available_at="2028-01-02T00:00:00Z",
        content=b"new",
        provenance={"source_reference": "new"},
    )
    result = register.build(config, repository=repo)
    assert result["counts"]["current_extra_versions_outside_historical_selection"] == 2
    assert result["counts"]["unique_physical_versions"] == 1
    assert result["source_snapshots"][0]["unselected_extras"][0]["native"]["record"] == "NEW"


@pytest.mark.parametrize("mutation", ["missing", "metadata", "content"])
def test_rejects_changed_or_missing_current_original(tmp_path, mutation):
    repo, store, config, _ = fixture(tmp_path)
    with store._db() as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute("DROP TRIGGER no_version_delete")
        if mutation == "missing":
            db.execute("DELETE FROM versions")
        elif mutation == "metadata":
            db.execute("UPDATE versions SET available_at='2029-01-01T00:00:00Z'")
        else:
            db.execute("UPDATE versions SET content=X'00'")
    with pytest.raises(ValueError):
        register.build(config, repository=repo)


def test_historical_inventory_pin_and_duplicate_identity_are_verified(tmp_path):
    repo, store, config, _ = fixture(tmp_path)
    p = Path(config["profiles"][0]["inventory"]["path"])
    obj = json.loads(p.read_text())
    obj["source_versions"] *= 2
    put(p, obj)
    with pytest.raises(ValueError, match="pin differs"):
        register.build(config, repository=repo)
    for profile in config["profiles"]:
        profile["inventory"] = put(p, obj)
    with pytest.raises(ValueError, match="Duplicate historical"):
        register.build(config, repository=repo)


def test_new_only_versioned_publication_and_manifest_members(tmp_path):
    repo, store, config, pin = fixture(tmp_path)
    destination = tmp_path / "report"
    first = register.write_register(Path(pin["path"]), destination, repository=repo)
    for name, info in first["members"].items():
        assert register.sha((destination / name).read_bytes()) == info["sha256"]
    with pytest.raises(ValueError, match="New private"):
        register.write_register(Path(pin["path"]), destination, repository=repo)
    config["previous"] = {
        "path": str(destination / "MANIFEST.json"),
        "sha256": register.sha((destination / "MANIFEST.json").read_bytes()),
    }
    put(Path(pin["path"]), config)
    second = register.write_register(Path(pin["path"]), tmp_path / "report2", repository=repo)
    assert (
        second["register_version"] == 2
        and second["predecessor_manifest_sha256"] == config["previous"]["sha256"]
    )


def test_final_source_change_prevents_publication(tmp_path, monkeypatch):
    repo, store, config, pin = fixture(tmp_path)
    original = register.canonical

    def changed(value):
        if isinstance(value, dict) and value.get("schema") == "COMPANY_SOURCE_REGISTER_MANIFEST_V1":
            with store._db() as db:
                db.execute("UPDATE systems SET owner='OTHER'")
        return original(value)

    monkeypatch.setattr(register, "canonical", changed)
    with pytest.raises(ValueError, match="Source changed before"):
        register.write_register(Path(pin["path"]), tmp_path / "report", repository=repo)
    assert not (tmp_path / "report").exists()


def test_alias_hardlink_and_sidecar_sources_rejected(tmp_path):
    repo, store, config, _ = fixture(tmp_path)
    import os

    alias = tmp_path / "alias"
    os.link(store.path, alias)
    with pytest.raises(ValueError, match="Owned bounded"):
        register.build(config, repository=repo)
    alias.unlink()
    put(Path(str(store.path) + "-wal"), b"not accepted")
    with pytest.raises(ValueError, match="sidecars"):
        register.build(config, repository=repo)


def test_output_inside_source_capsule_rejected(tmp_path):
    repo, store, config, pin = fixture(tmp_path)
    with pytest.raises(ValueError, match="overlaps"):
        register.write_register(
            Path(pin["path"]), store.path.parent.parent / "report", repository=repo
        )


def test_relationships_keep_native_branch_and_typed_version():
    pin = dict(company="SH", branch="a", system="s", record="r", version=1, sha256="a" * 64)
    result = register.relationships({"source": pin}, "source")
    assert result[0]["declared_target"] == pin and result[0]["producer_label"] is None
    with pytest.raises(ValueError, match="version"):
        register.relationships({**pin, "version": True}, "source")


def test_predecessor_member_tampering_denies_successor(tmp_path):
    repo, store, config, pin = fixture(tmp_path)
    destination = tmp_path / "report"
    register.write_register(Path(pin["path"]), destination, repository=repo)
    config["previous"] = {
        "path": str(destination / "MANIFEST.json"),
        "sha256": register.sha((destination / "MANIFEST.json").read_bytes()),
    }
    put(destination / "MIGRATION_REGISTER.json", {})
    with pytest.raises(ValueError, match="Predecessor register member"):
        register.build(config, repository=repo)


def test_changed_accepted_packet_rejected(tmp_path):
    repo, store, config, pin = fixture(tmp_path)
    put(repo / "docs/packet.bin", b"altered")
    with pytest.raises(ValueError, match="Accepted finance artifact"):
        register.build(config, repository=repo)


def test_descriptor_swap_cannot_replace_pinned_file(tmp_path, monkeypatch):
    import os

    target = tmp_path / "target"
    put(target, b"original")
    alternate = tmp_path / "alternate"
    put(alternate, b"replacement")
    original = os.open

    def swap(path, flags, *args, **kwargs):
        if Path(path) == target:
            target.rename(tmp_path / "old")
            alternate.rename(target)
        return original(path, flags, *args, **kwargs)

    monkeypatch.setattr(register.os, "open", swap)
    with pytest.raises(ValueError, match="replaced before descriptor"):
        register.raw_file(target)
