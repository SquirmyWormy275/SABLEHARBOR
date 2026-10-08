"""Finite trusted-local connection for reviewed native fieldwork supplements.

The caller supplies an existing retained room.engine, its original learner and
engagement, an issued PBC and externally approved exact native/task selections.
This module grants nothing and constructs no world, audit, Key or HTTP surface.
The unchanged legacy all-AVAILABLE population/sample writer remains separate.
"""

import json
import re
from copy import deepcopy

from enterprise.audit_suite import source_continuity_methods as continuity
from enterprise.audit_suite import source_governance_methods as governance
from enterprise.audit_suite import source_native_operating_methods as native
from enterprise.audit_suite import source_workforce_methods as workforce
from enterprise.audit_suite.company_collection import binding
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError, require
from enterprise.audit_suite.store import digest

BATCHES = {
    "B01": (workforce.inspections, workforce.task_contracts, {"SH-IAM-003", "SH-IAM-007"}),
    "B03": (continuity.examine, continuity.contracts, {"SH-BCM-002", "SH-BCM-003"}),
    "B07": (governance.examine, governance.contracts, {"SH-POL-001", "SH-POL-004"}),
}


class NativeSupplementInterrupted(ProcedureError):
    """Carry confirmed responses and an attempted request needing reconciliation."""

    def __init__(self, receipt):
        super().__init__("Native supplement interrupted; reconcile its attempted command")
        self.receipt = receipt


def perform_native_supplement(
    engine,
    auditor,
    engagement,
    *,
    batch,
    request_id,
    native_refs,
    task_ids,
    command_prefix,
    expected_revision,
    scratch_root,
):
    """Exact Engine collection → LIST reader → admitted callback → qualified WP/tasks.

    External Root selection must separately close source/runtime/code, exact
    dependency refs/grants, retained storage and old-epoch cutover. No evidence
    discovery, latest substitution, inferred alias or cached outcome occurs here.
    A changed revision or reused prefix requires explicit new read/selection.
    """
    require(batch in BATCHES, "Select one admitted native supplement batch")
    method, contracts_reader, controls = BATCHES[batch]
    contracts = contracts_reader()
    state = engine.store.get(auditor, engagement)
    require(
        type(expected_revision) is int
        and expected_revision == state["revision"]
        and state["phase"] == "ACTIVE"
        and type(command_prefix) is str
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}", command_prefix),
        "Exact current revision, active room and unique command prefix required",
    )
    require(
        type(task_ids) is list
        and task_ids
        and len(task_ids) == len(set(task_ids))
        and all(type(t) is str and t in contracts for t in task_ids),
        "Exact distinct admitted task IDs required",
    )
    tasks = {t["id"]: t for t in state["tasks"]}
    require(
        all(t in tasks and tasks[t]["control_id"] in controls for t in task_ids),
        "Selected native supplementary tasks must exist in this scope",
    )
    requests = [r for r in state["requests"] if r["id"] == request_id]
    require(
        len(requests) == 1
        and requests[0]["status"]
        in {"ISSUED", "ACKNOWLEDGED", "IN_PROGRESS", "CLARIFICATION", "SUBMITTED"},
        "Issue the exact ordinary PBC before invoking native supplement acquisition",
    )
    require(
        type(native_refs) is list and 0 < len(native_refs) <= native.MAX_ROWS,
        "Externally complete bounded exact dependency refs required",
    )
    selected = binding(engine, state)
    references, seen = [], set()
    for reference in native_refs:
        native.native_pin(reference)
        require(
            all(reference[k] == selected[k] for k in ("company", "branch"))
            and native.identity(reference) not in seen,
            "Exact same-branch distinct native versions required",
        )
        seen.add(native.identity(reference))
        references.append(deepcopy(reference))
    # A prior partially written WP is not an outcome cache or a resume checkpoint.
    for paper in state["workpapers"]:
        for version in paper["versions"]:
            try:
                text = json.loads(version.get("text", ""))
            except (TypeError, ValueError):
                continue
            require(
                type(text) is not dict
                or text.get("native_supplement_command_prefix") != command_prefix,
                "Command prefix already wrote a supplement; inspect partial state first",
            )
    # Normal permission/clock/byte-checked source API; no source mutation or grants.
    for reference in references:
        row = engine.company_store.read_version(
            auditor,
            engagement,
            reference["company"],
            reference["branch"],
            reference["system"],
            reference["record"],
            version=reference["version"],
            as_of=state["simulated_at"],
        )
        require(
            native.encoded({k: row[k] for k in native.PIN}) == native.encoded(reference),
            "Selected current native version/SHA differs before command writes",
        )
    receipt = {
        "batch": batch,
        "engagement_id": engagement,
        "principal_id": auditor,
        "request_id": request_id,
        "native_refs": references,
        "task_ids": list(task_ids),
        "command_prefix": command_prefix,
        "initial_revision": expected_revision,
        "current_revision": expected_revision,
        "commands": [],
        "commands_extent": "CONFIRMED_RETURNED_RESPONSES_ONLY",
        "unconfirmed_attempted_command": None,
        "journal_reconciliation_required": False,
        "links": [],
        "status": "STARTED",
        "professional_acceptance": "NOT_ASSERTED",
        "population_sample_retest_or_full_clause_credit": False,
        "source_or_task_results_imported": False,
    }
    cursor = expected_revision

    def command(kind, payload, suffix):
        nonlocal state, cursor
        command_value = {
            "command_id": command_prefix + ":" + suffix,
            "expected_revision": cursor,
            "kind": kind,
            "payload": payload,
        }
        # Engine may commit before projection raises: record the request first.
        receipt["unconfirmed_attempted_command"] = {
            "command": deepcopy(command_value),
            "request_sha256": digest(command_value),
        }
        returned = engine.command(auditor, engagement, command_value)
        require(
            returned["revision"] == cursor + 1,
            "Unexpected command revision; no silent skip/replay allowed",
        )
        receipt["commands"].append(
            {
                "command": deepcopy(command_value),
                "request_sha256": digest(command_value),
                "result_revision": returned["revision"],
                "result_state_sha256": digest(returned),
            }
        )
        receipt["unconfirmed_attempted_command"] = None
        state, cursor = returned, returned["revision"]
        receipt["current_revision"] = cursor

    try:
        ids = []
        for number, reference in enumerate(references):
            command(
                "company.collect",
                {
                    "request_id": request_id,
                    "system_id": reference["system"],
                    "record_id": reference["record"],
                    "version": reference["version"],
                },
                "COL-" + str(number),
            )
            held = [
                a
                for a in state["artifacts"]
                if a.get("request_id") == request_id
                and a["source"].get("kind") == "COLLECTED_COMPANY_SOURCE"
                and native.encoded({k: a["source"]["receipt"]["source"][k] for k in native.PIN})
                == native.encoded(reference)
            ]
            require(len(held) == 1, "Exact current request's retained original required")
            ids.append(held[0]["id"])
        rows = native.retained_inputs(engine, auditor, engagement, ids)
        callback_revision = cursor
        inspections = method(rows, as_of=state["simulated_at"], scratch_root=scratch_root)
        require(
            engine.store.get(auditor, engagement)["revision"] == callback_revision,
            "Room changed during pure examination; no supplementary write permitted",
        )
        by_task = {i["task_id"]: i for i in inspections}
        require(len(by_task) == len(inspections), "Distinct callback task IDs required")
        prepared = []
        row_by_id = {r["artifact_id"]: r for r in rows}
        for task_id in task_ids:
            item = by_task[task_id]
            require(
                item["result"].get("native_operating_attributes")
                and all(item[k] == contracts[task_id][k] for k in ("performed", "unperformed")),
                "No empty native observation or substituted task facet can promote a task",
            )
            evidence = set(item["artifact_ids"])
            evidence.update(e["artifact_id"] for o in item["observations"] for e in o["evidence"])
            require(
                evidence and evidence <= row_by_id.keys(), "All exact callback citations required"
            )
            require(
                item["disposition"]["conclusion"] in {"LIMITATION", "FAIL"},
                "Native supplement cannot assert an automatic PASS",
            )
            paper = {
                "native_supplement_command_prefix": command_prefix,
                "batch": batch,
                "task_id": task_id,
                "inspection": item,
                "cited_originals": [
                    {
                        "artifact_id": aid,
                        "sha256": row_by_id[aid]["artifact_sha256"],
                        "source": row_by_id[aid]["source"],
                        "artifact_intake": row_by_id[aid]["artifact_intake"],
                    }
                    for aid in sorted(evidence)
                ],
                "unsupported_basis": "Qualified local documentary facts only. Original intake "
                "status and quarantine warnings persist. No population/sample/retest, whole "
                "clause, enterprise or professional acceptance; unperformed facets remain exact.",
                "professional_acceptance": "NOT_ASSERTED",
            }
            prepared.append((task_id, item, sorted(evidence), paper))
        for number, (task_id, item, evidence, paper) in enumerate(prepared):
            command(
                "workpaper.add",
                {
                    "title": "Qualified native operating supplement " + task_id,
                    "control_id": tasks[task_id]["control_id"],
                    "task_ids": [task_id],
                    "text": native.encoded(paper).decode(),
                    "objective": item["performed"],
                    "procedures": item["performed"] + " Unperformed: " + item["unperformed"],
                    "evidence_ids": evidence,
                    "conclusion": item["disposition"]["conclusion"],
                },
                "WP-" + str(number),
            )
            wp = state["workpapers"][-1]
            receipt["links"].append(
                {
                    "task_id": task_id,
                    "workpaper_id": wp["id"],
                    "workpaper_version": wp["versions"][-1]["version"],
                    "evidence_ids": evidence,
                    "task_update_completed": False,
                }
            )
            command(
                "task.update",
                {
                    "task_id": task_id,
                    "status": "IN_PROGRESS",
                    "conclusion": item["disposition"]["conclusion"],
                    "rationale": item["disposition"]["rationale"] + " Qualified supplement only; "
                    "population/sample/retest and broader clauses remain unperformed.",
                },
                "TASK-" + str(number),
            )
            receipt["links"][-1]["task_update_completed"] = True
        receipt["status"] = "COMPLETED_QUALIFIED_NATIVE_SUPPLEMENT"
        return receipt
    except Exception as error:
        receipt["status"] = "INTERRUPTED_REQUIRING_JOURNAL_RECONCILIATION"
        receipt["journal_reconciliation_required"] = True
        receipt["last_confirmed_returned_revision"] = cursor
        receipt["current_revision"] = None
        try:
            receipt["current_revision"] = engine.store.get(auditor, engagement)["revision"]
        except Exception as observation_error:
            receipt["current_revision_read_failure_type"] = type(observation_error).__name__
        receipt["failure_type"] = type(error).__name__
        raise NativeSupplementInterrupted(receipt) from error
