"""One selected fictional internal customer case remains uncredited and unsent."""

import copy
import json
import os
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_product_customer_internal_2027_simulation as prd
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


@pytest.fixture(scope="module")
def sealed(tmp_path_factory):
    parent = tmp_path_factory.mktemp("prd-private")
    os.chmod(parent, 0o700)
    root = parent / "run-v1"
    prd.create(root, repository=REPOSITORY, private_repository=PRIVATE)
    return root


def test_selected_internal_case_and_original_messy_omission(sealed):
    manifest = prd.verify(sealed, repository=REPOSITORY, private_repository=PRIVATE)
    receipt = json.loads((sealed / "RECEIPT.json").read_text())
    assert manifest["native_version_count"] == 15
    assert {side: len(rows) for side, rows in receipt["records"].items()} == {
        "CLEAN": 5,
        "MESSY": 10,
    }
    assert receipt["external_send_counts"] == {"CLEAN": 0, "MESSY": 0}
    assert receipt["internal_concern_counts"] == {"CLEAN": 0, "MESSY": 1}
    assert len(receipt["selected_generic_candidate_route_ids_per_side"]) == 9
    assert set(receipt["unsupported_authored_route_ids_per_side"]) == {
        f"TASK-{control}-corporate-ACTION-S-COMMUNICATION"
        for control in ("SH-PRD-002", "SH-PRD-003", "SH-PRD-004")
    }
    assert receipt["audit_task_credit"] is False
    with sqlite3.connect(sealed / "company.sqlite3") as db:
        rows = [
            (branch, system, record, version, event, available, imported, json.loads(body))
            for branch, system, record, version, event, available, imported, body in db.execute(
                "SELECT branch,system,record,version,event_at,available_at,imported_at,content "
                "FROM versions ORDER BY branch,event_at"
            )
        ]
    assert len(rows) == 15
    assert all(
        event < available and imported < event for _, _, _, _, event, available, imported, _ in rows
    )
    assert all(
        body["customer_id"] == prd.CUSTOMER
        and body["service_id"] == prd.SERVICE
        and body["real_external_message_sent"] is False
        and body["fictional_external_message_sent"] is False
        and body["audit_task_credit"] is False
        for *_, body in rows
    )
    impacts = [
        body
        for branch, system, _, _, _, _, _, body in rows
        if branch == "PRD-MESSY" and system == "impact_assessment"
    ]
    assert len(impacts) == 2
    assert impacts[0]["support_dependency_omitted"] is True
    assert prd.SUPPORT not in impacts[0]["internal_dependency_ids"]
    assert impacts[1]["original_impact_sha256"] == prd.sha(prd.encoded(impacts[0]))
    assert prd.SUPPORT in impacts[1]["internal_dependency_ids"]
    assert impacts[1]["historical_omission_not_retroactively_cured"] is True
    assert receipt["open_historical_exception_ids"]["MESSY"] == [prd.EXCEPTION]


def test_upstream_availability_and_frozen_sidecar_fail_closed(sealed, tmp_path):
    context = prd._context(REPOSITORY, PRIVATE)
    altered = copy.deepcopy(context)
    altered["provider"]["CLEAN"]["relationship_register", "REL-SUPPORT", 1]["ref"][
        "available_at"
    ] = "2027-10-01T00:00:00.000000+00:00"
    with pytest.raises(CompanyStoreError, match="predates an upstream"):
        prd._expected_rows(altered, "CLEAN")
    copied_root = tmp_path / "copy"
    os.mkdir(copied_root, 0o700)
    for name in ("MANIFEST.json", "RECEIPT.json", "company.sqlite3"):
        source = sealed / name
        dest = copied_root / name
        dest.write_bytes(source.read_bytes())
        os.chmod(dest, 0o600)
    (copied_root / "company.sqlite3-wal").symlink_to("missing")
    with pytest.raises(CompanyStoreError, match="sidecar"):
        prd.verify(copied_root, repository=REPOSITORY, private_repository=PRIVATE)


def test_canon_pin_drift_fails_before_source_generation(monkeypatch):
    altered = dict(prd.SOURCE_PINS)
    key = "docs/organization/source/chartbook.json"
    altered[key] = "0" * 64
    monkeypatch.setattr(prd, "SOURCE_PINS", altered)
    with pytest.raises(CompanyStoreError, match="Canon/role/term source pin"):
        prd._context(REPOSITORY, PRIVATE)
