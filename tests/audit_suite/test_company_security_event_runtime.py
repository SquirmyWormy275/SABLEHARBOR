from dataclasses import replace
from pathlib import Path

import pytest

from enterprise.audit_suite import company_security_event_runtime as runtime
from enterprise.audit_suite.company_security_logging_activity import generate_pair
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from tests.audit_suite.test_company_security_logging_activity import inputs as inputs

ROOT = Path(__file__).resolve().parents[2]


def prepared(tmp_path, inputs, prevented=False):
    source, recipe = inputs
    if prevented:
        recipe = replace(recipe, source_branch="release-a", source_scenario="BLOCKED_THEN_ALLOWED")
    logs = tmp_path / ("log-a" if prevented else "log-b")
    generate_pair(logs, repository=ROOT, source_root=source, recipe=recipe)
    branch = recipe.complete_branch if prevented else recipe.omission_branch
    store = CompanyStore(logs)
    with store._db() as db:
        refs = [
            runtime._pin(dict(r))
            for r in db.execute("SELECT * FROM versions WHERE branch=?", (branch,))
        ]
    at = "2027-02-02T00:00:00Z"
    _, metadata = runtime.read_sources(logs, refs, at)
    return (
        logs,
        refs,
        dict(
            repository=ROOT,
            source_root=logs,
            source_pins=refs,
            expected_source_metadata_sha256=metadata,
            as_of=at,
            runtime_id="local-security-response",
            period_start="2027-02-01T00:00:00Z",
            period_end="2027-03-01T00:00:00Z",
            local_rules=dict(runtime.RULES),
        ),
    )


def command(root, initial, action, payload, number=1, **overrides):
    current = runtime.inspect(root, expected_runtime_sha256=initial["runtime_sha256"])
    args = dict(
        expected_runtime_sha256=initial["runtime_sha256"],
        expected_revision=current["state"]["revision"],
        expected_state_sha256=current["state_sha256"],
        command_id=f"COMMAND-{number}",
        operator_id="AS-P008",
        event_at=f"2027-02-02T01:{number:02}:00Z",
        action=action,
        payload=payload,
    )
    args.update(overrides)
    return runtime.execute(root, **args), args


@pytest.mark.parametrize("prevented", [False, True])
def test_native_denominator_transitions_and_preserved_sources(tmp_path, inputs, prevented):
    logs, refs, args = prepared(tmp_path, inputs, prevented)
    before = (logs / "company.sqlite3").read_bytes()
    target = tmp_path / "runtime"
    initial = runtime.initialize(target, **args)
    view = runtime.inspect(target, expected_runtime_sha256=initial["runtime_sha256"])
    assert view["state"]["subjects"] == {}
    first, replay = command(target, initial, "RECONCILE", {}, 1)
    assert len(first["outcome"]["missing_intake"]) == (3 if prevented else 4)
    assert runtime.execute(target, **replay) == first
    command(target, initial, "INTAKE", {"subject_id": "EVENT-1"}, 2)
    triage, _ = command(target, initial, "TRIAGE", {"subject_id": "EVENT-1"}, 3)
    assert triage["outcome"]["classification"] == (
        "INFORMATIONAL" if prevented else "LOCAL_RESPONSE_REQUIRED"
    )
    if prevented:
        with pytest.raises(CompanyStoreError, match="Required local response"):
            command(
                target, initial, "HANDOFF", {"subject_id": "EVENT-1", "person_id": "AS-P007"}, 4
            )
    else:
        gap, _ = command(target, initial, "RECONCILE", {}, 4)
        assert gap["outcome"]["missing_handoff"] == ["EVENT-1"]
        command(target, initial, "HANDOFF", {"subject_id": "EVENT-1", "person_id": "AS-P007"}, 5)
        source = view["declared_subjects"]["EVENT-1"]["source"]
        result, _ = command(
            target, initial, "RECORD_ACTION", {"subject_id": "EVENT-1", "source_pins": [source]}, 6
        )
        assert result["outcome"]["company_remediation_performed"] is False
        assert result["incident_closed"] is False
    assert (logs / "company.sqlite3").read_bytes() == before
    with CompanyStore(target)._db() as db:
        assert db.execute("SELECT count(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM collections").fetchone()[0] == 0
        old = db.execute(
            "SELECT content FROM versions WHERE system='security_event_reconciliation' "
            "ORDER BY event_at LIMIT 1"
        ).fetchone()[0]
        assert b'"missing_intake":["ALERT-' in old


def test_source_pin_missing_future_and_output_boundary(tmp_path, inputs):
    logs, refs, args = prepared(tmp_path, inputs)
    for changes, message in [
        ({"source_pins": refs[:-1]}, "Complete declared"),
        ({"as_of": "2027-02-01T01:00:00Z"}, "Future"),
        ({"expected_source_metadata_sha256": "0" * 64}, "metadata"),
    ]:
        destination = tmp_path / "denied"
        with pytest.raises(CompanyStoreError, match=message):
            runtime.initialize(destination, **(args | changes))
        assert not destination.exists()
    with pytest.raises(CompanyStoreError, match="separate"):
        runtime.initialize(logs / "nested", **args)


def test_conflicts_authority_and_rollback(tmp_path, inputs, monkeypatch):
    _, _, args = prepared(tmp_path, inputs)
    target = tmp_path / "runtime"
    initial = runtime.initialize(target, **args)
    _, replay = command(target, initial, "INTAKE", {"subject_id": "EVENT-1"})
    with pytest.raises(CompanyStoreError, match="replay"):
        runtime.execute(target, **(replay | {"payload": {"subject_id": "EVENT-2"}}))
    with pytest.raises(CompanyStoreError, match="conflict"):
        runtime.execute(target, **(replay | {"command_id": "NEW"}))
    with pytest.raises(CompanyStoreError, match="Scoped local"):
        command(target, initial, "TRIAGE", {"subject_id": "EVENT-1"}, 2, operator_id="AS-P007")
    before = (target / "company.sqlite3").read_bytes()
    insert = runtime._insert

    def fail(db, cfg, system, *other):
        if system == "security_event_state":
            raise RuntimeError("injected failure")
        return insert(db, cfg, system, *other)

    monkeypatch.setattr(runtime, "_insert", fail)
    with pytest.raises(RuntimeError, match="injected"):
        command(target, initial, "TRIAGE", {"subject_id": "EVENT-1"}, 2)
    assert (target / "company.sqlite3").read_bytes() == before
    monkeypatch.setattr(runtime, "_insert", insert)
    result, _ = command(target, initial, "TRIAGE", {"subject_id": "EVENT-1"}, 2)
    assert result["revision"] == 2


@pytest.mark.parametrize(
    "mutation", ["sequence_bool", "gate_decision", "missing_alert", "late_ack"]
)
def test_repinned_native_semantics_rejected(tmp_path, inputs, mutation):
    _, _, args = prepared(tmp_path, inputs)
    rows, _ = runtime.read_sources(args["source_root"], args["source_pins"], args["as_of"])
    # Pure validator receives newly pinned native bytes, not just a stale digest mismatch.
    if mutation == "missing_alert":
        rows = [
            r
            for r in rows
            if not (r["system"] == "detection_alerts" and r["record"] == "AUTH-ALERT-1")
        ]
    else:
        system = {
            "sequence_bool": "publisher_events",
            "gate_decision": "publisher_originals",
            "late_ack": "response_tickets",
        }[mutation]
        row = next(
            r
            for r in rows
            if r["system"] == system
            and (mutation != "gate_decision" or r["record"] == "GATE-PROPOSED")
        )
        body = runtime.decode(row["content"])
        if mutation == "sequence_bool":
            body["event"]["sequence"] = True
        elif mutation == "gate_decision":
            body["decision"] = "ALLOWED"
        else:
            row["event_at"] = "2027-01-01T00:00:00.000000+00:00"
        row["content"] = runtime.encoded(body)
        row["sha256"] = runtime.sha(row["content"])
    with pytest.raises(CompanyStoreError):
        runtime._validate(rows)


def test_private_source_and_final_source_race(tmp_path, inputs, monkeypatch):
    logs, _, args = prepared(tmp_path, inputs)
    db = logs / "company.sqlite3"
    db.chmod(0o644)
    with pytest.raises(CompanyStoreError):
        runtime.initialize(tmp_path / "denied", **args)
    db.chmod(0o600)
    real = runtime.read_sources
    count = 0

    def changed(*values):
        nonlocal count
        count += 1
        rows, pin = real(*values)
        return rows, ("0" * 64 if count > 1 else pin)

    monkeypatch.setattr(runtime, "read_sources", changed)
    with pytest.raises(CompanyStoreError, match="Source changed"):
        runtime.initialize(tmp_path / "raced", **args)
    assert not (tmp_path / "raced").exists()
