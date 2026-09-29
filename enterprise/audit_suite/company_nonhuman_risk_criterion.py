"""Exact prospective local simulation criterion; never enterprise risk acceptance."""

from pathlib import Path

from .company_backup_runtime import database, exact_pin, native, private, require
from .company_store import _time
from .inference import _json as decode
from .operating_source_bridge import encoded, sha

FIELDS = ("company", "branch", "system", "record", "version", "sha256")
MAX_CONTENT = 32768
MAX_METADATA = 16384
SYSTEM = "local_nonhuman_risk_decisions"


def resolve(dependency, *, scope, plan, author, reviewer, as_of):
    require(
        isinstance(dependency, dict) and set(dependency) == {"root", "native", "metadata_sha256"},
        "Exact local criterion dependency required",
    )
    require(isinstance(dependency["root"], str), "Typed criterion root required")
    root = private(Path(dependency["root"]), True)
    require(
        str(root) == dependency["root"] and root.is_absolute(),
        "Exact private criterion root required",
    )
    ref = dependency["native"]
    exact_pin(ref)
    require(
        ref["company"] == plan["company_id"]
        and ref["branch"] == plan["branch_id"]
        and ref["system"] == SYSTEM,
        "Criterion company/branch/system differs",
    )
    pin = dependency["metadata_sha256"]
    require(
        isinstance(pin, str) and len(pin) == 64 and all(c in "0123456789abcdef" for c in pin),
        "Exact criterion metadata digest required",
    )
    where = " AND ".join(k + "=?" for k in FIELDS[:-1])
    metadata = (
        "company",
        "branch",
        "system",
        "record",
        "version",
        "sha256",
        "event_at",
        "available_at",
        "imported_at",
        "origin",
        "provenance",
        "command_id",
        "input_digest",
    )
    expression = "+".join("COALESCE(length(CAST(" + k + " AS BLOB)),0)" for k in metadata)
    with database(root) as db:
        sizes = db.execute(
            "SELECT length(content)," + expression + " FROM versions WHERE " + where,
            tuple(ref[k] for k in FIELDS[:-1]),
        ).fetchone()
        require(
            sizes is not None
            and type(sizes[0]) is int
            and sizes[0] <= MAX_CONTENT
            and type(sizes[1]) is int
            and sizes[1] <= MAX_METADATA,
            "Bounded criterion content and metadata required",
        )
        owner = db.execute(
            "SELECT owner FROM systems WHERE company=? AND branch=? AND system=? AND owner=?",
            (ref["company"], ref["branch"], ref["system"], author),
        ).fetchone()
        require(owner is not None, "Criterion registered author custody differs")
        row = dict(native(db, ref, as_of))
    require(row["origin"] == "AUTHORED_TRAINING_SOURCE", "Authored local criterion origin required")
    raw = row.pop("content")
    require(sha(encoded(row)) == pin, "Criterion native metadata changed")
    body = decode(raw)
    keys = {
        "format",
        "status",
        "scope",
        "author_id",
        "reviewer_id",
        "approved_at",
        "effective_from",
        "effective_to_exclusive",
        "storage",
        "rights",
        "rotation_rules",
        "review_rules",
        "rationale",
    }
    require(isinstance(body, dict) and set(body) == keys, "Exact local criterion schema required")
    require(
        body["format"] == "LOCAL_NONHUMAN_RISK_CRITERION_V1"
        and body["status"] == "LOCAL_SIMULATION_RULE_APPROVED",
        "Approved local simulation rule required",
    )
    require(
        encoded(body["scope"]) == encoded(scope), "Criterion exact subject/workload scope differs"
    )
    require(
        body["author_id"] == author and body["reviewer_id"] == reviewer and author != reviewer,
        "Distinct scoped criterion author/reviewer required",
    )
    for key in ["approved_at", "effective_from", "effective_to_exclusive"]:
        require(
            isinstance(body[key], str) and _time(body[key]) == body[key],
            "Canonical criterion time required",
        )
    require(
        row["event_at"] == body["approved_at"]
        and row["event_at"] <= row["available_at"] <= as_of
        and body["approved_at"] <= body["effective_from"] <= plan["period_start"]
        and body["effective_to_exclusive"] >= plan["period_end_exclusive"],
        "Criterion approval/availability/effective chronology differs",
    )
    require(
        body["storage"] == "INERT_NATIVE_COPY_NO_SECRET_MATERIAL"
        and encoded(body["rights"])
        == encoded(
            [
                {"action": "READ", "object_id": scope["dataset_id"]},
                {"action": "WRITE", "object_id": scope["target_id"]},
            ]
        ),
        "Exact local storage and rights required",
    )
    for key, prefix in [("rotation_rules", "ROTATION-"), ("review_rules", "REVIEW-")]:
        expected = [
            {
                k: s[k]
                for k in ["id", "due_at", "window_start", "window_end_exclusive", "depends_on"]
            }
            for s in plan["schedule"]
            if s["id"].startswith(prefix)
        ]
        require(
            expected and encoded(body[key]) == encoded(expected),
            "Criterion declared cadence rules differ",
        )
    require(
        isinstance(body["rationale"], str)
        and bool(body["rationale"].strip())
        and len(body["rationale"]) <= 2000,
        "Bounded authored criterion rationale required",
    )
    return {
        "dependency": dependency,
        "criterion": body,
        "qualification": "APPROVED_LOCAL_SIMULATION_RULE_ONLY_NOT_ENTERPRISE_ACCEPTANCE",
    }
