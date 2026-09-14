from copy import deepcopy

from enterprise.audit_suite.artifacts import render
from enterprise.audit_suite.composition import advance_events, compose_control


def test_multiple_behaviors_gate_same_source_without_changing_its_history():
    recipe = {
        "format": "csv",
        "title": "Source",
        "columns": ["record_id"],
        "rows": [{"record_id": "EXISTING-1"}],
    }
    clean = {
        "requests": [
            {
                "id": "R",
                "title": "Source",
                "available_by": "2027-12-31",
                "artifact_recipes": [{"name": "source.csv", "recipe": recipe}],
            }
        ]
    }
    frozen = deepcopy(clean)
    cases = []
    for index in range(2):
        cases.append(
            {
                "parameters": {"intensity": 100},
                "definition": {
                    "id": f"CASE-{index}",
                    "binding_contract": {
                        "portable_behavior": {
                            "mode": "BEHAVIOR_OVERLAY",
                            "initial_statement": "Clarification is needed.",
                            "followup_statement": (
                                "Clarification recorded; source authority is unchanged."
                            ),
                            "source_requirements": {"required_fields": ["record_id"]},
                            "anchors": [
                                {"at": at, "minimum_followups": index + 1, "delay_business_days": 0}
                                for at in [0, 25, 50, 75, 100]
                            ],
                        }
                    },
                },
            }
        )
    result = compose_control(
        clean,
        cases,
        {
            "id": "C1",
            "assignment": {"primary_person_id": "P1"},
        },
        {"boundary_id": "corporate"},
        {"P1": "Owner"},
    )
    request = result["requests"][0]
    assert render(request["artifact_recipes"][0]["recipe"])[0] == render(recipe)[0]
    assert len(request["scenario_definition"]["behavior_overlays"]) == 2
    args = {"now": "2028-01-03T09:00:00+00:00", "timezone": "UTC"}
    state, effects = advance_events(request["scenario_definition"], None, trigger="REQUEST", **args)
    assert not any(e["operation"] == "release_artifact" for e in effects)
    state, effects = advance_events(
        request["scenario_definition"], state, trigger="FOLLOWUP", **args
    )
    assert not any(e["operation"] == "release_artifact" for e in effects)
    _, effects = advance_events(request["scenario_definition"], state, trigger="FOLLOWUP", **args)
    assert len([e for e in effects if e["operation"] == "release_artifact"]) == 1
    assert clean == frozen
