import pytest

from enterprise.audit_suite.review_anchor import normalize_anchor
from enterprise.audit_suite.store import DomainError


def test_emoji_combining_marks_and_repeated_passage_keep_exact_codepoints():
    version = {"version": 1, "text": "A😀 cafe\u0301 repeat repeat"}
    anchor = {"field": "text", "start": 2, "end": 8, "excerpt": " cafe\u0301"}
    result = normalize_anchor(anchor, version)
    assert result == {**anchor, "offset_unit": "UNICODE_CODEPOINT"}
    assert "offset_unit" not in anchor
    assert (
        normalize_anchor({"field": "text", "start": 16, "end": 22, "excerpt": "repeat"}, version)[
            "start"
        ]
        == 16
    )


@pytest.mark.parametrize("value", [True, 1.0, -1, "1"])
def test_invalid_offset_types_and_ranges(value):
    with pytest.raises(DomainError):
        normalize_anchor(
            {"field": "text", "start": value, "end": 3, "excerpt": "bc"}, {"text": "abc"}
        )


@pytest.mark.parametrize(
    "anchor",
    [
        None,
        {"field": "text", "start": 0, "end": 1, "excerpt": "a", "offset_unit": "UTF16"},
        {"field": "evidence_ids", "start": 0, "end": 1, "excerpt": "a"},
        {"field": "text", "start": 0, "end": 0, "excerpt": ""},
        {"field": "text", "start": 0, "end": 2, "excerpt": "wrong"},
        {"field": "text", "start": 0, "end": 4, "excerpt": "abcd"},
    ],
)
def test_invalid_shape_field_and_excerpt_rejected(anchor):
    with pytest.raises(DomainError):
        normalize_anchor(anchor, {"text": "abc", "evidence_ids": ["a"]})


@pytest.mark.parametrize("target,excerpt", [("\ud800", "\ud800"), ("a\udfff", "a")])
def test_unpaired_surrogates_rejected_even_outside_excerpt(target, excerpt):
    with pytest.raises(DomainError):
        normalize_anchor(
            {"field": "text", "start": 0, "end": 1, "excerpt": excerpt}, {"text": target}
        )


def test_no_normalization_or_nearest_match_or_new_version_substitution():
    anchor = {"field": "text", "start": 0, "end": 4, "excerpt": "café"}
    assert normalize_anchor(anchor, {"version": 1, "text": "café"})["excerpt"] == "café"
    for text in ("cafe\u0301", "new café", "CAFÉ"):
        with pytest.raises(DomainError):
            normalize_anchor(anchor, {"version": 2, "text": text})
    with pytest.raises(DomainError):
        normalize_anchor(
            {"field": "text", "start": 0, "end": 4001, "excerpt": "a" * 4001}, {"text": "a" * 4001}
        )
