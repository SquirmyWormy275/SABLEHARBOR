"""Exact B01 calculations with task-specific original custody and compact observations.

The accepted 52-task method still examines every ordinary retained input at the
actual cutoff. Only documentary presentation changes: unrelated raw documents
are not repeated in other tasks, and a calculated result already in the same
workpaper is linked by its exact digest instead of quoted a second time.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path

from . import source_identity_methods as identity
from . import source_workforce_methods as workforce
from .fresh_sec003_procedure import require
from .store import digest

WORKFORCE_SHA256 = "5e7f77a5f4dbe7359a57d9bd5664b61674295169b4b09fbdec239c9cf4e05770"
retained_inputs = workforce.retained_inputs

CURRENT_FIELDS = {
    1: ("affiliation_context", "authority_context", "actual_account_version_count", "grant_tests"),
    2: ("authority_context", "grant_tests", "permission_tests"),
    3: (
        "affiliation_context",
        "authority_context",
        "grant_tests",
        "retained_duty_authority_limits",
    ),
    4: ("authority_context", "permission_tests"),
    5: ("authority_context", "grant_tests", "permission_tests", "periodic_reviews"),
    6: ("authority_context", "permission_tests"),
    7: (
        "affiliation_context",
        "monthly_denominators",
        "periodic_reviews",
        "retained_duty_authority_limits",
    ),
}
CURRENT_ROLES = {
    "affiliation_context": {"affiliation_register"},
    "authority_context": {"company_authority"},
    "actual_account_version_count": {"*ACCOUNT_STATES*"},
    "grant_tests": {"*ACCOUNT_STATES*", "access_approvals", "entitlement_catalogue"},
    "permission_tests": {"*ACCOUNT_STATES*", "permission_activity", "workspace_object"},
    "monthly_denominators": {"*ACCOUNT_STATES*", "denominator_snapshot"},
    "periodic_reviews": {
        "*ACCOUNT_STATES*",
        "periodic_review_population",
        "periodic_review_decisions",
    },
    "retained_duty_authority_limits": {"duty_authorizations"},
}


def task_contracts():
    require(
        hashlib.sha256(Path(workforce.__file__).read_bytes()).hexdigest() == WORKFORCE_SHA256,
        "Exact accepted workforce calculation dependency required",
    )
    return workforce.task_contracts()


class _MethodInputs:
    """Track actual method queries on an already validated complete History.

    No input is sliced before examination. Exact queried originals, plus their
    retained native-reference dependencies (including late unsupported targets),
    determine custody membership. Broad query results are conservative method
    inputs; the purpose is to remove unrelated components, never causal history.
    """

    def __init__(self, history):
        self.history = history
        self.used = set()

    def __getattr__(self, name):
        return getattr(self.history, name)

    def selected(self, component, role=None):
        rows = self.history.selected(component, role)
        self.used.update(r["artifact_id"] for r in rows)
        return rows

    def exact(self, component, role, record, version=1):
        row = self.history.exact(component, role, record, version)
        self.used.add(row["artifact_id"])
        return row

    def resolve(self, row, reference):
        self.used.add(row["artifact_id"])
        target, state = self.history.resolve(row, reference)
        if target is not None:
            self.used.add(target["artifact_id"])
        return target, state


def _dependencies(history, used):
    """Retain exact transitive native originals without name/digest aliases."""
    used = set(used)
    while True:
        before = len(used)
        origins = {identity.identity(r["source"]) for r in history.rows if r["artifact_id"] in used}
        for join in history.joins:
            if identity.identity(join["from"]) in origins and join["to"] is not None:
                target = history.index[identity.identity(join["to"])]
                used.add(target["artifact_id"])
        if len(used) == before:
            return [r for r in history.rows if r["artifact_id"] in used]


def _current_inputs(history, fields):
    roles = set().union(*(CURRENT_ROLES[field] for field in fields))
    return {
        r["artifact_id"]
        for r in history.selected("workforce")
        if r["logical_system"] in roles
        or (
            "*ACCOUNT_STATES*" in roles
            and r["logical_system"].startswith("account_")
            and "state" in r["document"]
        )
    }


def _result_inputs(history, result):
    """Preserve custody for every retained native source actually reported."""
    used = set()
    for _, reference in identity.references(result):
        target = history.index.get(identity.identity(reference))
        if target is not None and reference.get("sha256") == target["source"]["sha256"]:
            used.add(target["artifact_id"])
    return used


def _summary(result):
    """Named actual calculations stay visible without repeating their documents."""
    if "selected_groups" in result:
        groups = result["selected_groups"]
        current = result["company_workforce_access"].get("selected_attributes") or {}
        return {
            "selected_methods": {name: value["state"] for name, value in groups.items()},
            "current_attribute_counts": {
                name: len(value) if isinstance(value, (list, dict)) else value
                for name, value in current.items()
            },
            "missing_selected_inputs": result["missing_selected_inputs"],
        }
    return {
        "selected_methods": {
            name: value["state"] for name, value in result["method_results"].items()
        },
        "performed_attributes": [a["attribute"] for a in result["performed_attributes"]],
        "exception_attributes": [
            a["attribute"] for a in result["performed_attributes"] if a["exception"]
        ],
        "missing_selected_inputs": result["missing_selected_inputs"],
    }


def _compact_custody(task_id, rows, result, *, boundary_only=False):
    result_hash = digest(result)
    observations = []
    # A missing method can have no relevant original. This one retained custody
    # witness is explicitly an input boundary, never evidence of nonoccurrence.
    for start in range(0, len(rows), 20):
        part = rows[start : start + 20]
        observations.append(
            {
                "id": "B01-INPUTS-"
                + hashlib.sha256(task_id.encode()).hexdigest()
                + f"-{start // 20 + 1}",
                "status": "OBSERVED",
                "facts": {
                    "task_id": task_id,
                    "exact_task_result_sha256": result_hash,
                    "calculated_attributes_location": "workpaper.examination",
                    "actual_native_originals": [identity.custody(r) for r in part],
                    "method_input_custody_part": start // 20 + 1,
                    "complete_method_input_count": len(rows),
                    "input_boundary_witness_only": boundary_only,
                    "missing_original_is_not_event_nonoccurrence": True,
                    "unrelated_raw_documents_quoted": False,
                    "actual_calculation_summary": _summary(result) if start == 0 else None,
                },
                "evidence": [
                    {
                        "artifact_id": r["artifact_id"],
                        "sha256": r["artifact_sha256"],
                        "locator": "$; exact method query/native dependency; "
                        "complete recalculation retained in workpaper.examination",
                    }
                    for r in part
                ],
            }
        )
    return observations


def inspections(records, *, as_of, scratch_root=None):
    """Preserve exact accepted results/dispositions while reducing repeated custody."""
    task_contracts()  # Exact code/instruction checks precede any method output.
    # All inputs, every permission attempt and every version are examined by the
    # unchanged method. Its fresh results are not previous audit outcomes.
    calculated = workforce.inspections(records, as_of=as_of, scratch_root=scratch_root)
    history = identity.History(records, as_of)
    group_inputs, additional_inputs = {}, {}
    for name, method in identity.GROUP_METHODS.items():
        tracked = _MethodInputs(history)
        try:
            method(tracked)
        except identity.MissingOriginal:
            pass
        group_inputs[name] = tracked.used
    authored = workforce.authored_contracts()
    for task in authored["tasks"].values():
        for name, method in workforce.task_methods(task):
            if name not in additional_inputs:
                tracked = _MethodInputs(history)
                try:
                    method(tracked)
                except identity.MissingOriginal:
                    pass
                additional_inputs[name] = tracked.used
    for inspected in calculated:
        task_id, result = inspected["task_id"], inspected["result"]
        if "selected_groups" in result:
            used = set().union(*(group_inputs[name] for name in result["selected_groups"]))
            context = result["company_workforce_access"]
            if context["state"] == "EXAMINED_SELECTED_ORIGINALS":
                number = int(result["authored_task"]["control_id"][-3:])
                used.update(_current_inputs(history, CURRENT_FIELDS[number]))
        else:
            used = set().union(*(additional_inputs[name] for name in result["method_results"]))
        used.update(_result_inputs(history, result))
        rows = _dependencies(history, used)
        boundary_only = not rows
        if boundary_only:
            rows = [history.rows[0]]
        inspected["artifact_ids"] = [r["artifact_id"] for r in rows]
        inspected["observations"] = _compact_custody(
            task_id, rows, result, boundary_only=boundary_only
        )
    return calculated


def input_roles(records, *, as_of):
    """Engineering description of the fully validated held input; no audit credit."""
    task_contracts()
    history = identity.History(records, as_of)
    return dict(Counter(r["source"]["system"] for r in history.rows))
