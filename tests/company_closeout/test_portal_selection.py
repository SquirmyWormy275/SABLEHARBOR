import pytest

from tools.company_closeout.edition import EditionError
from tools.company_closeout.portal_rehearsal import review_plan


def inputs():
    contract = dict(
        edition_id="test",
        components=[
            dict(
                id="finance",
                members=[{}, {}, {}],
                population_definition="Three source originals, not three ledger events",
                fact_status="SYNTHETIC",
            )
        ],
    )
    originals = [
        ("finance", p, "2026-09-22T00:00:00Z", p + "-hash", size, [dict(record=p, kind="ORIGINAL")])
        for p, size in [("empty", 0), ("small", 5), ("large", 100)]
    ]
    records = [
        ("finance", p, "2026-09-22T00:00:00Z", p + "-hash") for p in ["empty", "small", "large"]
    ]
    return contract, originals, records


def test_declares_surrounding_population_and_does_not_select_empty_over_evidence(tmp_path):
    plan = review_plan(tmp_path, *inputs())
    assert [r["path"] for r in plan["selected"]] == ["small"]
    assert plan["surrounding_population"][0]["members"] == 3
    assert plan["available_at"] == "2026-09-22T00:00:00Z"


def test_explicit_selection_preserves_real_source_identity(tmp_path):
    plan = review_plan(tmp_path, *inputs(), review_paths=["large"])
    assert plan["selected"][0]["sha256"] == "large-hash"
    assert plan["selected"][0]["parts"][0]["sha256"] == "large-hash"


@pytest.mark.parametrize("paths", [[], ["missing"], ["small", "small"]])
def test_invalid_or_duplicate_selection_cannot_claim_review(tmp_path, paths):
    with pytest.raises(EditionError, match="distinct existing"):
        review_plan(tmp_path, *inputs(), review_paths=paths)
