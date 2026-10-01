"""One fictional SH-DAT-002 rights-intake and record-scope discovery source.

The request is internally seeded training history about a payload-free marker. It
does not represent an actual individual's request, a customer instruction, a BA
determination, a completed rights action, or an audit collection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from . import company_processing_purpose_2027_simulation as purpose
from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_SELECTED_DAT002_RIGHTS_SCOPE_V1"
COMPANY = purpose.COMPANY
BRANCHES = {"CLEAN": "DAT002-RIGHTS-CLEAN", "MESSY": "DAT002-RIGHTS-MESSY"}
SOURCE_REFERENCE = "enterprise/audit_suite/company_dat002_rights_scope_2027.py"
SOURCE_ROOT = "enterprise/generated/audit-suite"
PURPOSE_FOLDER = "company-processing-purpose-2027-simulation-2026-09-29"
PURPOSE_RUN = f"{PURPOSE_FOLDER}/run-v1"
PURPOSE_REVIEW = f"{PURPOSE_FOLDER}/independent-review-v2/REVIEW.json"
ROUTE_REVIEW = (
    "documentary-283-route-reconciliation-v16-2026-10-01/independent-review-main-v1/REVIEW.json"
)
SOURCE_PINS = {
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md": (
        "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496"
    ),
    "docs/internal/development/CCF_ASSURANCE_SCOPE_PROPOSAL_2026-09-11.md": (
        "0ea41553d1f8bc975242f7ea8939f8750ec6f74e3aceb43f2e82101421a8b25a"
    ),
    "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V16_2026-10-01.json": (
        "cd3b55409e9e0112b49d060cfbbacf329660422d0c4e1b2002ec220af5bad5a3"
    ),
}
UPSTREAM_HASHES = {
    "manifest": "cffdc8ca2590d79d7d0f77aa7d6457ca06e438196d1014da84406df8796799cf",
    "receipt": "2c8e8205f20c03a1de981324db45c43cc66303ddaea60eccbce67023a452fb9d",
    "database": "2d61b583b61213d844db5764d7d6beac3aaf2a4c65799d1c3a8a7936e151e39a",
    "review": "d768b1fa01d7e2a1b56326c5a0ba14df61564d7e4cc9ccee208f0996b4f050f1",
    "route_review": "138bc8e7cd5e701d0507e4dcb6228364c3406aa097d12d14d9753c456ae60b34",
}
UNTARGETED_TASKS = (
    "TASK-SH-DAT-002-corporate-ACTION-H-RIGHTS-ASSISTANCE",
    "TASK-SH-DAT-002-corporate-CHECK-HIPAA:164.302",
    "TASK-SH-DAT-002-corporate-CHECK-HIPAA:164.500",
    "TASK-SH-DAT-002-corporate-CHECK-HIPAA:164.501",
    "TASK-SH-DAT-002-corporate-CHECK-HIPAA:164.506",
    "TASK-SH-DAT-002-corporate-CHECK-HIPAA:164.508",
    "TASK-SH-DAT-002-corporate-CHECK-HIPAA:164.510",
    "TASK-SH-DAT-002-corporate-CHECK-HIPAA:164.512",
    "TASK-SH-DAT-002-corporate-CHECK-HIPAA:164.514",
    "TASK-SH-DAT-002-corporate-CHECK-HIPAA:164.522",
    "TASK-SH-DAT-002-corporate-CHECK-SOC2:C1.1",
    "TASK-SH-DAT-002-corporate-CHECK-SOC2:CC6.7",
    "TASK-SH-DAT-002-corporate-IMPLEMENTATION",
    "TASK-SH-DAT-002-corporate-TOD",
    "TASK-SH-DAT-002-corporate-TOE",
)
DISCOVERY_TASKS = (
    UNTARGETED_TASKS[0],
    "TASK-SH-DAT-002-corporate-CHECK-HIPAA:164.501",
)
SYSTEM_OWNERS = {
    "rights_intake": "AS-P014",
    "record_scope_review": "AS-P014",
    "rights_queue": "AS-P014",
    "authority_review": "AS-P003",
    "rights_exception": "AS-P003",
    "rights_reconciliation": "AS-P014",
}
ORIGINAL_FIELDS = (
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
EXCEPTION_ID = "EXC-SIM-DAT002-RIGHTS-SCOPE-01"
LIMITS = [
    "One internally seeded, synthetic, payload-free rights inquiry per branch; no actual or "
    "externally received individual/customer request or response.",
    "The selected marker and purpose case are not a complete designated-record-set, backup, "
    "subcontractor, decision-use, disclosure or selected-period population.",
    "Customer delegation, qualified applicability, requester authority, record-set boundaries, "
    "accepted amendment and accounting completion remain unresolved.",
    "The Messy premature no-record shortcut was caught and held; its scope exception remains open.",
    "No real PHI, actual BA/legal status, release, disclosure, complete rights operation, "
    "audit collection, fresh pair, task credit or Atlas write.",
]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _context(repository: Path, private_repository: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    for relative, expected in SOURCE_PINS.items():
        path = repository / relative
        if path.is_symlink() or not path.is_file() or _digest(path) != expected:
            raise CompanyStoreError("Pinned scenario or route source differs")
    ledger = json.loads((repository / list(SOURCE_PINS)[-1]).read_text())
    if ledger.get("schema") != "SH_DOCUMENTARY_283_PAIRED_ROUTE_CANDIDATE_RECONCILIATION_V16":
        raise CompanyStoreError("Reviewed route schema differs")
    route_review = private / SOURCE_ROOT / ROUTE_REVIEW
    purpose._private(route_review, directory=False)
    if _digest(route_review) != UPSTREAM_HASHES["route_review"]:
        raise CompanyStoreError("Reviewed route pin differs")
    route_review_body = json.loads(route_review.read_text())
    if (
        route_review_body.get("verdict") != "PASS_MAIN_SELECTED_GOV_LEAD_NO_AUDIT_CREDIT"
        or route_review_body.get("output_sha256", {}).get("LEDGER.json")
        != SOURCE_PINS[list(SOURCE_PINS)[-1]]
        or route_review_body.get("audit_task_credit") is not False
    ):
        raise CompanyStoreError("Reviewed route boundary differs")
    for side in "AB":
        routes = [
            row
            for row in ledger["rows"]
            if row["side"] == side and row["control_id"] == "SH-DAT-002"
        ]
        untargeted = sorted(
            row["task_id"] for row in routes if not row["targeted_integrated_source_ids"]
        )
        if (
            len(routes) != 16
            or untargeted != sorted(UNTARGETED_TASKS)
            or any(
                row["current_status"] != "NOT_STARTED"
                or row["current_conclusion"] != "NOT_RUN"
                or row["audit_task_credit"] is not False
                for row in routes
            )
        ):
            raise CompanyStoreError("Exact 15 unrun DAT002 discovery routes differ")
    root = private / SOURCE_ROOT / PURPOSE_RUN
    review = private / SOURCE_ROOT / PURPOSE_REVIEW
    purpose._private(root, directory=True)
    paths = {
        "manifest": root / "MANIFEST.json",
        "receipt": root / "RECEIPT.json",
        "database": root / "company.sqlite3",
        "review": review,
    }
    before = purpose._frozen(paths)
    if {key: value[-1] for key, value in before.items()} != {
        key: UPSTREAM_HASHES[key] for key in paths
    }:
        raise CompanyStoreError("Reviewed purpose source bytes differ")
    manifest = json.loads(paths["manifest"].read_text())
    receipt = json.loads(paths["receipt"].read_text())
    reviewed = json.loads(review.read_text())
    if (
        manifest.get("schema") != purpose.SCHEMA + "_MANIFEST"
        or manifest.get("native_version_count") != 8
        or manifest.get("receipt_sha256") != UPSTREAM_HASHES["receipt"]
        or manifest.get("company_db_sha256") != UPSTREAM_HASHES["database"]
        or manifest.get("audit_task_credit") is not False
        or receipt.get("schema") != purpose.SCHEMA
        or receipt.get("branches") != purpose.BRANCHES
        or receipt.get("audit_task_credit") is not False
        or receipt.get("approved_execution_count_per_branch") != {"CLEAN": 0, "MESSY": 0}
        or reviewed.get("schema") != "SH_FICTIONAL_2027_PROCESSING_PURPOSE_INDEPENDENT_REVIEW_V2"
        or reviewed.get("verdict") != "PASS_PRIVATE_FICTIONAL_SOURCE_FOR_INTEGRATION_REVIEW"
        or reviewed.get("run_v1_sha256")
        != {
            "MANIFEST.json": UPSTREAM_HASHES["manifest"],
            "RECEIPT.json": UPSTREAM_HASHES["receipt"],
            "company.sqlite3": UPSTREAM_HASHES["database"],
        }
    ):
        raise CompanyStoreError("Reviewed purpose claim boundary differs")
    selected = {}
    with closing(
        sqlite3.connect(paths["database"].as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if (
            db.execute("PRAGMA quick_check").fetchone()[0] != "ok"
            or db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != 8
            or any(
                db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("grants", "collections", "access_events")
            )
        ):
            raise CompanyStoreError("Purpose source integrity or access boundary differs")
        for scenario, branch in purpose.BRANCHES.items():
            refs = receipt["records"][scenario]
            if len(refs) != 4:
                raise CompanyStoreError("Purpose original roster differs")
            selected[scenario] = {}
            for ref in refs:
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    (COMPANY, branch, ref["system"], ref["record"], ref["version"]),
                ).fetchone()
                if (
                    row is None
                    or ref["company"] != COMPANY
                    or ref["branch"] != branch
                    or ref["version"] != 1
                    or ref["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or row["sha256"] != ref["sha256"]
                    or sha(row["content"]) != ref["sha256"]
                    or any(
                        row[field] != ref[field]
                        for field in ("event_at", "available_at", "imported_at")
                    )
                ):
                    raise CompanyStoreError("Purpose native original differs")
                selected[scenario][ref["system"]] = {
                    "ref": {field: ref[field] for field in ORIGINAL_FIELDS},
                    "body": json.loads(row["content"]),
                }
            if set(selected[scenario]) != {
                "purpose_request",
                "purpose_review",
                "privacy_case_queue",
                "purpose_reconciliation",
            }:
                raise CompanyStoreError("Purpose selected system roster differs")
            request = selected[scenario]["purpose_request"]["body"]
            review_body = selected[scenario]["purpose_review"]["body"]
            reconcile = selected[scenario]["purpose_reconciliation"]["body"]
            if (
                request["marker_id"] != purpose.MARKER
                or request["payload_bytes"] != 0
                or request["real_phi_payload"] is not False
                or request["rights_request_or_response"]
                != "NONE_IN_THIS_SELECTED_FIXTURE_NOT_ENTERPRISE_NONOCCURRENCE"
                or review_body["new_flow_executed"] is not False
                or reconcile["approved_execution_count"] != 0
                or reconcile["actual_transfer_count"] != 0
                or reconcile["rights_response_count"] != 0
                or request["actual_hipaa_applicability"] != "UNDETERMINED"
                or request["task_credit"] is not False
            ):
                raise CompanyStoreError("Purpose marker or rights boundary differs")
            if scenario == "CLEAN":
                if review_body["decision"] != "SCENARIO_CONTRACT_PURPOSE_MATCH_EXECUTION_PENDING":
                    raise CompanyStoreError("Clean purpose hold differs")
            elif review_body["decision"] != "REFUSED_UNAPPROVED_AI_REUSE":
                raise CompanyStoreError("Messy purpose refusal differs")
    if purpose._frozen(paths) != before:
        raise CompanyStoreError("Purpose source changed during read")
    return selected


def _expected_rows(context: dict, scenario: str) -> list[dict]:
    if scenario not in BRANCHES:
        raise CompanyStoreError("Unknown rights branch")
    messy = scenario == "MESSY"
    upstream = context[scenario]
    if (
        set(upstream)
        != {"purpose_request", "purpose_review", "privacy_case_queue", "purpose_reconciliation"}
        or any(
            row["ref"]["branch"] != purpose.BRANCHES[scenario]
            or row["ref"]["company"] != COMPANY
            or row["ref"]["version"] != 1
            for row in upstream.values()
        )
        or upstream["purpose_request"]["body"]["marker_id"] != purpose.MARKER
        or upstream["purpose_review"]["body"]["decision"]
        != (
            "REFUSED_UNAPPROVED_AI_REUSE"
            if messy
            else "SCENARIO_CONTRACT_PURPOSE_MATCH_EXECUTION_PENDING"
        )
        or upstream["purpose_reconciliation"]["body"]["approved_execution_count"] != 0
        or upstream["purpose_reconciliation"]["body"]["actual_transfer_count"] != 0
        or upstream["purpose_reconciliation"]["body"]["rights_response_count"] != 0
    ):
        raise CompanyStoreError("Selected branch purpose hold or native identity differs")
    available = upstream["purpose_reconciliation"]["ref"]["available_at"]
    base = datetime.fromisoformat(available) + timedelta(days=1)
    purpose_refs = {name: row["ref"] for name, row in upstream.items()}
    common = {
        "schema": SCHEMA,
        "scenario": scenario,
        "truth_class": "FUTURE_TRAINING_SCENARIO_ONLY",
        "control_id": "SH-DAT-002",
        "boundary_id": "corporate",
        "marker_id": purpose.MARKER,
        "dataset_id": purpose.DATASET,
        "payload_bytes": 0,
        "real_phi_payload": False,
        "actual_request_or_customer_instruction": False,
        "actual_hipaa_applicability": "UNDETERMINED",
        "actual_ba_or_legal_status": "UNDETERMINED",
        "actual_rights_response_or_disclosure": False,
        "actor_authority_limit": "PROPOSED_CONTACT_TRAINING_SCENARIO_ONLY_NO_ACTUAL_DELEGATION",
        "task_credit": False,
    }
    intake = {
        "action": "INTERNAL_SYNTHETIC_RIGHTS_INQUIRY_SEEDED",
        "case_id": "SIM-DAT002-RIGHTS-01",
        "requester": "SIM-REQUESTER-NONPERSONAL-01",
        "simulated_customer": "SIM-COVERED-CUSTOMER-01",
        "requested_action_scopes": ["ELECTRONIC_COPY", "AMENDMENT", "ACCOUNTING"],
        "verified_customer_delegation": False,
        "verified_individual_authority": False,
        "external_message_received": False,
        "upstream_purpose_originals": purpose_refs,
    }
    scope = {
        "action": "SELECTED_MARKER_RECORD_SCOPE_SCREEN",
        "reviewed_selected_sources": ["SIM-EHR-MARKER-001", "SIM-DAT002-PURPOSE-CASE"],
        "designated_record_set_determination": "UNDETERMINED",
        "complete_record_population": False,
        "unreconciled_locations": [
            "CUSTOMER_DECISION_RECORDS",
            "RENO_AND_BOISE_BACKUPS",
            "SUBCONTRACTOR_COPY_STATUS",
            "DISCLOSURE_LOG",
            "AMENDMENT_HISTORY",
            "ACCOUNTING_POPULATION",
        ],
        "premature_no_record_mark": messy,
        "scope_conclusion": "PREMATURE_NO_RECORD_CANDIDATE" if messy else "INCOMPLETE_SEARCH_HELD",
        "record_copy_prepared": False,
    }
    authority = {
        "action": "RIGHTS_AUTHORITY_AND_RECIPIENT_GATE",
        "customer_instruction_status": "MISSING_VERIFIED_DELEGATION",
        "requester_authority_status": "UNVERIFIED_SYNTHETIC_IDENTITY",
        "ba_duty_applicability": "UNDETERMINED_BY_QUALIFIED_REVIEW",
        "decision_owner": "SIMULATED_CUSTOMER_UNCONFIRMED",
        "response_recipient": "UNDETERMINED",
        "release_decision": "HOLD_NO_RESPONSE",
        "accepted_amendment": False,
        "accounting_complete": False,
        "copy_sent": False,
    }
    queue = {
        "action": "RETAIN_SELECTED_RIGHTS_CASE",
        "case_status": "PREMATURE_NO_RECORD_MARK_HELD_FOR_REVIEW"
        if messy
        else "PENDING_CUSTOMER_AND_RECORD_SCOPE_AUTHORITY",
        "shortcut_detected": messy,
        "external_response_sent": False,
        "subject_or_payload_exported": False,
        "requested_action_scopes_open": ["ELECTRONIC_COPY", "AMENDMENT", "ACCOUNTING"],
    }
    exception = {
        "action": "OPEN_PREMATURE_NO_RECORD_SCOPE_EXCEPTION",
        "exception_id": EXCEPTION_ID,
        "detected_issue": "SELECTED_MARKER_SEARCH_MISTAKEN_FOR_COMPLETE_RECORD_SET_SEARCH",
        "first_no_record_mark_not_dispatched": True,
        "affected_case_id": "SIM-DAT002-RIGHTS-01",
        "corrective_owner": "AS-P014",
        "corrective_action": "REOPEN_SCOPE_AND_CUSTOMER_AUTHORITY_REVIEW",
        "status": "OPEN",
        "separate_from_upstream_purpose_exception": True,
    }
    reconcile = {
        "action": "RECONCILE_ONE_SELECTED_RIGHTS_INQUIRY",
        "selected_inquiry_count": 1,
        "actual_request_count": 0,
        "external_response_count": 0,
        "accepted_amendment_count": 0,
        "accounting_completion_count": 0,
        "released_copy_count": 0,
        "actual_disclosure_count": 0,
        "selected_case_status": "HELD_OPEN",
        "open_scope_exception_ids": [EXCEPTION_ID] if messy else [],
        "complete_period_population": False,
    }
    items = [
        ("rights_intake", "INTAKE-01", 0, intake),
        ("record_scope_review", "SCOPE-01", 1, scope),
    ]
    if messy:
        items += [
            ("rights_queue", "QUEUE-01", 2, queue),
            ("authority_review", "AUTH-01", 3, authority),
            ("rights_exception", "EXC-01", 4, exception),
            ("rights_reconciliation", "RECON-01", 28, reconcile),
        ]
    else:
        items += [
            ("authority_review", "AUTH-01", 2, authority),
            ("rights_queue", "QUEUE-01", 3, queue),
            ("rights_reconciliation", "RECON-01", 27, reconcile),
        ]
    rows = []
    previous = None
    for system, record, hours, details in items:
        event = _time((base + timedelta(hours=hours)).isoformat())
        availability_lag = (
            timedelta(minutes=90)
            if messy and system == "rights_exception"
            else timedelta(minutes=10)
        )
        at = _time((datetime.fromisoformat(event) + availability_lag).isoformat())
        body = {
            **common,
            "record": record,
            "actor_person_id": SYSTEM_OWNERS[system],
            "event_at": event,
            "available_at": at,
            "source_previous": previous,
            **details,
        }
        row = {
            "system": system,
            "record": record,
            "version": 1,
            "event_at": event,
            "available_at": at,
            "body": body,
            "sha256": sha(encoded(body)),
        }
        rows.append(row)
        previous = {
            key: row[key]
            for key in ("system", "record", "version", "sha256", "event_at", "available_at")
        }
    if rows[0]["event_at"] <= available or any(
        later["event_at"] <= earlier["available_at"]
        for earlier, later in zip(rows, rows[1:], strict=False)
    ):
        raise CompanyStoreError("Rights source chronology or upstream availability differs")
    return rows


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, ensure_ascii=False, indent=2)
        stream.write("\n")
    path.chmod(0o600)


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    destination = Path(destination).absolute()
    purpose._private(destination.parent, directory=True)
    if destination.exists() or destination.is_symlink() or destination != destination.resolve():
        raise CompanyStoreError("Fresh private DAT002 rights destination required")
    context = _context(repository, private_repository)
    with tempfile.TemporaryDirectory(prefix=".dat002-rights-", dir=destination.parent) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in BRANCHES.items():
            records[scenario] = []
            for system, owner in SYSTEM_OWNERS.items():
                if system != "rights_exception" or scenario == "MESSY":
                    store.register_system(COMPANY, branch, system, owner)
            for item in _expected_rows(context, scenario):
                ref = store.append_version(
                    COMPANY,
                    branch,
                    item["system"],
                    item["record"],
                    expected_version=0,
                    command_id=f"DAT002-RIGHTS-{branch}-{item['system']}-{item['record']}",
                    event_at=item["event_at"],
                    available_at=item["available_at"],
                    content=encoded(item["body"]),
                    provenance={
                        "source_reference": SOURCE_REFERENCE,
                        "scenario": scenario,
                        "source_pins": SOURCE_PINS,
                        "upstream_hashes": UPSTREAM_HASHES,
                        "qualification": "FUTURE_FICTIONAL_DISCOVERY_ONLY_NO_AUDIT_CREDIT",
                    },
                )
                if ref["sha256"] != item["sha256"]:
                    raise CompanyStoreError("DAT002 rights native serialization differs")
                records[scenario].append(ref)
        receipt = {
            "schema": SCHEMA,
            "company": COMPANY,
            "branches": BRANCHES,
            "records": records,
            "source_pins": SOURCE_PINS,
            "upstream_hashes": UPSTREAM_HASHES,
            "baseline_untargeted_task_ids_per_side": list(UNTARGETED_TASKS),
            "discovery_only_task_ids_per_side": list(DISCOVERY_TASKS),
            "native_versions_per_branch": {"CLEAN": 5, "MESSY": 6},
            "selected_synthetic_inquiries_per_branch": 1,
            "actual_requests_or_external_responses": 0,
            "accepted_amendments_or_accounting_completions": 0,
            "open_scope_exception_ids": {"CLEAN": [], "MESSY": [EXCEPTION_ID]},
            "complete_record_or_period_population": False,
            "actual_phi_or_ba_claim": False,
            "fresh_audit_pair_created": False,
            "audit_task_credit": False,
            "limits": LIMITS,
        }
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _digest(stage / "RECEIPT.json"),
            "company_db_sha256": _digest(stage / "company.sqlite3"),
            "module_sha256": _digest(Path(__file__)),
            "native_version_count": 11,
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return manifest


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    root = purpose._private(destination, directory=True)
    paths = {
        "manifest": root / "MANIFEST.json",
        "receipt": root / "RECEIPT.json",
        "database": root / "company.sqlite3",
    }
    if {member.name for member in root.iterdir()} != {
        "MANIFEST.json",
        "RECEIPT.json",
        "company.sqlite3",
    }:
        raise CompanyStoreError("Exact private three-file rights source required")
    before = purpose._frozen(paths)
    manifest = json.loads(paths["manifest"].read_text())
    receipt = json.loads(paths["receipt"].read_text())
    context = _context(repository, private_repository)
    if (
        manifest.get("schema") != SCHEMA + "_MANIFEST"
        or manifest.get("receipt_sha256") != before["receipt"][-1]
        or manifest.get("company_db_sha256") != before["database"][-1]
        or manifest.get("module_sha256") != _digest(Path(__file__))
        or manifest.get("native_version_count") != 11
        or manifest.get("audit_task_credit") is not False
        or receipt.get("schema") != SCHEMA
        or receipt.get("company") != COMPANY
        or receipt.get("branches") != BRANCHES
        or receipt.get("source_pins") != SOURCE_PINS
        or receipt.get("upstream_hashes") != UPSTREAM_HASHES
        or receipt.get("baseline_untargeted_task_ids_per_side") != list(UNTARGETED_TASKS)
        or receipt.get("discovery_only_task_ids_per_side") != list(DISCOVERY_TASKS)
        or receipt.get("native_versions_per_branch") != {"CLEAN": 5, "MESSY": 6}
        or receipt.get("selected_synthetic_inquiries_per_branch") != 1
        or receipt.get("actual_requests_or_external_responses") != 0
        or receipt.get("accepted_amendments_or_accounting_completions") != 0
        or receipt.get("open_scope_exception_ids") != {"CLEAN": [], "MESSY": [EXCEPTION_ID]}
        or receipt.get("complete_record_or_period_population") is not False
        or receipt.get("actual_phi_or_ba_claim") is not False
        or receipt.get("fresh_audit_pair_created") is not False
        or receipt.get("audit_task_credit") is not False
        or receipt.get("limits") != LIMITS
        or set(receipt.get("records", {})) != set(BRANCHES)
    ):
        raise CompanyStoreError("DAT002 rights manifest/receipt boundary differs")
    with closing(
        sqlite3.connect(paths["database"].as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if (
            db.execute("PRAGMA quick_check").fetchone()[0] != "ok"
            or db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != 11
            or any(
                db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("grants", "collections", "access_events")
            )
        ):
            raise CompanyStoreError("DAT002 rights native integrity or audit access differs")
        expected_systems = {
            (COMPANY, branch, system, owner)
            for scenario, branch in BRANCHES.items()
            for system, owner in SYSTEM_OWNERS.items()
            if system != "rights_exception" or scenario == "MESSY"
        }
        if {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        } != expected_systems:
            raise CompanyStoreError("DAT002 rights custody roster differs")
        for scenario, branch in BRANCHES.items():
            expected = _expected_rows(context, scenario)
            refs = receipt["records"][scenario]
            if len(refs) != len(expected):
                raise CompanyStoreError("DAT002 rights branch incomplete")
            provenance = {
                "source_reference": SOURCE_REFERENCE,
                "scenario": scenario,
                "source_pins": SOURCE_PINS,
                "upstream_hashes": UPSTREAM_HASHES,
                "qualification": "FUTURE_FICTIONAL_DISCOVERY_ONLY_NO_AUDIT_CREDIT",
            }
            for ref, item in zip(refs, expected, strict=True):
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=1",
                    (COMPANY, branch, item["system"], item["record"]),
                ).fetchone()
                if (
                    row is None
                    or any(
                        ref[key] != item[key]
                        for key in (
                            "system",
                            "record",
                            "version",
                            "sha256",
                            "event_at",
                            "available_at",
                        )
                    )
                    or ref["company"] != COMPANY
                    or ref["branch"] != branch
                    or ref["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or ref["provenance"] != provenance
                    or row["origin"] != ref["origin"]
                    or json.loads(row["provenance"]) != provenance
                    or row["sha256"] != item["sha256"]
                    or row["content"] != encoded(item["body"])
                    or any(
                        row[key] != ref[key] for key in ("event_at", "available_at", "imported_at")
                    )
                    or row["available_at"] < row["event_at"]
                    or datetime.fromisoformat(row["imported_at"])
                    >= datetime.fromisoformat(row["event_at"])
                ):
                    raise CompanyStoreError("DAT002 rights native original differs")
    if purpose._frozen(paths) != before:
        raise CompanyStoreError("DAT002 rights source changed during verification")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
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
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
