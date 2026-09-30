"""Selected fictional 2027 Boise issue history, separate from audit findings."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import tempfile
from contextlib import closing
from pathlib import Path

from . import company_runtime_transition_exercise as transition
from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_ASSURANCE_FINDINGS_V1"
COMPANY = transition.COMPANY
AS_OF = "2026-09-29"
QUALIFICATION = "AUTHORED_FUTURE_IN_UNIVERSE_LOCAL_ISSUE_SOURCE_NO_AUDIT_CREDIT"
TRANSITION_REL = "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/run-v3"
TRANSITION_REVIEW = (
    "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/"
    "independent-review-v3/REVIEW.json"
)
MATRIX_REL = (
    "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/run-v2/MATRIX.json"
)
MATRIX_REVIEW = (
    "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/"
    "independent-review-v2/REVIEW.json"
)
PRIVATE_PINS = {
    f"{TRANSITION_REL}/MANIFEST.json": (
        "f7c6ec3ab460f204f69cf6b50df66399687034b3b63cb38aaee84841daedcbd4"
    ),
    f"{TRANSITION_REL}/RECEIPT.json": (
        "0a0a448f619e490870f69959d196eb6d5ca3747af0d4fb68056195910ce6cc11"
    ),
    f"{TRANSITION_REL}/company.sqlite3": (
        "428b5c740cb8fc627b38f2aa6847e450fd166e62be52a6309d4f5a7b284988fd"
    ),
    TRANSITION_REVIEW: "f1acaeaea963055f99b0de120fd1b0347ee984edf085d353e7af1e427234d5a9",
    MATRIX_REL: "e9477d2074bebce185e412a3ee7c424ded395c1a1128a7c918a94f6acbd1e327",
    MATRIX_REVIEW: "c4064f6217c0e7f69276adc71004d6da7971867ccf3d844a3e198145cec31ace",
}
TRACKED = (
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md",
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md",
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
    "docs/controls/CCF_HISTORICAL_MATURITY_AND_EXCEPTION_MODEL_v0.1.md",
    "enterprise/audit_suite/ASSURANCE_FINDINGS_2027_PROPOSAL.md",
    "enterprise/audit_suite/company_assurance_findings_exercise.py",
)
SOURCE_REF = "enterprise/audit_suite/company_assurance_findings_exercise.py"
SYSTEMS = (
    "issue_screening",
    "issue_finding",
    "owner_notification",
    "remediation_request",
    "overdue_escalation",
)
RECORD = "BOISE-KEY-BYPASS-SELECTED"
DENOMINATORS = {
    "CLEAN": {
        "selected_conditions": 1,
        "screenings": 1,
        "open_findings": 0,
        "owner_notifications": 0,
        "plan_requests": 0,
        "overdue_escalation_requests": 0,
    },
    "MESSY": {
        "selected_conditions": 1,
        "screenings": 1,
        "open_findings": 1,
        "owner_notifications": 1,
        "plan_requests": 1,
        "overdue_escalation_requests": 1,
    },
}
LIMITS = [
    "2027 event/availability is authored future in-universe as of 2026-09-29; "
    "imported_at is actual insertion.",
    "One selected Boise issue condition, not complete 2027 enterprise issue population.",
    "Company-native issue history is separate from audit findings and workpapers.",
    "No closure, validation, approved plan, accepted risk, governance decision, "
    "real operation or audit credit.",
]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private_file(path: Path) -> None:
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_nlink != 1
        or path.stat().st_mode & 0o077
        or any(parent.is_symlink() for parent in path.parents)
    ):
        raise CompanyStoreError("Ordinary private source file required")


def _frozen_db(path: Path) -> tuple:
    _private_file(path)
    if any(
        Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Frozen transition DB has active sidecar")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise CompanyStoreError("Frozen transition DB must be regular")
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IMODE(info.st_mode),
        info.st_size,
        info.st_mtime_ns,
        _digest(path),
    )


def _context(repository: Path, private_repository: Path) -> tuple[dict, dict, dict]:
    repository, private_repository = repository.resolve(), private_repository.resolve()
    pins = {}
    for relative in TRACKED:
        path = repository / relative
        if not path.is_file() or path.is_symlink():
            raise CompanyStoreError("Required tracked issue source missing")
        pins[f"repo://{relative}"] = _digest(path)
    if pins[f"repo://{TRACKED[0]}"] != transition.DECISION_SHA256:
        raise CompanyStoreError("Owner fictional scenario choice differs")
    appointments = (repository / TRACKED[1]).read_text()
    if any(actor not in appointments for actor in ("AS-P005", "AS-P007", "AS-P008")):
        raise CompanyStoreError("Required canonical issue roles absent")
    for relative, expected in PRIVATE_PINS.items():
        path = private_repository / relative
        _private_file(path)
        if _digest(path) != expected:
            raise CompanyStoreError(f"Reviewed private source differs: {relative}")
        pins[f"private://{relative}"] = expected
    if json.loads((private_repository / TRANSITION_REVIEW).read_text()).get("verdict") != (
        "PASS_PRIVATE_FICTIONAL_SOURCE_FOR_INTEGRATION_REVIEW"
    ):
        raise CompanyStoreError("Transition independent review absent")
    if json.loads((private_repository / MATRIX_REVIEW).read_text()).get("verdict") != (
        "PASS_READ_ONLY_CANDIDATE_MATRIX_FOR_INTEGRATION"
    ):
        raise CompanyStoreError("Route matrix independent review absent")
    upstream_db = private_repository / TRANSITION_REL / "company.sqlite3"
    before = _frozen_db(upstream_db)
    transition.verify(private_repository / TRANSITION_REL, repository=repository)
    trans = json.loads((private_repository / TRANSITION_REL / "RECEIPT.json").read_text())
    if _frozen_db(upstream_db) != before:
        raise CompanyStoreError("Frozen transition DB changed during read")
    matrix = json.loads((private_repository / MATRIX_REL).read_text())
    routes = {}
    for side in "AB":
        found = [
            c
            for f in matrix["sides"][side]["families"]
            for c in f["controls"]
            if c["control_id"] == "SH-ASS-005"
        ]
        if (
            len(found) != 1
            or len(found[0]["tasks"]) != 4
            or found[0]["candidate_native_source_search_target"] != "Findings register"
            or any(
                task["current_status"] != "NOT_STARTED"
                or task["current_conclusion"] != "NOT_RUN"
                or task["task_credit"] is not False
                for task in found[0]["tasks"]
            )
        ):
            raise CompanyStoreError("Frozen four-route issue cohort differs")
        routes[side] = [task["task_id"] for task in found[0]["tasks"]]
    return pins, trans, routes


def _steps(scenario: str) -> tuple[tuple, ...]:
    if scenario == "CLEAN":
        return (
            (
                "issue_screening",
                "2027-07-23T09:00:00+00:00",
                "NO_SELECTED_DEFECT",
                (("CM-BOISE", 1), ("RX-BOISE", 1)),
            ),
        )
    return (
        (
            "issue_screening",
            "2027-07-23T09:00:00+00:00",
            "SELECTED_DEFECT_REQUIRES_FINDING",
            (("CM-BOISE", 1), ("EX-BOISE", 1), ("RX-BOISE", 1), ("EX-BOISE", 2)),
        ),
        (
            "issue_finding",
            "2027-07-24T09:00:00+00:00",
            "OPEN_UNVALIDATED",
            (("CM-BOISE", 1), ("RX-BOISE", 1), ("EX-BOISE", 2)),
        ),
        (
            "owner_notification",
            "2027-07-25T09:00:00+00:00",
            "ROUTED_NO_ACKNOWLEDGMENT_ASSERTED",
            (("EX-BOISE", 2),),
        ),
        (
            "remediation_request",
            "2027-08-12T09:00:00+00:00",
            "PLAN_REQUESTED_NOT_APPROVED",
            (("CM-BOISE", 2), ("RX-BOISE", 2), ("RL-BOISE", 1), ("EX-BOISE", 2)),
        ),
        (
            "overdue_escalation",
            "2027-09-02T09:00:00+00:00",
            "GOVERNANCE_ROUTING_REQUEST_NOT_REVIEWED",
            (("RL-BOISE", 1), ("EX-BOISE", 2)),
        ),
    )


def _external(trans: dict, scenario: str, names: tuple[tuple[str, int], ...]) -> list[dict]:
    refs = []
    for record, version in names:
        matches = [
            ref
            for ref in trans["records"][scenario]
            if ref["record"] == record and ref["version"] == version
        ]
        if len(matches) != 1:
            raise CompanyStoreError("Exact transition issue source unavailable")
        refs.append(
            {
                key: matches[0][key]
                for key in (
                    "company",
                    "branch",
                    "system",
                    "record",
                    "version",
                    "event_at",
                    "available_at",
                    "sha256",
                )
            }
        )
    return refs


def _body(scenario: str, step: tuple, refs: list[dict], previous: dict | None) -> dict:
    system, at, status, _ = step
    is_finding = scenario == "MESSY"
    return {
        "schema": SCHEMA,
        "scenario": scenario,
        "system": system,
        "record": RECORD,
        "status": status,
        "event_at": _time(at),
        "available_at": _time(at),
        "issue_manager_person_id": "AS-P005",
        "technical_action_owner_person_id": "AS-P007" if is_finding else None,
        "security_oversight_person_id": "AS-P008" if is_finding else None,
        "selected_condition": "BOISE_RECOVERY_INDEPENDENT_KEY_AND_LOCAL_READY_BYPASS",
        "transition_source_refs": refs,
        "prior_issue_event_sha256": previous["sha256"] if previous else None,
        "severity": "HIGH_LOCAL_PRELIMINARY" if is_finding else None,
        "severity_basis": (
            "Recovery independence and unauthorized-ready-marker exposure; "
            "no observed customer impact or provider outage asserted."
            if is_finding
            else None
        ),
        "severity_factors": (
            {
                "recovery_dependency": "FAILED_THEN_CORRECTED_TECHNICAL_GATE",
                "security": "INVALID_LOCAL_READY_MARKER_QUARANTINED",
                "customer_impact": "NOT_ESTABLISHED",
                "systemic_recurrence": "NOT_ESTABLISHED",
            }
            if is_finding
            else None
        ),
        "plan_response_due_at": _time("2027-09-01T17:00:00+00:00") if is_finding else None,
        "proposed_action": (
            "Investigate bypass root cause, constrain local-ready authority, "
            "reperform independent-key recovery and retain validation records."
            if system in {"remediation_request", "overdue_escalation"}
            else None
        ),
        "closure_criteria": (
            "Independent evidence of corrected authorization and repeat recovery "
            "plus review of historical bypass."
            if is_finding
            else None
        ),
        "technical_recovery_correction_observed": (
            system in {"remediation_request", "overdue_escalation"}
        ),
        "plan_approval": "NOT_PERFORMED",
        "durable_bypass_prevention_implemented": False,
        "validation_performed": False,
        "finding_closed": False,
        "risk_acceptance": "NOT_PERFORMED",
        "governance_decision": "NOT_PERFORMED",
        "proposed_governance_route": (
            "TECHNOLOGY_OPERATIONS_GOVERNANCE_QUEUE" if system == "overdue_escalation" else None
        ),
        "governance_delivery_status": (
            "QUEUED_NOT_ACKNOWLEDGED" if system == "overdue_escalation" else None
        ),
        "transition_bypass_exception_open": is_finding,
        "real_world_operation": False,
        "real_world_actor_action": False,
        "actual_phi_processing": False,
        "audit_task_credit": False,
        "qualification": QUALIFICATION,
    }


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Create one private source without any P1 grant, collection or task write."""
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or destination.is_symlink()
        or destination != destination.resolve()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(parent.is_symlink() for parent in destination.parents)
    ):
        raise CompanyStoreError("New private destination required")
    pins, trans, routes = _context(Path(repository), Path(private_repository))
    branches = {"CLEAN": "ISSUE-CLEAN", "MESSY": "ISSUE-MESSY"}
    with tempfile.TemporaryDirectory(prefix=".issue-stage-", dir=destination.parent) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in branches.items():
            for system in SYSTEMS:
                store.register_system(COMPANY, branch, system, "AS-P005")
            records[scenario] = []
            previous = None
            for system, at, status, names in _steps(scenario):
                refs = _external(trans, scenario, names)
                if any(ref["available_at"] >= _time(at) for ref in refs):
                    raise CompanyStoreError("Issue event predates source availability")
                step = (system, at, status, names)
                body = _body(scenario, step, refs, previous)
                ref = store.append_version(
                    COMPANY,
                    branch,
                    system,
                    RECORD,
                    expected_version=0,
                    command_id=f"IF-{branch}-{system}",
                    event_at=body["event_at"],
                    available_at=body["available_at"],
                    content=encoded(body),
                    provenance={
                        "source_reference": SOURCE_REF,
                        "source_pins": pins,
                        "scenario": scenario,
                        "qualification": QUALIFICATION,
                    },
                )
                records[scenario].append(ref)
                previous = ref
        receipt = {
            "schema": SCHEMA,
            "status": "FUTURE_FICTIONAL_LOCAL_ISSUE_HISTORY_NO_CREDIT",
            "as_of": AS_OF,
            "company": COMPANY,
            "branches": branches,
            "source_pins": pins,
            "selected_route_task_ids": routes,
            "records": records,
            "local_denominators": DENOMINATORS,
            "authority_gate": "NO_PLAN_APPROVAL_RISK_ACCEPTANCE_OR_GOVERNANCE_DISPOSITION",
            "limits": LIMITS,
        }
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _digest(stage / "RECEIPT.json"),
            "company_db_sha256": _digest(stage / "company.sqlite3"),
            "module_sha256": _digest(Path(__file__)),
            "native_version_count": 6,
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private_repository)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Reperform source pins, exact native rows, three clocks and claim limits."""
    root = Path(destination).absolute()
    if (
        root != root.resolve()
        or not root.is_dir()
        or root.stat().st_mode & 0o077
        or any(parent.is_symlink() for parent in (root, *root.parents))
        or {path.name for path in root.iterdir()}
        != {"MANIFEST.json", "RECEIPT.json", "company.sqlite3"}
    ):
        raise CompanyStoreError("Private ordinary three-file issue source required")
    for name in ("MANIFEST.json", "RECEIPT.json", "company.sqlite3"):
        _private_file(root / name)
    manifest = json.loads((root / "MANIFEST.json").read_text())
    receipt = json.loads((root / "RECEIPT.json").read_text())
    if manifest != {
        "schema": SCHEMA + "_MANIFEST",
        "receipt_sha256": _digest(root / "RECEIPT.json"),
        "company_db_sha256": _digest(root / "company.sqlite3"),
        "module_sha256": _digest(Path(__file__)),
        "native_version_count": 6,
        "audit_task_credit": False,
    }:
        raise CompanyStoreError("Issue manifest pin differs")
    pins, trans, routes = _context(Path(repository), Path(private_repository))
    if (
        receipt["schema"] != SCHEMA
        or receipt["status"] != "FUTURE_FICTIONAL_LOCAL_ISSUE_HISTORY_NO_CREDIT"
        or receipt["as_of"] != AS_OF
        or receipt["company"] != COMPANY
        or receipt["branches"] != {"CLEAN": "ISSUE-CLEAN", "MESSY": "ISSUE-MESSY"}
        or receipt["source_pins"] != pins
        or receipt["selected_route_task_ids"] != routes
        or receipt["local_denominators"] != DENOMINATORS
        or receipt["limits"] != LIMITS
        or receipt["authority_gate"] != "NO_PLAN_APPROVAL_RISK_ACCEPTANCE_OR_GOVERNANCE_DISPOSITION"
        or set(receipt["records"]) != {"CLEAN", "MESSY"}
    ):
        raise CompanyStoreError("Issue receipt scope differs")
    with closing(
        sqlite3.connect((root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Native issue database integrity failure")
        if any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] != count
            for table, count in (
                ("versions", 6),
                ("systems", 10),
                ("grants", 0),
                ("collections", 0),
                ("access_events", 0),
            )
        ):
            raise CompanyStoreError("Issue population/access differs")
        systems = {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        }
        if systems != {
            (COMPANY, branch, system, "AS-P005")
            for branch in receipt["branches"].values()
            for system in SYSTEMS
        }:
            raise CompanyStoreError("Issue system custody differs")
        for scenario, branch in receipt["branches"].items():
            steps, refs, previous = _steps(scenario), receipt["records"][scenario], None
            if len(refs) != len(steps):
                raise CompanyStoreError("Issue branch denominator differs")
            for step, ref in zip(steps, refs, strict=True):
                system, at, _status, names = step
                route = (COMPANY, branch, system, RECORD, 1)
                if (
                    tuple(ref[key] for key in ("company", "branch", "system", "record", "version"))
                    != route
                ):
                    raise CompanyStoreError("Issue route differs")
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    route,
                ).fetchone()
                if (
                    row is None
                    or row["sha256"] != ref["sha256"]
                    or sha(row["content"]) != ref["sha256"]
                    or row["command_id"] != f"IF-{branch}-{system}"
                    or any(
                        row[key] != ref[key] for key in ("event_at", "available_at", "imported_at")
                    )
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or ref["origin"] != row["origin"]
                ):
                    raise CompanyStoreError("Native issue row identity differs")
                provenance = {
                    "source_reference": SOURCE_REF,
                    "source_pins": pins,
                    "scenario": scenario,
                    "qualification": QUALIFICATION,
                }
                if json.loads(row["provenance"]) != provenance or ref["provenance"] != provenance:
                    raise CompanyStoreError("Issue provenance differs")
                external = _external(trans, scenario, names)
                if any(item["available_at"] >= _time(at) for item in external):
                    raise CompanyStoreError("Issue source availability differs")
                expected = _body(scenario, step, external, previous)
                if (
                    json.loads(row["content"]) != expected
                    or row["event_at"] != expected["event_at"]
                    or row["available_at"] != expected["available_at"]
                    or row["imported_at"] >= row["event_at"]
                ):
                    raise CompanyStoreError("Issue content or future clock differs")
                previous = ref
    return manifest
