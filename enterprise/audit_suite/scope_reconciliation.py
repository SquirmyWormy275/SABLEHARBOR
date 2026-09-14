"""Versioned scope changes preserve original audit work and evidence boundaries."""

from copy import deepcopy

from .organization import ASSERTIONS, snapshot
from .programs import dependency_tasks, ism_tasks
from .scope import control_projection
from .store import DomainError, digest


def apply(engine, state: dict, revised: dict, rationale: str, stamped: dict) -> None:
    if digest(revised) == digest(state["scope"]):
        raise DomainError("Scope is unchanged")
    org = snapshot(engine.repository, as_of=revised["period_start"])
    controls = control_projection(
        revised, repository=engine.repository, program_pack=engine.program_pack
    )
    if revised["programs"] == ["FINANCIAL"] and not revised.get("control_ids"):
        accounts = {a["id"] for a in revised["accounts"]}
        candidates = {
            cid
            for process in org["financial_model"]["processes"]
            if accounts.intersection(process["account_ids"])
            for cid in process["candidate_control_ids"]
        }
        controls = [c for c in controls if c["id"] in candidates]
    if not controls:
        raise DomainError("Revised scope has no supporting control implementations")
    assignments = {a["control_id"]: a for a in org["control_assignments"]}
    epoch = state.get("generation_epoch", 0) + 1
    old_epoch = state.get("generation_epoch", 0)
    tasks = []
    for control in controls:
        assignment = assignments[control["id"]]
        control["assignment"] = assignment
        control["owner_ids"] = (
            [assignment["primary_person_id"]] if assignment["primary_person_id"] else []
        )
        for boundary in revised["boundaries"]:
            kinds = ["TOD", "IMPLEMENTATION"] + (
                [] if revised["temporal_basis"] == "POINT_IN_TIME" else ["TOE"]
            )
            for kind in kinds:
                tasks.append(
                    {
                        "id": f"TASK-E{epoch}-{control['id']}-{boundary}-{kind}",
                        "control_id": control["id"],
                        "boundary_id": boundary,
                        "title": f"{kind}: {control['title']}",
                        "kind": kind,
                        "owner_id": assignment["primary_person_id"],
                    }
                )
            for duty in control.get("additional_duties", []):
                tasks.append(
                    {
                        "id": f"TASK-E{epoch}-{control['id']}-{boundary}-{duty['id']}",
                        "control_id": control["id"],
                        "boundary_id": boundary,
                        "title": duty["procedure"],
                        "kind": "ADDITIONAL_DUTY",
                        "requirement_ids": duty["requirement_ids"],
                        "test": duty["acceptance_test"],
                        "owner_id": assignment["primary_person_id"],
                    }
                )
    for account in revised.get("accounts", []) if "FINANCIAL" in revised["programs"] else []:
        for assertion in account["assertions"]:
            tasks.append(
                {
                    "id": f"TASK-E{epoch}-{account['id']}-{assertion}",
                    "title": f"{account['name']} — {ASSERTIONS[assertion]}",
                    "account_id": account["id"],
                    "assertion": assertion,
                    "kind": "SUBSTANTIVE",
                    "frameworks": ["FINANCIAL"],
                    "risk_rationale": account["risk_rationale"],
                    "planned_procedures": account["planned_procedures"],
                    "jurisdiction": revised["financial_audit_jurisdiction"],
                }
            )
    for task in ism_tasks(revised, engine.repository):
        tasks.append({**task, "id": f"E{epoch}-" + task["id"]})
    for task in dependency_tasks(revised, engine.program_pack):
        tasks.append({**task, "id": f"E{epoch}-" + task["id"]})
    for task in tasks:
        task.update(
            status="NOT_STARTED",
            conclusion="NOT_RUN",
            note="",
            history=[],
            scope_version=epoch,
            coverage=deepcopy(revised),
            applicability="CURRENT_SCOPE",
        )
    state.setdefault("scope_history", []).append(
        {
            "scope": deepcopy(state["scope"]),
            "controls": deepcopy(state["controls"]),
            "people": deepcopy(state["people"]),
            "organization": deepcopy(state.get("organization", {})),
            "generation_epoch": old_epoch,
            "world_digest": state.get("generation", {}).get("world_digest"),
            "rationale": rationale,
            **stamped,
        }
    )
    # Metadata marks prior scope; original conclusions, immutable samples and
    # retained bytes are never rewritten or silently carried forward as assurance.
    for task in state["tasks"]:
        task.setdefault("scope_version", old_epoch)
        task.setdefault("coverage", deepcopy(state["scope"]))
        task["applicability"] = "PRIOR_SCOPE_REQUIRES_REASSESSMENT"
    for request in state["requests"]:
        request.setdefault("plan_epoch", old_epoch)
        request.setdefault("scope_version", old_epoch)
    for population in state["populations"]:
        population.setdefault("scope_version", old_epoch)
        population["scope_reassessment"] = "REQUIRED_FOR_REUSE"
    current_people = {p["id"]: p for p in state["people"]}
    for person in org["canonical_people"] + org["proposed_people"]:
        current_people[person["person_id"]] = {
            **person,
            "id": person["person_id"],
            "name": person.get("name", person.get("display_name", person["person_id"])),
            "title": person.get("title", person.get("role_title", "")),
        }
    state["people"] = list(current_people.values())
    state["organization"] = {
        key: deepcopy(org[key])
        for key in (
            "snapshot_digest",
            "source_revision",
            "repository_acceptance_status",
            "reconciliation",
        )
        if key in org
    }
    state["scope"] = revised
    state["controls"] = controls
    state["tasks"].extend(tasks)
    state["generation_epoch"] = epoch
    state["resume_active_after_generation"] = state["phase"] == "ACTIVE"
    state["phase"] = "CONFIGURING"
    state["generation"] = {
        "state": "NOT_STARTED",
        "completed": 0,
        "total": len(controls) * len(revised["boundaries"]),
        "errors": [],
        "stage": "Revised scope requires generation",
    }
    state["scope_reconciliation_required"] = True
