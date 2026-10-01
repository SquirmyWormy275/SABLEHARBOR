"""Persistent fictional legal mailbox originals and company-owned exports.

The declared four-channel archive exists independently of engagements. Its
original messages corroborate prior intake summaries without altering them.
It does not establish completeness of unregistered channels or accept N/A.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import os
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from . import company_leg001_trigger_screening_2027 as intake
from .company_store import CompanyStore, CompanyStoreError, _time
from .documentary_283_route_reconciliation_v6 import _p1_inventory
from .operating_source_bridge import encoded
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_COMPANY_LEGAL_MESSAGE_ARCHIVE_2027_V1"
SOURCE = "enterprise/audit_suite/company_legal_message_archive_2027.py"
BASE = "enterprise/generated/audit-suite/company-leg001-trigger-screening-2027-2026-10-01"
PINS = {
    "main-run-v1/company.sqlite3": (
        "12553a5e6e1c9501b2ea5046ae2f18066b5f194ea546faba69947b2e9d09eee4"
    ),
    "main-run-v1/RECEIPT.json": "b87413c859ffad2c811437614b99124910b1e0a3189861874ef0bd51d7336846",
    "main-run-v1/MANIFEST.json": "9380291b87db722a6a8eab6e160d046b8c8f8ad0795a80284c66e3ea50eb16af",
    "independent-review-main-v1/REVIEW.json": (
        "842d04934e1996ff599406d57948ff39f37b11aa82db4c602425cef7c6b46ebe"
    ),
}
COMPANY = intake.COMPANY
BRANCHES = {"A": "MAIL-A", "B": "MAIL-B"}
OWNERS = {
    "legal_channel_configuration": "AS-P014",
    "legal_inbound_attachment": "AS-P014",
    "legal_inbound_message": "AS-P014",
    "legal_channel_export": "AS-P014",
    "legal_archive_reconciliation": "AS-P009",
}
QUERY = (
    "SELECT record,version,sha256,content FROM versions WHERE company=? AND branch=? "
    "AND system='legal_inbound_message' AND available_at<=? ORDER BY record,version"
)
TEXTS = {
    "INQ-PROVIDER-0907": (
        "We are reviewing the customer retention and return instructions for the recovery "
        "support workstream. Please identify the approved instructions and the handling of "
        "materials subject to a pending hold. This question does not instruct deletion or "
        "override the customer's directions. Please return the attached question list to "
        "the recovery-support contract manager.",
        "Question list: (1) Which customer instruction governs retention? "
        "(2) Who confirms return or continued hold? (3) Which recovery-support records "
        "must remain available while the instruction is pending?",
    ),
    "INQ-CUSTOMER-1020": (
        "Please confirm the current records-response service level for the shared runtime "
        "and identify the owner of an outstanding response. We need the agreed routing "
        "and response status; this inquiry does not change the service agreement. "
        "The attached worksheet lists our requested response fields.",
        "Response worksheet: accountable records owner; request receipt date; agreed "
        "service-level reference; current status; outstanding customer instruction.",
    ),
}


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read_only(path):
    db = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    return closing(db)


def _context(private_repository):
    private = Path(private_repository).resolve(strict=True)
    if _p1_inventory(private) != intake.overlay.P1_FREEZE:
        raise CompanyStoreError("Frozen P1 differs")
    paths = {name: private / BASE / name for name in PINS}
    before = {name: intake.docket._private(path) for name, path in paths.items()}
    if any(_sha(path) != PINS[name] for name, path in paths.items()):
        raise CompanyStoreError("Reviewed legal intake predecessor differs")
    review = json.loads(paths["independent-review-main-v1/REVIEW.json"].read_text())
    if review.get("verdict") != "PASS_BOUNDED_FICTIONAL_SOURCE_NO_AUDIT_CREDIT":
        raise CompanyStoreError("Legal intake predecessor not independently reviewed")
    result = {}
    with _read_only(paths["main-run-v1/company.sqlite3"]) as db:
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Predecessor integrity differs")
        for side, original_branch in zip("AB", intake.BRANCHES.values(), strict=True):
            rows = list(
                db.execute(
                    "SELECT * FROM versions WHERE branch=? AND system='intake_channel_ledger'",
                    (original_branch,),
                )
            )
            messages = {}
            for row in rows:
                body = json.loads(row["content"])
                for item in body["intake_items"]:
                    if item["item_id"] in messages:
                        raise CompanyStoreError("Ambiguous original inquiry")
                    messages[item["item_id"]] = {**item, "channel_id": body["channel_id"]}
            if len(rows) != 48 or set(messages) != set(TEXTS):
                raise CompanyStoreError("Declared channel/message population differs")
            result[side] = messages
    if any(intake.docket._private(path) != before[name] for name, path in paths.items()):
        raise CompanyStoreError("Predecessor mutated")
    return result


def _steps(messages):
    rows = []

    def add(system, record, at, body):
        rows.append((system, record, _time(at), {"schema": SCHEMA, "record_id": record, **body}))

    for channel in intake.CHANNELS:
        add(
            "legal_channel_configuration",
            channel,
            "2027-01-01T09:00:00+00:00",
            {
                "channel_id": channel,
                "custodian": "AS-P014",
                "legal_owner": "AS-P003",
                "retained_intake_registry_id": "REGISTRY-2027",
                "retained_originals": "MESSAGE_AND_ATTACHMENT_VERSIONS",
                "scope": intake.SCOPE,
                "unregistered_channels": "NOT_ESTABLISHED",
                "outside_mail_service": "NONE_LOCAL_FICTIONAL_ARCHIVE",
            },
        )
    for record, item in sorted(messages.items(), key=lambda pair: pair[1]["received_at"]):
        at = item["received_at"]
        attachment = "ATT-" + record
        attachment_body = {
            "schema": SCHEMA,
            "record_id": attachment,
            "channel_id": item["channel_id"],
            "inbound_message_id": record,
            "attachment_name": "contract-questions.txt",
            "attachment_kind": "CONTRACT_QUESTION_WORKSHEET",
            "text": TEXTS[record][1],
            "official_notice_or_case_identifier": None,
        }
        add("legal_inbound_attachment", attachment, at, attachment_body)
        add(
            "legal_inbound_message",
            record,
            at,
            {
                "channel_id": item["channel_id"],
                "received_at": _time(at),
                "sender_role": item["sender_role"],
                "sender_identity_kind": "FICTIONAL_CONTRACT_CORRESPONDENT",
                "subject": item["subject"],
                "text": TEXTS[record][0],
                "attachment_refs": [
                    {
                        "system": "legal_inbound_attachment",
                        "record": attachment,
                        "version": 1,
                        "sha256": hashlib.sha256(encoded(attachment_body)).hexdigest(),
                    }
                ],
                "actual_external_message": False,
            },
        )
    # These are retained company export records. The operation executes QUERY
    # against its own original archive before appending each export below.
    for month in range(1, 13):
        start = _time(f"2027-{month:02d}-01T00:00:00+00:00")
        last = f"2027-{month:02d}-{calendar.monthrange(2027, month)[1]:02d}"
        end = _time((datetime.fromisoformat(last) + timedelta(days=1)).isoformat() + "+00:00")
        at = _time(end.replace("T00:00:00.000000", "T09:00:00.000000"))
        for channel in intake.CHANNELS:
            selected = [
                record
                for record, item in messages.items()
                if item["channel_id"] == channel and start <= _time(item["received_at"]) < end
            ]
            add(
                "legal_channel_export",
                f"EXPORT-{month:02d}-{channel}",
                at,
                {
                    "channel_id": channel,
                    "event_window_start": start,
                    "event_window_end_exclusive": end,
                    "source_available_as_of": at,
                    "source_system": "legal_inbound_message",
                    "query": QUERY,
                    "event_filter": "received_at >= start AND received_at < end",
                    "declared_message_ids": sorted(selected),
                    "record_count": len(selected),
                    "operator": "AS-P014",
                    "registered_channels_only": True,
                },
            )
    add(
        "legal_archive_reconciliation",
        "ARCHIVE-2027",
        "2028-01-02T11:00:00+00:00",
        {
            "reviewed_by": "AS-P009",
            "operating_custodian": "AS-P014",
            "registered_channel_ids": list(intake.CHANNELS),
            "monthly_export_count": 48,
            "inbound_message_count": 2,
            "retained_attachment_count": 2,
            "retained_summary_item_ids": sorted(messages),
            "period_end_exclusive": "2028-01-01T00:00:00+00:00",
            "reconciliation": "EXACT_REGISTERED_ARCHIVE_AND_INTAKE_SUMMARY_IDS",
            "unregistered_channel_completeness": "NOT_ESTABLISHED",
            "regulator_case_classification": "REFER_TO_COUNSEL_RECORDS",
            "earlier_screening_and_exceptions_changed": False,
            "source_scope": intake.SCOPE,
        },
    )
    return rows


def _provenance():
    return {"source_reference": SOURCE, "truth_class": "AUTHORED_FICTIONAL_COMPANY_OPERATION"}


def _archive_query(db, branch, body):
    rows = db.execute(QUERY, (COMPANY, branch, body["source_available_as_of"]))
    return sorted(
        row["record"]
        for row in rows
        if (item := json.loads(row["content"]))["channel_id"] == body["channel_id"]
        and body["event_window_start"] <= item["received_at"] < body["event_window_end_exclusive"]
    )


def _write(path, value):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def create(destination, *, private_repository):
    destination = Path(destination).absolute()
    if destination.exists() or destination != destination.resolve():
        raise CompanyStoreError("Fresh ordinary private archive destination required")
    intake.docket._private(destination.parent, directory=True)
    context = _context(private_repository)
    with tempfile.TemporaryDirectory(prefix=".mail-archive-", dir=destination.parent) as temp:
        root = Path(temp)
        store = CompanyStore(root)
        records = {}
        for side, branch in BRANCHES.items():
            for system, owner in OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            records[side] = []
            for system, record, at, body in _steps(context[side]):
                if system == "legal_channel_export":
                    with _read_only(root / "company.sqlite3") as db:
                        if _archive_query(db, branch, body) != body["declared_message_ids"]:
                            raise CompanyStoreError("Actual company archive query differs")
                records[side].append(
                    store.append_version(
                        COMPANY,
                        branch,
                        system,
                        record,
                        expected_version=0,
                        command_id=f"MAIL-{branch}-{system}-{record}",
                        event_at=at,
                        available_at=at,
                        content=encoded(body),
                        provenance=_provenance(),
                    )
                )
        _write(
            root / "RECEIPT.json",
            {
                "schema": SCHEMA,
                "source_pins": {BASE + "/" + p: h for p, h in PINS.items()},
                "branches": BRANCHES,
                "records": records,
                "source_complete": False,
                "nonoccurrence_acceptance": False,
                "audit_task_credit": False,
                "outside_message_sent": False,
                "actual_phi": False,
            },
        )
        _write(
            root / "MANIFEST.json",
            {
                "schema": SCHEMA + "_MANIFEST",
                "module_sha256": _sha(Path(__file__)),
                "receipt_sha256": _sha(root / "RECEIPT.json"),
                "company_db_sha256": _sha(root / "company.sqlite3"),
                "native_versions": sum(len(rows) for rows in records.values()),
            },
        )
        verify(root, private_repository=private_repository)
        publish(root, destination)
    return verify(destination, private_repository=private_repository)


def verify(destination, *, private_repository):
    root = Path(destination).absolute()
    intake.docket._private(root, directory=True)
    if {p.name for p in root.iterdir()} != {"MANIFEST.json", "RECEIPT.json", "company.sqlite3"}:
        raise CompanyStoreError("Exact three-file private archive required")
    before = {p: intake.docket._private(p) for p in root.iterdir()}
    context = _context(private_repository)
    receipt = json.loads((root / "RECEIPT.json").read_text())
    expected_receipt = {
        "schema": SCHEMA,
        "source_pins": {BASE + "/" + p: h for p, h in PINS.items()},
        "branches": BRANCHES,
        "records": receipt.get("records"),
        "source_complete": False,
        "nonoccurrence_acceptance": False,
        "audit_task_credit": False,
        "outside_message_sent": False,
        "actual_phi": False,
    }
    if (
        receipt != expected_receipt
        or not isinstance(receipt.get("records"), dict)
        or set(receipt["records"]) != set(BRANCHES)
        or json.loads((root / "MANIFEST.json").read_text())
        != {
            "schema": SCHEMA + "_MANIFEST",
            "module_sha256": _sha(Path(__file__)),
            "receipt_sha256": _sha(root / "RECEIPT.json"),
            "company_db_sha256": _sha(root / "company.sqlite3"),
            "native_versions": sum(len(_steps(v)) for v in context.values()),
        }
    ):
        raise CompanyStoreError("Archive manifest/receipt scope differs")
    with _read_only(root / "company.sqlite3") as db:
        intake._trigger_schema(db)
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok" or any(
            db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ("grants", "collections", "access_events")
        ):
            raise CompanyStoreError("Archive integrity/access journal differs")
        if {tuple(r) for r in db.execute("SELECT company,branch,system,owner FROM systems")} != {
            (COMPANY, branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in OWNERS.items()
        }:
            raise CompanyStoreError("Archive system ownership differs")
        count = 0
        for side, branch in BRANCHES.items():
            refs = []
            for system, record, at, body in _steps(context[side]):
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=1",
                    (COMPANY, branch, system, record),
                ).fetchone()
                if (
                    row is None
                    or row["content"] != encoded(body)
                    or row["sha256"] != hashlib.sha256(row["content"]).hexdigest()
                    or row["event_at"] != at
                    or row["available_at"] != at
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or row["command_id"] != f"MAIL-{branch}-{system}-{record}"
                    or json.loads(row["provenance"]) != _provenance()
                    or _time(row["imported_at"]) != row["imported_at"]
                ):
                    raise CompanyStoreError("Archive original/version/provenance differs")
                if system == "legal_channel_export" and (
                    at <= body["event_window_end_exclusive"]
                    or _archive_query(db, branch, body) != body["declared_message_ids"]
                ):
                    raise CompanyStoreError("Archive window/query differs")
                refs.append(CompanyStore._metadata(row))
                count += 1
            if refs != receipt["records"][side]:
                raise CompanyStoreError("Archive custody receipt differs")
        if db.execute("SELECT count(*) FROM versions").fetchone()[0] != count:
            raise CompanyStoreError("Archive population differs")
    if any(intake.docket._private(p) != old for p, old in before.items()):
        raise CompanyStoreError("Archive verifier mutated originals")
    if _p1_inventory(Path(private_repository).resolve()) != intake.overlay.P1_FREEZE:
        raise CompanyStoreError("Frozen P1 changed")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("--private-repository", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    receipt = (create if args.action == "create" else verify)(
        args.destination, private_repository=args.private_repository
    )
    print(
        json.dumps({"schema": SCHEMA, "counts": {s: len(r) for s, r in receipt["records"].items()}})
    )


if __name__ == "__main__":
    main()
