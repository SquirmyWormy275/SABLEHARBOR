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
from sable_harbor.config.assumptions import load_assumptions
from sable_harbor.core.ids import stable_id

D = Decimal


def scenario_multipliers(scenario: str) -> tuple[D, D]:
    path = Path("config/finance/scenarios/operating.yml")
    scenarios = yaml.safe_load(path.read_text())["scenarios"]
    if scenario not in scenarios:
        raise ValueError(f"Unknown scenario {scenario!r}")
    selected = scenarios[scenario]
    return D(selected["revenue_multiplier"]), D(selected["cost_multiplier"])


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
) -> None:
    entry = JournalEntry(
        id=stable_id("journal", key),
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
    session.add(entities[0])
    session.flush()
    session.add_all(entities[1:])
    session.flush()
    for code, name, cls, normal in ACCOUNTS:
        session.add(
            Account(
                id=_account_id(code), code=code, name=name, account_class=cls, normal_balance=normal
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
    session.add_all(sites.values())
    periods: dict[str, tuple[str, str]] = {}
    for entity_obj in entities:
        book_id = stable_id("book", f"{entity_obj.code}:PRIMARY_USD")
        period_id = stable_id("period", f"{book_id}:2026-12")
        session.add(AccountingBook(id=book_id, entity_id=entity_obj.id, code="PRIMARY_USD"))
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
                    id=stable_id("worker", number),
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
                id=stable_id("worker", number),
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
            id=stable_id("party", code),
            code=code,
            party_type="CUSTOMER",
            segment_code="CORE",
            risk_tier="T2" if i < 10 else "T3",
            fact_state=FactState.SYNTHETIC_INSTANCE,
        )
        session.add(party)
        session.add(
            Contract(
                id=stable_id("contract", code),
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
                id=stable_id("party", code),
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
                id=stable_id("asset", asset_no),
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
    for month in range(1, 13):
        ore = D(13500 + rng.randrange(-1600, 1601))
        recovery = D(str(0.812 + rng.random() * 0.048)).quantize(D("0.000001"))
        lbs = (ore * D("1.72") * recovery).quantize(D("0.01"))
        session.add(
            ProductionRecord(
                id=stable_id("production", f"RWH:2026-{month:02d}"),
                site_id=sites["RED_WASH"].id,
                period_code=f"2026-{month:02d}",
                ore_tonnes=ore,
                mill_feed_tonnes=(ore * D("0.94")).quantize(D("0.01")),
                concentrate_lbs=lbs,
                recovery_rate=recovery,
                fact_state=FactState.SYNTHETIC_INSTANCE,
            )
        )
    session.add(
        InventoryLot(
            id=stable_id("lot", "RWH-2026-ENDING"),
            lot_number="RWH-2026-ENDING",
            entity_id=_entity_id("RWH"),
            site_id=sites["RED_WASH"].id,
            inventory_stage="CONCENTRATE",
            quantity=D("68400"),
            unit="LB_U3O8",
            carrying_value=D("2900000"),
            as_of_date=date(2026, 12, 31),
            fact_state=FactState.SYNTHETIC_INSTANCE,
        )
    )
    session.add(
        EnvironmentalObligation(
            id=stable_id("obligation", "RWH-ARO"),
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
        intercompany = i % 20 == 0
        session.add(
            FreightMovement(
                id=stable_id("movement", f"ARU-2026-{i:04d}"),
                movement_number=f"ARU-2026-{i:04d}",
                entity_id=_entity_id("ARU"),
                movement_date=date(2026, ((i - 1) % 12) + 1, min(25, ((i * 7) % 27) + 1)),
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


def generate_standard(
    session: Session, seed: int = 20260831, scenario: str = "base"
) -> dict[str, int | str]:
    """Generate deterministic monthly 2023–2026 ledgers and operating driver values."""
    standard_scenario = f"standard_{scenario}"
    revenue_multiplier, cost_multiplier = scenario_multipliers(scenario)
    marker = stable_id("scenario", f"{standard_scenario}:{seed}")
    marker_id = stable_id("scenario_value", f"{marker}:marker")
    if session.get(ScenarioValue, marker_id):
        return {
            "scenario": scenario,
            "profile": "standard",
            "seed": seed,
            "periods": 48,
        }
    generate_baseline(session, seed=seed, scenario=standard_scenario, post_summary=False)
    books = {
        entity.code: book
        for entity, book in session.execute(
            select(LegalEntity, AccountingBook).join(
                AccountingBook, AccountingBook.entity_id == LegalEntity.id
            )
        )
    }
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
            book = books[entity_code]
            allocated_revenue = D(0)
            allocated_cost = D(0)
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
                active_weights = weights
                if entity_code == "RWH" and year == 2025:
                    active_weights = weights[6:]
                if entity_code == "ARU" and year == 2026:
                    active_weights = weights[1:]
                denominator = sum(active_weights)
                scenario_revenue = annual_revenue * revenue_multiplier
                scenario_cost = annual_cost * cost_multiplier
                revenue = (scenario_revenue * weight / denominator).quantize(D("0.01"))
                cost = (scenario_cost * weight / denominator).quantize(D("0.01"))
                is_last = month == 12
                if is_last:
                    revenue = scenario_revenue - allocated_revenue
                    cost = scenario_cost - allocated_cost
                allocated_revenue += revenue
                allocated_cost += cost
                availability = (
                    "monthly_actual"
                    if date(year, month, 1) <= date(2026, 8, 1)
                    else "monthly_forecast"
                )
                key = f"{marker}:{entity_code}:{period_code}:OPERATIONS"
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
                )
                for metric, amount in (("revenue", revenue), ("operating_cost", cost)):
                    session.add(
                        ScenarioValue(
                            id=stable_id(
                                "scenario_value", f"{marker}:{entity_code}:{period_code}:{metric}"
                            ),
                            scenario_code=scenario,
                            metric_code=metric,
                            entity_code=entity_code,
                            period_code=period_code,
                            amount=amount,
                            unit="USD",
                            fact_state=FactState.DERIVED,
                            provenance=f"{availability} from versioned annual driver",
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
    session.flush()
    return {"scenario": scenario, "profile": "standard", "seed": seed, "periods": 48}


def generate_full_history(
    session: Session, seed: int = 20260831, scenario: str = "base"
) -> dict[str, int | str]:
    result = generate_standard(session, seed=seed, scenario=scenario)
    marker = stable_id("scenario", f"full_history:{scenario}:{seed}")
    marker_id = stable_id("scenario_value", f"{marker}:marker")
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
