from copy import deepcopy
from types import SimpleNamespace

import pytest

from enterprise.audit_suite.audit_readiness import report, summarize
from enterprise.audit_suite.store import DomainError, digest


def projection():
    return {
        "id": "E1",
        "revision": 3,
        "scope": {"boundaries": ["corporate"], "exclusions": ["Explicit outside service"]},
        "mode": "MESSY",
        "controls": [{"id": "C1"}, {"id": "C2"}],
        "tasks": [
            {
                "id": "T1",
                "control_id": "C1",
                "kind": "TOE",
                "status": "COMPLETE",
                "conclusion": "PASS",
            },
            {"id": "T2", "control_id": "C1", "kind": "TOD", "status": "NOT_APPLICABLE"},
            {"id": "T3", "kind": "GATE", "status": "NOT_STARTED"},
        ],
        "requests": [{"id": "R1", "control_id": "C1", "status": "ISSUED", "artifact_ids": ["A1"]}],
        "artifacts": [
            {
                "id": "A1",
                "request_id": "R1",
                "version": 2,
                "sha256": "a" * 64,
                "status": "AVAILABLE",
                "source": {
                    "origin": "MIGRATED_SYNTHETIC_HISTORY",
                    "receipt": {
                        "source": {
                            "company": "CO",
                            "branch": "B",
                            "system": "SYS",
                            "record": "ROW",
                            "version": 2,
                            "sha256": "a" * 64,
                        }
                    },
                },
            }
        ],
        "populations": [{"id": "POP1", "version": 1, "artifact_id": "A1", "status": "PROVISIONAL"}],
        "selections": [{"id": "SEL1", "population_id": "POP1"}],
        "workpapers": [],
        "reviews": [],
    }


def test_denominators_include_declared_exclusions_and_unknowns_are_not_failures():
    result = summarize(projection())
    assert result["denominators"] == {
        "scoped_controls": 2,
        "scoped_procedures": 2,
        "known_not_applicable_tasks": 1,
        "unassigned_or_out_of_scope_tasks": 1,
    }
    one, two = result["controls"]
    assert one["known_excluded_task_ids"] == ["T2"]
    assert {r["code"] for r in one["reasons"]} == {
        "OUTSTANDING_RESPONSE",
        "RETAINED_ARTIFACT_WITHOUT_WORKPAPER_LINK",
        "PROVISIONAL_POPULATION",
    }
    assert two["reasons"][0]["code"] == "NO_ISSUED_REQUEST"
    assert all(c["control_effectiveness"] == "NOT_ASSESSED" for c in result["controls"])
    assert one["sources"][0]["current_source_freshness"] == "UNKNOWN_NOT_QUERIED"
    assert one["sources"][0]["qualifiers"][0]["value"] == "MIGRATED_SYNTHETIC_HISTORY"


def test_control_workpaper_and_completed_task_do_not_imply_all_procedures_tested():
    p = projection()
    p["workpapers"] = [
        {
            "id": "W1",
            "control_id": "C1",
            "prepared_by": "A",
            "versions": [
                {
                    "version": 1,
                    "actor": "A",
                    "evidence_ids": ["A1"],
                    "procedures": "We completed everything perfectly",
                }
            ],
        }
    ]
    result = summarize(p)["controls"][0]
    assert "RETAINED_ARTIFACT_WITHOUT_WORKPAPER_LINK" not in {r["code"] for r in result["reasons"]}
    assert all(t["testing_verified"] == "NOT_ASSESSED" for t in result["procedures"])
    assert all(t["procedure_evidence_linkage"] == "NOT_RECORDED" for t in result["procedures"])
    assert "NO_CURRENT_DISTINCT_CONTRIBUTOR_REVIEW_RECORD" in {r["code"] for r in result["reasons"]}


def test_review_kind_resolution_and_distinct_identity_do_not_establish_qualification():
    p = projection()
    version = {"version": 1, "actor": "A", "evidence_ids": ["A1"]}
    p["workpapers"] = [{"id": "W1", "control_id": "C1", "prepared_by": "A", "versions": [version]}]
    p["reviews"] = [
        {
            "id": "RV1",
            "workpaper_id": "W1",
            "workpaper_version": 1,
            "workpaper_version_digest": digest(version),
            "actor": "B",
            "kind": "HUMAN",
            "status": "RESOLVED",
        }
    ]
    result = summarize(p)["controls"][0]
    assert result["reviews"][0]["contributor_identity_comparison"] == "DISTINCT_CONTRIBUTOR"
    assert result["reviews"][0]["professional_qualification"] == "NOT_ASSESSED"
    assert result["reviews"][0]["reviewer_membership_at_review"] == "NOT_AVAILABLE_IN_PROJECTION"
    p["workpapers"][0]["versions"].append({"version": 2, "actor": "A", "evidence_ids": ["A1"]})
    current = summarize(p)["controls"][0]
    assert not current["reviews"][0]["targets_latest_version"]
    assert "NO_CURRENT_DISTINCT_CONTRIBUTOR_REVIEW_RECORD" in {
        r["code"] for r in current["reasons"]
    }
    p["reviews"][0]["actor"] = "A"
    assert (
        summarize(p)["controls"][0]["reviews"][0]["contributor_identity_comparison"]
        == "SAME_CONTRIBUTOR"
    )


def test_source_digest_mismatch_missing_links_and_provisional_are_separate():
    p = projection()
    p["artifacts"][0]["sha256"] = "b" * 64
    p["workpapers"] = [
        {"id": "W1", "control_id": "C1", "versions": [{"version": 1, "evidence_ids": ["ABSENT"]}]}
    ]
    c = summarize(p)["controls"][0]
    assert c["recorded_source_warnings"][0]["reason"] == "SOURCE_RECEIPT_DIGEST_MISMATCH"
    assert c["missing_artifact_links"][0]["artifact_id"] == "ABSENT"
    assert c["populations"][0]["recorded_status"] == "PROVISIONAL"


def test_only_authorized_projection_is_requested_and_modes_or_hidden_prose_do_not_change_report():
    p = projection()
    calls = []
    engine = SimpleNamespace(get=lambda actor, eid: calls.append((actor, eid)) or p)
    result = report(engine, "USER", "E1")
    assert calls == [("USER", "E1")]
    other = deepcopy(p)
    other["mode"] = "CLEAN"
    other["private_key"] = {"answer": "FAIL"}
    other["notes"] = [{"text": "Everything is wrong"}]
    assert summarize(other) == result

    def denied(*args):
        raise DomainError("Denied", status=403)

    with pytest.raises(DomainError):
        report(SimpleNamespace(get=denied), "USER", "E1")


def test_unknown_review_identity_remains_unknown_and_duplicate_ids_rejected():
    p = projection()
    p["workpapers"] = [{"id": "W1", "control_id": "C1", "versions": [{"version": 1}]}]
    p["reviews"] = [{"id": "RV", "workpaper_id": "W1", "kind": "HUMAN", "workpaper_version": None}]
    assert summarize(p)["controls"][0]["reviews"][0]["contributor_identity_comparison"] == "UNKNOWN"
    p["controls"].append(p["controls"][0])
    with pytest.raises(DomainError):
        summarize(p)


def test_recorded_forecast_and_source_clock_qualifiers_are_preserved_without_prose_inference():
    p = projection()
    fields = {
        "classification": "CONDITIONAL_FORECAST",
        "forecast_status": "PLANNING_ONLY",
        "model_version": "example-v1",
        "event_time_state": "UNKNOWN_MONTHLY_SNAPSHOT",
        "source_period_start": "2027-01-01",
        "source_period_end": "2027-01-31",
        "availability_basis": "UTC month-close release rule",
    }
    p["artifacts"][0]["source"]["receipt"]["source"]["provenance"] = fields
    values = summarize(p)["controls"][0]["sources"][0]["qualifiers"]
    assert all({"field": k, "value": v} in values for k, v in fields.items())
    p["artifacts"][0]["unrelated_description"] = "Production completed and audited"
    assert summarize(p)["controls"][0]["sources"][0]["qualifiers"] == values


def test_documentary_custody_qualifiers_remain_explicit_and_do_not_assert_operation():
    p = projection()
    provenance = {
        "custody_status": "PROVISIONAL_DOCUMENTARY_CUSTODY",
        "custody_basis": "CURRENT_SCOPED_PRIMARY_OWNER_NOT_HISTORICAL_SYSTEM_OWNERSHIP",
        "operational_fact_status": "REQUIRES_SOURCE_RECONCILIATION",
    }
    p["artifacts"][0]["source"]["receipt"]["source"]["provenance"] = provenance
    result = summarize(p)["controls"][0]
    assert all(
        {"field": key, "value": value} in result["sources"][0]["qualifiers"]
        for key, value in provenance.items()
    )
    assert result["control_effectiveness"] == "NOT_ASSESSED"
    assert result["sources"][0]["current_source_freshness"] == "UNKNOWN_NOT_QUERIED"
