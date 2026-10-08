"""Read-only V5 source-request delta for 121 unsupported clauses per side."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from . import documentary_283_route_reconciliation_v5 as routes_v5
from . import unsupported_121_pbc_plan as prior

SCHEMA = "SH_UNSUPPORTED_121_PAIRED_SOURCE_REQUEST_PLAN_V5"
V5_LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V5_2026-09-30.json"
V5_REVIEW = (
    "enterprise/generated/audit-suite/documentary-283-route-reconciliation-v5-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
V2_PLAN = "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_2026-09-29.json"
PINS = {
    V5_LEDGER: "61d16ce933628b7c6bda4b90e5ee5292fd1634d1c9c9e2ac0201a46e02726a10",
    V5_REVIEW: "89d03c1b1b4a2450524c6093dbe5ab9c02452afde351da939c92e3f9c835497b",
    V2_PLAN: "25ea72e4b2480e11d6dc2b8d3018fb04cc1be019eb9da69bd5c6e881d947aa05",
}
NEW_SOURCE_GROUPS = {
    "SH-ASS-001": ("ASS001002_OWNER_MONITOR_V1",),
    "SH-ASS-002": ("ASS001002_OWNER_MONITOR_V1",),
    "SH-ERM-002": ("GOV_POL_ERM_APPETITE_V1",),
    "SH-GOV-003": ("GOV_POL_ERM_APPETITE_V1",),
    "SH-POL-002": ("GOV_POL_ERM_APPETITE_V1",),
    "SH-SEC-005": ("SEC005_SYMBOLIC_LOCAL_V1", "SEC005_SELECTED_OPERATIONS_V2"),
}
NEXT_ACTION = {
    "SH-ASS-001": (
        "Inspect the selected Q3 fictional owner submission, Messy omission, "
        "correction and open escalation; then request the full critical-duty, "
        "competence, backup and recurring-failure population with qualified challenge."
    ),
    "SH-ASS-002": (
        "Inspect the selected Q3 monitoring plan and objectivity-limited Messy "
        "challenge; then request the complete technical and nontechnical evaluation "
        "population, change-triggered refresh and independent evaluation."
    ),
    "SH-ERM-002": (
        "Inspect the selected fictional 240/15 recovery envelope and denied Messy "
        "waiver; then request approved measurable risk appetite, service commitments, "
        "tolerances and dated exception/escalation decisions for the full scope."
    ),
    "SH-GOV-003": (
        "Inspect the selected fictional member actions and bounded CEO delegation; "
        "then obtain qualified security-official and HIPAA entity/function decisions, "
        "effective reserved matters and complete cross-site escalation examples."
    ),
    "SH-POL-002": (
        "Inspect the selected fictional delegation and denied Messy waiver; then "
        "locate accepted policy/control authority, any legally required "
        "security-official appointment and full risk-to-control conflict resolution."
    ),
    "SH-SEC-005": (
        "Inspect both symbolic and selected-operated fictional traces, retaining "
        "the October false pass, open Messy exception and AS-P008 self-review limit; "
        "then request the complete interface/asset/period population and independent "
        "reperformance of ingress, egress, administration, install/update and detection."
    ),
}


class V5SourceRequestError(prior.SourceRequestError):
    """A reviewed clause, request group, or no-credit boundary changed."""


def build(repository: Path, private_repository: Path) -> dict:
    """Reperform the V2 request plan and exact reviewed V5 route delta."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    ledger = prior._pinned(repository / V5_LEDGER, PINS[V5_LEDGER])
    review = prior._pinned(private / V5_REVIEW, PINS[V5_REVIEW], private=True)
    old_pinned = prior._pinned(repository / V2_PLAN, PINS[V2_PLAN])
    if (
        review.get("verdict")
        != "PASS_READ_ONLY_PARTIAL_ROUTE_RECONCILIATION_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or review.get("main_tracked_sha256", {}).get("ledger_json") != PINS[V5_LEDGER]
        or review.get("checks", {}).get("tracked_code_or_p1_mutated_by_review") is not False
        or ledger.get("audit_task_credit") is not False
        or ledger.get("active_pair_mutated") is not False
        or ledger.get("reviewed_source_roster")
        != {"cohorts": 26, "native_versions": 475, "source_complete": False}
    ):
        raise V5SourceRequestError("Independent V5 route review/ledger join differs")
    if routes_v5.build(repository, private) != ledger:
        raise V5SourceRequestError("V5 reviewed route ledger does not reproduce")
    old = prior.build(repository, private)
    if old != old_pinned:
        raise V5SourceRequestError("Historical 121-clause plan does not reproduce")
    if (
        old["counts"]["A"] != old["counts"]["B"]
        or old["counts"]["A"]["unsupported_exact_clauses"] != 121
        or old["counts"]["A"]["possible_nonoccurrence_review_candidates"] != 53
        or len(old["request_groups"]) != 30
        or set(NEW_SOURCE_GROUPS) != set(NEXT_ACTION)
    ):
        raise V5SourceRequestError("Historical request denominator differs")
    route_rows = {
        (row["side"], row["task_id"]): row
        for row in ledger["rows"]
        if row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
    }
    old_rows = {(row["side"], row["task_id"]): row for row in old["rows"]}
    if len(route_rows) != 242 or set(route_rows) != set(old_rows):
        raise V5SourceRequestError("Exact unsupported 121/side task identity differs")
    rows = []
    group_leads = {group["request_group_id"]: set() for group in old["request_groups"]}
    for old_row in old["rows"]:
        row = dict(old_row)
        key = row["side"], row["task_id"]
        source = route_rows[key]
        leads = tuple(source["v5_reviewed_source_ids"])
        group = row["request_group_id"]
        if (
            source["control_id"] != row["control_id"]
            or source["authored_test_clause"] != row["authored_test_clause"]
            or source["remaining_test_gate"] != row["remaining_test_gate"]
            or source["requirement_ids"] != row["requirement_ids"]
            or source["screen_row_sha256"] != row["screen_row_sha256"]
            or source["source_limit"] != row["v3_source_limit"]
            or source["candidate_or_design_source_ids"] != row["v3_candidate_native_leads"]
            or not set(row["v3_targeted_source_ids"]).issubset(
                source["targeted_integrated_source_ids"]
            )
            or source["current_status"] != "NOT_STARTED"
            or source["current_conclusion"] != "NOT_RUN"
            or source["actual_operation_eligibility_as_of_packet"] is not False
            or source["audit_task_credit"] is not False
        ):
            raise V5SourceRequestError(f"Unsupported V5 clause/source drift: {key}")
        expected_leads = NEW_SOURCE_GROUPS.get(group, ())
        if leads != expected_leads:
            raise V5SourceRequestError(f"New source/group overlap differs: {key}")
        if set(source["v5_source_limits"]) != set(leads):
            raise V5SourceRequestError(f"Selected source limit missing: {key}")
        if (
            row["pbc_request_status"] != "DRAFT_NOT_SENT"
            or row["current_task_status"] != "NOT_STARTED"
            or row["current_task_conclusion"] != "NOT_RUN"
            or row["task_credit"] is not False
            or row["accepted_nonoccurrence_status"] == "ACCEPTED"
        ):
            raise V5SourceRequestError("Unsupported request was accepted or credited")
        group_leads[group].update(leads)
        row["v5_reviewed_source_ids"] = list(leads)
        row["v5_source_limits"] = source["v5_source_limits"]
        row["v5_targeted_source_ids"] = source["targeted_integrated_source_ids"]
        row["v5_next_action"] = NEXT_ACTION.get(group, row["requested_originals_or_decision"])
        row["v5_next_action_changed"] = group in NEXT_ACTION
        rows.append(row)
    expected_groups = set(NEW_SOURCE_GROUPS)
    changed_groups = {group for group, leads in group_leads.items() if leads}
    if changed_groups != expected_groups:
        raise V5SourceRequestError("Exact six source-affected request groups differ")
    groups = []
    deltas = []
    for previous in old["request_groups"]:
        group = dict(previous)
        group_id = group["request_group_id"]
        leads = sorted(group_leads[group_id])
        if leads != sorted(NEW_SOURCE_GROUPS.get(group_id, ())):
            raise V5SourceRequestError("Paired group source leads differ")
        next_action = NEXT_ACTION.get(group_id, group["requested_originals_or_decision"])
        group["v5_reviewed_source_ids"] = leads
        group["v5_next_action"] = next_action
        group["v5_next_action_changed"] = group_id in NEXT_ACTION
        groups.append(group)
        deltas.append(
            {
                "request_group_id": group_id,
                "grouping_changed": False,
                "candidate_contact_changed": False,
                "source_locator_changed": False,
                "requested_originals_changed": False,
                "next_action_changed": group_id in NEXT_ACTION,
                "v5_reviewed_source_ids": leads,
                "prior_next_action": previous["requested_originals_or_decision"],
                "v5_next_action": next_action,
            }
        )
    if len(groups) != 30 or len({group["request_group_id"] for group in groups}) != 30:
        raise V5SourceRequestError("Exact request grouping differs")
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
            or sum(bool(row["v5_reviewed_source_ids"]) for row in selected) != 13
            or any(
                row["accepted_nonoccurrence_status"] != "NOT_ESTABLISHED"
                for row in selected
                if row["possible_nonoccurrence_review_candidate"]
            )
        ):
            raise V5SourceRequestError("V5 exact unsupported/LEGAL/no-event split differs")
        counts[side] = {
            **old["counts"][side],
            "source_affected_unsupported_clauses": 13,
            "source_affected_request_groups": 6,
            "grouping_or_contact_changes": 0,
            "next_action_changes": 6,
        }
    if counts["A"] != counts["B"] or len([d for d in deltas if d["next_action_changed"]]) != 6:
        raise V5SourceRequestError("Paired request delta counts differ")
    return {
        "schema": SCHEMA,
        "as_of": "2026-09-30",
        "source_pins": PINS,
        "reviewed_route_roster": {"cohorts": 26, "native_versions": 475, "source_complete": False},
        "counts": counts,
        "rows": rows,
        "request_groups": groups,
        "group_delta": deltas,
        "candidate_owner_source_queues": old["candidate_owner_source_queues"],
        "nonoccurrence_acceptance_protocol": old["nonoccurrence_acceptance_protocol"],
        "limits": [
            "V5 source leads update six next actions only; all 30 group identities, "
            "candidate contacts, source locators and original requests remain unchanged.",
            "A selected fictional company record is a partial lead, not an authored "
            "clause disposition, approved authority or complete operating population.",
            "Possible no-event reviews remain unaccepted; empty fixtures do not "
            "establish nonoccurrence or N/A.",
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
    """Render the explicit V3-request/V5-source change decision."""
    counts = result["counts"]["A"]
    lines = [
        "# Unsupported exact clauses: reviewed V5 PBC/source-request delta",
        "",
        "This read-only successor compares the independently reviewed V5 route ledger "
        "against the historical 121-clause PBC plan. All 121 authored unsupported "
        "clauses per side remain unsupported across 28 controls and 30 draft request "
        "groups. The [paired JSON](UNSUPPORTED_121_PBC_PLAN_V5_2026-09-30.json) "
        "retains exact clauses, source limits, proposed contacts, request lanes and "
        "explicit group-by-group decisions.",
        "",
        "| Per-side measure | Count |",
        "| --- | ---: |",
        f"| Unsupported authored clauses | {counts['unsupported_exact_clauses']} |",
        "| Possible no-event review candidates | "
        f"{counts['possible_nonoccurrence_review_candidates']} |",
        "| Accepted no-event or N/A decisions | 0 |",
        "| Unsupported clauses with new V5 source leads | "
        f"{counts['source_affected_unsupported_clauses']} |",
        f"| Request groups with a changed next action | {counts['next_action_changes']} |",
        "| Changed groups, contacts, locators or original requests | 0 |",
        "",
        "The six changed next actions are listed below. They direct a future reviewer "
        "to inspect the selected native source and then seek the still-missing "
        "population, authority, independent challenge or outside record. They do "
        "not send a request or accept an authored clause.",
        "",
        "| Request group | New reviewed source lead | V5 next action |",
        "| --- | --- | --- |",
    ]
    lines.extend(
        f"| {delta['request_group_id']} | "
        f"{', '.join(delta['v5_reviewed_source_ids'])} | {delta['v5_next_action']} |"
        for delta in result["group_delta"]
        if delta["next_action_changed"]
    )
    lines += [
        "",
        "All other 24 groups explicitly retain their prior next action, proposed "
        "contact and source locator. REC003 introduces no new unsupported authored "
        "route. Symbolic and selected-operated SEC005 affect the same two unsupported "
        "clauses; their provenance is retained separately without double counting.",
        "",
        "SH-LEG-001 remains 16 provision/status, four source-context and 46 "
        "conditional matter clauses per side. Its 46 possible no-matter reviews, "
        "plus seven other possible no-event reviews, remain unaccepted until a "
        "complete population, attributable qualified statement and independent "
        "challenge support them. Nothing becomes N/A.",
        "",
        "All requests remain `DRAFT_NOT_SENT`; this packet sent zero external "
        "messages, issued zero audit task commands and granted zero task credit. "
        "The 2027 records are fictional future history as of 2026-09-30. The frozen "
        "A/B pair, workpapers, Key and Atlas remain untouched.",
        "",
    ]
    return "\n".join(lines)
