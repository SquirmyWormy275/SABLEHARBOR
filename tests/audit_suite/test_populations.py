"""Neutral arithmetic and lineage fixtures; no hidden authored scenario solutions."""

from dataclasses import FrozenInstanceError
from fractions import Fraction
from itertools import combinations

import pytest

from enterprise.audit_suite import populations as p


def population(rows=None, status="PROVISIONAL"):
    return p.create_population(
        "P",
        1,
        rows if rows is not None else [{"id": str(i), "amount": str(i + 1)} for i in range(10)],
        scope=dict(
            boundary_id="B",
            unit="record",
            timezone="UTC",
            period_start="2026-01-01T00:00:00Z",
            period_end="2027-01-01T00:00:00Z",
        ),
        source=dict(
            source_id="SOURCE",
            query="Explicit fixture extract",
            original_sha256="a" * 64,
            completeness_representation="Supplier representation, not independent assurance",
            reliability_purpose="purpose",
            reliability_rationale="Fixture review",
            reliability_actor="reviewer",
            observable_source_ref="visible-second-source",
        ),
        status=status,
    )


def select(pop, **kwargs):
    return p.select(
        pop,
        selection_id="S",
        method="SIMPLE_RANDOM",
        purpose="purpose",
        rationale="Neutral fixture",
        seed="seed",
        size=3,
        **kwargs,
    )


def test_immutable_roundtrip_and_selection_versions():
    pop = population()
    with pytest.raises(FrozenInstanceError):
        pop.version = 2
    original = pop.sha256
    rows = pop.rows
    rows[0]["amount"] = "999"
    assert pop.sha256 == original and pop.rows[0]["amount"] == "1"
    chosen = select(pop)
    assert chosen == select(pop)
    revised = p.revise_population(pop, [{"id": "new"}], source=pop.source, rationale="New extract")
    assert revised.version == 2 and revised.predecessor_digest == original
    with pytest.raises(ValueError, match="different population"):
        p.validate_selection(revised, chosen)
    assert chosen.provisional


def test_reliability_is_purpose_specific():
    pop = population(status="READY_FOR_PURPOSE")
    chosen = select(pop)
    assert not chosen.provisional
    other = p.select(
        pop,
        selection_id="other",
        method="ENTIRE",
        purpose="different objective",
        rationale="exploratory",
    )
    assert other.provisional
    with pytest.raises(ValueError):
        p.create_population(
            "bad",
            1,
            [],
            scope=pop.scope,
            source={k: v for k, v in pop.source.items() if k != "observable_source_ref"},
            status="READY_FOR_PURPOSE",
        )


@pytest.mark.parametrize("rows", [[{"id": "x"}, {"id": "x"}], [{"id": None}], [{"id": ""}]])
def test_invalid_identifiers(rows):
    with pytest.raises(ValueError):
        population(rows)


def test_empty_one_oversize_and_seed():
    empty = population([])
    assert (
        p.select(
            empty,
            selection_id="E",
            method="ENTIRE",
            purpose="purpose",
            rationale="empty supplied population",
        ).all_ids
        == ()
    )
    with pytest.raises(ValueError, match="exceeds"):
        select(empty)
    one = population([{"id": "one"}])
    assert p.select(
        one,
        selection_id="S",
        method="SYSTEMATIC",
        purpose="purpose",
        rationale="one",
        size=1,
        seed="x",
    ).selected_ids == ("one",)
    pop = population()
    choices = {
        p.select(
            pop,
            selection_id="S",
            method="SIMPLE_RANDOM",
            purpose="purpose",
            rationale="choice",
            seed=str(n),
            size=3,
        ).selected_ids
        for n in range(20)
    }
    assert len(choices) > 1
    assert all(len(set(c)) == 3 for c in choices)


def test_all_methods_and_targeted_not_representative():
    pop = population()
    manual = p.select(
        pop,
        selection_id="M",
        method="MANUAL",
        purpose="purpose",
        rationale="targeted",
        ids=["1", "2"],
        targeted_ids=["9"],
    )
    assert manual.selected_ids == ("1", "2") and manual.targeted_ids == ("9",)
    assert manual.parameters["representative_claim"] is False
    for method in ["SIMPLE_RANDOM", "SYSTEMATIC"]:
        result = p.select(
            pop,
            selection_id="S",
            method=method,
            purpose="purpose",
            rationale="r",
            size=8,
            seed="x",
            targeted_ids=["9"],
        )
        assert "9" not in result.selected_ids and len(result.selected_ids) == 8
    strata = {
        "first": {"ids": ["0", "1", "2", "3", "4"], "size": 2},
        "second": {"ids": ["5", "6", "7", "8", "9"], "size": 3},
    }
    result = p.select(
        pop,
        selection_id="S",
        method="STRATIFIED",
        purpose="purpose",
        rationale="r",
        strata=strata,
        seed="x",
    )
    assert len(set(result.selected_ids) & set(strata["first"]["ids"])) == 2
    assert len(result.selected_ids) == 5
    strata["second"]["ids"].append("0")
    with pytest.raises(ValueError, match="overlapping"):
        p.select(
            pop,
            selection_id="S",
            method="STRATIFIED",
            purpose="purpose",
            rationale="r",
            strata=strata,
            seed="x",
        )


def test_nested_foreign_keys_reimports_and_missing_support():
    parent = population([{"id": "A"}, {"id": "B"}, {"id": "C"}])
    selection = p.select(
        parent,
        selection_id="S",
        method="MANUAL",
        purpose="purpose",
        rationale="sites",
        ids=["A", "C"],
    )
    child = p.create_population(
        "tickets",
        1,
        [{"id": "t1", "site": "A"}, {"id": "t2", "site": "C"}],
        scope=parent.scope,
        source=parent.source,
        parent_population=parent,
        parent_selection=selection,
        parent_key="site",
    )
    with pytest.raises(ValueError, match="outside parent"):
        p.create_population(
            "bad",
            1,
            [{"id": "t", "site": "B"}],
            scope=parent.scope,
            source=parent.source,
            parent_population=parent,
            parent_selection=selection,
            parent_key="site",
        )
    tickets = p.select(
        child,
        selection_id="tickets",
        method="MANUAL",
        purpose="purpose",
        rationale="imported IDs",
        ids=["t1"],
    )
    assert tickets.parent_selection_digest == selection.sha256
    missing = p.response_manifest(
        child, tickets, {"t1": {"status": "UNAVAILABLE", "rationale": "Missing source"}}
    )
    assert missing["test_conclusion"] == "NOT_ASSERTED"
    with pytest.raises(ValueError, match="absent|missing"):
        p.select(
            child,
            selection_id="bad",
            method="MANUAL",
            purpose="purpose",
            rationale="bad import",
            ids=["no-such-ticket"],
        )


def test_replacement_preserves_history_and_requires_authority():
    pop = population()
    old = select(pop)
    replacement = next(i for i in pop.ids if i not in old.all_ids)
    with pytest.raises(ValueError, match="authorization"):
        p.revise_selection(
            pop,
            old,
            selection_id="new",
            remove_ids=[old.selected_ids[0]],
            add_ids=[replacement],
            rationale="inconvenient evidence",
        )
    revised = p.revise_selection(
        pop,
        old,
        selection_id="new",
        remove_ids=[old.selected_ids[0]],
        add_ids=[replacement],
        rationale="Explicit neutral methodology fixture",
        methodology_authorizes_replacement=True,
    )
    assert (
        revised.predecessor_digest == old.sha256 and old.selected_ids[0] not in revised.selected_ids
    )
    expanded = p.revise_selection(
        pop, old, selection_id="more", add_ids=[replacement], rationale="additional procedure"
    )
    assert len(expanded.selected_ids) == len(old.selected_ids) + 1


def test_binomial_boundaries_and_no_truncation():
    result = p.attribute_size(".05", ".05")
    assert result["size"] == 59
    assert Fraction(95, 100) ** 59 <= Fraction(5, 100) < Fraction(95, 100) ** 58
    assert p.attribute_size(".5", ".5")["size"] == 1
    for alpha, tolerance in [(0, 0.1), (1, 0.1), (0.1, 0), (0.1, 1), ("NaN", ".1")]:
        with pytest.raises(ValueError):
            p.attribute_size(alpha, tolerance)
    with pytest.raises(ValueError, match="bounded"):
        p.attribute_size(".05", "0.000000000001")


def test_finite_sample_matches_independent_enumeration():
    for n in range(1, 12):
        result = p.attribute_size(".1", ".2", n)
        d = (n + 4) // 5
        size = result["size"]
        all_samples = list(combinations(range(n), size))
        missed = sum(not set(s) & set(range(d)) for s in all_samples)
        assert Fraction(missed, len(all_samples)) <= Fraction(1, 10)
        if size:
            previous = list(combinations(range(n), size - 1))
            missed = sum(not set(s) & set(range(d)) for s in previous)
            assert Fraction(missed, len(previous)) > Fraction(1, 10)
    assert p.attribute_size(".05", ".05", 10)["size"] == 10


def test_monetary_distinct_draws_zero_negative_and_planning_limits():
    pop = population([{"id": "large", "amount": "90"}, {"id": "small", "amount": "10"}])
    selected = p.select(
        pop,
        selection_id="S",
        method="MONETARY_SYSTEMATIC",
        purpose="purpose",
        rationale="PPS fixture",
        seed="fixed",
        size=10,
        amount_field="amount",
    )
    assert len(selected.parameters["draw_ids"]) == 10
    assert selected.parameters["draw_ids"].count("large") == 9
    assert set(selected.selected_ids) == {"large", "small"}
    assert p.monetary_size("100000", "5000", ".05")["size"] == 60
    with pytest.raises(ValueError, match="external methodology"):
        p.monetary_size("100000", "5000", ".05", "1")
    for amount in ["0", "-1"]:
        with pytest.raises(ValueError, match="positive eligible"):
            p.select(
                population([{"id": "a", "amount": amount}]),
                selection_id="S",
                method="MONETARY_SYSTEMATIC",
                purpose="purpose",
                rationale="invalid",
                seed="s",
                size=1,
                amount_field="amount",
            )


def test_sampling_can_miss_fixed_item_without_rewriting_source():
    pop = population()
    original = pop.sha256
    sample = p.select(
        pop,
        selection_id="S",
        method="SIMPLE_RANDOM",
        purpose="purpose",
        rationale="neutral selection",
        seed="fixed",
        size=1,
    )
    assert len(set(pop.ids) - set(sample.all_ids)) == 9 and pop.sha256 == original


def test_exclusions_retained_without_silent_selection():
    original = population()
    source = dict(
        original.source,
        excluded_ids=["9"],
        exclusion_rationale="Separate explicit population scope disposition",
    )
    revised = p.create_population("P", 2, original.rows, scope=original.scope, source=source)
    entire = p.select(
        revised,
        selection_id="E",
        method="ENTIRE",
        purpose="purpose",
        rationale="entire eligible supplied population",
    )
    assert len(revised.ids) == 10 and len(entire.selected_ids) == 9
    assert "9" not in entire.selected_ids
    with pytest.raises(ValueError, match="missing|already targeted"):
        p.select(
            revised,
            selection_id="M",
            method="MANUAL",
            purpose="purpose",
            rationale="excluded",
            ids=["9"],
        )


def test_empty_and_overlapping_strata_and_invalid_parent_scope():
    pop = population()
    with pytest.raises(ValueError, match="partition"):
        p.select(
            pop,
            selection_id="S",
            method="STRATIFIED",
            purpose="purpose",
            rationale="incomplete partition",
            strata={"only": {"ids": ["1"], "size": 1}},
            seed="s",
        )
    parent = p.select(
        pop, selection_id="parent", method="MANUAL", purpose="purpose", rationale="site", ids=["1"]
    )
    with pytest.raises(ValueError, match="scope exceeds"):
        p.create_population(
            "child",
            1,
            [{"id": "c", "parent": "1"}],
            scope=dict(pop.scope, boundary_id="elsewhere"),
            source=pop.source,
            parent_population=pop,
            parent_selection=parent,
            parent_key="parent",
        )
    with pytest.raises(ValueError, match="requires|together"):
        p.create_population(
            "child", 1, [], scope=pop.scope, source=pop.source, parent_population=pop
        )
