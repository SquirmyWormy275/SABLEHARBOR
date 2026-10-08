"""Selected future-fictional procurement conflict source, outside any audit."""

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

SCHEMA = "SH_ETH004_SELECTED_CONFLICT_SOURCE_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
OPPORTUNITY = "SIM-ETH004-PROCUREMENT-001"
SIGNAL = "SIM-ETH004-AFFILIATION-001"
EXCEPTION = "LOCAL-ETH004-EXC-001"
START = "2027-05-18T09:00:00+00:00"
BRANCHES = {"CLEAN": "ETH004-CLEAN", "MESSY": "ETH004-MESSY"}
AS_OF = "2026-09-29"
CONTROL = "SH-ETH-004"
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
    "docs/governance/CONFLICT_INTEGRITY_AND_FOUNDER_AUTHORITY.md": (
        "2e565f983a38683b0533f5da45a947158cd257039b45abf1df4c6b758dd184bd"
    ),
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md": (
        "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433"
    ),
    "docs/controls/CCF_CONTROL_OBJECTIVES_v0.1.md": (
        "db7a189139b86fb51d684b6af3e681002b5e0f3f81c38c5bc15a61c20e4a59a3"
    ),
    "docs/structured/enterprise_leadership_2026-09-13.json": (
        "90ec45642cc50219544910e60e4bf6d28b810302c62f29c5936bf965501d673d"
    ),
    "docs/organization/source/chartbook.json": (
        "6ba4f1ed1a14581455a62c3e79a29ca59dbaf1270dfb0db850c0376c15507b49"
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
        ("conflict_intake", "SCOPE", 0),
        ("conflict_intake", "INDICATOR", 5),
        ("conflict_intake", "DISCLOSURE", 8),
        ("conflict_gate", "LOCAL-HOLD", 12),
        ("risk_review", "RISK-TRIAGE", 20),
        ("conflict_gate", "FINAL", 30),
    ),
    "MESSY": (
        ("conflict_intake", "SCOPE", 0),
        ("conflict_intake", "INDICATOR", 5),
        ("conflict_gate", "LOCAL-RECOMMENDATION", 10),
        ("risk_review", "OMISSION-DISCOVERY", 18),
        ("conflict_gate", "WITHDRAWAL", 22),
        ("risk_review", "RISK-TRIAGE", 25),
        ("conflict_gate", "FINAL", 30),
    ),
}
TASK_IDS = {
    "TASK-SH-ETH-004-corporate-CHECK-SOC2:CC3.3",
    "TASK-SH-ETH-004-corporate-IMPLEMENTATION",
    "TASK-SH-ETH-004-corporate-TOD",
    "TASK-SH-ETH-004-corporate-TOE",
}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pins(repository: Path) -> dict:
    pins = {}
    for name, expected in CANON_SHA.items():
        path = repository / name
        if path.is_symlink() or not path.is_file() or _digest(path) != expected:
            raise CompanyStoreError(f"Conflict canon pin differs: {name}")
        pins[name] = expected
    module = "enterprise/audit_suite/company_eth004_conflict_activity.py"
    pins[module] = _digest(repository / module)
    return pins


def _contacts(repository: Path) -> None:
    chart = json.loads((repository / "docs/organization/source/chartbook.json").read_bytes())
    leadership = json.loads(
        (repository / "docs/structured/enterprise_leadership_2026-09-13.json").read_bytes()
    )
    expected = {
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
            or leader[0]["org_role_id"] != role
        ):
            raise CompanyStoreError("Selected proposed actor mapping differs")


def _routes(private_repository: Path) -> tuple[dict, dict]:
    paths = {MATRIX: MATRIX_SHA, MATRIX_REVIEW: MATRIX_REVIEW_SHA}
    identities = {}
    for name, expected in paths.items():
        path = private_repository / name
        identities[name] = _private(path)
        if identities[name][-1] != expected:
            raise CompanyStoreError("Reviewed route matrix pin differs")
    review = json.loads((private_repository / MATRIX_REVIEW).read_bytes())
    if review.get("verdict") != "PASS_READ_ONLY_CANDIDATE_MATRIX_FOR_INTEGRATION":
        raise CompanyStoreError("Route matrix independent review missing")
    matrix = json.loads((private_repository / MATRIX).read_bytes())
    if any(
        _private(private_repository / name) != identity for name, identity in identities.items()
    ):
        raise CompanyStoreError("Reviewed route matrix changed during read")
    result = {}
    for side in "AB":
        controls = [
            control
            for family in matrix["sides"][side]["families"]
            for control in family["controls"]
            if control["control_id"] == CONTROL
        ]
        if len(controls) != 1 or {t["task_id"] for t in controls[0]["tasks"]} != TASK_IDS:
            raise CompanyStoreError("Exact four ETH004 task routes differ")
        rows = controls[0]["tasks"]
        if any(
            t["current_status"] != "NOT_STARTED"
            or t["current_conclusion"] != "NOT_RUN"
            or t["task_credit"] is not False
            for t in rows
        ):
            raise CompanyStoreError("ETH004 route was credited")
        result[side] = [
            {
                "task_id": t["task_id"],
                "procedure_type": t["procedure_type"],
                "authored_test_clause": t["authored_test_clause"],
                "remaining_test_gate": t["remaining_test_gate"],
                "current_status": "NOT_STARTED",
                "current_conclusion": "NOT_RUN",
                "task_credit": False,
            }
            for t in rows
        ]
    return result, paths


def _body(branch: str, record: str) -> dict:
    common = {
        "opportunity_id": OPPORTUNITY,
        "indicator_id": SIGNAL,
        "control_id": CONTROL,
        "scenario_status": "FUTURE_FICTIONAL_SELECTED_PROCUREMENT_EXERCISE_ONLY",
        "actual_affiliation_or_fraud": False,
        "actual_vendor_or_contract": False,
        "award_or_payment": False,
        "qualified_legal_or_independent_disposition": "PENDING_NOT_ASSERTED",
        "accepted_corporate_decision_authority": False,
        "audit_task_credit": False,
    }
    specific = {
        "SCOPE": {
            "actor": "AS-P013",
            "selected_opportunities": [OPPORTUNITY],
            "population_status": "ONE_SELECTED_SYNTHETIC_OPPORTUNITY_NOT_PROCUREMENT_CENSUS",
            "scenario_evaluator_id": "SIM-ETH004-EVALUATOR-001_NOT_ACCEPTED_PERSON",
        },
        "INDICATOR": {
            "actor": "AS-P013",
            "source": "SYNTHETIC_BID_METADATA",
            "signal": "SIMULATED_SUPPLIER_AFFILIATION_INDICATOR_UNVERIFIED",
            "available_for_local_screening": True,
        },
        "DISCLOSURE": {
            "actor": "AS-P013",
            "scenario_evaluator_declaration": "SYNTHETIC_DECLARATION_NOT_ACTUAL_PERSON_DISCLOSURE",
            "indicator_included": True,
        },
        "LOCAL-HOLD": {
            "actor": "AS-P013",
            "decision": "LOCAL_RECOMMENDATION_WITHHELD_PENDING_QUALIFIED_REVIEW",
            "indicator_included": True,
        },
        "LOCAL-RECOMMENDATION": {
            "actor": "AS-P013",
            "decision": "INVALID_LOCAL_DRAFT_RECOMMENDATION_BEFORE_CONFLICT_TRIAGE",
            "indicator_included": False,
            "omitted_indicator_id": SIGNAL,
            "external_effect": False,
        },
        "OMISSION-DISCOVERY": {
            "actor": "AS-P005",
            "finding": "AVAILABLE_INDICATOR_OMITTED_FROM_LOCAL_DRAFT",
            "omitted_indicator_id": SIGNAL,
            "exception_id": EXCEPTION,
        },
        "WITHDRAWAL": {
            "actor": "AS-P013",
            "decision": "LOCAL_DRAFT_WITHDRAWN_AND_OPPORTUNITY_HELD",
            "original_draft_remains_in_HISTORY": True,
            "exception_id": EXCEPTION,
        },
    }
    if record == "RISK-TRIAGE":
        specific[record] = {
            "actor": "AS-P005",
            "decision": "SCOPED_RISK_CANDIDATE_PENDING_QUALIFIED_INDEPENDENT_AND_LEGAL_DISPOSITION",
            "risk_themes": ["RELATED_PARTY", "CONTROL_OVERRIDE", "DISHONEST_REPORTING"],
            "exception_id": EXCEPTION if branch == "MESSY" else None,
            "substantiated_fraud": False,
        }
    if record == "FINAL":
        specific[record] = {
            "actor": "AS-P013",
            "draft_recommendation_active": False,
            "opportunity_held": True,
            "open_exception_ids": [EXCEPTION] if branch == "MESSY" else [],
            "local_review_open": True,
        }
    return {**common, **specific[record]}


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Write one new private native source pair; no audit or existing-source mutation."""
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(path.is_symlink() for path in (destination, *destination.parents))
    ):
        raise CompanyStoreError("New private destination required")
    pins = _pins(repository)
    _contacts(repository)
    routes, route_pins = _routes(private_repository)
    start = datetime.fromisoformat(_time(START))
    if start.date().isoformat() <= AS_OF:
        raise CompanyStoreError("Prospective ETH004 source date required")
    originals = []
    with tempfile.TemporaryDirectory(prefix="eth004-stage-", dir=destination.parent) as staged:
        stage = Path(staged)
        store = CompanyStore(stage)
        for kind, branch in BRANCHES.items():
            for system, owner in (
                ("conflict_intake", "AS-P013"),
                ("conflict_gate", "AS-P013"),
                ("risk_review", "AS-P005"),
            ):
                store.register_system(COMPANY, branch, system, owner)
            previous = None
            for system, record, minute in PLAN[kind]:
                at = (start + timedelta(minutes=minute)).isoformat(timespec="microseconds")
                content = encoded(
                    {
                        **_body(kind, record),
                        "record_id": record,
                        "event_at": at,
                        "previous_source": previous,
                    }
                )
                row = store.append_version(
                    COMPANY,
                    branch,
                    system,
                    record,
                    expected_version=0,
                    command_id="ETH4-" + sha(encoded([branch, system, record])),
                    event_at=at,
                    available_at=at,
                    content=content,
                    provenance={
                        "source_reference": OPPORTUNITY,
                        "source_sha256": pins,
                        "matrix_sha256": route_pins[MATRIX],
                        "control_ids": [CONTROL],
                        "operational_fact_status": "FUTURE_FICTIONAL_LOCAL_EXERCISE_ONLY",
                    },
                )
                original = {
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
                originals.append(original)
                previous = {k: original[k] for k in ("system", "record", "version", "sha256")}
        receipt = {
            "schema": SCHEMA,
            "status": "SEALED_SELECTED_FUTURE_FICTIONAL_COMPANY_NATIVE_PAIR_NO_AUDIT_CREDIT",
            "opportunity_id": OPPORTUNITY,
            "indicator_id": SIGNAL,
            "branch_ids": BRANCHES,
            "source_sha256": pins,
            "route_sha256": route_pins,
            "routes": routes,
            "native_originals": originals,
            "native_count": len(originals),
            "population": "ONE_SELECTED_SYNTHETIC_OPPORTUNITY_NOT_PROCUREMENT_CENSUS",
            "qualified_legal_or_independent_disposition": "PENDING_NOT_ASSERTED",
            "actual_affiliation_or_fraud": False,
            "actual_vendor_or_contract": False,
            "award_or_payment": False,
            "actual_2027_operation": False,
            "source_complete": False,
            "audit_task_credit": False,
            "active_P1_mutated": False,
        }
        source = stage / "SOURCE_RECEIPT.json"
        source.write_bytes(encoded(receipt))
        source.chmod(0o600)
        database = stage / "company.sqlite3"
        manifest = {
            "schema": "SH_ETH004_SELECTED_CONFLICT_MANIFEST_V1",
            "status": "SEALED_PRIVATE_FUTURE_SOURCE_ONLY",
            "source_receipt_sha256": _digest(source),
            "native_db_sha256": _digest(database),
            "native_count": len(originals),
            "audit_task_credit": False,
            "active_P1_mutated": False,
        }
        path = stage / "RUN-MANIFEST.json"
        path.write_bytes(encoded(manifest))
        path.chmod(0o600)
        publish(stage, destination)
    return receipt


def _private(path: Path) -> tuple:
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise CompanyStoreError("Private source path alias forbidden")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077:
        raise CompanyStoreError("Ordinary private source file required")
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, _digest(path)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Reperform one frozen selected source without writing or collecting it."""
    raw_destination = Path(destination).absolute()
    if any(path.is_symlink() for path in (raw_destination, *raw_destination.parents)):
        raise CompanyStoreError("Private source directory alias forbidden")
    destination = raw_destination.resolve(strict=True)
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    if destination.stat().st_mode & 0o077 or destination.is_symlink():
        raise CompanyStoreError("Private source directory required")
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
        raise CompanyStoreError("Frozen conflict source has SQLite sidecar")
    pins = _pins(repository)
    _contacts(repository)
    routes, route_pins = _routes(private_repository)
    receipt = json.loads(paths["SOURCE_RECEIPT.json"].read_bytes())
    manifest = json.loads(paths["RUN-MANIFEST.json"].read_bytes())
    if manifest != {
        "schema": "SH_ETH004_SELECTED_CONFLICT_MANIFEST_V1",
        "status": "SEALED_PRIVATE_FUTURE_SOURCE_ONLY",
        "source_receipt_sha256": identities["SOURCE_RECEIPT.json"][-1],
        "native_db_sha256": identities["company.sqlite3"][-1],
        "native_count": 13,
        "audit_task_credit": False,
        "active_P1_mutated": False,
    }:
        raise CompanyStoreError("Selected conflict manifest differs")
    if (
        receipt["schema"] != SCHEMA
        or receipt["status"]
        != "SEALED_SELECTED_FUTURE_FICTIONAL_COMPANY_NATIVE_PAIR_NO_AUDIT_CREDIT"
        or receipt["opportunity_id"] != OPPORTUNITY
        or receipt["indicator_id"] != SIGNAL
        or receipt["branch_ids"] != BRANCHES
        or receipt["source_sha256"] != pins
        or receipt["route_sha256"] != route_pins
        or receipt["routes"] != routes
        or receipt["native_count"] != 13
        or receipt["population"] != "ONE_SELECTED_SYNTHETIC_OPPORTUNITY_NOT_PROCUREMENT_CENSUS"
        or receipt["qualified_legal_or_independent_disposition"] != "PENDING_NOT_ASSERTED"
        or any(
            receipt[key] is not False
            for key in (
                "actual_affiliation_or_fraud",
                "actual_vendor_or_contract",
                "award_or_payment",
                "actual_2027_operation",
                "source_complete",
                "audit_task_credit",
                "active_P1_mutated",
            )
        )
    ):
        raise CompanyStoreError("Selected conflict source claims unsupported completion")
    expected = []
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok" or any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "collections", "access_events")
        ):
            raise CompanyStoreError("Conflict source integrity or audit access differs")
        rows = db.execute("SELECT * FROM versions ORDER BY rowid").fetchall()
        systems = {
            (r["branch"], r["system"], r["owner"]) for r in db.execute("SELECT * FROM systems")
        }
        if len(rows) != 13 or systems != {
            (branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in (
                ("conflict_intake", "AS-P013"),
                ("conflict_gate", "AS-P013"),
                ("risk_review", "AS-P005"),
            )
        }:
            raise CompanyStoreError("Selected source population/custody differs")
        start = datetime.fromisoformat(_time(START))
        for kind, branch in BRANCHES.items():
            selected = [row for row in rows if row["branch"] == branch]
            if len(selected) != len(PLAN[kind]):
                raise CompanyStoreError("Selected branch count differs")
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
                        "source_reference": OPPORTUNITY,
                        "source_sha256": pins,
                        "matrix_sha256": route_pins[MATRIX],
                        "control_ids": [CONTROL],
                        "operational_fact_status": "FUTURE_FICTIONAL_LOCAL_EXERCISE_ONLY",
                    }
                ):
                    raise CompanyStoreError("Selected conflict native chronology/content differs")
                imported = datetime.fromisoformat(row["imported_at"])
                if (
                    imported.tzinfo is None
                    or imported.astimezone(UTC) > datetime.now(UTC)
                    or imported.astimezone(UTC).date().isoformat() < AS_OF
                ):
                    raise CompanyStoreError("Selected conflict import clock differs")
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
                expected.append(item)
                previous = {key: item[key] for key in ("system", "record", "version", "sha256")}
    if expected != receipt["native_originals"]:
        raise CompanyStoreError("Conflict receipt/native original tuple differs")
    if any(_private(path) != identities[name] for name, path in paths.items()):
        raise CompanyStoreError("Conflict source changed during immutable read")
    if any(
        Path(str(database) + suffix).exists() or Path(str(database) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Conflict source sidecar appeared during read")
    return {
        "schema": "SH_ETH004_SELECTED_CONFLICT_VERIFICATION_V1",
        "status": "SELECTED_FUTURE_LOCAL_SOURCE_ONLY_INDEPENDENT_REVIEW_REQUIRED",
        "source_sha256": {name: value[-1] for name, value in identities.items()},
        "native_originals": expected,
        "native_count": 13,
        "branch_counts": {"CLEAN": 6, "MESSY": 7},
        "route_disposition": routes,
        "route_counts": {"A": 4, "B": 4},
        "messy_exception_open": EXCEPTION,
        "qualified_disposition": "PENDING_NOT_ASSERTED",
        "selected_population_only": True,
        "actual_fraud_or_contract": False,
        "award_or_payment": False,
        "actual_2027_operation": False,
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
