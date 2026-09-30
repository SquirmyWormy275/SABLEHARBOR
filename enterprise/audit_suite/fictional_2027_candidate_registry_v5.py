"""Private partial V5 routing diagnostic; does not create an audit engagement."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from . import fictional_2027_candidate_registry_v4 as prior
from . import fictional_2027_source_portfolio_v5 as portfolio
from .company_federation import FederatedCompanyStore

CandidateRegistryError = prior.CandidateRegistryError
SCHEMA = "SH_FICTIONAL_2027_PARTIAL_CANDIDATE_REGISTRY_DIAGNOSTIC_V5"


def candidate_profiles(repository: Path, private_repository: Path) -> tuple[dict, dict]:
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    old_diagnostic, old_profiles = prior.candidate_profiles(repository, private_repository)
    diagnostic = portfolio.verify_all(repository, private_repository=private_repository)
    if (
        old_diagnostic.get("source_count"),
        old_diagnostic.get("native_versions"),
        old_diagnostic.get("source_component_count"),
    ) != (24, 401, 25) or diagnostic["sources"][:24] != old_diagnostic["sources"]:
        raise CandidateRegistryError("Reviewed V4 candidate/source prefix differs")
    if (
        diagnostic.get("source_count"),
        diagnostic.get("native_versions"),
        diagnostic.get("source_component_count"),
    ) != (26, 475, 27):
        raise CandidateRegistryError("Reviewed V5 source roster differs")
    reviewed = {row["source"]: row for row in diagnostic["sources"]}
    profiles = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        old = old_profiles[side]
        components = dict(old["manifest"]["components"])
        pins = list(old["source_pins"])
        if len(components) != 38 or len(pins) != 25:
            raise CandidateRegistryError("Historical V4 candidate roster differs")
        for source in portfolio.STANDARD:
            component, pin = prior._component_for_standard(
                private_repository, source, scenario, reviewed[source.key]
            )
            name = "scenario-" + source.key
            if name in components:
                raise CandidateRegistryError("V5 source component collision")
            components[name] = component
            pins.append(pin)
        if len(components) != 40 or len(pins) != 27:
            raise CandidateRegistryError("Exact V5 40-component/27-pin roster differs")
        profile_id = "fictional27-candidate-v5-" + scenario.lower()
        manifest = {
            "schema": prior.historical.REGISTRY_SCHEMA,
            "components": components,
            "profiles": {
                profile_id: {
                    "company": "SABLEHARBOR",
                    "components": sorted(components),
                    "qualification": prior.historical.QUALIFICATION,
                }
            },
        }
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
        if aliases != 246:
            raise CandidateRegistryError("Exact V5 246 selected system aliases differ")
        sides[side] = {
            "profile_id": profile["profile_id"],
            "registry_sha256": prior.historical._sha(files[side]),
            "base_registry_sha256": profile["base_registry_sha256"],
            "component_count": 40,
            "source_cohort_count": 26,
            "scenario_source_component_count": 27,
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
        "v4_portfolio_verifier_sha256": diagnostic["v4_verifier_sha256"],
        "v4_independent_review_sha256": diagnostic["v4_review_sha256"],
        "reviewed_native_versions": 475,
        "sides": sides,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "grants_or_collections_created": False,
        "limits": [
            "A/B are routing profiles, not new Clean/Messy audit engagements.",
            "GOVAPP and SEC005-operated are future fictional selected sources only.",
            "SEC005 November Security recheck is AS-P008 self-review, not independent assurance.",
            "V4 REC003 journals are inherited and excluded from business versions.",
            "No source-complete population, PBC, grant, collection, task or grade.",
        ],
    }


def write_candidate(repository: Path, private_repository: Path, destination: Path) -> dict:
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise CandidateRegistryError("Fresh V5 candidate destination required")
    prior.historical._private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".candidate-v5-", dir=destination.parent) as temp:
        stage = Path(temp)
        files = {}
        for side in "AB":
            path = stage / f"{side}.json"
            path.write_text(json.dumps(profiles[side]["manifest"], sort_keys=True, indent=2) + "\n")
            path.chmod(0o600)
            adapter = FederatedCompanyStore(path, profiles[side]["profile_id"])
            if adapter._manifest["components"] != profiles[side]["manifest"]["components"]:
                raise CandidateRegistryError("V5 federated adapter route differs")
            files[side] = path
        report = _report(diagnostic, profiles, files)
        report_path = stage / "REPORT.json"
        report_path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
        report_path.chmod(0o600)
        after = portfolio.verify_all(repository, private_repository=private_repository)
        if after["sources"] != diagnostic["sources"]:
            raise CandidateRegistryError("Reviewed V5 source portfolio changed during build")
        os.rename(stage, destination)
    return verify_candidate(destination, repository, private_repository)


def verify_candidate(destination: Path, repository: Path, private_repository: Path) -> dict:
    root = Path(destination).absolute()
    prior.historical._private(root, directory=True)
    if {path.name for path in root.iterdir()} != {"A.json", "B.json", "REPORT.json"}:
        raise CandidateRegistryError("Exact three-file V5 candidate required")
    before = {
        name: prior.historical._private(root / name) for name in ("A.json", "B.json", "REPORT.json")
    }
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    files = {side: root / f"{side}.json" for side in "AB"}
    for side in "AB":
        if prior.historical._json(files[side]) != profiles[side]["manifest"]:
            raise CandidateRegistryError("V5 candidate manifest differs")
        FederatedCompanyStore(files[side], profiles[side]["profile_id"])
    report = prior.historical._json(root / "REPORT.json")
    if report != _report(diagnostic, profiles, files):
        raise CandidateRegistryError("V5 candidate report differs")
    if {name: prior.historical._private(root / name) for name in before} != before:
        raise CandidateRegistryError("V5 candidate changed during verification")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    result = (
        write_candidate(args.repository, args.private_repository, args.destination)
        if args.action == "create"
        else verify_candidate(args.destination, args.repository, args.private_repository)
    )
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "reviewed_native_versions": result["reviewed_native_versions"],
                "component_count": result["sides"]["A"]["component_count"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
