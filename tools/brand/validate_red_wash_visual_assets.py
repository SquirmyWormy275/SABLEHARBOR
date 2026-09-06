"""Validate the owner-approved Pale Sun and Red Wash raster sources.

These four files are controlling source artwork.  Their bytes are not generator
inputs that may be normalized or refreshed: a different digest is a different
asset and requires an explicit identity decision.
"""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
VISUAL_MANIFEST = Path("assets/brand/red_wash_visual_manifest.json")

APPROVED_MANIFEST: dict[str, Any] = {
    "manifest_id": "SH-BRAND-PS-RW-001",
    "version": "1.0.0",
    "decision_date": "2026-09-05",
    "approval_state": "LOCKED",
    "binary_ingestion_state": "COMPLETE",
    "source_bundle": {
        "filename": "RED_WASH_APPROVED_VISUAL_ASSETS.zip",
        "manifest_id": "SH-BRAND-PS-RW-001-HANDOFF-BUNDLE",
        "sha256": "92eda63de9dfe6b102349f9c0d8da27ab8b09591d418d505bc89d885630100af",
        "bytes": 7_211_032,
    },
}

APPROVED_ASSETS: dict[str, dict[str, Any]] = {
    "assets/brand/logos/pale_sun__canonical.png": {
        "sha256": "eedcabfca73460e8ff5ad72864c9f669ba2375097b05daa2912f30c9ff35c025",
        "bytes": 837_461,
        "width": 1_536,
        "height": 1_024,
    },
    "assets/brand/logos/red_wash__canonical.png": {
        "sha256": "7c26b8afd7954045d9dd4b5c691ba820cdce2e3ccb8e41ac6873b103f0c59720",
        "bytes": 738_834,
        "width": 1_774,
        "height": 887,
    },
    "assets/brand/maps/red_wash__site_overview.png": {
        "sha256": "8dbb0053c4a563d57d5a24be4f4687dc11e2e00e2b1e62c279d9be945f68d77a",
        "bytes": 3_230_867,
        "width": 1_536,
        "height": 1_024,
    },
    "assets/brand/maps/red_wash__underground_plan.png": {
        "sha256": "0658de3b7c63ecc9757b545f29895eab51801b2148cb3862935620b6049a7dda",
        "bytes": 2_401_412,
        "width": 1_536,
        "height": 1_024,
    },
}


class VisualAssetValidationError(ValueError):
    """Raised when a controlled visual asset or its manifest has drifted."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_equal(label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise VisualAssetValidationError(
            f"{label} drifted: expected {expected!r}, found {actual!r}"
        )


def png_dimensions(path: Path) -> tuple[int, int]:
    """Read PNG dimensions from the mandatory IHDR chunk using the stdlib."""

    with path.open("rb") as handle:
        header = handle.read(24)
    if (
        len(header) != 24
        or header[:8] != b"\x89PNG\r\n\x1a\n"
        or header[8:12] != b"\x00\x00\x00\r"
        or header[12:16] != b"IHDR"
    ):
        raise VisualAssetValidationError(
            f"controlled visual asset is not a valid PNG: {path}"
        )
    return struct.unpack(">II", header[16:24])


def validate_red_wash_visual_assets(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Return a verification report or fail on any manifest/binary drift."""

    repo_root = repo_root.resolve()
    manifest_path = repo_root / VISUAL_MANIFEST
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise VisualAssetValidationError(
            f"controlled visual manifest is missing or not a regular file: {manifest_path}"
        )

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VisualAssetValidationError(
            f"cannot parse controlled visual manifest: {manifest_path}"
        ) from exc

    for field in (
        "manifest_id",
        "version",
        "decision_date",
        "approval_state",
        "binary_ingestion_state",
        "source_bundle",
    ):
        _require_equal(
            f"{VISUAL_MANIFEST.as_posix()}::{field}",
            manifest.get(field),
            APPROVED_MANIFEST[field],
        )

    entries = manifest.get("assets")
    if not isinstance(entries, list):
        raise VisualAssetValidationError("visual manifest assets must be an array")

    indexed: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("canonical_path"), str):
            raise VisualAssetValidationError(
                "every visual manifest asset must have a string canonical_path"
            )
        canonical_path = entry["canonical_path"]
        if canonical_path in indexed:
            raise VisualAssetValidationError(
                f"duplicate visual manifest canonical_path: {canonical_path}"
            )
        indexed[canonical_path] = entry

    _require_equal(
        "controlled visual asset path set",
        set(indexed),
        set(APPROVED_ASSETS),
    )

    verified: list[dict[str, Any]] = []
    for relative_path, expected in APPROVED_ASSETS.items():
        entry = indexed[relative_path]
        for field, expected_value in expected.items():
            _require_equal(
                f"{VISUAL_MANIFEST.as_posix()}::{relative_path}::{field}",
                entry.get(field),
                expected_value,
            )
        _require_equal(
            f"{VISUAL_MANIFEST.as_posix()}::{relative_path}::approval_state",
            entry.get("approval_state"),
            "LOCKED",
        )

        asset_path = repo_root / relative_path
        if not asset_path.is_file() or asset_path.is_symlink():
            raise VisualAssetValidationError(
                f"controlled visual asset is missing or not a regular file: {asset_path}"
            )
        actual_bytes = asset_path.stat().st_size
        actual_sha256 = sha256(asset_path)
        _require_equal(f"{relative_path} byte count", actual_bytes, expected["bytes"])
        _require_equal(f"{relative_path} SHA-256", actual_sha256, expected["sha256"])

        actual_dimensions = png_dimensions(asset_path)
        _require_equal(
            f"{relative_path} dimensions",
            actual_dimensions,
            (expected["width"], expected["height"]),
        )
        verified.append(
            {
                "path": relative_path,
                "sha256": actual_sha256,
                "bytes": actual_bytes,
                "width": actual_dimensions[0],
                "height": actual_dimensions[1],
            }
        )

    return {
        "status": "PASS",
        "manifest": VISUAL_MANIFEST.as_posix(),
        "manifest_id": manifest["manifest_id"],
        "assets": verified,
    }


def assert_safe_generation_output(
    output_path: Path, repo_root: Path = REPO_ROOT
) -> None:
    """Refuse any build root whose deletion could remove controlled sources."""

    repo_root = repo_root.resolve()
    output_path = output_path.resolve()
    protected_paths = [
        repo_root / VISUAL_MANIFEST,
        *(repo_root / relative_path for relative_path in APPROVED_ASSETS),
    ]
    endangered = [
        path
        for path in protected_paths
        if path == output_path or output_path in path.parents
    ]
    if endangered:
        joined = ", ".join(str(path) for path in endangered)
        raise VisualAssetValidationError(
            f"refusing generation output {output_path}: cleanup would endanger "
            f"controlled visual source(s): {joined}"
        )


def main() -> None:
    print(json.dumps(validate_red_wash_visual_assets(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
