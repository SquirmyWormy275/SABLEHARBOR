#!/usr/bin/env python3
"""Build the controlled fictional operating case, registers and vector maps.

The default build is offline and uses only the Python standard library. Source
geography and screening profiles are pinned; no survey or license is implied.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parents[1]
SOURCE = BASE / "source"
DEFAULT_OUT = BASE / "generated" / "operations"
MOUNTAIN = ZoneInfo("America/Denver")
UTC = UTC


def load() -> dict:
    return json.loads((SOURCE / "operations.json").read_text())


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def elapsed_hours(start: datetime, end: datetime) -> float:
    return (end.astimezone(UTC) - start.astimezone(UTC)).total_seconds() / 3600


def add_elapsed(start: datetime, hours: float) -> datetime:
    return (start.astimezone(UTC) + timedelta(hours=hours)).astimezone(MOUNTAIN)


def service_case(received: datetime, commodity: str, data: dict | None = None) -> dict:
    """Apply real elapsed-time limits, including DST and weekend exceptions.

    Processing includes unload, drayage, inspection and empty release. Exception
    handling is a funded synthetic operating commitment, never a legal waiver.
    """
    data = data or load()
    spec = data["interface"]["service"]
    if received.tzinfo is None:
        raise ValueError("Interchange receipt must include its timezone")
    received = received.astimezone(MOUNTAIN)
    processing = spec["processing_hours"][commodity]
    sla = (
        spec["steel_sla_elapsed_hours"]
        if commodity == "steel"
        else spec["default_sla_elapsed_hours"]
    )
    scheduled = []
    weekday = []
    for day in range(9):
        d = received.date() + timedelta(days=day)
        slot = datetime(d.year, d.month, d.day, spec["scheduled_hour"], tzinfo=MOUNTAIN)
        if slot.astimezone(UTC) < received.astimezone(UTC):
            continue
        if d.weekday() < 5:
            weekday.append(slot)
        if d.weekday() in spec["scheduled_weekdays"]:
            scheduled.append(slot)
    start = scheduled[0]
    release = add_elapsed(start, processing)
    mode = "scheduled Tuesday/Friday window"
    if elapsed_hours(received, release) > sla:
        start = weekday[0]
        release = add_elapsed(start, processing)
        mode = "dispatch exception: next weekday window"
        if elapsed_hours(received, release) > sla:
            start = add_elapsed(received, spec["exception_response_hours"])
            release = add_elapsed(start, processing)
            mode = "dispatch exception: on-call weekend/holiday resources"
    return {
        "record_origin": "SYNTHETIC_SERVICE_SIMULATION",
        "case_role": "CALENDAR_TEST_NOT_AN_ACTUAL_SHIPMENT",
        "commodity": commodity,
        "received": received.isoformat(),
        "handling_start": start.isoformat(),
        "empty_release": release.isoformat(),
        "elapsed_hours": elapsed_hours(received, release),
        "sla_hours": sla,
        "within_sla": elapsed_hours(received, release) <= sla,
        "mode": mode,
    }


def vincenty_miles(a: list, b: list) -> float:
    """WGS84 inverse ellipsoid distance, used on the small Wyoming footprint."""
    major, flattening = 6378137.0, 1 / 298.257223563
    minor = (1 - flattening) * major
    u1 = math.atan((1 - flattening) * math.tan(math.radians(a[1])))
    u2 = math.atan((1 - flattening) * math.tan(math.radians(b[1])))
    longitude = math.radians(b[0] - a[0])
    lam = longitude
    for _ in range(100):
        sine = math.sqrt(
            (math.cos(u2) * math.sin(lam)) ** 2
            + (math.cos(u1) * math.sin(u2) - math.sin(u1) * math.cos(u2) * math.cos(lam)) ** 2
        )
        if sine == 0:
            return 0.0
        cosine = math.sin(u1) * math.sin(u2) + math.cos(u1) * math.cos(u2) * math.cos(lam)
        sigma = math.atan2(sine, cosine)
        alpha_sine = math.cos(u1) * math.cos(u2) * math.sin(lam) / sine
        alpha_cos2 = 1 - alpha_sine**2
        twice_mid = cosine - 2 * math.sin(u1) * math.sin(u2) / alpha_cos2 if alpha_cos2 else 0
        c = flattening / 16 * alpha_cos2 * (4 + flattening * (4 - 3 * alpha_cos2))
        old = lam
        lam = longitude + (1 - c) * flattening * alpha_sine * (
            sigma + c * sine * (twice_mid + c * cosine * (-1 + 2 * twice_mid**2))
        )
        if abs(lam - old) < 1e-12:
            break
    else:
        raise ValueError("Inverse distance did not converge")
    square = alpha_cos2 * (major * major - minor * minor) / (minor * minor)
    aa = 1 + square / 16384 * (4096 + square * (-768 + square * (320 - 175 * square)))
    bb = square / 1024 * (256 + square * (-128 + square * (74 - 47 * square)))
    correction = (
        bb
        * sine
        * (
            twice_mid
            + bb
            / 4
            * (
                cosine * (-1 + 2 * twice_mid**2)
                - bb / 6 * twice_mid * (-3 + 4 * sine**2) * (-3 + 4 * twice_mid**2)
            )
        )
    )
    return minor * aa * (sigma - correction) / 1609.344


def line_miles(coordinates: list) -> float:
    return sum(vincenty_miles(a, b) for a, b in zip(coordinates, coordinates[1:], strict=False))


def geography_verification() -> dict:
    """Independently resample pinned terrain and repeat waterbody intersections.

    Optional numerical dependencies are isolated from the offline standard build.
    Published formation stations remain design inputs; this verifies their grade
    and terrain arithmetic without pretending they establish civil engineering.
    """
    try:
        import numpy as np
        import rasterio
        from pyproj import Transformer
        from scipy.ndimage import map_coordinates
        from shapely.geometry import shape
        from shapely.ops import transform, unary_union
    except ImportError as exc:
        raise RuntimeError(
            "Run with uv --with numpy --with rasterio --with pyproj "
            "--with scipy --with shapely to verify pinned geography"
        ) from exc
    directory = SOURCE / "geography"
    network = json.loads((directory / "network.geojson").read_text())
    profiles = json.loads((directory / "derived_ground_profiles.json").read_text())
    routes = {f["id"]: f for f in network["features"]}
    findings = []
    with rasterio.open(directory / "wyoming_screening_dem.tif") as raster:
        project = Transformer.from_crs(4326, raster.crs, always_xy=True)
        inverse = ~raster.transform
        pixels = raster.read(1)
        for profile in profiles:
            coordinates = routes[profile["route_id"]]["geometry"]["coordinates"]
            points = np.array([project.transform(*point) for point in coordinates])
            cells = np.array([inverse * tuple(point) for point in points])
            if (
                np.any(cells < 0)
                or np.any(cells[:, 0] >= raster.width)
                or np.any(cells[:, 1] >= raster.height)
            ):
                raise ValueError("Route leaves the pinned DEM")
            ground = map_coordinates(
                pixels, [cells[:, 1] - 0.5, cells[:, 0] - 0.5], order=1, mode="nearest"
            )
            stations = profile["stations"]
            supplied = np.array([s["ground_m"] for s in stations])
            formation = np.array([s["formation_m"] for s in stations])
            chainage = np.r_[0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
            if np.max(np.abs(ground - supplied)) > 0.001:
                raise ValueError(f"Pinned ground profile differs: {profile['route_id']}")
            grade = float(np.max(np.abs(np.diff(formation) / np.diff(chainage))) * 100)
            if grade > profile["constraint_max_grade_pct"] + 1e-7:
                raise ValueError(f"Formation grade exceeds bound: {profile['route_id']}")
            findings.append(
                {
                    "route_id": profile["route_id"],
                    "sample_count": len(ground),
                    "maximum_formation_grade_pct": grade,
                }
            )
        anchor = load()["geography"]["red_wash_lon_lat"]
        col, row = inverse * project.transform(*anchor)
        anchor_z = float(
            map_coordinates(pixels, [[row - 0.5], [col - 0.5]], order=1, mode="nearest")[0]
        )
    project12 = Transformer.from_crs(4326, 26912, always_xy=True)
    water = json.loads((directory / "wyoming_waterbodies.geojson").read_text())
    polygons = unary_union(
        [transform(project12.transform, shape(f["geometry"])) for f in water["features"]]
    )
    overlaps = []
    for feature in network["features"]:
        length = (
            transform(project12.transform, shape(feature["geometry"])).intersection(polygons).length
        )
        if length > 0.001:
            raise ValueError(f"Mapped waterbody crossing: {feature['id']}")
        overlaps.append({"route_id": feature["id"], "overlap_m": length})
    return {
        "passed": True,
        "anchor_epsg26912": project12.transform(*anchor),
        "anchor_dem_m": anchor_z,
        "profiles": findings,
        "waterbody_screen": overlaps,
        "scope": "Pinned geography and grade arithmetic only; no survey or permit certification",
    }


def economics(data: dict) -> dict:
    rows = []
    for row in data["interface"]["rates"]:
        cars = row["normalized_billable_cars"]
        legs = row["truck_legs_per_car"]
        revenue = row["rail_rate"] + row["terminal_rate"] + legs * row["dray_rate"]
        cost = row["rail_unit_cost"] + row["terminal_unit_cost"] + legs * row["dray_unit_cost"]
        rows.append(
            {
                "commodity": row["commodity"],
                "billable_cars": cars,
                "payload_short_tons": row["car_payload_short_tons"],
                "annual_short_tons": cars * row["car_payload_short_tons"],
                "annual_truck_trips": cars * legs,
                "aru_revenue_per_car_usd": revenue,
                "variable_cost_per_car_usd": cost,
                "annual_aru_revenue_usd": cars * revenue,
                "annual_variable_cost_usd": cars * cost,
                "external_linehaul_usd": cars * row["external_linehaul_per_car"],
            }
        )
    revenue = sum(r["annual_aru_revenue_usd"] for r in rows)
    variable = sum(r["annual_variable_cost_usd"] for r in rows)
    fixed = data["interface"]["fixed_incremental_annual_usd"]
    monthly = []
    by_commodity = {r["commodity"]: r for r in rows}
    for month in data["interface"]["monthly_2026"]:
        rev = sum(
            n * by_commodity[c]["aru_revenue_per_car_usd"] for c, n in month["carloads"].items()
        )
        cost = sum(
            n * by_commodity[c]["variable_cost_per_car_usd"] for c, n in month["carloads"].items()
        )
        monthly.append(
            {
                "month": month["month"],
                "status": month["status"],
                "cars": sum(month["carloads"].values()),
                "aru_revenue_usd": rev,
                "variable_cost_usd": cost,
                "fixed_cost_usd": fixed // 12,
                "incremental_ebitda_usd": rev - cost - fixed // 12,
            }
        )
    return {
        "normalized_rows": rows,
        "normalized_revenue_usd": revenue,
        "normalized_variable_cost_usd": variable,
        "normalized_fixed_cost_usd": fixed,
        "normalized_ebitda_usd": revenue - variable - fixed,
        "old_revenue_target_variance_usd": revenue - 875000,
        "old_ebitda_target_variance_usd": revenue - variable - fixed - 365000,
        "external_linehaul_excluded_from_aru_revenue_usd": sum(
            r["external_linehaul_usd"] for r in rows
        ),
        "monthly_2026": monthly,
        "commissioning_2026_opex_usd": data["interface"]["commissioning_expense_2026_usd"],
        "full_year_2026_forecast_ebitda_usd": sum(m["incremental_ebitda_usd"] for m in monthly)
        - data["interface"]["commissioning_expense_2026_usd"],
    }


def validate(data: dict) -> dict:
    interface = data["interface"]
    calculated = economics(data)
    checks = {}

    def check(name: str, result: bool) -> None:
        checks[name] = bool(result)
        if not result:
            raise ValueError(f"Operations reconciliation failed: {name}")

    network = json.loads((SOURCE / "geography/network.geojson").read_text())
    rails = [f for f in network["features"] if f["id"].startswith("BST-")]
    measured = sum(line_miles(f["geometry"]["coordinates"]) for f in rails)
    check("measured unique railroad centerline is 40 miles", abs(measured - 40) < 0.0001)
    check(
        "no mine rail endpoint",
        all(
            vincenty_miles(f["geometry"]["coordinates"][-1], data["geography"]["red_wash_lon_lat"])
            > 1
            for f in rails
        ),
    )
    check(
        "branch junctions are on mainline",
        all(
            f["properties"].get("junction_main_mile", 0) < data["geography"]["mainline_route_miles"]
            for f in rails
        ),
    )
    road = next(f for f in network["features"] if f["id"] == "ROAD-RW-01")
    check(
        "truck route is nine measured miles",
        abs(line_miles(road["geometry"]["coordinates"]) - 9) < 0.0001,
    )
    check(
        "four owned locomotives",
        len(data["locomotives"]) == 4
        and all(r["ownership"] == "owned" for r in data["locomotives"]),
    )
    check(
        "three available two normally required",
        sum(r["available"] for r in data["locomotives"]) == 3
        and sum(r["normal_service"] for r in data["locomotives"]) == 2,
    )
    check("58 railway employees", sum(r["count"] for r in data["employee_allocations"]) == 58)
    epochs = {r["epoch"]: r for r in data["geography"]["historical_route_epochs"]}
    history = {r["id"]: r for r in data["history"]}
    check(
        "early coal route extent is not invented",
        epochs["1898"]["route_miles"] is None
        and epochs["1898"]["extent_state"] == "UNKNOWN_EARLY_ALIGNMENT",
    )
    check(
        "1954 range remains unlocated",
        epochs["1954"]["route_miles"] is None
        and epochs["1954"]["surviving_route_miles_low"] == 14
        and epochs["1954"]["surviving_route_miles_high"] == 16,
    )
    check(
        "historical construction dates resolve",
        all(
            r["effective_date"] == history[r["history_id"]]["date"]
            for r in epochs.values()
            if r["history_id"]
        ),
    )
    check(
        "historical branch growth reconciles",
        abs(
            epochs["1968"]["route_miles"]
            + epochs["1972"]["added_route_miles"]
            - epochs["1972"]["route_miles"]
        )
        < 1e-8
        and abs(
            epochs["1972"]["route_miles"]
            + epochs["1986"]["added_route_miles"]
            - epochs["1986"]["route_miles"]
        )
        < 1e-8,
    )
    check(
        "ownership change adds no route miles",
        epochs["1986"]["route_miles"]
        == epochs["1991"]["route_miles"]
        == epochs["2026"]["route_miles"]
        == 40,
    )
    check(
        "nonempty full asset registers",
        all(
            data[k]
            for k in [
                "facilities",
                "track_segments",
                "structures",
                "locomotives",
                "railcars",
                "road_equipment",
                "handling_equipment",
                "safety_events",
            ]
        ),
    )
    check(
        "track classifications and speeds",
        all(
            r["maximum_freight_mph"] == {1: 10, 2: 25}[r["track_class"]]
            for r in data["track_segments"]
        ),
    )
    check(
        "205 base plus ten projects billable",
        sum(r["normalized_billable_cars"] for r in interface["rates"]) == 215
        and sum(
            r["normalized_billable_cars"] for r in interface["rates"] if r["commodity"] != "project"
        )
        == 205,
    )
    check(
        "225 planning and 300 capacity distinct",
        interface["contingent_unbilled_cars"] + 215 == interface["planning_cars"] == 225
        and interface["design_capacity_cars"] == 300,
    )
    check("2026 ramp 63 cars", sum(m["cars"] for m in calculated["monthly_2026"]) == 63)
    check("July 7 service start", interface["service_start"] == "2026-07-07")
    check(
        "forecast is not historical actual",
        all(
            m["status"] == "FORECAST_AT_2026_09_05"
            for m in interface["monthly_2026"]
            if m["month"] >= "2026-09"
        ),
    )
    check(
        "direct uranium custody remains gated",
        interface["direct_uranium_custody"] == "OPEN_GATED"
        and not interface["finished_product_included"],
    )
    check(
        "phase one capital reconciles",
        sum(r["amount_usd"] for r in interface["phase1_capex"]) == 8500000,
    )
    check(
        "mine capital 3.25M",
        sum(
            r["amount_usd"]
            for r in interface["phase1_capex"]
            if r["owner"] == "Red Wash Mining, LLC"
        )
        == 3250000,
    )
    check(
        "ARU capital 5.25M",
        sum(
            r["amount_usd"]
            for r in interface["phase1_capex"]
            if r["owner"] == "American Resource Utility, Inc."
        )
        == 5250000,
    )
    check("catch-up capital 11M", sum(r["amount_usd"] for r in data["catchup_capital"]) == 11000000)
    check(
        "drainage structures tie to 1.2M",
        sum(r["catchup_usd"] for r in data["structures"]) == 1200000,
    )
    check(
        "locomotive program ties to 1.8M",
        sum(r["catchup_usd"] for r in data["locomotives"]) == 1800000,
    )
    check(
        "terminal capacity supports external plus mine",
        data["facility_capacity_bridge"]["terminal_external_tons_2025"]
        + data["facility_capacity_bridge"]["rw_normalized_receiving_tons"]
        <= data["facility_capacity_bridge"]["terminal_total_annual_capacity_tons"],
    )
    check(
        "warehouse occupancy fits capacity",
        data["facility_capacity_bridge"]["warehouse_2025_reserved_pallet_months"]
        <= 12 * sum(r["pallet_slots"] for r in data["facilities"]),
    )
    check(
        "traction constraint",
        data["capacity_model"]["required_tractive_effort_lb"]
        < data["capacity_model"]["available_tractive_effort_lb"],
    )
    finance = json.loads((SOURCE / "finance.json").read_text())
    employees = {e["employee_id"]: e for e in finance["employees"]}
    facilities = {f["id"]: f for f in data["facilities"]}
    assignments = data["contract_facility_assignments"]
    for contract in finance["contracts"]:
        check(
            f"physical units reconcile for {contract['contract_id']}",
            sum(
                a["annual_units_2025"]
                for a in assignments
                if a["contract_id"] == contract["contract_id"]
            )
            == contract["annual_units"],
        )
    for manager in data["management"]:
        check(
            f"management census {manager['name']}",
            employees[manager["employee_id_reference"]]["name"] == manager["name"],
        )
    check(
        "external terminal volume agrees with finance",
        sum(c["annual_units"] for c in finance["contracts"] if c["segment"] == "TERMINALS")
        == data["facility_capacity_bridge"]["terminal_external_tons_2025"],
    )
    for fid in ["FAC-TAY-TERMINAL", "FAC-RAW-TERMINAL"]:
        required = sum(
            a["annual_units_2025"]
            for a in assignments
            if a["facility_id"] == fid and a["segment"] == "TERMINALS"
        )
        if fid == "FAC-TAY-TERMINAL":
            required += sum(r["annual_short_tons"] for r in calculated["normalized_rows"])
        check(
            f"terminal capacity at {fid}",
            required <= facilities[fid]["annual_external_ton_capacity"],
        )
    for fid in ["FAC-TAY-WAREHOUSE", "FAC-RAW-WAREHOUSE"]:
        required = sum(a["annual_units_2025"] for a in assignments if a["facility_id"] == fid)
        check(f"warehouse capacity at {fid}", required <= facilities[fid]["pallet_slots"] * 12)
    truck = data["facility_capacity_bridge"]["trucking"]
    truck_mine_hours = sum(
        r["normalized_billable_cars"]
        * r["truck_legs_per_car"]
        * interface["unit_cost_components"][r["commodity"]]["dray"]["cycle_hours"]
        for r in interface["rates"]
    )
    check(
        "mine truck hours derive from invoices",
        abs(truck_mine_hours - truck["rw_normalized_cycle_hours"]) < 0.001,
    )
    check(
        "external truck dispatches agree with finance",
        truck["external_dispatches_2025"]
        == sum(c["annual_units"] for c in finance["contracts"] if c["segment"] == "TRUCKING"),
    )
    check(
        "trucking census supports all assigned roles",
        sum(truck["staff_allocation"].values())
        == sum(e["fte"] for e in employees.values() if e["function"] == "trucking")
        == 24,
    )
    check(
        "driver and tractor hours fit the dispatch book",
        truck["total_required_cycle_hours"]
        == truck["external_annual_cycle_hours"] + truck_mine_hours
        and truck["total_required_cycle_hours"]
        <= min(truck["available_driver_hours"], truck["available_tractor_hours"]),
    )
    check(
        "branch service included within two normal crew turns",
        data["capacity_model"]["base_daily_train_hours_including_branches"]
        <= 2 * data["capacity_model"]["crew_shift_hours"],
    )
    for facility in facilities.values():
        tracks = [t for t in data["track_segments"] if t.get("facility_id") == facility["id"]]
        check(f"full yard track inventory {facility['id']}", len(tracks) == facility["track_count"])
        check(
            f"car spots reconcile {facility['id']}",
            sum(t["car_spots"] for t in tracks) == facility["car_spots"],
        )
        for track in tracks:
            check(
                f"train length fits {track['id']}",
                track["car_spots"] * track["reference_car_length_ft"]
                + track["locomotive_and_clearance_allowance_ft"]
                <= track["length_miles"] * 5280,
            )
    check(
        "catch-up timing agrees with finance",
        all(
            sorted(int(m[-2:]) for m in r["cash_timing"]["monthly_fractions"])
            == finance["forecast_2026"]["catchup_months"]
            and abs(sum(r["cash_timing"]["monthly_fractions"].values()) - 1) < 1e-9
            for r in data["catchup_capital"]
        ),
    )
    check(
        "phase one commissioning agrees with finance",
        all(
            r["in_service_date"] == finance["forecast_2026"]["interface_in_service"]
            for r in interface["phase1_capex"]
        ),
    )
    for commodity, comp in interface["unit_cost_components"].items():
        dray = comp["dray"]
        bottom_up = (
            dray["cycle_hours"]
            * (dray["burden_labor_usd_per_hour"] + dray["equipment_usd_per_hour"])
            + dray["fuel_usd"]
            + dray["other_usd"]
        )
        check(
            f"{commodity} dray price model covers cost drivers",
            bottom_up <= dray["rounded_unit_cost_usd"],
        )
    for stored in interface["receiving"]:
        daily = stored.get(
            "consumption_short_tons_per_processing_day",
            stored.get("consumption_as_received_short_tons_per_processing_day"),
        )
        minimum_days = stored["minimum_operating_inventory_short_tons"] / daily
        reorder_days = stored["reorder_point_short_tons"] / daily
        check(
            f"{stored['commodity']} storage buffer",
            10 <= minimum_days <= 11 and 14 <= reorder_days <= 15,
        )
    check(
        "claim reserve and upside not double-counted",
        data["claims"]["closing_reserve_usd"]
        + data["claims"]["additional_possible_adverse_development_usd"]
        == data["claims"]["total_adverse_case_usd"]
        == 1300000,
    )
    screen = json.loads((SOURCE / "geography/spatial_screen.json").read_text())
    check(
        "no inherited waterbody crossing introduced",
        all(r["overlap_metres"] < 0.001 for r in screen["waterbody_overlaps"]),
    )
    for name, digest in screen["input_sha256"].items():
        check(
            f"spatial screen input {name}",
            hashlib.sha256((SOURCE / "geography" / name).read_bytes()).hexdigest() == digest,
        )
    for path, digest in data["geography"]["source_file_sha256"].items():
        check(
            f"pinned geography {path}",
            hashlib.sha256((SOURCE / path).read_bytes()).hexdigest() == digest,
        )
    return {
        "passed": True,
        "check_count": len(checks),
        "checks": checks,
        "measured_rail_miles": measured,
        "normalized_economics": calculated,
        "scope": "Synthetic case reconciliation; no professional survey, license or safety certification",  # noqa: E501 — literal SVG/document text
    }


class SVG:
    def __init__(self, title: str, subtitle: str, width: int = 1400, height: int = 960):
        self.width, self.height = width, height
        self.items = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',  # noqa: E501 — literal SVG/document text
            f"<title>{html.escape(title)}</title>",
            "<style>text{font-family:Arial,Helvetica,sans-serif;fill:#182b32}.muted{fill:#586b70}.small{font-size:14px}.label{font-size:17px}.title{font-size:30px;font-weight:700}.sub{font-size:17px}.panel{fill:#f3f5f2;stroke:#b6c1bc}</style>",  # noqa: E501 — literal SVG/document text
            f'<rect width="{width}" height="{height}" fill="#faf9f4"/>',
        ]
        self.text(48, 53, title, "title")
        self.text(48, 86, subtitle, "sub")
        self.items.append(f'<path d="M48 105 H{width - 48}" stroke="#224d57" stroke-width="3"/>')

    def text(self, x: float, y: float, text: object, cls: str = "label", **attrs) -> None:
        extra = " ".join(f'{k.replace("_", "-")}="{html.escape(str(v))}"' for k, v in attrs.items())
        self.items.append(
            f'<text x="{x:.2f}" y="{y:.2f}" class="{cls}" {extra}>{html.escape(str(text))}</text>'
        )

    def path(
        self, points: list, color: str, width: float = 2, dash: str = "", fill: str = "none"
    ) -> None:
        d = " ".join(
            ("M" if i == 0 else "L") + f"{x:.2f},{y:.2f}" for i, (x, y) in enumerate(points)
        )
        self.items.append(
            f'<path d="{d}" stroke="{color}" stroke-width="{width}" fill="{fill}" stroke-dasharray="{dash}"/>'  # noqa: E501 — literal SVG/document text
        )

    def box(
        self, x: float, y: float, w: float, h: float, fill: str = "#dce6df", stroke: str = "#497169"
    ) -> None:
        self.items.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="{fill}" stroke="{stroke}"/>'  # noqa: E501 — literal SVG/document text
        )

    def dot(self, x: float, y: float, r: float = 5, color: str = "#224d57") -> None:
        self.items.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r}" fill="{color}"/>')

    def north(self, x: float, y: float) -> None:
        self.path([(x, y + 48), (x, y)], "#183f49", 3)
        self.path([(x - 8, y + 15), (x, y), (x + 8, y + 15)], "#183f49", 2)
        self.text(x - 7, y - 12, "N")

    def save(self, path: Path) -> None:
        path.write_text("\n".join(self.items + ["</svg>"]) + "\n")


def regional_map(out: Path, data: dict) -> None:
    svg = SVG(
        "BS&T / TAYLOR / RED WASH",
        "Controlled operating geography · 40.000 route-miles · September 5, 2026 case cutoff",
    )
    lon0, lat0 = -108.1, 42.0
    metres_lon = math.pi * 6371008.8 / 180 * math.cos(math.radians(lat0))
    metres_lat = math.pi * 6371008.8 / 180
    scale = 720 / (0.64 * metres_lat)

    def screen(p):
        return (440 + (p[0] - lon0) * metres_lon * scale, 460 - (p[1] - lat0) * metres_lat * scale)

    # Restrict reference features to the mapped footprint, without reinterpreting them as company assets.  # noqa: E501 — literal SVG/document text
    svg.box(48, 126, 790, 720, "#eef0e6", "#bec6bd")

    def reference_lines(obj):
        kind, c = obj["type"], obj["coordinates"]
        if kind == "LineString":
            return [c]
        if kind == "MultiLineString" or kind == "Polygon":
            return c
        if kind == "MultiPolygon":
            return [ring for polygon in c for ring in polygon]
        return []

    for file, color, weight in [
        ("wyoming_waterbodies.geojson", "#b9d0d5", 1),
        ("wyoming_local_roads.geojson", "#d6d2c2", 0.7),
        ("wamsutter_highways.geojson", "#c8b18b", 2),
        ("wamsutter_fra_rail.geojson", "#7e888c", 2),
    ]:
        for feature in json.loads((SOURCE / "geography" / file).read_text())["features"]:
            for line in reference_lines(feature["geometry"]):
                visible = [
                    screen(p) for p in line if -108.43 < p[0] < -107.82 and 41.66 < p[1] < 42.29
                ]
                if len(visible) > 1:
                    svg.path(
                        visible,
                        color,
                        weight,
                        fill="#d7e4e7" if file == "wyoming_waterbodies.geojson" else "none",
                    )
    network = json.loads((SOURCE / "geography/network.geojson").read_text())
    for feature in network["features"]:
        road = feature["id"] == "ROAD-RW-01"
        svg.path(
            [screen(p) for p in feature["geometry"]["coordinates"]],
            "#b66531" if road else "#163f50",
            3 if road else 4,
            "9 5" if road else "",
        )
    markers = [
        (data["geography"]["wamsutter_junction_lon_lat"], "Wamsutter / UP context", 14, -14),
        (data["geography"]["taylor_lon_lat"], "Taylor · fictional hub", 16, 7),
        (data["geography"]["red_wash_lon_lat"], "Red Wash · truck receiving", 16, -8),
    ]
    for p, name, dx, dy in markers:
        x, y = screen(p)
        svg.dot(x, y, 6)
        svg.text(x + dx, y + dy, name, "small")
    for f in network["features"][1:3]:
        x, y = screen(f["geometry"]["coordinates"][-1])
        svg.dot(x, y, 4)
        svg.text(x + 10, y + 8, f["properties"]["name"], "small")
    for structure in data["structures"]:
        x, y = screen(structure["lon_lat"])
        if structure["kind"] == "rail_bridge":
            svg.box(x - 4, y - 3, 8, 6, "#faf9f4", "#163f50")
    svg.north(793, 173)
    five_mile_pixels = 5 * 1609.344 * scale
    svg.path([(78, 811), (78 + five_mile_pixels, 811)], "#183f49", 4)
    svg.text(78, 798, "0", "small")
    svg.text(78 + five_mile_pixels - 12, 798, "5 mi", "small")
    notes = [
        "NETWORK AND CUSTODY",
        "33.3485 mi Wamsutter–Taylor main",
        "4.0000 mi East Materials branch",
        "2.6515 mi Mineral Transfer branch",
        "Parallel yard tracks excluded from route miles",
        "",
        "Solid navy: synthetic railway",
        "Dashed ochre: 9 mi truck-only access",
        "Gray: official FRA rail reference",
        "Pale tan: Census road reference",
        "",
        "Main / branches: Class 2, 25 mph ceiling",
        "Yard / industrial tracks: Class 1, 10 mph",
        "Temporary restrictions remain controlling",
        "",
        "225-car normalized planning allowance",
        "205 base + 10 projects + 10 contingency",
        "300-car design capacity; no guarantee",
        "Direct uranium custody: OPEN_GATED",
        "",
        "Red Wash: 42.2200° N, 108.1800° W",
        "Sweetwater County / Great Divide Basin",
        "Screening elevation: about 2,098 m / 6,885 ft",
        "Taylor selected from prior candidate A",
        "",
        "County/roads do not establish land rights.",
        "Railway, town, facilities and access road",
        "are synthetic; this is not a surveyed plan.",
    ]
    for i, text in enumerate(notes):
        svg.text(868, 151 + i * 24, text, "small" if i else "label")
    svg.text(
        48,
        886,
        "CRS: local equirectangular metric frame, origin 42° N / 108.1° W; WGS84 geographic source coordinates.",  # noqa: E501 — literal SVG/document text
        "small",
    )
    svg.text(
        48,
        910,
        "Sources: Census TIGER, FRA/BTS rail and pinned USGS 3DEP screening; exact URLs, dates and hashes in source/geography.",  # noqa: E501 — literal SVG/document text
        "small",
    )
    svg.text(
        48,
        934,
        "Scale is local-screening accuracy. Existing candidate terrain and new branch grade screens do not establish professional engineering approval.",  # noqa: E501 — literal SVG/document text
        "small",
    )
    svg.save(out / "bst_network.svg")


def historical_map(out: Path, data: dict) -> None:
    """Show construction epochs without inventing an old georeferenced survey."""
    svg = SVG(
        "BS&T · HISTORICAL ROUTE DEVELOPMENT",
        "1898 coal origin · 1954 rescue · later industrial extensions · September 5, 2026 case cutoff",  # noqa: E501 — literal SVG/document text
    )
    epochs = {r["epoch"]: r for r in data["geography"]["historical_route_epochs"]}
    colors = {"old": "#8b684c", "main": "#1f5261", "east": "#ba803d", "mineral": "#548375"}
    for x, title in [
        (48, "1898 / 1954 · COAL ESTATE"),
        (478, "1968 · TAYLOR MAINLINE"),
        (908, "1972 / 1986 · BRANCHES"),
    ]:
        svg.box(x, 132, 410, 532, "#f0eee4", "#c0c8bd")
        svg.text(x + 18, 160, title, "label")
    svg.path([(170, 548), (188, 445), (171, 363), (209, 273)], colors["old"], 7, "9 7")
    svg.box(129, 249, 124, 328, "none", colors["old"])
    svg.dot(170, 548, 6, colors["old"])
    svg.text(148, 602, "1954 surviving extent: 14–16 mi", "small")
    svg.text(76, 195, "1898: predecessor organized for coal", "small")
    svg.text(76, 219, "Original extent and alignment unknown", "small")
    svg.text(267, 340, "Coal workings", "small")
    svg.text(267, 366, "Unlocated", "small")
    svg.text(267, 392, "reconstruction", "small")
    svg.text(76, 635, "Rescue does not establish an 1898 survey.", "small")
    svg.path([(625, 570), (606, 492), (650, 398), (633, 315), (654, 248)], colors["main"], 7)
    svg.dot(625, 570, 6)
    svg.dot(654, 248, 6)
    svg.text(668, 249, "Taylor hub", "small")
    svg.text(654, 591, "Wamsutter context", "small")
    svg.text(500, 196, "Completed October 14, 1968", "small")
    svg.text(500, 620, f"Mainline: {epochs['1968']['route_miles']:.4f} route-mi", "small")
    svg.text(500, 645, "Old-line retention / relocation unverified.", "small")
    main = [(1041, 570), (1027, 492), (1069, 397), (1056, 315), (1077, 248)]
    svg.path(main, colors["main"], 7)
    svg.path([(1049, 442), (1140, 402), (1190, 359)], colors["east"], 6)
    svg.path([(1064, 283), (1140, 285), (1200, 250)], colors["mineral"], 6)
    svg.dot(1041, 570, 6)
    svg.dot(1077, 248, 6)
    svg.text(927, 196, "1972 East +4.0000 mi", "small")
    svg.text(927, 222, "1986 Mineral +2.6515 mi", "small")
    svg.text(1157, 335, "Mineral", "small")
    svg.text(1160, 430, "East", "small")
    svg.text(1050, 612, "Current total: 40.0000 mi", "small")
    svg.text(927, 645, "1991 ARU ownership: no added mileage.", "small")
    svg.text(50, 704, "HOW TO READ THIS HISTORY", "label")
    notes = [
        "Dashed brown: unlocated coal-era reconstruction. Navy: derived 1968 mainline. Ochre: 1972 East. Green: 1986 Mineral.",  # noqa: E501 — literal SVG/document text
        "The 14–16-mile range belongs to the surviving 1954 estate; it is not a precise 1898 length or a surveyed old boundary.",  # noqa: E501 — literal SVG/document text
        "1968 net route growth is about 17.35–19.35 miles; gross new construction and realigned old mileage are not established.",  # noqa: E501 — literal SVG/document text
        "1972 total: 37.3485 miles. 1986, 1991 and current total: 40.0000. Parallel yard tracks add no unique route-miles.",  # noqa: E501 — literal SVG/document text
        "Red Wash is absent from every rail epoch: ordinary mine receipts use trucks, and direct uranium custody remains gated.",  # noqa: E501 — literal SVG/document text
    ]
    for index, note in enumerate(notes):
        svg.text(50, 733 + index * 26, note, "small")
    svg.text(
        50,
        890,
        "CRS / scale: logical schematic canvas, not georeferenced. North and a ground-distance scale cannot be established for the early estate.",  # noqa: E501 — literal SVG/document text
        "small",
    )  # noqa: E501 — literal SVG/document text
    svg.text(
        50,
        917,
        "Sources: controlled history and source/operations.json historical_route_epochs; current geographic geometry is separately published in bst_network.svg.",  # noqa: E501 — literal SVG/document text
        "small",
    )  # noqa: E501 — literal SVG/document text
    svg.text(
        50,
        944,
        "Fictional reconstruction. Exact extension dates are declared case derivations; no historical survey, mapped property right or professional certification is claimed.",  # noqa: E501 — literal SVG/document text
        "small",
    )  # noqa: E501 — literal SVG/document text
    svg.save(out / "bst_historical_routes.svg")


def site_map(out: Path, data: dict) -> None:
    svg = SVG(
        "RED WASH · SITE AND RECEIVING",
        "Red Wash Mining, LLC · Sweetwater County, Wyoming · Pale Sun Inc. ownership",
    )
    svg.box(48, 130, 790, 680, "#f1efe3", "#bac5b9")

    # Local design grid in metres relative to the mine anchor; all placements are fictional.
    def p(x, y):
        return (440 + x * 0.6, 470 - y * 0.6)

    def facility(x, y, w, h, name, fill="#dce6df"):
        xx, yy = p(x, y + h)
        svg.box(xx, yy, w * 0.6, h * 0.6, fill)
        svg.text(xx + 8, yy + 23, name, "small")

    facility(-510, 255, 270, 160, "Tailings Cell 1", "#d7d3bc")
    facility(-180, 250, 270, 165, "Tailings Cell 2 / cover plan", "#e4ddc5")
    facility(-440, -80, 230, 160, "Mill / product handling")
    facility(-125, -40, 150, 110, "Shaft / hoist")
    facility(110, -65, 200, 150, "Shop / mine services")
    facility(-440, -370, 255, 190, "Truck receiving / scales", "#d2dce4")
    facility(-145, -370, 195, 190, "Binder / MRO", "#d2dce4")
    facility(100, -370, 190, 190, "Acid containment", "#e7d6c8")
    facility(335, -340, 140, 160, "Steel laydown", "#d2dce4")
    facility(220, 245, 215, 160, "Water controls", "#cfdee3")
    svg.path([p(-620, -440), p(-320, -440), p(-320, -330)], "#b66531", 8)
    svg.text(
        65,
        770,
        "To Taylor: existing synthetic industrial road, 9 mi; 2026 targeted rehabilitation",
        "small",
    )
    svg.path([p(-495, 240), p(-495, 165), p(350, 165), p(350, 245)], "#6992a4", 2, "5 4")
    for x, y in [(-455, 155), (310, 195), (330, 120)]:
        a, b = p(x, y)
        svg.dot(a, b, 4, "#477f96")
    a, b = p(330, 120)
    svg.text(a + 9, b + 5, "MW-17", "small")
    svg.north(792, 170)
    svg.path([(80, 798), (200, 798)], "#183f49", 4)
    svg.text(80, 785, "0", "small")
    svg.text(175, 785, "200 m", "small")
    notes = [
        "CONTROLLED SITE BASIS",
        "Operator: Red Wash Mining, LLC",
        "Site workforce: 128; platform: 12",
        "Anchor: 42.2200° N / 108.1800° W",
        "NAD83 / UTM 12N: 732,749 E / 4,678,054 N",
        "DEM screening: 2,098 m / 6,885 ft",
        "",
        "RECEIVING: JULY 7, 2026",
        "Truck scales, signed custody handoffs",
        "Two 30,000-gallon acid tanks",
        "Acid: 210 t minimum / 290 t reorder",
        "Three 150-ton binder silos",
        "Binder: 245 t minimum / 340 t reorder",
        "10–14 operating-day buffer policy",
        "",
        "Mine-specific Phase 1: $3.25M",
        "Total interface Phase 1: $8.50M",
        "No mine rail spur or rail loadout",
        "Uranium product: qualified outside carriers",
        "",
        "KNOWN OPERATING DEFECTS RETAINED",
        "Cell 1 underdrain / MW-17 trends",
        "Fan redundancy and electrical backlog",
        "Progressive reclamation / water controls",
        "",
        "Blue: receiving · green: operating plant",
        "Tan: tailings · dots/dashes: water controls",
    ]
    for i, line in enumerate(notes):
        svg.text(865, 153 + i * 24, line, "label" if i == 0 else "small")
    svg.text(
        48,
        854,
        "Local metre-based design schematic; surface reference CRS: NAD83/UTM 12N. Building placement and footprints are synthetic.",  # noqa: E501 — literal SVG/document text
        "small",
    )
    svg.text(
        48,
        881,
        "Source: controlled Red Wash operating record; verified Census county; pinned USGS elevation. Scale refers to this conceptual local layout.",  # noqa: E501 — literal SVG/document text
        "small",
    )
    svg.text(
        48,
        908,
        "Preserves diligence defects; does not substitute for licensed mine plans, tank design, land rights, containment design or surveyed drainage.",  # noqa: E501 — literal SVG/document text
        "small",
    )
    svg.save(out / "red_wash_site.svg")


def underground_map(out: Path, data: dict) -> None:
    svg = SVG(
        "RED WASH · UNDERGROUND OPERATING PLAN",
        "Selective drift-and-fill with cemented paste backfill · conceptual 2,500-foot working depth",  # noqa: E501 — literal SVG/document text
    )
    svg.box(48, 130, 790, 670, "#eeeee8", "#bac5b9")

    def p(x, y):
        return (420 + x * 0.7, 470 - y * 0.7)

    svg.path([p(-370, -280), p(-200, -200), p(0, 0), p(80, 180), p(200, 300)], "#294b59", 9)
    for _index, (x, y, dy) in enumerate(
        [(-210, -185, 70), (-120, -110, -85), (55, 140, 80), (120, 235, -80)]
    ):
        svg.path([p(x, y), p(x + 230, y + dy)], "#52747b", 6)
        for t in [0.25, 0.5, 0.75]:
            xx = x + 230 * t
            yy = y + dy * t
            svg.path([p(xx, yy), p(xx + 55, yy + 75)], "#879b91", 4)
    # Explicit uncertain outline preserves the East 12 diligence defect.
    svg.path(
        [p(0, 160), p(170, 300), p(395, 230), p(260, 90), p(0, 160)], "#a0693d", 3, "8 5", "none"
    )
    svg.text(480, 255, "East 12 lens: continuity disputed", "small")
    x, y = p(0, 0)
    svg.dot(x, y, 10)
    svg.text(x + 18, y + 7, "Main shaft / access", "small")
    svg.path([p(-270, -80), p(-60, 140), p(-40, 320)], "#8b5850", 3, "6 4")
    svg.text(142, 380, "Ventilation return", "small")
    svg.text(
        76,
        739,
        "Subsurface traces are local synthetic engineering geometry, not geographic surface boundaries.",  # noqa: E501 — literal SVG/document text
        "small",
    )
    svg.north(790, 175)
    svg.path([(78, 781), (218, 781)], "#183f49", 4)
    svg.text(78, 768, "0", "small")
    svg.text(195, 768, "200 m", "small")
    notes = [
        "OPERATING AND RESOURCE BASIS",
        "Surface anchor: 42.22° N / 108.18° W",
        "Operator: Red Wash Mining, LLC",
        "Site 128 FTE / platform 12 FTE",
        "",
        "2026 selected: 175,000 short tons",
        "Grade 0.17% U3O8 · recovery 92%",
        "547,400 lb produced in annual plan",
        "225,000 t normalized target is a later case",
        "Future throughput requires capacity bridge",
        "",
        "Navy: main development / access",
        "Gray-green: stopes and backfill sequence",
        "Rust dashed: conceptual ventilation return",
        "Ochre dashed: uncertain resource continuity",
        "",
        "TECHNICAL DEFECTS REMAIN VISIBLE",
        "East 12 lens smoothing / cutoff issues",
        "Carbonate-rich acid/recovery response",
        "Main exhaust fan / control redundancy",
        "No inferred tonnes in base valuation",
        "",
        "No mine rail track exists in this plan.",
        "This is a schematic: no survey, reserve",
        "certification or approved ventilation design.",
    ]
    for i, line in enumerate(notes):
        svg.text(865, 152 + i * 26, line, "label" if i == 0 else "small")
    svg.text(
        48,
        852,
        "Local mine grid in metres, oriented to conceptual north. Surface reference CRS: NAD83 / UTM zone 12N; no surveyed underground tie claimed.",  # noqa: E501 — literal SVG/document text
        "small",
    )
    svg.text(
        48,
        880,
        "Source: selected Red Wash technical case, with original raster preserved separately as a superseded historical artifact.",  # noqa: E501 — literal SVG/document text
        "small",
    )
    svg.text(
        48,
        908,
        "Depth, stope geometry, ventilation traces and lens boundaries are synthetic case assumptions whose uncertainty is part of the participant evidence.",  # noqa: E501 — literal SVG/document text
        "small",
    )
    svg.save(out / "red_wash_underground.svg")


def csv_table(path: Path, rows: list) -> None:
    keys = sorted({k for row in rows for k in row})
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    k: json.dumps(v, sort_keys=True) if isinstance(v, (list, dict)) else v
                    for k, v in row.items()
                }
            )


def geography_outputs(out: Path, data: dict) -> None:
    """Emit portable GIS layers, keeping synthetic envelopes distinct from parcels."""
    out.mkdir(exist_ok=True)
    features = []
    for r in data["facilities"]:
        lon, lat = r["lon_lat"]
        area = r["acreage"] * 4046.8564224
        aspect = r["footprint_aspect_ratio"]
        dx = math.sqrt(area * aspect) / 2 / (111195 * math.cos(math.radians(lat)))
        dy = math.sqrt(area / aspect) / 2 / 111195
        props = dict(r)
        props["geometry_role"] = "synthetic derived site envelope; not a cadastral parcel"
        features.append(
            {
                "type": "Feature",
                "id": r["id"],
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [lon - dx, lat - dy],
                            [lon + dx, lat - dy],
                            [lon + dx, lat + dy],
                            [lon - dx, lat + dy],
                            [lon - dx, lat - dy],
                        ]
                    ],
                },
                "properties": props,
            }
        )
    write_json(out / "facilities.geojson", {"type": "FeatureCollection", "features": features})
    write_json(
        out / "structure_points.geojson",
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": r["id"],
                    "geometry": {"type": "Point", "coordinates": r["lon_lat"]},
                    "properties": r,
                }
                for r in data["structures"]
            ],
        },
    )
    network = json.loads((SOURCE / "geography/network.geojson").read_text())
    write_json(out / "network.geojson", network)
    route_by_id = {f["id"]: f for f in network["features"]}
    facility_by_id = {f["id"]: f for f in data["facilities"]}
    yard_counts = {}
    track_features = []
    for track in data["track_segments"]:
        if track.get("route_id"):
            coordinates = route_by_id[track["route_id"]]["geometry"]["coordinates"]
            selected = []
            chainage = 0.0
            for a, b in zip(coordinates, coordinates[1:], strict=False):
                length = vincenty_miles(a, b)
                low = max(chainage, track["mp_start"])
                high = min(chainage + length, track["mp_end"])
                if low < high:
                    for station in [low, high]:
                        fraction = (station - chainage) / length
                        point = [a[i] + fraction * (b[i] - a[i]) for i in range(2)]
                        if not selected or point != selected[-1]:
                            selected.append(point)
                chainage += length
            role = "registered route segment clipped to engineering chainage"
        else:
            fid = track["facility_id"]
            facility = facility_by_id[fid]
            lon, lat = facility["lon_lat"]
            index = yard_counts.get(fid, 0)
            yard_counts[fid] = index + 1
            lat += (index - (facility["track_count"] - 1) / 2) * 12 / 111195
            half_lon = track["length_miles"] * 1609.344 / 2 / (111195 * math.cos(math.radians(lat)))
            selected = [[lon - half_lon, lat], [lon + half_lon, lat]]
            role = (
                "synthetic parallel yard-track envelope; conceptual orientation, "
                "excludes switches and not a surveyed alignment"
            )
        track_features.append(
            {
                "type": "Feature",
                "id": track["id"],
                "geometry": {"type": "LineString", "coordinates": selected},
                "properties": dict(track, geometry_role=role),
            }
        )
    write_json(
        out / "track_segments.geojson", {"type": "FeatureCollection", "features": track_features}
    )
    csv_table(
        out / "nodes_and_mileposts.csv",
        [
            {
                "id": r["id"],
                "name": r["name"],
                "longitude": r["lon_lat"][0],
                "latitude": r["lon_lat"][1],
                "entity": r["owner"],
                "fact_state": r["fact_state"],
            }
            for r in data["facilities"]
        ],
    )


def build(out: Path = DEFAULT_OUT) -> dict:
    data = load()
    result = validate(data)
    out.mkdir(parents=True, exist_ok=True)
    maps = out / "maps"
    maps.mkdir(exist_ok=True)
    tables = out / "registers"
    tables.mkdir(exist_ok=True)
    registers = [
        "facilities",
        "track_segments",
        "structures",
        "locomotives",
        "railcars",
        "road_equipment",
        "handling_equipment",
        "employee_allocations",
        "management",
        "labor_agreements",
        "safety_events",
        "history",
        "catchup_capital",
        "external_references",
        "contract_facility_assignments",
    ]
    for key in registers:
        csv_table(tables / (key + ".csv"), data[key])
    csv_table(tables / "normalized_interface_rates.csv", data["interface"]["rates"])
    csv_table(tables / "phase1_capital.csv", data["interface"]["phase1_capex"])
    write_json(out / "interface_economics.json", economics(data))
    write_json(out / "physical_finance_bridge.json", data["facility_capacity_bridge"])
    cases = [
        service_case(datetime.fromisoformat(ts), commodity, data)
        for ts, commodity in [
            ("2026-07-07T07:30:00-06:00", "acid"),
            ("2026-07-10T09:00:00-06:00", "acid"),
            ("2026-07-11T13:00:00-06:00", "binder"),
            ("2026-07-10T09:00:00-06:00", "steel"),
            ("2026-11-01T00:30:00-06:00", "acid"),
            ("2026-03-07T23:30:00-07:00", "binder"),
        ]
    ]
    write_json(out / "service_calendar_cases.json", cases)
    regional_map(maps, data)
    historical_map(maps, data)
    site_map(maps, data)
    underground_map(maps, data)
    geography_outputs(out / "geography", data)
    db = out / "operations.sqlite3"
    if db.exists():
        db.unlink()
    with closing(sqlite3.connect(db)) as con:
        for name in registers:
            con.execute(f'CREATE TABLE "{name}" (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
            con.executemany(
                f'INSERT INTO "{name}" VALUES (?,?)',
                [
                    (r["id"], json.dumps(r, sort_keys=True, separators=(",", ":")))
                    for r in data[name]
                ],
            )
        con.commit()
        con.execute("VACUUM")
    write_json(out / "validation.json", result)
    manifest = {
        "document_id": "SH-IND-OPS-001",
        "source_sha256": hashlib.sha256((SOURCE / "operations.json").read_bytes()).hexdigest(),
        "cutoff": data["cutoff"],
        "generated": {
            str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(out.rglob("*"))
            if p.is_file() and p.name != "manifest.json"
        },
    }
    write_json(out / "manifest.json", manifest)
    return {
        "checks": result["check_count"],
        "rail_miles": result["measured_rail_miles"],
        "generated_files": len(manifest["generated"]),
        "output": str(out),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--verify-geography", action="store_true")
    args = parser.parse_args()
    if args.verify_geography:
        print(json.dumps(geography_verification(), sort_keys=True))
    elif args.validate_only:
        result = validate(load())
        print(
            json.dumps(
                {"passed": result["passed"], "checks": result["check_count"]}, sort_keys=True
            )
        )
    else:
        print(json.dumps(build(args.out), sort_keys=True))


if __name__ == "__main__":
    main()
