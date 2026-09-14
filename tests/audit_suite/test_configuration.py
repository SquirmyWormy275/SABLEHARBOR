import pytest

from enterprise.audit_suite.configuration import (
    allocate_incomplete,
    normalize_shares,
    rounded_count,
    selector_catalog,
    validate_configuration,
)
from enterprise.audit_suite.store import DomainError


def test_catalog_and_no_owner_disagreement_submenu():
    selectors = selector_catalog()
    assert len(selectors) == 18
    assert sum(len(s["options"]) for s in selectors) == 110
    assert next(s for s in selectors if s["id"] == "MM-08")["options"] == []


def test_incomplete_deduplicates_frameworks_and_largest_remainder():
    units = [
        {"control_id": f"C-{i}", "boundary_id": "A", "implementation_version": "1"}
        for i in range(5)
    ]
    result = allocate_incomplete(
        units + units, 50, {"MM-02.01": 50, "MM-02.02": 50}, private_seed=b"fixture"
    )
    assert result["eligible_count"] == 5
    assert result["affected_count"] == 3
    assert result["allocation"] == {"MM-02.01": 2, "MM-02.02": 1}
    assert len({a["control_id"] for a in result["assignments"]}) == 3
    assert result == allocate_incomplete(
        list(reversed(units)), 50, {"MM-02.02": 50, "MM-02.01": 50}, private_seed=b"fixture"
    )


def test_shares_never_silently_normalized():
    with pytest.raises(DomainError, match="total 100"):
        allocate_incomplete([], 50, {"MM-02.01": 20}, private_seed=b"fixture")
    assert normalize_shares({"b": 1, "a": 1, "c": 1}) == {"b": 33, "a": 34, "c": 33}


def test_disagreement_positive_minimum_and_zero():
    assert rounded_count(1, 2, positive_minimum=True) == 1
    assert rounded_count(0, 100, positive_minimum=True) == 0
    assert rounded_count(100, 0, positive_minimum=True) == 0
    assert rounded_count(50, 5) == 3


def test_client_intensities_independent_and_clean_not_messy():
    config = {
        "selections": [
            {"selector_id": "MM-03", "option_id": f"MM-03.0{i}", "parameters": {"intensity": 100}}
            for i in range(1, 7)
        ]
    }
    assert validate_configuration(config, "MESSY")["valid"]
    with pytest.raises(DomainError, match="Clean"):
        validate_configuration(config, "CLEAN")
    config["selections"][0]["parameters"]["overall"] = 50
    with pytest.raises(DomainError, match="no overall"):
        validate_configuration(config, "MESSY")
