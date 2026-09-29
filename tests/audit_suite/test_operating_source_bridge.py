"""Neutral monthly-source import tests, with actual private CompanyStore writes."""

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import (
    encoded,
    import_operating_tables,
    month_bounds,
    plan_operating_import,
    sha,
)

ROOT = Path(__file__).resolve().parents[2]


def model(rows):
    inputs = {"business": {}, "operations": {}}
    return SimpleNamespace(
        _built=True,
        inputs={},
        operations_inputs={},
        input_hash=sha(encoded(inputs)),
        tables={"commercial_changes": rows},
    )


def row(month=1, scenario="base"):
    return {
        "scenario": scenario,
        "unit": "unit-a",
        "change_id": "CHANGE-1",
        "month_index": month,
        "period": "2027-01-31" if month == 1 else "2027-02-28",
        "fact_state": "PUBLIC_SYNTHETIC_CONDITIONAL_FORECAST",
    }


def options():
    return {
        "owner_ids": {"commercial_changes": "EXISTING-OWNER"},
        "branch_ids": {"base": "source-base"},
        "tables": ["commercial_changes"],
        "repository": ROOT,
    }


def test_monthly_versions_idempotency_and_no_default_grants(tmp_path):
    tmp_path.chmod(0o700)
    store = CompanyStore(tmp_path)
    source = model([row(2), row(1)])
    first = import_operating_tables(store, source, company_id="COMPANY", **options())
    again = import_operating_tables(store, source, company_id="COMPANY", **options())
    assert first == again and first["record_versions"] == 2
    with sqlite3.connect(store.path) as db:
        versions = db.execute(
            "SELECT version,event_at,available_at,imported_at,content "
            "FROM versions ORDER BY version"
        ).fetchall()
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
    assert [v[0] for v in versions] == [1, 2]
    assert all(v[1] is None and v[3] for v in versions)
    assert versions[0][2].startswith("2027-02-01T00:00:00")
    assert json.loads(versions[0][4])["source_row"] == row(1)
    receipt = first["receipts"][0]
    with pytest.raises(CompanyStoreError, match="unavailable or unauthorized"):
        store.read_version(
            "READER",
            "AUDIT",
            "COMPANY",
            "source-base",
            "commercial_changes",
            receipt["record"],
            version=1,
            as_of="2027-03-01T00:00:00Z",
        )
    store.grant("READER", "AUDIT", "COMPANY", "source-base", "commercial_changes")
    with pytest.raises(CompanyStoreError, match="unavailable or unauthorized"):
        store.read_version(
            "READER",
            "AUDIT",
            "COMPANY",
            "source-base",
            "commercial_changes",
            receipt["record"],
            version=1,
            as_of="2027-01-31T23:59:59Z",
        )
    value = store.read_version(
        "READER",
        "AUDIT",
        "COMPANY",
        "source-base",
        "commercial_changes",
        receipt["record"],
        version=1,
        as_of="2027-02-01T00:00:00Z",
    )
    assert value["provenance"]["source_row_sha256"] == sha(encoded(row(1)))


def test_bad_late_row_fails_before_any_system_is_registered(tmp_path):
    tmp_path.chmod(0o700)
    store = CompanyStore(tmp_path)
    bad = row(2)
    bad["period"] = "2027-02-01"
    with pytest.raises(CompanyStoreError, match="month close"):
        import_operating_tables(store, model([row(), bad]), company_id="COMPANY", **options())
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT COUNT(*) FROM systems").fetchone()[0] == 0


def test_scenarios_cannot_share_a_branch_and_duplicate_chronology_fails():
    opts = options()
    opts["branch_ids"] = {"base": "same", "downside": "same"}
    with pytest.raises(CompanyStoreError, match="isolated"):
        plan_operating_import(model([row(), row(scenario="downside")]), **opts)
    with pytest.raises(CompanyStoreError, match="chronology"):
        plan_operating_import(model([row(), row()]), **options())


def test_unapplied_month_sentinel_is_not_an_event_date():
    value = {**row(), "applied_month": 0, "status": "HELD_PENDING_ACTIVATION"}
    assert month_bounds(value)[2] == "2027-02-01T00:00:00+00:00"
    with pytest.raises(CompanyStoreError, match="invalid month"):
        month_bounds({**value, "status": "APPLIED"})
    with pytest.raises(CompanyStoreError, match="invalid month"):
        month_bounds({**value, "applied_month": False})


def test_input_tampering_and_hidden_table_selection_rejected():
    source = model([row()])
    source.inputs["changed"] = True
    with pytest.raises(CompanyStoreError, match="input hash"):
        plan_operating_import(source, **options())
    opts = options()
    opts["tables"] = ["rubric"]
    with pytest.raises(CompanyStoreError, match="approved operating tables"):
        plan_operating_import(model([row()]), **opts)
