import csv
import hashlib
import json
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from sable_harbor.core.database import required_schema_head
from sable_harbor.exports.safety import scan_generated_artifacts
from sable_harbor.provenance.models import GenerationRun
from sable_harbor.provenance.service import run_context
from sable_harbor.workbooks.suite import generate_workbook_suite

PUBLIC_ALLOWLIST = Path("config/releases/public-demo-v0.1.json")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _export_csv(
    session: Session,
    table: str,
    selected_columns: list[str],
    destination: Path,
    generation_run_id: str,
    actual_run_id: str,
) -> int:
    if session.bind is None:
        raise ValueError("Export session is not bound to a database")
    columns = {column["name"] for column in inspect(session.bind).get_columns(table)}
    unknown = set(selected_columns) - columns
    if unknown:
        raise ValueError(f"Public allowlist has unknown columns for {table}: {sorted(unknown)}")
    projection = ",".join(f'"{column}"' for column in selected_columns)
    if "generation_run_id" in columns:
        statement = text(
            f'SELECT {projection} FROM "{table}" WHERE generation_run_id IN '
            "(:actual_run_id,:generation_run_id)"
        )
    elif table == "journal_line":
        qualified_projection = ",".join(
            f'jl."{column}"' for column in selected_columns
        )
        statement = text(
            f"SELECT {qualified_projection} "
            'FROM "journal_line" jl JOIN "journal_entry" je '
            "ON je.id=jl.entry_id WHERE je.generation_run_id IN "
            "(:actual_run_id,:generation_run_id)"
        )
    else:
        statement = text(f'SELECT {projection} FROM "{table}"')
    rows = session.execute(
        statement,
        {"generation_run_id": generation_run_id, "actual_run_id": actual_run_id},
    ).mappings().all()
    with destination.open("w", newline="", encoding="utf-8") as output:
        if not rows:
            output.write("")
            return 0
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(
            [
                {key: str(value) if value is not None else "" for key, value in row.items()}
                for row in rows
            ]
        )
    return len(rows)


def _allowlist() -> dict[str, list[str]]:
    document = json.loads(PUBLIC_ALLOWLIST.read_text())
    tables = document.get("tables")
    if not isinstance(tables, dict) or not tables:
        raise ValueError("Public release allowlist must define tables")
    return {str(table): [str(column) for column in columns] for table, columns in tables.items()}


def _sqlite_public_database(
    csv_directory: Path, destination: Path, allowlist: dict[str, list[str]]
) -> None:
    """Build a new empty database containing only explicitly allowlisted columns."""
    target = sqlite3.connect(destination)
    try:
        for table, columns in allowlist.items():
            declarations = ",".join(f'"{column}" TEXT' for column in columns)
            target.execute(f'CREATE TABLE "{table}" ({declarations})')
            with (csv_directory / f"{table}.csv").open(
                newline="", encoding="utf-8"
            ) as source:
                rows = csv.DictReader(source)
                if rows.fieldnames is None:
                    continue
                placeholders = ",".join("?" for _ in columns)
                target.executemany(
                    f'INSERT INTO "{table}" VALUES ({placeholders})',
                    ([row[column] for column in columns] for row in rows),
                )
        target.commit()
    finally:
        target.close()


def package_public_demo(
    session: Session,
    destination: Path = Path("releases/generated/public-demo-v0.1"),
    *,
    generation_run_id: str,
    generated_at: datetime | None = None,
) -> Path:
    context = run_context(session, generation_run_id)
    run = session.get(GenerationRun, context.generation_run_id)
    if run is None:
        raise ValueError(f"Unknown generation run {generation_run_id!r}")
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    csv_directory = destination / "csv"
    workbook_directory = destination / "workbooks"
    csv_directory.mkdir(exist_ok=True)
    allowlist = _allowlist()
    row_counts = {
        table: _export_csv(
            session,
            table,
            columns,
            csv_directory / f"{table}.csv",
            context.generation_run_id,
            context.included_run_ids[0],
        )
        for table, columns in allowlist.items()
    }
    _sqlite_public_database(
        csv_directory, destination / "sable_harbor_public_demo.sqlite", allowlist
    )
    generate_workbook_suite(
        session,
        workbook_directory,
        generation_run_id=context.generation_run_id,
    )
    usage = destination / "LICENSE_USAGE.md"
    usage.write_text(
        "# Sable Harbor public-demo usage\n\n"
        "Synthetic fictional data. All rights reserved. No open-source license is granted. "
        "No representation of audited or GAAP-compliant financial statements is made.\n"
    )
    limitations = destination / "KNOWN_LIMITATIONS.md"
    limitations.write_text(Path("docs/finance/KNOWN_LIMITATIONS.md").read_text())
    artifacts = sorted(
        path for path in destination.rglob("*") if path.is_file() and path.name != "manifest.json"
    )
    inventory: list[dict[str, Any]] = [
        {
            "path": str(path.relative_to(destination)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in artifacts
    ]
    manifest = {
        "package_name": "public-demo",
        "package_version": "0.1.0",
        "generation_run_id": context.generation_run_id,
        "included_run_ids": list(context.included_run_ids),
        "scenario": context.scenario_code,
        "profile": run.profile,
        "generation_seed": run.seed,
        "generator_version": "0.1.0",
        "git_commit": run.git_commit,
        "source_canon_branch": "origin/canon/corporate-lore-v0.2",
        "source_canon_commit": "5137c5abc025ad757a4e1af2a57279e4964578cf",
        "generated_timestamp": (
            generated_at or run.completed_at or datetime.now(UTC)
        ).astimezone(UTC).isoformat(),
        "period_covered": "2023-01 through 2026-12",
        "business_lines": [
            "Foundry Field",
            "Atlas",
            "Willow",
            "Pale Sun/Red Wash",
            "Cradle",
            "ARU/BS&T",
            "Advisory",
        ],
        "row_counts": row_counts,
        "schema_versions": [required_schema_head()],
        "checksum_algorithm": "SHA-256",
        "artifacts": inventory,
        "classification": "PUBLIC_SAFE_SYNTHETIC",
        "license": "All rights reserved; see LICENSE_USAGE.md",
        "known_limitations": "See KNOWN_LIMITATIONS.md",
        "compatibility": ["SQLite 3", "PostgreSQL schema via Alembic", "Excel OOXML"],
        "validation_status": "PENDING_ARTIFACT_SCAN",
    }
    manifest_path = destination / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    failures = scan_generated_artifacts(destination)
    if failures:
        raise ValueError("Generated-artifact safety scan failed:\n" + "\n".join(failures))
    manifest["validation_status"] = "PASS"
    manifest["artifact_safety_scan"] = {"status": "PASS", "failures": 0}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest_path
