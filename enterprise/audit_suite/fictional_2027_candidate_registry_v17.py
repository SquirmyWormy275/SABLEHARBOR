"""V17 partial candidate routing for reviewed ENG005 and GOV oversight."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from . import fictional_2027_source_portfolio_v17 as portfolio
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

SCHEMA = "SH_FICTIONAL_2027_PARTIAL_CANDIDATE_REGISTRY_DIAGNOSTIC_V17"
ALIASES = {
    "eng005operating": [
        "change_application",
        "change_approval",
        "change_recovery",
        "change_release",
        "change_request",
        "change_review",
        "change_risk",
        "change_test",
        "change_verification",
        "exception_register",
    ],
    "govoversight": [
        "action_register",
        "audit_committee_packet",
        "charter_register",
        "committee_note",
        "committee_roster",
        "conflict_questionnaire",
        "eligibility_review",
        "governance_exception",
        "secretariat_discovery",
        "secretariat_intake",
        "secretariat_reconciliation",
    ],
}
NAMESPACES = {"eng005operating": "F27ENG005OPERATING", "govoversight": "F27GOVOVERSIGHT"}


def _component(private: Path, scenario: str, selected: dict, row: dict) -> tuple[dict, dict]:
    """Route a reviewed private original without creating access or audit state."""
    module = selected["module"]
    run = private / portfolio.BASE / selected["folder"] / "main-run-v1"
    database = run / "company.sqlite3"
    receipt_path = run / "RECEIPT.json"
    _private(run, directory=True)
    before = _private(database)
    receipt_before = _private(receipt_path)
    _no_sidecars(database)
    receipt = _json(receipt_path)
    branch = module.BRANCHES[scenario]
    if (
        before[-1] != selected["db_sha"]
        or receipt_before[-1] != selected["receipt_sha"]
        or row.get("database_sha256") != {"native": before[-1]}
        or row.get("branch_versions", {}).get(branch)
        != selected["counts"][("CLEAN", "MESSY").index(scenario)]
        or row.get("ledger_system_counts") != {"native": selected["systems"]}
        or row.get("source_complete") is not False
        or row.get("audit_task_credit") is not False
        or receipt.get("branches", {}).get(scenario) != branch
    ):
        raise CandidateRegistryError("Selected reviewed source route differs")
    native, systems, journals = _frozen_rows(database)
    if (
        sorted(native)
        != sorted(
            (module.COMPANY, value, count)
            for value, count in zip(module.BRANCHES.values(), selected["counts"], strict=True)
        )
        or sorted(systems)
        != sorted(
            (module.COMPANY, value, selected["systems"]) for value in module.BRANCHES.values()
        )
        or any(journals.values())
    ):
        raise CandidateRegistryError("Selected source physical route or journals differ")
    aliases = sorted(
        system
        for company, value, system in _systems(database)
        if company == module.COMPANY and value == branch
    )
    if aliases != ALIASES[selected["source"]]:
        raise CandidateRegistryError("Selected exact system aliases differ")
    _no_sidecars(database)
    if _private(database) != before or _private(receipt_path) != receipt_before:
        raise CandidateRegistryError("Selected source changed during routing read")
    component = {
        "root": str(run),
        "company": module.COMPANY,
        "branch": branch,
        "namespace": NAMESPACES[selected["source"]],
        "systems": aliases,
    }
    pin = {
        "source": selected["source"],
        "ledger": "native",
        "source_review_sha256": selected["review_sha"],
        "manifest_sha256": selected["manifest_sha"],
        "receipt_sha256": selected["receipt_sha"],
        "database_sha256": before[-1],
        "physical_company": module.COMPANY,
        "physical_branch": branch,
        "system_count": selected["systems"],
        "inherited_audit_journals": {name: 0 for name in portfolio.JOURNALS},
    }
    return component, pin


def candidate_profiles(repository: Path, private_repository: Path) -> tuple[dict, dict]:
    """Append only two routed sources to the exact reviewed V16 manifest/pins."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    old_report, old_candidates, reviewed_before = portfolio.reviewed_v16(repository, private)
    diagnostic = portfolio.verify_all(repository, private_repository=private)
    if (
        diagnostic["sources"][:37] != old_report["sources"]
        or (
            diagnostic.get("source_count"),
            diagnostic.get("native_versions"),
            diagnostic.get("source_component_count"),
        )
        != (39, 897, 40)
        or [row["source"] for row in diagnostic["sources"][-2:]]
        != [item["source"] for item in portfolio.SOURCES]
    ):
        raise CandidateRegistryError("Reviewed V16 source prefix or V17 extension differs")
    profiles = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        old_manifest = old_candidates[f"{side}.json"]
        old_side = old_candidates["REPORT.json"]["sides"][side]
        components = dict(old_manifest["components"])
        pins = list(old_side["source_pins"])
        if (
            len(components) != 51
            or len(pins) != 38
            or sum(len(component["systems"]) for component in components.values()) != 324
            or old_side["registry_sha256"] != portfolio.V16_CANDIDATE_SHA[f"{side}.json"]
        ):
            raise CandidateRegistryError("Reviewed V16 candidate denominator differs")
        for selected, row in zip(portfolio.SOURCES, diagnostic["sources"][-2:], strict=True):
            name = "scenario-" + selected["source"]
            if name in components or row["source"] != selected["source"]:
                raise CandidateRegistryError("V17 selected source collision")
            component, pin = _component(private, scenario, selected, row)
            components[name] = component
            pins.append(pin)
        if (
            len(components) != 53
            or len(pins) != 40
            or sum(len(component["systems"]) for component in components.values()) != 345
        ):
            raise CandidateRegistryError("Derived V17 component/pin/alias roster differs")
        profile_id = "fictional27-candidate-v17-" + scenario.lower()
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
            "base_registry_sha256": old_side["base_registry_sha256"],
        }
    if portfolio.reviewed_v16(repository, private)[2] != reviewed_before:
        raise CandidateRegistryError("Reviewed V16 bytes changed during routing")
    return diagnostic, profiles


def _report(diagnostic: dict, profiles: dict, files: dict) -> dict:
    sides = {}
    for side in "AB":
        profile = profiles[side]
        components = profile["manifest"]["components"]
        aliases = sum(len(item["systems"]) for item in components.values())
        if (len(components), len(profile["source_pins"]), aliases) != (53, 40, 345):
            raise CandidateRegistryError("V17 report component roster differs")
        sides[side] = {
            "profile_id": profile["profile_id"],
            "registry_sha256": _sha(files[side]),
            "base_registry_sha256": profile["base_registry_sha256"],
            "component_count": 53,
            "source_cohort_count": 39,
            "scenario_source_component_count": 40,
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
        "v16_portfolio_verifier_sha256": diagnostic["v16_verifier_sha256"],
        "v16_independent_review_sha256": diagnostic["v16_review_sha256"],
        "reviewed_native_versions": 897,
        "sides": sides,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "grants_or_collections_created": False,
        "limits": [
            "A/B are routing profiles, not new Clean/Messy audit engagements.",
            "ENG005 has no corporate emergency authority or real deployment; "
            "two Messy historical exceptions stay open.",
            "GOV selected committee cycle is not an actual Board meeting, "
            "adopted minutes or complete oversight population.",
            "GOV Messy governance and SEC003 exceptions remain OPEN; no independent "
            "assurance or authored CC1.2 satisfaction.",
            "No fresh pair, grant, collection, audit task credit, Key or grade.",
        ],
    }


def write_candidate(repository: Path, private_repository: Path, destination: Path) -> dict:
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise CandidateRegistryError("Fresh V17 candidate destination required")
    _private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".candidate-v17-", dir=destination.parent) as name:
        stage = Path(name)
        files = {}
        for side in "AB":
            path = stage / f"{side}.json"
            path.write_text(json.dumps(profiles[side]["manifest"], sort_keys=True, indent=2) + "\n")
            path.chmod(0o600)
            adapter = FederatedCompanyStore(path, profiles[side]["profile_id"])
            if adapter._manifest["components"] != profiles[side]["manifest"]["components"]:
                raise CandidateRegistryError("V17 federated adapter route differs")
            files[side] = path
        report = _report(diagnostic, profiles, files)
        output = stage / "REPORT.json"
        output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
        output.chmod(0o600)
        os.rename(stage, destination)
    return verify_candidate(destination, repository, private_repository)


def verify_candidate(destination: Path, repository: Path, private_repository: Path) -> dict:
    root = Path(destination).absolute()
    _private(root, directory=True)
    if {path.name for path in root.iterdir()} != {"A.json", "B.json", "REPORT.json"}:
        raise CandidateRegistryError("Exact three-file V17 candidate required")
    before = {name: _private(root / name) for name in ("A.json", "B.json", "REPORT.json")}
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    files = {side: root / f"{side}.json" for side in "AB"}
    for side in "AB":
        if _json(files[side]) != profiles[side]["manifest"]:
            raise CandidateRegistryError("V17 candidate manifest differs")
        FederatedCompanyStore(files[side], profiles[side]["profile_id"])
    report = _json(root / "REPORT.json")
    if report != _report(diagnostic, profiles, files):
        raise CandidateRegistryError("V17 candidate report differs")
    if {name: _private(root / name) for name in before} != before:
        raise CandidateRegistryError("V17 candidate changed during verification")
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
