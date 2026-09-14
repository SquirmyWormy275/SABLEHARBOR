"""Observable company-source changes, never automatic audit invalidation or grading."""

from __future__ import annotations

import json
from datetime import UTC, datetime

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
    """Compare exact retained originals with later observed versions, per source only."""
    from .store import DomainError

    state = engine.store.get(actor_id, engagement_id)
    bound = dict(binding(engine, state))
    federated = getattr(engine.company_store, "is_federated", False)
    started_at = datetime.now(UTC).isoformat()
    catalog, discovered_at, candidates, unavailable = {}, {}, [], 0
    identity_fields = ("company", "branch", "system", "record", "version", "sha256")

    def read(system, record, version):
        return engine.company_store.read_version(
            actor_id,
            engagement_id,
            bound["company"],
            bound["branch"],
            system,
            record,
            version=version,
            as_of=state["simulated_at"],
        )

    for artifact in state.get("artifacts", []):
        source = artifact.get("source", {})
        if source.get("kind") != "COLLECTED_COMPANY_SOURCE":
            continue
        if artifact.get("status") != "AVAILABLE":
            unavailable += 1
            continue
        receipt = source.get("receipt", {})
        retained = receipt.get("source", {})
        try:
            try:
                engine.artifacts.read(artifact)
            except (DomainError, OSError) as exc:
                raise CompanyStoreError("Retained artifact unavailable or corrupt") from exc
            if receipt.get("engagement_id") != engagement_id:
                raise CompanyStoreError("Retained receipt engagement differs")
            if federated:
                system = engine.company_store.resolve_source_identity(retained)
                upstream = receipt.get("upstream_receipt", {})
                if (
                    receipt.get("registry_sha256") != bound["registry_sha256"]
                    or upstream.get("engagement_id") != engagement_id
                    or any(
                        upstream.get("source", {}).get(k) != retained.get(k)
                        for k in identity_fields
                    )
                ):
                    raise CompanyStoreError("Retained upstream receipt identity differs")
            else:
                if (
                    retained.get("company") != bound["company"]
                    or retained.get("branch") != bound["branch"]
                ):
                    raise CompanyStoreError("Retained source binding differs")
                system = retained.get("system")
            old = read(system, retained.get("record"), retained.get("version"))
            if any(old.get(k) != retained.get(k) for k in identity_fields) or old[
                "sha256"
            ] != artifact.get("sha256"):
                raise CompanyStoreError("Retained original differs")
            if system not in catalog:
                rows, cursor, pages = {}, None, 0
                while True:
                    pages += 1
                    if pages > 1000:
                        raise CompanyStoreError("Source discovery page limit exceeded")
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
                    observed_at = datetime.now(UTC).isoformat()
                    for row in page["records"]:
                        if row["record"] in rows or (
                            cursor is not None and row["record"] <= cursor
                        ):
                            raise CompanyStoreError("Source discovery repeated a record")
                        rows[row["record"]] = row
                        discovered_at[system, row["record"]] = observed_at
                    next_cursor = page["next_after_record"]
                    if next_cursor is None:
                        break
                    if not page["records"] or next_cursor != page["records"][-1]["record"]:
                        raise CompanyStoreError("Source discovery cursor is incomplete")
                    cursor = next_cursor
                catalog[system] = rows
            latest = catalog[system].get(old["record"])
            if latest is None or latest["version"] < old["version"]:
                raise CompanyStoreError("Retained record missing from source discovery")
            current = read(system, old["record"], latest["version"])
            if current["sha256"] != latest["sha256"]:
                raise CompanyStoreError("Observed source version changed")
            candidates.append((artifact, system, old, current))
        except CompanyStoreError:
            unavailable += 1

    # Recheck all originals/current versions after aggregation; a failed comparison
    # must not turn into an unchanged assertion because a catalog was cached earlier.
    changes, compared = [], 0
    for artifact, system, old, current in candidates:
        try:
            for record in (old, current):
                checked = read(system, record["record"], record["version"])
                if any(checked.get(k) != record.get(k) for k in identity_fields):
                    raise CompanyStoreError("Source identity changed during comparison")
        except CompanyStoreError:
            unavailable += 1
            continue
        compared += 1
        if current["version"] == old["version"]:
            continue
        physical = {k: old[k] for k in ("company", "branch", "system", "record")}
        for key in (
            "source_store_id",
            "source_system_alias",
            "registry_sha256",
            "portfolio_qualification",
        ):
            if key in old:
                physical[key] = old[key]
        changes.append(
            {
                "artifact_id": artifact["id"],
                "source_identity": physical,
                "collected_version": old["version"],
                "latest_visible_version": current["version"],
                "collected_sha256": old["sha256"],
                "latest_visible_sha256": current["sha256"],
                "latest_source_qualifiers": {
                    k: current["provenance"][k]
                    for k in (
                        "classification",
                        "operational_fact_status",
                        "record_status",
                        "document_status",
                        "source_status",
                        "record_state",
                        "repository_state",
                        "change_kind",
                    )
                    if isinstance(current["provenance"].get(k), str)
                },
                "references": references(state, artifact["id"]),
                "comparison_basis": "LATEST_VERSION_OBSERVED_DURING_SOURCE_DISCOVERY",
                "discovered_at": discovered_at[system, old["record"]],
                "rechecked_at": datetime.now(UTC).isoformat(),
                "reason": "A later source version is available; review its relevance explicitly.",
                "automatic_invalidation": False,
            }
        )
    current_state = engine.store.get(actor_id, engagement_id)
    if (
        current_state["revision"] != state["revision"]
        or current_state.get("scope") != state.get("scope")
        or current_state.get("simulated_at") != state.get("simulated_at")
        or binding(engine, current_state) != bound
    ):
        raise DomainError("Engagement or company binding changed during comparison", status=409)
    return {
        "status": "OBSERVABLE_SOURCE_CHANGE_REVIEW",
        "engagement_id": engagement_id,
        "engagement_revision": state["revision"],
        "started_at": started_at,
        "completed_at": datetime.now(UTC).isoformat(),
        "simulated_as_of": state["simulated_at"],
        "changes": changes,
        "unavailable_comparisons": unavailable,
        "compared_artifacts": compared,
        "snapshot_isolation": "PER_SOURCE_OPERATION_NOT_GLOBAL",
        "limitations": [
            "Only explicit artifact and exact population-version references are linked.",
            "Unavailable comparisons do not establish unchanged sources, a change or a deficiency.",
            "Later appends after discovery are outside this non-atomic comparison.",
            (
                "Retained evidence and prior conclusions are unchanged. "
                "No professional conclusion is inferred."
            ),
        ],
    }
