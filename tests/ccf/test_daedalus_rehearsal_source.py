"""Cross-source checks for the bounded, newly authored Daedalus exercise."""

import hashlib
import json
from pathlib import Path

from enterprise.ccf.company_closeout.information_policy import build_policy, decide
from enterprise.operations.completed_period import build as completed_period

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "enterprise/ccf/company_closeout/source/daedalus_rehearsal_2026_09_29.json"


def _source():
    return json.loads(SOURCE.read_text())


def _person(person_id):
    return {"id": person_id, "tenant": "SH", "purpose": "inspection"}


def test_rehearsal_persons_case_and_byte_pins_match_accepted_sources():
    source = _source()
    for pin in (source["policy_source"], source["person_population"], source["case_source"]):
        actual = hashlib.sha256((ROOT / pin["source_path"]).read_bytes()).hexdigest()
        assert actual == pin["source_sha256"]
    for record in source["records"]:
        actual = hashlib.sha256((ROOT / record["repository_path"]).read_bytes()).hexdigest()
        assert actual == record["source_sha256"]

    people = completed_period()["tables"]["people"]
    person_ids = [person["person_id"] for person in people]
    assert len(person_ids) == source["person_population"]["population_count"] == 702
    assert len(person_ids) == len(set(person_ids))
    assert {binding["person_id"] for binding in source["person_bindings"]} <= set(person_ids)

    case = json.loads((ROOT / source["case_source"]["source_path"]).read_text())
    assert case["record_id"] == source["case_source"]["record_id"]
    delegations = {row["person_id"]: row["role"] for row in case["role_delegations"]}
    assert all(
        delegations[binding["person_id"]] == binding["case_source_role"]
        for binding in source["person_bindings"]
    )
    missing = case["missing_decision_response"]
    assert missing["owner_decision_source_id"] is None
    assert missing["independent_verification_source_id"] is None
    assert missing["state"] == "MISSING_OWNER_DECISION_AND_INDEPENDENT_VERIFICATION"


def test_narrow_grants_case_clock_and_transitive_restriction():
    source = _source()
    people = completed_period()["tables"]["people"]
    expected_person_ids = [person["person_id"] for person in people]
    expected_record_ids = source["record_population"]["expected_record_ids"]
    built = build_policy(
        people,
        source["records"],
        expected_person_ids=expected_person_ids,
        expected_record_ids=expected_record_ids,
    )
    assert built["counts"] == {"people": 702, "records": 4}
    assert built["implicit_restricted_grants"] == 0
    assert built["runtime_enforcement_claimed"] is False

    assert source["case_clock_approval"]["learner_may_advance"] is False
    now = source["case_clock_approval"]["case_as_of"]
    records = {row["record_id"]: row for row in source["records"]}
    auditor = _person("SH-EMP-INTERNAL-AUDIT-0001")
    owner = _person("SH-EMP-ESS-0005")
    unrelated = _person("SH-EMP-ESS-0006")
    base, view, notice, denied = expected_record_ids
    assert records[view]["sources"] == [base]
    assert records[notice]["sources"] == [view]
    for person in (auditor, owner):
        for action in (
            "read",
            "search",
            "snippet",
            "count",
            "citation",
            "tool_result",
            "answer",
            "export",
        ):
            assert decide(records, base, person, action, now) == "ALLOW"
            assert decide(records, view, person, action, now) == "ALLOW"
            assert decide(records, notice, person, action, now) == "ALLOW"
            assert decide(records, denied, person, action, now) == "DENY"
        assert decide(records, view, person, "read", now, tombstones=[base]) == "DENY"
        assert decide(records, notice, person, "read", now, tombstones=[base]) == "DENY"
        assert decide(records, notice, person, "read", now, revoked_ids=[person["id"]]) == "DENY"
    for record_id in expected_record_ids:
        assert decide(records, record_id, unrelated, "read", now) == "DENY"
    assert decide(records, notice, auditor, "read", "2027-04-01T01:59:59+00:00") == "DENY"
    assert decide(records, notice, auditor, "authoritative_write", now) == "DENY"


def test_rehearsal_is_explicitly_bounded_and_no_implicit_grants():
    source = _source()
    assert source["state"] == "PROVISIONAL"
    assert source["scenario"] == "BOUNDED_LOCAL_DAEDALUS_REHEARSAL_NOT_REAL_DEPLOYMENT"
    assert "fresh private portal Store engagement" in source["engagement"]["creation"]
    assert source["record_population"]["complete_for_scope"] is True
    assert all(record["class_id"] == "WORKING_OPERATIONS" for record in source["records"])
    assert source["records"][-1]["grants"] == []
