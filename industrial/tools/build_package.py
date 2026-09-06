#!/usr/bin/env python3
"""Build an explicit, dated industrial participant corpus and deterministic ZIP.

The reviewed catalog is an allowlist, not a recursive repository export. Unknown
availability dates fail closed. A future effective date is admitted only as an
explicit forecast, commitment or option known at the cutoff. Company evidence and
the editorial handoff remain different publication classes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
import zlib
from calendar import monthrange
from datetime import datetime, time
from pathlib import Path, PurePosixPath
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
INDUSTRIAL = ROOT / "industrial"
CATALOG = INDUSTRIAL / "source/participant_catalog.json"
DIST = INDUSTRIAL / "dist"
VERSION = "1.0.0"
CUTOFF = "2026-09-05T23:59:59-07:00"
ARCHIVE_NAME = f"sable-harbor-industrial-participant-v{VERSION}.zip"
FUTURE_MODES = {"MODEL_WITH_FORECASTS", "COMMITMENT", "OPTION"}
FORBIDDEN_PARTS = {".git", ".env", "history", "handoffs", "__pycache__", "tests"}
FORBIDDEN_TERMS = ("evaluator", "answer_key", "hidden_truth", "scoring_key")


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def instant(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("An explicit availability/effective date is required")
    if re.fullmatch(r"\d{4}", value):
        value += "-12-31"  # conservative upper bound of an imprecise year
    elif re.fullmatch(r"\d{4}-\d{2}", value):
        year, month = map(int, value.split("-"))
        value += f"-{monthrange(year, month)[1]:02d}"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        day = datetime.fromisoformat(value).date()
        return datetime.combine(day, time(23, 59, 59), ZoneInfo("America/Los_Angeles"))
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"Timestamp lacks a timezone: {value}")
    return parsed


def eligible(entry: dict, cutoff: str = CUTOFF) -> bool:
    available = instant(entry.get("available_at"))
    effective = instant(entry.get("effective_at"))
    limit = instant(cutoff)
    if available > limit:
        return False
    if effective > limit and entry.get("temporal_mode") not in FUTURE_MODES:
        return False
    if not entry.get("availability_basis") or not entry.get("fact_state"):
        raise ValueError("Availability provenance and fact state are required")
    return True


def member_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value or "\x00" in value:
        raise ValueError(f"Unsafe participant path: {value!r}")
    if any(part in FORBIDDEN_PARTS for part in path.parts):
        raise ValueError(f"Nonparticipant source path: {value}")
    if any(term in value.lower() for term in FORBIDDEN_TERMS):
        raise ValueError(f"Nonparticipant content class: {value}")
    return path


def validate_row_time(row: dict, source: str, cutoff: str = CUTOFF) -> None:
    """A full financial/production month becomes complete only at its end.

    Artifact-level availability cannot convert a future row into a completed
    result. An explicitly forecast/commitment row remains eligible for inclusion.
    Undated registers instead inherit their reviewed artifact metadata.
    """
    for name in ("available_at", "available_on"):
        if name in row and instant(row[name]) > instant(cutoff):
            raise ValueError(f"Row unavailable at case cutoff: {source}")
    role = row.get("period_role", "")
    if role and role not in {
        "SYNTHETIC_CALIBRATION",
        "SYNTHETIC_HISTORICAL_CASE",
        "MANAGEMENT_FORECAST",
        "MANAGEMENT_SCENARIO_AT_2026_09_05",
        "FORECAST",
        "COMMITMENT",
        "OPTION",
    }:
        raise ValueError(f"Unrecognized or actual result class in {source}: {role}")
    labels = [
        str(row.get(key, "")).upper()
        for key in (
            "period_role",
            "status",
            "state",
            "record_origin",
            "case_role",
            "temporal_mode",
            "epistemic_state",
        )
    ]
    completed = any(
        label
        in {
            "ACTUAL",
            "SYNTHETIC_ACTUAL",
            "COMPLETE",
            "COMPLETED",
            "COMPLETE_SYNTHETIC",
            "CLOSED",
            "CLOSED_SYNTHETIC",
            "SYNTHETIC_CALIBRATION",
            "SYNTHETIC_HISTORICAL_CASE",
        }
        for label in labels
    )
    prospective = any(
        any(
            term in label
            for term in (
                "FORECAST",
                "COMMITMENT",
                "CONTRACTUAL_FUTURE",
                "OPTION",
                "SCENARIO",
                "SIMULATION",
                "OPEN_GATED",
            )
        )
        for label in labels
    )
    for key in (
        "date",
        "event_date",
        "effective_period_end",
        "received",
        "handling_start",
        "empty_release",
    ):
        if key in row and row[key] not in (None, ""):
            if instant(str(row[key])) > instant(cutoff) and (completed or not prospective):
                raise ValueError(
                    f"Future event lacks a prospective class in {source}: {key}={row[key]}"
                )
    if row.get("effective_period_end"):
        if instant(row["effective_period_end"]) > instant(cutoff) and role in {
            "SYNTHETIC_CALIBRATION",
            "SYNTHETIC_HISTORICAL_CASE",
        }:
            raise ValueError(f"Future effective period labeled completed in {source}")
    year = row.get("year")
    month = row.get("through_month", row.get("month"))
    if isinstance(month, str) and re.fullmatch(r"\d{4}-\d{2}(?:-\d{2})?", month):
        year, month = int(month[:4]), int(month[5:7])
    elif year is not None and month not in (None, ""):
        year, month = int(year), int(month)
    else:
        return
    if month == 0:  # explicitly posted acquisition/opening balance
        return
    last = monthrange(year, month)[1]
    period_end = instant(f"{year:04d}-{month:02d}-{last:02d}")
    if period_end > instant(cutoff) and (completed or not prospective):
        raise ValueError(
            f"Future month labeled completed calibration in {source}: {year}-{month:02d}"
        )


def validate_temporal_tree(value: object, source: str, cutoff: str = CUTOFF) -> None:
    """Inspect dated records in JSON, GeoJSON properties and embedded CSV JSON."""
    if isinstance(value, dict):
        validate_row_time(value, source, cutoff)
        for child in value.values():
            validate_temporal_tree(child, source, cutoff)
    elif isinstance(value, list):
        for child in value:
            validate_temporal_tree(child, source, cutoff)
    elif isinstance(value, str) and value.startswith(("{", "[")):
        try:
            child = json.loads(value)
        except json.JSONDecodeError:
            return
        validate_temporal_tree(child, source, cutoff)


def reviewed_entries(catalog: dict, root: Path = ROOT) -> list[dict]:
    if catalog.get("cutoff") != CUTOFF or catalog.get("version") != VERSION:
        raise ValueError("Unsupported case version/cutoff")
    entries = catalog.get("artifacts", [])
    if not entries:
        raise ValueError("An empty catalog is not a participant case")
    paths: set[str] = set()
    chronology_path = root / "industrial/source/chronology.json"
    dated_records = {}
    if chronology_path.is_file():
        dated_records = {
            document["path"]: document
            for document in json.loads(chronology_path.read_text())["documents"]
        }
    for entry in entries:
        source_name = str(member_path(entry["path"]))
        if source_name in paths:
            raise ValueError(f"Duplicate participant artifact: {source_name}")
        paths.add(source_name)
        source = root / source_name
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"Missing or linked participant artifact: {source_name}")
        if not source.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Artifact escapes source checkout: {source_name}")
        if not eligible(entry, catalog["cutoff"]):
            raise ValueError(f"Artifact unavailable at case cutoff: {source_name}")
        if source.suffix in {".json", ".geojson"}:
            validate_temporal_tree(json.loads(source.read_text()), source_name, catalog["cutoff"])
        if source_name in dated_records:
            document = dated_records[source_name]
            if (
                entry["available_at"] != document["available_on"]
                or entry["effective_at"] != document["event_date"]
            ):
                raise ValueError(f"Catalog dates differ from controlled chronology: {source_name}")
    required = {"COMPANY_RECORD", "MODEL_SOURCE", "OPERATING_DATA", "FINANCIAL_DATA", "MAP"}
    if not required.issubset({entry.get("kind") for entry in entries}):
        raise ValueError("Participant corpus lacks a required evidence category")
    return sorted(entries, key=lambda entry: entry["path"])


def write_zip(stage: Path, destination: Path) -> None:
    """Normalize order, compression, permissions, timestamps and ZIP metadata."""
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(p for p in stage.rglob("*") if p.is_file()):
            name = path.relative_to(stage).as_posix()
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 5, 23, 59, 58))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(
                info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9
            )


def sql_name(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Unsafe SQL identifier: {value}")
    return f'"{value}"'


def tabular_database(stage: Path, entries: list[dict]) -> dict:
    """Combine the selected CSVs without collapsing their separate model scopes."""
    path = stage / "industrial_case.sqlite3"
    tables = []
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA page_size=4096")
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute(
            "CREATE TABLE artifact_lineage (table_name TEXT PRIMARY KEY, "
            "source_path TEXT NOT NULL, source_sha256 TEXT NOT NULL, "
            "available_at TEXT NOT NULL, effective_at TEXT NOT NULL, "
            "fact_state TEXT NOT NULL, temporal_mode TEXT NOT NULL)"
        )
        for entry in entries:
            if not entry["path"].endswith(".csv"):
                continue
            source = stage / entry["path"]
            with source.open(newline="", encoding="utf-8-sig") as stream:
                reader = csv.DictReader(stream)
                fields = reader.fieldnames
                rows = list(reader)
            if not fields or len(set(fields)) != len(fields):
                raise ValueError(f"Missing/duplicate CSV columns: {source}")
            if any(None in row or None in row.values() for row in rows):
                raise ValueError(f"Malformed CSV row: {source}")
            for row in rows:
                validate_temporal_tree(row, entry["path"])
            prefix = (
                "red_wash"
                if entry["path"].startswith("red_wash/")
                else ("finance" if "/finance/" in entry["path"] else "operations")
            )
            if "/source/" in entry["path"]:
                prefix += "_source"
            name = prefix + "__" + source.stem
            columns = []
            for field in fields:
                values = [row[field] for row in rows if row[field] != ""]
                field_type = "TEXT"
                if values and all(re.fullmatch(r"-?\d+", value) for value in values):
                    field_type = "INTEGER"
                elif values and all(re.fullmatch(r"-?\d+(?:\.\d+)?", value) for value in values):
                    field_type = "REAL"
                columns.append(f"{sql_name(field)} {field_type}")
            db.execute(f"CREATE TABLE {sql_name(name)} ({','.join(columns)})")
            placeholders = ",".join("?" for _ in fields)
            db.executemany(
                f"INSERT INTO {sql_name(name)} VALUES ({placeholders})",
                ([row[field] or None for field in fields] for row in rows),
            )
            db.execute(
                "INSERT INTO artifact_lineage VALUES (?,?,?,?,?,?,?)",
                (
                    name,
                    entry["path"],
                    digest(source),
                    entry["available_at"],
                    entry["effective_at"],
                    entry["fact_state"],
                    entry["temporal_mode"],
                ),
            )
            tables.append({"table": name, "rows": len(rows), "source": entry["path"]})
        db.commit()
        result = db.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise ValueError(result)
        db.execute("VACUUM")
    return {"path": path.name, "sha256": digest(path), "tables": tables}


def run_builders(root: Path = ROOT) -> None:
    for relative in (
        "red_wash/tools/validate_red_wash_record.py",
        "industrial/tools/build_operations.py",
        "industrial/tools/build_financials.py",
    ):
        args = [sys.executable, str(root / relative)]
        if relative.startswith("red_wash/"):
            args.append("--generate")
        result = subprocess.run(args, cwd=root, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f"Builder failed: {relative}\n{result.stdout}\n{result.stderr}")


def build(*, allow_working_tree: bool = False, skip_builders: bool = False) -> dict:
    if not skip_builders:
        run_builders()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(
        subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
    )
    if dirty and not allow_working_tree:
        raise ValueError(
            "Release requires a clean source commit; development builds need --allow-working-tree"
        )
    catalog = json.loads(CATALOG.read_text())
    entries = reviewed_entries(catalog)
    DIST.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sh-industrial-participant-") as temp:
        stage = Path(temp) / "corpus"
        stage.mkdir()
        copied = []
        for entry in entries:
            target = stage / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / entry["path"], target)
            copied.append({**entry, "sha256": digest(target), "bytes": target.stat().st_size})
        database = tabular_database(stage, entries)
        participant_intro = stage / "README.md"
        participant_intro.write_text(
            "# Sable Harbor industrial M&A participant case\n\n"
            "Pale Sun, Red Wash, American Resource Utility and Blood, Sweat & Tears Railway.\n\n"
            "Publication cutoff: September 5, 2026, 23:59:59 America/Los_Angeles. "
            "This is a complete selected synthetic case corpus. "
            "Begin with industrial/CASE_GUIDE.md. "
            "Each artifact's manifest records its effective date, company availability, "
            "origin and model state. Reconstructed evidence is synthetic. "
            "Future commitments, expansion options and forecasts are not completed results. "
            "The standalone mine and integrated successor have separate model scopes.\n\n"
            "The SQLite artifact_lineage table binds each dataset to its exact source "
            "and temporal metadata. The archive includes no private assessment material. "
            "Verify CHECKSUMS.sha256 before use.\n",
            encoding="utf-8",
        )
        manifest = {
            "package_id": "SH-INDUSTRIAL-MA-PARTICIPANT-001",
            "version": VERSION,
            "cutoff": CUTOFF,
            "classification": "PUBLIC_SYNTHETIC_PARTICIPANT_CORPUS",
            "source_revision": revision,
            "build_toolchain": {
                "python": sys.version.split()[0],
                "sqlite": sqlite3.sqlite_version,
                "zlib": zlib.ZLIB_RUNTIME_VERSION,
            },
            "source_state": "WORKING_TREE_DEVELOPMENT" if dirty else "CLEAN_COMMIT",
            "catalog_sha256": digest(CATALOG),
            "temporal_policy": (
                "Exact artifact availability; known forecasts/commitments remain labeled; "
                "unknown dates excluded."
            ),
            "editorial_handoff_included": False,
            "private_assessment_material_included": False,
            "artifacts": copied,
            "database": database,
            "readme_sha256": digest(participant_intro),
        }
        (stage / "manifest.json").write_bytes(encoded(manifest))
        files = sorted(path for path in stage.rglob("*") if path.is_file())
        checksum_text = "".join(
            f"{digest(path)}  {path.relative_to(stage).as_posix()}\n" for path in files
        )
        (stage / "CHECKSUMS.sha256").write_text(checksum_text)
        first = Path(temp) / "first.zip"
        second = Path(temp) / "second.zip"
        write_zip(stage, first)
        write_zip(stage, second)
        if first.read_bytes() != second.read_bytes():
            raise ValueError("ZIP rebuild changed bytes")
        with zipfile.ZipFile(first) as archive:
            if archive.testzip() is not None:
                raise ValueError("ZIP CRC check failed")
            for path in files:
                name = path.relative_to(stage).as_posix()
                if hashlib.sha256(archive.read(name)).hexdigest() != digest(path):
                    raise ValueError(f"ZIP member checksum mismatch: {name}")
        shutil.copyfile(first, DIST / ARCHIVE_NAME)
        (DIST / "participant_manifest.json").write_bytes(encoded(manifest))
        (DIST / "SHA256SUMS.txt").write_text(f"{digest(first)}  {ARCHIVE_NAME}\n")
        report = {
            "status": "PASS",
            "version": VERSION,
            "source_revision": revision,
            "source_state": manifest["source_state"],
            "cutoff": CUTOFF,
            "artifact_count": len(copied),
            "table_count": len(database["tables"]),
            "zip_path": str((DIST / ARCHIVE_NAME).relative_to(ROOT)),
            "zip_sha256": digest(first),
            "zip_bytes": first.stat().st_size,
            "zip_repeat_bytes_identical": True,
        }
        (DIST / "validation.json").write_bytes(encoded(report))
        return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-working-tree", action="store_true")
    parser.add_argument("--skip-builders", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            build(allow_working_tree=args.allow_working_tree, skip_builders=args.skip_builders),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
