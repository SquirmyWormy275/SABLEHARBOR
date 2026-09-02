import json
from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from random import Random

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sable_harbor.accounting.ledger import post_entry
from sable_harbor.accounting.models import (
    Account,
    AccountingBook,
    BusinessParty,
    Contract,
    EnvironmentalObligation,
    FactState,
    FiscalPeriod,
    FixedAsset,
    FreightMovement,
    InventoryLot,
    JournalEntry,
    JournalLine,
    LegalEntity,
    ProductionRecord,
    ScenarioValue,
    Site,
    Worker,
)
from sable_harbor.commercial.contract_to_cash import (
    create_foundry_contract_flow,
    receive_cash,
    recognize_month,
)
from sable_harbor.commercial.engagements import deliver_and_bill_engagement
from sable_harbor.commercial.models import PerformanceObligation
from sable_harbor.config.assumptions import load_assumptions
from sable_harbor.core.ids import stable_id
from sable_harbor.logistics.flows import operate_waybill
from sable_harbor.mining.flows import produce_concentrate, ship_and_collect
from sable_harbor.operations.flows import (
    depreciate_asset,
    draw_debt_and_accrue_interest,
    procure_and_pay_asset,
    run_payroll,
)
from sable_harbor.provenance.models import GenerationRun
from sable_harbor.provenance.service import (
    GENERATION_RUN_SESSION_KEY,
    complete_generation_run,
    record_generation_run,
)
from sable_harbor.recovery.flows import execute_recovery_run
from sable_harbor.research.flows import run_atlas_evaluation, run_willow_experiment

D = Decimal


def _scenario_document() -> dict[str, object]:
    path = Path("config/finance/scenarios/operating.yml")
    return dict(yaml.safe_load(path.read_text()))


def scenario_multipliers(scenario: str, entity_code: str = "SHI") -> tuple[D, D]:
    document = _scenario_document()
    scenarios = document["scenarios"]
    assert isinstance(scenarios, dict)
    if scenario not in scenarios:
        raise ValueError(f"Unknown scenario {scenario!r}")
    selected = scenarios[scenario]
    assert isinstance(selected, dict)
    definitions = document["driver_definitions"]
    assert isinstance(definitions, dict)
    entity_definition = definitions[entity_code]
    assert isinstance(entity_definition, dict)
    values_by_entity = selected.get("values", {})
    assert isinstance(values_by_entity, dict)
    values = values_by_entity.get(entity_code, {})
    assert isinstance(values, dict)

    def product(kind: str) -> D:
        result = D(1)
        drivers = entity_definition[kind]
        assert isinstance(drivers, list)
        for driver in drivers:
            result *= D(str(values.get(driver, "1.00")))
        return result

    return product("revenue"), product("cost")


def _persist_scenario_drivers(
    session: Session, run: GenerationRun, scenario_code: str
) -> None:
    document = _scenario_document()
    scenarios = document["scenarios"]
    definitions = document["driver_definitions"]
    assert isinstance(scenarios, dict) and isinstance(definitions, dict)
    selected = scenarios[scenario_code]
    assert isinstance(selected, dict)
    values_by_entity = selected.get("values", {})
    assert isinstance(values_by_entity, dict)
    for entity_code, kinds in definitions.items():
        assert isinstance(kinds, dict)
        entity_values = values_by_entity.get(entity_code, {})
        assert isinstance(entity_values, dict)
        for kind, drivers in kinds.items():
            assert isinstance(drivers, list)
            for driver in drivers:
                record_id = stable_id(
                    "scenario_value", f"{run.id}:driver:{entity_code}:{driver}"
                )
                if session.get(ScenarioValue, record_id) is not None:
                    continue
                metadata = {
                    "owner": document["owner"],
                    "rationale": selected["description"],
                    "sensitivity": kind,
                    "source": document["provenance"],
                }
                session.add(
                    ScenarioValue(
                        id=record_id,
                        generation_run_id=run.id,
                        scenario_code=scenario_code,
                        metric_code=f"driver_{driver}",
                        entity_code=str(entity_code),
                        period_code=str(document["effective_period"]),
                        amount=D(str(entity_values.get(driver, "1.00"))),
                        unit="multiplier",
                        fact_state=FactState.SCENARIO_INPUT,
                        provenance=json.dumps(metadata, sort_keys=True),
                    )
                )


@dataclass(frozen=True)
class EntityPlan:
    code: str
    name: str
    revenue: D
    operating_cost: D
    employees: int
    segment: str
    site: str


def entity_plans() -> tuple[EntityPlan, ...]:
    assumptions = {
        assumption.id: D(str(assumption.value))
        for assumption in load_assumptions(Path("config/finance/assumptions"))
        if assumption.id.startswith("FIN-Q-")
    }
    return (
        EntityPlan(
            "SHI",
            "Sable Harbor, Inc. (model parent)",
            assumptions["FIN-Q-001"],
            assumptions["FIN-Q-002"],
            450,
            "CORE",
            "SAC",
        ),
        EntityPlan(
            "RWH",
            "Red Wash Operations LLC (scenario entity)",
            assumptions["FIN-Q-003"],
            assumptions["FIN-Q-004"],
            126,
            "PALE_SUN",
            "RED_WASH",
        ),
        EntityPlan(
            "ARU",
            "American Resource Utility, Inc. (scenario entity)",
            assumptions["FIN-Q-005"],
            assumptions["FIN-Q-006"],
            132,
            "ARU_BST",
            "ARU_HUB",
        ),
    )


def _generate_causal_month(
    session: Session,
    *,
    entity_code: str,
    entity_id: str,
    site_id: str | None,
    book_id: str,
    period_id: str,
    period_end: date,
    key: str,
    revenue: D,
    cost: D,
) -> tuple[D, D]:
    """Materialize a causal forecast subledger slice and return GL amounts replaced."""
    causal_revenue = (revenue * D("0.10")).quantize(D("0.01"))
    causal_cost = (cost * D("0.10")).quantize(D("0.01"))
    if entity_code == "SHI":
        contract, invoice = create_foundry_contract_flow(
            session,
            book_id=book_id,
            entity_id=entity_id,
            period_id=period_id,
            natural_key=f"{key}:FOUNDRY",
            invoice_date=period_end,
            annual_value=causal_revenue,
        )
        obligation = session.scalar(
            select(PerformanceObligation).where(
                PerformanceObligation.contract_id == contract.id
            )
        )
        if obligation is None:
            raise ValueError("Generated Foundry contract is missing its performance obligation")
        recognize_month(
            session,
            obligation=obligation,
            book_id=book_id,
            period_id=period_id,
            recognition_date=period_end,
            amount=causal_revenue,
        )
        receive_cash(
            session,
            invoice=invoice,
            book_id=book_id,
            period_id=period_id,
            receipt_date=period_end,
        )
        worker_key = stable_id("forecast_worker", key)
        worker = Worker(
            id=worker_key,
            worker_number=f"FC-{period_end:%Y%m}",
            worker_type="EMPLOYEE",
            entity_id=entity_id,
            segment_code="CORE",
            function_code="FORECAST_COHORT",
            annual_cost=cost,
            starts_on=period_end.replace(day=1),
            fact_state=FactState.SYNTHETIC_INSTANCE,
        )
        session.add(worker)
        session.flush()
        payroll_gross = (causal_cost * D("0.04")).quantize(D("0.01"))
        payroll_employer = (causal_cost * D("0.01")).quantize(D("0.01"))
        run_payroll(
            session,
            entity_id=entity_id,
            book_id=book_id,
            period_id=period_id,
            worker=worker,
            pay_date=period_end,
            gross_pay=payroll_gross,
            employer_cost=payroll_employer,
        )
        compact_key = stable_id("forecast_capital", key).replace("-", "")[:20]
        _, _, asset = procure_and_pay_asset(
            session,
            entity_id=entity_id,
            book_id=book_id,
            period_id=period_id,
            key=compact_key,
            event_date=period_end,
            amount=(cost * D("0.01")).quantize(D("0.01")),
        )
        depreciation = depreciate_asset(
            session,
            asset=asset,
            book_id=book_id,
            period_id=period_id,
            depreciation_date=period_end,
        )
        draw_debt_and_accrue_interest(
            session,
            entity_id=entity_id,
            book_id=book_id,
            period_id=period_id,
            key=compact_key,
            event_date=period_end,
            principal=D("100000"),
            annual_rate=D("0.08"),
        )
        service_revenue = (revenue * D("0.01")).quantize(D("0.01"))
        service_cost = (cost * D("0.01")).quantize(D("0.01"))
        deliver_and_bill_engagement(
            session,
            contract=contract,
            worker=worker,
            book_id=book_id,
            period_id=period_id,
            key=f"{compact_key}:ADV",
            work_date=period_end,
            hours=D("100"),
            bill_rate=service_revenue / D("100"),
            cost_rate=service_cost / D("100"),
        )
        willow_cost = (cost * D("0.005")).quantize(D("0.01"))
        run_willow_experiment(
            session,
            entity_id=entity_id,
            book_id=book_id,
            period_id=period_id,
            key=f"{compact_key}:WIL",
            experiment_date=period_end,
            question="Can the reversible forecast experiment improve field decisions?",
            belief="Controlled synthetic evidence can inform a later operating gate.",
            budget=willow_cost,
            actual_cost=willow_cost,
            observation="Synthetic forecast observation; no canon change.",
            gate_decision="CONTINUE",
        )
        atlas_cost = (cost * D("0.005")).quantize(D("0.01"))
        atlas_fee = (revenue * D("0.005")).quantize(D("0.01"))
        run_atlas_evaluation(
            session,
            entity_id=entity_id,
            book_id=book_id,
            period_id=period_id,
            key=f"{compact_key}:ATL",
            evaluation_date=period_end,
            model_version="scenario-v0.1",
            investigation_question="Forecast validation under explicit scenario drivers",
            compute_cost=atlas_cost * D("0.60"),
            validation_cost=atlas_cost * D("0.40"),
            customer_fee=atlas_fee,
        )
        cradle_revenue = (revenue * D("0.005")).quantize(D("0.01"))
        recovery_run = execute_recovery_run(
            session,
            entity_id=entity_id,
            book_id=book_id,
            period_id=period_id,
            key=f"{compact_key}:CRA",
            run_date=period_end,
            feed_tons=D("100"),
            grade_fraction=D("0.001"),
            recovery_fraction=D("0.80"),
            price_per_unit=cradle_revenue / D("160"),
            host_share=D("0.20"),
            operating_cost=(cost * D("0.005")).quantize(D("0.01")),
        )
        replaced_revenue = (
            causal_revenue + service_revenue + atlas_fee + recovery_run.gross_sale
        )
        replaced_cost = (
            payroll_gross
            + payroll_employer
            + depreciation.amount
            + service_cost
            + willow_cost
            + atlas_cost
            + recovery_run.operating_cost
            + recovery_run.host_share_amount
        )
        return replaced_revenue, replaced_cost
    if entity_code == "RWH":
        if site_id is None:
            raise ValueError("Red Wash causal generation requires a site")
        feed_tons = D("1000")
        grade = D("0.001")
        recovery = D("0.80")
        pounds = feed_tons * D(2000) * grade * recovery
        batch = produce_concentrate(
            session,
            entity_id=entity_id,
            site_id=site_id,
            book_id=book_id,
            period_id=period_id,
            key=f"{key}:MINE",
            production_date=period_end,
            feed_tons=feed_tons,
            grade_fraction=grade,
            recovery_fraction=recovery,
            production_cost=causal_cost,
        )
        ship_and_collect(
            session,
            batch=batch,
            book_id=book_id,
            period_id=period_id,
            shipment_date=period_end,
            pounds_shipped=pounds,
            realized_price_per_lb=causal_revenue / pounds,
        )
        return causal_revenue, causal_cost
    if entity_code == "ARU":
        fuel_cost = (causal_cost * D("0.55")).quantize(D("0.01"))
        crew_cost = causal_cost - fuel_cost
        operate_waybill(
            session,
            entity_id=entity_id,
            book_id=book_id,
            period_id=period_id,
            key=f"{key}:WAYBILL",
            movement_date=period_end,
            carloads=12,
            tons=D("840"),
            route_miles=D("120"),
            base_rate=causal_revenue,
            fuel_surcharge=D(0),
            fuel_gallons=D("1000"),
            fuel_price=fuel_cost / D("1000"),
            crew_hours=D("100"),
            crew_rate=crew_cost / D("100"),
        )
        return causal_revenue, causal_cost
    return D(0), D(0)


ACCOUNTS = (
    ("1000", "Cash and cash equivalents", "ASSET", "DEBIT"),
    ("1100", "Accounts receivable", "ASSET", "DEBIT"),
    ("1200", "Inventory", "ASSET", "DEBIT"),
    ("1500", "Property plant and equipment", "ASSET", "DEBIT"),
    ("1590", "Accumulated depreciation", "ASSET", "CREDIT"),
    ("1600", "Goodwill and acquired intangibles", "ASSET", "DEBIT"),
    ("2000", "Accounts payable and accrued liabilities", "LIABILITY", "CREDIT"),
    ("2100", "Trade accounts payable", "LIABILITY", "CREDIT"),
    ("2200", "Deferred revenue", "LIABILITY", "CREDIT"),
    ("2300", "Asset retirement obligation", "LIABILITY", "CREDIT"),
    ("2500", "Long-term debt", "LIABILITY", "CREDIT"),
    ("2510", "Accrued interest", "LIABILITY", "CREDIT"),
    ("3000", "Contributed capital and accumulated deficit", "EQUITY", "CREDIT"),
    ("4000", "Foundry Field subscription and usage revenue", "REVENUE", "CREDIT"),
    ("4010", "Implementation and support revenue", "REVENUE", "CREDIT"),
    ("4020", "Atlas Meridian revenue", "REVENUE", "CREDIT"),
    ("4030", "Uranium concentrate revenue", "REVENUE", "CREDIT"),
    ("4040", "Freight terminal and handling revenue", "REVENUE", "CREDIT"),
    ("4050", "Cradle recovery participation revenue", "REVENUE", "CREDIT"),
    ("4060", "Advisory method-transfer revenue", "REVENUE", "CREDIT"),
    ("4090", "Intercompany revenue", "REVENUE", "CREDIT"),
    ("5000", "Cost of revenue and production", "EXPENSE", "DEBIT"),
    ("5050", "Mine production costs", "EXPENSE", "DEBIT"),
    ("6000", "Research and development", "EXPENSE", "DEBIT"),
    ("6100", "Payroll and benefits", "EXPENSE", "DEBIT"),
    ("6110", "Sales and marketing", "EXPENSE", "DEBIT"),
    ("6200", "General and administrative", "EXPENSE", "DEBIT"),
    ("6300", "Depreciation depletion and accretion", "EXPENSE", "DEBIT"),
    ("6400", "Intercompany freight and services", "EXPENSE", "DEBIT"),
    ("7100", "Interest expense", "OTHER_EXPENSE", "DEBIT"),
    ("9000", "Consolidation eliminations", "EQUITY", "CREDIT"),
)


def _entity_id(code: str) -> str:
    return stable_id("entity", code)


def _account_id(code: str) -> str:
    return stable_id("account", code)


def _line(
    entry_key: str,
    index: int,
    account: str,
    debit: D | None = None,
    credit: D | None = None,
    segment: str | None = None,
    counterparty: str | None = None,
) -> JournalLine:
    debit = debit or D(0)
    credit = credit or D(0)
    signed = debit - credit
    return JournalLine(
        id=stable_id("line", f"{entry_key}:{index}"),
        account_id=_account_id(account),
        debit=debit,
        credit=credit,
        functional_amount=signed,
        reporting_amount=signed,
        fact_state=FactState.SYNTHETIC_INSTANCE,
        segment_code=segment,
        cost_center_code=segment,
        counterparty_entity_id=_entity_id(counterparty) if counterparty else None,
    )


def _post(
    session: Session,
    book_id: str,
    period_id: str,
    key: str,
    description: str,
    lines: list[JournalLine],
    entry_date: date = date(2026, 12, 31),
    source_type: str = "deterministic_generation",
    generation_run_id: str | None = None,
) -> None:
    entry = JournalEntry(
        id=stable_id("journal", key),
        generation_run_id=generation_run_id,
        book_id=book_id,
        period_id=period_id,
        entry_date=entry_date,
        description=description,
        source_type=source_type,
        source_id=stable_id("event", key),
        lines=lines,
    )
    session.add(entry)
    post_entry(session, entry)


def _period_is_actual(run: GenerationRun, starts_on: date, ends_on: date) -> bool:
    """Classify a whole reporting period from the persisted run contract."""
    if run.actual_through is None or run.forecast_from is None:
        raise ValueError(f"Generation run {run.id!r} has no cutoff contract")
    if ends_on <= run.actual_through:
        return True
    if starts_on >= run.forecast_from:
        return False
    raise ValueError(
        f"Reporting period {starts_on}..{ends_on} crosses or is not covered by the "
        f"persisted cutoff {run.actual_through} / {run.forecast_from}"
    )


def _dated_fact_is_actual(run: GenerationRun, effective_on: date) -> bool:
    """Classify a point-in-time fact from the persisted run contract."""
    if run.actual_through is None or run.forecast_from is None:
        raise ValueError(f"Generation run {run.id!r} has no cutoff contract")
    if effective_on <= run.actual_through:
        return True
    if effective_on >= run.forecast_from:
        return False
    raise ValueError(
        f"Fact date {effective_on} is not covered by persisted cutoff "
        f"{run.actual_through} / {run.forecast_from}"
    )


def generate_baseline(
    session: Session,
    seed: int = 20260831,
    scenario: str = "base",
    post_summary: bool = True,
) -> dict[str, int | str]:
    """Generate a deterministic, public-safe FY2026 enterprise instance."""
    marker = stable_id("scenario", f"{scenario}:{seed}")
    if session.get(ScenarioValue, stable_id("scenario_value", f"{marker}:marker")):
        employees = session.scalar(
            select(func.count(Worker.id)).where(Worker.worker_type == "EMPLOYEE")
        )
        contractors = session.scalar(
            select(func.count(Worker.id)).where(Worker.worker_type == "CONTRACTOR")
        )
        return {
            "scenario": scenario,
            "seed": seed,
            "employees": employees or 0,
            "contractors": contractors or 0,
        }
    rng = Random(seed)
    plans = entity_plans()
    active_run_id = session.info.get(GENERATION_RUN_SESSION_KEY)
    active_run = (
        session.get(GenerationRun, str(active_run_id)) if active_run_id is not None else None
    )
    if active_run is None or active_run.actual_through is None or active_run.forecast_from is None:
        raise ValueError("Baseline generation requires a persisted run cutoff contract")

    parent_id = _entity_id("SHI")
    entities = [
        LegalEntity(
            id=parent_id,
            code="SHI",
            name=plans[0].name,
            fact_state=FactState.MODEL_PROPOSED,
            effective_from=date(2016, 1, 1),
            jurisdiction="US-DE",
        ),
        LegalEntity(
            id=_entity_id("RWH"),
            code="RWH",
            name=plans[1].name,
            parent_id=parent_id,
            fact_state=FactState.MODEL_PROPOSED,
            effective_from=date(2025, 7, 1),
            jurisdiction="US-WY",
        ),
        LegalEntity(
            id=_entity_id("ARU"),
            code="ARU",
            name=plans[2].name,
            parent_id=parent_id,
            fact_state=FactState.MODEL_PROPOSED,
            effective_from=date(2026, 2, 1),
            jurisdiction="US-WY",
        ),
        LegalEntity(
            id=_entity_id("CONS"),
            code="CONS",
            name="Sable Harbor consolidation book",
            parent_id=parent_id,
            fact_state=FactState.MODEL_PROPOSED,
            effective_from=date(2026, 1, 1),
            jurisdiction="N/A",
        ),
    ]
    for entity in entities:
        if session.get(LegalEntity, entity.id) is None:
            session.add(entity)
    session.flush()
    for code, name, cls, normal in ACCOUNTS:
        account_id = _account_id(code)
        if session.get(Account, account_id) is None:
            session.add(
                Account(
                    id=account_id,
                    code=code,
                    name=name,
                    account_class=cls,
                    normal_balance=normal,
                )
            )

    sites = {
        "SAC": Site(
            id=stable_id("site", "SAC"),
            code="SAC",
            name="Sacramento headquarters",
            site_type="OFFICE",
            region="California",
            owner_entity_id=parent_id,
            fact_state=FactState.MODEL_PROPOSED,
        ),
        "RED_WASH": Site(
            id=stable_id("site", "RED_WASH"),
            code="RED_WASH",
            name="Red Wash Mine",
            site_type="UNDERGROUND_MINE_MILL",
            region="Wyoming",
            owner_entity_id=_entity_id("RWH"),
            fact_state=FactState.LOCKED_CANON,
        ),
        "ARU_HUB": Site(
            id=stable_id("site", "ARU_HUB"),
            code="ARU_HUB",
            name="ARU regional operating estate",
            site_type="RAIL_TERMINAL_NETWORK",
            region="Mountain West",
            owner_entity_id=_entity_id("ARU"),
            fact_state=FactState.MODEL_PROPOSED,
        ),
    }
    for site_record in sites.values():
        if session.get(Site, site_record.id) is None:
            session.add(site_record)
    periods: dict[str, tuple[str, str]] = {}
    for entity_obj in entities:
        book_id = stable_id("book", f"{entity_obj.code}:PRIMARY_USD")
        period_id = stable_id("period", f"{book_id}:2026-12")
        if session.get(AccountingBook, book_id) is None:
            session.add(
                AccountingBook(id=book_id, entity_id=entity_obj.id, code="PRIMARY_USD")
            )
        if session.get(FiscalPeriod, period_id) is None:
            session.add(
                FiscalPeriod(
                    id=period_id,
                    book_id=book_id,
                    code="2026-12",
                    starts_on=date(2026, 12, 1),
                    ends_on=date(2026, 12, monthrange(2026, 12)[1]),
                )
            )
        periods[entity_obj.code] = (book_id, period_id)
    session.flush()

    opening_layers = {
        "SHI": [
            ("1000", D("34800000")),
            ("1500", D("9000000")),
            ("1600", D("30000000")),
            ("2500", -D("35000000")),
            ("3000", -D("38800000")),
        ],
        "RWH": [
            ("1000", D("5000000")),
            ("1200", D("2900000")),
            ("1500", D("53500000")),
            ("1600", D("7100000")),
            ("2500", -D("32000000")),
            ("2300", -D("18500000")),
            ("3000", -D("18000000")),
        ],
        "ARU": [
            ("1000", D("7000000")),
            ("1500", D("82000000")),
            ("1600", D("15000000")),
            ("2000", -D("8000000")),
            ("2500", -D("44000000")),
            ("3000", -D("52000000")),
        ],
    }
    for entity_code, balances in opening_layers.items():
        book, period = periods[entity_code]
        key = f"{marker}:{entity_code}:OPENING"
        lines = [
            _line(
                key,
                index,
                account,
                debit=amount if amount > 0 else None,
                credit=-amount if amount < 0 else None,
                segment=next(plan.segment for plan in plans if plan.code == entity_code),
            )
            for index, (account, amount) in enumerate(balances, 1)
        ]
        _post(
            session,
            book,
            period,
            key,
            f"Scenario opening and acquisition balances — {entity_code}",
            lines,
        )

    # CoreCo includes Foundry/Atlas/Willow; Cradle and Advisory remain traceable segments.
    allocations = [
        ("SHI", "CORE", "SOFTWARE_SERVICES", 431, "SAC"),
        ("SHI", "CRADLE", "RECOVERY", 12, "SAC"),
        ("SHI", "ADVISORY", "ADVISORY", 7, "SAC"),
        ("RWH", "PALE_SUN", "MINE_OPERATIONS", 126, "RED_WASH"),
        ("ARU", "ARU_BST", "LOGISTICS", 132, "ARU_HUB"),
    ]
    worker_no = 1
    for entity_code, segment, function, count, site in allocations:
        for _ in range(count):
            annual_cost = D(str(rng.randrange(62000, 188001))).quantize(D("1"))
            number = f"SHW-{worker_no:05d}"
            session.add(
                Worker(
                    id=stable_id("worker", f"{marker}:{number}"),
                    worker_number=number,
                    worker_type="EMPLOYEE",
                    entity_id=_entity_id(entity_code),
                    site_id=sites[site].id,
                    segment_code=segment,
                    function_code=function,
                    annual_cost=annual_cost,
                    starts_on=date(2026 - rng.randrange(0, 7), rng.randrange(1, 13), 1),
                    fact_state=FactState.SYNTHETIC_INSTANCE,
                )
            )
            worker_no += 1
    for i in range(1, 62):
        number = f"SHC-{i:05d}"
        session.add(
            Worker(
                id=stable_id("worker", f"{marker}:{number}"),
                worker_number=number,
                worker_type="CONTRACTOR",
                entity_id=parent_id,
                site_id=sites["SAC"].id,
                segment_code="CORE",
                function_code="SPECIALIST",
                annual_cost=D(rng.randrange(90000, 260001)),
                starts_on=date(2026, 1, 1),
                ends_on=date(2026, 12, 31),
                fact_state=FactState.SYNTHETIC_INSTANCE,
            )
        )

    # Public-safe synthetic business parties and contracts.
    for i in range(1, 59):
        code = f"CUS-{i:04d}"
        party = BusinessParty(
            id=stable_id("party", f"{marker}:{code}"),
            code=code,
            party_type="CUSTOMER",
            segment_code="CORE",
            risk_tier="T2" if i < 10 else "T3",
            fact_state=FactState.SYNTHETIC_INSTANCE,
        )
        session.add(party)
        session.add(
            Contract(
                id=stable_id("contract", f"{marker}:{code}"),
                code=f"MSA-2026-{i:04d}",
                entity_id=parent_id,
                party_id=party.id,
                contract_type="SUBSCRIPTION_SERVICES",
                starts_on=date(2026, 1, 1),
                ends_on=date(2028, 12, 31),
                committed_value=D(600000 + i * 51000),
                fact_state=FactState.SYNTHETIC_INSTANCE,
            )
        )
    for i in range(1, 81):
        code = f"VEN-{i:04d}"
        session.add(
            BusinessParty(
                id=stable_id("party", f"{marker}:{code}"),
                code=code,
                party_type="VENDOR",
                segment_code="ENTERPRISE",
                risk_tier="T1" if i <= 12 else "T3",
                fact_state=FactState.SYNTHETIC_INSTANCE,
            )
        )

    # Operational subledgers.
    for asset_no, entity_code, site, cls, cost, life, layer in [
        ("RWH-MINERAL", "RWH", "RED_WASH", "MINERAL_INTEREST", D("22000000"), 120, True),
        ("RWH-PLANT", "RWH", "RED_WASH", "MILL_AND_MINE_PLANT", D("31500000"), 144, True),
        ("ARU-TRACK", "ARU", "ARU_HUB", "TRACK_AND_TERMINALS", D("54000000"), 240, True),
        ("ARU-ROLL", "ARU", "ARU_HUB", "ROLLING_STOCK", D("28000000"), 180, True),
        ("SHI-PLATFORM", "SHI", "SAC", "PLATFORM_INFRASTRUCTURE", D("9000000"), 48, False),
    ]:
        session.add(
            FixedAsset(
                id=stable_id("asset", f"{marker}:{asset_no}"),
                asset_number=asset_no,
                entity_id=_entity_id(entity_code),
                site_id=sites[site].id,
                asset_class=cls,
                placed_in_service=date(2025, 7, 1) if entity_code == "RWH" else date(2026, 2, 1),
                cost=cost,
                useful_life_months=life,
                acquisition_layer=layer,
                fact_state=FactState.SCENARIO_INPUT,
            )
        )
    # The common-actual layer stops at its persisted cutoff. Future
    # operating facts are materialized by ``generate_standard`` in the selected
    # scenario run; keeping them here would make forecasts look observed.
    for month in range(1, 13):
        period_start = date(2026, month, 1)
        period_end = date(2026, month, monthrange(2026, month)[1])
        if not _period_is_actual(active_run, period_start, period_end):
            continue
        ore = D(13500 + rng.randrange(-1600, 1601))
        recovery = D(str(0.812 + rng.random() * 0.048)).quantize(D("0.000001"))
        lbs = (ore * D("1.72") * recovery).quantize(D("0.01"))
        session.add(
            ProductionRecord(
                id=stable_id("production", f"{marker}:RWH:2026-{month:02d}"),
                site_id=sites["RED_WASH"].id,
                period_code=f"2026-{month:02d}",
                ore_tonnes=ore,
                mill_feed_tonnes=(ore * D("0.94")).quantize(D("0.01")),
                concentrate_lbs=lbs,
                recovery_rate=recovery,
                fact_state=FactState.SYNTHETIC_INSTANCE,
            )
        )
    ending_inventory_date = date(2026, 12, 31)
    if _dated_fact_is_actual(active_run, ending_inventory_date):
        ending_inventory_id = stable_id("lot", f"{marker}:RWH-2026-ENDING")
        if session.get(InventoryLot, ending_inventory_id) is None:
            session.add(
                InventoryLot(
                    id=ending_inventory_id,
                    lot_number="RWH-2026-ENDING",
                    entity_id=_entity_id("RWH"),
                    site_id=sites["RED_WASH"].id,
                    inventory_stage="CONCENTRATE",
                    quantity=D("68400"),
                    unit="LB_U3O8",
                    carrying_value=D("2900000"),
                    as_of_date=ending_inventory_date,
                    fact_state=FactState.SYNTHETIC_INSTANCE,
                )
            )
    session.add(
        EnvironmentalObligation(
            id=stable_id("obligation", f"{marker}:RWH-ARO"),
            entity_id=_entity_id("RWH"),
            site_id=sites["RED_WASH"].id,
            obligation_type="MINE_CLOSURE_ARO",
            undiscounted_amount=D("28500000"),
            discount_rate=D("0.0525"),
            recognized_liability=D("18500000"),
            expected_settlement_year=2041,
            fact_state=FactState.SCENARIO_INPUT,
        )
    )
    for i in range(1, 121):
        movement_month = ((i - 1) % 12) + 1
        movement_date = date(2026, movement_month, min(25, ((i * 7) % 27) + 1))
        if not _dated_fact_is_actual(active_run, movement_date):
            continue
        intercompany = i % 20 == 0
        session.add(
            FreightMovement(
                id=stable_id("movement", f"{marker}:ARU-2026-{i:04d}"),
                movement_number=f"ARU-2026-{i:04d}",
                entity_id=_entity_id("ARU"),
                movement_date=movement_date,
                commodity="URANIUM_CONCENTRATE" if intercompany else "MINERAL_PRODUCTS",
                tonnes=D(65 if intercompany else 740 + rng.randrange(-120, 121)),
                revenue=D("500000") if intercompany else D(100000 + rng.randrange(20000, 90001)),
                intercompany=intercompany,
                custody_status="HELD_RECONCILIATION" if i == 100 else "COMPLETE",
                fact_state=FactState.SYNTHETIC_INSTANCE,
            )
        )

    if not post_summary:
        session.add(
            ScenarioValue(
                id=stable_id("scenario_value", f"{marker}:marker"),
                scenario_code=scenario,
                metric_code="marker",
                entity_code="CONSOLIDATED",
                period_code="2023-2026",
                amount=D("1"),
                unit="count",
                fact_state=FactState.DERIVED,
                provenance="standard monthly generation marker",
            )
        )
        session.flush()
        return {"scenario": scenario, "seed": seed, "employees": 708, "contractors": 61}

    # Summary ledgers: cash-realized revenue and expense; acquisition/opening positions.
    for plan in plans:
        book, period = periods[plan.code]
        rev_account = "4000" if plan.code == "SHI" else "4030" if plan.code == "RWH" else "4040"
        _post(
            session,
            book,
            period,
            f"{marker}:{plan.code}:OPERATIONS",
            f"FY2026 generated operating summary — {plan.code}",
            [
                _line(
                    f"{marker}:{plan.code}:OPERATIONS",
                    1,
                    "1000",
                    debit=plan.revenue,
                    segment=plan.segment,
                ),
                _line(
                    f"{marker}:{plan.code}:OPERATIONS",
                    2,
                    rev_account,
                    credit=plan.revenue,
                    segment=plan.segment,
                ),
                _line(
                    f"{marker}:{plan.code}:OPERATIONS",
                    3,
                    "5000" if plan.code != "SHI" else "6000",
                    debit=plan.operating_cost,
                    segment=plan.segment,
                ),
                _line(
                    f"{marker}:{plan.code}:OPERATIONS",
                    4,
                    "1000",
                    credit=plan.operating_cost,
                    segment=plan.segment,
                ),
            ],
        )
    # Reclassify parent revenue into its real lines without changing total.
    book, period = periods["SHI"]
    key = f"{marker}:SHI:REVENUE_MIX"
    _post(
        session,
        book,
        period,
        key,
        "CoreCo revenue mix reclassification",
        [
            _line(key, 1, "4000", debit=D("130300000"), segment="CORE"),
            _line(key, 2, "4000", credit=D("84200000"), segment="FOUNDRY_FIELD"),
            _line(key, 3, "4010", credit=D("39100000"), segment="DELIVERY"),
            _line(key, 4, "4020", credit=D("4500000"), segment="ATLAS"),
            _line(key, 5, "4050", credit=D("1300000"), segment="CRADLE"),
            _line(key, 6, "4060", credit=D("1200000"), segment="ADVISORY"),
        ],
    )
    # Intercompany freight and its consolidation elimination ($3.0M).
    ic = D("3000000")
    aru_book, aru_period = periods["ARU"]
    key = f"{marker}:ARU:IC"
    _post(
        session,
        aru_book,
        aru_period,
        key,
        "Freight billed to Red Wash",
        [
            _line(key, 1, "1100", debit=ic, segment="ARU_BST", counterparty="RWH"),
            _line(key, 2, "4090", credit=ic, segment="ARU_BST", counterparty="RWH"),
        ],
    )
    rwh_book, rwh_period = periods["RWH"]
    key = f"{marker}:RWH:IC"
    _post(
        session,
        rwh_book,
        rwh_period,
        key,
        "Freight purchased from ARU",
        [
            _line(key, 1, "6400", debit=ic, segment="PALE_SUN", counterparty="ARU"),
            _line(key, 2, "2000", credit=ic, segment="PALE_SUN", counterparty="ARU"),
        ],
    )
    cons_book, cons_period = periods["CONS"]
    key = f"{marker}:CONS:IC_ELIM"
    _post(
        session,
        cons_book,
        cons_period,
        key,
        "Eliminate ARU–Red Wash intercompany freight",
        [
            _line(key, 1, "4090", debit=ic, segment="ELIMINATION", counterparty="ARU"),
            _line(key, 2, "6400", credit=ic, segment="ELIMINATION", counterparty="RWH"),
            _line(key, 3, "2000", debit=ic, segment="ELIMINATION", counterparty="RWH"),
            _line(key, 4, "1100", credit=ic, segment="ELIMINATION", counterparty="ARU"),
        ],
    )

    # Scenario registry, including a marker for idempotence.
    values = {
        "employees": D("708"),
        "contractors": D("61"),
        "revenue": D("178600000"),
        "gross_debt": D("111000000"),
        "cash_target": D("42000000"),
        "red_wash_enterprise_value": D("48000000"),
        "aru_enterprise_value": D("76000000"),
        "red_wash_aro": D("18500000"),
        "marker": D("1"),
    }
    for metric, amount in values.items():
        sid = stable_id("scenario_value", f"{marker}:{metric}")
        session.add(
            ScenarioValue(
                id=sid,
                scenario_code=scenario,
                metric_code=metric,
                entity_code="CONSOLIDATED",
                period_code="2026-FY",
                amount=amount,
                unit="count" if metric in {"employees", "contractors", "marker"} else "USD",
                fact_state=FactState.MODEL_PROPOSED
                if metric
                not in {"red_wash_enterprise_value", "aru_enterprise_value", "red_wash_aro"}
                else FactState.SCENARIO_INPUT,
                provenance="docs/finance/QUANTITATIVE_BASELINE_RECONCILIATION.md",
            )
        )
    session.flush()
    return {"scenario": scenario, "seed": seed, "employees": 708, "contractors": 61}


def _ensure_common_actual_layer(
    session: Session, seed: int, *, complete: bool = True
) -> GenerationRun:
    selected_run_id = session.info.get(GENERATION_RUN_SESSION_KEY)
    selected_run = (
        session.get(GenerationRun, str(selected_run_id)) if selected_run_id is not None else None
    )
    git_commit = selected_run.git_commit if selected_run is not None else "UNKNOWN"
    actual_run = record_generation_run(
        session,
        profile="actual_common",
        scenario_code="actual_common",
        seed=seed,
        git_commit=git_commit,
    )
    generate_baseline(session, seed=seed, scenario="actual_common", post_summary=False)
    if complete and actual_run.status == "RUNNING":
        complete_generation_run(session, actual_run)
    if selected_run is not None:
        selected_run.actual_generation_run_id = actual_run.id
        session.info[GENERATION_RUN_SESSION_KEY] = selected_run.id
    return actual_run


def generate_baseline_run(
    session: Session, seed: int = 20260831, scenario: str = "base"
) -> dict[str, int | str]:
    """Attach a baseline scenario run to deterministic common opening and actual facts."""
    _ensure_common_actual_layer(session, seed, complete=False)
    session.info["populate_common_actuals_only"] = True
    try:
        generate_standard(session, seed=seed, scenario=scenario)
    finally:
        session.info.pop("populate_common_actuals_only", None)
    run_id = str(session.info[GENERATION_RUN_SESSION_KEY])
    marker_id = stable_id("scenario_value", f"run:{run_id}:marker")
    if session.get(ScenarioValue, marker_id) is None:
        session.add(
            ScenarioValue(
                id=marker_id,
                scenario_code=scenario,
                metric_code="generation_marker",
                entity_code="CONSOLIDATED",
                period_code="BASELINE",
                amount=D(1),
                unit="count",
                fact_state=FactState.DERIVED,
                provenance="baseline run marker; includes deterministic common-actual layer",
            )
        )
        session.flush()
    return {"scenario": scenario, "seed": seed, "employees": 708, "contractors": 61}


def generate_standard(
    session: Session, seed: int = 20260831, scenario: str = "base"
) -> dict[str, int | str]:
    """Generate deterministic monthly 2023–2026 ledgers and operating driver values."""
    # Validate the scenario contract before requiring a database run context.
    scenario_multipliers(scenario)
    run_id = session.info.get(GENERATION_RUN_SESSION_KEY)
    if run_id is None:
        raise ValueError("Standard generation requires an active generation run")
    selected_run = session.get(GenerationRun, str(run_id))
    if selected_run is None:
        raise ValueError(f"Unknown active generation run {run_id!r}")
    _persist_scenario_drivers(session, selected_run, scenario)
    marker = stable_id("generation_namespace", str(run_id))
    marker_id = stable_id("scenario_value", f"run:{run_id}:generation-marker")
    actuals_only = bool(session.info.get("populate_common_actuals_only"))
    existing_marker = session.get(ScenarioValue, marker_id)
    if not actuals_only and existing_marker is not None:
        return {
            "scenario": scenario,
            "profile": "standard",
            "seed": seed,
            "periods": 48,
        }
    actual_run = _ensure_common_actual_layer(session, seed, complete=False)
    if (
        selected_run.actual_through != actual_run.actual_through
        or selected_run.forecast_from != actual_run.forecast_from
    ):
        raise ValueError("Selected and common-actual runs have incompatible cutoff contracts")
    actual_standard_marker_id = stable_id(
        "scenario_value", f"run:{actual_run.id}:standard-actual-marker"
    )
    if (
        actual_run.status == "COMPLETED"
        and session.get(ScenarioValue, actual_standard_marker_id) is None
    ):
        raise ValueError(
            "Completed common-actual layer does not satisfy the standard profile contract; "
            "completed generation runs are immutable"
        )
    books = {
        entity.code: book
        for entity, book in session.execute(
            select(LegalEntity, AccountingBook).join(
                AccountingBook, AccountingBook.entity_id == LegalEntity.id
            )
        )
    }
    site_ids = {site.code: site.id for site in session.scalars(select(Site))}
    plan_map = {plan.code: plan for plan in entity_plans()}
    yearly = {
        2023: {"SHI": (D("67200000"), D("75000000"))},
        2024: {"SHI": (D("85700000"), D("95000000"))},
        2025: {
            "SHI": (D("104900000"), D("115000000")),
            "RWH": (D("10000000"), D("11000000")),
        },
        2026: {
            "SHI": (plan_map["SHI"].revenue, plan_map["SHI"].operating_cost),
            "RWH": (plan_map["RWH"].revenue, plan_map["RWH"].operating_cost),
            "ARU": (plan_map["ARU"].revenue, plan_map["ARU"].operating_cost),
        },
    }
    revenue_accounts = {"SHI": "4000", "RWH": "4030", "ARU": "4040"}
    weights = [
        D("0.075"),
        D("0.077"),
        D("0.080"),
        D("0.081"),
        D("0.082"),
        D("0.083"),
        D("0.084"),
        D("0.085"),
        D("0.086"),
        D("0.087"),
        D("0.089"),
        D("0.091"),
    ]
    for year, entity_values in yearly.items():
        for entity_code, (annual_revenue, annual_cost) in entity_values.items():
            revenue_multiplier, cost_multiplier = scenario_multipliers(
                scenario, entity_code
            )
            book = books[entity_code]
            allocated_revenue = D(0)
            allocated_cost = D(0)
            first_active_month = (
                7
                if entity_code == "RWH" and year == 2025
                else 2
                if entity_code == "ARU" and year == 2026
                else 1
            )
            denominator = sum(weights[first_active_month - 1 :])

            def multiplier_for(
                month: int, scenario_multiplier: D, calculation_year: int = year
            ) -> D:
                return (
                    D(1)
                    if _period_is_actual(
                        selected_run,
                        date(calculation_year, month, 1),
                        date(
                            calculation_year,
                            month,
                            monthrange(calculation_year, month)[1],
                        ),
                    )
                    else scenario_multiplier
                )

            target_revenue = sum(
                annual_revenue
                * multiplier_for(month, revenue_multiplier)
                * weights[month - 1]
                / denominator
                for month in range(first_active_month, 13)
            )
            target_cost = sum(
                annual_cost
                * multiplier_for(month, cost_multiplier)
                * weights[month - 1]
                / denominator
                for month in range(first_active_month, 13)
            )
            for month, weight in enumerate(weights, start=1):
                if entity_code == "RWH" and year == 2025 and month < 7:
                    continue
                if entity_code == "ARU" and year == 2026 and month < 2:
                    continue
                period_code = f"{year}-{month:02d}"
                period_id = stable_id("period", f"{book.id}:{period_code}")
                period = session.get(FiscalPeriod, period_id)
                if period is None:
                    period = FiscalPeriod(
                        id=period_id,
                        book_id=book.id,
                        code=period_code,
                        starts_on=date(year, month, 1),
                        ends_on=date(year, month, monthrange(year, month)[1]),
                    )
                    session.add(period)
                    session.flush()
                is_actual = _period_is_actual(selected_run, period.starts_on, period.ends_on)
                if actuals_only and not is_actual:
                    continue
                period_revenue_multiplier = D(1) if is_actual else revenue_multiplier
                period_cost_multiplier = D(1) if is_actual else cost_multiplier
                scenario_revenue = annual_revenue * period_revenue_multiplier
                scenario_cost = annual_cost * period_cost_multiplier
                revenue = (scenario_revenue * weight / denominator).quantize(D("0.01"))
                cost = (scenario_cost * weight / denominator).quantize(D("0.01"))
                is_last = month == 12
                if is_last:
                    revenue = target_revenue - allocated_revenue
                    cost = target_cost - allocated_cost
                allocated_revenue += revenue
                allocated_cost += cost
                availability = (
                    "monthly_actual" if is_actual else "monthly_forecast"
                )
                owner_run_id = actual_run.id if is_actual else str(run_id)
                owner_scenario = "actual_common" if is_actual else scenario
                owner_marker = stable_id("generation_namespace", owner_run_id)
                key = f"{owner_marker}:{entity_code}:{period_code}:OPERATIONS"
                reported_revenue = revenue
                reported_cost = cost
                if not is_actual and year == 2026:
                    causal_revenue, causal_cost = _generate_causal_month(
                        session,
                        entity_code=entity_code,
                        entity_id=book.entity_id,
                        site_id=site_ids.get("RED_WASH") if entity_code == "RWH" else None,
                        book_id=book.id,
                        period_id=period.id,
                        period_end=period.ends_on,
                        key=key,
                        revenue=revenue,
                        cost=cost,
                    )
                    revenue -= causal_revenue
                    cost -= causal_cost
                if session.get(JournalEntry, stable_id("journal", key)) is None:
                    _post(
                        session,
                        book.id,
                        period.id,
                        key,
                        f"Monthly generated operating control — {entity_code} {period_code}",
                        [
                            _line(key, 1, "1000", debit=revenue, segment=entity_code),
                            _line(
                                key,
                                2,
                                revenue_accounts[entity_code],
                                credit=revenue,
                                segment=entity_code,
                            ),
                            _line(key, 3, "5000", debit=cost, segment=entity_code),
                            _line(key, 4, "1000", credit=cost, segment=entity_code),
                        ],
                        entry_date=period.ends_on,
                        source_type=availability,
                        generation_run_id=owner_run_id,
                    )
                for metric, amount in (
                    ("revenue", reported_revenue),
                    ("operating_cost", reported_cost),
                ):
                    value_id = stable_id(
                        "scenario_value",
                        f"{owner_marker}:{entity_code}:{period_code}:{metric}",
                    )
                    if session.get(ScenarioValue, value_id) is None:
                        session.add(
                            ScenarioValue(
                                id=value_id,
                                generation_run_id=owner_run_id,
                                scenario_code=owner_scenario,
                                metric_code=metric,
                                entity_code=entity_code,
                                period_code=period_code,
                                amount=amount,
                                unit="USD",
                                fact_state=FactState.DERIVED,
                                provenance=f"{availability} from versioned annual driver",
                            )
                        )
    if actuals_only:
        if session.get(ScenarioValue, actual_standard_marker_id) is None:
            session.add(
                ScenarioValue(
                    id=actual_standard_marker_id,
                    generation_run_id=actual_run.id,
                    scenario_code="actual_common",
                    metric_code="standard_actual_completion_marker",
                    entity_code="CONSOLIDATED",
                    period_code=(
                        f"2023-2026_ACTUAL_THROUGH_{actual_run.actual_through:%Y-%m-%d}"
                    ),
                    amount=D(1),
                    unit="count",
                    fact_state=FactState.DERIVED,
                    provenance="common actual superset contract marker",
                )
            )
        if actual_run.status == "RUNNING":
            complete_generation_run(session, actual_run)
        session.flush()
        return {"scenario": scenario, "profile": "standard", "seed": seed, "periods": 44}

    # Scenario-owned operating forecasts.  These deliberately mirror the dated
    # actual registers above without placing post-cutoff records in actual_common.
    forecast_rng = Random(seed)
    actual_production_months = [
        month
        for month in range(1, 13)
        if _period_is_actual(
            selected_run,
            date(2026, month, 1),
            date(2026, month, monthrange(2026, month)[1]),
        )
    ]
    for _ in actual_production_months:
        forecast_rng.randrange(-1600, 1601)
        forecast_rng.random()
    red_wash_site_id = stable_id("site", "RED_WASH")
    rwh_revenue_multiplier, rwh_cost_multiplier = scenario_multipliers(scenario, "RWH")
    aru_revenue_multiplier, _aru_cost_multiplier = scenario_multipliers(scenario, "ARU")
    for month in range(1, 13):
        period_start = date(2026, month, 1)
        period_end = date(2026, month, monthrange(2026, month)[1])
        if _period_is_actual(selected_run, period_start, period_end):
            continue
        ore = D(13500 + forecast_rng.randrange(-1600, 1601))
        ore = (ore * rwh_revenue_multiplier).quantize(D("0.01"))
        recovery = D(str(0.812 + forecast_rng.random() * 0.048)).quantize(D("0.000001"))
        lbs = (ore * D("1.72") * recovery).quantize(D("0.01"))
        session.add(
            ProductionRecord(
                id=stable_id("production", f"{marker}:RWH:2026-{month:02d}"),
                site_id=red_wash_site_id,
                period_code=f"2026-{month:02d}",
                ore_tonnes=ore,
                mill_feed_tonnes=(ore * D("0.94")).quantize(D("0.01")),
                concentrate_lbs=lbs,
                recovery_rate=recovery,
                fact_state=FactState.SYNTHETIC_INSTANCE,
            )
        )
    ending_inventory_date = date(2026, 12, 31)
    if not _dated_fact_is_actual(selected_run, ending_inventory_date):
        session.add(
            InventoryLot(
                id=stable_id("lot", f"{marker}:RWH-2026-ENDING"),
                lot_number="RWH-2026-ENDING",
                entity_id=_entity_id("RWH"),
                site_id=red_wash_site_id,
                inventory_stage="CONCENTRATE",
                quantity=(D("68400") * rwh_revenue_multiplier).quantize(D("0.01")),
                unit="LB_U3O8",
                carrying_value=(D("2900000") * rwh_cost_multiplier).quantize(D("0.01")),
                as_of_date=ending_inventory_date,
                fact_state=FactState.SYNTHETIC_INSTANCE,
            )
        )
    for i in range(1, 121):
        movement_month = ((i - 1) % 12) + 1
        movement_date = date(2026, movement_month, min(25, ((i * 7) % 27) + 1))
        if _dated_fact_is_actual(selected_run, movement_date):
            continue
        intercompany = i % 20 == 0
        baseline_revenue = D("500000") if intercompany else D(
            100000 + forecast_rng.randrange(20000, 90001)
        )
        session.add(
            FreightMovement(
                id=stable_id("movement", f"{marker}:ARU-2026-{i:04d}"),
                movement_number=f"ARU-2026-{i:04d}",
                entity_id=_entity_id("ARU"),
                movement_date=movement_date,
                commodity="URANIUM_CONCENTRATE" if intercompany else "MINERAL_PRODUCTS",
                tonnes=D(65 if intercompany else 740 + forecast_rng.randrange(-120, 121)),
                revenue=(baseline_revenue * aru_revenue_multiplier).quantize(D("0.01")),
                intercompany=intercompany,
                custody_status="HELD_RECONCILIATION" if i == 100 else "COMPLETE",
                fact_state=FactState.SYNTHETIC_INSTANCE,
            )
        )

    ic = D("3000000")
    ic_period = "2026-12"
    aru_book = books["ARU"]
    rwh_book = books["RWH"]
    cons_book = books["CONS"]
    aru_period = session.scalar(
        select(FiscalPeriod).where(
            FiscalPeriod.book_id == aru_book.id, FiscalPeriod.code == ic_period
        )
    )
    rwh_period = session.scalar(
        select(FiscalPeriod).where(
            FiscalPeriod.book_id == rwh_book.id, FiscalPeriod.code == ic_period
        )
    )
    cons_period = session.scalar(
        select(FiscalPeriod).where(
            FiscalPeriod.book_id == cons_book.id, FiscalPeriod.code == ic_period
        )
    )
    if aru_period is not None and rwh_period is not None:
        key = f"{marker}:ARU:RWH:IC"
        _post(
            session,
            aru_book.id,
            aru_period.id,
            f"{key}:SELLER",
            "ARU freight billed to Red Wash",
            [
                _line(key, 1, "1100", debit=ic, segment="ARU_BST", counterparty="RWH"),
                _line(key, 2, "4090", credit=ic, segment="ARU_BST", counterparty="RWH"),
            ],
            entry_date=aru_period.ends_on,
            source_type="intercompany_service",
        )
        _post(
            session,
            rwh_book.id,
            rwh_period.id,
            f"{key}:BUYER",
            "Red Wash freight purchased from ARU",
            [
                _line(key, 3, "6400", debit=ic, segment="PALE_SUN", counterparty="ARU"),
                _line(key, 4, "2000", credit=ic, segment="PALE_SUN", counterparty="ARU"),
            ],
            entry_date=rwh_period.ends_on,
            source_type="intercompany_service",
        )
    if cons_period is None:
        cons_period = FiscalPeriod(
            id=stable_id("period", f"{cons_book.id}:{ic_period}"),
            book_id=cons_book.id,
            code=ic_period,
            starts_on=date(2026, 12, 1),
            ends_on=date(2026, 12, 31),
        )
        session.add(cons_period)
        session.flush()
    key = f"{marker}:CONS:IC_ELIM"
    _post(
        session,
        cons_book.id,
        cons_period.id,
        key,
        "Eliminate ARU and Red Wash intercompany freight",
        [
            _line(key, 1, "4090", debit=ic, segment="ELIMINATION", counterparty="ARU"),
            _line(key, 2, "6400", credit=ic, segment="ELIMINATION", counterparty="RWH"),
            _line(key, 3, "2000", debit=ic, segment="ELIMINATION", counterparty="RWH"),
            _line(key, 4, "1100", credit=ic, segment="ELIMINATION", counterparty="ARU"),
        ],
        entry_date=cons_period.ends_on,
        source_type="consolidation_elimination",
    )
    session.add(
        ScenarioValue(
            id=marker_id,
            scenario_code=scenario,
            metric_code="generation_marker",
            entity_code="CONSOLIDATED",
            period_code="2023-2026",
            amount=D(1),
            unit="count",
            fact_state=FactState.DERIVED,
            provenance="standard run marker; common actuals plus scenario forecast",
        )
    )
    if session.get(ScenarioValue, actual_standard_marker_id) is None:
        session.add(
            ScenarioValue(
                id=actual_standard_marker_id,
                generation_run_id=actual_run.id,
                scenario_code="actual_common",
                metric_code="standard_actual_completion_marker",
                entity_code="CONSOLIDATED",
                period_code=(
                    f"2023-2026_ACTUAL_THROUGH_{actual_run.actual_through:%Y-%m-%d}"
                ),
                amount=D(1),
                unit="count",
                fact_state=FactState.DERIVED,
                provenance="standard profile common-actual contract marker",
            )
        )
    if actual_run.status == "RUNNING":
        complete_generation_run(session, actual_run)
    session.flush()
    return {"scenario": scenario, "profile": "standard", "seed": seed, "periods": 48}


def generate_full_history(
    session: Session, seed: int = 20260831, scenario: str = "base"
) -> dict[str, int | str]:
    result = generate_standard(session, seed=seed, scenario=scenario)
    run_id = session.info.get(GENERATION_RUN_SESSION_KEY)
    if run_id is None:
        raise ValueError("Full-history generation requires an active generation run")
    marker = stable_id("generation_namespace", str(run_id))
    marker_id = stable_id("scenario_value", f"run:{run_id}:full-history-marker")
    if session.get(ScenarioValue, marker_id):
        return {**result, "profile": "full_history", "history_start": 2016}
    annual_revenue = {
        2016: D("900000"),
        2017: D("2700000"),
        2018: D("6400000"),
        2019: D("12200000"),
        2020: D("13800000"),
        2021: D("28100000"),
        2022: D("46500000"),
    }
    for year, amount in annual_revenue.items():
        session.add(
            ScenarioValue(
                id=stable_id("scenario_value", f"{marker}:SHI:{year}:revenue"),
                scenario_code=scenario,
                metric_code="historical_revenue_anchor",
                entity_code="SHI",
                period_code=str(year),
                amount=amount,
                unit="USD",
                fact_state=FactState.LEGACY_CALIBRATION,
                provenance="legacy operating model annual anchor; noncontrolling",
            )
        )
    session.add(
        ScenarioValue(
            id=marker_id,
            scenario_code=scenario,
            metric_code="full_history_marker",
            entity_code="CONSOLIDATED",
            period_code="2016-2026",
            amount=D(1),
            unit="count",
            fact_state=FactState.DERIVED,
            provenance="full-history generation marker",
        )
    )
    session.flush()
    return {**result, "profile": "full_history", "history_start": 2016}
