"""Prospective local restore-use contracts and actual parsed reads of restored copies.

These are native company-source operations, not application/BIA usability acceptance.
The trusted local operator supplies a prospective expectation; the separate review
contact is recorded without pretending that contact approved or reviewed it.
"""

import json
from pathlib import Path

from . import company_backup_runtime as backup
from .company_store import CompanyStoreError, _id
from .operating_source_bridge import encoded, sha

QUALIFICATION = "LOCAL_PARSED_RESTORE_USE_PROBE_NOT_APPLICATION_OR_BIA_ACCEPTANCE"


def _reader(value):
    backup.require(
        isinstance(value, dict)
        and set(value)
        in (
            {"kind", "field", "expected"},
            {"kind", "record_id", "field", "expected"},
        ),
        "Exact read-path contract required",
    )
    kind = value["kind"]
    backup.require(
        kind in {"JSON_OBJECT_FIELD_EQUALS", "JSON_RECORD_FIELD_EQUALS"},
        "Supported parsed read path required",
    )
    backup.require(
        (kind == "JSON_RECORD_FIELD_EQUALS") == ("record_id" in value),
        "Reader kind and record selector differ",
    )
    _id(value["field"])
    if "record_id" in value:
        _id(value["record_id"])
    expected = value["expected"]
    backup.require(
        type(expected) in (str, int, bool, type(None)) and len(encoded(expected)) <= 512,
        "Bounded scalar expected result required",
    )
    return dict(value)


def record_use_contract(
    runtime,
    *,
    expected_runtime_sha256,
    expected_revision,
    command_id,
    occurrence_id,
    source_pin,
    reader,
    rationale,
    event_at,
    previous_pin=None,
):
    """Retain a versioned, prospective local expectation, not an approval claim."""
    _id(occurrence_id)
    backup.require(
        isinstance(rationale, str) and 10 <= len(rationale) <= 2000,
        "Specific bounded use rationale required",
    )
    reader = _reader(reader)

    def perform(db, cfg, at):
        binding = cfg["bindings"].get(occurrence_id)
        backup.require(
            binding is not None and binding["operation"] == "RESTORE",
            "Declared restore occurrence required",
        )
        dataset = binding["dataset_id"]
        backup._selected(db, cfg, source_pin, "source_dataset", dataset, at, latest=True)
        backup._previous(db, cfg, "restore_use_contract", occurrence_id, previous_pin, at)
        body = {
            "occurrence_id": occurrence_id,
            "dataset_id": dataset,
            "source_pin": source_pin,
            "reader": reader,
            "rationale": rationale,
            "authored_by": cfg["operator_id"],
            "recorded_review_contact": cfg["operating_reviewer_id"],
            "review_performed": False,
            "authority": "TRUSTED_LOCAL_OPERATOR_AND_DISTINCT_CONTACT_NOT_CORPORATE_APPROVAL",
            "qualification": QUALIFICATION,
        }
        ref = backup._insert(
            db,
            cfg,
            "restore_use_contract",
            occurrence_id,
            encoded(body),
            at,
            "USE-CONTRACT-" + sha(command_id.encode())[:48],
        )
        return {"contract_pin": ref, "status": "PROSPECTIVE_LOCAL_CONTRACT_RECORDED"}

    return backup._execute(
        runtime,
        expected_runtime_sha256,
        expected_revision,
        command_id,
        event_at,
        {
            "kind": "USE_CONTRACT",
            "occurrence_id": occurrence_id,
            "source_pin": source_pin,
            "reader": reader,
            "rationale": rationale,
            "previous_pin": previous_pin,
        },
        perform,
    )


def _actual(raw, reader):
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return "MALFORMED_JSON", None
    if reader["kind"] == "JSON_RECORD_FIELD_EQUALS":
        try:
            records = backup._records(raw)
        except (ValueError, CompanyStoreError):
            return "MALFORMED_RECORDS", None
        row = records.get(reader["record_id"])
        if row is None:
            return "RECORD_ABSENT", None
        value = row
    if not isinstance(value, dict) or reader["field"] not in value:
        return "FIELD_ABSENT", None
    actual = value[reader["field"]]
    if type(actual) not in (str, int, bool, type(None)) or len(encoded(actual)) > 512:
        return "UNSUPPORTED_ACTUAL", None
    return "READ", actual


def run_restore_use_probe(
    runtime,
    *,
    expected_runtime_sha256,
    expected_revision,
    command_id,
    contract_pin,
    restore_job_pin,
    restored_dataset_pin,
    event_at,
):
    """Read the persisted restored copy through its declared JSON path."""

    def perform(db, cfg, at):
        backup.exact_pin(contract_pin)
        contract_row = backup._selected(
            db, cfg, contract_pin, "restore_use_contract", contract_pin["record"], at
        )
        contract = json.loads(contract_row["content"])
        backup.require(
            contract.get("qualification") == QUALIFICATION
            and contract.get("authored_by") == cfg["operator_id"]
            and contract.get("recorded_review_contact") == cfg["operating_reviewer_id"]
            and contract.get("review_performed") is False,
            "Contract authority and qualification differ",
        )
        reader = _reader(contract["reader"])
        occurrence = contract["occurrence_id"]
        binding = cfg["bindings"].get(occurrence)
        backup.require(
            binding is not None
            and binding["operation"] == "RESTORE"
            and binding["dataset_id"] == contract["dataset_id"],
            "Contract restore binding differs",
        )
        job_row = backup._selected(db, cfg, restore_job_pin, "restore_job", occurrence, at)
        job = json.loads(job_row["content"])
        backup.require(
            job.get("status") == "COMPLETED"
            and job.get("object_pin") == restored_dataset_pin
            and job.get("comparison_source_pin") == contract["source_pin"],
            "Completed restore and prospective source pins required",
        )
        backup.require(
            contract_row["event_at"] < job_row["event_at"] < at,
            "Use contract must precede restore and probe",
        )
        latest_contract = backup._latest(
            db, cfg, "restore_use_contract", occurrence, job_row["event_at"]
        )
        backup.require(
            latest_contract is not None and backup.pin(latest_contract) == contract_pin,
            "Contract superseded before restore",
        )
        source = backup._selected(
            db,
            cfg,
            contract["source_pin"],
            "source_dataset",
            binding["dataset_id"],
            job_row["event_at"],
            latest=True,
        )
        restored = backup._selected(
            db, cfg, restored_dataset_pin, "restored_dataset", occurrence, at
        )
        backup.require(
            restored["event_at"] == job_row["event_at"]
            and source["sha256"] == contract["source_pin"]["sha256"],
            "Restored dataset/source identity differs",
        )
        relative = Path(job["copy_path"])
        backup.require(
            not relative.is_absolute()
            and len(relative.parts) == 3
            and relative.parts[0] == "attempts"
            and relative.parts[2] == "copied.bin"
            and all(part not in {"", ".", ".."} for part in relative.parts),
            "Exact private restore copy path required",
        )
        copied = backup.checked_bytes(Path(runtime) / relative)
        backup.require(copied == restored["content"], "Restored copy bytes changed")
        read_status, actual = _actual(copied, reader)
        passed = read_status == "READ" and encoded(actual) == encoded(reader["expected"])
        observation = {
            "contract_pin": contract_pin,
            "restore_job_pin": restore_job_pin,
            "restored_dataset_pin": restored_dataset_pin,
            "source_pin": contract["source_pin"],
            "copy_sha256": sha(copied),
            "reader": reader,
            "read_status": read_status,
            "actual": actual,
            "status": "PASS_LOCAL_PARSED_READ" if passed else "FAIL_LOCAL_PARSED_READ",
            "performed_by": cfg["operator_id"],
            "recorded_review_contact": cfg["operating_reviewer_id"],
            "review_performed": False,
            "qualification": QUALIFICATION,
            "not_application_or_data_usability_acceptance": True,
        }
        ref = backup._insert(
            db,
            cfg,
            "restore_use_probe",
            occurrence,
            encoded(observation),
            at,
            "USE-PROBE-" + sha(command_id.encode())[:48],
        )
        return {"probe_pin": ref, "status": observation["status"]}

    return backup._execute(
        runtime,
        expected_runtime_sha256,
        expected_revision,
        command_id,
        event_at,
        {
            "kind": "USE_PROBE",
            "contract_pin": contract_pin,
            "restore_job_pin": restore_job_pin,
            "restored_dataset_pin": restored_dataset_pin,
        },
        perform,
    )
