import json

import pytest

from enterprise.audit_suite.company_migration import (
    import_documentary_custody,
    plan_documentary_custody,
    plan_legacy_documents,
)
from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_migration import fixture


def setup(tmp_path):
    source = fixture(tmp_path)
    first = tmp_path / "worlds" / "ENG-abc" / "unit-00000.json"
    second = json.loads(first.read_bytes())
    second["control_id"] = "CONTROL-2"
    second["requests"][0]["id"] = "REQ-2"
    second["requests"][0]["prepared_artifacts"][0]["id"] = "ART-2"
    (first.parent / "unit-00001.json").write_text(json.dumps(second))
    state = {
        "id": "ENG-abc",
        "scope": {"boundaries": ["corporate"]},
        "organization": {"snapshot_digest": "a" * 64},
        "controls": [
            {"id": f"CONTROL-{i}", "assignment": {"primary_person_id": f"P{i}"}} for i in (1, 2)
        ],
        "people": [{"id": "P1"}, {"id": "P2"}],
    }
    legacy = plan_legacy_documents(tmp_path, "ENG-abc")
    owners = {"CONTROL-1": "P1", "CONTROL-2": "P2"}
    plan = plan_documentary_custody(
        tmp_path,
        legacy,
        scoped_state=state,
        company_id="SH",
        branch_id="documentary",
        owner_ids=owners,
    )
    output = tmp_path / "private-output"
    output.mkdir(mode=0o700)
    return source, state, legacy, owners, plan, output


def test_two_control_archives_original_bytes_unknown_events_and_no_grants(tmp_path):
    source, state, legacy, owners, plan, output = setup(tmp_path)
    original = source.read_bytes()
    result = import_documentary_custody(
        tmp_path, plan, scoped_state=state, destination=output / "new"
    )
    assert result["archive_count"] == result["document_count"] == 2
    assert "HIDDEN" not in json.dumps(plan)
    assert result["access_grants"] == "NONE"
    store = CompanyStore(output / "new")
    with store._db() as db:
        assert db.execute("SELECT count(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM access_events").fetchone()[0] == 0
        systems = list(db.execute("SELECT * FROM systems"))
        assert {r["owner"] for r in systems} == {"P1", "P2"}
        rows = list(db.execute("SELECT * FROM versions"))
        for row in rows:
            assert row["content"] == original
            assert row["event_at"] is None
            assert row["imported_at"] != row["available_at"]
            assert row["origin"] == "MIGRATED_SYNTHETIC_HISTORY"
            provenance = json.loads(row["provenance"])
            assert provenance["custody_status"] == "PROVISIONAL_DOCUMENTARY_CUSTODY"
            assert provenance["operational_fact_status"] == "REQUIRES_SOURCE_RECONCILIATION"
            assert provenance["custodian_person_id"] == owners[provenance["control_id"]]
    assert source.read_bytes() == original
    with pytest.raises(DomainError, match="New documentary"):
        import_documentary_custody(tmp_path, plan, scoped_state=state, destination=output / "new")


@pytest.mark.parametrize(
    "owners",
    [
        {"CONTROL-1": "P1"},
        {"CONTROL-1": "P2", "CONTROL-2": "P1"},
        {"CONTROL-1": "P1", "CONTROL-2": "UNKNOWN"},
        {"CONTROL-1": "P1", "CONTROL-2": "P2", "EXTRA": "P1"},
    ],
)
def test_incomplete_crossowner_unknown_and_extra_mapping_rejected(tmp_path, owners):
    _, state, legacy, _, _, _ = setup(tmp_path)
    with pytest.raises(DomainError):
        plan_documentary_custody(
            tmp_path,
            legacy,
            scoped_state=state,
            company_id="SH",
            branch_id="documentary",
            owner_ids=owners,
        )


def test_changed_owner_or_original_fails_before_publishing(tmp_path):
    source, state, legacy, owners, plan, output = setup(tmp_path)
    state["controls"][0]["assignment"]["primary_person_id"] = "P2"
    with pytest.raises(DomainError, match="actual scoped"):
        import_documentary_custody(tmp_path, plan, scoped_state=state, destination=output / "new")
    assert not (output / "new").exists()
    state["controls"][0]["assignment"]["primary_person_id"] = "P1"
    source.write_bytes(b"changed")
    with pytest.raises(DomainError, match="integrity"):
        import_documentary_custody(tmp_path, plan, scoped_state=state, destination=output / "new")
    assert not (output / "new").exists()


def test_import_failure_leaves_no_published_store(tmp_path, monkeypatch):
    _, state, _, _, plan, output = setup(tmp_path)
    original = CompanyStore.append_version
    calls = []

    def fail_second(self, *args, **kwargs):
        calls.append(1)
        if len(calls) == 2:
            raise RuntimeError("simulated storage failure")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(CompanyStore, "append_version", fail_second)
    with pytest.raises(RuntimeError, match="storage failure"):
        import_documentary_custody(tmp_path, plan, scoped_state=state, destination=output / "new")
    assert not (output / "new").exists()
    assert list(output.iterdir()) == []


def test_failed_final_publication_retains_legacy_and_retry_succeeds(tmp_path, monkeypatch):
    from enterprise.audit_suite import private_publication

    source, state, _, _, plan, output = setup(tmp_path)
    original = source.read_bytes()
    destination = output / "retryable"
    rename = private_publication.os.rename
    moved = []

    def fail_second(source_path, target):
        if target.parent == destination:
            moved.append(target)
            if len(moved) == 2:
                raise OSError("publication unavailable")
        return rename(source_path, target)

    with monkeypatch.context() as patch:
        patch.setattr(private_publication.os, "rename", fail_second)
        with pytest.raises(OSError, match="publication unavailable"):
            import_documentary_custody(tmp_path, plan, scoped_state=state, destination=destination)
    assert not destination.exists()
    assert source.read_bytes() == original
    assert (
        import_documentary_custody(tmp_path, plan, scoped_state=state, destination=destination)[
            "document_count"
        ]
        == 2
    )
