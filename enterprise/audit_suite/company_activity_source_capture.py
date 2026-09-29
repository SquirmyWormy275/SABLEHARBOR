"""Explicit selected metadata capture; caller content pins are never discovered."""

import json
from pathlib import Path

from .company_activity_plan_sources import _check, _hash, _manifest, _private, resolve_source
from .company_lifecycle_activity import FIELDS, LifecycleSourceRef, read_inputs
from .company_store import _id
from .operating_source_bridge import encoded

CAPTURE_BASIS = "CAPTURED_AFTER_VERIFIED_PRODUCER_NOT_CALLER_PREDECLARED"


def capture_source(
    *,
    source_root,
    source_manifest_path,
    expected_manifest_sha256,
    source_store_id,
    expected_records,
    consumed_at,
    destination,
):
    """Capture metadata once, then independently recheck the frozen pin strictly.

    This reads only a completed, caller-pinned operator producer. The caller owns
    DAG authorization, immutable receipt publication and subsequent strict checks.
    Nothing here creates a source, audit, grant or destination.
    """
    root, manifest, target = map(Path, (source_root, source_manifest_path, destination))
    _private(root, directory=True)
    _private(target.parent, directory=True)
    _check(
        target.is_absolute()
        and ".." not in target.parts
        and not any(p.is_symlink() for p in (target, *target.parents))
        and not target.resolve().is_relative_to(manifest.parent.resolve())
        and not manifest.parent.resolve().is_relative_to(target.resolve()),
        "Private consumer destination outside source job required",
    )
    if target.exists():
        _private(target, directory=True)
    _id(source_store_id)
    _check(
        isinstance(expected_records, list) and 2 <= len(expected_records) <= 8,
        "Two to8 caller-declared exact native records required",
    )
    # Detach caller data before any filesystem read; never derive missing pins.
    records = json.loads(encoded(expected_records))
    refs, seen = [], set()
    for row in records:
        _check(
            isinstance(row, dict) and set(row) == set(FIELDS),
            "Exact caller-declared native six-field reference required",
        )
        for key in FIELDS[:4]:
            _id(row[key])
        _check(
            type(row["version"]) is int and row["version"] > 0 and _hash(row["sha256"]),
            "Positive integer version and caller-declared content SHA256 required",
        )
        identity = tuple(row[k] for k in FIELDS[:-1])
        _check(identity not in seen, "Duplicate selected native identity")
        seen.add(identity)
        refs.append(LifecycleSourceRef(**row))
    _check(
        len({(ref.company, ref.branch) for ref in refs}) == 1,
        "One exact source company/branch required",
    )
    _manifest(manifest, expected_manifest_sha256, root)
    rows, captured_pin = read_inputs(root, tuple(refs))
    # resolve_source reads again and compares against this value. A changed
    # producer cannot cause an unnoticed second capture or pin replacement.
    result = resolve_source(
        source_root=root,
        source_manifest_path=manifest,
        expected_manifest_sha256=expected_manifest_sha256,
        binding={
            "source_store_id": source_store_id,
            "expected_records": records,
            "expected_selected_metadata_sha256": captured_pin,
        },
        consumed_at=consumed_at,
        destination=target,
    )
    result["receipt"] = {
        **result["receipt"],
        "schema": "CAPTURED_ACTIVITY_SOURCE_BINDING_V1",
        "capture_basis": CAPTURE_BASIS,
        "captured_selected_metadata_sha256": captured_pin,
        "metadata_fields": sorted({key for row in rows for key in row if key != "content"}),
        "caller_predeclared_content_pins": True,
        "caller_predeclared_selected_metadata_pin": False,
        "capture_count": 1,
        "strict_recheck_completed": True,
    }
    return result
