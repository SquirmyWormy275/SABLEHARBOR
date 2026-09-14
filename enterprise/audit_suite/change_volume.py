"""Expand an authored prefix of distinct change tickets and their original records.

The private pool supplies actual source rows and lifecycle mechanics. This adapter
never invents additional changes by copying a rendered packet or changing a label.
Counts describe change tickets; rollback lifecycle transitions are counted separately.
"""

from copy import deepcopy
from decimal import Decimal, InvalidOperation

from .store import DomainError, digest

ADAPTER = "CHANGE_EVENT_PREFIX_V1"
ROLES = ("initial", "operating", "retest", "test_source")


def apply(definition: dict, count: int) -> dict:
    if type(count) is not int or not 1 <= count <= 100:
        raise DomainError("Change volume requires 1 to 100 actual change events")
    contract = definition.get("parameter_contract", {}).get("count", {})
    if definition.get("selector_id") != "MM-10" or contract.get("adapter") != ADAPTER:
        raise DomainError(
            "This variant needs an authored distinct-change pool",
            code="PARAMETER_MECHANICS_REQUIRED",
        )
    pool = contract.get("episodes", [])
    if len(pool) != 100 or contract.get("source_pool_digest") != digest(pool):
        raise DomainError("Change pool must retain exactly 100 hash-verified source episodes")
    ids, objects, versions = set(), set(), set()
    for episode in pool:
        cid, object_id = episode.get("change_id"), episode.get("affected_object_id")
        if not cid or cid in ids or not object_id or object_id in objects:
            raise DomainError("Change tickets and affected objects must be distinct")
        ids.add(cid)
        objects.add(object_id)
        rows = episode.get("rows", {})
        if set(rows) != set(ROLES):
            raise DomainError(
                "Every change requires original, operating, retest and test-source rows"
            )
        if any(
            row.get("change_id") != cid or row.get("affected_object_id") != object_id
            for row in rows.values()
        ):
            raise DomainError("Change evidence contains a cross-item reference")
        if rows["retest"].get("supporting_source_record") != rows["test_source"].get(
            "source_record"
        ):
            raise DomainError("Retest does not reference its retained original source")
        lifecycle = episode.get("lifecycle", [])
        if len(lifecycle) < 2 or len({step.get("version") for step in lifecycle}) < 2:
            raise DomainError("A change requires actual distinct before/after lifecycle versions")
        offsets = [step.get("effective_business_day_offset") for step in lifecycle]
        if (
            any(type(i) is not int or not 0 <= i <= 30 for i in offsets)
            or offsets != sorted(offsets)
            or len(offsets) != len(set(offsets))
        ):
            raise DomainError("Change lifecycle dates must be strictly ordered and bounded")
        for step in lifecycle:
            versions.add((object_id, step["version"]))
        if (
            rows["operating"].get("old_implementation") != lifecycle[0]["version"]
            or rows["operating"].get("effective_implementation") != lifecycle[-1]["version"]
        ):
            raise DomainError("Native before/after row differs from its lifecycle")
        source = rows["test_source"]
        test = rows["retest"]
        if test.get("inputs") != source.get("source_inputs") or test.get(
            "observed_output"
        ) != source.get("recorded_output"):
            raise DomainError("Retest inputs/results differ from the retained source record")
        if type(source.get("source_available")) is not bool:
            raise DomainError("Source availability requires an explicit boolean")
        if test.get("recorded_result") == "OBSERVED_MATCH" and test.get(
            "expected_output"
        ) != test.get("observed_output"):
            raise DomainError("A mismatched retest cannot be stamped as an observed match")
        if not source.get("source_available") and (
            test.get("recorded_result") != "NOT_RUN" or test.get("observed_output") is not None
        ):
            raise DomainError("Missing source cannot produce a fabricated retest result")
        if (
            type(episode.get("test_offset")) is not int
            or not offsets[-1] <= episode["test_offset"] <= 30
        ):
            raise DomainError("Retest cannot precede the effective implementation")
        if (
            source.get("source_capture_offset") != episode["test_offset"]
            or test.get("performed_business_day_offset") != episode["test_offset"]
        ):
            raise DomainError("Retest and original source timestamps must agree")
        try:
            hours = Decimal(str(episode.get("review_hours", "-1")))
        except InvalidOperation as exc:
            raise DomainError("Invalid change workload") from exc
        if not hours.is_finite() or hours < 0:
            raise DomainError("Change workload must be explicitly nonnegative")
    chosen = deepcopy(pool[:count])
    result = deepcopy(definition)
    artifact_ids = contract.get("artifact_ids", {})
    if set(artifact_ids) != {*ROLES, "reconciliation", "lifecycles"}:
        raise DomainError("Change pool must bind all six native artifacts")
    artifacts = {a["id"]: a for a in result["artifacts"]}
    if not set(artifact_ids.values()) <= artifacts.keys():
        raise DomainError("Change pool references an unknown artifact")
    for role in ROLES:
        rows = [episode["rows"][role] for episode in chosen]
        if any(set(r) != set(rows[0]) for r in rows):
            raise DomainError("Native change source rows need a consistent explicit schema")
        recipe = artifacts[artifact_ids[role]]["recipe"]
        recipe.pop("document", None)
        recipe.update(columns=list(rows[0]), rows=rows)
    unresolved = [
        e["change_id"] for e in chosen if not e["rows"]["test_source"]["source_available"]
    ]
    reconciliation = [
        {
            "request": "INITIAL",
            "source_count": count,
            "delivered_count": count,
            "query": "Selected immutable change-source prefix",
            "distinct_affected_objects": count,
            "retest_sources_available": count - len(unresolved),
            "missing_retest_change_ids": ",".join(unresolved),
        },
        {
            "request": "FOLLOWUP",
            "source_count": count,
            "delivered_count": count,
            "query": "Same selected change IDs and original source version; no replacement census",
            "distinct_affected_objects": count,
            "retest_sources_available": count - len(unresolved),
            "missing_retest_change_ids": ",".join(unresolved),
        },
    ]
    artifacts[artifact_ids["reconciliation"]]["recipe"].update(
        columns=list(reconciliation[0]), rows=reconciliation
    )
    document = {
        "source_pool_digest": contract["source_pool_digest"],
        "selected_change_ids": [e["change_id"] for e in chosen],
        "implementation_lifecycles": [
            {
                "change_id": e["change_id"],
                "affected_object_id": e["affected_object_id"],
                "steps": e["lifecycle"],
                "context": e["mechanism_context"],
            }
            for e in chosen
        ],
        "original_records_preserved": True,
        "origin": "AUTHORED_TRAINING_RECORDS",
    }
    artifacts[artifact_ids["lifecycles"]]["recipe"] = {"format": "json", "document": document}
    event_ids = contract.get("base_event_ids", {})
    events = {e["id"]: e for e in result["events"]}
    if set(event_ids) != {"initial", "followup"} or not set(event_ids.values()) <= events.keys():
        raise DomainError("Change pool requires existing request/follow-up release events")
    initial, followup = events[event_ids["initial"]], events[event_ids["followup"]]
    last_source = max(e["test_offset"] for e in chosen)
    initial["offset_business_days"] = last_source + 1
    followup["offset_business_days"] = 1
    for event in (initial, followup):
        event["effects"] = [e for e in event["effects"] if e["operation"] == "release_artifact"]
    # These are dated company change notices. Native lifecycle dates remain
    # offsets from the scoped period start, not silently rewritten receipt dates.
    notices = []
    for episode in chosen:
        notices.append(
            {
                "id": result["id"] + "-CHANGE-" + episode["change_id"],
                "trigger": "REQUEST",
                "offset_business_days": episode["lifecycle"][-1]["effective_business_day_offset"],
                "effects": [
                    {
                        "operation": "record_change",
                        "target": episode["affected_object_id"],
                        "value": {
                            "change_id": episode["change_id"],
                            "affected_object_id": episode["affected_object_id"],
                            "source_lifecycle": episode["lifecycle"],
                            "source_time_anchor": "scoped_period_start",
                            "requires_scoped_version_reconciliation": True,
                        },
                    }
                ],
            }
        )
    result["events"] = [initial, followup, *notices]
    summary = contract.get("causal_summary")
    if not isinstance(summary, str) or not summary.strip():
        raise DomainError("Change volume requires a case-specific causal explanation")
    factual = (
        f"The company retains {count} distinct change tickets for {count} affected objects. "
        + summary
    )
    for fact in result["facts"]:
        if fact["id"] == "F1":
            fact["statement"] = factual
        if fact["id"] == "F2":
            fact["statement"] = (
                f"Native source and retest records reconcile {count} change IDs; "
                f"{len(unresolved)} have unavailable retest sources. " + summary
            )
    result["rubric"]["supported_conclusions"] = [
        summary,
        "Determine effects from individual lifecycle, approval and retest records; "
        "event volume alone does not establish failure.",
    ]
    for path in result["playable_paths"]:
        path["rationale"] = (
            "Trace the selected change IDs, source versions and scope; "
            "preserve supported alternatives or missing-source limitations."
        )
    result.setdefault("binding_contract", {})["minimum_period_business_days"] = last_source + 3
    result.setdefault("applied_parameters", {})["count"] = {
        "value": count,
        "unit": "distinct change tickets",
        "change_events": len(notices),
        "affected_objects": len({e["affected_object_id"] for e in chosen}),
        "implementation_transitions": sum(len(e["lifecycle"]) - 1 for e in chosen),
        "review_hours": str(sum(Decimal(str(e["review_hours"])) for e in chosen)),
        "source_pool_digest": contract["source_pool_digest"],
        "source_ids": [e["change_id"] for e in chosen],
        "professional_sufficiency": "NOT_ASSERTED",
    }
    return result
