"""Read-only legacy documentary migration planning, never an operating-fact inference.

A trusted operator supplies a frozen world. Only already-rendered company-facing
originals are candidates; hidden facts, actor beliefs and rubrics are not imported.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .private_publication import publish
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
    directories = [world]
    for directory in sorted(world.glob("scope-*")):
        if (
            directory.is_symlink()
            or not directory.is_dir()
            or not re.fullmatch(r"scope-\d{5,}", directory.name)
            or int(directory.name.removeprefix("scope-")) < 1
        ):
            raise DomainError("Invalid legacy scope epoch")
        directories.append(directory)
    for path in sorted(p for directory in directories for p in directory.glob("unit-*.json")):
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
                    "unit": str(path.relative_to(world)),
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


def plan_documentary_custody(
    private_root: Path,
    legacy_plan: dict,
    *,
    scoped_state: dict,
    company_id: str,
    branch_id: str,
    owner_ids: dict[str, str],
) -> dict:
    """Validate explicit documentary custody against a trusted scoped engagement.

    The local operator must supply the actual retained engagement projection, not
    caller-authored ownership. Custody describes today's provisional archive routing;
    it does not assert historical system operation or backdate a person's appointment.
    """
    verified = plan_legacy_documents(private_root, legacy_plan.get("legacy_engagement", ""))
    if verified != legacy_plan:
        raise DomainError("Migration plan or original source pins changed")
    pattern = r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}"
    if any(not isinstance(v, str) or not re.fullmatch(pattern, v) for v in (company_id, branch_id)):
        raise DomainError("Explicit valid company and documentary branch required")
    if scoped_state.get("id") != legacy_plan["legacy_engagement"]:
        raise DomainError("Custody requires the original scoped engagement")
    controls = scoped_state.get("controls", [])
    people = scoped_state.get("people", [])
    if (
        not isinstance(controls, list)
        or not isinstance(people, list)
        or any(not isinstance(c, dict) or not isinstance(c.get("id"), str) for c in controls)
        or any(not isinstance(p, dict) or not isinstance(p.get("id"), str) for p in people)
    ):
        raise DomainError("Actual scoped controls and people required")
    by_control = {c["id"]: c for c in controls}
    by_person = {p["id"]: p for p in people}
    source_controls = {d["control_id"] for d in legacy_plan["documents"]}
    if (
        None in source_controls
        or not isinstance(owner_ids, dict)
        or set(owner_ids) != source_controls
        or not source_controls <= by_control.keys()
        or len(by_control) != len(controls)
        or len(by_person) != len(people)
    ):
        raise DomainError("Exact complete per-control documentary custody mapping required")
    archives = []
    for control_id in sorted(source_controls):
        assignment = by_control[control_id].get("assignment", {})
        owner = owner_ids[control_id]
        if (
            not isinstance(owner, str)
            or not re.fullmatch(pattern, owner)
            or owner not in by_person
            or assignment.get("primary_person_id") != owner
        ):
            raise DomainError("Documentary custodian must be the actual scoped control owner")
        documents = [d for d in legacy_plan["documents"] if d["control_id"] == control_id]
        if any(not d["available_at"] for d in documents):
            raise DomainError("Explicit document availability mapping required")
        archives.append(
            {
                "control_id": control_id,
                "system_id": "DOC-" + digest(control_id)[:32],
                "owner_id": owner,
                "assignment_sha256": digest(assignment),
                "record_ids": [d["record_id"] for d in documents],
                "custody_status": "PROVISIONAL_DOCUMENTARY_CUSTODY",
                "custody_basis": "CURRENT_SCOPED_PRIMARY_OWNER_NOT_HISTORICAL_SYSTEM_OWNERSHIP",
            }
        )
    body = {
        "schema": "CONTROL_DOCUMENTARY_CUSTODY_V1",
        "legacy_plan": legacy_plan,
        "company_id": company_id,
        "branch_id": branch_id,
        "organization_snapshot_digest": scoped_state.get("organization", {}).get("snapshot_digest"),
        "scope_sha256": digest(scoped_state.get("scope", {})),
        "archives": archives,
        "status": "PLANNED_NOT_IMPORTED",
        "operating_history_migration": "NOT_COMPLETE",
        "access_grants": "NONE",
    }
    if not isinstance(body["organization_snapshot_digest"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", body["organization_snapshot_digest"]
    ):
        raise DomainError("Pinned scoped organization snapshot required")
    return {**body, "custody_plan_sha256": digest(body)}


def import_documentary_custody(
    private_root: Path,
    custody_plan: dict,
    *,
    scoped_state: dict,
    destination: Path,
) -> dict:
    """Publish a new private documentary store only after every original imports.

    Existing legacy/operating stores are never written. A failure leaves no published
    store; retry uses the same source plan and a still-new destination. No grants.
    """
    import os
    import tempfile

    from .company_store import CompanyStore

    owners = {r["control_id"]: r["owner_id"] for r in custody_plan.get("archives", [])}
    verified = plan_documentary_custody(
        private_root,
        custody_plan.get("legacy_plan", {}),
        scoped_state=scoped_state,
        company_id=custody_plan.get("company_id"),
        branch_id=custody_plan.get("branch_id"),
        owner_ids=owners,
    )
    if verified != custody_plan:
        raise DomainError("Documentary custody or organization pins changed")
    destination = Path(destination).absolute()
    if (
        any(p.is_symlink() for p in (destination, *destination.parents))
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or destination.exists()
    ):
        raise DomainError("New documentary store under private nonsymlink parent required")
    company, branch = verified["company_id"], verified["branch_id"]
    legacy = verified["legacy_plan"]
    archives = {a["control_id"]: a for a in verified["archives"]}
    records = []
    with tempfile.TemporaryDirectory(prefix="documentary-import-", dir=destination.parent) as temp:
        store = CompanyStore(Path(temp))
        for archive in archives.values():
            store.register_system(company, branch, archive["system_id"], archive["owner_id"])
        for row in legacy["documents"]:
            archive = archives[row["control_id"]]
            source = Path(private_root) / row["original_relative_path"]
            if any(p.is_symlink() for p in (source, *source.parents)):
                raise DomainError("Original source aliases forbidden")
            content = source.read_bytes()
            if hashlib.sha256(content).hexdigest() != row["sha256"] or len(content) != row["bytes"]:
                raise DomainError("Original changed during documentary import")
            records.append(
                store.append_version(
                    company,
                    branch,
                    archive["system_id"],
                    row["record_id"],
                    expected_version=0,
                    command_id="DOCMIG-"
                    + digest([verified["custody_plan_sha256"], row["record_id"]]),
                    event_at=None,
                    available_at=row["available_at"],
                    content=content,
                    origin="MIGRATED_SYNTHETIC_HISTORY",
                    provenance={
                        "source_reference": row["source_identity"],
                        "plan_sha256": legacy["plan_sha256"],
                        "custody_plan_sha256": verified["custody_plan_sha256"],
                        "original_sha256": row["sha256"],
                        "name": row["name"],
                        "mime": row["mime"],
                        "classification": row["classification"],
                        "operational_fact_status": row["operational_fact_status"],
                        "control_id": row["control_id"],
                        "custodian_person_id": archive["owner_id"],
                        "custody_status": archive["custody_status"],
                        "custody_basis": archive["custody_basis"],
                        "organization_snapshot_digest": verified["organization_snapshot_digest"],
                        "assignment_sha256": archive["assignment_sha256"],
                    },
                )
            )
        receipt = {
            "status": "CONTROL_DOCUMENTARY_IMPORT_COMPLETE",
            "custody_plan_sha256": verified["custody_plan_sha256"],
            "plan_sha256": legacy["plan_sha256"],
            "company_id": company,
            "branch_id": branch,
            "archive_count": len(archives),
            "document_count": len(records),
            "records": records,
            "access_grants": "NONE",
            "operating_history_migration": "NOT_COMPLETE",
            "historical_audit_modified": False,
        }
        raw = json.dumps(receipt, sort_keys=True).encode()
        target = Path(temp) / "DOCUMENTARY_IMPORT_RECEIPT.json"
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        publish(Path(temp), destination)
    return receipt
