"""V14 partial candidate routing for the selected POL004 procedure fixture."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from . import fictional_2027_candidate_registry_v13 as prior
from . import fictional_2027_source_portfolio_v14 as portfolio
from .company_federation import FederatedCompanyStore
from .fictional_2027_candidate_registry import (
    QUALIFICATION,
    REGISTRY_SCHEMA,
    CandidateRegistryError,
    _json,
    _private,
    _sha,
)
from .fictional_2027_candidate_registry_v4 import _systems
from .fictional_2027_source_portfolio_v4 import _frozen_rows, _no_sidecars

SCHEMA = "SH_FICTIONAL_2027_PARTIAL_CANDIDATE_REGISTRY_DIAGNOSTIC_V14"


def _component_for_source(private: Path, scenario: str, row: dict) -> tuple[dict, dict]:
    """Route one reviewed pending POL004 procedure source without a collection grant."""
    run = private / portfolio.BASE / portfolio.PROCEDURE_FOLDER / portfolio.PROCEDURE_RUN
    database = run / "company.sqlite3"
    _private(run, directory=True)
    db_before = _private(database)
    _no_sidecars(database)
    receipt_path = run / "SOURCE_RECEIPT.json"
    receipt_before = _private(receipt_path)
    receipt = _json(receipt_path)
    branch = portfolio.PROCEDURE_BRANCHES[("CLEAN", "MESSY").index(scenario)]
    if (
        receipt.get("branch_ids", {}).get(scenario) != branch
        or db_before[-1] != portfolio.PROCEDURE_DB_SHA
        or receipt_before[-1] != portfolio.PROCEDURE_RECEIPT_SHA
        or row.get("database_sha256", {}).get("native") != db_before[-1]
    ):
        raise CandidateRegistryError("POL004 procedure reviewed route bytes differ")
    native, systems, journals = _frozen_rows(database)
    if (
        sorted(native)
        != sorted(
            ("SABLE-HARBOR-REFERENCE", selected, count)
            for selected, count in zip(
                portfolio.PROCEDURE_BRANCHES, portfolio.PROCEDURE_COUNTS, strict=True
            )
        )
        or sorted(systems)
        != sorted(
            ("SABLE-HARBOR-REFERENCE", selected, portfolio.PROCEDURE_SYSTEMS)
            for selected in portfolio.PROCEDURE_BRANCHES
        )
        or any(journals.values())
    ):
        raise CandidateRegistryError("POL004 procedure physical route/journal gate differs")
    _no_sidecars(database)
    if _private(database) != db_before or _private(receipt_path) != receipt_before:
        raise CandidateRegistryError("POL004 procedure source changed during routing read")
    component = {
        "root": str(run),
        "company": "SABLE-HARBOR-REFERENCE",
        "branch": branch,
        "namespace": "F27POL004PROCEDURE",
        "systems": sorted(
            {
                system
                for company, selected, system in _systems(database)
                if company == "SABLE-HARBOR-REFERENCE" and selected == branch
            }
        ),
    }
    if component["systems"] != [
        "approval_gate",
        "challenge",
        "correction",
        "due_trigger",
        "exception_review",
        "execution_trace",
        "procedure_candidate",
        "result_register",
    ]:
        raise CandidateRegistryError("POL004 procedure exact system aliases differ")
    pin = {
        "source": "pol004procedure",
        "ledger": "native",
        "source_review_sha256": portfolio.PROCEDURE_REVIEW_SHA,
        "manifest_sha256": portfolio.PROCEDURE_MANIFEST_SHA,
        "receipt_sha256": portfolio.PROCEDURE_RECEIPT_SHA,
        "database_sha256": db_before[-1],
        "physical_company": "SABLE-HARBOR-REFERENCE",
        "physical_branch": branch,
        "system_count": portfolio.PROCEDURE_SYSTEMS,
        "inherited_audit_journals": {key: 0 for key in portfolio.JOURNALS},
    }
    return component, pin


def candidate_profiles(repository: Path, private_repository: Path) -> tuple[dict, dict]:
    """Retain the accepted V13 profile prefix and append one POL004 component."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    reviewed = portfolio._v13_review(private)
    old_diagnostic, old_profiles = prior.candidate_profiles(repository, private)
    if old_diagnostic != reviewed[0] or (
        old_diagnostic.get("source_count"),
        old_diagnostic.get("native_versions"),
        old_diagnostic.get("source_component_count"),
    ) != (34, 780, 35):
        raise CandidateRegistryError("Exact reviewed V13 source prefix differs")
    reviewed_candidates = reviewed[1]
    for side in "AB":
        old = old_profiles[side]
        selected = reviewed_candidates["REPORT.json"]["sides"][side]
        if (
            old["manifest"] != reviewed_candidates[f"{side}.json"]
            or old["source_pins"] != selected["source_pins"]
            or old["profile_id"] != selected["profile_id"]
            or old["base_registry_sha256"] != selected["base_registry_sha256"]
            or selected["registry_sha256"] != portfolio.V13_CANDIDATE_SHA[f"{side}.json"]
            or (selected["component_count"], selected["scenario_source_component_count"])
            != (48, 35)
            or selected["system_alias_count"] != 297
        ):
            raise CandidateRegistryError("Exact reviewed V13 candidate row/pin differs")
    diagnostic = portfolio.verify_all(repository, private_repository=private)
    if diagnostic["sources"][:34] != old_diagnostic["sources"] or (
        diagnostic.get("source_count"),
        diagnostic.get("native_versions"),
        diagnostic.get("source_component_count"),
    ) != (35, 796, 36):
        raise CandidateRegistryError("Exact reviewed V14 source extension differs")
    sources = {row["source"]: row for row in diagnostic["sources"]}
    if len(sources) != 35 or sources["pol004procedure"] != diagnostic["sources"][-1]:
        raise CandidateRegistryError("Exact V14 POL004 procedure identity differs")
    profiles = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        old = old_profiles[side]
        components = dict(old["manifest"]["components"])
        pins = list(old["source_pins"])
        if len(components) != 48 or len(pins) != 35:
            raise CandidateRegistryError("Historical V13 routing denominator differs")
        component, pin = _component_for_source(private, scenario, sources["pol004procedure"])
        name = "scenario-pol004procedure"
        if name in components:
            raise CandidateRegistryError("V14 POL004 procedure collision")
        components[name] = component
        pins.append(pin)
        if len(components) != 49 or len(pins) != 36:
            raise CandidateRegistryError("Exact V14 component/pin roster differs")
        profile_id = "fictional27-candidate-v14-" + scenario.lower()
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
            "prior_system_alias_count": selected["system_alias_count"],
        }
    if portfolio._v13_review(private) != reviewed:
        raise CandidateRegistryError("Reviewed V13 candidate prefix changed during routing")
    return diagnostic, profiles


def _report(diagnostic: dict, profiles: dict, files: dict) -> dict:
    sides = {}
    for side in "AB":
        profile = profiles[side]
        components = profile["manifest"]["components"]
        aliases = sum(len(item["systems"]) for item in components.values())
        if (
            aliases != profile["prior_system_alias_count"] + portfolio.PROCEDURE_SYSTEMS
            or aliases != 305
        ):
            raise CandidateRegistryError("Derived V14 component aliases differ")
        sides[side] = {
            "profile_id": profile["profile_id"],
            "registry_sha256": _sha(files[side]),
            "base_registry_sha256": profile["base_registry_sha256"],
            "component_count": 49,
            "source_cohort_count": 35,
            "scenario_source_component_count": 36,
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
        "v13_portfolio_verifier_sha256": diagnostic["v13_verifier_sha256"],
        "v13_independent_review_sha256": diagnostic["v13_review_sha256"],
        "reviewed_native_versions": 796,
        "sides": sides,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "grants_or_collections_created": False,
        "limits": [
            "A/B are routing profiles, not new Clean/Messy audit engagements.",
            "POL004 adds one selected fictional local procedure trial per side; the 2026 "
            "enterprise policy remains OPEN and procedure authority pending.",
            "Messy missed interval and corrected false close retain an OPEN historical exception.",
            "The CC5.3 authored clause remains unsupported and unrun.",
            "2027 clocks are authored prospective events, not actual operation.",
            "REC003 inherited journals are excluded from business version counts.",
            "No source-complete population, fresh pair, grant, collection, task, Key or grade.",
        ],
    }


def write_candidate(repository: Path, private_repository: Path, destination: Path) -> dict:
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise CandidateRegistryError("Fresh V14 candidate destination required")
    _private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".candidate-v14-", dir=destination.parent) as name:
        stage = Path(name)
        files = {}
        for side in "AB":
            path = stage / f"{side}.json"
            path.write_text(json.dumps(profiles[side]["manifest"], sort_keys=True, indent=2) + "\n")
            path.chmod(0o600)
            adapter = FederatedCompanyStore(path, profiles[side]["profile_id"])
            if adapter._manifest["components"] != profiles[side]["manifest"]["components"]:
                raise CandidateRegistryError("V14 federated adapter route differs")
            files[side] = path
        report = _report(diagnostic, profiles, files)
        output = stage / "REPORT.json"
        output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
        output.chmod(0o600)
        if portfolio.verify_all(repository, private_repository=private_repository) != diagnostic:
            raise CandidateRegistryError("Reviewed V13 portfolio changed during build")
        os.rename(stage, destination)
    return verify_candidate(destination, repository, private_repository)


def verify_candidate(destination: Path, repository: Path, private_repository: Path) -> dict:
    root = Path(destination).absolute()
    _private(root, directory=True)
    if {path.name for path in root.iterdir()} != {"A.json", "B.json", "REPORT.json"}:
        raise CandidateRegistryError("Exact three-file V14 candidate required")
    before = {name: _private(root / name) for name in ("A.json", "B.json", "REPORT.json")}
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    files = {side: root / f"{side}.json" for side in "AB"}
    for side in "AB":
        if _json(files[side]) != profiles[side]["manifest"]:
            raise CandidateRegistryError("V14 candidate manifest differs")
        FederatedCompanyStore(files[side], profiles[side]["profile_id"])
    report = _json(root / "REPORT.json")
    if report != _report(diagnostic, profiles, files):
        raise CandidateRegistryError("V14 candidate report differs")
    if {name: _private(root / name) for name in before} != before:
        raise CandidateRegistryError("V14 candidate changed during verification")
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
            }
        )
    )


if __name__ == "__main__":
    main()
