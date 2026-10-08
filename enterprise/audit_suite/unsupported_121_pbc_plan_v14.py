"""Draft-only selected governance leads for two unsupported CC1.2 requests."""

from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path

from . import company_gov_selected_oversight_2027 as source
from . import documentary_283_route_reconciliation_v16 as route
from . import unsupported_121_pbc_plan as pinned
from . import unsupported_121_pbc_plan_v13 as prior
from .documentary_283_route_reconciliation_v6 import _p1_inventory, _pinned_db

SCHEMA = "SH_UNSUPPORTED_121_PAIRED_SOURCE_REQUEST_PLAN_V14"
BASE = "enterprise/generated/audit-suite"
V13_PLAN = "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V13_2026-10-01.json"
V13_RUN = f"{BASE}/unsupported-121-pbc-plan-v13-2026-10-01/main-run-v1/PLAN.json"
V13_REVIEW = (
    f"{BASE}/unsupported-121-pbc-plan-v13-2026-10-01/independent-review-main-v1/REVIEW.json"
)
ROUTE_LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V16_2026-10-01.json"
ROUTE_RUN = f"{BASE}/documentary-283-route-reconciliation-v16-2026-10-01/main-run-v1/LEDGER.json"
ROUTE_REVIEW = (
    f"{BASE}/documentary-283-route-reconciliation-v16-2026-10-01/"
    "independent-review-main-v1/REVIEW.json"
)
SOURCE_RUN = f"{BASE}/company-gov-selected-oversight-2026-10-01/main-run-v1"
SOURCE_REVIEW = (
    f"{BASE}/company-gov-selected-oversight-2026-10-01/independent-review-main-v1/REVIEW.json"
)
SOURCE_MANIFEST = f"{SOURCE_RUN}/MANIFEST.json"
SOURCE_RECEIPT = f"{SOURCE_RUN}/RECEIPT.json"
SOURCE_DB = f"{SOURCE_RUN}/company.sqlite3"
PENDING = "PENDING_INDEPENDENT_MAIN_REVIEW_SHA256"
PINS = {
    V13_PLAN: "87efb4318598be3f15642062950f771b23ad51bdabddf1b64948516f8daf6d09",
    V13_RUN: "87efb4318598be3f15642062950f771b23ad51bdabddf1b64948516f8daf6d09",
    V13_REVIEW: "35416defe76a2938a12c93f8d2ac3e12226a42301d095a0f68332f84d5b0cb40",
    ROUTE_LEDGER: "cd3b55409e9e0112b49d060cfbbacf329660422d0c4e1b2002ec220af5bad5a3",
    ROUTE_RUN: "cd3b55409e9e0112b49d060cfbbacf329660422d0c4e1b2002ec220af5bad5a3",
    ROUTE_REVIEW: "138bc8e7cd5e701d0507e4dcb6228364c3406aa097d12d14d9753c456ae60b34",
    SOURCE_REVIEW: "54f59bd5a7db74ab29ead5d322908f4ad9e844c746c2f1b6f0cf3b0731bbcb01",
    SOURCE_MANIFEST: "09cee311aac8f62cc5aee39626fccf67b6bbb5a8be4a1c218f533a7c7c7cbad4",
    SOURCE_RECEIPT: "6c4b5a9c56e930e7875667fc3cd85e7825f69a5e4901f9d940c2f10ab29c40bd",
    SOURCE_DB: "81aef24a796a07e4daf2fc32f1dcfec10712a944b6d58f757eae2a73ef03228e",
}
P1_FREEZE = prior.P1_FREEZE
GROUPS = route.CONTROLS
TASKS = route.AUTHORED
SOURCE = route.SOURCE
SOURCE_LIMIT = route.LIMIT
REF_FIELDS = route.IDENTITY
NEXT_ACTION_ADDENDUM = (
    "Inspect the exact selected fictional 2027 Corporate Secretary originals (9 Clean/14 "
    "Messy) as one branch-matched discovery lead, not a collective decision. Clean "
    "reviews only its SEC003 selected finding and closure. Messy preserves the false-clean "
    "3/4 signoff, AS-P008 self-review, OPEN SEC003 exception, omitted first committee "
    "packet, missing director questionnaire, false closure, later corrected packet and "
    "OPEN governance exception. Obtain period-valid approved charters, complete director "
    "composition and conflict/eligibility population, returned declarations, recusals, "
    "actual committee attendance/quorum and adopted minutes challenging the control "
    "failure, Board escalation and independent exception follow-up. A secretary or "
    "review contact cannot supply collective approval. The selected drafts establish no "
    "authored CC1.2 satisfaction, full-period operation or audit task credit."
)


class V14SourceRequestError(prior.V13SourceRequestError):
    """Reviewed GOV source, route, PBC prefix or no-credit gate changed."""


def _selected_refs(receipt: dict, ledger: dict, old: dict) -> dict[str, list[dict]]:
    """Require branch-matched reviewed GOV tuples in both authored route rows."""
    if (
        receipt.get("schema") != source.SCHEMA
        or receipt.get("branches") != source.BRANCHES
        or receipt.get("native_version_counts") != {"CLEAN": 9, "MESSY": 14}
        or receipt.get("selected_case_count") != 1
        or receipt.get("target_task_ids") != list(source.TARGETS)
        or receipt.get("spec_sha256") != route.PINS["gov_spec"]["sha256"]
        or receipt.get("source_pins") != {**source.TRACKED_PINS, **source.PRIVATE_PINS}
        or receipt.get("clean_selected_finding_status") != "CLOSED_SELECTED_ONLY"
        or receipt.get("messy_historical_sec003_exception_status") != "OPEN"
        or receipt.get("messy_historical_governance_exception_status") != "OPEN"
        or receipt.get("real_external_messages_sent") != 0
        or any(
            receipt.get(key) is not False
            for key in (
                "actual_board_meeting",
                "legal_quorum_established",
                "adopted_minutes",
                "complete_oversight_population",
                "authored_cc12_clause_satisfied",
                "independent_assurance_completed",
                "actual_phi_processing",
                "source_complete",
                "fresh_audit_pair_created",
                "audit_task_credit",
            )
        )
        or ledger.get("schema") != route.SCHEMA
        or ledger.get("as_of") != "2026-10-01"
        or ledger.get("p1_freeze") != P1_FREEZE
        or ledger.get("audit_task_credit") is not False
        or ledger.get("active_pair_mutated") is not False
        or ledger.get("active_p1_tasks") != old["active_p1_tasks"]
        or any(ledger["counts"][side]["targeted_integrated_route_count"] != 183 for side in "AB")
    ):
        raise V14SourceRequestError("GOV selected source or reviewed route scope differs")
    refs = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        records = receipt.get("records", {}).get(scenario, [])
        upstream = receipt.get("upstream_original_refs", {}).get(scenario, [])
        if (
            not isinstance(records, list)
            or len(records) != len(route.ROSTER[scenario])
            or tuple((row.get("system"), row.get("record")) for row in records)
            != route.ROSTER[scenario]
            or not isinstance(upstream, list)
            or len(upstream) != (2 if scenario == "CLEAN" else 3)
            or any(row.get("branch") != source.sec3.BRANCHES[scenario] for row in upstream)
            or any(
                row.get("company") != source.COMPANY
                or row.get("branch") != source.BRANCHES[scenario]
                or row.get("version") != 1
                or row.get("origin") != "AUTHORED_TRAINING_SOURCE"
                or any(not row.get(key) for key in REF_FIELDS)
                for row in records
            )
        ):
            raise V14SourceRequestError("GOV branch native original roster differs")
        selected = [{key: row[key] for key in REF_FIELDS} for row in records]
        for group, task in zip(GROUPS, TASKS, strict=True):
            route_row = next(
                row for row in ledger["rows"] if row["side"] == side and row["task_id"] == task
            )
            previous = next(
                row for row in old["rows"] if row["side"] == side and row["task_id"] == task
            )
            if (
                route_row.get("control_id") != group
                or route_row.get("classification") != "UNSUPPORTED_EXACT_CLAUSE"
                or route_row.get("test_gate_basis") != "AUTHORED_TASK_CLAUSE"
                or route_row.get("authored_test_clause") != route.CLAUSE
                or route_row.get("remaining_test_gate") != route.CLAUSE
                or route_row.get("v16_reviewed_source_ids") != [SOURCE]
                or route_row.get("v16_source_limits") != {SOURCE: SOURCE_LIMIT}
                or route_row.get("v16_source_record_refs") != {SOURCE: selected}
                or route_row.get("targeted_integrated_source_ids") != [SOURCE]
                or route_row.get("candidate_or_design_source_ids") != []
                or route_row.get("current_status") != "NOT_STARTED"
                or route_row.get("current_conclusion") != "NOT_RUN"
                or route_row.get("audit_task_credit") is not False
                or previous.get("control_id") != group
                or previous.get("request_group_id") != group
                or previous.get("authored_test_clause") != route.CLAUSE
                or previous.get("remaining_test_gate") != route.CLAUSE
                or previous.get("v13_reviewed_source_ids") != []
                or previous.get("v13_targeted_source_ids") != []
            ):
                raise V14SourceRequestError("Exact GOV authored route or source refs differ")
        refs[side] = selected
    return refs


def _extend(old: dict, ledger: dict, receipt: dict, freeze: dict) -> dict:
    """Retain V13 request fields and add only two GOV selected draft leads."""
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
            for side in "AB"
        )
    ):
        raise V14SourceRequestError("Reviewed V13 PBC or P1 denominator differs")
    refs = _selected_refs(receipt, ledger, old)
    route_rows = {(row["side"], row["task_id"]): row for row in ledger["rows"]}
    rows = []
    for previous in old["rows"]:
        row = deepcopy(previous)
        side, task, group = row["side"], row["task_id"], row["request_group_id"]
        selected = task in TASKS
        route_row = route_rows[(side, task)]
        if (
            row["pbc_request_status"] != "DRAFT_NOT_SENT"
            or row["current_task_status"] != "NOT_STARTED"
            or row["current_task_conclusion"] != "NOT_RUN"
            or row["task_credit"] is not False
            or row["accepted_nonoccurrence_status"] == "ACCEPTED"
            or route_row["classification"] != "UNSUPPORTED_EXACT_CLAUSE"
            or (selected and group not in GROUPS)
        ):
            raise V14SourceRequestError("V13 task/request or route boundary differs")
        row["v14_reviewed_source_ids"] = [SOURCE] if selected else []
        row["v14_source_limits"] = {SOURCE: SOURCE_LIMIT} if selected else {}
        row["v14_source_record_refs"] = {SOURCE: refs[side]} if selected else {}
        row["v14_targeted_source_ids"] = list(route_row["targeted_integrated_source_ids"])
        if not selected and row["v14_targeted_source_ids"] != row["v13_targeted_source_ids"]:
            raise V14SourceRequestError("Unselected unsupported route target changed")
        row["v14_next_action"] = (
            row["v13_next_action"] + " " + NEXT_ACTION_ADDENDUM
            if selected
            else row["v13_next_action"]
        )
        row["v14_next_action_changed_from_v13"] = selected
        rows.append(row)
    groups, deltas = [], []
    for previous_group, previous_delta in zip(
        old["request_groups"], old["group_delta"], strict=True
    ):
        group = deepcopy(previous_group)
        delta = deepcopy(previous_delta)
        name = group["request_group_id"]
        selected = name in GROUPS
        if (
            delta["request_group_id"] != name
            or (selected and (group["control_id"], group["routes_per_side"]) != (name, 1))
            or group["request_status"] != "DRAFT_NOT_SENT"
            or group["task_credit"] is not False
        ):
            raise V14SourceRequestError("V13 GOV group or unsent boundary differs")
        task = TASKS[GROUPS.index(name)] if selected else None
        leads = [SOURCE] if selected else []
        limits = {SOURCE: SOURCE_LIMIT} if selected else {}
        source_refs = {side: {task: {SOURCE: refs[side]}} if selected else {} for side in "AB"}
        action = (
            group["v13_next_action"] + " " + NEXT_ACTION_ADDENDUM
            if selected
            else group["v13_next_action"]
        )
        group.update(
            {
                "v14_reviewed_source_ids": leads,
                "v14_source_limits": limits,
                "v14_source_record_refs_by_side": source_refs,
                "v14_next_action": action,
                "v14_next_action_changed_from_v13": selected,
            }
        )
        delta.update(
            {
                "v14_reviewed_source_ids": leads,
                "v14_source_limits": limits,
                "v14_source_record_refs_by_side": source_refs,
                "v13_next_action_before_v14": previous_group["v13_next_action"],
                "v14_next_action": action,
                "v14_next_action_changed_from_v13": selected,
            }
        )
        groups.append(group)
        deltas.append(delta)
    counts = {}
    for side in "AB":
        selected = [row for row in rows if row["side"] == side]
        affected = sum(
            bool(any(row[f"v{version}_reviewed_source_ids"] for version in range(5, 15)))
            for row in selected
        )
        targeted = sum(bool(row["v14_targeted_source_ids"]) for row in selected)
        previous_counts = old["counts"][side]
        if (
            len(selected) != 121
            or len({row["task_id"] for row in selected}) != 121
            or len({row["control_id"] for row in selected}) != 28
            or sum(row["possible_nonoccurrence_review_candidate"] for row in selected) != 53
            or any(
                row["accepted_nonoccurrence_status"] != "NOT_ESTABLISHED"
                for row in selected
                if row["possible_nonoccurrence_review_candidate"]
            )
            or sum(bool(row["v14_reviewed_source_ids"]) for row in selected) != 2
            or previous_counts["v13_cumulative_reviewed_source_affected_unsupported_clauses"] != 27
            or previous_counts["v13_cumulative_targeted_unsupported_clauses"] != 35
            or previous_counts["v13_cumulative_changed_request_groups"] != 15
            or affected != 29
            or targeted != 37
        ):
            raise V14SourceRequestError("V14 unsupported/GOV/no-event denominator differs")
        counts[side] = {
            **previous_counts,
            "v14_new_reviewed_source_leads": 2,
            "v14_newly_source_affected_unsupported_clauses": 2,
            "v14_newly_route_targeted_unsupported_clauses": 2,
            "v14_selected_source_affected_request_groups": 2,
            "v14_next_action_changes_from_v13": 2,
            "v14_cumulative_reviewed_source_affected_unsupported_clauses": 29,
            "v14_cumulative_targeted_unsupported_clauses": 37,
            "v14_cumulative_changed_request_groups": 17,
            "v14_grouping_or_contact_changes": 0,
        }
    if (
        counts["A"] != counts["B"]
        or len(groups) != 30
        or len({group["request_group_id"] for group in groups}) != 30
        or sum(group["v14_next_action_changed_from_v13"] for group in groups) != 2
        or sum(group["v14_next_action_changed_from_v13"] for group in deltas) != 2
    ):
        raise V14SourceRequestError("Paired GOV draft group delta differs")
    return {
        **old,
        "schema": SCHEMA,
        "as_of": "2026-10-01",
        "source_pins": {**old["source_pins"], **PINS},
        "v16_route_ledger_sha256": PINS[ROUTE_LEDGER],
        "counts": counts,
        "rows": rows,
        "request_groups": groups,
        "group_delta": deltas,
        "limits": [
            *old["limits"],
            "All V13 row, group, contact, locator and original-request fields remain exact; "
            "only SH-GOV-001/004 gain V14 draft next actions and selected native leads.",
            "Both authored CC1.2 clauses remain UNSUPPORTED_EXACT_CLAUSE and unrun. "
            "A selected committee-cycle draft is not a complete oversight period.",
            "No actual Board meeting, collective approval, legal quorum, adopted minutes, "
            "independent assurance, request send, accepted N/A/no-event decision, audit "
            "task credit, fresh pair, Key, grade or Atlas write.",
        ],
        "external_messages_sent": 0,
        "fresh_pair_created": False,
        "source_complete": False,
        "audit_task_credit": False,
        "accepted_na_determinations": 0,
        "active_pair_mutated": False,
    }


def build(repository: Path, private_repository: Path) -> dict:
    """Join pinned reviewed V13/V16 bytes and verify the selected GOV originals."""
    if any(re.fullmatch(r"[0-9a-f]{64}", PINS[rel]) is None for rel in (V13_REVIEW, ROUTE_REVIEW)):
        raise V14SourceRequestError("Pending independent main review pin")
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    freeze = _p1_inventory(private)
    if freeze != P1_FREEZE:
        raise V14SourceRequestError("Frozen P1 inventory differs")
    old_pinned = pinned._pinned(repository / V13_PLAN, PINS[V13_PLAN])
    old_main = pinned._pinned(private / V13_RUN, PINS[V13_RUN], private=True)
    old_review = pinned._pinned(private / V13_REVIEW, PINS[V13_REVIEW], private=True)
    route_pinned = pinned._pinned(repository / ROUTE_LEDGER, PINS[ROUTE_LEDGER])
    route_main = pinned._pinned(private / ROUTE_RUN, PINS[ROUTE_RUN], private=True)
    route_review = pinned._pinned(private / ROUTE_REVIEW, PINS[ROUTE_REVIEW], private=True)
    source_review = pinned._pinned(private / SOURCE_REVIEW, PINS[SOURCE_REVIEW], private=True)
    manifest = pinned._pinned(private / SOURCE_MANIFEST, PINS[SOURCE_MANIFEST], private=True)
    receipt = pinned._pinned(private / SOURCE_RECEIPT, PINS[SOURCE_RECEIPT], private=True)
    _pinned_db(private, {"path": SOURCE_DB, "sha256": PINS[SOURCE_DB]})
    if (
        old_pinned != old_main
        or route_pinned != route_main
        or old_review.get("schema") != "SH_INDEPENDENT_PRD_PBC_V13_MAIN_REVIEW_V1"
        or old_review.get("verdict") != "PASS_MAIN_DRAFT_ONLY_NO_AUDIT_CREDIT"
        or old_review.get("output_sha256", {}).get("PLAN.json") != PINS[V13_PLAN]
        or old_review.get("p1_freeze") != freeze
        or old_review.get("audit_task_credit") is not False
        or old_review.get("source_complete") is not False
        or old_review.get("fresh_audit_pair_created") is not False
        or route_review.get("schema") != "SH_INDEPENDENT_GOV_ROUTE_V16_MAIN_REVIEW_V1"
        or route_review.get("verdict") != "PASS_MAIN_SELECTED_GOV_LEAD_NO_AUDIT_CREDIT"
        or route_review.get("output_sha256", {}).get("LEDGER.json") != PINS[ROUTE_LEDGER]
        or route_review.get("p1_freeze") != freeze
        or route_review.get("audit_task_credit") is not False
        or route_review.get("source_complete") is not False
        or route_review.get("fresh_audit_pair_created") is not False
        or source_review.get("schema") != "SH_INDEPENDENT_GOV_SELECTED_OVERSIGHT_MAIN_REVIEW_V1"
        or source_review.get("verdict") != "PASS_MAIN_SELECTED_GOV_SOURCE_NO_AUDIT_CREDIT"
        or source_review.get("main_run_sha256")
        != {
            "MANIFEST.json": PINS[SOURCE_MANIFEST],
            "RECEIPT.json": PINS[SOURCE_RECEIPT],
            "company.sqlite3": PINS[SOURCE_DB],
        }
        or source_review.get("native_versions") != {"CLEAN": 9, "MESSY": 14}
        or source_review.get("p1_freeze") != freeze
        or source_review.get("source_complete") is not False
        or source_review.get("fresh_audit_pair_created") is not False
        or source_review.get("audit_task_credit") is not False
        or manifest.get("receipt_sha256") != PINS[SOURCE_RECEIPT]
        or manifest.get("db_sha256") != PINS[SOURCE_DB]
        or manifest.get("native_version_count") != 23
    ):
        raise V14SourceRequestError("Independent V13/V16/GOV review join differs")
    source.verify(private / SOURCE_RUN, repository=repository, private_repository=private)
    result = _extend(old_pinned, route_pinned, receipt, freeze)
    if _p1_inventory(private) != freeze:
        raise V14SourceRequestError("Frozen P1 changed during read-only PBC build")
    return result


def markdown(result: dict) -> str:
    """Render two bounded GOV draft deltas with collective-authority gates."""
    counts = result["counts"]["A"]
    groups = [
        next(group for group in result["request_groups"] if group["request_group_id"] == name)
        for name in GROUPS
    ]
    lines = [
        "# Unsupported exact clauses: selected GOV request delta V14",
        "",
        "All 121 unsupported authored clauses per side remain unsupported across 30 "
        "draft unsent groups. Every V13 row, group, contact, locator and original "
        "request field is retained.",
        "",
        "| Per-side measure | Count |",
        "| --- | ---: |",
        f"| Unsupported authored clauses | {counts['unsupported_exact_clauses']} |",
        "| Possible unaccepted no-event reviews | "
        f"{counts['possible_nonoccurrence_review_candidates']} |",
        "| New selected GOV authored leads | 2 |",
        "| Newly source-affected clauses | 2 |",
        "| Newly route-targeted clauses | 2 |",
        "| Cumulative source-affected clauses | "
        f"{counts['v14_cumulative_reviewed_source_affected_unsupported_clauses']} |",
        "| Cumulative route-targeted unsupported clauses | "
        f"{counts['v14_cumulative_targeted_unsupported_clauses']} |",
        "| V14 changed draft next actions | 2 |",
        "| Changed groups, contacts, locators or original requests | 0 |",
        "",
        "One selected fictional Corporate Secretary cycle supplies 9 Clean and 14 Messy "
        "native originals to the two authored GOV CC1.2 routes. Clean references only "
        "its SEC003 selected finding and closure. Messy retains false-clean, omitted "
        "packet, missing questionnaire, false close, correction and OPEN historical "
        "SEC003/governance exceptions. Neither branch has adopted collective minutes.",
        "",
        "| Request group | New V14 reviewed lead | V14 draft next action |",
        "| --- | --- | --- |",
    ]
    lines.extend(
        f"| {group['request_group_id']} | {SOURCE} | {group['v14_next_action']} |"
        for group in groups
    )
    lines += [
        "",
        "All requests remain `DRAFT_NOT_SENT`; all 409 A/B P1 tasks remain "
        "`NOT_STARTED`/`NOT_RUN`. No message, accepted no-event or N/A decision, "
        "collective approval, clause satisfaction, audit task credit, fresh pair, Key, "
        "grade or Atlas write was issued.",
        "",
    ]
    return "\n".join(lines)
