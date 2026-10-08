"""Bounded emergency-replay discovery lead for the frozen unsupported PBC plan."""

from __future__ import annotations

from pathlib import Path

from . import company_emergency_replay_2027 as replay
from . import documentary_283_route_reconciliation_v13 as route
from . import unsupported_121_pbc_plan as pinned
from . import unsupported_121_pbc_plan_v10 as prior
from .documentary_283_route_reconciliation_v6 import _p1_inventory, _pinned_db

SCHEMA = "SH_UNSUPPORTED_121_PAIRED_SOURCE_REQUEST_PLAN_V11"
BASE = "enterprise/generated/audit-suite"
V10_PLAN = "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V10_2026-09-30.json"
V10_REVIEW = (
    f"{BASE}/unsupported-121-pbc-plan-v10-2026-09-30/independent-review-main-v1/REVIEW.json"
)
ROUTE_LEDGER = f"{BASE}/documentary-283-route-reconciliation-v13-2026-09-30/main-run-v1/LEDGER.json"
ROUTE_REVIEW = (
    f"{BASE}/documentary-283-route-reconciliation-v13-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
ROUTE_REVIEW_SHA = "609ffba4ad9dcdaa4ce370abdb32de995dd2f3f0664275692cf66d7da0e495ec"
SOURCE_ROOT = f"{BASE}/company-emergency-replay-2026-09-30"
SOURCE_RUN = f"{SOURCE_ROOT}/main-run-v1"
SOURCE_REVIEW = f"{SOURCE_ROOT}/independent-review-main-v1/REVIEW.json"
SOURCE_MANIFEST = f"{SOURCE_RUN}/MANIFEST.json"
SOURCE_RECEIPT = f"{SOURCE_RUN}/RECEIPT.json"
SOURCE_DB = f"{SOURCE_RUN}/company.sqlite3"
PINS = {
    V10_PLAN: "ce1ce8ea105dd1dd33f9c0efbfae92a405846940fc267392a64a919b437c4bd3",
    V10_REVIEW: "1c7036ae69fb587f59b21f85ac66154fc5da33e5490b0b6f203c14b3df008317",
    ROUTE_LEDGER: "042ad50cadeb9677d59045d0c263c3e87e320292fd51a7dd3ae484c87d9aba90",
    ROUTE_REVIEW: ROUTE_REVIEW_SHA,
    SOURCE_REVIEW: "2fd0f0d2f72f592c929dc1ae01d1c895a1c90cbdd6ebca776813f796cf4b0a36",
    SOURCE_MANIFEST: "8552fbfe0ebd8487b7bda55e9577cf11b2f45bfa2835d6459cf3265aa3b3455b",
    SOURCE_RECEIPT: "ffe8ee5f874a2581e9502c1b9cca9992fbf4602437ecede9005b50d098762e9c",
    SOURCE_DB: "39dc7d18f22d064a007b42a3ce1f33391cb34aea226eaac9604915e8a73c259b",
}
P1_FREEZE = prior.P1_FREEZE
GROUP = "SH-IAM-005"
TASK = route.TASK
SOURCE = route.SOURCE
SOURCE_LIMIT = route.LIMIT
POL004_TASK = prior.TASK
POL004_SOURCE = prior.SOURCE
NEXT_ACTION_ADDENDUM = (
    "Inspect the exact reviewed fictional emergency-replay originals (8 Clean/15 Messy) "
    "only as a selected discovery lead for the authored emergency-mode clause. Compare "
    "the denied Messy preauthorization path, stale-checkpoint mismatch, corrected local "
    "retest and OPEN local, BA-flowdown, BCM capacity/BIA, IAM and SEC005 historical "
    "gates. Request an authorized deployed ePHI emergency exercise, exact operator and "
    "service access decisions and activity surviving recovery, protected credentials, "
    "complete trust-boundary and recovery populations, period coverage, independent "
    "challenge and qualified review. The selected nonpersonal marker proves no actual "
    "ePHI access, deployed replay, source completeness or clause satisfaction."
)
REF_FIELDS = prior.REF_FIELDS


class V11SourceRequestError(prior.V10SourceRequestError):
    """A reviewed emergency source, route, PBC prefix or no-credit gate changed."""


def _selected_refs(receipt: dict, ledger: dict, old: dict) -> dict[str, list[dict]]:
    """Require the same exact original tuples in native source and V13 route."""
    if (
        receipt.get("schema") != replay.SCHEMA
        or receipt.get("branches") != replay.BRANCHES
        or receipt.get("native_version_counts") != {"CLEAN": 8, "MESSY": 15}
        or receipt.get("selected_population_count") != 1
        or receipt.get("local_open_exception_counts") != {"CLEAN": 0, "MESSY": 1}
        or receipt.get("messy_upstream_gates_remain_open") is not True
        or receipt.get("external_bytes_or_packets") != 0
        or any(
            receipt.get(key) is not False
            for key in (
                "actual_phi_processing",
                "deployed_recovery_proven",
                "source_complete",
                "audit_task_credit",
            )
        )
        or ledger.get("schema") != route.SCHEMA
        or ledger.get("p1_freeze") != P1_FREEZE
        or ledger.get("audit_task_credit") is not False
        or ledger.get("active_pair_mutated") is not False
        or ledger.get("active_p1_tasks") != old["active_p1_tasks"]
    ):
        raise V11SourceRequestError("Emergency source or reviewed route scope differs")
    refs = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        source_rows = receipt.get("records", {}).get(scenario, [])
        expected = [(system, record) for _, system, record, _, _, _ in replay._plan(scenario)]
        selected = [{key: row[key] for key in REF_FIELDS} for row in source_rows]
        route_row = next(
            row for row in ledger["rows"] if row["side"] == side and row["task_id"] == TASK
        )
        prior_row = next(
            row for row in old["rows"] if row["side"] == side and row["task_id"] == TASK
        )
        if (
            len(source_rows) != len(expected)
            or [(row["system"], row["record"]) for row in source_rows] != expected
            or any(
                row["branch"] != replay.BRANCHES[scenario] or row["version"] != 1
                for row in source_rows
            )
            or route_row.get("classification") != "UNSUPPORTED_EXACT_CLAUSE"
            or route_row.get("test_gate_basis") != "AUTHORED_TASK_CLAUSE"
            or route_row.get("authored_test_clause") != route.CLAUSE
            or route_row.get("remaining_test_gate") != route.CLAUSE
            or route_row.get("v13_reviewed_source_ids") != [SOURCE]
            or route_row.get("v13_source_record_refs", {}).get(SOURCE) != selected
            or route_row.get("targeted_integrated_source_ids")
            != [*prior_row["v10_targeted_source_ids"], SOURCE]
            or route_row.get("current_status") != "NOT_STARTED"
            or route_row.get("current_conclusion") != "NOT_RUN"
            or route_row.get("audit_task_credit") is not False
            or prior_row.get("authored_test_clause") != route.CLAUSE
            or prior_row.get("request_group_id") != GROUP
            or prior_row.get("control_id") != GROUP
            or prior_row.get("v6_reviewed_source_ids") != ["IAM005_EMERGENCY_MARKER_V1"]
            or prior_row.get("v10_reviewed_source_ids")
            or prior_row.get("v10_targeted_source_ids")
            != ["IAM005_EMERGENCY_MARKER_V1", "IAM005_LOCAL_V1"]
        ):
            raise V11SourceRequestError("Exact emergency authored route or native roster differs")
        refs[side] = selected
    return refs


def _extend(old: dict, ledger: dict, receipt: dict, freeze: dict) -> dict:
    """Keep every V10 field; add one selected source and one draft group action."""
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
        raise V11SourceRequestError("Reviewed V10 PBC or P1 denominator differs")
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
            raise V11SourceRequestError("V10 task/request or route boundary differs")
        row["v11_reviewed_source_ids"] = [SOURCE] if selected else []
        row["v11_source_limits"] = {SOURCE: SOURCE_LIMIT} if selected else {}
        row["v11_source_record_refs"] = {SOURCE: refs[side]} if selected else {}
        row["v11_targeted_source_ids"] = list(route_row["targeted_integrated_source_ids"])
        if task == POL004_TASK:
            if (
                row["v10_targeted_source_ids"]
                or row["v11_targeted_source_ids"] != [POL004_SOURCE]
                or row["v10_reviewed_source_ids"] != [POL004_SOURCE]
                or route_row["classification"] != "UNSUPPORTED_EXACT_CLAUSE"
            ):
                raise V11SourceRequestError("Reviewed V12 POL004 route target differs")
        elif not selected and row["v11_targeted_source_ids"] != row["v10_targeted_source_ids"]:
            raise V11SourceRequestError("Unselected unsupported route target changed")
        row["v11_next_action"] = (
            row["v10_next_action"] + " " + NEXT_ACTION_ADDENDUM
            if group == GROUP
            else row["v10_next_action"]
        )
        row["v11_next_action_changed_from_v10"] = group == GROUP
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
            or (selected and (group["control_id"], group["routes_per_side"]) != (GROUP, 2))
            or group["request_status"] != "DRAFT_NOT_SENT"
        ):
            raise V11SourceRequestError("V10 IAM005 group or unsent boundary differs")
        leads = [SOURCE] if selected else []
        limits = {SOURCE: SOURCE_LIMIT} if selected else {}
        source_refs = {side: {TASK: {SOURCE: refs[side]}} if selected else {} for side in "AB"}
        action = (
            group["v10_next_action"] + " " + NEXT_ACTION_ADDENDUM
            if selected
            else group["v10_next_action"]
        )
        group.update(
            {
                "v11_reviewed_source_ids": leads,
                "v11_source_limits": limits,
                "v11_source_record_refs_by_side": source_refs,
                "v11_next_action": action,
                "v11_next_action_changed_from_v10": selected,
            }
        )
        delta.update(
            {
                "v11_reviewed_source_ids": leads,
                "v11_source_limits": limits,
                "v11_source_record_refs_by_side": source_refs,
                "v10_next_action_before_v11": previous_group["v10_next_action"],
                "v11_next_action": action,
                "v11_next_action_changed_from_v10": selected,
            }
        )
        groups.append(group)
        deltas.append(delta)
    counts = {}
    for side in "AB":
        selected = [row for row in rows if row["side"] == side]
        affected = sum(
            bool(any(row[f"v{version}_reviewed_source_ids"] for version in range(5, 12)))
            for row in selected
        )
        targeted = sum(bool(row["v11_targeted_source_ids"]) for row in selected)
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
            or sum(bool(row["v11_reviewed_source_ids"]) for row in selected) != 1
            or previous_counts["v10_cumulative_reviewed_source_affected_unsupported_clauses"] != 23
            or previous_counts["v10_cumulative_targeted_unsupported_clauses"] != 34
            or previous_counts["v10_cumulative_changed_request_groups"] != 11
            or affected != 23
            or targeted != 35
        ):
            raise V11SourceRequestError("V11 unsupported/IAM005/no-event denominator differs")
        counts[side] = {
            **previous_counts,
            "v11_new_reviewed_source_leads": 1,
            "v11_newly_source_affected_unsupported_clauses": 0,
            "v11_newly_route_targeted_unsupported_clauses": 1,
            "v11_selected_source_affected_request_groups": 1,
            "v11_next_action_changes_from_v10": 1,
            "v11_cumulative_reviewed_source_affected_unsupported_clauses": 23,
            "v11_cumulative_targeted_unsupported_clauses": 35,
            "v11_cumulative_changed_request_groups": 11,
            "v11_grouping_or_contact_changes": 0,
        }
    if (
        counts["A"] != counts["B"]
        or len(groups) != 30
        or len({group["request_group_id"] for group in groups}) != 30
        or sum(group["v11_next_action_changed_from_v10"] for group in groups) != 1
        or sum(group["v11_next_action_changed_from_v10"] for group in deltas) != 1
    ):
        raise V11SourceRequestError("Paired IAM005 draft group delta differs")
    return {
        "schema": SCHEMA,
        "as_of": "2026-09-30",
        "source_pins": {**old["source_pins"], **PINS},
        "p1_freeze": freeze,
        "active_p1_tasks": old["active_p1_tasks"],
        "reviewed_route_roster": old["reviewed_route_roster"],
        "v13_route_ledger_sha256": PINS[ROUTE_LEDGER],
        "counts": counts,
        "rows": rows,
        "request_groups": groups,
        "group_delta": deltas,
        "candidate_owner_source_queues": old["candidate_owner_source_queues"],
        "nonoccurrence_acceptance_protocol": old["nonoccurrence_acceptance_protocol"],
        "limits": [
            *old["limits"],
            "All V10 row, group, contact, locator and original-request fields remain exact; "
            "only SH-IAM-005 gains a V11 draft next action and selected native lead.",
            "The earlier independently routed POL004 CC5.3 lead also becomes explicitly "
            "targeted in V11; both authored clauses remain UNSUPPORTED_EXACT_CLAUSE.",
            "The authored emergency-mode clause remains unsupported and unrun; the "
            "selected nonpersonal marker is not deployed ePHI recovery evidence.",
            "Messy denied fast path, stale checkpoint, later local retest and historical "
            "BA/BCM/IAM/SEC005 and local OPEN exceptions remain visible.",
            "No complete population, actual ePHI, independent operating test, Type 2 "
            "period, N/A determination or audit task credit.",
        ],
        "external_messages_sent": 0,
        "fresh_pair_created": False,
        "source_complete": False,
        "audit_task_credit": False,
        "accepted_na_determinations": 0,
        "active_pair_mutated": False,
    }


def build(repository: Path, private_repository: Path) -> dict:
    """Fail closed until V13 route review, then replay every pinned source."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    freeze = _p1_inventory(private)
    if freeze != P1_FREEZE:
        raise V11SourceRequestError("Frozen P1 inventory differs")
    old_pinned = pinned._pinned(repository / V10_PLAN, PINS[V10_PLAN])
    old_review = pinned._pinned(private / V10_REVIEW, PINS[V10_REVIEW], private=True)
    route_pinned = pinned._pinned(private / ROUTE_LEDGER, PINS[ROUTE_LEDGER], private=True)
    route_review = pinned._pinned(private / ROUTE_REVIEW, PINS[ROUTE_REVIEW], private=True)
    source_review = pinned._pinned(private / SOURCE_REVIEW, PINS[SOURCE_REVIEW], private=True)
    manifest = pinned._pinned(private / SOURCE_MANIFEST, PINS[SOURCE_MANIFEST], private=True)
    receipt = pinned._pinned(private / SOURCE_RECEIPT, PINS[SOURCE_RECEIPT], private=True)
    _pinned_db(private, {"path": SOURCE_DB, "sha256": PINS[SOURCE_DB]})
    if (
        old_review.get("verdict")
        != "PASS_READ_ONLY_UNSUPPORTED_121_PBC_V10_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or old_review.get("main_tracked_sha256", {}).get(V10_PLAN) != PINS[V10_PLAN]
        or old_review.get("p1_freeze") != freeze
        or old_review.get("audit_task_credit") is not False
        or route_review.get("schema") != "SH_DOCUMENTARY_283_ROUTE_V13_INDEPENDENT_MAIN_REVIEW_V1"
        or route_review.get("verdict") != "PASS_MAIN_SELECTED_EMERGENCY_LEAD_NO_CREDIT"
        or route_review.get("output_sha256", {}).get("LEDGER.json") != PINS[ROUTE_LEDGER]
        or route_review.get("p1_freeze") != freeze
        or route_review.get("audit_task_credit") is not False
        or source_review.get("verdict")
        != "PASS_SELECTED_EMERGENCY_REPLAY_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or source_review.get("main_run_sha256")
        != {
            "MANIFEST.json": PINS[SOURCE_MANIFEST],
            "RECEIPT.json": PINS[SOURCE_RECEIPT],
            "company.sqlite3": PINS[SOURCE_DB],
        }
        or source_review.get("p1_freeze") != freeze
        or source_review.get("source_complete") is not False
        or source_review.get("audit_task_credit") is not False
        or manifest.get("receipt_sha256") != PINS[SOURCE_RECEIPT]
        or manifest.get("db_sha256") != PINS[SOURCE_DB]
        or manifest.get("native_version_count") != 23
    ):
        raise V11SourceRequestError("Independent V10/V13/replay review join differs")
    old = prior.build(repository, private)
    route_replayed = route.build(repository, private)
    replay.verify(private / SOURCE_RUN, repository=repository, private_repository=private)
    if old != old_pinned or route_replayed != route_pinned:
        raise V11SourceRequestError("Reviewed V10 or V13 route fails replay")
    result = _extend(old, route_pinned, receipt, freeze)
    if _p1_inventory(private) != freeze:
        raise V11SourceRequestError("Frozen P1 changed during read-only PBC build")
    return result


def markdown(result: dict) -> str:
    """Render the one-group emergency replay draft delta without credit."""
    counts = result["counts"]["A"]
    group = next(g for g in result["request_groups"] if g["request_group_id"] == GROUP)
    lines = [
        "# Unsupported exact clauses: emergency replay request delta V11",
        "",
        "All 121 unsupported authored clauses per side remain unsupported across 30 "
        "draft unsent groups. Every V10 row, group, contact, locator and original "
        "request field is retained.",
        "",
        "| Per-side measure | Count |",
        "| --- | ---: |",
        f"| Unsupported authored clauses | {counts['unsupported_exact_clauses']} |",
        "| Possible unaccepted no-event reviews | "
        f"{counts['possible_nonoccurrence_review_candidates']} |",
        "| New selected emergency replay leads | 1 |",
        "| Newly source-affected clauses | 0 (IAM005 already affected) |",
        "| Newly route-targeted clauses | 1 (prior POL004 route V12) |",
        "| Cumulative source-affected clauses | "
        f"{counts['v11_cumulative_reviewed_source_affected_unsupported_clauses']} |",
        "| Cumulative route-targeted unsupported clauses | "
        f"{counts['v11_cumulative_targeted_unsupported_clauses']} |",
        "| V11 changed draft next actions | 1 |",
        "| Changed groups, contacts, locators or original requests | 0 |",
        "",
        "The reviewed local replay adds 8 Clean and 15 Messy selected native originals "
        "to the exact authored IAM005 emergency-mode discovery route. Messy retains "
        "a denied fast path, stale checkpoint, later local retest and OPEN upstream "
        "and local exceptions. No actual ePHI, deployed replay or independent "
        "assurance is established; the clause remains unsupported and unrun.",
        "",
        "| Request group | New V11 reviewed lead | V11 draft next action |",
        "| --- | --- | --- |",
        f"| {GROUP} | {SOURCE} | {group['v11_next_action']} |",
        "",
        "All requests remain `DRAFT_NOT_SENT`; all 409 A/B P1 tasks remain "
        "`NOT_STARTED`/`NOT_RUN`. No message, accepted no-event or N/A decision, "
        "audit task credit, fresh pair, Key, grade or Atlas write was issued.",
        "",
    ]
    return "\n".join(lines)
