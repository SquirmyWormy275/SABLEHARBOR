"""Add one reviewed emergency-replay lead to the exact unsupported IAM005 route."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from . import company_emergency_replay_2027 as replay
from . import documentary_283_route_reconciliation_v12 as prior
from .documentary_283_route_reconciliation_v6 import _p1_inventory

SCHEMA = "SH_DOCUMENTARY_283_PAIRED_ROUTE_CANDIDATE_RECONCILIATION_V13"
BASE = "enterprise/generated/audit-suite"
TASK = "TASK-SH-IAM-005-corporate-ACTION-H-EMERGENCY"
CONTROL = "SH-IAM-005"
CLAUSE = (
    "Observe an approved emergency-mode exercise; verify necessary ePHI remains accessible "
    "to authorized operators and access decisions and activity survive recovery."
)
SOURCE = "EMERGENCY_REPLAY_SELECTED_V1"
LIMIT = (
    "One future-authored, payload-free fictional Boise marker and selected local replay path. "
    "Clean has a bounded local hash match; Messy retains a denied preauthorization fast path, "
    "stale-checkpoint mismatch, later local retest and OPEN historical/upstream exceptions. "
    "No actual ePHI access, deployed replay, transmission, complete population, independent "
    "assurance or full-period operation. The authored IAM005 emergency clause remains unsupported."
)
V12_LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V12_2026-09-30.json"
V12_REVIEW = (
    f"{BASE}/documentary-283-route-reconciliation-v12-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
REPLAY_ROOT = f"{BASE}/company-emergency-replay-2026-09-30"
REPLAY_RUN = f"{REPLAY_ROOT}/main-run-v1"
REPLAY_REVIEW = f"{REPLAY_ROOT}/independent-review-main-v1/REVIEW.json"
PINS = {
    "v12_ledger": {
        "scope": "repo",
        "path": V12_LEDGER,
        "sha256": "4eee560f86aedef7dad15d172828cb652ee1be5318e4a473947adde8167a69b5",
    },
    "v12_review": {
        "scope": "private",
        "path": V12_REVIEW,
        "sha256": "4769b515bed5861407c9aaacbe6b9b3eccf2dee2f279077f2d3d6f13a6973fa3",
    },
    "replay_review": {
        "scope": "private",
        "path": REPLAY_REVIEW,
        "sha256": "2fd0f0d2f72f592c929dc1ae01d1c895a1c90cbdd6ebca776813f796cf4b0a36",
    },
    "replay_manifest": {
        "scope": "private",
        "path": f"{REPLAY_RUN}/MANIFEST.json",
        "sha256": "8552fbfe0ebd8487b7bda55e9577cf11b2f45bfa2835d6459cf3265aa3b3455b",
    },
    "replay_receipt": {
        "scope": "private",
        "path": f"{REPLAY_RUN}/RECEIPT.json",
        "sha256": "ffe8ee5f874a2581e9502c1b9cca9992fbf4602437ecede9005b50d098762e9c",
    },
    "replay_db": {
        "scope": "private",
        "path": f"{REPLAY_RUN}/company.sqlite3",
        "sha256": "39dc7d18f22d064a007b42a3ce1f33391cb34aea226eaac9604915e8a73c259b",
    },
    "replay_module": {
        "scope": "repo",
        "path": "enterprise/audit_suite/company_emergency_replay_2027.py",
        "sha256": "991e10163322cff32ebe957b5d0b5101e1a9079925393d9c6a7b78a353a5deb9",
    },
    "replay_spec": {
        "scope": "repo",
        "path": "enterprise/audit_suite/emergency_replay_2027_spec_v1.json",
        "sha256": "16f53c1e1244643e78c1cfcff21aee830bb9254756625a28611987a35a11faf5",
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


class V13ReconciliationError(prior.V12ReconciliationError):
    """A reviewed route, native original or no-credit boundary changed."""


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _selected_refs(receipt: dict, previous: dict) -> dict[str, list[dict]]:
    if (
        receipt.get("schema") != replay.SCHEMA
        or receipt.get("branches") != replay.BRANCHES
        or receipt.get("native_version_counts") != {"CLEAN": 8, "MESSY": 15}
        or receipt.get("selected_population_count") != 1
        or receipt.get("local_open_exception_counts") != {"CLEAN": 0, "MESSY": 1}
        or receipt.get("messy_upstream_gates_remain_open") is not True
        or receipt.get("external_bytes_or_packets") != 0
        or any(
            receipt.get(key) is not False
            for key in (
                "actual_phi_processing",
                "deployed_recovery_proven",
                "source_complete",
                "audit_task_credit",
            )
        )
    ):
        raise V13ReconciliationError("Selected replay scope or open exceptions differ")
    selected = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        rows = receipt.get("records", {}).get(scenario, [])
        expected = [(system, record) for _, system, record, _, _, _ in replay._plan(scenario)]
        if (
            not isinstance(rows, list)
            or len(rows) != len(expected)
            or [(row.get("system"), row.get("record")) for row in rows] != expected
            or any(
                row.get("branch") != replay.BRANCHES[scenario]
                or row.get("version") != 1
                or any(not row.get(key) for key in IDENTITY)
                for row in rows
            )
        ):
            raise V13ReconciliationError("Selected replay native roster or clocks differ")
        old = next(
            row for row in previous["rows"] if row["side"] == side and row["task_id"] == TASK
        )
        if (
            old["control_id"] != CONTROL
            or old["classification"] != "UNSUPPORTED_EXACT_CLAUSE"
            or old["test_gate_basis"] != "AUTHORED_TASK_CLAUSE"
            or old["authored_test_clause"] != CLAUSE
            or old["remaining_test_gate"] != CLAUSE
            or old["candidate_or_design_source_ids"]
            or old["targeted_integrated_source_ids"]
            != ["IAM005_EMERGENCY_MARKER_V1", "IAM005_LOCAL_V1"]
            or old["current_status"] != "NOT_STARTED"
            or old["current_conclusion"] != "NOT_RUN"
            or old["audit_task_credit"] is not False
        ):
            raise V13ReconciliationError("Exact unsupported IAM005 emergency clause differs")
        selected[side] = [{key: row[key] for key in IDENTITY} for row in rows]
    return selected


def _extend(previous: dict, receipt: dict, freeze: dict) -> dict:
    """Retain every V12 row field except one selected targeted source-ID append."""
    if (
        previous.get("schema") != prior.SCHEMA
        or previous.get("p1_freeze") != freeze
        or previous.get("audit_task_credit") is not False
        or previous.get("active_pair_mutated") is not False
        or len(previous.get("rows", [])) != 566
        or previous.get("active_p1_tasks")
        != {
            side: {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"}
            for side in "AB"
        }
        or any(
            previous["counts"][side]["targeted_integrated_route_count"] != 175
            or previous["counts"][side]["classifications"]
            != {
                "DESIGN_CONTEXT_ONLY": 27,
                "SOURCE_CANDIDATE_PARTIAL": 135,
                "UNSUPPORTED_EXACT_CLAUSE": 121,
            }
            for side in "AB"
        )
    ):
        raise V13ReconciliationError("Reviewed V12 prefix or P1 boundary differs")
    refs = _selected_refs(receipt, previous)
    rows = []
    for old in previous["rows"]:
        selected = old["task_id"] == TASK
        row = deepcopy(old)
        if selected:
            row["targeted_integrated_source_ids"].append(SOURCE)
        row["v13_reviewed_source_ids"] = [SOURCE] if selected else []
        row["v13_source_limits"] = {SOURCE: LIMIT} if selected else {}
        row["v13_source_record_refs"] = {SOURCE: refs[old["side"]]} if selected else {}
        if any(
            row[key] != value
            for key, value in old.items()
            if key != "targeted_integrated_source_ids" or not selected
        ):
            raise V13ReconciliationError("V12 row field changed")
        rows.append(row)
    counts = {}
    for side in "AB":
        subset = [row for row in rows if row["side"] == side]
        selected = [row for row in subset if row["v13_reviewed_source_ids"]]
        targeted = sum(bool(row["targeted_integrated_source_ids"]) for row in subset)
        if (
            len(subset) != len({row["task_id"] for row in subset})
            or len(subset) != 283
            or len(selected) != 1
            or selected[0]["task_id"] != TASK
            or selected[0]["classification"] != "UNSUPPORTED_EXACT_CLAUSE"
            or selected[0]["remaining_test_gate"] != CLAUSE
            or targeted != 175
            or any(
                row["current_status"] != "NOT_STARTED"
                or row["current_conclusion"] != "NOT_RUN"
                or row["audit_task_credit"] is not False
                for row in subset
            )
        ):
            raise V13ReconciliationError("Exact one-lead IAM005 denominator differs")
        counts[side] = {
            **deepcopy(previous["counts"][side]),
            "v13_new_selected_emergency_replay_authored_leads": 1,
            "v13_new_distinct_targeted_routes": 0,
            "v13_new_generic_promotions": 0,
        }
    if counts["A"] != counts["B"]:
        raise V13ReconciliationError("Paired emergency route counts differ")
    pins = {**previous["source_pins"], **PINS}
    return {
        **previous,
        "schema": SCHEMA,
        "v12_prefix_sha256": PINS["v12_ledger"]["sha256"],
        "source_pins": pins,
        "source_pins_sha256": hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest(),
        "reviewed_source_roster": {
            **previous["reviewed_source_roster"],
            "additional_selected_emergency_replay_cohort_versions": 23,
        },
        "counts": counts,
        "rows": rows,
        "limits": [
            *previous["limits"],
            "Only the exact SH-IAM-005 emergency-mode authored route per side gains one "
            "selected fictional source lead. It was already targeted; distinct targeted "
            "route count remains 175 per side.",
            LIMIT,
            "All 121 unsupported exact clauses remain unsupported; P1 retains 409 "
            "NOT_STARTED/NOT_RUN tasks per side. No fresh pair, Key, grade or Atlas write.",
        ],
        "audit_task_credit": False,
        "active_pair_mutated": False,
    }


def build(repository: Path, private_repository: Path) -> dict:
    """Reperform V12 and exact reviewed emergency native source before routing."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    freeze = _p1_inventory(private)
    if freeze != P1_FREEZE:
        raise V13ReconciliationError("Frozen P1 inventory differs")
    paths = {name: prior._pin(repository, private, entry) for name, entry in PINS.items()}
    previous = prior.build(repository, private)
    if previous != json.loads(paths["v12_ledger"].read_text()):
        raise V13ReconciliationError("Reviewed V12 route replay differs")
    route_review = json.loads(paths["v12_review"].read_text())
    if (
        route_review.get("verdict")
        != "PASS_SELECTED_POL004_CC53_ROUTE_V12_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or route_review.get("main_tracked_sha256", {}).get(V12_LEDGER)
        != PINS["v12_ledger"]["sha256"]
        or route_review.get("main_output_sha256", {}).get("LEDGER.json")
        != PINS["v12_ledger"]["sha256"]
        or route_review.get("p1_freeze") != freeze
        or route_review.get("source_complete") is not False
        or route_review.get("audit_task_credit") is not False
        or route_review.get("active_pair_mutated") is not False
        or route_review.get("fresh_pair_created") is not False
        or route_review.get("main_or_atlas_external_write") is not False
    ):
        raise V13ReconciliationError("V12 independent review join differs")
    review = json.loads(paths["replay_review"].read_text())
    manifest = json.loads(paths["replay_manifest"].read_text())
    source_hashes = {
        name: PINS[key]["sha256"]
        for name, key in (
            ("MANIFEST.json", "replay_manifest"),
            ("RECEIPT.json", "replay_receipt"),
            ("company.sqlite3", "replay_db"),
        )
    }
    if (
        review.get("verdict") != "PASS_SELECTED_EMERGENCY_REPLAY_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or review.get("main_run_sha256") != source_hashes
        or review.get("main_tracked_sha256", {}).get(PINS["replay_module"]["path"])
        != PINS["replay_module"]["sha256"]
        or review.get("main_tracked_sha256", {}).get(PINS["replay_spec"]["path"])
        != PINS["replay_spec"]["sha256"]
        or review.get("p1_freeze") != freeze
        or review.get("source_complete") is not False
        or review.get("fresh_pair_eligible") is not False
        or review.get("audit_task_credit") is not False
        or review.get("active_pair_mutated") is not False
        or review.get("main_or_atlas_external_write") is not False
        or manifest.get("native_version_count") != 23
        or manifest.get("receipt_sha256") != PINS["replay_receipt"]["sha256"]
        or manifest.get("db_sha256") != PINS["replay_db"]["sha256"]
        or manifest.get("module_sha256") != PINS["replay_module"]["sha256"]
        or manifest.get("audit_task_credit") is not False
    ):
        raise V13ReconciliationError("Emergency independent review/source join differs")
    replay.verify(private / REPLAY_RUN, repository=repository, private_repository=private)
    receipt = json.loads(paths["replay_receipt"].read_text())
    result = _extend(previous, receipt, freeze)
    if _p1_inventory(private) != freeze or any(
        _digest(path) != PINS[name]["sha256"] for name, path in paths.items()
    ):
        raise V13ReconciliationError("Pinned input or P1 changed during route build")
    return result


def markdown(result: dict) -> str:
    count = result["counts"]["A"]
    lines = [
        "# Paired 283-route emergency replay reconciliation V13",
        "",
        "The exact 566-row JSON retains every V12 row field except the named SH-IAM-005 "
        "emergency authored task's additional targeted source ID. One reviewed fictional "
        "local marker replay contributes eight Clean and fifteen Messy native original leads.",
        "",
        "| Classification | Routes per side |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {name} | {number} |" for name, number in count["classifications"].items())
    lines += [
        "",
        "Clean records a bounded approved local hash match. Messy denies an early fast path, "
        "records a stale-checkpoint mismatch, then a local retest while historical and upstream "
        "exceptions remain OPEN. No bytes or packets are sent, and there is no actual ePHI access.",
        "",
        "The authored emergency clause remains UNSUPPORTED_EXACT_CLAUSE. All 121 unsupported "
        "routes per side remain unsupported; the named target already existed, so distinct "
        f"targeted routes stay {count['targeted_integrated_route_count']} per side.",
        "",
        "No task credit, fresh pair, Key, grade or Atlas write occurred. The frozen P1 pair "
        "retains 409 NOT_STARTED/NOT_RUN tasks per side.",
        "",
    ]
    return "\n".join(lines)
