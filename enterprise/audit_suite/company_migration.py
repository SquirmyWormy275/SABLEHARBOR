"""Read-only legacy documentary migration planning, never an operating-fact inference.

A trusted operator supplies a frozen world. Only already-rendered company-facing
originals are candidates; hidden facts, actor beliefs and rubrics are not imported.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .store import DomainError, digest


def plan_legacy_documents(private_root: Path, engagement_id: str) -> dict:
    """Pin originals and world units without rewriting either or granting access."""
    if not re.fullmatch(r"ENG-[0-9a-f]+", engagement_id):
        raise DomainError("Invalid legacy engagement identity")
    root = private_root.absolute()
    if any(path.is_symlink() for path in (root, *root.parents)):
        raise DomainError("Legacy source ancestor symlinks are not permitted")
    world = root / "worlds" / engagement_id
    if any(p.is_symlink() for p in (root, root / "worlds", world, root / "artifacts")):
        raise DomainError("Legacy source symlinks are not permitted")
    if not world.is_dir():
        raise DomainError("Legacy world unavailable")
    entries, pins, seen = [], [], set()
    for path in sorted(world.glob("unit-*.json")):
        if path.is_symlink() or not re.fullmatch(r"unit-\d+\.json", path.name):
            raise DomainError("Invalid legacy unit")
        raw = path.read_bytes()
        unit = json.loads(raw)
        pins.append(
            {"path": str(path.relative_to(root)), "sha256": hashlib.sha256(raw).hexdigest()}
        )
        for request in unit.get("requests", []):
            for manifest in request.get("prepared_artifacts", []):
                sha = manifest.get("sha256", "")
                if not re.fullmatch(r"[0-9a-f]{64}", sha):
                    raise DomainError("Invalid original hash")
                source = root / "artifacts" / sha
                if source.is_symlink():
                    raise DomainError("Original symlink rejected")
                content = source.read_bytes()
                if hashlib.sha256(content).hexdigest() != sha or len(content) != manifest["bytes"]:
                    raise DomainError("Legacy original integrity failure")
                identity = {
                    "engagement": engagement_id,
                    "unit": path.name,
                    "request": request["id"],
                    "artifact": manifest["id"],
                }
                key = digest(identity)
                if key in seen:
                    raise DomainError("Duplicate legacy original identity")
                seen.add(key)
                entries.append(
                    {
                        "record_id": "LEGACY-" + key,
                        "source_identity": identity,
                        "control_id": unit.get("control_id"),
                        "name": manifest["name"],
                        "mime": manifest["mime"],
                        "sha256": sha,
                        "bytes": len(content),
                        "original_relative_path": "artifacts/" + sha,
                        "available_at": manifest.get("available_at"),
                        "event_at": None,
                        "classification": "LEGACY_SYNTHETIC_DOCUMENTARY_SOURCE",
                        "operational_fact_status": "REQUIRES_SOURCE_RECONCILIATION",
                    }
                )
    if not entries:
        raise DomainError("No retained company originals to migrate")
    body = {
        "schema_version": 1,
        "legacy_engagement": engagement_id,
        "source_units": pins,
        "documents": entries,
        "status": "PLANNED_NOT_IMPORTED",
        "limitations": [
            "Legacy audit-prepared documents are not canonical operating events.",
            "Event dates, system ownership and source reconciliation require explicit mapping.",
            "No hidden truth, actor beliefs, recipes or rubrics are projected into this plan.",
            "No historical source-system collection is asserted.",
        ],
    }
    return {**body, "plan_sha256": digest(body)}


def import_legacy_documents(
    company_store,
    private_root: Path,
    plan: dict,
    *,
    company_id: str,
    branch_id: str,
    system_id: str,
) -> dict:
    """Resume imports into an operator-registered archive, preserving unknown dates.

    Every source pin is revalidated before the first mutation. Partial imports are
    resumable using deterministic commands; no existing company version is replaced.
    This is documentary migration, not the completed operating-history migration.
    """
    verified = plan_legacy_documents(private_root, plan.get("legacy_engagement", ""))
    if verified != plan:
        raise DomainError("Migration plan or original source pins changed")
    if any(not row["available_at"] for row in plan["documents"]):
        raise DomainError("Explicit document availability mapping required")
    imported = []
    for row in plan["documents"]:
        source = private_root / row["original_relative_path"]
        if source.is_symlink():
            raise DomainError("Original symlink rejected")
        content = source.read_bytes()
        if hashlib.sha256(content).hexdigest() != row["sha256"]:
            raise DomainError("Original changed during import")
        command = "MIG-" + digest(
            [company_id, branch_id, system_id, row["record_id"], row["sha256"]]
        )
        result = company_store.append_version(
            company_id,
            branch_id,
            system_id,
            row["record_id"],
            expected_version=0,
            command_id=command,
            event_at=None,
            available_at=row["available_at"],
            content=content,
            origin="MIGRATED_SYNTHETIC_HISTORY",
            provenance={
                "source_reference": row["source_identity"],
                "plan_sha256": plan["plan_sha256"],
                "original_sha256": row["sha256"],
                "name": row["name"],
                "mime": row["mime"],
                "classification": row["classification"],
                "operational_fact_status": row["operational_fact_status"],
            },
        )
        imported.append(result)
    return {
        "status": "DOCUMENTARY_IMPORT_COMPLETE",
        "plan_sha256": plan["plan_sha256"],
        "records": imported,
        "operating_history_migration": "NOT_COMPLETE",
        "historical_audit_modified": False,
    }
