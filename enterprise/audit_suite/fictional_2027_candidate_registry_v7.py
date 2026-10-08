"""Private partial V7 routing diagnostic, without a new audit engagement."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from . import fictional_2027_candidate_registry_v6 as prior
from . import fictional_2027_source_portfolio_v7 as portfolio
from .company_federation import FederatedCompanyStore
from .fictional_2027_candidate_registry import (
    QUALIFICATION,
    REGISTRY_SCHEMA,
    CandidateRegistryError,
    _json,
    _private,
    _sha,
)
from .fictional_2027_candidate_registry_v4 import _component_for_standard
from .fictional_2027_source_portfolio_v5 import AddedSource

SCHEMA = "SH_FICTIONAL_2027_PARTIAL_CANDIDATE_REGISTRY_DIAGNOSTIC_V7"
SEC_SOURCE = AddedSource(
    "sec003vuln",
    portfolio.SEC_FOLDER,
    portfolio.SEC_REVIEW,
    portfolio.SEC_REVIEW_SHA,
    portfolio.SEC_REVIEW_VERDICT,
    portfolio.SEC_MANIFEST_SHA,
    portfolio.SEC_RECEIPT_SHA,
    portfolio.SEC_DB_SHA,
    portfolio.SEC_BRANCHES,
    portfolio.SEC_COUNTS,
    portfolio.SEC_SYSTEMS,
)


def candidate_profiles(repository: Path, private_repository: Path) -> tuple[dict, dict]:
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    reviewed = portfolio._v6_review(private)
    old_diagnostic, old_profiles = prior.candidate_profiles(repository, private)
    if old_diagnostic != reviewed[0] or (
        old_diagnostic.get("source_count"),
        old_diagnostic.get("native_versions"),
        old_diagnostic.get("source_component_count"),
    ) != (27, 500, 28):
        raise CandidateRegistryError("Exact reviewed V6 source prefix differs")
    reviewed_candidates = reviewed[1]
    for side in "AB":
        old = old_profiles[side]
        selected = reviewed_candidates["REPORT.json"]["sides"][side]
        if (
            old["manifest"] != reviewed_candidates[f"{side}.json"]
            or old["source_pins"] != selected["source_pins"]
            or old["profile_id"] != selected["profile_id"]
            or old["base_registry_sha256"] != selected["base_registry_sha256"]
            or selected["registry_sha256"] != portfolio.V6_CANDIDATE_SHA[f"{side}.json"]
            or (selected["component_count"], selected["scenario_source_component_count"])
            != (41, 28)
            or selected["system_alias_count"] != 255
        ):
            raise CandidateRegistryError("Exact reviewed V6 candidate row/pin differs")
    diagnostic = portfolio.verify_all(repository, private_repository=private)
    if diagnostic["sources"][:27] != old_diagnostic["sources"] or (
        diagnostic.get("source_count"),
        diagnostic.get("native_versions"),
        diagnostic.get("source_component_count"),
    ) != (28, 529, 29):
        raise CandidateRegistryError("Exact reviewed V7 source extension differs")
    sources = {row["source"]: row for row in diagnostic["sources"]}
    if len(sources) != 28 or sources["sec003vuln"] != diagnostic["sources"][-1]:
        raise CandidateRegistryError("Exact V7 source identity differs")
    profiles = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        old = old_profiles[side]
        components = dict(old["manifest"]["components"])
        pins = list(old["source_pins"])
        if len(components) != 41 or len(pins) != 28:
            raise CandidateRegistryError("Historical V6 routing denominator differs")
        component, pin = _component_for_standard(
            private, SEC_SOURCE, scenario, sources["sec003vuln"]
        )
        name = "scenario-sec003vuln"
        if name in components:
            raise CandidateRegistryError("V7 SEC003 component collision")
        components[name] = component
        pins.append(pin)
        if len(components) != 42 or len(pins) != 29:
            raise CandidateRegistryError("Exact V7 component/pin roster differs")
        profile_id = "fictional27-candidate-v7-" + scenario.lower()
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
        profiles[side] = {
            "manifest": manifest,
            "profile_id": profile_id,
            "source_pins": pins,
            "base_registry_sha256": old["base_registry_sha256"],
        }
    if portfolio._v6_review(private) != reviewed:
        raise CandidateRegistryError("Reviewed V6 candidate prefix changed during routing")
    return diagnostic, profiles


def _report(diagnostic: dict, profiles: dict, files: dict) -> dict:
    sides = {}
    for side in "AB":
        profile = profiles[side]
        components = profile["manifest"]["components"]
        aliases = sum(len(item["systems"]) for item in components.values())
        if aliases != 265:
            raise CandidateRegistryError("Exact V7 265 selected aliases differ")
        sides[side] = {
            "profile_id": profile["profile_id"],
            "registry_sha256": _sha(files[side]),
            "base_registry_sha256": profile["base_registry_sha256"],
            "component_count": 42,
            "source_cohort_count": 28,
            "scenario_source_component_count": 29,
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
        "v6_portfolio_verifier_sha256": diagnostic["v6_verifier_sha256"],
        "v6_independent_review_sha256": diagnostic["v6_review_sha256"],
        "reviewed_native_versions": 529,
        "sides": sides,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "grants_or_collections_created": False,
        "limits": [
            "A/B are routing profiles, not new Clean/Messy audit engagements.",
            "SEC003 is a selected fictional data-only vulnerability source with an open Messy "
            "historical exception; CC7.1/CC5.2 remain unsupported authored clauses.",
            "AS-P008's November recheck is self-review, not independent assurance.",
            "REC003 inherited journals are excluded from business version counts.",
            "No source-complete population, grant, collection, task, Key or grade.",
        ],
    }


def write_candidate(repository: Path, private_repository: Path, destination: Path) -> dict:
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise CandidateRegistryError("Fresh V7 candidate destination required")
    _private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".candidate-v7-", dir=destination.parent) as name:
        stage = Path(name)
        files = {}
        for side in "AB":
            path = stage / f"{side}.json"
            path.write_text(json.dumps(profiles[side]["manifest"], sort_keys=True, indent=2) + "\n")
            path.chmod(0o600)
            adapter = FederatedCompanyStore(path, profiles[side]["profile_id"])
            if adapter._manifest["components"] != profiles[side]["manifest"]["components"]:
                raise CandidateRegistryError("V7 federated adapter route differs")
            files[side] = path
        report = _report(diagnostic, profiles, files)
        output = stage / "REPORT.json"
        output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
        output.chmod(0o600)
        if portfolio.verify_all(repository, private_repository=private_repository) != diagnostic:
            raise CandidateRegistryError("Reviewed V7 portfolio changed during build")
        os.rename(stage, destination)
    return verify_candidate(destination, repository, private_repository)


def verify_candidate(destination: Path, repository: Path, private_repository: Path) -> dict:
    root = Path(destination).absolute()
    _private(root, directory=True)
    if {path.name for path in root.iterdir()} != {"A.json", "B.json", "REPORT.json"}:
        raise CandidateRegistryError("Exact three-file V7 candidate required")
    before = {name: _private(root / name) for name in ("A.json", "B.json", "REPORT.json")}
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    files = {side: root / f"{side}.json" for side in "AB"}
    for side in "AB":
        if _json(files[side]) != profiles[side]["manifest"]:
            raise CandidateRegistryError("V7 candidate manifest differs")
        FederatedCompanyStore(files[side], profiles[side]["profile_id"])
    report = _json(root / "REPORT.json")
    if report != _report(diagnostic, profiles, files):
        raise CandidateRegistryError("V7 candidate report differs")
    if {name: _private(root / name) for name in before} != before:
        raise CandidateRegistryError("V7 candidate changed during verification")
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
