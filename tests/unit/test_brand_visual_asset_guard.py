from __future__ import annotations

import json
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = runpy.run_path(str(ROOT / "tools/brand/validate_red_wash_visual_assets.py"))
APPROVED_ASSETS = VALIDATOR["APPROVED_ASSETS"]
VISUAL_MANIFEST = VALIDATOR["VISUAL_MANIFEST"]
VisualAssetValidationError = VALIDATOR["VisualAssetValidationError"]
assert_safe_generation_output = VALIDATOR["assert_safe_generation_output"]
validate_red_wash_visual_assets = VALIDATOR["validate_red_wash_visual_assets"]


def test_approved_red_wash_visual_assets_are_byte_exact() -> None:
    report = validate_red_wash_visual_assets(ROOT)

    assert report["status"] == "PASS"
    assert report["manifest_id"] == "SH-BRAND-PS-RW-001"
    assert {asset["path"] for asset in report["assets"]} == set(APPROVED_ASSETS)
    assert {asset["path"]: asset["sha256"] for asset in report["assets"]} == {
        path: facts["sha256"] for path, facts in APPROVED_ASSETS.items()
    }


@pytest.mark.parametrize(
    "relative_output",
    [
        ".",
        "assets",
        "assets/brand",
        "assets/brand/logos",
        "assets/brand/maps",
        VISUAL_MANIFEST.as_posix(),
        "assets/brand/logos/pale_sun__canonical.png",
    ],
)
def test_generation_refuses_output_that_could_remove_controlled_sources(
    relative_output: str,
) -> None:
    with pytest.raises(VisualAssetValidationError, match="cleanup would endanger"):
        assert_safe_generation_output(ROOT / relative_output, ROOT)


def test_generation_allows_isolated_build_directory(tmp_path: Path) -> None:
    assert_safe_generation_output(tmp_path / "brand-build", ROOT)


def test_manifest_cannot_silently_replace_an_approved_digest(tmp_path: Path) -> None:
    manifest_path = tmp_path / VISUAL_MANIFEST
    manifest_path.parent.mkdir(parents=True)
    manifest = json.loads((ROOT / VISUAL_MANIFEST).read_text(encoding="utf-8"))
    manifest["assets"][0]["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(VisualAssetValidationError, match="sha256.*drifted"):
        validate_red_wash_visual_assets(tmp_path)
