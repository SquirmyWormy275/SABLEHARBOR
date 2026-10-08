"""Selected synthetic terms never imply legal acceptance or audit credit."""

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite.company_contract_obligation_triage import (
    _frozen,
    _routes,
    create,
    verify,
)
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


def _build(tmp_path):
    root = tmp_path / "triage"
    create(root, repository=REPOSITORY, private_repository=PRIVATE)
    return root


def test_selected_34_terms_and_exact_72_route_boundary(tmp_path):
    root = _build(tmp_path)
    assert (
        verify(root, repository=REPOSITORY, private_repository=PRIVATE)["native_version_count"] == 4
    )
    receipt = json.loads((root / "RECEIPT.json").read_text())
    assert {
        side: len(data["routes"])
        for side, data in receipt["separate_read_only_72_route_disposition"].items()
    } == {"A": 72, "B": 72}
    assert receipt["separate_read_only_72_route_disposition"]["A"]["counts"] == {
        "TERM_LEVEL_CANDIDATE_CONTEXT_ONLY": 3,
        "ROLE_CONTEXT_ONLY_NOT_TERM_LEVEL": 3,
        "UNSUPPORTED_NO_DIRECT_SOURCE": 66,
    }
    for scenario in ("CLEAN", "MESSY"):
        terms = receipt["selected_source_terms"][scenario]["term_occurrences"]
        assert len(terms) == 34
        assert len({term["occurrence_id"] for term in terms}) == 34
        assert {term["source_ref"]["record"] for term in terms} == {
            "BAA-CUST-01",
            "BAA-SUB-01",
            "CAL-RENO",
            "CAL-BOISE",
            "CAL-SUPPORT",
        }
    assert receipt["selected_source_terms"]["CLEAN"]["open_provider_exception_ref"] is None
    assert receipt["selected_source_terms"]["MESSY"]["open_provider_exception_ref"]["version"] == 2
    with sqlite3.connect(
        (root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM versions ORDER BY branch,event_at").fetchall()
        bodies = {(row["branch"], row["system"]): json.loads(row["content"]) for row in rows}
        assert len(rows) == 4
        assert all(row["imported_at"] < row["event_at"] == row["available_at"] for row in rows)
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0
    assert (
        bodies[("OBL-CLEAN", "owner_candidate_triage")]["owner_attests_selected_source_enumeration"]
        is True
    )
    assert bodies[("OBL-MESSY", "owner_candidate_triage")]["provider_support_omission_open"] is True
    assert all(
        body["qualified_counsel_provision_review"] == "PENDING"
        and body["statutory_applicability_decided"] is False
        and body["supplier_attestation"] == "NOT_REQUESTED_NOT_RECEIVED"
        and body["new_contract_executed"] is False
        and body["audit_collection"] is False
        and body["audit_task_credit"] is False
        for body in bodies.values()
    )


def test_frozen_original_rejects_sidecar(tmp_path):
    source = PRIVATE / (
        "enterprise/generated/audit-suite/company-provider-lifecycle-2026-09-29/"
        "run-v2/company.sqlite3"
    )
    clone = tmp_path / "company.sqlite3"
    shutil.copy2(source, clone)
    assert _frozen(clone)[-1] == hashlib.sha256(source.read_bytes()).hexdigest()
    sidecar = tmp_path / "company.sqlite3-wal"
    sidecar.write_bytes(b"uncheckpointed source")
    sidecar.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="active sidecar"):
        _frozen(clone)


def test_resealed_false_counsel_acceptance_rejected(tmp_path):
    root = _build(tmp_path)
    with sqlite3.connect(root / "company.sqlite3") as db:
        db.execute("DROP TRIGGER no_version_update")
        row = db.execute(
            "SELECT content FROM versions WHERE branch='OBL-MESSY' "
            "AND system='owner_candidate_triage'"
        ).fetchone()
        body = json.loads(row[0])
        body["qualified_counsel_provision_review"] = "APPROVED"
        body["statutory_applicability_decided"] = True
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(raw).hexdigest()
        db.execute(
            "UPDATE versions SET content=?,sha256=? WHERE branch='OBL-MESSY' "
            "AND system='owner_candidate_triage'",
            (raw, digest),
        )
    receipt = json.loads((root / "RECEIPT.json").read_text())
    for ref in receipt["records"]["MESSY"]:
        if ref["system"] == "owner_candidate_triage":
            ref["sha256"] = digest
    (root / "RECEIPT.json").write_text(json.dumps(receipt, sort_keys=True))
    manifest = json.loads((root / "MANIFEST.json").read_text())
    manifest["receipt_sha256"] = hashlib.sha256((root / "RECEIPT.json").read_bytes()).hexdigest()
    manifest["company_db_sha256"] = hashlib.sha256(
        (root / "company.sqlite3").read_bytes()
    ).hexdigest()
    (root / "MANIFEST.json").write_text(json.dumps(manifest, sort_keys=True))
    with pytest.raises(CompanyStoreError, match="content or future clock differs"):
        verify(root, repository=REPOSITORY, private_repository=PRIVATE)


def test_route_map_cannot_drop_unsupported_clause():
    route_map = json.loads(
        (
            REPOSITORY / ("enterprise/audit_suite/provider_ba_85_candidate_routes_v2.json")
        ).read_text()
    )
    assert len(_routes(route_map)["A"]["routes"]) == 72
    route_map["routes"] = [
        route
        for route in route_map["routes"]
        if route["task_id"] != "TASK-SH-LEG-001-corporate-ACTION-H-LEGAL-STATUS"
    ]
    with pytest.raises(CompanyStoreError, match="Exact 72"):
        _routes(route_map)
