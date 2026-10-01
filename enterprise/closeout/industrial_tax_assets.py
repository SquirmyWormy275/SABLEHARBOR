"""Industrial asset cohorts tied to existing costs and conditional service records."""

import json
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path

from enterprise.closeout.cost_recovery import quarterly_test, schedule
from enterprise.closeout.rwh_history import build as mine_history

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).with_name("source") / "industrial_tax_cohorts.json"


def validate_components(source, finance):
    """Tie independent component buckets to retained acquisition source amounts."""
    mapping = {
        "ARU-TRACK": "track_bridges_culverts",
        "ARU-TERMINAL": "terminals_warehouses",
        "ARU-MOBILE": "locomotives_trucks_equipment",
    }
    expected = {
        group: D(
            str(
                next(
                    r["fair_value"]
                    for r in finance["ppa_assets"]
                    if r["asset_class"] == asset_class
                )
            )
        )
        for group, asset_class in mapping.items()
    }
    expected["LEASE"] = D(str(finance["transaction"]["retained_leases"]))
    actual = defaultdict(D)
    ids = set()
    for row in source["aru_initial_components"]:
        if row["id"] in ids:
            raise ValueError("Duplicate acquired tax component")
        ids.add(row["id"])
        actual[row["book_group"]] += D(row["cost_usd"])
    if dict(actual) != expected:
        raise ValueError("Acquired tax component buckets differ from source asset population")


def validate_card_history(rows):
    """One paid tranche keeps identity, gross cost and one supported service gate."""
    keys = set()
    identity = None
    service = None
    for row in rows:
        key = (int(row["year"]), int(row["month"]))
        if key in keys:
            raise ValueError("Duplicate forecast tax asset period")
        keys.add(key)
        current = (row["entity"], row["project_id"], D(str(row["gross_usd"])))
        if identity is not None and current != identity:
            raise ValueError("Forecast paid tranche identity or cost changed")
        identity = current
        period = row["actual_conditional_service_period"]
        if row["asset_status"] == "CONSTRUCTION_IN_PROGRESS":
            if period not in {"", "NOT_IN_SERVICE", "NONE"} or service is not None:
                raise ValueError("Forecast CIP has an inconsistent service state")
        elif row["asset_status"] == "CONDITIONAL_IN_SERVICE":
            if period in {"", "NOT_IN_SERVICE", "NONE"}:
                raise ValueError("Forecast in-service asset lacks service period")
            actual_service = tuple(map(int, period.split("-")))
            if actual_service > key or (service is not None and actual_service != service):
                raise ValueError("Forecast service date is future or changes")
            service = actual_service
        else:
            raise ValueError("Unknown forecast tax asset status")


def build(forecast_result):
    source = json.loads(SOURCE.read_text())
    finance = json.loads((ROOT / "industrial/source/finance.json").read_text())
    operations = json.loads((ROOT / "industrial/source/operations.json").read_text())
    validate_components(source, finance)
    history = mine_history()
    cohorts = []

    def add(scenario, group, identifier, cost, year, month, life, ca_life, building=False, **extra):
        if D(str(cost)) < 0:
            raise ValueError("Negative asset cohort")
        cohorts.append(
            dict(
                scenario=scenario,
                group=group,
                asset_id=identifier,
                cost_usd=str(cost),
                service_year=year,
                service_month=month,
                life_years=life,
                ca_life_years=ca_life,
                building=building,
                **extra,
            )
        )

    for scenario in ("base", "downside", "expansion"):
        for row in source["aru_initial_components"]:
            add(
                scenario,
                "ARU_GROUP",
                row["id"],
                row["cost_usd"],
                2026,
                1,
                row["life_years"],
                row["ca_life_years"],
                row.get("building", False),
                lease=row["book_group"] == "LEASE",
            )
        if sum(
            D(r["cost_usd"]) for r in source["aru_initial_components"] if r["book_group"] != "LEASE"
        ) != D("34000000"):
            raise ValueError("ARU acquired depreciable allocation changed")
        for category in operations["catchup_capital"]:
            life, ca_life = source["catchup_classes"][category["category"]]
            for month in finance["forecast_2026"]["catchup_months"]:
                add(
                    scenario,
                    "ARU_GROUP",
                    f"{category['id']}-{month}",
                    D(category["amount_usd"]) / 10,
                    2026,
                    month,
                    life,
                    ca_life,
                    life == 39,
                )
        for month in range(1, 13):
            add(
                scenario,
                "ARU_GROUP",
                f"ARU-SUSTAIN-{month}",
                D(finance["forecast_2026"]["sustaining_capex"]) / 12,
                2026,
                month,
                7,
                10,
            )
        add(
            scenario,
            "ARU_GROUP",
            "ARU-INTERFACE",
            finance["forecast_2026"]["aru_interface_capex"],
            2026,
            7,
            7,
            10,
        )
        # The 2025 equipment/building allocation is independently reconstructed;
        # do not reuse the 59m book opening card as tax cost.
        initial = history["rows"][0]
        plant = D(initial["initial_plant_basis_usd"])
        equipment = plant * D(18) / 22
        add(scenario, "RWH_PS", "RW-ACQUIRED-EQUIPMENT", equipment, 2025, 7, 7, 10)
        add(scenario, "RWH_PS", "RW-ACQUIRED-BUILDING", plant - equipment, 2025, 7, 39, 39, True)
        add(scenario, "RWH_PS", "RW-H2-REHAB", 8000000, 2026, 1, 7, 10, acquisition_year=2025)
        for month in range(1, 13):
            add(
                scenario,
                "RWH_PS",
                f"RW-2026-SUSTAIN-REHAB-{month}",
                D(9000000) / 12,
                2026,
                month,
                7,
                10,
            )
        add(scenario, "RWH_PS", "RW-INTERFACE", 3250000, 2026, 7, 7, 10)
    assets = forecast_result["datasets"]["assets"]
    by_asset = defaultdict(list)
    for row in assets:
        if str(row["asset_id"]).startswith("CAPEX-"):
            by_asset[row["scenario"], row["asset_id"]].append(row)
    projects = {
        "": (7, 10),
        "MINE-CAPACITY": (7, 10),
        "RAIL-RESILIENCE": (7, 10),
        "TERMINAL-EXPANSION": (39, 39),
        "TRUCK-CAPACITY": (5, 8),
        "WAREHOUSE-CAPACITY": (39, 39),
    }
    for (scenario, identifier), rows in by_asset.items():
        rows.sort(key=lambda r: (int(r["year"]), int(r["month"])))
        validate_card_history(rows)
        active = next(
            (
                r
                for r in rows
                if r["actual_conditional_service_period"] not in {"", "NOT_IN_SERVICE", "NONE"}
                and r["asset_status"] == "CONDITIONAL_IN_SERVICE"
            ),
            None,
        )
        if active is None:
            # Unserved CIP remains a basis asset, not a deduction.
            active = rows[-1]
            service_year, service_month = 2032, 1
        else:
            service_year, service_month = map(
                int, active["actual_conditional_service_period"].split("-")
            )
        project = active["project_id"]
        if project not in projects:
            raise ValueError("Unclassified industrial project tax cohort")
        life, ca_life = projects[project]
        add(
            scenario,
            active["entity"],
            identifier,
            active["gross_usd"],
            service_year,
            service_month,
            life,
            ca_life,
            life == 39,
            project_id=project,
            acquisition_year=int(rows[0]["year"]),
        )
    grouped = defaultdict(list)
    for cohort in cohorts:
        grouped[cohort["scenario"], cohort["group"], cohort["service_year"]].append(cohort)
    rows = []
    totals = defaultdict(lambda: defaultdict(D))
    for cohort in cohorts:
        midquarter = quarterly_test(
            grouped[cohort["scenario"], cohort["group"], cohort["service_year"]]
        )
        for jurisdiction in ("US", "CA", "IL", "WV"):
            is_ca = jurisdiction == "CA"
            life = cohort["ca_life_years"] if is_ca else cohort["life_years"]
            charges = schedule(
                cohort["cost_usd"],
                cohort["service_year"],
                cohort["service_month"],
                life,
                bonus=jurisdiction in {"US", "WV"} and not cohort["building"],
                building=cohort["building"],
                straight_line=is_ca and not cohort["building"],
                mid_quarter=midquarter,
            )
            acquisition_year = cohort.get("acquisition_year", cohort["service_year"])
            prior_rows = [
                dict(
                    year=year,
                    opening_tax_basis_usd="0" if year == acquisition_year else cohort["cost_usd"],
                    tax_depreciation_usd="0",
                    closing_tax_basis_usd=cohort["cost_usd"],
                    convention="NOT_YET_IN_SERVICE",
                    bonus_selected=False,
                )
                for year in range(acquisition_year, min(cohort["service_year"], 2032))
            ]
            # Preserve precise historical ACT365 CA first-year equipment method.
            if is_ca and cohort["asset_id"] == "RW-ACQUIRED-EQUIPMENT":
                first = D(cohort["cost_usd"]) / 10 * D(167) / 365
                balance = D(cohort["cost_usd"])
                for charge in charges:
                    amount = (
                        first
                        if charge["year"] == 2025
                        else min(balance, D(cohort["cost_usd"]) / 10)
                    )
                    charge.update(
                        opening_tax_basis_usd=str(balance),
                        tax_depreciation_usd=str(amount),
                        closing_tax_basis_usd=str(balance - amount),
                        convention="HISTORICAL_ACT365_THEN_FULL_YEAR",
                    )
                    balance -= amount
            owners = (
                [("PS", D(1))]
                if cohort["group"] == "RWH_PS"
                else [
                    ("ARU", D(".4") if cohort.get("lease") else D(".45")),
                    ("BST", D(".6") if cohort.get("lease") else D(".55")),
                ]
            )
            for charge in prior_rows + charges:
                for entity, share in owners:
                    row = dict(
                        scenario=cohort["scenario"],
                        taxpayer=entity,
                        jurisdiction=jurisdiction,
                        asset_id=cohort["asset_id"],
                        service_year=cohort["service_year"],
                        service_month=cohort["service_month"],
                        gross_cost_usd=str(D(cohort["cost_usd"]) * share),
                        **charge,
                    )
                    for key in (
                        "opening_tax_basis_usd",
                        "tax_depreciation_usd",
                        "closing_tax_basis_usd",
                    ):
                        row[key] = str((D(charge[key]) * share).quantize(D(".0001")))
                        totals[cohort["scenario"], entity, jurisdiction, charge["year"]][key] += D(
                            row[key]
                        )
                    rows.append(row)
    return dict(rows=rows, cohorts=cohorts, totals=totals, source=source)
