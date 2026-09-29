"""Explicit exact-source reassessment decisions; never automatic result invalidation."""

from copy import deepcopy

from .company_collection import binding
from .company_impact import references, report
from .store import DomainError, digest, identifier

COMMAND = "source.impact.disposition.record"
KINDS = {"ACKNOWLEDGED", "REASSESSMENT_NEEDED", "RETEST_LINKED", "NOT_APPLICABLE_TO_SELECTED_WORK"}
LIMIT = 256
MAX_HISTORY = 2000
QUALIFICATION = "AUTHOR_RECORDED_REASSESSMENT_NOT_RETEST_RESULT_OR_PROFESSIONAL_CLEARANCE"


def require(ok, message, status=400):
    if not ok:
        raise DomainError(message, status=status)


def _basis(state):
    return digest(
        {k: state.get(k) for k in ("scope", "company_source_binding", "evidence_acquisition")}
    )


def _row(state, reference):
    collection = reference["collection"]
    require(
        collection
        in {
            "artifacts",
            "workpapers",
            "populations",
            "selections",
            "tasks",
            "sample_executions",
            "reviews",
            "findings",
        },
        "Unsupported affected work",
    )
    matches = [r for r in state.get(collection, []) if r.get("id") == reference["id"]]
    require(len(matches) == 1, "Exact affected work unavailable", 409)
    row = matches[0]
    version = reference.get("version")
    if collection == "workpapers":
        require(type(version) is int and version > 0, "Exact workpaper version required")
        versions = [
            v
            for v in row.get("versions", [])
            if type(v.get("version")) is int and v["version"] == version
        ]
        require(len(versions) == 1, "Exact workpaper version unavailable", 409)
        row = versions[0]
    elif collection == "findings" and reference.get("remediation_id"):
        matches = [
            r for r in row.get("remediations", []) if r.get("id") == reference["remediation_id"]
        ]
        require(len(matches) == 1, "Exact remediation unavailable", 409)
        row = matches[0]
    elif collection == "sample_executions":
        require(
            type(version) is int and version == row.get("revision"),
            "Exact observation revision unavailable",
            409,
        )
        if reference.get("item_id"):
            require(
                sum(i.get("item_id") == reference["item_id"] for i in row.get("items", [])) == 1,
                "Exact observed item unavailable",
                409,
            )
    return row


def _choice(state, reference):
    base = {"reference": deepcopy(reference), "record_sha256": digest(_row(state, reference))}
    identity = {
        k: reference[k]
        for k in ("collection", "id", "version", "item_id", "remediation_id")
        if k in reference
    }
    return {
        "sha256": digest({"identity": identity, "record_sha256": base["record_sha256"]}),
        **base,
    }


def _choices(state, artifact_ids):
    result = {}
    for artifact_id in artifact_ids:
        matches = [
            a
            for a in state.get("artifacts", [])
            if a.get("id") == artifact_id
            and a.get("status") == "AVAILABLE"
            and a.get("audience", "LEARNER") == "LEARNER"
        ]
        require(len(matches) == 1, "Exact retained original unavailable", 409)
        original = {
            "collection": "artifacts",
            "id": artifact_id,
            "sha256": matches[0]["sha256"],
            "relation": "EXACT_RETAINED_ORIGINAL",
        }
        for ref in [*references(state, artifact_id), original]:
            choice = _choice(state, ref)
            result[choice["sha256"]] = choice
            require(len(result) <= LIMIT, "Affected work choice limit exceeded")
    return list(result.values())


def project(state, engine=None, *, current_context=None):
    """No source reads; historical visibility is not a current source recheck."""
    rows = state.get("source_impact_dispositions", [])
    require(isinstance(rows, list) and len(rows) <= MAX_HISTORY, "Disposition history limit")
    context = state if current_context is None else current_context
    result = []
    for row in rows:
        status = "CURRENT"
        if row.get("basis_sha256") != _basis(context):
            status = "CONTEXT_CHANGED"
        else:
            try:
                if engine is not None:
                    require(
                        row["comparison"]["company_binding"] == dict(binding(engine, context)),
                        "Source binding changed",
                    )
                artifact = [
                    a
                    for a in context.get("artifacts", [])
                    if a.get("id") == row["artifact_id"] and a.get("status") == "AVAILABLE"
                ]
                require(
                    len(artifact) == 1
                    and artifact[0]["sha256"] == row["comparison"]["collected_sha256"],
                    "Original unavailable",
                )
                for target in (row["target"], row.get("retest")):
                    if target:
                        require(
                            digest(_row(context, target["reference"])) == target["record_sha256"],
                            "Recorded target unavailable",
                        )
            except (DomainError, KeyError, TypeError):
                status = "TARGET_UNAVAILABLE"
        metadata = {k: row[k] for k in ("id", "revision", "version", "actor", "recorded_at")}
        result.append(
            {
                **(deepcopy(row) if status == "CURRENT" else metadata),
                "context_status": status,
                "personal_content_visible": status == "CURRENT",
            }
        )
    return result


def _inputs(engine, actor, state, artifact_id):
    eid = state["id"]
    require(state.get("phase") == "ACTIVE", "Active engagement required", 409)
    require(
        engine.store.membership(actor, eid) in {"learn", "instruct"},
        "Reassessment author authority required",
        403,
    )
    observed = report(engine, actor, eid, artifact_id=artifact_id)
    require(observed["engagement_revision"] == state["revision"], "Engagement changed", 409)
    changes = [c for c in observed["changes"] if c["artifact_id"] == artifact_id]
    require(
        len(changes) == 1,
        "Current authorized source change unavailable; no unchanged assertion inferred",
        409,
    )
    change = changes[0]
    base = {
        k: deepcopy(change[k])
        for k in (
            "artifact_id",
            "source_identity",
            "collected_version",
            "latest_visible_version",
            "collected_sha256",
            "latest_visible_sha256",
            "latest_source_qualifiers",
            "comparison_basis",
        )
    }
    base.update(
        context_basis_sha256=_basis(state),
        simulated_as_of=state["simulated_at"],
        company_binding=dict(binding(engine, state)),
    )
    comparison = {**base, "sha256": digest(base)}
    targets = _choices(state, [artifact_id])
    exact_artifacts = [artifact_id]
    native = change["source_identity"]
    for artifact in state.get("artifacts", []):
        source = artifact.get("source", {}).get("receipt", {}).get("source", {})
        if (
            artifact.get("audience", "LEARNER") == "LEARNER"
            and artifact.get("status") == "AVAILABLE"
            and artifact.get("sha256") == change["latest_visible_sha256"]
            and type(source.get("version")) is int
            and source["version"] == change["latest_visible_version"]
            and all(source.get(k) == v for k, v in native.items())
        ):
            exact_artifacts.append(artifact["id"])
    retests = [
        c
        for c in _choices(state, exact_artifacts)
        if c["reference"]["collection"]
        in {"workpapers", "sample_executions", "reviews", "findings"}
    ]
    history = [
        {k: v for k, v in row.items() if k not in {"context_status", "personal_content_visible"}}
        for row in state.get("source_impact_dispositions", [])
        if row.get("personal_content_visible", True)
    ]
    require(len(history) <= MAX_HISTORY, "Disposition history limit")
    superseded = {r["predecessor"]["id"] for r in history if r.get("predecessor")}
    visible = {r["id"] for r in project(state, engine) if r["personal_content_visible"]}
    predecessors = [
        {"id": r["id"], "sha256": digest(r), "target_sha256": r["target"]["sha256"]}
        for r in history
        if r["artifact_id"] == artifact_id and r["id"] not in superseded and r["id"] in visible
    ]
    require(len(predecessors) <= LIMIT, "Disposition predecessor limit")
    return {
        "engagement_id": eid,
        "engagement_revision": state["revision"],
        "artifact_id": artifact_id,
        "comparison": comparison,
        "observed": {k: change[k] for k in ("discovered_at", "rechecked_at")},
        "targets": targets,
        "retests": retests,
        "predecessors": predecessors,
    }


def inputs(engine, actor_id, engagement_id, artifact_id):
    return _inputs(engine, actor_id, engine.get(actor_id, engagement_id), artifact_id)


def handle(engine, state, payload, stamped):
    require(
        isinstance(payload, dict)
        and set(payload)
        == {
            "artifact_id",
            "comparison_sha256",
            "target_sha256",
            "disposition",
            "rationale",
            "intended_action",
            "retest_sha256",
            "predecessor",
        },
        "Exact disposition payload required",
    )
    require(
        isinstance(payload["disposition"], str) and payload["disposition"] in KINDS,
        "Explicit disposition required",
    )
    for key, limit in (("rationale", 4000), ("intended_action", 2000)):
        require(
            isinstance(payload[key], str) and 0 < len(payload[key].strip()) <= limit,
            "Bounded authored " + key + " required",
        )
    history = state.setdefault("source_impact_dispositions", [])
    require(len(history) < MAX_HISTORY, "Disposition history limit")
    # Use the same authorized projection as the inputs route; never hidden Key material.
    projected = engine._project(stamped["actor"], deepcopy(state))
    current = _inputs(engine, stamped["actor"], projected, payload["artifact_id"])
    require(
        current["comparison"]["sha256"] == payload["comparison_sha256"],
        "Source comparison changed; inspect again",
        409,
    )
    targets = [c for c in current["targets"] if c["sha256"] == payload["target_sha256"]]
    require(len(targets) == 1, "Exact selected target changed", 409)
    retest = None
    if payload["disposition"] == "RETEST_LINKED":
        matches = [c for c in current["retests"] if c["sha256"] == payload["retest_sha256"]]
        require(
            len(matches) == 1 and matches[0]["sha256"] != targets[0]["sha256"],
            "Distinct existing reassessment work required",
            409,
        )
        retest = matches[0]
    else:
        require(
            payload["retest_sha256"] is None,
            "Retest link requires explicit linked-work disposition",
        )
    predecessor = payload["predecessor"]
    leaves = [p for p in current["predecessors"] if p["target_sha256"] == payload["target_sha256"]]
    if predecessor is None:
        require(not leaves, "Exact current predecessor required", 409)
        version = 1
    else:
        require(
            isinstance(predecessor, dict) and set(predecessor) == {"id", "sha256"},
            "Exact predecessor required",
        )
        require(
            len(leaves) == 1 and all(predecessor[k] == leaves[0][k] for k in predecessor),
            "Disposition predecessor changed",
            409,
        )
        version = next(r["version"] for r in history if r["id"] == predecessor["id"]) + 1
    final = _inputs(engine, stamped["actor"], projected, payload["artifact_id"])
    require(
        all(final[k] == current[k] for k in ("comparison", "targets", "retests", "predecessors")),
        "Source or linked work changed before disposition",
        409,
    )
    history.append(
        {
            "id": identifier("SID"),
            "revision": state["revision"] + 1,
            "version": version,
            **stamped,
            "artifact_id": payload["artifact_id"],
            "comparison": final["comparison"],
            "observed": final["observed"],
            "target": targets[0],
            "retest": retest,
            "disposition": payload["disposition"],
            "rationale": payload["rationale"],
            "intended_action": payload["intended_action"],
            "predecessor": deepcopy(predecessor),
            "basis_sha256": _basis(state),
            "qualification": QUALIFICATION,
        }
    )
