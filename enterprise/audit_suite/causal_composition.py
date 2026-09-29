"""Declared source-packet composition with bounded, typed truth checks.

This does not infer independence from different filenames or model prose. Every
primary owns complete frozen source packets and declares the scope of every
private factual assertion. Requests retain independent event progress; no merged
fictional evidence table or automatic professional coherence claim is produced.
"""

from copy import deepcopy
from datetime import date

from .corpus import bind_tokens
from .store import DomainError, canonical, digest


def conflict(message):
    raise DomainError(message, code="COMPOSITION_CONFLICT")


def _claims(entry, contract, scope):
    claims = contract.get("fact_claims")
    from .parameters import apply as apply_parameters

    effective = apply_parameters(entry["definition"], entry.get("parameters", {}))
    facts = {fact["id"] for fact in effective.get("facts", [])}
    if not isinstance(claims, list) or len(claims) > 200:
        conflict("Each independent packet needs bounded typed fact claims")
    if any(
        not isinstance(claim, dict) or not isinstance(claim.get("fact_id"), str) for claim in claims
    ):
        conflict("Composition fact declarations need string identities")
    if {claim["fact_id"] for claim in claims} != facts:
        conflict("Every private fact must have an explicit composition scope")
    if len(claims) != len(facts):
        conflict("Duplicate or absent factual composition declarations")
    result = []
    for claim in claims:
        if set(claim) != {"fact_id", "subject", "predicate", "value", "valid_from", "valid_to"}:
            conflict("Unknown factual composition fields")
        if any(
            not isinstance(claim[k], str) or not claim[k].strip()
            for k in ("fact_id", "subject", "predicate", "valid_from", "valid_to")
        ):
            conflict("Composition fact identity and dates must be explicit")
        row = bind_tokens(
            claim,
            {
                "period_start": scope["period_start"],
                "period_end": scope["period_end"],
                "control_id": scope["control_id"],
                "boundary": scope["boundary_id"],
            },
        )
        try:
            start, end = date.fromisoformat(row["valid_from"]), date.fromisoformat(row["valid_to"])
            canonical(row["value"])
        except (ValueError, TypeError):
            conflict("Invalid dated factual composition value")
        if start > end:
            conflict("Composition fact interval is reversed")
        result.append({**row, "case_id": entry["definition"]["id"]})
    return result


def source_catalog(clean):
    """Address frozen baseline packets; an address is not evidence of independence."""
    result = {}
    for request in clean["requests"]:
        for index, artifact in enumerate(request["artifact_recipes"]):
            source = (
                artifact.get("source_identity")
                or "BASELINE-" + digest([request["id"], artifact["name"], index])[:24]
            )
            if not isinstance(source, str) or source in result:
                conflict("Frozen baseline source identities must be distinct and explicit")
            rows = artifact["recipe"].get("rows", [])
            record_ids = [str(row.get("record_id", row.get("id", ""))) for row in rows]
            result[source] = {
                "request_id": request["id"],
                "artifact": artifact,
                "record_ids": record_ids,
            }
    return result


def pin_contract(clean, entry, control, scope):
    """Validate instructor-selected packet boundaries and pin current source bytes."""
    contract = deepcopy(entry["definition"]["binding_contract"]["causal_composition"])
    required = {"mode", "source_ids", "fact_claims", "semantic_status"}
    if set(contract) - (required | {"source_pins"}) or not required <= set(contract):
        conflict("Unknown or absent causal composition contract fields")
    if (
        contract["mode"] != "INDEPENDENT_SOURCE_PACKETS"
        or contract["semantic_status"] != "AUTHOR_DECLARED_REQUIRES_COMBINED_REVIEW"
    ):
        conflict("Unknown causal composition mode or semantic status")
    selected = contract["source_ids"]
    if (
        not isinstance(selected, list)
        or not selected
        or any(not isinstance(s, str) for s in selected)
        or len(set(selected)) != len(selected)
    ):
        conflict("Choose distinct existing source packet identities")
    sources = source_catalog(clean)
    if not set(selected) <= sources.keys():
        conflict("An independent case refers to a source absent from the frozen baseline")
    packets = {sources[s]["request_id"] for s in selected}
    if any(v["request_id"] in packets and sid not in selected for sid, v in sources.items()):
        conflict("Independent ownership must cover each complete source packet")
    for sid in selected:
        ids = sources[sid]["record_ids"]
        if not ids or any(not value for value in ids) or len(set(ids)) != len(ids):
            conflict("Independent source packets need stable distinct record IDs")
    _claims(entry, contract, {**scope, "control_id": control["id"]})
    pins = {sid: digest(sources[sid]["artifact"]) for sid in selected}
    if contract.get("source_pins") is not None and contract["source_pins"] != pins:
        conflict("Composition source changed since instructor review")
    contract["source_pins"] = pins
    return contract


def compose(clean, cases, control, scope, people, *, compose_one):
    """Combine explicitly disjoint complete source packets, then retain provenance."""
    if not 2 <= len(cases) <= 20:
        conflict("Independent composition supports two to twenty bounded primaries")
    case_ids = [entry["definition"]["id"] for entry in cases]
    if len(set(case_ids)) != len(case_ids):
        conflict("A primary case cannot be applied twice")
    sources = source_catalog(clean)
    request_sources = {
        request["id"]: {
            sid for sid, value in sources.items() if value["request_id"] == request["id"]
        }
        for request in clean["requests"]
    }
    claimed = set()
    plans = []
    claims = []
    provenance = []
    bindings = {
        "period_start": scope["period_start"],
        "period_end": scope["period_end"],
        "control_id": control["id"],
        "boundary": scope["boundary_id"],
    }
    for entry in cases:
        if "causal_composition" not in entry["definition"].get("binding_contract", {}):
            conflict(
                "Multiple primaries require an explicit independent-source composition contract"
            )
        contract = pin_contract(clean, entry, control, scope)
        selected = bind_tokens(contract["source_ids"], bindings)
        if (
            not isinstance(selected, list)
            or not selected
            or any(not isinstance(value, str) for value in selected)
            or len(set(selected)) != len(selected)
        ):
            conflict("Independent source ownership must list distinct source identities")
        owned = set(selected)
        if not owned <= sources.keys():
            conflict("An independent case refers to a source absent from the frozen baseline")
        if claimed & owned:
            conflict(
                "Two primaries write the same source; an explicit sequential projection is required"
            )
        own_rows = {rid for sid in owned for rid in sources[sid]["record_ids"]}
        prior_rows = {rid for sid in claimed for rid in sources[sid]["record_ids"]}
        if own_rows & prior_rows:
            conflict(
                "Primary packets refer to the same underlying record; "
                "sequential projection required"
            )
        requests = []
        for request in clean["requests"]:
            packet = request_sources[request["id"]]
            if packet & owned:
                # All artifacts must be identified; otherwise a companion clean
                # answer could escape the declared replacement boundary.
                if not packet <= owned or len(packet) != len(request["artifact_recipes"]):
                    conflict("Independent ownership must cover each complete source packet")
                requests.append(deepcopy(request))
        local_claims = _claims(entry, contract, {**scope, "control_id": control["id"]})
        for newer in local_claims:
            for previous in claims:
                if (newer["subject"], newer["predicate"]) == (
                    previous["subject"],
                    previous["predicate"],
                ):
                    overlap = max(newer["valid_from"], previous["valid_from"]) <= min(
                        newer["valid_to"], previous["valid_to"]
                    )
                    if overlap and canonical(newer["value"]) != canonical(previous["value"]):
                        conflict("Simultaneous primary cases assert contradictory shared facts")
        claims.extend(local_claims)
        subset = deepcopy(clean)
        subset["requests"] = requests
        subset["actor_knowledge"] = []
        compiled = compose_one(subset, [entry], control, scope, people)
        plans.append(compiled)
        claimed.update(owned)
        provenance.append(
            {
                "case_id": entry["definition"]["id"],
                "authoring_kind": "CUSTOM"
                if entry["definition"]["id"].startswith("CUSTOM-")
                else "STANDARD",
                "definition_digest": digest(entry["definition"]),
                "parameters_digest": digest(entry.get("parameters", {})),
                "source_ids": sorted(owned),
                "frozen_sources": {sid: digest(sources[sid]["artifact"]) for sid in sorted(owned)},
                "replaced_request_ids": [r["id"] for r in requests],
                "compiled_request_ids": [r["id"] for r in compiled["requests"]],
            }
        )
    result = deepcopy(clean)
    result["baseline_private"] = deepcopy(clean)
    replaced = {rid for row in provenance for rid in row["replaced_request_ids"]}
    result["requests"] = [deepcopy(r) for r in clean["requests"] if r["id"] not in replaced]
    result["scenario_cases"] = []
    result["actor_knowledge"] = []
    for plan in plans:
        result["requests"].extend(deepcopy(plan["requests"]))
        result["scenario_cases"].extend(deepcopy(plan.get("scenario_cases", [])))
        result["actor_knowledge"].extend(deepcopy(plan.get("actor_knowledge", [])))
    ids = [r["id"] for r in result["requests"]]
    if len(set(ids)) != len(ids):
        conflict("Independent source compilation produced overlapping request identities")
    result["causal_composition"] = {
        "version": 1,
        "mode": "INDEPENDENT_SOURCE_PACKETS",
        "cases": provenance,
        "typed_fact_ledger": claims,
        "baseline_digest": digest(clean),
        "independent_request_progress": True,
        "untouched_request_ids": [r["id"] for r in clean["requests"] if r["id"] not in replaced],
        "withheld_unscoped_baseline_knowledge": len(clean.get("actor_knowledge", [])),
        "semantic_status": "AUTHOR_DECLARED_REQUIRES_COMBINED_REVIEW",
        "professional_sufficiency": "NOT_ASSERTED",
    }
    return result
