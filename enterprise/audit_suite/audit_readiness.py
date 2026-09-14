"""Administrative investigation progress from an authorized Engine projection only.

No corpus, inferred intent, semantic grading, mode-based findings or professional
qualification checks. Recorded completion and collected files are not effectiveness.
"""

from collections import Counter

from .store import DomainError, digest

REFERENCE_COLLECTIONS = {
    "control": "controls",
    "task": "tasks",
    "request": "requests",
    "artifact": "artifacts",
    "population": "populations",
    "selection": "selections",
    "workpaper": "workpapers",
    "review": "reviews",
}


def _ref(kind, row):
    result = {"kind": kind, "id": row["id"]}
    if row.get("version") is not None:
        result["version"] = row["version"]
    if kind == "artifact":
        result["sha256"] = row.get("sha256")
    return result


def _qualifiers(artifact):
    source = artifact.get("source", {})
    receipt = source.get("receipt", {}) if isinstance(source, dict) else {}
    original = receipt.get("source", {}) if isinstance(receipt, dict) else {}
    parts = [artifact.get("coverage", {}), source, original, original.get("provenance", {})]
    keys = {
        "origin",
        "fact_state",
        "operational_fact_status",
        "source_basis",
        "support_status",
        "population_basis",
        "classification",
        "custody_status",
        "custody_basis",
        "forecast_status",
        "model_version",
        "event_time_state",
        "source_period_start",
        "source_period_end",
        "availability_basis",
        "qualification",
        "source_scenario",
    }
    values = []
    for part in parts:
        if isinstance(part, dict):
            for key in sorted(keys & part.keys()):
                if isinstance(part[key], str):
                    values.append({"field": key, "value": part[key]})
    return values or [{"field": "qualifier", "value": "NOT_RECORDED_IN_PROJECTION"}]


def _review(workpaper, review):
    target = next(
        (
            v
            for v in workpaper.get("versions", [])
            if v["version"] == review.get("workpaper_version")
        ),
        None,
    )
    versions = workpaper.get("versions", [])
    latest = max((v["version"] for v in versions), default=None)
    contributors = [workpaper.get("prepared_by")] + [
        v.get("actor")
        for v in versions
        if (
            type(review.get("workpaper_version")) is int
            and v["version"] <= review["workpaper_version"]
        )
    ]
    known = bool(contributors) and all(isinstance(x, str) and x for x in contributors)
    actor = review.get("actor")
    comparison = "UNKNOWN"
    if known and isinstance(actor, str) and actor:
        comparison = "SAME_CONTRIBUTOR" if actor in contributors else "DISTINCT_CONTRIBUTOR"
    exact = target is not None and digest(target) == review.get("workpaper_version_digest")
    return {
        "reference": _ref("review", review),
        "workpaper_id": workpaper["id"],
        "workpaper_version": review.get("workpaper_version"),
        "recorded_kind": review.get("kind"),
        "recorded_status": review.get("status"),
        "target_digest_matches": exact,
        "targets_latest_version": exact and latest == review.get("workpaper_version"),
        "contributor_identity_comparison": comparison,
        "reviewer_membership_at_review": "NOT_AVAILABLE_IN_PROJECTION",
        "professional_qualification": "NOT_ASSESSED",
        "resolution_meaning": "RECORDED_WORKFLOW_STATUS_ONLY",
    }


def summarize(projection):
    """Pure report; caller must supply the current authorized Engine.get result."""
    if not isinstance(projection, dict) or not isinstance(projection.get("scope"), dict):
        raise DomainError("Authorized engagement projection required")
    for name in REFERENCE_COLLECTIONS.values():
        rows = projection.get(name, [])
        if not isinstance(rows, list) or any(
            not isinstance(r, dict) or not isinstance(r.get("id"), str) for r in rows
        ):
            raise DomainError("Typed projected workspace records required")
        if len({r["id"] for r in rows}) != len(rows):
            raise DomainError("Duplicate projected record identity")
    controls = projection.get("controls", [])
    control_ids = {c["id"] for c in controls}
    tasks = projection.get("tasks", [])
    requests = projection.get("requests", [])
    artifacts = projection.get("artifacts", [])
    artifact_by_id = {a["id"]: a for a in artifacts}
    workpapers = projection.get("workpapers", [])
    populations = projection.get("populations", [])
    reports = []
    for control in controls:
        cid = control["id"]
        ct = [t for t in tasks if t.get("control_id") == cid]
        cr = [r for r in requests if r.get("control_id") == cid]
        request_ids = {r["id"] for r in cr}
        ca = [
            a
            for a in artifacts
            if a.get("control_id") == cid
            or a.get("coverage", {}).get("control_id") == cid
            or a.get("request_id") in request_ids
            or any(a["id"] in r.get("artifact_ids", []) for r in cr)
        ]
        artifact_ids = {a["id"] for a in ca}
        cw = [w for w in workpapers if w.get("control_id") == cid]
        cp = [
            p
            for p in populations
            if p.get("control_id") == cid or p.get("artifact_id") in artifact_ids
        ]
        population_ids = {p["id"] for p in cp}
        selections = [
            s for s in projection.get("selections", []) if s.get("population_id") in population_ids
        ]
        issued = [
            r
            for r in cr
            if r.get("issued_at")
            or r.get("status")
            in {
                "ISSUED",
                "ACKNOWLEDGED",
                "IN_PROGRESS",
                "CLARIFICATION",
                "SUBMITTED",
                "ACCEPTED_FOR_PURPOSE",
                "CLOSED",
            }
        ]
        outstanding = [
            r
            for r in issued
            if r.get("status") in {"ISSUED", "ACKNOWLEDGED", "IN_PROGRESS", "CLARIFICATION"}
        ]
        linked = set()
        wp_refs = []
        missing = []
        for wp in cw:
            for version in wp.get("versions", []):
                refs = set(version.get("evidence_ids", []))
                if version.get("artifact_id"):
                    refs.add(version["artifact_id"])
                linked.update(refs)
                wp_refs.append(
                    {
                        "kind": "workpaper",
                        "id": wp["id"],
                        "version": version["version"],
                        "version_digest": digest(version),
                        "artifact_ids": sorted(refs),
                    }
                )
                missing.extend(
                    {"workpaper_id": wp["id"], "version": version["version"], "artifact_id": a}
                    for a in sorted(refs)
                    if a not in artifact_by_id
                )
        source_details = []
        stale = []
        for a in ca:
            original = a.get("source", {}).get("receipt", {}).get("source", {})
            identity = {
                k: original.get(k)
                for k in ("company", "branch", "system", "record", "version", "sha256")
            }
            exact = all(v is not None for v in identity.values())
            if original.get("sha256") and original["sha256"] != a.get("sha256"):
                stale.append(
                    {"reference": _ref("artifact", a), "reason": "SOURCE_RECEIPT_DIGEST_MISMATCH"}
                )
            if a.get("status") not in {None, "AVAILABLE"}:
                stale.append(
                    {
                        "reference": _ref("artifact", a),
                        "reason": "RECORDED_ARTIFACT_STATUS",
                        "recorded_status": a.get("status"),
                    }
                )
            source_details.append(
                {
                    "artifact": _ref("artifact", a),
                    "request_id": a.get("request_id"),
                    "source_identity": identity if exact else None,
                    "source_identity_status": "RECORDED" if exact else "NOT_RECORDED",
                    "qualifiers": _qualifiers(a),
                    "current_source_freshness": "UNKNOWN_NOT_QUERIED",
                    "original_byte_recheck": "NOT_PERFORMED_BY_THIS_REPORT",
                }
            )
        review_records = [
            _review(w, r)
            for w in cw
            for r in projection.get("reviews", [])
            if r.get("workpaper_id") == w["id"]
        ]
        reviewed = {
            r["workpaper_id"]
            for r in review_records
            if r["recorded_kind"] == "HUMAN"
            and r["targets_latest_version"]
            and r["contributor_identity_comparison"] == "DISTINCT_CONTRIBUTOR"
        }
        reasons = []

        def reason(code, refs, destination, reasons=reasons):
            reasons.append(
                {
                    "code": code,
                    "references": refs,
                    "navigation": {"workspace": destination},
                    "action_type": "OPEN_EXISTING_WORKSPACE_ONLY",
                }
            )

        if not issued:
            reason("NO_ISSUED_REQUEST", [_ref("control", control)], "requests")
        if outstanding:
            reason("OUTSTANDING_RESPONSE", [_ref("request", r) for r in outstanding], "requests")
        if artifact_ids - linked:
            reason(
                "RETAINED_ARTIFACT_WITHOUT_WORKPAPER_LINK",
                [_ref("artifact", artifact_by_id[a]) for a in sorted(artifact_ids - linked)],
                "workpapers",
            )
        provisional = [p for p in cp if p.get("status") == "PROVISIONAL"]
        if provisional:
            reason(
                "PROVISIONAL_POPULATION",
                [_ref("population", p) for p in provisional],
                "populations",
            )
        unreviewed = [w for w in cw if w["id"] not in reviewed]
        if unreviewed:
            reason(
                "NO_CURRENT_DISTINCT_CONTRIBUTOR_REVIEW_RECORD",
                [_ref("workpaper", w) for w in unreviewed],
                "reviews",
            )
        if stale:
            reason(
                "RECORDED_SOURCE_OR_ARTIFACT_WARNING", [s["reference"] for s in stale], "artifacts"
            )
        if missing:
            reason(
                "WORKPAPER_REFERENCES_MISSING_ARTIFACT",
                [{"kind": "artifact", "id": m["artifact_id"]} for m in missing],
                "workpapers",
            )
        procedures = []
        for task in ct:
            explicit = [
                w
                for w in cw
                if w.get("task_id") == task["id"] or w["id"] in task.get("workpaper_ids", [])
            ]
            procedures.append(
                {
                    "task": _ref("task", task),
                    "assigned_kind": task.get("kind", task.get("test_type")),
                    "recorded_status": task.get("status", "UNKNOWN"),
                    "recorded_conclusion": task.get("conclusion", "UNKNOWN"),
                    "workpaper_links": [_ref("workpaper", w) for w in explicit],
                    "procedure_evidence_linkage": "EXPLICIT_LINK_RECORDED"
                    if explicit
                    else "NOT_RECORDED",
                    "testing_verified": "NOT_ASSESSED",
                }
            )
        reports.append(
            {
                "control": _ref("control", control),
                "procedure_denominator": len(ct),
                "procedures": procedures,
                "task_status_counts": dict(Counter(t.get("status", "UNKNOWN") for t in ct)),
                "known_excluded_task_ids": [
                    t["id"] for t in ct if t.get("status") == "NOT_APPLICABLE"
                ],
                "requests": [_ref("request", r) for r in cr],
                "issued_requests": len(issued),
                "outstanding_request_ids": [r["id"] for r in outstanding],
                "sources": source_details,
                "populations": [
                    {
                        "reference": _ref("population", p),
                        "recorded_status": p.get("status", "UNKNOWN"),
                    }
                    for p in cp
                ],
                "selections": [_ref("selection", s) for s in selections],
                "workpapers": wp_refs,
                "reviews": review_records,
                "recorded_source_warnings": stale,
                "missing_artifact_links": missing,
                "reasons": reasons,
                "control_effectiveness": "NOT_ASSESSED",
                "procedure_testing_from_collection": "NOT_INFERRED",
            }
        )
    return {
        "schema_version": "1.0",
        "engagement_id": projection["id"],
        "engagement_revision": projection["revision"],
        "scope_sha256": digest(projection["scope"]),
        "status": "OBSERVABLE_ADMINISTRATIVE_PROGRESS_ONLY",
        "controls": reports,
        "denominators": {
            "scoped_controls": len(controls),
            "scoped_procedures": sum(r["procedure_denominator"] for r in reports),
            "known_not_applicable_tasks": sum(len(r["known_excluded_task_ids"]) for r in reports),
            "unassigned_or_out_of_scope_tasks": len(
                [t for t in tasks if t.get("control_id") not in control_ids]
            ),
        },
        "unassigned_or_out_of_scope_task_ids": [
            t["id"] for t in tasks if t.get("control_id") not in control_ids
        ],
        "unassigned_request_ids": [
            r["id"] for r in requests if r.get("control_id") not in control_ids
        ],
        "recorded_scope_exclusions": projection["scope"].get("exclusions", []),
        "scope_exclusion_qualification": "Recorded exclusions; not independently accepted",
        "limits": [
            "Collected/opened files establish neither understanding nor effectiveness.",
            "Manual conclusions and workflow statuses remain user-recorded assertions.",
            "Identity comparison establishes neither qualification nor professional independence.",
            "No hidden keys, mode inference, prose grading or source freshness query.",
            "Control-level workpaper links do not prove every assigned procedure was tested.",
        ],
    }


def report(engine, actor, engagement_id):
    return summarize(engine.get(actor, engagement_id))
