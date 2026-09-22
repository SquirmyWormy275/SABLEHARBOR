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


MAX_REFERENCE_ENTRIES = 200_000


def _reference_guard(state):
    """Bound the complete traversal; overflow never returns a partial reference list."""
    from .store import DomainError

    remaining = MAX_REFERENCE_ENTRIES

    def visit(row, depth=0):
        nonlocal remaining
        if depth > 5:
            raise DomainError(
                "Impact reference nesting limit exceeded", code="IMPACT_REFERENCE_LIMIT_EXCEEDED"
            )
        for key in (
            "versions",
            "items",
            "evidence",
            "remediations",
            "evidence_ids",
            "artifact_ids",
            "observable_artifact_ids",
        ):
            values = row.get(key, [])
            if not isinstance(values, list) or len(values) > 20000:
                raise DomainError(
                    "Impact reference data unavailable", code="IMPACT_REFERENCES_UNAVAILABLE"
                )
            remaining -= len(values)
            if remaining < 0:
                raise DomainError(
                    "Impact reference limit exceeded", code="IMPACT_REFERENCE_LIMIT_EXCEEDED"
                )
            for value in values:
                if key in ("versions", "items", "evidence", "remediations") and not isinstance(
                    value, dict
                ):
                    raise DomainError(
                        "Malformed impact references", code="IMPACT_REFERENCES_UNAVAILABLE"
                    )
                if isinstance(value, dict):
                    visit(value, depth + 1)

    for name in (
        "artifacts",
        "workpapers",
        "populations",
        "tasks",
        "selections",
        "sample_executions",
        "reviews",
        "findings",
    ):
        rows = state.get(name, [])
        if not isinstance(rows, list) or len(rows) > 20000:
            raise DomainError(
                "Impact reference limit exceeded", code="IMPACT_REFERENCE_LIMIT_EXCEEDED"
            )
        remaining -= len(rows)
        seen = set()
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or row["id"] in seen:
                raise DomainError(
                    "Ambiguous impact reference identity", code="IMPACT_REFERENCES_UNAVAILABLE"
                )
            seen.add(row["id"])
            visit(row)
        if remaining < 0:
            raise DomainError(
                "Impact reference limit exceeded", code="IMPACT_REFERENCE_LIMIT_EXCEEDED"
            )


def _exact_references(state, artifact_id):
    from .review_anchor import normalize_anchor
    from .store import DomainError, digest

    result = []
    artifacts = {a["id"]: a for a in state.get("artifacts", [])}
    artifact = artifacts.get(artifact_id)
    evidence_sha = artifact.get("sha256") if artifact else None
    if (
        not isinstance(evidence_sha, str)
        or len(evidence_sha) != 64
        or any(c not in "0123456789abcdef" for c in evidence_sha)
        or artifact.get("audience", "LEARNER") != "LEARNER"
    ):
        evidence_sha = None
    papers = {}
    for paper in state.get("workpapers", []):
        versions = paper.get("versions", [])
        numbers = [v.get("version") for v in versions]
        if any(type(n) is not int or n <= 0 for n in numbers) or len(set(numbers)) != len(numbers):
            raise DomainError(
                "Ambiguous retained workpaper versions", code="IMPACT_REFERENCES_UNAVAILABLE"
            )
        for version in versions:
            papers[paper["id"], version["version"]] = (
                version,
                max(numbers),
                _direct(version, artifact_id),
            )
    traces = {r["id"]: r for r in state.get("sample_executions", [])}
    successors = {}
    for trace in traces.values():
        ids = [item.get("item_id") for item in trace.get("items", [])]
        if (
            any(not isinstance(i, str) for i in ids)
            or len(set(ids)) != len(ids)
            or not isinstance(trace.get("predecessor_id"), (str, type(None)))
        ):
            raise DomainError("Ambiguous execution identity", code="IMPACT_REFERENCES_UNAVAILABLE")
    for trace in traces.values():
        predecessor_id = trace.get("predecessor_id")
        if predecessor_id:
            predecessor = traces.get(predecessor_id)
            if (
                predecessor is None
                or predecessor_id in successors
                or trace.get("predecessor_digest") != digest(predecessor)
                or type(trace.get("revision")) is not int
                or type(predecessor.get("revision")) is not int
                or trace["revision"] != predecessor["revision"] + 1
                or any(
                    trace.get(k) != predecessor.get(k)
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
                or {i.get("item_id") for i in trace.get("items", [])}
                != {i.get("item_id") for i in predecessor.get("items", [])}
            ):
                raise DomainError(
                    "Unverifiable execution correction chain", code="IMPACT_REFERENCES_UNAVAILABLE"
                )
            successors[predecessor_id] = trace["id"]
    for trace in traces.values():
        if (
            type(trace.get("revision")) is not int
            or trace["revision"] <= 0
            or (not trace.get("predecessor_id") and trace["revision"] != 1)
        ):
            raise DomainError("Invalid execution revision", code="IMPACT_REFERENCES_UNAVAILABLE")
        item_ids = [i.get("item_id") for i in trace.get("items", [])]
        if any(not isinstance(i, str) for i in item_ids) or len(set(item_ids)) != len(item_ids):
            raise DomainError("Ambiguous execution items", code="IMPACT_REFERENCES_UNAVAILABLE")
        for item in trace.get("items", []):
            matched = [
                r
                for r in item.get("evidence", [])
                if isinstance(r, dict)
                and r.get("artifact_id") == artifact_id
                and isinstance(evidence_sha, str)
                and r.get("sha256") == evidence_sha
            ]
            if not matched:
                continue
            current_context = (
                trace.get("scope_digest") == digest(state.get("scope", {}))
                and trace.get("company_source_binding") == state.get("company_source_binding")
                and trace.get("evidence_acquisition") == state.get("evidence_acquisition")
            )
            result.append(
                {
                    "collection": "sample_executions",
                    "id": trace["id"],
                    "version": trace["revision"],
                    "item_id": item["item_id"],
                    "task_id": trace.get("task_id"),
                    "selection_id": trace.get("selection_id"),
                    "population_id": trace.get("population_id"),
                    "relation": "EXACT_ITEM_EVIDENCE_ID_AND_SHA256",
                    "artifact_sha256": evidence_sha,
                    "predecessor_id": trace.get("predecessor_id"),
                    "successor_id": successors.get(trace["id"]),
                    "trace_status": "HISTORICAL_CORRECTED"
                    if trace["id"] in successors
                    else "CURRENT_LEAF",
                    "context_status": "CURRENT"
                    if current_context
                    else "HISTORICAL_SCOPE_OR_SOURCE_CONTEXT",
                    "locators": [r.get("locator") for r in matched],
                    "locator_validation": "AUTHOR_SUPPLIED_NOT_CONTENT_MATCH_VERIFIED",
                }
            )
    for review in state.get("reviews", []):
        number = review.get("workpaper_version")
        if review.get("kind") != "HUMAN" or type(number) is not int:
            continue
        if not isinstance(review.get("workpaper_id"), str):
            continue
        entry = papers.get((review.get("workpaper_id"), number))
        if not entry:
            continue
        version, latest, linked = entry
        if not linked or review.get("workpaper_version_digest") != digest(version):
            continue
        anchor = review.get("anchor")
        if anchor is not None:
            try:
                checked = normalize_anchor(
                    {k: v for k, v in anchor.items() if k != "offset_unit"}, version
                )
            except (DomainError, AttributeError):
                continue
            if checked != anchor:
                continue
        result.append(
            {
                "collection": "reviews",
                "id": review["id"],
                "relation": "EXACT_REVIEWED_WORKPAPER_VERSION",
                "workpaper_id": review["workpaper_id"],
                "version": number,
                "workpaper_version_digest": review["workpaper_version_digest"],
                "version_status": "CURRENT" if number == latest else "HISTORICAL",
                "review_scope": "EXACT_PASSAGE"
                if anchor is not None
                else "WHOLE_WORKPAPER_VERSION",
                **({"anchor": dict(anchor)} if anchor is not None else {}),
            }
        )
    for finding in state.get("findings", []):
        if artifact_id in finding.get("evidence_ids", []):
            result.append(
                {
                    "collection": "findings",
                    "id": finding["id"],
                    "relation": "DIRECT_EVIDENCE_ID",
                    "reference_scope": "FINDING",
                }
            )
        for remediation in finding.get("remediations", []):
            if artifact_id in remediation.get("evidence_ids", []) and isinstance(
                remediation.get("id"), str
            ):
                result.append(
                    {
                        "collection": "findings",
                        "id": finding["id"],
                        "relation": "DIRECT_REMEDIATION_EVIDENCE_ID",
                        "remediation_id": remediation["id"],
                        "reference_scope": "REMEDIATION_NOT_ORIGINAL_FINDING",
                    }
                )
    return result


def references(state, artifact_id):
    """Known typed ID fields only; matching narrative or control IDs are not links."""
    _reference_guard(state)
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
    result.extend(_exact_references(state, artifact_id))
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
