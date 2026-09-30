"""Read-only planning joins for the frozen 283 documentary/activity routes per side.

This produces source-search candidates, not company records or audit evidence.
Private reviewed inputs stay outside the tracked tree and are read by exact hash.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

SCHEMA = "SH_DOCUMENTARY_ACTIVITY_DISCOVERY_MATRIX_V1"
BASE = "enterprise/generated/audit-suite/acceptance-audit-2026-09-22/"
PLAN = BASE + "aq06-aq07-unmatched373-company-native-coverage-plan-v2/"
PREFLIGHT = (
    "enterprise/generated/audit-suite/source-complete-registry-readonly-preflight-2026-09-29/"
)
REVIEW = (
    "enterprise/generated/audit-suite/"
    "source-complete-registry-readonly-preflight-independent-review-2026-09-29-v3/"
)
INPUTS = {
    "plan_manifest": (
        PLAN + "MANIFEST.json",
        "7460ebcb5ed8ebe887f2ebe1cce61d13b61a9dea51cf878570936dd890728aa8",
    ),
    "plan_review": (
        BASE + "aq06-aq07-unmatched373-company-native-coverage-independent-review-v2/REVIEW.json",
        "f09117919331a3a2ca36963f4d9ad9135461af47f9fd9a6db00c38a0d235e1f4",
    ),
    "control_routes": (
        PLAN + "CONTROL-ROUTES.json",
        "aaa0b627ec7f5022bb79b920ecddd71920b9dbcfac8389ac5f5c687df09cb874",
    ),
    "task_routes": (
        PLAN + "TASK-ROUTES.json",
        "00415fca7d40339ca416514829e62a33b0a7f47e2905c818fd4fee329d5cf69b",
    ),
    "screen_v2": (
        BASE + "aq06-aq07-paired-all409-task-source-screen-v2/TASK-ROWS.json",
        "8fc784db26fb65033a8058403e4898a2b4414b400c793c4e32c7fcc8bea6b5c5",
    ),
    "screen_v3": (
        BASE + "aq06-aq07-paired-all409-task-source-screen-v3/TASK-ROWS.json",
        "a0f995228683bde4663e1232380622fe208a225d71152cfb5aaf3cb0620f98ba",
    ),
    "preflight_manifest": (
        PREFLIGHT + "run-v5/MANIFEST.json",
        "750880875d60d3dc511904b0103cac1a5b9488b30256fbf86d56eafeeeacddaf",
    ),
    "preflight_report": (
        PREFLIGHT + "run-v5/REPORT.json",
        "9fa72cdde326926b5d4bf401cbdaed20f9b06f2e0028c406afe554a69dcc3d21",
    ),
    "preflight_review": (
        REVIEW + "REVIEW.json",
        "66a45ca163c97f0991eb9c77c920cf504608e8c86b9b4c27cc471db218585a4f",
    ),
    "registry_a": (
        BASE + "aq06-aq07-integrated-full-portfolio-bootstrap-run-v1/registry/A.json",
        "4b224115e511bedb67396aae35c51d976bc92032e96e1b15725a67bea3cc5656",
    ),
    "registry_b": (
        BASE + "aq06-aq07-integrated-full-portfolio-bootstrap-run-v1/registry/B.json",
        "3a0568317f962ec005d3ac030a9356935e12d1f14f798ce38639c77a1f873ef5",
    ),
    "procedures": (
        "enterprise/ccf/assurance/design_data/control_procedures.json",
        "258f5c868e16f3dc197594857dc86a4f2b3ef11e3e5a36dd0a80a9fc6d40c679",
    ),
    "catalog": (
        "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
        "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433",
    ),
}
FALLBACK_SEARCH_TARGETS = {
    "SH-ASS-003": "Independent assurance engagement and review record system",
    "SH-ETH-003": "Speak-up intake, independent triage and investigation case system",
    "SH-PPL-005": "Critical-role succession and capacity review system",
    "SH-PRD-002": "Customer commitment and nonstandard-term approval register",
    "SH-PRD-003": "Customer-impacting change and notice decision system",
    "SH-PRD-004": "Support issue, problem and corrective-action linkage system",
}
GENERIC_GATES = {
    "TOD": (
        "Test design against the stated control objective, boundary, owner, frequency, "
        "inputs, decision criteria, outputs and exception path."
    ),
    "IMPLEMENTATION": (
        "Locate deployed company-native configuration or decision records for the scoped "
        "service; reconcile owner and effective date to the population."
    ),
    "TOE": (
        "Define the complete selected-period population and sample, reperform execution "
        "and exceptions, and retain exact native provenance and availability clocks."
    ),
}
LIMIT = (
    "Candidate source search only. Documentary design leads and proposed systems of record "
    "do not establish period operation, applicability, sufficiency or task credit."
)


class MatrixError(ValueError):
    """A required source pin, identity, count or planning boundary differs."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_inputs(repository: Path, private_repository: Path) -> tuple[dict, dict]:
    values, pins = {}, {}
    for name, (relative, expected) in INPUTS.items():
        root = repository if name in {"procedures", "catalog"} else private_repository
        path = root / relative
        if not path.is_file() or path.is_symlink() or _sha(path) != expected:
            raise MatrixError(f"Pinned source missing or changed: {name}")
        pins[name] = {"path": str(path), "sha256": expected}
        values[name] = path.read_text() if name == "catalog" else json.loads(path.read_text())
    return values, pins


def _catalog(text: str) -> dict:
    rows = {}
    for line in text.splitlines():
        match = re.match(r"^\| (SH-[A-Z]+-\d+) \| ([^|]+) \| [^|]* \| ([^|]+) \|", line)
        if match:
            control, description, role = match.groups()
            if control in rows:
                raise MatrixError("Duplicate catalog control")
            rows[control] = {"description": description.strip(), "catalog_owner_role": role.strip()}
    return rows


def _unique(rows: list[dict], key: str) -> dict:
    indexed = {}
    for row in rows:
        identity = (row["side"], row[key])
        if identity in indexed:
            raise MatrixError(f"Duplicate {key}: {identity}")
        indexed[identity] = row
    return indexed


def assemble(
    data: dict, pins: dict, *, expected_controls: int = 43, expected_tasks: int = 283
) -> dict:
    """Join exact frozen routes to the current task clauses and registry diagnostic."""
    plan = data["plan_manifest"]
    review = data["plan_review"]
    preflight_manifest = data["preflight_manifest"]
    preflight_review = data["preflight_review"]
    report = data["preflight_report"]
    if (
        not str(review.get("status", "")).startswith("PASS_INDEPENDENT")
        or not str(preflight_review.get("verdict", "")).startswith("PASS")
        or preflight_manifest.get("source_complete") is not False
        or report.get("source_complete") is not False
        or plan["files"]["CONTROL-ROUTES.json"] != pins["control_routes"]["sha256"]
        or plan["files"]["TASK-ROUTES.json"] != pins["task_routes"]["sha256"]
    ):
        raise MatrixError("Frozen plan or baseline review gate differs")
    controls = _unique(data["control_routes"], "control_id")
    routes = _unique(data["task_routes"], "task_id")
    screen_old = _unique(data["screen_v2"]["rows"], "task_id")
    screen_now = _unique(data["screen_v3"]["rows"], "task_id")
    procedures = {row["control_id"]: row for row in data["procedures"]}
    catalog = _catalog(data["catalog"])
    sides = {}
    for side in "AB":
        registry = data[f"registry_{side.lower()}"]
        selected = set(registry["components"])
        if len(selected) != 13 or len(registry["profiles"]) != 1:
            raise MatrixError("Current registry is not the frozen 13-component profile")
        preflight_side = report["sides"][side]
        if set(preflight_side["selected_components"]) != selected:
            raise MatrixError("Preflight and current registry components differ")
        preflight_tasks = {row["task_id"]: row for row in preflight_side["tasks"]}
        preflight_controls = {row["control_id"]: row for row in preflight_side["controls"]}
        selected_controls = {
            cid: row
            for (s, cid), row in controls.items()
            if s == side and row["existing_native_route"] == "DOCUMENTARY_ONLY_IN_PINNED_PORTFOLIO"
        }
        selected_routes = {
            tid: row
            for (s, tid), row in routes.items()
            if s == side and row["control_id"] in selected_controls
        }
        if len(selected_controls) != expected_controls or len(selected_routes) != expected_tasks:
            raise MatrixError("Documentary/activity route count differs")
        if {tid for cid in selected_controls for tid in selected_controls[cid]["task_ids"]} != set(
            selected_routes
        ):
            raise MatrixError("Control/task route partition differs")
        families = {}
        for cid, control in sorted(selected_controls.items()):
            if cid not in catalog or cid not in preflight_controls:
                raise MatrixError("Catalog or preflight control missing")
            lead = procedures.get(cid)
            if lead:
                target = lead["proposed_system_of_record"]
                target_basis = "PROPOSED_CONTROL_PROCEDURE_DESIGN_NOT_DEPLOYED_SOURCE"
                reviewer = lead["reviewer_role_description"]
            elif cid in FALLBACK_SEARCH_TARGETS:
                target = FALLBACK_SEARCH_TARGETS[cid]
                target_basis = "CATALOG_DERIVED_SEARCH_HYPOTHESIS_NOT_DEPLOYED_SOURCE"
                reviewer = catalog[cid]["catalog_owner_role"]
            else:
                raise MatrixError("No candidate search target")
            diagnostic = preflight_controls[cid]
            documentary = diagnostic["candidate_components"]
            if (
                diagnostic["active_retained_control_components"]
                or not documentary
                or any(
                    x["classification"] != "DOCUMENTARY_DESIGN_ONLY"
                    or x["selected_in_proposed_registry"]
                    for x in documentary
                )
                or any(x["component_id"] in selected for x in documentary)
                or control["task_count"] != len(control["task_ids"])
                or control["task_credit"] is not False
            ):
                raise MatrixError("Documentary lead incorrectly treated as operation")
            tasks = []
            for tid in sorted(control["task_ids"]):
                route = selected_routes[tid]
                old, current = screen_old.get((side, tid)), screen_now.get((side, tid))
                preflight = preflight_tasks.get(tid)
                if (
                    old is None
                    or current is None
                    or preflight is None
                    or old["test_clause"] != current["test_clause"]
                    or route["control_id"] != cid
                    or route["procedure_type"] != current["procedure_type"]
                    or current["current_status"] != "NOT_STARTED"
                    or current["current_conclusion"] != "NOT_RUN"
                    or preflight["current_status"] != "NOT_STARTED"
                    or preflight["current_conclusion"] != "NOT_RUN"
                    or preflight["task_credit"] is not False
                    or "DOCUMENTARY_DESIGN_ONLY_DISCOVER_OR_PERFORM_NATIVE_PERIOD_ACTIVITY"
                    not in preflight["flags"]
                    or preflight["selected_candidate_component_ids"]
                ):
                    raise MatrixError(
                        f"Task clause, identity or no-credit gate differs: {side}/{tid}"
                    )
                clause = current["test_clause"]
                tasks.append(
                    {
                        "task_id": tid,
                        "procedure_type": route["procedure_type"],
                        "requirement_ids": route["requirement_ids"],
                        "authored_test_clause": clause,
                        "remaining_test_gate": clause
                        or GENERIC_GATES.get(
                            route["procedure_type"],
                            "Reperform the exact authored procedure with scoped native records "
                            "and qualified review.",
                        ),
                        "test_gate_basis": "AUTHORED_TASK_CLAUSE"
                        if clause
                        else "GENERIC_PROCEDURE_GATE_NOT_AN_AUTHORED_CLAUSE",
                        "missing_period_activity": control["period_and_clause_gap"],
                        "next_action": route["next_action"],
                        "current_status": "NOT_STARTED",
                        "current_conclusion": "NOT_RUN",
                        "task_credit": False,
                    }
                )
            group = {
                "control_id": cid,
                "control_description": catalog[cid]["description"],
                "family": control["family"],
                "priority": control["priority"],
                "frequency": control["frequency"],
                "frameworks": control["frameworks"],
                "candidate_native_source_search_target": target,
                "candidate_basis": target_basis,
                "documentary_design_leads_outside_current_registry": documentary,
                "selected_registry_native_component": None,
                "owner_ids_proposed": control["owner_ids"],
                "owner_assignment_status": control["owner_assignment_status"],
                "separate_reviewer_role": reviewer,
                "authority_gate": (
                    "ACCEPTED_SCOPE_OWNER_AND_QUALIFIED_APPLICABILITY_REVIEW_REQUIRED"
                ),
                "missing_period_activity": control["period_and_clause_gap"],
                "tasks": tasks,
            }
            families.setdefault(control["family"], []).append(group)
        sides[side] = {
            "registry_profile_id": next(iter(registry["profiles"])),
            "registry_components": sorted(selected),
            "families": [
                {"family": family, "controls": sorted(groups, key=lambda x: x["control_id"])}
                for family, groups in sorted(families.items())
            ],
        }
    if {
        (g["control_id"], t["task_id"])
        for f in sides["A"]["families"]
        for g in f["controls"]
        for t in g["tasks"]
    } != {
        (g["control_id"], t["task_id"])
        for f in sides["B"]["families"]
        for g in f["controls"]
        for t in g["tasks"]
    }:
        raise MatrixError("A/B documentary route identities differ")
    return {
        "schema": SCHEMA,
        "status": "READ_ONLY_DISCOVERY_PLAN_NO_SOURCE_OR_AUDIT_CREDIT",
        "as_of": "2026-09-29",
        "selected_period": ["2027-01-01", "2027-12-31"],
        "future_event_clock_limit": (
            "2027 period is authored future simulation as of the as_of date; "
            "no historical Type 2 assertion."
        ),
        "source_pins": pins,
        "counts": {
            "controls_per_side": expected_controls,
            "tasks_per_side": expected_tasks,
            "total_task_routes": expected_tasks * 2,
            "fallback_search_targets_per_side": len(FALLBACK_SEARCH_TARGETS),
        },
        "limits": LIMIT,
        "sides": sides,
    }


def _plan(matrix: dict) -> str:
    first = matrix["sides"]["A"]["families"]
    lines = [
        "# Documentary and activity discovery routes",
        "",
        (
            "**State:** source-pinned planning candidate only. The frozen unmatched373 V2 "
            "routes identify 283 tasks across 43 controls per branch for further discovery. "
            "The current 13-component registry has no selected native operating source for "
            "these routes; documentary components are design leads outside that binding. "
            "No task or source was changed."
        ),
        "",
        "| Family | Controls per branch | Tasks per branch |",
        "|---|---:|---:|",
    ]
    for family in first:
        task_count = sum(len(control["tasks"]) for control in family["controls"])
        lines.append(f"| {family['family']} | {len(family['controls'])} | {task_count} |")
    lines += [
        "",
        (
            "For each control, `MATRIX.json` names a proposed native system to search, "
            "the documentary lead already seen, the missing 2027 activity, proposed "
            "owners and separate reviewer role, and every task's unchanged clause. A "
            "missing authored clause is explicitly `null`; its generic procedure gate "
            "is an inference for planning, not replacement audit language. The six "
            "catalog-derived targets have a distinct candidate basis."
        ),
        "",
        (
            "Discover actual or properly simulated company-native period records, or "
            "document authorized nonoccurrence. First resolve service scope and legal "
            "applicability where relevant, then source-owner authority, complete populations, "
            "event/availability/import clocks, exceptions, ordinary collection and clause-level "
            "testing. Document versions alone do not establish implementation or operation. "
            "The 2027 period remains future-authored as of September 29, 2026."
        ),
        "",
        (
            "The 44/287 documentary portfolio count includes four SEC006 tasks with a "
            "separate bounded local native route; this matrix intentionally contains the "
            "remaining 43/283 discovery partition. `SH-POL-003` remains generic exception "
            "governance; the separate 22-item addressable docket is only a prospective pending "
            "source and cannot silently satisfy its clauses. New sources require a fresh "
            "source-complete registry and zero-evidence engagement, not expansion of the "
            "active pair."
        ),
        "",
        (
            "**Gate:** independent route review, accepted owner/legal facts where required, "
            "fresh ordinary native collection and qualified procedure conclusions. No source "
            "generation, P1 mutation, workpaper, Key, grade, deployment, real PHI/BA status "
            "or audit credit follows from this matrix."
        ),
        "",
    ]
    return "\n".join(lines)


def _write(path: Path, value: str) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Write only a new private plan directory; all inputs are read-only."""
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or destination.is_symlink()
        or destination != destination.resolve()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
    ):
        raise MatrixError("New private destination required")
    data, pins = _read_inputs(Path(repository), Path(private_repository))
    matrix = assemble(data, pins)
    plan = _plan(matrix)
    destination.mkdir(mode=0o700)
    try:
        _write(
            destination / "MATRIX.json",
            json.dumps(matrix, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        )
        _write(destination / "PLAN.md", plan)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "status": matrix["status"],
            "counts": matrix["counts"],
            "source_pins": pins,
            "matrix_sha256": _sha(destination / "MATRIX.json"),
            "plan_sha256": _sha(destination / "PLAN.md"),
            "module_sha256": _sha(Path(__file__)),
            "source_generation": False,
            "active_audit_mutation": False,
            "task_credit": False,
        }
        _write(destination / "MANIFEST.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    except BaseException:
        # Preserve a failed partial private attempt for diagnosis.
        raise
    return manifest


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Reperform exact source joins and compare sealed output bytes."""
    destination = Path(destination).absolute()
    if not destination.is_dir() or destination.is_symlink() or destination.stat().st_mode & 0o077:
        raise MatrixError("Private plan directory required")
    for name in ("MATRIX.json", "PLAN.md", "MANIFEST.json"):
        path = destination / name
        if not path.is_file() or path.is_symlink() or path.stat().st_mode & 0o077:
            raise MatrixError("Private plan file required")
    data, pins = _read_inputs(Path(repository), Path(private_repository))
    matrix = assemble(data, pins)
    plan = _plan(matrix)
    if (destination / "MATRIX.json").read_text() != json.dumps(
        matrix, indent=2, sort_keys=True, ensure_ascii=False
    ) + "\n" or (destination / "PLAN.md").read_text() != plan:
        raise MatrixError("Source route plan output differs")
    manifest = json.loads((destination / "MANIFEST.json").read_text())
    if (
        manifest["schema"] != SCHEMA + "_MANIFEST"
        or manifest["counts"] != matrix["counts"]
        or manifest["source_pins"] != pins
        or manifest["matrix_sha256"] != _sha(destination / "MATRIX.json")
        or manifest["plan_sha256"] != _sha(destination / "PLAN.md")
        or manifest["module_sha256"] != _sha(Path(__file__))
        or manifest["source_generation"] is not False
        or manifest["active_audit_mutation"] is not False
        or manifest["task_credit"] is not False
    ):
        raise MatrixError("Source route plan manifest differs")
    return manifest
