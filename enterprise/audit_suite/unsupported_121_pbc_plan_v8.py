"""Read-only LEG001 matter-clause successor to the frozen unsupported PBC plan."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from . import documentary_283_route_reconciliation_v8 as routes_v8
from . import unsupported_121_pbc_plan as pinned
from . import unsupported_121_pbc_plan_v7 as prior

SCHEMA = "SH_UNSUPPORTED_121_PAIRED_SOURCE_REQUEST_PLAN_V8"
V7_PLAN = "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V7_2026-09-30.json"
V7_REVIEW = (
    "enterprise/generated/audit-suite/unsupported-121-pbc-plan-v7-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
V8_LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V8_2026-09-30.json"
V8_REVIEW = (
    "enterprise/generated/audit-suite/documentary-283-route-reconciliation-v8-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
V8_REVIEW_VERDICT = "PASS_READ_ONLY_SELECTED_LEG001_ROUTE_RECONCILIATION_MAIN_LOCAL_NO_AUDIT_CREDIT"
PINS = {
    V7_PLAN: "54a12a750df92ea66462145d1c6d6d136cee0dfac20a5f30cec50957237d320e",
    V7_REVIEW: "7229a7c6f31dd6649bc9efa9ee2508d2f0960d27677c3cc74a1369d1be0c9836",
    V8_LEDGER: "6e92adbfeeda9b43f525036e43f978f6d3653ff314ec4fd8a44ffc57f1b56ec9",
    V8_REVIEW: "3587f7ec4fe0082a8f93d6e0565f6758a1f7b4bc0d6e43c8bd47cb7b012f86ea",
}
P1_FREEZE = prior.P1_FREEZE
SOURCE = routes_v8.SOURCE
NEW_SOURCE_TASKS = {
    "TASK-SH-LEG-001-corporate-CHECK-HIPAA:160.306",
    "TASK-SH-LEG-001-corporate-CHECK-HIPAA:160.504",
}
NEW_SOURCE_GROUP = "SH-LEG-001/MATTER"
NEXT_ACTION = (
    "Inspect the selected fictional LEG001 counsel docket only as a lead for "
    "160.306 complaint intake and 160.504 conditional hearing status. Its internal "
    "watch does not establish an all-company or outside-matter population, a "
    "triggered proceeding, real HIPAA applicability or 2027 law. Request the "
    "selected-period counsel-controlled regulator/enforcement/proceeding population "
    "and original complaints, notices, proposed determinations, hearing requests, "
    "deadlines, responses and dispositions if triggered. Obtain a qualified counsel "
    "applicability and change review, owner-supported completeness and independent "
    "challenge before considering any supported no-matter conclusion; keep Messy BA "
    "flowdown and support-omission histories open."
)


class V8SourceRequestError(prior.V7SourceRequestError):
    """A reviewed LEG001 route, unsupported clause, or frozen request changed."""


def _extend(old: dict, ledger: dict, p1_before: dict) -> dict:
    """Build the exact additive request delta from already checked predecessors."""
    if (
        old["counts"]["A"] != old["counts"]["B"]
        or old["counts"]["A"]["unsupported_exact_clauses"] != 121
        or old["counts"]["A"]["possible_nonoccurrence_review_candidates"] != 53
        or old["counts"]["A"]["v7_cumulative_reviewed_source_affected_unsupported_clauses"] != 19
        or old["counts"]["A"]["v7_cumulative_targeted_unsupported_clauses"] != 31
        or len(old["request_groups"]) != 30
        or len(old["group_delta"]) != 30
        or old["p1_freeze"] != p1_before
        or ledger["p1_freeze"] != p1_before
        or ledger["audit_task_credit"] is not False
        or ledger["active_pair_mutated"] is not False
        or any(
            ledger["active_p1_tasks"][side]
            != {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"}
            for side in "AB"
        )
    ):
        raise V8SourceRequestError("Frozen V7 request or V8 route denominator differs")
    routes = {
        (row["side"], row["task_id"]): row
        for row in ledger["rows"]
        if row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
    }
    old_rows = {(row["side"], row["task_id"]): row for row in old["rows"]}
    if len(routes) != 242 or len(old_rows) != 242 or set(routes) != set(old_rows):
        raise V8SourceRequestError("Exact unsupported task identity differs")
    rows = []
    group_leads = {group["request_group_id"]: set() for group in old["request_groups"]}
    group_limits = {group["request_group_id"]: {} for group in old["request_groups"]}
    group_refs = {group["request_group_id"]: {"A": {}, "B": {}} for group in old["request_groups"]}
    for previous in old["rows"]:
        row = dict(previous)
        side, task_id = row["side"], row["task_id"]
        source = routes[side, task_id]
        group = row["request_group_id"]
        leads = list(source["v8_reviewed_source_ids"])
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
            or source["v7_reviewed_source_ids"] != row["v7_reviewed_source_ids"]
            or source["v7_source_limits"] != row["v7_source_limits"]
            or set(source["targeted_integrated_source_ids"])
            != set(row["v7_targeted_source_ids"]) | set(leads)
            or set(source["v8_source_limits"]) != set(leads)
            or set(source["v8_source_record_refs"]) != set(leads)
            or source["current_status"] != row["current_task_status"]
            or source["current_conclusion"] != row["current_task_conclusion"]
            or source["actual_operation_eligibility_as_of_packet"] is not False
            or source["audit_task_credit"] is not False
            or not row["authored_test_clause"]
            or row["pbc_request_status"] != "DRAFT_NOT_SENT"
            or row["task_credit"] is not False
            or row["accepted_nonoccurrence_status"] == "ACCEPTED"
        ):
            raise V8SourceRequestError(f"Unsupported V8 clause/source drift: {(side, task_id)}")
        if leads:
            suffix = task_id.split("-corporate-", 1)[1]
            expected_records = routes_v8.LEAD_RECORDS[suffix]
            refs = source["v8_source_record_refs"][SOURCE]
            if (
                len(refs) != 2
                or [(ref["system"], ref["record"]) for ref in refs] != list(expected_records)
                or any(
                    ref["branch"] != ("LEG-CLEAN" if side == "A" else "LEG-MESSY")
                    or ref["version"] != 1
                    for ref in refs
                )
                or source["v8_source_limits"][SOURCE] != routes_v8.LIMIT
            ):
                raise V8SourceRequestError("Selected conditional matter native lead differs")
            group_limits[group][SOURCE] = routes_v8.LIMIT
            group_refs[group][side][task_id] = refs
        group_leads[group].update(leads)
        row["v8_reviewed_source_ids"] = leads
        row["v8_source_limits"] = source["v8_source_limits"]
        row["v8_source_record_refs"] = source["v8_source_record_refs"]
        row["v8_targeted_source_ids"] = source["targeted_integrated_source_ids"]
        row["v8_next_action"] = NEXT_ACTION if group == NEW_SOURCE_GROUP else row["v7_next_action"]
        row["v8_next_action_changed_from_v7"] = group == NEW_SOURCE_GROUP
        rows.append(row)
    if {group for group, leads in group_leads.items() if leads} != {NEW_SOURCE_GROUP}:
        raise V8SourceRequestError("Exact legal source-affected group differs")
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
            or (group_id == NEW_SOURCE_GROUP and group["v7_next_action_changed_from_v6"])
            or any(len(group_refs[group_id][side]) != (2 if leads else 0) for side in "AB")
        ):
            raise V8SourceRequestError("Historical group or legal source join differs")
        next_action = NEXT_ACTION if group_id == NEW_SOURCE_GROUP else group["v7_next_action"]
        group["v8_reviewed_source_ids"] = leads
        group["v8_source_limits"] = group_limits[group_id]
        group["v8_source_record_refs_by_side"] = group_refs[group_id]
        group["v8_next_action"] = next_action
        group["v8_next_action_changed_from_v7"] = group_id == NEW_SOURCE_GROUP
        delta.update(
            {
                "v8_reviewed_source_ids": leads,
                "v8_source_limits": group_limits[group_id],
                "v8_source_record_refs_by_side": group_refs[group_id],
                "v7_next_action_before_v8": previous["v7_next_action"],
                "v8_next_action": next_action,
                "v8_next_action_changed_from_v7": group_id == NEW_SOURCE_GROUP,
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
            or sum(bool(row["v8_reviewed_source_ids"]) for row in selected) != 2
            or sum(
                bool(
                    row["v5_reviewed_source_ids"]
                    or row["v6_reviewed_source_ids"]
                    or row["v7_reviewed_source_ids"]
                    or row["v8_reviewed_source_ids"]
                )
                for row in selected
            )
            != 21
            or sum(bool(row["v8_targeted_source_ids"]) for row in selected) != 33
            or any(
                row["accepted_nonoccurrence_status"] != "NOT_ESTABLISHED"
                for row in selected
                if row["possible_nonoccurrence_review_candidate"]
            )
        ):
            raise V8SourceRequestError("V8 unsupported/LEGAL/no-event split differs")
        counts[side] = {
            **old["counts"][side],
            "v8_new_legal_source_affected_unsupported_clauses": 2,
            "v8_new_source_affected_request_groups": 1,
            "v8_next_action_changes_from_v7": 1,
            "v8_cumulative_reviewed_source_affected_unsupported_clauses": 21,
            "v8_cumulative_targeted_unsupported_clauses": 33,
            "v8_cumulative_changed_request_groups": 10,
            "v8_grouping_or_contact_changes": 0,
        }
    if (
        counts["A"] != counts["B"]
        or len(groups) != 30
        or len({group["request_group_id"] for group in groups}) != 30
        or sum(delta["next_action_changed"] for delta in deltas) != 6
        or sum(delta["v6_next_action_changed_from_v5"] for delta in deltas) != 3
        or sum(delta["v7_next_action_changed_from_v6"] for delta in deltas) != 1
        or sum(delta["v8_next_action_changed_from_v7"] for delta in deltas) != 1
    ):
        raise V8SourceRequestError("Paired legal request delta differs")
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
            "All V7 and earlier next-action fields remain intact; only SH-LEG-001/MATTER "
            "gains a V8 draft next action, with no changed group, contact or original request.",
            "Only 160.306 and 160.504 authored matter clauses per side gain the selected "
            "fictional LEG001 lead; both remain unsupported exact clauses.",
            "The selected docket cannot establish a complete matter population, a real "
            "HIPAA applicability decision, triggered hearing or 2027 legal status.",
            "Messy BA flowdown and support-omission histories remain open.",
            "All 121 authored clauses and 53 possible no-event reviews per side remain "
            "unsupported or unaccepted. No N/A or task credit.",
            "No request, external communication, audit task command, collection, grade, "
            "Key or Atlas edit was issued by this read-only draft.",
        ],
        "external_messages_sent": 0,
        "fresh_pair_created": False,
        "audit_task_credit": False,
        "accepted_na_determinations": 0,
        "active_pair_mutated": False,
    }


def build(repository: Path, private_repository: Path) -> dict:
    """Reperform the V7 plan and V8 route only after V8 main review is pinned."""
    if PINS[V8_REVIEW] == "PENDING_INDEPENDENT_MAIN_REVIEW":
        raise V8SourceRequestError("Route V8 independent main review pin is pending")
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    p1_before = routes_v8.prior.prior._p1_inventory(private)
    if p1_before != P1_FREEZE:
        raise V8SourceRequestError("Frozen P1 inventory differs")
    old_pinned = pinned._pinned(repository / V7_PLAN, PINS[V7_PLAN])
    old_review = pinned._pinned(private / V7_REVIEW, PINS[V7_REVIEW], private=True)
    ledger_pinned = pinned._pinned(repository / V8_LEDGER, PINS[V8_LEDGER])
    route_review = pinned._pinned(private / V8_REVIEW, PINS[V8_REVIEW], private=True)
    if (
        old_review.get("verdict")
        != "PASS_READ_ONLY_UNSUPPORTED_CLAUSE_REQUEST_DELTA_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or old_review.get("main_tracked_sha256", {}).get(V7_PLAN) != PINS[V7_PLAN]
        or old_review.get("p1_freeze") != P1_FREEZE
        or old_review.get("audit_task_credit") is not False
        or old_review.get("active_pair_mutated") is not False
        or route_review.get("verdict") != V8_REVIEW_VERDICT
        or route_review.get("main_tracked_sha256", {}).get(V8_LEDGER) != PINS[V8_LEDGER]
        or route_review.get("p1_freeze") != P1_FREEZE
        or route_review.get("audit_task_credit") is not False
        or route_review.get("active_pair_mutated") is not False
    ):
        raise V8SourceRequestError("Independent PBC V7/route V8 review join differs")
    old = prior.build(repository, private)
    ledger = routes_v8.build(repository, private)
    if old != old_pinned or ledger != ledger_pinned:
        raise V8SourceRequestError("Reviewed PBC or route ledger does not reproduce")
    result = _extend(old, ledger, p1_before)
    if routes_v8.prior.prior._p1_inventory(private) != p1_before:
        raise V8SourceRequestError("Frozen P1 changed during read-only PBC build")
    return result


def markdown(result: dict) -> str:
    """Render the one-group legal-matter draft request delta."""
    counts = result["counts"]["A"]
    group = next(
        group for group in result["request_groups"] if group["request_group_id"] == NEW_SOURCE_GROUP
    )
    lines = [
        "# Unsupported exact clauses: conditional LEG001 matter request delta V8",
        "",
        "This read-only successor is gated on an independently reviewed main-local "
        "route V8 ledger. All 121 unsupported authored clauses per side remain "
        "unsupported across 28 controls and 30 draft groups. It preserves every "
        "V7 row, group, contact, source locator and original request.",
        "",
        "| Per-side measure | Count |",
        "| --- | ---: |",
        f"| Unsupported authored clauses | {counts['unsupported_exact_clauses']} |",
        "| Possible no-event review candidates | "
        f"{counts['possible_nonoccurrence_review_candidates']} |",
        "| Accepted no-event or N/A decisions | 0 |",
        "| New LEG001 leads on unsupported clauses | "
        f"{counts['v8_new_legal_source_affected_unsupported_clauses']} |",
        "| Cumulative reviewed V5/V6/V7/V8 source-affected clauses | "
        f"{counts['v8_cumulative_reviewed_source_affected_unsupported_clauses']} |",
        "| Unsupported clauses with a targeted source lead | "
        f"{counts['v8_cumulative_targeted_unsupported_clauses']} |",
        f"| New V8 next-action changes | {counts['v8_next_action_changes_from_v7']} |",
        "| Changed groups, contacts, locators or original requests | 0 |",
        "",
        "Only the authored 160.306 complaint and 160.504 conditional-hearing matter "
        "clauses gain the selected fictional docket lead. The other 44 matter clauses "
        "in SH-LEG-001/MATTER gain no lead. Neither the selected internal watch nor "
        "an empty feed establishes an all-company or external-matter no-event decision.",
        "",
        "| Request group | New reviewed source lead | V8 draft next action |",
        "| --- | --- | --- |",
        f"| {NEW_SOURCE_GROUP} | {SOURCE} | {group['v8_next_action']} |",
        "",
        "All requests remain `DRAFT_NOT_SENT`; zero external messages, accepted N/A "
        "decisions, audit task commands or task credit were issued. The frozen A/B "
        "P1 tasks remain `NOT_STARTED`/`NOT_RUN`; no Key, grade or Atlas write occurred.",
        "",
    ]
    return "\n".join(lines)
