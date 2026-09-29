"""Compose authored disclosure behaviors over the same immutable source records."""

from copy import deepcopy

from .configuration import percent
from .corpus import bind_tokens
from .store import DomainError, digest


def overlay(plan: dict, entry: dict, control: dict, scope: dict, people: dict) -> dict:
    definition = entry["definition"]
    contract = definition["binding_contract"]["portable_behavior"]
    if contract["mode"] != "BEHAVIOR_OVERLAY":
        raise DomainError("Unsupported behavior composition mode")
    value = percent(entry.get("parameters", {}).get("intensity", 50), "intensity")
    if not value:
        return plan
    anchors = contract["anchors"]
    if [a["at"] for a in anchors] != [0, 25, 50, 75, 100]:
        raise DomainError("Behavior overlay requires all intensity anchors")
    anchor = next(a for a in anchors if a["at"] >= value)
    rounds, delay = anchor["minimum_followups"], anchor["delay_business_days"]
    if (
        type(rounds) is not int
        or not 1 <= rounds <= 5
        or type(delay) is not int
        or not 0 <= delay <= 30
    ):
        raise DomainError("Behavior overlay exceeds finite interaction bounds")
    requirements = contract["source_requirements"]
    required = set(requirements.get("required_fields", []))
    result = deepcopy(plan)

    def compatible(request):
        coverage = request.get("coverage", {})
        fields = requirements.get("required_request_coverage", [])
        if any(not coverage.get(f) for f in fields):
            return False
        if fields and (
            coverage.get("control_id") != control["id"]
            or coverage.get("boundary_id") != scope["boundary_id"]
        ):
            return False
        return any(
            required <= set(a["recipe"].get("columns", []))
            and all(
                a.get(k) is not None for k in requirements.get("required_artifact_metadata", [])
            )
            for a in request["artifact_recipes"]
        )

    chosen = next(
        (
            request
            for request in sorted(result["requests"], key=lambda r: "scenario_definition" not in r)
            if compatible(request)
        ),
        None,
    )
    if chosen is None:
        raise DomainError(
            "Behavior overlay has no compatible retained source", code="SOURCE_NOT_APPLICABLE"
        )
    assignment = control["assignment"]
    bindings = {
        "owner": people[assignment["primary_person_id"]],
        "control_id": control["id"],
        "artifact_title": chosen["title"],
        "boundary": scope["boundary_id"],
    }
    behavior_id = "BEHAVIOR-" + digest([definition["id"], control["id"], scope["boundary_id"]])[:24]
    events = deepcopy(chosen.get("scenario_definition", {}).get("events", []))
    if not events:
        releases = []
        for index, artifact in enumerate(chosen["artifact_recipes"]):
            artifact_id = behavior_id + f"-SOURCE-{index}"
            artifact.update(scenario_artifact_id=artifact_id, stage="FOLLOWUP")
            releases.append({"operation": "release_artifact", "target": artifact_id})
        events.append(
            {
                "id": behavior_id + "-SOURCE",
                "trigger": "FOLLOWUP",
                "offset_business_days": delay,
                "minimum_followups": rounds,
                "effects": releases,
            }
        )
    else:
        # All active disclosure impediments must clear. Parallel clarification
        # needs use the largest gate, not a fabricated sequence of approvals.
        separate = []
        for event in events:
            if any(e["operation"] == "release_artifact" for e in event["effects"]):
                historical = [
                    e
                    for e in event["effects"]
                    if e["operation"] in {"scope_change", "record_change"}
                ]
                if historical:
                    separate.append(
                        {**deepcopy(event), "id": event["id"] + "-HISTORY", "effects": historical}
                    )
                    event["effects"] = [e for e in event["effects"] if e not in historical]
                event["trigger"] = "FOLLOWUP"
                event["minimum_followups"] = max(event.get("minimum_followups", 0), rounds)
                event["offset_business_days"] = max(event["offset_business_days"], delay)
        events.extend(separate)
    initial = bind_tokens(contract["initial_statement"], bindings)
    followup = bind_tokens(contract["followup_statement"], bindings)
    events.extend(
        [
            {
                "id": behavior_id + "-NOTICE",
                "trigger": "REQUEST",
                "offset_business_days": 0,
                "effects": [
                    {"operation": "statement", "target": bindings["owner"], "value": initial}
                ],
            },
            {
                "id": behavior_id + "-CLARIFIED",
                "trigger": "FOLLOWUP",
                "offset_business_days": delay,
                "minimum_followups": rounds,
                "effects": [
                    {"operation": "statement", "target": bindings["owner"], "value": followup}
                ],
            },
        ]
    )
    prior = chosen.get("scenario_definition", {})
    chosen["scenario_definition"] = {
        **prior,
        "id": "COMPOSED-" + digest([prior.get("id"), behavior_id])[:24],
        "events": events,
        "behavior_overlays": [
            *prior.get("behavior_overlays", []),
            {
                "template_id": definition["id"],
                "intensity": str(value),
                "minimum_followups": rounds,
                "delay_business_days": delay,
                "professional_validation": "UNVALIDATED",
            },
        ],
    }
    result.setdefault("scenario_cases", []).append(
        {
            "template_id": definition["id"],
            "composition_role": "BEHAVIOR_OVERLAY",
            "affected_request_id": chosen["id"],
            "contract_digest": digest(contract),
        }
    )
    result.setdefault("actor_knowledge", []).append(
        {
            "person_id": assignment["primary_person_id"],
            "available_by": chosen["available_by"],
            "summary": initial,
            "beliefs": [],
        }
    )
    return result
