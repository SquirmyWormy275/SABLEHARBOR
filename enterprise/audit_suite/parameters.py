"""Execute authored slider anchors without inventing causal record changes."""

from copy import deepcopy

from .configuration import percent
from .store import DomainError


def apply(definition: dict, parameters: dict) -> dict:
    result = deepcopy(definition)
    if "count" in parameters:
        from .change_volume import apply as apply_volume

        result = apply_volume(result, parameters["count"])
    selected_type = parameters.get("type")
    if selected_type:
        binding = definition.get("binding_contract", {})
        compatible = (
            binding.get("authority_mode") == selected_type
            if definition["selector_id"] == "MM-13"
            else selected_type in binding.get("compatible_types", [])
        )
        if not compatible:
            raise DomainError(
                "Variant does not implement the selected source, asset or system type"
            )
    contracts = definition.get("parameter_contract", {})
    for dimension in ("intensity", "severity"):
        if dimension not in parameters:
            continue
        value = percent(parameters[dimension], dimension)
        contract = contracts.get(dimension)
        if not contract:
            raise DomainError(
                f"This variant requires authored {dimension} mechanics",
                code="PARAMETER_MECHANICS_REQUIRED",
            )
        anchors = contract.get("anchors", [])
        if [a.get("at") for a in anchors] != [0, 25, 50, 75, 100]:
            raise DomainError("Behavioral anchors must cover 0, 25, 50, 75 and 100")
        anchor = next(a for a in anchors if a["at"] >= value)
        if not isinstance(anchor.get("mechanics"), str) or not anchor["mechanics"].strip():
            raise DomainError("Behavioral anchor requires a concrete causal rationale")
        if "record_set" in anchor:
            from .corpus import validate_variant

            record_set = anchor["record_set"]
            fields = {"facts", "actor_knowledge", "artifacts", "events", "playable_paths", "rubric"}
            if not isinstance(record_set, dict) or set(record_set) != fields:
                raise DomainError("Severity records require a complete causal record set")
            result.update(deepcopy(record_set))
            validate_variant(result)
        events = {e["id"]: e for e in result["events"]}
        for event_id, changes in anchor.get("event_overrides", {}).items():
            if (
                event_id not in events
                or not isinstance(changes, dict)
                or set(changes) - {"offset_business_days", "minimum_followups"}
            ):
                raise DomainError("Unsupported behavioral event override")
            for field, number in changes.items():
                maximum = 5 if field == "minimum_followups" else 30
                if type(number) is not int or not 0 <= number <= maximum:
                    raise DomainError("Behavioral gate exceeds its finite bound")
                if field == "minimum_followups" and events[event_id]["trigger"] != "FOLLOWUP":
                    raise DomainError("Follow-up gates require a follow-up event")
            events[event_id].update(changes)
        if set(anchor) - {"at", "mechanics", "event_overrides", "record_set"}:
            raise DomainError("Behavioral anchor requires an implemented typed adapter")
        result.setdefault("applied_parameters", {})[dimension] = {
            "value": str(value),
            "anchor": anchor["at"],
            "mechanics": anchor["mechanics"],
        }
    return result
