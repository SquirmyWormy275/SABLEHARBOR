"""Neutral private-plan binding contracts; no unreleased company answers."""

import hashlib
import json
from datetime import UTC

import pytest

from enterprise.audit_suite.artifacts import inspect_upload, render
from enterprise.audit_suite.clean import build_control, control_contract


@pytest.fixture
def inputs(tmp_path):
    control = {
        "id": "SH-XYZ-001",
        "description": "A neutral activity is reviewed.",
        "evidence_expectation": "review record",
        "frequency": "monthly",
    }
    assignment = {
        "control_id": control["id"],
        "primary_person_id": "person-a",
        "reviewer_person_id": "assurance-person",
        "operating_reviewer_person_id": "person-b",
        "effective_from": "2027-01-01",
    }
    scope = {"boundary_id": "neutral", "period_start": "2027-01-01", "period_end": "2027-12-31"}
    plan = {
        "schema_version": 1,
        "control_contract": control_contract(control),
        "origin": "SYNTHETIC_TRAINING",
        "record_fields": {"owner": "{{owner}}", "amount_usd": 12},
        "occurrences": 12,
        "policy": "Neutral policy",
        "process": "Inspect the record.",
        "walkthrough": "Ask {{owner}} about the record.",
        "coverage_status": "REQUIRES_REVIEW",
        "artifacts": [
            {
                "name": "records.xlsx",
                "format": "xlsx",
                "title": "Neutral records",
                "expectation": "review record",
                "purpose": "Inspection",
                "support_status": "AUTHORED",
            }
        ],
    }
    path = tmp_path / (control["id"] + ".json")
    path.write_text(json.dumps(plan))
    path.chmod(0o600)
    return control, assignment, scope, tmp_path, path, plan


def build(inputs):
    c, a, s, root, _, _ = inputs
    return build_control(c, a, s, private_root=root)


def save(inputs):
    inputs[4].write_text(json.dumps(inputs[5]))


def test_bound_private_plan_has_real_native_artifacts_and_dated_population(inputs):
    result = build(inputs)
    assert len(result["facts"]["records"]) == 12
    assert result["facts"]["records"][0]["owner"] == "person-a"
    assert result["events"][-1]["scheduled_at"] == "2027-12-31T23:59:59.999999+00:00"
    for request in result["requests"]:
        assert request["available_by"] in {"2027-01-01T00:00:00+00:00", "2028-01-01T00:00:00+00:00"}
        for artifact in request["artifact_recipes"]:
            data, mime = render(artifact["recipe"])
            assert data and mime
            assert inspect_upload(artifact["name"], data)
    assert not result["requests"][-1]["coverage"]["independent_external_census"]
    assert result == build(inputs)


@pytest.mark.parametrize(
    "mutation",
    [
        "statement",
        "unsafe_name",
        "token",
        "mode",
        "symlink",
        "historical",
        "future",
        "wrong_control",
        "same_person",
    ],
)
def test_invalid_or_unsafe_binding_rejected(inputs, mutation):
    c, a, _, root, path, plan = inputs
    if mutation == "statement":
        c["description"] = "Changed"
    elif mutation == "unsafe_name":
        plan["artifacts"][0]["name"] = "../private.json"
        save(inputs)
    elif mutation == "token":
        plan["policy"] = "{{unknown}}"
        save(inputs)
    elif mutation == "mode":
        path.chmod(0o644)
    elif mutation == "symlink":
        target = root / "target.json"
        path.rename(target)
        path.symlink_to(target)
    elif mutation == "historical":
        a["status"] = "HISTORICAL_ASSIGNMENT_REQUIRED"
    elif mutation == "future":
        a["effective_from"] = "2028-01-01"
    elif mutation == "wrong_control":
        a["control_id"] = "SH-XYZ-002"
    elif mutation == "same_person":
        a["operating_reviewer_person_id"] = a["primary_person_id"]
    with pytest.raises(ValueError):
        build(inputs)


def test_design_timing_and_owner_names_are_explicit(inputs):
    inputs[5]["artifacts"][0]["timing"] = "DESIGN"
    inputs[2]["owner_names"] = {"person-a": "Neutral Person"}
    save(inputs)
    result = build(inputs)
    assert result["requests"][0]["available_by"] == "2027-01-01T00:00:00+00:00"
    assert result["facts"]["records"][0]["owner"] == "Neutral Person"


def test_pinned_model_source_preserves_strings_and_rejects_wrong_year_or_hash(inputs):
    _, _, scope, root, _, plan = inputs
    path = root / "docs/finance/evidence/neutral.csv"
    path.parent.mkdir(parents=True)
    raw = b"id,amount\n001,12.00\n"
    path.write_bytes(raw)
    plan["source_tables"] = [
        {"path": "docs/finance/evidence/neutral.csv", "sha256": hashlib.sha256(raw).hexdigest()}
    ]
    scope["repository"] = str(root)
    save(inputs)
    result = build(inputs)
    assert result["requests"][-1]["artifact_recipes"][0]["recipe"]["rows"] == [
        {"id": "001", "amount": "12.00"}
    ]
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed"):
        build(inputs)
    path.write_bytes(raw)
    scope["period_end"] = "2028-01-01"
    with pytest.raises(ValueError, match="2027"):
        build(inputs)


def test_source_path_escape_rejected(inputs):
    _, _, scope, root, _, plan = inputs
    (root / "docs/finance/evidence").mkdir(parents=True)
    outside = root / "secret.csv"
    outside.write_text("secret")
    scope["repository"] = str(root)
    plan["source_tables"] = [
        {"path": "secret.csv", "sha256": hashlib.sha256(b"secret").hexdigest()}
    ]
    save(inputs)
    with pytest.raises(ValueError, match="inside repository"):
        build(inputs)


def test_artifact_specific_schema_and_native_recipe_override(inputs):
    plan = inputs[5]
    plan["artifacts"][0]["record_fields"] = {"review_id": "neutral-review", "decision": "recorded"}
    save(inputs)
    result = build(inputs)
    assert "review_id" in result["requests"][1]["artifact_recipes"][0]["recipe"]["columns"]
    assert "amount_usd" not in result["requests"][1]["artifact_recipes"][0]["recipe"]["columns"]
    plan["artifacts"][0]["format"] = "json"
    plan["artifacts"][0]["name"] = "native.json"
    plan["artifacts"][0]["recipe"] = {
        "format": "json",
        "columns": ["native_id", "enabled"],
        "rows": [{"native_id": "neutral", "enabled": False}],
    }
    save(inputs)
    artifact = build(inputs)["requests"][1]["artifact_recipes"][0]
    data, _ = render(artifact["recipe"])
    assert json.loads(data)["records"] == [{"native_id": "neutral", "enabled": False}]


def test_occurrence_cannot_override_bound_scope(inputs):
    inputs[5]["record_fields"]["boundary_id"] = "wrong-boundary"
    save(inputs)
    with pytest.raises(ValueError, match="scope or identity"):
        build(inputs)


def test_month_and_quarter_closes_and_short_scope():
    from datetime import datetime

    from enterprise.audit_suite.clean import occurrence_dates

    start = datetime(2028, 1, 1, tzinfo=UTC)
    end = datetime(2028, 3, 31, 23, 59, 59, 999999, tzinfo=UTC)
    assert [d.date().isoformat() for d in occurrence_dates("monthly", start, end)] == [
        "2028-01-31",
        "2028-02-29",
        "2028-03-31",
    ]
    assert [d.date().isoformat() for d in occurrence_dates("quarterly", start, end)] == [
        "2028-03-31"
    ]
    assert occurrence_dates("annual", start, end) == []
    assert occurrence_dates("on event", start, end) == []
    assert [
        d.day
        for d in occurrence_dates(
            "on event", start, end, planned_dates=["2028-02-03", "2029-01-01"]
        )
    ] == [3]


def test_point_observation_has_no_full_period_population(inputs):
    inputs[2]["period_start"] = inputs[2]["period_end"]
    result = build(inputs)
    assert len(result["facts"]["records"]) == 1
    assert result["temporal_support"] == "POINT_IN_TIME_OBSERVATION_NOT_PERIOD_TOE"
    assert not any(r["id"].endswith("-POP") for r in result["requests"])


def test_source_occurrences_retain_exact_identity_amount_and_filter_scope(inputs):
    inputs[5]["source_occurrences"] = [
        {
            "id": "model-row-001",
            "occurred_at": "2027-02-03T00:00:00Z",
            "fields": {"amount_usd": "123.4500", "source_key": "row-a"},
        },
        {
            "id": "model-row-002",
            "occurred_at": "2028-01-01T00:00:00Z",
            "fields": {"amount_usd": "6.00"},
        },
    ]
    save(inputs)
    result = build(inputs)
    assert len(result["facts"]["records"]) == 1
    record = result["facts"]["records"][0]
    assert record["id"] == "model-row-001" and record["amount_usd"] == "123.4500"
    artifact = result["requests"][1]["artifact_recipes"][0]
    assert artifact["recipe"]["rows"][0]["amount_usd"] == "123.4500"
    inputs[5]["source_occurrences"].append(inputs[5]["source_occurrences"][0])
    save(inputs)
    with pytest.raises(ValueError, match="Duplicate"):
        build(inputs)


@pytest.mark.parametrize("reviewer", [None, "AS-P009", "assurance-custom", "assurance-person"])
def test_operating_review_never_falls_back_to_assurance(inputs, reviewer):
    inputs[1]["operating_reviewer_person_id"] = reviewer
    inputs[2]["internal_audit_person_ids"] = ["assurance-custom"]
    with pytest.raises(ValueError):
        build(inputs)


def test_assurance_reviewer_not_bound_into_business_record(inputs):
    inputs[5]["record_fields"]["operating_reviewer"] = "{{reviewer}}"
    save(inputs)
    result = build(inputs)
    assert result["facts"]["records"][0]["operating_reviewer"] == "person-b"
    assert "assurance-person" not in json.dumps(result)


def test_named_operating_reviewer_cannot_substitute_for_collective_actions(inputs):
    inputs[1]["collective_approval_required"] = True
    with pytest.raises(ValueError, match="Collective approval"):
        build(inputs)


def test_collective_actions_require_downloadable_reconciled_member_votes(inputs):
    inputs[1]["collective_approval_required"] = True
    support = {
        "body_id": "neutral-body",
        "resolution_id": "neutral-resolution",
        "votes": [
            {
                "director_id": "member-1",
                "present": True,
                "eligible": True,
                "recused": False,
                "vote": "FOR",
            },
            {
                "director_id": "member-2",
                "present": True,
                "eligible": True,
                "recused": False,
                "vote": "FOR",
            },
        ],
        "tally": {"eligible_present": 2, "votes_for": 2},
        "meeting_rule": {"required_quorum": 2, "votes_required": 2},
    }
    inputs[5]["collective_decision_support"] = support
    artifact = {
        "name": "member-actions.json",
        "format": "json",
        "title": "Neutral member actions",
        "expectation": "Review collective actions",
        "purpose": "Inspect votes",
        "support_status": "AUTHORED",
        "recipe": {"format": "json", "document": support},
    }
    inputs[5]["artifacts"].append(artifact)
    save(inputs)
    assert build(inputs)["requests"]
    support["votes"][1]["vote"] = "AGAINST"
    save(inputs)
    with pytest.raises(ValueError, match="tally"):
        build(inputs)
    support["tally"]["votes_for"] = 1
    save(inputs)
    with pytest.raises(ValueError, match="meeting rule"):
        build(inputs)
    support["votes"][1]["vote"] = "FOR"
    support["tally"]["votes_for"] = 2
    inputs[5]["artifacts"].pop()
    save(inputs)
    with pytest.raises(ValueError, match="downloadable"):
        build(inputs)


def test_authored_source_classification_stays_on_private_recipe_wrapper(inputs):
    inputs[5]["artifacts"][0].update(
        artifact_kind="NEUTRAL_LOG", source_identity="source-a", source_role="PRIMARY"
    )
    save(inputs)
    result = build(inputs)
    wrapper = next(
        r["artifact_recipes"][0]
        for r in result["requests"]
        if r["artifact_recipes"][0]["name"] == "records.xlsx"
    )
    assert wrapper["artifact_kind"] == "NEUTRAL_LOG"
    assert wrapper["source_identity"] == "source-a" and wrapper["source_role"] == "PRIMARY"
    assert "source_identity" not in wrapper["recipe"] and "artifact_kind" not in wrapper["recipe"]


def test_local_period_bounds_and_population_wait_until_end_day_completes(inputs):
    inputs[2]["timezone"] = "America/Denver"
    result = build(inputs)
    assert result["temporal_bounds"]["start"] == "2027-01-01T00:00:00-07:00"
    assert result["temporal_bounds"]["end"] == "2027-12-31T23:59:59.999999-07:00"
    population = next(r for r in result["requests"] if r["id"].endswith("-POP"))
    assert population["available_by"] == "2028-01-01T00:00:00-07:00"
    assert result["events"][2]["scheduled_at"] == "2027-03-31T23:59:59.999999-06:00"


def test_inclusive_local_end_day_filters_actual_source_instants(inputs):
    inputs[2]["timezone"] = "America/Denver"
    inputs[5]["source_occurrences"] = [
        {"id": "before", "occurred_at": "2027-01-01T06:59:59Z", "fields": {}},
        {"id": "start", "occurred_at": "2027-01-01T07:00:00Z", "fields": {}},
        {"id": "last-day", "occurred_at": "2028-01-01T06:59:59Z", "fields": {}},
        {"id": "after", "occurred_at": "2028-01-01T07:00:00Z", "fields": {}},
    ]
    save(inputs)
    assert [r["id"] for r in build(inputs)["facts"]["records"]] == ["start", "last-day"]


def test_explicit_offset_bounds_are_not_extended_or_reinterpreted(inputs):
    inputs[2].update(
        timezone="America/Denver",
        period_start="2027-01-01T12:30:00+02:00",
        period_end="2027-12-31T17:15:00+02:00",
    )
    bounds = build(inputs)["temporal_bounds"]
    assert bounds["start"] == "2027-01-01T12:30:00+02:00"
    assert bounds["end"] == bounds["complete_available"] == "2027-12-31T17:15:00+02:00"


def test_explicit_single_day_period_and_date_only_point_have_distinct_meanings(inputs):
    inputs[2].update(
        timezone="America/Denver",
        period_start="2027-03-14",
        period_end="2027-03-14",
        temporal_basis="PERIOD",
    )
    period = build(inputs)
    assert period["temporal_bounds"]["start"] == "2027-03-14T00:00:00-07:00"
    assert period["temporal_bounds"]["complete_available"] == "2027-03-15T00:00:00-06:00"
    inputs[2]["temporal_basis"] = "POINT_IN_TIME"
    point = build(inputs)
    assert point["temporal_bounds"]["end"] == "2027-03-14T00:00:00-07:00"
    assert point["temporal_support"] == "POINT_IN_TIME_OBSERVATION_NOT_PERIOD_TOE"
    assert not any(r["id"].endswith("-POP") for r in point["requests"])
