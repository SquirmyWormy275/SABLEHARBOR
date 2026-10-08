"""Independent integrity and causal checks for the bounded company source."""

from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_workforce_identity_2027 as source
from enterprise.audit_suite.company_store import _json
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def candidate(tmp_path_factory):
    if not (PRIVATE / source.LEGACY).is_file():
        pytest.skip("Authorized private original mover input is unavailable")
    parent = tmp_path_factory.mktemp("workforce-native")
    parent.chmod(0o700)
    result = source.create(parent / "source", REPOSITORY, PRIVATE)
    root = parent / "source"
    return (
        root,
        result,
        source.native_records(root / "company/company.sqlite3"),
        source.canonical_basis(REPOSITORY),
        source.legacy_basis(PRIVATE),
    )


def record(rows, system, name=None, side="B", version=1):
    return next(
        r
        for r in rows
        if r["branch"] == source.BRANCHES[side]
        and r["system"] == system
        and (name is None or r["record"] == name)
        and r["version"] == version
    )


def sem(candidate, rows):
    root, _, _, basis, legacy = candidate
    return source.semantic_verify(rows, basis, legacy, root / "corporate-reference.txt")


def byte_copy(original, destination):
    destination.mkdir(mode=0o700)
    for p in original.rglob("*"):
        out = destination / p.relative_to(original)
        if p.is_dir():
            out.mkdir(mode=0o700)
        else:
            out.write_bytes(p.read_bytes())
            out.chmod(0o600)


def reseal(root):
    path = root / "MANIFEST.json"
    path.write_text(
        json.dumps(
            {"schema": source.SCHEMA, "files": source.private_inventory(root)},
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )
    path.chmod(0o600)


def mutate_unreferenced(root, system, name, change):
    """Alter actual database bytes, repair storage digest and outer file manifest."""
    path = root / "company/company.sqlite3"
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        row = dict(
            db.execute(
                "SELECT * FROM versions WHERE branch=? AND system=? AND record=? AND version=1",
                (source.BRANCHES["B"], system, name),
            ).fetchone()
        )
        body = json.loads(row["content"])
        change(body)
        content = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        checksum = hashlib.sha256(content).hexdigest()
        fingerprint = hashlib.sha256(
            _json(
                [
                    [row[k] for k in ("company", "branch", "system", "record")],
                    0,
                    row["event_at"],
                    row["available_at"],
                    row["origin"],
                    json.loads(row["provenance"]),
                    checksum,
                ]
            ).encode()
        ).hexdigest()
        trigger = db.execute(
            "SELECT sql FROM sqlite_master WHERE name='no_version_update'"
        ).fetchone()[0]
        db.execute("DROP TRIGGER no_version_update")
        db.execute(
            "UPDATE versions SET content=?,sha256=?,input_digest=? "
            "WHERE branch=? AND system=? AND record=? AND version=1",
            (content, checksum, fingerprint, source.BRANCHES["B"], system, name),
        )
        db.execute(trigger)
    reseal(root)


def test_actual_create_and_separate_verify(candidate):
    root, result, rows, _, _ = candidate
    assert source.verify(root) == result
    assert len(rows) == 3399
    assert result["summary"]["A"]["native_versions"] == 1695
    assert result["summary"]["B"]["native_versions"] == 1704


def test_canon_and_scoped_person_counts(candidate):
    _, _, rows, _, _ = candidate
    affiliates = [
        r["body"]
        for r in rows
        if r["system"] == "affiliation_register" and r["branch"] == source.BRANCHES["A"]
    ]
    assert len(affiliates) == 67
    assert sum(r["included_in_service_boundary"] for r in affiliates) == 57
    assert (
        record(rows, "affiliation_register", "P008")["body"]["included_in_service_boundary"]
        is False
    )
    assert (
        record(rows, "affiliation_register", "AS-P001")["body"]["included_in_service_boundary"]
        is False
    )
    assert (
        record(rows, "affiliation_register", "AS-P007")["body"]["source_status"]
        == "PROPOSED_OFFICE_OCCUPANT"
    )


def test_exact_closed_window_membership_and_history(candidate):
    _, _, rows, _, _ = candidate
    for side in source.BRANCHES:
        for quarter in range(1, 5):
            pop = record(rows, "periodic_review_population", f"2027-Q{quarter}", side)["body"]
            members = {r["subject_id"] for r in pop["members"]}
            assert ("P014" in members) == (side == "A")
            legacy = {r["person_id"] for r in pop["retained_local_privileged_population"]}
            assert ("P015" in legacy) == (quarter > 1)
            assert pop["retained_local_review_missing_ids"] == ([] if side == "A" else ["P014"])
    initial = source.instant("2027-12-31T09:00:00Z")
    for side in source.BRANCHES:
        q4 = record(rows, "periodic_review_population", "2027-Q4", side)
        assert source.instant(q4["available_at"]) > initial


def test_retained_approval_publication_and_restricted_lineage(candidate):
    root, _, rows, _, legacy = candidate
    for side in source.BRANCHES:
        for cause in ("MOVE-2027-Q1-001", "MOVE-2027-Q2-001"):
            row = record(rows, "duty_authorizations", cause, side)
            witness = row["body"]["original_source_witness"]
            assert source.instant(row["event_at"]).hour == 8
            assert source.instant(row["available_at"]).hour == 9
            assert source.instant(witness["available_at"]) <= source.instant(row["available_at"])
            assert "branch" not in witness
            assert witness["custody_status"] == "RESTRICTED_ARCHIVE_WITNESS_ONLY"
            assert sum(source.original_witness(original) == witness for original in legacy) == 1
    custody = json.loads((root / "ORIGINAL_CUSTODY.json").read_bytes())
    assert len(custody["records"]) == 64
    assert custody["admission_status"] == "RESTRICTED_NOT_PROJECTED_AUDITOR_ACCESS_NOT_ESTABLISHED"


def test_startup_gap_does_not_claim_whole_period_operations(candidate):
    root, _, rows, _, _ = candidate
    receipt = json.loads((root / "RECEIPT.json").read_bytes())
    assert receipt["whole_period_operations_established"] is False
    assert receipt["registered_account_first_issue_at"] == "2027-01-01T03:15:00Z"
    earliest = min(
        source.instant(r["event_at"])
        for r in rows
        if r["system"].startswith("account_") and r["body"] and "state" in r["body"]
    )
    assert earliest == source.instant(receipt["registered_account_first_issue_at"])


def test_permission_byte_mechanics(tmp_path):
    original = tmp_path / "object.txt"
    original.write_bytes(b"actual local original")
    runtime = source.LocalRuntime()
    runtime.install(
        "A",
        "worker",
        "local_account",
        ["read"],
        starts="2027-01-01T00:00:00Z",
        ends="2027-02-01T00:00:00Z",
    )
    allowed = runtime.read("A", "read", "2027-01-15T00:00:00Z", original)
    assert allowed["returned_sha256"] == source.sha(original)
    assert allowed["returned_bytes"] == len(original.read_bytes())
    assert runtime.read("A", "other", "2027-01-15T00:00:00Z", original)["returned_bytes"] == 0
    assert runtime.read("A", "read", "2027-02-01T00:00:00Z", original)["decision"] == "DENY"
    runtime.revoke("A")
    assert runtime.read("A", "read", "2027-01-15T00:00:00Z", original)["decision"] == "DENY"


def test_contract_expiry_and_credential_epoch_causes(candidate):
    _, _, rows, _, _ = candidate
    expiry = "SH-CW-001:application_session:EXPIRY"
    assert record(rows, "permission_activity", expiry, "A")["body"]["decision"] == "DENY"
    assert record(rows, "permission_activity", expiry, "B")["body"]["decision"] == "ALLOW"
    assert (
        record(rows, "permission_activity", "SH-CW-001:application_session:ACK")["body"]["decision"]
        == "DENY"
    )
    consumer = "SH-SVC-BACKUP:api_token:CONSUMER"
    assert record(rows, "permission_activity", consumer, "A")["body"]["decision"] == "ALLOW"
    assert record(rows, "permission_activity", consumer, "B")["body"]["decision"] == "DENY"
    assert (
        record(rows, "permission_activity", "SH-SVC-BACKUP:api_token:CORRECTION")["body"][
            "decision"
        ]
        == "ALLOW"
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "employee_count",
        "title",
        "proposed_hire",
        "self_approval",
        "wrong_provisioner",
        "overgrant",
        "unknown_actor",
        "future_reference",
        "reference_clock",
        "permission_flip",
        "permission_bytes",
        "stale_state",
        "monthly_member",
        "monthly_status",
        "quarter_member",
        "quarter_digest",
        "review_false_closure",
        "followup_false_closure",
        "historical_backfill",
        "late_reactivation",
        "late_review_replacement",
        "contract_term",
        "service_member",
        "answer_label",
        "future_ack",
        "truncated_month",
        "historical_definition",
        "mirrored_overgrant",
        "authority_window",
        "delegation_window",
        "original_scalar_future",
    ],
)
def test_semantics_reject_mutations(candidate, mutation):
    rows = copy.deepcopy(candidate[2])
    if mutation == "employee_count":
        record(rows, "affiliation_register", "P043")["body"]["source_status"] = "current_employee"
    elif mutation == "title":
        record(rows, "affiliation_register", "P014")["body"]["source_titles"][0]["title"] = (
            "Billing administrator"
        )
    elif mutation == "proposed_hire":
        record(rows, "affiliation_register", "AS-P007")["body"]["source_status"] = (
            "current_employee"
        )
    elif mutation == "self_approval":
        record(rows, "access_approvals", "P014")["body"]["approved_by"] = "AS-P006"
    elif mutation == "wrong_provisioner":
        record(rows, "access_approvals", "P014")["body"]["provisioner"] = "AS-P008"
    elif mutation == "overgrant":
        record(rows, "access_approvals", "P014")["body"]["approved_rights"].append("iam.approve")
    elif mutation == "unknown_actor":
        record(rows, "permission_activity")["body"]["performed_by"] = "UNKNOWN"
    elif mutation == "future_reference":
        record(rows, "access_approvals", "P014")["event_at"] = source._time("2026-01-01T00:00:00Z")
    elif mutation == "reference_clock":
        record(rows, "access_approvals", "P014")["body"]["request"]["available_at"] = source._time(
            "2026-01-01T00:00:00Z"
        )
    elif mutation == "permission_flip":
        record(rows, "permission_activity", "SH-CW-001:application_session:ACK")["body"][
            "decision"
        ] = "ALLOW"
    elif mutation == "permission_bytes":
        record(rows, "permission_activity")["body"]["returned_bytes"] += 1
    elif mutation == "stale_state":
        probe = record(rows, "permission_activity", "SH-CW-001:application_session:ACK")["body"]
        stale = record(
            rows, "account_application_session", "SH-CW-001:application_session", version=2
        )
        probe["account_state"] = {k: stale[k] for k in source.REFERENCE_KEYS}
    elif mutation == "monthly_member":
        record(rows, "denominator_snapshot", "2027-12")["body"]["registered_subject_ids"].remove(
            "P014"
        )
    elif mutation == "monthly_status":
        record(rows, "monthly_reconciliation", "2027-12")["body"]["status"] = (
            "REGISTERED_SCOPE_RECONCILED"
        )
    elif mutation == "quarter_member":
        record(rows, "periodic_review_population", "2027-Q2")["body"]["members"].pop()
    elif mutation == "quarter_digest":
        record(rows, "periodic_review_population", "2027-Q2")["body"]["membership_sha256"] = (
            "0" * 64
        )
    elif mutation == "review_false_closure":
        record(rows, "periodic_review_decisions", "2027-Q2")["body"]["review_status"] = (
            "REGISTERED_SCOPE_REVIEW_RECORDED"
        )
    elif mutation == "followup_false_closure":
        record(rows, "review_followup", "2027-Q2")["body"]["status"] = (
            "NO_ACTION_REQUIRED_FOR_REGISTERED_SCOPE"
        )
    elif mutation == "historical_backfill":
        record(rows, "periodic_review_population", "2027-Q2")["body"][
            "retained_local_review_missing_ids"
        ] = []
    elif mutation == "late_reactivation":
        record(rows, "account_legacy_application", "MOVE-2027-Q1-001:application", version=4)[
            "body"
        ]["state"]["active"] = True
    elif mutation == "late_review_replacement":
        record(rows, "late_correction", "MOVE-2027-Q1-001")["body"]["quarter_reviews_replaced"] = (
            True
        )
    elif mutation == "contract_term":
        record(rows, "contractor_relationship", "SH-CW-001")["body"]["ends"] = (
            "2028-01-01T00:00:00Z"
        )
    elif mutation == "service_member":
        record(rows, "nonhuman_inventory", "SH-SVC-BACKUP")["record"] = "FORECAST-SERVICE"
    elif mutation == "answer_label":
        record(rows, "company_authority")["body"]["false_clean"] = True
    elif mutation == "future_ack":
        record(rows, "account_application_session", "SH-CW-001:application_session", version=2)[
            "body"
        ]["invalidation_ack_at"] = "2027-06-30T13:00:00Z"
    elif mutation == "truncated_month":
        record(rows, "denominator_snapshot", "2027-12")["body"]["cutoff_exclusive"] = (
            "2027-12-31T09:00:00Z"
        )
    elif mutation == "historical_definition":
        record(rows, "entitlement_catalogue")["body"]["local_mover_duties"]["billing-admin"] = (
            "Bill-of-material workroom maintenance"
        )
    elif mutation == "mirrored_overgrant":
        record(rows, "access_requests", "P014")["body"]["requested_rights"] = [
            "iam.approve",
            "workspace.read",
        ]
        record(rows, "access_approvals", "P014")["body"]["approved_rights"] = [
            "iam.approve",
            "workspace.read",
        ]
    elif mutation == "authority_window":
        record(rows, "company_authority", "SERVICE-ORDER-2027")["body"]["effective_to"] = (
            "2027-01-01T00:45:00Z"
        )
    elif mutation == "delegation_window":
        record(rows, "service_delegation", "AS-P007")["body"]["effective_to"] = (
            "2029-01-01T00:00:00Z"
        )
    elif mutation == "original_scalar_future":
        row = record(rows, "duty_authorizations", "MOVE-2027-Q1-001")
        row["available_at"] = row["event_at"]
    with pytest.raises((ProcedureError, KeyError, ValueError)):
        sem(candidate, rows)


@pytest.mark.parametrize(
    "trigger",
    ["no_version_update", "no_version_delete", "no_collection_update", "no_collection_delete"],
)
def test_resealed_dropped_immutable_trigger(candidate, tmp_path, trigger):
    root = tmp_path / "copy"
    byte_copy(candidate[0], root)
    with sqlite3.connect(root / "company/company.sqlite3") as db:
        db.execute("DROP TRIGGER " + trigger)
    reseal(root)
    with pytest.raises(ProcedureError, match="immutable"):
        source.verify(root)


def mutate_source_metadata(root, mutation):
    with sqlite3.connect(root / "company/company.sqlite3") as db:
        db.row_factory = sqlite3.Row
        trigger = db.execute(
            "SELECT sql FROM sqlite_master WHERE name='no_version_update'"
        ).fetchone()[0]
        db.execute("DROP TRIGGER no_version_update")
        system = (
            "account_system_inventory"
            if mutation == "provenance_filename"
            else "duty_authorizations"
            if mutation == "original_scalar_future"
            else "workspace_object"
        )
        row = dict(
            db.execute(
                "SELECT * FROM versions WHERE branch=? AND system=? ORDER BY record LIMIT 1",
                (source.BRANCHES["A"], system),
            ).fetchone()
        )
        provenance = json.loads(row["provenance"])
        if mutation == "provenance_answer":
            provenance["expected_finding"] = "FALSE_CLEAN_EXPECTED"
        elif mutation == "provenance_filename":
            provenance["name"] = "EXPECTED_FALSE_CLEAN_ANSWER.json"
        elif mutation == "original_scalar_future":
            row["available_at"] = row["event_at"]
        else:
            provenance["name"] = "object.json"
        fingerprint = hashlib.sha256(
            _json(
                [
                    [row[k] for k in ("company", "branch", "system", "record")],
                    row["version"] - 1,
                    row["event_at"],
                    row["available_at"],
                    row["origin"],
                    provenance,
                    row["sha256"],
                ]
            ).encode()
        ).hexdigest()
        db.execute(
            "UPDATE versions SET provenance=?,available_at=?,input_digest=? "
            "WHERE branch=? AND system=? AND record=? AND version=?",
            (
                _json(provenance),
                row["available_at"],
                fingerprint,
                row["branch"],
                system,
                row["record"],
                row["version"],
            ),
        )
        db.execute(trigger)
    reseal(root)


@pytest.mark.parametrize(
    "mutation",
    [
        "owner",
        "journal",
        "schema",
        "typed_object",
        "import_clock",
        "open_followup",
        "permission",
        "provenance_answer",
        "provenance_filename",
        "receipt_extra",
        "manifest_extra",
        "original_scalar_future",
        "receipt_limits",
    ],
)
def test_actual_resealed_source_rejections(candidate, tmp_path, mutation):
    root = tmp_path / "copy"
    byte_copy(candidate[0], root)
    if mutation in {"receipt_extra", "receipt_limits"}:
        path = root / "RECEIPT.json"
        d = json.loads(path.read_bytes())
        if mutation == "receipt_extra":
            d["additional_branches"] = {"C": "COMPLETE_AND_ACCEPTED"}
        else:
            d["limitations"] = []
        path.write_text(json.dumps(d))
        reseal(root)
    elif mutation == "manifest_extra":
        path = root / "MANIFEST.json"
        d = json.loads(path.read_bytes())
        d["additional_branches"] = {"C": "COMPLETE_AND_ACCEPTED"}
        path.write_text(json.dumps(d))
    elif mutation == "open_followup":
        mutate_unreferenced(
            root,
            "review_followup",
            "2027-Q2",
            lambda d: d.update(status="NO_ACTION_REQUIRED_FOR_REGISTERED_SCOPE"),
        )
    elif mutation == "permission":
        mutate_unreferenced(
            root,
            "permission_activity",
            "SH-CW-001:application_session:ACK",
            lambda d: d.update(
                decision="ALLOW",
                returned_bytes=len((root / "corporate-reference.txt").read_bytes()),
                returned_sha256=source.sha(root / "corporate-reference.txt"),
            ),
        )
    elif mutation in {
        "typed_object",
        "provenance_answer",
        "provenance_filename",
        "original_scalar_future",
    }:
        mutate_source_metadata(root, mutation)
    else:
        with sqlite3.connect(root / "company/company.sqlite3") as db:
            if mutation == "owner":
                db.execute("UPDATE systems SET owner='P001' WHERE system='account_directory'")
            elif mutation == "journal":
                db.execute(
                    "INSERT INTO grants VALUES('reader','engagement',?,?,?,1)",
                    (source.COMPANY, source.BRANCHES["A"], "account_directory"),
                )
            elif mutation == "schema":
                db.execute("CREATE TABLE engagement(id TEXT)")
            else:
                trigger = db.execute(
                    "SELECT sql FROM sqlite_master WHERE name='no_version_update'"
                ).fetchone()[0]
                db.execute("DROP TRIGGER no_version_update")
                db.execute(
                    "UPDATE versions SET imported_at='2027-01-01T00:00:00.000000+00:00' "
                    "WHERE system='workspace_object'"
                )
                db.execute(trigger)
        reseal(root)
    with pytest.raises(ProcedureError):
        source.verify(root)


def test_private_modes_alias_and_unknown_files(candidate, tmp_path):
    root = tmp_path / "copy"
    byte_copy(candidate[0], root)
    (root / "corporate-reference.txt").chmod(0o644)
    with pytest.raises(ProcedureError, match="Private"):
        source.verify(root)
    (root / "corporate-reference.txt").chmod(0o600)
    (root / "extra.json").write_bytes(b"{}")
    (root / "extra.json").chmod(0o600)
    reseal(root)
    with pytest.raises(ProcedureError, match="roster"):
        source.verify(root)
