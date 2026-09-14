"""Bounded original company-source context shared by an owner and authorized auditor.

No instructor keys, scenario plans, actor answer banks, or collection mutations.
This is a source sample, never evidence of a complete population or missing records.
"""

import hashlib
import re

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
                "sample row into a missing approval. A qualified source portfolio does not "
                "establish a coherent full operating year. Keep each original source identity "
                "and qualification distinct. A source month is a snapshot period, "
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


def sources(engine, actor_id, state, person_id, *, selected_records=None):
    """Return model source objects; authority and clock are reloaded from durable state."""
    if selected_records is not None:
        return _selected_sources(engine, actor_id, state, person_id, selected_records)
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
                            "source_identity": _source_identity(record),
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
                                    "custody_status",
                                    "custody_basis",
                                    "source_authority",
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


def validate_selection(engine, actor_id, state, person_id, selected_records):
    """Reload current authority and exact chosen originals without parsing or mutation."""
    if not isinstance(selected_records, list) or not 1 <= len(selected_records) <= MAX_RECORDS:
        raise DomainError(
            "Choose one to four distinct original source versions", code="INVALID_SOURCE_SELECTION"
        )
    seen = set()
    for pin in selected_records:
        if (
            not isinstance(pin, dict)
            or set(pin) != {"system_id", "record_id", "version", "sha256"}
            or not isinstance(pin["system_id"], str)
            or not 1 <= len(pin["system_id"]) <= 257
            or not isinstance(pin["record_id"], str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", pin["record_id"])
            or type(pin["version"]) is not int
            or pin["version"] < 1
            or not isinstance(pin["sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", pin["sha256"])
        ):
            raise DomainError(
                "Exact typed source version and SHA pins required", code="INVALID_SOURCE_SELECTION"
            )
        identity = (pin["system_id"], pin["record_id"], pin["version"])
        if identity in seen:
            raise DomainError("Duplicate selected source version", code="INVALID_SOURCE_SELECTION")
        seen.add(identity)
    try:
        current = engine.store.get(actor_id, state["id"])
        if current.get("evidence_acquisition") != "COMPANY_SOURCE_COLLECTION" or not any(
            p.get("id") == person_id for p in current.get("people", [])
        ):
            raise CompanyStoreError("Selected company context unavailable")
        bound = dict(binding(engine, current))
        allowed = engine.company_store.list_systems(
            actor_id, current["id"], bound["company"], bound["branch"]
        )["systems"]
        owned = {r["system"] for r in allowed if r["owner"] == person_id}
        records = []
        total = 0
        for pin in selected_records:
            if pin["system_id"] not in owned:
                raise CompanyStoreError("Selected system not owned or authorized")
            record = engine.company_store.read_version(
                actor_id,
                current["id"],
                bound["company"],
                bound["branch"],
                pin["system_id"],
                pin["record_id"],
                version=pin["version"],
                as_of=current["simulated_at"],
            )
            if (
                record["sha256"] != pin["sha256"]
                or hashlib.sha256(record["content"]).hexdigest() != pin["sha256"]
            ):
                raise CompanyStoreError("Selected original changed")
            total += len(record["content"])
            if total > MAX_BYTES:
                raise CompanyStoreError("Selected source byte budget exceeded")
            records.append((dict(pin), record))
        latest = engine.store.get(actor_id, current["id"])
        if (
            binding(engine, latest) != bound
            or latest.get("scope") != current.get("scope")
            or latest.get("simulated_at") != current.get("simulated_at")
            or latest.get("evidence_acquisition") != current.get("evidence_acquisition")
            or not any(p.get("id") == person_id for p in latest.get("people", []))
        ):
            raise CompanyStoreError("Selected company context changed")
        allowed = engine.company_store.list_systems(
            actor_id, current["id"], bound["company"], bound["branch"]
        )["systems"]
        owned = {r["system"] for r in allowed if r["owner"] == person_id}
        if any(pin["system_id"] not in owned for pin in selected_records):
            raise CompanyStoreError("Selected source authority changed")
        return current, bound, records
    except (CompanyStoreError, DomainError) as exc:
        raise DomainError(
            (
                "Selected company source is unavailable, changed, oversized "
                "or outside this contact's authority"
            ),
            code="SOURCE_CONTEXT_UNAVAILABLE",
            status=403,
        ) from exc


def _selected_sources(engine, actor_id, state, person_id, selected_records):
    current, bound, records = validate_selection(
        engine, actor_id, state, person_id, selected_records
    )
    notice = _notice()
    notice["value"]["status"] = "EXPLICIT_SOURCE_SELECTION"
    notice["value"]["selection"] = (
        "Only the exact user-selected originals; no automatic source substitution"
    )
    result, characters = [notice], 0
    for pin, record in records:
        source_id = "COMPANY-" + digest(
            [bound, pin["system_id"], record["record"], record["version"], record["sha256"]]
        )
        decoded = extract(
            {
                "id": source_id,
                "name": record["provenance"].get("name", "source.json"),
                "sha256": record["sha256"],
                "status": "AVAILABLE",
            },
            record["content"],
        )
        rows = []
        if decoded["status"] != "EXTRACTED":
            raise DomainError(
                "Selected original cannot be safely extracted",
                code="SOURCE_CONTEXT_UNAVAILABLE",
                status=422,
            )
        for location in decoded["sources"]:
            text = location["text"]
            characters += len(text)
            if location.get("text_truncated") or characters > MAX_CHARACTERS:
                raise DomainError(
                    "Selected originals exceed context bounds; choose fewer or smaller records",
                    code="SOURCE_CONTEXT_UNAVAILABLE",
                    status=422,
                )
            rows.append(
                {
                    "locator": location["locator"],
                    "text": text,
                    "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                }
            )
        if not rows:
            raise DomainError(
                "Selected original has no extractable source locations",
                code="SOURCE_CONTEXT_UNAVAILABLE",
                status=422,
            )
        result.append(
            {
                "id": source_id,
                "kind": "COMPANY_ORIGINAL_RECORD",
                "value": {
                    "system_id": pin["system_id"],
                    "record_id": record["record"],
                    "version": record["version"],
                    "sha256": record["sha256"],
                    "owner_id": person_id,
                    "origin": record["origin"],
                    "event_at": record["event_at"],
                    "available_at": record["available_at"],
                    "imported_at": record["imported_at"],
                    "source_locations": rows,
                    "locations_omitted": 0,
                    "population_status": "NOT_POPULATION_COMPLETE",
                    "selection_basis": "EXPLICIT_EXACT_SOURCE_VERSION",
                    "source_identity": _source_identity(record),
                    "qualifiers": {
                        k: record["provenance"][k]
                        for k in (
                            "classification",
                            "operational_fact_status",
                            "forecast_status",
                            "model_version",
                            "event_time_state",
                            "source_period_start",
                            "source_period_end",
                            "availability_basis",
                            "custody_status",
                            "custody_basis",
                            "source_authority",
                        )
                        if k in record["provenance"]
                    },
                },
            }
        )
    final, final_bound, _ = validate_selection(engine, actor_id, state, person_id, selected_records)
    if (
        final_bound != bound
        or final.get("scope") != current.get("scope")
        or final.get("simulated_at") != current.get("simulated_at")
    ):
        raise DomainError(
            "Selected company context changed during parsing",
            code="SOURCE_CONTEXT_UNAVAILABLE",
            status=409,
        )
    return result


def _source_identity(record):
    return {
        k: record[k]
        for k in (
            "company",
            "branch",
            "system",
            "record",
            "version",
            "sha256",
            "source_store_id",
            "source_system_alias",
            "registry_sha256",
            "portfolio_qualification",
        )
        if k in record
    }
