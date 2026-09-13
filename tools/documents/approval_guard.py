"""Read-only protection of existing exact-file approval records; never rebaseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# These revisions contain existing accepted records, not new approvals.
RECORDS = (
    (
        "foundry-field",
        "e71996a5c1fe567b6654ddf8956c2b757ae52ba2",
        "docs/finance/evidence/SH-FIN-HUMAN-001/ACCEPTANCE.json",
    ),
    (
        "visitor-v08",
        "5ed6c8daa3b90cbb30122999fe92b1a36235aab8",
        "geospatial/facilities/visitor/ACCEPTANCE.json",
    ),
    (
        "sacramento-r01",
        "f91d6cbfef943927179aa3160c595028fce87d45",
        "docs/facilities/references/sacramento-hq/r01-approved/MANIFEST.json",
    ),
    ("j2-originals", "8ed187e5dd1b7221fee10265451bf6060a1ac0e6", "assets/brand/manifest.json"),
)


class ApprovalError(ValueError):
    """An accepted record or artifact cannot be verified."""


def git_bytes(root: Path, revision: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"{revision}:{path}"], capture_output=True
    )
    if result.returncode:
        raise ApprovalError(
            f"Missing approval history: git fetch origin {revision}; cannot verify {path}"
        )
    return result.stdout


def projection(kind: str, record: dict) -> dict:
    if kind in {"foundry-field", "visitor-v08"}:
        return record
    if kind == "sacramento-r01":
        return {
            "id": record["id"],
            "status": record["status"],
            "immutable": record["immutable"],
            "files": [
                {k: v for k, v in row.items() if k != "successor_artifacts"}
                for row in record["files"]
            ],
        }
    return {
        "assets": [
            row
            for row in record["assets"]
            if "controlling user-approved source asset" in row.get("canonical_status", "")
        ]
    }


def artifacts(kind: str, path: str, record: dict) -> dict[str, str]:
    if kind == "foundry-field":
        return record["artifacts"]
    if kind == "visitor-v08":
        return {row["path"]: row["sha256"] for row in record["artifacts"].values()}
    if kind == "sacramento-r01":
        return {str(Path(path).parent / row["filename"]): row["sha256"] for row in record["files"]}
    return {row["path"]: row["sha256"] for row in projection(kind, record)["assets"]}


def validate(root: Path = ROOT, records: tuple = RECORDS) -> dict:
    groups = []
    seen = set()
    for kind, revision, path in records:
        original = json.loads(git_bytes(root, revision, path))
        current = json.loads((root / path).read_text())
        if projection(kind, current) != projection(kind, original):
            raise ApprovalError(
                f"Approval record changed: {path}; "
                "preserve accepted record and use an explicitly approved successor"
            )
        expected = artifacts(kind, path, original)
        if not expected:
            raise ApprovalError(f"Empty approval coverage: {path}")
        for relative, checksum in expected.items():
            target = root / relative
            if not target.resolve().is_relative_to(root.resolve()):
                raise ApprovalError(f"Approval path escapes repository: {relative}")
            if relative in seen:
                raise ApprovalError(f"Duplicate approval artifact: {relative}")
            seen.add(relative)
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != checksum:
                raise ApprovalError(f"Approved artifact missing or changed: {relative}")
        # Bind the canonical acceptance prose as well as its JSON record.
        if controlling := original.get("controlling_record"):
            if (root / controlling).read_bytes() != git_bytes(root, revision, controlling):
                raise ApprovalError(f"Controlling acceptance changed: {controlling}")
        groups.append(
            {"group": kind, "record": path, "revision": revision, "artifacts": len(expected)}
        )
    return {
        "status": "PASS",
        "artifact_count": len(seen),
        "groups": groups,
        "scope": "Existing exact-file records only; no new approval or visual quality assessment",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        print(json.dumps(validate(args.root), indent=2))
    except (ApprovalError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"FAIL approval protection: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
