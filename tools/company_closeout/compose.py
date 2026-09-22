"""Pin the declared company source snapshot and existing generated packages for inspection."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from .edition import EditionError, encoded, sha, timestamp, validate_contract

ENTITIES = ["SHI", "SHIH", "PS", "RWH", "ARU", "BST"]
UNITS = [
    "foundry-field",
    "atlas-meridian",
    "advisory",
    "willow",
    "project-cradle",
    "pale-sun",
    "american-resource-utility",
    "corporate",
]


def pin(root, paths):
    result = []
    for relative in sorted(paths):
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise EditionError(f"Missing or linked input: {relative}")
        result.append({"path": relative, "sha256": sha(path.read_bytes())})
    return result


def generate(
    root: Path,
    available_at: str,
    version: str,
    accepted=False,
    acceptance_pr=None,
    adoption_path=None,
):
    timestamp(available_at)
    revision = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    recorded_at = subprocess.check_output(
        ["git", "-C", str(root), "show", "-s", "--format=%cI", "HEAD"], text=True
    ).strip()
    if timestamp(available_at) < max(timestamp(recorded_at), timestamp("2026-09-15T00:00:00Z")):
        raise EditionError("Edition evidence cannot predate its source record/authoring boundary")
    tracked = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"], text=True).split(
        "\0"
    )
    # Historical ZIP disposition is retained in source indexes, not silently redistributed.
    excluded = sorted(p for p in tracked if p.endswith(".zip"))
    sources = [p for p in tracked if p and p not in excluded]
    finance = root / "enterprise/generated/company-closeout-v1"
    workforce = root / "enterprise/generated/completed-period-2026-08"
    september = root / "enterprise/generated/september-custody-2026"
    identity = json.loads((finance / "identity.json").read_bytes())
    people_manifest = json.loads((workforce / "manifest.json").read_bytes())
    if identity["source_revision"] != revision or people_manifest["source_commit"] != revision:
        raise EditionError("Generated package source revision is stale; regenerate at this head")
    people_records = json.loads((workforce / "records.json").read_bytes())
    if (
        not isinstance(people_records, dict)
        or people_records.get("repository_source_commit") != revision
    ):
        raise EditionError("Workforce records and manifest source revision differ")
    if accepted and (
        people_manifest.get("publishable_source_snapshot") is not True
        or people_records.get("publishable_source_snapshot") is not True
    ):
        raise EditionError("Accepted package cannot use preview or unverified workforce provenance")
    if accepted and identity["dirty_development_build"]:
        raise EditionError("Accepted package cannot use a development finance build")
    for relative, digest in identity["source_files"].items():
        if sha((root / relative).read_bytes()) != digest:
            raise EditionError(f"Finance controlling source changed: {relative}")
    for relative, digest in people_manifest["source_hashes"].items():
        if sha((root / relative).read_bytes()) != digest:
            raise EditionError(f"Workforce controlling source changed: {relative}")
    september_record = json.loads((september / "records.json").read_bytes())
    if september_record["repository_source_commit"] != revision:
        raise EditionError("September custody source revision is stale")
    if accepted and not september_record["publishable_source_snapshot"]:
        raise EditionError("Accepted package cannot use preview September custody")
    for relative, digest in september_record["source_hashes"].items():
        if sha((root / relative).read_bytes()) != digest:
            raise EditionError(f"September custody source changed: {relative}")
    if {p.relative_to(september).as_posix() for p in september.rglob("*") if p.is_file()} != {
        "records.json"
    }:
        raise EditionError("Unexpected September custody artifact")
    finance_inventory = json.loads((finance / "manifest.json").read_bytes())
    generated = []
    for directory, inventory in [
        (finance, finance_inventory),
        (workforce, people_manifest["artifacts"]),
    ]:
        members = []
        for relative, digest in inventory.items():
            p = directory / relative
            if sha(p.read_bytes()) != digest:
                raise EditionError(f"Stale generated member: {p.relative_to(root)}")
            members.append(str(p.relative_to(root)))
        # Nested package manifests are separately verified by their native tools.
        members.extend(str(p.relative_to(root)) for p in directory.rglob("manifest.json"))
        actual = {str(p.relative_to(root)) for p in directory.rglob("*") if p.is_file()}
        if set(members) != actual:
            raise EditionError("Unexpected or omitted generated package file")
        generated.append(sorted(set(members)))
    generated[1].append(str((september / "records.json").relative_to(root)))
    components = []
    for cid, role, definition, members in [
        (
            "repository-source",
            "MIXED_SOURCE_ARCHIVE",
            "Exact tracked public repository snapshot except inventoried historical ZIP packages. "
            "Includes controlling and superseded sources, code, schemas, publications, "
            "catalogs and "
            "artwork; each source retains its own acceptance, period and fact status. Source files "
            "are not additional transaction or person populations.",
            sources,
        ),
        (
            "financial-successor",
            "CONDITIONAL_FORECAST",
            "Existing composed financial calibration and three conditional scenario populations, "
            "including seven-unit CSV/SQLite exports. Row-level period/scenario/source "
            "roles control; "
            "2027–2031 forecast activity is never September 2026 actual activity. Repeated formats "
            "and unit extracts are representations of the same populations, not additive members.",
            generated[0],
        ),
        (
            "completed-company-records",
            "NEWLY_AUTHORED_SYNTHETIC_HISTORY",
            "Declared August 2026 workforce, payroll and current operating populations with a "
            "separate September change/custody ledger through September 14. Authored evidence "
            "is available only from this edition's declared known-on boundary, "
            "regardless of event date.",
            generated[1],
        ),
    ]:
        components.append(
            {
                "id": cid,
                "fact_status": role,
                "access_scope": "PUBLIC_SYNTHETIC",
                "population_definition": definition,
                "units": UNITS,
                "legal_entities": ENTITIES,
                "available_at": available_at,
                "claims_known_on": available_at,
                "members": pin(root, members),
            }
        )
    contract = {
        "schema_version": "1.0.0",
        "edition_id": "SH-COMPANY-2026-09-15",
        "version": version,
        "status": "ACCEPTED_SCOPED_EDITION" if accepted else "REVIEW_CANDIDATE",
        "source_commit_required": revision,
        "scope": "Seven business lines and corporate: August completed-period packaging, "
        "September events through September 14 America/Los_Angeles, and separately "
        "identified forecasts.",
        "limitations": [
            "Synthetic company evidence, not actual registration, filings, payments or "
            "an audit opinion.",
            "Source status and the release exception register govern every claim; acceptance of "
            "this package does not convert OPEN records, forecasts or review proposals into facts.",
            "Engineering and original-artifact residuals remain at their precise recorded scope.",
            "The active portal's live services and private evaluator data are outside "
            "this package; "
            "only the documented isolated software exercises are demonstrated.",
            "Hash agreement establishes byte identity, not factual completeness or "
            "independent confirmation.",
        ],
        "allowed_joins": [
            "Existing stable record/person/position/asset/contract/source IDs within "
            "their declared populations.",
            "Financial scenario + legal entity + effective period + journal/source ID; "
            "never add consolidated, legal-book, unit or duplicate-format "
            "representations together.",
            "Workforce person_id + effective event interval + legal employer; "
            "positions, directors and FTE remain distinct.",
            "Evidence/source relationships preserve available_at, acceptance date and "
            "access scope; "
            "no latest-version fallback into an earlier known-on view.",
        ],
        "historical_zip_exclusions": excluded,
        "required_components": [c["id"] for c in components],
        "components": components,
    }
    if accepted:
        from .acceptance import collect

        if acceptance_pr is None or adoption_path is None:
            raise EditionError("Accepted edition requires merged PR and scoped adoption source")
        contract["acceptance_receipt"] = collect(root, revision, acceptance_pr, adoption_path)
    elif acceptance_pr is not None or adoption_path is not None:
        raise EditionError("Review candidate cannot assert repository acceptance")
    validate_contract(contract)
    return contract


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--available-at", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--accepted", action="store_true")
    parser.add_argument("--acceptance-pr", type=int)
    parser.add_argument("--adoption-path")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise EditionError("New immutable contract filename required")
    contract = generate(
        args.root.resolve(),
        args.available_at,
        args.version,
        args.accepted,
        args.acceptance_pr,
        args.adoption_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encoded(contract))
    print(
        json.dumps(
            {
                "components": len(contract["components"]),
                "members": sum(len(c["members"]) for c in contract["components"]),
            }
        )
    )
