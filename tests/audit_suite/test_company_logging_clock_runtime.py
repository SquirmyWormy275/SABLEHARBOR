from datetime import datetime, timedelta
from pathlib import Path

import pytest

from enterprise.audit_suite.company_change_activity import (
    ChangeRecipe,
)
from enterprise.audit_suite.company_change_activity import (
    generate_pair as change_pair,
)
from enterprise.audit_suite.company_configuration_activity import read_originals
from enterprise.audit_suite.company_logging_clock_runtime import (
    create_clock_runtime,
    read_native,
    record_clock_observation,
    record_missed_observation,
)
from enterprise.audit_suite.company_security_logging_activity import (
    LoggingRecipe,
)
from enterprise.audit_suite.company_security_logging_activity import (
    generate_pair as logging_pair,
)
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded

ROOT = Path(__file__).resolve().parents[2]
DUE = "2027-02-01T06:01:00Z"
CONTRACT_AT = "2027-02-01T06:00:10Z"


def pin(row):
    return {
        k: row[k]
        for k in ("company", "branch", "system", "record", "version", "sha256", "available_at")
    }


def native(root, branch, system, record, at, body, owner="AS-P008"):
    store = CompanyStore(root)
    store.register_system("SH", branch, system, owner)
    return pin(
        store.append_version(
            "SH",
            branch,
            system,
            record,
            expected_version=0,
            command_id=f"SOURCE-{branch}-{system}-{record}",
            event_at=at,
            available_at=at,
            content=encoded(body),
            provenance={"source_reference": record},
        )
    )


@pytest.fixture
def context(tmp_path):
    tmp_path.chmod(0o700)
    change_root = tmp_path / "change"
    change_pair(
        change_root,
        repository=ROOT,
        recipe=ChangeRecipe(
            "SH",
            "release-a",
            "release-b",
            "CYCLE",
            "2027-02-01T00:00:00Z",
            "2027-02-03T00:00:00Z",
            "Local reference release rule only",
        ),
    )
    _, change_pin = read_originals(change_root)
    logging_root = tmp_path / "logging"
    logging_pair(
        logging_root,
        repository=ROOT,
        source_root=change_root,
        recipe=LoggingRecipe(
            "SH",
            "change-original",
            change_pin,
            "release-b",
            "logging-a",
            "logging-b",
            "LOCAL-RELEASE-AUTH",
        ),
    )
    with CompanyStore(logging_root)._db() as db:
        inventory = pin(
            dict(
                db.execute(
                    "SELECT * FROM versions WHERE branch='logging-a' AND system='source_inventory'"
                ).fetchone()
            )
        )
    reference_root = tmp_path / "reference"
    reference_root.mkdir(mode=0o700)
    definition = native(
        reference_root,
        "clock-reference",
        "time_reference_definition",
        "REF-LOCAL",
        "2027-01-31T23:59:00Z",
        {
            "reference_id": "REF-LOCAL",
            "trust_status": "LOCAL_REFERENCE_DECLARED_NOT_ENTERPRISE_TRUST",
            "source_kind": "ISOLATED_FIXTURE_REFERENCE",
        },
    )
    runtime = tmp_path / "clock"
    contract = pin(
        create_clock_runtime(
            runtime,
            logging_root=logging_root,
            inventory_pin=inventory,
            reference_root=reference_root,
            reference_pin=definition,
            branch_id="clock-local",
            device_id="DEV-LOCAL",
            local_source_id="LOCAL-RELEASE-AUTH",
            actor_id="AS-P008",
            reviewer_id="AS-P007",
            threshold_ms=100,
            cadence_seconds=60,
            grace_seconds=30,
            period_start=DUE,
            slot_count=3,
            contract_at=CONTRACT_AT,
            rationale="Compare one declared local log source clock to an isolated reference",
            command_id="CLOCK-CONTRACT-1",
        )
    )
    device_root = tmp_path / "device"
    device_root.mkdir(mode=0o700)
    return locals()


def samples(ctx, index, offset_ms, *, offset_us=None, device_id="DEV-LOCAL", capture_id=None):
    due = datetime.fromisoformat(DUE.replace("Z", "+00:00")) + timedelta(minutes=index)
    stamp = due.isoformat()
    reference_time = due
    device_time = due + timedelta(microseconds=offset_ms * 1000 if offset_us is None else offset_us)
    capture = capture_id or f"CAPTURE-{index}"
    device_pin = native(
        ctx["device_root"],
        "clock-device",
        "device_clock_sample",
        f"DEVICE-{index}",
        stamp,
        {
            "device_id": device_id,
            "inventory_pin": ctx["inventory"],
            "local_source_id": "LOCAL-RELEASE-AUTH",
            "capture_id": capture,
            "slot_index": index,
            "sampled_at": stamp,
            "device_time": device_time.isoformat(),
            "ingestion_lag_seconds": 10000,
        },
    )
    reference_pin = native(
        ctx["reference_root"],
        "clock-reference",
        "time_reference_sample",
        f"REF-{index}",
        stamp,
        {
            "reference_id": "REF-LOCAL",
            "definition_pin": ctx["definition"],
            "capture_id": capture,
            "slot_index": index,
            "sampled_at": stamp,
            "reference_time": reference_time.isoformat(),
        },
    )
    return device_pin, reference_pin, due


def test_native_offset_alert_and_source_collection(context):
    c = context
    device_pin, reference_pin, due = samples(c, 0, 250)
    db_before = {
        root: (root / "company.sqlite3").read_bytes()
        for root in (c["logging_root"], c["device_root"], c["reference_root"])
    }
    args = dict(
        contract_pin=c["contract"],
        slot_index=0,
        device_root=c["device_root"],
        device_pin=device_pin,
        reference_root=c["reference_root"],
        reference_sample_pin=reference_pin,
        observed_at=(due + timedelta(seconds=5)).isoformat(),
        command_id="OBS-0",
    )
    receipt = record_clock_observation(c["runtime"], **args)
    assert record_clock_observation(c["runtime"], **args) == receipt
    body, _, _ = read_native(c["runtime"], pin(receipt))
    assert body["offset_ms"] == "250.000"
    assert body["offset_microseconds"] == 250000
    assert body["status"] == "OFFSET_THRESHOLD_EXCEEDED"
    assert body["alert_state"] == "OPEN_LOCAL_CLOCK_ALERT"
    assert body["alert_owner_id"] == "AS-P008"
    assert body["review_contact_id"] == "AS-P007"
    assert body["review_state"] == "PENDING_NOT_PERFORMED"
    assert body["reference_trust_status"] == "LOCAL_REFERENCE_DECLARED_NOT_ENTERPRISE_TRUST"
    assert body["device_pin"] == device_pin and body["reference_sample_pin"] == reference_pin
    assert all(
        (root / "company.sqlite3").read_bytes() == prior for root, prior in db_before.items()
    )
    store = CompanyStore(c["runtime"])
    store.grant("AUDITOR", "ENGAGEMENT", "SH", "clock-local", "clock_observation")
    collection = store.collect(
        "AUDITOR",
        "ENGAGEMENT",
        "SH",
        "clock-local",
        "clock_observation",
        "CLOCK-SLOT-0",
        version=1,
        as_of=(due + timedelta(seconds=5)).isoformat(),
        command_id="COLLECT-CLOCK-0",
    )
    assert collection["source"]["sha256"] == receipt["sha256"]
    assert store.read_version(
        "AUDITOR",
        "ENGAGEMENT",
        "SH",
        "clock-local",
        "clock_observation",
        "CLOCK-SLOT-0",
        version=1,
        as_of=(due + timedelta(seconds=5)).isoformat(),
    )["content"] == encoded(body)


def test_within_threshold_and_explicit_missed_slot(context):
    c = context
    device_pin, reference_pin, due = samples(c, 0, -50)
    within = record_clock_observation(
        c["runtime"],
        contract_pin=c["contract"],
        slot_index=0,
        device_root=c["device_root"],
        device_pin=device_pin,
        reference_root=c["reference_root"],
        reference_sample_pin=reference_pin,
        observed_at=(due + timedelta(seconds=1)).isoformat(),
        command_id="OBS-WITHIN",
    )
    body, _, _ = read_native(c["runtime"], pin(within))
    assert body["offset_ms"] == "-50.000" and body["alert_state"] == "NONE"
    missed = record_missed_observation(
        c["runtime"],
        contract_pin=c["contract"],
        slot_index=1,
        checked_at=(due + timedelta(seconds=91)).isoformat(),
        command_id="MISS-1",
    )
    absent, _, _ = read_native(c["runtime"], pin(missed))
    assert absent["offset_ms"] is None
    assert absent["offset_microseconds"] is None
    assert absent["status"] == "NO_SAMPLE_SUBMITTED_BY_LOCAL_DEADLINE"
    assert absent["alert_state"] == "OPEN_LOCAL_MISSED_OBSERVATION_ALERT"
    assert absent["review_state"] == "PENDING_NOT_PERFORMED"
    with pytest.raises(CompanyStoreError, match="Source version conflict"):
        record_missed_observation(
            c["runtime"],
            contract_pin=c["contract"],
            slot_index=0,
            checked_at=(due + timedelta(seconds=31)).isoformat(),
            command_id="MISS-CONFLICT",
        )


@pytest.mark.parametrize(
    ("offset_us", "expected_status", "expected_ms"),
    [
        (100000, "WITHIN_LOCAL_THRESHOLD", "100.000"),
        (100001, "OFFSET_THRESHOLD_EXCEEDED", "100.001"),
        (-100000, "WITHIN_LOCAL_THRESHOLD", "-100.000"),
        (-100001, "OFFSET_THRESHOLD_EXCEEDED", "-100.001"),
    ],
)
def test_exact_positive_negative_threshold_boundary(
    context, offset_us, expected_status, expected_ms
):
    c = context
    device_pin, reference_pin, due = samples(c, 0, 0, offset_us=offset_us)
    receipt = record_clock_observation(
        c["runtime"],
        contract_pin=c["contract"],
        slot_index=0,
        device_root=c["device_root"],
        device_pin=device_pin,
        reference_root=c["reference_root"],
        reference_sample_pin=reference_pin,
        observed_at=(due + timedelta(seconds=1)).isoformat(),
        command_id="EDGE-OBS",
    )
    body, _, _ = read_native(c["runtime"], pin(receipt))
    assert body["offset_microseconds"] == offset_us
    assert body["offset_ms"] == expected_ms
    assert body["status"] == expected_status


@pytest.mark.parametrize(
    "fault",
    [
        "wrong_device",
        "wrong_reference",
        "mismatch_capture",
        "wrong_slot",
        "late",
        "bad_pin",
        "premature",
    ],
)
def test_invalid_sample_fails_without_observation(context, fault):
    c = context
    device_pin, reference_pin, due = samples(
        c,
        0,
        250,
        device_id="OTHER" if fault == "wrong_device" else "DEV-LOCAL",
        capture_id="OTHER-CAPTURE" if fault == "mismatch_capture" else None,
    )
    if fault == "wrong_reference":
        reference_pin = native(
            c["reference_root"],
            "clock-reference",
            "time_reference_sample",
            "REF-OTHER",
            due.isoformat(),
            {
                "reference_id": "OTHER",
                "capture_id": "CAPTURE-0",
                "slot_index": 0,
                "sampled_at": due.isoformat(),
                "reference_time": due.isoformat(),
            },
        )
    if fault == "mismatch_capture":
        reference_pin = native(
            c["reference_root"],
            "clock-reference",
            "time_reference_sample",
            "REF-WRONG-CAPTURE",
            due.isoformat(),
            {
                "reference_id": "REF-LOCAL",
                "capture_id": "DIFFERENT-CAPTURE",
                "slot_index": 0,
                "sampled_at": due.isoformat(),
                "reference_time": due.isoformat(),
            },
        )
    if fault == "wrong_slot":
        reference_pin = native(
            c["reference_root"],
            "clock-reference",
            "time_reference_sample",
            "REF-WRONG-SLOT",
            due.isoformat(),
            {
                "reference_id": "REF-LOCAL",
                "capture_id": "CAPTURE-0",
                "slot_index": 1,
                "sampled_at": due.isoformat(),
                "reference_time": due.isoformat(),
            },
        )
    if fault == "bad_pin":
        device_pin = {**device_pin, "sha256": "0" * 64}
    if fault == "premature":
        device_pin = native(
            c["device_root"],
            "clock-device",
            "device_clock_sample",
            "DEVICE-PREMATURE",
            (due - timedelta(seconds=1)).isoformat(),
            {
                "device_id": "DEV-LOCAL",
                "local_source_id": "LOCAL-RELEASE-AUTH",
                "inventory_pin": c["inventory"],
                "capture_id": "CAPTURE-0",
                "slot_index": 0,
                "sampled_at": due.isoformat(),
                "device_time": (due + timedelta(milliseconds=250)).isoformat(),
            },
        )
    observed = due + timedelta(seconds=31 if fault == "late" else 1)
    with pytest.raises(CompanyStoreError):
        record_clock_observation(
            c["runtime"],
            contract_pin=c["contract"],
            slot_index=0,
            device_root=c["device_root"],
            device_pin=device_pin,
            reference_root=c["reference_root"],
            reference_sample_pin=reference_pin,
            observed_at=observed.isoformat(),
            command_id="OBS-FAIL",
        )
    with CompanyStore(c["runtime"])._db() as db:
        assert (
            db.execute("SELECT COUNT(*) FROM versions WHERE system='clock_observation'").fetchone()[
                0
            ]
            == 0
        )


def test_unapproved_reference_and_past_rule_rejected_before_runtime(context, tmp_path):
    c = context
    bad = native(
        c["reference_root"],
        "clock-reference",
        "time_reference_definition",
        "REF-BAD",
        "2027-01-31T23:59:00Z",
        {"reference_id": "REF-BAD", "trust_status": "ENTERPRISE_TRUSTED"},
    )
    kwargs = dict(
        logging_root=c["logging_root"],
        inventory_pin=c["inventory"],
        reference_root=c["reference_root"],
        reference_pin=bad,
        branch_id="clock-bad",
        device_id="DEV-LOCAL",
        local_source_id="LOCAL-RELEASE-AUTH",
        actor_id="AS-P008",
        reviewer_id="AS-P007",
        threshold_ms=100,
        cadence_seconds=60,
        grace_seconds=30,
        period_start=DUE,
        slot_count=1,
        contract_at=CONTRACT_AT,
        rationale="A local clock comparison rule for an isolated exercise",
        command_id="BAD-CONTRACT",
    )
    target = tmp_path / "rejected"
    with pytest.raises(CompanyStoreError):
        create_clock_runtime(target, **kwargs)
    assert not target.exists()
    with pytest.raises(CompanyStoreError, match="predate"):
        create_clock_runtime(
            target, **{**kwargs, "reference_pin": c["definition"], "contract_at": DUE}
        )
    assert not target.exists()
