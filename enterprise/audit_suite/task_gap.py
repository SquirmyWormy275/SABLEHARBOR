"""Auditor-authored task gaps; a record of an observation, never an audit result."""

from copy import deepcopy

from .store import DomainError, digest, identifier

COMMAND = "task.gap.record"
CAUSES = {
    "MISSING_OPERATION",
    "UNCOLLECTED_SOURCE",
    "INSUFFICIENT_SOURCE",
    "DENIED_ACCESS",
}
DISPOSITIONS = {"OPEN", "FOLLOW_UP_REQUESTED", "RETEST_LINKED", "LIMITATION_RETAINED"}
MAX_GAPS = 2000


def require(ok, message, status=400):
    if not ok:
        raise DomainError(message, status=status)


def _one(rows, row_id, label):
    matches = [row for row in rows if row.get("id") == row_id]
    require(len(matches) == 1, f"Exact {label} unavailable", 409)
    return matches[0]


def _text(value):
    require(
        isinstance(value, str) and 20 <= len(value.strip()) <= 4000,
        "Bounded authored gap narrative required",
    )
    return value.strip()


def _artifact(engine, state, pin, permission):
    if pin is None:
        return None
    require(
        isinstance(pin, dict) and set(pin) == {"id", "sha256"},
        "Exact retained artifact pin required",
    )
    row = _one(state.get("artifacts", []), pin["id"], "retained artifact")
    require(
        permission != "learn" or row.get("audience", "LEARNER") == "LEARNER",
        "Retained artifact unavailable",
        403,
    )
    require(
        row.get("status") == "AVAILABLE" and row.get("sha256") == pin["sha256"],
        "Retained artifact pin changed",
        409,
    )
    try:
        engine.artifacts.read(row)
    except (DomainError, OSError, KeyError, TypeError) as error:
        raise DomainError("Retained artifact bytes unavailable or changed", status=409) from error
    source = row.get("source")
    receipt = source.get("receipt") if isinstance(source, dict) else None
    native = receipt.get("source") if isinstance(receipt, dict) else None
    if isinstance(native, dict):
        require(
            native.get("sha256") == row["sha256"],
            "Retained artifact and native source hashes disagree",
            409,
        )
    return {
        "id": row["id"],
        "sha256": row["sha256"],
        "native_source_pin": deepcopy(native) if isinstance(native, dict) else None,
    }


def _retest(state, reference, task_id):
    if reference is None:
        return None
    require(
        isinstance(reference, dict) and set(reference) == {"workpaper_id", "version"},
        "Exact retest workpaper reference required",
    )
    require(
        type(reference["version"]) is int and reference["version"] > 0,
        "Positive retest workpaper version required",
    )
    paper = _one(state.get("workpapers", []), reference["workpaper_id"], "retest workpaper")
    versions = [v for v in paper.get("versions", []) if v.get("version") == reference["version"]]
    require(
        len(versions) == 1 and task_id in versions[0].get("task_ids", []),
        "Retest must link the exact task and workpaper version",
        409,
    )
    return {**reference, "version_sha256": digest(versions[0])}


def handle(engine, state, payload, stamped):
    require(
        isinstance(payload, dict)
        and set(payload)
        == {
            "task_id",
            "cause",
            "owner_id",
            "disposition",
            "narrative",
            "artifact_pin",
            "retest",
            "predecessor_id",
        },
        "Exact task gap payload required",
    )
    require(state.get("phase") == "ACTIVE", "Active engagement required", 409)
    task = _one(state.get("tasks", []), payload["task_id"], "task")
    require(
        task.get("status") not in {"NOT_APPLICABLE", "EXCLUDED"}
        and task.get("applicable") is not False,
        "Current scoped procedure required",
        409,
    )
    require(
        isinstance(payload["cause"], str) and payload["cause"] in CAUSES,
        "Explicit gap cause required",
    )
    require(
        isinstance(payload["disposition"], str) and payload["disposition"] in DISPOSITIONS,
        "Explicit gap disposition required",
    )
    owner = payload["owner_id"]
    require(isinstance(owner, str) and owner, "Scoped gap owner required")
    try:
        membership = engine.store.membership(owner, state["id"])
    except DomainError as error:
        raise DomainError("Scoped gap owner required", status=403) from error
    require(membership in {"learn", "instruct"}, "Auditor gap owner required", 403)
    actor_permission = engine.store.membership(stamped["actor"], state["id"])
    artifact = _artifact(engine, state, payload["artifact_pin"], actor_permission)
    retest = _retest(state, payload["retest"], payload["task_id"])
    require(
        (payload["disposition"] == "RETEST_LINKED") == (retest is not None),
        "Retest-linked disposition and exact retest must agree",
    )
    prior_id = payload["predecessor_id"]
    history = state.setdefault("task_gaps", [])
    require(len(history) < MAX_GAPS, "Task gap history limit")
    predecessor = None
    if prior_id is not None:
        prior = _one(history, prior_id, "predecessor gap")
        require(
            prior.get("task_id") == payload["task_id"], "Predecessor must concern the same task"
        )
        prior_artifact = prior.get("artifact_pin")
        if prior_artifact:
            _artifact(
                engine, state, {k: prior_artifact[k] for k in ("id", "sha256")}, actor_permission
            )
        require(
            not any(r.get("predecessor_id") == prior_id for r in history),
            "Predecessor already has a successor",
            409,
        )
        predecessor = {"id": prior_id, "sha256": digest(prior)}
    history.append(
        {
            "id": identifier("GAP"),
            "task_id": payload["task_id"],
            "cause": payload["cause"],
            "owner_id": owner,
            "disposition": payload["disposition"],
            "narrative": _text(payload["narrative"]),
            "artifact_pin": artifact,
            "retest": retest,
            "predecessor_id": prior_id,
            "predecessor_sha256": predecessor["sha256"] if predecessor else None,
            "qualification": "AUTHOR_RECORDED_GAP_NOT_EVIDENCE_OR_AUDIT_CONCLUSION",
            "revision": state["revision"] + 1,
            **stamped,
        }
    )


def project(state):
    """Suppress the whole row when its exact task or artifact is not visible."""
    tasks = {t["id"] for t in state.get("tasks", [])}
    artifacts = {(a["id"], a.get("sha256")) for a in state.get("artifacts", [])}
    result = []
    visible_ids = set()
    for row in state.get("task_gaps", []):
        pin = row.get("artifact_pin")
        if row.get("task_id") not in tasks or (pin and (pin["id"], pin["sha256"]) not in artifacts):
            continue
        if row.get("predecessor_id") and row["predecessor_id"] not in visible_ids:
            continue
        result.append(row)
        visible_ids.add(row["id"])
    return result
