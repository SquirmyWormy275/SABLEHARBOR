"""Disposable source-to-collector probe for the reviewed partial V3 portfolio.

Only ordinary-byte copies receive grants and collection journals. This is a
diagnostic of source access, not an audit engagement or an evidence population.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

from .company_federation import FederatedCompanyStore
from .company_store import CompanyStore, CompanyStoreError
from .fictional_2027_candidate_registry import CandidateRegistryError, _json, _private, _sha
from .fictional_2027_candidate_registry_v3 import candidate_profiles, verify_candidate
from .fictional_2027_collection_probe import _counts, _ordinary_copy

SCHEMA = "SH_FICTIONAL_2027_DISPOSABLE_COLLECTION_PROBE_V3"
PRINCIPAL = "F27-PROBE-V3-READER"
ENGAGEMENT = "F27-DISPOSABLE-PROBE-V3"
AS_OF = "2027-12-31T23:59:59+00:00"
REVIEWED_PACKAGE = "enterprise/generated/audit-suite/company-source-portfolio-v3-2026-09-29"
REVIEW_SHA256 = "19a182c9c79f6a128cbd6e2840bab7adc953e8a76c58392988e88cdca9ffe704"
PORTFOLIO_REPORT_SHA256 = "e868e937815350bc5d975d76c6cd00528e1931bdcdc40e8b408f06d1ceaa3ed3"
CANDIDATE_REPORT_SHA256 = "c62563c314baacbfee6c24e1dd6a981d406f7baf694dba7db8144b7329e8ba13"
IDENTITY = (
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


def _source_id(pin: dict) -> str:
    key = pin["source"]
    ledger = pin.get("ledger")
    if ledger not in (None, "native", "human", "service"):
        raise CandidateRegistryError("Unknown scenario source ledger")
    return (
        "scenario-"
        + key.replace("_", "-")
        + ("-" + ledger if ledger in ("human", "service") else "")
    )


def _no_sidecars(path: Path) -> None:
    if any(
        Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CandidateRegistryError("Company source has SQLite sidecar")


def _native(path: Path, component: dict) -> tuple[dict, str]:
    """Select one exact, frozen native version and hash the full business rows."""
    before = _private(path)
    _no_sidecars(path)
    with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CandidateRegistryError("Source integrity failed")
        systems = db.execute(
            "SELECT company,branch,system,owner FROM systems ORDER BY company,branch,system"
        ).fetchall()
        versions = db.execute(
            "SELECT company,branch,system,record,version,event_at,available_at,"
            "imported_at,origin,provenance,content,sha256,command_id,input_digest "
            "FROM versions ORDER BY company,branch,system,record,version"
        ).fetchall()
    if _private(path) != before or not versions:
        raise CandidateRegistryError("Frozen native source changed or is empty")
    business = {
        "systems": systems,
        "versions": [
            [*row[:10], hashlib.sha256(row[10]).hexdigest(), *row[11:]] for row in versions
        ],
    }
    digest = hashlib.sha256(
        json.dumps(business, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    selected = next(
        (
            row
            for row in versions
            if row[0] == component["company"]
            and row[1] == component["branch"]
            and row[2] in component["systems"]
        ),
        None,
    )
    if selected is None or hashlib.sha256(selected[10]).hexdigest() != selected[11]:
        raise CandidateRegistryError("Selected native version missing or damaged")
    ref = dict(zip(IDENTITY, (*selected[:5], selected[11], *selected[5:8]), strict=True))
    if ref["available_at"] > AS_OF:
        raise CandidateRegistryError("Selected source is future to probe clock")
    return ref, digest


def _component_rows(profile: dict) -> list[tuple[str, dict, dict]]:
    pins = profile["source_pins"]
    components = profile["manifest"]["components"]
    names = [_source_id(pin) for pin in pins]
    if len(pins) != 22 or len(set(names)) != 22 or len(components) != 35:
        raise CandidateRegistryError("Expected exact 22 scenario components")
    if {name for name in components if name.startswith("scenario-")} != set(names):
        raise CandidateRegistryError("Scenario source component roster differs")
    if {name for name in names if name.startswith("scenario-iam005-")} != {
        "scenario-iam005-human",
        "scenario-iam005-service",
    }:
        raise CandidateRegistryError("IAM human/service source split missing")
    return [(name, pin, components[name]) for name, pin in zip(names, pins, strict=True)]


def _journal(path: Path, ref: dict) -> dict:
    counts = _counts(path)
    if (counts["grants"], counts["collections"], counts["access_events"]) != (1, 1, 1):
        raise CandidateRegistryError("Disposable access journal denominator differs")
    _no_sidecars(path)
    with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        grant = db.execute(
            "SELECT principal,engagement,company,branch,system,active FROM grants"
        ).fetchone()
        event = db.execute(
            "SELECT principal,engagement,company,branch,system,active FROM access_events"
        ).fetchone()
        receipt = json.loads(db.execute("SELECT receipt FROM collections").fetchone()[0])
    expected = (PRINCIPAL, ENGAGEMENT, ref["company"], ref["branch"], ref["system"], 1)
    if (
        grant != expected
        or event != expected
        or any(receipt["source"][key] != ref[key] for key in IDENTITY)
    ):
        raise CandidateRegistryError("Disposable journal lacks exact scoped collection")
    return counts


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    path.chmod(0o600)


def _reviewed_v3(repository: Path, private_repository: Path) -> None:
    """Require the actual independently reviewed V3 portfolio and candidate bytes."""
    base = private_repository / REVIEWED_PACKAGE
    review_path = base / "independent-review-v1/REVIEW.json"
    portfolio_path = base / "run-v1/REPORT.json"
    candidate_root = base / "candidate-v1"
    candidate_path = candidate_root / "REPORT.json"
    if (
        _private(review_path)[-1] != REVIEW_SHA256
        or _private(portfolio_path)[-1] != PORTFOLIO_REPORT_SHA256
        or _private(candidate_path)[-1] != CANDIDATE_REPORT_SHA256
    ):
        raise CandidateRegistryError("Independently reviewed V3 package hash differs")
    review = _json(review_path)
    if (
        review.get("verdict") != "PASS_PARTIAL_READ_ONLY_CANDIDATE_REGISTRY_FOR_INTEGRATION"
        or review.get("portfolio_report_sha256") != PORTFOLIO_REPORT_SHA256
        or review.get("candidate_sha256", {}).get("REPORT.json") != CANDIDATE_REPORT_SHA256
    ):
        raise CandidateRegistryError("Independently reviewed V3 verdict differs")
    verify_candidate(candidate_root, repository, private_repository)


def run(repository: Path, private_repository: Path, destination: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise CandidateRegistryError("Fresh disposable V3 probe destination required")
    _private(destination.parent, directory=True)
    _reviewed_v3(repository, private_repository)
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    if (
        diagnostic["source_count"],
        diagnostic["native_versions"],
        diagnostic["source_complete"],
    ) != (21, 358, False):
        raise CandidateRegistryError("Reviewed V3 source qualification differs")
    destination.mkdir(mode=0o700)
    originals: dict[Path, tuple] = {}
    sides = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        profile = profiles[side]
        manifest = json.loads(json.dumps(profile["manifest"]))
        side_root = destination / side
        side_root.mkdir(mode=0o700)
        frozen = []
        for source_id, component in profile["manifest"]["components"].items():
            if source_id.startswith("scenario-"):
                continue
            origin = Path(component["root"]) / "company.sqlite3"
            before = _private(origin)
            _no_sidecars(origin)
            originals[origin] = before
            target = side_root / source_id / "company.sqlite3"
            _ordinary_copy(origin, target)
            manifest["components"][source_id]["root"] = str(target.parent)
            frozen.append((source_id, origin, target, before[-1]))
        if len(frozen) != 13:
            raise CandidateRegistryError("Frozen 13-component baseline differs")
        selected = []
        for source_id, pin, component in _component_rows(profile):
            origin = Path(component["root"]) / "company.sqlite3"
            original = _private(origin)
            if original[-1] != pin["database_sha256"]:
                raise CandidateRegistryError("Pinned original database hash differs")
            _no_sidecars(origin)
            originals[origin] = original
            ref, business = _native(origin, component)
            if (ref["company"], ref["branch"]) != (pin["physical_company"], pin["physical_branch"]):
                raise CandidateRegistryError("Selected original physical route differs")
            target = side_root / source_id / "company.sqlite3"
            _ordinary_copy(origin, target)
            if (
                _counts(target)["grants"]
                or _counts(target)["collections"]
                or _counts(target)["access_events"]
            ):
                raise CandidateRegistryError("Disposable copy inherited audit access")
            manifest["components"][source_id]["root"] = str(target.parent)
            selected.append((source_id, target, component, ref, business, original[-1]))
        registry_path = destination / f"{side}.json"
        _write_json(registry_path, manifest)
        federated = FederatedCompanyStore(registry_path, profile["profile_id"])
        rows = []
        for source_id, target, component, ref, business, original_sha in selected:
            alias = component["namespace"] + ":" + ref["system"]
            before = federated.list_systems(
                PRINCIPAL, ENGAGEMENT, "SABLEHARBOR", profile["profile_id"]
            )
            if alias in {row["system"] for row in before["systems"]}:
                raise CandidateRegistryError("Source visible before scoped grant")
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
                pass
            else:
                raise CandidateRegistryError("Original read succeeded before grant")
            CompanyStore(target.parent).grant(
                PRINCIPAL, ENGAGEMENT, ref["company"], ref["branch"], ref["system"]
            )
            discovered = federated.list_systems(
                PRINCIPAL, ENGAGEMENT, "SABLEHARBOR", profile["profile_id"]
            )
            if alias not in {row["system"] for row in discovered["systems"]}:
                raise CandidateRegistryError("Granted source system undiscoverable")
            records = federated.list_records(
                PRINCIPAL,
                ENGAGEMENT,
                "SABLEHARBOR",
                profile["profile_id"],
                alias,
                as_of=ref["available_at"],
            )
            if not any(
                all(row[key] == ref[key] for key in ("record", "version", "sha256"))
                for row in records["records"]
            ):
                raise CandidateRegistryError("Exact native record undiscoverable")
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
                read["source_store_id"] != source_id
                or hashlib.sha256(read["content"]).hexdigest() != ref["sha256"]
                or any(read[key] != ref[key] for key in IDENTITY)
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
                command_id=f"PROBE-V3-{side}-{source_id.upper()}",
            )
            if any(collection["source"][key] != ref[key] for key in IDENTITY):
                raise CandidateRegistryError("Retained collection differs from native source")
            counts = _journal(target, ref)
            if _native(target, component)[1] != business:
                raise CandidateRegistryError("Disposable native business rows changed")
            rows.append(
                {
                    "source_store_id": source_id,
                    "alias": alias,
                    "source_database_sha256": original_sha,
                    "disposable_database_sha256": _sha(target),
                    "native_business_sha256": business,
                    "native_identity": ref,
                    "pregrant_invisible_and_read_denied": True,
                    "scoped_grant_and_discovery_verified": True,
                    "original_read_sha256_verified": True,
                    "retained_collection_verified": True,
                    "disposable_access_counts": counts,
                }
            )
        frozen_rows = []
        for source_id, origin, target, before_sha in frozen:
            if _sha(origin) != before_sha or _sha(target) != before_sha:
                raise CandidateRegistryError("Frozen component changed during disposable probe")
            frozen_rows.append(
                {
                    "source_store_id": source_id,
                    "original_database_sha256": before_sha,
                    "disposable_database_sha256": before_sha,
                    "no_grant_or_collection_added": True,
                }
            )
        sides[side] = {
            "scenario": scenario,
            "profile_id": profile["profile_id"],
            "registry_sha256": _sha(registry_path),
            "source_component_count": len(rows),
            "frozen_component_count": len(frozen_rows),
            "frozen_copies": frozen_rows,
            "collections": rows,
        }
    if any(_private(path) != state for path, state in originals.items()):
        raise CandidateRegistryError("Reviewed original source changed during probe")
    later, _ = candidate_profiles(repository, private_repository)
    if later["sources"] != diagnostic["sources"]:
        raise CandidateRegistryError("Reviewed portfolio changed during probe")
    report = {
        "schema": SCHEMA,
        "status": "PASS_DISPOSABLE_SOURCE_TO_COLLECTOR_BOUNDARY_ONLY",
        "probe_module_sha256": _sha(Path(__file__)),
        "reviewed_portfolio_verifier_sha256": diagnostic["verifier_module_sha256"],
        "reviewed_v3_review_sha256": REVIEW_SHA256,
        "reviewed_v3_portfolio_report_sha256": PORTFOLIO_REPORT_SHA256,
        "reviewed_v3_candidate_report_sha256": CANDIDATE_REPORT_SHA256,
        "reviewed_sources": diagnostic["sources"],
        "reviewed_source_count": 21,
        "reviewed_native_version_count": 358,
        "scenario_source_component_count_per_side": 22,
        "frozen_baseline_component_count_per_side": 13,
        "disposable_component_count_per_side": 35,
        "disposable_collection_count": 44,
        "sides": sides,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "original_company_sources_unchanged": True,
        "limits": [
            "Grants and collection journals exist only in disposable ordinary-byte copies.",
            "Frozen 13-component baseline routes also use isolated ordinary-byte copies.",
            "One exact native version per component is selected, not a period population.",
            "No PBC, audit engagement, workpaper, task, grade or Key changed.",
            "The partial 21-cohort portfolio does not resolve 283 discovery routes per side.",
        ],
    }
    _write_json(destination / "REPORT.json", report)
    return report


def verify(destination: Path, repository: Path, private_repository: Path) -> dict:
    """Read-only verification of sealed probe, clones, journals and source pins."""
    root = Path(destination).absolute()
    _private(root, directory=True)
    if {path.name for path in root.iterdir()} != {"A", "B", "A.json", "B.json", "REPORT.json"}:
        raise CandidateRegistryError("Exact V3 disposable probe layout required")
    report = _json(root / "REPORT.json")
    _reviewed_v3(repository, private_repository)
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    if (
        report.get("schema") != SCHEMA
        or report.get("status") != "PASS_DISPOSABLE_SOURCE_TO_COLLECTOR_BOUNDARY_ONLY"
        or report.get("probe_module_sha256") != _sha(Path(__file__))
        or report.get("reviewed_sources") != diagnostic["sources"]
        or report.get("reviewed_portfolio_verifier_sha256") != diagnostic["verifier_module_sha256"]
        or report.get("reviewed_v3_review_sha256") != REVIEW_SHA256
        or report.get("reviewed_v3_portfolio_report_sha256") != PORTFOLIO_REPORT_SHA256
        or report.get("reviewed_v3_candidate_report_sha256") != CANDIDATE_REPORT_SHA256
        or report.get("reviewed_source_count") != 21
        or report.get("reviewed_native_version_count") != 358
        or report.get("scenario_source_component_count_per_side") != 22
        or report.get("frozen_baseline_component_count_per_side") != 13
        or report.get("disposable_component_count_per_side") != 35
        or report.get("disposable_collection_count") != 44
        or report.get("source_complete") is not False
        or report.get("fresh_audit_pair_created") is not False
        or report.get("audit_task_credit") is not False
        or report.get("original_company_sources_unchanged") is not True
    ):
        raise CandidateRegistryError("V3 probe report qualification differs")
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        profile = profiles[side]
        side_root = root / side
        _private(side_root, directory=True)
        selected = _component_rows(profile)
        if {p.name for p in side_root.iterdir()} != set(profile["manifest"]["components"]):
            raise CandidateRegistryError("Disposable source roster differs")
        manifest = _json(root / f"{side}.json")
        expected_manifest = json.loads(json.dumps(profile["manifest"]))
        frozen_rows = report["sides"][side]["frozen_copies"]
        frozen_components = [
            (name, component)
            for name, component in profile["manifest"]["components"].items()
            if not name.startswith("scenario-")
        ]
        if len(frozen_rows) != 13 or report["sides"][side]["frozen_component_count"] != 13:
            raise CandidateRegistryError("Frozen disposable roster count differs")
        for row, (source_id, component) in zip(frozen_rows, frozen_components, strict=True):
            copy_dir = side_root / source_id
            _private(copy_dir, directory=True)
            if {p.name for p in copy_dir.iterdir()} != {"company.sqlite3"}:
                raise CandidateRegistryError("Frozen disposable directory differs")
            origin = Path(component["root"]) / "company.sqlite3"
            copy = copy_dir / "company.sqlite3"
            original = _private(origin)
            cloned = _private(copy)
            if (
                original[-1] != cloned[-1]
                or row["source_store_id"] != source_id
                or row["original_database_sha256"] != original[-1]
                or row["disposable_database_sha256"] != cloned[-1]
                or row["no_grant_or_collection_added"] is not True
                or original[:2] == cloned[:2]
            ):
                raise CandidateRegistryError("Frozen original or ordinary-byte copy differs")
            expected_manifest["components"][source_id]["root"] = str(copy_dir)
        rows = report["sides"][side]["collections"]
        if len(rows) != 22 or report["sides"][side]["scenario"] != scenario:
            raise CandidateRegistryError("Disposable collection count differs")
        for row, (source_id, pin, component) in zip(rows, selected, strict=True):
            copy_dir = side_root / source_id
            _private(copy_dir, directory=True)
            if {p.name for p in copy_dir.iterdir()} != {"company.sqlite3"}:
                raise CandidateRegistryError("Disposable source has unexpected files")
            copy = copy_dir / "company.sqlite3"
            origin = Path(component["root"]) / "company.sqlite3"
            if (
                _private(origin)[-1] != pin["database_sha256"]
                or _sha(copy) != row["disposable_database_sha256"]
            ):
                raise CandidateRegistryError("Original or copied database hash differs")
            if (origin.stat().st_dev, origin.stat().st_ino) == (
                copy.stat().st_dev,
                copy.stat().st_ino,
            ):
                raise CandidateRegistryError("Original and copy share inode")
            original_ref, business = _native(origin, component)
            copy_ref, copied_business = _native(copy, component)
            if (
                original_ref != copy_ref
                or business != copied_business
                or business != row["native_business_sha256"]
            ):
                raise CandidateRegistryError("Original and collected business rows differ")
            if (
                row["source_store_id"] != source_id
                or row["source_database_sha256"] != pin["database_sha256"]
                or row["native_identity"] != original_ref
                or row["alias"] != component["namespace"] + ":" + original_ref["system"]
            ):
                raise CandidateRegistryError("Disposable original route differs")
            if (
                any(
                    row[key] is not True
                    for key in (
                        "pregrant_invisible_and_read_denied",
                        "scoped_grant_and_discovery_verified",
                        "original_read_sha256_verified",
                        "retained_collection_verified",
                    )
                )
                or _journal(copy, original_ref) != row["disposable_access_counts"]
            ):
                raise CandidateRegistryError("Disposable collection proof differs")
            expected_manifest["components"][source_id]["root"] = str(copy_dir)
        if (
            manifest != expected_manifest
            or _sha(root / f"{side}.json") != report["sides"][side]["registry_sha256"]
        ):
            raise CandidateRegistryError("Disposable routing manifest differs")
        FederatedCompanyStore(root / f"{side}.json", profile["profile_id"])
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "verify"))
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "run":
        result = run(args.repository, args.private_repository, args.destination)
    else:
        result = verify(args.destination, args.repository, args.private_repository)
    print(
        json.dumps({key: value for key, value in result.items() if key != "sides"}, sort_keys=True)
    )


if __name__ == "__main__":
    main()
