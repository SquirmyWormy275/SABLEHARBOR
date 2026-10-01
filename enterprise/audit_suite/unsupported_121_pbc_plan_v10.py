"""Bounded POL004 CC5.3 source lead for the frozen unsupported PBC plan."""

from __future__ import annotations

from pathlib import Path

from . import company_pol004_procedure_trace_2027 as procedure
from . import unsupported_121_pbc_plan as pinned
from . import unsupported_121_pbc_plan_v9 as prior
from .documentary_283_route_reconciliation_v6 import _p1_inventory, _pinned_db

SCHEMA = "SH_UNSUPPORTED_121_PAIRED_SOURCE_REQUEST_PLAN_V10"
BASE = "enterprise/generated/audit-suite"
V9_PLAN = "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V9_2026-09-30.json"
V9_REVIEW = f"{BASE}/unsupported-121-pbc-plan-v9-2026-09-30/independent-review-main-v1/REVIEW.json"
SOURCE_ROOT = f"{BASE}/company-pol004-procedure-trace-2027-09-30"
SOURCE_RUN = f"{SOURCE_ROOT}/main-run-v1"
SOURCE_REVIEW = f"{SOURCE_ROOT}/independent-review-main-v1/REVIEW.json"
SOURCE_MANIFEST = f"{SOURCE_RUN}/RUN-MANIFEST.json"
SOURCE_RECEIPT = f"{SOURCE_RUN}/SOURCE_RECEIPT.json"
SOURCE_DB = f"{SOURCE_RUN}/company.sqlite3"
PINS = {
    V9_PLAN: "3ee6f8a8dde7fe5502a55074e6861cab9aabf119a1657b447514e1410641ccff",
    V9_REVIEW: "eec6fc792c71849e34f25b280ef064fe29463860e1d1edff6102a16539a0958b",
    SOURCE_REVIEW: "2c0e96babf915c42d7d056de9ec87c30bc8966ddab126343ec444a1bad715143",
    SOURCE_MANIFEST: "2d81554213354d8dc76d167fcc624bb1fb98b7ee5c44c0a75d4990ddf8e4f266",
    SOURCE_RECEIPT: "442ddf2a36185460df20b04e00d63f12f877a3ef751f5f55cd9858fb9502af54",
    SOURCE_DB: "62c71eca6b9186936e89c6569735a6ea74b8d4909d356d2fb794a9e437d2d4bb",
}
P1_FREEZE = prior.P1_FREEZE
GROUP = "SH-POL-004"
TASK = procedure.TASK
SOURCE = "POL004_SELECTED_PROCEDURE_TRACE_V1"
SOURCE_LIMIT = (
    "One selected fictional due-time trial with 7 Clean and 9 Messy company-native "
    "originals. The 2026 broader policy/control-governance standard is OPEN; "
    "SH-GOV-DOC-001 v0.1.0 is an approved design standard only, and the fictional "
    "v0.2 distribution procedure remains pending authorized approval. Clean records "
    "two on-time local endpoint copies. Messy retains a missed endpoint, false close, "
    "challenge, late backfill, historical missed interval and expired unapproved "
    "exception. No effective enterprise procedure, human delivery, complete "
    "population, actual operation, independent test or authored CC5.3 satisfaction."
)
NEXT_ACTION_ADDENDUM = (
    "Inspect the exact reviewed fictional POL004 7-Clean/9-Messy due-time procedure "
    "originals only as a selected CC5.3 discovery lead. Preserve the policy-only "
    "rejection, Messy false close, dated challenge, backfill correction and OPEN "
    "expired historical exception. Request the authorized effective enterprise policy "
    "and execution procedure, trigger and responsible-person delegation, dated "
    "result/correction originals, complete selected-period population and qualified "
    "independent review. The 2026 broader policy remains OPEN; the approved document "
    "standard is design-only and the fictional v0.2 procedure approval is pending. "
    "Do not treat this trial as policy approval, actual operation or CC5.3 satisfaction."
)
REF_FIELDS = prior.REF_FIELDS


class V10SourceRequestError(prior.V9SourceRequestError):
    """A reviewed source, exact V9 prefix or no-credit boundary changed."""


def _selected_refs(receipt: dict, old: dict) -> dict[str, list[dict]]:
    """Reconcile exact selected POL004 originals and the still-unsupported route."""
    if (
        receipt.get("schema") != procedure.SCHEMA
        or receipt.get("task_id") != TASK
        or receipt.get("selected_authored_clause") != procedure.CLAUSE
        or receipt.get("branch_ids") != procedure.BRANCHES
        or receipt.get("branch_counts") != {"CLEAN": 7, "MESSY": 9}
        or receipt.get("native_count") != 16
        or receipt.get("enterprise_policy_status_2026") != "OPEN"
        or receipt.get("design_standard_approved_only") is not True
        or receipt.get("procedure_authority") != "PENDING_AUTHORIZED_DECISION"
        or receipt.get("messy_false_close_corrected") is not True
        or receipt.get("messy_missed_interval_retained") is not True
        or receipt.get("messy_exception_open") is not True
        or any(
            receipt.get(key) is not False
            for key in (
                "full_policy_or_procedure_population",
                "actual_operation",
                "source_complete",
                "audit_task_credit",
                "active_P1_mutated",
            )
        )
    ):
        raise V10SourceRequestError("POL004 selected procedure authority or scope differs")
    refs = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        route = receipt.get("route_disposition", {}).get(side, {})
        prior_row = next(
            row for row in old["rows"] if row["side"] == side and row["task_id"] == TASK
        )
        if (
            route.get("task_id") != TASK
            or route.get("authored_test_clause") != prior_row["authored_test_clause"]
            or route.get("screen_row_sha256") != prior_row["screen_row_sha256"]
            or route.get("classification") != "UNSUPPORTED_EXACT_CLAUSE"
            or route.get("current_status") != "NOT_STARTED"
            or route.get("current_conclusion") != "NOT_RUN"
            or route.get("audit_task_credit") is not False
            or prior_row["v9_targeted_source_ids"]
            or prior_row["v9_reviewed_source_ids"]
        ):
            raise V10SourceRequestError("POL004 reviewed source/V9 route join differs")
        selected = [
            row
            for row in receipt["native_originals"]
            if row["branch"] == procedure.BRANCHES[scenario]
        ]
        if (
            len(selected) != len(procedure.PLAN[scenario])
            or [(row["system"], row["record"]) for row in selected]
            != [(system, record) for system, record, _, _ in procedure.PLAN[scenario]]
            or any(row["version"] != 1 for row in selected)
        ):
            raise V10SourceRequestError("POL004 native procedure roster differs")
        refs[side] = [{key: row[key] for key in REF_FIELDS} for row in selected]
    return refs


def _extend(old: dict, receipt: dict, freeze: dict) -> dict:
    """Keep the complete V9 prefix; append only a selected POL004 draft action."""
    if (
        old.get("schema") != prior.SCHEMA
        or old.get("p1_freeze") != freeze
        or len(old.get("rows", [])) != 242
        or len(old.get("request_groups", [])) != 30
        or len(old.get("group_delta", [])) != 30
        or old.get("audit_task_credit") is not False
        or old.get("active_pair_mutated") is not False
        or old.get("external_messages_sent") != 0
        or old.get("accepted_na_determinations") != 0
        or any(
            old["active_p1_tasks"][side]
            != {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"}
            for side in "AB"
        )
    ):
        raise V10SourceRequestError("Reviewed V9 request or active P1 denominator differs")
    refs = _selected_refs(receipt, old)
    rows = []
    for previous in old["rows"]:
        row = dict(previous)
        side, task, group = row["side"], row["task_id"], row["request_group_id"]
        selected = task == TASK
        if (
            row["pbc_request_status"] != "DRAFT_NOT_SENT"
            or row["current_task_status"] != "NOT_STARTED"
            or row["current_task_conclusion"] != "NOT_RUN"
            or row["task_credit"] is not False
            or row["accepted_nonoccurrence_status"] == "ACCEPTED"
            or (selected and (group != GROUP or row["control_id"] != GROUP))
        ):
            raise V10SourceRequestError("V9 task/request or selected group boundary differs")
        row["v10_reviewed_source_ids"] = [SOURCE] if selected else []
        row["v10_source_limits"] = {SOURCE: SOURCE_LIMIT} if selected else {}
        row["v10_source_record_refs"] = {SOURCE: refs[side]} if selected else {}
        row["v10_targeted_source_ids"] = list(row["v9_targeted_source_ids"])
        row["v10_next_action"] = (
            row["v9_next_action"] + " " + NEXT_ACTION_ADDENDUM
            if group == GROUP
            else row["v9_next_action"]
        )
        row["v10_next_action_changed_from_v9"] = group == GROUP
        rows.append(row)
    groups, deltas = [], []
    for previous_group, previous_delta in zip(
        old["request_groups"], old["group_delta"], strict=True
    ):
        group = dict(previous_group)
        delta = dict(previous_delta)
        name = group["request_group_id"]
        selected = name == GROUP
        if (
            delta["request_group_id"] != name
            or (selected and (group["control_id"], group["routes_per_side"]) != (GROUP, 1))
            or group["request_status"] != "DRAFT_NOT_SENT"
        ):
            raise V10SourceRequestError("V9 POL004 group/unsent boundary differs")
        leads = [SOURCE] if selected else []
        limits = {SOURCE: SOURCE_LIMIT} if selected else {}
        source_refs = {side: {TASK: {SOURCE: refs[side]}} if selected else {} for side in "AB"}
        action = (
            group["v9_next_action"] + " " + NEXT_ACTION_ADDENDUM
            if selected
            else group["v9_next_action"]
        )
        group.update(
            {
                "v10_reviewed_source_ids": leads,
                "v10_source_limits": limits,
                "v10_source_record_refs_by_side": source_refs,
                "v10_next_action": action,
                "v10_next_action_changed_from_v9": selected,
            }
        )
        delta.update(
            {
                "v10_reviewed_source_ids": leads,
                "v10_source_limits": limits,
                "v10_source_record_refs_by_side": source_refs,
                "v9_next_action_before_v10": previous_group["v9_next_action"],
                "v10_next_action": action,
                "v10_next_action_changed_from_v9": selected,
            }
        )
        groups.append(group)
        deltas.append(delta)
    counts = {}
    for side in "AB":
        selected = [row for row in rows if row["side"] == side]
        affected = sum(
            bool(any(row[f"v{v}_reviewed_source_ids"] for v in range(5, 11))) for row in selected
        )
        targeted = sum(bool(row["v10_targeted_source_ids"]) for row in selected)
        prior_counts = old["counts"][side]
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
            or sum(bool(row["v10_reviewed_source_ids"]) for row in selected) != 1
            or prior_counts["v9_cumulative_reviewed_source_affected_unsupported_clauses"] != 22
            or prior_counts["v9_cumulative_targeted_unsupported_clauses"] != 34
            or affected != 23
            or targeted != 34
        ):
            raise V10SourceRequestError("V10 unsupported/POL004/no-event denominator differs")
        counts[side] = {
            **prior_counts,
            "v10_new_reviewed_source_leads": 1,
            "v10_newly_source_affected_unsupported_clauses": 1,
            "v10_selected_source_affected_request_groups": 1,
            "v10_next_action_changes_from_v9": 1,
            "v10_cumulative_reviewed_source_affected_unsupported_clauses": 23,
            "v10_cumulative_targeted_unsupported_clauses": 34,
            "v10_cumulative_changed_request_groups": 11,
            "v10_grouping_or_contact_changes": 0,
        }
    if (
        counts["A"] != counts["B"]
        or len(groups) != 30
        or len({g["request_group_id"] for g in groups}) != 30
        or sum(g["v10_next_action_changed_from_v9"] for g in groups) != 1
        or sum(g["v10_next_action_changed_from_v9"] for g in deltas) != 1
    ):
        raise V10SourceRequestError("Paired POL004 draft group delta differs")
    return {
        "schema": SCHEMA,
        "as_of": "2026-09-30",
        "source_pins": {**old["source_pins"], **PINS},
        "p1_freeze": freeze,
        "active_p1_tasks": old["active_p1_tasks"],
        "reviewed_route_roster": old["reviewed_route_roster"],
        "counts": counts,
        "rows": rows,
        "request_groups": groups,
        "group_delta": deltas,
        "candidate_owner_source_queues": old["candidate_owner_source_queues"],
        "nonoccurrence_acceptance_protocol": old["nonoccurrence_acceptance_protocol"],
        "limits": [
            *old["limits"],
            "All V9 row, group, contact, locator and original-request fields remain exact; "
            "only SH-POL-004 gains a V10 draft next action and selected native lead.",
            "The 2026 broader policy is OPEN, the approved corporate document standard "
            "is design-only, and the fictional v0.2 procedure approval is pending.",
            "CC5.3 remains UNSUPPORTED_EXACT_CLAUSE and NOT_STARTED/NOT_RUN. Messy false "
            "close, later correction, missed interval and open expired exception remain visible.",
            "No complete population, deployed procedure, human delivery, independent "
            "operating test, Type 2 period, N/A determination or audit task credit.",
        ],
        "external_messages_sent": 0,
        "fresh_pair_created": False,
        "source_complete": False,
        "audit_task_credit": False,
        "accepted_na_determinations": 0,
        "active_pair_mutated": False,
    }


def build(repository: Path, private_repository: Path) -> dict:
    """Reperform reviewed V9 and the selected POL004 main-native source."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    freeze = _p1_inventory(private)
    if freeze != P1_FREEZE:
        raise V10SourceRequestError("Frozen P1 inventory differs")
    old_pinned = pinned._pinned(repository / V9_PLAN, PINS[V9_PLAN])
    old_review = pinned._pinned(private / V9_REVIEW, PINS[V9_REVIEW], private=True)
    source_review = pinned._pinned(private / SOURCE_REVIEW, PINS[SOURCE_REVIEW], private=True)
    source_manifest = pinned._pinned(private / SOURCE_MANIFEST, PINS[SOURCE_MANIFEST], private=True)
    source_pinned = pinned._pinned(private / SOURCE_RECEIPT, PINS[SOURCE_RECEIPT], private=True)
    _pinned_db(private, {"path": SOURCE_DB, "sha256": PINS[SOURCE_DB]})
    if (
        old_review.get("verdict")
        != "PASS_READ_ONLY_UNSUPPORTED_121_PBC_V9_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or old_review.get("main_head") != "97faf1da14643bb35fc4b28ef24ffff0cdeaadc8"
        or old_review.get("main_tracked_sha256", {}).get(V9_PLAN) != PINS[V9_PLAN]
        or old_review.get("p1_freeze") != freeze
        or old_review.get("audit_task_credit") is not False
        or source_review.get("verdict")
        != "PASS_SELECTED_POL004_PROCEDURE_TRACE_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or source_review.get("integration_commits_in_order")
        != [
            "83c2f3ea37aa63b3a1904cd10f74b724e207b7c6",
            "c92d43e0346921e31889baf4dfbea55ade09a765",
        ]
        or source_review.get("main_run_sha256")
        != {
            "RUN-MANIFEST.json": PINS[SOURCE_MANIFEST],
            "SOURCE_RECEIPT.json": PINS[SOURCE_RECEIPT],
            "company.sqlite3": PINS[SOURCE_DB],
        }
        or source_review.get("main_tracked_sha256", {}).get(
            "enterprise/audit_suite/company_pol004_procedure_trace_2027.py"
        )
        != source_manifest.get("module_sha256")
        or source_review.get("p1_freeze") != freeze
        or source_review.get("source_complete") is not False
        or source_review.get("audit_task_credit") is not False
        or source_manifest.get("source_receipt_sha256") != PINS[SOURCE_RECEIPT]
        or source_manifest.get("native_db_sha256") != PINS[SOURCE_DB]
        or source_manifest.get("native_count") != 16
    ):
        raise V10SourceRequestError("Independent V9/POL004 review join differs")
    old = prior.build(repository, private)
    receipt = procedure.verify(
        private / SOURCE_RUN, repository=repository, private_repository=private
    )
    if old != old_pinned or receipt != source_pinned:
        raise V10SourceRequestError("Reviewed V9 or POL004 native source fails replay")
    result = _extend(old, receipt, freeze)
    if _p1_inventory(private) != freeze:
        raise V10SourceRequestError("Frozen P1 changed during read-only PBC build")
    return result


def markdown(result: dict) -> str:
    """Render the one-group POL004 draft delta without audit task credit."""
    counts = result["counts"]["A"]
    group = next(g for g in result["request_groups"] if g["request_group_id"] == GROUP)
    lines = [
        "# Unsupported exact clauses: selected POL004 request delta V10",
        "",
        "All 121 unsupported authored clauses per side remain unsupported across 30 "
        "draft unsent request groups. Every V9 row, group, contact and original request "
        "field is retained.",
        "",
        "| Per-side measure | Count |",
        "| --- | ---: |",
        f"| Unsupported authored clauses | {counts['unsupported_exact_clauses']} |",
        "| Possible unaccepted no-event reviews | "
        f"{counts['possible_nonoccurrence_review_candidates']} |",
        "| New selected POL004 source leads | 1 |",
        "| Newly source-affected clauses | 1 (CC5.3) |",
        "| Cumulative source-affected clauses | "
        f"{counts['v10_cumulative_reviewed_source_affected_unsupported_clauses']} |",
        "| Cumulative route-targeted unsupported clauses | "
        f"{counts['v10_cumulative_targeted_unsupported_clauses']} |",
        "| V10 changed draft next actions | 1 |",
        "| Changed groups, contacts, locators or original requests | 0 |",
        "",
        "The reviewed local trial joins 7 Clean and 9 Messy native originals to one "
        "due-time distribution variation check. It rejects policy-only sufficiency. "
        "The 2026 enterprise policy remains OPEN, the corporate document standard is "
        "approved as design only, and fictional procedure approval remains pending. "
        "Messy false close, challenge, backfill and open expired exception remain visible. "
        "The authored CC5.3 route remains unsupported and unrun.",
        "",
        "| Request group | New V10 reviewed lead | V10 draft next action |",
        "| --- | --- | --- |",
        f"| {GROUP} | {SOURCE} | {group['v10_next_action']} |",
        "",
        "All requests remain `DRAFT_NOT_SENT`; all 409 A/B P1 tasks remain "
        "`NOT_STARTED`/`NOT_RUN`. No message, accepted no-event or N/A decision, "
        "audit task credit, fresh pair, Key, grade or Atlas write was issued.",
        "",
    ]
    return "\n".join(lines)
