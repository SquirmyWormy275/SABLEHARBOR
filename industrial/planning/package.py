#!/usr/bin/env python3
"""Assemble only reviewed v2 artifacts; preserve exact CSV evidence in all exports."""

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
import xml.etree.ElementTree as ET
import zipfile
import zlib
from datetime import datetime
from pathlib import Path

from industrial.tools import build_package as legacy

from . import browser, integrity

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "industrial/planning/source/participant_catalog.json"
DIST = ROOT / "industrial/dist/v2.0.0"
VERSION = "2.0.0"
CUTOFF = "2026-09-06T23:59:59-07:00"
ARCHIVE_NAME = f"sable-harbor-industrial-participant-v{VERSION}.zip"
DATABASE_NAME = "industrial_planning_case.sqlite3"
WORKBOOK_NAME = "industrial_planning_review.xlsx"
RESERVED = {
    "README.md",
    "manifest.json",
    "CHECKSUMS.sha256",
    "case_browser.html",
    "case_data.js",
    "dataset_index.json",
    DATABASE_NAME,
    WORKBOOK_NAME,
}
RAW_DATABASE_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".db3", ".sql"}


def read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        fields = next(reader, [])
        rows = list(reader)
    if not fields or len(set(fields)) != len(fields) or any(not field for field in fields):
        raise ValueError(f"Missing or duplicate CSV columns: {path}")
    for field in fields:
        legacy.sql_name(field)
    if any(len(row) != len(fields) for row in rows):
        raise ValueError(f"Malformed CSV row: {path}")
    return fields, rows


def reviewed_entries(catalog: dict, root: Path = ROOT) -> list[dict]:
    if catalog.get("version") != VERSION or catalog.get("cutoff") != CUTOFF:
        raise ValueError("Unsupported planning catalog version or cutoff")
    entries = catalog.get("artifacts", [])
    if not entries:
        raise ValueError("An empty allowlist is not a participant corpus")
    preservation_file = root / "industrial/planning/source/preservation.json"
    preserved = {
        item["path"]: item["sha256"]
        for item in json.loads(preservation_file.read_text())["artifacts"]
    }
    old_catalog_file = root / "industrial/source/participant_catalog.json"
    old_metadata = {
        item["path"]: item for item in json.loads(old_catalog_file.read_text())["artifacts"]
    }
    paths = set()
    for entry in entries:
        name = entry["path"]
        safe = legacy.member_path(name)
        if name != safe.as_posix() or name in RESERVED or name in paths:
            raise ValueError(f"Duplicate, noncanonical or reserved participant path: {name}")
        paths.add(name)
        source = root / name
        if source.suffix.lower() in RAW_DATABASE_SUFFIXES:
            raise ValueError(f"Raw database or SQL is not a selected participant export: {name}")
        if any(part.startswith(".") for part in safe.parts):
            raise ValueError(f"Hidden participant source is forbidden: {name}")
        if any(
            word in str(entry.get("kind", "")).lower()
            for word in ("private", "answer", "evaluator")
        ):
            raise ValueError(f"Nonparticipant classification: {name}")
        if not source.is_file() or not source.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Missing or escaping participant source: {name}")
        if any((root / Path(*safe.parts[:i])).is_symlink() for i in range(1, len(safe.parts) + 1)):
            raise ValueError(f"Linked participant source: {name}")
        if not legacy.eligible(entry, CUTOFF):
            raise ValueError(f"Artifact unavailable at planning cutoff: {name}")
        if name in preserved:
            if legacy.digest(source) != preserved[name] or entry != old_metadata.get(name):
                raise ValueError(f"Accepted v1 bytes or metadata changed: {name}")
        elif legacy.instant(entry["available_at"]) < legacy.instant("2026-09-06T00:00:00-07:00"):
            raise ValueError(f"New planning artifact backdated into v1: {name}")
        if entry.get("sha256") and entry["sha256"] != legacy.digest(source):
            raise ValueError(f"Catalog source hash mismatch: {name}")
        values = []
        if source.suffix.lower() in {".json", ".geojson"}:
            values = [json.loads(source.read_text())]
        elif source.suffix.lower() == ".csv":
            fields, rows = read_csv(source)
            values = [dict(zip(fields, row, strict=True)) for row in rows]
        for value in values:
            if name in preserved:
                legacy.validate_temporal_tree(value, name)
            else:
                integrity.temporal(value, inherited={"period_role": "FORECAST"})
    missing = set(preserved) - paths
    if missing:
        raise ValueError(f"Planning catalog omitted accepted v1 members: {sorted(missing)}")
    return sorted(entries, key=lambda entry: entry["path"])


def table_name(path: str) -> str:
    stem = re.sub(r"[^a-zA-Z0-9_]", "_", Path(path).stem)[:65]
    suffix = hashlib.sha256(path.encode()).hexdigest()[:12]
    return f"csv__{stem}__{suffix}"


def tabular_database(stage: Path, entries: list[dict]) -> dict:
    """Every cell remains TEXT, including empty strings and four-decimal USD."""
    destination = stage / DATABASE_NAME
    destination.unlink(missing_ok=True)
    tables = []
    with sqlite3.connect(destination) as database:
        database.execute("PRAGMA page_size=4096")
        database.execute("PRAGMA journal_mode=DELETE")
        database.execute(
            "CREATE TABLE artifact_lineage (table_name TEXT PRIMARY KEY, "
            "source_path TEXT NOT NULL, "
            "source_sha256 TEXT NOT NULL, available_at TEXT NOT NULL, effective_at TEXT NOT NULL, "
            "fact_state TEXT NOT NULL, temporal_mode TEXT NOT NULL, row_count TEXT NOT NULL, "
            "storage_policy TEXT NOT NULL)"
        )
        for entry in entries:
            if not entry["path"].endswith(".csv"):
                continue
            source = stage / entry["path"]
            fields, rows = read_csv(source)
            name = table_name(entry["path"])
            columns = ",".join(f"{legacy.sql_name(field)} TEXT NOT NULL" for field in fields)
            database.execute(f"CREATE TABLE {legacy.sql_name(name)} ({columns})")
            database.executemany(
                f"INSERT INTO {legacy.sql_name(name)} VALUES ({','.join('?' for _ in fields)})",
                rows,
            )
            source_hash = legacy.digest(source)
            database.execute(
                "INSERT INTO artifact_lineage VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    name,
                    entry["path"],
                    source_hash,
                    entry["available_at"],
                    entry["effective_at"],
                    entry["fact_state"],
                    entry["temporal_mode"],
                    str(len(rows)),
                    "EXACT_CSV_TEXT_NO_FLOAT_OR_NULL_COERCION",
                ),
            )
            actual = database.execute(
                f"SELECT * FROM {legacy.sql_name(name)} ORDER BY rowid"
            ).fetchall()
            if [list(row) for row in actual] != rows:
                raise ValueError(f"SQLite exact cell readback failed: {entry['path']}")
            types = database.execute(f"PRAGMA table_info({legacy.sql_name(name)})").fetchall()
            if any(column[2] != "TEXT" for column in types):
                raise ValueError("Numeric affinity would destroy exact CSV evidence")
            tables.append(
                {
                    "table": name,
                    "rows": len(rows),
                    "columns": fields,
                    "source": entry["path"],
                    "source_sha256": source_hash,
                }
            )
        database.commit()
        if database.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity check failed")
        database.execute("VACUUM")
    return {
        "path": DATABASE_NAME,
        "sha256": legacy.digest(destination),
        "tables": tables,
        "all_cells_exact_text": True,
        "csv_readback_verified": True,
    }


def workbook_candidates(entries: list[dict]) -> list[dict]:
    terms = ("monthly", "trial_balance", "funding", "capital", "cashflow")
    return [
        entry
        for entry in entries
        if entry["path"].endswith(".csv")
        and any(term in Path(entry["path"]).stem.lower() for term in terms)
    ]


def verify_workbook(path: Path, expected: dict[str, tuple[list[str], list[list[str]]]]) -> None:
    """Read OOXML directly; require string cells and compare every selected cell."""
    namespace = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("Workbook CRC failed")
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = ["".join(node.itertext()) for node in root]
        for index, (name, (fields, rows)) in enumerate(expected.items(), start=1):
            sheet = ET.fromstring(archive.read(f"xl/worksheets/sheet{index}.xml"))
            actual_rows = []
            for row in sheet.findall("s:sheetData/s:row", namespace):
                values = [""] * len(fields)
                for cell in row.findall("s:c", namespace):
                    column = re.match(r"[A-Z]+", cell.attrib["r"])[0]
                    column_index = 0
                    for letter in column:
                        column_index = column_index * 26 + ord(letter) - ord("A") + 1
                    if cell.find("s:f", namespace) is not None:
                        raise ValueError("A workbook evidence cell became a formula")
                    if cell.attrib.get("t") == "inlineStr":
                        value = "".join(cell.find("s:is", namespace).itertext())
                    elif cell.attrib.get("t") == "s":
                        value = strings[int(cell.find("s:v", namespace).text)]
                    else:
                        raise ValueError("Workbook evidence cell lost exact text storage")
                    values[column_index - 1] = value
                actual_rows.append(values)
            if actual_rows != [fields, *rows]:
                raise ValueError(f"Workbook exact cell readback failed: {name}")


def workbook(stage: Path, entries: list[dict]) -> dict:
    import xlsxwriter

    chosen = workbook_candidates(entries)
    if not chosen:
        raise ValueError("No reviewed monthly, trial balance, funding or capital CSVs selected")
    expected = {}
    index_fields = [
        "sheet",
        "source_path",
        "source_sha256",
        "rows",
        "available_at",
        "fact_state",
        "storage_policy",
    ]
    index_rows = []
    tables = []
    for entry in chosen:
        fields, rows = read_csv(stage / entry["path"])
        suffix = hashlib.sha256(entry["path"].encode()).hexdigest()[:8]
        name = re.sub(r"[^a-zA-Z0-9_]", "_", Path(entry["path"]).stem)[:21] + "_" + suffix
        if len(rows) + 1 > 1048576 or len(fields) > 16384:
            raise ValueError(f"Workbook capacity exceeded: {entry['path']}")
        expected[name] = fields, rows
        index_rows.append(
            [
                name,
                entry["path"],
                legacy.digest(stage / entry["path"]),
                str(len(rows)),
                entry["available_at"],
                entry["fact_state"],
                "EXACT_CSV_TEXT",
            ]
        )
        tables.append({"sheet": name, "source": entry["path"], "rows": len(rows)})
    expected = {"Source_Index": (index_fields, index_rows), **expected}
    path = stage / WORKBOOK_NAME
    with xlsxwriter.Workbook(path, {"constant_memory": True, "strings_to_urls": False}) as book:
        book.set_properties(
            {
                "title": "Sable Harbor conditional planning review",
                "created": datetime(2026, 9, 6),
                "author": "Sable Harbor synthetic case",
                "comments": "All evidence cells are exact text; no floating-point rounding.",
            }
        )
        header = book.add_format({"bold": True, "bg_color": "#DCE5E7", "text_wrap": True})
        exact = book.add_format({"num_format": "@"})
        for name, (fields, rows) in expected.items():
            sheet = book.add_worksheet(name)
            sheet.freeze_panes(1, 0)
            sheet.set_column(0, len(fields) - 1, 20)
            for row_index, values in enumerate([fields, *rows]):
                for column_index, value in enumerate(values):
                    if len(value) > 32767:
                        raise ValueError(f"Excel cell length would truncate evidence: {name}")
                    result = sheet.write_string(
                        row_index, column_index, value, header if row_index == 0 else exact
                    )
                    if result != 0:
                        raise ValueError(f"Excel rejected evidence cell: {name}")
            sheet.autofilter(0, 0, len(rows), len(fields) - 1)
    verify_workbook(path, expected)
    return {
        "path": WORKBOOK_NAME,
        "sha256": legacy.digest(path),
        "tables": tables,
        "xlsxwriter": xlsxwriter.__version__,
        "all_evidence_cells_exact_text": True,
        "ooxml_readback_verified": True,
    }


def validate_archive(archive_path: Path, stage: Path) -> None:
    expected = {
        p.relative_to(stage).as_posix(): legacy.digest(p) for p in stage.rglob("*") if p.is_file()
    }
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if names != sorted(expected) or len(names) != len(set(names)):
            raise ValueError("ZIP member population or order differs from staged inventory")
        if archive.testzip() is not None:
            raise ValueError("ZIP CRC check failed")
        for name in names:
            legacy.member_path(name)
            if hashlib.sha256(archive.read(name)).hexdigest() != expected[name]:
                raise ValueError(f"ZIP member hash mismatch: {name}")
        checksums = {}
        for line in archive.read("CHECKSUMS.sha256").decode().splitlines():
            digest, name = line.split("  ", 1)
            checksums[name] = digest
        if checksums != {
            name: value for name, value in expected.items() if name != "CHECKSUMS.sha256"
        }:
            raise ValueError("Checksum inventory omits or changes an archive member")


def build(*, allow_working_tree: bool = False) -> dict:
    """Build only from existing generated exports; never rerun source builders."""
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(
        subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
    )
    if dirty and not allow_working_tree:
        raise ValueError(
            "Release requires a clean source commit; use --allow-working-tree for development"
        )
    count = integrity.preservation(ROOT)
    if count != 199:
        raise ValueError("Accepted v1 preservation inventory must contain exactly 199 members")
    acceptance = integrity.verify_acceptance_binding(
        ROOT / "industrial/generated/planning", root=ROOT
    )
    catalog = json.loads(CATALOG.read_text())
    entries = reviewed_entries(catalog, ROOT)
    state = "WORKING_TREE_DEVELOPMENT" if dirty else "CLEAN_COMMIT"
    DIST.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sable-planning-package-") as directory:
        temp = Path(directory)
        stage = temp / "corpus"
        stage.mkdir()
        copied = []
        for entry in entries:
            target = stage / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / entry["path"], target)
            copied.append(
                {**entry, "sha256": legacy.digest(target), "bytes": target.stat().st_size}
            )
        database = tabular_database(stage, copied)
        spreadsheet = workbook(stage, copied)
        browser_result = browser.build(stage, copied, revision, state)
        (stage / "dataset_index.json").write_bytes(
            legacy.encoded(
                {
                    "database": database,
                    "workbook": spreadsheet,
                    "browser": browser_result,
                    "policy": (
                        "SQLite and workbook retain exact CSV cell text; "
                        "cast deliberately for analysis."
                    ),
                }
            )
        )
        (stage / "README.md").write_text(
            "# Sable Harbor industrial planning participant case — v2.0.0\n\n"
            "Unzip this full selected corpus, then open case_browser.html locally. "
            "Begin reading industrial/planning/README.md for scope and model commands.\n\n"
            "Publication cutoff: September 6, 2026, America/Los_Angeles. The accepted v1 "
            "199-member corpus remains byte-identical. The accepted December 2026 opening "
            "is a reference forecast; 2027–2031 operations, funding and transaction evidence "
            "are conditional synthetic scenarios, not completed results or authority grants.\n\n"
            "The SQLite artifact_lineage table and workbook Source_Index bind every table "
            "to its selected CSV and dates. All database/workbook evidence cells are TEXT, "
            "preserving decimal precision, empty strings and identifiers. Deliberately cast "
            "amounts in a separate analysis; no rounding is hidden in this export. "
            "dataset_index.json lists tables and sheets. Verify CHECKSUMS.sha256 before use.\n"
        )
        builder_paths = [
            Path(__file__),
            Path(browser.__file__),
            Path(integrity.__file__),
            Path(legacy.__file__),
            browser.TEMPLATE,
            ROOT / "uv.lock",
            ROOT / "industrial/planning/source/preservation.json",
        ]
        derived = [
            DATABASE_NAME,
            WORKBOOK_NAME,
            "case_browser.html",
            "case_data.js",
            "dataset_index.json",
            "README.md",
        ]
        manifest = {
            "package_id": "SH-INDUSTRIAL-PLANNING-PARTICIPANT-002",
            "version": VERSION,
            "cutoff": CUTOFF,
            "classification": "PUBLIC_SYNTHETIC_PARTICIPANT_CORPUS",
            "source_revision": revision,
            "source_state": state,
            "catalog_sha256": legacy.digest(CATALOG),
            "preserved_v1_artifacts": count,
            "independent_acceptance_verified": acceptance.get(
                "status", acceptance.get("passed", True)
            ),
            "build_toolchain": {
                "python": sys.version.split()[0],
                "sqlite": sqlite3.sqlite_version,
                "zlib": zlib.ZLIB_RUNTIME_VERSION,
                "xlsxwriter": spreadsheet["xlsxwriter"],
            },
            "builder_source_sha256": {
                str(p.relative_to(ROOT)): legacy.digest(p) for p in builder_paths
            },
            "archive_timestamp_policy": (
                "Inherited fixed ZIP container timestamp; "
                "content dates are solely manifest metadata."
            ),
            "private_assessment_material_included": False,
            "raw_database_included": False,
            "artifacts": copied,
            "database": database,
            "workbook": spreadsheet,
            "browser": browser_result,
            "derived_artifacts": [
                {
                    "path": name,
                    "sha256": legacy.digest(stage / name),
                    "bytes": (stage / name).stat().st_size,
                }
                for name in derived
            ],
        }
        (stage / "manifest.json").write_bytes(legacy.encoded(manifest))
        files = sorted(p for p in stage.rglob("*") if p.is_file())
        (stage / "CHECKSUMS.sha256").write_text(
            "".join(
                f"{legacy.digest(path)}  {path.relative_to(stage).as_posix()}\n" for path in files
            )
        )
        first, second = temp / "first.zip", temp / "second.zip"
        legacy.write_zip(stage, first)
        legacy.write_zip(stage, second)
        if first.read_bytes() != second.read_bytes():
            raise ValueError("Repeated ZIP generation changed bytes")
        validate_archive(first, stage)
        release_files = [
            (first, ARCHIVE_NAME),
            (stage / DATABASE_NAME, DATABASE_NAME),
            (stage / WORKBOOK_NAME, WORKBOOK_NAME),
            (stage / "manifest.json", "participant_manifest.json"),
        ]
        assets = []
        for source, name in release_files:
            shutil.copyfile(source, DIST / name)
            assets.append(
                {
                    "path": str((DIST / name).relative_to(ROOT)),
                    "sha256": legacy.digest(source),
                    "bytes": source.stat().st_size,
                }
            )
        report = {
            "status": "PASS",
            "version": VERSION,
            "cutoff": CUTOFF,
            "source_revision": revision,
            "source_state": state,
            "artifact_count": len(copied),
            "preserved_v1_artifacts": count,
            "independent_acceptance_verified": acceptance.get(
                "status", acceptance.get("passed", True)
            ),
            "table_count": len(database["tables"]),
            "workbook_table_count": len(spreadsheet["tables"]),
            "zip_path": str((DIST / ARCHIVE_NAME).relative_to(ROOT)),
            "zip_sha256": legacy.digest(first),
            "zip_bytes": first.stat().st_size,
            "zip_repeat_bytes_identical": True,
            "zip_crc_and_all_members_verified": True,
            "csv_database_cells_exact": True,
            "csv_workbook_cells_exact": True,
            "browser": browser_result,
            "release_assets": assets,
        }
        (DIST / "validation.json").write_bytes(legacy.encoded(report))
        names = [name for _, name in release_files] + ["validation.json"]
        (DIST / "SHA256SUMS.txt").write_text(
            "".join(f"{legacy.digest(DIST / name)}  {name}\n" for name in sorted(names))
        )
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-working-tree", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(allow_working_tree=args.allow_working_tree), indent=2))
