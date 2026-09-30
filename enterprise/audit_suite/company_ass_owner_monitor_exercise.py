"""Selected fictional owner self-assessment and second-line challenge history.

This is one shared-runtime control, not an enterprise certification population,
an independent evaluation, or audit evidence collection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import stat
import tempfile
from pathlib import Path

from . import company_assurance_findings_exercise as issue
from . import company_bcm_shared_runtime_exercise as bcm
from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_ASS001_002_SELECTED_OWNER_MONITOR_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
AS_OF = "2026-09-29"
SOURCE_REF = "enterprise/audit_suite/company_ass_owner_monitor_exercise.py"
QUALIFICATION = "FUTURE_FICTIONAL_SELECTED_LOCAL_MANAGEMENT_MONITORING_NO_AUDIT_CREDIT"
RECORD = "Q3-SVC-COMPUTE-BOISE-KEY-RECOVERY"
BRANCHES = {"CLEAN": "ASS12-CLEAN", "MESSY": "ASS12-MESSY"}
SYSTEM_OWNERS = {
    "monitoring_scope": "AS-P005",
    "owner_self_assessment": "AS-P007",
    "second_line_observation": "AS-P005",
    "monitoring_escalation": "AS-P005",
}
MATRIX = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V3_2026-09-29.json"
MATRIX_REVIEW = (
    "enterprise/generated/audit-suite/documentary-283-route-reconciliation-v3-2026-09-29/"
    "independent-review-v1/REVIEW.json"
)
PBC = "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_2026-09-29.json"
BCM = "enterprise/generated/audit-suite/company-bcm-shared-runtime-2026-09-29/run-v2"
BCM_REVIEW = (
    "enterprise/generated/audit-suite/company-bcm-shared-runtime-2026-09-29/"
    "independent-review-v2/REVIEW.json"
)
ISSUE = "enterprise/generated/audit-suite/company-assurance-findings-2026-09-29/run-v1"
ISSUE_REVIEW = (
    "enterprise/generated/audit-suite/company-assurance-findings-2026-09-29/"
    "independent-review-v1/REVIEW.json"
)
TRACKED_PINS = {
    MATRIX: "f7549eca0957a92d442cfabb385ae9eed4509fada804a3dfea5d371cfbbf4d33",
    PBC: "25ea72e4b2480e11d6dc2b8d3018fb04cc1be019eb9da69bd5c6e881d947aa05",
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md": (
        "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751"
    ),
    "docs/canon/CORPORATE_HEADQUARTERS_CLOSEOUT_2026-09-03.md": (
        "25e484d7fbc2c83a37f0e7ae7fe20ff741cde176bd0c2ba7be742fa7fb3e2624"
    ),
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md": (
        "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433"
    ),
    "docs/organization/source/chartbook.json": (
        "6ba4f1ed1a14581455a62c3e79a29ca59dbaf1270dfb0db850c0376c15507b49"
    ),
}
PRIVATE_PINS = {
    MATRIX_REVIEW: "b671d3547670b5de9c7f714d51e44b6d2e65b02502dac752464b9f36d7ca1603",
    f"{BCM}/MANIFEST.json": "ea52c6c0210da3840a94a922c122b43b3e054d986cd02650a9ff70adb316d3a1",
    f"{BCM}/RECEIPT.json": "3cd0b62de445cde7c1a76f61a156fb0fd5fa9c443cf3255ca85876b6f2c4de9a",
    f"{BCM}/company.sqlite3": "9227da660fb2bf910c877fa7abbe71f119a468040c0447092d0dee8b6da64b8e",
    BCM_REVIEW: "bff0e70bf1f8e72e2e94bf9c2fa91c4adec811a13d2a53f85788b57d967d9476",
    f"{ISSUE}/MANIFEST.json": "2a5db28d3024d00e194e02219428bb133dfbbe085123bf776980ac6b68f8b89f",
    f"{ISSUE}/RECEIPT.json": "74c614682c269eb1aff431b0c834e6c0581ebbb921e2549b0e200923d2129091",
    f"{ISSUE}/company.sqlite3": "0e010fb8f34acb7c4c8dfff6e43d8e9f2d9c01c99ae36311547175a6d0026c53",
    ISSUE_REVIEW: "23033dcf6641d18038bc58a1e02fd1b014a4e550fe0ae78bd854e1f7f5552f58",
}
SOURCE_FIELDS = (
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
CLAUSES = {
    "SH-ASS-001": {
        "ACTION-S-ACCOUNTABILITY": (
            "Trace critical duties to competence evidence and backups; inspect whether "
            "recurring execution failures led to appropriate workload, training or "
            "accountability action."
        ),
        "CHECK-SOC2:CC4.1": (
            "Compare the evaluation plan with risk, change and evaluator objectivity; "
            "inspect an ongoing monitoring gap and an independently performed evaluation."
        ),
    },
    "SH-ASS-002": {
        "ACTION-H-EVALUATION": (
            "Compare material environment changes and scheduled evaluations to "
            "completed work. Inspect a nontechnical safeguard and a technical "
            "configuration for evaluated effectiveness."
        ),
        "CHECK-SOC2:CC4.1": (
            "Compare the evaluation plan with risk, change and evaluator objectivity; "
            "inspect an ongoing monitoring gap and an independently performed evaluation."
        ),
    },
}
LIMITS = [
    "2027 event/availability is authored future simulation; imported_at is actual insertion.",
    "One selected Q3 shared-service technical control and self-assessment, "
    "not all owners or the year.",
    "AS-P007 submits a local technical self-assessment, not an enterprise-accepted certification.",
    "AS-P005 is a proposed PBC contact and local Risk monitor, not an independent auditor.",
    "Prior issue screening by AS-P005 limits evaluator objectivity; no professional conclusion.",
    "Messy omitted-source history and key-bypass exception remain open after "
    "correction/escalation.",
    "No deployed enterprise monitoring population, customer/PHI claim, "
    "audit collection or task credit.",
]


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def _private(path: Path) -> tuple:
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_nlink != 1
        or path.stat().st_mode & 0o077
        or any(p.is_symlink() for p in path.parents)
    ):
        raise CompanyStoreError("Private ordinary owner-monitor source required")
    info = path.stat()
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IMODE(info.st_mode),
        info.st_size,
        info.st_mtime_ns,
        _sha(path),
    )


def _frozen(path: Path) -> tuple:
    before = _private(path)
    if any(
        Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Frozen owner-monitor source has SQLite sidecar")
    return before


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def _source_refs(root: Path, receipt: dict, scenario: str) -> dict:
    db_path = root / "company.sqlite3"
    before = _frozen(db_path)
    refs = receipt["records"][scenario]
    branch = receipt["branches"][scenario]
    with sqlite3.connect(db_path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Upstream company source integrity differs")
        native = db.execute(
            "SELECT * FROM versions WHERE branch=? ORDER BY rowid", (branch,)
        ).fetchall()
        if len(native) != len(refs):
            raise CompanyStoreError("Upstream native source population differs")
        for row, ref in zip(native, refs, strict=True):
            if (
                any(row[key] != ref[key] for key in SOURCE_FIELDS)
                or hashlib.sha256(row["content"]).hexdigest() != ref["sha256"]
            ):
                raise CompanyStoreError("Upstream source original tuple differs")
    if _frozen(db_path) != before:
        raise CompanyStoreError("Upstream company source changed during read")
    return {
        (ref["system"], ref["record"], ref["version"]): {key: ref[key] for key in SOURCE_FIELDS}
        for ref in refs
    }


def _context(repository: Path, private_repository: Path) -> tuple[dict, dict, dict, dict]:
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    pins = {}
    stable = {}
    for relative, expected in TRACKED_PINS.items():
        path = repository / relative
        if not path.is_file() or path.is_symlink() or _sha(path) != expected:
            raise CompanyStoreError(f"Tracked owner-monitor source differs: {relative}")
        pins[f"repo://{relative}"] = expected
        stable[path] = (path.stat().st_dev, path.stat().st_ino, path.stat().st_mtime_ns, expected)
    for relative, expected in PRIVATE_PINS.items():
        path = private_repository / relative
        before = _frozen(path) if relative.endswith("company.sqlite3") else _private(path)
        if before[-1] != expected:
            raise CompanyStoreError(f"Reviewed owner-monitor source differs: {relative}")
        pins[f"private://{relative}"] = expected
        stable[path] = before
    appointments = (repository / "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md").read_text()
    closeout = (repository / "docs/canon/CORPORATE_HEADQUARTERS_CLOSEOUT_2026-09-03.md").read_text()
    catalog = (repository / "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md").read_text()
    chart = json.loads((repository / "docs/organization/source/chartbook.json").read_text())
    if (
        "| AS-P005 | Martin Ives | Head of Risk and Compliance |" not in appointments
        or "| AS-P007 | Elliot Tran | Head of Enterprise Technology Services |" not in appointments
        or "Risk & Compliance does not become Internal Audit" not in closeout
        or "| SH-ASS-001 | Management performs periodic control-owner certification" not in catalog
        or "| SH-ASS-002 | Second-line compliance/control monitoring" not in catalog
        or not isinstance(chart, dict)
        or "AS-P005" not in json.dumps(chart)
        or "AS-P007" not in json.dumps(chart)
    ):
        raise CompanyStoreError("Owner or second-line canon role differs")
    matrix = json.loads((repository / MATRIX).read_text())
    review = json.loads((private_repository / MATRIX_REVIEW).read_text())
    if (
        matrix.get("schema") != "SH_DOCUMENTARY_283_PAIRED_ROUTE_CANDIDATE_RECONCILIATION_V3"
        or matrix.get("audit_task_credit") is not False
        or review.get("verdict") is None
        or not str(review["verdict"]).startswith("PASS")
    ):
        raise CompanyStoreError("Reviewed route matrix differs")
    routes = {}
    for side in "AB":
        rows = [r for r in matrix["rows"] if r["side"] == side and r["control_id"] in CLAUSES]
        if len(rows) != 10 or {r["control_id"] for r in rows} != set(CLAUSES):
            raise CompanyStoreError("Exact ten selected ASS routes differ")
        for control, authored in CLAUSES.items():
            selected = [r for r in rows if r["control_id"] == control]
            if len(selected) != 5:
                raise CompanyStoreError("Five-route ASS control denominator differs")
            for suffix, clause in authored.items():
                matches = [r for r in selected if r["task_id"].endswith(suffix)]
                if len(matches) != 1 or matches[0]["authored_test_clause"] != clause:
                    raise CompanyStoreError("Authored ASS clause differs")
        if any(
            row["current_status"] != "NOT_STARTED"
            or row["current_conclusion"] != "NOT_RUN"
            or row["audit_task_credit"] is not False
            for row in rows
        ):
            raise CompanyStoreError("ASS audit task status differs")
        routes[side] = [
            {
                "task_id": row["task_id"],
                "control_id": row["control_id"],
                "authored_test_clause": row["authored_test_clause"],
                "remaining_test_gate": row["remaining_test_gate"],
            }
            for row in rows
        ]
    pbc = json.loads((repository / PBC).read_text())
    groups = [g for g in pbc["request_groups"] if g["control_id"] in CLAUSES]
    if (
        len(groups) != 2
        or {g["control_id"] for g in groups} != set(CLAUSES)
        or any(
            g["candidate_contact_person_id"] != "AS-P005"
            or g["request_status"] != "DRAFT_NOT_SENT"
            or g["task_credit"] is not False
            or g["routes_per_side"] != 2
            for g in groups
        )
    ):
        raise CompanyStoreError("ASS PBC candidate contact/status differs")
    bcm.verify(
        private_repository / BCM, repository=repository, private_repository=private_repository
    )
    issue.verify(
        private_repository / ISSUE, repository=repository, private_repository=private_repository
    )
    bcm_receipt = json.loads((private_repository / BCM / "RECEIPT.json").read_text())
    issue_receipt = json.loads((private_repository / ISSUE / "RECEIPT.json").read_text())
    source_refs = {}
    for scenario in BRANCHES:
        source_refs[scenario] = {
            "bcm": _source_refs(private_repository / BCM, bcm_receipt, scenario),
            "issue": _source_refs(private_repository / ISSUE, issue_receipt, scenario),
        }
        expected_bcm = 8 if scenario == "CLEAN" else 10
        expected_issue = 1 if scenario == "CLEAN" else 5
        if (
            len(source_refs[scenario]["bcm"]) != expected_bcm
            or len(source_refs[scenario]["issue"]) != expected_issue
        ):
            raise CompanyStoreError("Bounded upstream branch source differs")
    for path, before in stable.items():
        if path.is_relative_to(private_repository):
            relative = path.relative_to(private_repository)
            after = _frozen(path) if str(relative).endswith("company.sqlite3") else _private(path)
        else:
            after = (path.stat().st_dev, path.stat().st_ino, path.stat().st_mtime_ns, _sha(path))
        if after != before:
            raise CompanyStoreError("Reviewed owner-monitor source changed during read")
    return pins, routes, {g["control_id"]: g for g in groups}, source_refs


def _pick(refs: dict, family: str, system: str, version: int = 1) -> dict:
    record = (
        "MARKER-RECOVERY"
        if system.startswith("exercise_")
        else (
            "BOISE-KEY-BYPASS-SELECTED"
            if family == "issue"
            else ("KEY-AND-CAPACITY" if system == "closure_gate" else "SVC-COMPUTE")
        )
    )
    try:
        return refs[family][system, record, version]
    except KeyError as exc:
        raise CompanyStoreError("Selected owner-monitor upstream tuple missing") from exc


def _steps(scenario: str, refs: dict) -> list[dict]:
    bcm_review = _pick(refs, "bcm", "exercise_review") if scenario == "CLEAN" else None
    bcm_result = _pick(refs, "bcm", "exercise_result", 1 if scenario == "CLEAN" else 2)
    issue_screen = _pick(refs, "issue", "issue_screening")
    issue_finding = _pick(refs, "issue", "issue_finding") if scenario == "MESSY" else None
    issue_overdue = _pick(refs, "issue", "overdue_escalation") if scenario == "MESSY" else None
    closure = _pick(refs, "bcm", "closure_gate") if scenario == "MESSY" else None
    source_limit = "ONE_SELECTED_CONTROL_NOT_PERIOD_OR_ENTERPRISE_POPULATION"
    schedule = {
        "event_at": _time("2027-09-05T10:00:00Z"),
        "actor_person_id": "AS-P005",
        "status": "LOCAL_MONITORING_SCOPE_RECORDED_NOT_ENTERPRISE_PLAN_ACCEPTANCE",
        "selected_service": "SVC-COMPUTE",
        "selected_control": "SH-BCM-004-BOISE-KEY-RECOVERY",
        "quarter": "2027-Q3",
        "criteria": ["exercise_result", "issue_status", "owner_exception_disclosure"],
        "scope_limit": source_limit,
        "trigger": "Q3_SELECTED_CHECK" if scenario == "CLEAN" else "POST_RETEST_AND_OPEN_FINDING",
        "candidate_contact_person_id": "AS-P005",
        "contact_authority": "PBC_PROPOSED_NOT_ACCEPTED_CORPORATE_MANDATE",
        "evaluator_objectivity_limit": "AS-P005_PREVIOUSLY_AUTHORED_SELECTED_ISSUE_SCREENING",
        "upstream_refs": [bcm_result, issue_screen],
    }
    first = {
        "event_at": _time("2027-09-08T10:00:00Z"),
        "actor_person_id": "AS-P007",
        "status": "LOCAL_TECHNICAL_SELF_ASSESSMENT_NOT_ENTERPRISE_ACCEPTED",
        "selected_service": "SVC-COMPUTE",
        "selected_control": "SH-BCM-004-BOISE-KEY-RECOVERY",
        "quarter": "2027-Q3",
        "scope_limit": source_limit,
        "statement": (
            "SELECTED_EXERCISE_REVIEWED_NO_SELECTED_DEFECT"
            if scenario == "CLEAN"
            else "SELECTED_RETEST_PASSED_NO_OPEN_ISSUE_REPORTED"
        ),
        "upstream_refs": (
            [bcm_result, bcm_review, issue_screen] if scenario == "CLEAN" else [bcm_result]
        ),
        "omitted_known_issue": scenario == "MESSY",
        "corporate_certification_accepted": False,
    }
    observation = {
        "event_at": _time("2027-09-12T10:00:00Z"),
        "actor_person_id": "AS-P005",
        "status": (
            "SELECTED_LOCAL_CHECK_NO_MISMATCH_NOT_INDEPENDENT_EVALUATION"
            if scenario == "CLEAN"
            else "SELECTED_MISMATCH_OPEN_NOT_INDEPENDENT_EVALUATION"
        ),
        "technical_input": bcm_result,
        "nontechnical_input": issue_screen if scenario == "CLEAN" else issue_finding,
        "owner_submission_sha256": hashlib.sha256(encoded(first)).hexdigest(),
        "other_source_refs": ([bcm_review] if scenario == "CLEAN" else [closure, issue_overdue]),
        "owner_omission_detected": scenario == "MESSY",
        "evaluated_effectiveness": "NOT_CONCLUDED",
        "independent_professional_assurance": False,
        "evaluator_objectivity_limit": "AS-P005_PREVIOUSLY_AUTHORED_SELECTED_ISSUE_SCREENING",
        "scope_limit": source_limit,
    }
    result = [
        {"system": "monitoring_scope", "version": 1, "body": schedule},
        {"system": "owner_self_assessment", "version": 1, "body": first},
        {"system": "second_line_observation", "version": 1, "body": observation},
    ]
    if scenario == "MESSY":
        corrected = {
            **first,
            "event_at": _time("2027-09-13T10:00:00Z"),
            "status": "CORRECTED_QUALIFIED_LOCAL_SUBMISSION_OPEN_EXCEPTION",
            "statement": "RETEST_NUMERIC_PASS_BUT_KEY_BYPASS_AND_CAPACITY_HOLD_OPEN",
            "upstream_refs": [bcm_result, closure, issue_finding, issue_overdue],
            "omitted_known_issue": False,
            "prior_submission_sha256": hashlib.sha256(encoded(first)).hexdigest(),
            "correction_does_not_erase_original": True,
        }
        escalation = {
            "event_at": _time("2027-09-14T10:00:00Z"),
            "actor_person_id": "AS-P005",
            "status": "SELECTED_EXCEPTION_ESCALATION_REQUESTED_NOT_ACCEPTED_OR_CLOSED",
            "selected_service": "SVC-COMPUTE",
            "selected_control": "SH-BCM-004-BOISE-KEY-RECOVERY",
            "qualified_submission_sha256": hashlib.sha256(encoded(corrected)).hexdigest(),
            "source_refs": [closure, issue_finding, issue_overdue],
            "requested_routing_person_ids": ["AS-P001", "AS-P008"],
            "owner_or_governance_disposition": "PENDING",
            "issue_open": True,
            "scope_limit": source_limit,
        }
        result.extend(
            [
                {"system": "owner_self_assessment", "version": 2, "body": corrected},
                {"system": "monitoring_escalation", "version": 1, "body": escalation},
            ]
        )
    if any(
        ref["available_at"] >= step["body"]["event_at"]
        for step in result
        for ref in (
            step["body"].get("upstream_refs", [])
            + step["body"].get("other_source_refs", [])
            + step["body"].get("source_refs", [])
            + [
                value
                for key, value in step["body"].items()
                if key in ("technical_input", "nontechnical_input")
            ]
        )
    ):
        raise CompanyStoreError("Owner-monitor event precedes original source availability")
    return result


def _provenance(pins: dict, scenario: str) -> dict:
    return {
        "source_reference": SOURCE_REF,
        "source_pins": pins,
        "scenario": scenario,
        "qualification": QUALIFICATION,
    }


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or destination.is_symlink()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(p.is_symlink() for p in destination.parents)
    ):
        raise CompanyStoreError("Fresh private owner-monitor source required")
    pins, routes, pbc, originals = _context(repository, private_repository)
    with tempfile.TemporaryDirectory(prefix=".ass12-stage-", dir=destination.parent) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in BRANCHES.items():
            for system, owner in SYSTEM_OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            records[scenario] = []
            for step in _steps(scenario, originals[scenario]):
                body = step["body"]
                ref = store.append_version(
                    COMPANY,
                    branch,
                    step["system"],
                    RECORD,
                    expected_version=step["version"] - 1,
                    command_id=f"ASS12-{branch}-{step['system']}-V{step['version']}",
                    event_at=body["event_at"],
                    available_at=body["event_at"],
                    content=encoded(body),
                    provenance=_provenance(pins, scenario),
                )
                records[scenario].append(ref)
        receipt = {
            "schema": SCHEMA,
            "status": "FUTURE_FICTIONAL_LOCAL_MANAGEMENT_ACTIVITY_NO_AUDIT_CREDIT",
            "as_of": AS_OF,
            "company": COMPANY,
            "branches": BRANCHES,
            "source_pins": pins,
            "selected_routes": routes,
            "pbc_candidate_groups": pbc,
            "selected_population": {
                "services": 1,
                "controls": 1,
                "quarters": 1,
                "initial_owner_submissions_per_branch": 1,
                "second_line_observations_per_branch": 1,
                "messy_corrections": 1,
                "messy_open_escalations": 1,
            },
            "records": records,
            "messy_exception_open": True,
            "corporate_certification_accepted": False,
            "independent_evaluation_completed": False,
            "source_complete": False,
            "audit_task_credit": False,
            "limits": LIMITS,
        }
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _sha(stage / "RECEIPT.json"),
            "company_db_sha256": _sha(stage / "company.sqlite3"),
            "module_sha256": _sha(Path(__file__)),
            "native_version_count": 8,
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private_repository)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    root = Path(destination).absolute()
    if (
        not root.is_dir()
        or root.is_symlink()
        or root.stat().st_mode & 0o077
        or any(p.is_symlink() for p in root.parents)
        or {p.name for p in root.iterdir()} != {"RECEIPT.json", "MANIFEST.json", "company.sqlite3"}
    ):
        raise CompanyStoreError("Private ordinary three-file owner-monitor source required")
    for name in ("RECEIPT.json", "MANIFEST.json", "company.sqlite3"):
        _private(root / name)
    before = _frozen(root / "company.sqlite3")
    manifest = json.loads((root / "MANIFEST.json").read_text())
    receipt = json.loads((root / "RECEIPT.json").read_text())
    pins, routes, pbc, originals = _context(repository, private_repository)
    if manifest != {
        "schema": SCHEMA + "_MANIFEST",
        "receipt_sha256": _sha(root / "RECEIPT.json"),
        "company_db_sha256": _sha(root / "company.sqlite3"),
        "module_sha256": _sha(Path(__file__)),
        "native_version_count": 8,
        "audit_task_credit": False,
    }:
        raise CompanyStoreError("Owner-monitor source manifest differs")
    expected_fields = {
        "schema": SCHEMA,
        "status": "FUTURE_FICTIONAL_LOCAL_MANAGEMENT_ACTIVITY_NO_AUDIT_CREDIT",
        "as_of": AS_OF,
        "company": COMPANY,
        "branches": BRANCHES,
        "source_pins": pins,
        "selected_routes": routes,
        "pbc_candidate_groups": pbc,
        "selected_population": {
            "services": 1,
            "controls": 1,
            "quarters": 1,
            "initial_owner_submissions_per_branch": 1,
            "second_line_observations_per_branch": 1,
            "messy_corrections": 1,
            "messy_open_escalations": 1,
        },
        "messy_exception_open": True,
        "corporate_certification_accepted": False,
        "independent_evaluation_completed": False,
        "source_complete": False,
        "audit_task_credit": False,
        "limits": LIMITS,
    }
    if (
        set(receipt) != set(expected_fields) | {"records"}
        or any(receipt.get(key) != value for key, value in expected_fields.items())
        or set(receipt["records"]) != set(BRANCHES)
    ):
        raise CompanyStoreError("Owner-monitor source qualification differs")
    with sqlite3.connect(
        (root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Owner-monitor native database integrity differs")
        counts = {
            name: db.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            for name in ("systems", "versions", "grants", "collections", "access_events")
        }
        if counts != {
            "systems": 8,
            "versions": 8,
            "grants": 0,
            "collections": 0,
            "access_events": 0,
        }:
            raise CompanyStoreError("Owner-monitor native/access population differs")
        systems = {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        }
        if systems != {
            (COMPANY, branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in SYSTEM_OWNERS.items()
        }:
            raise CompanyStoreError("Owner-monitor system custody differs")
        for scenario, branch in BRANCHES.items():
            rows = db.execute(
                "SELECT * FROM versions WHERE branch=? ORDER BY rowid", (branch,)
            ).fetchall()
            expected_steps = _steps(scenario, originals[scenario])
            refs = receipt["records"][scenario]
            if len(rows) != len(expected_steps) or len(refs) != len(rows):
                raise CompanyStoreError("Owner-monitor branch event denominator differs")
            for row, step, ref in zip(rows, expected_steps, refs, strict=True):
                body = step["body"]
                if (
                    (row["company"], row["branch"], row["system"], row["record"], row["version"])
                    != (COMPANY, branch, step["system"], RECORD, step["version"])
                    or row["content"] != encoded(body)
                    or row["sha256"] != hashlib.sha256(encoded(body)).hexdigest()
                    or row["event_at"] != body["event_at"]
                    or row["available_at"] != body["event_at"]
                    or row["imported_at"] >= row["event_at"]
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or json.loads(row["provenance"]) != _provenance(pins, scenario)
                    or row["command_id"] != f"ASS12-{branch}-{step['system']}-V{step['version']}"
                    or any(row[key] != ref[key] for key in SOURCE_FIELDS)
                ):
                    raise CompanyStoreError("Owner-monitor native event, source or clock differs")
    if _frozen(root / "company.sqlite3") != before:
        raise CompanyStoreError("Owner-monitor source changed during verification")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    func = create if args.action == "create" else verify
    result = func(
        args.destination, repository=args.repository, private_repository=args.private_repository
    )
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "records"}, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
