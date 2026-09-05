import csv
import hashlib
import json
import re
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]
from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import FiscalPeriod, JournalEntry
from sable_harbor.accounting.validation import validate_financial_integrity
from sable_harbor.exports.metadata import (
    REPOSITORY_ROOT,
    file_sha256,
    generation_manifest_metadata,
    included_run_metadata,
    public_profile,
)
from sable_harbor.exports.safety import (
    TECHNICAL_SAFETY_SCOPE,
    scan_generated_artifacts,
    spreadsheet_safe_value,
    staged_package_directory,
)
from sable_harbor.provenance.models import GenerationRun
from sable_harbor.provenance.service import run_context
from sable_harbor.workbooks.suite import generate_workbook_suite

PUBLIC_ALLOWLIST = REPOSITORY_ROOT / "config/releases/public-demo-v0.1.json"
PUBLIC_MANIFEST_SCHEMA = REPOSITORY_ROOT / "releases/manifests/public-demo-v0.1.schema.json"
KNOWN_LIMITATIONS = REPOSITORY_ROOT / "docs/finance/KNOWN_LIMITATIONS.md"
SQL_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
RFC3339_DATE_TIME = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})$"
)
PUBLIC_FORMAT_CHECKER = FormatChecker()


@PUBLIC_FORMAT_CHECKER.checks("date", raises=ValueError)  # type: ignore[untyped-decorator]
def _is_iso_date(value: object) -> bool:
    if not isinstance(value, str):
        return True
    return date.fromisoformat(value).isoformat() == value


@PUBLIC_FORMAT_CHECKER.checks(  # type: ignore[untyped-decorator]
    "date-time", raises=ValueError
)
def _is_rfc3339_date_time(value: object) -> bool:
    if not isinstance(value, str):
        return True
    if RFC3339_DATE_TIME.fullmatch(value) is None:
        return False
    parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


SUPPORTED_PUBLIC_TABLES = {
    "legal_entity",
    "site",
    "accounting_book",
    "fiscal_period",
    "account",
    "journal_entry",
    "journal_line",
    "scenario_value",
    "worker",
    "production_record",
    "freight_movement",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_public_manifest(manifest: dict[str, Any]) -> None:
    """Validate release evidence with structural and temporal format enforcement."""
    schema_document = json.loads(PUBLIC_MANIFEST_SCHEMA.read_text())
    Draft202012Validator.check_schema(schema_document)
    Draft202012Validator(
        schema_document,
        format_checker=PUBLIC_FORMAT_CHECKER,
    ).validate(manifest)


def _export_csv(
    session: Session,
    table: str,
    selected_columns: list[str],
    destination: Path,
    generation_run_id: str,
    calibration_run_id: str,
) -> int:
    if session.bind is None:
        raise ValueError("Export session is not bound to a database")
    columns = {column["name"] for column in inspect(session.bind).get_columns(table)}
    unknown = set(selected_columns) - columns
    if unknown:
        raise ValueError(f"Public allowlist has unknown columns for {table}: {sorted(unknown)}")
    projection = ",".join(f'"{column}"' for column in selected_columns)
    primary_key = inspect(session.bind).get_pk_constraint(table).get("constrained_columns") or []
    order_columns = [str(column) for column in primary_key] or selected_columns
    order_by = ",".join(f'"{column}"' for column in order_columns)
    run_filter = "(:calibration_run_id,:generation_run_id)"
    if table == "legal_entity":
        qualified_projection = ",".join(f'le."{column}"' for column in selected_columns)
        statement = text(
            "WITH RECURSIVE relevant_entity(id) AS ("
            "SELECT ab.entity_id FROM accounting_book ab JOIN journal_entry je ON je.book_id=ab.id "
            f"WHERE je.generation_run_id IN {run_filter} UNION "
            "SELECT jl.counterparty_entity_id FROM journal_line jl "
            "JOIN journal_entry je ON je.id=jl.entry_id "
            f"WHERE je.generation_run_id IN {run_filter} "
            "AND jl.counterparty_entity_id IS NOT NULL UNION "
            f"SELECT entity_id FROM worker WHERE generation_run_id IN {run_filter} UNION "
            f"SELECT entity_id FROM freight_movement WHERE generation_run_id IN {run_filter} UNION "
            "SELECT le.parent_id FROM legal_entity le JOIN relevant_entity re ON le.id=re.id "
            "WHERE le.parent_id IS NOT NULL) "
            f"SELECT {qualified_projection} FROM legal_entity le "
            "WHERE le.id IN (SELECT id FROM relevant_entity) ORDER BY le.id"
        )
    elif table == "accounting_book":
        qualified_projection = ",".join(f'ab."{column}"' for column in selected_columns)
        statement = text(
            f"SELECT {qualified_projection} FROM accounting_book ab "
            "WHERE EXISTS (SELECT 1 FROM journal_entry je WHERE je.book_id=ab.id "
            f"AND je.generation_run_id IN {run_filter}) ORDER BY ab.id"
        )
    elif table == "fiscal_period":
        qualified_projection = ",".join(f'fp."{column}"' for column in selected_columns)
        statement = text(
            f"SELECT {qualified_projection} FROM fiscal_period fp "
            "WHERE EXISTS (SELECT 1 FROM journal_entry je WHERE je.period_id=fp.id "
            f"AND je.generation_run_id IN {run_filter}) ORDER BY fp.id"
        )
    elif table == "account":
        qualified_projection = ",".join(f'a."{column}"' for column in selected_columns)
        statement = text(
            f"SELECT {qualified_projection} FROM account a "
            "WHERE EXISTS (SELECT 1 FROM journal_line jl "
            "JOIN journal_entry je ON je.id=jl.entry_id WHERE jl.account_id=a.id "
            f"AND je.generation_run_id IN {run_filter}) ORDER BY a.id"
        )
    elif table == "site":
        qualified_projection = ",".join(f's."{column}"' for column in selected_columns)
        statement = text(
            f"SELECT {qualified_projection} FROM site s WHERE s.id IN ("
            f"SELECT site_id FROM worker WHERE generation_run_id IN {run_filter} "
            "AND site_id IS NOT NULL UNION "
            f"SELECT site_id FROM production_record WHERE generation_run_id IN {run_filter} UNION "
            f"SELECT site_id FROM fixed_asset WHERE generation_run_id IN {run_filter} "
            "AND site_id IS NOT NULL UNION "
            f"SELECT site_id FROM inventory_lot WHERE generation_run_id IN {run_filter} UNION "
            f"SELECT site_id FROM environmental_obligation WHERE generation_run_id IN {run_filter}"
            ") ORDER BY s.id"
        )
    elif "generation_run_id" in columns:
        statement = text(
            f'SELECT {projection} FROM "{table}" WHERE generation_run_id IN '
            f"{run_filter} ORDER BY {order_by}"
        )
    elif table == "journal_line":
        qualified_projection = ",".join(f'jl."{column}"' for column in selected_columns)
        statement = text(
            f"SELECT {qualified_projection} "
            'FROM "journal_line" jl JOIN "journal_entry" je '
            "ON je.id=jl.entry_id WHERE je.generation_run_id IN "
            f"{run_filter} ORDER BY " + ",".join(f'jl."{column}"' for column in order_columns)
        )
    else:
        raise ValueError(f"Public allowlist table {table!r} has no selected-run scope rule")
    rows = (
        session.execute(
            statement,
            {
                "generation_run_id": generation_run_id,
                "calibration_run_id": calibration_run_id,
            },
        )
        .mappings()
        .all()
    )
    with destination.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=selected_columns)
        writer.writeheader()
        if not rows:
            return 0
        writer.writerows(
            [
                {
                    key: spreadsheet_safe_value(str(value)) if value is not None else ""
                    for key, value in row.items()
                }
                for row in rows
            ]
        )
    return len(rows)


def _allowlist() -> dict[str, list[str]]:
    document = json.loads(PUBLIC_ALLOWLIST.read_text())
    if not isinstance(document, dict) or document.get("version") != "0.1.0":
        raise ValueError("Public release allowlist must use version '0.1.0'")
    tables = document.get("tables")
    if not isinstance(tables, dict) or not tables:
        raise ValueError("Public release allowlist must define tables")
    validated: dict[str, list[str]] = {}
    for table, columns in tables.items():
        if not isinstance(table, str) or SQL_IDENTIFIER.fullmatch(table) is None:
            raise ValueError(f"Public allowlist has unsafe table identifier: {table!r}")
        if not isinstance(columns, list) or not columns:
            raise ValueError(f"Public allowlist table {table!r} requires a nonempty column list")
        if any(
            not isinstance(column, str) or SQL_IDENTIFIER.fullmatch(column) is None
            for column in columns
        ):
            raise ValueError(f"Public allowlist table {table!r} has an unsafe column identifier")
        if len(columns) != len(set(columns)):
            raise ValueError(f"Public allowlist table {table!r} has duplicate columns")
        validated[table] = columns
    if set(validated) != SUPPORTED_PUBLIC_TABLES:
        raise ValueError("Public release allowlist must define exactly the supported public tables")
    return validated


def _sqlite_public_database(
    csv_directory: Path, destination: Path, allowlist: dict[str, list[str]]
) -> None:
    """Build a new empty database containing only explicitly allowlisted columns."""
    target = sqlite3.connect(destination)
    try:
        for table, columns in allowlist.items():
            declarations = ",".join(f'"{column}" TEXT' for column in columns)
            target.execute(f'CREATE TABLE "{table}" ({declarations})')
            with (csv_directory / f"{table}.csv").open(newline="", encoding="utf-8") as source:
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


def _build_public_demo_package(
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
    if run.profile != "standard":
        raise ValueError("The public demo contract requires the standard profile")
    if (
        len(context.included_run_ids) != 2
        or run.shared_synthetic_calibration_run_id != context.included_run_ids[0]
    ):
        raise ValueError(
            "The public demo contract requires one selected standard run and its governed "
            "shared synthetic calibration run"
        )
    validation = validate_financial_integrity(session, generation_run_id)
    period_start, period_end = session.execute(
        select(func.min(FiscalPeriod.code), func.max(FiscalPeriod.code))
        .join(JournalEntry, JournalEntry.period_id == FiscalPeriod.id)
        .where(
            JournalEntry.state == "POSTED",
            JournalEntry.generation_run_id.in_(context.included_run_ids),
        )
    ).one()
    if period_start is None or period_end is None:
        raise ValueError("Public release requires a nonempty reporting period")
    included_runs = [
        item
        for run_id in context.included_run_ids
        if (item := session.get(GenerationRun, run_id)) is not None
    ]
    if len(included_runs) != len(context.included_run_ids):
        raise ValueError("Public release context contains an unknown generation run")
    controlled_timestamp = generated_at or run.completed_at or datetime.now(UTC)
    generation_metadata = generation_manifest_metadata(
        run,
        scenario_code=context.scenario_code,
        built_at=controlled_timestamp,
        effective_from=str(period_start),
        effective_through=str(period_end),
        effective_period_basis="posted_fiscal_period_codes",
    )
    destination.mkdir(parents=True, exist_ok=True)
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
        generated_at=controlled_timestamp,
    )
    usage = destination / "LICENSE_USAGE.md"
    usage.write_text(
        "# Sable Harbor public-demo usage\n\n"
        "Synthetic fictional data. All rights reserved. No open-source license is granted. "
        "No representation of audited or GAAP-compliant financial statements is made.\n"
    )
    limitations = destination / "KNOWN_LIMITATIONS.md"
    limitations.write_text(KNOWN_LIMITATIONS.read_text())
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
        "included_runs": included_run_metadata(
            included_runs, selected_run_id=context.generation_run_id
        ),
        "profile": public_profile(run.profile),
        "seed": run.seed,
        "source_commit": run.git_commit,
        "period_covered": f"{period_start} through {period_end}",
        "calibration_classification": "SHARED_SYNTHETIC_CALIBRATION_REFERENCE",
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
        "schema_versions": [run.schema_head],
        "checksum_algorithm": "SHA-256",
        "package_input_digests": {
            "public_allowlist_sha256": file_sha256(PUBLIC_ALLOWLIST),
            "public_manifest_schema_sha256": file_sha256(PUBLIC_MANIFEST_SCHEMA),
            "known_limitations_sha256": file_sha256(KNOWN_LIMITATIONS),
        },
        "artifacts": inventory,
        "output_hashes": {artifact["path"]: artifact["sha256"] for artifact in inventory},
        "classification": "PUBLIC_SAFE_SYNTHETIC",
        "database_artifact_type": "ALLOWLISTED_EVIDENCE_EXTRACT_NOT_SOURCE_SCHEMA",
        "license": "All rights reserved; see LICENSE_USAGE.md",
        "known_limitations": "See KNOWN_LIMITATIONS.md",
        "compatibility": ["SQLite 3", "PostgreSQL schema via Alembic", "Excel OOXML"],
        "financial_validation": validation.as_dict(),
        "validation_status": "PENDING_ARTIFACT_SCAN",
        **generation_metadata,
    }
    manifest_path = destination / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    failures = scan_generated_artifacts(destination)
    if failures:
        raise ValueError("Generated-artifact safety scan failed:\n" + "\n".join(failures))
    manifest["validation_status"] = "PASS"
    manifest["artifact_safety_scan"] = {
        "status": "PASS",
        "failures": 0,
        "scope": TECHNICAL_SAFETY_SCOPE,
    }
    validate_public_manifest(manifest)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    final_failures = scan_generated_artifacts(destination)
    if final_failures:
        raise ValueError(
            "Final generated-artifact safety scan failed:\n" + "\n".join(final_failures)
        )
    checksum_paths = sorted(
        path for path in destination.rglob("*") if path.is_file() and path.name != "SHA256SUMS.txt"
    )
    (destination / "SHA256SUMS.txt").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(destination)}\n" for path in checksum_paths)
    )
    checksum_failures = scan_generated_artifacts(destination / "SHA256SUMS.txt")
    if checksum_failures:
        raise ValueError("Release checksum safety scan failed:\n" + "\n".join(checksum_failures))
    return manifest_path


def package_public_demo(
    session: Session,
    destination: Path = Path("releases/generated/public-demo-v0.1"),
    *,
    generation_run_id: str,
    generated_at: datetime | None = None,
) -> Path:
    with staged_package_directory(
        destination,
        package_kind="public-demo-v0.1",
        repository_output_root=REPOSITORY_ROOT / "releases/generated",
    ) as (final_destination, staging):
        staged_manifest = _build_public_demo_package(
            session,
            staging,
            generation_run_id=generation_run_id,
            generated_at=generated_at,
        )
        relative_manifest = staged_manifest.relative_to(staging)
    return final_destination / relative_manifest
