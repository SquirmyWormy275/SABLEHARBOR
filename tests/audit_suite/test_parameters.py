import pytest

from enterprise.audit_suite.composition import advance_events
from enterprise.audit_suite.parameters import apply
from enterprise.audit_suite.store import DomainError


def definition():
    return {
        "id": "CASE",
        "events": [
            {
                "id": "USEFUL",
                "trigger": "FOLLOWUP",
                "offset_business_days": 0,
                "effects": [{"operation": "statement", "value": "Bounded useful response"}],
            }
        ],
        "parameter_contract": {
            "intensity": {
                "anchors": [
                    {
                        "at": level,
                        "mechanics": "Explicit clarification rounds before this response",
                        "event_overrides": {"USEFUL": {"minimum_followups": rounds}},
                    }
                    for level, rounds in [(0, 0), (25, 1), (50, 2), (75, 3), (100, 4)]
                ]
            }
        },
    }


def test_independent_intensity_changes_actual_finite_followup_gate():
    low = apply(definition(), {"intensity": 25})
    high = apply(definition(), {"intensity": 100})
    args = {"now": "2028-01-03T09:00:00+00:00", "timezone": "UTC"}
    progress, effects = advance_events(high, None, trigger="REQUEST", **args)
    assert not effects
    for _ in range(3):
        progress, effects = advance_events(high, progress, trigger="FOLLOWUP", **args)
        assert not effects
    progress, effects = advance_events(high, progress, trigger="FOLLOWUP", **args)
    assert len(effects) == 1
    progress, effects = advance_events(high, progress, trigger="FOLLOWUP", **args)
    assert not effects
    first, _ = advance_events(low, None, trigger="REQUEST", **args)
    assert advance_events(low, first, trigger="FOLLOWUP", **args)[1]
    assert definition()["events"][0].get("minimum_followups") is None


def test_missing_mechanics_and_unbounded_gates_are_rejected():
    with pytest.raises(DomainError, match="authored severity"):
        apply(definition(), {"severity": 50})
    malformed = definition()
    malformed["parameter_contract"]["intensity"]["anchors"][-1]["event_overrides"]["USEFUL"][
        "minimum_followups"
    ] = 1000
    with pytest.raises(DomainError, match="finite bound"):
        apply(malformed, {"intensity": 100})
