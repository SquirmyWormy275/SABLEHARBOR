import copy
import json

import pytest

from .rail_authority import DIRECTORY, SOURCE, threshold_on, validate


def test_primary_notices_and_event_day_review():
    reporting = json.loads((DIRECTORY / "rail_reporting_successor.json").read_text())
    result = validate(json.loads(SOURCE.read_text()), reporting)
    assert result["unrecovered_original_notices"] == 0
    assert threshold_on("2021-01-07", reporting) == 10700
    assert threshold_on("2021-01-08", reporting) == 11200


@pytest.mark.parametrize("change", ["snapshot", "proposal", "future", "event", "threshold"])
def test_authority_mutation_is_rejected(change):
    data = copy.deepcopy(json.loads(SOURCE.read_text()))
    reporting = json.loads((DIRECTORY / "rail_reporting_successor.json").read_text())
    if change == "snapshot":
        data["annual_notices"][0]["sha256"] = "0" * 64
    elif change == "proposal":
        next(r for r in data["rule_index"]["records"] if r["document_number"] == "2025-12179")["effective_on"] = "2025-07-01"
    elif change == "future":
        next(r for r in data["rule_index"]["records"] if r["document_number"] == "2026-17791")["effective_on"] = "2026-08-01"
    elif change == "event":
        data["events"].pop()
    else:
        reporting["thresholds"]["2025"]["usd"] = 100000
    with pytest.raises(ValueError):
        validate(data, reporting)
