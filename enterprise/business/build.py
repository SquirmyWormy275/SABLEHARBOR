"""Build causal Core business economics, preserved industrial integration and unit evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import zipfile
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path

from industrial.planning import enterprise, forecast, operating_model, transactions
from industrial.planning.legacy_adapter import legacy_snapshot
from industrial.tools.build_package import run_builders
from . import capital, exports, validation
from .model import BusinessModel, amount, money

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "enterprise/generated/business-v1"
DIST = ROOT / "enterprise/dist/v1.0.0"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def sources(model):
    paths = set()
    for directory in (
        ROOT / "enterprise/business",
        ROOT / "industrial/planning",
        ROOT / "industrial/source",
        ROOT / "industrial/tools",
        ROOT / "red_wash/source",
        ROOT / "red_wash/tools",
        ROOT / "src/sable_harbor",
    ):
        paths.update(
            p
            for p in directory.rglob("*")
            if p.is_file()
            and p.suffix in {".py", ".json"}
            and "tests" not in p.parts
            and "__pycache__" not in p.parts
        )
    paths.update(ROOT / p for p in model.policy["canonical_sources"])
    paths.add(ROOT / "uv.lock")
    return {str(p.relative_to(ROOT)): exports.file_hash(p) for p in sorted(paths)}


def replacement_bridge(baseline, result):
    """Full-population replacement is explicit, including induced treasury/close changes."""
    rows = []
    for origin, records in [
        ("PRIOR_V2", baseline["journal_rows"]),
        ("SUCCESSOR", result["journal_rows"]),
    ]:
        for r in records:
            if int(r["year"]) == 2026:
                if origin == "SUCCESSOR":
                    continue
                action = "RETAIN_2026"
                signed = D(r["signed_usd"])
            else:
                action = (
                    "REMOVE_PRIOR_FORECAST" if origin == "PRIOR_V2" else "ADD_SUCCESSOR_FORECAST"
                )
                signed = -D(r["signed_usd"]) if origin == "PRIOR_V2" else D(r["signed_usd"])
            rows.append(
                {
                    k: r[k]
                    for k in (
                        "scenario",
                        "entity",
                        "year",
                        "month",
                        "unit",
                        "account",
                        "source_id",
                        "journal_id",
                    )
                }
                | {
                    "bridge_action": action,
                    "source_signed_usd": r["signed_usd"],
                    "bridge_signed_usd": money(signed),
                }
            )
    # Old forecast + removal/addition equals new forecast; retained 2026 unchanged.
    keys = ["scenario", "entity", "year", "month", "account", "unit"]
    old = validation.total(baseline["journal_rows"], keys)
    delta = validation.total(
        [r for r in rows if r["bridge_action"] != "RETAIN_2026"], keys, "bridge_signed_usd"
    )
    combined = {k: old.get(k, D(0)) + delta.get(k, D(0)) for k in set(old) | set(delta)}
    if {k: v for k, v in combined.items() if v} != validation.total(result["journal_rows"], keys):
        raise ValueError("Removal/addition bridge does not reconstruct successor exactly")
    return rows


def analytical_views(result, model, baseline):
    comparisons = []
    lookup = {(r["scenario"], r["entity"], r["year"]): r for r in baseline["annual_rows"]}
    for row in result["annual_rows"]:
        previous = lookup[row["scenario"], row["entity"], row["year"]]
        comparisons.append(
            {k: row[k] for k in ("scenario", "entity", "year")}
            | {
                f"{k}_change": money(D(row[k]) - D(previous[k]))
                for k in ("revenue_usd", "expense_usd", "net_income_usd", "ending_cash_usd")
            }
        )
    fte = defaultdict(D)
    for position in model.roster:
        if position["occupied"]:
            for unit, fraction in position["assignments"].items():
                if unit != "corporate":
                    fte[unit] += D(fraction)
    fte["pale-sun"] = D(140)
    fte["american-resource-utility"] = D(131)
    units = {(r["scenario"], r["year"], r["unit"]): r for r in result["unit_annual_rows"]}
    allocations = []
    for scenario in model.policy["cases"]:
        for year in range(2027, 2032):
            corporate = units[scenario, year, "corporate"]
            pool = D(corporate["expense_usd"]) - D(corporate["revenue_usd"])
            allocated = D(0)
            items = list(fte.items())
            for index, (unit, weight) in enumerate(items):
                share = (
                    pool - allocated
                    if index == len(items) - 1
                    else amount(pool * weight / sum(fte.values()))
                )
                allocated += share
                r = units[scenario, year, unit]
                allocations.append(
                    {
                        "scenario": scenario,
                        "year": year,
                        "unit": unit,
                        "direct_income_usd": r["net_income_usd"],
                        "support_allocation_usd": money(share),
                        "after_support_income_usd": money(D(r["net_income_usd"]) - share),
                        "basis_fte": str(weight),
                        "allocation_pool_usd": money(pool),
                        "posting_state": "NONPOSTING_MANAGEMENT_VIEW; statutory intercompany fees already in direct books",
                        "workforce_basis": "2027 conditional Core assignments plus accepted 140/131 industrial population; not 2026 combined actual headcount",
                    }
                )
    quality = []
    for row in result["monthly_rows"]:
        if row["entity"] == "CONSOLIDATED" and int(row["month"]) == 12:
            goodwill = sum(
                D(r["signed_usd"])
                for r in result["legal_trial_balance_rows"]
                if r["scenario"] == row["scenario"]
                and r["year"] == row["year"]
                and r["month"] == 12
                and r["account"] == "LEG_1600"
            )
            quality.append(
                {
                    "scenario": row["scenario"],
                    "year": row["year"],
                    "reported_equity_usd": row["equity_usd"],
                    "unallocated_legacy_intangible_usd": money(goodwill),
                    "equity_excluding_legacy_intangible_usd": money(
                        D(row["equity_usd"]) - goodwill
                    ),
                    "adjustment_state": "NONPOSTING_QUALITY_OF_BALANCE_SHEET_VIEW",
                    "reason": "Retained $30M Core goodwill/intangible calibration is not substantiated by an invented acquisition.",
                }
            )
    return comparisons, allocations, quality


def build(output=OUT, *, allow_working_tree=False, package=True):
    output = Path(output)
    if output.resolve() != OUT.resolve():
        raise ValueError("Build uses its explicit generated output boundary")
    if output.exists():
        # Only this generator-owned directory may be replaced; arbitrary paths rejected above.
        shutil.rmtree(output)
    output.mkdir(parents=True)
    model = BusinessModel()
    revision = git("rev-parse", "HEAD")
    initial = sources(model)
    dirty = bool(git("status", "--porcelain"))
    if dirty and not allow_working_tree:
        raise ValueError("Release requires clean source; use --allow-working-tree for development")
    print("Building physical industrial anchors and business events", flush=True)
    run_builders(ROOT)
    model.build()
    business_validation = validation.business(model)
    operations = operating_model.build(output / "industrial/operations")
    finances = forecast.build(
        output / "industrial/forecast", operating_rows=operations["operating_rows"]
    )
    evidence = transactions.build(
        output / "industrial/transactions",
        operating_rows=operations["operating_rows"],
        forecast=finances,
    )
    print(
        "Executing the preserved legacy source once for both comparison and successor", flush=True
    )
    legacy = legacy_snapshot()
    baseline = enterprise.build(
        output / "comparison/v2", forecast_result=finances, legacy_result=legacy
    )
    policy = json.loads(enterprise.SOURCE.read_text())
    policy = copy.deepcopy(policy)
    policy["model_id"] = "SH-ENTERPRISE-BUSINESS-V3"
    policy["schema_version"] = "3.0.0"
    policy["knowledge_cutoff"] = model.policy["available_at"]
    policy["created_on"] = model.policy["as_of"]
    policy["core"]["payment_deferral_accounts"] = {
        "OPERATING": "CORE_UNPAID",
        "INVESTING": "BIZ_CAPITAL_UNPAID",
        "FINANCING": "BIZ_DEBT_UNPAID",
    }
    policy["canonical_sources"] = list(
        dict.fromkeys(policy["canonical_sources"] + model.policy["canonical_sources"])
    )
    print(
        "Replacing Core forecast operations; retaining existing assets, debt and legal consolidation",
        flush=True,
    )
    result = enterprise.build(
        output / "enterprise",
        forecast_result=finances,
        legacy_result=legacy,
        source=policy,
        core_provider=model,
    )
    integrated = validation.enterprise(result, baseline, model)
    bridge = replacement_bridge(baseline, result)
    exports.write_csv(output / "replacement_bridge.csv", bridge)
    comparisons, allocations, quality = analytical_views(result, model, baseline)
    for name, rows in [
        ("scenario_comparison", comparisons),
        ("support_allocation", allocations),
        ("quality_of_balance_sheet", quality),
    ]:
        exports.write_csv(output / (name + ".csv"), rows)
    mine, closure = capital.calculate(model.inputs["capital_cases"])
    exports.write_csv(output / "capital/mine_upgrade.csv", mine)
    exports.write_csv(output / "capital/closure_sensitivity.csv", closure)
    for name, rows in model.tables.items():
        exports.write_csv(output / "business" / (name + ".csv"), rows)
    source_hash = hashlib.sha256(json.dumps(initial, sort_keys=True).encode()).hexdigest()
    identity = {
        "run_id": result["summary"]["run_id"],
        "source_revision": revision,
        "canon_source_revision": revision,
        "business_input_sha256": model.input_hash,
        "source_snapshot_sha256": source_hash,
        "source_files": initial,
        "source_policy": policy,
        "legacy_generation_identity": legacy["metadata"],
        "scenarios": list(model.policy["cases"]),
        "periods": "2026 retained reconstruction; 2027-2031 conditional forecasts",
        "dirty_development_build": dirty,
    }
    (output / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    print("Exporting seven allowlisted unit databases and audit workbooks", flush=True)
    packages = exports.unit_packages(output / "units", model, result, evidence["tables"], identity)
    counts = validation.unit_exports(output / "units", packages)
    report = {
        "status": "PASS",
        "business": business_validation,
        "enterprise": integrated,
        "unit_table_counts": counts,
        "source_identity": identity["run_id"],
        "limitations": [
            "2026 legacy Core remains an explicit preserved calibration.",
            "Conditional staff occupancy, prices, measurements, chemistry and future contracts are not locked historical facts.",
            "Treasury separately defers operating, capital and debt cash requests when finite funding is exhausted; the infeasible plan is not operating authorization or a bank statement.",
            "Industrial service/payroll evidence retains its disclosed allocation/reconstruction granularity.",
            "Exact custody qualification, sites, legal tax treatment, carry economics and production Atlas runtime remain separately gated.",
            "Mine upgrade/closure support sensitivities are standalone conditional cases and do not change approved engineering or booked industrial ARO.",
        ],
    }
    (output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    if initial != sources(model) or revision != git("rev-parse", "HEAD"):
        raise ValueError("Source changed during build; repeat from a stable checkout")
    artifacts = {
        str(p.relative_to(output)): exports.file_hash(p)
        for p in sorted(output.rglob("*"))
        if p.is_file()
    }
    manifest = {
        "version": "1.0.0",
        "classification": "PUBLIC_SYNTHETIC_CONDITIONAL_FORECAST",
        "identity": identity,
        "validation": "validation.json",
        "artifacts": artifacts,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    checks = {**artifacts, "manifest.json": exports.file_hash(output / "manifest.json")}
    (output / "SHA256SUMS.txt").write_text(
        "".join(f"{h}  {p}\n" for p, h in sorted(checks.items()))
    )
    validation.verify_files(output)
    if package:
        DIST.mkdir(parents=True, exist_ok=True)
        archive = DIST / "sable-harbor-business-finance-v1.0.0.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
            for p in sorted(output.rglob("*")):
                if p.is_file():
                    info = zipfile.ZipInfo(str(p.relative_to(output)), (2026, 9, 9, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    bundle.writestr(info, p.read_bytes())
        (DIST / "SHA256SUMS.txt").write_text(
            exports.file_hash(archive) + "  " + archive.name + "\n"
        )
        report["archive"] = str(archive.relative_to(ROOT))
    print(
        json.dumps(
            {
                "status": "PASS",
                "business_events": len(model.tables["events"]),
                "enterprise_lines": len(result["journal_rows"]),
                "units": list(packages),
                "source_revision": revision,
                "archive": report.get("archive"),
            },
            indent=2,
        ),
        flush=True,
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-working-tree", action="store_true")
    parser.add_argument("--skip-package", action="store_true")
    args = parser.parse_args()
    build(allow_working_tree=args.allow_working_tree, package=not args.skip_package)


if __name__ == "__main__":
    main()
