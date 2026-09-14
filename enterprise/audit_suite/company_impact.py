"""Observable company-source changes, never automatic audit invalidation or grading."""

from __future__ import annotations

import json

from .company_collection import binding
from .company_store import CompanyStoreError


def _direct(row, artifact_id):
    return row.get("artifact_id") == artifact_id or any(
        artifact_id in row.get(field, [])
        for field in ("artifact_ids", "evidence_ids", "observable_artifact_ids")
        if isinstance(row.get(field, []), list)
    )


def references(state, artifact_id):
    """Known typed ID fields only; matching narrative or control IDs are not links."""
    result, populations = [], {}
    for workpaper in state.get("workpapers", []):
        for version in workpaper.get("versions", []):
            if _direct(version, artifact_id):
                result.append(
                    {
                        "collection": "workpapers",
                        "id": workpaper["id"],
                        "version": version["version"],
                        "relation": "DIRECT_EVIDENCE_ID",
                    }
                )
    for collection in ("populations", "tasks"):
        for row in state.get(collection, []):
            linked = _direct(row, artifact_id)
            if collection == "populations":
                try:
                    source = json.loads(row.get("source_json", "{}"))
                except (ValueError, TypeError):
                    source = {}
                linked |= isinstance(source, dict) and source.get("source_id") == artifact_id
            if linked:
                ref = {"collection": collection, "id": row["id"], "relation": "DIRECT_EVIDENCE_ID"}
                if collection == "populations":
                    ref["version"] = row.get("version")
                    populations[row["id"]] = row.get("version")
                result.append(ref)
    for selection in state.get("selections", []):
        if (
            _direct(selection, artifact_id)
            or selection.get("population_id") in populations
            and selection.get("population_version") == populations[selection["population_id"]]
        ):
            result.append(
                {
                    "collection": "selections",
                    "id": selection["id"],
                    "relation": "DIRECT_EVIDENCE_ID"
                    if _direct(selection, artifact_id)
                    else "EXACT_REFERENCED_POPULATION_VERSION",
                }
            )
    return result


def report(engine, actor_id, engagement_id):
    """Read current authorized state and compare immutable receipts to visible versions.

    The caller supplies the authenticated principal; clock/company/branch come only
    from the engagement and operator binding. No company context receives hidden keys.
    """
    state = engine.store.get(actor_id, engagement_id)
    bound = binding(engine, state)
    catalog, changes, unavailable = {}, [], 0
    for artifact in state.get("artifacts", []):
        if artifact.get("status") != "AVAILABLE":
            continue
        source = artifact.get("source", {})
        if source.get("kind") != "COLLECTED_COMPANY_SOURCE":
            continue
        receipt = source.get("receipt", {})
        retained = receipt.get("source", {})
        if (
            receipt.get("engagement_id") != engagement_id
            or retained.get("company") != bound["company"]
            or retained.get("branch") != bound["branch"]
        ):
            unavailable += 1
            continue
        system = retained.get("system")
        try:
            # Every comparison rechecks authorization, even if a catalog was already read.
            old = engine.company_store.read_version(
                actor_id,
                engagement_id,
                bound["company"],
                bound["branch"],
                system,
                retained.get("record"),
                version=retained.get("version"),
                as_of=state["simulated_at"],
            )
            if old["sha256"] != retained.get("sha256") or old["sha256"] != artifact.get("sha256"):
                unavailable += 1
                continue
            if system not in catalog:
                rows, cursor = {}, None
                while True:
                    page = engine.company_store.list_records(
                        actor_id,
                        engagement_id,
                        bound["company"],
                        bound["branch"],
                        system,
                        as_of=state["simulated_at"],
                        after_record=cursor,
                        limit=1000,
                    )
                    rows.update({row["record"]: row for row in page["records"]})
                    cursor = page["next_after_record"]
                    if cursor is None:
                        break
                catalog[system] = rows
            latest = catalog[system].get(old["record"])
            if latest is None:
                unavailable += 1
                continue
            if latest["version"] <= old["version"]:
                continue
            # Recheck new version before reporting; catalog is never authority on its own.
            current = engine.company_store.read_version(
                actor_id,
                engagement_id,
                bound["company"],
                bound["branch"],
                system,
                old["record"],
                version=latest["version"],
                as_of=state["simulated_at"],
            )
        except CompanyStoreError:
            unavailable += 1
            continue
        changes.append(
            {
                "artifact_id": artifact["id"],
                "source_identity": {
                    "company": bound["company"],
                    "branch": bound["branch"],
                    "system": system,
                    "record": old["record"],
                },
                "collected_version": old["version"],
                "latest_visible_version": current["version"],
                "collected_sha256": old["sha256"],
                "latest_visible_sha256": current["sha256"],
                "references": references(state, artifact["id"]),
                "reason": "A later source version is available; review its relevance explicitly.",
                "automatic_invalidation": False,
            }
        )
    return {
        "status": "OBSERVABLE_SOURCE_CHANGE_REVIEW",
        "simulated_as_of": state["simulated_at"],
        "changes": changes,
        "unavailable_comparisons": unavailable,
        "limitations": [
            "Only explicit artifact and exact population-version references are linked.",
            "Unavailable comparisons do not establish a source change or deficiency.",
            "Retained evidence and prior conclusions are unchanged. "
            "No professional conclusion is inferred.",
        ],
    }
