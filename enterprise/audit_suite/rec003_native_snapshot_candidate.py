"""Freeze reviewed nonpersonal DQ originals as a candidate native source.

The source is a byte copy of the post-journal company database. Historical audit
journals remain present and are excluded from company transformation activity.
No grant, collection, transformation or audit task operation occurs here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from . import rec003_lineage_gap as rec003
from .company_federation import QUALIFICATION, FederatedCompanyStore
from .company_federation import SCHEMA as REGISTRY_SCHEMA
from .company_store import CompanyStoreError
from .fictional_2027_collection_probe import _ordinary_copy

SCHEMA = "SH_REC003_REBASED_NATIVE_SOURCE_SNAPSHOT_CANDIDATE_V1"
PACKET = "enterprise/generated/audit-suite/rec003-lineage-gap-2026-09-29"
REVIEW_SHA256 = "f162bf84513163be4c21479c85ab986b20c62d026870bd9741a8e1285470844e"
LINEAGE_SHA256 = "b696a1162e7af78db371bf4b541aafeb69bf67a548dd30e2134d260227caf421"
MANIFEST_SHA256 = "05216ad94c43ec7cd411a4d7800688af2c8114d1ed9806d70d92fea4aef083a3"
SYSTEMS = (
    "quality_aggregate",
    "quality_definition",
    "quality_derived",
    "quality_operation",
    "quality_raw",
    "quality_reference",
)
JOURNALS = {"grants": 12, "collections": 22, "access_events": 25}
PRINCIPAL = "F27-REC003-SNAPSHOT-DIAGNOSTIC"
ENGAGEMENT = "F27-REC003-SNAPSHOT-DIAGNOSTIC"
FIELDS = (
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
LIMITS = [
    "2027 event and availability clocks are authored future simulation; import was 2026.",
    "These are independent ordinary-byte copies of reviewed post-journal company sources.",
    "Inherited audit journals are not transformation activity.",
    "No deployed transformation, population, source truth or review is proven.",
    "Snapshot candidates receive no grant, collection or audit task credit.",
]


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def _private_dir(path: Path) -> None:
    if (
        not path.is_dir()
        or path.is_symlink()
        or path.stat().st_mode & 0o077
        or any(parent.is_symlink() for parent in path.parents)
    ):
        raise CompanyStoreError("Private ordinary snapshot directory required")


def _no_shared_extents(path: Path) -> None:
    """Fail closed if FIEMAP reports a shared Btrfs extent on the new copy."""
    try:
        result = subprocess.run(
            ["filefrag", "-v", str(path)], capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CompanyStoreError("REC003 copy extent inspection unavailable") from exc
    if "extents found" not in result.stdout or any(
        line.lstrip()[:1].isdigit() and "shared" in line for line in result.stdout.splitlines()
    ):
        raise CompanyStoreError("REC003 copy has shared or uninspectable extents")


def _json(path: Path) -> dict:
    rec003._private(path)
    return json.loads(path.read_bytes())


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def _lineage(repository: Path, private_repository: Path) -> dict:
    base = private_repository / PACKET
    expected = {
        base / "independent-review-v1/REVIEW.json": REVIEW_SHA256,
        base / "run-v1/LINEAGE.json": LINEAGE_SHA256,
        base / "run-v1/MANIFEST.json": MANIFEST_SHA256,
    }
    for path, digest in expected.items():
        if rec003._frozen(path)[-1] != digest:
            raise CompanyStoreError("Reviewed REC003 packet pin differs")
    review = _json(base / "independent-review-v1/REVIEW.json")
    if review.get(
        "verdict"
    ) != "PASS_READ_ONLY_LINEAGE_GAP_PACKET_FOR_INTEGRATION_REVIEW" or review.get("run_sha256") != {
        "LINEAGE.json": LINEAGE_SHA256,
        "MANIFEST.json": MANIFEST_SHA256,
    }:
        raise CompanyStoreError("REC003 independent review differs")
    rec003.verify(base / "run-v1", repository=repository, private_repository=private_repository)
    lineage = _json(base / "run-v1/LINEAGE.json")
    if (
        lineage.get("audit_task_credit") is not False
        or lineage.get("new_company_operation") is not False
    ):
        raise CompanyStoreError("REC003 packet qualification differs")
    return lineage


def _originals(db_path: Path, side: str, branch_packet: dict) -> dict:
    before = rec003._frozen(db_path)
    if before[-1] != rec003.EXPECTED_DB[side.lower()]:
        raise CompanyStoreError("Rebased REC003 company source hash differs")
    with sqlite3.connect(db_path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("REC003 source integrity differs")
        systems = db.execute(
            "SELECT company,branch,system FROM systems ORDER BY company,branch,system"
        ).fetchall()
        rows = db.execute(
            "SELECT company,branch,system,record,version,sha256,event_at,available_at,"
            "imported_at,content FROM versions ORDER BY system,record,version"
        ).fetchall()
        journals = {
            name: db.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in JOURNALS
        }
    if rec003._frozen(db_path) != before:
        raise CompanyStoreError("REC003 source changed during native read")
    expected_refs = branch_packet["native_original_refs"]
    actual = [{name: row[name] for name in FIELDS} for row in rows]
    if (
        len(actual) != 11
        or actual != expected_refs
        or journals != JOURNALS
        or journals != branch_packet["audit_journal_counts_excluded_from_company_lineage"]
        or branch_packet["branch"] != f"local-data-quality-{side.lower()}"
        or sorted({row["system"] for row in systems if row["branch"] == branch_packet["branch"]})
        != list(SYSTEMS)
        or any(
            row["company"] != "SABLEHARBOR"
            or row["branch"] != branch_packet["branch"]
            or hashlib.sha256(row["content"]).hexdigest() != row["sha256"]
            for row in rows
        )
    ):
        raise CompanyStoreError("REC003 exact company originals or inherited journals differ")
    return {
        "source_database_sha256": before[-1],
        "branch": branch_packet["branch"],
        "native_original_count": 11,
        "native_original_refs": actual,
        "inherited_audit_journals_excluded_from_company_lineage": journals,
        "system_count": len(SYSTEMS),
    }


def _route_template() -> dict:
    return {
        "schema": SCHEMA + "_ROUTES",
        "sides": {
            side: {
                "source_store_id": "scenario-rec003-dq",
                "root_locator": "snapshot://" + side,
                "physical_company": "SABLEHARBOR",
                "physical_branch": f"local-data-quality-{side.lower()}",
                "namespace": "F27REC003DQ",
                "systems": list(SYSTEMS),
                "logical_company": "SABLEHARBOR",
                "profile_id": "fictional27-rec003-snapshot-" + side.lower(),
                "qualification": QUALIFICATION,
            }
            for side in "AB"
        },
    }


def _registry(side: str, snapshot: Path) -> dict:
    route = _route_template()["sides"][side]
    component_id = "scenario-rec003-dq"
    profile_id = route["profile_id"]
    return {
        "schema": REGISTRY_SCHEMA,
        "components": {
            component_id: {
                "root": str(snapshot.parent),
                "company": route["physical_company"],
                "branch": route["physical_branch"],
                "namespace": route["namespace"],
                "systems": route["systems"],
            }
        },
        "profiles": {
            profile_id: {
                "company": route["logical_company"],
                "components": [component_id],
                "qualification": QUALIFICATION,
            }
        },
    }


def _probe_route(side: str, snapshot: Path, scratch_parent: Path) -> None:
    """Load an absolute registry only in disposable scratch; keep package portable."""
    with tempfile.TemporaryDirectory(prefix=".rec003-route-", dir=scratch_parent) as name:
        path = Path(name) / "registry.json"
        _write(path, _registry(side, snapshot))
        adapter = FederatedCompanyStore(path, "fictional27-rec003-snapshot-" + side.lower())
        invisible = adapter.list_systems(PRINCIPAL, ENGAGEMENT, "SABLEHARBOR", adapter.profile_id)[
            "systems"
        ]
        if invisible:
            raise CompanyStoreError("Unreviewed REC003 snapshot visible without grant")


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise CompanyStoreError("Fresh REC003 snapshot candidate required")
    _private_dir(destination.parent)
    lineage = _lineage(repository, private_repository)
    destination.mkdir(mode=0o700)
    _write(destination / "ROUTES.json", _route_template())
    sides = {}
    originals = {}
    for side in "AB":
        original = private_repository / rec003.DQ / "run-v1" / side.lower() / "company.sqlite3"
        before = rec003._frozen(original)
        originals[original] = before
        source = _originals(original, side, lineage["branches"][side])
        snapshot = destination / side / "company.sqlite3"
        _ordinary_copy(original, snapshot)
        _no_shared_extents(snapshot)
        if rec003._frozen(snapshot)[-1] != before[-1]:
            raise CompanyStoreError("Ordinary REC003 snapshot differs")
        _probe_route(side, snapshot, destination.parent)
        if rec003._frozen(snapshot)[-1] != before[-1]:
            raise CompanyStoreError("Read-only routing changed REC003 snapshot")
        sides[side] = {
            **source,
            "disposable_snapshot_sha256": _sha(snapshot),
            "route_locator": "snapshot://" + side,
            "source_and_snapshot_distinct_inode": True,
            "ordinary_byte_identical": True,
            "btrfs_shared_extent_lines": 0,
            "pregrant_invisible": True,
            "candidate_only_no_new_company_operation": True,
        }
    if any(rec003._frozen(path) != before for path, before in originals.items()):
        raise CompanyStoreError("Original DQ source changed during snapshot")
    receipt = {
        "schema": SCHEMA,
        "status": "CANDIDATE_REBASED_LOCAL_SOURCE_ONLY_NO_AUDIT_CREDIT",
        "module_sha256": _sha(Path(__file__)),
        "independent_rec003_review_sha256": REVIEW_SHA256,
        "rec003_lineage_sha256": LINEAGE_SHA256,
        "rec003_manifest_sha256": MANIFEST_SHA256,
        "source_original_count": 22,
        "sides": sides,
        "source_complete": False,
        "audit_task_credit": False,
        "audit_collection": False,
        "new_company_operation": False,
        "actual_operating_evidence": False,
        "limits": LIMITS,
    }
    _write(destination / "RECEIPT.json", receipt)
    manifest = {
        "schema": SCHEMA + "_MANIFEST",
        "receipt_sha256": _sha(destination / "RECEIPT.json"),
        "module_sha256": _sha(Path(__file__)),
        "snapshot_sha256": {side: sides[side]["disposable_snapshot_sha256"] for side in "AB"},
        "routes_sha256": _sha(destination / "ROUTES.json"),
        "audit_task_credit": False,
    }
    _write(destination / "MANIFEST.json", manifest)
    return verify(destination, repository=repository, private_repository=private_repository)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    root = Path(destination).absolute()
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    _private_dir(root)
    if {item.name for item in root.iterdir()} != {
        "A",
        "B",
        "ROUTES.json",
        "RECEIPT.json",
        "MANIFEST.json",
    }:
        raise CompanyStoreError("Exact REC003 snapshot candidate layout required")
    lineage = _lineage(repository, private_repository)
    if _json(root / "ROUTES.json") != _route_template():
        raise CompanyStoreError("REC003 portable source locator differs")
    receipt = _json(root / "RECEIPT.json")
    manifest = _json(root / "MANIFEST.json")
    if (
        set(receipt)
        != {
            "schema",
            "status",
            "module_sha256",
            "independent_rec003_review_sha256",
            "rec003_lineage_sha256",
            "rec003_manifest_sha256",
            "source_original_count",
            "sides",
            "source_complete",
            "audit_task_credit",
            "audit_collection",
            "new_company_operation",
            "actual_operating_evidence",
            "limits",
        }
        or receipt.get("schema") != SCHEMA
        or receipt.get("status") != "CANDIDATE_REBASED_LOCAL_SOURCE_ONLY_NO_AUDIT_CREDIT"
        or receipt.get("module_sha256") != _sha(Path(__file__))
        or receipt.get("independent_rec003_review_sha256") != REVIEW_SHA256
        or receipt.get("rec003_lineage_sha256") != LINEAGE_SHA256
        or receipt.get("rec003_manifest_sha256") != MANIFEST_SHA256
        or receipt.get("source_original_count") != 22
        or receipt.get("source_complete") is not False
        or receipt.get("audit_task_credit") is not False
        or receipt.get("audit_collection") is not False
        or receipt.get("new_company_operation") is not False
        or receipt.get("actual_operating_evidence") is not False
        or receipt.get("limits") != LIMITS
        or set(receipt.get("sides", {})) != {"A", "B"}
    ):
        raise CompanyStoreError("REC003 snapshot qualification differs")
    for side in "AB":
        snapshot_dir = root / side
        _private_dir(snapshot_dir)
        if {item.name for item in snapshot_dir.iterdir()} != {"company.sqlite3"}:
            raise CompanyStoreError("Exact REC003 snapshot DB required")
        snapshot = snapshot_dir / "company.sqlite3"
        _no_shared_extents(snapshot)
        original = private_repository / rec003.DQ / "run-v1" / side.lower() / "company.sqlite3"
        source = _originals(original, side, lineage["branches"][side])
        copied = _originals(snapshot, side, lineage["branches"][side])
        row = receipt["sides"][side]
        expected_row = {
            **source,
            "disposable_snapshot_sha256": _sha(snapshot),
            "route_locator": "snapshot://" + side,
            "source_and_snapshot_distinct_inode": True,
            "ordinary_byte_identical": True,
            "btrfs_shared_extent_lines": 0,
            "pregrant_invisible": True,
            "candidate_only_no_new_company_operation": True,
        }
        if (
            source != copied
            or row != expected_row
            or rec003._frozen(original)[:2] == rec003._frozen(snapshot)[:2]
        ):
            raise CompanyStoreError("REC003 snapshot original provenance differs")
        _probe_route(side, snapshot, root.parent)
    if manifest != {
        "schema": SCHEMA + "_MANIFEST",
        "receipt_sha256": _sha(root / "RECEIPT.json"),
        "module_sha256": _sha(Path(__file__)),
        "snapshot_sha256": {
            side: receipt["sides"][side]["disposable_snapshot_sha256"] for side in "AB"
        },
        "routes_sha256": _sha(root / "ROUTES.json"),
        "audit_task_credit": False,
    }:
        raise CompanyStoreError("REC003 snapshot manifest differs")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    func = create if args.action == "create" else verify
    result = func(
        args.destination,
        repository=args.repository,
        private_repository=args.private_repository,
    )
    print(
        json.dumps({key: value for key, value in result.items() if key != "sides"}, sort_keys=True)
    )


if __name__ == "__main__":
    main()
