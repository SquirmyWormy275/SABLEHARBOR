"""Read-only blocked readiness diagnostic over reviewed PRD and GOV successors."""

from __future__ import annotations

import argparse
import json
import os
import stat
import tempfile
from collections import Counter
from copy import deepcopy
from pathlib import Path

from . import audit_readiness_gate_v3 as prior
from . import documentary_283_route_reconciliation_v16 as routes
from . import fictional_2027_candidate_registry_v16 as candidates
from . import fictional_2027_source_portfolio_v16 as portfolio
from . import unsupported_121_pbc_plan_v13 as requests
from .documentary_283_route_reconciliation_v6 import _p1_inventory

SCHEMA = "SH_FICTIONAL_AUDIT_READINESS_GATE_V4"
BASE = "enterprise/generated/audit-suite"
PINS = {
    "v3_report": (
        "private",
        f"{BASE}/readiness-gate-v3-2026-09-30/main-run-v1/REPORT.json",
        "ae8f0bb6dc247a5992338ac8b8326502375bae4b97122c5438025ebfa1cc8bec",
    ),
    "v3_review": (
        "private",
        f"{BASE}/readiness-gate-v3-2026-09-30/independent-review-main-v1/REVIEW.json",
        "586edfc9c69c0efea68bfe6550180ea8f82d0092781f930d855009921e44b7e3",
    ),
    "v16_portfolio_review": (
        "private",
        f"{BASE}/company-source-portfolio-v16-2026-10-01/independent-review-main-v1/REVIEW.json",
        "30923f186892af9f99d49acbd341fc5298ac8d95347d65499783590f226ede2c",
    ),
    "v16_portfolio": (
        "private",
        f"{BASE}/company-source-portfolio-v16-2026-10-01/main-report-v1/REPORT.json",
        "e5e311f4bf38f2d94caf827e3bbe6b6e0e1f5dca25328f31f51b398a9dd39d67",
    ),
    "v16_candidate_a": (
        "private",
        f"{BASE}/company-source-portfolio-v16-2026-10-01/main-candidate-v1/A.json",
        "f8559bd7bca5af378506d65493e244a2be0a7814b427815c3006baa8c41fb527",
    ),
    "v16_candidate_b": (
        "private",
        f"{BASE}/company-source-portfolio-v16-2026-10-01/main-candidate-v1/B.json",
        "71fc721a391ae2302a86e87bb4137d4b703fa9069b8515bd6c89cf868904e2ae",
    ),
    "v16_candidate_report": (
        "private",
        f"{BASE}/company-source-portfolio-v16-2026-10-01/main-candidate-v1/REPORT.json",
        "88eb2b8efda6f9a98d8d0113092ef6c5c9f4b28e62a2673999956890fa43bb4f",
    ),
    "v16_route_review": (
        "private",
        f"{BASE}/documentary-283-route-reconciliation-v16-2026-10-01/independent-review-main-v1/REVIEW.json",
        "138bc8e7cd5e701d0507e4dcb6228364c3406aa097d12d14d9753c456ae60b34",
    ),
    "v16_route": (
        "repo",
        "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V16_2026-10-01.json",
        "cd3b55409e9e0112b49d060cfbbacf329660422d0c4e1b2002ec220af5bad5a3",
    ),
    "v16_route_main": (
        "private",
        f"{BASE}/documentary-283-route-reconciliation-v16-2026-10-01/main-run-v1/LEDGER.json",
        "cd3b55409e9e0112b49d060cfbbacf329660422d0c4e1b2002ec220af5bad5a3",
    ),
    "pbc_v13_review": (
        "private",
        f"{BASE}/unsupported-121-pbc-plan-v13-2026-10-01/independent-review-main-v1/REVIEW.json",
        "35416defe76a2938a12c93f8d2ac3e12226a42301d095a0f68332f84d5b0cb40",
    ),
    "pbc_v13": (
        "repo",
        "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V13_2026-10-01.json",
        "87efb4318598be3f15642062950f771b23ad51bdabddf1b64948516f8daf6d09",
    ),
    "pbc_v13_main": (
        "private",
        f"{BASE}/unsupported-121-pbc-plan-v13-2026-10-01/main-run-v1/PLAN.json",
        "87efb4318598be3f15642062950f771b23ad51bdabddf1b64948516f8daf6d09",
    ),
}
P1_FREEZE = prior.P1_FREEZE
GOV_AUTHORED = set(routes.AUTHORED)
GOV_GENERIC = set(routes.GENERIC)
GOV_TARGETS = GOV_AUTHORED | GOV_GENERIC
PRD_AUTHORED = set(requests.TASKS)
READINESS_FALSE = (
    "source_complete",
    "fresh_pair_eligible",
    "fresh_audit_pair_created",
    "audit_ready",
    "audit_task_credit",
    "audit_conclusion_issued",
    "key_issued",
    "grade_issued",
    "actual_operation_claimed",
    "grants_or_collections_created",
)


class GateError(prior.GateError):
    """A reviewed input, source join, blocker or no-credit boundary changed."""


def _load_pins(repository: Path, private: Path) -> tuple[dict, dict]:
    loaded, identities = {}, {}
    for key, (scope, relative, expected) in PINS.items():
        if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
            raise GateError(f"{key}: accepted independent review pin pending")
        path = (private if scope == "private" else repository) / relative
        if scope == "private":
            prior._reject_symlink_chain(path)
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise GateError(f"{key}: ordinary single-link file required")
        if scope == "private" and stat.S_IMODE(info.st_mode) != 0o600:
            raise GateError(f"{key}: private 0600 mode required")
        if prior._digest(path) != expected:
            raise GateError(f"{key}: pinned SHA-256 differs")
        loaded[key] = json.loads(path.read_text())
        identities[key] = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    return loaded, identities


def _assert_review_boundaries(data: dict) -> None:
    base, base_review = data["v3_report"], data["v3_review"]
    port = data["v16_portfolio_review"]
    route = data["v16_route_review"]
    pbc = data["pbc_v13_review"]
    if (
        base_review.get("schema") != "SH_INDEPENDENT_READINESS_GATE_V3_MAIN_REVIEW_V1"
        or base_review.get("verdict") != "PASS_MAIN_READ_ONLY_BLOCKED_NO_CREDIT"
        or base_review.get("output_sha256", {}).get("REPORT.json") != PINS["v3_report"][2]
        or base_review.get("p1_freeze") != P1_FREEZE
        or base_review.get("audit_ready") is not False
        or base_review.get("audit_task_credit") is not False
        or base.get("schema") != prior.SCHEMA
        or base.get("p1_freeze") != P1_FREEZE
        or any(base.get(key) is not False for key in READINESS_FALSE)
        or base.get("accepted_na_determinations") != 0
        or base.get("external_messages_sent") != 0
        or port.get("schema") != "SH_INDEPENDENT_PRD_PORTFOLIO_V16_MAIN_REVIEW_V1"
        or port.get("verdict") != "PASS_MAIN_PARTIAL_CANDIDATE_NO_AUDIT_CREDIT"
        or port.get("output_sha256")
        != {
            "main-report-v1/REPORT.json": PINS["v16_portfolio"][2],
            "main-candidate-v1/A.json": PINS["v16_candidate_a"][2],
            "main-candidate-v1/B.json": PINS["v16_candidate_b"][2],
            "main-candidate-v1/REPORT.json": PINS["v16_candidate_report"][2],
        }
        or port.get("source_complete") is not False
        or port.get("fresh_audit_pair_created") is not False
        or port.get("audit_task_credit") is not False
        or route.get("schema") != "SH_INDEPENDENT_GOV_ROUTE_V16_MAIN_REVIEW_V1"
        or route.get("verdict") != "PASS_MAIN_SELECTED_GOV_LEAD_NO_AUDIT_CREDIT"
        or route.get("output_sha256", {}).get("LEDGER.json") != PINS["v16_route_main"][2]
        or route.get("p1_freeze") != P1_FREEZE
        or route.get("audit_task_credit") is not False
        or pbc.get("schema") != "SH_INDEPENDENT_PRD_PBC_V13_MAIN_REVIEW_V1"
        or pbc.get("verdict") != "PASS_MAIN_DRAFT_ONLY_NO_AUDIT_CREDIT"
        or pbc.get("output_sha256", {}).get("PLAN.json") != PINS["pbc_v13_main"][2]
        or pbc.get("p1_freeze") != P1_FREEZE
        or pbc.get("audit_task_credit") is not False
        or data["v16_route"] != data["v16_route_main"]
        or data["pbc_v13"] != data["pbc_v13_main"]
    ):
        raise GateError("Independent review or exact output join differs")


def _assemble(base: dict, port: dict, candidate: dict, ledger: dict, pbc: dict) -> dict:
    """Update V3's exact 43-control map without promoting any readiness state."""
    if (
        base.get("schema") != prior.SCHEMA
        or base.get("p1_freeze") != P1_FREEZE
        or base.get("audit_ready") is not False
        or sum(len(controls) for controls in base["blockers_by_family_control"].values()) != 43
        or port.get("schema") != portfolio.SCHEMA
        or (
            port.get("source_count"),
            port.get("native_versions"),
            port.get("source_component_count"),
        )
        != (37, 840, 38)
        or port.get("sources", [])[:36] != base["source_roster"]
        or len(port.get("sources", [])) != 37
        or any(
            port.get(key) is not False
            for key in ("source_complete", "fresh_audit_pair_created", "audit_task_credit")
        )
        or candidate.get("schema") != candidates.SCHEMA
        or candidate.get("reviewed_native_versions") != 840
        or any(
            candidate.get(key) is not False
            for key in (
                "source_complete",
                "fresh_audit_pair_created",
                "grants_or_collections_created",
                "audit_task_credit",
            )
        )
        or ledger.get("schema") != routes.SCHEMA
        or ledger.get("p1_freeze") != P1_FREEZE
        or ledger.get("audit_task_credit") is not False
        or ledger.get("active_pair_mutated") is not False
        or pbc.get("schema") != requests.SCHEMA
        or pbc.get("p1_freeze") != P1_FREEZE
        or any(
            pbc.get(key) is not False
            for key in (
                "audit_task_credit",
                "source_complete",
                "active_pair_mutated",
                "fresh_pair_created",
            )
        )
        or pbc.get("external_messages_sent") != 0
        or pbc.get("accepted_na_determinations") != 0
    ):
        raise GateError("Source, route, request or P1 claim boundary differs")
    concern = port["sources"][-1]
    if (
        concern.get("source") != "prdconcern"
        or concern.get("native_versions") != 21
        or concern.get("branch_versions") != {"PRD-CONCERN-CLEAN": 8, "PRD-CONCERN-MESSY": 13}
        or concern.get("review_sha256") != portfolio.CONCERN_REVIEW_SHA
        or concern.get("receipt_sha256") != portfolio.CONCERN_RECEIPT_SHA
        or concern.get("manifest_sha256") != portfolio.CONCERN_MANIFEST_SHA
        or concern.get("database_sha256") != {"native": portfolio.CONCERN_DB_SHA}
        or concern.get("selected_claimant_verified") is not False
        or concern.get("fictional_accepted_deliveries") != 0
        or concern.get("customer_acknowledgments") != 0
        or concern.get("real_external_messages_sent") != 0
        or concern.get("source_complete") is not False
    ):
        raise GateError("Selected PRD concern source or held gate differs")
    candidate_pins = {}
    for side, branch in (("A", "PRD-CONCERN-CLEAN"), ("B", "PRD-CONCERN-MESSY")):
        selected = candidate["sides"][side]
        pins = selected["source_pins"]
        last = pins[-1]
        if (
            selected.get("source_complete") is not False
            or (
                selected.get("source_cohort_count"),
                selected.get("scenario_source_component_count"),
                selected.get("component_count"),
                selected.get("system_alias_count"),
            )
            != (37, 38, 51, 324)
            or len(pins) != 38
            or pins[:37] != base["candidate_source_pins"][side]
            or last.get("source") != "prdconcern"
            or last.get("physical_branch") != branch
            or last.get("source_review_sha256") != concern["review_sha256"]
            or last.get("receipt_sha256") != concern["receipt_sha256"]
            or last.get("manifest_sha256") != concern["manifest_sha256"]
            or last.get("database_sha256") != concern["database_sha256"]["native"]
            or last.get("system_count") != 10
        ):
            raise GateError(f"{side}: V16 candidate/source prefix or held pin differs")
        candidate_pins[side] = pins
    route_rows, request_rows = ledger.get("rows", []), pbc.get("rows", [])
    if len(route_rows) != 566 or len(request_rows) != 242:
        raise GateError("Route or request row denominator differs")
    route_index = {(row["side"], row["task_id"]): row for row in route_rows}
    request_index = {(row["side"], row["task_id"]): row for row in request_rows}
    if len(route_index) != 566 or len(request_index) != 242:
        raise GateError("Duplicate route or request key")
    original = base["blockers_by_family_control"]
    blockers = deepcopy(original)
    old_targets = {side: set() for side in "AB"}
    old_classes = {}
    for controls in blockers.values():
        for item in controls.values():
            for key in item["targeted_task_ids"]:
                old_targets[key[0]].add(key)
            for key in item["design_task_ids"]:
                old_classes[key] = "DESIGN_CONTEXT_ONLY"
            for key in item["partial_task_ids"]:
                old_classes[key] = "SOURCE_CANDIDATE_PARTIAL"
            for key in item["unsupported_task_ids"]:
                old_classes[key] = "UNSUPPORTED_EXACT_CLAUSE"
            item.update(
                route_classes=Counter(),
                targeted_task_ids=[],
                unsupported_task_ids=[],
                design_task_ids=[],
                partial_task_ids=[],
                draft_request_group_ids=set(),
                unaccepted_no_event_task_ids=[],
                route_pbc_sync_pending_task_ids=[],
            )
    if len(old_classes) != 566:
        raise GateError("V3 blocker task map differs")
    side_counts = {}
    for side in "AB":
        side_routes = [row for row in route_rows if row["side"] == side]
        side_requests = [row for row in request_rows if row["side"] == side]
        classes = Counter(row["classification"] for row in side_routes)
        actual_targets = {
            f"{side}:{row['task_id']}"
            for row in side_routes
            if row["targeted_integrated_source_ids"]
        }
        if (
            len(side_routes) != 283
            or classes
            != {
                "SOURCE_CANDIDATE_PARTIAL": 141,
                "DESIGN_CONTEXT_ONLY": 21,
                "UNSUPPORTED_EXACT_CLAUSE": 121,
            }
            or len(actual_targets) != 183
            or actual_targets - old_targets[side] != {f"{side}:{task}" for task in GOV_TARGETS}
            or old_targets[side] - actual_targets
            or len(side_requests) != 121
            or sum(row["possible_nonoccurrence_review_candidate"] for row in side_requests) != 53
            or sum(bool(row["v13_targeted_source_ids"]) for row in side_requests) != 35
            or sum(
                bool(row["targeted_integrated_source_ids"])
                for row in side_routes
                if row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
            )
            != 37
            or pbc["counts"][side]["v13_cumulative_reviewed_source_affected_unsupported_clauses"]
            != 27
            or pbc["counts"][side]["v13_cumulative_changed_request_groups"] != 15
        ):
            raise GateError(f"{side}: V16 route or V13 request denominator differs")
        for upstream in (ledger, pbc):
            if upstream["active_p1_tasks"][side] != {
                "task_count": 409,
                "status": "NOT_STARTED",
                "conclusion": "NOT_RUN",
            }:
                raise GateError(f"{side}: frozen P1 task status differs")
        side_counts[side] = {
            "source_cohorts": 37,
            "native_business_versions": 840,
            "routes": 283,
            "targeted_routes": 183,
            "partial_routes": 141,
            "design_routes": 21,
            "unsupported_exact_clauses": 121,
            "route_targeted_unsupported_clauses": 37,
            "pbc_targeted_unsupported_clauses": 35,
            "source_affected_unsupported_clauses": 27,
            "draft_unsent_request_groups": 30,
            "unaccepted_no_event_candidates": 53,
            "p1_tasks_not_started_not_run": 409,
        }
    for route_row in route_rows:
        side, task = route_row["side"], route_row["task_id"]
        key = f"{side}:{task}"
        family, control = route_row["family"], route_row["control_id"]
        if family not in blockers or control not in blockers[family]:
            raise GateError("V3 family/control blocker identity differs")
        item = blockers[family][control]
        if key not in item["remaining_gates"] or key not in item["route_limits"]:
            raise GateError("V3 blocker task identity differs")
        old_class = old_classes[key]
        expected_class = "SOURCE_CANDIDATE_PARTIAL" if task in GOV_GENERIC else old_class
        if (
            route_row["classification"] != expected_class
            or route_row["remaining_test_gate"] != item["remaining_gates"][key]
            or route_row["source_limit"] != item["route_limits"][key]["source_limit"]
            or (
                route_row["current_status"],
                route_row["current_conclusion"],
                route_row["audit_task_credit"],
                route_row["actual_operation_eligibility_as_of_packet"],
            )
            != ("NOT_STARTED", "NOT_RUN", False, False)
        ):
            raise GateError(f"{key}: V3 blocker gate or no-credit status differs")
        item["route_classes"][expected_class] += 1
        if route_row["targeted_integrated_source_ids"]:
            item["targeted_task_ids"].append(key)
        request = request_index.get((side, task))
        if expected_class == "UNSUPPORTED_EXACT_CLAUSE":
            if request is None:
                raise GateError(f"{key}: unsupported route lacks PBC row")
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
            }
            if any(route_row[left] != request[right] for left, right in comparisons.items()):
                raise GateError(f"{key}: route/PBC clause join differs")
            if (
                request["pbc_request_status"] != "DRAFT_NOT_SENT"
                or request["task_credit"] is not False
                or request["accepted_nonoccurrence_status"]
                not in {"NOT_ESTABLISHED", "NO_NONOCCURRENCE_PATH_DEFINED"}
            ):
                raise GateError(f"{key}: request acceptance or credit changed")
            route_targets = route_row["targeted_integrated_source_ids"]
            request_targets = request["v13_targeted_source_ids"]
            if task in GOV_AUTHORED:
                if (
                    route_targets != [routes.SOURCE]
                    or request_targets != []
                    or request["v13_reviewed_source_ids"]
                ):
                    raise GateError(f"{key}: expected GOV route/PBC gap differs")
                item["route_pbc_sync_pending_task_ids"].append(key)
            elif route_targets != request_targets:
                raise GateError(f"{key}: route/PBC source target join differs")
            item["unsupported_task_ids"].append(key)
            item["draft_request_group_ids"].add(request["request_group_id"])
            if request["possible_nonoccurrence_review_candidate"]:
                item["unaccepted_no_event_task_ids"].append(key)
        elif request is not None:
            raise GateError(f"{key}: nonunsupported route gained PBC request")
        elif expected_class == "DESIGN_CONTEXT_ONLY":
            item["design_task_ids"].append(key)
        else:
            item["partial_task_ids"].append(key)
        limit = item["route_limits"][key]
        limit.update(
            targeted_source_ids=route_row["targeted_integrated_source_ids"],
            candidate_or_design_source_ids=route_row["candidate_or_design_source_ids"],
            v14_source_limits=route_row["v14_source_limits"],
            v14_source_record_refs=route_row["v14_source_record_refs"],
            v15_source_limits=route_row["v15_source_limits"],
            v15_source_record_refs=route_row["v15_source_record_refs"],
            v16_source_limits=route_row["v16_source_limits"],
            v16_source_record_refs=route_row["v16_source_record_refs"],
            pbc_v12_reviewed_source_ids=request["v12_reviewed_source_ids"] if request else [],
            pbc_v12_source_limits=request["v12_source_limits"] if request else {},
            pbc_v12_source_record_refs=request["v12_source_record_refs"] if request else {},
            pbc_v13_reviewed_source_ids=request["v13_reviewed_source_ids"] if request else [],
            pbc_v13_source_limits=request["v13_source_limits"] if request else {},
            pbc_v13_source_record_refs=request["v13_source_record_refs"] if request else {},
        )
    if set(request_index) != {
        key
        for key, row in route_index.items()
        if row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
    }:
        raise GateError("PBC coverage differs from unsupported routes")
    group_rows = pbc.get("request_groups", [])
    if len(group_rows) != 30 or len({group["request_group_id"] for group in group_rows}) != 30:
        raise GateError("PBC group denominator differs")
    base_groups = {group["request_group_id"]: group for group in base["request_groups"]}
    groups = []
    for group in group_rows:
        name = group["request_group_id"]
        previous = base_groups[name]
        if (
            group["request_status"] != "DRAFT_NOT_SENT"
            or group["task_credit"] is not False
            or group["control_id"] != previous["control_id"]
            or group["task_ids_per_side"] != previous["task_ids_per_side"]
            or group["v11_next_action"] != previous["v11_next_action"]
            or any(
                group[key] != value
                for key, value in previous.items()
                if key.startswith(("v9_", "v10_", "v11_"))
            )
            or any(
                sorted(
                    row["task_id"]
                    for row in request_rows
                    if row["side"] == side and row["request_group_id"] == name
                )
                != sorted(group["task_ids_per_side"][side])
                for side in "AB"
            )
        ):
            raise GateError(f"{name}: V3 draft group prefix differs")
        groups.append(
            {
                **previous,
                "next_action": group["v13_next_action"],
                **{key: value for key, value in group.items() if key.startswith(("v12_", "v13_"))},
            }
        )
    if set(base_groups) != {group["request_group_id"] for group in groups}:
        raise GateError("V3 request group roster differs")
    for controls in blockers.values():
        for item in controls.values():
            for key in (
                "targeted_task_ids",
                "unsupported_task_ids",
                "design_task_ids",
                "partial_task_ids",
                "unaccepted_no_event_task_ids",
                "route_pbc_sync_pending_task_ids",
            ):
                item[key].sort()
            item["draft_request_group_ids"] = sorted(item["draft_request_group_ids"])
            item["route_classes"] = dict(item["route_classes"])
    if sum(map(len, blockers.values())) != 43:
        raise GateError("Blocked control map denominator differs")
    pending = sorted(f"{side}:{task}" for side in "AB" for task in GOV_AUTHORED)
    actual_pending = sorted(
        task
        for controls in blockers.values()
        for item in controls.values()
        for task in item["route_pbc_sync_pending_task_ids"]
    )
    if actual_pending != pending:
        raise GateError("Two GOV route/PBC synchronization gaps differ")
    return {
        **{
            key: value
            for key, value in base.items()
            if key
            not in (
                "schema",
                "as_of",
                "pins",
                "sides",
                "source_roster",
                "candidate_source_pins",
                "request_groups",
                "blockers_by_family_control",
                "boundary_limits",
                "readiness_blockers",
            )
        },
        "schema": SCHEMA,
        "as_of": "2026-10-01",
        "pins": {
            **base["pins"],
            **{
                key: {"scope": scope, "path": path, "sha256": sha}
                for key, (scope, path, sha) in PINS.items()
            },
        },
        "sides": side_counts,
        "source_roster": port["sources"],
        "candidate_source_pins": candidate_pins,
        "request_groups": groups,
        "blockers_by_family_control": blockers,
        "route_pbc_synchronization_pending_task_ids": pending,
        "boundary_limits": {
            **base["boundary_limits"],
            "portfolio_v16": port["limits"],
            "candidate_v16": candidate["limits"],
            "route_v16": ledger["limits"],
            "requests_v13": pbc["limits"],
        },
        "readiness_blockers": [
            *base["readiness_blockers"],
            "The selected PRD concern has an unverified claimant and held drafts; "
            "no accepted delivery or separate customer acknowledgment exists.",
            "Two GOV CC1.2 authored source targets await PBC request-plan reconciliation; "
            "selected committee-cycle records do not establish an actual Board meeting, "
            "legal quorum, adopted minutes or full-period oversight.",
        ],
    }


def build(repository: Path, private_repository: Path) -> dict:
    prior._reject_symlink_chain(private_repository)
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    base_pins, base_ids = prior._load_pins(repository, private)
    prior._assert_review_boundaries(base_pins)
    data, identities = _load_pins(repository, private)
    _assert_review_boundaries(data)
    if _p1_inventory(private) != P1_FREEZE:
        raise GateError("Frozen P1 inventory differs")
    base = prior._assemble(
        base_pins["v15_portfolio"],
        base_pins["v15_candidate_report"],
        base_pins["v13_route"],
        base_pins["pbc_v11"],
    )
    if base != data["v3_report"]:
        raise GateError("Reviewed V3 readiness blocker replay differs")
    result = _assemble(
        base,
        data["v16_portfolio"],
        data["v16_candidate_report"],
        data["v16_route"],
        data["pbc_v13"],
    )
    after, after_ids = _load_pins(repository, private)
    old_after, old_ids = prior._load_pins(repository, private)
    if (
        (after, after_ids) != (data, identities)
        or (old_after, old_ids) != (base_pins, base_ids)
        or _p1_inventory(private) != P1_FREEZE
    ):
        raise GateError("Pinned input or frozen P1 changed during readiness gate")
    return result


def markdown(report: dict) -> str:
    counts = report["sides"]["A"]
    lines = [
        "# Fictional audit readiness gate V4",
        "",
        "**Blocked.** This read-only diagnostic joins the selected PRD concern and "
        "GOV oversight leads to the frozen audit scope. It grants no task credit.",
        "",
        "| Per side | Count |",
        "| --- | ---: |",
    ]
    for label, key in (
        ("Selected source cohorts", "source_cohorts"),
        ("Native business versions", "native_business_versions"),
        ("Documentary/activity routes", "routes"),
        ("Targeted routes", "targeted_routes"),
        ("Partial routes", "partial_routes"),
        ("Design context routes", "design_routes"),
        ("Unsupported exact clauses", "unsupported_exact_clauses"),
        ("Route-targeted unsupported clauses", "route_targeted_unsupported_clauses"),
        ("PBC-targeted unsupported clauses", "pbc_targeted_unsupported_clauses"),
        ("Source-affected unsupported clauses", "source_affected_unsupported_clauses"),
        ("Draft unsent request groups", "draft_unsent_request_groups"),
        ("Unaccepted possible no-event cases", "unaccepted_no_event_candidates"),
        ("Frozen NOT_STARTED/NOT_RUN tasks", "p1_tasks_not_started_not_run"),
    ):
        lines.append(f"| {label} | {counts[key]} |")
    lines += [
        "",
        "The two GOV CC1.2 authored leads are present in the route ledger but not yet "
        "synchronized into the PBC draft plan. Both remain unsupported and unrun.",
        "",
        "All 43 controls retain blockers. The PRD concern has no verified claimant, "
        "accepted delivery or customer acknowledgment; the selected GOV cycle has no "
        "actual Board meeting, legal quorum or adopted minutes.",
        "",
        "`source_complete=false`; `fresh_pair_eligible=false`; `audit_ready=false`. "
        "No N/A decision, external request, collection, task credit, Key or grade was issued.",
        "",
    ]
    return "\n".join(lines)


def write(repository: Path, private_repository: Path, destination: Path) -> dict:
    destination = Path(destination).absolute()
    prior._reject_symlink_chain(destination)
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
    prior._reject_symlink_chain(destination)
    with tempfile.TemporaryDirectory(prefix=".readiness-gate-", dir=destination.parent) as temp:
        stage = Path(temp)
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
    prior._reject_symlink_chain(destination)
    if (
        destination.is_symlink()
        or stat.S_IMODE(destination.stat().st_mode) != 0o700
        or stat.S_IMODE(destination.parent.stat().st_mode) != 0o700
        or {path.name for path in destination.iterdir()} != {"REPORT.json", "REPORT.md"}
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
