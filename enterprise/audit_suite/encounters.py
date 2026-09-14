"""Frozen eligible encounter identities for owner/provider frequency allocation."""

from .store import DomainError, digest


def pool(definition: dict, units: list[dict], controls: list[dict], people: list[dict]) -> dict:
    selector = definition["selector_id"]
    contract = definition.get("binding_contract", {}).get("encounter")
    expected = {
        "MM-08": "CONTROL_OWNER_INTERACTION",
        "MM-09": "THIRD_PARTY_REQUEST",
    }.get(selector)
    if not expected or not isinstance(contract, dict) or contract.get("kind") != expected:
        raise DomainError(
            "Frequency requires an authored encounter contract", code="ENCOUNTER_REQUIRED"
        )
    if not isinstance(contract.get("purpose"), str) or not contract["purpose"].strip():
        raise DomainError("Encounter purpose must be explicit")
    if not any(event.get("trigger") == "REQUEST" for event in definition.get("events", [])):
        raise DomainError("Encounter must have an actual initial source-request event")
    artifacts = [
        item["id"] for item in definition.get("artifacts", []) if item["stage"] == "INITIAL"
    ]
    if not artifacts:
        raise DomainError("Encounter must identify its authored initial source packet")
    by_control = {control["id"]: control for control in controls}
    person_ids = {person["id"] for person in people}
    records, excluded = [], []
    for unit in units:
        assignment = by_control[unit["control_id"]]["assignment"]
        custodian = assignment.get("custodian_person_id")
        if custodian not in person_ids:
            raise DomainError("Encounter source custodian is not a scoped person")
        record = {
            "unit": unit,
            "kind": expected,
            "purpose": contract["purpose"],
            "custodian_person_id": custodian,
            "planned_request_id": "CASE-"
            + digest(
                [
                    definition["id"],
                    unit["control_id"],
                    unit["boundary_id"],
                ]
            )[:20],
            "source_definition_digest": digest(definition),
            "initial_source_artifact_ids": artifacts,
            "followup_basis": "FOLLOWUPS_REMAIN_WITHIN_THIS_INITIAL_REQUEST_ENCOUNTER",
        }
        if selector == "MM-08":
            roles = contract.get("participant_roles")
            if roles != ["primary_person_id", "operating_reviewer_person_id"]:
                raise DomainError(
                    "Owner encounter requires explicit operating responsibility roles"
                )
            participants = [assignment.get(role) for role in roles]
            if (
                any(person not in person_ids for person in participants)
                or len(set(participants)) != 2
            ):
                excluded.append(
                    {"unit": unit, "reason": "TWO_DISTINCT_SCOPED_RESPONSIBILITY_HOLDERS_REQUIRED"}
                )
                continue
            record["participants"] = dict(zip(roles, participants, strict=True))
        else:
            provider = contract.get("provider_identity")
            if (
                not isinstance(provider, dict)
                or any(
                    not isinstance(provider.get(key), str) or not provider[key].strip()
                    for key in ("id", "name", "relationship")
                )
                or provider.get("origin") != "AUTHORED_TRAINING_COUNTERPARTY"
            ):
                raise DomainError(
                    "Provider encounter requires an independently identified provider"
                )
            record["provider_identity"] = provider
            record["provider_role"] = (
                "SYNTHETIC_EXTERNAL_PROVIDER_INTERNAL_CUSTODIAN_RELAYS_RESPONSE"
            )
        record["id"] = "ENCOUNTER-" + digest(record)[:24]
        records.append(record)
    return {"basis": expected, "encounters": records, "excluded": excluded}
