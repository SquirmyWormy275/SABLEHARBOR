"""Read-only physical-site successor for the frozen unsupported PBC requests."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from . import documentary_283_route_reconciliation_v7 as routes_v7
from . import unsupported_121_pbc_plan as pinned
from . import unsupported_121_pbc_plan_v6 as prior

SCHEMA = "SH_UNSUPPORTED_121_PAIRED_SOURCE_REQUEST_PLAN_V7"
V6_PLAN = "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V6_2026-09-30.json"
V6_REVIEW = (
    "enterprise/generated/audit-suite/unsupported-121-pbc-plan-v6-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
V7_LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V7_2026-09-30.json"
V7_REVIEW = (
    "enterprise/generated/audit-suite/documentary-283-route-reconciliation-v7-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
PINS = {
    V6_PLAN: "cca9d32fa2937b88a5d1580d967a4a2c14ae531304eb5732107a218956a3a538",
    V6_REVIEW: "fd55f8be206919dee519e7147554c6f8e4e43f7485d042138b4bd10592108fdd",
    V7_LEDGER: "a72d462a7b677bea6be6463b7fc91f48359c2c4b2abf878c9e92f3e7a52197c9",
    V7_REVIEW: "c4405c5e5a5daa73c5d6936ce2b55327b65b3b0bcaad608bd0b9ab1a49108d90",
}
P1_FREEZE = {
    "file_count": 538,
    "inventory_sha256": "f266ef682b502b3b093170f8a7b64fcf5cbab722d5c8ddf6715a63c0e535360f",
}
SOURCE = routes_v7.SOURCE
NEW_SOURCE_TASKS = {
    "TASK-SH-SEC-001-corporate-CHECK-SOC2:A1.2",
    "TASK-SH-SEC-001-corporate-CHECK-SOC2:CC6.4",
}
NEW_SOURCE_GROUP = "SH-SEC-001"
NEXT_ACTION = (
    "Inspect the selected SEC003 four-asset fictional vulnerability history only "
    "for CC5.2 and the selected Reno/Boise two-cage physical history only for "
    "CC6.4/A1.2. Preserve both October false-clean histories, the unescorted "
    "expired entry, the open Messy historical exceptions and AS-P008 management "
    "self-review limit. Request complete deployed Reno, Boise and provider "
    "building-perimeter access, badge/visitor and environmental populations, "
    "site-failure recovery proof, original architecture and other-clause records, "
    "and qualified independent challenge."
)


class V7SourceRequestError(prior.V6SourceRequestError):
    """A reviewed source, unsupported clause, or frozen request changed."""


def build(repository: Path, private_repository: Path) -> dict:
    """Reperform reviewed PBC V6 and route V7, then add two exact physical leads."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    p1_before = routes_v7.prior._p1_inventory(private)
    if p1_before != P1_FREEZE:
        raise V7SourceRequestError("Frozen P1 inventory differs")
    old_pinned = pinned._pinned(repository / V6_PLAN, PINS[V6_PLAN])
    old_review = pinned._pinned(private / V6_REVIEW, PINS[V6_REVIEW], private=True)
    ledger_pinned = pinned._pinned(repository / V7_LEDGER, PINS[V7_LEDGER])
    route_review = pinned._pinned(private / V7_REVIEW, PINS[V7_REVIEW], private=True)
    if (
        old_review.get("verdict")
        != "PASS_READ_ONLY_UNSUPPORTED_CLAUSE_REQUEST_DELTA_NO_AUDIT_CREDIT"
        or old_review.get("sha256", {}).get("tracked_json") != PINS[V6_PLAN]
        or old_review.get("p1_freeze") != P1_FREEZE
        or old_review.get("audit_task_credit") is not False
        or old_review.get("active_pair_mutated") is not False
        or route_review.get("verdict")
        != "PASS_READ_ONLY_PARTIAL_PHYSICAL_ROUTE_RECONCILIATION_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or route_review.get("main_tracked_sha256", {}).get(V7_LEDGER) != PINS[V7_LEDGER]
        or route_review.get("p1_freeze") != P1_FREEZE
        or route_review.get("audit_task_credit") is not False
        or route_review.get("active_pair_mutated") is not False
    ):
        raise V7SourceRequestError("Independent PBC V6/route V7 review join differs")
    old = prior.build(repository, private)
    ledger = routes_v7.build(repository, private)
    if old != old_pinned or ledger != ledger_pinned:
        raise V7SourceRequestError("Reviewed PBC or route ledger does not reproduce")
    if (
        old["counts"]["A"] != old["counts"]["B"]
        or old["counts"]["A"]["unsupported_exact_clauses"] != 121
        or old["counts"]["A"]["possible_nonoccurrence_review_candidates"] != 53
        or old["counts"]["A"]["v6_cumulative_source_affected_unsupported_clauses"] != 17
        or old["counts"]["A"]["v6_cumulative_targeted_unsupported_clauses"] != 29
        or old["counts"]["A"]["next_action_changes"] != 6
        or old["counts"]["A"]["v6_next_action_changes_from_v5"] != 3
        or len(old["request_groups"]) != 30
        or len(old["group_delta"]) != 30
        or ledger["p1_freeze"] != P1_FREEZE
        or ledger["audit_task_credit"] is not False
        or ledger["active_pair_mutated"] is not False
        or any(
            ledger["active_p1_tasks"][side]
            != {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"}
            for side in "AB"
        )
    ):
        raise V7SourceRequestError("Frozen request or route denominator differs")
    routes = {
        (row["side"], row["task_id"]): row
        for row in ledger["rows"]
        if row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
    }
    old_rows = {(row["side"], row["task_id"]): row for row in old["rows"]}
    if len(routes) != 242 or len(old_rows) != 242 or set(routes) != set(old_rows):
        raise V7SourceRequestError("Exact unsupported task identity differs")
    rows = []
    group_leads = {group["request_group_id"]: set() for group in old["request_groups"]}
    group_limits = {group["request_group_id"]: {} for group in old["request_groups"]}
    for previous in old["rows"]:
        row = dict(previous)
        side, task_id = row["side"], row["task_id"]
        source = routes[side, task_id]
        group = row["request_group_id"]
        leads = list(source["v7_reviewed_source_ids"])
        expected = [SOURCE] if task_id in NEW_SOURCE_TASKS else []
        if (
            leads != expected
            or (task_id in NEW_SOURCE_TASKS and group != NEW_SOURCE_GROUP)
            or source["control_id"] != row["control_id"]
            or source["authored_test_clause"] != row["authored_test_clause"]
            or source["remaining_test_gate"] != row["remaining_test_gate"]
            or source["requirement_ids"] != row["requirement_ids"]
            or source["screen_row_sha256"] != row["screen_row_sha256"]
            or source["source_limit"] != row["v3_source_limit"]
            or source["v5_reviewed_source_ids"] != row["v5_reviewed_source_ids"]
            or source["v5_source_limits"] != row["v5_source_limits"]
            or source["v6_reviewed_source_ids"] != row["v6_reviewed_source_ids"]
            or source["v6_source_limits"] != row["v6_source_limits"]
            or set(source["targeted_integrated_source_ids"])
            != set(row["v6_targeted_source_ids"]) | set(leads)
            or set(source["v7_source_limits"]) != set(leads)
            or source["current_status"] != row["current_task_status"]
            or source["current_conclusion"] != row["current_task_conclusion"]
            or source["actual_operation_eligibility_as_of_packet"] is not False
            or source["audit_task_credit"] is not False
            or not row["authored_test_clause"]
            or row["pbc_request_status"] != "DRAFT_NOT_SENT"
            or row["task_credit"] is not False
            or row["accepted_nonoccurrence_status"] == "ACCEPTED"
        ):
            raise V7SourceRequestError(f"Unsupported V7 clause/source drift: {(side, task_id)}")
        group_leads[group].update(leads)
        for lead in leads:
            limit = source["v7_source_limits"][lead]
            if lead in group_limits[group] and group_limits[group][lead] != limit:
                raise V7SourceRequestError("Paired selected physical limit differs")
            group_limits[group][lead] = limit
        row["v7_reviewed_source_ids"] = leads
        row["v7_source_limits"] = source["v7_source_limits"]
        row["v7_targeted_source_ids"] = source["targeted_integrated_source_ids"]
        row["v7_next_action"] = NEXT_ACTION if group == NEW_SOURCE_GROUP else row["v6_next_action"]
        row["v7_next_action_changed_from_v6"] = group == NEW_SOURCE_GROUP
        rows.append(row)
    if {group for group, leads in group_leads.items() if leads} != {NEW_SOURCE_GROUP}:
        raise V7SourceRequestError("Exact physical source-affected group differs")
    groups = []
    deltas = []
    for previous, previous_delta in zip(old["request_groups"], old["group_delta"], strict=True):
        group = dict(previous)
        delta = dict(previous_delta)
        group_id = group["request_group_id"]
        leads = sorted(group_leads[group_id])
        if (
            delta["request_group_id"] != group_id
            or leads != ([SOURCE] if group_id == NEW_SOURCE_GROUP else [])
            or (group_id == NEW_SOURCE_GROUP and not group["v6_next_action_changed_from_v5"])
        ):
            raise V7SourceRequestError("Historical group or physical source join differs")
        next_action = NEXT_ACTION if group_id == NEW_SOURCE_GROUP else group["v6_next_action"]
        group["v7_reviewed_source_ids"] = leads
        group["v7_source_limits"] = group_limits[group_id]
        group["v7_next_action"] = next_action
        group["v7_next_action_changed_from_v6"] = group_id == NEW_SOURCE_GROUP
        delta.update(
            {
                "v7_reviewed_source_ids": leads,
                "v7_source_limits": group_limits[group_id],
                "v6_next_action_before_v7": previous["v6_next_action"],
                "v7_next_action": next_action,
                "v7_next_action_changed_from_v6": group_id == NEW_SOURCE_GROUP,
            }
        )
        groups.append(group)
        deltas.append(delta)
    counts = {}
    for side in "AB":
        selected = [row for row in rows if row["side"] == side]
        legal = [row for row in selected if row["control_id"] == "SH-LEG-001"]
        if (
            len(selected) != 121
            or len({row["task_id"] for row in selected}) != 121
            or len({row["control_id"] for row in selected}) != 28
            or Counter(row["request_group_id"] for row in legal)
            != {"SH-LEG-001/PROVISION": 16, "SH-LEG-001/CONTEXT": 4, "SH-LEG-001/MATTER": 46}
            or sum(row["possible_nonoccurrence_review_candidate"] for row in selected) != 53
            or sum(bool(row["v7_reviewed_source_ids"]) for row in selected) != 2
            or sum(
                bool(
                    row["v5_reviewed_source_ids"]
                    or row["v6_reviewed_source_ids"]
                    or row["v7_reviewed_source_ids"]
                )
                for row in selected
            )
            != 19
            or sum(bool(row["v7_targeted_source_ids"]) for row in selected) != 31
            or any(
                row["accepted_nonoccurrence_status"] != "NOT_ESTABLISHED"
                for row in selected
                if row["possible_nonoccurrence_review_candidate"]
            )
        ):
            raise V7SourceRequestError("V7 unsupported/LEGAL/no-event split differs")
        counts[side] = {
            **old["counts"][side],
            "v7_new_physical_source_affected_unsupported_clauses": 2,
            "v7_new_source_affected_request_groups": 1,
            "v7_next_action_changes_from_v6": 1,
            "v7_cumulative_reviewed_source_affected_unsupported_clauses": 19,
            "v7_cumulative_targeted_unsupported_clauses": 31,
            "v7_cumulative_changed_request_groups": 9,
            "v7_grouping_or_contact_changes": 0,
        }
    if (
        counts["A"] != counts["B"]
        or len(groups) != 30
        or len({group["request_group_id"] for group in groups}) != 30
        or sum(delta["next_action_changed"] for delta in deltas) != 6
        or sum(delta["v6_next_action_changed_from_v5"] for delta in deltas) != 3
        or sum(delta["v7_next_action_changed_from_v6"] for delta in deltas) != 1
        or routes_v7.prior._p1_inventory(private) != p1_before
    ):
        raise V7SourceRequestError("Paired request delta or frozen P1 differs")
    return {
        "schema": SCHEMA,
        "as_of": "2026-09-30",
        "source_pins": PINS,
        "p1_freeze": p1_before,
        "active_p1_tasks": ledger["active_p1_tasks"],
        "reviewed_route_roster": ledger["reviewed_source_roster"],
        "counts": counts,
        "rows": rows,
        "request_groups": groups,
        "group_delta": deltas,
        "candidate_owner_source_queues": old["candidate_owner_source_queues"],
        "nonoccurrence_acceptance_protocol": old["nonoccurrence_acceptance_protocol"],
        "limits": [
            "All V5 and V6 next-action fields remain intact. Only SH-SEC-001 gains a "
            "V7 next action; every group identity, proposed contact, source locator "
            "and original request is unchanged.",
            "The physical lead covers two unsupported authored clauses per side in "
            "one fictional Reno/Boise two-cage history, not provider building "
            "perimeters, complete access/environmental populations or recovery proof.",
            "Messy false closure, unescorted entry and historical exception remain "
            "open; AS-P008's recheck is management self-review, not independent challenge.",
            "All 121 authored clauses remain unsupported and 53 possible no-event "
            "reviews per side remain unaccepted. No N/A or task credit.",
            "No request, external communication, audit task command, collection, "
            "grade, Key or Atlas edit was issued by this read-only plan.",
        ],
        "external_messages_sent": 0,
        "fresh_pair_created": False,
        "audit_task_credit": False,
        "accepted_na_determinations": 0,
        "active_pair_mutated": False,
    }


def markdown(result: dict) -> str:
    """Render the one-group physical-site request delta."""
    counts = result["counts"]["A"]
    group = next(
        group for group in result["request_groups"] if group["request_group_id"] == NEW_SOURCE_GROUP
    )
    lines = [
        "# Unsupported exact clauses: reviewed V7 physical-site request delta",
        "",
        "This read-only successor joins the independently reviewed PBC V6 plan to "
        "the independently reviewed main-local physical-site route V7 ledger. "
        "All 121 unsupported authored clauses per side remain unsupported across "
        "28 controls and 30 draft request groups. The "
        "[paired JSON](UNSUPPORTED_121_PBC_PLAN_V7_2026-09-30.json) retains every "
        "V6 row, group, contact, locator, original request and source limit.",
        "",
        "| Per-side measure | Count |",
        "| --- | ---: |",
        f"| Unsupported authored clauses | {counts['unsupported_exact_clauses']} |",
        "| Possible no-event review candidates | "
        f"{counts['possible_nonoccurrence_review_candidates']} |",
        "| Accepted no-event or N/A decisions | 0 |",
        "| New physical-site leads on unsupported clauses | "
        f"{counts['v7_new_physical_source_affected_unsupported_clauses']} |",
        "| Cumulative reviewed V5/V6/V7 source-affected clauses | "
        f"{counts['v7_cumulative_reviewed_source_affected_unsupported_clauses']} |",
        "| Unsupported clauses with any targeted source lead | "
        f"{counts['v7_cumulative_targeted_unsupported_clauses']} |",
        f"| V5 next-action changes retained | {counts['next_action_changes']} |",
        f"| V6 next-action changes retained | {counts['v6_next_action_changes_from_v5']} |",
        f"| New V7 next-action changes | {counts['v7_next_action_changes_from_v6']} |",
        "| Changed groups, contacts, locators or original requests | 0 |",
        "",
        "Only SH-SEC-001 gains a V7 next action. The physical source attaches "
        "only to its authored CC6.4 and A1.2 clauses per side. The earlier "
        "SEC003 CC5.2 lead and all six V5/three V6 next-action fields remain "
        "as historical text.",
        "",
        "| Request group | New reviewed source lead | V7 next action |",
        "| --- | --- | --- |",
        f"| {NEW_SOURCE_GROUP} | {SOURCE} | {group['v7_next_action']} |",
        "",
        "The selected Reno/Boise two-cage history preserves the Messy false "
        "badge/visitor closure, unescorted expired entry, November self-recheck "
        "and open historical exception. It does not establish provider building "
        "perimeters, full access/environmental populations or site-failure "
        "recovery proof. Qualified independent challenge remains to be sought.",
        "",
        "SH-LEG-001 retains 16 provision/status, four source-context and 46 "
        "conditional matter clauses per side. Its 46 possible no-matter reviews "
        "and seven other possible no-event reviews remain unaccepted. Nothing "
        "becomes N/A.",
        "",
        "All requests remain `DRAFT_NOT_SENT`; zero external messages, audit task "
        "commands or task credit were issued. Both A/B engagements retain 409 "
        "`NOT_STARTED`/`NOT_RUN` tasks and the 538-file P1 inventory is frozen. "
        "The source is fictional future history as of 2026-09-30; no Key, grade "
        "or Atlas write occurred.",
        "",
    ]
    return "\n".join(lines)
