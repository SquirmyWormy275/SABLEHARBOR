from __future__ import annotations

import io
import re
import sqlite3
import zipfile
from pathlib import Path

FORBIDDEN_BYTES = (
    b"ghp_",
    b"github_pat_",
    b"sk-proj-",
    b"BEGIN PRIVATE KEY",
    b"/home/",
    b"\\Users\\",
)
FORBIDDEN_ARCHIVE_MEMBERS = (
    "vbaproject.bin",
    "embeddings/",
    "activex/",
    "oleobject",
)
EXTERNAL_RELATIONSHIP = re.compile(rb"TargetMode=[\"']External[\"']", re.IGNORECASE)


def _scan_bytes(data: bytes, label: str, failures: list[str]) -> None:
    lowered = data.lower()
    for marker in FORBIDDEN_BYTES:
        if marker.lower() in lowered:
            failures.append(f"forbidden marker {marker!r} in {label}")


def _scan_zip(data: bytes, label: str, failures: list[str], depth: int = 0) -> None:
    if depth > 4:
        failures.append(f"nested archive depth exceeded in {label}")
        return
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for info in archive.infolist():
            member = info.filename.lower()
            if any(marker in member for marker in FORBIDDEN_ARCHIVE_MEMBERS):
                failures.append(f"unexpected executable/embedded object {info.filename} in {label}")
            payload = archive.read(info)
            _scan_bytes(payload, f"{label}!{info.filename}", failures)
            if member.endswith(".rels") and EXTERNAL_RELATIONSHIP.search(payload):
                failures.append(f"external relationship in {label}!{info.filename}")
            if member.endswith((".zip", ".xlsx", ".xlsm")):
                _scan_zip(payload, f"{label}!{info.filename}", failures, depth + 1)


def _scan_sqlite(path: Path, failures: list[str]) -> None:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        objects = connection.execute(
            "SELECT name, sql FROM sqlite_master WHERE type IN ('table','view','trigger')"
        ).fetchall()
        for name, sql in objects:
            _scan_bytes(str(sql or "").encode(), f"{path}:{name}:schema", failures)
        for (table,) in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ):
            columns = connection.execute(f'PRAGMA table_info("{table}")').fetchall()
            textual = [
                column[1]
                for column in columns
                if "CHAR" in column[2].upper() or "TEXT" in column[2].upper()
            ]
            for column in textual:
                for (value,) in connection.execute(
                    f'SELECT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL'
                ):
                    _scan_bytes(str(value).encode(), f"{path}:{table}.{column}", failures)
    finally:
        connection.close()


def scan_generated_artifacts(root: Path) -> list[str]:
    """Return concrete public-safety failures from generated package contents."""
    failures: list[str] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        data = path.read_bytes()
        _scan_bytes(data, str(path), failures)
        suffix = path.suffix.lower()
        if suffix in {".zip", ".xlsx", ".xlsm"}:
            try:
                _scan_zip(data, str(path), failures)
            except zipfile.BadZipFile:
                failures.append(f"invalid archive: {path}")
        elif suffix in {".sqlite", ".db", ".sqlite3"}:
            try:
                _scan_sqlite(path, failures)
            except sqlite3.DatabaseError as error:
                failures.append(f"invalid SQLite artifact {path}: {error}")
    return failures
