"""Fresh selected privacy documentary fieldwork through ordinary company APIs.

Requires separately accepted native library, adapter and privacy-method pins.
No company recipe, private transformation, Key or prior workroom is an input.
Every selected procedure remains partial, with no full-task or legal credit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from datetime import UTC, datetime
from pathlib import Path

from .company_store import _time
from .fresh_sec003_procedure import CLOCK_ID, NATIVE_ID, require
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
)
from .source_privacy_methods import CASE_SYSTEMS, examine
from .store import digest

PROGRAM_SHA = "73d856274fbfe65e32a61cffaf3bb101b801e2ff24825be1eddfe8b4f2138134"
INITIAL = "2027-12-31T09:00:00.000000+00:00"
FINAL = "2028-01-15T09:00:00.000000+00:00"
EARLY_CLOSE = "2027-09-30T20:00:00.000000+00:00"
BRANCHES = ("HARBOR-OPERATIONS-A", "HARBOR-OPERATIONS-B")
CONTROL = "SH-DAT-002"
TASKS = {
    "TOD": "TASK-SH-DAT-002-corporate-TOD",
    "IMPLEMENTATION": "TASK-SH-DAT-002-corporate-IMPLEMENTATION",
    "TOE": "TASK-SH-DAT-002-corporate-TOE",
    "PURPOSE": "TASK-SH-DAT-002-corporate-ACTION-H-PRIVACY-PURPOSE",
    "TRANSFER": "TASK-SH-DAT-002-corporate-CHECK-SOC2:CC6.7",
    "LIFECYCLE": "TASK-SH-DAT-002-corporate-CHECK-SOC2:C1.1",
}
SYSTEMS = (
    "privacy_authority",
    "privacy_change_approval",
    "privacy_configuration",
    "privacy_contract",
    "privacy_customer_decision",
    "privacy_customer_instruction",
    "privacy_dataset_inventory",
    "privacy_exception",
    "privacy_gate_decision",
    "privacy_legal_review",
    "privacy_lifecycle",
    "privacy_monitoring",
    "privacy_receipt",
    "privacy_reconciliation",
    "privacy_release",
    "privacy_request",
)
RECORD_SYSTEMS = {
    "TOD": {
        "privacy_authority",
        "privacy_contract",
        "privacy_customer_instruction",
        "privacy_dataset_inventory",
        "privacy_legal_review",
    },
    "IMPLEMENTATION": {"privacy_change_approval", "privacy_configuration", "privacy_monitoring"},
    "LIFECYCLE": {"privacy_dataset_inventory", "privacy_contract", "privacy_lifecycle"},
}
METHODS = {
    "TOD": {
        "performed": (
            "Inspect retained authority, customer instruction, contract, "
            "legal-review and dataset records; resolve collected dependency "
            "custody and separate simulated role boundaries."
        ),
        "unperformed": (
            "Qualified full-clause design/applicability assessment; wider "
            "enterprise/ePHI/designated-record-set inventory; acceptance of real "
            "authority and effectiveness of safeguards."
        ),
    },
    "IMPLEMENTATION": {
        "performed": (
            "Inspect every collected configuration/change-approval/monitoring "
            "version, its publication timing and exact dependency joins. Preserve "
            "documentary changes without asserting executable application."
        ),
        "unperformed": (
            "Actual application, routing/permission enforcement, channel testing "
            "and independent configuration inspection across all operating systems."
        ),
    },
    "TOE": {
        "performed": (
            "Reconcile all observed September case IDs, inlet sequences, current "
            "documentary customer/counsel decisions, recorded release "
            "scope/recipient and receipt status, plus the premature month-close "
            "assertion."
        ),
        "unperformed": (
            "Complete accepted-year/corporate population, missing month-end intake "
            "tail, actual routing/transfer/recipient confirmation and independent "
            "full-procedure review."
        ),
    },
    "PURPOSE": {
        "performed": (
            "Trace every observed case request through documentary customer and "
            "counsel permission to its recorded release, comparing scope, "
            "recipient, business boundary and chronology."
        ),
        "unperformed": (
            "Qualified purpose-specific HIPAA/legal decision reperformance, actual "
            "ePHI reuse, AI-training use and all real minimum-necessary exceptions."
        ),
    },
    "TRANSFER": {
        "performed": (
            "Trace every observed documentary release and retained recipient "
            "status against the collected request/customer/counsel versions and "
            "exact native custody."
        ),
        "unperformed": (
            "Live channel/endpoint protection, actual network transfer, "
            "destination control, independent recipient acknowledgment and wider "
            "transfer census."
        ),
    },
    "LIFECYCLE": {
        "performed": (
            "Inspect the retained selected dataset/contract/lifecycle histories, "
            "including documentary retention/deletion restrictions and available "
            "dependency joins."
        ),
        "unperformed": (
            "Actual copy inventory, deletion/retention execution, independent "
            "object inspection and broader corporate/annual lifecycle coverage."
        ),
    },
}


def write(path: Path, value) -> None:
    data = (
        value
        if isinstance(value, bytes)
        else (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    )
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    private_file(path)


def load_pins(path: Path) -> AcceptedLibrary:
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
        "Exact accepted source fields required",
    )
    return AcceptedLibrary(
        **{**data, **{key: Path(data[key]) for key in ("database", "manifest", "review")}}
    )


def gate(path: Path, expected: str, *, method: bool) -> dict:
    private_file(path)
    require(file_sha(path) == expected, "Independent execution gate pin changed")
    review = json.loads(path.read_bytes())
    if method:
        schema, verdict = (
            "SH_PRIVACY_METHOD_INDEPENDENT_REVIEW_V2",
            "PASS_COLLECTED_BYTES_BOUNDED_PRIVACY_METHOD",
        )
        module, key = "source_privacy_methods.py", "privacy_module_sha256"
    else:
        schema, verdict = (
            "SH_ROOT_SOURCE_LIBRARY_ADAPTER_INDEPENDENT_REVIEW_V2",
            "PASS_QUIESCENT_ENGINE_BOUND_ADAPTER",
        )
        module, key = "source_library_audit.py", "adapter_module_sha256"
    actual = file_sha(Path(__file__).with_name(module))
    require(
        review.get("schema") == schema
        and review.get("verdict") == verdict
        and review.get("source_execution_authorized") is True
        and review.get(key) == actual,
        "Actual independently reviewed implementation required",
    )
    return {"path": str(path), "sha256": expected, "module_sha256": actual, "verdict": verdict}


def command(engine, actor, engagement, kind, payload):
    state = engine.store.get(actor, engagement)
    return engine.command(
        actor,
        engagement,
        {
            "command_id": f"privacy-{state['revision']}-{kind}",
            "expected_revision": state["revision"],
            "kind": kind,
            "payload": payload,
        },
    )


def routes(accepted: AcceptedLibrary, branch: str):
    requested = [
        BusinessRoute(
            "SABLE-HARBOR-REFERENCE", branch, "privacyops." + system, "privacyops", system
        )
        for system in SYSTEMS
    ]
    accepted.verify()
    with quiescent_read(accepted.database) as db:
        registered = {tuple(row) for row in db.execute("SELECT company,branch,system FROM systems")}
    chosen = [r for r in requested if (r.company, r.branch, r.system) in registered]
    require(chosen, "Selected privacy business systems unavailable")
    return chosen, {
        "requested_systems": [r.system for r in requested],
        "registered_granted_systems": [r.system for r in chosen],
        "unregistered_systems": [r.system for r in requested if r not in chosen],
        "unregistered_is_not_event_nonoccurrence": True,
    }


def custody(row):
    return {
        "artifact_id": row["artifact_id"],
        "artifact_sha256": row["artifact_sha256"],
        "source": {k: row["source"][k] for k in CLOCK_ID},
    }


def retained(engine, auditor, engagement, rows):
    """Return the bytes actually held by the artifact store; discard cached bodies."""
    artifacts = {a["id"]: a for a in engine.store.get(auditor, engagement)["artifacts"]}
    result = []
    for row in rows:
        artifact = artifacts[row["artifact_id"]]
        require(
            artifact["status"] == "AVAILABLE",
            "Quarantined artifact cannot supply source examination",
        )
        path = engine.artifacts.root / artifact["sha256"]
        private_file(path)
        raw = engine.artifacts.read(artifact)
        require(
            hashlib.sha256(raw).hexdigest() == row["artifact_sha256"] == row["source"]["sha256"],
            "Actual retained original hash differs",
        )
        result.append({**{k: v for k, v in row.items() if k != "document"}, "retained_bytes": raw})
    return result


def document(row):
    raw = row["retained_bytes"]
    require(
        hashlib.sha256(raw).hexdigest() == row["artifact_sha256"],
        "Inspection original hash differs",
    )
    body = json.loads(raw)
    require(isinstance(body, dict), "Structured retained privacy record required")
    return body


def authored_instruction(state, task_id):
    task = next(t for t in state["tasks"] if t["id"] == task_id)
    control = next(c for c in state["controls"] if c["id"] == CONTROL)
    if task["kind"] in {"TOD", "IMPLEMENTATION", "TOE"}:
        require(
            control.get("procedure") and control.get("base_test"),
            "Authored base procedure/test unavailable",
        )
        return {
            "kind": task["kind"],
            "procedure": control["procedure"],
            "test": control["base_test"],
        }
    require(task.get("test"), "Exact additional-duty instruction unavailable")
    return {
        "kind": task["kind"],
        "procedure": task["title"],
        "test": task["test"],
        "requirement_ids": task.get("requirement_ids", []),
    }


def observations(rows, result, label):
    """Different performed steps retain different populations and observations."""
    if label in RECORD_SYSTEMS:
        selected_rows = [r for r in rows if r["logical_system"] in RECORD_SYSTEMS[label]]
        require(selected_rows, "Selected documentary inspection source absent")
        output = []
        for row in selected_rows:
            source = row["source"]
            body = document(row)
            ident = f"{source['system']}/{source['record']}/v{source['version']}"
            unresolved = [
                r
                for r in result["uncollected_dependency_references"]
                if all(r["from"][k] == source[k] for k in NATIVE_ID)
            ]
            joins = [
                r
                for r in result["checked_dependency_joins"]
                if all(r["from"][k] == source[k] for k in NATIVE_ID)
            ]
            observed = {
                "native_record": custody(row),
                "retained_business_fields": {k: v for k, v in body.items() if k != "dependencies"},
                "checked_dependencies": joins,
                "uncollected_dependencies": unresolved,
                "performed_step": METHODS[label]["performed"],
                "unperformed_step": METHODS[label]["unperformed"],
            }
            # These are inspected source facts, never a reconstructed company document.
            output.append(
                (ident, observed, "SUPPORT_UNAVAILABLE" if unresolved else "OBSERVED", [row])
            )
        return output, selected_rows
    by_artifact = {r["artifact_id"]: r for r in rows}
    output = []
    for case in result["cases"]:
        if "evidence" not in case:
            output.append((case["case_id"], case, "SUPPORT_UNAVAILABLE", []))
            continue
        systems = CASE_SYSTEMS if label in {"TOE", "TRANSFER"} else CASE_SYSTEMS[:4]
        refs = [by_artifact[case["evidence"][system]["artifact_id"]] for system in systems]
        facts = [
            {
                "system": r["logical_system"],
                "source": custody(r),
                "business_fields": {k: v for k, v in document(r).items() if k != "dependencies"},
            }
            for r in refs
        ]
        output.append(
            (
                case["case_id"],
                {
                    "case": case,
                    "recorded_facts": facts,
                    "performed_step": METHODS[label]["performed"],
                    "unperformed_step": METHODS[label]["unperformed"],
                },
                "EXCEPTION_RECORDED" if case["recorded_mismatches"] else "OBSERVED",
                refs,
            )
        )
    require(output, "Observed selected privacy cases unavailable")
    return output, [
        r for r in rows if r["logical_system"] in {*CASE_SYSTEMS, "privacy_reconciliation"}
    ]


def sample_items(observed):
    output = []
    for item_id, facts, status, refs in observed:
        raw = json.dumps(facts, sort_keys=True)
        # Preserve the complete examination in the workpaper. Bounded sample
        # observations identify the actual comparison and cite exact originals.
        if len(raw) > 3900:
            raw = json.dumps(
                {
                    "item_id": item_id,
                    "performed_step": facts.get("performed_step"),
                    "case": facts.get("case"),
                    "native_record": facts.get("native_record"),
                    "checked_dependency_count": len(facts.get("checked_dependencies", [])),
                    "uncollected_dependency_count": len(facts.get("uncollected_dependencies", [])),
                    "full_observation": "Exact linked workpaper observation for this item",
                },
                sort_keys=True,
            )
        require(
            len(raw) <= 4000 and len(refs) <= 20,
            "Selected sample observation/citation bound exceeded",
        )
        output.append(
            {
                "item_id": item_id,
                "observation": raw,
                "status": status,
                "evidence": [
                    {
                        "artifact_id": r["artifact_id"],
                        "sha256": r["artifact_sha256"],
                        "locator": (
                            f"Collected {r['source']['system']}/{r['source']['record']} "
                            f"v{r['source']['version']}; actual native byte/receipt join"
                        ),
                    }
                    for r in refs
                ],
            }
        )
    return output


def sample_batches(observed):
    """Partition performed items only to respect ordinary citation byte bounds."""
    batches, batch, unique = [], [], {}
    for item in observed:
        candidate = {**unique, **{r["artifact_id"]: r for r in item[3]}}
        total = sum(len(r["retained_bytes"]) for r in candidate.values())
        if batch and (len(candidate) > 100 or total > 32 * 1024 * 1024):
            batches.append(batch)
            batch, unique = [], {}
            candidate = {r["artifact_id"]: r for r in item[3]}
        require(len(candidate) <= 100, "One item exceeds ordinary citation bound")
        batch.append(item)
        unique = candidate
    if batch:
        batches.append(batch)
    return batches


def record_method(engine, auditor, engagement, rows, result, label, root):
    task_id = TASKS[label]
    observed, relevant = observations(rows, result, label)
    anchor = relevant[0]
    periods = [r["source"]["event_at"] for r in relevant]
    state = command(
        engine,
        auditor,
        engagement,
        "population.import",
        {
            "artifact_id": anchor["artifact_id"],
            "title": f"Privacy {label} observed documentary subpopulation",
            "rows": [{"id": item_id} for item_id, *_ in observed],
            "scope": {
                "boundary_id": "corporate",
                "unit": "selected privacy routing documentary records",
                "timezone": "UTC",
                "period_start": min(periods),
                "period_end": max(periods),
            },
            "source": {
                "source_id": "privacy:ordinary-collected:" + label,
                "query": (
                    "All exact native versions in declared granted privacy systems at "
                    "actual engagement clock; full observed subpopulation inspected"
                ),
                "completeness_representation": (
                    "Observed selected native subpopulation only. Recorded September close "
                    "precedes its claimed period end; intake nonoccurrence and broader "
                    "year/corporate completeness are unestablished."
                ),
                "excluded_ids": [],
            },
        },
    )
    pop = state["populations"][-1]
    state = command(
        engine,
        auditor,
        engagement,
        "population.assess",
        {
            "population_id": pop["id"],
            "status": "READY_FOR_PURPOSE",
            "purpose": f"Privacy {label} inspection of all observed selected documentary items",
            "rationale": (
                "Ready only to inspect the retained subpopulation. Missing month tail, "
                "enterprise denominator and actual operating/legal execution are not "
                "supplied by this assessment."
            ),
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
            "purpose": f"Privacy {label} every observed selected item",
            "rationale": (
                "Entire observed documentary subpopulation; no sampling extrapolation "
                "or full-period/enterprise credit"
            ),
        },
    )
    chosen = state["selections"][-1]
    work = {
        "task_id": task_id,
        "authored_instruction": authored_instruction(state, task_id),
        "selected_method": METHODS[label],
        "examination": result,
        "observations": [
            {"item_id": i, "facts": f, "status": s, "evidence": [custody(r) for r in refs]}
            for i, f, s, refs in observed
        ],
        "source_custody": [custody(r) for r in relevant],
        "conclusion": "LIMITATION",
        "independent_review": "PENDING_RESERVED_REVIEWER",
    }
    write(root / (label + "-WORKPAPER.json"), work)
    state = command(
        engine,
        auditor,
        engagement,
        "workpaper.add",
        {
            "title": f"Privacy {label} actual collected documentary inspection",
            "control_id": CONTROL,
            "task_ids": [task_id],
            "text": json.dumps(work, sort_keys=True, indent=2),
            "objective": METHODS[label]["performed"],
            "procedures": METHODS[label]["performed"],
            "evidence_ids": [r["artifact_id"] for r in relevant],
            "conclusion": "LIMITATION",
        },
    )
    paper = state["workpapers"][-1]
    execution_ids = []
    for batch in sample_batches(observed):
        state = command(
            engine,
            auditor,
            engagement,
            "sample.execution.record",
            {
                "task_id": task_id,
                "task_digest": digest(next(t for t in state["tasks"] if t["id"] == task_id)),
                "population_id": pop["id"],
                "population_digest": population(pop).sha256,
                "selection_id": chosen["id"],
                "selection_digest": selection(chosen).sha256,
                "workpaper_id": paper["id"],
                "workpaper_version": 1,
                "workpaper_digest": digest(paper["versions"][0]),
                "purpose": METHODS[label]["performed"],
                "procedure": METHODS[label]["performed"]
                + " Unperformed: "
                + METHODS[label]["unperformed"],
                "items": sample_items(batch),
            },
        )
        execution_ids.append(state["sample_executions"][-1]["id"])
    state = command(
        engine,
        auditor,
        engagement,
        "task.update",
        {
            "task_id": task_id,
            "status": "IN_PROGRESS",
            "conclusion": "LIMITATION",
            "rationale": (
                "Actual selected documentary steps performed and pinned. Exact "
                "authored procedure remains partial. "
            )
            + METHODS[label]["unperformed"],
        },
    )
    return {
        "task_id": task_id,
        "population_id": pop["id"],
        "selection_id": chosen["id"],
        "workpaper_id": paper["id"],
        "sample_execution_ids": execution_ids,
        "observed_items": len(observed),
    }


def record_findings(engine, auditor, engagement, rows, result):
    by_artifact = {r["artifact_id"]: r for r in rows}
    close = next(r for r in rows if r["logical_system"] == "privacy_reconciliation")
    held = document(close)
    conditions = [
        (
            "Selected privacy scope and premature closure limitation",
            {
                "unestablished_period_tail": result["unestablished_period_tail"],
                "selected_population_corroborated": result["selected_population_corroborated"],
                "old_held_rights_case_status": held.get("old_held_rights_case_status"),
                "prior_scope_exception_closed": held.get("prior_scope_exception_closed"),
                "enterprise_period_population_complete": held.get(
                    "enterprise_period_population_complete"
                ),
                "open_incident_ids": held.get("open_incident_ids"),
                "limits": result["limits"],
            },
            "SOURCE_SCOPE_LIMITATION",
            [close],
        )
    ]
    for case in result["cases"]:
        if case.get("recorded_mismatches"):
            refs = [by_artifact[v["artifact_id"]] for v in case["evidence"].values()]
            conditions.append(
                (
                    "Selected recorded privacy delivery discrepancy: " + case["case_id"],
                    {
                        "case_id": case["case_id"],
                        "observed_documentary_mismatches": case["recorded_mismatches"],
                        "legal_failure_or_actual_transfer_not_asserted": True,
                    },
                    "SELECTED_DOCUMENTARY_DISCREPANCY",
                    refs,
                )
            )
    for title, facts, classification, refs in conditions:
        command(
            engine,
            auditor,
            engagement,
            "finding.create",
            {
                "title": title,
                "condition": json.dumps(facts, sort_keys=True),
                "classification": classification,
                "control_id": CONTROL,
                "criterion": (
                    "Exact selected DAT002 authored instructions and documentary business "
                    "permissions; no whole HIPAA legal conclusion"
                ),
                "evidence_ids": [r["artifact_id"] for r in refs],
            },
        )


def run(
    repository,
    destination,
    accepted,
    program_pack,
    adapter_review,
    adapter_sha,
    method_review,
    method_sha,
):
    adapter = gate(adapter_review, adapter_sha, method=False)
    method = gate(method_review, method_sha, method=True)
    accepted.verify()
    private_file(program_pack)
    require(file_sha(program_pack) == PROGRAM_SHA, "Instruction-only program pack changed")
    require(
        not destination.exists()
        and not any(p.is_symlink() for p in [destination, *destination.parents]),
        "Fresh ordinary private destination required",
    )
    require(
        stat.S_IMODE(destination.parent.stat().st_mode) == 0o700,
        "Private execution parent required",
    )
    destination.mkdir(mode=0o700)
    ordinary_copy(program_pack, destination / "program-pack.json")
    write(destination / "ACCEPTANCE.json", {"adapter": adapter, "privacy_method": method})
    receipts = {}
    for branch in BRANCHES:
        root = destination / branch
        root.mkdir(mode=0o700)
        selected_routes, routing = routes(accepted, branch)
        write(root / "ROUTING.json", routing)
        session = LibraryAudit(accepted, root / "company-source", selected_routes)
        engine, state, identities = session.create(
            repository=repository,
            audit_root=root / "audit-state",
            program_pack=destination / "program-pack.json",
            payload={
                "command_id": "fresh-privacy-create",
                "title": "Selected company privacy documentary investigation " + branch,
                "discipline": "IT",
                "mode": "CLEAN",
                "configuration": {"selections": []},
                "scope": {
                    "programs": ["SOC2", "HIPAA"],
                    "report_type": "Type 2",
                    "period_start": "2027-01-01",
                    "period_end": "2027-12-31",
                    "fieldwork_start": "2027-12-31",
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
            "Exact selected authored privacy tasks unavailable",
        )
        require(len(state["tasks"]) == 409, "Complete pinned 2027 authored programme required")
        require(_time(state["simulated_at"]) == INITIAL, "Frozen initial fieldwork clock differs")
        write(
            root / "START.json",
            {
                "engagement_id": engagement,
                "task_count": len(state["tasks"]),
                "scope": state["scope"],
                "initial_clock": state["simulated_at"],
                **identities,
            },
        )
        try:
            command(engine, operator, engagement, "company.activate", {})
            command(engine, auditor, engagement, "kickoff.start", {})
            plan = {
                "methods": METHODS,
                "selected_task_ids": TASKS,
                "selected_month": "2027-09",
                "selection_sealed_at": datetime.now(UTC).isoformat(),
                "initial_clock": INITIAL,
                "final_clock": FINAL,
                "basis": (
                    "Exact authored instruction, explicit granted privacy systems and "
                    "entire observed subpopulations; no outcomes or producer recipes "
                    "inspected"
                ),
                "authored_instructions": {
                    label: authored_instruction(state, task) for label, task in TASKS.items()
                },
                "adapter_acceptance": adapter,
                "privacy_method_acceptance": method,
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
                        "note": label + " selected documentary fieldwork; no full-task credit",
                    },
                )
            state = command(
                engine,
                auditor,
                engagement,
                "pbc.create",
                {
                    "title": "Selected September privacy native histories",
                    "purpose": (
                        "Ordinary source discovery and entire observed documentary history "
                        "inspection"
                    ),
                    "control_id": CONTROL,
                    "person_id": "AS-P014",
                    "boundary_id": "corporate",
                },
            )
            request = state["requests"][-1]["id"]
            command(engine, auditor, engagement, "pbc.issue", {"request_id": request})
            session.authorize(**session.identities, engagement=engagement)
            initial_rows, initial_pages = session.discover(engine, auditor, engagement)
            old_rows, old_pages = session.discover(engine, auditor, engagement, as_of=EARLY_CLOSE)
            command(
                engine,
                auditor,
                engagement,
                "clock.advance",
                {"mode": "TARGET_DATE", "target": FINAL},
            )
            discovered, pages = session.discover(engine, auditor, engagement)
            require(
                _time(engine.store.get(auditor, engagement)["simulated_at"]) == FINAL,
                "Supported final clock differs",
            )
            write(
                root / "DISCOVERY.json",
                {
                    "initial_rows": [
                        {k: v for k, v in r.items() if k != "content"} for r in initial_rows
                    ],
                    "initial_pages": initial_pages,
                    "older_cutoff_rows": [
                        {k: v for k, v in r.items() if k != "content"} for r in old_rows
                    ],
                    "older_cutoff_pages": old_pages,
                    "older_cutoff": EARLY_CLOSE,
                    "rows": [{k: v for k, v in r.items() if k != "content"} for r in discovered],
                    "pages": pages,
                },
            )
            collected = [
                session.collect(
                    engine,
                    auditor,
                    engagement,
                    request,
                    row,
                    command_id=f"privacy-exact-collect-{index}",
                )
                for index, row in enumerate(discovered)
            ]
            write(
                root / "COLLECTION.json",
                [{k: v for k, v in r.items() if k != "document"} for r in collected],
            )
            actual = retained(engine, auditor, engagement, collected)
            result = examine(actual, as_of=FINAL)
            require(
                result["selected_period"]
                == {"start": "2027-09-01T00:00:00+00:00", "end": "2027-09-30T23:59:59+00:00"},
                "Selected documentary month changed",
            )
            links = {
                label: record_method(engine, auditor, engagement, actual, result, label, root)
                for label in TASKS
            }
            record_findings(engine, auditor, engagement, actual, result)
            state = engine.store.get(auditor, engagement)
            require(not state["reviews"], "Performer cannot supply independent review")
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
            write(root / "EXAMINATION.json", result)
            write(root / "FINAL_STATE.json", state)
            receipts[branch] = {
                "engagement_id": engagement,
                "collected_native_versions": len(collected),
                "zero_workroom_counts": identities["zero_workroom_counts"],
                "task_links": links,
                "native_business_sha256": session.business_sha256,
                "native_schema_sha256": session.schema_sha256,
                "selected_task_disposition": "IN_PROGRESS_LIMITATION",
                "independent_review": "PENDING",
            }
        finally:
            if (
                session.identities
                and session.engine
                and session.engine.store.get(auditor, engagement).get("company_source_binding")
            ):
                session.authorize(**session.identities, engagement=engagement, active=False)
                write(root / "ACCESS.json", session.access_log)
            session.check_unchanged()
    receipt = {
        "schema": "SH_FRESH_SELECTED_PRIVACY_EXECUTION_V1",
        "accepted_library": accepted.verify(),
        "adapter_acceptance": adapter,
        "privacy_method_acceptance": method,
        "program_pack_sha256": PROGRAM_SHA,
        "branches": receipts,
        "full_audit_credit": False,
        "actual_privacy_routing_reperformed": False,
        "real_hipaa_applicability_decided": False,
        "enterprise_period_population_established": False,
    }
    write(destination / "RECEIPT.json", receipt)
    write(
        destination / "MANIFEST.json",
        {
            "schema": "SH_FRESH_SELECTED_PRIVACY_FILES_V1",
            "files": {
                str(p.relative_to(destination)): file_sha(p)
                for p in sorted(destination.rglob("*"))
                if p.is_file()
            },
        },
    )
    return receipt


def verify(destination, accepted, adapter_review, adapter_sha, method_review, method_sha):
    """Read-only original-byte, command-history and method/sample reperformance."""
    adapter = gate(adapter_review, adapter_sha, method=False)
    method = gate(method_review, method_sha, method=True)
    pins = accepted.verify()
    manifest = json.loads((destination / "MANIFEST.json").read_bytes())
    require(
        set(manifest) == {"schema", "files"}
        and manifest["schema"] == "SH_FRESH_SELECTED_PRIVACY_FILES_V1",
        "Privacy manifest schema differs",
    )
    files = {
        str(p.relative_to(destination)): p
        for p in destination.rglob("*")
        if p.is_file() or p.is_symlink()
    }
    require(
        set(files) == set(manifest["files"]) | {"MANIFEST.json"},
        "Privacy execution file inventory changed",
    )
    for rel, path in files.items():
        private_file(path)
        if rel != "MANIFEST.json":
            require(file_sha(path) == manifest["files"][rel], "Privacy execution file pin changed")
    for p in [destination, *[p for p in destination.rglob("*") if p.is_dir()]]:
        require(
            not p.is_symlink() and stat.S_IMODE(p.stat().st_mode) == 0o700,
            "Private ordinary output directory required",
        )
    receipt = json.loads((destination / "RECEIPT.json").read_bytes())
    require(
        receipt["accepted_library"] == pins
        and receipt["adapter_acceptance"] == adapter
        and receipt["privacy_method_acceptance"] == method,
        "Accepted execution custody differs",
    )
    require(set(receipt["branches"]) == set(BRANCHES), "Exact two privacy branch boundary required")
    require(
        all(
            receipt[k] is False
            for k in (
                "full_audit_credit",
                "actual_privacy_routing_reperformed",
                "real_hipaa_applicability_decided",
                "enterprise_period_population_established",
            )
        ),
        "False full privacy audit/operating credit",
    )
    require(file_sha(destination / "program-pack.json") == PROGRAM_SHA, "Instruction pack changed")
    summaries = {}
    for branch in BRANCHES:
        root = destination / branch
        branch_receipt = receipt["branches"][branch]
        start = json.loads((root / "START.json").read_bytes())
        plan = json.loads((root / "PLAN.json").read_bytes())
        require(
            plan["methods"] == METHODS
            and plan["selected_task_ids"] == TASKS
            and plan["initial_clock"] == INITIAL
            and plan["final_clock"] == FINAL,
            "Presealed selected privacy plan changed",
        )
        require(not any(start["zero_workroom_counts"].values()), "Nonzero initial work/evidence")
        ids = {k: start[k] for k in ("operator", "auditor", "reviewer")}
        require(len(set(ids.values())) == 3, "Privacy actor separation differs")
        database = root / "company-source/company.sqlite3"
        require(
            business_digest(database)
            == business_digest(accepted.database)
            == branch_receipt["native_business_sha256"],
            "Staged native business bytes changed",
        )
        require(
            schema_sha(database)
            == schema_sha(accepted.database)
            == branch_receipt["native_schema_sha256"],
            "Native schema/immutable triggers changed",
        )
        with quiescent_read(root / "audit-state/engagements.sqlite3") as db:
            states = db.execute("SELECT id,state FROM engagements").fetchall()
            require(
                len(states) == 1 and states[0]["id"] == start["engagement_id"],
                "Exact fresh engagement differs",
            )
            state = json.loads(states[0]["state"])
            require(
                dict(
                    db.execute(
                        "SELECT principal,permission FROM members WHERE engagement=?",
                        (state["id"],),
                    )
                )
                == {
                    ids["operator"]: "instruct",
                    ids["auditor"]: "learn",
                    ids["reviewer"]: "review",
                },
                "Reserved reviewer membership differs",
            )
            previous, events = "", []
            for revision, row in enumerate(db.execute("SELECT * FROM events ORDER BY revision")):
                event = {
                    "actor": row["actor"],
                    "recorded_at": row["recorded_at"],
                    "previous_hash": row["previous_hash"],
                    "state": json.loads(row["state"]),
                    "command": json.loads(row["command"]),
                    "command_id": row["command_id"],
                }
                require(
                    row["revision"] == revision
                    and row["previous_hash"] == previous
                    and digest(event) == row["hash"]
                    and digest(event["command"]) == row["request_hash"],
                    "Actual privacy command history changed",
                )
                previous = row["hash"]
                events.append(event)
        require(
            events
            and events[-1]["state"] == state
            and state == json.loads((root / "FINAL_STATE.json").read_bytes()),
            "Final privacy state/history/export differs",
        )
        first = events[0]["state"]
        require(
            all(not first[k] for k in start["zero_workroom_counts"])
            and _time(first["simulated_at"]) == INITIAL,
            "Initial privacy state/clock differs",
        )
        require(
            all(
                t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN"
                for t in first["tasks"]
            ),
            "Initial tasks inherited credit",
        )
        require(
            not state["reviews"] and all(e["actor"] != ids["reviewer"] for e in events),
            "Manufactured independent privacy review",
        )
        require(
            _time(state["simulated_at"]) == FINAL
            and state["scope"]["fieldwork_start"] == "2027-12-31"
            and state["company_source_binding"]
            == {"company": "SABLE-HARBOR-REFERENCE", "branch": branch}
            and state["evidence_acquisition"] == "COMPANY_SOURCE_COLLECTION",
            "Activated scope/clock binding differs",
        )
        advances = [e for e in events if e["command"].get("kind") == "clock.advance"]
        require(
            len(advances) == 1
            and advances[0]["actor"] == ids["auditor"]
            and advances[0]["command"]["payload"] == {"mode": "TARGET_DATE", "target": FINAL},
            "Supported actual clock advance missing",
        )
        require(
            all(
                t["status"] == ("IN_PROGRESS" if t["id"] in TASKS.values() else "NOT_STARTED")
                and t["conclusion"] == ("LIMITATION" if t["id"] in TASKS.values() else "NOT_RUN")
                for t in state["tasks"]
            ),
            "False task credit or incomplete disposition",
        )
        artifacts = {a["id"]: a for a in state["artifacts"]}
        collected = json.loads((root / "COLLECTION.json").read_bytes())
        discovery = json.loads((root / "DISCOVERY.json").read_bytes())
        require(
            len(collected)
            == len(discovery["rows"])
            == len(artifacts)
            == branch_receipt["collected_native_versions"],
            "Actual collected census differs",
        )
        require(
            all(r["record"] != "PERIOD-01" for r in discovery["older_cutoff_rows"]),
            "Early unavailable month-close leaked",
        )
        actual = []
        with quiescent_read(database) as db:
            require(
                db.execute("SELECT COUNT(*) FROM grants WHERE active!=0").fetchone()[0] == 0,
                "Privacy source grants not revoked",
            )
            require(
                db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == len(collected),
                "Ordinary collection journal differs",
            )
            for row in collected:
                source = row["source"]
                require(
                    source["branch"] == branch
                    and source["system"] == "privacyops." + row["logical_system"],
                    "Native privacy routing differs",
                )
                native = db.execute(
                    (
                        "SELECT * FROM versions WHERE company=? AND branch=? AND system=? AND "
                        "record=? AND version=?"
                    ),
                    tuple(source[k] for k in NATIVE_ID),
                ).fetchone()
                require(
                    native is not None and all(native[k] == source[k] for k in CLOCK_ID),
                    "Exact collected native custody differs",
                )
                require(
                    source["provenance"] == json.loads(native["provenance"])
                    and source["origin"] == native["origin"],
                    "Collected provenance differs",
                )
                require(
                    _time(source["available_at"]) <= FINAL
                    and _time(source["event_at"]) <= FINAL
                    and _time(plan["selection_sealed_at"])
                    <= _time(row["receipt"]["collected_at"])
                    <= _time(datetime.now(UTC).isoformat()),
                    "Collection publication/custody chronology differs",
                )
                recorded = db.execute(
                    "SELECT receipt FROM collections WHERE command_id=?",
                    (row["receipt"]["command_id"],),
                ).fetchone()
                require(
                    recorded is not None and json.loads(recorded["receipt"]) == row["receipt"],
                    "Immutable collection receipt differs",
                )
                artifact = artifacts[row["artifact_id"]]
                require(
                    artifact["status"] == "AVAILABLE"
                    and artifact["source"]["receipt"] == row["receipt"]
                    and artifact["sha256"] == row["artifact_sha256"] == source["sha256"],
                    "Audit artifact/receipt custody differs",
                )
                path = root / "audit-state/artifacts" / artifact["sha256"]
                require(
                    path.read_bytes() == native["content"] and file_sha(path) == source["sha256"],
                    "Actual retained original bytes differ",
                )
                actual.append({**row, "retained_bytes": path.read_bytes()})
        result = examine(actual, as_of=FINAL)
        require(
            result == json.loads((root / "EXAMINATION.json").read_bytes()),
            "Separate retained-byte examination differs",
        )
        for label, task_id in TASKS.items():
            link = branch_receipt["task_links"][label]
            observed, relevant = observations(actual, result, label)
            work = json.loads((root / (label + "-WORKPAPER.json")).read_bytes())
            paper = next(w for w in state["workpapers"] if w["id"] == link["workpaper_id"])
            require(
                work["task_id"] == task_id
                and work["authored_instruction"] == authored_instruction(state, task_id)
                and work["selected_method"] == METHODS[label]
                and work["examination"] == result
                and work["source_custody"] == [custody(r) for r in relevant]
                and work["observations"]
                == [
                    {"item_id": i, "facts": f, "status": s, "evidence": [custody(r) for r in refs]}
                    for i, f, s, refs in observed
                ]
                and json.loads(paper["versions"][0]["text"]) == work,
                "Exact privacy method workpaper differs",
            )
            traces = [t for t in state["sample_executions"] if t["task_id"] == task_id]
            batches = sample_batches(observed)
            require(
                len(traces) == len(batches)
                and [t["id"] for t in traces] == link["sample_execution_ids"],
                "Exact performed privacy sample batches required",
            )
            pop = next(p for p in state["populations"] if p["id"] == link["population_id"])
            chosen = next(s for s in state["selections"] if s["id"] == link["selection_id"])
            source_rows = {r["id"]: r for r in population(pop).rows}
            performed_ids = []
            for trace, batch in zip(traces, batches, strict=True):
                require(
                    trace["population_id"] == pop["id"]
                    and trace["selection_id"] == chosen["id"]
                    and population(pop).sha256 == trace["population_digest"]
                    and selection(chosen).sha256 == trace["selection_digest"]
                    and digest(paper["versions"][0]) == trace["workpaper_digest"],
                    "Sample input lineage differs",
                )
                expected_items = [
                    {
                        **item,
                        "item_digest": digest(source_rows[item["item_id"]]),
                        "selection_basis": "SAMPLED",
                        "locator_validation": "AUTHOR_SUPPLIED_NOT_CONTENT_MATCH_VERIFIED",
                    }
                    for item in sample_items(batch)
                ]
                require(
                    trace["items"] == expected_items
                    and trace["automatic_testing_credit"] is False
                    and trace["independent_review"] == "NOT_PERFORMED",
                    "Actual item performance differs or false review credit",
                )
                performed_ids.extend(i["item_id"] for i in trace["items"])
            require(
                len(performed_ids) == len(set(performed_ids))
                and set(performed_ids) == set(selection(chosen).all_ids),
                "Entire observed privacy selection not exactly performed across batches",
            )
        summaries[branch] = {
            "native_versions": len(actual),
            "selected_tasks": len(TASKS),
            "sample_traces": len(state["sample_executions"]),
            "documentary_mismatch_case_ids": result["recorded_mismatch_case_ids"],
            "tail": result["unestablished_period_tail"],
            "full_audit_credit": False,
        }
    accepted.verify()
    return {
        "schema": "SH_FRESH_SELECTED_PRIVACY_READ_ONLY_VERIFICATION_V1",
        "verdict": "PASS_REPRODUCIBLE_SELECTED_DOCUMENTARY_PRIVACY_WORK_NO_FULL_AUDIT_CREDIT",
        "receipt_sha256": file_sha(destination / "RECEIPT.json"),
        "manifest_sha256": file_sha(destination / "MANIFEST.json"),
        "branches": summaries,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "repository",
        "destination",
        "source-pins",
        "program-pack",
        "adapter-review",
        "method-review",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--adapter-review-sha256", required=True)
    parser.add_argument("--method-review-sha256", required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    common = (
        args.destination,
        load_pins(args.source_pins),
        args.adapter_review,
        args.adapter_review_sha256,
        args.method_review,
        args.method_review_sha256,
    )
    result = (
        verify(*common)
        if args.verify_only
        else run(args.repository, args.destination, common[1], args.program_pack, *common[2:])
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
