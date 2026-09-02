import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import Base
from sable_harbor.exports.release import PUBLIC_ALLOWLIST, package_public_demo, sha256
from sable_harbor.exports.safety import scan_generated_artifacts
from sable_harbor.generation import generate_standard
from sable_harbor.provenance.service import complete_generation_run, record_generation_run


def test_public_release_manifest_inventory_and_checksums(tmp_path: Path) -> None:
    database = tmp_path / "source.sqlite"
    engine = create_engine(f"sqlite:///{database}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run = record_generation_run(
            session, profile="standard", scenario_code="base", seed=20260831, git_commit="test"
        )
        generate_standard(session)
        complete_generation_run(session, run)
        session.commit()
        generated_at = datetime(2026, 8, 31, tzinfo=UTC)
        manifest_path = package_public_demo(
            session,
            tmp_path / "release",
            generation_run_id=run.id,
            generated_at=generated_at,
        )
    manifest = json.loads(manifest_path.read_text())
    assert manifest["validation_status"] == "PASS"
    assert manifest["artifact_safety_scan"] == {"status": "PASS", "failures": 0}
    assert manifest["schema_versions"] == ["0014"]
    assert manifest["classification"] == "PUBLIC_SAFE_SYNTHETIC"
    assert manifest["row_counts"]["journal_entry"] > 0
    for artifact in manifest["artifacts"]:
        path = manifest_path.parent / artifact["path"]
        assert path.exists()
        assert sha256(path) == artifact["sha256"]
    assert (manifest_path.parent / "sable_harbor_public_demo.sqlite").stat().st_size > 0
    allowlist = json.loads(PUBLIC_ALLOWLIST.read_text())["tables"]
    connection = sqlite3.connect(manifest_path.parent / "sable_harbor_public_demo.sqlite")
    try:
        actual_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        assert actual_tables == set(allowlist)
        for table, expected_columns in allowlist.items():
            actual_columns = [
                row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')
            ]
            assert actual_columns == expected_columns
        assert "generation_run" not in actual_tables
        assert "artifact" not in actual_tables
    finally:
        connection.close()
    assert scan_generated_artifacts(manifest_path.parent) == []


def test_public_release_is_deterministic_and_removes_stale_outputs(tmp_path: Path) -> None:
    database = tmp_path / "source.sqlite"
    engine = create_engine(f"sqlite:///{database}")
    Base.metadata.create_all(engine)
    generated_at = datetime(2026, 8, 31, tzinfo=UTC)
    with Session(engine) as session:
        run = record_generation_run(
            session, profile="standard", scenario_code="base", seed=20260831, git_commit="test"
        )
        generate_standard(session)
        complete_generation_run(session, run)
        session.commit()
        first = package_public_demo(
            session, tmp_path / "first", generation_run_id=run.id, generated_at=generated_at
        )
        stale = tmp_path / "second" / "obsolete.txt"
        stale.parent.mkdir()
        stale.write_text("must be removed")
        second = package_public_demo(
            session, tmp_path / "second", generation_run_id=run.id, generated_at=generated_at
        )
    first_files = {
        path.relative_to(first.parent): sha256(path)
        for path in first.parent.rglob("*")
        if path.is_file()
    }
    second_files = {
        path.relative_to(second.parent): sha256(path)
        for path in second.parent.rglob("*")
        if path.is_file()
    }
    assert first_files == second_files
    assert not stale.exists()


def test_generated_artifact_scan_reads_values_and_xlsx_relationships(tmp_path: Path) -> None:
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("value\n/home/private/oracle\n")
    failures = scan_generated_artifacts(tmp_path)
    assert any("forbidden marker" in failure for failure in failures)
