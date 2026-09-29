"""Factual checks over explicit observable state; never professional conclusions."""

import json
from datetime import datetime
from decimal import Decimal

from . import populations
from .store import digest


def checks(state):
    results = []

    def add(identity, kind, status, inputs, detail):
        results.append(
            {
                "id": identity,
                "check": kind,
                "status": status,
                "input_digest": digest(inputs),
                "detail": detail,
                "hidden_sources_used": False,
                "professional_sufficiency": "NOT_ASSERTED",
            }
        )

    calculations = state.get("calculations", [])
    if len(calculations) > 100:
        add(
            "CALCULATIONS_OMITTED",
            "BOUNDED_CHECK_LIMIT",
            "NOT_OBSERVABLE",
            {"omitted": len(calculations) - 100},
            "Only first100 explicit calculations rechecked.",
        )
    calculations = calculations[:100]
    if not calculations:
        add(
            "ARITHMETIC",
            "EXPLICIT_CALCULATOR_REPERFORMANCE",
            "NOT_OBSERVABLE",
            {},
            "No retained structured calculation. Prose amounts are not inferred.",
        )
    for calculation in calculations:
        p, original = calculation.get("inputs", {}), calculation.get("result", {})
        try:
            if original.get("version") != "sampling-v1":
                raise ValueError("Unrecognized or external calculation version")
            if p.get("method") == "zero_deviation_attribute":
                confidence = Decimal(str(p["confidence"]))
                population_size = Decimal(str(p["population_size"]))
                if (
                    not confidence.is_finite()
                    or type(p["population_size"]) is bool
                    or not population_size.is_finite()
                    or population_size != population_size.to_integral_value()
                ):
                    raise ValueError("Invalid explicit numeric input")
                expected = populations.attribute_size(
                    1 - confidence, p["tolerable_rate"], population_size=int(p["population_size"])
                )
            elif p.get("method") == "monetary":
                expected = populations.monetary_size(
                    p["total_book_value"],
                    p["tolerable_misstatement"],
                    p["alpha"],
                    p.get("expected_misstatement", "0"),
                )
            else:
                raise ValueError("No supported explicit arithmetic method")
            size = original.get("size")
            if type(size) is not int:
                raise ValueError("No explicit integer result")
            add(
                calculation["id"],
                "EXPLICIT_CALCULATOR_REPERFORMANCE",
                "SUPPORTED" if size == expected["size"] else "CONTRADICTED",
                calculation,
                {
                    "recorded_size": size,
                    "recomputed_size": expected["size"],
                    "method": expected["method"],
                    "limitation": (
                        "Formula consistency only; input assumptions and audit sufficiency are "
                        "not established."
                    ),
                },
            )
        except (ValueError, TypeError, KeyError, ArithmeticError):
            add(
                calculation.get("id", "CALC"),
                "EXPLICIT_CALCULATOR_REPERFORMANCE",
                "NOT_OBSERVABLE",
                calculation,
                "Missing, unsupported or invalid structured calculation inputs.",
            )
    available = {
        m["id"]
        for m in state.get("artifacts", [])
        if m.get("status") == "AVAILABLE" and m.get("audience", "LEARNER") == "LEARNER"
    }
    population_map = {p["id"]: p for p in state.get("populations", [])}
    if not population_map:
        add(
            "POPULATIONS",
            "SUPPLIED_POPULATION_COMPARISON",
            "NOT_OBSERVABLE",
            {},
            "No supplied population is retained.",
        )
    for population in population_map.values():
        rows = population.get("rows")
        if not isinstance(rows, list) or len(rows) > 100000:
            add(
                population["id"],
                "SUPPLIED_POPULATION_COMPARISON",
                "NOT_OBSERVABLE",
                {"id": population["id"]},
                "Missing or excessive explicit rows.",
            )
            continue
        ids = [row.get("id") for row in rows if isinstance(row, dict)]
        if len(ids) != len(rows) or any(not isinstance(i, str) for i in ids):
            add(
                population["id"],
                "SUPPLIED_POPULATION_COMPARISON",
                "NOT_OBSERVABLE",
                rows,
                "Row identities are not explicit strings.",
            )
            continue
        count = population.get("count")
        add(
            population["id"],
            "RECORDED_COUNT_EQUALS_SUPPLIED_ROWS",
            "NOT_OBSERVABLE"
            if type(count) is not int
            else ("SUPPORTED" if count == len(rows) else "CONTRADICTED"),
            {"count": count, "ids": ids},
            {
                "recorded_count": count,
                "supplied_count": len(rows),
                "completeness": "UNIVERSE_COMPLETENESS_NOT_ASSERTED",
            },
        )
        add(
            population["id"],
            "SUPPLIED_IDENTIFIERS_DISTINCT",
            "SUPPORTED" if len(ids) == len(set(ids)) else "CONTRADICTED",
            ids,
            "Duplicate identity check; no hidden census comparison.",
        )
        frozen = population.get("immutable", {}).get("records_json")
        if isinstance(frozen, (list, tuple)):
            try:
                retained = [json.loads(row) for row in frozen]
                add(
                    population["id"],
                    "WORKING_ROWS_EQUAL_RETAINED_VERSION",
                    "SUPPORTED" if rows == retained else "CONTRADICTED",
                    {"working": rows, "retained": retained},
                    (
                        "Only this exact population version compared; a valid successor is "
                        "independent."
                    ),
                )
            except (ValueError, TypeError):
                add(
                    population["id"],
                    "WORKING_ROWS_EQUAL_RETAINED_VERSION",
                    "NOT_OBSERVABLE",
                    {"id": population["id"]},
                    "Unparseable retained structured rows.",
                )
        else:
            add(
                population["id"],
                "WORKING_ROWS_EQUAL_RETAINED_VERSION",
                "NOT_OBSERVABLE",
                {"id": population["id"]},
                "No immutable source-version rows retained.",
            )
    for selection in state.get("selections", []):
        pop = population_map.get(selection.get("population_id"))
        immutable = selection.get("immutable", {})
        if not pop or not immutable:
            add(
                selection["id"],
                "SELECTION_VERSION_AND_SETS",
                "NOT_OBSERVABLE",
                selection,
                "Missing explicit selection version or supplied population.",
            )
            continue
        selected, targeted = selection.get("selected_ids", []), selection.get("targeted_ids", [])
        if any(not isinstance(i, str) for i in selected + targeted):
            add(
                selection["id"],
                "SELECTION_VERSION_AND_SETS",
                "NOT_OBSERVABLE",
                selection,
                "Identifiers are not explicit strings.",
            )
            continue
        supplied = {r["id"] for r in pop.get("rows", [])}
        mismatch = (
            immutable.get("population_version") != pop.get("version")
            or len(selected) != len(set(selected))
            or len(targeted) != len(set(targeted))
            or bool(set(selected) & set(targeted))
            or not set(selected + targeted) <= supplied
        )
        add(
            selection["id"],
            "SELECTION_VERSION_AND_SETS",
            "CONTRADICTED" if mismatch else "SUPPORTED",
            {
                "selection": selection,
                "population_version": pop.get("version"),
                "supplied_ids": sorted(supplied),
            },
            (
                "Exact version, distinct sampled/targeted sets and supplied-ID "
                "membership only; sampling quality not asserted."
            ),
        )
    epochs = state.get("temporal", {})
    found = False
    for epoch, temporal in epochs.items():
        versions = {v["id"]: v for v in temporal.get("versions", [])}
        for work in temporal.get("work", []):
            found = True
            try:
                version = versions[work["implementation_id"]]

                def instant(value):
                    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    if result.tzinfo is None:
                        raise ValueError("Explicit offset required")
                    return result

                start, end = map(instant, (work["covered"]["start"], work["covered"]["end"]))
                effective_start, effective_end = map(
                    instant, (version["effective"]["start"], version["effective"]["end"])
                )
                future = instant(work["performed_at"]) > instant(state["simulated_at"])
                valid = effective_start <= start < end <= effective_end and not future
                add(
                    work["id"],
                    "RECORDED_COVERAGE_INTERVAL_LOGIC",
                    "SUPPORTED" if valid else "CONTRADICTED",
                    {
                        "epoch": epoch,
                        "work": work,
                        "implementation": version,
                        "clock": state["simulated_at"],
                    },
                    (
                        "Compare explicit offset-aware half-open intervals and performed date "
                        "to recorded clock. No assumption that all audit support must originate "
                        "within the audit period."
                    ),
                )
                evidence = work.get("evidence_ids", [])
                add(
                    work["id"],
                    "COVERAGE_HAS_OBSERVABLE_REFERENCES",
                    "SUPPORTED" if evidence and set(evidence) <= available else "NOT_OBSERVABLE",
                    evidence,
                    (
                        "Absent/quarantined/unreleased references do not by themselves prove "
                        "control failure."
                    ),
                )
            except (KeyError, TypeError, ValueError):
                add(
                    work.get("id", "COVERAGE"),
                    "RECORDED_COVERAGE_INTERVAL_LOGIC",
                    "NOT_OBSERVABLE",
                    work,
                    "Missing or malformed explicit dates/version; no inferred chronology.",
                )
    if not found:
        add(
            "COVERAGE",
            "RECORDED_COVERAGE_INTERVAL_LOGIC",
            "NOT_OBSERVABLE",
            {},
            "No structured dated procedure records retained.",
        )
    return results
