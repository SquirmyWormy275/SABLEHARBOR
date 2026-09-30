"""Private, partial 35-component routing diagnostic for 21 reviewed cohorts."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import tempfile
from pathlib import Path

from . import fictional_2027_candidate_registry as historical
from . import fictional_2027_candidate_registry_v2 as previous
from . import fictional_2027_source_portfolio_v3 as portfolio
from .company_federation import FederatedCompanyStore

CandidateRegistryError = historical.CandidateRegistryError
SCHEMA = "SH_FICTIONAL_2027_PARTIAL_CANDIDATE_REGISTRY_DIAGNOSTIC_V3"


def _new_component(
    private: Path, source: portfolio.NewSource, scenario: str, ledger: str
) -> tuple[dict, dict]:
    run = private / portfolio.BASE / source.folder / source.run
    db_path = portfolio._db_path(run, ledger)
    root = db_path.parent
    receipt_path = run / source.receipt_name
    historical._private(root, directory=True)
    receipt_before = historical._private(receipt_path)
    db_before = historical._private(db_path)
    if any(
        Path(str(db_path) + suffix).exists() or Path(str(db_path) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CandidateRegistryError("New source database has active sidecar")
    receipt = historical._json(receipt_path)
    branches = portfolio._branches(source, receipt)
    branch = branches[scenario]
    with sqlite3.connect(db_path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CandidateRegistryError("New source database integrity differs")
        rows = db.execute(
            "SELECT company,branch,system FROM systems ORDER BY company,branch,system"
        ).fetchall()
        native = db.execute(
            "SELECT company,branch,COUNT(*) FROM versions GROUP BY company,branch"
        ).fetchall()
        if any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "access_events", "collections")
        ):
            raise CandidateRegistryError("New source contains audit access")
    if (
        historical._private(receipt_path) != receipt_before
        or historical._private(db_path) != db_before
    ):
        raise CandidateRegistryError("New source changed during routing read")
    systems = sorted(system for company, selected, system in rows if selected == branch)
    expected = source.system_counts[[name for name, _ in source.databases].index(ledger)]
    if (
        len(systems) != expected
        or len(set(systems)) != expected
        or {company for company, selected, system in rows if selected == branch}
        != {"SABLE-HARBOR-REFERENCE"}
        or {(company, selected) for company, selected, _ in rows}
        != {("SABLE-HARBOR-REFERENCE", value) for value in branches.values()}
        or {(company, selected) for company, selected, _ in native}
        != {("SABLE-HARBOR-REFERENCE", value) for value in branches.values()}
        or db_before[-1] != dict(source.databases)[ledger]
    ):
        raise CandidateRegistryError("New source physical route differs")
    name = source.key + ("-" + ledger if len(source.databases) > 1 else "")
    component = {
        "root": str(root),
        "company": "SABLE-HARBOR-REFERENCE",
        "branch": branch,
        "namespace": "F27" + name.upper().replace("-", ""),
        "systems": systems,
    }
    pin = {
        "source": source.key,
        "ledger": ledger,
        "source_review_sha256": source.review_sha256,
        "manifest_sha256": source.manifest_sha256,
        "receipt_sha256": receipt_before[-1],
        "database_sha256": db_before[-1],
        "physical_company": "SABLE-HARBOR-REFERENCE",
        "physical_branch": branch,
        "system_count": expected,
    }
    return component, pin


def candidate_profiles(repository: Path, private_repository: Path) -> tuple[dict, dict]:
    """Derive a new diagnostic, preserving V2's reviewed 15-source routing."""
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    old_diagnostic, old_profiles = previous.candidate_profiles(repository, private_repository)
    diagnostic = portfolio.verify_all(repository, private_repository=private_repository)
    if (
        old_diagnostic["source_count"] != 15
        or old_diagnostic["native_versions"] != 256
        or diagnostic["source_count"] != 21
        or diagnostic["native_versions"] != 358
        or diagnostic["sources"][:15] != old_diagnostic["sources"]
    ):
        raise CandidateRegistryError("Historical V2 roster differs")
    reviewed = {row["source"]: row for row in diagnostic["sources"]}
    profiles = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        old = old_profiles[side]
        components = dict(old["manifest"]["components"])
        pins = list(old["source_pins"])
        if len(components) != 28 or len(pins) != 15:
            raise CandidateRegistryError("Historical V2 partial profile differs")
        for source in portfolio.NEW_SOURCES:
            row = reviewed[source.key]
            for ledger, _hash in source.databases:
                component, pin = _new_component(private_repository, source, scenario, ledger)
                if (
                    pin["database_sha256"] != row["database_sha256"][ledger]
                    or pin["receipt_sha256"] != row["receipt_sha256"]
                    or pin["physical_company"] not in row["physical_company_ids"]
                    or pin["physical_branch"] not in row["branch_versions"]
                    or pin["system_count"] != row["ledger_system_counts"][ledger]
                ):
                    raise CandidateRegistryError("New reviewed physical source route differs")
                name = (
                    "scenario-" + source.key + ("-" + ledger if len(source.databases) > 1 else "")
                )
                if name in components:
                    raise CandidateRegistryError("Successor source component collision")
                components[name] = component
                pins.append(pin)
        profile_id = "fictional27-candidate-v3-" + scenario.lower()
        manifest = {
            "schema": historical.REGISTRY_SCHEMA,
            "components": components,
            "profiles": {
                profile_id: {
                    "company": "SABLEHARBOR",
                    "components": sorted(components),
                    "qualification": historical.QUALIFICATION,
                }
            },
        }
        if len(components) != 35 or len(pins) != 22:
            raise CandidateRegistryError("Expected partial 35-component/22-pin source roster")
        profiles[side] = {
            "manifest": manifest,
            "profile_id": profile_id,
            "source_pins": pins,
            "base_registry_sha256": old["base_registry_sha256"],
        }
    return diagnostic, profiles


def _report(diagnostic: dict, profiles: dict, files: dict) -> dict:
    sides = {}
    for side in "AB":
        profile = profiles[side]
        components = profile["manifest"]["components"]
        aliases = sum(len(item["systems"]) for item in components.values())
        if aliases != 211:
            raise CandidateRegistryError("Expected 211 partial system aliases per side")
        sides[side] = {
            "profile_id": profile["profile_id"],
            "registry_sha256": historical._sha(files[side]),
            "base_registry_sha256": profile["base_registry_sha256"],
            "component_count": len(components),
            "source_cohort_count": diagnostic["source_count"],
            "scenario_source_component_count": len(profile["source_pins"]),
            "system_alias_count": aliases,
            "source_pins": profile["source_pins"],
            "logical_company": "SABLEHARBOR",
            "physical_company_ids": sorted({item["company"] for item in components.values()}),
            "source_complete": False,
        }
    return {
        "schema": SCHEMA,
        "status": "PARTIAL_ROUTING_DIAGNOSTIC_NOT_AUDIT_READY",
        "portfolio_verifier_sha256": diagnostic["verifier_module_sha256"],
        "v2_portfolio_verifier_sha256": diagnostic["v2_verifier_sha256"],
        "reviewed_native_versions": diagnostic["native_versions"],
        "sides": sides,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "grants_or_collections_created": False,
        "limits": [
            "A/B are routing profiles, not Clean/Messy audit engagements.",
            "Twenty-one selected cohorts, two physical IAM005 ledgers, 22 source-component pins.",
            "Mixed physical company IDs and Clean/Messy source branches remain explicit.",
            "No source-complete population, global snapshot, PBC, grant, collection, "
            "task or grade.",
            "Frozen 283 documentary/activity routes per side remain unresolved.",
        ],
    }


def write_candidate(repository: Path, private_repository: Path, destination: Path) -> dict:
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise CandidateRegistryError("Fresh V3 successor destination required")
    historical._private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".candidate-v3-", dir=destination.parent) as temp:
        stage = Path(temp)
        files = {}
        for side in "AB":
            path = stage / f"{side}.json"
            path.write_text(json.dumps(profiles[side]["manifest"], sort_keys=True, indent=2) + "\n")
            path.chmod(0o600)
            adapter = FederatedCompanyStore(path, profiles[side]["profile_id"])
            if adapter._manifest["components"] != profiles[side]["manifest"]["components"]:
                raise CandidateRegistryError("V3 adapter routes differ")
            files[side] = path
        report = _report(diagnostic, profiles, files)
        report_path = stage / "REPORT.json"
        report_path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
        report_path.chmod(0o600)
        after = portfolio.verify_all(repository, private_repository=private_repository)
        if after["sources"] != diagnostic["sources"]:
            raise CandidateRegistryError("Reviewed V3 source portfolio changed during build")
        os.rename(stage, destination)
    return verify_candidate(destination, repository, private_repository)


def verify_candidate(destination: Path, repository: Path, private_repository: Path) -> dict:
    """Rebuild exact V3 routing bytes and no-credit report read-only."""
    root = Path(destination).absolute()
    historical._private(root, directory=True)
    if {path.name for path in root.iterdir()} != {"A.json", "B.json", "REPORT.json"}:
        raise CandidateRegistryError("Exact three-file V3 diagnostic required")
    before = {
        name: historical._private(root / name) for name in ("A.json", "B.json", "REPORT.json")
    }
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    files = {side: root / f"{side}.json" for side in "AB"}
    for side in "AB":
        if historical._json(files[side]) != profiles[side]["manifest"]:
            raise CandidateRegistryError("V3 candidate manifest differs")
        FederatedCompanyStore(files[side], profiles[side]["profile_id"])
    report = historical._json(root / "REPORT.json")
    if report != _report(diagnostic, profiles, files):
        raise CandidateRegistryError("V3 candidate report differs")
    if any(
        report["sides"][side]["component_count"] != 35
        or report["sides"][side]["source_cohort_count"] != 21
        or report["sides"][side]["scenario_source_component_count"] != 22
        for side in "AB"
    ):
        raise CandidateRegistryError("V3 candidate counts differ")
    if {name: historical._private(root / name) for name in before} != before:
        raise CandidateRegistryError("V3 candidate changed during verification")
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
