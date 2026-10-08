"""Dedicated ordinary-collection and workpaper path for scope dependencies.

Uses an independently accepted bound shared-company workroom. These tasks have
no control owner, control population or test sample. Every source still comes
through an ordinary PBC and the actual engagement's collection receipt.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .company_store import _time
from .fresh_sec003_procedure import require
from .persistent_company_journey import write
from .source_library_audit import discover_history, file_sha
from .source_library_security_execution import command
from .source_scope_methods import CONTRACTS, FAMILIES, TASKS, examine
from .store import canonical

SCHEMA = "SH_ROOT_COLLECTED_SCOPE_DEPENDENCY_METHOD_REVIEW_V1"
VERDICT = "PASS_COLLECTED_SCOPE_FACTS_AND_DEPENDENCY_WRITER_SELECTED_BOUNDARY"
SYSTEMS = (
    "transition.provider_contract",
    "transition.contract_authority",
    "transition.contract_clearance",
    "transition.contract_approval",
    "transition.counterparty_acceptance",
    "transition.site_installation",
    "transition.site_commissioning",
    "transition.site_release",
    "transition.exception_event",
    "phi_ba.operation_scope",
    "phi_ba.legal_decision",
    "phi_ba.contract_authority",
    "phi_ba.contract_approval",
    "phi_ba.counterparty_acceptance",
    "phi_ba.contract_register",
    "phi_ba.flow_register",
    "phi_ba.exception_register",
    "person-access-history.company_authority",
    "person-access-history.affiliation_register",
    "person-access-history.service_delegation",
    "person-access-history.contractor_relationship",
    "person-access-history.account_system_inventory",
    "person-access-history.entitlement_catalogue",
    "govapp.board_decision",
    "govapp.ceo_delegation",
    "govapp.control_mapping",
    "govapp.selected_application",
    "legprovision.provision_locator",
    "legprovision.obligation_snapshot",
    "legprovision.overlay_reconciliation",
    "assuranceops.assurance_programme",
    "assuranceops.assurance_scope",
    "assuranceops.assurance_independence",
    "assuranceops.assurance_description",
    "assuranceops.assurance_review",
)


def _tasks(room):
    state = room.state()
    selected = [t for t in state["tasks"] if t["id"] in TASKS]
    require(
        len(selected) == 2
        and {t["id"] for t in selected} == set(TASKS)
        and all(
            t.get("kind") == "SCOPE_DEPENDENCY"
            and t.get("control_id") is None
            and t.get("scope") == state["scope"]
            for t in selected
        ),
        "Exact current source-dependency tasks required",
    )
    return state


def _gate(room, review):
    approval = review.read()
    pins = {
        "scope_method_module_sha256": Path(__file__).with_name("source_scope_methods.py"),
        "scope_writer_module_sha256": Path(__file__),
        "full_scope_pair_module_sha256": Path(__file__).with_name("full_scope_company_pair.py"),
        "workpaper_links_sha256": Path(__file__).with_name("workpaper_links.py"),
    }
    require(
        approval.get("schema") == SCHEMA
        and approval.get("verdict") == VERDICT
        and approval.get("source_execution_authorized") is True
        and approval.get("selected_task_ids") == list(TASKS)
        and approval.get("task_contracts") == CONTRACTS
        and all(file_sha(path) == approval.get(name) for name, path in pins.items()),
        "Exact independently reviewed scope content/writer dependencies required",
    )
    room.session._context(room.engine, room.auditor, room.engagement)
    _tasks(room)
    return approval


def acquire_scope(room, *, review, task_id, systems, purpose, as_of=None):
    """Request source facts without assigning an invented control/person owner."""
    _gate(room, review)
    require(task_id in TASKS, "Current scope dependency required")
    systems = tuple(systems)
    state = _tasks(room)
    require(
        systems
        and len(set(systems)) == len(systems)
        and all(system in SYSTEMS for system in systems),
        "Declared distinct scope native systems required",
    )
    cutoff = _time(as_of if as_of is not None else state["simulated_at"])
    require(cutoff <= _time(state["simulated_at"]), "Source view exceeds actual workroom clock")
    room._authorize(systems, active=True)
    try:
        rows, _ = discover_history(
            room.session.store,
            room.auditor,
            room.engagement,
            room.binding["company"],
            room.binding["branch"],
            as_of=cutoff,
            systems=systems,
        )
        require(
            all(r["system"].split(".", 1)[0] in FAMILIES for r in rows),
            "Scope source routing differs",
        )
        request_state = command(
            room.engine,
            room.auditor,
            room.engagement,
            "pbc.create",
            {
                "title": "Source dependency originals: " + task_id,
                "purpose": purpose,
                "boundary_id": "corporate",
            },
        )
        request = request_state["requests"][-1]["id"]
        command(room.engine, room.auditor, room.engagement, "pbc.issue", {"request_id": request})
        artifacts, retained = room.state()["artifacts"], []
        for row in rows:
            row = {**row, "discovered_as_of": cutoff}
            held = room._retained(
                row, artifacts, cutoff=cutoff, collection_clock=state["simulated_at"]
            )
            if held is not None:
                retained.append(held)
                continue
            item = room.session.collect(
                room.engine,
                room.auditor,
                room.engagement,
                request,
                row,
                command_id="scope-collect-" + str(room.state()["revision"]),
            )
            artifact = next(a for a in room.state()["artifacts"] if a["id"] == item["artifact_id"])
            raw = room.engine.artifacts.read(artifact)
            retained.append(
                {
                    **item,
                    "content": raw,
                    "retained_bytes": raw,
                    "artifact_id": artifact["id"],
                    "artifact_sha256": artifact["sha256"],
                    "receipt": artifact["source"]["receipt"],
                }
            )
            artifacts.append(artifact)
        if retained:
            room._checked_rows(retained)
        write(
            room.root / ("SCOPE-ACQUISITION-" + request + ".json"),
            {
                "schema": "SH_COLLECTED_SCOPE_SOURCE_ACQUISITION_V1",
                "task_id": task_id,
                "engagement_id": room.engagement,
                "request_id": request,
                "systems": list(systems),
                "actual_workroom_clock": state["simulated_at"],
                "source_view_cutoff": cutoff,
                "retained_artifact_ids": [r["artifact_id"] for r in retained],
                "control_or_person_owner_invented": False,
            },
        )
        return retained
    finally:
        room._authorize(systems, active=False)
        room.session.check_unchanged()


def execute_scope(room, *, review, rows):
    """Preflight both exact inspections, then append two no-control workpapers."""
    approval = _gate(room, review)
    before = room._checked_rows(rows)
    require(
        all(
            t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN"
            for t in before["tasks"]
            if t["id"] in TASKS
        ),
        "Scope examination cannot overwrite previous task work",
    )
    before_digest = hashlib.sha256(canonical(before).encode()).hexdigest()
    checkpoint = room.pair.world.checkpoint_sha256
    inspections = examine(rows, as_of=before["simulated_at"])
    require(
        hashlib.sha256(canonical(room.state()).encode()).hexdigest() == before_digest
        and room.pair.world.checkpoint_sha256 == checkpoint,
        "Pure scope method changed audit state or company history",
    )
    room._checked_rows(rows)
    require(
        [i["task_id"] for i in inspections] == list(TASKS), "Exact two scope inspections required"
    )
    for inspection in inspections:
        room._validate_inspection(rows, inspection, CONTRACTS[inspection["task_id"]])
    root = room.root / "BATCH-B00-SCOPE"
    require(not root.exists(), "Distinct new scope examination destination required")
    root.mkdir(mode=0o700)
    write(root / "EXAMINATION.json", inspections)
    links = []
    for inspection in inspections:
        task_id = inspection["task_id"]
        state = command(
            room.engine,
            room.auditor,
            room.engagement,
            "workpaper.add",
            {
                "title": "Collected source dependency: " + task_id,
                "task_ids": [task_id],
                "section": "SCOPE_DEPENDENCY",
                "objective": next(t["test"] for t in before["tasks"] if t["id"] == task_id),
                "procedures": inspection["performed"],
                "evidence_ids": inspection["artifact_ids"],
                "text": json.dumps(inspection, indent=2, sort_keys=True),
                "conclusion": inspection["disposition"]["rationale"],
            },
        )
        paper = state["workpapers"][-1]
        command(
            room.engine,
            room.auditor,
            room.engagement,
            "task.update",
            {
                "task_id": task_id,
                **inspection["disposition"],
            },
        )
        links.append(
            {
                "task_id": task_id,
                "workpaper_id": paper["id"],
                "workpaper_version": 1,
                "artifact_ids": inspection["artifact_ids"],
            }
        )
    after = room.state()
    require(
        all(after[k] == before[k] for k in ("populations", "selections", "sample_executions")),
        "Scope dependencies have no invented control populations or samples",
    )
    require(
        all(p.get("control_id") is None for p in after["workpapers"][len(before["workpapers"]) :]),
        "Scope workpapers have no invented control ownership",
    )
    room._verify_batch_append(
        before, {task: {"status": "IN_PROGRESS", "conclusion": "LIMITATION"} for task in TASKS}
    )
    write(
        root / "RECEIPT.json",
        {
            "schema": "SH_COLLECTED_SCOPE_DEPENDENCY_EXECUTION_RECEIPT_V1",
            "engagement_id": room.engagement,
            "selected_task_ids": list(TASKS),
            "links": links,
            "review": approval,
            "review_sha256": review.sha256,
            "actual_simulated_at": after["simulated_at"],
            "qualified_or_owner_acceptance": "NOT_ASSERTED",
            "reviewer_used": False,
            "company_preexists_audit": True,
            "previous_results_reused": False,
        },
    )
    return links
