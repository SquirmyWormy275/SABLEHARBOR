"""Explicit authored procedure associations, never inferred execution or grading."""

from .store import DomainError, digest
from .workpaper_links import validate_task_ids


def validate_authored_tasks(state, controls, value):
    if state is None:
        raise DomainError("Scoped state required for authored procedure links")
    if (
        not isinstance(value, list)
        or len(value) > 500
        or any(not isinstance(v, str) or not v or len(v) > 128 for v in value)
        or len(set(value)) != len(value)
    ):
        raise DomainError("Authored procedure links require unique bounded task IDs")
    for task_id in value:
        matches = [t for t in state.get("tasks", []) if t.get("id") == task_id]
        if len(matches) != 1 or matches[0].get("control_id") not in controls:
            raise DomainError("Authored procedure must belong to an issue's scoped control")
        task = matches[0]
        if task.get("applicability", "CURRENT_SCOPE") != "CURRENT_SCOPE":
            raise DomainError("Authored procedure must belong to the current scope")
        validate_task_ids(state, task.get("control_id"), [task_id])
    return list(value)


def inventory(expectation, controls, artifact_ids, state):
    authored = expectation.get("task_ids", [])
    try:
        valid = validate_authored_tasks(state, set(controls), authored)
        status = "EXPLICIT_AUTHORED_LINKS" if valid else "UNMAPPED"
    except DomainError:
        valid, status = [], "UNRESOLVED_IN_SELECTED_SCOPE"
    associated = []
    for wp in state.get("workpapers", []):
        for version in wp.get("versions", []):
            try:
                declared = validate_task_ids(
                    state, wp.get("control_id"), version.get("task_ids", [])
                )
            except DomainError:
                continue
            matched = sorted(set(valid) & set(declared))
            if not matched:
                continue
            refs = set(version.get("evidence_ids", []))
            if version.get("artifact_id"):
                refs.add(version["artifact_id"])
            associated.append(
                {
                    "id": wp["id"],
                    "version": version["version"],
                    "version_sha256": digest(version),
                    "task_ids": matched,
                    "source_artifact_ids": sorted(refs & artifact_ids),
                    "actor": version.get("actor"),
                    "prepared_by": wp.get("prepared_by"),
                    "recorded_conclusion": version.get("conclusion"),
                }
            )
    return {
        "authored_task_ids": list(authored),
        "task_mapping_status": status,
        "task_linked_workpaper_versions": associated,
    }
