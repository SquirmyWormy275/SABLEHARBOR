"""Exact selected-source prerequisite for linked activity plans; never generates records."""

import hashlib
import json
import os
import stat
from pathlib import Path

from .company_lifecycle_activity import FIELDS, LifecycleSourceRef, read_inputs
from .company_store import CompanyStoreError, _id, _time
from .operating_source_bridge import encoded

MAX_MANIFEST_BYTES = 512 * 1024
MAX_JOB_BYTES = 256 * 1024 * 1024


def _check(condition, message):
    if not condition:
        raise CompanyStoreError(message)


def _hash(value):
    return (
        isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    )


def _private(path, *, directory=False):
    _check(
        path.is_absolute()
        and ".." not in path.parts
        and not any(p.is_symlink() for p in (path, *path.parents)),
        "Canonical nonalias path required",
    )
    info = path.stat()
    _check(
        not info.st_mode & 0o077
        and (
            stat.S_ISDIR(info.st_mode)
            if directory
            else stat.S_ISREG(info.st_mode) and info.st_nlink == 1
        ),
        "Private regular source file/directory required",
    )
    return info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_ctime_ns


def _file(path, *, limit, retain=False):
    before = _private(path)
    total, digest, parts = 0, hashlib.sha256(), []
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        _check((info.st_dev, info.st_ino) == before[:2], "Source file changed before read")
        while block := stream.read(min(128 * 1024, limit + 1 - total)):
            total += len(block)
            _check(total <= limit, "Source manifest/member byte quota exceeded")
            digest.update(block)
            if retain:
                parts.append(block)
    _check(_private(path) == before, "Source file changed during read")
    return digest.hexdigest(), total, b"".join(parts)


def _manifest(path, expected, source_root):
    _check(_hash(expected), "Exact source manifest SHA256 required")
    stamp = _private(path.parent, directory=True)
    actual, _, raw = _file(path, limit=MAX_MANIFEST_BYTES, retain=True)
    _check(actual == expected, "Source job manifest pin differs")

    def pairs(items):
        result = {}
        for key, value in items:
            _check(key not in result, "Duplicate source manifest key")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw,
            object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except (ValueError, UnicodeError) as error:
        raise CompanyStoreError("Strict source job manifest required") from error
    _check(
        isinstance(value, dict)
        and value.get("format") == "PRIVATE_COMPANY_ACTIVITY_RUN_V1"
        and value.get("audit_created") is False
        and value.get("grants_created") is False,
        "Completed company-only source job manifest required",
    )
    counts = value.get("counts")
    _check(
        isinstance(counts, dict)
        and all(type(counts.get(k)) is int and counts[k] == 0 for k in ("grants", "collections")),
        "Source job must not assert audit grants/collections",
    )
    members = value.get("members")
    _check(
        isinstance(members, dict)
        and 1 <= len(members) <= 5000
        and "company/company.sqlite3" in members,
        "Bounded explicit native source members required",
    )
    _check(source_root == path.parent / "company", "Source root differs from manifest native store")
    total = 0
    for name, checksum in members.items():
        _check(isinstance(name, str) and bool(name), "Typed manifest member name required")
        relative = Path(name)
        _check(
            not relative.is_absolute()
            and relative.parts
            and ".." not in relative.parts
            and _hash(checksum),
            "Invalid source manifest member",
        )
        _check(str(relative) == name, "Canonical manifest member path required")
        member = path.parent / relative
        for parent in member.parents:
            _private(parent, directory=True)
            if parent == path.parent:
                break
        _check(member != path, "Manifest cannot include itself")
        digest, size, _ = _file(member, limit=MAX_JOB_BYTES - total)
        _check(digest == checksum, "Source job member pin differs")
        total += size
    _check(
        _private(path.parent, directory=True) == stamp,
        "Source job directory changed during verification",
    )
    return value, total


def resolve_source(
    *,
    source_root,
    source_manifest_path,
    expected_manifest_sha256,
    binding,
    consumed_at,
    destination,
):
    """Resolve existing exact rows and verify availability; return no automatic selectors.

    A caller must re-run this check before marking a consumer completed. No global
    transaction covers producer read, consumer generation and later verification.
    """
    source_root, manifest, destination = map(Path, (source_root, source_manifest_path, destination))
    _private(source_root, directory=True)
    _private(destination.parent, directory=True)
    _check(
        destination.is_absolute()
        and ".." not in destination.parts
        and not any(p.is_symlink() for p in (destination, *destination.parents))
        and not destination.resolve().is_relative_to(manifest.parent.resolve())
        and not manifest.parent.resolve().is_relative_to(destination.resolve()),
        "Private consumer destination outside source job required",
    )
    if destination.exists():
        _private(destination, directory=True)
    _check(
        isinstance(binding, dict)
        and set(binding)
        == {"source_store_id", "expected_records", "expected_selected_metadata_sha256"},
        "Exact selected-source binding required",
    )
    binding = json.loads(encoded(binding))
    _id(binding["source_store_id"])
    _check(
        _hash(binding["expected_selected_metadata_sha256"]),
        "Expected selected metadata SHA256 required",
    )
    records = binding["expected_records"]
    _check(
        isinstance(records, list) and 2 <= len(records) <= 8,
        "Two to8 exact expected records required",
    )
    refs, seen = [], set()
    for row in records:
        _check(
            isinstance(row, dict) and set(row) == set(FIELDS),
            "Exact native six-field reference required",
        )
        for key in FIELDS[:4]:
            _id(row[key])
        _check(
            type(row["version"]) is int and row["version"] > 0 and _hash(row["sha256"]),
            "Positive integer version and exact SHA256 required",
        )
        key = tuple(row[k] for k in FIELDS[:-1])
        _check(key not in seen, "Duplicate selected native identity")
        seen.add(key)
        refs.append(LifecycleSourceRef(**row))
    _check(
        len({(r.company, r.branch) for r in refs}) == 1, "One exact source company/branch required"
    )
    cutoff = _time(consumed_at)
    from datetime import datetime

    cutoff_time = datetime.fromisoformat(cutoff)
    job, job_bytes = _manifest(manifest, expected_manifest_sha256, source_root)
    rows, pin = read_inputs(source_root, tuple(refs))
    _check(
        pin == binding["expected_selected_metadata_sha256"], "Selected source metadata pin differs"
    )
    for row in rows:
        _check(
            row["event_at"] is not None and row["available_at"] is not None,
            "Known source event and availability instants required",
        )
        _check(
            datetime.fromisoformat(_time(row["event_at"])) <= cutoff_time
            and datetime.fromisoformat(_time(row["available_at"])) <= cutoff_time,
            "Selected source unavailable at consumer cutoff",
        )
    _manifest(manifest, expected_manifest_sha256, source_root)
    receipt = {
        "schema": "EXACT_ACTIVITY_SOURCE_BINDING_V1",
        "source_root": str(source_root),
        "source_manifest_path": str(manifest),
        "source_manifest_sha256": expected_manifest_sha256,
        "source_job_kind": job.get("kind"),
        "source_store_id": binding["source_store_id"],
        "source_label_basis": "EXPLICIT_CALLER_LABEL_NOT_INFERRED_NATIVE_PRODUCER_IDENTITY",
        "selected_records": records,
        "selected_metadata_sha256": pin,
        "selected_metadata": [{k: v for k, v in row.items() if k != "content"} for row in rows],
        "consumed_at": cutoff,
        "manifest_members_verified_bytes": job_bytes,
        "snapshot_isolation": "SELECTED_NATIVE_READ_TRANSACTION_PLUS_BEFORE_AFTER_MANIFEST_CHECKS",
        "chronology_claim": "SELECTED_INPUTS_AVAILABLE_BY_DECLARED_CUTOFF_ONLY",
        "coherent_operating_year": "NOT_ESTABLISHED",
        "audit_created": False,
        "grants_created": False,
    }
    return {"source_refs": tuple(refs), "source_versions_sha256": pin, "receipt": receipt}
