"""Build a private, partial routing diagnostic for reviewed fictional sources.

The generated profiles are loadable by FederatedCompanyStore, but are never
source-complete and are not bound to an audit engagement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import stat
import tempfile
from pathlib import Path

from .company_federation import (
    QUALIFICATION,
    FederatedCompanyStore,
)
from .company_federation import (
    SCHEMA as REGISTRY_SCHEMA,
)
from .fictional_2027_source_portfolio import BASE, SOURCES, verify_all

BASE_REL = (
    "enterprise/generated/audit-suite/acceptance-audit-2026-09-22/"
    "aq06-aq07-integrated-full-portfolio-bootstrap-run-v1/registry"
)
BASE_SHA256 = {
    "A": "4b224115e511bedb67396aae35c51d976bc92032e96e1b15725a67bea3cc5656",
    "B": "3a0568317f962ec005d3ac030a9356935e12d1f14f798ce38639c77a1f873ef5",
}
SCHEMA = "SH_FICTIONAL_2027_PARTIAL_CANDIDATE_REGISTRY_DIAGNOSTIC_V1"


class CandidateRegistryError(ValueError):
    """A source or route changed during candidate construction."""


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def _private(path: Path, *, directory: bool = False) -> tuple:
    path = path.absolute()
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise CandidateRegistryError("Private path cannot contain aliases")
    info = path.stat()
    if info.st_mode & 0o077 or not (
        stat.S_ISDIR(info.st_mode)
        if directory
        else stat.S_ISREG(info.st_mode) and info.st_nlink == 1
    ):
        raise CandidateRegistryError("Private regular source or directory required")
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IMODE(info.st_mode),
        info.st_size,
        info.st_mtime_ns,
        None if directory else _sha(path),
    )


def _pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise CandidateRegistryError("Duplicate JSON field")
        result[key] = value
    return result


def _json(path: Path) -> dict:
    result = json.loads(path.read_bytes(), object_pairs_hook=_pairs)
    if not isinstance(result, dict):
        raise CandidateRegistryError("Expected JSON object")
    return result


def _source_component(root: Path, source, scenario: str) -> tuple[dict, dict]:
    run = root / BASE / source.folder / source.run
    receipt_path = run / "RECEIPT.json"
    db_path = run / "company.sqlite3"
    _private(run, directory=True)
    receipt_before, db_before = _private(receipt_path), _private(db_path)
    if any(Path(str(db_path) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
        raise CandidateRegistryError("Source database has active sidecar")
    receipt = _json(receipt_path)
    branches = receipt.get("branches")
    if not isinstance(branches, dict) or set(branches) != {"CLEAN", "MESSY"}:
        raise CandidateRegistryError("Exact fictional branch routing required")
    branch = branches[scenario]
    if (
        not isinstance(branch, str)
        or branch == branches["MESSY" if scenario == "CLEAN" else "CLEAN"]
    ):
        raise CandidateRegistryError("Distinct fictional source branches required")
    with sqlite3.connect(db_path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CandidateRegistryError("Source database integrity failed")
        rows = db.execute(
            "SELECT company,branch,system FROM systems ORDER BY company,branch,system"
        ).fetchall()
        native = db.execute("SELECT DISTINCT company,branch FROM versions").fetchall()
    if _private(receipt_path) != receipt_before or _private(db_path) != db_before:
        raise CandidateRegistryError("Source changed during routing read")
    companies = {company for company, selected, _ in rows if selected == branch}
    systems = sorted(system for company, selected, system in rows if selected == branch)
    if (
        len(companies) != 1
        or not systems
        or len(set(systems)) != len(systems)
        or {(company, selected) for company, selected in native}
        != {(company, value) for value in branches.values() for company in companies}
    ):
        raise CandidateRegistryError("Selected source system and native population differ")
    company = next(iter(companies))
    component = {
        "root": str(run),
        "company": company,
        "branch": branch,
        "namespace": "F27" + source.key.upper().replace("_", ""),
        "systems": systems,
    }
    pin = {
        "source": source.key,
        "source_review_sha256": source.review_sha256,
        "receipt_sha256": receipt_before[-1],
        "database_sha256": db_before[-1],
        "physical_company": company,
        "physical_branch": branch,
        "system_count": len(systems),
    }
    return component, pin


def candidate_profiles(repository: Path, private_repository: Path) -> tuple[dict, dict]:
    """Verify ten sources and derive A/B diagnostic profiles without grants."""
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    diagnostic = verify_all(repository, private_repository=private_repository)
    if (
        diagnostic["source_count"],
        diagnostic["native_versions"],
        diagnostic["source_complete"],
    ) != (10, 178, False):
        raise CandidateRegistryError("Reviewed source roster differs")
    profiles = {}
    reviewed = {row["source"]: row for row in diagnostic["sources"]}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        base_path = private_repository / BASE_REL / f"{side}.json"
        before = _private(base_path)
        if before[-1] != BASE_SHA256[side]:
            raise CandidateRegistryError("Frozen baseline registry differs")
        base = _json(base_path)
        if (
            base.get("schema") != REGISTRY_SCHEMA
            or len(base.get("profiles", {})) != 1
            or len(base.get("components", {})) != 13
        ):
            raise CandidateRegistryError("Expected frozen 13-component profile")
        base_profile = next(iter(base["profiles"].values()))
        if base_profile.get("company") != "SABLEHARBOR" or set(
            base_profile.get("components", [])
        ) != set(base["components"]):
            raise CandidateRegistryError("Frozen profile routing differs")
        components = dict(base["components"])
        pins = []
        for source in SOURCES:
            component, pin = _source_component(private_repository, source, scenario)
            pin["manifest_sha256"] = reviewed[source.key]["manifest_sha256"]
            name = "scenario-" + source.key.replace("_", "-")
            if name in components:
                raise CandidateRegistryError("Source component identity collision")
            components[name] = component
            pins.append(pin)
        profile_id = "fictional27-candidate-" + scenario.lower()
        manifest = {
            "schema": REGISTRY_SCHEMA,
            "components": components,
            "profiles": {
                profile_id: {
                    "company": "SABLEHARBOR",
                    "components": sorted(components),
                    "qualification": QUALIFICATION,
                }
            },
        }
        if _private(base_path) != before:
            raise CandidateRegistryError("Frozen baseline changed during read")
        profiles[side] = {
            "manifest": manifest,
            "profile_id": profile_id,
            "source_pins": pins,
            "base_registry_sha256": before[-1],
        }
    return diagnostic, profiles


def write_candidate(repository: Path, private_repository: Path, destination: Path) -> dict:
    """Publish a private diagnostic pair, with no audit engagement or collection."""
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise CandidateRegistryError("Fresh diagnostic destination required")
    _private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".candidate-registry-", dir=destination.parent) as temp:
        temp_root = Path(temp)
        rows = {}
        for side in ("A", "B"):
            profile = profiles[side]
            path = temp_root / f"{side}.json"
            path.write_text(json.dumps(profile["manifest"], sort_keys=True, indent=2) + "\n")
            path.chmod(0o600)
            store = FederatedCompanyStore(path, profile["profile_id"])
            expected = profile["manifest"]["components"]
            if store._manifest["components"] != expected:
                raise CandidateRegistryError("Federated adapter routing differs")
            rows[side] = {
                "profile_id": profile["profile_id"],
                "registry_sha256": _sha(path),
                "base_registry_sha256": profile["base_registry_sha256"],
                "component_count": len(expected),
                "scenario_source_count": len(profile["source_pins"]),
                "system_alias_count": sum(len(item["systems"]) for item in expected.values()),
                "source_pins": profile["source_pins"],
                "logical_company": "SABLEHARBOR",
                "physical_company_ids": sorted({item["company"] for item in expected.values()}),
                "source_complete": False,
            }
        report = {
            "schema": SCHEMA,
            "status": "PARTIAL_ROUTING_DIAGNOSTIC_NOT_AUDIT_READY",
            "portfolio_verifier_sha256": diagnostic["verifier_module_sha256"],
            "reviewed_native_versions": diagnostic["native_versions"],
            "sides": rows,
            "source_complete": False,
            "fresh_audit_pair_created": False,
            "audit_task_credit": False,
            "grants_or_collections_created": False,
            "limits": [
                "A/B are routing profiles, not Clean/Messy audit engagements.",
                "Mixed physical company IDs remain explicit; no actual operation is asserted.",
                "Selected sources are partial; 283 discovery routes per side remain unresolved.",
                "No source population, global snapshot, PBC request, grant or evidence collection.",
            ],
        }
        report_path = temp_root / "REPORT.json"
        report_path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
        report_path.chmod(0o600)
        after = verify_all(repository, private_repository=private_repository)
        if after["sources"] != diagnostic["sources"]:
            raise CandidateRegistryError("Reviewed sources changed during routing build")
        os.rename(temp_root, destination)
    for side in ("A", "B"):
        path = destination / f"{side}.json"
        if _sha(path) != rows[side]["registry_sha256"]:
            raise CandidateRegistryError("Published diagnostic registry differs")
        FederatedCompanyStore(path, rows[side]["profile_id"])
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            write_candidate(args.repository, args.private_repository, args.destination),
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
