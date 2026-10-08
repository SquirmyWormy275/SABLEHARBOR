"""Add one reviewed POL004 procedure-trial lead to the exact unsupported CC5.3 route."""

from __future__ import annotations

import hashlib
import json
import stat
from copy import deepcopy
from pathlib import Path

from . import company_pol004_procedure_trace_2027 as procedure
from . import documentary_283_route_reconciliation_v11 as prior
from .documentary_283_route_reconciliation_v6 import _p1_inventory

SCHEMA = "SH_DOCUMENTARY_283_PAIRED_ROUTE_CANDIDATE_RECONCILIATION_V12"
BASE = "enterprise/generated/audit-suite"
TASK = procedure.TASK
CLAUSE = procedure.CLAUSE
SOURCE = "POL004_SELECTED_PROCEDURE_TRACE_V1"
LIMIT = (
    "One selected fictional local due-time procedure trial only. The enterprise policy "
    "remains OPEN, the corporate document standard is approved design only, and procedure "
    "authority awaits an authorized decision. Clean has one selected on-time result; Messy "
    "retains the missed due interval, rejected false close, later correction and OPEN "
    "exception. No full-period policy/procedure population, effective enterprise procedure, "
    "actual operation or independent audit conclusion follows. CC5.3 remains unsupported."
)
V11_LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V11_2026-09-30.json"
V11_REVIEW = (
    f"{BASE}/documentary-283-route-reconciliation-v11-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
POL_ROOT = f"{BASE}/company-pol004-procedure-trace-2027-09-30"
POL_RUN = f"{POL_ROOT}/main-run-v1"
POL_REVIEW = f"{POL_ROOT}/independent-review-main-v1/REVIEW.json"
PINS = {
    "v11_ledger": {
        "scope": "repo",
        "path": V11_LEDGER,
        "sha256": "41facc0f48c2f0fc4b9144366bb239131e54c1693fde2bcbfa9ded7360792299",
    },
    "v11_review": {
        "scope": "private",
        "path": V11_REVIEW,
        "sha256": "5db6205b1afcbd578562345a7ff0af6a212b8cbf1c39139cb71a22590fd394a2",
    },
    "pol_review": {
        "scope": "private",
        "path": POL_REVIEW,
        "sha256": "2c0e96babf915c42d7d056de9ec87c30bc8966ddab126343ec444a1bad715143",
    },
    "pol_manifest": {
        "scope": "private",
        "path": f"{POL_RUN}/RUN-MANIFEST.json",
        "sha256": "2d81554213354d8dc76d167fcc624bb1fb98b7ee5c44c0a75d4990ddf8e4f266",
    },
    "pol_receipt": {
        "scope": "private",
        "path": f"{POL_RUN}/SOURCE_RECEIPT.json",
        "sha256": "442ddf2a36185460df20b04e00d63f12f877a3ef751f5f55cd9858fb9502af54",
    },
    "pol_db": {
        "scope": "private",
        "path": f"{POL_RUN}/company.sqlite3",
        "sha256": "62c71eca6b9186936e89c6569735a6ea74b8d4909d356d2fb794a9e437d2d4bb",
    },
    "pol_module": {
        "scope": "repo",
        "path": "enterprise/audit_suite/company_pol004_procedure_trace_2027.py",
        "sha256": "c418e73f5ce67398237a50814bca8ee48a0295f746b31dd2ab823828a8083a8e",
    },
}
P1_FREEZE = prior.P1_FREEZE
IDENTITY = (
    "branch",
    "system",
    "record",
    "version",
    "sha256",
    "event_at",
    "available_at",
    "imported_at",
)


class V12ReconciliationError(prior.V11ReconciliationError):
    """A reviewed route, native original, or no-credit boundary changed."""


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pin(repository: Path, private: Path, entry: dict) -> Path:
    path = (repository if entry["scope"] == "repo" else private) / entry["path"]
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise V12ReconciliationError("Pinned input alias forbidden")
    before = path.lstat()
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or (entry["scope"] == "private" and stat.S_IMODE(before.st_mode) != 0o600)
        or _digest(path) != entry["sha256"]
    ):
        raise V12ReconciliationError(f"Reviewed input byte or mode differs: {entry['path']}")
    after = path.lstat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ) or _digest(path) != entry["sha256"]:
        raise V12ReconciliationError("Pinned input changed during read")
    return path


def _selected_refs(receipt: dict, previous: dict) -> dict[str, list[dict]]:
    """Bind the complete selected Clean/Messy original chains to the authored clause."""
    if (
        receipt.get("schema") != procedure.SCHEMA
        or receipt.get("control_id") != procedure.CONTROL
        or receipt.get("task_id") != TASK
        or receipt.get("selected_authored_clause") != CLAUSE
        or receipt.get("branch_ids") != procedure.BRANCHES
        or receipt.get("branch_counts") != {"CLEAN": 7, "MESSY": 9}
        or receipt.get("native_count") != 16
        or receipt.get("enterprise_policy_status_2026") != "OPEN"
        or receipt.get("design_standard_approved_only") is not True
        or receipt.get("procedure_authority") != "PENDING_AUTHORIZED_DECISION"
        or receipt.get("messy_missed_interval_retained") is not True
        or receipt.get("messy_false_close_corrected") is not True
        or receipt.get("messy_exception_open") is not True
        or any(
            receipt.get(key) is not False
            for key in (
                "full_policy_or_procedure_population",
                "actual_operation",
                "source_complete",
                "audit_task_credit",
                "active_P1_mutated",
            )
        )
    ):
        raise V12ReconciliationError("Selected POL004 authority or scope differs")
    originals = receipt.get("native_originals", [])
    if len(originals) != 16:
        raise V12ReconciliationError("Selected POL004 native original denominator differs")
    selected = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        old = next(
            row for row in previous["rows"] if row["side"] == side and row["task_id"] == TASK
        )
        disposition = receipt["route_disposition"][side]
        if (
            disposition.get("task_id") != TASK
            or disposition.get("screen_row_sha256") != old["screen_row_sha256"]
            or disposition.get("authored_test_clause") != CLAUSE
            or disposition.get("classification") != "UNSUPPORTED_EXACT_CLAUSE"
            or disposition.get("current_status") != "NOT_STARTED"
            or disposition.get("current_conclusion") != "NOT_RUN"
            or disposition.get("audit_task_credit") is not False
        ):
            raise V12ReconciliationError("Selected POL004 route disposition differs")
        rows = [row for row in originals if row["branch"] == procedure.BRANCHES[scenario]]
        expected = [(system, record) for system, record, _, _ in procedure.PLAN[scenario]]
        if (
            len(rows) != len(expected)
            or [(row["system"], row["record"]) for row in rows] != expected
            or any(row["version"] != 1 or any(not row.get(key) for key in IDENTITY) for row in rows)
        ):
            raise V12ReconciliationError("Selected POL004 native roster or clocks differ")
        selected[side] = [{key: row[key] for key in IDENTITY} for row in rows]
    return selected


def _extend(previous: dict, receipt: dict, freeze: dict) -> dict:
    """Keep every V11 row field; add one reviewed CC5.3 source lead per side."""
    if (
        previous.get("schema") != prior.SCHEMA
        or previous.get("p1_freeze") != freeze
        or previous.get("audit_task_credit") is not False
        or previous.get("active_pair_mutated") is not False
        or len(previous.get("rows", [])) != 566
        or previous["counts"]["A"] != previous["counts"]["B"]
        or previous["counts"]["A"]["classifications"]
        != {
            "DESIGN_CONTEXT_ONLY": 27,
            "SOURCE_CANDIDATE_PARTIAL": 135,
            "UNSUPPORTED_EXACT_CLAUSE": 121,
        }
        or previous["counts"]["A"]["targeted_integrated_route_count"] != 174
        or previous["active_p1_tasks"]
        != {
            side: {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"}
            for side in "AB"
        }
    ):
        raise V12ReconciliationError("Reviewed V11 prefix or P1 boundary differs")
    refs = _selected_refs(receipt, previous)
    rows = []
    for old in previous["rows"]:
        selected = old["task_id"] == TASK
        row = dict(old)
        if selected:
            if (
                old["control_id"] != procedure.CONTROL
                or old["classification"] != "UNSUPPORTED_EXACT_CLAUSE"
                or old["test_gate_basis"] != "AUTHORED_TASK_CLAUSE"
                or old["authored_test_clause"] != CLAUSE
                or old["remaining_test_gate"] != CLAUSE
                or old["candidate_or_design_source_ids"]
                or old["targeted_integrated_source_ids"]
                or old["current_status"] != "NOT_STARTED"
                or old["current_conclusion"] != "NOT_RUN"
                or old["audit_task_credit"] is not False
            ):
                raise V12ReconciliationError("Exact authored POL004 CC5.3 boundary differs")
            row["targeted_integrated_source_ids"] = [SOURCE]
        row["v12_reviewed_source_ids"] = [SOURCE] if selected else []
        row["v12_source_limits"] = {SOURCE: LIMIT} if selected else {}
        row["v12_source_record_refs"] = {SOURCE: refs[old["side"]]} if selected else {}
        if any(
            row[key] != value
            for key, value in old.items()
            if key != "targeted_integrated_source_ids" or not selected
        ):
            raise V12ReconciliationError("V11 row field changed")
        rows.append(row)
    counts = {}
    for side in "AB":
        subset = [row for row in rows if row["side"] == side]
        selected = [row for row in subset if row["v12_reviewed_source_ids"]]
        targeted = sum(bool(row["targeted_integrated_source_ids"]) for row in subset)
        if (
            len(subset) != len({row["task_id"] for row in subset})
            or len(subset) != 283
            or len(selected) != 1
            or selected[0]["task_id"] != TASK
            or selected[0]["classification"] != "UNSUPPORTED_EXACT_CLAUSE"
            or selected[0]["remaining_test_gate"] != CLAUSE
            or targeted != 175
            or sum(row["authored_test_clause"] is not None for row in subset) != 154
            or any(
                row["current_status"] != "NOT_STARTED"
                or row["current_conclusion"] != "NOT_RUN"
                or row["audit_task_credit"] is not False
                for row in subset
            )
        ):
            raise V12ReconciliationError("Exact POL004 one-lead route denominator differs")
        counts[side] = {
            **deepcopy(previous["counts"][side]),
            "targeted_integrated_route_count": targeted,
            "v12_new_selected_pol004_authored_leads": 1,
            "v12_new_generic_promotions": 0,
        }
    if counts["A"] != counts["B"]:
        raise V12ReconciliationError("Paired POL004 route counts differ")
    pins = {**previous["source_pins"], **PINS}
    return {
        "schema": SCHEMA,
        "as_of": "2026-09-30",
        "v11_prefix_sha256": PINS["v11_ledger"]["sha256"],
        "source_pins": pins,
        "source_pins_sha256": hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest(),
        "p1_freeze": freeze,
        "active_p1_tasks": previous["active_p1_tasks"],
        "reviewed_source_roster": {
            **previous["reviewed_source_roster"],
            "additional_selected_pol004_cohort_versions": 16,
        },
        "counts": counts,
        "rows": rows,
        "limits": [
            "Only the exact SH-POL-004 SOC2:CC5.3 authored route per side gains one "
            "selected fictional source lead; every prior V11 row field persists.",
            LIMIT,
            "All 121 unsupported authored clauses per side remain unsupported; no generic "
            "route is promoted.",
            "No source completeness, audit task credit, fresh pair, Key, grade or Atlas write.",
        ],
        "audit_task_credit": False,
        "active_pair_mutated": False,
    }


def build(repository: Path, private_repository: Path) -> dict:
    """Reperform the reviewed V11 route and selected POL004 native source."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    freeze = _p1_inventory(private)
    if freeze != P1_FREEZE:
        raise V12ReconciliationError("Frozen P1 inventory differs")
    paths = {name: _pin(repository, private, entry) for name, entry in PINS.items()}
    previous = prior.build(repository, private)
    if previous != json.loads(paths["v11_ledger"].read_text()):
        raise V12ReconciliationError("Reviewed V11 route replay differs")
    route_review = json.loads(paths["v11_review"].read_text())
    if (
        route_review.get("verdict")
        != "PASS_SELECTED_SEC001_CC67_ROUTE_V11_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or route_review.get("main_tracked_sha256", {}).get(V11_LEDGER)
        != PINS["v11_ledger"]["sha256"]
        or route_review.get("main_output_sha256", {}).get("LEDGER.json")
        != PINS["v11_ledger"]["sha256"]
        or route_review.get("p1_freeze") != freeze
        or route_review.get("audit_task_credit") is not False
        or route_review.get("active_pair_mutated") is not False
    ):
        raise V12ReconciliationError("V11 independent review join differs")
    review = json.loads(paths["pol_review"].read_text())
    manifest = json.loads(paths["pol_manifest"].read_text())
    source_hashes = {
        name: PINS[key]["sha256"]
        for name, key in (
            ("RUN-MANIFEST.json", "pol_manifest"),
            ("SOURCE_RECEIPT.json", "pol_receipt"),
            ("company.sqlite3", "pol_db"),
        )
    }
    if (
        review.get("verdict") != "PASS_SELECTED_POL004_PROCEDURE_TRACE_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or review.get("integration_commits_in_order")
        != [
            "83c2f3ea37aa63b3a1904cd10f74b724e207b7c6",
            "c92d43e0346921e31889baf4dfbea55ade09a765",
        ]
        or review.get("main_run_sha256") != source_hashes
        or review.get("main_tracked_sha256", {}).get(PINS["pol_module"]["path"])
        != PINS["pol_module"]["sha256"]
        or review.get("p1_freeze") != freeze
        or review.get("source_complete") is not False
        or review.get("audit_task_credit") is not False
        or review.get("active_pair_mutated") is not False
        or review.get("fresh_pair_created") is not False
        or review.get("main_or_atlas_external_write") is not False
        or manifest.get("native_count") != 16
        or manifest.get("source_receipt_sha256") != PINS["pol_receipt"]["sha256"]
        or manifest.get("native_db_sha256") != PINS["pol_db"]["sha256"]
        or manifest.get("module_sha256") != PINS["pol_module"]["sha256"]
    ):
        raise V12ReconciliationError("POL004 independent review/source join differs")
    receipt = procedure.verify(private / POL_RUN, repository=repository, private_repository=private)
    if receipt != json.loads(paths["pol_receipt"].read_text()):
        raise V12ReconciliationError("Reviewed POL004 native replay differs")
    result = _extend(previous, receipt, freeze)
    if _p1_inventory(private) != freeze or any(
        _digest(path) != PINS[name]["sha256"] for name, path in paths.items()
    ):
        raise V12ReconciliationError("Pinned input or P1 changed during route build")
    return result


def markdown(result: dict) -> str:
    """Describe the selected lead and the still-open authored CC5.3 gate."""
    count = result["counts"]["A"]
    lines = [
        "# Paired 283-route POL004 procedure-trace reconciliation V12",
        "",
        "The exact 566-row JSON retains every V11 row field. Only SH-POL-004 "
        "SOC2:CC5.3 per side gains a bounded native lead from a reviewed 16-version "
        "fictional local due-time procedure trial.",
        "",
        "| Classification | Routes per side |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {name} | {number} |" for name, number in count["classifications"].items())
    lines += [
        "",
        "Clean records one selected on-time result. Messy retains a missed due interval, "
        "rejected false close, later correction and OPEN exception. The enterprise policy "
        "remains OPEN; the corporate document standard is design only, and procedure "
        "approval is pending. There is no full-period population or actual operation.",
        "",
        "CC5.3 and all 121 authored unsupported clauses per side remain "
        "UNSUPPORTED_EXACT_CLAUSE with their authored gates open. No generic route "
        "promotion occurred. Named targeted leads total "
        f"{count['targeted_integrated_route_count']} "
        "distinct routes per side.",
        "",
        "No audit task credit, fresh pair, Key, grade or Atlas write was issued. The frozen "
        "A/B P1 tasks remain 409 NOT_STARTED/NOT_RUN.",
        "",
    ]
    return "\n".join(lines)
