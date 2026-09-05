import csv
import hashlib
import json
import sqlite3
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import Base, JournalEntry, JournalLine, Worker
from sable_harbor.exports.safety import scan_generated_artifacts
from sable_harbor.exports.units import package_business_units
from sable_harbor.generation import generate_standard
from sable_harbor.provenance.service import complete_generation_run, record_generation_run


def test_all_current_business_units_get_scoped_reconciled_packages(tmp_path) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run = record_generation_run(
            session, profile="standard", scenario_code="base", seed=20260831, git_commit="a" * 40
        )
        generate_standard(session)
        complete_generation_run(session, run)
        session.commit()
        manifests = package_business_units(
            session, tmp_path / "units", generation_run_id=run.id, generated_at=run.completed_at
        )

    assert len(manifests) == 7
    assert scan_generated_artifacts(tmp_path / "units") == []
    aggregate_checksum = tmp_path / "units/SHA256SUMS.txt"
    aggregate_lines = aggregate_checksum.read_text().splitlines()
    assert any(line.endswith("/manifest.json") for line in aggregate_lines)
    for line in aggregate_lines:
        expected, relative = line.split("  ", 1)
        assert hashlib.sha256((tmp_path / "units" / relative).read_bytes()).hexdigest() == expected
    for manifest_path in manifests:
        root = manifest_path.parent
        manifest = json.loads(manifest_path.read_text())
        assert manifest["validation"]["status"] == "PASS"
        assert manifest["epistemic_mode"] == "RETROSPECTIVE_CURRENT_CANON"
        assert manifest["canon_effective_through"] == "2026-09-03"
        assert manifest["canon_reconciled_at"] == "2026-09-05"
        assert manifest["prepared_at"] == "2026-09-05"
        assert manifest["synthetic_calibration_through"] == "2026-08-31"
        assert "knowledge_cutoff" not in manifest
        assert manifest["input_version"] == "finance-generation-input-manifest/v1"
        assert len(manifest["input_manifest_digest"]) == 64
        assert len(manifest["generator_source_digest"]) == 64
        assert manifest["effective_period"]["from"] <= manifest["effective_period"]["through"]
        assert manifest["source_snapshot_ids"]["current_canon"].startswith("main@")
        assert {item["data_role"] for item in manifest["included_runs"]} == {
            "selected_synthetic_scenario",
            "shared_synthetic_calibration",
        }
        assert manifest["row_counts"]["journal_line_evidence"] > 0
        bridge = manifest["validation"]["enterprise_bridge"]
        for field in (
            "enterprise_debits",
            "enterprise_credits",
            "packaged_debits",
            "packaged_credits",
            "excluded_debits",
            "excluded_credits",
            "debit_difference",
            "credit_difference",
        ):
            value = Decimal(bridge[field])
            assert value == value.quantize(Decimal("0.0001"))
        assert manifest["output_hashes"] == {
            artifact["path"]: artifact["sha256"] for artifact in manifest["artifacts"]
        }
        for artifact in manifest["artifacts"]:
            assert (
                hashlib.sha256((root / artifact["path"]).read_bytes()).hexdigest()
                == artifact["sha256"]
            )
        database = root / f"database/{manifest['unit_id']}.sqlite"
        with sqlite3.connect(database) as connection:
            entities = {
                row[0]
                for row in connection.execute(
                    "SELECT DISTINCT entity_code FROM journal_line_evidence"
                )
            }
        assert entities <= set(manifest["filters"]["entities"])
        assert (
            "NO_RECORDS"
            not in (root / "operations/domain-registers/primary-register.csv").read_text()
        )
        for line in (root / "SHA256SUMS.txt").read_text().splitlines():
            expected, relative = line.split("  ", 1)
            assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected


def test_unit_packages_are_segment_disjoint_and_ignore_another_seed(tmp_path) -> None:
    engine = create_engine("sqlite:///:memory:")
    with Session(engine) as session:
        Base.metadata.create_all(engine)
        selected = record_generation_run(
            session, profile="standard", scenario_code="base", seed=20260831, git_commit="a" * 40
        )
        generate_standard(session, seed=20260831)
        complete_generation_run(session, selected)
        session.commit()
        selected_run_ids = (selected.actual_generation_run_id, selected.id)
        registry = json.loads(Path("config/finance/unit_scopes.json").read_text())
        expected_workers = {
            unit["id"]: len(
                session.scalars(
                    select(Worker).where(
                        Worker.generation_run_id.in_(selected_run_ids),
                        Worker.segment_code.in_(unit["segment_codes"]),
                    )
                ).all()
            )
            for unit in registry["units"]
        }

        other = record_generation_run(
            session, profile="standard", scenario_code="base", seed=20260901, git_commit="a" * 40
        )
        generate_standard(session, seed=20260901)
        complete_generation_run(session, other)
        session.commit()
        other_line_ids = set(
            session.scalars(
                select(JournalLine.id)
                .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
                .where(
                    JournalEntry.generation_run_id.in_((other.actual_generation_run_id, other.id))
                )
            )
        )

        manifests = package_business_units(
            session, tmp_path / "units", generation_run_id=selected.id
        )

    seen_lines: set[str] = set()
    for manifest_path in manifests:
        root = manifest_path.parent
        manifest = json.loads(manifest_path.read_text())
        with sqlite3.connect(root / f"database/{manifest['unit_id']}.sqlite") as connection:
            lines = connection.execute(
                "SELECT journal_line_id, segment_code FROM journal_line_evidence"
            ).fetchall()
        line_ids = {line_id for line_id, _segment in lines}
        assert seen_lines.isdisjoint(line_ids)
        seen_lines.update(line_ids)
        for _line_id, segment in lines:
            assert segment in manifest["filters"]["segments"] or (
                not segment and manifest["filters"]["include_unsegmented"]
            )
        workforce = root / "operations/workforce-summary.csv"
        rows = list(csv.DictReader(workforce.open()))
        packaged_workers = sum(int(row["workers"]) for row in rows if "workers" in row)
        assert packaged_workers == expected_workers[manifest["unit_id"]]

    # A second seed in the enterprise database cannot leak into any package.
    assert seen_lines.isdisjoint(other_line_ids)
    bridge = json.loads(manifests[0].read_text())["validation"]["enterprise_bridge"]
    assert bridge["packaged_unique_line_count"] == len(seen_lines)
    assert bridge["duplicate_packaged_line_count"] == 0
    assert bridge["unknown_packaged_line_count"] == 0


def test_unit_packages_are_byte_deterministic_for_a_controlled_timestamp(tmp_path) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run = record_generation_run(
            session, profile="standard", scenario_code="base", seed=20260831, git_commit="a" * 40
        )
        generate_standard(session)
        complete_generation_run(session, run)
        session.commit()
        first = package_business_units(
            session, tmp_path / "first", generation_run_id=run.id, generated_at=run.completed_at
        )
        second = package_business_units(
            session, tmp_path / "second", generation_run_id=run.id, generated_at=run.completed_at
        )

    def inventory(manifests: list[Path]) -> dict[Path, str]:
        root = manifests[0].parents[2]
        return {
            path.relative_to(root): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*")
            if path.is_file()
        }

    assert inventory(first) == inventory(second)


def test_unit_registry_rejects_path_traversal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sable_harbor.exports.units as units

    registry = json.loads(units.UNIT_REGISTRY.read_text())
    unsafe = deepcopy(registry)
    unsafe["units"][0]["id"] = "../escape"
    path = tmp_path / "unit-scopes.json"
    path.write_text(json.dumps(unsafe))
    monkeypatch.setattr(units, "UNIT_REGISTRY", path)
    with pytest.raises(ValueError, match="unsafe id"):
        units._unit_registry()


def test_unit_workbook_rejects_rows_beyond_excel_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sable_harbor.exports.units as units

    monkeypatch.setattr(units, "EXCEL_MAX_ROWS", 4)
    with pytest.raises(ValueError, match="exceeds the Excel row limit"):
        units._workbook(
            tmp_path / "oversized.xlsx",
            "Test unit",
            [{"account": "1000"}, {"account": "2000"}],
            datetime(2026, 9, 5, tzinfo=UTC),
        )


def test_unit_controls_honor_an_explicit_unsegmented_scope() -> None:
    import sable_harbor.exports.units as units

    lines = [
        {
            "journal_entry_id": "journal",
            "journal_line_id": "debit",
            "debit": "1",
            "credit": "0",
            "segment_code": "",
            "source_type": "test",
            "source_id": "source",
        },
        {
            "journal_entry_id": "journal",
            "journal_line_id": "credit",
            "debit": "0",
            "credit": "1",
            "segment_code": "",
            "source_type": "test",
            "source_id": "source",
        },
    ]
    controls = units._unit_control_results(lines, ["TEST"], include_unsegmented=True)
    assert (
        next(item for item in controls if item["code"] == "UNIT_SEGMENT_SCOPE")["status"] == "PASS"
    )
