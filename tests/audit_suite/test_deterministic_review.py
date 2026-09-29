from copy import deepcopy
from dataclasses import asdict

from enterprise.audit_suite.deterministic_review import checks
from enterprise.audit_suite.populations import create_population, monetary_size


def find(state, kind):
    return [r for r in checks(state) if r["check"] == kind]


def test_arithmetic_reperform_and_external_method_not_guessed():
    inputs = {
        "method": "monetary",
        "total_book_value": "100000",
        "tolerable_misstatement": "1000",
        "alpha": "0.05",
    }
    result = monetary_size("100000", "1000", "0.05")
    state = {"calculations": [{"id": "C", "inputs": inputs, "result": result}]}
    assert find(state, "EXPLICIT_CALCULATOR_REPERFORMANCE")[0]["status"] == "SUPPORTED"
    state["calculations"][0]["result"] = {**result, "size": result["size"] + 1}
    assert find(state, "EXPLICIT_CALCULATOR_REPERFORMANCE")[0]["status"] == "CONTRADICTED"
    state["calculations"][0]["inputs"]["method"] = "manual_methodology"
    assert find(state, "EXPLICIT_CALCULATOR_REPERFORMANCE")[0]["status"] == "NOT_OBSERVABLE"
    assert find({}, "EXPLICIT_CALCULATOR_REPERFORMANCE")[0]["status"] == "NOT_OBSERVABLE"


def test_supplied_rows_count_frozen_version_not_hidden_completeness():
    population = create_population(
        "P",
        1,
        [{"id": "A", "amount": "1"}, {"id": "B", "amount": "2"}],
        scope={
            "boundary_id": "B",
            "unit": "record",
            "timezone": "UTC",
            "period_start": "2027-01-01T00:00:00Z",
            "period_end": "2028-01-01T00:00:00Z",
        },
        source={
            "source_id": "original",
            "query": "explicit",
            "original_sha256": "0" * 64,
            "completeness_representation": "Supplied records only",
        },
    )
    state = {
        "populations": [
            {
                "id": "P",
                "version": 1,
                "count": 2,
                "rows": list(population.rows),
                "immutable": asdict(population),
            }
        ]
    }
    assert find(state, "WORKING_ROWS_EQUAL_RETAINED_VERSION")[0]["status"] == "SUPPORTED"
    state["hidden_census"] = [{"id": "PRIVATE"}]
    assert "PRIVATE" not in str(checks(state))
    state["populations"][0]["rows"][0]["amount"] = "99"
    assert find(state, "WORKING_ROWS_EQUAL_RETAINED_VERSION")[0]["status"] == "CONTRADICTED"
    assert find(state, "RECORDED_COUNT_EQUALS_SUPPLIED_ROWS")[0]["status"] == "SUPPORTED"


def test_selected_and_targeted_sets_are_distinct_and_version_pinned():
    state = {
        "populations": [{"id": "P", "version": 1, "count": 2, "rows": [{"id": "A"}, {"id": "B"}]}],
        "selections": [
            {
                "id": "S",
                "population_id": "P",
                "selected_ids": ["A"],
                "targeted_ids": ["B"],
                "immutable": {"population_version": 1},
            }
        ],
    }
    assert find(state, "SELECTION_VERSION_AND_SETS")[0]["status"] == "SUPPORTED"
    state["selections"][0]["targeted_ids"] = ["A"]
    assert find(state, "SELECTION_VERSION_AND_SETS")[0]["status"] == "CONTRADICTED"
    state["selections"][0]["targeted_ids"] = ["B"]
    state["selections"][0]["immutable"]["population_version"] = 2
    assert find(state, "SELECTION_VERSION_AND_SETS")[0]["status"] == "CONTRADICTED"


def test_coverage_offsets_prior_support_and_missing_evidence_not_control_failure():
    state = {
        "simulated_at": "2028-01-02T09:00:00Z",
        "artifacts": [],
        "temporal": {
            "0": {
                "versions": [
                    {
                        "id": "I",
                        "effective": {
                            "start": "2027-01-01T00:00:00-07:00",
                            "end": "2028-01-01T00:00:00-07:00",
                        },
                    }
                ],
                "work": [
                    {
                        "id": "W",
                        "implementation_id": "I",
                        "covered": {
                            "start": "2027-06-01T00:00:00-06:00",
                            "end": "2027-07-01T00:00:00-06:00",
                        },
                        "performed_at": "2028-01-01T09:00:00Z",
                        "evidence_ids": [],
                    }
                ],
            }
        },
    }
    assert find(state, "RECORDED_COVERAGE_INTERVAL_LOGIC")[0]["status"] == "SUPPORTED"
    assert find(state, "COVERAGE_HAS_OBSERVABLE_REFERENCES")[0]["status"] == "NOT_OBSERVABLE"
    bad = deepcopy(state)
    bad["temporal"]["0"]["work"][0]["performed_at"] = "2029-01-01T09:00:00Z"
    assert find(bad, "RECORDED_COVERAGE_INTERVAL_LOGIC")[0]["status"] == "CONTRADICTED"
    bad["temporal"]["0"]["work"][0]["performed_at"] = "2027-01-01"
    assert find(bad, "RECORDED_COVERAGE_INTERVAL_LOGIC")[0]["status"] == "NOT_OBSERVABLE"


def test_fractional_or_nonfinite_population_size_is_not_silently_rounded():
    for invalid in ["10.5", "NaN", True]:
        state = {
            "calculations": [
                {
                    "id": "C",
                    "inputs": {
                        "method": "zero_deviation_attribute",
                        "confidence": "0.95",
                        "tolerable_rate": "0.1",
                        "population_size": invalid,
                    },
                    "result": {"version": "sampling-v1", "size": 10},
                }
            ]
        }
        assert find(state, "EXPLICIT_CALCULATOR_REPERFORMANCE")[0]["status"] == "NOT_OBSERVABLE"
