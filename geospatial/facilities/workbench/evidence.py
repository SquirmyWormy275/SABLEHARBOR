"""Evidence candidates are review objects, never a canonical write API."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import subprocess

COVERAGE = "geospatial/facilities/coverage/COVERAGE_MATRIX.json"
CLAIM_FIELDS = {
    "parcel": {"geometry", "precision", "fictionality", "status"},
    "tenure": {"tenure", "status"},
    "occupancy": {
        "occupancy_start",
        "occupancy_end",
        "actual_occupancy",
        "actual_floor_count",
        "status",
    },
    "workforce": {
        "current_named_employees",
        "authorized_positions",
        "vacancies",
        "shift_population",
        "maximum_concurrent_attendance",
        "status",
    },
    "engineering": {"geometry", "engineering_reference", "precision", "status"},
}
PRECISIONS = {
    "UNKNOWN",
    "UNLOCATED",
    "REGION",
    "CITY_OR_DISTRICT",
    "STUDY_AREA",
    "SYNTHETIC_METRIC",
    "PARCEL",
    "SURVEYED",
}
FICTIONALITIES = {
    "UNKNOWN",
    "REAL",
    "FICTIONAL_IN_REAL_GEOGRAPHY",
    "ACCEPTED_SYNTHETIC",
    "ILLUSTRATIVE",
}


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def canonical_hash(value: object) -> str:
    return digest(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    )


def safe_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("source path must be repository-relative")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or ".." in Path(relative).parts:
        raise ValueError("source path escapes repository")
    return path


def git(root: Path, *args: str) -> str:
    return (
        subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.DEVNULL)
        .decode()
        .strip()
    )


def baseline(root: Path) -> dict:
    raw = (root / COVERAGE).read_bytes()
    matrix = json.loads(raw)
    for name, sha in matrix["input_sha256"].items():
        if digest(safe_path(root, name).read_bytes()) != sha:
            raise ValueError(f"stale coverage input: {name}")
    return {"coverage_sha256": digest(raw), "source_main_sha": matrix["source_main_sha"]}


def build_evidence_queue(root: Path) -> dict:
    """All coverage IDs remain addressable, with explicit unresolved field lists."""
    bound = baseline(root)
    matrix = json.loads((root / COVERAGE).read_text())
    records = []
    for row in matrix["records"]:
        missing = [
            k
            for k in ("occupancy_start", "occupancy_end", "actual_occupancy", "actual_floor_count")
            if row.get(k) is None
        ]
        if row.get("precision", "").upper() in {"UNKNOWN", "UNLOCATED", "CITY_OR_DISTRICT"}:
            missing.append("supported_geometry")
        if "unknown" in row.get("tenure", "").lower():
            missing.append("tenure")
        records.append(
            {
                "scope_id": row["id"],
                "name": row["name"],
                "status": row["status"],
                "classification": row["classification"],
                "unresolved_fields": missing,
                "disposition": row["reason"],
                "provenance": row["provenance"],
                "issues": [row[k] for k in ("geometry_issue", "detail_issue") if row.get(k)],
                "claim_required": False,
            }
        )
    return {
        "schema_version": "1.0.0",
        "state": "REVIEW_QUEUE_NOT_CANON",
        "baseline": bound,
        "records": records,
    }


def submission_template(root: Path) -> dict:
    return {
        "evidence_id": "",
        "baseline": baseline(root),
        "scope_ids": [],
        "claim_type": "occupancy",
        "evidence_kind": "SOURCE_EVIDENCE",
        "source": {"path": "", "sha256": "", "locator": ""},
        "effective_interval": {"start": None, "end": None},
        "precision": "UNKNOWN",
        "fictionality": "UNKNOWN",
        "proposed_changes": [],
        "reviewer": "",
        "decision": "PENDING",
        "decision_provenance": None,
    }


def accepted_decision(root: Path, record: dict) -> bool:
    """Require an exact binding in current accepted canon, not a self-asserted flag."""
    p = record.get("decision_provenance")
    if not isinstance(p, dict) or set(p) != {"path", "sha256", "commit"}:
        return False
    name = p["path"]
    if not isinstance(name, str) or not name.startswith("docs/canon/") or not name.endswith(".md"):
        return False
    commit = p["commit"]
    if not isinstance(commit, str) or not re.fullmatch("[0-9a-f]{40}", commit):
        return False
    try:
        safe_path(root, name)
        git(root, "merge-base", "--is-ancestor", commit, "refs/remotes/origin/main")
        raw = git(root, "show", f"refs/remotes/origin/main:{name}")
        historical = git(root, "show", f"{commit}:{name}")
        # Hash actual blobs, preserving terminal newlines.
        blob = subprocess.check_output(
            ["git", "-C", str(root), "show", f"refs/remotes/origin/main:{name}"]
        )
        if raw != historical or digest(blob) != p["sha256"]:
            return False
        binding = {
            "evidence_id": record["evidence_id"],
            "scope_ids": record["scope_ids"],
            "claim_type": record["claim_type"],
            "source": record["source"],
            "effective_interval": record["effective_interval"],
            "precision": record["precision"],
            "fictionality": record["fictionality"],
            "evidence_kind": record["evidence_kind"],
            "proposed_changes": record["proposed_changes"],
        }
        blocks = re.findall(r"```facility-evidence-decision\s*\n(.*?)\n```", raw, re.S)
        return any(
            json.loads(b)
            == {
                "decision": "ACCEPTED",
                "reviewer": record["reviewer"],
                "claim_sha256": canonical_hash(binding),
            }
            for b in blocks
        )
    except (ValueError, OSError, subprocess.CalledProcessError, KeyError):
        return False


def validate_submission(root: Path, record: dict) -> list[str]:
    errors = []
    try:
        expected = submission_template(root)
        if not isinstance(record, dict) or set(record) != set(expected):
            return ["submission fields missing or unknown"]
        if record["baseline"] != expected["baseline"]:
            errors.append("stale baseline")
        if not isinstance(record["evidence_id"], str) or not re.fullmatch(
            r"SH-EVID-[A-Z0-9-]+", record["evidence_id"]
        ):
            errors.append("invalid evidence_id")
        ids = record["scope_ids"]
        known = {r["id"] for r in json.loads((root / COVERAGE).read_text())["records"]}
        if (
            not isinstance(ids, list)
            or not ids
            or any(not isinstance(i, str) or i not in known for i in ids)
            or len(ids) != len(set(ids))
        ):
            errors.append("unknown, empty or duplicate scope IDs")
        claim = record["claim_type"]
        if claim not in CLAIM_FIELDS:
            errors.append("unsupported claim type")
        if record["evidence_kind"] not in {"SOURCE_EVIDENCE", "PLANNING_ASSUMPTION"}:
            errors.append("invalid evidence kind")
        source = record["source"]
        if (
            not isinstance(source, dict)
            or set(source) != {"path", "sha256", "locator"}
            or not isinstance(source["locator"], str)
            or not source["locator"].strip()
        ):
            errors.append("source reference and locator required")
        elif digest(safe_path(root, source["path"]).read_bytes()) != source["sha256"]:
            errors.append("stale evidence source hash")
        interval = record["effective_interval"]
        if not isinstance(interval, dict) or set(interval) != {"start", "end"}:
            errors.append("invalid effective interval")
        else:
            for value in interval.values():
                if value is not None:
                    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                        raise ValueError("invalid effective date")
                    date.fromisoformat(value)
            if interval["start"] and interval["end"] and interval["end"] < interval["start"]:
                errors.append("reversed effective interval")
        if record["precision"] not in PRECISIONS or record["fictionality"] not in FICTIONALITIES:
            errors.append("unsupported precision or fictionality")
        changes = record["proposed_changes"]
        if not isinstance(changes, list) or not changes:
            errors.append("explicit proposed changes required")
        else:
            pairs = []
            for change in changes:
                if not isinstance(change, dict) or set(change) != {
                    "scope_id",
                    "field",
                    "before",
                    "after",
                }:
                    errors.append("invalid proposed change fields")
                    continue
                if change["scope_id"] not in ids or change["field"] not in CLAIM_FIELDS.get(
                    claim, set()
                ):
                    errors.append("change outside scope or claim fields")
                pairs.append((change["scope_id"], change["field"]))
                if change["before"] == change["after"]:
                    errors.append("change has no effect")
                rows = {r["id"]: r for r in json.loads((root / COVERAGE).read_text())["records"]}
                if change["before"] != rows.get(change["scope_id"], {}).get(change["field"]):
                    errors.append("change before value differs from baseline")
                if change["field"].endswith(("_start", "_end")) and change["after"] is not None:
                    date.fromisoformat(change["after"])
                if change["field"] in {
                    "actual_occupancy",
                    "actual_floor_count",
                    "current_named_employees",
                    "authorized_positions",
                    "vacancies",
                    "shift_population",
                    "maximum_concurrent_attendance",
                } and (type(change["after"]) is not int or change["after"] < 0):
                    errors.append("population/count must be a nonnegative integer")
                if change["field"] == "status" and not accepted_decision(root, record):
                    errors.append("unsupported status promotion: accepted decision required")
            if len(pairs) != len(set(pairs)):
                errors.append("duplicate field change")
        if record["decision"] not in {
            "PENDING",
            "REJECTED",
            "REQUEST_CHANGES",
            "ACCEPTED_CANDIDATE",
        }:
            errors.append("invalid review decision")
        if record["decision"] != "PENDING" and (
            not isinstance(record["reviewer"], str) or not record["reviewer"].strip()
        ):
            errors.append("reviewer required")
        if record["decision"] == "ACCEPTED_CANDIDATE" and not accepted_decision(root, record):
            errors.append("accepted candidate requires current repository decision provenance")
        if (
            record["evidence_kind"] == "PLANNING_ASSUMPTION"
            and record["decision"] == "ACCEPTED_CANDIDATE"
        ):
            errors.append("planning assumptions cannot be promoted as source evidence")
        canonical_hash(record)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        errors.append(f"invalid or unavailable evidence: {exc}")
    return errors


def export_candidate(root: Path, record: dict, output: Path) -> None:
    errors = validate_submission(root, record)
    if errors:
        raise ValueError("; ".join(errors))
    # No writes anywhere inside the canonical repository, including symlink routes.
    if output.resolve().is_relative_to(root.resolve()):
        raise ValueError("candidate output must be outside repository")
    payload = {
        "state": "REVIEW_CANDIDATE_NOT_CANON",
        "submission_sha256": canonical_hash(record),
        "submission": record,
    }
    with output.open("x") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=["queue", "template", "validate", "stage", "review", "export"]
    )
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action in {"queue", "template"}:
        print(
            json.dumps(
                build_evidence_queue(args.root)
                if args.action == "queue"
                else submission_template(args.root),
                indent=2,
            )
        )
        return
    if not args.input:
        parser.error("--input is required")
    record = json.loads(args.input.read_text())
    errors = validate_submission(args.root, record)
    if errors:
        raise SystemExit("\n".join(errors))
    if args.action in {"stage", "export"}:
        if not args.output:
            parser.error("--output is required")
        export_candidate(args.root, record, args.output)
    else:
        print(
            json.dumps(
                {"validation": "PASS", "decision": record["decision"], "canon_modified": False}
            )
        )


if __name__ == "__main__":
    main()
