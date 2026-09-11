"""Validate and export the September 2026 runtime successor independently of v1 services."""

from __future__ import annotations

import argparse
import copy
from datetime import date
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = {
    "sites": "enterprise/services/source/runtime_sites_2026-09-11.json",
    "capital": "enterprise/services/source/runtime_capital_plan_2026-09-11.json",
}
SELECTIONS = {
    "RUNTIME-RENO-COLO": ("Switch", "CP-SWITCH"),
    "RUNTIME-BOISE-DR": ("IDACORE", "CP-IDACORE"),
}
CROSSWALK = {
    "RUNTIME-RENO-COLO": ("FAC-PRIMARY", "SH-SITE-0028", "DEP-colo-primary"),
    "RUNTIME-BOISE-DR": ("FAC-RECOVERY", "SH-SITE-0029", "DEP-colo-recovery"),
    "RUNTIME-NN-OWNED-DC": ("FAC-OWNED", "SH-SITE-0030", None),
}
COMMON_FIELDS = "id name geography status operating entity_id geospatial_entity_id facility_id geospatial_site_id planned_environment_ids dependency_id record_origin installed_capacity_kw".split()
COLO_FIELDS = "provider facility provider_selection_date contract_executed capacity_reserved initial_usable_it_kw_low initial_usable_it_kw_high evidence_boundary provider_id contract_id contract_status provider_legal_name".split()
OWNED_FIELDS = "planning_lon_lat fictionality parcel_acres_planning real_apn planning_purchase_date planning_consideration_usd vertical_construction_percent commissioned_it_kw commissioned_critical_kw planned_shell_sqft_low planned_shell_sqft_high planned_initial_critical_kw_low planned_initial_critical_kw_high planned_utility_path_kw preserve_expansion_path_kw".split()


def fields(record, names):
    if set(record) != set(names):
        raise ValueError(
            f"Runtime schema fields: missing={set(names) - set(record)}, unknown={set(record) - set(names)}"
        )


def load(repository=ROOT, service_source=None):
    paths = {k: Path(repository) / v for k, v in FILES.items()}
    if service_source is not None:
        paths = {k: Path(service_source) / p.name for k, p in paths.items()}
    present = [p.is_file() for p in paths.values()]
    if not any(present):
        return None  # Explicit legacy source directories remain usable.
    if not all(present):
        raise ValueError("Incomplete runtime source pair")
    return {k: json.loads(p.read_text()) for k, p in paths.items()}


def _numbers(value, path="runtime"):
    """Reject nonfinite JSON numbers and booleans in quantity fields."""
    import math

    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(item, (dict, list)) and any(
                x in key
                for x in ("_kw", "_usd", "_percent", "_acres", "_sqft", "_months")
            ):
                if item is not None and (
                    type(item) not in (int, float)
                    or not math.isfinite(item)
                    or item < 0
                ):
                    raise ValueError(f"Invalid nonnegative quantity {path}.{key}")
            _numbers(item, f"{path}.{key}")
    elif isinstance(value, list):
        for item in value:
            _numbers(item, path)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"Nonfinite value in {path}")


def validate(data, repository=None):
    from jsonschema import Draft202012Validator

    schema = json.loads((ROOT / "enterprise/runtime/source_schema.json").read_text())
    errors = sorted(
        Draft202012Validator(schema).iter_errors(data), key=lambda e: str(list(e.path))
    )
    if errors:
        raise ValueError(f"Runtime schema {list(errors[0].path)}: {errors[0].message}")
    _numbers(data)
    fields(data, FILES)
    fields(
        data["sites"],
        "schema_version as_of state_rule sites repository_acceptance recorded_on".split(),
    )
    fields(
        data["capital"],
        "schema_version as_of state owned_site central_it_design_kw construction_truth accounting_rules recorded_on reference_cases_state implementation_assumptions".split(),
    )
    for name in FILES:
        if data[name]["schema_version"] != "1.0.0":
            raise ValueError(f"Unsupported runtime schema: {name}")
        for field in ("as_of", "recorded_on"):
            if date.fromisoformat(data[name][field]) != date(2026, 9, 11):
                raise ValueError("Runtime source cutoff must remain explicit")
    rows = data["sites"]["sites"]
    ids = [s["id"] for s in rows]
    if len(set(ids)) != len(ids) or set(ids) != set(SELECTIONS) | {
        "RUNTIME-NN-OWNED-DC"
    }:
        raise ValueError("Duplicate or missing runtime site")
    for field in ("facility_id", "geospatial_site_id"):
        if len({s[field] for s in rows}) != len(rows):
            raise ValueError(f"Duplicate runtime crosswalk: {field}")
    for site in rows:
        if (
            tuple(
                site[k] for k in ("facility_id", "geospatial_site_id", "dependency_id")
            )
            != CROSSWALK[site["id"]]
        ):
            raise ValueError("Runtime stable-ID crosswalk conflict")
        extra = (
            (
                COLO_FIELDS
                + (
                    ["required_expansion_kw"]
                    if site["id"] == "RUNTIME-RENO-COLO"
                    else "street_address published_planning_price_usd_per_kw_month published_power_included published_standard_term_months independence_required independence_verified independence_evidence".split()
                )
            )
            if site["id"] in SELECTIONS
            else OWNED_FIELDS
        )
        fields(site, COMMON_FIELDS + extra)
        for key in ("name", "geography", "status", "record_origin"):
            if not isinstance(site[key], str) or not site[key].strip():
                raise ValueError(f"Missing runtime description {key}")
        if not isinstance(site["planned_environment_ids"], list) or len(
            set(site["planned_environment_ids"])
        ) != len(site["planned_environment_ids"]):
            raise ValueError("Invalid environment references")
        if site["entity_id"] != "SHI" or site["geospatial_entity_id"] != "SH-ENT-001":
            raise ValueError("Runtime must use the existing legal parent")
        if site["operating"] is not False or site["installed_capacity_kw"] is not None:
            raise ValueError(
                "Design input cannot assert installed or operating capacity"
            )
        if site["id"] in SELECTIONS:
            if (site["provider"], site["provider_id"]) != SELECTIONS[site["id"]]:
                raise ValueError("Selected provider substitution conflicts with canon")
            if (
                site["contract_executed"] is not False
                or site["capacity_reserved"] is not False
            ):
                raise ValueError(
                    "Selection does not execute contracts or reserve capacity"
                )
            if (
                site["contract_status"] != "DRAFT"
                or site["provider_legal_name"] is not None
            ):
                raise ValueError(
                    "Contracting entity and execution require separate evidence"
                )
            if date.fromisoformat(site["provider_selection_date"]) > date.fromisoformat(
                data["sites"]["as_of"]
            ):
                raise ValueError("Future selection cannot be current")
            if site["initial_usable_it_kw_low"] > site["initial_usable_it_kw_high"]:
                raise ValueError("Reversed capacity envelope")
    sites = {s["id"]: s for s in rows}
    boise = sites["RUNTIME-BOISE-DR"]
    if (
        boise["independence_required"] is not True
        or boise["independence_verified"] is not False
        or boise["independence_evidence"]
    ):
        raise ValueError("Provider diversity is not verified recoverability")
    owned = sites["RUNTIME-NN-OWNED-DC"]
    if owned["real_apn"] is not None or owned["planning_lon_lat"] != [-119.455, 39.545]:
        raise ValueError("Synthetic planning anchor cannot claim cadastral precision")
    if (
        owned["parcel_acres_planning"] != 7.5
        or owned["planning_purchase_date"] != "2026-09-04"
    ):
        raise ValueError("Land decision conflict")
    if any(
        owned[k] != 0
        for k in (
            "vertical_construction_percent",
            "commissioned_it_kw",
            "commissioned_critical_kw",
        )
    ):
        raise ValueError("September owned site is preconstruction")
    costs = data["capital"]["owned_site"]
    buckets = (
        "land_usd",
        "site_civil_security_usd",
        "shell_support_building_usd",
        "utility_fiber_backbone_usd",
        "initial_critical_plant_usd",
        "engineering_permitting_contingency_usd",
    )
    fields(
        costs,
        (
            *buckets,
            "phase_1_total_usd",
            "range_total_usd_low",
            "range_total_usd_high",
            "production_it_hardware_included",
        ),
    )
    if costs["production_it_hardware_included"] is not False:
        raise ValueError("Production IT is outside the approved facility envelope")
    if (
        sum(costs[k] for k in buckets) != costs["phase_1_total_usd"]
        or costs["phase_1_total_usd"] != 15500000
    ):
        raise ValueError("Phase I must reconcile to $15.5M inclusive of land")
    if (
        costs["land_usd"] != owned["planning_consideration_usd"]
        or costs["land_usd"] != 3000000
    ):
        raise ValueError("Land amount does not reconcile")
    from . import planning

    planning.validate(data["capital"]["implementation_assumptions"], costs)
    truth = data["capital"]["construction_truth"]
    if any(type(v) is not bool for v in truth.values()):
        raise ValueError("Construction truth requires typed boolean fields")
    if truth != dict(
        land_acquired=True,
        vertical_construction_started=False,
        shell_complete=False,
        critical_plant_ordered=False,
        critical_plant_commissioned=False,
        production_operating=False,
    ):
        raise ValueError("Construction state cannot be promoted from forecasts")
    if repository:
        entity_path = Path(repository) / "industrial/source/entities.json"
        if not entity_path.is_file():
            raise ValueError(
                "Missing repository source: industrial/source/entities.json"
            )
        entities = json.loads(entity_path.read_text())["entities"]
        parent = next(e for e in entities if e["entity_id"] == "SHI")
        if parent["legal_name"] != "Sable Harbor, LLC":
            raise ValueError("Runtime legal identity conflict")
        components = json.loads(
            (
                Path(repository) / "enterprise/services/source/components.json"
            ).read_text()
        )["components"]
        known_components = {c["id"] for c in components}
        for site in rows:
            if not set(site["planned_environment_ids"]) <= known_components:
                raise ValueError("Unknown logical environment")
        native_services = json.loads(
            (Path(repository) / "enterprise/services/source/services.json").read_text()
        )["services"]
        native_ids = {r[0] for r in native_services}
        direction = data["capital"]["implementation_assumptions"]["technical_design"][
            "enterprise_vendor_direction"
        ]
        if (
            not (Path(repository) / direction["authority"]).is_file()
            or not {r["service_id"] for r in direction["bindings"]} <= native_ids
        ):
            raise ValueError(
                "Missing vendor authority or unknown vendor service binding"
            )

        for service in data["capital"]["implementation_assumptions"][
            "technical_design"
        ]["recovery_services"]:
            if service["service_id"] not in native_ids:
                raise ValueError(
                    "Recovery service must reference the existing service catalog"
                )
        import re

        control_text = (
            Path(repository) / "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md"
        ).read_text()
        objective_text = (
            Path(repository) / "docs/controls/CCF_CONTROL_OBJECTIVES_v0.1.md"
        ).read_text()
        risk_text = (
            Path(repository)
            / "docs/controls/CCF_RISK_CONTROL_TRACEABILITY_MATRIX_v0.1.md"
        ).read_text()
        for control in data["capital"]["implementation_assumptions"][
            "control_implementations"
        ]:
            if control["control_id"] not in set(
                re.findall(r"SH-[A-Z]+-\d{3}", control_text)
            ):
                raise ValueError("Unknown native CCF control")
            if control["objective_id"] not in objective_text or any(
                r not in risk_text for r in control["risk_ids"]
            ):
                raise ValueError("Unknown objective/risk relationship")
            if not (
                Path(repository) / control["procedure_reference"].split("#")[0]
            ).is_file():
                raise ValueError("Missing implementation procedure")
    return {
        "schema_version": "1.0.0",
        "sites": len(rows),
        "operating_effectiveness": "NOT_ASSERTED",
    }


def world_state(data, as_of="2026-09-11", known_on=None):
    """No system clock and no forecast-to-actual promotion."""
    cutoff = date.fromisoformat(as_of)
    known = date.fromisoformat(known_on) if known_on else None
    result = []
    for site in data["sites"]["sites"]:
        effective = site.get(
            "planning_purchase_date", site.get("provider_selection_date")
        )
        if date.fromisoformat(effective) > cutoff:
            continue
        if known and date.fromisoformat(data["sites"]["recorded_on"]) > known:
            continue
        result.append(copy.deepcopy(site))
    return result


def apply_services(data, runtime):
    """Decorate current registers without changing the frozen six-file cost model."""
    validate(runtime)
    components = {c["id"]: c for c in data["components"]["components"]}
    dependencies = {d["id"]: d for d in data["counterparties"]["dependencies"]}
    for site in runtime["sites"]["sites"]:
        component = components[site["facility_id"]]
        component.update(
            runtime_id=site["id"],
            location=site["geography"],
            state=site["status"],
            planned_canonical_site_id=site["geospatial_site_id"],
        )
        if "provider_id" in site:
            party = dict(
                id=site["provider_id"],
                name=site["provider"],
                kind="REAL_EXTERNAL_PROVIDER",
                identity_status="BRAND_SELECTED_LEGAL_PARTY_UNVERIFIED",
                source="runtime",
                contract_status="DRAFT",
                scope=site["facility"],
            )
            data["counterparties"]["counterparties"].append(party)
            dependencies[site["dependency_id"]].update(
                provider_id=site["provider_id"],
                lifecycle_state=site["status"],
                contracting_entity="SHI",
                contracting_entity_state="EXISTING_PARENT",
                proposed_agreement_id=site["contract_id"],
            )
            for env in site["planned_environment_ids"]:
                components[env].update(
                    planned_runtime_id=site["id"],
                    planned_provider_id=site["provider_id"],
                )
    components["FAC-ALEXANDRIA"].update(
        planned_runtime_id="RUNTIME-RENO-COLO",
        planned_successor_runtime_id="RUNTIME-NN-OWNED-DC",
        placement_state="PLANNED_NOT_INSTALLED",
        location="Tahoe-Reno, Nevada (planned transition)",
        state="PROVIDER_SELECTED_PROCUREMENT_PENDING",
    )


def export(data):
    validate(data)
    from . import planning, temporal, readiness, design, construction_finance

    assumptions = data["capital"]["implementation_assumptions"]
    return {
        "version": "1.0.0",
        "state": "SYNTHETIC_DESIGN_NOT_OPERATIONAL",
        "repository_acceptance": data["sites"]["repository_acceptance"],
        "readiness": readiness.load(),
        "sites": world_state(data),
        "capital": copy.deepcopy(data["capital"]),
        "construction": temporal.construction(
            temporal.baseline_events(data), "2026-09-11", "2026-09-11"
        ),
        "contract_covers": [
            {
                "contract_id": s["contract_id"],
                "site_name": s["name"],
                "customer_entity": s["entity_id"],
                "provider_brand": s["provider"],
                "facility": s["facility"],
                "state": s["contract_status"],
                "executed": s["contract_executed"],
            }
            for s in data["sites"]["sites"]
            if s["id"] in SELECTIONS
        ],
        "capacity": [
            planning.capacity(assumptions, year, scenario, recovery)
            for scenario in assumptions["scenarios"]
            for year in (2027, 2031, 2036)
            for recovery in (False, True)
        ],
        "technical_design": design.export(assumptions),
        "workforce": {
            "colo": planning.workforce(assumptions),
            "owned": planning.workforce(assumptions, True),
        },
        "finance": planning.finance(data),
        "investment_comparison": planning.investment(data),
        "construction_finance_bridge": construction_finance.phase_reconciliation(data),
        "commercial_cash_cases": construction_finance.commercial_cash_cases(data),
        "owned_asset_acceptance_sensitivity": construction_finance.asset_forecast(data),
        "source_sha256": hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "build"])
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--database", action="store_true")
    args = parser.parse_args()
    data = load(args.repository_root)
    result = validate(data, args.repository_root)
    if args.command == "build":
        if not args.output:
            parser.error("build requires an explicit --output")
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "runtime.json").write_text(
            json.dumps(export(data), indent=2) + "\n"
        )
        if args.database:
            from .database import build

            build(args.output / "runtime.sqlite3", export(data))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
