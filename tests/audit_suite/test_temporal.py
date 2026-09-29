"""Neutral timing contracts for twelve required coverage situations and clock edges."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime

import pytest

from enterprise.audit_suite import temporal as t

START = "2026-01-01T00:00:00Z"
MID = "2026-07-01T00:00:00Z"
END = "2027-01-01T00:00:00Z"
LATER = "2027-01-10T00:00:00Z"


def version(id="v1", start=START, end=END, owner="owner"):
    return t.ImplementationVersion(id, "C", "B", t.Interval(start, end), owner)


def work(id="work", implementation="v1", start=START, end=MID, result="RECORDED", kind="TOE"):
    return t.Coverage(
        id,
        implementation,
        t.Interval(start, end),
        LATER,
        LATER,
        kind,
        result,
        ("evidence",),
        "Neutral recorded procedure coverage",
    )


def report(versions, items, **scope):
    return t.coverage_report(
        dict(
            control_id="C",
            boundary_id="B",
            reporting_basis="PERIOD",
            period_start=START,
            period_end=END,
            **scope,
        ),
        versions,
        items,
    )


def test_stable_recurring_interim_and_remaining_period():
    first = report([version()], [work()])
    assert first["versions"][0]["gaps"] == [
        {"start": t.instant(MID).isoformat(), "end": t.instant(END).isoformat()}
    ]
    complete = report(
        [version()], [work(), work("remaining", start=MID, end=END, kind="ROLL_FORWARD")]
    )
    assert complete["reported_work_complete"]
    assert complete["professional_sufficiency"] == "NOT_ASSERTED"


def test_late_redesign_splits_implementation_versions():
    versions = [version(end=MID), version("v2", start=MID)]
    result = report(versions, [work()])
    assert not result["versions"][0]["gaps"] and result["versions"][1]["gaps"]
    with pytest.raises(ValueError, match="exceeds"):
        report(versions, [work(end=END)])


def test_owner_turnover_does_not_erase_earlier_work():
    versions = [version(end=MID, owner="earlier"), version("v2", start=MID, owner="later")]
    result = report(versions, [work()])
    assert result["versions"][0]["work_ids"] == ["work"]
    assert result["versions"][1]["owner_id"] == "later"


def test_late_period_exception_preserved():
    result = report([version()], [work(), work("later", start=MID, end=END, result="EXCEPTION")])
    assert result["reported_work_complete"] and result["historical_exception_ids"] == ["later"]


def test_final_population_not_available_before_simulated_capture():
    result = t.coverage_report(
        dict(
            control_id="C",
            boundary_id="B",
            reporting_basis="PERIOD",
            period_start=START,
            period_end=END,
        ),
        [version()],
        [work(end=END)],
        as_of=END,
    )
    assert not result["reported_work_complete"] and not result["versions"][0]["work_ids"]


def test_year_end_activity_has_no_invented_interim_occurrence():
    result = report([version()], [work(start="2026-12-31T00:00:00Z", end=END)])
    assert result["versions"][0]["gaps"][0]["end"] == t.instant("2026-12-31T00:00:00Z").isoformat()


def test_type_one_point_in_time_does_not_require_toe():
    point = "2026-12-31T00:00:00Z"
    rows = [
        work("design", start=point, end=point, kind="TOD"),
        work("implemented", start=point, end=point, kind="IMPLEMENTATION"),
    ]
    result = t.coverage_report(
        dict(control_id="C", boundary_id="B", reporting_basis="POINT_IN_TIME", as_of=point),
        [version()],
        rows,
    )
    assert result["reported_work_complete"] and not result["full_period_toe_required"]
    assert result["missing_kinds"] == []


def test_type_two_design_does_not_cover_period_operation():
    result = report([version()], [work(end=END, kind="TOD")])
    assert not result["reported_work_complete"]


def test_financial_interim_and_final_procedures():
    result = report(
        [version()],
        [work(kind="SUBSTANTIVE"), work("final", start=MID, end=END, kind="SUBSTANTIVE")],
        procedure_kind="SUBSTANTIVE",
    )
    assert result["reported_work_complete"]


def test_gap_incident_limits_affected_version_only():
    result = report(
        [version(end=MID), version("v2", start=MID)],
        [
            work(),
            work(
                "incident", implementation="v2", start=MID, end=END, result="INSUFFICIENT_EVIDENCE"
            ),
        ],
    )
    assert not result["versions"][0]["gaps"]
    assert result["versions"][1]["limitation_ids"] == ["incident"] and result["versions"][1]["gaps"]


def test_early_vendor_report_and_no_change_claim_leave_gap():
    result = report(
        [version()],
        [work(), work("bridge", start=MID, end=END, kind="INQUIRY", result="NO_CHANGE_REPORTED")],
    )
    assert not result["reported_work_complete"]
    assert result["versions"][0]["limitation_ids"] == ["bridge"]


def test_prospective_remediation_never_erases_original_exception():
    result = report(
        [version(end=MID), version("v2", start=MID)],
        [work(result="EXCEPTION"), work("retest", implementation="v2", start=MID, end=END)],
    )
    assert result["historical_exception_ids"] == ["work"] and result["reported_work_complete"]


def test_interval_union_overlap_and_bad_inputs():
    assert t.gaps(t.Interval(START, END), [t.Interval(START, MID), t.Interval(MID, END)]) == ()
    with pytest.raises(ValueError, match="overlap"):
        report([version(), version("v2")], [])
    with pytest.raises(ValueError, match="future coverage"):
        t.Coverage(
            "future",
            "v1",
            t.Interval(START, END),
            MID,
            MID,
            "TOE",
            "RECORDED",
            ("e",),
            "invalid future work",
        )
    with pytest.raises(ValueError):
        t.Interval("2026-01-01", "2026-02-01")
    with pytest.raises(ValueError, match="point-in-time"):
        t.gaps(t.Interval(START, START), [])


def test_time_jump_dependencies_stable_order_idempotency_and_host_clock():
    now = datetime.now(UTC)
    clock = t.SimulationClock(START)
    events = [
        t.ScheduledEvent("late", END, ("early",)),
        t.ScheduledEvent("early", MID),
        t.ScheduledEvent("same", MID),
    ]
    changed, emitted = t.advance(
        clock, events, action="TARGET_DATE", target=LATER, request_id="command"
    )
    assert [e["event_id"] for e in emitted] == ["early", "same", "late"]
    assert [e["simulated_at"] for e in emitted] == [
        t.instant(MID).isoformat(),
        t.instant(MID).isoformat(),
        t.instant(END).isoformat(),
    ]
    again, repeated = t.advance(
        changed, events, action="TARGET_DATE", target=LATER, request_id="command"
    )
    assert again == changed and repeated == ()
    with pytest.raises(ValueError, match="different command"):
        t.advance(changed, events, action="TARGET_DATE", target=END, request_id="command")
    assert datetime.now(UTC) >= now and clock.simulated_at == START
    with pytest.raises(FrozenInstanceError):
        clock.simulated_at = END


def test_next_event_cycles_changed_plan_and_past_target():
    clock = t.SimulationClock(START)
    events = [t.ScheduledEvent("a", MID), t.ScheduledEvent("b", START, ("a",))]
    changed, emitted = t.advance(clock, events, action="NEXT_EVENT")
    assert len(emitted) == 2 and changed.simulated_at == t.instant(MID).isoformat()
    with pytest.raises(ValueError, match="Frozen"):
        t.advance(changed, [replace(events[0], scheduled_at=END), events[1]], action="NEXT_EVENT")
    with pytest.raises(ValueError, match="Cyclic"):
        t.advance(
            clock,
            [t.ScheduledEvent("a", MID, ("b",)), t.ScheduledEvent("b", END, ("a",))],
            action="NEXT_EVENT",
        )
    with pytest.raises(ValueError, match="backward"):
        t.advance(changed, events, action="TARGET_DATE", target=START)


@pytest.mark.parametrize(
    "start,expected",
    [
        ("2026-03-06T09:00:00-08:00", "2026-03-09T16:00:00+00:00"),
        ("2026-10-30T09:00:00-07:00", "2026-11-02T17:00:00+00:00"),
        ("2026-01-30T09:00:00-08:00", "2026-02-02T17:00:00+00:00"),
    ],
)
def test_business_day_preserves_local_wall_hour_across_dst_and_month(start, expected):
    clock, _ = t.advance(
        t.SimulationClock(start), [], action="ONE_BUSINESS_DAY", timezone_name="America/Los_Angeles"
    )
    assert clock.simulated_at == expected


def test_holidays_milestone_and_repeat_next_command():
    clock = t.SimulationClock("2026-07-02T09:00:00-07:00")
    next_clock, _ = t.advance(
        clock,
        [],
        action="ONE_BUSINESS_DAY",
        timezone_name="America/Los_Angeles",
        holidays=["2026-07-03"],
    )
    assert next_clock.simulated_at == "2026-07-06T16:00:00+00:00"
    final, _ = t.advance(next_clock, [], action="MILESTONE", target="end", milestones={"end": END})
    assert final.simulated_at == t.instant(END).isoformat()
    with pytest.raises(ValueError, match="Unknown milestone"):
        t.advance(final, [], action="MILESTONE", target="absent", milestones={})


def test_imported_history_cannot_claim_early_or_dependency_free_execution():
    events = [t.ScheduledEvent("a", MID), t.ScheduledEvent("b", END, ("a",))]
    for completed in [(("a", START),), (("b", END),)]:
        with pytest.raises(ValueError, match="history violates"):
            t.advance(t.SimulationClock(END, completed), events, action="NEXT_EVENT")
