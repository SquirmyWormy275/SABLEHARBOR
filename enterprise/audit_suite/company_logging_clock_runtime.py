"""Prospective, collectable local clock observations for a single logging source.

This trusted-operator companion never treats ingestion lag as clock offset. Reference
trust, thresholds and cadence are local contract inputs, not Security Operations
approval or evidence of deployed enterprise clock synchronization.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _id, _time
from .operating_source_bridge import encoded

QUALIFICATION = "LOCAL_CLOCK_COMPARISON_NOT_ENTERPRISE_SYNCHRONIZATION"
CONTROL = "SH-SEC-002"
PIN_FIELDS = ("company", "branch", "system", "record", "version", "sha256", "available_at")


def _require(condition, message):
    if not condition:
        raise CompanyStoreError(message)


def _stamp(value):
    return datetime.fromisoformat(_time(value))


def _offset_microseconds(device_time, reference_time):
    delta = _stamp(device_time) - _stamp(reference_time)
    return delta.days * 86_400_000_000 + delta.seconds * 1_000_000 + delta.microseconds


def _milliseconds_decimal(offset_microseconds):
    magnitude = abs(offset_microseconds)
    sign = "-" if offset_microseconds < 0 else ""
    return f"{sign}{magnitude // 1000}.{magnitude % 1000:03d}"


def _pin(pin):
    _require(
        isinstance(pin, dict) and set(pin) == set(PIN_FIELDS), "Exact native source pin required"
    )
    for key in PIN_FIELDS[:4]:
        _id(pin[key])
    _require(type(pin["version"]) is int and pin["version"] > 0, "Positive source version required")
    _require(
        isinstance(pin["sha256"], str)
        and len(pin["sha256"]) == 64
        and all(c in "0123456789abcdef" for c in pin["sha256"]),
        "SHA-256 source pin required",
    )
    _time(pin["available_at"])
    return dict(pin)


def read_native(root, pin):
    """Read exact original bytes without initializing or altering the source store."""
    pin = _pin(pin)
    path = Path(root).absolute() / "company.sqlite3"
    _require(
        path.is_file()
        and not any(p.is_symlink() for p in (path, *path.parents))
        and path.stat().st_nlink == 1
        and not path.stat().st_mode & 0o077
        and not path.parent.stat().st_mode & 0o077,
        "Existing private nonsymlink company source required",
    )
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA query_only=ON")
        row = db.execute(
            "SELECT company,branch,system,record,version,sha256,available_at,event_at,"
            "provenance,content "
            "FROM versions WHERE company=? AND branch=? AND system=? AND record=? AND version=?",
            tuple(pin[k] for k in PIN_FIELDS[:5]),
        ).fetchone()
    finally:
        db.close()
    _require(row is not None, "Pinned native source unavailable")
    _require(all(row[k] == pin[k] for k in PIN_FIELDS), "Pinned native source changed")
    _require(
        hashlib.sha256(row["content"]).hexdigest() == pin["sha256"],
        "Native source integrity failure",
    )
    try:
        body = json.loads(row["content"])
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CompanyStoreError("Native source JSON required") from error
    _require(isinstance(body, dict), "Native source object required")
    return body, row["event_at"], json.loads(row["provenance"])


def _emit(store, company, branch, system, record, at, body, *, command_id):
    return store.append_version(
        company,
        branch,
        system,
        record,
        expected_version=0,
        command_id=command_id,
        event_at=at,
        available_at=at,
        content=encoded(body),
        provenance={
            "source_reference": record,
            "control_ids": [CONTROL],
            "classification": QUALIFICATION,
            "operational_fact_status": "LOCAL_EXERCISE_ONLY",
        },
    )


def create_clock_runtime(
    destination,
    *,
    logging_root,
    inventory_pin,
    reference_root,
    reference_pin,
    branch_id,
    device_id,
    local_source_id,
    actor_id,
    reviewer_id,
    threshold_ms,
    cadence_seconds,
    grace_seconds,
    period_start,
    slot_count,
    contract_at,
    rationale,
    command_id,
):
    """Record a prospective local rule against two exact preexisting native sources."""
    destination = Path(destination).absolute()
    _require(
        not destination.exists()
        and destination.parent.is_dir()
        and not destination.parent.stat().st_mode & 0o077
        and not any(p.is_symlink() for p in (destination, *destination.parents)),
        "New private nonsymlink runtime destination required",
    )
    for root in (logging_root, reference_root):
        _require(
            not destination.is_relative_to(Path(root).resolve()),
            "Runtime must be outside source trees",
        )
    for value in (branch_id, device_id, local_source_id, actor_id, reviewer_id, command_id):
        _id(value)
    _require(actor_id != reviewer_id, "Distinct operating reviewer contact required")
    for value, bound in (
        (threshold_ms, 3_600_000),
        (cadence_seconds, 86_400),
        (grace_seconds, 86_400),
        (slot_count, 128),
    ):
        _require(
            type(value) is int and 0 < value <= bound, "Positive bounded local clock rule required"
        )
    _require(
        isinstance(rationale, str) and 10 <= len(rationale) <= 2000,
        "Specific local rule rationale required",
    )
    start, authored = _stamp(period_start), _stamp(contract_at)
    _require(authored < start, "Clock rule must predate observations")
    inventory, inventory_event, inventory_provenance = read_native(logging_root, inventory_pin)
    reference, reference_event, _ = read_native(reference_root, reference_pin)
    _require(
        inventory_pin["system"] == "source_inventory"
        and inventory["record_id"] == inventory_pin["record"],
        "Pinned logging inventory required",
    )
    _require(inventory_pin["company"] == reference_pin["company"], "Same company source required")
    _require(
        inventory.get("control_ids") == [CONTROL] and inventory.get("owner_id") == actor_id,
        "Scoped logging owner required",
    )
    assignment = inventory_provenance.get("scoped_assignment", {})
    _require(
        assignment.get("control_id") == CONTROL
        and assignment.get("primary_person_id") == actor_id
        and assignment.get("operating_reviewer_person_id") == reviewer_id,
        "Pinned scoped logging owner/reviewer assignment required",
    )
    _require(
        any(x.get("source_id") == local_source_id for x in inventory.get("required_sources", [])),
        "Inventory source identity required",
    )
    _require(
        reference_pin["system"] == "time_reference_definition"
        and reference.get("reference_id") == reference_pin["record"],
        "Exact native time reference definition required",
    )
    _require(
        reference.get("trust_status") == "LOCAL_REFERENCE_DECLARED_NOT_ENTERPRISE_TRUST",
        "Reference trust must remain local/unaccepted",
    )
    _require(
        _stamp(inventory_pin["available_at"]) <= authored
        and _stamp(reference_pin["available_at"]) <= authored,
        "Contract sources must predate rule",
    )
    _require(
        inventory_event
        and reference_event
        and _stamp(inventory_event) <= authored
        and _stamp(reference_event) <= authored,
        "Prospective source chronology required",
    )
    body = {
        "qualification": QUALIFICATION,
        "control_ids": [CONTROL],
        "policy_status": "LOCAL_RULE_NOT_ACCEPTED_SECURITY_OPERATIONS_POLICY",
        "device_id": device_id,
        "local_source_id": local_source_id,
        "reference_id": reference["reference_id"],
        "reference_trust_status": reference["trust_status"],
        "inventory_pin": _pin(inventory_pin),
        "reference_pin": _pin(reference_pin),
        "threshold_ms": threshold_ms,
        "cadence_seconds": cadence_seconds,
        "grace_seconds": grace_seconds,
        "period_start": _time(period_start),
        "slot_count": slot_count,
        "rationale": rationale,
        "authored_by": actor_id,
        "review_contact_id": reviewer_id,
        "review_performed": False,
    }
    destination.mkdir(mode=0o700)
    try:
        store = CompanyStore(destination)
        for system in ("clock_contract", "clock_observation"):
            store.register_system(inventory_pin["company"], branch_id, system, actor_id)
        pin = _emit(
            store,
            inventory_pin["company"],
            branch_id,
            "clock_contract",
            "CLOCK-CONTRACT",
            _time(contract_at),
            body,
            command_id=command_id,
        )
    except BaseException:
        import shutil

        shutil.rmtree(destination)
        raise
    return pin


def _contract(runtime, contract_pin):
    body, event_at, _ = read_native(runtime, contract_pin)
    _require(
        contract_pin["system"] == "clock_contract" and contract_pin["record"] == "CLOCK-CONTRACT",
        "Exact clock contract required",
    )
    _require(
        body.get("qualification") == QUALIFICATION
        and body.get("policy_status") == "LOCAL_RULE_NOT_ACCEPTED_SECURITY_OPERATIONS_POLICY",
        "Local clock contract required",
    )
    return body, event_at


def _slot(contract, index):
    _require(
        type(index) is int and 0 <= index < contract["slot_count"], "Declared clock slot required"
    )
    return _stamp(contract["period_start"]) + timedelta(seconds=index * contract["cadence_seconds"])


def record_clock_observation(
    runtime,
    *,
    contract_pin,
    slot_index,
    device_root,
    device_pin,
    reference_root,
    reference_sample_pin,
    observed_at,
    command_id,
):
    """Compare separately persisted readings of one capture; never use ingestion lag."""
    contract, contract_at = _contract(runtime, contract_pin)
    due, observed = _slot(contract, slot_index), _stamp(observed_at)
    _require(
        _stamp(contract_at) < due <= observed <= due + timedelta(seconds=contract["grace_seconds"]),
        "Observation outside prospective slot/window",
    )
    device, device_event, _ = read_native(device_root, device_pin)
    reference, reference_event, _ = read_native(reference_root, reference_sample_pin)
    _require(
        device_pin["system"] == "device_clock_sample"
        and reference_sample_pin["system"] == "time_reference_sample",
        "Native clock samples required",
    )
    _require(
        device_pin["company"] == contract_pin["company"] == reference_sample_pin["company"],
        "Same company clock samples required",
    )
    _require(
        device.get("inventory_pin") == contract["inventory_pin"],
        "Device sample inventory binding required",
    )
    _require(
        reference.get("definition_pin") == contract["reference_pin"],
        "Reference sample definition binding required",
    )
    _require(
        device.get("device_id") == contract["device_id"]
        and device.get("local_source_id") == contract["local_source_id"],
        "Pinned device/source identity mismatch",
    )
    _require(
        reference.get("reference_id") == contract["reference_id"],
        "Pinned reference identity mismatch",
    )
    _require(
        device.get("capture_id") == reference.get("capture_id") and device.get("capture_id"),
        "Same physical capture identifier required",
    )
    _require(
        device.get("slot_index") == reference.get("slot_index") == slot_index,
        "Exact observation slot required",
    )
    _require(
        _time(device.get("sampled_at"))
        == _time(reference.get("sampled_at"))
        == _time(due.isoformat()),
        "Coincident scheduled capture required",
    )
    _require(
        device_event
        and reference_event
        and due <= _stamp(device_event) <= observed
        and due <= _stamp(reference_event) <= observed,
        "Native sample event must fall within scheduled observation window",
    )
    _require(
        _stamp(device_pin["available_at"]) <= observed
        and _stamp(reference_sample_pin["available_at"]) <= observed,
        "Native sample must be available",
    )
    offset_microseconds = _offset_microseconds(
        device.get("device_time"), reference.get("reference_time")
    )
    status = (
        "OFFSET_THRESHOLD_EXCEEDED"
        if abs(offset_microseconds) > contract["threshold_ms"] * 1000
        else "WITHIN_LOCAL_THRESHOLD"
    )
    body = {
        "qualification": QUALIFICATION,
        "contract_pin": _pin(contract_pin),
        "slot_index": slot_index,
        "due_at": _time(due.isoformat()),
        "observed_at": _time(observed_at),
        "device_id": contract["device_id"],
        "local_source_id": contract["local_source_id"],
        "reference_id": contract["reference_id"],
        "device_pin": _pin(device_pin),
        "reference_sample_pin": _pin(reference_sample_pin),
        "capture_id": device["capture_id"],
        "device_time": _time(device["device_time"]),
        "reference_time": _time(reference["reference_time"]),
        "offset_microseconds": offset_microseconds,
        "offset_ms": _milliseconds_decimal(offset_microseconds),
        "threshold_ms": contract["threshold_ms"],
        "status": status,
        "alert_state": "OPEN_LOCAL_CLOCK_ALERT"
        if status == "OFFSET_THRESHOLD_EXCEEDED"
        else "NONE",
        "alert_owner_id": contract["authored_by"]
        if status == "OFFSET_THRESHOLD_EXCEEDED"
        else None,
        "review_contact_id": contract["review_contact_id"],
        "review_state": "PENDING_NOT_PERFORMED",
        "reference_trust_status": contract["reference_trust_status"],
        "policy_status": contract["policy_status"],
    }
    store = CompanyStore(runtime)
    return _emit(
        store,
        contract_pin["company"],
        contract_pin["branch"],
        "clock_observation",
        f"CLOCK-SLOT-{slot_index}",
        _time(observed_at),
        body,
        command_id=command_id,
    )


def record_missed_observation(runtime, *, contract_pin, slot_index, checked_at, command_id):
    """Mark no sample submitted to this runtime by the deadline, without inventing offset."""
    contract, contract_at = _contract(runtime, contract_pin)
    due, checked = _slot(contract, slot_index), _stamp(checked_at)
    deadline = due + timedelta(seconds=contract["grace_seconds"])
    _require(
        _stamp(contract_at) < due and checked > deadline,
        "Missed-observation check must follow deadline",
    )
    body = {
        "qualification": QUALIFICATION,
        "contract_pin": _pin(contract_pin),
        "slot_index": slot_index,
        "due_at": _time(due.isoformat()),
        "checked_at": _time(checked_at),
        "deadline_at": _time(deadline.isoformat()),
        "device_id": contract["device_id"],
        "local_source_id": contract["local_source_id"],
        "reference_id": contract["reference_id"],
        "offset_ms": None,
        "offset_microseconds": None,
        "threshold_ms": contract["threshold_ms"],
        "status": "NO_SAMPLE_SUBMITTED_BY_LOCAL_DEADLINE",
        "alert_state": "OPEN_LOCAL_MISSED_OBSERVATION_ALERT",
        "alert_owner_id": contract["authored_by"],
        "review_contact_id": contract["review_contact_id"],
        "review_state": "PENDING_NOT_PERFORMED",
        "policy_status": contract["policy_status"],
    }
    store = CompanyStore(runtime)
    return _emit(
        store,
        contract_pin["company"],
        contract_pin["branch"],
        "clock_observation",
        f"CLOCK-SLOT-{slot_index}",
        _time(checked_at),
        body,
        command_id=command_id,
    )
