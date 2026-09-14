"""Bind an authored incomplete-evidence mechanism to an actual clean source."""

from copy import deepcopy
from pathlib import Path

from .corpus import bind_tokens
from .evidence_transform import project
from .store import DomainError, digest


def compose(clean: dict, entry: dict, control: dict, scope: dict, people: dict) -> dict:
    definition = entry["definition"]
    contract = definition["binding_contract"].get("portable_evidence_transform", {})
    if not contract.get("runtime_binding"):
        raise DomainError(
            "Portable evidence semantics are not authored", code="SOURCE_ADAPTER_REQUIRED"
        )
    alternatives = {
        artifact["source_role"]: artifact
        for request in clean["requests"]
        for artifact in request["artifact_recipes"]
        if artifact.get("source_role")
    }
    failures = []
    chosen = None
    for request_index, request in enumerate(clean["requests"]):
        for artifact_index, source in enumerate(request["artifact_recipes"]):
            try:
                projection = project(source, contract, alternates=alternatives)
            except DomainError as exc:
                failures.append(str(exc))
                continue
            chosen = request_index, artifact_index, source, projection
            break
        if chosen:
            break
    if chosen is None:
        raise DomainError(
            "No bound source satisfies the selected incomplete-evidence semantics: "
            + "; ".join(sorted(set(failures)))[:350],
            code="SOURCE_NOT_APPLICABLE",
        )
    request_index, artifact_index, source, projection = chosen
    assignment = control["assignment"]
    owner = people[assignment["primary_person_id"]]
    custodian = people[assignment["custodian_person_id"]]
    bindings = {
        "owner": owner,
        "custodian": custodian,
        "control_id": control["id"],
        "artifact_title": source["recipe"].get("title", source["name"]),
        "boundary": scope["boundary_id"],
        "period_start": scope["period_start"],
        "period_end": scope["period_end"],
    }
    initial_text = bind_tokens(contract["initial_response"], bindings)
    followup_text = bind_tokens(contract["followup_response"], bindings)
    case_id = "BOUND-" + digest([definition["id"], source, scope])[0:24]
    plan = deepcopy(clean)
    plan.setdefault("baseline_private", deepcopy(clean))
    request = plan["requests"][request_index]
    available = source.get("available_by", request.get("available_by", scope["period_end"]))
    initial_available = projection["initial_source_private"].get("available_by", available)
    initial_effects = [{"operation": "statement", "target": custodian, "value": initial_text}]
    later_effects = [{"operation": "statement", "target": custodian, "value": followup_text}]
    recipes = []
    for index, artifact in enumerate(request["artifact_recipes"]):
        if index != artifact_index:
            private_id = case_id + f"-COMPANION-{index}"
            recipes.append({**artifact, "scenario_artifact_id": private_id, "stage": "INITIAL"})
            initial_effects.append({"operation": "release_artifact", "target": private_id})
    for stage, recipe in (
        ("INITIAL", projection["initial_recipe"]),
        ("FOLLOWUP", projection["followup_recipe"]),
    ):
        if recipe is None:
            continue
        actual_source = projection["initial_source_private"] if stage == "INITIAL" else source
        source_available = actual_source.get("available_by")
        if actual_source != source and not source_available:
            raise DomainError("Alternate source must declare its actual availability")
        private_id = case_id + "-" + stage
        name = stage.lower() + "-" + Path(source["name"]).stem + "." + recipe["format"]
        recipes.append(
            {
                "name": name,
                "recipe": recipe,
                "scenario_artifact_id": private_id,
                "stage": stage,
                "available_by": source_available or available,
                "source_identity": actual_source.get("source_identity"),
            }
        )
        (initial_effects if stage == "INITIAL" else later_effects).append(
            {
                "operation": "release_artifact",
                "target": private_id,
            }
        )
    bound = {
        "id": case_id,
        "source_template_id": definition["id"],
        "execution_basis": "ACTUAL_BOUND_SOURCE_PROJECTION_NOT_TEMPLATE_RECORD_SUBSTITUTION",
        "events": [
            {
                "id": case_id + "-REQUEST",
                "trigger": "REQUEST",
                "not_before": initial_available,
                "offset_business_days": 0,
                "effects": initial_effects,
            },
            {
                "id": case_id + "-FOLLOWUP",
                "trigger": "FOLLOWUP",
                "not_before": available,
                "offset_business_days": contract["delay_business_days"],
                "effects": later_effects,
            },
        ],
        "source_projection": projection,
        "rubric": {
            "professional_status": "UNVALIDATED",
            "expected_work": "Inspect the supplied source projection, document its precise "
            "coverage limits, request the actual missing source and evaluate all available "
            "support. A missing document alone does not prove failed control operation.",
            "terminal": projection["recovery_route"],
        },
    }
    request["scenario_definition"] = bound
    request["artifact_recipes"] = recipes
    plan.setdefault("scenario_cases", []).append(
        {
            "template_id": definition["id"],
            "bound_definition": bound,
            "affected_request_id": request["id"],
            "source_recipe_digest": projection["source_recipe_digest"],
        }
    )
    plan.setdefault("actor_knowledge", []).append(
        {
            "person_id": assignment["custodian_person_id"],
            "available_by": initial_available,
            "summary": initial_text,
            "beliefs": [],
        }
    )
    return plan
