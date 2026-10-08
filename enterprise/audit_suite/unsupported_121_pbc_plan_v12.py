"""Bounded ENG005 operating-source discovery lead for the frozen unsupported PBC plan."""

from __future__ import annotations

from pathlib import Path

from . import company_eng005_operating_2027 as source
from . import documentary_283_route_reconciliation_v14 as route
from . import unsupported_121_pbc_plan as pinned
from . import unsupported_121_pbc_plan_v11 as prior
from .documentary_283_route_reconciliation_v6 import _p1_inventory, _pinned_db

SCHEMA = "SH_UNSUPPORTED_121_PAIRED_SOURCE_REQUEST_PLAN_V12"
BASE = "enterprise/generated/audit-suite"
V11_PLAN = "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V11_2026-09-30.json"
V11_REVIEW = (
    f"{BASE}/unsupported-121-pbc-plan-v11-2026-09-30/independent-review-main-v1/REVIEW.json"
)
ROUTE_LEDGER = f"{BASE}/documentary-283-route-reconciliation-v14-2026-09-30/main-run-v1/LEDGER.json"
ROUTE_REVIEW = (
    f"{BASE}/documentary-283-route-reconciliation-v14-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
SOURCE_RUN = f"{BASE}/company-eng005-operating-2026-09-30/main-run-v1"
SOURCE_REVIEW = f"{BASE}/company-eng005-operating-2026-09-30/independent-review-main-v1/REVIEW.json"
SOURCE_MANIFEST = f"{SOURCE_RUN}/MANIFEST.json"
SOURCE_RECEIPT = f"{SOURCE_RUN}/RECEIPT.json"
SOURCE_DB = f"{SOURCE_RUN}/company.sqlite3"
PINS = {
    V11_PLAN: "880403ea27f6047861a7214ceb6808a04dafff8ec9b8c4772a1402d0590dd3fb",
    V11_REVIEW: "0d3d2e4eb0a846a64c3f48c5b2c74897deb2d929bbc65f142db271ced60db151",
    ROUTE_LEDGER: "e43e644eecd53a2111c247d16466627ad8d4d63b14012b78fead47c48a23877a",
    ROUTE_REVIEW: "4cebb2939e5dacf308757640f3643c0f3de4ebd78fbaf77e385c1f883ee8ceee",
    SOURCE_REVIEW: "03453687ff227cb6ef4376e6b1b313638e5a5841fc78f43cd09551fd62e44075",
    SOURCE_MANIFEST: "505be4531461c0d73e0466fb39540b5757512bf13b9d4ed8f44c13d86e90fc75",
    SOURCE_RECEIPT: "0d9209de464d0f4e9186eb41824ac66beba1b7f7e1e735364ba64cded20f02bd",
    SOURCE_DB: "8696b55b03ec1df8597556d0b949f82a34c0e0cabc9d8130fae078e6b2812ee3",
}
P1_FREEZE = prior.P1_FREEZE
GROUP = route.CONTROL
TASK = route.AUTHORED
SOURCE = route.SOURCE
SOURCE_LIMIT = route.LIMIT
REF_FIELDS = route.IDENTITY
NEXT_ACTION_ADDENDUM = (
    "Inspect the exact reviewed fictional ENG005 selected originals (12 Clean/22 Messy) "
    "as a CC8.1 discovery lead for one ordinary Reno and one emergency Boise request "
    "per branch. Preserve Clean's emergency hold for unevidenced corporate delegation "
    "and Messy's invalid ordinary application, unauthorized emergency bypass, rollbacks "
    "and two OPEN historical exceptions. Obtain adopted corporate change policy and "
    "emergency authority, the complete scoped-period code/infrastructure/data change "
    "population, requirements, security tests, independent approvals, deployment "
    "verification, rollback records and independent exception review before assessing "
    "the authored clause. The selected simulation proves no real deployment, actual PHI, "
    "full population, operating assurance or audit task credit."
)


class V12SourceRequestError(prior.V11SourceRequestError):
    """Reviewed ENG005 source, route, PBC prefix or no-credit gate changed."""


def _selected_refs(receipt: dict, ledger: dict, old: dict) -> dict[str, list[dict]]:
    """Require native original tuples to match the reviewed authored route exactly."""
    if (
        receipt.get("schema") != source.SCHEMA
        or receipt.get("branches") != source.BRANCHES
        or receipt.get("selected_service_id") != "SVC-compute"
        or receipt.get("selected_population") != ["CHG-RNO-MARKER-2027-01", "CHG-BOI-GATE-2027-02"]
        or receipt.get("native_version_counts") != {"CLEAN": 12, "MESSY": 22}
        or receipt.get("open_exception_counts") != {"CLEAN": 0, "MESSY": 2}
        or receipt.get("open_exception_ids")
        != {"CLEAN": [], "MESSY": ["EXC-ENG005-ORD-01", "EXC-ENG005-EMG-01"]}
        or receipt.get("corporate_emergency_authority_status") != "NOT_EVIDENCED_OPEN"
        or receipt.get("historical_exercise_is_operating_source") is not False
        or receipt.get("historical_prospective_receipt_sha256") != source.HISTORICAL_SHA256
        or receipt.get("external_packets_or_writes") != 0
        or any(
            receipt.get(key) is not False
            for key in (
                "real_deployment",
                "actual_phi",
                "enterprise_policy_approved",
                "source_complete",
                "authored_eng005_clause_satisfied",
                "full_period_or_enterprise_change_population_complete",
                "audit_task_credit",
            )
        )
        or ledger.get("schema") != route.SCHEMA
        or ledger.get("p1_freeze") != P1_FREEZE
        or ledger.get("audit_task_credit") is not False
        or ledger.get("active_pair_mutated") is not False
        or ledger.get("active_p1_tasks") != old["active_p1_tasks"]
    ):
        raise V12SourceRequestError("ENG005 source or reviewed route scope differs")
    refs = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        records = receipt.get("records", {}).get(scenario, [])
        selected = [{key: row[key] for key in REF_FIELDS} for row in records]
        route_row = next(
            row for row in ledger["rows"] if row["side"] == side and row["task_id"] == TASK
        )
        previous = next(
            row for row in old["rows"] if row["side"] == side and row["task_id"] == TASK
        )
        if (
            len(records) != (12 if side == "A" else 22)
            or any(
                row["company"] != source.COMPANY
                or row["branch"] != source.BRANCHES[scenario]
                or row["version"] != 1
                or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                for row in records
            )
            or route_row.get("control_id") != GROUP
            or route_row.get("classification") != "UNSUPPORTED_EXACT_CLAUSE"
            or route_row.get("test_gate_basis") != "AUTHORED_TASK_CLAUSE"
            or route_row.get("authored_test_clause") != route.CLAUSE
            or route_row.get("remaining_test_gate") != route.CLAUSE
            or route_row.get("v14_reviewed_source_ids") != [SOURCE]
            or route_row.get("v14_source_limits") != {SOURCE: SOURCE_LIMIT}
            or route_row.get("v14_source_record_refs") != {SOURCE: selected}
            or route_row.get("targeted_integrated_source_ids")
            != [*previous["v11_targeted_source_ids"], SOURCE]
            or route_row.get("candidate_or_design_source_ids") != []
            or route_row.get("current_status") != "NOT_STARTED"
            or route_row.get("current_conclusion") != "NOT_RUN"
            or route_row.get("audit_task_credit") is not False
            or previous.get("authored_test_clause") != route.CLAUSE
            or previous.get("remaining_test_gate") != route.CLAUSE
            or previous.get("request_group_id") != GROUP
            or previous.get("control_id") != GROUP
            or previous.get("v11_reviewed_source_ids") != []
            or previous.get("v11_targeted_source_ids") != ["ENG005_LOCAL_V1"]
        ):
            raise V12SourceRequestError("Exact ENG005 authored route or native roster differs")
        refs[side] = selected
    return refs


def _extend(old: dict, ledger: dict, receipt: dict, freeze: dict) -> dict:
    """Keep every V11 field and change only one ENG005 draft next action."""
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
        raise V12SourceRequestError("Reviewed V11 PBC or P1 denominator differs")
    refs = _selected_refs(receipt, ledger, old)
    route_rows = {(row["side"], row["task_id"]): row for row in ledger["rows"]}
    rows = []
    for previous in old["rows"]:
        row = dict(previous)
        side, task, group = row["side"], row["task_id"], row["request_group_id"]
        selected = task == TASK
        route_row = route_rows[(side, task)]
        if (
            row["pbc_request_status"] != "DRAFT_NOT_SENT"
            or row["current_task_status"] != "NOT_STARTED"
            or row["current_task_conclusion"] != "NOT_RUN"
            or row["task_credit"] is not False
            or row["accepted_nonoccurrence_status"] == "ACCEPTED"
            or route_row["classification"] != "UNSUPPORTED_EXACT_CLAUSE"
            or (selected and group != GROUP)
        ):
            raise V12SourceRequestError("V11 task/request or route boundary differs")
        row["v12_reviewed_source_ids"] = [SOURCE] if selected else []
        row["v12_source_limits"] = {SOURCE: SOURCE_LIMIT} if selected else {}
        row["v12_source_record_refs"] = {SOURCE: refs[side]} if selected else {}
        row["v12_targeted_source_ids"] = list(route_row["targeted_integrated_source_ids"])
        if not selected and row["v12_targeted_source_ids"] != row["v11_targeted_source_ids"]:
            raise V12SourceRequestError("Unselected unsupported route target changed")
        row["v12_next_action"] = (
            row["v11_next_action"] + " " + NEXT_ACTION_ADDENDUM
            if selected
            else row["v11_next_action"]
        )
        row["v12_next_action_changed_from_v11"] = selected
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
            or group["task_credit"] is not False
        ):
            raise V12SourceRequestError("V11 ENG005 group or unsent boundary differs")
        leads = [SOURCE] if selected else []
        limits = {SOURCE: SOURCE_LIMIT} if selected else {}
        source_refs = {side: {TASK: {SOURCE: refs[side]}} if selected else {} for side in "AB"}
        action = (
            group["v11_next_action"] + " " + NEXT_ACTION_ADDENDUM
            if selected
            else group["v11_next_action"]
        )
        group.update(
            {
                "v12_reviewed_source_ids": leads,
                "v12_source_limits": limits,
                "v12_source_record_refs_by_side": source_refs,
                "v12_next_action": action,
                "v12_next_action_changed_from_v11": selected,
            }
        )
        delta.update(
            {
                "v12_reviewed_source_ids": leads,
                "v12_source_limits": limits,
                "v12_source_record_refs_by_side": source_refs,
                "v11_next_action_before_v12": previous_group["v11_next_action"],
                "v12_next_action": action,
                "v12_next_action_changed_from_v11": selected,
            }
        )
        groups.append(group)
        deltas.append(delta)
    counts = {}
    for side in "AB":
        selected = [row for row in rows if row["side"] == side]
        affected = sum(
            bool(any(row[f"v{version}_reviewed_source_ids"] for version in range(5, 13)))
            for row in selected
        )
        targeted = sum(bool(row["v12_targeted_source_ids"]) for row in selected)
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
            or sum(bool(row["v12_reviewed_source_ids"]) for row in selected) != 1
            or previous_counts["v11_cumulative_reviewed_source_affected_unsupported_clauses"] != 23
            or previous_counts["v11_cumulative_targeted_unsupported_clauses"] != 35
            or previous_counts["v11_cumulative_changed_request_groups"] != 11
            or affected != 24
            or targeted != 35
        ):
            raise V12SourceRequestError("V12 unsupported/ENG005/no-event denominator differs")
        counts[side] = {
            **previous_counts,
            "v12_new_reviewed_source_leads": 1,
            "v12_newly_source_affected_unsupported_clauses": 1,
            "v12_newly_route_targeted_unsupported_clauses": 0,
            "v12_selected_source_affected_request_groups": 1,
            "v12_next_action_changes_from_v11": 1,
            "v12_cumulative_reviewed_source_affected_unsupported_clauses": 24,
            "v12_cumulative_targeted_unsupported_clauses": 35,
            "v12_cumulative_changed_request_groups": 12,
            "v12_grouping_or_contact_changes": 0,
        }
    if (
        counts["A"] != counts["B"]
        or len(groups) != 30
        or len({group["request_group_id"] for group in groups}) != 30
        or sum(group["v12_next_action_changed_from_v11"] for group in groups) != 1
        or sum(group["v12_next_action_changed_from_v11"] for group in deltas) != 1
    ):
        raise V12SourceRequestError("Paired ENG005 draft group delta differs")
    return {
        "schema": SCHEMA,
        "as_of": "2026-09-30",
        "source_pins": {**old["source_pins"], **PINS},
        "p1_freeze": freeze,
        "active_p1_tasks": old["active_p1_tasks"],
        "reviewed_route_roster": old["reviewed_route_roster"],
        "v13_route_ledger_sha256": old["v13_route_ledger_sha256"],
        "v14_route_ledger_sha256": PINS[ROUTE_LEDGER],
        "counts": counts,
        "rows": rows,
        "request_groups": groups,
        "group_delta": deltas,
        "candidate_owner_source_queues": old["candidate_owner_source_queues"],
        "nonoccurrence_acceptance_protocol": old["nonoccurrence_acceptance_protocol"],
        "limits": [
            *old["limits"],
            "All V11 row, group, contact, locator and original-request fields remain exact; "
            "only SH-ENG-005 gains a V12 draft next action and selected native lead.",
            "The authored CC8.1 clause remains UNSUPPORTED_EXACT_CLAUSE and unrun. "
            "One selected operating source is not the complete change population.",
            "Corporate emergency authority remains NOT_EVIDENCED_OPEN. Clean holds, "
            "Messy bypasses and retains two OPEN historical exceptions.",
            "No real deployment, actual PHI, adopted enterprise policy, full-period operating "
            "assurance, accepted N/A or no-event decision, or audit task credit.",
        ],
        "external_messages_sent": 0,
        "fresh_pair_created": False,
        "source_complete": False,
        "audit_task_credit": False,
        "accepted_na_determinations": 0,
        "active_pair_mutated": False,
    }


def build(repository: Path, private_repository: Path) -> dict:
    """Fail closed on V11, reviewed V14 and selected source, then replay inputs."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    freeze = _p1_inventory(private)
    if freeze != P1_FREEZE:
        raise V12SourceRequestError("Frozen P1 inventory differs")
    old_pinned = pinned._pinned(repository / V11_PLAN, PINS[V11_PLAN])
    old_review = pinned._pinned(private / V11_REVIEW, PINS[V11_REVIEW], private=True)
    route_pinned = pinned._pinned(private / ROUTE_LEDGER, PINS[ROUTE_LEDGER], private=True)
    route_review = pinned._pinned(private / ROUTE_REVIEW, PINS[ROUTE_REVIEW], private=True)
    source_review = pinned._pinned(private / SOURCE_REVIEW, PINS[SOURCE_REVIEW], private=True)
    manifest = pinned._pinned(private / SOURCE_MANIFEST, PINS[SOURCE_MANIFEST], private=True)
    receipt = pinned._pinned(private / SOURCE_RECEIPT, PINS[SOURCE_RECEIPT], private=True)
    _pinned_db(private, {"path": SOURCE_DB, "sha256": PINS[SOURCE_DB]})
    if (
        old_review.get("verdict") != "PASS_MAIN_DRAFT_ONLY_NO_AUDIT_CREDIT"
        or old_review.get("output_sha256", {}).get("PLAN.json") != PINS[V11_PLAN]
        or old_review.get("p1_freeze") != freeze
        or old_review.get("audit_task_credit") is not False
        or old_review.get("external_messages_sent") != 0
        or route_review.get("schema") != "SH_INDEPENDENT_ENG005_ROUTE_V14_MAIN_REVIEW_V1"
        or route_review.get("verdict") != "PASS_MAIN_SELECTED_OPERATING_LEAD_NO_CREDIT"
        or route_review.get("output_sha256", {}).get("LEDGER.json") != PINS[ROUTE_LEDGER]
        or route_review.get("p1_freeze") != freeze
        or route_review.get("audit_task_credit") is not False
        or source_review.get("verdict") != "PASS_MAIN_SELECTED_SOURCE_NO_AUDIT_CREDIT"
        or source_review.get("main_run_sha256")
        != {
            "MANIFEST.json": PINS[SOURCE_MANIFEST],
            "RECEIPT.json": PINS[SOURCE_RECEIPT],
            "company.sqlite3": PINS[SOURCE_DB],
        }
        or source_review.get("p1_freeze") != freeze
        or source_review.get("corporate_emergency_authority_status") != "NOT_EVIDENCED_OPEN"
        or source_review.get("real_deployment") is not False
        or source_review.get("source_complete") is not False
        or source_review.get("audit_task_credit") is not False
        or manifest.get("receipt_sha256") != PINS[SOURCE_RECEIPT]
        or manifest.get("db_sha256") != PINS[SOURCE_DB]
        or manifest.get("native_version_count") != 34
    ):
        raise V12SourceRequestError("Independent V11/V14/ENG005 review join differs")
    old = prior.build(repository, private)
    route_replayed = route.build(repository, private)
    source.verify(private / SOURCE_RUN, repository=repository, private_repository=private)
    if old != old_pinned or route_replayed != route_pinned:
        raise V12SourceRequestError("Reviewed V11 or V14 route fails replay")
    result = _extend(old, route_pinned, receipt, freeze)
    if _p1_inventory(private) != freeze:
        raise V12SourceRequestError("Frozen P1 changed during read-only PBC build")
    return result


def markdown(result: dict) -> str:
    """Render one ENG005 draft group delta with its no-credit boundaries."""
    counts = result["counts"]["A"]
    group = next(g for g in result["request_groups"] if g["request_group_id"] == GROUP)
    lines = [
        "# Unsupported exact clauses: selected ENG005 request delta V12",
        "",
        "All 121 unsupported authored clauses per side remain unsupported across 30 "
        "draft unsent groups. Every V11 row, group, contact, locator and original "
        "request field is retained.",
        "",
        "| Per-side measure | Count |",
        "| --- | ---: |",
        f"| Unsupported authored clauses | {counts['unsupported_exact_clauses']} |",
        "| Possible unaccepted no-event reviews | "
        f"{counts['possible_nonoccurrence_review_candidates']} |",
        "| New selected ENG005 operating leads | 1 |",
        "| Newly source-affected clauses | 1 |",
        "| Newly route-targeted clauses | 0 |",
        "| Cumulative source-affected clauses | "
        f"{counts['v12_cumulative_reviewed_source_affected_unsupported_clauses']} |",
        "| Cumulative route-targeted unsupported clauses | "
        f"{counts['v12_cumulative_targeted_unsupported_clauses']} |",
        "| V12 changed draft next actions | 1 |",
        "| Changed groups, contacts, locators or original requests | 0 |",
        "",
        "One selected fictional company change queue adds 12 Clean and 22 Messy native "
        "originals to the exact authored CC8.1 route. Clean holds emergency execution "
        "for unevidenced corporate authority. Messy retains invalid ordinary and "
        "emergency paths, rollbacks and two OPEN exceptions. The selected lead does "
        "not establish a complete change population or clause satisfaction.",
        "",
        "| Request group | New V12 reviewed lead | V12 draft next action |",
        "| --- | --- | --- |",
        f"| {GROUP} | {SOURCE} | {group['v12_next_action']} |",
        "",
        "All requests remain `DRAFT_NOT_SENT`; all 409 A/B P1 tasks remain "
        "`NOT_STARTED`/`NOT_RUN`. No message, accepted no-event or N/A decision, "
        "audit task credit, fresh pair, Key, grade or Atlas write was issued.",
        "",
    ]
    return "\n".join(lines)
