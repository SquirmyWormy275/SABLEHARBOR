from copy import deepcopy

import pytest

from enterprise.audit_suite import company_operating_period as period
from enterprise.audit_suite.company_activity import generate_pair
from enterprise.audit_suite.company_lifecycle_activity import (
    FIELDS,
    LifecycleSourceRef,
    read_inputs,
)
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.organization import snapshot
from tests.audit_suite.test_company_activity import ROOT, recipe


@pytest.fixture
def setup(tmp_path):
    source = tmp_path / "source"
    ledger = tmp_path / "ledger"
    source.mkdir(mode=0o700)
    ledger.mkdir(mode=0o700)
    native, store = CompanyStore(source), CompanyStore(ledger)
    generate_pair(native, repository=ROOT, recipe=recipe())
    with native._db() as db:
        rows = db.execute(
            "SELECT * FROM versions WHERE branch='activity-clean' "
            "AND system='application' ORDER BY version"
        ).fetchall()
    refs = [{k: row[k] for k in FIELDS} for row in rows]
    _, pin = read_inputs(source, tuple(LifecycleSourceRef(**ref) for ref in refs))
    owner = next(
        a
        for a in snapshot(ROOT, as_of="2027-01-01")["control_assignments"]
        if a["control_id"] == "SH-IAM-003"
    )["primary_person_id"]
    plan = {
        "period_id": "YEAR-2027",
        "company_id": "SH",
        "branch_id": "activity-clean",
        "owner_id": owner,
        "control_ids": ["SH-IAM-003"],
        "period_start": "2027-01-01T00:00:00Z",
        "period_end_exclusive": "2028-01-01T00:00:00Z",
        "declared_at": "2026-12-31T20:00:00Z",
        "inventory": [
            {
                "id": "LOCAL-APP",
                "description": "One local application exercise, not enterprise systems",
            }
        ],
        "local_basis": "Explicit two-occurrence test schedule; no corporate cadence inferred",
        "schedule": [
            {
                "id": "FIRST",
                "inventory_ids": ["LOCAL-APP"],
                "control_id": "SH-IAM-003",
                "window_start": "2027-04-01T00:00:00Z",
                "window_end_exclusive": "2027-05-01T00:00:00Z",
                "due_at": "2027-04-16T00:00:00Z",
                "depends_on": [],
            },
            {
                "id": "NEXT",
                "inventory_ids": ["LOCAL-APP"],
                "control_id": "SH-IAM-003",
                "window_start": "2027-05-01T00:00:00Z",
                "window_end_exclusive": "2027-06-01T00:00:00Z",
                "due_at": "2027-05-16T00:00:00Z",
                "depends_on": ["FIRST"],
            },
        ],
    }
    group = {
        "source_store_id": "application-native",
        "root": str(source),
        "refs": refs,
        "expected_metadata_sha256": pin,
    }
    return store, native, plan, group


def action(group, **changes):
    value = dict(
        period_id="YEAR-2027",
        occurrence_id="FIRST",
        expected_version=0,
        command_id="FIRST-1",
        recorded_at="2027-04-16T00:00:00Z",
        disposition="EXECUTED",
        sources=[group],
        reason="Operator records this pinned local source assertion",
        predecessor_refs=[],
    )
    return value | changes


def test_independent_due_ledger_preserves_skip_late_source_and_replay(setup):
    store, native, plan, group = setup
    original = native.path.read_bytes()
    period.create_period(store, repository=ROOT, plan=plan)
    before = period.report_period(store, period_id="YEAR-2027", as_of="2027-04-15T23:59:59Z")
    assert before["due_count"] == before["missing_due_count"] == 0
    due = period.report_period(store, period_id="YEAR-2027", as_of="2027-04-15T17:00:00-07:00")
    assert due["due_count"] == due["missing_due_count"] == 1
    skip = action(
        group, sources=[], disposition="SKIPPED", reason="Explicit locally missed occurrence"
    )
    period.record_occurrence(store, **skip)
    late = action(
        group, expected_version=1, command_id="FIRST-2", recorded_at="2027-04-17T00:00:00Z"
    )
    receipt = period.record_occurrence(store, **late)
    assert period.record_occurrence(store, **late) == receipt
    report = period.report_period(store, period_id="YEAR-2027", as_of="2027-07-01T00:00:00Z")
    assert report["missing_due_count"] == 1
    history = report["occurrences"][0]["history"]
    assert [h["disposition"] for h in history] == ["SKIPPED", "EXECUTED"]
    assert history[-1]["recording_timeliness"] == "AFTER_DUE"
    assert report["operation_execution"] == "NOT_PERFORMED_BY_LEDGER"
    assert report["whole_company_year"] == "NOT_ESTABLISHED"
    assert str(native.path.parent) not in str(history)
    assert native.path.read_bytes() == original
    with store._db() as db:
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0


def test_exact_dependency_requires_current_version_but_old_history_stays(setup):
    store, _, plan, group = setup
    period.create_period(store, repository=ROOT, plan=plan)
    first = period.record_occurrence(store, **action(group))
    dep = {"occurrence_id": "FIRST", "version": first["version"], "sha256": first["sha256"]}
    next_action = action(
        group,
        occurrence_id="NEXT",
        command_id="NEXT-1",
        recorded_at="2027-05-10T00:00:00Z",
        predecessor_refs=[dep],
    )
    period.record_occurrence(store, **next_action)
    period.record_occurrence(
        store,
        **action(
            group,
            expected_version=1,
            command_id="FIRST-2",
            recorded_at="2027-05-11T00:00:00Z",
            reason="Later explicit correction",
        ),
    )
    # Historical exact retry remains historical; a NEW assertion cannot select the stale parent.
    assert period.record_occurrence(store, **next_action)["version"] == 1
    with pytest.raises(CompanyStoreError, match="Stale predecessor"):
        period.record_occurrence(
            store,
            **(
                next_action
                | {
                    "expected_version": 1,
                    "command_id": "NEXT-2",
                    "recorded_at": "2027-05-12T00:00:00Z",
                }
            ),
        )
    report = period.report_period(store, period_id="YEAR-2027", as_of="2027-06-01T00:00:00Z")
    assert report["occurrences"][1]["history"][0]["predecessor_refs"] == [dep]


@pytest.mark.parametrize(
    "fault",
    [
        "branch",
        "hash",
        "metadata",
        "future",
        "bool_version",
        "duplicate",
        "missing_dependency",
        "stale",
        "changed_replay",
    ],
)
def test_failed_capture_does_not_append(setup, fault):
    store, _, plan, group = setup
    period.create_period(store, repository=ROOT, plan=plan)
    value = action(deepcopy(group))
    if fault == "branch":
        value["sources"][0]["refs"][0]["branch"] = "activity-messy"
    elif fault == "hash":
        value["sources"][0]["refs"][0]["sha256"] = "f" * 64
    elif fault == "metadata":
        value["sources"][0]["expected_metadata_sha256"] = "f" * 64
    elif fault == "future":
        value["recorded_at"] = "2027-04-15T00:00:00Z"
    elif fault == "bool_version":
        value["sources"][0]["refs"][0]["version"] = True
    elif fault == "duplicate":
        value["sources"] *= 2
    elif fault == "missing_dependency":
        value.update(occurrence_id="NEXT", recorded_at="2027-05-02T00:00:00Z")
    elif fault == "stale":
        value["expected_version"] = 1
    elif fault == "changed_replay":
        period.record_occurrence(store, **value)
        value["reason"] = "Changed original command"
    original = store.path.read_bytes()
    with pytest.raises(CompanyStoreError):
        period.record_occurrence(store, **value)
    assert store.path.read_bytes() == original


@pytest.mark.parametrize(
    "fault",
    ["duplicate_slot", "undeclared_inventory", "inverted", "future_declaration", "unknown_control"],
)
def test_invalid_schedule_leaves_empty_store(setup, fault):
    store, _, plan, _ = setup
    if fault == "duplicate_slot":
        plan["schedule"].append(deepcopy(plan["schedule"][0]))
    elif fault == "undeclared_inventory":
        plan["schedule"][0]["inventory_ids"] = ["OTHER"]
    elif fault == "inverted":
        plan["schedule"][0]["window_start"] = "2027-06-01T00:00:00Z"
    elif fault == "future_declaration":
        plan["declared_at"] = "2027-01-02T00:00:00Z"
    elif fault == "unknown_control":
        plan["control_ids"] = ["SH-UNKNOWN-001"]
        for slot in plan["schedule"]:
            slot["control_id"] = "SH-UNKNOWN-001"
    with pytest.raises(CompanyStoreError):
        period.create_period(store, repository=ROOT, plan=plan)
    with store._db() as db:
        assert db.execute("SELECT COUNT(*) FROM systems").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 0


def test_source_revalidation_failure_preserves_ledger(setup, monkeypatch):
    store, _, plan, group = setup
    period.create_period(store, repository=ROOT, plan=plan)
    original = store.path.read_bytes()
    read = period.read_inputs
    calls = 0

    def changed(*args):
        nonlocal calls
        calls += 1
        rows, pin = read(*args)
        return rows, ("f" * 64 if calls == 2 else pin)

    monkeypatch.setattr(period, "read_inputs", changed)
    with pytest.raises(CompanyStoreError, match="metadata pin"):
        period.record_occurrence(store, **action(group))
    assert calls == 2
    assert store.path.read_bytes() == original


def test_writer_lock_rejects_concurrent_occurrence_attempt(setup, monkeypatch):
    store, _, plan, group = setup
    period.create_period(store, repository=ROOT, plan=plan)
    read = period.read_inputs
    attempts = []

    def overlapping(*args):
        with pytest.raises(CompanyStoreError, match="writer is busy"):
            period.record_occurrence(store, **action(group, command_id="CONCURRENT"))
        attempts.append(True)
        return read(*args)

    monkeypatch.setattr(period, "read_inputs", overlapping)
    period.record_occurrence(store, **action(group))
    assert len(attempts) == 2
    with store._db() as db:
        assert db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 2


@pytest.mark.parametrize(
    "raw", [b'{"x":1,"x":2}', b'{"x":{"y":1,"y":2}}', b'{"x":NaN}', b'{"x":1e999}', b"[]"]
)
def test_ledger_parser_rejects_ambiguous_or_nonfinite_hashed_original(raw):
    with pytest.raises(CompanyStoreError):
        period._body({"content": raw, "sha256": period.sha(raw)})


def test_declaration_rejects_maintained_source_change_before_mutation(setup, monkeypatch):
    store, _, plan, _ = setup
    original = period._module_pins
    calls = 0

    def changed(repository):
        nonlocal calls
        calls += 1
        pins = original(repository)
        if calls == 2:
            pins["enterprise/audit_suite/company_operating_period.py"] = "f" * 64
        return pins

    monkeypatch.setattr(period, "_module_pins", changed)
    before = store.path.read_bytes()
    with pytest.raises(CompanyStoreError, match="Maintained source changed"):
        period.create_period(store, repository=ROOT, plan=plan)
    assert store.path.read_bytes() == before
