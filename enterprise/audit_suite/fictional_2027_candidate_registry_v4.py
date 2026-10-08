"""Private partial V4 routing diagnostic for 24 reviewed source cohorts."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import tempfile
from pathlib import Path

from . import fictional_2027_candidate_registry as historical
from . import fictional_2027_candidate_registry_v3 as prior
from . import fictional_2027_source_portfolio_v4 as portfolio
from .company_federation import FederatedCompanyStore

CandidateRegistryError = historical.CandidateRegistryError
SCHEMA = "SH_FICTIONAL_2027_PARTIAL_CANDIDATE_REGISTRY_DIAGNOSTIC_V4"


def _component_for_rec003(private: Path, side: str, row: dict) -> tuple[dict, dict]:
    """Resolve sealed snapshot://A/B only at the private routing boundary."""
    run = private / portfolio.BASE / portfolio.REC_FOLDER / portfolio.REC_RUN
    routes_path = run / "ROUTES.json"
    db = run / side / "company.sqlite3"
    for directory in (run, db.parent):
        historical._private(directory, directory=True)
    route_before, db_before = historical._private(routes_path), historical._private(db)
    portfolio._no_sidecars(db)
    route = historical._json(routes_path)["sides"][side]
    branch = f"local-data-quality-{side.lower()}"
    if (
        route.get("source_store_id") != "scenario-rec003-dq"
        or route.get("root_locator") != "snapshot://" + side
        or route.get("physical_company") != "SABLEHARBOR"
        or route.get("physical_branch") != branch
        or route.get("namespace") != "F27REC003DQ"
        or route.get("systems") != list(portfolio.rec.SYSTEMS)
        or route_before[-1] != portfolio.REC_ROUTES_SHA256
        or db_before[-1] != portfolio.REC_DATABASES[side]
        or row.get("database_sha256", {}).get(side) != db_before[-1]
        or row.get("routes_sha256") != route_before[-1]
    ):
        raise CandidateRegistryError("Reviewed REC003 portable route differs")
    native, systems, journals = portfolio._frozen_rows(db)
    if (
        native != [("SABLEHARBOR", branch, 11)]
        or systems != [("SABLEHARBOR", branch, 6)]
        or journals != portfolio.JOURNALS
    ):
        raise CandidateRegistryError("REC003 reviewed snapshot/journal baseline differs")
    portfolio._no_sidecars(db)
    if historical._private(routes_path) != route_before or historical._private(db) != db_before:
        raise CandidateRegistryError("REC003 snapshot changed during routing read")
    component = {
        "root": str(db.parent),
        "company": "SABLEHARBOR",
        "branch": branch,
        "namespace": "F27REC003DQ",
        "systems": list(portfolio.rec.SYSTEMS),
    }
    pin = {
        "source": "rec003",
        "ledger": side,
        "source_review_sha256": portfolio.REC_REVIEW_SHA256,
        "manifest_sha256": portfolio.REC_MANIFEST_SHA256,
        "receipt_sha256": portfolio.REC_RECEIPT_SHA256,
        "routes_sha256": portfolio.REC_ROUTES_SHA256,
        "root_locator": "snapshot://" + side,
        "database_sha256": db_before[-1],
        "physical_company": "SABLEHARBOR",
        "physical_branch": branch,
        "system_count": 6,
        "inherited_audit_journals": portfolio.JOURNALS,
    }
    return component, pin


def _component_for_standard(
    private: Path, source: portfolio.AddedSource, scenario: str, row: dict
) -> tuple[dict, dict]:
    run = private / portfolio.BASE / source.folder / source.run
    db = run / "company.sqlite3"
    historical._private(run, directory=True)
    db_before = historical._private(db)
    portfolio._no_sidecars(db)
    receipt_path = run / "RECEIPT.json"
    receipt_before = historical._private(receipt_path)
    receipt = historical._json(receipt_path)
    branch = source.branches[("CLEAN", "MESSY").index(scenario)]
    if (
        receipt.get("branches", {}).get(scenario) != branch
        or db_before[-1] != source.database_sha256
        or receipt_before[-1] != source.receipt_sha256
        or row.get("database_sha256", {}).get("native") != db_before[-1]
    ):
        raise CandidateRegistryError(f"{source.key} reviewed route bytes differ")
    native, systems, journals = portfolio._frozen_rows(db)
    if (
        sorted(native)
        != sorted(
            ("SABLE-HARBOR-REFERENCE", b, count)
            for b, count in zip(source.branches, source.counts, strict=True)
        )
        or sorted(systems)
        != sorted(("SABLE-HARBOR-REFERENCE", b, source.systems) for b in source.branches)
        or any(journals.values())
    ):
        raise CandidateRegistryError(f"{source.key} physical route/zero-journal gate differs")
    portfolio._no_sidecars(db)
    if historical._private(db) != db_before or historical._private(receipt_path) != receipt_before:
        raise CandidateRegistryError(f"{source.key} changed during routing read")
    component = {
        "root": str(run),
        "company": "SABLE-HARBOR-REFERENCE",
        "branch": branch,
        "namespace": "F27" + source.key.upper(),
        "systems": sorted(
            {
                system
                for company, selected, system in _systems(db)
                if company == "SABLE-HARBOR-REFERENCE" and selected == branch
            }
        ),
    }
    if len(component["systems"]) != source.systems:
        raise CandidateRegistryError(f"{source.key} exact system aliases differ")
    pin = {
        "source": source.key,
        "ledger": "native",
        "source_review_sha256": source.review_sha256,
        "manifest_sha256": source.manifest_sha256,
        "receipt_sha256": source.receipt_sha256,
        "database_sha256": db_before[-1],
        "physical_company": "SABLE-HARBOR-REFERENCE",
        "physical_branch": branch,
        "system_count": source.systems,
        "inherited_audit_journals": {k: 0 for k in portfolio.JOURNALS},
    }
    return component, pin


def _systems(path: Path) -> list[tuple]:
    with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        return db.execute(
            "SELECT company,branch,system FROM systems ORDER BY company,branch,system"
        ).fetchall()


def candidate_profiles(repository: Path, private_repository: Path) -> tuple[dict, dict]:
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    old_diagnostic, old_profiles = prior.candidate_profiles(repository, private_repository)
    diagnostic = portfolio.verify_all(repository, private_repository=private_repository)
    if (
        (
            old_diagnostic["source_count"],
            old_diagnostic["native_versions"],
            old_diagnostic["source_component_count"],
        )
        != (21, 358, 22)
        or diagnostic["sources"][:21] != old_diagnostic["sources"]
        or (
            diagnostic["source_count"],
            diagnostic["native_versions"],
            diagnostic["source_component_count"],
        )
        != (24, 401, 25)
    ):
        raise CandidateRegistryError("Reviewed V3 prefix or V4 roster differs")
    reviewed = {row["source"]: row for row in diagnostic["sources"]}
    profiles = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        old = old_profiles[side]
        components = dict(old["manifest"]["components"])
        pins = list(old["source_pins"])
        if len(components) != 35 or len(pins) != 22:
            raise CandidateRegistryError("Historical V3 candidate roster differs")
        rec_component, rec_pin = _component_for_rec003(private_repository, side, reviewed["rec003"])
        components["scenario-rec003-dq"] = rec_component
        pins.append(rec_pin)
        for source in portfolio.STANDARD:
            component, pin = _component_for_standard(
                private_repository, source, scenario, reviewed[source.key]
            )
            name = "scenario-" + source.key
            if name in components:
                raise CandidateRegistryError("Successor source component collision")
            components[name] = component
            pins.append(pin)
        if len(components) != 38 or len(pins) != 25:
            raise CandidateRegistryError("Exact 38-component/25-pin partial roster differs")
        profile_id = "fictional27-candidate-v4-" + scenario.lower()
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
        if aliases != 227:
            raise CandidateRegistryError("Exact 227 system aliases differ")
        sides[side] = {
            "profile_id": profile["profile_id"],
            "registry_sha256": historical._sha(files[side]),
            "base_registry_sha256": profile["base_registry_sha256"],
            "component_count": 38,
            "source_cohort_count": 24,
            "scenario_source_component_count": 25,
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
        "v3_portfolio_verifier_sha256": diagnostic["v3_verifier_sha256"],
        "reviewed_native_versions": 401,
        "sides": sides,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "grants_or_collections_created": False,
        "limits": [
            "A/B are routing profiles, not new Clean/Messy audit engagements.",
            "REC003 has one separately pinned snapshot per profile.",
            "REC003 inherited journals (12/22/25) are excluded from native versions.",
            "Private absolute roots resolve portable snapshot:// locators only for routing.",
            "No source-complete population, PBC, grant, collection, task or grade.",
        ],
    }


def write_candidate(repository: Path, private_repository: Path, destination: Path) -> dict:
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise CandidateRegistryError("Fresh V4 successor destination required")
    historical._private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".candidate-v4-", dir=destination.parent) as temp:
        stage = Path(temp)
        files = {}
        for side in "AB":
            path = stage / f"{side}.json"
            path.write_text(json.dumps(profiles[side]["manifest"], sort_keys=True, indent=2) + "\n")
            path.chmod(0o600)
            adapter = FederatedCompanyStore(path, profiles[side]["profile_id"])
            if adapter._manifest["components"] != profiles[side]["manifest"]["components"]:
                raise CandidateRegistryError("V4 adapter route differs")
            files[side] = path
        report = _report(diagnostic, profiles, files)
        report_path = stage / "REPORT.json"
        report_path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
        report_path.chmod(0o600)
        after = portfolio.verify_all(repository, private_repository=private_repository)
        if after["sources"] != diagnostic["sources"]:
            raise CandidateRegistryError("Reviewed V4 source portfolio changed during build")
        os.rename(stage, destination)
    return verify_candidate(destination, repository, private_repository)


def verify_candidate(destination: Path, repository: Path, private_repository: Path) -> dict:
    root = Path(destination).absolute()
    historical._private(root, directory=True)
    if {path.name for path in root.iterdir()} != {"A.json", "B.json", "REPORT.json"}:
        raise CandidateRegistryError("Exact three-file V4 diagnostic required")
    before = {
        name: historical._private(root / name) for name in ("A.json", "B.json", "REPORT.json")
    }
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    files = {side: root / f"{side}.json" for side in "AB"}
    for side in "AB":
        if historical._json(files[side]) != profiles[side]["manifest"]:
            raise CandidateRegistryError("V4 candidate manifest differs")
        FederatedCompanyStore(files[side], profiles[side]["profile_id"])
    report = historical._json(root / "REPORT.json")
    if report != _report(diagnostic, profiles, files):
        raise CandidateRegistryError("V4 candidate report differs")
    if {name: historical._private(root / name) for name in before} != before:
        raise CandidateRegistryError("V4 candidate changed during verification")
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
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
