from copy import deepcopy

import pytest

from enterprise.audit_suite.artifacts import render
from enterprise.audit_suite.composition import advance_events, compose_control
from enterprise.audit_suite.corpus import validate_variant
from enterprise.audit_suite.store import DomainError, digest


def fixture(custom=True):
    control = {
        "id": "C1",
        "assignment": {
            "primary_person_id": "P1",
            "custodian_person_id": "P1",
            "operating_reviewer_person_id": "P2",
        },
    }
    scope = {"boundary_id": "unit", "period_start": "2027-01-01", "period_end": "2027-12-31"}
    people = {"P1": "Owner", "P2": "Reviewer"}
    clean = {"requests": [], "actor_knowledge": [{"summary": "Unscoped clean statement"}]}
    cases = []
    for index in range(2):
        source = f"SOURCE-{index}"
        row = f"ROW-{index}"
        fact = f"F-{index}"
        recipe = {
            "format": "csv",
            "title": f"Packet {index}",
            "columns": ["id", "status"],
            "rows": [{"id": row, "status": "original"}],
        }
        clean["requests"].append(
            {
                "id": f"BASE-{index}",
                "title": f"Packet {index}",
                "artifact_recipes": [
                    {"name": f"baseline-{index}.csv", "source_identity": source, "recipe": recipe}
                ],
            }
        )
        artifacts = []
        events = []
        for stage, status in [("INITIAL", "pending"), ("FOLLOWUP", "supported")]:
            aid = f"A-{index}-{stage}"
            artifacts.append(
                {
                    "id": aid,
                    "name": f"{index}-{stage.lower()}.csv",
                    "stage": stage,
                    "available_on": "2027-12-31",
                    "request_purpose": "Inspect this independently scoped record",
                    "recipe": {**deepcopy(recipe), "rows": [{"id": row, "status": status}]},
                }
            )
            events.append(
                {
                    "id": f"E-{index}-{stage}",
                    "trigger": "REQUEST" if stage == "INITIAL" else "FOLLOWUP",
                    "offset_business_days": 0 if stage == "INITIAL" else index + 1,
                    "effects": [{"operation": "release_artifact", "target": aid}],
                }
            )
        definition = {
            "schema_version": "1.0",
            "id": f"CUSTOM-Packet-{index}" if custom else f"MM-11.01.V0{index + 1}",
            "selector_id": "MM-11",
            "option_id": "MM-11.01",
            "title": f"Independent record {index}",
            "disciplines": ["IT"],
            "applicability": {
                "IT": "Neutral process fixture",
                "FINANCIAL": "Not applied in this fixture",
            },
            "mechanism": {
                "cause": "A supporting record is retrieved later",
                "process": "Scoped record review",
                "control_domains": ["C1"],
                "objective": "Distinguish initial status from later source support",
                "failure_type": "DISCLOSURE",
            },
            "facts": [
                {
                    "id": fact,
                    "statement": f"{row} has separate retained support.",
                    "source_class": "SYNTHETIC_SCENARIO_FACT",
                    "visibility": "PRIVATE",
                }
            ],
            "actor_knowledge": [
                {
                    "role_ref": "{{owner}}",
                    "knows_fact_ids": [fact],
                    "allowed_actions": ["respond", "release_artifact"],
                }
            ],
            "artifacts": artifacts,
            "events": events,
            "playable_paths": [
                {
                    "id": "PATH-1",
                    "actions": ["REQUEST", "FOLLOWUP"],
                    "terminal_state": "SUPPORTED_CONCLUSION",
                    "rationale": "Evaluate this record and its exact later support independently.",
                }
            ],
            "rubric": {
                "professional_validation": "UNVALIDATED",
                "supported_conclusions": ["Limited record support"],
                "acceptable_alternatives": ["Document limitation"],
                "unsupported_guesses": ["Infer an unrelated record status"],
            },
            "clean_counterpart": "Baseline source packet",
            "source_refs": [],
            "binding_contract": {
                "applicable_control_ids": ["C1"],
                "causal_composition": {
                    "mode": "INDEPENDENT_SOURCE_PACKETS",
                    "source_ids": [source],
                    "semantic_status": "AUTHOR_DECLARED_REQUIRES_COMBINED_REVIEW",
                    "fact_claims": [
                        {
                            "fact_id": fact,
                            "subject": row,
                            "predicate": "retained_support",
                            "value": True,
                            "valid_from": "{{period_start}}",
                            "valid_to": "{{period_end}}",
                        }
                    ],
                },
            },
        }
        cases.append({"definition": definition, "parameters": {}})
    return clean, cases, control, scope, people


@pytest.mark.parametrize("custom", [False, True])
def test_independent_primary_packets_preserve_sources_events_and_truth(custom):
    args = fixture(custom)
    clean, cases, *_ = args
    frozen = deepcopy(args)
    for entry in cases:
        validate_variant(entry["definition"])
    plan = compose_control(*args)
    assert args == frozen and plan["baseline_private"] == clean
    assert len(plan["requests"]) == 2 and len(plan["scenario_cases"]) == 2
    assert len(plan["causal_composition"]["typed_fact_ledger"]) == 2
    assert {c["authoring_kind"] for c in plan["causal_composition"]["cases"]} == (
        {"CUSTOM"} if custom else {"STANDARD"}
    )
    for index, request in enumerate(plan["requests"]):
        data = render(request["artifact_recipes"][0]["recipe"])[0]
        assert f"ROW-{index}".encode() in data and f"ROW-{1 - index}".encode() not in data
        definition = request["scenario_definition"]
        progress, effects = advance_events(
            definition, None, trigger="REQUEST", now="2028-01-03T09:00:00Z", timezone="UTC"
        )
        assert [e["target"] for e in effects if e["operation"] == "release_artifact"] == [
            f"A-{index}-INITIAL"
        ]
        progress, effects = advance_events(
            definition, progress, trigger="FOLLOWUP", now="2028-01-03T09:00:00Z", timezone="UTC"
        )
        assert not effects
        progress, effects = advance_events(
            definition, progress, trigger="CLOCK", now="2028-01-04T09:00:00Z", timezone="UTC"
        )
        assert bool(effects) == (index == 0)
        assert (
            request["id"] == plan["causal_composition"]["cases"][index]["compiled_request_ids"][0]
        )
        assert plan["causal_composition"]["cases"][index]["frozen_sources"][
            f"SOURCE-{index}"
        ] == digest(clean["requests"][index]["artifact_recipes"][0])
    assert all("Unscoped clean statement" not in k["summary"] for k in plan["actor_knowledge"])


@pytest.mark.parametrize(
    "failure",
    ["overlap", "unknown", "missing_fact", "contradiction", "partial_packet", "missing_contract"],
)
def test_primary_collisions_fail_closed_without_mutating_baseline(failure):
    clean, cases, control, scope, people = fixture()
    contract = cases[1]["definition"]["binding_contract"]["causal_composition"]
    if failure == "overlap":
        contract["source_ids"] = ["SOURCE-0"]
    elif failure == "unknown":
        contract["source_ids"] = ["ABSENT"]
    elif failure == "missing_fact":
        contract["fact_claims"] = []
    elif failure == "contradiction":
        contract["fact_claims"][0].update(subject="ROW-0", value=False)
    elif failure == "partial_packet":
        clean["requests"][0]["artifact_recipes"].append(
            {
                "name": "companion.csv",
                "recipe": deepcopy(clean["requests"][0]["artifact_recipes"][0]["recipe"]),
            }
        )
    else:
        cases[1]["definition"]["binding_contract"].pop("causal_composition")
    frozen = deepcopy(clean)
    with pytest.raises(DomainError) as error:
        compose_control(clean, cases, control, scope, people)
    assert error.value.code == "COMPOSITION_CONFLICT" and clean == frozen


def test_source_pins_reject_changed_original_and_malformed_fact():
    from enterprise.audit_suite.causal_composition import pin_contract

    clean, cases, control, scope, _ = fixture(True)
    entry = cases[0]
    contract = pin_contract(clean, entry, control, scope)
    entry["definition"]["binding_contract"]["causal_composition"] = contract
    clean["requests"][0]["artifact_recipes"][0]["recipe"]["rows"][0]["status"] = "CHANGED"
    with pytest.raises(DomainError, match="source changed"):
        pin_contract(clean, entry, control, scope)
    contract["fact_claims"][0]["fact_id"] = []
    with pytest.raises(DomainError, match="string identities"):
        pin_contract(clean, entry, control, scope)


def test_edited_encounters_resolve_real_scoped_participants():
    from enterprise.audit_suite.custom import validated_encounter

    control = {
        "id": "C1",
        "assignment": {
            "primary_person_id": "P1",
            "operating_reviewer_person_id": "P2",
            "custodian_person_id": "P3",
        },
    }
    state = {
        "scope": {"boundaries": ["corporate"]},
        "people": [{"id": p} for p in ("P1", "P2", "P3")],
    }
    variant = {
        "id": "CUSTOM-demo",
        "selector_id": "MM-08",
        "events": [{"trigger": "REQUEST"}],
        "artifacts": [{"id": "A1", "stage": "INITIAL"}],
        "binding_contract": {
            "encounter": {
                "kind": "CONTROL_OWNER_INTERACTION",
                "participant_roles": ["primary_person_id", "operating_reviewer_person_id"],
                "purpose": "Resolve opposing responsibility holders",
                "require_distinct_participants": True,
            }
        },
    }
    assert validated_encounter(variant, control, state)["kind"] == "CONTROL_OWNER_INTERACTION"
    control["assignment"]["operating_reviewer_person_id"] = "P1"
    with pytest.raises(DomainError, match="resolve"):
        validated_encounter(variant, control, state)
    variant["selector_id"] = "MM-09"
    variant["binding_contract"]["encounter"] = {
        "kind": "THIRD_PARTY_REQUEST",
        "purpose": "Request independently authored provider records",
        "provider_identity": {
            "id": "V1",
            "name": "Synthetic provider",
            "relationship": "Training service vendor",
            "origin": "AUTHORED_TRAINING_COUNTERPARTY",
        },
    }
    assert validated_encounter(variant, control, state)["provider_identity"]["id"] == "V1"
    variant["binding_contract"]["encounter"]["provider_identity"]["origin"] = (
        "INFERRED_FROM_CUSTODIAN"
    )
    with pytest.raises(DomainError, match="independently identified"):
        validated_encounter(variant, control, state)
