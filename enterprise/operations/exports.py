"""Fail-closed, scoped CSV and SQLite reporting distributions."""

import csv
import hashlib
import json
import re
import sqlite3
from pathlib import Path

from enterprise.business.exports import UNITS, encoded, file_hash, physical_registers
from sable_harbor.exports.safety import spreadsheet_safe_value

SCHEMA = Path(__file__).with_name("export_schema.json")
SCOPE = Path(__file__).with_name("export_scope.json")
SCOPE_FIELDS = (
    "unit",
    "reporting_unit",
    "home_unit",
    "entity",
    "scenario",
    "fact_state",
    "record_origin",
    "scope",
    "segment",
    "site",
)
ROUTING_FIELDS = ("unit", "reporting_unit", "home_unit", "entity")


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def columns(rows):
    return sorted({key for row in rows for key in row}) or ["scope_state"]


def csv_table(path, rows, fields=None):
    fields = fields or columns(rows)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(
            {key: spreadsheet_safe_value(encoded(row.get(key))) for key in fields} for row in rows
        )


def validate_schema(tables, schema, scope=None):
    if set(tables) != set(schema):
        raise ValueError(f"Export table schema changed: {set(tables) ^ set(schema)}")
    if scope is not None and set(scope) != set(tables):
        raise ValueError("Export scope table population changed")
    for name, rows in tables.items():
        extra = set(columns(rows)) - set(schema[name]) if rows else set()
        if extra:
            raise ValueError(f"Unapproved columns in {name}: {sorted(extra)}")
        for row in rows:
            if row.get("scenario") not in (None, "", "base", "downside", "expansion"):
                raise ValueError(f"Unexpected scenario in {name}")
            if scope is not None:
                rule = scope[name]
                for key, allowed in rule["allowed_values"].items():
                    if encoded(row.get(key)) not in allowed:
                        raise ValueError(f"Unapproved row scope: {name}/{key}")
                route = [encoded(row.get(k)) for k in rule["routing_fields"]]
                if route not in rule["allowed_routes"]:
                    raise ValueError(f"Invalid unit/entity routing: {name}")


def proposed_scope(tables):
    """Review-only proposal; release acceptance never learns permissions from output."""
    result = {}
    for name, rows in sorted(tables.items()):
        keys = set(columns(rows))
        routing = [k for k in ROUTING_FIELDS if k in keys]
        result[name] = {
            "allowed_values": {
                k: sorted({encoded(r.get(k)) for r in rows}) for k in SCOPE_FIELDS if k in keys
            },
            "routing_fields": routing,
            "allowed_routes": sorted({tuple(encoded(r.get(k)) for k in routing) for r in rows}),
        }
    return result


def database(path, tables, schema):
    if Path(path).exists():
        raise ValueError("Export database target must be new")
    with sqlite3.connect(path) as db:
        for name in sorted(tables):
            fields = schema[name]
            if not all(re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", k) for k in [name, *fields]):
                raise ValueError("Unsafe export identifier")
            definition = ", ".join(f'"{k}" TEXT NOT NULL' for k in fields)
            db.execute(f'CREATE TABLE "{name}" ({definition})')
            db.executemany(
                f'INSERT INTO "{name}" VALUES ({",".join("?" for _ in fields)})',
                (tuple(encoded(row.get(k)) for k in fields) for row in tables[name]),
            )
        if db.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise ValueError("Database integrity failure")


def verify_database(path, tables, schema):
    if Path(path).is_symlink():
        raise ValueError("Symlink database is prohibited")
    with sqlite3.connect(path) as db:
        if db.execute("SELECT name FROM sqlite_master WHERE type != 'table'").fetchone():
            raise ValueError("Unexpected database objects: views, triggers or indexes")
        if {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")} != set(
            tables
        ):
            raise ValueError("Database table population mismatch")
        for name, rows in tables.items():
            fields = [r[1] for r in db.execute(f'PRAGMA table_info("{name}")')]
            if fields != schema[name]:
                raise ValueError("Database column population mismatch")
            actual = db.execute(f'SELECT * FROM "{name}" ORDER BY rowid')
            for row in rows:
                if actual.fetchone() != tuple(encoded(row.get(k)) for k in fields):
                    raise ValueError(f"Database rows differ from source: {name}")
            if actual.fetchone() is not None:
                raise ValueError(f"Database has extra rows: {name}")


def inventory(root, identity):
    root = Path(root)
    if root.is_symlink() or any(p.is_symlink() for p in root.rglob("*")):
        raise ValueError("Symlink in package inventory")
    artifacts = {
        str(p.relative_to(root)): file_hash(p)
        for p in sorted(root.rglob("*"))
        if p.is_file() and not (p.parent == root and p.name in {"manifest.json", "SHA256SUMS.txt"})
    }
    write_json(root / "manifest.json", {"identity": identity, "artifacts": artifacts})
    checks = {**artifacts, "manifest.json": file_hash(root / "manifest.json")}
    (root / "SHA256SUMS.txt").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(checks.items()))
    )
    return artifacts


def collect_tables(model, result):
    tables = {name: list(rows) for name, rows in model.tables.items()}
    tables.update(
        annual_statements=result["unit_annual_rows"],
        monthly_statements=result["unit_monthly_rows"],
        legal_statements=result["monthly_rows"],
        legal_trial_balance=result["legal_trial_balance_rows"],
        enterprise_journal=result["journal_rows"],
        unit_trial_balance=result["unit_rows"],
        enterprise_funding=result["funding_rows"],
    )
    for unit in ("pale-sun", "american-resource-utility"):
        for name, rows in physical_registers(unit).items():
            tables[f"reference_{unit.replace('-', '_')}_{name}"] = [
                dict(row, reporting_unit=unit) for row in rows
            ]
    return tables


def write_packages(output, tables, identity, *, schema_draft=False):
    output = Path(output)
    if schema_draft:
        schema = {name: columns(rows) for name, rows in sorted(tables.items())}
        scope = proposed_scope(tables)
        write_json(output / "proposed_export_schema.json", schema)
        write_json(output / "proposed_export_scope.json", scope)
    else:
        schema, scope = json.loads(SCHEMA.read_text()), json.loads(SCOPE.read_text())
        validate_schema(tables, schema, scope)
    for name, rows in sorted(tables.items()):
        csv_table(output / "tables" / f"{name}.csv", rows, schema[name])
    database(output / "enterprise.sqlite3", tables, schema)
    verify_database(output / "enterprise.sqlite3", tables, schema)
    unit_counts = {}
    for unit in UNITS:
        selected = {
            name: subset
            for name, rows in tables.items()
            if (
                subset := [
                    r
                    for r in rows
                    if r.get("reporting_unit", r.get("unit", r.get("home_unit"))) == unit
                ]
            )
        }
        unit_schema = {name: schema[name] for name in selected}
        root = output / "units" / unit
        root.mkdir(parents=True, exist_ok=True)
        for name, rows in selected.items():
            csv_table(root / f"{name}.csv", rows, unit_schema[name])
        database(root / "evidence.sqlite3", selected, unit_schema)
        verify_database(root / "evidence.sqlite3", selected, unit_schema)
        write_json(root / "schema.json", unit_schema)
        counts = {name: len(rows) for name, rows in selected.items()}
        write_json(root / "coverage.json", counts)
        (root / "README.md").write_text(
            f"# {unit}: operating evidence\n\n"
            "Public synthetic conditional scenarios and retained 2026 calibration.\n"
            "CSV and SQLite are exact reporting-unit extracts from the integrated enterprise.\n"
            "Shared corporate Treasury/control populations remain in the parent package.\n"
            "The parent workbook summarizes all seven lines. Unit cash is not a bank balance.\n"
        )
        inventory(root, dict(identity, unit=unit))
        unit_counts[unit] = counts
    write_json(output / "export_schema.json", schema)
    write_json(output / "export_scope.json", scope)
    return unit_counts


def content_hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
