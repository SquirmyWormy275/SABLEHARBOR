"""Verified native policy prefix replay, preserving the strict current inspector."""

import pytest

from enterprise.audit_suite import company_operating_depth_runtime as depth
from enterprise.audit_suite import company_policy_delivery_runtime as policy
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError, _time
from enterprise.audit_suite.operating_source_bridge import sha
from tests.audit_suite.test_precise_operating_due_offset import (
    DUE,
    LATE,
)
from tests.audit_suite.test_precise_operating_due_offset import (
    test_real_native_policy_15hour_due_missing_late_receipts_and_typed_collection as source_case,
)


@pytest.fixture
def completed(tmp_path):
    source_case(tmp_path)
    source = CompanyStore(tmp_path / "source")
    runtime = tmp_path / "policy"
    config_sha = sha((runtime / "RUNTIME.json").read_bytes())
    with source._db() as db:
        definition = depth.pin(
            dict(
                db.execute(
                    "SELECT * FROM versions WHERE system='operating_depth_definition'"
                ).fetchone()
            )
        )
        original = dict(
            db.execute("SELECT * FROM versions WHERE command_id='OWN-BIND-DUE'").fetchone()
        )
    return source, runtime, config_sha, definition, original


def test_historical_cutoff_and_idempotent_prior_binding_after_late_delivery(completed):
    source, runtime, config_sha, definition, original = completed
    before = source.path.read_bytes()
    with pytest.raises(CompanyStoreError, match="Current state unavailable"):
        policy.inspect(runtime, expected_runtime_sha256=config_sha, as_of=DUE)
    initial = policy.inspect_at(
        runtime, expected_runtime_sha256=config_sha, as_of="2027-11-01T09:05:00Z"
    )
    assert initial["revision"] == 0
    timely = policy.inspect_at(
        runtime, expected_runtime_sha256=config_sha, as_of="2027-11-01T09:10:00Z"
    )
    assert timely["revision"] == 2
    due = policy.inspect_at(runtime, expected_runtime_sha256=config_sha, as_of=DUE)
    assert due["revision"] == 2
    missing = next(r for r in due["report"]["recipients"] if r["recipient_id"] == "AS-P014")
    assert missing["delivery_status"] == "MISSING_DUE"
    late = policy.inspect_at(runtime, expected_runtime_sha256=config_sha, as_of=LATE)
    assert late["revision"] == 4
    corrected = next(r for r in late["report"]["recipients"] if r["recipient_id"] == "AS-P014")
    assert corrected["late"] is True
    assert corrected["read_return_current_delivery"] is True
    assert (
        policy.inspect(runtime, expected_runtime_sha256=config_sha, as_of=LATE)["report"]
        == late["report"]
    )
    replay = depth.policy_binding(
        source,
        declaration_pin=definition,
        slot_id="NOVEMBER:0",
        runtime_root=runtime,
        runtime_sha256=config_sha,
        actor_id="AS-P005",
        command_id="OWN-BIND-DUE",
        event_at=DUE,
    )
    assert depth.pin(replay) == depth.pin(original)
    assert source.path.read_bytes() == before
    body = depth.decode(original["content"])
    assert (
        body["observation"]["policy_state_basis"]
        == "FRESH_VERIFIED_NATIVE_OPERATION_PREFIX_AT_EXACT_CUTOFF"
    )
    with source._db() as db:
        assert (
            db.execute("SELECT COUNT(*) FROM versions WHERE system=?", (depth.SYSTEM,)).fetchone()[
                0
            ]
            == 2
        )
    # Only actual operation originals available by this cutoff can be bound.
    for p in body["observation"]["native_refs"]:
        if p["system"] == "policy_operation":
            with policy.database(runtime) as db:
                row = policy.native(db, p, DUE)
                assert _time(row["event_at"]) <= DUE


@pytest.mark.parametrize("fault", ["late_mailbox", "late_observation", "current_projection"])
def test_future_chain_tamper_refuses_past_prefix_and_appends_nothing(completed, fault):
    source, runtime, config_sha, definition, _ = completed
    if fault == "late_mailbox":
        path = runtime / "attempts" / sha(b"OWN-LATE-DELIVER") / "copied.bin"
        raw = path.read_bytes()
        path.write_bytes(b"X" * len(raw))
    else:
        with policy.database(runtime, True) as db:
            if fault == "late_observation":
                db.execute("DROP TRIGGER policy_no_update")
                row = db.execute("SELECT * FROM policy_commands WHERE revision=4").fetchone()
                receipt = depth.decode(row["receipt"])
                receipt["observation"]["receipt_counter_not_supported"] = True
                db.execute(
                    "UPDATE policy_commands SET receipt=? WHERE revision=4",
                    (policy.encoded(receipt),),
                )
            else:
                db.execute("UPDATE policy_state SET body=? WHERE id=1", (b"{}",))
    before = source.path.read_bytes()
    with pytest.raises(CompanyStoreError):
        policy.inspect_at(runtime, expected_runtime_sha256=config_sha, as_of=DUE)
    with pytest.raises(CompanyStoreError):
        depth.policy_binding(
            source,
            declaration_pin=definition,
            slot_id="NOVEMBER:0",
            runtime_root=runtime,
            runtime_sha256=config_sha,
            actor_id="AS-P005",
            command_id="MUST-NOT-APPEND",
            event_at=DUE,
            expected_version=2,
        )
    assert source.path.read_bytes() == before


@pytest.mark.parametrize("cutoff", [None, True, "2027-11-01T09:04:59Z"])
def test_explicit_historical_cutoff_cannot_precede_initial_native_runtime(completed, cutoff):
    _, runtime, config_sha, _, _ = completed
    with pytest.raises(CompanyStoreError):
        policy.inspect_at(runtime, expected_runtime_sha256=config_sha, as_of=cutoff)
