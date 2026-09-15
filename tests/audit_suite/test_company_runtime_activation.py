import hashlib
import json
import os
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_runtime_activation as activation
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from tests.audit_suite.test_company_activity_plan_sources import source as original_source


@pytest.fixture
def source(tmp_path):
    return original_source.__wrapped__(tmp_path)


def activate(source, dest):
    return activation.activate(
        source["source_manifest_path"].parent,
        dest,
        expected_manifest_sha256=source["expected_manifest_sha256"],
    )


def tables(path):
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
        return {
            t: db.execute("SELECT * FROM " + t + " ORDER BY 1,2,3").fetchall()
            for t in ["systems", "versions"]
        }


def repin(source):
    manifest = source["source_manifest_path"]
    body = json.loads(manifest.read_bytes())
    for name in body["members"]:
        body["members"][name] = hashlib.sha256((manifest.parent / name).read_bytes()).hexdigest()
    manifest.write_text(json.dumps(body))
    source["expected_manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()


def test_all_native_fields_immutable_capsule_and_mutable_runtime(source, tmp_path):
    capsule = source["source_manifest_path"].parent
    originals = {
        p: hashlib.sha256(p.read_bytes()).hexdigest() for p in capsule.rglob("*") if p.is_file()
    }
    native = tables(source["source_root"] / "company.sqlite3")
    result = activate(source, tmp_path / "runtime")
    assert result["seed_counts"] == {
        "systems": 10,
        "versions": 20,
        "grants": 0,
        "collections": 0,
        "access_events": 0,
    }
    assert tables(tmp_path / "runtime/company.sqlite3") == native
    assert result["native_fields_preserved"] == list(activation.VERSION_FIELDS)
    store = CompanyStore(tmp_path / "runtime")
    row = native["systems"][0]
    store.grant("auditor", "engagement", *row[:3])
    assert hashlib.sha256(store.path.read_bytes()).hexdigest() != result["seed_database_sha256"]
    assert tables(store.path) == native
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == pin for p, pin in originals.items())
    assert all(p.stat().st_mode & 0o077 == 0 for p in (tmp_path / "runtime").iterdir())
    with pytest.raises(CompanyStoreError):
        activate(source, tmp_path / "runtime")


def test_source_schema_triggers_are_not_executed_or_copied(source, tmp_path):
    path = source["source_root"] / "company.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TRIGGER incoming_trigger AFTER INSERT ON systems BEGIN "
            "INSERT INTO access_events(principal) VALUES('incoming'); END"
        )
    repin(source)
    activate(source, tmp_path / "runtime")
    with CompanyStore(tmp_path / "runtime")._db() as db:
        assert (
            db.execute("SELECT name FROM sqlite_master WHERE name='incoming_trigger'").fetchone()
            is None
        )
        assert db.execute("SELECT COUNT(*) FROM access_events").fetchone()[0] == 0


@pytest.mark.parametrize("fault", ["digest", "grants", "schema", "sequence"])
def test_repinned_but_invalid_native_capsule_rejected(source, tmp_path, fault):
    path = source["source_root"] / "company.sqlite3"
    with sqlite3.connect(path) as db:
        if fault == "digest":
            db.execute("DROP TRIGGER no_version_update")
            db.execute(
                "UPDATE versions SET input_digest='incorrect' "
                "WHERE rowid=(SELECT MIN(rowid) FROM versions)"
            )
        if fault == "grants":
            db.execute("INSERT INTO grants VALUES('p','e','SH','b','s',0)")
        if fault == "schema":
            db.execute("ALTER TABLE systems ADD COLUMN unexpected TEXT")
        if fault == "sequence":
            db.execute("DROP TRIGGER no_version_update")
            db.execute(
                "UPDATE versions SET version=99 WHERE rowid=(SELECT MIN(rowid) FROM versions)"
            )
    repin(source)
    with pytest.raises(CompanyStoreError):
        activate(source, tmp_path / "runtime")
    assert not (tmp_path / "runtime").exists()


@pytest.mark.parametrize("fault", ["inside", "hardlink", "alias", "manifest"])
def test_private_input_output_boundaries(source, tmp_path, fault):
    destination = tmp_path / "runtime"
    if fault == "inside":
        destination = source["source_manifest_path"].parent / "runtime"
    if fault == "hardlink":
        os.link(source["source_root"] / "company.sqlite3", tmp_path / "alias.sqlite3")
    if fault == "alias":
        alias = tmp_path / "alias"
        alias.symlink_to(source["source_manifest_path"].parent)
        source["source_manifest_path"] = alias / "MANIFEST.json"
    if fault == "manifest":
        source["expected_manifest_sha256"] = "0" * 64
    with pytest.raises(CompanyStoreError):
        activate(source, destination)
    assert not destination.exists()


@pytest.mark.parametrize("fail", [False, True])
def test_readonly_source_connection_closed_on_success_and_failure(
    source, tmp_path, monkeypatch, fail
):
    actual = activation.sqlite3.connect
    connections = []

    def connect(*args, **kwargs):
        result = actual(*args, **kwargs)
        if "?mode=ro" in str(args[0]):
            connections.append(result)
            if fail:
                (source["source_root"] / "company.sqlite3").chmod(0o644)
        return result

    monkeypatch.setattr(activation.sqlite3, "connect", connect)
    if fail:
        with pytest.raises(CompanyStoreError):
            activate(source, tmp_path / "runtime")
    else:
        activate(source, tmp_path / "runtime")
    assert len(connections) == 1
    with pytest.raises(sqlite3.ProgrammingError):
        connections[0].execute("SELECT 1")
    if fail:
        assert not (tmp_path / "runtime").exists()


def test_failed_publication_leaves_no_destination(source, tmp_path, monkeypatch):
    import enterprise.audit_suite.private_publication as publication

    original = publication.os.rename
    count = 0

    def move(src, dst):
        nonlocal count
        if Path(dst).parent == tmp_path / "runtime":
            count += 1
            if count == 2:
                raise OSError("injected publication failure")
        return original(src, dst)

    monkeypatch.setattr(publication.os, "rename", move)
    with pytest.raises(OSError):
        activate(source, tmp_path / "runtime")
    assert not (tmp_path / "runtime").exists()
    assert source["source_manifest_path"].exists()


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_unmanifested_sqlite_sidecars_are_rejected(source, tmp_path, suffix):
    path = source["source_root"] / ("company.sqlite3" + suffix)
    path.write_bytes(b"unmanifested state")
    path.chmod(0o600)
    with pytest.raises(CompanyStoreError):
        activate(source, tmp_path / "runtime")
    assert not (tmp_path / "runtime").exists()
