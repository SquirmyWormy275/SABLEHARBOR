"""Draft-only PBC actions for reviewed LEG provision and DAT rights discovery."""

from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path

from . import documentary_283_route_reconciliation_v17 as route
from . import unsupported_121_pbc_plan as pinned
from . import unsupported_121_pbc_plan_v14 as prior
from .documentary_283_route_reconciliation_v6 import _p1_inventory, _pinned_db

SCHEMA = "SH_UNSUPPORTED_121_PAIRED_SOURCE_REQUEST_PLAN_V15"
BASE = "enterprise/generated/audit-suite"
V14_PLAN = "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V14_2026-10-01.json"
V14_RUN = f"{BASE}/unsupported-121-pbc-plan-v14-2026-10-01/main-run-v1/PLAN.json"
V14_REVIEW = (
    f"{BASE}/unsupported-121-pbc-plan-v14-2026-10-01/independent-review-main-v1/REVIEW.json"
)
ROUTE_LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V17_2026-10-01.json"
ROUTE_RUN = f"{BASE}/documentary-283-route-reconciliation-v17-2026-10-01/main-run-v1/LEDGER.json"
ROUTE_REVIEW = (
    f"{BASE}/documentary-283-route-reconciliation-v17-2026-10-01/"
    "independent-review-main-v1/REVIEW.json"
)
V16_LEDGER = route.V16_LEDGER
LEG_GAP = route.LEG_GAP
LEG_RECEIPT = f"{route.LEG_RUN}/RECEIPT.json"
LEG_DB = f"{route.LEG_RUN}/company.sqlite3"
DAT_RECEIPT = f"{route.DAT_RUN}/RECEIPT.json"
DAT_DB = f"{route.DAT_RUN}/company.sqlite3"
PINS = {
    V14_PLAN: "c414799171d1256222f80675be0e0b4dd5fff45ce5d345f7540cd34f08a905b4",
    V14_RUN: "c414799171d1256222f80675be0e0b4dd5fff45ce5d345f7540cd34f08a905b4",
    V14_REVIEW: "2a212e9ff08e9bad9532b4c88c685094251424fbc7bfd973451cadad2801819a",
    ROUTE_LEDGER: "43b33d7ca19e670eea704193fff947c268c2d1c736f0c8829420a556576e8bcb",
    ROUTE_RUN: "43b33d7ca19e670eea704193fff947c268c2d1c736f0c8829420a556576e8bcb",
    ROUTE_REVIEW: "dee0ff288245b0306b79c3b9819f61c940c45fb0355eec5b94a2e73baa0f6db2",
    V16_LEDGER: route.PINS["v16_ledger"]["sha256"],
    LEG_GAP: route.PINS["leg_gap"]["sha256"],
    LEG_RECEIPT: route.PINS["leg_receipt"]["sha256"],
    LEG_DB: route.PINS["leg_db"]["sha256"],
    DAT_RECEIPT: route.PINS["dat_receipt"]["sha256"],
    DAT_DB: route.PINS["dat_db"]["sha256"],
}
P1_FREEZE = prior.P1_FREEZE
LEG_SOURCE = route.LEG_SOURCE
DAT_SOURCE = route.DAT_SOURCE
LEG_GROUP = "SH-LEG-001/PROVISION"
DAT_GROUP = "SH-DAT-002"
NEXT_ACTION_ADDENDA = {
    LEG_GROUP: (
        "Inspect the branch-matched selected fictional 2027 counsel overlay and exact "
        "provision-locator originals for these 16 authored candidates only. Obtain primary "
        "text effective on the tested date, qualified counsel legal-status and entity/function "
        "applicability decisions, executed term/authority, trigger and performance facts. "
        "The 164.509 locator remains held; historical XML, synthetic terms and a proposed "
        "counsel contact do not prove 2027 law or duty. Retain the other 50 LEG001 authored "
        "candidates as unmodeled here. No clause satisfaction or audit credit."
    ),
    DAT_GROUP: (
        "Inspect the branch-matched selected payload-free rights-scope inquiry originals "
        "(5 Clean/6 Messy) for only the rights-assistance and 164.501 discovery tasks. "
        "Obtain customer delegation, requester authority, qualified duty decision and the "
        "complete designated-record-set, backup, subcontractor and disclosure population; "
        "then trace actual electronic-copy, accepted-amendment and accounting work if "
        "triggered. Messy retains its OPEN premature no-record exception. An internal "
        "inquiry is not an actual customer request, response or completed rights action."
    ),
}


class V15SourceRequestError(prior.V14SourceRequestError):
    """Reviewed V14 PBC, V17 route, selected native original or no-credit gate changed."""


def _selected_refs(
    old: dict,
    ledger: dict,
    v16: dict,
    gap: dict,
    leg_receipt: dict,
    dat_receipt: dict,
) -> tuple[dict, dict[str, set[str]]]:
    """Require exact route/native refs for 16 LEG plus two DAT authored tasks per side."""
    if (
        ledger.get("schema") != route.SCHEMA
        or ledger.get("as_of") != "2026-10-01"
        or ledger.get("v16_prefix_sha256") != PINS[V16_LEDGER]
        or ledger.get("p1_freeze") != P1_FREEZE
        or ledger.get("active_p1_tasks") != old.get("active_p1_tasks")
        or ledger.get("audit_task_credit") is not False
        or ledger.get("active_pair_mutated") is not False
        or len(ledger.get("rows", [])) != 566
        or any(
            ledger["counts"][side]["targeted_integrated_route_count"] != 201
            or ledger["counts"][side]["classifications"]["UNSUPPORTED_EXACT_CLAUSE"] != 121
            for side in "AB"
        )
    ):
        raise V15SourceRequestError("Reviewed V17 route or frozen P1 scope differs")
    refs = route._selected_refs(leg_receipt, dat_receipt, gap, v16)
    selected = {"leg": set(refs["A"]["leg"]), "dat": set(route.DAT_TASKS)}
    if (
        selected["leg"] != set(refs["B"]["leg"])
        or len(selected["leg"]) != 16
        or len(selected["dat"]) != 2
        or selected["leg"] & selected["dat"]
    ):
        raise V15SourceRequestError("Selected LEG/DAT authored task roster differs")
    route_rows = {(row["side"], row["task_id"]): row for row in ledger["rows"]}
    if len(route_rows) != 566:
        raise V15SourceRequestError("V17 route rows duplicated")
    for prior_row in old["rows"]:
        side, task = prior_row["side"], prior_row["task_id"]
        row = route_rows[(side, task)]
        source = (
            LEG_SOURCE
            if task in selected["leg"]
            else DAT_SOURCE
            if task in selected["dat"]
            else None
        )
        exact_refs = (
            refs[side]["leg"][task]
            if source == LEG_SOURCE
            else refs[side]["dat"]
            if source
            else None
        )
        previous_ids = prior_row["v14_targeted_source_ids"]
        expected_ids = [*previous_ids, source] if source else previous_ids
        if (
            row["classification"] != "UNSUPPORTED_EXACT_CLAUSE"
            or row["test_gate_basis"] != "AUTHORED_TASK_CLAUSE"
            or row["authored_test_clause"] != prior_row["authored_test_clause"]
            or row["remaining_test_gate"] != prior_row["remaining_test_gate"]
            or row["control_id"] != prior_row["control_id"]
            or row["targeted_integrated_source_ids"] != expected_ids
            or row["v17_reviewed_source_ids"] != ([source] if source else [])
            or row["v17_source_limits"]
            != (
                {source: route.LEG_LIMIT if source == LEG_SOURCE else route.DAT_LIMIT}
                if source
                else {}
            )
            or row["v17_source_record_refs"] != ({source: exact_refs} if source else {})
            or row["current_status"] != "NOT_STARTED"
            or row["current_conclusion"] != "NOT_RUN"
            or row["audit_task_credit"] is not False
            or (source == LEG_SOURCE and prior_row["request_group_id"] != LEG_GROUP)
            or (source == DAT_SOURCE and prior_row["request_group_id"] != DAT_GROUP)
            or (source and (previous_ids or prior_row["v14_reviewed_source_ids"]))
        ):
            raise V15SourceRequestError("Exact unsupported V17 route/native lead differs")
    return refs, selected


def _extend(
    old: dict,
    ledger: dict,
    v16: dict,
    gap: dict,
    leg_receipt: dict,
    dat_receipt: dict,
    freeze: dict,
) -> dict:
    """Preserve V14 draft fields and add only 18 selected LEG/DAT actions per side."""
    if (
        old.get("schema") != prior.SCHEMA
        or old.get("as_of") != "2026-10-01"
        or old.get("p1_freeze") != freeze
        or len(old.get("rows", [])) != 242
        or len(old.get("request_groups", [])) != 30
        or len(old.get("group_delta", [])) != 30
        or old.get("audit_task_credit") is not False
        or old.get("active_pair_mutated") is not False
        or old.get("external_messages_sent") != 0
        or old.get("accepted_na_determinations") != 0
        or old.get("fresh_pair_created") is not False
        or old.get("source_complete") is not False
        or any(
            old["active_p1_tasks"][side]
            != {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"}
            or old["counts"][side]["v14_cumulative_reviewed_source_affected_unsupported_clauses"]
            != 29
            or old["counts"][side]["v14_cumulative_targeted_unsupported_clauses"] != 37
            or old["counts"][side]["v14_cumulative_changed_request_groups"] != 17
            for side in "AB"
        )
    ):
        raise V15SourceRequestError("Reviewed V14 PBC or P1 denominator differs")
    refs, selected = _selected_refs(old, ledger, v16, gap, leg_receipt, dat_receipt)
    route_rows = {(row["side"], row["task_id"]): row for row in ledger["rows"]}
    rows = []
    for previous in old["rows"]:
        row = deepcopy(previous)
        side, task = row["side"], row["task_id"]
        source = (
            LEG_SOURCE
            if task in selected["leg"]
            else DAT_SOURCE
            if task in selected["dat"]
            else None
        )
        group = LEG_GROUP if source == LEG_SOURCE else DAT_GROUP if source else None
        route_row = route_rows[(side, task)]
        if (
            row["pbc_request_status"] != "DRAFT_NOT_SENT"
            or row["current_task_status"] != "NOT_STARTED"
            or row["current_task_conclusion"] != "NOT_RUN"
            or row["task_credit"] is not False
            or row["accepted_nonoccurrence_status"] == "ACCEPTED"
            or (source and row["request_group_id"] != group)
        ):
            raise V15SourceRequestError("V14 task, draft request or acceptance gate differs")
        row["v15_reviewed_source_ids"] = [source] if source else []
        row["v15_source_limits"] = dict(route_row["v17_source_limits"])
        row["v15_source_record_refs"] = deepcopy(route_row["v17_source_record_refs"])
        row["v15_targeted_source_ids"] = list(route_row["targeted_integrated_source_ids"])
        row["v15_next_action"] = (
            row["v14_next_action"] + " " + NEXT_ACTION_ADDENDA[group]
            if source
            else row["v14_next_action"]
        )
        row["v15_next_action_changed_from_v14"] = bool(source)
        rows.append(row)
    groups, deltas = [], []
    for previous_group, previous_delta in zip(
        old["request_groups"], old["group_delta"], strict=True
    ):
        group = deepcopy(previous_group)
        delta = deepcopy(previous_delta)
        name = group["request_group_id"]
        selected_group = name in NEXT_ACTION_ADDENDA
        tasks = (
            selected["leg"]
            if name == LEG_GROUP
            else selected["dat"]
            if name == DAT_GROUP
            else set()
        )
        source = LEG_SOURCE if name == LEG_GROUP else DAT_SOURCE if name == DAT_GROUP else None
        if (
            delta["request_group_id"] != name
            or group["request_status"] != "DRAFT_NOT_SENT"
            or group["task_credit"] is not False
            or (selected_group and not tasks <= set(group["task_ids_per_side"]["A"]))
            or (name == LEG_GROUP and group["routes_per_side"] != 16)
            or (name == DAT_GROUP and group["routes_per_side"] != 8)
            or (
                selected_group
                and group["task_ids_per_side"]["A"] != group["task_ids_per_side"]["B"]
            )
        ):
            raise V15SourceRequestError("V14 group or unsent request gate differs")
        source_refs = {
            side: {
                task: {
                    source: refs[side]["leg"][task] if source == LEG_SOURCE else refs[side]["dat"]
                }
                for task in sorted(tasks)
            }
            for side in "AB"
        }
        next_action = (
            group["v14_next_action"] + " " + NEXT_ACTION_ADDENDA[name]
            if selected_group
            else group["v14_next_action"]
        )
        additions = {
            "v15_reviewed_source_ids": [source] if selected_group else [],
            "v15_source_limits": {
                source: route.LEG_LIMIT if source == LEG_SOURCE else route.DAT_LIMIT
            }
            if selected_group
            else {},
            "v15_source_record_refs_by_side": source_refs,
            "v15_next_action": next_action,
            "v15_next_action_changed_from_v14": selected_group,
        }
        group.update(additions)
        delta.update({**additions, "v14_next_action_before_v15": previous_group["v14_next_action"]})
        groups.append(group)
        deltas.append(delta)
    counts = {}
    for side in "AB":
        subset = [row for row in rows if row["side"] == side]
        affected = sum(
            any(row[f"v{version}_reviewed_source_ids"] for version in range(5, 16))
            for row in subset
        )
        targeted = sum(bool(row["v15_targeted_source_ids"]) for row in subset)
        if (
            len(subset) != 121
            or len({row["task_id"] for row in subset}) != 121
            or len({row["control_id"] for row in subset}) != 28
            or sum(row["possible_nonoccurrence_review_candidate"] for row in subset) != 53
            or any(
                row["accepted_nonoccurrence_status"] != "NOT_ESTABLISHED"
                for row in subset
                if row["possible_nonoccurrence_review_candidate"]
            )
            or sum(bool(row["v15_reviewed_source_ids"]) for row in subset) != 18
            or affected != 47
            or targeted != 55
            or any(row["task_credit"] is not False for row in subset)
        ):
            raise V15SourceRequestError("V15 exact unsupported/no-event denominator differs")
        counts[side] = {
            **deepcopy(old["counts"][side]),
            "v15_new_reviewed_source_leads": 18,
            "v15_newly_source_affected_unsupported_clauses": 18,
            "v15_newly_route_targeted_unsupported_clauses": 18,
            "v15_selected_source_affected_request_groups": 2,
            "v15_next_action_changes_from_v14": 18,
            "v15_cumulative_reviewed_source_affected_unsupported_clauses": 47,
            "v15_cumulative_targeted_unsupported_clauses": 55,
            "v15_cumulative_changed_request_groups": 19,
            "v15_grouping_or_contact_changes": 0,
        }
    if (
        counts["A"] != counts["B"]
        or len(groups) != 30
        or len({group["request_group_id"] for group in groups}) != 30
        or sum(group["v15_next_action_changed_from_v14"] for group in groups) != 2
        or sum(group["v15_next_action_changed_from_v14"] for group in deltas) != 2
    ):
        raise V15SourceRequestError("Paired V15 draft group delta differs")
    return {
        **old,
        "schema": SCHEMA,
        "as_of": "2026-10-01",
        "source_pins": {**old["source_pins"], **PINS},
        "v17_route_ledger_sha256": PINS[ROUTE_LEDGER],
        "counts": counts,
        "rows": rows,
        "request_groups": groups,
        "group_delta": deltas,
        "limits": [
            *old["limits"],
            "All V14 row, group, contact, locator and original-request fields remain exact; "
            "only 16 LEG provision and two DAT rights authored draft actions per side gain "
            "selected native discovery leads. The other 103 unsupported rows per side "
            "retain their prior next actions.",
            route.LEG_LIMIT,
            route.DAT_LIMIT,
            "No actual 2027 legal-text or HIPAA applicability decision, real PHI/BA claim, "
            "customer rights response, accepted no-event/N/A determination, source "
            "completeness, clause satisfaction, request send, audit credit, fresh pair, "
            "Key, grade or Atlas write.",
        ],
        "external_messages_sent": 0,
        "accepted_na_determinations": 0,
        "fresh_pair_created": False,
        "source_complete": False,
        "audit_task_credit": False,
        "active_pair_mutated": False,
    }


def build(repository: Path, private_repository: Path) -> dict:
    """Join exact reviewed V14/V17 bytes; verify bounded LEG/DAT originals directly."""
    if any(re.fullmatch(r"[0-9a-f]{64}", PINS[rel]) is None for rel in (V14_REVIEW, ROUTE_REVIEW)):
        raise V15SourceRequestError("Pending independent main review pin")
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    freeze = _p1_inventory(private)
    if freeze != P1_FREEZE:
        raise V15SourceRequestError("Frozen P1 inventory differs")
    old = pinned._pinned(repository / V14_PLAN, PINS[V14_PLAN])
    old_main = pinned._pinned(private / V14_RUN, PINS[V14_RUN], private=True)
    old_review = pinned._pinned(private / V14_REVIEW, PINS[V14_REVIEW], private=True)
    ledger = pinned._pinned(repository / ROUTE_LEDGER, PINS[ROUTE_LEDGER])
    route_main = pinned._pinned(private / ROUTE_RUN, PINS[ROUTE_RUN], private=True)
    route_review = pinned._pinned(private / ROUTE_REVIEW, PINS[ROUTE_REVIEW], private=True)
    v16 = pinned._pinned(repository / V16_LEDGER, PINS[V16_LEDGER])
    gap = pinned._pinned(repository / LEG_GAP, PINS[LEG_GAP])
    leg_receipt = pinned._pinned(private / LEG_RECEIPT, PINS[LEG_RECEIPT], private=True)
    dat_receipt = pinned._pinned(private / DAT_RECEIPT, PINS[DAT_RECEIPT], private=True)
    _pinned_db(private, {"path": LEG_DB, "sha256": PINS[LEG_DB]})
    _pinned_db(private, {"path": DAT_DB, "sha256": PINS[DAT_DB]})
    if (
        old != old_main
        or ledger != route_main
        or old_review.get("schema") != "SH_INDEPENDENT_GOV_PBC_V14_MAIN_REVIEW_V1"
        or old_review.get("verdict") != "PASS_MAIN_DRAFT_ONLY_NO_AUDIT_CREDIT"
        or old_review.get("output_sha256", {}).get("PLAN.json") != PINS[V14_PLAN]
        or old_review.get("p1_freeze") != freeze
        or old_review.get("audit_task_credit") is not False
        or old_review.get("source_complete") is not False
        or old_review.get("fresh_audit_pair_created") is not False
        or route_review.get("schema") != "SH_INDEPENDENT_LEG_DAT_ROUTE_V17_MAIN_REVIEW_V1"
        or route_review.get("verdict") != "PASS_MAIN_SELECTED_LEADS_NO_AUDIT_CREDIT"
        or route_review.get("output_sha256", {}).get("LEDGER.json") != PINS[ROUTE_LEDGER]
        or route_review.get("audit_task_credit") is not False
        or route_review.get("source_complete") is not False
        or route_review.get("active_pair_mutated") is not False
    ):
        raise V15SourceRequestError("Independent V14/V17 main review join differs")
    verified_leg = route.leg.verify(
        private / route.LEG_RUN, repository=repository, private_repository=private
    )
    route.dat.verify(private / route.DAT_RUN, repository=repository, private_repository=private)
    if verified_leg != leg_receipt:
        raise V15SourceRequestError("LEG native verifier/receipt differs")
    result = _extend(old, ledger, v16, gap, leg_receipt, dat_receipt, freeze)
    if _p1_inventory(private) != freeze:
        raise V15SourceRequestError("Frozen P1 changed during read-only PBC build")
    return result


def markdown(result: dict) -> str:
    """Render two bounded selected draft group deltas without clause promotion."""
    counts = result["counts"]["A"]
    groups = [
        next(group for group in result["request_groups"] if group["request_group_id"] == name)
        for name in (LEG_GROUP, DAT_GROUP)
    ]
    lines = [
        "# Unsupported exact clauses: selected LEG/DAT draft delta V15",
        "",
        "All 121 authored unsupported clauses per side remain unsupported across 30 "
        "draft unsent groups. Every V14 row, group, contact, locator and original "
        "request field is retained.",
        "",
        "| Per-side measure | Count |",
        "| --- | ---: |",
        f"| Unsupported authored clauses | {counts['unsupported_exact_clauses']} |",
        "| Possible unaccepted no-event reviews | "
        f"{counts['possible_nonoccurrence_review_candidates']} |",
        "| New selected LEG/DAT authored leads | 16 / 2 |",
        "| Newly source-affected and route-targeted clauses | 18 |",
        "| Cumulative source-affected clauses | "
        f"{counts['v15_cumulative_reviewed_source_affected_unsupported_clauses']} |",
        "| Cumulative route-targeted clauses | "
        f"{counts['v15_cumulative_targeted_unsupported_clauses']} |",
        "| Changed draft next actions (rows/groups) | 18 / 2 |",
        "| Changed groups, contacts, locators or original requests | 0 |",
        "",
        "| Draft request group | New selected lead | V15 draft next action |",
        "| --- | --- | --- |",
    ]
    lines.extend(
        f"| {group['request_group_id']} | {group['v15_reviewed_source_ids'][0]} | "
        f"{group['v15_next_action']} |"
        for group in groups
    )
    lines += [
        "",
        "LEG locators do not establish 2027 law, duty, contract or performance. "
        "DAT's internal inquiry does not establish a delegated customer request, "
        "complete record population or rights completion; its Messy exception remains OPEN.",
        "",
        "Every request remains `DRAFT_NOT_SENT`; all 409 A/B P1 tasks remain "
        "`NOT_STARTED`/`NOT_RUN`. No external message, accepted no-event/N/A decision, "
        "clause satisfaction, audit task credit, fresh pair, Key, grade or Atlas write.",
        "",
    ]
    return "\n".join(lines)
