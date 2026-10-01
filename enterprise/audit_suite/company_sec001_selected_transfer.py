"""Selected future fictional SEC001 transfer custody source, without audit credit."""

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
from .documentary_283_route_reconciliation_v6 import _p1_inventory
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_SEC001_SELECTED_SYNTHETIC_TRANSFER_SOURCE_V1"
MANIFEST_SCHEMA = "SH_SEC001_SELECTED_SYNTHETIC_TRANSFER_MANIFEST_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
CONTROL = "SH-SEC-001"
TASK = "TASK-SH-SEC-001-corporate-CHECK-SOC2:CC6.7"
CLAUSE = (
    "Trace a transfer to purpose, recipient authorization, channel/endpoint protection "
    "and handling after receipt; transport encryption alone does not authorize the transfer."
)
TRANSFER = "SIM-SEC001-XFER-2027-001"
EXCEPTION = "SIM-SEC001-FALSE-CLOSE-EXC-001"
PAYLOAD = b"SEC001 fictional non-PHI fixture v1; no live transfer\n"
PAYLOAD_SHA = sha(PAYLOAD)
START = "2027-09-15T09:00:00+00:00"
AS_OF = "2026-09-30"
BRANCHES = {"CLEAN": "SEC001-XFER-CLEAN", "MESSY": "SEC001-XFER-MESSY"}
SYSTEM_OWNERS = {
    "transfer_authority": "AS-P014",
    "security_path": "AS-P008",
    "transfer_operations": "AS-P007",
    "receipt_handling": "AS-P014",
    "exception_register": "AS-P008",
}
ROUTE_LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V10_2026-09-30.json"
ROUTE_REVIEW = (
    "enterprise/generated/audit-suite/documentary-283-route-reconciliation-v10-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
ROUTE_SHA = "d7904fe36b8307e31071a24086d71b2500910e88e5243256a1d5bf4b4f050324"
REVIEW_SHA = "b702667f9f480774c07d160c31939250c7ad76a65661a1f7c8c41f23e068b674"
P1_FREEZE = {
    "file_count": 538,
    "inventory_sha256": "f266ef682b502b3b093170f8a7b64fcf5cbab722d5c8ddf6715a63c0e535360f",
}
CANON_SHA = {
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md": (
        "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433"
    ),
    "docs/controls/CCF_CONTROL_OBJECTIVES_v0.1.md": (
        "db7a189139b86fb51d684b6af3e681002b5e0f3f81c38c5bc15a61c20e4a59a3"
    ),
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md": (
        "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751"
    ),
    "docs/organization/source/chartbook.json": (
        "6ba4f1ed1a14581455a62c3e79a29ca59dbaf1270dfb0db850c0376c15507b49"
    ),
    "docs/structured/enterprise_leadership_2026-09-13.json": (
        "90ec45642cc50219544910e60e4bf6d28b810302c62f29c5936bf965501d673d"
    ),
    "enterprise/ccf/assurance/design_data/control_procedures.json": (
        "258f5c868e16f3dc197594857dc86a4f2b3ef11e3e5a36dd0a80a9fc6d40c679"
    ),
    "enterprise/ccf/assurance/design_data/supplements.json": (
        "e89da921f880496f299b7569673daa1ae271068436f574e7b28bb842410f284b"
    ),
    "enterprise/audit_suite/SEC001_SELECTED_TRANSFER_2027_PROPOSAL.md": (
        "feba420a15b51cb4891e86eb1d79f71284e04436e925980278a947f9319777c4"
    ),
}
PEOPLE = {
    "AS-P007": ("Elliot Tran", "Head of Enterprise Technology Services", "ROLE-33"),
    "AS-P008": ("Dana West", "Chief Information Security Officer", "ROLE-34"),
    "AS-P014": ("Omar Vale", "Data Governance and Records Lead", "AS-ROLE-DATA"),
}
PLAN = {
    "CLEAN": (
        ("transfer_authority", "DATASET", 0, 0),
        ("transfer_authority", "PURPOSE", 10, 0),
        ("transfer_authority", "RECIPIENT", 20, 0),
        ("security_path", "CHANNEL", 30, 0),
        ("security_path", "ENDPOINT", 40, 0),
        ("transfer_operations", "REQUEST", 50, 0),
        ("transfer_operations", "OBSERVATION", 60, 0),
        ("receipt_handling", "RECEIPT", 70, 0),
        ("receipt_handling", "HANDLING", 80, 0),
        ("exception_register", "FINAL", 90, 0),
    ),
    "MESSY": (
        ("transfer_authority", "DATASET", 0, 0),
        ("transfer_authority", "PURPOSE", 10, 0),
        ("transfer_authority", "RECIPIENT", 20, 0),
        ("security_path", "CHANNEL", 30, 0),
        ("security_path", "ENDPOINT", 40, 0),
        ("transfer_operations", "REQUEST", 50, 0),
        ("transfer_operations", "WRONG-ENDPOINT-ATTEMPT", 60, 0),
        ("security_path", "BLOCK", 61, 0),
        ("security_path", "ENDPOINT-CORRECTION", 70, 0),
        ("transfer_operations", "OBSERVATION", 80, 0),
        ("exception_register", "FALSE-CLOSE", 90, 2),
        ("exception_register", "GAP-DISCOVERY", 100, 1),
        ("receipt_handling", "RECEIPT", 110, 0),
        ("receipt_handling", "HANDLING", 120, 0),
        ("exception_register", "CORRECTION", 130, 0),
        ("exception_register", "FINAL", 140, 0),
    ),
}
ACTORS = {
    "DATASET": "AS-P014",
    "PURPOSE": "AS-P014",
    "RECIPIENT": "AS-P014",
    "CHANNEL": "AS-P008",
    "ENDPOINT": "AS-P008",
    "REQUEST": "AS-P007",
    "WRONG-ENDPOINT-ATTEMPT": "AS-P007",
    "BLOCK": "AS-P008",
    "ENDPOINT-CORRECTION": "AS-P008",
    "OBSERVATION": "AS-P007",
    "FALSE-CLOSE": "AS-P007",
    "GAP-DISCOVERY": "AS-P014",
    "RECEIPT": "AS-P014",
    "HANDLING": "AS-P014",
    "CORRECTION": "AS-P008",
    "FINAL": "AS-P008",
}
LINKS = {
    "DATASET": (),
    "PURPOSE": ("DATASET",),
    "RECIPIENT": ("PURPOSE",),
    "CHANNEL": ("PURPOSE", "RECIPIENT"),
    "ENDPOINT": ("RECIPIENT", "CHANNEL"),
    "REQUEST": ("PURPOSE", "RECIPIENT", "CHANNEL", "ENDPOINT"),
    "WRONG-ENDPOINT-ATTEMPT": ("REQUEST", "ENDPOINT"),
    "BLOCK": ("WRONG-ENDPOINT-ATTEMPT",),
    "ENDPOINT-CORRECTION": ("BLOCK", "RECIPIENT"),
    "OBSERVATION": ("REQUEST", "ENDPOINT"),
    "FALSE-CLOSE": ("OBSERVATION",),
    "GAP-DISCOVERY": ("FALSE-CLOSE",),
    "RECEIPT": ("OBSERVATION",),
    "HANDLING": ("RECEIPT", "PURPOSE"),
    "CORRECTION": ("FALSE-CLOSE", "GAP-DISCOVERY", "HANDLING"),
    "FINAL": ("HANDLING",),
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


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private_file(path: Path) -> tuple:
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise CompanyStoreError("Private transfer path alias forbidden")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600:
        raise CompanyStoreError("Ordinary 0600 private transfer file required")
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, _digest(path)


def _pins(repository: Path) -> dict:
    pins = {}
    for name, expected in CANON_SHA.items():
        path = repository / name
        if path.is_symlink() or not path.is_file() or _digest(path) != expected:
            raise CompanyStoreError(f"Selected transfer canon pin differs: {name}")
        pins[name] = expected
    module = "enterprise/audit_suite/company_sec001_selected_transfer.py"
    pins[module] = _digest(repository / module)
    return pins


def _canon(repository: Path) -> None:
    chart = json.loads((repository / "docs/organization/source/chartbook.json").read_bytes())
    leaders = json.loads(
        (repository / "docs/structured/enterprise_leadership_2026-09-13.json").read_bytes()
    )
    for person, (name, title, role) in PEOPLE.items():
        cards = [
            x for x in chart["nodes"] if x.get("person_id") == person and x.get("type") == "person"
        ]
        leadership = [x for x in leaders["people"] if x["person_id"] == person]
        if (
            len(cards) != 1
            or len(leadership) != 1
            or (cards[0]["name"], cards[0]["title"], cards[0]["role_id"]) != (name, title, role)
            or cards[0]["title_state"] != "DELEGATED_FICTIONAL_APPOINTMENT_PENDING_ACCEPTANCE"
            or (leadership[0]["name"], leadership[0]["title"], leadership[0]["org_role_id"])
            != (name, title, role)
        ):
            raise CompanyStoreError("Selected transfer actor authority mapping differs")
    procedures = json.loads(
        (repository / "enterprise/ccf/assurance/design_data/control_procedures.json").read_bytes()
    )
    selected = [row for row in procedures if row.get("control_id") == CONTROL]
    if (
        len(selected) != 1
        or selected[0].get("proposed_system_of_record") != "Security architecture repository"
        or selected[0].get("reviewer_role_description") != "Security architecture authority"
    ):
        raise CompanyStoreError("Selected SEC001 procedure authority differs")
    supplements = json.loads(
        (repository / "enterprise/ccf/assurance/design_data/supplements.json").read_bytes()
    )
    crypto = [row for row in supplements if row.get("id") == "CRYPTO-TRANSFER"]
    if (
        len(crypto) != 1
        or crypto[0].get("status") != "PROPOSED_DESIGN_SUPPLEMENT"
        or CONTROL not in crypto[0].get("native_control_ids", [])
        or "SOC2:CC6.7" not in crypto[0].get("requirement_ids", [])
        or crypto[0].get("approval")
        != "No deployed settings, budget or contract is approved by this proposal."
    ):
        raise CompanyStoreError("Proposed transfer supplement boundary differs")


def _route(repository: Path, private: Path) -> tuple[dict, dict]:
    ledger_path = repository / ROUTE_LEDGER
    review_path = private / ROUTE_REVIEW
    before = _private_file(review_path)
    if _digest(ledger_path) != ROUTE_SHA or before[-1] != REVIEW_SHA:
        raise CompanyStoreError("Reviewed V10 transfer route bytes differ")
    ledger = json.loads(ledger_path.read_bytes())
    review = json.loads(review_path.read_bytes())
    if (
        review.get("verdict")
        != "PASS_READ_ONLY_SELECTED_ETH001_ROUTE_RECONCILIATION_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or review.get("main_tracked_sha256", {}).get(ROUTE_LEDGER) != ROUTE_SHA
        or review.get("p1_freeze") != P1_FREEZE
        or review.get("audit_task_credit") is not False
        or ledger.get("audit_task_credit") is not False
        or ledger.get("active_pair_mutated") is not False
    ):
        raise CompanyStoreError("Reviewed V10 transfer route claim differs")
    selected = {}
    for side in "AB":
        rows = [row for row in ledger["rows"] if row["side"] == side and row["task_id"] == TASK]
        if len(rows) != 1:
            raise CompanyStoreError("Selected SEC001 route missing")
        row = rows[0]
        if (
            row["control_id"] != CONTROL
            or row["classification"] != "UNSUPPORTED_EXACT_CLAUSE"
            or row["requirement_ids"] != ["SOC2:CC6.7"]
            or row["authored_test_clause"] != CLAUSE
            or row["remaining_test_gate"] != CLAUSE
            or row["targeted_integrated_source_ids"]
            or row["candidate_or_design_source_ids"]
            or row["current_status"] != "NOT_STARTED"
            or row["current_conclusion"] != "NOT_RUN"
            or row["audit_task_credit"] is not False
        ):
            raise CompanyStoreError("Selected SEC001 authored clause boundary differs")
        selected[side] = {
            "task_id": TASK,
            "authored_test_clause": row["authored_test_clause"],
            "screen_row_sha256": row["screen_row_sha256"],
            "classification": row["classification"],
            "remaining_test_gate": row["remaining_test_gate"],
            "current_status": row["current_status"],
            "current_conclusion": row["current_conclusion"],
            "source_limit": row["source_limit"],
            "audit_task_credit": False,
        }
    if _private_file(review_path) != before or _digest(ledger_path) != ROUTE_SHA:
        raise CompanyStoreError("Reviewed V10 transfer route changed during read")
    return selected, {ROUTE_LEDGER: ROUTE_SHA, ROUTE_REVIEW: REVIEW_SHA}


def _ref(row: dict) -> dict:
    return {key: row[key] for key in ORIGINAL_FIELDS}


def _detail(scenario: str, record: str) -> dict:
    common = {
        "scope": "ONE_SELECTED_FUTURE_FICTIONAL_SYNTHETIC_NON_PHI_TRANSFER",
        "payload_sha256": PAYLOAD_SHA,
        "real_network_bytes": 0,
        "actual_customer_or_phi_data": False,
        "deployed_channel_or_endpoint": False,
        "approved_enterprise_transfer_standard": False,
    }
    details = {
        "DATASET": {"data_class": "SYNTHETIC_NON_PHI", "selected_payload_count": 1},
        "PURPOSE": {
            "purpose": "LOCAL_SECURITY_TRANSFER_TRACE_FIXTURE",
            "local_decision": "TRAINING_ONLY_PURPOSE_ACCEPTED",
        },
        "RECIPIENT": {
            "recipient_id": "SIM-SEC001-RECEIVER",
            "approved_fixture_endpoint": "synthetic:sec001:receipt-vault",
            "local_decision": "TRAINING_ONLY_RECIPIENT_ACCEPTED",
        },
        "CHANNEL": {
            "channel_fixture": "SIMULATED_MUTUAL_TLS_WITH_TEST_CERTIFICATE",
            "deployed": False,
        },
        "ENDPOINT": {
            "endpoint_fixture": "synthetic:sec001:receipt-vault",
            "fixture_cert_bound": True,
        },
        "REQUEST": {
            "operator_request": "SELECTED_SYNTHETIC_TRANSFER",
            "self_approval_allowed": False,
        },
        "WRONG-ENDPOINT-ATTEMPT": {
            "attempted_endpoint": "synthetic:sec001:unlisted-endpoint",
            "authorization_result": "DENIED_BEFORE_SEND",
            "payload_sent": False,
        },
        "BLOCK": {"detection": "UNLISTED_ENDPOINT_BLOCKED", "quarantined": True},
        "ENDPOINT-CORRECTION": {
            "corrected_endpoint": "synthetic:sec001:receipt-vault",
            "blocked_original_retained": True,
        },
        "OBSERVATION": {
            "rehearsal_result": "SELECTED_FIXTURE_TRANSFER_ACCEPTED",
            "recipient_fixture": "SIM-SEC001-RECEIVER",
            "actual_network_transfer": False,
        },
        "FALSE-CLOSE": {
            "claimed_complete_without_receipt": True,
            "operator_lacked_review_authority": True,
            "exception_id": EXCEPTION,
        },
        "GAP-DISCOVERY": {
            "missing_receipt_handling_found": True,
            "false_close_retained": True,
            "exception_id": EXCEPTION,
        },
        "RECEIPT": {
            "fictional_receiver_ack": True,
            "received_payload_sha256": PAYLOAD_SHA,
            "actual_receipt": False,
        },
        "HANDLING": {
            "fictional_restricted_staging": True,
            "hash_reconciled": True,
            "retention_label": "SYNTHETIC_FIXTURE_ONLY",
            "actual_storage_or_deletion": False,
        },
        "CORRECTION": {
            "false_close_corrected": True,
            "false_close_erased": False,
            "exception_open": True,
            "exception_id": EXCEPTION,
        },
        "FINAL": {
            "selected_fixture_reconciled": True,
            "exception_open": scenario == "MESSY",
            "open_exception_ids": [EXCEPTION] if scenario == "MESSY" else [],
            "authored_clause_satisfied": False,
        },
    }
    return {**common, **details[record]}


def _body(scenario: str, record: str, refs: dict, previous: dict | None) -> dict:
    links = list(LINKS[record])
    if record == "OBSERVATION" and scenario == "MESSY":
        links.append("ENDPOINT-CORRECTION")
    if record == "FINAL" and scenario == "MESSY":
        links.append("CORRECTION")
    return {
        "schema": SCHEMA,
        "transfer_id": TRANSFER,
        "control_id": CONTROL,
        "selected_task_id": TASK,
        "scenario": scenario,
        "record_id": record,
        "actor_id": ACTORS[record],
        "actor_authority": "CANON_LISTED_FICTIONAL_APPOINTMENT_PENDING_ACCEPTANCE",
        "qualification": "AUTHORED_FUTURE_SELECTED_EXERCISE_NOT_REAL_OPERATION",
        "record_links": {name: refs[name] for name in links},
        "previous_original": previous,
        "detail": _detail(scenario, record),
        "source_complete": False,
        "audit_task_credit": False,
    }


def _provenance(pins: dict, route_pins: dict) -> dict:
    return {
        "source_reference": TRANSFER,
        "source_sha256": pins,
        "route_sha256": route_pins,
        "control_ids": [CONTROL],
        "operational_fact_status": "FUTURE_FICTIONAL_SELECTED_EXERCISE_ONLY",
        "actor_authority": "CANON_LISTED_FICTIONAL_APPOINTMENTS_PENDING_ACCEPTANCE",
        "independent_approval": False,
        "actual_network_or_phi": False,
    }


def _receipt(originals: list[dict], pins: dict, route_pins: dict, routes: dict) -> dict:
    return {
        "schema": SCHEMA,
        "status": "SEALED_SELECTED_FUTURE_FICTIONAL_COMPANY_SOURCE_NO_AUDIT_CREDIT",
        "transfer_id": TRANSFER,
        "control_id": CONTROL,
        "task_id": TASK,
        "selected_authored_clause": CLAUSE,
        "branch_ids": BRANCHES,
        "branch_counts": {scenario: len(plan) for scenario, plan in PLAN.items()},
        "source_sha256": pins,
        "route_sha256": route_pins,
        "route_disposition": routes,
        "native_originals": originals,
        "native_count": len(originals),
        "selected_payload_count": 1,
        "payload_sha256": PAYLOAD_SHA,
        "actor_authority": "CANON_LISTED_FICTIONAL_APPOINTMENTS_PENDING_ACCEPTANCE",
        "independent_approval": False,
        "clean_selected_reconciliation": "FICTIONAL_FIXTURE_COMPLETE_NO_LOCAL_EXCEPTION",
        "messy_blocked_wrong_endpoint": True,
        "messy_false_close_corrected": True,
        "messy_historical_exception_open": True,
        "actual_network_transmission": False,
        "actual_customer_or_phi_data": False,
        "actual_deployed_endpoint_or_channel": False,
        "enterprise_transfer_standard_approved": False,
        "population_complete": False,
        "source_complete": False,
        "audit_task_credit": False,
        "active_P1_mutated": False,
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
    """Append selected Clean/Messy company originals, with no audit journal write."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or destination.is_symlink()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(path.is_symlink() for path in (destination, *destination.parents))
    ):
        raise CompanyStoreError("New private selected transfer destination required")
    if _p1_inventory(private) != P1_FREEZE:
        raise CompanyStoreError("Frozen P1 inventory differs")
    pins = _pins(repository)
    _canon(repository)
    routes, route_pins = _route(repository, private)
    start = datetime.fromisoformat(_time(START))
    if start.date().isoformat() <= AS_OF:
        raise CompanyStoreError("Prospective synthetic transfer chronology required")
    originals = []
    with tempfile.TemporaryDirectory(
        prefix="sec001-transfer-stage-", dir=destination.parent
    ) as staged:
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
                        **_body(scenario, record, refs, previous),
                        "event_at": event,
                        "available_at": available,
                    }
                )
                provenance = _provenance(pins, route_pins)
                command = "SEC1-" + sha(encoded([branch, system, record]))
                original = store.append_version(
                    COMPANY,
                    branch,
                    system,
                    record,
                    expected_version=0,
                    command_id=command,
                    event_at=event,
                    available_at=available,
                    content=content,
                    provenance=provenance,
                )
                originals.append(
                    {
                        **original,
                        "command_id": command,
                        "input_digest": _input_digest(
                            branch, system, record, event, available, provenance, content
                        ),
                    }
                )
                previous = refs[record] = _ref(original)
        receipt = _receipt(originals, pins, route_pins, routes)
        source = stage / "SOURCE_RECEIPT.json"
        source.write_bytes(encoded(receipt))
        source.chmod(0o600)
        database = stage / "company.sqlite3"
        manifest = {
            "schema": MANIFEST_SCHEMA,
            "status": "SEALED_PRIVATE_FUTURE_SOURCE_ONLY",
            "source_receipt_sha256": _digest(source),
            "native_db_sha256": _digest(database),
            "module_sha256": pins["enterprise/audit_suite/company_sec001_selected_transfer.py"],
            "proposal_sha256": pins[
                "enterprise/audit_suite/SEC001_SELECTED_TRANSFER_2027_PROPOSAL.md"
            ],
            "native_count": len(originals),
            "audit_task_credit": False,
            "active_P1_mutated": False,
        }
        path = stage / "RUN-MANIFEST.json"
        path.write_bytes(encoded(manifest))
        path.chmod(0o600)
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Reperform all source bytes, original links, three clocks and frozen claims."""
    raw = Path(destination).absolute()
    if any(path.is_symlink() for path in (raw, *raw.parents)):
        raise CompanyStoreError("Private selected transfer directory alias forbidden")
    destination = raw.resolve(strict=True)
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    if _p1_inventory(private) != P1_FREEZE:
        raise CompanyStoreError("Frozen P1 inventory differs")
    database = destination / "company.sqlite3"
    if any(Path(str(database) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
        raise CompanyStoreError("Selected transfer SQLite sidecar forbidden")
    if destination.stat().st_mode & 0o077 or {p.name for p in destination.iterdir()} != {
        "SOURCE_RECEIPT.json",
        "RUN-MANIFEST.json",
        "company.sqlite3",
    }:
        raise CompanyStoreError("Exact private selected transfer layout required")
    paths = {
        name: destination / name
        for name in ("SOURCE_RECEIPT.json", "RUN-MANIFEST.json", "company.sqlite3")
    }
    before = {name: _private_file(path) for name, path in paths.items()}
    pins = _pins(repository)
    _canon(repository)
    routes, route_pins = _route(repository, private)
    receipt = json.loads(paths["SOURCE_RECEIPT.json"].read_bytes())
    manifest = json.loads(paths["RUN-MANIFEST.json"].read_bytes())
    if manifest != {
        "schema": MANIFEST_SCHEMA,
        "status": "SEALED_PRIVATE_FUTURE_SOURCE_ONLY",
        "source_receipt_sha256": before["SOURCE_RECEIPT.json"][-1],
        "native_db_sha256": before["company.sqlite3"][-1],
        "module_sha256": pins["enterprise/audit_suite/company_sec001_selected_transfer.py"],
        "proposal_sha256": pins["enterprise/audit_suite/SEC001_SELECTED_TRANSFER_2027_PROPOSAL.md"],
        "native_count": 26,
        "audit_task_credit": False,
        "active_P1_mutated": False,
    }:
        raise CompanyStoreError("Selected transfer manifest differs")
    expected = []
    start = datetime.fromisoformat(_time(START))
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Selected transfer database integrity failed")
        systems = {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        }
        if systems != {
            (COMPANY, branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in SYSTEM_OWNERS.items()
        }:
            raise CompanyStoreError("Selected transfer system custody differs")
        if db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != 26 or any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "collections", "access_events")
        ):
            raise CompanyStoreError("Selected transfer rows or audit journals differ")
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
                        **_body(scenario, record, refs, previous),
                        "event_at": event,
                        "available_at": available,
                    }
                )
                provenance = _provenance(pins, route_pins)
                if (
                    row is None
                    or row["event_at"] != event
                    or row["available_at"] != available
                    or not row["imported_at"].startswith("2026-")
                    or _time(row["imported_at"]) != row["imported_at"]
                    or (previous is not None and row["imported_at"] < previous["imported_at"])
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or row["provenance"]
                    != json.dumps(provenance, sort_keys=True, separators=(",", ":"))
                    or row["content"] != body
                    or row["sha256"] != sha(body)
                    or row["command_id"] != "SEC1-" + sha(encoded([branch, system, record]))
                    or row["input_digest"]
                    != _input_digest(branch, system, record, event, available, provenance, body)
                ):
                    raise CompanyStoreError(
                        "Selected transfer original bytes, provenance or clocks differ"
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
        if receipt != _receipt(expected, pins, route_pins, routes):
            raise CompanyStoreError("Selected transfer receipt or original claim differs")
    if any(_private_file(path) != before[name] for name, path in paths.items()):
        raise CompanyStoreError("Selected transfer source changed during verification")
    if _pins(repository) != pins or _p1_inventory(private) != P1_FREEZE:
        raise CompanyStoreError("Selected transfer pins or P1 changed during verification")
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
