"""Literal quotation checks, independent of whether a paraphrase is justified."""

import pytest

from enterprise.audit_suite.inference import validate_result
from enterprise.audit_suite.store import DomainError


def result(text, refs=None):
    return {"text": text, "source_refs": refs if refs is not None else ["S1"]}


def context(text):
    return {
        "source_ids": ["S1", "S2"],
        "sources": [{"id": "S1", "text": text}, {"id": "S2", "text": "Different record"}],
    }


@pytest.mark.parametrize("quote", ['"Observed record"', "“Observed record”"])
def test_exact_decoded_excerpt(quote):
    assert (
        validate_result("experimental_reviewer", result(quote), context("Observed record"))[
            "whole_audit_grade"
        ]
        is None
    )


@pytest.mark.parametrize("placement", ["text", "claim", "observation"])
def test_invented_quote_with_valid_identifier_rejected(placement):
    value = result('"Fabricated record"')
    if placement != "text":
        value = result("Review limitations")
        if placement == "claim":
            value["claims"] = [
                {"text": '"Fabricated record"', "kind": "SOURCE_SUPPORTED", "source_refs": ["S1"]}
            ]
        else:
            value["observations"] = [
                {
                    "text": '"Fabricated record"',
                    "limitation": "Bounded input",
                    "source_refs": ["S1"],
                }
            ]
    with pytest.raises(DomainError, match="Quoted review excerpt"):
        validate_result("experimental_reviewer", value, context("Observed record"))


def test_source_membership_alone_and_uncited_quote_fail():
    for refs in (["S2"], []):
        with pytest.raises(DomainError):
            validate_result(
                "experimental_reviewer",
                result('"Observed record"', refs),
                context("Observed record"),
            )


def test_numeric_and_nested_values_are_decoded_not_repr():
    validate_result("experimental_reviewer", result('"125.5"'), context({"amount": 125.5}))
    with pytest.raises(DomainError):
        validate_result("experimental_reviewer", result('"amount"'), context({"amount": 125.5}))


def test_whitespace_normalization_requires_source_declaration():
    ctx = context("Observed\nrecord")
    with pytest.raises(DomainError):
        validate_result("experimental_reviewer", result('"Observed record"'), ctx)
    ctx["sources"][0]["whitespace_normalization"] = "COLLAPSE_WHITESPACE"
    validate_result("experimental_reviewer", result('"Observed record"'), ctx)


def test_unquoted_paraphrase_is_not_called_verified():
    output = validate_result(
        "experimental_reviewer", result("Possibly insufficient support"), context("Observed record")
    )
    assert output["authority"] == "PROPOSAL_ONLY"
