"""Build a separate runtime enterprise successor and exact predecessor statement bridge."""

import argparse
import hashlib
import json
import subprocess
from decimal import Decimal as D
from enterprise.operations.model import OperatingModel
from enterprise.operations.build import enterprise_policy
from collections import defaultdict
from industrial.planning import enterprise, forecast, operating_model
from industrial.planning.legacy_adapter import legacy_snapshot
from industrial.tools.build_package import run_builders
from . import model
from .finance import RuntimeAdjustment, verify_land_adjustment

ROOT = model.ROOT
OUT = ROOT / "enterprise/generated/runtime-v1"


def replacement_bridge(before, after):
    keys = ("scenario", "entity", "year", "month", "account", "unit")
    bridge = []
    combined = defaultdict(D)
    expected = defaultdict(D)
    for row in before["journal_rows"]:
        key = tuple(row[k] for k in keys)
        combined[key] += D(row["signed_usd"])
        if int(row["year"]) > 2026:
            combined[key] -= D(row["signed_usd"])
            bridge.append(
                {k: row[k] for k in keys}
                | {
                    "action": "REMOVE_PRIOR_FORECAST",
                    "signed_usd": str(-D(row["signed_usd"])),
                    "source_id": row["source_id"],
                }
            )
    for row in after["journal_rows"]:
        key = tuple(row[k] for k in keys)
        expected[key] += D(row["signed_usd"])
        if int(row["year"]) > 2026 or row["source_id"] in {"RT-LAND-20260904", "SH-VOICE-GW-01"}:
            combined[key] += D(row["signed_usd"])
            bridge.append(
                {k: row[k] for k in keys}
                | {
                    "action": ("ADD_GOODWILL_OPENING_CORRECTION" if row["source_id"] == "SH-VOICE-GW-01" else "ADD_RUNTIME_LAND_OVERLAY")
                    if int(row["year"]) == 2026
                    else "ADD_SUCCESSOR_FORECAST",
                    "signed_usd": row["signed_usd"],
                    "source_id": row["source_id"],
                }
            )
    if {k: v for k, v in combined.items() if v} != {
        k: v for k, v in expected.items() if v
    }:
        raise ValueError("Runtime bridge does not reconstruct enterprise successor")
    return bridge


def build(allow_working_tree=False, *, company_closeout=False):
    output = ROOT / "enterprise/generated/company-closeout-v1" if company_closeout else OUT
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    dirty = bool(
        subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True
        ).strip()
    )
    if dirty and not allow_working_tree:
        raise ValueError(
            "Runtime release requires clean source; development needs --allow-working-tree"
        )
    source = model.load()
    model.validate(source, ROOT)
    from enterprise.operations.build import sources as operating_sources

    def snapshot():
        result = operating_sources(OperatingModel())
        for p in sorted((ROOT / "enterprise/runtime").rglob("*")):
            if (
                "tests" not in p.parts
                and p.suffix in {".py", ".json"}
                and "publications" not in p.parts
                and "visuals" not in p.parts
            ):
                result[str(p.relative_to(ROOT))] = hashlib.sha256(
                    p.read_bytes()
                ).hexdigest()
        for relative in model.FILES.values():
            result[relative] = hashlib.sha256(
                (ROOT / relative).read_bytes()
            ).hexdigest()
        return result

    if company_closeout:
        original_snapshot = snapshot
        def snapshot():
            result = original_snapshot()
            from enterprise.operations.completed_period import build as completed_source
            result.update(completed_source()["source_hashes"])
            for rel in ["enterprise/ccf/company_closeout/industrial_transaction_tax.json", "red_wash/source/core_operating_data.json"]:
                result[rel] = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
            for p in sorted((ROOT / "enterprise/closeout").rglob("*")):
                if p.suffix in {".py", ".json"}:
                    result[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
            p = ROOT / "industrial/planning/enterprise.py"
            result[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
            return result
    source_snapshot = snapshot()
    initial = model.export(source)["source_sha256"]
    output.mkdir(parents=True, exist_ok=True)
    print(
        "Building runtime successor from retained operations and industrial sources",
        flush=True,
    )
    run_builders(ROOT)
    op = operating_model.build(output / "industrial/operations")
    fin = forecast.build(
        output / "industrial/forecast", operating_rows=op["operating_rows"]
    )
    legacy = legacy_snapshot()
    operating = OperatingModel().build()
    predecessor = enterprise.build(
        output / "predecessor",
        forecast_result=fin,
        legacy_result=legacy,
        source=enterprise_policy(operating, 4),
        core_provider=operating,
    )
    policy = enterprise_policy(operating, 5)
    policy.update(
        model_id="SH-ENTERPRISE-RUNTIME-V1",
        schema_version="5.0.0",
        knowledge_cutoff="2026-09-11",
        created_on="2026-09-11",
    )
    policy["canonical_sources"] += list(model.FILES.values())
    policy["core"]["additional_deferrable_source_types"] = [
        "RUNTIME_CONDITIONAL_FORECAST_REQUEST"
    ]
    adjustment = RuntimeAdjustment(source)
    if company_closeout:
        from enterprise.closeout.finance import CloseoutAdjustment
        adjustment = CloseoutAdjustment(source)
        adjustment.legacy_equipment_correction = True
        adjustment.payroll_legal_correction = True
        from enterprise.closeout.state_minimum import StateMinimum
        adjustment.state_minimum = StateMinimum()
        from enterprise.closeout.software_sales_tax import SoftwareTax
        adjustment.software_tax=SoftwareTax(operating)
        policy.update(model_id="SH-COMPANY-CLOSEOUT-V1", schema_version="6.0.0",
                      knowledge_cutoff="2026-09-15", created_on="2026-09-15")
        policy["canonical_sources"] += ["enterprise/closeout/source/adjustments.json"]
        policy["legacy_adapter"]["calibration_boundary"] = "Preserved legacy calibration; dated successor removes $30M unsupported Core goodwill against initialization equity. ARU allocation remains separate."
        policy["core"]["tax_boundary"] = "Owner adopted corporate-from-formation history; parent provision follows separately versioned closeout tax workpapers; historical sources retain omission disclosures."
    successor = enterprise.build(
        output / "enterprise",
        forecast_result=fin,
        legacy_result=legacy,
        source=policy,
        core_provider=operating,
        adjustment_provider=adjustment,
    )
    if company_closeout:
        from enterprise.closeout.industrial_tax import IndustrialTax
        adjustment.industrial_tax = IndustrialTax(successor)
        from enterprise.closeout.rwh_book import RwhBook
        adjustment.rwh_book = RwhBook(successor, fin, enterprise.load_anchor())
        successor = enterprise.build(output / "enterprise", forecast_result=fin, legacy_result=legacy,
            source=policy, core_provider=operating, adjustment_provider=adjustment)
        from enterprise.closeout.parent_tax import ParentTax
        tax = ParentTax(successor, legacy, operating)
        enterprise.write_csv(output / "before_parent_tax_statements.csv", successor["annual_rows"])
        enterprise.write_csv(output / "before_parent_tax_monthly.csv", successor["monthly_rows"])
        adjustment.parent_tax = tax
        adjustment.input_hash = hashlib.sha256((adjustment.input_hash + tax.input_hash).encode()).hexdigest()
        successor = enterprise.build(output / "enterprise", forecast_result=fin,
            legacy_result=legacy, source=policy, core_provider=operating, adjustment_provider=adjustment)
        enterprise.write_csv(output / "rwh_book_carrying.csv", adjustment.rwh_book.rows)
        enterprise.write_csv(output / "rwh_historical_tax.csv", adjustment.rwh_book.history["rows"])
        enterprise.write_csv(output / "state_minimum_tax.csv", adjustment.state_minimum.rows)
        enterprise.write_csv(output / "industrial_sales_tax.csv", adjustment.industrial_tax.rows)
        enterprise.write_csv(output / "parent_tax_provision.csv", tax.rows)
        enterprise.write_csv(output / "parent_tax_assets.csv", tax.asset_rows)
        enterprise.write_csv(output / "software_sales_tax.csv", adjustment.software_tax.rows)
        enterprise.write_csv(output / "software_tax_customer_population.csv", adjustment.software_tax.population)
        enterprise.write_csv(output / "historical_tax_events.csv", tax.history["events"])
        enterprise.write_csv(output / "historical_tax_annual.csv", tax.history["annual"])
        (output / "parent_tax_history.json").write_text(json.dumps({"source": tax.source,
            "supported_historical_income": tax.historical_income,
            "supported_opening_nol_usd": str(tax.opening_nol)}, indent=2) + "\n")
    rows = enterprise.read_csv(output / "enterprise/enterprise_journal.csv")
    check = verify_land_adjustment(rows)
    if company_closeout:
        from enterprise.closeout.industrial_tax import august_receipt_workpaper
        from enterprise.operations.completed_period import build as completed_edition
        receipt_tax, receipt_bridge = august_receipt_workpaper(completed_edition())
        enterprise.write_csv(output / "rwh_august_collected_tax.csv", receipt_tax)
        enterprise.write_csv(output / "rwh_august_return_bridge.csv", receipt_bridge)
        from enterprise.closeout.receipt_markets import allocate as receipt_markets
        enterprise.write_csv(output / "receipt_markets.csv", receipt_markets(rows))
        from enterprise.closeout.finance import verify
        check["company_closeout"] = verify(rows)
        check["industrial_sales_tax"] = adjustment.industrial_tax.verify(rows)
        check["software_sales_tax"] = adjustment.software_tax.verify(rows)
    if company_closeout:
        from enterprise.closeout.statement_bridge import bridge as company_bridge
        bridge = company_bridge(predecessor, successor)
    else:
        bridge = replacement_bridge(predecessor, successor)
    from .construction_finance import phase_reconciliation, asset_forecast

    enterprise.write_csv(
        output / "construction_budget_bridge.csv", phase_reconciliation(source)
    )
    enterprise.write_csv(
        output / "owned_asset_acceptance_sensitivity.csv", asset_forecast(source)
    )
    enterprise.write_csv(output / "runtime_statement_bridge.csv", bridge)
    # The accepted historical journals must survive byte-for-field outside adjustment identity dates.
    before = enterprise.read_csv(output / "predecessor/enterprise_journal.csv")
    fields = (
        "scenario",
        "entity",
        "year",
        "month",
        "account",
        "signed_usd",
        "source_id",
        "source_type",
        "description",
        "cash_flow",
        "segment",
    )

    if company_closeout:
        # The new reciprocal payroll clearing has one precisely bounded derived elimination.
        for scenario in ["base", "downside", "expansion"]:
            for account, delta in [("1150", D(-78125)), ("2150", D(78125))]:
                def elimination_value(population):
                    selected = [r for r in population if r["scenario"] == scenario and r["entity"] == "ELIM"
                        and int(r["year"]) == 2026 and int(r["month"]) == 8 and r["source_id"] == "1150"
                        and r["source_type"] == "BALANCE_ELIMINATION" and r["account"] == account]
                    if len(selected) != 1:
                        raise ValueError("Payroll clearing elimination population differs")
                    return D(selected[0]["signed_usd"])
                if elimination_value(rows) - elimination_value(before) != delta:
                    raise ValueError("Payroll clearing elimination differs from reciprocal 78125 correction")

    def history(records):
        return sorted(
            tuple(r[k] for k in fields)
            for r in records
            if int(r["year"]) == 2026 and not r["source_id"].startswith("RT-")
            and r["source_id"] != "SH-VOICE-GW-01"
            and not (company_closeout and r["entity"] == "ELIM" and int(r["year"]) == 2026 and int(r["month"]) == 8 and r["source_id"] == "1150" and r["source_type"] == "BALANCE_ELIMINATION" and r["account"] in {"1150", "2150"})
            and not (company_closeout and (r["source_id"].startswith(("CO-TAX-", "CO-ASSET-", "CO-PAYROLL-", "SH-RWH-IL-ROT-", "CO-STATE-", "CO-RWH-BOOK-")) or r["source_type"] == "MEMBER_EQUITY"))
        )

    if history(before) != history(rows):
        raise ValueError(
            "Runtime changed preserved 2026 journals outside explicit land overlay"
        )
    if (
        model.export(model.load())["source_sha256"] != initial
        or snapshot() != source_snapshot
        or revision
        != subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    ):
        raise ValueError("Runtime sources changed during build")
    identity = {
        "source_revision": revision,
        "runtime_source_sha256": initial,
        "dirty_development_build": dirty,
        "source_files": source_snapshot,
        "classification": "SYNTHETIC_SUCCESSOR_NOT_REAL_PAYMENTS",
        "land": check,
        "limitations": [
            "Settlement clearing is unresolved, not vendor financing.",
            *(["Corporate-from-formation tax history adopted; current provision and cash plan are modeled. Tax asset-basis/apportionment reservations and exact holder rights remain disclosed."] if company_closeout else []),
            "Future expenses and IT acceptance are conditional scenarios, not actual occupied employees or operations.",
            "Construction remains CIP; no building/plant in-service event is fabricated.",
            "Runtime delayed-build sensitivity is separate from the three consolidated enterprise scenarios.",
        ],
    }
    (output / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    (output / "runtime.json").write_text(json.dumps(model.export(source), indent=2) + "\n")
    if company_closeout:
        from enterprise.closeout.report import report
        from enterprise.closeout.tax_sensitivity import run as tax_sensitivity
        tax_sensitivity(output)
        from enterprise.closeout.treasury import build as treasury
        treasury(output)
        from enterprise.closeout.exports import build as company_exports
        company_exports(output, operating, successor, op, fin, bridge, identity)
        report(output)
        from enterprise.closeout.tax_calendar import build as tax_calendar
        enterprise.write_csv(output / "tax_filing_register.csv", tax_calendar())
    inventory = {
        str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(output.rglob("*"))
        if p.is_file() and p.name != "manifest.json"
    }
    (output / "manifest.json").write_text(json.dumps(inventory, indent=2) + "\n")
    print(
        json.dumps(
            {k: v for k, v in identity.items() if k != "source_files"}, indent=2
        ),
        flush=True,
    )
    return identity


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-working-tree", action="store_true")
    build(parser.parse_args().allow_working_tree)
