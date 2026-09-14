"""Simulation time and reported temporal coverage, isolated from authorization clocks.

Period intervals are half-open [start,end); point-in-time scopes use explicit
as_of. Coverage measures recorded work, not professional evidence sufficiency.
No function reads, changes or monkeypatches the real host clock.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, timedelta
from zoneinfo import ZoneInfo

from enterprise.ccf.operations.testing import instant

from .populations import digest, text, unique


@dataclass(frozen=True)
class Interval:
    start: str
    end: str

    def __post_init__(self):
        if instant(self.start) > instant(self.end):
            raise ValueError("Interval ends before it starts")
        object.__setattr__(self, "start", instant(self.start).isoformat())
        object.__setattr__(self, "end", instant(self.end).isoformat())

    @property
    def point(self):
        return self.start == self.end


def overlap(a: Interval, b: Interval):
    start, end = max(instant(a.start), instant(b.start)), min(instant(a.end), instant(b.end))
    return Interval(start.isoformat(), end.isoformat()) if start < end else None


def gaps(scope: Interval, coverage):
    """Exact interval union/complement; no universal roll-forward day threshold."""
    if scope.point:
        raise ValueError("Use point-in-time coverage report for an assessment instant")
    clipped = sorted(
        (x for c in coverage if (x := overlap(scope, c))), key=lambda x: instant(x.start)
    )
    cursor, end = instant(scope.start), instant(scope.end)
    result = []
    for item in clipped:
        start, stop = instant(item.start), instant(item.end)
        if start > cursor:
            result.append(Interval(cursor.isoformat(), start.isoformat()))
        cursor = max(cursor, stop)
    if cursor < end:
        result.append(Interval(cursor.isoformat(), end.isoformat()))
    return tuple(result)


@dataclass(frozen=True)
class ImplementationVersion:
    id: str
    control_id: str
    boundary_id: str
    effective: Interval
    owner_id: str

    def __post_init__(self):
        for value in (self.id, self.control_id, self.boundary_id, self.owner_id):
            text(value)
        if not isinstance(self.effective, Interval) or self.effective.point:
            raise ValueError("Implementation needs a positive effective interval")


@dataclass(frozen=True)
class Coverage:
    id: str
    implementation_id: str
    covered: Interval
    performed_at: str
    received_at: str
    kind: str
    result: str
    evidence_ids: tuple[str, ...]
    rationale: str

    def __post_init__(self):
        for value in (self.id, self.implementation_id, self.rationale):
            text(value)
        if not isinstance(self.covered, Interval):
            raise ValueError("Coverage interval required")
        instant(self.performed_at)
        instant(self.received_at)
        if type(self.evidence_ids) is not tuple:
            raise ValueError("Immutable evidence references required")
        unique(self.evidence_ids)
        if self.kind not in {
            "TOD",
            "IMPLEMENTATION",
            "TOE",
            "SUBSTANTIVE",
            "ROLL_FORWARD",
            "INQUIRY",
        }:
            raise ValueError("Unknown work kind")
        if self.result not in {
            "RECORDED",
            "EXCEPTION",
            "INSUFFICIENT_EVIDENCE",
            "NO_CHANGE_REPORTED",
            "NOT_CONCLUDED",
        }:
            raise ValueError("Unknown work disposition")
        if self.result in {"RECORDED", "EXCEPTION"} and not self.evidence_ids:
            raise ValueError("Addressed work requires retained evidence references")
        if instant(self.performed_at) < instant(self.covered.end):
            raise ValueError("A procedure cannot establish future coverage")


def coverage_report(scope, versions, work, *, as_of=None):
    """Scope has control_id,boundary_id,reporting_basis,period_start/end or as_of.

    Optional procedure_kind limits a specific task. For PERIOD, unqualified TOD,
    implementation and inquiry statements never automatically cover TOE periods.
    as_of is an optional simulated observation cutoff, not an authorization clock.
    """
    versions, work = tuple(versions), tuple(work)
    unique(v.id for v in versions)
    unique(w.id for w in work)
    selected = sorted(
        (
            v
            for v in versions
            if v.control_id == scope["control_id"] and v.boundary_id == scope["boundary_id"]
        ),
        key=lambda v: instant(v.effective.start),
    )
    for left, right in zip(selected, selected[1:], strict=False):
        if overlap(left.effective, right.effective):
            raise ValueError("Implementation effective periods overlap")
    index = {v.id: v for v in versions}
    for item in work:
        if item.implementation_id not in index:
            raise ValueError("Work references unknown implementation")
        effective = index[item.implementation_id].effective
        if (
            not instant(effective.start)
            <= instant(item.covered.start)
            <= instant(item.covered.end)
            <= instant(effective.end)
        ):
            raise ValueError("Work coverage exceeds its implementation version")
    cutoff = instant(as_of) if as_of else None
    available = [
        w
        for w in work
        if not cutoff or max(instant(w.performed_at), instant(w.received_at)) <= cutoff
    ]
    usable = [w for w in available if w.result in {"RECORDED", "EXCEPTION"}]
    basis = scope["reporting_basis"]
    if basis == "POINT_IN_TIME":
        point = instant(scope["as_of"])
        applicable = [
            v for v in selected if instant(v.effective.start) <= point < instant(v.effective.end)
        ]
        kinds = (
            {scope["procedure_kind"]} if scope.get("procedure_kind") else {"TOD", "IMPLEMENTATION"}
        )
        covered_kinds = {
            w.kind
            for w in usable
            if any(w.implementation_id == v.id for v in applicable)
            and (
                (w.covered.point and instant(w.covered.start) == point)
                or instant(w.covered.start) <= point < instant(w.covered.end)
            )
        }
        return dict(
            reporting_basis=basis,
            as_of=point.isoformat(),
            applicable_versions=[v.id for v in applicable],
            missing_kinds=sorted(kinds - covered_kinds),
            full_period_toe_required=False,
            reported_work_complete=bool(applicable) and kinds <= covered_kinds,
            professional_sufficiency="NOT_ASSERTED",
            exception_ids=[
                w.id
                for w in available
                if w.result == "EXCEPTION" and any(w.implementation_id == v.id for v in applicable)
            ],
        )
    if basis != "PERIOD":
        raise ValueError("Unknown reporting basis")
    period = Interval(scope["period_start"], scope["period_end"])
    if period.point:
        raise ValueError("Period reporting requires positive interval")
    kinds = (
        {scope["procedure_kind"]}
        if scope.get("procedure_kind")
        else {"TOE", "SUBSTANTIVE", "ROLL_FORWARD"}
    )
    reports, version_intervals = [], []
    for version in selected:
        applicable = overlap(period, version.effective)
        if not applicable:
            continue
        version_intervals.append(applicable)
        rows = [
            w
            for w in available
            if w.implementation_id == version.id and overlap(applicable, w.covered)
        ]
        addressed = [
            w.covered
            for w in usable
            if w.implementation_id == version.id and w.kind in kinds and not w.covered.point
        ]
        reports.append(
            dict(
                implementation_id=version.id,
                owner_id=version.owner_id,
                scope=asdict(applicable),
                gaps=[asdict(i) for i in gaps(applicable, addressed)],
                work_ids=[w.id for w in rows],
                exception_ids=[w.id for w in rows if w.result == "EXCEPTION"],
                limitation_ids=[
                    w.id
                    for w in rows
                    if w.result in {"INSUFFICIENT_EVIDENCE", "NO_CHANGE_REPORTED", "NOT_CONCLUDED"}
                ],
            )
        )
    missing = gaps(period, version_intervals)
    return dict(
        reporting_basis=basis,
        versions=reports,
        missing_implementation_intervals=[asdict(i) for i in missing],
        reported_work_complete=bool(reports)
        and not missing
        and not any(r["gaps"] for r in reports),
        professional_sufficiency="NOT_ASSERTED",
        historical_exception_ids=[wid for r in reports for wid in r["exception_ids"]],
    )


@dataclass(frozen=True)
class ScheduledEvent:
    id: str
    scheduled_at: str
    requires: tuple[str, ...] = ()
    effects_json: str = "{}"

    def __post_init__(self):
        text(self.id)
        instant(self.scheduled_at)
        if type(self.requires) is not tuple:
            raise ValueError("Immutable prerequisite IDs required")
        unique(self.requires)
        if self.id in self.requires:
            raise ValueError("Event cannot depend on itself")
        json.loads(self.effects_json)


@dataclass(frozen=True)
class SimulationClock:
    simulated_at: str
    completed: tuple[tuple[str, str], ...] = ()
    plan_digest: str | None = None
    requests: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        instant(self.simulated_at)
        if type(self.completed) is not tuple or type(self.requests) is not tuple:
            raise ValueError("Immutable clock history required")
        if any(
            type(item) is not tuple or len(item) != 2 for item in self.completed + self.requests
        ):
            raise ValueError("Immutable clock history pairs required")
        unique(k for k, _ in self.completed)
        unique(k for k, _ in self.requests)
        for _, at in self.completed:
            if instant(at) > instant(self.simulated_at):
                raise ValueError("Completed event lies after simulation clock")


def _business_day(value, timezone_name, holidays):
    zone = ZoneInfo(timezone_name)
    local = value.astimezone(zone)
    excluded = {date.fromisoformat(d) for d in holidays}
    candidate = local + timedelta(days=1)
    while candidate.weekday() >= 5 or candidate.date() in excluded:
        candidate += timedelta(days=1)
    # A local wall time may fall in a DST gap. Reject, rather than silently shifting.
    restored = candidate.astimezone(UTC).astimezone(zone)
    if restored.replace(tzinfo=None) != candidate.replace(tzinfo=None):
        raise ValueError("Target local business-day time does not exist after DST change")
    return candidate.astimezone(UTC)


def advance(
    clock: SimulationClock,
    events,
    *,
    action,
    target=None,
    milestones=None,
    timezone_name="UTC",
    holidays=(),
    request_id=None,
):
    """Return (new_clock, emitted_records); caller authorizes and persists atomically.

    Optional request_id makes retries no-ops and rejects changed command payloads.
    Frozen plan binds all supplied events. New authored events require an explicit
    run version/migration rather than modifying this plan behind the learner.
    """
    events = tuple(events)
    unique(e.id for e in events)
    index = {e.id: e for e in events}
    for event in events:
        if not set(event.requires) <= set(index):
            raise ValueError("Unknown event prerequisite")
    plan_hash = digest([asdict(e) for e in sorted(events, key=lambda e: e.id)])
    if clock.plan_digest not in (None, plan_hash):
        raise ValueError("Frozen simulation event plan changed")
    # Topological pass rejects cycles even outside the selected date window.
    pending = set(index)
    resolved = set()
    while pending:
        ready = {i for i in pending if set(index[i].requires) <= resolved}
        if not ready:
            raise ValueError("Cyclic simulation prerequisites")
        pending -= ready
        resolved |= ready
    prior = dict(clock.completed)
    if not set(prior) <= set(index):
        raise ValueError("Clock contains events outside plan")
    for event_id, completed_at in prior.items():
        event = index[event_id]
        if (
            instant(completed_at) < instant(event.scheduled_at)
            or not set(event.requires) <= set(prior)
            or any(
                instant(prior[dependency]) > instant(completed_at) for dependency in event.requires
            )
        ):
            raise ValueError("Completed simulation history violates event chronology")
    command = digest(
        dict(
            action=action,
            target=target,
            milestones=milestones,
            timezone_name=timezone_name,
            holidays=sorted(holidays),
        )
    )
    if request_id:
        text(request_id)
        old = dict(clock.requests).get(request_id)
        if old:
            if old != command:
                raise ValueError("Idempotency key reused with a different command")
            return clock, ()
    current = instant(clock.simulated_at)
    if action == "NEXT_EVENT":
        ready = [e for e in events if e.id not in prior and set(e.requires) <= set(prior)]
        destination = (
            max(current, min(instant(e.scheduled_at) for e in ready)) if ready else current
        )
    elif action == "ONE_BUSINESS_DAY":
        destination = _business_day(current, timezone_name, holidays)
    elif action == "TARGET_DATE":
        destination = instant(target)
    elif action == "MILESTONE":
        if not milestones or target not in milestones:
            raise ValueError("Unknown milestone")
        destination = instant(milestones[target])
    else:
        raise ValueError("Unknown simulation-clock action")
    if destination < current:
        raise ValueError("Simulation clock cannot move backward")
    emitted = []
    while True:
        ready = [
            e
            for e in events
            if e.id not in prior
            and set(e.requires) <= set(prior)
            and instant(e.scheduled_at) <= destination
        ]
        if not ready:
            break

        # Eligibility time follows the latest prerequisite, then stable event ID.
        def eligible_time(e):
            return max([current, instant(e.scheduled_at), *(instant(prior[i]) for i in e.requires)])

        event = min(ready, key=lambda e: (eligible_time(e), e.id))
        at = eligible_time(event)
        prior[event.id] = at.isoformat()
        emitted.append(
            dict(
                event_id=event.id,
                simulated_at=at.isoformat(),
                scheduled_at=instant(event.scheduled_at).isoformat(),
                effects=json.loads(event.effects_json),
                idempotency_key=event.id,
                plan_digest=plan_hash,
            )
        )
    requests = clock.requests + ((request_id, command),) if request_id else clock.requests
    return SimulationClock(
        destination.isoformat(), tuple(prior.items()), plan_hash, requests
    ), tuple(emitted)
