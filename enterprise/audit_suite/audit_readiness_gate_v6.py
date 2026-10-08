"""Read-only blocked readiness gate over reviewed LEG/DAT source and draft leads."""

from __future__ import annotations

import argparse
import json
import os
import stat
import tempfile
from collections import Counter
from copy import deepcopy
from pathlib import Path

from . import audit_readiness_gate_v5 as prior
from . import documentary_283_route_reconciliation_v17 as routes
from . import fictional_2027_candidate_registry_v18 as candidates
from . import fictional_2027_source_portfolio_v18 as portfolio
from . import unsupported_121_pbc_plan_v15 as requests
from .audit_readiness_gate_v3 import _digest, _reject_symlink_chain
from .documentary_283_route_reconciliation_v6 import _p1_inventory

SCHEMA = "SH_FICTIONAL_AUDIT_READINESS_GATE_V6"
BASE = "enterprise/generated/audit-suite"
PINS = {
    "v5_report": (
        "private",
        f"{BASE}/readiness-gate-v5-2026-10-01/main-run-v1/REPORT.json",
        "9931f5bca3cbeac3322ca959ffedd6d023aeee28b848843640303ee3bc95add8",
    ),
    "v5_md": (
        "private",
        f"{BASE}/readiness-gate-v5-2026-10-01/main-run-v1/REPORT.md",
        "9e9dac395ea6879f6de946082c060b1769b4584805ccb8e460fdf41c4a56abc1",
    ),
    "v5_review": (
        "private",
        f"{BASE}/readiness-gate-v5-2026-10-01/independent-review-main-v1/REVIEW.json",
        "fc6569b903e4b525adf9ba13a6cc32850ec0de5974c531087c1a5498a86caa4c",
    ),
    "v18_review": (
        "private",
        f"{BASE}/company-source-portfolio-v18-2026-10-01/independent-review-main-v1/REVIEW.json",
        "626ce0755804ee22a7963343fc8dee7d1e684098c614e9188b78e0baf1d91a97",
    ),
    "v18_portfolio": (
        "private",
        f"{BASE}/company-source-portfolio-v18-2026-10-01/main-report-v1/REPORT.json",
        "254f5d1cc4d5a93da95f6fc9e5977fc36f0397511b96cd6cb5e7cd59dc56337a",
    ),
    "v18_candidate_a": (
        "private",
        f"{BASE}/company-source-portfolio-v18-2026-10-01/main-candidate-v1/A.json",
        "750de5973825de9750029ccdef1f42faf681dc7addd03b8536241c48872f2d1d",
    ),
    "v18_candidate_b": (
        "private",
        f"{BASE}/company-source-portfolio-v18-2026-10-01/main-candidate-v1/B.json",
        "9332b7f3821dd09dd643cc104c9fc1e4c82679371253d2c779c40983e5bff569",
    ),
    "v18_candidate_report": (
        "private",
        f"{BASE}/company-source-portfolio-v18-2026-10-01/main-candidate-v1/REPORT.json",
        "27d1fd7b0fd9a0c372b3d9edc4f49931a8ddb6af8907dec1c30ff3c27fcbb884",
    ),
    "v17_route_review": (
        "private",
        f"{BASE}/documentary-283-route-reconciliation-v17-2026-10-01/independent-review-main-v1/REVIEW.json",
        "dee0ff288245b0306b79c3b9819f61c940c45fb0355eec5b94a2e73baa0f6db2",
    ),
    "v17_route": (
        "repo",
        "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V17_2026-10-01.json",
        "43b33d7ca19e670eea704193fff947c268c2d1c736f0c8829420a556576e8bcb",
    ),
    "v17_route_md": (
        "repo",
        "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V17_2026-10-01.md",
        "83a4c820bd919586da52cecc586f3b156949a96dcba702ef02fe32ddd6771a81",
    ),
    "v17_route_main": (
        "private",
        f"{BASE}/documentary-283-route-reconciliation-v17-2026-10-01/main-run-v1/LEDGER.json",
        "43b33d7ca19e670eea704193fff947c268c2d1c736f0c8829420a556576e8bcb",
    ),
    "v17_route_main_md": (
        "private",
        f"{BASE}/documentary-283-route-reconciliation-v17-2026-10-01/main-run-v1/LEDGER.md",
        "83a4c820bd919586da52cecc586f3b156949a96dcba702ef02fe32ddd6771a81",
    ),
    "pbc_v15_review": (
        "private",
        f"{BASE}/unsupported-121-pbc-plan-v15-2026-10-01/independent-review-main-v1/REVIEW.json",
        "b5d1082b89088d7a08d021efa51cf30d5e6ff938d50e66944a870413d3089586",
    ),
    "pbc_v15": (
        "repo",
        "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V15_2026-10-01.json",
        "012aceb233bbaf7cd51f5e3859d6c7b7845992055a4da1e68a069db6e26fa1bc",
    ),
    "pbc_v15_md": (
        "repo",
        "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V15_2026-10-01.md",
        "a1012a0e5f24b93af5b54e53452839d35c6da44956ec7c5520047be45b0254be",
    ),
    "pbc_v15_main": (
        "private",
        f"{BASE}/unsupported-121-pbc-plan-v15-2026-10-01/main-run-v1/PLAN.json",
        "012aceb233bbaf7cd51f5e3859d6c7b7845992055a4da1e68a069db6e26fa1bc",
    ),
    "pbc_v15_main_md": (
        "private",
        f"{BASE}/unsupported-121-pbc-plan-v15-2026-10-01/main-run-v1/PLAN.md",
        "a1012a0e5f24b93af5b54e53452839d35c6da44956ec7c5520047be45b0254be",
    ),
}
P1_FREEZE = prior.P1_FREEZE
READINESS_FALSE = prior.READINESS_FALSE
DAT_TASKS = set(routes.DAT_TASKS)
LEG_SOURCE = routes.LEG_SOURCE
DAT_SOURCE = routes.DAT_SOURCE
SELECTED_GROUPS = {"SH-DAT-002", "SH-LEG-001/PROVISION"}
BASE_SIDE = {
    "source_cohorts": 37,
    "native_business_versions": 840,
    "routes": 283,
    "targeted_routes": 183,
    "partial_routes": 141,
    "design_routes": 21,
    "unsupported_exact_clauses": 121,
    "route_targeted_unsupported_clauses": 37,
    "pbc_targeted_unsupported_clauses": 37,
    "source_affected_unsupported_clauses": 29,
    "draft_unsent_request_groups": 30,
    "unaccepted_no_event_candidates": 53,
    "p1_tasks_not_started_not_run": 409,
}
NEW_BLOCKERS = (
    "LEG001's 18 selected provision locators remain open counsel status holds. The 2026 "
    "reference check is not verified 2027 law; the 16 authored leads and other 50 "
    "unmodeled clauses remain unsupported, with two Messy historical exceptions open.",
    "DAT002's one internally seeded payload-free rights inquiry has no actual customer or "
    "individual request, verified delegation, complete record-set or period population, "
    "accepted amendment or accounting completion. The Messy scope exception remains open.",
)


class GateError(prior.GateError):
    """Reviewed snapshot, exact source join, blocker or no-credit boundary changed."""


def _load_pins(repository: Path, private: Path) -> tuple[dict, dict]:
    loaded, identities = {}, {}
    for key, (scope, relative, expected) in PINS.items():
        if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
            raise GateError(f"{key}: accepted independent review pin pending")
        path = (private if scope == "private" else repository) / relative
        _reject_symlink_chain(path)
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise GateError(f"{key}: ordinary single-link file required")
        if scope == "private" and stat.S_IMODE(info.st_mode) != 0o600:
            raise GateError(f"{key}: private 0600 mode required")
        if _digest(path) != expected:
            raise GateError(f"{key}: pinned SHA-256 differs")
        loaded[key] = path.read_bytes()
        identities[key] = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    return loaded, identities


def _assert_review_boundaries(data: dict[str, bytes]) -> tuple[dict, dict, dict, dict, dict]:
    base = json.loads(data["v5_report"])
    port = json.loads(data["v18_portfolio"])
    candidate = json.loads(data["v18_candidate_report"])
    ledger = json.loads(data["v17_route"])
    pbc = json.loads(data["pbc_v15"])
    reviews = {
        key: json.loads(data[key])
        for key in ("v5_review", "v18_review", "v17_route_review", "pbc_v15_review")
    }
    expected_reviews = {
        "v5_review": (
            "SH_INDEPENDENT_READINESS_GATE_V5_MAIN_REVIEW_V1",
            "PASS_MAIN_READ_ONLY_BLOCKED_NO_CREDIT",
            {"REPORT.json": PINS["v5_report"][2], "REPORT.md": PINS["v5_md"][2]},
        ),
        "v18_review": (
            "SH_INDEPENDENT_LEG_DAT_PORTFOLIO_V18_MAIN_REVIEW_V1",
            "PASS_MAIN_PARTIAL_CANDIDATE_NO_AUDIT_CREDIT",
            {
                "main-report-v1/REPORT.json": PINS["v18_portfolio"][2],
                "main-candidate-v1/A.json": PINS["v18_candidate_a"][2],
                "main-candidate-v1/B.json": PINS["v18_candidate_b"][2],
                "main-candidate-v1/REPORT.json": PINS["v18_candidate_report"][2],
            },
        ),
        "v17_route_review": (
            "SH_INDEPENDENT_LEG_DAT_ROUTE_V17_MAIN_REVIEW_V1",
            "PASS_MAIN_SELECTED_LEADS_NO_AUDIT_CREDIT",
            {"LEDGER.json": PINS["v17_route"][2], "LEDGER.md": PINS["v17_route_md"][2]},
        ),
        "pbc_v15_review": (
            "SH_INDEPENDENT_LEG_DAT_PBC_V15_MAIN_REVIEW_V1",
            "PASS_MAIN_DRAFT_ONLY_NO_AUDIT_CREDIT",
            {"PLAN.json": PINS["pbc_v15"][2], "PLAN.md": PINS["pbc_v15_md"][2]},
        ),
    }
    for key, (schema, verdict, outputs) in expected_reviews.items():
        review = reviews[key]
        if (
            review.get("schema") != schema
            or review.get("verdict") != verdict
            or review.get("output_sha256") != outputs
            or review.get("source_complete") is not False
            or review.get("audit_task_credit") is not False
        ):
            raise GateError(f"{key}: reviewed no-credit/output boundary differs")
    if (
        reviews["v5_review"].get("p1_freeze") != P1_FREEZE
        or reviews["v5_review"].get("audit_ready") is not False
        or reviews["v5_review"].get("fresh_pair_eligible") is not False
        or reviews["v18_review"].get("fresh_audit_pair_created") is not False
        or reviews["v17_route_review"].get("active_pair_mutated") is not False
        or reviews["pbc_v15_review"].get("external_messages_sent") != 0
        or data["v17_route"] != data["v17_route_main"]
        or data["v17_route_md"] != data["v17_route_main_md"]
        or data["pbc_v15"] != data["pbc_v15_main"]
        or data["pbc_v15_md"] != data["pbc_v15_main_md"]
        or base.get("schema") != prior.SCHEMA
        or port.get("schema") != portfolio.SCHEMA
        or candidate.get("schema") != candidates.SCHEMA
        or ledger.get("schema") != routes.SCHEMA
        or pbc.get("schema") != requests.SCHEMA
        or any(item.get("as_of") != "2026-10-01" for item in (base, port, ledger, pbc))
        or any(item.get("p1_freeze") != P1_FREEZE for item in (base, ledger, pbc))
        or any(base.get(key) is not False for key in READINESS_FALSE)
        or any(item.get("source_complete") is not False for item in (port, candidate, pbc))
        or any(
            item.get("audit_task_credit") is not False for item in (port, candidate, ledger, pbc)
        )
        or any(item.get("fresh_audit_pair_created") is not False for item in (port, candidate))
        or candidate.get("grants_or_collections_created") is not False
        or pbc.get("fresh_pair_created") is not False
        or pbc.get("active_pair_mutated") is not False
        or ledger.get("active_pair_mutated") is not False
        or base.get("external_messages_sent") != 0
        or pbc.get("external_messages_sent") != 0
        or base.get("accepted_na_determinations") != 0
        or pbc.get("accepted_na_determinations") != 0
        or pbc.get("v17_route_ledger_sha256") != PINS["v17_route"][2]
    ):
        raise GateError("Reviewed V5/V18/V17/V15 claim or route/PBC boundary differs")
    return base, port, candidate, ledger, pbc


def _assemble(base: dict, port: dict, candidate: dict, ledger: dict, pbc: dict) -> dict:
    """Retain V5 blockers and add only reviewed V18/V17/V15 discovery deltas."""
    if (
        base.get("schema") != prior.SCHEMA
        or port.get("schema") != portfolio.SCHEMA
        or candidate.get("schema") != candidates.SCHEMA
        or ledger.get("schema") != routes.SCHEMA
        or pbc.get("schema") != requests.SCHEMA
        or any(item.get("source_complete") is not False for item in (base, port, candidate, pbc))
        or any(
            item.get("audit_task_credit") is not False
            for item in (base, port, candidate, ledger, pbc)
        )
        or any(base.get(key) is not False for key in READINESS_FALSE)
        or base.get("p1_freeze") != P1_FREEZE
        or ledger.get("p1_freeze") != P1_FREEZE
        or pbc.get("p1_freeze") != P1_FREEZE
        or base.get("route_pbc_synchronization_pending_task_ids") != []
        or len(base.get("source_roster", [])) != 37
        or len(port.get("sources", [])) != 41
        or port["sources"][:37] != base["source_roster"]
        or [row["source"] for row in port["sources"][-4:]]
        != ["eng005operating", "govoversight", "legprovision", "dat002rights"]
        or (
            port.get("source_count"),
            port.get("native_versions"),
            port.get("source_component_count"),
        )
        != (41, 948, 42)
        or candidate.get("reviewed_native_versions") != 948
        or candidate.get("portfolio_verifier_sha256") != port.get("verifier_module_sha256")
        or len(ledger.get("rows", [])) != 566
        or len(pbc.get("rows", [])) != 242
        or len(pbc.get("request_groups", [])) != 30
        or len(pbc.get("group_delta", [])) != 30
    ):
        raise GateError("Reviewed source, route, PBC or V5 blocked prefix differs")
    for side in "AB":
        selected = candidate["sides"][side]
        suffix = selected.get("source_pins", [])[-4:]
        if (
            base["sides"][side] != BASE_SIDE
            or len(base["candidate_source_pins"][side]) != 38
            or selected.get("source_pins", [])[:38] != base["candidate_source_pins"][side]
            or len(selected["source_pins"]) != 42
            or [pin["source"] for pin in suffix]
            != ["eng005operating", "govoversight", "legprovision", "dat002rights"]
            or suffix[-2]["source_review_sha256"] != portfolio.SOURCES[0]["review_sha"]
            or suffix[-1]["source_review_sha256"] != portfolio.SOURCES[1]["review_sha"]
            or (
                selected["component_count"],
                selected["source_cohort_count"],
                selected["scenario_source_component_count"],
                selected["system_alias_count"],
            )
            != (55, 41, 42, 353 if side == "A" else 354)
            or selected.get("source_complete") is not False
        ):
            raise GateError(f"{side}: V18 candidate prefix/counts differ")
    blockers = deepcopy(base["blockers_by_family_control"])
    if sum(map(len, blockers.values())) != 43:
        raise GateError("Exact V5 43-control blocker map differs")
    route_index = {(row["side"], row["task_id"]): row for row in ledger["rows"]}
    pbc_index = {(row["side"], row["task_id"]): row for row in pbc["rows"]}
    if len(route_index) != 566 or len(pbc_index) != 242:
        raise GateError("Duplicate route or PBC row key")
    old_classes, old_targets, old_unsupported = {}, set(), set()
    for controls in blockers.values():
        for item in controls.values():
            if item["route_pbc_sync_pending_task_ids"]:
                raise GateError("V5 route/PBC synchronization reappeared")
            old_targets.update(item["targeted_task_ids"])
            old_unsupported.update(item["unsupported_task_ids"])
            for kind, key in (
                ("SOURCE_CANDIDATE_PARTIAL", "partial_task_ids"),
                ("DESIGN_CONTEXT_ONLY", "design_task_ids"),
                ("UNSUPPORTED_EXACT_CLAUSE", "unsupported_task_ids"),
            ):
                old_classes.update({task: kind for task in item[key]})
    if len(old_classes) != 566 or len(old_targets) != 366 or len(old_unsupported) != 242:
        raise GateError("V5 task blocker membership differs")
    new_keys, new_by_source = set(), Counter()
    for (side, task), row in route_index.items():
        key = f"{side}:{task}"
        family, control = row["family"], row["control_id"]
        if family not in blockers or control not in blockers[family]:
            raise GateError(f"{key}: V5 family/control identity differs")
        item = blockers[family][control]
        if key not in item["route_limits"] or key not in item["remaining_gates"]:
            raise GateError(f"{key}: V5 blocker task missing")
        limit = item["route_limits"][key]
        source_ids = row["v17_reviewed_source_ids"]
        if source_ids:
            new_keys.add(key)
            new_by_source[source_ids[0]] += 1
        expected_targets = source_ids if source_ids else limit["targeted_source_ids"]
        if (
            old_classes[key] != row["classification"]
            or item["remaining_gates"][key] != row["remaining_test_gate"]
            or limit["source_limit"] != row["source_limit"]
            or limit["candidate_or_design_source_ids"] != row["candidate_or_design_source_ids"]
            or limit["v16_source_limits"] != row["v16_source_limits"]
            or limit["v16_source_record_refs"] != row["v16_source_record_refs"]
            or row["targeted_integrated_source_ids"] != expected_targets
            or (
                row["current_status"],
                row["current_conclusion"],
                row["audit_task_credit"],
                row["actual_operation_eligibility_as_of_packet"],
            )
            != ("NOT_STARTED", "NOT_RUN", False, False)
        ):
            raise GateError(f"{key}: V5 route gate, source prefix or no-credit join differs")
        if source_ids:
            if (
                key in old_targets
                or row["classification"] != "UNSUPPORTED_EXACT_CLAUSE"
                or len(source_ids) != 1
                or source_ids != [DAT_SOURCE if task in DAT_TASKS else LEG_SOURCE]
                or control != ("SH-DAT-002" if task in DAT_TASKS else "SH-LEG-001")
                or set(row["v17_source_limits"]) != set(source_ids)
                or set(row["v17_source_record_refs"]) != set(source_ids)
            ):
                raise GateError(f"{key}: selected unsupported source is not an exact new lead")
            item["targeted_task_ids"].append(key)
        elif row["v17_source_limits"] or row["v17_source_record_refs"]:
            raise GateError(f"{key}: unselected V17 native refs appeared")
        limit.update(
            targeted_source_ids=expected_targets,
            v17_source_limits=row["v17_source_limits"],
            v17_source_record_refs=row["v17_source_record_refs"],
        )
        request = pbc_index.get((side, task))
        if row["classification"] == "UNSUPPORTED_EXACT_CLAUSE":
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
            if any(row[left] != request[right] for left, right in comparisons.items()):
                raise GateError(f"{key}: route/PBC authored clause join differs")
            if (
                request["pbc_request_status"] != "DRAFT_NOT_SENT"
                or request["task_credit"] is not False
                or request["accepted_nonoccurrence_status"] == "ACCEPTED"
                or request["v14_reviewed_source_ids"] != limit["pbc_v14_reviewed_source_ids"]
                or request["v14_source_limits"] != limit["pbc_v14_source_limits"]
                or request["v14_source_record_refs"] != limit["pbc_v14_source_record_refs"]
                or request["v15_reviewed_source_ids"] != source_ids
                or request["v15_source_limits"] != row["v17_source_limits"]
                or request["v15_source_record_refs"] != row["v17_source_record_refs"]
                or request["v15_targeted_source_ids"] != expected_targets
                or request["v15_next_action_changed_from_v14"] is not bool(source_ids)
                or (not source_ids and request["v15_next_action"] != request["v14_next_action"])
            ):
                raise GateError(f"{key}: reviewed V17/V15 source or draft join differs")
            limit.update(
                pbc_v15_reviewed_source_ids=request["v15_reviewed_source_ids"],
                pbc_v15_targeted_source_ids=request["v15_targeted_source_ids"],
                pbc_v15_source_limits=request["v15_source_limits"],
                pbc_v15_source_record_refs=request["v15_source_record_refs"],
            )
        elif request is not None:
            raise GateError(f"{key}: nonunsupported route gained a PBC row")
    if (
        set(pbc_index)
        != {
            (row["side"], row["task_id"])
            for row in ledger["rows"]
            if row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
        }
        or len(new_keys) != 36
        or new_by_source != {DAT_SOURCE: 4, LEG_SOURCE: 32}
    ):
        raise GateError("Exact 18 paired LEG/DAT authored leads differ")
    for side in "AB":
        side_new = {key for key in new_keys if key.startswith(f"{side}:")}
        if len(side_new) != 18 or {
            key for key in side_new if key.split(":", 1)[1] in DAT_TASKS
        } != {f"{side}:{task}" for task in DAT_TASKS}:
            raise GateError(f"{side}: exact two DAT plus sixteen LEG new task IDs differ")
        side_routes = [row for row in ledger["rows"] if row["side"] == side]
        side_pbc = [row for row in pbc["rows"] if row["side"] == side]
        classes = Counter(row["classification"] for row in side_routes)
        affected = sum(
            any(row[f"v{version}_reviewed_source_ids"] for version in range(5, 16))
            for row in side_pbc
        )
        if (
            len(side_routes) != 283
            or len(side_pbc) != 121
            or classes
            != {
                "SOURCE_CANDIDATE_PARTIAL": 141,
                "DESIGN_CONTEXT_ONLY": 21,
                "UNSUPPORTED_EXACT_CLAUSE": 121,
            }
            or sum(bool(row["targeted_integrated_source_ids"]) for row in side_routes) != 201
            or sum(
                bool(row["targeted_integrated_source_ids"])
                for row in side_routes
                if row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
            )
            != 55
            or sum(bool(row["v15_targeted_source_ids"]) for row in side_pbc) != 55
            or affected != 47
            or sum(row["possible_nonoccurrence_review_candidate"] for row in side_pbc) != 53
            or pbc["counts"][side]["v15_cumulative_targeted_unsupported_clauses"] != 55
            or pbc["counts"][side]["v15_cumulative_reviewed_source_affected_unsupported_clauses"]
            != 47
            or ledger["counts"][side]["targeted_integrated_route_count"] != 201
            or ledger["active_p1_tasks"][side]
            != {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"}
            or pbc["active_p1_tasks"][side]
            != {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"}
        ):
            raise GateError(f"{side}: V18 route/PBC/P1 denominator differs")
    if sum(map(len, blockers.values())) != 43:
        raise GateError("Exact 43 blocked controls changed")
    for controls in blockers.values():
        for item in controls.values():
            item["targeted_task_ids"].sort()
            if item["route_pbc_sync_pending_task_ids"]:
                raise GateError("Route/PBC synchronization gap reappeared")
    base_groups = {group["request_group_id"]: group for group in base["request_groups"]}
    groups = []
    changed_groups = set()
    for group in pbc["request_groups"]:
        name = group["request_group_id"]
        if name not in base_groups:
            raise GateError("V5 request group roster differs")
        previous = base_groups[name]
        changed = name in SELECTED_GROUPS
        if (
            group["control_id"] != previous["control_id"]
            or group["task_ids_per_side"] != previous["task_ids_per_side"]
            or group["request_status"] != previous["status"]
            or group["task_credit"] is not False
            or group["v14_next_action"] != previous["next_action"]
            or any(group[key] != value for key, value in previous.items() if key.startswith("v"))
            or group["v15_next_action_changed_from_v14"] is not changed
            or bool(group["v15_reviewed_source_ids"]) is not changed
            or (not changed and group["v15_next_action"] != group["v14_next_action"])
        ):
            raise GateError(f"{name}: V5 request prefix or V15 draft action differs")
        for side in "AB":
            expected_refs = {
                task: pbc_index[side, task]["v15_source_record_refs"]
                for task in group["task_ids_per_side"][side]
                if pbc_index[side, task]["v15_reviewed_source_ids"]
            }
            if group["v15_source_record_refs_by_side"][side] != expected_refs:
                raise GateError(f"{name}: selected group native refs differ")
        if changed:
            changed_groups.add(name)
        groups.append(
            {
                **previous,
                "next_action": group["v15_next_action"],
                **{key: value for key, value in group.items() if key.startswith("v15_")},
            }
        )
    if (
        len(groups) != 30
        or set(base_groups) != {group["request_group_id"] for group in groups}
        or changed_groups != SELECTED_GROUPS
    ):
        raise GateError("Exact two draft group changes differ")
    side_counts = deepcopy(base["sides"])
    for side in "AB":
        side_counts[side].update(
            source_cohorts=41,
            native_business_versions=948,
            targeted_routes=201,
            route_targeted_unsupported_clauses=55,
            pbc_targeted_unsupported_clauses=55,
            source_affected_unsupported_clauses=47,
        )
        if (
            side_counts[side]["unsupported_exact_clauses"] != 121
            or side_counts[side]["draft_unsent_request_groups"] != 30
            or side_counts[side]["unaccepted_no_event_candidates"] != 53
            or side_counts[side]["p1_tasks_not_started_not_run"] != 409
        ):
            raise GateError(f"{side}: frozen blocker denominator differs")
    result = deepcopy(base)
    result.update(
        schema=SCHEMA,
        as_of="2026-10-01",
        pins={
            **base["pins"],
            **{
                key: {"scope": scope, "path": relative, "sha256": sha}
                for key, (scope, relative, sha) in PINS.items()
            },
        },
        sides=side_counts,
        source_roster=port["sources"],
        candidate_source_pins={side: candidate["sides"][side]["source_pins"] for side in "AB"},
        request_groups=groups,
        blockers_by_family_control=blockers,
        route_pbc_synchronization_pending_task_ids=[],
        boundary_limits={
            **base["boundary_limits"],
            "portfolio_v18": port["limits"],
            "candidate_v18": candidate["limits"],
            "route_v17": ledger["limits"],
            "requests_v15": pbc["limits"],
        },
        readiness_blockers=[*base["readiness_blockers"], *NEW_BLOCKERS],
    )
    if (
        any(result[key] is not False for key in READINESS_FALSE)
        or result["external_messages_sent"] != 0
        or result["accepted_na_determinations"] != 0
        or result["p1_freeze"] != P1_FREEZE
    ):
        raise GateError("V6 readiness or frozen pair unexpectedly promoted")
    return result


def build(repository: Path, private_repository: Path) -> dict:
    """Read pinned reviewed snapshots only; never run predecessor builders."""
    _reject_symlink_chain(private_repository)
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    if _p1_inventory(private) != P1_FREEZE:
        raise GateError("Frozen P1 inventory differs")
    data, identities = _load_pins(repository, private)
    result = _assemble(*_assert_review_boundaries(data))
    after, after_ids = _load_pins(repository, private)
    if (after, after_ids) != (data, identities) or _p1_inventory(private) != P1_FREEZE:
        raise GateError("Pinned snapshots or frozen P1 changed during read-only gate")
    return result


def markdown(report: dict) -> str:
    counts = report["sides"]["A"]
    lines = [
        "# Fictional audit readiness gate V6",
        "",
        "**Blocked.** Reviewed LEG provision and DAT rights discovery leads are routed to "
        "draft requests, but no authored clause or frozen task has been tested.",
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
        "All 43 controls retain blockers. LEG legal status and 2027 law remain open; "
        "DAT is one synthetic inquiry with no actual request, response or complete record "
        "population. The Messy historical and scope exceptions remain open.",
        "",
        "`source_complete=false`; `fresh_pair_eligible=false`; `audit_ready=false`. "
        "No N/A decision, external request, collection, task credit, Key or grade was issued.",
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
    _reject_symlink_chain(destination)
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
        raise GateError("Gate output differs from pinned reviewed snapshots")
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
