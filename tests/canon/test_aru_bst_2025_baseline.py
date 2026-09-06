import json
from pathlib import Path


BASELINE_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "structured"
    / "aru_bst_2025_baseline_model.json"
)


def _baseline() -> dict:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def test_bst_operating_baseline_reconciles() -> None:
    baseline = _baseline()

    freight_revenue = sum(item["revenue"] for item in baseline["bst_revenue_schedule"])
    other_revenue = sum(item["revenue"] for item in baseline["bst_other_revenue"])
    operating_expense = sum(item["expense"] for item in baseline["bst_expense_schedule"])

    assert sum(item["carloads"] for item in baseline["bst_revenue_schedule"]) == 9_000
    assert freight_revenue + other_revenue == 15_500_000
    assert operating_expense == 14_000_000
    assert freight_revenue + other_revenue - operating_expense == 1_500_000
    assert sum(item["fte"] for item in baseline["bst_headcount_schedule"]) == 58


def test_aru_consolidated_baseline_reconciles() -> None:
    baseline = _baseline()
    segments = baseline["aru_segment_summary"]
    summary = baseline["consolidated_summary"]

    assert sum(item["revenue"] for item in segments) == summary["revenue"] == 42_000_000
    assert (
        sum(item["normalized_ebitda"] for item in segments)
        == summary["normalized_ebitda"]
        == 9_800_000
    )
    assert sum(item["employees"] for item in segments) == summary["employees"] == 131
    assert (
        sum(item["sustaining_capex"] for item in segments)
        == summary["sustaining_capex"]
        == 3_300_000
    )
    assert (
        summary["normalized_ebitda"] - summary["sustaining_capex"]
        == summary["ebitda_less_sustaining_capex"]
        == 6_500_000
    )


def test_baseline_preserves_acquisition_and_red_wash_boundaries() -> None:
    baseline = _baseline()

    assert baseline["as_of_date"] == "2025-12-31"
    assert baseline["acquisition_close_date"] == "2026-01-07"
    assert baseline["bst_operating_profile"]["annual_revenue_carloads"] == 9_000
    assert baseline["consolidated_summary"]["deferred_catch_up_capex"] == 11_000_000
    assert baseline["customer_concentration"]["meaningful_renewal_risk_count"] == 1
    assert any(
        "FIN-Q-005" in item for item in baseline["governance"]["supersession_candidates"]
    )
    assert any(
        "FIN-Q-006" in item for item in baseline["governance"]["supersession_candidates"]
    )
