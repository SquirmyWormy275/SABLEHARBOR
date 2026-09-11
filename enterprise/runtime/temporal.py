"""Evidence-bearing construction transitions, independent of dates in forecasts."""

from datetime import date

STAGES = (
    "LAND_ACQUIRED",
    "PRECONSTRUCTION",
    "CIVIL_WORKS",
    "SHELL_CONSTRUCTION",
    "SHELL_COMPLETE",
    "PLANT_INSTALLATION",
    "COMMISSIONING",
    "ACCEPTED_OPERATION",
)


def construction(events, as_of, known_on):
    cutoff, knowledge = date.fromisoformat(as_of), date.fromisoformat(known_on)
    state = {
        "stage": "NOT_ACQUIRED",
        "shell_complete": False,
        "commissioned_kw": 0,
        "operating": False,
        "accepted_event_ids": [],
    }
    identifiers = set()
    for event in sorted(events, key=lambda e: (e["effective_on"], e["sequence"])):
        required = {
            "id",
            "sequence",
            "stage",
            "effective_on",
            "recorded_on",
            "origin",
            "accepted_by",
            "evidence_ref",
            "commissioned_kw",
            "classification",
        }
        if set(event) != required or event["id"] in identifiers:
            raise ValueError("Invalid construction event schema or duplicate identity")
        identifiers.add(event["id"])
        if event["stage"] not in STAGES or event["origin"] not in {
            "SYNTHETIC_SCENARIO_EVENT",
            "ACTUAL_COLLECTED_EVIDENCE",
        }:
            raise ValueError("Forecast is not a construction event")
        if (
            not event["accepted_by"]
            or not event["evidence_ref"]
            or event["classification"] != "SYNTHETIC_ENTERPRISE"
        ):
            raise ValueError("Construction event requires acceptance and scope")
        if (
            type(event["commissioned_kw"]) not in (int, float)
            or event["commissioned_kw"] < 0
        ):
            raise ValueError("Invalid commissioned capacity")
        if (
            date.fromisoformat(event["effective_on"]) > cutoff
            or date.fromisoformat(event["recorded_on"]) > knowledge
        ):
            continue
        index = STAGES.index(event["stage"])
        previous = STAGES.index(state["stage"]) if state["stage"] in STAGES else -1
        if index != previous + 1:
            raise ValueError("Construction transition requires accepted predecessor")
        if index < STAGES.index("COMMISSIONING") and event["commissioned_kw"]:
            raise ValueError("Shell and installed plant are not commissioned capacity")
        if event["stage"] == "ACCEPTED_OPERATION" and event["commissioned_kw"] <= 0:
            raise ValueError("Operation requires accepted commissioned capacity")
        state.update(
            stage=event["stage"],
            shell_complete=index >= STAGES.index("SHELL_COMPLETE"),
            commissioned_kw=event["commissioned_kw"],
            operating=event["stage"] == "ACCEPTED_OPERATION",
        )
        state["accepted_event_ids"].append(event["id"])
    return state


def baseline_events(data):
    owned = next(s for s in data["sites"]["sites"] if s["id"] == "RUNTIME-NN-OWNED-DC")
    return [
        dict(
            id="RT-EVENT-LAND",
            sequence=1,
            stage="LAND_ACQUIRED",
            effective_on=owned["planning_purchase_date"],
            recorded_on=data["sites"]["recorded_on"],
            origin="SYNTHETIC_SCENARIO_EVENT",
            accepted_by="OWNER_DECISION_PR119",
            evidence_ref="docs/legal/MOCK_DEED_NORTHERN_NEVADA_DATA_CENTER_2026-09-04.md",
            commissioned_kw=0,
            classification="SYNTHETIC_ENTERPRISE",
        ),
        dict(
            id="RT-EVENT-PRECONSTRUCTION",
            sequence=2,
            stage="PRECONSTRUCTION",
            effective_on="2026-09-11",
            recorded_on=data["sites"]["recorded_on"],
            origin="SYNTHETIC_SCENARIO_EVENT",
            accepted_by="OWNER_DECISION_PR119",
            evidence_ref="docs/canon/RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md",
            commissioned_kw=0,
            classification="SYNTHETIC_ENTERPRISE",
        ),
    ]
