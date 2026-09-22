"""Compose an explicitly scoped edition over existing outputs, without new company tables."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath


class EditionError(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def member_path(value: str) -> PurePosixPath:
    p = PurePosixPath(value)
    if not value or p.is_absolute() or ".." in p.parts or str(p) != value or "\\" in value:
        raise EditionError("Noncanonical member path")
    return p


def timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise EditionError("Timezone required")
    return result


def validate_contract(contract: dict) -> None:
    if contract.get("schema_version") != "1.0.0":
        raise EditionError("Unsupported edition contract")
    if contract.get("status") not in {"REVIEW_CANDIDATE", "ACCEPTED_SCOPED_EDITION"}:
        raise EditionError("Explicit acceptance status required")
    if not contract.get("limitations") or not contract.get("allowed_joins"):
        raise EditionError("Limitations and allowed joins must be explicit")
    seen = set()
    for item in contract["components"]:
        if item["id"] in seen:
            raise EditionError("Duplicate component population")
        seen.add(item["id"])
        if item["fact_status"] not in {
            "ACCEPTED_SOURCE",
            "MIXED_SOURCE_ARCHIVE",
            "CONDITIONAL_FORECAST",
            "NEWLY_AUTHORED_SYNTHETIC_HISTORY",
            "REFERENCE_SOFTWARE_EXERCISE",
            "HISTORICAL_RELEASE",
        }:
            raise EditionError("Unknown fact role")
        if item["access_scope"] != "PUBLIC_SYNTHETIC":
            raise EditionError("Only explicitly public synthetic inputs may be packaged")
        if not item["population_definition"] or not item["units"] or not item["legal_entities"]:
            raise EditionError("Population, unit and entity scope required")
        timestamp(item["available_at"])
        if item.get("claims_known_on") and timestamp(item["available_at"]) > timestamp(
            item["claims_known_on"]
        ):
            raise EditionError("Future evidence promoted into an earlier known-on state")
        members = item["members"]
        if not members or len(members) != len({m["path"] for m in members}):
            raise EditionError("Empty or duplicate component members")
        for m in members:
            member_path(m["path"])
            if len(m["sha256"]) != 64:
                raise EditionError("Exact source pin required")
    if seen != set(contract["required_components"]):
        raise EditionError("Omitted or additional declared component population")
    from .acceptance import validate

    validate(contract)


def build(root: Path, contract_path: Path, destination: Path) -> dict:
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    validate_contract(contract)
    root = root.resolve()
    payloads = {}
    for component in contract["components"]:
        for member in component["members"]:
            path = root / member["path"]
            if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
                raise EditionError("Missing, linked or escaping source")
            data = path.read_bytes()
            if sha(data) != member["sha256"]:
                raise EditionError(f"Stale source/derivative pin: {member['path']}")
            if member["path"] in payloads:
                raise EditionError(
                    "A physical member must belong to one component; use relationships"
                )
            payloads[member["path"]] = data
    if destination.exists():
        raise EditionError("New immutable edition destination required")
    # Validate every input before writing the new package. No deletion/replacement mode.
    revision = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    if contract.get("source_commit_required", revision) != revision:
        raise EditionError("Contract pins another source revision")
    dirty = bool(
        subprocess.check_output(
            ["git", "-C", str(root), "status", "--porcelain"], text=True
        ).strip()
    )
    if contract["status"] == "ACCEPTED_SCOPED_EDITION" and dirty:
        raise EditionError("Accepted edition requires a clean source checkout")
    if contract["status"] == "ACCEPTED_SCOPED_EDITION":
        recorded_at = timestamp(
            subprocess.check_output(
                ["git", "-C", str(root), "show", "-s", "--format=%cI", "HEAD"], text=True
            ).strip()
        )
        if any(timestamp(c["available_at"]) < recorded_at for c in contract["components"]):
            raise EditionError("Accepted availability precedes source commit recording")
        from .acceptance import verify_live

        verify_live(contract, root)
    receipt = {
        "schema_version": "1.0.0",
        "edition_id": contract["edition_id"],
        "version": contract["version"],
        "status": contract["status"],
        "source_commit": revision,
        "dirty_source_checkout": dirty,
        "contract_sha256": sha(contract_bytes),
        "members": [
            {"path": p, "bytes": len(b), "sha256": sha(b)} for p, b in sorted(payloads.items())
        ],
        "component_count": len(contract["components"]),
        "scope": contract["scope"],
        "limitations": contract["limitations"],
    }
    destination.mkdir(parents=True)
    for path, data in payloads.items():
        target = destination / "content" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (destination / "CONTRACT.json").write_bytes(contract_bytes)
    (destination / "MANIFEST.json").write_bytes(encoded(receipt))
    verify(destination)
    return receipt


def verify(directory: Path) -> dict:
    if directory.is_symlink() or any(p.is_symlink() for p in directory.rglob("*")):
        raise EditionError("Linked edition member")
    manifest = json.loads((directory / "MANIFEST.json").read_bytes())
    contract_bytes = (directory / "CONTRACT.json").read_bytes()
    if sha(contract_bytes) != manifest["contract_sha256"]:
        raise EditionError("Contract changed")
    contract = json.loads(contract_bytes)
    validate_contract(contract)
    if (
        contract.get("source_commit_required", manifest["source_commit"])
        != manifest["source_commit"]
    ):
        raise EditionError("Receipt source revision contradicts contract")
    for key in ("edition_id", "version", "status", "scope", "limitations"):
        if manifest[key] != contract[key]:
            raise EditionError("Receipt metadata contradicts contract")
    if manifest["component_count"] != len(contract["components"]):
        raise EditionError("Receipt component count contradicts contract")
    if manifest["status"] == "ACCEPTED_SCOPED_EDITION" and manifest["dirty_source_checkout"]:
        raise EditionError("Accepted receipt has dirty source provenance")
    declared = {m["path"]: m["sha256"] for c in contract["components"] for m in c["members"]}
    inventoried = {m["path"]: m["sha256"] for m in manifest["members"]}
    if len(inventoried) != len(manifest["members"]) or declared != inventoried:
        raise EditionError("Manifest population differs from source contract")
    actual = {
        str(p.relative_to(directory / "content"))
        for p in (directory / "content").rglob("*")
        if p.is_file()
    }
    expected_files = {"CONTRACT.json", "MANIFEST.json"} | {"content/" + p for p in inventoried}
    all_files = {str(p.relative_to(directory)) for p in directory.rglob("*") if p.is_file()}
    if all_files != expected_files:
        raise EditionError("Missing or unmanifested edition member")
    if actual != set(inventoried):
        raise EditionError("Missing or unmanifested payload")
    for member in manifest["members"]:
        member_path(member["path"])
        p = directory / "content" / member["path"]
        if p.is_symlink() or not p.resolve().is_relative_to(directory.resolve()):
            raise EditionError("Linked payload")
        data = p.read_bytes()
        if len(data) != member["bytes"] or sha(data) != member["sha256"]:
            raise EditionError("Payload changed")
    from .acceptance import verify_packaged_scope

    verify_packaged_scope(contract, directory / "content")
    return {"result": "PASS", "members": len(actual), "components": len(contract["components"])}


def archive(directory: Path, output: Path) -> None:
    verify(directory)
    if output.exists():
        raise EditionError("New package filename required")
    manifest = json.loads((directory / "MANIFEST.json").read_bytes())
    selected = ["CONTRACT.json", "MANIFEST.json"] + [
        "content/" + m["path"] for m in manifest["members"]
    ]
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for relative in sorted(selected):
            info = zipfile.ZipInfo(relative, (2026, 9, 15, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, (directory / relative).read_bytes())
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{sha(output.read_bytes())}  {output.name}\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--zip", type=Path)
    args = parser.parse_args()
    result = verify(args.output) if args.verify else build(args.root, args.contract, args.output)
    if args.zip:
        archive(args.output, args.zip)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
