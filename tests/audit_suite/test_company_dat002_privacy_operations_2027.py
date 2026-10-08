"""Privacy source custody, legal distinctions, and causal mutation rejection."""

import hashlib
import json
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import company_dat002_privacy_operations_2027 as privacy
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def context():
    return privacy._context(REPOSITORY, PRIVATE)


def _record(rows, name, version=1):
    return next(r for r in rows if r["record"] == name and r["version"] == version)


def _rehash(row):
    row["sha256"] = sha(encoded(row["body"]))


def test_exact_thirteen_unrun_routes_and_all_substantive_locator_maps(context):
    assert len(privacy.TARGET_TASKS) == len(set(privacy.TARGET_TASKS)) == 13
    for scenario, count in (("CLEAN", 133), ("MESSY", 136)):
        rows = privacy._expected_rows(context, scenario)
        assert len(rows) == count
        refs = [
            {
                "company": privacy.COMPANY,
                "branch": privacy.BRANCHES[scenario],
                "imported_at": "2026-10-01T00:00:00+00:00",
                **{
                    k: r[k]
                    for k in ("system", "record", "version", "sha256", "event_at", "available_at")
                },
            }
            for r in rows
        ]
        leads = privacy._lead_map(rows, refs)
        assert set(leads) == set(privacy.TARGET_TASKS)
        assert all(len(locators) >= 3 for locators in leads.values())
        if scenario == "MESSY":
            configs = leads["TASK-SH-DAT-002-corporate-CHECK-HIPAA:164.522"]
            assert {r["version"] for r in configs if r["record"] == "CONFIG-01"} == {1, 2}


def test_customer_roles_do_not_promote_old_held_marker_cases(context):
    for scenario in privacy.BRANCHES:
        rows = privacy._expected_rows(context, scenario)
        schedule = _record(rows, "SCHEDULE-01")["body"]
        assert schedule["effective_at"] == privacy.PERIOD["start"]
        assert schedule["applies_only_to_dataset"] != privacy.purpose.DATASET
        assert schedule["prior_marker_remains_outside_schedule"] == privacy.purpose.MARKER
        assert schedule["not_a_cure_for_prior_flowdown_exception"] is True
        assert schedule["real_signature_or_agreement"] is False
        assert _record(rows, "INVENTORY-01")["body"]["enterprise_location_roster_complete"] is False
        assert rows[-1]["body"]["old_held_rights_case_status"] == "HELD_OPEN"
        assert rows[-1]["body"]["prior_scope_exception_closed"] is False
        assert all("scenario" not in r["body"] for r in rows)
        assert all("task_credit" not in r["body"] for r in rows)
    changed = deepcopy(context)
    changed["rights"]["MESSY"][-1]["body"]["selected_case_status"] = "CLOSED"
    with pytest.raises(CompanyStoreError, match="Prior rights hold"):
        privacy._expected_rows(changed, "MESSY")


def test_legal_gate_cases_retain_customer_and_counsel_distinctions(context):
    rows = privacy._expected_rows(context, "CLEAN")
    for cid in (
        "AUTH-02",
        "AUTH-03",
        "AUTH-04",
        "AUTH-PSY",
        "AUTH-MKT",
        "AUTH-SALE",
        "FAMILY-01",
        "JUDICIAL-02",
        "JUDICIAL-03",
        "DEID-01",
        "DEID-02",
        "MINIMUM-01",
        "RESTRICT-01",
        "RESTRICT-03",
    ):
        assert _record(rows, f"GATE-{cid}")["body"]["decision"] == "HOLD"
        assert _record(rows, f"EXEC-{cid}")["body"]["execution_status"] == "WITHHELD"
    valid = _record(rows, "REQ-AUTH-01")["body"]["request_facts"]
    assert valid["customer_copy_provided"] is True
    assert valid["signature_date"] < valid["expiration_at"]
    emergency = _record(rows, "DEC-FAMILY-02")["body"]
    assert emergency["customer_decision_actor"] == "SIM-CUST-CLINICIAN-01"
    assert emergency["scope"] == ["CARE_COORDINATION_TOKEN"]
    assert (
        _record(rows, "GATE-JUDICIAL-03")["body"]["legal_status_overlay"] == "PENDING_PERIOD_REVIEW"
    )
    safe = _record(rows, "REQ-DEID-03")["body"]["request_facts"]
    assert len(safe["removal_screen"]) == 18
    assert safe["reidentification_mechanism_released"] is False
    assert _record(rows, "REQ-LDS-01")["body"]["request_facts"]["deidentified_claim"] is False
    assert _record(rows, "GATE-RESTRICT-02")["body"]["decision"] == "PERMIT"
    assert (
        _record(rows, "REQ-RESTRICT-03")["body"]["request_facts"]["solely_paid_in_full_item"]
        is True
    )
    assert _record(rows, "REQ-CONTACT-01")["body"]["request_facts"]["explanation_demanded"] is False


def test_messy_authority_mismatch_stems_from_prior_operating_configuration(context):
    clean = privacy._expected_rows(context, "CLEAN")
    messy = privacy._expected_rows(context, "MESSY")
    conf = _record(messy, "CONFIG-01")["body"]
    revoke = _record(messy, "REQ-AUTH-03")["body"]["request_facts"]
    assert conf["revocation_cache_refreshed_at"] < revoke["revoked_at"]
    assert "PAID_IN_FULL_RESTRICTION" not in conf["restriction_keys"]
    for cid in ("AUTH-03", "RESTRICT-03"):
        assert _record(messy, f"GATE-{cid}")["body"]["decision"] == "HOLD"
        assert _record(messy, f"EXEC-{cid}")["body"]["execution_status"] == "DELIVERED"
        assert _record(clean, f"EXEC-{cid}")["body"]["execution_status"] == "WITHHELD"
    incident = _record(messy, "EXCEPTION-01")["body"]
    assert incident["status"] == "OPEN"
    assert incident["recipient_return_attestation"] == "PENDING"
    assert (
        _record(messy, "CONFIG-01", 2)["body"]["supersedes"]["sha256"]
        == _record(messy, "CONFIG-01")["sha256"]
    )
    assert _record(messy, "CONFIG-01", 2)["body"]["repaired_configuration_accepted"] is False
    assert messy[-1]["body"]["delivered_count"] == clean[-1]["body"]["delivered_count"] + 2


def test_rehashed_cross_branch_or_unavailable_dependency_and_answer_leak_rejected(context):
    for mutation in ("branch", "clock", "answer"):
        rows = deepcopy(privacy._expected_rows(context, "CLEAN"))
        row = _record(rows, "AP-LEGAL-01")
        if mutation == "branch":
            row["body"]["dependencies"][0]["branch"] = privacy.BRANCHES["MESSY"]
        elif mutation == "clock":
            row["body"]["dependencies"][0]["available_at"] = row["event_at"]
        else:
            row["body"]["expected_finding"] = "PASS"
        _rehash(row)
        with pytest.raises(CompanyStoreError, match="dependency|learner-answer"):
            privacy._validate_history(rows, "CLEAN")
    rows = deepcopy(privacy._expected_rows(context, "MESSY"))
    rows[-1]["body"]["delivered_count"] -= 2
    _rehash(rows[-1])
    with pytest.raises(CompanyStoreError, match="period reconciliation"):
        privacy._validate_history(rows, "MESSY")


def test_create_verify_private_source_roster_and_repinned_claim_mutation(
    tmp_path, context, monkeypatch
):
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    monkeypatch.setattr(privacy, "_context", lambda *_: context)
    root = parent / "run"
    privacy.create(root, repository=REPOSITORY, private_repository=PRIVATE)
    result = privacy.verify(root, repository=REPOSITORY, private_repository=PRIVATE)
    assert result["native_version_count"] == 269
    for path in root.iterdir():
        assert path.stat().st_mode & 0o077 == 0
        assert path.stat().st_nlink == 1
    receipt = root / "RECEIPT.json"
    body = json.loads(receipt.read_text())
    body["audit_task_credit"] = True
    receipt.write_text(json.dumps(body))
    manifest = root / "MANIFEST.json"
    body = json.loads(manifest.read_text())
    body["receipt_sha256"] = hashlib.sha256(receipt.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(body))
    with pytest.raises(CompanyStoreError, match="manifest/receipt boundary"):
        privacy.verify(root, repository=REPOSITORY, private_repository=PRIVATE)


def test_repinned_native_payload_mutation_is_rejected(tmp_path, context, monkeypatch):
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    monkeypatch.setattr(privacy, "_context", lambda *_: context)
    root = parent / "run"
    privacy.create(root, repository=REPOSITORY, private_repository=PRIVATE)
    dbpath = root / "company.sqlite3"
    with sqlite3.connect(dbpath) as db:
        db.execute("DROP TRIGGER no_version_update")
        content = db.execute(
            "SELECT content FROM versions WHERE branch=? AND record=? AND version=1",
            (privacy.BRANCHES["CLEAN"], "CONFIG-01"),
        ).fetchone()[0]
        body = json.loads(content)
        body["default_release"] = "ALLOW"
        db.execute(
            "UPDATE versions SET content=?,sha256=? WHERE branch=? AND record=? AND version=1",
            (encoded(body), sha(encoded(body)), privacy.BRANCHES["CLEAN"], "CONFIG-01"),
        )
        db.execute(
            "CREATE TRIGGER no_version_update BEFORE UPDATE ON versions "
            "BEGIN SELECT RAISE(ABORT,'Immutable source'); END"
        )
    manifest = root / "MANIFEST.json"
    body = json.loads(manifest.read_text())
    body["company_db_sha256"] = hashlib.sha256(dbpath.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(body))
    with pytest.raises(CompanyStoreError, match="native original"):
        privacy.verify(root, repository=REPOSITORY, private_repository=PRIVATE)


def test_unknown_branch_and_partial_pinned_hash_rejected(context, monkeypatch):
    with pytest.raises(CompanyStoreError, match="Unknown privacy branch"):
        privacy._expected_rows(context, "UNKNOWN")
    pins = dict(privacy.SOURCE_PINS)
    key = next(iter(pins))
    pins[key] = pins[key][:12]
    monkeypatch.setattr(privacy, "SOURCE_PINS", pins)
    with pytest.raises(CompanyStoreError, match="Pinned DAT002 privacy"):
        privacy._context(REPOSITORY, PRIVATE)


@pytest.mark.parametrize(
    "trigger",
    ["no_version_update", "no_version_delete", "no_collection_update", "no_collection_delete"],
)
def test_resealed_drop_of_any_immutable_trigger_rejected(tmp_path, context, monkeypatch, trigger):
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    monkeypatch.setattr(privacy, "_context", lambda *_: context)
    root = parent / "run"
    privacy.create(root, repository=REPOSITORY, private_repository=PRIVATE)
    dbpath = root / "company.sqlite3"
    with sqlite3.connect(dbpath) as db:
        db.execute(f"DROP TRIGGER {trigger}")
    manifest = root / "MANIFEST.json"
    body = json.loads(manifest.read_text())
    body["company_db_sha256"] = hashlib.sha256(dbpath.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(body))
    with pytest.raises(CompanyStoreError, match="immutable-source triggers"):
        privacy.verify(root, repository=REPOSITORY, private_repository=PRIVATE)


def test_resealed_noop_trigger_with_original_name_rejected(tmp_path, context, monkeypatch):
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    monkeypatch.setattr(privacy, "_context", lambda *_: context)
    root = parent / "run"
    privacy.create(root, repository=REPOSITORY, private_repository=PRIVATE)
    dbpath = root / "company.sqlite3"
    with sqlite3.connect(dbpath) as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute("CREATE TRIGGER no_version_update BEFORE UPDATE ON versions BEGIN SELECT 1; END")
    manifest = root / "MANIFEST.json"
    body = json.loads(manifest.read_text())
    body["company_db_sha256"] = hashlib.sha256(dbpath.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(body))
    with pytest.raises(CompanyStoreError, match="immutable-source triggers"):
        privacy.verify(root, repository=REPOSITORY, private_repository=PRIVATE)
