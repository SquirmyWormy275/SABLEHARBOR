"""Successor export contracts cannot bypass schema or entity routing controls."""

import sqlite3

import pytest

from enterprise.operations.exports import write_packages

SCHEMA = {"records": ["entity", "id", "unit"]}
SCOPE = {
    "records": {
        "allowed_values": {"entity": ["SHI"], "unit": ["corporate"]},
        "routing_fields": ["unit", "entity"],
        "allowed_routes": [["corporate", "SHI"]],
    }
}


def test_explicit_contract_preserves_enterprise_export(tmp_path):
    rows = {"records": [{"id": "CURRENT-1", "entity": "SHI", "unit": "corporate"}]}
    write_packages(tmp_path, rows, {"source": "synthetic-test"}, schema=SCHEMA, scope=SCOPE)
    with sqlite3.connect(tmp_path / "enterprise.sqlite3") as db:
        assert db.execute("SELECT entity,id,unit FROM records").fetchall() == [
            ("SHI", "CURRENT-1", "corporate")
        ]


@pytest.mark.parametrize("options", [{"schema": SCHEMA}, {"scope": SCOPE}])
def test_partial_contract_denied(tmp_path, options):
    with pytest.raises(ValueError, match="together"):
        write_packages(tmp_path, {}, {}, **options)


def test_scope_violation_denied(tmp_path):
    rows = {"records": [{"id": "WRONG-ENTITY", "entity": "ARU", "unit": "corporate"}]}
    with pytest.raises(ValueError, match="scope"):
        write_packages(tmp_path, rows, {}, schema=SCHEMA, scope=SCOPE)
    assert not (tmp_path / "enterprise.sqlite3").exists()


def test_draft_cannot_override_explicit_contract(tmp_path):
    with pytest.raises(ValueError, match="Draft inference"):
        write_packages(tmp_path, {}, {}, schema=SCHEMA, scope=SCOPE, schema_draft=True)
