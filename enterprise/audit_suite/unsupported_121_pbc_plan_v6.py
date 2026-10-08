"""Read-only V6 source-request delta for the frozen unsupported clauses."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from . import documentary_283_route_reconciliation_v6 as routes_v6
from . import unsupported_121_pbc_plan as pinned
from . import unsupported_121_pbc_plan_v5 as prior

SCHEMA = "SH_UNSUPPORTED_121_PAIRED_SOURCE_REQUEST_PLAN_V6"
V5_PLAN = "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V5_2026-09-30.json"
V5_REVIEW = (
    "enterprise/generated/audit-suite/unsupported-121-pbc-plan-v5-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
V6_LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V6_2026-09-30.json"
V6_REVIEW = (
    "enterprise/generated/audit-suite/documentary-283-route-reconciliation-v6-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
PINS = {
    V5_PLAN: "07569fd5636b3318e5dcd95f8c5409fba993bd78818ec2eedc61b30666381cdc",
    V5_REVIEW: "8bf8dbcdb3a4b0c0603bba00ba235a44ecbfc6c1a6e1b8d4cefd55c0ef8f97ca",
    V6_LEDGER: "45a88eb3b82a20d2be417a1f301f6103087748d721c392edcc24a476a77e5dfe",
    V6_REVIEW: "fe373c67bc5938a3263a1bcc85b51b1be55352748a1c3bee379d0b01a233d751",
}
P1_FREEZE = {
    "file_count": 538,
    "inventory_sha256": "f266ef682b502b3b093170f8a7b64fcf5cbab722d5c8ddf6715a63c0e535360f",
}
NEW_SOURCE_TASKS = {
    "TASK-SH-IAM-005-corporate-ACTION-H-EMERGENCY": routes_v6.IAM_SOURCE,
    "TASK-SH-IAM-005-corporate-CHECK-SOC2:CC6.1": routes_v6.IAM_SOURCE,
    "TASK-SH-SEC-001-corporate-CHECK-SOC2:CC5.2": routes_v6.SEC_SOURCE,
    "TASK-SH-SEC-003-corporate-CHECK-SOC2:CC7.1": routes_v6.SEC_SOURCE,
}
NEW_SOURCE_GROUPS = {
    "SH-IAM-005": (routes_v6.IAM_SOURCE,),
    "SH-SEC-001": (routes_v6.SEC_SOURCE,),
    "SH-SEC-003": (routes_v6.SEC_SOURCE,),
}
NEXT_ACTION = {
    "SH-IAM-005": (
        "Inspect the one fictional Boise human/inert-service marker and preserve the "
        "open Messy BCM and SEC005 exceptions; then request authorized deployed ePHI "
        "emergency access, protected credentials, the full trust-boundary population, "
        "operation logs and independent review."
    ),
    "SH-SEC-001": (
        "Inspect the selected four-asset fictional vulnerability history only as a "
        "CC5.2 risk-to-control lead, retaining the October false-clean sign-off and "
        "open missed-coverage exception; then request deployed two-site architecture, "
        "complete asset/control populations and independent challenge, alongside "
        "the original requests for the other seven clauses."
    ),
    "SH-SEC-003": (
        "Inspect the selected four-asset fictional scan, triage, correction and retest "
        "history, preserving the October 3/4 false-clean sign-off, open missed-coverage "
        "exception and AS-P008 November self-review; then request the complete "
        "asset/baseline/scan population, scanner execution, independent reconciliation "
        "and retest for CC7.1."
    ),
}


class V6SourceRequestError(prior.V5SourceRequestError):
    """A reviewed source, unsupported clause or frozen request changed."""


def build(repository: Path, private_repository: Path) -> dict:
    """Reperform V5 and reviewed route V6 before adding four selected leads per side."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    p1_before = routes_v6._p1_inventory(private)
    if p1_before != P1_FREEZE:
        raise V6SourceRequestError("Frozen P1 inventory differs")
    old_pinned = pinned._pinned(repository / V5_PLAN, PINS[V5_PLAN])
    old_review = pinned._pinned(private / V5_REVIEW, PINS[V5_REVIEW], private=True)
    ledger_pinned = pinned._pinned(repository / V6_LEDGER, PINS[V6_LEDGER])
    route_review = pinned._pinned(private / V6_REVIEW, PINS[V6_REVIEW], private=True)
    if (
        old_review.get("verdict")
        != "PASS_READ_ONLY_UNSUPPORTED_CLAUSE_REQUEST_DELTA_NO_AUDIT_CREDIT"
        or old_review.get("sha256", {}).get("tracked_json") != PINS[V5_PLAN]
        or old_review.get("checks", {}).get("tracked_main_files_mutated_by_review") is not False
        or route_review.get("verdict")
        != "PASS_READ_ONLY_PARTIAL_ROUTE_RECONCILIATION_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or route_review.get("main_tracked_sha256", {}).get(V6_LEDGER) != PINS[V6_LEDGER]
        or route_review.get("p1_freeze") != P1_FREEZE
        or route_review.get("audit_task_credit") is not False
        or route_review.get("active_pair_mutated") is not False
    ):
        raise V6SourceRequestError("Independent V5 PBC/V6 route review join differs")
    old = prior.build(repository, private)
    ledger = routes_v6.build(repository, private)
    if old != old_pinned or ledger != ledger_pinned:
        raise V6SourceRequestError("Reviewed plan or route ledger does not reproduce")
    if (
        old["counts"]["A"] != old["counts"]["B"]
        or old["counts"]["A"]["unsupported_exact_clauses"] != 121
        or old["counts"]["A"]["possible_nonoccurrence_review_candidates"] != 53
        or old["counts"]["A"]["source_affected_unsupported_clauses"] != 13
        or old["counts"]["A"]["next_action_changes"] != 6
        or len(old["request_groups"]) != 30
        or len(old["group_delta"]) != 30
        or set(NEW_SOURCE_GROUPS) != set(NEXT_ACTION)
        or ledger["p1_freeze"] != P1_FREEZE
        or ledger["audit_task_credit"] is not False
        or ledger["active_pair_mutated"] is not False
        or ledger["reviewed_source_roster"]
        != {
            "cohorts": 28,
            "native_versions": 529,
            "source_complete": False,
            "registry": "REVIEWED_MAIN_V7_PARTIAL_PORTFOLIO_AND_CANDIDATE",
        }
        or any(
            ledger["active_p1_tasks"][side]
            != {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"}
            for side in "AB"
        )
    ):
        raise V6SourceRequestError("Frozen request, source or task denominator differs")
    routes = {
        (row["side"], row["task_id"]): row
        for row in ledger["rows"]
        if row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
    }
    old_rows = {(row["side"], row["task_id"]): row for row in old["rows"]}
    if len(routes) != 242 or len(old_rows) != 242 or set(routes) != set(old_rows):
        raise V6SourceRequestError("Exact unsupported task identity differs")
    rows = []
    group_leads = {group["request_group_id"]: set() for group in old["request_groups"]}
    group_limits = {group["request_group_id"]: {} for group in old["request_groups"]}
    for previous in old["rows"]:
        row = dict(previous)
        side, task_id = row["side"], row["task_id"]
        source = routes[side, task_id]
        group = row["request_group_id"]
        leads = list(source["v6_reviewed_source_ids"])
        expected = [NEW_SOURCE_TASKS[task_id]] if task_id in NEW_SOURCE_TASKS else []
        if (
            leads != expected
            or source["control_id"] != row["control_id"]
            or source["authored_test_clause"] != row["authored_test_clause"]
            or source["remaining_test_gate"] != row["remaining_test_gate"]
            or source["requirement_ids"] != row["requirement_ids"]
            or source["screen_row_sha256"] != row["screen_row_sha256"]
            or source["source_limit"] != row["v3_source_limit"]
            or source["v5_reviewed_source_ids"] != row["v5_reviewed_source_ids"]
            or source["v5_source_limits"] != row["v5_source_limits"]
            or set(source["targeted_integrated_source_ids"])
            != set(row["v5_targeted_source_ids"]) | set(leads)
            or set(source["v6_source_limits"]) != set(leads)
            or source["current_status"] != row["current_task_status"]
            or source["current_conclusion"] != row["current_task_conclusion"]
            or source["actual_operation_eligibility_as_of_packet"] is not False
            or source["audit_task_credit"] is not False
            or not row["authored_test_clause"]
            or row["pbc_request_status"] != "DRAFT_NOT_SENT"
            or row["task_credit"] is not False
            or row["accepted_nonoccurrence_status"] == "ACCEPTED"
        ):
            raise V6SourceRequestError(f"Unsupported V6 clause/source drift: {(side, task_id)}")
        group_leads[group].update(leads)
        for lead in leads:
            limit = source["v6_source_limits"][lead]
            if lead in group_limits[group] and group_limits[group][lead] != limit:
                raise V6SourceRequestError("Paired selected source limit differs")
            group_limits[group][lead] = limit
        row["v6_reviewed_source_ids"] = leads
        row["v6_source_limits"] = source["v6_source_limits"]
        row["v6_targeted_source_ids"] = source["targeted_integrated_source_ids"]
        row["v6_next_action"] = NEXT_ACTION.get(group, row["v5_next_action"])
        row["v6_next_action_changed_from_v5"] = group in NEXT_ACTION
        rows.append(row)
    if {group for group, leads in group_leads.items() if leads} != set(NEW_SOURCE_GROUPS):
        raise V6SourceRequestError("Exact three source-affected request groups differ")
    groups = []
    deltas = []
    for previous, previous_delta in zip(old["request_groups"], old["group_delta"], strict=True):
        group = dict(previous)
        delta = dict(previous_delta)
        group_id = group["request_group_id"]
        leads = sorted(group_leads[group_id])
        if (
            delta["request_group_id"] != group_id
            or leads != sorted(NEW_SOURCE_GROUPS.get(group_id, ()))
            or (group_id in NEXT_ACTION and group["v5_next_action_changed"])
        ):
            raise V6SourceRequestError("Historical group or V6 source join differs")
        next_action = NEXT_ACTION.get(group_id, group["v5_next_action"])
        group["v6_reviewed_source_ids"] = leads
        group["v6_source_limits"] = group_limits[group_id]
        group["v6_next_action"] = next_action
        group["v6_next_action_changed_from_v5"] = group_id in NEXT_ACTION
        delta.update(
            {
                "v6_reviewed_source_ids": leads,
                "v6_source_limits": group_limits[group_id],
                "v5_next_action_before_v6": previous["v5_next_action"],
                "v6_next_action": next_action,
                "v6_next_action_changed_from_v5": group_id in NEXT_ACTION,
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
            or sum(bool(row["v6_reviewed_source_ids"]) for row in selected) != 4
            or sum(
                bool(row["v5_reviewed_source_ids"] or row["v6_reviewed_source_ids"])
                for row in selected
            )
            != 17
            or sum(bool(row["v6_targeted_source_ids"]) for row in selected) != 29
            or any(
                row["accepted_nonoccurrence_status"] != "NOT_ESTABLISHED"
                for row in selected
                if row["possible_nonoccurrence_review_candidate"]
            )
        ):
            raise V6SourceRequestError("V6 unsupported/LEGAL/no-event split differs")
        counts[side] = {
            **old["counts"][side],
            "v6_new_source_affected_unsupported_clauses": 4,
            "v6_new_source_affected_request_groups": 3,
            "v6_next_action_changes_from_v5": 3,
            "v6_cumulative_source_affected_unsupported_clauses": 17,
            "v6_cumulative_targeted_unsupported_clauses": 29,
            "v6_cumulative_changed_request_groups": 9,
            "v6_grouping_or_contact_changes": 0,
        }
    if (
        counts["A"] != counts["B"]
        or len(groups) != 30
        or len({group["request_group_id"] for group in groups}) != 30
        or sum(delta["next_action_changed"] for delta in deltas) != 6
        or sum(delta["v6_next_action_changed_from_v5"] for delta in deltas) != 3
        or routes_v6._p1_inventory(private) != p1_before
    ):
        raise V6SourceRequestError("Paired request delta or frozen P1 differs")
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
            "The six V5 next actions remain; only IAM005, SEC001 and SEC003 gain V6 "
            "next actions. All 30 group identities, proposed contacts, source locators "
            "and original requests are unchanged.",
            "IAM005 is one fictional Boise marker with an inert service identity, not "
            "authorized deployed ePHI emergency operation or a complete population.",
            "SEC003 is selected four-asset fictional vulnerability history. The October "
            "false-clean sign-off and missed-coverage exception remain; AS-P008's "
            "November recheck is management self-review, not independent assurance.",
            "All authored clauses remain unsupported; 53 possible no-event reviews "
            "per side are unaccepted. No N/A determination or audit task credit.",
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
    """Render the exact V5-to-V6 unsupported request changes."""
    counts = result["counts"]["A"]
    lines = [
        "# Unsupported exact clauses: reviewed V6 PBC/source-request delta",
        "",
        "This read-only successor joins the independently reviewed V5 PBC plan to "
        "the independently reviewed main-local V6 route ledger. All 121 unsupported "
        "authored clauses per side remain unsupported across 28 controls and 30 draft "
        "request groups. The [paired JSON](UNSUPPORTED_121_PBC_PLAN_V6_2026-09-30.json) "
        "retains every historical row, group, contact, locator, original request and "
        "source limit.",
        "",
        "| Per-side measure | Count |",
        "| --- | ---: |",
        f"| Unsupported authored clauses | {counts['unsupported_exact_clauses']} |",
        "| Possible no-event review candidates | "
        f"{counts['possible_nonoccurrence_review_candidates']} |",
        "| Accepted no-event or N/A decisions | 0 |",
        "| V5 source-affected unsupported clauses | "
        f"{counts['source_affected_unsupported_clauses']} |",
        "| New V6 source-affected unsupported clauses | "
        f"{counts['v6_new_source_affected_unsupported_clauses']} |",
        "| Cumulative source-affected unsupported clauses | "
        f"{counts['v6_cumulative_source_affected_unsupported_clauses']} |",
        "| Unsupported clauses with any targeted source lead | "
        f"{counts['v6_cumulative_targeted_unsupported_clauses']} |",
        f"| V5 next-action changes retained | {counts['next_action_changes']} |",
        f"| New V6 next-action changes | {counts['v6_next_action_changes_from_v5']} |",
        "| Changed groups, contacts, locators or original requests | 0 |",
        "",
        "Only the following three groups gain a V6 next action. The four new leads "
        "per side attach only to IAM005's emergency and CC6.1 clauses, SEC001 CC5.2 "
        "and SEC003 CC7.1. The six V5 changed actions and all other groups retain "
        "their V5 text.",
        "",
        "| Request group | New reviewed source lead | V6 next action |",
        "| --- | --- | --- |",
    ]
    lines.extend(
        f"| {delta['request_group_id']} | "
        f"{', '.join(delta['v6_reviewed_source_ids'])} | {delta['v6_next_action']} |"
        for delta in result["group_delta"]
        if delta["v6_next_action_changed_from_v5"]
    )
    lines += [
        "",
        "The IAM005 marker covers one fictional Boise human and inert service identity; "
        "Messy BCM and SEC005 exceptions remain open. SEC003 covers a selected four-asset "
        "fictional vulnerability history, with the October 3/4 false-clean sign-off "
        "and open missed-coverage exception preserved. AS-P008's November recheck is "
        "management self-review. Neither source satisfies an authored clause or "
        "supplies a complete operating population.",
        "",
        "SH-LEG-001 remains 16 provision/status, four source-context and 46 "
        "conditional matter clauses per side. Its 46 possible no-matter reviews "
        "and seven other possible no-event reviews remain unaccepted. Nothing "
        "becomes N/A.",
        "",
        "All requests remain `DRAFT_NOT_SENT`; this packet sent zero external "
        "messages, issued zero audit task commands and granted zero task credit. "
        "Both A/B engagements retain 409 `NOT_STARTED`/`NOT_RUN` tasks and the "
        "538-file P1 inventory is frozen. The records describe fictional future "
        "history as of 2026-09-30; no Key or Atlas write occurred.",
        "",
    ]
    return "\n".join(lines)
