"""Operator-only ingestion of explicitly mapped repository documentary originals."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath

from .company_store import CompanyStoreError, _id, _now

ORIGIN = "REPOSITORY_SYNTHETIC_DOCUMENT"
QUALIFICATION = "PROPOSED_DOCUMENTARY_RELATIONSHIP_NOT_OPERATING_EVIDENCE"


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _git(root, *args):
    try:
        return (
            subprocess.check_output(
                ["git", "-C", str(root), *args], stderr=subprocess.DEVNULL, timeout=15
            )
            .strip()
            .decode()
        )
    except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
        raise CompanyStoreError("Repository source pin unavailable") from exc


def _source(root, relative):
    path = PurePosixPath(relative)
    if (
        path.is_absolute()
        or ".." in path.parts
        or str(path) != relative
        or len(path.parts) < 3
        or path.parts[0] != "docs"
        or path.parts[1] not in {"governance", "controls", "canon"}
        or path.suffix != ".md"
        or any(
            part in {"internal", "generated", "publications", "structured", "finance"}
            for part in path.parts
        )
    ):
        raise CompanyStoreError("Explicit native documentary path required")
    target = root / relative
    if any(p.is_symlink() for p in [target, *target.parents]) or not target.is_file():
        raise CompanyStoreError("Native document unavailable")
    with target.open("rb") as stream:
        data = stream.read(25 * 1024 * 1024 + 1)
    if not 0 < len(data) <= 25 * 1024 * 1024:
        raise CompanyStoreError("Document size unsupported")
    blob = _git(root, "rev-parse", "HEAD:" + relative)
    actual_blob = (
        subprocess.check_output(
            ["git", "-C", str(root), "hash-object", "--stdin"],
            input=data,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
        .strip()
        .decode()
    )
    if actual_blob != blob:
        raise CompanyStoreError("Document differs from committed source")
    return data, blob


def plan_repository_documents(repository, *, manifest, organization_snapshot):
    """Validate explicit operator mappings; this does not approve their canon authority."""
    root = Path(repository).absolute()
    if set(manifest) != {"company", "branch", "documents"}:
        raise CompanyStoreError("Exact document manifest schema required")
    company, branch = _id(manifest["company"]), _id(manifest["branch"])
    assignments = {a["control_id"]: a for a in organization_snapshot["control_assignments"]}
    documents = manifest["documents"]
    if not isinstance(documents, list) or not 1 <= len(documents) <= 200:
        raise CompanyStoreError("Bounded document list required")
    prepared, identities = [], set()
    required = {
        "document_id",
        "path",
        "expected_version",
        "control_ids",
        "owner_id",
        "source_authority",
        "source_version",
        "effective_date",
        "revision_date",
        "supersedes",
        "mapping_rationale",
    }
    for item in documents:
        if not isinstance(item, dict) or set(item) != required:
            raise CompanyStoreError("Exact documentary entry schema required")
        identity = _id(item["document_id"])
        if identity in identities:
            raise CompanyStoreError("Duplicate document identity")
        identities.add(identity)
        if type(item["expected_version"]) is not int or item["expected_version"] < 0:
            raise CompanyStoreError("Expected source version required")
        for key in ("path", "owner_id", "source_authority", "source_version", "mapping_rationale"):
            if not isinstance(item[key], str) or not item[key].strip() or len(item[key]) > 2000:
                raise CompanyStoreError("Explicit bounded documentary metadata required")
        from datetime import date

        for key in ("effective_date", "revision_date"):
            if item[key] is not None:
                try:
                    if date.fromisoformat(item[key]).isoformat() != item[key]:
                        raise ValueError()
                except (ValueError, TypeError) as exc:
                    raise CompanyStoreError("ISO date or unknown required") from exc
        if not isinstance(item["supersedes"], list) or any(
            not isinstance(x, str) or not x or len(x) > 200 for x in item["supersedes"]
        ):
            raise CompanyStoreError("Explicit supersession references required")
        controls = item["control_ids"]
        if (
            not isinstance(controls, list)
            or not controls
            or len(controls) != len(set(controls))
            or any(c not in assignments for c in controls)
        ):
            raise CompanyStoreError("Actual control references required")
        selected = [assignments[c] for c in controls]
        if any(a["primary_person_id"] != item["owner_id"] for a in selected):
            raise CompanyStoreError("Document custody differs from scoped assignment")
        content, blob = _source(root, item["path"])
        prepared.append(
            dict(
                item,
                sha256=hashlib.sha256(content).hexdigest(),
                git_blob=blob,
                custody_assignments=selected,
            )
        )
    plan = {
        "schema": "REPOSITORY_DOCUMENT_PLAN_V1",
        "company": company,
        "branch": branch,
        "git_commit": _git(root, "rev-parse", "HEAD"),
        "organization_sha256": _digest(organization_snapshot),
        "documents": prepared,
        "qualification": QUALIFICATION,
    }
    # Detach the caller's mutable dictionaries from the pinned plan.
    plan = json.loads(json.dumps(plan, allow_nan=False))
    return dict(plan, plan_sha256=_digest(plan))


def sync_repository_documents(store, *, repository, plan, organization_snapshot, command_id):
    """Per-document durable commits; retry the identical plan/command after interruption.

    Availability starts at real ingestion, not effective date or git timestamp. No grants.
    """
    command = _id(command_id)
    raw = {k: v for k, v in plan.items() if k != "plan_sha256"}
    if _digest(raw) != plan.get("plan_sha256"):
        raise CompanyStoreError("Document plan integrity failure")
    entries = [
        {k: v for k, v in x.items() if k not in {"sha256", "git_blob", "custody_assignments"}}
        for x in plan["documents"]
    ]
    checked = plan_repository_documents(
        repository,
        manifest={"company": plan["company"], "branch": plan["branch"], "documents": entries},
        organization_snapshot=organization_snapshot,
    )
    if checked != plan:
        raise CompanyStoreError("Repository or custody pins changed; replan required")
    # Re-read and validate every original before the first write.
    contents = [_source(Path(repository).absolute(), x["path"])[0] for x in plan["documents"]]
    if any(
        hashlib.sha256(data).hexdigest() != x["sha256"]
        for x, data in zip(plan["documents"], contents, strict=True)
    ):
        raise CompanyStoreError("Source changed during planning")
    results = []
    for item, content in zip(plan["documents"], contents, strict=True):
        system = "REPO-" + hashlib.sha256(item["document_id"].encode()).hexdigest()[:24]
        operation = "RD-" + _digest([command, item["document_id"]])
        # Preserve initial availability on exact replay; append_version checks full fingerprint.
        with store._db() as db:
            previous = db.execute(
                "SELECT available_at FROM versions WHERE command_id=?", (operation,)
            ).fetchone()
        available = previous[0] if previous else _now()
        store.register_system(plan["company"], plan["branch"], system, item["owner_id"])
        results.append(
            store.append_version(
                plan["company"],
                plan["branch"],
                system,
                item["document_id"],
                expected_version=item["expected_version"],
                command_id=operation,
                event_at=None,
                available_at=available,
                content=content,
                origin=ORIGIN,
                provenance={
                    "source_reference": item["path"],
                    "name": Path(item["path"]).name,
                    "control_ids": item["control_ids"],
                    "custody_status": "PROVISIONAL_DOCUMENTARY_CUSTODY",
                    "custody_basis": "PINNED_SCOPED_PRIMARY_ASSIGNMENT_NOT_HISTORICAL_AUTHORSHIP",
                    "classification": "REPOSITORY_SYNTHETIC_DOCUMENT",
                    "operational_fact_status": (
                        "DOCUMENTARY_DESIGN_NOT_OPERATING_EVIDENCE; SOURCE_STATE="
                        + item["source_authority"]
                    ),
                    "source_authority": item["source_authority"],
                    "event_time_state": "UNKNOWN_BUSINESS_EVENT",
                    "document": item,
                    "plan_sha256": plan["plan_sha256"],
                    "git_commit": plan["git_commit"],
                    "organization_sha256": plan["organization_sha256"],
                    "qualification": QUALIFICATION,
                    "availability_basis": "REAL_INGESTION_NOT_HISTORICAL_PUBLICATION",
                    "authority_basis": "SOURCE_STATED_OPERATOR_MAPPED_NOT_NEW_APPROVAL",
                },
            )
        )
    return {
        "schema": "REPOSITORY_DOCUMENT_SYNC_V1",
        "plan_sha256": plan["plan_sha256"],
        "atomicity": "PER_DOCUMENT_REPLAYABLE_NOT_GLOBAL_TRANSACTION",
        "records": results,
    }
