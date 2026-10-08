"""Build a private, partial 28-component routing diagnostic for reviewed sources."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from . import fictional_2027_candidate_registry as historical
from . import fictional_2027_source_portfolio_v2 as portfolio
from .company_federation import FederatedCompanyStore

CandidateRegistryError = historical.CandidateRegistryError
SCHEMA = "SH_FICTIONAL_2027_PARTIAL_CANDIDATE_REGISTRY_DIAGNOSTIC_V2"


def candidate_profiles(repository: Path, private_repository: Path) -> tuple[dict, dict]:
    """Append five reviewed native routes to the unchanged V1 ten-source profile."""
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    original, old_profiles = historical.candidate_profiles(repository, private_repository)
    diagnostic = portfolio.verify_all(repository, private_repository=private_repository)
    if (
        original["source_count"] != 10
        or original["native_versions"] != 178
        or diagnostic["source_count"] != 15
        or diagnostic["native_versions"] != 256
        or diagnostic["sources"][:10] != original["sources"]
    ):
        raise CandidateRegistryError("Historical and successor rosters disagree")
    reviewed = {row["source"]: row for row in diagnostic["sources"]}
    profiles = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        old = old_profiles[side]
        components = dict(old["manifest"]["components"])
        pins = list(old["source_pins"])
        if len(components) != 23 or len(pins) != 10:
            raise CandidateRegistryError("Historical partial profile differs")
        for source in portfolio.EXTRA_SOURCES:
            component, pin = historical._source_component(private_repository, source, scenario)
            row = reviewed[source.key]
            if (
                pin["database_sha256"] != row["database_sha256"]
                or pin["receipt_sha256"] != row["receipt_sha256"]
                or [pin["physical_company"]] != row["physical_company_ids"]
                or pin["physical_branch"] not in row["branch_versions"]
                or row["branch_versions"][pin["physical_branch"]] < 1
            ):
                raise CandidateRegistryError("Selected physical source routing differs")
            pin["manifest_sha256"] = row["manifest_sha256"]
            name = "scenario-" + source.key.replace("_", "-")
            if name in components:
                raise CandidateRegistryError("Successor source component collides")
            components[name] = component
            pins.append(pin)
        profile_id = "fictional27-candidate-v2-" + scenario.lower()
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
        if len(components) != 28 or len(pins) != 15:
            raise CandidateRegistryError("Expected partial 28-component source roster")
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
        sides[side] = {
            "profile_id": profile["profile_id"],
            "registry_sha256": historical._sha(files[side]),
            "base_registry_sha256": profile["base_registry_sha256"],
            "component_count": len(components),
            "scenario_source_count": len(profile["source_pins"]),
            "system_alias_count": sum(len(item["systems"]) for item in components.values()),
            "source_pins": profile["source_pins"],
            "logical_company": "SABLEHARBOR",
            "physical_company_ids": sorted({item["company"] for item in components.values()}),
            "source_complete": False,
        }
    return {
        "schema": SCHEMA,
        "status": "PARTIAL_ROUTING_DIAGNOSTIC_NOT_AUDIT_READY",
        "portfolio_verifier_sha256": diagnostic["verifier_module_sha256"],
        "historical_portfolio_verifier_sha256": diagnostic["historical_v1_verifier_sha256"],
        "reviewed_native_versions": diagnostic["native_versions"],
        "sides": sides,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "grants_or_collections_created": False,
        "limits": [
            "A/B are routing profiles, not Clean/Messy audit engagements.",
            "Mixed physical company IDs and exact source branches remain explicit.",
            "Fifteen selected cohorts are partial; 283 discovery routes per "
            "side remain unresolved.",
            "No source-complete population, global snapshot, PBC, grant or collection.",
            "Reviewed policy source remains local and does not establish complete policy coverage.",
        ],
    }


def write_candidate(repository: Path, private_repository: Path, destination: Path) -> dict:
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise CandidateRegistryError("Fresh successor destination required")
    historical._private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".candidate-v2-", dir=destination.parent) as temp:
        stage = Path(temp)
        files = {}
        for side in "AB":
            path = stage / f"{side}.json"
            path.write_text(json.dumps(profiles[side]["manifest"], sort_keys=True, indent=2) + "\n")
            path.chmod(0o600)
            adapter = FederatedCompanyStore(path, profiles[side]["profile_id"])
            if adapter._manifest["components"] != profiles[side]["manifest"]["components"]:
                raise CandidateRegistryError("Successor adapter routes differ")
            files[side] = path
        report = _report(diagnostic, profiles, files)
        report_path = stage / "REPORT.json"
        report_path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
        report_path.chmod(0o600)
        after = portfolio.verify_all(repository, private_repository=private_repository)
        if after["sources"] != diagnostic["sources"]:
            raise CandidateRegistryError("Reviewed source portfolio changed during build")
        os.rename(stage, destination)
    return verify_candidate(destination, repository, private_repository)


def verify_candidate(destination: Path, repository: Path, private_repository: Path) -> dict:
    """Reconstruct exact routing bytes, report and no-credit claim read-only."""
    root = Path(destination).absolute()
    historical._private(root, directory=True)
    if {p.name for p in root.iterdir()} != {"A.json", "B.json", "REPORT.json"}:
        raise CandidateRegistryError("Exact three-file successor diagnostic required")
    before = {
        name: historical._private(root / name) for name in ("A.json", "B.json", "REPORT.json")
    }
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    files = {side: root / f"{side}.json" for side in "AB"}
    for side in "AB":
        if historical._json(files[side]) != profiles[side]["manifest"]:
            raise CandidateRegistryError("Successor candidate manifest differs")
        FederatedCompanyStore(files[side], profiles[side]["profile_id"])
    report = historical._json(root / "REPORT.json")
    if report != _report(diagnostic, profiles, files):
        raise CandidateRegistryError("Successor candidate report differs")
    if any(
        report["sides"][side]["component_count"] != 28
        or report["sides"][side]["scenario_source_count"] != 15
        for side in "AB"
    ):
        raise CandidateRegistryError("Successor candidate counts differ")
    if {
        name: historical._private(root / name) for name in ("A.json", "B.json", "REPORT.json")
    } != before:
        raise CandidateRegistryError("Successor diagnostic changed during verification")
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
