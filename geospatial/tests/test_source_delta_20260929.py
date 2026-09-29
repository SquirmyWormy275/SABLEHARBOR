"""Pin the next accepted 83-path geographic source interval exactly."""

import gzip
import hashlib
import json
import subprocess

from geospatial.successor_20260929 import source_delta as review


def test_exact_changed_path_population_and_artifact():
    result = review.build()
    paths = subprocess.check_output(
        ["git", "diff", "--name-only", review.FROM, review.THROUGH],
        cwd=review.ROOT,
        text=True,
    ).splitlines()
    assert len(paths) == len(set(paths)) == 83
    assert [r["source_path"] for r in result["rows"]] == sorted(paths)
    saved = json.loads(gzip.decompress((review.HERE / "SOURCE_DELTA.json.gz").read_bytes()))
    assert saved == result
    assert json.loads((review.HERE / "SUMMARY.json").read_text()) == result["summary"]
    assert result["summary"]["changed_controlling_canon"] == 1


def test_material_source_meaning_and_exact_bytes():
    rows = {row["source_path"]: row for row in review.build()["rows"]}
    assert len(review.FINDINGS) == 11
    assert all(
        rows[path]["review_level"] == "TARGETED_GEOGRAPHIC_SOURCE_REVIEW"
        for path in review.FINDINGS
    )
    for path in review.FINDINGS:
        accepted_bytes = subprocess.check_output(
            ["git", "show", f"{review.THROUGH}:{path}"], cwd=review.ROOT
        )
        assert rows[path]["through_sha256"] == hashlib.sha256(accepted_bytes).hexdigest()
    assert (
        "40 total route-miles"
        in rows["industrial/successors/rail_2026_09_29/source.json"]["geographic_finding"]
    )
    assert (
        "unknown"
        in rows["geospatial/engineering_review/historical_alignment_2026_09_29/source.json"][
            "geographic_finding"
        ]
    )
    assert (
        "no physical site ID"
        in rows["enterprise/operations/source/portal_2027_reference_controls_case_2026_09_29.json"][
            "geographic_finding"
        ]
    )
    canon = "docs/canon/COMPANY_SYNTHETIC_SCOPE_DISPOSITION_2026-09-29.md"
    assert set(path for path in rows if path.startswith("docs/canon/")) == {canon}
    assert rows[canon]["review_level"] == "CONTROLLING_CANON_FULL_TEXT_GEOGRAPHIC_REVIEW"
    assert "no site" in rows[canon]["geographic_finding"]


def test_compressed_output_reproduces_byte_for_byte(tmp_path, monkeypatch):
    expected = (review.HERE / "SOURCE_DELTA.json.gz").read_bytes()
    monkeypatch.setattr(review, "HERE", tmp_path)
    review.write()
    assert (tmp_path / "SOURCE_DELTA.json.gz").read_bytes() == expected
    assert expected[9] == 255
