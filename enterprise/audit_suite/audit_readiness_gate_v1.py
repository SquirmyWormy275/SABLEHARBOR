"""Read-only, fail-closed readiness diagnostic over reviewed fictional sources.

This gate reports the currently blocked workflow; it never accepts evidence or
updates a P1 task. The private main-local reviews and exact bytes are inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from . import documentary_283_route_reconciliation_v6 as frozen
from . import documentary_283_route_reconciliation_v9 as routes
from . import fictional_2027_candidate_registry_v10 as candidates
from . import fictional_2027_source_portfolio_v10 as portfolio
from . import unsupported_121_pbc_plan_v8 as requests

SCHEMA = "SH_FICTIONAL_AUDIT_READINESS_GATE_V1"
BASE = "enterprise/generated/audit-suite"
PINS = {
    "v10_review": (
        "private",
        f"{BASE}/company-source-portfolio-v10-2026-09-30/independent-review-main-v1/REVIEW.json",
        "395336ae7c9bdb68ceba5e3da19732e01fbc9b11c6c1bbed7d0438c02f6a3497",
    ),
    "v10_portfolio": (
        "private",
        f"{BASE}/company-source-portfolio-v10-2026-09-30/main-run-v1/REPORT.json",
        "5e76c4be99824fade2fdc6c7a9b462090990aa3803a07b2e17ff8227c7eada0a",
    ),
    "v10_candidate_a": (
        "private",
        f"{BASE}/company-source-portfolio-v10-2026-09-30/main-candidate-v1/A.json",
        "9c74e512b5ac1a780d927c9ba1c7860cd0da4fc5fc6c4d4401bc60c92a7d6801",
    ),
    "v10_candidate_b": (
        "private",
        f"{BASE}/company-source-portfolio-v10-2026-09-30/main-candidate-v1/B.json",
        "477fbed64bdebb7e1d91c2cdfb163d762d20f6127f6bd42f43edf4fc5debeecc",
    ),
    "v10_candidate_report": (
        "private",
        f"{BASE}/company-source-portfolio-v10-2026-09-30/main-candidate-v1/REPORT.json",
        "9753f9af7236e1b014361596e6f24c1407c0c29dfacdab7248b093f6d76bdbdf",
    ),
    "v9_route_review": (
        "private",
        f"{BASE}/documentary-283-route-reconciliation-v9-2026-09-30/independent-review-main-v1/REVIEW.json",
        "c290249ae02caa147566e590abe79b3b56ac45d27953dc9133a123f8ba045156",
    ),
    "v9_route": (
        "repo",
        "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V9_2026-09-30.json",
        "73483c9f47cdc58a6aae94f65cdaa1a2e1b038bc2d0e67061b1dd30ba0364c07",
    ),
    "pbc_v8_review": (
        "private",
        f"{BASE}/unsupported-121-pbc-plan-v8-2026-09-30/independent-review-main-v1/REVIEW.json",
        "bbbe153ef0110ddca325bd88830e521b14d8243aa09c1b65963946c02da68d65",
    ),
    "pbc_v8": (
        "repo",
        "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V8_2026-09-30.json",
        "02ecac983e06c8757f14ae252f4268b4d552bd21be7334707e0bd46fc7feb59a",
    ),
}
P1_FREEZE = {
    "file_count": 538,
    "inventory_sha256": "f266ef682b502b3b093170f8a7b64fcf5cbab722d5c8ddf6715a63c0e535360f",
}


class GateError(ValueError):
    """An input, row join, or readiness boundary changed."""


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _reject_symlink_chain(path: Path) -> None:
    """Reject aliases at every existing component, including the supplied root."""
    absolute = Path(path).absolute()
    for component in reversed((absolute, *absolute.parents)):
        try:
            mode = component.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise GateError(f"Symlinked path component forbidden: {component}")


def _load_pins(repository: Path, private: Path) -> tuple[dict, dict]:
    loaded = {}
    identities = {}
    for key, (scope, relative, expected) in PINS.items():
        path = (private if scope == "private" else repository) / relative
        if scope == "private":
            _reject_symlink_chain(path)
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise GateError(f"{key}: ordinary single-link file required")
        if scope == "private" and stat.S_IMODE(info.st_mode) != 0o600:
            raise GateError(f"{key}: private 0600 mode required")
        if _digest(path) != expected:
            raise GateError(f"{key}: pinned SHA-256 differs")
        loaded[key] = json.loads(path.read_text())
        identities[key] = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    return loaded, identities


def _assert_review_boundaries(data: dict) -> None:
    v10 = data["v10_review"]
    route = data["v9_route_review"]
    pbc = data["pbc_v8_review"]
    if (
        v10.get("verdict") != "PASS_PARTIAL_PENDING_ADDRESSABLE_REGISTRY_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or v10.get("main_output_sha256")
        != {
            "portfolio_report": PINS["v10_portfolio"][2],
            "candidate_A": PINS["v10_candidate_a"][2],
            "candidate_B": PINS["v10_candidate_b"][2],
            "candidate_report": PINS["v10_candidate_report"][2],
        }
        or route.get("verdict")
        != "PASS_READ_ONLY_PENDING_ADDRESSABLE_ROUTE_RECONCILIATION_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or route.get("main_tracked_sha256", {}).get(PINS["v9_route"][1]) != PINS["v9_route"][2]
        or pbc.get("verdict")
        != "PASS_READ_ONLY_UNSUPPORTED_CLAUSE_REQUEST_DELTA_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or pbc.get("main_tracked_sha256", {}).get(PINS["pbc_v8"][1]) != PINS["pbc_v8"][2]
    ):
        raise GateError("Independent review or exact output join differs")
    for review in (v10, route, pbc):
        if review.get("audit_task_credit") is True or review.get("active_pair_mutated") is True:
            raise GateError("Review asserts credit or P1 mutation")
    if route.get("p1_freeze") != P1_FREEZE or pbc.get("p1_freeze") != P1_FREEZE:
        raise GateError("Review P1 freeze differs")


def _assemble(port: dict, candidate: dict, ledger: dict, pbc: dict) -> dict:
    """Join every task and request row, then summarize blockers by family/control."""
    if (
        (port.get("source_count"), port.get("native_versions"), port.get("source_component_count"))
        != (31, 710, 32)
        or port.get("source_complete") is not False
        or port.get("fresh_audit_pair_created") is not False
        or port.get("audit_task_credit") is not False
        or len(port.get("sources", [])) != 31
        or sum(row["native_versions"] for row in port["sources"]) != 710
        or candidate.get("source_complete") is not False
        or candidate.get("fresh_audit_pair_created") is not False
        or candidate.get("audit_task_credit") is not False
        or candidate.get("grants_or_collections_created") is not False
        or candidate.get("reviewed_native_versions") != 710
        or ledger.get("audit_task_credit") is not False
        or ledger.get("active_pair_mutated") is not False
        or pbc.get("audit_task_credit") is not False
        or pbc.get("active_pair_mutated") is not False
        or pbc.get("fresh_pair_created") is not False
        or pbc.get("external_messages_sent") != 0
        or pbc.get("accepted_na_determinations") != 0
        or ledger.get("p1_freeze") != P1_FREEZE
        or pbc.get("p1_freeze") != P1_FREEZE
    ):
        raise GateError("Source, route, request or P1 claim boundary differs")
    source_names = [row["source"] for row in port["sources"]]
    if len(set(source_names)) != 31:
        raise GateError("Source cohort roster is not unique")
    for side in "AB":
        row = candidate["sides"][side]
        pins = row["source_pins"]
        if (
            row.get("source_complete") is not False
            or (
                row.get("source_cohort_count"),
                row.get("scenario_source_component_count"),
                row.get("component_count"),
                row.get("system_alias_count"),
            )
            != (31, 32, 45, 281)
            or len(pins) != 32
            or sorted(set(pin["source"] for pin in pins)) != sorted(source_names)
        ):
            raise GateError(f"{side}: candidate source roster differs")
        for source in port["sources"]:
            matched = [pin for pin in pins if pin["source"] == source["source"]]
            if not matched or any(
                pin["source_review_sha256"] != source["review_sha256"]
                or pin["receipt_sha256"] != source["receipt_sha256"]
                or pin["manifest_sha256"] != source["manifest_sha256"]
                for pin in matched
            ):
                raise GateError(
                    f"{side}: candidate/native source pin join differs: {source['source']}"
                )
    route_rows = ledger.get("rows", [])
    request_rows = pbc.get("rows", [])
    if len(route_rows) != 566 or len(request_rows) != 242:
        raise GateError("Route or request row denominator differs")
    route_index = {(row["side"], row["task_id"]): row for row in route_rows}
    request_index = {(row["side"], row["task_id"]): row for row in request_rows}
    if len(route_index) != 566 or len(request_index) != 242:
        raise GateError("Duplicate route or request key")
    grouped: dict[str, dict[str, dict]] = defaultdict(dict)
    side_counts = {}
    for side in "AB":
        side_routes = [row for row in route_rows if row["side"] == side]
        side_requests = [row for row in request_rows if row["side"] == side]
        classes = Counter(row["classification"] for row in side_routes)
        if len(side_routes) != 283 or classes != {
            "SOURCE_CANDIDATE_PARTIAL": 132,
            "DESIGN_CONTEXT_ONLY": 30,
            "UNSUPPORTED_EXACT_CLAUSE": 121,
        }:
            raise GateError(f"{side}: route classes differ")
        if sum(bool(row["targeted_integrated_source_ids"]) for row in side_routes) != 170:
            raise GateError(f"{side}: targeted route denominator differs")
        if (
            len(side_requests) != 121
            or sum(bool(row["possible_nonoccurrence_review_candidate"]) for row in side_requests)
            != 53
        ):
            raise GateError(f"{side}: unsupported/no-event denominator differs")
        for task_source in (ledger, pbc):
            if task_source["active_p1_tasks"][side] != {
                "task_count": 409,
                "status": "NOT_STARTED",
                "conclusion": "NOT_RUN",
            }:
                raise GateError(f"{side}: frozen P1 task status differs")
        for route in side_routes:
            if (
                route["current_status"],
                route["current_conclusion"],
                route["audit_task_credit"],
                route["actual_operation_eligibility_as_of_packet"],
            ) != ("NOT_STARTED", "NOT_RUN", False, False):
                raise GateError(f"{side}: route task gained status, operation or credit")
            family = route["family"]
            control = route["control_id"]
            control_row = grouped[family].setdefault(
                control,
                {
                    "route_classes": Counter(),
                    "targeted_task_ids": [],
                    "unsupported_task_ids": [],
                    "design_task_ids": [],
                    "partial_task_ids": [],
                    "draft_request_group_ids": set(),
                    "unaccepted_no_event_task_ids": [],
                    "remaining_gates": {},
                    "route_limits": {},
                },
            )
            task_key = f"{side}:{route['task_id']}"
            control_row["route_classes"][route["classification"]] += 1
            if route["targeted_integrated_source_ids"]:
                control_row["targeted_task_ids"].append(task_key)
            if route["classification"] == "UNSUPPORTED_EXACT_CLAUSE":
                key = (side, route["task_id"])
                if key not in request_index:
                    raise GateError(f"{side}: unsupported route lacks PBC row: {route['task_id']}")
                req = request_index[key]
                comparisons = {
                    "authored_test_clause": "authored_test_clause",
                    "control_id": "control_id",
                    "family": "family",
                    "procedure_type": "procedure_type",
                    "remaining_test_gate": "remaining_test_gate",
                    "requirement_ids": "requirement_ids",
                    "screen_row_sha256": "screen_row_sha256",
                    "current_status": "current_task_status",
                    "current_conclusion": "current_task_conclusion",
                    "targeted_integrated_source_ids": "v8_targeted_source_ids",
                }
                if any(route[left] != req[right] for left, right in comparisons.items()):
                    raise GateError(f"{side}: route/PBC clause join differs: {route['task_id']}")
                if (
                    req["pbc_request_status"] != "DRAFT_NOT_SENT"
                    or req["task_credit"] is not False
                    or req["accepted_nonoccurrence_status"]
                    not in {"NOT_ESTABLISHED", "NO_NONOCCURRENCE_PATH_DEFINED"}
                ):
                    raise GateError(f"{side}: request acceptance or credit changed")
                control_row["unsupported_task_ids"].append(task_key)
                control_row["draft_request_group_ids"].add(req["request_group_id"])
                if req["possible_nonoccurrence_review_candidate"]:
                    control_row["unaccepted_no_event_task_ids"].append(task_key)
            elif route["classification"] == "DESIGN_CONTEXT_ONLY":
                control_row["design_task_ids"].append(task_key)
            else:
                control_row["partial_task_ids"].append(task_key)
            control_row["remaining_gates"][task_key] = route["remaining_test_gate"]
            control_row["route_limits"][task_key] = {
                "source_limit": route["source_limit"],
                "targeted_source_ids": route["targeted_integrated_source_ids"],
                "candidate_or_design_source_ids": route["candidate_or_design_source_ids"],
                "v5_source_limits": route["v5_source_limits"],
                "v6_source_limits": route["v6_source_limits"],
                "v7_source_limits": route["v7_source_limits"],
                "v8_source_limits": route["v8_source_limits"],
                "v9_source_limits": route["v9_source_limits"],
            }
        side_counts[side] = {
            "source_cohorts": 31,
            "native_business_versions": 710,
            "routes": 283,
            "targeted_routes": 170,
            "partial_routes": 132,
            "design_routes": 30,
            "unsupported_exact_clauses": 121,
            "unaccepted_no_event_candidates": 53,
            "p1_tasks_not_started_not_run": 409,
        }
    if set(request_index) != {
        key
        for key, row in route_index.items()
        if row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
    }:
        raise GateError("PBC request coverage differs from unsupported routes")
    groups = pbc.get("request_groups", [])
    if (
        len(groups) != 30
        or len({row["request_group_id"] for row in groups}) != 30
        or any(
            row["request_status"] != "DRAFT_NOT_SENT" or row["task_credit"] is not False
            for row in groups
        )
    ):
        raise GateError("PBC draft group boundary differs")
    for group in groups:
        for side in "AB":
            actual = sorted(
                row["task_id"]
                for row in request_rows
                if row["side"] == side and row["request_group_id"] == group["request_group_id"]
            )
            if actual != sorted(group["task_ids_per_side"][side]):
                raise GateError("PBC group/task membership differs")
    blockers = {}
    for family, controls in sorted(grouped.items()):
        blockers[family] = {}
        for control, item in sorted(controls.items()):
            blockers[family][control] = {
                key: (
                    dict(value)
                    if isinstance(value, Counter)
                    else sorted(value)
                    if isinstance(value, (set, list))
                    else value
                )
                for key, value in item.items()
            }
    return {
        "schema": SCHEMA,
        "as_of": "2026-09-30",
        "purpose": "READ_ONLY_WORKFLOW_DIAGNOSTIC",
        "source_complete": False,
        "fresh_pair_eligible": False,
        "audit_ready": False,
        "audit_task_credit": False,
        "accepted_na_determinations": 0,
        "external_messages_sent": 0,
        "p1_freeze": P1_FREEZE,
        "pins": {
            key: {"scope": scope, "path": path, "sha256": sha}
            for key, (scope, path, sha) in PINS.items()
        },
        "sides": side_counts,
        "source_roster": port["sources"],
        "candidate_source_pins": {side: candidate["sides"][side]["source_pins"] for side in "AB"},
        "request_groups": [
            {
                "request_group_id": group["request_group_id"],
                "control_id": group["control_id"],
                "status": group["request_status"],
                "task_ids_per_side": group["task_ids_per_side"],
                "next_action": group["v8_next_action"],
            }
            for group in groups
        ],
        "blockers_by_family_control": blockers,
        "boundary_limits": {
            "portfolio": port["limits"],
            "candidate": candidate["limits"],
            "route": ledger["limits"],
            "requests": pbc["limits"],
        },
        "readiness_blockers": [
            "Partial selected fictional source roster; complete period populations and "
            "independent evidence are not established.",
            "All 283 documentary/activity routes per side remain partial, design context, or "
            "unsupported, with no task execution or credit.",
            "121 exact authored clauses per side remain unsupported; 30 request groups "
            "remain draft and unsent.",
            "53 possible no-event cases per side lack a qualified nonoccurrence decision; "
            "no blanket N/A acceptance.",
            "The pending addressable docket and open Messy exceptions do not establish "
            "actual applicability, decisions, safeguards, or operating effectiveness.",
            "The frozen P1 pair has 409 NOT_STARTED/NOT_RUN tasks per side; "
            "no fresh pair is eligible.",
        ],
    }


def build(repository: Path, private_repository: Path) -> dict:
    _reject_symlink_chain(private_repository)
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    before, identities = _load_pins(repository, private)
    _assert_review_boundaries(before)
    if frozen._p1_inventory(private) != P1_FREEZE:
        raise GateError("Frozen P1 inventory differs")
    port = portfolio.verify_report(
        private / Path(PINS["v10_portfolio"][1]).parent, repository, private
    )
    candidate = candidates.verify_candidate(
        private / Path(PINS["v10_candidate_a"][1]).parent, repository, private
    )
    ledger = routes.build(repository, private)
    pbc = requests.build(repository, private)
    for name, actual in (
        ("v10_portfolio", port),
        ("v10_candidate_report", candidate),
        ("v9_route", ledger),
        ("pbc_v8", pbc),
    ):
        if actual != before[name]:
            raise GateError(f"{name}: exact builder replay differs")
    result = _assemble(port, candidate, ledger, pbc)
    after, after_ids = _load_pins(repository, private)
    if after != before or after_ids != identities or frozen._p1_inventory(private) != P1_FREEZE:
        raise GateError("Pinned input or frozen P1 changed during gate")
    return result


def markdown(report: dict) -> str:
    lines = [
        "# Fictional audit readiness gate",
        "",
        "**Blocked.** This is a read-only workflow diagnostic for the selected 2027 "
        "fictional sources, not audit readiness or task credit.",
        "",
        "| Per side | Count |",
        "| --- | ---: |",
    ]
    counts = report["sides"]["A"]
    for label, key in (
        ("Selected source cohorts", "source_cohorts"),
        ("Native business versions", "native_business_versions"),
        ("Documentary/activity routes", "routes"),
        ("Targeted source leads", "targeted_routes"),
        ("Partial routes", "partial_routes"),
        ("Design context routes", "design_routes"),
        ("Unsupported exact clauses", "unsupported_exact_clauses"),
        ("Unaccepted no-event candidates", "unaccepted_no_event_candidates"),
        ("Frozen NOT_STARTED/NOT_RUN tasks", "p1_tasks_not_started_not_run"),
    ):
        lines.append(f"| {label} | {counts[key]} |")
    lines += [
        "| Draft, unsent request groups | 30 |",
        "",
        "`source_complete=false`; `fresh_pair_eligible=false`; `audit_ready=false`. "
        "No N/A determination, external request, collection, task credit, Key, grade, "
        "or actual-operation claim is made.",
        "",
        "## Blockers by family",
        "",
        "| Family | Partial | Design | Unsupported | Controls with blockers |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for family, controls in report["blockers_by_family_control"].items():
        totals = Counter()
        for item in controls.values():
            totals.update(item["route_classes"])
        partial = totals["SOURCE_CANDIDATE_PARTIAL"] // 2
        design = totals["DESIGN_CONTEXT_ONLY"] // 2
        unsupported = totals["UNSUPPORTED_EXACT_CLAUSE"] // 2
        lines.append(f"| {family} | {partial} | {design} | {unsupported} | {len(controls)} |")
    lines += ["", "## Gate conditions", ""]
    lines += [f"- {item}" for item in report["readiness_blockers"]]
    lines += [
        "",
        "The JSON contains the full 31-cohort roster, exact candidate source pins, "
        "all draft group memberships, and task-level remaining gates grouped by family "
        "and control. Clean and Messy limitations remain distinct in the pinned source "
        "rows and upstream reports.",
        "",
    ]
    return "\n".join(lines)


def write(repository: Path, private_repository: Path, destination: Path) -> dict:
    destination = Path(destination).absolute()
    _reject_symlink_chain(destination)
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
    _reject_symlink_chain(destination)
    with tempfile.TemporaryDirectory(
        prefix=".readiness-gate-", dir=destination.parent
    ) as temporary:
        stage = Path(temporary)
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
    _reject_symlink_chain(destination)
    if (
        destination.is_symlink()
        or stat.S_IMODE(destination.stat().st_mode) != 0o700
        or stat.S_IMODE(destination.parent.stat().st_mode) != 0o700
        or {p.name for p in destination.iterdir()} != {"REPORT.json", "REPORT.md"}
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
        raise GateError("Gate output differs from pinned replay")
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
