"""The post-#185 source review uses accepted Git bytes and an exact population."""

import gzip
import hashlib
import json
import subprocess

import pytest

from geospatial.successor_20260929_final import source_delta as review


def test_exact_accepted_path_population_and_artifact():
    result = review.build()
    paths = subprocess.check_output(
        ["git", "diff", "--name-only", review.FROM, review.THROUGH],
        cwd=review.ROOT,
        text=True,
    ).splitlines()
    assert len(paths) == len(set(paths)) == 18
    assert [r["source_path"] for r in result["rows"]] == sorted(paths)
    assert result["summary"]["changed_controlling_canon"] == 0
    assert result["summary"]["levels"]["TARGETED_GEOGRAPHIC_SOURCE_REVIEW"] == 2
    assert (
        json.loads(gzip.decompress((review.HERE / "SOURCE_DELTA.json.gz").read_bytes())) == result
    )
    assert json.loads((review.HERE / "SUMMARY.json").read_text()) == result["summary"]


def test_accepted_source_bytes_and_semantic_limits():
    rows = {row["source_path"]: row for row in review.build()["rows"]}
    for path, row in rows.items():
        accepted_bytes = subprocess.check_output(
            ["git", "show", f"{review.THROUGH}:{path}"], cwd=review.ROOT
        )
        assert row["through_sha256"] == hashlib.sha256(accepted_bytes).hexdigest()
    interface = rows["geospatial/engineering_review/interface_successor_20260929/source.json"]
    history = rows["geospatial/successors/rail_history_2026_09_29/source.json"]
    assert "no-mine-spur" in interface["geographic_finding"]
    assert "unknown" in history["geographic_finding"]
    assert all(not path.startswith("docs/canon/") for path in rows)


def test_missing_review_row_rejected(monkeypatch):
    findings = dict(review.FINDINGS)
    findings.pop("geospatial/successors/rail_history_2026_09_29/source.json")
    monkeypatch.setattr(review, "FINDINGS", findings)
    with pytest.raises(ValueError, match="fresh substantive review"):
        review.build()


def test_compressed_output_reproduces(tmp_path, monkeypatch):
    expected = (review.HERE / "SOURCE_DELTA.json.gz").read_bytes()
    monkeypatch.setattr(review, "HERE", tmp_path)
    review.write()
    assert (tmp_path / "SOURCE_DELTA.json.gz").read_bytes() == expected
    assert expected[9] == 255
