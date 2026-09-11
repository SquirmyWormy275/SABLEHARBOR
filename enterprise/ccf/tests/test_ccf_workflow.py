import copy

import pytest

from enterprise.ccf.examples import load, run
from enterprise.ccf.registry import compile_registry, digest
from enterprise.ccf.workflow import (
    advance,
    close,
    collect,
    open_exception,
    remediate,
    review,
    verify_evidence,
)


@pytest.fixture
def source():
    return load()


@pytest.fixture
def setup(source):
    case = source["cases"][0]
    actors = source["actors"]
    evidence = collect(
        case, actors, "SYN-PREPARER", "2027-04-01", attachments=set(case["tables"]) - {"journal"}
    )
    ex = open_exception(
        evidence,
        actors,
        "SYN-REVIEWER",
        "2027-04-02",
        "2027-04-05",
        "Missing evidence",
        "False assurance",
        "Independent review",
    )
    pending = remediate(
        advance(ex, "2027-04-06"), actors, "SYN-PREPARER", "2027-04-07", "SYN-CHANGE"
    )
    retest = collect(case, actors, "SYN-PREPARER", "2027-04-08")
    return case, actors, pending, retest


def test_three_examples_demonstrate_negative_and_closure_states():
    result = run(compile_registry())
    for case in result["cases"]:
        assert case["passing"]["outcome"] == "PASS"
        assert case["negative"]["outcome"] == "FAIL"
        assert case["missing"]["outcome"] == "NOT_RUN"
        assert case["expired"]["state"] == "EXPIRED_ESCALATED"
        assert case["self_review"] == "REJECTED"
        assert case["closed"]["state"] == "CLOSED"
        assert case["closed"]["original"] == case["missing"]
        assert case["closed"]["original"]["operating_effectiveness"] == "NOT_ASSERTED"


@pytest.mark.parametrize("case_index", [0, 1, 2])
@pytest.mark.parametrize(
    "mutation", ["drop", "duplicate", "boundary", "scenario", "period", "empty"]
)
def test_incomplete_or_wrong_population_never_passes(source, case_index, mutation):
    case = source["cases"][case_index]
    table = next(iter(case["tables"]))
    rows = case["tables"][table]
    if mutation == "drop":
        rows.pop()
    elif mutation == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    elif mutation == "empty":
        rows.clear()
    elif mutation == "boundary":
        rows[0]["boundary_id"] = "outside"
    elif mutation == "scenario":
        rows[0]["scenario"] = "other"
    elif mutation == "period":
        rows[0]["effective_on"] = "2027-02-28"
    result = collect(case, source["actors"], "SYN-PREPARER", "2027-04-01")
    assert result["outcome"] == "NOT_RUN"
    assert result["assertions"] == 0


def test_foreign_unauthorized_expired_and_self_review_fail(source):
    case = source["cases"][0]
    actors = source["actors"]
    result = collect(case, actors, "SYN-PREPARER", "2027-04-01")
    with pytest.raises(ValueError):
        review(result, actors, "SYN-PREPARER", "2027-04-02")
    actors[1]["boundaries"] = ["corporate"]
    with pytest.raises(ValueError):
        review(result, actors, "SYN-REVIEWER", "2027-04-02")
    actors[1]["boundaries"] = ["advisory"]
    actors[1]["effective_to"] = "2027-04-02"
    with pytest.raises(ValueError):
        review(result, actors, "SYN-REVIEWER", "2027-04-02")
    with pytest.raises(ValueError):
        collect(case, actors, "UNAPPOINTED", "2027-04-01")


def test_outcome_tampering_fails_even_with_rehashed_manifest(source):
    case = source["cases"][0]
    evidence = collect(
        case, source["actors"], "SYN-PREPARER", "2027-04-01", tables=case["negative_tables"]
    )
    evidence["outcome"] = "PASS"
    evidence["evidence_id"] = digest({k: v for k, v in evidence.items() if k != "evidence_id"})
    with pytest.raises(ValueError, match="re-performance"):
        verify_evidence(evidence)


@pytest.mark.parametrize(
    "change", ["period", "scope", "expected_population", "pre_remediation", "self", "failed"]
)
def test_invalid_retests_cannot_close(setup, change):
    case, actors, pending, retest = setup
    original = copy.deepcopy(pending)
    if change == "failed":
        retest = collect(case, actors, "SYN-PREPARER", "2027-04-08", tables=case["negative_tables"])
        result = close(pending, retest, actors, "SYN-REVIEWER", "2027-04-09")
        assert result["state"] == "VALIDATION_PENDING"
    else:
        if change == "period":
            case["period_start"] = "2027-03-02"
        elif change == "scope":
            case["implementation_id"] = "LC-CREDIT"
        elif change == "expected_population":
            case["expected_ids"]["journal"].append("SYN-EXTRA")
        retest = collect(
            case,
            actors,
            "SYN-PREPARER",
            "2027-04-06" if change == "pre_remediation" else "2027-04-08",
        )
        with pytest.raises(ValueError):
            close(
                pending,
                retest,
                actors,
                "SYN-PREPARER" if change == "self" else "SYN-REVIEWER",
                "2027-04-09",
            )
    assert pending == original


def test_invalid_exception_dates_and_states(setup):
    case, actors, pending, retest = setup
    with pytest.raises(ValueError):
        advance(pending, "2027-04-01")
    with pytest.raises(ValueError):
        open_exception(
            retest,
            actors,
            "SYN-REVIEWER",
            "2027-04-09",
            "2027-04-08",
            "reason",
            "risk",
            "compensation",
        )
    done = close(pending, retest, actors, "SYN-REVIEWER", "2027-04-09")
    with pytest.raises(ValueError):
        remediate(done, actors, "SYN-PREPARER", "2027-04-10", "change")


@pytest.mark.parametrize(
    "mutation", ["expired_contractor", "mover", "orphan", "late_disable", "boolean_string"]
)
def test_identity_control_assertions(source, mutation):
    case = source["cases"][1]
    t = case["tables"]
    if mutation == "expired_contractor":
        t["accounts"][2]["enabled"] = True
    elif mutation == "mover":
        t["entitlements"][1]["entitlement"] = "ROLE-OLD"
    elif mutation == "orphan":
        t["accounts"][0]["worker_id"] = "UNKNOWN"
    elif mutation == "late_disable":
        t["accounts"][0]["changed_at"] = "2027-04-01T12:00:00+00:00"
    elif mutation == "boolean_string":
        t["accounts"][0]["enabled"] = "false"
    assert collect(case, source["actors"], "SYN-PREPARER", "2027-04-02")["outcome"] == "FAIL"


@pytest.mark.parametrize(
    "mutation",
    ["hash", "deleted", "held", "rto", "rpo", "dependency", "naive_time", "boolean_target"],
)
def test_recovery_control_assertions(source, mutation):
    case = source["cases"][2]
    t = case["tables"]
    if mutation == "hash":
        t["backups"][0]["artifact_sha256"] = "0" * 64
    elif mutation == "deleted":
        t["restores"][0]["records"]["deleted"] = {"payload": "resurrected"}
    elif mutation == "held":
        t["restores"][0]["records"]["held"] = {"payload": "held"}
    elif mutation == "rto":
        t["restores"][0]["completed_at"] = "2027-03-31T12:10:00+00:00"
    elif mutation == "rpo":
        t["restores"][0]["recovery_point_at"] = "2027-03-31T11:00:00+00:00"
    elif mutation == "dependency":
        t["restores"][1]["started_at"] = "2027-03-31T12:00:30+00:00"
    elif mutation == "naive_time":
        t["restores"][0]["started_at"] = "2027-03-31T12:00:00"
    elif mutation == "boolean_target":
        t["services"][0]["rto_seconds"] = True
    assert collect(case, source["actors"], "SYN-PREPARER", "2027-04-01")["outcome"] in {
        "FAIL",
        "NOT_RUN",
    }


def test_waiver_expires_even_when_remediation_is_already_pending(source):
    case, actors = source["cases"][0], source["actors"]
    evidence = collect(
        case, actors, "SYN-PREPARER", "2027-04-01", attachments={"events", "subledger_rollforward"}
    )
    ex = open_exception(
        evidence,
        actors,
        "SYN-REVIEWER",
        "2027-04-02",
        "2027-04-05",
        "reason",
        "risk",
        "compensation",
    )
    pending = remediate(ex, actors, "SYN-PREPARER", "2027-04-03", "SYN-EARLY-REMEDIATION")
    expired = advance(pending, "2027-04-06")
    assert expired["state"] == "VALIDATION_PENDING"
    assert expired["waiver_state"] == "EXPIRED"
    assert expired["transitions"][-1]["state"] == "EXPIRED_ESCALATED"
