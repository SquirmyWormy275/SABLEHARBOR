"""Payload-free prospective speak-up routing marker, independent of audit state."""

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

SCHEMA = "SH_ETH003_SELECTED_SPEAKUP_SOURCE_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
CASE = "SIM-ETH003-SPEAKUP-MARKER-001"
EXCEPTION = "LOCAL-ETH003-ROUTING-EXC-001"
START = "2027-06-08T09:00:00+00:00"
AS_OF = "2026-09-29"
CONTROL = "SH-ETH-003"
BRANCHES = {"CLEAN": "ETH003-CLEAN", "MESSY": "ETH003-MESSY"}
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
    "docs/governance/committees/AUDIT_AND_COMPLIANCE_COMMITTEE_CHARTER.md": (
        "d59a708310e56dbe67fc28629efbedd4f790a4ef9765d841b651f3335ab8e993"
    ),
    "docs/governance/BOARD_AND_CAPITAL_GOVERNANCE_v1.0.1.md": (
        "dc1e2e3ea6e7ea8d364eae87bd890a8c79a5a577a7554ed371cda3810ea945a8"
    ),
    "docs/governance/PEOPLE_AND_CULTURE_DOCTRINE.md": (
        "9e8c8b6b3b3ce8500553adfc0e35e94956a8251d395fd8d39355f3d84c1dc5ee"
    ),
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md": (
        "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433"
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
        ("report_intake", "SCOPE", 0),
        ("report_intake", "MARKER", 5),
        ("report_intake", "RESTRICTED-ROUTE", 7),
        ("separate_triage", "TRIAGE", 12),
        ("protective_handling", "HANDLING", 16),
        ("case_state", "FINAL", 25),
    ),
    "MESSY": (
        ("report_intake", "SCOPE", 0),
        ("report_intake", "MARKER", 5),
        ("report_intake", "MISROUTE", 7),
        ("separate_triage", "ROUTING-DISCOVERY", 12),
        ("report_intake", "RESTRICTED-CORRECTION", 14),
        ("separate_triage", "TRIAGE", 18),
        ("protective_handling", "HANDLING", 21),
        ("case_state", "FINAL", 25),
    ),
}
TASK_IDS = {
    "TASK-SH-ETH-003-corporate-ACTION-H-REGULATOR",
    "TASK-SH-ETH-003-corporate-ACTION-H-SANCTIONS",
    "TASK-SH-ETH-003-corporate-IMPLEMENTATION",
    "TASK-SH-ETH-003-corporate-TOD",
    "TASK-SH-ETH-003-corporate-TOE",
}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private(path: Path) -> tuple:
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise CompanyStoreError("Private speak-up source alias forbidden")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077:
        raise CompanyStoreError("Ordinary private speak-up file required")
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, _digest(path)


def _pins(repository: Path) -> dict:
    for name, expected in CANON_PINS.items():
        path = repository / name
        if path.is_symlink() or not path.is_file() or _digest(path) != expected:
            raise CompanyStoreError(f"Speak-up canon differs: {name}")
    code = "enterprise/audit_suite/company_eth003_speakup_activity.py"
    return {**CANON_PINS, code: _digest(repository / code)}


def _actors(repository: Path) -> None:
    chart = json.loads((repository / "docs/organization/source/chartbook.json").read_bytes())
    leadership = json.loads(
        (repository / "docs/structured/enterprise_leadership_2026-09-13.json").read_bytes()
    )
    expected = {
        "AS-P003": ("Helena Ward", "General Counsel", "ROLE-29"),
        "AS-P005": ("Martin Ives", "Head of Risk and Compliance", "ROLE-31"),
        "AS-P006": ("Sofia Hart", "Head of People and Culture", "ROLE-32"),
    }
    for actor, (name, title, role) in expected.items():
        card = [
            node
            for node in chart["nodes"]
            if node.get("person_id") == actor and node.get("type") == "person"
        ]
        leader = [p for p in leadership["people"] if p["person_id"] == actor]
        if (
            len(card) != 1
            or len(leader) != 1
            or (card[0]["name"], card[0]["title"], card[0]["role_id"]) != (name, title, role)
            or card[0]["title_state"] != "DELEGATED_FICTIONAL_APPOINTMENT_PENDING_ACCEPTANCE"
            or leader[0]["org_role_id"] != role
        ):
            raise CompanyStoreError("Selected proposed speak-up role mapping differs")


def _routes(private_repository: Path) -> tuple[dict, dict]:
    identities = {}
    for name, expected in MATRIX_PINS.items():
        identity = _private(private_repository / name)
        if identity[-1] != expected:
            raise CompanyStoreError("Frozen speak-up route input differs")
        identities[name] = identity
    matrix = json.loads((private_repository / MATRIX).read_bytes())
    review = json.loads((private_repository / MATRIX_REVIEW).read_bytes())
    if any(
        _private(private_repository / name) != identity for name, identity in identities.items()
    ):
        raise CompanyStoreError("Frozen speak-up route input changed during read")
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
            raise CompanyStoreError("Exact five speak-up routes differ")
        rows = controls[0]["tasks"]
        if any(
            row["current_status"] != "NOT_STARTED"
            or row["current_conclusion"] != "NOT_RUN"
            or row["task_credit"] is not False
            for row in rows
        ):
            raise CompanyStoreError("Frozen speak-up route was credited")
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
        "case_id": CASE,
        "control_id": CONTROL,
        "qualification": "PAYLOAD_FREE_FUTURE_SYNTHETIC_SPEAKUP_ROUTING_MARKER",
        "reporter_identity": None,
        "report_payload": None,
        "real_report_or_allegation": False,
        "personal_data": False,
        "substantiated_case": False,
        "actual_retaliation": False,
        "sanction_or_performance_decision": False,
        "regulator_request_or_response": False,
        "investigation_complete": False,
        "committee_disposition": "PENDING_NOT_ASSERTED",
        "audit_task_credit": False,
    }
    stage = {
        "SCOPE": {
            "actor": "AS-P006",
            "selected_case_count": 1,
            "population": "ONE_SYNTHETIC_MARKER_NOT_HOTLINE_OR_EMPLOYEE_CENSUS",
        },
        "MARKER": {
            "actor": "AS-P006",
            "marker_class": "SYNTHETIC_RECORDS_PRESERVATION_CONCERN_NO_ALLEGATION_DETAIL",
            "intake_status": "LOCAL_FICTIONAL_EXERCISE_ONLY",
        },
        "RESTRICTED-ROUTE": {
            "actor": "AS-P006",
            "recipient": "AS-P005_SEPARATE_RISK_CONTACT",
            "case_existence_sent_to_implicated_line": False,
        },
        "MISROUTE": {
            "actor": "AS-P006",
            "recipient": "SCENARIO_IMPLICATED_LINE_ROLE_NOT_ACTUAL_PERSON",
            "exposure": "SYNTHETIC_CASE_EXISTENCE_ONLY_NO_IDENTITY_OR_PAYLOAD",
            "case_existence_sent_to_implicated_line": True,
            "exception_id": EXCEPTION,
        },
        "ROUTING-DISCOVERY": {
            "actor": "AS-P005",
            "finding": "LOCAL_CASE_EXISTENCE_MISROUTE_REQUIRES_CORRECTION",
            "exception_id": EXCEPTION,
        },
        "RESTRICTED-CORRECTION": {
            "actor": "AS-P006",
            "recipient": "AS-P005_SEPARATE_RISK_CONTACT",
            "prior_misroute_erased": False,
            "exception_id": EXCEPTION,
        },
        "HANDLING": {
            "actor": "AS-P003",
            "status": "LOCAL_PROTECTIVE_HANDLING_RECOMMENDATION_ONLY",
            "restricted_access_requested": True,
            "actual_person_protection_or_legal_opinion": False,
            "exception_id": EXCEPTION if branch == "MESSY" else None,
        },
    }
    if record == "TRIAGE":
        stage[record] = {
            "actor": "AS-P005",
            "status": "SEPARATE_SCOPED_TRIAGE_PENDING_INVESTIGATION",
            "referral_to_committee": "PENDING_NOT_SUBMITTED_OR_ACCEPTED",
            "exception_id": EXCEPTION if branch == "MESSY" else None,
        }
    if record == "FINAL":
        stage[record] = {
            "actor": "AS-P005",
            "current_route": "RESTRICTED_LOCAL_RISK_CONTACT",
            "open_exception_ids": [EXCEPTION] if branch == "MESSY" else [],
            "misroute_preserved": branch == "MESSY",
            "case_status": "INVESTIGATION_AND_COMMITTEE_DISPOSITION_PENDING",
        }
    return {**common, **stage[record]}


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Create one separate Clean/Messy native source without audit operations."""
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(p.is_symlink() for p in (destination, *destination.parents))
    ):
        raise CompanyStoreError("New private speak-up destination required")
    pins = _pins(repository)
    _actors(repository)
    routes, matrix_pins = _routes(private_repository)
    start = datetime.fromisoformat(_time(START))
    if start.date().isoformat() <= AS_OF:
        raise CompanyStoreError("Selected speak-up event must remain future fictional")
    originals = []
    with tempfile.TemporaryDirectory(prefix="eth003-stage-", dir=destination.parent) as temp:
        stage = Path(temp)
        store = CompanyStore(stage)
        for kind, branch in BRANCHES.items():
            for system, owner in (
                ("report_intake", "AS-P006"),
                ("separate_triage", "AS-P005"),
                ("protective_handling", "AS-P003"),
                ("case_state", "AS-P005"),
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
                    command_id="ETH3-" + sha(encoded([branch, system, record])),
                    event_at=at,
                    available_at=at,
                    content=encoded(body),
                    provenance={
                        "source_reference": CASE,
                        "source_sha256": pins,
                        "matrix_sha256": matrix_pins[MATRIX],
                        "control_ids": [CONTROL],
                        "operational_fact_status": "FUTURE_PAYLOAD_FREE_LOCAL_EXERCISE_ONLY",
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
            "status": "SEALED_PAYLOAD_FREE_FUTURE_COMPANY_SOURCE_NO_AUDIT_CREDIT",
            "case_id": CASE,
            "branch_ids": BRANCHES,
            "source_sha256": pins,
            "matrix_sha256": matrix_pins,
            "routes": routes,
            "native_originals": originals,
            "native_count": 14,
            "population": "ONE_SYNTHETIC_MARKER_NOT_HOTLINE_OR_EMPLOYEE_CENSUS",
            "messy_open_exception": EXCEPTION,
            "real_report_or_allegation": False,
            "personal_data": False,
            "actual_retaliation_or_sanction": False,
            "investigation_or_committee_disposition": "PENDING_NOT_ASSERTED",
            "actual_2027_operation": False,
            "source_complete": False,
            "audit_task_credit": False,
            "active_P1_mutated": False,
        }
        source = stage / "SOURCE_RECEIPT.json"
        source.write_bytes(encoded(receipt))
        source.chmod(0o600)
        manifest = {
            "schema": "SH_ETH003_SELECTED_SPEAKUP_MANIFEST_V1",
            "status": "SEALED_PRIVATE_FUTURE_SOURCE_ONLY",
            "source_receipt_sha256": _digest(source),
            "native_db_sha256": _digest(stage / "company.sqlite3"),
            "native_count": 14,
            "audit_task_credit": False,
            "active_P1_mutated": False,
        }
        path = stage / "RUN-MANIFEST.json"
        path.write_bytes(encoded(manifest))
        path.chmod(0o600)
        publish(stage, destination)
    return receipt


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Reperform the frozen selected source; do not read or write an engagement."""
    raw_destination = Path(destination).absolute()
    if any(p.is_symlink() for p in (raw_destination, *raw_destination.parents)):
        raise CompanyStoreError("Private speak-up directory alias forbidden")
    destination = raw_destination.resolve(strict=True)
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    if destination.stat().st_mode & 0o077:
        raise CompanyStoreError("Private speak-up directory required")
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
        raise CompanyStoreError("Frozen speak-up database has sidecar")
    pins = _pins(repository)
    _actors(repository)
    routes, matrix_pins = _routes(private_repository)
    receipt = json.loads(paths["SOURCE_RECEIPT.json"].read_bytes())
    manifest = json.loads(paths["RUN-MANIFEST.json"].read_bytes())
    if manifest != {
        "schema": "SH_ETH003_SELECTED_SPEAKUP_MANIFEST_V1",
        "status": "SEALED_PRIVATE_FUTURE_SOURCE_ONLY",
        "source_receipt_sha256": identities["SOURCE_RECEIPT.json"][-1],
        "native_db_sha256": identities["company.sqlite3"][-1],
        "native_count": 14,
        "audit_task_credit": False,
        "active_P1_mutated": False,
    }:
        raise CompanyStoreError("Selected speak-up manifest differs")
    if (
        receipt["schema"] != SCHEMA
        or receipt["status"] != "SEALED_PAYLOAD_FREE_FUTURE_COMPANY_SOURCE_NO_AUDIT_CREDIT"
        or receipt["case_id"] != CASE
        or receipt["branch_ids"] != BRANCHES
        or receipt["source_sha256"] != pins
        or receipt["matrix_sha256"] != matrix_pins
        or receipt["routes"] != routes
        or receipt["native_count"] != 14
        or receipt["population"] != "ONE_SYNTHETIC_MARKER_NOT_HOTLINE_OR_EMPLOYEE_CENSUS"
        or receipt["messy_open_exception"] != EXCEPTION
        or receipt["investigation_or_committee_disposition"] != "PENDING_NOT_ASSERTED"
        or any(
            receipt[key] is not False
            for key in (
                "real_report_or_allegation",
                "personal_data",
                "actual_retaliation_or_sanction",
                "actual_2027_operation",
                "source_complete",
                "audit_task_credit",
                "active_P1_mutated",
            )
        )
    ):
        raise CompanyStoreError("Selected speak-up receipt claims unsupported completion")
    originals = []
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok" or any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "access_events", "collections")
        ):
            raise CompanyStoreError("Speak-up source integrity/audit access differs")
        rows = db.execute("SELECT * FROM versions ORDER BY rowid").fetchall()
        owners = {
            (r["branch"], r["system"], r["owner"]) for r in db.execute("SELECT * FROM systems")
        }
        if len(rows) != 14 or owners != {
            (branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in (
                ("report_intake", "AS-P006"),
                ("separate_triage", "AS-P005"),
                ("protective_handling", "AS-P003"),
                ("case_state", "AS-P005"),
            )
        }:
            raise CompanyStoreError("Speak-up native population/custody differs")
        start = datetime.fromisoformat(_time(START))
        for kind, branch in BRANCHES.items():
            selected = [row for row in rows if row["branch"] == branch]
            if len(selected) != len(PLAN[kind]):
                raise CompanyStoreError("Speak-up branch count differs")
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
                        "source_reference": CASE,
                        "source_sha256": pins,
                        "matrix_sha256": matrix_pins[MATRIX],
                        "control_ids": [CONTROL],
                        "operational_fact_status": "FUTURE_PAYLOAD_FREE_LOCAL_EXERCISE_ONLY",
                    }
                ):
                    raise CompanyStoreError("Speak-up source chronology/content differs")
                imported = datetime.fromisoformat(row["imported_at"])
                if (
                    imported.tzinfo is None
                    or imported.astimezone(UTC) > datetime.now(UTC)
                    or imported.astimezone(UTC).date().isoformat() < AS_OF
                ):
                    raise CompanyStoreError("Speak-up import clock differs")
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
        raise CompanyStoreError("Speak-up receipt/native tuples differ")
    if any(_private(path) != identities[name] for name, path in paths.items()):
        raise CompanyStoreError("Speak-up source changed during read")
    if any(
        Path(str(database) + suffix).exists() or Path(str(database) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Speak-up sidecar appeared during read")
    return {
        "schema": "SH_ETH003_SELECTED_SPEAKUP_VERIFICATION_V1",
        "status": "SELECTED_PAYLOAD_FREE_FUTURE_SOURCE_INDEPENDENT_REVIEW_REQUIRED",
        "source_sha256": {name: identity[-1] for name, identity in identities.items()},
        "native_originals": originals,
        "native_count": 14,
        "branch_counts": {"CLEAN": 6, "MESSY": 8},
        "route_disposition": routes,
        "routes_per_side": {"A": 5, "B": 5},
        "messy_exception_open": EXCEPTION,
        "investigation_and_committee_disposition": "PENDING_NOT_ASSERTED",
        "source_complete": False,
        "real_report_or_retaliation": False,
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
