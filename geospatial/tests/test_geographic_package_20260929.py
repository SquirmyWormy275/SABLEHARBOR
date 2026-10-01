"""Bound the new complete distribution without changing the 1.4 release."""

from pathlib import Path

import pytest

from geospatial.successor_20260929_final import package, verify_package


def test_supplement_contains_all_controlling_new_sources():
    paths = package.source_paths()
    assert len(paths) >= 30
    assert "docs/canon/GEOGRAPHIC_SYNTHETIC_SCOPE_DISPOSITION_2026-09-29.md" in paths
    assert "geospatial/successor_20260929_final/SOURCE_DELTA.json.gz" in paths
    assert (
        "geospatial/successors/rail_history_2026_09_29/ATTRIBUTION_CORRECTION_2026-09-29.md"
        in paths
    )
    assert "geospatial/successors/rail_history_2026_09_29/report.json" in paths
    assert "geospatial/engineering_review/interface_successor_20260929/register.json" in paths
    assert "industrial/successors/rail_2026_09_29/reperform-result.json" in paths
    assert all((package.ROOT / path).is_file() for path in paths)
    assert package.BASE_SHA256 == verify_package.EXPECTED_BASE_SHA256


def test_rejects_wrong_predecessor_before_writing_output(tmp_path: Path):
    wrong = tmp_path / "base.zip"
    wrong.write_bytes(b"wrong")
    output = tmp_path / "release.zip"
    with pytest.raises(ValueError, match="Immutable 1.4 package hash mismatch"):
        package.build(wrong, output, preview=True)
    assert not output.exists()


@pytest.mark.parametrize("name", ["../escaped", "/absolute", "a\\b", "a/../../b"])
def test_import_rejects_unsafe_member_paths(name):
    assert not verify_package.safe(name)
