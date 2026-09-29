"""Bounded metadata reconciliation of authorized, author-recorded procedure traces.

No original reads, hidden data, effectiveness judgments or workflow mutations.
"""

from collections import Counter, defaultdict

from .population_lifecycle import population, selection
from .populations import STATUSES as POPULATION_STATUSES
from .sample_execution import STATUSES, input_pins
from .store import DomainError, canonical, digest

MAX_TRACES = 2000
MAX_ITEMS = 20000
MAX_BYTES = 32 * 1024 * 1024


def require(value, code):
    if not value:
        raise ValueError(code)


def ref(kind, identifier, sha256, version=None):
    return {"kind": kind, "id": identifier, "version": version, "sha256": sha256}


def empty(status="NO_RECORDED_TRACES"):
    return {
        "status": status,
        "trace_count": 0 if status == "NO_RECORDED_TRACES" else None,
        "traces": [],
        "lineages": [],
        "current_leaf_count": 0 if status == "NO_RECORDED_TRACES" else None,
        "current_leaf_item_status_counts": {} if status == "NO_RECORDED_TRACES" else None,
        "count_basis": "CURRENT_LEAF_RECORDED_OBSERVATIONS_NOT_UNIQUE_BUSINESS_ITEMS",
        "automatic_testing_credit": False,
        "completeness_accuracy": "NOT_ESTABLISHED_BY_TRACE_REPORT",
        "original_byte_recheck": "NOT_PERFORMED",
        "independent_review": "NOT_ESTABLISHED_BY_TRACE_REPORT",
    }


def _trace(state, row, indexes):
    tasks, selections, versions, artifacts = indexes
    require(
        row.get("assertion_origin") == "AUTHOR_RECORDED_PROCEDURE_OBSERVATION"
        and row.get("automatic_testing_credit") is False
        and isinstance(row.get("actor"), str)
        and bool(row["actor"]),
        "INVALID_AUTHOR_RECORD_METADATA",
    )
    for field in ("task_id", "population_id", "selection_id", "workpaper_id"):
        require(isinstance(row.get(field), str), "MALFORMED_REFERENCE")
    task = tasks.get(row["task_id"])
    chosen = selections.get(row["selection_id"])
    require(task is not None and chosen is not None, "SCOPED_REFERENCE_UNAVAILABLE")
    require(row.get("task_digest") == task["task_digest"], "TASK_PIN_CHANGED")
    require(type(row.get("workpaper_version")) is int, "MALFORMED_WORKPAPER_VERSION")
    paper = versions.get((row["workpaper_id"], row["workpaper_version"]))
    require(
        paper is not None
        and row.get("workpaper_digest") == paper["workpaper_digest"]
        and row["task_id"] in paper["task_ids"],
        "WORKPAPER_PIN_UNAVAILABLE",
    )
    require(
        all(
            row.get(k) == chosen[k]
            for k in ("population_id", "population_digest", "selection_digest")
        )
        and task["boundary_id"] == chosen["boundary_id"],
        "POPULATION_SELECTION_PIN_UNAVAILABLE",
    )
    require(
        row.get("scope_digest") == digest(state["scope"])
        and digest(row.get("scope")) == row.get("scope_digest")
        and digest(row.get("company_source_binding")) == digest(state.get("company_source_binding"))
        and digest(row.get("evidence_acquisition")) == digest(state.get("evidence_acquisition")),
        "SOURCE_OR_SCOPE_CONTEXT_CHANGED",
    )
    pop = population(next(p for p in state["populations"] if p["id"] == row["population_id"]))
    selected = selection(next(s for s in state["selections"] if s["id"] == row["selection_id"]))
    native_items = {item["id"]: item for item in pop.rows}
    counts, seen, evidence = Counter(), set(), {}
    require(isinstance(row.get("items"), list) and 1 <= len(row["items"]) <= 500, "INVALID_ITEMS")
    for item in row["items"]:
        require(isinstance(item, dict), "INVALID_ITEM")
        identifier = item.get("item_id")
        status = item.get("status")
        require(
            isinstance(identifier, str)
            and identifier not in seen
            and identifier in selected.all_ids,
            "ITEM_OUTSIDE_EXACT_SELECTION",
        )
        require(item.get("item_digest") == digest(native_items[identifier]), "ITEM_PIN_CHANGED")
        require(isinstance(status, str) and status in STATUSES, "INVALID_OBSERVATION_STATUS")
        require(
            item.get("selection_basis")
            == ("TARGETED" if identifier in selected.targeted_ids else "SAMPLED"),
            "ITEM_SELECTION_BASIS_CHANGED",
        )
        require(
            isinstance(item.get("observation"), str) and bool(item["observation"].strip()),
            "MISSING_RECORDED_OBSERVATION",
        )
        refs = item.get("evidence")
        require(isinstance(refs, list) and len(refs) <= 20, "INVALID_EVIDENCE")
        require(
            status in {"NOT_PERFORMED", "SUPPORT_UNAVAILABLE"} or refs,
            "OBSERVATION_WITHOUT_SUPPORT",
        )
        locator_pins = set()
        for original in refs:
            require(
                isinstance(original, dict)
                and set(original) == {"artifact_id", "sha256", "locator"},
                "INVALID_EVIDENCE",
            )
            require(
                isinstance(original["locator"], str) and 0 < len(original["locator"]) <= 1000,
                "INVALID_EVIDENCE_LOCATOR",
            )
            locator_pin = canonical(original)
            require(locator_pin not in locator_pins, "DUPLICATE_EVIDENCE_LOCATOR")
            locator_pins.add(locator_pin)
            aid = original.get("artifact_id")
            require(isinstance(aid, str), "INVALID_EVIDENCE")
            artifact = artifacts.get(aid)
            require(
                artifact is not None and artifact["sha256"] == original.get("sha256"),
                "ARTIFACT_PIN_UNAVAILABLE",
            )
            evidence[aid] = ref("artifact", aid, artifact["sha256"])
        counts[status] += 1
        seen.add(identifier)
    require(type(row.get("revision")) is int and row["revision"] >= 1, "INVALID_TRACE_REVISION")
    require(
        isinstance(row.get("population_status"), str)
        and row["population_status"] in POPULATION_STATUSES
        and type(row.get("selection_provisional")) is bool,
        "RECORDED_RELIABILITY_PIN_CHANGED",
    )
    return {
        "id": row["id"],
        "digest": digest(row),
        "revision": row["revision"],
        "status": "EXACT_VISIBLE_METADATA_LINKS",
        "reason_codes": [],
        "exact_refs": [
            ref("task", row["task_id"], row["task_digest"]),
            ref("population", pop.id, pop.sha256, pop.version),
            ref("selection", selected.id, selected.sha256),
            ref(
                "workpaper", row["workpaper_id"], row["workpaper_digest"], row["workpaper_version"]
            ),
            *evidence.values(),
        ],
        "recorded_item_status_counts": dict(counts),
        "selected_item_count": len(selected.all_ids),
        "items_with_no_recorded_observation_count": len(set(selected.all_ids) - seen),
        "population_reliability": {
            "recorded_status": row["population_status"],
            "selection_provisional": row["selection_provisional"],
            "current_population_status": pop.status,
            "current_selection_provisional": selected.provisional,
            "recorded_qualifiers_match_current_pins": row["population_status"] == pop.status
            and row["selection_provisional"] == selected.provisional,
            "decision_basis": "RECORDED_ASSERTION_NOT_INDEPENDENTLY_VERIFIED",
            "independent_denominator": "NOT_ESTABLISHED",
            "corroboration": "NOT_ASSESSED",
        },
        "period_qualification": {
            "declared_population_scope": pop.scope,
            "source_query": pop.source.get("query"),
            "completeness_representation": pop.source.get("completeness_representation"),
            "basis": "RECORDED_POPULATION_DECLARATIONS_NOT_PERIOD_COMPLETENESS",
        },
    }


def summarize(state):
    """Consume only a caller-authorized Engine projection, never storage or credentials."""
    tasks = state.get("tasks", [])
    by_task = {
        t["id"]: empty() for t in tasks if isinstance(t, dict) and isinstance(t.get("id"), str)
    }
    result = {"status": "AVAILABLE", "by_task": by_task, "unavailable_count": 0}
    rows = state.get("sample_executions", [])
    try:
        require(isinstance(rows, list) and len(rows) <= MAX_TRACES, "INPUT_LIMIT_OR_SHAPE")
        total_items = total_bytes = 0
        for row in rows:
            require(
                isinstance(row, dict) and isinstance(row.get("id"), str), "INPUT_LIMIT_OR_SHAPE"
            )
            require(isinstance(row.get("items"), list), "INPUT_LIMIT_OR_SHAPE")
            total_items += len(row["items"])
            require(total_items <= MAX_ITEMS, "INPUT_LIMIT_OR_SHAPE")
            raw = canonical(row).encode()
            total_bytes += len(raw)
            require(len(raw) <= 1024 * 1024 and total_bytes <= MAX_BYTES, "INPUT_LIMIT_OR_SHAPE")
        pins = input_pins({**state, "sample_executions": []})
        require(
            pins["status"] in {"AVAILABLE", "ENGAGEMENT_NOT_ACTIVE"}, "REFERENCE_INDEX_UNAVAILABLE"
        )
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        return {
            "status": "INPUT_UNAVAILABLE",
            "by_task": {tid: empty("INPUT_UNAVAILABLE") for tid in by_task},
            "unavailable_count": None,
        }
    indexes = (
        {r["task_id"]: r for r in pins["tasks"]},
        {r["selection_id"]: r for r in pins["selections"]},
        {(r["workpaper_id"], r["workpaper_version"]): r for r in pins["workpaper_versions"]},
        {r["artifact_id"]: r for r in pins["artifacts"]},
    )
    identities = Counter(r["id"] for r in rows)
    row_by_id = {r["id"]: r for r in rows}
    children = defaultdict(list)
    for row in rows:
        parent = row.get("predecessor_id")
        if isinstance(parent, str):
            children[parent].append(row["id"])
    analyzed = {}
    for row in rows:
        try:
            require(identities[row["id"]] == 1, "AMBIGUOUS_TRACE_IDENTITY")
            analyzed[row["id"]] = _trace(state, row, indexes)
        except (
            ValueError,
            TypeError,
            KeyError,
            DomainError,
            StopIteration,
            OverflowError,
        ) as error:
            code = (
                str(error)
                if isinstance(error, ValueError)
                else "MALFORMED_OR_UNAVAILABLE_REFERENCE"
            )
            analyzed[row["id"]] = {
                "id": row["id"],
                "status": "UNAVAILABLE",
                "reason_codes": [
                    code
                    if code.isupper() and len(code) < 100
                    else "MALFORMED_OR_UNAVAILABLE_REFERENCE"
                ],
            }
    groups = defaultdict(list)
    for row in rows:
        try:
            cursor, visited = row, set()
            while cursor.get("predecessor_id") is not None:
                require(
                    cursor["id"] not in visited and len(visited) < 64, "CYCLIC_OR_EXCESSIVE_LINEAGE"
                )
                visited.add(cursor["id"])
                parent = row_by_id.get(cursor["predecessor_id"])
                require(
                    parent is not None and identities[parent["id"]] == 1, "PREDECESSOR_UNAVAILABLE"
                )
                require(
                    cursor.get("predecessor_digest") == digest(parent), "PREDECESSOR_PIN_CHANGED"
                )
                require(
                    type(parent.get("revision")) is int
                    and cursor.get("revision") == parent["revision"] + 1,
                    "REVISION_CHAIN_CHANGED",
                )
                require(
                    all(
                        cursor.get(k) == parent.get(k)
                        for k in (
                            "task_id",
                            "selection_id",
                            "selection_digest",
                            "population_id",
                            "population_digest",
                        )
                    ),
                    "CORRECTION_TARGET_CHANGED",
                )
                require(
                    {i["item_id"] for i in cursor["items"]}
                    == {i["item_id"] for i in parent["items"]},
                    "CORRECTION_ITEMS_CHANGED",
                )
                cursor = parent
            require(
                cursor.get("revision") == 1 and type(cursor.get("revision")) is int,
                "ROOT_REVISION_CHANGED",
            )
            require(cursor.get("predecessor_digest") is None, "UNEXPECTED_ROOT_PREDECESSOR_PIN")
            groups[cursor["id"]].append(row["id"])
        except (ValueError, TypeError, KeyError):
            analyzed[row["id"]] = {
                "id": row["id"],
                "status": "UNAVAILABLE",
                "reason_codes": ["CORRECTION_LINEAGE_UNAVAILABLE"],
            }
            groups[row["id"]].append(row["id"])
    for root, members in groups.items():
        members = list(dict.fromkeys(members))
        tid = row_by_id[root].get("task_id")
        if not isinstance(tid, str) or tid not in by_task:
            result["unavailable_count"] += len(members)
            continue
        good = all(
            analyzed[mid]["status"] != "UNAVAILABLE" and len(children[mid]) <= 1 for mid in members
        )
        leaves = [mid for mid in members if not children[mid]]
        good = good and len(leaves) == 1
        by_task[tid]["lineages"].append(
            {
                "root_id": root,
                "current_leaf_id": leaves[0] if good else None,
                "status": "EXACT_VISIBLE_METADATA_LINKS" if good else "UNAVAILABLE",
                "historical_trace_ids": [mid for mid in members if good and mid != leaves[0]],
            }
        )
        by_task[tid]["traces"].extend(analyzed[mid] for mid in members)
    for report in by_task.values():
        report["trace_count"] = len(report["traces"])
        if not report["lineages"]:
            continue
        unavailable = any(g["status"] == "UNAVAILABLE" for g in report["lineages"])
        report["status"] = "UNAVAILABLE" if unavailable else "RECORDED_TRACE_LINKS"
        if unavailable:
            report["current_leaf_count"] = report["current_leaf_item_status_counts"] = None
            result["unavailable_count"] += sum(
                g["status"] == "UNAVAILABLE" for g in report["lineages"]
            )
        else:
            counts = Counter()
            for group in report["lineages"]:
                counts.update(analyzed[group["current_leaf_id"]]["recorded_item_status_counts"])
            report["current_leaf_count"] = len(report["lineages"])
            report["current_leaf_item_status_counts"] = dict(counts)
    if result["unavailable_count"]:
        result["status"] = "PARTIAL_UNAVAILABLE"
    return result
