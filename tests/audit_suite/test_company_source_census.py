import copy
import json

import pytest

from enterprise.audit_suite.company_source_census import export_census, verify_export
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.store import digest

QUERY = {
    "version_policy": "ALL_VISIBLE_VERSIONS",
    "event_window": {"start": "2027-01-01T00:00:00Z", "end": "2027-02-01T00:00:00Z"},
    "unknown_event_policy": "INCLUDE_UNDATED_STRATUM",
}


@pytest.fixture
def native(tmp_path):
    tmp_path.chmod(0o700)
    store = CompanyStore(tmp_path)
    with store._db() as db:
        db.execute("PRAGMA journal_mode=WAL")
    store.register_system("SH", "branch", "identity", "owner")
    store.register_system("SH", "branch", "empty", "owner")
    store.grant("actor", "audit", "SH", "branch", "identity")
    store.grant("actor", "audit", "SH", "branch", "empty")
    for record, version, event, available in [
        ("R1", 1, "2027-01-02T00:00:00Z", "2027-01-03T00:00:00Z"),
        ("R1", 2, "2027-02-02T00:00:00Z", "2027-02-03T00:00:00Z"),
        ("R1", 3, "2027-04-02T00:00:00Z", "2027-04-03T00:00:00Z"),
        ("U1", 1, None, "2027-01-05T00:00:00Z"),
    ]:
        store.append_version(
            "SH",
            "branch",
            "identity",
            record,
            expected_version=version - 1,
            command_id=f"{record}-{version}",
            event_at=event,
            available_at=available,
            content=json.dumps({"record": record, "version": version}).encode(),
            origin="REPOSITORY_SYNTHETIC_DOCUMENT" if event is None else "AUTHORED_TRAINING_SOURCE",
            provenance={
                "source_reference": "original",
                "name": "original.json",
                "qualification": "Local exercise, not actual deployment",
            },
        )
    return store


def run(store, query=None, **kwargs):
    options = dict(
        principal_id="actor",
        engagement_id="audit",
        company_id="SH",
        branch_id="branch",
        system_id="identity",
        as_of="2027-03-01T00:00:00Z",
        query=query or copy.deepcopy(QUERY),
        page_size=1,
    )
    options.update(kwargs)
    return export_census(store, **options)


def test_latest_policy_precedes_event_window_and_never_resurrects_old_version(native):
    all_versions = run(native)
    assert [
        (m["source"]["record"], m["source"]["version"]) for m in all_versions["manifest"]["members"]
    ] == [("R1", 1), ("U1", 1)]
    latest = run(native, {**QUERY, "version_policy": "LATEST_VISIBLE_PER_RECORD"})
    assert [m["source"]["record"] for m in latest["manifest"]["members"]] == ["U1"]
    assert latest["manifest"]["excluded"]["outside_event_window"] == 1
    assert latest["manifest"]["scanned_visible_versions"] == 2
    assert "future" not in json.dumps(latest["manifest"]).lower()
    assert latest["manifest"]["strata"] == {"IN_EVENT_WINDOW": 0, "UNDATED": 1}
    assert latest["manifest"]["members"][0]["source"]["event_at"] is None
    assert (
        verify_export(latest, expected_manifest_sha256=digest(latest["manifest"]))["members"] == 1
    )


def test_undated_excluded_without_inventing_dates_and_empty_valid(native):
    result = run(native, {**QUERY, "unknown_event_policy": "EXCLUDE"})
    assert result["manifest"]["excluded"]["undated"] == 1
    assert result["manifest"]["strata"]["UNDATED"] == 0
    empty = run(native, system_id="empty")
    assert empty["manifest"]["members"] == []
    assert verify_export(empty, expected_manifest_sha256=digest(empty["manifest"]))["members"] == 0


@pytest.mark.parametrize(
    "change",
    [
        {"version_policy": "LATEST"},
        {"unknown_event_policy": "GUESS"},
        {"as_of": "2029"},
        {"event_window": {"start": "2027-01-01", "end": "2027-02-01"}},
    ],
)
def test_query_rejects_unknown_modes_fields_and_implicit_timezones(native, change):
    with pytest.raises(CompanyStoreError):
        run(native, {**QUERY, **change})


def test_future_window_wrong_grant_and_wrong_engagement_denied(native):
    with pytest.raises(CompanyStoreError):
        run(native, as_of="2027-01-10T00:00:00Z")
    with pytest.raises(CompanyStoreError):
        run(native, engagement_id="other")
    native.grant("actor", "audit", "SH", "branch", "identity", active=False)
    with pytest.raises(CompanyStoreError):
        run(native)


def test_pagination_and_byte_quotas_fail_without_partial_export(native, monkeypatch):
    from enterprise.audit_suite import company_source_census as module

    with pytest.raises(CompanyStoreError, match="page budget"):
        run(native, max_pages=1)
    monkeypatch.setattr(module, "MAX_NATIVE_BYTES", 1)
    with pytest.raises(CompanyStoreError, match="byte quota"):
        run(native)


def test_native_bytes_and_manifest_page_changes_fail_verification(native):
    exported = run(native)
    pin = digest(exported["manifest"])
    broken = copy.deepcopy(exported)
    broken["originals"][0] = b"changed"
    with pytest.raises(CompanyStoreError, match="Native census source"):
        verify_export(broken, expected_manifest_sha256=pin)
    broken = copy.deepcopy(exported)
    broken["originals"].pop()
    with pytest.raises(CompanyStoreError, match="Incomplete"):
        verify_export(broken, expected_manifest_sha256=pin)
    broken = copy.deepcopy(exported)
    broken["manifest"]["pages"].pop()
    with pytest.raises(CompanyStoreError, match="manifest changed"):
        verify_export(broken, expected_manifest_sha256=pin)


def test_append_during_pagination_preserves_original_snapshot(native, monkeypatch):
    original = native._read
    done = False

    def read(*args, **kwargs):
        nonlocal done
        value = original(*args, **kwargs)
        if not done:
            done = True
            native.append_version(
                "SH",
                "branch",
                "identity",
                "NEW",
                expected_version=0,
                command_id="append",
                event_at="2027-01-06T00:00:00Z",
                available_at="2027-01-06T00:00:00Z",
                content=b"new",
                provenance={"source_reference": "new"},
            )
        return value

    monkeypatch.setattr(native, "_read", read)
    assert run(native)["manifest"]["source_versions"] == 2
    assert run(native)["manifest"]["source_versions"] == 3


def test_revocation_during_snapshot_blocks_return(native, monkeypatch):
    original = native._read

    def read(*args, **kwargs):
        value = original(*args, **kwargs)
        native.grant("actor", "audit", "SH", "branch", "identity", active=False)
        return value

    monkeypatch.setattr(native, "_read", read)
    with pytest.raises(CompanyStoreError, match="grant"):
        run(native)


def test_one_portfolio_alias_only_and_registry_change_denied(tmp_path, monkeypatch):
    from tests.audit_suite.test_company_federation import portfolio

    facade, stores, config, path = portfolio(tmp_path)
    kwargs = dict(
        principal_id="actor",
        engagement_id="ENG",
        company_id="LOGICAL",
        branch_id="portfolio",
        system_id="ONE:records",
        as_of="2027-03-01T00:00:00Z",
        query=QUERY,
    )
    result = export_census(facade, **kwargs)
    assert result["manifest"]["source_store_id"] == "one"
    assert result["manifest"]["source_versions"] == 1
    assert result["manifest"]["members"][0]["source"]["system"] == "records"
    assert result["manifest"]["portfolio_binding"] == facade.binding
    original = stores["one"]._read
    # Facade uses its own read-only adapter over the same database.
    original = facade._stores["one"]._read

    def read(*args, **kw):
        value = original(*args, **kw)
        config["components"]["one"]["namespace"] = "CHANGED"
        path.write_text(json.dumps(config))
        return value

    monkeypatch.setattr(facade._stores["one"], "_read", read)
    with pytest.raises(CompanyStoreError, match="changed"):
        export_census(facade, **kwargs)
