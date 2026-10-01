"""Fresh, bounded security/continuity fieldwork through ordinary CompanyStore APIs.

Requires separately pinned source-quality and adapter acceptance. It never opens
a transformation, Key, authoring recipe, old evidence or prior audit state.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
from datetime import UTC, datetime
from pathlib import Path

from .company_store import _time
from .fresh_sec003_procedure import CLOCK_ID, require
from .population_lifecycle import population, selection
from .source_library_audit import (
    AcceptedLibrary,
    BusinessRoute,
    LibraryAudit,
    business_digest,
    file_sha,
    ordinary_copy,
    private_file,
    quiescent_read,
    schema_sha,
    typed_content,
)
from .source_library_security_methods import (
    analyze_continuity_timestamps,
    analyze_security_publishers,
    analyze_vulnerability,
    custody,
    selected,
)
from .store import digest

PROGRAM_SHA = "73d856274fbfe65e32a61cffaf3bb101b801e2ff24825be1eddfe8b4f2138134"
ADAPTER_REVIEW_SCHEMA = "SH_ROOT_SOURCE_LIBRARY_ADAPTER_INDEPENDENT_REVIEW_V2"
ADAPTER_REVIEW_VERDICT = "PASS_QUIESCENT_ENGINE_BOUND_ADAPTER"
TASKS = {
    "SEC003": "TASK-SH-SEC-003-corporate-CHECK-SOC2:CC7.1",
    "SEC005": "TASK-SH-SEC-005-corporate-TOE",
    "BCM003": "TASK-SH-BCM-003-corporate-CHECK-SOC2:A1.3",
}
SYSTEMS = {
    "sec003vuln": [
        "vulnerability_" + name
        for name in (
            "inventory",
            "baseline",
            "schedule",
            "advisory",
            "scan",
            "reconciliation",
            "triage",
            "approval",
            "remediation",
            "exception",
        )
    ],
    "sec005operated": [
        "security_" + name
        for name in (
            "authority",
            "approval",
            "inventory",
            "baseline",
            "application",
            "probe",
            "monitor",
            "reconciliation",
            "exception",
        )
    ],
    "bcm": [
        "authority_decision",
        "business_impact",
        "closure_gate",
        "corrective_action",
        "demand_forecast",
        "exercise_plan",
        "exercise_result",
        "exercise_review",
        "service_inventory",
        "technical_objectives",
    ],
    "transition": ["site_release", "recovery_exercise"],
}


def write(path, value):
    raw = (
        value
        if isinstance(value, bytes)
        else (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    )
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
    private_file(path)


def load_pins(path):
    private_file(path)
    data = json.loads(path.read_bytes())
    require(
        set(data)
        == {
            "database",
            "database_sha256",
            "manifest",
            "manifest_sha256",
            "review",
            "review_sha256",
            "version_count",
        },
        "Exact source pin fields required",
    )
    return AcceptedLibrary(
        **{**data, **{key: Path(data[key]) for key in ("database", "manifest", "review")}}
    )


def adapter_gate(path, expected):
    private_file(path)
    require(file_sha(path) == expected, "Independent adapter review pin changed")
    review = json.loads(path.read_bytes())
    module = Path(__file__).with_name("source_library_audit.py")
    require(
        review.get("schema") == ADAPTER_REVIEW_SCHEMA
        and review.get("verdict") == ADAPTER_REVIEW_VERDICT
        and review.get("source_execution_authorized") is True
        and review.get("adapter_module_sha256") == file_sha(module),
        "Actual independently accepted quiescent Engine-bound adapter required",
    )
    return {"path": str(path), "sha256": expected, "module_sha256": file_sha(module)}


def command(engine, actor, engagement, kind, payload):
    state = engine.store.get(actor, engagement)
    return engine.command(
        actor,
        engagement,
        {
            "command_id": f"library-{state['revision']}-{kind}",
            "kind": kind,
            "expected_revision": state["revision"],
            "payload": payload,
        },
    )


def plans():
    """Business locators and procedures sealed before any outcome inspection."""
    return {
        "SEC003": {
            "inventory_record": "INVENTORY-SELECTED-01",
            "baseline_record": "BASELINE-01",
            "census_record": "CENSUS-OCT-01",
            "scan_record": "SCAN-OCT-01",
            "scan_baseline_record": "BASELINE-OCT-01",
            "schedule_record": "SCHEDULE-OCT-01",
            "reconciliation_record": "RECON-OCT-01",
            "advisory_record": "ADV-SH-SIM-2027-01",
            "snapshot_cutoff": "2027-10-31T23:59:59Z",
        },
        "SEC005": {
            "inventory_record": "INVENTORY-SELECTED-01",
            "baseline_record": "BASELINE-01",
            "application_record": "APPLY-BASELINE-01",
            "initial_approval_records": ["APPROVE-TECH-01", "APPROVE-SEC-01"],
        },
        "BCM003": {
            "exercise_record": "MARKER-RECOVERY",
            "target_record": "SVC-COMPUTE",
            "authority_record": "SELECTED-SERVICE",
        },
    }


def method_rows(rows, label):
    family = {"SEC003": "sec003vuln", "SEC005": "sec005operated", "BCM003": "bcm"}[label]
    chosen = selected(rows, family)
    if label == "SEC003":
        chosen += [
            row
            for row in selected(rows, "sec005operated")
            if row["logical_system"] in {"security_inventory", "security_baseline"}
        ]
    return chosen


def authored_instruction(state, task_id):
    task = next(t for t in state["tasks"] if t["id"] == task_id)
    if task["kind"] == "ADDITIONAL_DUTY":
        require(
            isinstance(task.get("test"), str) and task["test"], "Additional-duty instruction absent"
        )
        return {"task_kind": task["kind"], "test": task["test"]}
    require(task["kind"] in {"TOD", "IMPLEMENTATION", "TOE"}, "Unsupported authored task kind")
    control = next(c for c in state["controls"] if c["id"] == task["control_id"])
    require(
        all(
            isinstance(control.get(key), str) and control[key] for key in ("procedure", "base_test")
        ),
        "Authored base control procedure/test absent",
    )
    return {
        "task_kind": task["kind"],
        "procedure": control["procedure"],
        "base_test": control["base_test"],
        "population_rule": control.get("population_rule"),
    }


def business_routes(accepted, branch):
    requested = [
        BusinessRoute("SABLE-HARBOR-REFERENCE", branch, family + "." + system, family, system)
        for family, systems in SYSTEMS.items()
        for system in systems
    ]
    accepted.verify()
    with quiescent_read(accepted.database) as db:
        registered = {tuple(row) for row in db.execute("SELECT company,branch,system FROM systems")}
    granted = [
        route for route in requested if (route.company, route.branch, route.system) in registered
    ]
    require(granted, "No registered business systems in selected company branch")
    return granted, {
        "requested_systems": [r.system for r in requested],
        "registered_granted_systems": [r.system for r in granted],
        "unregistered_requested_systems": [r.system for r in requested if r not in granted],
        "missing_systems_are_scope_gaps_not_global_nonoccurrence": True,
    }


def sample_inputs(rows, label, result):
    if label == "SEC005":
        probes = selected(rows, "sec005operated", "security_probe")
        require(probes, "Native publisher population required")
        return probes[0]["artifact_id"], [
            {"id": f"{r['source']['record']}-v{r['source']['version']}"} for r in probes
        ]
    return result["population_anchor"], result["population_rows"]


def sample_items(rows, label, result):
    """Bounded citations support each recorded selected test; no invented originals."""
    relevant = method_rows(rows, label)
    if label == "SEC003":
        relevant = [
            r
            for r in relevant
            if r["logical_family"] == "sec005operated"
            or r["source"]["record"]
            in {
                "CENSUS-OCT-01",
                "BASELINE-OCT-01",
                "SCHEDULE-OCT-01",
                "SCAN-OCT-01",
                "RECON-OCT-01",
            }
        ]
    observations = []
    if label == "SEC003":
        for item in result["asset_census"]:
            observations.append(
                (
                    item["asset_id"],
                    item,
                    "OBSERVED"
                    if all(item[name] for name in ("census", "baseline", "schedule", "scan"))
                    else "EXCEPTION_RECORDED",
                    relevant,
                )
            )
    elif label == "SEC005":
        monitors = result["monitor_reconciliations"]
        reviews = result["company_review_reconciliations"]
        for probe in selected(rows, "sec005operated", "security_probe"):
            record = probe["source"]["record"]
            month = probe["source"]["event_at"][:7]
            matched = [r for r in monitors if r["month"] == month]
            checked = [r for r in reviews if r["month"] == month]
            observation = {
                "publisher": custody(probe),
                "monitor_cutoffs": [r["population_cutoff"] for r in matched],
                "collector_missing": any(record in r["unreceived_publisher_ids"] for r in matched),
                "company_review_missing": any(
                    record in r["unreviewed_publisher_ids"] for r in checked
                ),
                "collector_source_available": bool(matched),
                "company_review_source_available": bool(checked),
                "actual_traffic_or_executable_observed": False,
            }
            refs = [
                probe,
                *[
                    r
                    for r in relevant
                    if r["logical_system"]
                    in {
                        "security_inventory",
                        "security_baseline",
                        "security_monitor",
                        "security_reconciliation",
                    }
                ],
            ]
            observations.append(
                (
                    f"{record}-v{probe['source']['version']}",
                    observation,
                    "SUPPORT_UNAVAILABLE"
                    if not matched or not checked
                    else "EXCEPTION_RECORDED"
                    if observation["collector_missing"] or observation["company_review_missing"]
                    else "OBSERVED",
                    refs,
                )
            )
    else:
        for observation in result["observations"]:
            source = observation["source"]
            refs = [
                r
                for r in relevant
                if r["logical_system"]
                in {
                    "exercise_plan",
                    "business_impact",
                    "technical_objectives",
                    "authority_decision",
                }
                or all(r["source"][key] == source[key] for key in CLOCK_ID)
            ]
            observations.append(
                (
                    f"{source['record']}-v{source['version']}",
                    observation,
                    "SUPPORT_UNAVAILABLE",
                    refs,
                )
            )
    items = []
    for item_id, observation, status, refs in observations:
        unique = {r["artifact_id"]: r for r in refs}
        require(len(unique) <= 20, "Selected item exceeds bounded source citation limit")
        text = json.dumps(observation, sort_keys=True)
        require(len(text) <= 4000, "Selected item observation exceeds bound")
        items.append(
            {
                "item_id": item_id,
                "observation": text,
                "status": status,
                "evidence": [
                    {
                        "artifact_id": r["artifact_id"],
                        "sha256": r["artifact_sha256"],
                        "locator": "Exact collected native "
                        + r["source"]["system"]
                        + "/"
                        + r["source"]["record"]
                        + f" v{r['source']['version']}; "
                        + "retained source receipt and business fields",
                    }
                    for r in unique.values()
                ],
            }
        )
    return items


def record_method(engine, auditor, engagement, rows, label, result, plan, root):
    task = TASKS[label]
    control = "SH-" + label[:3] + "-" + label[3:]
    relevant = method_rows(rows, label)
    anchor, population_rows = sample_inputs(rows, label, result)
    primary = selected(
        rows, {"SEC003": "sec003vuln", "SEC005": "sec005operated", "BCM003": "bcm"}[label]
    )
    period_start = min(r["source"]["event_at"] for r in primary)
    period_end = max(r["source"]["event_at"] for r in primary)
    state = command(
        engine,
        auditor,
        engagement,
        "population.import",
        {
            "artifact_id": anchor,
            "title": label + " selected ordinary native population",
            "rows": population_rows,
            "scope": {
                "boundary_id": "corporate",
                "unit": "SVC-compute",
                "timezone": "UTC",
                "period_start": period_start,
                "period_end": period_end,
            },
            "source": {
                "source_id": label + ":ordinary-collected-native-selected-scope",
                "query": "Native IDs/versions discovered under scoped grants at engagement clock; "
                "selected method reconciliation in pinned workpaper",
                "completeness_representation": "Selected native subpopulation only; "
                "event bounds describe the observed records and do not establish "
                "full-period completeness",
                "excluded_ids": [],
            },
        },
    )
    state = command(
        engine,
        auditor,
        engagement,
        "population.assess",
        {
            "population_id": state["populations"][-1]["id"],
            "status": "READY_FOR_PURPOSE",
            "purpose": label + " bounded documentary/model reperformance only",
            "rationale": "Exact collected native records independently reconciled; broader "
            "corporate/year population and external/live operation remain unestablished. "
            "Separate review pending.",
            "observable_artifact_ids": [r["artifact_id"] for r in relevant],
        },
    )
    pop = state["populations"][-1]
    state = command(
        engine,
        auditor,
        engagement,
        "population.select",
        {
            "population_id": pop["id"],
            "method": "ENTIRE",
            "purpose": label + " entire selected subpopulation",
            "rationale": "Presealed selected method; no statistical extrapolation "
            "or corporate/full-period credit",
        },
    )
    chosen = state["selections"][-1]
    work = {
        "task_id": task,
        "selected_plan": plan,
        "authored_instruction": authored_instruction(state, task),
        "result": result,
        "source_custody": [custody(r) for r in relevant],
        "performed_scope": "Actual collected documentary/local-model examinations only",
        "conclusion": "LIMITATION",
        "independent_review": "PENDING_RESERVED_REVIEWER",
    }
    text = json.dumps(work, indent=2, sort_keys=True)
    write(root / (label + "-WORKPAPER.json"), work)
    state = command(
        engine,
        auditor,
        engagement,
        "workpaper.add",
        {
            "title": label + " collected-source selected reperformance",
            "control_id": control,
            "task_ids": [task],
            "text": text,
            "objective": label + " selected documentary/model examination",
            "procedures": "Ordinary grant, clock-bound discovery and exact-version collection; "
            "independent selected population reconciliation and recorded arithmetic",
            "evidence_ids": [r["artifact_id"] for r in relevant],
            "conclusion": "LIMITATION",
        },
    )
    paper = state["workpapers"][-1]
    state = command(
        engine,
        auditor,
        engagement,
        "sample.execution.record",
        {
            "task_id": task,
            "task_digest": digest(next(t for t in state["tasks"] if t["id"] == task)),
            "population_id": pop["id"],
            "population_digest": population(pop).sha256,
            "selection_id": chosen["id"],
            "selection_digest": selection(chosen).sha256,
            "workpaper_id": paper["id"],
            "workpaper_version": 1,
            "workpaper_digest": digest(paper["versions"][0]),
            "purpose": label + " selected documentary/model test",
            "procedure": "Author-recorded actual source comparisons and arithmetic in linked "
            "workpaper; unsupported full-clause duties remain unperformed",
            "items": sample_items(rows, label, result),
        },
    )
    execution_ids = [state["sample_executions"][-1]["id"]]
    if label == "SEC003":
        state = command(
            engine,
            auditor,
            engagement,
            "population.select",
            {
                "population_id": pop["id"],
                "method": "MANUAL",
                "selected_ids": [result["advisory_asset"]],
                "purpose": "Disclosed synthetic advisory target correction trace",
                "rationale": "Presealed disclosed-advisory locator selects its actual "
                "native target; "
                "no expected outcome or hidden answer determines selection",
            },
        )
        deep = state["selections"][-1]
        refs = [
            r
            for r in relevant
            if r["logical_family"] == "sec005operated"
            or any(
                all(r["source"][key] == traced[key] for key in CLOCK_ID)
                for traced in result["deep_trace"]
            )
        ]
        refs = {r["artifact_id"]: r for r in refs}
        require(len(refs) <= 20, "Advisory trace source citation bound exceeded")
        observation = {
            "trace": result["deep_trace"],
            "causal_discrepancy": result["causal_discrepancy"],
            "chronology_supported": result["approval_fix_retest_chronology_supported"],
            "retest_selected_coverage_complete": result["retest_selected_coverage_complete"],
            "actual_scanner_execution": False,
        }
        state = command(
            engine,
            auditor,
            engagement,
            "sample.execution.record",
            {
                "task_id": task,
                "task_digest": digest(next(t for t in state["tasks"] if t["id"] == task)),
                "population_id": pop["id"],
                "population_digest": population(pop).sha256,
                "selection_id": deep["id"],
                "selection_digest": selection(deep).sha256,
                "workpaper_id": paper["id"],
                "workpaper_version": 1,
                "workpaper_digest": digest(paper["versions"][0]),
                "purpose": "Selected disclosed-advisory correction chronology",
                "procedure": "Trace collected advisory/detection/triage/approval/"
                "remediation/retest "
                "versions; preserve unproved causal mechanism and model-only scope",
                "items": [
                    {
                        "item_id": result["advisory_asset"],
                        "observation": json.dumps(observation, sort_keys=True),
                        "status": "EXCEPTION_RECORDED"
                        if result["causal_discrepancy"]["disposition"] == "UNEXPLAINED_FALSE_CLEAN"
                        or not result["approval_fix_retest_chronology_supported"]
                        else "OBSERVED",
                        "evidence": [
                            {
                                "artifact_id": r["artifact_id"],
                                "sha256": r["artifact_sha256"],
                                "locator": "Exact collected advisory correction source "
                                + r["source"]["system"]
                                + "/"
                                + r["source"]["record"]
                                + f" v{r['source']['version']}",
                            }
                            for r in refs.values()
                        ],
                    }
                ],
            },
        )
        execution_ids.append(state["sample_executions"][-1]["id"])
    conditions = ["Unperformed scope: " + "; ".join(result["unperformed_clauses"])]
    if label == "SEC003" and (result["omitted_scan_assets"] or result["count_contradictions"]):
        conditions.append(
            "Selected coverage/count contradictions: "
            + json.dumps(
                {
                    "omitted": result["omitted_scan_assets"],
                    "counts": result["count_contradictions"],
                    "causal_discrepancy": result["causal_discrepancy"],
                },
                sort_keys=True,
            )
        )
    if label == "SEC005":
        discrepancies = [
            {
                k: r[k]
                for k in (
                    "month",
                    "unreceived_publisher_ids",
                    "publisher_claim_disagrees",
                    "missing_required_agent_assets",
                )
            }
            for r in result["monitor_reconciliations"]
            if r["unreceived_publisher_ids"]
            or r["publisher_claim_disagrees"]
            or r["missing_required_agent_assets"]
        ]
        if discrepancies:
            conditions.append(
                "Selected publisher/collector/agent discrepancies: "
                + json.dumps(discrepancies, sort_keys=True)
            )
    for index, condition in enumerate(conditions):
        command(
            engine,
            auditor,
            engagement,
            "finding.create",
            {
                "title": label
                + (
                    " selected source scope limitation"
                    if index == 0
                    else " selected source discrepancy"
                ),
                "condition": condition,
                "classification": "SOURCE_SCOPE_LIMITATION"
                if index == 0
                else "SELECTED_OPERATING_DISCREPANCY",
                "control_id": control,
                "criterion": task + " authored instructions and declared selected method scope",
                "evidence_ids": [r["artifact_id"] for r in relevant],
            },
        )
    state = command(
        engine,
        auditor,
        engagement,
        "task.update",
        {
            "task_id": task,
            "status": "IN_PROGRESS",
            "conclusion": "LIMITATION",
            "rationale": "Selected documentary/local-model procedure recorded. Broader clauses, "
            "independent task-scope review and actual operating/recovery tests remain "
            "unperformed; no full-task credit.",
        },
    )
    return {
        "task_id": task,
        "population_id": pop["id"],
        "selection_id": chosen["id"],
        "workpaper_id": paper["id"],
        "sample_execution_id": state["sample_executions"][-1]["id"],
        "sample_execution_ids": execution_ids,
    }


def run(repository, destination, accepted, program_pack, adapter_review, adapter_review_sha):
    gate = adapter_gate(adapter_review, adapter_review_sha)
    accepted.verify()
    private_file(program_pack)
    require(file_sha(program_pack) == PROGRAM_SHA, "Instruction-only program pack changed")
    require(
        not destination.exists()
        and not any(p.is_symlink() for p in [destination, *destination.parents]),
        "Fresh ordinary private execution directory required",
    )
    require(
        stat.S_IMODE(destination.parent.stat().st_mode) == 0o700,
        "Private execution parent required",
    )
    destination.mkdir(mode=0o700)
    write(destination / "ADAPTER_ACCEPTANCE.json", gate)
    ordinary_copy(program_pack, destination / "program-pack.json")
    branch_receipts = {}
    methods = {
        "SEC003": analyze_vulnerability,
        "SEC005": analyze_security_publishers,
        "BCM003": analyze_continuity_timestamps,
    }
    for branch in ("HARBOR-OPERATIONS-A", "HARBOR-OPERATIONS-B"):
        root = destination / branch
        root.mkdir(mode=0o700)
        routes, routing = business_routes(accepted, branch)
        write(root / "ROUTING.json", routing)
        session = LibraryAudit(accepted, root / "company-source", routes)
        engine, state, identities = session.create(
            repository=repository,
            audit_root=root / "audit-state",
            program_pack=destination / "program-pack.json",
            payload={
                "command_id": "fresh-library-create",
                "title": "Selected ordinary company investigation " + branch,
                "discipline": "IT",
                "mode": "CLEAN",
                "configuration": {"selections": []},
                "scope": {
                    "programs": ["SOC2", "HIPAA"],
                    "report_type": "Type 2",
                    "period_start": "2027-01-01",
                    "period_end": "2027-12-31",
                    "fieldwork_start": "2028-01-03",
                    "timezone": "UTC",
                    "boundaries": ["corporate"],
                    "soc2_categories": ["Security", "Availability", "Confidentiality"],
                    "hipaa_scenario": "FICTIONAL_BUSINESS_ASSOCIATE_SUBCONTRACTOR_SIMULATED_EPHI",
                },
            },
        )
        engagement, auditor, operator = state["id"], identities["auditor"], identities["operator"]
        require(
            set(TASKS.values()) <= {t["id"] for t in state["tasks"]},
            "Selected authored tasks unavailable",
        )
        write(
            root / "START.json",
            {
                "engagement_id": engagement,
                "task_count": len(state["tasks"]),
                "scope": state["scope"],
                **identities,
            },
        )
        command(engine, operator, engagement, "company.activate", {})
        command(engine, auditor, engagement, "kickoff.start", {})
        plan = {
            "methods": plans(),
            "selection_sealed_at": datetime.now(UTC).isoformat(),
            "basis": "Safe business locators and authored procedure instructions only; "
            "no outcomes inspected",
            "source_cutoff": state["simulated_at"],
            "selected_task_ids": TASKS,
            "adapter_acceptance": gate,
            "population_method": "ENTIRE_SELECTED_SUBPOPULATION",
        }
        write(root / "PLAN.json", plan)
        for label, task in TASKS.items():
            command(
                engine,
                auditor,
                engagement,
                "task.update",
                {
                    "task_id": task,
                    "status": "IN_PROGRESS",
                    "note": label + " selected-scope investigation; no full-task credit",
                },
            )
        requests = {}
        for label in TASKS:
            state = command(
                engine,
                auditor,
                engagement,
                "pbc.create",
                {
                    "title": label + " selected native originals",
                    "purpose": "Direct selected source investigation",
                    "control_id": "SH-" + label[:3] + "-" + label[3:],
                    "person_id": "AS-P007",
                    "boundary_id": "corporate",
                },
            )
            requests[label] = state["requests"][-1]["id"]
            command(engine, auditor, engagement, "pbc.issue", {"request_id": requests[label]})
        session.authorize(**session.identities, engagement=engagement)
        discovered, pages = session.discover(engine, auditor, engagement)
        write(
            root / "DISCOVERY.json",
            {
                "rows": [{k: v for k, v in r.items() if k != "content"} for r in discovered],
                "pages": pages,
            },
        )
        collected = []
        for index, row in enumerate(discovered):
            label = {"sec003vuln": "SEC003", "sec005operated": "SEC005", "bcm": "BCM003"}.get(
                row["logical_family"]
            )
            if label is None:
                label = "BCM003" if row["logical_system"] == "recovery_exercise" else "SEC005"
            collected.append(
                session.collect(
                    engine,
                    auditor,
                    engagement,
                    requests[label],
                    row,
                    command_id=f"exact-collect-{index}",
                )
            )
        write(root / "COLLECTION.json", collected)
        results = {}
        links = {}
        for label, method in methods.items():
            results[label] = method(collected, plan["methods"][label])
            links[label] = record_method(
                engine,
                auditor,
                engagement,
                collected,
                label,
                results[label],
                plan["methods"][label],
                root,
            )
        state = engine.store.get(auditor, engagement)
        require(not state["reviews"], "Performer cannot manufacture independent review")
        require(
            all(
                t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN"
                for t in state["tasks"]
                if t["id"] not in TASKS.values()
            ),
            "Unselected task promoted",
        )
        require(
            all(
                t["status"] == "IN_PROGRESS" and t["conclusion"] == "LIMITATION"
                for t in state["tasks"]
                if t["id"] in TASKS.values()
            ),
            "False selected full-task credit",
        )
        session.authorize(**session.identities, engagement=engagement, active=False)
        session.check_unchanged()
        write(root / "ACCESS.json", session.access_log)
        write(root / "RESULTS.json", results)
        write(root / "FINAL_STATE.json", state)
        branch_receipts[branch] = {
            "engagement_id": engagement,
            "collected_native_versions": len(collected),
            "zero_workroom_counts": identities["zero_workroom_counts"],
            "task_links": links,
            "selected_task_disposition": "IN_PROGRESS_LIMITATION",
            "independent_review": "PENDING",
            "native_business_sha256": session.business_sha256,
            "native_schema_sha256": session.schema_sha256,
        }
    receipt = {
        "schema": "SH_FRESH_LIBRARY_SELECTED_SECURITY_EXECUTION_V1",
        "accepted_library": accepted.verify(),
        "adapter_acceptance": gate,
        "program_pack_sha256": PROGRAM_SHA,
        "branches": branch_receipts,
        "full_audit_credit": False,
        "actual_restore_reperformed": False,
        "limitations": "Selected documentary/local-policy/data-model scope only; "
        "corporate/year/live/ePHI assurance unperformed",
    }
    write(destination / "RECEIPT.json", receipt)
    write(
        destination / "MANIFEST.json",
        {
            "schema": "SH_FRESH_LIBRARY_SELECTED_SECURITY_FILES_V1",
            "files": {
                str(p.relative_to(destination)): file_sha(p)
                for p in sorted(destination.rglob("*"))
                if p.is_file()
            },
        },
    )
    return receipt


def verify(destination, accepted, adapter_review, adapter_review_sha):
    """Separate read-only reperformance and custody checks of the actual workroom."""
    gate = adapter_gate(adapter_review, adapter_review_sha)
    pins = accepted.verify()
    manifest = json.loads((destination / "MANIFEST.json").read_bytes())
    require(
        manifest["schema"] == "SH_FRESH_LIBRARY_SELECTED_SECURITY_FILES_V1",
        "Execution manifest schema",
    )
    paths = {
        str(p.relative_to(destination)): p
        for p in destination.rglob("*")
        if p.is_file() or p.is_symlink()
    }
    require(
        set(paths) == set(manifest["files"]) | {"MANIFEST.json"}, "Execution file inventory changed"
    )
    for relative, path in paths.items():
        private_file(path)
        if relative != "MANIFEST.json":
            require(file_sha(path) == manifest["files"][relative], "Execution file pin changed")
    for directory in [destination, *[p for p in destination.rglob("*") if p.is_dir()]]:
        require(
            not directory.is_symlink() and stat.S_IMODE(directory.stat().st_mode) == 0o700,
            "Private ordinary execution directories required",
        )
    receipt = json.loads((destination / "RECEIPT.json").read_bytes())
    require(
        receipt["accepted_library"] == pins and receipt["adapter_acceptance"] == gate,
        "Execution accepted custody changed",
    )
    require(
        receipt["full_audit_credit"] is False and receipt["actual_restore_reperformed"] is False,
        "False full audit/recovery credit",
    )
    require(file_sha(destination / "program-pack.json") == PROGRAM_SHA, "Instruction pack changed")
    accepted_business, accepted_schema = (
        business_digest(accepted.database),
        schema_sha(accepted.database),
    )
    methods = {
        "SEC003": analyze_vulnerability,
        "SEC005": analyze_security_publishers,
        "BCM003": analyze_continuity_timestamps,
    }
    summaries = {}
    for branch, branch_receipt in receipt["branches"].items():
        require(branch in {"HARBOR-OPERATIONS-A", "HARBOR-OPERATIONS-B"}, "Unknown audit branch")
        root = destination / branch
        start = json.loads((root / "START.json").read_bytes())
        plan = json.loads((root / "PLAN.json").read_bytes())
        require(plan["methods"] == plans(), "Presealed selected method locators changed")
        require(not any(start["zero_workroom_counts"].values()), "Nonzero evidence start")
        identities = {key: start[key] for key in ("operator", "auditor", "reviewer")}
        require(len(set(identities.values())) == 3, "Identity separation failed")
        database = root / "company-source/company.sqlite3"
        require(
            business_digest(database)
            == accepted_business
            == branch_receipt["native_business_sha256"],
            "Staged native originals differ from accepted source",
        )
        require(
            schema_sha(database) == accepted_schema == branch_receipt["native_schema_sha256"],
            "Staged source schema/triggers changed",
        )
        audit = root / "audit-state/engagements.sqlite3"
        with quiescent_read(audit) as db:
            states = db.execute("SELECT id,state FROM engagements").fetchall()
            require(
                len(states) == 1 and states[0]["id"] == start["engagement_id"],
                "Fresh engagement identity changed",
            )
            state = json.loads(states[0]["state"])
            memberships = dict(
                db.execute(
                    "SELECT principal,permission FROM members WHERE engagement=?", (state["id"],)
                ).fetchall()
            )
            require(
                memberships
                == {
                    identities["operator"]: "instruct",
                    identities["auditor"]: "learn",
                    identities["reviewer"]: "review",
                },
                "Reserved reviewer membership changed",
            )
            previous = ""
            events = []
            for index, entry in enumerate(db.execute("SELECT * FROM events ORDER BY revision")):
                event = {
                    "actor": entry["actor"],
                    "recorded_at": entry["recorded_at"],
                    "previous_hash": entry["previous_hash"],
                    "state": json.loads(entry["state"]),
                    "command": json.loads(entry["command"]),
                    "command_id": entry["command_id"],
                }
                require(
                    entry["revision"] == index
                    and entry["previous_hash"] == previous
                    and digest(event) == entry["hash"]
                    and digest(event["command"]) == entry["request_hash"],
                    "Actual command history chain changed",
                )
                previous = entry["hash"]
                events.append(event)
            require(
                events and events[-1]["state"] == state,
                "Final audit state differs from command history",
            )
            require(
                all(event["actor"] != identities["reviewer"] for event in events),
                "Performer used reserved reviewer",
            )
            first = events[0]["state"]
            require(
                all(not first[key] for key in start["zero_workroom_counts"]),
                "Initial history carries evidence",
            )
            require(
                all(
                    t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN"
                    for t in first["tasks"]
                ),
                "Initial tasks inherited credit",
            )
        require(
            state == json.loads((root / "FINAL_STATE.json").read_bytes()),
            "Final state export differs",
        )
        require(
            not state["reviews"] and state["evidence_acquisition"] == "COMPANY_SOURCE_COLLECTION",
            "Prepared generation or manufactured reviewer work",
        )
        require(
            state["company_source_binding"]
            == {"company": "SABLE-HARBOR-REFERENCE", "branch": branch},
            "Frozen actual branch binding changed",
        )
        require(
            all(
                t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN"
                for t in state["tasks"]
                if t["id"] not in TASKS.values()
            ),
            "Unselected task credit",
        )
        require(
            all(
                t["status"] == "IN_PROGRESS" and t["conclusion"] == "LIMITATION"
                for t in state["tasks"]
                if t["id"] in TASKS.values()
            ),
            "Selected false full-task credit",
        )
        artifacts = {r["id"]: r for r in state["artifacts"]}
        collected = json.loads((root / "COLLECTION.json").read_bytes())
        discovered = json.loads((root / "DISCOVERY.json").read_bytes())["rows"]
        require(
            len(collected) == len(discovered) == branch_receipt["collected_native_versions"]
            and len(artifacts) == len(collected),
            "Collected population/count changed",
        )
        with quiescent_read(database) as db:
            require(
                db.execute("SELECT COUNT(*) FROM grants WHERE active!=0").fetchone()[0] == 0,
                "Source grants not revoked",
            )
            require(
                db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == len(collected),
                "Collection journal/count changed",
            )
            for item in collected:
                source = item["source"]
                native = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    tuple(source[key] for key in CLOCK_ID[:5]),
                ).fetchone()
                require(
                    native is not None and all(native[key] == source[key] for key in CLOCK_ID),
                    "Collected exact native identity/hash/clocks changed",
                )
                require(
                    source["provenance"] == json.loads(native["provenance"])
                    and source["origin"] == native["origin"],
                    "Source provenance changed",
                )
                require(
                    source["branch"] == branch
                    and _time(source["available_at"]) <= _time(plan["source_cutoff"])
                    and (
                        source["event_at"] is None
                        or _time(source["event_at"]) <= _time(plan["source_cutoff"])
                    ),
                    "Future or foreign collected source",
                )
                require(
                    _time(plan["selection_sealed_at"]) <= _time(item["receipt"]["collected_at"])
                    and _time(item["receipt"]["collected_at"])
                    <= _time(datetime.now(UTC).isoformat()),
                    "Transplanted or future collection chronology",
                )
                recorded = db.execute(
                    "SELECT receipt FROM collections WHERE command_id=?",
                    (item["receipt"]["command_id"],),
                ).fetchone()
                require(
                    recorded is not None and json.loads(recorded["receipt"]) == item["receipt"],
                    "Immutable collection receipt differs",
                )
                artifact = artifacts[item["artifact_id"]]
                require(
                    artifact["source"]["receipt"] == item["receipt"]
                    and artifact["sha256"] == item["artifact_sha256"] == source["sha256"],
                    "Retained collection receipt/bytes disagree",
                )
                original = root / "audit-state/artifacts" / artifact["sha256"]
                require(
                    file_sha(original) == artifact["sha256"]
                    and original.read_bytes() == native["content"],
                    "Retained original bytes differ from actual company source",
                )
                decoded, mime = typed_content({**source, "content": original.read_bytes()})
                require(
                    decoded == item["document"] and mime == item["content_type"],
                    "Retained typed body differs",
                )
        results = json.loads((root / "RESULTS.json").read_bytes())
        for label, method in methods.items():
            result = method(collected, plan["methods"][label])
            require(result == results[label], "Independent method reperformance differs")
            work = json.loads((root / (label + "-WORKPAPER.json")).read_bytes())
            paper = next(
                p
                for p in state["workpapers"]
                if p["id"] == branch_receipt["task_links"][label]["workpaper_id"]
            )
            require(
                work["result"] == result and json.loads(paper["versions"][0]["text"]) == work,
                "Actual pinned workpaper differs from method result",
            )
            traces = [t for t in state["sample_executions"] if t["task_id"] == TASKS[label]]
            require(
                len(traces) == (2 if label == "SEC003" else 1),
                "Actual selected sample trace missing",
            )
            for trace in traces:
                pop = next(p for p in state["populations"] if p["id"] == trace["population_id"])
                chosen = next(s for s in state["selections"] if s["id"] == trace["selection_id"])
                require(
                    population(pop).sha256 == trace["population_digest"]
                    and selection(chosen).sha256 == trace["selection_digest"]
                    and digest(paper["versions"][0]) == trace["workpaper_digest"],
                    "Sample input lineage changed",
                )
                require(
                    {i["item_id"] for i in trace["items"]} == set(selection(chosen).all_ids)
                    and trace["automatic_testing_credit"] is False
                    and trace["independent_review"] == "NOT_PERFORMED",
                    "Incomplete selected sample or false review/testing credit",
                )
        summaries[branch] = {
            "native_versions": len(collected),
            "tasks_with_selected_work": len(TASKS),
            "sample_execution_traces": len(state["sample_executions"]),
            "independent_review": "PENDING",
            "full_audit_credit": False,
        }
    accepted.verify()
    return {
        "schema": "SH_FRESH_LIBRARY_SELECTED_SECURITY_READ_ONLY_VERIFICATION_V1",
        "verdict": "PASS_REPRODUCIBLE_SELECTED_DOCUMENTARY_MODEL_WORK_NO_FULL_AUDIT_CREDIT",
        "receipt_sha256": file_sha(destination / "RECEIPT.json"),
        "manifest_sha256": file_sha(destination / "MANIFEST.json"),
        "branches": summaries,
        "actual_restore_reperformed": False,
        "owner_or_professional_acceptance": "NOT_ASSERTED",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--source-pins", type=Path, required=True)
    parser.add_argument("--program-pack", type=Path, required=True)
    parser.add_argument("--adapter-review", type=Path, required=True)
    parser.add_argument("--adapter-review-sha256", required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        print(
            json.dumps(
                verify(
                    args.destination,
                    load_pins(args.source_pins),
                    args.adapter_review,
                    args.adapter_review_sha256,
                ),
                sort_keys=True,
            )
        )
        return
    receipt = run(
        args.repository,
        args.destination,
        load_pins(args.source_pins),
        args.program_pack,
        args.adapter_review,
        args.adapter_review_sha256,
    )
    print(
        json.dumps(
            {
                "destination": str(args.destination),
                "branches": receipt["branches"],
                "full_audit_credit": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
