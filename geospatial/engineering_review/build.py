"""Reperform the accepted railway profiles without promoting screens to designs.

The industrial source bytes are read, not changed. Distances in the profile are
projected chainage; the accepted route-mile ledger uses geodesic route miles.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).with_name("PROFILE_AND_HISTORY_REVIEW.json")
SOURCES = {
    "epochs": "industrial/source/operations.json",
    "network": "geospatial/geojson/rail_network.geojson",
    "abandoned": "geospatial/geojson/rail_abandoned.geojson",
    "main_profile": "industrial/source/geography/candidate_comparison.json",
    "branch_profiles": "industrial/source/geography/derived_ground_profiles.json",
}


def _read(relative: str):
    return json.loads((ROOT / relative).read_text())


def assess_profile(
    route_id: str,
    chainage: list[float],
    ground: list[float],
    formation: list[float],
    grade_limit_pct: float,
    model: str,
) -> dict:
    """Compute sampled grades and abrupt adjacent-grade changes; do not design curves."""
    if not (len(chainage) == len(ground) == len(formation)) or len(chainage) < 3:
        raise ValueError(f"{route_id}: profile dimensions invalid")
    if not all(math.isfinite(v) for row in (chainage, ground, formation) for v in row):
        raise ValueError(f"{route_id}: nonfinite profile value")
    if chainage[0] != 0 or any(b <= a for a, b in zip(chainage, chainage[1:])):
        raise ValueError(f"{route_id}: chainage is not strictly increasing from zero")
    grades = [
        (b - a) / (end - start) * 100
        for a, b, start, end in zip(formation, formation[1:], chainage, chainage[1:])
    ]
    jump_index = max(range(1, len(grades)), key=lambda i: abs(grades[i] - grades[i - 1]))
    max_grade = max(abs(value) for value in grades)
    if max_grade > grade_limit_pct + 1e-8:
        raise ValueError(f"{route_id}: sampled grade exceeds source constraint")
    return {
        "route_id": route_id,
        "model": model,
        "station_count": len(chainage),
        "profile_chainage_end_m": chainage[-1],
        "maximum_sampled_formation_grade_pct": max_grade,
        "maximum_adjacent_grade_change_percentage_points": abs(
            grades[jump_index] - grades[jump_index - 1]
        ),
        "largest_grade_break_chainage_m": chainage[jump_index],
        "maximum_cut_m": max(g - f for g, f in zip(ground, formation)),
        "maximum_fill_m": max(f - g for g, f in zip(ground, formation)),
        "grade_constraint_pct": grade_limit_pct,
        "vertical_curve_design_status": (
            "CONSTRAINED_PRELIMINARY_SCREEN_NOT_CERTIFIED"
            if model == "CONSTRAINED_L1"
            else "NOT_MODELED"
        ),
    }


def build() -> dict:
    operations = _read(SOURCES["epochs"])
    network = _read(SOURCES["network"])["features"]
    abandoned = _read(SOURCES["abandoned"])["features"]
    candidates = _read(SOURCES["main_profile"])
    branches = _read(SOURCES["branch_profiles"])
    epochs = operations["geography"]["historical_route_epochs"]
    early = [e for e in epochs if e["epoch"] in {"1898", "1954"}]
    if {e["epoch"] for e in early} != {"1898", "1954"}:
        raise ValueError("The two unlocated historical epochs are missing")
    if any(f["properties"]["valid_from"] < "1968-10-14" for f in network):
        raise ValueError("Modern network feature back-projected into the unlocated history")
    if len({f["id"] for f in network}) != len(network) or len(network) != 5:
        raise ValueError("Current railway feature population changed")
    if abandoned:
        raise ValueError("Abandoned geometry now needs an evidence and time review")
    lengths = {f["properties"]["route_id"]: 0.0 for f in network}
    for feature in network:
        lengths[feature["properties"]["route_id"]] += feature["properties"]["route_miles"]
    if not math.isclose(sum(lengths.values()), 40, abs_tol=1e-7):
        raise ValueError("Current route-mile population no longer reconciles to 40")
    if not math.isclose(lengths["BST-MAIN"], epochs[2]["route_miles"], abs_tol=1e-7):
        raise ValueError("1968 mainline route miles do not reconcile")

    selected = [c for c in candidates["candidates"] if c["candidate_id"] == "TAYLOR-A"]
    if len(selected) != 1:
        raise ValueError("Accepted Taylor A profile is not unique")
    main = selected[0]["legacy_corridor"]
    stations = main["ground_profile"]
    main_grade_limit = main["vertical_design"]["design_grade_limit_pct"]
    if not math.isclose(main_grade_limit, operations["capacity_model"]["max_formation_grade_pct"]):
        raise ValueError("Mainline profile and capacity-model grade limits disagree")
    main_assessment = assess_profile(
        "BST-MAIN",
        [s["chainage_m"] for s in stations],
        [s["elevation_m"] for s in stations],
        main["vertical_design"]["track_elevations_m"],
        main_grade_limit,
        "CONSTRAINED_L1",
    )
    profiles = [main_assessment]
    for record in branches:
        if record["route_id"] not in {"BST-EAST", "BST-MINERAL", "ROAD-RW-01"}:
            raise ValueError("Unexpected branch/road profile")
        stations = record["stations"]
        profiles.append(
            assess_profile(
                record["route_id"],
                [s["chainage_m"] for s in stations],
                [s["ground_m"] for s in stations],
                [s["formation_m"] for s in stations],
                record["constraint_max_grade_pct"],
                "GRADE_ONLY_L1",
            )
        )
    if len(profiles) != 4 or len({p["route_id"] for p in profiles}) != 4:
        raise ValueError("Profile population incomplete or duplicated")

    historical = []
    for epoch in epochs:
        year = epoch["epoch"]
        historical.append(
            {
                "epoch": year,
                "history_id": epoch["history_id"],
                "effective_date": epoch["effective_date"],
                "source_extent_state": epoch["extent_state"],
                "route_miles": epoch.get("route_miles"),
                "surviving_route_miles_low": epoch.get("surviving_route_miles_low"),
                "surviving_route_miles_high": epoch.get("surviving_route_miles_high"),
                "georeferenced_alignment_available": year not in {"1898", "1954"},
                "geometry_basis": (
                    "UNLOCATED_SOURCE_CLAIM"
                    if year in {"1898", "1954"}
                    else "ACCEPTED_LATER_SYNTHETIC_ROUTE_CASE"
                ),
            }
        )
    surviving = next(e for e in epochs if e["epoch"] == "1954")
    completed = next(e for e in epochs if e["epoch"] == "1968")
    low = completed["route_miles"] - surviving["surviving_route_miles_high"]
    high = completed["route_miles"] - surviving["surviving_route_miles_low"]
    if not (
        math.isclose(low, completed["net_route_growth_from_1954_low"], abs_tol=1e-8)
        and math.isclose(high, completed["net_route_growth_from_1954_high"], abs_tol=1e-8)
    ):
        raise ValueError("1954–1968 net-growth interval no longer reconciles")
    return {
        "schema": "rail-engineering-source-review-v1",
        "source_sha256": {
            name: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for name, path in SOURCES.items()
        },
        "source_paths": SOURCES,
        "current_route_miles": lengths,
        "historical_epochs": historical,
        "unlocated_alignment_population": [
            {"object": "1898 coal-era line", "geometry": None, "basis": "UNKNOWN_EARLY_ALIGNMENT"},
            {
                "object": "1954 surviving 14–16-mile estate",
                "geometry": None,
                "basis": "RECONSTRUCTED_RANGE_UNLOCATED",
            },
            {
                "object": "abandoned/relocated historical track",
                "geometry": None,
                "basis": "NO_ACCEPTED_LINEWORK",
            },
        ],
        "net_1954_to_1968_route_growth_miles": {"low": low, "high": high},
        "profiles": profiles,
        "limitations": [
            "The 1898, 1954 and abandoned alignments remain unlocated; a 15-mile current segment does not identify the 14–16 surviving miles.",
            "Profile chainage is projected, whereas accepted route miles are geodesic; they are separate measures.",
            "Adjacent sampled-grade change is a screening observation, not vertical-curve length, radius or ride-quality design.",
            "The East, Mineral and Red Wash road sources constrain grade only. Abrupt grade breaks have no designed transition.",
            "No cross sections, earthwork volumes, geotechnical/drainage/structure design, construction approval, parcel/title/access instrument or client-site footprint is established.",
        ],
    }


def main() -> None:
    OUTPUT.write_text(json.dumps(build(), indent=2) + "\n")


if __name__ == "__main__":
    main()
