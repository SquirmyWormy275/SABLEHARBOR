"""Actual intake mechanics must fail closed and preserve independently reviewed history."""

import copy
import hashlib
import json
import sqlite3

import pytest

from enterprise.ccf.operations import examples as ex
from enterprise.ccf.operations import store, testing


@pytest.fixture
def plans():
    rows = [
        dict(
            id="COLLECT:" + cid + ":B",
            control_id=cid,
            boundary_id="B",
            owner_role_id="ROLE",
            trigger="Scheduled",
            proposed_source_system="Proposed export",
            required_records=["Source export"],
            procedure="Control-specific procedure",
            baseline_test="Reperform the control-specific base procedure",
            added_steps=[
                dict(action_id="DUTY", test="Independently inspect the additional scoped duty")
            ],
            population="Full independent source population",
            boundary_test="Confirm local execution",
        )
        for cid in [*testing.ADAPTERS, "SH-POL-001"]
    ]
    return testing.plans(dict(evidence_checklist=rows))


@pytest.fixture
def running(tmp_path, plans, monkeypatch):
    people = ex.principals(["B"])
    people[0]["permissions"].append(
        "review"
    )  # Two role labels still cannot establish independence.
    path = tmp_path / "workflow.sqlite3"
    tokens = store.initialize(path, plans, people)
    monkeypatch.setattr(store, "now", lambda: ex.AT)
    db = store.connect(path)
    yield db, tokens, plans, path
    db.close()


def prepared(running, failed=False, case="CASE"):
    db, tokens, plans, _ = running
    p = plans["COLLECT:SH-IAM-004:B"]
    rows = [ex.record("termination", "B", failed)]
    store.command(
        db, tokens["DEMO-PREPARER"], case, "create", dict(plan_id=p["id"], scope=ex.scope()), 0
    )
    store.command(db, tokens["DEMO-REVIEWER"], case, "population", ex.population(rows), 1)
    return p, rows


def intake_and_review(running, p, rows, revision=2, case="CASE", sub=None):
    db, tokens, _, _ = running
    s = store.command(
        db, tokens["DEMO-PREPARER"], case, "intake", sub or ex.submission(p, rows), revision
    )
    return store.command(
        db,
        tokens["DEMO-REVIEWER"],
        case,
        "review",
        dict(
            submission_id=s["submissions"][-1]["id"],
            decision="ACCEPT",
            rationale="Independent test review",
        ),
        revision + 1,
    )


@pytest.mark.parametrize("adapter", testing.ADAPTERS.values())
def test_eight_control_assertions_reject_substantive_failure(plans, adapter):
    p = next(p for p in plans.values() if p["adapter"] == adapter)
    for failed in (False, True):
        rows = [ex.record(adapter, "B", failed)]
        r = testing.evaluate(p, ex.scope(), ex.population(rows), ex.submission(p, rows), ex.AT)
        assert r["outcome"] == ("FAIL" if failed else "PASS")
        assert r["checks"]
        assert (
            r["raw_digest"]
            == hashlib.sha256(ex.submission(p, rows)["raw_json"].encode()).hexdigest()
        )


def test_automation_cannot_replace_manual_duties(plans):
    p = plans["COLLECT:SH-IAM-004:B"]
    rows = [ex.record("termination", "B")]
    sub = ex.submission(p, rows)
    del sub["manual_tests"]["DUTY"]
    assert testing.evaluate(p, ex.scope(), ex.population(rows), sub, ex.AT)["outcome"] == "NOT_RUN"
    sub["manual_tests"]["BASE"]["result"] = "FAIL"
    assert testing.evaluate(p, ex.scope(), ex.population(rows), sub, ex.AT)["outcome"] == "FAIL"


@pytest.mark.parametrize(
    "fault", ["omitted", "duplicate", "boundary", "origin", "period", "malformed"]
)
def test_unreconciled_or_malformed_evidence_cannot_pass(plans, fault):
    p = plans["COLLECT:SH-IAM-004:B"]
    rows = [ex.record("termination", "B")]
    pop = ex.population(rows)
    if fault == "omitted":
        rows = []
    elif fault == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    elif fault == "boundary":
        rows[0]["boundary_id"] = "OTHER"
    elif fault == "origin":
        rows[0]["origin"] = "OPERATOR_SUPPLIED"
    elif fault == "period":
        rows[0]["occurred_at"] = "2026-01-01T00:00:00+00:00"
    else:
        del rows[0]["data"]["disabled_at"]
    sub = ex.submission(p, rows)
    assert testing.evaluate(p, ex.scope(), pop, sub, ex.AT)["outcome"] == "NOT_RUN"


def test_manual_only_control_has_explicit_evidence_bound_criteria(plans):
    p = plans["COLLECT:SH-POL-001:B"]
    rows = [ex.record("termination", "B")]
    sub = ex.submission(p, rows)
    assert p["adapter"] is None and p["testing_mode"] == "MANUAL"
    assert testing.evaluate(p, ex.scope(), ex.population(rows), sub, ex.AT)["checks"] == []
    sub["manual_tests"]["DUTY"]["record_ids"] = ["NONEXISTENT"]
    with pytest.raises(ValueError, match="retained"):
        testing.evaluate(p, ex.scope(), ex.population(rows), sub, ex.AT)


def test_credentials_independence_revisions_and_restart(running):
    db, tokens, _, path = running
    p, rows = prepared(running)
    with pytest.raises(ValueError, match="credential"):
        store.command(db, "X" * 43, "CASE", "intake", ex.submission(p, rows), 2)
    state = store.command(db, tokens["DEMO-PREPARER"], "CASE", "intake", ex.submission(p, rows), 2)
    review = dict(
        submission_id=state["submissions"][-1]["id"], decision="ACCEPT", rationale="Review"
    )
    with pytest.raises(ValueError, match="Independent"):
        store.command(db, tokens["DEMO-PREPARER"], "CASE", "review", review, 3)
    with pytest.raises(ValueError, match="Stale"):
        store.command(db, tokens["DEMO-REVIEWER"], "CASE", "review", review, 2)
    state = store.command(db, tokens["DEMO-REVIEWER"], "CASE", "review", review, 3)
    reopened = store.connect(path)
    try:
        assert store.replay(reopened)["CASE"] == state
    finally:
        reopened.close()
    assert state["state"] == "REVIEWED_PASS"
    assert state["mapping_acceptance"] == state["operating_effectiveness"] == "NOT_ASSERTED"


def test_independent_population_export_must_reconcile(running):
    db, tokens, plans, _ = running
    p = plans["COLLECT:SH-IAM-004:B"]
    store.command(
        db, tokens["DEMO-PREPARER"], "CASE", "create", dict(plan_id=p["id"], scope=ex.scope()), 0
    )
    pop = ex.population([ex.record("termination", "B")])
    with pytest.raises(ValueError, match="Independent"):
        store.command(db, tokens["DEMO-PREPARER"], "CASE", "population", pop, 1)
    pop["census_json"] = '["DIFFERENT"]'
    with pytest.raises(ValueError, match="Retained population"):
        store.command(db, tokens["DEMO-REVIEWER"], "CASE", "population", pop, 1)
    assert store.replay(db)["CASE"]["revision"] == 1


def test_stale_evidence_rejection_allows_remediation(running, monkeypatch):
    db, tokens, _, _ = running
    p, rows = prepared(running)
    sub = ex.submission(p, rows)
    sub["expires_at"] = "2026-09-10T10:30:00+00:00"
    state = store.command(db, tokens["DEMO-PREPARER"], "CASE", "intake", sub, 2)
    monkeypatch.setattr(store, "now", lambda: "2026-09-10T11:00:00+00:00")
    review = dict(
        submission_id=state["submissions"][-1]["id"], decision="ACCEPT", rationale="Review"
    )
    with pytest.raises(ValueError, match="expired"):
        store.command(db, tokens["DEMO-REVIEWER"], "CASE", "review", review, 3)
    review["decision"] = "REJECT"
    assert (
        store.command(db, tokens["DEMO-REVIEWER"], "CASE", "review", review, 3)["state"]
        == "FINDING_OPEN"
    )


def test_failure_after_missing_evidence_is_never_erased(running):
    db, tokens, _, _ = running
    p, rows = prepared(running)
    sub = ex.submission(p, rows)
    sub["manual_tests"] = {}
    s = intake_and_review(running, p, rows, sub=sub)
    assert s["original_outcome"] == "NOT_RUN"
    for failed, revision in [(True, 4), (False, 7)]:
        store.command(
            db,
            tokens["DEMO-PREPARER"],
            "CASE",
            "remediate",
            dict(
                change_reference="CHANGE",
                action="Remediate missing/failed source",
                due_at=ex.EXPIRY,
            ),
            revision,
        )
        s = intake_and_review(
            running, p, [ex.record("termination", "B", failed)], revision=revision + 1
        )
    assert s["state"] == "RETEST_PASSED_HISTORICAL_FAILURE"
    assert s["historical_failure"] and s["original_outcome"] == "NOT_RUN"
    assert [r["result"]["outcome"] for r in s["submissions"]] == ["NOT_RUN", "FAIL", "PASS"]


def test_immutable_history_and_revocation_preserve_past_results(running, monkeypatch):
    db, tokens, _, _ = running
    p, rows = prepared(running)
    intake_and_review(running, p, rows)
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        db.execute("UPDATE event SET actor='DEMO-PREPARER'")
    monkeypatch.setattr(store, "now", lambda: "2026-09-10T11:00:00+00:00")
    store.revoke(db, tokens["DEMO-ADMIN"], "DEMO-PREPARER")
    assert store.replay(db)["CASE"]["state"] == "REVIEWED_PASS"
    with pytest.raises(ValueError, match="permission"):
        store.command(
            db,
            tokens["DEMO-PREPARER"],
            "OTHER",
            "create",
            dict(plan_id=p["id"], scope=ex.scope()),
            0,
        )
    db.execute("DROP TRIGGER immutable_event_UPDATE")
    db.execute("UPDATE event SET payload='{}' WHERE seq=1")
    with pytest.raises(ValueError, match="chain"):
        store.replay(db)


def test_changed_evaluator_requires_history_migration(running, monkeypatch):
    db, _, _, _ = running
    monkeypatch.setattr(store, "implementation_digest", lambda: "changed")
    with pytest.raises(ValueError, match="migration"):
        store.replay(db)


def test_full_demo_links_prospective_case_and_preserves_original(plans, tmp_path):
    out = tmp_path / "demo"
    summary = ex.build(out, plans)
    assert summary["cases"] == 17
    r = json.loads((out / "ASSESSMENT_REPORT.json").read_text())
    s = r["cases"]["DEMO-termination-negative"]
    assert s["state"] == "CLOSED_PROSPECTIVE_VALIDATION"
    assert s["original_outcome"] == "FAIL"
    assert [x["result"]["outcome"] for x in s["submissions"]] == ["FAIL", "PASS"]
    assert all(p.stat().st_mode & 0o077 == 0 for p in out.iterdir())


def test_competing_case_pass_does_not_hide_same_period_failure(running):
    db, tokens, _, _ = running
    for failed, case in [(False, "GOOD"), (True, "BAD")]:
        p, rows = prepared(running, failed, case)
        intake_and_review(running, p, rows, case=case)
    summary = list(store.report(db, tokens["DEMO-REVIEWER"])["period_results"].values())
    assert len(summary) == 1 and summary[0]["result"] == "FAIL"
    assert set(summary[0]["case_ids"]) == {"GOOD", "BAD"}


def test_scope_permissions_restrict_mutations_and_reports(tmp_path, plans, monkeypatch):
    plans = copy.deepcopy(plans)
    other = copy.deepcopy(plans["COLLECT:SH-IAM-004:B"])
    other.update(id="OTHER-PLAN", boundary_id="OTHER-BOUNDARY")
    plans[other["id"]] = other
    people = ex.principals(["B"])
    people.append(
        dict(
            id="OTHER-PREPARER",
            permissions=["prepare"],
            boundaries=["OTHER-BOUNDARY"],
            valid_from=people[0]["valid_from"],
            expires_at=people[0]["expires_at"],
        )
    )
    tokens = store.initialize(tmp_path / "scoped.sqlite3", plans, people)
    db = store.connect(tmp_path / "scoped.sqlite3")
    monkeypatch.setattr(store, "now", lambda: ex.AT)
    payload = dict(plan_id=other["id"], scope=ex.scope())
    try:
        with pytest.raises(ValueError, match="permission"):
            store.command(db, tokens["DEMO-PREPARER"], "OTHER", "create", payload, 0)
        store.command(db, tokens["OTHER-PREPARER"], "OTHER", "create", payload, 0)
        assert not store.report(db, tokens["DEMO-REVIEWER"])["cases"]
        assert set(store.report(db, tokens["OTHER-PREPARER"])["cases"]) == {"OTHER"}
    finally:
        db.close()


def test_same_period_success_cannot_be_used_as_prospective_closure(running):
    db, tokens, _, _ = running
    for failed, case in [(False, "PASSING"), (True, "FAILED")]:
        p, rows = prepared(running, failed, case)
        intake_and_review(running, p, rows, case=case)
    store.command(
        db,
        tokens["DEMO-PREPARER"],
        "FAILED",
        "remediate",
        dict(change_reference="CHANGE", action="Prospective correction", due_at=ex.EXPIRY),
        4,
    )
    with pytest.raises(ValueError, match="prospective case"):
        store.command(
            db,
            tokens["DEMO-REVIEWER"],
            "FAILED",
            "close_prospectively",
            dict(validation_case_id="PASSING", rationale="Attempt to reuse same-period result"),
            5,
        )
    assert store.replay(db)["FAILED"]["historical_failure"]
