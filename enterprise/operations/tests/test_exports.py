"""Independent distribution boundary and content-integrity checks."""

import copy
import csv
import json
import sqlite3

import pytest

from enterprise.business.validation import verify_files
from enterprise.operations import exports


@pytest.fixture
def population():
    tables = {
        "ledger": [
            {
                "unit": "foundry-field",
                "entity": "SHI",
                "scenario": "base",
                "fact_state": "SYNTHETIC",
                "amount": "10.0000",
            },
            {
                "unit": "pale-sun",
                "entity": "PS",
                "scenario": "base",
                "fact_state": "SYNTHETIC",
                "amount": "20.0000",
            },
            {
                "unit": "corporate",
                "entity": "SHI",
                "scenario": "base",
                "fact_state": "SYNTHETIC",
                "amount": "30.0000",
            },
        ]
    }
    schema = {"ledger": ["amount", "entity", "fact_state", "scenario", "unit"]}
    # Fixed permission contract; the tests never infer permission from mutations.
    scope = {
        "ledger": {
            "allowed_values": {
                "unit": ["foundry-field", "pale-sun", "corporate"],
                "entity": ["SHI", "PS"],
                "scenario": ["base"],
                "fact_state": ["SYNTHETIC"],
            },
            "routing_fields": ["unit", "entity"],
            "allowed_routes": [["foundry-field", "SHI"], ["pale-sun", "PS"], ["corporate", "SHI"]],
        }
    }
    return tables, schema, scope


@pytest.mark.parametrize(
    "mutation",
    [
        "new_table",
        "new_field",
        "unknown_unit",
        "wrong_entity",
        "missing_unit",
        "missing_entity",
        "unknown_scenario",
        "unknown_fact_state",
    ],
)
def test_schema_and_scope_fail_closed(population, mutation):
    tables, schema, scope = copy.deepcopy(population)
    row = tables["ledger"][0]
    if mutation == "new_table":
        tables["private_dossier"] = []
    elif mutation == "new_field":
        row["unapproved_notes"] = "Must not enter the package"
    elif mutation == "missing_unit":
        del row["unit"]
    elif mutation == "missing_entity":
        del row["entity"]
    elif mutation == "wrong_entity":
        # Each value is individually approved, but the joint route is wrong.
        row["entity"] = "PS"
    elif mutation == "unknown_unit":
        row["unit"] = "unapproved-business"
    elif mutation == "unknown_scenario":
        row["scenario"] = "actual"
    else:
        row["fact_state"] = "OBSERVED_ACTUAL"
    with pytest.raises(ValueError):
        exports.validate_schema(tables, schema, scope)


def test_approved_route_contract_accepts_valid_population(population):
    exports.validate_schema(*population)


@pytest.mark.parametrize(
    "value", ["=1+1", "+SUM(A1:A2)", "-HYPERLINK(1)", "@SUM(A1:A2)", "\t =1+1"]
)
def test_csv_formula_neutralization(tmp_path, value):
    path = tmp_path / "export.csv"
    exports.csv_table(path, [{"note": value}])
    with path.open(newline="") as stream:
        assert list(csv.DictReader(stream)) == [{"note": "'" + value}]


def test_csv_preserves_numeric_negatives_and_raw_database_values(tmp_path):
    rows = [{"amount": "-105.2300", "note": "=untrusted"}]
    path = tmp_path / "export.csv"
    exports.csv_table(path, rows)
    with path.open(newline="") as stream:
        assert list(csv.DictReader(stream)) == [{"amount": "-105.2300", "note": "'=untrusted"}]
    database = tmp_path / "evidence.sqlite3"
    schema = {"rows": ["amount", "note"]}
    exports.database(database, {"rows": rows}, schema)
    exports.verify_database(database, {"rows": rows}, schema)
    with sqlite3.connect(database) as db:
        assert db.execute('SELECT * FROM "rows"').fetchone() == ("-105.2300", "=untrusted")


@pytest.mark.parametrize(
    "mutation",
    [
        "changed_cell",
        "missing_row",
        "extra_row",
        "extra_table",
        "changed_column",
        "extra_view",
        "extra_trigger",
        "extra_index",
    ],
)
def test_database_verification_rejects_changed_content_and_schema(tmp_path, population, mutation):
    tables, schema, _ = population
    path = tmp_path / "evidence.sqlite3"
    exports.database(path, tables, schema)
    with sqlite3.connect(path) as db:
        if mutation == "changed_cell":
            db.execute("UPDATE ledger SET amount='10.0001' WHERE rowid=1")
        elif mutation == "missing_row":
            db.execute("DELETE FROM ledger WHERE rowid=1")
        elif mutation == "extra_row":
            db.execute("INSERT INTO ledger SELECT * FROM ledger WHERE rowid=1")
        elif mutation == "extra_table":
            db.execute("CREATE TABLE hidden (payload TEXT)")
        elif mutation == "changed_column":
            db.execute("ALTER TABLE ledger RENAME COLUMN amount TO replacement")
        elif mutation == "extra_view":
            db.execute("CREATE VIEW hidden AS SELECT * FROM ledger")
        elif mutation == "extra_trigger":
            db.execute(
                "CREATE TRIGGER hidden AFTER INSERT ON ledger BEGIN DELETE FROM ledger WHERE rowid=1; END"
            )
        else:
            db.execute("CREATE INDEX hidden ON ledger(amount)")
    with pytest.raises(ValueError):
        exports.verify_database(path, tables, schema)


def test_database_target_is_never_silently_overwritten(tmp_path, population):
    tables, schema, _ = population
    path = tmp_path / "evidence.sqlite3"
    exports.database(path, tables, schema)
    original = path.read_bytes()
    with pytest.raises(ValueError, match="new"):
        exports.database(path, tables, schema)
    assert path.read_bytes() == original


def test_database_verification_rejects_symlink(tmp_path, population):
    tables, schema, _ = population
    path = tmp_path / "outside.sqlite3"
    exports.database(path, tables, schema)
    link = tmp_path / "evidence.sqlite3"
    link.symlink_to(path)
    with pytest.raises(ValueError, match="[Ss]ymlink"):
        exports.verify_database(link, tables, schema)


def test_reporting_unit_routes_physical_unit_without_cross_entity_leak(
    tmp_path, population, monkeypatch
):
    tables, schema, scope = population
    tables["weights"] = [
        {"unit": "tonnes", "reporting_unit": "pale-sun", "entity": "PS", "value": "50"}
    ]
    schema["weights"] = ["entity", "reporting_unit", "unit", "value"]
    scope["weights"] = {
        "allowed_values": {"unit": ["tonnes"], "reporting_unit": ["pale-sun"], "entity": ["PS"]},
        "routing_fields": ["unit", "reporting_unit", "entity"],
        "allowed_routes": [["tonnes", "pale-sun", "PS"]],
    }
    tables["positions"] = [
        {"home_unit": "foundry-field", "person_id": "SYN-STAFF-1"},
        {"home_unit": "corporate", "person_id": "SYN-STAFF-2"},
    ]
    schema["positions"] = ["home_unit", "person_id"]
    scope["positions"] = {
        "allowed_values": {"home_unit": ["foundry-field", "corporate"]},
        "routing_fields": ["home_unit"],
        "allowed_routes": [["foundry-field"], ["corporate"]],
    }
    schema_path, scope_path = tmp_path / "schema.json", tmp_path / "scope.json"
    schema_path.write_text(json.dumps(schema))
    scope_path.write_text(json.dumps(scope))
    monkeypatch.setattr(exports, "SCHEMA", schema_path)
    monkeypatch.setattr(exports, "SCOPE", scope_path)
    output = tmp_path / "output"
    counts = exports.write_packages(output, tables, {"test": "synthetic"})
    assert counts["foundry-field"] == {"ledger": 1, "positions": 1}
    assert counts["pale-sun"] == {"ledger": 1, "weights": 1}
    assert counts["advisory"] == {}
    with sqlite3.connect(output / "units/foundry-field/evidence.sqlite3") as db:
        assert db.execute("SELECT unit,entity,amount FROM ledger").fetchall() == [
            ("foundry-field", "SHI", "10.0000")
        ]
        assert db.execute("SELECT home_unit,person_id FROM positions").fetchall() == [
            ("foundry-field", "SYN-STAFF-1")
        ]
    with sqlite3.connect(output / "units/pale-sun/evidence.sqlite3") as db:
        assert db.execute("SELECT unit,entity,amount FROM ledger").fetchall() == [
            ("pale-sun", "PS", "20.0000")
        ]
        assert db.execute("SELECT unit,reporting_unit FROM weights").fetchall() == [
            ("tonnes", "pale-sun")
        ]


def test_nested_manifests_and_checksums_are_parent_inventory_members(tmp_path):
    unit = tmp_path / "units/advisory"
    unit.mkdir(parents=True)
    (unit / "evidence.csv").write_text("item,value\nexample,1\n")
    exports.inventory(unit, {"unit": "advisory"})
    artifacts = exports.inventory(tmp_path, {"unit": "enterprise"})
    assert {
        "units/advisory/manifest.json",
        "units/advisory/SHA256SUMS.txt",
        "units/advisory/evidence.csv",
    } == set(artifacts)
    verify_files(tmp_path)
    (unit / "manifest.json").write_text("{}\n")
    with pytest.raises(ValueError, match="hash"):
        verify_files(tmp_path)


def test_inventory_rejects_symlink_to_outside_payload(tmp_path):
    outside = tmp_path / "outside.csv"
    outside.write_text("other_unit,amount\nprivate,100\n")
    package = tmp_path / "package"
    package.mkdir()
    (package / "evidence.csv").symlink_to(outside)
    with pytest.raises(ValueError, match="[Ss]ymbolic|[Ss]ymlink|link"):
        exports.inventory(package, {"unit": "advisory"})
