"""Private partial V9 LEG001 routing diagnostic, without a new audit engagement."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from . import fictional_2027_candidate_registry_v8 as prior
from . import fictional_2027_source_portfolio_v9 as portfolio
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

SCHEMA = "SH_FICTIONAL_2027_PARTIAL_CANDIDATE_REGISTRY_DIAGNOSTIC_V9"
LEG_SOURCE = AddedSource(
    "leg001docket",
    portfolio.LEG_FOLDER,
    portfolio.LEG_REVIEW,
    portfolio.LEG_REVIEW_SHA,
    portfolio.LEG_REVIEW_VERDICT,
    portfolio.LEG_MANIFEST_SHA,
    portfolio.LEG_RECEIPT_SHA,
    portfolio.LEG_DB_SHA,
    portfolio.LEG_BRANCHES,
    portfolio.LEG_COUNTS,
    portfolio.LEG_SYSTEMS,
)


def candidate_profiles(repository: Path, private_repository: Path) -> tuple[dict, dict]:
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    reviewed = portfolio._v8_review(private)
    old_diagnostic, old_profiles = prior.candidate_profiles(repository, private)
    if old_diagnostic != reviewed[0] or (
        old_diagnostic.get("source_count"),
        old_diagnostic.get("native_versions"),
        old_diagnostic.get("source_component_count"),
    ) != (29, 560, 30):
        raise CandidateRegistryError("Exact reviewed V8 source prefix differs")
    reviewed_candidates = reviewed[1]
    for side in "AB":
        old = old_profiles[side]
        selected = reviewed_candidates["REPORT.json"]["sides"][side]
        if (
            old["manifest"] != reviewed_candidates[f"{side}.json"]
            or old["source_pins"] != selected["source_pins"]
            or old["profile_id"] != selected["profile_id"]
            or old["base_registry_sha256"] != selected["base_registry_sha256"]
            or selected["registry_sha256"] != portfolio.V8_CANDIDATE_SHA[f"{side}.json"]
            or (selected["component_count"], selected["scenario_source_component_count"])
            != (43, 30)
            or selected["system_alias_count"] != 273
        ):
            raise CandidateRegistryError("Exact reviewed V8 candidate row/pin differs")
    diagnostic = portfolio.verify_all(repository, private_repository=private)
    if diagnostic["sources"][:29] != old_diagnostic["sources"] or (
        diagnostic.get("source_count"),
        diagnostic.get("native_versions"),
        diagnostic.get("source_component_count"),
    ) != (30, 660, 31):
        raise CandidateRegistryError("Exact reviewed V9 source extension differs")
    sources = {row["source"]: row for row in diagnostic["sources"]}
    if len(sources) != 30 or sources["leg001docket"] != diagnostic["sources"][-1]:
        raise CandidateRegistryError("Exact V9 LEG001 source identity differs")
    profiles = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        old = old_profiles[side]
        components = dict(old["manifest"]["components"])
        pins = list(old["source_pins"])
        if len(components) != 43 or len(pins) != 30:
            raise CandidateRegistryError("Historical V8 routing denominator differs")
        component, pin = _component_for_standard(
            private, LEG_SOURCE, scenario, sources["leg001docket"]
        )
        name = "scenario-leg001docket"
        if name in components:
            raise CandidateRegistryError("V9 LEG001 component collision")
        components[name] = component
        pins.append(pin)
        if len(components) != 44 or len(pins) != 31:
            raise CandidateRegistryError("Exact V9 component/pin roster differs")
        profile_id = "fictional27-candidate-v9-" + scenario.lower()
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
            "prior_system_alias_count": reviewed_candidates["REPORT.json"]["sides"][side][
                "system_alias_count"
            ],
        }
    if portfolio._v8_review(private) != reviewed:
        raise CandidateRegistryError("Reviewed V8 candidate prefix changed during routing")
    return diagnostic, profiles


def _report(diagnostic: dict, profiles: dict, files: dict) -> dict:
    sides = {}
    for side in "AB":
        profile = profiles[side]
        components = profile["manifest"]["components"]
        aliases = sum(len(item["systems"]) for item in components.values())
        if aliases != profile["prior_system_alias_count"] + portfolio.LEG_SYSTEMS:
            raise CandidateRegistryError("Derived V9 selected aliases differ")
        sides[side] = {
            "profile_id": profile["profile_id"],
            "registry_sha256": _sha(files[side]),
            "base_registry_sha256": profile["base_registry_sha256"],
            "component_count": 44,
            "source_cohort_count": 30,
            "scenario_source_component_count": 31,
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
        "v8_portfolio_verifier_sha256": diagnostic["v8_verifier_sha256"],
        "v8_independent_review_sha256": diagnostic["v8_review_sha256"],
        "reviewed_native_versions": 660,
        "sides": sides,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "grants_or_collections_created": False,
        "limits": [
            "A/B are routing profiles, not new Clean/Messy audit engagements.",
            "LEG001 adds one fictional selected-chain counsel docket; "
            "real legal status is undecided.",
            "Messy BA flowdown and provider support-omission exceptions remain OPEN.",
            "Sixty-six authored LEG001 routes per side remain unsupported and unaudited.",
            "REC003 inherited journals are excluded from business version counts.",
            "No source-complete population, grant, collection, task, Key or grade.",
        ],
    }


def write_candidate(repository: Path, private_repository: Path, destination: Path) -> dict:
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise CandidateRegistryError("Fresh V9 candidate destination required")
    _private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".candidate-v9-", dir=destination.parent) as name:
        stage = Path(name)
        files = {}
        for side in "AB":
            path = stage / f"{side}.json"
            path.write_text(json.dumps(profiles[side]["manifest"], sort_keys=True, indent=2) + "\n")
            path.chmod(0o600)
            adapter = FederatedCompanyStore(path, profiles[side]["profile_id"])
            if adapter._manifest["components"] != profiles[side]["manifest"]["components"]:
                raise CandidateRegistryError("V9 federated adapter route differs")
            files[side] = path
        report = _report(diagnostic, profiles, files)
        output = stage / "REPORT.json"
        output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
        output.chmod(0o600)
        if portfolio.verify_all(repository, private_repository=private_repository) != diagnostic:
            raise CandidateRegistryError("Reviewed V9 portfolio changed during build")
        os.rename(stage, destination)
    return verify_candidate(destination, repository, private_repository)


def verify_candidate(destination: Path, repository: Path, private_repository: Path) -> dict:
    root = Path(destination).absolute()
    _private(root, directory=True)
    if {path.name for path in root.iterdir()} != {"A.json", "B.json", "REPORT.json"}:
        raise CandidateRegistryError("Exact three-file V9 candidate required")
    before = {name: _private(root / name) for name in ("A.json", "B.json", "REPORT.json")}
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    files = {side: root / f"{side}.json" for side in "AB"}
    for side in "AB":
        if _json(files[side]) != profiles[side]["manifest"]:
            raise CandidateRegistryError("V9 candidate manifest differs")
        FederatedCompanyStore(files[side], profiles[side]["profile_id"])
    report = _json(root / "REPORT.json")
    if report != _report(diagnostic, profiles, files):
        raise CandidateRegistryError("V9 candidate report differs")
    if {name: _private(root / name) for name in before} != before:
        raise CandidateRegistryError("V9 candidate changed during verification")
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
