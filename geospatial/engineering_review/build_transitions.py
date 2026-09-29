"""Derive a preliminary, junction-matched vertical screen for Taylor branches.

This is a successor *screen*, not a construction profile. It does not alter the
accepted source geometry, original grade-only profiles or historical releases.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
from pyproj import Transformer
from scipy.optimize import linprog
from scipy.sparse import lil_matrix
from shapely.geometry import Point, shape
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).with_name("VERTICAL_TRANSITION_SCREEN.json")
SOURCES = {
    "network": "industrial/source/geography/network.geojson",
    "main_profile": "industrial/source/geography/candidate_comparison.json",
    "branch_profiles": "industrial/source/geography/derived_ground_profiles.json",
}
TO_UTM = Transformer.from_crs(4326, 26913, always_xy=True).transform
GRADE_LIMIT = 0.018
RADIUS_PROXY_M = 10000.0
CUT_FILL_BOUND_M = 12.0


def _load(name: str):
    return json.loads((ROOT / SOURCES[name]).read_text())


def solve(stations: list[dict], junction_elevation_m: float) -> list[float]:
    """Minimize absolute cut/fill with grade and discrete grade-change bounds."""
    chainage = np.asarray([s["chainage_m"] for s in stations], dtype=float)
    ground = np.asarray([s["ground_m"] for s in stations], dtype=float)
    n = len(stations)
    if n < 3 or not np.isfinite(chainage).all() or not np.isfinite(ground).all():
        raise ValueError("Invalid branch profile stations")
    if chainage[0] != 0 or not (np.diff(chainage) > 0).all():
        raise ValueError("Branch chainage must increase from zero")
    if not math.isfinite(junction_elevation_m):
        raise ValueError("Invalid junction elevation")
    rows = 2 * n + 2 * (n - 1) + 2 * (n - 2)
    matrix = lil_matrix((rows, 2 * n))
    limits = np.zeros(rows)
    index = 0

    def add(terms, limit):
        nonlocal index
        for col, value in terms:
            matrix[index, col] += value
        limits[index] = limit
        index += 1

    for i, elevation in enumerate(ground):
        add(((i, 1), (n + i, -1)), elevation)
        add(((i, -1), (n + i, -1)), -elevation)
    for i, interval in enumerate(np.diff(chainage)):
        add(((i + 1, 1), (i, -1)), GRADE_LIMIT * interval)
        add(((i + 1, -1), (i, 1)), GRADE_LIMIT * interval)
    for i in range(1, n - 1):
        before = chainage[i] - chainage[i - 1]
        after = chainage[i + 1] - chainage[i]
        # Discrete proxy for |change in slope| <= mean station interval / R.
        limit = (before + after) / (2 * RADIUS_PROXY_M)
        for sign in (-1, 1):
            add(
                (
                    (i + 1, sign / after),
                    (i, -sign * (1 / after + 1 / before)),
                    (i - 1, sign / before),
                ),
                limit,
            )
    bounds = [(float(z - CUT_FILL_BOUND_M), float(z + CUT_FILL_BOUND_M)) for z in ground]
    bounds += [(0, None)] * n
    bounds[0] = (junction_elevation_m, junction_elevation_m)
    bounds[n - 1] = (float(ground[-1]), float(ground[-1]))
    objective = np.r_[np.zeros(n), np.ones(n)]
    result = linprog(objective, A_ub=matrix.tocsr(), b_ub=limits, bounds=bounds, method="highs")
    if not result.success:
        raise ValueError(f"No feasible junction-matched preliminary profile: {result.message}")
    formation = result.x[:n]
    grades = np.diff(formation) / np.diff(chainage)
    grade_changes = np.abs(np.diff(grades))
    proxies = (np.diff(chainage)[:-1] + np.diff(chainage)[1:]) / (2 * RADIUS_PROXY_M)
    if (
        max(abs(grades)) > GRADE_LIMIT + 1e-9
        or max(grade_changes / proxies) > 1 + 1e-8
        or max(abs(formation - ground)) > CUT_FILL_BOUND_M + 1e-9
    ):
        raise ValueError("Optimizer output violates a declared screen constraint")
    return [float(value) for value in formation]


def build() -> dict:
    network = {f["id"]: f for f in _load("network")["features"]}
    mainline = transform(TO_UTM, shape(network["BST-MAIN"]["geometry"]))
    comparison = _load("main_profile")
    selected = [c for c in comparison["candidates"] if c["candidate_id"] == "TAYLOR-A"]
    if len(selected) != 1:
        raise ValueError("Selected Taylor A mainline is not unique")
    baseline = selected[0]["legacy_corridor"]
    main_chainage = np.asarray([s["chainage_m"] for s in baseline["ground_profile"]])
    main_formation = np.asarray(baseline["vertical_design"]["track_elevations_m"])
    if len(main_chainage) != len(main_formation) or abs(mainline.length - main_chainage[-1]) > 0.1:
        raise ValueError("Mainline profile and geometry do not align")
    profiles = {r["route_id"]: r for r in _load("branch_profiles")}
    if set(profiles) != {"BST-EAST", "BST-MINERAL", "ROAD-RW-01"}:
        raise ValueError("Branch/road source profile population changed")
    successors = []
    for route_id in ("BST-EAST", "BST-MINERAL"):
        branch = transform(TO_UTM, shape(network[route_id]["geometry"]))
        start = Point(branch.coords[0])
        if start.distance(mainline) > 0.01:
            raise ValueError(f"{route_id} no longer joins the mainline")
        main_station = mainline.project(start)
        junction_elevation = float(np.interp(main_station, main_chainage, main_formation))
        record = profiles[route_id]
        stations = record["stations"]
        if abs(branch.length - stations[-1]["chainage_m"]) > 0.1:
            raise ValueError(f"{route_id} profile and geometry lengths differ")
        formation = solve(stations, junction_elevation)
        chainage = np.asarray([s["chainage_m"] for s in stations])
        ground = np.asarray([s["ground_m"] for s in stations])
        grades = np.diff(formation) / np.diff(chainage)
        changes = np.abs(np.diff(grades))
        proxies = (np.diff(chainage)[:-1] + np.diff(chainage)[1:]) / (2 * RADIUS_PROXY_M)
        successors.append(
            {
                "route_id": route_id,
                "status": "PROPOSED_PRELIMINARY_ENGINEERING_SCREEN",
                "mainline_junction_chainage_m": float(main_station),
                "mainline_junction_formation_m": junction_elevation,
                "source_branch_start_formation_m": stations[0]["formation_m"],
                "source_junction_elevation_gap_m": stations[0]["formation_m"] - junction_elevation,
                "successor_junction_elevation_gap_m": formation[0] - junction_elevation,
                "maximum_sampled_formation_grade_pct": float(max(abs(grades)) * 100),
                "maximum_adjacent_grade_change_percentage_points": float(max(changes) * 100),
                "maximum_discrete_curvature_fraction": float(max(changes / proxies)),
                "maximum_cut_m": float(max(ground - formation)),
                "maximum_fill_m": float(max(formation - ground)),
                "stations": [
                    {
                        "chainage_m": s["chainage_m"],
                        "ground_m": s["ground_m"],
                        "proposed_formation_m": elevation,
                    }
                    for s, elevation in zip(stations, formation)
                ],
                "open_interface": "Turnout/switch vertical tangent, drainage, structures, geotechnical section, construction and land rights not designed.",
            }
        )
    return {
        "schema": "rail-vertical-transition-screen-v1",
        "source_paths": SOURCES,
        "source_sha256": {
            name: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for name, path in SOURCES.items()
        },
        "projection": "EPSG:26913",
        "method": "Sparse linear program minimizes L1 absolute formation-to-ground difference; branch start fixed to interpolated selected mainline formation, remote end fixed to source ground; sampled grade and unequal-station discrete grade-change bounded.",
        "maximum_sampled_grade_pct": GRADE_LIMIT * 100,
        "discrete_vertical_radius_proxy_m": RADIUS_PROXY_M,
        "maximum_absolute_cut_or_fill_m": CUT_FILL_BOUND_M,
        "branches": successors,
        "decision_boundary": "Proposed synthetic engineering derivative, not an accepted alteration of pinned industrial source, surveyed alignment, continuous turnout design or operating approval.",
    }


def main() -> None:
    OUTPUT.write_text(json.dumps(build(), indent=2) + "\n")


if __name__ == "__main__":
    main()
