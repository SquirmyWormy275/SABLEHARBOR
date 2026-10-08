"""Read-only blocked readiness diagnostic after reviewed GOV PBC reconciliation."""

from __future__ import annotations

import argparse
import json
import os
import stat
import tempfile
from copy import deepcopy
from pathlib import Path

from . import audit_readiness_gate_v4 as prior
from . import documentary_283_route_reconciliation_v16 as routes
from .documentary_283_route_reconciliation_v6 import _p1_inventory

SCHEMA = "SH_FICTIONAL_AUDIT_READINESS_GATE_V5"
BASE = "enterprise/generated/audit-suite"
PINS = {
    "v4_report": (
        "private",
        f"{BASE}/readiness-gate-v4-2026-10-01/main-run-v1/REPORT.json",
        "f977028b6d391a3407b685696c0194cf837ddfdf12f2aabffa7a3fe8f28ced5e",
    ),
    "v4_markdown": (
        "private",
        f"{BASE}/readiness-gate-v4-2026-10-01/main-run-v1/REPORT.md",
        "41aa97deab09c6da85ade5169e8aa23db57faa87d71aacf5d635341b7f6bdb06",
    ),
    "v4_review": (
        "private",
        f"{BASE}/readiness-gate-v4-2026-10-01/independent-review-main-v1/REVIEW.json",
        "c38ef47b6fee6b7914e8a970189242c594cdfb74876844631cb4a6dfb940bc72",
    ),
    "pbc_v14": (
        "repo",
        "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V14_2026-10-01.json",
        "c414799171d1256222f80675be0e0b4dd5fff45ce5d345f7540cd34f08a905b4",
    ),
    "pbc_v14_markdown": (
        "repo",
        "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V14_2026-10-01.md",
        "f322e65e97857314876b63a7634555f57d727d7f039897751a54d9928161918d",
    ),
    "pbc_v14_main": (
        "private",
        f"{BASE}/unsupported-121-pbc-plan-v14-2026-10-01/main-run-v1/PLAN.json",
        "c414799171d1256222f80675be0e0b4dd5fff45ce5d345f7540cd34f08a905b4",
    ),
    "pbc_v14_main_markdown": (
        "private",
        f"{BASE}/unsupported-121-pbc-plan-v14-2026-10-01/main-run-v1/PLAN.md",
        "f322e65e97857314876b63a7634555f57d727d7f039897751a54d9928161918d",
    ),
    "pbc_v14_review": (
        "private",
        f"{BASE}/unsupported-121-pbc-plan-v14-2026-10-01/independent-review-main-v1/REVIEW.json",
        "2a212e9ff08e9bad9532b4c88c685094251424fbc7bfd973451cadad2801819a",
    ),
}
P1_FREEZE = prior.P1_FREEZE
READINESS_FALSE = prior.READINESS_FALSE
GOV_AUTHORED = set(routes.AUTHORED)
SOURCE = routes.SOURCE
OLD_GOV_BLOCKER = (
    "Two GOV CC1.2 authored source targets await PBC request-plan reconciliation; "
    "selected committee-cycle records do not establish an actual Board meeting, "
    "legal quorum, adopted minutes or full-period oversight."
)
NEW_GOV_BLOCKER = (
    "The two GOV CC1.2 authored source targets are reconciled to draft PBC leads, "
    "but the selected committee cycle does not establish an actual Board meeting, "
    "legal quorum, adopted minutes, collective approval or full-period oversight."
)


class GateError(prior.GateError):
    """Pinned snapshot, exact source join or no-credit boundary changed."""


def _load_pins(repository: Path, private: Path) -> tuple[dict, dict]:
    loaded, identities = {}, {}
    for key, (scope, relative, expected) in PINS.items():
        if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
            raise GateError(f"{key}: accepted independent review pin pending")
        path = (private if scope == "private" else repository) / relative
        prior.prior._reject_symlink_chain(path)
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise GateError(f"{key}: ordinary single-link file required")
        if scope == "private" and stat.S_IMODE(info.st_mode) != 0o600:
            raise GateError(f"{key}: private 0600 mode required")
        if prior.prior._digest(path) != expected:
            raise GateError(f"{key}: pinned SHA-256 differs")
        loaded[key] = path.read_bytes()
        identities[key] = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    return loaded, identities


def _assert_review_boundaries(data: dict[str, bytes]) -> tuple[dict, dict]:
    base = json.loads(data["v4_report"])
    base_review = json.loads(data["v4_review"])
    pbc = json.loads(data["pbc_v14"])
    pbc_review = json.loads(data["pbc_v14_review"])
    if (
        base_review.get("schema") != "SH_INDEPENDENT_READINESS_GATE_V4_MAIN_REVIEW_V1"
        or base_review.get("verdict") != "PASS_MAIN_READ_ONLY_BLOCKED_NO_CREDIT"
        or base_review.get("output_sha256")
        != {"REPORT.json": PINS["v4_report"][2], "REPORT.md": PINS["v4_markdown"][2]}
        or base_review.get("p1_freeze") != P1_FREEZE
        or base_review.get("source_complete") is not False
        or base_review.get("fresh_pair_eligible") is not False
        or base_review.get("audit_ready") is not False
        or base_review.get("audit_task_credit") is not False
        or pbc_review.get("schema") != "SH_INDEPENDENT_GOV_PBC_V14_MAIN_REVIEW_V1"
        or pbc_review.get("verdict") != "PASS_MAIN_DRAFT_ONLY_NO_AUDIT_CREDIT"
        or pbc_review.get("output_sha256")
        != {"PLAN.json": PINS["pbc_v14"][2], "PLAN.md": PINS["pbc_v14_markdown"][2]}
        or pbc_review.get("p1_freeze") != P1_FREEZE
        or pbc_review.get("source_complete") is not False
        or pbc_review.get("fresh_audit_pair_created") is not False
        or pbc_review.get("audit_task_credit") is not False
        or data["pbc_v14"] != data["pbc_v14_main"]
        or data["pbc_v14_markdown"] != data["pbc_v14_main_markdown"]
        or base.get("schema") != prior.SCHEMA
        or base.get("as_of") != "2026-10-01"
        or pbc.get("schema") != "SH_UNSUPPORTED_121_PAIRED_SOURCE_REQUEST_PLAN_V14"
        or pbc.get("as_of") != "2026-10-01"
        or base.get("p1_freeze") != P1_FREEZE
        or pbc.get("p1_freeze") != P1_FREEZE
        or any(base.get(key) is not False for key in READINESS_FALSE)
        or pbc.get("source_complete") is not False
        or pbc.get("fresh_pair_created") is not False
        or pbc.get("audit_task_credit") is not False
        or pbc.get("active_pair_mutated") is not False
        or base.get("accepted_na_determinations") != 0
        or pbc.get("accepted_na_determinations") != 0
        or base.get("external_messages_sent") != 0
        or pbc.get("external_messages_sent") != 0
    ):
        raise GateError("Reviewed V4/V14 claim or output boundary differs")
    return base, pbc


def _assemble(base: dict, pbc: dict) -> dict:
    """Append the exact V14 draft PBC delta to a reviewed V4 blocked report."""
    if (
        base.get("schema") != prior.SCHEMA
        or pbc.get("schema") != "SH_UNSUPPORTED_121_PAIRED_SOURCE_REQUEST_PLAN_V14"
        or base.get("p1_freeze") != P1_FREEZE
        or pbc.get("p1_freeze") != P1_FREEZE
        or any(base.get(key) is not False for key in READINESS_FALSE)
        or base.get("accepted_na_determinations") != 0
        or base.get("external_messages_sent") != 0
        or pbc.get("external_messages_sent") != 0
        or pbc.get("accepted_na_determinations") != 0
        or pbc.get("fresh_pair_created") is not False
        or pbc.get("source_complete") is not False
        or pbc.get("audit_task_credit") is not False
        or pbc.get("active_pair_mutated") is not False
        or len(base.get("source_roster", [])) != 37
        or len(base.get("request_groups", [])) != 30
        or len(pbc.get("request_groups", [])) != 30
        or len(pbc.get("rows", [])) != 242
        or len(pbc.get("group_delta", [])) != 30
        or len(base.get("readiness_blockers", [])) < 1
        or base["readiness_blockers"][-1] != OLD_GOV_BLOCKER
    ):
        raise GateError("V4/V14 blocker or no-credit prefix differs")
    expected_pending = sorted(f"{side}:{task}" for side in "AB" for task in GOV_AUTHORED)
    if base.get("route_pbc_synchronization_pending_task_ids") != expected_pending:
        raise GateError("Exact four GOV route/PBC pending IDs differ")
    blockers = deepcopy(base["blockers_by_family_control"])
    if sum(map(len, blockers.values())) != 43:
        raise GateError("Exact 43-control blocker map differs")
    unsupported = {}
    actual_pending = []
    for controls in blockers.values():
        for control, item in controls.items():
            actual_pending.extend(item["route_pbc_sync_pending_task_ids"])
            for key in item["unsupported_task_ids"]:
                if key in unsupported:
                    raise GateError("Duplicate unsupported blocker task")
                unsupported[key] = (control, item)
    if sorted(actual_pending) != expected_pending or len(unsupported) != 242:
        raise GateError("V4 GOV pending or unsupported blocker roster differs")
    pbc_rows = {f"{row['side']}:{row['task_id']}": row for row in pbc["rows"]}
    if set(pbc_rows) != set(unsupported):
        raise GateError("V14 PBC row roster differs from unsupported blockers")
    expected_side = {
        "source_cohorts": 37,
        "native_business_versions": 840,
        "routes": 283,
        "targeted_routes": 183,
        "partial_routes": 141,
        "design_routes": 21,
        "unsupported_exact_clauses": 121,
        "route_targeted_unsupported_clauses": 37,
        "pbc_targeted_unsupported_clauses": 35,
        "source_affected_unsupported_clauses": 27,
        "draft_unsent_request_groups": 30,
        "unaccepted_no_event_candidates": 53,
        "p1_tasks_not_started_not_run": 409,
    }
    for side in "AB":
        counts = pbc["counts"][side]
        side_rows = [row for row in pbc_rows.values() if row["side"] == side]
        source_affected = sum(
            any(row[f"v{version}_reviewed_source_ids"] for version in range(5, 15))
            for row in side_rows
        )
        targeted = sum(bool(row["v14_targeted_source_ids"]) for row in side_rows)
        if (
            base["sides"][side] != expected_side
            or len(side_rows) != 121
            or len({row["control_id"] for row in side_rows}) != 28
            or sum(row["possible_nonoccurrence_review_candidate"] for row in side_rows) != 53
            or source_affected != 29
            or targeted != 37
            or pbc["active_p1_tasks"][side]
            != {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"}
            or counts.get("v13_cumulative_reviewed_source_affected_unsupported_clauses") != 27
            or counts.get("v13_cumulative_targeted_unsupported_clauses") != 35
            or counts.get("v14_cumulative_reviewed_source_affected_unsupported_clauses") != 29
            or counts.get("v14_cumulative_targeted_unsupported_clauses") != 37
            or counts.get("v14_cumulative_changed_request_groups") != 17
            or counts.get("v14_new_reviewed_source_leads") != 2
            or counts.get("v14_newly_route_targeted_unsupported_clauses") != 2
        ):
            raise GateError(f"{side}: reviewed V4/V14 denominator differs")
    selected = []
    for key, row in pbc_rows.items():
        side, task = row["side"], row["task_id"]
        control, item = unsupported[key]
        limit = item["route_limits"][key]
        is_gov = task in GOV_AUTHORED
        expected_source_ids = [SOURCE] if is_gov else []
        expected_limits = limit["v16_source_limits"] if is_gov else {}
        expected_refs = limit["v16_source_record_refs"] if is_gov else {}
        if (
            row["control_id"] != control
            or row["remaining_test_gate"] != item["remaining_gates"][key]
            or row["pbc_request_status"] != "DRAFT_NOT_SENT"
            or row["current_task_status"] != "NOT_STARTED"
            or row["current_task_conclusion"] != "NOT_RUN"
            or row["task_credit"] is not False
            or row["accepted_nonoccurrence_status"] == "ACCEPTED"
            or row["v13_reviewed_source_ids"] != limit["pbc_v13_reviewed_source_ids"]
            or row["v13_source_limits"] != limit["pbc_v13_source_limits"]
            or row["v13_source_record_refs"] != limit["pbc_v13_source_record_refs"]
            or row["v14_reviewed_source_ids"] != expected_source_ids
            or row["v14_source_limits"] != expected_limits
            or row["v14_source_record_refs"] != expected_refs
            or row["v14_targeted_source_ids"] != limit["targeted_source_ids"]
            or row["v14_next_action_changed_from_v13"] is not is_gov
            or (not is_gov and row["v14_next_action"] != row["v13_next_action"])
            or (is_gov and row["v14_next_action"] == row["v13_next_action"])
        ):
            raise GateError(f"{key}: reviewed GOV route/PBC source join differs")
        if is_gov:
            if (
                key not in item["route_pbc_sync_pending_task_ids"]
                or row["request_group_id"] != row["control_id"]
                or limit["targeted_source_ids"] != [SOURCE]
                or len(next(iter(expected_refs.values()))) != (9 if side == "A" else 14)
            ):
                raise GateError(f"{key}: exact selected GOV roster or refs differ")
            selected.append(key)
        limit.update(
            pbc_v14_reviewed_source_ids=row["v14_reviewed_source_ids"],
            pbc_v14_targeted_source_ids=row["v14_targeted_source_ids"],
            pbc_v14_source_limits=row["v14_source_limits"],
            pbc_v14_source_record_refs=row["v14_source_record_refs"],
        )
    if sorted(selected) != expected_pending:
        raise GateError("Exactly two GOV selected PBC leads per side required")
    for controls in blockers.values():
        for item in controls.values():
            item["route_pbc_sync_pending_task_ids"] = []
    base_groups = {group["request_group_id"]: group for group in base["request_groups"]}
    group_rows = {group["request_group_id"]: group for group in pbc["request_groups"]}
    if set(base_groups) != set(group_rows) or len(group_rows) != 30:
        raise GateError("V14 PBC group roster differs")
    groups = []
    for name, previous in base_groups.items():
        group = group_rows[name]
        is_gov = name in {"SH-GOV-001", "SH-GOV-004"}
        if (
            group["control_id"] != previous["control_id"]
            or group["task_ids_per_side"] != previous["task_ids_per_side"]
            or group["request_status"] != previous["status"]
            or group["task_credit"] is not False
            or previous["next_action"] != group["v13_next_action"]
            or any(group[key] != value for key, value in previous.items() if key.startswith("v"))
            or group["v14_next_action_changed_from_v13"] is not is_gov
            or group["v14_reviewed_source_ids"] != ([SOURCE] if is_gov else [])
            or group["v14_source_limits"] != ({SOURCE: routes.LIMIT} if is_gov else {})
            or (not is_gov and group["v14_next_action"] != group["v13_next_action"])
            or (is_gov and group["v14_next_action"] == group["v13_next_action"])
        ):
            raise GateError(f"{name}: V13 group prefix or V14 draft delta differs")
        for side in "AB":
            expected_group_refs = {
                task: {SOURCE: pbc_rows[f"{side}:{task}"]["v14_source_record_refs"][SOURCE]}
                for task in group["task_ids_per_side"][side]
                if task in GOV_AUTHORED
            }
            if group["v14_source_record_refs_by_side"][side] != expected_group_refs:
                raise GateError(f"{name}: V14 selected group source refs differ")
        groups.append(
            {
                **previous,
                "next_action": group["v14_next_action"],
                **{key: value for key, value in group.items() if key.startswith("v14_")},
            }
        )
    side_counts = deepcopy(base["sides"])
    for side in "AB":
        side_counts[side]["pbc_targeted_unsupported_clauses"] = 37
        side_counts[side]["source_affected_unsupported_clauses"] = 29
    report = deepcopy(base)
    report.update(
        schema=SCHEMA,
        as_of="2026-10-01",
        pins={
            **base["pins"],
            **{
                key: {"scope": scope, "path": relative, "sha256": sha}
                for key, (scope, relative, sha) in PINS.items()
            },
        },
        sides=side_counts,
        request_groups=groups,
        blockers_by_family_control=blockers,
        route_pbc_synchronization_pending_task_ids=[],
        boundary_limits={**base["boundary_limits"], "requests_v14": pbc["limits"]},
        readiness_blockers=[*base["readiness_blockers"][:-1], NEW_GOV_BLOCKER],
    )
    if (
        any(report[key] is not False for key in READINESS_FALSE)
        or report["accepted_na_determinations"] != 0
        or report["external_messages_sent"] != 0
        or report["p1_freeze"] != P1_FREEZE
    ):
        raise GateError("V5 readiness or frozen pair unexpectedly promoted")
    return report


def build(repository: Path, private_repository: Path) -> dict:
    """Read only pinned reviewed snapshots; never recursively run predecessor builders."""
    prior.prior._reject_symlink_chain(private_repository)
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    if _p1_inventory(private) != P1_FREEZE:
        raise GateError("Frozen P1 inventory differs")
    data, identities = _load_pins(repository, private)
    base, pbc = _assert_review_boundaries(data)
    report = _assemble(base, pbc)
    after, after_ids = _load_pins(repository, private)
    if (after, after_ids) != (data, identities) or _p1_inventory(private) != P1_FREEZE:
        raise GateError("Pinned snapshot or frozen P1 changed during read-only gate")
    return report


def markdown(report: dict) -> str:
    counts = report["sides"]["A"]
    lines = [
        "# Fictional audit readiness gate V5",
        "",
        "**Blocked.** The two GOV CC1.2 authored route targets now have selected draft PBC leads. "
        "The exact clauses and all 43 controls remain blocked and unrun.",
        "",
        "| Per side | Count |",
        "| --- | ---: |",
    ]
    for label, key in (
        ("Selected source cohorts", "source_cohorts"),
        ("Native business versions", "native_business_versions"),
        ("Documentary/activity routes", "routes"),
        ("Targeted routes", "targeted_routes"),
        ("Partial routes", "partial_routes"),
        ("Design context routes", "design_routes"),
        ("Unsupported exact clauses", "unsupported_exact_clauses"),
        ("Route-targeted unsupported clauses", "route_targeted_unsupported_clauses"),
        ("PBC-targeted unsupported clauses", "pbc_targeted_unsupported_clauses"),
        ("Source-affected unsupported clauses", "source_affected_unsupported_clauses"),
        ("Draft unsent request groups", "draft_unsent_request_groups"),
        ("Unaccepted possible no-event cases", "unaccepted_no_event_candidates"),
        ("Frozen NOT_STARTED/NOT_RUN tasks", "p1_tasks_not_started_not_run"),
    ):
        lines.append(f"| {label} | {counts[key]} |")
    lines += [
        "",
        "The route/PBC synchronization pending set is empty. The selected GOV cycle still "
        "lacks an actual Board meeting, legal quorum, adopted minutes, collective approval "
        "and full-period oversight. The PRD claimant and delivery remain unverified.",
        "",
        "`source_complete=false`; `fresh_pair_eligible=false`; `audit_ready=false`. "
        "No N/A decision, external request, collection, task credit, Key or grade was issued.",
        "",
    ]
    return "\n".join(lines)


def write(repository: Path, private_repository: Path, destination: Path) -> dict:
    destination = Path(destination).absolute()
    prior.prior._reject_symlink_chain(destination)
    if destination.exists() or destination.is_symlink():
        raise GateError("Fresh destination required")
    report = build(repository, private_repository)
    if destination.parent.exists():
        if (
            not destination.parent.is_dir()
            or stat.S_IMODE(destination.parent.stat().st_mode) != 0o700
        ):
            raise GateError("Preexisting output parent must already be private 0700")
    else:
        destination.parent.mkdir(parents=True, mode=0o700)
    prior.prior._reject_symlink_chain(destination)
    with tempfile.TemporaryDirectory(prefix=".readiness-gate-", dir=destination.parent) as temp:
        stage = Path(temp)
        for name, content in (
            ("REPORT.json", json.dumps(report, sort_keys=True, indent=2) + "\n"),
            ("REPORT.md", markdown(report)),
        ):
            path = stage / name
            path.write_text(content)
            path.chmod(0o600)
        os.rename(stage, destination)
    return report


def verify(destination: Path, repository: Path, private_repository: Path) -> dict:
    destination = Path(destination)
    prior.prior._reject_symlink_chain(destination)
    if (
        destination.is_symlink()
        or stat.S_IMODE(destination.stat().st_mode) != 0o700
        or stat.S_IMODE(destination.parent.stat().st_mode) != 0o700
        or {path.name for path in destination.iterdir()} != {"REPORT.json", "REPORT.md"}
    ):
        raise GateError("Exact private two-file gate output required")
    for path in destination.iterdir():
        info = path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or stat.S_IMODE(info.st_mode) != 0o600
        ):
            raise GateError("Private ordinary output required")
    actual = json.loads((destination / "REPORT.json").read_text())
    expected = build(repository, private_repository)
    if actual != expected or (destination / "REPORT.md").read_text() != markdown(expected):
        raise GateError("Gate output differs from pinned reviewed snapshots")
    return actual


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    result = (
        write(args.repository, args.private_repository, args.destination)
        if args.action == "create"
        else verify(args.destination, args.repository, args.private_repository)
    )
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "audit_ready": result["audit_ready"],
                "sides": result["sides"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
