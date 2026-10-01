"""Read-only exact LEG001 authored gap map; never an operating source or audit result."""

from __future__ import annotations

from pathlib import Path

from . import unsupported_121_pbc_plan as pinned

SCHEMA = "SH_LEG001_66_AUTHORED_CANDIDATE_GAP_V1"
LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V16_2026-10-01.json"
PLAN = "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V14_2026-10-01.json"
ROUTE_REVIEW = (
    "enterprise/generated/audit-suite/documentary-283-route-reconciliation-v16-2026-10-01/"
    "independent-review-main-v1/REVIEW.json"
)
PBC_REVIEW = (
    "enterprise/generated/audit-suite/unsupported-121-pbc-plan-v14-2026-10-01/"
    "independent-review-main-v1/REVIEW.json"
)
PINS = {
    LEDGER: "cd3b55409e9e0112b49d060cfbbacf329660422d0c4e1b2002ec220af5bad5a3",
    PLAN: "c414799171d1256222f80675be0e0b4dd5fff45ce5d345f7540cd34f08a905b4",
    ROUTE_REVIEW: "138bc8e7cd5e701d0507e4dcb6228364c3406aa097d12d14d9753c456ae60b34",
    PBC_REVIEW: "2a212e9ff08e9bad9532b4c88c685094251424fbc7bfd973451cadad2801819a",
}
P1_FREEZE = {
    "file_count": 538,
    "inventory_sha256": "f266ef682b502b3b093170f8a7b64fcf5cbab722d5c8ddf6715a63c0e535360f",
}
GROUP_COUNTS = {"SH-LEG-001/PROVISION": 16, "SH-LEG-001/MATTER": 46, "SH-LEG-001/CONTEXT": 4}


class Leg001GapError(ValueError):
    """Reviewed route, PBC, or 66-candidate boundary changed."""


def build(repository: Path, private_repository: Path) -> dict:
    repo = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    ledger = pinned._pinned(repo / LEDGER, PINS[LEDGER])
    plan = pinned._pinned(repo / PLAN, PINS[PLAN])
    route_review = pinned._pinned(private / ROUTE_REVIEW, PINS[ROUTE_REVIEW], private=True)
    pbc_review = pinned._pinned(private / PBC_REVIEW, PINS[PBC_REVIEW], private=True)
    if (
        route_review.get("schema") != "SH_INDEPENDENT_GOV_ROUTE_V16_MAIN_REVIEW_V1"
        or route_review.get("verdict") != "PASS_MAIN_SELECTED_GOV_LEAD_NO_AUDIT_CREDIT"
        or route_review.get("output_sha256", {}).get("LEDGER.json") != PINS[LEDGER]
        or pbc_review.get("schema") != "SH_INDEPENDENT_GOV_PBC_V14_MAIN_REVIEW_V1"
        or pbc_review.get("verdict") != "PASS_MAIN_DRAFT_ONLY_NO_AUDIT_CREDIT"
        or pbc_review.get("output_sha256", {}).get("PLAN.json") != PINS[PLAN]
        or any(
            review.get("p1_freeze") != P1_FREEZE
            or review.get("audit_task_credit") is not False
            or review.get("source_complete") is not False
            or review.get("fresh_audit_pair_created") is not False
            for review in (route_review, pbc_review)
        )
        or ledger.get("as_of") != "2026-10-01"
        or plan.get("as_of") != "2026-10-01"
        or ledger.get("p1_freeze") != P1_FREEZE
        or plan.get("p1_freeze") != P1_FREEZE
        or ledger.get("audit_task_credit") is not False
        or plan.get("audit_task_credit") is not False
    ):
        raise Leg001GapError("Reviewed LEG001 route/PBC join differs")
    group_by_task = {}
    for group in plan["request_groups"]:
        if group["request_group_id"] not in GROUP_COUNTS:
            continue
        if (
            group["routes_per_side"] != GROUP_COUNTS[group["request_group_id"]]
            or group["request_status"] != "DRAFT_NOT_SENT"
            or group["task_credit"] is not False
        ):
            raise Leg001GapError("LEG001 request group denominator or unsent gate differs")
        for side in "AB":
            for task in group["task_ids_per_side"][side]:
                key = side, task
                if key in group_by_task:
                    raise Leg001GapError("LEG001 task duplicated across groups")
                group_by_task[key] = group["request_group_id"]
    result = {}
    for side in "AB":
        routes = [
            row
            for row in ledger["rows"]
            if row["side"] == side and row["control_id"] == "SH-LEG-001"
        ]
        unsupported = [row for row in routes if row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"]
        pbc_rows = {
            row["task_id"]: row
            for row in plan["rows"]
            if row["side"] == side and row["control_id"] == "SH-LEG-001"
        }
        if (
            len(routes) != 72
            or len(unsupported) != 66
            or len(pbc_rows) != 66
            or {row["task_id"] for row in unsupported} != set(pbc_rows)
            or {task for branch, task in group_by_task if branch == side} != set(pbc_rows)
            or plan["active_p1_tasks"][side]
            != {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"}
        ):
            raise Leg001GapError("Exact 72/66 LEG001 or 409 P1 denominator differs")
        rows = []
        for route in unsupported:
            task = route["task_id"]
            pbc = pbc_rows[task]
            group = group_by_task[side, task]
            if (
                route["test_gate_basis"] != "AUTHORED_TASK_CLAUSE"
                or route["current_status"] != "NOT_STARTED"
                or route["current_conclusion"] != "NOT_RUN"
                or route["audit_task_credit"] is not False
                or pbc["request_group_id"] != group
                or pbc["pbc_request_status"] != "DRAFT_NOT_SENT"
                or pbc["task_credit"] is not False
            ):
                raise Leg001GapError("LEG001 authored route/request no-credit boundary differs")
            rows.append(
                {
                    "task_id": task,
                    "requirement_ids": route["requirement_ids"],
                    "authored_test_clause": route["authored_test_clause"],
                    "request_group_id": group,
                    "v16_existing_targeted_source_ids": route["targeted_integrated_source_ids"],
                    "new_overlay_cohort": group == "SH-LEG-001/PROVISION",
                    "new_overlay_status": (
                        "SELECTED_NATIVE_LOCATOR_CANDIDATE_NOT_ROUTED"
                        if group == "SH-LEG-001/PROVISION"
                        else "NO_NEW_NATIVE_LEAD_IN_THIS_ITERATION"
                    ),
                    "classification": "UNSUPPORTED_EXACT_CLAUSE",
                    "current_status": "NOT_STARTED",
                    "current_conclusion": "NOT_RUN",
                    "audit_task_credit": False,
                }
            )
        if (
            sum(row["new_overlay_cohort"] for row in rows) != 16
            or sum(not row["new_overlay_cohort"] for row in rows) != 50
            or {name: sum(row["request_group_id"] == name for row in rows) for name in GROUP_COUNTS}
            != GROUP_COUNTS
        ):
            raise Leg001GapError("Exact LEG001 provision/matter/context partition differs")
        result[side] = rows
    if [row["task_id"] for row in result["A"]] != [row["task_id"] for row in result["B"]]:
        raise Leg001GapError("LEG001 side task inventory differs")
    return {
        "schema": SCHEMA,
        "as_of": "2026-10-01",
        "truth_class": "DERIVED_READ_ONLY_GAP_MAP_NOT_COMPANY_SOURCE",
        "source_pins": PINS,
        "p1_freeze": P1_FREEZE,
        "counts_per_side": {
            "authored_routes": 72,
            "unsupported_exact_clauses": 66,
            "bounded_provision_candidates": 16,
            "remaining_matter_candidates": 46,
            "remaining_context_candidates": 4,
            "unmodeled_in_this_iteration": 50,
            "active_p1_tasks_unrun": 409,
        },
        "rows_by_side": result,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": [
            "This inventory maps audit task IDs to exact authored clauses and requirement IDs; "
            "it is not a company-native operating record or an audit test.",
            "The 16-provision native overlay is a selected source candidate outside the "
            "current route ledger; separate route and procedure reviews remain, and all "
            "66 clauses remain unsupported/unrun.",
            "The 46 matter and four context candidates remain outside this source cohort. "
            "No outside matter or all-company no-event determination is inferred.",
        ],
    }


def markdown(result: dict) -> str:
    """Show all exact tasks once; JSON preserves both branch rows and clauses."""
    lines = [
        "# SH-LEG-001: exact 66 unsupported authored candidates",
        "",
        "As of 2026-10-01, each branch has 72 authored routes: 66 unsupported exact "
        "clauses, three design-context and three source-candidate routes. This read-only "
        "gap map inventories the exact 66 task IDs and requirement references; it is "
        "not company-native evidence or an audit result.",
        "",
        "The new fictional counsel overlay is bounded to the 16 PROVISION "
        "candidates. The 46 MATTER and four CONTEXT candidates still lack a new "
        "source in this iteration. Every clause remains unsupported, every P1 task "
        "NOT_STARTED/NOT_RUN, and all requests DRAFT_NOT_SENT.",
        "",
        "| Task ID | Requirement references | Group | New overlay |",
        "| --- | --- | --- | --- |",
    ]
    for row in result["rows_by_side"]["A"]:
        lines.append(
            f"| {row['task_id']} | {', '.join(row['requirement_ids'])} | "
            f"{row['request_group_id']} | "
            f"{'locator candidate only' if row['new_overlay_cohort'] else 'none'} |"
        )
    lines.extend(
        [
            "",
            "Source locator, applicable legal status, triggering facts, no-event conclusion, "
            "contract terms and operating performance are separate decisions. The 2026 "
            "primary-reference snapshot does not establish fictional 2027 law or real "
            "HIPAA status. The visible eCFR §164.509 text and HHS's partial-vacatur "
            "notice require qualified reconciliation before any applicability decision.",
            "",
            "No outside response, accepted N/A, clause satisfaction, audit task credit, "
            "fresh pair or Atlas write is claimed.",
            "",
        ]
    )
    return "\n".join(lines)
