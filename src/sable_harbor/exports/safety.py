from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
import sqlite3
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

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
NUMERIC_TEXT = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
FORBIDDEN_SEMANTIC_FIELD = re.compile(
    rb"(?:^|[^a-z0-9])(?:answer_key|ground_truth|hidden_truth|oracle_label|"
    rb"evaluator_label|expected_answer|gold_label|private_label)(?:$|[^a-z0-9])",
    re.IGNORECASE,
)
EMAIL_ADDRESS = re.compile(
    rb"(?:^|[^a-z0-9._%+-])[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}(?:$|[^a-z0-9.-])",
    re.IGNORECASE,
)
US_SSN = re.compile(rb"(?:^|\D)\d{3}-\d{2}-\d{4}(?:$|\D)")
PACKAGE_MARKER = ".sable-harbor-generated.json"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TECHNICAL_SAFETY_SCOPE = (
    "CREDENTIAL_MARKERS_WORKSTATION_PATHS_PII_SHAPES_HIDDEN-TRUTH-FIELD-NAMES_"
    "CSV_FORMULAS_ARCHIVE_OBJECTS_EXTERNAL_LINKS"
)


def spreadsheet_safe_value(value: Any) -> Any:
    """Neutralize untrusted spreadsheet formulas while retaining genuine numeric values."""
    if not isinstance(value, str) or not value:
        return value
    stripped = value.lstrip()
    if not stripped or value.startswith("'"):
        return value
    first = stripped[0]
    if first in "=@" or (first in "+-" and NUMERIC_TEXT.fullmatch(stripped) is None):
        return "'" + value
    return value


def _unsafe_spreadsheet_text(value: str) -> bool:
    return bool(spreadsheet_safe_value(value) != value)


def _package_marker(package_kind: str) -> str:
    return (
        json.dumps(
            {
                "format": "sable-harbor-generated-package/v1",
                "package_kind": package_kind,
            },
            sort_keys=True,
        )
        + "\n"
    )


def _validated_package_destination(
    destination: Path, *, package_kind: str, repository_output_root: Path
) -> Path:
    requested = destination.expanduser()
    if requested.is_symlink():
        raise ValueError(f"Package destination cannot be a symbolic link: {destination}")
    resolved = requested.resolve()
    repository = REPOSITORY_ROOT.resolve()
    current_directory = Path.cwd().resolve()
    home_directory = Path.home().resolve()
    filesystem_root = Path(resolved.anchor)
    protected = (filesystem_root, repository, current_directory, home_directory)
    if any(resolved == path or resolved in path.parents for path in protected):
        raise ValueError(f"Refusing broad or protected package destination: {destination}")

    allowed_root = repository_output_root.resolve()
    if repository in resolved.parents and allowed_root not in resolved.parents:
        raise ValueError(
            "Repository package destinations must be strict descendants of "
            f"{repository_output_root}"
        )
    if resolved.exists():
        if not resolved.is_dir():
            raise ValueError(f"Package destination exists and is not a directory: {destination}")
        marker = resolved / PACKAGE_MARKER
        within_governed_output = allowed_root in resolved.parents
        if not within_governed_output and any(resolved.iterdir()):
            expected = _package_marker(package_kind)
            if not marker.is_file() or marker.read_text() != expected:
                raise ValueError(
                    "Refusing to replace a nonempty or unowned external directory; "
                    f"expected a {PACKAGE_MARKER} marker for {package_kind!r}: {destination}"
                )
    return resolved


@contextmanager
def staged_package_directory(
    destination: Path, *, package_kind: str, repository_output_root: Path
) -> Iterator[tuple[Path, Path]]:
    """Build a governed package beside its target, then publish it atomically."""
    final_destination = _validated_package_destination(
        destination,
        package_kind=package_kind,
        repository_output_root=repository_output_root,
    )
    final_destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{final_destination.name}.staging-", dir=final_destination.parent)
    )
    (staging / PACKAGE_MARKER).write_text(_package_marker(package_kind))
    backup: Path | None = None
    try:
        yield final_destination, staging
        if final_destination.exists():
            backup = final_destination.parent / (
                f".{final_destination.name}.replaced-{uuid4().hex}"
            )
            os.replace(final_destination, backup)
        try:
            os.replace(staging, final_destination)
        except BaseException:
            if backup is not None and backup.exists() and not final_destination.exists():
                os.replace(backup, final_destination)
            raise
        if backup is not None:
            shutil.rmtree(backup)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _scan_bytes(data: bytes, label: str, failures: list[str]) -> None:
    lowered = data.lower()
    for marker in FORBIDDEN_BYTES:
        if marker.lower() in lowered:
            failures.append(f"forbidden marker {marker!r} in {label}")
    if FORBIDDEN_SEMANTIC_FIELD.search(data):
        failures.append(f"hidden-truth/evaluator field marker in {label}")
    if EMAIL_ADDRESS.search(data):
        failures.append(f"email-address-shaped value in {label}")
    if US_SSN.search(data):
        failures.append(f"US-SSN-shaped value in {label}")


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


def _scan_csv(path: Path, failures: list[str]) -> None:
    try:
        with path.open(newline="", encoding="utf-8") as source:
            for row_number, row in enumerate(csv.reader(source), start=1):
                for column_number, value in enumerate(row, start=1):
                    if _unsafe_spreadsheet_text(value):
                        failures.append(
                            "spreadsheet formula injection risk in "
                            f"{path}:{row_number}:{column_number}"
                        )
    except (UnicodeDecodeError, csv.Error) as error:
        failures.append(f"invalid CSV artifact {path}: {error}")


def scan_generated_artifacts(root: Path) -> list[str]:
    """Return concrete public-safety failures from generated package contents."""
    failures: list[str] = []
    paths = [root] if root.is_file() else sorted(item for item in root.rglob("*") if item.is_file())
    for path in paths:
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
        elif suffix == ".csv":
            _scan_csv(path, failures)
    return failures
