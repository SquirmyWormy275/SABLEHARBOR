import csv
import hashlib
import json
import sqlite3

import pytest

from tools.company_closeout.independent_import import inspect

UNITS = (
    "foundry-field",
    "atlas-meridian",
    "advisory",
    "willow",
    "project-cradle",
    "pale-sun",
    "american-resource-utility",
)


def write_table(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["record_id", "unit"])
        writer.writerows(rows)


def write_db(path, rows):
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE records (record_id TEXT, unit TEXT)")
        db.executemany("INSERT INTO records VALUES (?,?)", rows)


def rehash(root):
    artifacts = {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file() and p.name != "manifest.json"
    }
    (root / "manifest.json").write_text(json.dumps({"identity": "fixture", "artifacts": artifacts}))


@pytest.fixture
def exports(tmp_path):
    rows = [(str(i), unit) for i, unit in enumerate(UNITS)]
    (tmp_path / "export_schema.json").write_text(json.dumps({"records": ["record_id", "unit"]}))
    write_table(tmp_path / "tables/records.csv", rows)
    write_db(tmp_path / "enterprise.sqlite3", rows)
    for row in rows:
        unit = tmp_path / "units" / row[1]
        write_table(unit / "records.csv", [row])
        write_db(unit / "evidence.sqlite3", [row])
        (unit / "coverage.json").write_text('{"records": 1}')
    rehash(tmp_path)
    return tmp_path


def test_all_seven_units_reconcile(exports):
    receipt = inspect(exports)
    assert receipt["rows"] == 7
    assert set(receipt["unit_table_counts"]) == set(UNITS)


def test_matching_unit_csv_and_sql_cannot_omit_enterprise_member(exports):
    unit = exports / "units/foundry-field"
    with sqlite3.connect(unit / "evidence.sqlite3") as db:
        db.execute("DELETE FROM records")
    write_table(unit / "records.csv", [])
    (unit / "coverage.json").write_text('{"records": 0}')
    rehash(exports)
    with pytest.raises(ValueError, match="Unit scope differs"):
        inspect(exports)


def test_matching_unit_csv_and_sql_cannot_substitute_member(exports):
    unit = exports / "units/foundry-field"
    with sqlite3.connect(unit / "evidence.sqlite3") as db:
        db.execute("UPDATE records SET record_id='forged'")
    write_table(unit / "records.csv", [("forged", "foundry-field")])
    rehash(exports)
    with pytest.raises(ValueError, match="exact enterprise subset"):
        inspect(exports)


def test_changed_bytes_rejected_before_import(exports):
    write_table(exports / "tables/records.csv", [])
    with pytest.raises(ValueError, match="Export bytes changed"):
        inspect(exports)


def test_executable_sql_object_rejected_even_with_new_hash(exports):
    with sqlite3.connect(exports / "enterprise.sqlite3") as db:
        db.execute("CREATE VIEW disguised AS SELECT * FROM records")
    rehash(exports)
    with pytest.raises(ValueError, match="executable object"):
        inspect(exports)
