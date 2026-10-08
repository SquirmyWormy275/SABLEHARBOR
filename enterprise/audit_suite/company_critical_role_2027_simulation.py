"""Future fictional critical-role review from a frozen local training source.

This is company-owned scenario activity, not employment, competence or audit evidence.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import stat
import tempfile
from contextlib import closing
from datetime import datetime
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _id, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_CRITICAL_ROLE_REVIEW_V1"
COMPANY = "SABLEHARBOR"
BRANCHES = {"CLEAN": "critical-role-clean", "MESSY": "critical-role-messy"}
TRAINING_BRANCHES = {"CLEAN": "training-cycle-a", "MESSY": "training-cycle-b"}
TRAINING_PINS = {
    "receipt": "6d1c9989edd4d17221f8daa5aab96bf1d6415e02b6fd4848ae0523388e721006",
    "database": "96bd095115547e27a42e657230de7b195d0735a63233e4fe1fe8c9c74212509a",
}
SOURCE_PINS = {
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md": (
        "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496"
    ),
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md": (
        "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751"
    ),
    "docs/structured/enterprise_leadership_2026-09-13.json": (
        "90ec45642cc50219544910e60e4bf6d28b810302c62f29c5936bf965501d673d"
    ),
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md": (
        "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433"
    ),
    "enterprise/ccf/assurance/design_data/control_procedures.json": (
        "258f5c868e16f3dc197594857dc86a4f2b3ef11e3e5a36dd0a80a9fc6d40c679"
    ),
}
SOURCE_REFERENCE = "enterprise/audit_suite/company_critical_role_2027_simulation.py"
LIMITS = [
    "Future 2027 training-world events; imported_at records actual 2026 authoring time.",
    "Only two scoped proposed role contacts; no workforce census, employment, qualifications, "
    "certifications, license, accepted backup or policy asserted.",
    "Q1 local course completion is not professional competence evidence.",
    "No audit grant, collection, workpaper, task credit, Key, Atlas or active-pair change.",
]
SYSTEM_OWNERS = {
    "role_scope": "AS-P006",
    "role_review": "AS-P006",
    "role_gap": "AS-P006",
    "role_action": "AS-P006",
}
ROLES = {"AS-P007": "ROLE-33", "AS-P008": "ROLE-34"}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private(path: Path, *, directory: bool) -> Path:
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise CompanyStoreError("Private nonsymlink path required")
    info = path.stat()
    if directory:
        if not path.is_dir() or info.st_mode & 0o077:
            raise CompanyStoreError("Private directory required")
    elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077:
        raise CompanyStoreError("Private regular source file required")
    return path


def _frozen(paths: dict[str, Path]) -> dict[str, tuple]:
    db = paths["database"]
    if any(
        Path(str(db) + suffix).exists() or Path(str(db) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Frozen source has SQLite sidecar")
    result = {}
    for name, path in paths.items():
        _private(path, directory=False)
        info = path.stat()
        result[name] = (
            info.st_dev,
            info.st_ino,
            stat.S_IMODE(info.st_mode),
            info.st_size,
            info.st_mtime_ns,
            _digest(path),
        )
    return result


def _role_projection(leadership: dict) -> dict:
    """Select only pinned proposed-contact facts; no git revision or broad roster."""
    if (
        leadership.get("record_id") != "SH-ENTERPRISE-PPL-20260913"
        or leadership.get("repository_acceptance_status")
        != "DELEGATED_IMPLEMENTATION_PENDING_ACCEPTED_MERGE"
        or leadership.get("employment_start_dates") != "NOT_ESTABLISHED"
    ):
        raise CompanyStoreError("Scoped leadership source boundary differs")
    contacts = {}
    for person in leadership["people"]:
        if person["person_id"] in {"AS-P006", *ROLES}:
            contacts[person["person_id"]] = person
    if set(contacts) != {"AS-P006", *ROLES}:
        raise CompanyStoreError("Scoped contact population differs")
    roles = {"AS-P006": "ROLE-32", **ROLES}
    if any(
        contacts[person]["org_role_id"] != role
        or contacts[person]["appointment_date"] != "2026-09-13"
        or contacts[person]["employment_start"] is not None
        or contacts[person]["source_acceptance"]
        != "DELEGATED_IMPLEMENTATION_PENDING_ACCEPTED_MERGE"
        for person, role in roles.items()
    ):
        raise CompanyStoreError("Scoped role-contact facts differ")
    return {
        "leadership_record_id": leadership["record_id"],
        "repository_acceptance_status": leadership["repository_acceptance_status"],
        "role_contacts": [
            {
                "person_id": person,
                "role_id": roles[person],
                "appointment_date": contacts[person]["appointment_date"],
                "source_acceptance": contacts[person]["source_acceptance"],
                "employment_start": None,
            }
            for person in ("AS-P006", "AS-P007", "AS-P008")
        ],
        "assertion_limit": "SCOPED_PROPOSED_CONTACTS_NOT_EMPLOYMENT_OR_CONTROL_AUTHORITY",
    }


def _input_context(repository: Path, training_root: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    for relative, expected in SOURCE_PINS.items():
        path = repository / relative
        if path.is_symlink() or not path.is_file() or _digest(path) != expected:
            raise CompanyStoreError("Canon/procedure pin differs")
    leadership = json.loads(
        (repository / "docs/structured/enterprise_leadership_2026-09-13.json").read_text()
    )
    projection = _role_projection(leadership)
    training_root = _private(training_root, directory=True)
    paths = {
        "receipt": training_root / "SOURCE_RECEIPT.json",
        "database": training_root / "company.sqlite3",
    }
    before = _frozen(paths)
    if {k: v[-1] for k, v in before.items()} != TRAINING_PINS:
        raise CompanyStoreError("Frozen local training input differs")
    receipt = json.loads(paths["receipt"].read_text())
    if (
        receipt.get("cohort_count") != 3
        or receipt.get("assignments_per_branch") != 5
        or receipt.get("professional_validation") != "UNVALIDATED"
        or receipt.get("audits_created") is not False
        or len(receipt.get("receipts", [])) != 29
        or {r["branch"] for r in receipt["receipts"]} != set(TRAINING_BRANCHES.values())
    ):
        raise CompanyStoreError("Local training receipt scope differs")
    selected = {s: {} for s in TRAINING_BRANCHES}
    with closing(
        sqlite3.connect(paths["database"].as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Training database integrity failed")
        if db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != 29:
            raise CompanyStoreError("Training native population differs")
        for ref in receipt["receipts"]:
            if (
                ref["company"] != COMPANY
                or ref["version"] != 1
                or ref["origin"] != "AUTHORED_TRAINING_SOURCE"
            ):
                raise CompanyStoreError("Training receipt identity differs")
            row = db.execute(
                "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                "AND record=? AND version=?",
                (COMPANY, ref["branch"], ref["system"], ref["record"], ref["version"]),
            ).fetchone()
            if (
                row is None
                or row["sha256"] != ref["sha256"]
                or sha(row["content"]) != ref["sha256"]
                or (row["event_at"], row["available_at"], row["imported_at"])
                != (ref["event_at"], ref["available_at"], ref["imported_at"])
                or row["available_at"] < row["event_at"]
            ):
                raise CompanyStoreError("Training native tuple differs from receipt")
            scenario = next(s for s, b in TRAINING_BRANCHES.items() if b == ref["branch"])
            key = (ref["system"], ref["record"])
            if key in selected[scenario]:
                raise CompanyStoreError("Duplicate training native tuple")
            selected[scenario][key] = {"ref": ref, "body": json.loads(row["content"])}
    if _frozen(paths) != before:
        raise CompanyStoreError("Training source changed during read")
    for scenario in TRAINING_BRANCHES:
        source = selected[scenario]
        roster = source[("training_roster", "ROSTER-LOCAL-TRN-2027-01")]["body"]
        matrix = source[("training_matrix", "MATRIX-LOCAL-TRN-2027-01")]["body"]
        if (
            {x["person_id"]: x["role_id"] for x in roster["members"]}
            != {
                "AS-P006": "ROLE-32",
                **ROLES,
            }
            or roster["custodian"] != "AS-P006"
            or matrix["approved_by"] != "AS-P006"
        ):
            raise CompanyStoreError("Training scoped roster differs")
        first = source[("training_monitoring", "MONITOR-LOCAL-TRN-2027-01-1")]["body"]
        final = source[("training_monitoring", "MONITOR-LOCAL-TRN-2027-01-2")]["body"]
        late = scenario == "MESSY"
        if (
            first["assigned_count"] != 5
            or first["overdue_count"] != int(late)
            or first["completion_count"] != 5 - int(late)
            or final["assigned_count"] != 5
            or final["completion_count"] != 5
            or final["overdue_count"] != 0
            or final["late_completed_count"] != int(late)
        ):
            raise CompanyStoreError("Training chronology differs")
        if late and (
            len(first["overdue"]) != 1
            or first["overdue"][0]["person_id"] != "AS-P007"
            or first["overdue"][0]["course_id"] != "LOCAL-CHANGE"
            or ("training_followup", "FOLLOWUP-LOCAL-TRN-2027-01") not in source
        ):
            raise CompanyStoreError("Late local-course causal chain differs")
    return {
        "selected": selected,
        "role_projection": projection,
        "role_projection_sha256": sha(encoded(projection)),
    }


def _source(context: dict, scenario: str, system: str, record: str) -> dict:
    ref = context["selected"][scenario][(system, record)]["ref"]
    return {
        k: ref[k]
        for k in (
            "company",
            "branch",
            "system",
            "record",
            "version",
            "sha256",
            "event_at",
            "available_at",
            "imported_at",
        )
    }


def _expected_rows(context: dict, scenario: str) -> list[dict]:
    if scenario not in BRANCHES:
        raise CompanyStoreError("Unknown role-review scenario")
    late = scenario == "MESSY"
    refs = {
        "roster": _source(context, scenario, "training_roster", "ROSTER-LOCAL-TRN-2027-01"),
        "initial": _source(context, scenario, "training_monitoring", "MONITOR-LOCAL-TRN-2027-01-1"),
        "closeout": _source(
            context, scenario, "training_monitoring", "MONITOR-LOCAL-TRN-2027-01-2"
        ),
    }
    if late:
        refs["followup"] = _source(
            context, scenario, "training_followup", "FOLLOWUP-LOCAL-TRN-2027-01"
        )
        refs["late_completion"] = _source(
            context, scenario, "training_completions", "LOCAL-TRN-2027-01-AS-P007-LOCAL-CHANGE"
        )
    common = {
        "schema": SCHEMA,
        "scenario": scenario,
        "scope": "FICTIONAL_2027_CORPORATE_SHARED_CONTROL_TWO_PROPOSED_ROLE_CONTACTS",
        "status": "SIMULATED_FUTURE_NOT_ACTUAL_OPERATION",
        "control_ids": ["SH-PPL-005", "SH-TRN-003"],
    }
    events = [
        (
            "role_scope",
            "SCOPE-APR-2027",
            "2027-04-15T09:00:00+00:00",
            "2027-04-15T09:15:00+00:00",
            {
                "role_contacts": [
                    {"person_id": p, "role_id": r, "contact_status": "PROPOSED_OFFICE_OCCUPANT"}
                    for p, r in ROLES.items()
                ],
                "review_owner_contact": "AS-P006",
                "population_basis": (
                    "TWO_SELECTED_CRITICAL_TECHNOLOGY_SECURITY_ROLE_CONTACTS_NOT_WORKFORCE_CENSUS"
                ),
                "training_roster_source": refs["roster"],
            },
        ),
        (
            "role_review",
            "REVIEW-APR-2027",
            "2027-04-15T10:00:00+00:00",
            "2027-04-15T10:20:00+00:00",
            {
                "reviewed_role_ids": list(ROLES.values()),
                "training_source": refs,
                "q1_local_assignment_count": 5,
                "q1_initial_overdue_count": int(late),
                "q1_final_overdue_count": 0,
                "q1_late_completion_count": int(late),
                "training_interpretation": (
                    "LOCAL_COURSE_HISTORY_ONLY_NOT_COMPETENCE_OR_WORKFORCE_COMPLETENESS"
                ),
                "qualification_evidence_status": (
                    "NOT_PRESENT_IN_SCOPED_INPUTS_VERIFICATION_PENDING"
                ),
                "backup_evidence_status": "NOT_PRESENT_IN_SCOPED_INPUTS_VERIFICATION_PENDING",
            },
        ),
        (
            "role_gap",
            "GAP-APR-2027",
            "2027-04-15T11:00:00+00:00",
            "2027-04-15T11:10:00+00:00",
            {
                "open_gap_ids": ["GAP-ROLE-33-COMPETENCE-BACKUP", "GAP-ROLE-34-COMPETENCE-BACKUP"],
                "gap_basis": "SCOPED_SOURCE_DOES_NOT_VERIFY_COMPETENCE_OR_ACCEPTED_BACKUP",
                "training_lateness": "HISTORICAL_LOCAL_COURSE_LATE_AND_FOLLOWED_UP"
                if late
                else "NONE_IN_SCOPED_Q1_SOURCE",
                "training_lateness_is_competence_finding": False,
                "closure_status": "PENDING_OWNER_SOURCE_REVIEW",
            },
        ),
        (
            "role_action",
            "ACTION-APR-2027",
            "2027-04-15T12:00:00+00:00",
            "2027-04-15T12:05:00+00:00",
            {
                "action_status": "INTERNAL_VERIFICATION_QUEUED_NOT_SENT_OR_APPROVED",
                "required_inputs": [
                    "ROLE_SPECIFIC_COMPETENCE_EVIDENCE",
                    "ACCEPTED_BACKUP_COVERAGE",
                    "CAPACITY_BASIS",
                ],
                "late_course_followup_review_needed": late,
                "performance_or_accountability_decision": "UNDETERMINED_NO_CASE_OR_AUTHORITY_FACTS",
                "owner_contact": "AS-P006",
            },
        ),
    ]
    return [
        {
            "system": system,
            "record": record,
            "version": 1,
            "event_at": _time(event),
            "available_at": _time(available),
            "body": {**common, "record_id": record, **body},
            "sha256": sha(encoded({**common, "record_id": record, **body})),
        }
        for system, record, event, available, body in events
    ]


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, ensure_ascii=False, indent=2)
        stream.write("\n")
    path.chmod(0o600)


def create(destination: Path, *, repository: Path, training_root: Path) -> dict:
    destination = Path(destination).absolute()
    _private(destination.parent, directory=True)
    if destination.exists() or destination.is_symlink() or destination != destination.resolve():
        raise CompanyStoreError("New destination required")
    context = _input_context(repository, training_root)
    with tempfile.TemporaryDirectory(
        prefix=".critical-role-stage-", dir=destination.parent
    ) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in BRANCHES.items():
            _id(branch)
            for system, owner in SYSTEM_OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            records[scenario] = []
            for item in _expected_rows(context, scenario):
                ref = store.append_version(
                    COMPANY,
                    branch,
                    item["system"],
                    item["record"],
                    expected_version=0,
                    command_id=f"CR-{branch}-{item['system']}-{item['record']}",
                    event_at=item["event_at"],
                    available_at=item["available_at"],
                    content=encoded(item["body"]),
                    provenance={
                        "source_reference": SOURCE_REFERENCE,
                        "source_pins": SOURCE_PINS,
                        "training_pins": TRAINING_PINS,
                        "role_projection_sha256": context["role_projection_sha256"],
                        "scenario": scenario,
                        "classification": "FUTURE_FICTIONAL_NO_AUDIT_CREDIT",
                    },
                )
                if ref["sha256"] != item["sha256"]:
                    raise CompanyStoreError("Role-review serialization differs")
                records[scenario].append(ref)
        receipt = {
            "schema": SCHEMA,
            "company": COMPANY,
            "branches": BRANCHES,
            "records": records,
            "source_pins": SOURCE_PINS,
            "training_pins": TRAINING_PINS,
            "training_branches": TRAINING_BRANCHES,
            "role_projection": context["role_projection"],
            "role_projection_sha256": context["role_projection_sha256"],
            "role_count_per_branch": 2,
            "source_version_count": 8,
            "open_scoped_gap_count_per_branch": 2,
            "q1_late_local_course_counts": {"CLEAN": 0, "MESSY": 1},
            "actual_operation_eligibility_as_of_2026_09_29": False,
            "audit_task_credit": False,
            "limits": LIMITS,
        }
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _digest(stage / "RECEIPT.json"),
            "company_db_sha256": _digest(stage / "company.sqlite3"),
            "module_sha256": _digest(Path(__file__)),
            "source_version_count": 8,
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return manifest


def verify(destination: Path, *, repository: Path, training_root: Path) -> dict:
    root = _private(destination, directory=True)
    paths = {
        "receipt": root / "RECEIPT.json",
        "manifest": root / "MANIFEST.json",
        "database": root / "company.sqlite3",
    }
    before = _frozen(paths)
    receipt = json.loads(paths["receipt"].read_text())
    manifest = json.loads(paths["manifest"].read_text())
    context = _input_context(repository, training_root)
    if (
        manifest.get("schema") != SCHEMA + "_MANIFEST"
        or manifest.get("receipt_sha256") != before["receipt"][-1]
        or manifest.get("company_db_sha256") != before["database"][-1]
        or manifest.get("module_sha256") != _digest(Path(__file__))
        or manifest.get("source_version_count") != 8
        or manifest.get("audit_task_credit") is not False
        or receipt.get("schema") != SCHEMA
        or receipt.get("company") != COMPANY
        or receipt.get("branches") != BRANCHES
        or receipt.get("source_pins") != SOURCE_PINS
        or receipt.get("training_pins") != TRAINING_PINS
        or receipt.get("training_branches") != TRAINING_BRANCHES
        or receipt.get("role_projection") != context["role_projection"]
        or receipt.get("role_projection_sha256") != context["role_projection_sha256"]
        or receipt.get("role_count_per_branch") != 2
        or receipt.get("source_version_count") != 8
        or receipt.get("open_scoped_gap_count_per_branch") != 2
        or receipt.get("q1_late_local_course_counts") != {"CLEAN": 0, "MESSY": 1}
        or receipt.get("actual_operation_eligibility_as_of_2026_09_29") is not False
        or receipt.get("audit_task_credit") is not False
        or receipt.get("limits") != LIMITS
        or set(receipt.get("records", {})) != set(BRANCHES)
    ):
        raise CompanyStoreError("Role-review receipt/manifest differs")
    with closing(
        sqlite3.connect(paths["database"].as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Role-review database integrity failed")
        if any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "collections", "access_events")
        ):
            raise CompanyStoreError("Audit access in role-review source")
        if db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != 8:
            raise CompanyStoreError("Role-review population differs")
        if {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        } != {
            (COMPANY, branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in SYSTEM_OWNERS.items()
        }:
            raise CompanyStoreError("Role-review custody differs")
        for scenario, branch in BRANCHES.items():
            expected = _expected_rows(context, scenario)
            refs = receipt["records"][scenario]
            expected_provenance = {
                "source_reference": SOURCE_REFERENCE,
                "source_pins": SOURCE_PINS,
                "training_pins": TRAINING_PINS,
                "role_projection_sha256": context["role_projection_sha256"],
                "scenario": scenario,
                "classification": "FUTURE_FICTIONAL_NO_AUDIT_CREDIT",
            }
            if len(refs) != len(expected):
                raise CompanyStoreError("Role-review chain incomplete")
            for item, ref in zip(expected, refs, strict=True):
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=1",
                    (COMPANY, branch, item["system"], item["record"]),
                ).fetchone()
                if (
                    row is None
                    or ref["company"] != COMPANY
                    or ref["branch"] != branch
                    or any(
                        ref[k] != item[k]
                        for k in (
                            "system",
                            "record",
                            "version",
                            "sha256",
                            "event_at",
                            "available_at",
                        )
                    )
                    or ref["imported_at"] != row["imported_at"]
                    or ref["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or row["origin"] != ref["origin"]
                    or json.loads(row["provenance"]) != expected_provenance
                    or ref["provenance"] != expected_provenance
                    or row["sha256"] != item["sha256"]
                    or row["content"] != encoded(item["body"])
                    or row["event_at"] != item["event_at"]
                    or row["available_at"] != item["available_at"]
                    or row["available_at"] < row["event_at"]
                    or datetime.fromisoformat(row["imported_at"])
                    >= datetime.fromisoformat(row["event_at"])
                ):
                    raise CompanyStoreError("Role-review native row differs")
    if _frozen(paths) != before:
        raise CompanyStoreError("Role-review source changed during verification")
    return manifest
