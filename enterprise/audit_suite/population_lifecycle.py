"""Observable-source population revisions, reliability decisions and native exports."""

from __future__ import annotations

from dataclasses import asdict, replace

from . import populations
from .artifacts import render
from .store import DomainError, canonical, identifier

COMMANDS = {
    "population.assess",
    "population.revise",
    "population.export",
    "selection.export",
    "selection.dispositions",
}


def required(payload: dict, field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise DomainError("Required: " + field.replace("_", " "))
    return value


def record(state: dict, collection: str, row_id: str) -> dict:
    matches = [r for r in state[collection] if r["id"] == row_id]
    if len(matches) != 1:
        raise DomainError("The referenced record is unavailable in this engagement")
    return matches[0]


def population(row: dict) -> populations.Population:
    return populations.Population(
        **{**row["immutable"], "records_json": tuple(row["immutable"]["records_json"])}
    )


def selection(row: dict) -> populations.Selection:
    data = row["immutable"]
    return populations.Selection(
        **{
            **data,
            "selected_ids": tuple(data["selected_ids"]),
            "targeted_ids": tuple(data["targeted_ids"]),
        }
    )


def handle(state: dict, kind: str, payload: dict, stamped: dict, artifacts) -> None:
    """Called within the engine's authorized command transaction.

    Every version has a distinct API record ID and an explicit stable family ID.
    Selections keep their original population digest and reliability decision.
    No operation receives or consults a private expected population.
    """
    if kind not in COMMANDS:
        raise DomainError("Unknown population lifecycle command")
    selected = None
    if kind.startswith("selection."):
        selected = selection(record(state, "selections", payload.get("selection_id")))
        row = record(state, "populations", selected.population_id)
    else:
        row = record(state, "populations", payload.get("population_id"))
    previous = population(row)
    if selected:
        populations.validate_selection(previous, selected)
    if kind == "population.assess":
        status = payload.get("status")
        if status not in populations.STATUSES:
            raise DomainError("Unknown population reliability decision")
        purpose, rationale = required(payload, "purpose"), required(payload, "rationale")
        refs = payload.get("observable_artifact_ids", [])
        if not isinstance(refs, list) or not refs or any(not isinstance(r, str) for r in refs):
            raise DomainError("A reliability decision requires observable source artifacts")
        for ref in refs:
            if record(state, "artifacts", ref)["status"] != "AVAILABLE":
                raise DomainError("A quarantined artifact cannot support population reliability")
        source = {
            **previous.source,
            "reliability_purpose": purpose,
            "reliability_rationale": rationale,
            "reliability_actor": stamped["actor"],
            "observable_source_ref": ", ".join(refs),
        }
        revised = replace(
            previous,
            id=identifier("POP"),
            version=previous.version + 1,
            source_json=canonical(source),
            status=status,
            predecessor_digest=previous.sha256,
            revision_rationale=rationale,
        )
    elif kind == "population.revise":
        artifact = record(state, "artifacts", payload.get("artifact_id"))
        if artifact["status"] != "AVAILABLE":
            raise DomainError("A quarantined artifact cannot supply a population revision")
        source = payload.get("source", {})
        revised = populations.revise_population(
            previous,
            payload.get("rows", []),
            source={**source, "original_sha256": artifact["sha256"]},
            rationale=required(payload, "rationale"),
        )
        revised = replace(revised, id=identifier("POP"))
    elif kind == "selection.dispositions":
        dispositions = payload.get("dispositions", {})
        for item in dispositions.values():
            for artifact_id in item.get("artifact_ids", []):
                if record(state, "artifacts", artifact_id)["status"] != "AVAILABLE":
                    raise DomainError("Delivered support must reference an available artifact")
        manifest = populations.response_manifest(previous, selected, dispositions)
        state.setdefault("sample_responses", []).append(
            {"id": identifier("SRESP"), "selection_id": selected.id, **manifest, **stamped}
        )
        return
    else:
        chosen = set(selected.all_ids) if selected else set(previous.ids)
        rows = [dict(r) for r in previous.rows if r["id"] in chosen]
        if selected:
            for r in rows:
                r["selection_basis"] = "TARGETED" if r["id"] in selected.targeted_ids else "SAMPLED"
        columns = list(dict.fromkeys(k for r in rows for k in r)) or ["id"]
        data, _ = render(
            {
                "format": "csv",
                "columns": columns,
                "rows": [{k: r.get(k, "") for k in columns} for r in rows],
            }
        )
        manifest = artifacts.retain(
            state["id"],
            (selected.id if selected else previous.id) + ".csv",
            data,
            source={
                "kind": "LEARNER_POPULATION_EXPORT",
                "population_digest": previous.sha256,
                "selection_digest": selected.sha256 if selected else None,
            },
            coverage=previous.scope,
            generated=True,
        )
        state["artifacts"].append({**manifest, "received_at": state["simulated_at"]})
        return
    state["populations"].append(
        {
            **row,
            "id": revised.id,
            "family_id": row.get("family_id", previous.id),
            "predecessor_id": previous.id,
            "version": revised.version,
            "immutable": asdict(revised),
            "rows": list(revised.rows),
            "count": len(revised.rows),
            "status": revised.status,
            "artifact_id": payload.get("artifact_id", row.get("artifact_id")),
            **stamped,
        }
    )
