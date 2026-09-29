"""Learner-visible configuration; no scenario solutions or private seeds."""

from __future__ import annotations

import hashlib
import hmac
import json
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal
from pathlib import Path

from .store import DomainError, canonical


def selector_catalog() -> list[dict]:
    return json.loads((Path(__file__).parent / "resources/selectors.json").read_text())["selectors"]


def percent(value: object, name: str = "percentage") -> Decimal:
    if isinstance(value, bool):
        raise DomainError(f"{name} must be between 0 and 100")
    try:
        number = Decimal(str(value))
    except Exception as exc:
        raise DomainError(f"Invalid {name}") from exc
    if not number.is_finite() or not 0 <= number <= 100:
        raise DomainError(f"{name} must be between 0 and 100")
    return number


def rounded_count(frequency: object, eligible: int, *, positive_minimum: bool = False) -> int:
    if type(eligible) is not int or eligible < 0:
        raise DomainError("Eligible count must be a nonnegative integer")
    frequency = percent(frequency)
    result = int((frequency * eligible / 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    return min(eligible, max(1, result)) if positive_minimum and frequency and eligible else result


def allocate_incomplete(
    units: list[dict], overall: object, shares: dict[str, object], *, private_seed: bytes
) -> dict:
    """Deduplicate implementation units; freeze one primary issue per affected unit.

    Output is private authoring state. It is never a learner population or API
    projection. Stable option-ID tie breaking; normalization is an explicit action.
    """
    options = {o["id"] for s in selector_catalog() if s["id"] == "MM-02" for o in s["options"]}
    if not shares or not set(shares) <= options:
        raise DomainError("Incomplete-evidence shares require approved option IDs")
    values = {key: percent(value, "share") for key, value in shares.items()}
    if sum(values.values()) != 100:
        raise DomainError("Shares must total 100; use explicit Normalize to change them")
    keys = set()
    for unit in units:
        key = tuple(
            unit.get(field) for field in ("control_id", "boundary_id", "implementation_version")
        )
        if any(not isinstance(value, str) or not value for value in key):
            raise DomainError("Implementation unit requires control, boundary and version")
        keys.add(key)
    ordered = sorted(
        keys, key=lambda k: hmac.new(private_seed, canonical(k).encode(), hashlib.sha256).digest()
    )
    count = rounded_count(overall, len(ordered))
    exact = {key: value * count / 100 for key, value in values.items()}
    allocated = {
        key: int(value.to_integral_value(rounding=ROUND_FLOOR)) for key, value in exact.items()
    }
    remaining = count - sum(allocated.values())
    for key in sorted(exact, key=lambda k: (-(exact[k] - allocated[k]), k))[:remaining]:
        allocated[key] += 1
    assignments, cursor = [], 0
    for key, amount in sorted(allocated.items()):
        for unit in ordered[cursor : cursor + amount]:
            assignments.append(
                {
                    "control_id": unit[0],
                    "boundary_id": unit[1],
                    "implementation_version": unit[2],
                    "option_id": key,
                }
            )
        cursor += amount
    return {
        "eligible_count": len(keys),
        "affected_count": count,
        "allocation": allocated,
        "assignments": assignments,
    }


def normalize_shares(shares: dict[str, object]) -> dict[str, int]:
    values = {k: percent(v, "share") for k, v in shares.items()}
    total = sum(values.values())
    if not total:
        raise DomainError("Cannot normalize all-zero shares")
    exact = {k: v * 100 / total for k, v in values.items()}
    result = {k: int(v.to_integral_value(rounding=ROUND_FLOOR)) for k, v in exact.items()}
    for k in sorted(exact, key=lambda k: (-(exact[k] - result[k]), k))[
        : 100 - sum(result.values())
    ]:
        result[k] += 1
    return result


def validate_configuration(configuration: dict, mode: str) -> dict:
    if mode not in {"CLEAN", "MESSY"}:
        raise DomainError("Select Clean or Messy")
    selections = configuration.get("selections", [])
    if not isinstance(selections, list):
        raise DomainError("Selections must be an array")
    known = {s["id"]: {o["id"] for o in s["options"]} for s in selector_catalog()}
    seen = set()
    for selected in selections:
        parent, option = selected.get("selector_id"), selected.get("option_id")
        if parent not in known or (parent != "MM-08" and option not in known[parent]):
            raise DomainError("Unknown selector or option")
        if parent == "MM-08" and option not in {None, "", "MM-08"}:
            raise DomainError("Owner disagreements has no visible submenu")
        key = (parent, option)
        if key in seen:
            raise DomainError("An option may be configured only once")
        seen.add(key)
        if selected.get("authoring_mode", "STANDARD") not in {"STANDARD", "CUSTOM"}:
            raise DomainError("Select Standard or Custom per option")
        parameters = selected.get("parameters", {})
        if not isinstance(parameters, dict):
            raise DomainError("Parameters must be an object")
        for name in ("frequency", "severity", "intensity"):
            if name in parameters:
                percent(parameters[name], name)
        # MM03 symptom intensities are independent; six at100 is valid.
        if parent == "MM-03" and "overall" in parameters:
            raise DomainError("Client symptoms have individual intensities, no overall slider")
        allowed_parameters = {
            "MM-03": {"intensity"},
            "MM-08": {"frequency", "severity"},
            "MM-09": {"frequency", "severity"},
            "MM-10": {"count"},
            "MM-11": {"severity"},
            "MM-13": {"type"},
            "MM-14": {"type", "severity"},
            "MM-15": {"type"},
        }.get(parent, set())
        if set(parameters) - allowed_parameters:
            raise DomainError("Parameters are not approved for this scenario family")
        if "count" in parameters and (
            type(parameters["count"]) is not int or not 1 <= parameters["count"] <= 100
        ):
            raise DomainError("Change volume must be 1 to 100 actual events")
        if parent == "MM-13" and parameters.get("type", "FICTIONAL_RULEBOOK") not in {
            "FICTIONAL_RULEBOOK",
            "REAL_SOURCE",
        }:
            raise DomainError("Select real-source or fictional-rulebook authority")
    if mode == "CLEAN" and selections:
        raise DomainError("Clean mode cannot include injected problems")
    incomplete = configuration.get("incomplete_evidence")
    incomplete_options = {option for parent, option in seen if parent == "MM-02"}
    if incomplete_options and not incomplete:
        raise DomainError("Incomplete evidence requires an overall rate and selected-option shares")
    if incomplete:
        if set(incomplete.get("shares", {})) != incomplete_options:
            raise DomainError("Incomplete-evidence shares must match the enabled options exactly")
        percent(incomplete.get("overall"), "overall")
        allocate_incomplete(
            [], incomplete["overall"], incomplete.get("shares", {}), private_seed=b"validation"
        )
    return {"valid": True, "selected_count": len(selections), "warnings": []}
