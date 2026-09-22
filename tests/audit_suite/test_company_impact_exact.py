"""Typed relationships preserve exact versions without interpreting conclusions."""

from copy import deepcopy

import pytest

from enterprise.audit_suite.company_impact import references
from enterprise.audit_suite.review_anchor import normalize_anchor
from enterprise.audit_suite.store import DomainError, digest


def fixture():
    state = {
        "scope": {"boundary": "corporate"},
        "artifacts": [{"id": "ART", "sha256": "a" * 64}],
        "workpapers": [
            {
                "id": "WP",
                "versions": [
                    {"version": 1, "text": "Original observation.", "evidence_ids": ["ART"]},
                    {"version": 2, "text": "Later observation.", "evidence_ids": []},
                ],
            }
        ],
    }
    first = {
        "id": "TRACE1",
        "revision": 1,
        "predecessor_id": None,
        "scope_digest": digest(state["scope"]),
        "task_id": "TASK",
        "selection_id": "SEL",
        "population_id": "POP",
        "items": [
            {
                "item_id": "ITEM1",
                "evidence": [{"artifact_id": "ART", "sha256": "a" * 64, "locator": "row 7"}],
            }
        ],
    }
    second = {
        **deepcopy(first),
        "id": "TRACE2",
        "revision": 2,
        "predecessor_id": first["id"],
        "predecessor_digest": digest(first),
    }
    state["sample_executions"] = [first, second]
    version = state["workpapers"][0]["versions"][0]
    state["reviews"] = [
        {
            "id": "REVIEW",
            "kind": "HUMAN",
            "workpaper_id": "WP",
            "workpaper_version": 1,
            "workpaper_version_digest": digest(version),
            "anchor": normalize_anchor(
                {"field": "text", "start": 0, "end": 8, "excerpt": "Original"}, version
            ),
        }
    ]
    state["findings"] = [
        {
            "id": "FIND",
            "evidence_ids": ["ART"],
            "remediations": [{"id": "REM", "evidence_ids": ["ART"]}],
        }
    ]
    return state


def test_exact_items_correction_history_review_passage_and_real_finding_fields():
    state = fixture()
    before = deepcopy(state)
    result = references(state, "ART")
    assert result[0] == {
        "collection": "workpapers",
        "id": "WP",
        "version": 1,
        "relation": "DIRECT_EVIDENCE_ID",
    }
    traces = [r for r in result if r["collection"] == "sample_executions"]
    assert [r["trace_status"] for r in traces] == ["HISTORICAL_CORRECTED", "CURRENT_LEAF"]
    assert traces[0]["successor_id"] == "TRACE2" and traces[1]["predecessor_id"] == "TRACE1"
    assert all(r["item_id"] == "ITEM1" and r["artifact_sha256"] == "a" * 64 for r in traces)
    assert all(
        r["locator_validation"] == "AUTHOR_SUPPLIED_NOT_CONTENT_MATCH_VERIFIED" for r in traces
    )
    review = next(r for r in result if r["collection"] == "reviews")
    assert review["version_status"] == "HISTORICAL" and review["review_scope"] == "EXACT_PASSAGE"
    assert review["anchor"]["excerpt"] == "Original"
    findings = [r for r in result if r["collection"] == "findings"]
    assert len(findings) == 2 and findings[1]["remediation_id"] == "REM"
    assert state == before


def test_wrong_sha_and_title_control_association_never_become_links():
    state = fixture()
    state["artifacts"][0]["sha256"] = "b" * 64
    state["findings"] = [
        {
            "id": "UNRELATED",
            "title": "ART",
            "control_id": "TASK",
            "artifact_id": "ART",
            "workpaper_id": "WP",
        }
    ]
    result = references(state, "ART")
    assert not any(r["collection"] in ("sample_executions", "findings") for r in result)


@pytest.mark.parametrize("alteration", ["digest", "passage", "offset_unit", "bool_version", "ai"])
def test_unverified_review_does_not_attach_to_retained_workpaper(alteration):
    state = fixture()
    review = state["reviews"][0]
    if alteration == "digest":
        review["workpaper_version_digest"] = "b" * 64
    elif alteration == "passage":
        review["anchor"]["excerpt"] = "Changed!"
    elif alteration == "offset_unit":
        review["anchor"]["offset_unit"] = "UTF16"
    elif alteration == "bool_version":
        review["workpaper_version"] = True
    else:
        review["kind"] = "AI"
    assert not any(r["collection"] == "reviews" for r in references(state, "ART"))


def test_unanchored_legacy_review_and_changed_scope_are_honestly_labeled():
    state = fixture()
    del state["reviews"][0]["anchor"]
    state["scope"] = {"boundary": "different"}
    refs = references(state, "ART")
    assert (
        next(r for r in refs if r["collection"] == "reviews")["review_scope"]
        == "WHOLE_WORKPAPER_VERSION"
    )
    assert all(
        r["context_status"] == "HISTORICAL_SCOPE_OR_SOURCE_CONTEXT"
        for r in refs
        if r["collection"] == "sample_executions"
    )


@pytest.mark.parametrize(
    "alteration", ["predecessor_digest", "task", "item", "fork", "duplicate_id"]
)
def test_unverifiable_correction_never_produces_partial_graph(alteration):
    state = fixture()
    child = state["sample_executions"][1]
    if alteration == "predecessor_digest":
        child["predecessor_digest"] = "0" * 64
    elif alteration == "task":
        child["task_id"] = "OTHER"
    elif alteration == "item":
        child["items"][0]["item_id"] = "OTHER"
    elif alteration == "fork":
        state["sample_executions"].append({**deepcopy(child), "id": "FORK"})
    else:
        state["sample_executions"].append(deepcopy(child))
    with pytest.raises(DomainError):
        references(state, "ART")


@pytest.mark.parametrize("alteration", ["collection", "nested", "malformed"])
def test_traversal_limits_fail_explicitly_without_partial_reference_output(alteration):
    state = fixture()
    if alteration == "collection":
        state["tasks"] = [{"id": str(i)} for i in range(20001)]
    elif alteration == "nested":
        state["workpapers"][0]["versions"][0]["evidence_ids"] = ["ART"] * 20001
    else:
        state["sample_executions"][0]["items"] = ["not an item"]
    with pytest.raises(DomainError):
        references(state, "ART")
