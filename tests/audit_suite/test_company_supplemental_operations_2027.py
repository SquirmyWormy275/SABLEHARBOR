"""Adversarial checks for source mechanics and preserved training-world history."""

import hashlib
import hmac
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from enterprise.audit_suite import company_supplemental_operations_2027 as source
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]


def test_retention_uses_later_date_and_protects_current_hold_and_boundary():
    result = source.retention_decision(
        "2027-08-24", "2027-11-01", current=False, requested="2033-08-25"
    )
    assert result["minimum_retain_through"] == "2033-11-01"
    assert result["decision"] == "DENY"
    assert (
        source.retention_decision(
            "2027-08-24", "2027-11-01", current=False, requested="2033-11-01"
        )["decision"]
        == "DENY"
    )
    assert (
        source.retention_decision(
            "2027-08-24", "2027-11-01", current=False, requested="2033-11-02"
        )["decision"]
        == "ELIGIBLE_FOR_SEPARATE_APPROVAL"
    )
    assert (
        source.retention_decision("2027-11-01", None, current=True, requested="2040-01-01")[
            "decision"
        ]
        == "DENY"
    )
    assert (
        source.retention_decision(
            "2027-11-01", None, current=False, requested="2040-01-01", held=True
        )["decision"]
        == "DENY"
    )
    assert (
        source.retention_decision("2028-02-29", None, current=False, requested="2034-02-28")[
            "minimum_retain_through"
        ]
        == "2034-02-28"
    )
    with pytest.raises(CompanyStoreError, match="predates"):
        source.retention_decision("2027-08-24", "2026-01-01", current=False, requested="2040-01-01")


def test_semantic_validity_does_not_authorize_receiving_or_transfer_change():
    fixtures = source.fixture_material()
    original, changed, key = (
        fixtures[x] for x in ("marker-original.json", "marker-altered.json", "verifier-key.bin")
    )
    expected = hmac.new(key, original, hashlib.sha256).hexdigest()
    rejected = source.integrity_trial(original, changed, key, expected)
    assert rejected["semantic_valid"] is True
    assert rejected["content_authentic"] is False
    assert rejected["handling"] == "QUARANTINE"
    assert (
        source.integrity_trial(original, changed, key, expected, semantic_only=True)["handling"]
        == "ACCEPT"
    )
    assert source.integrity_trial(original, original, key, expected)["handling"] == "ACCEPT"
    with pytest.raises(CompanyStoreError, match="preserved original"):
        source.integrity_trial(
            original, changed, key, hmac.new(key, changed, hashlib.sha256).hexdigest()
        )


def test_resource_and_privilege_are_not_authorized_by_a_nonempty_approval_string():
    policy = source._policy()
    request = {
        "principal": "AS-P007",
        "issuer": policy["issuer"],
        "audience": policy["audience"],
        "expires_at": "2027-09-07T09:15:00+00:00",
        "resource": "marker-store",
        "operation": "read",
        "mfa": True,
        "privileged": True,
        "approval": "FORGED-APPROVAL",
    }
    assert (
        source.access_decision(request, policy, at="2027-09-07T09:01:00+00:00")["decision"]
        == "DENY"
    )
    request["approval"] = "AS-P008-SUP-ELEVATION-01"
    assert (
        source.access_decision(request, policy, at="2027-09-07T09:01:00+00:00")["decision"]
        == "ALLOW"
    )
    request["resource"] = "marker-recovery"
    assert (
        "PRIVILEGE_APPROVAL_SCOPE_MISMATCH"
        in source.access_decision(request, policy, at="2027-09-07T09:01:00+00:00")["reasons"]
    )
    request.update(resource="marker-store", mfa="false")
    assert (
        "MFA_REQUIRED"
        in source.access_decision(request, policy, at="2027-09-07T09:01:00+00:00")["reasons"]
    )
    request.update(principal="SIM-SERVICE-RECOVERY-01", privileged=False, mfa=True)
    assert (
        "RESOURCE_PERMISSION_DENIED"
        in source.access_decision(request, policy, at="2027-09-07T09:01:00+00:00")["reasons"]
    )
    assert (
        "EXPIRED_CREDENTIAL"
        in source.access_decision(request, policy, at="2027-09-07T09:15:00+00:00")["reasons"]
    )


def test_exact_copy_and_disposable_reuse_preserve_original_and_reject_alias(tmp_path):
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir(mode=0o700)
    original = fixtures / "marker-original.json"
    source._write(original, source.fixture_material()["marker-original.json"])
    original_pin = source.private_file(original)
    working = fixtures / "reused-media.bin"
    result = source.exact_marker_copy(original, working)
    assert result["ordinary_independent_copy"] is True
    assert working.stat().st_ino != original.stat().st_ino
    cleared = source.sanitize_test_media(working, original_pin[-1])
    assert cleared["after_size"] == 0
    assert source.private_file(original) == original_pin
    with pytest.raises(CompanyStoreError, match="disposable"):
        source.sanitize_test_media(original, original_pin[-1])
    linked = fixtures / "linked-marker.json"
    os.link(original, linked)
    with pytest.raises(CompanyStoreError, match="single-link"):
        source.exact_marker_copy(linked, fixtures / "forbidden-copy.json")


def _fake_context():
    spec = json.loads((REPOSITORY / source.SPEC).read_bytes())
    originals = {}
    requirements = {
        "policy": [("policy_baseline", "BASELINE")],
        "procedure": [("result_register", "FINAL")],
        "conduct": [("conduct_code", "FICTIONAL-LOCAL-APPROVAL")],
        "phi": [("contract_register", "BAA-CUST-01"), ("contract_register", "BAA-SUB-01")],
        "addressable": [("addressable_candidate", f"SPEC-{i:02d}") for i in range(1, 23)],
        "physical": [("site_zoning", "RNO-CAGE-A"), ("site_zoning", "BOI-CAGE-R")],
        "transfer": [("security_path", "TEST-PREDECESSOR")],
        "rights": [("authority_review", "TEST-PREDECESSOR")],
        "retention": [("hold_marker", "TEST-PREDECESSOR")],
        "integrity": [("integrity_check", "TEST-PREDECESSOR")],
    }
    for family, records in requirements.items():
        originals[family] = {}
        for side in "AB":
            originals[family][side] = {}
            for system, record in records:
                row = {
                    "company": source.COMPANY,
                    "branch": f"TEST-PREDECESSOR-{side}",
                    "system": system,
                    "record": record,
                    "version": 1,
                    "event_at": "2027-01-01T00:00:00.000000+00:00",
                    "available_at": "2027-01-01T00:01:00.000000+00:00",
                    "imported_at": "2026-10-01T00:00:00.000000+00:00",
                    "sha256": "a" * 64,
                }
                originals[family][side][source._key(row)] = row
    matrix = json.loads((REPOSITORY / source.ROUTE).read_bytes())
    return {
        "spec": spec,
        "canon": {},
        "stamps": {},
        "originals": originals,
        "routes": {
            side: [
                r
                for r in matrix["rows"]
                if r["side"] == side and r["task_id"] in source.TASK_SYSTEMS
            ]
            for side in "AB"
        },
    }


@pytest.fixture
def native_run(tmp_path, monkeypatch):
    tmp_path.chmod(0o700)
    monkeypatch.setattr(source, "_context", lambda repository, private: _fake_context())
    monkeypatch.setattr(source, "_p1_inventory", lambda private: source.P1_FREEZE)
    run = tmp_path / "run"
    source.create(run, repository=REPOSITORY, private_repository=tmp_path)
    return run


def _bodies(run, side):
    with closing(
        sqlite3.connect((run / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        return {
            (system, record, version): json.loads(content)
            for system, record, version, content in db.execute(
                "SELECT system,record,version,content FROM versions WHERE branch=?",
                (source.BRANCHES[side],),
            )
        }


def test_later_operations_leave_old_scope_and_lapses_visible(native_run, tmp_path):
    a, b = _bodies(native_run, "A"), _bodies(native_run, "B")
    for bodies in [a, b]:
        decisions = [
            v
            for (system, record, _), v in bodies.items()
            if system == "risk_decision" and record.startswith("ENVIRONMENT-DECISION-")
        ]
        assert len(decisions) == 22
        assert len({d["specification"] for d in decisions}) == 22
        assert all(
            set(d["assessment"])
            == {
                "size_complexity_capability",
                "infrastructure",
                "cost",
                "probability_and_criticality",
            }
            for d in decisions
        )
        assert bodies[("policy_document", "SUP-OPERATING-POLICY-2027", 1)][
            "relationship_to_prior_policy"
        ].startswith("Separate local supplement")
        calendar = bodies[("procedure_calendar", "2027-REVIEW-DUE-REGISTER", 1)]
        assert len(calendar["scheduled"]) == 4
        assert calendar["not_scheduled_interval"]["end"] == "2027-08-24"
        closure = bodies[("period_register", "2027-LOCAL-CHANNEL-CLOSURE", 1)]
        assert closure["event_at"].startswith("2028-01-02")
        assert closure["monthly_status"][0]["local_supplement_status"] == "NOT_EFFECTIVE"
        privacy = bodies[("privacy_responsibility", "CUSTOMER-OBLIGATION-BOUNDARY", 1)]
        assert "Customer" not in privacy["business_role"]
        assert len(privacy["covered_customer_retains"]) == 4
        assert "not a decision" in privacy["security_vs_individual_access"]
    assert len(a[("procedure_operation", "REVIEW-2027-10", 1)]["required_original_retrieval"]) == 24
    assert b[("procedure_operation", "REVIEW-2027-10", 1)]["required_original_retrieval"] == []
    assert (
        b[("procedure_operation", "OCTOBER-RETRIEVAL-CORRECTION", 1)]["late_original_requirement"]
        is True
    )
    assert b[("integrity_operation", "RECEIVING-COPY-ALTERATION", 1)]["handling"] == "ACCEPT"
    assert b[("integrity_operation", "AUTHENTICITY-RETEST", 1)]["handling"] == "QUARANTINE"
    assert (
        b[("security_configuration", "SETTING-20-CONTENT_AUTHENTICITY", 1)]["observed_values"][
            "configured_validator"
        ]
        == "SEMANTIC_ONLY"
    )
    assert (
        b[("security_configuration", "SETTING-20-CONTENT_AUTHENTICITY", 2)]["configured_validator"]
        == "SEMANTIC_AND_CONTENT_AUTHENTICITY"
    )
    assert (
        b[("workforce_case", "ER-2027-PROTECTED-REPORT-REVIEW", 1)]["decision"]
        == "REJECT_ADVERSE_ACTION"
    )
    assert (
        b[("workforce_case", "ER-2027-CORRECTIVE-DECISION", 1)]["reporter_adverse_action"] is False
    )
    assert (
        b[("workforce_case", "ER-2027-FOLLOWUP", 1)]["case_status"]
        == "ACTIONS_COMPLETED_LATE_EFFECTIVENESS_REVIEW_OPEN"
    )
    assert b[("media_movement", "MOVEMENT-RELEASE-ATTEMPT-01", 1)]["actual_departure"] is False
    for bodies in [a, b]:
        assert bodies[("access_operation", "CORRECTIVE-RESTRICTION-SELF", 1)]["decision"] == "DENY"
        assert bodies[("access_operation", "CORRECTIVE-RESTRICTION-PEER", 1)]["decision"] == "ALLOW"
        restriction = bodies[("identity_permission", "MARKER-SERVICE-PERMISSION-MATRIX", 2)]
        assert restriction["reporter_permission_unchanged"] == "AS-P013"
    for side in "AB":
        for body in _bodies(native_run, side).values():
            raw = json.dumps(body)
            assert "TASK-SH-" not in raw
            assert '"audit_task_credit"' not in raw
            assert '"expected_answer"' not in raw
    checked = source.verify(native_run, repository=REPOSITORY, private_repository=tmp_path)
    assert checked["audit_task_credit"] is False
    assert checked["source_complete"] is False
    assert checked["route_locator_count_per_side"] == 12


def test_discovery_cannot_see_january_closure_at_december_fieldwork(native_run):
    # Grant only in a disposable ordinary-byte copy, never the sealed source output.
    copy = native_run.parent / "discovery-copy"
    copy.mkdir(mode=0o700)
    source._write(copy / "company.sqlite3", (native_run / "company.sqlite3").read_bytes())
    store = CompanyStore(copy)
    store.grant(
        "TEST-AUDITOR", "TEST-ENGAGEMENT", source.COMPANY, source.BRANCHES["A"], "period_register"
    )
    old = store.list_records(
        "TEST-AUDITOR",
        "TEST-ENGAGEMENT",
        source.COMPANY,
        source.BRANCHES["A"],
        "period_register",
        as_of="2027-12-31T09:00:00+00:00",
    )
    assert old["records"] == []
    new = store.list_records(
        "TEST-AUDITOR",
        "TEST-ENGAGEMENT",
        source.COMPANY,
        source.BRANCHES["A"],
        "period_register",
        as_of="2028-01-02T10:01:00+00:00",
    )
    assert len(new["records"]) == 1
    assert new["records"][0]["record"] == "2027-LOCAL-CHANNEL-CLOSURE"


@pytest.mark.parametrize(
    "attack", ["credit", "scope", "native_trigger", "fixture_alias", "fixture_bytes"]
)
def test_forged_receipts_triggers_and_fixture_mutations_fail_closed(native_run, tmp_path, attack):
    receipt_path = native_run / "SOURCE_RECEIPT.json"
    manifest_path = native_run / "RUN-MANIFEST.json"
    manifest = json.loads(manifest_path.read_bytes())
    if attack in {"credit", "scope"}:
        receipt = json.loads(receipt_path.read_bytes())
        if attack == "credit":
            receipt["route_locators"]["A"][0]["task_credit"] = True
        else:
            receipt["limits"] = ["Full enterprise year assured"]
        receipt_path.write_bytes(source.encoded(receipt))
        manifest["files"]["SOURCE_RECEIPT.json"] = source.digest(receipt_path)
    elif attack == "native_trigger":
        with closing(sqlite3.connect(native_run / "company.sqlite3")) as db:
            db.execute("DROP TRIGGER no_version_update")
            db.commit()
        manifest["files"]["company.sqlite3"] = source.digest(native_run / "company.sqlite3")
    elif attack == "fixture_alias":
        fixture = native_run / "fixtures/recovered-marker.json"
        fixture.unlink()
        os.link(native_run / "fixtures/marker-original.json", fixture)
    else:
        fixture = native_run / "fixtures/pre-movement-marker.json"
        fixture.write_bytes(b'{"batch_total":120}')
        manifest["files"]["fixtures/pre-movement-marker.json"] = source.digest(fixture)
    manifest_path.write_bytes(source.encoded(manifest))
    with pytest.raises(CompanyStoreError):
        source.verify(native_run, repository=REPOSITORY, private_repository=tmp_path)


def test_immutable_original_update_delete_and_causal_future_reference_are_rejected(native_run):
    with closing(sqlite3.connect(native_run / "company.sqlite3")) as db:
        for command in ["UPDATE versions SET sha256='changed'", "DELETE FROM versions"]:
            with pytest.raises(sqlite3.IntegrityError, match="Immutable source"):
                db.execute(command)
            db.rollback()
    item = {
        "system": "test",
        "record": "TEST",
        "version": 1,
        "event_at": "2027-01-01T00:00:00.000000+00:00",
        "body": {},
        "dependencies": ["future"],
        "upstream": [],
    }
    with pytest.raises(CompanyStoreError, match="not available"):
        source._content(
            item,
            {"future": {"available_at": "2027-01-02T00:00:00+00:00"}},
            native_run / "company.sqlite3",
        )


def test_missing_first_native_version_fails_even_with_valid_remaining_hashes(native_run):
    with closing(sqlite3.connect(native_run / "company.sqlite3")) as db:
        trigger = db.execute(
            "SELECT sql FROM sqlite_master WHERE name='no_version_delete'"
        ).fetchone()[0]
        db.execute("DROP TRIGGER no_version_delete")
        db.execute("DELETE FROM versions WHERE system='policy_document' AND version=1")
        db.execute(trigger)
        db.commit()
    with pytest.raises(CompanyStoreError, match="Incomplete native version sequence"):
        source._read_native(native_run / "company.sqlite3")


def test_context_rejects_changed_canon_before_any_predecessor_read(monkeypatch, tmp_path):
    monkeypatch.setattr(source, "_p1_inventory", lambda private: source.P1_FREEZE)
    monkeypatch.setattr(source, "digest", lambda path: "0" * 64)
    with pytest.raises(CompanyStoreError, match="Canon pin differs"):
        source._context(REPOSITORY, tmp_path)
