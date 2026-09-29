import copy

import pytest

from enterprise.operations.debt_host import build, validate
from industrial.planning.enterprise import load_anchor


@pytest.fixture(scope="module")
def corpus():
    anchor = load_anchor()
    return build(anchor), anchor


def test_source_debt_and_host_chains(corpus):
    result, anchor = corpus
    assert validate(result, anchor)["debt_settlements"] == 18
    assert result["principal_bridge"]["term_closing_usd"] == "21750000"
    assert result["principal_bridge"]["lease_closing_usd"] == "2175342"
    assert all(
        r["available_at"] >= result["repository_source_available_at"] for r in result["host_events"]
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "omit",
        "duplicate",
        "amount",
        "classification",
        "period",
        "reviewer",
        "lien",
        "host_amount",
        "host_timing",
        "bridge",
    ],
)
def test_debt_or_host_false_completion_rejected(corpus, mutation):
    source, anchor = corpus
    result = copy.deepcopy(source)
    row = result["debt_settlements"][0]
    if mutation == "omit":
        result["debt_settlements"].pop()
    elif mutation == "duplicate":
        result["debt_settlements"].append(copy.deepcopy(row))
    elif mutation == "amount":
        row["amount_usd"] = "1"
    elif mutation == "classification":
        row["classification"] = "TERM_PRINCIPAL"
    elif mutation == "period":
        row["settled_on"] = "2027-01-31"
    elif mutation == "reviewer":
        row["reviewer_role"] = row["preparer_role"]
    elif mutation == "lien":
        result["debt"]["lien_release_status"] = "RELEASED"
    elif mutation == "host_amount":
        result["host_events"][2]["amount_usd"] = "120000"
    elif mutation == "host_timing":
        result["host_events"][2]["effective_on"] = "2026-08-20"
    else:
        result["principal_bridge"]["term_closing_usd"] = "0"
    with pytest.raises(ValueError):
        validate(result, anchor)
