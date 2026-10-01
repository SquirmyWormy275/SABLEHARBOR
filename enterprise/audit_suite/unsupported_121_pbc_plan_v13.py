"""Bounded held PRD concern lead for three unsupported communication requests."""

from __future__ import annotations

from pathlib import Path

from . import company_prd_concern_intake_2027 as source
from . import documentary_283_route_reconciliation_v15 as route
from . import unsupported_121_pbc_plan as pinned
from . import unsupported_121_pbc_plan_v12 as prior
from .documentary_283_route_reconciliation_v6 import _p1_inventory, _pinned_db

SCHEMA = "SH_UNSUPPORTED_121_PAIRED_SOURCE_REQUEST_PLAN_V13"
BASE = "enterprise/generated/audit-suite"
V12_PLAN = "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V12_2026-09-30.json"
V12_REVIEW = (
    f"{BASE}/unsupported-121-pbc-plan-v12-2026-09-30/independent-review-main-v1/REVIEW.json"
)
ROUTE_LEDGER = f"{BASE}/documentary-283-route-reconciliation-v15-2026-09-30/main-run-v1/LEDGER.json"
ROUTE_REVIEW = (
    f"{BASE}/documentary-283-route-reconciliation-v15-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
SOURCE_RUN = f"{BASE}/company-prd-concern-intake-2026-09-30/main-run-v1"
SOURCE_REVIEW = (
    f"{BASE}/company-prd-concern-intake-2026-09-30/independent-review-main-v1/REVIEW.json"
)
SOURCE_MANIFEST = f"{SOURCE_RUN}/MANIFEST.json"
SOURCE_RECEIPT = f"{SOURCE_RUN}/RECEIPT.json"
SOURCE_DB = f"{SOURCE_RUN}/company.sqlite3"
PINS = {
    V12_PLAN: "30e8a28b8f6b85ea8732dbcd8b9256b78db001a3e7f42441d74fa5a92eeefb63",
    V12_REVIEW: "de68dd5ff83f46921cf93976406345ffac231824f5616c1b8f359dfb80307265",
    ROUTE_LEDGER: "bb3b74930b256f5396d2393438236e2bd9a3dd654d829080d0927129954a535c",
    ROUTE_REVIEW: "b9c20621f2512aeb66b8b7d02ba87a5fcc64f705a13208f610209cfabf950ff7",
    SOURCE_REVIEW: "695aa780d6bfd952e2b161fe0b21b8b01ae62c8e3db101686237532e57072794",
    SOURCE_MANIFEST: "a55481e58a8347d1539719ab02eff7f66b17ca7d87fb870935ccbe6b36898ff6",
    SOURCE_RECEIPT: "8fc7f4a4518e918975a13bdaac006336e6ffbdb5f03770e43e37e0506ec2ffe1",
    SOURCE_DB: "48b85f09899e5a74ef160e9bc10cd8c85ea128986086f1b73f1344d8739e4524",
}
P1_FREEZE = prior.P1_FREEZE
GROUPS = route.CONTROLS
TASKS = route.AUTHORED
SOURCE = route.SOURCE
SOURCE_LIMIT = route.LIMIT
REF_FIELDS = route.IDENTITY
NEXT_ACTION_ADDENDUM = (
    "Inspect the exact reviewed fictional concern-intake originals (8 Clean/13 Messy) "
    "only as one selected discovery lead. Verify the claimant, authorized customer "
    "contact and applicable commitment before treating any communication as delivered. "
    "Clean holds an internal response draft at unresolved authority; Messy preserves an "
    "omitted support role, denied local dispatch attempt, false completion, correction "
    "and OPEN historical exception. Obtain the complete applicable customer/channel "
    "population, governing terms and notice decision, accepted outbound delivery, "
    "separate customer receipt or acknowledgment where required, response, escalation "
    "and independent exception review. The local simulation establishes no real send, "
    "accepted fictional delivery, clause satisfaction or audit task credit."
)


class V13SourceRequestError(prior.V12SourceRequestError):
    """Reviewed PRD source, route, PBC prefix or no-credit gate changed."""


def _selected_refs(receipt: dict, ledger: dict, old: dict) -> dict[str, list[dict]]:
    """Require the same held original tuples in company source and all three routes."""
    if (
        receipt.get("schema") != source.SCHEMA
        or receipt.get("branches") != source.BRANCHES
        or receipt.get("native_version_counts") != {"CLEAN": 8, "MESSY": 13}
        or receipt.get("local_open_exception_counts") != {"CLEAN": 0, "MESSY": 1}
        or receipt.get("internal_draft_status")
        != {"CLEAN": "HELD", "MESSY": "HELD_AFTER_CORRECTION"}
        or receipt.get("selected_concern_count") != 1
        or receipt.get("real_external_messages_sent") != 0
        or receipt.get("fictional_accepted_deliveries") != 0
        or receipt.get("customer_acknowledgments") != 0
        or receipt.get("spec_sha256") != route.PINS["prd_spec"]["sha256"]
        or receipt.get("reviewed_prd_source_sha256") != source.UPSTREAM_HASHES
        or any(
            receipt.get(key) is not False
            for key in (
                "selected_claimant_verified",
                "actual_phi_processing",
                "source_complete",
                "fresh_audit_pair_created",
                "audit_task_credit",
            )
        )
        or ledger.get("schema") != route.SCHEMA
        or ledger.get("p1_freeze") != P1_FREEZE
        or ledger.get("audit_task_credit") is not False
        or ledger.get("active_pair_mutated") is not False
        or ledger.get("active_p1_tasks") != old["active_p1_tasks"]
    ):
        raise V13SourceRequestError("PRD concern source or reviewed route scope differs")
    refs = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        records = receipt.get("records", {}).get(scenario, [])
        selected = [{key: row[key] for key in REF_FIELDS} for row in records]
        if (
            len(records) != len(route.ROSTER[scenario])
            or tuple((row["system"], row["record"]) for row in records) != route.ROSTER[scenario]
            or any(
                row["company"] != source.COMPANY
                or row["branch"] != source.BRANCHES[scenario]
                or row["version"] != 1
                or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                for row in records
            )
        ):
            raise V13SourceRequestError("PRD concern native original roster differs")
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
                or route_row.get("v15_reviewed_source_ids") != [SOURCE]
                or route_row.get("v15_source_limits") != {SOURCE: SOURCE_LIMIT}
                or route_row.get("v15_source_record_refs") != {SOURCE: selected}
                or route_row.get("targeted_integrated_source_ids")
                != [*previous["v12_targeted_source_ids"], SOURCE]
                or route_row.get("candidate_or_design_source_ids") != []
                or route_row.get("current_status") != "NOT_STARTED"
                or route_row.get("current_conclusion") != "NOT_RUN"
                or route_row.get("audit_task_credit") is not False
                or previous.get("authored_test_clause") != route.CLAUSE
                or previous.get("remaining_test_gate") != route.CLAUSE
                or previous.get("request_group_id") != group
                or previous.get("control_id") != group
                or previous.get("v12_reviewed_source_ids") != []
                or previous.get("v12_targeted_source_ids") != ["PRD_INTERNAL_V2"]
            ):
                raise V13SourceRequestError("Exact PRD authored route or native roster differs")
        refs[side] = selected
    return refs


def _extend(old: dict, ledger: dict, receipt: dict, freeze: dict) -> dict:
    """Keep every V12 field and append three held PRD draft discovery leads."""
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
        raise V13SourceRequestError("Reviewed V12 PBC or P1 denominator differs")
    refs = _selected_refs(receipt, ledger, old)
    route_rows = {(row["side"], row["task_id"]): row for row in ledger["rows"]}
    rows = []
    for previous in old["rows"]:
        row = dict(previous)
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
            raise V13SourceRequestError("V12 task/request or route boundary differs")
        row["v13_reviewed_source_ids"] = [SOURCE] if selected else []
        row["v13_source_limits"] = {SOURCE: SOURCE_LIMIT} if selected else {}
        row["v13_source_record_refs"] = {SOURCE: refs[side]} if selected else {}
        row["v13_targeted_source_ids"] = list(route_row["targeted_integrated_source_ids"])
        if not selected and row["v13_targeted_source_ids"] != row["v12_targeted_source_ids"]:
            raise V13SourceRequestError("Unselected unsupported route target changed")
        row["v13_next_action"] = (
            row["v12_next_action"] + " " + NEXT_ACTION_ADDENDUM
            if selected
            else row["v12_next_action"]
        )
        row["v13_next_action_changed_from_v12"] = selected
        rows.append(row)
    groups, deltas = [], []
    for previous_group, previous_delta in zip(
        old["request_groups"], old["group_delta"], strict=True
    ):
        group = dict(previous_group)
        delta = dict(previous_delta)
        name = group["request_group_id"]
        selected = name in GROUPS
        if (
            delta["request_group_id"] != name
            or (selected and (group["control_id"], group["routes_per_side"]) != (name, 1))
            or group["request_status"] != "DRAFT_NOT_SENT"
            or group["task_credit"] is not False
        ):
            raise V13SourceRequestError("V12 PRD group or unsent boundary differs")
        task = TASKS[GROUPS.index(name)] if selected else None
        leads = [SOURCE] if selected else []
        limits = {SOURCE: SOURCE_LIMIT} if selected else {}
        source_refs = {side: {task: {SOURCE: refs[side]}} if selected else {} for side in "AB"}
        action = (
            group["v12_next_action"] + " " + NEXT_ACTION_ADDENDUM
            if selected
            else group["v12_next_action"]
        )
        group.update(
            {
                "v13_reviewed_source_ids": leads,
                "v13_source_limits": limits,
                "v13_source_record_refs_by_side": source_refs,
                "v13_next_action": action,
                "v13_next_action_changed_from_v12": selected,
            }
        )
        delta.update(
            {
                "v13_reviewed_source_ids": leads,
                "v13_source_limits": limits,
                "v13_source_record_refs_by_side": source_refs,
                "v12_next_action_before_v13": previous_group["v12_next_action"],
                "v13_next_action": action,
                "v13_next_action_changed_from_v12": selected,
            }
        )
        groups.append(group)
        deltas.append(delta)
    counts = {}
    for side in "AB":
        selected = [row for row in rows if row["side"] == side]
        affected = sum(
            bool(any(row[f"v{version}_reviewed_source_ids"] for version in range(5, 14)))
            for row in selected
        )
        targeted = sum(bool(row["v13_targeted_source_ids"]) for row in selected)
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
            or sum(bool(row["v13_reviewed_source_ids"]) for row in selected) != 3
            or previous_counts["v12_cumulative_reviewed_source_affected_unsupported_clauses"] != 24
            or previous_counts["v12_cumulative_targeted_unsupported_clauses"] != 35
            or previous_counts["v12_cumulative_changed_request_groups"] != 12
            or affected != 27
            or targeted != 35
        ):
            raise V13SourceRequestError("V13 unsupported/PRD/no-event denominator differs")
        counts[side] = {
            **previous_counts,
            "v13_new_reviewed_source_leads": 3,
            "v13_newly_source_affected_unsupported_clauses": 3,
            "v13_newly_route_targeted_unsupported_clauses": 0,
            "v13_selected_source_affected_request_groups": 3,
            "v13_next_action_changes_from_v12": 3,
            "v13_cumulative_reviewed_source_affected_unsupported_clauses": 27,
            "v13_cumulative_targeted_unsupported_clauses": 35,
            "v13_cumulative_changed_request_groups": 15,
            "v13_grouping_or_contact_changes": 0,
        }
    if (
        counts["A"] != counts["B"]
        or len(groups) != 30
        or len({group["request_group_id"] for group in groups}) != 30
        or sum(group["v13_next_action_changed_from_v12"] for group in groups) != 3
        or sum(group["v13_next_action_changed_from_v12"] for group in deltas) != 3
    ):
        raise V13SourceRequestError("Paired PRD draft group delta differs")
    return {
        "schema": SCHEMA,
        "as_of": "2026-10-01",
        "source_pins": {**old["source_pins"], **PINS},
        "p1_freeze": freeze,
        "active_p1_tasks": old["active_p1_tasks"],
        "reviewed_route_roster": old["reviewed_route_roster"],
        "v13_route_ledger_sha256": old["v13_route_ledger_sha256"],
        "v14_route_ledger_sha256": old["v14_route_ledger_sha256"],
        "v15_route_ledger_sha256": PINS[ROUTE_LEDGER],
        "counts": counts,
        "rows": rows,
        "request_groups": groups,
        "group_delta": deltas,
        "candidate_owner_source_queues": old["candidate_owner_source_queues"],
        "nonoccurrence_acceptance_protocol": old["nonoccurrence_acceptance_protocol"],
        "limits": [
            *old["limits"],
            "All V12 row, group, contact, locator and original-request fields remain exact; "
            "only SH-PRD-002/003/004 gain V13 draft next actions and selected native leads.",
            "Each authored external-communication clause remains UNSUPPORTED_EXACT_CLAUSE "
            "and unrun. One held concern is not a complete customer/channel population.",
            "Claimant identity, response authority, customer delivery and acknowledgment "
            "remain unresolved. Messy retains an OPEN historical exception.",
            "No real send, actual PHI, adopted notice duty, accepted fictional delivery, "
            "N/A or no-event decision, or audit task credit.",
        ],
        "external_messages_sent": 0,
        "fresh_pair_created": False,
        "source_complete": False,
        "audit_task_credit": False,
        "accepted_na_determinations": 0,
        "active_pair_mutated": False,
    }


def build(repository: Path, private_repository: Path) -> dict:
    """Fail closed on V12, reviewed V15 and held concern source, then replay inputs."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    freeze = _p1_inventory(private)
    if freeze != P1_FREEZE:
        raise V13SourceRequestError("Frozen P1 inventory differs")
    old_pinned = pinned._pinned(repository / V12_PLAN, PINS[V12_PLAN])
    old_review = pinned._pinned(private / V12_REVIEW, PINS[V12_REVIEW], private=True)
    route_pinned = pinned._pinned(private / ROUTE_LEDGER, PINS[ROUTE_LEDGER], private=True)
    route_review = pinned._pinned(private / ROUTE_REVIEW, PINS[ROUTE_REVIEW], private=True)
    source_review = pinned._pinned(private / SOURCE_REVIEW, PINS[SOURCE_REVIEW], private=True)
    manifest = pinned._pinned(private / SOURCE_MANIFEST, PINS[SOURCE_MANIFEST], private=True)
    receipt = pinned._pinned(private / SOURCE_RECEIPT, PINS[SOURCE_RECEIPT], private=True)
    _pinned_db(private, {"path": SOURCE_DB, "sha256": PINS[SOURCE_DB]})
    if (
        old_review.get("schema") != "SH_INDEPENDENT_ENG005_PBC_V12_MAIN_REVIEW_V1"
        or old_review.get("verdict") != "PASS_MAIN_DRAFT_ONLY_NO_AUDIT_CREDIT"
        or old_review.get("output_sha256", {}).get("PLAN.json") != PINS[V12_PLAN]
        or old_review.get("p1_freeze") != freeze
        or old_review.get("audit_task_credit") is not False
        or route_review.get("schema") != "SH_INDEPENDENT_PRD_ROUTE_V15_MAIN_REVIEW_V1"
        or route_review.get("verdict") != "PASS_MAIN_HELD_CONCERN_LEAD_NO_CREDIT"
        or route_review.get("output_sha256", {}).get("LEDGER.json") != PINS[ROUTE_LEDGER]
        or route_review.get("p1_freeze") != freeze
        or route_review.get("audit_task_credit") is not False
        or route_review.get("source_complete") is not False
        or source_review.get("schema") != "SH_INDEPENDENT_PRD_CONCERN_MAIN_REVIEW_V1"
        or source_review.get("verdict") != "PASS_MAIN_SELECTED_PRD_CONCERN_NO_AUDIT_CREDIT"
        or source_review.get("main_run_sha256")
        != {
            "MANIFEST.json": PINS[SOURCE_MANIFEST],
            "RECEIPT.json": PINS[SOURCE_RECEIPT],
            "company.sqlite3": PINS[SOURCE_DB],
        }
        or source_review.get("native_versions") != {"CLEAN": 8, "MESSY": 13}
        or source_review.get("p1_freeze") != freeze
        or source_review.get("source_complete") is not False
        or source_review.get("audit_task_credit") is not False
        or manifest.get("receipt_sha256") != PINS[SOURCE_RECEIPT]
        or manifest.get("db_sha256") != PINS[SOURCE_DB]
        or manifest.get("native_version_count") != 21
    ):
        raise V13SourceRequestError("Independent V12/V15/PRD review join differs")
    old = prior.build(repository, private)
    route_replayed = route.build(repository, private)
    source.verify(private / SOURCE_RUN, repository=repository, private_repository=private)
    if old != old_pinned or route_replayed != route_pinned:
        raise V13SourceRequestError("Reviewed V12 or V15 route fails replay")
    result = _extend(old, route_pinned, receipt, freeze)
    if _p1_inventory(private) != freeze:
        raise V13SourceRequestError("Frozen P1 changed during read-only PBC build")
    return result


def markdown(result: dict) -> str:
    """Render three held PRD draft deltas with explicit external-send gates."""
    counts = result["counts"]["A"]
    groups = [
        next(g for g in result["request_groups"] if g["request_group_id"] == name)
        for name in GROUPS
    ]
    lines = [
        "# Unsupported exact clauses: held PRD concern request delta V13",
        "",
        "All 121 unsupported authored clauses per side remain unsupported across 30 "
        "draft unsent groups. Every V12 row, group, contact, locator and original "
        "request field is retained.",
        "",
        "| Per-side measure | Count |",
        "| --- | ---: |",
        f"| Unsupported authored clauses | {counts['unsupported_exact_clauses']} |",
        "| Possible unaccepted no-event reviews | "
        f"{counts['possible_nonoccurrence_review_candidates']} |",
        "| New selected PRD authored leads | 3 |",
        "| Newly source-affected clauses | 3 |",
        "| Newly route-targeted clauses | 0 |",
        "| Cumulative source-affected clauses | "
        f"{counts['v13_cumulative_reviewed_source_affected_unsupported_clauses']} |",
        "| Cumulative route-targeted unsupported clauses | "
        f"{counts['v13_cumulative_targeted_unsupported_clauses']} |",
        "| V13 changed draft next actions | 3 |",
        "| Changed groups, contacts, locators or original requests | 0 |",
        "",
        "One selected fictional concern intake supplies 8 Clean and 13 Messy native "
        "originals to each of three authored communication routes. The claimant is "
        "unverified; drafts are held; Messy retains denied dispatch, false completion, "
        "correction and an OPEN exception. No accepted delivery or acknowledgment follows.",
        "",
        "| Request group | New V13 reviewed lead | V13 draft next action |",
        "| --- | --- | --- |",
    ]
    lines.extend(
        f"| {group['request_group_id']} | {SOURCE} | {group['v13_next_action']} |"
        for group in groups
    )
    lines += [
        "",
        "All requests remain `DRAFT_NOT_SENT`; all 409 A/B P1 tasks remain "
        "`NOT_STARTED`/`NOT_RUN`. No message, accepted no-event or N/A decision, "
        "audit task credit, fresh pair, Key, grade or Atlas write was issued.",
        "",
    ]
    return "\n".join(lines)
