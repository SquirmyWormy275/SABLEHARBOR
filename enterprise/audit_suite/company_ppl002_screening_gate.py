"""Nonpersonal fictional pre-assignment screening requirement negative gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import stat
import tempfile
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_PPL002_SELECTED_SCREENING_NEGATIVE_GATE_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
REQUISITION = "SIM-PPL002-TRUST-ROLE-REQ-001"
EXCEPTION = "LOCAL-PPL002-PREMATURE-NOMINATION-EXC-001"
CONTROL = "SH-PPL-002"
START = "2027-07-13T09:00:00+00:00"
AS_OF = "2026-09-29"
BRANCHES = {"CLEAN": "PPL002-CLEAN", "MESSY": "PPL002-MESSY"}
MATRIX = (
    "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/run-v2/MATRIX.json"
)
MATRIX_REVIEW = (
    "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/"
    "independent-review-v2/REVIEW.json"
)
MATRIX_PINS = {
    MATRIX: "e9477d2074bebce185e412a3ee7c424ded395c1a1128a7c918a94f6acbd1e327",
    MATRIX_REVIEW: "c4064f6217c0e7f69276adc71004d6da7971867ccf3d844a3e198145cec31ace",
}
CANON_PINS = {
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md": (
        "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433"
    ),
    "docs/controls/CCF_CONTROL_OBJECTIVES_v0.1.md": (
        "db7a189139b86fb51d684b6af3e681002b5e0f3f81c38c5bc15a61c20e4a59a3"
    ),
    "docs/governance/PEOPLE_AND_CULTURE_DOCTRINE.md": (
        "9e8c8b6b3b3ce8500553adfc0e35e94956a8251d395fd8d39355f3d84c1dc5ee"
    ),
    "docs/controls/CCF_POLICY_AND_ARTIFACT_INVENTORY_v0.1.md": (
        "395198400d72211716f26f7376dd362993e538d0c081fdaaee3d148d642ea0dd"
    ),
    "docs/organization/source/chartbook.json": (
        "6ba4f1ed1a14581455a62c3e79a29ca59dbaf1270dfb0db850c0376c15507b49"
    ),
    "docs/structured/enterprise_leadership_2026-09-13.json": (
        "90ec45642cc50219544910e60e4bf6d28b810302c62f29c5936bf965501d673d"
    ),
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md": (
        "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751"
    ),
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md": (
        "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496"
    ),
}
PLAN = {
    "CLEAN": (
        ("people_requirement_intake", "SCOPE", 0),
        ("people_requirement_intake", "REQUIREMENT-REQUEST", 5),
        ("security_requirement_input", "SECURITY-INPUT", 10),
        ("people_assignment_gate", "GATE", 12),
        ("people_assignment_gate", "FINAL", 20),
    ),
    "MESSY": (
        ("people_requirement_intake", "SCOPE", 0),
        ("people_requirement_intake", "REQUIREMENT-REQUEST", 5),
        ("people_assignment_gate", "INVALID-NOMINATION", 8),
        ("security_requirement_input", "SECURITY-INPUT", 10),
        ("people_assignment_gate", "DENIAL", 12),
        ("people_assignment_gate", "CORRECTION", 15),
        ("people_assignment_gate", "FINAL", 20),
    ),
}
TASK_IDS = {
    "TASK-SH-PPL-002-corporate-IMPLEMENTATION",
    "TASK-SH-PPL-002-corporate-TOD",
    "TASK-SH-PPL-002-corporate-TOE",
}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private(path: Path) -> tuple:
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise CompanyStoreError("Private screening source alias forbidden")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077:
        raise CompanyStoreError("Ordinary private screening file required")
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, _digest(path)


def _pins(repository: Path) -> dict:
    for name, expected in CANON_PINS.items():
        path = repository / name
        if path.is_symlink() or not path.is_file() or _digest(path) != expected:
            raise CompanyStoreError(f"Screening canon differs: {name}")
    code = "enterprise/audit_suite/company_ppl002_screening_gate.py"
    return {**CANON_PINS, code: _digest(repository / code)}


def _actors(repository: Path) -> None:
    chart = json.loads((repository / "docs/organization/source/chartbook.json").read_bytes())
    leadership = json.loads(
        (repository / "docs/structured/enterprise_leadership_2026-09-13.json").read_bytes()
    )
    for actor, name, title, role in (
        ("AS-P006", "Sofia Hart", "Head of People and Culture", "ROLE-32"),
        ("AS-P008", "Dana West", "Chief Information Security Officer", "ROLE-34"),
    ):
        card = [
            node
            for node in chart["nodes"]
            if node.get("type") == "person" and node.get("person_id") == actor
        ]
        leader = [p for p in leadership["people"] if p["person_id"] == actor]
        if (
            len(card) != 1
            or len(leader) != 1
            or (card[0]["name"], card[0]["title"], card[0]["role_id"]) != (name, title, role)
            or card[0]["title_state"] != "DELEGATED_FICTIONAL_APPOINTMENT_PENDING_ACCEPTANCE"
            or leader[0]["org_role_id"] != role
        ):
            raise CompanyStoreError("Selected proposed People/Security actor differs")


def _routes(private_repository: Path) -> tuple[dict, dict]:
    identities = {}
    for name, expected in MATRIX_PINS.items():
        identity = _private(private_repository / name)
        if identity[-1] != expected:
            raise CompanyStoreError("Frozen screening route input differs")
        identities[name] = identity
    matrix = json.loads((private_repository / MATRIX).read_bytes())
    review = json.loads((private_repository / MATRIX_REVIEW).read_bytes())
    if any(
        _private(private_repository / name) != identity for name, identity in identities.items()
    ):
        raise CompanyStoreError("Frozen screening route input changed during read")
    if review.get("verdict") != "PASS_READ_ONLY_CANDIDATE_MATRIX_FOR_INTEGRATION":
        raise CompanyStoreError("Frozen route review missing")
    routes = {}
    for side in "AB":
        controls = [
            control
            for family in matrix["sides"][side]["families"]
            for control in family["controls"]
            if control["control_id"] == CONTROL
        ]
        if len(controls) != 1 or {row["task_id"] for row in controls[0]["tasks"]} != TASK_IDS:
            raise CompanyStoreError("Exact three screening routes differ")
        rows = controls[0]["tasks"]
        if any(
            row["current_status"] != "NOT_STARTED"
            or row["current_conclusion"] != "NOT_RUN"
            or row["task_credit"] is not False
            for row in rows
        ):
            raise CompanyStoreError("Frozen screening route was credited")
        routes[side] = [
            {
                "task_id": row["task_id"],
                "procedure_type": row["procedure_type"],
                "authored_test_clause": row["authored_test_clause"],
                "remaining_test_gate": row["remaining_test_gate"],
                "status": "NOT_STARTED",
                "conclusion": "NOT_RUN",
                "task_credit": False,
            }
            for row in rows
        ]
    return routes, MATRIX_PINS


def _body(branch: str, record: str) -> dict:
    common = {
        "requisition_id": REQUISITION,
        "control_id": CONTROL,
        "qualification": "FUTURE_NONPERSONAL_SELECTED_ROLE_REQUIREMENT_EXERCISE_ONLY",
        "candidate_id": None,
        "personal_data": False,
        "actual_candidate_or_employee": False,
        "background_or_qualification_result": None,
        "qualified_legal_customer_field_applicability": "PENDING_NOT_ASSERTED",
        "accepted_people_or_security_delegation": False,
        "actual_assignment_or_access": False,
        "audit_task_credit": False,
    }
    stages = {
        "SCOPE": {
            "actor": "AS-P006",
            "selected_requisitions": [REQUISITION],
            "role_class": "SIMULATED_TRUST_SENSITIVE_ROLE_NOT_ACTUAL_POSITION",
            "population": "ONE_SYNTHETIC_REQUISITION_NOT_WORKFORCE_OR_SCREENING_CENSUS",
        },
        "REQUIREMENT-REQUEST": {
            "actor": "AS-P006",
            "requested_inputs": ["SECURITY_TRUST", "LEGAL", "CUSTOMER", "FIELD"],
            "decision": "CRITERIA_PENDING_BLOCK_ASSIGNMENT_AND_ACCESS",
        },
        "SECURITY-INPUT": {
            "actor": "AS-P008",
            "recommendation": "TRUST_SENSITIVE_REQUIREMENT_REVIEW_NEEDED",
            "screening_criteria": "NOT_QUALIFIED_OR_ACCEPTED",
            "clearance": False,
        },
        "GATE": {
            "actor": "AS-P006",
            "decision": "BLOCKED_PENDING_APPLICABILITY_CRITERIA_AND_SCREENING_RESULT",
            "role_nomination_attempted": False,
        },
        "INVALID-NOMINATION": {
            "actor": "AS-P006",
            "decision": "INVALID_LOCAL_UNBOUND_ROLE_NOMINATION_BEFORE_CRITERIA",
            "candidate_id": None,
            "external_effect": False,
            "exception_id": EXCEPTION,
        },
        "DENIAL": {
            "actor": "AS-P006",
            "decision": "INVALID_LOCAL_NOMINATION_DENIED_NO_ASSIGNMENT_OR_ACCESS",
            "security_input_considered": True,
            "exception_id": EXCEPTION,
        },
        "CORRECTION": {
            "actor": "AS-P006",
            "decision": "LOCAL_NOMINATION_WITHDRAWN_PENDING_CRITERIA",
            "prior_invalid_nomination_erased": False,
            "exception_id": EXCEPTION,
        },
    }
    if record == "FINAL":
        stages[record] = {
            "actor": "AS-P006",
            "role_status": "UNFILLED_AND_UNASSIGNED",
            "screening_requirement_status": "QUALIFIED_APPLICABILITY_PENDING",
            "open_exception_ids": [EXCEPTION] if branch == "MESSY" else [],
            "prior_invalid_nomination_preserved": branch == "MESSY",
        }
    return {**common, **stages[record]}


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Create one private selected native pair without people or audit operations."""
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(p.is_symlink() for p in (destination, *destination.parents))
    ):
        raise CompanyStoreError("New private screening destination required")
    pins = _pins(repository)
    _actors(repository)
    routes, matrix_pins = _routes(private_repository)
    start = datetime.fromisoformat(_time(START))
    if start.date().isoformat() <= AS_OF:
        raise CompanyStoreError("Selected screening event must remain future fictional")
    originals = []
    with tempfile.TemporaryDirectory(prefix="ppl002-stage-", dir=destination.parent) as temp:
        stage = Path(temp)
        store = CompanyStore(stage)
        for kind, branch in BRANCHES.items():
            for system, owner in (
                ("people_requirement_intake", "AS-P006"),
                ("security_requirement_input", "AS-P008"),
                ("people_assignment_gate", "AS-P006"),
            ):
                store.register_system(COMPANY, branch, system, owner)
            previous = None
            for system, record, minute in PLAN[kind]:
                at = (start + timedelta(minutes=minute)).isoformat(timespec="microseconds")
                body = {
                    **_body(kind, record),
                    "record_id": record,
                    "event_at": at,
                    "previous_source": previous,
                }
                row = store.append_version(
                    COMPANY,
                    branch,
                    system,
                    record,
                    expected_version=0,
                    command_id="PPL2-" + sha(encoded([branch, system, record])),
                    event_at=at,
                    available_at=at,
                    content=encoded(body),
                    provenance={
                        "source_reference": REQUISITION,
                        "source_sha256": pins,
                        "matrix_sha256": matrix_pins[MATRIX],
                        "control_ids": [CONTROL],
                        "operational_fact_status": "FUTURE_NONPERSONAL_LOCAL_EXERCISE_ONLY",
                    },
                )
                item = {
                    "company": COMPANY,
                    "branch": branch,
                    "system": system,
                    "record": record,
                    "version": row["version"],
                    "event_at": row["event_at"],
                    "available_at": row["available_at"],
                    "imported_at": row["imported_at"],
                    "sha256": row["sha256"],
                }
                originals.append(item)
                previous = {key: item[key] for key in ("system", "record", "version", "sha256")}
        receipt = {
            "schema": SCHEMA,
            "status": "SEALED_NONPERSONAL_FUTURE_SCREENING_GATE_NO_AUDIT_CREDIT",
            "requisition_id": REQUISITION,
            "branch_ids": BRANCHES,
            "source_sha256": pins,
            "matrix_sha256": matrix_pins,
            "routes": routes,
            "native_originals": originals,
            "native_count": 12,
            "population": "ONE_SYNTHETIC_REQUISITION_NOT_WORKFORCE_OR_SCREENING_CENSUS",
            "messy_open_exception": EXCEPTION,
            "qualified_applicability": "PENDING_NOT_ASSERTED",
            "candidate_or_personal_data": False,
            "screening_result": False,
            "actual_employment_assignment_or_access": False,
            "actual_2027_operation": False,
            "source_complete": False,
            "audit_task_credit": False,
            "active_P1_mutated": False,
        }
        source = stage / "SOURCE_RECEIPT.json"
        source.write_bytes(encoded(receipt))
        source.chmod(0o600)
        manifest = {
            "schema": "SH_PPL002_SELECTED_SCREENING_MANIFEST_V1",
            "status": "SEALED_PRIVATE_FUTURE_NEGATIVE_GATE_ONLY",
            "source_receipt_sha256": _digest(source),
            "native_db_sha256": _digest(stage / "company.sqlite3"),
            "native_count": 12,
            "audit_task_credit": False,
            "active_P1_mutated": False,
        }
        path = stage / "RUN-MANIFEST.json"
        path.write_bytes(encoded(manifest))
        path.chmod(0o600)
        publish(stage, destination)
    return receipt


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Reperform selected source, without reading or writing audit engagement."""
    raw = Path(destination).absolute()
    if any(p.is_symlink() for p in (raw, *raw.parents)):
        raise CompanyStoreError("Private screening directory alias forbidden")
    destination = raw.resolve(strict=True)
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    if destination.stat().st_mode & 0o077:
        raise CompanyStoreError("Private screening directory required")
    paths = {
        name: destination / name
        for name in ("SOURCE_RECEIPT.json", "RUN-MANIFEST.json", "company.sqlite3")
    }
    identities = {name: _private(path) for name, path in paths.items()}
    database = paths["company.sqlite3"]
    if any(
        Path(str(database) + suffix).exists() or Path(str(database) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Frozen screening database has sidecar")
    pins = _pins(repository)
    _actors(repository)
    routes, matrix_pins = _routes(private_repository)
    receipt = json.loads(paths["SOURCE_RECEIPT.json"].read_bytes())
    manifest = json.loads(paths["RUN-MANIFEST.json"].read_bytes())
    if manifest != {
        "schema": "SH_PPL002_SELECTED_SCREENING_MANIFEST_V1",
        "status": "SEALED_PRIVATE_FUTURE_NEGATIVE_GATE_ONLY",
        "source_receipt_sha256": identities["SOURCE_RECEIPT.json"][-1],
        "native_db_sha256": identities["company.sqlite3"][-1],
        "native_count": 12,
        "audit_task_credit": False,
        "active_P1_mutated": False,
    }:
        raise CompanyStoreError("Selected screening manifest differs")
    if (
        receipt["schema"] != SCHEMA
        or receipt["status"] != "SEALED_NONPERSONAL_FUTURE_SCREENING_GATE_NO_AUDIT_CREDIT"
        or receipt["requisition_id"] != REQUISITION
        or receipt["branch_ids"] != BRANCHES
        or receipt["source_sha256"] != pins
        or receipt["matrix_sha256"] != matrix_pins
        or receipt["routes"] != routes
        or receipt["native_count"] != 12
        or receipt["population"] != "ONE_SYNTHETIC_REQUISITION_NOT_WORKFORCE_OR_SCREENING_CENSUS"
        or receipt["messy_open_exception"] != EXCEPTION
        or receipt["qualified_applicability"] != "PENDING_NOT_ASSERTED"
        or any(
            receipt[key] is not False
            for key in (
                "candidate_or_personal_data",
                "screening_result",
                "actual_employment_assignment_or_access",
                "actual_2027_operation",
                "source_complete",
                "audit_task_credit",
                "active_P1_mutated",
            )
        )
    ):
        raise CompanyStoreError("Selected screening receipt claims unsupported operation")
    originals = []
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok" or any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "access_events", "collections")
        ):
            raise CompanyStoreError("Screening source integrity/audit access differs")
        rows = db.execute("SELECT * FROM versions ORDER BY rowid").fetchall()
        owners = {
            (r["branch"], r["system"], r["owner"]) for r in db.execute("SELECT * FROM systems")
        }
        if len(rows) != 12 or owners != {
            (branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in (
                ("people_requirement_intake", "AS-P006"),
                ("security_requirement_input", "AS-P008"),
                ("people_assignment_gate", "AS-P006"),
            )
        }:
            raise CompanyStoreError("Screening native population/custody differs")
        start = datetime.fromisoformat(_time(START))
        for kind, branch in BRANCHES.items():
            selected = [row for row in rows if row["branch"] == branch]
            if len(selected) != len(PLAN[kind]):
                raise CompanyStoreError("Screening branch count differs")
            previous = None
            for row, (system, record, minute) in zip(selected, PLAN[kind], strict=True):
                at = (start + timedelta(minutes=minute)).isoformat(timespec="microseconds")
                body = {
                    **_body(kind, record),
                    "record_id": record,
                    "event_at": at,
                    "previous_source": previous,
                }
                if (
                    row["company"] != COMPANY
                    or row["version"] != 1
                    or (row["system"], row["record"]) != (system, record)
                    or row["event_at"] != at
                    or row["available_at"] != at
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or row["content"] != encoded(body)
                    or row["sha256"] != sha(row["content"])
                    or json.loads(row["provenance"])
                    != {
                        "source_reference": REQUISITION,
                        "source_sha256": pins,
                        "matrix_sha256": matrix_pins[MATRIX],
                        "control_ids": [CONTROL],
                        "operational_fact_status": "FUTURE_NONPERSONAL_LOCAL_EXERCISE_ONLY",
                    }
                ):
                    raise CompanyStoreError("Screening source chronology/content differs")
                imported = datetime.fromisoformat(row["imported_at"])
                if (
                    imported.tzinfo is None
                    or imported.astimezone(UTC) > datetime.now(UTC)
                    or imported.astimezone(UTC).date().isoformat() < AS_OF
                ):
                    raise CompanyStoreError("Screening import clock differs")
                item = {
                    key: row[key]
                    for key in (
                        "company",
                        "branch",
                        "system",
                        "record",
                        "version",
                        "event_at",
                        "available_at",
                        "imported_at",
                        "sha256",
                    )
                }
                originals.append(item)
                previous = {key: item[key] for key in ("system", "record", "version", "sha256")}
    if originals != receipt["native_originals"]:
        raise CompanyStoreError("Screening receipt/native tuples differ")
    if any(_private(path) != identities[name] for name, path in paths.items()):
        raise CompanyStoreError("Screening source changed during read")
    if any(
        Path(str(database) + suffix).exists() or Path(str(database) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Screening sidecar appeared during read")
    return {
        "schema": "SH_PPL002_SELECTED_SCREENING_VERIFICATION_V1",
        "status": "SELECTED_NONPERSONAL_FUTURE_NEGATIVE_GATE_INDEPENDENT_REVIEW_REQUIRED",
        "source_sha256": {name: identity[-1] for name, identity in identities.items()},
        "native_originals": originals,
        "native_count": 12,
        "branch_counts": {"CLEAN": 5, "MESSY": 7},
        "route_disposition": routes,
        "routes_per_side": {"A": 3, "B": 3},
        "messy_exception_open": EXCEPTION,
        "qualified_applicability": "PENDING_NOT_ASSERTED",
        "actual_person_or_screening_result": False,
        "employment_assignment_or_access": False,
        "source_complete": False,
        "audit_task_credit": False,
        "active_P1_mutated": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("create", "verify"))
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    args = parser.parse_args()
    action = create if args.command == "create" else verify
    print(
        json.dumps(
            action(
                args.destination,
                repository=args.repository,
                private_repository=args.private_repository,
            ),
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
