"""Prospective company-native data-flow gate exercise, separate from any audit."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _id, _json, _time
from .operating_source_bridge import encoded, sha
from .organization import snapshot
from .private_publication import publish

SCHEMA = "SH_PROSPECTIVE_DATA_FLOW_EXERCISE_V1"
QUALIFICATION = "LOCAL_METADATA_ONLY_NONPERSONAL_FIXTURE_NO_PHI_OR_DEPLOYED_SITE"
COMPANY = "SABLE-HARBOR-REFERENCE"
OWNER = "AS-P014"
CONTROL_IDS = ("SH-DAT-001", "SH-DAT-002", "SH-DAT-003", "SH-REC-001", "SH-REC-004")
SOURCE_PATHS = (
    "docs/internal/development/CCF_ASSURANCE_SCOPE_PROPOSAL_2026-09-11.md",
    "enterprise/ccf/assurance/design_data/SERVICE_DESCRIPTION.md",
    "enterprise/ccf/assurance/design_data/control_procedures.json",
    "docs/canon/RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md",
)
EVENTS = {
    "CLEAN": (
        ("REGISTER", "NEW", "REGISTERED", "LOCAL_METADATA_ONLY", "2027-02-01T10:00:00+00:00"),
        (
            "INTAKE_SCREEN",
            "REGISTERED",
            "BLOCKED",
            "REJECT_UNVERIFIED_RESTRICTED_CANDIDATE",
            "2027-02-01T10:05:00+00:00",
        ),
        (
            "REPLICATION_REQUEST",
            "BLOCKED",
            "BLOCKED",
            "DENY_NO_AUTHORITY_OR_DEPLOYED_ROUTE",
            "2027-02-01T10:15:00+00:00",
        ),
        (
            "RECORD_RECONCILE",
            "BLOCKED",
            "BLOCKED",
            "DECISION_RECORD_PRESENT_NO_DATA_TRANSFER",
            "2027-02-01T11:00:00+00:00",
        ),
        (
            "RETENTION_REVIEW",
            "BLOCKED",
            "BLOCKED",
            "DEFER_NO_APPROVED_SCHEDULE_OR_HOLD_DISPOSITION",
            "2027-02-02T09:00:00+00:00",
        ),
    ),
    "MESSY": (
        ("REGISTER", "NEW", "REGISTERED", "LOCAL_METADATA_ONLY", "2027-02-01T10:00:00+00:00"),
        (
            "INTAKE_SCREEN",
            "REGISTERED",
            "LOCAL_MARKER_ADMITTED",
            "PREMATURE_OPERATOR_ELIGIBILITY_MARKER",
            "2027-02-01T10:05:00+00:00",
        ),
        (
            "REPLICATION_REQUEST",
            "LOCAL_MARKER_ADMITTED",
            "ROUTE_MARKER_QUEUED",
            "PREMATURE_RENO_BOISE_ROUTE_MARKER",
            "2027-02-01T10:15:00+00:00",
        ),
        (
            "LATE_REVIEW",
            "ROUTE_MARKER_QUEUED",
            "QUARANTINED",
            "AUTHORITY_GAP_FOUND_NO_TRANSFER_PROOF",
            "2027-02-01T11:00:00+00:00",
        ),
        (
            "RECORD_RECONCILE",
            "QUARANTINED",
            "QUARANTINED",
            "DESTINATION_ACK_UNVERIFIED_EXCEPTION_OPEN",
            "2027-02-01T11:30:00+00:00",
        ),
        (
            "RETENTION_REVIEW",
            "QUARANTINED",
            "QUARANTINED",
            "DEFER_NO_APPROVED_SCHEDULE_OR_HOLD_DISPOSITION",
            "2027-02-02T09:00:00+00:00",
        ),
    ),
}


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_pins(repository: Path) -> dict[str, str]:
    pins = {}
    for name in SOURCE_PATHS:
        path = repository / name
        if not path.is_file() or path.is_symlink():
            raise CompanyStoreError("Required canon source unavailable")
        pins[name] = _file_sha(path)
    return pins


def _check_canon(repository: Path) -> tuple[dict, dict]:
    organization = snapshot(repository)
    assignments = {a["control_id"]: a for a in organization["control_assignments"]}
    if any(assignments[c]["custodian_person_id"] != OWNER for c in CONTROL_IDS):
        raise CompanyStoreError("Current proposed data custodian assignment differs")
    if assignments["SH-DAT-002"]["primary_person_id"] != "AS-P003":
        raise CompanyStoreError("Privacy/legal proposed contact differs")
    if any(assignments[c]["status"] != "PROPOSED_CURRENT_ASSIGNMENT" for c in CONTROL_IDS):
        raise CompanyStoreError("Expected proposed assignments required")
    return _source_pins(repository), {
        c: {
            "primary_person_id": assignments[c]["primary_person_id"],
            "custodian_person_id": assignments[c]["custodian_person_id"],
            "status": assignments[c]["status"],
            "authority_limit": assignments[c]["authority_limit"],
        }
        for c in CONTROL_IDS
    }


def _private_new(destination: Path) -> Path:
    destination = destination.absolute()
    parent = destination.parent
    if (
        not parent.is_dir()
        or any(path.is_symlink() for path in (parent, *parent.parents))
        or parent.stat().st_mode & 0o077
        or destination.exists()
        or destination.is_symlink()
        or destination != destination.resolve()
    ):
        raise CompanyStoreError("New canonical destination with existing private parent required")
    return destination


def _definition(scenario: str, branch: str) -> dict:
    return {
        "schema": SCHEMA,
        "scenario": scenario,
        "company": COMPANY,
        "branch": branch,
        "dataset_id": "EXERCISE-RESTRICTED-CANDIDATE-MARKER",
        "fixture": "NONPERSONAL_METADATA_ONLY_NO_SOURCE_PAYLOAD",
        "physical_scope": "LOCAL_EXERCISE_NO_RENO_OR_BOISE_DEPLOYMENT",
        "candidate_flows": ["INTAKE_TO_LOCAL_REVIEW", "RENO_TO_BOISE_DESIGN_ONLY"],
        "control_ids": list(CONTROL_IDS),
        "authority_facts": {
            "actual_phi": "UNASSERTED",
            "ba_or_subcontractor_role": "UNASSERTED",
            "executed_agreement": "UNASSERTED",
            "approved_retention": "UNASSERTED",
            "actual_processing_or_transfer": "UNASSERTED",
        },
        "qualification": QUALIFICATION,
    }


def _event_body(scenario: str, ordinal: int, event: tuple) -> dict:
    action, before, after, outcome, at = event
    exception = scenario == "MESSY" and ordinal >= 2
    return {
        "schema": SCHEMA,
        "scenario": scenario,
        "sequence": ordinal,
        "event_at": _time(at),
        "action": action,
        "before": before,
        "after": after,
        "outcome": outcome,
        "actor_id": OWNER,
        "dataset_id": "EXERCISE-RESTRICTED-CANDIDATE-MARKER",
        "data_bytes": 0,
        "candidate_classification": "UNVERIFIED_RESTRICTED_CANDIDATE_NOT_PHI_DETERMINATION",
        "legal_role": "UNDETERMINED",
        "agreement": "UNVERIFIED_NOT_ASSERTED",
        "processing_purpose_authority": "UNVERIFIED_NOT_ASSERTED",
        "requested_route": "DESIGN_ONLY_RENO_TO_BOISE",
        "actual_transfer": False,
        "deployed_site": False,
        "retention_schedule": "UNAPPROVED",
        "legal_hold_disposition": "UNDETERMINED",
        "exception_open": exception,
        "qualification": QUALIFICATION,
    }


def _write_json(path: Path, body: dict) -> None:
    with open(path, "x", encoding="utf-8") as stream:
        json.dump(body, stream, sort_keys=True, indent=2, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def create(destination: Path, *, repository: Path, clean_branch: str, messy_branch: str) -> dict:
    """Create new isolated native sources; this never grants or collects audit evidence."""
    repository = Path(repository).resolve()
    destination = _private_new(Path(destination))
    branch_ids = {"CLEAN": _id(clean_branch), "MESSY": _id(messy_branch)}
    if branch_ids["CLEAN"] == branch_ids["MESSY"]:
        raise CompanyStoreError("Distinct branch identities required")
    pins, assignments = _check_canon(repository)
    with tempfile.TemporaryDirectory(
        prefix=".data-flow-stage-", dir=destination.parent
    ) as stage_name:
        stage = Path(stage_name)
        store = CompanyStore(stage)
        records = {"CLEAN": [], "MESSY": []}
        for scenario in ("CLEAN", "MESSY"):
            branch = branch_ids[scenario]
            for system in ("flow_definition", "flow_event"):
                store.register_system(COMPANY, branch, system, OWNER)
            definition = _definition(scenario, branch)
            base_at = _time("2027-02-01T09:00:00+00:00")
            provenance = {
                "source_reference": "enterprise/audit_suite/company_data_flow_exercise.py",
                "source_pins": pins,
                "proposed_custody": assignments,
                "scenario": scenario,
                "qualification": QUALIFICATION,
            }
            definition_raw = encoded(definition)
            definition_ref = store.append_version(
                COMPANY,
                branch,
                "flow_definition",
                "FLOW-01",
                expected_version=0,
                command_id=f"DF-{branch}-DEFINITION",
                event_at=base_at,
                available_at=base_at,
                content=definition_raw,
                provenance=provenance,
            )
            records[scenario].append(definition_ref)
            previous_sha = sha(definition_raw)
            previous_state = "NEW"
            for ordinal, event in enumerate(EVENTS[scenario], 1):
                body = _event_body(scenario, ordinal, event)
                if body["before"] != previous_state:
                    raise CompanyStoreError("Invalid scripted flow transition")
                body["definition_sha256"] = definition_ref["sha256"]
                body["previous_sha256"] = previous_sha
                raw = encoded(body)
                record_id = f"FLOW-01-E{ordinal:02d}"
                ref = store.append_version(
                    COMPANY,
                    branch,
                    "flow_event",
                    record_id,
                    expected_version=0,
                    command_id=f"DF-{branch}-E{ordinal:02d}",
                    event_at=body["event_at"],
                    available_at=body["event_at"],
                    content=raw,
                    provenance=provenance,
                )
                records[scenario].append(ref)
                previous_sha = ref["sha256"]
                previous_state = body["after"]
        receipt = {
            "schema": SCHEMA,
            "status": "PROSPECTIVE_COMPANY_NATIVE_EXERCISE_NO_AUDIT_CREDIT",
            "company": COMPANY,
            "branches": branch_ids,
            "records": records,
            "final_states": {"CLEAN": "BLOCKED", "MESSY": "QUARANTINED"},
            "open_exception_counts": {"CLEAN": 0, "MESSY": 5},
            "source_pins": pins,
            "proposed_custody": assignments,
            "qualification": QUALIFICATION,
            "limits": [
                "The 2027 event times are prospective authored exercise times; "
                "imported_at is actual source insertion time.",
                "No personal or PHI payload, real processing, site transfer, BA status, "
                "signed agreement, approved retention, or hold release is asserted.",
                "Messy records a premature local route marker and unverified destination "
                "acknowledgement, not a completed Reno-to-Boise transfer.",
                "Native rows belong to a company store. No grants, collections, audit tasks, "
                "Key bindings, grades, or release claims are made.",
            ],
        }
        _write_json(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _file_sha(stage / "RECEIPT.json"),
            "company_db_sha256": _file_sha(stage / "company.sqlite3"),
            "module_sha256": _file_sha(Path(__file__)),
            "status": receipt["status"],
            "native_version_count": sum(len(v) for v in records.values()),
            "audit_task_credit": False,
        }
        _write_json(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return manifest


def verify(destination: Path) -> dict:
    """Read-only receipt, row provenance, and causal-state verification."""
    root = Path(destination).absolute()
    if (
        root != root.resolve()
        or any(path.is_symlink() for path in (root, *root.parents))
        or not root.is_dir()
        or root.stat().st_mode & 0o077
        or any(
            (root / name).is_symlink()
            or (root / name).stat().st_nlink != 1
            or (root / name).stat().st_mode & 0o077
            for name in ("MANIFEST.json", "RECEIPT.json", "company.sqlite3")
        )
        or any(p.name.endswith(("-wal", "-shm")) for p in root.iterdir())
    ):
        raise CompanyStoreError("Private ordinary source files without active sidecars required")
    manifest = json.loads((root / "MANIFEST.json").read_text())
    receipt = json.loads((root / "RECEIPT.json").read_text())
    if (
        manifest["receipt_sha256"] != _file_sha(root / "RECEIPT.json")
        or manifest["company_db_sha256"] != _file_sha(root / "company.sqlite3")
        or manifest["module_sha256"] != _file_sha(Path(__file__))
        or manifest["native_version_count"] != 13
        or manifest["audit_task_credit"] is not False
    ):
        raise CompanyStoreError("Exercise receipt pin mismatch")
    if (
        receipt["schema"] != SCHEMA
        or receipt["status"] != manifest["status"]
        or receipt["qualification"] != QUALIFICATION
        or receipt["company"] != COMPANY
        or receipt["final_states"] != {"CLEAN": "BLOCKED", "MESSY": "QUARANTINED"}
        or receipt["open_exception_counts"] != {"CLEAN": 0, "MESSY": 5}
        or set(receipt["branches"]) != set(EVENTS)
        or receipt["branches"]["CLEAN"] == receipt["branches"]["MESSY"]
    ):
        raise CompanyStoreError("Exercise scope or state receipt differs")
    db_path = root / "company.sqlite3"
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Native source database integrity failure")
        if (
            db.execute("SELECT COUNT(*) FROM grants").fetchone()[0]
            or db.execute("SELECT COUNT(*) FROM collections").fetchone()[0]
        ):
            raise CompanyStoreError("Exercise must not mint audit access or collections")
        if db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != 13:
            raise CompanyStoreError("Unexpected native version count")
        systems = db.execute("SELECT company,branch,system,owner FROM systems").fetchall()
        expected_systems = {
            (COMPANY, branch, system, OWNER)
            for branch in receipt["branches"].values()
            for system in ("flow_definition", "flow_event")
        }
        if {tuple(row) for row in systems} != expected_systems or len(systems) != 4:
            raise CompanyStoreError("Native source system registration differs")
        for scenario in ("CLEAN", "MESSY"):
            branch = receipt["branches"][scenario]
            refs = receipt["records"][scenario]
            if len(refs) != 1 + len(EVENTS[scenario]):
                raise CompanyStoreError("Incomplete scenario source chain")
            previous_sha, previous_state = None, "NEW"
            for index, ref in enumerate(refs):
                expected_system = "flow_definition" if index == 0 else "flow_event"
                expected_record = "FLOW-01" if index == 0 else f"FLOW-01-E{index:02d}"
                expected_command = (
                    f"DF-{branch}-DEFINITION" if index == 0 else f"DF-{branch}-E{index:02d}"
                )
                if (
                    ref["company"] != COMPANY
                    or ref["branch"] != branch
                    or ref["system"] != expected_system
                    or ref["record"] != expected_record
                    or ref["version"] != 1
                ):
                    raise CompanyStoreError("Exact native source routing differs")
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    (ref["company"], ref["branch"], ref["system"], ref["record"], ref["version"]),
                ).fetchone()
                if (
                    row is None
                    or row["branch"] != branch
                    or row["sha256"] != ref["sha256"]
                    or sha(row["content"]) != ref["sha256"]
                ):
                    raise CompanyStoreError("Native source identity/content mismatch")
                if (
                    row["event_at"] != row["available_at"]
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                ):
                    raise CompanyStoreError("Native source chronology/origin mismatch")
                expected_event_at = (
                    _time("2027-02-01T09:00:00+00:00")
                    if index == 0
                    else _time(EVENTS[scenario][index - 1][4])
                )
                if row["event_at"] != expected_event_at or row["command_id"] != expected_command:
                    raise CompanyStoreError("Native event time or command differs")
                if row["imported_at"] is None or _time(row["imported_at"]) != row["imported_at"]:
                    raise CompanyStoreError("Actual source import time required")
                if (
                    ref["event_at"] != row["event_at"]
                    or ref["available_at"] != row["available_at"]
                    or ref["imported_at"] != row["imported_at"]
                ):
                    raise CompanyStoreError("Receipt source timestamps differ")
                provenance = json.loads(row["provenance"])
                if (
                    provenance["source_reference"]
                    != "enterprise/audit_suite/company_data_flow_exercise.py"
                    or provenance["source_pins"] != receipt["source_pins"]
                    or provenance["proposed_custody"] != receipt["proposed_custody"]
                    or provenance["scenario"] != scenario
                    or provenance["qualification"] != QUALIFICATION
                    or ref["provenance"] != provenance
                ):
                    raise CompanyStoreError("Native source provenance differs")
                key = [COMPANY, branch, expected_system, expected_record]
                digest = sha(
                    _json(
                        [
                            key,
                            0,
                            expected_event_at,
                            expected_event_at,
                            "AUTHORED_TRAINING_SOURCE",
                            provenance,
                            ref["sha256"],
                        ]
                    ).encode()
                )
                if row["input_digest"] != digest:
                    raise CompanyStoreError("Native immutable input digest differs")
                body = json.loads(row["content"])
                if body["schema"] != SCHEMA or body["scenario"] != scenario:
                    raise CompanyStoreError("Scenario provenance mismatch")
                if index == 0:
                    if row["system"] != "flow_definition" or body != _definition(scenario, branch):
                        raise CompanyStoreError("Definition missing")
                    definition_sha = row["sha256"]
                else:
                    expected = _event_body(scenario, index, EVENTS[scenario][index - 1])
                    expected["previous_sha256"] = previous_sha
                    expected["definition_sha256"] = definition_sha
                    if (
                        row["system"] != "flow_event"
                        or body != expected
                        or body["before"] != previous_state
                    ):
                        raise CompanyStoreError("Causal flow trace differs")
                    previous_state = body["after"]
                previous_sha = row["sha256"]
            if previous_state != receipt["final_states"][scenario]:
                raise CompanyStoreError("Final flow state differs")
    return {
        "status": "PASS_READONLY_PROSPECTIVE_NATIVE_FLOW_VERIFICATION",
        "manifest_sha256": _file_sha(root / "MANIFEST.json"),
        "native_version_count": 13,
        "company_database_sha256": _file_sha(db_path),
        "audit_task_credit": False,
    }
