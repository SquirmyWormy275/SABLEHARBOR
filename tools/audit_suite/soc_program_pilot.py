"""Portable, source-bound SOC 2 audit-program exercise (no answer key)."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from enterprise.audit_suite.source_library_security_execution import SYSTEMS
from tools.audit_suite.company_record_delivery import verify as verify_delivery

ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT / "docs/audit-suite/company-records"
PLAN = ROOT / "docs/audit-suite/soc-program-pilot/PLAN.json"
MANIFEST_SHA256 = "30cbdf23a68532e5026a87d0dddb06cd09242b87ea3a58d009b39aacddc629c7"
SCHEMA = "SH_SOC_PROGRAM_PILOT_SUBMISSION_V1"
HISTORIES = ("history-01", "history-02")
TASKS = ("SEC003", "SEC005", "BCM003")
FIELDS = {
    "SEC003": (
        "population_ids",
        "sample_ids",
        "omitted_scan_assets",
        "advisory_disposition",
        "count_contradictions",
        "retest_selected_coverage_complete",
        "actual_scanner_execution",
        "conclusion",
    ),
    "SEC005": (
        "publisher_ids",
        "unreceived_by_month",
        "unreviewed_by_month",
        "company_review_population_basis",
        "actual_packets_or_executable_execution",
        "conclusion",
    ),
    "BCM003": (
        "exercise_versions",
        "recalculated_minutes",
        "within_declared_rto",
        "actual_restore_reperformed",
        "independent_data_usability_tested",
        "conclusion",
    ),
}
REQUIRED_SYSTEMS = {
    "SEC003": {
        "sec005operated.security_inventory",
        "sec005operated.security_baseline",
        "sec003vuln.vulnerability_inventory",
        "sec003vuln.vulnerability_scan",
        "sec003vuln.vulnerability_advisory",
        "sec003vuln.vulnerability_reconciliation",
    },
    "SEC005": {
        "sec005operated.security_inventory",
        "sec005operated.security_baseline",
        "sec005operated.security_approval",
        "sec005operated.security_application",
        "sec005operated.security_probe",
        "sec005operated.security_monitor",
        "sec005operated.security_reconciliation",
    },
    "BCM003": {
        "bcm.business_impact",
        "bcm.technical_objectives",
        "bcm.authority_decision",
        "bcm.exercise_result",
    },
}


def task_source(task: str, system: str) -> bool:
    family, role = system.split(".", 1)
    if task == "SEC003":
        return family == "sec003vuln" or (
            family == "sec005operated" and role in {"security_inventory", "security_baseline"}
        )
    if task == "SEC005":
        return family == "sec005operated"
    return family == "bcm" or system == "transition.recovery_exercise"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_source(root: Path = SOURCE_ROOT) -> tuple[dict, dict[str, dict]]:
    """Verify the entire Git delivery before admitting selected source versions."""
    root = Path(root).resolve()
    raw = (root / "manifest.json").read_bytes()
    if sha(raw) != MANIFEST_SHA256:
        raise ValueError("Pilot requires the exact accepted company-record manifest")
    verify_delivery(root)
    manifest = json.loads(raw)
    selected_systems = {
        f"{family}.{system}" for family, names in SYSTEMS.items() for system in names
    }
    selected = {
        row["path"]: row for row in manifest["records"] if row["system"] in selected_systems
    }
    if {h: sum(row["history_id"] == h for row in selected.values()) for h in HISTORIES} != {
        "history-01": 39,
        "history-02": 55,
    }:
        raise ValueError("Selected source population changed")
    if any(row["relationship"] != "original" for row in selected.values()):
        raise ValueError("Selected audit originals include a derivative")
    return manifest, selected


def template(root: Path = SOURCE_ROOT) -> dict:
    _, selected = load_source(root)
    return {
        "schema": SCHEMA,
        "source_manifest_sha256": MANIFEST_SHA256,
        "plan_sha256": sha(PLAN.read_bytes()),
        "prepared_by": "",
        "histories": {
            history: {
                task: {
                    "observations": {field: None for field in FIELDS[task]},
                    "citations": [],
                    "finding": "",
                    "retest_and_scope_note": "",
                }
                for task in TASKS
            }
            for history in HISTORIES
        },
        "source_inventory": {
            history: [
                {
                    "path": path,
                    "sha256": row["sha256"],
                    "system": row["system"],
                    "record": row["record"],
                    "version": row["version"],
                }
                for path, row in sorted(selected.items())
                if row["history_id"] == history
            ]
            for history in HISTORIES
        },
        "review": {
            "performed_by": "",
            "independent_of_preparer": None,
            "scope_and_limitations_checked": None,
            "note": "",
        },
    }


def validate_submission(submission: dict, selected: dict[str, dict]) -> dict:
    """Validate custody and completeness; the private grader assesses observations."""
    if not isinstance(submission, dict) or submission.get("schema") != SCHEMA:
        raise ValueError("Unsupported submission schema")
    if submission.get("source_manifest_sha256") != MANIFEST_SHA256 or submission.get(
        "plan_sha256"
    ) != sha(PLAN.read_bytes()):
        raise ValueError("Source or frozen plan pin changed")
    if not isinstance(submission.get("prepared_by"), str) or not submission["prepared_by"].strip():
        raise ValueError("Identify the preparer")
    if set(submission.get("histories", {})) != set(HISTORIES):
        raise ValueError("Both separate histories are required")
    expected_inventory = template_inventory(selected)
    if submission.get("source_inventory") != expected_inventory:
        raise ValueError("Selected source inventory changed")
    lineage = {}
    for history in HISTORIES:
        work = submission["histories"][history]
        if set(work) != set(TASKS):
            raise ValueError("All three procedures are required in each history")
        lineage[history] = {}
        for task in TASKS:
            answer = work[task]
            observations = answer.get("observations")
            if not isinstance(observations, dict) or set(observations) != set(FIELDS[task]):
                raise ValueError(f"{history}/{task}: observation fields changed")
            if any(value is None for value in observations.values()):
                raise ValueError(f"{history}/{task}: incomplete observations")
            if any(
                not isinstance(answer.get(field), str) or not answer[field].strip()
                for field in ("finding", "retest_and_scope_note")
            ):
                raise ValueError(f"{history}/{task}: finding and retest/scope note required")
            citations = answer.get("citations")
            if not isinstance(citations, list) or not citations:
                raise ValueError(f"{history}/{task}: source citations required")
            seen = set()
            systems = set()
            for citation in citations:
                if not isinstance(citation, dict) or set(citation) != {"path", "sha256"}:
                    raise ValueError("Citation requires exact path and SHA-256")
                path = citation["path"]
                row = selected.get(path)
                if (
                    row is None
                    or row["history_id"] != history
                    or citation["sha256"] != row["sha256"]
                ):
                    raise ValueError(f"{history}/{task}: citation missing, crossed or changed")
                if path in seen:
                    raise ValueError("Duplicate citation")
                seen.add(path)
                systems.add(row["system"])
            if not REQUIRED_SYSTEMS[task] <= systems:
                raise ValueError(f"{history}/{task}: required source roles not cited")
            required_paths = {
                path
                for path, row in selected.items()
                if row["history_id"] == history and task_source(task, row["system"])
            }
            if not required_paths <= seen:
                raise ValueError(f"{history}/{task}: selected source versions not fully cited")
            lineage[history][task] = sorted(seen)
    review = submission.get("review")
    if not isinstance(review, dict) or set(review) != {
        "performed_by",
        "independent_of_preparer",
        "scope_and_limitations_checked",
        "note",
    }:
        raise ValueError("Explicit review record required")
    if not isinstance(review["note"], str) or not review["note"].strip():
        raise ValueError("Reviewer note required")
    if not isinstance(review["performed_by"], str) or not review["performed_by"].strip():
        raise ValueError("Identify the reviewer")
    if (
        review["independent_of_preparer"] is True
        and review["performed_by"] == submission["prepared_by"]
    ):
        raise ValueError("Independent reviewer identity must differ from preparer")
    if review["scope_and_limitations_checked"] is not True:
        raise ValueError("Review must address scope and limitations")
    return {"citation_paths": lineage, "review_identity": "USER_ASSERTED_UNVERIFIED"}


def template_inventory(selected: dict[str, dict]) -> dict:
    return {
        history: [
            {
                "path": path,
                "sha256": row["sha256"],
                "system": row["system"],
                "record": row["record"],
                "version": row["version"],
            }
            for path, row in sorted(selected.items())
            if row["history_id"] == history
        ]
        for history in HISTORIES
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("init", "check"))
    parser.add_argument("path", type=Path, help="Fresh submission path, or completed submission")
    parser.add_argument("--source-root", type=Path, default=SOURCE_ROOT)
    args = parser.parse_args()
    if args.action == "init":
        content = json.dumps(template(args.source_root), indent=2, sort_keys=True) + "\n"
        with args.path.open("x") as output:
            output.write(content)
        print(json.dumps({"submission": str(args.path), "status": "READY_TO_COMPLETE"}))
    else:
        _, selected = load_source(args.source_root)
        result = validate_submission(json.loads(args.path.read_bytes()), selected)
        print(json.dumps({"status": "SOURCE_BOUND_SUBMISSION", **result}, sort_keys=True))


if __name__ == "__main__":
    main()
