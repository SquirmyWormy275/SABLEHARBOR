"""Exercise scoped original collection from disposable copies of reviewed sources.

The probe cannot create an audit engagement. All grants and collection journals
are confined to ordinary-byte copies; independently reviewed originals stay read-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from pathlib import Path

from .company_federation import FederatedCompanyStore
from .company_store import CompanyStore, CompanyStoreError
from .fictional_2027_candidate_registry import (
    BASE,
    SOURCES,
    CandidateRegistryError,
    _private,
    _sha,
    candidate_profiles,
)

SCHEMA = "SH_FICTIONAL_2027_DISPOSABLE_COLLECTION_PROBE_V1"
PRINCIPAL = "F27-PROBE-READER"
ENGAGEMENT = "F27-DISPOSABLE-PROBE"
AS_OF = "2027-12-31T23:59:59+00:00"


def _ordinary_copy(source: Path, target: Path) -> None:
    """Write independent bytes, never a reflink or hardlink."""
    before = _private(source)
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    target.parent.chmod(0o700)
    with source.open("rb") as old, target.open("xb") as new:
        os.fchmod(new.fileno(), 0o600)
        while chunk := old.read(1024 * 1024):
            new.write(chunk)
        new.flush()
        os.fsync(new.fileno())
    if _private(source) != before or _sha(target) != before[-1]:
        raise CandidateRegistryError("Ordinary company source copy differs")
    if (source.stat().st_dev, source.stat().st_ino) == (target.stat().st_dev, target.stat().st_ino):
        raise CandidateRegistryError("Company source copy shares an inode")


def _first_exact_ref(private_repository: Path, source, scenario: str) -> dict:
    path = private_repository / BASE / source.folder / source.run / "RECEIPT.json"
    _private(path)
    receipt = json.loads(path.read_text())
    refs = receipt["records"][scenario]
    if not isinstance(refs, list) or not refs:
        raise CandidateRegistryError("Selected source has no native version")
    ref = refs[0]
    if ref["branch"] != receipt["branches"][scenario] or ref["version"] != 1:
        raise CandidateRegistryError("Selected native branch/version differs")
    return ref


def _counts(path: Path) -> dict:
    with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CandidateRegistryError("Disposable source integrity failed")
        return {
            table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("versions", "grants", "collections", "access_events")
        }


def run(repository: Path, private_repository: Path, destination: Path) -> dict:
    """Collect one exact native version per reviewed cohort and side, then seal report."""
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise CandidateRegistryError("Fresh disposable probe destination required")
    _private(destination.parent, directory=True)
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    destination.mkdir(mode=0o700)
    originals = {}
    output = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        side_root = destination / side
        side_root.mkdir(mode=0o700)
        profile = profiles[side]
        manifest = json.loads(json.dumps(profile["manifest"]))
        copied = {}
        refs = {}
        for source in SOURCES:
            source_id = "scenario-" + source.key.replace("_", "-")
            origin = Path(manifest["components"][source_id]["root"]) / "company.sqlite3"
            originals[str(origin)] = _private(origin)
            target = side_root / source.key / "company.sqlite3"
            _ordinary_copy(origin, target)
            manifest["components"][source_id]["root"] = str(target.parent)
            copied[source.key] = target
            refs[source.key] = _first_exact_ref(private_repository, source, scenario)
            counts = _counts(target)
            if counts["grants"] or counts["collections"] or counts["access_events"]:
                raise CandidateRegistryError("Disposable source copy inherited audit access")
        registry_path = destination / f"{side}.json"
        registry_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        registry_path.chmod(0o600)
        federated = FederatedCompanyStore(registry_path, profile["profile_id"])
        rows = []
        for source in SOURCES:
            source_id = "scenario-" + source.key.replace("_", "-")
            ref = refs[source.key]
            component = manifest["components"][source_id]
            alias = component["namespace"] + ":" + ref["system"]
            if (ref["company"], ref["branch"]) != (component["company"], component["branch"]):
                raise CandidateRegistryError("Selected native source route differs")
            before_systems = federated.list_systems(
                PRINCIPAL, ENGAGEMENT, "SABLEHARBOR", profile["profile_id"]
            )
            if alias in {row["system"] for row in before_systems["systems"]}:
                raise CandidateRegistryError("Source alias visible before scoped grant")
            try:
                federated.read_version(
                    PRINCIPAL,
                    ENGAGEMENT,
                    "SABLEHARBOR",
                    profile["profile_id"],
                    alias,
                    ref["record"],
                    version=ref["version"],
                    as_of=AS_OF,
                )
            except CompanyStoreError:
                pregrant_denied = True
            else:
                raise CandidateRegistryError("Source visible before scoped grant")
            CompanyStore(copied[source.key].parent).grant(
                PRINCIPAL, ENGAGEMENT, ref["company"], ref["branch"], ref["system"]
            )
            discovered_systems = federated.list_systems(
                PRINCIPAL, ENGAGEMENT, "SABLEHARBOR", profile["profile_id"]
            )
            if alias not in {row["system"] for row in discovered_systems["systems"]}:
                raise CandidateRegistryError("Granted source alias not discoverable")
            discovered_records = federated.list_records(
                PRINCIPAL,
                ENGAGEMENT,
                "SABLEHARBOR",
                profile["profile_id"],
                alias,
                as_of=ref["available_at"],
            )
            if not any(
                row["record"] == ref["record"]
                and row["version"] == ref["version"]
                and row["sha256"] == ref["sha256"]
                for row in discovered_records["records"]
            ):
                raise CandidateRegistryError("Exact native record not discoverable")
            read = federated.read_version(
                PRINCIPAL,
                ENGAGEMENT,
                "SABLEHARBOR",
                profile["profile_id"],
                alias,
                ref["record"],
                version=ref["version"],
                as_of=AS_OF,
            )
            if (
                read["sha256"] != ref["sha256"]
                or hashlib.sha256(read["content"]).hexdigest() != ref["sha256"]
                or read["source_store_id"] != source_id
                or read["company"] != ref["company"]
            ):
                raise CandidateRegistryError("Federated original read differs")
            collection = federated.collect(
                PRINCIPAL,
                ENGAGEMENT,
                "SABLEHARBOR",
                profile["profile_id"],
                alias,
                ref["record"],
                version=ref["version"],
                as_of=AS_OF,
                command_id=f"PROBE-{side}-{source.key.upper()}",
            )
            retained = collection["source"]
            if any(
                retained[k] != ref[k]
                for k in (
                    "company",
                    "branch",
                    "system",
                    "record",
                    "version",
                    "sha256",
                    "event_at",
                    "available_at",
                    "imported_at",
                )
            ):
                raise CandidateRegistryError("Collected provenance differs from original")
            counts = _counts(copied[source.key])
            if (counts["grants"], counts["collections"], counts["access_events"]) != (1, 1, 1):
                raise CandidateRegistryError("Disposable access journal denominator differs")
            rows.append(
                {
                    "source": source.key,
                    "source_store_id": source_id,
                    "alias": alias,
                    "native_identity": {
                        k: ref[k]
                        for k in (
                            "company",
                            "branch",
                            "system",
                            "record",
                            "version",
                            "sha256",
                            "event_at",
                            "available_at",
                            "imported_at",
                        )
                    },
                    "pregrant_denied": pregrant_denied,
                    "source_discovery_verified": True,
                    "read_original_sha256_verified": True,
                    "ordinary_collection_provenance_verified": True,
                    "disposable_access_counts": counts,
                }
            )
        output[side] = {
            "scenario": scenario,
            "registry_sha256": _sha(registry_path),
            "profile_id": profile["profile_id"],
            "source_count": len(rows),
            "collections": rows,
        }
    for path, before in originals.items():
        if _private(Path(path)) != before:
            raise CandidateRegistryError("Independently reviewed company source changed")
    after, _ = candidate_profiles(repository, private_repository)
    if after["sources"] != diagnostic["sources"]:
        raise CandidateRegistryError("Reviewed source portfolio changed during probe")
    if diagnostic["source_complete"] or sum(x["source_count"] for x in output.values()) != 20:
        raise CandidateRegistryError("Probe scope differs")
    report = {
        "schema": SCHEMA,
        "status": "PASS_DISPOSABLE_SOURCE_TO_COLLECTOR_BOUNDARY_ONLY",
        "probe_module_sha256": _sha(Path(__file__)),
        "source_portfolio_verifier_sha256": diagnostic["verifier_module_sha256"],
        "reviewed_source_inventory": diagnostic["sources"],
        "source_count": 10,
        "native_version_count_in_reviewed_sources": diagnostic["native_versions"],
        "disposable_collection_count": 20,
        "sides": output,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "original_company_sources_unchanged": True,
        "limits": [
            "All grants and collections are in disposable ordinary-byte source copies.",
            "No PBC, real audit engagement, workpaper, population, task or Key was created.",
            "Physical company/branch identities remain original fictional source identities.",
            "One exact version per cohort crosses the adapter; 283-route coverage is unproven.",
        ],
    }
    path = destination / "REPORT.json"
    path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    path.chmod(0o600)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.repository, args.private_repository, args.destination)
    print(json.dumps({k: v for k, v in report.items() if k != "sides"}, sort_keys=True))


if __name__ == "__main__":
    main()
