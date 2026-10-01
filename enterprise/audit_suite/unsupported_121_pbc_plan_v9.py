"""Bounded SEC001 CC5.2/CC6.7 source leads for the frozen unsupported PBC plan."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from . import company_sec001_component_lifecycle_2027 as component
from . import documentary_283_route_reconciliation_v11 as routes_v11
from . import unsupported_121_pbc_plan as pinned
from . import unsupported_121_pbc_plan_v8 as prior
from .documentary_283_route_reconciliation_v6 import _p1_inventory, _pinned_db

SCHEMA = "SH_UNSUPPORTED_121_PAIRED_SOURCE_REQUEST_PLAN_V9"
BASE = "enterprise/generated/audit-suite"
V8_PLAN = "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V8_2026-09-30.json"
V8_REVIEW = f"{BASE}/unsupported-121-pbc-plan-v8-2026-09-30/independent-review-main-v1/REVIEW.json"
V11_LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V11_2026-09-30.json"
V11_REVIEW = (
    f"{BASE}/documentary-283-route-reconciliation-v11-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
COMP_ROOT = f"{BASE}/company-sec001-component-lifecycle-2027-09-30"
COMP_RUN = f"{COMP_ROOT}/main-run-v1"
COMP_REVIEW = f"{COMP_ROOT}/independent-review-main-v1/REVIEW.json"
COMP_MANIFEST = f"{COMP_RUN}/RUN-MANIFEST.json"
COMP_RECEIPT = f"{COMP_RUN}/SOURCE_RECEIPT.json"
COMP_DB = f"{COMP_RUN}/company.sqlite3"
TRANSFER_RECEIPT = (
    f"{BASE}/company-sec001-selected-transfer-2027-09-30/main-run-v1/SOURCE_RECEIPT.json"
)
PINS = {
    V8_PLAN: "02ecac983e06c8757f14ae252f4268b4d552bd21be7334707e0bd46fc7feb59a",
    V8_REVIEW: "bbbe153ef0110ddca325bd88830e521b14d8243aa09c1b65963946c02da68d65",
    V11_LEDGER: "41facc0f48c2f0fc4b9144366bb239131e54c1693fde2bcbfa9ded7360792299",
    V11_REVIEW: "5db6205b1afcbd578562345a7ff0af6a212b8cbf1c39139cb71a22590fd394a2",
    COMP_REVIEW: "c780366186a166071040c74f99c72b728b260daa9d4de5d84c8da682ddc59758",
    COMP_MANIFEST: "95a73ceb8c360acec49dbad3bcaded86396284be77f53e74cd2272fb612e1547",
    COMP_RECEIPT: "36374e1fa5ba18fd5d42ac6229da270b90bbed0aeeba9b39f3f2191d09aa36eb",
    COMP_DB: "f8aba6420ce8fbdd5582e95f98aefd3a056b088b2e47d172e5fb6b2e69bfb41f",
    TRANSFER_RECEIPT: "73fa3ff1cb40f9e0e8196cd01bf18048c408427e0d10ade9003fd60d9c984d28",
}
P1_FREEZE = prior.P1_FREEZE
GROUP = "SH-SEC-001"
CC52_TASK = "TASK-SH-SEC-001-corporate-CHECK-SOC2:CC5.2"
CC67_TASK = "TASK-SH-SEC-001-corporate-CHECK-SOC2:CC6.7"
COMP_SOURCE = "SEC001_SELECTED_COMPONENT_LIFECYCLE_V1"
TRANSFER_SOURCE = routes_v11.SOURCE
CC52_LIMIT = (
    "One future fictional non-deployed internal component and unnamed outsourced candidate; "
    "no designed third-party landscape, named vendor, contract, entitlement or deployed "
    "component population. Clean blocks unsupported use; Messy omitted the candidate, "
    "falsely closed, corrected and retains an open historical exception. The evidence "
    "request remains unreceived. Existing SEC003 four-asset lead remains limited; neither "
    "fixture satisfies the authored CC5.2 technology-lifecycle gate."
)
CC67_LIMIT = routes_v11.LIMIT
NEXT_ACTION_ADDENDUM = (
    "Inspect the selected fictional 10-Clean/15-Messy SEC001 component-lifecycle "
    "originals only as a CC5.2 lead alongside SEC003. Retain the unnamed candidate, "
    "blocked use, Messy omitted inventory, false close, unreceived evidence request and "
    "open exception. Inspect the reviewed 10-Clean/16-Messy synthetic non-PHI transfer "
    "originals only as a CC6.7 lead, retaining the blocked wrong endpoint, false close "
    "correction and open exception. Request independently scoped deployed "
    "component/control/owner/lifecycle and supplier populations, if any, plus original "
    "vendor contracts or entitlements; request the actual transfer population, approved "
    "purposes and recipients, channel/endpoint configuration, receipts and post-receipt "
    "handling. The third-party landscape is undesigned, and neither pending fictional "
    "appointments nor simulated controls establish supplier selection, deployment, "
    "transmission, approval or either authored clause."
)
REF_FIELDS = routes_v11.IDENTITY


class V9SourceRequestError(prior.V8SourceRequestError):
    """A reviewed source, route, request prefix, or no-credit boundary changed."""


def _selected_component_refs(receipt: dict, old: dict) -> dict[str, list[dict]]:
    """Reconcile exact CC5.2 native originals and preexisting SEC003 route lead."""
    if (
        receipt.get("schema") != component.SCHEMA
        or receipt.get("task_id") != CC52_TASK
        or receipt.get("selected_authored_clause") != component.CLAUSE
        or receipt.get("branch_ids") != component.BRANCHES
        or receipt.get("branch_counts") != {"CLEAN": 10, "MESSY": 15}
        or receipt.get("native_count") != 25
        or receipt.get("selected_component_count") != 2
        or receipt.get("selected_component_ids") != [component.CORE, component.OUTSOURCED]
        or receipt.get("actor_authority")
        != "CANON_LISTED_FICTIONAL_APPOINTMENTS_PENDING_ACCEPTANCE"
        or receipt.get("messy_false_close_corrected") is not True
        or receipt.get("messy_historical_exception_open") is not True
        or any(
            receipt.get(key) is not False
            for key in (
                "actual_supplier_selected_or_contracted",
                "actual_deployed_component",
                "approved_enterprise_architecture",
                "independent_approval",
                "population_complete",
                "source_complete",
                "audit_task_credit",
                "active_P1_mutated",
            )
        )
    ):
        raise V9SourceRequestError("CC5.2 selected component authority or scope differs")
    refs = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        route = receipt.get("route_disposition", {}).get(side, {})
        prior_row = next(
            row for row in old["rows"] if row["side"] == side and row["task_id"] == CC52_TASK
        )
        if (
            route.get("task_id") != CC52_TASK
            or route.get("authored_test_clause") != prior_row["authored_test_clause"]
            or route.get("screen_row_sha256") != prior_row["screen_row_sha256"]
            or route.get("classification") != "UNSUPPORTED_EXACT_CLAUSE"
            or route.get("existing_targeted_integrated_source_ids")
            != ["SEC003_SELECTED_VULNERABILITY_V1"]
            or route.get("current_status") != "NOT_STARTED"
            or route.get("current_conclusion") != "NOT_RUN"
            or route.get("audit_task_credit") is not False
        ):
            raise V9SourceRequestError("CC5.2 reviewed source/SEC003 route join differs")
        selected = [
            item
            for item in receipt["native_originals"]
            if item["branch"] == component.BRANCHES[scenario]
        ]
        if (
            len(selected) != len(component.PLAN[scenario])
            or [(item["system"], item["record"]) for item in selected]
            != [(system, record) for system, record, _, _ in component.PLAN[scenario]]
            or any(item["version"] != 1 for item in selected)
        ):
            raise V9SourceRequestError("CC5.2 native component roster differs")
        refs[side] = [{key: item[key] for key in REF_FIELDS} for item in selected]
    return refs


def _extend(
    old: dict, ledger: dict, component_receipt: dict, transfer_receipt: dict, freeze: dict
) -> dict:
    """Preserve all V8 fields; add only two selected leads and one draft action."""
    if (
        old.get("schema") != prior.SCHEMA
        or old.get("p1_freeze") != freeze
        or ledger.get("p1_freeze") != freeze
        or len(old.get("rows", [])) != 242
        or len(old.get("request_groups", [])) != 30
        or len(old.get("group_delta", [])) != 30
        or old.get("audit_task_credit") is not False
        or old.get("active_pair_mutated") is not False
        or old.get("external_messages_sent") != 0
        or old.get("accepted_na_determinations") != 0
        or ledger.get("audit_task_credit") is not False
        or ledger.get("active_pair_mutated") is not False
        or len(ledger.get("rows", [])) != 566
        or any(
            ledger["active_p1_tasks"][side]
            != {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"}
            for side in "AB"
        )
    ):
        raise V9SourceRequestError("Frozen V8 request or V11 route denominator differs")
    component_refs = _selected_component_refs(component_receipt, old)
    transfer_refs = routes_v11._selected_refs(transfer_receipt)
    routes = {
        (row["side"], row["task_id"]): row
        for row in ledger["rows"]
        if row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
    }
    previous = {(row["side"], row["task_id"]): row for row in old["rows"]}
    if len(routes) != 242 or len(previous) != 242 or set(routes) != set(previous):
        raise V9SourceRequestError("Exact V8 unsupported task identity differs")
    group_sources = {group["request_group_id"]: set() for group in old["request_groups"]}
    group_limits = {group["request_group_id"]: {} for group in old["request_groups"]}
    group_refs = {group["request_group_id"]: {"A": {}, "B": {}} for group in old["request_groups"]}
    rows = []
    for prior_row in old["rows"]:
        row = dict(prior_row)
        side, task = row["side"], row["task_id"]
        route = routes[side, task]
        group = row["request_group_id"]
        selected = task in (CC52_TASK, CC67_TASK)
        source_ids = (
            [COMP_SOURCE] if task == CC52_TASK else [TRANSFER_SOURCE] if task == CC67_TASK else []
        )
        expected_targeted = list(row["v8_targeted_source_ids"])
        if task == CC67_TASK:
            expected_targeted.append(TRANSFER_SOURCE)
        if (
            route["control_id"] != row["control_id"]
            or route["authored_test_clause"] != row["authored_test_clause"]
            or route["remaining_test_gate"] != row["remaining_test_gate"]
            or route["screen_row_sha256"] != row["screen_row_sha256"]
            or route["requirement_ids"] != row["requirement_ids"]
            or route["current_status"] != row["current_task_status"]
            or route["current_conclusion"] != row["current_task_conclusion"]
            or route["classification"] != "UNSUPPORTED_EXACT_CLAUSE"
            or route["targeted_integrated_source_ids"] != expected_targeted
            or route["v11_reviewed_source_ids"] != ([TRANSFER_SOURCE] if task == CC67_TASK else [])
            or route["audit_task_credit"] is not False
            or row["pbc_request_status"] != "DRAFT_NOT_SENT"
            or row["task_credit"] is not False
            or row["accepted_nonoccurrence_status"] == "ACCEPTED"
            or (selected and (group != GROUP or row["control_id"] != "SH-SEC-001"))
        ):
            raise V9SourceRequestError(f"Unsupported V9 clause/route drift: {(side, task)}")
        if task == CC52_TASK and row["v8_targeted_source_ids"] != [
            "SEC003_SELECTED_VULNERABILITY_V1"
        ]:
            raise V9SourceRequestError("Existing CC5.2 SEC003 lead differs")
        if task == CC67_TASK and (
            row["v8_targeted_source_ids"]
            or route["remaining_test_gate"] != routes_v11.CLAUSE
            or route["v11_source_limits"] != {TRANSFER_SOURCE: CC67_LIMIT}
            or route["v11_source_record_refs"] != {TRANSFER_SOURCE: transfer_refs[side]}
        ):
            raise V9SourceRequestError("Selected CC6.7 V11 route/native lead differs")
        source_limits = (
            {COMP_SOURCE: CC52_LIMIT}
            if task == CC52_TASK
            else {TRANSFER_SOURCE: CC67_LIMIT}
            if task == CC67_TASK
            else {}
        )
        source_refs = (
            {COMP_SOURCE: component_refs[side]}
            if task == CC52_TASK
            else {TRANSFER_SOURCE: transfer_refs[side]}
            if task == CC67_TASK
            else {}
        )
        row["v9_reviewed_source_ids"] = source_ids
        row["v9_source_limits"] = source_limits
        row["v9_source_record_refs"] = source_refs
        row["v9_targeted_source_ids"] = expected_targeted
        row["v9_next_action"] = (
            row["v8_next_action"] + " " + NEXT_ACTION_ADDENDUM
            if group == GROUP
            else row["v8_next_action"]
        )
        row["v9_next_action_changed_from_v8"] = group == GROUP
        group_sources[group].update(source_ids)
        group_limits[group].update(source_limits)
        if source_refs:
            group_refs[group][side][task] = source_refs
        rows.append(row)
    if {group for group, sources in group_sources.items() if sources} != {GROUP}:
        raise V9SourceRequestError("Exact SEC001 source-affected group differs")
    groups, deltas = [], []
    for previous_group, previous_delta in zip(
        old["request_groups"], old["group_delta"], strict=True
    ):
        group = dict(previous_group)
        delta = dict(previous_delta)
        name = group["request_group_id"]
        leads = sorted(group_sources[name])
        if (
            delta["request_group_id"] != name
            or (name == GROUP and (group["control_id"], group["routes_per_side"]) != (GROUP, 8))
            or len(group_refs[name]["A"]) != (2 if name == GROUP else 0)
            or len(group_refs[name]["B"]) != (2 if name == GROUP else 0)
            or leads != (sorted((COMP_SOURCE, TRANSFER_SOURCE)) if name == GROUP else [])
        ):
            raise V9SourceRequestError("Historical SEC001 group or source join differs")
        next_action = (
            group["v8_next_action"] + " " + NEXT_ACTION_ADDENDUM
            if name == GROUP
            else group["v8_next_action"]
        )
        group["v9_reviewed_source_ids"] = leads
        group["v9_source_limits"] = group_limits[name]
        group["v9_source_record_refs_by_side"] = group_refs[name]
        group["v9_next_action"] = next_action
        group["v9_next_action_changed_from_v8"] = name == GROUP
        delta.update(
            {
                "v9_reviewed_source_ids": leads,
                "v9_source_limits": group_limits[name],
                "v9_source_record_refs_by_side": group_refs[name],
                "v8_next_action_before_v9": previous_group["v8_next_action"],
                "v9_next_action": next_action,
                "v9_next_action_changed_from_v8": name == GROUP,
            }
        )
        groups.append(group)
        deltas.append(delta)
    counts = {}
    for side in "AB":
        selected = [row for row in rows if row["side"] == side]
        affected = sum(
            bool(
                row["v5_reviewed_source_ids"]
                or row["v6_reviewed_source_ids"]
                or row["v7_reviewed_source_ids"]
                or row["v8_reviewed_source_ids"]
                or row["v9_reviewed_source_ids"]
            )
            for row in selected
        )
        targeted = sum(bool(row["v9_targeted_source_ids"]) for row in selected)
        if (
            len(selected) != len({row["task_id"] for row in selected})
            or len(selected) != 121
            or len({row["control_id"] for row in selected}) != 28
            or sum(row["possible_nonoccurrence_review_candidate"] for row in selected) != 53
            or sum(bool(row["v9_reviewed_source_ids"]) for row in selected) != 2
            or affected != 22
            or targeted != 34
            or any(
                row["accepted_nonoccurrence_status"] != "NOT_ESTABLISHED"
                for row in selected
                if row["possible_nonoccurrence_review_candidate"]
            )
            or Counter(row["request_group_id"] for row in selected if row["control_id"] == GROUP)
            != {GROUP: 8}
        ):
            raise V9SourceRequestError("V9 unsupported/SEC001/no-event denominator differs")
        counts[side] = {
            **old["counts"][side],
            "v9_new_reviewed_source_leads": 2,
            "v9_newly_source_affected_unsupported_clauses": 1,
            "v9_selected_source_affected_request_groups": 1,
            "v9_next_action_changes_from_v8": 1,
            "v9_cumulative_reviewed_source_affected_unsupported_clauses": 22,
            "v9_cumulative_targeted_unsupported_clauses": 34,
            "v9_cumulative_changed_request_groups": 10,
            "v9_grouping_or_contact_changes": 0,
        }
    if (
        counts["A"] != counts["B"]
        or len(groups) != 30
        or len({group["request_group_id"] for group in groups}) != 30
        or sum(group["v9_next_action_changed_from_v8"] for group in groups) != 1
        or sum(delta["v9_next_action_changed_from_v8"] for delta in deltas) != 1
    ):
        raise V9SourceRequestError("Paired SEC001 draft request delta differs")
    return {
        "schema": SCHEMA,
        "as_of": "2026-09-30",
        "source_pins": PINS,
        "p1_freeze": freeze,
        "active_p1_tasks": ledger["active_p1_tasks"],
        "reviewed_route_roster": ledger["reviewed_source_roster"],
        "counts": counts,
        "rows": rows,
        "request_groups": groups,
        "group_delta": deltas,
        "candidate_owner_source_queues": old["candidate_owner_source_queues"],
        "nonoccurrence_acceptance_protocol": old["nonoccurrence_acceptance_protocol"],
        "limits": [
            "All V8 and earlier row, group, contact, source-locator and original-request "
            "fields remain intact; only SH-SEC-001 gains a V9 draft next action.",
            "CC5.2 retains its limited SEC003 lead and gains one fictional component-lifecycle "
            "lead; CC6.7 gains the reviewed fictional transfer lead. Both remain unsupported.",
            "Only CC6.7 is newly source-affected and newly route-targeted; no other clause "
            "or group gains a V9 lead and no generic route is promoted.",
            "The third-party landscape is undesigned. No named supplier, contract, deployed "
            "component or channel, actual transfer, approved population or independent "
            "assurance follows from these fixtures.",
            "All 121 clauses and 53 possible no-event reviews per side remain unsupported "
            "or unaccepted; requests remain unsent and no N/A or task credit is awarded.",
        ],
        "external_messages_sent": 0,
        "fresh_pair_created": False,
        "audit_task_credit": False,
        "accepted_na_determinations": 0,
        "active_pair_mutated": False,
    }


def build(repository: Path, private_repository: Path) -> dict:
    """Reperform V8, route V11, and the selected component native source."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    freeze = _p1_inventory(private)
    if freeze != P1_FREEZE:
        raise V9SourceRequestError("Frozen P1 inventory differs")
    old_pinned = pinned._pinned(repository / V8_PLAN, PINS[V8_PLAN])
    old_review = pinned._pinned(private / V8_REVIEW, PINS[V8_REVIEW], private=True)
    ledger_pinned = pinned._pinned(repository / V11_LEDGER, PINS[V11_LEDGER])
    route_review = pinned._pinned(private / V11_REVIEW, PINS[V11_REVIEW], private=True)
    comp_review = pinned._pinned(private / COMP_REVIEW, PINS[COMP_REVIEW], private=True)
    comp_manifest = pinned._pinned(private / COMP_MANIFEST, PINS[COMP_MANIFEST], private=True)
    comp_pinned = pinned._pinned(private / COMP_RECEIPT, PINS[COMP_RECEIPT], private=True)
    transfer_pinned = pinned._pinned(
        private / TRANSFER_RECEIPT, PINS[TRANSFER_RECEIPT], private=True
    )
    _pinned_db(private, {"path": COMP_DB, "sha256": PINS[COMP_DB]})
    if (
        old_review.get("verdict")
        != "PASS_READ_ONLY_UNSUPPORTED_CLAUSE_REQUEST_DELTA_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or old_review.get("main_tracked_sha256", {}).get(V8_PLAN) != PINS[V8_PLAN]
        or old_review.get("p1_freeze") != freeze
        or old_review.get("audit_task_credit") is not False
        or route_review.get("verdict")
        != "PASS_SELECTED_SEC001_CC67_ROUTE_V11_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or route_review.get("main_head") != "26943729bfa74326707b5eb380343b1547c668e7"
        or route_review.get("main_output_sha256", {}).get("LEDGER.json") != PINS[V11_LEDGER]
        or route_review.get("p1_freeze") != freeze
        or route_review.get("audit_task_credit") is not False
        or comp_review.get("verdict")
        != "PASS_SELECTED_SYNTHETIC_SEC001_COMPONENT_LIFECYCLE_SOURCE_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or comp_review.get("integration_commit") != "17cb19c9e526dfd42aeb0968dbeb1f51b8ae8040"
        or comp_review.get("main_run_sha256")
        != {
            "RUN-MANIFEST.json": PINS[COMP_MANIFEST],
            "SOURCE_RECEIPT.json": PINS[COMP_RECEIPT],
            "company.sqlite3": PINS[COMP_DB],
        }
        or comp_review.get("p1_freeze") != freeze
        or comp_review.get("task_id") != CC52_TASK
        or comp_review.get("authored_clause") != component.CLAUSE
        or comp_review.get("source_complete") is not False
        or comp_review.get("audit_task_credit") is not False
        or comp_manifest.get("source_receipt_sha256") != PINS[COMP_RECEIPT]
        or comp_manifest.get("native_db_sha256") != PINS[COMP_DB]
        or comp_manifest.get("native_count") != 25
    ):
        raise V9SourceRequestError("Independent V8/V11/CC5.2 review join differs")
    old = prior.build(repository, private)
    ledger = routes_v11.build(repository, private)
    comp_receipt = component.verify(
        private / COMP_RUN, repository=repository, private_repository=private
    )
    if (
        old != old_pinned
        or ledger != ledger_pinned
        or comp_receipt != comp_pinned
        or transfer_pinned.get("task_id") != CC67_TASK
        or transfer_pinned.get("source_complete") is not False
        or transfer_pinned.get("audit_task_credit") is not False
    ):
        raise V9SourceRequestError("Reviewed request, route or native source fails replay")
    result = _extend(old, ledger, comp_receipt, transfer_pinned, freeze)
    if _p1_inventory(private) != freeze:
        raise V9SourceRequestError("Frozen P1 changed during read-only PBC build")
    return result


def markdown(result: dict) -> str:
    """Render the one-group SEC001 draft delta without task or source credit."""
    counts = result["counts"]["A"]
    group = next(item for item in result["request_groups"] if item["request_group_id"] == GROUP)
    lines = [
        "# Unsupported exact clauses: selected SEC001 request delta V9",
        "",
        "All 121 unsupported authored clauses per side remain unsupported across 30 "
        "draft unsent request groups. The exact V8 rows, groups, contacts and original "
        "request wording are retained.",
        "",
        "| Per-side measure | Count |",
        "| --- | ---: |",
        f"| Unsupported authored clauses | {counts['unsupported_exact_clauses']} |",
        "| Possible unaccepted no-event reviews | "
        f"{counts['possible_nonoccurrence_review_candidates']} |",
        "| New selected SEC001 source leads | 2 |",
        "| Newly source-affected clauses | 1 (CC6.7; CC5.2 already had SEC003) |",
        "| Cumulative source-affected clauses | "
        f"{counts['v9_cumulative_reviewed_source_affected_unsupported_clauses']} |",
        "| Cumulative targeted unsupported clauses | "
        f"{counts['v9_cumulative_targeted_unsupported_clauses']} |",
        "| V9 changed draft next actions | 1 |",
        "| Changed groups, contacts, locators or original requests | 0 |",
        "",
        "The reviewed component-lifecycle fixture is a bounded CC5.2 lead alongside "
        "the existing SEC003 lead. Its unnamed outsourced candidate has no vendor, "
        "contract or deployment, and the third-party landscape remains undesigned. "
        "The reviewed synthetic non-PHI transfer fixture is a bounded CC6.7 lead, "
        "without actual transmission or deployed channel/endpoint. Both authored gates "
        "remain open; Messy false-close histories retain open exceptions.",
        "",
        "| Request group | New V9 reviewed leads | V9 draft next action |",
        "| --- | --- | --- |",
        f"| {GROUP} | {', '.join(group['v9_reviewed_source_ids'])} | {group['v9_next_action']} |",
        "",
        "All requests remain `DRAFT_NOT_SENT`; all 409 A/B P1 tasks remain "
        "`NOT_STARTED`/`NOT_RUN`. No message, accepted no-event or N/A decision, "
        "audit task credit, fresh pair, Key, grade or Atlas write was issued.",
        "",
    ]
    return "\n".join(lines)
