"""Explicit author assertions about exact originals; never verified reading or testing."""

from datetime import datetime

from .artifacts import MAX_BYTES
from .store import DomainError, canonical, digest, identifier
from .workpaper_links import validate_task_ids

CLASSIFICATION = "SELF_REPORTED_INSPECTION"
LIMIT = 10000


def require(condition, message):
    if not condition:
        raise DomainError(message)


def handle(state, payload, stamped, artifacts, command_id):
    fields = {"artifact_id", "sha256", "version", "locator", "observation"}
    require(fields <= set(payload) <= fields | {"task_id"}, "Exact inspection fields required")
    for name, limit in (("artifact_id", 256), ("locator", 1000), ("observation", 4000)):
        require(
            isinstance(payload[name], str)
            and bool(payload[name].strip())
            and len(payload[name]) <= limit,
            "Bounded nonempty " + name + " required",
        )
    rows = [a for a in state.get("artifacts", []) if a.get("id") == payload["artifact_id"]]
    require(len(rows) == 1, "Exact retained original required")
    artifact = rows[0]
    require(
        artifact.get("status") == "AVAILABLE" and artifact.get("audience", "LEARNER") == "LEARNER",
        "Available learner original required",
    )
    version = payload["version"]
    require(
        version is None or type(version) is int and version >= 0, "Exact original version required"
    )
    require(
        type(version) is type(artifact.get("version")) and version == artifact.get("version"),
        "Original version changed",
    )
    require(
        isinstance(payload["sha256"], str)
        and len(payload["sha256"]) == 64
        and all(c in "0123456789abcdef" for c in payload["sha256"]),
        "Exact original SHA256 required",
    )
    require(payload["sha256"] == artifact.get("sha256"), "Original digest changed")
    require(
        type(artifact.get("bytes")) is int and 0 <= artifact["bytes"] <= MAX_BYTES,
        "Bounded original required",
    )
    available = artifact.get("available_at")
    if available is None:
        available = (
            artifact.get("source", {}).get("receipt", {}).get("source", {}).get("available_at")
        )
    if available is not None:
        try:
            at = datetime.fromisoformat(available.replace("Z", "+00:00"))
            now = datetime.fromisoformat(state["simulated_at"].replace("Z", "+00:00"))
            require(
                at.tzinfo is not None and now.tzinfo is not None and at <= now,
                "Original unavailable at current simulated time",
            )
        except (ValueError, TypeError, AttributeError) as error:
            raise DomainError("Explicit valid original availability required") from error
    task_id = payload.get("task_id")
    if task_id is not None:
        tasks = [t for t in state.get("tasks", []) if t.get("id") == task_id]
        require(isinstance(task_id, str) and len(tasks) == 1, "Existing scoped procedure required")
        task = tasks[0]
        require(
            task.get("status") not in {"EXCLUDED", "NOT_APPLICABLE"}
            and task.get("applicable") is not False,
            "Active procedure required",
        )
        validate_task_ids(state, task.get("control_id"), [task_id])
    records = state.setdefault("artifact_inspections", [])
    require(isinstance(records, list) and len(records) < LIMIT, "Inspection record limit reached")
    artifacts.read(artifact)
    records.append(
        {
            "id": identifier("INSPECT"),
            "artifact_id": artifact["id"],
            "sha256": artifact["sha256"],
            "version": version,
            "locator": payload["locator"],
            "observation": payload["observation"],
            "task_id": task_id,
            "classification": CLASSIFICATION,
            "command_id": command_id,
            "payload_sha256": digest(payload),
            "recorded_revision": state["revision"] + 1,
            **stamped,
        }
    )

    artifacts.read(artifact)


def inventory(state, history, audited_actor):
    """Link assertions to verified command actors, without inferring unrecorded activity."""
    events = {(h["revision"], h["command_id"]): h for h in history}
    artifacts = {
        a["id"]: a for a in state.get("artifacts", []) if a.get("audience", "LEARNER") == "LEARNER"
    }
    linked, unresolved = [], 0
    for row in state.get("artifact_inspections", []):
        event = events.get((row.get("recorded_revision"), row.get("command_id")))
        artifact = artifacts.get(row.get("artifact_id"))
        payload = event.get("command", {}).get("payload") if event else None
        fields = {"artifact_id", "sha256", "version", "locator", "observation"}
        payload_matches = (
            isinstance(payload, dict)
            and fields <= set(payload) <= fields | {"task_id"}
            and digest(payload) == row.get("payload_sha256")
            and canonical(payload) == canonical({key: row.get(key) for key in payload})
        )
        if (
            not payload_matches
            or not event
            or event["command"].get("kind") != "artifact.inspection.record"
            or event["actor"] != row.get("actor")
            or not artifact
            or artifact.get("sha256") != row.get("sha256")
            or type(artifact.get("version")) is not type(row.get("version"))
            or artifact.get("version") != row.get("version")
            or row.get("classification") != CLASSIFICATION
        ):
            unresolved += 1
            continue
        linked.append(
            {
                **row,
                "history_sha256": event["hash"],
                "attribution": "AUDITED_ACTOR"
                if event["actor"] == audited_actor
                else "OTHER_ACTOR",
            }
        )
    return {
        "status": CLASSIFICATION,
        "records": linked,
        "audited_actor_count": sum(r["attribution"] == "AUDITED_ACTOR" for r in linked),
        "other_actor_count": sum(r["attribution"] == "OTHER_ACTOR" for r in linked),
        "unresolved_record_count": unresolved,
        "qualification": "AUTHOR_ASSERTION_NOT_VERIFIED_READING_UNDERSTANDING_TESTING_OR_GRADE",
        "absence": "NO_RECORDED_ASSERTION_DOES_NOT_ESTABLISH_NO_INSPECTION",
    }
