"""Neutral source populations exercise real immutable company records and grants."""

import copy
from pathlib import Path
from types import SimpleNamespace

import pytest

from enterprise.audit_suite.company_population import export_population, verify_export
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, import_operating_tables, sha

ROOT = Path(__file__).resolve().parents[2]


def source_row(month):
    return {
        "scenario": "base",
        "period": "2027-01-31" if month == 1 else "2027-02-28",
        "month_index": month,
        "unit": "foundry-field",
        "fact_state": "PUBLIC_SYNTHETIC_CONDITIONAL_FORECAST",
        "contract_id": "C1",
        "change_id": "CHANGE1",
        "kind": "EXPANSION",
        "original_effective_month": month,
        "approval_id": "A1",
        "applied_month": month,
        "status": "APPLIED",
    }


def prepare(tmp_path, *, extra=False):
    tmp_path.chmod(0o700)
    store = CompanyStore(tmp_path)
    rows = [source_row(1), source_row(2)]
    if extra:
        rows[0]["unknown_field"] = "not approved"
    model = SimpleNamespace(
        _built=True,
        inputs={},
        operations_inputs={},
        input_hash=sha(encoded({"business": {}, "operations": {}})),
        tables={"commercial_changes": rows},
    )
    import_operating_tables(
        store,
        model,
        company_id="COMPANY",
        owner_ids={"commercial_changes": "OWNER"},
        branch_ids={"base": "base-branch"},
        tables=["commercial_changes"],
        repository=ROOT,
    )
    return store


def args():
    return {
        "principal_id": "READER",
        "engagement_id": "AUDIT",
        "company_id": "COMPANY",
        "branch_id": "base-branch",
        "repository": ROOT,
        "query": {
            "table": "commercial_changes",
            "source_scenario": "base",
            "month_start": 1,
            "month_end": 2,
            "units": ["foundry-field"],
            "as_of": "2027-03-01T00:00:00Z",
        },
    }


def grant(store, active=True):
    store.grant("READER", "AUDIT", "COMPANY", "base-branch", "commercial_changes", active=active)


def test_full_version_population_stable_across_page_sizes(tmp_path):
    store = prepare(tmp_path)
    grant(store)
    one = export_population(store, page_size=1, **args())
    two = export_population(store, page_size=2, **args())
    assert len(one["records"]) == 2  # Includes prior version, not latest-only discovery.
    assert [r["source"]["version"] for r in one["records"]] == [1, 2]
    assert one["manifest"]["snapshot_id"] == two["manifest"]["snapshot_id"]
    assert len(one["manifest"]["pages"]) == 2
    assert one["manifest"]["independent_population_review"] == "NOT_PERFORMED"
    assert (
        verify_export(one, expected_manifest_sha256=sha(encoded(one["manifest"])))["members"] == 2
    )


def test_no_grant_and_incomplete_pagination_fail_closed(tmp_path):
    store = prepare(tmp_path)
    with pytest.raises(CompanyStoreError, match="unauthorized"):
        export_population(store, **args())
    grant(store)
    with pytest.raises(CompanyStoreError, match="Incomplete pagination"):
        export_population(store, page_size=1, max_pages=1, **args())


def test_changed_duplicate_or_missing_members_rejected(tmp_path):
    store = prepare(tmp_path)
    grant(store)
    good = export_population(store, **args())
    pin = sha(encoded(good["manifest"]))
    changes = []
    bad = copy.deepcopy(good)
    bad["records"].pop()
    changes.append(bad)
    bad = copy.deepcopy(good)
    bad["records"][1] = bad["records"][0]
    changes.append(bad)
    bad = copy.deepcopy(good)
    bad["records"][0]["source_row"]["status"] = "CHANGED"
    changes.append(bad)
    bad = copy.deepcopy(good)
    bad["manifest"]["pages"].pop()
    changes.append(bad)
    for value in changes:
        with pytest.raises(CompanyStoreError):
            verify_export(value, expected_manifest_sha256=pin)


def test_unknown_query_scope_future_interval_and_source_fields_fail(tmp_path):
    store = prepare(tmp_path, extra=True)
    grant(store)
    for query in [
        {**args()["query"], "sql": "SELECT anything"},
        {**args()["query"], "units": ["outside-scope"]},
        {**args()["query"], "as_of": "2027-02-28T23:59:59Z"},
    ]:
        with pytest.raises(CompanyStoreError):
            export_population(store, **{**args(), "query": query})
    with pytest.raises(CompanyStoreError, match="Unknown or missing source fields"):
        export_population(store, **args())


def test_revocation_before_return_aborts_snapshot(tmp_path, monkeypatch):
    store = prepare(tmp_path)
    grant(store)
    original = store.list_systems

    def revoke(*a):
        grant(store, active=False)
        return original(*a)

    monkeypatch.setattr(store, "list_systems", revoke)
    with pytest.raises(CompanyStoreError, match="revoked"):
        export_population(store, **args())


def test_concurrent_correction_enters_next_snapshot_not_partial_pages(tmp_path, monkeypatch):
    import json
    import threading

    store = prepare(tmp_path)
    grant(store)
    writer = CompanyStore(tmp_path)
    latest = store.list_records(
        "READER",
        "AUDIT",
        "COMPANY",
        "base-branch",
        "commercial_changes",
        as_of=args()["query"]["as_of"],
    )["records"][0]
    retained = store.read_version(
        "READER",
        "AUDIT",
        "COMPANY",
        "base-branch",
        "commercial_changes",
        latest["record"],
        version=2,
        as_of=args()["query"]["as_of"],
    )
    envelope = json.loads(retained["content"])
    envelope["source_row"]["status"] = "CORRECTED_SOURCE"
    provenance = {
        **retained["provenance"],
        "source_row_sha256": sha(encoded(envelope["source_row"])),
    }
    started, errors = threading.Event(), []

    def append():
        started.set()
        try:
            writer.append_version(
                "COMPANY",
                "base-branch",
                "commercial_changes",
                latest["record"],
                expected_version=2,
                command_id="CORRECTION",
                event_at=None,
                available_at="2027-03-01T00:00:00Z",
                content=encoded(envelope),
                provenance=provenance,
                origin="MIGRATED_SYNTHETIC_HISTORY",
            )
        except Exception as error:
            errors.append(error)

    thread = threading.Thread(target=append)
    original = store._read

    def during_first_page(*a):
        value = original(*a)
        if not started.is_set():
            thread.start()
            assert started.wait(2)
        return value

    monkeypatch.setattr(store, "_read", during_first_page)
    first = export_population(store, page_size=1, **args())
    thread.join(5)
    assert not thread.is_alive() and not errors
    assert len(first["records"]) == 2
    second = export_population(store, page_size=1, **args())
    assert len(second["records"]) == 3
    assert first["manifest"]["snapshot_id"] != second["manifest"]["snapshot_id"]
