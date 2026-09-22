"""Read-only standalone CSV/SQLite reinspection without importing any company generator."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

D = Decimal
NUMERIC = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")


def csv_value(value):
    stripped = value.lstrip()
    if not value or value.startswith("'") or not stripped:
        return value
    if stripped[0] in "=@" or (stripped[0] in "+-" and not NUMERIC.fullmatch(stripped)):
        return "'" + value
    return value


def inspect(directory: Path):
    if directory.is_symlink() or any(p.is_symlink() for p in directory.rglob("*")):
        raise ValueError("Linked export rejected")
    manifest_bytes = (directory / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    for relative, digest in manifest["artifacts"].items():
        path = directory / relative
        if not path.resolve().is_relative_to(directory.resolve()):
            raise ValueError("Escaping export")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Export bytes changed")
    schema = json.loads((directory / "export_schema.json").read_bytes())
    counts = {}
    journal_balances = defaultdict(D)
    journal_keys = set()
    with sqlite3.connect(
        (directory / "enterprise.sqlite3").resolve().as_uri() + "?mode=ro", uri=True
    ) as db:
        if db.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise ValueError("SQLite integrity failure")
        objects = db.execute(
            "SELECT name,type FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
        ).fetchall()
        if set(objects) != {(name, "table") for name in schema}:
            raise ValueError("Unexpected SQLite executable object or table population")
        for name, columns in schema.items():
            if not re.fullmatch("[A-Za-z_][A-Za-z_0-9]*", name):
                raise ValueError("Unsafe table identifier")
            actual_columns = [r[1] for r in db.execute(f'PRAGMA table_info("{name}")')]
            if actual_columns != columns:
                raise ValueError("SQL column identity differs from declared export schema")
            with (directory / "tables" / f"{name}.csv").open(newline="") as stream:
                reader = csv.DictReader(stream)
                if reader.fieldnames != columns:
                    raise ValueError("CSV column population differs")
                actual = db.execute(f'SELECT * FROM "{name}" ORDER BY rowid')
                n = 0
                for row in reader:
                    values = actual.fetchone()
                    if values is None or tuple(csv_value(v) for v in values) != tuple(
                        row[c] for c in columns
                    ):
                        raise ValueError("CSV and independent SQL row population differ")
                    if name == "enterprise_journal":
                        key = (row["scenario"], row["journal_id"], row["line_no"])
                        if key in journal_keys:
                            raise ValueError("Duplicate journal line")
                        journal_keys.add(key)
                        signed = D(row["signed_usd"])
                        if D(row["debit_usd"]) - D(row["credit_usd"]) != signed:
                            raise ValueError("Journal sign arithmetic differs")
                        journal_balances[row["scenario"], row["journal_id"]] += signed
                    if name in {"legal_statements", "monthly_statements", "annual_statements"}:
                        if abs(
                            D(row["assets_usd"]) - D(row["liabilities_usd"]) - D(row["equity_usd"])
                        ) > D("0.01"):
                            raise ValueError("Statement balance equation failed")
                        cash = sum(
                            D(row[k])
                            for k in [
                                "opening_cash_usd",
                                "opening_or_noncash_cash_bridge_usd",
                                "operating_cash_flow_usd",
                                "investing_cash_flow_usd",
                                "financing_cash_flow_usd",
                            ]
                        )
                        if abs(cash - D(row["ending_cash_usd"])) > D("0.01"):
                            raise ValueError("Statement cash bridge failed")
                    n += 1
                if actual.fetchone() is not None:
                    raise ValueError("SQL contains omitted CSV members")
                counts[name] = n
    if any(abs(value) > D("0.01") for value in journal_balances.values()):
        raise ValueError("Unbalanced journal entry")
    units = {}
    expected_units = {
        "foundry-field",
        "atlas-meridian",
        "advisory",
        "willow",
        "project-cradle",
        "pale-sun",
        "american-resource-utility",
    }
    if {p.name for p in (directory / "units").iterdir()} != expected_units:
        raise ValueError("Omitted or additional reporting unit")
    with sqlite3.connect(
        (directory / "enterprise.sqlite3").resolve().as_uri() + "?mode=ro", uri=True
    ) as master:
        for unit in sorted((directory / "units").iterdir()):
            declared = json.loads((unit / "coverage.json").read_bytes())
            expected_counts = {}
            for table, fields in schema.items():
                routing = next(
                    (x for x in ("reporting_unit", "unit", "home_unit") if x in fields), None
                )
                if routing is None:
                    continue
                n = master.execute(
                    f'SELECT count(*) FROM "{table}" WHERE "{routing}"=?', (unit.name,)
                ).fetchone()[0]
                if n:
                    expected_counts[table] = n
            if declared != expected_counts:
                raise ValueError("Unit scope differs from enterprise population")
            with sqlite3.connect(
                (unit / "evidence.sqlite3").resolve().as_uri() + "?mode=ro", uri=True
            ) as db:
                objects = db.execute(
                    "SELECT name,type FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
                ).fetchall()
                if set(objects) != {(name, "table") for name in declared}:
                    raise ValueError("Unexpected unit objects or tables")
                for table in declared:
                    fields = schema[table]
                    actual_columns = [r[1] for r in db.execute(f'PRAGMA table_info("{table}")')]
                    if actual_columns != fields:
                        raise ValueError("Unit SQL column identity differs from declared schema")
                    routing = next(
                        x for x in ("reporting_unit", "unit", "home_unit") if x in fields
                    )
                    expected = master.execute(
                        f'SELECT * FROM "{table}" WHERE "{routing}"=? ORDER BY rowid', (unit.name,)
                    )
                    actual = db.execute(f'SELECT * FROM "{table}" ORDER BY rowid')
                    with (unit / f"{table}.csv").open(newline="") as stream:
                        reader = csv.reader(stream)
                        if next(reader) != fields:
                            raise ValueError("Unit CSV fields differ")
                        for values in expected:
                            if actual.fetchone() != values or next(reader, None) != [
                                csv_value(v) for v in values
                            ]:
                                raise ValueError(
                                    "Unit originals differ from exact enterprise subset"
                                )
                        if actual.fetchone() is not None or next(reader, None) is not None:
                            raise ValueError("Extra unit row")
                units[unit.name] = expected_counts
    if (directory / "manifest.json").read_bytes() != manifest_bytes:
        raise ValueError("Export manifest changed during independent inspection")
    return {
        "result": "PASS",
        "independence": "stdlib-only read-only CSV/SQL reperformance; no generator imports",
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "source_identity": manifest["identity"],
        "table_counts": counts,
        "rows": sum(counts.values()),
        "unit_table_counts": units,
        "journal_lines": len(journal_keys),
        "journal_entries": len(journal_balances),
        "limits": [
            "Declared population completeness is not external confirmation",
            "All seven reporting units plus corporate/legal/consolidated scopes remain distinct",
            "Do not add unit extracts to the enterprise tables or forecasts to completed periods",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    result = inspect(args.directory)
    body = json.dumps(result, indent=2) + "\n"
    if args.receipt:
        args.receipt.write_text(body)
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in {"table_counts", "unit_table_counts"}},
            indent=2,
        )
    )
