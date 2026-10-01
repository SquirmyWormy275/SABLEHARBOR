"""Read-only, historical procedure-method crosswalk for the frozen P1 pair.

The old packet is a method reference. No old evidence, workpaper result,
conclusion, instructor Key, or task state is applied to the new engagements.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import stat
from collections import Counter
from pathlib import Path

from .documentary_283_route_reconciliation_v6 import _p1_inventory

SCHEMA = "SH_PROCEDURE_METHOD_REUSE_CROSSWALK_V1"
BASE = "enterprise/generated/audit-suite"
OLD = (
    f"{BASE}/acceptance-audit-2026-09-22/"
    "integrated-review-packet-refresh-run-post-original-journals-a1939-b2066-v4"
)
OLD_REVIEW = f"{OLD}-independent-v1/REVIEW.json"
P1 = f"{BASE}/acceptance-audit-2026-09-22/aq06-aq07-integrated-full-portfolio-bootstrap-run-v1"
ROUTE = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V16_2026-10-01.json"
ROUTE_REVIEW = (
    f"{BASE}/documentary-283-route-reconciliation-v16-2026-10-01/"
    "independent-review-main-v1/REVIEW.json"
)
P1_FREEZE = {
    "file_count": 538,
    "inventory_sha256": "f266ef682b502b3b093170f8a7b64fcf5cbab722d5c8ddf6715a63c0e535360f",
}
PINS = {
    "old_packet": (
        "private",
        f"{OLD}/TASK-DISPOSITIONS.json",
        "e7e723d989b85cfbd60ebe65965f7acda4674d71602c6a0153fe8877159048a7",
    ),
    "old_manifest": (
        "private",
        f"{OLD}/MANIFEST.json",
        "84bde92c34462710d596c802b5952d4c94c926a31a4e4a0090fc387186cb70a3",
    ),
    "old_review": (
        "private",
        OLD_REVIEW,
        "a7ae5c1afed5c47d132eb1c41d8e16574b59767dffb817e3812ecda9f3c50f17",
    ),
    "p1_a_db": (
        "private",
        f"{P1}/audit/A/audit-state/engagements.sqlite3",
        "d3fe127988d5c5f785d0e6849b388a66a8800b1c4645dab8b7b1d59dcdcfabc7",
    ),
    "p1_b_db": (
        "private",
        f"{P1}/audit/B/audit-state/engagements.sqlite3",
        "30bb2b33895a3a49437ca7d94628e239da3e0c4da98c7328ba37791baa584004",
    ),
    "route_ledger": (
        "repo",
        ROUTE,
        "cd3b55409e9e0112b49d060cfbbacf329660422d0c4e1b2002ec220af5bad5a3",
    ),
    "route_review": (
        "private",
        ROUTE_REVIEW,
        "138bc8e7cd5e701d0507e4dcb6228364c3406aa097d12d14d9753c456ae60b34",
    ),
}
KNOWN_SCOPE_DRIFT = {"TASK-GATE-SERVICE-FACTS", "TASK-GATE-QUALIFIED-REVIEW"}
NONTRANSFERABLE = [
    "Historical source originals, evidence identifiers and custody remain bound "
    "to the old workrooms.",
    "Historical workpaper and sample observations, results, conclusions and "
    "task states do not transfer.",
    "The old instructor Key or grading cannot be used as a fresh-period expected result.",
    "Each new-pair procedure requires fresh company-native source collection, "
    "population and sample definition, execution, exception disposition and "
    "independent review.",
    "A selected route lead is neither a complete population nor clause "
    "satisfaction or audit credit.",
]


class CrosswalkError(RuntimeError):
    """An input pin, task identity, or no-credit boundary differs."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_pinned(repo: Path, private: Path, name: str) -> bytes:
    scope, relative, digest = PINS[name]
    root = repo if scope == "repo" else private
    path = root / relative
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise CrosswalkError(f"Input alias forbidden: {name}")
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise CrosswalkError(f"Ordinary single-link input required: {name}")
    if scope == "private" and stat.S_IMODE(before.st_mode) != 0o600:
        raise CrosswalkError(f"Private input mode differs: {name}")
    raw = path.read_bytes()
    after = path.stat()

    def identity(s):
        return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_mode, s.st_nlink)

    if _sha(raw) != digest or identity(before) != identity(after):
        raise CrosswalkError(f"Input byte/identity pin differs: {name}")
    return raw


def _p1_tasks(db_path: Path) -> list[dict]:
    connection = sqlite3.connect(db_path.as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        rows = connection.execute("SELECT state FROM engagements").fetchall()
        if len(rows) != 1:
            raise CrosswalkError("P1 engagement count differs")
        state = json.loads(rows[0][0])
        # The frozen bootstrap contains preparation objects; only task state
        # and the whole-run inventory establish the no-credit boundary here.
        return state["tasks"]
    finally:
        connection.close()


def _by_id(rows: list[dict], source: str) -> dict[str, dict]:
    indexed = {row["id"]: row for row in rows}
    if len(rows) != len(indexed) or len(indexed) != 409:
        raise CrosswalkError(f"{source} task count/identity differs")
    return indexed


def _compare_side(
    old_rows: list[dict], new_tasks: list[dict], routes: list[dict], side: str
) -> tuple[list[dict], dict]:
    old = _by_id([row["task"] for row in old_rows], f"old {side}")
    current = _by_id(new_tasks, f"P1 {side}")
    if old.keys() != current.keys():
        raise CrosswalkError(
            f"{side} task ID drift: old-only={sorted(old.keys() - current.keys())}, "
            f"new-only={sorted(current.keys() - old.keys())}"
        )
    route_map = {row["task_id"]: row for row in routes}
    if (
        len(routes) != len(route_map)
        or len(routes) != 283
        or not route_map.keys() <= current.keys()
    ):
        raise CrosswalkError(f"{side} route count/identity differs")
    old_packet = {row["task"]["id"]: row for row in old_rows}
    result = []
    for task_id in sorted(current):
        prior, new = old[task_id], current[task_id]
        for field in ("kind", "test", "title", "control_id", "boundary_id"):
            if prior.get(field) != new.get(field):
                raise CrosswalkError(f"{side} task method identity drift: {task_id}/{field}")
        old_scope, new_scope = prior.get("scope", {}), new.get("scope", {})
        drift = {
            key: {"old": old_scope.get(key), "p1": new_scope.get(key)}
            for key in sorted(old_scope.keys() | new_scope.keys())
            if old_scope.get(key) != new_scope.get(key)
        }
        if drift and not (
            task_id in KNOWN_SCOPE_DRIFT
            and drift == {"fieldwork_start": {"old": "2027-01-01", "p1": "2027-12-31"}}
        ):
            raise CrosswalkError(f"{side} unrecognized scope drift: {task_id}/{drift}")
        if new.get("status") != "NOT_STARTED" or new.get("conclusion") != "NOT_RUN":
            raise CrosswalkError(f"{side} P1 task no longer unrun: {task_id}")
        source = old_packet[task_id]
        method = source.get("authored_procedure")
        if method is not None and (not isinstance(method, str) or not method.strip()):
            raise CrosswalkError(f"{side} malformed authored method: {task_id}")
        work = source.get("linked_workpaper_versions", [])
        sample = source.get("linked_sample_executions", [])
        route = route_map.get(task_id)
        result.append(
            {
                "side": side,
                "task_id": task_id,
                "kind": new["kind"],
                "current_title": new["title"],
                "current_test_clause": new.get("test"),
                "prior_status_for_context_only": prior["status"],
                "prior_conclusion_for_context_only": prior["conclusion"],
                "p1_status": "NOT_STARTED",
                "p1_conclusion": "NOT_RUN",
                "scope_drift": drift,
                "reuse_class": "SCOPE_REVIEW_REQUIRED"
                if drift
                else "AUTHORED_METHOD_CANDIDATE"
                if method
                else "TEST_CLAUSE_ONLY",
                "prior_authored_method_text": method,
                "prior_workpaper_locators_only": [
                    {"id": x["id"], "version": x["version"], "sha256": x["sha256"]} for x in work
                ],
                "prior_sample_locators_only": [
                    {"id": x["id"], "sha256": x["sha256"]} for x in sample
                ],
                "prior_authored_gap_count": len(source.get("linked_authored_task_gaps", [])),
                "current_route_classification": route["classification"] if route else None,
                "current_route_selected_source_count": len(
                    route.get("targeted_integrated_source_ids", [])
                )
                if route
                else 0,
                "task_credit": False,
            }
        )
    counts = {
        "tasks": len(result),
        "prior_status": dict(
            sorted(Counter(x["prior_status_for_context_only"] for x in result).items())
        ),
        "prior_conclusion": dict(
            sorted(Counter(x["prior_conclusion_for_context_only"] for x in result).items())
        ),
        "reuse_class": dict(sorted(Counter(x["reuse_class"] for x in result).items())),
        "authored_method_rows": sum(x["prior_authored_method_text"] is not None for x in result),
        "workpaper_linked_rows": sum(bool(x["prior_workpaper_locators_only"]) for x in result),
        "workpaper_links": sum(len(x["prior_workpaper_locators_only"]) for x in result),
        "sample_linked_rows": sum(bool(x["prior_sample_locators_only"]) for x in result),
        "sample_links": sum(len(x["prior_sample_locators_only"]) for x in result),
        "authored_gap_linked_rows": sum(bool(x["prior_authored_gap_count"]) for x in result),
        "route_rows": len(route_map),
        "scope_drift_task_ids": [x["task_id"] for x in result if x["scope_drift"]],
        "p1_unrun": sum(
            x["p1_status"] == "NOT_STARTED" and x["p1_conclusion"] == "NOT_RUN" for x in result
        ),
    }
    return result, counts


def build(repository: Path, private: Path) -> dict:
    repository, private = repository.resolve(), private.resolve()
    raw = {name: _read_pinned(repository, private, name) for name in PINS}
    packet = json.loads(raw["old_packet"])
    manifest = json.loads(raw["old_manifest"])
    review = json.loads(raw["old_review"])
    route = json.loads(raw["route_ledger"])
    route_review = json.loads(raw["route_review"])
    if (
        manifest.get("files", {}).get("TASK-DISPOSITIONS.json") != PINS["old_packet"][2]
        or review.get("manifest_sha256") != PINS["old_manifest"][2]
        or review.get("status") != "PASS_INDEPENDENT_PRIVATE_SOURCE_REBASED_PACKET_V4"
        or review.get("task_instances_covered_by_prior_independent_review") != 818
        or review.get("task_or_grade_credit") is not False
    ):
        raise CrosswalkError("Old packet/review relationship differs")
    if (
        route_review.get("output_sha256", {}).get("LEDGER.json") != PINS["route_ledger"][2]
        or route_review.get("verdict") != "PASS_MAIN_SELECTED_GOV_LEAD_NO_AUDIT_CREDIT"
        or route_review.get("audit_task_credit") is not False
        or route_review.get("source_complete") is not False
        or route.get("p1_freeze") != P1_FREEZE
        or route.get("active_pair_mutated") is not False
        or route.get("audit_task_credit") is not False
        or route.get("active_p1_tasks")
        != {
            side: {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"}
            for side in "AB"
        }
    ):
        raise CrosswalkError("Current route/review boundary differs")
    inventory_before = _p1_inventory(private)
    if inventory_before != P1_FREEZE:
        raise CrosswalkError("Frozen P1 inventory differs")
    profiles = {"A": "full-integrated-a-v1", "B": "full-integrated-b-v1"}
    if packet.get("task_instances") != 818 or len(packet.get("rows", [])) != 818:
        raise CrosswalkError("Old packet count differs")
    output_rows, summary = [], {}
    side_sets = []
    for side, profile in profiles.items():
        old_rows = [x for x in packet["rows"] if x["profile"] == profile]
        new_tasks = _p1_tasks(private / PINS[f"p1_{side.lower()}_db"][1])
        route_rows = [x for x in route["rows"] if x["side"] == side]
        rows, counts = _compare_side(old_rows, new_tasks, route_rows, side)
        output_rows.extend(rows)
        summary[side] = counts
        side_sets.append({x["task_id"] for x in rows})
    if side_sets[0] != side_sets[1] or sum(len(x) for x in side_sets) != 818:
        raise CrosswalkError("Cross-side task ID drift")
    if _p1_inventory(private) != inventory_before:
        raise CrosswalkError("P1 changed during read")
    return {
        "schema": SCHEMA,
        "as_of": "2026-10-01",
        "classification": "HISTORICAL_METHOD_REFERENCE_ONLY",
        "pins": {
            name: {"scope": scope, "path": path, "sha256": sha}
            for name, (scope, path, sha) in PINS.items()
        },
        "p1_freeze": P1_FREEZE,
        "summary": summary,
        "rows": output_rows,
        "nontransferable": NONTRANSFERABLE,
        "fresh_pair_created": False,
        "audit_task_credit": False,
        "audit_write": False,
        "instructor_key_migrated": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or output.is_symlink():
        raise CrosswalkError("Output already exists")
    report = build(args.repository, args.private_root)
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(output.parent, 0o700)
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(report, stream, sort_keys=True, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
