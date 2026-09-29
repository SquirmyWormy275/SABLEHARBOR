import copy
import hashlib
import json
import sqlite3

import pytest

from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.source_readiness import inventory, load_config, write_inventory
from enterprise.audit_suite.store import Store


@pytest.fixture
def fixture(tmp_path):
    tmp_path.chmod(0o700)
    audit_root = tmp_path / "audit"
    store = Store(audit_root)
    actor = store.provision("Operator", ["instructor"])["id"]
    company_root = tmp_path / "company"
    company_root.mkdir(mode=0o700)
    company = CompanyStore(company_root)
    for branch in ("selected", "unselected"):
        company.register_system("SH", branch, "records", "owner")
    company.register_system("SH", "selected", "empty", "owner")
    content = b'{"control_id":"C1","boundary_id":"B1"}'
    company.append_version(
        "SH",
        "selected",
        "records",
        "R1",
        expected_version=0,
        command_id="source",
        event_at=None,
        available_at="2027-02-01T00:00:00Z",
        content=content,
        origin="REPOSITORY_SYNTHETIC_DOCUMENT",
        provenance={"source_reference": "source.md", "control_ids": ["C1"]},
    )
    state = store.create(
        actor,
        {
            "controls": [{"id": "C1", "procedure": "Inspect assigned source"}, {"id": "C2"}],
            "scope": {"boundaries": ["B1"], "exclusions": [{"id": "EX1"}]},
            "artifacts": [],
        },
        "create",
    )
    company.grant(actor, state["id"], "SH", "selected", "records")
    receipt = company.collect(
        actor,
        state["id"],
        "SH",
        "selected",
        "records",
        "R1",
        version=1,
        as_of="2027-02-02T00:00:00Z",
        command_id="collect",
    )
    config = {
        "target": {"root": str(audit_root), "engagement_id": state["id"]},
        "audits": [],
        "sources": [
            {
                "id": "source",
                "root": str(company_root),
                "company": "SH",
                "branch": "selected",
                "systems": ["records", "empty"],
                "category": "operations",
            }
        ],
    }
    return config, store, company, receipt, actor


def test_non70_scope_documentary_origin_and_no_mutation(fixture):
    config, store, company, _, _ = fixture
    before = company.path.read_bytes()
    report = inventory(config)
    assert report["summary"]["scoped_controls"] == 2
    assert report["summary"]["controls_with_explicit_references"] == 1
    assert report["source_versions"][0]["classification"] == "DOCUMENTARY_NOT_OPERATING_FACT"
    assert len(report["source_versions"][0]["verified_collections"]) == 1
    assert report["source_snapshots"][0]["systems"][0]["versions"] == 0
    assert report["scope"]["exclusions"] == [{"id": "EX1"}]
    assert report["controls"][1]["reference_status"] == "NO_EXPLICIT_REFERENCE_IN_SELECTED_SOURCES"
    assert company.path.read_bytes() == before
    assert "token_hash" not in json.dumps(report)
    assert "Operator" not in json.dumps(report)
    assert store.db_path.exists()


def test_explicit_engagement_only_and_categories_are_labels(fixture):
    config, store, _, _, actor = fixture
    other = store.create(
        actor, {"controls": [{"id": "SECRET"}], "scope": {}, "artifacts": []}, "other"
    )
    report = inventory(config)
    assert other["id"] not in json.dumps(report)
    config["sources"][0]["category"] = "ACTUAL_OPERATING_FACT"
    assert (
        inventory(config)["source_versions"][0]["classification"]
        == "DOCUMENTARY_NOT_OPERATING_FACT"
    )


def test_bad_native_hash_fails(fixture):
    config, _, company, _, _ = fixture
    with company._db() as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute("UPDATE versions SET content=?", (b"wrong",))
    with pytest.raises(ValueError, match="Native source integrity"):
        inventory(config)


@pytest.mark.parametrize(
    "field,value",
    [
        ("content_bytes", 999),
        ("simulated_as_of", "2020-01-01T00:00:00Z"),
        ("command_id", "changed"),
    ],
)
def test_bad_receipt_fails(fixture, field, value):
    config, _, company, receipt, _ = fixture
    receipt[field] = value
    with company._db() as db:
        db.execute("DROP TRIGGER no_collection_update")
        db.execute("UPDATE collections SET receipt=?", (json.dumps(receipt),))
    with pytest.raises(ValueError, match="Collection"):
        inventory(config)


def test_bad_receipt_source_identity_fails(fixture):
    config, _, company, receipt, _ = fixture
    receipt["source"]["sha256"] = "0" * 64
    with company._db() as db:
        db.execute("DROP TRIGGER no_collection_update")
        db.execute("UPDATE collections SET receipt=?", (json.dumps(receipt),))
    with pytest.raises(ValueError, match="absent or changed"):
        inventory(config)


def test_history_tamper_fails(fixture):
    config, store, _, _, _ = fixture
    with store.connect() as db:
        db.execute("DROP TRIGGER events_no_update")
        db.execute("UPDATE events SET actor='changed'")
    with pytest.raises(ValueError, match="history integrity"):
        inventory(config)


def test_private_output_and_no_overwrite(fixture, tmp_path):
    config, _, _, _, _ = fixture
    output = tmp_path / "report"
    result = write_inventory(config, output)
    assert result["summary"]["scoped_controls"] == 2
    for file in output.iterdir():
        assert file.stat().st_mode & 0o777 == 0o600
    assert output.stat().st_mode & 0o777 == 0o700
    with pytest.raises(ValueError, match="New destination"):
        write_inventory(config, output)
    with pytest.raises(ValueError, match="inside input"):
        write_inventory(config, tmp_path / "company" / "report")


def test_alias_public_missing_and_unknown_selectors(fixture, tmp_path):
    config, _, company, _, _ = fixture
    invalid = copy.deepcopy(config)
    invalid["target"]["unexpected"] = "no"
    with pytest.raises(ValueError):
        inventory(invalid)
    invalid = copy.deepcopy(config)
    invalid["sources"][0]["systems"] = ["unknown"]
    with pytest.raises(ValueError, match="not registered"):
        inventory(invalid)
    alias = tmp_path / "alias"
    alias.symlink_to(tmp_path / "company")
    invalid = copy.deepcopy(config)
    invalid["sources"][0]["root"] = str(alias)
    with pytest.raises(ValueError, match="aliases"):
        inventory(invalid)
    company.path.chmod(0o644)
    with pytest.raises(ValueError, match="Private"):
        inventory(config)


def test_malformed_typed_reference_is_not_prose_mapping(fixture):
    config, _, company, _, _ = fixture
    with company._db() as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute("UPDATE versions SET provenance=?", ('{"control_ids":42}',))
    with pytest.raises(ValueError, match="typed control"):
        inventory(config)


def test_duplicate_json_config_rejected(tmp_path):
    tmp_path.chmod(0o700)
    path = tmp_path / "config.json"
    path.write_text('{"target":{},"target":{}}')
    path.chmod(0o600)
    with pytest.raises(ValueError, match="Duplicate"):
        load_config(path)


def test_distinct_stores_same_native_identity_remain_separate(fixture, tmp_path):
    config, _, company, _, _ = fixture
    other = tmp_path / "other"
    other.mkdir(mode=0o700)
    # SQLite backup is test setup only, not part of the inventory API.
    with company._db() as src, sqlite3.connect(other / "company.sqlite3") as dst:
        src.backup(dst)
    (other / "company.sqlite3").chmod(0o600)
    config["sources"].append({**config["sources"][0], "id": "second", "root": str(other)})
    report = inventory(config)
    assert report["summary"]["source_versions"] == 2
    assert {r["component_id"] for r in report["source_versions"]} == {"source", "second"}
    assert all(
        p["snapshot_isolation"] == "ONE_DATABASE_READ_TRANSACTION"
        for p in report["source_snapshots"]
    )


def test_retained_native_original_verified_and_corruption_rejected(fixture):
    config, store, _, receipt, actor = fixture
    original = store.get(actor, config["target"]["engagement_id"])
    raw = b'{"control_id":"C1","boundary_id":"B1"}'
    sha = hashlib.sha256(raw).hexdigest()
    root = store.root / "artifacts"
    root.mkdir(mode=0o700)
    path = root / sha
    path.write_bytes(raw)
    path.chmod(0o600)
    # Same creation ID is needed by native receipt; add artifact through a normal store command.
    command = {
        "command_id": "retain",
        "expected_revision": 0,
        "kind": "neutral.fixture",
        "payload": {},
    }
    artifact = {
        "id": "A1",
        "sha256": sha,
        "bytes": len(raw),
        "source": {"kind": "COLLECTED_COMPANY_SOURCE", "receipt": receipt},
    }

    def reduce(current, _command, _actor):
        current["artifacts"].append(artifact)
        return current

    store.command(actor, original["id"], command, reduce, permissions={"instruct"})
    assert inventory(config)["summary"]["verified_retained_originals"] == 1
    path.write_bytes(b"broken")
    with pytest.raises(ValueError, match="Retained original integrity"):
        inventory(config)


def test_wal_append_does_not_change_current_source_snapshot(fixture, monkeypatch):
    from enterprise.audit_suite import source_readiness

    config, _, company, _, _ = fixture
    with company._db() as db:
        db.execute("PRAGMA journal_mode=WAL")
    original = source_readiness._references
    appended = False

    def during_read(obj, location):
        nonlocal appended
        if not appended and location == "provenance":
            appended = True
            company.append_version(
                "SH",
                "selected",
                "records",
                "R2",
                expected_version=0,
                command_id="later",
                event_at="2027-02-01T00:00:00Z",
                available_at="2027-02-01T00:00:00Z",
                content=b'{"control_id":"C2"}',
                provenance={"source_reference": "later"},
            )
        return original(obj, location)

    monkeypatch.setattr(source_readiness, "_references", during_read)
    first = inventory(config)
    assert first["summary"]["source_versions"] == 1
    assert inventory(config)["summary"]["source_versions"] == 2


def test_receipt_metadata_drift_is_rejected(fixture):
    config, _, company, receipt, _ = fixture
    receipt["source"]["provenance"]["control_ids"] = ["WRONG"]
    with company._db() as db:
        db.execute("DROP TRIGGER no_collection_update")
        db.execute("UPDATE collections SET receipt=?", (json.dumps(receipt),))
    with pytest.raises(ValueError, match="metadata mismatch"):
        inventory(config)


def test_cli_executes_from_outside_repository(fixture, tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    config, *_ = fixture
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    path.chmod(0o600)
    tool = Path(__file__).resolve().parents[2] / "tools/audit_suite/source_readiness.py"
    result = subprocess.run(
        [
            sys.executable,
            str(tool),
            "--config",
            str(path),
            "--output",
            str(tmp_path / "cli-report"),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["summary"]["scoped_controls"] == 2


def test_migrated_model_is_not_automatically_documentary_or_operating():
    from enterprise.audit_suite.source_readiness import _classification

    assert (
        _classification("MIGRATED_SYNTHETIC_HISTORY", {"classification": "MODEL_PROJECTION"})
        == "MIGRATED_REFERENCE_NOT_OPERATING_FACT"
    )
    assert (
        _classification(
            "MIGRATED_SYNTHETIC_HISTORY", {"classification": "LEGACY_SYNTHETIC_DOCUMENTARY_SOURCE"}
        )
        == "DOCUMENTARY_NOT_OPERATING_FACT"
    )
    assert (
        _classification("AUTHORED_TRAINING_SOURCE", {})
        == "AUTHORED_ACTIVITY_OR_REFERENCE_NOT_OPERATING_FACT"
    )
    assert _classification("UNKNOWN", {}) == "UNCLASSIFIED_NOT_OPERATING_FACT"
