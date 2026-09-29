"""Read-only company-source census; inventories never establish audit sufficiency."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
from collections import Counter
from pathlib import Path

SOURCE_ROOTS = {
    "docs/canon": "CONTROLLING_CANON_REQUIRES_ACCEPTANCE_INTERPRETATION",
    "docs/governance": "GOVERNANCE_SOURCE_OR_HISTORY",
    "docs/controls": "CONTROL_DESIGN_SOURCE",
    "docs/organization": "ORGANIZATIONAL_SOURCE_OR_REPRESENTATION",
    "docs/structured": "STRUCTURED_CANON_DERIVATIVE_OR_SOURCE",
    "docs/finance": "FINANCE_SOURCE_OR_LOCKED_HISTORY",
    "enterprise/operations/source": "PUBLIC_SYNTHETIC_OPERATING_HISTORY_INPUT",
    "enterprise/business/source": "PUBLIC_SYNTHETIC_BUSINESS_MODEL_INPUT",
    "enterprise/operations/export_schema.json": "EXPLICIT_EXPORT_SCHEMA",
    "enterprise/operations/export_scope.json": "EXPLICIT_EXPORT_SCOPE",
    "enterprise/operations/publications/review_manifest.json": "REVIEWED_DERIVATIVE_MANIFEST",
    "enterprise/ccf/assurance/design_data/control_procedures.json": "PROPOSED_CONTROL_PROCEDURES",
    "enterprise/ccf/assurance/completion_data/control_procedures.json": (
        "PROPOSED_CONTROL_PROCEDURES"
    ),
    "enterprise/generated/audit-suite/private-corpus/parent-support/source.json": (
        "PRIVATE_SYNTHETIC_COMPANY_SOURCE_FIXTURE_MIGRATION_CANDIDATE"
    ),
}


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def read_snapshot(store: Path, engagement: str):
    """Read one consistent SQLite transaction; never read credentials or mutate state."""
    database = store / "engagements.sqlite3"
    if database.is_symlink() or not database.is_file():
        raise ValueError("Expected a regular engagement database")
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        row = db.execute(
            "SELECT revision,state FROM engagements WHERE id=?", (engagement,)
        ).fetchone()
        if row is None:
            raise ValueError("Engagement not found")
        state = json.loads(row[1])
        if state.get("id") != engagement or state.get("revision") != row[0]:
            raise ValueError("Snapshot identity/revision mismatch")
        return state, digest_bytes(row[1].encode())


def file_inventory(repository: Path):
    result = []
    for relative, classification in SOURCE_ROOTS.items():
        root = repository / relative
        files = [root] if root.is_file() else sorted(root.rglob("*")) if root.is_dir() else []
        if not files:
            result.append({"path": relative, "classification": classification, "status": "ABSENT"})
        for path in files:
            if not path.is_file() or path.is_symlink():
                continue
            data = path.read_bytes()
            item = {
                "path": str(path.relative_to(repository)),
                "classification": classification,
                "status": "PRESENT_NOT_SUFFICIENT_BY_EXISTENCE",
                "sha256": digest_bytes(data),
                "bytes": len(data),
                "explicit_control_references": sorted(
                    set(
                        re.findall(
                            r"\bSH-[A-Z]{2,5}-\d{3}\b", data.decode("utf-8", errors="ignore")
                        )
                    )
                )
                if path.suffix in {".json", ".md"}
                else [],
            }
            if path.suffix == ".json":
                try:
                    value = json.loads(data)
                    item["structured_records"] = value
                    item["top_level_fields"] = sorted(value) if isinstance(value, dict) else []
                    item["declared_classification"] = (
                        value.get("classification") if isinstance(value, dict) else None
                    )
                    item["top_level_list_counts"] = (
                        {k: len(v) for k, v in value.items() if isinstance(v, list)}
                        if isinstance(value, dict)
                        else {"items": len(value)}
                        if isinstance(value, list)
                        else {}
                    )
                except (ValueError, UnicodeError):
                    item["parse_status"] = "UNPARSED"
            result.append(item)
    return result


def inventory(repository: Path, store: Path, engagement: str):
    state, state_hash = read_snapshot(store, engagement)
    sources = file_inventory(repository)
    procedures = {}
    for relative in SOURCE_ROOTS:
        if relative.endswith("control_procedures.json") and (repository / relative).exists():
            for procedure in json.loads((repository / relative).read_text()):
                procedures.setdefault(procedure["control_id"], []).append(
                    {**procedure, "source_path": relative}
                )
    controls, tasks, requests, gaps, units = [], [], [], [], []
    world = store / "worlds" / engagement
    for path in sorted(world.glob("unit-*.json")):
        if path.is_symlink():
            raise ValueError("Refusing a symlinked frozen unit")
        value = json.loads(path.read_text())
        units.append({"path": str(path), "sha256": digest_bytes(path.read_bytes()), "value": value})
    by_control = {u["value"]["control_id"]: u for u in units}
    for control in state["controls"]:
        cid = control["id"]
        unit = by_control.get(cid)
        source_refs = control.get("source_refs", [])
        entry = {
            "control_id": cid,
            "title": control.get("title"),
            "frequency": control.get("frequency"),
            "assignment": control.get("assignment"),
            "source_refs": source_refs,
            "existing_source_reference_candidates": [
                x["path"] for x in sources if cid in x.get("explicit_control_references", [])
            ],
            "procedure": control.get("procedure"),
            "candidate_test": control.get("candidate_test"),
            "authored_procedure_sources": procedures.get(cid, []),
            "requirement_links": control.get("requirement_links", []),
            "additional_duties": control.get("additional_duties", []),
            "prepared_world": {k: unit[k] for k in ["path", "sha256"]} if unit else None,
            "prepared_coverage_status": unit["value"].get("coverage_status") if unit else None,
            "source_classes_to_resolve": [
                "POLICY_AND_DESIGN",
                "DATED_OPERATING_RECORDS",
                "RECONCILED_SOURCE_POPULATION",
                "SEPARATE_CORROBORATION_AND_REVIEW",
            ],
            "company_source_collection_mapping": "NOT_ESTABLISHED_BY_PREPARED_WORLD",
            "professional_sufficiency": "NOT_ASSESSED",
        }
        controls.append(entry)
        gaps.append(
            {
                "control_id": cid,
                "gap": "FULL_PROCEDURE_COMPANY_SOURCE_LINEAGE_NOT_ESTABLISHED",
                "basis": (
                    "Frozen engagement support is not proof of "
                    "an independently existing source store or collection query"
                ),
                "owner": control.get("owner_ids", []),
                "status": "OPEN",
            }
        )
        if not unit:
            gaps.append({"control_id": cid, "gap": "FROZEN_SUPPORT_UNIT_ABSENT", "status": "OPEN"})
        for req in unit["value"].get("requests", []) if unit else []:
            requests.append(
                {
                    "control_id": cid,
                    "request_plan_id": req.get("id"),
                    "title": req.get("title"),
                    "purpose": req.get("purpose"),
                    "coverage": req.get("coverage"),
                    "available_by": req.get("available_by"),
                    "source_class": "ENGAGEMENT_PREPARED_SUPPORT",
                    "artifacts": [
                        {
                            "name": a.get("name"),
                            "kind": a.get("artifact_kind"),
                            "format": a.get("recipe", {}).get("format"),
                            "columns": a.get("recipe", {}).get("columns", []),
                            "source": a.get("source"),
                            "available_by": a.get("available_by"),
                        }
                        for a in req.get("artifact_recipes", [])
                    ],
                }
            )
    control_map = {c["id"]: c for c in state["controls"]}
    for task in state["tasks"]:
        control = control_map.get(task.get("control_id"), {})
        tasks.append(
            {
                **task,
                "control_procedure": control.get("procedure"),
                "candidate_control_test": control.get("candidate_test"),
                "control_evidence_expectation": control.get("evidence_expectation"),
                "additional_duty_candidates": [
                    d
                    for d in control.get("additional_duties", [])
                    if task["id"].endswith("-" + d["id"])
                ]
                if task["kind"] == "ADDITIONAL_DUTY"
                else [],
                "source_request_plan_ids": [
                    r["request_plan_id"]
                    for r in requests
                    if r["control_id"] == task.get("control_id")
                ],
                "mapping_boundary": (
                    "Control-level candidates only; procedure-specific "
                    "source/query/attribute sufficiency remains open"
                ),
            }
        )
    if len(tasks) != len(state["tasks"]) or len(controls) != len(state["controls"]):
        raise ValueError("Incomplete snapshot census")
    return {
        "schema_version": "1.0",
        "status": "INVENTORY_NOT_A_READINESS_OPINION",
        "engagement_id": engagement,
        "state_revision": state["revision"],
        "state_sha256": state_hash,
        "scope": state["scope"],
        "organization": state.get("organization"),
        "people": state.get("people", []),
        "controls": controls,
        "procedures_and_tasks": tasks,
        "prepared_requests": requests,
        "source_files": sources,
        "gaps": gaps,
        "counts": {
            "scoped_controls": len(controls),
            "audit_tasks": len(tasks),
            "prepared_requests": len(requests),
            "source_files": sum(x["status"] != "ABSENT" for x in sources),
            "task_kinds": dict(Counter(t["kind"] for t in tasks)),
            "task_statuses": dict(Counter(t["status"] for t in tasks)),
            "request_statuses": dict(Counter(r["status"] for r in state["requests"])),
            "retained_audit_artifacts": len(state["artifacts"]),
            "prepared_support_classes": dict(
                Counter(r.get("coverage", {}).get("support_status", "UNDECLARED") for r in requests)
            ),
        },
        "limits": [
            (
                "Exhaustive for the pinned engagement's controls/tasks and "
                "declared source roots; not an unrestricted disk census."
            ),
            (
                "Existing operations/business inputs are reusable synthetic "
                "history, not proof of live external systems."
            ),
            (
                "Private rubric/case-bank, credentials, database "
                "principals and inference configuration excluded."
            ),
            "No source population was declared complete and no professional conclusion assigned.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--engagement", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        raise ValueError("Inventory output must be new")
    result = inventory(args.repository.resolve(), args.store.resolve(), args.engagement)
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if args.output.parent.is_symlink() or args.output.parent.stat().st_mode & 0o077:
        raise ValueError("Inventory requires a private0700 output directory")
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as output:
        json.dump(result, output, indent=2)
        output.write("\n")
    print(json.dumps({"status": result["status"], "counts": result["counts"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
