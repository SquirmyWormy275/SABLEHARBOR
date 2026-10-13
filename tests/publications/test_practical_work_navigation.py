"""Navigation refreshes preserve historical legal review and reject altered pins."""

import pytest

from tools.legal_gaps import validate_practical_work as review


def test_current_navigation_preserves_review():
    review.validate()


@pytest.mark.parametrize("mutation", ["parent", "historical", "current", "owner"])
def test_altered_navigation_or_owner_state_is_rejected(monkeypatch, mutation):
    original = review.json.loads

    def altered(content, *args, **kwargs):
        result = original(content, *args, **kwargs)
        if result.get("record_id") == "SH-LEGAL-V3-NAVIGATION-SUCCESSOR-2026-10-13":
            if mutation == "parent":
                result["previous_successor_sha256"] = "0" * 64
            elif mutation == "historical":
                result["records"][0]["historical_sha256"] = "0" * 64
            elif mutation == "current":
                result["records"][0]["current_sha256"] = "0" * 64
        elif mutation == "owner" and result.get("status") == "MANUAL_REVIEW_COMPLETE_DRAFT_DESIGNS":
            result["owner_acceptance"] = "ACCEPTED"
        return result

    monkeypatch.setattr(review.json, "loads", altered)
    with pytest.raises(AssertionError):
        review.validate()
