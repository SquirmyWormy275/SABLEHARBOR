"""Navigation refreshes preserve historical legal review and reject altered pins."""

import pytest

from tools.legal_gaps import validate_practical_work as review


def test_current_navigation_preserves_review():
    review.validate()


@pytest.mark.parametrize("date", ["2026-10-13", "2026-10-18"])
@pytest.mark.parametrize(
    "mutation", ["parent", "historical", "current", "previous", "state", "duplicate", "owner"]
)
def test_altered_navigation_or_owner_state_is_rejected(monkeypatch, date, mutation):
    original = review.json.loads

    def altered(content, *args, **kwargs):
        result = original(content, *args, **kwargs)
        if result.get("record_id") == f"SH-LEGAL-V3-NAVIGATION-SUCCESSOR-{date}":
            if mutation == "parent":
                result["previous_successor_sha256"] = "0" * 64
            elif mutation == "historical":
                result["records"][0]["historical_sha256"] = "0" * 64
            elif mutation == "current":
                result["records"][0]["current_sha256"] = "0" * 64
            elif mutation == "previous":
                result["records"][0]["previous_current_sha256"] = "0" * 64
            elif mutation == "state":
                result["state"] = "MANUAL_REVIEW_COMPLETE_DRAFT_DESIGNS"
            elif mutation == "duplicate":
                result["records"].append(result["records"][0].copy())
        elif mutation == "owner" and result.get("status") == "MANUAL_REVIEW_COMPLETE_DRAFT_DESIGNS":
            result["owner_acceptance"] = "ACCEPTED"
        return result

    monkeypatch.setattr(review.json, "loads", altered)
    with pytest.raises(AssertionError):
        review.validate()
