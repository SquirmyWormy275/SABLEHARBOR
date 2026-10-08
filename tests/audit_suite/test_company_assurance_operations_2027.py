"""Company assurance source cannot become a learner result or mutable opinion store."""

import hashlib
import json
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import company_assurance_operations_2027 as assurance
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def context():
    return assurance._context(REPOSITORY, PRIVATE)


def _row(rows, record, version=1):
    return next(row for row in rows if row["record"] == record and row["version"] == version)


def _rehash(row):
    row["sha256"] = sha(encoded(row["body"]))


def test_exact_nine_routes_and_substantive_locators_preserve_versions(context):
    assert len(assurance.TASKS) == len(set(assurance.TASKS)) == 9
    for scenario, count in (("CLEAN", 26), ("MESSY", 27)):
        rows = assurance._expected_rows(context, scenario)
        assert len(rows) == count
        refs = [
            {
                "company": assurance.COMPANY,
                "branch": assurance.BRANCHES[scenario],
                "imported_at": "2026-10-01T00:00:00+00:00",
                **{
                    k: r[k]
                    for k in ("system", "record", "version", "sha256", "event_at", "available_at")
                },
            }
            for r in rows
        ]
        leads = assurance._lead_map(refs)
        assert set(leads) == set(assurance.TASKS)
        assert all(len(v) >= 4 for v in leads.values())
        selected = leads["TASK-SH-ASS-003-corporate-TOE"]
        assert {r["version"] for r in selected if r["record"] == "ENG-RECOVERY"} == {1, 2}


def test_independent_reperformance_is_bounded_and_preserves_history(context):
    for scenario in assurance.BRANCHES:
        rows = assurance._expected_rows(context, scenario)
        independence = _row(rows, "INDEPENDENCE-01")["body"]
        assert independence["preparer_id"] == "AS-P009"
        assert independence["quality_reviewer_id"] != independence["preparer_id"]
        assert {r["person_id"] for r in independence["excluded_evaluators"]} == {
            "AS-P005",
            "AS-P007",
        }
        assert independence["professional_external_opinion_authority"] is False
        replay = _row(rows, "WP-TECHNICAL-01")["body"]["reperformance"]
        assert replay["reperformed_elapsed_minutes"] == (155 if scenario == "CLEAN" else 180)
        assert replay["rto_met"] and replay["rpo_met"] and replay["marker_digest_match"]
        assert replay["application_recovery_proven"] is False
        assert (
            _row(rows, "REPORT-01")["body"]["full_control_or_hipaa_compliance_conclusion"]
            == "NOT_EXPRESSED"
        )
        assert (
            _row(rows, "COMMITTEE-ROUTE-01")["body"]["committee_collective_decision"]
            == "NOT_PERFORMED"
        )
        assert rows[-1]["body"]["enterprise_programme_population_complete"] is False
        assert all("scenario" not in r["body"] and "task_credit" not in r["body"] for r in rows)
    messy = assurance._expected_rows(context, "MESSY")
    technical = _row(messy, "WP-TECHNICAL-01")["body"]
    assert technical["objective_acceptance"] is False
    assert technical["historical_issue_remains_open"] is True
    assert len(technical["historical_failed_versions_retained"]) == 2
    assert _row(messy, "FOLLOWUP-01")["body"]["prior_finding_status_changed"] is False


def test_description_omission_has_configuration_cause_and_is_corrected_before_release(context):
    rows = assurance._expected_rows(context, "MESSY")
    config = _row(rows, "DESCRIPTION-CONFIG-01")["body"]
    assert "ISSUE" not in config["source_systems"]
    assert config["include_issue_and_exception_history"] is False
    draft = _row(rows, "DESCRIPTION-01")["body"]
    review = _row(rows, "DISCLOSURE-REVIEW-01")["body"]
    corrected = _row(rows, "DESCRIPTION-01", 2)["body"]
    assert review["missing_relevant_description_items"] == [
        "DESC-HISTORICAL-BYPASS",
        "DESC-OWNER-CORRECTION",
    ]
    assert review["decision"] == "RETURN_FOR_MATERIAL_ISSUE_DISCLOSURE"
    assert len(corrected["assertions"]) == len(draft["assertions"]) + 2
    assert corrected["supersedes"]["sha256"] == _row(rows, "DESCRIPTION-01")["sha256"]
    release = _row(rows, "CUSTOMER-RELEASE-01")["body"]
    assert release["approved_description_version"] == 2
    assert release["actual_customer_message_sent"] is False
    assert release["external_opinion_attached"] is False
    assert release["release_status"] == "APPROVED_LIMITED_FICTIONAL_BRIEFING_NOT_TRANSMITTED"


def test_rehashed_self_review_cross_branch_answer_and_period_claim_rejected(context):
    for kind in ("self_review", "cross_branch", "answer", "period"):
        rows = deepcopy(assurance._expected_rows(context, "CLEAN"))
        row = _row(rows, "REVIEW-RECOVERY")
        if kind == "self_review":
            row["body"]["reviewer_id"] = row["body"]["preparer_id"]
        elif kind == "cross_branch":
            row["body"]["dependencies"][0]["branch"] = assurance.BRANCHES["MESSY"]
        elif kind == "answer":
            row["body"]["expected_finding"] = "PASS"
        else:
            row = rows[-1]
            row["body"]["external_assurance_opinion_count"] = 1
        _rehash(row)
        with pytest.raises(
            CompanyStoreError, match="self-review|dependency|learner-answer|period/claim"
        ):
            assurance._validate_history(rows, "CLEAN")


def test_fractional_negative_or_wrong_numeric_replay_is_not_accepted(context):
    original = assurance._source(context, "CLEAN", "BCM", "exercise_result", "MARKER-RECOVERY")[
        "body"
    ]
    for finish in ("2027-08-15T12:35:01+00:00", "2027-08-15T09:59:00+00:00"):
        body = deepcopy(original)
        body["detail"]["observed_finish_at"] = finish
        with pytest.raises(CompanyStoreError, match="Invalid selected recovery"):
            assurance._numeric_replay(body)
    changed = deepcopy(context)
    changed["sources"]["BCM"]["CLEAN"]["exercise_result", "MARKER-RECOVERY", 1]["body"]["detail"][
        "measured_restore_minutes_simulated"
    ] = 154
    with pytest.raises(CompanyStoreError, match="arithmetic differs"):
        assurance._expected_rows(changed, "CLEAN")


def test_private_create_verify_and_resealed_claim_promotion_rejected(
    tmp_path, context, monkeypatch
):
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    monkeypatch.setattr(assurance, "_context", lambda *_: context)
    root = parent / "run"
    assurance.create(root, repository=REPOSITORY, private_repository=PRIVATE)
    assert (
        assurance.verify(root, repository=REPOSITORY, private_repository=PRIVATE)[
            "native_version_count"
        ]
        == 53
    )
    assert all(p.stat().st_mode & 0o077 == 0 and p.stat().st_nlink == 1 for p in root.iterdir())
    receipt = root / "RECEIPT.json"
    body = json.loads(receipt.read_text())
    body["external_assurance_opinion_count"] = 1
    receipt.write_text(json.dumps(body))
    manifest = root / "MANIFEST.json"
    body = json.loads(manifest.read_text())
    body["receipt_sha256"] = hashlib.sha256(receipt.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(body))
    with pytest.raises(CompanyStoreError, match="manifest/receipt qualification"):
        assurance.verify(root, repository=REPOSITORY, private_repository=PRIVATE)


@pytest.mark.parametrize(
    "trigger",
    ["no_version_update", "no_version_delete", "no_collection_update", "no_collection_delete"],
)
def test_resealed_mutable_source_is_rejected(tmp_path, context, monkeypatch, trigger):
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    monkeypatch.setattr(assurance, "_context", lambda *_: context)
    root = parent / "run"
    assurance.create(root, repository=REPOSITORY, private_repository=PRIVATE)
    dbpath = root / "company.sqlite3"
    with sqlite3.connect(dbpath) as db:
        db.execute(f"DROP TRIGGER {trigger}")
    manifest = root / "MANIFEST.json"
    body = json.loads(manifest.read_text())
    body["company_db_sha256"] = hashlib.sha256(dbpath.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(body))
    with pytest.raises(CompanyStoreError, match="immutable-source triggers"):
        assurance.verify(root, repository=REPOSITORY, private_repository=PRIVATE)


def test_partial_pin_and_unknown_branch_rejected(context, monkeypatch):
    with pytest.raises(CompanyStoreError, match="Unknown assurance branch"):
        assurance._expected_rows(context, "UNKNOWN")
    pins = dict(assurance.SOURCE_PINS)
    key = next(iter(pins))
    pins[key] = pins[key][:16]
    monkeypatch.setattr(assurance, "SOURCE_PINS", pins)
    with pytest.raises(CompanyStoreError, match="Pinned assurance canon"):
        assurance._context(REPOSITORY, PRIVATE)
