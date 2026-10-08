"""Bounded fictional policy draft, local byte distribution and generic exception."""

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

SCHEMA = "SH_FICTIONAL_2027_POLICY_EXCEPTION_LOCAL_SOURCE_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
BRANCHES = {"CLEAN": "POLICY-CLEAN", "MESSY": "POLICY-MESSY"}
QUALIFICATION = "FUTURE_LOCAL_SIMULATION_NO_POLICY_APPROVAL_OR_AUDIT_CREDIT"
SOURCE_REF = "enterprise/audit_suite/company_policy_exception_2027_exercise.py"
DOC = "docs/governance/CORPORATE_DOCUMENT_STANDARD_v0.1.md"
LEDGER = "enterprise/audit_suite/POLICY_EXCEPTION_22_ROUTE_LEDGER_2026-09-29.json"
PROPOSAL = "enterprise/audit_suite/POLICY_EXCEPTION_2027_PROPOSAL.md"
PRIVATE_BASE = "enterprise/generated/audit-suite/"
PRIVATE_PINS = {
    "company-addressable-docket-2026-09-29/run-v1/company.sqlite3": (
        "50d9fe4f9a49c72b72537a8a3d7a5dbf0b9eb3e3171d8072ffd63748bc750305"
    ),
    "company-addressable-docket-2026-09-29/run-v1/MANIFEST.json": (
        "41f3b1c783c3c84217f86edd03febad42da00a25e22fcc38c41e6bf61aa910e1"
    ),
    "company-addressable-docket-2026-09-29/run-v1/RECEIPT.json": (
        "7ef4cb845b14259acd7ecfb015ff8d0626c3b0a4a9a3052b485764f6a164e0f0"
    ),
    "company-addressable-docket-independent-review-2026-09-29-v1/REVIEW.json": (
        "5796cf3bee5075defb743401dad3831448cb5687c7f06d5df9dcba3021143c7d"
    ),
}
TRACKED_PINS = {
    DOC: "0023bb32d4cac8739bc940a54714e46da936cb6ba30ce727556b219537129bbb",
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md": (
        "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751"
    ),
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md": (
        "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433"
    ),
    LEDGER: "69cf0cbb368a58b30a9c55f1f09f0ee43895b245925a8336e5bdcb920a9118f0",
    PROPOSAL: "33e571b860a0dd1ddf7ff106fe9883d3dbcb38733ddb5a0a7fce9df53e8dc3fc",
}
ENDPOINTS = ("RISK_LOCAL_QUEUE", "SECURITY_LOCAL_QUEUE")
DUE = "2027-05-01T09:30:00+00:00"
EXCEPTION_ID = "EXC-POL-DIST-001"
SYSTEM_OWNERS = {
    "policy_baseline": "AS-P005",
    "policy_revision": "AS-P005",
    "revision_review": "AS-P003",
    "distribution_plan": "AS-P014",
    "local_delivery": "AS-P014",
    "distribution_reconcile": "AS-P005",
    "release_marker": "AS-P005",
    "generic_exception": "AS-P005",
    "exception_review": "AS-P003",
}
LIMITS = [
    "Canonical v0.1.0 is an approved design standard; fictional v0.2 remains an unapproved draft.",
    "Private endpoint byte copies are local simulation, not messages, "
    "human receipt or acknowledgment.",
    "The generic POL003 request is open and never grants a waiver or "
    "decides any HIPAA addressable item.",
    "No real 2027 operation, actual HIPAA applicability, complete policy "
    "population, audit task credit, P1, Key or Atlas write.",
]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frozen(path: Path) -> tuple:
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise CompanyStoreError("Source alias forbidden")
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600:
        raise CompanyStoreError("Private regular 0600 nlink-one source required")
    if path.suffix == ".sqlite3" and any(
        os.path.lexists(str(path) + suffix) for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("SQLite sidecar forbidden")
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IMODE(info.st_mode),
        info.st_size,
        info.st_mtime_ns,
        _digest(path),
    )


def _context(repository: Path, private_repository: Path) -> dict:
    repository, private_repository = (
        Path(repository).absolute(),
        Path(private_repository).absolute(),
    )
    pins = {}
    for relative, expected in TRACKED_PINS.items():
        path = repository / relative
        if not path.is_file() or path.is_symlink() or _digest(path) != expected:
            raise CompanyStoreError("Tracked policy source pin differs")
        pins[f"repo://{relative}"] = expected
    frozen = {}
    for relative, expected in PRIVATE_PINS.items():
        path = private_repository / PRIVATE_BASE / relative
        fingerprint = _frozen(path)
        if fingerprint[-1] != expected:
            raise CompanyStoreError("Reviewed addressable docket pin differs")
        frozen[relative] = fingerprint
        pins[f"private://{relative}"] = expected
    document = (repository / DOC).read_bytes()
    if not all(
        marker in document
        for marker in (
            b"Standard ID:** `SH-GOV-DOC-001`",
            b"Version:** 0.1.0",
            b"Approval date:** September 2, 2026",
            b"Status:** APPROVED DESIGN STANDARD",
        )
    ):
        raise CompanyStoreError("Approved design-standard metadata differs")
    catalog = (repository / "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md").read_text()
    appointments = (repository / "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md").read_text()
    if not all(
        marker in catalog
        for marker in (
            "SH-POL-001 | Enterprise policies and standards",
            "SH-POL-003 | Exceptions and waivers",
        )
    ) or not all(
        marker in appointments
        for marker in (
            "AS-P003 | Helena Ward | General Counsel",
            "AS-P005 | Martin Ives | Head of Risk and Compliance",
            "AS-P014 | Omar Vale | Data Governance and Records Lead",
        )
    ):
        raise CompanyStoreError("Proposed policy contacts or control statements differ")
    ledger = json.loads((repository / LEDGER).read_bytes())
    rows = ledger.get("rows", [])
    if (
        ledger.get("counts")
        != {
            "routes_per_side": 22,
            "controls_per_side": 4,
            "authored_clauses_per_side": 10,
            "inferred_gates_per_side": 12,
        }
        or len(rows) != 44
        or any(
            row["current_status"] != "NOT_STARTED"
            or row["current_conclusion"] != "NOT_RUN"
            or row["audit_task_credit"] is not False
            for row in rows
        )
    ):
        raise CompanyStoreError("Frozen paired policy route ledger differs")
    route_sources = {}
    for name, relative in ledger["source_paths"].items():
        path = private_repository / relative
        fingerprint = _frozen(path)
        if fingerprint[-1] != ledger["source_sha256"][name]:
            raise CompanyStoreError("Frozen policy route source differs")
        route_sources[name] = json.loads(path.read_bytes())
        pins[f"private://{relative}"] = fingerprint[-1]
        if _frozen(path) != fingerprint:
            raise CompanyStoreError("Policy route source changed during read")
    selected = [
        row
        for row in route_sources["routes"]
        if row.get("control_id") in {f"SH-POL-00{n}" for n in range(1, 5)}
    ]
    screen_by_key = {(row["side"], row["task_id"]): row for row in route_sources["screen"]["rows"]}
    matrix_by_key = {}
    for side in "AB":
        for family in route_sources["matrix"]["sides"][side]["families"]:
            for control in family["controls"]:
                if control["control_id"] in {f"SH-POL-00{n}" for n in range(1, 5)}:
                    for task in control["tasks"]:
                        matrix_by_key[side, task["task_id"]] = task
    if len(selected) != 44 or {(row["side"], row["task_id"]) for row in selected} != {
        (row["side"], row["task_id"]) for row in rows
    }:
        raise CompanyStoreError("Exact 22 paired policy task joins differ")
    for row in rows:
        key = row["side"], row["task_id"]
        screen = screen_by_key[key]
        matrix_task = matrix_by_key[key]
        if (
            row["authored_test_clause"] != screen["test_clause"]
            or row["authored_test_clause"] != matrix_task["authored_test_clause"]
            or row["test_gate_basis"] != matrix_task["test_gate_basis"]
            or row["procedure_type"] != screen["procedure_type"]
            or screen["current_status"] != "NOT_STARTED"
            or screen["current_conclusion"] != "NOT_RUN"
            or screen["task_credit_from_screen"] is not False
        ):
            raise CompanyStoreError("Policy authored clause or task status differs")
    docket = json.loads(
        (
            private_repository
            / PRIVATE_BASE
            / "company-addressable-docket-2026-09-29/run-v1/RECEIPT.json"
        ).read_bytes()
    )
    review = json.loads(
        (
            private_repository
            / PRIVATE_BASE
            / "company-addressable-docket-independent-review-2026-09-29-v1/REVIEW.json"
        ).read_bytes()
    )
    docket_manifest = json.loads(
        (
            private_repository
            / PRIVATE_BASE
            / "company-addressable-docket-2026-09-29/run-v1/MANIFEST.json"
        ).read_bytes()
    )
    if (
        docket.get("source_locator_count") != 22
        or docket.get("open_exception_counts") != {"CLEAN": 0, "MESSY": 1}
        or review.get("verdict", "").startswith("PASS") is False
        or docket_manifest.get("receipt_sha256")
        != PRIVATE_PINS["company-addressable-docket-2026-09-29/run-v1/RECEIPT.json"]
        or docket_manifest.get("company_db_sha256")
        != PRIVATE_PINS["company-addressable-docket-2026-09-29/run-v1/company.sqlite3"]
        or review.get("run_manifest_sha256")
        != PRIVATE_PINS["company-addressable-docket-2026-09-29/run-v1/MANIFEST.json"]
        or review.get("run_receipt_sha256")
        != PRIVATE_PINS["company-addressable-docket-2026-09-29/run-v1/RECEIPT.json"]
        or review.get("native_db_sha256")
        != PRIVATE_PINS["company-addressable-docket-2026-09-29/run-v1/company.sqlite3"]
    ):
        raise CompanyStoreError("Reviewed pending addressable locator status differs")
    for relative, fingerprint in frozen.items():
        if _frozen(private_repository / PRIVATE_BASE / relative) != fingerprint:
            raise CompanyStoreError("Addressable source changed during read")
    return {"pins": pins, "document": document, "frozen": frozen}


def _at(date_and_time: str) -> str:
    return _time(f"2027-{date_and_time}:00Z")


def _available(event_at: str) -> str:
    return _time((datetime.fromisoformat(event_at) + timedelta(minutes=1)).isoformat())


def _rows(context: dict, scenario: str) -> list[dict]:
    if scenario not in BRANCHES:
        raise CompanyStoreError("Unknown policy scenario")
    branch = BRANCHES[scenario]
    rows, refs = [], {}
    prior = None

    def add(name: str, system: str, at: str, data: dict, *, copy: str | None = None) -> None:
        nonlocal prior
        event = _at(at)
        body = {
            "schema": SCHEMA,
            "branch": branch,
            "scenario": scenario,
            "record_name": name,
            "event_at": event,
            "available_at": _available(event),
            "simulated_actor_person_id": SYSTEM_OWNERS[system],
            "actor_authority": "PROPOSED_LOCAL_RECORD_ROLE_ONLY",
            "source_previous": prior,
            "approved_document_id": "SH-GOV-DOC-001",
            "approved_document_version": "0.1.0",
            "approved_document_sha256": sha(context["document"]),
            "draft_v0_2_approved": False,
            "human_acknowledgment": "NOT_ESTABLISHED",
            "real_delivery_or_message": False,
            "audit_task_credit": False,
            "qualification": QUALIFICATION,
            **data,
        }
        content = encoded(body)
        ref = {
            "company": COMPANY,
            "branch": branch,
            "system": system,
            "record": name,
            "version": 1,
            "sha256": sha(content),
            "event_at": event,
            "available_at": body["available_at"],
        }
        provenance = {
            "source_reference": SOURCE_REF,
            "source_pins": context["pins"],
            "source_previous": prior,
            "scenario": scenario,
            "simulated_actor_person_id": SYSTEM_OWNERS[system],
            "local_copy_path": copy,
            "qualification": QUALIFICATION,
        }
        rows.append({"ref": ref, "content": content, "provenance": provenance, "copy": copy})
        refs[name] = ref
        prior = ref

    add(
        "BASELINE",
        "policy_baseline",
        "05-01T09:00",
        {
            "action": "PIN_APPROVED_DESIGN_STANDARD_NOT_GENERAL_POLICY_APPROVAL",
            "canonical_path": DOC,
            "canonical_sha256": sha(context["document"]),
            "approved_design_standard_date": "2026-09-02",
        },
    )
    add(
        "DRAFT",
        "policy_revision",
        "05-01T09:05",
        {
            "action": "PROPOSE_DISTRIBUTION_PROCEDURE_REVISION",
            "candidate_version": "0.2.0",
            "draft_change_summary": (
                "Require scoped endpoint denominator and dated local byte reconciliation"
            ),
            "status": "PENDING_AUTHORIZED_APPROVAL",
            "effective_at": None,
            "approval_ref": None,
            "base_ref": refs["BASELINE"],
        },
    )
    if scenario == "CLEAN":
        add(
            "DRAFT-HOLD",
            "revision_review",
            "05-01T09:10",
            {
                "action": "HOLD_DRAFT_FOR_APPROVER_AND_AUTHORITY_FACTS",
                "draft_ref": refs["DRAFT"],
                "approval_granted": False,
                "distributed_draft": False,
            },
        )
    else:
        add(
            "FALSE-RELEASE",
            "release_marker",
            "05-01T09:10",
            {
                "action": "INVALID_PREMATURE_DRAFT_RELEASE_MARKER",
                "draft_ref": refs["DRAFT"],
                "claimed_release_invalid": True,
                "effective_at": None,
                "approved_text_exists": False,
                "delivered_draft": False,
            },
        )
    add(
        "PLAN",
        "distribution_plan",
        "05-01T09:15",
        {
            "action": "DECLARE_TWO_PRIVATE_LOCAL_ENDPOINTS_FOR_APPROVED_V0_1",
            "recipient_endpoints": list(ENDPOINTS),
            "due_at": DUE,
            "draft_distributed": False,
            "approved_baseline_ref": refs["BASELINE"],
        },
    )

    def deliver(endpoint: str, when: str) -> None:
        add(
            f"DELIVER-{endpoint}",
            "local_delivery",
            when,
            {
                "action": "COPY_AND_REREAD_EXACT_APPROVED_V0_1_BYTES_LOCALLY",
                "endpoint": endpoint,
                "approved_baseline_ref": refs["BASELINE"],
                "plan_ref": refs["PLAN"],
                "source_sha256": sha(context["document"]),
                "copy_sha256": sha(context["document"]),
                "delivery_kind": "PRIVATE_LOCAL_FILE_ONLY",
                "due_at": DUE,
                "on_time": _at(when) <= DUE,
            },
            copy=f"copies/{scenario}/{endpoint}.md",
        )

    deliver("RISK_LOCAL_QUEUE", "05-01T09:20")
    if scenario == "CLEAN":
        deliver("SECURITY_LOCAL_QUEUE", "05-01T09:25")
        add(
            "RECONCILE",
            "distribution_reconcile",
            "05-01T09:31",
            {
                "action": "RECONCILE_EXACT_TWO_ENDPOINT_DENOMINATOR",
                "due_at": DUE,
                "on_time": list(ENDPOINTS),
                "missing_at_due": [],
                "late": [],
                "local_byte_checks_passed": 2,
                "policy_approval_inferred": False,
            },
        )
    else:
        add(
            "MISSED-AT-DUE",
            "distribution_reconcile",
            "05-01T09:31",
            {
                "action": "PRESERVE_MISSED_ENDPOINT_AT_DUE",
                "due_at": DUE,
                "on_time": ["RISK_LOCAL_QUEUE"],
                "missing_at_due": ["SECURITY_LOCAL_QUEUE"],
                "late": [],
                "local_byte_checks_passed": 1,
            },
        )
        add(
            "EXCEPTION-REQUEST",
            "generic_exception",
            "05-01T09:35",
            {
                "action": "FILE_SCOPED_GENERIC_DISTRIBUTION_EXCEPTION_REQUEST",
                "exception_id": EXCEPTION_ID,
                "requirement": (
                    "SH-POL-001 local approved-version distribution to declared endpoints"
                ),
                "scope": ["SECURITY_LOCAL_QUEUE"],
                "risk": "Security local endpoint lacked the approved design standard at due time",
                "proposed_compensating_measure": (
                    "Hold reliance on the missed local copy pending backfill"
                ),
                "compensating_measure_implemented": False,
                "candidate_expiry_at": "2027-05-08T09:30:00+00:00",
                "approver_id": None,
                "approval_status": "PENDING_AUTHORIZED_RISK_AND_CONTROL_OWNER_REVIEW",
                "actual_waiver_effective": False,
                "addressable_measure_decision": False,
                "missed_reconciliation_ref": refs["MISSED-AT-DUE"],
            },
        )
        add(
            "FALSE-WAIVER",
            "generic_exception",
            "05-01T09:40",
            {
                "action": "INVALID_BLANKET_WAIVER_MARKER",
                "exception_id": EXCEPTION_ID,
                "scope_claimed": "ALL_POLICY_AND_HIPAA_ADDRESSABLE_DUTIES",
                "valid": False,
                "approved": False,
                "effective": False,
                "request_ref": refs["EXCEPTION-REQUEST"],
            },
        )
        add(
            "QUARANTINE",
            "exception_review",
            "05-01T09:45",
            {
                "action": "QUARANTINE_INVALID_RELEASE_AND_WAIVER_MARKERS",
                "release_marker_ref": refs["FALSE-RELEASE"],
                "waiver_marker_ref": refs["FALSE-WAIVER"],
                "generic_request_ref": refs["EXCEPTION-REQUEST"],
                "legal_or_risk_approval_granted": False,
                "hipaa_addressable_decision": False,
                "exception_status": "OPEN_PENDING_AUTHORITY",
            },
        )
        deliver("SECURITY_LOCAL_QUEUE", "05-02T10:00")
        add(
            "LATE-RECONCILE",
            "distribution_reconcile",
            "05-02T10:05",
            {
                "action": "RECONCILE_BACKFILL_WITHOUT_ERASING_MISSED_INTERVAL",
                "prior_missed_ref": refs["MISSED-AT-DUE"],
                "late_delivery_ref": refs["DELIVER-SECURITY_LOCAL_QUEUE"],
                "on_time": ["RISK_LOCAL_QUEUE"],
                "missing_at_due": ["SECURITY_LOCAL_QUEUE"],
                "late": ["SECURITY_LOCAL_QUEUE"],
                "current_local_copy_count": 2,
                "exception_status": "OPEN_PENDING_AUTHORITY",
            },
        )
        add(
            "EXPIRY-ESCALATE",
            "exception_review",
            "06-01T10:00",
            {
                "action": "ESCALATE_UNAPPROVED_EXPIRED_REQUEST",
                "request_ref": refs["EXCEPTION-REQUEST"],
                "backfill_ref": refs["LATE-RECONCILE"],
                "candidate_expiry_at": "2027-05-08T09:30:00+00:00",
                "exception_status": "OPEN_EXPIRED_UNAPPROVED",
                "waiver_ever_effective": False,
                "historical_missed_interval_remains": True,
            },
        )
    return rows


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def _copy(path: Path, content: bytes) -> tuple:
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    path.parent.chmod(0o700)
    path.parent.parent.chmod(0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes() != content:
        raise CompanyStoreError("Local copied bytes differ")
    return _frozen(path)


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Publish a new isolated future-fictional company source, never an audit result."""
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or destination.is_symlink()
        or destination != destination.resolve()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(part.is_symlink() for part in (destination, *destination.parents))
    ):
        raise CompanyStoreError("New private ordinary destination required")
    context = _context(repository, private_repository)
    with tempfile.TemporaryDirectory(
        prefix=".policy-exception-stage-", dir=destination.parent
    ) as tmp:
        stage = Path(tmp)
        store = CompanyStore(stage)
        records, copies = {}, {}
        for scenario, branch in BRANCHES.items():
            for system, owner in SYSTEM_OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            records[scenario], copies[scenario] = [], []
            for item in _rows(context, scenario):
                ref = item["ref"]
                if item["copy"] is not None:
                    fingerprint = _copy(stage / item["copy"], context["document"])
                    copies[scenario].append(
                        {
                            "path": item["copy"],
                            "sha256": sha(context["document"]),
                            "inode": fingerprint[1],
                            "size": fingerprint[3],
                            "mode": 0o600,
                        }
                    )
                native = store.append_version(
                    COMPANY,
                    branch,
                    ref["system"],
                    ref["record"],
                    expected_version=0,
                    command_id=f"PE-{branch}-{ref['record']}",
                    event_at=ref["event_at"],
                    available_at=ref["available_at"],
                    content=item["content"],
                    provenance=item["provenance"],
                )
                if any(native[key] != ref[key] for key in ref):
                    raise CompanyStoreError("Policy native row differs at creation")
                records[scenario].append(native)
        receipt = {
            "schema": SCHEMA,
            "status": "FUTURE_FICTIONAL_LOCAL_POLICY_AND_OPEN_EXCEPTION_NO_CREDIT",
            "company": COMPANY,
            "branches": BRANCHES,
            "source_pins": context["pins"],
            "records": records,
            "copies": copies,
            "counts": {scenario: len(values) for scenario, values in records.items()},
            "declared_endpoints": list(ENDPOINTS),
            "approved_version_distributed": "0.1.0",
            "draft_version_status": "0.2.0_PENDING_AUTHORIZED_APPROVAL",
            "open_generic_exception_ids": {"CLEAN": [], "MESSY": [EXCEPTION_ID]},
            "hipaa_addressable_docket_role": "SEPARATE_22_PENDING_LOCATORS_NOT_WAIVERS",
            "audit_task_credit": False,
            "limits": LIMITS,
        }
        _write(stage / "RECEIPT.json", receipt)
        _write(
            stage / "MANIFEST.json",
            {
                "schema": SCHEMA + "_MANIFEST",
                "receipt_sha256": _digest(stage / "RECEIPT.json"),
                "company_db_sha256": _digest(stage / "company.sqlite3"),
                "module_sha256": _digest(Path(__file__)),
                "native_version_count": sum(map(len, records.values())),
                "local_copy_count": sum(map(len, copies.values())),
                "audit_task_credit": False,
            },
        )
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private_repository)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Reperform exact source joins, copy identity, chronology and no-credit limits."""
    root = Path(destination).absolute()
    if (
        root != root.resolve()
        or not root.is_dir()
        or root.stat().st_mode & 0o077
        or any(part.is_symlink() for part in (root, *root.parents))
        or {path.name for path in root.iterdir()}
        != {"MANIFEST.json", "RECEIPT.json", "company.sqlite3", "copies"}
    ):
        raise CompanyStoreError("Private ordinary policy source required")
    before = {
        name: _frozen(root / name) for name in ("MANIFEST.json", "RECEIPT.json", "company.sqlite3")
    }
    manifest = json.loads((root / "MANIFEST.json").read_bytes())
    receipt = json.loads((root / "RECEIPT.json").read_bytes())
    context = _context(repository, private_repository)
    expected_rows = {scenario: _rows(context, scenario) for scenario in BRANCHES}
    count = sum(map(len, expected_rows.values()))
    if manifest != {
        "schema": SCHEMA + "_MANIFEST",
        "receipt_sha256": before["RECEIPT.json"][-1],
        "company_db_sha256": before["company.sqlite3"][-1],
        "module_sha256": _digest(Path(__file__)),
        "native_version_count": count,
        "local_copy_count": 4,
        "audit_task_credit": False,
    }:
        raise CompanyStoreError("Policy manifest differs")
    if receipt != {
        "schema": SCHEMA,
        "status": "FUTURE_FICTIONAL_LOCAL_POLICY_AND_OPEN_EXCEPTION_NO_CREDIT",
        "company": COMPANY,
        "branches": BRANCHES,
        "source_pins": context["pins"],
        "records": receipt.get("records"),
        "copies": receipt.get("copies"),
        "counts": {scenario: len(values) for scenario, values in expected_rows.items()},
        "declared_endpoints": list(ENDPOINTS),
        "approved_version_distributed": "0.1.0",
        "draft_version_status": "0.2.0_PENDING_AUTHORIZED_APPROVAL",
        "open_generic_exception_ids": {"CLEAN": [], "MESSY": [EXCEPTION_ID]},
        "hipaa_addressable_docket_role": "SEPARATE_22_PENDING_LOCATORS_NOT_WAIVERS",
        "audit_task_credit": False,
        "limits": LIMITS,
    }:
        raise CompanyStoreError("Policy receipt scope differs")
    copy_root = root / "copies"
    if (
        not copy_root.is_dir()
        or copy_root.is_symlink()
        or stat.S_IMODE(copy_root.stat().st_mode) != 0o700
        or {p.name for p in copy_root.iterdir()} != set(BRANCHES)
    ):
        raise CompanyStoreError("Private copy branch inventory differs")
    copy_before = {}
    seen_inodes = {before["company.sqlite3"][1]}
    for scenario in BRANCHES:
        folder = copy_root / scenario
        if (
            not folder.is_dir()
            or folder.is_symlink()
            or stat.S_IMODE(folder.stat().st_mode) != 0o700
            or {p.name for p in folder.iterdir()} != {f"{ep}.md" for ep in ENDPOINTS}
        ):
            raise CompanyStoreError("Exact local endpoint copy inventory differs")
        expected_copy_rows = [row for row in expected_rows[scenario] if row["copy"]]
        got_copies = receipt["copies"][scenario]
        if len(got_copies) != 2:
            raise CompanyStoreError("Two local copies per branch required")
        for expected, got in zip(expected_copy_rows, got_copies, strict=True):
            name = expected["copy"]
            fingerprint = _frozen(root / name)
            copy_before[name] = fingerprint
            if (
                got
                != {
                    "path": name,
                    "sha256": sha(context["document"]),
                    "inode": fingerprint[1],
                    "size": len(context["document"]),
                    "mode": 0o600,
                }
                or fingerprint[1] in seen_inodes
                or (root / name).read_bytes() != context["document"]
            ):
                raise CompanyStoreError("Local endpoint bytes or inode differ")
            seen_inodes.add(fingerprint[1])
    with closing(
        sqlite3.connect((root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Policy native database integrity differs")
        if any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] != expected
            for table, expected in (
                ("versions", count),
                ("systems", len(BRANCHES) * len(SYSTEM_OWNERS)),
                ("grants", 0),
                ("collections", 0),
                ("access_events", 0),
            )
        ):
            raise CompanyStoreError("Policy source/access denominator differs")
        if {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        } != {
            (COMPANY, branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in SYSTEM_OWNERS.items()
        }:
            raise CompanyStoreError("Policy source owner registry differs")
        keys = set()
        for scenario, branch in BRANCHES.items():
            got = receipt["records"][scenario]
            if len(got) != len(expected_rows[scenario]):
                raise CompanyStoreError("Policy branch row count differs")
            prior_import = None
            for item, ref in zip(expected_rows[scenario], got, strict=True):
                target = item["ref"]
                key = tuple(target[k] for k in ("company", "branch", "system", "record", "version"))
                keys.add(key)
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    key,
                ).fetchone()
                if (
                    row is None
                    or row["content"] != item["content"]
                    or row["sha256"] != target["sha256"]
                    or sha(row["content"]) != target["sha256"]
                    or json.loads(row["provenance"]) != item["provenance"]
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or row["command_id"] != f"PE-{branch}-{target['record']}"
                    or any(row[k] != target[k] for k in ("event_at", "available_at"))
                    or any(ref[k] != target[k] for k in target)
                    or any(ref[k] != row[k] for k in ("sha256", "imported_at", "origin"))
                    or row["imported_at"] >= row["event_at"]
                    or (prior_import is not None and row["imported_at"] < prior_import)
                ):
                    raise CompanyStoreError("Policy native content, clock or provenance differs")
                prior_import = row["imported_at"]
        if {
            tuple(row)
            for row in db.execute("SELECT company,branch,system,record,version FROM versions")
        } != keys:
            raise CompanyStoreError("Unexpected policy native row")
    if {name: _frozen(root / name) for name in before} != before:
        raise CompanyStoreError("Policy run changed during read")
    if {name: _frozen(root / name) for name in copy_before} != copy_before:
        raise CompanyStoreError("Local copy changed during read")
    return manifest
