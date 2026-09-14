from copy import deepcopy

from enterprise.audit_suite.artifacts import render
from enterprise.audit_suite.composition import advance_events
from enterprise.audit_suite.portable_composition import compose


def test_cross_process_projection_releases_actual_source_not_template_records():
    source = {
        "name": "reviews.csv",
        "artifact_kind": "REVIEW_DECISION",
        "recipe": {
            "format": "csv",
            "title": "Scoped change reviews",
            "columns": ["change", "approver"],
            "rows": [{"change": "CHG-73", "approver": "Person Two"}],
        },
    }
    clean = {"requests": [{"id": "R1", "title": "Changes", "artifact_recipes": [source]}]}
    frozen = deepcopy(clean)
    entry = {
        "definition": {
            "id": "TEMPLATE",
            "binding_contract": {
                "portable_evidence_transform": {
                    "kind": "REDACT_FIELDS",
                    "recovery_route": "ACTUAL_SOURCE_RELEASE",
                    "delay_business_days": 1,
                    "initial_response": "{{owner}} supplied a redacted {{artifact_title}}.",
                    "followup_response": "The scoped original is now supplied.",
                    "runtime_binding": {
                        "required_fields": ["change"],
                        "target_fields": ["approver"],
                        "required_artifact_kind": "REVIEW_DECISION",
                    },
                }
            },
        }
    }
    result = compose(
        clean,
        entry,
        {
            "id": "C2",
            "assignment": {
                "primary_person_id": "P1",
                "custodian_person_id": "P2",
            },
        },
        {"boundary_id": "corporate", "period_start": "2027-01-01", "period_end": "2027-12-31"},
        {"P1": "Person One", "P2": "Person Two"},
    )
    request = result["requests"][0]
    initial, followup = request["artifact_recipes"]
    assert b"CHG-73" in render(initial["recipe"])[0]
    assert b"Person Two" not in render(initial["recipe"])[0]
    assert render(followup["recipe"])[0] == render(source["recipe"])[0]
    definition = request["scenario_definition"]
    progress, effects = advance_events(
        definition, None, trigger="REQUEST", now="2028-01-03T09:00:00+00:00", timezone="UTC"
    )
    assert [e["target"] for e in effects if e["operation"] == "release_artifact"] == [
        initial["scenario_artifact_id"]
    ]
    progress, effects = advance_events(
        definition, progress, trigger="FOLLOWUP", now="2028-01-03T09:00:00+00:00", timezone="UTC"
    )
    assert not effects
    _, effects = advance_events(
        definition, progress, trigger="CLOCK", now="2028-01-04T09:00:00+00:00", timezone="UTC"
    )
    assert followup["scenario_artifact_id"] in [e["target"] for e in effects]
    assert clean == frozen
