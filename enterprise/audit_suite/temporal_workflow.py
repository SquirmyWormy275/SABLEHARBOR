"""Dated procedure records, implementation changes and explicit remaining work."""

from copy import deepcopy
from dataclasses import asdict
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .composition import instant
from .store import DomainError, identifier
from .temporal import Coverage, ImplementationVersion, Interval, coverage_report

COMMANDS = {
    "coverage.record",
    "coverage.propose_remaining",
    "coverage.confirm_remaining",
    "implementation.change",
}


def bound(value: str, *, inclusive_end: bool = False, timezone: str = "UTC") -> str:
    if isinstance(value, str) and len(value) == 10:
        day = date.fromisoformat(value)
        if inclusive_end:
            day += timedelta(days=1)
        value = datetime.combine(day, time(), ZoneInfo(timezone)).isoformat()
    return instant(value).isoformat()


def initial(state: dict) -> dict:
    scope = state["scope"]
    epoch = state.get("generation_epoch", 0)
    return {
        "versions": [
            {
                "id": f"IMPL-E{epoch}-{c['id']}-{boundary}",
                "control_id": c["id"],
                "boundary_id": boundary,
                "owner_id": c["owner_ids"][0],
                "effective": {
                    "start": bound(scope["period_start"], timezone=scope.get("timezone", "UTC")),
                    "end": bound(
                        scope["period_end"],
                        inclusive_end=True,
                        timezone=scope.get("timezone", "UTC"),
                    ),
                },
                "source_implementation_version": c["implementation_version"],
            }
            for c in state["controls"]
            for boundary in scope["boundaries"]
        ],
        "work": [],
        "version_history": [],
        "proposals": [],
    }


def current(state: dict) -> dict:
    return state.get("temporal", {}).get(str(state.get("generation_epoch", 0))) or initial(state)


def reports(state: dict) -> list[dict]:
    data = current(state)
    versions = [
        ImplementationVersion(
            **{
                key: (Interval(**row[key]) if key == "effective" else row[key])
                for key in ("id", "control_id", "boundary_id", "effective", "owner_id")
            }
        )
        for row in data["versions"]
    ]
    index = {v.id: v for v in versions}
    work, reassess = [], []
    for row in data["work"]:
        version = index[row["implementation_id"]]
        if not (
            instant(version.effective.start)
            <= instant(row["covered"]["start"])
            <= instant(row["covered"]["end"])
            <= instant(version.effective.end)
        ):
            reassess.append(row["id"])
            continue
        work.append(
            Coverage(
                **{
                    key: Interval(**row[key])
                    if key == "covered"
                    else tuple(row[key])
                    if key == "evidence_ids"
                    else row[key]
                    for key in (
                        "id",
                        "implementation_id",
                        "covered",
                        "performed_at",
                        "received_at",
                        "kind",
                        "result",
                        "evidence_ids",
                        "rationale",
                    )
                }
            )
        )
    result = []
    for control in state["controls"]:
        for boundary in state["scope"]["boundaries"]:
            scope = {
                "control_id": control["id"],
                "boundary_id": boundary,
                "reporting_basis": state["scope"]["temporal_basis"],
                "as_of": bound(
                    state["scope"]["period_end"], timezone=state["scope"].get("timezone", "UTC")
                ),
                "period_start": bound(
                    state["scope"]["period_start"], timezone=state["scope"].get("timezone", "UTC")
                ),
                "period_end": bound(
                    state["scope"]["period_end"],
                    inclusive_end=True,
                    timezone=state["scope"].get("timezone", "UTC"),
                ),
            }
            report = coverage_report(scope, versions, work, as_of=state["simulated_at"])
            exception_key = (
                "exception_ids"
                if scope["reporting_basis"] == "POINT_IN_TIME"
                else "historical_exception_ids"
            )
            report[exception_key] = sorted(
                set(report.get(exception_key, []))
                | {
                    r["id"]
                    for r in data["work"]
                    if r["result"] == "EXCEPTION"
                    and index[r["implementation_id"]].control_id == control["id"]
                    and index[r["implementation_id"]].boundary_id == boundary
                }
            )
            result.append(
                {
                    **report,
                    "control_id": control["id"],
                    "boundary_id": boundary,
                    "records_requiring_reassessment": [
                        wid
                        for wid in reassess
                        if any(
                            r["id"] == wid
                            and index[r["implementation_id"]].control_id == control["id"]
                            and index[r["implementation_id"]].boundary_id == boundary
                            for r in data["work"]
                        )
                    ],
                }
            )
    return result


def handle(engine, state: dict, kind: str, payload: dict, stamped: dict) -> None:
    if state["phase"] != "ACTIVE":
        raise DomainError("Start the engagement before recording coverage work")
    epoch = str(state.get("generation_epoch", 0))
    data = state.setdefault("temporal", {}).setdefault(epoch, initial(state))

    def scoped_bound(value, *, inclusive_end=False):
        return bound(
            value, inclusive_end=inclusive_end, timezone=state["scope"].get("timezone", "UTC")
        )

    def text(field):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > 20000:
            raise DomainError("Record " + field.replace("_", " "))
        return value.strip()

    if kind == "coverage.record":
        version = next(
            (v for v in data["versions"] if v["id"] == payload.get("implementation_id")), None
        )
        if version is None:
            raise DomainError("Select a current scoped implementation version")
        ids = payload.get("evidence_ids", [])
        if (
            not isinstance(ids, list)
            or any(not isinstance(i, str) for i in ids)
            or len(set(ids)) != len(ids)
        ):
            raise DomainError("Evidence references must be distinct identifiers")
        available = {
            m["id"]: m
            for m in state["artifacts"]
            if m["status"] == "AVAILABLE" and m.get("audience", "LEARNER") == "LEARNER"
        }
        if not set(ids) <= available.keys():
            raise DomainError("Coverage evidence must be observable retained records")
        point = state["scope"]["temporal_basis"] == "POINT_IN_TIME"
        interval = Interval(
            scoped_bound(text("covered_start")),
            scoped_bound(text("covered_end"), inclusive_end=not point),
        )
        performed = scoped_bound(payload.get("performed_at", state["simulated_at"]))
        if instant(performed) > instant(state["simulated_at"]):
            raise DomainError("Cannot record a future procedure as completed")
        received = max(
            [scoped_bound(available[i].get("received_at", state["simulated_at"])) for i in ids]
            or [state["simulated_at"]],
            key=instant,
        )
        record = Coverage(
            identifier("COV"),
            version["id"],
            interval,
            performed,
            received,
            text("procedure_kind"),
            text("result"),
            tuple(ids),
            text("rationale"),
        )
        if not (
            instant(version["effective"]["start"])
            <= instant(interval.start)
            <= instant(interval.end)
            <= instant(version["effective"]["end"])
        ):
            raise DomainError(
                "Coverage crosses implementation versions; record separate procedures"
            )
        row = {
            **asdict(record),
            "methodology": text("methodology"),
            "nature_timing_extent": text("nature_timing_extent"),
            **stamped,
        }
        data["work"].append(row)
    elif kind == "implementation.change":
        version = next(
            (v for v in data["versions"] if v["id"] == payload.get("implementation_id")), None
        )
        if version is None:
            raise DomainError("Select the implementation being changed")
        changed = scoped_bound(text("effective_at"))
        if not (
            instant(version["effective"]["start"])
            < instant(changed)
            < instant(version["effective"]["end"])
            and instant(changed) <= instant(state["simulated_at"])
        ):
            raise DomainError(
                "Implementation change must fall within its effective period "
                "and known simulation time"
            )
        owner = text("owner_id")
        if owner not in {p["id"] for p in state["people"]}:
            raise DomainError("Select an existing scoped owner")
        data["version_history"].append(
            {"prior": deepcopy(version), "rationale": text("rationale"), **stamped}
        )
        successor = {
            **deepcopy(version),
            "id": identifier("IMPL"),
            "predecessor_id": version["id"],
            "owner_id": owner,
            "effective": {"start": changed, "end": version["effective"]["end"]},
            "source_implementation_version": text("implementation_version"),
            "change_basis": "LEARNER_RECORDED_REQUIRES_SOURCE_REVIEW",
        }
        version["effective"]["end"] = changed
        data["versions"].append(successor)
    elif kind == "coverage.propose_remaining":
        report = next(
            (
                r
                for r in reports(state)
                if r["control_id"] == payload.get("control_id")
                and r["boundary_id"] == payload.get("boundary_id")
            ),
            None,
        )
        if report is None:
            raise DomainError("Select a scoped control and boundary")
        selected = payload.get("source_request_ids", [])
        known = {
            r["id"]: r
            for r in state["requests"]
            if r.get("control_id") == report["control_id"]
            and r.get("boundary_id") == report["boundary_id"]
            and r.get("plan_epoch", 0) == int(epoch)
        }
        if (
            not isinstance(selected, list)
            or not selected
            or any(not isinstance(i, str) for i in selected)
            or len(set(selected)) != len(selected)
            or not set(selected) <= known.keys()
        ):
            raise DomainError(
                "Select current scoped source requests for the proposed remaining work"
            )
        proposal = {
            "id": identifier("ROLL"),
            "control_id": report["control_id"],
            "boundary_id": report["boundary_id"],
            "coverage_report": report,
            "source_request_ids": selected,
            "message": text("message"),
            "rationale": text("rationale"),
            "status": "PROPOSED",
            **stamped,
        }
        data["proposals"].append(proposal)
        state["tasks"].append(
            {
                "id": identifier("TASK"),
                "kind": "ROLL_FORWARD",
                "title": "Remaining-period work: " + report["control_id"],
                "control_id": report["control_id"],
                "boundary_id": report["boundary_id"],
                "proposal_id": proposal["id"],
                "status": "NOT_STARTED",
                "conclusion": "NOT_RUN",
                "note": proposal["rationale"],
                "history": [],
                "scope_version": int(epoch),
            }
        )
    elif kind == "coverage.confirm_remaining":
        proposal = next((r for r in data["proposals"] if r["id"] == payload.get("id")), None)
        if not proposal or proposal["status"] != "PROPOSED":
            raise DomainError("Select an unissued remaining-work proposal")
        message = text("message")
        for request_id in proposal["source_request_ids"]:
            request = next(r for r in state["requests"] if r["id"] == request_id)
            engine._request_command(
                state,
                "pbc.issue" if request["status"] == "DRAFT" else "pbc.followup",
                {"request_id": request_id, "message": message},
                stamped,
            )
        proposal.update(status="ISSUED", confirmed_message=message, confirmed_by=stamped)
    else:
        raise DomainError("Unknown temporal workflow command")
