"""Neutral supporting-source lifecycle and availability contracts."""

from copy import deepcopy

import pytest

from enterprise.audit_suite.artifacts import render
from enterprise.audit_suite.supporting_sources import demonstration_time, requests


def source():
    rows = [
        {
            "id": "DRAFT-1",
            "record_id": "DRAFT-1",
            "boundary_id": "unit-a",
            "occurred_at": "2027-01-01T09:00:00+00:00",
            "lifecycle_state": "DRAFT",
            "record_origin": "AUTHORED_TRAINING_SOURCE",
            "proposed_limit": 45,
            "approved_limit": None,
            "review_comment": "Resolve delegation review comment",
        }
    ]
    return {
        "name": "draft.json",
        "title": "Draft procedure",
        "purpose": "Inspect prior drafting",
        "source_identity": "NATIVE-DRAFT-01",
        "source_role": "DRAFT_PREDECESSOR",
        "artifact_kind": "POLICY_DRAFT",
        "available_by": "2027-01-01T09:00:00+00:00",
        "recipe": {"format": "json", "title": "Draft", "columns": list(rows[0]), "rows": rows},
    }


def test_bound_sources_preserve_original_native_fields_and_provenance():
    original = source()
    frozen = deepcopy(original)
    result = requests([original], control_id="CONTROL-1", boundary_id="unit-a")
    artifact = result[0]["artifact_recipes"][0]
    assert render(artifact["recipe"])[0] == render(original["recipe"])[0]
    assert artifact["source_identity"] == "NATIVE-DRAFT-01"
    assert artifact["recipe"]["rows"][0]["approved_limit"] is None
    artifact["recipe"]["rows"][0]["proposed_limit"] = 99
    assert original == frozen


@pytest.mark.parametrize("mutation", ["current", "same_scope", "future", "duplicate", "origin"])
def test_invalid_supporting_sources_rejected(mutation):
    s = source()
    row = s["recipe"]["rows"][0]
    if mutation == "current":
        row["lifecycle_state"] = "APPROVED"
    elif mutation == "same_scope":
        s["source_role"] = "INDEPENDENT_OTHER_SCOPE"
    elif mutation == "future":
        row["occurred_at"] = "2027-01-02T09:00:00+00:00"
    elif mutation == "duplicate":
        s["recipe"]["rows"].append(deepcopy(row))
    else:
        row["record_origin"] = "PRODUCTION_CONFIRMED"
    with pytest.raises(ValueError):
        requests([s], control_id="CONTROL-1", boundary_id="unit-a")


def test_counterfactual_source_keeps_distinct_boundary():
    s = source()
    s["source_role"] = "INDEPENDENT_OTHER_SCOPE"
    s["recipe"]["rows"][0]["boundary_id"] = "fictional-counterfactual-unit-a"
    actual = requests([s], control_id="CONTROL-1", boundary_id="unit-a")
    assert actual[0]["artifact_recipes"][0]["recipe"]["rows"][0]["boundary_id"] != "unit-a"


def test_demo_is_explicit_scheduled_local_observation_not_request_time():
    scope = {"period_end": "2027-03-12", "timezone": "America/Denver"}
    assert demonstration_time(scope) == "2027-03-15T09:00:00-06:00"
    assert demonstration_time({**scope, "holidays": ["2027-03-15"]}) == (
        "2027-03-16T09:00:00-06:00"
    )
    assert demonstration_time({**scope, "fieldwork_start": "2027-03-12"}) == (
        "2027-03-12T09:00:00-07:00"
    )


def test_demo_fallback_uses_local_date_of_explicit_offset_period_end():
    assert (
        demonstration_time(
            {
                "period_end": "2027-01-03T23:00:00-07:00",
                "timezone": "Asia/Tokyo",
            }
        )
        == "2027-01-05T09:00:00+09:00"
    )
