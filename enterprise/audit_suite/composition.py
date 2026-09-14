"""Private, deterministic scenario event execution.

The caller persists progress with its authorized engagement transaction. Definitions
and unreleased records stay private; only the returned observable effects may be
projected to a learner. Simulation dates never participate in authentication.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .store import DomainError, digest


def compose_control(
    clean: dict, cases: list[dict], control: dict, scope: dict, people: dict[str, str]
) -> dict:
    """Bind process-specific authored cases to a control without cross-process substitution.

    The baseline remains immutable in the private plan. A defect case replaces the
    affected support packet rather than simultaneously publishing a clean answer.
    Design-only cases retain operating records without asserting operating failure.
    """
    from .corpus import bind_tokens

    if not cases:
        return clean
    if len(cases) > 1:
        overlays = [
            c
            for c in cases
            if c["definition"].get("binding_contract", {}).get("portable_behavior", {}).get("mode")
            == "BEHAVIOR_OVERLAY"
        ]
        primary = [c for c in cases if c not in overlays]
        from .behavior_composition import overlay

        if len(primary) > 1:
            from .causal_composition import compose

            plan = compose(clean, primary, control, scope, people, compose_one=compose_control)
        else:
            plan = (
                compose_control(clean, primary, control, scope, people)
                if primary
                else deepcopy(clean)
            )
        plan.setdefault("baseline_private", deepcopy(clean))
        for entry in overlays:
            plan = overlay(plan, entry, control, scope, people)
        return plan
    entry = cases[0]
    if entry["definition"]["selector_id"] == "MM-02" and control["id"] not in entry[
        "definition"
    ].get("binding_contract", {}).get("applicable_control_ids", []):
        from .portable_composition import compose

        return compose(clean, entry, control, scope, people)
    from .parameters import apply as apply_parameters

    definition = apply_parameters(entry["definition"], entry.get("parameters", {}))
    binding = definition.get("binding_contract", {})
    if control["id"] not in binding.get("applicable_control_ids", []):
        raise DomainError("Scenario evidence belongs to a different business process")
    minimum = binding.get("minimum_period_business_days", 0)
    if type(minimum) is not int or minimum < 0:
        raise DomainError("Invalid scenario period requirement")
    if minimum:
        from datetime import date

        start, end = (
            date.fromisoformat(scope["period_start"]),
            date.fromisoformat(scope["period_end"]),
        )
        available = 0
        while start < end:
            start += timedelta(days=1)
            if start.weekday() < 5 and start.isoformat() not in scope.get("holidays", []):
                available += 1
        if available < minimum:
            raise DomainError(
                "The selected scenario requires a longer operating period",
                code="SCENARIO_PERIOD_INCOMPATIBLE",
            )
    assignment = control["assignment"]
    owner_id = assignment["primary_person_id"]
    operating_reviewer = assignment.get("operating_reviewer_person_id")
    if not operating_reviewer or operating_reviewer not in people:
        raise DomainError("Resolve management operating approval separately from assurance review")
    bindings = {
        "owner": people[owner_id],
        "control_id": control["id"],
        "boundary": scope["boundary_id"],
        "period_start": scope["period_start"],
        "period_end": scope["period_end"],
        "reviewer": people[operating_reviewer],
        "custodian": people[assignment["custodian_person_id"]],
        "artifact_title": definition["artifacts"][0]["recipe"].get("title", "Source record"),
    }
    bound = bind_tokens(definition, bindings)
    # Period-wide authored knowledge is held until its period has ended. Earlier
    # knowledge needs separately verified fact/as-of bindings, not a model claim.
    knowledge_available = scope["period_end"]
    if len(knowledge_available) == 10:
        knowledge_available = (
            (datetime.fromisoformat(knowledge_available) + timedelta(days=1))
            .replace(tzinfo=ZoneInfo(scope.get("timezone", "UTC")))
            .isoformat()
        )
    # Source-derived statements cannot disclose period-wide facts before the
    # source cutoff. Keep separately authored change/release mechanics intact.
    gated_events = []
    for event in bound["events"]:
        statements = [effect for effect in event["effects"] if effect["operation"] == "statement"]
        other_effects = [
            effect for effect in event["effects"] if effect["operation"] != "statement"
        ]
        if not statements:
            gated_events.append(event)
            continue
        notice = {**event, "effects": statements, "not_before": knowledge_available}
        if event.get("not_before"):
            original_cutoff = event["not_before"]
            if len(original_cutoff) == 10:
                original_cutoff = (
                    datetime.fromisoformat(original_cutoff)
                    .replace(tzinfo=ZoneInfo(scope.get("timezone", "UTC")))
                    .isoformat()
                )
            if instant(original_cutoff) > instant(knowledge_available):
                notice["not_before"] = original_cutoff
        if other_effects:
            gated_events.append({**event, "effects": other_effects})
            notice["id"] = event["id"] + "-SOURCE-NOTICE"
        gated_events.append(notice)
    bound["events"] = gated_events
    plan = deepcopy(clean)
    plan["baseline_private"] = deepcopy(clean)
    design_only = definition["selector_id"] == "MM-17"
    if design_only:
        plan["requests"] = [
            r for r in plan["requests"] if r.get("coverage", {}).get("kind") != "DESIGN_SUPPORT"
        ]
    else:
        plan["requests"] = []
    plan["scenario_cases"] = [{**deepcopy(entry), "bound_definition": bound}]
    plan["actor_knowledge"] = []
    # Named actor knowledge is privately routed; the persona must still qualify
    # statements and cannot turn a belief or an unseen file into auditor evidence.
    facts = {f["id"]: f for f in bound["facts"]}
    for actor in bound["actor_knowledge"]:
        candidates = [pid for pid, name in people.items() if name == actor["role_ref"]]
        if len(candidates) != 1:
            raise DomainError("Scenario actor does not resolve to exactly one scoped person")
        plan["actor_knowledge"].append(
            {
                "person_id": candidates[0],
                "available_by": knowledge_available,
                "summary": "\n".join(facts[f]["statement"] for f in actor["knows_fact_ids"]),
                "beliefs": actor.get("beliefs", []),
            }
        )
    initial = [a for a in bound["artifacts"] if a["stage"] == "INITIAL"]
    if not initial:
        raise DomainError("A case requires an initial auditable response")
    plan["requests"].append(
        {
            "id": "CASE-" + digest([definition["id"], control["id"], scope["boundary_id"]])[:20],
            "title": initial[0]["recipe"].get("title", "Requested supporting records"),
            "purpose": initial[0]["request_purpose"],
            "available_by": knowledge_available,
            "scenario_definition": bound,
            "artifact_recipes": [
                {
                    "name": a["name"],
                    "recipe": a["recipe"],
                    "scenario_artifact_id": a["id"],
                    "stage": a["stage"],
                    "available_by": max(
                        knowledge_available, a.get("available_on", knowledge_available)
                    ),
                }
                for a in bound["artifacts"]
            ],
            "coverage": {
                "control_id": control["id"],
                "boundary_id": scope["boundary_id"],
                "period_start": scope["period_start"],
                "period_end": scope["period_end"],
                "kind": "DESIGN_SUPPORT" if design_only else "COMPANY_SUPPORT",
                "professional_sufficiency": "NOT_ASSERTED",
            },
        }
    )
    return plan


def instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise DomainError("Scenario event timestamps must include a timezone")
    return parsed


def business_due(start: str, days: int, timezone: str, holidays: list[str]) -> str:
    if type(days) is not int or days < 0:
        raise DomainError("Scenario delay must be a nonnegative business-day count")
    date = instant(start).astimezone(ZoneInfo(timezone))
    remaining = days
    while remaining:
        date += timedelta(days=1)
        if date.weekday() < 5 and date.date().isoformat() not in holidays:
            remaining -= 1
    return date.isoformat()


def advance_events(
    definition: dict,
    progress: dict | None,
    *,
    trigger: str,
    now: str,
    timezone: str,
    holidays: list[str] | None = None,
) -> tuple[dict, list[dict]]:
    """Arm events once and emit each due effect exactly once.

    REQUEST anchors the case clock. FOLLOWUP never reveals records until actually
    requested; CLOCK only advances already armed events. A retry cannot reset a
    delay. Calendar conversion preserves the local time across DST transitions.
    """
    if trigger not in {"REQUEST", "FOLLOWUP", "CLOCK"}:
        raise DomainError("Unknown scenario interaction trigger")
    at = instant(now)
    state = (
        deepcopy(progress)
        if progress
        else {
            "definition_digest": digest(definition),
            "armed": {},
            "completed": [],
            "started_at": None,
            "last_at": None,
        }
    )
    if state["definition_digest"] != digest(definition):
        raise DomainError("An active scenario definition cannot be replaced")
    if state["last_at"] and at < instant(state["last_at"]):
        raise DomainError("Scenario time cannot move backwards")
    if trigger == "FOLLOWUP" and not state["started_at"]:
        raise DomainError("A follow-up requires an issued request")
    if trigger == "REQUEST" and not state["started_at"]:
        state["started_at"] = now
    if trigger == "FOLLOWUP":
        state["followup_count"] = state.get("followup_count", 0) + 1
    effects = []
    for event in definition["events"]:
        # Stable opaque progress keys do not disclose option or variant names.
        key = digest([definition["id"], event["id"]])[:24]
        if key in state["completed"]:
            continue
        minimum = event.get("minimum_followups", 0)
        if type(minimum) is not int or not 0 <= minimum <= 5:
            raise DomainError("Invalid finite follow-up gate")
        if event["trigger"] == "FOLLOWUP" and state.get("followup_count", 0) < minimum:
            continue
        if key not in state["armed"] and state["started_at"]:
            if event["trigger"] == trigger or (
                event["trigger"] == "CLOCK" and trigger == "REQUEST"
            ):
                state["armed"][key] = business_due(
                    now, event["offset_business_days"], timezone, holidays or []
                )
                not_before = event.get("not_before")
                if not_before:
                    if len(not_before) == 10:
                        not_before = (
                            datetime.fromisoformat(not_before)
                            .replace(tzinfo=ZoneInfo(timezone))
                            .isoformat()
                        )
                    if instant(not_before) > instant(state["armed"][key]):
                        state["armed"][key] = not_before
        due = state["armed"].get(key)
        if due is not None and instant(due) <= at:
            effects.extend(
                {**deepcopy(effect), "event_key": key, "effective_at": due}
                for effect in event["effects"]
            )
            state["completed"].append(key)
    state["last_at"] = now
    return state, effects


def observable_effects(effects: list[dict]) -> list[dict]:
    """Only statements and explicit change notices are directly learner-visible.

    Release and availability effects are consumed by the evidence delivery engine;
    their private artifact identifiers must not be echoed in a public response.
    A change notice requests reconciliation, never silently rewrites audit scope.
    """
    return [
        {
            "kind": effect["operation"],
            "text": str(effect["value"]),
            "effective_at": effect["effective_at"],
            "event_key": effect["event_key"],
        }
        for effect in effects
        if effect["operation"] in {"statement", "scope_change", "record_change"}
    ]
