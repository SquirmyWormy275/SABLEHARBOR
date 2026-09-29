"""Neutral distinct-change fixtures; no private scenario bank in public tests."""

import copy
from decimal import Decimal

import pytest

from enterprise.audit_suite import change_volume
from enterprise.audit_suite.artifacts import render
from enterprise.audit_suite.store import DomainError, digest


@pytest.fixture
def definition():
    pool = []
    for n in range(1, 101):
        cid, oid = f"C-{n:03}", f"O-{n:03}"
        common = {"change_id": cid, "affected_object_id": oid}
        old, new = oid + "-before", oid + "-after"
        inputs = {"quantity": n, "unit_value": "2.50"}
        expected = str(Decimal(n) * Decimal("2.50"))
        pool.append(
            {
                "change_id": cid,
                "affected_object_id": oid,
                "rows": {
                    "initial": {**common, "announced_version": new},
                    "operating": {
                        **common,
                        "old_implementation": old,
                        "effective_implementation": new,
                    },
                    "retest": {
                        **common,
                        "supporting_source_record": "S-" + cid,
                        "inputs": inputs,
                        "expected_output": expected,
                        "observed_output": expected,
                        "recorded_result": "OBSERVED_MATCH",
                        "performed_business_day_offset": 2,
                    },
                    "test_source": {
                        **common,
                        "source_record": "S-" + cid,
                        "source_inputs": inputs,
                        "recorded_output": expected,
                        "source_available": True,
                        "source_capture_offset": 2,
                    },
                },
                "lifecycle": [
                    {"version": old, "effective_business_day_offset": 0},
                    {"version": new, "effective_business_day_offset": 1},
                ],
                "test_offset": 2,
                "mechanism_context": {"neutral_case": "Retained changed object"},
                "review_hours": "1.5",
            }
        )
    artifacts = {
        role: "A-" + role for role in [*change_volume.ROLES, "reconciliation", "lifecycles"]
    }
    return {
        "id": "NEUTRAL-VOLUME",
        "selector_id": "MM-10",
        "facts": [{"id": "F1"}, {"id": "F2"}],
        "artifacts": [
            {"id": aid, "recipe": {"format": "json", "title": role, "rows": [], "columns": []}}
            for role, aid in artifacts.items()
        ],
        "events": [
            {"id": "E1", "trigger": "REQUEST", "offset_business_days": 0, "effects": []},
            {"id": "E2", "trigger": "FOLLOWUP", "offset_business_days": 1, "effects": []},
        ],
        "rubric": {},
        "playable_paths": [{"rationale": "Neutral path"}],
        "parameter_contract": {
            "count": {
                "adapter": change_volume.ADAPTER,
                "episodes": pool,
                "source_pool_digest": digest(pool),
                "artifact_ids": artifacts,
                "base_event_ids": {"initial": "E1", "followup": "E2"},
                "causal_summary": (
                    "Each changed object has an independently retained model observation."
                ),
            }
        },
    }


@pytest.mark.parametrize("count", [1, 50, 100])
def test_actual_native_records_not_duplicate_packets(definition, count):
    before = copy.deepcopy(definition)
    result = change_volume.apply(definition, count)
    preview = result["applied_parameters"]["count"]
    assert preview["change_events"] == preview["affected_objects"] == count
    assert Decimal(preview["review_hours"]) == Decimal("1.5") * count
    notices = [e for e in result["events"] if "-CHANGE-" in e["id"]]
    assert len(notices) == count
    assert len({e["effects"][0]["target"] for e in notices}) == count
    for role in change_volume.ROLES:
        artifact = next(a for a in result["artifacts"] if a["id"] == "A-" + role)
        assert artifact["recipe"]["rows"] == [
            e["rows"][role] for e in before["parameter_contract"]["count"]["episodes"][:count]
        ]
        data, mime = render(artifact["recipe"])
        assert data and mime == "application/json"
    assert definition == before
    assert result["binding_contract"]["minimum_period_business_days"] == 5


def test_source_prefix_ids_values_dates_and_versions_stable(definition):
    small, large = (change_volume.apply(definition, n) for n in (1, 100))
    for role in change_volume.ROLES:
        a = next(a for a in small["artifacts"] if a["id"] == "A-" + role)
        b = next(a for a in large["artifacts"] if a["id"] == "A-" + role)
        assert a["recipe"]["rows"][0] == b["recipe"]["rows"][0]
    assert (
        small["applied_parameters"]["count"]["source_ids"]
        == large["applied_parameters"]["count"]["source_ids"][:1]
    )


@pytest.mark.parametrize("value", [0, 101, True, 1.0, "1"])
def test_invalid_volume_rejected(definition, value):
    with pytest.raises(DomainError):
        change_volume.apply(definition, value)


@pytest.mark.parametrize(
    "mutation",
    [
        "hash",
        "duplicate_object",
        "cross_reference",
        "reversed_dates",
        "same_version",
        "false_match",
        "missing_source",
        "nonfinite_effort",
        "wrong_test_date",
    ],
)
def test_invalid_authored_pool_fails_closed(definition, mutation):
    contract = definition["parameter_contract"]["count"]
    e = contract["episodes"][0]
    if mutation == "duplicate_object":
        e["affected_object_id"] = contract["episodes"][1]["affected_object_id"]
    elif mutation == "cross_reference":
        e["rows"]["retest"]["supporting_source_record"] = "WRONG"
    elif mutation == "reversed_dates":
        e["lifecycle"][1]["effective_business_day_offset"] = 0
    elif mutation == "same_version":
        e["lifecycle"][1]["version"] = e["lifecycle"][0]["version"]
    elif mutation == "false_match":
        e["rows"]["retest"]["expected_output"] = "WRONG"
    elif mutation == "missing_source":
        e["rows"]["test_source"]["source_available"] = False
    elif mutation == "nonfinite_effort":
        e["review_hours"] = "NaN"
    elif mutation == "wrong_test_date":
        e["rows"]["retest"]["performed_business_day_offset"] = 0
    else:
        e["review_hours"] = "9"
    if mutation != "hash":
        contract["source_pool_digest"] = digest(contract["episodes"])
    with pytest.raises(DomainError):
        change_volume.apply(definition, 1)


def test_missing_retest_kept_not_run_without_discarding_change(definition):
    contract = definition["parameter_contract"]["count"]
    e = contract["episodes"][0]
    e["rows"]["test_source"].update(source_available=False, recorded_output=None)
    e["rows"]["retest"].update(recorded_result="NOT_RUN", observed_output=None)
    contract["source_pool_digest"] = digest(contract["episodes"])
    result = change_volume.apply(definition, 1)
    test = next(a for a in result["artifacts"] if a["id"] == "A-retest")["recipe"]["rows"][0]
    assert test["recorded_result"] == "NOT_RUN" and test["observed_output"] is None
    assert result["applied_parameters"]["count"]["change_events"] == 1
