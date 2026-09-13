import copy
import gzip
import json
import subprocess

import pytest

from geospatial.finalization import source_review, visual_review
from geospatial.finalization.prospects import recover
from geospatial.finalization.screen import BASE, ROOT, screen, equivalent


def test_selected_footprints_have_complete_screening_and_preserve_prior_geometry():
    report = screen()
    assert equivalent(report, json.loads((BASE / "SITE_SCREEN.json").read_text()))
    assert len(report["records"]) == 3
    for row in report["records"]:
        assert row["imagery_sources"] and row["flood_intersections"]
        assert row["elevation"]["valid_cells"] > 100
        assert not any(r["intersects"] for r in row["archived_reference_screen"])
    paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", "3213541", "--", "geospatial/geojson"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    for path in paths:
        assert (ROOT / path).read_bytes() == subprocess.check_output(
            ["git", "show", "3213541:" + path], cwd=ROOT
        ), path


def test_rejected_prospects_carry_inquiry_dates_without_tenure():
    rows = recover()
    assert len(rows) == 3
    assert [r["review_closed"] for r in rows] == [
        "2024-02-16",
        "2024-06-14",
        "2024-10-04",
    ]
    for row in rows:
        assert row["review_started"] < row["review_closed"]
        assert all(
            row[k] is None
            for k in (
                "geometry",
                "occupancy_start",
                "occupancy_end",
                "acquired_on",
                "owner_entity",
            )
        )


def test_fixed_baseline_adjudication_is_complete_and_rejects_an_omission(tmp_path, monkeypatch):
    summary, rows = source_review.review()
    assert summary["cumulative_reviewed_carriers"] == 78145
    assert len(rows) == len({r["occurrence_id"] for r in rows}) == 6896
    assert summary["remaining_baseline_carriers"] == 0
    assert not summary["issue_108_complete"]  # Other acceptance dimensions remain separate.
    packet = json.loads(gzip.decompress((BASE / "GROUP_DECISIONS.json.gz").read_bytes()))
    packet["groups"].pop()
    (tmp_path / "GROUP_DECISIONS.json.gz").write_bytes(
        gzip.compress(json.dumps(packet).encode(), mtime=0)
    )
    (tmp_path / "EXTRACTED_RESIDUAL.json.gz").write_bytes(
        (BASE / "EXTRACTED_RESIDUAL.json.gz").read_bytes()
    )
    monkeypatch.setattr(source_review, "BASE", tmp_path)
    with pytest.raises(ValueError, match="Missing editorial disposition"):
        source_review.review()


def test_visual_review_rejects_missing_and_changed_image_appearances():
    reviewed = json.loads((BASE / "VISUAL_REVIEW.json").read_text())
    inventory = {"records": [a for r in reviewed["records"] for a in r["appearances"]]}
    summary, images, appearances = visual_review.verify(inventory)
    assert len(images) == summary["unique_images"] == 135
    assert len(appearances) == summary["appearances"] == 290
    altered = copy.deepcopy(inventory)
    altered["records"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="differs"):
        visual_review.verify(altered)
    altered = copy.deepcopy(inventory)
    altered["records"].append({**altered["records"][0], "record_id": "unreviewed-extra"})
    with pytest.raises(ValueError, match="no visual disposition"):
        visual_review.verify(altered)


def test_reviewed_source_ledger_rejects_unreviewed_canon_population(monkeypatch):
    from geospatial.finalization import source_ledger

    ledger = source_ledger.build()
    assert ledger["summary"]["baseline_files"] == 919
    assert ledger["summary"]["canon_deltas"] == 17
    assert all(r["current_sha256"] or r["baseline_sha256"] for r in ledger["subsequent_changes"])
    monkeypatch.setattr(source_ledger, "CANON_FINDINGS", {})
    with pytest.raises(ValueError, match="canon delta population"):
        source_ledger.build()


def test_screen_comparison_allows_only_numerical_platform_noise():
    expected = {"distance_m": 665.6317066783402, "intersects": False, "sha256": "unchanged"}
    assert equivalent({**expected, "distance_m": 665.6317066782967}, expected)
    assert not equivalent({**expected, "distance_m": 665.6317}, expected)
    assert not equivalent({**expected, "intersects": True}, expected)
    assert not equivalent({**expected, "sha256": "changed"}, expected)
    assert not equivalent({**expected, "extra": None}, expected)
