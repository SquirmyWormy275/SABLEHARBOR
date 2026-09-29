"""Immutable supplied populations and selections; never hidden scenario truth.

All calculators are mathematical training helpers, not professional sample-size
recommendations. Selection does not establish population reliability or test success.
Public fixtures must use neutral inputs rather than private scenario answer keys.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass
from decimal import ROUND_CEILING, Decimal, localcontext
from fractions import Fraction
from functools import cached_property
from typing import Any

from enterprise.ccf.operations.testing import instant

STATUSES = {
    "RECEIVED",
    "PROVISIONAL",
    "UNDER_RELIABILITY_EVALUATION",
    "READY_FOR_PURPOSE",
    "SUPERSEDED",
    "DISPUTED",
}
METHODS = {"MANUAL", "SIMPLE_RANDOM", "SYSTEMATIC", "STRATIFIED", "ENTIRE", "MONETARY_SYSTEMATIC"}


def encoded(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Nonempty text required")
    return value


def unique(values) -> tuple[str, ...]:
    if isinstance(values, str):
        raise ValueError("Identifier collection required")
    values = tuple(text(v) for v in values)
    if len(values) != len(set(values)):
        raise ValueError("Duplicate identifiers")
    return values


def integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError("Invalid integer")
    return value


@dataclass(frozen=True)
class Population:
    id: str
    version: int
    records_json: tuple[str, ...]
    scope_json: str
    source_json: str
    status: str = "PROVISIONAL"
    parent_population_digest: str | None = None
    parent_selection_digest: str | None = None
    parent_key: str | None = None
    predecessor_digest: str | None = None
    revision_rationale: str | None = None

    def __post_init__(self):
        text(self.id)
        integer(self.version, 1)
        if type(self.records_json) is not tuple or not all(
            isinstance(r, str) for r in self.records_json
        ):
            raise ValueError("Immutable serialized records required")
        unique(r["id"] for r in self.rows)
        if self.status not in STATUSES:
            raise ValueError("Invalid reliability status")
        scope, source = self.scope, self.source
        for field in ("boundary_id", "unit", "timezone", "period_start", "period_end"):
            text(scope.get(field))
        if instant(scope["period_start"]) > instant(scope["period_end"]):
            raise ValueError("Invalid population period")
        for field in ("source_id", "query", "original_sha256", "completeness_representation"):
            text(source.get(field))
        if len(source["original_sha256"]) != 64 or any(
            c not in "0123456789abcdef" for c in source["original_sha256"]
        ):
            raise ValueError("Original artifact SHA256 required")
        exclusions = unique(source.get("excluded_ids", []))
        if not set(exclusions) <= set(self.ids):
            raise ValueError("Excluded IDs must exist in supplied population")
        if exclusions:
            text(source.get("exclusion_rationale"))
        if self.status == "READY_FOR_PURPOSE":
            for field in (
                "reliability_purpose",
                "reliability_rationale",
                "reliability_actor",
                "observable_source_ref",
            ):
                text(source.get(field))
        if any(
            (self.parent_population_digest, self.parent_selection_digest, self.parent_key)
        ) and not all(
            (self.parent_population_digest, self.parent_selection_digest, self.parent_key)
        ):
            raise ValueError("Complete parent lineage required")

    @property
    def rows(self):
        return tuple(json.loads(row) for row in self.records_json)

    @property
    def scope(self):
        return json.loads(self.scope_json)

    @property
    def source(self):
        return json.loads(self.source_json)

    @cached_property
    def sha256(self):
        return digest(asdict(self))

    @cached_property
    def ids(self):
        return tuple(row["id"] for row in self.rows)


@dataclass(frozen=True)
class Selection:
    id: str
    population_id: str
    population_version: int
    population_digest: str
    selected_ids: tuple[str, ...]
    targeted_ids: tuple[str, ...]
    method: str
    purpose: str
    rationale: str
    parameters_json: str
    population_status: str
    parent_selection_digest: str | None = None
    predecessor_digest: str | None = None

    def __post_init__(self):
        for field in (
            self.id,
            self.population_id,
            self.purpose,
            self.rationale,
            self.population_digest,
        ):
            text(field)
        integer(self.population_version, 1)
        if type(self.selected_ids) is not tuple or type(self.targeted_ids) is not tuple:
            raise ValueError("Immutable selection IDs required")
        unique(self.selected_ids)
        unique(self.targeted_ids)
        if set(self.selected_ids) & set(self.targeted_ids):
            raise ValueError("Targeted and sampled items must remain separate")
        if self.method not in METHODS | {"REVISED"} or self.population_status not in STATUSES:
            raise ValueError("Invalid selection metadata")
        json.loads(self.parameters_json)

    @cached_property
    def sha256(self):
        return digest(asdict(self))

    @property
    def parameters(self):
        return json.loads(self.parameters_json)

    @property
    def all_ids(self):
        return self.selected_ids + self.targeted_ids

    @property
    def provisional(self):
        return (
            self.parameters.get("reliability_for_this_purpose", self.population_status)
            != "READY_FOR_PURPOSE"
        )


def validate_selection(population: Population, selection: Selection):
    if (selection.population_id, selection.population_version, selection.population_digest) != (
        population.id,
        population.version,
        population.sha256,
    ):
        raise ValueError("Selection references a different population version or content")
    eligible = set(population.ids) - set(population.source.get("excluded_ids", []))
    if not set(selection.all_ids) <= eligible:
        raise ValueError("Selected IDs are absent from supplied population")
    if (
        selection.population_status != population.status
        or selection.parent_selection_digest != population.parent_selection_digest
    ):
        raise ValueError("Selection reliability or parent metadata differs")
    return True


def create_population(
    id,
    version,
    rows,
    *,
    scope,
    source,
    parent_population=None,
    parent_selection=None,
    parent_key=None,
    status="PROVISIONAL",
) -> Population:
    if any(v is not None for v in (parent_population, parent_selection, parent_key)):
        if any(v is None for v in (parent_population, parent_selection, parent_key)):
            raise ValueError("Parent population, selection and foreign key required together")
        validate_selection(parent_population, parent_selection)
        parent_ids = set(parent_selection.all_ids)
        rows = tuple(rows)
        if any(row.get(parent_key) not in parent_ids for row in rows):
            raise ValueError("Child row lies outside parent selection")
        ps = parent_population.scope
        if scope["boundary_id"] != ps["boundary_id"] or not instant(ps["period_start"]) <= instant(
            scope["period_start"]
        ) <= instant(scope["period_end"]) <= instant(ps["period_end"]):
            raise ValueError("Child scope exceeds parent scope")
    return Population(
        id,
        version,
        tuple(encoded(r) for r in rows),
        encoded(scope),
        encoded(source),
        status,
        parent_population.sha256 if parent_population else None,
        parent_selection.sha256 if parent_selection else None,
        parent_key,
    )


def revise_population(previous: Population, rows, *, source, rationale) -> Population:
    """New version invalidates prior selections without altering their original records."""
    text(rationale)
    rows = tuple(rows)
    if previous.parent_key:
        allowed = {r[previous.parent_key] for r in previous.rows}
        if any(r.get(previous.parent_key) not in allowed for r in rows):
            raise ValueError("Expanded child parent set requires a new explicit parent request")
    return Population(
        previous.id,
        previous.version + 1,
        tuple(encoded(r) for r in rows),
        previous.scope_json,
        encoded(source),
        "PROVISIONAL",
        previous.parent_population_digest,
        previous.parent_selection_digest,
        previous.parent_key,
        previous.sha256,
        rationale,
    )


def select(
    population: Population,
    *,
    selection_id,
    method,
    purpose,
    rationale,
    seed=None,
    size=None,
    ids=(),
    strata=None,
    targeted_ids=(),
    amount_field=None,
) -> Selection:
    text(purpose)
    text(rationale)
    if method not in METHODS:
        raise ValueError("Unsupported selection method")
    target = unique(targeted_ids)
    all_ids = tuple(
        i for i in population.ids if i not in set(population.source.get("excluded_ids", []))
    )
    if not set(target) <= set(all_ids):
        raise ValueError("Targeted ID absent from population")
    eligible = tuple(x for x in all_ids if x not in set(target))
    parameters = dict(
        seed=seed,
        size=size,
        strata=strata,
        amount_field=amount_field,
        excluded_targeted_ids=target,
        assurance="NOT_ASSERTED",
        calculator_version="sampling-v1",
    )
    if method in {"SIMPLE_RANDOM", "SYSTEMATIC", "STRATIFIED", "MONETARY_SYSTEMATIC"}:
        if not isinstance(seed, str) or not seed:
            raise ValueError("Explicit reproducibility seed required")
    rng = random.Random(seed)
    if method == "MANUAL":
        chosen = unique(ids)
        if not set(chosen) <= set(eligible):
            raise ValueError("Manual IDs missing or already targeted")
        parameters["representative_claim"] = False
    elif method == "ENTIRE":
        chosen = eligible
    elif method == "STRATIFIED":
        if not isinstance(strata, dict) or not strata:
            raise ValueError("Explicit disjoint stratum IDs and sizes required")
        covered, selected = set(), []
        for name, stratum in sorted(strata.items()):
            text(name)
            members = unique(stratum["ids"])
            count = integer(stratum["size"])
            if count > len(members) or covered & set(members) or not set(members) <= set(eligible):
                raise ValueError("Invalid, overlapping or oversized stratum")
            covered.update(members)
            local = random.Random(digest([seed, name]))
            selected.extend(local.sample(list(members), count))
        if covered != set(eligible):
            raise ValueError("Strata must partition the eligible supplied population")
        chosen = tuple(selected)
    elif method == "MONETARY_SYSTEMATIC":
        count = integer(size, 1)
        if count > 100_000:
            raise ValueError("Monetary draws exceed bounded selection limit")
        text(amount_field)
        rows = {r["id"]: r for r in population.rows}
        amounts = {rid: _decimal(rows[rid][amount_field]) for rid in eligible}
        if any(v <= 0 for v in amounts.values()) or not amounts:
            raise ValueError(
                "Monetary systematic selection requires positive eligible balances; "
                "zero/negative items need explicit separate treatment"
            )
        total = sum(amounts.values(), Decimal(0))
        interval = total / count
        start = interval * Decimal(rng.getrandbits(53)) / Decimal(2**53)
        hits, cumulative, point = [], Decimal(0), start
        for rid in eligible:
            cumulative += amounts[rid]
            while len(hits) < count and point < cumulative:
                hits.append(rid)
                point = start + interval * len(hits)
        if len(hits) != count:
            raise ValueError("Monetary point allocation failed")
        chosen = tuple(dict.fromkeys(hits))
        parameters.update(
            draw_ids=hits,
            monetary_interval=str(interval),
            monetary_start=str(start),
            unique_items=len(chosen),
            limitations=(
                "PPS systematic selection only; duplicate monetary hits retained. No projected "
                "misstatement or combined assurance evaluation."
            ),
        )
    else:
        count = integer(size)
        if count > len(eligible):
            raise ValueError(
                "Requested sample exceeds eligible population; no assurance-preserving truncation"
            )
        if method == "SIMPLE_RANDOM":
            chosen = tuple(rng.sample(list(eligible), count))
        elif count:
            # Rational interval avoids biased truncation for non-divisible populations.
            offset = Fraction(rng.getrandbits(53), 2**53)
            positions = tuple(int((offset + k) * len(eligible) / count) for k in range(count))
            chosen = tuple(eligible[i] for i in positions)
            parameters.update(
                random_start=str(offset),
                positions=positions,
                limitations="Population ordering and periodicity require evaluation",
            )
        else:
            chosen = ()
    if (
        population.status == "READY_FOR_PURPOSE"
        and purpose != population.source["reliability_purpose"]
    ):
        status = "PROVISIONAL"
    else:
        status = population.status
    # A purpose change must not silently inherit reliability; store actual input status
    # and mark the purpose assessment separately so lineage validation remains exact.
    parameters["reliability_for_this_purpose"] = status
    result = Selection(
        selection_id,
        population.id,
        population.version,
        population.sha256,
        chosen,
        target,
        method,
        purpose,
        rationale,
        encoded(parameters),
        population.status,
        population.parent_selection_digest,
    )
    validate_selection(population, result)
    return result


def revise_selection(
    population: Population,
    previous: Selection,
    *,
    selection_id,
    add_ids=(),
    remove_ids=(),
    rationale,
    methodology_authorizes_replacement=False,
) -> Selection:
    validate_selection(population, previous)
    text(rationale)
    additions, removals = unique(add_ids), unique(remove_ids)
    if removals and not methodology_authorizes_replacement:
        raise ValueError("Replacement requires explicit methodology authorization and reason")
    if not set(removals) <= set(previous.selected_ids) or set(additions) & set(previous.all_ids):
        raise ValueError("Invalid removal or already selected addition")
    if not set(additions) <= set(population.ids) - set(population.source.get("excluded_ids", [])):
        raise ValueError("New selection IDs missing")
    chosen = tuple(i for i in previous.selected_ids if i not in removals) + additions
    result = Selection(
        selection_id,
        population.id,
        population.version,
        population.sha256,
        chosen,
        previous.targeted_ids,
        "REVISED",
        previous.purpose,
        rationale,
        encoded(
            dict(
                added_ids=additions,
                removed_ids=removals,
                prior_method=previous.method,
                representativeness="REQUIRES_METHODOLOGY_REASSESSMENT",
                assurance="NOT_ASSERTED",
                reliability_for_this_purpose=previous.parameters.get(
                    "reliability_for_this_purpose", previous.population_status
                ),
            )
        ),
        population.status,
        population.parent_selection_digest,
        previous.sha256,
    )
    validate_selection(population, result)
    return result


def response_manifest(
    population: Population, selection: Selection, dispositions: dict[str, dict]
) -> dict:
    validate_selection(population, selection)
    if set(dispositions) != set(selection.all_ids):
        raise ValueError("Every selected item requires an explicit disposition")
    allowed = {"DELIVERED", "PARTIAL", "REFUSED", "UNAVAILABLE", "AWAITING_CLARIFICATION"}
    for value in dispositions.values():
        if value["status"] not in allowed:
            raise ValueError("Unknown item disposition")
        text(value["rationale"])
        if value["status"] == "DELIVERED" and not value.get("artifact_ids"):
            raise ValueError("Delivery must reference actual retained artifacts")
    return dict(
        population_digest=population.sha256,
        selection_digest=selection.sha256,
        items=json.loads(encoded(dispositions)),
        test_conclusion="NOT_ASSERTED",
    )


def _decimal(value):
    if isinstance(value, bool):
        raise ValueError("Numeric value required")
    try:
        number = Decimal(str(value))
    except Exception:
        raise ValueError("Numeric value required") from None
    if not number.is_finite():
        raise ValueError("Finite value required")
    return number


def _rates(alpha, tolerable):
    a, t = _decimal(alpha), _decimal(tolerable)
    if not 0 < a < 1 or not 0 < t < 1:
        raise ValueError("Risk and tolerable rate must lie strictly between zero and one")
    return a, t


def attribute_size(alpha, tolerable_rate, population_size=None):
    """Zero-observed-deviation acceptance model, not a general audit sample table.

    Finite case uses the exact hypergeometric probability of missing D deviations,
    where D=ceil(N*tolerable_rate); find the least n with P(zero)<=alpha.
    """
    a, t = _rates(alpha, tolerable_rate)
    if population_size is None:
        with localcontext() as ctx:
            ctx.prec = max(
                60,
                len(a.as_tuple().digits)
                + abs(a.adjusted())
                + len(t.as_tuple().digits)
                + abs(t.adjusted())
                + 10,
            )
            count = int((a.ln() / (1 - t).ln()).to_integral_value(rounding=ROUND_CEILING))
        if count > 10_000_000:
            raise ValueError("Required sample exceeds bounded calculator range")
        while count and (1 - t) ** (count - 1) <= a:
            count -= 1
        while (1 - t) ** count > a:
            count += 1
        return dict(
            size=count,
            method="ZERO_DEVIATION_BINOMIAL",
            miss_probability=str((1 - t) ** count),
            alpha=str(a),
            tolerable_rate=str(t),
            assumptions=(
                "Independent trials with fixed deviation probability; zero deviations expected "
                "and accepted. Not an audit-methodology sufficiency conclusion."
            ),
            version="sampling-v1",
        )
    n = integer(population_size, 1)
    if n > 100_000:
        raise ValueError("Exact finite calculator limited to 100000 units")
    deviations = int((t * n).to_integral_value(rounding=ROUND_CEILING))
    risk = Fraction(a)

    def probability(sample):
        return (
            Fraction(math.comb(n - deviations, sample), math.comb(n, sample))
            if sample <= n - deviations
            else Fraction(0)
        )

    low, high = 0, n
    while low < high:
        mid = (low + high) // 2
        if probability(mid) <= risk:
            high = mid
        else:
            low = mid + 1
    p = probability(low)
    return dict(
        size=low,
        method="ZERO_DEVIATION_HYPERGEOMETRIC",
        population_size=n,
        deviation_threshold=deviations,
        miss_probability=float(p),
        alpha=str(a),
        tolerable_rate=str(t),
        assumptions=(
            "Simple random without replacement from complete finite population; zero "
            "accepted deviations, integer threshold ceil(N*t). Does not establish "
            "population completeness or multistage assurance."
        ),
        version="sampling-v1",
    )


def monetary_size(total_book_value, tolerable_misstatement, alpha, expected_misstatement="0"):
    """Zero-error Poisson planning approximation; positive balances only.

    n=ceil(-ln(alpha)*book/tolerable). This is a mathematical PPS planning helper,
    not a validated firm MUS evaluation methodology. Nonzero expected errors need
    an externally validated method and are deliberately unavailable here.
    """
    book, tolerance, risk, expected = map(
        _decimal, (total_book_value, tolerable_misstatement, alpha, expected_misstatement)
    )
    if book <= 0 or not 0 < tolerance < book or not 0 < risk < 1:
        raise ValueError("Positive book, lower positive tolerance and valid risk required")
    if expected != 0:
        raise ValueError(
            "Nonzero expected-misstatement planning requires a validated external methodology"
        )
    count = int((-risk.ln() * book / tolerance).to_integral_value(rounding=ROUND_CEILING))
    return dict(
        size=count,
        method="ZERO_ERROR_POISSON_MONETARY_APPROXIMATION",
        risk=str(risk),
        book_value=str(book),
        tolerable_misstatement=str(tolerance),
        assumptions=(
            "Positive monetary units; zero expected errors; Poisson approximation for "
            "planning. No zero/negative balances, error projection, upper-error-limit "
            "evaluation or professional assurance claim."
        ),
        professional_validation="UNVALIDATED",
        version="sampling-v1",
    )
