import sqlite3

import pytest

from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError


@pytest.fixture
def source(tmp_path):
    tmp_path.chmod(0o700)
    store = CompanyStore(tmp_path)
    store.register_system("SH", "clean", "IAM", "owner")
    store.register_system("SH", "messy", "IAM", "owner")
    return store


def append(
    store, *, expected=0, command="import-1", content=b"original", available="2027-01-01T00:00:00Z"
):
    return store.append_version(
        "SH",
        "clean",
        "IAM",
        "EMP1",
        expected_version=expected,
        command_id=command,
        event_at="2026-12-31T00:00:00Z",
        available_at=available,
        content=content,
        provenance={"source_reference": "synthetic-original-1"},
    )


def read(store, **kwargs):
    return store.read_version(
        "auditor",
        "E1",
        "SH",
        "clean",
        "IAM",
        "EMP1",
        version=kwargs.get("version", 1),
        as_of=kwargs.get("as_of", "2027-01-02T00:00:00Z"),
    )


def collect(store, command="collect-1", version=1):
    return store.collect(
        "auditor",
        "E1",
        "SH",
        "clean",
        "IAM",
        "EMP1",
        version=version,
        as_of="2027-01-02T00:00:00Z",
        command_id=command,
    )


def test_independent_history_and_engagement_grants(source):
    original = append(source)  # No engagement exists or is required to write company activity.
    with pytest.raises(CompanyStoreError):
        read(source)
    source.grant("auditor", "E1", "SH", "clean", "IAM")
    assert read(source)["content"] == b"original"
    for company, branch, engagement in [
        ("OTHER", "clean", "E1"),
        ("SH", "messy", "E1"),
        ("SH", "clean", "E2"),
    ]:
        with pytest.raises(CompanyStoreError):
            source.read_version(
                "auditor",
                engagement,
                company,
                branch,
                "IAM",
                "EMP1",
                version=1,
                as_of="2027-01-02T00:00:00Z",
            )
    source.grant("auditor", "E2", "SH", "clean", "IAM")
    second = source.read_version(
        "auditor", "E2", "SH", "clean", "IAM", "EMP1", version=1, as_of="2027-01-02T00:00:00Z"
    )
    assert second["sha256"] == original["sha256"]


def test_future_gates_and_real_import_time(source):
    version = append(source)
    assert version["imported_at"] != version["event_at"]
    source.grant("auditor", "E1", "SH", "clean", "IAM")
    with pytest.raises(CompanyStoreError):
        read(source, as_of="2026-12-31T23:59:59Z")
    assert read(source, as_of="2026-12-31T17:00:00-07:00")["content"] == b"original"
    with pytest.raises(CompanyStoreError):
        read(source, as_of="2027-01-02")
    with pytest.raises(CompanyStoreError):
        append(source, available="2025-01-01T00:00:00Z")


def test_correction_preserves_versions_and_collection(source):
    append(source)
    source.grant("auditor", "E1", "SH", "clean", "IAM")
    retained = collect(source)
    append(source, expected=1, command="correction-2", content=b"corrected")
    assert read(source)["content"] == b"original"
    assert read(source, version=2)["content"] == b"corrected"
    assert collect(source) == retained
    assert (
        collect(source, command="collect-2", version=2)["source"]["sha256"]
        != retained["source"]["sha256"]
    )
    with sqlite3.connect(source.path) as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE versions SET content='replacement'")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("DELETE FROM collections")


def test_idempotency_conflicts_and_revocation(source):
    first = append(source)
    assert append(source) == first
    with pytest.raises(CompanyStoreError):
        append(source, content=b"different")
    with pytest.raises(CompanyStoreError):
        append(source, command="stale")
    source.grant("auditor", "E1", "SH", "clean", "IAM")
    collect(source)
    append(source, expected=1, command="second", content=b"second")
    with pytest.raises(CompanyStoreError):
        collect(source, version=2)
    source.grant("auditor", "E1", "SH", "clean", "IAM", active=False)
    with pytest.raises(CompanyStoreError):
        collect(source)
    with pytest.raises(CompanyStoreError):
        read(source)


def test_private_filesystem_and_input_fail_closed(tmp_path, source):
    alias = tmp_path / "alias"
    alias.symlink_to(source.path.parent, target_is_directory=True)
    with pytest.raises(CompanyStoreError):
        CompanyStore(alias)
    assert source.path.stat().st_mode & 0o077 == 0
    with pytest.raises(CompanyStoreError):
        source.register_system("SH", "clean", "IAM", "changed-owner")
    with pytest.raises(CompanyStoreError):
        append(source, expected=True)
    with pytest.raises(CompanyStoreError):
        source.grant("auditor", "E1", "SH", "clean", "missing")


def test_unknown_migration_date_and_discovery(source):
    append(source)
    append(source, expected=1, command="later", content=b"future", available="2028-01-01T00:00:00Z")
    source.append_version(
        "SH",
        "clean",
        "IAM",
        "EMP2",
        expected_version=0,
        command_id="migration",
        event_at=None,
        available_at="2027-01-01T00:00:00Z",
        content=b"old documentary source",
        provenance={"source_reference": "original-document"},
        origin="MIGRATED_SYNTHETIC_HISTORY",
    )
    with pytest.raises(CompanyStoreError):
        source.list_records("auditor", "E1", "SH", "clean", "IAM", as_of="2027-01-02T00:00:00Z")
    source.grant("auditor", "E1", "SH", "clean", "IAM")
    first = source.list_records(
        "auditor", "E1", "SH", "clean", "IAM", as_of="2027-01-02T00:00:00Z", limit=1
    )
    assert first["records"][0]["version"] == 1
    second = source.list_records(
        "auditor",
        "E1",
        "SH",
        "clean",
        "IAM",
        as_of="2027-01-02T00:00:00Z",
        after_record=first["next_after_record"],
    )
    assert second["records"][0]["event_at"] is None
    assert second["next_after_record"] is None
    with pytest.raises(CompanyStoreError):
        source.append_version(
            "SH",
            "clean",
            "IAM",
            "EMP3",
            expected_version=0,
            command_id="invalid-null",
            event_at=None,
            available_at="2027-01-01T00:00:00Z",
            content=b"new",
            provenance={"source_reference": "invalid"},
        )


def test_concurrent_correction_has_one_winner_and_replay_survives_reopen(source):
    from concurrent.futures import ThreadPoolExecutor

    append(source)

    def attempt(command):
        try:
            return append(source, expected=1, command=command, content=command.encode())
        except CompanyStoreError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, ["correction-a", "correction-b"]))
    assert sum(x is not None for x in outcomes) == 1
    reopened = CompanyStore(source.path.parent)
    assert append(reopened)["version"] == 1
    source.grant("auditor", "E1", "SH", "clean", "IAM")
    assert read(reopened, version=2)["content"] in {b"correction-a", b"correction-b"}


def test_system_discovery_only_exact_active_grants(source):
    source.register_system("SH", "clean", "HR", "hr-owner")
    source.grant("auditor", "E1", "SH", "clean", "IAM")
    source.grant("other", "E1", "SH", "clean", "HR")
    source.grant("auditor", "E2", "SH", "clean", "HR")
    source.grant("auditor", "E1", "SH", "messy", "IAM")
    assert source.list_systems("auditor", "E1", "SH", "clean") == {
        "systems": [{"system": "IAM", "owner": "owner"}]
    }
    assert source.list_systems("auditor", "E1", "OTHER", "clean") == {"systems": []}
    source.grant("auditor", "E1", "SH", "clean", "IAM", active=False)
    assert source.list_systems("auditor", "E1", "SH", "clean") == {"systems": []}
