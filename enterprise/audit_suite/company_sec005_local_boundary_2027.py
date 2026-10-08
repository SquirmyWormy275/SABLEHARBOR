"""Fictional 2027 SEC-005 local decision trace, with no network or install effect."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import tempfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_SEC005_LOCAL_BOUNDARY_TRACE_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
BRANCHES = {"CLEAN": "SEC005-LOCAL-CLEAN", "MESSY": "SEC005-LOCAL-MESSY"}
SPEC = "enterprise/audit_suite/sec005_local_boundary_spec_v1.json"
SOURCE_REFERENCE = "enterprise/audit_suite/company_sec005_local_boundary_2027.py"
REVIEW_PATH = (
    "enterprise/generated/audit-suite/documentary-283-route-reconciliation-v3-2026-09-29/"
    "independent-review-v1/REVIEW.json"
)
SOURCE_PINS = {
    SPEC: "b64532f5d7c53ace1ccba8aa1882f87ae8e7737d394687af9d8629168439c02f",
    "docs/canon/THIRD_PARTY_SERVICES_SOURCING_DECISIONS_2026-09-09.md": (
        "53dc3c69be68cd66fe9fdd30048f8229416fd6bd6660272dfeae20f802f986d4"
    ),
    "docs/canon/RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md": (
        "fd309a9bdf596ea96498b7207b60ea3bea70a35d8c418371aa96c06d928bb17b"
    ),
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md": (
        "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496"
    ),
    "docs/internal/development/audit-suite/ORGANIZATION_APPOINTMENT_PROPOSALS_2026-09-13.json": (
        "53681cf60e85d130d04ef79ed437e70da9b3211896e2098f049bc9ff26f54681"
    ),
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md": (
        "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433"
    ),
    "enterprise/ccf/assurance/design_data/control_procedures.json": (
        "258f5c868e16f3dc197594857dc86a4f2b3ef11e3e5a36dd0a80a9fc6d40c679"
    ),
    "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V3_2026-09-29.json": (
        "f7549eca0957a92d442cfabb385ae9eed4509fada804a3dfea5d371cfbbf4d33"
    ),
    "enterprise/audit_suite/company_software_install_activity.py": (
        "98363839915a9d4e5c0c8b3492c5be9a5c32ec7d19f100889aea2694e0c4e130"
    ),
}
REVIEW_SHA256 = "b671d3547670b5de9c7f714d51e44b6d2e65b02502dac752464b9f36d7ca1603"
AUTHORED = {
    "CHECK-SOC2:CC6.6": (
        "Test approved ingress/egress paths, remote administration and boundary defenses "
        "against an unauthorized connection; reconcile rules to actual external interfaces."
    ),
    "CHECK-SOC2:CC6.8": (
        "Inspect installation restrictions, update coverage and detection response on "
        "representative assets; test an unapproved executable and exception path."
    ),
}
SYSTEM_OWNERS = {
    "local_boundary_definition": "AS-P007",
    "local_interface_inventory": "AS-P007",
    "local_boundary_decision": "AS-P007",
    "local_endpoint_decision": "AS-P007",
    "local_reconciliation": "AS-P008",
    "local_exception": "AS-P008",
}
LIMITS = [
    "Future, local, nonpersonal decision exercise; imported_at is the real 2026 import clock.",
    "Symbolic interface IDs are not discovered network interfaces; no packets are sent.",
    "UTF-8 fixture digests are not executables; no install or execution occurs.",
    "AS-P007/AS-P008 are proposed contacts, not accepted corporate appointments or approvals.",
    "No Reno/Boise provider, production boundary, endpoint population, PHI "
    "or real operation is asserted.",
    "Both authored SEC-005 clauses remain unsupported; all five routes per side remain uncredited.",
    "No active P1 grant, collection, task, workpaper, Key, Atlas or roster mutation.",
]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private(path: Path, *, directory: bool) -> Path:
    path = Path(path).absolute()
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise CompanyStoreError("Private alias forbidden")
    info = path.stat()
    if directory:
        if not path.is_dir() or stat.S_IMODE(info.st_mode) != 0o700:
            raise CompanyStoreError("Private 0700 directory required")
    elif (
        not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600
    ):
        raise CompanyStoreError("Private 0600 regular file required")
    return path


def _frozen(paths: dict[str, Path]) -> dict[str, tuple]:
    db = paths["db"]
    if any(
        Path(str(db) + suffix).exists() or Path(str(db) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Frozen native DB has sidecar")
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


def _context(repository: Path, private_repository: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    for name, digest in SOURCE_PINS.items():
        path = repository / name
        if path.is_symlink() or not path.is_file() or _digest(path) != digest:
            raise CompanyStoreError("Pinned SEC-005 source bytes differ")
    review = private_repository / REVIEW_PATH
    _private(review, directory=False)
    if _digest(review) != REVIEW_SHA256:
        raise CompanyStoreError("Reviewed SEC-005 route authority differs")
    review_data = json.loads(review.read_text())
    ledger_path = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V3_2026-09-29.json"
    if (
        review_data.get("verdict") != "PASS_READ_ONLY_PARTIAL_ROUTE_RECONCILIATION"
        or review_data.get("tracked_sha256", {}).get("ledger_json") != SOURCE_PINS[ledger_path]
    ):
        raise CompanyStoreError("SEC-005 route review is not accepted")
    ledger = json.loads((repository / ledger_path).read_text())
    routes = {}
    expected_ids = {
        f"TASK-SH-SEC-005-corporate-{suffix}"
        for suffix in (*AUTHORED, "IMPLEMENTATION", "TOD", "TOE")
    }
    for side in "AB":
        rows = {
            row["task_id"]: row
            for row in ledger["rows"]
            if row["side"] == side and row["control_id"] == "SH-SEC-005"
        }
        if set(rows) != expected_ids or len(rows) != 5:
            raise CompanyStoreError("Exact five SEC-005 routes differ")
        for task_id, row in rows.items():
            suffix = task_id.removeprefix("TASK-SH-SEC-005-corporate-")
            authored = suffix in AUTHORED
            if (
                row["authored_test_clause"] != (AUTHORED[suffix] if authored else None)
                or row["classification"]
                != ("UNSUPPORTED_EXACT_CLAUSE" if authored else "DESIGN_CONTEXT_ONLY")
                or row["procedure_type"] != ("ADDITIONAL_DUTY" if authored else suffix)
                or row["current_status"] != "NOT_STARTED"
                or row["current_conclusion"] != "NOT_RUN"
                or row["audit_task_credit"] is not False
                or row["actual_operation_eligibility_as_of_packet"] is not False
            ):
                raise CompanyStoreError("SEC-005 route clause or status differs")
        routes[side] = {"task_ids": sorted(rows), "authored_unsupported": 2, "inferred": 3}
    if routes["A"] != routes["B"]:
        raise CompanyStoreError("SEC-005 paired route authority differs")
    spec = json.loads((repository / SPEC).read_text())
    appointment_path = (
        "docs/internal/development/audit-suite/ORGANIZATION_APPOINTMENT_PROPOSALS_2026-09-13.json"
    )
    appointments = json.loads((repository / appointment_path).read_text())
    people = {person["person_id"] for person in appointments["people"]}
    if (
        spec["schema"] != "SH_FICTIONAL_2027_SEC005_LOCAL_BOUNDARY_SPEC_V1"
        or spec["scenario_date"] != "2027-10-12"
        or spec["qualification"] != "LOCAL_NONPERSONAL_DECISION_EXERCISE_NOT_DEPLOYMENT"
        or spec["declared_symbolic_interface_ids"]
        != [
            "SYMBOLIC-LOCAL-ALLOW",
            "SYMBOLIC-FORBIDDEN-EGRESS",
            "SYMBOLIC-REMOTE-ADMIN",
        ]
        or spec["locally_permitted_interface_ids"] != ["SYMBOLIC-LOCAL-ALLOW"]
        or spec["selected_request_interface_id"] != "SYMBOLIC-FORBIDDEN-EGRESS"
        or spec["remote_admin_interface_id"] != "SYMBOLIC-REMOTE-ADMIN"
        or spec["operator_contact_id"] != "AS-P007"
        or spec["distinct_review_contact_id"] != "AS-P008"
        or not {"AS-P007", "AS-P008"} <= people
        or appointments["repository_acceptance_status"] != "PROPOSED_NOT_ACCEPTED_CANON"
        or any(
            spec[field]
            for field in (
                "contacts_are_accepted_corporate_appointments",
                "actual_network_packets_sent",
                "actual_executables_created_or_run",
                "actual_phi_present",
                "actual_deployment",
                "audit_task_credit",
            )
        )
    ):
        raise CompanyStoreError("SEC-005 local scope or proposed-contact limit differs")
    return {"spec": spec, "routes": routes}


def _rows(context: dict, scenario: str) -> list[dict]:
    if scenario not in BRANCHES:
        raise CompanyStoreError("Unknown SEC-005 scenario")
    spec = context["spec"]
    messy = scenario == "MESSY"
    approved = sha(spec["approved_fixture_utf8"].encode())
    candidate = sha(spec["unapproved_fixture_utf8"].encode())
    if approved == candidate:
        raise CompanyStoreError("Selected inert fixture digests collide")
    intended = spec["locally_permitted_interface_ids"]
    staged = [*intended, spec["selected_request_interface_id"]] if messy else intended
    common = {
        "qualification": spec["qualification"],
        "scope": spec["scope"],
        "scenario": scenario,
        "boundary_id": spec["boundary_id"],
        "endpoint_id": spec["endpoint_id"],
        "actual_network_packets_sent": 0,
        "actual_executables_created_or_run": 0,
        "actual_phi_present": False,
        "actual_deployment": False,
        "audit_task_credit": False,
        "corporate_approval": False,
    }
    events = [
        (
            "local_boundary_definition",
            "RULE-01",
            "09:00",
            {
                "action": "LOCAL_SYMBOLIC_RULE_DECLARED",
                "declared_symbolic_interface_ids": spec["declared_symbolic_interface_ids"],
                "intended_permitted_interface_ids": intended,
                "staged_rule_permitted_interface_ids": staged,
                "remote_admin_interface_id": spec["remote_admin_interface_id"],
                "rule_stale_against_intended": messy,
                "actor_id": spec["operator_contact_id"],
            },
        ),
        (
            "local_interface_inventory",
            "INVENTORY-01",
            "09:03",
            {
                "action": "LOCAL_DECLARED_SYMBOLIC_INTERFACE_AND_ENDPOINT_INVENTORY",
                "symbolic_interface_ids": spec["declared_symbolic_interface_ids"],
                "endpoint_id": spec["endpoint_id"],
                "approved_inert_text_sha256": approved,
                "unapproved_inert_text_sha256": candidate,
                "population_basis": "ONE_DECLARED_LOCAL_FIXTURE_NOT_DISCOVERED_ASSET_CENSUS",
                "actor_id": spec["operator_contact_id"],
            },
        ),
        (
            "local_boundary_decision",
            "EGRESS-ATTEMPT-01",
            "09:08",
            {
                "action": "SYMBOLIC_UNAUTHORIZED_EGRESS_REQUEST",
                "requested_interface_id": spec["selected_request_interface_id"],
                "staged_rule_match": messy,
                "intended_baseline_match": False,
                "decision": (
                    "STAGED_RULE_WOULD_ALLOW_GUARD_QUARANTINED"
                    if messy
                    else "DENIED_BY_LOCAL_SYMBOLIC_RULE"
                ),
                "effect": "NO_NETWORK_IO_OR_EXTERNAL_INTERFACE_CONTACT",
                "actor_id": spec["operator_contact_id"],
            },
        ),
        (
            "local_endpoint_decision",
            "INERT-CANDIDATE-01",
            "09:12",
            {
                "action": "UNAPPROVED_INERT_UTF8_DIGEST_REQUEST",
                "fixture_sha256": candidate,
                "approved_fixture_sha256": approved,
                "decision": "DENIED_UNAPPROVED_LOCAL_DIGEST",
                "effect": "NO_EXECUTABLE_FILE_OS_INSTALL_OR_RUN",
                "actor_id": spec["operator_contact_id"],
            },
        ),
    ]
    if messy:
        events += [
            (
                "local_reconciliation",
                "DRIFT-FOUND-01",
                "09:20",
                {
                    "action": "LATE_LOCAL_RULE_TO_INTENDED_BASELINE_RECONCILIATION",
                    "stale_candidate_found": True,
                    "original_attempt_record_id": "EGRESS-ATTEMPT-01",
                    "decision": "CORRECTION_REQUIRED_WITH_HISTORICAL_EXCEPTION",
                    "reviewer_id": spec["distinct_review_contact_id"],
                },
            ),
            (
                "local_boundary_definition",
                "RULE-CORRECTION-01",
                "09:25",
                {
                    "action": "LOCAL_SYMBOLIC_RULE_CORRECTED",
                    "corrected_permitted_interface_ids": intended,
                    "original_stale_rule_retained": True,
                    "actor_id": spec["operator_contact_id"],
                },
            ),
        ]
    events.append(
        (
            "local_reconciliation",
            "REVIEW-01",
            "10:00",
            {
                "action": "DISTINCT_LOCAL_CONTACT_REVIEW",
                "reviewer_id": spec["distinct_review_contact_id"],
                "operator_id": spec["operator_contact_id"],
                "selected_symbolic_interface_count": 3,
                "selected_endpoint_count": 1,
                "rule_drift_found": messy,
                "open_historical_exception_id": "EXC-SIM-SEC005-LATE-RULE-RECONCILIATION"
                if messy
                else None,
                "exception_closed": False if messy else None,
                "actual_external_interface_reconciliation": False,
                "actual_executable_test": False,
            },
        )
    )
    if messy:
        events.append(
            (
                "local_exception",
                "EXC-SIM-SEC005-LATE-RULE-RECONCILIATION",
                "10:03",
                {
                    "action": "HISTORICAL_LOCAL_RULE_DRIFT_EXCEPTION_RETAINED",
                    "original_attempt_record_id": "EGRESS-ATTEMPT-01",
                    "correction_record_id": "RULE-CORRECTION-01",
                    "status": "OPEN_REVIEW_AND_PREVENTION_NOT_ACCEPTED",
                    "owner_contact_id": spec["operator_contact_id"],
                    "review_contact_id": spec["distinct_review_contact_id"],
                    "network_effect": "NONE",
                },
            )
        )
    rows = []
    previous = None
    for system, record, hhmm, body in events:
        event = _time(f"{spec['scenario_date']}T{hhmm}:00+00:00")
        available = _time((datetime.fromisoformat(event) + timedelta(minutes=1)).isoformat())
        if previous and previous["available_at"] > event:
            raise CompanyStoreError("SEC-005 event predates predecessor availability")
        value = {
            **common,
            "system": system,
            "record": record,
            "event_at": event,
            "available_at": available,
            "source_previous": previous,
            **body,
        }
        raw = encoded(value)
        row = {
            "system": system,
            "record": record,
            "version": 1,
            "event_at": event,
            "available_at": available,
            "content": raw,
            "sha256": sha(raw),
        }
        rows.append(row)
        previous = {
            key: row[key]
            for key in ("system", "record", "version", "sha256", "event_at", "available_at")
        }
    return rows


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def _provenance(scenario: str) -> dict:
    return {
        "source_reference": SOURCE_REFERENCE,
        "scenario": scenario,
        "source_pins": SOURCE_PINS,
        "route_review_path": REVIEW_PATH,
        "route_review_sha256": REVIEW_SHA256,
        "qualification": "LOCAL_FUTURE_NONPERSONAL_NO_AUDIT_CREDIT",
    }


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    destination = Path(destination).absolute()
    _private(destination.parent, directory=True)
    if destination.exists() or destination.is_symlink() or destination != destination.resolve():
        raise CompanyStoreError("New private SEC-005 destination required")
    context = _context(repository, private_repository)
    with tempfile.TemporaryDirectory(prefix=".sec005-stage-", dir=destination.parent) as temp:
        stage = Path(temp)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in BRANCHES.items():
            for system, owner in SYSTEM_OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            records[scenario] = []
            for row in _rows(context, scenario):
                ref = store.append_version(
                    COMPANY,
                    branch,
                    row["system"],
                    row["record"],
                    expected_version=0,
                    command_id=f"S5-{branch}-{row['record']}",
                    event_at=row["event_at"],
                    available_at=row["available_at"],
                    content=row["content"],
                    provenance=_provenance(scenario),
                )
                if ref["sha256"] != row["sha256"]:
                    raise CompanyStoreError("SEC-005 authored bytes differ")
                records[scenario].append(ref)
        receipt = {
            "schema": SCHEMA,
            "company": COMPANY,
            "branches": BRANCHES,
            "records": records,
            "source_pins": SOURCE_PINS,
            "route_review_path": REVIEW_PATH,
            "route_review_sha256": REVIEW_SHA256,
            "selected_route_authority": context["routes"],
            "native_version_counts": {side: len(refs) for side, refs in records.items()},
            "open_exception_counts": {"CLEAN": 0, "MESSY": 1},
            "network_packets_sent": 0,
            "executables_created_or_run": 0,
            "actual_operation_eligibility_as_of_2026_09_29": False,
            "authored_sec005_clause_support": False,
            "audit_task_credit": False,
            "limits": LIMITS,
        }
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _digest(stage / "RECEIPT.json"),
            "db_sha256": _digest(stage / "company.sqlite3"),
            "module_sha256": _digest(Path(__file__)),
            "native_version_count": sum(len(refs) for refs in records.values()),
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return manifest


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    root = _private(destination, directory=True)
    paths = {
        "manifest": root / "MANIFEST.json",
        "receipt": root / "RECEIPT.json",
        "db": root / "company.sqlite3",
    }
    before = _frozen(paths)
    manifest = json.loads(paths["manifest"].read_text())
    receipt = json.loads(paths["receipt"].read_text())
    context = _context(repository, private_repository)
    expected_counts = {side: len(_rows(context, side)) for side in BRANCHES}
    if (
        manifest.get("schema") != SCHEMA + "_MANIFEST"
        or manifest.get("receipt_sha256") != before["receipt"][-1]
        or manifest.get("db_sha256") != before["db"][-1]
        or manifest.get("module_sha256") != _digest(Path(__file__))
        or manifest.get("native_version_count") != sum(expected_counts.values())
        or manifest.get("audit_task_credit") is not False
        or receipt.get("schema") != SCHEMA
        or receipt.get("company") != COMPANY
        or receipt.get("branches") != BRANCHES
        or receipt.get("source_pins") != SOURCE_PINS
        or receipt.get("route_review_path") != REVIEW_PATH
        or receipt.get("route_review_sha256") != REVIEW_SHA256
        or receipt.get("selected_route_authority") != context["routes"]
        or receipt.get("native_version_counts") != expected_counts
        or receipt.get("open_exception_counts") != {"CLEAN": 0, "MESSY": 1}
        or receipt.get("network_packets_sent") != 0
        or receipt.get("executables_created_or_run") != 0
        or receipt.get("actual_operation_eligibility_as_of_2026_09_29") is not False
        or receipt.get("authored_sec005_clause_support") is not False
        or receipt.get("audit_task_credit") is not False
        or receipt.get("limits") != LIMITS
        or set(receipt.get("records", {})) != set(BRANCHES)
    ):
        raise CompanyStoreError("SEC-005 manifest/receipt scope differs")
    with closing(sqlite3.connect(paths["db"].as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("SEC-005 native DB integrity differs")
        if db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != sum(
            expected_counts.values()
        ) or any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "collections", "access_events")
        ):
            raise CompanyStoreError("SEC-005 source/audit-access count differs")
        expected_systems = {
            (COMPANY, branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in SYSTEM_OWNERS.items()
        }
        if {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        } != expected_systems:
            raise CompanyStoreError("SEC-005 local system owners differ")
        for scenario, branch in BRANCHES.items():
            expected = _rows(context, scenario)
            refs = receipt["records"][scenario]
            if len(expected) != len(refs):
                raise CompanyStoreError("SEC-005 branch row count differs")
            for row, ref in zip(expected, refs, strict=True):
                native = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=1",
                    (COMPANY, branch, row["system"], row["record"]),
                ).fetchone()
                if native is None or native["content"] != row["content"]:
                    raise CompanyStoreError("SEC-005 native content differs")
                if (
                    native["sha256"] != row["sha256"]
                    or native["event_at"] != row["event_at"]
                    or native["available_at"] != row["available_at"]
                    or json.loads(native["provenance"]) != _provenance(scenario)
                    or native["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or native["imported_at"] >= row["event_at"]
                    or native["command_id"] != f"S5-{branch}-{row['record']}"
                ):
                    raise CompanyStoreError("SEC-005 native provenance or clocks differ")
                actual_ref = CompanyStore._metadata(native)
                if ref != actual_ref:
                    raise CompanyStoreError("SEC-005 receipt/native tuple differs")
    if _frozen(paths) != before:
        raise CompanyStoreError("SEC-005 frozen source changed during read")
    return {"status": "VERIFIED_LOCAL_NO_AUDIT_CREDIT", "native_version_counts": expected_counts}
