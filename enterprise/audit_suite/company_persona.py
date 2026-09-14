"""Bounded original company-source context shared by an owner and authorized auditor.

No instructor keys, scenario plans, actor answer banks, or collection mutations.
This is a source sample, never evidence of a complete population or missing records.
"""

import hashlib

from .company_collection import binding
from .company_store import CompanyStoreError
from .review import extract
from .store import DomainError, digest

MAX_RECORDS = 4
MAX_BYTES = 256 * 1024
MAX_CHARACTERS = 12000
MAX_SYSTEMS = 8


def _notice():
    return {
        "id": "COMPANY-SOURCE-BOUNDARY",
        "kind": "COMPANY_SOURCE_LIMITATION",
        "value": {
            "status": "BOUNDED_SOURCE_SAMPLE",
            "population_status": "NOT_POPULATION_COMPLETE",
            "availability": (
                "Only currently authorized original sources may be included; "
                "unavailable support is unknown."
            ),
            "protocol": (
                "Request records through the responsible company source system. "
                "Original records require explicit authorized collection; "
                "no prebuilt evidence arrival is promised."
            ),
            "interpretation": (
                "Preserve synthetic, documentary, forecast, model, proposed "
                "and historical qualifiers. Do not turn a forecast into an "
                "actual result, a company claim into corroboration, or an absent "
                "sample row into a missing approval. A source month is a snapshot period, "
                "not a confirmed occurrence date; when event_at is null, say the event "
                "date is not established rather than asserting when it occurred."
            ),
            "limits": {"records": MAX_RECORDS, "bytes": MAX_BYTES, "characters": MAX_CHARACTERS},
        },
    }


def _authorized_result(engine, actor_id, state, person_id, bound, result):
    """Recheck access after bounded native parsing, before returning model context."""
    try:
        current = engine.store.get(actor_id, state["id"])
        if (
            binding(engine, current) != bound
            or current.get("simulated_at") != state.get("simulated_at")
            or current.get("scope") != state.get("scope")
            or current.get("evidence_acquisition") != "COMPANY_SOURCE_COLLECTION"
            or not any(p.get("id") == person_id for p in current.get("people", []))
        ):
            return [_notice()]
        allowed = engine.company_store.list_systems(
            actor_id, state["id"], bound["company"], bound["branch"]
        )["systems"]
        owned = {system["system"] for system in allowed if system["owner"] == person_id}
        if any(
            item["value"]["system_id"] not in owned
            for item in result
            if item["kind"] == "COMPANY_ORIGINAL_RECORD"
        ):
            return [_notice()]
        return result
    except (CompanyStoreError, DomainError):
        return [_notice()]


def sources(engine, actor_id, state, person_id):
    """Return model source objects; authority and clock are reloaded from durable state."""
    if state.get("evidence_acquisition") != "COMPANY_SOURCE_COLLECTION":
        return []
    result = [_notice()]
    try:
        current = engine.store.get(actor_id, state["id"])
        if current.get("evidence_acquisition") != "COMPANY_SOURCE_COLLECTION":
            return result
        if not any(person.get("id") == person_id for person in current.get("people", [])):
            return result
        bound = binding(engine, current)
        systems = engine.company_store.list_systems(
            actor_id, current["id"], bound["company"], bound["branch"]
        )["systems"]
        systems = [system for system in systems if system["owner"] == person_id][:MAX_SYSTEMS]
        remaining_bytes, remaining_chars, records = MAX_BYTES, MAX_CHARACTERS, 0
        for system in systems:
            page = engine.company_store.list_records(
                actor_id,
                current["id"],
                bound["company"],
                bound["branch"],
                system["system"],
                as_of=current["simulated_at"],
                limit=MAX_RECORDS,
            )
            for item in page["records"]:
                if records >= MAX_RECORDS or remaining_bytes <= 0 or remaining_chars <= 0:
                    return _authorized_result(engine, actor_id, current, person_id, bound, result)
                # Exact read rechecks grants after discovery; no source content is model tooling.
                record = engine.company_store.read_version(
                    actor_id,
                    current["id"],
                    bound["company"],
                    bound["branch"],
                    system["system"],
                    item["record"],
                    version=item["version"],
                    as_of=current["simulated_at"],
                )
                content = record["content"]
                if len(content) > remaining_bytes:
                    continue
                source_id = "COMPANY-" + digest(
                    [bound, system["system"], record["record"], record["version"], record["sha256"]]
                )
                decoded = extract(
                    {
                        "id": source_id,
                        "name": record["provenance"].get("name", "source.json"),
                        "sha256": record["sha256"],
                        "status": "AVAILABLE",
                    },
                    content,
                )
                if decoded["status"] != "EXTRACTED":
                    continue
                rows = []
                for location in decoded["sources"]:
                    text = location["text"]
                    if location.get("text_truncated") or len(text) > remaining_chars:
                        continue  # Never quietly turn a partial sentence into an original claim.
                    rows.append(
                        {
                            "locator": location["locator"],
                            "text": text,
                            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                        }
                    )
                    remaining_chars -= len(text)
                if not rows:
                    continue
                records += 1
                remaining_bytes -= len(content)
                result.append(
                    {
                        "id": source_id,
                        "kind": "COMPANY_ORIGINAL_RECORD",
                        "value": {
                            "system_id": system["system"],
                            "record_id": record["record"],
                            "version": record["version"],
                            "sha256": record["sha256"],
                            "owner_id": person_id,
                            "origin": record["origin"],
                            "event_at": record["event_at"],
                            "available_at": record["available_at"],
                            "imported_at": record["imported_at"],
                            "source_locations": rows,
                            "locations_omitted": len(decoded["sources"]) - len(rows),
                            "qualifiers": {
                                key: record["provenance"][key]
                                for key in (
                                    "classification",
                                    "operational_fact_status",
                                    "model_version",
                                    "forecast_status",
                                    "event_time_state",
                                    "source_period_start",
                                    "source_period_end",
                                    "availability_basis",
                                    "scope_mapping",
                                )
                                if key in record["provenance"]
                            },
                            "population_status": "NOT_POPULATION_COMPLETE",
                        },
                    }
                )
    except (CompanyStoreError, DomainError):
        # Do not disclose which systems or record versions exist behind failed grants.
        return [_notice()]
    return _authorized_result(engine, actor_id, current, person_id, bound, result)
