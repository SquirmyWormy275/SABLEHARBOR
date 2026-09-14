"""Protected exact-link inventory. Neither learner assessment nor submission grading."""

from .bound_instructor import read_binding
from .instructor_access import InstructorAccessLog
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
            if all(original.get(k) == source[k] for k in IDENTITY):
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
            elif all(original.get(k) == source[k] for k in IDENTITY[:4]):
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
        results.append(
            {
                "expectation_id": expectation["id"],
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
    return {
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
    history = engine.store.history(principal["id"], engagement_id)
    if revision >= len(history):
        raise DomainError("Historical revision is unavailable", status=404)
    selected = history[revision]
    state = selected["state"]
    current = history[-1]["state"]
    original = snapshot["engagement"]
    if (
        original["revision"] >= len(history)
        or digest(history[: original["revision"] + 1]) != original["history_sha256"]
        or digest(history[original["revision"]]["state"]) != original["state_sha256"]
    ):
        raise DomainError("Bound history does not match the engagement chain", status=503)
    mismatch = []
    bound_controls = {c["id"] for c in history[original["revision"]]["state"].get("controls", [])}
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
        "selected_history_sha256": digest(history[: revision + 1]),
        "selected_history_tip_sha256": selected["hash"],
        "current_revision": history[-1]["revision"],
        "mismatches": mismatch,
        "grading": "NOT_PERFORMED",
        "professional_validation": "UNVALIDATED",
        "inspection": "NOT_OBSERVABLE_NO_DOWNLOAD_EVENT_LOG",
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
        result.update(_inventory(snapshot, state, history[: revision + 1]))
    if engine.store.membership(principal["id"], engagement_id) != "instruct":
        raise DomainError("Instructor access changed", status=403)
    if engine.store.get(principal["id"], engagement_id)["revision"] != history[-1]["revision"]:
        raise DomainError("Engagement changed during comparison; select again", status=409)
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
