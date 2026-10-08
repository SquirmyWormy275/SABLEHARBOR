"""Protected exact-link inventory. Neither learner assessment nor submission grading."""

from .bound_instructor import read_binding
from .expectation_links import inventory as task_inventory
from .instructor_access import InstructorAccessLog
from .instructor_work_links import index as work_index
from .instructor_work_links import selected as selected_work
from .portfolio_explanation import same_route, validate_routes
from .store import DomainError, digest
from .workpaper_links import validate_task_ids

IDENTITY = ("company", "branch", "system", "record", "version", "sha256")


def _ref(row, **extra):
    return {"id": row["id"], **extra}


def _inventory(snapshot, state, history):
    artifacts = [a for a in state.get("artifacts", []) if a.get("audience", "LEARNER") == "LEARNER"]
    sources = {}
    for source in snapshot["sources"]:
        matched, changed = [], []
        for artifact in artifacts:
            original = artifact.get("source", {}).get("receipt", {}).get("source", {})
            if same_route(original, source) and all(original.get(k) == source[k] for k in IDENTITY):
                if artifact.get("sha256") == source["sha256"]:
                    matched.append(
                        _ref(
                            artifact,
                            sha256=artifact["sha256"],
                            request_id=artifact.get("request_id"),
                        )
                    )
                else:
                    changed.append(artifact["id"])
            elif same_route(original, source) and all(
                original.get(k) == source[k] for k in IDENTITY[:4]
            ):
                changed.append(artifact["id"])
        sources[source["id"]] = {
            "source_id": source["id"],
            "source_sha256": source["sha256"],
            "exact_retained_artifacts": matched,
            "different_version_or_digest_artifact_ids": changed,
            "status": "EXACT_RETAINED_METADATA_LINK"
            if matched
            else "NO_EXACT_RETAINED_LINK_RECORDED",
        }
    issues = {i["id"]: i for i in snapshot["authored"]["issues"]}
    indexed_work = work_index(state, {a["id"]: a["sha256"] for a in artifacts})
    results = []
    for expectation in snapshot["authored"]["expectations"]:
        selected_issues = [issues[i] for i in expectation["issue_ids"]]
        controls = sorted({c for i in selected_issues for c in i["control_ids"]})
        source_ids = sorted({s for i in selected_issues for s in i["source_ids"]})
        artifact_ids = {a["id"] for s in source_ids for a in sources[s]["exact_retained_artifacts"]}
        populations = [
            p for p in state.get("populations", []) if p.get("artifact_id") in artifact_ids
        ]
        population_ids = {p["id"] for p in populations}
        workpapers = []
        for wp in state.get("workpapers", []):
            for version in wp.get("versions", []):
                refs = set(version.get("evidence_ids", []))
                if version.get("artifact_id"):
                    refs.add(version["artifact_id"])
                if refs & artifact_ids:
                    declared_tasks = version.get("task_ids", [])
                    try:
                        valid_tasks = validate_task_ids(state, wp.get("control_id"), declared_tasks)
                        task_validation = (
                            "VALID_FOR_SELECTED_STATE"
                            if "task_ids" in version
                            else "NOT_RECORDED_LEGACY_VERSION"
                        )
                    except DomainError:
                        valid_tasks = []
                        task_validation = "UNRESOLVED_IN_SELECTED_SCOPE"
                    workpapers.append(
                        _ref(
                            wp,
                            version=version["version"],
                            version_sha256=digest(version),
                            source_artifact_ids=sorted(refs & artifact_ids),
                            actor=version.get("actor"),
                            prepared_by=wp.get("prepared_by"),
                            task_ids=valid_tasks,
                            task_link_validation=task_validation,
                            recorded_conclusion=version.get("conclusion"),
                        )
                    )
        reviews = []
        for review in state.get("reviews", []):
            for wp in workpapers:
                if (
                    review.get("workpaper_id") == wp["id"]
                    and review.get("workpaper_version") == wp["version"]
                ):
                    reviews.append(
                        _ref(
                            review,
                            workpaper_id=wp["id"],
                            workpaper_version=wp["version"],
                            target_digest_matches=review.get("workpaper_version_digest")
                            == wp["version_sha256"],
                            actor=review.get("actor"),
                            recorded_status=review.get("status"),
                        )
                    )
        explicit_tasks = task_inventory(expectation, controls, artifact_ids, state)
        results.append(
            {
                "expectation_id": expectation["id"],
                **explicit_tasks,
                **selected_work(indexed_work, artifact_ids, explicit_tasks),
                "issue_ids": expectation["issue_ids"],
                "control_ids": controls,
                "source_ids": source_ids,
                "status": "EXPLICIT_SOURCE_LINK_PRESENT"
                if workpapers
                else "NO_EXPLICIT_WORKPAPER_SOURCE_LINK_RECORDED",
                "control_associated_records_only": {
                    "requests": [
                        _ref(r, recorded_status=r.get("status"))
                        for r in state.get("requests", [])
                        if r.get("control_id") in controls
                    ],
                    "tasks": [
                        _ref(
                            t,
                            recorded_status=t.get("status"),
                            recorded_conclusion=t.get("conclusion"),
                        )
                        for t in state.get("tasks", [])
                        if t.get("control_id") in controls
                    ],
                },
                "source_linked_populations": [
                    _ref(
                        p,
                        version=p.get("version"),
                        artifact_id=p.get("artifact_id"),
                        provisional=p.get("provisional"),
                    )
                    for p in populations
                ],
                "population_linked_selections": [
                    _ref(
                        s,
                        population_id=s["population_id"],
                        population_version=s.get("population_version"),
                        population_version_matches=any(
                            p["id"] == s["population_id"]
                            and p.get("version") == s.get("population_version")
                            for p in populations
                        ),
                    )
                    for s in state.get("selections", [])
                    if s.get("population_id") in population_ids
                ],
                "source_linked_workpaper_versions": workpapers,
                "workpaper_version_reviews": reviews,
                "testing": "NOT_ASSESSED",
                "understanding": "NOT_ASSESSED",
                "judgment": "NOT_ASSESSED",
            }
        )
    actor = snapshot["audited_actor_id"]
    activity = [
        {
            "revision": h["revision"],
            "command_id": h["command_id"],
            "kind": h["command"].get("kind"),
            "recorded_at": h["recorded_at"],
            "history_sha256": h["hash"],
        }
        for h in history
        if h["actor"] == actor
    ]
    from .artifact_inspection import inventory as inspection_inventory

    return {
        "inspection": inspection_inventory(state, history, actor),
        "sources": list(sources.values()),
        "expectations": results,
        "audited_actor_activity": activity,
        "shared_workspace_activity_count": len(history) - len(activity),
    }


def _compare(engine, principal, engagement_id, bindings, *, revision):
    """Read an explicit historical revision; no default to latest or submission inference."""
    if engine.store.membership(principal["id"], engagement_id) != "instruct":
        raise DomainError("Instructor membership required", status=403)
    if type(revision) is not int or revision < 0:
        raise DomainError("Explicit nonnegative historical revision required")
    bound = read_binding(engine, principal, engagement_id, bindings)
    snapshot = bound["snapshot"]
    from .history_integrity_reference import inspect_selected_integrity, validate_reference

    original = snapshot["engagement"]
    history = inspect_selected_integrity(
        engine.store,
        principal["id"],
        engagement_id,
        revisions=[revision, original["revision"]],
    )
    if revision >= history["count"]:
        raise DomainError("Historical revision is unavailable", status=404)
    selected = history["selected"][revision]
    state = selected["state"]
    current = history["latest"]["state"]
    original = snapshot["engagement"]
    if (
        original["revision"] >= history["count"]
        or history["prefix_sha256"][original["revision"]] != original["history_sha256"]
        or digest(history["selected"][original["revision"]]["state"]) != original["state_sha256"]
    ):
        raise DomainError("Bound history does not match the engagement chain", status=503)
    mismatch = []
    bound_controls = {
        c["id"] for c in history["selected"][original["revision"]]["state"].get("controls", [])
    }
    if {c["id"] for c in state.get("controls", [])} != bound_controls:
        mismatch.append("SELECTED_CONTROL_SCOPE_DIFFERS_FROM_BOUND_SCOPE")
    if {c["id"] for c in current.get("controls", [])} != bound_controls:
        mismatch.append("CURRENT_CONTROL_SCOPE_DIFFERS_FROM_BOUND_SCOPE")
    if state.get("scope") != original["scope"]:
        mismatch.append("SELECTED_SCOPE_DIFFERS_FROM_BOUND_SCOPE")
    frozen = state.get("company_source_binding")
    if frozen is None and revision == original["revision"]:
        frozen = snapshot["company_binding"]
    if frozen != snapshot["company_binding"]:
        mismatch.append("SELECTED_COMPANY_BASIS_DIFFERENT_OR_UNRECORDED")
    if (
        engine.company_bindings.get(engagement_id) != snapshot["company_binding"]
        or current.get("company_source_binding", snapshot["company_binding"])
        != snapshot["company_binding"]
    ):
        mismatch.append("CURRENT_COMPANY_BASIS_DIFFERS_FROM_BOUND_SOURCE")
    if current.get("scope") != original["scope"]:
        mismatch.append("CURRENT_SCOPE_DIFFERS_FROM_BOUND_SCOPE")
    result = {
        "schema_version": "1.0",
        "status": "CONTEXT_MISMATCH" if mismatch else "DETERMINISTIC_LINK_INVENTORY_ONLY",
        "engagement_id": engagement_id,
        "audited_actor_id": snapshot["audited_actor_id"],
        "binding_manifest_sha256": bound["binding"]["manifest_sha256"],
        "bound_revision": original["revision"],
        "selected_history_revision": revision,
        "selected_state_sha256": digest(state),
        **({"schema_version": "2.0", "selected_history_integrity_reference":
            validate_reference(history["selected_integrity_reference"][revision],
                engagement=engagement_id, revision=revision,
                state_sha256=digest(state), event_sha256=selected["hash"])}
           if "selected_integrity_reference" in history else
           {"selected_history_sha256": history["prefix_sha256"][revision]}),
        "selected_history_tip_sha256": selected["hash"],
        "current_revision": history["latest"]["revision"],
        "mismatches": mismatch,
        "grading": "NOT_PERFORMED",
        "professional_validation": "UNVALIDATED",
        "inspection": {"status": "UNAVAILABLE_SELECTED_CONTEXT_MISMATCH"},
        "submission": "NOT_INFERRED_FROM_REVISION",
        "limits": [
            "Source links match retained metadata; native bytes are not reread by this report.",
            "Control association does not prove a procedure implements an authored expectation.",
            "Shared workspace records are not attributed to the audited actor "
            "unless an actual command actor matches.",
            "Missing links do not establish missed issues, ineffective testing "
            "or unsupported judgment.",
        ],
    }
    if not mismatch:
        result.update(_inventory(snapshot, state, history["activity"][: revision + 1]))
    if engine.store.membership(principal["id"], engagement_id) != "instruct":
        raise DomainError("Instructor access changed", status=403)
    if (
        engine.store.get(principal["id"], engagement_id)["revision"]
        != history["latest"]["revision"]
    ):
        raise DomainError("Engagement changed during comparison; select again", status=409)
    try:
        validate_routes(engine, snapshot)
    except Exception as error:
        raise DomainError(
            "Bound portfolio routing changed during comparison", status=503
        ) from error
    InstructorAccessLog(engine.store.root / "instructor-key-access").append(
        actor=principal["id"],
        engagement=engagement_id,
        target=f"LINK_INVENTORY:{revision}",
        operation="BOUND_SNAPSHOT",
        outcome="SUCCESS",
        http_status=200,
        binding_manifest_sha256=bound["binding"]["manifest_sha256"],
        key_sha256=digest(result),
    )
    return result


def compare(engine, principal, engagement_id, bindings, *, revision):
    try:
        result = _compare(engine, principal, engagement_id, bindings, revision=revision)
        if engine.store.membership(principal["id"], engagement_id) != "instruct":
            raise DomainError("Instructor access changed", status=403)
        return result
    except Exception as error:
        status = error.status if isinstance(error, DomainError) else 500
        InstructorAccessLog(engine.store.root / "instructor-key-access").append(
            actor=principal["id"],
            engagement=engagement_id,
            target="LINK_INVENTORY",
            operation="BOUND_SNAPSHOT",
            outcome={403: "DENIED", 404: "NOT_FOUND", 503: "UNAVAILABLE"}.get(status, "ERROR"),
            http_status=status,
        )
        raise


# Opt-in transport only. The complete comparison and its historical checks above
# remain unchanged; every deferred field is recoverable through the same route.
COMPARISON_VIEW_SCHEMA = "SH_INSTRUCTOR_COMPARISON_TRANSPORT_V1"
COMPARISON_VIEW_MAX_BYTES = 4 * 1024 * 1024
COMPARISON_PAGE_LIMIT = 20
_EXPECTATION_FAMILIES = (
    "task_linked_workpaper_versions", "source_linked_workpaper_versions",
    "workpaper_version_reviews", "source_linked_populations",
    "population_linked_selections", "recorded_sample_executions",
    "recorded_findings", "recorded_remediations",
    "control_associated_records_only.requests", "control_associated_records_only.tasks",
)
_GLOBAL_FAMILIES = ("sources", "inspection.records", "audited_actor_activity")
_SOURCE_FAMILIES = ("sources.exact_retained_artifacts", "sources.different_version_or_digest_artifact_ids")
_SAMPLE_FAMILIES = (
    "expectation.recorded_sample_executions.matched_items",
    "expectation.recorded_sample_executions.matched_items.evidence",
)


def _view_require(condition, message, status=400):
    if not condition:
        raise DomainError(message, status=status)


def _view_size(value):
    import json

    total = 0
    encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    for part in encoder.iterencode(value):
        # Count UTF-8 in bounded slices; do not encode an unbounded scalar at once.
        for offset in range(0, len(part), 65536):
            total += len(part[offset:offset + 65536].encode("utf-8"))
            if total > COMPARISON_VIEW_MAX_BYTES:
                return total
    return total


def _view_list(value):
    _view_require(type(value) is list, "Comparison relationship list unavailable", 503)
    return value


def _view_one(rows, field, value):
    _view_require(type(value) is str and 0 < len(value) <= 256, "Exact comparison record selector required")
    matches = [row for row in rows if row.get(field) == value]
    _view_require(len(matches) == 1, "Exact comparison record unavailable", 404)
    return matches[0]


def _view_descriptor(rows, family, **selectors):
    return {"family": family, "count": len(rows), "sha256": digest(rows), **selectors}


def _view_target(inventory, family, expectation_id, source_id, record_id, item_id):
    _view_require(type(family) is str, "Exact comparison family required")
    if family in _GLOBAL_FAMILIES:
        _view_require(all(v is None for v in (expectation_id, source_id, record_id, item_id)), "Unexpected comparison selector")
        if family == "inspection.records":
            return _view_list(inventory["inspection"]["records"])
        return _view_list(inventory[family])
    if family in _SOURCE_FAMILIES:
        _view_require(all(v is None for v in (expectation_id, record_id, item_id)), "Unexpected source selector")
        row = _view_one(inventory["sources"], "source_id", source_id)
        return _view_list(row[family.split(".", 1)[1]])
    _view_require(source_id is None, "Unexpected expectation source selector")
    row = _view_one(inventory["expectations"], "expectation_id", expectation_id)
    if family == "expectation":
        _view_require(record_id is None and item_id is None, "Unexpected expectation record selector")
        return [row]
    if family in _SAMPLE_FAMILIES:
        sample = _view_one(row.get("recorded_sample_executions", []), "id", record_id)
        if family.endswith(".evidence"):
            item = _view_one(sample["matched_items"], "item_id", item_id)
            return _view_list(item["evidence"])
        _view_require(item_id is None, "Unexpected sample item selector")
        return _view_list(sample["matched_items"])
    _view_require(record_id is None and item_id is None, "Unexpected relationship record selector")
    name = family.removeprefix("expectation.")
    _view_require(family.startswith("expectation.") and name in _EXPECTATION_FAMILIES, "Unsupported comparison family")
    if name.startswith("control_associated_records_only."):
        return _view_list(row["control_associated_records_only"][name.rsplit(".", 1)[1]])
    return _view_list(row.get(name, []))


def _view_row(row, family, expectation_id=None, record_id=None):
    if type(row) is not dict:
        return row
    value = dict(row)
    deferred = {}
    if family == "expectation":
        for name in _EXPECTATION_FAMILIES:
            if name.startswith("control_associated_records_only."):
                rows = row["control_associated_records_only"][name.rsplit(".", 1)[1]]
            else:
                rows = row.get(name, [])
                value.pop(name, None)
            deferred[name] = _view_descriptor(rows, "expectation." + name, expectation_id=row["expectation_id"])
        value.pop("control_associated_records_only", None)
    elif family == "sources":
        for name in ("exact_retained_artifacts", "different_version_or_digest_artifact_ids"):
            deferred[name] = _view_descriptor(row[name], "sources." + name, source_id=row["source_id"])
            value.pop(name)
    elif family == "expectation.recorded_sample_executions":
        deferred["matched_items"] = _view_descriptor(row["matched_items"], family + ".matched_items", expectation_id=expectation_id, record_id=row["id"])
        value.pop("matched_items")
    elif family == "expectation.recorded_sample_executions.matched_items":
        deferred["evidence"] = _view_descriptor(row["evidence"], family + ".evidence", expectation_id=expectation_id, record_id=record_id, item_id=row["item_id"])
        value.pop("evidence")
    if deferred:
        value["_comparison_deferred"] = deferred
    return value


def comparison_view(inventory, *, view, family=None, expectation_id=None, source_id=None,
                    record_id=None, item_id=None, inventory_sha256=None, target_sha256=None,
                    offset=0, limit=COMPARISON_PAGE_LIMIT):
    """Complete header or typed bounded page; never alter the full inventory."""
    import re

    _view_require(view in {"summary-v1", "detail-v1"}, "Exact comparison transport required")
    _view_require(type(offset) is int and offset >= 0 and type(limit) is int and 1 <= limit <= COMPARISON_PAGE_LIMIT, "Bounded comparison page required")
    full_sha = digest(inventory)
    context = {k: v for k, v in inventory.items() if k not in {"sources", "expectations", "inspection", "audited_actor_activity"}}
    transport = {"schema": COMPARISON_VIEW_SCHEMA, "inventory_sha256": full_sha,
                 "complete_inventory_changed": False, "response_max_bytes": COMPARISON_VIEW_MAX_BYTES}
    if view == "summary-v1":
        _view_require(all(v is None for v in (family, expectation_id, source_id, record_id, item_id, inventory_sha256, target_sha256)) and offset == 0 and limit == COMPARISON_PAGE_LIMIT, "Summary does not accept detail selectors")
        result = {**context, "comparison_transport": {**transport, "view": "SUMMARY"}}
        if inventory["status"] == "DETERMINISTIC_LINK_INVENTORY_ONLY":
            result["expectations"] = [{"expectation_id": row["expectation_id"], "status": row["status"],
                                       "detail": _view_descriptor([row], "expectation", expectation_id=row["expectation_id"])}
                                      for row in inventory["expectations"]]
            result["deferred"] = {name: _view_descriptor(_view_target(inventory, name, None, None, None, None), name) for name in _GLOBAL_FAMILIES}
            result["inspection"] = {k: v for k, v in inventory["inspection"].items() if k != "records"}
            result["audited_actor_activity_count"] = len(inventory["audited_actor_activity"])
        else:
            result["inspection"] = inventory["inspection"]
            result["expectations"] = []
            result["deferred"] = {}
    else:
        _view_require(inventory["status"] == "DETERMINISTIC_LINK_INVENTORY_ONLY", "Selected comparison context unavailable", 409)
        _view_require(type(inventory_sha256) is str and re.fullmatch(r"[a-f0-9]{64}", inventory_sha256) and inventory_sha256 == full_sha, "Comparison context changed; select again", 409)
        rows = _view_target(inventory, family, expectation_id, source_id, record_id, item_id)
        _view_require(type(target_sha256) is str and re.fullmatch(r"[a-f0-9]{64}", target_sha256) and target_sha256 == digest(rows), "Comparison relationship changed; select again", 409)
        _view_require(offset <= len(rows), "Comparison page is outside the selected list")
        result = {**context, "comparison_transport": {**transport, "view": "DETAIL"},
                  "page": {"family": family, "target_sha256": target_sha256, "offset": offset,
                           "total": len(rows), "next_offset": None, "rows": []}}
        for row in rows[offset:offset + limit]:
            projected = _view_row(row, family, expectation_id, record_id)
            result["page"]["rows"].append(projected)
            if _view_size(result) > COMPARISON_VIEW_MAX_BYTES:
                result["page"]["rows"].pop()
                _view_require(bool(result["page"]["rows"]), "Selected comparison record exceeds the bounded view; use its declared detail or complete packet", 413)
                break
        end = offset + len(result["page"]["rows"])
        result["page"]["next_offset"] = end if end < len(rows) else None
    _view_require(_view_size(result) <= COMPARISON_VIEW_MAX_BYTES, "Comparison header exceeds the bounded view; complete packet remains available", 413)
    return result
