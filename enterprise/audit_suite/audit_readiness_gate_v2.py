"""Read-only, fail-closed readiness diagnostic over reviewed fictional sources.

This gate reports the currently blocked workflow; it never accepts evidence or
updates a P1 task. The private main-local reviews and exact bytes are inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from . import documentary_283_route_reconciliation_v6 as frozen
from . import documentary_283_route_reconciliation_v11 as routes
from . import fictional_2027_candidate_registry_v13 as candidates
from . import fictional_2027_source_portfolio_v13 as portfolio
from . import unsupported_121_pbc_plan_v9 as requests

SCHEMA = "SH_FICTIONAL_AUDIT_READINESS_GATE_V2"
BASE = "enterprise/generated/audit-suite"
PINS = {
    "v13_review": (
        "private",
        f"{BASE}/company-source-portfolio-v13-2026-09-30/independent-review-main-v1/REVIEW.json",
        "a035f34e1b530000395483dd2ae3b7eae9dc68fc0d881cca84373140a0c7f69f",
    ),
    "v13_portfolio": (
        "private",
        f"{BASE}/company-source-portfolio-v13-2026-09-30/main-run-v1/REPORT.json",
        "f07da9b6a2aa261c63a2cad0c8bef31ecbb4d56c397e8ee1b0d0b261ff088954",
    ),
    "v13_candidate_a": (
        "private",
        f"{BASE}/company-source-portfolio-v13-2026-09-30/main-candidate-v1/A.json",
        "aa0750be8ee501ea7274d53f87196f7bf9fd0c49f3971a3359b244baaef93f16",
    ),
    "v13_candidate_b": (
        "private",
        f"{BASE}/company-source-portfolio-v13-2026-09-30/main-candidate-v1/B.json",
        "7d39f207576d9d50373abe933d55004598a6dd1f83bb69b66325796636f1980e",
    ),
    "v13_candidate_report": (
        "private",
        f"{BASE}/company-source-portfolio-v13-2026-09-30/main-candidate-v1/REPORT.json",
        "c9f726cb73002018bfc70c9d97d39a8b1fa02286f184cdb42f1448b73ede1f21",
    ),
    "v11_route_review": (
        "private",
        f"{BASE}/documentary-283-route-reconciliation-v11-2026-09-30/independent-review-main-v1/REVIEW.json",
        "5db6205b1afcbd578562345a7ff0af6a212b8cbf1c39139cb71a22590fd394a2",
    ),
    "v11_route": (
        "repo",
        "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V11_2026-09-30.json",
        "41facc0f48c2f0fc4b9144366bb239131e54c1693fde2bcbfa9ded7360792299",
    ),
    "v11_route_main": (
        "private",
        f"{BASE}/documentary-283-route-reconciliation-v11-2026-09-30/main-run-v1/LEDGER.json",
        "41facc0f48c2f0fc4b9144366bb239131e54c1693fde2bcbfa9ded7360792299",
    ),
    "pbc_v9_review": (
        "private",
        f"{BASE}/unsupported-121-pbc-plan-v9-2026-09-30/independent-review-main-v1/REVIEW.json",
        "eec6fc792c71849e34f25b280ef064fe29463860e1d1edff6102a16539a0958b",
    ),
    "pbc_v9": (
        "repo",
        "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V9_2026-09-30.json",
        "3ee6f8a8dde7fe5502a55074e6861cab9aabf119a1657b447514e1410641ccff",
    ),
    "pbc_v9_main": (
        "private",
        f"{BASE}/unsupported-121-pbc-plan-v9-2026-09-30/main-run-v1/PLAN.json",
        "3ee6f8a8dde7fe5502a55074e6861cab9aabf119a1657b447514e1410641ccff",
    ),
}
P1_FREEZE = {
    "file_count": 538,
    "inventory_sha256": "f266ef682b502b3b093170f8a7b64fcf5cbab722d5c8ddf6715a63c0e535360f",
}


class GateError(ValueError):
    """An input, row join, or readiness boundary changed."""


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _reject_symlink_chain(path: Path) -> None:
    """Reject aliases at every existing component, including the supplied root."""
    absolute = Path(path).absolute()
    for component in reversed((absolute, *absolute.parents)):
        try:
            mode = component.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise GateError(f"Symlinked path component forbidden: {component}")


def _load_pins(repository: Path, private: Path) -> tuple[dict, dict]:
    loaded = {}
    identities = {}
    for key, (scope, relative, expected) in PINS.items():
        if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
            raise GateError(f"{key}: accepted independent review pin pending")
        path = (private if scope == "private" else repository) / relative
        if scope == "private":
            _reject_symlink_chain(path)
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise GateError(f"{key}: ordinary single-link file required")
        if scope == "private" and stat.S_IMODE(info.st_mode) != 0o600:
            raise GateError(f"{key}: private 0600 mode required")
        if _digest(path) != expected:
            raise GateError(f"{key}: pinned SHA-256 differs")
        loaded[key] = json.loads(path.read_text())
        identities[key] = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    return loaded, identities


def _assert_review_boundaries(data: dict) -> None:
    v13 = data["v13_review"]
    route = data["v11_route_review"]
    pbc = data["pbc_v9_review"]
    if (
        v13.get("verdict") != "PASS_PARTIAL_SEC001_COMPONENT_PORTFOLIO_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or v13.get("main_output_sha256")
        != {
            "portfolio_report": PINS["v13_portfolio"][2],
            "candidate_A": PINS["v13_candidate_a"][2],
            "candidate_B": PINS["v13_candidate_b"][2],
            "candidate_report": PINS["v13_candidate_report"][2],
        }
        or route.get("verdict") != "PASS_SELECTED_SEC001_CC67_ROUTE_V11_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or route.get("main_tracked_sha256", {}).get(PINS["v11_route"][1]) != PINS["v11_route"][2]
        or route.get("main_output_sha256", {}).get("LEDGER.json") != PINS["v11_route_main"][2]
        or pbc.get("verdict") != "PASS_READ_ONLY_UNSUPPORTED_121_PBC_V9_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or pbc.get("main_tracked_sha256", {}).get(PINS["pbc_v9"][1]) != PINS["pbc_v9"][2]
        or pbc.get("main_run_sha256", {}).get("PLAN.json") != PINS["pbc_v9_main"][2]
        or pbc.get("reviewed_input_sha256", {}).get(PINS["v11_route_review"][1])
        != PINS["v11_route_review"][2]
    ):
        raise GateError("Independent review or exact output join differs")
    for review in (v13, route, pbc):
        if (
            review.get("audit_task_credit") is not False
            or review.get("source_complete") is not False
            or review.get("active_pair_mutated") is True
        ):
            raise GateError("Review asserts credit or P1 mutation")
    if any(review.get("p1_freeze") != P1_FREEZE for review in (v13, route, pbc)):
        raise GateError("Review P1 freeze differs")
    if data["v11_route_main"] != data["v11_route"] or data["pbc_v9_main"] != data["pbc_v9"]:
        raise GateError("Reviewed main run/tracked route or request bytes differ")


def _assemble(port: dict, candidate: dict, ledger: dict, pbc: dict) -> dict:
    """Join every task and request row, then summarize blockers by family/control."""
    if (
        (port.get("source_count"), port.get("native_versions"), port.get("source_component_count"))
        != (34, 780, 35)
        or port.get("source_complete") is not False
        or port.get("fresh_audit_pair_created") is not False
        or port.get("audit_task_credit") is not False
        or len(port.get("sources", [])) != 34
        or sum(row["native_versions"] for row in port["sources"]) != 780
        or candidate.get("source_complete") is not False
        or candidate.get("fresh_audit_pair_created") is not False
        or candidate.get("audit_task_credit") is not False
        or candidate.get("grants_or_collections_created") is not False
        or candidate.get("reviewed_native_versions") != 780
        or ledger.get("audit_task_credit") is not False
        or ledger.get("active_pair_mutated") is not False
        or pbc.get("audit_task_credit") is not False
        or pbc.get("active_pair_mutated") is not False
        or pbc.get("fresh_pair_created") is not False
        or pbc.get("external_messages_sent") != 0
        or pbc.get("accepted_na_determinations") != 0
        or ledger.get("p1_freeze") != P1_FREEZE
        or pbc.get("p1_freeze") != P1_FREEZE
    ):
        raise GateError("Source, route, request or P1 claim boundary differs")
    source_names = [row["source"] for row in port["sources"]]
    if len(set(source_names)) != 34:
        raise GateError("Source cohort roster is not unique")
    source_by_name = {row["source"]: row for row in port["sources"]}
    if (
        source_by_name["sec001component"]["review_sha256"] != requests.PINS[requests.COMP_REVIEW]
        or source_by_name["sec001component"]["receipt_sha256"]
        != requests.PINS[requests.COMP_RECEIPT]
        or source_by_name["sec001transfer"]["receipt_sha256"]
        != requests.PINS[requests.TRANSFER_RECEIPT]
        or source_by_name["sec001component"]["actual_deployed_component"] is not False
        or source_by_name["sec001transfer"]["actual_network_transmission"] is not False
    ):
        raise GateError("Selected SEC001 source/PBC receipt or deployment boundary differs")
    for side in "AB":
        row = candidate["sides"][side]
        pins = row["source_pins"]
        if (
            row.get("source_complete") is not False
            or (
                row.get("source_cohort_count"),
                row.get("scenario_source_component_count"),
                row.get("component_count"),
                row.get("system_alias_count"),
            )
            != (34, 35, 48, 297)
            or len(pins) != 35
            or sorted(set(pin["source"] for pin in pins)) != sorted(source_names)
        ):
            raise GateError(f"{side}: candidate source roster differs")
        for source in port["sources"]:
            matched = [pin for pin in pins if pin["source"] == source["source"]]
            if not matched or any(
                pin["source_review_sha256"] != source["review_sha256"]
                or pin["receipt_sha256"] != source["receipt_sha256"]
                or pin["manifest_sha256"] != source["manifest_sha256"]
                or pin["database_sha256"]
                != (
                    source["database_sha256"][pin["ledger"]]
                    if isinstance(source["database_sha256"], dict)
                    else source["database_sha256"]
                )
                or (
                    "ledger_system_counts" in source
                    and pin["system_count"] != source["ledger_system_counts"][pin["ledger"]]
                )
                or (
                    "branch_versions" in source
                    and pin["physical_branch"] not in source["branch_versions"]
                )
                or (
                    "inherited_audit_journals" in source
                    and pin["inherited_audit_journals"] != source["inherited_audit_journals"]
                )
                for pin in matched
            ):
                raise GateError(
                    f"{side}: candidate/native source pin join differs: {source['source']}"
                )
    route_rows = ledger.get("rows", [])
    request_rows = pbc.get("rows", [])
    if len(route_rows) != 566 or len(request_rows) != 242:
        raise GateError("Route or request row denominator differs")
    route_index = {(row["side"], row["task_id"]): row for row in route_rows}
    request_index = {(row["side"], row["task_id"]): row for row in request_rows}
    if len(route_index) != 566 or len(request_index) != 242:
        raise GateError("Duplicate route or request key")
    for side, scenario, component_count, transfer_count in (
        ("A", "CLEAN", 10, 10),
        ("B", "MESSY", 15, 16),
    ):
        component_row = request_index[side, requests.CC52_TASK]
        transfer_row = request_index[side, requests.CC67_TASK]
        if (
            component_row["v9_reviewed_source_ids"] != [requests.COMP_SOURCE]
            or transfer_row["v9_reviewed_source_ids"] != [requests.TRANSFER_SOURCE]
            or len(component_row["v9_source_record_refs"][requests.COMP_SOURCE]) != component_count
            or len(transfer_row["v9_source_record_refs"][requests.TRANSFER_SOURCE])
            != transfer_count
            or source_by_name["sec001component"]["branch_versions"][f"SEC001-COMPONENT-{scenario}"]
            != component_count
            or source_by_name["sec001transfer"]["branch_versions"][f"SEC001-XFER-{scenario}"]
            != transfer_count
            or route_index[side, requests.CC67_TASK]["v11_reviewed_source_ids"]
            != [requests.TRANSFER_SOURCE]
            or component_row["v9_targeted_source_ids"] != ["SEC003_SELECTED_VULNERABILITY_V1"]
            or transfer_row["v9_targeted_source_ids"] != [requests.TRANSFER_SOURCE]
        ):
            raise GateError(f"{side}: selected SEC001 route/request/native lead differs")
    grouped: dict[str, dict[str, dict]] = defaultdict(dict)
    side_counts = {}
    for side in "AB":
        side_routes = [row for row in route_rows if row["side"] == side]
        side_requests = [row for row in request_rows if row["side"] == side]
        classes = Counter(row["classification"] for row in side_routes)
        if len(side_routes) != 283 or classes != {
            "SOURCE_CANDIDATE_PARTIAL": 135,
            "DESIGN_CONTEXT_ONLY": 27,
            "UNSUPPORTED_EXACT_CLAUSE": 121,
        }:
            raise GateError(f"{side}: route classes differ")
        if sum(bool(row["targeted_integrated_source_ids"]) for row in side_routes) != 174:
            raise GateError(f"{side}: targeted route denominator differs")
        if (
            len(side_requests) != 121
            or sum(bool(row["possible_nonoccurrence_review_candidate"]) for row in side_requests)
            != 53
        ):
            raise GateError(f"{side}: unsupported/no-event denominator differs")
        for task_source in (ledger, pbc):
            if task_source["active_p1_tasks"][side] != {
                "task_count": 409,
                "status": "NOT_STARTED",
                "conclusion": "NOT_RUN",
            }:
                raise GateError(f"{side}: frozen P1 task status differs")
        for route in side_routes:
            if (
                route["current_status"],
                route["current_conclusion"],
                route["audit_task_credit"],
                route["actual_operation_eligibility_as_of_packet"],
            ) != ("NOT_STARTED", "NOT_RUN", False, False):
                raise GateError(f"{side}: route task gained status, operation or credit")
            family = route["family"]
            control = route["control_id"]
            control_row = grouped[family].setdefault(
                control,
                {
                    "route_classes": Counter(),
                    "targeted_task_ids": [],
                    "unsupported_task_ids": [],
                    "design_task_ids": [],
                    "partial_task_ids": [],
                    "draft_request_group_ids": set(),
                    "unaccepted_no_event_task_ids": [],
                    "remaining_gates": {},
                    "route_limits": {},
                },
            )
            task_key = f"{side}:{route['task_id']}"
            control_row["route_classes"][route["classification"]] += 1
            if route["targeted_integrated_source_ids"]:
                control_row["targeted_task_ids"].append(task_key)
            req = None
            if route["classification"] == "UNSUPPORTED_EXACT_CLAUSE":
                key = (side, route["task_id"])
                if key not in request_index:
                    raise GateError(f"{side}: unsupported route lacks PBC row: {route['task_id']}")
                req = request_index[key]
                comparisons = {
                    "authored_test_clause": "authored_test_clause",
                    "control_id": "control_id",
                    "family": "family",
                    "procedure_type": "procedure_type",
                    "remaining_test_gate": "remaining_test_gate",
                    "requirement_ids": "requirement_ids",
                    "screen_row_sha256": "screen_row_sha256",
                    "current_status": "current_task_status",
                    "current_conclusion": "current_task_conclusion",
                    "targeted_integrated_source_ids": "v9_targeted_source_ids",
                }
                if any(route[left] != req[right] for left, right in comparisons.items()):
                    raise GateError(f"{side}: route/PBC clause join differs: {route['task_id']}")
                if (
                    req["pbc_request_status"] != "DRAFT_NOT_SENT"
                    or req["task_credit"] is not False
                    or req["accepted_nonoccurrence_status"]
                    not in {"NOT_ESTABLISHED", "NO_NONOCCURRENCE_PATH_DEFINED"}
                ):
                    raise GateError(f"{side}: request acceptance or credit changed")
                control_row["unsupported_task_ids"].append(task_key)
                control_row["draft_request_group_ids"].add(req["request_group_id"])
                if req["possible_nonoccurrence_review_candidate"]:
                    control_row["unaccepted_no_event_task_ids"].append(task_key)
            elif route["classification"] == "DESIGN_CONTEXT_ONLY":
                control_row["design_task_ids"].append(task_key)
            else:
                control_row["partial_task_ids"].append(task_key)
            control_row["remaining_gates"][task_key] = route["remaining_test_gate"]
            control_row["route_limits"][task_key] = {
                "source_limit": route["source_limit"],
                "targeted_source_ids": route["targeted_integrated_source_ids"],
                "candidate_or_design_source_ids": route["candidate_or_design_source_ids"],
                "v5_source_limits": route["v5_source_limits"],
                "v6_source_limits": route["v6_source_limits"],
                "v7_source_limits": route["v7_source_limits"],
                "v8_source_limits": route["v8_source_limits"],
                "v9_source_limits": route["v9_source_limits"],
                "v10_source_limits": route["v10_source_limits"],
                "v11_source_limits": route["v11_source_limits"],
                "v11_source_record_refs": route["v11_source_record_refs"],
                "pbc_v9_reviewed_source_ids": req["v9_reviewed_source_ids"] if req else [],
                "pbc_v9_source_limits": req["v9_source_limits"] if req else {},
                "pbc_v9_source_record_refs": req["v9_source_record_refs"] if req else {},
            }
        side_counts[side] = {
            "source_cohorts": 34,
            "native_business_versions": 780,
            "routes": 283,
            "targeted_routes": 174,
            "partial_routes": 135,
            "design_routes": 27,
            "unsupported_exact_clauses": 121,
            "unaccepted_no_event_candidates": 53,
            "p1_tasks_not_started_not_run": 409,
        }
    if set(request_index) != {
        key
        for key, row in route_index.items()
        if row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
    }:
        raise GateError("PBC request coverage differs from unsupported routes")
    groups = pbc.get("request_groups", [])
    if (
        len(groups) != 30
        or len({row["request_group_id"] for row in groups}) != 30
        or any(
            row["request_status"] != "DRAFT_NOT_SENT" or row["task_credit"] is not False
            for row in groups
        )
    ):
        raise GateError("PBC draft group boundary differs")
    for group in groups:
        for side in "AB":
            actual = sorted(
                row["task_id"]
                for row in request_rows
                if row["side"] == side and row["request_group_id"] == group["request_group_id"]
            )
            if actual != sorted(group["task_ids_per_side"][side]):
                raise GateError("PBC group/task membership differs")
    blockers = {}
    for family, controls in sorted(grouped.items()):
        blockers[family] = {}
        for control, item in sorted(controls.items()):
            blockers[family][control] = {
                key: (
                    dict(value)
                    if isinstance(value, Counter)
                    else sorted(value)
                    if isinstance(value, (set, list))
                    else value
                )
                for key, value in item.items()
            }
    if sum(map(len, blockers.values())) != 43:
        raise GateError("Blocked control map denominator differs")
    return {
        "schema": SCHEMA,
        "as_of": "2026-09-30",
        "purpose": "READ_ONLY_WORKFLOW_DIAGNOSTIC",
        "source_complete": False,
        "fresh_pair_eligible": False,
        "fresh_audit_pair_created": False,
        "audit_ready": False,
        "audit_task_credit": False,
        "audit_conclusion_issued": False,
        "key_issued": False,
        "grade_issued": False,
        "actual_operation_claimed": False,
        "grants_or_collections_created": False,
        "accepted_na_determinations": 0,
        "external_messages_sent": 0,
        "p1_freeze": P1_FREEZE,
        "pins": {
            key: {"scope": scope, "path": path, "sha256": sha}
            for key, (scope, path, sha) in PINS.items()
        },
        "sides": side_counts,
        "source_roster": port["sources"],
        "candidate_source_pins": {side: candidate["sides"][side]["source_pins"] for side in "AB"},
        "request_groups": [
            {
                "request_group_id": group["request_group_id"],
                "control_id": group["control_id"],
                "status": group["request_status"],
                "task_ids_per_side": group["task_ids_per_side"],
                "next_action": group["v9_next_action"],
                "v9_reviewed_source_ids": group["v9_reviewed_source_ids"],
                "v9_source_limits": group["v9_source_limits"],
                "v9_source_record_refs_by_side": group["v9_source_record_refs_by_side"],
            }
            for group in groups
        ],
        "blockers_by_family_control": blockers,
        "boundary_limits": {
            "portfolio": port["limits"],
            "candidate": candidate["limits"],
            "route": ledger["limits"],
            "requests": pbc["limits"],
        },
        "readiness_blockers": [
            "Partial selected fictional source roster; complete period populations and "
            "independent evidence are not established.",
            "All 283 documentary/activity routes per side remain partial, design context, or "
            "unsupported, with no task execution or credit.",
            "121 exact authored clauses per side remain unsupported; 30 request groups "
            "remain draft and unsent.",
            "53 possible no-event cases per side lack a qualified nonoccurrence decision; "
            "no blanket N/A acceptance.",
            "The pending addressable docket, fictional SEC001 transfer/component leads, "
            "and open Messy exceptions do not establish deployed populations, actual "
            "applicability, decisions, safeguards, or operating effectiveness.",
            "The frozen P1 pair has 409 NOT_STARTED/NOT_RUN tasks per side; "
            "no fresh pair is eligible.",
        ],
    }


def build(repository: Path, private_repository: Path) -> dict:
    _reject_symlink_chain(private_repository)
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    before, identities = _load_pins(repository, private)
    _assert_review_boundaries(before)
    if frozen._p1_inventory(private) != P1_FREEZE:
        raise GateError("Frozen P1 inventory differs")
    port = portfolio.verify_report(
        private / Path(PINS["v13_portfolio"][1]).parent, repository, private
    )
    candidate = candidates.verify_candidate(
        private / Path(PINS["v13_candidate_a"][1]).parent, repository, private
    )
    ledger = routes.build(repository, private)
    pbc = requests.build(repository, private)
    for name, actual in (
        ("v13_portfolio", port),
        ("v13_candidate_report", candidate),
        ("v11_route", ledger),
        ("pbc_v9", pbc),
    ):
        if actual != before[name]:
            raise GateError(f"{name}: exact builder replay differs")
    result = _assemble(port, candidate, ledger, pbc)
    after, after_ids = _load_pins(repository, private)
    if after != before or after_ids != identities or frozen._p1_inventory(private) != P1_FREEZE:
        raise GateError("Pinned input or frozen P1 changed during gate")
    return result


def markdown(report: dict) -> str:
    lines = [
        "# Fictional audit readiness gate",
        "",
        "**Blocked.** This is a read-only workflow diagnostic for the selected 2027 "
        "fictional sources, not audit readiness or task credit.",
        "",
        "| Per side | Count |",
        "| --- | ---: |",
    ]
    counts = report["sides"]["A"]
    for label, key in (
        ("Selected source cohorts", "source_cohorts"),
        ("Native business versions", "native_business_versions"),
        ("Documentary/activity routes", "routes"),
        ("Targeted source leads", "targeted_routes"),
        ("Partial routes", "partial_routes"),
        ("Design context routes", "design_routes"),
        ("Unsupported exact clauses", "unsupported_exact_clauses"),
        ("Unaccepted no-event candidates", "unaccepted_no_event_candidates"),
        ("Frozen NOT_STARTED/NOT_RUN tasks", "p1_tasks_not_started_not_run"),
    ):
        lines.append(f"| {label} | {counts[key]} |")
    lines += [
        "| Draft, unsent request groups | 30 |",
        "",
        "`source_complete=false`; `fresh_pair_eligible=false`; `audit_ready=false`. "
        "No N/A determination, external request, collection, task credit, Key, grade, "
        "or actual-operation claim is made.",
        "",
        "## Blockers by family",
        "",
        "| Family | Partial | Design | Unsupported | Controls with blockers |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for family, controls in report["blockers_by_family_control"].items():
        totals = Counter()
        for item in controls.values():
            totals.update(item["route_classes"])
        partial = totals["SOURCE_CANDIDATE_PARTIAL"] // 2
        design = totals["DESIGN_CONTEXT_ONLY"] // 2
        unsupported = totals["UNSUPPORTED_EXACT_CLAUSE"] // 2
        lines.append(f"| {family} | {partial} | {design} | {unsupported} | {len(controls)} |")
    lines += ["", "## Gate conditions", ""]
    lines += [f"- {item}" for item in report["readiness_blockers"]]
    lines += [
        "",
        "The JSON contains the full 34-cohort roster, exact candidate source pins, "
        "all draft group memberships, and task-level remaining gates grouped by family "
        "and control. Clean and Messy limitations remain distinct in the pinned source "
        "rows and upstream reports.",
        "",
    ]
    return "\n".join(lines)


def write(repository: Path, private_repository: Path, destination: Path) -> dict:
    destination = Path(destination).absolute()
    _reject_symlink_chain(destination)
    if destination.exists() or destination.is_symlink():
        raise GateError("Fresh destination required")
    report = build(repository, private_repository)
    if destination.parent.exists():
        if (
            not destination.parent.is_dir()
            or stat.S_IMODE(destination.parent.stat().st_mode) != 0o700
        ):
            raise GateError("Preexisting output parent must already be private 0700")
    else:
        destination.parent.mkdir(parents=True, mode=0o700)
    _reject_symlink_chain(destination)
    with tempfile.TemporaryDirectory(
        prefix=".readiness-gate-", dir=destination.parent
    ) as temporary:
        stage = Path(temporary)
        for name, content in (
            ("REPORT.json", json.dumps(report, sort_keys=True, indent=2) + "\n"),
            ("REPORT.md", markdown(report)),
        ):
            path = stage / name
            path.write_text(content)
            path.chmod(0o600)
        os.rename(stage, destination)
    return report


def verify(destination: Path, repository: Path, private_repository: Path) -> dict:
    destination = Path(destination)
    _reject_symlink_chain(destination)
    if (
        destination.is_symlink()
        or stat.S_IMODE(destination.stat().st_mode) != 0o700
        or stat.S_IMODE(destination.parent.stat().st_mode) != 0o700
        or {p.name for p in destination.iterdir()} != {"REPORT.json", "REPORT.md"}
    ):
        raise GateError("Exact private two-file gate output required")
    for path in destination.iterdir():
        info = path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or stat.S_IMODE(info.st_mode) != 0o600
        ):
            raise GateError("Private ordinary output required")
    actual = json.loads((destination / "REPORT.json").read_text())
    expected = build(repository, private_repository)
    if actual != expected or (destination / "REPORT.md").read_text() != markdown(expected):
        raise GateError("Gate output differs from pinned replay")
    return actual


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    result = (
        write(args.repository, args.private_repository, args.destination)
        if args.action == "create"
        else verify(args.destination, args.repository, args.private_repository)
    )
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "audit_ready": result["audit_ready"],
                "sides": result["sides"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
