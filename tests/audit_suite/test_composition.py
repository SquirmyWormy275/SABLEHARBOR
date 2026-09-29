from copy import deepcopy

import pytest

from enterprise.audit_suite.composition import advance_events, business_due, observable_effects
from enterprise.audit_suite.store import DomainError


def case():
    return {
        "id": "neutral-test-case",
        "events": [
            {
                "id": "initial",
                "trigger": "REQUEST",
                "offset_business_days": 0,
                "effects": [
                    {"operation": "release_artifact", "target": "private-a", "value": "private-a"}
                ],
            },
            {
                "id": "supplement",
                "trigger": "FOLLOWUP",
                "offset_business_days": 1,
                "effects": [
                    {"operation": "statement", "target": "owner", "value": "Supplement ready."}
                ],
            },
        ],
    }


def advance(definition, progress=None, trigger="REQUEST", now="2027-03-12T10:00:00-08:00"):
    return advance_events(
        definition, progress, trigger=trigger, now=now, timezone="America/Los_Angeles"
    )


def test_followup_is_not_released_by_clock_and_retry_does_not_repeat():
    definition = case()
    progress, effects = advance(definition)
    assert len(effects) == 1
    assert observable_effects(effects) == []
    progress, effects = advance(definition, progress)
    assert effects == []
    progress, effects = advance(definition, progress, "CLOCK", "2027-03-22T10:00:00-07:00")
    assert effects == []
    progress, effects = advance(definition, progress, "FOLLOWUP", "2027-03-22T10:00:00-07:00")
    assert effects == []
    progress, effects = advance(definition, progress, "CLOCK", "2027-03-23T10:00:00-07:00")
    assert observable_effects(effects)[0]["text"] == "Supplement ready."
    assert advance(definition, progress, "CLOCK", "2027-03-24T10:00:00-07:00")[1] == []


def test_business_delay_preserves_local_time_across_dst_and_holiday():
    assert (
        business_due("2027-03-12T10:00:00-08:00", 1, "America/Los_Angeles", [])
        == "2027-03-15T10:00:00-07:00"
    )
    assert (
        business_due("2027-03-12T10:00:00-08:00", 1, "America/Los_Angeles", ["2027-03-15"])
        == "2027-03-16T10:00:00-07:00"
    )


def test_definition_changes_backdating_and_unissued_followup_rejected():
    definition = case()
    progress, _ = advance(definition)
    changed = deepcopy(definition)
    changed["events"][0]["offset_business_days"] = 1
    with pytest.raises(DomainError, match="cannot be replaced"):
        advance(changed, progress)
    with pytest.raises(DomainError, match="backwards"):
        advance(definition, progress, now="2027-03-11T10:00:00-08:00")
    with pytest.raises(DomainError, match="issued request"):
        advance(definition, trigger="FOLLOWUP")


def test_source_notice_waits_for_actual_source_instant_across_date_only_zone():
    from enterprise.audit_suite.composition import advance_events

    definition = {
        "id": "SOURCE-NOTICE",
        "events": [
            {
                "id": "DATED",
                "trigger": "REQUEST",
                "offset_business_days": 0,
                "not_before": "2028-06-01",
                "effects": [
                    {
                        "operation": "statement",
                        "target": "Custodian",
                        "value": "The scheduled observation packet is available.",
                    }
                ],
            }
        ],
    }
    progress, effects = advance_events(
        definition,
        None,
        trigger="REQUEST",
        now="2028-05-31T20:00:00+00:00",
        timezone="America/Denver",
    )
    assert not effects
    progress, effects = advance_events(
        definition,
        progress,
        trigger="CLOCK",
        now="2028-06-01T05:59:00+00:00",
        timezone="America/Denver",
    )
    assert not effects
    progress, effects = advance_events(
        definition,
        progress,
        trigger="CLOCK",
        now="2028-06-01T06:00:00+00:00",
        timezone="America/Denver",
    )
    assert len(effects) == 1
    _, effects = advance_events(
        definition,
        progress,
        trigger="CLOCK",
        now="2028-06-02T06:00:00+00:00",
        timezone="America/Denver",
    )
    assert not effects
