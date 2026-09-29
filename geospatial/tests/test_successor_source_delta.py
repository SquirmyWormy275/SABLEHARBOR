"""Independent population and source-byte checks for the successor ledger."""

import gzip
import hashlib
import json
import subprocess

from geospatial.successor_20260928 import source_delta as review


def test_delta_matches_git_population_and_saved_artifact():
    result = review.build()
    paths = subprocess.check_output(
        ["git", "diff", "--name-only", review.FROM, review.THROUGH],
        cwd=review.ROOT,
        text=True,
    ).splitlines()
    assert len(paths) == len(set(paths)) == 1415
    assert [r["source_path"] for r in result["rows"]] == sorted(paths)
    saved = json.loads(gzip.decompress((review.OUTPUT / "SOURCE_DELTA.json.gz").read_bytes()))
    assert saved == result
    assert json.loads((review.OUTPUT / "SUMMARY.json").read_text()) == result["summary"]


def test_controlling_canon_and_selected_company_sources_have_exact_review():
    rows = {r["source_path"]: r for r in review.build()["rows"]}
    canon = {p for p in rows if p.startswith("docs/canon/")}
    assert canon == {"docs/canon/" + n for n in review.CANON_FINDINGS}
    assert all(rows[p]["review_level"] == "FULL_TEXT_CANON_GEOGRAPHIC_REVIEW" for p in canon)
    assert all(
        rows[p]["review_level"] == "TARGETED_DOMAIN_GEOGRAPHIC_REVIEW"
        for p in review.DOMAIN_FINDINGS
    )
    for path in (
        "docs/canon/HEADQUARTERS_VISUAL_WITHDRAWAL_2026-09-22.md",
        "docs/canon/ARU_ADMINISTRATIVE_COMPLETION_2026-09-22.md",
        "enterprise/operations/source/completed_period_2026_08.json",
    ):
        row = rows[path]
        assert (
            row["through_sha256"] == hashlib.sha256((review.ROOT / path).read_bytes()).hexdigest()
        )
    assert (
        "superseded" in rows["docs/canon/GEOGRAPHIC_COMPLETION_2026-09-13.md"]["geographic_finding"]
    )
    assert (
        "unlocated" in rows["docs/canon/GEOGRAPHIC_COMPLETION_2026-09-13.md"]["geographic_finding"]
    )


def test_boundary_labels_do_not_masquerade_as_full_text_review():
    result = review.build()
    assert result["summary"]["canon_full_text"] == 9
    assert result["summary"]["targeted_domain"] == 12
    assert all(
        r["review_level"] != "FULL_TEXT_CANON_GEOGRAPHIC_REVIEW"
        for r in result["rows"]
        if not r["source_path"].startswith("docs/canon/")
    )
    assert "does not close issue 108" in result["remaining"]


def test_compressed_artifact_reproduces_exact_bytes(tmp_path, monkeypatch):
    checked_in = (review.OUTPUT / "SOURCE_DELTA.json.gz").read_bytes()
    monkeypatch.setattr(review, "OUTPUT", tmp_path)
    review.write()
    assert (tmp_path / "SOURCE_DELTA.json.gz").read_bytes() == checked_in
    assert checked_in[9] == 255  # gzip's platform-independent OS marker
