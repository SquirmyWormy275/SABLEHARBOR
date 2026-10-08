"""One fictional customer-concern intake with held replies and no external send."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path

from . import company_product_customer_internal_2027_simulation as prior
from .company_store import CompanyStore, CompanyStoreError, _time
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_SELECTED_PRD_CONCERN_INTAKE_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
BRANCHES = {"CLEAN": "PRD-CONCERN-CLEAN", "MESSY": "PRD-CONCERN-MESSY"}
SPEC = "enterprise/audit_suite/prd_concern_intake_2027_spec_v1.json"
SPEC_SHA256 = "dde9f62c3de873bdf2ae8769f529e6bb43369f74038af1682ad94ff62caf5415"
SOURCE_REFERENCE = "enterprise/audit_suite/company_prd_concern_intake_2027.py"
SOURCE_ROOT = "enterprise/generated/audit-suite"
PRD_FOLDER = "company-prd-internal-customer-2026-09-29"
PRD_RUN = f"{PRD_FOLDER}/run-v2"
PRD_REVIEW = f"{PRD_FOLDER}/independent-review-v2/REVIEW.json"
UPSTREAM_HASHES = {
    "manifest": "438e21b197d7768a23912cf5850b076ec1ddb35b564e885fd144acd9ca9c9d2b",
    "receipt": "81b5a7f15636f824c6c48c449c726c1176d95c4ce7e70105b813730dc2b17842",
    "database": "a0ebf7b743f530408ea497abb791b2991694f65f5b076b933c16fc8a61318507",
    "review": "5f5289ec43d7644f4e623ca7dbf13896f807f351d5488461dc5ba257119f9122",
}
SYSTEM_OWNERS = {
    "simulated_inbox": "P004",
    "case_intake": "P004",
    "recipient_matrix": "P004",
    "concern_assessment": "P002",
    "legal_gate": "AS-P003",
    "response_draft": "P004",
    "dispatch_attempt": "P004",
    "dispatch_gate": "P002",
    "reconciliation": "P004",
    "exception_register": "P004",
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


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    path.chmod(0o600)


def _ref(receipt: dict, side: str, system: str, record: str, version: int = 1) -> dict:
    matches = [
        row
        for row in receipt["records"][side]
        if (row["system"], row["record"], row["version"]) == (system, record, version)
    ]
    if len(matches) != 1:
        raise CompanyStoreError("Selected PRD upstream version missing or ambiguous")
    return {field: matches[0][field] for field in ORIGINAL_FIELDS}


def _context(repository: Path, private_repository: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    spec_path = repository / SPEC
    if not spec_path.is_file() or spec_path.is_symlink() or _sha(spec_path) != SPEC_SHA256:
        raise CompanyStoreError("Selected concern specification differs")
    spec = json.loads(spec_path.read_text())
    if (
        spec.get("schema") != "SH_FICTIONAL_2027_PRD_CONCERN_INTAKE_SPEC_V1"
        or spec.get("truth_class") != "TRAINING_SCENARIO_ONLY"
        or spec.get("customer_id") != prior.CUSTOMER
        or spec.get("service_id") != prior.SERVICE
        or spec.get("change_id") != prior.CHANGE
        or spec.get("concern_id") != "SIM-CUSTOMER-CONCERN-01"
        or spec.get("selected_internal_recipient_roles")
        != ["CUSTOMER_DELIVERY", "LEGAL", "PRODUCT", "SUPPORT_RECOVERY"]
        or spec.get("expected_native_versions") != {"CLEAN": 8, "MESSY": 13}
        or spec.get("chronology") != {"CLEAN": "2027-11-19", "MESSY": "2027-11-20"}
    ):
        raise CompanyStoreError("Selected concern scope differs")
    source_root = private_repository / SOURCE_ROOT
    run = source_root / PRD_RUN
    review = source_root / PRD_REVIEW
    paths = {
        "manifest": run / "MANIFEST.json",
        "receipt": run / "RECEIPT.json",
        "database": run / "company.sqlite3",
        "review": review,
    }
    prior._private(run, directory=True)
    prior._private(review.parent, directory=True)
    before = prior._frozen(paths)
    if {key: value[-1] for key, value in before.items()} != UPSTREAM_HASHES:
        raise CompanyStoreError("Reviewed PRD source bytes differ")
    reviewed = json.loads(review.read_text())
    if (
        reviewed.get("verdict") != "PASS_BOUNDED_FICTIONAL_SOURCE_FOR_INTEGRATION"
        or reviewed.get("database_sha256") != UPSTREAM_HASHES["database"]
        or reviewed.get("receipt_sha256") != UPSTREAM_HASHES["receipt"]
        or reviewed.get("manifest_sha256") != UPSTREAM_HASHES["manifest"]
    ):
        raise CompanyStoreError("Selected PRD independent review differs")
    prior.verify(run, repository=repository, private_repository=private_repository)
    if prior._frozen(paths) != before:
        raise CompanyStoreError("Reviewed PRD source changed during verification")
    receipt = json.loads(paths["receipt"].read_text())
    if (
        receipt.get("schema") != prior.SCHEMA
        or receipt.get("external_send_counts") != {"CLEAN": 0, "MESSY": 0}
        or receipt.get("authored_external_communication_clause_support") is not False
    ):
        raise CompanyStoreError("PRD internal-only receipt boundary differs")
    refs = {}
    with sqlite3.connect(paths["database"].as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        for side, branch in prior.BRANCHES.items():
            refs[side] = {
                "case": _ref(receipt, side, "commitment_scope", "CASE-01"),
                "change": _ref(receipt, side, "change_request", "CHANGE-01"),
                "impact": _ref(
                    receipt, side, "impact_assessment", "IMPACT-01", 2 if side == "MESSY" else 1
                ),
                "notice": _ref(
                    receipt, side, "notice_decision", "NOTICE-01", 2 if side == "MESSY" else 1
                ),
                "reconciliation": _ref(receipt, side, "reconciliation", "RECON-01"),
            }
            if side == "MESSY":
                refs[side]["historical_concern"] = _ref(
                    receipt, side, "internal_concern", "CONCERN-01"
                )
                refs[side]["historical_discovery"] = _ref(
                    receipt, side, "dependency_discovery", "DISC-01"
                )
            for key, ref in refs[side].items():
                native = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    (COMPANY, branch, ref["system"], ref["record"], ref["version"]),
                ).fetchone()
                if native is None or {field: native[field] for field in ORIGINAL_FIELDS} != ref:
                    raise CompanyStoreError(f"PRD native original tuple differs: {side}:{key}")
                body = json.loads(native["content"])
                if (
                    body.get("customer_id") != spec["customer_id"]
                    or body.get("service_id") != spec["service_id"]
                    or body.get("change_id") != spec["change_id"]
                    or body.get("real_external_message_sent") is not False
                    or body.get("customer_receipt_or_acknowledgment") is not False
                ):
                    raise CompanyStoreError("PRD upstream customer or send boundary differs")
                if key == "notice" and (
                    body.get("send_gate") != "BLOCKED_NO_EXTERNAL_DELIVERY"
                    or body.get("external_notice_duty") != "UNDETERMINED_PENDING_CUSTOMER_TERMS"
                ):
                    raise CompanyStoreError("PRD notice authority remains unresolved")
                if key == "reconciliation" and (
                    body.get("external_messages_sent") != 0
                    or body.get("external_customer_receipts") != 0
                    or body.get("notice_duty_resolved") is not False
                ):
                    raise CompanyStoreError("PRD reconciliation external boundary differs")
                if _time(ref["available_at"]) >= _time(
                    spec["chronology"][side] + "T09:00:00+00:00"
                ):
                    raise CompanyStoreError("PRD original unavailable before concern intake")
    if prior._frozen(paths) != before:
        raise CompanyStoreError("Reviewed PRD source changed during concern read")
    return {"spec": spec, "refs": refs}


def _plan(side: str) -> list[tuple[str, str, str, str, str, str, list[str], bool]]:
    complete = ["CUSTOMER_DELIVERY", "LEGAL", "PRODUCT", "SUPPORT_RECOVERY"]
    omitted = ["CUSTOMER_DELIVERY", "LEGAL", "PRODUCT"]
    shared = [
        (
            "09:00",
            "simulated_inbox",
            "CLAIM-01",
            "SIM-UNVERIFIED-CLIENT-OPS-01",
            "LOCAL_SIMULATED_INBOUND_CONCERN",
            "CLAIMANT_UNVERIFIED",
            [],
            False,
        ),
        (
            "09:10",
            "case_intake",
            "INTAKE-01",
            "P004",
            "REGISTER_SELECTED_CONCERN",
            "INTERNAL_TRIAGE_OPEN",
            [],
            False,
        ),
    ]
    if side == "CLEAN":
        return shared + [
            (
                "09:20",
                "recipient_matrix",
                "MATRIX-01",
                "P004",
                "MAP_SELECTED_INTERNAL_ROLES",
                "SELECTED_INTERNAL_ROLES_LISTED",
                complete,
                False,
            ),
            (
                "09:30",
                "concern_assessment",
                "ASSESS-01",
                "P002",
                "ASSESS_PROPOSED_RESPONSIBILITY",
                "CHANGE_NOT_DEPLOYED",
                [],
                False,
            ),
            (
                "09:40",
                "legal_gate",
                "LEGAL-01",
                "AS-P003",
                "REVIEW_CONTACT_AND_NOTICE_AUTHORITY",
                "HOLD_AUTHORITY_UNRESOLVED",
                [],
                False,
            ),
            (
                "09:50",
                "response_draft",
                "DRAFT-01",
                "P004",
                "PREPARE_SELECTED_SUPPORT_RESPONSE",
                "DRAFT_HELD",
                complete,
                False,
            ),
            (
                "10:00",
                "dispatch_gate",
                "GATE-01",
                "P002",
                "BLOCK_EXTERNAL_DISPATCH",
                "DENIED_NO_SEND",
                complete,
                False,
            ),
            (
                "10:30",
                "reconciliation",
                "RECON-01",
                "P004",
                "RECONCILE_SELECTED_CASE",
                "OPEN_NO_DELIVERY_OR_ACK",
                complete,
                False,
            ),
        ]
    return shared + [
        (
            "09:20",
            "recipient_matrix",
            "MATRIX-INITIAL",
            "P004",
            "MAP_INCOMPLETE_INTERNAL_ROLES",
            "SUPPORT_RECOVERY_OMITTED",
            omitted,
            False,
        ),
        (
            "09:30",
            "response_draft",
            "DRAFT-INITIAL",
            "P004",
            "PREPARE_INCOMPLETE_RESPONSE",
            "DRAFT_INCOMPLETE",
            omitted,
            False,
        ),
        (
            "09:35",
            "dispatch_attempt",
            "ATTEMPT-01",
            "P004",
            "TRY_LOCAL_DISPATCH_WITHOUT_AUTHORITY",
            "INVALID_ATTEMPT",
            omitted,
            False,
        ),
        (
            "09:36",
            "dispatch_gate",
            "DENY-01",
            "P002",
            "DENY_LOCAL_DISPATCH",
            "DENIED_NO_SEND",
            omitted,
            False,
        ),
        (
            "09:45",
            "reconciliation",
            "FALSE-CLOSE",
            "P004",
            "CLAIM_SELECTED_ROUTING_COMPLETE",
            "FALSE_CLEAN",
            omitted,
            True,
        ),
        (
            "10:00",
            "concern_assessment",
            "DISCOVERY-01",
            "P002",
            "DETECT_MISSING_SUPPORT_AND_FALSE_CLOSE",
            "GAP_CONFIRMED",
            omitted,
            False,
        ),
        (
            "10:05",
            "exception_register",
            "EXCEPTION-OPEN",
            "P004",
            "OPEN_HISTORICAL_RECIPIENT_EXCEPTION",
            "OPEN",
            omitted,
            False,
        ),
        (
            "10:30",
            "recipient_matrix",
            "MATRIX-CORRECTED",
            "P004",
            "CORRECT_SELECTED_INTERNAL_ROLES",
            "CURRENT_MATRIX_CORRECTED",
            complete,
            False,
        ),
        (
            "10:40",
            "legal_gate",
            "LEGAL-01",
            "AS-P003",
            "REVIEW_CORRECTED_CASE_AUTHORITY",
            "HOLD_AUTHORITY_UNRESOLVED",
            complete,
            False,
        ),
        (
            "10:50",
            "response_draft",
            "DRAFT-CORRECTED",
            "P004",
            "CORRECT_DRAFT_WITHOUT_SEND",
            "DRAFT_HELD",
            complete,
            False,
        ),
        (
            "11:00",
            "reconciliation",
            "RECON-01",
            "P004",
            "RECONCILE_CORRECTED_CASE_AND_HISTORY",
            "HISTORICAL_EXCEPTION_OPEN_NO_SEND",
            complete,
            False,
        ),
    ]


def _rows(context: dict, side: str) -> list[dict]:
    spec = context["spec"]
    branch = BRANCHES[side]
    rows = []
    for clock, system, record, actor, action, status, roles, claimed_complete in _plan(side):
        at = _time(spec["chronology"][side] + "T" + clock + ":00+00:00")
        body = {
            "schema": SCHEMA + "_NATIVE_EVENT",
            "truth_class": "TRAINING_SCENARIO_ONLY",
            "company": COMPANY,
            "branch": branch,
            "customer_id": spec["customer_id"],
            "service_id": spec["service_id"],
            "change_id": spec["change_id"],
            "concern_id": spec["concern_id"],
            "claimant_id": spec["claimant_id"],
            "claimant_customer_identity_verified": False,
            "actor_id": actor,
            "actor_authority": "SCENARIO_CONTACT_ONLY_NO_ACCEPTED_EXTERNAL_SIGNATORY",
            "action": action,
            "status": status,
            "selected_internal_recipient_roles": roles,
            "claimed_selected_routing_complete": claimed_complete,
            "external_notice_duty": "UNDETERMINED_PENDING_CUSTOMER_TERMS",
            "company_outbound_delivery_accepted": False,
            "separate_customer_acknowledgment_exists": False,
            "real_external_messages_sent": 0,
            "fictional_accepted_deliveries": 0,
            "regulated_payload_bytes": 0,
            "actual_phi_processing": False,
            "authored_communication_clause_satisfied": False,
            "historical_exception_open": side == "MESSY"
            and record
            in {"EXCEPTION-OPEN", "MATRIX-CORRECTED", "LEGAL-01", "DRAFT-CORRECTED", "RECON-01"},
            "event_at": at,
            "previous_native_content": (
                {"record": rows[-1]["record"], "sha256": rows[-1]["sha256"]} if rows else None
            ),
            "upstream_original_refs": context["refs"][side] if not rows else None,
        }
        content = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        rows.append(
            {
                "system": system,
                "record": record,
                "event_at": at,
                "available_at": at,
                "content": content,
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    if len(rows) != spec["expected_native_versions"][side]:
        raise CompanyStoreError("Selected concern denominator differs")
    return rows


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    destination = Path(destination).absolute()
    prior._private(destination.parent, directory=True)
    if destination.exists() or destination.is_symlink() or destination != destination.resolve():
        raise CompanyStoreError("Fresh private concern destination required")
    context = _context(repository, private_repository)
    with tempfile.TemporaryDirectory(prefix=".prd-concern-stage-", dir=destination.parent) as temp:
        stage = Path(temp)
        store = CompanyStore(stage)
        refs = {}
        for side, branch in BRANCHES.items():
            for system, owner in SYSTEM_OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            refs[side] = []
            for row in _rows(context, side):
                ref = store.append_version(
                    COMPANY,
                    branch,
                    row["system"],
                    row["record"],
                    expected_version=0,
                    command_id=f"PCI-{branch}-{row['record']}",
                    event_at=row["event_at"],
                    available_at=row["available_at"],
                    content=row["content"],
                    provenance={
                        "source_reference": SOURCE_REFERENCE,
                        "truth_class": "TRAINING_SCENARIO_ONLY",
                    },
                )
                if ref["sha256"] != row["sha256"]:
                    raise CompanyStoreError("Concern native content differs")
                refs[side].append(ref)
        receipt = {
            "schema": SCHEMA,
            "company": COMPANY,
            "branches": BRANCHES,
            "records": refs,
            "spec_sha256": SPEC_SHA256,
            "reviewed_prd_source_sha256": UPSTREAM_HASHES,
            "upstream_original_refs": context["refs"],
            "native_version_counts": {side: len(rows) for side, rows in refs.items()},
            "selected_concern_count": 1,
            "selected_claimant_verified": False,
            "internal_draft_status": {"CLEAN": "HELD", "MESSY": "HELD_AFTER_CORRECTION"},
            "local_open_exception_counts": {"CLEAN": 0, "MESSY": 1},
            "real_external_messages_sent": 0,
            "fictional_accepted_deliveries": 0,
            "customer_acknowledgments": 0,
            "actual_phi_processing": False,
            "source_complete": False,
            "fresh_audit_pair_created": False,
            "audit_task_credit": False,
            "limits": context["spec"]["limits"],
        }
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _sha(stage / "RECEIPT.json"),
            "db_sha256": _sha(stage / "company.sqlite3"),
            "module_sha256": _sha(Path(__file__)),
            "native_version_count": 21,
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private_repository)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    root = prior._private(destination, directory=True)
    paths = {name: root / name for name in ("MANIFEST.json", "RECEIPT.json", "company.sqlite3")}
    if {child.name for child in root.iterdir()} != set(paths):
        raise CompanyStoreError("Exact three-file concern source required")
    frozen_paths = {
        "manifest": paths["MANIFEST.json"],
        "receipt": paths["RECEIPT.json"],
        "database": paths["company.sqlite3"],
    }
    before = prior._frozen(frozen_paths)
    context = _context(repository, private_repository)
    manifest = json.loads(paths["MANIFEST.json"].read_text())
    receipt = json.loads(paths["RECEIPT.json"].read_text())
    if manifest != {
        "schema": SCHEMA + "_MANIFEST",
        "receipt_sha256": _sha(paths["RECEIPT.json"]),
        "db_sha256": _sha(paths["company.sqlite3"]),
        "module_sha256": _sha(Path(__file__)),
        "native_version_count": 21,
        "audit_task_credit": False,
    }:
        raise CompanyStoreError("Concern manifest differs")
    expected = {
        "schema": SCHEMA,
        "company": COMPANY,
        "branches": BRANCHES,
        "records": receipt.get("records"),
        "spec_sha256": SPEC_SHA256,
        "reviewed_prd_source_sha256": UPSTREAM_HASHES,
        "upstream_original_refs": context["refs"],
        "native_version_counts": {"CLEAN": 8, "MESSY": 13},
        "selected_concern_count": 1,
        "selected_claimant_verified": False,
        "internal_draft_status": {"CLEAN": "HELD", "MESSY": "HELD_AFTER_CORRECTION"},
        "local_open_exception_counts": {"CLEAN": 0, "MESSY": 1},
        "real_external_messages_sent": 0,
        "fictional_accepted_deliveries": 0,
        "customer_acknowledgments": 0,
        "actual_phi_processing": False,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": context["spec"]["limits"],
    }
    if receipt != expected:
        raise CompanyStoreError("Concern receipt scope or qualification differs")
    with sqlite3.connect(
        paths["company.sqlite3"].as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Concern source database integrity differs")
        for table in ("grants", "collections", "access_events"):
            if db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]:
                raise CompanyStoreError("Concern source has audit access journal")
        systems = {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        }
        if systems != {
            (COMPANY, branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in SYSTEM_OWNERS.items()
        }:
            raise CompanyStoreError("Concern source systems differ")
        if db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != 21:
            raise CompanyStoreError("Concern native count differs")
        for side, branch in BRANCHES.items():
            rows = _rows(context, side)
            refs = receipt["records"][side]
            if len(refs) != len(rows):
                raise CompanyStoreError("Concern receipt branch count differs")
            for row, ref in zip(rows, refs, strict=True):
                native = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=1",
                    (COMPANY, branch, row["system"], row["record"]),
                ).fetchone()
                if native is None or native["content"] != row["content"]:
                    raise CompanyStoreError("Concern native bytes differ")
                if (
                    native["sha256"] != row["sha256"]
                    or native["event_at"] != row["event_at"]
                    or native["available_at"] != row["available_at"]
                    or native["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or native["command_id"] != f"PCI-{branch}-{row['record']}"
                    or json.loads(native["provenance"])
                    != {
                        "source_reference": SOURCE_REFERENCE,
                        "truth_class": "TRAINING_SCENARIO_ONLY",
                    }
                    or native["imported_at"] >= "2027-01-01"
                    or _time(native["imported_at"]) != native["imported_at"]
                    or ref != CompanyStore._metadata(native)
                ):
                    raise CompanyStoreError("Concern native clocks, provenance or receipt differ")
    if prior._frozen(frozen_paths) != before:
        raise CompanyStoreError("Concern source changed during verification")
    return {
        "status": "VERIFIED_FICTIONAL_SELECTED_PRD_CONCERN_HELD_NO_AUDIT_CREDIT",
        "native_version_counts": {"CLEAN": 8, "MESSY": 13},
        "audit_task_credit": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("destination", type=Path)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    args = parser.parse_args()
    command = create if args.action == "create" else verify
    print(
        json.dumps(
            command(
                args.destination,
                repository=args.repository,
                private_repository=args.private_repository,
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
