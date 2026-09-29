"""Exact recorded historical work associations; no inferred testing or understanding."""

from .company_impact import _reference_guard
from .store import DomainError, digest


def index(state, artifacts):
    """Bound and index once, retaining only explicitly linked work metadata."""
    _reference_guard(state)
    traces = {row["id"]: row for row in state.get("sample_executions", [])}
    successors = {}
    for row in traces.values():
        predecessor = row.get("predecessor_id")
        revision = row.get("revision")
        if type(revision) is not int or revision < 1:
            raise DomainError("Invalid historical execution revision")
        if predecessor is None:
            if revision != 1:
                raise DomainError("Unresolved historical execution predecessor")
        else:
            old = traces.get(predecessor)
            if (
                old is None
                or predecessor in successors
                or type(old.get("revision")) is not int
                or revision != old["revision"] + 1
                or row.get("predecessor_digest") != digest(old)
                or any(
                    row.get(k) != old.get(k)
                    for k in (
                        "task_id",
                        "selection_id",
                        "selection_digest",
                        "population_id",
                        "population_digest",
                        "scope_digest",
                        "company_source_binding",
                        "evidence_acquisition",
                    )
                )
                or {i.get("item_id") for i in row.get("items", [])}
                != {i.get("item_id") for i in old.get("items", [])}
            ):
                raise DomainError("Unresolved historical execution correction")
            successors[predecessor] = row["id"]
    tasks = {t["id"]: t for t in state.get("tasks", [])}
    result = {"sample_executions": [], "findings": [], "remediations": []}
    for row in traces.values():
        linked = set()
        items = []
        seen = set()
        for item in row.get("items", []):
            if not isinstance(item.get("item_id"), str) or item["item_id"] in seen:
                raise DomainError("Ambiguous historical execution item")
            seen.add(item["item_id"])
            pins = [
                e
                for e in item.get("evidence", [])
                if e.get("artifact_id") in artifacts
                and e.get("sha256") == artifacts[e["artifact_id"]]
            ]
            linked.update(e["artifact_id"] for e in pins)
            if pins:
                items.append(
                    {
                        "item_id": item["item_id"],
                        "recorded_status": item.get("status"),
                        "evidence": pins,
                        "locator_validation": "AUTHOR_SUPPLIED_NOT_CONTENT_MATCH_VERIFIED",
                    }
                )
        task = tasks.get(row.get("task_id"))
        result["sample_executions"].append(
            {
                "id": row["id"],
                "version": row["revision"],
                "record_sha256": digest(row),
                "task_id": row.get("task_id"),
                "task_digest": row.get("task_digest"),
                "task_pin_matches_selected_state": bool(
                    task and row.get("task_digest") == digest(task)
                ),
                "workpaper_id": row.get("workpaper_id"),
                "workpaper_version": row.get("workpaper_version"),
                "workpaper_digest": row.get("workpaper_digest"),
                "selection_id": row.get("selection_id"),
                "selection_digest": row.get("selection_digest"),
                "population_id": row.get("population_id"),
                "population_digest": row.get("population_digest"),
                "source_artifact_ids": sorted(linked),
                "matched_items": items,
                "predecessor_id": row.get("predecessor_id"),
                "predecessor_digest": row.get("predecessor_digest"),
                "successor_id": successors.get(row["id"]),
                "trace_status": "HISTORICAL_CORRECTED"
                if row["id"] in successors
                else "CURRENT_LEAF_IN_SELECTED_HISTORY",
                "automatic_testing_credit": False,
            }
        )
    seen_remediations = set()
    for finding in state.get("findings", []):
        linked = sorted(set(finding.get("evidence_ids", [])) & artifacts.keys())
        if linked:
            result["findings"].append(
                {
                    "id": finding["id"],
                    "record_sha256": digest(finding),
                    "source_artifact_ids": linked,
                    "recorded_status": finding.get("status"),
                }
            )
        for row in finding.get("remediations", []):
            if not isinstance(row.get("id"), str) or row["id"] in seen_remediations:
                raise DomainError("Ambiguous historical remediation identity")
            seen_remediations.add(row["id"])
            linked = sorted(set(row.get("evidence_ids", [])) & artifacts.keys())
            if linked:
                result["remediations"].append(
                    {
                        "id": row["id"],
                        "finding_id": finding["id"],
                        "record_sha256": digest(row),
                        "source_artifact_ids": linked,
                        "recorded_status": row.get("status"),
                    }
                )
    return result


def selected(indexed, artifact_ids, task_links):
    tasks = (
        set(task_links["authored_task_ids"])
        if task_links["task_mapping_status"] == "EXPLICIT_AUTHORED_LINKS"
        else set()
    )
    result = {}
    for family, rows in indexed.items():
        selected_rows = []
        for row in rows:
            matched = sorted(set(row["source_artifact_ids"]) & artifact_ids)
            task_match = (
                family == "sample_executions"
                and row["task_id"] in tasks
                and row["task_pin_matches_selected_state"]
            )
            if not matched and not task_match:
                continue
            copied = {**row, "source_artifact_ids": matched}
            if family == "sample_executions":
                copied["authored_task_match"] = bool(task_match)
                copied["matched_items"] = [
                    {
                        **item,
                        "evidence": [
                            e for e in item["evidence"] if e["artifact_id"] in artifact_ids
                        ],
                    }
                    for item in row["matched_items"]
                    if any(e["artifact_id"] in artifact_ids for e in item["evidence"])
                ]
            selected_rows.append(copied)
        result["recorded_" + family] = selected_rows
    return result
