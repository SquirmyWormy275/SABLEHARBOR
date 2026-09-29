"""Explicit version-scoped procedure references; no execution or conclusion inference."""

from .store import DomainError


def validate_task_ids(state, control_id, value):
    if (
        not isinstance(value, list)
        or len(value) > 500
        or any(not isinstance(v, str) or not v or len(v) > 128 for v in value)
        or len(set(value)) != len(value)
    ):
        raise DomainError("Procedure references must be unique bounded task IDs")
    if not value:
        return []
    if control_id not in {c["id"] for c in state.get("controls", [])}:
        raise DomainError("Linked procedures require a current scoped workpaper control")
    for task_id in value:
        matches = [t for t in state.get("tasks", []) if t["id"] == task_id]
        if len(matches) != 1 or matches[0].get("control_id") != control_id:
            raise DomainError("Procedure must belong to the same scoped control")
        task = matches[0]
        if task.get("boundary_id") and task["boundary_id"] not in state.get("scope", {}).get(
            "boundaries", []
        ):
            raise DomainError("Procedure is outside the current boundary scope")
    return list(value)
