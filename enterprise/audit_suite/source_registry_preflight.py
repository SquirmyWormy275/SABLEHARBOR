"""Read-only source-route census before a fresh, source-complete audit registry.

Control-level source references are discovery leads, never procedure evidence.
This module cannot activate an engagement or certify a registry as complete.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path

from .company_federation import FederatedCompanyStore


class PreflightError(ValueError):
    """The frozen task/source inputs cannot be safely reconciled."""


def read_state(path: Path) -> dict:
    """Read the existing engagement without constructing an initializing store."""
    path = Path(path).resolve(strict=True)
    with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise PreflightError("Audit state database integrity failed")
        rows = db.execute("SELECT state FROM engagements").fetchall()
    if len(rows) != 1:
        raise PreflightError("One frozen engagement per side required")
    return json.loads(rows[0][0])


def _unique(rows: list[dict], key: str, count: int, label: str) -> dict:
    if len(rows) != count or any(not isinstance(row, dict) or not row.get(key) for row in rows):
        raise PreflightError(f"Exact {count} {label} rows required")
    indexed = {row[key]: row for row in rows}
    if len(indexed) != count:
        raise PreflightError(f"Duplicate {label} identity")
    return indexed


def analyze(
    states: dict[str, dict],
    screen_rows: list[dict],
    task_routes: list[dict],
    control_routes: list[dict],
    source_families: list[dict],
    registries: dict[str, FederatedCompanyStore],
    *,
    expected_controls: int = 70,
    expected_tasks: int = 409,
) -> dict:
    """Join the complete task program to selected native components; grant no credit."""
    if set(states) != {"A", "B"} or set(registries) != {"A", "B"}:
        raise PreflightError("Exact paired sides required")
    if not all(
        isinstance(x, list) for x in (screen_rows, task_routes, control_routes, source_families)
    ):
        raise PreflightError("Exact source-plan lists required")
    result = {}
    paired_control_ids = paired_task_ids = None
    for side in ("A", "B"):
        state = states[side]
        controls = _unique(state["controls"], "id", expected_controls, "control")
        tasks = _unique(state["tasks"], "id", expected_tasks, "task")
        if paired_control_ids is not None and set(controls) != paired_control_ids:
            raise PreflightError("Paired control IDs differ")
        if paired_task_ids is not None and set(tasks) != paired_task_ids:
            raise PreflightError("Paired task IDs differ")
        paired_control_ids, paired_task_ids = set(controls), set(tasks)
        screen = _unique(
            [x for x in screen_rows if x["side"] == side], "task_id", expected_tasks, "task screen"
        )
        if set(screen) != set(tasks):
            raise PreflightError("Task screen does not enumerate the frozen task program")
        routes = {x["task_id"]: x for x in task_routes if x["side"] == side}
        if len(routes) != sum(x["side"] == side for x in task_routes) or not set(routes) <= set(
            tasks
        ):
            raise PreflightError("Unmatched task routes duplicate or leave the program")
        if set(routes) != {
            tid for tid, row in screen.items() if not row["matched_retained_sources"]
        }:
            raise PreflightError("Unmatched routes and complete task screen disagree")
        planned_controls = {x["control_id"]: x for x in control_routes if x["side"] == side}
        if len(planned_controls) != sum(x["side"] == side for x in control_routes):
            raise PreflightError("Duplicate control route")
        if set(planned_controls) != {r["control_id"] for r in routes.values() if r["control_id"]}:
            raise PreflightError("Unmatched control routes disagree")
        family_rows = [x for x in source_families if x["side"] == side]
        families = {x["component_id"]: x for x in family_rows}
        if len(families) != len(family_rows):
            raise PreflightError("Duplicate source component inventory")
        registry = registries[side]
        selected = set(registry._manifest["components"])
        selected_aliases = {
            component_id: list(component["systems"])
            for component_id, component in registry._manifest["components"].items()
        }
        collected: dict[str, set[str]] = {cid: set() for cid in controls}
        for request in state["requests"]:
            cid = request.get("control_id")
            if cid in collected:
                for copy in request.get("company_collections", []):
                    component = copy.get("source_identity", {}).get("source_store_id")
                    if component:
                        collected[cid].add(component)
        control_rows = []
        for cid, control in sorted(controls.items()):
            lead = planned_controls.get(cid)
            leads = []
            for component_id, family in sorted(families.items()):
                if cid not in family["explicit_control_ids"]:
                    continue
                classes = family["classifications"]
                if (
                    not classes
                    or not set(classes)
                    <= {
                        "DOCUMENTARY_NOT_OPERATING_FACT",
                        "AUTHORED_ACTIVITY_OR_REFERENCE_NOT_OPERATING_FACT",
                    }
                    or sum(classes.values()) != family["native_versions"]
                ):
                    raise PreflightError("Source-family classification or count differs")
                kind = (
                    "DOCUMENTARY_DESIGN_ONLY"
                    if set(classes) == {"DOCUMENTARY_NOT_OPERATING_FACT"}
                    else "AUTHORED_REFERENCE_NOT_OPERATING_FACT"
                    if set(classes) == {"AUTHORED_ACTIVITY_OR_REFERENCE_NOT_OPERATING_FACT"}
                    else "MIXED_REFERENCE_NOT_OPERATING_FACT"
                )
                leads.append(
                    {
                        "component_id": component_id,
                        "classification": kind,
                        "selected_in_proposed_registry": component_id in selected,
                        "native_version_count": family["native_versions"],
                    }
                )
            for component_id in sorted(collected[cid] - set(families)):
                leads.append(
                    {
                        "component_id": component_id,
                        "classification": "CURRENT_RETAINED_CONTROL_ASSOCIATION_ONLY",
                        "selected_in_proposed_registry": component_id in selected,
                        "native_version_count": None,
                    }
                )
            flags = []
            if not control.get("owner_ids"):
                flags.append("OWNER_UNASSIGNED")
            assignment = control.get("assignment", {}).get("status")
            if assignment == "PROPOSED_CURRENT_ASSIGNMENT":
                flags.append("PROPOSED_CONTACT_NOT_ACCEPTED_OPERATING_AUTHORITY")
            else:
                flags.append("OWNER_ASSIGNMENT_REVIEW_REQUIRED")
            if lead and lead["existing_native_route"] == "DOCUMENTARY_ONLY_IN_PINNED_PORTFOLIO":
                flags.append("NATIVE_ACTIVITY_DISCOVERY_OR_AUTHORIZED_NONOCCURRENCE_REQUIRED")
            if not any(
                x["classification"]
                in {
                    "AUTHORED_REFERENCE_NOT_OPERATING_FACT",
                    "MIXED_REFERENCE_NOT_OPERATING_FACT",
                }
                for x in leads
            ):
                flags.append("DOCUMENTS_DO_NOT_ESTABLISH_OPERATION")
            if leads and not any(x["selected_in_proposed_registry"] for x in leads):
                flags.append("REFERENCED_COMPONENT_OUTSIDE_PROPOSED_REGISTRY")
            control_rows.append(
                {
                    "control_id": cid,
                    "owner_ids": control.get("owner_ids", []),
                    "candidate_components": leads,
                    "active_retained_control_components": sorted(collected[cid]),
                    "flags": flags,
                }
            )
        by_control = {x["control_id"]: x for x in control_rows}
        task_rows = []
        for tid, task in sorted(tasks.items()):
            old = screen[tid]
            cid = task.get("control_id")
            if old["control_id"] != cid or (cid is not None and cid not in controls):
                raise PreflightError("Task/control identity changed since task screen")
            route = routes.get(tid)
            flags = ["CLAUSE_PERIOD_POPULATION_AND_QUALIFIED_REVIEW_REQUIRED"]
            if cid is None:
                flags.append("OWNER_SERVICE_SCOPE_FACTS_REQUIRED")
                candidates = []
            else:
                flags += by_control[cid]["flags"]
                candidates = [x["component_id"] for x in by_control[cid]["candidate_components"]]
            if route:
                flags.append(route["next_action"])
                if route.get("applicability_status") == "NOT_ASSESSED":
                    flags.append("CONDITIONAL_APPLICABILITY_UNRESOLVED")
                if route["next_action"].startswith("DOCUMENTARY") and cid and collected[cid]:
                    flags.append("OLDER_ROUTE_REQUIRES_CURRENT_SOURCE_RESCREEN")
            elif old["matched_retained_sources"]:
                flags.append("PRIOR_CONTROL_LEVEL_ASSOCIATION_NOT_TASK_CLAUSE_CREDIT")
                if old.get("applicability_status") == "NOT_ASSESSED":
                    flags.append("CONDITIONAL_APPLICABILITY_UNRESOLVED")
            else:
                raise PreflightError("Task has neither unmatched route nor screened association")
            task_rows.append(
                {
                    "task_id": tid,
                    "control_id": cid,
                    "kind": task["kind"],
                    "current_status": task["status"],
                    "current_conclusion": task["conclusion"],
                    "candidate_component_ids": sorted(set(candidates)),
                    "selected_candidate_component_ids": sorted(set(candidates) & selected),
                    "flags": sorted(set(flags)),
                    "task_credit": False,
                }
            )
        result[side] = {
            "engagement_id": state["id"],
            "revision": state["revision"],
            "frozen_binding_matches_proposal": state.get("company_source_binding")
            == registry.binding,
            "proposed_profile_id": registry.profile_id,
            "proposed_registry_sha256": registry.registry_sha256,
            "selected_components": selected_aliases,
            "selected_components_not_indexed_by_reference_plan": sorted(selected - set(families)),
            "counts": {
                "controls": len(control_rows),
                "tasks": len(task_rows),
                "unmatched_task_routes": len(routes),
                "prior_control_level_associations": len(task_rows) - len(routes),
                "control_flags": dict(
                    sorted(Counter(f for x in control_rows for f in x["flags"]).items())
                ),
                "task_flags": dict(
                    sorted(Counter(f for x in task_rows for f in x["flags"]).items())
                ),
            },
            "controls": control_rows,
            "tasks": task_rows,
        }
    return {
        "schema": "SH_SOURCE_COMPLETE_REGISTRY_READONLY_PREFLIGHT_V1",
        "status": "SOURCE_COMPLETE_NOT_ESTABLISHED",
        "source_complete": False,
        "qualification": (
            "Exact component routes and control-level references are only discovery leads. "
            "A fresh registry, ordinary company collection, service/PHI and owner decisions, "
            "period populations, clause workpapers, and qualified review remain separate gates."
        ),
        "sides": result,
    }
