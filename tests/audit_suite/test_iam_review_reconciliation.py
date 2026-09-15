from copy import deepcopy

import pytest

from enterprise.audit_suite.iam_review_reconciliation import checks
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from enterprise.audit_suite.store import DomainError

SCOPE = {"period_start": "2027-01-01", "period_end": "2027-12-31", "boundaries": ["corporate"]}


def example():
    def ref(id, system, record, version=1):
        return {
            "id": id,
            "source_store_id": "IAM",
            "company": "C",
            "branch": "B",
            "system": system,
            "record": record,
            "version": version,
            "sha256": "a" * 64,
            "available_at": "2027-01-02T00:00:00Z",
            "event_at": "2027-01-02T00:00:00Z",
        }

    app = ref("A", "application", "APP")
    hr = ref("H", "hr", "HR")
    common = {
        "control_id": "SH-IAM-007",
        "period_start": "2027-01-01T00:00:00Z",
        "period_end_exclusive": "2027-04-01T00:00:00Z",
    }
    member = {
        "person_id": "P",
        "record": "APP",
        "version": 1,
        "sha256": app["sha256"],
        "rights": ["read", "admin"],
        "cause_id": "MOVE",
    }
    pop = {
        **common,
        "members": [member],
        "membership_sha256": sha(encoded([member])),
        "query": {"system": "application", "as_of_exclusive": common["period_end_exclusive"]},
    }
    p = ref("P", "review_population", "POP")
    p["sha256"] = sha(encoded(pop))
    d = ref("D", "review_decisions", "DEC")
    r = ref("R", "review_reconciliation", "REC")
    for v in (p, d, r):
        v["available_at"] = "2027-04-01T00:00:01Z"
    decision = {
        "person_id": "P",
        "source_record": "APP",
        "source_version": 1,
        "source_sha256": app["sha256"],
        "observed_rights": ["admin", "read"],
        "authorized_rights": ["read"],
        "remove_rights": ["admin"],
        "decision": "REMOVE_EXCESS",
        "removal_confirmation": "NOT_YET_PERFORMED",
    }
    bodies = {
        "P": pop,
        "D": {**common, "population_sha256": p["sha256"], "decisions": [decision]},
        "R": {
            **common,
            "population_sha256": p["sha256"],
            "hr_sources": [{"record": "HR", "version": 1, "sha256": hr["sha256"]}],
            "hr_visible_person_ids": ["P"],
            "export_person_ids": ["P"],
            "missing_person_ids": [],
        },
        "A": {"person_id": "P", "rights": ["read", "admin"], "cause_id": "MOVE"},
        "H": {"person_id": "P"},
    }
    contract = {
        "population_ref_id": "P",
        "decisions_ref_id": "D",
        "reconciliation_ref_id": "R",
        "application_ref_ids": ["A"],
        "hr_ref_ids": ["H"],
    }
    return [contract], [p, d, r, app, hr], bodies


def test_exact_hashes_and_rights_order_are_separate_from_execution():
    contracts, refs, bodies = example()
    result = checks(contracts, refs, bodies, SCOPE)[0]
    assert result["membership_hash_matches"] and result["decision_population_hash_matches"]
    assert result["reconciliation_population_hash_matches"]
    assert result["decisions"][0]["rights_set_equal"] is True
    assert result["decisions"][0]["rights_array_equal"] is False
    assert result["decisions"][0]["removal_set_matches_arithmetic"] is True
    assert result["decisions"][0]["removal_execution"] == "NOT_VERIFIED"
    assert result["hr_resolution"] == "ALL_LISTED_HR_REFERENCES_RESOLVED"
    assert result["population_completeness"] == "NOT_ESTABLISHED"


def test_mismatched_hashes_rights_and_recorded_missing_lists_surface():
    contracts, refs, bodies = example()
    bodies["P"]["membership_sha256"] = "b" * 64
    bodies["D"]["population_sha256"] = "b" * 64
    bodies["D"]["decisions"][0]["observed_rights"] = ["read"]
    bodies["R"]["missing_person_ids"] = ["OTHER"]
    result = checks(contracts, refs, bodies, SCOPE)[0]
    assert not result["membership_hash_matches"] and not result["decision_population_hash_matches"]
    assert not result["decisions"][0]["rights_set_equal"]
    assert not result["recorded_missing_matches_recorded_list_difference"]
    assert not result["recorded_missing_matches_selected_hr_difference"]


def test_missing_hr_is_partial_and_application_pin_mismatch_visible():
    contracts, refs, bodies = example()
    contracts[0]["hr_ref_ids"] = []
    refs[3]["sha256"] = "b" * 64
    result = checks(contracts, refs, bodies, SCOPE)[0]
    assert result["hr_resolution"] == "PARTIAL_SELECTED_SUPPORT"
    assert result["selected_hr_minus_members"] is None
    assert result["members"][0]["source_status"] == "DIGEST_MISMATCH"


@pytest.mark.parametrize(
    "fault", ["bool", "float", "duplicate", "cutoff", "branch", "quarter", "hash", "source_ids"]
)
def test_invalid_schema_scope_and_duplicates_fail(fault):
    contracts, refs, bodies = example()
    if fault == "bool":
        bodies["P"]["members"][0]["version"] = True
    elif fault == "float":
        bodies["D"]["decisions"][0]["source_version"] = 1.0
    elif fault == "duplicate":
        bodies["P"]["members"].append(deepcopy(bodies["P"]["members"][0]))
    elif fault == "cutoff":
        bodies["P"]["query"]["as_of_exclusive"] = "2027-04-02T00:00:00Z"
    elif fault == "branch":
        refs[4]["branch"] = "OTHER"
    elif fault == "quarter":
        bodies["D"]["period_end_exclusive"] = "2027-07-01T00:00:00Z"
    elif fault == "hash":
        bodies["R"]["hr_sources"][0]["sha256"] = "bad"
    else:
        contracts[0]["hr_ref_ids"] = ["H", "H"]
    with pytest.raises(DomainError):
        checks(contracts, refs, bodies, SCOPE)


def test_exact_cutoff_is_not_prior_support_and_unmatched_decision_is_not_removed():
    contracts, refs, bodies = example()
    refs[4]["available_at"] = "2027-04-01T00:00:00Z"
    bodies["D"]["decisions"][0]["source_version"] = 2
    result = checks(contracts, refs, bodies, SCOPE)[0]
    assert result["hr_references"][0]["status"] == "NOT_BEFORE_EXCLUSIVE_CUTOFF"
    assert result["hr_resolution"] == "PARTIAL_SELECTED_SUPPORT"
    assert result["decisions"][0]["member_match"] == "NO_EXACT_MEMBER"
    assert len(result["members_without_exact_decision"]) == 1


def test_different_native_boundaries_do_not_become_one_review():
    contracts, refs, bodies = example()
    bodies["D"]["boundary_id"] = "secondary"
    with pytest.raises(DomainError):
        checks(contracts, refs, bodies, {**SCOPE, "boundaries": ["corporate", "secondary"]})


def test_review_event_timing_separate_from_later_availability():
    contracts, refs, bodies = example()
    refs[0]["event_at"] = None
    refs[1]["event_at"] = "2027-04-01T00:00:00Z"
    refs[2]["event_at"] = "2027-03-31T00:00:00Z"
    result = checks(contracts, refs, bodies, SCOPE)[0]
    assert [r["status"] for r in result["review_event_timing"]] == [
        "UNDATED",
        "AT_OR_AFTER_DECLARED_CUTOFF",
        "EVENT_BEFORE_DECLARED_CUTOFF",
    ]
    assert all(
        r["execution_inference"] == "NOT_MADE_FROM_AVAILABILITY"
        for r in result["review_event_timing"]
    )
