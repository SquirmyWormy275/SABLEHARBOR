"""Selected fictional conduct-code and attestation history, without audit credit."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import stat
import tempfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_ETH001_SELECTED_CONDUCT_SOURCE_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
CONTROL = "SH-ETH-001"
CODE = "SIM-ETH001-CODE-2027-001"
EXCEPTION = "LOCAL-ETH001-FALSE-CLEAN-EXC-001"
PEOPLE = ("AS-P005", "AS-P013")
BRANCHES = {"CLEAN": "ETH001-CLEAN", "MESSY": "ETH001-MESSY"}
START = "2027-08-16T09:00:00+00:00"
DUE = "2027-08-18T17:00:00+00:00"
AS_OF = "2026-09-30"
CANON_RECONCILIATION = "2026_ENTERPRISE_CODE_FUTURE_OPEN;_2027_LOCAL_APPROVAL_FICTIONAL_ONLY"
MATRIX = (
    "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/run-v2/MATRIX.json"
)
MATRIX_REVIEW = (
    "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/"
    "independent-review-v2/REVIEW.json"
)
MATRIX_SHA = "e9477d2074bebce185e412a3ee7c424ded395c1a1128a7c918a94f6acbd1e327"
MATRIX_REVIEW_SHA = "c4064f6217c0e7f69276adc71004d6da7971867ccf3d844a3e198145cec31ace"
CANON_SHA = {
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md": (
        "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433"
    ),
    "docs/controls/CCF_CONTROL_OBJECTIVES_v0.1.md": (
        "db7a189139b86fb51d684b6af3e681002b5e0f3f81c38c5bc15a61c20e4a59a3"
    ),
    "docs/controls/CCF_POLICY_AND_ARTIFACT_INVENTORY_v0.1.md": (
        "395198400d72211716f26f7376dd362993e538d0c081fdaaee3d148d642ea0dd"
    ),
    "docs/governance/PEOPLE_AND_CULTURE_DOCTRINE.md": (
        "9e8c8b6b3b3ce8500553adfc0e35e94956a8251d395fd8d39355f3d84c1dc5ee"
    ),
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md": (
        "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751"
    ),
    "docs/governance/ENTERPRISE_COORDINATION_2026-09-13.md": (
        "3f358e1a89ba640ab35be53682388e7d9604c0f5627dfeb5a176a6de1e7c2da9"
    ),
    "docs/organization/source/chartbook.json": (
        "6ba4f1ed1a14581455a62c3e79a29ca59dbaf1270dfb0db850c0376c15507b49"
    ),
    "docs/structured/enterprise_leadership_2026-09-13.json": (
        "90ec45642cc50219544910e60e4bf6d28b810302c62f29c5936bf965501d673d"
    ),
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md": (
        "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496"
    ),
    "enterprise/audit_suite/ETH001_SELECTED_CONDUCT_2027_PROPOSAL.md": (
        "d6a62a9a08c8ba6901b90299e51d0d17374da3baa955c65cc3acafb8088a45ef"
    ),
}
PLAN = {
    "CLEAN": (
        ("conduct_code", "DRAFT", 0, 0),
        ("conduct_code", "FICTIONAL-LOCAL-APPROVAL", 10, 0),
        ("conduct_distribution", "SELECTED-ROSTER", 20, 0),
        ("conduct_distribution", "DISTRIBUTION-AS-P005", 30, 0),
        ("conduct_distribution", "DISTRIBUTION-AS-P013", 31, 0),
        ("selected_attestation", "ACK-AS-P005", 60, 0),
        ("selected_attestation", "ACK-AS-P013", 70, 0),
        ("conduct_reconciliation", "FINAL", 80, 0),
    ),
    "MESSY": (
        ("conduct_code", "DRAFT", 0, 0),
        ("conduct_code", "FICTIONAL-LOCAL-APPROVAL", 10, 0),
        ("conduct_distribution", "SELECTED-ROSTER", 20, 0),
        ("conduct_distribution", "DISTRIBUTION-AS-P005", 30, 0),
        ("conduct_distribution", "DISTRIBUTION-AS-P013", 31, 0),
        ("selected_attestation", "ACK-AS-P005", 60, 0),
        ("conduct_reconciliation", "FALSE-CLEAN", 5760, 5),
        ("conduct_reconciliation", "MISSING-DISCOVERY", 5780, 1),
        ("selected_attestation", "LATE-ACK-AS-P013", 5800, 0),
        ("conduct_reconciliation", "CORRECTION", 5810, 0),
        ("conduct_reconciliation", "FINAL", 5820, 0),
    ),
}
TASK_IDS = {
    "TASK-SH-ETH-001-corporate-ACTION-H-SANCTIONS",
    "TASK-SH-ETH-001-corporate-IMPLEMENTATION",
    "TASK-SH-ETH-001-corporate-TOD",
    "TASK-SH-ETH-001-corporate-TOE",
}
ORIGINAL_FIELDS = (
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
SYSTEM_OWNERS = {
    "conduct_code": "AS-P003",
    "conduct_distribution": "AS-P006",
    "selected_attestation": "AS-P006",
    "conduct_reconciliation": "AS-P006",
}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private_file(path: Path) -> tuple:
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise CompanyStoreError("Private source path alias forbidden")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077:
        raise CompanyStoreError("Ordinary private source file required")
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, _digest(path)


def _pins(repository: Path) -> dict:
    pins = {}
    for name, expected in CANON_SHA.items():
        path = repository / name
        if path.is_symlink() or not path.is_file() or _digest(path) != expected:
            raise CompanyStoreError(f"Conduct canon pin differs: {name}")
        pins[name] = expected
    module = "enterprise/audit_suite/company_eth001_conduct_attestation.py"
    pins[module] = _digest(repository / module)
    return pins


def _actors(repository: Path) -> None:
    chart = json.loads((repository / "docs/organization/source/chartbook.json").read_bytes())
    leadership = json.loads(
        (repository / "docs/structured/enterprise_leadership_2026-09-13.json").read_bytes()
    )
    expected = {
        "AS-P003": ("Helena Ward", "General Counsel", "ROLE-29"),
        "AS-P006": ("Sofia Hart", "Head of People and Culture", "ROLE-32"),
        "AS-P005": ("Martin Ives", "Head of Risk and Compliance", "ROLE-31"),
        "AS-P013": ("Erin Cross", "Procurement and Supplier Risk Lead", "AS-ROLE-PROCUREMENT"),
    }
    for actor, (name, title, role) in expected.items():
        card = [
            node
            for node in chart["nodes"]
            if node.get("person_id") == actor and node.get("type") == "person"
        ]
        leader = [person for person in leadership["people"] if person["person_id"] == actor]
        if (
            len(card) != 1
            or len(leader) != 1
            or (card[0]["name"], card[0]["title"], card[0]["role_id"]) != (name, title, role)
            or card[0]["title_state"] != "DELEGATED_FICTIONAL_APPOINTMENT_PENDING_ACCEPTANCE"
            or (leader[0]["name"], leader[0]["title"], leader[0]["org_role_id"])
            != (name, title, role)
        ):
            raise CompanyStoreError("Proposed conduct actor mapping differs")


def _routes(private_repository: Path) -> tuple[dict, dict]:
    paths = {MATRIX: MATRIX_SHA, MATRIX_REVIEW: MATRIX_REVIEW_SHA}
    before = {}
    for name, expected in paths.items():
        before[name] = _private_file(private_repository / name)
        if before[name][-1] != expected:
            raise CompanyStoreError("Reviewed conduct route matrix pin differs")
    review = json.loads((private_repository / MATRIX_REVIEW).read_bytes())
    if review.get("verdict") != "PASS_READ_ONLY_CANDIDATE_MATRIX_FOR_INTEGRATION":
        raise CompanyStoreError("Conduct route matrix independent review missing")
    matrix = json.loads((private_repository / MATRIX).read_bytes())
    if any(_private_file(private_repository / name) != state for name, state in before.items()):
        raise CompanyStoreError("Reviewed conduct route matrix changed during read")
    result = {}
    for side in "AB":
        controls = [
            control
            for family in matrix["sides"][side]["families"]
            for control in family["controls"]
            if control["control_id"] == CONTROL
        ]
        if len(controls) != 1 or {t["task_id"] for t in controls[0]["tasks"]} != TASK_IDS:
            raise CompanyStoreError("Exact four ETH001 task routes differ")
        tasks = controls[0]["tasks"]
        sanctions = next(t for t in tasks if t["task_id"].endswith("ACTION-H-SANCTIONS"))
        if "An acknowledgment without enforcement evidence cannot pass" not in sanctions[
            "authored_test_clause"
        ] or any(
            t["current_status"] != "NOT_STARTED"
            or t["current_conclusion"] != "NOT_RUN"
            or t["task_credit"] is not False
            for t in tasks
        ):
            raise CompanyStoreError("ETH001 sanctions or uncredited route boundary differs")
        result[side] = [
            {
                "task_id": t["task_id"],
                "authored_test_clause": t["authored_test_clause"],
                "remaining_test_gate": t["remaining_test_gate"],
                "current_status": "NOT_STARTED",
                "current_conclusion": "NOT_RUN",
                "task_credit": False,
            }
            for t in tasks
        ]
    return result, paths


def _ref(original: dict) -> dict:
    return {field: original[field] for field in ORIGINAL_FIELDS}


def _body(scenario: str, record: str, prior: dict | None, refs: dict) -> dict:
    common = {
        "schema": SCHEMA,
        "code_id": CODE,
        "control_id": CONTROL,
        "scenario": scenario,
        "qualification": "FUTURE_FICTIONAL_SELECTED_CONDUCT_EXERCISE_ONLY",
        "canon_reconciliation": CANON_RECONCILIATION,
        "real_enterprise_code_approved": False,
        "actual_employee_action_or_signature": False,
        "workforce_population_complete": False,
        "substantiated_case_evidence_present": False,
        "no_case_population_decision": False,
        "sanctions_or_performance_review_conclusion": False,
        "audit_task_credit": False,
        "previous_original": prior,
    }
    if record == "DRAFT":
        detail = {
            "scenario_actor": "AS-P003",
            "document_state": "AUTHORED_TRAINING_DRAFT_ONLY",
            "selected_expectations": [
                "honest records",
                "conflict disclosure",
                "protected speak-up",
                "no retaliation",
            ],
        }
    elif record == "FICTIONAL-LOCAL-APPROVAL":
        detail = {
            "scenario_content_actor": "AS-P003",
            "scenario_learning_actor": "AS-P006",
            "approved_draft_original": refs["DRAFT"],
            "document_state": "FICTIONAL_LOCAL_TRAINING_APPROVAL_ONLY",
            "actual_canonical_approval_or_board_action": False,
        }
    elif record == "SELECTED-ROSTER":
        detail = {
            "scenario_actor": "AS-P006",
            "selected_person_ids": list(PEOPLE),
            "selected_population_status": "TWO_SCENARIO_IDENTITIES_NOT_WORKFORCE_CENSUS",
            "fictional_approval_original": refs["FICTIONAL-LOCAL-APPROVAL"],
            "due_at": DUE,
        }
    elif record.startswith("DISTRIBUTION-"):
        subject = record.removeprefix("DISTRIBUTION-")
        detail = {
            "scenario_actor": "AS-P006",
            "scenario_recipient_id": subject,
            "fictional_delivery": True,
            "actual_notice_sent": False,
            "fictional_approval_original": refs["FICTIONAL-LOCAL-APPROVAL"],
            "selected_roster_original": refs["SELECTED-ROSTER"],
        }
    elif record in ("ACK-AS-P005", "ACK-AS-P013", "LATE-ACK-AS-P013"):
        subject = record.removeprefix("LATE-").removeprefix("ACK-")
        detail = {
            "scenario_subject_id": subject,
            "scenario_attribution": "AUTHORED_PERSON_EVENT_NO_REAL_SIGNATURE",
            "fictional_acknowledgment": True,
            "actual_employee_attestation": False,
            "late_against_selected_due": record.startswith("LATE-"),
            "due_at": DUE,
            "fictional_approval_original": refs["FICTIONAL-LOCAL-APPROVAL"],
            "distribution_original": refs[f"DISTRIBUTION-{subject}"],
        }
    elif record == "FALSE-CLEAN":
        detail = {
            "scenario_actor": "AS-P006",
            "claimed_selected_acknowledgments": 2,
            "actual_originals_available": [refs["ACK-AS-P005"]],
            "missing_person_id": "AS-P013",
            "false_clean": True,
            "exception_id": EXCEPTION,
            "external_certification": False,
        }
    elif record == "MISSING-DISCOVERY":
        detail = {
            "scenario_actor": "AS-P006",
            "false_clean_original": refs["FALSE-CLEAN"],
            "missing_person_id": "AS-P013",
            "exception_id": EXCEPTION,
            "exception_open": True,
        }
    elif record == "CORRECTION":
        detail = {
            "scenario_actor": "AS-P006",
            "false_clean_original": refs["FALSE-CLEAN"],
            "late_ack_original": refs["LATE-ACK-AS-P013"],
            "historical_false_clean_erased": False,
            "exception_open": True,
        }
    elif record == "FINAL":
        late = scenario == "MESSY"
        detail = {
            "scenario_actor": "AS-P006",
            "selected_acknowledgment_originals": [
                refs["ACK-AS-P005"],
                refs["LATE-ACK-AS-P013" if late else "ACK-AS-P013"],
            ],
            "selected_acknowledgment_count": 2,
            "selected_late_count": int(late),
            "open_exception_ids": [EXCEPTION] if late else [],
            "historical_false_clean_erased": False,
            "fictional_approval_original": refs["FICTIONAL-LOCAL-APPROVAL"],
            "final_state": (
                "SELECTED_COMPLETE_WITH_LATE_ACK_AND_OPEN_EXCEPTION"
                if late
                else "SELECTED_TWO_ON_TIME_NO_LOCAL_EXCEPTION"
            ),
        }
    else:
        raise CompanyStoreError("Unknown selected conduct record")
    return {**common, **detail}


def _provenance(pins: dict, route_pins: dict) -> dict:
    return {
        "source_reference": CODE,
        "source_sha256": pins,
        "matrix_sha256": route_pins[MATRIX],
        "control_ids": [CONTROL],
        "operational_fact_status": "FUTURE_FICTIONAL_LOCAL_EXERCISE_ONLY",
        "canon_reconciliation": CANON_RECONCILIATION,
    }


def _input_digest(
    branch: str,
    system: str,
    record: str,
    event: str,
    available: str,
    provenance: dict,
    content: bytes,
) -> str:
    return sha(
        encoded(
            [
                [COMPANY, branch, system, record],
                0,
                event,
                available,
                "AUTHORED_TRAINING_SOURCE",
                provenance,
                sha(content),
            ]
        )
    )


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Create one private immutable Clean/Messy source pair, never an audit pair."""
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(path.is_symlink() for path in (destination, *destination.parents))
    ):
        raise CompanyStoreError("New private conduct destination required")
    pins = _pins(repository)
    _actors(repository)
    routes, route_pins = _routes(private_repository)
    start = datetime.fromisoformat(_time(START))
    if start.date().isoformat() <= AS_OF or datetime.fromisoformat(DUE) <= start:
        raise CompanyStoreError("Prospective conduct chronology required")
    originals = []
    with tempfile.TemporaryDirectory(prefix="eth001-stage-", dir=destination.parent) as staged:
        stage = Path(staged)
        store = CompanyStore(stage)
        for scenario, branch in BRANCHES.items():
            for system, owner in SYSTEM_OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            refs: dict[str, dict] = {}
            previous = None
            for system, record, minute, lag in PLAN[scenario]:
                event = _time((start + timedelta(minutes=minute)).isoformat())
                available = _time((start + timedelta(minutes=minute + lag)).isoformat())
                content = encoded(
                    {
                        **_body(scenario, record, previous, refs),
                        "record_id": record,
                        "event_at": event,
                        "available_at": available,
                    }
                )
                provenance = _provenance(pins, route_pins)
                command_id = "ETH1-" + sha(encoded([branch, system, record]))
                original = store.append_version(
                    COMPANY,
                    branch,
                    system,
                    record,
                    expected_version=0,
                    command_id=command_id,
                    event_at=event,
                    available_at=available,
                    content=content,
                    provenance=provenance,
                )
                originals.append(
                    {
                        **original,
                        "command_id": command_id,
                        "input_digest": _input_digest(
                            branch, system, record, event, available, provenance, content
                        ),
                    }
                )
                previous = refs[record] = _ref(original)
        receipt = {
            "schema": SCHEMA,
            "status": "SEALED_SELECTED_FUTURE_FICTIONAL_COMPANY_NATIVE_PAIR_NO_AUDIT_CREDIT",
            "code_id": CODE,
            "branch_ids": BRANCHES,
            "selected_person_ids": list(PEOPLE),
            "selected_population": "TWO_FICTIONAL_PERSON_IDENTITIES_NOT_WORKFORCE_CENSUS",
            "source_sha256": pins,
            "route_sha256": route_pins,
            "route_disposition": routes,
            "native_originals": originals,
            "native_count": len(originals),
            "branch_counts": {scenario: len(plan) for scenario, plan in PLAN.items()},
            "canon_reconciliation": CANON_RECONCILIATION,
            "real_enterprise_code_approved": False,
            "fictional_local_approval_only": True,
            "clean_selected_on_time_count": 2,
            "messy_selected_late_count": 1,
            "messy_historical_false_clean_exception_open": True,
            "actual_workforce_population_complete": False,
            "substantiated_case_evidence_present": False,
            "no_case_population_decision": False,
            "sanctions_or_performance_review_conclusion": False,
            "actual_2027_operation": False,
            "actual_distribution_or_attestation": False,
            "source_complete": False,
            "audit_task_credit": False,
            "active_P1_mutated": False,
        }
        source = stage / "SOURCE_RECEIPT.json"
        source.write_bytes(encoded(receipt))
        source.chmod(0o600)
        database = stage / "company.sqlite3"
        manifest = {
            "schema": "SH_ETH001_SELECTED_CONDUCT_MANIFEST_V1",
            "status": "SEALED_PRIVATE_FUTURE_SOURCE_ONLY",
            "source_receipt_sha256": _digest(source),
            "native_db_sha256": _digest(database),
            "module_sha256": pins["enterprise/audit_suite/company_eth001_conduct_attestation.py"],
            "native_count": len(originals),
            "audit_task_credit": False,
            "active_P1_mutated": False,
        }
        path = stage / "RUN-MANIFEST.json"
        path.write_bytes(encoded(manifest))
        path.chmod(0o600)
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private_repository)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Recompute every native original, source pin, authority limit and exception."""
    raw = Path(destination).absolute()
    if any(path.is_symlink() for path in (raw, *raw.parents)):
        raise CompanyStoreError("Private conduct source directory alias forbidden")
    destination = raw.resolve(strict=True)
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    database = destination / "company.sqlite3"
    if any(
        Path(str(database) + suffix).exists() or Path(str(database) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Frozen conduct source has SQLite sidecar")
    if destination.stat().st_mode & 0o077 or {p.name for p in destination.iterdir()} != {
        "SOURCE_RECEIPT.json",
        "RUN-MANIFEST.json",
        "company.sqlite3",
    }:
        raise CompanyStoreError("Exact private conduct source layout required")
    paths = {
        name: destination / name
        for name in ("SOURCE_RECEIPT.json", "RUN-MANIFEST.json", "company.sqlite3")
    }
    before = {name: _private_file(path) for name, path in paths.items()}
    pins = _pins(repository)
    _actors(repository)
    routes, route_pins = _routes(private_repository)
    receipt = json.loads(paths["SOURCE_RECEIPT.json"].read_bytes())
    manifest = json.loads(paths["RUN-MANIFEST.json"].read_bytes())
    if manifest != {
        "schema": "SH_ETH001_SELECTED_CONDUCT_MANIFEST_V1",
        "status": "SEALED_PRIVATE_FUTURE_SOURCE_ONLY",
        "source_receipt_sha256": before["SOURCE_RECEIPT.json"][-1],
        "native_db_sha256": before["company.sqlite3"][-1],
        "module_sha256": pins["enterprise/audit_suite/company_eth001_conduct_attestation.py"],
        "native_count": 19,
        "audit_task_credit": False,
        "active_P1_mutated": False,
    }:
        raise CompanyStoreError("Selected conduct manifest differs")
    if (
        receipt.get("schema") != SCHEMA
        or receipt.get("status")
        != "SEALED_SELECTED_FUTURE_FICTIONAL_COMPANY_NATIVE_PAIR_NO_AUDIT_CREDIT"
        or receipt.get("code_id") != CODE
        or receipt.get("branch_ids") != BRANCHES
        or receipt.get("selected_person_ids") != list(PEOPLE)
        or receipt.get("selected_population")
        != "TWO_FICTIONAL_PERSON_IDENTITIES_NOT_WORKFORCE_CENSUS"
        or receipt.get("source_sha256") != pins
        or receipt.get("route_sha256") != route_pins
        or receipt.get("route_disposition") != routes
        or receipt.get("native_count") != 19
        or receipt.get("branch_counts") != {"CLEAN": 8, "MESSY": 11}
        or receipt.get("canon_reconciliation") != CANON_RECONCILIATION
        or receipt.get("fictional_local_approval_only") is not True
        or receipt.get("clean_selected_on_time_count") != 2
        or receipt.get("messy_selected_late_count") != 1
        or receipt.get("messy_historical_false_clean_exception_open") is not True
        or any(
            receipt.get(key) is not False
            for key in (
                "real_enterprise_code_approved",
                "actual_workforce_population_complete",
                "substantiated_case_evidence_present",
                "no_case_population_decision",
                "sanctions_or_performance_review_conclusion",
                "actual_2027_operation",
                "actual_distribution_or_attestation",
                "source_complete",
                "audit_task_credit",
                "active_P1_mutated",
            )
        )
    ):
        raise CompanyStoreError("Selected conduct receipt overclaims authority or completion")
    expected = []
    start = datetime.fromisoformat(_time(START))
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Native conduct database integrity failed")
        systems = {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        }
        if systems != {
            (COMPANY, branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in SYSTEM_OWNERS.items()
        }:
            raise CompanyStoreError("Conduct source system custody differs")
        if db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != 19 or any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "collections", "access_events")
        ):
            raise CompanyStoreError("Conduct source rows or audit journals differ")
        for scenario, branch in BRANCHES.items():
            refs: dict[str, dict] = {}
            previous = None
            for system, record, minute, lag in PLAN[scenario]:
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=1",
                    (COMPANY, branch, system, record),
                ).fetchone()
                event = _time((start + timedelta(minutes=minute)).isoformat())
                available = _time((start + timedelta(minutes=minute + lag)).isoformat())
                body = encoded(
                    {
                        **_body(scenario, record, previous, refs),
                        "record_id": record,
                        "event_at": event,
                        "available_at": available,
                    }
                )
                if (
                    row is None
                    or row["event_at"] != event
                    or row["available_at"] != available
                    or not row["imported_at"].startswith("2026-")
                    or _time(row["imported_at"]) != row["imported_at"]
                    or (previous is not None and row["imported_at"] < previous["imported_at"])
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or row["provenance"]
                    != json.dumps(
                        _provenance(pins, route_pins), sort_keys=True, separators=(",", ":")
                    )
                    or row["content"] != body
                    or row["sha256"] != sha(body)
                    or row["command_id"] != "ETH1-" + sha(encoded([branch, system, record]))
                    or row["input_digest"]
                    != _input_digest(
                        branch,
                        system,
                        record,
                        event,
                        available,
                        _provenance(pins, route_pins),
                        body,
                    )
                ):
                    raise CompanyStoreError(
                        "Exact conduct original, provenance or three clocks differ"
                    )
                original = {
                    key: (json.loads(row[key]) if key == "provenance" else row[key])
                    for key in (
                        "company",
                        "branch",
                        "system",
                        "record",
                        "version",
                        "event_at",
                        "available_at",
                        "imported_at",
                        "origin",
                        "provenance",
                        "sha256",
                        "command_id",
                        "input_digest",
                    )
                }
                expected.append(original)
                previous = refs[record] = _ref(original)
        if receipt.get("native_originals") != expected:
            raise CompanyStoreError("Selected conduct original-version receipt differs")
    if any(_private_file(path) != before[name] for name, path in paths.items()):
        raise CompanyStoreError("Selected conduct source changed during verification")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    result = (
        create(
            args.destination, repository=args.repository, private_repository=args.private_repository
        )
        if args.action == "create"
        else verify(
            args.destination, repository=args.repository, private_repository=args.private_repository
        )
    )
    print(
        json.dumps(
            {key: result[key] for key in ("schema", "native_count", "branch_counts")},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
