"""Independent checks of local security workflow denominator and state boundaries."""

import pytest

from enterprise.audit_suite import company_security_event_runtime as runtime
from enterprise.audit_suite.company_backup_runtime import database
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from tests.audit_suite.test_company_security_event_runtime import command, prepared
from tests.audit_suite.test_company_security_logging_activity import inputs


@pytest.fixture
def ready(tmp_path):
    logs, refs, args = prepared(tmp_path, inputs.__wrapped__(tmp_path))
    target = tmp_path / "runtime"
    initial = runtime.initialize(target, **args)
    return target, initial, logs, refs, args


def test_rehashed_current_state_cannot_create_unrecorded_intake(ready):
    target, initial, *_ = ready
    view = runtime.inspect(target, expected_runtime_sha256=initial["runtime_sha256"])
    state = view["state"]
    state["subjects"]["EVENT-1"] = {"intake_at": state["event_at"]}
    with database(target, True) as db:
        db.execute(
            "UPDATE security_state SET body=?,digest=? WHERE id=1",
            (encoded(state), sha(encoded(state))),
        )
    with pytest.raises(CompanyStoreError):
        runtime.inspect(target, expected_runtime_sha256=initial["runtime_sha256"])


def test_one_handled_subject_never_erases_independent_missing_population(ready):
    target, initial, *_ = ready
    before = runtime.inspect(target, expected_runtime_sha256=initial["runtime_sha256"])
    baseline, _ = command(target, initial, "RECONCILE", {}, 1)
    command(target, initial, "INTAKE", {"subject_id": "EVENT-1"}, 2)
    command(target, initial, "TRIAGE", {"subject_id": "EVENT-1"}, 3)
    with pytest.raises(CompanyStoreError):
        command(target, initial, "HANDOFF", {"subject_id": "EVENT-1", "person_id": "AS-P009"}, 4)
    command(target, initial, "HANDOFF", {"subject_id": "EVENT-1", "person_id": "AS-P007"}, 4)
    subject = before["declared_subjects"]["EVENT-1"]["source"]
    inspected, _ = command(
        target, initial, "RECORD_ACTION", {"subject_id": "EVENT-1", "source_pins": [subject]}, 5
    )
    assert inspected["outcome"]["company_remediation_performed"] is False
    final, replay = command(target, initial, "RECONCILE", {}, 6)
    assert final["outcome"]["missing_intake"] == sorted(
        set(before["declared_subjects"]) - {"EVENT-1"}
    )
    assert (
        final["outcome"]["declared_subject_count"]
        == baseline["outcome"]["declared_subject_count"]
        == 4
    )
    assert final["incident_closed"] is False
    unchanged = target.joinpath("company.sqlite3").read_bytes()
    assert runtime.execute(target, **replay) == final
    assert target.joinpath("company.sqlite3").read_bytes() == unchanged
    with database(target) as db:
        for table in ("grants", "collections", "access_events"):
            assert db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
        original = db.execute(
            "SELECT content FROM versions WHERE system='security_event_reconciliation' "
            "ORDER BY event_at LIMIT 1"
        ).fetchone()[0]
        assert encoded(baseline["outcome"]["missing_intake"]) in original


def test_technical_read_of_unrelated_original_is_not_subject_inspection(ready):
    target, initial, *_ = ready
    view = runtime.inspect(target, expected_runtime_sha256=initial["runtime_sha256"])
    command(target, initial, "INTAKE", {"subject_id": "EVENT-1"}, 1)
    command(target, initial, "TRIAGE", {"subject_id": "EVENT-1"}, 2)
    command(target, initial, "HANDOFF", {"subject_id": "EVENT-1", "person_id": "AS-P007"}, 3)
    before = target.joinpath("company.sqlite3").read_bytes()
    other = view["declared_subjects"]["EVENT-2"]["source"]
    with pytest.raises(CompanyStoreError, match="subject original"):
        command(
            target, initial, "RECORD_ACTION", {"subject_id": "EVENT-1", "source_pins": [other]}, 4
        )
    assert target.joinpath("company.sqlite3").read_bytes() == before


def test_action_clock_bounds_and_offset_equivalent_replay(ready):
    target, initial, *_ = ready
    before = target.joinpath("company.sqlite3").read_bytes()
    for clock in ("2027-02-01T23:59:59Z", "2027-03-01T00:00:00Z"):
        with pytest.raises(CompanyStoreError):
            command(target, initial, "INTAKE", {"subject_id": "EVENT-1"}, 1, event_at=clock)
        assert target.joinpath("company.sqlite3").read_bytes() == before
    result, replay = command(
        target, initial, "INTAKE", {"subject_id": "EVENT-1"}, 1, event_at="2027-02-02T01:01:00Z"
    )
    stable = target.joinpath("company.sqlite3").read_bytes()
    assert runtime.execute(target, **{**replay, "event_at": "2027-02-01T18:01:00-07:00"}) == result
    assert target.joinpath("company.sqlite3").read_bytes() == stable
